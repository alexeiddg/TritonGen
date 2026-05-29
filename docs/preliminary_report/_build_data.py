"""
Compute aggregate data for the preliminary HTML report.

Reads:
- outputs/analysis/factorial_2x2_preliminary.json (authoritative for headline numbers)
- outputs/cluster1/baseline_repaired_l4_n20.jsonl  (none)
- outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl  (G)
- outputs/cluster2/c_paper_n20_l4.jsonl  (C)
- outputs/cluster2/g_plus_c_paper_n20_l4.jsonl  (G+C)
- outputs/cluster1/final_g_l4_n20.jsonl  (template-G upper-bound reference, optional)

Emits a single dict written to docs/preliminary_report/_report_data.json.
"""

import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ARTIFACTS = {
    "none": REPO_ROOT / "outputs/cluster1/baseline_repaired_l4_n20.jsonl",
    "G":    REPO_ROOT / "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl",
    "C":    REPO_ROOT / "outputs/cluster2/c_paper_n20_l4.jsonl",
    "G+C":  REPO_ROOT / "outputs/cluster2/g_plus_c_paper_n20_l4.jsonl",
}
TEMPLATE_G_REF = REPO_ROOT / "outputs/cluster1/final_g_l4_n20.jsonl"
ANALYZER = REPO_ROOT / "outputs/analysis/factorial_2x2_preliminary.json"


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _row_failure_code(row):
    """
    Classify a row into a failure-mode bucket.

    Cluster 1 rows (none, G) have only compile_success bool + compile_error_type.
    Cluster 2 rows (C, G+C) have failure_code / functional_success.
    Returns one of:
      success, F0_PARSE, F0_BAD_SIGNATURE, F1_COMPILE, F1_RUNTIME,
      F2_NUMERIC, F3_EVAL_PIPELINE, OTHER
    """
    # Cluster 2 path: failure_code present
    fc = row.get("failure_code")
    if row.get("functional_success") is True:
        return "success"
    if fc:
        if fc == "F0_PARSE":
            return "F0_PARSE"
        if fc == "F0_BAD_SIGNATURE":
            return "F0_BAD_SIGNATURE"
        if fc == "F1_COMPILE":
            return "F1_COMPILE"
        if fc == "F1_RUNTIME":
            return "F1_RUNTIME"
        if fc.startswith("F2_"):
            return "F2_NUMERIC"
        if fc == "F3_EVAL_PIPELINE":
            return "F3_EVAL_PIPELINE"
        return "OTHER"
    # Cluster 1 path
    if row.get("compile_success") is True:
        # Compiled but no failure_code → runtime/numeric on the matched-shape probe
        # In Cluster 1 we don't have post-compile evaluation; treat as 'compile_only_success'
        return "compile_only"
    et = row.get("compile_error_type")
    if et in ("SignatureError",):
        return "F0_BAD_SIGNATURE"
    if et == "SyntaxError":
        return "F0_PARSE"
    return "F1_COMPILE"


def _is_compile_success(row, condition):
    """
    Compile success per analyzer policy.
    - Cluster 1: row['compile_success'] bool
    - Cluster 2: derive from failure_code (F1_COMPILE/F0_*/F3 = no; everything else after compile = yes)
                 Cluster 2 G+C rows have an explicit compile_success bool too.
    """
    if "compile_success" in row and isinstance(row["compile_success"], bool):
        return row["compile_success"]
    fc = row.get("failure_code")
    if not fc:
        return bool(row.get("functional_success"))
    # Anything past F1_COMPILE/F0_* implies compile succeeded
    if fc.startswith("F0_") or fc == "F1_COMPILE":
        return False
    if fc == "F3_EVAL_PIPELINE":
        # Per F3 policy: excluded; treat as not-compile-success when no independent evidence
        return False
    return True  # F1_RUNTIME, F2_*, success → compiled


def aggregate():
    out = {"conditions": {}, "per_cell_compile": {}, "failure_modes": {},
           "repair": {}, "totals": {}}

    for cond, path in ARTIFACTS.items():
        rows = load_jsonl(path)
        out["totals"][cond] = len(rows)

        # Per-cell compile rates: keyed by (kernel_class, dtype)
        per_cell = {}
        per_cell_n = {}
        # Failure mode counts
        fm_counts = Counter()
        # Repair counts
        f2_reached = 0
        repair_lengths = []

        for r in rows:
            kc = r.get("kernel_class", "unknown")
            dt = r.get("dtype", "unknown")
            cell_key = f"{kc}/{dt}"
            per_cell.setdefault(cell_key, 0)
            per_cell_n.setdefault(cell_key, 0)
            per_cell_n[cell_key] += 1
            if _is_compile_success(r, cond):
                per_cell[cell_key] += 1

            fm = _row_failure_code(r)
            fm_counts[fm] += 1

            rt = r.get("repair_trace")
            if isinstance(rt, list) and rt:
                repair_lengths.append(len(rt))
                fc = r.get("failure_code", "")
                if fc.startswith("F2_"):
                    f2_reached += 1

        out["per_cell_compile"][cond] = {
            ck: {"successes": per_cell[ck], "n": per_cell_n[ck]}
            for ck in per_cell
        }
        out["failure_modes"][cond] = dict(fm_counts)
        out["repair"][cond] = {
            "f2_reached": f2_reached,
            "repair_trace_lengths": Counter(repair_lengths),
        }

    # Optional template-G reference
    if TEMPLATE_G_REF.exists():
        rows = load_jsonl(TEMPLATE_G_REF)
        out["totals"]["Template_G"] = len(rows)
        n_compile = sum(1 for r in rows if r.get("compile_success") is True)
        out["template_g_reference"] = {
            "n": len(rows), "compile_successes": n_compile,
            "compile_rate": n_compile / len(rows) if rows else 0.0,
        }

    # Pull headline numbers + diagnostics from analyzer JSON
    with open(ANALYZER) as f:
        analyzer = json.load(f)
    out["analyzer"] = {
        "condition_rates": analyzer["condition_rates"],
        "paired_comparisons": analyzer["paired_comparisons"],
        "factorial_model": analyzer["factorial_model"],
        "diagnostics_grammar": analyzer["diagnostics"]["grammar_acceptance_summary"],
        "diagnostics_rejection": analyzer["diagnostics"]["rejection_layer_breakdown"],
        "diagnostics_stop_reason": analyzer["diagnostics"]["stop_reason_breakdown"],
        "metadata": analyzer["metadata"],
        "missing_treatment_pairs": [
            pc.get("missing_treatment_pairs", [])
            for pc in analyzer["paired_comparisons"]
            if pc.get("response_variable") == "compile_success"
        ],
    }

    return out


if __name__ == "__main__":
    data = aggregate()
    # Convert Counters to dicts for JSON serialization
    for cond, rd in data["repair"].items():
        rd["repair_trace_lengths"] = {str(k): v for k, v in rd["repair_trace_lengths"].items()}
    out_path = Path(__file__).parent / "_report_data.json"
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Wrote {out_path}")
    print()
    print("=== summary ===")
    for cond in ("none", "G", "C", "G+C"):
        n = data["totals"][cond]
        successes = sum(
            data["per_cell_compile"][cond][ck]["successes"]
            for ck in data["per_cell_compile"][cond]
        )
        print(f"  {cond}: n={n}, compile_successes={successes}")
    print()
    print("Failure modes:")
    for cond in ("none", "G", "C", "G+C"):
        print(f"  {cond}: {data['failure_modes'][cond]}")
    print()
    print("Repair:")
    for cond in ("none", "G", "C", "G+C"):
        print(f"  {cond}: {data['repair'][cond]}")
    print()
    if "template_g_reference" in data:
        print(f"Template G ref: {data['template_g_reference']}")
