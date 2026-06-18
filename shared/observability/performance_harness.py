"""Pure O6b performance harness helpers.

This module intentionally imports no CUDA, Torch, Triton, Modal, profiler, or
network stack. It prepares and validates sidecar rows from already-collected
benchmark summaries.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from shared.observability.performance_sidecar import PerformanceSidecarRow


@dataclass(frozen=True)
class TensorBenchmarkSpec:
    shape_signature: str
    dtype: str
    device: str


@dataclass(frozen=True)
class TimingSummary:
    median_ms: float
    p25_ms: float
    p75_ms: float


def shape_signature_from_shape(shape: Sequence[int]) -> str:
    """Return the canonical O6b shape signature for a tensor shape."""

    if not shape:
        raise ValueError("shape must not be empty")
    dimensions: list[str] = []
    for dimension in shape:
        if isinstance(dimension, bool) or not isinstance(dimension, int):
            raise TypeError("shape dimensions must be integers")
        if dimension <= 0:
            raise ValueError("shape dimensions must be positive")
        dimensions.append(str(dimension))
    return "x".join(dimensions)


def summarize_timing_samples(samples_ms: Sequence[float]) -> TimingSummary:
    """Compute median and quartile summary values from timing samples."""

    values = _sorted_positive_finite_samples(samples_ms)
    return TimingSummary(
        median_ms=_quantile(values, 0.5),
        p25_ms=_quantile(values, 0.25),
        p75_ms=_quantile(values, 0.75),
    )


def compute_speedup_vs_baseline(
    *,
    baseline_median_ms: float,
    candidate_median_ms: float,
) -> float:
    """Compute speedup as baseline median divided by candidate median."""

    _require_positive_finite(baseline_median_ms, label="baseline_median_ms")
    _require_positive_finite(candidate_median_ms, label="candidate_median_ms")
    return baseline_median_ms / candidate_median_ms


def validate_same_shape_dtype_device(
    baseline: TensorBenchmarkSpec | Mapping[str, Any],
    candidate: TensorBenchmarkSpec | Mapping[str, Any],
) -> TensorBenchmarkSpec:
    """Fail closed unless baseline and candidate specs match exactly."""

    baseline_spec = _coerce_tensor_spec(baseline)
    candidate_spec = _coerce_tensor_spec(candidate)
    if baseline_spec != candidate_spec:
        raise ValueError("baseline and candidate must use the same shape/dtype/device")
    return baseline_spec


def build_performance_sidecar_row(
    *,
    experiment_id: str,
    run_id: str,
    benchmark_id: str,
    benchmark_scope: str,
    kernel_class: str,
    problem_id: str,
    dtype: str,
    baseline_type: str,
    candidate_type: str,
    timing_method: str,
    gpu_type: str,
    warmup_iters: int,
    repetitions: int,
    baseline_samples_ms: Sequence[float],
    candidate_samples_ms: Sequence[float],
    baseline_spec: TensorBenchmarkSpec | Mapping[str, Any],
    candidate_spec: TensorBenchmarkSpec | Mapping[str, Any],
    correctness_prerequisite_passed: bool,
    measurement_status: str,
    caveats: Sequence[str] = (),
) -> PerformanceSidecarRow:
    """Build a sidecar row from raw timing samples."""

    baseline_summary = summarize_timing_samples(baseline_samples_ms)
    candidate_summary = summarize_timing_samples(candidate_samples_ms)
    return build_performance_sidecar_row_from_summaries(
        experiment_id=experiment_id,
        run_id=run_id,
        benchmark_id=benchmark_id,
        benchmark_scope=benchmark_scope,
        kernel_class=kernel_class,
        problem_id=problem_id,
        dtype=dtype,
        baseline_type=baseline_type,
        candidate_type=candidate_type,
        timing_method=timing_method,
        gpu_type=gpu_type,
        warmup_iters=warmup_iters,
        repetitions=repetitions,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
        baseline_spec=baseline_spec,
        candidate_spec=candidate_spec,
        correctness_prerequisite_passed=correctness_prerequisite_passed,
        measurement_status=measurement_status,
        caveats=caveats,
    )


def build_performance_sidecar_row_from_summaries(
    *,
    experiment_id: str,
    run_id: str,
    benchmark_id: str,
    benchmark_scope: str,
    kernel_class: str,
    problem_id: str,
    dtype: str,
    baseline_type: str,
    candidate_type: str,
    timing_method: str,
    gpu_type: str,
    warmup_iters: int,
    repetitions: int,
    baseline_summary: TimingSummary | Mapping[str, Any],
    candidate_summary: TimingSummary | Mapping[str, Any],
    baseline_spec: TensorBenchmarkSpec | Mapping[str, Any],
    candidate_spec: TensorBenchmarkSpec | Mapping[str, Any],
    correctness_prerequisite_passed: bool,
    measurement_status: str,
    caveats: Sequence[str] = (),
) -> PerformanceSidecarRow:
    """Build a sidecar row from summarized timing values."""

    locked_spec = validate_same_shape_dtype_device(baseline_spec, candidate_spec)
    baseline = _coerce_timing_summary(baseline_summary)
    candidate = _coerce_timing_summary(candidate_summary)
    if dtype != locked_spec.dtype:
        raise ValueError("row dtype must match locked tensor dtype")
    if correctness_prerequisite_passed is not True:
        raise ValueError("performance timing requires a passed correctness prerequisite")
    return PerformanceSidecarRow(
        experiment_id=experiment_id,
        run_id=run_id,
        benchmark_id=benchmark_id,
        benchmark_scope=benchmark_scope,
        kernel_class=kernel_class,
        problem_id=problem_id,
        dtype=dtype,
        shape_signature=locked_spec.shape_signature,
        baseline_type=baseline_type,
        candidate_type=candidate_type,
        timing_method=timing_method,
        gpu_type=gpu_type,
        warmup_iters=warmup_iters,
        repetitions=repetitions,
        baseline_median_ms=baseline.median_ms,
        candidate_median_ms=candidate.median_ms,
        baseline_p25_ms=baseline.p25_ms,
        baseline_p75_ms=baseline.p75_ms,
        candidate_p25_ms=candidate.p25_ms,
        candidate_p75_ms=candidate.p75_ms,
        speedup_vs_baseline=compute_speedup_vs_baseline(
            baseline_median_ms=baseline.median_ms,
            candidate_median_ms=candidate.median_ms,
        ),
        correctness_prerequisite_passed=True,
        measurement_status=measurement_status,
        caveats=list(caveats),
        scientific_row_mutation_allowed=False,
        paper_scale_claim_allowed=False,
        profiler_traces_allowed=False,
    )


def _coerce_tensor_spec(value: TensorBenchmarkSpec | Mapping[str, Any]) -> TensorBenchmarkSpec:
    if isinstance(value, TensorBenchmarkSpec):
        spec = value
    elif isinstance(value, Mapping):
        spec = TensorBenchmarkSpec(
            shape_signature=str(value.get("shape_signature", "")),
            dtype=str(value.get("dtype", "")),
            device=str(value.get("device", "")),
        )
    else:
        raise TypeError("tensor spec must be a TensorBenchmarkSpec or mapping")
    if not spec.shape_signature or not spec.dtype or not spec.device:
        raise ValueError("tensor spec requires shape_signature, dtype, and device")
    return spec


def _coerce_timing_summary(value: TimingSummary | Mapping[str, Any]) -> TimingSummary:
    if isinstance(value, TimingSummary):
        summary = value
    elif isinstance(value, Mapping):
        summary = TimingSummary(
            median_ms=float(value.get("median_ms", 0)),
            p25_ms=float(value.get("p25_ms", 0)),
            p75_ms=float(value.get("p75_ms", 0)),
        )
    else:
        raise TypeError("timing summary must be a TimingSummary or mapping")
    _require_positive_finite(summary.median_ms, label="median_ms")
    _require_positive_finite(summary.p25_ms, label="p25_ms")
    _require_positive_finite(summary.p75_ms, label="p75_ms")
    if summary.p25_ms > summary.median_ms or summary.median_ms > summary.p75_ms:
        raise ValueError("timing summary must satisfy p25 <= median <= p75")
    return summary


def _sorted_positive_finite_samples(samples_ms: Sequence[float]) -> list[float]:
    if not samples_ms:
        raise ValueError("timing samples must not be empty")
    values: list[float] = []
    for index, value in enumerate(samples_ms):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"timing sample {index} must be numeric")
        numeric = float(value)
        _require_positive_finite(numeric, label=f"timing sample {index}")
        values.append(numeric)
    values.sort()
    return values


def _quantile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute quantile for empty samples")
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * q
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return float(sorted_values[lower_index])
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    weight = position - lower_index
    return float(lower + (upper - lower) * weight)


def _require_positive_finite(value: float, *, label: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be finite and positive")
