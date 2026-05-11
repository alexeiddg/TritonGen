"""Tests for Cluster 1 JSONL result validation."""

from __future__ import annotations

import json
from pathlib import Path

from cluster1.experiments.validate_cluster1_results import (
    DTYPES,
    main,
    validate_cluster1_results,
)


def test_valid_baseline_n1(tmp_path: Path) -> None:
    path = tmp_path / "baseline.jsonl"
    _write_jsonl(path, _rows(["baseline"], n=1))

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert report.passed
    assert report.row_count == 3
    assert report.observed_conditions == ("baseline",)
    assert report.observed_grammar_variants == (None,)


def test_valid_g_n1(tmp_path: Path) -> None:
    path = tmp_path / "g.jsonl"
    _write_jsonl(path, _rows(["G"], n=1))

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
    )

    assert report.passed
    assert report.row_count == 3
    assert report.observed_conditions == ("G",)
    assert report.observed_grammar_variants == ("template_upper_bound",)


def test_valid_both_n2(tmp_path: Path) -> None:
    path = tmp_path / "both.jsonl"
    _write_jsonl(path, _rows(["baseline", "G"], n=2))

    report = validate_cluster1_results(
        path,
        condition="both",
        kernel_class="elementwise",
        n=2,
    )

    assert report.passed
    assert report.row_count == 12
    assert report.observed_conditions == ("G", "baseline")
    assert report.observed_grammar_variants == (None, "template_upper_bound")


def test_valid_g_task_agnostic_variant_n1(tmp_path: Path) -> None:
    path = tmp_path / "g_task.jsonl"
    _write_jsonl(path, _rows(["G"], n=1, grammar_variant="task_agnostic"))

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
        grammar_variants=("task_agnostic",),
    )

    assert report.passed
    assert report.observed_grammar_variants == ("task_agnostic",)


def test_missing_variant_cell_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing_variant.jsonl"
    _write_jsonl(path, _rows(["G"], n=1, grammar_variant="template_upper_bound"))

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
        grammar_variants=("template_upper_bound", "task_agnostic"),
    )

    assert not report.passed
    assert report.expected_row_count == 6
    assert report.row_count_failures
    assert report.missing_cells
    assert any("task_agnostic" in cell for cell in report.missing_cells)


def test_duplicate_identity_within_variant_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate_variant.jsonl"
    rows = _rows(["G"], n=1, grammar_variant="template_upper_bound")
    rows.append(dict(rows[0], run_id="duplicate-run"))
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.duplicate_identities
    assert any("template_upper_bound" in item for item in report.duplicate_identities)


def test_legacy_g_rows_without_variant_load_as_template_upper_bound(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy_g.jsonl"
    rows = _rows(["G"], n=1)
    for row in rows:
        row.pop("grammar_variant")
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
    )

    assert report.passed
    assert report.observed_grammar_variants == ("template_upper_bound",)


def test_missing_row(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"
    rows = _rows(["baseline"], n=1)
    _write_jsonl(path, rows[:-1])

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.row_count_failures
    assert report.missing_cells


def test_wrong_masked_token_rate_for_baseline(tmp_path: Path) -> None:
    path = tmp_path / "bad_baseline_mask.jsonl"
    rows = _rows(["baseline"], n=1)
    rows[0]["masked_token_rate"] = 0.25
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.invariant_failures
    assert report.masked_token_rate_failures


def test_baseline_requires_null_grammar_variant(tmp_path: Path) -> None:
    path = tmp_path / "bad_baseline_variant.jsonl"
    rows = _rows(["baseline"], n=1)
    rows[0]["grammar_variant"] = "template_upper_bound"
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.invariant_failures


def test_invalid_grammar_variant_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad_variant.jsonl"
    rows = _rows(["G"], n=1)
    rows[0]["grammar_variant"] = "bogus"
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.invariant_failures


def test_missing_masked_token_rate_for_g(tmp_path: Path) -> None:
    path = tmp_path / "bad_g_mask.jsonl"
    rows = _rows(["G"], n=1)
    rows[0]["masked_token_rate"] = None
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="G",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.invariant_failures
    assert report.masked_token_rate_failures


def test_missing_dtype_in_compile_results_by_dtype(tmp_path: Path) -> None:
    path = tmp_path / "missing_compile_dtype.jsonl"
    rows = _rows(["baseline"], n=1)
    rows[2]["compile_results_by_dtype"] = {"fp32": True, "fp16": True}
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert any("bf16" in failure for failure in report.compile_results_by_dtype_failures)
    assert any(
        "prompt_dtype_compile_success" in failure
        for failure in report.compile_results_by_dtype_failures
    )


def test_malformed_compile_results_by_dtype_is_reported_not_crashed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "malformed_compile_dtype.jsonl"
    rows = _rows(["baseline"], n=1)
    rows[0]["compile_results_by_dtype"] = None
    rows[1]["compile_results_by_dtype"] = ["fp32", "fp16", "bf16"]
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert len(report.deserialization_failures) == 2
    assert "compile_results_by_dtype must be an object" in report.render()


def test_compile_success_must_be_strict_all_dtype(tmp_path: Path) -> None:
    path = tmp_path / "bad_strict_compile.jsonl"
    rows = _rows(["baseline"], n=1)
    rows[0]["compile_success"] = True
    rows[0]["compile_results_by_dtype"] = {
        "fp32": True,
        "fp16": False,
        "bf16": True,
    }
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert any(
        "strict all-dtype acceptance=False" in failure
        for failure in report.compile_results_by_dtype_failures
    )


def test_duplicate_row_identity(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.jsonl"
    rows = _rows(["baseline"], n=1)
    rows.append(dict(rows[0], run_id="duplicate-run"))
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.duplicate_identities
    assert report.row_count_failures


def test_duplicate_row_identity_can_be_allowed(tmp_path: Path) -> None:
    path = tmp_path / "duplicate_allowed.jsonl"
    rows = _rows(["baseline"], n=1)
    rows.append(dict(rows[0], run_id="duplicate-run"))
    _write_jsonl(path, rows)

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
        allow_duplicate_identities=True,
    )

    assert not report.duplicate_identities
    assert report.row_count_failures


def test_unexpected_condition_cell(tmp_path: Path) -> None:
    path = tmp_path / "unexpected_condition.jsonl"
    _write_jsonl(path, _rows(["G"], n=1))

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
    )

    assert not report.passed
    assert report.unexpected_cells
    assert report.missing_cells
    assert report.observed_conditions == ("G",)


def test_expected_row_count_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "wrong_count.jsonl"
    _write_jsonl(path, _rows(["baseline"], n=1))

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=2,
    )

    assert not report.passed
    assert report.expected_row_count == 6
    assert report.row_count_failures
    assert report.missing_cells


def test_require_full_n20_rejects_smoke_n(tmp_path: Path) -> None:
    path = tmp_path / "smoke.jsonl"
    _write_jsonl(path, _rows(["baseline"], n=1))

    report = validate_cluster1_results(
        path,
        condition="baseline",
        kernel_class="elementwise",
        n=1,
        require_full_n20=True,
    )

    assert not report.passed
    assert report.sample_size_failures


def test_cli_returns_failure_for_invalid_file(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.jsonl"
    _write_jsonl(path, _rows(["G"], n=1))

    rc = main(
        [
            "--input",
            str(path),
            "--condition",
            "baseline",
            "--kernel-class",
            "elementwise",
            "--n",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "Cluster 1 result validation: FAIL" in captured.out


def _rows(
    conditions: list[str],
    *,
    n: int,
    kernel_class: str = "elementwise",
    grammar_variant: str = "template_upper_bound",
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for condition in conditions:
        grammar_active = condition == "G"
        for dtype in DTYPES:
            for seed in range(n):
                rows.append(
                    _make_record(
                        grammar_active=grammar_active,
                        grammar_variant=grammar_variant if grammar_active else None,
                        masked_token_rate=0.25 if grammar_active else None,
                        kernel_class=kernel_class,
                        dtype=dtype,
                        generation_seed=seed,
                        run_id=f"{condition}-{kernel_class}-{dtype}-{seed}",
                    )
                )
    return rows


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
    return defaults


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
