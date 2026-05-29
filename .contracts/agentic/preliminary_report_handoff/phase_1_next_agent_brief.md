# Phase 1 Next Agent Brief

Phase 1 is complete with warnings. The created Phase 1 docs are:

- `docs/00_project_map.md`
- `docs/handoff/codebase_handoff_guide.md`
- `docs/handoff/stale_docs_inventory.md`

Next phase: Phase 2 - Artifact And Result Registry.

Expected Phase 2 file:

- `docs/05_artifacts_and_results_registry.md`

Key artifact identities from Phase 0:

| Condition | Path | Rows/status |
| --- | --- | --- |
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 valid JSONL rows |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 valid JSONL rows |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 valid JSONL rows |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 valid JSONL rows |
| analysis | `outputs/analysis/factorial_2x2_preliminary.json` | present, valid JSON, reportable=false |

Warnings to preserve:

- G and G+C are 177/180, not complete 180/180 artifacts.
- Analyzer output exists but is marked `reportable=false`.
- Current scope is the 2^2 subset: `none`, `G`, `C`, and `G+C`.
- Cluster 3/P is deferred; do not claim P results.
- Do not use old n5 artifacts for current preliminary claims.
- Template G is diagnostic/reference only, not the primary G condition.
- Cluster 1 is compile-only; do not claim Cluster 1 functional correctness.

Phase 2 should reference raw outputs by path and summarize row counts, schemas, provenance fields, caveats, and role in analysis. It must not modify output artifacts, grammar files, hashes, source code, README.md, or `.contracts/research/*`.
