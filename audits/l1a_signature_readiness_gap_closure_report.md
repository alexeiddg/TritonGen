# L1a Signature Readiness Gap Closure Report

report_version: `1.0.0`
date: 2026-06-06
branch: `codex/l1a-signature-readiness-gap-closure`
baseline_commit: `59fa0d6 Audit L1a approval packet promotion`
packet: `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
AUTHORIZES_EXECUTION: NO

## Executive Summary

This docs-only package narrows the remaining L1a signature-readiness gaps
without converting the packet into an execution packet. The packet now points
to the promoted handoff baseline `59fa0d6`, records a deterministic
observability run-id convention, records the repo-local Modal app name and
image-source files, attaches a synthetic local preflight-estimator placeholder
marked `NOT_SIGNABLE`, proposes unsigned stop/spend limits, documents a
plan-only billing reconciliation path, and lists exact local post-run
validation command surfaces where the repo exposes them.

Execution remains blocked because no executable 12-cell selector exists in the
current runner and no user signature has approved command(s), output mutation,
spend, stop limits, billing collection, or validation writes.

## Files Changed

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/l1a_signature_readiness_gap_closure_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

No runtime code, output, artifact, MLflow, dependency, lockfile, or preliminary
report path is in scope.

## Unresolved Field Inventory Before Patch

The pre-patch packet still carried these key unresolved fields:

- exact execution command:
  `REQUIRED_BEFORE_SIGNATURE_current_12cell_selector_is_dry_plan_only`;
- exact observability run id:
  `REQUIRED_BEFORE_SIGNATURE_exact_run_id`;
- numeric generation-attempt, wall-clock, estimated-cost, and reconciled
  billing limits:
  `REQUIRED_BEFORE_SIGNATURE`;
- advisory preflight estimate:
  `REQUIRED_BEFORE_SIGNATURE_advisory_only_pricing_must_be_reverified`;
- Modal app name and image digest:
  `REQUIRED_BEFORE_SIGNATURE`;
- post-run schema, content-hash, observability, grammar-mode, and billing
  validation commands:
  `REQUIRED_BEFORE_SIGNATURE`;
- signature block fields:
  signer, signed time, approval scope, exact execution command, numeric limits,
  estimate attachment, billing plan, and validation bundle.

## Fields Resolved

- Target baseline was refreshed from the older execution-planning baseline
  `c256af5` to the promoted handoff baseline `59fa0d6`.
- Observability run-id convention was defined as
  `full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__target_<short_commit>__signed_<YYYYMMDDTHHMMSSZ>`.
- Per-cell observability join-key convention was defined as
  `<run_id>__<condition_id>`, with the current dry-plan prefix traced to
  `cluster3/planning/grammar_mode_matrix.py`.
- Modal app name was resolved from `shared/modal_harness/app.py` as
  `tritongen-gpu-harness`.
- Modal image source files were identified as
  `shared/modal_harness/images.py`, with `llm_generation_image` and
  `triton_compile_image`.
- Exact local post-run schema, content-hash sidecar, observability sidecar,
  grammar-mode consistency, and analyzer/report command surfaces were listed
  for future signed use after artifacts exist.
- Billing reconciliation was converted from a blank placeholder into a
  plan-only requirement: actual reconciled billing is authoritative for actual
  spend, but no billing query is authorized now.

## Fields Still REQUIRED_BEFORE_SIGNATURE

- `exact_intended_execution_command` remains
  `REQUIRED_BEFORE_SIGNATURE_EXECUTABLE_SELECTOR_MISSING` because
  `grammar_mode_cp_12cell` is dry-plan-only.
- `modal_image_digest` remains
  `REQUIRED_BEFORE_SIGNATURE_REMOTE_IMAGE_DIGEST_UNKNOWN`; remote Modal/image
  state was not queried.
- Signable preflight estimate remains required; the attached estimator snapshot
  is synthetic and `NOT_SIGNABLE`.
- Human-approved numeric stop/spend limits remain required; the current limits
  are `PROPOSED_NOT_SIGNED`.
- Billing-query authorization, signed billing time window, and redacted report
  path remain required before billing reconciliation can be executed.
- Human signature fields remain unsigned, including signer, signed timestamp,
  target commit confirmation, spend cap, stop limits, pricing recheck status,
  estimate attachment status, and authorization statement.

## Proposed Unsigned Stop/Spend Limits

```text
max_rows: 12
max_generation_attempts: PROPOSED_NOT_SIGNED_72_total_initial_plus_C_and_P_repair_attempt_ceiling
max_repair_attempts_per_row: PROPOSED_NOT_SIGNED_P_5_when_enabled_C_5_when_enabled_0_otherwise
max_correctness_calls: PROPOSED_NOT_SIGNED_72_total_attempt_ceiling
max_wall_clock: PROPOSED_NOT_SIGNED_4_hours
max_estimated_cost: PROPOSED_NOT_SIGNED_USD_25_requires_official_pricing_reverification
max_reconciled_billing_cost: PROPOSED_NOT_SIGNED_USD_50_billing_reconciliation_authoritative
max_modal_invocations: PROPOSED_NOT_SIGNED_REQUIRES_EXECUTION_SHAPE_SELECTION
stop_on_first_infrastructure_failure: PROPOSED_NOT_SIGNED_yes
retry_policy: PROPOSED_NOT_SIGNED_no_retry_no_resume_unless_explicitly_signed
```

These values are candidates for human approval only. They do not authorize
execution or spend.

## Preflight Estimate Status

Status: `NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER_ATTACHED`.

The pure local estimator function was invoked with synthetic pricing and timing
inputs. It performed no Modal calls, billing queries, output writes, artifact
writes, or MLflow writes.

Observed placeholder output:

```text
total_planned_rows: 12
recommended_shape_name: bounded_fanout_across_cells_seeds
estimated_parallel_wall_clock_seconds: 59.0
estimated_gpu_seconds: 221.0
estimated_cost: 2.21
warning_flags: advisory_only_not_experimental_evidence, pricing_reverification_required, stage_timing_inputs_estimated_not_measured
```

This placeholder is not signable. A future signature must attach an advisory
estimate using approved timing inputs and Modal pricing re-verified on the
approval date.

## Executable Command Status

Status: `REQUIRED_BEFORE_SIGNATURE_EXECUTABLE_SELECTOR_MISSING`.

Repo inspection confirms the current `grammar_mode_cp_12cell` selector is
dry-plan-only. `cluster3/experiments/run_cluster3_modal.py` rejects that
selector unless `--dry-plan` is supplied, and `--grammar-mode-cell` is also
dry-plan-only. No execution command was inferred from the dry-plan selector.

## Validation Bundle Status

Status: `PROPOSED_NOT_SIGNED_REQUIRES_POST_RUN_ARTIFACTS`.

The packet now lists exact local command surfaces for:

- schema plus row-count validation for 12 rows;
- content-hash sidecar validation using `cluster3.results.logger`;
- observability event/summary/hash sidecar validation using
  `shared.observability.logger` and schema models;
- grammar-mode consistency validation;
- analyzer/report generation through `shared.analysis.factorial`.

The analyzer/report command writes planned post-run artifacts and must not be
run unless a future signed packet authorizes those writes.

## Billing Reconciliation Status

Status: `PLAN_ONLY_NO_BILLING_QUERY_AUTHORIZED`.

The packet now states that post-run reconciled billing is authoritative for
actual spend. A future billing reconciliation must have a signed time window,
experiment id, run id, redacted report handling policy, redacted report hash,
and billing-query authorization. No billing API/CLI call was run in this phase.

## Authorization Status

```text
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
```

No signature was added.

## No-Execution Proof

Actions performed:

- local git status and source inspection;
- local source searches with `rg`/`sed`;
- one pure local estimator function call through `.venv/bin/python -c ...`.

Actions not performed:

- no Modal invocation;
- no GPU job;
- no generation;
- no experiment run;
- no benchmark or profiler;
- no analyzer/report refresh;
- no billing query;
- no MLflow tracking execution.

## No-Output/mlruns Mutation Proof

No file under `outputs/`, `artifacts/`, `mlruns/`,
`docs/preliminary_report/`, dependency files, lockfiles, or runtime code was
modified.

## Validation Run

Validation commands run locally:

```text
git diff --check
git status --short --branch
git diff --name-only -- cluster1 cluster2 cluster3 shared
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
positive authorization scan from the supplied prompt over packet, audit, and handoff docs
rg -n "AUTHORIZES_EXECUTION: NO|REQUIRED_BEFORE_SIGNATURE|PROPOSED_NOT_SIGNED|NOT_SIGNABLE|EXECUTABLE_SELECTOR_MISSING|billing reconciliation|preflight|numeric stop|spend cap|signature|observability run id" docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md audits/l1a_signature_readiness_gap_closure_report.md
git diff -- docs audits | rg -n "speedup achieved|cost reduced|runtime reduced|throughput improved|performance result|benchmark result|Modal optimized|optimization complete|billing reconciled"
```

Results:

- `git diff --check`: passed with empty output.
- runtime-code scan over `cluster1`, `cluster2`, `cluster3`, and `shared`:
  empty output.
- protected mutation scan over `outputs`, `artifacts`, `mlruns`,
  `docs/preliminary_report`, dependencies, and lockfiles: empty output.
- positive authorization scan: no matches.
- required status scan: required non-authorizing concepts present.
- evidence-boundary scan: no matches.
- `git status --short --branch` shows only the five allowed package paths:
  packet, audit, and three handoff docs.

## Classification

`L1A_SIGNATURE_READINESS_GAP_CLOSURE_COMPLETE`

The packet is closer to signable, but it remains non-authorizing and blocked by
the missing executable selector, unsigned proposed limits, unsigned signable
estimate, and unsigned human approval.

## Next-Step Recommendation

Review and commit this docs-only signature-readiness gap closure branch. The
next technical branch, if approved later, should be narrowly scoped to making
the 12-cell selector executable or supplying a signed per-cell executable
command bundle. It should still avoid execution until a separate human signature
changes `AUTHORIZES_EXECUTION` under an approved packet.
