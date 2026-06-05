# Structural/Task S4 Experiment Integration Report

- Version: 1.0.0
- Date: 2026-06-05
- Branch: `codex/structural-task-s4-experiment-integration`
- Baseline: `80086f9 Audit structural task S0-S3 promotion`
- Scope: docs/planning-only future experiment integration guidance
- Classification: `S4_EXPERIMENT_INTEGRATION_COMPLETE_DOCS_ONLY`

## Executive Summary

S4 updates future experiment planning guidance so future packets declare how
metrics map to structural/code-surface, task/functional, mixed diagnostic,
planned-deferred, future-only, and benchmarkable/performance categories before
any new evidence, output mutation, report refresh, or paper-scale claim is
approved.

This branch does not create new scientific evidence. It does not run Modal,
GPU, generation, experiments, benchmarks, profilers, timing, or speedup work. It
does not mutate raw JSONL, `outputs/`, `artifacts/`, analyzer output, generated
report assets, result schemas, dependencies, lockfiles, analyzer code, report
builder code, or runner code.

## Docs Inspected

- `docs/15_experiment_change_orchestration_contract.md`
- `docs/14_structural_vs_task_outcome_reporting_plan.md`
- `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
- `docs/07_analysis_and_statistics.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Planning Changes Made

- Added S4 as a docs/planning-only structural/task work package in
  `docs/15_experiment_change_orchestration_contract.md`.
- Added future experiment metric-family declaration guidance to launch packets,
  run approval packets, and paper-readiness packets.
- Updated Gate G8 so future paper-scale readiness requires metric-family
  declarations compatible with S1/S2 `metric_registry` metadata or an explicit
  legacy fallback.
- Updated the Stream S plan and merge order so S4 guidance precedes optional
  future run branches.
- Added a narrow S4 note to
  `docs/17_structural_task_analyzer_metadata_implementation_spec.md`.
- Reconciled the live state and registry to record the S4 active branch and
  validation requirements.
- Updated the agentic hub so future experiment packet agents route through
  S0-S4 structural/task guidance.

## Future Experiment Packet Fields Added

Future packets must declare metric-family entries with:

```text
metric_name
outcome_family
level_gate
metric_gate
reportability
current_status
evidence_source
denominator_policy
claim_boundary
```

Future packets must also include:

```text
condition matrix
primary response variable
secondary response variables
diagnostic response variables
denominator policy
attempt-collapse policy
gate eligibility policy
feedback activation policy
metric_registry compatibility expectation
planned/future metric handling
output mutation authorization status
paper-scale claim authorization status
performance sidecar authorization status
```

## Contribution-Attribution Guidance

S4 guidance requires future experiment packets to ask:

- Did a condition improve structural/code-surface quality?
- Did it improve task/functional correctness?
- Did it only improve gate reach, denominator movement, or feedback activation?
- Did the feedback loop activate on the intended eligible set?
- Did the condition fail before reaching Level 2, or reach Level 2 and fail?
- Are performance, timing, speedup, profiler, and benchmark values separated
  into benchmarkable/performance sidecars?

The contract states that this enables attribution by metric family and gate but
does not by itself prove causality. Causal claims still require compatible
factorial design, fixed budgets, compatible denominators, same shapes, dtypes,
and devices, preregistered metrics, and a signed packet that authorizes the
claim scope.

## Fail-Closed Rules

Future report or analyzer consumers must fail closed, or mark the affected
metric diagnostic-only, when:

- unknown `metric_registry` major schema is encountered;
- `outcome_family` is missing;
- `reportability` is missing;
- `current_status` or `reportability` conflicts with computed values;
- `planned_deferred` or `future_only` metrics are presented as current;
- compile-only evidence is presented as task/functional correctness;
- benchmarkable/performance claims are requested without an approved
  performance sidecar evidence source.

## No-Execution Proof

S4 changed only docs and an audit report. It did not invoke Modal, GPU,
generation, experiments, benchmarks, profilers, timing, speedup, billing,
external APIs, package installation, dependency downloads, or model/tokenizer
downloads.

## No-Output-Refresh Proof

S4 did not run the analyzer, did not run the preliminary-report builder, did not
rewrite raw JSONL, did not refresh report artifacts, and did not write
`outputs/`, `artifacts/`, `docs/preliminary_report/_report_data.json`,
`docs/preliminary_report/index.html`, or
`docs/preliminary_report/index.es.html`.

## Validation Commands

Executed:

```bash
git diff --check
git status --short --branch
git diff --name-only -- shared/analysis shared/tests docs/preliminary_report outputs artifacts cluster1 cluster2 cluster3 pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
positive execution-authorization scan over docs/15, docs/handoff, docs/17,
and this audit report
rg -n "structural_code_surface|task_functional|mixed_diagnostic|planned_deferred|future_only|benchmarkable_performance|metric_registry|outcome_family|reportability|current_status|level_gate|metric_gate" docs/15_experiment_change_orchestration_contract.md docs/handoff docs/17_structural_task_analyzer_metadata_implementation_spec.md audits/structural_task_s4_experiment_integration_report.md
git status --short --ignored=matching -- docs/preliminary_report/_report_data.json docs/preliminary_report/index.html docs/preliminary_report/index.es.html
```

Results:

- `git diff --check`: pass.
- `git status --short --branch`: only allowed S4 docs/audit changes are
  present.
- Forbidden code/output diff scan: empty output.
- Positive execution-authorization scan: empty output, exit code 1 for no
  matches.
- Metric-family terminology scan: non-empty hits across S4-touched planning
  docs plus preexisting handoff policy docs; required terms are present.
- Ignored preview status:
  - `!! docs/preliminary_report/_report_data.json`
  - `!! docs/preliminary_report/index.es.html`
  - `!! docs/preliminary_report/index.html`

## Classification

`S4_EXPERIMENT_INTEGRATION_COMPLETE_DOCS_ONLY`

## Next-Step Recommendation

Commit the docs/audit-only S4 branch after review. Do not run experiments or
refresh outputs as part of S4 closeout.
