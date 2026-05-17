"""Phase 13 reporting helpers."""

from shared.eval.reporting.coverage_table import build_coverage_table
from shared.eval.reporting.grammar_language import (
    assert_paper_facing_grammar_language,
    grammar_condition_label,
    grammar_variant_label,
)
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
    "assert_paper_facing_grammar_language",
    "grammar_condition_label",
    "grammar_variant_label",
    "render_markdown_table",
]
