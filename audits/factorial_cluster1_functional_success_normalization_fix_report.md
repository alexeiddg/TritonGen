# Factorial Cluster 1 Functional Success Normalization Fix Report

## 1. Executive summary

Fix status: implemented and locally verified.

Final classification: FIX_VERIFIED.

The factorial analyzer now accepts Cluster 1 none/G compile-only rows that do not carry `functional_success`. For Cluster 1 scope, normalization sets `functional_success=False` and preserves `compile_success` as the separate compile metric.

## 2. Root cause

The analyzer normalized `functional_success` directly from each input payload. Cluster 1 result rows are compile-only artifacts and do not run Level 2 correctness, so they legitimately do not contain `functional_success`.

Primary normalization location:

- `shared/analysis/factorial.py`
- Function: `normalize_result_rows`
- Previous assumption: `functional_success` was read directly from the row payload and remained missing when Cluster 1 artifacts did not include it.

## 3. Methodological decision

Cluster 1 functional success normalizes to `False`.

Cluster 1 compile success remains preserved separately as `compile_success`.

This is methodologically required because `compile_success=True` in Cluster 1 proves only strict compile acceptance. It does not prove Level 2 numerical correctness, and Cluster 1 does not run Level 2.

## 4. Implementation summary

Files modified:

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`

Normalization changes:

- Added explicit Cluster 1 compile-only detection for none/G analyzer roles.
- Added source-path fallback detection for Cluster 1 artifact loads under `cluster1`.
- Added optional input role plumbing through `load_results`, `load_result_paths`, and CLI `--input-roles`.
- In `normalize_result_rows`, Cluster 1 compile-only rows force normalized `functional_success=False`.
- `compile_success` remains populated from the original row payload.

Cluster 2 behavior:

- C and G+C rows keep existing `functional_success` behavior.
- No Cluster 2 `compile_success` derivation from `failure_code` was implemented.

## 5. Tests added/updated

Added focused coverage in `shared/tests/test_factorial_analysis.py`:

- none role without `functional_success`, `compile_success=False`.
- G role without `functional_success`, `compile_success=True`.
- G role without `functional_success`, `compile_success=False`.
- G role with accidental `functional_success=True`, overridden to `False`.
- C role with existing `functional_success=True`, unchanged.
- Real Cluster 1 artifact samples from:
  - `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
  - `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

## 6. Validation results

Command:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or normalization or functional_success or compile_success" -q
```

Result:

- 52 passed
- 481 deselected

Command:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

paths = {
    "none": Path("outputs/cluster1/baseline_repaired_l4_n20.jsonl"),
    "g": Path("outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"),
}

for role, path in paths.items():
    if not path.exists():
        print(f"SKIP_MISSING {role} {path}")
        continue

    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(role, "rows", len(rows))
    print(role, "has_functional_success_count", sum("functional_success" in r for r in rows))
    print(role, "compile_success_true", sum(r.get("compile_success") is True for r in rows))
PY
```

Result:

- none rows: 180
- none raw `functional_success` fields: 0
- none raw `compile_success=True`: 0
- g rows: 177
- g raw `functional_success` fields: 0
- g raw `compile_success=True`: 3

Command:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

from shared.analysis.factorial import load_results

paths = {
    "none": Path("outputs/cluster1/baseline_repaired_l4_n20.jsonl"),
    "g": Path("outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"),
}

for role, path in paths.items():
    if not path.exists():
        print(f"SKIP_MISSING {role} {path}")
        continue
    df = load_results(path)
    print(role, "normalized_rows", len(df))
    print(role, "normalized_functional_success_true", int(df["functional_success"].astype(bool).sum()))
    print(role, "normalized_compile_success_true", int(df["compile_success"].astype(bool).sum()))
PY
```

Result:

- none normalized rows: 180
- none normalized `functional_success=True`: 0
- none normalized `compile_success=True`: 0
- g normalized rows: 177
- g normalized `functional_success=True`: 0
- g normalized `compile_success=True`: 3

Command:

```bash
.venv/bin/python -m shared.analysis.factorial --help
```

Result:

- passed
- help includes `--input-roles`

Command:

```bash
git diff --check
```

Result:

- passed

## 7. Remaining known out-of-scope issue

Cluster 2 `compile_success` derivation from `failure_code` remains out of scope and was not implemented.

If the analyzer reaches a workflow that requires Cluster 2 compile diagnostics for C/G+C rows that lack top-level `compile_success`, that remains the next normalization fix.

## 8. Next recommendation

PROCEED_TO_CLUSTER2_COMPILE_SUCCESS_NORMALIZATION_FIX
