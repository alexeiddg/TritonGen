"""Phase 0 tests for frozen replay-control manifest integrity helpers."""

from __future__ import annotations

import pytest

from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST
from cluster2.replay.manifest import (
    artifact_for_replay_condition,
    load_frozen_cluster1_manifest,
    selected_template_control_artifact_ids,
    validate_replay_manifest_integrity,
)


def test_selected_template_replay_artifacts_are_locked() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    assert selected_template_control_artifact_ids(manifest) == (
        "none_baseline_n20_l4",
        "g_template_upper_bound_n20_l4",
    )


def test_artifact_for_replay_condition_returns_frozen_paths() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    none = artifact_for_replay_condition("none", manifest)
    g = artifact_for_replay_condition("G", manifest)

    assert none.path == "outputs/cluster1/baseline_repaired_l4_n20.jsonl"
    assert none.grammar_active is False
    assert g.path == "outputs/cluster1/final_g_l4_n20.jsonl"
    assert g.grammar_active is True


def test_artifact_for_replay_condition_rejects_generated_conditions() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    with pytest.raises(ValueError, match="not a replay control"):
        artifact_for_replay_condition("C", manifest)


def test_replay_manifest_integrity_covers_equal_attempt_window() -> None:
    integrity = validate_replay_manifest_integrity(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    assert integrity.valid
    assert integrity.schema_version == 1
    assert len(integrity.coverage) == 18
    assert all(record.required_rows == 6 for record in integrity.coverage)
    assert all(record.observed_rows >= 6 for record in integrity.coverage)
    assert all(record.status == "ok" for record in integrity.coverage)
    assert integrity.artifact_hash_mismatches == ()
