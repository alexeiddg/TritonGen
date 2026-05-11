"""Reproducible Cluster 1 compile-acceptance tables and figures.

This module consumes only the frozen Cluster 1 JSONL artifact. It does not run
generation, compilation, correctness, or performance workflows.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
ARTIFACT_PATH: Final = REPO_ROOT / "outputs/cluster1/final_none_vs_g_l4_n20.jsonl"
FIGURE_DIR: Final = REPO_ROOT / "outputs/cluster1/figures"

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/tritongen-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/tritongen-cache")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

from cluster1.results.dataclass import GenerationResult, validate_result_invariants
from shared.eval.metrics.pass_at_k import pass_at_k


CONDITIONS: Final = ("baseline", "G")
KERNEL_CLASSES: Final = ("elementwise", "reduction", "matmul")
DTYPES: Final = ("fp32", "fp16", "bf16")
PASS_K_VALUES: Final = (1, 5, 10)

CONDITION_COLORS: Final = {
    "baseline": "#6b7280",
    "G": "#2563eb",
}


def load_generation_results(jsonl_path: Path = ARTIFACT_PATH) -> list[GenerationResult]:
    """Load JSONL records as GenerationResult instances."""

    field_names = {field.name for field in fields(GenerationResult)}
    rows: list[GenerationResult] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            result_fields = {key: record[key] for key in field_names if key in record}
            missing = field_names - set(result_fields)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise ValueError(f"{jsonl_path}:{line_number} missing fields: {missing_text}")
            result = GenerationResult(**result_fields)
            validate_result_invariants(result)
            rows.append(result)
    return rows


def results_to_dataframe(rows: list[GenerationResult]) -> pd.DataFrame:
    """Convert GenerationResult rows to a pandas DataFrame with stable sort order."""

    df = pd.DataFrame.from_records(asdict(row) for row in rows)
    if df.empty:
        return df

    df["condition"] = df["grammar_active"].map({False: "baseline", True: "G"})
    df["condition"] = pd.Categorical(df["condition"], CONDITIONS, ordered=True)
    df["kernel_class"] = pd.Categorical(df["kernel_class"], KERNEL_CLASSES, ordered=True)
    df["dtype"] = pd.Categorical(df["dtype"], DTYPES, ordered=True)
    df["compile_error_type_label"] = df["compile_error_type"].fillna("None/success")
    return df.sort_values(
        ["condition", "kernel_class", "dtype", "generation_seed"],
        ignore_index=True,
    )


def validate_integrity(df: pd.DataFrame) -> None:
    """Assert the frozen Cluster 1 n=20 two-condition design."""

    assert len(df) == 360, f"expected 360 rows, got {len(df)}"

    condition_counts = df.groupby("condition", observed=False).size().reindex(CONDITIONS)
    assert int(condition_counts["baseline"]) == 180, condition_counts.to_dict()
    assert int(condition_counts["G"]) == 180, condition_counts.to_dict()

    assert set(df["kernel_class"].dropna().astype(str)) == set(KERNEL_CLASSES)
    assert set(df["dtype"].dropna().astype(str)) == set(DTYPES)

    expected_index = pd.MultiIndex.from_product(
        [CONDITIONS, KERNEL_CLASSES, DTYPES],
        names=["condition", "kernel_class", "dtype"],
    )
    cell_counts = (
        df.groupby(["condition", "kernel_class", "dtype"], observed=False)
        .size()
        .reindex(expected_index, fill_value=0)
    )
    bad_cells = cell_counts[cell_counts != 20]
    assert bad_cells.empty, bad_cells.to_dict()

    baseline_mask = df["condition"].astype(str) == "baseline"
    g_mask = df["condition"].astype(str) == "G"
    assert df.loc[baseline_mask, "masked_token_rate"].isna().all()
    assert df.loc[g_mask, "masked_token_rate"].notna().all()

    duplicate_columns = ["condition", "kernel_class", "dtype", "generation_seed"]
    duplicates = df[df.duplicated(duplicate_columns, keep=False)]
    assert duplicates.empty, duplicates[duplicate_columns + ["run_id"]].to_dict("records")


def make_headline_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return condition-level compile acceptance."""

    table = (
        df.groupby("condition", observed=False)
        .agg(
            compile_successes=("compile_success", "sum"),
            total=("compile_success", "size"),
        )
        .reindex(CONDITIONS)
        .reset_index()
    )
    table["compile_successes"] = table["compile_successes"].astype(int)
    table["total"] = table["total"].astype(int)
    table["compile_failures"] = table["total"] - table["compile_successes"]
    table["compile@1"] = table["compile_successes"] / table["total"]
    return table[["condition", "compile_successes", "compile_failures", "compile@1"]]


def make_per_kernel_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return compile acceptance by condition and kernel class."""

    table = (
        df.groupby(["condition", "kernel_class"], observed=False)
        .agg(
            compile_successes=("compile_success", "sum"),
            total=("compile_success", "size"),
        )
        .reindex(pd.MultiIndex.from_product([CONDITIONS, KERNEL_CLASSES]))
        .reset_index()
        .rename(columns={"level_0": "condition", "level_1": "kernel_class"})
    )
    table["compile_successes"] = table["compile_successes"].astype(int)
    table["total"] = table["total"].astype(int)
    table["compile_rate"] = table["compile_successes"] / table["total"]
    return table[["condition", "kernel_class", "compile_successes", "total", "compile_rate"]]


def make_per_dtype_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return compile acceptance by condition, kernel class, and dtype."""

    index = pd.MultiIndex.from_product(
        [CONDITIONS, KERNEL_CLASSES, DTYPES],
        names=["condition", "kernel_class", "dtype"],
    )
    table = (
        df.groupby(["condition", "kernel_class", "dtype"], observed=False)
        .agg(
            compile_successes=("compile_success", "sum"),
            total=("compile_success", "size"),
        )
        .reindex(index)
        .reset_index()
    )
    table["compile_successes"] = table["compile_successes"].astype(int)
    table["total"] = table["total"].astype(int)
    table["compile_rate"] = table["compile_successes"] / table["total"]
    return table[
        ["condition", "kernel_class", "dtype", "compile_successes", "total", "compile_rate"]
    ]


def make_failure_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return compile error type counts by condition."""

    table = (
        df.groupby(["condition", "compile_error_type_label"], observed=False)
        .size()
        .rename("count")
        .reset_index()
    )
    return table.sort_values(["condition", "compile_error_type_label"], ignore_index=True)


def make_masked_token_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return G-only masked-token diagnostics by kernel class."""

    g_df = df[df["condition"].astype(str) == "G"]
    table = (
        g_df.groupby("kernel_class", observed=False)["masked_token_rate"]
        .agg(["count", "mean", "std", "min", "max"])
        .reindex(KERNEL_CLASSES)
        .reset_index()
    )
    return table


def make_diversity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return unique solution hash diversity by condition and kernel class."""

    table = (
        df.groupby(["condition", "kernel_class"], observed=False)
        .agg(
            unique_count=("unique_solution_hash", "nunique"),
            total=("unique_solution_hash", "size"),
        )
        .reindex(pd.MultiIndex.from_product([CONDITIONS, KERNEL_CLASSES]))
        .reset_index()
        .rename(columns={"level_0": "condition", "level_1": "kernel_class"})
    )
    table["unique_count"] = table["unique_count"].astype(int)
    table["total"] = table["total"].astype(int)
    table["unique_rate"] = table["unique_count"] / table["total"]
    return table[["condition", "kernel_class", "unique_count", "total", "unique_rate"]]


def make_pass_at_k_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return compile-only pass@k by condition and kernel class."""

    records: list[dict[str, object]] = []
    grouped = df.groupby(["condition", "kernel_class"], observed=False)
    for condition in CONDITIONS:
        for kernel_class in KERNEL_CLASSES:
            group = grouped.get_group((condition, kernel_class))
            total = len(group)
            successes = int(group["compile_success"].sum())
            record: dict[str, object] = {
                "condition": condition,
                "kernel_class": kernel_class,
                "compile_successes": successes,
                "total": total,
            }
            for k in PASS_K_VALUES:
                record[f"pass@{k}"] = pass_at_k(total, successes, k)
            records.append(record)
    return pd.DataFrame.from_records(records)


def make_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute all Cluster 1 notebook tables."""

    return {
        "headline": make_headline_table(df),
        "per_kernel": make_per_kernel_table(df),
        "per_dtype": make_per_dtype_table(df),
        "failure": make_failure_table(df),
        "masked_token": make_masked_token_table(df),
        "diversity": make_diversity_table(df),
        "pass_at_k": make_pass_at_k_table(df),
    }


def write_all_figures(
    df: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    figure_dir: Path = FIGURE_DIR,
) -> dict[str, Path]:
    """Write all thesis-ready Cluster 1 PNG figures."""

    figure_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "headline": figure_dir / "compile_acceptance_headline.png",
        "by_kernel": figure_dir / "compile_acceptance_by_kernel.png",
        "failure": figure_dir / "failure_distribution.png",
        "masked_token": figure_dir / "masked_token_rate_by_kernel.png",
        "diversity": figure_dir / "diversity_by_kernel.png",
        "pass_at_k": figure_dir / "compile_pass_at_k.png",
    }

    plot_headline_compile(tables["headline"], paths["headline"])
    plot_compile_by_kernel(tables["per_kernel"], paths["by_kernel"])
    plot_failure_distribution(tables["failure"], paths["failure"])
    plot_masked_token_rate(df, paths["masked_token"])
    plot_diversity(tables["diversity"], paths["diversity"])
    plot_pass_at_k(tables["pass_at_k"], paths["pass_at_k"])
    return paths


def plot_headline_compile(table: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    x = range(len(CONDITIONS))
    rates = table.set_index("condition").reindex(CONDITIONS)["compile@1"]
    bars = ax.bar(
        x,
        rates,
        color=[CONDITION_COLORS[condition] for condition in CONDITIONS],
        width=0.58,
    )
    ax.set_title("Cluster 1 Compile Acceptance: Baseline vs Grammar")
    ax.set_ylabel("compile@1")
    ax.set_xticks(list(x), CONDITIONS)
    _format_rate_axis(ax)
    for bar, condition in zip(bars, CONDITIONS, strict=True):
        row = table[table["condition"].astype(str) == condition].iloc[0]
        label = f"{int(row['compile_successes'])}/{int(row['compile_successes'] + row['compile_failures'])}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(float(row["compile@1"]) + 0.035, 1.03),
            label,
            ha="center",
            va="bottom",
            fontsize=10,
        )
    _save_figure(fig, output_path)


def plot_compile_by_kernel(table: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.25))
    x_positions = list(range(len(KERNEL_CLASSES)))
    width = 0.34
    for offset, condition in [(-width / 2, "baseline"), (width / 2, "G")]:
        rates = (
            table[table["condition"].astype(str) == condition]
            .set_index("kernel_class")
            .reindex(KERNEL_CLASSES)["compile_rate"]
        )
        ax.bar(
            [x + offset for x in x_positions],
            rates,
            width=width,
            label=condition,
            color=CONDITION_COLORS[condition],
        )
    ax.set_title("Compile@1 by Kernel Family")
    ax.set_ylabel("compile@1")
    ax.set_xticks(x_positions, KERNEL_CLASSES)
    ax.legend(frameon=False)
    _format_rate_axis(ax)
    _save_figure(fig, output_path)


def plot_failure_distribution(table: pd.DataFrame, output_path: Path) -> None:
    pivot = (
        table.pivot(index="condition", columns="compile_error_type_label", values="count")
        .fillna(0)
        .reindex(CONDITIONS)
    )
    ordered_columns = [
        label
        for label in ["SignatureError", "CompilationError", "RuntimeError", "None/success"]
        if label in pivot.columns
    ]
    remaining_columns = [label for label in pivot.columns if label not in ordered_columns]
    pivot = pivot[ordered_columns + sorted(remaining_columns)]

    fig, ax = plt.subplots(figsize=(7.0, 4.25))
    bottoms = [0] * len(CONDITIONS)
    colors = {
        "SignatureError": "#9ca3af",
        "CompilationError": "#ef4444",
        "RuntimeError": "#f59e0b",
        "None/success": "#2563eb",
    }
    for label in pivot.columns:
        values = pivot[label].astype(int).to_list()
        ax.bar(
            CONDITIONS,
            values,
            bottom=bottoms,
            label=str(label),
            color=colors.get(str(label), "#111827"),
        )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values, strict=True)]
    ax.set_title("Compile Error Type Distribution")
    ax.set_ylabel("count")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    _save_figure(fig, output_path)


def plot_masked_token_rate(df: pd.DataFrame, output_path: Path) -> None:
    g_df = df[df["condition"].astype(str) == "G"]
    values = [
        g_df[g_df["kernel_class"].astype(str) == kernel_class]["masked_token_rate"].dropna()
        for kernel_class in KERNEL_CLASSES
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.boxplot(values, tick_labels=KERNEL_CLASSES, showmeans=True)
    ax.set_title("G Masked Token Rate by Kernel Family")
    ax.set_ylabel("masked_token_rate")
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    fig.text(
        0.5,
        0.02,
        "masked_token_rate is a constraint-strength diagnostic, not quality/performance.",
        ha="center",
        fontsize=9,
    )
    _save_figure(fig, output_path, rect=(0, 0.07, 1, 1))


def plot_diversity(table: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    x_positions = list(range(len(KERNEL_CLASSES)))
    width = 0.34
    for offset, condition in [(-width / 2, "baseline"), (width / 2, "G")]:
        rates = (
            table[table["condition"].astype(str) == condition]
            .set_index("kernel_class")
            .reindex(KERNEL_CLASSES)["unique_rate"]
        )
        ax.bar(
            [x + offset for x in x_positions],
            rates,
            width=width,
            label=condition,
            color=CONDITION_COLORS[condition],
        )
    ax.set_title("Unique Solution Hash Rate by Kernel Family")
    ax.set_ylabel("unique solution rate")
    ax.set_xticks(x_positions, KERNEL_CLASSES)
    ax.legend(frameon=False)
    _format_rate_axis(ax)
    fig.text(
        0.5,
        0.02,
        "Tight grammar may reduce diversity; interpret alongside compile acceptance.",
        ha="center",
        fontsize=9,
    )
    _save_figure(fig, output_path, rect=(0, 0.07, 1, 1))


def plot_pass_at_k(table: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, len(PASS_K_VALUES), figsize=(11.0, 4.0), sharey=True)
    x_positions = list(range(len(KERNEL_CLASSES)))
    width = 0.34
    for ax, k in zip(axes, PASS_K_VALUES, strict=True):
        metric = f"pass@{k}"
        for offset, condition in [(-width / 2, "baseline"), (width / 2, "G")]:
            rates = (
                table[table["condition"].astype(str) == condition]
                .set_index("kernel_class")
                .reindex(KERNEL_CLASSES)[metric]
            )
            ax.bar(
                [x + offset for x in x_positions],
                rates,
                width=width,
                label=condition,
                color=CONDITION_COLORS[condition],
            )
        ax.set_title(metric)
        ax.set_xticks(x_positions, KERNEL_CLASSES, rotation=20, ha="right")
        _format_rate_axis(ax)
    axes[0].set_ylabel("compile-only pass@k")
    axes[-1].legend(frameon=False, loc="upper right")
    fig.suptitle("Compile-Only pass@k by Kernel Family")
    _save_figure(fig, output_path, rect=(0, 0, 1, 0.93))


def _format_rate_axis(ax: plt.Axes) -> None:
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
    ax.set_axisbelow(True)


def _save_figure(
    fig: plt.Figure,
    output_path: Path,
    rect: tuple[float, float, float, float] | None = None,
) -> None:
    fig.tight_layout(rect=rect)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def build_cluster1_visualizations(
    jsonl_path: Path = ARTIFACT_PATH,
    figure_dir: Path = FIGURE_DIR,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Path]]:
    """Load, validate, summarize, and plot the frozen Cluster 1 artifact."""

    rows = load_generation_results(jsonl_path)
    df = results_to_dataframe(rows)
    validate_integrity(df)
    tables = make_tables(df)
    figure_paths = write_all_figures(df, tables, figure_dir)
    return df, tables, figure_paths


def main() -> int:
    df, tables, figure_paths = build_cluster1_visualizations()
    print(f"validated rows: {len(df)}")
    print(tables["headline"].to_string(index=False))
    print("figures:")
    for path in figure_paths.values():
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
