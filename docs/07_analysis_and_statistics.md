# Analysis And Statistics

## Purpose

This document defines how current artifacts are normalized and analyzed for the preliminary 2^2 handoff. It is not the result report itself. It documents response variables, pairing rules, comparisons, statistical methods, caveats, and reportability status.

Artifact identities and row counts are governed by `docs/05_artifacts_and_results_registry.md`. The current analyzer output is reportable for the covered 2^2 scope because it records explicit paper-scale annotation, but it remains preliminary and caveated rather than a full final 2^3/P result.

## Current 2^2 Analysis Scope

The current preliminary scope is four conditions:

- none
- G
- C
- G+C

Cluster 3/P is deferred. Full 2^3 factorial completion is not current. The analyzer may support broader designs, but this documentation covers the present 2^2 subset only.

## Inputs

| Condition | Artifact path | Rows | Intended rows | Role | Caveat |
|---|---|---:|---:|---|---|
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | baseline replay / no G / no C | Cluster 1 compile-only, legacy schema/provenance |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | task-agnostic grammar condition | 3 missing matmul rows; Cluster 1 compile-only; `modal_image_sha=unknown` |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | correctness-feedback condition | no raw `compile_success`; analyzer derives it from `failure_code`; all current rows are `F0_PARSE` |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | task-agnostic grammar plus correctness feedback | 3 missing matmul rows; five `F3_EVAL_PIPELINE` rows |
| analyzer | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | N/A | preliminary analyzer output | valid JSON, `metadata.reportable=true` via `analysis_cli_annotation` |

The missing G/G+C rows are:

- matmul/fp32/base_seed=5
- matmul/bf16/base_seed=0
- matmul/bf16/base_seed=18

The legacy template-G artifact `outputs/cluster1/final_g_l4_n20.jsonl` is excluded from these inputs. It is a legacy `template_upper_bound` compile-only diagnostic artifact with 180/180 legacy compile success, but it fails the current paper-scale generation metadata gate and is not task-agnostic G. It must not be used to fill the missing task-agnostic G rows and must not be paired with the current task-agnostic G+C artifact.

The current-pipeline template G diagnostic artifact `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` now exists and is registered as non-primary compile-only evidence. It is excluded from `outputs/analysis/factorial_2x2_preliminary.json`, is not a substitute for task-agnostic G, and cannot complete a template correctness-feedback diagnostic comparison without a matching current-pipeline template G+C artifact over the same seed grid. The old legacy template artifact is not a current primary 2^2 analyzer input.

## Template Diagnostic Separation

Template upper-bound G is a diagnostic surface, not a primary factor cell in the current analyzer. It may be summarized separately as `G_template` using `grammar_variant=template_upper_bound`, but it must not be added to the current primary none/G/C/G+C table and must not change `outputs/analysis/factorial_2x2_preliminary.json`.

The current template G diagnostic can support only Cluster 1 compile and grammar-funnel discussion. A separate template G+C run is required before discussing a template C interaction or a template combined-condition diagnostic.

## Response Variables

| Variable | Role | Meaning | Caveat |
|---|---|---|---|
| `functional_success` | primary correctness outcome | whether a row passed numerical correctness evaluation | Cluster 1 rows did not run Level 2, so they normalize to false/unproven |
| `compile_success` | secondary structural outcome | whether a row passed the compile/launch gate | not equivalent to functional correctness |
| `grammar_valid` | grammar funnel diagnostic | joint GBNF parse and semantic-validator acceptance | not equivalent to compile or functional success |
| `failure_code` | failure-mode diagnostic | canonical F0/F1/F2/F3 failure family and code | artifact schemas differ; analyzer normalization owns cross-artifact interpretation |

Metric-to-question mapping:

- `functional_success` addresses whether C improves numerical correctness in C vs none and G+C vs G.
- `compile_success` addresses whether G changes structural/compile behavior in secondary diagnostic comparisons.
- `grammar_valid`, `rejection_layer`, and `failure_code` explain where generated rows fail and are diagnostic, not thesis metrics by themselves.

## Normalization Rules

The implemented analyzer normalization lives in `shared/analysis/factorial.py`.

Cluster 1:

- none and G are compile-only Cluster 1 rows.
- Cluster 1 `functional_success` normalizes to `False`/unproven because Level 2 was not run.
- Cluster 1 `compile_success` is preserved as a separate structural metric.
- `compile_success=True` is not converted to `functional_success=True`.

Cluster 2:

- C and G+C are generated Cluster 2 rows.
- `functional_success` is the primary correctness outcome.
- `compile_success` may be explicit or derived from `failure_code` where raw schema fields are absent.
- F0 and F1 imply `compile_success=False`.
- F2 implies `compile_success=True` because Level 2 was reached.
- `F3_EVAL_PIPELINE` implies `compile_success=False` unless independent Level 1 or Level 2 compile-pass evidence is present.
- Unknown or other F3-style failures are not successful compile evidence.

Conflict handling:

- Analyzer normalization validates raw `compile_success` against failure-code semantics.
- A raw value that contradicts hard F0/F1/F2 semantics is treated as an inconsistency.
- `F3_EVAL_PIPELINE` is evidence-sensitive: independent Level 1/2 evidence can support compile success, but absent that evidence it is not counted as compile success.

Compile-rate handling:

- `F3_EVAL_PIPELINE` rows are excluded from compile-success rate denominators in condition-rate summaries.
- In matched-pair analysis, an F3 row without independent compile-pass evidence is treated as `compile_success=False`.

## Pairing And Identity

Paired comparisons rely on matched experimental units. The current analyzer uses tuple identity such as `kernel_class`, `kernel_id` or equivalent kernel identity, `dtype`, and `base_seed`. Cluster 2 rows also carry replay metadata such as `replay_pair_id` where available. Raw Cluster 1 controls may require tuple matching rather than raw `replay_pair_id`.

Expected current pairs:

- C vs none: 180 pairs.
- G+C vs G: 177 pairs, due to G coverage.
- G vs none compile diagnostic: 177 matched pairs when missing G rows are skipped with an explicit coverage warning.
- G+C vs C compile diagnostic: 177 matched pairs when missing G+C rows are skipped with an explicit coverage warning.

Missing rows must be named explicitly. They must not be silently dropped or described as complete 180/180 G or G+C coverage.

Earlier pairing concerns in audits are superseded by the current analyzer output producing paired comparisons. Pairing is aligned for the covered rows, with the 177/180 G/G+C caveat preserved.

## Primary And Secondary Comparisons

| Comparison | Response | Role | Pairing | Expected pair count | Caveat |
|---|---|---|---|---:|---|
| C vs none | `functional_success` | primary C effect | matched | 180 | none/C matching required |
| G+C vs G | `functional_success` | primary C conditional-on-G effect | matched | 177 | 177/180 G and G+C coverage |
| G vs none | `compile_success` | secondary G structural effect | matched diagnostic | 177 | missing G treatment rows are skipped with coverage warning |
| G+C vs C | `compile_success` | secondary combined structural effect | matched diagnostic | 177 | missing G+C rows and F3 policy caveats |

The current analyzer output includes these comparisons and is reportable under the recorded paper-scale annotation. These comparisons still require the visible 177/180, F3, P-deferred, single-class model, and provenance caveats.

## Statistical Methods

Verified current methods from `shared/analysis/factorial.py` and `shared/eval/constants.py`:

- paired binary comparisons use an exact McNemar-style two-sided binomial test over discordant pairs,
- paired bootstrap confidence intervals are used for paired lift/difference metrics,
- bootstrap sample count is 10,000,
- bootstrap seed is 13013,
- confidence level is 95%,
- Holm correction is used for multiple comparisons,
- Wilson confidence intervals are emitted for condition rates,
- a binary logistic IRLS factorial model is available for `functional_success ~ G + C + G:C + kernel_class + dtype`.

The current functional outcome has a single observed class across the loaded rows, so the logistic model is not fit in the analyzer output. Current statistical output can be drafted only from the verified reportable analyzer JSON and only with the model-fit, coverage, F3, P-deferred, and provenance caveats attached.

## Interaction Term

The functional additive interaction is:

```text
(G+C - G) - (C - none)
```

It asks whether combining G and C produces more or less than the sum of their separate effects. The analyzer output records `interaction_additive_did=0.0` for the current functional-success data, but the logistic interaction coefficient is unavailable because the functional outcome has a single class.

Compile-success interaction language, if used later, should be treated as secondary diagnostic language and must carry the same coverage and F3 caveats.

## Analyzer Output Status

Path: `outputs/analysis/factorial_2x2_preliminary.json`

Current status:

- valid JSON,
- 714 loaded rows,
- populated cells: none, G, C, G+C,
- missing cells: P, G+P, C+P, G+C+P,
- analyzer version: `factorial_alignment_v3_f3_eval_pipeline_policy`,
- `metadata.reportable=true`,
- `metadata.scope_kind=temporary_2^2_subset`,
- `metadata.scale_tiers=["paper"]`,
- `metadata.raw_scale_tiers_before_annotation=["unspecified"]`,
- `metadata.scale_tier_source="analysis_cli_annotation"`,
- `metadata.requested_scale_tier="paper"`.

The current raw artifacts do not serialize row-level `scale_tier`; the analyzer was invoked with an explicit paper-scale annotation and records the annotation source in metadata. This is accepted for the current legacy/current 2^2 artifacts. It must not be generalized into a default rule that unspecified rows are paper scale.

## Failure-Mode And Grammar-Funnel Summaries

Current artifact failure-code distributions:

| Condition | Failure-code distribution |
|---|---|
| none | null/absent: 180 |
| G | null/absent: 3; `F1_RUNTIME`: 152; `F1_COMPILE`: 9; `F0_PARSE`: 13 |
| C | `F0_PARSE`: 180 |
| G+C | `F2_NUMERIC_NAN`: 4; `F1_RUNTIME`: 146; `F1_COMPILE`: 10; `F0_PARSE`: 12; `F3_EVAL_PIPELINE`: 5 |

Grammar-funnel diagnostics for current G/G+C artifacts:

| Condition | Rows | `grammar_active` | `grammar_valid` | `gbnf_parse_valid` | `semantic_valid` | Rejection-layer distribution |
|---|---:|---:|---:|---:|---:|---|
| G | 177 | 177 | 49 | 105 | 49 | null: 49; `semantic_validator`: 56; `gbnf_parse`: 72 |
| G+C | 177 | 177 | 52 | 100 | 52 | null: 52; `semantic_validator`: 48; `gbnf_parse`: 77 |

Stop-reason diagnostics:

| Condition | Stop-reason distribution |
|---|---|
| none | null/absent: 180 |
| G | `eos_token`: 105; `max_new_tokens`: 72 |
| C | `eos_token`: 175; `max_new_tokens`: 5 |
| G+C | `eos_token`: 100; `max_new_tokens`: 77 |

These summaries explain failure shape and grammar funnel behavior. They do not replace the primary functional-success and secondary compile-success comparisons.

## Known Analysis Caveats

- Analyzer output is `metadata.reportable=true` under explicit `analysis_cli_annotation`.
- Analyzer `scale_tiers` is `["paper"]`; raw rows were `["unspecified"]` before annotation.
- Current raw artifacts lack row-level `scale_tier`; raw artifacts were not rewritten.
- G and G+C are 177/180, not 180/180.
- G and G+C are missing matmul/fp32/base_seed=5 and matmul/bf16/base_seed=0,18.
- G+C has five `F3_EVAL_PIPELINE` rows.
- C lacks raw top-level `compile_success` and requires analyzer normalization from `failure_code`.
- G has `modal_image_sha=unknown`.
- none has legacy schema/provenance limitations.
- Cluster 1 functional success is unproven because Level 2 was not run.
- Cluster 3/P is absent and deferred.

## What This Document Does Not Claim

- It does not claim full final-paper results beyond the verified, caveated 2^2 analyzer output.
- It does not claim full 2^3/P results.
- It does not claim timing, profiling, speedup, or performance results.
- It does not claim Cluster 1 functional correctness.
- It does not claim compile success proves correctness.
- It does not claim missing rows are ignorable without caveat.

## Traceability

| Analysis concept | Code path | Test/audit path | Artifact path | Caveat |
|---|---|---|---|---|
| Artifact identities and row counts | `docs/05_artifacts_and_results_registry.md` | `audits/repository_documentation_methodology_readiness_audit.md` | all four JSONL artifacts and analyzer JSON | Registry is source of truth; raw artifacts remain in `outputs/` |
| Cluster 1 functional normalization | `shared/analysis/factorial.py`, `shared/eval/adapter_cluster1.py` | `shared/tests/test_factorial_analysis.py`, `audits/factorial_cluster1_functional_success_normalization_fix_report.md` | none and G artifacts | false means unproven for Level 2, not measured numerical failure |
| Cluster 2 compile normalization | `shared/analysis/factorial.py` | `shared/tests/test_factorial_analysis.py`, `audits/factorial_cluster2_compile_success_normalization_fix_report.md` | C and G+C artifacts | C has no raw top-level `compile_success` |
| F3 policy | `shared/analysis/factorial.py`, `cluster2/experiments/run_cluster2_modal.py` | `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`, `audits/g_plus_c_correctness_payload_failure_fix_report.md` | G+C artifact and analyzer output | five F3 rows remain visible caveats |
| Pairing identity | `shared/analysis/factorial.py` | `shared/tests/test_factorial_analysis.py`, `audits/analyzer_pre_output_verification_audit.md` | analyzer paired comparisons | tuple matching is needed for raw Cluster 1 controls |
| Statistical methods | `shared/analysis/factorial.py`, `shared/eval/constants.py` | `shared/tests/test_factorial_analysis.py` | analyzer output | current output is reportable for covered 2^2 with caveats |
| Grammar funnel | `cluster1/results/dataclass.py`, `shared/analysis/factorial.py` | `cluster1/tests/test_results.py`, `cluster1/tests/test_grammar_acceptance.py`, `shared/tests/test_factorial_analysis.py` | G and G+C artifacts | grammar_valid is diagnostic, not compile or functional success |
| Legacy template-G exclusion | `docs/05_artifacts_and_results_registry.md` | `audits/template_g_180_legacy_compatibility_audit.md` | `outputs/cluster1/final_g_l4_n20.jsonl` | diagnostic compile-only artifact; not current primary analyzer input |

## TODOs Before Report Prose Uses Final Results

- Keep final result prose tied to the verified `metadata.reportable=true` analyzer JSON.
- Verify pairing and replay identity language against final report-facing analyzer output.
- Verify hand-computed rates against the analyzer output intended for citation.
- Verify statistical-method output is citation-ready.
- Preserve the distinction between current legacy/current artifacts handled by `analysis_cli_annotation` and future artifacts that must serialize `scale_tier` in rows and registry entries.
