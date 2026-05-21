# TritonGen

TritonGen studies control mechanisms for LLM-generated Triton GPU kernels. The
current documented state is a preliminary Cluster 1 + Cluster 2 handoff
readiness package. It is not yet a final research paper and it does not claim
official final statistical results.

## Current Scope

The current preliminary scope is the 2^2 subset over grammar guidance and
correctness feedback:

| Condition | Meaning | Current artifact |
| --- | --- | --- |
| `none` | no grammar, no correctness repair | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| `G` | task-agnostic grammar-guided decoding plus semantic post-validation | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| `C` | correctness-feedback repair only | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| `G+C` | task-agnostic G plus C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |

Cluster 3 and the `P` factor are deferred. Full 2^3 factorial results are not
complete and should not be described as current results.

## Documentation Map

Use these docs as the current report-facing navigation layer:

| Topic | Path |
| --- | --- |
| Project map and trust policy | `docs/00_project_map.md` |
| Cluster 1 / G methodology | `docs/02_methodology_cluster1.md` |
| Cluster 2 / C and G+C methodology | `docs/03_methodology_cluster2.md` |
| Modal infrastructure and provenance | `docs/04_modal_infrastructure.md` |
| Artifact and result registry | `docs/05_artifacts_and_results_registry.md` |
| Failure taxonomy and evaluation ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` |
| Analysis and statistics semantics | `docs/07_analysis_and_statistics.md` |
| Decision log | `docs/08_decision_log.md` |
| Codebase handoff guide | `docs/handoff/codebase_handoff_guide.md` |
| Stale-doc inventory | `docs/handoff/stale_docs_inventory.md` |

The artifact registry is the source of truth for current artifact identities,
row counts, schema caveats, and analyzer status.

## Important Caveats

- `G` and `G+C` are 177/180 artifacts, not complete 180/180 artifacts.
- Missing `G` and `G+C` rows are `matmul/fp32` seed 5 and `matmul/bf16` seeds
  0 and 18.
- `outputs/analysis/factorial_2x2_preliminary.json` exists and loads 714 rows,
  but `metadata.reportable=false`; it is inspectable evidence, not an official
  final statistical result.
- Cluster 1 is compile-only. It does not run Level 2 numerical correctness and
  does not claim functional correctness.
- Template G and `template_upper_bound` artifacts are diagnostic/reference only.
  Current primary G is task-agnostic.
- Old n=5, template, smoke, failed, and partial artifacts are non-authoritative
  unless promoted into `docs/05_artifacts_and_results_registry.md`.
- No performance, timing, profiling, or speedup result is currently claimed.

## Source Of Truth

When sources disagree, use this hierarchy:

1. Current code and tests define actual behavior.
2. Current output artifacts define observed results.
3. `docs/` defines human-readable methodology.
4. `.contracts/research/` defines formal methodology constraints.
5. `audits/` provides historical evidence and verification records.
6. `.contracts/agentic/` provides agent working context only.

Audits and agentic notes can explain history, but they are not citation-grade
methodology unless their conclusions have been promoted into `docs/` or
`.contracts/research/`.

## Handoff Workflow

The phased handoff state lives at:

```text
.contracts/agentic/preliminary_report_handoff/phase_state.md
```

Files under `.contracts/agentic/` are context for agents and future maintenance.
They are not report-facing sources by themselves.
