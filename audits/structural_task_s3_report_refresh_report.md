# Structural/Task S3 Report Refresh Report

- Version: 1.0.0
- Date: 2026-06-04
- Classification: S3_REPORT_REFRESH_COMPLETE
- Review status: pending independent review
- Branch: `codex/structural-task-s3-report-refresh`
- Baseline: `a7b0cdb Add S2 report metadata consumption`
- Scope: derived preliminary-report output refresh only
- Modal/GPU/generation/experiment execution: none
- Raw JSONL rewrite: none
- Analyzer numeric semantics change: none

## Executive Summary

S3 refreshed the local preliminary-report derived output from existing local
inputs so the visible embedded report data reflects the S1/S2 structural vs
task separation. The refresh used the existing report builder only. It did not
rerun experiments, invoke Modal, run generation, mutate raw JSONL artifacts,
change analyzer numeric semantics, or add paper-scale claims.

The current analyzer artifact still lacks accepted S1 metadata fields, so the
refreshed report data correctly follows the conservative
`legacy_metadata_unavailable` fallback path while exposing structural,
task/functional, mixed diagnostic, and future benchmarkable/performance groups.

## Refresh Command Run

Report data refresh:

```text
.venv/bin/python docs/preliminary_report/_build_data.py
```

Observed output:

```text
Wrote /Users/alexeidelgado/Desktop/TritonGen/docs/preliminary_report/_report_data.json

none: n=180, compile_successes=0
G: n=177, compile_successes=3
C: n=180, compile_successes=0
G+C: n=177, compile_successes=4
Template G ref: {'n': 180, 'compile_successes': 180, 'compile_rate': 1.0}
```

HTML inline refresh:

```text
.venv/bin/python -c "... replace <script id=\"report-data\"> JSON in docs/preliminary_report/index.html and docs/preliminary_report/index.es.html ..."
```

The inline step reused the report README's documented replacement pattern and
applied it to both language variants.

## Input Artifacts Used

The report builder read the existing local inputs only:

```text
bf298d02d7a9e918fa59918ed7cc8295280e6577295a44da1f3804898c0f33b5  outputs/analysis/factorial_2x2_preliminary.json
1f3e004b25564f347b2fb293216d2a9589ac7aaa60728cabd1d20e40af4f4cc3  outputs/cluster1/baseline_repaired_l4_n20.jsonl
59e6026d18db58fae0472591f3b924f83c837e99b0a543b131efe94a9e37751a  outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
b87f7f8dc1b9e26a3f34f62c69843b46da55f1f58faddd5f68e9efb108de678b  outputs/cluster2/c_paper_n20_l4.jsonl
b02e2a02d1f60e823ec7464942e974037a324ff0153c33aff0051ad2bf3fdc5f  outputs/cluster2/g_plus_c_paper_n20_l4.jsonl
51af551433ae5180eac85cf877409a8d73b0e53fba07b40699d42024757a3d18  outputs/cluster1/final_g_l4_n20.jsonl
```

No raw input artifact was rewritten.

## Output Files Changed

Derived local preview outputs refreshed:

- `docs/preliminary_report/_report_data.json`
- `docs/preliminary_report/index.html`
- `docs/preliminary_report/index.es.html`

Source-controlled S3 audit/handoff files changed:

- `audits/structural_task_s3_report_refresh_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`

No source-controlled analyzer, runner, test, cluster, dependency, lockfile,
`outputs/`, `artifacts/`, or `mlruns/` files were changed by S3.

## Structural/Task Separation Verification

The refreshed embedded data includes:

- `metadata_consumption.status=legacy_metadata_unavailable`
- `outcome_families.structural_code_surface`
- `outcome_families.task_functional`
- `outcome_families.mixed_diagnostic`
- `outcome_families.benchmarkable_performance`
- `outcome_metric_groups.structural_code_surface`
- `outcome_metric_groups.task_functional`
- `outcome_metric_groups.mixed_diagnostic`
- `outcome_metric_groups.benchmarkable_performance`

Metric grouping remains separated:

- `level1_compile_success_rate` is structural/code-surface, secondary
  structural evidence, and not task correctness.
- `grammar_valid_rate` is structural/code-surface diagnostic evidence.
- `level2_functional_success_rate` is task/functional primary evidence under
  the Level 2 harness.
- `terminal_failure_distribution` is mixed diagnostic and non-headline.
- `benchmarkable_performance_future_scope` is future-only with
  `computed_report_value_present=false`.

The current local analyzer artifact does not contain S1 planned-deferred
registry rows, so the refreshed production payload has no current
`planned_deferred` rows. The S2 builder tests still cover planned-deferred
handling with accepted S1 metadata fixtures.

## Legacy Metadata Behavior

The current analyzer JSON predates the accepted S1 metadata shape. The builder
therefore emitted:

```text
metadata_status legacy_metadata_unavailable
legacy True
families benchmarkable_performance,mixed_diagnostic,structural_code_surface,task_functional
future_metric future_only False
s1_diagnostics {}
```

This is the expected S1/S2 handoff path for current local analyzer data: use
conservative structural/task labels, do not invent S1-only diagnostics, and do
not treat future-only metrics as computed current values.

## No Modal/GPU/Generation Proof

Only local `.venv/bin/python` commands and git/read-only inspection commands
were run. S3 did not invoke Modal, GPU jobs, generation, experiments,
benchmarks, profilers, Nsight, or NCU.

## No Raw JSONL Rewrite Proof

The raw-output diff scan is required to stay empty:

```text
git diff --name-only -- outputs artifacts
```

Observed result: empty.

S3 read raw JSONL inputs but did not write, append, archive, delete, or
regenerate them.

## Claim-Boundary Scan

Report-facing scan results were reviewed for caveats and prohibitions. S3 adds
no claim that:

- compile success is task correctness;
- functional success is structural quality;
- `syntax_valid_rate` is a computed current mixed-schema metric;
- benchmarkable/performance metrics are current evidence;
- ungated pass-at-k is a report headline;
- performance, speedup, profiler, or paper-scale evidence was generated.

The refreshed output keeps performance/benchmarkability future-only and keeps
the current 2x2 scope caveats intact.

## Tests/Checks Run

Passed:

```text
.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py shared/tests/test_reporting_tables.py -q
11 passed in 0.07s

.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q
102 passed in 6.96s
```

Passed post-doc-edit checks:

```text
git diff --check
passed

git diff --name-only -- shared/analysis/factorial.py shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
empty

git diff --name-only -- outputs artifacts
empty

rg -n "modal run|\\.remote\\(|MODAL_AUTHORIZED: YES|GPU_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|EXPERIMENT_EXECUTION_AUTHORIZED: YES|BENCHMARK_AUTHORIZED: YES|PROFILER_AUTHORIZED: YES|Nsight|NCU|ncu|nsys" docs/preliminary_report docs/handoff audits/structural_task_s3_report_refresh_report.md
hits reviewed as explicit prohibitions or historical observability records only

rg -n "\\bpass@k\\b|bare pass@k|compile success.*correctness|functional success.*structural|syntax_valid_rate.*computed|benchmarkable_pass_at_k.*current|paper-scale|performance improvement" docs/preliminary_report audits/structural_task_s3_report_refresh_report.md docs/handoff/experiment_change_orchestration_state.md
hits reviewed as caveats, prohibitions, future-only checks, tests, or existing report prose; no S3 claim leakage found

git status --short --ignored docs/preliminary_report/_report_data.json docs/preliminary_report/index.html docs/preliminary_report/index.es.html
!! docs/preliminary_report/_report_data.json
!! docs/preliminary_report/index.es.html
!! docs/preliminary_report/index.html
```

## HTML Commit Decision

`docs/preliminary_report/index.html`,
`docs/preliminary_report/index.es.html`, and
`docs/preliminary_report/_report_data.json` remain ignored by `.gitignore`:

```text
!! docs/preliminary_report/_report_data.json
!! docs/preliminary_report/index.es.html
!! docs/preliminary_report/index.html
```

S3 refreshed them as local derived report previews but does not force-add them
in this implementation checkpoint. The report README treats the HTML files as
report deliverables, but repository policy currently ignores them. Source
controlled publication of the generated HTML/data should be a review decision,
not an implicit S3 side effect.

## Classification

`S3_REPORT_REFRESH_COMPLETE`

Local S3 refresh is complete pending independent review. The refresh stayed
within the approved report-derived output boundary and kept all raw scientific
artifacts stable.

## Next-Step Recommendation

Review S3 with special attention to the generated-file policy decision. If the
review decides that the preliminary report publication model requires checked-in
HTML/data deliverables, force-add only the refreshed report-derived files under
an explicit review decision. Otherwise, commit the source-controlled audit and
handoff records only, leaving the refreshed HTML/data as ignored local preview
outputs.
