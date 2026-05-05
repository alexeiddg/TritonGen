"""Hardware checker tests for Phase 3."""

from __future__ import annotations

from cluster1.constraints.hardware_checker import (
    HardwareChecker,
    _pending_arange_start,
    _pending_arange_start_fragment,
    _ARANGE_START_RE,
    _ARANGE_RE,
)


def test_power_of_two_enforcement() -> None:
    checker = HardwareChecker()

    assert checker.validate_assignment("BLOCK_M", 64)
    assert not checker.validate_assignment("BLOCK_K", 37)
    assert checker.validate_assignment("BLOCK_SIZE", 512)


def test_smem_budget() -> None:
    checker = HardwareChecker(dtype_bytes=2)

    assert checker.validate_assignment("BLOCK_M", 128)
    assert not checker.validate_assignment("BLOCK_N", 256)

    checker.reset()
    assert checker.validate_assignment("BLOCK_M", 64)
    assert checker.validate_assignment("BLOCK_N", 64)


def test_warp_count() -> None:
    checker = HardwareChecker()

    assert not checker.validate_assignment("num_warps", 3)
    assert checker.validate_assignment("num_warps", 4)


def test_stage_count() -> None:
    checker = HardwareChecker()

    assert not checker.validate_assignment("num_stages", 6)
    assert checker.validate_assignment("num_stages", 3)


def test_arange_consistency() -> None:
    checker = HardwareChecker()

    assert checker.validate_assignment("BLOCK_SIZE", 64)
    assert checker.validate_arange(0, 64)
    assert not checker.validate_arange(0, 128)


def test_dot_shape_compatibility() -> None:
    checker = HardwareChecker()

    assert checker.validate_dot_shapes((64, 32), (32, 64))
    assert not checker.validate_dot_shapes((64, 32), (64, 32))


def test_reset_clears_state() -> None:
    checker = HardwareChecker(dtype_bytes=2)

    assert checker.validate_assignment("BLOCK_M", 256)
    assert 256 not in checker.allowed_values("BLOCK_N")
    checker.reset()
    assert 256 in checker.allowed_values("BLOCK_N")

def test_arange_start_detection() -> None:
    """_pending_arange_start fires during start-argument phase, not end-argument phase."""
    # Start-argument phase: `tl.arange(` with no comma yet.
    assert _pending_arange_start("tl.arange(")
    assert _pending_arange_start("tl.arange(0")  # partial '0' digit emitted
    assert _pending_arange_start("tl.arange( ")

    # End-argument phase: comma already present — must NOT fire.
    assert not _pending_arange_start("tl.arange(0, ")
    assert not _pending_arange_start("tl.arange(0, BLOCK_SIZE")

    # Unrelated prefix — must not fire.
    assert not _pending_arange_start("BLOCK_SIZE = 64")


def test_arange_start_fragment() -> None:
    """_pending_arange_start_fragment returns whatever digit(s) are already emitted."""
    assert _pending_arange_start_fragment("tl.arange(") == ""
    assert _pending_arange_start_fragment("tl.arange(0") == "0"
    assert _pending_arange_start_fragment("tl.arange(1") == "1"  # invalid, but parseable


class _FakeTokenizer:
    """Minimal tokenizer that maps single characters to their ordinal IDs."""

    vocab: dict[int, str]

    def __init__(self) -> None:
        # Build a tiny vocab: digits 0-9 and a few letters / punctuation.
        chars = "0123456789abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ_,()."
        self.vocab = {i: ch for i, ch in enumerate(chars)}

    def decode(self, ids, **_kwargs) -> str:
        return "".join(self.vocab.get(i, "") for i in ids)


def test_allowed_token_ids_arange_start_constrained() -> None:
    """allowed_token_ids must restrict the start argument of tl.arange to 0 only.

    This is the generation-time regression test for the gap identified in P2:
    previously _ARANGE_RE (which required `tl.arange(0,` already present) was
    the only guard, so the start argument was never masked.
    """
    tok = _FakeTokenizer()
    vocab_size = len(tok.vocab)
    checker = HardwareChecker()

    # Simulate the generation state right after `tl.arange(` is emitted.
    # The tokenizer maps char→ord; build a fake input_ids list that decodes to
    # "tl.arange(" using the FakeTokenizer vocab.
    prefix_text = "tl.arange("
    # Encode prefix manually: find each char's ID in tok.vocab.
    reverse_vocab = {ch: i for i, ch in tok.vocab.items()}
    input_ids = [reverse_vocab[ch] for ch in prefix_text if ch in reverse_vocab]

    allowed = checker.allowed_token_ids(tok, input_ids, vocab_size, prompt_length=0)

    assert allowed is not None, "Checker must return a non-None mask during start-arg phase"

    # Only the token that decodes to '0' should be allowed.
    zero_id = reverse_vocab["0"]
    assert zero_id in allowed, "Token '0' must be allowed as arange start"

    # Any non-zero digit token must NOT be allowed.
    for digit in "123456789":
        digit_id = reverse_vocab[digit]
        assert digit_id not in allowed, (
            f"Token '{digit}' must NOT be allowed as arange start — "
            "only 0 is a valid tl.arange start"
        )
