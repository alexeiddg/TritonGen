"""Offline guard for Triton language API reference coverage."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from cluster1.grammar.corpus.compare_api_coverage import compare_snapshots, write_report
from cluster1.grammar.corpus.extract_grammar_allowlist import extract_allowlist
from cluster1.grammar.corpus.extract_triton_reference import _parse_parameters


ROOT = Path(__file__).parents[2]
GRAMMAR_PATH = Path("cluster1/grammar/triton_kernel_agnostic.gbnf")
CORPUS_DIR = ROOT / "cluster1/grammar/corpus"
GRAMMAR_ALLOWLIST_PATH = CORPUS_DIR / "grammar_allowlist_extracted.json"
REFERENCE_PATH = CORPUS_DIR / "triton_language_reference_vmain_2026_05_16.json"
REPORT_PATH = CORPUS_DIR / "api_coverage_report.md"
LOCAL_TRITON_CORPUS_PATH = ROOT / ".contracts/agentic/reference/triton_corpus.md"
REFERENCE_SNAPSHOT_SHA256 = "a7a637be7f80d59a0764838a6d21a945e7d17e85f1781992fa5089c67b6a1b80"
LOCAL_CORPUS_SIGNATURE_RE = re.compile(
    r"^(?:class)?triton\.language\.([A-Za-z_][A-Za-z0-9_]*)\(([^\n]*)\)(?:\s*→[^\n]*)?$",
    re.MULTILINE,
)
NON_FUNCTION_PUBLIC_ENTRIES = {"tl.tensor", "tl.tensor_descriptor"}
IGNORED_REFERENCE_PARAMS = {"self", "_semantic", "_generator"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pinned_reference_snapshot_is_available_offline() -> None:
    reference = _load_json(REFERENCE_PATH)

    assert _sha256(REFERENCE_PATH) == REFERENCE_SNAPSHOT_SHA256
    assert reference["source_url"] == "https://triton-lang.org/main/python-api/triton.language.html"
    assert reference["docs_version"] == "main"
    assert reference["function_count"] == len(reference["functions"]) == 92
    assert all(function["source_url"].startswith("https://triton-lang.org/main/") for function in reference["functions"])
    assert {entry["name"] for entry in reference["excluded_public_entries"]} == {
        "tl.tensor",
        "tl.tensor_descriptor",
    }


def test_pasted_triton_corpus_matches_pinned_reference_snapshot() -> None:
    corpus_entries = _extract_local_triton_corpus_entries()
    duplicate_names = sorted(
        name
        for name, count in Counter(entry["name"] for entry in corpus_entries).items()
        if count > 1
    )
    assert not duplicate_names, f"Duplicate triton.language entries in pasted corpus: {duplicate_names}"

    corpus_by_name = {
        entry["name"]: entry
        for entry in corpus_entries
        if entry["name"] not in NON_FUNCTION_PUBLIC_ENTRIES
    }
    reference = _load_json(REFERENCE_PATH)
    reference_by_name = {entry["name"]: entry for entry in reference["functions"]}

    assert set(corpus_by_name) == set(reference_by_name), (
        "The pasted Triton corpus must be the first offline gate for tl.* APIs. "
        f"Missing from corpus: {sorted(set(reference_by_name) - set(corpus_by_name))}; "
        f"extra in corpus: {sorted(set(corpus_by_name) - set(reference_by_name))}."
    )

    mismatches: list[str] = []
    for name in sorted(reference_by_name):
        corpus_entry = corpus_by_name[name]
        reference_entry = reference_by_name[name]
        corpus_params = _public_parameter_names(corpus_entry["parameters"])
        reference_params = _public_parameter_names(reference_entry["parameters"])
        corpus_kwargs = _public_kwarg_names(corpus_entry["parameters"])
        reference_kwargs = reference_entry["kwargs"]
        if corpus_params != reference_params or corpus_kwargs != reference_kwargs:
            mismatches.append(
                f"{name}: corpus params={corpus_params}, reference params={reference_params}; "
                f"corpus kwargs={corpus_kwargs}, reference kwargs={reference_kwargs}"
            )

    assert not mismatches, "\n".join(mismatches)


def test_grammar_allowlist_snapshot_matches_current_gbnf() -> None:
    pinned = _load_json(GRAMMAR_ALLOWLIST_PATH)
    current = extract_allowlist(GRAMMAR_PATH)

    assert current == pinned, (
        "Regenerate cluster1/grammar/corpus/grammar_allowlist_extracted.json "
        "after changing the task-agnostic tl.* grammar allow-list."
    )


def test_api_coverage_has_no_unresolved_reference_drift() -> None:
    reference = _load_json(REFERENCE_PATH)
    grammar = _load_json(GRAMMAR_ALLOWLIST_PATH)
    comparison = compare_snapshots(reference, grammar)
    unresolved = comparison["unresolved"]

    assert not unresolved, "\n".join(
        f"{row.divergence_category}: {row.function} - {row.rationale}"
        for row in unresolved
    )


def test_api_coverage_detects_non_reference_grammar_kwarg(tmp_path: Path) -> None:
    mutated_grammar_path = tmp_path / "triton_kernel_agnostic_mutated.gbnf"
    mutated_grammar_path.write_text(
        GRAMMAR_PATH.read_text(encoding="utf-8").replace(
            '"volatile=" bool-literal',
            '"volatile=" bool-literal\n             | "invented_kw=" kernel-expr',
        ),
        encoding="utf-8",
    )

    reference = _load_json(REFERENCE_PATH)
    mutated_grammar = extract_allowlist(mutated_grammar_path)
    load_entry = next(entry for entry in mutated_grammar["functions"] if entry["name"] == "tl.load")
    assert "invented_kw" in load_entry["allowed_kwargs"]

    comparison = compare_snapshots(reference, mutated_grammar)
    unresolved_by_function = {row.function: row for row in comparison["unresolved"]}
    assert unresolved_by_function["tl.load"].divergence_category == "CATEGORY_C_SIGNATURE_DRIFT"
    assert "invented_kw" in unresolved_by_function["tl.load"].rationale


def test_api_coverage_detects_keyword_only_required_parameter_drift() -> None:
    reference = _load_json(REFERENCE_PATH)
    mutated_grammar = _load_json(GRAMMAR_ALLOWLIST_PATH)
    range_entry = next(entry for entry in mutated_grammar["functions"] if entry["name"] == "tl.range")
    range_entry["allowed_arities"] = [*range_entry["allowed_arities"], "keyword-list"]

    comparison = compare_snapshots(reference, mutated_grammar)
    unresolved_by_function = {row.function: row for row in comparison["unresolved"]}
    assert unresolved_by_function["tl.range"].divergence_category == "CATEGORY_C_SIGNATURE_DRIFT"
    assert "required public parameters: arg1" in unresolved_by_function["tl.range"].rationale


def test_api_coverage_detects_missing_required_positional_arity() -> None:
    reference = _load_json(REFERENCE_PATH)
    mutated_grammar = _load_json(GRAMMAR_ALLOWLIST_PATH)
    arange_entry = next(entry for entry in mutated_grammar["functions"] if entry["name"] == "tl.arange")
    arange_entry["allowed_arities"] = ["1"]

    comparison = compare_snapshots(reference, mutated_grammar)
    unresolved_by_function = {row.function: row for row in comparison["unresolved"]}
    assert unresolved_by_function["tl.arange"].divergence_category == "CATEGORY_C_SIGNATURE_DRIFT"
    assert "omits required public reference parameters: end" in unresolved_by_function["tl.arange"].rationale


def test_api_coverage_detects_excess_positional_arity() -> None:
    reference = _load_json(REFERENCE_PATH)
    mutated_grammar = _load_json(GRAMMAR_ALLOWLIST_PATH)
    arange_entry = next(entry for entry in mutated_grammar["functions"] if entry["name"] == "tl.arange")
    arange_entry["allowed_arities"] = ["3"]

    comparison = compare_snapshots(reference, mutated_grammar)
    unresolved_by_function = {row.function: row for row in comparison["unresolved"]}
    assert unresolved_by_function["tl.arange"].divergence_category == "CATEGORY_C_SIGNATURE_DRIFT"
    assert "allows 3 positional arguments" in unresolved_by_function["tl.arange"].rationale


def test_api_coverage_report_matches_current_comparison(tmp_path: Path) -> None:
    reference = _load_json(REFERENCE_PATH)
    grammar = _load_json(GRAMMAR_ALLOWLIST_PATH)
    comparison = compare_snapshots(reference, grammar)
    regenerated_report_path = tmp_path / "api_coverage_report.md"
    write_report(
        reference,
        grammar,
        comparison,
        regenerated_report_path,
        reference_snapshot_sha256=REFERENCE_SNAPSHOT_SHA256,
        manual_spot_check_status="COMPLETED_OFFICIAL_DOCS_SPOT_CHECK",
    )

    assert regenerated_report_path.read_text(encoding="utf-8") == REPORT_PATH.read_text(encoding="utf-8"), (
        "Regenerate cluster1/grammar/corpus/api_coverage_report.md after changing "
        "the reference snapshot, grammar allow-list, or comparison policy."
    )


def _extract_local_triton_corpus_entries() -> list[dict]:
    corpus_text = LOCAL_TRITON_CORPUS_PATH.read_text(encoding="utf-8")
    entries: list[dict] = []
    for name, raw_params in LOCAL_CORPUS_SIGNATURE_RE.findall(corpus_text):
        signature = f"triton.language.{name}({raw_params})"
        entries.append(
            {
                "name": f"tl.{name}",
                "signature": signature,
                "parameters": _parse_parameters(signature),
            }
        )
    return entries


def _public_parameter_names(parameters: list[dict]) -> list[str]:
    return [
        param["name"]
        for param in parameters
        if param["name"] not in IGNORED_REFERENCE_PARAMS
        and param["kind"] not in {"var_positional", "var_keyword"}
    ]


def _public_kwarg_names(parameters: list[dict]) -> list[str]:
    return [
        param["name"]
        for param in parameters
        if param["name"] not in IGNORED_REFERENCE_PARAMS
        and param["kind"] not in {"var_positional", "var_keyword"}
        and param["has_default"]
    ]
