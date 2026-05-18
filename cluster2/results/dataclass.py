"""Cluster 2 metadata dataclasses.

These records describe candidate identity and content/version hashes only. They
are not result loggers and do not contain runtime metric fields.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from typing import Any

from cluster2.constants import (
    DTYPE_NAMES,
    GENERATED_SOURCE_CLASS,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
    REPLAY_CONTROL_SOURCE_CLASS,
    generation_mode_for_condition,
    normalize_cluster2_condition,
    source_class_for_condition,
)
from cluster2.feedback.trace import TraceSummary
from shared.generation_metadata import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    GRAMMAR_CLAIM_SCOPE_BY_VARIANT,
    GRAMMAR_PATHS_BY_VARIANT,
    PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES,
    PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES,
    UNKNOWN,
    VALID_REJECTION_LAYERS,
    VALID_STOP_REASONS,
    is_immutable_hub_revision,
    modal_image_provenance_digest,
)
from shared.eval.correctness_shapes import LOCKED_KERNEL_CLASSES, get_shape_metadata
from shared.eval.failure_taxonomy import FAILURE_CODES


CLUSTER2_RESULTS_SCHEMA_VERSION = 1

FORBIDDEN_CLUSTER2_RESULT_FIELDS: frozenset[str] = frozenset(
    {
        "latency",
        "throughput",
        "speedup",
        "tokens",
        "token_counts",
        "gpu_utilization",
        "benchmark_score",
        "profiler_output",
        "ncu",
        "nsight",
        "timing",
        "wall_time",
        "fast@",
    }
)


@dataclass(frozen=True)
class Cluster2CellIdentity:
    """Stable identity for one locked C2 experimental cell."""

    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int

    def __post_init__(self) -> None:
        _validate_locked_kernel_identity(self.kernel_class, self.kernel_name)
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


@dataclass(frozen=True)
class Cluster2ReplayRowMetadata:
    """Replay-only provenance for rows sourced from frozen Cluster 1 artifacts."""

    frozen_cluster1_artifact_id: str
    frozen_cluster1_source_hash: str
    frozen_cluster1_generation_hashes: dict[str, str]
    frozen_cluster1_row_hash: str | None = None
    replay_pair_id: str | None = None
    replay_base_seed: int | None = None
    replay_generation_seed: int | None = None
    prompt_sha256: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    temperature: float | None = None
    max_new_tokens: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(
            self.frozen_cluster1_artifact_id,
            "frozen_cluster1_artifact_id",
        )
        _validate_sha256(self.frozen_cluster1_source_hash, "frozen_cluster1_source_hash")
        _validate_hash_mapping(
            self.frozen_cluster1_generation_hashes,
            "frozen_cluster1_generation_hashes",
            require_non_empty=True,
        )
        _validate_optional_sha256(
            self.frozen_cluster1_row_hash,
            "frozen_cluster1_row_hash",
        )
        _validate_pairing_metadata(
            replay_pair_id=self.replay_pair_id,
            replay_base_seed=self.replay_base_seed,
            replay_generation_seed=self.replay_generation_seed,
            prompt_sha256=self.prompt_sha256,
            model_id=self.model_id,
            model_revision=self.model_revision,
            tokenizer_revision=self.tokenizer_revision,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2ReplayRowMetadata":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster2GeneratedRowMetadata:
    """Generated-only provenance for rows produced by the C2 generation surface."""

    c2_generation_hashes: dict[str, str]
    generation_seed: int | None = None
    grammar_variant: str | None = None
    grammar_path: str | None = None
    grammar_sha: str | None = None
    grammar_claim_scope: str | None = None
    gbnf_parse_valid: bool | None = None
    semantic_valid: bool | None = None
    grammar_valid: bool | None = None
    rejection_layer: str | None = None
    stop_reason: str = UNKNOWN
    xgrammar_version: str = UNKNOWN
    transformers_version: str = UNKNOWN
    tokenizers_version: str = UNKNOWN
    modal_image_sha: str = UNKNOWN
    modal_image_provenance_sha256: str | None = None
    modal_image_provenance_components: dict[str, Any] | None = None
    generation_metadata_schema_version: int = 0
    replay_pair_id: str | None = None
    replay_control_condition: str | None = None
    replay_base_seed: int | None = None
    replay_generation_seed: int | None = None
    prompt_sha256: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    temperature: float | None = None
    max_new_tokens: int | None = None

    def __post_init__(self) -> None:
        _validate_hash_mapping(
            self.c2_generation_hashes,
            "c2_generation_hashes",
            require_non_empty=True,
        )
        if self.generation_seed is not None:
            _require_non_negative_int(self.generation_seed, "generation_seed")
        _validate_generated_grammar_metadata(
            grammar_variant=self.grammar_variant,
            grammar_path=self.grammar_path,
            grammar_claim_scope=self.grammar_claim_scope,
        )
        _validate_generated_runtime_metadata(
            generation_metadata_schema_version=(
                self.generation_metadata_schema_version
            ),
            grammar_variant=self.grammar_variant,
            grammar_sha=self.grammar_sha,
            gbnf_parse_valid=self.gbnf_parse_valid,
            semantic_valid=self.semantic_valid,
            grammar_valid=self.grammar_valid,
            rejection_layer=self.rejection_layer,
            stop_reason=self.stop_reason,
            modal_image_sha=self.modal_image_sha,
            modal_image_provenance_sha256=self.modal_image_provenance_sha256,
            modal_image_provenance_components=(
                self.modal_image_provenance_components
            ),
        )
        if self.replay_control_condition is not None:
            if self.replay_control_condition not in REPLAY_CONTROL_CONDITIONS:
                raise ValueError(
                    "replay_control_condition must be one of: "
                    f"{', '.join(REPLAY_CONTROL_CONDITIONS)}"
                )
        _validate_pairing_metadata(
            replay_pair_id=self.replay_pair_id,
            replay_base_seed=self.replay_base_seed,
            replay_generation_seed=self.replay_generation_seed,
            prompt_sha256=self.prompt_sha256,
            model_id=self.model_id,
            model_revision=self.model_revision,
            tokenizer_revision=self.tokenizer_revision,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2GeneratedRowMetadata":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster2EvalRow:
    """Primary Cluster 2 JSONL row.

    Eval-pipeline hashes and generation-source hashes intentionally stay in
    sidecars or source-class-specific metadata. Replay controls carry frozen
    Cluster 1 generation provenance, while generated rows carry C2 generation
    provenance.
    """

    condition: str
    source_class: str
    generation_mode: str
    attempt_index: int
    kernel_class: str
    kernel_name: str
    dtype: str
    base_seed: int
    source_hash: str
    functional_success: bool
    repair_set_success: bool
    eval_set_success: bool
    failure_code: str | None
    trace_summary: TraceSummary | None
    replay_metadata: Cluster2ReplayRowMetadata | None
    generated_metadata: Cluster2GeneratedRowMetadata | None

    def __post_init__(self) -> None:
        _assert_allowed_result_field_names(self)
        condition = normalize_cluster2_condition(self.condition)
        object.__setattr__(self, "condition", condition)

        expected_source_class = source_class_for_condition(condition)
        if self.source_class != expected_source_class:
            raise ValueError(
                f"condition {condition!r} requires source_class "
                f"{expected_source_class!r}; got {self.source_class!r}"
            )
        expected_generation_mode = generation_mode_for_condition(condition)
        if self.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.generation_mode!r}"
            )

        _require_non_negative_int(self.attempt_index, "attempt_index")
        _validate_locked_kernel_identity(self.kernel_class, self.kernel_name)
        if self.dtype not in DTYPE_NAMES:
            raise ValueError(
                f"unsupported dtype {self.dtype!r}; allowed: {', '.join(DTYPE_NAMES)}"
            )
        _require_non_negative_int(self.base_seed, "base_seed")
        _validate_sha256(self.source_hash, "source_hash")
        _require_bool(self.functional_success, "functional_success")
        _require_bool(self.repair_set_success, "repair_set_success")
        _require_bool(self.eval_set_success, "eval_set_success")
        if self.functional_success != (
            self.repair_set_success and self.eval_set_success
        ):
            raise ValueError(
                "functional_success must equal repair_set_success and eval_set_success"
            )
        if self.functional_success and self.failure_code is not None:
            raise ValueError("failure_code must be None when functional_success is True")
        if self.failure_code is not None and self.failure_code not in FAILURE_CODES:
            raise ValueError(f"unsupported failure_code {self.failure_code!r}")

        if self.trace_summary is not None:
            if not isinstance(self.trace_summary, TraceSummary):
                raise TypeError("trace_summary must be a TraceSummary or None")
            if self.trace_summary.attempt_index != self.attempt_index:
                raise ValueError("trace_summary attempt_index must match row")
            if (
                self.trace_summary.source_hash is not None
                and self.trace_summary.source_hash != self.source_hash
            ):
                raise ValueError("trace_summary source_hash must match row source_hash")
            if self.trace_summary.functional_success != self.functional_success:
                raise ValueError(
                    "trace_summary functional_success must match row functional_success"
                )
            if self.trace_summary.repair_set_success != self.repair_set_success:
                raise ValueError(
                    "trace_summary repair_set_success must match row repair_set_success"
                )
            if self.trace_summary.eval_set_success != self.eval_set_success:
                raise ValueError(
                    "trace_summary eval_set_success must match row eval_set_success"
                )
            if self.trace_summary.failure_code != self.failure_code:
                raise ValueError("trace_summary failure_code must match row failure_code")

        self._validate_source_class_metadata()

    def _validate_source_class_metadata(self) -> None:
        if self.condition in REPLAY_CONTROL_CONDITIONS:
            if self.trace_summary is not None:
                raise ValueError("replay controls must not carry trace_summary")
            if not isinstance(self.replay_metadata, Cluster2ReplayRowMetadata):
                raise TypeError(
                    "replay controls require Cluster2ReplayRowMetadata"
                )
            if self.generated_metadata is not None:
                raise ValueError("replay controls must not carry generated_metadata")
            if self.replay_metadata.frozen_cluster1_source_hash != self.source_hash:
                raise ValueError(
                    "replay source_hash must match frozen_cluster1_source_hash"
                )
            return

        if self.condition in NEW_GENERATION_CONDITIONS:
            if not isinstance(self.generated_metadata, Cluster2GeneratedRowMetadata):
                raise TypeError(
                    "generated rows require Cluster2GeneratedRowMetadata"
                )
            if self.condition == "G+C" and (
                self.generated_metadata.grammar_variant is None
                or self.generated_metadata.grammar_path is None
                or self.generated_metadata.grammar_claim_scope is None
            ):
                raise ValueError("G+C generated rows require grammar metadata")
            if self.condition == "C" and (
                self.generated_metadata.grammar_variant is not None
                or self.generated_metadata.grammar_path is not None
                or self.generated_metadata.grammar_claim_scope is not None
            ):
                raise ValueError("C generated rows must remain grammar-free")
            if self.replay_metadata is not None:
                raise ValueError("generated rows must not carry replay_metadata")
            if not isinstance(self.trace_summary, TraceSummary):
                raise TypeError("generated rows require a compact trace_summary")
            return

        raise ValueError(f"unsupported condition {self.condition!r}")

    def canonical_key(self) -> tuple[str, str, str, int, str, int]:
        return (
            self.kernel_class,
            self.kernel_name,
            self.dtype,
            self.base_seed,
            self.condition,
            self.attempt_index,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        _reject_forbidden_mapping_fields(payload)
        return payload

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2EvalRow":
        if not isinstance(payload, dict):
            raise TypeError("Cluster2EvalRow.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        _reject_forbidden_mapping_fields(payload)
        converted = dict(payload)
        trace_summary = converted.get("trace_summary")
        if trace_summary is not None and not isinstance(trace_summary, TraceSummary):
            converted["trace_summary"] = TraceSummary.from_dict(trace_summary)
        replay_metadata = converted.get("replay_metadata")
        if replay_metadata is not None and not isinstance(
            replay_metadata,
            Cluster2ReplayRowMetadata,
        ):
            converted["replay_metadata"] = Cluster2ReplayRowMetadata.from_dict(
                replay_metadata
            )
        generated_metadata = converted.get("generated_metadata")
        if generated_metadata is not None and not isinstance(
            generated_metadata,
            Cluster2GeneratedRowMetadata,
        ):
            converted["generated_metadata"] = Cluster2GeneratedRowMetadata.from_dict(
                generated_metadata
            )
        return cls(**converted)


@dataclass(frozen=True)
class Cluster2OptionalDiagnostics:
    """Optional diagnostics sidecars. Their paths are never required."""

    full_trace_sidecar_path: str | None = None
    private_eval_sidecar_path: str | None = None

    def __post_init__(self) -> None:
        _require_optional_non_empty_str(
            self.full_trace_sidecar_path,
            "full_trace_sidecar_path",
        )
        _require_optional_non_empty_str(
            self.private_eval_sidecar_path,
            "private_eval_sidecar_path",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2OptionalDiagnostics":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class Cluster2ContentHashSidecar:
    """Deterministic hash sidecar with eval/generation hash classes separated."""

    schema_version: int
    eval_pipeline_hashes: dict[str, str]
    generated_condition_hashes: dict[str, dict[str, str]]
    replay_control_hashes: dict[str, dict[str, str]]
    external_pins: dict[str, str]
    optional_diagnostics: Cluster2OptionalDiagnostics | None = None

    def __post_init__(self) -> None:
        if self.schema_version != CLUSTER2_RESULTS_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {CLUSTER2_RESULTS_SCHEMA_VERSION}"
            )
        _validate_hash_mapping(
            self.eval_pipeline_hashes,
            "eval_pipeline_hashes",
            require_non_empty=True,
        )
        _validate_condition_hash_mapping(
            self.generated_condition_hashes,
            "generated_condition_hashes",
            allowed_conditions=NEW_GENERATION_CONDITIONS,
        )
        _validate_condition_hash_mapping(
            self.replay_control_hashes,
            "replay_control_hashes",
            allowed_conditions=REPLAY_CONTROL_CONDITIONS,
        )
        _validate_string_mapping(self.external_pins, "external_pins")
        if self.optional_diagnostics is not None and not isinstance(
            self.optional_diagnostics,
            Cluster2OptionalDiagnostics,
        ):
            raise TypeError(
                "optional_diagnostics must be Cluster2OptionalDiagnostics or None"
            )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        _reject_forbidden_mapping_fields(payload)
        return payload

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    def content_signature_dict(self) -> dict[str, Any]:
        """Return the hash-checked subset used by resume mode."""

        return {
            "schema_version": self.schema_version,
            "eval_pipeline_hashes": self.eval_pipeline_hashes,
            "generated_condition_hashes": self.generated_condition_hashes,
            "replay_control_hashes": self.replay_control_hashes,
            "external_pins": self.external_pins,
        }

    def content_signature_sha256(self) -> str:
        payload = _json_dumps(self.content_signature_dict())
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def require_hash_compatible(self, other: "Cluster2ContentHashSidecar") -> None:
        if not isinstance(other, Cluster2ContentHashSidecar):
            raise TypeError("other must be a Cluster2ContentHashSidecar")
        if self.content_signature_dict() != other.content_signature_dict():
            raise ValueError("content-hash sidecar mismatch")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Cluster2ContentHashSidecar":
        if not isinstance(payload, dict):
            raise TypeError("Cluster2ContentHashSidecar.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        _reject_forbidden_mapping_fields(payload)
        converted = dict(payload)
        optional_diagnostics = converted.get("optional_diagnostics")
        if optional_diagnostics is not None and not isinstance(
            optional_diagnostics,
            Cluster2OptionalDiagnostics,
        ):
            converted["optional_diagnostics"] = Cluster2OptionalDiagnostics.from_dict(
                optional_diagnostics
            )
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


def replay_control_row(
    *,
    condition: str,
    attempt_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    source_hash: str,
    functional_success: bool,
    repair_set_success: bool,
    eval_set_success: bool,
    failure_code: str | None,
    frozen_cluster1_artifact_id: str,
    frozen_cluster1_generation_hashes: dict[str, str],
    frozen_cluster1_row_hash: str | None = None,
    replay_pair_id: str | None = None,
    replay_base_seed: int | None = None,
    replay_generation_seed: int | None = None,
    prompt_sha256: str | None = None,
    model_id: str | None = None,
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
    temperature: float | None = None,
    max_new_tokens: int | None = None,
) -> Cluster2EvalRow:
    """Build a replay-control row with frozen Cluster 1 provenance."""

    normalized = normalize_cluster2_condition(condition)
    if source_class_for_condition(normalized) != REPLAY_CONTROL_SOURCE_CLASS:
        raise ValueError(f"condition {normalized!r} is not a replay control")
    return Cluster2EvalRow(
        condition=normalized,
        source_class=REPLAY_CONTROL_SOURCE_CLASS,
        generation_mode=generation_mode_for_condition(normalized),
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=source_hash,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        failure_code=failure_code,
        trace_summary=None,
        replay_metadata=Cluster2ReplayRowMetadata(
            frozen_cluster1_artifact_id=frozen_cluster1_artifact_id,
            frozen_cluster1_source_hash=source_hash,
            frozen_cluster1_generation_hashes=frozen_cluster1_generation_hashes,
            frozen_cluster1_row_hash=frozen_cluster1_row_hash,
            replay_pair_id=replay_pair_id,
            replay_base_seed=replay_base_seed,
            replay_generation_seed=replay_generation_seed,
            prompt_sha256=prompt_sha256,
            model_id=model_id,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
        ),
        generated_metadata=None,
    )


def generated_row(
    *,
    condition: str,
    attempt_index: int,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    base_seed: int,
    source_hash: str,
    functional_success: bool,
    repair_set_success: bool,
    eval_set_success: bool,
    failure_code: str | None,
    trace_summary: TraceSummary,
    c2_generation_hashes: dict[str, str],
    generation_seed: int | None = None,
    grammar_variant: str | None = None,
    grammar_path: str | None = None,
    grammar_sha: str | None = None,
    grammar_claim_scope: str | None = None,
    gbnf_parse_valid: bool | None = None,
    semantic_valid: bool | None = None,
    grammar_valid: bool | None = None,
    rejection_layer: str | None = None,
    stop_reason: str = UNKNOWN,
    xgrammar_version: str = UNKNOWN,
    transformers_version: str = UNKNOWN,
    tokenizers_version: str = UNKNOWN,
    modal_image_sha: str = UNKNOWN,
    modal_image_provenance_sha256: str | None = None,
    modal_image_provenance_components: dict[str, Any] | None = None,
    generation_metadata_schema_version: int = 0,
    replay_pair_id: str | None = None,
    replay_control_condition: str | None = None,
    replay_base_seed: int | None = None,
    replay_generation_seed: int | None = None,
    prompt_sha256: str | None = None,
    model_id: str | None = None,
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
    temperature: float | None = None,
    max_new_tokens: int | None = None,
) -> Cluster2EvalRow:
    """Build a generated row with C2 generation provenance."""

    normalized = normalize_cluster2_condition(condition)
    if source_class_for_condition(normalized) != GENERATED_SOURCE_CLASS:
        raise ValueError(f"condition {normalized!r} is not a generated condition")
    return Cluster2EvalRow(
        condition=normalized,
        source_class=GENERATED_SOURCE_CLASS,
        generation_mode=generation_mode_for_condition(normalized),
        attempt_index=attempt_index,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        source_hash=source_hash,
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        failure_code=failure_code,
        trace_summary=trace_summary,
        replay_metadata=None,
        generated_metadata=Cluster2GeneratedRowMetadata(
            c2_generation_hashes=c2_generation_hashes,
            generation_seed=generation_seed,
            grammar_variant=grammar_variant,
            grammar_path=grammar_path,
            grammar_sha=grammar_sha,
            grammar_claim_scope=grammar_claim_scope,
            gbnf_parse_valid=gbnf_parse_valid,
            semantic_valid=semantic_valid,
            grammar_valid=grammar_valid,
            rejection_layer=rejection_layer,
            stop_reason=stop_reason,
            xgrammar_version=xgrammar_version,
            transformers_version=transformers_version,
            tokenizers_version=tokenizers_version,
            modal_image_sha=modal_image_sha,
            modal_image_provenance_sha256=modal_image_provenance_sha256,
            modal_image_provenance_components=modal_image_provenance_components,
            generation_metadata_schema_version=generation_metadata_schema_version,
            replay_pair_id=replay_pair_id,
            replay_control_condition=replay_control_condition,
            replay_base_seed=replay_base_seed,
            replay_generation_seed=replay_generation_seed,
            prompt_sha256=prompt_sha256,
            model_id=model_id,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
        ),
    )


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _from_dict_strict(cls: type[Any], payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        raise TypeError(f"{cls.__name__}.from_dict requires a dict")
    _reject_unknown_fields(cls, payload)
    _reject_forbidden_mapping_fields(payload)
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


def _validate_optional_sha256(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _validate_sha256(value, field_name)


def _validate_optional_stable_image_sha(value: str | None, field_name: str) -> None:
    if value is None or value == UNKNOWN:
        return
    _validate_sha256(value.removeprefix("sha256:"), field_name)


def _validate_modal_image_provenance_components(
    *,
    modal_image_provenance_sha256: str | None,
    modal_image_provenance_components: dict[str, Any] | None,
) -> None:
    if modal_image_provenance_components is None:
        return
    if modal_image_provenance_sha256 is None:
        raise ValueError(
            "modal_image_provenance_sha256 is required when "
            "modal_image_provenance_components is present"
        )
    expected = modal_image_provenance_digest(modal_image_provenance_components)
    if modal_image_provenance_sha256 != expected:
        raise ValueError(
            "modal_image_provenance_sha256 must equal the digest of "
            "modal_image_provenance_components"
        )


def _validate_hash_mapping(
    value: dict[str, str],
    field_name: str,
    *,
    require_non_empty: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    if require_non_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    for key, digest in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        _validate_sha256(digest, f"{field_name}[{key!r}]")


def _validate_generated_grammar_metadata(
    *,
    grammar_variant: str | None,
    grammar_path: str | None,
    grammar_claim_scope: str | None,
) -> None:
    if grammar_variant is None:
        if grammar_path is not None:
            raise ValueError("grammar_path must be None without grammar_variant")
        if grammar_claim_scope is not None:
            raise ValueError(
                "grammar_claim_scope must be None without grammar_variant"
            )
        return

    expected_paths = GRAMMAR_PATHS_BY_VARIANT
    expected_scopes = GRAMMAR_CLAIM_SCOPE_BY_VARIANT
    if grammar_variant not in expected_paths:
        allowed = ", ".join(sorted(expected_paths))
        raise ValueError(
            f"grammar_variant must be one of: {allowed}; got {grammar_variant!r}"
        )
    expected_path = expected_paths[grammar_variant]
    if grammar_path != expected_path and not str(grammar_path).endswith(expected_path):
        raise ValueError("grammar_path does not match grammar_variant")
    if grammar_claim_scope != expected_scopes[grammar_variant]:
        raise ValueError("grammar_claim_scope does not match grammar_variant")


def _validate_generated_runtime_metadata(
    *,
    generation_metadata_schema_version: int,
    grammar_variant: str | None,
    grammar_sha: str | None,
    gbnf_parse_valid: bool | None,
    semantic_valid: bool | None,
    grammar_valid: bool | None,
    rejection_layer: str | None,
    stop_reason: str,
    modal_image_sha: str | None,
    modal_image_provenance_sha256: str | None,
    modal_image_provenance_components: dict[str, Any] | None,
) -> None:
    if stop_reason not in VALID_STOP_REASONS:
        allowed = ", ".join(sorted(VALID_STOP_REASONS))
        raise ValueError(f"stop_reason must be one of {allowed}; got {stop_reason!r}")
    if rejection_layer is not None and rejection_layer not in VALID_REJECTION_LAYERS:
        allowed = ", ".join(sorted(VALID_REJECTION_LAYERS))
        raise ValueError(
            f"rejection_layer must be one of {allowed} or None; "
            f"got {rejection_layer!r}"
        )
    _validate_optional_sha256(grammar_sha, "grammar_sha")
    _validate_optional_sha256(
        modal_image_provenance_sha256,
        "modal_image_provenance_sha256",
    )
    _validate_optional_stable_image_sha(modal_image_sha, "modal_image_sha")
    _validate_modal_image_provenance_components(
        modal_image_provenance_sha256=modal_image_provenance_sha256,
        modal_image_provenance_components=modal_image_provenance_components,
    )
    if (
        generation_metadata_schema_version >= CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        and modal_image_sha in (None, UNKNOWN)
    ):
        if not modal_image_provenance_sha256:
            raise ValueError(
                "current-schema generated metadata with unknown modal_image_sha "
                "requires modal_image_provenance_sha256"
            )
        if modal_image_provenance_components is None:
            raise ValueError(
                "current-schema generated metadata with unknown modal_image_sha "
                "requires modal_image_provenance_components"
            )
    validation_values = (gbnf_parse_valid, semantic_valid, grammar_valid)
    if grammar_variant is None:
        if grammar_sha is not None:
            raise ValueError("grammar_sha must be None without grammar_variant")
        if any(value is not None for value in validation_values):
            raise ValueError(
                "grammar validation fields must be None without grammar_variant"
            )
        return
    if generation_metadata_schema_version >= CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION:
        missing_current_schema_fields = [
            field_name
            for field_name, value in (
                ("grammar_sha", grammar_sha),
                ("gbnf_parse_valid", gbnf_parse_valid),
                ("semantic_valid", semantic_valid),
                ("grammar_valid", grammar_valid),
            )
            if value is None
        ]
        if missing_current_schema_fields:
            missing = ", ".join(sorted(missing_current_schema_fields))
            raise ValueError(
                "current-schema generated grammar metadata requires: "
                f"{missing}"
            )
    if all(value is not None for value in validation_values):
        expected = bool(gbnf_parse_valid and semantic_valid)
        if grammar_valid is not expected:
            raise ValueError(
                "grammar_valid must equal gbnf_parse_valid and semantic_valid"
            )
        if grammar_valid and rejection_layer is not None:
            raise ValueError("rejection_layer must be None when grammar_valid=True")
        if not grammar_valid and rejection_layer is None:
            raise ValueError("rejection_layer is required when grammar_valid=False")


def validate_generated_paper_scale_metadata(
    metadata: Cluster2GeneratedRowMetadata,
) -> None:
    """Reject generated rows that cannot satisfy the paper-scale metadata gate."""

    missing: list[str] = []
    required = list(PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES)
    if metadata.grammar_variant is not None:
        required.extend(PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES)
    for field_name in required:
        value = getattr(metadata, field_name)
        if value is None or value == UNKNOWN:
            missing.append(field_name)
    malformed: list[str] = []
    if metadata.model_revision not in (None, UNKNOWN):
        _append_if_not_immutable_hub_revision(
            malformed,
            "model_revision",
            metadata.model_revision,
        )
    if metadata.tokenizer_revision not in (None, UNKNOWN):
        _append_if_not_immutable_hub_revision(
            malformed,
            "tokenizer_revision",
            metadata.tokenizer_revision,
        )
    if metadata.modal_image_sha not in (None, UNKNOWN):
        _append_if_not_stable_image_sha(
            malformed,
            "modal_image_sha",
            metadata.modal_image_sha,
        )
    if metadata.modal_image_provenance_sha256 is not None:
        _append_if_not_sha256_hex(
            malformed,
            "modal_image_provenance_sha256",
            metadata.modal_image_provenance_sha256,
        )
    if metadata.modal_image_sha in (None, UNKNOWN) and not metadata.modal_image_provenance_sha256:
        missing.append("modal_image_sha_or_modal_image_provenance_sha256")
    if (
        metadata.modal_image_sha in (None, UNKNOWN)
        and metadata.modal_image_provenance_components is None
    ):
        missing.append("modal_image_provenance_components")
    if metadata.modal_image_provenance_components is not None:
        try:
            _validate_modal_image_provenance_components(
                modal_image_provenance_sha256=(
                    metadata.modal_image_provenance_sha256
                ),
                modal_image_provenance_components=(
                    metadata.modal_image_provenance_components
                ),
            )
        except ValueError:
            malformed.append("modal_image_provenance_components_mismatch")
    if metadata.generation_metadata_schema_version < CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION:
        missing.append("generation_metadata_schema_version")
    if missing or malformed:
        problems = sorted(set(missing)) + sorted(set(malformed))
        raise ValueError(
            "paper-scale generated rows require generation metadata: "
            + ", ".join(problems)
        )


def _append_if_not_sha256_hex(
    failures: list[str],
    field_name: str,
    value: str,
) -> None:
    try:
        _validate_sha256(value, field_name)
    except ValueError:
        failures.append(f"{field_name}_malformed")


def _append_if_not_stable_image_sha(
    failures: list[str],
    field_name: str,
    value: str,
) -> None:
    candidate = value.removeprefix("sha256:")
    _append_if_not_sha256_hex(failures, field_name, candidate)


def _append_if_not_immutable_hub_revision(
    failures: list[str],
    field_name: str,
    value: str,
) -> None:
    if not is_immutable_hub_revision(value):
        failures.append(f"{field_name}_not_immutable")


def _validate_pairing_metadata(
    *,
    replay_pair_id: str | None,
    replay_base_seed: int | None,
    replay_generation_seed: int | None,
    prompt_sha256: str | None,
    model_id: str | None,
    model_revision: str | None,
    tokenizer_revision: str | None,
    temperature: float | None,
    max_new_tokens: int | None,
) -> None:
    if replay_pair_id is not None:
        _require_non_empty_str(replay_pair_id, "replay_pair_id")
    if replay_base_seed is not None:
        _require_non_negative_int(replay_base_seed, "replay_base_seed")
    if replay_generation_seed is not None:
        _require_non_negative_int(replay_generation_seed, "replay_generation_seed")
    if prompt_sha256 is not None:
        _validate_sha256(prompt_sha256, "prompt_sha256")
    if model_id is not None:
        _require_non_empty_str(model_id, "model_id")
    if model_revision is not None:
        _require_non_empty_str(model_revision, "model_revision")
    if tokenizer_revision is not None:
        _require_non_empty_str(tokenizer_revision, "tokenizer_revision")
    if temperature is not None:
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            raise TypeError("temperature must be numeric")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")
    if max_new_tokens is not None:
        _require_positive_int(max_new_tokens, "max_new_tokens")


def _validate_condition_hash_mapping(
    value: dict[str, dict[str, str]],
    field_name: str,
    *,
    allowed_conditions: tuple[str, ...],
) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    for condition, hashes in value.items():
        if condition not in allowed_conditions:
            allowed = ", ".join(allowed_conditions)
            raise ValueError(
                f"{field_name} condition {condition!r} must be one of: {allowed}"
            )
        _validate_hash_mapping(
            hashes,
            f"{field_name}[{condition!r}]",
            require_non_empty=True,
        )


def _validate_string_mapping(value: dict[str, str], field_name: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    for key, string_value in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(string_value, str) or not string_value:
            raise ValueError(f"{field_name}[{key!r}] must be a non-empty string")


def _validate_locked_kernel_identity(kernel_class: str, kernel_name: str) -> None:
    if kernel_class not in LOCKED_KERNEL_CLASSES:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise ValueError(f"unsupported kernel_class {kernel_class!r}; allowed: {allowed}")
    _require_non_empty_str(kernel_name, "kernel_name")
    expected_kernel_name = get_shape_metadata(kernel_class).kernel_name
    if kernel_name != expected_kernel_name:
        raise ValueError(
            f"kernel_class {kernel_class!r} requires kernel_name "
            f"{expected_kernel_name!r}; got {kernel_name!r}"
        )


def _require_bool(value: bool, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")


def _require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_non_empty_str(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _require_optional_non_empty_str(value: str | None, field_name: str) -> None:
    if value is None:
        return
    _require_non_empty_str(value, field_name)


def _assert_allowed_result_field_names(instance: object) -> None:
    field_names = {field.name for field in fields(instance)}
    forbidden = sorted(field_names & FORBIDDEN_CLUSTER2_RESULT_FIELDS)
    if forbidden:
        raise ValueError(f"forbidden Cluster 2 result fields: {', '.join(forbidden)}")


def _reject_forbidden_mapping_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key in FORBIDDEN_CLUSTER2_RESULT_FIELDS:
                raise ValueError(f"forbidden Cluster 2 result field: {key}")
            _reject_forbidden_mapping_fields(item)
    elif isinstance(value, list | tuple):
        for item in value:
            _reject_forbidden_mapping_fields(item)
