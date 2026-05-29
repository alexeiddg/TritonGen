# Codebase Handoff Guide

## Read First

A new agent or human should start with these files, in this order:

1. `docs/handoff/agentic_document_hub.md`
2. `docs/handoff/document_version_registry.md`
3. `docs/handoff/code_update_documentation_policy.md`
4. `docs/00_project_map.md`
5. `audits/repository_documentation_methodology_readiness_audit.md`
6. `.contracts/agentic/preliminary_report_handoff/phase_state.md`
7. `.contracts/agentic/preliminary_report_handoff/phase_0_next_agent_brief.md`
8. `.contracts/agentic/preliminary_report_handoff/phase_0_file_classification_table.md`

The Phase 0 files are handoff evidence, not citation-grade report material. Use them to locate facts and caveats, then verify against the current source-of-truth hierarchy before promoting claims.

## Working Without Hidden Chat Context

Do not rely on conversation history for methodology or artifact identity. Every claim used in a report-facing document should be recoverable from repository files.

Use this lookup map:

| Need | Location |
| --- | --- |
| Agentic routing hub | `docs/handoff/agentic_document_hub.md` |
| Document version registry | `docs/handoff/document_version_registry.md` |
| Code update documentation policy | `docs/handoff/code_update_documentation_policy.md` |
| Master workflow plan | `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` |
| Current phase state | `.contracts/agentic/preliminary_report_handoff/phase_state.md` |
| Phase 0 audit | `audits/repository_documentation_methodology_readiness_audit.md` |
| Phase 0 classification table | `.contracts/agentic/preliminary_report_handoff/phase_0_file_classification_table.md` |
| Current documentation policy | `docs/00_project_map.md` |
| Stale-doc inventory | `docs/handoff/stale_docs_inventory.md` |
| Output artifacts | `outputs/cluster1/`, `outputs/cluster2/`, `outputs/analysis/` |
| Analyzer output | `outputs/analysis/factorial_2x2_preliminary.json` |
| Formal research contracts | `.contracts/research/` |
| Cluster 1 code and tests | `cluster1/`, `cluster1/tests/` |
| Cluster 2 code and tests | `cluster2/`, `cluster2/tests/` |
| Shared analyzer and tests | `shared/`, `shared/tests/` |

## Working Rules

- Start with `git status --short`.
- Preserve the dirty worktree. Do not revert or overwrite unrelated user changes.
- Use `.venv/bin/python` for local validation or parsing.
- Do not use system Python for repository validation.
- Do not mutate `outputs/` while documenting.
- Do not modify grammar files while documenting.
- Do not run Modal unless the active phase explicitly allows it.
- Do not run GPU jobs, generation, or experiments during documentation-only phases.
- Do not update `.contracts/research/` until the phase explicitly asks for formal contract updates.
- Do not treat `.contracts/agentic/` as citation-grade methodology.

## Updating Phase State

At the end of each phase, update `.contracts/agentic/preliminary_report_handoff/phase_state.md` with:

- `current_phase`
- `last_completed_phase`
- `active_deliverables`
- `files_changed`
- `files_inspected`
- evidence used
- known blockers
- known caveats
- verification commands
- open questions
- next agent prompt

The phase state should be a compact baton. It should point to durable files and exact next actions, not summarize every detail from the audit.

## Citation Boundary

`.contracts/agentic/` files are context for agents. They may contain useful execution history, but they are not citation-grade docs unless a decision is sanitized, verified, and promoted into `docs/` or `.contracts/research/`.

Audits are evidence-grade. They can justify why a claim was promoted, but future report prose should prefer current docs, formal contracts, current artifact registries, and final analyzer outputs.
