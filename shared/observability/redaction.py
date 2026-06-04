"""Fail-closed privacy checks for observability sidecars."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

JsonPrimitive = str | int | float | bool | None
AttributeValue = JsonPrimitive | list[JsonPrimitive]

MAX_ATTRIBUTE_KEYS = 32
MAX_ATTRIBUTE_KEY_LENGTH = 80
MAX_ATTRIBUTE_STRING_LENGTH = 512
MAX_ATTRIBUTE_LIST_LENGTH = 32
MAX_SERIALIZED_ATTRIBUTES_BYTES = 8192

_SAFE_HASH_KEYS = {
    "source_sha256",
    "source_hash",
    "source_event_sha256",
    "prompt_sha256",
    "prompt_hash",
    "error_excerpt_sha256",
    "compile_error_excerpt_sha256",
    "row_sha256",
}
_SAFE_TOKEN_COUNT_KEYS = {
    "token_counts",
    "token_counts_available",
    "prompt_tokens",
    "generated_tokens",
    "total_tokens",
    "token_count_source",
    "token_count_status",
}
_SAFE_MODAL_CONTEXT_KEYS = {
    "modal_context",
    "modal_context_available",
    "is_remote",
    "function_call_id",
    "input_id",
    "task_id",
    "image_id",
    "region",
    "cloud_provider",
    "environment_name",
    "app_name",
    "gpu_type",
    "gpu_count",
    "cpu_cores",
    "memory_gib",
    "timeout_s",
    "container_started_at_utc",
    "modal_context_source",
    "modal_context_summary",
    "context_status",
    "events_with_modal_context",
    "events_with_available_context",
    "modal_context_sources",
}
_SAFE_COST_ESTIMATE_KEYS = {
    "cost_estimate",
    "estimated_cost_summary",
    "cost_estimate_available",
    "estimated_input_cost",
    "estimated_output_cost",
    "estimated_total_cost",
    "currency",
    "pricing_source",
    "pricing_source_version",
    "cost_estimate_status",
    "cost_estimate_method",
}
_SAFE_ACTUAL_BILLING_KEYS = {
    "billing_reconciliation",
    "actual_billing_summary",
    "actual_billing_available",
    "actual_billing_status",
    "actual_billing_reconciled_at_utc",
    "billing_source",
    "billing_source_version",
    "billing_time_window_start_utc",
    "billing_time_window_end_utc",
    "billing_attribution_method",
    "billing_attribution_confidence",
    "actual_total_cost",
    "actual_currency",
    "billing_query_id",
    "billing_report_redacted_sha256",
    "billing_reconciliation_notes",
}
_SAFE_ID_KEYS = {
    "event_id",
    "run_id",
    "experiment_id",
    "input_id",
    "task_id",
    "image_id",
    "clock_scope_id",
}
_SAFE_STATUS_KEYS = {
    "actual_billing_status",
    "summary_status",
}
_FORBIDDEN_EXACT_KEYS = {
    "authorization",
    "billing",
    "credential",
    "credentials",
    "env",
    "environ",
    "environment",
    "source",
    "prompt",
    "feedback",
    "password",
    "secret",
    "token",
}
_FORBIDDEN_KEY_PATTERNS = (
    "source_text",
    "full_source",
    "generated_source",
    "raw_source",
    "source_code",
    "kernel_source",
    "prompt_text",
    "raw_prompt",
    "system_prompt",
    "user_prompt",
    "feedback_prompt",
    "hidden_prompt",
    "completion_text",
    "generated_text",
    "raw_feedback",
    "private_feedback",
    "raw_model_output",
    "model_output",
    "raw_output",
    "raw_completion",
    "raw_compile_log",
    "compile_log",
    "stack_trace",
    "traceback",
    "private_eval",
    "eval_shape_set",
    "hidden_correctness",
    "token_ids",
    "input_ids",
    "output_ids",
    "tokenizer_dump",
    "tokenizer_state",
    "tokenizer_internal_state",
    "tokenizer_id",
    "tokenizer_revision",
    "max_new_tokens",
    "truncation_applied",
    "environment_dump",
    "environment_variables",
    "env_vars",
    "env_dump",
    "os_environ",
    "modal_identity_token",
    "hf_token",
    "aws_secret_access_key",
    "identity_token",
    "authorization_header",
    "actual_cost",
    "actual_billing",
    "actual_billing_cost",
    "account_charge",
    "billing_data",
    "billing_report",
    "billing_api_response",
    "full_billing_api_response",
    "pricing_api_response",
    "provider_bill",
    "provider_billing",
    "modal_bill",
    "modal_billing",
    "invoice",
    "raw_invoice_dump",
    "cloud_invoice_dump",
    "unredacted_workspace_billing_report",
    "workspace_billing_report",
    "external_pricing_fetch",
    "credit_card",
    "payment_method",
    "billing_account",
    "billing_account_secret",
    "customer_secret",
    "account_secret",
    "provider_api_key",
    "cost_per_success",
    "cost_per_pass",
    "pass_at_k_cost",
    "roi",
    "economic_lift",
    "benchmark_economics",
    "benchmark_cost_conclusion",
    "paper_scale_cost_conclusion",
    "price_snapshot_id",
    "estimated_gpu_seconds",
    "estimated_cpu_core_seconds",
    "estimated_memory_gib_seconds",
    "estimated_gpu_cost_usd",
    "estimated_cpu_cost_usd",
    "estimated_memory_cost_usd",
    "estimated_total_cost_usd",
    "estimation_confidence",
    "cost_basis",
    "gpu_utilization",
    "gpu_power",
    "gpu_memory",
    "gpu_temperature",
    "gpu_mem",
    "power_draw",
    "temperature",
    "profiler",
    "kernel_timing",
    "latency",
    "throughput",
    "speedup",
    "performance",
    "benchmark",
)
_FORBIDDEN_SECRET_KEY_PATTERNS = (
    "secret",
    "password",
    "credential",
    "api_key",
    "access_key",
    "private_key",
)
_FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"\bsource[\s_-]+text\b", re.IGNORECASE),
    re.compile(r"\bprompt[\s_-]+text\b", re.IGNORECASE),
    re.compile(r"\bcompletion[\s_-]+text\b", re.IGNORECASE),
    re.compile(r"\bgenerated[\s_-]+text\b", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+output\b", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+completion\b", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+feedback\b", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+compile[\s_-]+logs?\b", re.IGNORECASE),
    re.compile(r"\btokenizer[\s_-]+dump\b", re.IGNORECASE),
    re.compile(r"\btokenizer[\s_-]+(?:internal[\s_-]+)?state\b", re.IGNORECASE),
    re.compile(r"\bhidden[\s_-]+prompt\b", re.IGNORECASE),
    re.compile(r"\bprivate[\s_-]+eval\b", re.IGNORECASE),
    re.compile(r"\bprivate[\s_-]+feedback\b", re.IGNORECASE),
    re.compile(r"\beval_shape_set\b", re.IGNORECASE),
    re.compile(r"\bhidden[\s_-]+correctness\b", re.IGNORECASE),
    re.compile(r"\btorch\.testing\b", re.IGNORECASE),
    re.compile(r"\ballclose\b", re.IGNORECASE),
    re.compile(r"\bHF_TOKEN\b", re.IGNORECASE),
    re.compile(r"\bMODAL_IDENTITY_TOKEN\b", re.IGNORECASE),
    re.compile(r"\bAWS_SECRET_ACCESS_KEY\b", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+invoice\b", re.IGNORECASE),
    re.compile(r"\binvoice[\s_-]+dump\b", re.IGNORECASE),
    re.compile(r"\bfull[\s_-]+billing[\s_-]+api[\s_-]+response\b", re.IGNORECASE),
    re.compile(r"\bunredacted[\s_-]+workspace[\s_-]+billing[\s_-]+report\b", re.IGNORECASE),
    re.compile(r"\bpayment[\s_-]+method\b", re.IGNORECASE),
    re.compile(r"\bcredit[\s_-]+card\b", re.IGNORECASE),
    re.compile(r"\b(cost[\s_-]+per[\s_-]+success|cost_per_success)\b", re.IGNORECASE),
    re.compile(r"\b(pass[\s_-]+at[\s_-]+k[\s_-]+cost|pass_at_k_cost)\b", re.IGNORECASE),
    re.compile(r"\bROI\b", re.IGNORECASE),
    re.compile(r"\beconomic[\s_-]+lift\b", re.IGNORECASE),
    re.compile(r"\bbenchmark[\s_-]+economics\b", re.IGNORECASE),
    re.compile(r"\bpaper[\s_-]+scale[\s_-]+cost[\s_-]+conclusion\b", re.IGNORECASE),
)


class ObservabilityRedactionError(ValueError):
    """Raised when sidecar payloads contain forbidden operational content."""


def sanitize_attributes(attributes: Mapping[str, Any] | None) -> dict[str, AttributeValue]:
    """Return a JSON-safe attributes map or fail closed.

    Attributes are intentionally shallow: primitive values plus shallow lists of
    primitives. Rich telemetry belongs in typed sidecar sections, not here.
    """

    if attributes is None:
        return {}
    if not isinstance(attributes, Mapping):
        raise ObservabilityRedactionError("attributes must be a mapping")
    if len(attributes) > MAX_ATTRIBUTE_KEYS:
        raise ObservabilityRedactionError("attributes exceed maximum key count")

    sanitized: dict[str, AttributeValue] = {}
    for key, value in attributes.items():
        if not isinstance(key, str):
            raise ObservabilityRedactionError("attribute keys must be strings")
        if len(key) > MAX_ATTRIBUTE_KEY_LENGTH:
            raise ObservabilityRedactionError(f"attribute key {key!r} is too long")
        _reject_forbidden_key(key, path=f"attributes.{key}")
        sanitized[key] = _sanitize_attribute_value(value, path=f"attributes.{key}")

    reject_forbidden_observability_payload(sanitized)
    encoded = json.dumps(
        sanitized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if len(encoded) > MAX_SERIALIZED_ATTRIBUTES_BYTES:
        raise ObservabilityRedactionError("serialized attributes exceed byte limit")
    return sanitized


def sanitize_error_summary(summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Validate a bounded public error summary.

    O0 does not redact rich logs into sidecars. It accepts only already-bounded
    public summaries and rejects anything that looks like source, prompts, raw
    logs, private eval data, or secrets.
    """

    if summary is None:
        return None
    if not isinstance(summary, Mapping):
        raise ObservabilityRedactionError("error_summary must be a mapping")
    reject_forbidden_observability_payload(summary)
    encoded = json.dumps(
        summary,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if len(encoded) > MAX_SERIALIZED_ATTRIBUTES_BYTES:
        raise ObservabilityRedactionError("error_summary exceeds byte limit")
    return dict(summary)


def reject_forbidden_observability_payload(payload: Any, *, path: str = "$") -> None:
    """Reject forbidden sidecar keys or representative forbidden values."""

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise ObservabilityRedactionError(f"{path} contains a non-string key")
            child_path = f"{path}.{key}"
            _reject_forbidden_key(key, path=child_path)
            reject_forbidden_observability_payload(value, path=child_path)
        return
    if _is_string_sequence(payload):
        for index, item in enumerate(payload):
            reject_forbidden_observability_payload(item, path=f"{path}[{index}]")
        return
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raise ObservabilityRedactionError(f"{path} contains bytes")
    if isinstance(payload, str):
        _reject_forbidden_string(payload, path=path)


def _sanitize_attribute_value(value: Any, *, path: str) -> AttributeValue:
    if _is_primitive(value):
        _validate_primitive(value, path=path)
        return value
    if _is_string_sequence(value):
        if len(value) > MAX_ATTRIBUTE_LIST_LENGTH:
            raise ObservabilityRedactionError(f"{path} exceeds maximum list length")
        sanitized: list[JsonPrimitive] = []
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            if not _is_primitive(item):
                raise ObservabilityRedactionError(
                    f"{item_path} must be a JSON primitive"
                )
            _validate_primitive(item, path=item_path)
            sanitized.append(item)
        return sanitized
    raise ObservabilityRedactionError(
        f"{path} must be a JSON primitive or a shallow list of primitives"
    )


def _validate_primitive(value: JsonPrimitive, *, path: str) -> None:
    if isinstance(value, str):
        if len(value) > MAX_ATTRIBUTE_STRING_LENGTH:
            raise ObservabilityRedactionError(f"{path} string value is too long")
        _reject_forbidden_string(value, path=path)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ObservabilityRedactionError(f"{path} must be a finite number")


def _reject_forbidden_key(key: str, *, path: str) -> None:
    normalized = _normalize_key(key)
    if normalized in _SAFE_HASH_KEYS or normalized in _SAFE_TOKEN_COUNT_KEYS:
        return
    if normalized in _SAFE_MODAL_CONTEXT_KEYS or normalized in _SAFE_STATUS_KEYS:
        return
    if normalized in _SAFE_COST_ESTIMATE_KEYS:
        return
    if normalized in _SAFE_ACTUAL_BILLING_KEYS:
        return
    if normalized in _SAFE_ID_KEYS:
        return
    if normalized in _FORBIDDEN_EXACT_KEYS:
        raise ObservabilityRedactionError(f"{path} uses forbidden key {key!r}")
    if any(pattern in normalized for pattern in _FORBIDDEN_KEY_PATTERNS):
        raise ObservabilityRedactionError(f"{path} uses forbidden key {key!r}")
    if any(pattern in normalized for pattern in _FORBIDDEN_SECRET_KEY_PATTERNS):
        raise ObservabilityRedactionError(f"{path} uses secret-like key {key!r}")
    if normalized == "token" or normalized.endswith("_token"):
        raise ObservabilityRedactionError(f"{path} uses token-like key {key!r}")


def _reject_forbidden_string(value: str, *, path: str) -> None:
    for pattern in _FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(value):
            raise ObservabilityRedactionError(f"{path} contains forbidden content")


def _normalize_key(key: str) -> str:
    acronym_split = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", key.strip())
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", acronym_split)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray, memoryview),
    )
