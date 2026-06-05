from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("poster_graphs/.mplconfig").resolve()))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DATA_ROOT = Path("/private/tmp/tritongen_outputs_zip/outputs")
OUT_DIR = Path("poster_graphs")

CONDITION_FILES = {
    "none": DATA_ROOT / "cluster1/baseline_repaired_l4_n20.jsonl",
    "G": DATA_ROOT / "cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl",
    "C": DATA_ROOT / "cluster2/c_paper_n20_l4.jsonl",
    "G+C": DATA_ROOT / "cluster2/g_plus_c_paper_n20_l4.jsonl",
    "Claude": DATA_ROOT / "external/claude_baseline_n20.jsonl",
    "Gemini": DATA_ROOT / "external/gemini_baseline_n20.jsonl",
}

ORDER = ["none", "G", "C", "G+C", "Claude", "Gemini"]
DISPLAY = {
    "none": "none\nQwen 7B",
    "G": "G\nQwen 7B",
    "C": "C\nQwen 7B",
    "G+C": "G+C\nQwen 7B",
    "Claude": "Claude",
    "Gemini": "Gemini",
}
COLORS = {
    "none": "#94A3B8",
    "G": "#2563EB",
    "C": "#0EA5A4",
    "G+C": "#16A34A",
    "Claude": "#7C3AED",
    "Gemini": "#F97316",
}


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_all() -> dict[str, list[dict]]:
    return {condition: load_jsonl(path) for condition, path in CONDITION_FILES.items()}


def inferred_compile_success(row: dict, condition: str) -> bool:
    value = row.get("compile_success")
    if value is True:
        return True
    if value is False:
        return False
    # C does not serialize compile_success; all rows are F0_PARSE in this run.
    if condition == "C":
        return False
    return False


def inferred_failure_code(row: dict, condition: str) -> str:
    if inferred_compile_success(row, condition):
        return "L1_SUCCESS"
    code = row.get("failure_code")
    if code:
        return code
    if condition == "none":
        # Legacy schema; report classifies this baseline as F0_PARSE dominated.
        return "F0_PARSE"
    return "UNKNOWN"


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    phat = successes / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def compile_at_k(successes: int, n: int, k: int) -> float:
    if successes <= 0:
        return 0.0
    if k > n:
        k = n
    failures = n - successes
    if failures < k:
        return 1.0
    return 1.0 - math.comb(failures, k) / math.comb(n, k)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 240,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
        }
    )


def save_fig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


def plot_compile_success(all_rows: dict[str, list[dict]]) -> None:
    labels, rates, lows, highs, counts = [], [], [], [], []
    for condition in ORDER:
        rows = all_rows[condition]
        n = len(rows)
        ok = sum(inferred_compile_success(row, condition) for row in rows)
        lo, hi = wilson_interval(ok, n)
        labels.append(DISPLAY[condition])
        rates.append(ok / n * 100)
        lows.append((ok / n - lo) * 100)
        highs.append((hi - ok / n) * 100)
        counts.append((ok, n))

    fig, ax = plt.subplots(figsize=(10.6, 5.8))
    x = np.arange(len(labels))
    bars = ax.bar(
        x,
        rates,
        color=[COLORS[c] for c in ORDER],
        edgecolor="#0F172A",
        linewidth=0.6,
    )
    ax.errorbar(
        x,
        rates,
        yerr=np.array([lows, highs]),
        fmt="none",
        ecolor="#111827",
        capsize=4,
        linewidth=1,
    )
    ax.set_title("Tasa de compilación L1 por condición")
    ax.set_ylabel("compile_success L1 (%)")
    ax.set_ylim(0, 60)
    ax.set_xticks(x, labels)
    for bar, rate, (ok, n) in zip(bars, rates, counts, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{ok}/{n}\n{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#111827",
        )
    ax.text(
        0.01,
        -0.18,
        "Barras: porcentaje de kernels que compilan en Triton. Líneas: IC Wilson 95%.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    save_fig(OUT_DIR / "01_l1_compile_success_by_condition.png")


def plot_compile_at_k(all_rows: dict[str, list[dict]]) -> None:
    ks = [1, 5, 10]
    x = np.arange(len(ks))
    width = 0.12
    fig, ax = plt.subplots(figsize=(10.6, 5.8))
    for idx, condition in enumerate(ORDER):
        rows = all_rows[condition]
        n = len(rows)
        ok = sum(inferred_compile_success(row, condition) for row in rows)
        values = [compile_at_k(ok, n, k) * 100 for k in ks]
        offset = (idx - (len(ORDER) - 1) / 2) * width
        ax.bar(
            x + offset,
            values,
            width=width,
            label=DISPLAY[condition].replace("\n", " "),
            color=COLORS[condition],
            edgecolor="#0F172A",
            linewidth=0.35,
        )
    ax.set_title("Probabilidad de obtener al menos un kernel compilable")
    ax.set_ylabel("compile@k (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(x, [f"compile@{k}" for k in ks])
    ax.legend(ncols=3, loc="upper left", frameon=False)
    ax.text(
        0.01,
        -0.16,
        "compile@k mide compilación L1, no correctitud funcional L2.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    save_fig(OUT_DIR / "02_compile_at_k_by_condition.png")


def plot_failure_codes(all_rows: dict[str, list[dict]]) -> None:
    code_order = ["L1_SUCCESS", "F0_PARSE", "F0_BAD_SIGNATURE", "F1_COMPILE", "F1_RUNTIME", "F2_NUMERIC_NAN", "F3_EVAL_PIPELINE", "UNKNOWN"]
    code_colors = {
        "L1_SUCCESS": "#16A34A",
        "F0_PARSE": "#EF4444",
        "F0_BAD_SIGNATURE": "#F97316",
        "F1_COMPILE": "#F59E0B",
        "F1_RUNTIME": "#6366F1",
        "F2_NUMERIC_NAN": "#A855F7",
        "F3_EVAL_PIPELINE": "#64748B",
        "UNKNOWN": "#CBD5E1",
    }
    matrix = []
    for condition in ORDER:
        rows = all_rows[condition]
        counts = Counter(inferred_failure_code(row, condition) for row in rows)
        n = len(rows)
        matrix.append([counts.get(code, 0) / n * 100 for code in code_order])

    fig, ax = plt.subplots(figsize=(10.8, 5.9))
    bottom = np.zeros(len(ORDER))
    x = np.arange(len(ORDER))
    for code_idx, code in enumerate(code_order):
        values = [row[code_idx] for row in matrix]
        if max(values) == 0:
            continue
        ax.bar(
            x,
            values,
            bottom=bottom,
            label=code,
            color=code_colors[code],
            edgecolor="white",
            linewidth=0.4,
        )
        bottom += np.array(values)
    ax.set_title("Distribución de códigos de falla por condición")
    ax.set_ylabel("Porcentaje de muestras (%)")
    ax.set_ylim(0, 100)
    ax.set_xticks(x, [DISPLAY[c] for c in ORDER])
    ax.legend(ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    ax.text(
        0.01,
        -0.24,
        "Lectura: Gemini falla sobre todo en F0_PARSE; Claude y las condiciones con G avanzan más hacia F1_RUNTIME.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    save_fig(OUT_DIR / "03_failure_code_distribution.png")


def plot_kernel_class_breakdown(all_rows: dict[str, list[dict]]) -> None:
    kernel_order = ["elementwise", "reduction", "matmul"]
    x = np.arange(len(kernel_order))
    width = 0.12
    fig, ax = plt.subplots(figsize=(10.8, 5.9))
    for idx, condition in enumerate(ORDER):
        values = []
        for kernel in kernel_order:
            sub = [row for row in all_rows[condition] if row.get("kernel_class") == kernel]
            ok = sum(inferred_compile_success(row, condition) for row in sub)
            values.append(ok / len(sub) * 100 if sub else 0)
        offset = (idx - (len(ORDER) - 1) / 2) * width
        ax.bar(
            x + offset,
            values,
            width=width,
            color=COLORS[condition],
            label=DISPLAY[condition].replace("\n", " "),
            edgecolor="#0F172A",
            linewidth=0.35,
        )
    ax.set_title("Compilación L1 por tipo de kernel")
    ax.set_ylabel("compile_success L1 (%)")
    ax.set_ylim(0, 105)
    ax.set_xticks(x, ["ReLU\nelementwise", "Softmax\nreduction", "GEMM\nmatmul"])
    ax.legend(ncols=3, loc="upper right", frameon=False)
    ax.text(
        0.01,
        -0.16,
        "Claude domina en elementwise y reduction; matmul queda en 0% para todos.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    save_fig(OUT_DIR / "04_l1_compile_by_kernel_class.png")


def write_summary(all_rows: dict[str, list[dict]]) -> None:
    lines = ["condition,n,compile_success,compile_rate"]
    for condition in ORDER:
        rows = all_rows[condition]
        n = len(rows)
        ok = sum(inferred_compile_success(row, condition) for row in rows)
        lines.append(f"{condition},{n},{ok},{ok / n:.6f}")
    (OUT_DIR / "summary_compile_rates.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    setup_style()
    all_rows = load_all()
    plot_compile_success(all_rows)
    plot_compile_at_k(all_rows)
    plot_failure_codes(all_rows)
    plot_kernel_class_breakdown(all_rows)
    write_summary(all_rows)


if __name__ == "__main__":
    main()
