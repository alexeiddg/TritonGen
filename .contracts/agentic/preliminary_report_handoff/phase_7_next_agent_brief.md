# Phase 7 Next Agent Brief

## Next Phase

Phase 8 - README And Formal Contract Alignment

Expected actions:

- Update root README navigation if the phase explicitly allows README edits.
- Update formal `.contracts/research/*` only after comparing stale claims against current `docs/`.

## Use As Inputs

- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/handoff/stale_docs_inventory.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`

## Required Direction

- Preserve the source-of-truth hierarchy from `docs/00_project_map.md`.
- Treat audits and `.contracts/agentic/` files as evidence or context, not citation-grade methodology.
- Use `docs/08_decision_log.md` to align decisions rather than copying raw audit text.
- Preserve the current 2^2 scope: none, G, C, G+C.
- Preserve Cluster 3/P deferral.
- Preserve artifact caveats: G/G+C are 177/180, G has `modal_image_sha=unknown`, G+C has five `F3_EVAL_PIPELINE` rows, and analyzer `metadata.reportable=false`.
- Preserve methodology boundaries: Cluster 1 is compile-only, C repairs only F2, F0/F1 terminate without repair, and template-G is diagnostic/reference only.

## Must Not Do

- Do not modify outputs.
- Do not modify grammar files.
- Do not modify source code.
- Do not re-record hashes.
- Do not invoke Modal, GPU jobs, generation, experiments, or analyzer rewrites.
- Do not turn audits or agentic plans directly into report-facing methodology.
- Do not write the preliminary report.

## Phase 8 Watch Points

- README and formal contracts may currently contain stale template-G, n5, token-budget, or analyzer-blocker language.
- Formal contracts should be aligned to current docs rather than used to override them.
- Analyzer `metadata.reportable=false` remains a blocker for official statistical-result prose.
- Any formal contract update must keep the artifact registry as the source for current artifact identities.
