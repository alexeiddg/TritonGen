"""Final structured result schema for Cluster 1 generation experiments."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any, Literal, cast

from shared.generation_metadata import (
    DEFAULT_GRAMMAR_VARIANT,
    GENERATION_METADATA_FIELD_NAMES,
    GENERATION_METADATA_SCHEMA_VERSION,
    GRAMMAR_PATHS_BY_VARIANT,
    GrammarVariant,
    PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES,
    PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES,
    UNKNOWN,
    VALID_GRAMMAR_VARIANTS,
    VALID_REJECTION_LAYERS,
    VALID_STOP_REASONS,
    is_immutable_hub_revision,
    modal_image_provenance_digest,
)


# Task 5.1
CompileErrorType = Literal["CompilationError", "RuntimeError", "SignatureError", None]
_VALID_GRAMMAR_VARIANT_SET = frozenset(VALID_GRAMMAR_VARIANTS)
PAPER_SCALE_METADATA_FIELD_NAMES: tuple[str, ...] = (
    *PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES,
    *PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES,
    "modal_image_sha",
    "modal_image_provenance_sha256",
    "modal_image_provenance_components",
)


# Task 5.2
@dataclass(frozen=True)
class GenerationResult:
    source: str
    model_id: str
    grammar_active: bool
    grammar_variant: GrammarVariant | None
    kernel_class: Literal["elementwise", "reduction", "matmul"]
    kernel_name: str
    dtype: Literal["fp32", "fp16", "bf16"]
    compile_success: bool
    compile_results_by_dtype: dict[str, bool]
    compile_error_type: CompileErrorType
    compile_error_msg: str | None
    masked_token_rate: float | None
    unique_solution_hash: str
    n_shapes_tested: int
    generation_seed: int | None
    temperature: float
    run_id: str
    timestamp_utc: str
    generation_metadata_schema_version: int = 0
    grammar_sha: str | None = None
    grammar_path: str | None = None
    gbnf_parse_valid: bool | None = None
    semantic_valid: bool | None = None
    grammar_valid: bool | None = None
    rejection_layer: str | None = None
    stop_reason: str = UNKNOWN
    xgrammar_version: str = UNKNOWN
    transformers_version: str = UNKNOWN
    tokenizers_version: str = UNKNOWN
    model_revision: str = UNKNOWN
    tokenizer_revision: str = UNKNOWN
    modal_image_sha: str = UNKNOWN
    modal_image_provenance_sha256: str | None = None
    modal_image_provenance_components: dict[str, Any] | None = None


def validate_result_invariants(result: GenerationResult) -> None:
    validate_grammar_variant_invariants(
        grammar_active=result.grammar_active,
        grammar_variant=result.grammar_variant,
    )
    if not result.grammar_active and result.masked_token_rate is not None:
        raise ValueError("masked_token_rate must be None when grammar_active is False")
    if result.grammar_active and result.masked_token_rate is None:
        raise ValueError("masked_token_rate must not be None when grammar_active is True")
    validate_generation_metadata_invariants(result)


def validate_generation_metadata_invariants(result: GenerationResult) -> None:
    """Validate metadata semantics while allowing legacy defaulted rows."""

    if result.stop_reason not in VALID_STOP_REASONS:
        allowed = ", ".join(sorted(VALID_STOP_REASONS))
        raise ValueError(f"stop_reason must be one of {allowed}; got {result.stop_reason!r}")

    if result.rejection_layer is not None and result.rejection_layer not in VALID_REJECTION_LAYERS:
        allowed = ", ".join(sorted(VALID_REJECTION_LAYERS))
        raise ValueError(
            f"rejection_layer must be one of {allowed} or None; "
            f"got {result.rejection_layer!r}"
        )

    validation_values = (
        result.gbnf_parse_valid,
        result.semantic_valid,
        result.grammar_valid,
    )
    if (
        result.grammar_active
        and result.generation_metadata_schema_version >= GENERATION_METADATA_SCHEMA_VERSION
    ):
        missing_current_schema_fields = [
            field_name
            for field_name in (
                "grammar_variant",
                "grammar_sha",
                "grammar_path",
                "gbnf_parse_valid",
                "semantic_valid",
                "grammar_valid",
            )
            if getattr(result, field_name) is None
        ]
        if missing_current_schema_fields:
            missing = ", ".join(sorted(missing_current_schema_fields))
            raise ValueError(
                "current-schema grammar-active GenerationResult requires "
                f"generation metadata: {missing}"
            )
    if all(value is not None for value in validation_values):
        expected = bool(result.gbnf_parse_valid and result.semantic_valid)
        if result.grammar_valid is not expected:
            raise ValueError(
                "grammar_valid must equal gbnf_parse_valid and semantic_valid"
            )
        if result.grammar_valid and result.rejection_layer is not None:
            raise ValueError("rejection_layer must be None when grammar_valid=True")
        if not result.grammar_valid and result.rejection_layer is None:
            raise ValueError("rejection_layer is required when grammar_valid=False")

    if not result.grammar_active:
        if any(value is not None for value in validation_values):
            raise ValueError(
                "grammar validation fields must be None when grammar_active is False"
            )
        if result.grammar_sha is not None:
            raise ValueError("grammar_sha must be None when grammar_active is False")
        if result.grammar_path is not None:
            raise ValueError("grammar_path must be None when grammar_active is False")
    elif result.grammar_path is not None and result.grammar_variant is not None:
        validate_grammar_path_variant_invariants(
            grammar_path=result.grammar_path,
            grammar_variant=result.grammar_variant,
        )
    if (
        result.generation_metadata_schema_version >= GENERATION_METADATA_SCHEMA_VERSION
        and result.modal_image_sha in (None, UNKNOWN)
    ):
        if not result.modal_image_provenance_sha256:
            raise ValueError(
                "current-schema GenerationResult with unknown modal_image_sha "
                "requires modal_image_sha_or_modal_image_provenance_sha256"
            )
        if result.modal_image_provenance_components is None:
            raise ValueError(
                "current-schema GenerationResult with unknown modal_image_sha "
                "requires modal_image_provenance_components"
            )
    validate_modal_image_provenance_invariants(
        modal_image_provenance_sha256=result.modal_image_provenance_sha256,
        modal_image_provenance_components=result.modal_image_provenance_components,
    )


def validate_paper_scale_metadata(result: GenerationResult) -> None:
    """Reject rows that cannot satisfy the paper-scale metadata gate."""

    validate_generation_metadata_invariants(result)

    missing = []
    required_fields = list(PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES)
    if result.grammar_active:
        required_fields.extend(PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES)
    for field_name in required_fields:
        value = getattr(result, field_name)
        if value is None or value == UNKNOWN:
            missing.append(field_name)
    malformed = []
    if result.grammar_active and result.grammar_sha is not None:
        _append_if_not_sha256_hex(malformed, "grammar_sha", result.grammar_sha)
    if result.model_revision not in (None, UNKNOWN):
        _append_if_not_immutable_hub_revision(
            malformed,
            "model_revision",
            result.model_revision,
        )
    if result.tokenizer_revision not in (None, UNKNOWN):
        _append_if_not_immutable_hub_revision(
            malformed,
            "tokenizer_revision",
            result.tokenizer_revision,
        )
    if result.modal_image_sha not in (None, UNKNOWN):
        _append_if_not_stable_image_sha(
            malformed,
            "modal_image_sha",
            result.modal_image_sha,
        )
    if result.modal_image_provenance_sha256 is not None:
        _append_if_not_sha256_hex(
            malformed,
            "modal_image_provenance_sha256",
            result.modal_image_provenance_sha256,
        )
    if result.modal_image_sha in (None, UNKNOWN) and not result.modal_image_provenance_sha256:
        missing.append("modal_image_sha_or_modal_image_provenance_sha256")
    if (
        result.modal_image_sha in (None, UNKNOWN)
        and result.modal_image_provenance_components is None
    ):
        missing.append("modal_image_provenance_components")
    if result.modal_image_provenance_components is not None:
        try:
            validate_modal_image_provenance_invariants(
                modal_image_provenance_sha256=result.modal_image_provenance_sha256,
                modal_image_provenance_components=(
                    result.modal_image_provenance_components
                ),
            )
        except ValueError:
            malformed.append("modal_image_provenance_components_mismatch")
    if result.generation_metadata_schema_version < GENERATION_METADATA_SCHEMA_VERSION:
        missing.append("generation_metadata_schema_version")
    if missing or malformed:
        problems = sorted(set(missing)) + sorted(set(malformed))
        raise ValueError(
            "paper-scale rows require generation metadata: "
            + ", ".join(problems)
        )


def _append_if_not_sha256_hex(
    failures: list[str],
    field_name: str,
    value: str,
) -> None:
    if len(value) != 64:
        failures.append(f"{field_name}_malformed")
        return
    try:
        int(value, 16)
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


def validate_modal_image_provenance_invariants(
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
    if len(modal_image_provenance_sha256) != 64:
        raise ValueError(
            "modal_image_provenance_sha256_malformed: "
            "modal_image_provenance_sha256 must be a 64-character SHA256 hex digest"
        )
    try:
        int(modal_image_provenance_sha256, 16)
    except ValueError as exc:
        raise ValueError(
            "modal_image_provenance_sha256_malformed: "
            "modal_image_provenance_sha256 must be a SHA256 hex digest"
        ) from exc
    expected = modal_image_provenance_digest(modal_image_provenance_components)
    if modal_image_provenance_sha256 != expected:
        raise ValueError(
            "modal_image_provenance_sha256 must equal the digest of "
            "modal_image_provenance_components"
        )


def validate_grammar_variant_invariants(
    *,
    grammar_active: bool,
    grammar_variant: str | None,
    factor_cell: str | None = None,
) -> None:
    if factor_cell == "none" and grammar_active:
        raise ValueError("factor_cell='none' requires grammar_active=False")
    if factor_cell == "none" and grammar_variant is not None:
        raise ValueError("factor_cell='none' requires grammar_variant=None")
    if factor_cell == "G" and not grammar_active:
        raise ValueError("factor_cell='G' requires grammar_active=True")

    if not grammar_active:
        if grammar_variant is not None:
            raise ValueError("grammar_variant must be None when grammar_active is False")
        return

    if grammar_variant not in _VALID_GRAMMAR_VARIANT_SET:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(
            "grammar_variant must be one of "
            f"{allowed} when grammar_active is True; got {grammar_variant!r}"
        )


def validate_grammar_path_variant_invariants(
    *,
    grammar_path: str,
    grammar_variant: str,
) -> None:
    if grammar_variant not in _VALID_GRAMMAR_VARIANT_SET:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(f"invalid grammar_variant {grammar_variant!r}; expected {allowed}")
    expected_path = GRAMMAR_PATHS_BY_VARIANT[cast(GrammarVariant, grammar_variant)]
    normalized_path = grammar_path.replace("\\", "/")
    if normalized_path != expected_path and not normalized_path.endswith(
        "/" + expected_path
    ):
        raise ValueError(
            "grammar_path does not match grammar_variant: "
            f"{grammar_variant!r} expects {expected_path!r}; got {grammar_path!r}"
        )


def default_grammar_variant_for_active_grammar(
    grammar_variant: str | None = None,
) -> GrammarVariant:
    """Return the active-grammar variant, preserving the current G default."""

    if grammar_variant is None:
        return DEFAULT_GRAMMAR_VARIANT
    if grammar_variant not in _VALID_GRAMMAR_VARIANT_SET:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(f"invalid grammar_variant {grammar_variant!r}; expected {allowed}")
    return cast(GrammarVariant, grammar_variant)


def grammar_variant_for_cell(
    *,
    factor_cell: str,
    grammar_active: bool,
    grammar_variant: str | None = None,
) -> GrammarVariant | None:
    resolved = (
        default_grammar_variant_for_active_grammar(grammar_variant)
        if grammar_active
        else grammar_variant
    )
    validate_grammar_variant_invariants(
        factor_cell=factor_cell,
        grammar_active=grammar_active,
        grammar_variant=resolved,
    )
    return resolved


def generation_result_record_for_deserialization(
    record: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy with legacy generation metadata filled in memory."""

    updated = dict(record)
    if "grammar_variant" not in updated:
        updated["grammar_variant"] = (
            DEFAULT_GRAMMAR_VARIANT if updated.get("grammar_active") is True else None
        )
    updated.setdefault("generation_metadata_schema_version", 0)
    updated.setdefault("grammar_sha", None)
    updated.setdefault("grammar_path", None)
    updated.setdefault("gbnf_parse_valid", None)
    updated.setdefault("semantic_valid", None)
    updated.setdefault("grammar_valid", None)
    updated.setdefault("rejection_layer", None)
    updated.setdefault("stop_reason", UNKNOWN)
    updated.setdefault("xgrammar_version", UNKNOWN)
    updated.setdefault("transformers_version", UNKNOWN)
    updated.setdefault("tokenizers_version", UNKNOWN)
    updated.setdefault("model_revision", UNKNOWN)
    updated.setdefault("tokenizer_revision", UNKNOWN)
    updated.setdefault("modal_image_sha", UNKNOWN)
    updated.setdefault("modal_image_provenance_sha256", None)
    updated.setdefault("modal_image_provenance_components", None)
    return updated


# Task 5.3
def compute_unique_solution_hash(source: str) -> str:
    try:
        tree = ast.parse(source)
        normalized = ast.unparse(tree)
    except SyntaxError:
        normalized = " ".join(source.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
