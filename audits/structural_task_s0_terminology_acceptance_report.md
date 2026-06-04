# Structural/Task S0 Terminology Acceptance Report

- Version: 1.0.0
- Date: 2026-06-04
- Branch: `codex/structural-task-s0-terminology`
- Classification: `S0_TERMINOLOGY_ACCEPTANCE_COMPLETE`
- Scope: docs/audit only

## Executive Summary

S0 accepts the existing structural/task outcome terminology and closes Gate G2
for analyzer/report metadata implementation planning. `docs/14_structural_vs_task_outcome_reporting_plan.md`
is the vocabulary and planning source. `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
is the executable S0-S3 implementation contract.

S1 is unblocked only for additive analyzer metadata after taking the
`analyzer_metric_registry` serialized-surface lease. S1 must preserve the
existing analyzer output shape and may add only metadata/diagnostic fields such
as `metadata.outcome_families`, `metadata.metric_registry`,
`metadata.registry_provenance`, `diagnostics.level_reach_rates`,
`diagnostics.feedback_activation`, and `diagnostics.metric_availability`.
Existing consumers reading prior keys must keep working.

This S0 pass authorizes no analyzer code change, no report-builder change, no
output mutation, no raw JSONL rewrite, no Modal/GPU/generation run, no
dependency or lockfile change, and no performance, timing, profiler, speedup,
n=5, n=20, paper-scale, P-lift, or correctness-improvement claim.

## Docs Inspected

- `docs/14_structural_vs_task_outcome_reporting_plan.md`
- `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
- `docs/07_analysis_and_statistics.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/15_experiment_change_orchestration_contract.md`

## Terminology Scan Results

Reviewed terminology in the S0 source docs for ambiguous reporting language:
bare `pass`, bare `pass@k`, `format success`, unlabeled `success rate`,
compile-only correctness claims, functional-as-structural wording,
benchmarkable/performance mixing, `correct` used for compile-only claims, and
paper-scale language attached to unsupported execution.

Accepted terminology:

- structural/code-surface quality: syntax, grammar, harness surface,
  compile/launch, and other Level 0/Level 1 gates.
- task/functional quality: Level 2 numerical correctness.
- `compile_success`: structural/code-surface, secondary or diagnostic.
- `functional_success`: task/functional, primary for current C comparisons.
- Cluster 1 `functional_success=False`: false/unproven because Level 2 was not
  run, not measured Level 2 failure.
- C activation: F2/Level 2 eligible only.
- P activation: F1_COMPILE eligible only.
- `syntax_valid_rate`: planned-deferred/unavailable for mixed current schemas
  unless compatible explicit syntax evidence exists.
- Performance/timing/speedup/benchmarkable claims: future-only unless a later
  Level 4 contract authorizes execution and reporting.

No S0 doc contradiction remains after the audit-report exception was added to
`docs/17_structural_task_analyzer_metadata_implementation_spec.md`.

## Wording Changes Made

- Clarified in `docs/14_structural_vs_task_outcome_reporting_plan.md` that the
  file defines vocabulary and reporting intent, while
  `docs/17_structural_task_analyzer_metadata_implementation_spec.md` is the
  executable S0-S3 implementation contract.
- Bumped `docs/17_structural_task_analyzer_metadata_implementation_spec.md` to
  v0.1.3 and added a narrow S0 exception for this named acceptance audit report.
- Updated `docs/handoff/experiment_change_orchestration_state.md` to mark G2
  satisfied and record the S1/S2/S3 boundaries.
- Updated `docs/handoff/document_version_registry.md` to register this S0
  acceptance pass and touched document versions.

## G2/S0 Gate Status

Gate G2 is satisfied.

Accepted gate facts:

- structural/code-surface and task/functional terminology is accepted.
- `compile_success` is structural/code-surface, not functional correctness.
- `functional_success` remains task/functional.
- Cluster 1 Level 2 status is false/unproven, not measured Level 2 failure.
- Cluster 2 C activation remains F2 eligible only.
- `docs/17_structural_task_analyzer_metadata_implementation_spec.md` is the
  executable implementation authority.

## S1 Unblock Scope

S1 may start only after taking the `analyzer_metric_registry` serialized-surface
lease. The allowed S1 implementation target is additive analyzer metadata in
`shared/analysis/factorial.py` plus compatibility tests in
`shared/tests/test_factorial_analysis.py`, following docs/17.

Required S1 additions include metadata/diagnostic fields such as:

- `metadata.outcome_families`
- `metadata.metric_registry`
- `metadata.registry_provenance`
- `diagnostics.level_reach_rates`
- `diagnostics.feedback_activation`
- `diagnostics.metric_availability`

S1 must preserve existing top-level analyzer keys and legacy consumer behavior.
It must not mutate `outputs/`, raw JSONL artifacts, result-row schemas, report
builder outputs, dependencies, lockfiles, Modal/GPU/generation behavior, or
performance/timing/profiler surfaces.

## Remaining S1 Blockers

G2 is no longer a blocker. Remaining S1 prerequisites:

- take the `analyzer_metric_registry` serialized-surface lease;
- implement only docs/17 additive metadata requirements;
- pass analyzer compatibility, metric-registry validator, JSON-safe metadata,
  legacy-key, partial/empty design, alias-collision, status/value consistency,
  feedback-activation, level-reach, and golden compatibility tests.

## S2/S3 Blocked State

S2 remains blocked until S1 metadata lands, unless a later packet explicitly
scopes docs-prose-only or legacy-fallback-only work. S2 must not refresh report
data from a new analyzer output unless S3 is also approved.

S3 remains blocked pending a separate output-mutation approval packet. S3 must
never rewrite raw Cluster 1, Cluster 2, or Cluster 3 JSONL artifacts.

## Forbidden Scope Scan

Expected forbidden-scope diff: empty for analyzer, tests, report builder,
clusters, outputs, artifacts, dependencies, lockfiles, and MLflow runtime state.

Expected positive execution authorization scan: empty for Modal/GPU/generation,
output mutation, paper-scale, and performance execution authorization flags.

## Validation Commands

Run in `/Users/alexeidelgado/Desktop/TritonGen`:

```text
git diff --check
git status --short --branch
git diff --name-only -- shared/analysis shared/tests docs/preliminary_report cluster1 cluster2 cluster3 outputs artifacts pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
positive execution authorization scan from the S0 packet over handoff docs, audits, docs/14, docs/17, and docs/07
ambiguous terminology scan from the S0 packet over docs/14, docs/17, docs/07, live state, and this audit
```

Validation results:

- `git diff --check`: passed.
- `git status --short --branch`: branch is
  `codex/structural-task-s0-terminology`; changed files are docs/audit only.
- forbidden protected-scope diff: empty for analyzer, tests, report builder,
  clusters, outputs, artifacts, dependencies, lockfiles, and MLflow runtime
  state.
- broad positive execution authorization scan: reviewed. Hits are the
  pre-existing O6b signed smoke audit and command-pattern text, not S0
  authorization. No S0 touched file grants Modal/GPU/generation/output
  mutation/paper-scale/performance execution.
- ambiguous terminology scan: reviewed. Hits are gate-qualified, caveated, or
  explicitly listed as terms under review. No touched text uses compile success
  as task/functional correctness or treats Cluster 1 false/unproven as measured
  Level 2 failure.

## Classification

`S0_TERMINOLOGY_ACCEPTANCE_COMPLETE`

## Next-Step Recommendation

Start S1 on `codex/analyzer-metric-registry` after recording the
`analyzer_metric_registry` lease. Implement only the additive analyzer metadata
contract from docs/17, with compatibility tests proving existing analyzer
consumers still work.
