"""Repair/convergence metrics for Phase 13 Cluster 2 aggregation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import DEFAULT_EQUAL_ATTEMPTS_N, GENERATED_SOURCE_CLASS
from cluster2.results.dataclass import Cluster2EvalRow
from shared.eval.aggregation import (
    CellKey,
    group_rows_by_cell,
    require_generated_rows,
    require_unique_attempt_indexes,
)


@dataclass(frozen=True)
class CellOutcome:
    """One Bernoulli outcome for one Phase 13 cell."""

    cell: CellKey
    success: bool
    attempts_observed: int
    attempts_considered: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["cell"] = asdict(self.cell)
        return payload


@dataclass(frozen=True)
class RateResult:
    """A cell-level Bernoulli rate result."""

    metric: str
    condition: str | None
    source_class: str
    successes: int
    total_cells: int
    rate: float
    cell_outcomes: tuple[CellOutcome, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "condition": self.condition,
            "source_class": self.source_class,
            "successes": self.successes,
            "total_cells": self.total_cells,
            "rate": self.rate,
            "cell_outcomes": [outcome.to_dict() for outcome in self.cell_outcomes],
        }


def compute_pass_at_1_initial(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> RateResult:
    """Compute pass@1 over attempt-index 0 rows, one Bernoulli per cell."""

    groups = group_rows_by_cell(rows)
    outcomes: list[CellOutcome] = []
    source_classes: set[str] = set()
    for key, cell_rows in groups.items():
        source_classes.update(row.source_class for row in cell_rows)
        attempt_zero = [row for row in cell_rows if row.attempt_index == 0]
        if len(attempt_zero) > 1:
            raise ValueError(f"duplicate attempt_index 0 rows for cell {key}")
        if not attempt_zero:
            continue
        outcomes.append(
            CellOutcome(
                cell=key,
                success=attempt_zero[0].functional_success,
                attempts_observed=len(cell_rows),
                attempts_considered=1,
            )
        )

    if not outcomes:
        raise ValueError("pass@1 initial requires at least one attempt_index 0 row")

    successes = sum(outcome.success for outcome in outcomes)
    return RateResult(
        metric="pass_at_1_initial",
        condition=_single_condition(outcome.cell.condition for outcome in outcomes),
        source_class=_single_source_class(source_classes),
        successes=successes,
        total_cells=len(outcomes),
        rate=successes / len(outcomes),
        cell_outcomes=tuple(sorted(outcomes, key=lambda outcome: outcome.cell)),
    )


def compute_convergence_rate(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    *,
    max_attempts: int = DEFAULT_EQUAL_ATTEMPTS_N,
) -> RateResult:
    """Compute generated-condition convergence as Bernoulli per cell."""

    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    row_tuple = require_generated_rows(rows)
    groups = group_rows_by_cell(row_tuple)
    outcomes: list[CellOutcome] = []
    for key, cell_rows in groups.items():
        require_unique_attempt_indexes(key, cell_rows)
        considered = tuple(row for row in cell_rows if row.attempt_index < max_attempts)
        outcomes.append(
            CellOutcome(
                cell=key,
                success=any(row.functional_success for row in considered),
                attempts_observed=len(cell_rows),
                attempts_considered=len(considered),
            )
        )

    if not outcomes:
        raise ValueError("convergence rate requires at least one generated cell")
    successes = sum(outcome.success for outcome in outcomes)
    return RateResult(
        metric="convergence_rate",
        condition=_single_condition(outcome.cell.condition for outcome in outcomes),
        source_class=GENERATED_SOURCE_CLASS,
        successes=successes,
        total_cells=len(outcomes),
        rate=successes / len(outcomes),
        cell_outcomes=tuple(sorted(outcomes, key=lambda outcome: outcome.cell)),
    )


def cell_outcomes_by_cell(result: RateResult) -> dict[CellKey, CellOutcome]:
    """Return a deterministic mapping from cell key to outcome."""

    return {outcome.cell: outcome for outcome in result.cell_outcomes}


def _single_condition(values: Iterable[str]) -> str | None:
    conditions = tuple(dict.fromkeys(values))
    if len(conditions) == 1:
        return conditions[0]
    return None


def _single_source_class(values: Iterable[str]) -> str:
    classes = tuple(dict.fromkeys(values))
    if len(classes) == 1:
        return classes[0]
    return "mixed"
