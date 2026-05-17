"""Phase 13 aggregation helpers for Cluster 2 result rows.

These helpers consume only ``Cluster2EvalRow``-compatible rows. They do not
adapt Cluster 1 generation rows, execute evaluation, or infer missing results.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cluster2.constants import (
    DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    GENERATED_SOURCE_CLASS,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
    REPLAY_CONTROL_SOURCE_CLASS,
    source_class_for_condition,
)
from cluster2.results.dataclass import (
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    FORBIDDEN_CLUSTER2_RESULT_FIELDS,
)
from shared.eval.content_hashes import collect_cluster1_frozen_generation_hashes


UNAVAILABLE_FROZEN_REVISION = "unavailable_in_frozen_cluster1_artifact"


@dataclass(frozen=True, order=True)
class CellKey:
    """Phase 13 cell identity including condition."""

    kernel_class: str
    dtype: str
    base_seed: int
    condition: str


@dataclass(frozen=True, order=True)
class MatchedCellKey:
    """Cell identity used to align treatment and control outcomes."""

    kernel_class: str
    dtype: str
    base_seed: int


@dataclass(frozen=True)
class AggregationDataset:
    """Rows plus their content-hash sidecar for hash-class validation."""

    rows: tuple[Cluster2EvalRow, ...]
    content_hash_sidecar: Cluster2ContentHashSidecar
    label: str = ""

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
        *,
        content_hash_sidecar: Cluster2ContentHashSidecar,
        label: str = "",
    ) -> "AggregationDataset":
        return cls(
            rows=coerce_cluster2_eval_rows(rows),
            content_hash_sidecar=content_hash_sidecar,
            label=label,
        )


def coerce_cluster2_eval_row(row: Cluster2EvalRow | Mapping[str, Any]) -> Cluster2EvalRow:
    """Return a strict Cluster 2 row or reject non-C2 result shapes."""

    if isinstance(row, Cluster2EvalRow):
        return row
    if isinstance(row, Mapping):
        return Cluster2EvalRow.from_dict(dict(row))
    raise TypeError("Phase 13 aggregation requires Cluster2EvalRow-compatible rows")


def coerce_cluster2_eval_rows(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> tuple[Cluster2EvalRow, ...]:
    """Return rows as a deterministic tuple of strict C2 rows."""

    return tuple(coerce_cluster2_eval_row(row) for row in rows)


def cell_key(row: Cluster2EvalRow) -> CellKey:
    """Return the explicit Phase 13 cell key for ``row``."""

    return CellKey(
        kernel_class=row.kernel_class,
        dtype=row.dtype,
        base_seed=row.base_seed,
        condition=row.condition,
    )


def matched_cell_key(row: Cluster2EvalRow) -> MatchedCellKey:
    """Return the condition-free cell key used for paired lift estimates."""

    return MatchedCellKey(
        kernel_class=row.kernel_class,
        dtype=row.dtype,
        base_seed=row.base_seed,
    )


def group_rows_by_cell(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> dict[CellKey, tuple[Cluster2EvalRow, ...]]:
    """Group rows by ``(kernel_class, dtype, base_seed, condition)``."""

    groups: dict[CellKey, list[Cluster2EvalRow]] = defaultdict(list)
    for row in coerce_cluster2_eval_rows(rows):
        groups[cell_key(row)].append(row)
    return {
        key: tuple(sorted(value, key=lambda item: item.attempt_index))
        for key, value in sorted(groups.items())
    }


def require_unique_attempt_indexes(
    key: CellKey,
    cell_rows: Sequence[Cluster2EvalRow],
) -> None:
    """Reject duplicate candidate attempt indexes within one cell."""

    seen: set[int] = set()
    duplicates: set[int] = set()
    for row in cell_rows:
        if row.attempt_index in seen:
            duplicates.add(row.attempt_index)
        seen.add(row.attempt_index)
    if duplicates:
        duplicate_text = ", ".join(str(index) for index in sorted(duplicates))
        raise ValueError(
            f"duplicate attempt_index values for cell {key}: {duplicate_text}"
        )


def require_source_class(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    source_class: str,
) -> tuple[Cluster2EvalRow, ...]:
    """Return rows after asserting every row belongs to ``source_class``."""

    row_tuple = coerce_cluster2_eval_rows(rows)
    if source_class not in {GENERATED_SOURCE_CLASS, REPLAY_CONTROL_SOURCE_CLASS}:
        raise ValueError(f"unsupported Cluster 2 source_class {source_class!r}")
    mismatched = sorted({row.source_class for row in row_tuple if row.source_class != source_class})
    if mismatched:
        raise ValueError(
            "source_class mismatch: expected "
            f"{source_class!r}, observed {', '.join(mismatched)}"
        )
    return row_tuple


def require_generated_rows(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> tuple[Cluster2EvalRow, ...]:
    """Return generated C2 rows or raise if replay controls are present."""

    row_tuple = require_source_class(rows, GENERATED_SOURCE_CLASS)
    invalid = sorted({row.condition for row in row_tuple if row.condition not in NEW_GENERATION_CONDITIONS})
    if invalid:
        raise ValueError(f"generated aggregation received invalid conditions: {', '.join(invalid)}")
    return row_tuple


def require_replay_control_rows(
    rows: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> tuple[Cluster2EvalRow, ...]:
    """Return replay-control rows or raise if generated rows are present."""

    row_tuple = require_source_class(rows, REPLAY_CONTROL_SOURCE_CLASS)
    invalid = sorted({row.condition for row in row_tuple if row.condition not in REPLAY_CONTROL_CONDITIONS})
    if invalid:
        raise ValueError(f"replay aggregation received invalid conditions: {', '.join(invalid)}")
    return row_tuple


def validate_paired_replay_alignment(
    rows_treatment: Iterable[Cluster2EvalRow | Mapping[str, Any]],
    rows_control: Iterable[Cluster2EvalRow | Mapping[str, Any]],
) -> None:
    """Reject generated/replay comparisons that are not paired by seed."""

    treatment = require_generated_rows(rows_treatment)
    control = require_replay_control_rows(rows_control)
    treatment_condition = _single_row_condition(treatment, "treatment")
    control_condition = _single_row_condition(control, "control")
    expected_control = {"C": "none", "G+C": "G"}[treatment_condition]
    if control_condition != expected_control:
        raise ValueError(
            f"condition {treatment_condition!r} must pair with replay "
            f"{expected_control!r}; got {control_condition!r}"
        )

    treatment_by_cell = _generated_rows_by_matched_cell(treatment)
    control_by_cell = _single_replay_rows_by_matched_cell(control)
    if set(treatment_by_cell) != set(control_by_cell):
        missing_control = sorted(set(treatment_by_cell) - set(control_by_cell))
        missing_treatment = sorted(set(control_by_cell) - set(treatment_by_cell))
        raise ValueError(
            "missing replay pair for paired-by-seed comparison: "
            f"missing_control={missing_control}, "
            f"missing_treatment={missing_treatment}"
        )

    for key in sorted(treatment_by_cell):
        control_row = control_by_cell[key]
        _validate_control_pair_metadata(control_row, key)
        for generated in treatment_by_cell[key]:
            _validate_generated_pair_metadata(
                generated,
                control_row,
                expected_control_condition=expected_control,
            )


def validate_hash_classes(
    datasets: Iterable[AggregationDataset],
    *,
    frozen_cluster1_manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
) -> None:
    """Validate Phase 13 hash semantics across compared datasets.

    Eval-pipeline hashes must match across all datasets. Generation hashes are
    validated only within their source class: generated rows against C2
    generation sidecar entries, and replay rows against frozen Cluster 1
    manifest hashes. Replay rows are not compared to generated-row generation
    hashes.
    """

    dataset_tuple = tuple(datasets)
    if not dataset_tuple:
        raise ValueError("at least one aggregation dataset is required")

    first_eval_hashes = dataset_tuple[0].content_hash_sidecar.eval_pipeline_hashes
    generated_hashes_by_condition: dict[str, dict[str, str]] = {}
    required_g_replay_artifact_id = _required_g_replay_artifact_id_for_comparison(
        dataset_tuple,
        frozen_cluster1_manifest_path=frozen_cluster1_manifest_path,
    )
    for dataset in dataset_tuple:
        sidecar = dataset.content_hash_sidecar
        if sidecar.eval_pipeline_hashes != first_eval_hashes:
            label = f" for {dataset.label}" if dataset.label else ""
            raise ValueError(f"eval pipeline hash mismatch{label}")
        dataset_generated_hashes = _validate_dataset_hash_classes(
            dataset,
            frozen_cluster1_manifest_path=frozen_cluster1_manifest_path,
            required_g_replay_artifact_id=required_g_replay_artifact_id,
        )
        for condition, observed in dataset_generated_hashes.items():
            prior = generated_hashes_by_condition.setdefault(condition, observed)
            if prior != observed:
                raise ValueError(
                    "generated hash mismatch across datasets for condition "
                    f"{condition!r}"
                )


def _validate_dataset_hash_classes(
    dataset: AggregationDataset,
    *,
    frozen_cluster1_manifest_path: str | Path,
    required_g_replay_artifact_id: str | None,
) -> dict[str, dict[str, str]]:
    sidecar = dataset.content_hash_sidecar
    generated_seen: dict[str, dict[str, str]] = {}
    replay_seen: dict[str, dict[str, str]] = {}
    replay_manifest: dict[str, Any] | None = None
    replay_hashes_by_condition: dict[str, dict[str, str]] = {}

    for row in dataset.rows:
        expected_source_class = source_class_for_condition(row.condition)
        if row.source_class != expected_source_class:
            raise ValueError(
                f"condition {row.condition!r} requires source_class "
                f"{expected_source_class!r}"
            )

        if row.source_class == GENERATED_SOURCE_CLASS:
            if row.generated_metadata is None:
                raise ValueError("generated row is missing generated_metadata")
            expected = sidecar.generated_condition_hashes.get(row.condition)
            if expected is None:
                raise ValueError(
                    f"missing generated_condition_hashes for {row.condition!r}"
                )
            observed = row.generated_metadata.c2_generation_hashes
            if observed != expected:
                raise ValueError("generated row uses hashes outside C2 generation class")
            prior = generated_seen.setdefault(row.condition, observed)
            if prior != observed:
                raise ValueError(
                    f"generated hash mismatch within condition {row.condition!r}"
                )
            continue

        if row.source_class == REPLAY_CONTROL_SOURCE_CLASS:
            if row.replay_metadata is None:
                raise ValueError("replay row is missing replay_metadata")
            expected = sidecar.replay_control_hashes.get(row.condition)
            if expected is None:
                raise ValueError(f"missing replay_control_hashes for {row.condition!r}")
            manifest_expected = replay_hashes_by_condition.setdefault(
                row.condition,
                collect_cluster1_frozen_generation_hashes(
                    row.condition,
                    str(frozen_cluster1_manifest_path),
                ),
            )
            observed = row.replay_metadata.frozen_cluster1_generation_hashes
            if expected != manifest_expected or observed != manifest_expected:
                raise ValueError("frozen replay hash mismatch against Phase -1 manifest")
            if replay_manifest is None:
                replay_manifest = _load_frozen_replay_manifest(
                    frozen_cluster1_manifest_path
                )
            _validate_replay_row_manifest_membership(
                row,
                replay_manifest,
                required_g_replay_artifact_id=required_g_replay_artifact_id,
            )
            prior = replay_seen.setdefault(row.condition, observed)
            if prior != observed:
                raise ValueError(
                    f"replay hash mismatch within condition {row.condition!r}"
                )
            continue

        raise ValueError(f"unsupported Cluster 2 source_class {row.source_class!r}")

    return generated_seen


def _required_g_replay_artifact_id_for_comparison(
    datasets: Sequence[AggregationDataset],
    *,
    frozen_cluster1_manifest_path: str | Path,
) -> str | None:
    if not _contains_primary_task_agnostic_gc_rows(datasets):
        return None

    manifest = _load_frozen_replay_manifest(frozen_cluster1_manifest_path)
    artifact_id = _selected_task_agnostic_g_artifact_id(manifest)
    if artifact_id is None:
        raise ValueError(
            "primary task_agnostic G+C comparison requires a task-agnostic "
            "G replay artifact in the Phase -1 manifest"
        )
    return artifact_id


def _contains_primary_task_agnostic_gc_rows(
    datasets: Sequence[AggregationDataset],
) -> bool:
    for dataset in datasets:
        for row in dataset.rows:
            if row.condition != "G+C" or row.source_class != GENERATED_SOURCE_CLASS:
                continue
            if row.generated_metadata is None:
                raise ValueError("generated row is missing generated_metadata")
            if (
                row.generated_metadata.grammar_variant == "task_agnostic"
                and row.generated_metadata.grammar_claim_scope == "primary"
            ):
                return True
    return False


def _load_frozen_replay_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("frozen replay manifest must be a JSON object")
    return payload


def _validate_replay_row_manifest_membership(
    row: Cluster2EvalRow,
    manifest: Mapping[str, Any],
    *,
    required_g_replay_artifact_id: str | None = None,
) -> None:
    if row.replay_metadata is None:
        raise ValueError("replay row is missing replay_metadata")
    artifact_id = row.replay_metadata.frozen_cluster1_artifact_id
    if (
        row.condition == "G"
        and required_g_replay_artifact_id is not None
        and artifact_id != required_g_replay_artifact_id
    ):
        raise ValueError(
            "primary task_agnostic G+C comparison requires task-agnostic "
            f"G replay artifact {required_g_replay_artifact_id!r}; "
            f"got {artifact_id!r}"
        )

    artifact = _manifest_artifact_for_replay_row(row, manifest)
    row_records = artifact.get("row_records", [])
    if not isinstance(row_records, list):
        raise ValueError("frozen replay manifest artifact row_records must be a list")

    for record in row_records:
        if not isinstance(record, Mapping):
            continue
        if _replay_manifest_record_matches_row(row, record):
            return

    raise ValueError("replay row source/row hash missing from Phase -1 manifest")


def _manifest_artifact_for_replay_row(
    row: Cluster2EvalRow,
    manifest: Mapping[str, Any],
) -> Mapping[str, Any]:
    assert row.replay_metadata is not None
    artifact_id = row.replay_metadata.frozen_cluster1_artifact_id
    selected_ids = _selected_replay_artifact_ids(manifest)
    if artifact_id not in selected_ids:
        raise ValueError(
            f"replay artifact {artifact_id!r} is not a selected Phase -1 control"
        )
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("frozen replay manifest artifacts must be a list")
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        if artifact.get("artifact_id") != artifact_id:
            continue
        if artifact.get("condition") != row.condition:
            raise ValueError("replay row artifact condition mismatch")
        return artifact
    raise ValueError(f"replay artifact {artifact_id!r} missing from Phase -1 manifest")


def _selected_replay_artifact_ids(
    manifest: Mapping[str, Any],
) -> frozenset[str]:
    selected_ids = set(_selected_template_replay_artifact_ids(manifest))
    task_agnostic_g_artifact_id = _selected_task_agnostic_g_artifact_id(manifest)
    if task_agnostic_g_artifact_id is not None:
        selected_ids.add(task_agnostic_g_artifact_id)
    return frozenset(selected_ids)


def _selected_template_replay_artifact_ids(
    manifest: Mapping[str, Any],
) -> frozenset[str]:
    selected = manifest.get("selected_controls", {})
    if not isinstance(selected, Mapping):
        raise ValueError("frozen replay manifest selected_controls must be an object")
    template_controls = selected.get("cluster2_v5_template_upper_bound_controls", {})
    if not isinstance(template_controls, Mapping):
        raise ValueError(
            "frozen replay manifest template controls must be an object"
        )
    artifact_ids = template_controls.get("artifact_ids", [])
    if (
        not isinstance(artifact_ids, list)
        or not artifact_ids
        or not all(isinstance(item, str) and item for item in artifact_ids)
    ):
        raise ValueError(
            "selected Phase -1 replay artifact_ids must be non-empty strings"
        )
    return frozenset(artifact_ids)


def _selected_task_agnostic_g_artifact_id(
    manifest: Mapping[str, Any],
) -> str | None:
    selected = manifest.get("selected_controls", {})
    if not isinstance(selected, Mapping):
        raise ValueError("frozen replay manifest selected_controls must be an object")
    status = selected.get("task_agnostic_g_status")
    if status is None:
        return None
    if not isinstance(status, Mapping):
        raise ValueError("frozen replay manifest task-agnostic G status must be an object")
    artifact_id = status.get("available_development_artifact_id")
    if artifact_id is None:
        return None
    if not isinstance(artifact_id, str) or not artifact_id:
        raise ValueError("task-agnostic G replay artifact id must be a non-empty string")
    return artifact_id


def _replay_manifest_record_matches_row(
    row: Cluster2EvalRow,
    record: Mapping[str, Any],
) -> bool:
    assert row.replay_metadata is not None
    expected_fields = {
        "condition": row.condition,
        "kernel_class": row.kernel_class,
        "kernel_name": row.kernel_name,
        "dtype": row.dtype,
        "source_sha256": row.replay_metadata.frozen_cluster1_source_hash,
    }
    for field_name, expected in expected_fields.items():
        if record.get(field_name) != expected:
            return False

    row_hash = row.replay_metadata.frozen_cluster1_row_hash
    if row_hash is not None and record.get("row_sha256") != row_hash:
        return False

    pairing_fields = {
        "base_seed": row.replay_metadata.replay_base_seed,
        "generation_seed": row.replay_metadata.replay_generation_seed,
        "prompt_sha256": row.replay_metadata.prompt_sha256,
        "model_id": row.replay_metadata.model_id,
        "model_revision": row.replay_metadata.model_revision,
        "tokenizer_revision": row.replay_metadata.tokenizer_revision,
        "temperature": row.replay_metadata.temperature,
        "max_new_tokens": row.replay_metadata.max_new_tokens,
        "replay_pair_id": row.replay_metadata.replay_pair_id,
    }
    for field_name, expected in pairing_fields.items():
        if expected is None:
            continue
        if field_name not in record:
            return False
        if record.get(field_name) != expected:
            return False
    return True


def _single_row_condition(rows: Sequence[Cluster2EvalRow], label: str) -> str:
    conditions = sorted({row.condition for row in rows})
    if len(conditions) != 1:
        raise ValueError(f"{label} rows must contain exactly one condition")
    return conditions[0]


def _generated_rows_by_matched_cell(
    rows: Sequence[Cluster2EvalRow],
) -> dict[MatchedCellKey, tuple[Cluster2EvalRow, ...]]:
    grouped: dict[MatchedCellKey, list[Cluster2EvalRow]] = defaultdict(list)
    for row in rows:
        grouped[matched_cell_key(row)].append(row)
    result: dict[MatchedCellKey, tuple[Cluster2EvalRow, ...]] = {}
    for key, cell_rows in grouped.items():
        attempt_indexes: set[int] = set()
        duplicates: set[int] = set()
        for row in cell_rows:
            if row.attempt_index in attempt_indexes:
                duplicates.add(row.attempt_index)
            attempt_indexes.add(row.attempt_index)
        if duplicates:
            duplicate_text = ", ".join(str(index) for index in sorted(duplicates))
            raise ValueError(f"duplicate pair attempt_index values for {key}: {duplicate_text}")
        if 0 not in attempt_indexes:
            raise ValueError(f"missing generated attempt 0 for replay pair {key}")
        result[key] = tuple(sorted(cell_rows, key=lambda row: row.attempt_index))
    return result


def _single_replay_rows_by_matched_cell(
    rows: Sequence[Cluster2EvalRow],
) -> dict[MatchedCellKey, Cluster2EvalRow]:
    result: dict[MatchedCellKey, Cluster2EvalRow] = {}
    for row in rows:
        key = matched_cell_key(row)
        if key in result:
            raise ValueError(f"duplicate replay pair for {key}")
        if row.attempt_index != 0:
            raise ValueError(
                f"replay pair {key} must use attempt_index 0; "
                f"got {row.attempt_index}"
            )
        result[key] = row
    return result


def _validate_control_pair_metadata(
    row: Cluster2EvalRow,
    key: MatchedCellKey,
) -> None:
    metadata = row.replay_metadata
    if metadata is None:
        raise ValueError("replay row is missing replay_metadata")
    missing = [
        field
        for field in (
            "replay_pair_id",
            "replay_base_seed",
            "replay_generation_seed",
            "prompt_sha256",
            "model_id",
            "temperature",
            "max_new_tokens",
        )
        if getattr(metadata, field) is None
    ]
    if missing:
        raise ValueError(
            "replay row is missing paired seed metadata: "
            + ", ".join(missing)
        )
    if metadata.replay_base_seed != key.base_seed:
        raise ValueError("replay metadata base_seed mismatch")
    if metadata.replay_generation_seed != key.base_seed:
        raise ValueError("replay metadata generation_seed mismatch")


def _validate_generated_pair_metadata(
    row: Cluster2EvalRow,
    control_row: Cluster2EvalRow,
    *,
    expected_control_condition: str,
) -> None:
    generated = row.generated_metadata
    replay = control_row.replay_metadata
    if generated is None or replay is None:
        raise ValueError("paired comparison requires generated and replay metadata")
    missing = [
        field
        for field in (
            "replay_pair_id",
            "replay_control_condition",
            "replay_base_seed",
            "replay_generation_seed",
            "prompt_sha256",
            "model_id",
            "temperature",
            "max_new_tokens",
        )
        if getattr(generated, field) is None
    ]
    if missing:
        raise ValueError(
            "generated row is missing paired seed metadata: "
            + ", ".join(missing)
        )
    expected = {
        "replay_pair_id": replay.replay_pair_id,
        "replay_control_condition": expected_control_condition,
        "replay_base_seed": replay.replay_base_seed,
        "replay_generation_seed": replay.replay_generation_seed,
        "prompt_sha256": replay.prompt_sha256,
        "model_id": replay.model_id,
        "temperature": replay.temperature,
    }
    # Fresh generated rows may use a larger token budget than historical replay
    # controls. Keep max_new_tokens as per-side provenance, not pair identity.
    if _known_frozen_revision(replay.model_revision):
        expected["model_revision"] = replay.model_revision
    if _known_frozen_revision(replay.tokenizer_revision):
        expected["tokenizer_revision"] = replay.tokenizer_revision
    mismatches = [
        f"{field}: expected {expected_value!r}, got {getattr(generated, field)!r}"
        for field, expected_value in expected.items()
        if getattr(generated, field) != expected_value
    ]
    if mismatches:
        raise ValueError("metadata mismatch for replay pair: " + "; ".join(mismatches))
    if row.attempt_index == 0 and generated.generation_seed != replay.replay_generation_seed:
        raise ValueError("initial generated seed does not match replay seed")


def _known_frozen_revision(value: str | None) -> bool:
    return value is not None and value != UNAVAILABLE_FROZEN_REVISION


def sorted_cell_keys(rows: Iterable[Cluster2EvalRow | Mapping[str, Any]]) -> tuple[CellKey, ...]:
    """Return deterministic unique cell keys represented by ``rows``."""

    return tuple(sorted(group_rows_by_cell(rows)))


def assert_no_forbidden_metric_fields(mapping: Mapping[str, Any]) -> None:
    """Reject Phase 13 outputs that add forbidden performance/accounting fields."""

    keys = _recursive_keys(mapping)
    overlap = sorted(key for key in keys if key in FORBIDDEN_CLUSTER2_RESULT_FIELDS)
    if overlap:
        raise ValueError(f"forbidden Phase 13 fields: {', '.join(overlap)}")


def _recursive_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = set(value)
        for nested in value.values():
            keys.update(_recursive_keys(nested))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        keys: set[str] = set()
        for item in value:
            keys.update(_recursive_keys(item))
        return keys
    return set()
