"""Small adapter for Phase 6 C2 remote correctness calls.

Documented smoke commands:

- ``.venv/bin/python -m pytest cluster2/tests/test_modal_correctness_check.py -v``
- ``/Users/alexeidelgado/miniconda3/bin/modal run cluster2/modal/correctness.py::smoke_remote_correctness``

This adapter validates request/result payloads and delegates to the C2 Modal
correctness function. It is not an experiment runner and does not call
generation or repair-loop code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cluster2.constants import DEFAULT_C2_MODAL_EVAL_GPU
from cluster2.modal.correctness_runner import (
    REMOTE_CORRECTNESS_EVAL_GPU,
    validate_remote_correctness_payload,
)
from cluster2.modal.schemas import (
    EvalIdentity,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
)


SMOKE_COMMANDS: tuple[str, ...] = (
    ".venv/bin/python -m pytest cluster2/tests/test_modal_correctness_check.py -v",
    "/Users/alexeidelgado/miniconda3/bin/modal run "
    "cluster2/modal/correctness.py::smoke_remote_correctness",
)


RemoteCorrectnessCallable = Callable[[dict[str, Any]], dict[str, Any]]


def build_correctness_request(
    *,
    identity: EvalIdentity | dict[str, Any],
    source: str,
) -> RemoteCorrectnessRequest:
    """Build and validate one C2 remote correctness request."""

    coerced_identity = (
        identity if isinstance(identity, EvalIdentity) else EvalIdentity(**identity)
    )
    return RemoteCorrectnessRequest(identity=coerced_identity, source=source)


def check_remote_correctness(
    request: RemoteCorrectnessRequest | dict[str, Any],
    *,
    remote_call: RemoteCorrectnessCallable | None = None,
) -> dict[str, Any]:
    """Validate ``request``, call remote correctness, and validate the wrapper."""

    coerced_request = (
        request if isinstance(request, RemoteCorrectnessRequest)
        else RemoteCorrectnessRequest(**request)
    )
    if remote_call is None:
        from cluster2.modal.correctness import remote_c2_correctness

        remote_call = remote_c2_correctness.remote

    payload = remote_call(coerced_request.model_dump())
    return validate_correctness_response(payload)


def validate_correctness_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the Phase 6 wrapper and nested result schema."""

    return validate_remote_correctness_payload(payload)


def extract_correctness_result(
    payload: dict[str, Any],
) -> RemoteCorrectnessResult | None:
    """Return the nested correctness result, or ``None`` for INFRA_FAILURE."""

    validate_correctness_response(payload)
    result_payload = payload.get("correctness_result")
    if result_payload is None:
        return None
    return RemoteCorrectnessResult(**result_payload)


def configured_modal_eval_gpu() -> str:
    """Return the locked C2 eval GPU for request/metadata checks."""

    if REMOTE_CORRECTNESS_EVAL_GPU != DEFAULT_C2_MODAL_EVAL_GPU:
        raise RuntimeError("C2 remote correctness GPU drifted from C2 constants")
    return REMOTE_CORRECTNESS_EVAL_GPU
