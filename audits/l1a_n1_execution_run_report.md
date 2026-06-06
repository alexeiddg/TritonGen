# L1a n=1 Execution Run Report

report_version: 1.0.0
created_at: 2026-06-06
branch: codex-track-handoff-context
classification: L1A_N1_RUN_FAILED_EXECUTION
AUTHORIZES_RETRY: NO
AUTHORIZES_RESUME: NO
AUTHORIZES_L1B: NO
AUTHORIZES_L2: NO
AUTHORIZES_PAPER_SCALE: NO
AUTHORIZES_PERFORMANCE_PROFILER: NO

## Executive Summary

The final L1a execution authorization was promoted into
`codex-track-handoff-context` and pushed to origin at commit
`8f97129ca66a9619cc55bdc030df13959ee2344c`.

The exact signed L1a n=1 command was invoked once. It failed immediately before
Modal launch because `cluster3/experiments/run_cluster3_modal.py` still contains
the fail-closed `grammar_mode_cp_12cell` execution guard. No retry, resume,
repair, L1b, L2, paper-scale, benchmark, profiler, billing reconciliation, or
post-run analyzer execution occurred.

No L1a output namespace, observability artifact namespace, or `mlruns/`
directory was created.

## Authorization Commit

authorization_commit: `8f97129ca66a9619cc55bdc030df13959ee2344c`
authorization_commit_subject: `Authorize L1a n1 execution`
promotion_target: `codex-track-handoff-context`
remote_push_status: `PUSHED`
remote_ref_after_push: `origin/codex-track-handoff-context`
remote_ref_sha: `8f97129ca66a9619cc55bdc030df13959ee2344c`

## Execution Code Target Commit

execution_code_target_commit:
`31a097e3231e5b73a1402a26d18c660ba2f53d84`

runtime_drift_check:
`git diff --name-only 31a097e3231e5b73a1402a26d18c660ba2f53d84..HEAD -- cluster1 cluster2 cluster3 shared`

runtime_drift_result: `PASS_EMPTY_OUTPUT`

## Approval Record Commit

approval_record_commit:
`8f97129ca66a9619cc55bdc030df13959ee2344c`

approval_record_commit_policy:
The approval record is the final execution authorization commit promoted and
pushed before the attempted L1a run.

## Exact Command Run

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

invocation_count: 1
retry_count: 0
resume_count: 0

## Start/End Timestamps

start_timestamp_utc: `2026-06-06T08:02:30Z`
end_timestamp_utc: `2026-06-06T08:03:09Z`

## Modal/GPU Metadata

modal_app_name: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
gpu_type_used: `NONE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
modal_run_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
modal_function_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`
container_id: `NOT_AVAILABLE_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`

## Fallback Provenance Metadata Captured

fallback_provenance_policy:
`WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY`

captured_during_run:
`NO_RUNTIME_PROVENANCE_CAPTURED_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`

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

## Stop-Limit Compliance

max_rows: 12
max_generation_attempts: 72
max_correctness_calls: 72
max_wall_clock: 4h
rows_written: 0
generation_attempts_observed: 0
correctness_calls_observed: 0
wall_clock_observed: less_than_1_minute
stop_on_first_failure: `COMPLIED`
no_retry: `COMPLIED`
no_resume: `COMPLIED`

## Spend-Limit/Preflight Status

max_estimated_cost: `USD_25`
max_reconciled_billing_cost: `USD_50`
preflight_estimate_status:
`SIGNED_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED`

spend_result:
`NO_MODAL_GPU_RUN_OBSERVED_COMMAND_FAILED_BEFORE_MODAL_LAUNCH`

## Billing Reconciliation Status

billing_reconciliation_status:
`NOT_RUN_NO_MODAL_RUN_WINDOW_AVAILABLE_AFTER_PRE_LAUNCH_FAILURE`

reason:
Billing reconciliation was scoped to the post-run L1a window. The command failed
before Modal launch, so there was no signed Modal run window to reconcile.

## Post-Run Validation Results

post_run_validation_status:
`NOT_RUN_NO_L1A_ARTIFACTS_EXIST_AFTER_EXECUTION_FAILURE`

reason:
The signed post-run validation bundle requires the L1a JSONL and sidecar
artifacts. The command failed before artifact creation, so validation would only
confirm missing artifacts and was not run as a separate artifact-consuming step.

pre_execution_validation_results:

- `git diff --check`: pass
- `git status --short --branch`: clean on `codex-track-handoff-context`
- authorization scan: pass, L1a-only authorization present
- runtime drift check: pass, no runtime-code changes after execution target
- output namespace collision check: pass, target output root absent
- observability namespace collision check: pass, target artifact root absent
- dry-plan verification: pass, `cell_count=12`
- execution-plan verification: pass, `cell_count=12`

## Failure/Error

error_class: `RuntimeError`

error_message:

```text
grammar_mode_cp_12cell execution is not enabled by this local support branch; the selector remains fail-closed until a separate signed execution packet authorizes launch
```

failure_location:
`cluster3/experiments/run_cluster3_modal.py:1117`

observed_fail_closed_guard:
The runner returns local dry-plan and execution-plan payloads, then raises for
the `grammar_mode_cp_12cell` runtime path before entering the Modal execution
surface.

## No Retry/No Resume Proof

The exact signed command was invoked once. After the fail-closed runtime error,
no second invocation, retry, resume, repair, or alternate command was run.

## No L1b/L2/Paper-Scale Proof

Only the signed L1a n=1 command was invoked. No L1b, L2, paper-scale, n=5, n=20,
or report-scale command was run.

## No Performance/Profiler Proof

No profiler, benchmark, speedup, performance optimization, or timing comparison
path was run. The run failed before Modal launch.

## No Output/Mlruns Mutation Proof

Post-failure checks:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`: absent
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`: absent
- `mlruns`: absent
- `git diff --name-only -- outputs artifacts mlruns docs/preliminary_report`: empty

## Files Created

- `audits/l1a_n1_execution_run_report.md`

No output JSONL, content-hash sidecar, observability sidecar, analysis artifact,
report artifact, billing artifact, preliminary report, runtime code, dependency
file, or `mlruns/` artifact was created.

## Classification

`L1A_N1_RUN_FAILED_EXECUTION`

## Next-Step Recommendation

Open a narrow launcher-unlock branch that removes or updates only the
`grammar_mode_cp_12cell` fail-closed runtime guard under the already-signed
L1a-only authorization constraints, then re-review and explicitly authorize any
second execution attempt before running it. Do not retry or resume this failed
attempt.
