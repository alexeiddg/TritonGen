"""Phase 3 failure taxonomy checks."""

from __future__ import annotations

from shared.eval.failure_taxonomy import FAILURE_CODES, classify_failure
from shared.eval.schema import EvalResult


def test_f0_surface_violation_is_registered() -> None:
    assert "F0_SURFACE_VIOLATION" in FAILURE_CODES


def test_classifies_explicit_f0_surface_violation() -> None:
    result = _make_eval_result(failure_code="F0_SURFACE_VIOLATION")

    assert classify_failure(result) == "F0_SURFACE_VIOLATION"


def test_f3_eval_pipeline_is_registered_and_preserved() -> None:
    assert "F3_EVAL_PIPELINE" in FAILURE_CODES

    result = _make_eval_result(failure_code="F3_EVAL_PIPELINE")

    assert classify_failure(result) == "F3_EVAL_PIPELINE"


def test_classifies_level0_sanitizer_failure_as_surface_violation() -> None:
    result = _make_eval_result(
        safe_success=False,
        sanitizer_tool="level0_ast_sanitizer",
        sanitizer_errors=[
            "F0_SURFACE_VIOLATION: line 8: torch compute call 'torch.relu' is not allowed"
        ],
    )

    assert classify_failure(result) == "F0_SURFACE_VIOLATION"


def test_classifies_level0_sanitizer_parse_failure_as_parse() -> None:
    result = _make_eval_result(
        safe_success=False,
        sanitizer_tool="level0_ast_sanitizer",
        sanitizer_errors=["F0_PARSE: line 1: SyntaxError: invalid syntax"],
    )

    assert classify_failure(result) == "F0_PARSE"


def _make_eval_result(**overrides) -> EvalResult:
    defaults = {
        "kernel_id": 19,
        "kernel_name": "relu",
        "kernel_class": "elementwise",
        "kernelbench_level": 1,
        "condition": "none",
        "sample_index": 0,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "run_id": "rid",
        "timestamp": "2026-05-05T00:00:00+00:00",
        "dtype_tested": "fp32",
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "source_hash": "hash",
        "ast_hash": None,
        "level_reached": 0,
        "parse_success": None,
        "parse_error": None,
        "has_triton_decorator": None,
        "signature_valid": None,
        "compile_success": None,
        "compile_error": None,
        "failure_code": None,
    }
    defaults.update(overrides)
    return EvalResult(**defaults)
