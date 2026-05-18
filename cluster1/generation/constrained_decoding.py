"""Logits processor glue for grammar and hardware masks."""

from __future__ import annotations

from statistics import mean

from cluster1.constraints.hardware_checker import HardwareChecker

try:
    from transformers import LogitsProcessor
except Exception:  # pragma: no cover - exercised only when transformers is absent.
    class LogitsProcessor:  # type: ignore[no-redef]
        pass


class TritonGrammarLogitsProcessor(LogitsProcessor):
    def __init__(
        self,
        compiled_grammar,
        tokenizer,
        hardware_checker: HardwareChecker | None = None,
        prompt_length: int = 0,
    ) -> None:
        self.compiled_grammar = compiled_grammar
        self.tokenizer = tokenizer
        self.hardware_checker = hardware_checker
        self.prompt_length = prompt_length
        self._masked_fractions: list[float] = []
        self._xgr = None
        self._matcher = None
        self._token_bitmask = None
        self._bitmask_vocab_size: int | None = None
        self._accepted_length: int | None = None
        self._backend = getattr(compiled_grammar, "backend_grammar", compiled_grammar)
        self._grammar_vocab_size = (
            _compiled_grammar_vocab_size(self._backend)
            or _tokenizer_mask_vocab_size(tokenizer)
        )
        self._uses_fake_mask_api = _has_direct_mask_api(self._backend)
        if not self._uses_fake_mask_api:
            self._init_xgrammar_matcher()

    def __call__(self, input_ids, scores):
        logits_vocab_size = _vocab_size_from_scores(scores)
        allowed = set(range(logits_vocab_size))
        grammar_allowed = self._grammar_allowed_token_ids(input_ids, scores, logits_vocab_size)
        if grammar_allowed is not None:
            allowed &= grammar_allowed

        hardware_allowed = _hardware_allowed_token_ids(
            self.hardware_checker,
            self.tokenizer,
            input_ids,
            logits_vocab_size,
            self.prompt_length,
        )
        if hardware_allowed is not None:
            hardware_allowed = set(hardware_allowed)
            intersected = allowed & hardware_allowed
            if intersected or grammar_allowed is None:
                allowed = intersected

        if not allowed and logits_vocab_size:
            raise RuntimeError(
                "grammar/hardware mask allowed zero tokens "
                f"(grammar_allowed={len(grammar_allowed) if grammar_allowed is not None else 'all'}, "
                f"hardware_allowed={len(hardware_allowed) if hardware_allowed is not None else 'all'}, "
                f"logits_vocab_size={logits_vocab_size}, "
                f"grammar_vocab_size={self._grammar_vocab_size})"
            )

        masked = logits_vocab_size - len(allowed)
        self._masked_fractions.append(masked / logits_vocab_size if logits_vocab_size else 0.0)
        _apply_disallowed(scores, allowed, logits_vocab_size)
        return scores

    def masked_token_rate(self) -> float:
        if not self._masked_fractions:
            return 0.0
        return float(mean(self._masked_fractions))

    def observe_generated_tokens(self, input_ids) -> None:
        """Advance matcher state through the final generated token sequence."""

        if self._uses_fake_mask_api:
            return
        self._accept_generated_tokens(input_ids)

    def grammar_final_state_observed(self) -> bool | None:
        """Return final-state status if the backend exposes it."""

        for target in (self._matcher, self._backend):
            if target is None:
                continue
            for name in (
                "is_terminated",
                "is_accepting",
                "is_final_state",
                "is_finished",
                "is_completed",
            ):
                method = getattr(target, name, None)
                if callable(method):
                    try:
                        return bool(method())
                    except TypeError:
                        continue
        return None

    def _init_xgrammar_matcher(self) -> None:
        try:
            import xgrammar as xgr
        except Exception as exc:  # noqa: BLE001 - dependency may be absent in unit env.
            raise RuntimeError(
                "compiled_grammar does not expose a direct mask API and xgrammar "
                "is not importable"
            ) from exc

        if not hasattr(xgr, "GrammarMatcher"):
            raise RuntimeError("xgrammar.GrammarMatcher is unavailable")
        self._xgr = xgr
        self._matcher = xgr.GrammarMatcher(self._backend)

    def _grammar_allowed_token_ids(self, input_ids, scores, logits_vocab_size: int) -> set[int]:
        if self._uses_fake_mask_api:
            direct_allowed = _direct_allowed_token_ids(self._backend, input_ids, scores)
            if direct_allowed is None:
                raise RuntimeError("direct grammar mask API returned no mask")
            return direct_allowed

        self._accept_generated_tokens(input_ids)
        grammar_vocab_size = self._grammar_vocab_size or logits_vocab_size
        grammar_vocab_size = min(grammar_vocab_size, logits_vocab_size)
        self._ensure_token_bitmask(grammar_vocab_size)
        need_apply = self._matcher.fill_next_token_bitmask(self._token_bitmask)
        if need_apply is False:
            return set(range(grammar_vocab_size))
        return _allowed_from_bitmask(self._token_bitmask, grammar_vocab_size)

    def _accept_generated_tokens(self, input_ids) -> None:
        token_ids = _first_sequence_token_ids(input_ids)
        if self._accepted_length is None:
            self._accepted_length = len(token_ids)
            return

        for token_id in token_ids[self._accepted_length :]:
            accepted = self._matcher.accept_token(int(token_id))
            if not accepted:
                raise RuntimeError(f"XGrammar matcher rejected token {token_id}")
        self._accepted_length = len(token_ids)

    def _ensure_token_bitmask(self, vocab_size: int) -> None:
        if self._token_bitmask is not None and self._bitmask_vocab_size == vocab_size:
            return
        if not hasattr(self._xgr, "allocate_token_bitmask"):
            raise RuntimeError("xgrammar.allocate_token_bitmask is unavailable")
        self._token_bitmask = _allocate_token_bitmask(self._xgr, vocab_size)
        self._bitmask_vocab_size = vocab_size


def _has_direct_mask_api(backend) -> bool:
    return any(
        hasattr(backend, name)
        for name in ("allowed_token_ids", "mask_for")
    )


def _direct_allowed_token_ids(backend, input_ids, scores) -> set[int] | None:
    allowed_method = getattr(backend, "allowed_token_ids", None)
    if callable(allowed_method):
        return set(allowed_method(input_ids))
    allowed_attr = getattr(backend, "allowed_token_ids", None)
    if allowed_attr is not None:
        return set(allowed_attr)
    mask_method = getattr(backend, "mask_for", None)
    if callable(mask_method):
        mask = mask_method(input_ids, scores)
        return {index for index, is_allowed in enumerate(mask) if is_allowed}
    return None


def _hardware_allowed_token_ids(
    hardware_checker: HardwareChecker | None,
    tokenizer,
    input_ids,
    vocab_size: int,
    prompt_length: int,
) -> set[int] | None:
    if hardware_checker is None:
        return None
    allowed_method = getattr(hardware_checker, "allowed_token_ids", None)
    if callable(allowed_method):
        allowed = allowed_method(
            tokenizer,
            input_ids,
            vocab_size,
            prompt_length=prompt_length,
        )
        if allowed is None:
            return None
        return set(allowed)
    return None


def _allowed_from_bitmask(bitmask, vocab_size: int) -> set[int]:
    row = bitmask[0]
    if hasattr(row, "tolist"):
        row = row.tolist()
    allowed: set[int] = set()
    for token_id in range(vocab_size):
        word_index = token_id // 32
        bit_index = token_id % 32
        if int(row[word_index]) & (1 << bit_index):
            allowed.add(token_id)
    return allowed


def _allocate_token_bitmask(xgr, vocab_size: int):
    """Allocate a token bitmask across XGrammar API argument-order variants."""
    buffer_size = (vocab_size + 31) // 32
    last_bitmask = None
    for args in ((1, vocab_size), (vocab_size, 1)):
        bitmask = xgr.allocate_token_bitmask(*args)
        if _bitmask_buffer_width(bitmask) == buffer_size:
            return bitmask
        last_bitmask = bitmask
    return last_bitmask


def _bitmask_buffer_width(bitmask) -> int | None:
    shape = getattr(bitmask, "shape", None)
    if shape is not None and len(shape) >= 2:
        return int(shape[1])
    try:
        first_row = bitmask[0]
    except Exception:
        return None
    try:
        return len(first_row)
    except TypeError:
        return None


def _tokenizer_mask_vocab_size(tokenizer) -> int | None:
    get_vocab = getattr(tokenizer, "get_vocab", None)
    if callable(get_vocab):
        try:
            vocab = get_vocab()
        except Exception:
            vocab = None
        if vocab:
            return max(int(token_id) for token_id in vocab.values()) + 1

    vocab_size = getattr(tokenizer, "vocab_size", None)
    if vocab_size is None:
        return None
    return int(vocab_size)


def _compiled_grammar_vocab_size(compiled_grammar) -> int | None:
    tokenizer_info = getattr(compiled_grammar, "tokenizer_info", None)
    vocab_size = getattr(tokenizer_info, "vocab_size", None)
    return int(vocab_size) if vocab_size is not None else None


def _first_sequence_token_ids(input_ids) -> list[int]:
    shape = getattr(input_ids, "shape", None)
    if shape is not None:
        sequence = input_ids[0] if len(shape) == 2 else input_ids
    elif input_ids and isinstance(input_ids[0], list):
        sequence = input_ids[0]
    else:
        sequence = input_ids
    if hasattr(sequence, "tolist"):
        sequence = sequence.tolist()
    return [int(token_id) for token_id in sequence]


def _vocab_size_from_scores(scores) -> int:
    shape = getattr(scores, "shape", None)
    if shape is not None:
        return int(shape[-1])
    first_row = scores[0] if scores and isinstance(scores[0], list) else scores
    return len(first_row)


def _apply_disallowed(scores, allowed: set[int], vocab_size: int) -> None:
    disallowed = [index for index in range(vocab_size) if index not in allowed]
    if not disallowed:
        return

    try:
        scores[:, disallowed] = -float("inf")
        return
    except Exception:
        pass

    if scores and isinstance(scores[0], list):
        rows = scores
    else:
        rows = [scores]
    for row in rows:
        for index in disallowed:
            row[index] = -float("inf")
