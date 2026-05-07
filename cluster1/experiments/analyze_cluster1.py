"""Phase 8 analysis for Cluster 1 compile-only records.

Analyzer semantics:
- ``compile_success`` is strict all-dtype compile acceptance.
- ``prompt_dtype_compile_success`` is derived from
  ``compile_results_by_dtype[row.dtype]``.
- Cluster 1 analysis is compile-only and does not execute future-level checks.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path

import pandas as pd

from cluster1.experiments.validate_cluster1_results import (
    Cluster1ValidationReport,
    validate_cluster1_results,
)
from cluster1.results.dataclass import GenerationResult
from shared.eval.metrics.pass_at_k import compile_at_1, pass_at_k


REQUIRED_GROUP_SIZE = 20
COMPILE_SUCCESS_SCOPE = "all_dtype_strict"
PASS_K_VALUES = (1, 5, 10)


def unique_solution_rate(rows: list[GenerationResult]) -> float:
    """Return the fraction of rows with distinct normalized solution hashes."""

    if not rows:
        return 0.0
    return len({row.unique_solution_hash for row in rows}) / len(rows)


def prompt_dtype_compile_success(row: GenerationResult) -> bool:
    """Return compile success for the prompt dtype represented by ``row``."""

    if row.dtype not in row.compile_results_by_dtype:
        raise ValueError(
            f"run_id={row.run_id!r} missing compile_results_by_dtype[{row.dtype!r}]"
        )
    return bool(row.compile_results_by_dtype[row.dtype])


def summarize_results(
    jsonl_path: Path,
    *,
    min_group_size: int = REQUIRED_GROUP_SIZE,
    allow_small_matrix: bool = False,
) -> pd.DataFrame:
    """Summarize pass@k and diversity from Cluster 1 JSONL output."""

    rows = _load_jsonl_rows(jsonl_path)
    records: list[dict[str, object]] = []
    groups: dict[tuple[str, str, bool, str], list[GenerationResult]] = {}
    for row in rows:
        key = (
            _condition_for_row(row),
            row.kernel_class,
            row.grammar_active,
            row.dtype,
        )
        groups.setdefault(key, []).append(row)

    for (condition, kernel_class, grammar_active, dtype), group_rows in sorted(
        groups.items()
    ):
        n = len(group_rows)
        if not allow_small_matrix and n < min_group_size:
            raise ValueError(
                "expected at least "
                f"{min_group_size} rows for "
                f"condition={condition!r}, "
                f"kernel_class={kernel_class!r}, "
                f"grammar_active={grammar_active!r}, dtype={dtype!r}; got {n}"
            )

        correct = sum(1 for row in group_rows if row.compile_success)
        prompt_dtype_correct = sum(
            1 for row in group_rows if prompt_dtype_compile_success(row)
        )
        pass_values = {
            f"pass@{k}": _pass_at_k_or_none(
                n,
                correct,
                k,
                allow_small_matrix=allow_small_matrix,
            )
            for k in PASS_K_VALUES
        }
        records.append(
            {
                "condition": condition,
                "kernel_class": kernel_class,
                "grammar_active": grammar_active,
                "dtype": dtype,
                "n": n,
                "compile_success_scope": COMPILE_SUCCESS_SCOPE,
                "compile_successes": correct,
                "compile_failures": n - correct,
                "compile@1": compile_at_1(correct, n),
                "prompt_dtype_compile_successes": prompt_dtype_correct,
                "prompt_dtype_compile_failures": n - prompt_dtype_correct,
                "prompt_dtype_compile_success_rate": prompt_dtype_correct / n,
                **pass_values,
                "unique_solution_rate": unique_solution_rate(group_rows),
            }
        )

    return pd.DataFrame.from_records(records)


def null_hypothesis_report(
    jsonl_path: Path,
    output_markdown: Path,
    *,
    condition: str | None = None,
    kernel_class: str | None = None,
    n: int | None = None,
    allow_small_matrix: bool = False,
    validate: bool = False,
    require_full_n20: bool = False,
) -> None:
    """Write pass@k summary and grammar OFF vs ON failure comparison."""

    markdown = build_compile_summary_markdown(
        jsonl_path,
        condition=condition,
        kernel_class=kernel_class,
        n=n,
        allow_small_matrix=allow_small_matrix,
        validate=validate,
        require_full_n20=require_full_n20,
    )
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(markdown, encoding="utf-8")


def build_compile_summary_markdown(
    jsonl_path: Path,
    *,
    condition: str | None = None,
    kernel_class: str | None = None,
    n: int | None = None,
    allow_small_matrix: bool = False,
    validate: bool = False,
    require_full_n20: bool = False,
) -> str:
    """Return a Cluster 1 compile-only Markdown report."""

    validation_report = _maybe_validate(
        jsonl_path,
        condition=condition,
        kernel_class=kernel_class,
        n=n,
        validate=validate,
        require_full_n20=require_full_n20,
    )
    rows = _load_jsonl_rows(jsonl_path)
    summary = summarize_results(
        jsonl_path,
        allow_small_matrix=allow_small_matrix,
    )
    comparison_lines = _null_hypothesis_lines(summary)
    markdown = "\n".join(
        [
            "# Cluster 1 Compile-Only Summary",
            "",
            "## Run Shape",
            "",
            *_run_shape_lines(rows, validation_report),
            "",
            "## Compile Metrics",
            "",
            "compile_success_scope: all_dtype_strict",
            "",
            _summary_markdown(summary),
            "",
            "## Masked Token Rate",
            "",
            _masked_token_rate_markdown(rows),
            "",
            "## Compile Error Types",
            "",
            _compile_error_distribution_markdown(rows),
            "",
            "## Null-Hypothesis Report",
            "",
            *comparison_lines,
            "",
        ]
    )
    return markdown


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze Cluster 1 compile-only JSONL results. compile_success is "
            "strict all-dtype acceptance; prompt_dtype_compile_success is "
            "derived from compile_results_by_dtype[row.dtype]."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to result JSONL records.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to Markdown report.",
    )
    parser.add_argument("--condition", choices=("baseline", "G", "both"))
    parser.add_argument(
        "--kernel-class",
        choices=("elementwise", "reduction", "matmul", "all"),
    )
    parser.add_argument("--n", type=int)
    parser.add_argument(
        "--allow-small-matrix",
        action="store_true",
        help=(
            "Allow n<20 smoke/small-matrix summaries. pass@k with k>n "
            "is reported as NA."
        ),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run Cluster 1 JSONL validation before analysis.",
    )
    parser.add_argument(
        "--require-full-n20",
        action="store_true",
        help="Require --n 20 and fail analysis on validation failures.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    null_hypothesis_report(
        args.input,
        args.output,
        condition=args.condition,
        kernel_class=args.kernel_class,
        n=args.n,
        allow_small_matrix=args.allow_small_matrix,
        validate=args.validate,
        require_full_n20=args.require_full_n20,
    )
    return 0


def _load_jsonl_rows(jsonl_path: Path) -> list[GenerationResult]:
    field_names = {field.name for field in fields(GenerationResult)}
    rows: list[GenerationResult] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            result_fields = {key: record[key] for key in field_names if key in record}
            missing = field_names - set(result_fields)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ValueError(f"{jsonl_path}:{line_number} missing fields: {missing_text}")
            rows.append(GenerationResult(**result_fields))
    return rows


def _summary_markdown(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "No result rows found."

    display = summary.copy()
    for column in (
        "compile@1",
        "prompt_dtype_compile_success_rate",
        "pass@1",
        "pass@5",
        "pass@10",
        "unique_solution_rate",
    ):
        display[column] = display[column].map(_format_metric)
    columns = list(display.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in display.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _null_hypothesis_lines(summary: pd.DataFrame) -> list[str]:
    if summary.empty:
        return ["No result rows found; DoD #7 cannot be evaluated."]

    lines: list[str] = []
    for (kernel_class, dtype), group in summary.groupby(
        ["kernel_class", "dtype"],
        sort=True,
    ):
        by_condition = {str(row.condition): row for row in group.itertuples(index=False)}
        off = by_condition.get("baseline")
        on = by_condition.get("G")
        label = f"`kernel_class={kernel_class}`, `dtype={dtype}`"
        if off is None or on is None:
            lines.append(
                f"- {label}: comparison requires both baseline and G rows; "
                f"observed {len(group)} condition group(s)."
            )
            continue

        off_failures = int(off.compile_failures)
        on_failures = int(on.compile_failures)
        eliminated = off_failures - on_failures
        if off_failures > 0 and eliminated > 0:
            lines.append(
                f"- {label}: grammar ON eliminated {eliminated} compile failure(s) "
                f"({off_failures} OFF failures vs {on_failures} ON failures)."
            )
        else:
            lines.append(
                f"- Anomaly for {label}: OFF failures={off_failures}, "
                f"ON failures={on_failures}. DoD #7 requires documentation."
            )
    return lines


def _maybe_validate(
    jsonl_path: Path,
    *,
    condition: str | None,
    kernel_class: str | None,
    n: int | None,
    validate: bool,
    require_full_n20: bool,
) -> Cluster1ValidationReport | None:
    if condition is None or kernel_class is None or n is None:
        if validate or require_full_n20:
            raise ValueError(
                "--validate/--require-full-n20 require "
                "--condition, --kernel-class, and --n"
            )
        return None

    report = validate_cluster1_results(
        jsonl_path,
        condition=condition,
        kernel_class=kernel_class,
        n=n,
        require_full_n20=require_full_n20,
    )
    if (validate or require_full_n20) and not report.passed:
        raise ValueError(
            "Cluster 1 validation failed before analysis:\n" + report.render()
        )
    return report


def _run_shape_lines(
    rows: list[GenerationResult],
    validation_report: Cluster1ValidationReport | None,
) -> list[str]:
    lines = [f"row_count: {len(rows)}"]
    actual_cells = sorted(
        {
            (_condition_for_row(row), row.kernel_class, row.dtype)
            for row in rows
        }
    )
    lines.append(f"actual_cells: {len(actual_cells)}")

    if validation_report is None:
        lines.append("expected_cells: not requested")
        return lines

    lines.extend(
        [
            f"expected_row_count: {validation_report.expected_row_count}",
            f"expected_conditions: {list(validation_report.expected_conditions)}",
            f"actual_conditions: {list(validation_report.observed_conditions)}",
            f"expected_kernel_classes: {list(validation_report.expected_kernel_classes)}",
            f"actual_kernel_classes: {list(validation_report.observed_kernel_classes)}",
            f"expected_dtypes: {list(validation_report.expected_dtypes)}",
            f"actual_dtypes: {list(validation_report.observed_dtypes)}",
            f"missing_cells: {len(validation_report.missing_cells)}",
            f"unexpected_cells: {len(validation_report.unexpected_cells)}",
            f"duplicate_identities: {len(validation_report.duplicate_identities)}",
        ]
    )
    return lines


def _masked_token_rate_markdown(rows: list[GenerationResult]) -> str:
    g_rows = [row for row in rows if row.grammar_active]
    if not g_rows:
        return "No G rows found."

    groups: dict[tuple[str, str], list[float]] = {}
    for row in g_rows:
        if row.masked_token_rate is None:
            continue
        groups.setdefault((row.kernel_class, row.dtype), []).append(
            row.masked_token_rate
        )

    if not groups:
        return "No non-null G masked_token_rate values found."

    lines = [
        "| condition | kernel_class | dtype | n | mean | min | max |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for (kernel_class, dtype), values in sorted(groups.items()):
        mean = sum(values) / len(values)
        lines.append(
            "| G | "
            f"{kernel_class} | {dtype} | {len(values)} | "
            f"{mean:.6f} | {min(values):.6f} | {max(values):.6f} |"
        )
    return "\n".join(lines)


def _compile_error_distribution_markdown(rows: list[GenerationResult]) -> str:
    if not rows:
        return "No result rows found."

    counts: dict[tuple[str, str, str, str], int] = {}
    for row in rows:
        error_type = row.compile_error_type or "None"
        key = (_condition_for_row(row), row.kernel_class, row.dtype, error_type)
        counts[key] = counts.get(key, 0) + 1

    lines = [
        "| condition | kernel_class | dtype | compile_error_type | count |",
        "| --- | --- | --- | --- | --- |",
    ]
    for (condition, kernel_class, dtype, error_type), count in sorted(counts.items()):
        lines.append(
            f"| {condition} | {kernel_class} | {dtype} | {error_type} | {count} |"
        )
    return "\n".join(lines)


def _condition_for_row(row: GenerationResult) -> str:
    return "G" if row.grammar_active else "baseline"


def _pass_at_k_or_none(
    n: int,
    c: int,
    k: int,
    *,
    allow_small_matrix: bool,
) -> float | None:
    if k > n and allow_small_matrix:
        return None
    return pass_at_k(n, c, k)


def _format_metric(value: object) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
