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
    build_l1a_grammar_mode_cp_matrix,
    build_l1a_launcher_dry_plan,
    build_l1a_launcher_executable_plan,
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
