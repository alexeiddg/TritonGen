"""Tests for shared failure taxonomy dispatch."""

from __future__ import annotations

import pytest

from shared.eval.failure_taxonomy import FAILURE_CODES, classify_failure
from shared.eval.schema import EvalResult


@pytest.mark.parametrize("failure_code", sorted(FAILURE_CODES))
def test_classifies_each_contract_failure_code(failure_code: str) -> None:
    result = _make_eval_result(failure_code=failure_code)

    assert classify_failure(result) == failure_code


def test_successful_result_returns_none() -> None:
    result = _make_eval_result(
        level_reached=1,
        parse_success=True,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        failure_code=None,
    )

    assert classify_failure(result) is None


def test_maps_cluster1_legacy_compile_error_types() -> None:
    assert classify_failure(_make_eval_result(failure_code="CompilationError")) == "F1_COMPILE"
    assert classify_failure(_make_eval_result(failure_code="RuntimeError")) == "F1_RUNTIME"
    assert classify_failure(_make_eval_result(failure_code="SignatureError")) == "F0_BAD_SIGNATURE"


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
