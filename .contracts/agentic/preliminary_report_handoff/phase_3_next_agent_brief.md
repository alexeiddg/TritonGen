# Phase 3 Next Agent Brief

Phase 3 is complete with warnings. The created methodology document is:

- `docs/02_methodology_cluster1.md`

Next phase: Phase 4 - Cluster 2 Methodology Documentation.

Expected Phase 4 file:

- `docs/03_methodology_cluster2.md`

Use `docs/05_artifacts_and_results_registry.md` as the artifact source of truth. Current Cluster 2 artifacts:

| Condition | Path | Rows/status |
| --- | --- | --- |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 valid JSONL rows; correctness-feedback condition; no grammar |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 valid JSONL rows; task-agnostic grammar plus correctness feedback |

Warnings to preserve in Phase 4:

- Correctness feedback repair is F2-only.
- F0 parse/signature failures and F1 compile/runtime failures terminate without repair feedback.
- `G+C` is `G` plus `C`, not a separate cluster.
- G+C has the same 177/180 coverage caveat as G.
- Missing rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- Analyzer output exists but remains `metadata.reportable=false`.
- Cluster 3/P is deferred.

Phase 4 should explain Cluster 2 from current code, tests, artifacts, and the registry. It must not modify outputs, grammar files, source code, README.md, or `.contracts/research/*`, and it must not run Modal, GPU jobs, generation, or experiments.
