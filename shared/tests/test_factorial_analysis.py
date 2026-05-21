"""Tests for cross-cluster factorial analysis helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from shared.analysis.factorial import (
    analyze_factorial,
    normalize_result_rows,
    validate_paired_replay_dataframe,
)


def test_factorial_cli_runs_when_invoked_by_file_path() -> None:
    script = Path(__file__).resolve().parents[1] / "analysis" / "factorial.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=script.parents[2],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--response-variable" in result.stdout


def test_analyze_factorial_accepts_eval_result_sample_index_identity() -> None:
    result = analyze_factorial(
        [
            {
                "condition": "none",
                "kernel_class": "elementwise",
                "kernel_id": 1,
                "kernel_name": "relu",
                "dtype_tested": "fp32",
                "sample_index": 7,
                "compile_success": True,
                "functional_success": True,
                "scale_tier": "paper",
            }
        ],
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=10,
    )

    summary = result["cell_summaries"][0]
    assert summary["condition"] == "none"
    assert summary["n_cells"] == 1
    assert summary["successes"] == 1


def test_analyze_factorial_emits_primary_four_cell_output() -> None:
    result = analyze_factorial(
        _four_cell_rows(),
        bootstrap_samples=200,
        bootstrap_seed=17,
    )

    assert result["metadata"]["response_variable"] == "functional_success"
    assert result["metadata"]["analysis_scope"] == "primary_functional"
    assert result["metadata"]["reportable"] is True
    assert result["metadata"]["analysis_label"] == "current 2² subset analysis over G and C"
    assert result["metadata"]["scope_kind"] == "temporary_2^2_subset"
    assert (
        result["metadata"]["full_factorial_goal"]
        == "The full 2³ factorial over G, C, and P remains the defined project goal."
    )
    assert (
        result["metadata"]["p_cell_status"]
        == "P-containing cells are deferred for this iteration and are not included "
        "in current paper-claiming outputs."
    )
    assert "full 2³ factorial analysis" not in result["metadata"]["analysis_label"]
    assert result["metadata"]["cells_populated"] == ["none", "G", "C", "G+C"]
    assert set(result["metadata"]["cells_missing"]) == {"P", "G+P", "C+P", "G+C+P"}
    assert "p_cells_not_populated" in result["metadata"]["interpretation_flags"]
    assert (
        "This is a current-status scope statement, not a methodology realignment."
        in result["metadata"]["scope_statements"]
    )
    assert result["diagnostics"]["analysis_label"] == "current 2² subset analysis over G and C"

    comparisons = {
        row["comparison"]: row for row in result["paired_comparisons"]
    }
    assert set(comparisons) == {"C vs none", "G+C vs G"}
    primary = comparisons["C vs none"]
    assert primary["paired_analysis"] is True
    assert primary["n_pairs"] == 4
    assert primary["success_rate_a"] == 0.25
    assert primary["success_rate_b"] == 0.5
    assert primary["absolute_lift"] == 0.25
    assert primary["ci_low"] <= primary["absolute_lift"] <= primary["ci_high"]
    assert primary["p_value_holm"] is not None

    model_terms = {
        row["term"]: row["coefficient"]
        for row in result["factorial_model"]["terms"]
    }
    assert result["factorial_model"]["model_type"] == "reduced_four_cell"
    assert result["factorial_model"]["model_family"] == "binary_logistic_irls"
    assert result["factorial_model"]["model_fit_status"] == "fit"
    assert model_terms["G:C"] > 0
    assert result["paper_tables"]["table_1_cell_summaries"]
    assert result["paper_tables"]["table_2_paired_comparisons"]
    assert result["paper_tables"]["table_3_factorial_terms"]
    table_1_condition_rows = [
        row
        for row in result["paper_tables"]["table_1_cell_summaries"]
        if row["summary_level"] == "condition"
        and row["response_variable"] == "functional_success"
    ]
    assert {row["scale_tier"] for row in table_1_condition_rows} == {"paper"}
    assert {row["cell_status"] for row in table_1_condition_rows} == {"populated"}
    labels_by_condition = {
        row["condition"]: row["condition_label"] for row in table_1_condition_rows
    }
    assert labels_by_condition["G"] == "task-agnostic G"
    assert labels_by_condition["G+C"] == "task-agnostic G + C"
    table_3_rows = result["paper_tables"]["table_3_factorial_terms"]
    assert {row["model_fit_status"] for row in table_3_rows} == {"fit"}
    assert {row["model_type"] for row in table_3_rows} == {"reduced_four_cell"}


@pytest.mark.parametrize("scale_tier", ["smoke", "development", "unspecified"])
def test_primary_analysis_is_reportable_only_for_paper_scale(scale_tier: str) -> None:
    rows = _four_cell_rows()
    for row in rows:
        row["scale_tier"] = scale_tier

    result = analyze_factorial(rows, bootstrap_samples=100)

    assert result["metadata"]["scale_tiers"] == [scale_tier]
    assert result["metadata"]["reportable"] is False


def test_null_scale_tier_is_unspecified_for_direct_dataframe() -> None:
    rows = _four_cell_rows()
    for row in rows:
        row["dtype_original"] = row["dtype"]
    rows[0]["scale_tier"] = None

    df = pd.DataFrame(rows)

    with pytest.raises(ValueError, match="mixed scale_tier"):
        analyze_factorial(df, bootstrap_samples=100)

    result = analyze_factorial(
        df,
        allow_mixed_scale=True,
        bootstrap_samples=100,
    )

    assert result["metadata"]["scale_tiers"] == ["paper", "unspecified"]
    assert result["metadata"]["reportable"] is False
    none_summary = next(
        row
        for row in result["cell_summaries"]
        if row["summary_level"] == "condition"
        and row["condition"] == "none"
        and row["response_variable"] == "functional_success"
    )
    assert none_summary["scale_tier"] == "mixed:paper,unspecified"


def test_separated_binary_model_does_not_emit_logistic_coefficients() -> None:
    rows = _separated_four_cell_rows()

    result = analyze_factorial(rows, bootstrap_samples=100)

    assert result["factorial_model"]["model_family"] == "binary_logistic_irls"
    assert result["factorial_model"]["model_fit_status"] == "not_fit"
    assert "model_separation_detected" in result["factorial_model"]["warnings"]
    assert all(row["coefficient"] is None for row in result["factorial_model"]["terms"])
    table_3_rows = result["paper_tables"]["table_3_factorial_terms"]
    assert {row["model_fit_status"] for row in table_3_rows} == {"not_fit"}
    assert all(
        "model_separation_detected" in row["model_warnings"]
        for row in table_3_rows
    )


def test_compile_success_analysis_is_secondary_diagnostic() -> None:
    result = analyze_factorial(
        _four_cell_rows(),
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=100,
    )

    assert result["metadata"]["response_variable"] == "compile_success"
    assert result["metadata"]["analysis_scope"] == "secondary_compile_diagnostic"
    assert result["metadata"]["reportable"] is False
    assert result["cell_summaries"][0]["analysis_role"] == "secondary_diagnostic"
    assert "diagnostic_only" in result["paired_comparisons"][0]["interpretation_flags"]


def test_primary_analysis_skips_partial_compile_success_summary() -> None:
    rows = _four_cell_rows()
    rows[0]["compile_success"] = None

    result = analyze_factorial(rows, bootstrap_samples=100)

    assert all(
        row["response_variable"] == "functional_success"
        for row in result["cell_summaries"]
    )
    assert (
        result["diagnostics"]["secondary_compile_summary"]["status"]
        == "not_emitted_partial_missing"
    )
    assert result["diagnostics"]["secondary_compile_summary"]["missing_rows"] == 1


def test_cluster1_none_missing_functional_success_normalizes_false() -> None:
    normalized = normalize_result_rows(
        [{"compile_success": False}],
        input_role="none",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "none"
    assert bool(row["functional_success"]) is False
    assert bool(row["compile_success"]) is False


def test_cluster1_g_compile_success_true_missing_functional_success_normalizes_false() -> None:
    normalized = normalize_result_rows(
        [{"compile_success": True}],
        input_role="g",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "G"
    assert bool(row["functional_success"]) is False
    assert bool(row["compile_success"]) is True


def test_cluster1_g_compile_success_false_missing_functional_success_normalizes_false() -> None:
    normalized = normalize_result_rows(
        [{"compile_success": False}],
        input_role="g",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "G"
    assert bool(row["functional_success"]) is False
    assert bool(row["compile_success"]) is False


def test_cluster1_accidental_functional_success_true_is_overridden_false() -> None:
    normalized = normalize_result_rows(
        [{"compile_success": True, "functional_success": True}],
        input_role="g",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "G"
    assert bool(row["functional_success"]) is False
    assert bool(row["compile_success"]) is True


def test_cluster2_functional_success_is_not_overridden_by_role() -> None:
    normalized = normalize_result_rows(
        [
            {
                "condition": "C",
                "compile_success": True,
                "functional_success": True,
            }
        ],
        input_role="c",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "C"
    assert bool(row["functional_success"]) is True
    assert bool(row["compile_success"]) is True


@pytest.mark.parametrize(
    ("role", "condition", "failure_code", "expected"),
    [
        ("c", "C", "F0_PARSE", False),
        ("c", "C", "F1_COMPILE", False),
        ("c", "C", "F2_NUMERIC_LARGE", True),
        ("gc", "G+C", "F2_SHAPE_MISMATCH", True),
        ("gc", "G+C", "F3_EVAL_PIPELINE", True),
        ("gc", "G+C", "F3_TIMEOUT", False),
    ],
)
def test_cluster2_compile_success_derives_from_failure_code(
    role: str,
    condition: str,
    failure_code: str,
    expected: bool,
) -> None:
    normalized = normalize_result_rows(
        [{"condition": condition, "failure_code": failure_code}],
        input_role=role,
    )

    assert bool(normalized.iloc[0]["compile_success"]) is expected


@pytest.mark.parametrize("failure_code", [None, ""])
def test_cluster2_success_failure_code_derives_compile_success_true(
    failure_code: str | None,
) -> None:
    normalized = normalize_result_rows(
        [
            {
                "condition": "G+C",
                "failure_code": failure_code,
                "functional_success": True,
            }
        ],
        input_role="gc",
    )

    row = normalized.iloc[0]
    assert bool(row["compile_success"]) is True
    assert bool(row["functional_success"]) is True


def test_cluster2_explicit_compile_success_agrees_with_failure_code() -> None:
    normalized = normalize_result_rows(
        [
            {
                "condition": "C",
                "failure_code": "F2_NUMERIC_NAN",
                "compile_success": True,
            }
        ],
        input_role="c",
    )

    assert bool(normalized.iloc[0]["compile_success"]) is True


def test_cluster2_explicit_compile_success_conflict_fails_loudly() -> None:
    with pytest.raises(
        ValueError,
        match="compile_success conflicts with failure_code-derived semantics.*F1_COMPILE",
    ):
        normalize_result_rows(
            [
                {
                    "condition": "C",
                    "failure_code": "F1_COMPILE",
                    "compile_success": True,
                }
            ],
            input_role="c",
        )


def test_cluster2_functional_success_compile_success_conflict_without_failure_code_fails() -> None:
    with pytest.raises(
        ValueError,
        match="functional_success=True requires compile_success=True",
    ):
        normalize_result_rows(
            [
                {
                    "condition": "C",
                    "compile_success": False,
                    "functional_success": True,
                }
            ],
            input_role="c",
        )


def test_cluster2_functional_success_derived_compile_conflict_fails() -> None:
    with pytest.raises(
        ValueError,
        match="functional_success=True requires compile_success=True",
    ):
        normalize_result_rows(
            [
                {
                    "condition": "C",
                    "failure_code": "F1_COMPILE",
                    "functional_success": True,
                }
            ],
            input_role="c",
        )


def test_cluster1_g_compile_success_ignores_cluster2_failure_code_derivation() -> None:
    normalized = normalize_result_rows(
        [
            {
                "compile_success": True,
                "functional_success": True,
                "failure_code": "F1_COMPILE",
            }
        ],
        input_role="g",
    )

    row = normalized.iloc[0]
    assert row["condition"] == "G"
    assert bool(row["compile_success"]) is True
    assert bool(row["functional_success"]) is False


def test_cluster2_real_artifact_samples_normalize_missing_compile_success() -> None:
    samples = {
        "c": Path("outputs/cluster2/c_paper_n20_l4.jsonl"),
        "gc": Path("outputs/cluster2/g_plus_c_paper_n20_l4.jsonl"),
    }
    for role, path in samples.items():
        if not path.exists():
            pytest.skip(f"missing artifact sample: {path}")
        rows = []
        for payload in _jsonl_sample(path, limit=10):
            row = dict(payload)
            row.pop("compile_success", None)
            rows.append(row)

        normalized = normalize_result_rows(rows, source_path=str(path), input_role=role)

        assert normalized["compile_success"].notna().all()
        expected = [
            _expected_cluster2_compile_success(row.get("failure_code")) for row in rows
        ]
        assert normalized["compile_success"].astype(bool).tolist() == expected


def test_cluster1_real_artifact_samples_normalize_functional_success_false() -> None:
    samples = {
        "none": Path("outputs/cluster1/baseline_repaired_l4_n20.jsonl"),
        "G": Path("outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"),
    }
    for condition, path in samples.items():
        if not path.exists():
            pytest.skip(f"missing artifact sample: {path}")
        rows = _jsonl_sample(path, limit=5)

        normalized = normalize_result_rows(rows, source_path=str(path))

        assert set(normalized["condition"]) == {condition}
        assert normalized["functional_success"].eq(False).all()


def test_primary_analysis_rejects_missing_functional_success() -> None:
    rows = _four_cell_rows()
    rows[0].pop("functional_success")

    with pytest.raises(ValueError, match="missing functional_success"):
        analyze_factorial(rows)


def test_primary_analysis_rejects_missing_pair() -> None:
    rows = [
        row
        for row in _four_cell_rows()
        if not (row["condition"] == "none" and row["base_seed"] == 3)
    ]

    with pytest.raises(ValueError, match="unmatched seed rows"):
        analyze_factorial(rows)


def test_primary_analysis_rejects_duplicate_pair() -> None:
    rows = _four_cell_rows()
    rows.append(_replay_row(condition="none", base_seed=0, functional_success=False))

    with pytest.raises(ValueError, match="duplicate"):
        analyze_factorial(rows)


def test_primary_analysis_rejects_metadata_mismatch() -> None:
    rows = _four_cell_rows()
    for row in rows:
        if row["condition"] == "none" and row["base_seed"] == 0:
            row["replay_metadata"]["prompt_sha256"] = "d" * 64

    with pytest.raises(ValueError, match="metadata mismatch"):
        analyze_factorial(rows)


def test_mode_collapse_warning_is_cell_summary_flag() -> None:
    rows = _four_cell_rows()
    for row in rows:
        if row["condition"] == "G" and row["base_seed"] == 0:
            row["grammar_variant"] = "template_upper_bound"
            row["unique_ratio_ast"] = 0.05

    result = analyze_factorial(rows, bootstrap_samples=100)

    g_summary = next(
        row
        for row in result["cell_summaries"]
        if row["summary_level"] == "condition"
        and row["condition"] == "G"
        and row["response_variable"] == "functional_success"
    )
    assert "mode_collapse_warning" in g_summary["interpretation_flags"]
    assert result["diagnostics"]["mode_collapse_warning_rows"] == 1


def test_template_upper_bound_condition_label_is_reference() -> None:
    rows = _four_cell_rows()
    for row in rows:
        if row["condition"] == "G":
            row["grammar_variant"] = "template_upper_bound"

    result = analyze_factorial(rows, bootstrap_samples=100)

    g_summary = next(
        row
        for row in result["cell_summaries"]
        if row["summary_level"] == "condition"
        and row["condition"] == "G"
        and row["response_variable"] == "functional_success"
    )
    assert g_summary["condition_label"] == "template G reference"


def test_missing_optional_interpretation_columns_do_not_crash() -> None:
    rows = _four_cell_rows()
    for row in rows:
        row["dtype_original"] = row["dtype"]
        row.pop("grammar_variant", None)
        row.pop("unique_ratio_ast", None)

    result = analyze_factorial(pd.DataFrame(rows), bootstrap_samples=100)

    assert result["diagnostics"]["mode_collapse_warning_rows"] == 0
    assert all(
        "mode_collapse_warning" not in row["interpretation_flags"]
        for row in result["cell_summaries"]
    )


def test_full_eight_cell_design_emits_p_terms() -> None:
    rows = _four_cell_rows()
    for condition in ("P", "G+P", "C+P", "G+C+P"):
        for seed in range(4):
            rows.append(
                _generic_factor_row(
                    condition=condition,
                    base_seed=seed,
                    functional_success=condition in {"C+P", "G+C+P"},
                )
            )

    result = analyze_factorial(rows, bootstrap_samples=100)

    assert result["metadata"]["analysis_label"] == "full 2³ factorial analysis"
    assert result["metadata"]["scope_kind"] == "full_2^3_factorial"
    assert result["metadata"]["p_cell_status"] == "P-containing cells are populated."
    assert "p_cells_not_populated" not in result["metadata"]["interpretation_flags"]
    assert result["factorial_model"]["model_type"] == "full_eight_cell"
    terms = {row["term"] for row in result["factorial_model"]["terms"]}
    assert {"P", "G:P", "C:P", "G:C:P"}.issubset(terms)


def test_partial_p_cell_coverage_is_not_labeled_deferred() -> None:
    rows = _four_cell_rows()
    for seed in range(4):
        rows.append(
            _generic_factor_row(
                condition="P",
                base_seed=seed,
                functional_success=True,
            )
        )

    result = analyze_factorial(rows, bootstrap_samples=100)

    assert result["metadata"]["analysis_label"] == "partial factorial analysis"
    assert result["metadata"]["scope_kind"] == "partial_factorial"
    assert "P-containing cell coverage is partial" in result["metadata"]["p_cell_status"]
    assert "deferred for this iteration" not in result["metadata"]["p_cell_status"]
    assert result["factorial_model"]["model_type"] == "partial_eight_cell_not_reportable"


def test_pairing_keeps_distinct_kernel_ids_with_same_seed() -> None:
    rows = _four_cell_rows(kernel_name="relu")
    rows.extend(_four_cell_rows(kernel_name="softmax"))

    result = analyze_factorial(rows, bootstrap_samples=100)

    comparisons = {
        row["comparison"]: row for row in result["paired_comparisons"]
    }
    assert comparisons["C vs none"]["n_pairs"] == 8
    assert comparisons["G+C vs G"]["n_pairs"] == 8
    condition_summaries = [
        row
        for row in result["cell_summaries"]
        if row["summary_level"] == "condition"
        and row["response_variable"] == "functional_success"
    ]
    assert {row["n_cells"] for row in condition_summaries} == {8}


def test_pairing_fills_missing_kernel_id_from_kernel_name() -> None:
    rows = _four_cell_rows(kernel_name="relu")
    rows.extend(_four_cell_rows(kernel_name="softmax"))
    for row in rows:
        row["kernel_id"] = None

    result = analyze_factorial(pd.DataFrame(rows), bootstrap_samples=100)

    comparisons = {
        row["comparison"]: row for row in result["paired_comparisons"]
    }
    assert comparisons["C vs none"]["n_pairs"] == 8
    assert comparisons["G+C vs G"]["n_pairs"] == 8


def test_paired_validation_rejects_missing_kernel_identity() -> None:
    rows = [_generated_row(base_seed=0), _replay_row(base_seed=0)]
    for row in rows:
        row.pop("kernel_name")
        row["kernel_id"] = None

    with pytest.raises(ValueError, match="missing required paired identity fields"):
        validate_paired_replay_dataframe(pd.DataFrame(rows), treatment_condition="C")


def test_incomplete_non_p_design_does_not_claim_reduced_four_cell_model() -> None:
    rows = [
        row
        for row in _four_cell_rows()
        if row["condition"] in {"none", "G"}
    ]

    result = analyze_factorial(
        rows,
        response_variable="compile_success",
        analysis_scope="secondary_compile_diagnostic",
        bootstrap_samples=100,
    )

    assert result["factorial_model"]["model_type"] == "partial_four_cell_not_reportable"
    assert result["factorial_model"]["model_fit_status"] == "not_fit"
    assert result["factorial_model"]["terms"] == []
    assert (
        "partial_four_cell_coverage_blocks_reduced_factorial_model"
        in result["factorial_model"]["warnings"]
    )
    table_3 = result["paper_tables"]["table_3_factorial_terms"]
    assert table_3 == [
        {
            "response_variable": "compile_success",
            "model_type": "partial_four_cell_not_reportable",
            "model_family": "binary_logistic_irls",
            "model_fit_status": "not_fit",
            "model_warnings": [
                "partial_four_cell_coverage_blocks_reduced_factorial_model",
                "p_cells_not_populated",
            ],
            "term": None,
            "coefficient": None,
            "direction": "unavailable",
        }
    ]


def test_validate_paired_replay_dataframe_reads_nested_metadata() -> None:
    df = pd.DataFrame(
        [
            _generated_row(base_seed=0),
            _replay_row(base_seed=0),
        ]
    )

    validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_nested_metadata_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["replay_metadata"]["prompt_sha256"] = "d" * 64
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_allows_generated_token_budget_migration() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated["generated_metadata"]["max_new_tokens"] = 1536
    df = pd.DataFrame([generated, replay])

    validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_replay_base_seed_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["replay_metadata"]["replay_base_seed"] = 1
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_known_revision_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(
        base_seed=0,
        model_revision="frozen-model-rev",
        tokenizer_revision="frozen-tokenizer-rev",
    )
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_missing_pair_metadata() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated.pop("generated_metadata")
    replay.pop("replay_metadata")
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="missing paired replay metadata"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_generated_seed_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated["generated_metadata"]["generation_seed"] = 999
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_control_condition_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated["generated_metadata"]["replay_control_condition"] = "G"
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_nonzero_replay_attempt() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["attempt_index"] = 5
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="attempt_index 0"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_accepts_repair_trace_attempt_zero() -> None:
    generated = _generated_row(base_seed=0, attempt_index=1)
    generated["generated_metadata"]["generation_seed"] = 1
    generated["repair_trace"] = [
        {
            "attempt_index": 0,
            "failure_code": "F2_NUMERIC_LARGE",
            "functional_success": False,
        },
        {
            "attempt_index": 1,
            "failure_code": None,
            "functional_success": True,
        },
    ]
    replay = _replay_row(base_seed=0)
    df = pd.DataFrame([generated, replay])

    validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_missing_generated_attempt_zero() -> None:
    generated = _generated_row(base_seed=0, attempt_index=1)
    generated["generated_metadata"]["generation_seed"] = 1
    replay = _replay_row(base_seed=0)
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="attempt_index 0"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def _four_cell_rows(*, kernel_name: str = "relu") -> list[dict[str, object]]:
    patterns = {
        "none": (False, False, False, True),
        "G": (False, False, False, True),
        "C": (True, True, False, False),
        "G+C": (True, True, True, False),
    }
    return _rows_from_patterns(patterns, kernel_name=kernel_name)


def _separated_four_cell_rows() -> list[dict[str, object]]:
    return _rows_from_patterns(
        {
            "none": (False, False, False, False),
            "G": (False, True, False, False),
            "C": (True, True, False, False),
            "G+C": (True, True, True, True),
        },
        kernel_name="relu",
    )


def _rows_from_patterns(
    patterns: dict[str, tuple[bool, ...]],
    *,
    kernel_name: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for condition, successes in patterns.items():
        for seed, success in enumerate(successes):
            if condition in {"none", "G"}:
                rows.append(
                    _replay_row(
                        condition=condition,
                        base_seed=seed,
                        kernel_name=kernel_name,
                        functional_success=success,
                        compile_success=True,
                    )
                )
            else:
                rows.append(
                    _generated_row(
                        condition=condition,
                        base_seed=seed,
                        kernel_name=kernel_name,
                        functional_success=success,
                        compile_success=True,
                    )
                )
    return rows


def _generated_row(
    *,
    condition: str = "C",
    base_seed: int,
    kernel_name: str = "relu",
    attempt_index: int = 0,
    functional_success: bool = True,
    compile_success: bool = True,
) -> dict[str, object]:
    control_condition = "G" if condition == "G+C" else "none"
    return {
        "condition": condition,
        "source_class": "generated_row",
        "kernel_class": "elementwise",
        "kernel_id": kernel_name,
        "kernel_name": kernel_name,
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": attempt_index,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "grammar_variant": "task_agnostic" if "G" in condition.split("+") else None,
        "grammar_claim_scope": "primary" if "G" in condition.split("+") else None,
        "scale_tier": "paper",
        "generated_metadata": _generated_pair_metadata(
            base_seed,
            kernel_name=kernel_name,
            control_condition=control_condition,
            attempt_index=attempt_index,
        ),
    }


def _replay_row(
    *,
    condition: str = "none",
    base_seed: int,
    kernel_name: str = "relu",
    functional_success: bool = False,
    compile_success: bool = True,
    model_revision: str = "unavailable_in_frozen_cluster1_artifact",
    tokenizer_revision: str = "unavailable_in_frozen_cluster1_artifact",
) -> dict[str, object]:
    return {
        "condition": condition,
        "source_class": "replay_control_row",
        "kernel_class": "elementwise",
        "kernel_id": kernel_name,
        "kernel_name": kernel_name,
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": 0,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "grammar_variant": "task_agnostic" if condition == "G" else None,
        "grammar_claim_scope": "primary" if condition == "G" else None,
        "scale_tier": "paper",
        "replay_metadata": _pair_metadata(
            base_seed,
            kernel_name=kernel_name,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
        ),
    }


def _generic_factor_row(
    *,
    condition: str,
    base_seed: int,
    kernel_name: str = "relu",
    functional_success: bool,
) -> dict[str, object]:
    return {
        "condition": condition,
        "source_class": "generated_row",
        "kernel_class": "elementwise",
        "kernel_id": kernel_name,
        "kernel_name": kernel_name,
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": 0,
        "compile_success": True,
        "functional_success": functional_success,
        "grammar_variant": "task_agnostic" if "G" in condition.split("+") else None,
        "grammar_claim_scope": "primary" if "G" in condition.split("+") else None,
        "scale_tier": "paper",
        "generated_metadata": _generated_pair_metadata(
            base_seed,
            kernel_name=kernel_name,
            control_condition="none",
        ),
    }


def _pair_metadata(
    base_seed: int,
    *,
    kernel_name: str = "relu",
    model_revision: str = "model-rev",
    tokenizer_revision: str = "tok-rev",
) -> dict[str, object]:
    return {
        "replay_pair_id": f"elementwise:{kernel_name}:fp32:{base_seed}",
        "replay_base_seed": base_seed,
        "replay_generation_seed": base_seed,
        "prompt_sha256": "c" * 64,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": model_revision,
        "tokenizer_revision": tokenizer_revision,
        "temperature": 0.2,
        "max_new_tokens": 512,
    }


def _generated_pair_metadata(
    base_seed: int,
    *,
    kernel_name: str = "relu",
    control_condition: str = "none",
    attempt_index: int = 0,
) -> dict[str, object]:
    metadata = _pair_metadata(base_seed, kernel_name=kernel_name)
    metadata["generation_seed"] = (
        base_seed if attempt_index == 0 else base_seed * 10 + attempt_index
    )
    metadata["replay_control_condition"] = control_condition
    return metadata


def _jsonl_sample(path: Path, *, limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
        if len(rows) == limit:
            break
    return rows


def _expected_cluster2_compile_success(failure_code: object) -> bool:
    return (
        failure_code is None
        or failure_code == ""
        or (isinstance(failure_code, str) and failure_code.startswith("F2_"))
        or failure_code == "F3_EVAL_PIPELINE"
    )
