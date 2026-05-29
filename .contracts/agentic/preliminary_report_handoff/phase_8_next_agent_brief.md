# Phase 8 Next Agent Brief

## Next Phase

Phase 9 - Preliminary Report Outline

Expected file:

- `docs/09_preliminary_report_outline.md`

## Use As Inputs

- `README.md`
- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md`

## Required Direction

- Build an outline only; do not write full report prose.
- Use `docs/05_artifacts_and_results_registry.md` for artifact identities and row counts.
- Use `docs/08_decision_log.md` for decision rationale and Cluster 3 implications.
- Preserve the current 2^2 scope: `none`, `G`, `C`, and `G+C`.
- Preserve Cluster 3/P deferral.
- Preserve artifact caveats: G/G+C are 177/180, G has `modal_image_sha=unknown`, G+C has five `F3_EVAL_PIPELINE` rows, and analyzer `metadata.reportable=false`.
- Preserve methodology boundaries: Cluster 1 is compile-only, C repairs only F2, F0/F1 terminate without repair, and template-G is diagnostic/reference only.

## Must Not Do

- Do not quote official final statistical results while analyzer `metadata.reportable=false`.
- Do not modify outputs.
- Do not modify grammar files.
- Do not modify source code.
- Do not re-record hashes.
- Do not invoke Modal, GPU jobs, generation, experiments, or analyzer rewrites.
- Do not treat audits or `.contracts/agentic/` files as citation-grade report text.

## Phase 9 Watch Points

- The outline should separate supported methodology, artifact caveats, analyzer caveats, and future Cluster 3 inheritance.
- The outline should not claim full 2^3 completion or P results.
- The outline should not claim Cluster 1 functional correctness or performance/speedup results.
- If the outline includes result placeholders, mark them as non-final while `metadata.reportable=false`.
