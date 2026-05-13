"""Tests for Phase 4 deterministic Level 2 correctness."""

from __future__ import annotations

import json

import pytest

from shared.eval.correctness_shapes import CorrectnessShapeSets
from shared.eval.failure_taxonomy import classify_failure
from shared.eval.levels.level2_correctness import (
    GENERIC_EVAL_FAILURE_FEEDBACK,
    Level2CandidateRequest,
    evaluate_level2_correctness,
)
from shared.eval.schema import EvalResult
from shared.tests.level2_fake_torch import install_fake_level2_runtime


@pytest.fixture(autouse=True)
def fake_level2_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_level2_runtime(monkeypatch)


def test_level2_success_requires_repair_and_eval_sets() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),))

    passing = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _matching_candidate,
        base_seed=7,
        shape_sets=shape_sets,
    )
    eval_failure = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="eval"),
        base_seed=7,
        shape_sets=shape_sets,
    )

    assert passing.repair_set_success is True
    assert passing.eval_set_success is True
    assert passing.functional_success is True
    assert eval_failure.repair_set_success is True
    assert eval_failure.eval_set_success is False
    assert eval_failure.functional_success is False


def test_eval_failure_feedback_is_generic_and_hides_eval_shape_details() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((97,),))

    result = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="eval"),
        base_seed=7,
        shape_sets=shape_sets,
    )
    payload = result.to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert result.repair_set_success is True
    assert result.eval_set_success is False
    assert result.feedback == GENERIC_EVAL_FAILURE_FEEDBACK
    assert result.correctness_error == GENERIC_EVAL_FAILURE_FEEDBACK
    assert "97" not in rendered
    assert "eval_shape_set" not in rendered
    assert "diff tensor" not in rendered.lower()
    assert "edge case" not in rendered.lower()


def test_repair_failure_feedback_may_include_repair_shape_and_diff() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),))

    result = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="repair"),
        base_seed=7,
        shape_sets=shape_sets,
    )

    assert result.repair_set_success is False
    assert result.eval_set_success is True
    assert result.functional_success is False
    assert result.failure_code == "F2_NUMERIC_LARGE"
    assert result.feedback is not None
    assert "Repair shape (2,)" in result.feedback
    assert "max_abs_diff=" in result.feedback
    assert result.max_abs_diff is not None
    assert result.max_abs_diff > result.atol


def test_level2_outputs_are_deterministic() -> None:
    shape_sets = _elementwise_shape_sets(
        repair=((2,), (5,)),
        eval_=((3,), (7,)),
        base_seed=123,
    )

    first = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="eval"),
        base_seed=123,
        attempt_index=2,
        shape_sets=shape_sets,
    )
    second = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="eval"),
        base_seed=123,
        attempt_index=2,
        shape_sets=shape_sets,
    )

    assert first.to_dict() == second.to_dict()


def test_level2_applies_pinned_tolerances() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=9)

    within_tolerance = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=5e-6),
        base_seed=9,
        shape_sets=shape_sets,
    )
    outside_tolerance = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1e-3),
        base_seed=9,
        shape_sets=shape_sets,
    )

    assert within_tolerance.atol == pytest.approx(1e-5)
    assert within_tolerance.rtol == pytest.approx(1e-5)
    assert within_tolerance.functional_success is True
    assert outside_tolerance.functional_success is False
    assert outside_tolerance.failure_code == "F2_NUMERIC_LARGE"


def test_level2_failure_taxonomy_mapping() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=5)

    numeric = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _offset_candidate(offset=1.0, only_split="repair"),
        base_seed=5,
        shape_sets=shape_sets,
    )
    nan = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _nan_candidate,
        base_seed=5,
        shape_sets=shape_sets,
    )
    shape = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _shape_mismatch_candidate,
        base_seed=5,
        shape_sets=shape_sets,
    )

    assert numeric.failure_code == "F2_NUMERIC_LARGE"
    assert nan.failure_code == "F2_NUMERIC_NAN"
    assert shape.failure_code == "F2_SHAPE_MISMATCH"
    assert classify_failure(_eval_result_from_level2(numeric)) == "F2_NUMERIC_LARGE"
    assert classify_failure(_eval_result_from_level2(nan)) == "F2_NUMERIC_NAN"
    assert classify_failure(_eval_result_from_level2(shape)) == "F2_SHAPE_MISMATCH"


def test_level2_public_output_has_no_performance_fields() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),))

    result = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _matching_candidate,
        base_seed=7,
        shape_sets=shape_sets,
    )
    rendered = json.dumps(result.to_dict(), sort_keys=True).lower()

    assert "timing" not in rendered
    assert "performance" not in rendered
    assert "speedup" not in rendered
    assert "profiling" not in rendered


@pytest.mark.parametrize(
    ("repair", "eval_", "message"),
    (
        ((), ((3,),), "repair_shape_set must not be empty"),
        (((2,),), (), "eval_shape_set must not be empty"),
    ),
)
def test_level2_rejects_empty_shape_sets(
    repair: tuple[tuple[int, ...], ...],
    eval_: tuple[tuple[int, ...], ...],
    message: str,
) -> None:
    shape_sets = _elementwise_shape_sets(repair=repair, eval_=eval_)

    with pytest.raises(ValueError, match=message):
        evaluate_level2_correctness(
            "elementwise",
            "fp32",
            _matching_candidate,
            base_seed=7,
            shape_sets=shape_sets,
        )


def test_level2_configures_torch_determinism_flags() -> None:
    import torch

    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),))

    result = evaluate_level2_correctness(
        "elementwise",
        "fp32",
        _matching_candidate,
        base_seed=7,
        shape_sets=shape_sets,
    )

    assert result.functional_success is True
    assert torch._deterministic_algorithms is True
    assert torch._deterministic_warn_only is True
    assert torch.backends.cuda.matmul.allow_tf32 is False
    assert torch.backends.cudnn.allow_tf32 is False
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False


def _matching_candidate(request: Level2CandidateRequest):
    import torch

    if request.kernel_name == "relu":
        return torch.relu(request.inputs[0])
    if request.kernel_name == "softmax":
        return torch.softmax(request.inputs[0], dim=1)
    if request.kernel_name == "gemm":
        return torch.matmul(request.inputs[0], request.inputs[1])
    raise AssertionError(f"unexpected kernel {request.kernel_name!r}")


def _offset_candidate(
    *,
    offset: float,
    only_split: str | None = None,
):
    def run(request: Level2CandidateRequest):
        output = _matching_candidate(request)
        if only_split is not None and request.split != only_split:
            return output
        return output + offset

    return run


def _nan_candidate(request: Level2CandidateRequest):
    return _matching_candidate(request).clone().with_first(float("nan"))


def _shape_mismatch_candidate(request: Level2CandidateRequest):
    import torch

    del request
    return torch.zeros((1,), dtype=torch.float32)


def _elementwise_shape_sets(
    *,
    repair: tuple[tuple[int, ...], ...],
    eval_: tuple[tuple[int, ...], ...],
    base_seed: int = 7,
) -> CorrectnessShapeSets:
    return CorrectnessShapeSets(
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=base_seed,
        repair_shape_set=repair,
        eval_shape_set=eval_,
    )


def _eval_result_from_level2(level2_result) -> EvalResult:
    return EvalResult(
        kernel_id=19,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=1,
        condition="C",
        sample_index=0,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        run_id="rid",
        timestamp="2026-05-13T00:00:00+00:00",
        dtype_tested="fp32",
        source="import triton\n@triton.jit\ndef k(): pass",
        source_hash="hash",
        ast_hash=None,
        level_reached=2,
        parse_success=True,
        parse_error=None,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        compile_error=None,
        failure_code=level2_result.failure_code,
        functional_success=level2_result.functional_success,
        correctness_error=level2_result.correctness_error,
        max_abs_diff=level2_result.max_abs_diff,
        max_rel_diff=level2_result.max_rel_diff,
        num_test_shapes=level2_result.num_test_shapes,
        shapes_passed=level2_result.shapes_passed,
        dtype_results=level2_result.to_eval_fields()["dtype_results"],
    )
