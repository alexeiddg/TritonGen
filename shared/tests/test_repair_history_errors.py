"""Tests for typed repair-history errors."""

from __future__ import annotations

from shared.repair_history.errors import (
    ForbiddenFeedbackContentError,
    InvalidAttemptEvidenceError,
    MissingAnchorSourceError,
    MixedHistoryPolicyError,
    PromptBudgetExceededError,
    REPAIR_HISTORY_ERROR_CODES,
    RepairHistoryError,
    UnsupportedHistoryPolicyError,
)


def test_required_error_codes_are_exposed() -> None:
    assert {
        "unsupported_history_policy",
        "invalid_attempt_evidence",
        "missing_anchor_source",
        "prompt_budget_exceeded",
        "forbidden_feedback_content",
        "mixed_history_policy",
    }.issubset(REPAIR_HISTORY_ERROR_CODES)


def test_error_code_property_matches_class_code() -> None:
    error = MissingAnchorSourceError("missing source")

    assert isinstance(error, RepairHistoryError)
    assert error.error_code == "missing_anchor_source"
    assert str(error) == "missing source"


def test_error_subclasses_are_fail_closed_value_errors() -> None:
    for error_type in (
        UnsupportedHistoryPolicyError,
        InvalidAttemptEvidenceError,
        MissingAnchorSourceError,
        PromptBudgetExceededError,
        ForbiddenFeedbackContentError,
        MixedHistoryPolicyError,
    ):
        error = error_type()
        assert isinstance(error, ValueError)
        assert error.error_code in REPAIR_HISTORY_ERROR_CODES
