from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cluster3.planning.grammar_mode_matrix import (
    L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L1A_GRAMMAR_MODE_CP_SELECTOR,
    L1A_OBSERVABILITY_ROOT,
    L1A_OUTPUT_ROOT,
    L1A_SIGNED_AUTHORIZATION_PLACEHOLDER,
    L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_KNOWN_HIGH_COST_CELL_ID,
    L2B_N20_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    L2B_N20_OUTPUT_ROOT,
    L2B_N20_OBSERVABILITY_ROOT,
    L2B_N20_SELECTOR_PROFILE_ID,
    L2B_N20_SIGNATURE_STATUS,
    L2B_N20_SIGNED_AUTHORIZATION_TOKEN,
    L2B_N2_OUTPUT_ROOT,
    L2B_N2_OBSERVABILITY_ROOT,
    L2B_N2_SELECTOR_PROFILE_ID,
    L2B_N2_SIGNATURE_STATUS,
    L2B_N2_SIGNED_AUTHORIZATION_TOKEN,
    L2B_SLOW_CELL_STOP_CLASSIFICATION,
    L2B_TIMING_OBSERVABILITY_REQUIRED_DIAGNOSTICS,
    L2_OBSERVABILITY_ROOT,
    L2_OUTPUT_ROOT,
    L2_RUN_ID_PREFIX,
    L2_SIGNED_AUTHORIZATION_PLACEHOLDER,
    build_l1a_grammar_mode_cp_matrix,
    build_l1a_launcher_dry_plan,
    build_l1a_launcher_executable_plan,
    build_l2b_full_coverage_shard_plan,
    l2b_full_coverage_shard_ids,
    l2b_full_coverage_stage_spec,
)


def test_l1a_grammar_mode_cp_matrix_has_12_unique_cells() -> None:
    cells = build_l1a_grammar_mode_cp_matrix()

    assert len(cells) == 12
    assert len({cell.condition_name for cell in cells}) == 12
    assert len({cell.output_namespace_suffix for cell in cells}) == 12
    assert {
        cell.grammar_mode for cell in cells
    } == {"grammar_off", "template_upper_bound", "task_agnostic"}


def test_l1a_grammar_mode_cp_matrix_order_and_factor_cells() -> None:
    cells = build_l1a_grammar_mode_cp_matrix()

    assert [cell.condition_name for cell in cells] == [
        "grammar_off",
        "grammar_off+C",
        "grammar_off+P",
        "grammar_off+C+P",
        "template_upper_bound",
        "template_upper_bound+C",
        "template_upper_bound+P",
        "template_upper_bound+C+P",
        "task_agnostic",
        "task_agnostic+C",
        "task_agnostic+P",
        "task_agnostic+C+P",
    ]
    assert [cell.factor_cell for cell in cells] == [
        "none",
        "C",
        "P",
        "C+P",
        "G",
        "G+C",
        "G+P",
        "G+C+P",
        "G",
        "G+C",
        "G+P",
        "G+C+P",
    ]


def test_l1a_grammar_mode_cp_matrix_maps_grammar_paths_and_scopes() -> None:
    cells = build_l1a_grammar_mode_cp_matrix()
    by_name = {cell.condition_name: cell for cell in cells}

    off = by_name["grammar_off+P"]
    assert off.grammar_active is False
    assert off.grammar_variant is None
    assert off.grammar_path is None
    assert off.grammar_claim_scope is None
    assert "P loop eligible only for F1_COMPILE failures" in off.expected_eligibility_notes

    template = by_name["template_upper_bound+C"]
    assert template.grammar_active is True
    assert template.grammar_variant == "template_upper_bound"
    assert template.grammar_path == "cluster1/grammar/triton_kernel.gbnf"
    assert template.grammar_claim_scope == "diagnostic_non_primary"
    assert template.correctness_feedback_active is True

    task = by_name["task_agnostic+C+P"]
    assert task.grammar_active is True
    assert task.grammar_variant == "task_agnostic"
    assert task.grammar_path == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    assert task.grammar_claim_scope == "primary"
    assert task.compile_feedback_active is True


def test_l1a_launcher_dry_plan_has_12_selectable_cells() -> None:
    plan = build_l1a_launcher_dry_plan(repair_history_policy="agentic_transcript_v1")

    assert len(plan) == 12
    assert {cell.selector for cell in plan} == {L1A_GRAMMAR_MODE_CP_SELECTOR}
    assert len({cell.condition_name for cell in plan}) == 12
    assert len({cell.condition_id for cell in plan}) == 12
    assert len({cell.output_path for cell in plan}) == 12
    assert {cell.grammar_mode for cell in plan} == {
        "grammar_off",
        "template_upper_bound",
        "task_agnostic",
    }
    assert sum(not cell.compile_feedback_active for cell in plan) == 6
    assert {cell.execution_role for cell in plan} == {
        "no_p_control_cell",
        "p_enabled_generated_cell",
    }


def test_l1a_launcher_dry_plan_paths_use_l1a_namespace() -> None:
    plan = build_l1a_launcher_dry_plan(repair_history_policy="agentic_transcript_v1")

    for cell in plan:
        assert cell.output_path == f"{L1A_OUTPUT_ROOT}/{cell.condition_id}.jsonl"
        assert cell.content_hash_sidecar_path == (
            f"{L1A_OUTPUT_ROOT}/{cell.condition_id}.jsonl.hashes.json"
        )
        assert cell.observability_event_path == (
            f"{L1A_OBSERVABILITY_ROOT}/{cell.condition_id}.observability.jsonl"
        )
        assert cell.observability_summary_path == (
            f"{L1A_OBSERVABILITY_ROOT}/{cell.condition_id}.observability.summary.json"
        )
        assert cell.observability_hash_path == (
            f"{L1A_OBSERVABILITY_ROOT}/{cell.condition_id}.observability.jsonl.hashes.json"
        )
        assert cell.observability_run_id_suffix == cell.condition_id
        assert cell.condition_id in cell.observability_join_key
        assert cell.path_collision_policy == "fail_if_any_target_path_exists"


def test_l1a_launcher_dry_plan_records_grammar_hashes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_hash = hashlib.sha256(
        (repo_root / "cluster1/grammar/triton_kernel.gbnf").read_bytes()
    ).hexdigest()
    task_hash = hashlib.sha256(
        (repo_root / "cluster1/grammar/triton_kernel_agnostic.gbnf").read_bytes()
    ).hexdigest()

    by_id = {
        cell.condition_id: cell
        for cell in build_l1a_launcher_dry_plan(
            repair_history_policy="agentic_transcript_v1",
            repo_root=repo_root,
        )
    }

    assert by_id["grammar_off__c_off__p_off"].grammar_sha256 is None
    assert (
        by_id["template_upper_bound__c_off__p_on"].grammar_sha256 == template_hash
    )
    assert by_id["task_agnostic__c_on__p_on"].grammar_sha256 == task_hash


def test_l1a_launcher_dry_plan_can_select_one_cell() -> None:
    plan = build_l1a_launcher_dry_plan(
        cell_selector="task_agnostic__c_on__p_off",
        repair_history_policy="agentic_transcript_v1",
    )

    assert len(plan) == 1
    cell = plan[0]
    assert cell.condition_name == "task_agnostic+C"
    assert cell.factor_cell == "G+C"
    assert cell.compile_feedback_active is False
    assert cell.execution_role == "no_p_control_cell"
    assert cell.command_grammar_argument == "--grammar-variant task_agnostic"


def test_l1a_launcher_dry_plan_rejects_invalid_cell_selector() -> None:
    with pytest.raises(ValueError, match="grammar_mode_cell"):
        build_l1a_launcher_dry_plan(cell_selector="primary_grammar__c_on__p_off")


def test_l1a_launcher_executable_plan_has_12_selectable_cells() -> None:
    plan = build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1"
    )

    assert len(plan) == 12
    assert [cell.condition_id for cell in plan] == [
        cell.condition_id
        for cell in build_l1a_launcher_dry_plan(
            repair_history_policy="agentic_transcript_v1"
        )
    ]
    assert {cell.command_mode for cell in plan} == {"executable"}
    assert {cell.selector for cell in plan} == {L1A_GRAMMAR_MODE_CP_SELECTOR}
    assert {cell.support_status for cell in plan} == {
        L1A_EXECUTABLE_SELECTOR_SUPPORT_STATUS
    }
    assert {cell.path_collision_policy for cell in plan} == {
        "fail_if_any_target_path_exists"
    }
    assert sum(not cell.compile_feedback_active for cell in plan) == 6
    assert {cell.execution_role for cell in plan} == {
        "no_p_control_cell",
        "p_enabled_generated_cell",
    }


def test_l1a_launcher_executable_plan_commands_encode_paths_and_authorization() -> None:
    plan = build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1"
    )
    by_id = {cell.condition_id: cell for cell in plan}

    off = by_id["grammar_off__c_off__p_off"]
    assert "--dry-plan" not in off.command_selector
    assert "--grammar-variant" not in off.command_selector
    assert f"--grammar-mode-cell {off.condition_id}" in off.command_selector
    assert f"--output {off.output_path}" in off.command_selector
    assert f"--observability-output {off.observability_event_path}" in off.command_selector
    assert "--overwrite" in off.command_selector
    assert L1A_SIGNED_AUTHORIZATION_PLACEHOLDER in off.executable_command
    assert off.signed_authorization_placeholder == L1A_SIGNED_AUTHORIZATION_PLACEHOLDER
    assert off.execution_role == "no_p_control_cell"

    template = by_id["template_upper_bound__c_on__p_on"]
    assert "--grammar-variant template_upper_bound" in template.command_selector
    assert template.command_grammar_argument == "--grammar-variant template_upper_bound"
    assert template.grammar_path == "cluster1/grammar/triton_kernel.gbnf"

    task = by_id["task_agnostic__c_on__p_off"]
    assert "--grammar-variant task_agnostic" in task.command_selector
    assert task.grammar_path == "cluster1/grammar/triton_kernel_agnostic.gbnf"
    assert task.execution_role == "no_p_control_cell"


def test_l2_launcher_dry_plan_uses_n20_namespace_without_execution() -> None:
    plan = build_l1a_launcher_dry_plan(
        repair_history_policy="agentic_transcript_v1",
        output_root=L2_OUTPUT_ROOT,
        observability_root=L2_OBSERVABILITY_ROOT,
        run_id_prefix=L2_RUN_ID_PREFIX,
        scale_tier="paper",
        n=20,
    )

    assert len(plan) == 12
    assert [cell.condition_id for cell in plan] == [
        cell.condition_id
        for cell in build_l1a_launcher_dry_plan(
            repair_history_policy="agentic_transcript_v1"
        )
    ]
    assert {cell.command_mode for cell in plan} == {"dry_plan"}
    assert {cell.support_status for cell in plan} == {
        "DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION"
    }
    for cell in plan:
        assert cell.output_path == f"{L2_OUTPUT_ROOT}/{cell.condition_id}.jsonl"
        assert cell.observability_event_path == (
            f"{L2_OBSERVABILITY_ROOT}/{cell.condition_id}.observability.jsonl"
        )
        assert f"--grammar-mode-cell {cell.condition_id}" in cell.command_selector
        assert "--scale-tier paper" in cell.command_selector
        assert "--n 20" in cell.command_selector
        assert "--dry-plan" in cell.command_selector
        assert cell.path_collision_policy == "fail_if_any_target_path_exists"


def test_l2_launcher_executable_plan_commands_encode_signed_l2_placeholder() -> None:
    plan = build_l1a_launcher_executable_plan(
        repair_history_policy="agentic_transcript_v1",
        output_root=L2_OUTPUT_ROOT,
        observability_root=L2_OBSERVABILITY_ROOT,
        run_id_prefix=L2_RUN_ID_PREFIX,
        scale_tier="paper",
        n=20,
        signed_authorization_placeholder=L2_SIGNED_AUTHORIZATION_PLACEHOLDER,
        signed_authorization_option="--signed-l2-authorization",
        support_status=L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS,
    )
    by_id = {cell.condition_id: cell for cell in plan}

    assert len(plan) == 12
    assert {cell.support_status for cell in plan} == {
        L2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
    }
    assert sum(not cell.compile_feedback_active for cell in plan) == 6
    assert sum(cell.compile_feedback_active for cell in plan) == 6

    off = by_id["grammar_off__c_off__p_off"]
    assert "--signed-l2-authorization" in off.command_selector
    assert L2_SIGNED_AUTHORIZATION_PLACEHOLDER in off.command_selector
    assert "--scale-tier paper" in off.command_selector
    assert "--n 20" in off.command_selector
    assert "--grammar-variant" not in off.command_selector
    assert off.execution_role == "no_p_control_cell"

    template = by_id["template_upper_bound__c_on__p_on"]
    assert "--grammar-variant template_upper_bound" in template.command_selector
    assert template.execution_role == "p_enabled_generated_cell"

    task = by_id["task_agnostic__c_on__p_off"]
    assert "--grammar-variant task_agnostic" in task.command_selector
    assert task.execution_role == "no_p_control_cell"


def test_l2b_stage_specs_define_compressed_sharded_ladder() -> None:
    n2 = l2b_full_coverage_stage_spec(L2B_N2_SELECTOR_PROFILE_ID)
    n20 = l2b_full_coverage_stage_spec(L2B_N20_SELECTOR_PROFILE_ID)

    assert n2.rung == "L2b-2"
    assert n2.n == 2
    assert n2.total_shards == 9
    assert n2.rows_per_shard == 24
    assert n2.full_matrix_planned_rows == 216
    assert n2.output_root == L2B_N2_OUTPUT_ROOT
    assert n2.observability_root == L2B_N2_OBSERVABILITY_ROOT
    assert n2.runtime_execution_enabled is True
    assert n2.signed_authorization_available is True
    assert n2.signature_status == L2B_N2_SIGNATURE_STATUS
    assert n2.concurrency_limits["max_gpu_concurrency"] <= 4
    assert n2.concurrency_limits["max_container_concurrency"] <= 40
    assert n2.timing_observability["required_diagnostics"] == (
        L2B_TIMING_OBSERVABILITY_REQUIRED_DIAGNOSTICS
    )
    assert n2.timing_observability["performance_evidence_authorized"] is False
    assert n2.timing_observability["known_high_cost_cell"] == (
        L2B_KNOWN_HIGH_COST_CELL_ID
    )
    assert (
        n2.slow_cell_stop_policy["classification"]
        == L2B_SLOW_CELL_STOP_CLASSIFICATION
    )
    assert n2.slow_cell_stop_policy["automatic_retry_authorized"] is False
    assert n2.slow_cell_stop_policy["automatic_resume_authorized"] is False

    assert n20.rung == "L2b-4"
    assert n20.n == 20
    assert n20.total_shards == 9
    assert n20.rows_per_shard == 240
    assert n20.full_matrix_planned_rows == 2160
    assert n20.output_root == L2B_N20_OUTPUT_ROOT
    assert n20.observability_root == L2B_N20_OBSERVABILITY_ROOT
    assert n20.runtime_execution_enabled is True
    assert n20.signed_authorization_available is True
    assert n20.signature_status == L2B_N20_SIGNATURE_STATUS
    assert n20.concurrency_limits["max_gpu_concurrency"] <= 4
    assert n20.concurrency_limits["max_container_concurrency"] <= 40
    assert n20.concurrency_limits["wave_4_max_gpu_concurrency"] <= 2
    assert n20.concurrency_limits["wave_4_max_container_concurrency"] <= 20
    assert n20.timing_observability["required_diagnostics"] == (
        L2B_TIMING_OBSERVABILITY_REQUIRED_DIAGNOSTICS
    )
    assert n20.timing_observability["performance_evidence_authorized"] is False


def test_l2b_shard_ids_are_exact_kernel_dtype_tuples() -> None:
    assert l2b_full_coverage_shard_ids() == (
        "elementwise__fp32",
        "elementwise__fp16",
        "elementwise__bf16",
        "reduction__fp32",
        "reduction__fp16",
        "reduction__bf16",
        "matmul__fp32",
        "matmul__fp16",
        "matmul__bf16",
    )


def test_l2b_n2_shard_plan_uses_deterministic_namespaces() -> None:
    plan = build_l2b_full_coverage_shard_plan(
        stage_id=L2B_N2_SELECTOR_PROFILE_ID,
        shard_selector="elementwise__fp32",
        repair_history_policy="agentic_transcript_v1",
    )

    assert len(plan) == 1
    shard = plan[0]
    assert shard.shard_id == "elementwise__fp32"
    assert shard.kernel_class == "elementwise"
    assert shard.dtype_variant == "fp32"
    assert shard.planned_cells == 12
    assert shard.planned_rows == 24
    assert shard.output_namespace == f"{L2B_N2_OUTPUT_ROOT}/elementwise__fp32"
    assert (
        shard.artifact_namespace
        == f"{L2B_N2_OBSERVABILITY_ROOT}/elementwise__fp32"
    )
    assert shard.fail_if_any_target_path_exists is True
    assert shard.path_collision_policy == "fail_if_any_target_path_exists"
    assert shard.support_status == L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
    assert shard.output_paths["result_files"][0].startswith(
        f"{L2B_N2_OUTPUT_ROOT}/elementwise__fp32/"
    )
    assert shard.artifact_paths["observability_event_files"][0].startswith(
        f"{L2B_N2_OBSERVABILITY_ROOT}/elementwise__fp32/"
    )
    assert shard.artifact_paths["analysis_namespace_glob"].endswith(
        "/elementwise__fp32*"
    )
    assert shard.artifact_paths["reports_namespace_glob"].endswith(
        "/elementwise__fp32*"
    )
    assert shard.artifact_paths["billing_namespace_glob"].endswith(
        "/elementwise__fp32*"
    )
    assert "--l2b-stage l2b_n2_full_coverage" in shard.future_command
    assert "--l2b-shard-selector elementwise__fp32" in shard.future_command
    assert "--kernel-class elementwise" in shard.future_command
    assert "--dtypes fp32" in shard.future_command
    assert "--signed-l2b-authorization" in shard.future_command
    assert L2B_N2_SIGNED_AUTHORIZATION_TOKEN in shard.future_command
    assert shard.support_status == L2B_N2_EXECUTABLE_SELECTOR_SUPPORT_STATUS
    assert shard.timing_observability["scope"] == (
        "per_cell_and_per_shard_sidecar_metadata_only"
    )
    assert shard.timing_observability["performance_evidence_authorized"] is False
    assert shard.slow_cell_stop_policy["classification"] == (
        L2B_SLOW_CELL_STOP_CLASSIFICATION
    )
    assert shard.slow_cell_stop_policy["preserve_partial_shard_audit"] is True


def test_l2b_n2_shard_plan_supports_recovery_cell_subset() -> None:
    plan = build_l2b_full_coverage_shard_plan(
        stage_id=L2B_N2_SELECTOR_PROFILE_ID,
        shard_selector="reduction__fp16",
        cell_selector=(
            "task_agnostic__c_off__p_off",
            "task_agnostic__c_on__p_off",
            "task_agnostic__c_off__p_on",
            "task_agnostic__c_on__p_on",
        ),
        repair_history_policy="agentic_transcript_v1",
    )

    assert len(plan) == 1
    shard = plan[0]
    assert shard.shard_id == "reduction__fp16"
    assert shard.planned_cells == 4
    assert shard.planned_rows == 8
    assert "--l2b-recovery-cells task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on" in shard.future_command


def test_l2b_n2_shard_plan_rejects_recovery_cell_selector_duplicates() -> None:
    with pytest.raises(ValueError, match="duplicate selector"):
        build_l2b_full_coverage_shard_plan(
            stage_id=L2B_N2_SELECTOR_PROFILE_ID,
            shard_selector="reduction__fp16",
            cell_selector=("task_agnostic__c_on__p_off", "task_agnostic__c_on__p_off"),
            repair_history_policy="agentic_transcript_v1",
        )


def test_l2b_wave_selector_returns_bounded_shard_window() -> None:
    plan = build_l2b_full_coverage_shard_plan(
        stage_id=L2B_N20_SELECTOR_PROFILE_ID,
        shard_selector="wave:3:2",
        repair_history_policy="agentic_transcript_v1",
    )

    assert [shard.shard_id for shard in plan] == [
        "reduction__fp32",
        "reduction__fp16",
    ]
    assert {shard.planned_rows for shard in plan} == {240}
    for shard in plan:
        assert shard.output_namespace.startswith(L2B_N20_OUTPUT_ROOT + "/")
        assert shard.artifact_namespace.startswith(L2B_N20_OBSERVABILITY_ROOT + "/")
        assert shard.support_status == L2B_N20_EXECUTABLE_SELECTOR_SUPPORT_STATUS
        assert L2B_N20_SIGNED_AUTHORIZATION_TOKEN in shard.future_command
        assert "--overwrite" not in shard.future_command
        assert all("--overwrite" not in command for command in shard.cell_commands)


def test_l2b_wave_selector_rejects_unbounded_window() -> None:
    with pytest.raises(ValueError, match="within 9 shards"):
        build_l2b_full_coverage_shard_plan(
            stage_id=L2B_N20_SELECTOR_PROFILE_ID,
            shard_selector="wave:8:2",
        )
