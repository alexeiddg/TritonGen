# Template G Legacy Registry/Docs Alignment Fix Report

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `ALIGNMENT_FIX_COMPLETE_WITH_WARNINGS`

## 1. Executive summary

The old template-G artifact `outputs/cluster1/final_g_l4_n20.jsonl` is now documented in the current registry and methodology surfaces as legacy diagnostic / `template_upper_bound` / compile-only / non-primary evidence only.

The current primary G status is preserved: task-agnostic G remains `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, with 177/180 coverage and the known missing matmul rows. The old template artifact is explicitly excluded from the current primary 2^2 analyzer, cannot fill missing task-agnostic G rows, and cannot pair with current task-agnostic G+C.

No raw JSONL artifacts, analyzer outputs, source code, grammar files, manifests, or hashes were modified. The only `cluster1/` change is the allowed documentation file `cluster1/README.md`.

## 2. Files updated

- `docs/05_artifacts_and_results_registry.md`
- `docs/02_methodology_cluster1.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `README.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`
- `cluster1/README.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `audits/template_g_legacy_registry_docs_alignment_fix_report.md`

## 3. Template artifact status now documented

`docs/05_artifacts_and_results_registry.md` now has a dedicated legacy template-G diagnostic entry for `outputs/cluster1/final_g_l4_n20.jsonl`.

Documented status:

- legacy diagnostic / `template_upper_bound`;
- compile-only reference;
- 180 rows;
- 180/180 legacy `compile_success=true`;
- fails the current paper-scale generation metadata gate;
- not primary G;
- not task-agnostic G;
- not Level 2 correctness evidence;
- not a current 2^2 analyzer input;
- not pairable with current task-agnostic G+C;
- not usable to fill missing task-agnostic G rows.

## 4. Current primary G status preserved

Current primary G remains task-agnostic:

- Current G artifact: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`.
- Current G rows: 177/180.
- Current G+C artifact: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.
- Current G+C rows: 177/180.
- Missing rows remain `matmul/fp32` seed 5 and `matmul/bf16` seeds 0 and 18.

The registry, methodology doc, analysis/statistics doc, decision log, preliminary report outline, README, research contracts, Cluster 1 README, and handoff hub all keep task-agnostic G as the current primary G surface.

## 5. Invalid claims removed

The updated current docs now reject these claims:

- old template G is current primary G;
- old template G is task-agnostic G evidence;
- old template G can fill the three missing task-agnostic G rows;
- old template G can pair with current task-agnostic G+C;
- old template G supports Level 2 functional correctness;
- old template G belongs in the current primary 2^2 analyzer;
- old template G is current paper-scale metadata-compliant evidence.

`cluster1/README.md` was rewritten from a template-result-forward component page into a current-status component summary. It now points to `docs/02_methodology_cluster1.md` and `docs/05_artifacts_and_results_registry.md` for current primary G status.

## 6. Scale-tier/reportability status preserved

The current analyzer status remains aligned with the scale-tier docs/contracts fix:

- `metadata.reportable=true`;
- `metadata.scale_tiers=["paper"]`;
- `metadata.raw_scale_tiers_before_annotation=["unspecified"]`;
- `metadata.scale_tier_source="analysis_cli_annotation"`;
- `metadata.requested_scale_tier="paper"`;
- `diagnostics.rows_loaded=714`.

The raw JSONL artifacts were not rewritten. Future rows must still persist `scale_tier` in row schema and registry/manifest entries.

## 7. Validation commands and results

Required pre-edit searches were run:

```text
rg "final_g_l4_n20|template_upper_bound|template G|template-G|template grammar|180/180|upper-bound|upper bound" README.md docs .contracts cluster1 audits outputs -u
rg "primary G|task_agnostic|task-agnostic|diagnostic/reference|legacy diagnostic|non-primary|current primary" README.md docs .contracts cluster1 audits -u
rg "reportable=true|analysis_cli_annotation|scale_tier|scale-tier|reportable=false" README.md docs .contracts audits -u
```

Local artifact parsing used `.venv/bin/python`:

```text
outputs/cluster1/final_g_l4_n20.jsonl rows=180
compile_success=True rows=180
condition_present=0
grammar_variant_present=0
generated_metadata_present=0
functional_success_present=0
scale_tier_present=0
all 9 kernel/dtype cells have 20 rows
```

Legacy validation:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/final_g_l4_n20.jsonl --condition G --kernel-class all --n 20
```

Result: `PASS`; row count 180, observed legacy grammar variant `template_upper_bound`, no missing cells.

Current metadata gate:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/final_g_l4_n20.jsonl --condition G --kernel-class all --n 20 --require-generation-metadata
```

Result: expected `FAIL`; `generation_metadata_failures=180`.

Analyzer metadata verification:

```text
.venv/bin/python analyzer metadata read
```

Result: `reportable=True`, `scale_tiers=['paper']`, `scale_tier_source=analysis_cli_annotation`, `rows_loaded=714`.

Post-edit stale-claim search:

```text
rg "final_g_l4_n20|template.*180/180|template_upper_bound|template G|primary G|task-agnostic G" README.md docs .contracts cluster1/README.md
rg "reportable=false|metadata.reportable=false|blocked while analyzer|until reportability is resolved" README.md docs .contracts/research
```

Result: current `README.md`, `docs/`, `.contracts/research/`, and `cluster1/README.md` hits classify template G as diagnostic/reference and task-agnostic G as current primary. The only stale-looking `.contracts` hit was `.contracts/agentic/cluster2_contract.md`, which is historical agent-internal context and outside the allowed edit set. No stale `reportable=false` hits remain in current docs/contracts.

No forbidden artifact/source/analyzer changes:

```text
git diff -- outputs shared cluster1 cluster2
```

Result: output is limited to the allowed documentation file `cluster1/README.md` under `cluster1/`; no `outputs/`, `shared/`, cluster source, grammar, analyzer output, or `cluster2/` source changes were present.

## 8. Remaining caveats

- `.contracts/agentic/cluster2_contract.md` still contains historical template replay-control language. It is agent-internal, explicitly non-citation-grade under the current source-of-truth policy, and outside this task's allowed edit set.
- Old output summaries under `outputs/cluster1/` still contain historical 180/180 template-result prose. They are generated output summaries and remain non-authoritative unless promoted through `docs/05_artifacts_and_results_registry.md`.
- A fair template diagnostic comparison still requires current-pipeline template G and matching template G+C artifacts, analyzed separately as non-primary diagnostics.
- Current primary G/G+C coverage remains 177/180.

## 9. Next recommendation

`PROCEED_TO_RESULTS_SECTION_DRAFT`
