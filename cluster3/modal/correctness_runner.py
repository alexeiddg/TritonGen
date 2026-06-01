"""Local Cluster 3 adapter over the existing Cluster 2 correctness surface."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from cluster2.constants import generation_mode_for_condition, source_class_for_condition
from cluster2.modal.schemas import EvalIdentity, RemoteCorrectnessRequest
from cluster3.constants import normalize_cluster3_condition
from cluster3.feedback.condition_adapters import (
    cluster3_to_cluster2_eval_condition,
    restamp_cluster3_condition,
)


CLUSTER3_CORRECTNESS_SURFACE = "c3_remote_correctness"
_CLUSTER2_CORRECTNESS_SURFACE = "c2_remote_correctness"
_NORMAL_CORRECTNESS_STATUSES = frozenset({"passed", "failed"})


@dataclass(frozen=True)
class Cluster3CorrectnessRequest:
    """Cluster 3 correctness request wrapper.

    ``identity`` may be a mapping, dataclass, pydantic-like object with
    ``model_dump()``, or a plain object exposing the EvalIdentity field names.
    """

    identity: Any
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("Cluster 3 correctness source must be non-empty")


def run_cluster3_correctness(
    request: Cluster3CorrectnessRequest,
    *,
    modal_call: Callable[[dict], dict] | None = None,
) -> dict:
    """Run Cluster 3 correctness through the existing Cluster 2 function."""

    if not isinstance(request, Cluster3CorrectnessRequest):
        raise TypeError("request must be a Cluster3CorrectnessRequest")

    c3_condition = _cluster3_condition_from_identity(request.identity)
    c2_request = _build_cluster2_correctness_request(request, c3_condition)
    request_payload = c2_request.model_dump()

    if modal_call is None:
        payload = _call_existing_cluster2_correctness(request_payload)
    else:
        payload = modal_call(request_payload)

    if not isinstance(payload, dict):
        raise TypeError("Cluster 2 correctness call must return a dict payload")

    _restamp_payload_to_cluster3(payload, c3_condition)
    _assert_normal_payload_identity_consistency(payload)
    return payload


def validate_cluster3_remote_correctness_payload(payload: Any) -> dict:
    """Validate a Cluster 3-restamped correctness payload with C2's validator."""

    if not isinstance(payload, dict):
        raise TypeError("Cluster 3 remote correctness payload must be a dict")

    c3_condition = _cluster3_condition_from_payload(payload)
    c2_condition = cluster3_to_cluster2_eval_condition(c3_condition)
    validation_payload = copy.deepcopy(payload)
    _restamp_payload_condition(
        validation_payload,
        condition=c2_condition,
        surface=_CLUSTER2_CORRECTNESS_SURFACE,
    )

    from cluster2.modal.correctness_runner import validate_remote_correctness_payload

    validate_remote_correctness_payload(validation_payload)
    _restamp_payload_to_cluster3(payload, c3_condition)
    return payload


def _build_cluster2_correctness_request(
    request: Cluster3CorrectnessRequest,
    c3_condition: str,
) -> RemoteCorrectnessRequest:
    c2_condition = cluster3_to_cluster2_eval_condition(c3_condition)
    identity_payload = _identity_to_dict(request.identity)
    identity_payload["condition"] = c2_condition
    identity_payload["source_class"] = source_class_for_condition(c2_condition)
    identity_payload["generation_mode"] = generation_mode_for_condition(c2_condition)
    identity = EvalIdentity(**identity_payload)
    return RemoteCorrectnessRequest(identity=identity, source=request.source)


def _call_existing_cluster2_correctness(request_payload: dict[str, Any]) -> dict:
    from cluster2.modal.correctness import remote_c2_correctness

    return remote_c2_correctness.remote(request_payload)


def _cluster3_condition_from_identity(identity: Any) -> str:
    identity_payload = _identity_to_dict(identity)
    condition = identity_payload.get("condition")
    return normalize_cluster3_condition(condition)


def _cluster3_condition_from_payload(payload: dict[str, Any]) -> str:
    for container in (
        payload.get("identity"),
        _get_field(payload.get("correctness_result"), "identity"),
        payload.get("source_identity"),
        payload.get("eval_identity"),
        payload,
    ):
        condition = _get_field(container, "condition")
        if condition is None:
            continue
        try:
            return normalize_cluster3_condition(condition)
        except ValueError:
            continue
    raise ValueError("payload does not contain a Cluster 3 condition stamp")


def _identity_to_dict(identity: Any) -> dict[str, Any]:
    if isinstance(identity, Mapping):
        return dict(identity)
    if hasattr(identity, "model_dump"):
        dumped = identity.model_dump()
        if isinstance(dumped, dict):
            return dict(dumped)
    if is_dataclass(identity) and not isinstance(identity, type):
        return asdict(identity)

    fields = (
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
    payload: dict[str, Any] = {}
    for field_name in fields:
        if hasattr(identity, field_name):
            payload[field_name] = getattr(identity, field_name)
    if payload:
        return payload
    raise TypeError("identity must be a mapping or expose EvalIdentity fields")


def _restamp_payload_to_cluster3(payload: dict[str, Any], c3_condition: str) -> None:
    restamp_cluster3_condition(payload, c3_condition)
    _restamp_payload_condition(
        payload,
        condition=c3_condition,
        surface=CLUSTER3_CORRECTNESS_SURFACE,
    )


def _restamp_payload_condition(
    payload: dict[str, Any],
    *,
    condition: str,
    surface: str,
) -> None:
    payload["surface"] = surface
    if "condition" in payload:
        payload["condition"] = condition

    for field_name in ("identity", "source_identity", "eval_identity"):
        _set_condition_if_present(payload.get(field_name), condition)

    correctness_result = payload.get("correctness_result")
    if correctness_result is not None:
        _set_condition_if_present(_get_field(correctness_result, "identity"), condition)


def _assert_normal_payload_identity_consistency(payload: dict[str, Any]) -> None:
    status = payload.get("correctness_status")
    if status not in _NORMAL_CORRECTNESS_STATUSES:
        return
    correctness_result = payload.get("correctness_result")
    if correctness_result is None:
        raise ValueError("normal correctness payload missing correctness_result")

    wrapper_condition = _get_field(payload.get("identity"), "condition")
    result_condition = _get_field(
        _get_field(correctness_result, "identity"),
        "condition",
    )
    if wrapper_condition != result_condition:
        raise ValueError(
            "Cluster 3 correctness payload identity condition mismatch after restamp"
        )


def _get_field(container: Any, field_name: str) -> Any:
    if isinstance(container, Mapping):
        return container.get(field_name)
    if container is None:
        return None
    return getattr(container, field_name, None)


def _set_condition_if_present(container: Any, condition: str) -> None:
    if container is None:
        return
    if isinstance(container, dict):
        container["condition"] = condition
        return
    if hasattr(container, "condition"):
        try:
            setattr(container, "condition", condition)
        except (AttributeError, TypeError):
            return

