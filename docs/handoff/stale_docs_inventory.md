# Stale Documentation Inventory

## Status

This inventory began as a Phase 0 risk map and was refreshed after the Phase 14e
four-cell n=5 matrix freeze. It now distinguishes resolved alignment work from
remaining legacy, evidence-grade, or agent-internal surfaces.

README and the three core `.contracts/research/` files were aligned in Phase 8. They are no longer treated here as unresolved blockers for preliminary report drafting.

Analyzer `metadata.reportable=true` is now recorded for the current 2^2 output under explicit scale-tier annotation. Remaining caveats are coverage, F3, P-deferred scope, model-fit, provenance, and future scale-tier serialization.

Cluster 3 Phase 0-10 local implementation and documentation work is complete
with the known Cluster 1 docs-lock warning. Phase 9 boundary tests have been
added, the focused Phase 9 latency remediation makes the Cluster 3 P sanitizer
reject `latency` as forbidden performance/timing feedback language, and Phase
10 added current methodology documentation plus a refreshed component README.
Phase 11 Modal smoke was first blocked on Modal runner hydration, leaving a
zero-row placeholder. The bounded hydration remediation archived that blocked
attempt under `outputs/cluster3/blocked/`, fixed the Cluster 3 Modal invocation
path, and generated one validated n=1 P smoke row at
`outputs/cluster3/p_smoke_l4_n1.jsonl`. Phase 12 then generated one validated
n=5 `G+P` template-grammar development artifact at
`outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`. The Phase 12 artifact is
development-scale diagnostic evidence only and observed zero `F1_COMPILE` seeds
and zero P attempts, so it is insufficient F1-loop signal. Phase 12b then
attempted two bounded targeted F1 diagnostic fixture runs, but both fixture
sources classified remotely as `F0_BAD_SIGNATURE`, produced zero rows, and are
blocked zero-row evidence only. Phase 12c locally aligned a
launcher-compatible F1 fixture. Phase 12d used that aligned fixture to validate
the remote `F1_COMPILE` -> P-loop branch at n=1. Phase 12e used an existing
wrong-output ReLU fixture to validate the remote initial `F2_NUMERIC_LARGE` ->
C-loop branch under `G+C+P` at n=1 while P remained inactive. Phase 13 froze
and audited this diagnostic matrix, Phase 13b verified commit/provenance
freeze, Phase 14 planned the smallest optional n=5 condition matrix without
execution, Phase 14a generated one validated P-only n=5 elementwise/fp32
matrix cell at `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`, and
Phase 14b generated one validated C+P n=5 elementwise/fp32 matrix cell at
`outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`. Phase 14c
generated one validated G+C+P n=5 elementwise/fp32 matrix cell at
`outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` using the
`template_upper_bound` diagnostic grammar route. Phase 14d approved reuse of
the Phase 12 `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` artifact as
the Phase 14 G+P n=5 matrix cell after comparability, schema, content-hash,
grammar-metadata, and boundary validation. Phase 14e froze the four-cell n=5
development matrix as condition coverage only, covering P, C+P, G+C+P, and
reused G+P cells with 20 total validated rows. All five Phase 14a rows are
`F0_PARSE`, with zero `F1_COMPILE` seeds and zero P attempts. All five Phase
14b rows are also `F0_PARSE`, with zero `F1_COMPILE` seeds, zero initial F2
rows, zero P attempts, and zero C attempts. All five Phase 14c rows are clean
successes, with zero `F1_COMPILE` seeds, zero initial F2 rows, zero P attempts,
and zero C attempts. The reused G+P cell also has five clean-success rows, zero
`F1_COMPILE` seeds, and zero P attempts. Across the frozen matrix, P attempts
are zero and C fires are zero. Phase 14a remains insufficient F1/P-loop signal,
and Phases 14b/14c plus the reused G+P cell remain insufficient repair signal.
None of these Cluster 3 artifacts is paper-scale, P/C-lift evidence, pass@k
evidence, statistical evidence, correctness-improvement evidence, or a
performance claim.

## Current Inventory

| Path or category | Current classification | Issue or status | Recommended action | Citation-grade? |
|---|---|---|---|---|
| `README.md` | `RESOLVED_PHASE8_AND_POST_PHASE11_REFRESHED` | Aligned to current 2^2 scope in Phase 8; Phase 9/10 links added after Phase 11. | Maintain as navigation and status entrypoint. | Yes |
| `docs/00_project_map.md` | `RESOLVED_POST_PHASE11_REFRESHED` | Older planned-page statuses were stale after docs 02-10 were created. | Use as current documentation map and trust policy. | Yes |
| `.contracts/research/research_scope.md` | `RESOLVED_PHASE8` | Aligned to 2^2 scope, Cluster 3/P deferral, task-agnostic G, Cluster 1 compile-only boundary, and Cluster 2 F2-only repair. | Keep aligned if scope changes later. | Yes |
| `.contracts/research/eval_metrics.md` | `PARTIALLY_RESOLVED_PHASE8` | Current-status preamble scopes present metrics to the 2^2 report; future P/performance material remains future-facing. | Do not treat future P/performance sections as current results. Move to a Cluster 3 contract later if needed. | Yes, with caveat |
| `.contracts/research/scale_policy.md` | `RESOLVED_PHASE8` | Aligned to current n=20 preliminary artifacts and legacy n5 policy. | Keep aligned if new artifacts are promoted. | Yes |
| `.contracts/research/paper_outline.md` | `SUPERSEDED_BY_DOCS_09` | Older outline predates the current report scaffold and artifact/reportability caveats. | Use `docs/09_preliminary_report_outline.md` for current drafting. | No for current handoff |
| `docs/09_preliminary_report_outline.md` | `AUTHORITATIVE_CURRENT_SCAFFOLD` | Current technical-report scaffold; result values may be drafted only from the verified reportable analyzer output with caveats. | Draft from this file without full 2^3/P or uncaveated final-paper claims. | Yes |
| `docs/cluster2_c_limitation_memo.md` | `AUTHORITATIVE_CURRENT_LIMITATION_MEMO` | Current thesis-facing characterization of Cluster 2 C as an operational but mixed-limitation numerical-feedback repair loop. It uses the diagnostic template G+C run for limitation analysis and does not promote template artifacts into the primary analyzer. | Use for C limitation framing in report prose; do not use as primary 2^2 artifact evidence. | Yes |
| `docs/10_cluster3_drift_prevention_plan.md` | `AUTHORITATIVE_CURRENT_GUARDRAILS` | Current Cluster 3/P guardrail doc; points to `docs/cluster3_implementation_specification.md` as the reviewed v1 implementation plan. It is a guardrail document, not P result evidence. | Use with `docs/04_methodology_cluster3.md`, the implementation specification, completed Phase 0-10 reports, and current code for Cluster 3 work. | Yes |
| `docs/04_methodology_cluster3.md` | `AUTHORITATIVE_CURRENT_CLUSTER3_METHOD` | Current Cluster 3/P v1 methodology. It documents compile-error repair scope, F1_COMPILE-only routing, F1_RUNTIME v2 deferral, schema version 1, feedback boundaries, no-P controls, and the Phase 11/12 gates. | Required reading before any broader Cluster 3/P planning; do not cite it as output evidence. | Yes |
| `cluster3/README.md` | `CURRENT_COMPONENT_README` | Component overview refreshed in Phase 10. It points to `docs/04_methodology_cluster3.md`, documents local v1 status, and keeps development-scale/paper-scale runs gated. | Use as component navigation, with `docs/04_methodology_cluster3.md` as the methodology owner. | No for result claims |
| `docs/handoff/agentic_document_hub.md` | `AGENTIC_ROUTING_CURRENT` | Central agent routing index across tracked and ignored project-owned docs. | Start agent work here; do not cite as methodology. | No |
| `docs/handoff/document_version_registry.md` | `AGENTIC_VERSION_REGISTRY_CURRENT` | Central version registry for relevant project-owned markdown files. | Update on every doc add/edit/promotion/stale-status change. | No |
| `docs/handoff/code_update_documentation_policy.md` | `AGENTIC_POLICY_CURRENT` | Defines which docs must change when code, artifacts, analysis, or methodology changes. | Apply during every code change. | No |
| `cluster1/README.md` | `STALE_COMPONENT_README` | May not cleanly present current task-agnostic G n20 artifact and caveats. | Do not cite for current report claims; refresh only in a future component-doc cleanup. | No for current handoff |
| `cluster2/README.md` | `STALE_COMPONENT_README` | May contain stale Cluster 2 readiness or artifact language. | Do not cite for current report claims; refresh only in a future component-doc cleanup. | No for current handoff |
| `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` | `AGENT_INTERNAL` | Workflow plan for agents, not report methodology. | Keep as internal execution context. | No |
| `.contracts/agentic/cluster1_contract.md` | `AGENT_INTERNAL` | Useful internal history, but not citation-grade and may contain old assumptions. | Use only as evidence/context unless promoted. | No |
| `.contracts/agentic/cluster2_contract.md` | `AGENT_INTERNAL` | Historical agent contract that may contain stale artifact or token defaults. | Use only as evidence/context unless promoted. | No |
| `.contracts/agentic/*plan*.md` | `LEGACY_EVIDENCE_OR_AGENT_INTERNAL` | Historical plans and TODOs may not match current implementation. | Keep as evidence or archive after explicit review. | No |
| `.contracts/agentic/reference/*.md` | `AGENT_INTERNAL` | Cached helper/reference material. | Do not cite without verification. | No |
| `audits/final_documentation_consistency_audit.md` | `CURRENT_EVIDENCE` | Final Phase 11 audit; identified bounded cleanup and verified current consistency. | Use as evidence for cleanup and report-readiness state. | Evidence-grade |
| Older audit reports | `LEGACY_EVIDENCE` | Important history, but some blocker statuses are superseded by current docs and analyzer output. | Cite only as evidence for historical decisions; prefer current docs for methodology. | Evidence-grade |
| Older n5 audits and summaries | `LEGACY_EVIDENCE` | Development-scale artifacts are historical and not current paper/preliminary-scale evidence. | Do not use for current report-scale claims unless promoted into the registry. | No |
| Template-G summaries and upper-bound notes | `LEGACY_EVIDENCE` | Diagnostic/reference material can be mistaken for the primary G condition. | Preserve only with explicit diagnostic/reference labels. | No |
| Old smoke, failed, and partial outputs or summaries | `LEGACY_EVIDENCE` | Smoke/failed/partial evidence is not current report-scale output. | Do not cite as current results unless explicitly promoted. | No |
| Duplicate old smoke summaries/TODO files | `DELETE_CANDIDATE_LATER` | Search noise after consolidation. | Delete only after explicit review and approval. | No |

## Resolved By Phase 8 And Post-Phase-11 Cleanup

- Root README now states current 2^2 scope, Cluster 3/P deferral, artifact paths, caveats, source-of-truth hierarchy, and links to docs 00/02/03/04/05/06/07/08/09/10.
- `.contracts/research/research_scope.md`, `.contracts/research/eval_metrics.md`, and `.contracts/research/scale_policy.md` were aligned to the current documented state in Phase 8.
- `docs/00_project_map.md` now marks docs 02-10 as current instead of planned future pages.

## Remaining Active Caveats

- Analyzer output exists at `outputs/analysis/factorial_2x2_preliminary.json` with `metadata.reportable=true` via `analysis_cli_annotation`; full 2^3/P and uncaveated final-paper prose remain out of scope.
- G and G+C are 177/180, with missing matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18.
- G has `modal_image_sha=unknown`.
- none has legacy provenance limitations.
- C requires analyzer normalization for `compile_success`.
- G+C has five `F3_EVAL_PIPELINE` rows.
- Old n5, template-G, smoke, failed, and partial artifacts remain non-authoritative unless promoted into `docs/05_artifacts_and_results_registry.md`.
- Cluster 3 has local Phase 0-10 implementation and documentation work complete
  with the known Cluster 1 docs-lock warning. Phase 11 has one validated n=1 P
  smoke artifact at `outputs/cluster3/p_smoke_l4_n1.jsonl`, but it is smoke-only
  plumbing/schema/provenance evidence. The initial zero-row blocked attempt is
  archived under `outputs/cluster3/blocked/` and remains non-evidence for smoke
  success. Phase 12 has one validated n=5 `G+P` template-grammar development
  artifact at `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`, but it
  observed zero `F1_COMPILE` seeds and zero P attempts. Phase 12b targeted F1
  attempts produced only zero-row blocked outputs because both authorized
  fixtures classified remotely as `F0_BAD_SIGNATURE`. Phase 12d produced one
  valid aligned F1/P-loop branch diagnostic row, and Phase 12e produced one
  valid initial-F2/C-loop branch diagnostic row. Phase 13 validated rows,
  sidecars, boundaries, tests, and unsupported claims; Phase 13b verified the
  clean commit/provenance freeze; Phase 14 planned a one-cell-at-a-time
  optional n=5 condition matrix; Phase 14a generated one validated P-only n=5
  matrix cell with five `F0_PARSE` rows, zero `F1_COMPILE` seeds, and zero P
  attempts; and Phase 14b generated one validated C+P n=5 matrix cell with five
  `F0_PARSE` rows, zero `F1_COMPILE` seeds, zero initial F2 rows, zero P
  attempts, and zero C attempts. Phase 14c generated one validated G+C+P n=5
  matrix cell with five clean-success rows, `template_upper_bound` diagnostic
  grammar metadata, zero `F1_COMPILE` seeds, zero initial F2 rows, zero P
  attempts, and zero C attempts. Phase 14d approved reuse of the validated
  Phase 12 G+P n=5 artifact as the Phase 14 G+P matrix cell; this is prior
  Phase 12 evidence reused with caveats, not a fresh Phase 14 run. Phase 14e
  froze the resulting four-cell n=5 development matrix with 20 total
  schema-valid rows, validated hash sidecars, clean boundary scans, and no
  disallowed completed-evidence claims. The frozen matrix remains
  development-scale condition coverage only because it has zero P attempts and
  zero C fires. Additional diagnostics, paper-scale P artifacts, and
  performance/profiler/speedup artifacts remain out of scope until later
  explicitly approved phases.

Do not use this inventory to make new methodology decisions. It is a maintenance map for stale and non-authoritative surfaces.
