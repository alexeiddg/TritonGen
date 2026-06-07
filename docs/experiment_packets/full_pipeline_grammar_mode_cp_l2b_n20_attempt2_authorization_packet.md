# Full Pipeline L2b-4 n=20 Attempt2 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.0`
packet_type: signed bounded relaunch authorization packet
target_branch: `codex-track-handoff-context`
execution_code_target_commit: `2e9ca7b1959e09d97a370838a909a0c935175fa9`
runtime_gate_commit: current packet commit after review
selector_profile_id: `l2b_n20_attempt2_full_coverage`
scale_namespace: `l2b_n20_attempt2`
rung: `L2b-4`
status: `SIGNED_ATTEMPT2_ONLY_NO_EXECUTION_DURING_DRAFT`
classification: `L2B_N20_ATTEMPT2_AUTHORIZATION_READY`

```text
AUTHORIZES_EXECUTION: YES_L2B_N20_ATTEMPT2_ONLY
MODAL_AUTHORIZED: YES_L2B_N20_ATTEMPT2_ONLY
GPU_AUTHORIZED: YES_L2B_N20_ATTEMPT2_ONLY
GENERATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N20_ATTEMPT2_RECONCILIATION_ONLY_AFTER_WAVES
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
FIREWORKS_EXECUTION_AUTHORIZED: NO
L2B_N20_ORIGINAL_MUTATION_AUTHORIZED: NO
L2B_N2_MUTATION_AUTHORIZED: NO
L2B_N2_RECOVERY_MUTATION_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N20_ATTEMPT2_ONLY
```

This packet authorizes only a fresh create-only L2b n20 relaunch under
`l2b_n20_attempt2`. It does not authorize continuing, retrying, resuming,
overwriting, deleting, or patching the archived partial `l2b_n20` attempt.

## Prerequisites And Archive Boundary

L2b-2 prerequisite:

```text
logical_rows_complete: 216/216
complete_shards: 9/9
duplicate_logical_keys: 0
missing_logical_keys: 0
classification: L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT
```

Original L2b n20 attempt:

```text
namespace: l2b_n20
classification: L2B_N20_PARTIAL_WAVE1_ARCHIVED_LAUNCH_SURFACE_REPAIRED
completed_waves: 0
partial_result_jsonl_files: 3
partial_content_hash_sidecars: 3
partial_observability_jsonl_files: 3
partial_observability_hash_sidecars: 3
partial_observability_summary_sidecars: 0
archive_reference: audits/l2b_n20_partial_wave1_launch_surface_blocker_report.md
```

The original `l2b_n20` namespace is read-only provenance. Attempt2 must use
only the new `l2b_n20_attempt2` namespace.

## Matrix Scope

```text
condition selector: grammar_mode_cp_12cell
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
kernel classes: elementwise, reduction, matmul
dtype variants: fp32, fp16, bf16
total_shards: 9
cells_per_shard: 12
n: 20
rows_per_shard: 240
total_planned_rows: 2160
repair_history_policy: agentic_transcript_v1
backend: modal_local_model
TRITONGEN_MLFLOW: 0
```

## Wave Execution Plan

```text
wave_1:
  selector: wave:0:3
  shards: elementwise__fp32, elementwise__fp16, elementwise__bf16
  planned_rows: 720

wave_2:
  selector: wave:3:3
  shards: reduction__fp32, reduction__fp16, reduction__bf16
  planned_rows: 720

wave_3:
  selector: wave:7:2
  shards: matmul__fp16, matmul__bf16
  planned_rows: 480

wave_4:
  selector: matmul__fp32
  shards: matmul__fp32
  planned_rows: 240
```

Wave 4 isolates `matmul__fp32` because L2b-2 hit a slow-cell stop in matmul
fp32 scope. Wave 3 uses `wave:7:2`, matching the repo shard order for
`matmul__fp16` and `matmul__bf16`.

## Command Bundle

Dry plan for all shards:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution plan for all shards:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Wave 1 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:0:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

Wave 2 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:3:3 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

Wave 3 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector wave:7:2 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

Wave 4 command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

One-shard command template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_full_coverage --l2b-shard-selector <kernel_class>__<dtype_variant> --kernel-class <kernel_class> --scale-tier paper --n 20 --dtypes <dtype_variant> --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

Post-wave validation commands:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_1 --expected-rows 720 --require-content-hash-sidecars --require-observability-sidecars
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_2 --expected-rows 720 --require-content-hash-sidecars --require-observability-sidecars
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_3 --expected-rows 480 --require-content-hash-sidecars --require-observability-sidecars
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --wave-id wave_4 --expected-rows 240 --require-content-hash-sidecars --require-observability-sidecars
```

Combined validation command:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_full_coverage --expected-rows 2160 --expected-shards 9 --require-content-hash-sidecars --require-observability-sidecars
```

Analyzer/report command after 2160/2160 only:

```bash
.venv/bin/python -m cluster3.analysis.grammar_mode_cp_factorial_l2b --stage l2b_n20_attempt2_full_coverage --require-validated-rows 2160 --no-performance-claims
```

Billing reconciliation template after each wave and combined total:

```bash
.venv/bin/python -m cluster3.billing.reconcile_modal_costs --stage l2b_n20_attempt2_full_coverage --wave-id <wave_id> --utc-window <start_utc>/<end_utc> --output artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/<wave_id>_billing_reconciliation.json
```

## Stop Limits

```text
max_total_rows: 2160
max_rows_per_shard: 240
max_shards: 9
max_rows_per_cell_per_shard: 20
wave_1_max_rows: 720
wave_2_max_rows: 720
wave_3_max_rows: 480
wave_4_max_rows: 240
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
abort_if_namespace_escapes_l2b_n20_attempt2: true
```

If a wall-clock limit is exceeded, finish the active row if safe, stop the
active wave, classify
`L2B_N20_ATTEMPT2_WAVE_TERMINAL_WALLCLOCK_LIMIT`, preserve partial attempt2
audit, and do not retry or resume automatically.

## Spend And Concurrency

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

Carry forward the Modal empty-tag billing caveat. If Modal tags are empty,
billing reconciliation may be UTC-window-only and must be labeled as such.

## Namespaces

Authorized attempt2-only namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*
```

Forbidden namespaces:

```text
l2b_n20 original partial namespace
l2b_n2 namespace
l2b_n2_recovery_missing28 namespace
l2_n20 namespace
L3 paths
mlruns
docs/preliminary_report
dependency files
lockfiles
Fireworks implementation files
```

## Runtime Readiness

```text
token_allowlist_contains: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
selector_profile: l2b_n20_attempt2_full_coverage
runtime_dispatch_guard_removed_for_signed_attempt2_only: true
mocked_modal_dispatch_test_present: true
validator_entrypoint_resolves: true
missing_run_result_classification: L2B_N20_RUN_FAILED_INTERRUPTED_OR_MISSING_RUN_RESULT
no_overwrite_command_generation: true
create_mode_for_signed_attempt2_token: true
fail_if_any_target_path_exists: true
observability_event_hash_summary_sidecars_required: true
dirty_worktree_launch_forbidden: true
local_origin_alignment_required_before_launch: true
```

Launch preflight must run `git status --short --branch`, `git rev-parse HEAD`,
`git rev-parse origin/codex-track-handoff-context`, target path absence scans,
DNS/auth checks, local tests, and protected mutation scans before Wave 1.

## Fireworks Boundary

Fireworks API implementation and execution remain separate. This packet does
not authorize Fireworks credentials, Fireworks billing, Fireworks output or
artifact mutation, or Fireworks implementation edits.

## No Execution During Draft

This packet was prepared under:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
```

No Modal, GPU, generation, experiment execution, output/artifact/mlruns
mutation, billing query, Fireworks work, retry, resume, overwrite, or analyzer
refresh occurred while drafting this packet.
