"""Local unit tests for the shared Modal harness schemas.

These run without Modal — the schemas are pure Pydantic. They lock the
Cluster 1 boundary by asserting that reserved factor cells are rejected at
request construction time.
"""

from __future__ import annotations

import pytest

from shared.modal_harness.errors import truncate_output
from shared.modal_harness.schemas import (
    RemoteCompileRequest,
    RemoteCompileResult,
    RemoteEvalResult,
    RemoteGenerationRequest,
    RemoteGenerationResult,
    dtype_name_to_bytes,
    remote_compile_result_to_cluster1_fields,
)


# ---------------------------------------------------------------------------
# RemoteCompileRequest.factor_cell validator
# ---------------------------------------------------------------------------

def _make_request(**overrides):
    base = dict(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        source="def relu(x): return x",
        run_id="test-run-id",
    )
    base.update(overrides)
    return RemoteCompileRequest(**base)


def test_none_mode_accepted() -> None:
    req = _make_request(factor_cell="none")
    assert req.factor_cell == "none"


def test_g_mode_accepted() -> None:
    req = _make_request(factor_cell="G")
    assert req.factor_cell == "G"


@pytest.mark.parametrize("reserved", ["C", "P", "G+C", "G+P", "C+P", "G+C+P"])
def test_reserved_modes_rejected(reserved: str) -> None:
    with pytest.raises(ValueError, match="only 'none' and 'G' are implemented"):
        _make_request(factor_cell=reserved)


def test_unknown_mode_rejected_by_literal() -> None:
    # Outside the FactorCell Literal: rejected by Pydantic's enum check
    # before our custom validator gets a chance.
    with pytest.raises(Exception):
        _make_request(factor_cell="bogus")


# ---------------------------------------------------------------------------
# RemoteCompileRequest round-trip
# ---------------------------------------------------------------------------

def test_request_round_trip_preserves_fields() -> None:
    req = _make_request(timeout_s=60)
    payload = req.model_dump()
    rebuilt = RemoteCompileRequest(**payload)
    assert rebuilt == req
    assert rebuilt.timeout_s == 60


# ---------------------------------------------------------------------------
# RemoteGenerationRequest / RemoteGenerationResult
# ---------------------------------------------------------------------------

def _make_generation_request(**overrides):
    base = dict(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        prompt="write relu",
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
        run_id="test-run-id",
    )
    base.update(overrides)
    return RemoteGenerationRequest(**base)


def test_generation_request_baseline_mode() -> None:
    req = _make_generation_request()
    assert req.factor_cell == "none"
    assert req.grammar_active is False
    assert req.grammar_variant is None


def test_generation_request_g_mode() -> None:
    req = _make_generation_request(factor_cell="G", grammar_active=True)
    assert req.factor_cell == "G"
    assert req.grammar_active is True
    assert req.grammar_variant == "template_upper_bound"


def test_generation_request_task_agnostic_variant_accepted() -> None:
    req = _make_generation_request(
        factor_cell="G",
        grammar_active=True,
        grammar_variant="task_agnostic",
    )
    assert req.grammar_variant == "task_agnostic"


@pytest.mark.parametrize("reserved", ["C", "P", "G+C", "G+P", "C+P", "G+C+P"])
def test_generation_request_reserved_modes_rejected(reserved: str) -> None:
    with pytest.raises(ValueError, match="only 'none' and 'G' are implemented"):
        _make_generation_request(factor_cell=reserved)


def test_generation_request_factor_cell_matches_grammar_flag() -> None:
    with pytest.raises(ValueError, match="requires grammar_active=False"):
        _make_generation_request(factor_cell="none", grammar_active=True)
    with pytest.raises(ValueError, match="requires grammar_active=True"):
        _make_generation_request(factor_cell="G", grammar_active=False)
    with pytest.raises(ValueError, match="requires grammar_variant=None"):
        _make_generation_request(
            factor_cell="none",
            grammar_active=False,
            grammar_variant="template_upper_bound",
        )


def test_generation_request_invalid_grammar_variant_rejected() -> None:
    with pytest.raises(ValueError):
        _make_generation_request(
            factor_cell="G",
            grammar_active=True,
            grammar_variant="bogus",
        )


def test_generation_result_masked_rate_invariant() -> None:
    baseline = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    assert baseline.masked_token_rate is None

    constrained = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=True,
        grammar_variant="template_upper_bound",
        masked_token_rate=0.25,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    assert constrained.masked_token_rate == 0.25
    assert constrained.grammar_variant == "template_upper_bound"


def test_generation_result_rejects_wrong_masked_rate_shape() -> None:
    with pytest.raises(ValueError, match="must be None"):
        RemoteGenerationResult(
            source="@triton.jit",
            model_id="model",
            grammar_active=False,
            grammar_variant=None,
            masked_token_rate=0.1,
            generation_seed=0,
            temperature=0.2,
            run_id="rid",
        )
    with pytest.raises(ValueError, match="is required"):
        RemoteGenerationResult(
            source="@triton.jit",
            model_id="model",
            grammar_active=True,
            grammar_variant="template_upper_bound",
            masked_token_rate=None,
            generation_seed=0,
            temperature=0.2,
            run_id="rid",
        )


def test_generation_dtype_bytes_for_hardware_masks() -> None:
    assert dtype_name_to_bytes("fp32") == 4
    assert dtype_name_to_bytes("fp16") == 2
    assert dtype_name_to_bytes("bf16") == 2
    with pytest.raises(ValueError, match="unsupported dtype"):
        dtype_name_to_bytes("int8")


# ---------------------------------------------------------------------------
# RemoteCompileResult shape
# ---------------------------------------------------------------------------

def test_result_minimal_construction() -> None:
    result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=15,
        run_id="rid",
    )
    assert result.compile_error_type is None
    assert result.stdout == ""
    assert result.metadata == {}


def test_result_round_trip() -> None:
    result = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="CompilationError",
        compile_error_msg="bad IR",
        n_shapes_tested=0,
        stdout="hello",
        stderr="oops",
        traceback="Traceback ...",
        run_id="rid",
        factor_cell="G",
        modal_function_call_id="fc-abc",
        modal_input_id="in-abc",
        metadata={"app_name": "tritongen-gpu-harness"},
    )
    rebuilt = RemoteCompileResult(**result.model_dump())
    assert rebuilt == result
    assert rebuilt.factor_cell == "G"


def test_result_factor_cell_defaults_to_none() -> None:
    """Older sidecar logs without the field still parse cleanly."""
    result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=3,
        run_id="rid",
    )
    assert result.factor_cell is None


def test_remote_eval_result_round_trip() -> None:
    generation = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    compile_result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=3,
        run_id="rid",
    )
    result = RemoteEvalResult(generation=generation, compile=compile_result)
    rebuilt = RemoteEvalResult(**result.model_dump())
    assert rebuilt == result


def test_remote_compile_result_to_cluster1_fields() -> None:
    result = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": True, "bf16": True},
        compile_error_type="RuntimeError",
        compile_error_msg="x" * 600,
        n_shapes_tested=2,
        run_id="rid",
    )

    fields = remote_compile_result_to_cluster1_fields(result)

    assert fields == {
        "compile_success": False,
        "compile_results_by_dtype": {"fp32": False, "fp16": True, "bf16": True},
        "compile_error_type": "RuntimeError",
        "compile_error_msg": "x" * 500,
        "n_shapes_tested": 2,
    }


def test_result_has_no_timing_fields() -> None:
    """Cluster 1 boundary: no timing / profiling fields anywhere."""
    forbidden = {
        "elapsed_s",
        "compile_time_s",
        "generation_time_s",
        "latency_ms",
        "speedup",
    }
    for model in (RemoteCompileResult, RemoteGenerationResult):
        fields = set(model.model_fields.keys())
        assert forbidden.isdisjoint(fields)


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def test_truncate_output_short_text_unchanged() -> None:
    assert truncate_output("hello") == "hello"


def test_truncate_output_long_text_keeps_head_and_tail() -> None:
    text = "A" * 5000 + "B" * 5000
    out = truncate_output(text, max_chars=4000)
    assert len(out) <= 4000 + 64  # plus the small marker line
    assert out.startswith("A")
    assert out.rstrip().endswith("B")
    assert "truncated" in out


def test_truncate_output_empty_string() -> None:
    assert truncate_output("") == ""
