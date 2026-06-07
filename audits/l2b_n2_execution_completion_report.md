# L2b-2 Execution Completion Report

## Executive Summary

The signed L2b-2 n=2 full-coverage launch was attempted once from
`codex-track-handoff-context` at commit
`4cb911f84734211e5d5508399820aba671989be3`.

The run did not complete the planned 216 rows. It stopped under the signed
per-cell slow-cell budget policy after 188 rows with:

```text
SLOW_CELL_BUDGET_EXCEEDED
```

No retry, resume, second launch, analyzer refresh, report refresh, billing
query, profiler, benchmark, speedup analysis, L2b-4/L3 launch, or MLflow
runtime write was run.

The existing partial L2b-2 output and observability artifacts are archived as
the terminal record of this one signed attempt. This archive is not complete
L2b-2 validation and does not authorize any retry, resume, overwrite, rerun,
additional generation, analyzer/report refresh, billing reconciliation, or
L2b-4/n20 action.

## Exact Command Run

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector all --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

## Command Caveat

The signed command contained `--overwrite`, while earlier L2b authorization
language emphasized `fail_if_any_target_path_exists=true`. Preflight target-path
checks found the L2b-2 target namespaces absent before launch, so this is not
known to have corrupted existing artifacts. For any future packet or recovery
command, remove `--overwrite` unless the packet explicitly signs overwrite
semantics.

## Terminal Failure

The launcher exited with code `1` after raising:

```text
RuntimeError: SLOW_CELL_BUDGET_EXCEEDED: signed L2b shard matmul__fp32 cell template_upper_bound__c_on__p_off took 2379.955s, exceeding 1800s
```

The stop occurred after the active cell returned and wrote its two rows. The
failure is an operational slow-cell budget stop, not a scientific evidence
failure.

## Row Coverage

Planned:

```text
total_shards: 9
planned_rows_per_shard: 24
total_planned_rows: 216
```

Observed:

```text
jsonl_files: 94
rows_observed: 188
json_parse_errors: 0
complete_shards: 6
partial_shards: 3
missing_rows: 28
```

Per-shard rows:

| shard_id | observed_rows | status |
|---|---:|---|
| `elementwise__fp32` | 24 | complete |
| `elementwise__fp16` | 24 | complete |
| `elementwise__bf16` | 24 | complete |
| `reduction__fp32` | 24 | complete |
| `reduction__fp16` | 16 | partial |
| `reduction__bf16` | 16 | partial |
| `matmul__fp32` | 12 | partial stopped shard |
| `matmul__fp16` | 24 | complete |
| `matmul__bf16` | 24 | complete |

Partial shard cell coverage:

```text
matmul__fp32:
  grammar_off__c_off__p_off: 2
  grammar_off__c_on__p_off: 2
  grammar_off__c_off__p_on: 2
  grammar_off__c_on__p_on: 2
  template_upper_bound__c_off__p_off: 2
  template_upper_bound__c_on__p_off: 2

reduction__fp16:
  grammar_off__c_off__p_off: 2
  grammar_off__c_on__p_off: 2
  grammar_off__c_off__p_on: 2
  grammar_off__c_on__p_on: 2
  template_upper_bound__c_off__p_off: 2
  template_upper_bound__c_on__p_off: 2
  template_upper_bound__c_off__p_on: 2
  template_upper_bound__c_on__p_on: 2

reduction__bf16:
  grammar_off__c_off__p_off: 2
  grammar_off__c_on__p_off: 2
  grammar_off__c_off__p_on: 2
  grammar_off__c_on__p_on: 2
  template_upper_bound__c_off__p_off: 2
  template_upper_bound__c_on__p_off: 2
  template_upper_bound__c_off__p_on: 2
  template_upper_bound__c_on__p_on: 2
```

## Artifact Summary

```text
output files under l2b_n2: 188
jsonl result files under l2b_n2: 94
observability files under l2b_n2: 282
analysis files under l2b_n2: 0
reports files under l2b_n2: 0
billing files under l2b_n2: 0
mlruns mutation: none observed
```

Archived namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
```

## Validation Run

Partial JSONL parse validation:

```text
jsonl_files=94 rows=188 json_errors=0
```

Full L2b-2 validation was not run because the row count is incomplete.
Analyzer/report refresh was not run.

## Protected Scope

The run wrote only the signed L2b-2 output and observability namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
```

No `artifacts/analysis`, `artifacts/reports`, `artifacts/billing`, `mlruns`, or
`docs/preliminary_report` mutation was authorized or performed by this audit.

## Stop Compliance

- No retry was run.
- No resume was run.
- No L2b-4/n20 was run.
- No L3 was run.
- No additional shard command was run.
- Partial shard outputs and observability sidecars were preserved.

## Classification

```text
L2B_N2_PARTIAL_ARTIFACTS_ARCHIVED_SLOW_CELL_STOP
L2B_N2_TERMINAL_PARTIAL_SLOW_CELL_STOP
```

Scientific/reporting interpretation: L2b-2 was attempted once under signed
full-coverage smoke authorization. It did not complete; it produced partial
operational evidence showing slow-tail behavior severe enough to trigger the
signed stop policy. Therefore L2b-4 remains blocked, and no full-coverage
validation claim is made.

## Next-Step Recommendation

Do not treat this run as L2b-2 validation. Prepare a separate signed recovery
packet if the project wants to resume, retry, overwrite, rerun, clean up, or
otherwise mutate any partial shard. Keep L2b-4 blocked until L2b-2 completes
and validates under a separate approval.
