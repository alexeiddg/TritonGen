"""Deterministic Level 2 correctness evaluation for the locked C2 archetypes.

This module compares a caller-provided candidate output runner against the
isolated reference wrapper over the procedural repair/eval shape sets. It does
not compile Triton, call Modal, run a repair loop, or retry candidates.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Final

from shared.eval.correctness_shapes import (
    DEFAULT_SHAPES_PER_SPLIT,
    CorrectnessShapeSets,
    Shape,
    ShapeSplit,
    generate_correctness_shape_sets,
    get_shape_metadata,
    validate_shape_for_kernel,
)
from shared.eval.reference_runner import make_reference_inputs, run_reference
from shared.eval.tolerances import get_tolerances


GENERIC_EVAL_FAILURE_FEEDBACK: Final = (
    "The previous attempt passed initial correctness shapes but failed Level 2. "
    "Produce a corrected complete Triton Python module."
)
_MAX_ERROR_CHARS: Final = 500
_FLOAT_EPSILON: Final = 1e-12


@dataclass(frozen=True)
class Level2CandidateRequest:
    """One deterministic candidate-output request for a shape cell."""

    kernel_class: str
    kernel_name: str
    dtype: str
    shape: Shape
    base_seed: int
    attempt_index: int
    split: ShapeSplit
    inputs: tuple[Any, ...]


Level2CandidateRunner = Callable[[Level2CandidateRequest], Any]


@dataclass(frozen=True)
class Level2ShapeResult:
    """Visible per-shape result for repair-set feedback."""

    shape: Shape
    passed: bool
    failure_code: str | None
    error: str | None
    max_abs_diff: float | None
    max_rel_diff: float | None
    atol: float
    rtol: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _ShapeComparison:
    passed: bool
    failure_code: str | None
    error: str | None
    max_abs_diff: float | None
    max_rel_diff: float | None


@dataclass(frozen=True)
class Level2CorrectnessResult:
    """Public Level 2 result with eval-set details kept private."""

    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    attempt_index: int
    functional_success: bool
    repair_set_success: bool
    eval_set_success: bool
    failure_code: str | None
    correctness_error: str | None
    feedback: str | None
    num_repair_shapes: int
    num_eval_shapes: int
    num_test_shapes: int
    shapes_passed: int
    repair_shapes_passed: int
    eval_shapes_passed: int
    max_abs_diff: float | None
    max_rel_diff: float | None
    atol: float
    rtol: float
    repair_shape_results: tuple[Level2ShapeResult, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["repair_shape_results"] = [
            result.to_dict() for result in self.repair_shape_results
        ]
        return payload

    def to_eval_fields(self) -> dict[str, Any]:
        """Return fields that map onto the shared ``EvalResult`` Level 2 surface."""

        return {
            "functional_success": self.functional_success,
            "correctness_error": self.correctness_error,
            "max_abs_diff": self.max_abs_diff,
            "max_rel_diff": self.max_rel_diff,
            "num_test_shapes": self.num_test_shapes,
            "shapes_passed": self.shapes_passed,
            "dtype_results": {
                self.dtype: {
                    "functional_success": self.functional_success,
                    "repair_set_success": self.repair_set_success,
                    "eval_set_success": self.eval_set_success,
                    "failure_code": self.failure_code,
                    "num_repair_shapes": self.num_repair_shapes,
                    "num_eval_shapes": self.num_eval_shapes,
                    "repair_shapes_passed": self.repair_shapes_passed,
                    "eval_shapes_passed": self.eval_shapes_passed,
                    "atol": self.atol,
                    "rtol": self.rtol,
                }
            },
        }


def evaluate_level2_correctness(
    kernel_class: str,
    dtype: str,
    candidate_runner: Level2CandidateRunner,
    *,
    base_seed: int,
    attempt_index: int = 0,
    shape_sets: CorrectnessShapeSets | None = None,
    shapes_per_split: int = DEFAULT_SHAPES_PER_SPLIT,
    device: str = "cpu",
) -> Level2CorrectnessResult:
    """Evaluate one candidate over deterministic repair and eval shape sets."""

    metadata = get_shape_metadata(kernel_class)
    _require_int(base_seed, "base_seed")
    _require_non_negative_int(attempt_index, "attempt_index")
    if not callable(candidate_runner):
        raise TypeError("candidate_runner must be callable")

    if shape_sets is None:
        shape_sets = generate_correctness_shape_sets(
            metadata.kernel_class,
            dtype,
            base_seed=base_seed,
            shapes_per_split=shapes_per_split,
        )
    _validate_shape_sets(shape_sets, metadata.kernel_class, dtype, base_seed)

    _configure_torch_determinism()
    tolerances = get_tolerances(metadata.kernel_class, dtype)
    atol = float(tolerances["atol"])
    rtol = float(tolerances["rtol"])

    repair_results = _evaluate_shape_split(
        metadata.kernel_class,
        metadata.kernel_name,
        dtype,
        shape_sets.repair_shape_set,
        split="repair",
        base_seed=base_seed,
        attempt_index=attempt_index,
        candidate_runner=candidate_runner,
        atol=atol,
        rtol=rtol,
        device=device,
    )
    eval_results = _evaluate_shape_split(
        metadata.kernel_class,
        metadata.kernel_name,
        dtype,
        shape_sets.eval_shape_set,
        split="eval",
        base_seed=base_seed,
        attempt_index=attempt_index,
        candidate_runner=candidate_runner,
        atol=atol,
        rtol=rtol,
        device=device,
    )

    repair_set_success = all(result.passed for result in repair_results)
    eval_set_success = all(result.passed for result in eval_results)
    functional_success = repair_set_success and eval_set_success

    repair_shapes_passed = sum(result.passed for result in repair_results)
    eval_shapes_passed = sum(result.passed for result in eval_results)
    repair_visible_max_abs = _max_optional(result.max_abs_diff for result in repair_results)
    repair_visible_max_rel = _max_optional(result.max_rel_diff for result in repair_results)

    failure_code: str | None
    correctness_error: str | None
    feedback: str | None
    if functional_success:
        failure_code = None
        correctness_error = None
        feedback = None
    elif repair_set_success:
        first_eval_failure = _first_failure(eval_results)
        failure_code = (
            first_eval_failure.failure_code
            if first_eval_failure is not None
            else "F2_NUMERIC_LARGE"
        )
        correctness_error = GENERIC_EVAL_FAILURE_FEEDBACK
        feedback = GENERIC_EVAL_FAILURE_FEEDBACK
    else:
        first_repair_failure = _first_failure(repair_results)
        failure_code = (
            first_repair_failure.failure_code
            if first_repair_failure is not None
            else "F2_NUMERIC_LARGE"
        )
        correctness_error = _repair_feedback(first_repair_failure)
        feedback = correctness_error

    return Level2CorrectnessResult(
        kernel_class=metadata.kernel_class,
        kernel_name=metadata.kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        attempt_index=attempt_index,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        failure_code=failure_code,
        correctness_error=correctness_error,
        feedback=feedback,
        num_repair_shapes=len(repair_results),
        num_eval_shapes=len(eval_results),
        num_test_shapes=len(repair_results) + len(eval_results),
        shapes_passed=repair_shapes_passed + eval_shapes_passed,
        repair_shapes_passed=repair_shapes_passed,
        eval_shapes_passed=eval_shapes_passed,
        max_abs_diff=repair_visible_max_abs,
        max_rel_diff=repair_visible_max_rel,
        atol=atol,
        rtol=rtol,
        repair_shape_results=repair_results,
    )


def _evaluate_shape_split(
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    shapes: Sequence[Shape],
    *,
    split: ShapeSplit,
    base_seed: int,
    attempt_index: int,
    candidate_runner: Level2CandidateRunner,
    atol: float,
    rtol: float,
    device: str,
) -> tuple[Level2ShapeResult, ...]:
    results: list[Level2ShapeResult] = []
    for shape in shapes:
        validated_shape = validate_shape_for_kernel(kernel_class, shape)
        inputs = make_reference_inputs(
            kernel_name,
            dtype,
            validated_shape,
            base_seed=base_seed,
            attempt_index=attempt_index,
            split=split,
            device=device,
        )
        reference = run_reference(
            kernel_class,
            dtype,
            validated_shape,
            base_seed=base_seed,
            attempt_index=attempt_index,
            split=split,
            device=device,
        )
        request = Level2CandidateRequest(
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            shape=validated_shape,
            base_seed=base_seed,
            attempt_index=attempt_index,
            split=split,
            inputs=inputs,
        )
        try:
            candidate_output = candidate_runner(request)
            comparison = _compare_outputs(
                candidate_output,
                reference.output,
                atol=atol,
                rtol=rtol,
            )
        except Exception as exc:
            comparison = _ShapeComparison(
                passed=False,
                failure_code="F1_RUNTIME",
                error=_truncate_error(
                    f"Candidate output runner raised {type(exc).__name__}: {exc}"
                ),
                max_abs_diff=None,
                max_rel_diff=None,
            )
        results.append(
            Level2ShapeResult(
                shape=validated_shape,
                passed=comparison.passed,
                failure_code=comparison.failure_code,
                error=comparison.error,
                max_abs_diff=comparison.max_abs_diff,
                max_rel_diff=comparison.max_rel_diff,
                atol=atol,
                rtol=rtol,
            )
        )
    return tuple(results)


def _compare_outputs(
    candidate_output: Any,
    reference_output: Any,
    *,
    atol: float,
    rtol: float,
) -> _ShapeComparison:
    candidate_values = _flatten_output(candidate_output)
    reference_values = _flatten_output(reference_output)
    if len(candidate_values) != len(reference_values):
        return _ShapeComparison(
            passed=False,
            failure_code="F2_SHAPE_MISMATCH",
            error=(
                "Output arity mismatch: expected "
                f"{len(reference_values)}, got {len(candidate_values)}"
            ),
            max_abs_diff=None,
            max_rel_diff=None,
        )

    max_abs_values: list[float] = []
    max_rel_values: list[float] = []
    for candidate_value, reference_value in zip(
        candidate_values,
        reference_values,
        strict=True,
    ):
        tensor_check = _compare_tensor_like(
            candidate_value,
            reference_value,
            atol=atol,
            rtol=rtol,
        )
        if not tensor_check.passed:
            return tensor_check
        if tensor_check.max_abs_diff is not None:
            max_abs_values.append(tensor_check.max_abs_diff)
        if tensor_check.max_rel_diff is not None:
            max_rel_values.append(tensor_check.max_rel_diff)

    return _ShapeComparison(
        passed=True,
        failure_code=None,
        error=None,
        max_abs_diff=max(max_abs_values, default=0.0),
        max_rel_diff=max(max_rel_values, default=0.0),
    )


def _compare_tensor_like(
    candidate_value: Any,
    reference_value: Any,
    *,
    atol: float,
    rtol: float,
) -> _ShapeComparison:
    torch = _torch()
    candidate = _as_cpu_tensor(candidate_value, torch)
    reference = _as_cpu_tensor(reference_value, torch)

    if tuple(candidate.shape) != tuple(reference.shape):
        return _ShapeComparison(
            passed=False,
            failure_code="F2_SHAPE_MISMATCH",
            error=(
                "Output shape mismatch: expected "
                f"{tuple(reference.shape)}, got {tuple(candidate.shape)}"
            ),
            max_abs_diff=None,
            max_rel_diff=None,
        )

    candidate_float = candidate.to(dtype=torch.float64)
    reference_float = reference.to(dtype=torch.float64)
    if bool(torch.isnan(candidate_float).any().item()) or bool(
        torch.isinf(candidate_float).any().item()
    ):
        return _ShapeComparison(
            passed=False,
            failure_code="F2_NUMERIC_NAN",
            error="Candidate output contains NaN or Inf",
            max_abs_diff=None,
            max_rel_diff=None,
        )
    if bool(torch.isnan(reference_float).any().item()) or bool(
        torch.isinf(reference_float).any().item()
    ):
        return _ShapeComparison(
            passed=False,
            failure_code="F2_NUMERIC_NAN",
            error="Reference output contains NaN or Inf",
            max_abs_diff=None,
            max_rel_diff=None,
        )

    diff = torch.abs(candidate_float - reference_float)
    max_abs_diff = _tensor_max(diff)
    denominator = torch.clamp(torch.abs(reference_float), min=_FLOAT_EPSILON)
    max_rel_diff = _tensor_max(diff / denominator)
    passed = bool(torch.allclose(candidate_float, reference_float, atol=atol, rtol=rtol))
    if passed:
        return _ShapeComparison(
            passed=True,
            failure_code=None,
            error=None,
            max_abs_diff=max_abs_diff,
            max_rel_diff=max_rel_diff,
        )
    return _ShapeComparison(
        passed=False,
        failure_code="F2_NUMERIC_LARGE",
        error=(
            "Numeric mismatch: "
            f"max_abs_diff={max_abs_diff:.6g}, max_rel_diff={max_rel_diff:.6g}, "
            f"atol={atol:.6g}, rtol={rtol:.6g}"
        ),
        max_abs_diff=max_abs_diff,
        max_rel_diff=max_rel_diff,
    )


def _as_cpu_tensor(value: Any, torch: Any) -> Any:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "is_sparse") and value.is_sparse:
        value = value.to_dense()
    if hasattr(value, "shape") and hasattr(value, "to"):
        return value
    return torch.as_tensor(value)


def _tensor_max(tensor: Any) -> float:
    if tensor.numel() == 0:
        return 0.0
    return float(tensor.max().item())


def _flatten_output(output: Any) -> tuple[Any, ...]:
    if isinstance(output, tuple):
        return tuple(item for value in output for item in _flatten_output(value))
    if isinstance(output, list):
        return tuple(item for value in output for item in _flatten_output(value))
    return (output,)


def _validate_shape_sets(
    shape_sets: CorrectnessShapeSets,
    kernel_class: str,
    dtype: str,
    base_seed: int,
) -> None:
    if shape_sets.kernel_class != kernel_class:
        raise ValueError(
            f"shape_sets kernel_class {shape_sets.kernel_class!r} does not match "
            f"{kernel_class!r}"
        )
    if shape_sets.dtype != dtype:
        raise ValueError(f"shape_sets dtype {shape_sets.dtype!r} does not match {dtype!r}")
    if shape_sets.base_seed != base_seed:
        raise ValueError(
            f"shape_sets base_seed {shape_sets.base_seed!r} does not match {base_seed!r}"
        )
    if not shape_sets.repair_shape_set:
        raise ValueError("repair_shape_set must not be empty")
    if not shape_sets.eval_shape_set:
        raise ValueError("eval_shape_set must not be empty")
    if set(shape_sets.repair_shape_set) & set(shape_sets.eval_shape_set):
        raise ValueError("repair_shape_set and eval_shape_set must be disjoint")
    for shape in shape_sets.repair_shape_set + shape_sets.eval_shape_set:
        validate_shape_for_kernel(kernel_class, shape)


def _first_failure(results: Sequence[Level2ShapeResult]) -> Level2ShapeResult | None:
    return next((result for result in results if not result.passed), None)


def _repair_feedback(result: Level2ShapeResult | None) -> str:
    if result is None:
        return "Level 2 repair correctness failed"
    detail = result.error or "repair shape did not match reference output"
    return f"Repair shape {result.shape} failed Level 2: {detail}"


def _max_optional(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return max(present)


def _truncate_error(error: str) -> str:
    return " ".join(error.split())[:_MAX_ERROR_CHARS]


def _require_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")


def _require_non_negative_int(value: int, field_name: str) -> None:
    _require_int(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _configure_torch_determinism() -> None:
    torch = _torch()
    use_deterministic = getattr(torch, "use_deterministic_algorithms", None)
    if callable(use_deterministic):
        try:
            use_deterministic(True, warn_only=True)
        except TypeError:
            use_deterministic(True)

    backends = getattr(torch, "backends", None)
    cuda_backend = getattr(backends, "cuda", None)
    matmul_backend = getattr(cuda_backend, "matmul", None)
    _set_existing_attr(matmul_backend, "allow_tf32", False)

    cudnn_backend = getattr(backends, "cudnn", None)
    _set_existing_attr(cudnn_backend, "allow_tf32", False)
    _set_existing_attr(cudnn_backend, "deterministic", True)
    _set_existing_attr(cudnn_backend, "benchmark", False)


def _set_existing_attr(target: Any, name: str, value: Any) -> None:
    if target is not None and hasattr(target, name):
        setattr(target, name, value)


def _torch() -> Any:
    import torch

    return torch
