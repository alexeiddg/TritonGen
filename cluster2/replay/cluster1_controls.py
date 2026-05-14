"""Replay adapter for frozen Cluster 1 controls.

This module maps frozen Cluster 1 JSONL rows into deterministic Cluster 2
replay candidates. It never calls model generation, correctness evaluation, or
repair-loop code.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cluster2.constants import (
    DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    DTYPE_NAMES,
    require_replay_control_condition,
)
from cluster2.replay.manifest import (
    artifact_for_replay_condition,
    load_frozen_cluster1_manifest,
)
from shared.eval.content_hashes import (
    collect_cluster1_frozen_generation_hashes,
    file_sha256,
)
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES, get_shape_metadata


COVERAGE_FAILURE_MISSING_FROZEN_CONTROL = (
    "coverage_failure_missing_frozen_control"
)
REPLAY_MAPPING_OK = "ok"
_TEMPLATE_SELECTED_CONTROLS = "cluster2_v5_template_upper_bound_controls"


@dataclass(frozen=True)
class FrozenReplayCandidate:
    """One frozen Cluster 1 source mapped into a C2 replay attempt."""

    condition: str
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    attempt_index: int
    source: str
    source_sha256: str
    row_sha256: str
    unique_solution_hash: str
    model_id: str
    model_revision: str | None
    tokenizer_revision: str | None
    generation_seed: int | None
    generation_index: int | None
    frozen_attempt_index: int | None
    artifact_id: str
    artifact_path: str
    artifact_sha256: str
    grammar_active: bool
    grammar_variant: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayCoverageFailure:
    """Pre-candidate coverage failure for a replay-control cell."""

    condition: str
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    required_rows: int
    observed_rows: int
    missing_rows: int
    status: str = COVERAGE_FAILURE_MISSING_FROZEN_CONTROL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayCandidateMapping:
    """Result of mapping one replay-control cell."""

    condition: str
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    required_rows: int
    status: str
    candidates: tuple[FrozenReplayCandidate, ...]
    coverage_failure: ReplayCoverageFailure | None = None

    @property
    def ok(self) -> bool:
        return self.status == REPLAY_MAPPING_OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "kernel_class": self.kernel_class,
            "kernel_name": self.kernel_name,
            "dtype": self.dtype,
            "base_seed": self.base_seed,
            "required_rows": self.required_rows,
            "status": self.status,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "coverage_failure": (
                None
                if self.coverage_failure is None
                else self.coverage_failure.to_dict()
            ),
        }


def map_replay_candidates(
    *,
    condition: str,
    kernel_class: str,
    dtype: str,
    candidate_count: int,
    manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    base_seed: int = 0,
) -> ReplayCandidateMapping:
    """Map exactly ``candidate_count`` frozen sources for one replay cell.

    Candidate attempts are deterministic and dense: attempt indexes
    ``0..candidate_count-1`` are selected from frozen attempt/generation indexes.
    If the frozen artifact cannot cover the requested window, the mapping is
    marked as a coverage failure and no generation fallback is attempted.
    """

    normalized = require_replay_control_condition(condition)
    _require_kernel_class(kernel_class)
    _require_dtype(dtype)
    _require_positive_int(candidate_count, "candidate_count")
    _require_non_negative_int(base_seed, "base_seed")

    manifest_file = Path(manifest_path)
    manifest = load_frozen_cluster1_manifest(manifest_file)
    artifact = _selected_artifact(normalized, manifest)
    artifact_summary = artifact_for_replay_condition(normalized, manifest)
    artifact_path = _resolve_artifact_path(artifact_summary.path, manifest_file)
    _verify_artifact_sha256(
        artifact_path,
        expected_sha256=artifact_summary.sha256,
        artifact_id=artifact_summary.artifact_id,
    )
    raw_rows = _load_raw_artifact_rows(artifact_path)
    row_records = _matching_manifest_rows(
        artifact,
        condition=normalized,
        kernel_class=kernel_class,
        dtype=dtype,
        grammar_active=artifact_summary.grammar_active,
    )
    selected_records = _select_attempt_records(row_records, candidate_count)
    metadata = get_shape_metadata(kernel_class)

    if len(selected_records) < candidate_count:
        failure = ReplayCoverageFailure(
            condition=normalized,
            kernel_class=kernel_class,
            kernel_name=metadata.kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            required_rows=candidate_count,
            observed_rows=len(selected_records),
            missing_rows=candidate_count - len(selected_records),
        )
        return ReplayCandidateMapping(
            condition=normalized,
            kernel_class=kernel_class,
            kernel_name=metadata.kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            required_rows=candidate_count,
            status=COVERAGE_FAILURE_MISSING_FROZEN_CONTROL,
            candidates=(),
            coverage_failure=failure,
        )

    candidates = tuple(
        _candidate_from_record(
            record,
            raw_rows=raw_rows,
            condition=normalized,
            kernel_class=kernel_class,
            kernel_name=metadata.kernel_name,
            dtype=dtype,
            base_seed=base_seed,
            mapped_attempt_index=attempt_index,
            artifact_id=artifact_summary.artifact_id,
            artifact_path=str(artifact_path),
            artifact_sha256=artifact_summary.sha256,
            grammar_active=artifact_summary.grammar_active,
        )
        for attempt_index, record in enumerate(selected_records)
    )
    return ReplayCandidateMapping(
        condition=normalized,
        kernel_class=kernel_class,
        kernel_name=metadata.kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        required_rows=candidate_count,
        status=REPLAY_MAPPING_OK,
        candidates=candidates,
        coverage_failure=None,
    )


def replay_generation_hashes(
    condition: str,
    manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
) -> dict[str, str]:
    """Return the authoritative frozen hash class for replay row metadata."""

    normalized = require_replay_control_condition(condition)
    return collect_cluster1_frozen_generation_hashes(normalized, str(manifest_path))


def _selected_artifact(condition: str, manifest: dict[str, Any]) -> dict[str, Any]:
    selected_ids = set(
        manifest.get("selected_controls", {})
        .get(_TEMPLATE_SELECTED_CONTROLS, {})
        .get("artifact_ids", [])
    )
    for artifact in manifest.get("artifacts", []):
        if artifact.get("artifact_id") in selected_ids and artifact.get("condition") == condition:
            return artifact
    raise KeyError(f"no selected frozen replay artifact for {condition!r}")


def _resolve_artifact_path(path: str, manifest_path: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    manifest_relative = manifest_path.parent / candidate
    if manifest_relative.is_file():
        return manifest_relative
    return Path.cwd() / candidate


def _verify_artifact_sha256(
    path: Path,
    *,
    expected_sha256: str,
    artifact_id: str,
) -> None:
    observed_sha256 = file_sha256(path)
    if observed_sha256 != expected_sha256:
        raise ValueError(
            "frozen Cluster 1 artifact hash mismatch for "
            f"{artifact_id}: expected {expected_sha256}, got {observed_sha256}"
        )


def _load_raw_artifact_rows(path: Path) -> dict[int, tuple[dict[str, Any], str]]:
    raw_by_line: dict[int, tuple[dict[str, Any], str]] = {}
    for line_number, raw_line in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        if not raw_line.strip():
            raise ValueError(f"blank frozen Cluster 1 JSONL line at {line_number}")
        row_sha256 = hashlib.sha256(raw_line).hexdigest()
        payload = json.loads(raw_line.decode("utf-8"))
        raw_by_line[line_number] = (payload, row_sha256)
    return raw_by_line


def _matching_manifest_rows(
    artifact: dict[str, Any],
    *,
    condition: str,
    kernel_class: str,
    dtype: str,
    grammar_active: bool,
) -> tuple[dict[str, Any], ...]:
    rows = []
    for record in artifact.get("row_records", []):
        if record.get("condition") != condition:
            continue
        if record.get("kernel_class") != kernel_class:
            continue
        if record.get("dtype") != dtype:
            continue
        if bool(record.get("grammar_active")) != grammar_active:
            continue
        rows.append(record)
    return tuple(sorted(rows, key=_record_order_key))


def _select_attempt_records(
    row_records: Sequence[dict[str, Any]],
    candidate_count: int,
) -> tuple[dict[str, Any], ...]:
    by_attempt: dict[int, dict[str, Any]] = {}
    for record in row_records:
        key = _record_attempt_key(record)
        if key is None or key < 0 or key >= candidate_count:
            continue
        by_attempt.setdefault(key, record)

    if len(by_attempt) == candidate_count:
        return tuple(by_attempt[index] for index in range(candidate_count))

    return tuple(
        by_attempt[index]
        for index in range(candidate_count)
        if index in by_attempt
    )


def _candidate_from_record(
    record: dict[str, Any],
    *,
    raw_rows: dict[int, tuple[dict[str, Any], str]],
    condition: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    mapped_attempt_index: int,
    artifact_id: str,
    artifact_path: str,
    artifact_sha256: str,
    grammar_active: bool,
) -> FrozenReplayCandidate:
    line_number = _require_positive_int(record.get("line_number"), "line_number")
    try:
        raw_row, observed_row_hash = raw_rows[line_number]
    except KeyError as exc:
        raise ValueError(f"frozen artifact missing line {line_number}") from exc

    source = raw_row.get("source")
    if not isinstance(source, str) or not source:
        raise ValueError(f"frozen artifact line {line_number} is missing source")
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    expected_source_hash = record.get("source_sha256")
    if source_hash != expected_source_hash:
        raise ValueError(
            f"source_sha256 mismatch at frozen artifact line {line_number}"
        )
    expected_row_hash = record.get("row_sha256")
    if observed_row_hash != expected_row_hash:
        raise ValueError(f"row_sha256 mismatch at frozen artifact line {line_number}")

    _validate_raw_row_matches_record(
        raw_row,
        record,
        condition=condition,
        kernel_class=kernel_class,
        dtype=dtype,
        grammar_active=grammar_active,
    )

    return FrozenReplayCandidate(
        condition=condition,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        attempt_index=mapped_attempt_index,
        source=source,
        source_sha256=source_hash,
        row_sha256=observed_row_hash,
        unique_solution_hash=str(record.get("unique_solution_hash") or ""),
        model_id=str(record.get("model_id") or raw_row.get("model_id") or ""),
        model_revision=_optional_str(record.get("model_revision")),
        tokenizer_revision=_optional_str(record.get("tokenizer_revision")),
        generation_seed=_optional_int(record.get("generation_seed")),
        generation_index=_optional_int(record.get("generation_index")),
        frozen_attempt_index=_optional_int(record.get("attempt_index")),
        artifact_id=artifact_id,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        grammar_active=grammar_active,
        grammar_variant=_optional_str(record.get("grammar_variant")),
    )


def _validate_raw_row_matches_record(
    raw_row: dict[str, Any],
    record: dict[str, Any],
    *,
    condition: str,
    kernel_class: str,
    dtype: str,
    grammar_active: bool,
) -> None:
    del condition
    checks = {
        "kernel_class": kernel_class,
        "dtype": dtype,
        "grammar_active": grammar_active,
    }
    for field_name, expected in checks.items():
        if raw_row.get(field_name) != expected:
            raise ValueError(
                f"frozen row {field_name} mismatch: expected {expected!r}, "
                f"got {raw_row.get(field_name)!r}"
            )
    if raw_row.get("kernel_name") != record.get("kernel_name"):
        raise ValueError("frozen row kernel_name mismatch")
    raw_seed = raw_row.get("generation_seed")
    record_seed = record.get("generation_seed")
    if raw_seed != record_seed:
        raise ValueError("frozen row generation_seed mismatch")


def _record_order_key(record: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        _sort_int(record.get("attempt_index")),
        _sort_int(record.get("generation_index")),
        _sort_int(record.get("generation_seed")),
        _sort_int(record.get("line_number")),
    )


def _record_attempt_key(record: dict[str, Any]) -> int | None:
    for field_name in ("attempt_index", "generation_index", "generation_seed"):
        value = _optional_int(record.get(field_name))
        if value is not None:
            return value
    return None


def _sort_int(value: object) -> int:
    parsed = _optional_int(value)
    return parsed if parsed is not None else 2**31 - 1


def _require_kernel_class(value: str) -> None:
    if value not in LOCKED_KERNEL_CLASSES:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise ValueError(f"unsupported kernel_class {value!r}; allowed: {allowed}")


def _require_dtype(value: str) -> None:
    if value not in DTYPE_NAMES:
        allowed = ", ".join(DTYPE_NAMES)
        raise ValueError(f"unsupported dtype {value!r}; allowed: {allowed}")


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


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("expected int or None")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("expected str or None")
    return value
