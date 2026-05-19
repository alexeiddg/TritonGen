"""Lightweight provenance helpers for generation rows.

This module is safe to import from local tests and from Modal generation
methods. It must not import torch, transformers, xgrammar, or triton at module
import time.
"""

from __future__ import annotations

import hashlib
import ast
import importlib.metadata as importlib_metadata
import os
import platform
from pathlib import Path
from typing import Any

from shared.generation_metadata import (
    UNKNOWN,
    VALID_REJECTION_LAYERS,
    VALID_STOP_REASONS,
    is_stable_modal_image_identifier,
    modal_image_provenance_digest,
    normalize_immutable_hub_revision,
)

RUNTIME_VERSION_PACKAGES = ("xgrammar", "transformers", "tokenizers")
MODAL_IMAGE_SHA_ENV_VARS = (
    "MODAL_IMAGE_SHA",
    "MODAL_IMAGE_DIGEST",
)
MODAL_IMAGE_ID_ENV_VARS = (
    "MODAL_IMAGE_ID",
    "MODAL_CONTAINER_IMAGE_ID",
)
MODAL_IMAGE_FALLBACK_ENV_VARS = (
    *MODAL_IMAGE_ID_ENV_VARS,
    "MODAL_IMAGE_TAG",
)
MODAL_IMAGE_ENV_VARS = MODAL_IMAGE_SHA_ENV_VARS + MODAL_IMAGE_FALLBACK_ENV_VARS
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODAL_IMAGE_SOURCE_PATH = _REPO_ROOT / "shared" / "modal_harness" / "images.py"


def sha256_file(path: str | Path) -> str:
    """Return SHA-256 over raw file bytes."""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grammar_provenance(
    grammar_path: str | Path | None,
    *,
    grammar_variant: str | None,
) -> dict[str, str | None]:
    """Return row-level grammar provenance for the actual loaded path."""

    if grammar_path is None:
        return {
            "grammar_sha": None,
            "grammar_path": None,
            "grammar_variant": grammar_variant,
        }
    path = Path(grammar_path)
    return {
        "grammar_sha": sha256_file(path),
        "grammar_path": str(path),
        "grammar_variant": grammar_variant,
    }


def runtime_versions() -> dict[str, str]:
    """Return package versions observed in the current Python runtime."""

    return {
        f"{package}_version": _package_version(package)
        for package in RUNTIME_VERSION_PACKAGES
    }


def normalize_explicit_revision(value: str | None, *, field_name: str) -> str | None:
    """Normalize a user-supplied immutable Hub revision.

    Paper metadata must identify immutable model/tokenizer bytes, so explicit
    revisions must be resolved Hub commit SHAs rather than tags or branches.
    """

    return normalize_immutable_hub_revision(value, field_name=field_name)


def resolve_tokenizer_revision(
    *,
    model_id: str,
    model_revision: str | None,
    tokenizer_revision: str | None,
    tokenizer_id: str | None = None,
) -> str | None:
    """Resolve the tokenizer revision requested for C1 generation.

    Cluster 1 loads model and tokenizer from the same Hugging Face repo. When a
    caller pins the model revision but omits a tokenizer revision, using the
    same immutable revision for the tokenizer is explicit same-repo provenance,
    not a post-hoc replacement for missing metadata.
    """

    resolved_model_revision = normalize_explicit_revision(
        model_revision,
        field_name="model_revision",
    )
    resolved_tokenizer_revision = normalize_explicit_revision(
        tokenizer_revision,
        field_name="tokenizer_revision",
    )
    if resolved_tokenizer_revision is not None:
        return resolved_tokenizer_revision
    if resolved_model_revision is None:
        return None
    resolved_tokenizer_id = tokenizer_id or model_id
    if resolved_tokenizer_id == model_id:
        return resolved_model_revision
    return None


def tokenizer_revision_policy(
    *,
    model_id: str,
    model_revision: str | None,
    tokenizer_revision: str | None,
    tokenizer_id: str | None = None,
) -> str:
    """Return a compact label for how tokenizer revision provenance was chosen."""

    if normalize_explicit_revision(
        tokenizer_revision,
        field_name="tokenizer_revision",
    ):
        return "explicit_tokenizer_revision"
    if (
        normalize_explicit_revision(model_revision, field_name="model_revision")
        and (tokenizer_id or model_id) == model_id
    ):
        return "same_repo_model_revision"
    return "best_effort_extraction"


def model_tokenizer_revisions(
    model: Any,
    tokenizer: Any,
    *,
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
) -> dict[str, str]:
    """Return observed model/tokenizer revisions with explicit args as fallback."""

    return {
        "model_revision": _first_known(
            _attribute_chain(model, ("config", "_commit_hash")),
            _attribute_chain(model, ("generation_config", "_commit_hash")),
            getattr(model, "_commit_hash", None),
            model_revision,
        ),
        "tokenizer_revision": extract_tokenizer_revision(
            tokenizer,
            explicit_revision=tokenizer_revision,
        ),
    }


def extract_tokenizer_revision(
    tokenizer: Any,
    explicit_revision: str | None = None,
) -> str:
    """Return tokenizer Hub revision using object metadata before fallback.

    Tokenizer commit metadata is not exposed consistently across pinned
    Transformers versions, so keep the object checks narrow and use the
    explicit loader revision only as a provenance fallback.
    """

    return _first_known(
        _mapping_value(getattr(tokenizer, "init_kwargs", None), "_commit_hash"),
        getattr(tokenizer, "_commit_hash", None),
        explicit_revision,
    )


def modal_image_provenance(
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stable Modal image identifier plus deterministic provenance."""

    fallback_payload = modal_image_provenance_components(extra=extra)
    fallback = modal_image_provenance_digest(fallback_payload)
    modal_image_sha = _first_stable_image_identifier(
        *(os.environ.get(name) for name in MODAL_IMAGE_ID_ENV_VARS),
        *(os.environ.get(name) for name in MODAL_IMAGE_SHA_ENV_VARS),
        fallback,
    )
    return {
        "modal_image_sha": modal_image_sha,
        "modal_image_provenance_sha256": fallback,
        "modal_image_provenance_components": fallback_payload,
    }


def modal_image_provenance_components(
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the deterministic payload used for fallback image provenance."""

    return {
        "schema": "modal_image_fallback_provenance.v1",
        "image_source": _modal_image_source_manifest(),
        "modal_image_env": {
            name: os.environ.get(name)
            for name in MODAL_IMAGE_ENV_VARS
            if os.environ.get(name)
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "runtime_versions": runtime_versions(),
        "extra": extra or {},
    }


def classify_stop_reason(
    *,
    generated_token_ids: list[int] | tuple[int, ...] | None,
    max_new_tokens: int,
    eos_token_id: int | None = None,
    grammar_final_state_observed: bool | None = None,
    stopped_on_grammar_final_state: bool = False,
    error: bool = False,
) -> str:
    """Classify generation termination without claiming unobserved grammar finality."""

    if error:
        return "error"
    if stopped_on_grammar_final_state and grammar_final_state_observed is True:
        return "grammar_final_state"
    token_ids = list(generated_token_ids or [])
    if token_ids and eos_token_id is not None and token_ids[-1] == eos_token_id:
        return "eos_token"
    if max_new_tokens > 0 and len(token_ids) >= max_new_tokens:
        return "max_new_tokens"
    return "unknown"


def validation_payload_or_unknown(exc: BaseException) -> dict[str, Any]:
    """Return a structured validation runtime-error payload."""

    return {
        "gbnf_parse_valid": False,
        "semantic_valid": False,
        "grammar_valid": False,
        "rejection_layer": "runtime_error",
        "validation_error_type": type(exc).__name__,
        "validation_error_msg": str(exc),
    }


def _package_version(package: str) -> str:
    try:
        version = importlib_metadata.version(package)
    except Exception:
        return UNKNOWN
    return version if isinstance(version, str) and version else UNKNOWN


def _first_known(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value and value != UNKNOWN:
            return value
    return UNKNOWN


def _first_stable_image_identifier(*values: object) -> str:
    for value in values:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if is_stable_modal_image_identifier(candidate):
            return candidate
    return UNKNOWN


def _modal_image_source_manifest() -> dict[str, Any]:
    source_path = _MODAL_IMAGE_SOURCE_PATH
    if not source_path.is_file():
        return {
            "path": "shared/modal_harness/images.py",
            "sha256": UNKNOWN,
            "generation_package_pins": [],
        }
    return {
        "path": str(source_path.relative_to(_REPO_ROOT)),
        "sha256": sha256_file(source_path),
        "generation_package_pins": _generation_package_pins(source_path),
    }


def _generation_package_pins(source_path: Path) -> list[str]:
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    pins: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "uv_pip_install":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if "==" in arg.value or "[" in arg.value:
                    pins.add(arg.value)
    return sorted(pins)


def _attribute_chain(obj: Any, names: tuple[str, ...]) -> Any:
    value = obj
    for name in names:
        value = getattr(value, name, None)
        if value is None:
            return None
    return value


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return None
