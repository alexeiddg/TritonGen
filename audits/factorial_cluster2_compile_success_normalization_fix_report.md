# Factorial Cluster 2 Compile Success Normalization Fix Report

## 1. Executive summary

Fix status: implemented and focused tests pass.

Final classification: `NEXT_BLOCKER_FOUND`. The analyzer now derives missing Cluster 2 `compile_success` from canonical `failure_code` and raises on explicit conflicts. The preliminary analyzer dry-run no longer fails because C rows lack `compile_success`; it now fails loudly on five existing G+C artifact rows where `failure_code=F3_EVAL_PIPELINE` but explicit `compile_success=false`.

No JSONL source artifacts, frozen artifacts, grammar files, hash records, Modal jobs, GPU jobs, generation jobs, or C/G+C experiments were modified or run.

## 2. Root cause

The factorial analyzer normalized `compile_success` only from a top-level `compile_success` field in `shared.analysis.factorial.normalize_result_rows`.

Cluster 2 generated rows can expose compile reachability through canonical terminal `failure_code` semantics. The local C paper artifact has 180 rows, zero top-level `compile_success` fields, and canonical `failure_code` on every row, so compile metrics could not be computed consistently across the 2² subset without analyzer-side normalization.

## 3. Methodological decision

For Cluster 2 generated rows only (`C`, `G+C`), compile reachability is derived from canonical failure code when top-level `compile_success` is absent or null:

- `failure_code is None`, `failure_code == ""`, any `F2_*`, or `F3_EVAL_PIPELINE` means the row reached Level 2, so `compile_success=True`.
- `F0_*` and `F1_*` mean the row did not compile successfully, so `compile_success=False`.
- Other F3 codes are not treated as compile success unless they are the eval-pipeline code.

The taxonomy has the exact eval-pipeline code `F3_EVAL_PIPELINE` in `shared/eval/failure_taxonomy.py`. Other present F3 codes are `F3_OOB`, `F3_RACE`, and `F3_TIMEOUT`; these are not treated as Level 2 compile reachability for this analyzer fix.

## 4. Implementation summary

Files modified:

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`

Normalization function changed:

- `normalize_result_rows`

Implementation details:

- Added `CLUSTER2_GENERATED_CONDITIONS = {"C", "G+C"}`.
- Added `CLUSTER2_EVAL_PIPELINE_FAILURE_CODE = "F3_EVAL_PIPELINE"`.
- Added `_normalize_compile_success(...)`.
- Added `_cluster2_compile_success_from_failure_code(...)`.
- Cluster 1 rows still use direct `_bool_or_none(payload.get("compile_success"))` behavior.

Exact Cluster 2 derivation rule:

```python
compile_success = (
    failure_code is None
    or failure_code == ""
    or failure_code.startswith("F2_")
    or failure_code == "F3_EVAL_PIPELINE"
)
```

## 5. Conflict behavior

If a Cluster 2 row has explicit boolean `compile_success`, the analyzer computes the failure-code-derived value and compares them.

If they agree, normalization preserves the explicit value.

If they conflict, normalization raises a `ValueError` with condition, source path, row index, explicit value, failure code, and derived value. Example conflict now detected in the real G+C artifact:

`condition='G+C', row_index=91, compile_success=False, failure_code='F3_EVAL_PIPELINE', derived_compile_success=True`.

## 6. Tests added/updated

Added focused coverage in `shared/tests/test_factorial_analysis.py` for:

- C row `F0_PARSE` derives `compile_success=False`.
- C row `F1_COMPILE` derives `compile_success=False`.
- C row `F2_NUMERIC_LARGE` derives `compile_success=True`.
- G+C row `F2_SHAPE_MISMATCH` derives `compile_success=True`.
- G+C row null and empty-string success failure codes derive `compile_success=True`.
- G+C row `F3_EVAL_PIPELINE` derives `compile_success=True`.
- Other F3 code `F3_TIMEOUT` derives `compile_success=False`.
- Explicit agreement: `F2_NUMERIC_NAN` plus `compile_success=True` succeeds.
- Explicit conflict: `F1_COMPILE` plus `compile_success=True` raises.
- Cluster 1 G behavior remains unchanged: compile success is preserved and functional success normalizes to false.
- Real Cluster 2 artifact samples normalize successfully after removing top-level `compile_success` from the in-memory sample rows.

## 7. Validation results

Required searches:

- `rg "compile_success|functional_success|failure_code|F2_|F3_EVAL_PIPELINE|F3_|factorial|normalize|normalization|Cluster 2|cluster2|condition|G\\+C|C\\b" shared cluster1 cluster2 tests`
  - Completed with exit code 2 because this repo has no top-level `tests` directory; relevant matches were returned from `shared`, `cluster1`, and `cluster2`.
- `rg "FAILURE_CODES|classify_failure|F0_|F1_|F2_|F3_" shared cluster2 cluster1 tests`
  - Completed with exit code 2 because this repo has no top-level `tests` directory; relevant matches were returned from `shared`, `cluster1`, and `cluster2`.
- `rg "baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|c_paper_n20_l4|g_plus_c_paper_n20_l4|factorial_2x2" shared outputs audits cluster1 cluster2`
  - Passed.

Focused analyzer tests:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or normalization or compile_success or failure_code" -q
```

Result: passed, `82 passed, 463 deselected`.

Failure taxonomy tests:

```bash
.venv/bin/python -m pytest shared/tests -k "failure_taxonomy or F3 or classify_failure" -q
```

Result: passed, `32 passed, 513 deselected`.

Real artifact inspection:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from collections import Counter

paths = {
    "c": Path("outputs/cluster2/c_paper_n20_l4.jsonl"),
    "gc": Path("outputs/cluster2/g_plus_c_paper_n20_l4.jsonl"),
}

for role, path in paths.items():
    if not path.exists():
        print(f"SKIP_MISSING {role} {path}")
        continue

    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(role, "rows", len(rows))
    print(role, "has_compile_success_count", sum("compile_success" in r for r in rows))
    print(role, "failure_code_counts", dict(Counter(r.get("failure_code") for r in rows)))
PY
```

Result:

- C: 180 rows, 0 rows with top-level `compile_success`, failure codes `{"F0_PARSE": 180}`.
- G+C: 177 rows, 177 rows with top-level `compile_success`, failure codes `{"F2_NUMERIC_NAN": 4, "F1_RUNTIME": 146, "F1_COMPILE": 10, "F0_PARSE": 12, "F3_EVAL_PIPELINE": 5}`.

## 8. Analyzer dry-run status

CLI help passed:

```bash
.venv/bin/python -m shared.analysis.factorial --help
```

The current CLI supports `--inputs` and `--input-roles`; it does not expose separate `--none`, `--g`, `--c`, or `--gc` flags.

Equivalent preliminary dry-run attempted:

```bash
.venv/bin/python -m shared.analysis.factorial \
  --inputs outputs/cluster1/baseline_repaired_l4_n20.jsonl \
           outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl \
           outputs/cluster2/c_paper_n20_l4.jsonl \
           outputs/cluster2/g_plus_c_paper_n20_l4.jsonl \
  --input-roles none g c gc \
  --output /private/tmp/factorial_2x2_preliminary.json
```

Result: failed before output was produced because the new consistency guard found an explicit G+C artifact conflict:

`Cluster 2 compile_success conflicts with failure_code-derived semantics for condition='G+C', source_path='outputs/cluster2/g_plus_c_paper_n20_l4.jsonl', row_index=91: compile_success=False, failure_code='F3_EVAL_PIPELINE', derived_compile_success=True`

Additional read-only conflict count:

- C: 180 missing `compile_success`, 0 explicit conflicts.
- G+C: 0 missing `compile_success`, 5 explicit conflicts.
- Conflicting G+C rows:
  - row 91: reduction/softmax/fp16/base_seed 11, `F3_EVAL_PIPELINE`, explicit false, derived true.
  - row 144: matmul/gemm/fp16/base_seed 5, `F3_EVAL_PIPELINE`, explicit false, derived true.
  - row 148: matmul/gemm/fp16/base_seed 9, `F3_EVAL_PIPELINE`, explicit false, derived true.
  - row 165: matmul/gemm/bf16/base_seed 7, `F3_EVAL_PIPELINE`, explicit false, derived true.
  - row 169: matmul/gemm/bf16/base_seed 11, `F3_EVAL_PIPELINE`, explicit false, derived true.

## 9. Next recommendation

`INVESTIGATE_NEXT_ANALYZER_BLOCKER`

The normalization fix is implemented and tested, but the current G+C artifact contains explicit `compile_success` values that conflict with the required `F3_EVAL_PIPELINE` method. The next step should investigate whether those G+C rows need an artifact/schema correction, a read-time adapter exception, or a methodological decision that differs from the stated rule.
