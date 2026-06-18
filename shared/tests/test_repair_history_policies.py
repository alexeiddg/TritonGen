"""Tests for repair-history policy configuration."""

from __future__ import annotations

import pytest

from cluster2.constants import (
    AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
    DEFAULT_REPAIR_HISTORY_POLICY_V1,
    LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
)
from shared.repair_history.errors import (
    InvalidRepairHistoryConfigError,
    MixedHistoryPolicyError,
    UnsupportedHistoryPolicyError,
)
from shared.repair_history.policies import (
    UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY,
    RepairHistoryConfig,
    agentic_repair_history_config,
    classify_history_policy_values,
    require_repair_history_policy,
    should_render_agentic_transcript,
)


def test_repair_history_config_defaults_to_legacy_last_attempt_only() -> None:
    config = RepairHistoryConfig()

    assert config.repair_history_policy == DEFAULT_REPAIR_HISTORY_POLICY_V1
    assert config.repair_history_policy == LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
    assert config.max_prompt_chars == 24000
    assert config.include_latest_source is False
    assert should_render_agentic_transcript(config) is False


def test_agentic_config_is_explicit_opt_in() -> None:
    config = agentic_repair_history_config(include_latest_source=True)

    assert config.repair_history_policy == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1
    assert config.include_latest_source is True
    assert should_render_agentic_transcript(config) is True


def test_policy_config_rejects_unknown_policies() -> None:
    with pytest.raises(UnsupportedHistoryPolicyError) as exc_info:
        RepairHistoryConfig(repair_history_policy="future_policy_v9")  # type: ignore[arg-type]

    assert exc_info.value.error_code == "unsupported_history_policy"


@pytest.mark.parametrize("value", (["agentic_transcript_v1"], {"policy": "agentic_transcript_v1"}))
def test_policy_config_rejects_non_string_policy_values(value: object) -> None:
    with pytest.raises(InvalidRepairHistoryConfigError) as exc_info:
        RepairHistoryConfig(repair_history_policy=value)  # type: ignore[arg-type]

    assert exc_info.value.error_code == "invalid_repair_history_config"


@pytest.mark.parametrize("value", (["agentic_transcript_v1"], {"policy": "agentic_transcript_v1"}))
def test_policy_classification_rejects_non_string_policy_values(value: object) -> None:
    with pytest.raises(InvalidRepairHistoryConfigError) as exc_info:
        classify_history_policy_values([value])  # type: ignore[list-item]

    assert exc_info.value.error_code == "invalid_repair_history_config"


@pytest.mark.parametrize("value", (True, False))
def test_policy_config_rejects_bool_max_prompt_chars(value: bool) -> None:
    with pytest.raises(InvalidRepairHistoryConfigError):
        RepairHistoryConfig(max_prompt_chars=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", (0, -1))
def test_policy_config_rejects_non_positive_max_prompt_chars(value: int) -> None:
    with pytest.raises(InvalidRepairHistoryConfigError):
        RepairHistoryConfig(max_prompt_chars=value)


def test_policy_config_rejects_non_bool_include_latest_source() -> None:
    with pytest.raises(InvalidRepairHistoryConfigError):
        RepairHistoryConfig(include_latest_source="yes")  # type: ignore[arg-type]


def test_invalid_explicit_agentic_config_does_not_fallback_to_legacy() -> None:
    with pytest.raises(InvalidRepairHistoryConfigError):
        agentic_repair_history_config(max_prompt_chars=False)  # type: ignore[arg-type]


def test_require_repair_history_policy_returns_known_policy() -> None:
    assert (
        require_repair_history_policy(AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1)
        == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1
    )


@pytest.mark.parametrize("value", (["agentic_transcript_v1"], {"policy": "agentic_transcript_v1"}))
def test_require_repair_history_policy_rejects_non_string_values(value: object) -> None:
    with pytest.raises(InvalidRepairHistoryConfigError) as exc_info:
        require_repair_history_policy(value)  # type: ignore[arg-type]

    assert exc_info.value.error_code == "invalid_repair_history_config"


def test_policy_classification_rejects_non_string_missing_policy_artifact_kind() -> None:
    with pytest.raises(InvalidRepairHistoryConfigError) as exc_info:
        classify_history_policy_values(
            [None],
            missing_policy_artifact_kind=["unknown"],  # type: ignore[arg-type]
        )

    assert exc_info.value.error_code == "invalid_repair_history_config"


def test_policy_classification_covers_legacy_agentic_missing_and_mixed_rows() -> None:
    assert (
        classify_history_policy_values([LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1])
        == LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
    )
    assert (
        classify_history_policy_values([AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1])
        == AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1
    )
    assert (
        classify_history_policy_values(
            [None, None],
            missing_policy_artifact_kind="known_legacy",
        )
        == LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1
    )
    assert (
        classify_history_policy_values(
            [None],
            missing_policy_artifact_kind="unknown",
        )
        == UNKNOWN_LEGACY_REPAIR_HISTORY_POLICY
    )

    with pytest.raises(MixedHistoryPolicyError):
        classify_history_policy_values(
            [
                LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1,
                AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1,
            ]
        )
    with pytest.raises(MixedHistoryPolicyError):
        classify_history_policy_values([LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1, None])
    with pytest.raises(UnsupportedHistoryPolicyError):
        classify_history_policy_values(["not_a_policy"])
