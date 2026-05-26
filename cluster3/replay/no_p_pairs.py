"""Public Cluster 3 P/no-P replay manifest and pair identity helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from cluster3.constants import CLUSTER3_CONDITIONS, normalize_cluster3_condition


NO_P_PAIR_MANIFEST_SCHEMA_VERSION = "cluster3.no_p_pair_manifest.v1"
NO_P_CONTROL_CONDITIONS: tuple[str, ...] = ("none", "G", "C", "G+C")
SampleIndexSource = Literal[
    "row_sample_index",
    "base_seed_derived",
    "attempt_index_derived",
    "missing",
]

_PAIR_FOR_CONDITION: dict[str, str] = {
    "P": "none",
    "G+P": "G",
    "C+P": "C",
    "G+C+P": "G+C",
}
_PAIR_IDENTITY_FIELDS = (
    "kernel_class",
    "kernel_name",
    "dtype",
    "base_seed",
)
_OPTIONAL_MODEL_FIELDS = (
    "model_id",
    "model_revision",
    "tokenizer_revision",
    "temperature",
    "max_new_tokens",
    "scale_tier",
)
_PROMPT_HASH_FIELDS = (
    "prompt_sha",
    "prompt_sha256",
    "prompt_hash",
    "base_prompt_sha256",
)
_SOURCE_HASH_FIELDS = (
    "source_hash",
    "source_sha256",
)
_SAMPLE_INDEX_SOURCES: tuple[SampleIndexSource, ...] = (
    "row_sample_index",
    "base_seed_derived",
    "attempt_index_derived",
    "missing",
)
_REQUIRED_MANIFEST_ENTRY_FIELDS = (
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


@dataclass(frozen=True)
class NoPControlManifestEntry:
    """One no-P control row that can validate a Cluster 3 P-row pair."""

    artifact_id: str
    artifact_path: str
    condition: str
    grammar_variant: str | None
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    generation_seed: int
    sample_index: int | None
    sample_index_source: SampleIndexSource
    replay_pair_id: str | None
    source_sha256: str
    prompt_sha256: str
    model_id: str
    model_revision: str
    tokenizer_revision: str
    temperature: float
    max_new_tokens: int
    scale_tier: str | None
    compile_success: bool | None
    functional_success: bool | None
    failure_code: str | None
    row_index: int
    row_schema_version: int | str | None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NoPControlManifestEntry":
        """Build a validated manifest entry from JSON data."""

        if not isinstance(payload, Mapping):
            raise TypeError("manifest entry must be a JSON object")
        _validate_manifest_entry_payload(payload)
        return cls(
            artifact_id=str(payload["artifact_id"]),
            artifact_path=str(payload["artifact_path"]),
            condition=str(payload["condition"]),
            grammar_variant=_optional_str(payload["grammar_variant"]),
            kernel_class=str(payload["kernel_class"]),
            kernel_name=str(payload["kernel_name"]),
            dtype=str(payload["dtype"]),
            base_seed=int(payload["base_seed"]),
            generation_seed=int(payload["generation_seed"]),
            sample_index=(
                None
                if payload["sample_index"] is None
                else int(payload["sample_index"])
            ),
            sample_index_source=payload["sample_index_source"],
            replay_pair_id=_optional_str(payload["replay_pair_id"]),
            source_sha256=str(payload["source_sha256"]),
            prompt_sha256=str(payload["prompt_sha256"]),
            model_id=str(payload["model_id"]),
            model_revision=str(payload["model_revision"]),
            tokenizer_revision=str(payload["tokenizer_revision"]),
            temperature=float(payload["temperature"]),
            max_new_tokens=int(payload["max_new_tokens"]),
            scale_tier=_optional_str(payload["scale_tier"]),
            compile_success=_optional_bool(payload["compile_success"]),
            functional_success=_optional_bool(payload["functional_success"]),
            failure_code=_optional_str(payload["failure_code"]),
            row_index=int(payload["row_index"]),
            row_schema_version=payload["row_schema_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable manifest entry data."""

        return asdict(self)


NoPPairManifestEntry = NoPControlManifestEntry


@dataclass(frozen=True)
class NoPPairManifest:
    """Loaded Cluster 3 no-P control manifest."""

    schema_version: str
    entries: tuple[NoPControlManifestEntry, ...]
    description: str | None = None
    build_metadata: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable manifest data."""

        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "entries": [entry.to_dict() for entry in self.entries],
        }
        if self.description is not None:
            payload["description"] = self.description
        if self.build_metadata is not None:
            payload["build_metadata"] = self.build_metadata
        return payload


def pair_for_condition(p_condition: str) -> str:
    """Return the no-P control condition paired with a Cluster 3 P condition."""

    condition = normalize_cluster3_condition(p_condition)
    return _PAIR_FOR_CONDITION[condition]


def validate_pair_identity(p_row: Any, control_row: Any) -> None:
    """Validate public identity fields for a Cluster 3 row and no-P control row."""

    _require_control_entry_usable(control_row)
    _require_source_hash_matches_available_source(p_row)
    _require_source_hash_matches_available_source(control_row)

    p_condition = _field(p_row, "condition")
    if p_condition not in CLUSTER3_CONDITIONS:
        raise ValueError("p_row condition must be one of the Cluster 3 conditions")
    expected_control = pair_for_condition(str(p_condition))
    observed_control = _field(control_row, "condition")
    if observed_control != expected_control:
        raise ValueError(
            f"control row condition must be {expected_control!r}; "
            f"got {observed_control!r}"
        )

    for field_name in _PAIR_IDENTITY_FIELDS:
        _require_equal_required(p_row, control_row, field_name)

    _require_equal_when_present(p_row, control_row, "sample_index")
    _require_equal_when_present(p_row, control_row, "replay_pair_id")

    for field_name in _OPTIONAL_MODEL_FIELDS:
        _require_equal_when_present(p_row, control_row, field_name)

    _require_matching_prompt_hash_when_present(p_row, control_row)
    _require_matching_grammar_variant_when_needed(
        str(p_condition),
        p_row,
        control_row,
    )
    _require_matching_control_source_when_declared(p_row, control_row)


def load_no_p_pair_manifest(path: str | Path) -> NoPPairManifest:
    """Load and validate a Cluster 3 no-P pair manifest JSON file."""

    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("no-P pair manifest must be a JSON object")
    schema_version = payload.get("schema_version")
    if schema_version != NO_P_PAIR_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "unsupported no-P pair manifest schema_version: "
            f"{schema_version!r}"
        )
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("no-P pair manifest entries must be a list")
    entries = tuple(NoPControlManifestEntry.from_dict(item) for item in raw_entries)
    _reject_duplicate_manifest_pair_keys(entries)
    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("no-P pair manifest description must be a string when present")
    build_metadata = payload.get("build_metadata")
    if build_metadata is not None and not isinstance(build_metadata, Mapping):
        raise ValueError("no-P pair manifest build_metadata must be an object")
    return NoPPairManifest(
        schema_version=NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
        description=description,
        entries=entries,
        build_metadata=build_metadata,
    )


def resolve_no_p_control(
    manifest: NoPPairManifest | Mapping[str, Any],
    p_row: Any,
) -> NoPControlManifestEntry:
    """Return the unique manifest control entry for a Cluster 3 P row."""

    loaded_manifest = _coerce_manifest(manifest)
    p_condition = _field(p_row, "condition")
    if p_condition not in CLUSTER3_CONDITIONS:
        raise ValueError("p_row condition must be one of the Cluster 3 conditions")
    expected_control = pair_for_condition(str(p_condition))

    kernel_class = _required_row_field(p_row, "kernel_class")
    kernel_name = _required_row_field(p_row, "kernel_name")
    dtype = _required_row_field(p_row, "dtype")
    base_seed = _required_row_field(p_row, "base_seed")
    sample_index = _find_field(p_row, "sample_index")
    replay_pair_id = _find_field(p_row, "replay_pair_id")

    matches: list[NoPControlManifestEntry] = []
    for entry in loaded_manifest.entries:
        if entry.condition != expected_control:
            continue
        if entry.kernel_class != kernel_class:
            continue
        if entry.kernel_name != kernel_name:
            continue
        if entry.dtype != dtype:
            continue
        if entry.base_seed != base_seed:
            continue
        if sample_index is not None and entry.sample_index != sample_index:
            continue
        if replay_pair_id is not None and entry.replay_pair_id != replay_pair_id:
            continue
        matches.append(entry)

    if not matches:
        raise ValueError(
            "no matching no-P control entry for "
            f"{p_condition!r}/{expected_control!r} "
            f"{kernel_class}/{kernel_name}/{dtype}/base_seed={base_seed!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            "multiple no-P control entries match "
            f"{p_condition!r}/{expected_control!r} "
            f"{kernel_class}/{kernel_name}/{dtype}/base_seed={base_seed!r}"
        )
    validate_pair_identity(p_row, matches[0])
    return matches[0]


def _require_equal_when_present(row: Any, control_row: Any, field_name: str) -> None:
    left = _find_field(row, field_name)
    right = _find_field(control_row, field_name)
    if left is None or right is None:
        return
    if left != right:
        raise ValueError(
            f"pair identity mismatch for {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_equal_required(row: Any, control_row: Any, field_name: str) -> None:
    left = _find_field(row, field_name)
    right = _find_field(control_row, field_name)
    if left is None or right is None:
        raise ValueError(
            f"pair identity missing required {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )
    if left != right:
        raise ValueError(
            f"pair identity mismatch for {field_name}: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_prompt_hash_when_present(row: Any, control_row: Any) -> None:
    left = _first_present(row, _PROMPT_HASH_FIELDS)
    right = _first_present(control_row, _PROMPT_HASH_FIELDS)
    if left is None or right is None:
        return
    if left != right:
        raise ValueError(
            f"pair identity mismatch for prompt hash: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_grammar_variant_when_needed(
    p_condition: str,
    row: Any,
    control_row: Any,
) -> None:
    if p_condition not in {"G+P", "G+C+P"}:
        return
    if _truthy_field(row, "allow_grammar_variant_mismatch") or _truthy_field(
        control_row,
        "allow_grammar_variant_mismatch",
    ):
        return
    left = _find_field(row, "grammar_variant")
    right = _find_field(control_row, "grammar_variant")
    if left is None or right is None:
        raise ValueError(
            "pair identity missing required grammar_variant: "
            f"p_row={left!r}, control_row={right!r}"
        )
    if left != right:
        raise ValueError(
            "pair identity mismatch for grammar_variant: "
            f"p_row={left!r}, control_row={right!r}"
        )


def _require_matching_control_source_when_declared(row: Any, control_row: Any) -> None:
    expected = _first_present(
        row,
        (
            "replay_control_source_hash",
            "expected_control_source_hash",
            "control_source_hash",
            "frozen_control_source_hash",
        ),
    )
    observed = _first_present(
        control_row,
        (
            "source_hash",
            "source_sha256",
            "replay_control_source_hash",
            "expected_control_source_hash",
        ),
    )
    if expected is None or observed is None:
        return
    if expected != observed:
        raise ValueError(
            "pair identity mismatch for control source hash: "
            f"expected={expected!r}, observed={observed!r}"
        )


def _require_control_entry_usable(control_row: Any) -> None:
    sample_index_source = _find_field(control_row, "sample_index_source")
    if sample_index_source == "missing":
        raise ValueError('sample_index_source="missing" cannot be used for validation')


def _require_source_hash_matches_available_source(row: Any) -> None:
    source = _find_field(row, "source")
    if source is None:
        return
    source_hash = _first_present(row, _SOURCE_HASH_FIELDS)
    if source_hash is None:
        return
    if not isinstance(source, str):
        raise ValueError("source must be a string when source hash is declared")
    observed = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if observed != source_hash:
        raise ValueError(
            "pair identity mismatch for source hash: "
            f"declared={source_hash!r}, observed={observed!r}"
        )


def _first_present(row: Any, field_names: tuple[str, ...]) -> Any:
    for field_name in field_names:
        value = _find_field(row, field_name)
        if value is not None:
            return value
    return None


def _find_field(row: Any, field_name: str) -> Any:
    direct = _field(row, field_name)
    if direct is not None:
        return direct
    for nested_name in (
        "generated_metadata",
        "replay_metadata",
        "metadata",
        "identity",
        "generation_identity",
        "source_identity",
        "eval_identity",
    ):
        nested = _field(row, nested_name)
        if nested is None:
            continue
        value = _field(nested, field_name)
        if value is not None:
            return value
    return None


def _truthy_field(row: Any, field_name: str) -> bool:
    return _find_field(row, field_name) is True


def _field(container: Any, field_name: str) -> Any:
    if isinstance(container, Mapping):
        return container.get(field_name)
    return getattr(container, field_name, None)


def _coerce_manifest(manifest: NoPPairManifest | Mapping[str, Any]) -> NoPPairManifest:
    if isinstance(manifest, NoPPairManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a NoPPairManifest or mapping")
    schema_version = manifest.get("schema_version")
    if schema_version != NO_P_PAIR_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "unsupported no-P pair manifest schema_version: "
            f"{schema_version!r}"
        )
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list | tuple):
        raise ValueError("no-P pair manifest entries must be a list")
    entries = tuple(
        item
        if isinstance(item, NoPControlManifestEntry)
        else NoPControlManifestEntry.from_dict(item)
        for item in raw_entries
    )
    _reject_duplicate_manifest_pair_keys(entries)
    return NoPPairManifest(
        schema_version=NO_P_PAIR_MANIFEST_SCHEMA_VERSION,
        description=_optional_str(manifest.get("description")),
        entries=entries,
        build_metadata=manifest.get("build_metadata")
        if isinstance(manifest.get("build_metadata"), Mapping)
        else None,
    )


def _validate_manifest_entry_payload(payload: Mapping[str, Any]) -> None:
    missing = [field for field in _REQUIRED_MANIFEST_ENTRY_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"manifest entry missing required fields: {missing}")
    unknown = sorted(set(payload) - set(_REQUIRED_MANIFEST_ENTRY_FIELDS))
    if unknown:
        raise ValueError(f"manifest entry has unknown fields: {unknown}")

    condition = _required_str(payload["condition"], "condition")
    if condition not in NO_P_CONTROL_CONDITIONS:
        raise ValueError(f"unknown no-P control condition {condition!r}")
    for field_name in (
        "artifact_id",
        "artifact_path",
        "kernel_class",
        "kernel_name",
        "dtype",
        "source_sha256",
        "prompt_sha256",
        "model_id",
        "model_revision",
        "tokenizer_revision",
    ):
        _required_str(payload[field_name], field_name)
    _optional_str(payload["grammar_variant"])
    _optional_str(payload["replay_pair_id"])
    _optional_str(payload["scale_tier"])
    _optional_str(payload["failure_code"])
    _require_non_negative_int(payload["base_seed"], "base_seed")
    _require_non_negative_int(payload["generation_seed"], "generation_seed")
    _require_non_negative_int(payload["row_index"], "row_index")
    _require_non_negative_int(payload["max_new_tokens"], "max_new_tokens")
    if payload["max_new_tokens"] <= 0:
        raise ValueError("max_new_tokens must be positive")
    _require_number(payload["temperature"], "temperature")
    _optional_bool(payload["compile_success"])
    _optional_bool(payload["functional_success"])

    sample_source = payload["sample_index_source"]
    if sample_source not in _SAMPLE_INDEX_SOURCES:
        raise ValueError(f"unknown sample_index_source {sample_source!r}")
    if sample_source == "missing":
        raise ValueError('sample_index_source="missing" cannot be used for validation')
    _require_non_negative_int(payload["sample_index"], "sample_index")
    if payload["row_schema_version"] is not None and not isinstance(
        payload["row_schema_version"],
        int | str,
    ):
        raise ValueError("row_schema_version must be an int, string, or null")


def _reject_duplicate_manifest_pair_keys(
    entries: tuple[NoPControlManifestEntry, ...],
) -> None:
    full_keys: set[tuple[Any, ...]] = set()
    sample_keys: set[tuple[Any, ...]] = set()
    replay_keys: set[tuple[Any, ...]] = set()
    for entry in entries:
        full_key = _manifest_full_pair_key(entry)
        if full_key in full_keys:
            raise ValueError(f"duplicate no-P control pair key {full_key!r}")
        full_keys.add(full_key)

        if entry.sample_index is not None:
            sample_key = _manifest_sample_pair_key(entry)
            if sample_key in sample_keys:
                raise ValueError(f"duplicate no-P control sample pair key {sample_key!r}")
            sample_keys.add(sample_key)
        if entry.replay_pair_id is not None:
            replay_key = (entry.condition, entry.replay_pair_id)
            if replay_key in replay_keys:
                raise ValueError(f"duplicate no-P control replay_pair_id {replay_key!r}")
            replay_keys.add(replay_key)


def _manifest_full_pair_key(entry: NoPControlManifestEntry) -> tuple[Any, ...]:
    return (
        entry.condition,
        entry.kernel_class,
        entry.kernel_name,
        entry.dtype,
        entry.base_seed,
        entry.sample_index,
        entry.replay_pair_id,
    )


def _manifest_sample_pair_key(entry: NoPControlManifestEntry) -> tuple[Any, ...]:
    return (
        entry.condition,
        entry.kernel_class,
        entry.kernel_name,
        entry.dtype,
        entry.base_seed,
        entry.sample_index,
    )


def _required_row_field(row: Any, field_name: str) -> Any:
    value = _find_field(row, field_name)
    if value is None:
        raise ValueError(f"p_row missing required {field_name}")
    return value


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


def _require_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _require_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")
    return float(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError("optional boolean fields must be booleans or null")
    return value


__all__ = [
    "NO_P_CONTROL_CONDITIONS",
    "NO_P_PAIR_MANIFEST_SCHEMA_VERSION",
    "NoPControlManifestEntry",
    "NoPPairManifest",
    "NoPPairManifestEntry",
    "load_no_p_pair_manifest",
    "pair_for_condition",
    "resolve_no_p_control",
    "validate_pair_identity",
]
