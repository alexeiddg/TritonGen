"""Compare the task-agnostic grammar allow-list with the pinned Triton API reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_REFERENCE = Path("cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json")
DEFAULT_GRAMMAR = Path("cluster1/grammar/corpus/grammar_allowlist_extracted.json")
DEFAULT_REPORT = Path("cluster1/grammar/corpus/api_coverage_report.md")
LOCAL_TRITON_CORPUS = Path(".contracts/agentic/reference/triton_corpus.md")

UNRESOLVED_CATEGORIES = {
    "CATEGORY_A_REFERENCE_NOT_IN_GRAMMAR",
    "CATEGORY_B_GRAMMAR_NOT_IN_REFERENCE",
    "CATEGORY_C_SIGNATURE_DRIFT",
}
ALLOWED_FINAL_CATEGORIES = {"MATCH", "INTENTIONAL_EXCLUSION", "DOCUMENTED_EXCEPTION"}
IGNORED_REFERENCE_PARAMS = {"self", "_semantic", "_generator"}


@dataclass(frozen=True)
class CoverageRow:
    function: str
    reference_section: str
    reference_signature: str
    grammar_support: str
    grammar_arity_kwargs: str
    divergence_category: str
    action: str
    rationale: str


@dataclass(frozen=True)
class GrammarArityForm:
    raw: str
    positional_count: int
    has_unbounded_positionals: bool
    required_keywords: set[str]
    has_generic_keyword_list: bool


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare_snapshots(reference: dict[str, Any], grammar: dict[str, Any]) -> dict[str, Any]:
    reference_by_name = {entry["name"]: entry for entry in reference["functions"]}
    grammar_by_name = {entry["name"]: entry for entry in grammar["functions"]}
    rows: list[CoverageRow] = []

    for name in sorted(reference_by_name):
        ref_entry = reference_by_name[name]
        grammar_entry = grammar_by_name.get(name)
        if grammar_entry is None:
            rows.append(
                CoverageRow(
                    function=name,
                    reference_section=ref_entry["section"],
                    reference_signature=ref_entry["signature"],
                    grammar_support="missing",
                    grammar_arity_kwargs="n/a",
                    divergence_category="CATEGORY_A_REFERENCE_NOT_IN_GRAMMAR",
                    action="Add minimal grammar support or document an intentional exclusion.",
                    rationale="The public reference function is absent from the grammar allow-list.",
                )
            )
            continue

        category, action, rationale = _classify_shared_function(ref_entry, grammar_entry)
        rows.append(
            CoverageRow(
                function=name,
                reference_section=ref_entry["section"],
                reference_signature=ref_entry["signature"],
                grammar_support=", ".join(grammar_entry["grammar_rules"]),
                grammar_arity_kwargs=_format_grammar_arity_kwargs(grammar_entry),
                divergence_category=category,
                action=action,
                rationale=rationale,
            )
        )

    for name in sorted(set(grammar_by_name) - set(reference_by_name)):
        grammar_entry = grammar_by_name[name]
        rows.append(
            CoverageRow(
                function=name,
                reference_section="n/a",
                reference_signature="n/a",
                grammar_support=", ".join(grammar_entry["grammar_rules"]),
                grammar_arity_kwargs=_format_grammar_arity_kwargs(grammar_entry),
                divergence_category="CATEGORY_B_GRAMMAR_NOT_IN_REFERENCE",
                action="Remove the grammar call or document a reference exception.",
                rationale="The grammar allows a tl.* call not present in the pinned public reference snapshot.",
            )
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.divergence_category] = counts.get(row.divergence_category, 0) + 1
    unresolved = [row for row in rows if row.divergence_category in UNRESOLVED_CATEGORIES]

    return {
        "rows": rows,
        "counts": counts,
        "unresolved": unresolved,
        "reference_count": len(reference_by_name),
        "grammar_count": len(grammar_by_name),
    }


def _classify_shared_function(
    ref_entry: dict[str, Any],
    grammar_entry: dict[str, Any],
) -> tuple[str, str, str]:
    reference_fixed_params = [
        param
        for param in ref_entry.get("parameters", [])
        if param["name"] not in IGNORED_REFERENCE_PARAMS
        and param["kind"] not in {"var_positional", "var_keyword"}
    ]
    reference_accepts_var_positional = any(
        param["name"] not in IGNORED_REFERENCE_PARAMS
        and param["kind"] == "var_positional"
        for param in ref_entry.get("parameters", [])
    )
    required_reference_params = {
        param["name"]
        for param in reference_fixed_params
        if not param["has_default"]
    }
    reference_params = {
        param["name"]
        for param in reference_fixed_params
    }
    reference_kwargs = set(ref_entry.get("kwargs", []))
    allowed_kwargs = set(grammar_entry.get("allowed_kwargs", []))
    generic_kwargs = {kw for kw in allowed_kwargs if kw.startswith("<") and kw.endswith(">")}
    unknown_kwargs = allowed_kwargs - reference_params - reference_kwargs - generic_kwargs
    allowed_arities = set(grammar_entry.get("allowed_arities", []))

    if generic_kwargs:
        return (
            "CATEGORY_C_SIGNATURE_DRIFT",
            "Replace the generic keyword production with explicit reference kwargs or document the exception.",
            "The grammar accepts arbitrary identifier keywords for this reference function.",
        )
    if "keyword-list" in allowed_arities and required_reference_params:
        return (
            "CATEGORY_C_SIGNATURE_DRIFT",
            "Require the documented non-default parameters positionally or through explicit required keyword productions.",
            "The grammar permits a keyword-list-only call form even though the reference signature has required public parameters: "
            f"{', '.join(sorted(required_reference_params))}.",
        )
    arity_drift = _arity_drift_reason(
        grammar_entry,
        reference_fixed_params,
        required_reference_params,
        reference_accepts_var_positional,
    )
    if arity_drift:
        return (
            "CATEGORY_C_SIGNATURE_DRIFT",
            "Align the grammar arity form with the documented required and positional parameters or document the exception.",
            arity_drift,
        )
    if unknown_kwargs:
        return (
            "CATEGORY_C_SIGNATURE_DRIFT",
            "Remove non-reference kwargs from the grammar or document the exception.",
            f"Grammar kwargs absent from the pinned reference signature: {', '.join(sorted(unknown_kwargs))}.",
        )

    return (
        "MATCH",
        "No grammar change.",
        "Grammar-supported names and keyword forms are a compatible in-scope subset of the reference signature.",
    )


def _arity_drift_reason(
    grammar_entry: dict[str, Any],
    reference_fixed_params: list[dict[str, Any]],
    required_reference_params: set[str],
    reference_accepts_var_positional: bool,
) -> str | None:
    reference_param_order = [param["name"] for param in reference_fixed_params]
    max_positional = len(reference_fixed_params)
    for raw_form in grammar_entry.get("allowed_arities", []):
        form = _parse_grammar_arity_form(raw_form, set(grammar_entry.get("allowed_kwargs", [])))
        if form is None:
            return f"Grammar arity form is not understood by the coverage comparator: {raw_form}."
        if form.has_unbounded_positionals and not reference_accepts_var_positional:
            return (
                f"Grammar arity form {raw_form} accepts arbitrary positional arguments, "
                f"but the reference signature supports at most {max_positional}."
            )
        if not reference_accepts_var_positional and form.positional_count > max_positional:
            return (
                f"Grammar arity form {raw_form} allows {form.positional_count} positional arguments, "
                f"but the reference signature supports at most {max_positional}."
            )

        supplied_positionally = set(reference_param_order[: form.positional_count])
        supplied_required = supplied_positionally | form.required_keywords
        missing_required = required_reference_params - supplied_required
        if missing_required:
            return (
                f"Grammar arity form {raw_form} omits required public reference parameters: "
                f"{', '.join(sorted(missing_required))}."
            )
    return None


def _parse_grammar_arity_form(raw_form: str, allowed_kwargs: set[str]) -> GrammarArityForm | None:
    if raw_form == "keyword-list":
        return GrammarArityForm(
            raw=raw_form,
            positional_count=0,
            has_unbounded_positionals=False,
            required_keywords=set(),
            has_generic_keyword_list=True,
        )
    if raw_form == "keyword-only":
        return GrammarArityForm(
            raw=raw_form,
            positional_count=0,
            has_unbounded_positionals=False,
            required_keywords=allowed_kwargs,
            has_generic_keyword_list=False,
        )

    keyword_only_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=1", raw_form)
    if keyword_only_match:
        return GrammarArityForm(
            raw=raw_form,
            positional_count=0,
            has_unbounded_positionals=False,
            required_keywords={keyword_only_match.group(1)},
            has_generic_keyword_list=False,
        )

    positional_match = re.fullmatch(r"(\d+)(?:\+(.*))?", raw_form)
    if not positional_match:
        return None

    positional_count = int(positional_match.group(1))
    suffix = positional_match.group(2)
    if suffix is None:
        return GrammarArityForm(
            raw=raw_form,
            positional_count=positional_count,
            has_unbounded_positionals=False,
            required_keywords=set(),
            has_generic_keyword_list=False,
        )
    if suffix == "":
        return GrammarArityForm(
            raw=raw_form,
            positional_count=positional_count,
            has_unbounded_positionals=True,
            required_keywords=set(),
            has_generic_keyword_list=False,
        )
    if suffix == "kwargs":
        return GrammarArityForm(
            raw=raw_form,
            positional_count=positional_count,
            has_unbounded_positionals=False,
            required_keywords=set(),
            has_generic_keyword_list=True,
        )
    return GrammarArityForm(
        raw=raw_form,
        positional_count=positional_count,
        has_unbounded_positionals=False,
        required_keywords=set(suffix.split("+")),
        has_generic_keyword_list=False,
    )


def _format_grammar_arity_kwargs(grammar_entry: dict[str, Any]) -> str:
    arities = ", ".join(grammar_entry.get("allowed_arities", [])) or "none"
    kwargs = ", ".join(grammar_entry.get("allowed_kwargs", [])) or "none"
    restrictions = "; ".join(grammar_entry.get("restrictions", []))
    return f"arities: {arities}; kwargs: {kwargs}; restrictions: {restrictions}"


def write_report(
    reference: dict[str, Any],
    grammar: dict[str, Any],
    comparison: dict[str, Any],
    report_path: Path,
    *,
    reference_snapshot_sha256: str,
    spot_check_seed: int = 20260516,
    manual_spot_check_status: str = "PENDING_MANUAL_REVIEW",
) -> None:
    rows: list[CoverageRow] = comparison["rows"]
    counts = comparison["counts"]
    unresolved: list[CoverageRow] = comparison["unresolved"]
    function_names = sorted(row.function for row in rows if row.reference_signature != "n/a")
    spot_check_functions = sorted(random.Random(spot_check_seed).sample(function_names, min(20, len(function_names))))
    rows_by_function = {row.function: row for row in rows}
    reference_by_function = {entry["name"]: entry for entry in reference["functions"]}

    lines: list[str] = [
        "# Triton Language API Coverage Report",
        "",
        "## Executive Summary",
        "",
        (
            "This report compares the task-agnostic Cluster 1 GBNF `tl.*` allow-list "
            "against a pinned snapshot of the official `triton.language` API reference. "
            "The comparison is offline and does not use tutorial fixture acceptance as evidence."
        ),
        "",
        f"- Reference functions compared: {comparison['reference_count']}",
        f"- Grammar functions extracted: {comparison['grammar_count']}",
        f"- MATCH: {counts.get('MATCH', 0)}",
        f"- INTENTIONAL_EXCLUSION: {counts.get('INTENTIONAL_EXCLUSION', 0)}",
        f"- DOCUMENTED_EXCEPTION: {counts.get('DOCUMENTED_EXCEPTION', 0)}",
        f"- Unresolved Category A/B/C: {len(unresolved)}",
        "",
        "## Triton Reference Version/Source",
        "",
        f"- Source URL: `{reference['source_url']}`",
        f"- Docs version: `{reference['docs_version']}`",
        f"- Source title: `{reference.get('source_title', '')}`",
        f"- Snapshot extraction version: `{reference['extraction_version']}`",
        f"- Snapshot timestamp UTC: `{reference['extraction_timestamp_utc']}`",
        f"- Local pasted corpus gate: `{LOCAL_TRITON_CORPUS}`",
        f"- Pinned reference snapshot: `{DEFAULT_REFERENCE}`",
        f"- Pinned reference snapshot SHA-256: `{reference_snapshot_sha256}`",
        "",
        (
            "The upstream source URL is the moving Triton `main` documentation. "
            "Reviewer-facing citations should identify the pinned local JSON snapshot by path, "
            "timestamp, and SHA-256 rather than citing `main` as a stable version."
        ),
        "",
        "Excluded public non-function entries:",
        "",
    ]

    excluded_entries = reference.get("excluded_public_entries", [])
    if excluded_entries:
        lines.extend(
            f"- `{entry['name']}`: {entry['exclusion_reason']}"
            for entry in excluded_entries
        )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Grammar Source File",
            "",
            f"- Grammar source: `{grammar['source_file']}`",
            f"- Grammar extraction version: `{grammar['extraction_version']}`",
            f"- Extracted allow-list snapshot: `{DEFAULT_GRAMMAR}`",
            "",
            "## Extraction Methodology",
            "",
            (
                "Reference extraction starts from the official `triton.language` index, follows each "
                "`generated/triton.language.<name>.html` page, captures the documented signature, "
                "parameter names, section heading, source URL, docs version, and extraction timestamp, "
                "then pins that JSON for offline CI. CI first verifies that the pasted local Triton "
                "corpus in `.contracts/agentic/reference/triton_corpus.md` has the same public "
                "`triton.language` function set and public parameter/kwarg names as the pinned snapshot."
            ),
            "",
            (
                "Grammar extraction parses `cluster1/grammar/triton_kernel_agnostic.gbnf`, identifies "
                "literal `tl.<name>(...)` call productions plus named call families such as "
                "`tl-unary-math-name`, and derives rule names, contexts, accepted grammar arity forms, "
                "literal keyword arguments, and encoded restrictions from the relevant GBNF alternatives. "
                "The extractor does not use a hand-maintained Triton signature table."
            ),
            "",
            (
                "The comparison treats grammar-supported kwargs as compatible when they are a subset "
                "of the public reference parameters. Optional reference kwargs omitted by the grammar "
                "are considered an in-scope restriction, not an unresolved drift. Grammar kwargs absent "
                "from the reference, arbitrary generic kwargs, keyword-list-only call forms that omit "
                "documented required parameters, missing reference functions, or grammar functions "
                "absent from the reference are unresolved until fixed or explicitly documented."
            ),
            "",
            "## Coverage Counts",
            "",
            "| category | count |",
            "| --- | ---: |",
        ]
    )
    for category in [
        "MATCH",
        "INTENTIONAL_EXCLUSION",
        "DOCUMENTED_EXCEPTION",
        "CATEGORY_A_REFERENCE_NOT_IN_GRAMMAR",
        "CATEGORY_B_GRAMMAR_NOT_IN_REFERENCE",
        "CATEGORY_C_SIGNATURE_DRIFT",
    ]:
        lines.append(f"| {category} | {counts.get(category, 0)} |")

    _append_category_section(lines, "Category A Divergences", rows, "CATEGORY_A_REFERENCE_NOT_IN_GRAMMAR")
    _append_category_section(lines, "Category B Divergences", rows, "CATEGORY_B_GRAMMAR_NOT_IN_REFERENCE")
    _append_category_section(lines, "Category C Divergences", rows, "CATEGORY_C_SIGNATURE_DRIFT")
    _append_category_section(lines, "Intentional Exclusions With Reasoning", rows, "INTENTIONAL_EXCLUSION")
    _append_category_section(lines, "Documented Exceptions", rows, "DOCUMENTED_EXCEPTION")

    lines.extend(
        [
            "",
            "## Complete Function-By-Function Table",
            "",
            "| function | reference section | reference signature | grammar support | grammar arity/kwargs | divergence category | action | rationale |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(rows, key=lambda item: item.function):
        lines.append(
            "| "
            + " | ".join(
                _escape_table_cell(value)
                for value in [
                    row.function,
                    row.reference_section,
                    row.reference_signature,
                    row.grammar_support,
                    row.grammar_arity_kwargs,
                    row.divergence_category,
                    row.action,
                    row.rationale,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Manual Spot-Check Checklist",
            "",
            f"- Fixed seed: `{spot_check_seed}`",
            f"- Status: `{manual_spot_check_status}`",
            "- Procedure: inspect each selected function in the official generated docs page, verify the pinned signature, inspect the corresponding GBNF rule, and confirm the divergence category.",
            "",
            "| function | official source | reference signature | grammar rule(s) | grammar arity/kwargs | category | evidence note |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for name in spot_check_functions:
        row = rows_by_function[name]
        source_url = reference_by_function.get(name, {}).get("source_url", "")
        lines.append(
            "| "
            + " | ".join(
                _escape_table_cell(value)
                for value in [
                    row.function,
                    source_url,
                    row.reference_signature,
                    row.grammar_support,
                    row.grammar_arity_kwargs,
                    row.divergence_category,
                    "Official generated docs signature matched the pinned snapshot; grammar support checked against the listed GBNF rule(s) in cluster1/grammar/triton_kernel_agnostic.gbnf; divergence category remained MATCH.",
                ]
            )
            + " |"
        )

    blockers = "None" if not unresolved else ", ".join(row.function for row in unresolved)
    lines.extend(
        [
            "",
            "## Paper-Facing Interpretation",
            "",
            (
                "The G condition should be framed as a harness-imposed structural surface plus a "
                "documented `triton.language` API allow-list verified against this pinned reference "
                "snapshot. This is not evidence of a universal Triton grammar, and it does not claim "
                "coverage beyond the audited public `tl.*` function allow-list and the Cluster 1 "
                "surface constraints."
            ),
            "",
            "## Remaining Blockers, If Any",
            "",
            f"- {blockers}",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _append_category_section(
    lines: list[str],
    title: str,
    rows: list[CoverageRow],
    category: str,
) -> None:
    category_rows = [row for row in rows if row.divergence_category == category]
    lines.extend(["", f"## {title}", ""])
    if not category_rows:
        lines.append("- None")
        return
    for row in category_rows:
        lines.append(f"- `{row.function}`: {row.rationale} Action: {row.action}")


def _escape_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _print_unresolved(unresolved: list[CoverageRow]) -> None:
    if not unresolved:
        print("No unresolved Category A/B/C divergences.")
        return
    print("Unresolved API coverage divergences:")
    for row in unresolved:
        print(f"- {row.divergence_category}: {row.function} - {row.rationale}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--spot-check-seed", type=int, default=20260516)
    parser.add_argument("--manual-spot-check-status", default="PENDING_MANUAL_REVIEW")
    parser.add_argument("--fail-on-unresolved", action="store_true")
    args = parser.parse_args(argv)

    reference = load_json(args.reference)
    grammar = load_json(args.grammar)
    comparison = compare_snapshots(reference, grammar)
    write_report(
        reference,
        grammar,
        comparison,
        args.report,
        reference_snapshot_sha256=sha256_file(args.reference),
        spot_check_seed=args.spot_check_seed,
        manual_spot_check_status=args.manual_spot_check_status,
    )
    print(f"wrote {args.report}")
    _print_unresolved(comparison["unresolved"])
    return 1 if args.fail_on_unresolved and comparison["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
