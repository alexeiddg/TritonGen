# Code Update Documentation Policy

Version: 1.0.0
Date: 2026-05-21
Status: active agent-facing policy
Owner: documentation maintenance agents

## Purpose

This policy defines what documentation must change when code, artifacts,
analysis, or methodology changes. The goal is to prevent stale docs by making
documentation impact part of the same work unit as the code update.

## Required Rule

Every code update must answer:

1. What behavior, artifact, schema, or claim changed?
2. Which document owns that claim today?
3. Which registry row needs a version bump?
4. Which tests, artifacts, or audits verify the new claim?
5. Which old docs now need a caveat, stale label, or promotion?

If the answer to any question is unclear, the change is not documentation-ready.

## Version Bump Rules

Use semantic versions in `docs/handoff/document_version_registry.md`.

| Bump | Use when | Examples |
|---|---|---|
| Patch | Clarifying wording, fixing links, adding evidence without changing the claim | Add a test path, fix a typo, add a verification command |
| Minor | Adding a new section, artifact entry, schema field, caveat, policy mapping, or issue pull set | Register a new output artifact, add a new failure-code policy, document a new provenance field |
| Major | Changing scope, factor definitions, source-of-truth hierarchy, artifact authority, metric semantics, or report-facing claims | Move from 2^2 to 2^3 scope, redefine C feedback, promote a new primary G artifact |

Audit files and generated output summaries are evidence snapshots. Prefer not to
rewrite them. If a snapshot is superseded, update the registry, stale-doc
inventory, and current owner docs instead of editing history.

## Code-To-Doc Mapping

| Change area | Must update | Also check | Why |
|---|---|---|---|
| Root project scope, current conditions, or report readiness | `README.md`; `docs/00_project_map.md`; `docs/08_decision_log.md`; version registry | `.contracts/research/research_scope.md`; `docs/09_preliminary_report_outline.md`; stale-doc inventory | Entry points and decision records must match the current experimental scope |
| Cluster 1 grammar, validator, constrained generation, compile validation, or G semantics | `docs/02_methodology_cluster1.md`; `cluster1/docs/grammar_surface_contract.md`; version registry | `.contracts/research/cluster1_generated_surface.md`; `.contracts/research/eval_metrics.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/08_decision_log.md`; Cluster 1 README | G claims depend on grammar, semantic validation, and compile-only boundaries |
| Cluster 1 output artifact, row count, metadata, or provenance | `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md`; version registry | `docs/02_methodology_cluster1.md`; `.contracts/research/scale_policy.md`; `README.md`; output summary docs | Artifact identity and caveats are centralized in the registry |
| Cluster 2 generation, C repair, G+C routing, replay controls, feedback prompts, result logging, or correctness validation | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/08_decision_log.md`; version registry | `.contracts/agentic/cluster2_contract.md`; `.contracts/agentic/cluster2_integrated_agent_plan.md`; `.contracts/research/eval_metrics.md`; relevant tests | C and G+C behavior are methodology-sensitive and easy to overclaim |
| Cluster 2 output artifact, row count, schema, missing rows, F3 rows, hashes, or provenance | `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md`; `docs/03_methodology_cluster2.md`; version registry | `.contracts/research/scale_policy.md`; `docs/04_modal_infrastructure.md`; `README.md`; stale-doc inventory | Report-facing artifact facts must be updated before citation |
| Shared evaluation ladder, failure taxonomy, levels, tolerances, reference runner, or schema | `docs/06_failure_taxonomy_and_eval_ladder.md`; `.contracts/research/eval_metrics.md`; version registry | `docs/03_methodology_cluster2.md`; `docs/07_analysis_and_statistics.md`; tests under `shared/tests/` | Failure-code semantics control repair eligibility and analyzer normalization |
| Analyzer normalization, paired comparisons, reportability, statistical methods, paper table generation, or model outputs | `docs/07_analysis_and_statistics.md`; `docs/05_artifacts_and_results_registry.md`; version registry | `docs/09_preliminary_report_outline.md`; `docs/08_decision_log.md`; analyzer audits; `shared/tests/test_factorial_analysis.py` | Analyzer output drives result claims and must preserve caveats |
| Modal harness, remote run setup, image provenance, content hashes, secrets policy, volumes, or durable write behavior | `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md`; version registry | `.contracts/agentic/modal_integration_plan.md`; `.contracts/agentic/modal_harness_draft.md`; `.contracts/research/scale_policy.md`; Modal audits | Remote execution and provenance are reproducibility controls |
| New raw output artifact or regenerated artifact lineage | `docs/05_artifacts_and_results_registry.md`; version registry | `docs/07_analysis_and_statistics.md`; `.contracts/research/scale_policy.md`; relevant methodology doc; audit file if verification is substantial | New artifacts are not authoritative until registered |
| Preliminary report prose or report assets | `docs/09_preliminary_report_outline.md`; `docs/preliminary_report/README.md`; version registry | `README.md`; `docs/00_project_map.md`; artifact registry; analyzer reportability status | Report text must not outrun artifact and analyzer authority |
| Cluster 3 or P-factor code, planning, metrics, or artifacts | `docs/10_cluster3_drift_prevention_plan.md`; `docs/08_decision_log.md`; version registry | future P contract; `.contracts/research/eval_metrics.md`; artifact registry only after artifacts exist | P is deferred until definitions, gates, schema, and analyzer behavior are locked |
| Documentation process, agent handoff, stale-doc policy, or central navigation | `docs/handoff/agentic_document_hub.md`; `docs/handoff/document_version_registry.md`; `docs/handoff/codebase_handoff_guide.md`; version registry | `docs/00_project_map.md`; `docs/handoff/stale_docs_inventory.md`; `.contracts/agentic/preliminary_report_handoff/phase_state.md` | Agents need one current routing layer and a durable baton |

## How To Update Docs

- Update docs in the same commit or review unit as the code change.
- State the claim, the evidence path, the caveat, and the verification command.
- Reference raw artifacts by path, row count, schema facts, hashes or metadata,
  and caveats; do not paste raw rows into methodology docs.
- Preserve the source-of-truth hierarchy. If code and docs disagree, verify code
  and tests first, then update docs.
- Promote research-relevant conclusions from `audits/` or `.contracts/agentic/`
  into `docs/` or `.contracts/research/` before using them in report prose.
- Mark superseded docs as historical in the stale-doc inventory instead of
  deleting them without explicit review.
- Do not re-record hashes or change output artifacts during documentation-only
  work.

## Required Checklist For Any Code Change

Include this checklist in the agent's working notes before finalizing:

```text
Documentation impact:
- Behavior changed:
- Artifact/schema changed:
- Methodology claim changed:
- Docs updated:
- Registry version bumps:
- Stale docs/caveats updated:
- Verification command:
```

If all entries are `none`, say why the change has no documentation impact.

## Stop Conditions

Stop and ask for direction before continuing when:

- a code change would change the current 2^2 scope or make P current,
- a new artifact conflicts with the registered artifact identities,
- analyzer output becomes reportable or unreportable for a new reason,
- source-of-truth docs disagree about factor definitions,
- generated output would need manual rewriting to match docs,
- or a documentation-only request appears to require GPU, Modal, or experiment
  execution.
