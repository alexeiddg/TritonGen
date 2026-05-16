"""Tests for factorial analysis table rendering."""

from __future__ import annotations

import pytest

from shared.eval.reporting.tables import (
    build_factorial_paper_tables,
    render_factorial_markdown_report,
)


def test_factorial_table_renderer_consumes_structured_output() -> None:
    analysis = {
        "paper_tables": {
            "table_1_cell_summaries": [
                {
                    "metric_name": "level2_functional_success_rate",
                    "response_variable": "functional_success",
                    "analysis_role": "primary",
                    "summary_level": "condition",
                    "scale_tier": "paper",
                    "cell_status": "populated",
                    "condition": "C",
                    "n_cells": 4,
                    "successes": 2,
                    "success_rate": 0.5,
                    "interpretation_flags": [],
                }
            ],
            "table_2_paired_comparisons": [
                {
                    "metric_name": "level2_functional_success_rate",
                    "response_variable": "functional_success",
                    "comparison": "C vs none",
                    "n_pairs": 4,
                    "success_rate_a": 0.0,
                    "success_rate_b": 0.5,
                    "absolute_lift": 0.5,
                    "ci_low": 0.0,
                    "ci_high": 1.0,
                    "p_value": 0.5,
                    "p_value_holm": 1.0,
                    "paired_analysis": True,
                    "interpretation_flags": ["p_cells_not_populated"],
                }
            ],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "reduced_four_cell",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "not_fit",
                    "term": "C",
                    "coefficient": None,
                    "direction": "unavailable",
                    "model_warnings": ["model_separation_detected"],
                }
            ],
        }
    }

    tables = build_factorial_paper_tables(analysis)
    markdown = render_factorial_markdown_report(analysis)

    assert tables["table_1_cell_summaries"][0]["response_variable"] == "functional_success"
    assert tables["table_1_cell_summaries"][0]["scale_tier"] == "paper"
    assert tables["table_1_cell_summaries"][0]["cell_status"] == "populated"
    assert tables["table_2_paired_comparisons"][0]["paired_analysis"] is True
    assert tables["table_3_factorial_terms"][0]["model_fit_status"] == "not_fit"
    assert "Table 1 Cell Summaries" in markdown
    assert "C vs none" in markdown
    assert "model_separation_detected" in markdown


def test_factorial_table_renderer_rejects_missing_paper_tables() -> None:
    with pytest.raises(ValueError, match="must contain paper_tables"):
        build_factorial_paper_tables({"metadata": {"analyzer_version": "stale"}})


def test_factorial_table_renderer_rejects_missing_table_section() -> None:
    analysis = {
        "paper_tables": {
            "table_1_cell_summaries": [],
            "table_2_paired_comparisons": [],
        }
    }

    with pytest.raises(ValueError, match="table_3_factorial_terms"):
        build_factorial_paper_tables(analysis)
