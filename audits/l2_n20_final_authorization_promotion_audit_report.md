# L2 n=20 Final Authorization Promotion Audit Report

## Source Branch

```text
codex/l2-n20-final-authorization
```

## Promoted Commit

```text
bd84940 Authorize L2 n20 execution
```

## Target Baseline

Promotion target:

```text
target_branch: codex-track-handoff-context
pre_promotion_head: 182db35 Review L2 n20 final signature readiness
post_promotion_head: bd84940 Authorize L2 n20 execution
promotion_mode: git merge --ff-only
```

The promotion was a clean fast-forward from the pushed handoff baseline.

## Authorization Status

The promoted packet signs only the L2 n=20 surface:

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
```

The packet preserves these explicit non-authorizations:

```text
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
PAPER_SCALE_CLAIMS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L3_AUTHORIZED: NO
```

## Signature Status

```text
SIGNATURE_STATUS: SIGNED_FOR_L2_N20_ONLY
classification: L2_N20_FINAL_AUTHORIZATION_READY
```

## Command Bundle Status

The promoted packet records the exact command bundle:

- local dry-plan command;
- local execution-plan command;
- future signed L2 n=20 execution command;
- post-run analyzer/report command;
- post-run billing reconciliation command template.

The exact future execution command is limited to
`grammar_mode_cp_12cell`, `scale_tier=paper`, `n=20`, `dtypes=fp32`,
`kernel-class=elementwise`, `repair-history-policy=agentic_transcript_v1`,
`TRITONGEN_MLFLOW=0`, and
`--signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1`.

## Stop/Spend Limits

Signed stop limits:

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

Signed spend limits:

```text
max_estimated_cost_before_launch: USD 150
max_reconciled_billing_cap: USD 250
pricing_status: advisory; accepted without live re-verification in this packet
```

## Namespace Authorization

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

## Billing Caveat

The L1b Modal billing artifact had empty tags. The promoted L2 packet preserves
that caveat and authorizes billing reconciliation only after the L2 run and only
for the selected UTC window and signed L2 billing namespace.

## No-Execution Proof

No Modal command was run. No GPU job was run. No generation was run. No L2 n=20
execution was run. No billing query was run. No analyzer/report refresh was
run. No preliminary-report refresh was run. No dependency or lockfile command
was run. No runtime code was changed by this promotion audit.

The promotion was limited to git status/log checks, a fast-forward merge, this
audit report, and handoff documentation updates.

## Classification

```text
L2_N20_FINAL_AUTHORIZATION_PROMOTION_COMPLETE
```

## Next-Step Recommendation

Create the narrow runtime-gate enablement branch from the promoted handoff
trunk. The gate patch may only allow the exact signed L2 n=20 pre-launch path
to pass and must keep every other selector/token/profile combination
fail-closed. Do not execute L2 from this promotion audit.
