"""Tests for Phase 8 pass@k analysis and reporting."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cluster1.experiments.analyze_cluster1 import (
    build_compile_summary_markdown,
    main,
    null_hypothesis_report,
    pass_at_k,
    prompt_dtype_compile_success,
    summarize_results,
    unique_solution_rate,
)
from cluster1.experiments.make_cluster1_figures import (
    results_to_dataframe,
    validate_integrity,
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
    assert row["grammar_variant"] is None
    assert row["dtype"] == "fp32"
    assert row["n"] == 20
    assert row["compile_success_scope"] == "all_dtype_strict"
    assert row["compile_successes"] == 5
    assert row["compile_failures"] == 15
    assert row["compile@1"] == 5 / 20
    assert row["prompt_dtype_compile_successes"] == 20
    assert row["prompt_dtype_compile_failures"] == 0
    assert row["prompt_dtype_compile_success_rate"] == 1.0
    assert row["pass@1"] == 5 / 20
    assert row["pass@5"] == pytest.approx(pass_at_k(20, 5, 5))
    assert row["pass@10"] == pytest.approx(pass_at_k(20, 5, 10))
    assert row["unique_solution_rate"] == 10 / 20


def test_summary_distinguishes_strict_and_prompt_dtype_compile_success(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "mixed_dtype.jsonl"
    rows = [
        _make_record(
            dtype="fp16",
            compile_success=False,
            compile_results_by_dtype={"fp32": True, "fp16": i < 7, "bf16": False},
            compile_error_type="CompilationError",
            compile_error_msg="bf16 failed",
            generation_seed=i,
        )
        for i in range(20)
    ]
    _write_jsonl(jsonl_path, rows)

    summary = summarize_results(jsonl_path)

    row = summary.iloc[0]
    assert row["compile_success_scope"] == "all_dtype_strict"
    assert row["compile_successes"] == 0
    assert row["compile_failures"] == 20
    assert row["compile@1"] == 0.0
    assert row["prompt_dtype_compile_successes"] == 7
    assert row["prompt_dtype_compile_failures"] == 13
    assert row["prompt_dtype_compile_success_rate"] == 7 / 20
    assert row["pass@1"] == 0.0


def test_baseline_only_compile_summary_markdown(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "baseline_n20.jsonl"
    _write_jsonl(jsonl_path, _condition_rows(["baseline"], n=20))

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="baseline",
        kernel_class="elementwise",
        n=20,
        validate=True,
    )

    assert "# Cluster 1 Compile-Only Summary" in markdown
    assert "row_count: 60" in markdown
    assert "expected_row_count: 60" in markdown
    assert "compile_success_scope: all_dtype_strict" in markdown
    assert "compile@1" in markdown
    assert "prompt_dtype_compile_success_rate" in markdown
    assert "pass@1" in markdown
    assert "pass@5" in markdown
    assert "pass@10" in markdown
    assert "unique_solution_rate" in markdown
    assert "No grammar-active rows found." in markdown
    assert "comparison requires both baseline and grammar-active rows" in markdown
    assert "| baseline | none | elementwise | fp32 | None |" in markdown


def test_g_only_compile_summary_markdown(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "g_n20.jsonl"
    _write_jsonl(jsonl_path, _condition_rows(["G"], n=20))

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="G",
        kernel_class="elementwise",
        n=20,
        validate=True,
    )

    assert "row_count: 60" in markdown
    assert "expected_conditions: ['G']" in markdown
    assert (
        "| G | template G reference | elementwise | fp32 | 20 | "
        "0.250000 | 0.250000 | 0.250000 |"
    ) in markdown
    assert "comparison requires both baseline and grammar-active rows" in markdown


def test_both_condition_compile_summary_markdown(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "both_n20.jsonl"
    rows = _condition_rows(["baseline"], n=20, strict_success_cutoff=8)
    rows.extend(_condition_rows(["G"], n=20, strict_success_cutoff=14))
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="both",
        kernel_class="elementwise",
        n=20,
        validate=True,
    )

    assert "row_count: 120" in markdown
    assert "expected_row_count: 120" in markdown
    assert "template G reference eliminated 6 compile failure(s)" in markdown
    assert "| baseline | none | elementwise | fp32 |" in markdown
    assert "| G | template G reference | elementwise | fp32 |" in markdown


def test_summary_rejects_small_matrix_unless_explicit(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "small.jsonl"
    _write_jsonl(jsonl_path, _condition_rows(["baseline"], n=1))

    with pytest.raises(ValueError, match="expected at least 20 rows"):
        build_compile_summary_markdown(jsonl_path)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
        allow_small_matrix=True,
        validate=True,
    )

    assert "row_count: 3" in markdown
    assert "pass@5" in markdown
    assert "NA" in markdown


def test_require_full_n20_is_fatal_without_validate_flag(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "small.jsonl"
    _write_jsonl(jsonl_path, _condition_rows(["baseline"], n=1))

    with pytest.raises(ValueError, match="--require-full-n20 requires --n 20"):
        build_compile_summary_markdown(
            jsonl_path,
            condition="baseline",
            kernel_class="elementwise",
            n=1,
            allow_small_matrix=True,
            require_full_n20=True,
        )


def test_masked_token_summary_excludes_baseline_rows(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "both_masked.jsonl"
    _write_jsonl(jsonl_path, _condition_rows(["baseline", "G"], n=20))

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="both",
        kernel_class="elementwise",
        n=20,
        validate=True,
    )
    masked_section = markdown.split("## Masked Token Rate", maxsplit=1)[1].split(
        "## Compile Error Types",
        maxsplit=1,
    )[0]

    assert "| G | template G reference | elementwise | fp32 |" in masked_section
    assert "| baseline |" not in masked_section


def test_compile_error_distribution_reported(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "errors.jsonl"
    rows = _condition_rows(["baseline"], n=20)
    rows[0].update(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="CompilationError",
        compile_error_msg="bad generated source",
    )
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="baseline",
        kernel_class="elementwise",
        n=20,
        validate=True,
    )

    assert "## Compile Error Types" in markdown
    assert "| baseline | none | elementwise | fp32 | CompilationError | 1 |" in markdown
    assert "| baseline | none | elementwise | fp32 | None | 19 |" in markdown


def test_prompt_dtype_compile_success_uses_row_dtype() -> None:
    row = _make_result(
        dtype="bf16",
        compile_success=False,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": False},
    )

    assert prompt_dtype_compile_success(row) is False


def test_prompt_dtype_compile_success_requires_dtype_key() -> None:
    row = _make_result(
        dtype="bf16",
        compile_success=False,
        compile_results_by_dtype={"fp32": True, "fp16": True},
    )

    with pytest.raises(ValueError, match=r"compile_results_by_dtype\['bf16'\]"):
        prompt_dtype_compile_success(row)


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
    assert "compile_success_scope" in markdown
    assert "prompt_dtype_compile_successes" in markdown
    assert "template G reference eliminated 6 compile failure(s)" in markdown


def test_summary_groups_by_condition_variant_kernel_and_dtype(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "variants.jsonl"
    rows = [
        _make_record(
            grammar_active=True,
            grammar_variant="template_upper_bound",
            masked_token_rate=0.25,
            unique_solution_hash=f"template-{i}",
            generation_seed=i,
            run_id=f"template-{i}",
        )
        for i in range(20)
    ]
    rows.extend(
        _make_record(
            grammar_active=True,
            grammar_variant="task_agnostic",
            masked_token_rate=0.35,
            unique_solution_hash=f"task-{i}",
            generation_seed=i,
            run_id=f"task-{i}",
        )
        for i in range(20)
    )
    _write_jsonl(jsonl_path, rows)

    summary = summarize_results(jsonl_path)

    assert len(summary) == 2
    assert set(summary["grammar_variant"]) == {
        "template_upper_bound",
        "task_agnostic",
    }


def test_analyzer_cli_accepts_task_agnostic_grammar_variant(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "task_agnostic.jsonl"
    output_path = tmp_path / "summary.md"
    _write_jsonl(
        jsonl_path,
        [
            _make_record(
                grammar_active=True,
                grammar_variant="task_agnostic",
                masked_token_rate=0.35,
                dtype=dtype,
                generation_seed=0,
                run_id=f"task-agnostic-{dtype}",
            )
            for dtype in ("fp32", "fp16", "bf16")
        ],
    )

    rc = main(
        [
            "--input",
            str(jsonl_path),
            "--output",
            str(output_path),
            "--condition",
            "G",
            "--grammar-variant",
            "task_agnostic",
            "--kernel-class",
            "elementwise",
            "--n",
            "1",
            "--validate",
            "--allow-small-matrix",
        ]
    )

    assert rc == 0
    markdown = output_path.read_text(encoding="utf-8")
    assert "expected_grammar_variants: ['task_agnostic (task-agnostic G primary)']" in markdown
    assert "| G | task-agnostic G | elementwise | fp32 |" in markdown


def test_analyzer_validates_and_groups_both_g_variants(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "both_variants.jsonl"
    rows: list[dict[str, object]] = []
    for grammar_variant in ("template_upper_bound", "task_agnostic"):
        for dtype in ("fp32", "fp16", "bf16"):
            rows.append(
                _make_record(
                    grammar_active=True,
                    grammar_variant=grammar_variant,
                    masked_token_rate=0.25,
                    dtype=dtype,
                    generation_seed=0,
                    run_id=f"{grammar_variant}-{dtype}",
                )
            )
    _write_jsonl(jsonl_path, rows)

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition="G",
        grammar_variants=("both",),
        kernel_class="elementwise",
        n=1,
        allow_small_matrix=True,
        validate=True,
    )

    assert "expected_row_count: 6" in markdown
    assert (
        "expected_grammar_variants: ['template_upper_bound reference "
        "(template G reference)', 'task_agnostic (task-agnostic G primary)']"
    ) in markdown
    assert "| G | template G reference | elementwise | fp32 |" in markdown
    assert "| G | task-agnostic G | elementwise | fp32 |" in markdown


def test_cluster1_figures_reject_non_template_g_variant() -> None:
    rows = [
        _make_result(
            grammar_active=condition == "G",
            grammar_variant="task_agnostic" if condition == "G" else None,
            masked_token_rate=0.25 if condition == "G" else None,
            dtype=dtype,
            kernel_class=kernel_class,
            kernel_name=f"{kernel_class}_{dtype}",
            generation_seed=seed,
            run_id=f"{condition}-{kernel_class}-{dtype}-{seed}",
            unique_solution_hash=f"{condition}-{kernel_class}-{dtype}-{seed}",
        )
        for condition in ("baseline", "G")
        for kernel_class in ("elementwise", "reduction", "matmul")
        for dtype in ("fp32", "fp16", "bf16")
        for seed in range(20)
    ]
    df = results_to_dataframe(rows)

    with pytest.raises(AssertionError):
        validate_integrity(df)


def _make_result(**overrides) -> GenerationResult:
    return GenerationResult(**_make_record(**overrides))


def _make_record(**overrides) -> dict[str, object]:
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
    if defaults["grammar_active"] is True and defaults["grammar_variant"] is None:
        defaults["grammar_variant"] = "template_upper_bound"
    return defaults


def _condition_rows(
    conditions: list[str],
    *,
    n: int,
    strict_success_cutoff: int | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cutoff = n if strict_success_cutoff is None else strict_success_cutoff
    for condition in conditions:
        grammar_active = condition == "G"
        for dtype in ("fp32", "fp16", "bf16"):
            for seed in range(n):
                compile_success = seed < cutoff
                compile_results_by_dtype = (
                    {"fp32": True, "fp16": True, "bf16": True}
                    if compile_success
                    else {"fp32": False, "fp16": False, "bf16": False}
                )
                rows.append(
                    _make_record(
                        grammar_active=grammar_active,
                        grammar_variant=(
                            "template_upper_bound" if grammar_active else None
                        ),
                        masked_token_rate=0.25 if grammar_active else None,
                        dtype=dtype,
                        compile_success=compile_success,
                        compile_results_by_dtype=compile_results_by_dtype,
                        compile_error_type=None if compile_success else "RuntimeError",
                        compile_error_msg=None if compile_success else "compile failed",
                        unique_solution_hash=f"{condition}-{dtype}-{seed}",
                        generation_seed=seed,
                        run_id=f"{condition}-elementwise-{dtype}-{seed}",
                    )
                )
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
