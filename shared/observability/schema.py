"""Strict schemas for TritonGen observability sidecars."""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from decimal import Decimal
from datetime import datetime
from pathlib import PurePath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.observability.redaction import (
    AttributeValue,
    reject_forbidden_observability_payload,
    sanitize_attributes,
    sanitize_error_summary,
)

SCHEMA_VERSION = "tritongen.observability.v1"

Severity = Literal["debug", "info", "warning", "error", "critical"]
EventType = Literal[
    "run_started",
    "run_completed",
    "run_failed",
    "run_aborted",
    "resume_validated",
    "stage_started",
    "stage_completed",
    "stage_failed",
    "row_started",
    "row_completed",
    "row_skipped",
    "remote_call_started",
    "remote_call_completed",
    "remote_call_failed",
    "summary_written",
    "partial_artifact_detected",
    "cost_estimate_written",
]
StageName = Literal[
    "preflight",
    "generation",
    "compile_eval",
    "correctness_eval",
    "p_repair",
    "c_repair",
    "row_append",
    "hash_validation",
    "summary",
    "analysis",
    "billing_reconciliation",
]
Status = Literal[
    "started",
    "succeeded",
    "failed",
    "skipped",
    "unavailable",
    "blocked",
    "partial",
    "not_applicable",
]
DurationSource = Literal[
    "local_monotonic",
    "remote_monotonic",
    "caller_observed_remote_call",
    "unavailable",
    "not_applicable",
]
TokenCountSource = Literal[
    "generation_sequence_length_delta",
    "existing_generation_result",
    "existing_remote_payload",
    "unavailable",
    "not_applicable",
]
TokenCountStatus = Literal["available", "partial", "unavailable", "not_applicable"]
ModalContextSource = Literal[
    "shared_modal_runtime_helper",
    "modal_environment_allowlist",
    "runner_config",
    "unavailable",
]
CostEstimateStatus = Literal["not_implemented", "not_requested", "unavailable", "estimated"]
CostEstimateMethod = Literal[
    "supplied",
    "static_table",
    "test_fixture",
    "unavailable",
    "not_applicable",
]
ActualBillingStatus = Literal[
    "not_implemented",
    "not_requested",
    "unavailable",
    "pending",
    "reconciled",
    "ambiguous",
    "failed",
]
CompletenessStatus = Literal["complete", "partial", "unavailable", "failed"]
HashSummaryStatus = Literal["not_written", "written", "unavailable", "failed"]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_GIT_RE = re.compile(r"^[0-9a-f]{7,64}$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
        strict=True,
    )


class ObservabilityRunIdentity(_StrictModel):
    experiment_id: str
    run_id: str

    @field_validator("experiment_id", "run_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class ObservabilityArtifactIdentity(_StrictModel):
    result_path: str
    observability_event_path: str | None = None
    observability_summary_path: str | None = None
    git_commit: str | None = None

    @field_validator("result_path", "observability_event_path", "observability_summary_path")
    @classmethod
    def _path_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty(value)

    @field_validator("git_commit")
    @classmethod
    def _git_commit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.lower()
        if not _GIT_RE.fullmatch(value):
            raise ValueError("git_commit must be a hex commit prefix or full digest")
        return value


class ObservabilityRowIdentity(_StrictModel):
    cluster: str | None = None
    condition: str | None = None
    kernel_class: str | None = None
    kernel_name: str | None = None
    dtype: str | None = None
    base_seed: int | None = Field(default=None, ge=0)
    generation_seed: int | None = Field(default=None, ge=0)
    attempt_index: int | None = Field(default=None, ge=0)
    terminal_attempt_index: int | None = Field(default=None, ge=0)
    source_hash: str | None = None
    row_sha256: str | None = None

    @field_validator("cluster", "condition", "kernel_class", "kernel_name", "dtype")
    @classmethod
    def _optional_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty(value)

    @field_validator("source_hash", "row_sha256")
    @classmethod
    def _sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value)


class ObservabilityAttemptIdentity(_StrictModel):
    attempt_index: int | None = Field(default=None, ge=0)
    terminal_attempt_index: int | None = Field(default=None, ge=0)
    repair_attempt_index: int | None = Field(default=None, ge=0)
    condition: str | None = None

    @field_validator("condition")
    @classmethod
    def _condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty(value)


class ObservabilityTokenCounts(_StrictModel):
    token_counts_available: bool
    prompt_tokens: int | None = Field(default=None, ge=0)
    generated_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    token_count_source: TokenCountSource
    token_count_status: TokenCountStatus

    @model_validator(mode="after")
    def _validate_totals(self) -> "ObservabilityTokenCounts":
        count_values = (
            self.prompt_tokens,
            self.generated_tokens,
            self.total_tokens,
        )
        if (
            self.prompt_tokens is not None
            and self.generated_tokens is not None
            and self.total_tokens is not None
            and self.prompt_tokens + self.generated_tokens != self.total_tokens
        ):
            raise ValueError("total_tokens must equal prompt_tokens + generated_tokens")
        if self.token_counts_available:
            if self.token_count_source in {"unavailable", "not_applicable"}:
                raise ValueError("available token counts require an available source")
            if self.token_count_status not in {"available", "partial"}:
                raise ValueError("available token counts require available or partial status")
            if not any(value is not None for value in count_values):
                raise ValueError("available token counts require at least one count")
            if self.token_count_status == "available" and any(
                value is None for value in count_values
            ):
                raise ValueError("available token count status requires all counts")
            return self

        if self.token_count_source not in {
            "unavailable",
            "not_applicable",
        }:
            raise ValueError("unavailable token counts require an unavailable source")
        if self.token_count_status not in {"unavailable", "not_applicable"}:
            raise ValueError("unavailable token counts require unavailable status")
        if any(value is not None for value in count_values):
            raise ValueError("unavailable token counts must not include counts")
        return self


class ObservabilityModalContext(_StrictModel):
    modal_context_available: bool
    is_remote: bool | None = None
    function_call_id: str | None = None
    input_id: str | None = None
    task_id: str | None = None
    image_id: str | None = None
    region: str | None = None
    cloud_provider: str | None = None
    environment_name: str | None = None
    app_name: str | None = None
    gpu_type: str | None = None
    gpu_count: int | None = Field(default=None, ge=0)
    cpu_cores: float | None = Field(default=None, ge=0)
    memory_gib: float | None = Field(default=None, ge=0)
    timeout_s: int | None = Field(default=None, ge=0)
    container_started_at_utc: str | None = None
    modal_context_source: ModalContextSource

    @field_validator(
        "function_call_id",
        "input_id",
        "task_id",
        "image_id",
        "region",
        "cloud_provider",
        "environment_name",
        "app_name",
        "gpu_type",
    )
    @classmethod
    def _optional_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty(value)

    @field_validator("container_started_at_utc")
    @classmethod
    def _utc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_utc(value)

    @model_validator(mode="after")
    def _availability_contract(self) -> "ObservabilityModalContext":
        present_fields = (
            self.function_call_id,
            self.input_id,
            self.task_id,
            self.image_id,
            self.region,
            self.cloud_provider,
            self.environment_name,
            self.app_name,
            self.gpu_type,
            self.gpu_count,
            self.cpu_cores,
            self.memory_gib,
            self.timeout_s,
            self.container_started_at_utc,
        )
        if self.modal_context_available:
            if self.modal_context_source == "unavailable":
                raise ValueError("available Modal context requires a non-unavailable source")
            if not any(value is not None for value in present_fields):
                raise ValueError(
                    "available Modal context requires at least one runtime identity "
                    "or resource field"
                )
            reject_forbidden_observability_payload(self.model_dump(mode="json"))
            return self

        if self.modal_context_source != "unavailable":
            raise ValueError("unavailable Modal context requires source unavailable")
        if self.is_remote:
            raise ValueError("unavailable Modal context cannot be remote")
        if any(value is not None for value in present_fields):
            raise ValueError("unavailable Modal context must not include runtime fields")
        reject_forbidden_observability_payload(self.model_dump(mode="json"))
        return self


_FORBIDDEN_COST_LABEL_PATTERNS = (
    "actual_billing",
    "actual_cost",
    "account_charge",
    "billing",
    "billing_account",
    "billing_api_response",
    "billing_data",
    "billing_report",
    "benchmark_cost_conclusion",
    "cloud_invoice_dump",
    "cost_per_pass",
    "cost_per_success",
    "credit_card",
    "economic_lift",
    "external_pricing_fetch",
    "invoice",
    "modal_bill",
    "modal_billing",
    "pass_at_k_cost",
    "payment_method",
    "pricing_api_response",
    "provider_bill",
    "provider_billing",
    "roi",
)


def _normalize_cost_label(value: str) -> str:
    acronym_split = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", value.strip())
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", acronym_split)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _reject_forbidden_cost_label(value: str) -> None:
    normalized = _normalize_cost_label(value)
    compact = normalized.replace("_", "")
    for pattern in _FORBIDDEN_COST_LABEL_PATTERNS:
        if pattern in normalized or pattern.replace("_", "") in compact:
            raise ValueError(
                "pricing source labels must not name billing, invoice, API "
                "response, external pricing fetch, or economic claim sources"
            )


class ObservabilityCostEstimate(_StrictModel):
    cost_estimate_available: bool
    estimated_input_cost: float | None = Field(default=None, ge=0)
    estimated_output_cost: float | None = Field(default=None, ge=0)
    estimated_total_cost: float | None = Field(default=None, ge=0)
    currency: Literal["USD"] | None = None
    pricing_source: str | None = Field(default=None, max_length=80)
    pricing_source_version: str | None = Field(default=None, max_length=80)
    cost_estimate_status: CostEstimateStatus
    cost_estimate_method: CostEstimateMethod

    @field_validator("pricing_source", "pricing_source_version")
    @classmethod
    def _optional_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = _require_non_empty(value)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,79}", value):
            raise ValueError("pricing source labels must be bounded safe identifiers")
        _reject_forbidden_cost_label(value)
        return value

    @field_validator(
        "estimated_input_cost",
        "estimated_output_cost",
        "estimated_total_cost",
    )
    @classmethod
    def _decimal_safe_cost(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("cost values must be finite")
        decimal = Decimal(str(value))
        if decimal.as_tuple().exponent < -12:
            raise ValueError("cost values must be decimal-safe to 12 places")
        return value

    @model_validator(mode="after")
    def _cost_contract(self) -> "ObservabilityCostEstimate":
        cost_values = (
            self.estimated_input_cost,
            self.estimated_output_cost,
            self.estimated_total_cost,
        )
        if self.cost_estimate_available:
            if self.cost_estimate_status != "estimated":
                raise ValueError("available cost estimates require estimated status")
            if self.cost_estimate_method not in {
                "supplied",
                "static_table",
                "test_fixture",
            }:
                raise ValueError("available cost estimates require an estimate method")
            if self.currency != "USD":
                raise ValueError("available cost estimates require USD currency")
            if self.pricing_source is None or self.pricing_source_version is None:
                raise ValueError("available cost estimates require pricing source metadata")
            if any(value is None for value in cost_values):
                raise ValueError("available cost estimates require all cost values")
            assert self.estimated_input_cost is not None
            assert self.estimated_output_cost is not None
            assert self.estimated_total_cost is not None
            expected_total = self.estimated_input_cost + self.estimated_output_cost
            if not math.isclose(
                self.estimated_total_cost,
                expected_total,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise ValueError(
                    "estimated_total_cost must equal estimated_input_cost + "
                    "estimated_output_cost"
                )
            reject_forbidden_observability_payload(self.model_dump(mode="json"))
            return self

        if self.cost_estimate_status == "estimated":
            raise ValueError("unavailable cost estimates cannot use estimated status")
        if any(value is not None for value in cost_values):
            raise ValueError("unavailable cost estimates must not include cost values")
        if self.currency is not None:
            raise ValueError("unavailable cost estimates must not include currency")
        if self.pricing_source is not None or self.pricing_source_version is not None:
            raise ValueError(
                "unavailable cost estimates must not include pricing source metadata"
            )
        if self.cost_estimate_method not in {"unavailable", "not_applicable"}:
            raise ValueError("unavailable cost estimates require unavailable method")
        reject_forbidden_observability_payload(self.model_dump(mode="json"))
        return self


class ObservabilityErrorSummary(_StrictModel):
    public_failure_code: str | None = None
    bounded_public_error_class: str | None = None
    error_excerpt_sha256: str | None = None
    message: str | None = Field(default=None, max_length=512)

    @field_validator("public_failure_code", "bounded_public_error_class", "message")
    @classmethod
    def _optional_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty(value)

    @field_validator("error_excerpt_sha256")
    @classmethod
    def _hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value)

    @model_validator(mode="after")
    def _validate_privacy(self) -> "ObservabilityErrorSummary":
        sanitize_error_summary(self.model_dump(mode="json"))
        return self


class ObservabilityEvent(_StrictModel):
    schema_version: Literal["tritongen.observability.v1"] = SCHEMA_VERSION
    event_id: str
    event_sequence: int = Field(ge=0)
    event_type: EventType
    severity: Severity
    timestamp_utc: str
    timestamp_unix_ns: int = Field(ge=0)
    monotonic_ns: int = Field(ge=0)
    clock_scope_id: str
    experiment_id: str
    run_id: str
    artifact: ObservabilityArtifactIdentity
    row_identity: ObservabilityRowIdentity
    stage: StageName | None
    attempt: ObservabilityAttemptIdentity
    status: Status
    duration_ns: int | None = Field(default=None, ge=0)
    duration_source: DurationSource
    start_monotonic_ns: int | None = Field(default=None, ge=0)
    end_monotonic_ns: int | None = Field(default=None, ge=0)
    token_counts: ObservabilityTokenCounts | None
    modal_context: ObservabilityModalContext | None
    cost_estimate: ObservabilityCostEstimate | None
    error_summary: ObservabilityErrorSummary | None
    attributes: dict[str, AttributeValue]

    @field_validator("event_id")
    @classmethod
    def _uuid(cls, value: str) -> str:
        try:
            parsed = uuid.UUID(value)
        except ValueError as exc:
            raise ValueError("event_id must be an RFC 4122 UUID string") from exc
        return str(parsed)

    @field_validator("timestamp_utc")
    @classmethod
    def _timestamp_utc(cls, value: str) -> str:
        return _validate_utc(value)

    @field_validator("clock_scope_id", "experiment_id", "run_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("attributes")
    @classmethod
    def _attributes(cls, value: dict[str, Any]) -> dict[str, AttributeValue]:
        return sanitize_attributes(value)

    @model_validator(mode="after")
    def _duration_contract(self) -> "ObservabilityEvent":
        if self.duration_source in {"unavailable", "not_applicable"}:
            if any(
                value is not None
                for value in (
                    self.duration_ns,
                    self.start_monotonic_ns,
                    self.end_monotonic_ns,
                )
            ):
                raise ValueError(
                    "unavailable durations must not include duration or monotonic bounds"
                )
            return self._privacy_checked()

        if self.duration_ns is None:
            raise ValueError("measured durations require duration_ns")
        if self.start_monotonic_ns is None or self.end_monotonic_ns is None:
            raise ValueError("measured durations require start and end monotonic fields")
        if self.end_monotonic_ns < self.start_monotonic_ns:
            raise ValueError("end_monotonic_ns must be >= start_monotonic_ns")
        if self.duration_ns != self.end_monotonic_ns - self.start_monotonic_ns:
            raise ValueError("duration_ns must equal end_monotonic_ns - start_monotonic_ns")
        return self._privacy_checked()

    def _privacy_checked(self) -> "ObservabilityEvent":
        reject_forbidden_observability_payload(self.model_dump(mode="json"))
        return self


class ObservabilitySummary(_StrictModel):
    schema_version: Literal["tritongen.observability.v1"] = SCHEMA_VERSION
    experiment_id: str
    run_id: str
    result_path: str
    observability_event_path: str
    observability_summary_path: str
    generated_at_utc: str
    git_commit: str
    branch: str
    workspace: str
    row_counts: dict[str, int]
    event_counts: dict[str, int]
    stage_durations_ns: dict[str, int]
    token_totals: dict[str, Any]
    modal_context_summary: dict[str, Any]
    estimated_cost_summary: dict[str, Any]
    actual_billing_status: ActualBillingStatus
    completeness_status: CompletenessStatus
    caveats: list[str]
    source_event_sha256: str
    summary_sha256: str | None

    @field_validator(
        "experiment_id",
        "run_id",
        "result_path",
        "observability_event_path",
        "observability_summary_path",
        "git_commit",
        "branch",
        "workspace",
    )
    @classmethod
    def _non_empty(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("generated_at_utc")
    @classmethod
    def _generated_at(cls, value: str) -> str:
        return _validate_utc(value)

    @field_validator("git_commit")
    @classmethod
    def _git_commit(cls, value: str) -> str:
        value = value.lower()
        if not _GIT_RE.fullmatch(value):
            raise ValueError("git_commit must be a hex commit prefix or full digest")
        return value

    @field_validator("workspace")
    @classmethod
    def _workspace(cls, value: str) -> str:
        if PurePath(value).is_absolute():
            raise ValueError("workspace must be a repo-relative label")
        return value

    @field_validator("row_counts", "event_counts", "stage_durations_ns")
    @classmethod
    def _nonnegative_counts(cls, value: dict[str, int]) -> dict[str, int]:
        for key, count in value.items():
            _require_non_empty(key)
            if count < 0:
                raise ValueError("summary counts must be nonnegative")
        return value

    @field_validator("source_event_sha256", "summary_sha256")
    @classmethod
    def _hashes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value)

    @model_validator(mode="after")
    def _validate_privacy(self) -> "ObservabilitySummary":
        reject_forbidden_observability_payload(self.model_dump(mode="json"))
        return self


class ObservabilityHashSidecar(_StrictModel):
    schema_version: Literal["tritongen.observability.v1"] = SCHEMA_VERSION
    experiment_id: str
    run_id: str
    result_path: str
    observability_event_path: str
    observability_summary_path: str
    event_jsonl_sha256: str
    summary_json_sha256: str | None
    summary_status: HashSummaryStatus
    event_count: int = Field(ge=0)
    generated_at_utc: str
    hash_algorithm: Literal["sha256"] = "sha256"

    @field_validator(
        "experiment_id",
        "run_id",
        "result_path",
        "observability_event_path",
        "observability_summary_path",
    )
    @classmethod
    def _non_empty(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("event_jsonl_sha256", "summary_json_sha256")
    @classmethod
    def _hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_sha256(value)

    @field_validator("generated_at_utc")
    @classmethod
    def _utc(cls, value: str) -> str:
        return _validate_utc(value)

    @model_validator(mode="after")
    def _summary_status_contract(self) -> "ObservabilityHashSidecar":
        if self.summary_status == "written" and self.summary_json_sha256 is None:
            raise ValueError("written summary status requires summary_json_sha256")
        if self.summary_status == "not_written" and self.summary_json_sha256 is not None:
            raise ValueError("not_written summary status requires null summary hash")
        return self


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    """Return deterministic JSON bytes with one trailing newline."""

    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_event_json(event: ObservabilityEvent) -> str:
    """Return one canonical event JSON object without its JSONL newline."""

    return canonical_json_bytes(event).decode("utf-8").removesuffix("\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file_bytes(data: bytes) -> str:
    return sha256_bytes(data)


def row_sha256_from_canonical_json(row_json: str) -> str:
    """Hash the exact canonical result-row JSON string before JSONL newline."""

    if row_json.endswith("\n"):
        raise ValueError("row_json must not include the trailing JSONL newline")
    return sha256_bytes(row_json.encode("utf-8"))


def summary_with_digest(summary: ObservabilitySummary) -> ObservabilitySummary:
    """Return a summary whose self-reference hash follows the spec algorithm."""

    without_digest = summary.model_copy(update={"summary_sha256": None})
    digest = sha256_bytes(canonical_json_bytes(without_digest))
    final = without_digest.model_copy(update={"summary_sha256": digest})
    reloaded = ObservabilitySummary.model_validate_json(canonical_json_bytes(final))
    check = reloaded.model_copy(update={"summary_sha256": None})
    if sha256_bytes(canonical_json_bytes(check)) != digest:
        raise ValueError("summary hash verification failed")
    return final


def _require_non_empty(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string")
    return value


def _validate_sha256(value: str) -> str:
    value = value.lower()
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("value must be a sha256 hex digest")
    return value


def _validate_utc(value: str) -> str:
    if not _UTC_RE.fullmatch(value):
        raise ValueError("UTC timestamp must be RFC3339 and end with Z")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError("UTC timestamp must contain a valid date and time") from exc
    return value
