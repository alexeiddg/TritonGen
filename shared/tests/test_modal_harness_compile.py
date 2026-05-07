"""Local tests for the compile-side harness plumbing.

These exercise ``_run_remote_compile`` directly (the underlying
implementation of ``remote_compile_only``) so subprocess result-file
handling can be verified without Modal.

The compile child is replaced by patching ``subprocess.run`` so each test
can simulate stdout noise, missing result files, or malformed JSON without
shipping a real subprocess.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

from shared.modal_harness import compile as compile_module
from shared.modal_harness.compile import _run_remote_compile

REQUEST = {
    "factor_cell": "none",
    "kernel_class": "elementwise",
    "kernel_name": "relu",
    "source": "def relu(x): return x",
    "run_id": "test-rid",
    "timeout_s": 30,
}


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _patched_run(
    monkeypatch: pytest.MonkeyPatch,
    behavior: Callable[[Path, Path], _FakeCompletedProcess],
) -> None:
    """Patch ``subprocess.run`` to invoke ``behavior(request_path, result_path)``."""

    def fake_run(args, capture_output, text, timeout):  # type: ignore[no-untyped-def]
        request_path = Path(args[-2])
        result_path = Path(args[-1])
        # Sanity: the parent must always pass two real paths to the runner.
        assert request_path.exists()
        return behavior(request_path, result_path)

    monkeypatch.setattr(compile_module.subprocess, "run", fake_run)


def test_run_remote_compile_ignores_stray_stdout(monkeypatch) -> None:
    """A noisy child must not break result parsing."""

    def behavior(request_path: Path, result_path: Path) -> _FakeCompletedProcess:
        result_path.write_text(
            json.dumps(
                {
                    "compile_success": True,
                    "compile_results_by_dtype": {
                        "fp32": True,
                        "fp16": True,
                        "bf16": True,
                    },
                    "compile_error_type": None,
                    "compile_error_msg": None,
                    "n_shapes_tested": 9,
                }
            )
        )
        return _FakeCompletedProcess(
            returncode=0,
            stdout="triton: autotuning kernel\nWARNING: not a JSON document\n",
            stderr="torch: cudnn benchmark = True\n",
        )

    _patched_run(monkeypatch, behavior)
    result = _run_remote_compile(REQUEST)

    assert result["compile_success"] is True
    assert result["compile_results_by_dtype"] == {
        "fp32": True,
        "fp16": True,
        "bf16": True,
    }
    assert result["n_shapes_tested"] == 9
    # Success path drops stdout (it carried noise, not signal).
    assert result["stdout"] == ""
    # stderr is preserved as a debugging breadcrumb.
    assert "cudnn benchmark" in result["stderr"]
    assert result["run_id"] == "test-rid"
    # factor_cell is stitched in from the canonical request, not the child.
    assert result["factor_cell"] == "none"


def test_run_remote_compile_missing_result_file_is_structured_error(monkeypatch) -> None:
    """Child that exits without writing a result file → UnknownError."""

    def behavior(request_path: Path, result_path: Path) -> _FakeCompletedProcess:
        # Intentionally do NOT write result_path.
        return _FakeCompletedProcess(
            returncode=0,
            stdout="garbled output\n",
            stderr="oops\n",
        )

    _patched_run(monkeypatch, behavior)
    result = _run_remote_compile(REQUEST)

    assert result["compile_success"] is False
    assert result["compile_error_type"] == "UnknownError"
    assert "did not produce a result file" in (result["compile_error_msg"] or "")
    # Stdout/stderr preserved on failure for debugging.
    assert "garbled output" in result["stdout"]
    assert "oops" in result["stderr"]


def test_run_remote_compile_invalid_json_is_structured_error(monkeypatch) -> None:
    """Child that writes invalid JSON to result_path → UnknownError."""

    def behavior(request_path: Path, result_path: Path) -> _FakeCompletedProcess:
        result_path.write_text("not json at all }}", encoding="utf-8")
        return _FakeCompletedProcess(returncode=0, stdout="", stderr="")

    _patched_run(monkeypatch, behavior)
    result = _run_remote_compile(REQUEST)

    assert result["compile_success"] is False
    assert result["compile_error_type"] == "UnknownError"
    assert "not valid JSON" in (result["compile_error_msg"] or "")


def test_run_remote_compile_timeout_is_structured(monkeypatch) -> None:
    """Subprocess timeout becomes a TimeoutError result row, not an exception."""

    def behavior(request_path: Path, result_path: Path) -> _FakeCompletedProcess:
        raise subprocess.TimeoutExpired(cmd="compile_runner", timeout=30)

    _patched_run(monkeypatch, behavior)
    result = _run_remote_compile(REQUEST)

    assert result["compile_success"] is False
    assert result["compile_error_type"] == "TimeoutError"
    # Even on timeout, the dtype dictionary is populated so analysis code
    # never has to handle a missing key.
    assert result["compile_results_by_dtype"] == {
        "fp32": False,
        "fp16": False,
        "bf16": False,
    }


def test_compile_runner_module_writes_result_file(tmp_path) -> None:
    """End-to-end: the real compile_runner emits a JSON result file and
    never relies on stdout for correctness."""
    request = {
        "factor_cell": "none",
        "kernel_class": "nonexistent-class",  # forces SignatureError early
        "kernel_name": "relu",
        "source": "def relu(x): return x",
        "run_id": "rid",
        "timeout_s": 30,
    }
    request_path = tmp_path / "req.json"
    result_path = tmp_path / "res.json"
    request_path.write_text(json.dumps(request))

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "shared.modal_harness.compile_runner",
            str(request_path),
            str(result_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["compile_success"] is False
    assert payload["compile_error_type"] == "SignatureError"
    assert payload["n_shapes_tested"] == 0
