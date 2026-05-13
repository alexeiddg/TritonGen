"""Content-hash helpers for Cluster 2 reproducibility manifests.

This module is intentionally cheap to import. It hashes source files and Python
function source without importing Modal, Torch, Triton, or generation stacks.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

EVAL_PIPELINE_SOURCE_PATHS: tuple[str, ...] = (
    "shared/eval/schema.py",
    "shared/eval/constants.py",
    "shared/eval/tolerances.py",
    "shared/eval/failure_taxonomy.py",
    "shared/eval/diversity.py",
    "shared/eval/adapter_cluster1.py",
    "shared/eval/run_config.py",
    "shared/eval/pipeline.py",
    "shared/eval/levels/level0_parse.py",
    "shared/eval/levels/level1_compile.py",
    "shared/eval/content_hashes.py",
    "shared/eval/correctness_shapes.py",
)

C2_GENERATION_SOURCE_PATHS: tuple[str, ...] = (
    "cluster2/modal/schemas.py",
    "cluster2/modal/generation.py",
    "cluster2/generation/modal_generate_c2.py",
    "cluster2/feedback/prompts.py",
    "cluster2/feedback/trace.py",
    "cluster2/feedback/repair_loop.py",
)

C2_MODAL_SOURCE_PATHS: tuple[str, ...] = (
    "cluster2/modal/schemas.py",
    "cluster2/modal/generation.py",
    "cluster2/modal/correctness.py",
    "cluster2/modal/correctness_runner.py",
)


def file_sha256(path: str | Path) -> str:
    """Return SHA256 over raw file bytes."""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module_content_sha256(module_path: str) -> str:
    """Return SHA256 for a Python module file or direct filesystem path."""

    path = _resolve_module_or_file(module_path)
    return file_sha256(path)


def function_source_sha256(fn: Callable[..., Any]) -> str:
    """Return SHA256 over ``inspect.getsource(fn)``."""

    source = inspect.getsource(fn)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def collect_eval_pipeline_hashes() -> dict[str, str]:
    """Return source hashes for the current shared eval pipeline files."""

    return _collect_existing_repo_path_hashes(EVAL_PIPELINE_SOURCE_PATHS)


def collect_c2_generation_hashes(condition: str) -> dict[str, str]:
    """Return source hashes for C2 generation paths for generated conditions."""

    if condition not in {"C", "G+C"}:
        raise ValueError("C2 generation hashes are defined only for C and G+C")
    return _collect_existing_repo_path_hashes(C2_GENERATION_SOURCE_PATHS)


def collect_c2_modal_hashes() -> dict[str, str]:
    """Return source hashes for isolated C2 Modal scaffold files."""

    return _collect_existing_repo_path_hashes(C2_MODAL_SOURCE_PATHS)


def collect_cluster1_frozen_generation_hashes(
    condition: str,
    manifest_path: str,
) -> dict[str, str]:
    """Return frozen Cluster 1 replay artifact hashes for ``condition``."""

    if condition not in {"none", "G"}:
        raise ValueError("frozen Cluster 1 generation hashes are defined for none and G")

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for artifact in manifest.get("artifacts", []):
        if artifact.get("condition") != condition:
            continue
        artifact_id = artifact["artifact_id"]
        hashes[f"{artifact_id}:artifact"] = artifact["sha256"]
        sidecar = artifact.get("metadata_sidecar")
        if isinstance(sidecar, dict) and sidecar.get("sha256"):
            hashes[f"{artifact_id}:metadata_sidecar"] = sidecar["sha256"]
    return hashes


def collect_external_pins() -> dict[str, str]:
    """Return lightweight interpreter and package-version pins."""

    pins = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    for package in ("modal", "torch", "triton", "transformers", "xgrammar"):
        pins[f"package:{package}"] = _package_version(package)
    return pins


def collect_modal_source_manifest(paths: list[str]) -> dict[str, str]:
    """Return source-content hashes for Modal-related source paths."""

    return _collect_existing_repo_path_hashes(tuple(paths))


def _collect_existing_repo_path_hashes(paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel_path in paths:
        path = REPO_ROOT / rel_path
        if path.is_file():
            hashes[rel_path] = file_sha256(path)
    return hashes


def _resolve_module_or_file(module_path: str) -> Path:
    candidate = Path(module_path)
    if candidate.is_file():
        return candidate

    repo_candidate = REPO_ROOT / module_path
    if repo_candidate.is_file():
        return repo_candidate

    spec = importlib.util.find_spec(module_path)
    if spec is None or spec.origin is None or spec.origin == "built-in":
        raise FileNotFoundError(f"module or file not found: {module_path}")

    path = Path(spec.origin)
    if not path.is_file():
        raise FileNotFoundError(f"module has no source file: {module_path}")
    return path


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"
