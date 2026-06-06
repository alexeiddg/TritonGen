# L1b n=5 Completion And Analyzer Boundary Audit

## Executive Summary

This audit reviewed the pushed L1b n=5 12-cell
`grammar_mode x C x P` completion package and the analyzer/reporting patch that
made valid development-scale selector output analyzable without replay-paired
metadata.

Result: the L1b package is clean enough to proceed to a separate L2 n=20
authorization-packet drafting/review step. This audit does not authorize L2
execution, Modal/GPU use, generation, output mutation, MLflow runtime writes,
benchmarking, profiling, speedup claims, cost-per-success claims, or paper-scale
claims.

Classification: `L1B_N5_AUDIT_PASS_L2_READY`

## Pushed Baseline Status

Baseline verification commands:

```text
git checkout codex-track-handoff-context
git status --short --branch
git fetch origin codex-track-handoff-context
git rev-parse HEAD
git rev-parse origin/codex-track-handoff-context
git log --oneline -12
```

Observed status:

- current branch: `codex-track-handoff-context`
- local `HEAD`: `387c0736715e7686630703550c888f42e153c9f3`
- origin `codex-track-handoff-context`:
  `387c0736715e7686630703550c888f42e153c9f3`
- local and origin agree
- required commit `a52d64a Authorize L1b n5 selector profile` is in history
- required commit `387c073 Complete L1b n5 12-cell validation` is in history
- worktree was clean before audit edits

Recent history included:

```text
387c073 Complete L1b n5 12-cell validation
a52d64a Authorize L1b n5 selector profile
bc77e9b Audit L1a analyzer patch and golden drift
1367cdb Preserve L1a n1 generated artifacts
61fa0ac Validate L1a n1 12-cell completion
```

## L1b Output Evidence Checked

Reviewed evidence surfaces:

- `audits/l1b_n5_execution_completion_report.md`
- `audits/l1b_n5_analyzer_dev_scope_patch_report.md`
- `shared/analysis/factorial.py`
- `shared/tests/test_analyzer_cluster3.py`
- `shared/tests/test_factorial_analysis.py`
- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.json`
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.md`
- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_billing_report_20260606_utc.json`
- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

The audit did not mutate L1b outputs, observability artifacts, analysis JSON,
markdown report artifacts, billing artifacts, or `mlruns/`.

## Row/Cell Coverage Result

Direct disk validation found:

```text
rows 60
jsonl_files 12
cells 12 rows_per_cell [5]
grammar_modes ['grammar_off', 'task_agnostic', 'template_upper_bound']
grammar_mode_counts {'grammar_off': 20, 'task_agnostic': 20, 'template_upper_bound': 20}
c_values ['c_off', 'c_on'] p_values ['p_off', 'p_on']
condition_counts {'C': 5, 'C+P': 5, 'G': 10, 'G+C': 10, 'G+C+P': 10, 'G+P': 10, 'P': 5, 'none': 5}
no_p_repairs_bad 0 p_repairs 2 c_repairs 2
```

Coverage result:

- exactly 12 `grammar_mode x C x P` cells exist
- exactly 5 rows per cell exist
- `grammar_off`, `template_upper_bound`, and `task_agnostic` are all present
- C off/on and P off/on are represented
- no-P cells are controls, not P evidence
- no P repair fired in no-P controls

## Sidecar/Provenance Validation Result

Direct sidecar validation found:

```text
content_hash_sidecars_valid 12
observability_hash_sidecars_valid 12
observability_event_counts {'row_completed': 60, 'row_started': 60, 'run_completed': 12, 'run_started': 12, 'stage_completed': 184, 'stage_started': 184}
mlruns_exists False
```

For each output JSONL, the corresponding `.jsonl.hashes.json` sidecar exists
and contains schema, pipeline-hash, and external-pin provenance. For each
observability JSONL, the hash sidecar's event JSONL SHA-256, summary JSON
SHA-256, and event count matched the files on disk.

The analysis JSON, markdown report, billing artifact, output JSONL files,
content-hash sidecars, observability JSONL files, observability summary files,
and observability hash sidecars are present.

## Analyzer Patch Assessment

The analyzer patch from `a52d64a..387c073` is narrow. In
`shared/analysis/factorial.py`, the old L1a smoke-only skip helper was replaced
with `GRAMMAR_MODE_SELECTOR_NON_PAPER_PAIR_SKIP_SCOPES`, currently:

```text
l1a_grammar_mode_cp_smoke
l1b_grammar_mode_cp_dev
```

The skip applies only to paired-comparison construction errors caused by
selector outputs that lack replay-paired metadata. It does not alter row
parsing, pass/fail definitions, C/P dispatch, repair eligibility, repair
history policy, grammar semantics, model/sampling settings, denominators, or
output row schema semantics.

The patch does not fabricate missing C/P metadata and does not silently drop
required repair metadata. C and P activity remains read from the preserved row
metadata.

## Paper-Scale Strictness Assessment

Paper-scale strictness is preserved. The new regression test in
`shared/tests/test_analyzer_cluster3.py` removes paired replay metadata from
development rows and verifies both sides of the boundary:

- default analyzer scope still raises `missing paired replay metadata`
- `analysis_scope="l1b_grammar_mode_cp_dev"` succeeds only as non-reportable
  development evidence
- `metadata.reportable` remains `False`
- `metadata.scale_tiers` remains `["development"]`
- three-way interaction reportability remains `False`
- three-way reason remains `requires_reportable_primary_paper_scale_output`

The existing paper/reportability tests in `shared/tests/test_factorial_analysis.py`
also passed in the focused regression bundle.

## Dev/Smoke Evidence Boundary Assessment

The L1b analysis is development-scale evidence only. It is not L2, n=20,
paper-scale, or reportable paper evidence.

The L1b markdown report title is:

```text
L1b development-scale 2^3 factorial diagnostic analysis
```

The report states that the analysis is development-scale only, not paper-scale
or reportable paper evidence, and that three-way interaction fields are
diagnostic only.

## Analyzer/Report Output Assessment

Direct analysis/report checks found:

```text
analysis l1b_grammar_mode_cp_dev False ['development'] 0
three_way {'formula': '(rate_GCP - rate_GC) - (rate_GP - rate_G) - (rate_CP - rate_C) + (rate_P - rate_none)', 'reason': 'requires_reportable_primary_paper_scale_output', 'reportable': False, 'response_variable': 'functional_success'}
report_boundary True True
```

The analysis/report output:

- identifies the scope as `l1b_grammar_mode_cp_dev`
- marks the result `reportable=false`
- records `scale_tiers=["development"]`
- emits no paired comparisons because selector rows lack paired replay metadata
- records model separation for factorial terms rather than presenting fitted
  effect estimates as claims
- keeps three-way interaction output diagnostic and non-reportable
- keeps C/P metadata observational rather than treating no-P controls as P
  evidence

One interpretation caveat remains important for future graphs: condition labels
`G`, `G+C`, `G+P`, and `G+C+P` are collapsed across both
`template_upper_bound` and `task_agnostic` rows in the current L1b report table.
Future L2 reporting should facet or stratify by `grammar_mode` before making
claims about grammar effects.

## Billing Caveat Assessment

The preserved billing artifact exists and the billing query succeeded. The L1b
matching UTC-hour entry is:

```text
Interval Start: 2026-06-06T18:00:00
Cost: 2.13879534
Tags: {}
```

Because Modal returned empty tags, billing is UTC-window-only workspace evidence
and not clean tag-attributed per-run billing proof. The audits and report
surfaces do not claim cost-per-success, pass@k cost, ROI, economic lift,
speedup, benchmark results, or tag-attributed per-run billing.

The matching L1b UTC-hour cost is below the user-stated operational cap, but the
empty-tag caveat remains material for attribution.

## Tests Run

Analyzer regression bundle:

```text
.venv/bin/python -m pytest shared/tests/test_analyzer_cluster3.py shared/tests/test_factorial_analysis.py -q
```

Result:

```text
142 passed
```

Launcher/grammar-mode regression bundle:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Result:

```text
167 passed
```

Compilation:

```text
.venv/bin/python -m compileall -q shared cluster3
```

Result: passed.

Whitespace:

```text
git diff --check
```

Result: passed after audit edits.

## Protected Mutation Proof

Protected mutation scan:

```text
git diff --name-only -- \
  outputs \
  mlruns \
  docs/preliminary_report \
  pyproject.toml \
  requirements.txt \
  requirements-dev.txt \
  uv.lock \
  poetry.lock \
  Pipfile.lock
```

Result: empty output.

Artifact/output mutation scan:

```text
git diff --name-only -- artifacts outputs
```

Result: empty output.

No Modal command, GPU job, generation command, L1b rerun, L2 run, n=20 run,
paper-scale run, profiler, benchmark, billing query, output mutation, artifact
mutation, dependency change, lockfile change, preliminary-report refresh, or
MLflow runtime write occurred during this audit.

## Remaining Caveats

- L1b is n=5 development-scale evidence only.
- L1b is not paper-scale evidence and is not reportable paper evidence.
- L1b billing attribution is UTC-window-only because Modal returned empty tags.
- MLflow was disabled for the run and `mlruns/` is absent.
- Current L1b outcomes are dominated by grammar mode; future graphs must not
  collapse `template_upper_bound` and `task_agnostic` into one unqualified `G`
  claim.
- C/P repair activity was observed but sparse at L1b n=5; this does not support
  a repair-efficacy claim.
- L2 n=20 execution still requires a separate signed packet with explicit
  stop/spend limits, output paths, validation plan, billing policy, and claim
  boundaries.

## L2 n=20 Go/No-Go

Go for a separate L2 n=20 authorization packet drafting/review step.

No-go for L2 execution until a later packet explicitly authorizes Modal/GPU,
generation, output/artifact mutation, billing handling, validation commands,
MLflow policy, stop/spend limits, and claim boundaries.

## Classification

`L1B_N5_AUDIT_PASS_L2_READY`

## Next-Step Recommendation

Prepare a separate L2 n=20 packet that preserves the 12-cell
`grammar_mode x C x P` design, keeps `grammar_mode` as a first-class reporting
dimension, records the empty-tag billing caveat from L1b, and requires signed
authorization before any Modal/GPU/generation/output-mutating execution.
