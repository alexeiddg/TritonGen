# L2b-2 Recovery Missing-28 Authorization Report

## Executive Summary

classification: `L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_READY`
status: `READY_FOR_AUTHORIZED_RECOVERY_DRAFTING`
AUTHORIZES_EXECUTION: YES_L2B_N2_RECOVERY_MISSING28_ONLY
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_RECOVERY_MISSING28_ONLY

This report documents a separate recovery authorization scope for exactly 28 missing
rows from the partial L2b-2 archive. It is **recovery-only** and does not
authorize L2b-4/n20, L3, retry, resume, or overwrite.

No runtime execution, Modal invocation, GPU job, billing query, analyzer/report,
output mutation, artifact mutation, or `mlruns` mutation was performed during this
packet preparation.

## Target Baseline

```text
branch: codex-track-handoff-context
baseline commit: 136a8b07cc9043200de73a91be4803b59817cac4
packet: docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_recovery_missing28_authorization_packet.md
parent archive classification: L2B_N2_TERMINAL_PARTIAL_SLOW_CELL_STOP
```

## Recovery Scope and Constraints

Authorized missing rows: 28
Shards: 3 partial shards
Cell instances: 14

- `reduction__fp16`: 4 cells / 8 rows
- `reduction__bf16`: 4 cells / 8 rows
- `matmul__fp32`: 6 cells / 12 rows

No completed shards or completed cells are in scope.

## Authorized Namespaces

Recovery writes are restricted to a dedicated namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
```

All base namespaces under `.../l2b_n2/` and `.../l2_n20/` must remain immutable for this run.

## Exact Recovery Command Bundle

- dry-plan and execution-plan commands are as listed in the packet.
- exact future recovery command: signed recovery + one shard at a time for:
  - `reduction__fp16`
  - `reduction__bf16`
  - `matmul__fp32`
- one-shard template is as listed in the packet.

## Stop Limits and Runtime Governance

```text
max_recovery_rows: 28
max_recovery_shards: 3
max_rows_per_recovery_shard:
  reduction__fp16: 8
  reduction__bf16: 8
  matmul__fp32: 12
max_total_combined_rows_after_recovery: 216
max_gpu_concurrency: 3
max_container_concurrency: 30
max_estimated_cost_usd: 75.00
max_reconciled_billing_cost_usd: 90.00
fail_if_recovery_target_path_exists: true
fail_if_base_archive_missing: true
fail_if_base_archive_changed: true
fail_if_duplicate_logical_row_key: true
fail_if_any_non_missing_row_is_planned: true
```

Slow-cell fail-closed policy:

```text
Signed wall-clock budget remains 1800s per cell.
On overrun, preserve partial recovery audit and stop.
Classification on overrun: L2B_N2_RECOVERY_TERMINAL_SLOW_CELL_LIMIT
No retry, no resume
```

## Authorization Block Flags

```text
AUTHORIZES_EXECUTION: YES_L2B_N2_RECOVERY_MISSING28_ONLY
MODAL_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
GPU_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
GENERATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_NAMESPACE_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_NAMESPACE_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N2_RECOVERY_RECONCILIATION_ONLY_AFTER_RUN
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L2B_N20_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_RECOVERY_MISSING28_ONLY
```

## Planned Validation Sequence

1) local test/compile gates (authorized in packet)
2) combined logical row validation across base + recovery namespaces (216/216)
3) per-shard analyzer/report commands (only after successful combined validation)
4) per-shard billing reconciliation (only after redacted report/window and authorization)

This report is non-executing and remains pending explicit runtime-gate pass before any recovery launch.
