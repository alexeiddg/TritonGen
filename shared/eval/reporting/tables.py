"""Simple deterministic Phase 13 reporting tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import is_dataclass
from typing import Any

from shared.eval.aggregation import assert_no_forbidden_metric_fields
from shared.eval.metrics.equal_attempts import LiftEstimate
from shared.eval.metrics.repair import RateResult


PRIMARY_COMPARISON_LABEL = "primary comparison: C vs frozen none replay control"
SECONDARY_COMPARISON_LABEL = "secondary comparison: G+C vs frozen G replay control"


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
    return str(value)


def _tupleify(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        return (value,)
    if is_dataclass(value):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)
