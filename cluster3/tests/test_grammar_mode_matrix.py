from __future__ import annotations

from cluster3.planning.grammar_mode_matrix import build_l1a_grammar_mode_cp_matrix


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
