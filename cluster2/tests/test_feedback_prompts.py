"""Phase 8 tests for deterministic feedback prompt construction."""

from __future__ import annotations

import json

import pytest

from cluster1.data.kernels import KERNEL_SPECS
from cluster1.data.prompts.prompt_contract import build_prompt as build_cluster1_prompt
from cluster2.feedback.prompts import (
    FORBIDDEN_FEEDBACK_TERMS,
    GENERIC_EVAL_FAILURE_FEEDBACK,
    build_feedback_prompt,
    build_feedback_prompt_from_result,
    build_feedback_text,
    feedback_required_for_condition,
)
from shared.eval.failure_taxonomy import FAILURE_CODES
from shared.eval.schema import EvalResult


BASE_PROMPT = "Implement the relu kernel as a complete Triton Python module."
SOURCE = "@triton.jit\ndef relu_kernel(x, y, n:tl.constexpr):\n    return\n"


def _replay_eval_result_with_legacy_failure(condition: str) -> EvalResult:
    return EvalResult(
        kernel_id=None,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=None,
        condition=condition,
        sample_index=0,
        model_id="test-model",
        run_id="test-run",
        timestamp="2026-01-01T00:00:00Z",
        dtype_tested="fp32",
        source=SOURCE,
        source_hash="e" * 64,
        ast_hash=None,
        level_reached=0,
        parse_success=None,
        parse_error=None,
        has_triton_decorator=None,
        signature_valid=None,
        compile_success=False,
        compile_error="legacy compile failure",
        failure_code="CompilationError",
    )


def _eval_result_with_dtype_flags(
    *,
    correctness_error: str,
    repair_set_success: bool,
    eval_set_success: bool,
) -> EvalResult:
    return EvalResult(
        kernel_id=1,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=1,
        condition="C",
        sample_index=0,
        model_id="test-model",
        run_id="test-run",
        timestamp="2026-01-01T00:00:00Z",
        dtype_tested="fp32",
        source=SOURCE,
        source_hash="d" * 64,
        ast_hash=None,
        level_reached=2,
        parse_success=True,
        parse_error=None,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        compile_error=None,
        failure_code="F2_NUMERIC_LARGE",
        functional_success=False,
        correctness_error=correctness_error,
        dtype_results={
            "fp32": {
                "repair_set_success": repair_set_success,
                "eval_set_success": eval_set_success,
            }
        },
    )


@pytest.mark.parametrize("failure_code", sorted(FAILURE_CODES))
def test_feedback_prompt_is_deterministic_for_each_failure_code(
    failure_code: str,
) -> None:
    kwargs = {
        "condition": "C",
        "failure_code": failure_code,
        "base_prompt": BASE_PROMPT,
        "candidate_source": SOURCE,
        "public_failure_summary": "Repair shape (2,) failed Level 2: max_abs_diff=1",
        "functional_success": False,
        "repair_set_success": False,
        "eval_set_success": True,
    }

    first = build_feedback_prompt(**kwargs)
    second = build_feedback_prompt(**kwargs)

    assert first == second
    assert first is not None
    assert failure_code in first
    assert BASE_PROMPT in first
    assert "@triton.jit def relu_kernel" in first
    _assert_no_forbidden_terms(first)


def test_eval_set_failure_feedback_is_generic_and_redacted() -> None:
    feedback = build_feedback_text(
        condition="G+C",
        failure_code="F2_NUMERIC_LARGE",
        public_failure_summary=(
            "eval_shape_set shape (97,) max_abs_diff=99 hidden private edge cases"
        ),
        functional_success=False,
        repair_set_success=True,
        eval_set_success=False,
    )
    prompt = build_feedback_prompt(
        condition="G+C",
        failure_code="F2_NUMERIC_LARGE",
        base_prompt=BASE_PROMPT,
        candidate_source=SOURCE,
        public_failure_summary=(
            "eval_shape_set shape (97,) max_abs_diff=99 hidden private edge cases"
        ),
        functional_success=False,
        repair_set_success=True,
        eval_set_success=False,
    )

    assert feedback == GENERIC_EVAL_FAILURE_FEEDBACK
    assert prompt is not None
    assert GENERIC_EVAL_FAILURE_FEEDBACK in prompt
    assert "97" not in prompt
    assert "max_abs_diff=99" not in prompt
    _assert_no_forbidden_terms(prompt)


def test_eval_detail_fragment_is_redacted_without_split_flags() -> None:
    prompt = build_feedback_prompt(
        condition="C",
        failure_code="F2_NUMERIC_LARGE",
        base_prompt=BASE_PROMPT,
        candidate_source=SOURCE,
        public_failure_summary=(
            "Repair shape (2,) failed Level 2: max_abs_diff=1 | "
            "eval_shape_set shape (97,) max_abs_diff=99"
        ),
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    assert prompt is not None
    assert "Repair shape (2,)" in prompt
    assert "max_abs_diff=1" in prompt
    assert "97" not in prompt
    assert "max_abs_diff=99" not in prompt
    _assert_no_forbidden_terms(prompt)


def test_forbidden_terms_are_redacted_from_public_details() -> None:
    prompt = build_feedback_prompt(
        condition="C",
        failure_code="F1_COMPILE",
        base_prompt=BASE_PROMPT,
        candidate_source=SOURCE,
        public_failure_summary=(
            "LLVM PTX C++ traceback compute-sanitizer speedup fast@ nsight ncu "
            "nvml profil benchmark RL GRPO TRL hidden private edge cases extra shapes"
        ),
        compile_error="compile failed",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    assert prompt is not None
    assert "[redacted]" in prompt
    _assert_no_forbidden_terms(prompt)


def test_replay_controls_do_not_require_feedback_prompts() -> None:
    for condition in ("none", "G"):
        assert feedback_required_for_condition(condition) is False
        assert (
            build_feedback_text(
                condition=condition,
                failure_code="CompilationError",
                functional_success=False,
            )
            is None
        )
        assert (
            build_feedback_prompt(
                condition=condition,
                failure_code="CompilationError",
                base_prompt="",
                candidate_source=SOURCE,
                functional_success=False,
            )
            is None
        )


def test_result_helper_respects_replay_control_condition() -> None:
    for condition in ("none", "G"):
        result = _replay_eval_result_with_legacy_failure(condition)
        assert build_feedback_prompt_from_result(result, base_prompt="") is None


def test_result_helper_reads_level2_split_flags_from_dtype_results() -> None:
    result = _eval_result_with_dtype_flags(
        correctness_error="eval_shape_set shape (97,) max_abs_diff=99 hidden",
        repair_set_success=True,
        eval_set_success=False,
    )

    prompt = build_feedback_prompt_from_result(
        result,
        base_prompt=BASE_PROMPT,
        candidate_source=SOURCE,
    )

    assert prompt is not None
    assert prompt.count(GENERIC_EVAL_FAILURE_FEEDBACK) == 1
    assert "97" not in prompt
    assert "max_abs_diff=99" not in prompt
    assert "incorrect numeric values" not in prompt
    _assert_no_forbidden_terms(prompt)


def test_base_prompt_preserves_locked_cluster1_prompt_verbatim() -> None:
    base_prompt = build_cluster1_prompt(KERNEL_SPECS["elementwise"], "fp32")

    prompt = build_feedback_prompt(
        condition="C",
        failure_code="F1_COMPILE",
        base_prompt=base_prompt,
        candidate_source=SOURCE,
        public_failure_summary="compile failed",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    assert prompt is not None
    assert f"Base task:\n{base_prompt}\n\nPrevious source:" in prompt
    assert "Private Triton helper name" in prompt
    assert "- Define one private @triton.jit helper" in prompt


def test_feedback_serialization_has_no_eval_shape_or_forbidden_leakage() -> None:
    prompt = build_feedback_prompt(
        condition="C",
        failure_code="F2_SHAPE_MISMATCH",
        base_prompt=BASE_PROMPT,
        candidate_source=SOURCE,
        public_failure_summary="Repair shape (2,) failed Level 2: expected (2,), got (1,)",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=True,
    )
    rendered = json.dumps({"prompt": prompt}, sort_keys=True)

    assert "eval_shape_set" not in rendered
    assert "hidden" not in rendered.lower()
    assert "private" not in rendered.lower()
    assert "edge cases" not in rendered.lower()
    _assert_no_forbidden_terms(rendered)


def _assert_no_forbidden_terms(value: str) -> None:
    lowered = value.lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        assert term.lower() not in lowered
