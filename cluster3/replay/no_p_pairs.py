"""Public Cluster 3 P/no-P pair identity validator."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cluster3.constants import CLUSTER3_CONDITIONS, normalize_cluster3_condition


_PAIR_FOR_CONDITION: dict[str, str] = {
    "P": "none",
    "G+P": "G",
    "C+P": "C",
    "G+C+P": "G+C",
}
_PAIR_IDENTITY_FIELDS = (
    "kernel_class",
    "kernel_name",
    "dtype",
    "base_seed",
)
_OPTIONAL_MODEL_FIELDS = (
    "model_id",
    "model_revision",
    "tokenizer_revision",
    "temperature",
    "max_new_tokens",
)
_PROMPT_HASH_FIELDS = (
    "prompt_sha",
    "prompt_sha256",
    "prompt_hash",
    "base_prompt_sha256",
)


def pair_for_condition(p_condition: str) -> str:
    """Return the no-P control condition paired with a Cluster 3 P condition."""

    condition = normalize_cluster3_condition(p_condition)
    return _PAIR_FOR_CONDITION[condition]


def validate_pair_identity(p_row: Any, control_row: Any) -> None:
    """Validate public identity fields for a Cluster 3 row and no-P control row."""

    p_condition = _field(p_row, "condition")
    if p_condition not in CLUSTER3_CONDITIONS:
        raise ValueError("p_row condition must be one of the Cluster 3 conditions")
    expected_control = pair_for_condition(str(p_condition))
    observed_control = _field(control_row, "condition")
    if observed_control != expected_control:
        raise ValueError(
            f"control row condition must be {expected_control!r}; "
            f"got {observed_control!r}"
        )

    for field_name in _PAIR_IDENTITY_FIELDS:
        _require_equal_required(p_row, control_row, field_name)

    _require_equal_when_present(p_row, control_row, "sample_index")
    _require_equal_when_present(p_row, control_row, "replay_pair_id")

    for field_name in _OPTIONAL_MODEL_FIELDS:
        _require_equal_when_present(p_row, control_row, field_name)

    _require_matching_prompt_hash_when_present(p_row, control_row)
    _require_matching_grammar_variant_when_needed(
        str(p_condition),
        p_row,
        control_row,
    )
    _require_matching_control_source_when_declared(p_row, control_row)


def _require_equal_when_present(row: Any, control_row: Any, field_name: str) -> None:
    left = _find_field(row, field_name)
    right = _find_field(control_row, field_name)
    if left is None or right is None:
        return
    if left != right:
        raise ValueError(
            f"pair identity mismatch for {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_equal_required(row: Any, control_row: Any, field_name: str) -> None:
    left = _find_field(row, field_name)
    right = _find_field(control_row, field_name)
    if left is None or right is None:
        raise ValueError(
            f"pair identity missing required {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )
    if left != right:
        raise ValueError(
            f"pair identity mismatch for {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_prompt_hash_when_present(row: Any, control_row: Any) -> None:
    left = _first_present(row, _PROMPT_HASH_FIELDS)
    right = _first_present(control_row, _PROMPT_HASH_FIELDS)
    if left is None or right is None:
        return
    if left != right:
        raise ValueError(
            f"pair identity mismatch for prompt hash: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_grammar_variant_when_needed(
    p_condition: str,
    row: Any,
    control_row: Any,
) -> None:
    if p_condition not in {"G+P", "G+C+P"}:
        return
    if _truthy_field(row, "allow_grammar_variant_mismatch") or _truthy_field(
        control_row,
        "allow_grammar_variant_mismatch",
    ):
        return
    left = _find_field(row, "grammar_variant")
    right = _find_field(control_row, "grammar_variant")
    if left is None or right is None:
        raise ValueError(
            "pair identity missing required grammar_variant: "
            f"p_row={left!r}, control_row={right!r}"
        )
    if left != right:
        raise ValueError(
            "pair identity mismatch for grammar_variant: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_control_source_when_declared(row: Any, control_row: Any) -> None:
    expected = _first_present(
        row,
        (
            "replay_control_source_hash",
            "expected_control_source_hash",
            "control_source_hash",
            "frozen_control_source_hash",
        ),
    )
    observed = _first_present(
        control_row,
        (
            "source_hash",
            "source_sha256",
            "replay_control_source_hash",
            "expected_control_source_hash",
        ),
    )
    if expected is None or observed is None:
        return
    if expected != observed:
        raise ValueError(
            "pair identity mismatch for control source hash: "
            f"expected={expected!r}, observed={observed!r}"
        )


def _first_present(row: Any, field_names: tuple[str, ...]) -> Any:
    for field_name in field_names:
        value = _find_field(row, field_name)
        if value is not None:
            return value
    return None


def _find_field(row: Any, field_name: str) -> Any:
    direct = _field(row, field_name)
    if direct is not None:
        return direct
    for nested_name in (
        "generated_metadata",
        "replay_metadata",
        "metadata",
        "identity",
        "generation_identity",
        "source_identity",
        "eval_identity",
    ):
        nested = _field(row, nested_name)
        if nested is None:
            continue
        value = _field(nested, field_name)
        if value is not None:
            return value
    return None


def _truthy_field(row: Any, field_name: str) -> bool:
    return _find_field(row, field_name) is True


def _field(container: Any, field_name: str) -> Any:
    if isinstance(container, Mapping):
        return container.get(field_name)
    return getattr(container, field_name, None)


__all__ = ["pair_for_condition", "validate_pair_identity"]
