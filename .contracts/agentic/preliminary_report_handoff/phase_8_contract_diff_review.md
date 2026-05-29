# Phase 8 Contract Diff Review

Phase 8 aligned README and formal research contracts to the current citation-grade docs. This file is an agentic handoff record, not citation-grade methodology by itself.

| File | Old/stale claim | New aligned claim | Supporting doc | Supporting artifact/code/audit | Risk if not changed |
|---|---|---|---|---|---|
| `README.md` | Project entrypoint centered full 2^3 framing, template-G 180/180 history, old artifact paths, and command-oriented Cluster 1 status. | README is now a navigation/status entrypoint for the current 2^2 preliminary Cluster 1 + Cluster 2 handoff. It states Cluster 3/P deferral, reportable=false, 177/180 caveats, Cluster 1 compile-only boundary, and source-of-truth hierarchy. | `docs/00_project_map.md`; `docs/05_artifacts_and_results_registry.md`; `docs/08_decision_log.md` | `outputs/analysis/factorial_2x2_preliminary.json`; Phase 0 readiness audit | New readers would start from stale template-G and full-factorial framing rather than current task-agnostic 2^2 handoff state. |
| `.contracts/research/research_scope.md` | Mixed current 2^2 scope with future full 2^3 vocabulary and historical template-G 180/180 framing. | Rewritten as the current formal scope: 2^2 only; P deferred; task-agnostic G primary; template G diagnostic/reference; G acceptance is joint grammar and semantic validation; Cluster 1 compile-only; C repair F2-only; analyzer reportable=false. | `docs/00_project_map.md`; `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md`; `docs/05_artifacts_and_results_registry.md`; `docs/08_decision_log.md` | Current registry artifacts; `outputs/analysis/factorial_2x2_preliminary.json`; Phase 0 readiness audit | Formal scope would continue to license stale full-factorial, template-primary, or result-ready interpretations. |
| `.contracts/research/eval_metrics.md` | Metric contract foregrounded all-cluster/full 2^3 schema and future performance metrics without a current preliminary override. | Added current preliminary metric contract: functional_success is primary for Cluster 2/2^2 analysis; compile_success is secondary; grammar_valid is diagnostic; Cluster 1 functional_success is false/unproven; C compile_success may normalize from failure_code; no performance metric is currently reportable; analyzer reportable=false. Updated factor-label and factorial-analysis language to scope P as deferred. | `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` | `shared/analysis/factorial.py`; `shared/tests/test_factorial_analysis.py`; analyzer JSON; normalization/F3 audits | Report-facing metrics could incorrectly quote future P/speedup machinery or treat compile success as the primary correctness result. |
| `.contracts/research/scale_policy.md` | Scale policy still said task-agnostic n=20 was blocked behind n=5 gates and referenced old template/final-G artifacts as frozen artifacts. | Replaced stale n5/n20 gate with current registered n=20 artifact table; n=5 is legacy unless promoted; G/G+C are 177/180; analyzer is reportable=false; C/G+C current token budget is 2048 per registry evidence; registered artifacts own current identities. | `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` | Current artifacts; Phase 0/7 handoff evidence; artifact registry | Future agents could treat old n=5/token-budget/template artifacts as current gates or current report evidence. |

## Contracts Reviewed But Not Edited

| File | Rationale |
|---|---|
| `.contracts/README.md` | Already states audience split and agentic-doc non-citation policy; no severe current contradiction found. |
| `.contracts/research/cluster1_generated_surface.md` | Required searches did not surface current-scope contradictions. |
| `.contracts/research/paper_outline.md` | Already notes the current 2^2 subset and full-factorial deferral; Phase 9 owns the new preliminary outline. |
| `.contracts/research/modal_new_account_setup_guide.md` | Operational Modal setup guide; Phase 8 did not authorize Modal execution or broad operational rewrite. |
| `.contracts/research/phase4_parse_reclassification_disposition.md` | Historical disposition record; no current methodology rewrite needed in Phase 8. |

## Residual Risk

- `.contracts/research/eval_metrics.md` still contains future-facing Level 3/4/P sections. They are retained as future design material and scoped by the new current preliminary metric contract.
- Analyzer `metadata.reportable=false` remains unresolved and must be carried into Phase 9.
- The final report outline must continue to use the artifact registry rather than older README or contract history.
