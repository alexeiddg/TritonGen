"""Tests for Cluster 1 analyzer failure taxonomy alignment."""

from __future__ import annotations

import json
from pathlib import Path

from cluster1.experiments.analyze_cluster1 import build_compile_summary_markdown


def test_analyzer_reports_canonical_failure_codes_as_primary(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "results.jsonl"
    rows = [
        _make_record(
            run_id="legacy-signature",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg="missing launcher",
            generation_seed=0,
        ),
        _make_record(
            run_id="legacy-compile",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="CompilationError",
            compile_error_msg="triton compile failed",
            generation_seed=1,
        ),
        _make_record(
            run_id="new-parse",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg="invalid Python syntax",
            failure_code="F0_PARSE",
            generation_seed=2,
        ),
        _make_record(
            run_id="success",
            compile_success=True,
            compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
            compile_error_type=None,
            compile_error_msg=None,
            generation_seed=3,
        ),
    ]
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    failure_section = markdown.split("## Failure Codes", maxsplit=1)[1].split(
        "## Compile Error Types",
        maxsplit=1,
    )[0]
    assert (
        "| baseline | none | elementwise | fp32 | F0_BAD_SIGNATURE | 1 |"
        in failure_section
    )
    assert "| baseline | none | elementwise | fp32 | F0_PARSE | 1 |" in failure_section
    assert "| baseline | none | elementwise | fp32 | F1_COMPILE | 1 |" in failure_section
    assert "| baseline | none | elementwise | fp32 | None | 1 |" in failure_section


def test_analyzer_maps_legacy_signature_syntax_wrapper_to_parse(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "results.jsonl"
    rows = [
        _make_record(
            run_id="legacy-syntax-wrapper",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg=(
                "SignatureError: syntax error in generated source: "
                "invalid syntax (tmp.py, line 19)"
            ),
            generation_seed=0,
        ),
        _make_record(
            run_id="legacy-signature",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg="missing launcher",
            generation_seed=1,
        ),
    ]
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    failure_section = markdown.split("## Failure Codes", maxsplit=1)[1].split(
        "## Compile Error Types",
        maxsplit=1,
    )[0]
    assert "| baseline | none | elementwise | fp32 | F0_PARSE | 1 |" in failure_section
    assert (
        "| baseline | none | elementwise | fp32 | F0_BAD_SIGNATURE | 1 |"
        in failure_section
    )


def test_analyzer_keeps_legacy_compile_error_distribution_secondary(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "results.jsonl"
    rows = [
        _make_record(
            run_id="legacy-signature",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg="missing launcher",
            generation_seed=0,
        ),
        _make_record(
            run_id="new-parse",
            compile_success=False,
            compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
            compile_error_type="SignatureError",
            compile_error_msg="invalid Python syntax",
            failure_code="F0_PARSE",
            generation_seed=1,
        ),
        _make_record(
            run_id="success",
            compile_success=True,
            compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
            compile_error_type=None,
            compile_error_msg=None,
            generation_seed=2,
        ),
    ]
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        allow_small_matrix=True,
    )

    legacy_section = markdown.split("## Compile Error Types", maxsplit=1)[1].split(
        "## Grammar Acceptance",
        maxsplit=1,
    )[0]
    assert (
        "| baseline | none | elementwise | fp32 | SignatureError | 2 |"
        in legacy_section
    )
    assert "| baseline | none | elementwise | fp32 | None | 1 |" in legacy_section


def _make_record(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": False,
        "grammar_variant": None,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": True,
        "compile_results_by_dtype": {"fp32": True, "fp16": True, "bf16": True},
        "compile_error_type": None,
        "compile_error_msg": None,
        "masked_token_rate": None,
        "unique_solution_hash": "hash",
        "n_shapes_tested": 5,
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
