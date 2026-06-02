"""Cluster 2 condition and routing constants.

This module is intentionally metadata-only. It does not import Modal, Torch,
Triton, transformers, xgrammar, or any generation/evaluation runtime.
"""

from __future__ import annotations

from typing import Literal, TypeAlias, cast


Cluster2Condition: TypeAlias = Literal["none", "G", "C", "G+C"]
Cluster2ReplayCondition: TypeAlias = Literal["none", "G"]
Cluster2GeneratedCondition: TypeAlias = Literal["C", "G+C"]
Cluster2SourceClass: TypeAlias = Literal["replay_control_row", "generated_row"]
Cluster2GenerationMode: TypeAlias = Literal[
    "replay_control",
    "new_c2_generation",
    "new_c2_generation_with_G_adapter",
]
RepairHistoryPolicyV1: TypeAlias = Literal[
    "last_attempt_only_v1",
    "agentic_transcript_v1",
]

CLUSTER2_CONDITIONS: tuple[Cluster2Condition, ...] = ("none", "G", "C", "G+C")
REPLAY_CONTROL_CONDITIONS: tuple[Cluster2ReplayCondition, ...] = ("none", "G")
NEW_GENERATION_CONDITIONS: tuple[Cluster2GeneratedCondition, ...] = ("C", "G+C")

REPLAY_CONTROL_SOURCE_CLASS: Cluster2SourceClass = "replay_control_row"
GENERATED_SOURCE_CLASS: Cluster2SourceClass = "generated_row"

REPLAY_CONTROL_GENERATION_MODE: Cluster2GenerationMode = "replay_control"
C_GENERATION_MODE: Cluster2GenerationMode = "new_c2_generation"
G_PLUS_C_GENERATION_MODE: Cluster2GenerationMode = "new_c2_generation_with_G_adapter"

DEFAULT_REPAIR_BUDGET = 5
DEFAULT_EQUAL_ATTEMPTS_N = DEFAULT_REPAIR_BUDGET + 1
LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1: RepairHistoryPolicyV1 = (
    "last_attempt_only_v1"
)
AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1: RepairHistoryPolicyV1 = (
    "agentic_transcript_v1"
)
REPAIR_HISTORY_POLICIES_V1: frozenset[RepairHistoryPolicyV1] = frozenset(
    {
        LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
        AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    }
)
DEFAULT_REPAIR_HISTORY_POLICY_V1: RepairHistoryPolicyV1 = (
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
)
AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1: int = 24000

# Raised to avoid budget-exhaustion confound for full launcher + kernel generations.
DEFAULT_MAX_NEW_TOKENS = 1536

DEFAULT_C2_MODAL_GENERATION_GPU = "L4"
DEFAULT_C2_MODAL_EVAL_GPU = "L4"

DEFAULT_FROZEN_CLUSTER1_MANIFEST = "cluster2/contracts/frozen_cluster1_artifacts_manifest.json"
FROZEN_NONE_REPLAY_ARTIFACT = "outputs/cluster1/baseline_repaired_l4_n20.jsonl"
FROZEN_G_REPLAY_ARTIFACT = "outputs/cluster1/final_g_l4_n20.jsonl"

DTYPE_NAMES: tuple[str, ...] = ("fp32", "fp16", "bf16")


def normalize_cluster2_condition(condition: str) -> Cluster2Condition:
    """Return a Cluster 2 condition or raise ``ValueError``."""

    if not isinstance(condition, str):
        raise TypeError("condition must be a string")
    normalized = condition.strip()
    if normalized not in CLUSTER2_CONDITIONS:
        raise ValueError(
            f"unsupported Cluster 2 condition {condition!r}; "
            f"expected one of: {', '.join(CLUSTER2_CONDITIONS)}"
        )
    return cast(Cluster2Condition, normalized)


def require_replay_control_condition(condition: str) -> Cluster2ReplayCondition:
    """Validate that ``condition`` is a replay-only Cluster 2 control."""

    normalized = normalize_cluster2_condition(condition)
    if normalized not in REPLAY_CONTROL_CONDITIONS:
        raise ValueError(
            f"condition {normalized!r} is not a replay control; "
            f"expected one of: {', '.join(REPLAY_CONTROL_CONDITIONS)}"
        )
    return cast(Cluster2ReplayCondition, normalized)


def require_generated_condition(condition: str) -> Cluster2GeneratedCondition:
    """Validate that ``condition`` is allowed to invoke new C2 generation."""

    normalized = normalize_cluster2_condition(condition)
    if normalized not in NEW_GENERATION_CONDITIONS:
        raise ValueError(
            f"condition {normalized!r} must not invoke C2 generation; "
            f"expected one of: {', '.join(NEW_GENERATION_CONDITIONS)}"
        )
    return cast(Cluster2GeneratedCondition, normalized)


def source_class_for_condition(condition: str) -> Cluster2SourceClass:
    """Return the C2 source class implied by a condition."""

    normalized = normalize_cluster2_condition(condition)
    if normalized in REPLAY_CONTROL_CONDITIONS:
        return REPLAY_CONTROL_SOURCE_CLASS
    return GENERATED_SOURCE_CLASS


def generation_mode_for_condition(condition: str) -> Cluster2GenerationMode:
    """Return the generation-mode sidecar value implied by a condition."""

    normalized = normalize_cluster2_condition(condition)
    if normalized in REPLAY_CONTROL_CONDITIONS:
        return REPLAY_CONTROL_GENERATION_MODE
    if normalized == "C":
        return C_GENERATION_MODE
    return G_PLUS_C_GENERATION_MODE


def generation_allowed_for_condition(condition: str) -> bool:
    """Return whether ``condition`` may call new Cluster 2 generation."""

    return normalize_cluster2_condition(condition) in NEW_GENERATION_CONDITIONS
