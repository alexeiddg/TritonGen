# Project Documentation Map

## Purpose

This map orients a research committee reviewer to the current TritonGen
repository. The current handoff is results-and-pipeline focused: include the
evidence rows, the code that produced them, and concise docs that explain how to
read the repository. Do not use agentic routing notes, execution packets, or
spec-driven development plans as primary committee-facing documentation.

## Current Handoff Status

Current candidate inventory:

```text
docs/results/research_committee_candidate_inventory.md
```

That inventory supersedes the older preliminary-report framing for current
cut-list decisions. It records:

- tracked diff versus `main`,
- untracked docs/audits,
- ignored output directories,
- row counts,
- artifact sizes,
- `git check-ignore` status,
- recommended include/exclude lists for the final branch.

The older `docs/paper_draft/` and `paper_figures/` paths are excluded from the
candidate handoff.

## Current Result Scope

| Stream | Scope | Committee interpretation |
| --- | --- | --- |
| Modal / Qwen2.5-Coder-7B-AWQ | 2,040 / 2,160 rows across `l2b_n20_attempt2*` | Primary Level-2 evidence for the Modal pipeline. Primary grammar-off plus task-agnostic rows are 1,360 / 1,440 and currently have 0 functional successes. |
| Fireworks / MiniMax M2 | 2,160 / 2,160 rows in the combined validated JSONL | Separate full-coverage stream using a shallower 15-shape compile-and-run endpoint. Not directly comparable to Modal functional success. |

The canonical analyzer is blocked for both current streams by schema/metric
gaps. Current row-count and outcome statements are direct JSONL aggregation with
explicit response-variable caveats.

## Committee Navigation Map

Use these files first:

| Topic | Path | Status |
| --- | --- | --- |
| Candidate inventory and cut-list | `docs/results/research_committee_candidate_inventory.md` | Current source of truth for branch selection |
| Root overview | `README.md` | Current committee-facing entrypoint |
| This map | `docs/00_project_map.md` | Current navigation and trust policy |
| Cluster 3 G/C/P methodology | `docs/04_methodology_cluster3.md` | Current methodology owner for the full factorial pipeline |
| Modal infrastructure and provenance | `docs/04_modal_infrastructure.md` | Current background for Modal execution/provenance |
| Failure taxonomy and evaluation ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` | Current outcome semantics |
| Analyzer and statistics semantics | `docs/07_analysis_and_statistics.md` | Useful for analyzer behavior and caveats; older sections may describe the preliminary 2^2 state |
| Codebase handoff guide | `docs/handoff/codebase_handoff_guide.md` | Developer navigation; not a result source |
| Optional tracking notes | `docs/tracking/README.md` | Optional observability/tracking context |

Research-facing contracts that may be useful:

| Topic | Path |
| --- | --- |
| Research scope | `.contracts/research/research_scope.md` |
| Evaluation metrics | `.contracts/research/eval_metrics.md` |
| Scale policy | `.contracts/research/scale_policy.md` |
| MLflow tracking policy | `.contracts/research/mlflow_tracking_policy.md` |

## Internal Or Historical Material

The following categories are not primary committee-facing docs:

| Category | Examples | Handoff rule |
| --- | --- | --- |
| Agentic contracts | `.contracts/agentic/**` | Exclude unless a maintenance audit requires them. |
| Execution packets | `docs/experiment_packets/**` | Exclude from committee docs; they are authorization history. |
| Implementation/spec plans | `docs/implementation_plans/**`, `docs/12_*` through `docs/19_*` | Exclude unless a reviewer asks for development history. |
| Agent routing/version files | `docs/handoff/agentic_*`, `docs/handoff/document_version_registry.md`, `docs/handoff/experiment_change_orchestration_state.md` | Internal maintenance context. |
| Audits | `audits/*.md` | Evidence-grade history. Promote conclusions into `docs/` before using them as primary docs. |
| Paper leftovers | `docs/paper_draft/`, `paper_figures/` | Exclude from final branch. |

## Source-Of-Truth Hierarchy

When sources disagree, use this hierarchy:

1. Current code and tests define implemented behavior.
2. Current JSONL output artifacts define observed results.
3. `docs/results/research_committee_candidate_inventory.md` defines the current
   cut-list and inventory.
4. Current methodology docs in `docs/` define human-readable interpretation.
5. `.contracts/research/` defines research-facing policy constraints.
6. `audits/` provides historical evidence and verification records.
7. Agentic/internal documents provide maintenance context only.

## Remaining Work Before Final Branch

- Review and approve the include/exclude policy in
  `docs/results/research_committee_candidate_inventory.md`.
- Create a final branch from `main` only after the cut-list is accepted.
- Selectively add ignored result evidence rather than broadly unignoring
  `outputs/`.
- Run only local verification unless explicit execution authorization is given.
