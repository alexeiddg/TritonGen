# Full Pipeline Launch Packet v1 Report

- Version: 1.0.1
- Date: 2026-06-05
- Branch: `codex/full-pipeline-launch-packet-v1`
- Baseline: `7d9ac22 Add C3 n20 metric family packet`
- Scope: full-pipeline launch packet planning only / no execution authorized
- Classification: `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_PASS_COMMIT_ALLOWED`

## Executive Summary

This docs-only package creates
`docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md` as a
draft/non-authorizing launch packet for a future fresh G/C/P factorial after
MLflow tracking, observability sidecars, `agentic_transcript_v1` repair memory,
and structural/task reporting updates.

No Modal, GPU, generation, experiment execution, benchmark, profiler,
paper-scale work, output mutation, raw JSONL rewrite, analyzer output refresh,
report artifact refresh, MLflow runtime write, billing query, dependency change,
or lockfile change was performed or authorized.

Packet review passed locally under
`FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_PASS_COMMIT_ALLOWED`. The packet remains
non-authorizing and does not launch L1 smoke/dev, L2 n20, paper-scale, MLflow
runtime, billing, benchmark, profiler, timing, or speedup work.

## Design Selected And Rationale

Selected design: fresh 8-cell G/C/P factorial:

- `none`
- `G`
- `C`
- `P`
- `G+C`
- `G+P`
- `C+P`
- `G+C+P`

The packet rejects a primary 4-cell P-extension as the default design because it
would likely require pairing new `agentic_transcript_v1` P-containing rows with
historical no-P controls. That can be useful diagnostically, but it is weaker
for primary paper claims unless repair-history policy is explicitly modeled as a
cohort/factor with a caveat.

## MLflow Architecture

MLflow is specified as a post-hoc index/dashboard over repo artifacts. It is not
the source of truth and is not authoritative.

Authoritative artifacts remain:

- JSONL result rows;
- content-hash sidecars;
- observability event, summary, and hash sidecars;
- analyzer JSON;
- report files;
- billing reconciliation artifacts if later approved and available.

The packet records that `TRITONGEN_MLFLOW=1` plus importable `mlflow` supports
the current optional tracking seam, but is not sufficient for broad artifact
indexing unless a post-hoc importer exists. Future work item M0 is to implement
or script that importer before paper-scale.

## Observability Policy

L1 smoke/dev should use `best_effort` by default unless the approval packet
selects `required`. L2 paper-scale should use `required` unless the approval
packet explicitly accepts observability unavailability.

The packet reserves:

```text
artifacts/observability/full_pipeline_gcp_factorial_v1/smoke/
artifacts/observability/full_pipeline_gcp_factorial_v1/n20/
```

It requires explicit `observability_experiment_id`,
`observability_run_id`, sidecar paths, join keys, failure behavior, and hash
sidecar success before any future execution.

## Repair Memory Policy

The packet preserves the hard repair-memory boundary:

- `agentic_transcript_v1` remains opt-in;
- `last_attempt_only_v1` remains historical/default unless explicitly selected;
- `none` and `G` have no repair-loop memory activation;
- P repairs only F1_COMPILE;
- C repairs only F2;
- F1_RUNTIME remains terminal;
- initial-F2 and post-P F2 paths must remain distinct;
- rows/artifacts must label `repair_history_policy` where supported;
- analyzer/reporting must group or quarantine mixed policies before headline
  comparisons.

## Structural/Task Policy

The packet carries forward S4 metric-family guidance:

- `structural_code_surface` for syntax, grammar, harness, compile, and
  gate-qualified compile pass@k;
- `task_functional` for numerical correctness, repair success, eval-set success,
  and gate-qualified correctness pass@k;
- `mixed_diagnostic` for terminal failure distribution, `feedback_activation`,
  `level_reach_rates`, and `metric_availability`;
- `benchmarkable_performance` for future-only benchmarkable pass@k, timing,
  speedup, profiler, and performance metrics.

It explicitly names `level2_functional_success_rate` as the primary task metric
when prerequisites pass and `level1_compile_success_rate` as a structural
secondary/diagnostic metric.

## Output Namespace

The packet reserves fresh namespaces:

```text
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/
outputs/cluster3/full_pipeline_gcp_factorial_v1/n20/
artifacts/observability/full_pipeline_gcp_factorial_v1/smoke/
artifacts/observability/full_pipeline_gcp_factorial_v1/n20/
artifacts/analysis/full_pipeline_gcp_factorial_v1/
artifacts/reports/full_pipeline_gcp_factorial_v1/
artifacts/mlflow_index/full_pipeline_gcp_factorial_v1/
artifacts/billing/full_pipeline_gcp_factorial_v1/
```

No overwrite is allowed. If a target path exists, a future execution packet must
stop unless explicit resume, append, overwrite, or archive policy is approved.

## Old-Run Comparability

Old `last_attempt_only_v1` outputs are historical baselines or diagnostics only.
They should not be mixed with new `agentic_transcript_v1` C/P cells for primary
paper claims unless the future analysis explicitly models repair-history policy
as a separate factor/cohort and records the limitation.

The existing Phase 14e four-cell n=5 matrix remains development-scale condition
coverage with zero P attempts and zero C fires. It does not unblock n=20 or
paper-scale claims.

## Smoke/Dev Gate

Recommended next executable gate is L1 smoke/dev:

- future authorization required;
- `n=1` or small explicitly bounded n;
- validates command path, output namespace, sidecars, analyzer compatibility,
  MLflow post-hoc indexing, no-overwrite protections, and repair-history policy
  labels;
- not paper evidence.

## Paper-Scale Gate

L2 paper-scale is blocked until:

- L1 passes;
- Gate G8 is satisfied;
- exact n=20 condition matrix is approved;
- exact Modal command, output paths, sidecar paths, analyzer/report commands,
  MLflow import/indexing commands, cost/spend limits, model revisions, and claim
  boundaries are recorded;
- user explicitly approves execution.

## Unresolved Launch Fields

The future approval packet must still provide:

- exact command;
- exact conditions to execute;
- exact n;
- exact model and model revision;
- tokenizer revision if applicable;
- decoding config;
- seed policy;
- problem IDs;
- dtype/shape lock;
- output paths;
- observability IDs and paths;
- repair-history CLI/config;
- max generation and repair attempts;
- Modal budget and wall-clock limit;
- billing policy or unavailable status;
- analyzer/report commands;
- MLflow post-hoc import command.

## No-Execution Proof

This package did not run Modal, GPU jobs, generation, experiments, benchmarks,
profilers, paper-scale work, billing queries, or MLflow runtime commands.

Authorization state remains:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
AUTHORIZES_EXECUTION: NO
```

## No-Output/MLflow Mutation Proof

The intended changed files are docs/audit/handoff only:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
- `audits/full_pipeline_launch_packet_v1_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

Protected paths are not in scope:

- `outputs/`
- `artifacts/`
- `mlruns/`
- `docs/preliminary_report/`
- `shared/tracking/`
- `shared/analysis/`
- `shared/tests/`
- `cluster1/`
- `cluster2/`
- `cluster3/`
- `shared/modal_harness/`
- dependency and lock files

## Validation Commands

Required validation:

```bash
git diff --check
git status --short --branch
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report shared/tracking shared/analysis shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
rg -n "<positive execution authorization tokens from the launch prompt>" docs audits .contracts --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
rg -n "<source-of-truth and replacement-claim patterns from the launch prompt>" docs audits .contracts --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
rg -n "full_pipeline_gcp_factorial_v1|no overwrite|overwrite|append|resume|outputs/cluster3|artifacts/observability|artifacts/mlflow_index|artifacts/billing" docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md audits/full_pipeline_launch_packet_v1_report.md docs/handoff
rg -n "agentic_transcript_v1|last_attempt_only_v1|repair_history_policy|P repairs only F1_COMPILE|C repairs only F2|F1_RUNTIME remains terminal|initial-F2|post-P F2" docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md audits/full_pipeline_launch_packet_v1_report.md docs/handoff
rg -n "structural_code_surface|task_functional|mixed_diagnostic|planned_deferred|future_only|benchmarkable_performance|level2_functional_success_rate|level1_compile_success_rate|feedback_activation|level_reach_rates|metric_availability" docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md audits/full_pipeline_launch_packet_v1_report.md docs/handoff
```

Results:

- `git diff --check`: pass.
- `git status --short --branch`: branch
  `codex/full-pipeline-launch-packet-v1` with only the packet/audit/handoff
  docs changed.
- Forbidden protected-path diff scan: empty output.
- Positive execution-authorization scan: empty output, exit code 1 for no
  matches.
- Source-of-truth scan: hits are existing caveats/prohibitions or explicit
  statements that MLflow is not authoritative and does not replace JSONL or
  analyzer evidence.
- Fresh namespace scan: required output, observability, MLflow-index, billing,
  no-overwrite, resume, append, and archive policy hits are present.
- Repair-memory scan: required `agentic_transcript_v1`,
  `last_attempt_only_v1`, `repair_history_policy`, C/P eligibility, terminal
  F1_RUNTIME, initial-F2, and post-P F2 hits are present.
- Metric-family scan: required structural/task, mixed diagnostic,
  planned-deferred, future-only, benchmarkable/performance, primary metric, and
  diagnostic metric hits are present.
- No Modal, GPU, generation, experiment, benchmark, profiler, billing, MLflow
  runtime, analyzer/report refresh, output mutation, dependency, lockfile, n=5,
  n=20, or paper-scale command was run.

## Classification

Review classification after validation:

`FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_PASS_COMMIT_ALLOWED`

Blocking classifications remain available if validation finds scope mutation,
authorization leakage, design ambiguity, or source-of-truth violations:

- `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_PATCH_REQUIRED`
- `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_BLOCKED_DESIGN_AMBIGUITY`
- `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_BLOCKED_SCOPE_VIOLATION`
- `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_BLOCKED_AUTHORIZATION_LEAK`
- `FULL_PIPELINE_LAUNCH_PACKET_V1_REVIEW_BLOCKED_SOURCE_OF_TRUTH_VIOLATION`

## Next-Step Recommendation

Commit the reviewed packet branch. Do not launch L1 smoke/dev from this packet.
If the packet is later accepted, prepare a separate L1 smoke/dev approval packet
with exact command, paths, model revisions, stop/spend limits, observability
IDs, repair-history config, analyzer/report validation, and MLflow post-hoc
indexing proof. Do not proceed to n=20 or paper-scale until L1 passes and a new
approval satisfies Gate G8.
