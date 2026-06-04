"""Tiny runtime helpers shared by harness functions and classes."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any

SAFE_MODAL_CONTEXT_FIELDS = frozenset(
    {
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
    }
)
_MODAL_RUNTIME_CONTEXT_FIELDS = SAFE_MODAL_CONTEXT_FIELDS - {
    "modal_context_available",
    "modal_context_source",
    "is_remote",
}


def unavailable_modal_context() -> dict[str, Any]:
    """Return an explicit no-context payload without reading Modal state."""

    return {
        "modal_context_available": False,
        "is_remote": False,
        "modal_context_source": "unavailable",
    }


def normalize_modal_context(raw_context: Any) -> dict[str, Any]:
    """Return only allowlisted Modal context fields or fail closed.

    The helper accepts local fakes, dicts, and Pydantic-like objects. It does
    not redact arbitrary structures: unknown keys are rejected so callers do not
    accidentally persist env dumps, secrets, billing, or performance payloads.
    """

    if raw_context is None:
        return unavailable_modal_context()

    if hasattr(raw_context, "model_dump"):
        try:
            raw_context = raw_context.model_dump(mode="json")
        except TypeError:
            raw_context = raw_context.model_dump()

    if not isinstance(raw_context, Mapping):
        raise ValueError("Modal context must be a mapping")

    unknown_keys = sorted(
        str(key) for key in raw_context if key not in SAFE_MODAL_CONTEXT_FIELDS
    )
    if unknown_keys:
        raise ValueError(f"Modal context contains non-allowlisted keys: {unknown_keys}")

    payload = {
        str(key): value
        for key, value in raw_context.items()
        if value is not None and key in SAFE_MODAL_CONTEXT_FIELDS
    }
    if not payload:
        return unavailable_modal_context()

    if "modal_context_available" in payload and not isinstance(
        payload["modal_context_available"], bool
    ):
        raise ValueError("Modal context availability must be a boolean")
    if "is_remote" in payload and not isinstance(payload["is_remote"], bool):
        raise ValueError("Modal context remote flag must be a boolean")

    if payload.get("modal_context_available") is False:
        _reject_unavailable_context_conflicts(payload)
        return unavailable_modal_context()

    has_runtime_context = _has_runtime_context(payload)
    if payload.get("modal_context_available") is True and not has_runtime_context:
        raise ValueError(
            "available Modal context requires at least one runtime identity "
            "or resource field"
        )
    if "modal_context_available" not in payload:
        if not has_runtime_context:
            _reject_unavailable_context_conflicts(payload)
            return unavailable_modal_context()
        payload["modal_context_available"] = True

    payload.setdefault("is_remote", True)
    payload.setdefault("modal_context_source", "runner_config")
    return payload


def get_modal_runtime_context_or_unavailable(
    raw_context: Any = None,
    *,
    collect_current_ids: bool = True,
) -> dict[str, Any]:
    """Collect safe Modal identifiers already exposed by the runtime helper.

    This does not create a Modal call or inspect environment variables. Local
    callers can pass ``collect_current_ids=False`` to force unavailable context.
    """

    if raw_context is not None:
        return normalize_modal_context(raw_context)
    if not collect_current_ids:
        return unavailable_modal_context()

    call_id, input_id = current_modal_ids()
    if call_id is None and input_id is None:
        return unavailable_modal_context()
    return normalize_modal_context(
        {
            "modal_context_available": True,
            "is_remote": True,
            "function_call_id": call_id,
            "input_id": input_id,
            "modal_context_source": "shared_modal_runtime_helper",
        }
    )


def current_modal_ids() -> tuple[str | None, str | None]:
    """Return ``(function_call_id, input_id)`` if available, else ``(None, None)``.

    Both calls raise outside a Modal container, so each is wrapped
    independently — a runner that calls this defensively from anywhere
    cannot crash on missing context.
    """
    try:
        modal = importlib.import_module("modal")
    except Exception:
        return None, None

    try:
        call_id = modal.current_function_call_id()
    except Exception:
        call_id = None
    try:
        input_id = modal.current_input_id()
    except Exception:
        input_id = None
    return call_id, input_id


def _has_runtime_context(payload: Mapping[str, Any]) -> bool:
    return any(payload.get(key) is not None for key in _MODAL_RUNTIME_CONTEXT_FIELDS)


def _reject_unavailable_context_conflicts(payload: Mapping[str, Any]) -> None:
    if _has_runtime_context(payload):
        raise ValueError("unavailable Modal context must not include runtime fields")
    if payload.get("is_remote") is True:
        raise ValueError("unavailable Modal context cannot be remote")
    source = payload.get("modal_context_source")
    if source not in {None, "unavailable"}:
        raise ValueError("unavailable Modal context requires source unavailable")
