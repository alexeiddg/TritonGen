"""Cluster 3-owned correctness result extraction and F3 synthesis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from cluster3.constants import normalize_cluster3_condition


F3_EVAL_PIPELINE_FAILURE_CODE = "F3_EVAL_PIPELINE"
_PUBLIC_TEXT_LIMIT = 300
_COMPILE_ERROR_EXCERPT_LIMIT = 2000
_IDENTITY_FIELDS = (
    "run_id",
    "condition",
    "source_class",
    "generation_mode",
    "kernel_class",
    "kernel_name",
    "dtype",
    "sample_index",
    "base_seed",
    "attempt_index",
)
_SOURCE_IDENTITY_FIELDS = (
    "condition",
    "source_class",
    "generation_mode",
    "kernel_class",
    "kernel_name",
    "dtype",
    "sample_index",
    "base_seed",
    "attempt_index",
)
_EVAL_IDENTITY_FIELDS = (
    "condition",
    "kernel_class",
    "kernel_name",
    "dtype",
    "base_seed",
    "attempt_index",
)


def extract_or_synthesize_cluster3_correctness_result_dict(
    payload: Any,
    identity: Any,
) -> dict[str, Any]:
    """Return a canonical Cluster 3 correctness-result dict.

    Malformed and infrastructure payloads synthesize a public F3 result instead
    of leaking raw payload internals or crashing the caller.
    """

    identity_payload, identity_error = _coerce_cluster3_identity(identity)
    if identity_error is not None:
        return _synthesize_f3_result(identity_payload, reason=identity_error)

    if not isinstance(payload, dict):
        return _synthesize_f3_result(
            identity_payload,
            reason=_public_payload_summary(
                payload,
                prefix="Malformed correctness payload",
            ),
        )

    wrapper_error = _validate_available_wrapper_identities(payload, identity_payload)
    if wrapper_error is not None:
        return _synthesize_f3_result(identity_payload, reason=wrapper_error)

    result = payload.get("correctness_result")
    if isinstance(result, dict):
        nested_error = _validate_nested_result_identity(result, identity_payload)
        if nested_error is not None:
            return _synthesize_f3_result(identity_payload, reason=nested_error)
        return _canonicalize_result(result, identity_payload)

    return _synthesize_f3_result(
        identity_payload,
        reason=_public_payload_summary(
            payload,
            prefix="Correctness payload without correctness_result",
        ),
    )


def _canonicalize_result(
    result: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    canonical = dict(result)
    canonical["identity"] = dict(identity_payload)
    canonical.setdefault("failure_code", None)
    canonical.setdefault("level_reached", 0)
    if canonical.get("compile_success") is None:
        canonical["compile_success"] = _compile_success_from_result(canonical)
    canonical.setdefault("functional_success", False)
    canonical.setdefault("repair_set_success", False)
    canonical.setdefault("eval_set_success", False)
    canonical.setdefault("compile_error_type", None)
    canonical.setdefault("compile_error", None)
    if "compile_error_excerpt" not in canonical and isinstance(
        canonical.get("compile_error"),
        str,
    ):
        canonical["compile_error_excerpt"] = canonical["compile_error"][
            :_COMPILE_ERROR_EXCERPT_LIMIT
        ]
    return canonical


def _synthesize_f3_result(
    identity_payload: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    public_reason = _clean_public_text(reason)
    return {
        "identity": dict(identity_payload),
        "failure_code": F3_EVAL_PIPELINE_FAILURE_CODE,
        "level_reached": 0,
        "compile_success": False,
        "functional_success": False,
        "repair_set_success": False,
        "eval_set_success": False,
        "compile_error_type": None,
        "compile_error": None,
        "compile_error_excerpt": None,
        "f3_reason": public_reason,
        "correctness_error": public_reason,
        "parse_success": None,
        "parse_error": None,
        "signature_valid": None,
        "signature_error": None,
        "feedback": None,
        "num_repair_shapes": 0,
        "num_eval_shapes": 0,
        "num_test_shapes": 0,
        "shapes_passed": 0,
        "repair_shapes_passed": 0,
        "eval_shapes_passed": 0,
        "max_abs_diff": None,
        "max_rel_diff": None,
    }


def _coerce_cluster3_identity(identity: Any) -> tuple[dict[str, Any], str | None]:
    try:
        payload = _object_to_dict(identity)
    except TypeError as exc:
        return {}, f"Malformed Cluster 3 identity: {exc}"

    condition = payload.get("condition")
    try:
        payload["condition"] = normalize_cluster3_condition(condition)
    except (TypeError, ValueError) as exc:
        return payload, f"Malformed Cluster 3 identity condition: {exc}"

    missing = [
        field_name for field_name in _IDENTITY_FIELDS if field_name not in payload
    ]
    if missing:
        return payload, "Malformed Cluster 3 identity: missing fields=" + ",".join(
            missing
        )
    return payload, None


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dict(dumped)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)

    payload: dict[str, Any] = {}
    for field_name in _IDENTITY_FIELDS:
        if hasattr(value, field_name):
            payload[field_name] = getattr(value, field_name)
    if payload:
        return payload
    raise TypeError("identity must be a mapping or expose identity fields")


def _validate_nested_result_identity(
    result: dict[str, Any],
    identity_payload: dict[str, Any],
) -> str | None:
    result_identity = result.get("identity")
    if not isinstance(result_identity, dict):
        return "Malformed correctness_result identity: missing or non-dict identity"
    missing = [
        field_name
        for field_name in _IDENTITY_FIELDS
        if field_name not in result_identity
    ]
    if missing:
        return "Malformed correctness_result identity: missing fields=" + ",".join(
            missing
        )
    return _identity_mismatch_reason(
        result_identity,
        identity_payload,
        fields=_IDENTITY_FIELDS,
        label="correctness_result.identity",
    )


def _validate_available_wrapper_identities(
    payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> str | None:
    wrapper_identity = payload.get("identity")
    if wrapper_identity is not None:
        if not isinstance(wrapper_identity, dict):
            return "Malformed wrapper identity: identity is not a dict"
        missing = [
            field_name
            for field_name in _IDENTITY_FIELDS
            if field_name not in wrapper_identity
        ]
        if missing:
            return "Malformed wrapper identity: missing fields=" + ",".join(missing)
        reason = _identity_mismatch_reason(
            wrapper_identity,
            identity_payload,
            fields=_IDENTITY_FIELDS,
            label="identity",
        )
        if reason is not None:
            return reason

    source_identity = payload.get("source_identity")
    if source_identity is not None:
        if not isinstance(source_identity, dict):
            return "Malformed source_identity: source_identity is not a dict"
        reason = _identity_mismatch_reason(
            source_identity,
            identity_payload,
            fields=_SOURCE_IDENTITY_FIELDS,
            label="source_identity",
        )
        if reason is not None:
            return reason

    eval_identity = payload.get("eval_identity")
    if eval_identity is not None:
        if not isinstance(eval_identity, dict):
            return "Malformed eval_identity: eval_identity is not a dict"
        reason = _identity_mismatch_reason(
            eval_identity,
            identity_payload,
            fields=_EVAL_IDENTITY_FIELDS,
            label="eval_identity",
        )
        if reason is not None:
            return reason
    return None


def _identity_mismatch_reason(
    observed: dict[str, Any],
    expected: dict[str, Any],
    *,
    fields: tuple[str, ...],
    label: str,
) -> str | None:
    for field_name in fields:
        if field_name not in observed:
            continue
        if field_name not in expected:
            continue
        if observed[field_name] != expected[field_name]:
            return (
                f"Cluster 3 identity mismatch in {label}: "
                f"field={field_name}"
            )
    return None


def _compile_success_from_result(result: dict[str, Any]) -> bool:
    value = result.get("compile_success")
    if isinstance(value, bool):
        return value
    if result.get("functional_success") is True:
        return True
    failure_code = result.get("failure_code")
    if isinstance(failure_code, str):
        if failure_code.startswith(("F0_", "F1_")):
            return False
        if failure_code.startswith("F2_"):
            return True
    level_reached = result.get("level_reached")
    return (
        isinstance(level_reached, int)
        and not isinstance(level_reached, bool)
        and level_reached >= 2
    )


def _public_payload_summary(payload: Any, *, prefix: str) -> str:
    payload_type = type(payload).__name__
    if not isinstance(payload, dict):
        return f"{prefix}: payload_type={payload_type}"

    keys = ",".join(sorted(str(key) for key in payload.keys())) or "<none>"
    parts = [f"{prefix}: payload_type={payload_type}"]
    status = payload.get("correctness_status")
    if isinstance(status, str):
        parts.append(f"correctness_status={_clean_public_text(status)}")

    infrastructure_failure = payload.get("infrastructure_failure")
    if isinstance(infrastructure_failure, dict):
        error_type = infrastructure_failure.get("error_type")
        error_msg = infrastructure_failure.get("error_msg")
        if isinstance(error_type, str):
            parts.append(f"error_type={_clean_public_text(error_type)}")
        if isinstance(error_msg, str):
            parts.append(f"error_msg={_clean_public_text(error_msg)}")
    parts.append(f"keys=[{keys}]")
    return "; ".join(parts)


def _clean_public_text(value: str) -> str:
    text = " ".join(str(value).split())
    if len(text) > _PUBLIC_TEXT_LIMIT:
        return text[: _PUBLIC_TEXT_LIMIT - 3] + "..."
    return text
