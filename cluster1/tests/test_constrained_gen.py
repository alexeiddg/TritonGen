"""Phase 3 constrained generation tests using fake model/tokenizer objects."""

from __future__ import annotations

import sys
import types

import pytest

from cluster1.constraints.hardware_checker import HardwareChecker
from cluster1.generation import grammar_loader
from cluster1.generation.constrained_decoding import TritonGrammarLogitsProcessor
from cluster1.generation.constrained_gen import generate_source
from cluster1.grammar.test_grammar_acceptance import GOOD_KERNELS
from cluster1.grammar.triton_kernel_validator import accepts_source


class FakeTokenizer:
    def __init__(
        self,
        vocab: dict[str, int] | None = None,
        input_ids=None,
    ) -> None:
        self._vocab = vocab or {"<pad>": 0, "valid": 1, "invalid": 2, "x": 3}
        self.next_decode = ""
        self.input_ids = input_ids or [[101, 102]]

    def get_vocab(self) -> dict[str, int]:
        return self._vocab

    def __call__(self, prompt: str, return_tensors: str):
        return {"input_ids": self.input_ids}

    def decode(self, token_ids, skip_special_tokens: bool = True) -> str:
        return self.next_decode


class MappingTokenizer(FakeTokenizer):
    def __init__(self, tokens: dict[int, str], input_ids=None) -> None:
        super().__init__(input_ids=input_ids)
        self.tokens = tokens

    def decode(self, token_ids, skip_special_tokens: bool = True) -> str:
        return "".join(self.tokens[token_id] for token_id in token_ids)


class FakeCompiledGrammar:
    def allowed_token_ids(self, input_ids):
        return {1, 2}


class FakeFullGrammar:
    def allowed_token_ids(self, input_ids):
        return {0, 1, 2, 3, 4, 5}


class TokenMaskTokenizer:
    def __init__(self) -> None:
        self.tokens = {
            0: "BLOCK_M = ",
            1: "16",
            2: "37",
            3: "64",
            4: "256",
            5: "\nBLOCK_N = ",
            6: "1",
            7: "28",
            8: "5",
            9: "512",
            10: "BLOCK_SIZE = ",
            11: "64",
            12: "\n",
            13: "num_warps=",
            14: "4",
            15: ",",
            16: "0",
            17: ")",
            18: "6",
            19: "tl.arange(0, ",
            20: " ",
            21: "BLOCK_SIZE",
            22: "BLOCK_M",
            23: "BLOCK_N",
            24: "BLOCK",
            25: "_SIZE",
            26: "_M",
        }

    def decode(self, token_ids, skip_special_tokens: bool = True) -> str:
        return "".join(self.tokens[token_id] for token_id in token_ids)


class FakeXGrammarModule:
    def __init__(self, fill_return=True) -> None:
        self.last_matcher = None
        self.fill_return = fill_return
        self.allocate_calls: list[tuple[int, int]] = []

    def allocate_token_bitmask(self, batch_size: int, vocab_size: int):
        self.allocate_calls.append((batch_size, vocab_size))
        return [[0 for _ in range((vocab_size + 31) // 32)] for _ in range(batch_size)]

    def GrammarMatcher(self, compiled_grammar):  # noqa: N802 - mirrors xgrammar API.
        self.last_matcher = FakeXGrammarMatcher(compiled_grammar, self.fill_return)
        return self.last_matcher


class FakeReversedXGrammarModule(FakeXGrammarModule):
    def allocate_token_bitmask(self, vocab_size: int, batch_size: int):
        self.allocate_calls.append((vocab_size, batch_size))
        return [[0 for _ in range((vocab_size + 31) // 32)] for _ in range(batch_size)]


class FakeXGrammarMatcher:
    def __init__(self, compiled_grammar, fill_return=True) -> None:
        self.compiled_grammar = compiled_grammar
        self.fill_return = fill_return
        self.accepted_tokens: list[int] = []

    def accept_token(self, token_id: int) -> bool:
        self.accepted_tokens.append(token_id)
        return True

    def fill_next_token_bitmask(self, bitmask) -> bool:
        bitmask[0][0] = (1 << 1) | (1 << 3)
        return self.fill_return


class FakeModel:
    def __init__(self, tokenizer: FakeTokenizer, source: str) -> None:
        self.tokenizer = tokenizer
        self.source = source
        self.calls: list[dict] = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        for processor in kwargs.get("logits_processor", []):
            processor([[101, 102]], [[0.0, 0.0, 0.0, 0.0]])
        self.tokenizer.next_decode = self.source
        return [[101, 102, 1]]


class FakeTensor:
    def __init__(self, values, device: str = "cpu") -> None:
        self.values = values
        self.device = device
        self.shape = (len(values), len(values[0]))

    def to(self, device: str):
        return FakeTensor(self.values, device=device)

    def __getitem__(self, index):
        return self.values[index]


class FakeCudaModel(FakeModel):
    device = "cuda:0"


class FakeXGrammarCompilerModule:
    class Grammar:
        @staticmethod
        def from_ebnf(grammar_text: str, root_rule_name: str = "root"):
            return {"grammar_text": grammar_text, "root_rule_name": root_rule_name}


def test_tokenizer_info_retries_with_tokenizer_object(monkeypatch) -> None:
    captured = {}

    class FakeTokenizerInfo:
        @staticmethod
        def from_huggingface(tokenizer_or_id):
            if isinstance(tokenizer_or_id, str):
                raise ValueError("expected tokenizer object")
            captured["tokenizer"] = tokenizer_or_id
            return "tokenizer-info"

    class FakeXGrammar:
        TokenizerInfo = FakeTokenizerInfo

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(tokenizer_id: str):
            return {"tokenizer_id": tokenizer_id}

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(tokenizer_id: str):
            return types.SimpleNamespace(vocab_size=128)

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            AutoConfig=FakeAutoConfig,
            AutoTokenizer=FakeAutoTokenizer,
        ),
    )

    tokenizer_info = grammar_loader._build_tokenizer_info(FakeXGrammar(), "model-id")

    assert tokenizer_info == "tokenizer-info"
    assert captured["tokenizer"] == {"tokenizer_id": "model-id"}


def test_tokenizer_info_uses_model_config_vocab_size(monkeypatch) -> None:
    captured = {}

    class FakeTokenizerInfo:
        @staticmethod
        def from_huggingface(tokenizer, *, vocab_size=None):
            captured["tokenizer"] = tokenizer
            captured["vocab_size"] = vocab_size
            return "tokenizer-info"

    class FakeXGrammar:
        TokenizerInfo = FakeTokenizerInfo

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(tokenizer_id: str):
            return {"tokenizer_id": tokenizer_id}

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(tokenizer_id: str):
            return types.SimpleNamespace(vocab_size=152064)

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            AutoConfig=FakeAutoConfig,
            AutoTokenizer=FakeAutoTokenizer,
        ),
    )

    tokenizer_info = grammar_loader._build_tokenizer_info(FakeXGrammar(), "model-id")

    assert tokenizer_info == "tokenizer-info"
    assert captured["tokenizer"] == {"tokenizer_id": "model-id"}
    assert captured["vocab_size"] == 152064


def test_compile_xgrammar_wraps_text_with_grammar_object(monkeypatch) -> None:
    captured = {}

    class FakeCompiler:
        def __init__(self, tokenizer_info) -> None:
            captured["tokenizer_info"] = tokenizer_info

        def compile_grammar(self, grammar):
            captured["grammar"] = grammar
            return "compiled"

    fake_xgr = FakeXGrammarCompilerModule()
    fake_xgr.GrammarCompiler = FakeCompiler
    monkeypatch.setitem(sys.modules, "xgrammar", fake_xgr)
    monkeypatch.setattr(
        grammar_loader,
        "_build_tokenizer_info",
        lambda xgr, tokenizer_id: "tokenizer-info",
    )

    compiled = grammar_loader._compile_xgrammar("root ::= \"x\"", "model-id")

    assert compiled == "compiled"
    assert captured["tokenizer_info"] == "tokenizer-info"
    assert captured["grammar"] == {
        "grammar_text": "root ::= \"x\"",
        "root_rule_name": "root",
    }


def test_cache_key_uses_vocab_fingerprint(monkeypatch, tmp_path) -> None:
    tokenizers = [
        FakeTokenizer({"a": 0, "b": 1}),
        FakeTokenizer({"a": 0, "b": 1, "c": 2}),
    ]
    call_index = {"value": 0}
    compile_calls: list[tuple[str, str]] = []

    def fake_load_tokenizer(tokenizer_id: str):
        tokenizer = tokenizers[call_index["value"]]
        call_index["value"] += 1
        return tokenizer

    def fake_compile(grammar_text: str, tokenizer_id: str):
        compile_calls.append((grammar_text, tokenizer_id))
        return {"compiled": len(compile_calls)}

    grammar_loader._load_compiled_grammar_cached.cache_clear()
    monkeypatch.setattr(grammar_loader, "_load_tokenizer", fake_load_tokenizer)
    monkeypatch.setattr(grammar_loader, "_compile_xgrammar", fake_compile)
    grammar_path = tmp_path / "triton_kernel.gbnf"
    grammar_path.write_text("root ::= \"x\"\n", encoding="utf-8")

    first = grammar_loader._vocab_fingerprint("same-id")
    second = grammar_loader._vocab_fingerprint("same-id")

    assert first != second

    call_index["value"] = 0
    grammar_loader.load_compiled_grammar(str(grammar_path), "same-id")
    grammar_loader.load_compiled_grammar(str(grammar_path), "same-id")

    assert len(compile_calls) == 2


def test_vocab_fingerprint_uses_middle_tokens(monkeypatch) -> None:
    base_vocab = {f"tok_{index}": index for index in range(120)}
    changed_vocab = dict(base_vocab)
    changed_vocab["changed_middle"] = changed_vocab.pop("tok_60")
    tokenizers = [FakeTokenizer(base_vocab), FakeTokenizer(changed_vocab)]
    call_index = {"value": 0}

    def fake_load_tokenizer(tokenizer_id: str):
        tokenizer = tokenizers[call_index["value"]]
        call_index["value"] += 1
        return tokenizer

    monkeypatch.setattr(grammar_loader, "_load_tokenizer", fake_load_tokenizer)

    assert grammar_loader._vocab_fingerprint("same-id") != grammar_loader._vocab_fingerprint(
        "same-id"
    )


def test_grammar_active_only_changes_logits_processor() -> None:
    valid_tokenizer = FakeTokenizer()
    invalid_tokenizer = FakeTokenizer()
    valid_model = FakeModel(valid_tokenizer, GOOD_KERNELS["relu"])
    invalid_model = FakeModel(invalid_tokenizer, "Here is a kernel:\nprint('bad')\n")

    on = generate_source(
        prompt="Write a Triton ReLU kernel.",
        model=valid_model,
        tokenizer=valid_tokenizer,
        grammar_active=True,
        compiled_grammar=FakeCompiledGrammar(),
        max_new_tokens=64,
        temperature=0.2,
        seed=7,
    )
    off = generate_source(
        prompt="Write a Triton ReLU kernel.",
        model=invalid_model,
        tokenizer=invalid_tokenizer,
        grammar_active=False,
        max_new_tokens=64,
        temperature=0.2,
        seed=7,
    )

    on_kwargs = dict(valid_model.calls[0])
    off_kwargs = dict(invalid_model.calls[0])
    on_kwargs.pop("logits_processor")

    assert on_kwargs == off_kwargs
    assert accepts_source(on.source)
    assert on.masked_token_rate is not None
    assert on.masked_token_rate > 0.0
    assert off.source == "Here is a kernel:\nprint('bad')\n"
    assert off.masked_token_rate is None
    assert not accepts_source(off.source)


def test_generate_moves_tokenized_inputs_to_model_device() -> None:
    tokenizer = FakeTokenizer(input_ids=FakeTensor([[101, 102]]))
    model = FakeCudaModel(tokenizer, GOOD_KERNELS["relu"])

    generate_source(
        prompt="Write a Triton ReLU kernel.",
        model=model,
        tokenizer=tokenizer,
        grammar_active=False,
    )

    assert model.calls[0]["input_ids"].device == "cuda:0"


def test_generate_resets_hardware_checker_per_generation() -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel(tokenizer, GOOD_KERNELS["relu"])
    checker = HardwareChecker()
    checker.assignments["BLOCK_M"] = 256

    generate_source(
        prompt="Write a Triton ReLU kernel.",
        model=model,
        tokenizer=tokenizer,
        grammar_active=True,
        compiled_grammar=FakeCompiledGrammar(),
        hardware_checker=checker,
    )

    assert checker.assignments == {}


def test_grammar_active_requires_compiled_grammar() -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel(tokenizer, GOOD_KERNELS["relu"])

    with pytest.raises(ValueError):
        generate_source(
            prompt="Write a Triton ReLU kernel.",
            model=model,
            tokenizer=tokenizer,
            grammar_active=True,
        )


def test_logits_processor_intersects_hardware_mask() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=FakeFullGrammar(),
        tokenizer=tokenizer,
        hardware_checker=checker,
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[0]], scores)

    assert scores[0][1] == 0.0
    assert scores[0][2] == -float("inf")
    assert scores[0][3] == 0.0
    assert processor.masked_token_rate() == 0.5


def test_logits_processor_relaxes_conflicting_hardware_mask() -> None:
    class ConflictingHardwareChecker:
        def allowed_token_ids(self, *args, **kwargs):
            return {3}

    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=FakeCompiledGrammar(),
        tokenizer=TokenMaskTokenizer(),
        hardware_checker=ConflictingHardwareChecker(),
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[0]], scores)

    assert scores[0] == [-float("inf"), 0.0, 0.0, -float("inf")]


def test_hardware_mask_allows_split_numeric_prefix_tokens() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    first_token_allowed = checker.allowed_token_ids(tokenizer, [[0]], 10)
    continuation_allowed = checker.allowed_token_ids(tokenizer, [[0, 6]], 10)

    assert 6 in first_token_allowed
    assert 7 in continuation_allowed


def test_hardware_mask_allows_documented_512_block_size() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    allowed = checker.allowed_token_ids(tokenizer, [[10]], 11)

    assert 9 in allowed


def test_hardware_mask_releases_after_completed_block_size_literal() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    allowed = checker.allowed_token_ids(tokenizer, [[10, 11]], 18)

    assert 12 in allowed
    assert 16 not in allowed


def test_hardware_mask_releases_after_completed_autotune_literal() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    allowed = checker.allowed_token_ids(tokenizer, [[13, 14]], 18)

    assert 15 in allowed
    assert 16 not in allowed
    assert 17 in allowed


def test_hardware_mask_allows_ambiguous_warp_digit_continuation() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    allowed = checker.allowed_token_ids(tokenizer, [[13, 6]], 20)

    assert 18 in allowed
    assert 15 in allowed


def test_hardware_mask_applies_to_arange_end_literal() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    checker.assignments["BLOCK_SIZE"] = 64

    allowed = checker.allowed_token_ids(tokenizer, [[19]], 20)

    assert 3 in allowed
    assert 4 not in allowed


def test_hardware_mask_allows_symbolic_arange_end() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    checker.assignments["BLOCK_SIZE"] = 64

    allowed = checker.allowed_token_ids(tokenizer, [[19]], 24)

    assert 21 in allowed
    assert 22 not in allowed


def test_hardware_mask_keeps_split_symbolic_arange_end_constrained() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    checker.assignments["BLOCK_SIZE"] = 64

    allowed = checker.allowed_token_ids(tokenizer, [[19, 24]], 27)

    assert 25 in allowed
    assert 26 not in allowed


def test_hardware_mask_allows_symbolic_matmul_arange_end() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    checker.assignments["BLOCK_M"] = 64

    allowed = checker.allowed_token_ids(tokenizer, [[19]], 24)

    assert 22 in allowed
    assert 21 not in allowed


def test_hardware_mask_allows_separator_before_assignment_integer() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()

    allowed = checker.allowed_token_ids(tokenizer, [[10]], 21)

    assert 20 in allowed


def test_hardware_mask_allows_separator_before_arange_integer() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    checker.assignments["BLOCK_SIZE"] = 64

    allowed = checker.allowed_token_ids(tokenizer, [[19]], 21)

    assert 20 in allowed


def test_hardware_no_mask_prefix_is_preserved() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker()
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=FakeFullGrammar(),
        tokenizer=tokenizer,
        hardware_checker=checker,
    )
    scores = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]

    processor([[1]], scores)

    assert all(value == 0.0 for value in scores[0])


def test_hardware_mask_ignores_prompt_prefix() -> None:
    tokenizer = MappingTokenizer(
        {
            0: "BLOCK_SIZE = ",
            1: "@",
            2: "64",
            3: "\n",
        }
    )
    checker = HardwareChecker()
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=FakeFullGrammar(),
        tokenizer=tokenizer,
        hardware_checker=checker,
        prompt_length=1,
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[0]], scores)

    assert scores[0] == [0.0, 0.0, 0.0, 0.0]


def test_logits_processor_uses_xgrammar_matcher_api(monkeypatch) -> None:
    fake_xgrammar = FakeXGrammarModule()
    monkeypatch.setitem(__import__("sys").modules, "xgrammar", fake_xgrammar)
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=object(),
        tokenizer=TokenMaskTokenizer(),
    )
    first_scores = [[0.0, 0.0, 0.0, 0.0]]
    second_scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[10, 11]], first_scores)
    processor([[10, 11, 3]], second_scores)

    assert first_scores[0] == [-float("inf"), 0.0, -float("inf"), 0.0]
    assert second_scores[0] == [-float("inf"), 0.0, -float("inf"), 0.0]
    assert fake_xgrammar.last_matcher.accepted_tokens == [3]


def test_logits_processor_accepts_reversed_xgrammar_bitmask_args(monkeypatch) -> None:
    fake_xgrammar = FakeReversedXGrammarModule()
    monkeypatch.setitem(sys.modules, "xgrammar", fake_xgrammar)
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=object(),
        tokenizer=TokenMaskTokenizer(),
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[10, 11]], scores)

    assert scores[0] == [-float("inf"), 0.0, -float("inf"), 0.0]


def test_logits_processor_uses_tokenizer_vocab_for_xgrammar_bitmask(monkeypatch) -> None:
    fake_xgrammar = FakeXGrammarModule()
    monkeypatch.setitem(sys.modules, "xgrammar", fake_xgrammar)
    tokenizer = TokenMaskTokenizer()
    tokenizer.get_vocab = lambda: {"a": 0, "b": 1, "c": 2}
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=object(),
        tokenizer=tokenizer,
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[10, 11]], scores)

    assert fake_xgrammar.allocate_calls[0] == (1, 3)
    assert scores[0] == [-float("inf"), 0.0, -float("inf"), -float("inf")]


def test_logits_processor_prefers_compiled_grammar_vocab_size(monkeypatch) -> None:
    fake_xgrammar = FakeXGrammarModule()
    monkeypatch.setitem(sys.modules, "xgrammar", fake_xgrammar)
    tokenizer = TokenMaskTokenizer()
    tokenizer.get_vocab = lambda: {"a": 0, "b": 1, "c": 2}
    compiled = types.SimpleNamespace(
        tokenizer_info=types.SimpleNamespace(vocab_size=4),
    )
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=compiled,
        tokenizer=tokenizer,
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[10, 11]], scores)

    assert fake_xgrammar.allocate_calls[0] == (1, 4)
    assert scores[0] == [-float("inf"), 0.0, -float("inf"), 0.0]


def test_logits_processor_applies_xgrammar_mutating_none_bitmask(monkeypatch) -> None:
    fake_xgrammar = FakeXGrammarModule(fill_return=None)
    monkeypatch.setitem(sys.modules, "xgrammar", fake_xgrammar)
    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=object(),
        tokenizer=TokenMaskTokenizer(),
    )
    scores = [[0.0, 0.0, 0.0, 0.0]]

    processor([[10, 11]], scores)

    assert scores[0] == [-float("inf"), 0.0, -float("inf"), 0.0]


def test_logits_processor_rejects_empty_allowed_mask() -> None:
    class EmptyGrammar:
        def allowed_token_ids(self, input_ids):
            return set()

    processor = TritonGrammarLogitsProcessor(
        compiled_grammar=EmptyGrammar(),
        tokenizer=TokenMaskTokenizer(),
    )

    with pytest.raises(RuntimeError, match="allowed zero tokens"):
        processor([[10, 11]], [[0.0, 0.0]])


def test_hardware_records_sampled_block_assignments_for_later_masks() -> None:
    tokenizer = TokenMaskTokenizer()
    checker = HardwareChecker(dtype_bytes=2)
    allowed = checker.allowed_token_ids(tokenizer, [[0, 4, 5]], 6)

    assert checker.assignments["BLOCK_M"] == 256
    assert 4 not in allowed
