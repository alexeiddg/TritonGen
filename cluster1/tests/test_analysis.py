"""Tests for Phase 8 pass@k analysis and reporting."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cluster1.experiments.analyze_cluster1 import (
    null_hypothesis_report,
    pass_at_k,
    summarize_results,
    unique_solution_rate,
)
from cluster1.results.dataclass import GenerationResult


def test_pass_at_k_matches_humaneval() -> None:
    assert pass_at_k(20, 5, 1) == 5 / 20

    expected_k5 = 1.0 - math.comb(15, 5) / math.comb(20, 5)
    expected_k10 = 1.0 - math.comb(15, 10) / math.comb(20, 10)
    assert pass_at_k(20, 5, 5) == pytest.approx(expected_k5)
    assert pass_at_k(20, 5, 10) == pytest.approx(expected_k10)
    assert pass_at_k(20, 5, 5) != 5 / 20
    assert pass_at_k(20, 16, 5) == 1.0

    with pytest.raises(ValueError, match="k must be <= n"):
        pass_at_k(4, 1, 5)


def test_unique_solution_rate() -> None:
    rows = [
        _make_result(unique_solution_hash="a"),
        _make_result(unique_solution_hash="a"),
        _make_result(unique_solution_hash="b"),
        _make_result(unique_solution_hash="c"),
    ]
    assert unique_solution_rate(rows) == 3 / 4


def test_summary_uses_compile_success_only(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "results.jsonl"
    rows = [
        _make_record(
            grammar_active=False,
            dtype="fp32",
            compile_success=i < 5,
            unique_solution_hash=f"off-{i % 10}",
            numerical_correct=bool(i % 2),
        )
        for i in range(20)
    ]
    _write_jsonl(jsonl_path, rows)

    summary = summarize_results(jsonl_path)

    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["kernel_class"] == "elementwise"
    assert bool(row["grammar_active"]) is False
    assert row["dtype"] == "fp32"
    assert row["n"] == 20
    assert row["compile_successes"] == 5
    assert row["compile_failures"] == 15
    assert row["pass@1"] == 5 / 20
    assert row["pass@5"] == pytest.approx(pass_at_k(20, 5, 5))
    assert row["pass@10"] == pytest.approx(pass_at_k(20, 5, 10))
    assert row["unique_solution_rate"] == 10 / 20


def test_summary_requires_n20_per_group(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "small.jsonl"
    _write_jsonl(jsonl_path, [_make_record(generation_seed=i) for i in range(19)])

    with pytest.raises(ValueError, match="expected at least 20 rows"):
        summarize_results(jsonl_path)


def test_null_hypothesis_report_documents_eliminated_failures(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "both.jsonl"
    output_path = tmp_path / "summary.md"
    rows = [
        _make_record(
            grammar_active=False,
            dtype="fp32",
            compile_success=i < 8,
            unique_solution_hash=f"off-{i}",
            generation_seed=i,
        )
        for i in range(20)
    ]
    rows.extend(
        _make_record(
            grammar_active=True,
            dtype="fp32",
            compile_success=i < 14,
            masked_token_rate=0.25,
            unique_solution_hash=f"on-{i}",
            generation_seed=i,
        )
        for i in range(20)
    )
    _write_jsonl(jsonl_path, rows)

    null_hypothesis_report(jsonl_path, output_path)

    markdown = output_path.read_text(encoding="utf-8")
    assert "pass@1" in markdown
    assert "pass@5" in markdown
    assert "pass@10" in markdown
    assert "unique_solution_rate" in markdown
    assert "grammar ON eliminated 6 compile failure(s)" in markdown


def _make_result(**overrides) -> GenerationResult:
    return GenerationResult(**_make_record(**overrides))


def _make_record(**overrides) -> dict[str, object]:
    defaults: dict[str, object] = {
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": False,
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
