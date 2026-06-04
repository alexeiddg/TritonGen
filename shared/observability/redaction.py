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
    "max_new_tokens",
    "tokenizer_id",
    "tokenizer_revision",
    "count_source",
    "truncation_applied",
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
_SAFE_ID_KEYS = {
    "event_id",
    "run_id",
    "experiment_id",
    "input_id",
    "task_id",
    "image_id",
    "clock_scope_id",
    "price_snapshot_id",
    "snapshot_id",
}
_SAFE_STATUS_KEYS = {
    "actual_billing_status",
    "summary_status",
    "estimate_status",
    "cost_basis",
    "estimation_confidence",
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
    "raw_feedback",
    "raw_model_output",
    "model_output",
    "raw_output",
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
    "actual_billing_cost",
    "billing_data",
    "billing_report",
    "invoice",
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
    re.compile(r"\braw[\s_-]+feedback\b", re.IGNORECASE),
    re.compile(r"\braw[\s_-]+compile[\s_-]+logs?\b", re.IGNORECASE),
    re.compile(r"\bprivate[\s_-]+eval\b", re.IGNORECASE),
    re.compile(r"\beval_shape_set\b", re.IGNORECASE),
    re.compile(r"\bhidden[\s_-]+correctness\b", re.IGNORECASE),
    re.compile(r"\btorch\.testing\b", re.IGNORECASE),
    re.compile(r"\ballclose\b", re.IGNORECASE),
    re.compile(r"\bHF_TOKEN\b", re.IGNORECASE),
    re.compile(r"\bMODAL_IDENTITY_TOKEN\b", re.IGNORECASE),
    re.compile(r"\bAWS_SECRET_ACCESS_KEY\b", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY", re.IGNORECASE),
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
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key.strip())
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray, memoryview),
    )
