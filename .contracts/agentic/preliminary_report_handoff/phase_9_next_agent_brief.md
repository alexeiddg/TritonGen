# Phase 9 Next Agent Brief

## Next Phase

Phase 10 - Cluster 3 Drift-Prevention Plan

Expected file:

- `docs/10_cluster3_drift_prevention_plan.md`

## Use As Inputs

- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `docs/00_project_map.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`

## Required Direction

- Create guardrails for future Cluster 3/P work; do not implement P.
- Preserve that current results are 2^2 only: `none`, `G`, `C`, and `G+C`.
- Preserve that Cluster 3/P and full 2^3 results are deferred.
- Use the decision log to extract inheritance rules:
  - define P before code;
  - define allowed feedback before repair loops;
  - define failure classes before routing;
  - define artifact schema and provenance before Modal execution;
  - update analyzer semantics before paper-scale runs;
  - update the artifact registry before reporting.
- Preserve artifact caveats: G/G+C are 177/180, G has `modal_image_sha=unknown`, G+C has five `F3_EVAL_PIPELINE` rows, and analyzer `metadata.reportable=false`.

## Must Not Do

- Do not claim P results.
- Do not define final P implementation details beyond supported guardrails.
- Do not quote official final statistical results while analyzer `metadata.reportable=false`.
- Do not modify outputs.
- Do not modify grammar files.
- Do not modify source code.
- Do not modify README or formal `.contracts/research/*` surfaces unless a later phase explicitly requests it.
- Do not re-record hashes.
- Do not invoke Modal, GPU jobs, generation, experiments, or analyzer rewrites.

## Phase 10 Watch Points

- The plan should prevent Cluster 3 from repeating Cluster 1/2 drift around hidden factor semantics, stale docs, mixed schemas, missing provenance, and unregistered artifacts.
- The plan should describe gates and required definitions, not final P results.
- The plan should keep analyzer reportability and artifact registration as hard report-facing requirements.
- The plan should not turn old agentic plans into citation-grade Cluster 3 methodology.
