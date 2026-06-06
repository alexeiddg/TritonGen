# L2 n=20 Final Authorization Report

## Executive Summary

This report reviews the final L2 n=20 authorization packet prepared on
`codex/l2-n20-final-authorization` from baseline
`182db35ccc4fd0dd57c0c258bb3c35645c511004`.

The packet now signs the bounded L2 n=20 authorization surface for the 12-cell
`grammar_mode x C x P` matrix. This audit did not execute L2, invoke Modal,
run GPU work, run generation, query billing, mutate output or artifact
namespaces, refresh analyzer/report artifacts, change runtime code, or change
scientific semantics.

Classification: `L2_N20_FINAL_AUTHORIZATION_READY`.

Important execution caveat: the target baseline still records the L2 runtime
selector profile as fail-closed. The packet authorizes the exact L2 n=20
surface, but this docs-only branch does not enable the runtime gate.

## Target Baseline

```text
target_branch: codex-track-handoff-context
execution_code_target_commit: 182db35ccc4fd0dd57c0c258bb3c35645c511004
baseline_commit: 182db35 Review L2 n20 final signature readiness
packet_branch: codex/l2-n20-final-authorization
packet_path: docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md
```

The working branch was created from the required baseline.

## L1a/L1b Readiness Evidence

L1a evidence reviewed:

- `audits/l1a_n1_attempt_006_completion_report.md`
- `61fa0ac Validate L1a n1 12-cell completion`
- `1367cdb Preserve L1a n1 generated artifacts`
- `bc77e9b Audit L1a analyzer patch and golden drift`

L1b evidence reviewed:

- `audits/l1b_n5_completion_and_analyzer_boundary_audit.md`
- `a52d64a Authorize L1b n5 selector profile`
- `387c073 Complete L1b n5 12-cell validation`
- `134bcf9 Audit L1b n5 completion and analyzer boundary`

The L1b boundary audit classifies the previous rung as
`L1B_N5_AUDIT_PASS_L2_READY` for separate L2 n=20 packet work while preserving
development-scale and non-paper boundaries for L1b artifacts.

## Selector/Profile Readiness Evidence

Selector/profile evidence reviewed:

- `audits/l2_n20_selector_profile_support_promotion_audit_report.md`
- `audits/l2_n20_final_signature_readiness_report.md`
- `27493c0 Add L2 n20 selector profile support`
- `48efad7 Audit L2 n20 selector profile support promotion`
- `182db35 Review L2 n20 final signature readiness`

The promoted selector/profile support represents `grammar_mode_cp_12cell` with
`scale_tier=paper`, `n=20`, `dtypes=fp32`, 12 cells, and 240 planned rows. It
also records source-backed dry-plan, execution-plan, and signed-L2 command
surfaces.

The current code still keeps the L2 runtime profile disabled:

```text
runtime_execution_enabled: false
runtime_gate_status_at_target_baseline: DISABLED_FAIL_CLOSED
```

## Exact Command Bundle

Dry-plan command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution-plan command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Exact future execution command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1 --overwrite
```

Post-run analyzer/report command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/*.jsonl --analysis-scope primary_functional --scale-tier paper --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.md
```

Post-run billing reconciliation command template:

```bash
.venv/bin/python -m modal billing report --start <YYYY-MM-DD> --end <YYYY-MM-DD> --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

## Matrix And Row Expectation

```text
condition: grammar_mode_cp_12cell
grammar_mode: grammar_off, template_upper_bound, task_agnostic
C: off, on
P: off, on
expected_cells: 12
expected_rows_per_cell: 20
expected_rows: 240
kernel_class: elementwise
dtypes: fp32
scale_tier: paper
repair_history_policy: agentic_transcript_v1
runtime_mlflow: disabled with TRITONGEN_MLFLOW=0
```

## Stop Limits

```text
max_rows: 240
max_generation_attempts: 1440
max_correctness_calls: 1440
max_wall_clock: 24h
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
abort_if_row_count_exceeds: 240
abort_if_target_namespace_outside_l2_n20: true
abort_if_runtime_mlflow_tracking_enabled: true
```

## Spend Limits

```text
pricing_status: advisory; accepted without live re-verification in this packet
l1b_utc_window_cost_usd: 2.13879534
l1b_billing_attribution: UTC-window-only because Modal tags were empty
l2_row_scale_factor_from_l1b: 4
rough_l2_linear_cost_reference_usd: 8.55518136
max_estimated_cost_before_launch: USD 150
max_reconciled_billing_cap: USD 250
billing_reconciliation_source_of_truth: actual Modal billing report
```

The packet makes no speedup, performance, ROI, cost-per-success, or economic
claim.

## Output/Artifact Namespace Authorization

Authorized future output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
```

Authorized future artifact namespaces:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
```

Any target path outside those namespaces remains forbidden.

## Billing Caveat

The L1b billing artifact had empty Modal tags. L2 billing reconciliation is
therefore authorized only as post-run UTC-window reconciliation unless Modal
tags are demonstrably populated for L2.

```text
BILLING_QUERY_AUTHORIZED: YES_L2_N20_RECONCILIATION_ONLY_AFTER_RUN
```

## Post-Run Validation Authorization

The packet authorizes only the listed post-run validation commands and checks:

```text
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
12 JSONL files
240 total rows
20 rows per cell
explicit grammar_mode values
C/P eligibility checks
content-hash sidecars
observability event, summary, and hash sidecars
mlruns absent unless separately authorized
paper-scale analyzer strictness before graph/report/paper claims
```

## Forbidden Scope

Forbidden in this authorization:

- L3, additional kernels, extra dtypes, profiler, benchmark, timing,
  performance, speedup, ROI, or cost-per-success claims
- preliminary report refresh
- dependency or lockfile changes
- runtime MLflow tracking
- output/artifact mutation outside the L2 n=20 namespaces
- analyzer/report claims before post-run audit
- retry or resume
- grammar semantics, repair policy, sampling, model, tokenizer, pass/fail, or
  scientific-row schema changes

## Signature Status

```text
AUTHORIZES_EXECUTION: YES_L2_N20_ONLY
MODAL_AUTHORIZED: YES_L2_N20_ONLY
GPU_AUTHORIZED: YES_L2_N20_ONLY
GENERATION_AUTHORIZED: YES_L2_N20_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2_N20_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2_N20_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2_N20_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2_N20_RECONCILIATION_ONLY_AFTER_RUN
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2_N20_ONLY
```

## No-Execution Proof

No Modal command was run. No GPU job was run. No generation was run. No L2 n=20
execution was run. No billing query was run. No analyzer/report refresh was
run. No preliminary-report refresh was run. No dependency or lockfile command
was run. No runtime code was changed.

Validation was limited to local tests, local compilation, git checks, protected
mutation scans, packet signature scans, and docs-only edits.

## Classification

```text
L2_N20_FINAL_AUTHORIZATION_READY
```

## Next-Step Recommendation

Do not execute from this packet-preparation branch. If the next phase is
execution, first perform an execution-readiness step that verifies or enables
only the L2 n=20 runtime gate for the signed selector profile, then runs exactly
the signed command from this packet under the signed stop, spend, namespace,
billing, and post-run validation limits.
