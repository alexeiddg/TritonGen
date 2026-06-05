from __future__ import annotations

import pytest

from shared.factors.grammar_modes import (
    GRAMMAR_MODE_VALUES,
    grammar_mode_config,
    grammar_mode_from_active_variant,
    normalize_grammar_mode,
    validate_grammar_mode_binding,
)


def test_grammar_mode_values_are_exact() -> None:
    assert GRAMMAR_MODE_VALUES == (
        "grammar_off",
        "template_upper_bound",
        "task_agnostic",
    )


@pytest.mark.parametrize("grammar_mode", GRAMMAR_MODE_VALUES)
def test_grammar_mode_config_maps_supported_values(grammar_mode: str) -> None:
    config = grammar_mode_config(grammar_mode)
    assert config.grammar_mode == grammar_mode
    if grammar_mode == "grammar_off":
        assert config.grammar_active is False
        assert config.grammar_variant is None
        assert config.grammar_path is None
        assert config.grammar_claim_scope is None
    else:
        assert config.grammar_active is True
        assert config.grammar_variant == grammar_mode
        assert config.grammar_path is not None
        assert config.grammar_claim_scope in {"primary", "diagnostic_non_primary"}


def test_invalid_grammar_mode_rejected() -> None:
    with pytest.raises(ValueError, match="grammar_mode"):
        normalize_grammar_mode("primary_grammar")


def test_grammar_mode_from_legacy_active_variant_fields() -> None:
    assert (
        grammar_mode_from_active_variant(
            grammar_active=False,
            grammar_variant=None,
        )
        == "grammar_off"
    )
    assert (
        grammar_mode_from_active_variant(
            grammar_active=True,
            grammar_variant="template_upper_bound",
        )
        == "template_upper_bound"
    )


def test_grammar_mode_invalid_combinations_fail_closed() -> None:
    with pytest.raises(ValueError, match="grammar_variant"):
        grammar_mode_from_active_variant(
            grammar_active=False,
            grammar_variant="task_agnostic",
        )
    with pytest.raises(ValueError, match="active grammar"):
        grammar_mode_from_active_variant(
            grammar_active=True,
            grammar_variant=None,
        )
    with pytest.raises(ValueError, match="grammar_active"):
        validate_grammar_mode_binding(
            grammar_mode="grammar_off",
            grammar_active=True,
            grammar_variant=None,
        )
    with pytest.raises(ValueError, match="grammar_variant"):
        validate_grammar_mode_binding(
            grammar_mode="task_agnostic",
            grammar_active=True,
            grammar_variant="template_upper_bound",
        )
