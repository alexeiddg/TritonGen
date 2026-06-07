# L2b-2 Missing-28 Recovery Execution Report

## Executive Summary

The L2b-2 missing-28 recovery completed all authorized recovery rows:

- `reduction__fp16`: 8 rows
- `reduction__bf16`: 8 rows
- `matmul__fp32`: 12 rows

Combined logical validation passed with 188 archived base rows plus 28 recovery rows for 216/216 total L2b-2 rows. All 9 shards are logically complete at 24 rows each. Duplicate logical row keys: 0. Missing logical row keys: 0.

Classification: `L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT`

## Signed Recovery Authorization Reference

Signed packet:

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_recovery_missing28_authorization_packet.md`
- `packet_id`: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1`
- Scope: L2b-2 recovery missing-28 only.
- Authorized recovery namespace: `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/`
- Authorized observability namespace: `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/`

The packet explicitly forbids retry, resume, overwrite, L2b-4, L2b-n20, Fireworks mutation, MLflow runtime mutation, and non-recovery row generation.

## Base Archive Reference

Base archive:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/`
- Archived base row count: 188
- Archived base classification before recovery: `L2B_N2_TERMINAL_PARTIAL_SLOW_CELL_STOP`
- Base archive commit reference from signed packet: `136a8b07cc9043200de73a91be4803b59817cac4`

The base namespace was not overwritten during finalization. `git diff --name-only -- outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2 artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2` produced empty output.

## Dirty-Worktree Execution Caveat

Recovery launch was performed after the user explicitly approved launching with a dirty worktree. The dirty tracked files present during finalization were:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/results/logger.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `shared/observability/logger.py`

Those code changes enabled the no-overwrite recovery launch path and create-mode artifact writing, but they are outside this archive commit scope unless explicitly staged later.

## Exact Recovery Commands Run

The recovery launch used `TRITONGEN_MLFLOW=0` and the signed recovery token.

`reduction__fp16`:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1 --l2b-shard-selector reduction__fp16 --l2b-recovery-cells task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --kernel-class reduction --scale-tier development --n 2 --dtypes fp16 --repair-history-policy agentic_transcript_v1
```

`reduction__bf16`:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1 --l2b-shard-selector reduction__bf16 --l2b-recovery-cells task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --kernel-class reduction --scale-tier development --n 2 --dtypes bf16 --repair-history-policy agentic_transcript_v1
```

`matmul__fp32`:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1 --l2b-shard-selector matmul__fp32 --l2b-recovery-cells template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --kernel-class matmul --scale-tier development --n 2 --dtypes fp32 --repair-history-policy agentic_transcript_v1
```

No `--overwrite` flag was used in the successful recovery commands.

## Recovery Row Result

Recovery namespace row counts:

| Shard | Recovery rows |
| --- | ---: |
| `reduction__fp16` | 8 |
| `reduction__bf16` | 8 |
| `matmul__fp32` | 12 |
| Total | 28 |

Authorized recovery cell counts were exactly 2 rows per listed missing cell:

- `reduction__fp16`: four `task_agnostic` cells, 8 rows total.
- `reduction__bf16`: four `task_agnostic` cells, 8 rows total.
- `matmul__fp32`: two `template_upper_bound` P-on cells and four `task_agnostic` cells, 12 rows total.

No completed shards or completed cells were included in the recovery namespace.

## Combined 216/216 Logical Validation Result

Final combined validation:

| Metric | Value |
| --- | ---: |
| Base rows | 188 |
| Recovery rows | 28 |
| Combined rows | 216 |
| Duplicate logical row keys | 0 |
| Missing or mismatched shards | 0 |

Combined shard counts:

| Shard | Base | Recovery | Combined |
| --- | ---: | ---: | ---: |
| `elementwise__fp32` | 24 | 0 | 24 |
| `elementwise__fp16` | 24 | 0 | 24 |
| `elementwise__bf16` | 24 | 0 | 24 |
| `reduction__fp32` | 24 | 0 | 24 |
| `reduction__fp16` | 16 | 8 | 24 |
| `reduction__bf16` | 16 | 8 | 24 |
| `matmul__fp32` | 12 | 12 | 24 |
| `matmul__fp16` | 24 | 0 | 24 |
| `matmul__bf16` | 24 | 0 | 24 |

Validation command status:

- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q`: 224 passed.
- `.venv/bin/python -m compileall -q cluster3 shared`: passed.
- `git diff --check`: passed.
- Combined local validation script: passed with `errors: []`.

## Observability Sidecar Caveat

`reduction__fp16` has result rows and result hash sidecars, but it does not have observability sidecars. It completed before create-mode support was fixed for the observability logger.

Observability sidecar state:

- `reduction__fp16`: 0 event files, 0 event hash sidecars, 0 summary sidecars.
- `reduction__bf16`: 4 event files, 4 event hash sidecars, 4 summary sidecars.
- `matmul__fp32`: 6 event files, 6 event hash sidecars, 6 summary sidecars.

No rerun or repair was performed to fill the missing `reduction__fp16` observability sidecars.

## Analyzer/Report Result

Analyzer/report was not run in this finalization pass. The signed recovery packet authorizes analyzer/report only conditionally after 216/216 validation, but it does not list a concrete analyzer/report command. No analyzer/report command was invented during finalization.

Required caveats for any future analyzer/report step:

- Evidence must be combined base plus recovery L2b-2.
- Recovery was append-only.
- Recovery was launched from a dirty worktree.
- `reduction__fp16` recovery observability sidecars are absent.
- Timing observability is incomplete for one recovery shard segment.
- No performance or speedup claims are permitted from this recovery archive alone.

## Billing Result

Billing reconciliation was not run in this finalization pass. The signed recovery packet includes only a billing reconciliation template requiring a redacted report/window, not a concrete runnable packet command. No experiment rerun was performed because of billing caveats.

Carry-forward caveat: Modal empty-tag / UTC-window limitations remain applicable to any later billing reconciliation.

## No Overwrite Proof

Successful recovery commands omitted `--overwrite`.

Finalization checks:

- Base output/observability diff scan: empty.
- Recovery namespace contains exactly the authorized missing recovery rows.
- `git diff --check`: passed.

## No Retry/No Resume Proof

No retry or resume command was run during finalization. Recovery artifacts were archived as completed. The finalization phase performed only local validation and audit/archive file creation.

The two failed pre-row dispatch attempts from launch setup did not create recovery rows. No completed recovery row was rerun, repaired, or overwritten.

## No L2b-4/n20 Proof

The recovery namespace was scanned for `l2b_4`, `l2b_n20`, and `n20` matches under output and observability recovery paths. No matches were found.

No L2b-4 or L2b-n20 command was run during finalization.

## No MLflow Proof

MLflow was disabled during recovery launch with `TRITONGEN_MLFLOW=0`.

Finalization check:

```bash
test ! -e mlruns
```

Result: passed.

## Files Archived

Recovery result namespace:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/`

Recovery observability namespace:

- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/`

Audit report:

- `audits/l2b_n2_recovery_missing28_execution_report.md`

No analysis, report, or billing recovery artifacts were present at finalization time.

## Remaining Caveats

- `reduction__fp16` recovery observability sidecars are absent.
- Timing observability is incomplete for one recovery shard segment.
- Recovery launch occurred from a dirty worktree with user approval.
- Analyzer/report was not run because no concrete analyzer/report command was listed in the signed packet.
- Billing reconciliation was not run because no redacted billing report/window command was provided.
- No performance, speedup, or cost claims are made by this archive.

## Classification

`L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT`

This classification is selected because combined 216/216 row validation passed and analyzer/report is explicitly caveated as not run due the absence of a concrete signed command.

## Next-Step Recommendation

Treat the L2b-2 row coverage recovery as complete and archived. If a later report refresh is needed, prepare a separate signed analyzer/report packet that explicitly consumes combined base plus recovery rows and carries forward the dirty-worktree and `reduction__fp16` observability caveats.
