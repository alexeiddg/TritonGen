"""Phase 8 tests for compact feedback trace summaries."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

from cluster2.feedback.prompts import (
    FORBIDDEN_FEEDBACK_TERMS,
    GENERIC_EVAL_FAILURE_FEEDBACK,
)
from cluster2.feedback.trace import (
    TraceSummary,
    build_trace_summary,
    build_trace_summary_from_result,
    trace_required_for_condition,
)
from shared.eval.schema import EvalResult


SOURCE = "@triton.jit\ndef relu_kernel(x, y, n:tl.constexpr):\n    return\n"


def _eval_result_with_dtype_flags(
    *,
    condition: str = "C",
    correctness_error: str,
    repair_iteration: int,
    source_hash: str = "c" * 64,
    repair_set_success: bool,
    eval_set_success: bool | None,
) -> EvalResult:
    return EvalResult(
        kernel_id=1,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=1,
        condition=condition,
        sample_index=0,
        model_id="test-model",
        run_id="test-run",
        timestamp="2026-01-01T00:00:00Z",
        dtype_tested="fp32",
        source=SOURCE,
        source_hash=source_hash,
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
        repair_iteration=repair_iteration,
    )


def test_trace_summary_excludes_full_source_by_default() -> None:
    summary = build_trace_summary(
        condition="C",
        attempt_index=1,
        failure_code="F2_NUMERIC_LARGE",
        public_failure_summary="Repair shape (2,) failed Level 2: max_abs_diff=1",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=True,
        source=SOURCE,
    )

    assert summary is not None
    payload = summary.to_dict()
    assert set(payload) == {
        "attempt_index",
        "failure_code",
        "public_failure_summary",
        "functional_success",
        "repair_set_success",
        "eval_set_success",
        "source_hash",
    }
    assert "source" not in payload
    assert SOURCE not in json.dumps(payload, sort_keys=True)
    assert payload["source_hash"] == hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()


def test_trace_summary_excludes_timing_performance_and_token_fields() -> None:
    summary = build_trace_summary(
        condition="G+C",
        attempt_index=2,
        failure_code="F1_COMPILE",
        public_failure_summary=(
            "tokens_input timing performance speedup profile benchmark eval_shape_set "
            "hidden private edge cases extra shapes"
        ),
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    assert summary is not None
    rendered = summary.to_json()
    lowered = rendered.lower()
    for forbidden_field in (
        "token",
        "timing",
        "performance",
        "speed",
        "profile",
        "benchmark",
    ):
        assert forbidden_field not in lowered
    _assert_no_forbidden_terms(rendered)


def test_eval_failure_trace_summary_is_generic_and_redacted() -> None:
    summary = build_trace_summary(
        condition="C",
        attempt_index=3,
        failure_code="F2_NUMERIC_LARGE",
        public_failure_summary="eval_shape_set shape (97,) max_abs_diff=99 hidden",
        functional_success=False,
        repair_set_success=True,
        eval_set_success=False,
    )

    assert summary is not None
    assert summary.public_failure_summary == GENERIC_EVAL_FAILURE_FEEDBACK
    rendered = summary.to_json()
    assert "97" not in rendered
    assert "max_abs_diff" not in rendered
    _assert_no_forbidden_terms(rendered)


def test_eval_detail_fragment_is_redacted_from_trace_without_split_flags() -> None:
    summary = build_trace_summary(
        condition="C",
        attempt_index=4,
        failure_code="F2_NUMERIC_LARGE",
        public_failure_summary=(
            "Repair shape (2,) failed Level 2: max_abs_diff=1 | "
            "eval_shape_set shape (97,) max_abs_diff=99"
        ),
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    assert summary is not None
    rendered = summary.to_json()
    assert "Repair shape (2,)" in rendered
    assert "max_abs_diff=1" in rendered
    assert "97" not in rendered
    assert "max_abs_diff=99" not in rendered
    _assert_no_forbidden_terms(rendered)


def test_trace_serialization_is_deterministic() -> None:
    summary = build_trace_summary(
        condition="C",
        attempt_index=0,
        failure_code="F0_PARSE",
        public_failure_summary="line 1 syntax error",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
        source_hash="a" * 64,
    )

    assert summary is not None
    rendered = summary.to_json()
    assert rendered == json.dumps(
        summary.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert TraceSummary.from_dict(json.loads(rendered)) == summary
    assert TraceSummary.from_dict(json.loads(rendered)).to_json() == rendered


def test_replay_controls_do_not_need_trace_summaries() -> None:
    for condition in ("none", "G"):
        assert trace_required_for_condition(condition) is False
        assert (
            build_trace_summary(
                condition=condition,
                attempt_index=0,
                failure_code="F1_COMPILE",
                public_failure_summary="compile failed",
                functional_success=False,
                repair_set_success=False,
                eval_set_success=None,
            )
            is None
        )


def test_result_helper_skips_replay_control_without_trace_fields() -> None:
    result = SimpleNamespace(
        condition="none",
        failure_code="CompilationError",
    )

    assert build_trace_summary_from_result(result) is None


def test_result_helper_uses_repair_iteration_fallback() -> None:
    result = SimpleNamespace(
        condition="C",
        repair_iteration=4,
        failure_code="F1_RUNTIME",
        correctness_error="runtime failure",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=None,
    )

    summary = build_trace_summary_from_result(result, source_hash="b" * 64)

    assert summary is not None
    assert summary.attempt_index == 4
    assert summary.source_hash == "b" * 64


def test_result_helper_preserves_source_hash_from_result() -> None:
    result = _eval_result_with_dtype_flags(
        repair_iteration=1,
        source_hash="c" * 64,
        correctness_error="runtime failure",
        repair_set_success=False,
        eval_set_success=None,
    )

    summary = build_trace_summary_from_result(result)

    assert summary is not None
    assert summary.source_hash == "c" * 64


def test_result_helper_reads_level2_split_flags_for_eval_failure_trace() -> None:
    result = _eval_result_with_dtype_flags(
        condition="G+C",
        repair_iteration=2,
        correctness_error="eval_shape_set shape (97,) max_abs_diff=99 hidden",
        repair_set_success=True,
        eval_set_success=False,
    )

    summary = build_trace_summary_from_result(result)

    assert summary is not None
    assert summary.public_failure_summary == GENERIC_EVAL_FAILURE_FEEDBACK
    rendered = summary.to_json()
    assert "97" not in rendered
    assert "max_abs_diff=99" not in rendered
    _assert_no_forbidden_terms(rendered)


def _assert_no_forbidden_terms(value: str) -> None:
    lowered = value.lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        assert term.lower() not in lowered
