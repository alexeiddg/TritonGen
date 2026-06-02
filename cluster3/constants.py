"""Cluster 3 condition and routing constants.

This module is intentionally metadata-only. It does not import Modal, Torch,
Triton, transformers, xgrammar, or any generation/evaluation runtime.
"""

from __future__ import annotations

from typing import Literal, TypeAlias, cast

from cluster2.constants import (
    GENERATED_SOURCE_CLASS,
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
    REPAIR_HISTORY_POLICIES_V1,
    generation_mode_for_condition,
)


Cluster3Condition: TypeAlias = Literal["P", "G+P", "C+P", "G+C+P"]

CLUSTER3_CONDITIONS: tuple[str, ...] = ("P", "G+P", "C+P", "G+C+P")
P_GENERATION_CONDITIONS: tuple[str, ...] = CLUSTER3_CONDITIONS

DEFAULT_P_REPAIR_BUDGET: int = 5
P_ELIGIBLE_FAILURE_CODES: frozenset[str] = frozenset({"F1_COMPILE"})
P_FEEDBACK_FORMAT_V1: str = "compile_error_template_v1"
P_HISTORY_POLICY_V1: str = LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
if P_HISTORY_POLICY_V1 not in REPAIR_HISTORY_POLICIES_V1:
    raise ValueError("P_HISTORY_POLICY_V1 must be a known repair history policy")
P_REPAIR_STOP_REASONS: frozenset[str] = frozenset(
    {
        "p_compile_repaired_then_success",
        "p_budget_exhausted",
        "p_compile_repaired_f2_observed",
        "p_post_compile_f3_observed",
        "p_f3_without_compile_evidence",
        "p_terminal_non_repairable",
        "p_not_applicable",
    }
)

_CLUSTER3_TO_CLUSTER2_GENERATION: dict[str, str] = {
    "P": "C",
    "C+P": "C",
    "G+P": "G+C",
    "G+C+P": "G+C",
}

_CLUSTER3_TO_CLUSTER2_REPAIR: dict[str, str] = {
    "C+P": "C",
    "G+C+P": "G+C",
}


def normalize_cluster3_condition(value: str) -> str:
    """Return a Cluster 3 condition or raise ``ValueError``."""

    if not isinstance(value, str):
        raise ValueError("condition must be a string")
    normalized = value.strip()
    if normalized not in CLUSTER3_CONDITIONS:
        raise ValueError(
            f"unsupported Cluster 3 condition {value!r}; "
            f"expected one of: {', '.join(CLUSTER3_CONDITIONS)}"
        )
    return cast(Cluster3Condition, normalized)


def source_class_for_cluster3_condition(condition: str) -> str:
    """Return the source class implied by a Cluster 3 condition."""

    normalize_cluster3_condition(condition)
    return GENERATED_SOURCE_CLASS


def generation_mode_for_cluster3_condition(condition: str) -> str:
    """Return the translated Cluster 2 generation mode for a Cluster 3 condition."""

    normalized = normalize_cluster3_condition(condition)
    return generation_mode_for_condition(_CLUSTER3_TO_CLUSTER2_GENERATION[normalized])
