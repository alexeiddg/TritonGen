"""Phase 8 analysis for Cluster 1 compile-success records."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import fields
from pathlib import Path

import pandas as pd

from cluster1.results.dataclass import GenerationResult


REQUIRED_GROUP_SIZE = 20


def pass_at_k(n: int, c: int, k: int) -> float:
    """Return the unbiased HumanEval pass@k estimate."""

    if n < 0:
        raise ValueError("n must be non-negative")
    if c < 0 or c > n:
        raise ValueError("c must satisfy 0 <= c <= n")
    if k <= 0:
        raise ValueError("k must be positive")
    if k > n:
        raise ValueError("k must be <= n")
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def unique_solution_rate(rows: list[GenerationResult]) -> float:
    """Return the fraction of rows with distinct normalized solution hashes."""

    if not rows:
        return 0.0
    return len({row.unique_solution_hash for row in rows}) / len(rows)


def summarize_results(jsonl_path: Path) -> pd.DataFrame:
    """Summarize pass@k and diversity from Cluster 1 JSONL output."""

    rows = _load_jsonl_rows(jsonl_path)
    records: list[dict[str, object]] = []
    groups: dict[tuple[str, bool, str], list[GenerationResult]] = {}
    for row in rows:
        key = (row.kernel_class, row.grammar_active, row.dtype)
        groups.setdefault(key, []).append(row)

    for (kernel_class, grammar_active, dtype), group_rows in sorted(groups.items()):
        n = len(group_rows)
        if n < REQUIRED_GROUP_SIZE:
            raise ValueError(
                "expected at least "
                f"{REQUIRED_GROUP_SIZE} rows for "
                f"kernel_class={kernel_class!r}, "
                f"grammar_active={grammar_active!r}, dtype={dtype!r}; got {n}"
            )

        correct = sum(1 for row in group_rows if row.compile_success)
        records.append(
            {
                "kernel_class": kernel_class,
                "grammar_active": grammar_active,
                "dtype": dtype,
                "n": n,
                "compile_successes": correct,
                "compile_failures": n - correct,
                "pass@1": pass_at_k(n, correct, 1),
                "pass@5": pass_at_k(n, correct, 5),
                "pass@10": pass_at_k(n, correct, 10),
                "unique_solution_rate": unique_solution_rate(group_rows),
            }
        )

    return pd.DataFrame.from_records(records)


def null_hypothesis_report(jsonl_path: Path, output_markdown: Path) -> None:
    """Write pass@k summary and grammar OFF vs ON failure comparison."""

    summary = summarize_results(jsonl_path)
    comparison_lines = _null_hypothesis_lines(summary)
    markdown = "\n".join(
        [
            "# Cluster 1 Phase 8 Summary",
            "",
            "## pass@k and Diversity",
            "",
            _summary_markdown(summary),
            "",
            "## Null-Hypothesis Report",
            "",
            *comparison_lines,
            "",
        ]
    )
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(markdown, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Cluster 1 JSONL results.")
    parser.add_argument("--input", type=Path, required=True, help="Path to result JSONL records.")
    parser.add_argument("--output", type=Path, required=True, help="Path to Markdown report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    null_hypothesis_report(args.input, args.output)
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
    for column in ("pass@1", "pass@5", "pass@10", "unique_solution_rate"):
        display[column] = display[column].map(lambda value: f"{value:.6f}")
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
    for (kernel_class, dtype), group in summary.groupby(["kernel_class", "dtype"], sort=True):
        by_condition = {bool(row.grammar_active): row for row in group.itertuples(index=False)}
        off = by_condition.get(False)
        on = by_condition.get(True)
        label = f"`kernel_class={kernel_class}`, `dtype={dtype}`"
        if off is None or on is None:
            lines.append(
                f"- Anomaly for {label}: expected both grammar OFF and ON rows; "
                f"observed {len(group)} condition group(s). DoD #7 requires documentation."
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


if __name__ == "__main__":
    raise SystemExit(main())
