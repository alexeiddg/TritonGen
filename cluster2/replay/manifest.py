"""Frozen Cluster 1 replay-control manifest validation.

Phase 0 uses this module only to validate artifact-driven metadata. It does not
load candidate sources, call generation, evaluate correctness, or repair code.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cluster2.constants import (
    DEFAULT_EQUAL_ATTEMPTS_N,
    DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    DTYPE_NAMES,
    REPLAY_CONTROL_CONDITIONS,
    require_replay_control_condition,
)
from shared.eval.content_hashes import file_sha256
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES


REPLAY_GRAMMAR_VARIANT_TASK_AGNOSTIC = "task_agnostic"
REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND = "template_upper_bound"
_TEMPLATE_SELECTED_CONTROLS = "cluster2_v5_template_upper_bound_controls"
_TASK_AGNOSTIC_G_STATUS = "task_agnostic_g_status"


@dataclass(frozen=True)
class ReplayArtifactSummary:
    artifact_id: str
    condition: str
    path: str
    sha256: str
    row_count: int
    grammar_active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayCellCoverage:
    artifact_id: str
    condition: str
    kernel_class: str
    dtype: str
    required_rows: int
    observed_rows: int
    missing_rows: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayManifestIntegrity:
    manifest_path: str
    schema_version: int
    selected_artifact_ids: tuple[str, ...]
    artifacts: tuple[ReplayArtifactSummary, ...]
    coverage: tuple[ReplayCellCoverage, ...]
    artifact_hash_mismatches: tuple[str, ...]
    valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def load_frozen_cluster1_manifest(
    path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
) -> dict[str, Any]:
    """Load the tracked frozen Cluster 1 replay-control manifest."""

    manifest_path = Path(path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def selected_template_control_artifact_ids(manifest: dict[str, Any]) -> tuple[str, ...]:
    """Return the Phase -1 selected template-control artifact ids."""

    selected = manifest.get("selected_controls", {}).get(
        _TEMPLATE_SELECTED_CONTROLS,
        {},
    )
    artifact_ids = selected.get("artifact_ids", [])
    if not isinstance(artifact_ids, list) or not all(
        isinstance(item, str) for item in artifact_ids
    ):
        raise ValueError("selected template control artifact_ids must be a list of strings")
    return tuple(artifact_ids)


def selected_replay_control_artifact_ids(
    manifest: dict[str, Any],
    *,
    grammar_variant: str = REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
) -> tuple[str, ...]:
    """Return selected replay artifact ids for the requested grammar route."""

    return tuple(
        artifact_id
        for condition in REPLAY_CONTROL_CONDITIONS
        for artifact_id in selected_replay_artifact_ids_for_condition(
            condition,
            manifest,
            grammar_variant=grammar_variant,
        )
    )


def selected_replay_artifact_ids_for_condition(
    condition: str,
    manifest: dict[str, Any],
    *,
    grammar_variant: str = REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
) -> tuple[str, ...]:
    """Return selected replay artifact ids for one replay condition."""

    normalized = require_replay_control_condition(condition)
    requested_variant = _require_replay_grammar_variant(grammar_variant)
    if normalized == "G" and requested_variant == REPLAY_GRAMMAR_VARIANT_TASK_AGNOSTIC:
        return (_task_agnostic_g_artifact_id(manifest),)
    return _selected_template_artifact_ids_for_condition(normalized, manifest)


def artifact_for_replay_condition(
    condition: str,
    manifest: dict[str, Any] | None = None,
    *,
    manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    grammar_variant: str = REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
) -> ReplayArtifactSummary:
    """Return the selected replay artifact for ``condition``."""

    normalized = require_replay_control_condition(condition)
    loaded_manifest = (
        load_frozen_cluster1_manifest(manifest_path) if manifest is None else manifest
    )
    selected_ids = set(
        selected_replay_artifact_ids_for_condition(
            normalized,
            loaded_manifest,
            grammar_variant=grammar_variant,
        )
    )
    for artifact in loaded_manifest.get("artifacts", []):
        if artifact.get("artifact_id") not in selected_ids:
            continue
        if artifact.get("condition") == normalized:
            return _artifact_summary_from_manifest(artifact)
    raise KeyError(f"no selected replay artifact for condition {normalized!r}")


def validate_replay_manifest_integrity(
    path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    *,
    required_attempts: int = DEFAULT_EQUAL_ATTEMPTS_N,
    verify_artifact_hashes: bool = False,
    grammar_variant: str = REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
) -> ReplayManifestIntegrity:
    """Validate selected replay-control metadata without evaluating candidates."""

    manifest_path = Path(path)
    manifest = load_frozen_cluster1_manifest(manifest_path)
    selected_ids = selected_replay_control_artifact_ids(
        manifest,
        grammar_variant=grammar_variant,
    )
    artifacts_by_id = {
        artifact.get("artifact_id"): artifact for artifact in manifest.get("artifacts", [])
    }
    selected_artifacts = [
        artifacts_by_id[artifact_id]
        for artifact_id in selected_ids
        if artifact_id in artifacts_by_id
    ]
    summaries = tuple(_artifact_summary_from_manifest(artifact) for artifact in selected_artifacts)
    coverage = tuple(
        item
        for artifact in selected_artifacts
        for item in _coverage_for_artifact(artifact, required_attempts=required_attempts)
    )
    hash_mismatches = (
        tuple(_artifact_hash_mismatches(selected_artifacts))
        if verify_artifact_hashes
        else ()
    )

    selected_conditions = {summary.condition for summary in summaries}
    required_conditions_present = all(
        condition in selected_conditions for condition in REPLAY_CONTROL_CONDITIONS
    )
    coverage_ok = all(item.status == "ok" for item in coverage)
    valid = required_conditions_present and coverage_ok and not hash_mismatches

    return ReplayManifestIntegrity(
        manifest_path=str(manifest_path),
        schema_version=int(manifest.get("schema_version", 0)),
        selected_artifact_ids=selected_ids,
        artifacts=summaries,
        coverage=coverage,
        artifact_hash_mismatches=hash_mismatches,
        valid=valid,
    )


def _require_replay_grammar_variant(grammar_variant: str) -> str:
    if grammar_variant not in {
        REPLAY_GRAMMAR_VARIANT_TASK_AGNOSTIC,
        REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
    }:
        raise ValueError(
            "grammar_variant must be one of: "
            f"{REPLAY_GRAMMAR_VARIANT_TASK_AGNOSTIC}, "
            f"{REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND}"
        )
    return grammar_variant


def _selected_template_artifact_ids_for_condition(
    condition: str,
    manifest: dict[str, Any],
) -> tuple[str, ...]:
    artifact_conditions = _artifact_conditions_by_id(manifest)
    selected_ids = tuple(
        artifact_id
        for artifact_id in selected_template_control_artifact_ids(manifest)
        if artifact_conditions.get(artifact_id) == condition
    )
    if not selected_ids:
        raise KeyError(f"no selected replay artifact for condition {condition!r}")
    return selected_ids


def _task_agnostic_g_artifact_id(manifest: dict[str, Any]) -> str:
    selected_controls = manifest.get("selected_controls", {})
    status = selected_controls.get(_TASK_AGNOSTIC_G_STATUS, {})
    artifact_id = status.get("available_development_artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ValueError("task-agnostic G replay artifact id is not recorded")

    artifacts = {
        artifact.get("artifact_id"): artifact
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
    }
    artifact = artifacts.get(artifact_id)
    if not isinstance(artifact, dict):
        raise KeyError(f"task-agnostic G replay artifact {artifact_id!r} missing")
    if artifact.get("condition") != "G":
        raise ValueError("task-agnostic replay artifact must belong to condition 'G'")
    condition_check = artifact.get("condition_flag_check", {})
    expected_variant = condition_check.get("expected_grammar_variant")
    if expected_variant != REPLAY_GRAMMAR_VARIANT_TASK_AGNOSTIC:
        raise ValueError("task-agnostic G replay artifact is not marked task_agnostic")
    return artifact_id


def _artifact_conditions_by_id(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        artifact["artifact_id"]: artifact["condition"]
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict)
        and isinstance(artifact.get("artifact_id"), str)
        and isinstance(artifact.get("condition"), str)
    }


def _artifact_summary_from_manifest(artifact: dict[str, Any]) -> ReplayArtifactSummary:
    condition = require_replay_control_condition(artifact["condition"])
    condition_check = artifact.get("condition_flag_check", {})
    expected_grammar_active = bool(condition_check.get("expected_grammar_active", condition == "G"))
    return ReplayArtifactSummary(
        artifact_id=artifact["artifact_id"],
        condition=condition,
        path=artifact["path"],
        sha256=artifact["sha256"],
        row_count=int(artifact["row_count"]),
        grammar_active=expected_grammar_active,
    )


def _coverage_for_artifact(
    artifact: dict[str, Any],
    *,
    required_attempts: int,
) -> tuple[ReplayCellCoverage, ...]:
    rows = artifact.get("rows_per_kernel_dtype_grammar_active", [])
    observed_by_cell = {
        (row.get("kernel_class"), row.get("dtype")): int(row.get("row_count", 0))
        for row in rows
    }
    records: list[ReplayCellCoverage] = []
    for kernel_class in LOCKED_KERNEL_CLASSES:
        for dtype in DTYPE_NAMES:
            observed = observed_by_cell.get((kernel_class, dtype), 0)
            missing = max(0, required_attempts - observed)
            status = "ok" if missing == 0 else "coverage_failure_missing_frozen_control"
            records.append(
                ReplayCellCoverage(
                    artifact_id=artifact["artifact_id"],
                    condition=require_replay_control_condition(artifact["condition"]),
                    kernel_class=kernel_class,
                    dtype=dtype,
                    required_rows=required_attempts,
                    observed_rows=observed,
                    missing_rows=missing,
                    status=status,
                )
            )
    return tuple(records)


def _artifact_hash_mismatches(artifacts: list[dict[str, Any]]) -> list[str]:
    mismatches: list[str] = []
    for artifact in artifacts:
        artifact_path = Path(artifact["path"])
        if not artifact_path.is_file():
            mismatches.append(f"{artifact['artifact_id']}:missing_artifact:{artifact_path}")
        elif file_sha256(artifact_path) != artifact["sha256"]:
            mismatches.append(f"{artifact['artifact_id']}:artifact_sha256")

        sidecar = artifact.get("metadata_sidecar")
        if isinstance(sidecar, dict) and sidecar.get("path") and sidecar.get("sha256"):
            sidecar_path = Path(sidecar["path"])
            if not sidecar_path.is_file():
                mismatches.append(f"{artifact['artifact_id']}:missing_sidecar:{sidecar_path}")
            elif file_sha256(sidecar_path) != sidecar["sha256"]:
                mismatches.append(f"{artifact['artifact_id']}:sidecar_sha256")
    return mismatches
