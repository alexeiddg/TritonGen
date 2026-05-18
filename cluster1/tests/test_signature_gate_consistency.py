"""Phase 2 tests for C1 signature-gate alignment with shared Level 0."""

from __future__ import annotations

import inspect
import types

import pytest

from cluster1.validation import compile_check
from cluster1.validation.compile_check import CompileSpec, check_compiles


def _make_spec(
    launcher_name: str = "relu",
    params: tuple[str, ...] = ("x",),
) -> CompileSpec:
    signature = inspect.Signature(
        [
            inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for name in params
        ]
    )

    def build_args(shape, dtype):
        return ["value"], {}

    return CompileSpec(
        launcher_name=launcher_name,
        reference_signature=signature,
        build_args=build_args,
    )


def _level0_valid_source() -> str:
    return """\
@triton.jit
def relu_kernel(x):
    return x

def relu(x):
    return x
"""


def test_level0_parse_runs_before_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_check_parse(source: str):
        calls.append("parse")
        return False, "SyntaxError: broken"

    def fail_load(source: str):
        raise AssertionError("runtime import must not run after parse failure")

    monkeypatch.setattr(compile_check, "check_parse", fake_check_parse)
    monkeypatch.setattr(compile_check, "load_generated_module", fail_load)

    result = check_compiles("def broken(:\n", _make_spec(), "fp32", [(32,)])

    assert calls == ["parse"]
    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_PARSE"
    assert result.n_shapes_tested == 0


def test_level0_signature_runs_before_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_check_parse(source: str):
        calls.append("parse")
        return True, None

    def fake_check_signature(source: str, kernel_spec):
        calls.append("signature")
        return False, "Signature mismatch: launcher 'relu' not found"

    def fail_load(source: str):
        raise AssertionError("runtime import must not run after signature failure")

    monkeypatch.setattr(compile_check, "check_parse", fake_check_parse)
    monkeypatch.setattr(compile_check, "check_signature", fake_check_signature)
    monkeypatch.setattr(compile_check, "load_generated_module", fail_load)

    result = check_compiles(_level0_valid_source(), _make_spec(), "fp32", [(32,)])

    assert calls == ["parse", "signature"]
    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_BAD_SIGNATURE"
    assert result.n_shapes_tested == 0


def test_ast_parse_failure_records_canonical_parse_code() -> None:
    result = check_compiles("def broken(:\n", _make_spec(), "fp32", [(32,)])

    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_PARSE"
    assert result.error_msg is not None
    assert result.error_msg.startswith("SyntaxError:")
    assert result.n_shapes_tested == 0


def test_missing_launcher_records_bad_signature_code() -> None:
    source = """\
@triton.jit
def relu_kernel(x):
    return x

def not_relu(x):
    return x
"""

    result = check_compiles(source, _make_spec(), "fp32", [(32,)])

    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_BAD_SIGNATURE"
    assert result.error_msg is not None
    assert "launcher 'relu' not found" in result.error_msg


def test_wrong_launcher_params_records_bad_signature_code() -> None:
    source = """\
@triton.jit
def relu_kernel(x):
    return x

def relu(y):
    return y
"""

    result = check_compiles(source, _make_spec(), "fp32", [(32,)])

    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_BAD_SIGNATURE"
    assert result.error_msg is not None
    assert "Signature mismatch" in result.error_msg


def test_valid_source_reaches_runtime_import_and_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def relu(x):
        calls.append(("launch", x))
        return x

    module = types.ModuleType("generated")
    module.relu = relu  # type: ignore[attr-defined]

    def fake_load(source: str):
        calls.append("load")
        return module

    def fake_cleanup(loaded_module):
        calls.append(("cleanup", loaded_module.__name__))

    monkeypatch.setattr(compile_check, "load_generated_module", fake_load)
    monkeypatch.setattr(compile_check, "cleanup_generated_module", fake_cleanup)

    result = check_compiles(_level0_valid_source(), _make_spec(), "fp32", [(32,)])

    assert result.success is True
    assert result.error_type is None
    assert result.failure_code is None
    assert result.n_shapes_tested == 1
    assert calls == ["load", ("launch", "value"), ("cleanup", "generated")]


def test_runtime_signature_guard_still_runs_after_level0(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = types.ModuleType("generated")

    def relu(y):
        return y

    module.relu = relu  # type: ignore[attr-defined]
    monkeypatch.setattr(compile_check, "load_generated_module", lambda source: module)
    monkeypatch.setattr(compile_check, "cleanup_generated_module", lambda module: None)

    result = check_compiles(_level0_valid_source(), _make_spec(), "fp32", [(32,)])

    assert result.success is False
    assert result.error_type == "SignatureError"
    assert result.failure_code == "F0_BAD_SIGNATURE"
    assert result.error_msg is not None
    assert "signature mismatch" in result.error_msg


def test_runtime_import_failure_after_level0_records_runtime_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(source: str):
        raise ValueError("SignatureError: import error in generated source: boom")

    monkeypatch.setattr(compile_check, "load_generated_module", fail_load)

    result = check_compiles(_level0_valid_source(), _make_spec(), "fp32", [(32,)])

    assert result.success is False
    assert result.error_type == "RuntimeError"
    assert result.failure_code == "F1_RUNTIME"
