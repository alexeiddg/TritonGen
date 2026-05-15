"""Phase 14 import-discipline tests for Cluster 2 and shared eval modules."""

from __future__ import annotations

import ast
import importlib.util
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

HEAVY_RUNTIME_MODULES = (
    "torch",
    "triton",
    "transformers",
    "xgrammar",
    "autoawq",
    "huggingface_hub",
)
MODAL_RUNTIME_MODULES = ("modal",)
FORBIDDEN_SHARED_MODAL_MODULES = (
    "shared.modal_harness.generation",
    "shared.modal_harness.schemas",
    "shared.modal_harness.smoke",
)

C2_NO_MODAL_IMPORT_TARGETS = (
    "cluster2.constants",
    "cluster2.feedback.prompts",
    "cluster2.feedback.trace",
    "cluster2.feedback.repair_loop",
    "cluster2.results.dataclass",
    "cluster2.results.logger",
    "cluster2.replay.manifest",
    "cluster2.replay.cluster1_controls",
    "cluster2.experiments.run_cluster2_modal",
    "cluster2.modal.schemas",
    "cluster2.modal.correctness_runner",
)
C2_MODAL_DECLARATION_IMPORT_TARGETS = (
    "cluster2.modal.generation",
    "cluster2.modal.correctness",
    "cluster2.generation.modal_generate_c2",
    "cluster2.validation.modal_correctness_check",
)

SHARED_EVAL_CLUSTER2_IMPORT_ALLOWLIST = {
    "shared/eval/aggregation.py": {
        "cluster2.constants",
        "cluster2.results.dataclass",
    },
    "shared/eval/correctness_shapes.py": {"cluster2.constants"},
    "shared/eval/metrics/coverage.py": {"cluster2.results.dataclass"},
    "shared/eval/metrics/equal_attempts.py": {
        "cluster2.constants",
        "cluster2.results.dataclass",
    },
    "shared/eval/metrics/repair.py": {
        "cluster2.constants",
        "cluster2.results.dataclass",
    },
    "shared/eval/run_config.py": {"cluster2.constants"},
    "shared/eval/pipeline.py": {"cluster2.constants"},
    "shared/eval/reference_runner.py": {"cluster2.constants"},
}


@pytest.mark.parametrize("target", C2_NO_MODAL_IMPORT_TARGETS)
def test_cluster2_non_modal_modules_import_without_modal_or_heavy_runtime(
    target: str,
) -> None:
    leaked = _modules_after_import(target, HEAVY_RUNTIME_MODULES + MODAL_RUNTIME_MODULES)

    assert leaked == []


@pytest.mark.parametrize("target", C2_MODAL_DECLARATION_IMPORT_TARGETS)
def test_cluster2_modal_declaration_modules_import_without_heavy_runtime(
    target: str,
) -> None:
    leaked = _modules_after_import(target, HEAVY_RUNTIME_MODULES)

    assert leaked == []


@pytest.mark.parametrize("target", C2_MODAL_DECLARATION_IMPORT_TARGETS)
def test_cluster2_modal_imports_do_not_load_cluster1_shared_modal_surfaces(
    target: str,
) -> None:
    leaked = _modules_after_import(target, FORBIDDEN_SHARED_MODAL_MODULES)

    assert leaked == []


def test_shared_eval_modules_import_without_modal_or_heavy_runtime() -> None:
    leaks: dict[str, list[str]] = {}
    for target in sorted(_shared_eval_module_names()):
        leaked = _modules_after_import(
            target,
            HEAVY_RUNTIME_MODULES + MODAL_RUNTIME_MODULES,
        )
        if leaked:
            leaks[target] = leaked

    assert leaks == {}


def test_no_top_level_model_loading_or_torch_cuda_calls() -> None:
    violations: list[str] = []
    for path in _source_paths_for_static_import_checks():
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _module_level_calls(tree):
            chain = _call_chain(call.func)
            if not chain:
                continue
            rendered = ".".join(chain)
            if chain[-1] in {"from_pretrained", "snapshot_download"}:
                violations.append(f"{rel_path}:{call.lineno}:{rendered}")
            elif chain[:2] == ["torch", "cuda"] or chain[-1] == "cuda":
                violations.append(f"{rel_path}:{call.lineno}:{rendered}")
            elif rendered.startswith("modal.") and chain[-1] == "run":
                violations.append(f"{rel_path}:{call.lineno}:{rendered}")
            elif chain[-1] == "remote":
                violations.append(f"{rel_path}:{call.lineno}:{rendered}")

    assert violations == []


def test_shared_eval_only_imports_cluster2_constants_to_avoid_cycles() -> None:
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "shared/eval").rglob("*.py")):
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        allowed = SHARED_EVAL_CLUSTER2_IMPORT_ALLOWLIST.get(rel_path, set())
        for imported in _imported_modules(path):
            if imported == "cluster2" or imported.startswith("cluster2."):
                if imported not in allowed:
                    violations.append(f"{rel_path}:{imported}")

    assert violations == []


def test_cluster2_constants_stays_below_shared_eval_import_boundary() -> None:
    imports = _imported_modules(REPO_ROOT / "cluster2/constants.py")

    assert not any(
        imported == "shared.eval" or imported.startswith("shared.eval.")
        for imported in imports
    )


def test_cluster2_modal_has_no_forbidden_shared_modal_imports() -> None:
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "cluster2/modal").glob("*.py")):
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for imported in _imported_modules(path, include_from_aliases=True):
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_SHARED_MODAL_MODULES
            ):
                violations.append(f"{rel_path}:{imported}")

    assert violations == []


def test_cluster2_replay_does_not_import_generation_modules() -> None:
    forbidden_prefixes = (
        "cluster2.generation",
        "cluster2.modal.generation",
        "cluster1.generation",
        "shared.modal_harness.generation",
    )
    violations: list[str] = []
    for path in sorted((REPO_ROOT / "cluster2/replay").glob("*.py")):
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for imported in _imported_modules(path, include_from_aliases=True):
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for forbidden in forbidden_prefixes
            ):
                violations.append(f"{rel_path}:{imported}")

    assert violations == []


def test_forbidden_import_scans_expand_import_from_aliases(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from shared.modal_harness import generation\n"
        "from cluster2.modal import generation as modal_generation\n",
        encoding="utf-8",
    )

    imports = _imported_modules(probe, include_from_aliases=True)
    top_level_imports = _top_level_imported_modules(probe, include_from_aliases=True)

    assert "shared.modal_harness.generation" in imports
    assert "cluster2.modal.generation" in imports
    assert "shared.modal_harness.generation" in top_level_imports
    assert "cluster2.modal.generation" in top_level_imports


def test_forbidden_import_scans_resolve_relative_import_from_aliases(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "cluster2" / "replay" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text(
        "from ..modal import generation\n"
        "from . import cluster1_controls\n",
        encoding="utf-8",
    )

    imports = _imported_modules(probe, include_from_aliases=True)
    top_level_imports = _top_level_imported_modules(probe, include_from_aliases=True)

    assert "cluster2.modal" in imports
    assert "cluster2.modal.generation" in imports
    assert "cluster2.replay.cluster1_controls" in imports
    assert "cluster2.modal" in top_level_imports
    assert "cluster2.modal.generation" in top_level_imports
    assert "cluster2.replay.cluster1_controls" in top_level_imports


def _modules_after_import(target: str, module_names: tuple[str, ...]) -> list[str]:
    code = (
        "import importlib\n"
        "import sys\n"
        f"importlib.import_module({target!r})\n"
        "loaded = [name for name in "
        f"{module_names!r} if name in sys.modules]\n"
        "print('\\n'.join(loaded))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"probe failed for {target}: rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    return [line for line in proc.stdout.splitlines() if line]


def _shared_eval_module_names() -> tuple[str, ...]:
    package_dir = REPO_ROOT / "shared/eval"
    names = ["shared.eval"]
    for module in pkgutil.walk_packages([str(package_dir)], prefix="shared.eval."):
        if module.ispkg:
            names.append(module.name)
            continue
        spec = importlib.util.find_spec(module.name)
        if spec is not None:
            names.append(module.name)
    return tuple(names)


def _source_paths_for_static_import_checks() -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in (REPO_ROOT / "cluster2", REPO_ROOT / "shared/eval"):
        for path in root.rglob("*.py"):
            rel_parts = path.relative_to(REPO_ROOT).parts
            if "tests" in rel_parts or "__pycache__" in rel_parts:
                continue
            paths.append(path)
    return tuple(sorted(paths))


def _module_level_calls(tree: ast.Module) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        calls.extend(child for child in ast.walk(node) if isinstance(child, ast.Call))
    return calls


def _call_chain(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_call_chain(node.value), node.attr]
    return []


def _imported_modules(path: Path, *, include_from_aliases: bool = False) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None:
                continue
            modules.add(module)
            if include_from_aliases:
                modules.update(
                    f"{module}.{alias.name}" for alias in node.names if alias.name != "*"
                )
    return modules


def _top_level_imported_modules(
    path: Path,
    *,
    include_from_aliases: bool = False,
) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None:
                continue
            modules.add(module)
            if include_from_aliases:
                modules.update(
                    f"{module}.{alias.name}" for alias in node.names if alias.name != "*"
                )
    return modules


def _resolve_import_from_module(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    relative_name = f"{'.' * node.level}{node.module or ''}"
    return importlib.util.resolve_name(relative_name, _package_name_for_path(path))


def _package_name_for_path(path: Path) -> str:
    parts = _import_path_parts(path)
    if path.name == "__init__.py":
        return ".".join(parts)
    return ".".join(parts[:-1])


def _import_path_parts(path: Path) -> tuple[str, ...]:
    if path.name == "__init__.py":
        path = path.parent
    else:
        path = path.with_suffix("")
    try:
        rel_parts = path.relative_to(REPO_ROOT).parts
    except ValueError:
        rel_parts = path.parts
        for package_root in ("cluster2", "shared", "cluster1"):
            if package_root in rel_parts:
                rel_parts = rel_parts[rel_parts.index(package_root) :]
                break
    return tuple(part for part in rel_parts if part)
