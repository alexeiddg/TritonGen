# Preliminary Report Draft Write Report

Date: 2026-05-22
Repository: `/Users/alexeidelgado/Desktop/TritonGen`
Report path: `docs/preliminary_report/preliminary_report.md`

## 1. Inputs read

Read the required core docs: `README.md`, `docs/00_project_map.md`, `docs/02_methodology_cluster1.md`, `docs/03_methodology_cluster2.md`, `docs/04_modal_infrastructure.md`, `docs/05_artifacts_and_results_registry.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `docs/07_analysis_and_statistics.md`, `docs/08_decision_log.md`, `docs/09_preliminary_report_outline.md`, and `docs/10_cluster3_drift_prevention_plan.md`.

Read the required research contracts: `.contracts/research/research_scope.md`, `.contracts/research/eval_metrics.md`, and `.contracts/research/scale_policy.md`.

Read the current preliminary report assets: `docs/preliminary_report/index.html` and `docs/preliminary_report/README.md`.

Read the analyzer output: `outputs/analysis/factorial_2x2_preliminary.json`.

Read and verified the four current primary raw artifacts read-only: `outputs/cluster1/baseline_repaired_l4_n20.jsonl`, `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, `outputs/cluster2/c_paper_n20_l4.jsonl`, and `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.

Read the relevant audits present in the repository: `audits/final_documentation_consistency_audit.md`, `audits/scale_tier_docs_contract_alignment_fix_report.md`, `audits/cross_pipeline_reportability_alignment_audit.md`, `audits/template_g_180_legacy_compatibility_audit.md`, and `audits/c1_c2_evaluation_surface_audit.md`.

Read handoff/hub files present under `docs/handoff/`: `agentic_document_hub.md`, `document_version_registry.md`, and `code_update_documentation_policy.md`.

## 2. Analyzer metadata verified

Verified directly with `.venv/bin/python`:

| Field | Value |
|---|---|
| Valid JSON | true |
| Top-level keys | `cell_summaries`, `condition_rates`, `diagnostics`, `factorial_model`, `metadata`, `paired_comparisons`, `paper_tables` |
| `metadata.reportable` | `True` |
| `metadata.scale_tiers` | `["paper"]` |
| `metadata.scale_tier_source` | `analysis_cli_annotation` |
| `metadata.raw_scale_tiers_before_annotation` | `["unspecified"]` |
| `diagnostics.rows_loaded` | `714` |
| Populated cells | `none`, `G`, `C`, `G+C` |
| Missing cells | `P`, `G+P`, `C+P`, `G+C+P` |
| Analyzer version | `factorial_alignment_v3_f3_eval_pipeline_policy` |

`metadata.rows_loaded` is absent; the loaded-row count is recorded under `diagnostics.rows_loaded`.

## 3. Artifact counts verified

Verified directly with `.venv/bin/python`:

| Condition | Artifact | Valid rows | Bad JSON | Key counts |
|---|---|---:|---:|---|
| `none` | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 0 | `compile_success=false` 180; `functional_success` absent/null 180; no current revision/image provenance |
| `G` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 0 | `compile_success=true` 3; `F1_RUNTIME` 152; `F1_COMPILE` 9; `F0_PARSE` 13; `grammar_variant=task_agnostic` 177 |
| `C` | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 0 | `failure_code=F0_PARSE` 180; `functional_success=false` 180; raw `compile_success` absent/null 180 |
| `G+C` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 0 | `compile_success=true` 4; `functional_success=false` 177; `F2_NUMERIC_NAN` 4; `F3_EVAL_PIPELINE` 5 |

Coverage by cell confirmed the known missing rows for both `G` and `G+C`: matmul/fp32 seed 5, matmul/bf16 seed 0, and matmul/bf16 seed 18.

## 4. Result numbers used

Condition rates came from `condition_rates` in the analyzer output:

| Condition | Compile success used | Functional success used |
|---|---:|---:|
| `none` | 0/180, Wilson [0.0, 0.020895497921613035] | 0/180, Wilson [0.0, 0.020895497921613035] |
| `G` | 3/177, Wilson [0.005780703080104099, 0.048639665373415256] | 0/177, Wilson [0.0, 0.021242135767677934] |
| `C` | 0/180, Wilson [0.0, 0.020895497921613035] | 0/180, Wilson [0.0, 0.020895497921613035] |
| `G+C` | 4/172 condition-rate denominator, Wilson [0.009080035264397483, 0.058261642290546374]; matched analysis 4/177 | 0/177, Wilson [0.0, 0.021242135767677934] |

The prompt's expected target table listed G+C compile success as 4/177. The analyzer condition-rate output uses 4/172 because five `F3_EVAL_PIPELINE` rows are excluded from the compile-rate denominator. The report states both the condition-rate denominator and the matched-analysis denominator.

Paired comparisons came from `paired_comparisons`: `C` vs `none` functional p=1.0, `G+C` vs `G` functional p=1.0, `G` vs `none` compile p=0.25 / Holm p=0.25, and `G+C` vs `C` compile p=0.125 / Holm p=0.25.

## 5. Claims avoided

The report intentionally avoids claims of full 2^3 completion, P/Cluster 3 results, performance or speedup results, frontier-model results, RL/fine-tuning results, Cluster 1 measured functional correctness, template `G` as primary `G`, old template 180/180 as current-pipeline evidence, G/G+C as 180/180, C repairing F0/F1, Modal by itself guaranteeing reproducibility, and compile success implying numerical correctness.

## 6. C1/C2 audit dependency status

`audits/c1_c2_evaluation_surface_audit.md` is present and was incorporated into Section 3.5.

Audit classifications used:

- Cluster 1: `C1_COMPILE_ONLY_BY_DESIGN`
- Cluster 2: `C2_FULL_LEVEL0_LEVEL1_LEVEL2_WITH_F2_REPAIR`
- C1/C2 asymmetry: `ASYMMETRY_ACCEPTED_COMPILE_ONLY_DESIGN` plus `ASYMMETRY_REQUIRES_REPORT_CAVEAT`
- Metrics: `METRICS_APPROPRIATE_FOR_CURRENT_COMPILE_AND_CORRECTNESS_SCOPE` plus `METRIC_CONCERNS_REQUIRE_CAVEATS`

The report now states that Cluster 1 uses Level 0-style parse/signature checks plus Triton import/JIT/dummy-launch compile acceptance and then stops before Level 2. It also states that Cluster 2 evaluates generated `C` and `G+C` rows through Level 0, Level 1, and Level 2 with F2-only repair. The report explicitly frames Cluster 1 `functional_success` normalization as a conservative lower bound that may undercount any numerically correct kernels among the three `G` compile-success rows.

## 7. Files created/updated

Created:

- `docs/preliminary_report/preliminary_report.md`
- `audits/preliminary_report_draft_write_report.md`

No raw artifacts, analyzer output, source code, grammar files, or contracts were modified.

## 8. Remaining caveats

- `G` and `G+C` are 177/180.
- Missing rows are matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18.
- G+C has five `F3_EVAL_PIPELINE` rows.
- Cluster 1 does not directly measure Level 2 functional correctness.
- Cluster 1 functional success is normalized false/unproven for preliminary analysis.
- `G` has `modal_image_sha=unknown` but has fallback Modal image provenance SHA.
- `none` has legacy schema/provenance gaps.
- Raw rows still lack row-level `scale_tier`; analyzer reportability relies on `analysis_cli_annotation`.
- The functional logistic model is not fit because all functional outcomes are zero.
- Template G remains legacy diagnostic/reference only.
- Cluster 3/`P`, full 2^3, frontier models, and performance metrics remain future work.

## 9. Recommendation

`READY_FOR_HUMAN_REVIEW`

The report is complete for human review using verified analyzer numbers and the C1/C2 Evaluation Surface Audit classifications.
