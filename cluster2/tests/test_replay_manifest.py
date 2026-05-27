"""Phase 0 tests for frozen replay-control manifest integrity helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST
from cluster2.replay.manifest import (
    REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING,
    analyze_replay_grid_coverage,
    artifact_for_replay_condition,
    load_frozen_cluster1_manifest,
    replay_coverage_report_for_condition,
    replay_seed_schedule_for_condition,
    selected_replay_control_artifact_ids,
    selected_template_control_artifact_ids,
    validate_replay_manifest_integrity,
)


def test_selected_template_replay_artifacts_are_locked() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    assert selected_template_control_artifact_ids(manifest) == (
        "none_baseline_n20_l4",
        "g_template_upper_bound_current_pipeline_n20_l4",
    )


def test_artifact_for_replay_condition_returns_frozen_paths() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)

    none = artifact_for_replay_condition("none", manifest)
    g = artifact_for_replay_condition("G", manifest)

    assert none.path == "outputs/cluster1/baseline_repaired_l4_n20.jsonl"
    assert none.grammar_active is False
    assert g.artifact_id == "g_template_upper_bound_current_pipeline_n20_l4"
    assert g.path == (
        "outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl"
    )
    assert g.row_count == 180
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

    assert selected_ids == (
        "none_baseline_n20_l4",
        "g_task_agnostic_aligned_pipeline_n20_l4",
    )
    assert g.path == "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"
    assert g.row_count == 177
    assert g.grammar_active is True
    assert artifact_for_replay_condition("none", manifest).path == (
        "outputs/cluster1/baseline_repaired_l4_n20.jsonl"
    )


def test_task_agnostic_g_n20_manifest_records_skip_missing_policy() -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)
    artifacts = {artifact["artifact_id"]: artifact for artifact in manifest["artifacts"]}
    artifact = artifacts["g_task_agnostic_aligned_pipeline_n20_l4"]
    status = manifest["selected_controls"]["task_agnostic_g_status"]
    assessment = manifest["coverage_assessment"]

    assert artifact["path"] == (
        "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"
    )
    assert artifact["condition"] == "G"
    assert artifact["coverage_policy"] == REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING
    assert artifact["expected_n"] == 20
    assert artifact["intended_rows"] == 180
    assert artifact["observed_rows"] == 177
    assert status["available_task_agnostic_g_n20_replay_artifact_id"] == (
        "g_task_agnostic_aligned_pipeline_n20_l4"
    )
    assert status["coverage_policy"] == REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING
    assert status["observed_rows"] == 177
    assert status["intended_rows"] == 180
    assert "g_task_agnostic_n5_l4_rerun" not in json.dumps(
        assessment,
        sort_keys=True,
    )
    assert assessment["paper"]["coverage_failure_missing_frozen_control_count"] == 0
    assert assessment["paper"]["coverage_warning_skip_missing_count"] == 2
    assert assessment["paper"]["coverage_warnings"] == [
        {
            "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
            "condition": "G",
            "coverage_policy": REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING,
            "dtype": "fp32",
            "grammar_active": True,
            "kernel_class": "matmul",
            "missing_rows": 1,
            "missing_samples": [5],
            "observed_rows": 19,
            "required_rows": 20,
            "status": "coverage_warning_skip_missing",
        },
        {
            "artifact_id": "g_task_agnostic_aligned_pipeline_n20_l4",
            "condition": "G",
            "coverage_policy": REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING,
            "dtype": "bf16",
            "grammar_active": True,
            "kernel_class": "matmul",
            "missing_rows": 2,
            "missing_samples": [0, 18],
            "observed_rows": 18,
            "required_rows": 20,
            "status": "coverage_warning_skip_missing",
        },
    ]


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


def test_task_agnostic_replay_integrity_reports_partial_n20_grid() -> None:
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

    assert development.valid is False
    assert paper.valid is False
    assert any(
        "g_task_agnostic_aligned_pipeline_n20_l4:matmul:bf16:"
        "seed_schedule_not_dense"
        in failure
        for failure in paper.seed_schedule_failures
    )
    assert {
        record.artifact_id
        for record in paper.coverage
        if record.status == "coverage_failure_missing_frozen_control"
    } == {"g_task_agnostic_aligned_pipeline_n20_l4"}


def test_task_agnostic_g_n20_coverage_report_identifies_missing_matmul_rows() -> None:
    report = replay_coverage_report_for_condition(
        "G",
        manifest_path=DEFAULT_FROZEN_CLUSTER1_MANIFEST,
        grammar_variant="task_agnostic",
        expected_n=20,
    )

    assert report.replay_coverage_policy == REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING
    assert report.replay_expected_rows == 180
    assert report.replay_observed_rows == 177
    assert report.replay_coverage_complete is False
    assert [row.to_dict() for row in report.replay_missing_rows] == [
        {"kernel_class": "matmul", "dtype": "fp32", "sample_index": 5},
        {"kernel_class": "matmul", "dtype": "bf16", "sample_index": 0},
        {"kernel_class": "matmul", "dtype": "bf16", "sample_index": 18},
    ]
    assert report.replay_duplicate_rows == ()
    assert report.replay_unexpected_rows == ()
    assert report.replay_invalid_rows == ()


def test_task_agnostic_skip_policy_rejects_schedule_holes_not_reported_missing(
    tmp_path: Path,
) -> None:
    manifest = load_frozen_cluster1_manifest(DEFAULT_FROZEN_CLUSTER1_MANIFEST)
    artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["artifact_id"] == "g_task_agnostic_aligned_pipeline_n20_l4"
    )
    _drop_seed_schedule_entry(
        artifact,
        kernel_class="elementwise",
        dtype="fp32",
        base_seed=2,
    )
    manifest_path = tmp_path / "schedule_hole_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing_from_schedule"):
        replay_seed_schedule_for_condition(
            condition="G",
            kernel_class="elementwise",
            dtype="fp32",
            candidate_count=20,
            manifest_path=manifest_path,
            grammar_variant="task_agnostic",
            allow_incomplete=True,
        )


def test_coverage_report_surfaces_invalid_replay_identities() -> None:
    report = analyze_replay_grid_coverage(
        [
            {
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "generation_seed": 0,
                "line_number": 1,
            },
            {
                "kernel_class": "unsupported",
                "dtype": "fp32",
                "generation_seed": 0,
                "line_number": 2,
            },
            {
                "kernel_class": "reduction",
                "dtype": "unsupported",
                "generation_seed": 0,
                "line_number": 3,
            },
            {
                "kernel_class": "matmul",
                "dtype": "bf16",
                "generation_seed": "bad",
                "line_number": 4,
            },
            "not-a-row-object",
        ],
        artifact_id="test_artifact",
        condition="G",
        expected_n=1,
        coverage_policy=REPLAY_COVERAGE_POLICY_WARNING_SKIP_MISSING,
    )

    assert report.replay_observed_rows == 1
    assert report.replay_coverage_complete is False
    assert [row.to_dict() for row in report.replay_invalid_rows] == [
        {"row_index": 1, "line_number": 2, "reason": "invalid_kernel_class"},
        {"row_index": 2, "line_number": 3, "reason": "invalid_dtype"},
        {"row_index": 3, "line_number": 4, "reason": "invalid_sample_identity"},
        {"row_index": 4, "line_number": None, "reason": "row_not_object"},
    ]


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


def _drop_seed_schedule_entry(
    artifact: dict[str, object],
    *,
    kernel_class: str,
    dtype: str,
    base_seed: int,
) -> None:
    schedule = artifact["seed_schedule"]
    assert isinstance(schedule, dict)
    records = schedule["records"]
    assert isinstance(records, list)
    record = next(
        record
        for record in records
        if record["kernel_class"] == kernel_class and record["dtype"] == dtype
    )
    index = record["base_seeds"].index(base_seed)
    for key in (
        "base_seeds",
        "generation_seeds",
        "attempt_indexes",
        "generation_indexes",
        "line_numbers",
        "replay_pair_ids",
    ):
        record[key].pop(index)
    record["row_count"] -= 1
