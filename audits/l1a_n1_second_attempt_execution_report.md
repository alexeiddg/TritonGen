# L1a n=1 Second-Attempt Execution Report

report_version: 1.0.0
created_at: 2026-06-06
branch: codex-track-handoff-context
classification: L1A_SECOND_ATTEMPT_RUN_FAILED_EXECUTION
AUTHORIZES_RETRY: NO
AUTHORIZES_RESUME: NO
AUTHORIZES_L1B: NO
AUTHORIZES_L2: NO
AUTHORIZES_PAPER_SCALE: NO
AUTHORIZES_PERFORMANCE_PROFILER: NO

## Executive Summary

The runtime guard unlock commit was reviewed, promoted by fast-forward into
`codex-track-handoff-context`, audited, and pushed to origin. A fresh
second-attempt authorization audit was then committed before execution.

The exact signed L1a n=1 command was invoked once. It passed the patched
`main(...)` pre-launch authorization guard, then failed inside
`run_cluster3(...)` at the remaining internal `grammar_mode_cp_12cell` runtime
guard. The command failed before Modal launch, GPU allocation, generation,
correctness calls, output writes, observability artifact writes, content-hash
sidecar writes, `mlruns/` mutation, post-run validation, or billing
reconciliation.

No retry, resume, repair, alternate command, L1b, L2, paper-scale, n=5, n=20,
profiler, benchmark, speedup, or performance-claim path was run.

## First-Attempt Reference

First-attempt audit:
`audits/l1a_n1_execution_run_report.md`

First-attempt classification:
`L1A_N1_RUN_FAILED_EXECUTION`

First-attempt failure:
The first command failed before Modal launch at the unconditional `main(...)`
selector guard.

## Second-Attempt Authorization Commit

`0c55aa1 Authorize L1a n1 second attempt`

Authorization source:
`User message: I authorize a second attempt.`

## Guard Unlock Commit

`bf7989d Unlock signed L1a n1 runtime guard`

Promotion audit commit:
`8ed054d Audit L1a runtime guard unlock promotion`

## Exact Command Run

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

invocation_count: 1
retry_count: 0
resume_count: 0

## Start/End Timestamps

start_timestamp_utc: `2026-06-06T08:26:51Z`
end_timestamp_utc: `2026-06-06T08:27:20Z`

## Modal/GPU Metadata

modal_app_name: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
gpu_type_used: `NONE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
modal_run_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
modal_function_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
container_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`

## Output Paths

output_root:
`outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`

observability_artifact_root:
`artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`

content_hash_sidecar_paths:
`NOT_CREATED_COMMAND_FAILED_BEFORE_OUTPUT_WRITES`

observability_sidecar_paths:
`NOT_CREATED_COMMAND_FAILED_BEFORE_ARTIFACT_WRITES`

mlruns_path:
`NOT_PRESENT`

## Row-Count Result

expected_rows: 12
actual_rows: 0
result: `FAILED_EXECUTION_BEFORE_ROW_WRITES`

## 12-Cell Coverage Result

expected_cells:

- `grammar_off__c_off__p_off`
- `grammar_off__c_on__p_off`
- `grammar_off__c_off__p_on`
- `grammar_off__c_on__p_on`
- `template_upper_bound__c_off__p_off`
- `template_upper_bound__c_on__p_off`
- `template_upper_bound__c_off__p_on`
- `template_upper_bound__c_on__p_on`
- `task_agnostic__c_off__p_off`
- `task_agnostic__c_on__p_off`
- `task_agnostic__c_off__p_on`
- `task_agnostic__c_on__p_on`

actual_cells_written: 0
result: `FAILED_EXECUTION_BEFORE_CELL_WRITES`

## Post-Run Validation Result

post_run_validation_status:
`NOT_RUN_NO_L1A_ARTIFACTS_EXIST_AFTER_EXECUTION_FAILURE`

Reason:
The command failed before output or sidecar creation. The target L1a output root
and observability artifact root remained absent after the command, so there were
no artifacts for row-count, schema, sidecar, or cell-coverage validation.

## Billing Reconciliation Result

billing_reconciliation_status:
`NOT_RUN_NO_MODAL_RUN_WINDOW_AVAILABLE_AFTER_PRE_LAUNCH_FAILURE`

Reason:
The command failed before Modal launch, so there was no Modal run window to
reconcile. No billing query was run.

## Stop-Limit Compliance

- max_rows: 12
- rows_written: 0
- max_generation_attempts: 72
- generation_attempts_observed: 0
- max_correctness_calls: 72
- correctness_calls_observed: 0
- max_wall_clock: 4h
- wall_clock_observed: less_than_1_minute
- no_retry: complied
- no_resume: complied
- one_invocation_only: complied

## Spend-Limit Status

- max_estimated_cost: USD 25
- max_reconciled_billing_cost: USD 50
- Modal/GPU spend observed: none, command failed before Modal launch
- billing reconciliation required: no, no Modal run window

## Failure/Error

error_class: `RuntimeError`

error_message:

```text
grammar_mode_cp_12cell execution is not enabled by this local support branch
```

failure_location:
`cluster3/experiments/run_cluster3_modal.py:1442`

Remaining guard:

```python
if config.condition == L1A_GRAMMAR_MODE_CP_SELECTOR:
    raise RuntimeError(
        f"{L1A_GRAMMAR_MODE_CP_SELECTOR} execution is not enabled by this "
        "local support branch"
    )
```

## No Retry/No Resume Proof

The exact signed command was invoked once. After the internal guard failure, no
retry, resume, repair, alternate command, or second invocation was run.

## No L1b/L2/Paper-Scale Proof

Only the signed L1a n=1 selector command was invoked. No L1b, L2, paper-scale,
n=5, n=20, report-scale, or broader experiment command was run.

## No Benchmark/Profiler/Performance Proof

No profiler, benchmark, timing comparison, speedup measurement, performance
optimization, or performance claim was run. The command failed before Modal
launch.

## Files Created/Modified

Created by this audit step:

- `audits/l1a_n1_second_attempt_execution_report.md`

Committed before the second attempt:

- `audits/l1a_n1_second_attempt_authorization_report.md`

No L1a output files, observability sidecars, content-hash sidecars, `mlruns/`
entries, preliminary report files, dependency files, or lockfiles were created
or modified by the command.

## Classification

`L1A_SECOND_ATTEMPT_RUN_FAILED_EXECUTION`

## Next-Step Recommendation

Do not retry or resume. The next branch should be a narrow local-only runtime
selector dispatch unblock that removes or replaces the remaining
`run_cluster3(...)` internal selector guard and proves the 12-cell selector can
dispatch into the executable per-cell plan without invoking Modal. Only after
that branch is reviewed, promoted, audited, and separately authorized should a
third fresh L1a attempt be considered.
