"""Equal-attempt replay-control and lift metrics for Phase 13."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import DEFAULT_EQUAL_ATTEMPTS_N, REPLAY_CONTROL_SOURCE_CLASS
from cluster2.results.dataclass import Cluster2EvalRow
from shared.eval.constants import BOOTSTRAP_SAMPLES, BOOTSTRAP_SEED, CI_LEVEL
from shared.eval.aggregation import (
    CellKey,
    MatchedCellKey,
    require_replay_control_rows,
    validate_paired_replay_alignment,
)
from shared.eval.metrics.repair import (
    CellOutcome,
    RateResult,
    compute_convergence_rate,
)


DEFAULT_BOOTSTRAP_RESAMPLES = BOOTSTRAP_SAMPLES
DEFAULT_BOOTSTRAP_SEED = BOOTSTRAP_SEED


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
    discordant_treatment_only: int
    discordant_control_only: int
    mcnemar_p_value: float
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
            "discordant_treatment_only": self.discordant_treatment_only,
            "discordant_control_only": self.discordant_control_only,
            "mcnemar_p_value": self.mcnemar_p_value,
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
    """Compute replay-control success over the first N paired seed cells."""

    if n <= 0:
        raise ValueError("n must be positive")
    row_tuple = require_replay_control_rows(rows)
    grouped_by_schedule_cell: dict[tuple[str, str, str], list[Cluster2EvalRow]] = {}
    outcomes: list[CellOutcome] = []
    seen_cells: set[CellKey] = set()
    for row in row_tuple:
        key = CellKey(
            kernel_class=row.kernel_class,
            dtype=row.dtype,
            base_seed=row.base_seed,
            condition=row.condition,
        )
        if key in seen_cells:
            raise ValueError(f"duplicate replay pair for {key}")
        seen_cells.add(key)
        if row.attempt_index != 0:
            raise ValueError(
                f"replay pair {key} must use attempt_index 0; got {row.attempt_index}"
            )
        grouped_by_schedule_cell.setdefault(
            (row.condition, row.kernel_class, row.dtype),
            [],
        ).append(row)
        outcomes.append(
            CellOutcome(
                cell=key,
                success=row.functional_success,
                attempts_observed=1,
                attempts_considered=1,
            )
        )

    if not outcomes:
        raise ValueError("pass-within-N requires at least one replay-control cell")
    for group_key, cell_rows in sorted(grouped_by_schedule_cell.items()):
        _require_complete_replay_seed_window(group_key, cell_rows, n)
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


def _require_complete_replay_seed_window(
    key: tuple[str, str, str],
    cell_rows: Sequence[Cluster2EvalRow],
    n: int,
) -> None:
    observed = {row.base_seed for row in cell_rows}
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
    condition, kernel_class, dtype = key
    raise ValueError(
        "replay control schedule cell must have exactly the mapped base_seed "
        f"values for pass-within-{n}: condition={condition!r}, "
        f"kernel_class={kernel_class!r}, dtype={dtype!r}, {details}; "
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
    """Compute generated-vs-replay paired lift over matched seed cells."""

    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    treatment_rows = tuple(rows_treatment)
    control_rows = tuple(rows_control)
    validate_paired_replay_alignment(treatment_rows, control_rows)
    treatment = compute_convergence_rate(treatment_rows, max_attempts=n)
    control = _compute_single_replay_pair_rate(control_rows)
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
    discordant_treatment_only = sum(
        outcome.treatment_success and not outcome.control_success
        for outcome in paired
    )
    discordant_control_only = sum(
        outcome.control_success and not outcome.treatment_success
        for outcome in paired
    )
    return LiftEstimate(
        treatment_condition=_require_condition(treatment.condition, "treatment"),
        control_condition=_require_condition(control.condition, "control"),
        treatment_rate=treatment_rate,
        control_rate=control_rate,
        lift=lift,
        ci_lower=_percentile(bootstrap_values, (1.0 - CI_LEVEL) / 2.0),
        ci_upper=_percentile(bootstrap_values, 1.0 - (1.0 - CI_LEVEL) / 2.0),
        discordant_treatment_only=discordant_treatment_only,
        discordant_control_only=discordant_control_only,
        mcnemar_p_value=_mcnemar_exact_p_value(
            discordant_treatment_only,
            discordant_control_only,
        ),
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        total_cells=len(paired),
        cell_outcomes=paired,
    )


def _compute_single_replay_pair_rate(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> RateResult:
    row_tuple = require_replay_control_rows(rows)
    outcomes = tuple(
        CellOutcome(
            cell=cell_key,
            success=row.functional_success,
            attempts_observed=1,
            attempts_considered=1,
        )
        for cell_key, row in sorted(
            (
                (
                    CellKey(
                        kernel_class=row.kernel_class,
                        dtype=row.dtype,
                        base_seed=row.base_seed,
                        condition=row.condition,
                    ),
                    row,
                )
                for row in row_tuple
            ),
            key=lambda item: item[0],
        )
    )
    if not outcomes:
        raise ValueError("paired replay rate requires at least one control row")
    successes = sum(outcome.success for outcome in outcomes)
    return RateResult(
        metric="paired_replay_success",
        condition=_single_condition(outcome.cell.condition for outcome in outcomes),
        source_class=REPLAY_CONTROL_SOURCE_CLASS,
        successes=successes,
        total_cells=len(outcomes),
        rate=successes / len(outcomes),
        cell_outcomes=outcomes,
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


def _mcnemar_exact_p_value(treatment_only: int, control_only: int) -> float:
    discordant = treatment_only + control_only
    if discordant == 0:
        return 1.0
    smaller = min(treatment_only, control_only)
    cumulative = sum(
        math.comb(discordant, index) * (0.5 ** discordant)
        for index in range(smaller + 1)
    )
    return min(1.0, 2.0 * cumulative)


def _single_condition(values: Iterable[str]) -> str | None:
    conditions = tuple(dict.fromkeys(values))
    if len(conditions) == 1:
        return conditions[0]
    return None


def _require_condition(condition: str | None, label: str) -> str:
    if condition is None:
        raise ValueError(f"{label} rows must contain exactly one condition")
    return condition
