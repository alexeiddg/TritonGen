from __future__ import annotations

import json
from pathlib import Path

import pytest

from cluster3.planning.modal_preflight_estimator import (
    SHAPE_BOUNDED_FANOUT_ACROSS_CELLS_SEEDS,
    SHAPE_ONE_INVOCATION_PER_CELL,
    SHAPE_ONE_INVOCATION_PER_GRAMMAR_MODE_SHARD,
    SHAPE_ONE_INVOCATION_PER_ROW,
    SHAPE_SINGLE_FULL_PLAN_INVOCATION,
    TIMING_SOURCE_MEASURED,
    WARNING_LARGER_GPU_UNMEASURED,
    WARNING_PRICING_REVERIFY,
    WARNING_STAGE_TIMING_ESTIMATED,
    ModalPreflightInputs,
    compare_gpu_breakeven,
    estimate_preflight_run,
)


def _inputs(**overrides: object) -> ModalPreflightInputs:
    values = {
        "cell_count": 12,
        "n_per_cell": 1,
        "gpu_label": "L4",
        "price_per_gpu_second": 0.01,
        "cold_start_seconds": 10.0,
        "model_load_seconds": 20.0,
        "generation_seconds_per_row": 2.0,
        "compile_correctness_seconds_per_row": 3.0,
        "repair_overhead_seconds_per_activated_repair": 4.0,
        "expected_p_activation_rate": 0.25,
        "expected_c_activation_rate": 0.5,
        "fanout_limit": 4,
        "safety_multiplier": 1.0,
        "fixed_overhead_seconds": 5.0,
        "pricing_verified": True,
        "stage_timing_source": TIMING_SOURCE_MEASURED,
    }
    values.update(overrides)
    return ModalPreflightInputs(**values)


def _shape(estimate, name: str):
    return {
        shape.shape_name: shape for shape in estimate.execution_shape_comparisons
    }[name]


def test_l1a_12_cells_n1_row_count() -> None:
    estimate = estimate_preflight_run(_inputs(n_per_cell=1))

    assert estimate.total_planned_rows == 12
    assert estimate.rows_per_cell == 1


def test_l1b_12_cells_n5_row_count() -> None:
    estimate = estimate_preflight_run(_inputs(n_per_cell=5))

    assert estimate.total_planned_rows == 60
    assert estimate.rows_per_cell == 5


def test_l2_12_cells_n20_row_count() -> None:
    estimate = estimate_preflight_run(_inputs(n_per_cell=20))

    assert estimate.total_planned_rows == 240
    assert estimate.rows_per_cell == 20


def test_serial_vs_fanout_wall_clock_arithmetic_for_per_cell_shape() -> None:
    estimate = estimate_preflight_run(_inputs())
    per_cell = _shape(estimate, SHAPE_ONE_INVOCATION_PER_CELL)

    assert per_cell.invocation_count == 12
    assert per_cell.estimated_serial_wall_clock_seconds == pytest.approx(461.0)
    assert per_cell.estimated_parallel_wall_clock_seconds == pytest.approx(119.0)
    assert per_cell.estimated_gpu_seconds == pytest.approx(461.0)
    assert per_cell.estimated_cost == pytest.approx(4.61)


def test_execution_shape_comparison_partitions_rows() -> None:
    estimate = estimate_preflight_run(_inputs(n_per_cell=5, fanout_limit=4))

    per_row = _shape(estimate, SHAPE_ONE_INVOCATION_PER_ROW)
    per_cell = _shape(estimate, SHAPE_ONE_INVOCATION_PER_CELL)
    grammar_shard = _shape(estimate, SHAPE_ONE_INVOCATION_PER_GRAMMAR_MODE_SHARD)
    full_plan = _shape(estimate, SHAPE_SINGLE_FULL_PLAN_INVOCATION)
    bounded = _shape(estimate, SHAPE_BOUNDED_FANOUT_ACROSS_CELLS_SEEDS)

    assert per_row.invocation_count == 60
    assert per_row.row_partitions == tuple(1 for _ in range(60))
    assert per_cell.invocation_count == 12
    assert per_cell.row_partitions == tuple(5 for _ in range(12))
    assert grammar_shard.invocation_count == 3
    assert grammar_shard.row_partitions == (20, 20, 20)
    assert full_plan.invocation_count == 1
    assert full_plan.row_partitions == (60,)
    assert bounded.invocation_count == 4
    assert bounded.row_partitions == (15, 15, 15, 15)


def test_breakeven_speedup_equals_price_ratio() -> None:
    comparison = compare_gpu_breakeven(
        baseline_gpu_label="L4",
        baseline_price_per_gpu_second=0.2,
        candidate_gpu_label="L40S",
        candidate_price_per_gpu_second=0.5,
    )

    assert comparison.price_ratio == pytest.approx(2.5)
    assert comparison.breakeven_speedup == pytest.approx(2.5)
    assert comparison.minimum_justification_speedup == pytest.approx(2.5)


def test_larger_gpu_remains_advisory_without_measured_speedup() -> None:
    comparison = compare_gpu_breakeven(
        baseline_gpu_label="L4",
        baseline_price_per_gpu_second=0.2,
        candidate_gpu_label="H100",
        candidate_price_per_gpu_second=0.8,
        breakeven_safety_margin=0.1,
    )

    assert comparison.larger_gpu_is_cost_justified is False
    assert comparison.minimum_justification_speedup == pytest.approx(4.1)
    assert WARNING_LARGER_GPU_UNMEASURED in comparison.warning_flags


def test_pricing_reverification_warning_when_unverified() -> None:
    estimate = estimate_preflight_run(
        _inputs(pricing_verified=False, pricing_source="stale_local_fixture")
    )

    assert WARNING_PRICING_REVERIFY in estimate.warning_flags


def test_estimated_stage_warning_when_no_measured_timing_inputs() -> None:
    estimate = estimate_preflight_run(_inputs(stage_timing_source="estimated"))

    assert WARNING_STAGE_TIMING_ESTIMATED in estimate.warning_flags


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cell_count", 0),
        ("n_per_cell", 0),
        ("gpu_label", ""),
        ("price_per_gpu_second", 0.0),
        ("cold_start_seconds", -1.0),
        ("model_load_seconds", -1.0),
        ("generation_seconds_per_row", -1.0),
        ("compile_correctness_seconds_per_row", -1.0),
        ("repair_overhead_seconds_per_activated_repair", -1.0),
        ("expected_p_activation_rate", 1.5),
        ("expected_c_activation_rate", -0.1),
        ("fanout_limit", 0),
        ("safety_multiplier", 0.5),
        ("fixed_overhead_seconds", -1.0),
        ("stage_timing_source", "unknown"),
    ],
)
def test_invalid_inputs_fail_closed(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        estimate_preflight_run(_inputs(**{field: value}))


def test_price_per_gpu_hour_is_accepted_and_converted() -> None:
    estimate = estimate_preflight_run(
        _inputs(price_per_gpu_second=None, price_per_gpu_hour=36.0)
    )

    assert estimate.price_per_gpu_second == pytest.approx(0.01)


@pytest.mark.parametrize(
    "overrides",
    [
        {"measured_speedup_vs_baseline": 2.0},
        {"breakeven_safety_margin": 0.1},
        {"baseline_gpu_label": "L4"},
        {"baseline_price_per_gpu_second": 0.005},
    ],
)
def test_incomplete_baseline_comparison_inputs_fail_closed(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        estimate_preflight_run(_inputs(**overrides))


def test_estimate_output_is_json_serializable() -> None:
    estimate = estimate_preflight_run(_inputs())

    json.dumps(estimate.to_dict(), sort_keys=True)


def test_preflight_estimator_source_has_no_modal_import() -> None:
    module_path = Path(__file__).resolve().parents[1] / "planning" / (
        "modal_preflight_estimator.py"
    )
    source = module_path.read_text()

    assert "import modal" not in source
    assert "from modal" not in source
    assert "modal.billing" not in source
