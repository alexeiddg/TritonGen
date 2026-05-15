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
class ReplaySeedScheduleEntry:
    """One manifest-authoritative seed/prompt row for paired replay."""

    artifact_id: str
    condition: str
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    generation_seed: int
    attempt_index: int
    generation_index: int
    prompt_sha256: str
    model_id: str
    model_revision: str | None
    tokenizer_revision: str | None
    temperature: float
    max_new_tokens: int
    line_number: int
    replay_pair_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayManifestIntegrity:
    manifest_path: str
    schema_version: int
    selected_artifact_ids: tuple[str, ...]
    artifacts: tuple[ReplayArtifactSummary, ...]
    coverage: tuple[ReplayCellCoverage, ...]
    seed_schedule_failures: tuple[str, ...]
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
    seed_schedule_failures = tuple(
        _seed_schedule_failures(
            selected_artifacts,
            required_attempts=required_attempts,
        )
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
    valid = (
        required_conditions_present
        and coverage_ok
        and not seed_schedule_failures
        and not hash_mismatches
    )

    return ReplayManifestIntegrity(
        manifest_path=str(manifest_path),
        schema_version=int(manifest.get("schema_version", 0)),
        selected_artifact_ids=selected_ids,
        artifacts=summaries,
        coverage=coverage,
        seed_schedule_failures=seed_schedule_failures,
        artifact_hash_mismatches=hash_mismatches,
        valid=valid,
    )


def replay_seed_schedule_for_condition(
    *,
    condition: str,
    kernel_class: str,
    dtype: str,
    candidate_count: int,
    manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    grammar_variant: str = REPLAY_GRAMMAR_VARIANT_TEMPLATE_UPPER_BOUND,
) -> tuple[ReplaySeedScheduleEntry, ...]:
    """Return the manifest-authoritative paired seed schedule for one cell."""

    normalized = require_replay_control_condition(condition)
    _require_kernel_class(kernel_class)
    _require_dtype(dtype)
    _require_positive_int(candidate_count, "candidate_count")

    manifest = load_frozen_cluster1_manifest(manifest_path)
    selected_ids = set(
        selected_replay_artifact_ids_for_condition(
            normalized,
            manifest,
            grammar_variant=grammar_variant,
        )
    )
    selected_artifacts = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("artifact_id") in selected_ids
        and artifact.get("condition") == normalized
    ]
    if len(selected_artifacts) != 1:
        raise ValueError(
            f"expected exactly one selected replay artifact for {normalized!r}, "
            f"got {len(selected_artifacts)}"
        )

    entries = tuple(
        entry
        for entry in _seed_schedule_entries_for_artifact(selected_artifacts[0])
        if entry.kernel_class == kernel_class and entry.dtype == dtype
    )
    if len(entries) < candidate_count:
        raise ValueError(
            "seed_schedule coverage failure for "
            f"{normalized}/{kernel_class}/{dtype}: required {candidate_count}, "
            f"observed {len(entries)}"
        )
    selected = entries[:candidate_count]
    expected_base_seeds = tuple(range(candidate_count))
    observed_base_seeds = tuple(entry.base_seed for entry in selected)
    if observed_base_seeds != expected_base_seeds:
        raise ValueError(
            "seed_schedule must be dense and zero-based for requested window: "
            f"expected {expected_base_seeds}, got {observed_base_seeds}"
        )
    return selected


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


def _seed_schedule_failures(
    artifacts: list[dict[str, Any]],
    *,
    required_attempts: int,
) -> list[str]:
    failures: list[str] = []
    for artifact in artifacts:
        try:
            entries = _seed_schedule_entries_for_artifact(artifact)
        except (TypeError, ValueError, KeyError) as exc:
            failures.append(f"{artifact.get('artifact_id', '<unknown>')}:seed_schedule:{exc}")
            continue
        by_cell: dict[tuple[str, str], list[ReplaySeedScheduleEntry]] = {}
        for entry in entries:
            by_cell.setdefault((entry.kernel_class, entry.dtype), []).append(entry)
        for kernel_class in LOCKED_KERNEL_CLASSES:
            for dtype in DTYPE_NAMES:
                cell_entries = sorted(
                    by_cell.get((kernel_class, dtype), []),
                    key=lambda entry: entry.base_seed,
                )
                observed_all = tuple(entry.base_seed for entry in cell_entries)
                expected_all = tuple(range(len(cell_entries)))
                if len(set(observed_all)) != len(observed_all):
                    failures.append(
                        f"{artifact['artifact_id']}:{kernel_class}:{dtype}:"
                        f"duplicate_seed_schedule_base_seed:{observed_all}"
                    )
                    continue
                if observed_all != expected_all:
                    failures.append(
                        f"{artifact['artifact_id']}:{kernel_class}:{dtype}:"
                        f"seed_schedule_not_dense:{observed_all}"
                    )
                    continue
                if len(cell_entries) < required_attempts:
                    failures.append(
                        f"{artifact['artifact_id']}:{kernel_class}:{dtype}:"
                        f"seed_schedule_rows<{required_attempts}"
                    )
                    continue
    return failures


def _seed_schedule_entries_for_artifact(
    artifact: dict[str, Any],
) -> tuple[ReplaySeedScheduleEntry, ...]:
    artifact_id = _require_non_empty_str(artifact.get("artifact_id"), "artifact_id")
    condition = require_replay_control_condition(
        _require_non_empty_str(artifact.get("condition"), "condition")
    )
    schedule = artifact.get("seed_schedule")
    if not isinstance(schedule, dict):
        raise ValueError("seed_schedule must be an object")
    if schedule.get("schedule_type") != "paired_by_seed":
        raise ValueError("seed_schedule.schedule_type must be 'paired_by_seed'")
    schedule_records = schedule.get("records")
    if not isinstance(schedule_records, list) or not schedule_records:
        raise ValueError("seed_schedule.records must be a non-empty list")
    row_records = artifact.get("row_records")
    if not isinstance(row_records, list) or not row_records:
        raise ValueError("row_records must be a non-empty list")

    row_by_line: dict[int, dict[str, Any]] = {}
    for record in row_records:
        if not isinstance(record, dict):
            continue
        line_number = _require_positive_int(record.get("line_number"), "line_number")
        if line_number in row_by_line:
            raise ValueError(f"duplicate row_record line_number {line_number}")
        row_by_line[line_number] = record
    entries: list[ReplaySeedScheduleEntry] = []
    seen_pair_ids: set[str] = set()
    for schedule_record in schedule_records:
        if not isinstance(schedule_record, dict):
            raise ValueError("seed_schedule.records entries must be objects")
        cell_entries = _entries_for_schedule_record(
            artifact_id=artifact_id,
            condition=condition,
            schedule_record=schedule_record,
            row_by_line=row_by_line,
        )
        for entry in cell_entries:
            if entry.replay_pair_id in seen_pair_ids:
                raise ValueError(f"duplicate replay_pair_id {entry.replay_pair_id!r}")
            seen_pair_ids.add(entry.replay_pair_id)
        entries.extend(cell_entries)
    return tuple(sorted(entries, key=_seed_schedule_entry_order_key))


def _entries_for_schedule_record(
    *,
    artifact_id: str,
    condition: str,
    schedule_record: dict[str, Any],
    row_by_line: dict[int, dict[str, Any]],
) -> tuple[ReplaySeedScheduleEntry, ...]:
    kernel_class = _require_kernel_class(
        _require_non_empty_str(schedule_record.get("kernel_class"), "kernel_class")
    )
    kernel_name = _require_non_empty_str(schedule_record.get("kernel_name"), "kernel_name")
    dtype = _require_dtype(_require_non_empty_str(schedule_record.get("dtype"), "dtype"))
    prompt_sha256 = _require_sha256(schedule_record.get("prompt_sha256"), "prompt_sha256")
    model_id = _require_non_empty_str(schedule_record.get("model_id"), "model_id")
    model_revision = _optional_str(schedule_record.get("model_revision"))
    tokenizer_revision = _optional_str(schedule_record.get("tokenizer_revision"))
    temperature = _require_non_negative_number(
        schedule_record.get("temperature"),
        "temperature",
    )
    max_new_tokens = _require_positive_int(
        schedule_record.get("max_new_tokens"),
        "max_new_tokens",
    )
    base_seeds = _require_int_list(schedule_record.get("base_seeds"), "base_seeds")
    generation_seeds = _require_int_list(
        schedule_record.get("generation_seeds"),
        "generation_seeds",
    )
    attempt_indexes = _require_int_list(
        schedule_record.get("attempt_indexes"),
        "attempt_indexes",
    )
    generation_indexes = _require_int_list(
        schedule_record.get("generation_indexes"),
        "generation_indexes",
    )
    line_numbers = _require_int_list(schedule_record.get("line_numbers"), "line_numbers")
    replay_pair_ids = _require_str_list(
        schedule_record.get("replay_pair_ids"),
        "replay_pair_ids",
    )
    lengths = {
        len(base_seeds),
        len(generation_seeds),
        len(attempt_indexes),
        len(generation_indexes),
        len(line_numbers),
        len(replay_pair_ids),
    }
    if len(lengths) != 1:
        raise ValueError("seed_schedule lists must have identical lengths")

    entries: list[ReplaySeedScheduleEntry] = []
    for index, line_number in enumerate(line_numbers):
        row_record = row_by_line.get(line_number)
        if row_record is None:
            raise ValueError(f"seed_schedule line_number {line_number} missing row_record")
        entry = ReplaySeedScheduleEntry(
            artifact_id=artifact_id,
            condition=condition,
            kernel_class=kernel_class,
            kernel_name=kernel_name,
            dtype=dtype,
            base_seed=base_seeds[index],
            generation_seed=generation_seeds[index],
            attempt_index=attempt_indexes[index],
            generation_index=generation_indexes[index],
            prompt_sha256=prompt_sha256,
            model_id=model_id,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            line_number=line_number,
            replay_pair_id=replay_pair_ids[index],
        )
        _validate_schedule_entry_matches_row(entry, row_record)
        entries.append(entry)
    return tuple(entries)


def _validate_schedule_entry_matches_row(
    entry: ReplaySeedScheduleEntry,
    record: dict[str, Any],
) -> None:
    expected = {
        "condition": entry.condition,
        "kernel_class": entry.kernel_class,
        "kernel_name": entry.kernel_name,
        "dtype": entry.dtype,
        "base_seed": entry.base_seed,
        "generation_seed": entry.generation_seed,
        "attempt_index": entry.attempt_index,
        "generation_index": entry.generation_index,
        "prompt_sha256": entry.prompt_sha256,
        "model_id": entry.model_id,
        "model_revision": entry.model_revision,
        "tokenizer_revision": entry.tokenizer_revision,
        "temperature": entry.temperature,
        "max_new_tokens": entry.max_new_tokens,
        "replay_pair_id": entry.replay_pair_id,
    }
    for field_name, expected_value in expected.items():
        if record.get(field_name) != expected_value:
            raise ValueError(
                f"seed_schedule row mismatch for {field_name}: "
                f"expected {expected_value!r}, got {record.get(field_name)!r}"
            )
    if entry.base_seed != entry.generation_seed:
        raise ValueError("base_seed must equal generation_seed for paired replay")
    if entry.attempt_index != entry.generation_index:
        raise ValueError("attempt_index must equal generation_index for paired replay")


def _seed_schedule_entry_order_key(
    entry: ReplaySeedScheduleEntry,
) -> tuple[str, str, int]:
    return (entry.kernel_class, entry.dtype, entry.base_seed)


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


def _require_kernel_class(value: str) -> str:
    if value not in LOCKED_KERNEL_CLASSES:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise ValueError(f"unsupported kernel_class {value!r}; allowed: {allowed}")
    return value


def _require_dtype(value: str) -> str:
    if value not in DTYPE_NAMES:
        allowed = ", ".join(DTYPE_NAMES)
        raise ValueError(f"unsupported dtype {value!r}; allowed: {allowed}")
    return value


def _require_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _require_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _require_non_negative_number(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return float(value)


def _require_non_empty_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("expected str or None")
    return value


def _require_sha256(value: object, field_name: str) -> str:
    digest = _require_non_empty_str(value, field_name)
    if len(digest) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc
    return digest


def _require_int_list(value: object, field_name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    return tuple(_require_non_negative_int(item, field_name) for item in value)


def _require_str_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    return tuple(_require_non_empty_str(item, field_name) for item in value)
