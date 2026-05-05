"""Tests for the Phase 4 compile validation gate.

CPU-only tests (Tasks 4.7, signature taxonomy) always run.
CUDA-dependent tests (Task 4.8, actual JIT launch) are skipped without a GPU.
No torch.allclose, no timing, no repair logic — Cluster 1 boundary.
"""

from __future__ import annotations

import inspect
import pytest

from cluster1.validation.compile_check import (
    CompileResult,
    CompileSpec,
    check_compiles,
    check_compiles_all_dtypes,
    load_generated_module,
    validate_signature,
)


# ---------------------------------------------------------------------------
# Helpers shared by multiple tests
# ---------------------------------------------------------------------------

def _make_spec(launcher_name: str, sig: inspect.Signature) -> CompileSpec:
    def build_args(shape, dtype):
        return [], {}

    return CompileSpec(
        launcher_name=launcher_name,
        reference_signature=sig,
        build_args=build_args,
    )


def _sig(*param_names: str) -> inspect.Signature:
    params = [
        inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in param_names
    ]
    return inspect.Signature(params)


_VALID_SOURCE = """\
import torch
import triton
import triton.language as tl

@triton.jit
def relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

_WRONG_SIG_SOURCE = """\
def wrong_launcher(a, b, c):
    pass
"""

_SYNTAX_ERROR_SOURCE = """\
def broken(:
    pass
"""

_MISSING_LAUNCHER_SOURCE = """\
def some_other_fn(x):
    pass
"""

# Torch-free source for CPU unit tests of load_generated_module/validate_signature.
_SIMPLE_SOURCE = """\
def relu(x):
    return x
"""


# ---------------------------------------------------------------------------
# Task 4.1 — CompileResult
# ---------------------------------------------------------------------------

def test_compile_result_truncates_error_msg() -> None:
    long_msg = "x" * 600
    result = CompileResult(
        success=False,
        error_type="RuntimeError",
        error_msg=long_msg,
        dtype="fp32",
        n_shapes_tested=0,
    )
    assert result.error_msg is not None
    assert len(result.error_msg) == 500


def test_compile_result_none_error_msg() -> None:
    result = CompileResult(
        success=True,
        error_type=None,
        error_msg=None,
        dtype="fp32",
        n_shapes_tested=3,
    )
    assert result.success is True
    assert result.error_type is None
    assert result.error_msg is None


# ---------------------------------------------------------------------------
# Task 4.3 — load_generated_module
# ---------------------------------------------------------------------------

def test_load_generated_module_imports_valid_source() -> None:
    module = load_generated_module(_SIMPLE_SOURCE)
    assert hasattr(module, "relu")


def test_load_generated_module_raises_on_syntax_error() -> None:
    with pytest.raises(ValueError, match="SignatureError"):
        load_generated_module(_SYNTAX_ERROR_SOURCE)


# ---------------------------------------------------------------------------
# Task 4.4 — validate_signature
# ---------------------------------------------------------------------------

def test_validate_signature_matches() -> None:
    module = load_generated_module(_SIMPLE_SOURCE)
    spec = _make_spec("relu", _sig("x"))
    assert validate_signature(module, spec) is None


def test_validate_signature_wrong_params() -> None:
    module = load_generated_module(_SIMPLE_SOURCE)
    spec = _make_spec("relu", _sig("x", "y"))
    error = validate_signature(module, spec)
    assert error is not None
    assert "mismatch" in error


def test_validate_signature_missing_launcher() -> None:
    module = load_generated_module(_MISSING_LAUNCHER_SOURCE)
    spec = _make_spec("relu", _sig("x"))
    error = validate_signature(module, spec)
    assert error is not None
    assert "not found" in error


# ---------------------------------------------------------------------------
# Task 4.7 — test_signature_error_precedes_compile (V4)
# ---------------------------------------------------------------------------

def test_signature_error_precedes_compile() -> None:
    """SignatureError is returned before any Triton launch attempt."""
    launch_attempted = []

    def build_args_spy(shape, dtype):
        launch_attempted.append(shape)
        return [], {}

    spec = CompileSpec(
        launcher_name="relu",
        reference_signature=_sig("x", "y", "z"),  # wrong — relu only takes x
        build_args=build_args_spy,
    )

    try:
        import torch
        dtype = torch.float32
    except ImportError:
        pytest.skip("torch not installed")

    result = check_compiles(_VALID_SOURCE, spec, dtype, [(32,)])

    assert result.error_type == "SignatureError"
    assert result.success is False
    assert not launch_attempted, "build_args must not be called before signature check"


def test_signature_error_on_syntax_bad_source() -> None:
    spec = _make_spec("relu", _sig("x"))

    try:
        import torch
        dtype = torch.float32
    except ImportError:
        pytest.skip("torch not installed")

    result = check_compiles(_SYNTAX_ERROR_SOURCE, spec, dtype, [(32,)])
    assert result.error_type == "SignatureError"
    assert result.success is False
    assert result.n_shapes_tested == 0


def test_signature_error_on_missing_launcher() -> None:
    spec = _make_spec("relu", _sig("x"))

    try:
        import torch
        dtype = torch.float32
    except ImportError:
        pytest.skip("torch not installed")

    result = check_compiles(_MISSING_LAUNCHER_SOURCE, spec, dtype, [(32,)])
    assert result.error_type == "SignatureError"
    assert result.success is False
    assert result.n_shapes_tested == 0


# ---------------------------------------------------------------------------
# Task 4.8 — test_error_taxonomy (V2, V5) — CUDA required
# ---------------------------------------------------------------------------

def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


@pytest.mark.skipif(not _cuda_available(), reason="CUDA not available")
def test_valid_relu_compiles_on_cuda() -> None:
    import torch

    def build_relu_args(shape, dtype):
        x = torch.randn(*shape, dtype=dtype, device="cuda")
        return [x], {}

    spec = CompileSpec(
        launcher_name="relu",
        reference_signature=_sig("x"),
        build_args=build_relu_args,
    )

    result = check_compiles(_VALID_SOURCE, spec, torch.float32, [(1024,), (4096,)])
    assert result.success is True
    assert result.error_type is None
    assert result.n_shapes_tested == 2


@pytest.mark.skipif(not _cuda_available(), reason="CUDA not available")
def test_compilation_error_and_runtime_error_are_distinct() -> None:
    """CompilationError and RuntimeError must be caught and labelled separately."""
    import torch

    # A source that imports but fails at Triton JIT compile time (bad IL).
    bad_compile_source = """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = tl.arange(0, BLOCK_SIZE)
    # deliberately invalid: tl.load with wrong type to trigger CompilationError
    x = tl.load(x_ptr + offsets)
    result = tl.dot(x, x)  # dot on 1D is invalid at compile time
    tl.store(x_ptr + offsets, result)

def bad_kernel_launcher(x):
    BLOCK_SIZE = 64
    grid = (1,)
    bad_kernel[grid](x, BLOCK_SIZE)
    return x
"""

    def build_args(shape, dtype):
        x = torch.randn(*shape, dtype=dtype, device="cuda")
        return [x], {}

    spec = CompileSpec(
        launcher_name="bad_kernel_launcher",
        reference_signature=_sig("x"),
        build_args=build_args,
    )

    result = check_compiles(bad_compile_source, spec, torch.float32, [(64,)])
    # Must be one of the two allowed error types — not a broad Exception catch.
    assert result.error_type in {"CompilationError", "RuntimeError"}
    assert result.success is False
    assert result.error_msg is not None


@pytest.mark.skipif(not _cuda_available(), reason="CUDA not available")
def test_check_compiles_all_dtypes_returns_three_results() -> None:
    import torch

    def build_relu_args(shape, dtype):
        x = torch.randn(*shape, dtype=dtype, device="cuda")
        return [x], {}

    spec = CompileSpec(
        launcher_name="relu",
        reference_signature=_sig("x"),
        build_args=build_relu_args,
    )

    shapes_by_dtype = {
        "fp32": [(512,)],
        "fp16": [(512,)],
        "bf16": [(512,)],
    }

    results = check_compiles_all_dtypes(_VALID_SOURCE, spec, shapes_by_dtype)
    assert len(results) == 3
    dtypes_returned = {r.dtype for r in results}
    assert dtypes_returned == {"fp32", "fp16", "bf16"}
    # No boundary violations — no timing, no numerical comparison.
    for r in results:
        assert not hasattr(r, "elapsed_s")
        assert not hasattr(r, "compile_time_s")


def test_check_compiles_all_dtypes_signature_error_without_cuda() -> None:
    """Without CUDA the signature check still fires correctly for all dtypes."""
    try:
        import torch
    except ImportError:
        pytest.skip("torch not installed")

    # Wrong launcher name triggers SignatureError before any CUDA launch.
    spec = _make_spec("nonexistent_fn", _sig("x"))
    shapes_by_dtype = {"fp32": [(32,)], "fp16": [(32,)], "bf16": [(32,)]}

    results = check_compiles_all_dtypes(_VALID_SOURCE, spec, shapes_by_dtype)
    assert len(results) == 3
    for r in results:
        assert r.error_type == "SignatureError"
        assert r.success is False
