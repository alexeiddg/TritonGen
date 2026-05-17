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
    assert "Current 2² subset analysis over G and C" in markdown
    assert "P-containing cells are deferred for this iteration" in markdown
    assert "full 2³ factorial analysis" not in markdown
    assert "# Factorial Analysis" not in markdown
    assert "Table 1 Cell Summaries" in markdown
    assert "C vs none" in markdown
    assert "model_separation_detected" in markdown


def test_factorial_table_renderer_labels_full_eight_cell_output() -> None:
    analysis = {
        "metadata": {
            "analysis_label": "full 2³ factorial analysis",
            "scope_statements": [
                "The full 2³ factorial over G, C, and P remains the defined project goal."
            ],
        },
        "paper_tables": {
            "table_1_cell_summaries": [],
            "table_2_paired_comparisons": [],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "full_eight_cell",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "fit",
                    "term": "P",
                    "coefficient": 0.25,
                    "direction": "positive",
                    "model_warnings": [],
                }
            ],
        },
    }

    markdown = render_factorial_markdown_report(analysis)

    assert "Full 2³ factorial analysis" in markdown
    assert "P-containing cells are deferred" not in markdown


def test_factorial_table_renderer_rejects_stale_scope_metadata() -> None:
    analysis = {
        "metadata": {
            "analysis_label": "full 2³ factorial analysis",
            "scope_statements": [
                "The full 2³ factorial over G, C, and P remains the defined project goal."
            ],
        },
        "paper_tables": {
            "table_1_cell_summaries": [],
            "table_2_paired_comparisons": [],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "reduced_four_cell",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "fit",
                    "term": "G:C",
                    "coefficient": 0.25,
                    "direction": "positive",
                    "model_warnings": ["p_cells_not_populated"],
                }
            ],
        },
    }

    markdown = render_factorial_markdown_report(analysis)

    assert "Current 2² subset analysis over G and C" in markdown
    assert "P-containing cells are deferred for this iteration" in markdown
    assert "Full 2³ factorial analysis" not in markdown


def test_factorial_table_renderer_uses_canonical_scope_statements() -> None:
    analysis = {
        "metadata": {
            "analysis_label": "current 2² subset analysis over G and C",
            "scope_statements": [],
        },
        "paper_tables": {
            "table_1_cell_summaries": [],
            "table_2_paired_comparisons": [],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "reduced_four_cell",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "fit",
                    "term": "G:C",
                    "coefficient": 0.25,
                    "direction": "positive",
                    "model_warnings": ["p_cells_not_populated"],
                }
            ],
        },
    }

    markdown = render_factorial_markdown_report(analysis)

    assert "Current 2² subset analysis over G and C" in markdown
    assert "P-containing cells are deferred for this iteration" in markdown
    assert "The full 2³ factorial over G, C, and P remains" in markdown


def test_factorial_table_renderer_preserves_partial_scope_statements() -> None:
    analysis = {
        "paper_tables": {
            "table_1_cell_summaries": [],
            "table_2_paired_comparisons": [],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "partial_eight_cell_not_reportable",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "fit",
                    "term": "P",
                    "coefficient": 0.25,
                    "direction": "positive",
                    "model_warnings": [
                        "p_cells_not_populated",
                        "partial_p_cell_coverage_blocks_full_factorial_claims",
                    ],
                }
            ],
        },
    }

    markdown = render_factorial_markdown_report(analysis)

    assert "Partial factorial analysis" in markdown
    assert "The full 2³ factorial over G, C, and P remains" in markdown
    assert "P-containing cell coverage is partial" in markdown
    assert "full 2³ factorial completion" in markdown


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
