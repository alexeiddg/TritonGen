"""Tests for public repair-history evidence validation."""

from __future__ import annotations

import pytest

from shared.repair_history.errors import (
    ForbiddenFeedbackContentError,
    InvalidAttemptEvidenceError,
)
from shared.repair_history.evidence import (
    RepairAttemptEvidence,
    RepairSourceRecord,
    sha256_text,
    validate_attempt_history,
    validate_source_records,
)


SOURCE = "def kernel(x):\n    return x\n"
PROMPT_HASH = "a" * 64


def test_source_record_hash_must_match_source_text() -> None:
    record = RepairSourceRecord(0, SOURCE)

    assert record.source_hash == sha256_text(SOURCE)
    with pytest.raises(InvalidAttemptEvidenceError):
        RepairSourceRecord(0, SOURCE, source_hash="b" * 64)


def test_attempt_evidence_rejects_malformed_indexes_hashes_and_failure_codes() -> None:
    with pytest.raises(InvalidAttemptEvidenceError):
        _attempt(attempt_index=True)  # type: ignore[arg-type]
    with pytest.raises(InvalidAttemptEvidenceError):
        _attempt(source_hash="not-a-hash")
    with pytest.raises(InvalidAttemptEvidenceError):
        _attempt(failure_code="F9_UNKNOWN")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", (["F2_NUMERIC_LARGE"], {"code": "F2_NUMERIC_LARGE"}))
def test_attempt_evidence_rejects_non_string_failure_codes(value: object) -> None:
    with pytest.raises(InvalidAttemptEvidenceError) as exc_info:
        _attempt(failure_code=value)

    assert exc_info.value.error_code == "invalid_attempt_evidence"


@pytest.mark.parametrize("field_name", ("max_abs_diff", "max_rel_diff"))
@pytest.mark.parametrize("value", (float("nan"), float("inf"), -float("inf")))
def test_attempt_evidence_rejects_non_finite_numeric_diffs(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(InvalidAttemptEvidenceError) as exc_info:
        _attempt(**{field_name: value})

    assert exc_info.value.error_code == "invalid_attempt_evidence"


def test_attempt_history_requires_contiguous_zero_based_indexes() -> None:
    attempts = (
        _attempt(attempt_index=0),
        _attempt(attempt_index=2, generation_seed=2),
    )

    with pytest.raises(InvalidAttemptEvidenceError, match="contiguous"):
        validate_attempt_history(attempts, loop_kind="C")


def test_attempt_history_rejects_success_with_failure_code() -> None:
    with pytest.raises(InvalidAttemptEvidenceError, match="failure_code=None") as exc_info:
        validate_attempt_history([_attempt(functional_success=True)], loop_kind="C")

    assert exc_info.value.error_code == "invalid_attempt_evidence"


def test_f2_history_requires_level_two_and_public_summary() -> None:
    with pytest.raises(InvalidAttemptEvidenceError, match="level_reached=2"):
        _attempt(level_reached=1)
    with pytest.raises(InvalidAttemptEvidenceError, match="public_failure_summary"):
        _attempt(public_failure_summary=None)


def test_f0_history_requires_level_zero_or_unknown_and_public_summary() -> None:
    with pytest.raises(InvalidAttemptEvidenceError, match="level_reached=0"):
        validate_attempt_history([_f0_attempt(level_reached=1)], loop_kind="C")
    with pytest.raises(InvalidAttemptEvidenceError, match="public_failure_summary"):
        validate_attempt_history([_f0_attempt(public_failure_summary=None)], loop_kind="C")

    assert validate_attempt_history([_f0_attempt(level_reached=0)], loop_kind="C")
    assert validate_attempt_history([_f0_attempt(level_reached=None)], loop_kind="C")


def test_f3_history_must_end_active_loop() -> None:
    attempts = (
        _f3_attempt(attempt_index=0),
        _attempt(attempt_index=1, generation_seed=2),
    )

    with pytest.raises(InvalidAttemptEvidenceError, match="end the active loop"):
        validate_attempt_history(attempts, loop_kind="C")

    assert validate_attempt_history([_f3_attempt(attempt_index=0)], loop_kind="C")


def test_p_f1_compile_history_requires_public_compile_evidence() -> None:
    attempt = RepairAttemptEvidence(
        attempt_index=0,
        generation_seed=0,
        failure_code="F1_COMPILE",
        level_reached=1,
        compile_success=False,
        functional_success=False,
        repair_set_success=None,
        eval_set_success=None,
        public_failure_summary="Compilation failed before validation.",
        source_hash=sha256_text(SOURCE),
        prompt_hash=PROMPT_HASH,
    )

    with pytest.raises(InvalidAttemptEvidenceError, match="compile evidence"):
        validate_attempt_history([attempt], loop_kind="P")


def test_prompt_visible_evidence_rejects_private_and_performance_signals() -> None:
    with pytest.raises(ForbiddenFeedbackContentError):
        _attempt(public_failure_summary="hidden eval_shape_set had a speedup issue")


def test_repeated_source_hashes_remain_separate_source_records() -> None:
    first = RepairSourceRecord(0, SOURCE)
    second = RepairSourceRecord(1, SOURCE)

    records = validate_source_records([first, second])

    assert records[0].source_hash == records[1].source_hash
    assert records[0].attempt_index == 0
    assert records[1].attempt_index == 1


def _attempt(**overrides: object) -> RepairAttemptEvidence:
    values = {
        "attempt_index": 0,
        "generation_seed": 1,
        "failure_code": "F2_NUMERIC_LARGE",
        "level_reached": 2,
        "compile_success": True,
        "functional_success": False,
        "repair_set_success": False,
        "eval_set_success": None,
        "public_failure_summary": "Repair shape failed: max_abs_diff=1.0",
        "source_hash": sha256_text(SOURCE),
        "prompt_hash": PROMPT_HASH,
        "repair_shapes_passed": 1,
        "num_repair_shapes": 4,
        "max_abs_diff": 1.0,
        "max_rel_diff": 0.5,
    }
    values.update(overrides)
    return RepairAttemptEvidence(**values)  # type: ignore[arg-type]


def _f0_attempt(**overrides: object) -> RepairAttemptEvidence:
    values = {
        "attempt_index": 0,
        "generation_seed": 1,
        "failure_code": "F0_PARSE",
        "level_reached": 0,
        "compile_success": False,
        "functional_success": False,
        "repair_set_success": None,
        "eval_set_success": None,
        "public_failure_summary": "Parse failed before repairable evidence.",
        "source_hash": sha256_text(SOURCE),
        "prompt_hash": PROMPT_HASH,
    }
    values.update(overrides)
    return RepairAttemptEvidence(**values)  # type: ignore[arg-type]


def _f3_attempt(**overrides: object) -> RepairAttemptEvidence:
    values = {
        "attempt_index": 0,
        "generation_seed": 1,
        "failure_code": "F3_TIMEOUT",
        "level_reached": 3,
        "compile_success": True,
        "functional_success": False,
        "repair_set_success": None,
        "eval_set_success": None,
        "public_failure_summary": "Evaluation timed out.",
        "source_hash": sha256_text(SOURCE),
        "prompt_hash": PROMPT_HASH,
    }
    values.update(overrides)
    return RepairAttemptEvidence(**values)  # type: ignore[arg-type]
