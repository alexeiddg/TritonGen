"""Simple deterministic Phase 13 reporting tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import is_dataclass
from typing import Any

from shared.eval.aggregation import assert_no_forbidden_metric_fields
from shared.eval.metrics.equal_attempts import LiftEstimate
from shared.eval.metrics.repair import RateResult
from shared.eval.reporting.grammar_language import assert_paper_facing_grammar_language


PRIMARY_COMPARISON_LABEL = "primary comparison: C vs frozen none replay control"
SECONDARY_COMPARISON_LABEL = (
    "secondary comparison: task-agnostic G + C vs frozen task-agnostic G replay control"
)
FACTORIAL_TABLE_SECTION_KEYS = (
    "table_1_cell_summaries",
    "table_2_paired_comparisons",
    "table_3_factorial_terms",
)


def comparison_label(treatment_condition: str, control_condition: str) -> str:
    """Return the pre-registered comparison label when applicable."""

    if treatment_condition == "C" and control_condition == "none":
        return PRIMARY_COMPARISON_LABEL
    if treatment_condition == "G+C" and control_condition == "G":
        return SECONDARY_COMPARISON_LABEL
    return f"{treatment_condition} vs {control_condition}"


def build_lift_table(
    estimates: LiftEstimate | Iterable[LiftEstimate],
) -> tuple[dict[str, Any], ...]:
    """Return deterministic rows for treatment/control lift reporting."""

    estimate_tuple = _tupleify(estimates)
    rows = tuple(
        {
            "comparison": comparison_label(
                estimate.treatment_condition,
                estimate.control_condition,
            ),
            "treatment_condition": estimate.treatment_condition,
            "control_condition": estimate.control_condition,
            "total_cells": estimate.total_cells,
            "treatment_rate": estimate.treatment_rate,
            "control_rate": estimate.control_rate,
            "lift": estimate.lift,
            "ci_lower": estimate.ci_lower,
            "ci_upper": estimate.ci_upper,
            "discordant_treatment_only": estimate.discordant_treatment_only,
            "discordant_control_only": estimate.discordant_control_only,
            "mcnemar_p_value": estimate.mcnemar_p_value,
            "bootstrap_resamples": estimate.bootstrap_resamples,
            "bootstrap_seed": estimate.bootstrap_seed,
        }
        for estimate in sorted(
            estimate_tuple,
            key=lambda item: comparison_label(
                item.treatment_condition,
                item.control_condition,
            ),
        )
    )
    for row in rows:
        assert_no_forbidden_metric_fields(row)
    return rows


def build_convergence_table(
    results: RateResult | Iterable[RateResult],
) -> tuple[dict[str, Any], ...]:
    """Return deterministic rows for convergence/pass-within-N summaries."""

    result_tuple = _tupleify(results)
    rows = tuple(
        {
            "metric": result.metric,
            "condition": result.condition,
            "source_class": result.source_class,
            "total_cells": result.total_cells,
            "successes": result.successes,
            "rate": result.rate,
        }
        for result in sorted(
            result_tuple,
            key=lambda item: (
                item.metric,
                "" if item.condition is None else item.condition,
                item.source_class,
            ),
        )
    )
    for row in rows:
        assert_no_forbidden_metric_fields(row)
    return rows


def build_factorial_paper_tables(
    analysis: Mapping[str, Any],
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Return table rows from structured factorial analyzer output.

    This function intentionally does not recompute statistics. It only selects
    deterministic rows produced by ``shared.analysis.factorial``.
    """

    if "paper_tables" not in analysis:
        raise ValueError("factorial analysis output must contain paper_tables")
    tables = analysis["paper_tables"]
    if not isinstance(tables, Mapping):
        raise ValueError("factorial analysis output must contain paper_tables")
    missing_tables = [
        table_key
        for table_key in FACTORIAL_TABLE_SECTION_KEYS
        if table_key not in tables
    ]
    if missing_tables:
        raise ValueError(
            "factorial paper_tables missing required sections: "
            + ", ".join(missing_tables)
        )
    return {
        "table_1_cell_summaries": tuple(
            _mapping_rows(tables.get("table_1_cell_summaries", ()))
        ),
        "table_2_paired_comparisons": tuple(
            _mapping_rows(tables.get("table_2_paired_comparisons", ()))
        ),
        "table_3_factorial_terms": tuple(
            _mapping_rows(tables.get("table_3_factorial_terms", ()))
        ),
    }


def render_factorial_markdown_report(analysis: Mapping[str, Any]) -> str:
    """Render the analyzer's Table 1-3 rows as markdown."""

    tables = build_factorial_paper_tables(analysis)
    parts = ["# Factorial Analysis"]
    table_columns = {
        "table_1_cell_summaries": (
            "metric_name",
            "response_variable",
            "analysis_role",
            "summary_level",
            "scale_tier",
            "cell_status",
            "condition",
            "condition_label",
            "kernel_class",
            "dtype",
            "n_cells",
            "successes",
            "success_rate",
            "interpretation_flags",
        ),
        "table_2_paired_comparisons": (
            "metric_name",
            "response_variable",
            "comparison",
            "comparison_label",
            "n_pairs",
            "success_rate_a",
            "success_rate_b",
            "absolute_lift",
            "ci_low",
            "ci_high",
            "p_value",
            "p_value_holm",
            "paired_analysis",
            "interpretation_flags",
        ),
        "table_3_factorial_terms": (
            "response_variable",
            "model_type",
            "model_family",
            "model_fit_status",
            "term",
            "coefficient",
            "direction",
            "model_warnings",
        ),
    }
    titles = {
        "table_1_cell_summaries": "Table 1 Cell Summaries",
        "table_2_paired_comparisons": "Table 2 Paired Comparisons",
        "table_3_factorial_terms": "Table 3 Factorial Terms",
    }
    for key, rows in tables.items():
        parts.append(f"\n## {titles[key]}")
        rendered = render_markdown_table(rows, columns=table_columns[key])
        parts.append(rendered if rendered else "_No rows emitted._")
    report = "\n".join(parts)
    assert_paper_facing_grammar_language(report)
    return report


def render_markdown_table(
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> str:
    """Render a minimal deterministic markdown table."""

    if not rows:
        return ""
    column_tuple = tuple(columns) if columns is not None else tuple(rows[0].keys())
    header = "| " + " | ".join(column_tuple) + " |"
    separator = "| " + " | ".join("---" for _ in column_tuple) + " |"
    body = [
        "| "
        + " | ".join(_format_value(row.get(column)) for column in column_tuple)
        + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _mapping_rows(rows: Any) -> tuple[dict[str, Any], ...]:
    return tuple(dict(row) for row in rows)


def _tupleify(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        return (value,)
    if is_dataclass(value):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)
