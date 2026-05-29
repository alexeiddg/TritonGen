# Phase 0 Next Agent Brief

Phase 0 is complete with warnings. The current audit is:

`audits/repository_documentation_methodology_readiness_audit.md`

Important current facts:

- Current report scope is the temporary 2^2 subset: `none`, `G`, `C`, `G+C`.
- Cluster 3/P is deferred; P-containing cells are not populated.
- Current primary G is task-agnostic grammar-guided decoding plus semantic post-validation.
- Template G is diagnostic/reference only.
- Cluster 1 is compile-only; functional correctness is false/unproven in the analyzer.
- Cluster 2 implements C and G+C; repair feedback is F2-only, while F0/F1 terminate without feedback.
- Modal is methodology infrastructure for generation/evaluation/provenance/durable rows.
- Current artifacts:
  - `outputs/cluster1/baseline_repaired_l4_n20.jsonl`: 180 rows.
  - `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`: 177 rows.
  - `outputs/cluster2/c_paper_n20_l4.jsonl`: 180 rows.
  - `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`: 177 rows.
  - `outputs/analysis/factorial_2x2_preliminary.json`: present and valid.
- Analyzer output has `metadata.reportable=false`. Preserve that caveat.
- G/G+C missing rows are matmul/fp32/base_seed=5 and matmul/bf16/base_seed=0,18.
- F3 policy now exists in analyzer metadata: `F3_EVAL_PIPELINE` rows are excluded from compile-success rates and treated as compile false in matched-pair analysis when independent compile-pass evidence is absent.

Recommended Phase 1 files:

- `docs/00_project_map.md`
- `docs/01_research_story.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/handoff/stale_docs_inventory.md`

Do not modify `outputs/`, grammar files, hashes, or source code in Phase 1 unless explicitly asked. Do not run Modal, generation, GPU jobs, or experiments.
