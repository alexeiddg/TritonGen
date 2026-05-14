"""Coverage table helpers for Phase 13 reporting."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import is_dataclass
from typing import Any

from shared.eval.aggregation import assert_no_forbidden_metric_fields
from shared.eval.metrics.coverage import CoverageSummary


def build_coverage_table(
    summaries: CoverageSummary | Iterable[CoverageSummary],
) -> tuple[dict[str, Any], ...]:
    """Return deterministic coverage-feasibility table rows."""

    summary_tuple = _tupleify(summaries)
    rows = tuple(
        {
            "total_records": summary.total_records,
            "covered_records": summary.covered_records,
            "coverage_failures": summary.coverage_failures,
            "candidate_failures": summary.candidate_failures,
            "coverage_rate": summary.coverage_rate,
            "passed": summary.passed,
            "failure_reasons": ",".join(
                f"{reason}:{count}"
                for reason, count in sorted(summary.failure_reasons.items())
            ),
        }
        for summary in summary_tuple
    )
    for row in rows:
        assert_no_forbidden_metric_fields(row)
    return rows


def _tupleify(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        return (value,)
    if is_dataclass(value):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)
