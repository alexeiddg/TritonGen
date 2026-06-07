# L2 n=20 Execution Completion Report

Date: 2026-06-07
Status: failed validation / preserved partial artifacts
Classification: L2_N20_RUN_FAILED_VALIDATION
Scope: signed L2 n=20 12-cell grammar-mode x C x P execution attempt

## Executive Summary

The signed L2 n=20 command was run exactly once after runtime-gate promotion.
The run produced output JSONL files for all 12 planned cells, but validation
failed because `task_agnostic__c_on__p_on` stopped at 8 rows instead of 20.
Total preserved rows are 228 of the required 240.

Because row validation failed, the post-run analyzer/report command was not run.
The preserved artifacts are partial evidence only and must not be used for paper
graphs, paper-scale results, paper conclusions, or analyzer/report claims.

## Final Authorization Reference

- final packet:
  `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md`
- authorization report:
  `audits/l2_n20_final_authorization_report.md`
- authorization commit:
  `bd84940 Authorize L2 n20 execution`
- authorization promotion audit:
  `2102259 Audit L2 n20 final authorization promotion`
- signed token:
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1`
- signed scope:
  `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`

## Runtime Gate Promotion Reference

- runtime-gate commit:
  `426ede8 Enable signed L2 n20 runtime gate`
- runtime-gate promotion audit:
  `4b85c24 Audit L2 n20 runtime gate promotion`
- promoted target branch:
  `codex-track-handoff-context`

The runtime gate allowed only the exact signed L2 n=20 selector/profile/path
through pre-launch validation. Wrong tokens, wrong rung token reuse, wrong `n`,
non-elementwise kernels, non-fp32 dtypes, MLflow-enabled runtime, retry/resume,
target-path collisions, row/cell mismatch, namespace mismatch, L3, profiler,
benchmark, speedup/performance paths, and other variants remained fail-closed
before execution.

## Exact Command Run

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1 --overwrite
```

This command was run once. No retry command, resume command, alternate selector,
extra dtype, extra kernel, L3 command, analyzer command, report command, or
MLflow runtime command was run.

## Start And End Timestamps

- execution start UTC:
  `2026-06-06T21:35:35Z`
- execution end UTC:
  `2026-06-07T01:16:05Z`
- observed wall clock:
  approximately 3 hours 40 minutes 30 seconds

The process did not exit cleanly after all visible cell files had appeared. It
was terminated with `SIGTERM` after an idle post-artifact cleanup hang. This is
a run-completion caveat and one reason the partial final cell must not be
treated as successful L2 evidence.

## Modal And GPU Metadata

The command used the approved `cluster3.experiments.run_cluster3_modal` launch
surface. The preserved observability sidecars report Modal context as
unavailable:

```text
modal_context_available=false
is_remote=false
gpu_type=null
app_name=null
function_call_id=null
task_id=null
region=null
```

Therefore no GPU type, Modal app id, Modal function call id, container id, image
id, region, or remote-context claim is available from the sidecars. The audit
does not infer those fields.

## Output Paths

Generated output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
```

Generated observability namespace:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
```

Generated billing artifact:

```text
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_billing_report_20260606T2100_20260607T0200_utc.redacted.jsonl
```

Analyzer/report outputs were not created:

```text
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.json
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.md
```

## Row-Count Result

Validation failed.

```text
expected_rows: 240
actual_rows: 228
expected_cells: 12
actual_cell_files: 12
expected_rows_per_cell: 20
```

Per-cell row counts:

```text
grammar_off__c_off__p_off: 20
grammar_off__c_on__p_off: 20
grammar_off__c_off__p_on: 20
grammar_off__c_on__p_on: 20
template_upper_bound__c_off__p_off: 20
template_upper_bound__c_on__p_off: 20
template_upper_bound__c_off__p_on: 20
template_upper_bound__c_on__p_on: 20
task_agnostic__c_off__p_off: 20
task_agnostic__c_on__p_off: 20
task_agnostic__c_off__p_on: 20
task_agnostic__c_on__p_on: 8
```

The incomplete cell is `task_agnostic__c_on__p_on`, which corresponds to the
task-agnostic grammar mode with C enabled and P enabled.

## 12-Cell Coverage Result

All 12 output JSONL files and all 12 output hash sidecars exist. Coverage is
not successful because one cell is partial.

Observed grammar-mode row counts:

```text
grammar_off: 80
template_upper_bound: 80
task_agnostic: 68
```

Observed condition row counts:

```text
none: 20
C: 20
P: 20
C+P: 20
G: 40
G+C: 40
G+P: 40
G+C+P: 28
```

## Post-Run Validation Result

Read-only validation checks confirmed:

- 12 output JSONL files exist.
- 12 output hash sidecars exist.
- 12 observability event JSONL files exist.
- 12 observability event hash sidecars exist.
- 11 observability summary files exist.
- the missing summary is `task_agnostic__c_on__p_on`.
- `mlruns/` is absent.
- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.json`
  does not exist.
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_factorial.md`
  does not exist.

C/P loop indicators were present in the row payloads:

```text
c_loop_fired false: 223
c_loop_fired true: 5
p_repair_attempted false: 216
p_repair_attempted true: 12
p_repair_attempt_count_positive: 12
```

These counts are descriptive only for the partial run and are not reportable
paper-scale results.

## Analyzer And Report Result

The analyzer/report command was not run because validation failed before the
240-row requirement was satisfied.

No analysis JSON or markdown report was created for L2 n=20. This preserves the
signed packet boundary: analyzer/report refresh is allowed only after valid L2
outputs exist.

## Billing Reconciliation Result

The signed post-run billing reconciliation was run for the narrow observed UTC
hour window:

```bash
.venv/bin/python -m modal billing report --start 2026-06-06T21:00:00Z --end 2026-06-07T02:00:00Z --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

Raw billing output was written only to:

```text
/private/tmp/tritongen_l2_n20_billing_raw_20260606T2100_20260607T0200.json
```

Raw billing output is not committed.

The retained redacted billing artifact is:

```text
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_billing_report_20260606T2100_20260607T0200_utc.redacted.jsonl
```

Billing reconciliation status:

```text
raw_record_count: 5
redacted_record_count: 1
total_redacted_cost_usd: 9.4437485
attribution_method: time_window
attribution_confidence: low
redacted_report_sha256: f2ab6937f9ff2413338dfe1e44368401b39fe2ec00cf0808d8cdb2f023637c6e
```

Modal returned no usable run tags in the retained redacted record, so this is
UTC-window-only workspace billing evidence. It is not clean tag-attributed
per-run billing proof.

## Stop-Limit Compliance

- no retry was run.
- no resume was run.
- no L3 command was run.
- no extra dtype was run.
- no extra kernel class was run.
- no MLflow runtime write was enabled.
- max rows were not exceeded.
- wall clock remained under the signed 24-hour limit.
- reconciled UTC-window cost is below the signed USD 250 cap, with low
  attribution confidence.

The run failed the row-count stop condition because it preserved only 228 of
240 expected rows.

## Spend-Limit Status

The redacted billing artifact records `total_cost=9.4437485` USD for the narrow
UTC window. This is below the signed reconciliation cap of USD 250. Because
Modal billing tags were absent, the spend status is attribution-limited and
must not be reported as exact per-run cost.

## No Retry Or Resume Proof

The execution command was invoked once with `--overwrite`. No command with a
resume flag, retry flag, alternate selector, rerun path, or second L2 invocation
was run. The partial output was preserved exactly as written.

## No L3, Extra Kernel, Or Extra Dtype Proof

The only execution command used:

```text
condition=grammar_mode_cp_12cell
scale_tier=paper
n=20
kernel_class=elementwise
dtypes=fp32
```

No L3, non-elementwise kernel, or non-fp32 dtype output namespace was created.

## No Performance Claim Proof

No benchmark command, speedup analysis, cost-per-success analysis, throughput
claim, latency claim, profiler result, or economic claim was created or
committed.

Scope caveat: a one-second macOS `sample` diagnostic was run against the local
Python process after visible artifacts had appeared and the process was idle in
cleanup. It was used only to decide whether the process was hung; no profiler
artifact, timing result, performance conclusion, speedup claim, or benchmark
evidence is retained or claimed.

## Files Created Or Modified

Preserved result artifacts:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/`
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/`
- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20_billing_report_20260606T2100_20260607T0200_utc.redacted.jsonl`

Audit and handoff updates:

- `audits/l2_n20_execution_completion_report.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`

No runtime code, dependency file, lockfile, `mlruns/`, or
`docs/preliminary_report/` file was changed by this completion audit.

## Remaining Caveats

- The L2 n=20 run failed validation at 228 of 240 rows.
- `task_agnostic__c_on__p_on` is partial at 8 of 20 rows.
- The process was terminated after an idle cleanup hang and did not exit
  cleanly.
- One observability summary is missing for the partial final cell.
- Observability Modal/GPU context is unavailable.
- Some observability summary provenance labels record a docs-only side branch
  (`codex/fireworks-api-modal-implementation-plan`, commit `2155630`) while the
  runtime-gate trunk was otherwise promoted at `4b85c24`. The side-branch diff
  from the promoted runtime gate was handoff/planning docs only, but this remains
  a provenance caveat.
- Billing is UTC-window-only and low-confidence because Modal returned no usable
  run tags.
- Analyzer/report artifacts were intentionally not generated.
- Paper-scale graphs, reports, results, and conclusions remain blocked.

## Classification

`L2_N20_RUN_FAILED_VALIDATION`

## Next-Step Recommendation

Do not retry or resume under the completed packet. The next branch should be an
audit/fix-planning branch that inspects the partial
`task_agnostic__c_on__p_on` cell, the idle cleanup hang, and the provenance
metadata split. Any retry, resume, overwrite, or full rerun requires a new
signed packet that explicitly authorizes the chosen recovery shape and billing
scope.
