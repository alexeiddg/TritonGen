# L2b-2 Final Authorization Report

## Executive Summary

classification: `L2B_N2_FINAL_AUTHORIZATION_READY`
report_version: `1.0.0`
target_branch: `codex-track-handoff-context`
target_baseline: `eab664f560404cc40e309caa8d4202346452ecc3`
packet: `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_full_coverage_authorization_packet.md`
AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_ONLY

This report records the final signed L2b-2 authorization packet preparation.
No L2b execution, Modal call, GPU job, generation, billing query, output
mutation, artifact mutation, `mlruns` mutation, analyzer/report refresh, retry,
or resume was performed while preparing the packet.

## Target Baseline

```text
target branch: codex-track-handoff-context
execution_code_target_commit: eab664f560404cc40e309caa8d4202346452ecc3
planning_commit: 8b26951e37cde7eab5497f2a35860b95da067302
local venv: .venv/bin/python
runtime MLflow for future execution: TRITONGEN_MLFLOW=0
```

The packet signs policy authorization for L2b-2 only. This report does not
change runtime launcher behavior; a separate runtime-gate readiness step must
verify or enable only the exact signed L2b-2 token/profile/path before launch.

## L2a Incomplete Slow-Tail Context

The preserved L2a n=20 run at `04d2eef Record failed L2 n20 validation`
completed 228 of 240 rows. Only `task_agnostic__c_on__p_on` stopped early at
8 of 20 rows. This remains classified as incomplete wall-clock/slow-tail
preservation, not as a scientific evidence failure. Analyzer/report refresh,
retry, resume, overwrite, rerun, and paper-scale claims remain blocked for L2a.

## L2b Planning Readiness Evidence

The reconciled planning support at
`8b26951e37cde7eab5497f2a35860b95da067302` provides local-only selector/profile
support for:

```text
l2b_n2_full_coverage
l2b_n20_full_coverage
```

It defines deterministic `kernel_class__dtype_variant` shards, per-shard
output/artifact namespaces, execution-plan payloads, concurrency limits,
sidecar-only timing diagnostics, slow-cell stop policy, and
`fail_if_any_target_path_exists=true`.

## Shard Scope

```text
total_shards: 9
kernel_classes: elementwise, reduction, matmul
dtype_variants: fp32, fp16, bf16
shard_id form: <kernel_class>__<dtype_variant>
```

Authorized shard ids:

```text
elementwise__fp32
elementwise__fp16
elementwise__bf16
reduction__fp32
reduction__fp16
reduction__bf16
matmul__fp32
matmul__fp16
matmul__bf16
```

## Matrix And Row Expectation

```text
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
planned cells per shard: 12
n per cell: 2
rows per shard: 24
total planned rows: 216
```

## Exact Command Bundle

Dry plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future signed all-shards command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector all --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Future one-shard template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector <shard_id> --kernel-class <kernel_class> --scale-tier development --n 2 --dtypes <dtype_variant> --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Future bounded-wave template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector wave:<start>:<count> --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

The packet also lists post-run row-count validation, analyzer/report, and
billing reconciliation command templates. Those commands are authorized only
after the future L2b-2 run completes or stops.

## Stop Limits

```text
max_total_rows: 216
max_rows_per_shard: 24
max_shards: 9
max_generation_attempts_per_row: 11
max_generation_attempts_per_shard: 264
max_total_generation_attempts: 2376
max_correctness_calls_per_row: 11
max_correctness_calls_per_shard: 264
max_total_correctness_calls: 2376
max_compile_attempts_per_row: 11
max_compile_attempts_per_shard: 264
max_total_compile_attempts: 2376
max_p_repair_attempts_per_p_active_row: 5
max_c_repair_attempts_per_c_active_row: 5
max_wall_clock_seconds_total: 21600
max_wall_clock_seconds_per_shard: 7200
signed_wall_clock_seconds_per_cell: 1800
fail_if_any_target_path_exists: true
no retry
no resume
```

## Spend And Concurrency Limits

```text
max_gpu_concurrency: 4
max_container_concurrency: 40
max_estimated_cost_usd: 150.00
max_reconciled_billing_cost_usd: 200.00
```

The packet carries forward the Modal empty-tag billing caveat. If tags remain
empty or ambiguous, attribution may be UTC-window-only and low confidence.

## Output And Artifact Namespace Authorization

Only per-shard L2b-2 namespaces are signed:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
```

L2a paths, L2b n20 paths, `mlruns`, and `docs/preliminary_report` remain
forbidden.

## Timing Observability Authorization

Per-cell and per-shard timing metadata is authorized as sidecar-only operational
diagnostics:

```text
wall_clock_seconds_per_row
generation_attempt_count
compile_attempt_count
correctness_call_count
p_repair_attempt_count
c_repair_attempt_count
terminal_failure_type
timeout_or_stop_reason if applicable
```

These fields must not be used for speedup, performance, throughput, latency,
profiler, benchmark, paper evidence, or economic claims.

## Slow-Cell Stop Policy

Known high-cost cell:

```text
task_agnostic__c_on__p_on
```

If any single cell exceeds the signed 1800 second wall-clock budget, the future
runtime must finish the active row if safe, then stop the shard and classify
`SLOW_CELL_BUDGET_EXCEEDED`. No automatic retry or resume is authorized. Partial
shard audit metadata must be preserved.

## Billing Caveat

`BILLING_QUERY_AUTHORIZED` is limited to
`YES_L2B_N2_RECONCILIATION_ONLY_AFTER_RUN`. Billing collection requires a
post-run UTC window and redacted/static report handling. Raw billing output is
not authorized for commit.

## Post-Run Validation Authorization

Post-run validation is limited to the packet-listed commands: focused tests,
compileall, row-count validation, per-shard analyzer/report commands, and
per-shard billing reconciliation commands after a redacted report is available.

## Forbidden Scope

Forbidden during packet preparation and outside the future signed L2b-2 command:

```text
L2b execution during packet draft
Modal call during packet draft
GPU job during packet draft
generation during packet draft
billing query during packet draft
outputs mutation during packet draft
artifacts mutation during packet draft
mlruns mutation
docs/preliminary_report refresh
runtime launcher behavior change
scientific semantics change
L2b-4 signature
L2b-4 execution
L3 execution
retry
resume
performance/speedup/profiler/benchmark claim
paper-scale claim before post-run validation and audit
```

## L2b-4 Blocked Status

L2b-4 remains unsigned and blocked until L2b-2 completes and validates.

```text
L2B_N20_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
```

## Signature Status

The packet now contains:

```text
AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_ONLY
```

## No-Execution Proof

During this packet preparation, no L2b launch command, Modal command, GPU job,
generation command, billing query, analyzer/report refresh, output mutation,
artifact mutation, `mlruns` mutation, dependency update, lockfile update, or
preliminary-report refresh was run.

## Classification

```text
L2B_N2_FINAL_AUTHORIZATION_READY
```

## Next-Step Recommendation

Do not execute L2b yet from this packet-preparation commit. Next, perform a
separate L2b-2 runtime-gate readiness step that verifies or enables only the
exact signed L2b-2 token/profile/path and keeps L2b-4, retry, resume, and all
non-L2b-2 namespaces fail-closed.
