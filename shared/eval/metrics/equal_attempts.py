"""Equal-attempt replay-control and lift metrics for Phase 13."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import DEFAULT_EQUAL_ATTEMPTS_N, REPLAY_CONTROL_SOURCE_CLASS
from cluster2.results.dataclass import Cluster2EvalRow
from shared.eval.aggregation import (
    CellKey,
    MatchedCellKey,
    group_rows_by_cell,
    require_replay_control_rows,
    require_unique_attempt_indexes,
)
from shared.eval.metrics.repair import (
    CellOutcome,
    RateResult,
    compute_convergence_rate,
)


DEFAULT_BOOTSTRAP_RESAMPLES = 10_000
DEFAULT_BOOTSTRAP_SEED = 13013


@dataclass(frozen=True)
class CellLiftOutcome:
    """Paired treatment/control Bernoulli outcome for one matched cell."""

    cell: MatchedCellKey
    treatment_success: bool
    control_success: bool

    @property
    def difference(self) -> float:
        return float(self.treatment_success) - float(self.control_success)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell": asdict(self.cell),
            "treatment_success": self.treatment_success,
            "control_success": self.control_success,
            "difference": self.difference,
        }


@dataclass(frozen=True)
class LiftEstimate:
    """Treatment-control lift with deterministic bootstrap CI over cells."""

    treatment_condition: str
    control_condition: str
    treatment_rate: float
    control_rate: float
    lift: float
    ci_lower: float
    ci_upper: float
    bootstrap_resamples: int
    bootstrap_seed: int
    total_cells: int
    cell_outcomes: tuple[CellLiftOutcome, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "treatment_condition": self.treatment_condition,
            "control_condition": self.control_condition,
            "treatment_rate": self.treatment_rate,
            "control_rate": self.control_rate,
            "lift": self.lift,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "bootstrap_resamples": self.bootstrap_resamples,
            "bootstrap_seed": self.bootstrap_seed,
            "total_cells": self.total_cells,
            "cell_outcomes": [outcome.to_dict() for outcome in self.cell_outcomes],
        }


def compute_pass_rate_within_n(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    *,
    n: int = DEFAULT_EQUAL_ATTEMPTS_N,
) -> RateResult:
    """Compute replay-control pass-within-N as Bernoulli per cell."""

    if n <= 0:
        raise ValueError("n must be positive")
    row_tuple = require_replay_control_rows(rows)
    groups = group_rows_by_cell(row_tuple)
    outcomes: list[CellOutcome] = []
    for key, cell_rows in groups.items():
        require_unique_attempt_indexes(key, cell_rows)
        _require_complete_replay_window(key, cell_rows, n)
        considered = tuple(row for row in cell_rows if row.attempt_index < n)
        outcomes.append(
            CellOutcome(
                cell=key,
                success=any(row.functional_success for row in considered),
                attempts_observed=len(cell_rows),
                attempts_considered=len(considered),
            )
        )

    if not outcomes:
        raise ValueError("pass-within-N requires at least one replay-control cell")
    successes = sum(outcome.success for outcome in outcomes)
    return RateResult(
        metric="pass_rate_within_n",
        condition=_single_condition(outcome.cell.condition for outcome in outcomes),
        source_class=REPLAY_CONTROL_SOURCE_CLASS,
        successes=successes,
        total_cells=len(outcomes),
        rate=successes / len(outcomes),
        cell_outcomes=tuple(sorted(outcomes, key=lambda outcome: outcome.cell)),
    )


def _require_complete_replay_window(
    key: CellKey,
    cell_rows: Sequence[Cluster2EvalRow],
    n: int,
) -> None:
    observed = {row.attempt_index for row in cell_rows}
    expected = set(range(n))
    if observed == expected:
        return
    missing = ", ".join(str(index) for index in sorted(expected - observed))
    extra = ", ".join(str(index) for index in sorted(observed - expected))
    detail_parts = []
    if missing:
        detail_parts.append(f"missing={missing}")
    if extra:
        detail_parts.append(f"extra={extra}")
    details = ", ".join(detail_parts)
    raise ValueError(
        "replay control cell must have exactly the mapped attempt_index values "
        f"for pass-within-{n}: cell={key}, {details}; "
        "record coverage_failure_missing_frozen_control instead"
    )


def compute_lift_with_bootstrap_ci(
    rows_treatment: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    rows_control: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    *,
    n: int = DEFAULT_EQUAL_ATTEMPTS_N,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> LiftEstimate:
    """Compute generated-vs-replay lift with bootstrap over matched cells."""

    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    treatment = compute_convergence_rate(rows_treatment, max_attempts=n)
    control = compute_pass_rate_within_n(rows_control, n=n)
    treatment_by_cell = _matched_outcomes(treatment.cell_outcomes)
    control_by_cell = _matched_outcomes(control.cell_outcomes)
    if set(treatment_by_cell) != set(control_by_cell):
        missing_control = sorted(set(treatment_by_cell) - set(control_by_cell))
        missing_treatment = sorted(set(control_by_cell) - set(treatment_by_cell))
        raise ValueError(
            "matched cell mismatch between treatment and control: "
            f"missing_control={missing_control}, missing_treatment={missing_treatment}"
        )

    paired = tuple(
        CellLiftOutcome(
            cell=key,
            treatment_success=treatment_by_cell[key].success,
            control_success=control_by_cell[key].success,
        )
        for key in sorted(treatment_by_cell)
    )
    if not paired:
        raise ValueError("lift requires at least one matched cell")

    treatment_rate = sum(outcome.treatment_success for outcome in paired) / len(paired)
    control_rate = sum(outcome.control_success for outcome in paired) / len(paired)
    lift = treatment_rate - control_rate
    bootstrap_values = _bootstrap_cell_lifts(
        paired,
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )
    return LiftEstimate(
        treatment_condition=_require_condition(treatment.condition, "treatment"),
        control_condition=_require_condition(control.condition, "control"),
        treatment_rate=treatment_rate,
        control_rate=control_rate,
        lift=lift,
        ci_lower=_percentile(bootstrap_values, 0.025),
        ci_upper=_percentile(bootstrap_values, 0.975),
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        total_cells=len(paired),
        cell_outcomes=paired,
    )


def _matched_outcomes(
    outcomes: Sequence[CellOutcome],
) -> dict[MatchedCellKey, CellOutcome]:
    matched: dict[MatchedCellKey, CellOutcome] = {}
    for outcome in outcomes:
        key = MatchedCellKey(
            kernel_class=outcome.cell.kernel_class,
            dtype=outcome.cell.dtype,
            base_seed=outcome.cell.base_seed,
        )
        if key in matched:
            raise ValueError(f"duplicate matched cell outcome {key}")
        matched[key] = outcome
    return matched


def _bootstrap_cell_lifts(
    paired: Sequence[CellLiftOutcome],
    *,
    resamples: int,
    seed: int,
) -> tuple[float, ...]:
    rng = random.Random(seed)
    n_cells = len(paired)
    values: list[float] = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(n_cells):
            total += rng.choice(paired).difference
        values.append(total / n_cells)
    return tuple(sorted(values))


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= percentile <= 1.0:
        raise ValueError("percentile must be in [0, 1]")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _single_condition(values: Iterable[str]) -> str | None:
    conditions = tuple(dict.fromkeys(values))
    if len(conditions) == 1:
        return conditions[0]
    return None


def _require_condition(condition: str | None, label: str) -> str:
    if condition is None:
        raise ValueError(f"{label} rows must contain exactly one condition")
    return condition
