"""Cluster 3 additive analyzer coverage."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from cluster3.results.dataclass import Cluster3EvalRow
from shared.analysis.factorial import (
    PAIRED_REPLAY_COMPARISONS,
    _ensure_cluster3_analysis_columns,
    analyze_factorial,
    factorial_summary,
    load_results,
    normalize_result_rows,
    paired_p_factor_summary,
)


PROMPT_SHA = "c" * 64


def test_analyzer_compile_feedback_alias_matches_perf_feedback() -> None:
    normalized = normalize_result_rows(_all_eight_rows())

    assert "perf_feedback_active" in normalized.columns
    assert "compile_feedback_active" in normalized.columns
    assert normalized["compile_feedback_active"].equals(
        normalized["perf_feedback_active"]
    )


def test_factorial_summary_keeps_perf_feedback_active_with_compile_alias() -> None:
    summary = factorial_summary(normalize_result_rows(_four_cell_rows()))

    assert "perf_feedback_active" in summary.columns
    assert "compile_feedback_active" in summary.columns


def test_analyzer_2x2_reproducible_without_cluster3_rows() -> None:
    first = analyze_factorial(_four_cell_rows(), bootstrap_samples=20, bootstrap_seed=7)
    second = analyze_factorial(_four_cell_rows(), bootstrap_samples=20, bootstrap_seed=7)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert json.dumps(first, sort_keys=True, indent=2) == LEGACY_2X2_GOLDEN_JSON
    assert _legacy_2x2_contract_snapshot(first) == {
        "top_level_keys": [
            "cell_summaries",
            "condition_rates",
            "diagnostics",
            "factorial_model",
            "metadata",
            "paired_comparisons",
            "paper_tables",
        ],
        "metadata_keys": [
            "analysis_label",
            "analysis_scope",
            "analyzer_version",
            "cells_missing",
            "cells_populated",
            "cells_status",
            "constants",
            "current_status_scope",
            "f3_eval_pipeline_policy",
            "f3_excluded_counts",
            "full_factorial_goal",
            "g_replay_coverage",
            "interpretation_flags",
            "metric_aliases",
            "metric_registry",
            "metric_registry_schema_version",
            "normalized_scale_tiers",
            "outcome_families",
            "outcome_family_schema_version",
            "p_cell_status",
            "paired_primary_comparisons",
            "primary_response_variable",
            "raw_scale_tiers_before_annotation",
            "registry_provenance",
            "repair_history_group_columns",
            "repair_history_groups",
            "repair_history_policies",
            "repair_history_policy_quarantine",
            "repair_history_policy_states",
            "reportable",
            "requested_scale_tier",
            "response_variable",
            "scale_tier_source",
            "scale_tier_sources",
            "scale_tiers",
            "scope_kind",
            "scope_statements",
            "secondary_response_variable",
        ],
        "metadata": {
            "analysis_label": "current 2² subset analysis over G and C",
            "analysis_scope": "primary_functional",
            "cells_missing": ["P", "G+P", "C+P", "G+C+P"],
            "cells_populated": ["none", "G", "C", "G+C"],
            "interpretation_flags": ["p_cells_not_populated"],
            "paired_primary_comparisons": [
                {"treatment_condition": "C", "control_condition": "none"},
                {"treatment_condition": "G+C", "control_condition": "G"},
            ],
            "reportable": True,
            "response_variable": "functional_success",
            "scale_tiers": ["paper"],
            "scope_kind": "temporary_2^2_subset",
        },
        "condition_rate_keys": [
            "compile_success_f3_excluded",
            "compile_success_matched_analysis_n",
            "compile_success_matched_analysis_rate",
            "compile_success_matched_analysis_successes",
            "compile_success_n",
            "compile_success_rate",
            "compile_success_successes",
            "compile_success_wilson_ci_95",
            "condition",
            "functional_success_n",
            "functional_success_rate",
            "functional_success_successes",
            "functional_success_wilson_ci_95",
        ],
        "condition_rates": {
            condition: {
                "compile_success_f3_excluded": 0,
                "compile_success_matched_analysis_n": 2,
                "compile_success_matched_analysis_rate": 1.0,
                "compile_success_matched_analysis_successes": 2,
                "compile_success_n": 2,
                "compile_success_rate": 1.0,
                "compile_success_successes": 2,
                "condition": condition,
                "functional_success_n": 2,
                "functional_success_rate": 0.5,
                "functional_success_successes": 1,
            }
            for condition in ("C", "G", "G+C", "none")
        },
        "paired_comparison_keys": [
            "absolute_lift",
            "bootstrap_samples",
            "bootstrap_seed",
            "cells_missing",
            "cells_populated",
            "ci_high",
            "ci_level",
            "ci_low",
            "comparison",
            "comparison_label",
            "comparison_role",
            "concordant_failure",
            "concordant_success",
            "condition_a",
            "condition_b",
            "control_condition",
            "control_rate",
            "discordant_control_only",
            "discordant_treatment_only",
            "interpretation_flags",
            "level_gate",
            "metric_current_status",
            "metric_display_name",
            "metric_gate",
            "metric_name",
            "metric_reportability",
            "missing_control_pairs",
            "missing_treatment_pairs",
            "multiple_testing_method",
            "n_pairs",
            "outcome_family",
            "p_value",
            "p_value_holm",
            "paired_analysis",
            "relative_lift",
            "response_variable",
            "significant_holm",
            "success_rate_a",
            "success_rate_b",
            "treatment_condition",
            "treatment_rate",
        ],
        "paired_comparisons": [
            {
                "comparison": "C vs none",
                "comparison_role": "primary",
                "condition_a": "none",
                "condition_b": "C",
                "control_condition": "none",
                "treatment_condition": "C",
                "n_pairs": 2,
                "success_rate_a": 0.5,
                "success_rate_b": 0.5,
                "absolute_lift": 0.0,
                "discordant_control_only": 1,
                "discordant_treatment_only": 1,
                "interpretation_flags": ["p_cells_not_populated"],
            },
            {
                "comparison": "G+C vs G",
                "comparison_role": "primary",
                "condition_a": "G",
                "condition_b": "G+C",
                "control_condition": "G",
                "treatment_condition": "G+C",
                "n_pairs": 2,
                "success_rate_a": 0.5,
                "success_rate_b": 0.5,
                "absolute_lift": 0.0,
                "discordant_control_only": 1,
                "discordant_treatment_only": 1,
                "interpretation_flags": ["p_cells_not_populated"],
            },
            {
                "comparison": "G vs none",
                "comparison_role": "secondary_diagnostic",
                "condition_a": "none",
                "condition_b": "G",
                "control_condition": "none",
                "treatment_condition": "G",
                "n_pairs": 2,
                "success_rate_a": 1.0,
                "success_rate_b": 1.0,
                "absolute_lift": 0.0,
                "discordant_control_only": 0,
                "discordant_treatment_only": 0,
                "interpretation_flags": [
                    "diagnostic_only",
                    "strict_surface_metric",
                    "p_cells_not_populated",
                ],
            },
            {
                "comparison": "G+C vs C",
                "comparison_role": "secondary_diagnostic",
                "condition_a": "C",
                "condition_b": "G+C",
                "control_condition": "C",
                "treatment_condition": "G+C",
                "n_pairs": 2,
                "success_rate_a": 1.0,
                "success_rate_b": 1.0,
                "absolute_lift": 0.0,
                "discordant_control_only": 0,
                "discordant_treatment_only": 0,
                "interpretation_flags": [
                    "diagnostic_only",
                    "strict_surface_metric",
                    "p_cells_not_populated",
                ],
            },
        ],
        "factorial_model_keys": [
            "control_terms",
            "controls",
            "formula",
            "interaction_additive_did",
            "interaction_logistic_ci_95",
            "interaction_logistic_coefficient",
            "iterations",
            "model_family",
            "model_fit_status",
            "model_type",
            "n_observations",
            "rank",
            "response_variable",
            "terms",
            "warnings",
        ],
        "factorial_model": {
            "controls": ["kernel_class", "dtype"],
            "formula": "functional_success ~ G + C + G:C + kernel_class + dtype",
            "interaction_additive_did": 0.0,
            "iterations": 1,
            "model_family": "binary_logistic_irls",
            "model_fit_status": "fit",
            "model_type": "reduced_four_cell",
            "n_observations": 8,
            "rank": 4,
            "response_variable": "functional_success",
            "term_names": ["G", "C", "G:C"],
            "warnings": ["p_cells_not_populated"],
        },
        "paper_tables": {
            "table_1_cell_summaries": {
                "rows": 16,
                "summary_levels": ["condition", "condition_kernel_dtype"],
                "response_variables": ["compile_success", "functional_success"],
            },
            "table_2_paired_comparisons": {
                "rows": 4,
                "comparisons": [
                    "C vs none",
                    "G+C vs G",
                    "G vs none",
                    "G+C vs C",
                ],
            },
            "table_3_factorial_terms": {
                "rows": 3,
                "terms": ["G", "C", "G:C"],
            },
        },
    }
    assert "three_way_interaction" not in first["metadata"]


def test_analyzer_metadata_paired_pairs_match_2x2_when_no_cluster3_rows() -> None:
    result = analyze_factorial(_four_cell_rows(), bootstrap_samples=20)

    assert result["metadata"]["paired_primary_comparisons"] == [
        {"treatment_condition": "C", "control_condition": "none"},
        {"treatment_condition": "G+C", "control_condition": "G"},
    ]


def test_analyzer_does_not_raise_on_missing_p_pair_when_only_2x2_populated() -> None:
    result = analyze_factorial(_four_cell_rows(), bootstrap_samples=20)

    assert result["metadata"]["scope_kind"] == "temporary_2^2_subset"


def test_analyzer_module_level_paired_replay_comparisons_unchanged() -> None:
    assert PAIRED_REPLAY_COMPARISONS == {"C": "none", "G+C": "G"}


def test_analyzer_loads_cluster3_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "cluster3.jsonl"
    path.write_text(json.dumps(_row("P", 0, functional_success=True)) + "\n")

    normalized = load_results(path)

    assert normalized["condition"].tolist() == ["P"]
    assert normalized["compile_feedback_active"].tolist() == [True]
    assert normalized["p_repair_attempted"].tolist() == [True]


def test_analyzer_rejects_non_p_row_with_p_fields() -> None:
    row = _row("none", 0, functional_success=False)
    row["p_repair_attempted"] = True

    with pytest.raises(ValueError, match="non-P analyzer row"):
        normalize_result_rows([row])


def test_analyzer_rejects_non_p_row_with_nested_p_attempt_count() -> None:
    row = _row(
        "C",
        0,
        functional_success=False,
        compile_success=False,
        failure_code="F1_COMPILE",
    )
    row["generated_metadata"]["p_repair_attempted"] = False
    row["generated_metadata"]["p_compile_repair_succeeded"] = False
    row["generated_metadata"]["p_repair_attempt_count"] = 1

    with pytest.raises(ValueError, match="non-P analyzer row"):
        normalize_result_rows([row])


@pytest.mark.parametrize("placement", ("top_level", "generated_metadata"))
def test_analyzer_rejects_non_p_row_with_p_repair_trace_summary(
    placement: str,
) -> None:
    row = _row(
        "C",
        0,
        functional_success=False,
        compile_success=False,
        failure_code="F1_COMPILE",
    )
    if placement == "top_level":
        row["p_repair_trace_summary"] = {"status": "unexpected_p_trace"}
    else:
        row["generated_metadata"]["p_repair_trace_summary"] = {
            "status": "unexpected_p_trace"
        }

    with pytest.raises(ValueError, match="non-P analyzer row"):
        normalize_result_rows([row])


def test_analyzer_handles_p_compile_repair_succeeded_with_f2_failure_code() -> None:
    row = _row(
        "P",
        0,
        functional_success=False,
        compile_success=True,
        failure_code="F2_NUMERIC_LARGE",
    )
    row["p_compile_repair_succeeded"] = True
    row["p_repair_changed_terminal_class"] = True

    normalized = normalize_result_rows([row])
    result = analyze_factorial(
        normalized,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert bool(normalized.loc[0, "p_compile_repair_succeeded"]) is True
    assert bool(normalized.loc[0, "p_repair_changed_terminal_class"]) is True
    assert result["condition_rates"]["P"]["compile_success_rate"] == 1.0
    assert result["condition_rates"]["P"]["functional_success_rate"] == 0.0


def test_analyzer_preserves_nested_p_repair_changed_terminal_class() -> None:
    row = _row(
        "P",
        0,
        functional_success=False,
        compile_success=True,
        failure_code="F2_NUMERIC_LARGE",
    )
    row.pop("p_repair_changed_terminal_class")
    row["generated_metadata"]["p_repair_changed_terminal_class"] = True

    normalized = normalize_result_rows([row])

    assert bool(normalized.loc[0, "p_repair_changed_terminal_class"]) is True


def test_analyzer_json_path_preserves_nested_p_trace_summary() -> None:
    row = _row(
        "P",
        0,
        functional_success=False,
        compile_success=False,
        failure_code="F1_COMPILE",
    )
    row.pop("p_repair_trace_summary")
    row["generated_metadata"]["p_repair_trace_summary"] = {"status": "nested"}

    normalized = normalize_result_rows([row])

    assert normalized["p_repair_trace_summary"].tolist() == [{"status": "nested"}]


def test_analyzer_json_path_preserves_nested_c_terminal_failure_code() -> None:
    row = _row(
        "C+P",
        0,
        functional_success=False,
        compile_success=True,
        failure_code="F2_NUMERIC_LARGE",
    )
    for column, value in (
        ("c_loop_fired", True),
        ("c_loop_source", "post_p_f2"),
        ("c_terminal_failure_code", "F2_NUMERIC_LARGE"),
    ):
        row.pop(column, None)
        row["generated_metadata"][column] = value

    normalized = normalize_result_rows([row])

    assert normalized["c_loop_fired"].tolist() == [True]
    assert normalized["c_loop_source"].tolist() == ["post_p_f2"]
    assert normalized["c_terminal_failure_code"].tolist() == ["F2_NUMERIC_LARGE"]


def test_analyzer_dataframe_path_preserves_nested_p_diagnostics() -> None:
    row = _row(
        "P",
        0,
        functional_success=True,
        compile_success=True,
        failure_code=None,
    )
    for column in (
        "p_repair_attempted",
        "p_compile_repair_succeeded",
        "p_repair_changed_terminal_class",
    ):
        row["generated_metadata"][column] = row.pop(column)
    row["dtype_original"] = row["dtype"]

    normalized = _ensure_cluster3_analysis_columns(pd.DataFrame([row]))

    assert normalized["p_repair_attempted"].tolist() == [True]
    assert normalized["p_compile_repair_succeeded"].tolist() == [True]
    assert normalized["p_repair_changed_terminal_class"].tolist() == [True]
    assert normalized["p_helped"].tolist() == [True]


def test_analyzer_dataframe_path_preserves_nested_scalar_diagnostics() -> None:
    row = _row(
        "C+P",
        0,
        functional_success=False,
        compile_success=True,
        failure_code="F2_NUMERIC_LARGE",
    )
    for column, value in (
        ("c_loop_fired", True),
        ("c_loop_source", "post_p_f2"),
        ("c_terminal_failure_code", "F2_NUMERIC_LARGE"),
        ("p_repair_trace_summary", {"status": "nested"}),
    ):
        row.pop(column, None)
        row["generated_metadata"][column] = value
    row["dtype_original"] = row["dtype"]

    normalized = _ensure_cluster3_analysis_columns(pd.DataFrame([row]))

    assert normalized["c_loop_fired"].tolist() == [True]
    assert normalized["c_loop_source"].tolist() == ["post_p_f2"]
    assert normalized["c_terminal_failure_code"].tolist() == ["F2_NUMERIC_LARGE"]
    assert normalized["p_repair_trace_summary"].tolist() == [{"status": "nested"}]


def test_analyzer_emits_paired_p_vs_none() -> None:
    rows = _four_cell_rows()
    rows.extend(_rows_for_condition("P", (True, False)))

    result = analyze_factorial(rows, bootstrap_samples=20)

    comparisons = {row["comparison"] for row in result["paired_comparisons"]}
    assert "P vs none" in comparisons


def test_p_vs_none_pairs_no_p_control_rows() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
        _row("none", 1, functional_success=True),
        _row("P", 1, functional_success=True),
    ]

    paired = paired_p_factor_summary(
        pd.DataFrame(rows),
        treatment_condition="P",
        control_condition="none",
        response_variable="functional_success",
    )

    assert len(paired) == 2
    assert set(pd.DataFrame(rows).query("condition == 'none'")["source_class"]) == {
        "replay_control_row"
    }


def test_gp_vs_g_pairs_replay_control_rows() -> None:
    paired = paired_p_factor_summary(
        pd.DataFrame(
            [
                _row("G", 0, functional_success=False),
                _row("G+P", 0, functional_success=True),
            ]
        ),
        treatment_condition="G+P",
        control_condition="G",
        response_variable="functional_success",
    )

    assert paired["paired_lift"].tolist() == [1]


def test_cp_vs_c_pairs_generated_cluster2_control_rows() -> None:
    paired = paired_p_factor_summary(
        pd.DataFrame(
            [
                _row("C", 0, functional_success=False),
                _row("C+P", 0, functional_success=True),
            ]
        ),
        treatment_condition="C+P",
        control_condition="C",
        response_variable="functional_success",
    )

    assert paired["control_condition"].tolist() == ["C"]
    assert paired["paired_lift"].tolist() == [1]


def test_gcp_vs_gc_pairs_generated_cluster2_control_rows() -> None:
    paired = paired_p_factor_summary(
        pd.DataFrame(
            [
                _row("G+C", 0, functional_success=False),
                _row("G+C+P", 0, functional_success=True),
            ]
        ),
        treatment_condition="G+C+P",
        control_condition="G+C",
        response_variable="functional_success",
    )

    assert paired["control_condition"].tolist() == ["G+C"]
    assert paired["paired_lift"].tolist() == [1]


def test_p_pair_summary_rejects_mixed_grammar_variant_unless_allowed() -> None:
    control = _row("G", 0, functional_success=False)
    treatment = _row("G+P", 0, functional_success=True)
    treatment["grammar_variant"] = "template_upper_bound"

    with pytest.raises(ValueError, match="mixed grammar variants"):
        paired_p_factor_summary(
            pd.DataFrame([control, treatment]),
            treatment_condition="G+P",
            control_condition="G",
            response_variable="functional_success",
        )

    paired = paired_p_factor_summary(
        pd.DataFrame([control, treatment]),
        treatment_condition="G+P",
        control_condition="G",
        response_variable="functional_success",
        allow_mixed_grammar_variant=True,
    )
    assert len(paired) == 1


def test_p_pair_summary_rejects_nested_mixed_grammar_variant() -> None:
    control = _row("G+C", 0, functional_success=False)
    treatment = _row("G+C+P", 0, functional_success=True)
    for row, grammar_variant in (
        (control, "task_agnostic"),
        (treatment, "template_upper_bound"),
    ):
        row.pop("grammar_variant", None)
        row.pop("grammar_claim_scope", None)
        row.setdefault("generated_metadata", {})["grammar_variant"] = grammar_variant
        row["generated_metadata"]["grammar_claim_scope"] = "primary"

    with pytest.raises(ValueError, match="mixed grammar variants"):
        paired_p_factor_summary(
            pd.DataFrame([control, treatment]),
            treatment_condition="G+C+P",
            control_condition="G+C",
            response_variable="functional_success",
        )


def test_analyzer_omits_p_pair_when_only_p_present() -> None:
    result = analyze_factorial(
        _rows_for_condition("P", (True, False)),
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert "P vs none" not in {
        row["comparison"] for row in result["paired_comparisons"]
    }
    assert "missing_p_pair_controls" in result["metadata"]["interpretation_flags"]


def test_analyzer_skips_p_pair_when_control_lacks_optional_sample_index() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
    ]
    rows[1]["generated_metadata"]["sample_index"] = 0

    result = analyze_factorial(
        rows,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert "P vs none" not in {
        row["comparison"] for row in result["paired_comparisons"]
    }
    warning = result["metadata"]["p_paired_control_warnings"][0]
    assert warning["reason"] == "control_pair_keys_missing"
    assert warning["missing_control_pairs"][0]["sample_index"] == 0


def test_analyzer_warns_for_p_pair_replay_pair_id_mismatch() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
    ]
    rows[1]["generated_metadata"]["replay_pair_id"] = "p-row-different-pair"

    result = analyze_factorial(
        rows,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert "P vs none" not in {
        row["comparison"] for row in result["paired_comparisons"]
    }
    warning = result["metadata"]["p_paired_control_warnings"][0]
    assert warning["reason"] == "control_pair_keys_missing"
    assert (
        warning["missing_control_pairs"][0]["replay_pair_id"]
        == "p-row-different-pair"
    )


def test_analyzer_warns_for_nested_p_pair_id_mismatch_in_dataframe() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
    ]
    for row in rows:
        row["dtype_original"] = row["dtype"]
    rows[1]["generated_metadata"]["replay_pair_id"] = "p-row-different-pair"

    result = analyze_factorial(
        pd.DataFrame(rows),
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert "P vs none" not in {
        row["comparison"] for row in result["paired_comparisons"]
    }
    assert "missing_p_pair_controls" in result["metadata"]["interpretation_flags"]
    warning = result["metadata"]["p_paired_control_warnings"][0]
    assert warning["reason"] == "control_pair_keys_missing"
    assert (
        warning["missing_control_pairs"][0]["replay_pair_id"]
        == "p-row-different-pair"
    )


def test_p_pair_summary_uses_nested_replay_pair_id_for_raw_dataframe() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
    ]
    rows[1]["generated_metadata"]["replay_pair_id"] = "p-row-different-pair"

    with pytest.raises(ValueError, match="unmatched seed rows"):
        paired_p_factor_summary(
            pd.DataFrame(rows),
            treatment_condition="P",
            control_condition="none",
            response_variable="functional_success",
        )


def test_p_pair_summary_strict_mismatch_sorts_missing_nullable_keys() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
        _row("P", 0, functional_success=False),
    ]
    rows[0]["sample_index"] = 2
    rows[2]["generated_metadata"]["sample_index"] = 1

    with pytest.raises(ValueError, match="unmatched seed rows"):
        paired_p_factor_summary(
            pd.DataFrame(rows),
            treatment_condition="P",
            control_condition="none",
            response_variable="functional_success",
        )


def test_p_pair_summary_canonicalizes_missing_nullable_sample_index() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("P", 0, functional_success=True),
        _row("none", 1, functional_success=False),
        _row("P", 1, functional_success=True),
    ]
    rows[2]["sample_index"] = 1
    rows[3]["generated_metadata"]["sample_index"] = 1

    paired = paired_p_factor_summary(
        pd.DataFrame(rows),
        treatment_condition="P",
        control_condition="none",
        response_variable="functional_success",
    )

    assert len(paired) == 2
    result = analyze_factorial(
        rows,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )
    assert "P vs none" in {
        row["comparison"] for row in result["paired_comparisons"]
    }
    assert "missing_p_pair_controls" not in result["metadata"]["interpretation_flags"]
    assert "p_paired_control_warnings" not in result["metadata"]


def test_analyzer_emits_additive_3way_interaction_when_all_eight_cells_populated() -> None:
    rows = [
        _row("none", 0, functional_success=False),
        _row("G", 0, functional_success=False),
        _row("C", 0, functional_success=False),
        _row("G+C", 0, functional_success=False),
        _row("P", 0, functional_success=True),
        _row("G+P", 0, functional_success=False),
        _row("C+P", 0, functional_success=False),
        _row("G+C+P", 0, functional_success=True),
    ]

    result = analyze_factorial(rows, bootstrap_samples=20)

    assert result["factorial_model"]["model_type"] == "full_eight_cell"
    assert result["factorial_model"]["three_way_interaction_additive"] == 2.0
    assert result["metadata"]["three_way_interaction"]["reportable"] is True


def test_smoke_full_eight_cells_do_not_report_three_way_claim() -> None:
    rows = _all_eight_rows()
    for row in rows:
        row["scale_tier"] = "smoke"

    result = analyze_factorial(
        rows,
        analysis_scope="l1a_grammar_mode_cp_smoke",
        bootstrap_samples=20,
    )

    assert result["metadata"]["reportable"] is False
    assert result["metadata"]["three_way_interaction"]["reportable"] is False
    assert (
        result["metadata"]["three_way_interaction"]["reason"]
        == "requires_reportable_primary_paper_scale_output"
    )
    assert result["factorial_model"]["three_way_interaction_reportable"] is False
    assert (
        "three_way_interaction_requires_reportable_primary_paper_scale_output"
        in result["factorial_model"]["warnings"]
    )


def test_l1b_dev_selector_scope_skips_missing_pair_metadata_without_reportable_claim() -> None:
    rows = _all_eight_rows()
    for row in rows:
        row["scale_tier"] = "development"
        metadata = row.get("generated_metadata")
        if isinstance(metadata, dict):
            metadata.pop("replay_control_condition", None)

    with pytest.raises(ValueError, match="missing paired replay metadata"):
        analyze_factorial(rows, bootstrap_samples=20)

    result = analyze_factorial(
        rows,
        analysis_scope="l1b_grammar_mode_cp_dev",
        bootstrap_samples=20,
    )

    assert result["metadata"]["reportable"] is False
    assert result["metadata"]["scale_tiers"] == ["development"]
    assert len(result["paired_comparisons"]) <= 6
    assert result["metadata"]["three_way_interaction"]["reportable"] is False
    assert (
        result["metadata"]["three_way_interaction"]["reason"]
        == "requires_reportable_primary_paper_scale_output"
    )
    assert result["factorial_model"]["three_way_interaction_reportable"] is False


def test_analyzer_metadata_paired_pairs_extend_when_all_eight_cells_present() -> None:
    result = analyze_factorial(_all_eight_rows(), bootstrap_samples=20)

    assert result["metadata"]["paired_primary_comparisons"] == [
        {"treatment_condition": "C", "control_condition": "none"},
        {"treatment_condition": "G+C", "control_condition": "G"},
        {"treatment_condition": "P", "control_condition": "none"},
        {"treatment_condition": "G+P", "control_condition": "G"},
        {"treatment_condition": "C+P", "control_condition": "C"},
        {"treatment_condition": "G+C+P", "control_condition": "G+C"},
    ]


def test_analyzer_p_helped_derived_conservatively() -> None:
    rows = [
        _row("P", 0, functional_success=True, failure_code=None),
        _row(
            "P",
            1,
            functional_success=False,
            compile_success=True,
            failure_code="F2_NUMERIC_LARGE",
        ),
    ]

    normalized = normalize_result_rows(rows)

    assert normalized["p_helped"].tolist() == [True, False]


def test_cluster3_row_does_not_carry_p_helped() -> None:
    assert "p_helped" not in {field.name for field in fields(Cluster3EvalRow)}


def test_analyzer_cluster3_f3_rows_follow_cluster2_denominator_policy() -> None:
    rows = [
        _row(
            "P",
            0,
            functional_success=False,
            compile_success=False,
            failure_code="F3_EVAL_PIPELINE",
        ),
        _row("P", 1, functional_success=True, compile_success=True, failure_code=None),
    ]

    result = analyze_factorial(
        rows,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=20,
    )

    assert result["metadata"]["f3_excluded_counts"] == {"P": 1}
    assert result["condition_rates"]["P"]["compile_success_n"] == 1
    assert result["condition_rates"]["P"]["compile_success_rate"] == 1.0


def _legacy_2x2_contract_snapshot(result: dict[str, object]) -> dict[str, object]:
    condition_rates = result["condition_rates"]
    paired_comparisons = result["paired_comparisons"]
    factorial_model = result["factorial_model"]
    paper_tables = result["paper_tables"]
    assert isinstance(condition_rates, dict)
    assert isinstance(paired_comparisons, list)
    assert isinstance(factorial_model, dict)
    assert isinstance(paper_tables, dict)

    rate_value_columns = (
        "compile_success_f3_excluded",
        "compile_success_matched_analysis_n",
        "compile_success_matched_analysis_rate",
        "compile_success_matched_analysis_successes",
        "compile_success_n",
        "compile_success_rate",
        "compile_success_successes",
        "condition",
        "functional_success_n",
        "functional_success_rate",
        "functional_success_successes",
    )
    paired_value_columns = (
        "comparison",
        "comparison_role",
        "condition_a",
        "condition_b",
        "control_condition",
        "treatment_condition",
        "n_pairs",
        "success_rate_a",
        "success_rate_b",
        "absolute_lift",
        "discordant_control_only",
        "discordant_treatment_only",
        "interpretation_flags",
    )
    table_1 = paper_tables["table_1_cell_summaries"]
    table_2 = paper_tables["table_2_paired_comparisons"]
    table_3 = paper_tables["table_3_factorial_terms"]
    assert isinstance(table_1, list)
    assert isinstance(table_2, list)
    assert isinstance(table_3, list)

    return {
        "top_level_keys": sorted(result),
        "metadata_keys": sorted(result["metadata"]),
        "metadata": {
            key: result["metadata"][key]
            for key in (
                "analysis_label",
                "analysis_scope",
                "cells_missing",
                "cells_populated",
                "interpretation_flags",
                "paired_primary_comparisons",
                "reportable",
                "response_variable",
                "scale_tiers",
                "scope_kind",
            )
        },
        "condition_rate_keys": sorted(next(iter(condition_rates.values()))),
        "condition_rates": {
            condition: {
                key: condition_rates[condition][key]
                for key in rate_value_columns
            }
            for condition in condition_rates
        },
        "paired_comparison_keys": sorted(paired_comparisons[0]),
        "paired_comparisons": [
            {key: row[key] for key in paired_value_columns}
            for row in paired_comparisons
        ],
        "factorial_model_keys": sorted(factorial_model),
        "factorial_model": {
            "controls": factorial_model["controls"],
            "formula": factorial_model["formula"],
            "interaction_additive_did": factorial_model["interaction_additive_did"],
            "iterations": factorial_model["iterations"],
            "model_family": factorial_model["model_family"],
            "model_fit_status": factorial_model["model_fit_status"],
            "model_type": factorial_model["model_type"],
            "n_observations": factorial_model["n_observations"],
            "rank": factorial_model["rank"],
            "response_variable": factorial_model["response_variable"],
            "term_names": [term["term"] for term in factorial_model["terms"]],
            "warnings": factorial_model["warnings"],
        },
        "paper_tables": {
            "table_1_cell_summaries": {
                "rows": len(table_1),
                "summary_levels": sorted(
                    {row["summary_level"] for row in table_1}
                ),
                "response_variables": sorted(
                    {row["response_variable"] for row in table_1}
                ),
            },
            "table_2_paired_comparisons": {
                "rows": len(table_2),
                "comparisons": [row["comparison"] for row in table_2],
            },
            "table_3_factorial_terms": {
                "rows": len(table_3),
                "terms": [row["term"] for row in table_3],
            },
        },
    }


def _four_cell_rows() -> list[dict[str, object]]:
    return [
        row
        for condition, successes in {
            "none": (False, True),
            "G": (False, True),
            "C": (True, False),
            "G+C": (True, False),
        }.items()
        for row in _rows_for_condition(condition, successes)
    ]


def _all_eight_rows() -> list[dict[str, object]]:
    return [
        row
        for condition, successes in {
            "none": (False, True),
            "G": (False, True),
            "C": (True, False),
            "G+C": (True, False),
            "P": (True, False),
            "G+P": (True, False),
            "C+P": (False, True),
            "G+C+P": (True, False),
        }.items()
        for row in _rows_for_condition(condition, successes)
    ]


def _rows_for_condition(
    condition: str,
    successes: tuple[bool, ...],
) -> list[dict[str, object]]:
    return [
        _row(condition, base_seed, functional_success=success)
        for base_seed, success in enumerate(successes)
    ]


def _row(
    condition: str,
    base_seed: int,
    *,
    functional_success: bool,
    compile_success: bool = True,
    failure_code: str | None = None,
) -> dict[str, object]:
    parts = set() if condition == "none" else set(condition.split("+"))
    row: dict[str, object] = {
        "condition": condition,
        "source_class": (
            "replay_control_row" if condition in {"none", "G"} else "generated_row"
        ),
        "kernel_class": "elementwise",
        "kernel_id": "relu",
        "kernel_name": "relu",
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": 0,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "failure_code": failure_code,
        "grammar_variant": "task_agnostic" if "G" in parts else None,
        "grammar_claim_scope": "primary" if "G" in parts else None,
        "scale_tier": "paper",
    }
    if condition in {"none", "G"}:
        row["replay_metadata"] = _pair_metadata(base_seed)
    else:
        row["generated_metadata"] = _generated_pair_metadata(
            base_seed,
            control_condition=_control_condition_for(condition),
        )
    if "P" in parts:
        row.update(
            {
                "p_repair_attempted": True,
                "p_compile_repair_succeeded": compile_success,
                "p_repair_changed_terminal_class": failure_code is None
                or failure_code.startswith("F2_"),
                "p_repair_trace_summary": {"status": "fixture"},
                "c_loop_fired": False,
                "c_loop_source": "none",
                "c_terminal_failure_code": None,
            }
        )
    return row


def _control_condition_for(condition: str) -> str:
    return {
        "C": "none",
        "G+C": "G",
        "P": "none",
        "G+P": "G",
        "C+P": "C",
        "G+C+P": "G+C",
    }[condition]


def _pair_metadata(base_seed: int) -> dict[str, object]:
    return {
        "replay_pair_id": f"elementwise:relu:fp32:{base_seed}",
        "replay_base_seed": base_seed,
        "replay_generation_seed": base_seed,
        "prompt_sha256": PROMPT_SHA,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": "unavailable_in_frozen_cluster1_artifact",
        "tokenizer_revision": "unavailable_in_frozen_cluster1_artifact",
        "temperature": 0.2,
        "max_new_tokens": 512,
    }


def _generated_pair_metadata(
    base_seed: int,
    *,
    control_condition: str,
) -> dict[str, object]:
    metadata = _pair_metadata(base_seed)
    metadata["generation_seed"] = base_seed
    metadata["replay_control_condition"] = control_condition
    return metadata


LEGACY_2X2_GOLDEN_JSON = r"""
{
  "cell_summaries": [
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "C",
      "condition_label": "C",
      "interpretation_flags": [],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "G",
      "condition_label": "task-agnostic G",
      "interpretation_flags": [],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "G+C",
      "condition_label": "task-agnostic G + C",
      "interpretation_flags": [],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "none",
      "condition_label": "none",
      "interpretation_flags": [],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "C",
      "condition_label": "C",
      "dtype": "fp32",
      "interpretation_flags": [],
      "kernel_class": "elementwise",
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "G",
      "condition_label": "task-agnostic G",
      "dtype": "fp32",
      "interpretation_flags": [],
      "kernel_class": "elementwise",
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "G+C",
      "condition_label": "task-agnostic G + C",
      "dtype": "fp32",
      "interpretation_flags": [],
      "kernel_class": "elementwise",
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "primary",
      "cell_status": "populated",
      "condition": "none",
      "condition_label": "none",
      "dtype": "fp32",
      "interpretation_flags": [],
      "kernel_class": "elementwise",
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "n_cells": 2,
      "outcome_family": "task_functional",
      "response_variable": "functional_success",
      "scale_tier": "paper",
      "success_rate": 0.5,
      "successes": 1,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "C",
      "condition_label": "C",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "G",
      "condition_label": "task-agnostic G",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "G+C",
      "condition_label": "task-agnostic G + C",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "none",
      "condition_label": "none",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "C",
      "condition_label": "C",
      "dtype": "fp32",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "kernel_class": "elementwise",
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "G",
      "condition_label": "task-agnostic G",
      "dtype": "fp32",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "kernel_class": "elementwise",
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "G+C",
      "condition_label": "task-agnostic G + C",
      "dtype": "fp32",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "kernel_class": "elementwise",
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition_kernel_dtype"
    },
    {
      "analysis_role": "secondary_diagnostic",
      "cell_status": "populated",
      "condition": "none",
      "condition_label": "none",
      "dtype": "fp32",
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric"
      ],
      "kernel_class": "elementwise",
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "n_cells": 2,
      "outcome_family": "structural_code_surface",
      "response_variable": "compile_success",
      "scale_tier": "paper",
      "success_rate": 1.0,
      "successes": 2,
      "summary_level": "condition_kernel_dtype"
    }
  ],
  "condition_rates": {
    "C": {
      "compile_success_f3_excluded": 0,
      "compile_success_matched_analysis_n": 2,
      "compile_success_matched_analysis_rate": 1.0,
      "compile_success_matched_analysis_successes": 2,
      "compile_success_n": 2,
      "compile_success_rate": 1.0,
      "compile_success_successes": 2,
      "compile_success_wilson_ci_95": [
        0.3423802275066532,
        1.0
      ],
      "condition": "C",
      "functional_success_n": 2,
      "functional_success_rate": 0.5,
      "functional_success_successes": 1,
      "functional_success_wilson_ci_95": [
        0.09453120573423074,
        0.9054687942657693
      ]
    },
    "G": {
      "compile_success_f3_excluded": 0,
      "compile_success_matched_analysis_n": 2,
      "compile_success_matched_analysis_rate": 1.0,
      "compile_success_matched_analysis_successes": 2,
      "compile_success_n": 2,
      "compile_success_rate": 1.0,
      "compile_success_successes": 2,
      "compile_success_wilson_ci_95": [
        0.3423802275066532,
        1.0
      ],
      "condition": "G",
      "functional_success_n": 2,
      "functional_success_rate": 0.5,
      "functional_success_successes": 1,
      "functional_success_wilson_ci_95": [
        0.09453120573423074,
        0.9054687942657693
      ]
    },
    "G+C": {
      "compile_success_f3_excluded": 0,
      "compile_success_matched_analysis_n": 2,
      "compile_success_matched_analysis_rate": 1.0,
      "compile_success_matched_analysis_successes": 2,
      "compile_success_n": 2,
      "compile_success_rate": 1.0,
      "compile_success_successes": 2,
      "compile_success_wilson_ci_95": [
        0.3423802275066532,
        1.0
      ],
      "condition": "G+C",
      "functional_success_n": 2,
      "functional_success_rate": 0.5,
      "functional_success_successes": 1,
      "functional_success_wilson_ci_95": [
        0.09453120573423074,
        0.9054687942657693
      ]
    },
    "none": {
      "compile_success_f3_excluded": 0,
      "compile_success_matched_analysis_n": 2,
      "compile_success_matched_analysis_rate": 1.0,
      "compile_success_matched_analysis_successes": 2,
      "compile_success_n": 2,
      "compile_success_rate": 1.0,
      "compile_success_successes": 2,
      "compile_success_wilson_ci_95": [
        0.3423802275066532,
        1.0
      ],
      "condition": "none",
      "functional_success_n": 2,
      "functional_success_rate": 0.5,
      "functional_success_successes": 1,
      "functional_success_wilson_ci_95": [
        0.09453120573423074,
        0.9054687942657693
      ]
    }
  },
  "diagnostics": {
    "analysis_label": "current 2\u00b2 subset analysis over G and C",
    "analysis_scope": "primary_functional",
    "current_status_scope": "This is a current-status scope statement, not a methodology realignment.",
    "feedback_activation": [
      {
        "c_factor_active": false,
        "c_feedback_eligibility_proxy_rows": 0,
        "c_feedback_eligible_rows": 0,
        "c_feedback_evidence_policy": "not_available",
        "c_feedback_loop_fired_rows": 0,
        "caveats": [],
        "condition": "none",
        "f0_rows": 0,
        "f1_rows": 0,
        "f2_rows": 0,
        "f3_rows": 0,
        "level1_compile_failure_rows": 0,
        "level2_reached_rows": 1,
        "n_rows": 2,
        "p_factor_active": false,
        "p_feedback_eligible_rows": 0,
        "p_feedback_evidence_policy": "not_available",
        "p_feedback_loop_fired_rows": 0
      },
      {
        "c_factor_active": false,
        "c_feedback_eligibility_proxy_rows": 0,
        "c_feedback_eligible_rows": 0,
        "c_feedback_evidence_policy": "not_available",
        "c_feedback_loop_fired_rows": 0,
        "caveats": [],
        "condition": "G",
        "f0_rows": 0,
        "f1_rows": 0,
        "f2_rows": 0,
        "f3_rows": 0,
        "level1_compile_failure_rows": 0,
        "level2_reached_rows": 1,
        "n_rows": 2,
        "p_factor_active": false,
        "p_feedback_eligible_rows": 0,
        "p_feedback_evidence_policy": "not_available",
        "p_feedback_loop_fired_rows": 0
      },
      {
        "c_factor_active": true,
        "c_feedback_eligibility_proxy_rows": 0,
        "c_feedback_eligible_rows": 0,
        "c_feedback_evidence_policy": "not_available",
        "c_feedback_loop_fired_rows": 0,
        "caveats": [
          "C feedback eligibility = 0/2 unless explicit F2 initial-failure evidence exists."
        ],
        "condition": "C",
        "f0_rows": 0,
        "f1_rows": 0,
        "f2_rows": 0,
        "f3_rows": 0,
        "level1_compile_failure_rows": 0,
        "level2_reached_rows": 1,
        "n_rows": 2,
        "p_factor_active": false,
        "p_feedback_eligible_rows": 0,
        "p_feedback_evidence_policy": "not_available",
        "p_feedback_loop_fired_rows": 0
      },
      {
        "c_factor_active": true,
        "c_feedback_eligibility_proxy_rows": 0,
        "c_feedback_eligible_rows": 0,
        "c_feedback_evidence_policy": "not_available",
        "c_feedback_loop_fired_rows": 0,
        "caveats": [
          "C feedback eligibility = 0/2 unless explicit F2 initial-failure evidence exists."
        ],
        "condition": "G+C",
        "f0_rows": 0,
        "f1_rows": 0,
        "f2_rows": 0,
        "f3_rows": 0,
        "level1_compile_failure_rows": 0,
        "level2_reached_rows": 1,
        "n_rows": 2,
        "p_factor_active": false,
        "p_feedback_eligible_rows": 0,
        "p_feedback_evidence_policy": "not_available",
        "p_feedback_loop_fired_rows": 0
      }
    ],
    "full_factorial_goal": "The full 2\u00b3 factorial over G, C, and P remains the defined project goal.",
    "grammar_acceptance_summary": [],
    "interpretation_flags": [
      "p_cells_not_populated"
    ],
    "level_reach_rates": [
      {
        "caveats": [
          "Level 0 syntax/surface pass is not inferred from missing failure codes.",
          "Cluster 1 replay controls may be compile-only in artifact-backed analyses; normalized Level 2 false values are unproven, not measured failure."
        ],
        "condition": "none",
        "level0_evidence_policy": "not_available",
        "level0_parse_surface_evaluable_rows": 0,
        "level0_parse_surface_pass_rate": null,
        "level0_parse_surface_pass_rows": 0,
        "level1_compile_launch_evaluable_rows": 2,
        "level1_compile_launch_reached_rate": 1.0,
        "level1_compile_launch_reached_rows": 2,
        "level1_evidence_policy": "derived_with_policy",
        "level2_correctness_evaluable_rows": 2,
        "level2_correctness_reached_rate": 0.5,
        "level2_correctness_reached_rows": 1,
        "level2_evidence_policy": "derived_with_policy",
        "n_rows": 2,
        "unavailable_reasons": [
          "level0_parse_surface_explicit_evidence_absent"
        ]
      },
      {
        "caveats": [
          "Level 0 syntax/surface pass is not inferred from missing failure codes.",
          "Cluster 1 replay controls may be compile-only in artifact-backed analyses; normalized Level 2 false values are unproven, not measured failure."
        ],
        "condition": "G",
        "level0_evidence_policy": "not_available",
        "level0_parse_surface_evaluable_rows": 0,
        "level0_parse_surface_pass_rate": null,
        "level0_parse_surface_pass_rows": 0,
        "level1_compile_launch_evaluable_rows": 2,
        "level1_compile_launch_reached_rate": 1.0,
        "level1_compile_launch_reached_rows": 2,
        "level1_evidence_policy": "derived_with_policy",
        "level2_correctness_evaluable_rows": 2,
        "level2_correctness_reached_rate": 0.5,
        "level2_correctness_reached_rows": 1,
        "level2_evidence_policy": "derived_with_policy",
        "n_rows": 2,
        "unavailable_reasons": [
          "level0_parse_surface_explicit_evidence_absent"
        ]
      },
      {
        "caveats": [
          "Level 0 syntax/surface pass is not inferred from missing failure codes."
        ],
        "condition": "C",
        "level0_evidence_policy": "not_available",
        "level0_parse_surface_evaluable_rows": 0,
        "level0_parse_surface_pass_rate": null,
        "level0_parse_surface_pass_rows": 0,
        "level1_compile_launch_evaluable_rows": 2,
        "level1_compile_launch_reached_rate": 1.0,
        "level1_compile_launch_reached_rows": 2,
        "level1_evidence_policy": "derived_with_policy",
        "level2_correctness_evaluable_rows": 2,
        "level2_correctness_reached_rate": 0.5,
        "level2_correctness_reached_rows": 1,
        "level2_evidence_policy": "derived_with_policy",
        "n_rows": 2,
        "unavailable_reasons": [
          "level0_parse_surface_explicit_evidence_absent"
        ]
      },
      {
        "caveats": [
          "Level 0 syntax/surface pass is not inferred from missing failure codes."
        ],
        "condition": "G+C",
        "level0_evidence_policy": "not_available",
        "level0_parse_surface_evaluable_rows": 0,
        "level0_parse_surface_pass_rate": null,
        "level0_parse_surface_pass_rows": 0,
        "level1_compile_launch_evaluable_rows": 2,
        "level1_compile_launch_reached_rate": 1.0,
        "level1_compile_launch_reached_rows": 2,
        "level1_evidence_policy": "derived_with_policy",
        "level2_correctness_evaluable_rows": 2,
        "level2_correctness_reached_rate": 0.5,
        "level2_correctness_reached_rows": 1,
        "level2_evidence_policy": "derived_with_policy",
        "n_rows": 2,
        "unavailable_reasons": [
          "level0_parse_surface_explicit_evidence_absent"
        ]
      }
    ],
    "metric_availability": {
      "benchmarkable_pass_at_k": {
        "availability_status": "future_only",
        "available": false,
        "computed_value_present": false,
        "current_status": "future_only",
        "level_gate": "level4_performance",
        "metric_gate": "future_performance",
        "metric_name": "benchmarkable_pass_at_k",
        "outcome_family": "benchmarkable_performance",
        "reason": "Metric requires a future Level 4 or benchmarkable/performance contract.",
        "reportability": "future_only",
        "reportable_output": true
      },
      "compile_pass_at_k": {
        "availability_status": "planned_deferred",
        "available": false,
        "computed_value_present": false,
        "current_status": "planned_deferred",
        "level_gate": "level1_compile_launch",
        "metric_gate": "compile_success",
        "metric_name": "compile_pass_at_k",
        "outcome_family": "structural_code_surface",
        "reason": "Metric is registered but intentionally not computed in S1.",
        "reportability": "diagnostic_only",
        "reportable_output": true
      },
      "correctness_pass_at_k": {
        "availability_status": "planned_deferred",
        "available": false,
        "computed_value_present": false,
        "current_status": "planned_deferred",
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "correctness_pass_at_k",
        "outcome_family": "task_functional",
        "reason": "Metric is registered but intentionally not computed in S1.",
        "reportability": "not_reportable",
        "reportable_output": true
      },
      "eval_set_success_rate": {
        "availability_status": "planned_deferred",
        "available": false,
        "computed_value_present": false,
        "current_status": "planned_deferred",
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "eval_set_success_rate",
        "outcome_family": "task_functional",
        "reason": "Metric is registered but intentionally not computed in S1.",
        "reportability": "diagnostic_only",
        "reportable_output": true
      },
      "grammar_valid_rate": {
        "availability_status": "not_available",
        "available": false,
        "computed_value_present": false,
        "current_status": "current_with_caveats",
        "level_gate": "level0_parse_surface",
        "metric_gate": "grammar_valid",
        "metric_name": "grammar_valid_rate",
        "outcome_family": "structural_code_surface",
        "reason": "Required compatible source evidence is absent from this input.",
        "reportability": "diagnostic_only",
        "reportable_output": true
      },
      "level1_compile_success_rate": {
        "availability_status": "available",
        "available": true,
        "computed_value_present": true,
        "current_status": "current_with_caveats",
        "level_gate": "level1_compile_launch",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "outcome_family": "structural_code_surface",
        "reason": "Required source evidence is present under current analyzer policy.",
        "reportability": "reportable_secondary",
        "reportable_output": true
      },
      "level2_functional_success_rate": {
        "availability_status": "available",
        "available": true,
        "computed_value_present": true,
        "current_status": "current_with_caveats",
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "outcome_family": "task_functional",
        "reason": "Required source evidence is present under current analyzer policy.",
        "reportability": "reportable_primary",
        "reportable_output": true
      },
      "repair_set_success_rate": {
        "availability_status": "planned_deferred",
        "available": false,
        "computed_value_present": false,
        "current_status": "planned_deferred",
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "repair_set_success_rate",
        "outcome_family": "task_functional",
        "reason": "Metric is registered but intentionally not computed in S1.",
        "reportability": "diagnostic_only",
        "reportable_output": true
      },
      "syntax_valid_rate": {
        "availability_status": "not_available_mixed_schema",
        "available": false,
        "computed_value_present": false,
        "current_status": "planned_deferred",
        "level_gate": "level0_parse_surface",
        "metric_gate": "syntax_valid",
        "metric_name": "syntax_valid_rate",
        "outcome_family": "structural_code_surface",
        "reason": "S1 does not compute mixed-schema syntax validity aggregates.",
        "reportability": "not_reportable",
        "reportable_output": true
      },
      "terminal_failure_distribution": {
        "availability_status": "not_available",
        "available": false,
        "computed_value_present": false,
        "current_status": "current_with_caveats",
        "level_gate": "failure_taxonomy",
        "metric_gate": "terminal_failure",
        "metric_name": "terminal_failure_distribution",
        "outcome_family": "mixed_diagnostic",
        "reason": "Required compatible source evidence is absent from this input.",
        "reportability": "diagnostic_only",
        "reportable_output": true
      }
    },
    "missing_cells": [
      "P",
      "G+P",
      "C+P",
      "G+C+P"
    ],
    "mixed_scale_policy": "reject_by_default",
    "mode_collapse_warning_rows": 0,
    "mode_collapse_warning_text": null,
    "p_cell_status": "P-containing cells are deferred for this iteration and are not included in current paper-claiming outputs.",
    "rejection_layer_breakdown": [],
    "response_variable": "functional_success",
    "rows_loaded": 8,
    "scope_kind": "temporary_2^2_subset",
    "scope_statements": [
      "The current iteration analyzes a temporary 2\u00b2 subset over G and C: none, G, C, and G+C.",
      "The full 2\u00b3 factorial over G, C, and P remains the defined project goal.",
      "P-containing cells are deferred for this iteration and are not included in current paper-claiming outputs.",
      "This is a current-status scope statement, not a methodology realignment."
    ],
    "secondary_compile_summary": {
      "missing_rows": 0,
      "response_variable": "compile_success",
      "status": "emitted",
      "total_rows": 8
    },
    "stop_reason_breakdown": [
      {
        "condition": "C",
        "count": 2,
        "stop_reason": "unknown"
      },
      {
        "condition": "G",
        "count": 2,
        "stop_reason": "unknown"
      },
      {
        "condition": "G+C",
        "count": 2,
        "stop_reason": "unknown"
      },
      {
        "condition": "none",
        "count": 2,
        "stop_reason": "unknown"
      }
    ],
    "unpaired_primary_comparisons_allowed": false
  },
  "factorial_model": {
    "control_terms": [],
    "controls": [
      "kernel_class",
      "dtype"
    ],
    "formula": "functional_success ~ G + C + G:C + kernel_class + dtype",
    "interaction_additive_did": 0.0,
    "interaction_logistic_ci_95": [
      -5.543615297398708,
      5.543615297398712
    ],
    "interaction_logistic_coefficient": 1.520579907027754e-15,
    "iterations": 1,
    "model_family": "binary_logistic_irls",
    "model_fit_status": "fit",
    "model_type": "reduced_four_cell",
    "n_observations": 8,
    "rank": 4,
    "response_variable": "functional_success",
    "terms": [
      {
        "ci_95": [
          -3.9199279690801077,
          3.919927969080106
        ],
        "coefficient": -7.6028995351387725e-16,
        "direction": "negative",
        "term": "G"
      },
      {
        "ci_95": [
          -3.919927969080108,
          3.9199279690801054
        ],
        "coefficient": -1.2632898076655715e-15,
        "direction": "negative",
        "term": "C"
      },
      {
        "ci_95": [
          -5.543615297398708,
          5.543615297398712
        ],
        "coefficient": 1.520579907027754e-15,
        "direction": "positive",
        "term": "G:C"
      }
    ],
    "warnings": [
      "p_cells_not_populated"
    ]
  },
  "metadata": {
    "analysis_label": "current 2\u00b2 subset analysis over G and C",
    "analysis_scope": "primary_functional",
    "analyzer_version": "factorial_alignment_v3_f3_eval_pipeline_policy",
    "cells_missing": [
      "P",
      "G+P",
      "C+P",
      "G+C+P"
    ],
    "cells_populated": [
      "none",
      "G",
      "C",
      "G+C"
    ],
    "cells_status": {
      "C": "populated",
      "C+P": "not_populated",
      "G": "populated",
      "G+C": "populated",
      "G+C+P": "not_populated",
      "G+P": "not_populated",
      "P": "not_populated",
      "none": "populated"
    },
    "constants": {
      "bootstrap_samples": 20,
      "bootstrap_seed": 7,
      "ci_level": 0.95,
      "multiple_testing_method": "holm",
      "significance_alpha": 0.05
    },
    "current_status_scope": "This is a current-status scope statement, not a methodology realignment.",
    "f3_eval_pipeline_policy": "F3_EVAL_PIPELINE rows excluded from compile_success rate calculations; treated as compile_success=False in matched-pair analysis when independent compile-pass evidence is absent.",
    "f3_excluded_counts": {},
    "full_factorial_goal": "The full 2\u00b3 factorial over G, C, and P remains the defined project goal.",
    "g_replay_coverage": "2/2 task-agnostic G replay rows; 0 rows missing. Policy: COVERAGE_WARNING_SKIP_MISSING.",
    "interpretation_flags": [
      "p_cells_not_populated"
    ],
    "metric_aliases": {
      "compile_launch_success_rate": "level1_compile_success_rate",
      "compile_success_rate": "level1_compile_success_rate",
      "evaluation_set_success_rate": "eval_set_success_rate",
      "failure_code_distribution": "terminal_failure_distribution",
      "functional_success_rate": "level2_functional_success_rate",
      "grammar_acceptance_rate": "grammar_valid_rate",
      "grammar_valid": "grammar_valid_rate",
      "level1_compile_pass_at_k": "compile_pass_at_k",
      "level2_correctness_pass_at_k": "correctness_pass_at_k",
      "level4_benchmarkable_pass_at_k": "benchmarkable_pass_at_k",
      "python_syntax_valid_rate": "syntax_valid_rate",
      "repair_success_rate": "repair_set_success_rate",
      "task_functional_success_rate": "level2_functional_success_rate",
      "terminal_failure_rate": "terminal_failure_distribution"
    },
    "metric_registry": {
      "benchmarkable_pass_at_k": {
        "aliases": [
          "level4_benchmarkable_pass_at_k"
        ],
        "analysis_role": "future_only",
        "attempt_policy": "Future-only; no S1 computation.",
        "caveat": "Future-only metric; no current computation or paper claim is authorized.",
        "cluster_owner": "cross_cluster",
        "current_status": "future_only",
        "denominator_policy": "Future-only; requires a later Level 4 performance contract.",
        "denominator_unit": "sample_group",
        "display_name": "Benchmarkable pass-at-k with future performance gate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not claim performance, timing, speedup, or benchmarkability from S1 metadata.",
          "Do not emit a current computed rate for this future-only metric."
        ],
        "level_gate": "level4_performance",
        "metric_gate": "future_performance",
        "metric_name": "benchmarkable_pass_at_k",
        "missing_policy": "Always unavailable in S1.",
        "numerator_policy": "Future sample groups that satisfy correctness and performance gates.",
        "outcome_family": "benchmarkable_performance",
        "reportability": "future_only",
        "required_source_fields": [
          "future_level4_performance_evidence"
        ],
        "response_variable": null,
        "schema_version": "metric_registry_v1",
        "scope": "future benchmarkable/performance work only"
      },
      "compile_pass_at_k": {
        "aliases": [
          "level1_compile_pass_at_k"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Requires explicit k/sample-group policy before computation.",
        "caveat": "Gate-specific pass-at-k metadata only; no current S1 aggregate is computed.",
        "cluster_owner": "cross_cluster",
        "current_status": "planned_deferred",
        "denominator_policy": "Deferred unless gate-specific sample-group counts exist.",
        "denominator_unit": "sample_group",
        "display_name": "Compile pass-at-k with Level 1 gate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not emit an ungated pass-at-k metric.",
          "Do not treat compile pass-at-k as task correctness."
        ],
        "level_gate": "level1_compile_launch",
        "metric_gate": "compile_success",
        "metric_name": "compile_pass_at_k",
        "missing_policy": "Not populated until explicit k-group evidence exists.",
        "numerator_policy": "Sample groups with at least one compile_success=True member.",
        "outcome_family": "structural_code_surface",
        "reportability": "diagnostic_only",
        "required_source_fields": [
          "sample_group",
          "compile_success"
        ],
        "response_variable": "compile_success",
        "schema_version": "metric_registry_v1",
        "scope": "planned gate-specific diagnostic"
      },
      "correctness_pass_at_k": {
        "aliases": [
          "level2_correctness_pass_at_k"
        ],
        "analysis_role": "primary",
        "attempt_policy": "Requires explicit k/sample-group policy before computation.",
        "caveat": "No current correctness pass-at-k aggregate is computed in S1.",
        "cluster_owner": "cross_cluster",
        "current_status": "planned_deferred",
        "denominator_policy": "Deferred until Level 2 sample groups exist.",
        "denominator_unit": "sample_group",
        "display_name": "Correctness pass-at-k with Level 2 gate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not emit an ungated pass-at-k metric.",
          "Do not compute from compile-only evidence."
        ],
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "correctness_pass_at_k",
        "missing_policy": "Not populated until explicit Level 2 sample groups exist.",
        "numerator_policy": "Sample groups with at least one functional_success=True member.",
        "outcome_family": "task_functional",
        "reportability": "not_reportable",
        "required_source_fields": [
          "sample_group",
          "functional_success"
        ],
        "response_variable": "functional_success",
        "schema_version": "metric_registry_v1",
        "scope": "planned deferred task/functional sample-group metric"
      },
      "eval_set_success_rate": {
        "aliases": [
          "evaluation_set_success_rate"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Requires explicit eval-set membership and attempt policy.",
        "caveat": "Deferred until explicit eval-set evidence exists.",
        "cluster_owner": "cross_cluster",
        "current_status": "planned_deferred",
        "denominator_policy": "Deferred unless explicit eval-set evidence is available.",
        "denominator_unit": "sample_group",
        "display_name": "Evaluation-set task success rate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not infer eval-set success from compile-only evidence.",
          "Do not describe as paper-scale evidence without an approved eval-set contract."
        ],
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "eval_set_success_rate",
        "missing_policy": "Not populated without explicit eval-set evidence.",
        "numerator_policy": "Eval-set rows with functional_success=True.",
        "outcome_family": "task_functional",
        "reportability": "diagnostic_only",
        "required_source_fields": [
          "eval_set_id",
          "functional_success"
        ],
        "response_variable": "functional_success",
        "schema_version": "metric_registry_v1",
        "scope": "planned eval-set diagnostic"
      },
      "grammar_valid_rate": {
        "aliases": [
          "grammar_acceptance_rate",
          "grammar_valid"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Diagnostic row-attempt summary; not a primary condition comparison.",
        "caveat": "Grammar validity is a structural diagnostic with schema-specific meaning.",
        "cluster_owner": "cluster1",
        "current_status": "current_with_caveats",
        "denominator_policy": "Rows with explicit grammar_valid evidence only.",
        "denominator_unit": "row_attempt",
        "display_name": "Grammar-valid rate",
        "evidence_policy": "explicit_only",
        "forbidden_interpretations": [
          "Do not treat grammar acceptance as Python syntax validity.",
          "Do not treat grammar acceptance as compile or functional success."
        ],
        "level_gate": "level0_parse_surface",
        "metric_gate": "grammar_valid",
        "metric_name": "grammar_valid_rate",
        "missing_policy": "Unavailable when grammar_valid evidence is absent.",
        "numerator_policy": "Rows where grammar_valid=True.",
        "outcome_family": "structural_code_surface",
        "reportability": "diagnostic_only",
        "required_source_fields": [
          "grammar_valid"
        ],
        "response_variable": null,
        "schema_version": "metric_registry_v1",
        "scope": "diagnostic grammar acceptance metadata where explicit evidence exists"
      },
      "level1_compile_success_rate": {
        "aliases": [
          "compile_success_rate",
          "compile_launch_success_rate"
        ],
        "analysis_role": "secondary_diagnostic",
        "attempt_policy": "Same attempt collapse as current compile_success analyzer summaries.",
        "caveat": "Compile success is structural/code-surface evidence, not task correctness.",
        "cluster_owner": "cross_cluster",
        "current_status": "current_with_caveats",
        "denominator_policy": "Condition denominator after current analyzer attempt collapse; F3_EVAL_PIPELINE rows remain excluded from compile-rate condition summaries under the existing policy.",
        "denominator_unit": "experimental_unit",
        "display_name": "Level 1 structural compile/launch success rate",
        "evidence_policy": "derived_with_policy",
        "forbidden_interpretations": [
          "Do not claim numerical correctness from compile success.",
          "Do not combine compile and functional success under an unlabeled pass metric."
        ],
        "level_gate": "level1_compile_launch",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "missing_policy": "Compile summaries are omitted when compile_success is unavailable.",
        "numerator_policy": "Experimental units with compile_success=True.",
        "outcome_family": "structural_code_surface",
        "reportability": "reportable_secondary",
        "required_source_fields": [
          "condition",
          "compile_success",
          "kernel_class",
          "kernel_id",
          "dtype",
          "base_seed"
        ],
        "response_variable": "compile_success",
        "schema_version": "metric_registry_v1",
        "scope": "secondary structural/code-surface diagnostic"
      },
      "level2_functional_success_rate": {
        "aliases": [
          "functional_success_rate",
          "task_functional_success_rate"
        ],
        "analysis_role": "primary",
        "attempt_policy": "Replay controls use attempt_index 0; generated rows collapse attempts by experimental unit using any success for the selected response variable.",
        "caveat": "Cluster 1 controls may be normalized false/unproven under current compile-only policy; this is not measured Level 2 failure.",
        "cluster_owner": "cross_cluster",
        "current_status": "current_with_caveats",
        "denominator_policy": "Current analyzer condition denominator after existing attempt collapse and F3 policy; paper-primary only when reportable four-cell paper-scale metadata is true.",
        "denominator_unit": "experimental_unit",
        "display_name": "Level 2 task/functional success rate",
        "evidence_policy": "derived_with_policy",
        "forbidden_interpretations": [
          "Do not treat Cluster 1 compile-only normalized false values as measured Level 2 failure.",
          "Do not infer performance or benchmarkability from this metric."
        ],
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "missing_policy": "Primary functional analysis rejects missing functional_success.",
        "numerator_policy": "Experimental units with functional_success=True.",
        "outcome_family": "task_functional",
        "reportability": "reportable_primary",
        "required_source_fields": [
          "condition",
          "functional_success",
          "kernel_class",
          "kernel_id",
          "dtype",
          "base_seed"
        ],
        "response_variable": "functional_success",
        "schema_version": "metric_registry_v1",
        "scope": "current primary 2^2 G/C subset when reportable; diagnostic otherwise"
      },
      "repair_set_success_rate": {
        "aliases": [
          "repair_success_rate"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Requires explicit repair-set membership and attempt policy.",
        "caveat": "Deferred until explicit repair-set evidence exists.",
        "cluster_owner": "cross_cluster",
        "current_status": "planned_deferred",
        "denominator_policy": "Deferred unless explicit repair-set evidence is available.",
        "denominator_unit": "matched_pair",
        "display_name": "Repair-set task success rate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not infer repair success from factor labels alone.",
          "Do not claim repair-memory lift from this deferred registry entry."
        ],
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "metric_name": "repair_set_success_rate",
        "missing_policy": "Not populated without explicit repair-set evidence.",
        "numerator_policy": "Repair-set rows with functional_success=True.",
        "outcome_family": "task_functional",
        "reportability": "diagnostic_only",
        "required_source_fields": [
          "repair_set_id",
          "functional_success"
        ],
        "response_variable": "functional_success",
        "schema_version": "metric_registry_v1",
        "scope": "planned or diagnostic repair-set evidence only"
      },
      "syntax_valid_rate": {
        "aliases": [
          "python_syntax_valid_rate"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Deferred; no mixed-schema aggregation in S1.",
        "caveat": "S1 intentionally does not compute mixed-schema syntax_valid_rate.",
        "cluster_owner": "cross_cluster",
        "current_status": "planned_deferred",
        "denominator_policy": "Deferred until every included row has compatible explicit syntax evidence and a shared syntax_valid_definition_id.",
        "denominator_unit": "row_attempt",
        "display_name": "Syntax-valid rate",
        "evidence_policy": "not_computed",
        "forbidden_interpretations": [
          "Do not infer syntax validity from missing failure codes.",
          "Do not infer syntax validity from compile_success.",
          "Do not merge grammar, parser, and semantic-validator evidence under one syntax label."
        ],
        "level_gate": "level0_parse_surface",
        "metric_gate": "syntax_valid",
        "metric_name": "syntax_valid_rate",
        "missing_policy": "Emit availability metadata instead of a mixed-schema rate.",
        "numerator_policy": "Rows with explicit Python syntax parse success.",
        "outcome_family": "structural_code_surface",
        "reportability": "not_reportable",
        "required_source_fields": [
          "syntax_valid",
          "syntax_valid_definition_id"
        ],
        "response_variable": null,
        "schema_version": "metric_registry_v1",
        "scope": "planned deferred metric registry entry only"
      },
      "terminal_failure_distribution": {
        "aliases": [
          "failure_code_distribution",
          "terminal_failure_rate"
        ],
        "analysis_role": "diagnostic",
        "attempt_policy": "Diagnostic row-attempt distribution; not a primary rate.",
        "caveat": "Failure distributions are explanatory diagnostics.",
        "cluster_owner": "cross_cluster",
        "current_status": "current_with_caveats",
        "denominator_policy": "Rows with terminal failure_code or terminal diagnostic evidence.",
        "denominator_unit": "row_attempt",
        "display_name": "Terminal failure distribution",
        "evidence_policy": "derived_with_policy",
        "forbidden_interpretations": [
          "Do not convert F3_EVAL_PIPELINE into functional success.",
          "Do not describe failure movement as a primary success metric."
        ],
        "level_gate": "failure_taxonomy",
        "metric_gate": "terminal_failure",
        "metric_name": "terminal_failure_distribution",
        "missing_policy": "Unavailable when terminal failure evidence is absent.",
        "numerator_policy": "Counts by terminal failure family or failure_code.",
        "outcome_family": "mixed_diagnostic",
        "reportability": "diagnostic_only",
        "required_source_fields": [
          "failure_code"
        ],
        "response_variable": null,
        "schema_version": "metric_registry_v1",
        "scope": "diagnostic failure movement and coverage explanation"
      }
    },
    "metric_registry_schema_version": "metric_registry_v1",
    "normalized_scale_tiers": [
      "paper"
    ],
    "outcome_families": {
      "benchmarkable_performance": {
        "display_name": "Benchmarkable/performance quality",
        "key": "benchmarkable_performance",
        "level_gates": [
          "level2_correctness",
          "level4_performance"
        ],
        "question_answered": "What would qualify a correct row for future performance evaluation?",
        "report_role": "future_only",
        "schema_version": "outcome_family_v1"
      },
      "mixed_diagnostic": {
        "display_name": "Mixed diagnostic",
        "key": "mixed_diagnostic",
        "level_gates": [
          "failure_taxonomy"
        ],
        "question_answered": "What explains failure movement or activation without being a primary outcome?",
        "report_role": "diagnostic_only",
        "schema_version": "outcome_family_v1"
      },
      "structural_code_surface": {
        "display_name": "Structural/code-surface quality",
        "key": "structural_code_surface",
        "level_gates": [
          "level0_parse_surface",
          "level1_compile_launch"
        ],
        "question_answered": "What improves generated-code structure, surface validity, grammar acceptance, compile, or launch?",
        "report_role": "secondary_or_diagnostic",
        "schema_version": "outcome_family_v1"
      },
      "task_functional": {
        "display_name": "Task/functional quality",
        "key": "task_functional",
        "level_gates": [
          "level2_correctness"
        ],
        "question_answered": "What improves numerical correctness under the Level 2 task harness?",
        "report_role": "primary_current_c_comparisons",
        "schema_version": "outcome_family_v1"
      }
    },
    "outcome_family_schema_version": "outcome_family_v1",
    "p_cell_status": "P-containing cells are deferred for this iteration and are not included in current paper-claiming outputs.",
    "paired_primary_comparisons": [
      {
        "control_condition": "none",
        "treatment_condition": "C"
      },
      {
        "control_condition": "G",
        "treatment_condition": "G+C"
      }
    ],
    "primary_response_variable": "functional_success",
    "raw_scale_tiers_before_annotation": [
      "paper"
    ],
    "registry_provenance": {
      "analyzer_version": "factorial_alignment_v3_f3_eval_pipeline_policy",
      "generated_by_activity": "analyze_factorial",
      "row_count": 8,
      "scale_tiers": [
        "paper"
      ],
      "schema_version": "registry_provenance_v1",
      "software_entity": "shared/analysis/factorial.py",
      "source_artifact_paths": [],
      "source_code": [
        "shared/analysis/factorial.py"
      ],
      "source_doc_versions": {
        "docs/14_structural_vs_task_outcome_reporting_plan.md": "0.1.1",
        "docs/17_structural_task_analyzer_metadata_implementation_spec.md": "0.1.3"
      },
      "source_docs": [
        "docs/14_structural_vs_task_outcome_reporting_plan.md",
        "docs/17_structural_task_analyzer_metadata_implementation_spec.md"
      ],
      "source_tests": [
        "shared/tests/test_factorial_analysis.py"
      ]
    },
    "repair_history_group_columns": [
      "repair_history_policy",
      "repair_prompt_template_version",
      "repair_prompt_renderer_version",
      "repair_max_prompt_chars",
      "repair_include_latest_source"
    ],
    "repair_history_groups": [
      {
        "n_rows": 8,
        "repair_history_policy": "last_attempt_only_v1",
        "repair_include_latest_source": null,
        "repair_max_prompt_chars": null,
        "repair_prompt_renderer_version": null,
        "repair_prompt_template_version": null
      }
    ],
    "repair_history_policies": [
      "last_attempt_only_v1"
    ],
    "repair_history_policy_quarantine": "reject_by_default",
    "repair_history_policy_states": [
      "known_legacy_missing_policy"
    ],
    "reportable": true,
    "requested_scale_tier": null,
    "response_variable": "functional_success",
    "scale_tier_source": "raw_row",
    "scale_tier_sources": [
      "raw_row"
    ],
    "scale_tiers": [
      "paper"
    ],
    "scope_kind": "temporary_2^2_subset",
    "scope_statements": [
      "The current iteration analyzes a temporary 2\u00b2 subset over G and C: none, G, C, and G+C.",
      "The full 2\u00b3 factorial over G, C, and P remains the defined project goal.",
      "P-containing cells are deferred for this iteration and are not included in current paper-claiming outputs.",
      "This is a current-status scope statement, not a methodology realignment."
    ],
    "secondary_response_variable": "compile_success"
  },
  "paired_comparisons": [
    {
      "absolute_lift": 0.0,
      "bootstrap_samples": 20,
      "bootstrap_seed": 7,
      "cells_missing": [
        "P",
        "G+P",
        "C+P",
        "G+C+P"
      ],
      "cells_populated": [
        "none",
        "G",
        "C",
        "G+C"
      ],
      "ci_high": 1.0,
      "ci_level": 0.95,
      "ci_low": -0.5249999999999996,
      "comparison": "C vs none",
      "comparison_label": "C vs none",
      "comparison_role": "primary",
      "concordant_failure": 0,
      "concordant_success": 0,
      "condition_a": "none",
      "condition_b": "C",
      "control_condition": "none",
      "control_rate": 0.5,
      "discordant_control_only": 1,
      "discordant_treatment_only": 1,
      "interpretation_flags": [
        "p_cells_not_populated"
      ],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "missing_control_pairs": [],
      "missing_treatment_pairs": [],
      "multiple_testing_method": "holm",
      "n_pairs": 2,
      "outcome_family": "task_functional",
      "p_value": 1.0,
      "p_value_holm": 1.0,
      "paired_analysis": true,
      "relative_lift": 0.0,
      "response_variable": "functional_success",
      "significant_holm": false,
      "success_rate_a": 0.5,
      "success_rate_b": 0.5,
      "treatment_condition": "C",
      "treatment_rate": 0.5
    },
    {
      "absolute_lift": 0.0,
      "bootstrap_samples": 20,
      "bootstrap_seed": 7,
      "cells_missing": [
        "P",
        "G+P",
        "C+P",
        "G+C+P"
      ],
      "cells_populated": [
        "none",
        "G",
        "C",
        "G+C"
      ],
      "ci_high": 1.0,
      "ci_level": 0.95,
      "ci_low": -0.5249999999999996,
      "comparison": "G+C vs G",
      "comparison_label": "task-agnostic G + C vs task-agnostic G",
      "comparison_role": "primary",
      "concordant_failure": 0,
      "concordant_success": 0,
      "condition_a": "G",
      "condition_b": "G+C",
      "control_condition": "G",
      "control_rate": 0.5,
      "discordant_control_only": 1,
      "discordant_treatment_only": 1,
      "interpretation_flags": [
        "p_cells_not_populated"
      ],
      "level_gate": "level2_correctness",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 2 task/functional success rate",
      "metric_gate": "functional_success",
      "metric_name": "level2_functional_success_rate",
      "metric_reportability": "reportable_primary",
      "missing_control_pairs": [],
      "missing_treatment_pairs": [],
      "multiple_testing_method": "holm",
      "n_pairs": 2,
      "outcome_family": "task_functional",
      "p_value": 1.0,
      "p_value_holm": 1.0,
      "paired_analysis": true,
      "relative_lift": 0.0,
      "response_variable": "functional_success",
      "significant_holm": false,
      "success_rate_a": 0.5,
      "success_rate_b": 0.5,
      "treatment_condition": "G+C",
      "treatment_rate": 0.5
    },
    {
      "absolute_lift": 0.0,
      "bootstrap_samples": 20,
      "bootstrap_seed": 7,
      "cells_missing": [
        "P",
        "G+P",
        "C+P",
        "G+C+P"
      ],
      "cells_populated": [
        "none",
        "G",
        "C",
        "G+C"
      ],
      "ci_high": 0.0,
      "ci_level": 0.95,
      "ci_low": 0.0,
      "comparison": "G vs none",
      "comparison_label": "task-agnostic G vs none",
      "comparison_role": "secondary_diagnostic",
      "concordant_failure": 0,
      "concordant_success": 2,
      "condition_a": "none",
      "condition_b": "G",
      "control_condition": "none",
      "control_rate": 1.0,
      "discordant_control_only": 0,
      "discordant_treatment_only": 0,
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric",
        "p_cells_not_populated"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "missing_control_pairs": [],
      "missing_treatment_pairs": [],
      "multiple_testing_method": "holm",
      "n_pairs": 2,
      "outcome_family": "structural_code_surface",
      "p_value": 1.0,
      "p_value_holm": 1.0,
      "paired_analysis": true,
      "relative_lift": 0.0,
      "response_variable": "compile_success",
      "significant_holm": false,
      "success_rate_a": 1.0,
      "success_rate_b": 1.0,
      "treatment_condition": "G",
      "treatment_rate": 1.0
    },
    {
      "absolute_lift": 0.0,
      "bootstrap_samples": 20,
      "bootstrap_seed": 7,
      "cells_missing": [
        "P",
        "G+P",
        "C+P",
        "G+C+P"
      ],
      "cells_populated": [
        "none",
        "G",
        "C",
        "G+C"
      ],
      "ci_high": 0.0,
      "ci_level": 0.95,
      "ci_low": 0.0,
      "comparison": "G+C vs C",
      "comparison_label": "task-agnostic G + C vs C",
      "comparison_role": "secondary_diagnostic",
      "concordant_failure": 0,
      "concordant_success": 2,
      "condition_a": "C",
      "condition_b": "G+C",
      "control_condition": "C",
      "control_rate": 1.0,
      "discordant_control_only": 0,
      "discordant_treatment_only": 0,
      "interpretation_flags": [
        "diagnostic_only",
        "strict_surface_metric",
        "p_cells_not_populated"
      ],
      "level_gate": "level1_compile_launch",
      "metric_current_status": "current_with_caveats",
      "metric_display_name": "Level 1 structural compile/launch success rate",
      "metric_gate": "compile_success",
      "metric_name": "level1_compile_success_rate",
      "metric_reportability": "reportable_secondary",
      "missing_control_pairs": [],
      "missing_treatment_pairs": [],
      "multiple_testing_method": "holm",
      "n_pairs": 2,
      "outcome_family": "structural_code_surface",
      "p_value": 1.0,
      "p_value_holm": 1.0,
      "paired_analysis": true,
      "relative_lift": 0.0,
      "response_variable": "compile_success",
      "significant_holm": false,
      "success_rate_a": 1.0,
      "success_rate_b": 1.0,
      "treatment_condition": "G+C",
      "treatment_rate": 1.0
    }
  ],
  "paper_tables": {
    "table_1_cell_summaries": [
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "C",
        "condition_label": "C",
        "interpretation_flags": [],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "G",
        "condition_label": "task-agnostic G",
        "interpretation_flags": [],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "G+C",
        "condition_label": "task-agnostic G + C",
        "interpretation_flags": [],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "none",
        "condition_label": "none",
        "interpretation_flags": [],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "C",
        "condition_label": "C",
        "dtype": "fp32",
        "interpretation_flags": [],
        "kernel_class": "elementwise",
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "G",
        "condition_label": "task-agnostic G",
        "dtype": "fp32",
        "interpretation_flags": [],
        "kernel_class": "elementwise",
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "G+C",
        "condition_label": "task-agnostic G + C",
        "dtype": "fp32",
        "interpretation_flags": [],
        "kernel_class": "elementwise",
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "primary",
        "cell_status": "populated",
        "condition": "none",
        "condition_label": "none",
        "dtype": "fp32",
        "interpretation_flags": [],
        "kernel_class": "elementwise",
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "n_cells": 2,
        "outcome_family": "task_functional",
        "response_variable": "functional_success",
        "scale_tier": "paper",
        "success_rate": 0.5,
        "successes": 1,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "C",
        "condition_label": "C",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "G",
        "condition_label": "task-agnostic G",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "G+C",
        "condition_label": "task-agnostic G + C",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "none",
        "condition_label": "none",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "C",
        "condition_label": "C",
        "dtype": "fp32",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "kernel_class": "elementwise",
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "G",
        "condition_label": "task-agnostic G",
        "dtype": "fp32",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "kernel_class": "elementwise",
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "G+C",
        "condition_label": "task-agnostic G + C",
        "dtype": "fp32",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "kernel_class": "elementwise",
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition_kernel_dtype"
      },
      {
        "analysis_role": "secondary_diagnostic",
        "cell_status": "populated",
        "condition": "none",
        "condition_label": "none",
        "dtype": "fp32",
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric"
        ],
        "kernel_class": "elementwise",
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "n_cells": 2,
        "outcome_family": "structural_code_surface",
        "response_variable": "compile_success",
        "scale_tier": "paper",
        "success_rate": 1.0,
        "successes": 2,
        "summary_level": "condition_kernel_dtype"
      }
    ],
    "table_2_paired_comparisons": [
      {
        "absolute_lift": 0.0,
        "bootstrap_samples": 20,
        "bootstrap_seed": 7,
        "cells_missing": [
          "P",
          "G+P",
          "C+P",
          "G+C+P"
        ],
        "cells_populated": [
          "none",
          "G",
          "C",
          "G+C"
        ],
        "ci_high": 1.0,
        "ci_level": 0.95,
        "ci_low": -0.5249999999999996,
        "comparison": "C vs none",
        "comparison_label": "C vs none",
        "comparison_role": "primary",
        "concordant_failure": 0,
        "concordant_success": 0,
        "condition_a": "none",
        "condition_b": "C",
        "control_condition": "none",
        "control_rate": 0.5,
        "discordant_control_only": 1,
        "discordant_treatment_only": 1,
        "interpretation_flags": [
          "p_cells_not_populated"
        ],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "missing_control_pairs": [],
        "missing_treatment_pairs": [],
        "multiple_testing_method": "holm",
        "n_pairs": 2,
        "outcome_family": "task_functional",
        "p_value": 1.0,
        "p_value_holm": 1.0,
        "paired_analysis": true,
        "relative_lift": 0.0,
        "response_variable": "functional_success",
        "significant_holm": false,
        "success_rate_a": 0.5,
        "success_rate_b": 0.5,
        "treatment_condition": "C",
        "treatment_rate": 0.5
      },
      {
        "absolute_lift": 0.0,
        "bootstrap_samples": 20,
        "bootstrap_seed": 7,
        "cells_missing": [
          "P",
          "G+P",
          "C+P",
          "G+C+P"
        ],
        "cells_populated": [
          "none",
          "G",
          "C",
          "G+C"
        ],
        "ci_high": 1.0,
        "ci_level": 0.95,
        "ci_low": -0.5249999999999996,
        "comparison": "G+C vs G",
        "comparison_label": "task-agnostic G + C vs task-agnostic G",
        "comparison_role": "primary",
        "concordant_failure": 0,
        "concordant_success": 0,
        "condition_a": "G",
        "condition_b": "G+C",
        "control_condition": "G",
        "control_rate": 0.5,
        "discordant_control_only": 1,
        "discordant_treatment_only": 1,
        "interpretation_flags": [
          "p_cells_not_populated"
        ],
        "level_gate": "level2_correctness",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 2 task/functional success rate",
        "metric_gate": "functional_success",
        "metric_name": "level2_functional_success_rate",
        "metric_reportability": "reportable_primary",
        "missing_control_pairs": [],
        "missing_treatment_pairs": [],
        "multiple_testing_method": "holm",
        "n_pairs": 2,
        "outcome_family": "task_functional",
        "p_value": 1.0,
        "p_value_holm": 1.0,
        "paired_analysis": true,
        "relative_lift": 0.0,
        "response_variable": "functional_success",
        "significant_holm": false,
        "success_rate_a": 0.5,
        "success_rate_b": 0.5,
        "treatment_condition": "G+C",
        "treatment_rate": 0.5
      },
      {
        "absolute_lift": 0.0,
        "bootstrap_samples": 20,
        "bootstrap_seed": 7,
        "cells_missing": [
          "P",
          "G+P",
          "C+P",
          "G+C+P"
        ],
        "cells_populated": [
          "none",
          "G",
          "C",
          "G+C"
        ],
        "ci_high": 0.0,
        "ci_level": 0.95,
        "ci_low": 0.0,
        "comparison": "G vs none",
        "comparison_label": "task-agnostic G vs none",
        "comparison_role": "secondary_diagnostic",
        "concordant_failure": 0,
        "concordant_success": 2,
        "condition_a": "none",
        "condition_b": "G",
        "control_condition": "none",
        "control_rate": 1.0,
        "discordant_control_only": 0,
        "discordant_treatment_only": 0,
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric",
          "p_cells_not_populated"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "missing_control_pairs": [],
        "missing_treatment_pairs": [],
        "multiple_testing_method": "holm",
        "n_pairs": 2,
        "outcome_family": "structural_code_surface",
        "p_value": 1.0,
        "p_value_holm": 1.0,
        "paired_analysis": true,
        "relative_lift": 0.0,
        "response_variable": "compile_success",
        "significant_holm": false,
        "success_rate_a": 1.0,
        "success_rate_b": 1.0,
        "treatment_condition": "G",
        "treatment_rate": 1.0
      },
      {
        "absolute_lift": 0.0,
        "bootstrap_samples": 20,
        "bootstrap_seed": 7,
        "cells_missing": [
          "P",
          "G+P",
          "C+P",
          "G+C+P"
        ],
        "cells_populated": [
          "none",
          "G",
          "C",
          "G+C"
        ],
        "ci_high": 0.0,
        "ci_level": 0.95,
        "ci_low": 0.0,
        "comparison": "G+C vs C",
        "comparison_label": "task-agnostic G + C vs C",
        "comparison_role": "secondary_diagnostic",
        "concordant_failure": 0,
        "concordant_success": 2,
        "condition_a": "C",
        "condition_b": "G+C",
        "control_condition": "C",
        "control_rate": 1.0,
        "discordant_control_only": 0,
        "discordant_treatment_only": 0,
        "interpretation_flags": [
          "diagnostic_only",
          "strict_surface_metric",
          "p_cells_not_populated"
        ],
        "level_gate": "level1_compile_launch",
        "metric_current_status": "current_with_caveats",
        "metric_display_name": "Level 1 structural compile/launch success rate",
        "metric_gate": "compile_success",
        "metric_name": "level1_compile_success_rate",
        "metric_reportability": "reportable_secondary",
        "missing_control_pairs": [],
        "missing_treatment_pairs": [],
        "multiple_testing_method": "holm",
        "n_pairs": 2,
        "outcome_family": "structural_code_surface",
        "p_value": 1.0,
        "p_value_holm": 1.0,
        "paired_analysis": true,
        "relative_lift": 0.0,
        "response_variable": "compile_success",
        "significant_holm": false,
        "success_rate_a": 1.0,
        "success_rate_b": 1.0,
        "treatment_condition": "G+C",
        "treatment_rate": 1.0
      }
    ],
    "table_3_factorial_terms": [
      {
        "ci_95": [
          -3.9199279690801077,
          3.919927969080106
        ],
        "coefficient": -7.6028995351387725e-16,
        "direction": "negative",
        "model_family": "binary_logistic_irls",
        "model_fit_status": "fit",
        "model_type": "reduced_four_cell",
        "model_warnings": [
          "p_cells_not_populated"
        ],
        "response_variable": "functional_success",
        "term": "G"
      },
      {
        "ci_95": [
          -3.919927969080108,
          3.9199279690801054
        ],
        "coefficient": -1.2632898076655715e-15,
        "direction": "negative",
        "model_family": "binary_logistic_irls",
        "model_fit_status": "fit",
        "model_type": "reduced_four_cell",
        "model_warnings": [
          "p_cells_not_populated"
        ],
        "response_variable": "functional_success",
        "term": "C"
      },
      {
        "ci_95": [
          -5.543615297398708,
          5.543615297398712
        ],
        "coefficient": 1.520579907027754e-15,
        "direction": "positive",
        "model_family": "binary_logistic_irls",
        "model_fit_status": "fit",
        "model_type": "reduced_four_cell",
        "model_warnings": [
          "p_cells_not_populated"
        ],
        "response_variable": "functional_success",
        "term": "G:C"
      }
    ]
  }
}
""".strip()
