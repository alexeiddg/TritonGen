"""Compact deterministic trace summaries for Cluster 2 repair attempts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from typing import Any

from cluster2.constants import NEW_GENERATION_CONDITIONS, normalize_cluster2_condition
from shared.eval.failure_taxonomy import FAILURE_CODES

from cluster2.feedback.prompts import (
    GENERIC_EVAL_FAILURE_FEEDBACK,
    _result_level2_success_flag,
    build_feedback_text,
    feedback_allowed_for_failure_code,
    sanitize_public_feedback_text,
    validate_no_forbidden_feedback_terms,
)


@dataclass(frozen=True)
class TraceSummary:
    """One compact public attempt summary for generated repair conditions."""

    attempt_index: int
    failure_code: str | None
    public_failure_summary: str | None
    functional_success: bool | None
    repair_set_success: bool | None
    eval_set_success: bool | None
    source_hash: str | None = None

    def __post_init__(self) -> None:
        _require_non_negative_int(self.attempt_index, "attempt_index")
        if self.failure_code is not None and self.failure_code not in FAILURE_CODES:
            raise ValueError(f"unsupported failure_code {self.failure_code!r}")
        if self.public_failure_summary is not None:
            validate_no_forbidden_feedback_terms(self.public_failure_summary)
        if self.source_hash is not None:
            _validate_sha256(self.source_hash, "source_hash")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TraceSummary":
        if not isinstance(payload, dict):
            raise TypeError("TraceSummary.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        return cls(**payload)


def trace_required_for_condition(condition: str) -> bool:
    """Return whether a condition can have generated repair trace summaries."""

    return normalize_cluster2_condition(condition) in NEW_GENERATION_CONDITIONS


def build_trace_summary(
    *,
    condition: str = "C",
    attempt_index: int,
    failure_code: str | None,
    public_failure_summary: str | None = None,
    functional_success: bool | None,
    repair_set_success: bool | None,
    eval_set_success: bool | None,
    source_hash: str | None = None,
    source: str | None = None,
) -> TraceSummary | None:
    """Build one compact summary without including full source text."""

    if not trace_required_for_condition(condition):
        return None
    resolved_hash = source_hash or _source_hash(source)
    summary = _summary_text(
        failure_code=failure_code,
        public_failure_summary=public_failure_summary,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
    )
    return TraceSummary(
        attempt_index=attempt_index,
        failure_code=failure_code,
        public_failure_summary=summary,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        source_hash=resolved_hash,
    )


def build_trace_summary_from_result(
    result: object,
    *,
    condition: str | None = None,
    source_hash: str | None = None,
    source: str | None = None,
) -> TraceSummary | None:
    """Build a trace summary from an object exposing C2 correctness fields."""

    identity = getattr(result, "identity", None)
    resolved_condition = (
        condition
        or getattr(result, "condition", None)
        or getattr(identity, "condition", None)
        or "C"
    )
    if not trace_required_for_condition(str(resolved_condition)):
        return None

    attempt_index = getattr(result, "attempt_index", None)
    if attempt_index is None:
        attempt_index = getattr(identity, "attempt_index", None)
    if attempt_index is None:
        attempt_index = getattr(result, "repair_iteration", None)
    if attempt_index is None:
        raise ValueError("result must expose attempt_index")

    return build_trace_summary(
        condition=str(resolved_condition),
        attempt_index=attempt_index,
        failure_code=getattr(result, "failure_code", None),
        public_failure_summary=getattr(result, "correctness_error", None),
        functional_success=getattr(result, "functional_success", None),
        repair_set_success=_result_level2_success_flag(result, "repair_set_success"),
        eval_set_success=_result_level2_success_flag(result, "eval_set_success"),
        source_hash=source_hash if source_hash is not None else _result_source_hash(result),
        source=source,
    )


def _summary_text(
    *,
    failure_code: str | None,
    public_failure_summary: str | None,
    functional_success: bool | None,
    repair_set_success: bool | None,
    eval_set_success: bool | None,
) -> str | None:
    if functional_success is True:
        return "Candidate passed Level 2."
    if repair_set_success is True and eval_set_success is False:
        return GENERIC_EVAL_FAILURE_FEEDBACK
    if public_failure_summary:
        return sanitize_public_feedback_text(public_failure_summary)
    if failure_code is None:
        return "Validation failed."
    if not feedback_allowed_for_failure_code(failure_code):
        return "Validation failed."
    feedback = build_feedback_text(
        condition="C",
        failure_code=failure_code,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
    )
    return feedback or "Validation failed."


def _source_hash(source: str | None) -> str | None:
    if source is None:
        return None
    if not isinstance(source, str):
        raise TypeError("source must be a string when provided")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _result_source_hash(result: object) -> str | None:
    value = getattr(result, "source_hash", None) or getattr(result, "source_sha256", None)
    if not value:
        return None
    if not isinstance(value, str):
        raise TypeError("source_hash must be a string when present")
    return value


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _validate_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc
