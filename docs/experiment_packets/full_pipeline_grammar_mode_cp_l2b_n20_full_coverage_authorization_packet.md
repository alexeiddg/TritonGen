# Full Pipeline L2b-4 n=20 Sharded Full-Coverage Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.0-signed-l2b-n20-only`
packet_type: signed bounded authorization packet
target_branch: `codex-track-handoff-context`
execution_code_target_commit: `28255c3afec51a2d61fcd59dbe9ee624b45e1306`
runtime_gate_commit: current packet commit after review
selector_profile_id: `l2b_n20_full_coverage`
rung: `L2b-4`
status: `SIGNED_FOR_L2B_N20_ONLY`
classification: `L2B_N20_FINAL_AUTHORIZATION_READY`

```text
AUTHORIZES_EXECUTION: YES_L2B_N20_ONLY
MODAL_AUTHORIZED: YES_L2B_N20_ONLY
GPU_AUTHORIZED: YES_L2B_N20_ONLY
GENERATION_AUTHORIZED: YES_L2B_N20_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N20_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N20_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N20_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N20_RECONCILIATION_ONLY_AFTER_WAVES
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
FIREWORKS_EXECUTION_AUTHORIZED: NO
L2B_N2_MUTATION_AUTHORIZED: NO
L2B_N2_RECOVERY_MUTATION_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N20_ONLY
```

This packet signs L2b-4 / n20 only. It does not execute L2b-4 during packet
preparation and does not authorize Fireworks API execution.

## L2b-2 Prerequisite

The L2b-2 prerequisite gate is satisfied:

```text
base_l2b_2_rows: 188
recovery_rows: 28
combined_logical_rows: 216/216
duplicate_logical_keys: 0
missing_logical_keys: 0
complete_shards: 9/9
classification: L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT
post_recovery_baseline: 28255c3afec51a2d61fcd59dbe9ee624b45e1306
post_recovery_baseline_classification: L2B_N2_POST_RECOVERY_BASELINE_CLEAN_READY_FOR_L2B4_AUTHORIZATION
```

Known caveat carried forward: the `reduction__fp16` recovery produced result
rows and hash sidecars but no observability sidecars. This packet does not
retroactively patch those L2b-2 observability sidecars. It requires L2b-4 to
produce observability event, hash, and summary sidecars for every L2b-4 shard.
If L2b-4 sidecars are missing after a wave, record a validation caveat or
failure under this packet's signed validation rules; do not rerun rows merely
to patch observability.

## Scope

```text
condition selector: grammar_mode_cp_12cell
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
kernel classes: elementwise, reduction, matmul
dtype variants: fp32, fp16, bf16
shard_id: <kernel_class>__<dtype_variant>
total_shards: 9
n: 20
rows_per_12_cell_shard: 240
total_planned_rows: 2160
repair_history_policy: agentic_transcript_v1
backend: modal_local_model
TRITONGEN_MLFLOW: 0
profiler: not authorized
benchmark: not authorized
speedup_or_performance_claims: not authorized
```

Authorized shards:

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

## Wave Execution Plan

L2b-4 must run as bounded waves, not one uncontrolled monolith.

```text
wave_1_elementwise:
  shards: elementwise__fp32, elementwise__fp16, elementwise__bf16
  planned_rows: 720

wave_2_reduction:
  shards: reduction__fp32, reduction__fp16, reduction__bf16
  planned_rows: 720

wave_3_matmul_lower_risk:
  shards: matmul__fp16, matmul__bf16
  planned_rows: 480

wave_4_matmul_fp32_isolated:
  shards: matmul__fp32
  planned_rows: 240
```

`matmul__fp32` is isolated last because the L2b-2 slow-cell stop occurred in
matmul fp32 scope. It must not block elementwise, reduction, fp16, or bf16 n20
evidence.

## Command Bundle

Dry plan for all shards:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution plan for all shards:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future Wave 1 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector wave:0:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
```

Future Wave 2 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector wave:3:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
```

Future Wave 3 commands:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector matmul__fp16 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector matmul__bf16 --kernel-class matmul --scale-tier paper --n 20 --dtypes bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
```

Future Wave 4 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
```

One-shard template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector <kernel_class>__<dtype_variant> --kernel-class <kernel_class> --scale-tier paper --n 20 --dtypes <dtype_variant> --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
```

No future L2b-4 command may contain `--overwrite`.

Post-wave validation commands:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_full_coverage --wave-id <wave_id> --expected-rows <wave_rows> --require-content-hash-sidecars --require-observability-sidecars
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Combined post-run validation command:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_full_coverage --expected-rows 2160 --expected-shards 9 --require-content-hash-sidecars --require-observability-sidecars
```

Analyzer/report command is authorized only after 2160/2160 validation or after
an explicitly recorded partial-wave caveat:

```bash
.venv/bin/python -m cluster3.analysis.grammar_mode_cp_factorial_l2b --stage l2b_n20_full_coverage --require-validated-rows 2160 --no-performance-claims
```

Billing reconciliation template after each wave and after the combined total:

```bash
.venv/bin/python -m cluster3.billing.reconcile_modal_costs --stage l2b_n20_full_coverage --wave-id <wave_id> --utc-window <start_utc>/<end_utc> --output artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/<wave_id>_billing_reconciliation.json
```

## Stop Limits

```text
max_total_rows: 2160
max_rows_per_shard: 240
max_shards: 9
max_rows_per_cell_per_shard: 20
max_wave_rows.wave_1: 720
max_wave_rows.wave_2: 720
max_wave_rows.wave_3: 480
max_wave_rows.wave_4: 240
max_wall_clock_total: 24 hours
max_wall_clock_per_wave: 10 hours
max_wall_clock_per_shard: 8 hours
max_wall_clock_per_cell: 7200 seconds
max_wall_clock_for_matmul_fp32_wave: 12 hours
max_wall_clock_for_matmul_fp32_cell: 10800 seconds
fail_if_any_target_path_exists: true
overwrite: forbidden
retry: forbidden
resume: forbidden
abort_if_rows_exceed_signed_limits: true
abort_if_namespace_escapes_l2b_n20: true
```

If a signed wall-clock budget is exceeded, finish the active row if safe, stop
the active wave, classify `L2B_N20_WAVE_TERMINAL_WALLCLOCK_LIMIT`, preserve the
partial wave audit, and do not retry or resume automatically.

## Spend And Concurrency Limits

```text
wave_1_max_gpu_concurrency: 4
wave_1_max_container_concurrency: 40
wave_2_max_gpu_concurrency: 4
wave_2_max_container_concurrency: 40
wave_3_max_gpu_concurrency: 4
wave_3_max_container_concurrency: 40
wave_4_max_gpu_concurrency: 2
wave_4_max_container_concurrency: 20
max_estimated_cost_usd: 400
max_reconciled_billing_cost_usd: 500
```

Carry forward the Modal empty-tag billing caveat. If Modal tags remain empty,
billing reconciliation may be UTC-window-only and must be labeled as such.

## Namespaces

Authorized future namespaces only:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/<wave_id>/<shard_id>
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/<wave_id>/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20*
```

Forbidden namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
mlruns
L3 paths
```

## Timing Observability

Required sidecar-only fields:

```text
wall_clock_seconds_per_row
generation_attempt_count
compile_attempt_count
correctness_call_count
p_repair_attempt_count
c_repair_attempt_count
terminal_failure_type
timeout_or_stop_reason if applicable
wave_id
shard_id
```

These fields are operational diagnostics only and must not be used for
speedup, benchmark, throughput, latency, cost-per-success, performance, or
paper evidence claims.

## High-Risk Cells

Known high-risk cells:

```text
matmul__fp32/template_upper_bound__c_on__p_off
matmul__fp32/task_agnostic__c_on__p_on
reduction/task_agnostic cells
```

Use the signed long wall-clock budgets. Do not use the old 1800s per-cell stop
limit from L2b-2 for L2b-4.

## Runtime Readiness Checklist

The runtime gate and planner must satisfy:

```text
token_allowlist_contains: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
selector_profile: l2b_n20_full_coverage
runtime_dispatch_guard_removed_for_signed_n20_only: true
mocked_modal_dispatch_test_present: true
no_overwrite_command_generation: true
create_mode_for_signed_n20_token: true
fail_if_any_target_path_exists: true
observability_create_mode_present: true
clean_worktree_required_before_future_launch: true
local_origin_alignment_required_before_future_launch: true
```

The future launch agent must run `git status --short --branch`,
`git rev-parse HEAD`, `git rev-parse origin/codex-track-handoff-context`, and
confirm local equals origin before launch. Launch from a dirty worktree is
forbidden.

## Fireworks Boundary

Fireworks API implementation may proceed separately. This packet does not
authorize Fireworks execution, Fireworks billing, Fireworks credentials use, or
Fireworks output/artifact mutation.

## Validation

Packet-preparation validation:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
protected mutation scan over outputs, artifacts, mlruns, docs/preliminary_report, dependency files, and lockfiles
packet signature scan for token, row counts, wave counts, no-overwrite, no-retry, no-resume, Fireworks boundary, and wall-clock budgets
```

## No-Execution Proof

Packet preparation may run only git inspection, local pytest, local compileall,
diff checks, protected mutation scans, packet/audit/handoff edits, staging,
commit, and push. It must not invoke Modal, run GPU jobs, generate rows, launch
L2b-4, launch L2b-2, mutate outputs/artifacts/mlruns, refresh preliminary
reports, run billing queries, or touch Fireworks implementation.
