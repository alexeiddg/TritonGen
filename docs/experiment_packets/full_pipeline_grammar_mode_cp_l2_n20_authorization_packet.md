# Full Pipeline Grammar-Mode x C x P L2 n=20 Authorization Packet Draft

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_DRAFT_V1`
packet_version: `0.1.0-draft-blocked-command-surface`
packet_type: L2 n=20 authorization packet draft; not an execution packet
branch: `codex/l2-n20-authorization-packet`
target_branch: `codex-track-handoff-context`
execution_code_target_commit: `134bcf9c7fda9da933acf6fe3f93766b2b0a731e Audit L1b n5 completion and analyzer boundary`
baseline_commit: `134bcf9 Audit L1b n5 completion and analyzer boundary`
status: `UNSIGNED_COMMAND_SURFACE_BLOCKED`
signature_status: `UNSIGNED`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
L2_AUTHORIZED: NO
N20_AUTHORIZED: NO
PAPER_SCALE_CLAIMS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
```

This packet drafts the bounded approval surface for a future L2 n=20 run of the
12-cell `grammar_mode x C x P` matrix. It records target baseline, proposed
commands, stop limits, spend limits, artifact namespaces, validation surfaces,
and signature fields. It does not authorize Modal, GPU use, generation,
experiment execution, output mutation, artifact mutation, billing queries,
runtime MLflow writes, retry, resume, analyzer/report artifact refresh, or
paper-scale claims.

The current repo cannot yet execute this packet as written. The launcher has
selector profiles for L1a n=1 smoke and L1b n=5 development only. A later
narrow implementation branch must add a source-backed L2 n=20 selector profile,
signed L2 authorization option/token, L2 output and observability roots, and
paper-scale analyzer compatibility proof before this packet can become
signable.

## Readiness Evidence

L1a evidence:

- `61fa0ac Validate L1a n1 12-cell completion`
- `1367cdb Preserve L1a n1 generated artifacts`
- `bc77e9b Audit L1a analyzer patch and golden drift`
- `audits/l1a_n1_attempt_006_completion_report.md`
- `audits/l1a_analyzer_patch_and_golden_drift_audit.md`

L1b evidence:

- `a52d64a Authorize L1b n5 selector profile`
- `387c073 Complete L1b n5 12-cell validation`
- `134bcf9 Audit L1b n5 completion and analyzer boundary`
- `audits/l1b_n5_execution_authorization_report.md`
- `audits/l1b_n5_execution_completion_report.md`
- `audits/l1b_n5_analyzer_dev_scope_patch_report.md`
- `audits/l1b_n5_completion_and_analyzer_boundary_audit.md`

The L1b boundary audit classifies the current baseline as
`L1B_N5_AUDIT_PASS_L2_READY` for separate L2 n=20 packet drafting and review
only. It does not authorize L2 execution.

## L2 Scope

Experiment id:

```text
full_pipeline_grammar_mode_cp_factorial_v1
```

Design:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

Expected cells:

```text
12
```

Expected rows:

```text
n_per_cell: 20
kernel_class: elementwise
dtypes: fp32
rows_per_cell: 20
total_rows: 240
scale_tier: paper
```

Runtime MLflow policy:

```text
TRITONGEN_MLFLOW=0
```

MLflow may be used later for post-hoc indexing only if a separate signed packet
authorizes the exact post-hoc operation. JSONL rows and repo analyzers remain
the scientific source of truth.

## Authorized Future Namespaces

Future output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
```

Future artifact namespaces:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
```

Target paths must be absent before any future signed launch. The path-collision
policy is:

```text
fail_if_any_target_path_exists: true
```

## Command Bundle Status

Current command-surface classification:

```text
L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE
```

Reason:

`cluster3/experiments/run_cluster3_modal.py` currently defines selector
profiles only for:

```text
L1a n=1 smoke
L1b n=5 development
```

The current `_selector_profile_for_scale()` function rejects
`--scale-tier paper --n 20` for `--condition grammar_mode_cp_12cell`. The
current CLI also exposes `--signed-l1a-authorization` and
`--signed-l1b-authorization`, not a signed L2 authorization option.

Required implementation before signature:

- add L2 namespace constants for `l2_n20`;
- add an L2 selector profile for `scale_tier=paper`, `n=20`, and 240 planned
  rows;
- add a signed L2 authorization option/token without reusing L1a or L1b tokens;
- keep `TRITONGEN_MLFLOW=0` required for signed selector execution unless a
  later packet explicitly changes the policy;
- keep selector-level path collision checks fail-closed;
- prove all 12 cells plan into the L2 namespace and all target paths are absent;
- prove paper-scale analyzer/report strictness is satisfied without using L1a
  smoke or L1b development pair-skip scopes.

## Future Command Surfaces

These commands are proposed for the eventual L2 packet. They are not authorized
by this draft and are blocked until the L2 selector/profile implementation
exists.

Dry-plan command, blocked until L2 profile support exists:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution-plan command, blocked until L2 profile support exists:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future execution command, blocked until signed L2 support exists:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1 --overwrite
```

Post-run analyzer/report command, blocked until valid L2 outputs exist and
paper-scale analyzer strictness is satisfied:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/*.jsonl --analysis-scope primary_functional --scale-tier paper --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.md
```

Post-run billing reconciliation command template, blocked until a signed billing
query window exists:

```bash
.venv/bin/python -m modal billing report --start <YYYY-MM-DD> --end <YYYY-MM-DD> --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

The billing JSON may be written only to:

```text
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_billing_report_<YYYYMMDD>_utc.json
```

## Stop Limits

Proposed limits; not signed:

```text
max_rows: 240
max_generation_attempts: 1440
max_correctness_calls: 1440
max_wall_clock: 24h
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
overwrite_policy: only if all target L2 paths are absent before launch
abort_if_row_count_exceeds: 240
abort_if_command_requests_l1a_l1b_l3_or_non_l2_scope: true
```

Rationale:

- L1b n=5 used 60 planned rows and the existing authorization capped generation
  and correctness calls at 360 each.
- L2 n=20 is four times the L1b row count, so the conservative per-row cap
  scales to 1440 generation attempts and 1440 correctness calls.
- The L1b authorization used a 6h wall-clock cap for 60 rows. Scaling that cap
  by four yields a proposed 24h L2 cap. The exact cap should be refreshed from
  available L1b observability timing before final signature.

Stop immediately on:

- any target L2 output, content-hash sidecar, observability event sidecar,
  observability summary sidecar, observability hash sidecar, analysis artifact,
  report artifact, billing artifact, or `mlruns/` write outside the signed
  namespace;
- row count above 240;
- fewer than 12 cells;
- any cell with rows not equal to 20;
- missing or mismatched content-hash sidecar;
- missing or mismatched observability hash sidecar;
- P loop firing in no-P controls;
- C loop firing outside C-active rows or outside eligible F2 routing;
- private-eval leakage;
- performance/profiler/speedup/cost-per-success claim leakage;
- dependency, lockfile, Modal image, model revision, tokenizer revision,
  grammar semantics, repair policy, sampling, or pass/fail definition drift.

## Spend Limits

Proposed limits; not signed:

```text
pricing_status: must be re-verified before final signature
l1b_utc_window_cost_usd: 2.13879534
l1b_billing_attribution: UTC-window-only because Modal tags were empty
l2_row_scale_factor_from_l1b: 4
rough_l2_linear_cost_reference_usd: 8.55518136
max_estimated_cost_before_launch: USD 150
max_reconciled_billing_cap: USD 250
billing_reconciliation_source_of_truth: actual Modal billing report
```

The L1b billing artifact had empty Modal tags. That caveat must be carried into
L2. A future L2 billing artifact is authoritative for spend only after it is
reconciled to the signed UTC window and recorded with the empty-tag caveat if
tags remain empty. This packet makes no cost-per-success, ROI, speedup, or
economic-lift claim.

## Evidence Boundary

L2 n=20 is the first evidence-quality rung for the 12-cell
`grammar_mode x C x P` matrix. It is not a paper conclusion by itself until the
post-run analyzer/report output is audited.

Required boundaries:

- graph grammar effects by explicit `grammar_mode`; do not collapse
  `template_upper_bound` and `task_agnostic` into an unqualified `G` claim;
- keep `grammar_off` controls separate from grammar-active rows;
- respect analyzer strictness and reportability gates;
- do not use L1a smoke or L1b development pair-skip scopes for L2 paper-scale
  reporting;
- do not claim speedup, performance lift, cost reduction, ROI, or
  cost-per-success;
- carry the empty-tag billing caveat from L1b until Modal billing tags are
  demonstrably populated for L2.

## Post-Run Validation Plan

Future validation after a separately signed L2 execution:

```text
git status --short --branch
git diff --check
```

Expected output validation:

```text
12 JSONL files under outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
240 total rows
20 rows per cell
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C values: c_off, c_on
P values: p_off, p_on
content-hash sidecars valid for all 12 JSONL files
observability event, summary, and hash sidecars valid for all 12 cells
no P repair activity in no-P controls
C/P repair activity only in eligible rows
mlruns absent unless a separate packet authorized runtime MLflow
```

Required analyzer/report validation:

```text
analysis_scope: primary_functional
scale_tier: paper
reportable: true only if analyzer strictness passes
grammar_mode_summary.status: explicit_grammar_mode
no binary grammar collapse for template_upper_bound and task_agnostic
three_way_interaction.reportable: true only if the analyzer marks the full L2 output reportable
```

## Human Signature Block

All fields are unsigned.

```text
target_commit_accepted:
command_bundle_accepted:
stop_limits_accepted:
spend_limits_accepted:
output_artifact_mutation_accepted:
billing_reconciliation_accepted:
post_run_validation_accepted:
modal_gpu_generation_accepted:
no_retry_no_resume_accepted:
no_digest_or_digest_policy_accepted:
signature_status: UNSIGNED
AUTHORIZES_EXECUTION: NO
```

## Remaining Blockers

1. L2 selector/profile support is missing.
2. Signed L2 authorization option/token is missing.
3. L2 dry-plan and execution-plan commands are currently rejected by the
   selector profile gate.
4. L2 output, observability, run-id, and placeholder constants are missing.
5. Paper-scale analyzer strictness must be proven for valid 12-cell selector
   output without using non-paper L1a/L1b pair-skip scopes.
6. Pricing must be re-verified before signature.
7. Spend and wall-clock caps must be human-signed.
8. Billing query window and billing artifact write must be separately signed.
9. Output/artifact mutation must remain blocked until final signature.

## Classification

`L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE`

## Next-Step Recommendation

Create a narrow local-only L2 selector/profile support branch. It should make
`grammar_mode_cp_12cell` representable for `scale_tier=paper`, `n=20`, 240
planned rows, L2 namespaces, and signed L2 authorization planning without
running Modal, generation, billing, analyzer/report refresh, or output/artifact
mutation. After that branch is reviewed and promoted, revisit this packet for
final signature readiness.
