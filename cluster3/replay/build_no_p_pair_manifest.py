"""Build Cluster 3 no-P control manifests from fixture or artifact metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cluster2.constants import DEFAULT_FROZEN_CLUSTER1_MANIFEST
from cluster3.replay.no_p_pairs import NO_P_PAIR_MANIFEST_SCHEMA_VERSION


MANIFEST_DESCRIPTION = (
    "Cluster 3 no-P control manifest for P vs none, G+P vs G, C+P vs C, "
    "and G+C+P vs G+C pair validation."
)
CLUSTER1_CONTROL_CONDITIONS = ("none", "G")
CLUSTER2_CONTROL_CONDITIONS = ("C", "G+C")
ENTRY_FIELD_ORDER = (
    "artifact_id",
    "artifact_path",
    "condition",
    "grammar_variant",
    "kernel_class",
    "kernel_name",
    "dtype",
    "base_seed",
    "generation_seed",
    "sample_index",
    "sample_index_source",
    "replay_pair_id",
    "source_sha256",
    "prompt_sha256",
    "model_id",
    "model_revision",
    "tokenizer_revision",
    "temperature",
    "max_new_tokens",
    "scale_tier",
    "compile_success",
    "functional_success",
    "failure_code",
    "row_index",
    "row_schema_version",
)
_PROMPT_HASH_FIELDS = (
    "prompt_sha256",
    "prompt_sha",
    "prompt_hash",
    "base_prompt_sha256",
)
_SOURCE_HASH_FIELDS = (
    "source_sha256",
    "source_hash",
    "terminal_source_hash",
)
_NESTED_FIELD_CONTAINERS = (
    "generated_metadata",
    "replay_metadata",
    "metadata",
    "identity",
    "generation_identity",
    "source_identity",
    "eval_identity",
)


def build_no_p_pair_manifest(
    *,
    cluster1_frozen_manifest: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    cluster2_outputs: Sequence[str | Path] = (),
    allow_missing_cluster2_outputs: bool = False,
    built_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a no-P pair manifest from frozen Cluster 1 and Cluster 2 rows."""

    cluster1_path = Path(cluster1_frozen_manifest)
    cluster2_paths = tuple(Path(path) for path in cluster2_outputs)
    if not cluster2_paths and not allow_missing_cluster2_outputs:
        raise ValueError(
            "at least one --cluster2-outputs path is required unless "
            "--allow-missing-cluster2-outputs is set"
        )

    metadata = _initial_build_metadata(
        cluster1_path=cluster1_path,
        cluster2_paths=cluster2_paths,
        built_at_utc=built_at_utc,
    )
    entries: list[dict[str, Any]] = []

    cluster1_payload = json.loads(cluster1_path.read_text(encoding="utf-8"))
    for row_context in _iter_cluster1_manifest_rows(cluster1_payload, cluster1_path):
        metadata["row_counts"]["cluster1_frozen_manifest"] += 1
        entry = _entry_from_row_context(
            row_context,
            source_kind="cluster1_frozen_manifest",
            metadata=metadata,
        )
        if entry is not None:
            entries.append(entry)

    for cluster2_path in cluster2_paths:
        path_key = str(cluster2_path)
        metadata["row_counts"]["cluster2_outputs"][path_key] = 0
        if not cluster2_path.is_file():
            if allow_missing_cluster2_outputs:
                metadata["missing_input_paths"].append(path_key)
                continue
            raise FileNotFoundError(path_key)
        for row_index, row in _read_jsonl_rows(cluster2_path):
            metadata["row_counts"]["cluster2_outputs"][path_key] += 1
            if not isinstance(row, Mapping):
                _reject(metadata, path_key, row_index, "row_not_object", row)
                continue
            row_context = {
                "row": row,
                "row_index": row_index,
                "artifact_id": _artifact_id_for_cluster2_row(row, cluster2_path),
                "artifact_path": str(cluster2_path),
                "condition": _find_field(row, "condition"),
                "grammar_variant": _find_field(row, "grammar_variant"),
                "input_path": path_key,
            }
            entry = _entry_from_row_context(
                row_context,
                source_kind="cluster2_jsonl",
                metadata=metadata,
            )
            if entry is not None:
                entries.append(entry)

    entries = sorted(entries, key=_entry_sort_key)
    _reject_duplicate_entry_keys(entries)
    metadata["row_counts"]["total_input_rows"] = (
        metadata["row_counts"]["cluster1_frozen_manifest"]
        + sum(metadata["row_counts"]["cluster2_outputs"].values())
    )
    metadata["row_counts"]["accepted_entries"] = len(entries)
    metadata["rejected_row_counts"]["total"] = sum(
        count
        for source, count in metadata["rejected_row_counts"].items()
        if source != "total"
    )
    metadata["rejection_reasons"] = dict(sorted(metadata["rejection_reasons"].items()))

    return {
        "schema_version": NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
        "description": MANIFEST_DESCRIPTION,
        "entries": entries,
        "build_metadata": metadata,
    }


def write_no_p_pair_manifest(
    manifest: Mapping[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a no-P pair manifest without allowing writes under outputs/."""

    output_path = Path(output)
    _reject_output_path_under_outputs(output_path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"output manifest already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the fixture-friendly manifest-builder CLI parser."""

    parser = argparse.ArgumentParser(
        prog="build_no_p_pair_manifest",
        description="Build Cluster 3 no-P control manifest JSON.",
    )
    parser.add_argument(
        "--cluster1-frozen-manifest",
        default=DEFAULT_FROZEN_CLUSTER1_MANIFEST,
        help="Read-only Cluster 1 frozen manifest path.",
    )
    parser.add_argument(
        "--cluster2-outputs",
        nargs="*",
        default=(),
        metavar="PATH",
        help="Cluster 2 C/G+C JSONL output paths to read.",
    )
    parser.add_argument("--output", required=True, help="Manifest path to write.")
    parser.add_argument(
        "--allow-missing-cluster2-outputs",
        action="store_true",
        help="Skip missing Cluster 2 JSONL paths and permit schema-only C2 input.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing output manifest.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        manifest = build_no_p_pair_manifest(
            cluster1_frozen_manifest=args.cluster1_frozen_manifest,
            cluster2_outputs=args.cluster2_outputs,
            allow_missing_cluster2_outputs=args.allow_missing_cluster2_outputs,
        )
        write_no_p_pair_manifest(
            manifest,
            args.output,
            overwrite=args.overwrite,
        )
    except (FileExistsError, FileNotFoundError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    return 0


def _initial_build_metadata(
    *,
    cluster1_path: Path,
    cluster2_paths: tuple[Path, ...],
    built_at_utc: str | None,
) -> dict[str, Any]:
    return {
        "built_at_utc": built_at_utc or datetime.now(timezone.utc).isoformat(),
        "input_paths": {
            "cluster1_frozen_manifest": str(cluster1_path),
            "cluster2_outputs": [str(path) for path in cluster2_paths],
        },
        "row_counts": {
            "cluster1_frozen_manifest": 0,
            "cluster2_outputs": {},
            "total_input_rows": 0,
            "accepted_entries": 0,
        },
        "rejected_row_counts": {},
        "rejection_reasons": Counter(),
        "rejections": [],
        "missing_input_paths": [],
    }


def _iter_cluster1_manifest_rows(
    manifest: Mapping[str, Any],
    manifest_path: Path,
) -> Iterable[dict[str, Any]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("Cluster 1 frozen manifest artifacts must be a list")
    selected = _selected_cluster1_artifact_ids(manifest)
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        condition = artifact.get("condition")
        if condition not in CLUSTER1_CONTROL_CONDITIONS:
            continue
        selected_ids = selected.get(str(condition), ())
        artifact_id = _required_str(artifact.get("artifact_id"), "artifact_id")
        if selected_ids and artifact_id not in selected_ids:
            continue
        row_records = artifact.get("row_records", [])
        if not isinstance(row_records, list):
            raise ValueError(f"{artifact_id} row_records must be a list")
        default_grammar_variant = _artifact_grammar_variant(artifact)
        artifact_path = str(artifact.get("path") or manifest_path)
        for fallback_index, row in enumerate(row_records):
            if not isinstance(row, Mapping):
                yield {
                    "row": row,
                    "row_index": fallback_index,
                    "artifact_id": artifact_id,
                    "artifact_path": artifact_path,
                    "condition": condition,
                    "grammar_variant": default_grammar_variant,
                    "input_path": str(manifest_path),
                }
                continue
            row_index = _row_index(row, fallback_index)
            yield {
                "row": row,
                "row_index": row_index,
                "artifact_id": artifact_id,
                "artifact_path": artifact_path,
                "condition": row.get("condition", condition),
                "grammar_variant": row.get("grammar_variant", default_grammar_variant),
                "input_path": str(manifest_path),
            }


def _selected_cluster1_artifact_ids(
    manifest: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    try:
        from cluster2.replay.manifest import (  # pylint: disable=import-outside-toplevel
            selected_replay_artifact_ids_for_condition,
        )

        return {
            "none": tuple(
                selected_replay_artifact_ids_for_condition(
                    "none",
                    dict(manifest),
                    grammar_variant="template_upper_bound",
                )
            ),
            "G": tuple(
                selected_replay_artifact_ids_for_condition(
                    "G",
                    dict(manifest),
                    grammar_variant="task_agnostic",
                )
            ),
        }
    except (KeyError, TypeError, ValueError):
        return _fallback_selected_cluster1_artifact_ids(manifest)


def _fallback_selected_cluster1_artifact_ids(
    manifest: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    artifacts = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, Mapping)
    ]
    selected: dict[str, tuple[str, ...]] = {}
    for condition in CLUSTER1_CONTROL_CONDITIONS:
        candidates = [
            _required_str(artifact.get("artifact_id"), "artifact_id")
            for artifact in artifacts
            if artifact.get("condition") == condition
        ]
        if condition == "G":
            task_agnostic = [
                _required_str(artifact.get("artifact_id"), "artifact_id")
                for artifact in artifacts
                if artifact.get("condition") == "G"
                and _artifact_grammar_variant(artifact) == "task_agnostic"
            ]
            if task_agnostic:
                candidates = task_agnostic
        selected[condition] = tuple(candidates)
    return selected


def _entry_from_row_context(
    context: Mapping[str, Any],
    *,
    source_kind: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    row = context["row"]
    row_index = int(context["row_index"])
    input_path = str(context["input_path"])
    if not isinstance(row, Mapping):
        _reject(metadata, input_path, row_index, "row_not_object", row)
        return None

    try:
        condition = _optional_str(_find_field(row, "condition")) or _optional_str(
            context.get("condition")
        )
    except (TypeError, ValueError) as exc:
        _reject(metadata, input_path, row_index, f"invalid_condition:{exc}", row)
        return None
    if condition is None:
        _reject(metadata, input_path, row_index, "missing_condition", row)
        return None
    if source_kind == "cluster1_frozen_manifest" and condition not in CLUSTER1_CONTROL_CONDITIONS:
        _reject(metadata, input_path, row_index, "unexpected_cluster1_condition", row)
        return None
    if source_kind == "cluster2_jsonl" and condition not in CLUSTER2_CONTROL_CONDITIONS:
        _reject(metadata, input_path, row_index, "unexpected_cluster2_condition", row)
        return None

    sample_index, sample_index_source, sample_reason = _derive_sample_index(
        row,
        source_kind=source_kind,
    )
    if sample_index_source == "missing":
        _reject(metadata, input_path, row_index, sample_reason, row)
        return None

    try:
        source_hash = _source_sha256(row)
        prompt_hash = _prompt_sha256(row)
        entry = {
            "artifact_id": _optional_str(_find_field(row, "artifact_id"))
            or _required_str(context.get("artifact_id"), "artifact_id"),
            "artifact_path": _required_str(context.get("artifact_path"), "artifact_path"),
            "condition": condition,
            "grammar_variant": _optional_str(_find_field(row, "grammar_variant"))
            if _find_field(row, "grammar_variant") is not None
            else _optional_str(context.get("grammar_variant")),
            "kernel_class": _find_field(row, "kernel_class"),
            "kernel_name": _find_field(row, "kernel_name"),
            "dtype": _find_field(row, "dtype"),
            "base_seed": _find_field(row, "base_seed"),
            "generation_seed": _find_field(row, "generation_seed"),
            "sample_index": sample_index,
            "sample_index_source": sample_index_source,
            "replay_pair_id": _optional_str(_find_field(row, "replay_pair_id")),
            "source_sha256": source_hash,
            "prompt_sha256": prompt_hash,
            "model_id": _find_field(row, "model_id"),
            "model_revision": _find_field(row, "model_revision"),
            "tokenizer_revision": _find_field(row, "tokenizer_revision"),
            "temperature": _find_field(row, "temperature"),
            "max_new_tokens": _find_field(row, "max_new_tokens"),
            "scale_tier": _optional_str(_find_field(row, "scale_tier")),
            "compile_success": _optional_bool(_find_field(row, "compile_success")),
            "functional_success": _optional_bool(_find_field(row, "functional_success")),
            "failure_code": _optional_str(_find_field(row, "failure_code")),
            "row_index": row_index,
            "row_schema_version": _first_present(
                row,
                ("row_schema_version", "schema_version", "results_schema_version"),
            ),
        }
    except (TypeError, ValueError) as exc:
        _reject(metadata, input_path, row_index, f"invalid_entry:{exc}", row)
        return None
    missing_required = [
        field_name
        for field_name in (
            "kernel_class",
            "kernel_name",
            "dtype",
            "base_seed",
            "generation_seed",
            "source_sha256",
            "prompt_sha256",
            "model_id",
            "model_revision",
            "tokenizer_revision",
            "temperature",
            "max_new_tokens",
        )
        if entry[field_name] is None
    ]
    if missing_required:
        _reject(
            metadata,
            input_path,
            row_index,
            f"missing_required_fields:{','.join(missing_required)}",
            row,
        )
        return None
    try:
        return _normalize_entry(entry)
    except (TypeError, ValueError) as exc:
        _reject(metadata, input_path, row_index, f"invalid_entry:{exc}", row)
        return None


def _normalize_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {
        "artifact_id": _required_str(entry["artifact_id"], "artifact_id"),
        "artifact_path": _required_str(entry["artifact_path"], "artifact_path"),
        "condition": _required_str(entry["condition"], "condition"),
        "grammar_variant": _optional_str(entry["grammar_variant"]),
        "kernel_class": _required_str(entry["kernel_class"], "kernel_class"),
        "kernel_name": _required_str(entry["kernel_name"], "kernel_name"),
        "dtype": _required_str(entry["dtype"], "dtype"),
        "base_seed": _require_non_negative_int(entry["base_seed"], "base_seed"),
        "generation_seed": _require_non_negative_int(
            entry["generation_seed"],
            "generation_seed",
        ),
        "sample_index": _require_non_negative_int(
            entry["sample_index"],
            "sample_index",
        ),
        "sample_index_source": _required_str(
            entry["sample_index_source"],
            "sample_index_source",
        ),
        "replay_pair_id": _optional_str(entry["replay_pair_id"]),
        "source_sha256": _require_sha256(entry["source_sha256"], "source_sha256"),
        "prompt_sha256": _require_sha256(entry["prompt_sha256"], "prompt_sha256"),
        "model_id": _required_str(entry["model_id"], "model_id"),
        "model_revision": _required_str(entry["model_revision"], "model_revision"),
        "tokenizer_revision": _required_str(
            entry["tokenizer_revision"],
            "tokenizer_revision",
        ),
        "temperature": _require_non_negative_number(
            entry["temperature"],
            "temperature",
        ),
        "max_new_tokens": _require_positive_int(
            entry["max_new_tokens"],
            "max_new_tokens",
        ),
        "scale_tier": _optional_str(entry["scale_tier"]),
        "compile_success": _optional_bool(entry["compile_success"]),
        "functional_success": _optional_bool(entry["functional_success"]),
        "failure_code": _optional_str(entry["failure_code"]),
        "row_index": _require_non_negative_int(entry["row_index"], "row_index"),
        "row_schema_version": entry["row_schema_version"],
    }
    return {field_name: normalized[field_name] for field_name in ENTRY_FIELD_ORDER}


def _derive_sample_index(
    row: Mapping[str, Any],
    *,
    source_kind: str,
) -> tuple[int | None, str, str]:
    sample_index = _find_field(row, "sample_index")
    if sample_index is not None:
        if _is_non_negative_int(sample_index):
            return int(sample_index), "row_sample_index", "ok"
        return None, "missing", "invalid_sample_index"

    base_seed = _find_field(row, "base_seed")
    if _base_seed_derivation_proven(row, source_kind=source_kind):
        if _is_non_negative_int(base_seed):
            return int(base_seed), "base_seed_derived", "ok"
        return None, "missing", "invalid_base_seed_for_sample_index"

    attempt_index = _find_field(row, "attempt_index")
    if _attempt_index_derivation_proven(row):
        if _is_non_negative_int(attempt_index):
            return int(attempt_index), "attempt_index_derived", "ok"
        return None, "missing", "invalid_attempt_index_for_sample_index"

    return None, "missing", "missing_sample_index_identity"


def _base_seed_derivation_proven(
    row: Mapping[str, Any],
    *,
    source_kind: str,
) -> bool:
    if source_kind == "cluster1_frozen_manifest":
        base_seed = _find_field(row, "base_seed")
        generation_seed = _find_field(row, "generation_seed")
        return _is_non_negative_int(base_seed) and base_seed == generation_seed
    if _truthy_field(row, "base_seed_is_sample_identity"):
        return True
    if _truthy_field(row, "base_seed_equals_sample_identity"):
        return True
    if _find_field(row, "sample_index_derivation") == "base_seed":
        return True
    return _find_field(row, "sample_index_source") == "base_seed_derived"


def _attempt_index_derivation_proven(row: Mapping[str, Any]) -> bool:
    if _truthy_field(row, "attempt_index_is_sample_identity"):
        return True
    if _find_field(row, "sample_index_derivation") == "attempt_index":
        return True
    return _find_field(row, "sample_index_source") == "attempt_index_derived"


def _read_jsonl_rows(path: Path) -> Iterable[tuple[int, Any]]:
    for row_index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        yield row_index, json.loads(line)


def _artifact_id_for_cluster2_row(row: Mapping[str, Any], path: Path) -> str:
    artifact_id = _find_field(row, "artifact_id")
    if isinstance(artifact_id, str) and artifact_id:
        return artifact_id
    return path.stem


def _artifact_grammar_variant(artifact: Mapping[str, Any]) -> str | None:
    condition_check = artifact.get("condition_flag_check")
    if not isinstance(condition_check, Mapping):
        return None
    variant = condition_check.get("expected_grammar_variant")
    return variant if isinstance(variant, str) and variant else None


def _row_index(row: Mapping[str, Any], fallback_index: int) -> int:
    row_index = row.get("row_index")
    if _is_non_negative_int(row_index):
        return int(row_index)
    line_number = row.get("line_number")
    if _is_non_negative_int(line_number) and int(line_number) > 0:
        return int(line_number) - 1
    return fallback_index


def _source_sha256(row: Mapping[str, Any]) -> str | None:
    declared = _first_present(row, _SOURCE_HASH_FIELDS)
    source = _find_field(row, "source")
    if declared is None and isinstance(source, str):
        return _sha256_text(source)
    if declared is not None and isinstance(source, str):
        observed = _sha256_text(source)
        if observed != declared:
            raise ValueError("declared source hash does not match source text")
    return declared if isinstance(declared, str) else None


def _prompt_sha256(row: Mapping[str, Any]) -> str | None:
    declared = _first_present(row, _PROMPT_HASH_FIELDS)
    prompt = _find_field(row, "prompt")
    if declared is None and isinstance(prompt, str):
        return _sha256_text(prompt)
    if declared is not None and isinstance(prompt, str):
        observed = _sha256_text(prompt)
        if observed != declared:
            raise ValueError("declared prompt hash does not match prompt text")
    return declared if isinstance(declared, str) else None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _first_present(row: Mapping[str, Any], field_names: tuple[str, ...]) -> Any:
    for field_name in field_names:
        value = _find_field(row, field_name)
        if value is not None:
            return value
    return None


def _find_field(row: Mapping[str, Any], field_name: str) -> Any:
    direct = row.get(field_name)
    if direct is not None:
        return direct
    for nested_name in _NESTED_FIELD_CONTAINERS:
        nested = row.get(nested_name)
        if not isinstance(nested, Mapping):
            continue
        value = nested.get(field_name)
        if value is not None:
            return value
    return None


def _truthy_field(row: Mapping[str, Any], field_name: str) -> bool:
    return _find_field(row, field_name) is True


def _reject(
    metadata: dict[str, Any],
    input_path: str,
    row_index: int,
    reason: str,
    row: Any,
) -> None:
    metadata["rejected_row_counts"][input_path] = (
        metadata["rejected_row_counts"].get(input_path, 0) + 1
    )
    metadata["rejection_reasons"][reason] += 1
    condition = row.get("condition") if isinstance(row, Mapping) else None
    metadata["rejections"].append(
        {
            "input_path": input_path,
            "row_index": row_index,
            "condition": condition,
            "reason": reason,
        }
    )


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[int, str, str, str, int, int]:
    condition_order = {
        "none": 0,
        "G": 1,
        "C": 2,
        "G+C": 3,
    }
    return (
        condition_order.get(str(entry["condition"]), 99),
        str(entry["kernel_class"]),
        str(entry["kernel_name"]),
        str(entry["dtype"]),
        int(entry["base_seed"]),
        int(entry["sample_index"]),
    )


def _reject_duplicate_entry_keys(entries: Sequence[Mapping[str, Any]]) -> None:
    full_keys: set[tuple[Any, ...]] = set()
    sample_keys: set[tuple[Any, ...]] = set()
    replay_keys: set[tuple[Any, ...]] = set()
    for entry in entries:
        full_key = _entry_full_pair_key(entry)
        if full_key in full_keys:
            raise ValueError(f"duplicate no-P control pair key {full_key!r}")
        full_keys.add(full_key)

        sample_key = _entry_sample_pair_key(entry)
        if sample_key in sample_keys:
            raise ValueError(f"duplicate no-P control sample pair key {sample_key!r}")
        sample_keys.add(sample_key)

        replay_pair_id = entry.get("replay_pair_id")
        if replay_pair_id is not None:
            replay_key = (entry["condition"], replay_pair_id)
            if replay_key in replay_keys:
                raise ValueError(f"duplicate no-P control replay_pair_id {replay_key!r}")
            replay_keys.add(replay_key)


def _entry_full_pair_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry["condition"],
        entry["kernel_class"],
        entry["kernel_name"],
        entry["dtype"],
        entry["base_seed"],
        entry["sample_index"],
        entry.get("replay_pair_id"),
    )


def _entry_sample_pair_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry["condition"],
        entry["kernel_class"],
        entry["kernel_name"],
        entry["dtype"],
        entry["base_seed"],
        entry["sample_index"],
    )


def _reject_output_path_under_outputs(output_path: Path) -> None:
    repo_root = _repository_root()
    resolved_output = (
        output_path.resolve()
        if output_path.is_absolute()
        else (Path.cwd() / output_path).resolve()
    )
    outputs_root = (repo_root / "outputs").resolve()
    try:
        resolved_output.relative_to(outputs_root)
    except ValueError:
        return
    raise ValueError("no-P pair manifest builder must not write under outputs/")


def _repository_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / ".git").exists():
            return candidate
    return current.parents[2]


def _required_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("optional string fields must be non-empty strings or null")
    return value


def _is_non_negative_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if not _is_non_negative_int(value):
        raise ValueError(f"{field_name} must be a non-negative integer")
    return int(value)


def _require_positive_int(value: Any, field_name: str) -> int:
    if not _is_non_negative_int(value) or int(value) <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return int(value)


def _require_non_negative_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _require_sha256(value: Any, field_name: str) -> str:
    text = _required_str(value, field_name)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field_name} must be a lowercase sha256 hex digest")
    return text


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError("optional boolean fields must be booleans or null")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
