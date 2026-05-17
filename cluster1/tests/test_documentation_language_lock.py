"""Documentation guard for grammar-attribution language."""

from __future__ import annotations

from pathlib import Path

from shared.eval.reporting.grammar_language import (
    find_paper_facing_grammar_language_violations,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_FACING_DOCS = (
    REPO_ROOT / ".contracts/research/research_scope.md",
    REPO_ROOT / ".contracts/research/cluster1_generated_surface.md",
    REPO_ROOT / ".contracts/research/eval_metrics.md",
    REPO_ROOT / ".contracts/research/scale_policy.md",
    REPO_ROOT / "cluster1/README.md",
    REPO_ROOT / "README.md",
)


def test_committed_docs_lock_primary_and_reference_grammar_roles() -> None:
    research_scope = (REPO_ROOT / ".contracts/research/research_scope.md").read_text(
        encoding="utf-8"
    )
    cluster1_readme = (REPO_ROOT / "cluster1/README.md").read_text(
        encoding="utf-8"
    )
    durable_text = f"{research_scope}\n{cluster1_readme}".lower()

    assert "task-agnostic g is the primary grammar condition" in durable_text
    assert "template g is a diagnostic/reference upper bound" in durable_text
    assert "template g is not used as the primary grammar-effect estimate" in durable_text


def test_paper_facing_docs_qualify_template_grammar_lines() -> None:
    violations: list[str] = []
    for path in PAPER_FACING_DOCS:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line_violations = find_paper_facing_grammar_language_violations((line,))
            violations.extend(
                f"{path.relative_to(REPO_ROOT)}:{line_number}: {violation}"
                for violation in line_violations
            )

    assert violations == []
