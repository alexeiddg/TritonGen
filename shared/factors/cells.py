"""Canonical labels for the TritonGen 2^3 factor cells."""

from __future__ import annotations

from typing import Literal, TypeAlias, cast


FactorCell: TypeAlias = Literal[
    "none",
    "G",
    "C",
    "P",
    "G+C",
    "G+P",
    "C+P",
    "G+C+P",
]
FactorPart: TypeAlias = Literal["G", "C", "P"]

CANONICAL_FACTOR_CELLS: tuple[FactorCell, ...] = (
    "none",
    "G",
    "C",
    "P",
    "G+C",
    "G+P",
    "C+P",
    "G+C+P",
)
FACTOR_PARTS: tuple[FactorPart, ...] = ("G", "C", "P")

_CANONICAL_SET = frozenset(CANONICAL_FACTOR_CELLS)
_FACTOR_PART_SET = frozenset(FACTOR_PARTS)


def normalize_factor_cell(cell: str) -> FactorCell:
    """Return a canonical factor-cell label or raise ``ValueError``.

    Normalization is intentionally narrow: surrounding whitespace and
    whitespace around ``+`` separators are removed, but factor order and case
    must already match the canonical labels.
    """

    if not isinstance(cell, str):
        raise TypeError("factor cell must be a string")

    stripped = cell.strip()
    if not stripped:
        raise ValueError("factor cell must not be empty")

    normalized = "+".join(part.strip() for part in stripped.split("+"))
    if normalized not in _CANONICAL_SET:
        raise ValueError(
            f"invalid factor cell {cell!r}; expected one of: "
            f"{', '.join(CANONICAL_FACTOR_CELLS)}"
        )
    return cast(FactorCell, normalized)


def is_valid_factor_cell(cell: object) -> bool:
    """Return whether ``cell`` is a valid canonical factor-cell label."""

    if not isinstance(cell, str):
        return False
    try:
        normalize_factor_cell(cell)
    except ValueError:
        return False
    return True


def require_valid_factor_cell(cell: str) -> FactorCell:
    """Validate and return ``cell`` as a ``FactorCell``."""

    return normalize_factor_cell(cell)


def factor_cell_parts(cell: str) -> tuple[FactorPart, ...]:
    """Return factor symbols present in ``cell``.

    ``none`` has no active factor parts and returns an empty tuple.
    """

    normalized = require_valid_factor_cell(cell)
    if normalized == "none":
        return ()
    parts = tuple(normalized.split("+"))
    invalid_parts = [part for part in parts if part not in _FACTOR_PART_SET]
    if invalid_parts:
        raise ValueError(f"invalid factor part(s): {', '.join(invalid_parts)}")
    return cast(tuple[FactorPart, ...], parts)
