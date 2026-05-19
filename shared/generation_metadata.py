"""Lightweight generation metadata constants shared by C1/C2 contracts.

This module is intentionally dependency-free. It is safe for Modal schemas to
import because it does not load Modal, generation, evaluation, Torch, Triton,
transformers, xgrammar, or Cluster 1 runtime modules.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal, TypeAlias


UNKNOWN = "unknown"
HUB_COMMIT_SHA_LENGTH = 40
_HUB_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_MODAL_IMAGE_OBJECT_ID_RE = re.compile(r"^im-[A-Za-z0-9]+$")

GrammarVariant: TypeAlias = Literal["template_upper_bound", "task_agnostic"]
DEFAULT_GRAMMAR_VARIANT: GrammarVariant = "template_upper_bound"
VALID_GRAMMAR_VARIANTS: tuple[GrammarVariant, ...] = (
    "template_upper_bound",
    "task_agnostic",
)

GRAMMAR_PATHS_BY_VARIANT: dict[GrammarVariant, str] = {
    "template_upper_bound": "cluster1/grammar/triton_kernel.gbnf",
    "task_agnostic": "cluster1/grammar/triton_kernel_agnostic.gbnf",
}

GRAMMAR_CLAIM_SCOPE_BY_VARIANT: dict[GrammarVariant, str] = {
    "template_upper_bound": "diagnostic_non_primary",
    "task_agnostic": "primary",
}

VALID_REJECTION_LAYERS = frozenset(
    {
        "python_ast",
        "gbnf_parse",
        "semantic_validator",
        "runtime_error",
        "unknown",
    }
)

VALID_STOP_REASONS = frozenset(
    {
        "grammar_final_state",
        "max_new_tokens",
        "eos_token",
        "error",
        "unknown",
    }
)

GENERATION_METADATA_SCHEMA_VERSION = 1
CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION = GENERATION_METADATA_SCHEMA_VERSION

GRAMMAR_METADATA_FIELD_NAMES: tuple[str, ...] = (
    "grammar_sha",
    "grammar_path",
    "grammar_variant",
    "gbnf_parse_valid",
    "semantic_valid",
    "grammar_valid",
    "rejection_layer",
)

RUNTIME_METADATA_FIELD_NAMES: tuple[str, ...] = (
    "stop_reason",
    "xgrammar_version",
    "transformers_version",
    "tokenizers_version",
    "model_revision",
    "tokenizer_revision",
    "modal_image_sha",
    "modal_image_provenance_sha256",
    "modal_image_provenance_components",
)

GENERATION_METADATA_FIELD_NAMES: tuple[str, ...] = (
    *GRAMMAR_METADATA_FIELD_NAMES,
    *RUNTIME_METADATA_FIELD_NAMES,
)

PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES: tuple[str, ...] = (
    "stop_reason",
    "xgrammar_version",
    "transformers_version",
    "tokenizers_version",
    "model_revision",
    "tokenizer_revision",
)

PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES: tuple[str, ...] = (
    "grammar_sha",
    "grammar_path",
    "grammar_variant",
    "gbnf_parse_valid",
    "semantic_valid",
    "grammar_valid",
)

MODAL_IMAGE_PROVENANCE_COMPONENTS_FIELD = "modal_image_provenance_components"


def canonical_metadata_json(payload: Any) -> str:
    """Serialize metadata evidence with deterministic JSON settings."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def modal_image_provenance_digest(components: dict[str, Any]) -> str:
    """Return the fallback Modal image provenance digest for stored components."""

    if not isinstance(components, dict) or not components:
        raise ValueError("modal_image_provenance_components must be a non-empty dict")
    return hashlib.sha256(
        canonical_metadata_json(components).encode("utf-8")
    ).hexdigest()


def is_immutable_hub_revision(value: object) -> bool:
    """Return True only for immutable Hugging Face Git commit revisions."""

    return isinstance(value, str) and _HUB_COMMIT_SHA_RE.fullmatch(value) is not None


def is_stable_modal_image_identifier(value: object) -> bool:
    """Return True for stable Modal image provenance identifiers."""

    if not isinstance(value, str):
        return False
    return (
        _SHA256_HEX_RE.fullmatch(value) is not None
        or _SHA256_DIGEST_RE.fullmatch(value) is not None
        or _MODAL_IMAGE_OBJECT_ID_RE.fullmatch(value) is not None
    )


def normalize_immutable_hub_revision(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    """Normalize an optional user-supplied immutable Hugging Face revision."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or None")
    revision = value.strip()
    if not revision:
        return None
    if not is_immutable_hub_revision(revision):
        raise ValueError(
            f"{field_name} must be an immutable revision: a "
            f"{HUB_COMMIT_SHA_LENGTH}-character Hub commit SHA, not {revision!r}"
        )
    return revision
