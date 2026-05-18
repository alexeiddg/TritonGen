"""Tests for C1 analyzer metadata and grammar failure taxonomy integration."""

from __future__ import annotations

import json
from pathlib import Path

from cluster1.experiments.analyze_cluster1 import (
    build_compile_summary_markdown,
    summarize_results,
)
from shared.generation_metadata import GENERATION_METADATA_SCHEMA_VERSION


def test_analyzer_classifies_grammar_rejections_through_shared_taxonomy(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "metadata_results.jsonl"
    rows = [
        _make_record(
            run_id="gbnf-parse",
            gbnf_parse_valid=False,
            semantic_valid=False,
            grammar_valid=False,
            rejection_layer="gbnf_parse",
            generation_seed=0,
        ),
        _make_record(
            run_id="semantic",
            gbnf_parse_valid=True,
            semantic_valid=False,
            grammar_valid=False,
            rejection_layer="semantic_validator",
            generation_seed=1,
        ),
        _make_record(
            run_id="fallback",
            gbnf_parse_valid=None,
            semantic_valid=None,
            grammar_valid=False,
            rejection_layer="unknown",
            generation_seed=2,
        ),
    ]
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    failure_section = markdown.split("## Failure Codes", maxsplit=1)[1].split(
        "## Metadata Completeness",
        maxsplit=1,
    )[0]
    assert "| G | template G reference | elementwise | fp32 | F0_GBNF_PARSE | 1 |" in (
        failure_section
    )
    assert (
        "| G | template G reference | elementwise | fp32 | "
        "F0_SEMANTIC_INVALID | 1 |"
    ) in failure_section
    assert (
        "| G | template G reference | elementwise | fp32 | "
        "F0_GRAMMAR_INVALID | 1 |"
    ) in failure_section

    grammar_section = markdown.split("## Grammar Rejections", maxsplit=1)[1].split(
        "## Provenance Metadata",
        maxsplit=1,
    )[0]
    assert "gbnf_parse | false | false | false | F0_GBNF_PARSE | 1 |" in (
        grammar_section
    )
    assert (
        "semantic_validator | true | false | false | "
        "F0_SEMANTIC_INVALID | 1 |"
    ) in grammar_section
    assert "unknown | unknown | unknown | false | F0_GRAMMAR_INVALID | 1 |" in (
        grammar_section
    )


def test_metadata_sections_surface_current_schema_fields_without_mutating_input(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "metadata_results.jsonl"
    rows = [
        _make_record(
            run_id="metadata-row",
            gbnf_parse_valid=True,
            semantic_valid=True,
            grammar_valid=True,
            rejection_layer=None,
        )
    ]
    _write_jsonl(jsonl_path, rows)
    original_text = jsonl_path.read_text(encoding="utf-8")

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    assert jsonl_path.read_text(encoding="utf-8") == original_text
    assert "## Metadata Completeness" in markdown
    assert "## Provenance Metadata" in markdown
    assert "| grammar_sha | 1 | 1 | 0 | 0 |" in markdown
    assert "| gbnf_parse_valid | 1 | 1 | 0 | 0 |" in markdown
    assert "| modal_image_sha | 1 | 1 | 0 | 0 |" in markdown
    assert "| modal_image_provenance_sha256 | 0 | 0 | 0 | 0 |" in markdown
    assert "| modal_image_provenance_components | 0 | 0 | 0 | 0 |" in markdown
    assert "| xgrammar_version | 0.1.33 | 1 |" in markdown
    assert "| modal_image_provenance_components | missing |" not in markdown


def test_metadata_sections_report_fallback_modal_provenance_when_needed(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "metadata_results.jsonl"
    rows = [
        _make_record(
            run_id="fallback-modal-image",
            modal_image_sha="unknown",
            modal_image_provenance_sha256="e" * 64,
            modal_image_provenance_components={"runtime": "modal-l4"},
        )
    ]
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    assert "| modal_image_sha | 1 | 0 | 1 | 0 |" in markdown
    assert "| modal_image_provenance_sha256 | 1 | 1 | 0 | 0 |" in markdown
    assert "| modal_image_provenance_components | 1 | 1 | 0 | 0 |" in markdown
    assert "| modal_image_provenance_sha256 | " + ("e" * 64) + " | 1 |" in markdown
    assert "| modal_image_provenance_components | present | 1 |" in markdown


def test_compile_metrics_ignore_grammar_rejection_metadata(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "metadata_results.jsonl"
    rows = [
        _make_record(
            run_id="gbnf-parse",
            gbnf_parse_valid=False,
            semantic_valid=False,
            grammar_valid=False,
            rejection_layer="gbnf_parse",
            generation_seed=0,
        ),
        _make_record(
            run_id="semantic",
            gbnf_parse_valid=True,
            semantic_valid=False,
            grammar_valid=False,
            rejection_layer="semantic_validator",
            generation_seed=1,
        ),
    ]
    _write_jsonl(jsonl_path, rows)

    summary = summarize_results(jsonl_path, allow_small_matrix=True)

    assert summary.loc[0, "n"] == 2
    assert summary.loc[0, "compile_successes"] == 2
    assert summary.loc[0, "compile_failures"] == 0
    assert summary.loc[0, "compile@1"] == 1.0
    assert summary.loc[0, "grammar_valid_count"] == 0
    assert summary.loc[0, "grammar_valid_rate"] == 0.0


def _make_record(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": True,
        "grammar_variant": "template_upper_bound",
        "generation_metadata_schema_version": GENERATION_METADATA_SCHEMA_VERSION,
        "grammar_sha": "a" * 64,
        "grammar_path": "cluster1/grammar/triton_kernel.gbnf",
        "gbnf_parse_valid": True,
        "semantic_valid": True,
        "grammar_valid": True,
        "rejection_layer": None,
        "stop_reason": "eos_token",
        "xgrammar_version": "0.1.33",
        "transformers_version": "4.47.1",
        "tokenizers_version": "0.21.4",
        "model_revision": "b" * 40,
        "tokenizer_revision": "c" * 40,
        "modal_image_sha": "sha256:" + "d" * 64,
        "modal_image_provenance_sha256": None,
        "modal_image_provenance_components": None,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": True,
        "compile_results_by_dtype": {"fp32": True, "fp16": True, "bf16": True},
        "compile_error_type": None,
        "compile_error_msg": None,
        "failure_code": None,
        "masked_token_rate": 0.25,
        "unique_solution_hash": "hash",
        "n_shapes_tested": 4,
        "generation_seed": 0,
        "temperature": 0.2,
        "run_id": "run",
        "timestamp_utc": "2026-05-05T00:00:00+00:00",
    }
    defaults.update(overrides)
    return defaults


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
