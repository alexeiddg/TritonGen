from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OBSERVABILITY_MODULES = (
    "shared.observability",
    "shared.observability.schema",
    "shared.observability.logger",
    "shared.observability.paths",
    "shared.observability.redaction",
    "shared.observability.performance_contract",
    "shared.observability.billing_reconciliation",
    "shared.observability.billing_modal_collection",
)
FORBIDDEN_IMPORTS = (
    "anthropic",
    "boto3",
    "google",
    "httpx",
    "mlflow",
    "modal",
    "openai",
    "requests",
    "stripe",
    "torch",
    "transformers",
    "triton",
    "urllib",
    "wandb",
    "xgrammar",
)
MODAL_RUNTIME_PATH = REPO_ROOT / "shared" / "modal_harness" / "runtime.py"
FORBIDDEN_TIMING_CALL_STRINGS = (
    "torch.cuda.Event",
    "triton.testing.do_bench",
    "time.perf_counter",
    "time.time",
    "torch.profiler",
    "nsys",
    "subprocess.*nsys",
    "subprocess.*ncu",
    "nvml",
    "pynvml",
)


def test_observability_imports_do_not_load_remote_or_generation_stacks() -> None:
    for target in OBSERVABILITY_MODULES:
        leaked = _modules_after_import(target)
        assert leaked == [], f"{target} imported forbidden modules: {leaked}"


def test_observability_sources_do_not_reference_forbidden_runtime_imports() -> None:
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "shared" / "observability").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        violations.append(f"{path.name}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    violations.append(f"{path.name}:{node.lineno}:{node.module}")

    assert violations == []


def test_observability_sources_do_not_call_timing_or_profiler_apis() -> None:
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "shared" / "observability").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_TIMING_CALL_STRINGS:
            if needle in source:
                violations.append(f"{path.name}:{needle}")

    assert violations == []


def test_modal_runtime_context_helper_import_is_lazy_and_has_no_spawn() -> None:
    leaked = _modules_after_import("shared.modal_harness.runtime")
    assert "modal" not in leaked

    source = MODAL_RUNTIME_PATH.read_text(encoding="utf-8")
    assert ".spawn(" not in source
    assert ".spawn_map(" not in source


def test_modal_runtime_context_normalizer_requires_consistent_availability() -> None:
    from shared.modal_harness.runtime import normalize_modal_context

    with pytest.raises(ValueError, match="available Modal context"):
        normalize_modal_context({"modal_context_available": True})

    with pytest.raises(ValueError, match="unavailable Modal context"):
        normalize_modal_context(
            {
                "modal_context_available": False,
                "function_call_id": "fc-123",
                "modal_context_source": "runner_config",
            }
        )
    with pytest.raises(ValueError, match="remote flag"):
        normalize_modal_context(
            {"modal_context_available": False, "is_remote": "false"}
        )


def test_modal_runtime_context_normalizer_accepts_supplied_runtime_context() -> None:
    from shared.modal_harness.runtime import normalize_modal_context

    context = normalize_modal_context({"function_call_id": "fc-123"})

    assert context == {
        "function_call_id": "fc-123",
        "modal_context_available": True,
        "is_remote": True,
        "modal_context_source": "runner_config",
    }


def _modules_after_import(target: str) -> list[str]:
    code = (
        "import sys\n"
        f"import {target}  # noqa: F401\n"
        "loaded = [name for name in "
        f"{FORBIDDEN_IMPORTS!r} if name in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"probe failed for {target}: rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    out = proc.stdout.strip()
    return out.split(",") if out else []
