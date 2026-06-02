# Document Version Registry

Registry version: 1.45.0
Date: 2026-06-02
Status: active agent-facing registry
Owner: documentation maintenance agents

## Purpose

This registry versions the project-owned markdown knowledge base, including
ignored files under `docs/`, `audits/`, `outputs/`, and `.contracts/agentic/`.
It is the non-invasive versioning layer for documents that do not carry their
own front matter.

Vendored or duplicated markdown under `.venv/`, `.pytest_cache/`, and
`.claude/worktrees/` is intentionally excluded.

## Versioning Model

Each row below is a versioned document record. Existing files are assigned a
baseline version as of 2026-05-21. Future edits must bump the row version and
add a concise change note.

| Class | Meaning |
|---|---|
| `CITATION_CURRENT` | Current report-facing or handoff source after verification |
| `FORMAL_CONTRACT` | Formal methodology contract under `.contracts/research/` |
| `AGENT_POLICY` | Agent-facing policy, routing, version, or handoff control |
| `AGENT_INTERNAL` | Agent plan, prompt, reference cache, or operational context |
| `EVIDENCE_SNAPSHOT` | Audit or investigation record; preserve as historical evidence |
| `OUTPUT_SUMMARY` | Generated output summary; authority depends on artifact registry |
| `COMPONENT_DOC` | Component README or local component doc |
| `LEGACY_OR_SUPERSEDED` | Useful historical document that is not current authority |

Version bump rules are defined in
`docs/handoff/code_update_documentation_policy.md`.

## Registry Changelog

| Version | Date | Change |
|---|---|---|
| 1.45.0 | 2026-06-02 | Registered the Agentic Transcript v1 docs-only checkpoint report, confirming spec/readiness alignment, A0 readiness, boundary/non-goal verification, worktree caveats, and no-code/no-output mutation before implementation starts. |
| 1.44.0 | 2026-06-01 | Added the Agentic Transcript v1 ready-to-implement kickoff state with the active branch/worktree, first A0 package, allowed/forbidden A0 files/actions, required A0 proof, and current targeted validation command. |
| 1.43.0 | 2026-06-01 | Added Agentic Transcript v1 implementation-discipline gates for commit/package slicing, commit-message template, per-package exit checklist, rollback independence, A2/A3 config precedence, and no-opportunistic-cleanup policy. |
| 1.42.0 | 2026-06-01 | Added final Agentic Transcript v1 plan gates for the A1 fixture acceptance manifest, legacy C/P byte-invariance snapshots, prompt-core import isolation, A2/A3 metadata nullability matrix, CLI/API/default tests, and A5 mixed-policy analyzer quarantine fixture. |
| 1.41.0 | 2026-06-01 | Hardened the Agentic Transcript v1 implementation spec after targeted research cross-checks, adding explicit policy-config validation, canonical prompt grammar, public-evidence-only ranking, source/failure delimiters, active repair eligibility, and additional A1 drift-prevention tests. |
| 1.40.0 | 2026-06-01 | Added final A-stream implementation planning gates to the Agentic Transcript v1 spec: spec-only checkpoint, A0.5 preflight, fixture-first A1 gate, legacy/migration classification plan, implementation stop triggers, and A1 review checkpoint. |
| 1.39.0 | 2026-05-31 | Hardened the Agentic Transcript v1 implementation spec with evidence-completeness rules, source-record and duplicate-hash handling, seed-candidate semantics, resume constraints, prompt-injection fixtures, typed fail-closed errors, sanitizer boundaries, prompt/history hash definitions, artifact-mixing policy, and expanded metadata/tests. |
| 1.38.0 | 2026-05-31 | Added the Agentic Transcript v1 implementation spec, resolved the remaining A-stream prompt-budget/latest-source/P-to-C provenance decisions, routed A0-A6 work through the project map, hub, contract, and live state, and recorded the readiness validation audit for LLM repair memory. |
| 1.37.0 | 2026-05-28 | Added final structural/task analyzer metadata edge-case guardrails for JSON-safe numeric output, metric alias collisions, metric status/value consistency, partial and empty designs, condition/factor conflicts, report display-string safety, localization parity, and document-version provenance. |
| 1.36.0 | 2026-05-28 | Hardened the structural/task analyzer metadata spec with registry validation, golden compatibility snapshots, schema evolution policy, legacy analyzer fallback, metadata cardinality limits, and S1-to-S2 handoff rules. |
| 1.35.0 | 2026-05-28 | Added the structural/task analyzer metadata implementation spec, resolved D-MET-01 through D-MET-03, and routed S0-S3 analyzer/report metadata work through the new spec. |
| 1.34.0 | 2026-05-28 | Froze the experiment change orchestration contract for implementation use and added the amendment-trigger policy and amendment template. |
| 1.33.0 | 2026-05-28 | Added final safety boundaries to the experiment change plan: secrets and credentials handling, network/dependency-download authorization, negative-test requirements, orchestrator escalation thresholds, and post-merge verification windows. |
| 1.32.0 | 2026-05-28 | Added final orchestration safeguards to the experiment change plan: independent review gates, fixture-first rollout gates, orchestrator dry-run checks, explicit conflict-resolution order, and maximum branch-scope limits. |
| 1.31.0 | 2026-05-28 | Added orchestration hardening controls to the experiment change plan: single-writer state updates, agent launch packets, requirement-to-test traceability, merge train promotion, default-invariance proofs, dependency/lockfile policy, planning-doc fingerprints in run packets, and stale worker/worktree cleanup. |
| 1.30.0 | 2026-05-28 | Hardened the observability sidecar implementation spec with dual-write failure handling, strict schema and attribute limits, summary/hash canonicalization, runner no-remote tests, path-collision safety, import-boundary tests, cost-basis confidence rules, and join/completeness validation. |
| 1.29.0 | 2026-05-28 | Added the observability sidecar implementation spec, resolved the initial observability rollout decisions, reconciled the experiment orchestration state and contract to the Phase 14e matrix freeze, and routed O0-O4 work through the new spec. |
| 1.28.0 | 2026-05-28 | Registered the Cluster 3 Phase 14e four-cell n=5 matrix freeze, the frozen development-scale condition-coverage matrix, validated hash/schema/boundary status for all four cells, and the no-paper/no-lift/no-performance caveats. |
| 1.27.0 | 2026-05-28 | Registered the Cluster 3 Phase 14d G+P reuse-vs-rerun decision, approved reuse of the validated Phase 12 G+P n=5 artifact as the Phase 14 G+P matrix cell, and updated artifact registry and handoff routing caveats. |
| 1.26.0 | 2026-05-28 | Registered the Cluster 3 Phase 14c G+C+P n=5 Modal execution, the validated G+C+P matrix artifact, template upper-bound diagnostic grammar metadata, the insufficient repair-signal caveat, and the Phase 14d G+P reuse-or-rerun decision gate. |
| 1.25.3 | 2026-05-28 | Added edge-case guardrails to the experiment change orchestration state file, including freshness checks, state-drift reconciliation, partial artifact handling, hard run limits, no-silent-defaults policy, abandoned-work protocol, and provenance freeze requirements. |
| 1.25.2 | 2026-05-28 | Added the open decisions register to the experiment change orchestration state file and made the orchestration contract block packages on unresolved decisions unless they use the recorded conservative default. |
| 1.25.1 | 2026-05-28 | Added the validation matrix to the experiment change orchestration state file, required packages to satisfy or explain those validations before exit gates, and aligned orchestration state/contract routing with the Phase 14c explicit-approval gate. |
| 1.25.0 | 2026-05-28 | Registered the Cluster 3 Phase 14b C+P n=5 Modal execution, the validated C+P matrix artifact, the insufficient repair-signal caveat, the registry docs-lock compatibility correction, and the Phase 14c explicit-approval gate. |
| 1.24.2 | 2026-05-28 | Added the canonical experiment change orchestration state file and routed future docs 12-14 work through that live state record before branch, lease, or run work starts. |
| 1.24.1 | 2026-05-27 | Added operating controls to the experiment change orchestration contract and aligned its Cluster 3 run-control language with the Phase 14a completed / Phase 14b explicit-approval state. |
| 1.24.0 | 2026-05-27 | Registered the Cluster 3 Phase 14a P-only n=5 Modal execution, the validated P-only matrix artifact, the insufficient F1/P-loop signal caveat, and the Phase 14b explicit-approval gate. |
| 1.23.0 | 2026-05-27 | Registered the experiment change orchestration contract for docs 12-14 implementation sequencing, parallel branch ownership, serialized surfaces, and paid-run gates. |
| 1.22.0 | 2026-05-27 | Registered the Cluster 3 Phase 13b commit/provenance freeze verification and Phase 14 optional n=5 condition-matrix planning report; updated agent routing from the Phase 13 hold state to the Phase 14a explicit-approval gate. |
| 1.21.0 | 2026-05-27 | Registered Cluster 3 Phase 12c fixture alignment, Phase 12d F1/P-loop branch evidence, Phase 12e initial-F2/C-loop branch evidence, and the Phase 13 diagnostic evidence freeze/go-no-go audit. |
| 1.20.0 | 2026-05-27 | Registered the Cluster 3 Phase 12b targeted F1 diagnostic, the blocked zero-row fixture attempts, and the no-F1-fixture-signal caveat. |
| 1.19.0 | 2026-05-27 | Registered the Cluster 3 Phase 12 G+P template-grammar n=5 development run, the validated development artifact, and the insufficient F1-signal caveat. |
| 1.18.0 | 2026-05-27 | Registered the Cluster 3 Phase 11 Modal hydration remediation, the validated n=1 P smoke artifact, the archived zero-row blocked attempt, and the continued Phase 12 explicit-approval gate. |
| 1.17.0 | 2026-05-27 | Registered the blocked Cluster 3 Phase 11 Modal n=1 smoke attempt, the zero-row placeholder artifact status, and updated Phase 12 routing to require Phase 11 remediation/rerun first. |
| 1.16.0 | 2026-05-27 | Registered Cluster 3 Phase 10 documentation updates, including the new Cluster 3 methodology doc, artifact registry planning section, decision-log records, README refresh, docs-consistency tests, and Phase 11 read-set routing. |
| 1.15.3 | 2026-05-27 | Registered the Cluster 3 Phase 9 boundary latency remediation that makes the P sanitizer reject latency, restores Cluster 3 validation to green, and clears the Phase 10 preflight blocker. |
| 1.15.2 | 2026-05-27 | Registered the Cluster 3 Phase 9 injected-review fix that removed the sanitizer latency xfail and restored the boundary as an enforcing failing test without production sanitizer changes. |
| 1.15.1 | 2026-05-27 | Registered the Cluster 3 Phase 9 review-fix pass that records the sanitizer latency boundary as an expected xfail while keeping Cluster 3 validation green without production sanitizer changes. |
| 1.15.0 | 2026-05-27 | Registered Cluster 3 Phase 9 boundary-test evidence, recorded the sanitizer latency boundary failure, and routed future Cluster 3/P agents through the blocked Phase 9 report before Phase 10. |
| 1.14.0 | 2026-05-27 | Registered Cluster 3 Phase 8 F1 compile-error fixture smoke evidence, updated Phase 9 read-set routing, and refreshed Cluster 3 stale-status notes after the fixture smoke implementation. |
| 1.13.12 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for full sorted legacy 2x2 JSON golden compatibility testing. |
| 1.13.11 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for explicit legacy 2x2 contract snapshot testing. |
| 1.13.10 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for JSONL nested C terminal failure-code preservation. |
| 1.13.9 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for canonicalized pair-key mismatch sorting and JSONL nested P trace-summary preservation. |
| 1.13.8 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for nullable optional P-pair key canonicalization and direct DataFrame nested scalar diagnostic preservation. |
| 1.13.7 | 2026-05-27 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for direct DataFrame nested P diagnostic preservation before p_helped derivation. |
| 1.13.6 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for nested P terminal-class diagnostics and P trace-summary quarantine. |
| 1.13.5 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for direct DataFrame P-pair mixed-grammar validation with nested grammar metadata. |
| 1.13.4 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for direct DataFrame P-pair warning metadata with nested optional identity. |
| 1.13.3 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for raw DataFrame nested P-pair identity and factorial-summary feedback-column compatibility. |
| 1.13.2 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for nested generated-metadata P diagnostic quarantine. |
| 1.13.1 | 2026-05-26 | Registered the Cluster 3 Phase 7a analyzer review-fix pass for optional P-pair identity coverage and dynamic missing-control warnings. |
| 1.13.0 | 2026-05-26 | Registered Cluster 3 Phase 7a analyzer additive-support evidence and routed future Cluster 3 agents through the blocked Phase 7a report. |
| 1.12.0 | 2026-05-26 | Registered the frontier feedback-loop ablation proposal and updated public documentation navigation. |
| 1.11.0 | 2026-05-26 | Registered Cluster 3 Phase 6 replay manifest integration evidence, updated Phase 7 read-set routing, and refreshed Cluster 3 component-doc caveats after Phase 0-6 implementation. |
| 1.10.2 | 2026-05-26 | Registered the Cluster 3 Phase 5 no-P control resolver TypeError propagation review-fix evidence. |
| 1.10.1 | 2026-05-26 | Registered the Cluster 3 Phase 5 review-fix pass for fail-closed pair identity validation and C trace provenance rejection. |
| 1.10.0 | 2026-05-26 | Registered Cluster 3 Phase 5 runner orchestration, C-loop adapter, public pair-validator evidence, and Phase 6 read-set routing. |
| 1.9.1 | 2026-05-26 | Registered Cluster 3 Phase 4 correctness adapter review-fix evidence for canonical F0 compile_success normalization. |
| 1.9.0 | 2026-05-26 | Registered Cluster 3 Phase 4 correctness adapter evidence, updated Phase 5 read-set routing, and recorded Cluster 3 component-doc freshness caveats after Phase 0-4 implementation. |
| 1.8.0 | 2026-05-26 | Registered Cluster 3 Phase 3 dispatcher evidence, updated Phase 4 read-set routing, and recorded Cluster 3 component-doc freshness caveats after Phase 0-3 implementation. |
| 1.7.0 | 2026-05-26 | Registered the Cluster 2 C limitation memo, routed it through agent-facing pull sets, and recorded the Cluster 3 audit-only research prediction addendum. |
| 1.6.12 | 2026-05-26 | Registered Cluster 3 Phase 2 active P row initial-failure binding review-fix evidence. |
| 1.6.11 | 2026-05-26 | Registered Cluster 3 Phase 2 P seed trace binding and private resume-close bypass review-fix evidence. |
| 1.6.10 | 2026-05-26 | Registered Cluster 3 Phase 2 manual resume-close validation review-fix evidence. |
| 1.6.9 | 2026-05-26 | Registered Cluster 3 Phase 2 inactive-C repair-trace rejection review-fix evidence. |
| 1.6.8 | 2026-05-26 | Registered Cluster 3 Phase 2 P stop-reason terminal-outcome and replay pairing string validation review-fix evidence. |
| 1.6.7 | 2026-05-26 | Registered Cluster 3 Phase 2 compile-repaired P stop-reason success-flag binding review-fix validation evidence. |
| 1.6.6 | 2026-05-26 | Registered Cluster 3 Phase 2 trace terminal provenance, C repair-trace index, and generated runtime metadata review-fix validation evidence. |
| 1.6.5 | 2026-05-26 | Registered Cluster 3 Phase 2 P compile-repair evidence, P trace-index, and C seed-terminal provenance review-fix validation evidence. |
| 1.6.4 | 2026-05-26 | Registered Cluster 3 Phase 2 P/C terminal outcome binding and replay-control condition review-fix validation evidence. |
| 1.6.3 | 2026-05-26 | Registered Cluster 3 Phase 2 trace-bound terminal provenance and replay sidecar review-fix validation evidence. |
| 1.6.2 | 2026-05-26 | Registered Cluster 3 Phase 2 terminal provenance and builder-default review-fix validation evidence. |
| 1.6.1 | 2026-05-26 | Registered Cluster 3 Phase 2 schema/logger review-fix validation evidence. |
| 1.6.0 | 2026-05-26 | Registered Cluster 3 Phase 2 schema/logger evidence and bumped edited handoff state/version records. |
| 1.5.3 | 2026-05-26 | Registered Cluster 3 Phase 1 trace success-inference review-fix evidence. |
| 1.5.2 | 2026-05-26 | Registered Cluster 3 Phase 1 prompt-provenance and seed-lineage review-fix evidence. |
| 1.5.1 | 2026-05-26 | Registered Cluster 3 Phase 1 review-fix trace validation evidence. |
| 1.5.0 | 2026-05-26 | Registered Cluster 3 Phase 1 P repair-loop evidence and bumped edited handoff state/version records. |
| 1.4.0 | 2026-05-26 | Registered Cluster 3 Phase 0 scaffolding evidence and bumped edited handoff state/version records. |
| 1.3.0 | 2026-05-26 | Registered the reviewed Cluster 3 v1 implementation specification and patch reports; aligned Cluster 3 routing docs for pre-Phase-0 implementation. |
| 1.2.0 | 2026-05-21 | Registered the current-pipeline template upper-bound G diagnostic artifact and run report; bumped affected docs and routing entries. |
| 1.1.0 | 2026-05-21 | Registered template-G legacy alignment documentation updates and the new fix report; bumped affected docs/contracts/component records. |
| 1.0.0 | 2026-05-21 | Created baseline registry for all relevant project-owned markdown, including ignored docs and agentic files. |

## Control Documents

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `docs/handoff/agentic_document_hub.md` | 1.23.0 | `AGENT_POLICY` | Central routing hub for agents; latest Cluster 3 gate is post-Phase-14e, docs 12-14 agents are routed through the single-writer state and launch-packet controls, launch packets must authorize network/dependency/credential/secrets handling, the orchestration contract is frozen for implementation use, observability agents are routed through `docs/16_observability_sidecar_implementation_spec.md`, structural/task analyzer/report metadata agents are routed through `docs/17_structural_task_analyzer_metadata_implementation_spec.md`, and agentic repair-memory agents are routed through `docs/18_agentic_transcript_v1_implementation_spec.md` | Any new issue pull set, doc shelf, or agent entrypoint |
| `docs/handoff/document_version_registry.md` | 1.45.0 | `AGENT_POLICY` | Version source of truth for markdown docs; registers the hardened Agentic Transcript v1 implementation spec, docs-only checkpoint report, ready-to-implement kickoff state, A-stream checkpoint/preflight/review gates, explicit config validation, canonical prompt grammar, public-evidence-only ranking, fixture acceptance manifest, legacy byte-invariance snapshots, prompt-core import isolation, metadata nullability matrix, CLI/API default tests, mixed-policy analyzer fixture, commit/package slicing, rollback independence, no-opportunistic-cleanup policy, resolved A-stream decisions, fully hardened structural/task analyzer metadata implementation spec, resolved D-MET decisions, hardened observability sidecar implementation spec, Phase 14e-aligned orchestration updates, orchestration-hardening controls, secrets/network/negative-test/escalation/post-merge boundaries, and contract-freeze/amendment policy | Any doc creation, edit, promotion, or stale classification change |
| `docs/handoff/code_update_documentation_policy.md` | 1.0.0 | `AGENT_POLICY` | Code-to-doc update policy | Any new code area, artifact type, or documentation maintenance rule |
| `docs/handoff/codebase_handoff_guide.md` | 1.0.0 | `AGENT_POLICY` | Existing codebase handoff guide | Handoff workflow, read order, or phase-state process changes |
| `docs/handoff/stale_docs_inventory.md` | 1.14.0 | `AGENT_POLICY` | Current stale-doc and caveat inventory; records the Phase 14e four-cell n=5 development matrix freeze and insufficient repair-signal caveats | Any stale/superseded/citation status change |
| `docs/handoff/experiment_change_orchestration_state.md` | 1.5.7 | `AGENT_POLICY` | Canonical live state record for docs 12-14 parallel branches, active worktrees, serialized-surface leases, gate status, launch packets, run packets, work-package cards, ready-to-implement kickoff state, Agentic Transcript v1 docs-only checkpoint status, validation matrix, requirement-to-test traceability, default-invariance proofs, fixture-first proofs, independent review gates, commit/package slicing, rollback independence, no-opportunistic-cleanup controls, secrets/credentials boundaries, network/dependency-download authorization, negative-test requirements, orchestrator escalation thresholds, post-merge verification windows, dependency/lockfile controls, conflict-resolution order, orchestrator dry-run checklist, contract-freeze/amendment template, resolved observability, analyzer-metadata, and agentic-transcript decisions, edge-case guardrails, A0.5 preflight, A1 review checkpoint, stale-work cleanup, Phase 14e freeze state, hardened observability spec version, fully hardened structural/task analyzer metadata spec version, hardened agentic transcript implementation spec version, and next allowed actions | Any branch start/finish, launch packet, lease take/release, validation requirement, traceability requirement, review gate, fixture gate, secrets/network boundary, negative-test requirement, escalation, post-merge verification, contract amendment, open decision, edge-case guardrail, run packet, merge, abandonment, gate status, or next-action change |
| `docs/15_experiment_change_orchestration_contract.md` | 1.0.12 | `AGENT_POLICY` | Active frozen control-plane contract for docs 12-14 implementation sequencing, parallel branch ownership, serialized-surface leases, single-writer state control, agent launch packets, requirement-to-test traceability, merge train promotion, default-invariance proofs, independent review gates, fixture-first rollout, orchestrator dry-run checks, explicit conflict-resolution order, maximum branch-scope limits, secrets/credentials boundaries, network/dependency-download authorization, negative-test requirements, orchestrator escalation thresholds, post-merge verification windows, dependency/lockfile policy, planning-doc run fingerprints, stale worktree cleanup, amendment-trigger policy, validation matrix, open decisions register, edge-case guardrails, run approval packet, gating, Phase 14e run-control, observability spec routing, structural/task analyzer spec routing, agentic transcript spec routing, and no-run/no-n20 policy | Any sequencing, branch ownership, serialized-surface, launch-packet, validation requirement, traceability requirement, review gate, fixture gate, branch-scope limit, secrets/network boundary, negative-test requirement, escalation, post-merge verification, dependency policy, contract amendment, decision-blocker, edge-case guardrail, run-gate, trust-boundary, or paper-scale readiness change |
| `docs/16_observability_sidecar_implementation_spec.md` | 0.2.0 | `AGENT_POLICY` | Authoritative O0-O4 implementation contract for sidecar schema, logger, identity, artifact paths, privacy, Modal context, token telemetry, estimated cost, rollout modes, tests, gates, dual-write handling, strict attributes, hash canonicalization, import boundaries, cost-basis confidence, and completeness validation | Any observability schema, logger, runner instrumentation, Modal context, token telemetry, cost-estimate, billing, privacy, or sidecar-routing change |
| `docs/17_structural_task_analyzer_metadata_implementation_spec.md` | 0.1.2 | `AGENT_POLICY` | Authoritative S0-S3 implementation contract for outcome-family metadata, analyzer metric registry, metric-registry validation, golden compatibility snapshots, schema evolution, metadata cardinality limits, JSON-safe output, alias-collision rejection, metric status/value consistency, partial and empty design behavior, condition/factor conflict handling, document-version provenance, level-reach diagnostics, feedback activation diagnostics, legacy analyzer fallback, display-string safety, localization parity, S1-to-S2 handoff, mixed-schema syntax validity policy, report-builder sequencing, compatibility tests, and D-MET decisions | Any structural/task analyzer metadata, metric registry, report-label, feedback-activation, level-reach, syntax-validity, report-builder, analyzer-output compatibility, or S0-S3 routing change |
| `docs/18_agentic_transcript_v1_implementation_spec.md` | 0.1.5 | `AGENT_POLICY` | Authoritative A0-A6 implementation contract for opt-in `agentic_transcript_v1` repair-history prompts, structured public attempt evidence, explicit policy config and precedence, canonical prompt grammar, source/failure delimiters, public-evidence-only best-anchor selection, prompt budgets, metadata labels, C/P boundaries, P-to-C isolation, analyzer grouping, A/B gates, fail-closed edge cases, source-record handling, resume constraints, prompt-injection fixtures, artifact-mixing policy, spec-only checkpoint, A0.5 preflight, fixture acceptance manifest, legacy byte-invariance snapshots, prompt-core import isolation, metadata nullability matrix, CLI/API default tests, fixture-first A1 gate, migration classification plan, stop triggers, mixed-policy analyzer fixture, commit/package slicing, per-package exit checklist, rollback independence, no-opportunistic-cleanup policy, and A1 review checkpoint | Any agentic repair-memory constants, prompt renderer, C/P loop integration, P-to-C history isolation, policy labels, analyzer grouping, or A/B gate change |
| `.contracts/agentic/preliminary_report_handoff/phase_state.md` | 1.22.0 | `AGENT_INTERNAL` | Current agent baton and phase status; latest state is Cluster 3 Phase 14e four-cell n=5 matrix freeze complete with known Cluster 1 docs-lock warning remaining | End of each bounded documentation or handoff phase |

## Citation-Current Docs

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `README.md` | 1.2.1 | `CITATION_CURRENT` | Root entry point and current scope summary; links the frontier feedback-loop ablation proposal as proposal-only documentation | Scope, artifact, caveat, or navigation change |
| `docs/00_project_map.md` | 1.0.6 | `CITATION_CURRENT` | Project documentation map and trust policy; links the docs 12-18 planning/spec sequence including the observability sidecar, structural/task analyzer metadata, and agentic transcript implementation specs | Scope, source-of-truth, or documentation architecture change |
| `docs/02_methodology_cluster1.md` | 1.2.0 | `CITATION_CURRENT` | Cluster 1/G methodology; separates current task-agnostic G from current and legacy template diagnostics | Grammar, G semantics, compile boundary, or Cluster 1 artifact change |
| `docs/03_methodology_cluster2.md` | 1.0.0 | `CITATION_CURRENT` | Cluster 2/C and G+C methodology | C/G+C routing, feedback, replay, schema, or artifact change |
| `docs/cluster2_c_limitation_memo.md` | 1.0.0 | `CITATION_CURRENT` | Thesis-facing C limitation memo; classifies Cluster 2 C as operational but `MIXED_LIMITATION` using diagnostic template G+C repair traces | C limitation framing, diagnostic template G+C interpretation, or C/P research prediction change |
| `docs/04_modal_infrastructure.md` | 1.0.0 | `CITATION_CURRENT` | Modal, provenance, hash, and durability methodology | Modal harness, provenance, hash, or durability change |
| `docs/04_methodology_cluster3.md` | 1.0.0 | `CITATION_CURRENT` | Cluster 3/P v1 methodology; documents compile-error repair scope, F1_COMPILE-only routing, schema version 1, feedback boundaries, and Phase 11 gate | P semantics, Cluster 3 routing, schema, artifact gate, or scale-policy change |
| `docs/05_artifacts_and_results_registry.md` | 1.12.0 | `CITATION_CURRENT` | Current artifact identities, row counts, schemas, caveats, current/legacy template-G diagnostic status, validated Cluster 3 Phase 11/12/12d/12e artifacts, blocked Phase 12b attempts, Phase 13 diagnostic evidence freeze, Phase 14a P-only n=5 matrix cell, Phase 14b C+P n=5 matrix cell, Phase 14c G+C+P n=5 matrix cell, Phase 14d G+P reuse decision, and Phase 14e four-cell n=5 matrix freeze | Any artifact, output, row-count, schema, or provenance change |
| `docs/06_failure_taxonomy_and_eval_ladder.md` | 1.1.0 | `CITATION_CURRENT` | Evaluation ladder and F0/F1/F2/F3 semantics, including Cluster 3 P repair firing only on F1_COMPILE | Failure-code, eval-level, or repair-eligibility change |
| `docs/07_analysis_and_statistics.md` | 1.2.0 | `CITATION_CURRENT` | Analyzer normalization, pairing, statistics, reportability, and template-G diagnostic exclusion | Analyzer code/output, statistics, pairing, or reportability change |
| `docs/08_decision_log.md` | 1.3.0 | `CITATION_CURRENT` | Current methodology and artifact decision records, including Cluster 3 v1 routing, schema, feedback, adapter, analyzer, and Phase 11 gate decisions | New decision, superseded decision, or caveat change |
| `docs/09_preliminary_report_outline.md` | 1.3.0 | `CITATION_CURRENT` | Preliminary report scaffold with current template-G diagnostic appendix-only placement and C limitation memo citation | Report structure, source matrix, or result-placeholder status change |
| `docs/10_cluster3_drift_prevention_plan.md` | 1.1.0 | `CITATION_CURRENT` | Cluster 3/P guardrails; points to the reviewed v1 implementation specification for Phase 0+ work | P semantics, gates, or Cluster 3 planning changes |
| `docs/11_frontier_feedback_loop_ablation.md` | 0.1.0 | `AGENT_INTERNAL` | Frontier-model C/P feedback-loop ablation proposal; documentation only, no API calls, Modal runs, artifacts, or result claims | Frontier ablation methodology, provider-backend plan, or promotion status change |
| `docs/preliminary_report/README.md` | 1.0.0 | `CITATION_CURRENT` | Preliminary report asset/readme surface | Report generation or source asset changes |

## Formal Research Contracts

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `.contracts/README.md` | 1.0.0 | `FORMAL_CONTRACT` | Explains contract directory roles | Contract directory policy changes |
| `.contracts/research/research_scope.md` | 1.1.0 | `FORMAL_CONTRACT` | Formal research scope; legacy template G excluded from current primary G | Scope, mechanism, or non-goal change |
| `.contracts/research/scale_policy.md` | 1.1.0 | `FORMAL_CONTRACT` | Scale tiers, promotion rules, artifact naming, metadata, and legacy template-G exclusion | New scale tier, artifact promotion rule, or paper-scale artifact |
| `.contracts/research/eval_metrics.md` | 1.1.0 | `FORMAL_CONTRACT` | Evaluation metrics, ladder, schemas, statistical protocols, and template metadata-gate caveat | Metric, schema, tolerance, or analyzer semantics change |
| `.contracts/research/cluster1_generated_surface.md` | 1.0.0 | `FORMAL_CONTRACT` | Cluster 1 generated-surface contract | Grammar/surface acceptance changes |
| `.contracts/research/phase4_parse_reclassification_disposition.md` | 1.0.0 | `FORMAL_CONTRACT` | Parse reclassification disposition | Only if disposition changes with new verified evidence |
| `.contracts/research/modal_new_account_setup_guide.md` | 0.1.0 | `AGENT_INTERNAL` | Modal setup guide with operational content | Account/setup procedure changes; keep out of report citations |
| `.contracts/research/paper_outline.md` | 0.3.0 | `LEGACY_OR_SUPERSEDED` | Older working paper outline | Prefer `docs/09_preliminary_report_outline.md`; update only with explicit revival |

## Component Docs

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `cluster1/README.md` | 1.0.0 | `COMPONENT_DOC` | Cluster 1 component overview aligned to current primary task-agnostic G and legacy template diagnostic status | Cluster 1 component-doc cleanup |
| `cluster1/docs/grammar_surface_contract.md` | 1.0.0 | `COMPONENT_DOC` | Local grammar surface contract | Grammar/surface acceptance changes |
| `cluster1/grammar/corpus/api_coverage_report.md` | 1.0.0 | `COMPONENT_DOC` | Grammar API coverage report | Triton reference/corpus allowlist changes |
| `cluster1/tests/fixtures/README.md` | 1.0.0 | `COMPONENT_DOC` | Cluster 1 fixture description | Fixture additions or behavior changes |
| `cluster2/README.md` | 0.8.0 | `COMPONENT_DOC` | Cluster 2 component overview; may be stale | Cluster 2 component-doc cleanup |
| `cluster3/README.md` | 1.0.0 | `COMPONENT_DOC` | Cluster 3 component overview refreshed through Phase 10; points to `docs/04_methodology_cluster3.md` and keeps Phase 11 Modal smoke gated by explicit approval | Any P/Cluster 3 planning or implementation change |

## Agentic Internal Docs

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `docs/12_experiment_observability_plan.md` | 0.1.0 | `AGENT_INTERNAL` | Planning source for experiment observability metrics, sidecar-first rollout, Modal billing/context research, token counts, estimated cost, and future performance boundaries | Observability scope, metric coverage, source research, billing/cost policy, or sidecar rollout changes |
| `docs/13_agentic_repair_memory_strategy.md` | 0.1.0 | `AGENT_INTERNAL` | Strategy source for future opt-in `agentic_transcript_v1` repair-memory behavior and C/P prompt-history guardrails | Repair-memory policy, C/P prompt behavior, history labels, or A/B gate changes |
| `docs/14_structural_vs_task_outcome_reporting_plan.md` | 0.1.0 | `AGENT_INTERNAL` | Planning source for separating structural/code-surface metrics from task/functional metrics in analyzer and report work | Metric terminology, outcome families, analyzer metadata, or report table planning changes |
| `docs/cluster3_implementation_specification.md` | 1.1.0 | `AGENT_INTERNAL` | Reviewed Cluster 3 v1 implementation specification for Phases 0-14; Phase 0-10 local implementation/documentation work is complete with the Phase 10 warning path, and later diagnostic/freeze/planning phases remain governed by this specification | Any Cluster 3 implementation contract, phase ordering, schema, Modal policy, analyzer plan, or acceptance-test change |
| `docs/cluster3_implementation_plan_draft.md` | 0.9.0 | `LEGACY_OR_SUPERSEDED` | Superseded Cluster 3 draft plan; use `docs/cluster3_implementation_specification.md` for implementation | Historical unless explicitly revived |
| `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` | 1.0.0 | `AGENT_INTERNAL` | Completed Phase 0-11 handoff-readiness plan | Only if the completed plan is explicitly amended |
| `.contracts/agentic/preliminary_report_handoff/phase_0_inventory_notes.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 0 inventory notes | Historical; prefer appending new phase notes elsewhere |
| `.contracts/agentic/preliminary_report_handoff/phase_0_file_classification_table.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 0 file classifications | Historical; update stale inventory instead |
| `.contracts/agentic/preliminary_report_handoff/phase_0_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 0 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_1_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 1 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_2_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 2 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_3_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 3 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_4_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 4 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_5_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 5 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_6_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 6 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_7_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 7 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_8_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 8 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 8 contract diff review | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_9_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 9 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_10_next_agent_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 10 baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/phase_11_completion_brief.md` | 1.0.0 | `AGENT_INTERNAL` | Phase 11 completion baton | Historical |
| `.contracts/agentic/preliminary_report_handoff/post_phase11_doc_cleanup_report.md` | 1.0.0 | `AGENT_INTERNAL` | Post-Phase-11 cleanup report | Historical unless cleanup is revised |
| `.contracts/agentic/cluster1_contract.md` | 0.9.0 | `AGENT_INTERNAL` | Historical Cluster 1 agent contract | Promote verified claims into `docs/02` or contracts instead |
| `.contracts/agentic/cluster1_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Historical Cluster 1 plan | Historical |
| `.contracts/agentic/post_cluster1_scope_and_execution_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Historical post-Cluster-1 plan | Historical |
| `.contracts/agentic/cluster2_contract.md` | 0.9.0 | `AGENT_INTERNAL` | Historical Cluster 2 contract | Update only if active agent contract changes; promote current claims into `docs/03` |
| `.contracts/agentic/cluster2_integrated_agent_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Historical Cluster 2 integrated plan | Historical |
| `.contracts/agentic/cluster2_f2_repair_smoke_plan.md` | 0.9.0 | `AGENT_INTERNAL` | F2 repair smoke plan | Update only if smoke procedure changes |
| `.contracts/agentic/cluster2_paired_replay_alignment_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Replay alignment plan | Historical unless replay remediation resumes |
| `.contracts/agentic/cluster2_paired_replay_alignment_review_todo.md` | 0.9.0 | `AGENT_INTERNAL` | Replay alignment review TODO | Historical unless review resumes |
| `.contracts/agentic/cross_cluster_eval_alignment_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Cross-cluster eval alignment plan | Historical; current owner is `docs/06` and `docs/07` |
| `.contracts/agentic/fix_brief_c_factorial_analysis_alignment_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Analyzer alignment fix plan | Historical |
| `.contracts/agentic/fix_brief_c_factorial_analysis_unstaged_verification_report.md` | 0.9.0 | `AGENT_INTERNAL` | Analyzer fix verification report | Evidence only |
| `.contracts/agentic/generation_metadata_instrumentation_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Metadata instrumentation plan | Historical; current owner is registry/provenance docs |
| `.contracts/agentic/modal_integration_plan.md` | 0.9.0 | `AGENT_INTERNAL` | Modal integration plan | Historical or operational context |
| `.contracts/agentic/modal_harness_draft.md` | 0.9.0 | `AGENT_INTERNAL` | Modal harness draft | Historical or operational context |
| `.contracts/agentic/modal_cost_optimization_auditability_report.md` | 0.9.0 | `AGENT_INTERNAL` | Modal cost/auditability report | Evidence only |
| `.contracts/agentic/reference/modal_opt.md` | 0.1.0 | `AGENT_INTERNAL` | Cached Modal reference | Refresh only from source if explicitly needed |
| `.contracts/agentic/reference/modal_docs_helper.md` | 0.1.0 | `AGENT_INTERNAL` | Cached Modal helper docs | Refresh only from source if explicitly needed |
| `.contracts/agentic/reference/modal_docs_RL_helper.md` | 0.1.0 | `AGENT_INTERNAL` | Cached Modal RL helper docs | Refresh only from source if explicitly needed |
| `.contracts/agentic/reference/triton_corpus.md` | 0.1.0 | `AGENT_INTERNAL` | Cached Triton corpus/reference material | Refresh only from source if explicitly needed |

## Audit Evidence Snapshots

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `audits/repository_documentation_methodology_readiness_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Phase 0 documentation/methodology audit | Historical; create a new audit for new evidence |
| `audits/final_documentation_consistency_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Phase 11 final consistency audit | Historical |
| `audits/analyzer_reportability_blocker_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Analyzer reportability blocker audit | New analyzer audit if reportability changes |
| `audits/analyzer_scale_tier_reportability_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Scale-tier reportability fix evidence | Historical |
| `audits/scale_tier_docs_contract_alignment_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Scale-tier docs/contracts alignment fix evidence | Historical |
| `audits/cross_pipeline_reportability_alignment_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cross-pipeline reportability alignment evidence | Historical |
| `audits/template_g_180_legacy_compatibility_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Template G 180/180 legacy compatibility evidence | Historical |
| `audits/template_g_legacy_registry_docs_alignment_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Template G legacy registry/docs alignment fix evidence | Create a new audit for later template-G policy changes |
| `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Current-pipeline template upper-bound G n20 L4 run, validation, and registry evidence | Historical evidence for registered diagnostic artifact |
| `audits/analyzer_pre_output_verification_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Analyzer pre-output verification | Historical |
| `audits/factorial_2x2_preliminary_analysis_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Preliminary factorial analysis report | Historical while analyzer remains caveated |
| `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | F3 compile-success policy decision evidence | Historical |
| `audits/factorial_cluster1_functional_success_normalization_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 1 functional normalization evidence | Historical |
| `audits/factorial_cluster2_compile_success_normalization_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 2 compile normalization evidence | Historical |
| `audits/pre_paper_factorial_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Broad pre-paper factorial audit | Historical |
| `audits/cluster3_implementation_plan_draft_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 implementation plan audit and early post-review findings | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_specification_e_patch_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 specification §E patch evidence | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_specification_f_cleanup_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 specification §F cleanup evidence | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_specification_g_contract_cleanup_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 specification §G contract cleanup evidence | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_specification_h_pre_phase0_cleanup_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 specification §H pre-Phase-0 cleanup evidence | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_specification_i_final_pre_phase0_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 specification §I final pre-Phase-0 cleanup evidence | Historical evidence for the reviewed implementation specification |
| `audits/cluster3_phase0_scaffolding_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 0 scaffolding implementation, preflight, tests, and docs-impact evidence | Historical evidence for Phase 0; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase1_p_repair_loop_report.md` | 1.0.3 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 1 P repair loop, prompt, sanitizer, adapter, trace implementation, and trace success-inference review-fix evidence | Historical evidence for Phase 1; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase2_schema_logger_report.md` | 1.0.12 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 2 row schema/logger implementation, active P row initial-failure binding review-fix evidence, preflight, tests, and docs-impact evidence | Historical evidence for Phase 2; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase3_dispatcher_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 3 deterministic dispatcher implementation, preflight, tests, regression status, and docs-impact evidence | Historical evidence for Phase 3; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase4_correctness_adapter_report.md` | 1.0.1 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 4 local correctness adapter implementation, F0 compile_success normalization review fix, preflight, tests, Modal boundary verification, regression status, and docs-impact evidence | Historical evidence for Phase 4; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase5_runner_orchestration_report.md` | 1.0.2 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 5 local runner orchestration, C-loop adapter, public no-P pair validator, review-fix passes including no-P control resolver TypeError propagation, preflight, tests, Modal boundary verification, regression status, and docs-impact evidence | Historical evidence for Phase 5; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase6_replay_manifest_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 6 no-P replay manifest schema, builder, loader, resolver, fixture-pairing tests, preflight, regression status, and docs-impact evidence | Historical evidence for Phase 6; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase7a_analyzer_support_report.md` | 1.0.12 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 7a analyzer additive-support implementation and review-fix evidence for optional P-pair identity coverage, dynamic P-pair warnings, nested generated-metadata P diagnostic quarantine, raw DataFrame nested P-pair identity matching, direct DataFrame P-pair warning metadata, nested grammar-metadata mixed-grammar validation, nested P terminal-class diagnostics, P trace-summary quarantine, direct DataFrame nested P and scalar diagnostic preservation, nullable optional P-pair key canonicalization, canonicalized pair-key mismatch sorting, JSONL nested P trace-summary and C terminal failure-code preservation, explicit legacy 2x2 contract and full sorted JSON golden snapshot testing, factorial-summary feedback-column compatibility, tests, 2x2 compatibility checks, P-pairing evidence, 3-way interaction evidence, and shared documentation-language validation blocker | Resolve or acknowledge the blocker before classifying Phase 7a complete; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase8_f1_fixture_smoke_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 8 F1 compile-error fixture-smoke evidence covering four text-only broken Triton fixtures, P-loop success/exhaustion smoke, compile-error-only feedback boundaries, excerpt truncation, full-error SHA256, validation, and known Cluster 1 docs-lock warning | Historical evidence for Phase 8; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase9_boundary_tests_report.md` | 1.0.2 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 9 boundary-test and review-fix evidence covering dispatcher F0/F1_RUNTIME/F2/F3 routing, P feedback leakage boundaries, sanitizer isolation, LLVM/PTX allowance, and the sanitizer latency boundary failure later remediated in the focused latency report | Historical Phase 9 evidence; create new reports for later Cluster 3 phases |
| `audits/cluster3_phase9_boundary_latency_remediation_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Focused Cluster 3 Phase 9 boundary remediation evidence showing the P sanitizer now rejects latency and full Cluster 3 validation passes after the narrow fix | Historical remediation evidence; read before retrying Phase 10 |
| `audits/cluster3_phase10_documentation_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 10 documentation-update evidence covering methodology, registry, decision-log, README, docs-consistency tests, validation, and known Cluster 1 docs-lock warning | Historical Phase 10 evidence; read before Phase 11 Modal smoke |
| `audits/cluster3_phase11_modal_n1_smoke_report.md` | 1.0.1 | `EVIDENCE_SNAPSHOT` | Initial blocked Cluster 3 Phase 11 Modal n=1 smoke evidence, now linked to the hydration remediation rerun that produced one validated smoke row | Historical initial-attempt evidence; read with the hydration remediation report before Phase 12 development-scale planning |
| `audits/cluster3_phase11_modal_hydration_remediation_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 11 Modal hydration remediation evidence covering root cause, narrow runner local-entrypoint fix, archived blocked artifacts, validated n=1 P smoke rerun, row/schema/boundary validation, tests, and known Cluster 1 docs-lock warning | Required before any Phase 12 development-scale planning |
| `audits/cluster3_phase12_gp_template_grammar_n5_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 12 G+P template-grammar n=5 development run evidence covering command discovery, template selection, Modal execution, row/schema/sidecar validation, insufficient F1 signal, boundary scans, tests, and known Cluster 1 docs-lock warning | Required before any broader development-scale or paper-scale Cluster 3/P planning |
| `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 12b targeted F1 diagnostic evidence covering the diagnostic seed-source runner flags, two bounded Modal attempts, remote F0_BAD_SIGNATURE fixture classifications, zero-row blocked artifacts, tests, and known Cluster 1 docs-lock warning | Required before any additional targeted F1 diagnostic or broader P-loop planning |
| `audits/cluster3_phase12c_f1_fixture_alignment_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 12c local fixture-alignment evidence for a launcher-compatible F1_COMPILE diagnostic source crossing F0/signature checks without Modal or output mutation | Required before rerunning the aligned targeted F1/P-loop diagnostic |
| `audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 12d aligned F1/P-loop Modal diagnostic evidence showing one valid G+P row with observed F1_COMPILE seed, P fired, p_compile_repaired_then_success, terminal failure None, schema/hash validation, and known Cluster 1 docs-lock warning | Required branch-coverage evidence before broader P-loop planning |
| `audits/cluster3_phase12e_initial_f2_c_loop_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 12e initial-F2/C-loop Modal diagnostic evidence showing one valid G+C+P row with observed F2_NUMERIC_LARGE seed, P inactive, C fired from initial_f2, terminal failure None, schema/hash validation, and known Cluster 1 docs-lock warning | Required branch-coverage evidence before broader G+C+P planning |
| `audits/cluster3_phase13_diagnostic_evidence_freeze_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 13 diagnostic evidence freeze and go/no-go audit covering Phase 11/12/12d/12e artifact validation, hash sidecars, boundary scans, unsupported-claim audit, tests, known Cluster 1 docs-lock warning, and hold for commit/provenance freeze | Required before optional non-paper-scale n=5 matrix or any broader Cluster 3/P planning |
| `audits/cluster3_phase13b_commit_provenance_freeze_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 13b commit/provenance freeze verification showing a clean commit state, valid diagnostic artifacts and sidecars, boundary scans, unsupported-claim audit, tests, and the known Cluster 1 docs-lock warning | Required before optional non-paper-scale n=5 matrix planning or execution approval |
| `audits/cluster3_phase14_n5_condition_matrix_plan.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14 planning report for the optional non-paper-scale n=5 condition matrix; recommends one-cell-at-a-time execution beginning with P-only n=5 and preserves no-execution/no-output-mutation boundaries | Required before any Phase 14a n=5 matrix execution approval |
| `audits/cluster3_phase14a_p_only_n5_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14a P-only n=5 Modal execution evidence showing one valid P-only elementwise/fp32 development matrix cell with five F0_PARSE rows, zero F1_COMPILE seeds, zero P attempts, zero C fires, schema/hash validation, and the known Cluster 1 docs-lock warning | Required before Phase 14b C+P n=5 matrix execution approval |
| `audits/cluster3_phase14b_c_plus_p_n5_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14b C+P n=5 Modal execution evidence showing one valid C+P elementwise/fp32 development matrix cell with five F0_PARSE rows, zero F1_COMPILE seeds, zero initial F2 rows, zero P attempts, zero C fires, schema/hash validation, and the known Cluster 1 docs-lock warning | Required before Phase 14c G+C+P n=5 matrix execution approval |
| `audits/cluster3_phase14c_g_plus_c_plus_p_n5_modal_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14c G+C+P n=5 Modal execution evidence showing one valid G+C+P elementwise/fp32 development matrix cell with five clean-success rows, template upper-bound diagnostic grammar metadata, zero F1_COMPILE seeds, zero initial F2 rows, zero P attempts, zero C fires, schema/hash validation, and the known Cluster 1 docs-lock warning | Required before Phase 14d G+P reuse-or-rerun decision approval |
| `audits/cluster3_phase14d_g_plus_p_reuse_vs_rerun_decision.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14d G+P reuse-vs-rerun decision evidence approving reuse of the Phase 12 G+P n=5 artifact as the Phase 14 G+P matrix cell after comparability, schema, content-hash, grammar-metadata, boundary, and test validation, with the known Cluster 1 docs-lock warning | Required before any four-cell non-paper-scale matrix freeze/audit or broader Cluster 3 matrix decision |
| `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 3 Phase 14e four-cell n=5 matrix freeze evidence covering the P, C+P, G+C+P, and reused G+P development matrix cells, 20 schema-valid rows, hash sidecar validation, boundary scans, unsupported-claim audit, insufficient repair-signal caveat, and the known Cluster 1 docs-lock warning | Required before any broader Cluster 3 matrix analysis, paper-scale readiness decision, or run approval |
| `audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md` | 1.0.6 | `EVIDENCE_SNAPSHOT` | Readiness evidence for the LLM repair-memory worktree, missing implementation-spec finding, A-spec routing and hardening, research cross-check, canonical prompt grammar, public-evidence-only ranking, fixture acceptance manifest, legacy byte-invariance snapshots, metadata nullability matrix, commit/package discipline, ready-to-implement kickoff state, implementation checkpoint gates, local C/P prompt-loop validation, and no-Modal/no-output-mutation boundaries | Required context before starting A0 or A1 from the prepared worktree |
| `audits/agentic_transcript_v1_spec_checkpoint_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Agentic Transcript v1 docs-only checkpoint evidence confirming source-doc inspection, readiness-audit reconciliation, package rollout status, A0 readiness, boundary/non-goal verification, implementation stop triggers, local docs/import sanity tests, worktree caveats, and no-code/no-output mutation before A0 | Required before starting A0 policy constants from the prepared worktree |
| `audits/cross_cluster_pipeline_compatibility_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cross-cluster compatibility audit | Historical |
| `audits/generation_metadata_instrumentation_alignment_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Metadata instrumentation alignment audit | Historical |
| `audits/cluster1_eval_path_pre_n5_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 1 eval path pre-n5 audit | Historical |
| `audits/cluster2_pre_smoke_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Cluster 2 pre-smoke audit | Historical |
| `audits/cluster2_g_plus_c_readiness_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | G+C readiness audit | Historical |
| `audits/c2_replay_readiness_for_g_plus_c_from_g_n20_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Replay readiness audit | Historical |
| `audits/cluster2_c_smoke_n1_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | C smoke report | Historical |
| `audits/cluster2_g_plus_c_smoke_n1_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | G+C smoke report | Historical |
| `audits/cluster2_c_paper_n20_l4_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | C paper-scale run report | Historical evidence for registered artifact |
| `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | G+C paper-scale run report | Historical evidence for registered artifact |
| `audits/cluster2_g_plus_c_paper_n20_l4_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | G+C paper-scale report | Historical evidence for registered artifact |
| `audits/task_agnostic_g_aligned_pipeline_n5_l4_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | n5 task-agnostic G report | Legacy evidence |
| `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | n20 task-agnostic G report | Historical evidence for registered G artifact |
| `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Missing-row RCA | Historical evidence for G/G+C caveat |
| `audits/task_agnostic_grammar_n5_incompatibility_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | n5 grammar incompatibility audit | Legacy evidence |
| `audits/current_grammar_n5_rerun_hash_gate_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | n5 hash-gate report | Legacy evidence |
| `audits/grammar_hash_rerecord_compatibility_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Grammar hash rerecord compatibility | Historical |
| `audits/g_plus_c_hash_gate_and_metadata_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | G+C hash/metadata fix report | Historical |
| `audits/g_plus_c_implicit_level0_validator_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Level 0 validator fix report | Historical |
| `audits/g_plus_c_nested_metadata_validator_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Nested metadata validator fix report | Historical |
| `audits/g_plus_c_correctness_payload_failure_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Correctness payload failure fix report | Historical |
| `audits/c2_durable_result_writing_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Durable result writing fix evidence | Historical |
| `audits/c2_generated_eval_level0_level1_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Generated eval Level 0/1 fix report | Historical |
| `audits/c2_g_replay_manifest_and_metadata_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Replay manifest and metadata fix report | Historical |
| `audits/shared_modal_smoke_boundary_hash_resolution_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Shared Modal smoke/hash resolution | Historical |
| `audits/modal_image_sha_provenance_fix_report.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Modal image SHA provenance fix report | Historical |
| `audits/final_pre_n5_re_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Final pre-n5 re-audit | Legacy evidence |
| `audits/untracked_files_tracking_recommendation_audit.md` | 1.0.0 | `EVIDENCE_SNAPSHOT` | Untracked/ignored files tracking recommendation | Historical; this registry now includes ignored docs |

## Output Summaries

| Path | Version | Class | Current role | Update trigger |
|---|---|---|---|---|
| `outputs/cluster1/baseline_repaired_l4_n20_summary.md` | 1.0.0 | `OUTPUT_SUMMARY` | Summary for registered none artifact | Regenerate only with new artifact lineage |
| `outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic aligned n5 summary | Legacy unless promoted |
| `outputs/cluster1/cluster1_final_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical Cluster 1 final summary | Legacy unless promoted |
| `outputs/cluster1/full_baseline_n20_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical baseline summary | Legacy unless promoted |
| `outputs/cluster1/full_none_vs_g_n20_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical none-vs-G summary | Legacy unless promoted |
| `outputs/cluster1/final_none_vs_g_l4_n20_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical final none-vs-G summary | Legacy unless promoted |
| `outputs/cluster1/repaired_none_vs_g_n20_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical repaired none-vs-G summary | Legacy unless promoted |
| `outputs/cluster1/m1_small_matrix_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical small matrix summary | Legacy unless promoted |
| `outputs/cluster1/g_all_surface_hardened_n20_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical G surface hardened n20 summary | Legacy unless promoted |
| `outputs/cluster1/g_all_surface_hardened_n5_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical n5 summary | Legacy unless promoted |
| `outputs/cluster1/g_all_surface_hardened_n2_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical n2 summary | Legacy unless promoted |
| `outputs/cluster1/g_all_post_hardening_n5_l4_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical n5 post-hardening summary | Legacy unless promoted |
| `outputs/cluster1/g_elementwise_expr_hardened_n5_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical elementwise summary | Legacy unless promoted |
| `outputs/cluster1/g_surface_hardened_elementwise_n5_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical elementwise surface summary | Legacy unless promoted |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic n5 summary | Legacy unless promoted |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic n5 rerun summary | Legacy unless promoted |
| `outputs/cluster1/task_agnostic_g_all_n5_l4_surface_once_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic n5 surface-once summary | Legacy unless promoted |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic elementwise n5 summary | Legacy unless promoted |
| `outputs/cluster1/task_agnostic_g_elementwise_n5_l4_rerun_summary.md` | 0.6.0 | `OUTPUT_SUMMARY` | Historical task-agnostic elementwise n5 rerun summary | Legacy unless promoted |

## Known Exclusions

These are not versioned here:

- `.venv/**` markdown: vendored dependency docs.
- `.pytest_cache/**` markdown: tool cache docs.
- `.claude/worktrees/**` markdown: duplicate nested worktree copies.
- Raw JSONL, JSON, PNG, Python, GBNF, YAML, and manifest files: important, but
  not markdown documents. They are referenced by owner docs instead.

## Maintenance Checklist

When a markdown file is added, edited, promoted, superseded, or deleted:

1. Update its row here.
2. Bump the row version.
3. Update the registry changelog if the change affects policy, authority, or
   navigation.
4. Update `docs/handoff/agentic_document_hub.md` if the file belongs in an
   issue pull set or shelf.
5. Update `docs/handoff/stale_docs_inventory.md` if the change affects
   citation status or stale risk.
