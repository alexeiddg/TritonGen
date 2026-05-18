"""Canonical Cluster 1 grammar variant to GBNF path mapping."""

from __future__ import annotations

from typing import cast

from cluster1.results.dataclass import (
    DEFAULT_GRAMMAR_VARIANT,
    GrammarVariant,
    VALID_GRAMMAR_VARIANTS,
    validate_grammar_variant_invariants,
)
from shared.generation_metadata import GRAMMAR_PATHS_BY_VARIANT as _SHARED_GRAMMAR_PATHS

TEMPLATE_UPPER_BOUND_GRAMMAR_PATH = _SHARED_GRAMMAR_PATHS["template_upper_bound"]
TASK_AGNOSTIC_GRAMMAR_PATH = _SHARED_GRAMMAR_PATHS["task_agnostic"]

GRAMMAR_PATHS_BY_VARIANT: dict[GrammarVariant, str] = dict(_SHARED_GRAMMAR_PATHS)

DEFAULT_GRAMMAR_PATH = GRAMMAR_PATHS_BY_VARIANT[DEFAULT_GRAMMAR_VARIANT]


def grammar_path_for_variant(grammar_variant: str) -> str:
    """Return the GBNF path selected by an active grammar variant."""

    if grammar_variant not in GRAMMAR_PATHS_BY_VARIANT:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(
            f"invalid grammar_variant {grammar_variant!r}; expected {allowed}"
        )
    return GRAMMAR_PATHS_BY_VARIANT[cast(GrammarVariant, grammar_variant)]


def grammar_path_for_cell(
    *,
    grammar_active: bool,
    grammar_variant: str | None,
) -> str | None:
    """Return the grammar path for one cell, or ``None`` for baseline rows."""

    validate_grammar_variant_invariants(
        grammar_active=grammar_active,
        grammar_variant=grammar_variant,
    )
    if not grammar_active:
        return None
    assert grammar_variant is not None
    return grammar_path_for_variant(grammar_variant)
