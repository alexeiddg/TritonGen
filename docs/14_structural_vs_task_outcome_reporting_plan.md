# Structural Vs Task Outcome Reporting Plan

- Status: implementation planning document / no code changes authorized by itself
- Scope: analyzer/reporting terminology, metric grouping, and report tables
- Primary goal: make the report answer two separate questions cleanly:
  - what improves generated-code structure?
  - what improves task success?
- Implementation authority: this document defines the vocabulary and reporting
  intent. `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
  is the executable S0-S3 implementation contract for analyzer metadata,
  report-label sequencing, compatibility, and output-mutation boundaries.

## Executive Summary

The current report should distinguish structural/code-surface quality from
task/functional quality. The shorthand "format" is too narrow because syntax,
grammar acceptance, harness surface compatibility, and compile/launch success
are not merely formatting. They are structural gates. They are also not task
success, because a Triton kernel can compile and still compute the wrong values.

The implementation should add an explicit outcome-family layer to docs,
analyzer metadata, and report tables:

| Report question | Outcome family | Evaluation levels | Example metrics |
|---|---|---|---|
| What improves generated-code structure? | `structural_code_surface` | Level 0 / Level 1 | `syntax_valid_rate`, `grammar_valid_rate`, F0/F1 distribution, `compile_success_rate`, `compile_pass@k` |
| What improves task success? | `task_functional` | Level 2 and later | `functional_success_rate`, `repair_set_success`, `eval_set_success`, F2 distribution, `correctness_pass@k`, future benchmarkable/performance metrics |

This is a reporting and analysis-clarity change first. It must not silently
change Cluster 2 repair semantics, current artifact identities, or current
primary/secondary comparisons.

## Non-Goals

- Do not rename `C` or change it from F2-only correctness feedback.
- Do not make Cluster 2 repair F0 or F1 failures.
- Do not rewrite current JSONL artifacts.
- Do not replace `functional_success` as the primary correctness outcome.
- Do not promote performance, timing, profiling, or speedup claims before the
  Cluster 3/performance contracts allow them.
- Do not hide the current result that C has 180/180 `F0_PARSE` rows and
  therefore does not activate correctness feedback in the current paper-scale
  artifact.

## Terminology

Use these names in new docs and report prose:

| Term | Meaning | Do not imply |
|---|---|---|
| Structural/code-surface quality | The generated source passes syntax, grammar, harness-surface, compile, or launch gates. | Numerical correctness or speed. |
| Task/functional quality | The candidate computes the correct result under the Level 2 correctness harness. | Performance or benchmark superiority. |
| Benchmarkable/performance quality | The candidate is correct and reaches authorized timing/performance evaluation. | Current preliminary 2^2 evidence. |

Avoid saying "format success" when the metric is actually compile, launch, or
harness acceptance. Prefer "structural", "surface", "compile", or
"code-surface" depending on the exact gate.

## Metric Registry Target

Every report-facing metric should have a small registry entry before it appears
in a table or chart. This can be implemented as analyzer metadata first, then
formalized in code if more reports reuse it.

Required fields:

```text
metric_name
display_name
outcome_family
level_gate
metric_gate
denominator_unit
denominator_policy
attempt_policy
cluster_owner
scope
reportability
current_status
caveat
```

Initial registry rows:

| Metric | Outcome family | Gate | Denominator policy | Status |
|---|---|---|---|---|
| `syntax_valid_rate` | `structural_code_surface` | Level 0 parse/surface | all generated rows with parse/surface evidence | planned |
| `grammar_valid_rate` | `structural_code_surface` | GBNF parse and semantic validator | grammar-active rows with grammar metadata | current diagnostic |
| `compile_success_rate` | `structural_code_surface` | Level 1 compile/launch | all generated rows, with documented F3 policy | current secondary |
| `compile_pass@k` | `structural_code_surface` | Level 1 compile/launch | sample groups by condition/kernel/dtype | current Cluster 1, needs cross-cluster labeling |
| `functional_success_rate` | `task_functional` | Level 2 correctness | all generated rows; Cluster 1 remains false/unproven | current primary |
| `correctness_pass@k` | `task_functional` | Level 2 correctness | sample groups with Level 2 evidence | planned |
| `repair_set_success_rate` | `task_functional` | Level 2 repair set | rows that reached Level 2 repair-set evaluation | current Cluster 2 diagnostic |
| `eval_set_success_rate` | `task_functional` | Level 2 eval set | rows that reached Level 2 eval-set evaluation | current Cluster 2 diagnostic |
| `terminal_failure_distribution` | mixed diagnostic | F0/F1/F2/F3 family | all terminal rows | current diagnostic |
| `benchmarkable_pass@k` | `benchmarkable_performance` | Level 2 plus performance stage reached | correct rows with authorized timing stage | future only |

## Analysis Policy

### Intent-To-Treat First

Primary condition comparisons should remain intent-to-treat: every generated row
for a condition stays in the denominator unless an existing analyzer policy
explicitly says otherwise, such as the current F3 compile-rate denominator
policy.

This prevents a feedback loop from looking better only because ineligible rows
were removed.

### Eligibility Diagnostics Second

Add activation and eligibility diagnostics next to intent-to-treat results:

```text
level0_pass_rate
level1_reached_rate
level2_reached_rate
c_feedback_eligible_rate
c_feedback_loop_fired_rate
p_feedback_eligible_rate
p_feedback_loop_fired_rate
```

For the current C artifact, this should make the limitation explicit:

```text
C feedback eligibility = 0/180 because current C rows are F0_PARSE.
```

That statement is more accurate than saying the correctness-feedback mechanism
was exercised and failed.

### Current Primary And Secondary Roles Stay Stable

For the current 2^2 report:

- `functional_success` remains the primary task/functional response.
- `compile_success` remains a secondary structural response.
- `grammar_valid`, failure distribution, and stop reasons remain diagnostics.
- Cluster 1 functional success remains false/unproven because Level 2 was not
  run.

## Implementation Phases

### Phase 0 - Documentation Alignment

Update docs only.

Files:

- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/09_preliminary_report_outline.md`
- `docs/12_experiment_observability_plan.md`
- `docs/preliminary_report/preliminary_report.md` if current prose is refreshed

Required changes:

- Add the structural vs task terminology.
- Add the question-to-metric table.
- State that `compile_success` is structural, not task success.
- State that `functional_success` is task/functional and is unproven for
  Cluster 1 rows.
- State that C activation requires Level 2/F2 eligibility.
- Preserve all current caveats: 177/180 G/G+C coverage, five G+C F3 rows,
  P-deferred, single model, and provenance gaps.

Acceptance criteria:

- A reader can identify which metrics answer "what improves code structure?"
  and which answer "what improves task success?"
- No doc says F0/F1 repair is part of Cluster 2 C.
- No doc implies compile success is numerical correctness.

### Phase 1 - Analyzer Metadata Extension

Add additive metadata to the analyzer output. Preserve existing keys for
backward compatibility.

Likely files:

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`

Add:

```text
metadata.metric_registry
metadata.outcome_families
diagnostics.feedback_activation
diagnostics.level_reach_rates
```

Do not remove or rename:

```text
condition_rates
paired_comparisons
grammar_funnel
failure_code_distribution
```

Acceptance criteria:

- Existing tests for the current 2^2 analyzer remain green.
- Old consumers that read `condition_rates` still work.
- New metadata clearly marks `compile_success` as
  `structural_code_surface` and `functional_success` as `task_functional`.
- Cluster 1 `functional_success=False` is explicitly marked as unproven rather
  than measured Level 2 failure.

### Phase 2 - Report Data Builder And Dashboard

Use analyzer metadata to drive report sections rather than hard-coding ambiguous
labels.

Likely files:

- `docs/preliminary_report/_build_data.py`
- `docs/preliminary_report/preliminary_report.md`
- `docs/preliminary_report/index.html`
- `docs/preliminary_report/index.es.html`

Target report structure:

```text
Structural/code-surface outcomes
  - syntax/grammar funnel
  - F0/F1 distribution
  - compile success and compile pass@k

Task/functional outcomes
  - Level 2 reach rate
  - functional success
  - repair/eval set success
  - F2 distribution and C activation

Future benchmarkable/performance outcomes
  - present only as deferred scope unless Cluster 3/performance artifacts exist
```

Acceptance criteria:

- Tables do not mix compile and functional success under one unlabeled "pass"
  heading.
- Any `pass@k` display includes the gate, such as `compile_pass@k` or
  `correctness_pass@k`.
- Current C rows show zero C-feedback eligibility in diagnostics rather than
  being interpreted as an exercised repair loop.

### Phase 3 - Pass@k Label Cleanup

Standardize pass@k names by gate.

Likely files:

- `shared/eval/metrics/pass_at_k.py`
- `shared/stats/pass_at_k.py`
- `cluster1/experiments/analyze_cluster1.py`
- `cluster1/experiments/make_cluster1_figures.py`
- report data builders

Policy:

- Existing Cluster 1 `pass@k` may remain for backward compatibility inside old
  outputs, but new report-facing labels should say `compile_pass@k`.
- New Level 2 pass@k should be named `correctness_pass@k`.
- Future performance-stage pass@k should be named `benchmarkable_pass@k`.

Acceptance criteria:

- No new table uses bare `pass@k` without `metric_gate`.
- Existing tests and old output parsers are not broken by label additions.

### Phase 4 - Optional Analyzer Output Rerun

If the report needs a refreshed analyzer JSON, write a new output or make the
rerun explicitly documented.

Rules:

- Do not edit raw JSONL artifacts.
- Preserve the current artifact registry identities.
- Record analyzer version and reportability metadata.
- Keep current numeric results unchanged unless the analyzer logic intentionally
  changes a diagnostic-only output.

Acceptance criteria:

- Any changed analyzer output has a reproducible command and audit note.
- Primary current rates and paired comparisons remain traceable to the same
  714 loaded rows unless a new registered artifact lineage is introduced.

## Backward Compatibility Plan

- Add new fields rather than renaming existing analyzer keys.
- Treat missing metric-registry metadata as legacy output, not invalid output.
- Preserve current `functional_success` and `compile_success` fields.
- Preserve current `condition_rates` and `paired_comparisons` shapes.
- Keep Cluster 1 compile-only pass@k code working while exposing report-facing
  aliases as `compile_pass@k`.
- Do not mutate current artifact rows to add derived fields.

## Fairness And Correctness Controls

| Risk | Control |
|---|---|
| Structural metrics get mistaken for task success | Outcome-family labels and level gates in every report table. |
| Feedback looks ineffective because it never activates | Add eligibility and loop-fired diagnostics. |
| Feedback looks effective because only eligible rows are shown | Intent-to-treat comparison remains primary; eligible-set analysis is diagnostic. |
| Extra attempts confound feedback effects | Report attempt budgets and no-feedback retry controls for future feedback ablations. |
| Current C all-F0 result is over-interpreted | State that C did not reach Level 2 in the current paper-scale artifact. |
| Cluster 1 is treated as functionally failed | Label Cluster 1 functional status as unproven, not measured false. |
| F3 rows disappear from interpretation | Keep F3 counts visible and preserve current compile-rate F3 policy. |

## Report Copy Rules

Use:

```text
Task-agnostic G improved structural/code-surface outcomes modestly in the
current artifacts, but did not establish task/functional success.
```

Avoid:

```text
G improved format and therefore made kernels correct.
```

Use:

```text
Current C rows were not eligible for correctness feedback because they failed at
F0 before reaching Level 2.
```

Avoid:

```text
C feedback was tried 180 times and failed.
```

Use:

```text
Cluster 1 functional success is unproven because Level 2 was not run.
```

Avoid:

```text
Cluster 1 failed numerical correctness.
```

## Open Decisions

Before code implementation, decide:

- whether `metric_registry` should live only in analyzer output metadata or also
  in a shared Python registry module;
- the exact formula for `syntax_valid_rate` across mixed Cluster 1/Cluster 2
  schemas;
- whether current report HTML should be refreshed immediately or only after the
  analyzer metadata extension;
- whether a new analyzer output path is needed for the metadata-only rerun.

## Recommended First PR

Start with a docs-only PR:

1. Add this plan.
2. Update `docs/06_failure_taxonomy_and_eval_ladder.md` with terminology.
3. Update `docs/07_analysis_and_statistics.md` with the question-to-metric map.
4. Update `docs/09_preliminary_report_outline.md` so report prose uses the two
   outcome families.
5. Do not touch code, artifacts, or analyzer outputs in the first PR.

That keeps blast radius low and gives the analyzer/report changes a stable
contract before implementation.

After `docs/17_structural_task_analyzer_metadata_implementation_spec.md` is in
force, S0 acceptance should be a short terminology gate confirmation rather
than a second planning cycle. S1 should then implement only the additive
analyzer metadata contract defined there.
