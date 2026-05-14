"""Phase 13 reporting helpers."""

from shared.eval.reporting.coverage_table import build_coverage_table
from shared.eval.reporting.tables import (
    PRIMARY_COMPARISON_LABEL,
    SECONDARY_COMPARISON_LABEL,
    build_convergence_table,
    build_lift_table,
    comparison_label,
    render_markdown_table,
)

__all__ = [
    "PRIMARY_COMPARISON_LABEL",
    "SECONDARY_COMPARISON_LABEL",
    "build_convergence_table",
    "build_coverage_table",
    "build_lift_table",
    "comparison_label",
    "render_markdown_table",
]
