"""Repair-history policy configuration helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from cluster2.constants import (
    AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
    AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    DEFAULT_REPAIR_HISTORY_POLICY_V1,
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
    REPAIR_HISTORY_POLICIES_V1,
    RepairHistoryPolicyV1,
)

from shared.repair_history.errors import (
    InvalidRepairHistoryConfigError,
    MixedHistoryPolicyError,
    UnsupportedHistoryPolicyError,
)


MissingPolicyArtifactKind: TypeAlias = Literal["known_legacy", "unknown"]
UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY = "unknown_legacy"


@dataclass(frozen=True)
class RepairHistoryConfig:
    """Validated local config for repair-history prompt rendering."""

    repair_history_policy: RepairHistoryPolicyV1 = DEFAULT_REPAIR_HISTORY_POLICY_V1
    max_prompt_chars: int = AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1
    include_latest_source: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.repair_history_policy, str):
            raise InvalidRepairHistoryConfigError(
                "repair_history_policy must be a string"
            )
        if self.repair_history_policy not in REPAIR_HISTORY_POLICIES_V1:
            raise UnsupportedHistoryPolicyError(
                f"unsupported repair_history_policy {self.repair_history_policy!r}"
            )
        if not isinstance(self.max_prompt_chars, int) or isinstance(
            self.max_prompt_chars,
            bool,
        ):
            raise InvalidRepairHistoryConfigError(
                "max_prompt_chars must be a positive int"
            )
        if self.max_prompt_chars <= 0:
            raise InvalidRepairHistoryConfigError(
                "max_prompt_chars must be a positive int"
            )
        if not isinstance(self.include_latest_source, bool):
            raise InvalidRepairHistoryConfigError(
                "include_latest_source must be a bool"
            )


def agentic_repair_history_config(
    *,
    max_prompt_chars: int = AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1,
    include_latest_source: bool = False,
) -> RepairHistoryConfig:
    """Return a validated opt-in agentic transcript config."""

    return RepairHistoryConfig(
        repair_history_policy=AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
        max_prompt_chars=max_prompt_chars,
        include_latest_source=include_latest_source,
    )


def should_render_agentic_transcript(config: RepairHistoryConfig) -> bool:
    """Return whether the config requests the agentic transcript prompt core."""

    return config.repair_history_policy == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1


def classify_history_policy_values(
    policy_values: Iterable[str | None],
    *,
    missing_policy_artifact_kind: MissingPolicyArtifactKind = "unknown",
) -> str:
    """Classify explicit, legacy-missing, unknown-missing, and mixed rows."""

    if not isinstance(missing_policy_artifact_kind, str) or (
        missing_policy_artifact_kind not in {"known_legacy", "unknown"}
    ):
        raise InvalidRepairHistoryConfigError(
            "missing_policy_artifact_kind must be known_legacy or unknown"
        )

    values = tuple(policy_values)
    explicit = tuple(value for value in values if value is not None)
    missing_count = len(values) - len(explicit)

    for value in explicit:
        if not isinstance(value, str):
            raise InvalidRepairHistoryConfigError(
                "repair_history_policy must be a string when present"
            )
        if value not in REPAIR_HISTORY_POLICIES_V1:
            raise UnsupportedHistoryPolicyError(
                f"unsupported repair_history_policy {value!r}"
            )

    unique = frozenset(explicit)
    if len(unique) > 1 or (explicit and missing_count):
        raise MixedHistoryPolicyError("mixed repair history policy values")

    if unique:
        return next(iter(unique))
    if missing_policy_artifact_kind == "known_legacy":
        return LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
    return UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY


def require_repair_history_policy(value: str) -> RepairHistoryPolicyV1:
    """Return a known policy name or raise a typed local error."""

    if not isinstance(value, str):
        raise InvalidRepairHistoryConfigError(
            "repair_history_policy must be a string"
        )
    if value not in REPAIR_HISTORY_POLICIES_V1:
        raise UnsupportedHistoryPolicyError(
            f"unsupported repair_history_policy {value!r}"
        )
    return cast(RepairHistoryPolicyV1, value)
