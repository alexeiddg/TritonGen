"""Hardware-aware constraint checks for Cluster 1 generation."""

from __future__ import annotations

import re


BLOCK_DIM_VALUES = frozenset({16, 32, 64, 128, 256})
BLOCK_SIZE_VALUES = frozenset({64, 128, 256, 512})
WARP_VALUES = frozenset({1, 2, 4, 8, 16})
STAGE_VALUES = frozenset({1, 2, 3, 4, 5})
BLOCK_NAMES = frozenset({"BLOCK_SIZE", "BLOCK_M", "BLOCK_N", "BLOCK_K"})


class HardwareChecker:
    """Stateful per-generation checker for context-dependent Triton literals."""

    def __init__(self, smem_limit: int = 49152, dtype_bytes: int = 2) -> None:
        self.smem_limit = smem_limit
        self.dtype_bytes = dtype_bytes
        self.reset()

    def reset(self) -> None:
        self.assignments: dict[str, int] = {}
        self.block_params: set[str] = set()

    def validate_assignment(self, name: str, value: int) -> bool:
        if value not in self.allowed_values(name):
            return False
        if name in BLOCK_NAMES or name in {"num_warps", "num_stages"}:
            self.assignments[name] = value
        return True

    def allowed_values(self, name: str) -> set[int]:
        if name == "BLOCK_SIZE":
            return set(BLOCK_SIZE_VALUES)
        if name in {"BLOCK_M", "BLOCK_N", "BLOCK_K"}:
            values = set(BLOCK_DIM_VALUES)
            if name in {"BLOCK_M", "BLOCK_N"}:
                values = {
                    value
                    for value in values
                    if self._smem_valid_with(name, value)
                }
            return values
        if name == "num_warps":
            return set(WARP_VALUES)
        if name == "num_stages":
            return set(STAGE_VALUES)
        return set()

    def validate_arange(
        self,
        start: int,
        end: int,
        block_name: str | None = None,
    ) -> bool:
        if start != 0:
            return False
        if block_name is not None:
            return self.assignments.get(block_name) == end

        sampled_blocks = [
            value
            for name, value in self.assignments.items()
            if name in BLOCK_NAMES
        ]
        if not sampled_blocks:
            return end in BLOCK_DIM_VALUES or end in BLOCK_SIZE_VALUES
        return end in sampled_blocks

    def validate_dot_shapes(
        self,
        lhs_shape: tuple[int, ...],
        rhs_shape: tuple[int, ...],
    ) -> bool:
        # Design decision: this method is NOT called from allowed_token_ids() during
        # autoregressive decoding. Shape compatibility depends on resolved symbolic
        # tensor bindings across multiple generated statements; enforcing it at the
        # prefix level would require an incremental semantic parser beyond Phase 3
        # scope and beyond H5's stated requirement. validate_dot_shapes() is kept as
        # a unit-tested post-hoc semantic utility. Phase 3 masking covers BLOCK_*
        # literals, num_warps, num_stages, shared-memory limits, and arange
        # consistency — which transitively constrain dot shapes when BLOCK dimensions
        # are correctly assigned.
        if len(lhs_shape) < 2 or len(rhs_shape) < 2:
            return False
        return lhs_shape[-1] == rhs_shape[-2]

    def allowed_token_ids(
        self,
        tokenizer,
        input_ids,
        vocab_size: int,
        prompt_length: int = 0,
    ) -> set[int] | None:
        """Return allowed token IDs when the decoded prefix expects a constrained int.

        This is intentionally conservative: if the checker cannot recognize the
        next-token context, it returns None and leaves masking to the grammar.
        """

        prefix = _decode_prefix(tokenizer, input_ids, prompt_length)
        self.record_completed_surface_bindings(prefix)
        name = _pending_assignment_name(prefix)
        # validate_dot_shapes() is intentionally not called here — see its docstring.
        if name is None:
            # Phase A: sampling the *start* argument of tl.arange — must be 0.
            if _pending_arange_start(prefix):
                current_literal = _pending_arange_start_fragment(prefix)
                allowed_values = {"0"}
            else:
                # Phase B: sampling the *end* argument of tl.arange(0, ...).
                allowed_values = _pending_arange_values(
                    prefix,
                    self.assignments,
                    self.block_params,
                )
                if allowed_values is None:
                    return None
                current_literal = _pending_arange_fragment(prefix)
        else:
            allowed_values = {str(value) for value in self.allowed_values(name)}
            current_literal = _pending_numeric_fragment(prefix, name)

        if not allowed_values:
            return None

        allowed_ids: set[int] = set()
        for token_id in range(vocab_size):
            token_text = _decode_token(tokenizer, token_id)
            if _token_keeps_value_valid(current_literal, token_text, allowed_values):
                allowed_ids.add(token_id)
        return allowed_ids

    def record_completed_surface_bindings(self, text: str) -> None:
        for match in _COMPLETED_ASSIGNMENT_RE.finditer(text):
            name = match.group("name")
            value = int(match.group("value"))
            if value in self.allowed_values(name):
                self.assignments[name] = value
        for match in _COMPLETED_BLOCK_PARAM_RE.finditer(text):
            self.block_params.add(match.group("name"))

    def record_completed_assignments(self, text: str) -> None:
        self.record_completed_surface_bindings(text)

    def _smem_valid_with(self, name: str, value: int) -> bool:
        block_m = value if name == "BLOCK_M" else self.assignments.get("BLOCK_M")
        block_n = value if name == "BLOCK_N" else self.assignments.get("BLOCK_N")
        if block_m is None or block_n is None:
            return True
        return block_m * block_n * self.dtype_bytes <= self.smem_limit


_ASSIGNMENT_RE = re.compile(
    r"(BLOCK_SIZE|BLOCK_M|BLOCK_N|BLOCK_K|num_warps|num_stages)\s*=\s*[0-9]*$"
)
_COMPLETED_ASSIGNMENT_RE = re.compile(
    r"(?P<name>BLOCK_SIZE|BLOCK_M|BLOCK_N|BLOCK_K|num_warps|num_stages)"
    r"\s*=\s*(?P<value>[0-9]+)\b"
)
_COMPLETED_BLOCK_PARAM_RE = re.compile(
    r"(?P<name>BLOCK_[A-Za-z0-9_]*)\s*:\s*tl\.constexpr"
)
# Detects the generation of tl.arange's *start* argument before the comma.
# Matches as soon as `tl.arange(` appears with an optional in-progress digit
# fragment and no comma yet — the only valid start is 0.
_ARANGE_START_RE = re.compile(r"tl\.arange\(\s*([0-9]*)$")
# Detects the generation of tl.arange's *end* argument (after `tl.arange(0,`).
_ARANGE_RE = re.compile(r"tl\.arange\(\s*0\s*,\s*([A-Za-z0-9_]*)$")


def _pending_assignment_name(prefix: str) -> str | None:
    match = _ASSIGNMENT_RE.search(prefix)
    if match is None:
        return None
    return match.group(1)


def _pending_numeric_fragment(prefix: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*=\s*([0-9]*)$", prefix)
    if match is None:
        return ""
    return match.group(1)


def _pending_arange_start(prefix: str) -> bool:
    """Return True when the prefix is mid-way through the start argument of tl.arange.

    Specifically, this fires when `tl.arange(` is present but no comma has
    been emitted yet — meaning the model is still choosing the start value.
    It returns False once `tl.arange(0,` appears (end-argument phase).
    """
    return (
        _ARANGE_START_RE.search(prefix) is not None
        and _ARANGE_RE.search(prefix) is None
    )


def _pending_arange_start_fragment(prefix: str) -> str:
    """Return the digit(s) already emitted for the start argument, or ''."""
    match = _ARANGE_START_RE.search(prefix)
    if match is None:
        return ""
    return match.group(1)


def _pending_arange_fragment(prefix: str) -> str:
    match = _ARANGE_RE.search(prefix)
    if match is None:
        return ""
    return match.group(1)


def _pending_arange_values(
    prefix: str,
    assignments: dict[str, int],
    block_params: set[str] | None = None,
) -> set[str] | None:
    if _ARANGE_RE.search(prefix) is None:
        return None
    block_params = block_params or set()
    symbolic_blocks = {
        name
        for name in assignments
        if name in BLOCK_NAMES
    } | block_params
    sampled_blocks = {
        str(assignments[name])
        for name in symbolic_blocks & set(assignments)
    }
    literal_blocks = {str(value) for value in BLOCK_DIM_VALUES | BLOCK_SIZE_VALUES}
    if sampled_blocks:
        return sampled_blocks | symbolic_blocks
    if symbolic_blocks:
        return symbolic_blocks | literal_blocks
    return literal_blocks


def _token_keeps_value_valid(
    current_fragment: str,
    token_text: str,
    allowed_values: set[str],
) -> bool:
    stripped = token_text.strip()
    if stripped == "":
        return current_fragment == "" or current_fragment in allowed_values
    if current_fragment in allowed_values and not stripped[0].isalnum():
        return True
    candidate = current_fragment + stripped
    if any(value.startswith(candidate) for value in allowed_values):
        return True

    digit_prefix = _leading_digits(stripped)
    if digit_prefix and digit_prefix != stripped:
        numeric_candidate = current_fragment + digit_prefix
        return any(value.startswith(numeric_candidate) for value in allowed_values)
    return False


def _leading_digits(value: str) -> str:
    digits = []
    for char in value:
        if not char.isdigit():
            break
        digits.append(char)
    return "".join(digits)


def _decode_prefix(tokenizer, input_ids, prompt_length: int = 0) -> str:
    shape = getattr(input_ids, "shape", None)
    if shape is not None:
        sequence = input_ids[0] if len(shape) == 2 else input_ids
    elif input_ids and isinstance(input_ids[0], list):
        sequence = input_ids[0]
    else:
        sequence = input_ids
    if hasattr(sequence, "tolist"):
        sequence = sequence.tolist()
    if prompt_length:
        sequence = sequence[prompt_length:]
    try:
        return tokenizer.decode(sequence, skip_special_tokens=True)
    except TypeError:
        return tokenizer.decode(sequence)


def _decode_token(tokenizer, token_id: int) -> str:
    try:
        return tokenizer.decode([token_id], skip_special_tokens=True)
    except TypeError:
        return tokenizer.decode([token_id])
