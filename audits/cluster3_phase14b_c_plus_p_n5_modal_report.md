# Cluster 3 Phase 14b C+P n=5 Modal Report

## Authorization Evidence

The operator prompt explicitly authorized this bounded run:

```text
I authorize Phase 14b C+P n=5 Modal execution.
```

The authorization was limited to condition `C+P`, `elementwise`, `fp32`,
`n=5`. No n=20, paper-scale, all-condition, all-task, profiling, timing,
speedup, latency, throughput, benchmark, performance, grammar-containing,
P-only, G+P, G+C+P, or RL work was authorized or performed.

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

```text
```

The working tree was clean at preflight. No dirty path classification was
required.

## Phase 14 Plan Status

The required planning report existed before execution:

- `audits/cluster3_phase14_n5_condition_matrix_plan.md`

The Phase 14b output path did not exist before the run:

- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`

## Phase 14a Status

The required Phase 14a report and artifact existed before execution:

- `audits/cluster3_phase14a_p_only_n5_modal_report.md`
- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`

The Phase 14a artifact had exactly five rows:

```text
phase14a_row_count 5
```

Phase 14a classification was
`PHASE14A_P_N5_COMPLETE_INSUFFICIENT_F1_SIGNAL_WITH_WARNINGS`.

## Exact Modal Command

CLI discovery confirmed the runner exposes the required flags:

```text
--condition
--kernel-class
--scale-tier
--n
--dtypes
--p-repair-budget
--c-repair-budget
--output
--overwrite / --no-overwrite
--resume / --no-resume
```

The successful command used the runner's fresh-write mode:

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition C+P --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --p-repair-budget 5 --c-repair-budget 5 --output outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl --overwrite
```

`--overwrite` was permitted by the Phase 14b instructions because preflight
confirmed the target output did not already exist. No prior Phase 14b artifact
was overwritten.

## Modal Execution Summary

Successful Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-kW8UTQWkGWF5k4AX1KUFHf
```

Runner summary:

```json
{"output": "outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl", "route_audit": [{"c_loop_calls": 0, "condition": "C+P", "correctness_calls": 5, "generation_calls": 5, "p_loop_calls": 0, "route": "initial_terminal"}], "rows": 5, "write_mode": "overwrite"}
```

The successful run stayed within scope:

- condition: `C+P`
- kernel class: `elementwise`
- dtype: `fp32`
- n: `5`
- P repair budget: `5`
- C repair budget: `5`
- generated rows: `5`
- generation calls: `5`
- correctness calls: `5`
- P-loop calls: `0`
- C-loop calls: `0`

## Output Artifact Paths

Generated artifacts:

- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json`

File sizes:

```text
outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl              23330 bytes
outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json   2218 bytes
```

SHA256 digests computed with `.venv/bin/python`:

```text
7ce0606820a3de8735b163ea7cf8e34d1681ddac68fbab35f3ce4364d1c03930 outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl
2199348868fe3ab292cb0bad9ad486d592c733f7c45e4567d3ae07237b86302c outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json
```

## Row Count

Validation result:

```text
row_count 5
```

## Row Schema Validation

All five rows validated with `Cluster3EvalRow.from_dict`.

C+P invariants validated:

- every row has `condition == "C+P"`;
- P was not attempted on non-`F1_COMPILE` rows;
- C did not fire without an F2 path;
- no invalid `c_loop_source` appeared;
- no row-count or schema invariant failed.

## Content Hash Validation

The sidecar exists:

- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json`

Repository helper validation passed with parsed `Cluster3EvalRow` instances:

```text
hash_sidecar_valid outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json
```

Helpers used:

- `cluster3.results.logger.load_content_hash_sidecar`
- `cluster3.results.logger.validate_content_hash_sidecar_for_rows`

## Failure-Code Counts

Validated counts:

```text
failure_counts {'F0_PARSE': 5}
```

All five rows terminated at initial `F0_PARSE`.

## Initial Failure-Code Counts

Validated counts:

```text
initial_failure_counts {'F0_PARSE': 5}
```

## F1_COMPILE Seed Count

Validated count:

```text
f1_seed_count 0
```

This run produced no natural `F1_COMPILE` seeds.

## F2 Initial Count

Validated count:

```text
f2_initial_count 0
```

This run produced no initial F2 rows.

## P Firing Summary

Validated count:

```text
p_attempted 0
```

P did not fire because every initial row was `F0_PARSE`, not `F1_COMPILE`.
This is correct boundary behavior, but it is insufficient P repair signal.

## P Stop-Reason Counts

Validated counts:

```text
p_stop_reasons {'p_not_applicable': 5}
```

## C Firing Summary

Validated count:

```text
c_fired 0
```

C did not fire because no row reached an initial or post-P F2 path. This is
correct boundary behavior, but it is insufficient C repair signal.

## C Loop Source Counts

Validated counts:

```text
c_sources {'none': 5}
```

## C Terminal Failure-Code Counts

Validated counts:

```text
c_terminal_counts {}
```

## Boundary Scan Result

Private-eval and hidden-shape scan:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl
```

Result: no matches.

Performance/profiler/timing scan:

```bash
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl
```

Result: no matches.

## Artifact Registry Update

Updated:

- `docs/05_artifacts_and_results_registry.md`

The registry now records the Phase 14b C+P n=5 matrix cell, row count, schema
version, hash sidecar, failure-code counts, initial failure-code counts, zero
F1 seed count, zero initial F2 count, zero P attempt count, zero C fire count,
C loop source counts, C terminal failure-code counts, and development-scale
caveats.

The entry explicitly states that the artifact is one matrix cell only,
development-scale only, not paper-scale, not pass@k evidence, not P-lift
evidence, not C-lift evidence, not statistical evidence, and not
performance/speedup/profiler/timing evidence.

## Tests Run

Pre-run:

```bash
.venv/bin/python -m pytest cluster3/tests -v
```

Initial result: one docs-consistency failure because the registry no longer
included the legacy planned Cluster 3 development identifiers required by
`cluster3/tests/test_docs_consistency.py`. A narrow artifact-registry-only fix
restored those planned identifiers without changing source or outputs.

Focused rerun:

```text
cluster3/tests/test_docs_consistency.py::test_registry_tracks_cluster3_smoke_without_claiming_scale_outputs PASSED
1 passed
```

Full Cluster 3 rerun:

```text
744 passed
```

Analyzer/factorial sanity:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v
```

Result:

```text
128 passed, 480 deselected
```

Post-run:

```bash
.venv/bin/python -m pytest cluster3/tests -v
.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v
```

Results:

```text
744 passed
128 passed, 480 deselected
```

## Regression Checks

Pre-run full regression:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: failed only at the known pre-existing Cluster 1 docs-lock test:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
1 failed, 130 passed, 7 skipped
```

Post-run full regression:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: failed only at the same known pre-existing Cluster 1 docs-lock test:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
1 failed, 130 passed, 7 skipped
```

No new regression was observed.

## Cost / Spend Notes

Only one authorized Phase 14b Modal run completed. The run stayed at one
condition, one kernel class, `fp32`, and `n=5`. The Modal output showed five
generation calls, five correctness calls, zero P-loop calls, and zero C-loop
calls. No cost total was printed by the runner.

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
files, Cluster 3 implementation/test files, or analyzer output JSON files were
modified.

No profiling, timing, Nsight, NCU, speedup, latency, throughput, benchmark, or
performance measurement was run or recorded.

## Classification

`PHASE14B_C_PLUS_P_N5_COMPLETE_INSUFFICIENT_REPAIR_SIGNAL_WITH_WARNINGS`

The run generated exactly five valid C+P rows, schema and hash validation
passed, P did not fire outside `F1_COMPILE`, C did not fire outside an F2 path,
boundary scans passed, local tests passed, and full regression still failed
only at the known Cluster 1 docs-lock failure. The warning is that this C+P
cell produced zero `F1_COMPILE`/P attempts and zero F2/C attempts.

## Next-Step Recommendation

Proceed only with separate explicit approval. The next optional matrix cell is
Phase 14c: `G+C+P` n=5 elementwise fp32.
