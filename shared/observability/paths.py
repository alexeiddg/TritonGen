"""Path helpers for adjacent observability sidecars."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ObservabilityPaths:
    result_path: Path
    event_path: Path
    summary_path: Path
    hash_path: Path


def default_observability_event_path(result_path: str | Path) -> Path:
    """Return ``<result stem>.observability.jsonl`` next to a result JSONL."""

    path = Path(result_path)
    if path.suffix == ".jsonl":
        return path.with_name(f"{path.stem}.observability.jsonl")
    return path.with_name(f"{path.name}.observability.jsonl")


def default_observability_summary_path(result_path: str | Path) -> Path:
    """Return ``<result stem>.observability.summary.json`` next to a result."""

    path = Path(result_path)
    if path.suffix == ".jsonl":
        return path.with_name(f"{path.stem}.observability.summary.json")
    return path.with_name(f"{path.name}.observability.summary.json")


def default_observability_hash_path(event_path: str | Path) -> Path:
    """Return the hash sidecar path for an observability event JSONL."""

    path = Path(event_path)
    return path.with_name(f"{path.name}.hashes.json")


def default_result_content_hash_path(result_path: str | Path) -> Path:
    path = Path(result_path)
    return path.with_name(f"{path.name}.hashes.json")


def default_result_metadata_path(result_path: str | Path) -> Path:
    path = Path(result_path)
    return path.with_name(f"{path.name}.meta.json")


def resolve_observability_paths(
    result_path: str | Path,
    *,
    event_path: str | Path | None = None,
    summary_path: str | Path | None = None,
    hash_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    allow_external: bool = False,
) -> ObservabilityPaths:
    """Resolve and validate event, summary, and hash sidecar paths."""

    result = Path(result_path)
    event = Path(event_path) if event_path is not None else default_observability_event_path(result)
    summary = (
        Path(summary_path)
        if summary_path is not None
        else default_observability_summary_path(result)
    )
    hash_sidecar = (
        Path(hash_path) if hash_path is not None else default_observability_hash_path(event)
    )
    paths = ObservabilityPaths(
        result_path=result,
        event_path=event,
        summary_path=summary,
        hash_path=hash_sidecar,
    )
    validate_observability_paths(
        paths,
        workspace_root=workspace_root,
        allow_external=allow_external,
    )
    return paths


def validate_observability_paths(
    paths: ObservabilityPaths,
    *,
    workspace_root: str | Path | None = None,
    allow_external: bool = False,
) -> None:
    """Fail before sidecar paths can collide with result or hash artifacts."""

    result_hash = default_result_content_hash_path(paths.result_path)
    result_meta = default_result_metadata_path(paths.result_path)
    named_paths = {
        "result_path": paths.result_path,
        "result_content_hash_path": result_hash,
        "result_metadata_path": result_meta,
        "event_path": paths.event_path,
        "summary_path": paths.summary_path,
        "hash_path": paths.hash_path,
    }
    sidecar_fields = ("event_path", "summary_path", "hash_path")
    for sidecar_name in sidecar_fields:
        sidecar = named_paths[sidecar_name]
        for other_name, other in named_paths.items():
            if sidecar_name == other_name:
                continue
            if _same_path(sidecar, other):
                raise ValueError(f"{sidecar_name} collides with {other_name}")
        if sidecar.exists() and not sidecar.is_file():
            raise ValueError(f"{sidecar_name} points at an existing non-file path")

    if workspace_root is not None and not allow_external:
        root = Path(workspace_root).resolve()
        for sidecar_name in sidecar_fields:
            resolved = named_paths[sidecar_name].resolve(strict=False)
            if not resolved.is_relative_to(root):
                raise ValueError(f"{sidecar_name} resolves outside the workspace root")


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)
