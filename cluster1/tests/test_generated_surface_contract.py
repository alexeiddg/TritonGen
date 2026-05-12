"""Cluster 1 generated-code surface contract tests."""

from __future__ import annotations

import ast
import types
from pathlib import Path

import pytest

from cluster1.data.kernels import get_kernel_spec
from cluster1.data.kernels.spec import torch as spec_torch
from cluster1.grammar.acceptance_fixtures import BAD_KERNELS
from cluster1.grammar.triton_kernel_validator import (
    TASK_AGNOSTIC_GBNF_PATH,
    accepts_source,
)
from cluster1.validation.compile_check import (
    cleanup_generated_module,
    load_generated_module,
    validate_signature,
)
from shared.eval.levels.level0_parse import check_parse, check_signature


GOLDEN_FIXTURES = {
    "elementwise": "generated_relu.py.txt",
    "reduction": "generated_softmax.py.txt",
    "matmul": "generated_matmul.py.txt",
}

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _read_fixture(kernel_class: str) -> str:
    return (GOLDEN_DIR / GOLDEN_FIXTURES[kernel_class]).read_text(encoding="utf-8")


@pytest.fixture
def fake_gpu_modules(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.Tensor = spec_torch.Tensor
    fake_torch.empty_like = lambda x: x
    fake_torch.empty = lambda *args, **kwargs: object()

    fake_triton = types.ModuleType("triton")
    fake_triton.__path__ = []
    fake_triton.jit = lambda fn: fn
    fake_triton.cdiv = lambda x, y: (x + y - 1) // y
    fake_triton.Config = lambda values, **kwargs: (values, kwargs)

    fake_tl = types.ModuleType("triton.language")
    fake_tl.constexpr = object()
    fake_triton.language = fake_tl

    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)
    monkeypatch.setitem(__import__("sys").modules, "triton", fake_triton)
    monkeypatch.setitem(__import__("sys").modules, "triton.language", fake_tl)


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_ast_and_level0_parse(kernel_class: str) -> None:
    source = _read_fixture(kernel_class)

    ast.parse(source)
    assert check_parse(source) == (True, None)


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_level0_signature(kernel_class: str) -> None:
    source = _read_fixture(kernel_class)
    spec = get_kernel_spec(kernel_class)

    assert check_signature(source, spec) == (True, None)


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_compile_checker_signature_exact(
    kernel_class: str,
    fake_gpu_modules,
) -> None:
    source = _read_fixture(kernel_class)
    spec = get_kernel_spec(kernel_class)
    module = load_generated_module(source)
    try:
        assert validate_signature(module, spec.compile_spec) is None
    finally:
        cleanup_generated_module(module)


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_offline_grammar(kernel_class: str) -> None:
    assert accepts_source(_read_fixture(kernel_class))


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_task_agnostic_offline_grammar(kernel_class: str) -> None:
    assert accepts_source(_read_fixture(kernel_class), TASK_AGNOSTIC_GBNF_PATH)


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_required_imports(kernel_class: str) -> None:
    tree = ast.parse(_read_fixture(kernel_class))
    imports = [
        [(alias.name, alias.asname) for alias in node.names]
        for node in tree.body[:3]
        if isinstance(node, ast.Import)
    ]

    assert imports == [
        [("torch", None)],
        [("triton", None)],
        [("triton.language", "tl")],
    ]


@pytest.mark.parametrize(
    "kernel_class,launcher_name",
    [("elementwise", "relu"), ("reduction", "softmax"), ("matmul", "matmul")],
)
def test_golden_fixture_required_functions(
    kernel_class: str,
    launcher_name: str,
) -> None:
    tree = ast.parse(_read_fixture(kernel_class))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]

    assert [node.name for node in functions] == [
        f"_{launcher_name}_kernel",
        launcher_name,
    ]
    assert _has_triton_jit(functions[0])
    assert _signature_text(functions[1]) == {
        "relu": "def relu(x: torch.Tensor) -> torch.Tensor",
        "softmax": "def softmax(x: torch.Tensor) -> torch.Tensor",
        "matmul": "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor",
    }[launcher_name]


@pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
def test_golden_fixture_launcher_body_shape(kernel_class: str) -> None:
    source = _read_fixture(kernel_class)
    tree = ast.parse(source)
    spec = get_kernel_spec(kernel_class)
    launcher = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == spec.launcher_name
    )
    helper_name = f"_{spec.launcher_name}_kernel"

    assert _allocates_output(launcher)
    assert _assigns_name(launcher, "grid")
    assert _has_bracket_launch(launcher, helper_name)
    assert any(isinstance(stmt, ast.Return) and stmt.value is not None for stmt in launcher.body)


@pytest.mark.parametrize(
    "bad_name",
    [
        "markdown_fence",
        "missing_public_launcher",
        "wrong_launcher_signature",
        "missing_return_annotation",
        "missing_imports",
        "model_class_only",
        "undefined_name_in_wrapper_prelude",
        "relu_helper_missing_args",
        "relu_helper_missing_constexpr",
        "relu_helper_wrong_output_name",
        "softmax_helper_missing_args",
        "softmax_helper_missing_constexpr",
        "matmul_helper_missing_args",
        "matmul_helper_wrong_ptr_name",
        "missing_output_allocation",
        "launch_uses_input_not_output",
        "relu_missing_launch_tail",
        "relu_wrong_launch_tail",
        "softmax_missing_launch_tail",
        "matmul_missing_launch_tail",
        "return_input_after_allocation",
        "unused_output_allocation",
        "reassigned_output_after_allocation",
        "undefined_name_in_output_allocation",
        "empty_like_non_tensor_input",
        "torch_empty_tensor_shape",
        "torch_empty_missing_device_dtype",
        "torch_empty_like_invalid_empty_source",
        "grid_reassigned_after_assignment",
        "undefined_name_in_grid_tuple",
        "empty_grid_tuple",
        "tensor_name_in_grid_tuple",
        "dtype_attribute_in_grid_tuple",
        "grid_float_division",
        "grid_matmul_operator",
        "inline_undefined_grid_tuple",
        "relu_tl_max_scalar_axis",
        "relu_tl_max_x_axis",
        "relu_tl_sum_x_axis",
        "relu_tl_dot_x_x",
        "relu_tl_atomic_add",
        "relu_tl_exp_x",
        "relu_tl_log_x",
        "relu_tl_sqrt_x",
        "relu_bare_x_compute",
        "relu_x_plus_one_compute",
        "relu_x_times_x_compute",
        "relu_scalar_zero_compute",
        "relu_boolean_compute",
        "relu_arbitrary_tl_call",
        "softmax_duplicate_mask_keyword",
        "softmax_uses_undefined_n_rows_in_kernel",
        "softmax_python_min_subscript",
        "softmax_pointer_slice_assignment",
        "softmax_negative_tensor_index_mask",
        "softmax_missing_store",
        "matmul_program_id_tuple_subscript",
        "matmul_missing_store",
    ],
)
def test_bad_surface_fixtures_rejected_by_grammar(bad_name: str) -> None:
    assert not accepts_source(BAD_KERNELS[bad_name])


def test_bad_markdown_fixture_rejected_by_level0_parse() -> None:
    ok, error = check_parse(BAD_KERNELS["markdown_fence"])

    assert ok is False
    assert error is not None


@pytest.mark.parametrize("bad_name", ["missing_public_launcher", "wrong_launcher_signature"])
def test_bad_launcher_fixtures_rejected_by_level0_signature(bad_name: str) -> None:
    ok, error = check_signature(BAD_KERNELS[bad_name], get_kernel_spec("elementwise"))

    assert ok is False
    assert error is not None


def test_model_class_only_rejected_for_current_cluster1_surface() -> None:
    source = BAD_KERNELS["model_class_only"]
    ok, error = check_signature(source, get_kernel_spec("elementwise"))

    assert not accepts_source(source)
    assert ok is False
    assert error is not None


def test_compile_checker_signature_equality_requires_annotations(fake_gpu_modules) -> None:
    spec = get_kernel_spec("elementwise")
    module = types.ModuleType("generated")

    exec(
        compile(
            "def relu(x: torch.Tensor) -> torch.Tensor:\n    return x\n",
            "<generated>",
            "exec",
            dont_inherit=True,
        ),
        {"torch": spec_torch},
        module.__dict__,
    )
    assert validate_signature(module, spec.compile_spec) is None

    exec(
        compile(
            "def relu(x):\n    return x\n",
            "<generated>",
            "exec",
            dont_inherit=True,
        ),
        {},
        module.__dict__,
    )
    error = validate_signature(module, spec.compile_spec)
    assert error is not None
    assert "signature mismatch" in error


def _has_triton_jit(function: ast.FunctionDef) -> bool:
    return any(ast.unparse(decorator) == "triton.jit" for decorator in function.decorator_list)


def _signature_text(function: ast.FunctionDef) -> str:
    args = ", ".join(
        f"{arg.arg}: {ast.unparse(arg.annotation)}" for arg in function.args.args
    )
    returns = ast.unparse(function.returns) if function.returns is not None else "None"
    return f"def {function.name}({args}) -> {returns}"


def _allocates_output(function: ast.FunctionDef) -> bool:
    for stmt in function.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not isinstance(stmt.value, ast.Call):
            continue
        if ast.unparse(stmt.value.func) in {"torch.empty_like", "torch.empty"}:
            return True
    return False


def _assigns_name(function: ast.FunctionDef, name: str) -> bool:
    for stmt in function.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in stmt.targets):
            return True
    return False


def _has_bracket_launch(function: ast.FunctionDef, helper_name: str) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Subscript) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == helper_name:
                return True
    return False
