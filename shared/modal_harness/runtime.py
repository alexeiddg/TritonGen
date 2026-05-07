"""Tiny runtime helpers shared by harness functions and classes."""

from __future__ import annotations

import modal


def current_modal_ids() -> tuple[str | None, str | None]:
    """Return ``(function_call_id, input_id)`` if available, else ``(None, None)``.

    Both calls raise outside a Modal container, so each is wrapped
    independently — a runner that calls this defensively from anywhere
    cannot crash on missing context.
    """
    try:
        call_id = modal.current_function_call_id()
    except Exception:
        call_id = None
    try:
        input_id = modal.current_input_id()
    except Exception:
        input_id = None
    return call_id, input_id
