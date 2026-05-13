"""Registry of factor cells and cluster-specific execution boundaries."""

from __future__ import annotations

from shared.factors.cells import (
    CANONICAL_FACTOR_CELLS,
    FactorCell,
    require_valid_factor_cell,
)
from shared.factors.config import FactorConfig


FACTOR_CONFIGS: dict[FactorCell, FactorConfig] = {
    cell: FactorConfig.from_cell(cell) for cell in CANONICAL_FACTOR_CELLS
}

_CLUSTER_ALLOWED_CELLS: dict[str, tuple[FactorCell, ...]] = {
    "cluster1": ("none", "G"),
    "cluster2": ("none", "G", "C", "G+C"),
    "cluster3": ("P", "G+P", "C+P", "G+C+P"),
}


def allowed_cells_for_cluster(cluster_name: str) -> tuple[FactorCell, ...]:
    """Return the factor cells that ``cluster_name`` is allowed to execute."""

    try:
        return _CLUSTER_ALLOWED_CELLS[cluster_name]
    except KeyError as exc:
        raise ValueError(
            f"unknown cluster {cluster_name!r}; expected one of: "
            f"{', '.join(sorted(_CLUSTER_ALLOWED_CELLS))}"
        ) from exc


def require_cell_allowed_for_cluster(cluster_name: str, cell: str) -> FactorCell:
    """Validate that ``cell`` is canonical and executable by ``cluster_name``."""

    normalized = require_valid_factor_cell(cell)
    allowed = allowed_cells_for_cluster(cluster_name)
    if normalized not in allowed:
        raise ValueError(
            f"factor cell {normalized!r} is not allowed for {cluster_name!r}; "
            f"allowed cells: {', '.join(allowed)}"
        )
    return normalized
