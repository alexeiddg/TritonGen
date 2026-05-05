"""
2^3 Factorial analysis across all three clusters.

The experiment is a 2³ full-factorial design:
  G (Grammar constraint)   — Cluster 1
  C (Compiler feedback)    — Cluster 2
  P (Performance feedback) — Cluster 3

This module combines per-cluster JSONL result files and computes:
  - Main effects: G, C, P on pass@k
  - Two-way interactions: G×C, G×P, C×P
  - Three-way interaction: G×C×P (additive vs interference)

Results feed directly into the thesis's interaction-effect hypothesis.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


FACTORS = ("grammar_active", "compiler_feedback_active", "perf_feedback_active")


def load_results(jsonl_path: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
    return pd.DataFrame(rows)


def merge_cluster_results(
    cluster1_path: Path | None = None,
    cluster2_path: Path | None = None,
    cluster3_path: Path | None = None,
) -> pd.DataFrame:
    """Merge JSONL result files from all clusters into one DataFrame.

    Missing cluster paths produce columns filled with False/NaN so partial
    analyses work before all clusters are complete.
    """
    frames = []
    for path, has_c, has_p in [
        (cluster1_path, False, False),
        (cluster2_path, True, False),
        (cluster3_path, True, True),
    ]:
        if path is not None and path.exists():
            df = load_results(path)
            if "compiler_feedback_active" not in df.columns:
                df["compiler_feedback_active"] = has_c
            if "perf_feedback_active" not in df.columns:
                df["perf_feedback_active"] = has_p
            frames.append(df)
    if not frames:
        raise ValueError("No result files provided.")
    return pd.concat(frames, ignore_index=True)


def factorial_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Group by all factor combinations and compute pass@1 mean per cell."""
    group_cols = [f for f in FACTORS if f in df.columns] + ["kernel_class", "dtype"]
    return (
        df.groupby(group_cols)["compile_success"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "n_correct", "count": "n_total"})
        .assign(pass_at_1=lambda x: x["n_correct"] / x["n_total"])
        .reset_index()
    )
