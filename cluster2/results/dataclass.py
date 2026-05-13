"""Cluster 2 metadata dataclasses.

These records describe candidate identity and content/version hashes only. They
are not result loggers and do not contain runtime metric fields.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from typing import Any

from cluster2.constants import (
    DTYPE_NAMES,
    generation_mode_for_condition,
    normalize_cluster2_condition,
    source_class_for_condition,
)
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES


@dataclass(frozen=True)
class Cluster2CellIdentity:
    """Stable identity for one locked C2 experimental cell."""

    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int

    def __post_init__(self) -> None:
        if self.kernel_class not in LOCKED_KERNEL_CLASSES:
            allowed = ", ".join(LOCKED_KERNEL_CLASSES)
            raise ValueError(
                f"unsupported kernel_class {self.kernel_class!r}; allowed: {allowed}"
            )
        if self.dtype not in DTYPE_NAMES:
            raise ValueError(
                f"unsupported dtype {self.dtype!r}; allowed: {', '.join(DTYPE_NAMES)}"
            )
        if self.base_seed < 0:
            raise ValueError("base_seed must be non-negative")

    def canonical_key(self) -> tuple[str, str, str, int]:
        return (self.kernel_class, self.kernel_name, self.dtype, self.base_seed)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2CellIdentity":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster2CandidateIdentity:
    """Stable identity for one generated or replayed candidate source."""

    cell: Cluster2CellIdentity
    condition: str
    source_class: str
    generation_mode: str
    attempt_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.cell, Cluster2CellIdentity):
            raise TypeError("cell must be a Cluster2CellIdentity")
        condition = normalize_cluster2_condition(self.condition)
        object.__setattr__(self, "condition", condition)
        expected_source_class = source_class_for_condition(condition)
        expected_generation_mode = generation_mode_for_condition(condition)
        if self.source_class != expected_source_class:
            raise ValueError(
                f"condition {condition!r} requires source_class "
                f"{expected_source_class!r}; got {self.source_class!r}"
            )
        if self.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.generation_mode!r}"
            )
        if self.attempt_index < 0:
            raise ValueError("attempt_index must be non-negative")

    def canonical_key(self) -> tuple[str, str, str, int, str, int]:
        return (*self.cell.canonical_key(), self.condition, self.attempt_index)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2CandidateIdentity":
        if not isinstance(payload, dict):
            raise TypeError("Cluster2CandidateIdentity.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        converted = dict(payload)
        cell = converted.get("cell")
        if not isinstance(cell, Cluster2CellIdentity):
            converted["cell"] = Cluster2CellIdentity.from_dict(cell)
        return cls(**converted)


@dataclass(frozen=True)
class Cluster2CandidateMetadata:
    """Hash/version metadata for one C2 candidate.

    ``generation_hashes`` are source-class-specific: replay controls carry
    frozen Cluster 1 artifact/source hashes, while generated rows later carry
    C2 generation-source hashes.
    """

    identity: Cluster2CandidateIdentity
    source_sha256: str
    model_id: str
    model_revision: str | None
    tokenizer_revision: str | None
    eval_pipeline_hashes: dict[str, str]
    generation_hashes: dict[str, str]
    external_pins: dict[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, Cluster2CandidateIdentity):
            raise TypeError("identity must be a Cluster2CandidateIdentity")
        _validate_sha256(self.source_sha256, "source_sha256")
        _validate_hash_mapping(self.eval_pipeline_hashes, "eval_pipeline_hashes")
        _validate_hash_mapping(self.generation_hashes, "generation_hashes")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2CandidateMetadata":
        if not isinstance(payload, dict):
            raise TypeError("Cluster2CandidateMetadata.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        converted = dict(payload)
        identity = converted.get("identity")
        if not isinstance(identity, Cluster2CandidateIdentity):
            converted["identity"] = Cluster2CandidateIdentity.from_dict(identity)
        return cls(**converted)


def make_candidate_identity(
    *,
    cell: Cluster2CellIdentity,
    condition: str,
    attempt_index: int,
) -> Cluster2CandidateIdentity:
    """Build a condition-consistent candidate identity."""

    normalized = normalize_cluster2_condition(condition)
    return Cluster2CandidateIdentity(
        cell=cell,
        condition=normalized,
        source_class=source_class_for_condition(normalized),
        generation_mode=generation_mode_for_condition(normalized),
        attempt_index=attempt_index,
    )


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _from_dict_strict(cls: type[Any], payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        raise TypeError(f"{cls.__name__}.from_dict requires a dict")
    _reject_unknown_fields(cls, payload)
    try:
        return cls(**payload)
    except TypeError as exc:
        raise ValueError(f"invalid {cls.__name__} payload: {exc}") from exc


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")


def _validate_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a SHA256 hex digest") from exc


def _validate_hash_mapping(value: dict[str, str], field_name: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    for key, digest in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        _validate_sha256(digest, f"{field_name}[{key!r}]")
