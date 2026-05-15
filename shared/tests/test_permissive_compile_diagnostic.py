"""Tests for diagnostic-only permissive Triton compile extraction."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from shared.eval.diagnostics import permissive_compile as diagnostic


JIT_SOURCE = """
import triton
import triton.language as tl

@triton.jit
def arbitrary_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    return
"""


def test_strips_python_fenced_code() -> None:
    source = "prefix\n```python\nx = 1\n```\ntrailing"

    assert diagnostic.strip_markdown_fences(source) == "x = 1"


def test_strips_plain_fenced_code() -> None:
    source = "```\ny = 2\n```"

    assert diagnostic.strip_markdown_fences(source) == "y = 2"


def test_preserves_and_parses_raw_code() -> None:
    source = "z = 3\n"

    stripped = diagnostic.strip_markdown_fences(source)

    assert stripped == source
    assert diagnostic.ast.parse(stripped) is not None


def test_finds_triton_jit_regardless_of_function_name() -> None:
    functions = diagnostic.extract_triton_jit_functions(JIT_SOURCE)

    assert [function.name for function in functions] == ["arbitrary_kernel"]


def test_finds_triton_jit_with_triton_heuristics() -> None:
    source = """
import triton

@triton.heuristics({"BLOCK_SIZE": lambda args: 64})
@triton.jit
def heuristic_name(x_ptr, BLOCK_SIZE):
    return
"""

    functions = diagnostic.extract_triton_jit_functions(source)

    assert [function.name for function in functions] == ["heuristic_name"]


def test_ignores_non_jit_functions() -> None:
    source = """
def helper(x):
    return x
"""

    assert diagnostic.extract_triton_jit_functions(source) == []


def test_handles_multiple_jit_functions_deterministically() -> None:
    source = """
import triton

@triton.jit
def first_kernel(x_ptr):
    return

@triton.jit
def second_kernel(x_ptr):
    return
"""
    selected: list[str] = []

    def fake_runner(
        stripped_source: str,
        function: diagnostic.TritonJitFunction,
    ) -> diagnostic.PermissiveCompileAttempt:
        selected.append(function.name)
        return diagnostic.PermissiveCompileAttempt(compile_success=True)

    row = diagnostic.evaluate_source_permissive_compile(
        source,
        {"compile_success": False},
        compile_runner=fake_runner,
    )

    assert selected == ["first_kernel"]
    assert row["selected_jit_function"] == "first_kernel"
    assert row["permissive_compile_success"] is True
    assert row["strict_compile_success"] is False


def test_does_not_require_canonical_signature() -> None:
    def fake_runner(
        stripped_source: str,
        function: diagnostic.TritonJitFunction,
    ) -> diagnostic.PermissiveCompileAttempt:
        return diagnostic.PermissiveCompileAttempt(compile_success=True)

    row = diagnostic.evaluate_source_permissive_compile(
        JIT_SOURCE,
        {},
        compile_runner=fake_runner,
    )

    assert row["parse_success"] is True
    assert row["selected_jit_function"] == "arbitrary_kernel"
    assert row["permissive_compile_success"] is True


def test_records_parse_failure_separately() -> None:
    row = diagnostic.evaluate_source_permissive_compile(
        "def broken(:\n",
        {},
        compile_runner=lambda source, function: diagnostic.PermissiveCompileAttempt(
            compile_success=True
        ),
    )

    assert row["parse_success"] is False
    assert row["parse_error_type"] == "SyntaxError"
    assert row["failure_type"] == "ParseError"
    assert row["permissive_compile_success"] is False


def test_records_no_jit_found_separately() -> None:
    row = diagnostic.evaluate_source_permissive_compile(
        "def helper(x):\n    return x\n",
        {},
        compile_runner=lambda source, function: diagnostic.PermissiveCompileAttempt(
            compile_success=True
        ),
    )

    assert row["parse_success"] is True
    assert row["no_jit_found"] is True
    assert row["failure_type"] == "NoJitFound"
    assert row["permissive_compile_success"] is False


def test_build_permissive_launch_inputs_infers_pointer_and_constexpr() -> None:
    function = diagnostic.extract_triton_jit_functions(JIT_SOURCE)[0]

    launch_inputs = diagnostic.build_permissive_launch_inputs(function.node)

    assert launch_inputs.parameter_kinds == {
        "x_ptr": "pointer",
        "out_ptr": "pointer",
        "n_elements": "constexpr",
        "BLOCK_SIZE": "constexpr",
    }
    assert isinstance(launch_inputs.args[0], diagnostic.TensorInputSpec)
    assert launch_inputs.kwargs == {"n_elements": 16, "BLOCK_SIZE": 64}


def test_build_permissive_launch_inputs_treats_uppercase_abc_as_pointers() -> None:
    source = """
import triton

@triton.jit
def matmul_kernel(A, B, C, M, N, K, BLOCK_M, BLOCK_N, BLOCK_K):
    return
"""
    function = diagnostic.extract_triton_jit_functions(source)[0]

    launch_inputs = diagnostic.build_permissive_launch_inputs(function.node)

    assert launch_inputs.parameter_kinds == {
        "A": "pointer",
        "B": "pointer",
        "C": "pointer",
        "M": "constexpr",
        "N": "constexpr",
        "K": "constexpr",
        "BLOCK_M": "constexpr",
        "BLOCK_N": "constexpr",
        "BLOCK_K": "constexpr",
    }
    assert all(
        isinstance(arg, diagnostic.TensorInputSpec) for arg in launch_inputs.args
    )
    assert [arg.name for arg in launch_inputs.args] == ["A", "B", "C"]


def test_records_value_error_parse_failure_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_value_error(source: str) -> object:
        raise ValueError("source code string cannot contain null bytes")

    monkeypatch.setattr(diagnostic.ast, "parse", raise_value_error)

    row = diagnostic.evaluate_source_permissive_compile(
        "x = 1\x00\n",
        {},
        compile_runner=lambda source, function: diagnostic.PermissiveCompileAttempt(
            compile_success=True
        ),
    )

    assert row["parse_success"] is False
    assert row["parse_error_type"] == "ValueError"
    assert row["failure_type"] == "ParseError"
    assert row["permissive_compile_success"] is False


def test_does_not_call_strict_signature_validator() -> None:
    attempt_source = inspect.getsource(diagnostic._attempt_permissive_compile)

    assert "validate_signature" not in attempt_source
    assert "check_compiles" not in attempt_source


def test_jsonl_outputs_are_diagnostic_only_without_performance_fields(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    summary_path = tmp_path / "summary.json"
    input_path.write_text(
        json.dumps(
            {
                "source": JIT_SOURCE,
                "run_id": "run-1",
                "compile_success": False,
                "compile_error_type": "SignatureError",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = diagnostic.evaluate_jsonl_permissive_compile(
        input_path,
        output_path,
        summary_path,
        compile_runner=lambda source, function: diagnostic.PermissiveCompileAttempt(
            compile_success=True
        ),
    )
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    summary_from_disk = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["diagnostic_only"] is True
    assert summary_from_disk == summary
    assert rows[0]["diagnostic_only"] is True
    assert rows[0]["diagnostic_name"] == "permissive_compile"
    assert rows[0]["strict_compile_success"] is False
    assert rows[0]["strict_compile_error_type"] == "SignatureError"
    assert rows[0]["permissive_compile_success"] is True
    assert _forbidden_performance_keys(rows[0]) == []
    assert _forbidden_performance_keys(summary) == []


def _forbidden_performance_keys(payload: dict[str, object]) -> list[str]:
    return [
        key
        for key in payload
        if any(fragment in key.lower() for fragment in ("timing", "profiling", "speedup"))
    ]
