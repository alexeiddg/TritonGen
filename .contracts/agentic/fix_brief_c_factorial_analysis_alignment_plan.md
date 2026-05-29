# Fix Brief C: Factorial Analysis Alignment Plan

**Status:** planning only; no code changes in this file
**Date:** 2026-05-15
**Scope:** `shared/analysis/factorial.py` and only the supporting interfaces needed to keep paper-table generation aligned with the current research contract
**Primary goal:** prevent contract drift while updating factorial analysis semantics from old Cluster 1 compile-only assumptions to current Cluster 2 Level 2 paired-comparison claims

## Purpose

This plan defines the bounded rewrite needed for `shared/analysis/factorial.py`.
The fix is not a general statistics redesign and not a new analysis pipeline. It
is a research-alignment repair: the canonical analyzer must read the current
`EvalResult` shape, use `functional_success` as the primary Cluster 2 response,
preserve paired-by-seed semantics, and emit table-ready outputs without creating
parallel metric definitions.

The intended paper claim is:

```text
For matched seed cells, do the C and G+C conditions improve Level 2 functional
success relative to their frozen replay controls, and how do the G, C, and
eventual P factors compose in the factorial model?
```

## Non-Negotiable Boundaries

- Do not change data generation, replay-control selection, repair-loop behavior,
  grammar behavior, or correctness gates as part of this fix.
- Do not introduce a second aggregation contract inside the analyzer.
  `shared/eval/constants.py`, `shared/eval/aggregation.py`, and
  `shared/eval/metrics/*` remain the upstream sources for statistical constants
  and cell-level outcomes.
- Do not silently pool generated and replay rows for primary Cluster 2 claims.
  Primary Cluster 2 comparisons are matched by `(kernel_class, dtype, base_seed)`.
- Do not use `compile_success` as the primary response for Cluster 2 paper
  claims. `compile_success` is a secondary structural-validity diagnostic.
- Do not treat missing `P` cells as failed cells. They are explicitly
  `not_populated` until Cluster 3 data exists.
- Do not embed bootstrap counts, confidence levels, alpha thresholds, or
  multiple-testing methods directly in `shared/analysis/factorial.py`; consume
  constants from `shared/eval/constants.py` or add named constants there first.
- Do not write paper tables from an ad hoc script path. The canonical paper
  analyzer remains `shared/analysis/factorial.py`.
- Do not expand the fix to speedup/profiler claims except for schema-aware
  placeholders and future-compatible full `P` design handling.

## Current Mismatch To Fix

The existing analyzer was written for an older state where compile success was
the headline metric and all eight factorial cells were assumed to be available.
That is now wrong for Cluster 2 paper claims.

Required semantic corrections:

- Primary response: `functional_success` at Level 2.
- Secondary response: `compile_success` for structural-validity diagnostics.
- Current populated design: four cells only: `none`, `G`, `C`, and `G+C`.
- Future design: all eight cells: `none`, `G`, `C`, `P`, `G+C`, `G+P`,
  `C+P`, and `G+C+P`.
- Primary comparisons: paired by seed, not pooled by condition.
- Binary paired test: McNemar-style discordance test for matched outcomes.
- Lift interval: paired bootstrap over matched cells.
- Multiple testing: Holm correction using the canonical constant.
- Output shape: structured JSON-compatible rows and markdown table renderings
  that map cleanly to planned paper Tables 1-3.

## Canonical Inputs

The analyzer must accept current `EvalResult`-derived rows and Cluster 2
aggregation rows without crashing on current fields:

- `condition`
- `kernel_class`
- `dtype` or `dtype_tested`, normalized to one analyzer column
- `base_seed`
- `attempt_index`
- `compile_success`
- `functional_success`
- `scale_tier`
- `grammar_variant`
- `grammar_claim_scope`
- `unique_ratio_ast`
- `repair_traces`
- `generated_metadata`
- `replay_metadata`

Missing optional fields should produce explicit analyzer warnings when they only
affect interpretation. Missing required fields for a requested analysis mode
should fail before statistics are computed.

## Canonical Outputs

The analyzer should emit one structured result object with these sections:

- `metadata`: input paths, scale tier, populated cells, missing cells,
  constants used, analyzer version/date, and whether output is reportable.
- `cell_summaries`: per-condition rates for `functional_success` primary and
  `compile_success` secondary, grouped by condition plus `kernel_class` and
  `dtype` where applicable.
- `paired_comparisons`: matched `C` vs `none` and `G+C` vs `G` rows with effect
  size, paired confidence interval, McNemar discordance counts, raw p-value,
  Holm-adjusted p-value, and interpretation flags.
- `factorial_model`: reduced four-cell model now; full eight-cell model when
  `P` cells arrive.
- `paper_tables`: deterministic rows that can be rendered by
  `shared/eval/reporting/tables.py`.
- `diagnostics`: rejected rows, unmatched pairs, missing cells, mixed-scale
  warnings, mode-collapse warnings, and any unpaired diagnostic outputs.

## Paper Table Mapping

Use the analyzer output as the single source for planned paper tables.

| Paper Table | Analyzer Section | Required Content |
| --- | --- | --- |
| Table 1 | `cell_summaries` | Per-condition Level 2 `functional_success` rate, secondary `compile_success`, sample count, scale tier, populated-cell status |
| Table 2 | `paired_comparisons` | `C` vs `none` and `G+C` vs `G`, paired lift, paired CI, McNemar p-value, Holm-adjusted p-value |
| Table 3 | `factorial_model` | G, C, and G:C terms now; G, C, P, all two-way terms, and G:C:P after P cells exist |

## Phase 1: Contract Snapshot And Drift Guard

Before code edits, snapshot the active contracts and implementation state.

Read and reconcile:

- `.contracts/research/eval_metrics.md`
- `.contracts/research/research_scope.md`
- `.contracts/agentic/cluster2_contract.md`
- `.contracts/agentic/cluster2_paired_replay_alignment_plan.md`
- `shared/eval/constants.py`
- `shared/eval/schema.py`
- `shared/eval/aggregation.py`
- `shared/eval/metrics/equal_attempts.py`
- `shared/eval/metrics/repair.py`
- `shared/eval/reporting/tables.py`
- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`

Acceptance criteria:

- The implementation plan names every semantic source of truth.
- Any conflict between research docs and current implementation is written down
  before editing code.
- The code change list is limited to the files needed for this issue.

## Phase 2: Schema-Aware Loading

Refactor analyzer loading so it accepts current EvalResult-shaped JSONL and
Cluster 2 aggregation rows.

Acceptance criteria:

- Loader normalizes `dtype_tested` and `dtype` without losing the original value.
- Loader preserves `grammar_variant`, `grammar_claim_scope`, `scale_tier`, and
  `repair_traces`.
- Loader rejects mixed `scale_tier` inputs by default.
- Loader permits diagnostic mixed-scale mode only when explicitly requested and
  marks the output as non-paper.
- Loader distinguishes missing required fields from optional interpretation
  fields.
- No new schema fields are invented only for the analyzer when an existing
  `EvalResult` or aggregation field can be used.

## Phase 3: Response Variable Selection

Replace compile-first assumptions with explicit response-variable policy.

Required response modes:

- `primary_functional`: `functional_success`, Level 2, default for Cluster 2
  paper output.
- `secondary_compile`: `compile_success`, Level 1, diagnostic only.
- `future_fast_tc`: `fast_tc@p`, not primary until Cluster 3 / P data is
  implemented and validated.

Acceptance criteria:

- Analyzer default output uses `functional_success`.
- `compile_success` output is labeled secondary or diagnostic everywhere.
- A missing `functional_success` field is a hard failure for primary Cluster 2
  analysis, not a fallback to `compile_success`.
- Rows where `functional_success is None` are treated as not evaluated and are
  surfaced in diagnostics rather than silently counted as failures.

## Phase 4: Paired Primary Comparisons

Keep the existing paired-replay validation direction and make it the primary
analysis path for Cluster 2 comparisons.

Required primary comparisons:

- `C` vs frozen `none`, paired by `(kernel_class, dtype, base_seed)`.
- `G+C` vs frozen `G`, paired by `(kernel_class, dtype, base_seed)`.

Acceptance criteria:

- Analyzer validates pair completeness before computing statistics.
- Analyzer rejects duplicate replay rows per pair key.
- Analyzer rejects duplicate generated attempts per pair key and attempt index.
- Analyzer validates generated and replay metadata before comparing outcomes.
- Treatment success for repair-loop rows is a cell-level Bernoulli outcome:
  success if any considered attempt reaches `functional_success=True`.
- Replay success is the frozen attempt-zero outcome for the matching pair cell.
- McNemar discordance counts are emitted:
  `discordant_treatment_only`, `discordant_control_only`, and concordant counts.
- McNemar p-value is emitted for binary matched outcomes when sample size permits.
- Primary lift CI uses paired bootstrap over matched cells, not pooled bootstrap.
- Unpaired comparisons, if retained, are labeled diagnostic and excluded from
  paper-primary sections.

## Phase 5: Reduced And Full Factorial Models

Implement design-matrix handling that matches available data without pretending
future cells exist.

Current four-cell model:

```text
functional_success ~ G + C + G:C + kernel_class + dtype
```

Future eight-cell model:

```text
functional_success ~ G + C + P + G:C + G:P + C:P + G:C:P + kernel_class + dtype
```

Acceptance criteria:

- The analyzer detects populated canonical cells.
- With only `none`, `G`, `C`, and `G+C`, output says P-containing cells are
  `not_populated`.
- Missing P cells do not block current Cluster 2 tables.
- Unexpected non-canonical condition labels fail fast.
- When all eight cells exist, the analyzer switches to the full model without a
  second script path.
- Model output distinguishes model coefficients from paired primary comparison
  estimates.
- If model fitting is underpowered or separated, analyzer emits a diagnostic
  warning and still provides cell summaries and paired comparison results.

## Phase 6: Multiple Testing And Constants

Wire statistical parameters through the canonical constants.

Required constants:

- `BOOTSTRAP_SAMPLES`
- `CI_LEVEL`
- `SIGNIFICANCE_ALPHA`
- `MULTIPLE_TESTING_METHOD`

Acceptance criteria:

- Holm correction is applied to planned primary comparison p-values.
- The output records raw and adjusted p-values.
- The output records which correction method was used.
- If paired bootstrap needs separate resampling parameters, add explicitly named
  constants to `shared/eval/constants.py` before use.
- No magic statistical parameters are embedded in analyzer functions.

## Phase 7: Interpretation Flags

Emit qualitative flags as output metadata, not as hard failures.

Required flag:

```text
mode_collapse_warning
```

Trigger:

```text
grammar_variant == "template_upper_bound" and unique_ratio_ast < 0.1
```

Required interpretation text:

```text
this cell shows mode collapse - interpret as template instantiation control,
not as evidence of grammar-constrained generation
```

Acceptance criteria:

- Mode-collapse warning appears at the cell-summary level.
- Warning does not invalidate template-upper-bound control rows.
- Warning is carried into paper-table metadata so it cannot be lost during
  markdown rendering.
- `grammar_variant="template_upper_bound"` is not treated as the task-agnostic
  grammar claim.

## Phase 8: Reporting Integration

Update reporting only enough to render the analyzer's structured output.

Acceptance criteria:

- `shared/eval/reporting/tables.py` can render the planned Table 1-3 rows.
- Table rows do not recompute statistics.
- Table rows do not rename primary metrics in a way that blurs Level 1 compile
  success and Level 2 functional success.
- Existing Cluster 2 lift-table labels remain compatible:
  `C` vs `none` is primary, `G+C` vs `G` is secondary unless the research
  contract explicitly promotes it.

## Phase 9: Contract Updates

After implementation behavior is clear, update research-facing contracts in a
small, separate documentation pass.

Required contract updates:

- `.contracts/research/eval_metrics.md`: state that the primary factorial
  analysis for Cluster 2 paper claims uses Level 2 `functional_success`, paired
  methods, and `shared/analysis/factorial.py`.
- `.contracts/research/eval_metrics.md`: state that `compile_success` factorial
  analysis is secondary structural-validity diagnostics.
- `.contracts/agentic/cluster2_contract.md`: reference
  `shared/analysis/factorial.py` as the canonical paper-table analyzer.
- `.contracts/agentic/cluster3_contract.md`: when written, reference the same
  analyzer instead of a parallel P-analysis path.
- `shared/eval/constants.py`: remains the single source of truth for statistical
  parameters.

Acceptance criteria:

- Contract updates describe the implemented behavior, not future aspirations.
- No internal agentic-only wording is promoted into research-facing docs.
- Future agents can find the canonical analyzer path from both Cluster 2 and
  Cluster 3 contracts.

## Phase 10: Test Plan

Add focused tests before relying on the analyzer for paper output.

Required tests:

- Synthetic four-cell EvalResult data with planted G, C, and G:C effects.
- Synthetic paired data where `C` improves over `none` only in known discordant
  cells.
- Synthetic paired data where `G+C` and `G` have equal outcomes.
- Partial-cell coverage with no P cells; analyzer must not crash and must mark
  P-containing cells as `not_populated`.
- Full eight-cell synthetic coverage; analyzer must include P terms and the
  three-way interaction.
- Missing `functional_success` in primary mode fails loudly.
- Mixed `scale_tier` input fails by default.
- Template-upper-bound row with `unique_ratio_ast < 0.1` emits
  `mode_collapse_warning`.
- Unpaired rows are rejected from primary Cluster 2 comparison output.
- `compile_success` analysis is labeled secondary and never becomes the default.

Targeted command:

```bash
.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -v
```

Broader shared-eval regression:

```bash
.venv/bin/python -m pytest shared/tests/test_aggregation.py shared/tests/test_eval_schema.py shared/tests/test_factorial_analysis.py -v
```

## Phase 11: Validation Passes

Run validation in three passes.

### Pass 1: Synthetic Factorial Data

Generate fake EvalResult rows for the active four cells with known effect sizes.

Acceptance criteria:

- Analyzer recovers the planted direction of G and C effects.
- Analyzer identifies the planted G:C interaction direction.
- Paired CI covers the planted paired lift under reasonable bootstrap variance.
- P-containing cells are explicitly marked `not_populated`.

### Pass 2: Existing Cluster 1 Data

Run secondary compile analysis on existing frozen Cluster 1 data:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl`

Acceptance criteria:

- Output is labeled secondary compile analysis.
- The known compile contrast is reproduced.
- No Level 2 functional claim is inferred from Cluster 1 compile-only rows.

### Pass 3: First Four-Cell Cluster 2 Dataset

After the task-agnostic G n=20 path and four-cell Cluster 2 dataset are frozen,
run primary functional analysis.

Acceptance criteria:

- Analyzer reports G main effect, C main effect, and G:C interaction for
  `functional_success`.
- Primary comparisons use matched seed pairs only.
- P-containing cells are marked `not_populated`.
- Output contains table-ready rows for Tables 1-3.
- Any nonsensical output blocks paper-table generation until fixed.

## Implementation Order

1. Add tests that encode current research semantics.
2. Refactor loader and field normalization.
3. Implement explicit response-variable modes.
4. Make paired comparison output the primary Cluster 2 path.
5. Add reduced/full design matrix detection.
6. Add structured output sections.
7. Wire constants and Holm correction.
8. Add mode-collapse interpretation flags.
9. Update reporting renderers.
10. Update contracts to describe the implemented analyzer.
11. Run validation passes.

## Stop Conditions

Stop and ask for research-owner review if any of these occur:

- Existing data cannot provide `(kernel_class, dtype, base_seed)` pair keys.
- Current Cluster 2 rows cannot distinguish replay controls from generated rows.
- `functional_success` is absent from the first paper-scale Cluster 2 dataset.
- The four active cells contain mixed `scale_tier` values.
- The analyzer needs a new metric definition not already present in
  `.contracts/research/eval_metrics.md`.
- A proposed fix requires changing generation, replay, repair, or correctness
  behavior.

## Done Definition

This fix is done when `shared/analysis/factorial.py` can run end-to-end on
current four-cell Cluster 2-shaped data, produce primary Level 2 paired
functional-success results, mark missing P cells explicitly, emit table-ready
structured output, and leave constants and contracts aligned with the research
semantics.
