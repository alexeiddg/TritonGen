"""Tests for shared Level 1 compile adapter."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from shared.eval.levels.level1_compile import (
    Level1CompileResult,
    check_compile_level1,
)


@dataclass(frozen=True)
class FakeCompileResult:
    success: bool
    error_type: str | None
    error_msg: str | None
    dtype: str
    n_shapes_tested: int


def test_module_import_does_not_require_torch_triton_or_cuda() -> None:
    code = (
        "import sys\n"
        "from shared.eval.levels import Level1CompileResult, check_compile_level1\n"
        "loaded = [name for name in ('torch', 'triton') if name in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_check_compile_level1_delegates_to_cluster1_compile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cluster1.validation import compile_check as compile_module

    compile_spec = object()
    shapes_by_dtype = {"fp32": [(32,)], "fp16": [(32,)], "bf16": [(32,)]}
    calls = []

    def fake_check_compiles_all_dtypes(source, spec, shapes):  # type: ignore[no-untyped-def]
        calls.append((source, spec, shapes))
        return [
            FakeCompileResult(True, None, None, "fp32", 1),
            FakeCompileResult(True, None, None, "fp16", 1),
            FakeCompileResult(True, None, None, "bf16", 1),
        ]

    monkeypatch.setattr(
        compile_module,
        "check_compiles_all_dtypes",
        fake_check_compiles_all_dtypes,
    )
    spec = SimpleNamespace(compile_spec=compile_spec, shapes_by_dtype=shapes_by_dtype)

    result = check_compile_level1("source", spec)

    assert calls == [("source", compile_spec, shapes_by_dtype)]
    assert isinstance(result, Level1CompileResult)


def test_all_dtype_successes_return_compile_success_true(monkeypatch: pytest.MonkeyPatch) -> None:
    from cluster1.validation import compile_check as compile_module

    def fake_check_compiles_all_dtypes(source, spec, shapes):  # type: ignore[no-untyped-def]
        return [
            FakeCompileResult(True, None, None, "fp32", 2),
            FakeCompileResult(True, None, None, "fp16", 3),
            FakeCompileResult(True, None, None, "bf16", 4),
        ]

    monkeypatch.setattr(
        compile_module,
        "check_compiles_all_dtypes",
        fake_check_compiles_all_dtypes,
    )
    spec = SimpleNamespace(compile_spec=object(), shapes_by_dtype={})

    result = check_compile_level1("source", spec)

    assert result.compile_success is True
    assert result.compile_error is None
    assert result.compile_error_type is None
    assert result.compile_results_by_dtype == {
        "fp32": True,
        "fp16": True,
        "bf16": True,
    }
    assert result.n_shapes_tested == 9


def test_one_dtype_failure_returns_false_and_surfaces_first_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cluster1.validation import compile_check as compile_module

    def fake_check_compiles_all_dtypes(source, spec, shapes):  # type: ignore[no-untyped-def]
        return [
            FakeCompileResult(True, None, None, "fp32", 2),
            FakeCompileResult(
                False,
                "CompilationError",
                "fp16 compile failed",
                "fp16",
                1,
            ),
            FakeCompileResult(False, "RuntimeError", "bf16 runtime failed", "bf16", 0),
        ]

    monkeypatch.setattr(
        compile_module,
        "check_compiles_all_dtypes",
        fake_check_compiles_all_dtypes,
    )
    spec = SimpleNamespace(compile_spec=object(), shapes_by_dtype={})

    result = check_compile_level1("source", spec)

    assert result.compile_success is False
    assert result.compile_error_type == "CompilationError"
    assert result.compile_error == "fp16 compile failed"
    assert result.compile_results_by_dtype == {
        "fp32": True,
        "fp16": False,
        "bf16": False,
    }
    assert result.n_shapes_tested == 3


def test_delegate_exception_returns_structured_unknown_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cluster1.validation import compile_check as compile_module

    def fake_check_compiles_all_dtypes(source, spec, shapes):  # type: ignore[no-untyped-def]
        raise RuntimeError("delegate boom")

    monkeypatch.setattr(
        compile_module,
        "check_compiles_all_dtypes",
        fake_check_compiles_all_dtypes,
    )
    spec = SimpleNamespace(
        compile_spec=object(),
        shapes_by_dtype={"fp32": [(32,)], "fp16": [(32,)], "bf16": [(32,)]},
    )

    result = check_compile_level1("source", spec)

    assert result.compile_success is False
    assert result.compile_error_type == "UnknownError"
    assert result.compile_error is not None
    assert "check_compiles_all_dtypes raised: delegate boom" in result.compile_error
    assert result.compile_results_by_dtype == {
        "fp32": False,
        "fp16": False,
        "bf16": False,
    }
    assert result.n_shapes_tested == 0


def test_cluster1_runners_still_use_existing_compile_paths() -> None:
    local_runner = Path("cluster1/experiments/run_cluster1.py").read_text(
        encoding="utf-8"
    )
    modal_runner = Path("cluster1/experiments/run_cluster1_modal.py").read_text(
        encoding="utf-8"
    )
    combined = f"{local_runner}\n{modal_runner}"

    assert "check_compile_level1" not in combined
    assert "shared.eval.levels.level1_compile" not in combined
    assert (
        "from cluster1.validation.compile_check import "
        "CompileResult, check_compiles_all_dtypes"
    ) in local_runner
    assert "check_compiles_all_dtypes(" in local_runner
    assert (
        "from cluster1.validation.modal_compile_check import check_compiles_modal"
        in modal_runner
    )
