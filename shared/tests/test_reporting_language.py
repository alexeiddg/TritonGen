"""Tests for locked grammar-attribution language in reporting outputs."""

from __future__ import annotations

import pytest

from shared.eval.reporting.grammar_language import (
    GrammarLanguageError,
    assert_paper_facing_grammar_language,
    grammar_condition_label,
    grammar_condition_label_for_variants,
    grammar_variant_label,
)
from shared.eval.reporting.tables import render_factorial_markdown_report


@pytest.mark.parametrize(
    "text",
    [
        "template G reference",
        "template-G reference",
        "template upper bound diagnostic",
        "template_upper_bound reference condition",
    ],
)
def test_template_grammar_language_guard_accepts_qualified_examples(text: str) -> None:
    assert_paper_facing_grammar_language(text)


@pytest.mark.parametrize(
    "text",
    [
        "G result",
        "template G result",
        "grammar condition: template_upper_bound",
        "G compile rate from template_upper_bound",
        "template-G output",
        "template-G artifacts",
        "G result is the primary grammar condition",
        "G condition is the primary grammar condition",
        "G replay control",
        "secondary comparison: G+C vs frozen G replay control",
    ],
)
def test_template_grammar_language_guard_rejects_ambiguous_examples(text: str) -> None:
    with pytest.raises(GrammarLanguageError):
        assert_paper_facing_grammar_language(text)


def test_template_grammar_language_guard_rejects_unqualified_later_lines() -> None:
    text = "template G reference\ngrammar condition: template_upper_bound"

    with pytest.raises(GrammarLanguageError):
        assert_paper_facing_grammar_language(text)


def test_ambiguous_g_guard_rejects_unattributed_later_lines() -> None:
    text = "task-agnostic G is the primary grammar condition\nG result"

    with pytest.raises(GrammarLanguageError):
        assert_paper_facing_grammar_language(text)


def test_grammar_variant_labels_lock_primary_and_reference_roles() -> None:
    assert grammar_variant_label("task_agnostic") == "task-agnostic G"
    assert grammar_condition_label("G", "task_agnostic") == "task-agnostic G"
    assert grammar_variant_label("template_upper_bound") == "template G reference"
    assert grammar_condition_label("G", "template_upper_bound") == "template G reference"
    assert grammar_condition_label("G+C", "template_upper_bound") == (
        "template G reference + C"
    )


def test_missing_grammar_variant_condition_label_is_not_baseline_none() -> None:
    assert grammar_variant_label(None) == "none"
    assert grammar_condition_label("none", None) == "none"
    assert grammar_condition_label("G", None) == "G (missing grammar variant)"
    assert grammar_condition_label("G+C", None) == "G (missing grammar variant) + C"
    assert grammar_condition_label_for_variants("G", ()) == "G (missing grammar variant)"
    assert grammar_condition_label_for_variants("G", (None, "task_agnostic")) == (
        "task-agnostic G mixed with missing grammar variant"
    )


def test_factorial_markdown_report_rejects_unsafe_template_label() -> None:
    analysis = _minimal_factorial_analysis(condition_label="template G result")

    with pytest.raises(GrammarLanguageError):
        render_factorial_markdown_report(analysis)


def test_factorial_markdown_report_accepts_template_reference_label() -> None:
    analysis = _minimal_factorial_analysis(condition_label="template G reference")

    markdown = render_factorial_markdown_report(analysis)

    assert "template G reference" in markdown


def _minimal_factorial_analysis(*, condition_label: str) -> dict[str, object]:
    return {
        "paper_tables": {
            "table_1_cell_summaries": [
                {
                    "metric_name": "level2_functional_success_rate",
                    "response_variable": "functional_success",
                    "analysis_role": "primary",
                    "summary_level": "condition",
                    "scale_tier": "paper",
                    "cell_status": "populated",
                    "condition": "G",
                    "condition_label": condition_label,
                    "kernel_class": None,
                    "dtype": None,
                    "n_cells": 4,
                    "successes": 2,
                    "success_rate": 0.5,
                    "interpretation_flags": [],
                }
            ],
            "table_2_paired_comparisons": [],
            "table_3_factorial_terms": [
                {
                    "response_variable": "functional_success",
                    "model_type": "reduced_four_cell",
                    "model_family": "binary_logistic_irls",
                    "model_fit_status": "not_fit",
                    "term": None,
                    "coefficient": None,
                    "direction": "unavailable",
                    "model_warnings": [],
                }
            ],
        }
    }
