"""Grammar-mode labels for designs that split G by grammar variant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from shared.generation_metadata import (
    GRAMMAR_CLAIM_SCOPE_BY_VARIANT,
    GRAMMAR_PATHS_BY_VARIANT,
    VALID_GRAMMAR_VARIANTS,
)


GrammarMode: TypeAlias = Literal[
    "grammar_off",
    "template_upper_bound",
    "task_agnostic",
]

GRAMMAR_OFF_MODE: GrammarMode = "grammar_off"
GRAMMAR_MODE_VALUES: tuple[GrammarMode, ...] = (
    GRAMMAR_OFF_MODE,
    "template_upper_bound",
    "task_agnostic",
)
ACTIVE_GRAMMAR_MODES: tuple[GrammarMode, ...] = (
    "template_upper_bound",
    "task_agnostic",
)


@dataclass(frozen=True)
class GrammarModeConfig:
    """Boolean and metadata expansion for one grammar mode."""

    grammar_mode: GrammarMode
    grammar_active: bool
    grammar_variant: str | None
    grammar_path: str | None
    grammar_claim_scope: str | None


def normalize_grammar_mode(value: str) -> GrammarMode:
    """Return a supported grammar mode or raise ``ValueError``."""

    if not isinstance(value, str):
        raise TypeError("grammar_mode must be a string")
    normalized = value.strip()
    if normalized not in GRAMMAR_MODE_VALUES:
        raise ValueError(
            f"grammar_mode must be one of: {', '.join(GRAMMAR_MODE_VALUES)}; "
            f"got {value!r}"
        )
    return cast(GrammarMode, normalized)


def grammar_mode_config(grammar_mode: str) -> GrammarModeConfig:
    """Return the activation and metadata mapping for ``grammar_mode``."""

    mode = normalize_grammar_mode(grammar_mode)
    if mode == GRAMMAR_OFF_MODE:
        return GrammarModeConfig(
            grammar_mode=mode,
            grammar_active=False,
            grammar_variant=None,
            grammar_path=None,
            grammar_claim_scope=None,
        )
    return GrammarModeConfig(
        grammar_mode=mode,
        grammar_active=True,
        grammar_variant=mode,
        grammar_path=GRAMMAR_PATHS_BY_VARIANT[mode],
        grammar_claim_scope=GRAMMAR_CLAIM_SCOPE_BY_VARIANT[mode],
    )


def grammar_mode_from_active_variant(
    *,
    grammar_active: bool,
    grammar_variant: str | None,
) -> GrammarMode:
    """Derive a grammar mode from legacy ``grammar_active``/variant fields."""

    if not isinstance(grammar_active, bool):
        raise TypeError("grammar_active must be a bool")
    if not grammar_active:
        if grammar_variant is not None:
            raise ValueError(
                "grammar_off requires grammar_variant=None when grammar_active=False"
            )
        return GRAMMAR_OFF_MODE
    if grammar_variant not in VALID_GRAMMAR_VARIANTS:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(
            "active grammar rows require grammar_variant to be one of: "
            f"{allowed}; got {grammar_variant!r}"
        )
    return cast(GrammarMode, grammar_variant)


def validate_grammar_mode_binding(
    *,
    grammar_mode: str,
    grammar_active: bool,
    grammar_variant: str | None,
    grammar_path: str | None = None,
    grammar_claim_scope: str | None = None,
) -> GrammarMode:
    """Validate that explicit mode and legacy grammar metadata agree."""

    mode = normalize_grammar_mode(grammar_mode)
    config = grammar_mode_config(mode)
    if grammar_active is not config.grammar_active:
        raise ValueError("grammar_mode does not match grammar_active")
    if grammar_variant != config.grammar_variant:
        raise ValueError("grammar_mode does not match grammar_variant")
    if (
        grammar_path is not None
        and grammar_path != config.grammar_path
        and not str(grammar_path).endswith(str(config.grammar_path))
    ):
        raise ValueError("grammar_mode does not match grammar_path")
    if (
        grammar_claim_scope is not None
        and grammar_claim_scope != config.grammar_claim_scope
    ):
        raise ValueError("grammar_mode does not match grammar_claim_scope")
    return mode
