"""Local-only Modal preflight cost/time estimator.

The estimator is advisory planning code. It does not import Modal, call billing
APIs, query pricing, run generation, write artifacts, or change scientific rows.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import asdict, dataclass
from typing import Any


SHAPE_ONE_INVOCATION_PER_ROW = "one_remote_invocation_per_row"
SHAPE_ONE_INVOCATION_PER_CELL = "one_remote_invocation_per_cell"
SHAPE_ONE_INVOCATION_PER_GRAMMAR_MODE_SHARD = (
    "one_remote_invocation_per_grammar_mode_shard"
)
SHAPE_SINGLE_FULL_PLAN_INVOCATION = "single_full_plan_invocation"
SHAPE_BOUNDED_FANOUT_ACROSS_CELLS_SEEDS = "bounded_fanout_across_cells_seeds"

TIMING_SOURCE_ESTIMATED = "estimated"
TIMING_SOURCE_MEASURED = "measured"

WARNING_ADVISORY_ONLY = "advisory_only_not_experimental_evidence"
WARNING_PRICING_REVERIFY = "pricing_reverification_required"
WARNING_STAGE_TIMING_ESTIMATED = "stage_timing_inputs_estimated_not_measured"
WARNING_LARGER_GPU_UNMEASURED = "larger_gpu_speedup_unmeasured"
WARNING_LARGER_GPU_NOT_JUSTIFIED = (
    "larger_gpu_not_justified_by_supplied_speedup"
)


@dataclass(frozen=True)
class ModalPreflightInputs:
    """Explicit local inputs for advisory time/cost estimates."""

    cell_count: int
    n_per_cell: int
    gpu_label: str
    price_per_gpu_second: float | None = None
    price_per_gpu_hour: float | None = None
    cold_start_seconds: float = 0.0
    model_load_seconds: float = 0.0
    generation_seconds_per_row: float = 0.0
    compile_correctness_seconds_per_row: float = 0.0
    repair_overhead_seconds_per_activated_repair: float = 0.0
    expected_p_activation_rate: float = 0.0
    expected_c_activation_rate: float = 0.0
    fanout_limit: int = 1
    safety_multiplier: float = 1.0
    fixed_overhead_seconds: float = 0.0
    pricing_source: str = "user_supplied_reverify_before_spend"
    pricing_verified: bool = False
    stage_timing_source: str = TIMING_SOURCE_ESTIMATED
    grammar_mode_shard_count: int = 3
    baseline_gpu_label: str | None = None
    baseline_price_per_gpu_second: float | None = None
    measured_speedup_vs_baseline: float | None = None
    breakeven_safety_margin: float = 0.0


@dataclass(frozen=True)
class ExecutionShapeEstimate:
    """Advisory estimate for one execution shape."""

    shape_name: str
    invocation_count: int
    row_partitions: tuple[int, ...]
    total_planned_rows: int
    rows_per_cell: int
    fanout_limit: int
    estimated_serial_wall_clock_seconds: float
    estimated_parallel_wall_clock_seconds: float
    estimated_gpu_seconds: float
    estimated_cost: float
    cold_start_overhead_share: float
    setup_model_load_overhead_share: float
    fixed_overhead_share: float
    generation_share: float
    correctness_eval_share: float
    repair_share: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GpuBreakevenComparison:
    """Advisory larger-GPU breakeven calculation."""

    baseline_gpu_label: str
    candidate_gpu_label: str
    baseline_price_per_gpu_second: float
    candidate_price_per_gpu_second: float
    price_ratio: float
    breakeven_speedup: float
    breakeven_safety_margin: float
    minimum_justification_speedup: float
    measured_speedup: float | None
    larger_gpu_is_cost_justified: bool
    justification_status: str
    warning_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModalPreflightEstimate:
    """JSON-safe advisory preflight estimate."""

    total_planned_rows: int
    rows_per_cell: int
    cell_count: int
    gpu_label: str
    price_per_gpu_second: float
    safety_multiplier: float
    warning_flags: tuple[str, ...]
    source_of_truth_boundary: str
    execution_shape_comparisons: tuple[ExecutionShapeEstimate, ...]
    recommended_shape_name: str
    estimated_serial_wall_clock_seconds: float
    estimated_parallel_wall_clock_seconds: float
    estimated_gpu_seconds: float
    estimated_cost: float
    cold_start_overhead_share: float
    setup_model_load_overhead_share: float
    fixed_overhead_share: float
    generation_share: float
    correctness_eval_share: float
    repair_share: float
    breakeven_speedup_needed_vs_baseline: float | None
    gpu_breakeven: GpuBreakevenComparison | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["execution_shape_comparisons"] = [
            shape.to_dict() for shape in self.execution_shape_comparisons
        ]
        payload["gpu_breakeven"] = (
            None if self.gpu_breakeven is None else self.gpu_breakeven.to_dict()
        )
        return payload


def estimate_preflight_run(inputs: ModalPreflightInputs) -> ModalPreflightEstimate:
    """Estimate advisory time/cost for planned Cluster 3 Modal execution shapes."""

    _validate_inputs(inputs)
    price_per_second = _price_per_second(inputs)
    total_rows = inputs.cell_count * inputs.n_per_cell
    row_stage_seconds = _row_stage_seconds(inputs)

    shapes = (
        _shape_estimate(
            SHAPE_ONE_INVOCATION_PER_ROW,
            row_partitions=tuple(1 for _ in range(total_rows)),
            inputs=inputs,
            price_per_second=price_per_second,
            row_stage_seconds=row_stage_seconds,
        ),
        _shape_estimate(
            SHAPE_ONE_INVOCATION_PER_CELL,
            row_partitions=tuple(inputs.n_per_cell for _ in range(inputs.cell_count)),
            inputs=inputs,
            price_per_second=price_per_second,
            row_stage_seconds=row_stage_seconds,
        ),
        _shape_estimate(
            SHAPE_ONE_INVOCATION_PER_GRAMMAR_MODE_SHARD,
            row_partitions=tuple(
                _split_count(total_rows, inputs.grammar_mode_shard_count)
            ),
            inputs=inputs,
            price_per_second=price_per_second,
            row_stage_seconds=row_stage_seconds,
        ),
        _shape_estimate(
            SHAPE_SINGLE_FULL_PLAN_INVOCATION,
            row_partitions=(total_rows,),
            inputs=inputs,
            price_per_second=price_per_second,
            row_stage_seconds=row_stage_seconds,
        ),
        _shape_estimate(
            SHAPE_BOUNDED_FANOUT_ACROSS_CELLS_SEEDS,
            row_partitions=tuple(_split_count(total_rows, inputs.fanout_limit)),
            inputs=inputs,
            price_per_second=price_per_second,
            row_stage_seconds=row_stage_seconds,
        ),
    )
    recommended = _shape_by_name(shapes, SHAPE_BOUNDED_FANOUT_ACROSS_CELLS_SEEDS)
    breakeven = _optional_gpu_breakeven(inputs, price_per_second)
    return ModalPreflightEstimate(
        total_planned_rows=total_rows,
        rows_per_cell=inputs.n_per_cell,
        cell_count=inputs.cell_count,
        gpu_label=inputs.gpu_label,
        price_per_gpu_second=price_per_second,
        safety_multiplier=inputs.safety_multiplier,
        warning_flags=_warning_flags(inputs, breakeven),
        source_of_truth_boundary=(
            "advisory_only_jsonl_sidecars_analyzers_and_billing_reconciliation_remain_authoritative"
        ),
        execution_shape_comparisons=shapes,
        recommended_shape_name=recommended.shape_name,
        estimated_serial_wall_clock_seconds=(
            recommended.estimated_serial_wall_clock_seconds
        ),
        estimated_parallel_wall_clock_seconds=(
            recommended.estimated_parallel_wall_clock_seconds
        ),
        estimated_gpu_seconds=recommended.estimated_gpu_seconds,
        estimated_cost=recommended.estimated_cost,
        cold_start_overhead_share=recommended.cold_start_overhead_share,
        setup_model_load_overhead_share=recommended.setup_model_load_overhead_share,
        fixed_overhead_share=recommended.fixed_overhead_share,
        generation_share=recommended.generation_share,
        correctness_eval_share=recommended.correctness_eval_share,
        repair_share=recommended.repair_share,
        breakeven_speedup_needed_vs_baseline=(
            None if breakeven is None else breakeven.breakeven_speedup
        ),
        gpu_breakeven=breakeven,
    )


def compare_gpu_breakeven(
    *,
    baseline_gpu_label: str,
    baseline_price_per_gpu_second: float,
    candidate_gpu_label: str,
    candidate_price_per_gpu_second: float,
    measured_speedup: float | None = None,
    breakeven_safety_margin: float = 0.0,
) -> GpuBreakevenComparison:
    """Compare candidate GPU pricing against a baseline.

    The breakeven speedup is the candidate/baseline price ratio. A more
    expensive candidate remains advisory unless a supplied measured speedup
    clears the ratio plus the caller's safety margin.
    """

    _validate_label(baseline_gpu_label, "baseline_gpu_label")
    _validate_label(candidate_gpu_label, "candidate_gpu_label")
    _validate_positive_number(
        baseline_price_per_gpu_second, "baseline_price_per_gpu_second"
    )
    _validate_positive_number(
        candidate_price_per_gpu_second, "candidate_price_per_gpu_second"
    )
    if measured_speedup is not None:
        _validate_positive_number(measured_speedup, "measured_speedup")
    _validate_non_negative_number(
        breakeven_safety_margin, "breakeven_safety_margin"
    )

    price_ratio = candidate_price_per_gpu_second / baseline_price_per_gpu_second
    minimum = price_ratio + breakeven_safety_margin
    warnings: list[str] = []
    if candidate_price_per_gpu_second > baseline_price_per_gpu_second:
        if measured_speedup is None:
            justified = False
            status = "requires_measured_speedup_before_use"
            warnings.append(WARNING_LARGER_GPU_UNMEASURED)
        elif measured_speedup >= minimum:
            justified = True
            status = "measured_speedup_clears_price_ratio_plus_margin"
        else:
            justified = False
            status = "measured_speedup_below_price_ratio_plus_margin"
            warnings.append(WARNING_LARGER_GPU_NOT_JUSTIFIED)
    else:
        justified = measured_speedup is not None or price_ratio <= 1.0
        status = "candidate_not_more_expensive_than_baseline"

    return GpuBreakevenComparison(
        baseline_gpu_label=baseline_gpu_label,
        candidate_gpu_label=candidate_gpu_label,
        baseline_price_per_gpu_second=baseline_price_per_gpu_second,
        candidate_price_per_gpu_second=candidate_price_per_gpu_second,
        price_ratio=price_ratio,
        breakeven_speedup=price_ratio,
        breakeven_safety_margin=breakeven_safety_margin,
        minimum_justification_speedup=minimum,
        measured_speedup=measured_speedup,
        larger_gpu_is_cost_justified=justified,
        justification_status=status,
        warning_flags=tuple(warnings),
    )


def _shape_estimate(
    shape_name: str,
    *,
    row_partitions: tuple[int, ...],
    inputs: ModalPreflightInputs,
    price_per_second: float,
    row_stage_seconds: float,
) -> ExecutionShapeEstimate:
    invocation_count = len(row_partitions)
    durations = tuple(
        inputs.cold_start_seconds
        + inputs.model_load_seconds
        + row_count * row_stage_seconds
        for row_count in row_partitions
    )
    total_rows = sum(row_partitions)
    fixed = inputs.fixed_overhead_seconds
    raw_serial_seconds = fixed + sum(durations)
    raw_parallel_seconds = fixed + _parallel_wall_seconds(
        durations, fanout_limit=inputs.fanout_limit
    )
    raw_gpu_seconds = raw_serial_seconds
    estimated_gpu_seconds = raw_gpu_seconds * inputs.safety_multiplier
    estimated_cost = estimated_gpu_seconds * price_per_second
    shares = _shares(
        fixed=fixed,
        cold_start=invocation_count * inputs.cold_start_seconds,
        model_load=invocation_count * inputs.model_load_seconds,
        generation=total_rows * inputs.generation_seconds_per_row,
        correctness=total_rows * inputs.compile_correctness_seconds_per_row,
        repair=total_rows
        * inputs.repair_overhead_seconds_per_activated_repair
        * (inputs.expected_p_activation_rate + inputs.expected_c_activation_rate),
    )
    return ExecutionShapeEstimate(
        shape_name=shape_name,
        invocation_count=invocation_count,
        row_partitions=row_partitions,
        total_planned_rows=total_rows,
        rows_per_cell=inputs.n_per_cell,
        fanout_limit=inputs.fanout_limit,
        estimated_serial_wall_clock_seconds=(
            raw_serial_seconds * inputs.safety_multiplier
        ),
        estimated_parallel_wall_clock_seconds=(
            raw_parallel_seconds * inputs.safety_multiplier
        ),
        estimated_gpu_seconds=estimated_gpu_seconds,
        estimated_cost=estimated_cost,
        cold_start_overhead_share=shares["cold_start"],
        setup_model_load_overhead_share=shares["model_load"],
        fixed_overhead_share=shares["fixed"],
        generation_share=shares["generation"],
        correctness_eval_share=shares["correctness"],
        repair_share=shares["repair"],
    )


def _optional_gpu_breakeven(
    inputs: ModalPreflightInputs, candidate_price_per_second: float
) -> GpuBreakevenComparison | None:
    if (
        inputs.baseline_gpu_label is None
        and inputs.baseline_price_per_gpu_second is None
    ):
        if inputs.measured_speedup_vs_baseline is not None:
            raise ValueError(
                "measured_speedup_vs_baseline requires baseline GPU comparison inputs"
            )
        if inputs.breakeven_safety_margin > 0:
            raise ValueError(
                "breakeven_safety_margin requires baseline GPU comparison inputs"
            )
        return None
    if (
        inputs.baseline_gpu_label is None
        or inputs.baseline_price_per_gpu_second is None
    ):
        raise ValueError(
            "baseline_gpu_label and baseline_price_per_gpu_second must be supplied together"
        )
    return compare_gpu_breakeven(
        baseline_gpu_label=inputs.baseline_gpu_label,
        baseline_price_per_gpu_second=inputs.baseline_price_per_gpu_second,
        candidate_gpu_label=inputs.gpu_label,
        candidate_price_per_gpu_second=candidate_price_per_second,
        measured_speedup=inputs.measured_speedup_vs_baseline,
        breakeven_safety_margin=inputs.breakeven_safety_margin,
    )


def _warning_flags(
    inputs: ModalPreflightInputs, breakeven: GpuBreakevenComparison | None
) -> tuple[str, ...]:
    warnings = [WARNING_ADVISORY_ONLY]
    if not inputs.pricing_verified:
        warnings.append(WARNING_PRICING_REVERIFY)
    if inputs.stage_timing_source != TIMING_SOURCE_MEASURED:
        warnings.append(WARNING_STAGE_TIMING_ESTIMATED)
    if breakeven is not None:
        warnings.extend(breakeven.warning_flags)
    return tuple(dict.fromkeys(warnings))


def _row_stage_seconds(inputs: ModalPreflightInputs) -> float:
    return (
        inputs.generation_seconds_per_row
        + inputs.compile_correctness_seconds_per_row
        + inputs.repair_overhead_seconds_per_activated_repair
        * (inputs.expected_p_activation_rate + inputs.expected_c_activation_rate)
    )


def _parallel_wall_seconds(durations: tuple[float, ...], *, fanout_limit: int) -> float:
    if not durations:
        return 0.0
    if fanout_limit >= len(durations):
        return max(durations)
    workers = [0.0 for _ in range(fanout_limit)]
    for duration in sorted(durations, reverse=True):
        earliest = heapq.heappop(workers)
        heapq.heappush(workers, earliest + duration)
    return max(workers)


def _split_count(total: int, partitions: int) -> tuple[int, ...]:
    count = min(total, partitions)
    base = total // count
    remainder = total % count
    return tuple(base + (1 if index < remainder else 0) for index in range(count))


def _shares(**parts: float) -> dict[str, float]:
    total = sum(parts.values())
    if total <= 0:
        return {name: 0.0 for name in parts}
    return {name: value / total for name, value in parts.items()}


def _shape_by_name(
    shapes: tuple[ExecutionShapeEstimate, ...], shape_name: str
) -> ExecutionShapeEstimate:
    for shape in shapes:
        if shape.shape_name == shape_name:
            return shape
    raise ValueError(f"missing execution shape: {shape_name}")


def _price_per_second(inputs: ModalPreflightInputs) -> float:
    if inputs.price_per_gpu_second is None and inputs.price_per_gpu_hour is None:
        raise ValueError("price_per_gpu_second or price_per_gpu_hour is required")
    if inputs.price_per_gpu_second is not None and inputs.price_per_gpu_hour is not None:
        raise ValueError("supply only one of price_per_gpu_second or price_per_gpu_hour")
    if inputs.price_per_gpu_second is not None:
        _validate_positive_number(inputs.price_per_gpu_second, "price_per_gpu_second")
        return inputs.price_per_gpu_second
    assert inputs.price_per_gpu_hour is not None
    _validate_positive_number(inputs.price_per_gpu_hour, "price_per_gpu_hour")
    return inputs.price_per_gpu_hour / 3600.0


def _validate_inputs(inputs: ModalPreflightInputs) -> None:
    _validate_positive_int(inputs.cell_count, "cell_count")
    _validate_positive_int(inputs.n_per_cell, "n_per_cell")
    _validate_label(inputs.gpu_label, "gpu_label")
    _validate_positive_int(inputs.fanout_limit, "fanout_limit")
    _validate_positive_int(inputs.grammar_mode_shard_count, "grammar_mode_shard_count")
    _validate_non_negative_number(inputs.cold_start_seconds, "cold_start_seconds")
    _validate_non_negative_number(inputs.model_load_seconds, "model_load_seconds")
    _validate_non_negative_number(
        inputs.generation_seconds_per_row, "generation_seconds_per_row"
    )
    _validate_non_negative_number(
        inputs.compile_correctness_seconds_per_row,
        "compile_correctness_seconds_per_row",
    )
    _validate_non_negative_number(
        inputs.repair_overhead_seconds_per_activated_repair,
        "repair_overhead_seconds_per_activated_repair",
    )
    _validate_rate(inputs.expected_p_activation_rate, "expected_p_activation_rate")
    _validate_rate(inputs.expected_c_activation_rate, "expected_c_activation_rate")
    _validate_non_negative_number(
        inputs.fixed_overhead_seconds, "fixed_overhead_seconds"
    )
    _validate_positive_number(inputs.safety_multiplier, "safety_multiplier")
    if inputs.safety_multiplier < 1:
        raise ValueError("safety_multiplier must be >= 1")
    if inputs.stage_timing_source not in {
        TIMING_SOURCE_ESTIMATED,
        TIMING_SOURCE_MEASURED,
    }:
        raise ValueError("stage_timing_source must be estimated or measured")
    if not isinstance(inputs.pricing_verified, bool):
        raise ValueError("pricing_verified must be a bool")
    _validate_label(inputs.pricing_source, "pricing_source")
    _price_per_second(inputs)
    if inputs.baseline_price_per_gpu_second is not None:
        _validate_positive_number(
            inputs.baseline_price_per_gpu_second,
            "baseline_price_per_gpu_second",
        )
    if inputs.measured_speedup_vs_baseline is not None:
        _validate_positive_number(
            inputs.measured_speedup_vs_baseline,
            "measured_speedup_vs_baseline",
        )
    _validate_non_negative_number(
        inputs.breakeven_safety_margin, "breakeven_safety_margin"
    )


def _validate_label(value: str | None, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer >= 1")


def _validate_rate(value: float, name: str) -> None:
    _validate_non_negative_number(value, name)
    if value > 1:
        raise ValueError(f"{name} must be between 0 and 1")


def _validate_positive_number(value: float, name: str) -> None:
    if not _is_real_number(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def _validate_non_negative_number(value: float, name: str) -> None:
    if not _is_real_number(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative finite number")


def _is_real_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )
