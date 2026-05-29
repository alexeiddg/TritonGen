# F3 Eval Pipeline Compile Success Decision Report

## 1. Executive summary

Status: `FIX_VERIFIED_BUT_ANALYZER_BLOCKED`

Initial status recorded before analyzer edits: `HOLD_FOR_METHOD_DECISION`.

Chosen option: Option A, strict infrastructure/eval-pipeline failure.

Analyzer output status: `outputs/analysis/factorial_2x2_preliminary.json` was not generated. The F3 contradiction is fixed, and all four inputs now normalize, but the full analyzer next fails on a separate paired-metadata requirement for raw Cluster 1 control rows: `missing paired replay metadata: replay_pair_id`.

Final classification: `FIX_VERIFIED_BUT_ANALYZER_BLOCKED`.

No JSONL artifacts, frozen artifacts, grammar files, hashes, Modal jobs, GPU jobs, generation jobs, C runs, or G+C runs were modified or invoked.

## 2. Problem statement

The G+C artifact contains rows with:

- `compile_success=false`
- `failure_code=F3_EVAL_PIPELINE`

Before this fix, the factorial analyzer derived `compile_success=true` for `F3_EVAL_PIPELINE`, creating a semantic contradiction:

- artifact says compile did not succeed,
- analyzer-derived rule says compile succeeded.

That caused the analyzer to halt before producing `outputs/analysis/factorial_2x2_preliminary.json`.

## 3. Current analyzer rule

File/function:

- `shared/analysis/factorial.py`
- `_normalize_compile_success`
- `_cluster2_compile_success_from_failure_code`

Old rule:

```python
compile_success = (
    failure_code is None
    or failure_code == ""
    or failure_code.startswith("F2_")
    or failure_code == "F3_EVAL_PIPELINE"
)
```

The rule was hardcoded in the analyzer. It was not inherited from `shared/eval/failure_taxonomy.py`; the taxonomy only registers `F3_EVAL_PIPELINE` as a canonical code and preserves explicit canonical codes. The old analyzer did not inspect independent Level 1 evidence such as `level1_success`, `level_reached`, `compile_result`, `correctness_result`, trace/debug payloads, or terminal reason. It inferred compile success solely from the F3 code string.

The rule appears intentional as a previous Cluster 2 missing-field normalization, but methodologically under-evidenced for the actual G+C rows.

## 4. Artifact evidence

Artifact inspected:

- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

Read-only counts:

- total rows: 177
- `F3_EVAL_PIPELINE` rows: 5
- failure codes: `F2_NUMERIC_NAN=4`, `F1_RUNTIME=146`, `F1_COMPILE=10`, `F0_PARSE=12`, `F3_EVAL_PIPELINE=5`
- compile success counts: `true=4`, `false=173`
- F3 compile pairs: 5 rows with `("F3_EVAL_PIPELINE", false)`

F3 rows by cell:

- `reduction/fp16`: 1
- `matmul/fp16`: 2
- `matmul/bf16`: 2

Example identities:

- `reduction/fp16/base_seed=11`
- `matmul/fp16/base_seed=5`
- `matmul/fp16/base_seed=9`
- `matmul/bf16/base_seed=7`
- `matmul/bf16/base_seed=11`

Evidence assessment:

- Each F3 row has explicit top-level `compile_success=false`.
- Each F3 row has `functional_success=false`, `repair_set_success=false`, and `eval_set_success=false`.
- Each trace summary says the correctness payload was malformed and missing `correctness_result`.
- Persisted rows do not include independent `level1_success`, `compile_result`, or top-level `level_reached` evidence proving compile success.
- Generated metadata shows grammar rejection details and generation provenance, not Level 1 compile pass evidence.

Conclusion: the rows do not prove Level 1 compile success. The malformed payload could not be defensibly reclassified as compile success from the persisted row evidence.

## 5. Methodology decision

Decision: Option A, strict infrastructure/eval-pipeline failure.

Rationale:

- The artifact explicitly records `compile_success=false`.
- The rows do not carry independent proof that Level 1 compile passed.
- `F3_EVAL_PIPELINE` means the evaluation pipeline/payload failed before a valid correctness measurement was available.
- Treating these as compile successes would inflate the secondary compile diagnostic from code-string inference alone.
- The conservative interpretation is defensible for the preliminary report and matches the original synthetic malformed-payload writer behavior.

## 6. Analyzer/schema policy after fix

Cluster 1 behavior is unchanged.

Cluster 2 compile-success normalization after the fix:

- explicit `compile_success` is preserved unless it conflicts with hard terminal evidence,
- `failure_code is None` or `failure_code == ""` derives `compile_success=true`,
- `F2_*` derives `compile_success=true`,
- `F0_*` and `F1_*` derive `compile_success=false`,
- `F3_EVAL_PIPELINE` derives `compile_success=false` unless independent Level 1/Level 2 evidence is present,
- explicit `compile_success=false` with `F3_EVAL_PIPELINE` is accepted when no independent compile-pass evidence exists.

Conflict behavior preserved:

- `F0_* + compile_success=true` fails,
- `F1_* + compile_success=true` fails,
- `F2_* + compile_success=false` fails,
- `F3_EVAL_PIPELINE + compile_success=false + independent Level 1/2 evidence` fails.

Functional-success behavior and statistical tests were not changed.

## 7. Tests added/updated

Updated `shared/tests/test_factorial_analysis.py`:

- `F3_EVAL_PIPELINE` missing `compile_success` now normalizes to false without Level 1 evidence.
- `F3_EVAL_PIPELINE` with explicit `compile_success=false` loads without contradiction.
- `F3_EVAL_PIPELINE` with independent Level 1/2 evidence can normalize to true.
- `F3_EVAL_PIPELINE` with explicit false plus independent Level 1/2 evidence fails loudly.
- `F2_NUMERIC_LARGE` with missing `compile_success` still derives true.
- `F2_NUMERIC_LARGE` with explicit `compile_success=false` still fails loudly.
- `F1_COMPILE` with missing `compile_success` still derives false.
- Existing real G+C artifact F3 rows normalize without contradiction and remain compile failures.

## 8. Validation results

Required searches were run before editing. The first two exact commands returned exit code 2 because this repository has no top-level `tests/` directory, but relevant results were returned from existing paths. The searches were rerun successfully over `shared`, `cluster2`, `cluster1`, `shared/tests`, `cluster2/tests`, `audits`, and `outputs`.

Focused analyzer tests:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or normalization or F3_EVAL_PIPELINE or compile_success or failure_code" -q
```

Result: passed, `91 passed, 462 deselected`.

Failure taxonomy tests:

```bash
.venv/bin/python -m pytest shared/tests -k "failure_taxonomy or F3 or classify_failure" -q
```

Result: passed, `37 passed, 516 deselected`.

Real artifact dry normalization:

```text
rows 177
failure_code_counts {'F2_NUMERIC_NAN': 4, 'F1_RUNTIME': 146, 'F1_COMPILE': 10, 'F0_PARSE': 12, 'F3_EVAL_PIPELINE': 5}
compile_success_counts {True: 4, False: 173}
F3_compile_pairs Counter({('F3_EVAL_PIPELINE', False): 5})
```

All four analyzer inputs now normalize:

```text
normalized_rows 714
conditions {'C': 180, 'G': 177, 'G+C': 177, 'none': 180}
compile_success {False: 707, True: 7}
functional_success {False: 714}
f3_rows 5
f3_compile_success {False: 5}
```

CLI help:

```bash
.venv/bin/python -m shared.analysis.factorial --help
```

Result: passed. The CLI uses `--inputs` and `--input-roles`, not separate `--none`, `--g`, `--c`, or `--gc` flags.

Full analyzer command attempted:

```bash
.venv/bin/python -m shared.analysis.factorial --inputs \
  outputs/cluster1/baseline_repaired_l4_n20.jsonl \
  outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl \
  outputs/cluster2/c_paper_n20_l4.jsonl \
  outputs/cluster2/g_plus_c_paper_n20_l4.jsonl \
  --input-roles none g c gc \
  --output outputs/analysis/factorial_2x2_preliminary.json
```

Result: failed on a new blocker after F3 normalization succeeded:

```text
ValueError: missing paired replay metadata: replay_pair_id
```

## 9. Analyzer output

`outputs/analysis/factorial_2x2_preliminary.json` was not regenerated.

Reason: after the F3 contradiction was resolved, the analyzer reached paired replay metadata validation and failed because the raw Cluster 1 none/G inputs do not contain `replay_pair_id` metadata. This is a separate analyzer compatibility issue from the F3 compile-success semantics.

No partial output file was written.

## 10. Documentation update note

After the analyzer passes, report-facing documentation should state:

- `F3_EVAL_PIPELINE` is an infrastructure/eval-pipeline malformed-payload failure unless independent Level 1 compile evidence is present.
- The five current G+C F3 rows count as `compile_success=false` and `functional_success=false`.
- Cluster 1 none/G rows are compile-only controls and are normalized to `functional_success=false` only for the temporary 2x2 functional analysis.
- The 177/180 G and G+C coverage caveat remains a skip-not-impute policy.

Repository docs were not updated in this task.

## 11. Next recommendation

`INVESTIGATE_NEXT_ANALYZER_BLOCKER`

Next blocker: decide how paired replay metadata validation should handle direct frozen Cluster 1 control artifacts that lack `replay_pair_id`, while preserving strict seed pairing and generated-row replay metadata checks.
