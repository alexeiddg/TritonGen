"""Tests for shared Level 0 parse and signature checks."""

from __future__ import annotations

import inspect
import os
from types import SimpleNamespace

import pytest

from shared.eval.levels.level0_parse import check_parse, check_signature


WELL_FORMED_KERNEL = """\
import triton
import triton.language as tl

@triton.jit
def relu(x):
    return x
"""


def test_check_parse_accepts_well_formed_triton_kernel_source() -> None:
    assert check_parse(WELL_FORMED_KERNEL) == (True, None)


def test_check_parse_rejects_syntax_error() -> None:
    ok, error = check_parse("def broken(:\n    pass\n")

    assert ok is False
    assert error is not None
    assert error.startswith("SyntaxError:")


def test_check_signature_accepts_expected_params() -> None:
    spec = SimpleNamespace(expected_params=["x"])

    assert check_signature(WELL_FORMED_KERNEL, spec) == (True, None)


def test_check_signature_rejects_syntax_error() -> None:
    ok, error = check_signature(
        "def broken(:\n    pass\n",
        SimpleNamespace(expected_params=["x"]),
    )

    assert ok is False
    assert error is not None
    assert error.startswith("SyntaxError:")


def test_check_signature_missing_triton_jit_decorator_returns_level0_error() -> None:
    source = """\
def relu(x):
    return x
"""
    spec = SimpleNamespace(expected_params=["x"])

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error is not None
    assert "F0_NO_DECORATOR" in error
    assert "No @triton.jit" in error


def test_check_signature_wrong_param_names_returns_mismatch() -> None:
    source = """\
@triton.jit
def relu(y):
    return y
"""
    spec = SimpleNamespace(expected_params=["x"])

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error is not None
    assert "Signature mismatch" in error


def test_check_signature_uses_launcher_not_jit_helper_when_launcher_name_exists() -> None:
    source = """\
import torch
import triton
import triton.language as tl

@triton.jit
def relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    return

def relu(x):
    return x
"""
    spec = SimpleNamespace(
        launcher_name="relu",
        expected_params=["x"],
    )

    assert check_signature(source, spec) == (True, None)


def test_check_signature_rejects_wrong_launcher_even_if_jit_helper_exists() -> None:
    source = """\
import triton
import triton.language as tl

@triton.jit
def relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    return

def relu(y):
    return y
"""
    spec = SimpleNamespace(
        launcher_name="relu",
        expected_params=["x"],
    )

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error is not None
    assert "Signature mismatch" in error
    assert "got ['y']" in error


def test_check_signature_validates_last_duplicate_launcher_definition() -> None:
    source = """\
import triton

@triton.jit
def relu_kernel(x_ptr):
    return x_ptr

def relu(x):
    return x

def relu(y):
    return y
"""
    spec = SimpleNamespace(
        launcher_name="relu",
        expected_params=["x"],
    )

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error is not None
    assert "Signature mismatch" in error
    assert "got ['y']" in error


def test_check_signature_rejects_nested_launcher() -> None:
    source = """\
import triton

@triton.jit
def relu_kernel(x_ptr):
    return x_ptr

def outer():
    def relu(x):
        return x
    return relu
"""
    spec = SimpleNamespace(
        launcher_name="relu",
        expected_params=["x"],
    )

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error == "Signature mismatch: launcher 'relu' not found"


@pytest.mark.parametrize(
    "launcher_definition",
    [
        "def relu(*x):",
        "def relu(**x):",
        "def relu(*, x):",
        "def relu(x, /):",
    ],
)
def test_check_signature_rejects_non_regular_launcher_args(
    launcher_definition: str,
) -> None:
    source = f"""\
import triton

@triton.jit
def relu_kernel(x_ptr):
    return x_ptr

{launcher_definition}
    return x
"""
    spec = SimpleNamespace(
        launcher_name="relu",
        expected_params=["x"],
    )

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error == "Signature mismatch: unsupported launcher argument kind"


def test_check_signature_detects_call_form_triton_jit_decorator() -> None:
    source = """\
@triton.jit(debug=True)
def relu(x):
    return x
"""
    spec = SimpleNamespace(expected_params=["x"])

    assert check_signature(source, spec) == (True, None)


def test_check_signature_detects_call_form_imported_jit_decorator() -> None:
    source = """\
@jit()
def relu(x):
    return x
"""
    spec = SimpleNamespace(expected_params=["x"])

    assert check_signature(source, spec) == (True, None)


def test_check_signature_detects_imported_jit_decorator_name() -> None:
    source = """\
@jit
def relu(x):
    return x
"""
    spec = SimpleNamespace(expected_params=["x"])

    assert check_signature(source, spec) == (True, None)


def test_check_signature_derives_expected_params_from_compile_spec_signature() -> None:
    signature = inspect.Signature(
        [
            inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]
    )
    source = """\
@triton.jit
def matmul(a, b):
    return a
"""
    spec = SimpleNamespace(compile_spec=SimpleNamespace(signature=signature))

    assert check_signature(source, spec) == (True, None)


def test_check_signature_does_not_execute_import_time_code(monkeypatch: pytest.MonkeyPatch) -> None:
    marker = "TRITONGEN_LEVEL0_SHOULD_NOT_EXECUTE"
    monkeypatch.delenv(marker, raising=False)
    source = f"""\
import os
os.environ[{marker!r}] = "executed"

@triton.jit
def relu(x):
    return x
"""
    spec = SimpleNamespace(expected_params=["x"])

    assert check_signature(source, spec) == (True, None)
    assert marker not in os.environ


def test_check_signature_works_with_real_cluster1_specs_without_cuda() -> None:
    kernels = pytest.importorskip("cluster1.data.kernels")

    cases = [
        (
            kernels.RELU_SPEC,
            """\
@triton.jit
def relu(x):
    return x
""",
        ),
        (
            kernels.SOFTMAX_SPEC,
            """\
@triton.jit
def softmax(x):
    return x
""",
        ),
        (
            kernels.GEMM_SPEC,
            """\
@triton.jit
def matmul(a, b):
    return a
""",
        ),
    ]

    for spec, source in cases:
        assert check_signature(source, spec) == (True, None)


def test_check_signature_accepts_real_cluster1_helper_plus_launcher_shape_without_cuda() -> None:
    kernels = pytest.importorskip("cluster1.data.kernels")
    source = """\
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

    assert check_signature(source, kernels.RELU_SPEC) == (True, None)
