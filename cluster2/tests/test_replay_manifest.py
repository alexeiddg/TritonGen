"""Phase 0 tests for frozen replay-control manifest integrity helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST
from cluster2.replay.manifest import (
    artifact_for_replay_condition,
    load_frozen_cluster1_manifest,
    replay_seed_schedule_for_condition,
    selected_replay_control_artifact_ids,
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


def test_task_agnostic_replay_artifacts_use_task_agnostic_g_control() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    selected_ids = selected_replay_control_artifact_ids(
        manifest,
        grammar_variant="task_agnostic",
    )
    g = artifact_for_replay_condition(
        "G",
        manifest,
        grammar_variant="task_agnostic",
    )

    assert selected_ids == ("none_baseline_n20_l4", "g_task_agnostic_n5_l4_rerun")
    assert g.path == "outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl"
    assert g.grammar_active is True


def test_artifact_for_replay_condition_rejects_generated_conditions() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    with pytest.raises(ValueError, match="not a replay control"):
        artifact_for_replay_condition("C", manifest)


def test_replay_manifest_integrity_covers_equal_attempt_window() -> None:
    integrity = validate_replay_manifest_integrity(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    assert integrity.valid
    assert integrity.schema_version == 2
    assert len(integrity.coverage) == 18
    assert all(record.required_rows == 6 for record in integrity.coverage)
    assert all(record.observed_rows >= 6 for record in integrity.coverage)
    assert all(record.status == "ok" for record in integrity.coverage)
    assert integrity.seed_schedule_failures == ()
    assert integrity.artifact_hash_mismatches == ()


def test_task_agnostic_replay_integrity_blocks_paper_window_until_n20() -> None:
    development = validate_replay_manifest_integrity(
        DEFAULT_FROZEN_CLUSTER1_MANIFEST,
        required_attempts=5,
        grammar_variant="task_agnostic",
    )
    paper = validate_replay_manifest_integrity(
        DEFAULT_FROZEN_CLUSTER1_MANIFEST,
        required_attempts=20,
        grammar_variant="task_agnostic",
    )

    assert development.valid
    assert paper.valid is False
    assert {
        record.artifact_id
        for record in paper.coverage
        if record.status == "coverage_failure_missing_frozen_control"
    } == {"g_task_agnostic_n5_l4_rerun"}


def test_replay_seed_schedule_is_manifest_authoritative() -> None:
    schedule = replay_seed_schedule_for_condition(
        condition="none",
        kernel_class="elementwise",
        dtype="fp32",
        candidate_count=3,
        manifest_path=DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    )

    assert [entry.base_seed for entry in schedule] == [0, 1, 2]
    assert [entry.generation_seed for entry in schedule] == [0, 1, 2]
    assert {entry.prompt_sha256 for entry in schedule} == {
        "76eb9d064610e428095c402366771d6e6e42a19413815409a7bebb9e6f252109"
    }
    assert {entry.max_new_tokens for entry in schedule} == {512}


def test_selected_frozen_sidecar_contracts_record_seed_schedule() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)
    artifacts = {
        artifact["artifact_id"]: artifact
        for artifact in manifest["artifacts"]
    }

    for artifact_id in ("none_baseline_n20_l4", "g_template_upper_bound_n20_l4"):
        artifact = artifacts[artifact_id]
        sidecar = artifact["metadata_sidecar"]["content"]

        assert sidecar["seed_schedule"] == artifact["seed_schedule"]


def test_replay_manifest_integrity_rejects_full_schedule_corruption(
    tmp_path: Path,
) -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)
    artifact = manifest["artifacts"][0]
    for schedule in artifact["seed_schedule"]["records"]:
        if schedule["kernel_class"] == "elementwise" and schedule["dtype"] == "fp32":
            schedule["base_seeds"][10] = 999
            schedule["generation_seeds"][10] = 999
            line_number = schedule["line_numbers"][10]
            for record in artifact["row_records"]:
                if record["line_number"] == line_number:
                    record["base_seed"] = 999
                    record["generation_seed"] = 999
            break
    manifest_path = tmp_path / "corrupt_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    integrity = validate_replay_manifest_integrity(manifest_path)

    assert integrity.valid is False
    assert any(
        "none_baseline_n20_l4:elementwise:fp32:seed_schedule_not_dense"
        in failure
        for failure in integrity.seed_schedule_failures
    )
