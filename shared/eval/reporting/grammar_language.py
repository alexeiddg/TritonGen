"""Locked grammar-attribution language for paper-facing reporting."""

from __future__ import annotations

import re
from collections.abc import Iterable


TEMPLATE_GRAMMAR_VARIANT = "template_upper_bound"
TASK_AGNOSTIC_GRAMMAR_VARIANT = "task_agnostic"

TEMPLATE_GRAMMAR_LABEL = "template G reference"
TASK_AGNOSTIC_GRAMMAR_LABEL = "task-agnostic G"
MISSING_GRAMMAR_VARIANT_LABEL = "G (missing grammar variant)"

_TEMPLATE_MARKER_RE = re.compile(
    r"template_upper_bound"
    r"|grammar_variant\s*=\s*template_upper_bound"
    r"|template[- ]G\b"
    r"|template[- ]grammar\b"
    r"|template\s+grammar\b",
    re.IGNORECASE,
)
_TEMPLATE_QUALIFIER_RE = re.compile(
    r"\breference\b|_reference\b|\bdiagnostic\b|_diagnostic\b|\bupper[- ]bound\b",
    re.IGNORECASE,
)
_AMBIGUOUS_G_RE = re.compile(
    r"(?<![A-Za-z0-9_+`])G(?![A-Za-z0-9_+`])\s+"
    r"(?:result|results|row|rows|condition|compile|compile rate|success|"
    r"summary|cell|comparison|replay|control)\b",
    re.IGNORECASE,
)
_ATTRIBUTED_G_RE = re.compile(
    r"\btask[- ]agnostic\s+G\b"
    r"|\btemplate[- ]G\b.*(?:\breference\b|\bdiagnostic\b|\bupper[- ]bound\b)",
    re.IGNORECASE,
)


class GrammarLanguageError(ValueError):
    """Raised when paper-facing grammar attribution is ambiguous."""


def grammar_variant_label(grammar_variant: str | None) -> str:
    """Return the paper-facing label for a grammar variant value."""

    if grammar_variant is None:
        return "none"
    if grammar_variant == TASK_AGNOSTIC_GRAMMAR_VARIANT:
        return TASK_AGNOSTIC_GRAMMAR_LABEL
    if grammar_variant == TEMPLATE_GRAMMAR_VARIANT:
        return TEMPLATE_GRAMMAR_LABEL
    return str(grammar_variant)


def grammar_variant_metadata_label(grammar_variant: str | None) -> str:
    """Return a metadata-preserving label with locked attribution language."""

    if grammar_variant is None:
        return "None"
    if grammar_variant == TASK_AGNOSTIC_GRAMMAR_VARIANT:
        return f"{TASK_AGNOSTIC_GRAMMAR_VARIANT} ({TASK_AGNOSTIC_GRAMMAR_LABEL} primary)"
    if grammar_variant == TEMPLATE_GRAMMAR_VARIANT:
        return f"{TEMPLATE_GRAMMAR_VARIANT} reference ({TEMPLATE_GRAMMAR_LABEL})"
    return str(grammar_variant)


def grammar_condition_label(condition: str, grammar_variant: str | None = None) -> str:
    """Return a condition label with the G factor attributed when present."""

    parts = condition.split("+")
    if "G" not in parts:
        return condition
    labels = [
        (
            MISSING_GRAMMAR_VARIANT_LABEL
            if grammar_variant is None
            else grammar_variant_label(grammar_variant)
        )
        if part == "G"
        else part
        for part in parts
    ]
    separator = " + " if any(" " in part for part in labels) else "+"
    return separator.join(labels)


def grammar_condition_label_for_variants(
    condition: str,
    grammar_variants: Iterable[str | None],
) -> str:
    """Return a condition label from the variants represented by a row subset."""

    variant_values = tuple(grammar_variants)
    variants = tuple(
        sorted({variant for variant in variant_values if variant is not None})
    )
    if not variants:
        return grammar_condition_label(condition)
    if "G" in condition.split("+") and any(
        variant is None for variant in variant_values
    ):
        if TEMPLATE_GRAMMAR_VARIANT in variants:
            base_label = grammar_condition_label(condition, TEMPLATE_GRAMMAR_VARIANT)
        else:
            base_label = grammar_condition_label(condition, variants[0])
        return base_label + " mixed with missing grammar variant"
    if len(variants) == 1:
        return grammar_condition_label(condition, variants[0])
    if TEMPLATE_GRAMMAR_VARIANT in variants:
        return grammar_condition_label(condition, TEMPLATE_GRAMMAR_VARIANT) + " mixed"
    return grammar_condition_label(condition, variants[0]) + " mixed"


def assert_paper_facing_grammar_language(text: str) -> None:
    """Raise when grammar-attribution wording is unsafe for reports or docs."""

    violations = find_paper_facing_grammar_language_violations((text,))
    if violations:
        raise GrammarLanguageError(violations[0])


def find_paper_facing_grammar_language_violations(
    strings: Iterable[str],
) -> tuple[str, ...]:
    """Return every grammar-attribution language violation in ``strings``."""

    violations: list[str] = []
    for text in strings:
        for line in text.splitlines() or [text]:
            has_template_marker = _TEMPLATE_MARKER_RE.search(line)
            has_template_qualifier = _TEMPLATE_QUALIFIER_RE.search(line)
            if has_template_marker and not has_template_qualifier:
                violations.append(
                    "template G language must include reference, diagnostic, or upper-bound "
                    f"qualifier: {line!r}"
                )
                continue
            if _AMBIGUOUS_G_RE.search(line) and not _ATTRIBUTED_G_RE.search(line):
                violations.append(
                    "grammar result language must identify task-agnostic G or template G "
                    f"reference/diagnostic role: {line!r}"
                )
    return tuple(violations)
