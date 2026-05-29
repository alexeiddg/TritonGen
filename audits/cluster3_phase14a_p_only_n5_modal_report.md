# Cluster 3 Phase 14a P-only n=5 Modal Report

## Authorization Evidence

The operator prompt explicitly authorized this bounded run:

```text
I authorize Phase 14a P-only n=5 Modal execution.
```

The authorization was limited to condition `P`, `elementwise`, `fp32`, `n=5`.
No n=20, paper-scale, all-condition, all-task, profiling, timing, speedup,
latency, throughput, benchmark, performance, grammar, C-containing, or RL work
was authorized or performed.

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

The Phase 13b provenance-freeze report also existed:

- `audits/cluster3_phase13b_commit_provenance_freeze_report.md`

The target output path did not exist before the Phase 14a run:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`

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

The final successful command used the runner's fresh-write mode:

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition P --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl --overwrite
```

Invocation notes:

- The first sandboxed Modal attempt failed before row generation with `Could not connect to the Modal server`.
- The first escalated attempt, without an explicit write mode, stopped locally before row generation with `FileNotFoundError('resume requires an existing JSONL output')`.
- A `--no-resume` attempt stopped the same way because the Modal local entrypoint maps the runner write mode through `--overwrite` or `--resume`; `--no-resume` did not select the runner's fresh-write mode.
- `--overwrite` was permitted by the Phase 14a instructions because preflight confirmed the target output did not already exist. No prior artifact was overwritten.

## Modal Execution Summary

Successful Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-GwS4pegTsRNeTMOBZA2yXc
```

Runner summary:

```json
{"output": "outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl", "route_audit": [{"c_loop_calls": 0, "condition": "P", "correctness_calls": 5, "generation_calls": 5, "p_loop_calls": 0, "route": "initial_terminal"}], "rows": 5, "write_mode": "overwrite"}
```

The successful run stayed within scope:

- condition: `P`
- kernel class: `elementwise`
- dtype: `fp32`
- n: `5`
- P repair budget: `5`
- C repair budget: `0`
- generated rows: `5`
- generation calls: `5`
- correctness calls: `5`
- P-loop calls: `0`
- C-loop calls: `0`

## Output Artifact Paths

Generated artifacts:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json`

File sizes:

```text
outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl              23310 bytes
outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json   2216 bytes
```

SHA256 digests computed with `.venv/bin/python`:

```text
d9d92f6a809bf3786eefacc8a8ae20358fc92a1aa684cf3ffd5ea12763a693ea outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl
3928d54583e5d74aac38bd73fb1d43c8a577dc5c84471d719da065f6ca64aad7 outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json
```

## Row Count

Validation command:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
p = Path("outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl")
rows = [line for line in p.read_text().splitlines() if line.strip()]
print("row_count", len(rows))
assert len(rows) == 5, len(rows)
PY
```

Result:

```text
row_count 5
```

## Row Schema Validation

All five rows validated with `Cluster3EvalRow.from_dict`.

P-only invariants validated:

- every row has `condition == "P"`;
- P was not attempted on non-`F1_COMPILE` rows;
- C never fired;
- no row-count or schema invariant failed.

## Content Hash Validation

The sidecar exists:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json`

Repository helper validation passed:

```text
content_hash_validation passed
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

## F1_COMPILE Seed Count

Validated count:

```text
f1_seed_count 0
```

This run produced no natural `F1_COMPILE` seeds.

## P Firing Summary

Validated count:

```text
p_attempted 0
```

P did not fire because every initial row was `F0_PARSE`, not `F1_COMPILE`.
This is correct boundary behavior for P-only Cluster 3 v1, but it is
insufficient F1/P-loop signal for this n=5 matrix cell.

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

C did not fire, as expected for condition `P` with `c_repair_budget=0`.

## Boundary Scan Result

Private-eval and hidden-shape scan:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl
```

Result: no matches.

Performance/profiler/timing scan:

```bash
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl
```

Result: no matches.

## Artifact Registry Update

Updated:

- `docs/05_artifacts_and_results_registry.md`

The registry now records the Phase 14a P-only n=5 matrix cell, row count,
schema version, hash sidecar, failure-code counts, zero F1 seed count, zero P
attempt count, zero C fire count, and development-scale caveats.

The entry explicitly states that the artifact is one matrix cell only,
development-scale only, not paper-scale, not pass@k evidence, not P-lift
evidence, not C-lift evidence, not statistical evidence, and not
performance/speedup/profiler/timing evidence.

## Tests Run

Pre-run:

```bash
.venv/bin/python -m pytest cluster3/tests -v
```

Result:

```text
744 passed
```

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
```

Result:

```text
744 passed
```

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v
```

Result:

```text
128 passed, 480 deselected
```

## Regression Checks

Pre-run and post-run full regression command:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Both pre-run and post-run checks stopped only at the known pre-existing Cluster
1 docs-lock failure:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Post-run summary before `-x` stop:

```text
1 failed, 130 passed, 7 skipped
```

No new regression was observed.

## Cost/Spend Notes

The successful run generated exactly five rows for the single authorized
P-only cell. The route audit recorded five generation calls and five
correctness calls, with zero P-loop calls and zero C-loop calls.

Two earlier Modal app initializations stopped locally before row generation:
one due sandboxed network connection failure and one due the runner write mode
defaulting to resume for a new output path. The final run did not expand beyond
n=5, did not run additional conditions, did not run additional kernel classes,
and did not execute profiling, timing, speedup, benchmark, throughput, or
performance measurement.

No explicit dollar cost was emitted in the local command output.

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
files, analyzer outputs, Modal harness source, or unrelated Cluster 3
implementation/test files were modified.

The only generated output artifacts for this phase are:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json`

The forbidden implementation diff check returned no implementation/test diff.

## Classification

`PHASE14A_P_N5_COMPLETE_INSUFFICIENT_F1_SIGNAL_WITH_WARNINGS`

Reason: exactly five valid `P` rows were generated; schema and content-hash
validation passed; P did not fire outside `F1_COMPILE`; C never fired; boundary
scans passed; local Cluster 3 and shared sanity tests passed; full regression
failed only at the known Cluster 1 docs-lock failure; and no out-of-scope source
mutation occurred. The warning is required because the run produced zero
`F1_COMPILE` seeds and zero P repair attempts.

## Next-Step Recommendation

Do not treat this artifact as P-loop efficacy, pass@k, paper-scale,
statistical, or performance evidence. The next optional matrix cell should be
Phase 14b `C+P` n=5 elementwise fp32, only after a separate explicit approval
and with the same one-cell-at-a-time spend and validation controls.
