# Phase 4 Next Agent Brief

Next phase: Phase 5 - Evaluation Ladder, Failure Taxonomy, And Analyzer Semantics.

Expected files:

- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`

Use these current citation-grade docs first:

- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/05_artifacts_and_results_registry.md`

Key artifact facts to preserve:

| Condition | Artifact | Rows | Caveat |
|---|---|---:|---|
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | compile-only control; functional correctness unproven |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | task-agnostic G; missing three matmul rows |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | C lacks raw top-level `compile_success`; analyzer normalization required |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | missing three matmul rows; five `F3_EVAL_PIPELINE` rows |
| analyzer | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | valid JSON but `metadata.reportable=false` |

Phase 5 must preserve:

- Cluster 1 `functional_success=false/unproven` normalization.
- Cluster 2 `compile_success` normalization from explicit fields and failure-code policy.
- F2-only correctness-feedback repair.
- F0/F1 no-feedback termination.
- `F3_EVAL_PIPELINE` as an evaluation-pipeline/infrastructure failure policy that remains denominator failure unless independently proven otherwise.
- 177/180 G and G+C coverage; missing rows are matmul/fp32/base_seed=5 and matmul/bf16/base_seed=0,18.
- Current analyzer output must not be treated as reportable while `metadata.reportable=false`.

Phase 5 must not:

- Modify output artifacts.
- Modify source code.
- Modify grammar files.
- Modify README.md.
- Modify `.contracts/research/*`.
- Run Modal, GPU jobs, generation, or experiments.
