# Phase 6 Next Agent Brief

## Next Phase

Phase 7 - Decision Log Extraction

Expected file:

- `docs/08_decision_log.md`

## Use As Inputs

- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- relevant audits under `audits/`

## Required Direction

- Distill audit history into concise human-readable decisions.
- Promote decisions, reasons, evidence, and current status; do not copy raw agent prompts or raw audit prose.
- Preserve the current 2^2 scope: none, G, C, G+C.
- Preserve artifact caveats: G/G+C are 177/180, G has `modal_image_sha=unknown`, G+C has five `F3_EVAL_PIPELINE` rows, and analyzer `metadata.reportable=false`.
- Preserve methodology boundaries: Cluster 1 is compile-only, C repairs only F2, F0/F1 terminate without repair, and template G is diagnostic/reference only.

## Must Not Do

- Do not edit outputs.
- Do not edit grammar files.
- Do not edit source code.
- Do not edit README.md.
- Do not edit `.contracts/research/*`.
- Do not run Modal, GPU jobs, generation, experiments, or analyzer rewrites.
- Do not write the preliminary report.

## Candidate Decisions To Extract

- Task-agnostic G became the primary G condition.
- Template G became diagnostic/reference only.
- Cluster 1 functional success is false/unproven in preliminary functional analysis.
- C repair is F2-only; F0/F1 terminate without feedback.
- G+C is G plus C, not a new cluster.
- Frozen none/G replay controls define paired comparisons.
- G/G+C 177/180 coverage is explicit and must not be silently filled.
- Durable Modal row writing is methodology infrastructure.
- Malformed correctness payloads become `F3_EVAL_PIPELINE` rows.
- F3 policy is conservative and analyzer output remains not reportable.
