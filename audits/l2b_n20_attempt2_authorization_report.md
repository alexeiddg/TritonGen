# L2b n20 Attempt2 Authorization Report

## Executive Summary

This audit prepares and signs a fresh L2b n20 relaunch packet for
`l2b_n20_attempt2` only. The archived partial `l2b_n20` attempt remains
read-only provenance and is not continued, retried, resumed, overwritten,
deleted, or patched by this phase.

classification: `L2B_N20_ATTEMPT2_AUTHORIZATION_READY`

## Reason Attempt2 Is Required

The original `l2b_n20` create-only namespace received partial Wave 1 artifacts
before the launcher surfaced a missing run result. Because create-only target
paths now exist, continuing the original namespace would create overwrite,
resume, and provenance ambiguity. Attempt2 uses a distinct signed namespace:
`l2b_n20_attempt2`.

## Original Partial L2b n20 Archive Reference

Archive audit:
`audits/l2b_n20_partial_wave1_launch_surface_blocker_report.md`

Archived state:

```text
namespace: l2b_n20
completed_waves: 0
partial_result_jsonl_files: 3
partial_content_hash_sidecars: 3
partial_observability_jsonl_files: 3
partial_observability_hash_sidecars: 3
partial_observability_summary_sidecars: 0
classification: L2B_N20_PARTIAL_WAVE1_ARCHIVED_LAUNCH_SURFACE_REPAIRED
```

## L2b-2 Prerequisite Status

```text
logical_rows_complete: 216/216
complete_shards: 9/9
duplicate_logical_keys: 0
missing_logical_keys: 0
classification: L2B_N2_RECOVERY_COMPLETE_VALIDATED_WITH_OBSERVABILITY_CAVEAT
```

## Target Baseline

```text
branch: codex-track-handoff-context
required_baseline: 2e9ca7b1959e09d97a370838a909a0c935175fa9
execution_code_target_commit: 2e9ca7b1959e09d97a370838a909a0c935175fa9
```

## Attempt2 Namespace

```text
selector_profile_id: l2b_n20_attempt2_full_coverage
scale_namespace: l2b_n20_attempt2
output_root: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2
observability_root: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2
analysis_root: artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2
reports_root: artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2
billing_root: artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2
```

## Wave Execution Plan

```text
wave_1: wave:0:3 -> elementwise fp32/fp16/bf16 -> 720 rows
wave_2: wave:3:3 -> reduction fp32/fp16/bf16 -> 720 rows
wave_3: wave:7:2 -> matmul fp16/bf16 -> 480 rows
wave_4: matmul__fp32 -> matmul fp32 only -> 240 rows
```

## Exact Command Bundle

The exact dry-plan, execution-plan, four wave commands, one-shard template,
post-wave validation commands, combined validation command, analyzer/report
command, and billing reconciliation template are recorded in:

`docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_attempt2_authorization_packet.md`

Every signed execution command uses:

```text
--l2b-stage l2b_n20_attempt2_full_coverage
--signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1
```

No attempt2 command contains `--overwrite`.

## Validator Surface Readiness

The local validator entrypoint exists:

```text
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage
```

The validator now derives `n` and namespace roots from the requested L2b stage
spec and supports the signed non-contiguous Wave 3 plan that excludes
`matmul__fp32`.

## Launcher Missing-Result Handling Readiness

The signed launcher already fails closed with:

```text
L2B_N20_RUN_FAILED_INTERRUPTED_OR_MISSING_RUN_RESULT
```

This avoids the earlier `AttributeError` when a signed Modal dispatch returns
no run result.

## No-Overwrite Policy

Attempt2 is create-only:

```text
fail_if_any_target_path_exists: true
overwrite: forbidden
retry: forbidden
resume: forbidden
```

The runtime gate rejects `--overwrite`, `--resume`, mismatched tokens, wrong
stage, wrong `n`, MLflow-enabled launches, and namespace reuse.

## Long Wall-Clock Policy

```text
max_wall_clock_total: 24 hours
max_wall_clock_per_wave: 10 hours
max_wall_clock_per_shard: 8 hours
max_wall_clock_per_cell: 7200 seconds
max_wall_clock_for_matmul_fp32_wave: 12 hours
max_wall_clock_for_matmul_fp32_cell: 10800 seconds
```

The old L2b-2 1800s per-cell stop is not reused for attempt2.

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
```

If a wall-clock limit is exceeded, stop the active wave, classify
`L2B_N20_ATTEMPT2_WAVE_TERMINAL_WALLCLOCK_LIMIT`, preserve partial attempt2
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

## Output/Artifact Namespace Authorization

Authorized mutation is limited to `l2b_n20_attempt2` output, observability,
analysis, reports, and billing namespaces. Original `l2b_n20`, L2b-2,
recovery, L2, L3, `mlruns`, preliminary report, dependency, lockfile, and
Fireworks implementation paths are forbidden.

## Timing Observability Authorization

Attempt2 requires observability event files, hash sidecars, and summary
sidecars for every shard. Timing fields remain sidecar-only operational
diagnostics and are not authorized for performance, speedup, benchmark,
throughput, latency, cost-per-success, or paper evidence claims.

## Fireworks Separation

Fireworks implementation and execution remain outside this authorization.
`FIREWORKS_EXECUTION_AUTHORIZED: NO`.

## Billing Caveat

Billing reconciliation is authorized only after each wave and for the combined
attempt2 total. Carry forward the Modal empty-tag caveat; if tags are empty,
reconciliation may be UTC-window-only and must be labeled as such.

## Forbidden Scope

```text
l2b_n20 original partial namespace mutation
l2b_n2 mutation
l2b_n2_recovery_missing28 mutation
l2_n20 mutation
L3 paths
mlruns
docs/preliminary_report
dependency files
lockfiles
Fireworks implementation or execution
retry/resume/overwrite/delete
```

## Signature Status

```text
AUTHORIZES_EXECUTION: YES_L2B_N20_ATTEMPT2_ONLY
SIGNATURE_STATUS: SIGNED_FOR_L2B_N20_ATTEMPT2_ONLY
```

## No-Execution Proof

This phase did not invoke Modal, GPU jobs, generation, experiment execution,
billing queries, analyzer/report refreshes, or output/artifact/mlruns mutation.
Only packet, audit, handoff, runtime-gate, validator, and test files were
edited.

## Validation Run

Validation commands for this packet-preparation phase:

```text
git status --short --branch
git log --oneline -15
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
rg -n "YES_L2B_N20_ATTEMPT2_ONLY|SIGNED_FOR_L2B_N20_ATTEMPT2_ONLY|FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_AUTHORIZATION_PACKET_V1|l2b_n20_attempt2|2160|240|720|480|10800|7200|OVERWRITE_AUTHORIZED: NO|RETRY_AUTHORIZED: NO|RESUME_AUTHORIZED: NO|FIREWORKS_EXECUTION_AUTHORIZED: NO" docs/experiment_packets audits docs/handoff cluster3
```

The final command results are recorded in the user-facing completion report.

## Classification

`L2B_N20_ATTEMPT2_AUTHORIZATION_READY`

## Next-Step Recommendation

Commit and push this authorization package. A future launch agent may run
attempt2 only after confirming a clean, origin-aligned branch, absent attempt2
target paths, passing tests, protected mutation scan empty, and live Modal
DNS/auth readiness.
