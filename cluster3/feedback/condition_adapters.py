"""Condition adapters for Cluster 3 local orchestration."""

from __future__ import annotations

from typing import Any

from cluster3 import constants as _constants


_CLUSTER3_TO_CLUSTER2_GENERATION = _constants._CLUSTER3_TO_CLUSTER2_GENERATION
_CLUSTER3_TO_CLUSTER2_REPAIR = _constants._CLUSTER3_TO_CLUSTER2_REPAIR


def cluster3_to_cluster2_generation_condition(c3_condition: str) -> str:
    """Translate a Cluster 3 generation condition to a Cluster 2 condition."""

    normalized = _constants.normalize_cluster3_condition(c3_condition)
    return _CLUSTER3_TO_CLUSTER2_GENERATION[normalized]


def cluster3_to_cluster2_eval_condition(c3_condition: str) -> str:
    """Translate a Cluster 3 correctness-eval condition to Cluster 2 labels."""

    return cluster3_to_cluster2_generation_condition(c3_condition)


def cluster3_to_cluster2_repair_condition(c3_condition: str) -> str:
    """Translate C-active Cluster 3 conditions for Cluster 2 C repair."""

    normalized = _constants.normalize_cluster3_condition(c3_condition)
    try:
        return _CLUSTER3_TO_CLUSTER2_REPAIR[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Cluster 3 condition {c3_condition!r} cannot invoke C repair"
        ) from exc


def restamp_cluster3_condition(payload_or_result: dict[str, Any] | object, c3_condition: str) -> None:
    """Restamp a Cluster 2 correctness payload back to Cluster 3 labels in-place."""

    normalized = _constants.normalize_cluster3_condition(c3_condition)
    _set_field(payload_or_result, "surface", "c3_remote_correctness", create=True)
    _set_field(payload_or_result, "condition", normalized, create=True)

    for field_name in ("identity", "source_identity", "eval_identity"):
        nested = _get_field(payload_or_result, field_name)
        if nested is not None:
            _set_field(nested, "condition", normalized, create=False)

    correctness_result = _get_field(payload_or_result, "correctness_result")
    if correctness_result is not None:
        nested_identity = _get_field(correctness_result, "identity")
        if nested_identity is not None:
            _set_field(nested_identity, "condition", normalized, create=False)


def _get_field(container: dict[str, Any] | object, field_name: str) -> Any:
    if isinstance(container, dict):
        return container.get(field_name)
    return getattr(container, field_name, None)


def _set_field(
    container: dict[str, Any] | object,
    field_name: str,
    value: Any,
    *,
    create: bool,
) -> None:
    if isinstance(container, dict):
        if create or field_name in container:
            container[field_name] = value
        return

    if create or hasattr(container, field_name):
        try:
            setattr(container, field_name, value)
        except (AttributeError, TypeError):
            return

