# Structural/Task S2 Report Consumption Report

- Version: 1.0.1
- Date: 2026-06-04
- Classification: S2_REVIEW_PASS_COMMIT_ALLOWED_CODE_DOCS_ONLY
- Branch: `codex/structural-task-s2-report-consumption`
- Baseline: `ff876d2 Add S1 analyzer metric registry metadata`
- Scope: report builder/dashboard consumption only
- Output mutation: none
- Raw JSONL rewrite: none
- Experiment run: none

## Purpose

S2 updates the preliminary report builder/dashboard path to consume S1 analyzer
metadata when available while preserving legacy fallback behavior for analyzer
JSON that predates S1 metadata. The implementation keeps structural/code-surface
quality separate from task/functional quality, keeps mixed diagnostics out of
headline claims, and keeps planned-deferred or future-only metrics from becoming
computed current values.

## Files Changed

Source-controlled S2 files changed:

- `docs/preliminary_report/_build_data.py`
- `docs/preliminary_report/tests/test_build_data.py`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `audits/structural_task_s2_report_consumption_report.md`

Ignored preview files reviewed but excluded from the code/docs-only commit:

- `docs/preliminary_report/index.html`
- `docs/preliminary_report/index.es.html`

Forbidden surfaces not changed:

- `shared/analysis/factorial.py`
- `outputs/`
- `artifacts/`
- `cluster1/`
- `cluster2/`
- `cluster3/`
- result schemas
- dependencies and lockfiles
- `mlruns/`

## Implementation Summary

`docs/preliminary_report/_build_data.py` now emits additive report-consumption
metadata beside the existing report data:

- `metadata_consumption`
- `outcome_families`
- `outcome_metric_groups`
- `analyzer.metadata_consumption`
- `analyzer.outcome_families`
- `analyzer.report_metric_registry`
- `analyzer.report_metric_groups`
- `analyzer.s1_diagnostics`

When S1 metadata and diagnostics are present, the builder consumes:

- `metadata.outcome_families`
- `metadata.metric_registry`
- `diagnostics.level_reach_rates`
- `diagnostics.feedback_activation`
- `diagnostics.metric_availability`

The existing `analyzer.metadata` pass-through preserves S1 fields such as
`metadata.metric_aliases` and `metadata.registry_provenance` for consumers that
already read analyzer metadata, but S2 does not promote them into new
report-facing tables.

When S1 metadata or diagnostics are missing, the builder marks
`legacy_metadata_unavailable=true`, uses conservative fallback labels for
legacy fields, and does not invent S1-only diagnostics such as feedback
activation, level-reach rates, or syntax-validity aggregates.

The English and Spanish ignored dashboard preview files were reviewed. They add
a small outcome-family panel and keep locale text aligned, but they are ignored
by repository policy and are intentionally excluded from the code/docs-only S2
commit unless a later review explicitly approves force-adding dashboard assets.

## Claim-Boundary Checks

- `level1_compile_success_rate` is grouped as structural/code-surface and
  secondary structural evidence.
- `level2_functional_success_rate` is grouped as task/functional and primary
  task evidence.
- `terminal_failure_distribution` remains mixed diagnostic and non-headline.
- `syntax_valid_rate`, `compile_pass_at_k`, `correctness_pass_at_k`,
  `repair_set_success_rate`, and `eval_set_success_rate` remain deferred when
  S1 metadata marks them planned-deferred.
- `benchmarkable_pass_at_k` remains future-only and has no computed current
  report value.
- Current production/embedded analyzer data still predates S1 metadata unless
  S3 refresh is separately approved, so it follows the legacy fallback display
  path.

## Requirement Mapping

| Requirement | Evidence |
|---|---|
| S2-REQ-001 legacy analyzer fallback | `metadata_consumption.status=legacy_metadata_unavailable`; focused legacy fallback test |
| S2-REQ-002 handoff path recorded | This report and live state record path 1 support in code/tests and path 3 fallback for current pre-S1 analyzer data |
| S2-REQ-003 no S1-only diagnostics from legacy JSON | `analyzer.s1_diagnostics={}` in legacy fallback test |
| S2-REQ-004 registry display-string safety | Builder rejects unsafe registry display strings before report output |
| S2-REQ-005 localization parity | Ignored English and Spanish dashboard preview hooks were reviewed together and intentionally excluded from the code/docs-only commit; source-controlled bilingual dashboard publication remains deferred unless force-add is explicitly approved |

## Validation

Passed:

```text
.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py -q
4 passed

.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q
102 passed

.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py shared/tests/test_reporting_tables.py -q
11 passed

.venv/bin/python -c "import importlib.util, pathlib; p=pathlib.Path('docs/preliminary_report/_build_data.py'); spec=importlib.util.spec_from_file_location('bd', p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); data=m.aggregate(); assert data['metadata_consumption']['status'] == 'legacy_metadata_unavailable'; assert data['analyzer']['s1_diagnostics'] == {}; print(data['metadata_consumption']['status'])"
legacy_metadata_unavailable

git diff --check
passed

git diff --name-only -- outputs artifacts cluster1 cluster2 cluster3 pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
empty

git diff --name-only -- shared/analysis/factorial.py
empty

git diff --name-only -- outputs artifacts
empty
```

Known non-S2 residual:

```text
.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py shared/tests/test_reporting_tables.py shared/tests/test_reporting_language.py -q
31 passed, 2 failed
```

The two failures are in `shared/tests/test_reporting_language.py` and assert
specific strings in `.contracts/research/research_scope.md`. S2 did not touch
that contract file, `git diff -- .contracts/research/research_scope.md` is
empty, and patching it would exceed the S2 launch scope. The S2-specific report
builder tests and reporting table tests pass.

Report-facing terminology scan:

- Expected hits in this report and handoff state were reviewed as caveats or
  prohibitions, including the future-only benchmarkable metric and paper-scale
  non-authorization language.
- The scan found no S2 claim that compile success is task correctness, no S2
  claim that functional success is structural quality, and no report-facing
  ungated pass-at-k display.

Ignored-file decision:

- `docs/preliminary_report/index.html` and
  `docs/preliminary_report/index.es.html` are ignored by `.gitignore` via
  `docs/preliminary_report/index*.html`.
- They were reviewed in the working tree for dashboard consumption parity.
- They are excluded from the S2 code/docs-only commit because repository policy
  treats them as ignored preview/generated assets and this review did not
  authorize force-add.
- Citation-ready bilingual dashboard publication remains deferred until a later
  explicit force-add or regeneration approval.

## Boundary State

S2 review passed for a code/docs-only commit. S3 remains blocked until a separate
output-mutation packet explicitly authorizes analyzer output refresh, output
path policy, traceability checks, and audit/registry update behavior. No
current S2 change authorizes Modal, GPU, generation, experiments, raw JSONL
rewrite, analyzer-output refresh, n=5, n=20, paper-scale, profiler, timing,
speedup, benchmark, dependency, lockfile, or result-schema work.
