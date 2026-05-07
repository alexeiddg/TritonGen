"""Tests for shared factor-cell labels and cluster boundaries."""

from __future__ import annotations

import pytest

from shared.factors import (
    CANONICAL_FACTOR_CELLS,
    FACTOR_CONFIGS,
    FactorConfig,
    allowed_cells_for_cluster,
    factor_cell_parts,
    is_valid_factor_cell,
    normalize_factor_cell,
    require_cell_allowed_for_cluster,
    require_valid_factor_cell,
)


def test_canonical_factor_cells_are_exact() -> None:
    assert CANONICAL_FACTOR_CELLS == (
        "none",
        "G",
        "C",
        "P",
        "G+C",
        "G+P",
        "C+P",
        "G+C+P",
    )


@pytest.mark.parametrize("cell", CANONICAL_FACTOR_CELLS)
def test_canonical_cells_validate(cell: str) -> None:
    assert is_valid_factor_cell(cell)
    assert require_valid_factor_cell(cell) == cell


@pytest.mark.parametrize("bad", ["T", "baseline", "G+T", "", " ", "g", "C+G", "G+G"])
def test_invalid_or_old_factor_cells_rejected(bad: str) -> None:
    assert not is_valid_factor_cell(bad)
    with pytest.raises(ValueError):
        require_valid_factor_cell(bad)


def test_normalize_factor_cell_strips_separator_whitespace_only() -> None:
    assert normalize_factor_cell(" G + C + P ") == "G+C+P"


def test_factor_cell_parts() -> None:
    assert factor_cell_parts("none") == ()
    assert factor_cell_parts("G") == ("G",)
    assert factor_cell_parts("G+C+P") == ("G", "C", "P")


def test_factor_config_round_trips_all_canonical_cells() -> None:
    for cell in CANONICAL_FACTOR_CELLS:
        config = FactorConfig.from_cell(cell)
        assert config.to_cell() == cell
        assert FACTOR_CONFIGS[cell] == config


def test_factor_config_boolean_mapping() -> None:
    assert FactorConfig.from_cell("none") == FactorConfig(
        grammar=False,
        compiler_feedback=False,
        performance_feedback=False,
    )
    assert FactorConfig.from_cell("G+C+P") == FactorConfig(
        grammar=True,
        compiler_feedback=True,
        performance_feedback=True,
    )


def test_cluster_allowed_cells_are_exact() -> None:
    assert allowed_cells_for_cluster("cluster1") == ("none", "G")
    assert allowed_cells_for_cluster("cluster2") == ("none", "C", "G+C")
    assert allowed_cells_for_cluster("cluster3") == ("P", "G+P", "C+P", "G+C+P")


@pytest.mark.parametrize("cell", ["none", "G"])
def test_cluster1_accepts_only_implemented_cells(cell: str) -> None:
    assert require_cell_allowed_for_cluster("cluster1", cell) == cell


@pytest.mark.parametrize("cell", ["C", "P", "G+C", "G+P", "C+P", "G+C+P"])
def test_cluster1_rejects_reserved_cells(cell: str) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        require_cell_allowed_for_cluster("cluster1", cell)


def test_unknown_cluster_rejected() -> None:
    with pytest.raises(ValueError, match="unknown cluster"):
        allowed_cells_for_cluster("cluster4")
