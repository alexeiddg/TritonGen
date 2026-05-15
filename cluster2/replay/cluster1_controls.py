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
    ReplaySeedScheduleEntry,
    artifact_for_replay_condition,
    load_frozen_cluster1_manifest,
    selected_replay_artifact_ids_for_condition,
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
    prompt_sha256: str
    temperature: float
    max_new_tokens: int
    replay_pair_id: str
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
    grammar_variant: str = "template_upper_bound",
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
    artifact = _selected_artifact(
        normalized,
        manifest,
        grammar_variant=grammar_variant,
    )
    artifact_summary = artifact_for_replay_condition(
        normalized,
        manifest,
        grammar_variant=grammar_variant,
    )
    artifact_path = _resolve_artifact_path(artifact_summary.path, manifest_file)
    _verify_artifact_sha256(
        artifact_path,
        expected_sha256=artifact_summary.sha256,
        artifact_id=artifact_summary.artifact_id,
    )
    selected_schedule = _validate_seed_schedule_cell_structure(
        artifact,
        condition=normalized,
        kernel_class=kernel_class,
        dtype=dtype,
        candidate_count=candidate_count,
    )
    raw_rows = _load_raw_artifact_rows(artifact_path)
    row_records = _matching_manifest_rows(
        artifact,
        condition=normalized,
        kernel_class=kernel_class,
        dtype=dtype,
        grammar_active=artifact_summary.grammar_active,
    )
    _validate_available_records_match_seed_schedule(
        artifact.get("row_records", []),
        selected_schedule,
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

    selected_records = _records_for_seed_schedule(row_records, selected_schedule)
    candidates = tuple(
        _candidate_from_record(
            record,
            schedule_entry=selected_schedule[attempt_index],
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


def _validate_seed_schedule_present(artifact: dict[str, Any]) -> None:
    schedule = artifact.get("seed_schedule")
    if not isinstance(schedule, dict):
        raise ValueError("seed_schedule must be an object")
    if schedule.get("schedule_type") != "paired_by_seed":
        raise ValueError("seed_schedule.schedule_type must be 'paired_by_seed'")
    records = schedule.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("seed_schedule.records must be a non-empty list")


def _validate_seed_schedule_cell_structure(
    artifact: dict[str, Any],
    *,
    condition: str,
    kernel_class: str,
    dtype: str,
    candidate_count: int,
) -> tuple[ReplaySeedScheduleEntry, ...]:
    _validate_seed_schedule_present(artifact)
    artifact_id = _require_non_empty_str(artifact.get("artifact_id"), "artifact_id")
    records = artifact["seed_schedule"]["records"]
    matching = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("kernel_class") == kernel_class
        and record.get("dtype") == dtype
    ]
    if len(matching) != 1:
        raise ValueError(
            "seed_schedule must contain exactly one record for "
            f"{condition}/{kernel_class}/{dtype}; got {len(matching)}"
        )

    record = matching[0]
    kernel_name = _require_non_empty_str(record.get("kernel_name"), "kernel_name")
    prompt_sha256 = _require_sha256(record.get("prompt_sha256"), "prompt_sha256")
    model_id = _require_non_empty_str(record.get("model_id"), "model_id")
    model_revision = _optional_str(record.get("model_revision"))
    tokenizer_revision = _optional_str(record.get("tokenizer_revision"))
    temperature = _require_non_negative_number(record.get("temperature"), "temperature")
    max_new_tokens = _require_positive_int(record.get("max_new_tokens"), "max_new_tokens")
    base_seeds = _require_int_list(record.get("base_seeds"), "base_seeds")
    generation_seeds = _require_int_list(
        record.get("generation_seeds"),
        "generation_seeds",
    )
    attempt_indexes = _require_int_list(
        record.get("attempt_indexes"),
        "attempt_indexes",
    )
    generation_indexes = _require_int_list(
        record.get("generation_indexes"),
        "generation_indexes",
    )
    line_numbers = _require_positive_int_list(
        record.get("line_numbers"),
        "line_numbers",
    )
    replay_pair_ids = _require_str_list(
        record.get("replay_pair_ids"),
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
    if len(base_seeds) < candidate_count:
        raise ValueError(
            "seed_schedule coverage failure for "
            f"{condition}/{kernel_class}/{dtype}: required {candidate_count}, "
            f"observed {len(base_seeds)}"
        )

    expected_base_seeds = tuple(range(len(base_seeds)))
    if base_seeds != expected_base_seeds:
        raise ValueError(
            "seed_schedule base_seeds must be dense and zero-based: "
            f"expected {expected_base_seeds}, got {base_seeds}"
        )
    requested_window = tuple(range(candidate_count))
    if base_seeds[:candidate_count] != requested_window:
        raise ValueError(
            "seed_schedule must cover requested dense window: "
            f"expected {requested_window}, got {base_seeds[:candidate_count]}"
        )
    if generation_seeds != base_seeds:
        raise ValueError("seed_schedule generation_seeds must equal base_seeds")
    if generation_indexes != attempt_indexes:
        raise ValueError("seed_schedule generation_indexes must equal attempt_indexes")
    if len(set(replay_pair_ids)) != len(replay_pair_ids):
        raise ValueError("seed_schedule replay_pair_ids must be unique")
    return tuple(
        ReplaySeedScheduleEntry(
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
            line_number=line_numbers[index],
            replay_pair_id=replay_pair_ids[index],
        )
        for index in range(candidate_count)
    )


def _selected_artifact(
    condition: str,
    manifest: dict[str, Any],
    *,
    grammar_variant: str,
) -> dict[str, Any]:
    selected_ids = set(
        selected_replay_artifact_ids_for_condition(
            condition,
            manifest,
            grammar_variant=grammar_variant,
        )
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


def _validate_available_records_match_seed_schedule(
    row_records: Sequence[dict[str, Any]],
    seed_schedule: Sequence[ReplaySeedScheduleEntry],
) -> None:
    records_by_line: dict[int, dict[str, Any]] = {}
    for record in row_records:
        line_number = _optional_int(record.get("line_number"))
        if line_number is None:
            raise ValueError("selected row_record is missing line_number")
        if line_number in records_by_line:
            raise ValueError(f"duplicate row_record line_number {line_number}")
        records_by_line[line_number] = record
    for entry in seed_schedule:
        record = records_by_line.get(entry.line_number)
        if record is None:
            continue
        _validate_record_matches_seed_schedule(record, entry)


def _records_for_seed_schedule(
    row_records: Sequence[dict[str, Any]],
    seed_schedule: Sequence[ReplaySeedScheduleEntry],
) -> tuple[dict[str, Any], ...]:
    by_line: dict[int, dict[str, Any]] = {}
    for record in row_records:
        line_number = _optional_int(record.get("line_number"))
        if line_number is None:
            continue
        if line_number in by_line:
            raise ValueError(f"duplicate row_record line_number {line_number}")
        by_line[line_number] = record

    selected: list[dict[str, Any]] = []
    for entry in seed_schedule:
        record = by_line.get(entry.line_number)
        if record is None:
            raise ValueError(
                "seed_schedule line_number "
                f"{entry.line_number} missing matching row_record"
            )
        _validate_record_matches_seed_schedule(record, entry)
        selected.append(record)
    return tuple(selected)


def _validate_record_matches_seed_schedule(
    record: dict[str, Any],
    entry: ReplaySeedScheduleEntry,
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


def _candidate_from_record(
    record: dict[str, Any],
    *,
    schedule_entry: Any,
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
        base_seed=schedule_entry.base_seed,
        attempt_index=0,
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
        prompt_sha256=schedule_entry.prompt_sha256,
        temperature=schedule_entry.temperature,
        max_new_tokens=schedule_entry.max_new_tokens,
        replay_pair_id=schedule_entry.replay_pair_id,
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


def _require_positive_int_list(value: object, field_name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    return tuple(_require_positive_int(item, field_name) for item in value)


def _require_str_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    return tuple(_require_non_empty_str(item, field_name) for item in value)


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
