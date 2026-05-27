"""Triton JIT compile evaluator for external API baselines.

Reads the JSONL files produced by run_external_baselines.py, attempts Triton
JIT compilation for each generated kernel (same check_compiles_all_dtypes gate
used by Cluster 1), updates compile_success and failure_code in-place, and
prints a summary table.

GPU REQUIREMENT — THIS SCRIPT REQUIRES:
    - Linux (Triton does not install on macOS/Windows)
    - NVIDIA CUDA GPU
    - CUDA toolkit installed
    - triton + torch (CUDA build) installed

If running locally on macOS or a CPU-only machine, use the Modal path instead:
    python eval_external_baselines.py --modal

Usage (local, Linux+GPU):
    python eval_external_baselines.py

Usage (Modal, any machine):
    python eval_external_baselines.py --modal
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EXTERNAL_DIR = Path("outputs/external")
DEFAULT_FILES = [
    EXTERNAL_DIR / "claude_baseline_n20.jsonl",
    EXTERNAL_DIR / "gemini_baseline_n20.jsonl",
]


# ---------------------------------------------------------------------------
# Local compile path (Linux + GPU only)
# ---------------------------------------------------------------------------

def _compile_local(source: str, kernel_class: str) -> dict:
    """Run Triton JIT compile check via cluster1.validation.compile_check."""
    from cluster1.data.kernels import get_kernel_spec
    from cluster1.validation.compile_check import check_compiles_all_dtypes
    from shared.eval.failure_taxonomy import canonical_failure_code_from_compile_error

    try:
        spec = get_kernel_spec(kernel_class)
    except KeyError as exc:
        return {
            "compile_success": False,
            "compile_error_type": "SignatureError",
            "compile_error_msg": str(exc),
            "failure_code": "F0_BAD_SIGNATURE",
            "compile_results_by_dtype": {"fp32": False, "fp16": False, "bf16": False},
            "n_shapes_tested": 0,
        }

    try:
        results = check_compiles_all_dtypes(source, spec.compile_spec, spec.shapes_by_dtype)
    except Exception as exc:
        return {
            "compile_success": False,
            "compile_error_type": "UnknownError",
            "compile_error_msg": str(exc)[:500],
            "failure_code": "F1_RUNTIME",
            "compile_results_by_dtype": {"fp32": False, "fp16": False, "bf16": False},
            "n_shapes_tested": 0,
        }

    compile_success = all(r.success for r in results)
    by_dtype = {r.dtype: r.success for r in results}
    first_fail = next((r for r in results if not r.success), None)
    n_shapes = sum(r.n_shapes_tested for r in results)

    return {
        "compile_success": compile_success,
        "compile_error_type": first_fail.error_type if first_fail else None,
        "compile_error_msg": first_fail.error_msg if first_fail else None,
        "failure_code": (
            first_fail.failure_code
            if first_fail and first_fail.failure_code
            else canonical_failure_code_from_compile_error(
                first_fail.error_type if first_fail else None,
                first_fail.error_msg if first_fail else None,
            )
            if first_fail
            else None
        ),
        "compile_results_by_dtype": by_dtype,
        "n_shapes_tested": n_shapes,
    }


# ---------------------------------------------------------------------------
# Modal compile path (runs on remote L4 GPU)
# ---------------------------------------------------------------------------

def _compile_modal(source: str, kernel_class: str, kernel_name: str) -> dict:
    """Run Triton JIT compile check via Modal (any host machine)."""
    import uuid
    from cluster1.validation.modal_compile_check import check_compiles_modal

    result = check_compiles_modal(
        source=source,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        factor_cell="none",
        run_id=str(uuid.uuid4()),
    )
    return {
        "compile_success": result.compile_success,
        "compile_error_type": result.compile_error_type,
        "compile_error_msg": result.compile_error_msg,
        "failure_code": result.failure_code,
        "compile_results_by_dtype": result.compile_results_by_dtype,
        "n_shapes_tested": result.n_shapes_tested,
    }


# ---------------------------------------------------------------------------
# JSONL read/write
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def _print_summary(all_rows: dict[str, list[dict]]) -> None:
    print("\n" + "=" * 72)
    print("COMPILE SUCCESS SUMMARY")
    print("=" * 72)

    kernel_classes = ["elementwise", "matmul", "reduction"]
    dtypes = ["fp32", "fp16", "bf16"]

    for condition, rows in all_rows.items():
        print(f"\n  Condition: {condition}  (n={len(rows)})")

        # Overall
        n_with_field = sum(1 for r in rows if r.get("compile_success") is not None)
        n_ok = sum(1 for r in rows if r.get("compile_success") is True)
        if n_with_field > 0:
            print(f"  Overall: {n_ok}/{n_with_field}  ({n_ok/n_with_field*100:.1f}%)")
        else:
            print("  Overall: not yet evaluated")

        # By kernel_class
        print("  By kernel_class:")
        for kc in kernel_classes:
            sub = [r for r in rows if r.get("kernel_class") == kc]
            ev = [r for r in sub if r.get("compile_success") is not None]
            ok = sum(1 for r in ev if r.get("compile_success") is True)
            rate = f"{ok/len(ev)*100:.1f}%" if ev else "N/A"
            print(f"    {kc:15s}  n={len(sub)}  evaluated={len(ev)}  ok={ok}  rate={rate}")

        # By dtype
        print("  By dtype:")
        for dt in dtypes:
            sub = [r for r in rows if r.get("dtype") == dt]
            ev = [r for r in sub if r.get("compile_success") is not None]
            ok = sum(1 for r in ev if r.get("compile_success") is True)
            rate = f"{ok/len(ev)*100:.1f}%" if ev else "N/A"
            print(f"    {dt:6s}  n={len(sub)}  evaluated={len(ev)}  ok={ok}  rate={rate}")

        # By kernel × dtype
        print("  By kernel_class × dtype:")
        for kc in kernel_classes:
            for dt in dtypes:
                sub = [r for r in rows
                       if r.get("kernel_class") == kc and r.get("dtype") == dt]
                ev = [r for r in sub if r.get("compile_success") is not None]
                ok = sum(1 for r in ev if r.get("compile_success") is True)
                rate = f"{ok/len(ev)*100:.1f}%" if ev else "N/A"
                print(f"    {kc:15s} × {dt:6s}  n={len(sub)}  ok={ok}  rate={rate}")

        # Failure code distribution
        if any(r.get("failure_code") for r in rows):
            import collections
            fc_dist = collections.Counter(
                r.get("failure_code") for r in rows
                if r.get("compile_success") is not None
            )
            print("  failure_code distribution:")
            for code, cnt in fc_dist.most_common():
                print(f"    {str(code):25s}  count={cnt}  ({cnt/len(rows)*100:.1f}%)")


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def evaluate(paths: list[Path], use_modal: bool = False, force: bool = False) -> None:
    all_rows: dict[str, list[dict]] = {}

    for path in paths:
        if not path.exists():
            print(f"  [skip] {path} not found")
            continue

        rows = _load_jsonl(path)
        condition = path.stem  # e.g. "claude_baseline_n20"
        all_rows[condition] = rows

        needs_eval = [
            (i, r) for i, r in enumerate(rows)
            if force or r.get("compile_success") is None
        ]
        print(f"\n{path.name}  ({len(rows)} rows, {len(needs_eval)} need evaluation)")

        if not needs_eval:
            print("  All rows already evaluated.")
            continue

        modified = False
        for idx, (row_idx, row) in enumerate(needs_eval):
            source = row.get("source", "")
            kernel_class = row.get("kernel_class", "")
            kernel_name = row.get("kernel_name", "")
            cell = f"{kernel_name} × {row.get('dtype')} × seed={row.get('generation_seed')}"

            print(f"  [{idx+1}/{len(needs_eval)}] {cell}", end=" ", flush=True)

            if not source:
                result = {
                    "compile_success": False,
                    "compile_error_type": "SignatureError",
                    "compile_error_msg": "empty source",
                    "failure_code": "F0_PARSE",
                    "compile_results_by_dtype": {"fp32": False, "fp16": False, "bf16": False},
                    "n_shapes_tested": 0,
                }
            elif use_modal:
                try:
                    result = _compile_modal(source, kernel_class, kernel_name)
                except Exception as exc:
                    print(f"→ MODAL ERROR: {exc}")
                    result = {
                        "compile_success": False,
                        "compile_error_type": "UnknownError",
                        "compile_error_msg": str(exc)[:500],
                        "failure_code": "F1_RUNTIME",
                        "compile_results_by_dtype": {},
                        "n_shapes_tested": 0,
                    }
            else:
                try:
                    result = _compile_local(source, kernel_class)
                except Exception as exc:
                    print(f"→ LOCAL ERROR: {exc}")
                    result = {
                        "compile_success": False,
                        "compile_error_type": "UnknownError",
                        "compile_error_msg": str(exc)[:500],
                        "failure_code": "F1_RUNTIME",
                        "compile_results_by_dtype": {},
                        "n_shapes_tested": 0,
                    }

            status = "OK" if result["compile_success"] else result.get("failure_code", "FAIL")
            print(f"→ {status}")

            rows[row_idx].update(result)
            modified = True

        if modified:
            _write_jsonl(path, rows)
            print(f"  Updated {path}")

    _print_summary(all_rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate external baseline JSONL files with Triton JIT compile check."
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        default=DEFAULT_FILES,
        help="JSONL files to evaluate (default: outputs/external/*.jsonl)",
    )
    parser.add_argument(
        "--modal",
        action="store_true",
        help=(
            "Run compile check via Modal (remote L4 GPU). "
            "Use this when not on a Linux+CUDA machine."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-evaluate rows that already have compile_success set.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary table without running new evaluations.",
    )
    args = parser.parse_args()

    if not args.modal and not args.summary_only:
        # Attempt a quick import check for the local path
        try:
            import triton  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            print(
                f"\nERROR: {exc}\n"
                "Local Triton JIT compilation requires Linux + CUDA GPU + triton installed.\n"
                "On macOS or a CPU-only machine, use --modal to run via Modal:\n"
                "    python eval_external_baselines.py --modal\n"
                "Or use --summary-only to print summary of already-evaluated rows.",
                file=sys.stderr,
            )
            return 1

    paths = args.files
    if not any(p.exists() for p in paths):
        print(
            "No input files found. Run run_external_baselines.py first.",
            file=sys.stderr,
        )
        return 1

    if args.summary_only:
        all_rows = {}
        for path in paths:
            if path.exists():
                rows = _load_jsonl(path)
                all_rows[path.stem] = rows
        _print_summary(all_rows)
        return 0

    evaluate(paths, use_modal=args.modal, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
