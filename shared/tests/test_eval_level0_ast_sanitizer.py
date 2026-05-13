"""Tests for the Phase 3 Level 0 AST sanitizer."""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

import pytest

from shared.eval.levels.level0_ast_sanitizer import (
    F0_SURFACE_VIOLATION,
    check_level0_ast_sanitizer,
    scan_generated_code_surface,
)

_GOLDEN_FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "cluster1"
    / "tests"
    / "fixtures"
    / "golden"
)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "generated_relu.py.txt",
        "generated_softmax.py.txt",
        "generated_matmul.py.txt",
    ],
)
def test_accepts_canonical_cluster1_launcher_golden_fixture(fixture_name: str) -> None:
    source = (_GOLDEN_FIXTURE_DIR / fixture_name).read_text()

    result = check_level0_ast_sanitizer(source)

    assert result.safe_success is True, result.sanitizer_errors
    assert result.failure_code is None
    assert "torch.Tensor" in source


def test_accepts_torch_empty_allocation_and_triton_launch() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            out = torch.empty_like(x)
            n_elements = x.numel()
            BLOCK_SIZE = 256
            grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
            _kernel[grid](x, out, n_elements, BLOCK_SIZE)
            return out
            """
        )
    )

    assert result.safe_success is True
    assert result.failure_code is None
    assert result.sanitizer_errors is None


def test_accepts_input_as_tensor_parameter_name() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            out = torch.empty_like(input)
            n_elements = input.numel()
            grid = (triton.cdiv(n_elements, 256),)
            _kernel[grid](input, out, n_elements, 256)
            return out
            """,
            launcher_param="input",
        )
    )

    assert result.safe_success is True
    assert result.sanitizer_errors is None


def test_accepts_input_as_tensor_alias_name() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            x = input
            out = torch.empty_like(x)
            n_elements = x.numel()
            grid = (triton.cdiv(n_elements, 256),)
            _kernel[grid](x, out, n_elements, 256)
            return out
            """,
            launcher_param="input",
        )
    )

    assert result.safe_success is True
    assert result.sanitizer_errors is None


def test_accepts_tensor_metadata_surfaces() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            out = torch.empty(x.shape, device=x.device, dtype=x.dtype)
            n_elements = x.numel()
            stride0 = x.stride(0)
            size0 = x.size(0)
            dim0 = x.shape[0]
            BLOCK_SIZE = 128
            grid = (triton.cdiv(n_elements + size0 + stride0 + dim0, BLOCK_SIZE),)
            _kernel[grid](x, out, n_elements, BLOCK_SIZE)
            return out
            """
        )
    )

    assert result.safe_success is True


def test_accepts_triton_cdiv_grid_metadata() -> None:
    result = scan_generated_code_surface(
        _module(
            """
            out = torch.zeros_like(x)
            n_elements = x.numel()
            blocks = triton.cdiv(n_elements, 1024)
            grid = (blocks,)
            _kernel[grid](x, out, n_elements, 1024)
            return out
            """
        )
    )

    assert result.safe_success is True


@pytest.mark.parametrize(
    "allocator,expression",
    [
        ("empty", "torch.empty(x.shape, device=x.device, dtype=x.dtype)"),
        ("empty_like", "torch.empty_like(x)"),
        ("zeros", "torch.zeros(x.shape, device=x.device, dtype=x.dtype)"),
        ("zeros_like", "torch.zeros_like(x)"),
        ("ones", "torch.ones(x.shape, device=x.device, dtype=x.dtype)"),
        ("ones_like", "torch.ones_like(x)"),
    ],
)
def test_torch_allocation_allowlist(allocator: str, expression: str) -> None:
    result = check_level0_ast_sanitizer(
        _module(
            f"""
            out = {expression}
            n_elements = x.numel()
            grid = (triton.cdiv(n_elements, 256),)
            _kernel[grid](x, out, n_elements, 256)
            return out
            """
        )
    )

    assert allocator in expression
    assert result.safe_success is True


@pytest.mark.parametrize(
    "torch_call",
    [
        "torch.relu(x)",
        "torch.softmax(x, dim=-1)",
        "torch.matmul(x, x)",
        "torch.mm(x, x)",
        "torch.bmm(x, x)",
        "torch.einsum('ij,jk->ik', x, x)",
        "torch.dot(x, x)",
    ],
)
def test_rejects_torch_compute_calls(torch_call: str) -> None:
    source = _module(
        f"""
        out = {torch_call}
        return out
        """
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, torch_call.split("(", maxsplit=1)[0])


def test_rejects_torch_nn_functional_alias() -> None:
    source = _module(
        """
        out = F.softmax(x, dim=-1)
        return out
        """,
        extra_imports="import torch.nn.functional as F\n",
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "torch.nn.functional")
    assert _has_reason(result, "torch.nn.functional")


@pytest.mark.parametrize(
    "method_call",
    [
        "x.relu()",
        "x.softmax(dim=-1)",
        "x.matmul(x)",
        "x.mm(x)",
        "x.bmm(x)",
        "x.exp()",
        "x.sum()",
        "x.max()",
        "x.mean()",
        "x.var()",
        "x.std()",
    ],
)
def test_rejects_tensor_compute_methods(method_call: str) -> None:
    source = _module(
        f"""
        out = {method_call}
        return out
        """
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, method_call.split("(", maxsplit=1)[0])


def test_rejects_tensor_matmul_operator() -> None:
    source = _module(
        """
        out = x @ x
        return out
        """
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "x @ x")


def test_rejects_direct_torch_import_bypass() -> None:
    source = _module(
        """
        out = relu(x)
        return out
        """,
        extra_imports="from torch import relu\n",
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "from torch import relu")


def test_rejects_torch_assignment_alias_bypass() -> None:
    source = _module(
        """
        T = torch
        out = T.relu(x)
        return out
        """
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "T.relu")


def test_rejects_dynamic_getattr_bypass() -> None:
    source = _module(
        """
        out = getattr(torch, "relu")(x)
        return out
        """
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "getattr")


@pytest.mark.parametrize(
    "decorator",
    [
        "@torch.compile",
        "@torch.compile()",
        "@eval",
        "@custom_decorator",
    ],
)
def test_rejects_non_jit_function_decorators(decorator: str) -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        launcher_decorator=decorator,
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, decorator)
    assert _has_reason(result, "decorator")


@pytest.mark.parametrize(
    "kernel_decorator",
    [
        "@triton.jit(eval)",
        "@triton.jit(compile)",
        "@triton.jit(debug=eval)",
    ],
)
def test_rejects_triton_jit_decorator_arguments(kernel_decorator: str) -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        kernel_decorator=kernel_decorator,
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, kernel_decorator)
    assert _has_reason(result, "decorator arguments")


def test_accepts_call_form_triton_jit_without_arguments() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            out = torch.empty_like(x)
            n_elements = x.numel()
            grid = (triton.cdiv(n_elements, 256),)
            _kernel[grid](x, out, n_elements, 256)
            return out
            """,
            kernel_decorator="@triton.jit()",
        )
    )

    assert result.safe_success is True


def test_rejects_dangerous_builtin_jit_function_default() -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        kernel_signature=(
            "x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, fn=eval"
        ),
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "fn=eval")


@pytest.mark.parametrize(
    "kernel_signature,return_annotation,needle",
    [
        (
            "x_ptr: eval, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr",
            "",
            "x_ptr: eval",
        ),
        (
            "x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr",
            "eval",
            "-> eval",
        ),
    ],
)
def test_rejects_dangerous_builtin_jit_function_annotations(
    kernel_signature: str,
    return_annotation: str,
    needle: str,
) -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        kernel_signature=kernel_signature,
        kernel_return_annotation=return_annotation,
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


@pytest.mark.parametrize(
    "kernel_signature,needle",
    [
        (
            "x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, "
            "y=torch.relu(out_ptr)",
            "torch.relu(out_ptr)",
        ),
        (
            "x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr, "
            "y=torch.softmax(out_ptr, dim=0)",
            "torch.softmax(out_ptr, dim=0)",
        ),
        (
            "x_ptr: torch.relu(out_ptr), out_ptr, n_elements, "
            "BLOCK_SIZE: tl.constexpr",
            "torch.relu(out_ptr)",
        ),
    ],
)
def test_rejects_torch_compute_call_in_jit_signature_load_time_expression(
    kernel_signature: str,
    needle: str,
) -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        kernel_signature=kernel_signature,
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


def test_rejects_torch_compute_call_in_jit_return_annotation() -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """,
        kernel_return_annotation="torch.relu(out_ptr)",
    )

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, "torch.relu(out_ptr)")


def test_accepts_safe_triton_jit_function_annotations() -> None:
    result = check_level0_ast_sanitizer(
        _module(
            """
            out = torch.empty_like(x)
            n_elements = x.numel()
            grid = (triton.cdiv(n_elements, 256),)
            _kernel[grid](x, out, n_elements, 256)
            return out
            """,
            kernel_signature=(
                "x_ptr: tl.constexpr, out_ptr, n_elements, "
                "BLOCK_SIZE: tl.constexpr"
            ),
        )
    )

    assert result.safe_success is True
    assert result.sanitizer_errors is None


@pytest.mark.parametrize(
    "body,needle",
    [
        ("model = Model()\nout = model(x)\nreturn out", "Model()"),
        ("out = reference_model(x)\nreturn out", "reference_model"),
    ],
)
def test_rejects_model_and_reference_calls(body: str, needle: str) -> None:
    source = _module(body)

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


@pytest.mark.parametrize(
    "body,needle",
    [
        ("out = eval('x')\nreturn out", "eval"),
        ("exec('out = x')\nreturn x", "exec"),
        ("code = compile('x', '<x>', 'eval')\nreturn x", "compile"),
        ("import os\nreturn x", "import os"),
    ],
)
def test_rejects_eval_exec_compile_import(body: str, needle: str) -> None:
    source = _module(body)

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


def test_parse_failure_uses_parse_failure_code_in_errors() -> None:
    result = check_level0_ast_sanitizer("def broken(:\n    pass\n")

    assert result.safe_success is False
    assert result.failure_code == "F0_PARSE"
    assert result.sanitizer_errors is not None
    assert result.sanitizer_errors[0].startswith("F0_PARSE:")


@pytest.mark.parametrize(
    "body,needle",
    [
        ("data = open('/tmp/x').read()\nreturn x", "open"),
        ("out = os.system('true')\nreturn x", "os.system"),
        ("out = subprocess.run(['true'])\nreturn x", "subprocess.run"),
        ("out = socket.socket()\nreturn x", "socket.socket"),
        ("out = requests.get('https://example.com')\nreturn x", "requests.get"),
    ],
)
def test_rejects_file_network_process_system_surfaces(body: str, needle: str) -> None:
    source = _module(body)

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


@pytest.mark.parametrize(
    "body,needle",
    [
        ("speedup = 1.0\nreturn x", "speedup"),
        ("profile_name = 'kernel profile'\nreturn x", "profile"),
        ("timing = 'timing data'\nreturn x", "timing"),
    ],
)
def test_rejects_timing_profiling_speedup_surfaces(body: str, needle: str) -> None:
    source = _module(body)

    result = check_level0_ast_sanitizer(source)

    _assert_rejected_on_line(result, source, needle)


def test_fixture_runtime_stays_under_50_ms() -> None:
    source = _module(
        """
        out = torch.empty_like(x)
        n_elements = x.numel()
        grid = (triton.cdiv(n_elements, 256),)
        _kernel[grid](x, out, n_elements, 256)
        return out
        """
    )

    start = time.perf_counter()
    result = check_level0_ast_sanitizer(source)
    elapsed = time.perf_counter() - start

    assert result.safe_success is True
    assert elapsed < 0.05


def _module(
    body: str,
    *,
    extra_imports: str = "",
    launcher_decorator: str = "",
    launcher_param: str = "x",
    kernel_decorator: str = "@triton.jit",
    kernel_signature: str = "x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr",
    kernel_return_annotation: str = "",
) -> str:
    indented_body = textwrap.indent(textwrap.dedent(body).strip(), "    ")
    decorator = f"{launcher_decorator}\n" if launcher_decorator else ""
    return_annotation = (
        f" -> {kernel_return_annotation}" if kernel_return_annotation else ""
    )
    return (
        "import torch\n"
        "import triton\n"
        "import triton.language as tl\n"
        f"{extra_imports}"
        "\n"
        f"{kernel_decorator}\n"
        f"def _kernel({kernel_signature}){return_annotation}:\n"
        "    pass\n"
        "\n"
        f"{decorator}"
        f"def launch({launcher_param}):\n"
        f"{indented_body}\n"
    )


def _assert_rejected_on_line(result, source: str, needle: str) -> None:
    assert result.safe_success is False
    assert result.failure_code == F0_SURFACE_VIOLATION
    expected_line = _line_number(source, needle)
    assert any(violation.line_number == expected_line for violation in result.violations), (
        expected_line,
        result.sanitizer_errors,
    )


def _line_number(source: str, needle: str) -> int:
    for line_number, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return line_number
    raise AssertionError(f"needle {needle!r} not found")


def _has_reason(result, text: str) -> bool:
    return any(text in violation.reason for violation in result.violations)
