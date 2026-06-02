# Project Documentation Map

## Purpose

This documentation set is the citation-grade frame for the preliminary Cluster 1 + Cluster 2 technical handoff. It lets a new reader understand what was built, where the evidence lives, which claims are current, and which caveats must be preserved before report prose is drafted.

This is not a research paper. The report-facing work is a traceable technical handoff that explains methodology, artifacts, decisions, and remaining risks.

## Current Documentation Status

The Phase 0-11 handoff-readiness documentation pipeline is complete.

Current drafting status: `READY_WITH_RESULTS_PLACEHOLDER`.

Preliminary statistical-result prose may proceed only from the verified reportable analyzer output at `outputs/analysis/factorial_2x2_preliminary.json` and only with the coverage, F3, P-deferred, model-fit, and provenance caveats preserved.

Post-handoff agent maintenance now has a central routing and versioning layer:

- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/code_update_documentation_policy.md`

README and the three core `.contracts/research/` files were aligned in Phase 8:

- `README.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`

Optional MLflow experiment tracking is governed by
`.contracts/research/mlflow_tracking_policy.md`; team onboarding lives at
`docs/tracking/README.md`.

## Current Report Scope

The current preliminary scope is the 2^2 subset over grammar guidance and correctness feedback:

| Report condition | Short label | Current meaning | Methodology owner |
|---|---|---|---|
| No control | `none` | Baseline/replay condition without grammar guidance or correctness-feedback repair. | `docs/05_artifacts_and_results_registry.md` |
| Grammar guidance | `G` | Cluster 1 task-agnostic grammar-guided decoding plus semantic post-validation. | `docs/02_methodology_cluster1.md` |
| Correctness feedback | `C` | Cluster 2 correctness-feedback repair restricted to F2 numerical/correctness failures. | `docs/03_methodology_cluster2.md` |
| Grammar plus correctness feedback | `G+C` | Task-agnostic G plus C. | `docs/03_methodology_cluster2.md` |

Cluster 3 and the `P` factor are deferred. P-containing cells are not current preliminary results.

## Navigation Map

Current documentation locations:

| Topic | Path | Status |
|---|---|---|
| Project map and trust policy | `docs/00_project_map.md` | Current |
| Cluster 1 methodology | `docs/02_methodology_cluster1.md` | Current |
| Cluster 2 methodology | `docs/03_methodology_cluster2.md` | Current |
| Modal infrastructure | `docs/04_modal_infrastructure.md` | Current |
| Artifact and result registry | `docs/05_artifacts_and_results_registry.md` | Current artifact source of truth |
| Failure taxonomy and evaluation ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` | Current |
| Analysis and statistics | `docs/07_analysis_and_statistics.md` | Current, with reportable analyzer and caveats |
| Decision log | `docs/08_decision_log.md` | Current |
| Preliminary report outline | `docs/09_preliminary_report_outline.md` | Current scaffold; final result values blocked |
| Cluster 3 drift-prevention plan | `docs/10_cluster3_drift_prevention_plan.md` | Current guardrails; no P implementation or results |
| Frontier feedback-loop ablation plan | `docs/11_frontier_feedback_loop_ablation.md` | Proposal only; no API, Modal, artifact, or result claims |
| Experiment observability plan | `docs/12_experiment_observability_plan.md` | Planning doc for sidecar-first cost, token, Modal context, and duration observability |
| MLflow tracking onboarding | `docs/tracking/README.md` | Current operational onboarding for optional MLflow dashboard tracking; JSONL artifacts remain the source of truth |
| Agentic repair memory strategy | `docs/13_agentic_repair_memory_strategy.md` | Strategy doc for future opt-in repair-history policy changes |
| Structural vs task outcome reporting plan | `docs/14_structural_vs_task_outcome_reporting_plan.md` | Planning doc for separating structural/code-surface metrics from task/functional metrics |
| Experiment change orchestration contract | `docs/15_experiment_change_orchestration_contract.md` | Active control-plane contract for docs 12-14 implementation sequencing, parallel work, and run gates |
| Observability sidecar implementation spec | `docs/16_observability_sidecar_implementation_spec.md` | Implementation contract for O0-O4 sidecar schema, logger, privacy, token, Modal context, and estimated cost work |
| Structural/task analyzer metadata implementation spec | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` | Implementation contract for S0-S3 outcome-family metadata, metric registry, feedback activation diagnostics, report labels, and analyzer-output compatibility |
| Agentic transcript implementation spec | `docs/18_agentic_transcript_v1_implementation_spec.md` | Implementation contract for opt-in `agentic_transcript_v1` C/P repair-history prompts, best-anchor selection, policy labels, and rollout gates |
| Experiment change orchestration state | `docs/handoff/experiment_change_orchestration_state.md` | Live operational state for docs 12-14 parallel branches, leases, gates, and run packets |
| Agentic document hub | `docs/handoff/agentic_document_hub.md` | Current agent routing index |
| Document version registry | `docs/handoff/document_version_registry.md` | Current markdown version registry |
| Code update documentation policy | `docs/handoff/code_update_documentation_policy.md` | Current code-to-doc maintenance policy |
| Codebase handoff guide | `docs/handoff/codebase_handoff_guide.md` | Current handoff guide |
| Stale-doc inventory | `docs/handoff/stale_docs_inventory.md` | Refreshed after Phase 11 |

## Source-Of-Truth Hierarchy

When sources disagree, use this hierarchy:

1. Current code and tests define actual behavior.
2. Current output artifacts define observed results.
3. `docs/` defines human-readable methodology once populated.
4. `.contracts/research/` defines formal methodology constraints.
5. `audits/` provides historical evidence and verification records.
6. `.contracts/agentic/` provides agent working context only and is not citation-grade unless promoted.

The hierarchy is a guardrail against drift. Audits, agent plans, and older summaries can be useful evidence, but they may be stale until their conclusions are promoted into `docs/` or `.contracts/research/`.

## Citation Grade Vs Evidence Grade

Citation-grade sources are intended to support report-facing claims after they are verified:

- `README.md`
- `docs/*.md`
- `.contracts/research/*.md`
- current artifact registry
- final analyzer outputs when reportable

Evidence-grade sources support reconstruction and traceability but should not be cited as the primary methodology source without promotion:

- `audits/*.md`
- git history
- test outputs
- ignored agent plans
- intermediate smoke reports
- old output summaries

## Remaining Work

- Draft preliminary result prose from the verified `metadata.reportable=true` analyzer JSON only, with all current caveats preserved.
- Keep Cluster 3/P deferred until the gates in `docs/10_cluster3_drift_prevention_plan.md` are satisfied.
- Continue treating n5, template-G, smoke, failed, and partial artifacts as non-authoritative unless promoted into `docs/05_artifacts_and_results_registry.md`.

## Staleness Warning

Audits and `.contracts/agentic/` files may contain correct historical observations, superseded blockers, or stale implementation assumptions. Treat them as evidence or context only until the relevant claim is verified against current code, tests, artifacts, and analyzer output.
