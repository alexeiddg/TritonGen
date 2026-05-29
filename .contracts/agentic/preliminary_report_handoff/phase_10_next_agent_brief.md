# Phase 10 Next Agent Brief

## Next Phase

Phase 11 - Final Documentation Consistency Audit

Expected report:

- `audits/final_documentation_consistency_audit.md`

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
- `docs/09_preliminary_report_outline.md`
- `docs/10_cluster3_drift_prevention_plan.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`

## Required Direction

- Verify README, docs, and research contracts agree on current scope and caveats.
- Verify no unsupported final result claims were introduced.
- Verify current artifact identities, row counts, and caveats point to `docs/05_artifacts_and_results_registry.md`.
- Verify analyzer `metadata.reportable=false` remains visible wherever result prose is planned.
- Verify Cluster 3/P remains deferred and `docs/10_cluster3_drift_prevention_plan.md` is guardrails-only.

## Must Not Do

- Do not edit outputs.
- Do not edit source code.
- Do not edit grammar files.
- Do not re-record hashes.
- Do not invoke Modal, GPU jobs, generation, experiments, or analyzer rewrites.
- Do not claim official final statistical results while analyzer `metadata.reportable=false`.

## Watch Points

- Phase 11 should be read-only except for the final audit report and phase handoff updates.
- The audit should distinguish current citation-grade docs from evidence-grade audits and agentic notes.
- The audit should flag any remaining stale contradiction in README, docs, or `.contracts/research/*`.
