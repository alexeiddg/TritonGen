# L2b n20 Final Authorization Report

## Executive Summary

This audit records preparation of the final signed L2b-4 / L2b n20
authorization packet for human review. The packet signs only the 2160-row L2b
n20 scope and does not execute L2b-4 during drafting.

Classification:
`L2B_N20_FINAL_AUTHORIZATION_READY`.

## L2b-2 Prerequisite Satisfaction

The prerequisite L2b-2 gate is satisfied:

```text
base_l2b_2_rows: 188
recovery_rows: 28
combined_logical_rows: 216/216
duplicate_logical_keys: 0
missing_logical_keys: 0
complete_shards: 9/9
classification: L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT
clean_post_recovery_baseline: 28255c3afec51a2d61fcd59dbe9ee624b45e1306
baseline_classification: L2B_N2_POST_RECOVERY_BASELINE_CLEAN_READY_FOR_L2B4_AUTHORIZATION
```

## L2b-2 Observability Caveat Carried Forward

The `reduction__fp16` missing-28 recovery has result rows and hash sidecars but
no observability sidecars. This caveat is explicitly carried into the L2b n20
packet. It does not block L2b-4 because the post-recovery reconciliation added
and tested create-mode support for result and observability loggers.

L2b-4 must emit observability event, hash, and summary sidecars for every n20
shard. Missing n20 observability sidecars after a wave must be classified as a
validation caveat or failure under the signed rules. Rows must not be rerun
solely to patch observability.

## Target Baseline

```text
target_branch: codex-track-handoff-context
required_clean_baseline: 28255c3afec51a2d61fcd59dbe9ee624b45e1306
execution_code_target_commit: 28255c3afec51a2d61fcd59dbe9ee624b45e1306
```

The runtime gate patch in this commit adds the exact L2b n20 token and
create-only/no-overwrite parser behavior without executing any experiment.

## L2b-4 Scope

```text
condition selector: grammar_mode_cp_12cell
grammar modes: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
kernel classes: elementwise, reduction, matmul
dtype variants: fp32, fp16, bf16
shards: 9
n: 20
rows_per_shard: 240
total_rows: 2160
TRITONGEN_MLFLOW: 0
profiler: not authorized
benchmark: not authorized
performance_or_speedup_claims: not authorized
```

## Wave Execution Plan

```text
wave_1: elementwise__fp32, elementwise__fp16, elementwise__bf16 = 720 rows
wave_2: reduction__fp32, reduction__fp16, reduction__bf16 = 720 rows
wave_3: matmul__fp16, matmul__bf16 = 480 rows
wave_4: matmul__fp32 = 240 rows
```

`matmul__fp32` is isolated last because matmul fp32 scope caused the L2b-2
slow-cell stop.

## Exact Command Bundle

The command bundle is recorded in
`docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_full_coverage_authorization_packet.md`.
It includes all-shard dry plan, all-shard execution plan, Wave 1, Wave 2, Wave
3, Wave 4, one-shard template, post-wave validation, combined validation,
analyzer/report gate, and billing reconciliation templates.

All signed runtime commands use:

```text
FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
TRITONGEN_MLFLOW=0
```

No signed future command contains `--overwrite`.

## Long Wall-Clock Policy

```text
max_wall_clock_total: 24 hours
max_wall_clock_per_wave: 10 hours
max_wall_clock_per_shard: 8 hours
max_wall_clock_per_cell: 7200 seconds
max_wall_clock_for_matmul_fp32_wave: 12 hours
max_wall_clock_for_matmul_fp32_cell: 10800 seconds
```

The L2b-2 1800s per-cell stop is not used for L2b-4.

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
fail_if_any_target_path_exists: true
overwrite: forbidden
retry: forbidden
resume: forbidden
abort_if_rows_exceed_signed_limits: true
abort_if_namespace_escapes_l2b_n20: true
```

If a signed wall-clock budget is exceeded, stop the active wave after safe row
completion, classify `L2B_N20_WAVE_TERMINAL_WALLCLOCK_LIMIT`, preserve partial
audit, and do not retry or resume automatically.

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

Carry forward the Modal empty-tag billing caveat. Billing may be UTC-window-only
if Modal tags remain empty.

## Output And Artifact Namespace Authorization

Authorized future namespaces are limited to `l2b_n20` output, observability,
analysis, reports, and billing paths listed in the signed packet.

Forbidden scopes include `l2b_n2`, `l2b_n2_recovery_missing28`, `l2_n20`, L3
paths, and `mlruns`.

## Timing Observability Authorization

L2b n20 is authorized to record sidecar-only operational diagnostics:

```text
wall_clock_seconds_per_row
generation_attempt_count
compile_attempt_count
correctness_call_count
p_repair_attempt_count
c_repair_attempt_count
terminal_failure_type
timeout_or_stop_reason
wave_id
shard_id
```

These diagnostics are not performance evidence.

## High-Risk Cell Policy

Known high-risk cells:

```text
matmul__fp32/template_upper_bound__c_on__p_off
matmul__fp32/task_agnostic__c_on__p_on
reduction/task_agnostic cells
```

Use long wall-clock budgets, preserve partial wave audit on a terminal budget
limit, and do not auto-retry or auto-resume.

## Token Allowlist And Dispatch Readiness

Runtime/planner readiness changes in this commit:

```text
token_allowlist_contains: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
stage_profile: l2b_n20_full_coverage
signature_status: SIGNED_FOR_L2B_N20_ONLY
future_command_omits_overwrite: true
parser_write_mode_for_signed_n20: create
mocked_modal_dispatch_boundary_test: present
fail_closed_for_l2b_n2_token_on_l2b_n20: present
```

Future launch still requires clean worktree and local/origin alignment before
Modal dispatch.

## No-Overwrite Policy

L2b n20 commands omit `--overwrite`; the signed token maps to create mode.
Target paths must be absent. Existing target paths fail closed.

## Fireworks Separation

Fireworks API implementation is separate. This packet does not authorize
Fireworks execution, Fireworks billing, Fireworks credential use, or Fireworks
output/artifact mutation.

## Billing Caveat

Billing reconciliation is authorized only after each wave and after combined
total validation. If Modal tags remain empty, billing reconciliation may be
UTC-window-only and must carry that caveat.

## Post-Wave And Combined Validation Authorization

Post-wave validation must check row counts, content hash sidecars,
observability sidecars, protected mutation scope, and terminal caveats. Combined
post-run validation must check 2160/2160 rows and all 9 shards before
analyzer/report refresh unless an explicit partial-wave caveat is signed.

## Forbidden Scope

Forbidden during packet preparation:

```text
Modal execution
GPU execution
generation
experiment launch
L2b-4 launch
L2b-2 launch
outputs mutation
artifacts mutation
mlruns mutation
preliminary report refresh
billing query
Fireworks implementation or execution
grammar semantic changes
repair semantic changes
analyzer scientific semantic changes
```

## Signature Status

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

## No-Execution Proof

Packet preparation used git inspection, local pytest, local compileall, diff
checks, protected mutation scans, source/test/doc edits, staging, commit, and
push only. No Modal command, GPU command, generation entrypoint, experiment
launch, output mutation command, artifact mutation command, MLflow command,
billing query, preliminary report refresh, or Fireworks command was run.

## Validation Run

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
226 passed

.venv/bin/python -m compileall -q cluster3 shared
passed

git diff --check
passed
```

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result: empty output.

## Classification

`L2B_N20_FINAL_AUTHORIZATION_READY`.

## Next-Step Recommendation

Use the committed packet and audit as the only L2b n20 authorization surface.
Before any future launch, verify clean worktree, local/origin alignment, target
path absence, Modal DNS/auth readiness, and wave-specific command scope.
