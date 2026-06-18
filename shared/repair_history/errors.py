"""Typed local errors for repair-history prompt construction."""

from __future__ import annotations

from typing import ClassVar


class RepairHistoryError(ValueError):
    """Base class for fail-closed repair-history errors."""

    code: ClassVar[str] = "repair_history_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)

    @property
    def error_code(self) -> str:
        return self.code


class UnsupportedHistoryPolicyError(RepairHistoryError):
    code = "unsupported_history_policy"


class InvalidAttemptEvidenceError(RepairHistoryError):
    code = "invalid_attempt_evidence"


class MissingAnchorSourceError(RepairHistoryError):
    code = "missing_anchor_source"


class PromptBudgetExceededError(RepairHistoryError):
    code = "prompt_budget_exceeded"


class ForbiddenFeedbackContentError(RepairHistoryError):
    code = "forbidden_feedback_content"


class MixedHistoryPolicyError(RepairHistoryError):
    code = "mixed_history_policy"


class InvalidRepairHistoryConfigError(RepairHistoryError):
    code = "invalid_repair_history_config"


REPAIR_HISTORY_ERROR_CODES: frozenset[str] = frozenset(
    {
        UnsupportedHistoryPolicyError.code,
        InvalidAttemptEvidenceError.code,
        MissingAnchorSourceError.code,
        PromptBudgetExceededError.code,
        ForbiddenFeedbackContentError.code,
        MixedHistoryPolicyError.code,
        InvalidRepairHistoryConfigError.code,
    }
)
