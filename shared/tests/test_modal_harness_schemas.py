"""Local unit tests for the shared Modal harness schemas.

These run without Modal — the schemas are pure Pydantic. They lock the
Cluster 1 boundary by asserting that reserved factor cells are rejected at
request construction time.
"""

from __future__ import annotations

import pytest

from shared.modal_harness.errors import map_compile_error_type, truncate_output
from shared.modal_harness.schemas import RemoteCompileRequest, RemoteCompileResult


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
        modal_function_call_id="fc-abc",
        modal_input_id="in-abc",
        metadata={"app_name": "tritongen-gpu-harness"},
    )
    rebuilt = RemoteCompileResult(**result.model_dump())
    assert rebuilt == result


def test_result_has_no_timing_fields() -> None:
    """Cluster 1 boundary: no timing / profiling fields anywhere."""
    forbidden = {
        "elapsed_s",
        "compile_time_s",
        "generation_time_s",
        "latency_ms",
        "speedup",
    }
    fields = set(RemoteCompileResult.model_fields.keys())
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


def test_map_compile_error_type_runtime_error() -> None:
    assert map_compile_error_type(RuntimeError("boom")) == "RuntimeError"


def test_map_compile_error_type_signature_keyword() -> None:
    assert map_compile_error_type(ValueError("SignatureError: bad")) == "SignatureError"


def test_map_compile_error_type_unknown_falls_back() -> None:
    assert map_compile_error_type(ValueError("unrelated")) == "UnknownError"


class _FakeCompilationError(Exception):
    """Stand-in for triton.compiler.errors.CompilationError when Triton is absent."""


def test_map_compile_error_type_compilation_error_by_name() -> None:
    # The mapper checks the type name, so a class named "CompilationError"
    # is enough — Triton does not need to be installed locally.
    class CompilationError(Exception):
        pass

    assert map_compile_error_type(CompilationError("bad IR")) == "CompilationError"
