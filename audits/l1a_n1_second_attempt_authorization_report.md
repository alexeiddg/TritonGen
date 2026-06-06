# L1a n=1 Second-Attempt Authorization Report

report_version: 1.0.0
created_at: 2026-06-06
branch: codex-track-handoff-context
current_promoted_head: 8ed054d64265e798e65c77d8d5cc5bfbb5d58c7f
guard_unlock_commit: bf7989d Unlock signed L1a n1 runtime guard
classification: L1A_N1_SECOND_ATTEMPT_AUTHORIZED

## User Authorization Source

`AUTHORIZATION_SOURCE: "User message: I authorize a second attempt."`

`SECOND_L1A_N1_ATTEMPT_AUTHORIZED: YES`

This authorization applies to exactly one fresh L1a n=1 attempt after the
runtime guard unlock promotion. It is not a retry and is not a resume of the
first failed pre-launch attempt.

## First Attempt Result

The first authorized L1a n=1 command was invoked once and failed before Modal
launch at `cluster3/experiments/run_cluster3_modal.py:1117`.

Result:

- rows written: 0
- Modal launch: no
- GPU allocation: no
- generation: no
- correctness calls: no
- output namespace mutation: no
- artifact namespace mutation: no
- `mlruns/` mutation: no

The first-attempt audit is
`audits/l1a_n1_execution_run_report.md`.

## Guard Unlock Commit

`bf7989d Unlock signed L1a n1 runtime guard`

The guard unlock was promoted into `codex-track-handoff-context` and audited in
`audits/l1a_runtime_guard_unlock_promotion_audit_report.md`.

## Current Promoted HEAD

`8ed054d64265e798e65c77d8d5cc5bfbb5d58c7f`

Commit subject:
`Audit L1a runtime guard unlock promotion`

## Execution Scope

Authorized execution scope:

- L1a only
- n=1 only
- 12 cells only
- `scale_tier == smoke`
- `kernel_class == elementwise`
- `dtypes == fp32`
- `repair_history_policy == agentic_transcript_v1`
- `TRITONGEN_MLFLOW=0`
- overwrite mode only when target paths are absent

Expected matrix:

- `grammar_mode in {grammar_off, template_upper_bound, task_agnostic}`
- `C in {off, on}`
- `P in {off, on}`

Expected rows: 12 total, exactly 1 row per cell.

## Exact Command To Run

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

Invocation count authorized: 1.

## Stop Limits

- max_rows: 12
- max_generation_attempts: 72
- max_correctness_calls: 72
- max_wall_clock: 4h
- fail if planned rows are not exactly 12
- fail if any target path exists before launch
- stop after one invocation regardless of success or failure
- no retry
- no resume

## Spend Limits

- max_estimated_cost: USD 25
- max_reconciled_billing_cost: USD 50

If billing reconciliation is blocked by rate limit, classify the billing step as
rate-limited and do not rerun the experiment.

## Output and Artifact Namespace Authorization

Authorized output namespace:

`outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`

Authorized observability artifact namespace:

`artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`

Authorized content-hash sidecars are limited to the same L1a n=1 namespace.

`OUTPUT_MUTATION_AUTHORIZED: YES_L1A_NAMESPACES_ONLY`

`ARTIFACT_MUTATION_AUTHORIZED: YES_L1A_NAMESPACES_ONLY`

Mutation outside these namespaces is not authorized.

## Billing Reconciliation Authorization

`BILLING_QUERY_AUTHORIZED: YES_L1A_RECONCILIATION_ONLY_AFTER_RUN`

Billing reconciliation is authorized only if the second attempt creates a Modal
run window. If the command fails before Modal launch, billing reconciliation is
not required. If Modal billing is rate-limited, record the rate-limit
classification and do not rerun.

## Post-Run Validation Authorization

`POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY`

Post-run validation is authorized only for the listed L1a checks:

- exactly 12 rows
- exactly 12 unique cells
- exactly 1 row per cell
- grammar modes exactly `grammar_off`, `template_upper_bound`, and
  `task_agnostic`
- C off/on represented
- P off/on represented
- no-P cells labeled controls
- L1a n=1 output namespace only
- observability sidecars exist
- content-hash sidecars exist
- `mlruns/` absent when `TRITONGEN_MLFLOW=0`
- no preliminary report refresh
- no benchmark, profiler, performance, or speedup claim

## Authorization Fields

`MODAL_AUTHORIZED: YES_L1A_N1_SECOND_ATTEMPT_ONLY`

`GPU_AUTHORIZED: YES_L1A_N1_SECOND_ATTEMPT_ONLY`

`GENERATION_AUTHORIZED: YES_L1A_N1_SECOND_ATTEMPT_ONLY`

`EXPERIMENT_EXECUTION_AUTHORIZED: YES_L1A_N1_SECOND_ATTEMPT_ONLY`

`MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO`

## No Retry/No Resume Statement

The first failed pre-launch attempt must not be retried or resumed.

This packet authorizes one new second attempt after the guard unlock promotion.
The command must be invoked once only. If it fails, do not retry, do not resume,
and do not repair in-place.

## Forbidden Scope

This authorization does not allow:

- L1b
- L2
- paper-scale execution
- n=5
- n=20
- retry
- resume
- profiler
- benchmark
- speedup or performance claim
- MLflow tracking execution or `mlruns/` mutation
- preliminary report refresh
- output or artifact writes outside signed L1a n=1 namespaces
- scientific row, grammar, repair policy, sampling/model, or pass/fail changes

## Classification

`L1A_N1_SECOND_ATTEMPT_AUTHORIZED`
