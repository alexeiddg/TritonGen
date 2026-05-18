"""Tests for EvalResult-lite schema and Cluster 1 adapter."""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from cluster1.results.dataclass import GenerationResult
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.schema import EvalResult, LEVEL_2_TO_4_FIELDS, RepairTrace, append_result


def test_eval_result_fully_populated_json_round_trip() -> None:
    result = _make_fully_populated_eval_result()

    rebuilt = EvalResult.from_dict(json.loads(result.to_json()))

    assert rebuilt == result
    assert rebuilt.to_dict() == result.to_dict()


def test_eval_result_level1_only_json_round_trip_preserves_none() -> None:
    result = _make_eval_result()

    rebuilt = EvalResult.from_dict(json.loads(result.to_json()))

    assert rebuilt == result
    for field_name in LEVEL_2_TO_4_FIELDS:
        assert getattr(rebuilt, field_name) is None


def test_eval_result_nullable_future_fields_remain_none() -> None:
    result = _make_eval_result()

    for field_name in LEVEL_2_TO_4_FIELDS:
        assert getattr(result, field_name) is None


def test_eval_result_from_dict_rejects_unknown_extra_fields() -> None:
    payload = _make_eval_result().to_dict()
    payload["unexpected"] = "value"

    with pytest.raises(ValueError, match="unknown EvalResult fields"):
        EvalResult.from_dict(payload)


def test_eval_result_from_dict_rejects_missing_required_fields() -> None:
    payload = _make_eval_result().to_dict()
    del payload["kernel_name"]

    with pytest.raises(ValueError, match="invalid EvalResult payload"):
        EvalResult.from_dict(payload)


def test_append_result_writes_jsonl_one_object_per_line(tmp_path) -> None:
    path = tmp_path / "nested" / "eval_results.jsonl"
    first = _make_eval_result(run_id="one", sample_index=0)
    second = _make_eval_result(run_id="two", sample_index=1)

    append_result(path, first)
    append_result(path, second)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(line.startswith("{") and line.endswith("}") for line in lines)
    assert [EvalResult.from_dict(json.loads(line)) for line in lines] == [first, second]


def test_generation_result_converts_to_eval_result_for_baseline() -> None:
    row = _make_generation_result(
        grammar_active=False,
        masked_token_rate=None,
        compile_success=True,
    )

    result = eval_result_from_generation_result(row, sample_index=3)

    assert result.condition == "none"
    assert result.sample_index == 3
    assert result.kernel_name == row.kernel_name
    assert result.kernel_class == row.kernel_class
    assert result.model_id == row.model_id
    assert result.run_id == row.run_id
    assert result.timestamp == row.timestamp_utc
    assert result.dtype_tested == row.dtype
    assert result.source == row.source
    assert result.source_hash == row.unique_solution_hash
    assert result.ast_hash is None
    assert result.compile_success is True
    assert result.compile_error is None
    assert result.failure_code is None
    assert result.level_reached == 1


def test_generation_result_converts_to_eval_result_for_g() -> None:
    row = _make_generation_result(
        grammar_active=True,
        masked_token_rate=0.25,
        compile_success=False,
        compile_results_by_dtype={"fp32": True, "fp16": False, "bf16": True},
        compile_error_type="CompilationError",
        compile_error_msg="bad generated IR",
        failure_code="F1_COMPILE",
    )

    result = eval_result_from_generation_result(row)

    assert result.condition == "G"
    assert result.compile_success is False
    assert result.compile_error == "bad generated IR"
    assert result.failure_code == "F1_COMPILE"
    assert result.level_reached == 0


def test_generation_result_adapter_falls_back_to_legacy_compile_error_type() -> None:
    row = _make_generation_result(
        grammar_active=True,
        masked_token_rate=0.25,
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg="signature mismatch",
    )

    result = eval_result_from_generation_result(row)

    assert result.failure_code == "SignatureError"


def test_generation_result_adapter_accepts_explicit_condition() -> None:
    row = _make_generation_result(grammar_active=False, masked_token_rate=None)

    result = eval_result_from_generation_result(row, condition="G")

    assert result.condition == "G"


def test_generation_result_adapter_rejects_cluster1_reserved_condition() -> None:
    row = _make_generation_result(grammar_active=False, masked_token_rate=None)

    with pytest.raises(ValueError, match="not allowed"):
        eval_result_from_generation_result(row, condition="C")


def test_cluster1_adapter_leaves_level_2_to_4_fields_none() -> None:
    row = _make_generation_result(grammar_active=True, masked_token_rate=0.25)

    result = eval_result_from_generation_result(row)

    for field_name in LEVEL_2_TO_4_FIELDS:
        assert getattr(result, field_name) is None


def test_compile_success_preserves_strict_all_dtype_value() -> None:
    row = _make_generation_result(
        compile_success=False,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": False},
    )

    result = eval_result_from_generation_result(row)

    assert result.compile_success is False


def test_eval_result_schema_contains_expected_fields() -> None:
    field_names = {field.name for field in fields(EvalResult)}

    assert "compile_success" in field_names
    assert "functional_success" in field_names
    assert "speedup_vs_compile" in field_names
    assert "repair_traces" in field_names


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
        "level_reached": 1,
        "parse_success": None,
        "parse_error": None,
        "has_triton_decorator": None,
        "signature_valid": None,
        "compile_success": True,
        "compile_error": None,
        "failure_code": None,
    }
    defaults.update(overrides)
    return EvalResult(**defaults)


def _make_fully_populated_eval_result(**overrides) -> EvalResult:
    defaults = _make_eval_result(
        ast_hash="ast-hash",
        gpu_model="NVIDIA A100-SXM4-80GB",
        gpu_clock_mhz=1410,
        tokens_input=123,
        tokens_output=456,
        generation_time_s=1.25,
        level_reached=4,
        parse_success=True,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        compile_time_s=0.5,
        functional_success=True,
        max_abs_diff=1e-6,
        max_rel_diff=1e-6,
        num_test_shapes=5,
        shapes_passed=5,
        dtype_results={"fp32": {"passed": True, "max_abs_diff": 1e-6}},
        safe_success=True,
        sanitizer_errors=[],
        sanitizer_tool="memcheck",
        kernel_time_ms=0.1,
        kernel_time_iqr_ms=0.01,
        eager_time_ms=0.2,
        compile_time_ms=0.15,
        speedup_vs_eager=2.0,
        speedup_vs_compile=1.5,
        repair_iteration=1,
        repair_budget=5,
        repair_converged=True,
        repair_traces=[
            RepairTrace(
                iteration=0,
                source="bad source",
                level_reached=1,
                feedback_type="compile_error",
                feedback_content="compile failed",
                tokens_generated=100,
                converged=False,
            ),
            RepairTrace(
                iteration=1,
                source="good source",
                level_reached=2,
                feedback_type="correctness_error",
                feedback_content="fixed",
                tokens_generated=120,
                converged=True,
            ),
        ],
    ).to_dict()
    defaults.update(overrides)
    return EvalResult.from_dict(defaults)


def _make_generation_result(**overrides) -> GenerationResult:
    defaults = {
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": False,
        "grammar_variant": None,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": True,
        "compile_results_by_dtype": {"fp32": True, "fp16": True, "bf16": True},
        "compile_error_type": None,
        "compile_error_msg": None,
        "masked_token_rate": None,
        "unique_solution_hash": "unique-hash",
        "n_shapes_tested": 5,
        "generation_seed": 0,
        "temperature": 0.2,
        "run_id": "rid",
        "timestamp_utc": "2026-05-05T00:00:00+00:00",
    }
    defaults.update(overrides)
    if defaults["grammar_active"] is True and defaults["grammar_variant"] is None:
        defaults["grammar_variant"] = "template_upper_bound"
    return GenerationResult(**defaults)
