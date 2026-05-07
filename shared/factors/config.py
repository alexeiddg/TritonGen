"""Factor-cell configuration objects."""

from __future__ import annotations

from dataclasses import dataclass

from typing import cast

from shared.factors.cells import FactorCell, factor_cell_parts


@dataclass(frozen=True)
class FactorConfig:
    """Boolean expansion of one factorial condition."""

    grammar: bool
    compiler_feedback: bool
    performance_feedback: bool

    @classmethod
    def from_cell(cls, cell: str) -> "FactorConfig":
        parts = set(factor_cell_parts(cell))
        return cls(
            grammar="G" in parts,
            compiler_feedback="C" in parts,
            performance_feedback="P" in parts,
        )

    def to_cell(self) -> FactorCell:
        parts: list[str] = []
        if self.grammar:
            parts.append("G")
        if self.compiler_feedback:
            parts.append("C")
        if self.performance_feedback:
            parts.append("P")
        if not parts:
            return "none"
        return cast(FactorCell, "+".join(parts))
