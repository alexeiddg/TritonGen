# Phase 2 Next Agent Brief

Phase 2 is complete with warnings. The created registry is:

- `docs/05_artifacts_and_results_registry.md`

Next phase: Phase 3 - Cluster 1 Methodology Documentation.

Expected Phase 3 file:

- `docs/02_methodology_cluster1.md`

Use the artifact registry as the artifact source of truth. Current registered artifacts:

| Condition | Path | Rows/status |
| --- | --- | --- |
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 valid JSONL rows; compile-only; legacy flat schema |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 valid JSONL rows; task-agnostic grammar; compile-only |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 valid JSONL rows |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 valid JSONL rows |
| analysis | `outputs/analysis/factorial_2x2_preliminary.json` | valid JSON; 714 loaded rows; `metadata.reportable=false` |

Warnings to preserve in Phase 3:

- Cluster 1 is compile-only. Do not claim functional correctness for none or G.
- G is task-agnostic grammar-guided generation plus semantic post-validation.
- Template G is diagnostic/reference only, not the primary G condition.
- G has 177/180 coverage, not 180/180.
- Missing G rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- Analyzer output exists but remains `metadata.reportable=false`.
- Cluster 3/P is deferred.

Phase 3 should explain Cluster 1 methodology from current code, tests, artifacts, and the registry. It must not modify outputs, grammar files, source code, README.md, or `.contracts/research/*`, and it must not run Modal, GPU jobs, generation, or experiments.
