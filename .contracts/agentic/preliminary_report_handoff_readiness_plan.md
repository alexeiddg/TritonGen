# Preliminary Report Handoff Readiness Plan

**Status:** agentic/internal execution plan; gitignored unless explicitly promoted
**Date:** 2026-05-21
**Audience:** Codex or another engineering agent preparing the Cluster 1 + Cluster 2 preliminary technical-report handoff
**Do not cite directly:** promote distilled decisions, definitions, and artifact identities into tracked docs before citation.

## Framing Sentence

Treat this as codebase handoff preparation for a preliminary Cluster 1 + Cluster 2 technical report. The deliverable is not a research paper; it is a deeply traceable explanation of what was built, why decisions were made, how the experiment works, what artifacts are authoritative, what caveats remain, and what Cluster 3 must inherit to avoid drift.

## Immediate Objective

Turn the current research and development history into a tracked, readable, auditable documentation layer that answers:

1. What problem is being studied.
2. What Cluster 1 and Cluster 2 actually do.
3. Why Modal exists in the architecture.
4. What decisions changed over time and why.
5. Which artifacts and results are authoritative.
6. Which old docs, audits, and scratch plans are historical only.
7. What Cluster 3 must inherit so the project does not repeat methodology drift.

This is a handoff-readiness and methodology reconstruction project. It is a documentation-control pipeline. Do not start by writing the preliminary report itself, and do not turn this into broad repository cleanup.

## Source-Of-Truth Hierarchy

Future agents must use this hierarchy when docs, audits, contracts, and code disagree:

1. Current code and tests define actual behavior.
2. Current output artifacts define observed results.
3. `docs/` defines human-readable methodology.
4. `.contracts/research/` defines formal methodology constraints.
5. `audits/` provides historical evidence and verification records.
6. `.contracts/agentic/` provides agent working context only and is not citation-grade unless promoted.

Reason: audits may be stale, contracts may lag implementation, and ignored agent docs may contain useful but non-authoritative text. The hierarchy tells future agents what to trust first.

## Citation Grade Vs Evidence Grade

Use this distinction when preparing the preliminary report.

Citation-grade sources:

- `README.md`;
- `docs/*.md`;
- `.contracts/research/*.md`;
- current artifact registry;
- final analyzer outputs.

Evidence-grade sources:

- `audits/*.md`;
- git history;
- test outputs;
- ignored agent plans;
- intermediate smoke reports.

The preliminary report should cite or rely on citation-grade docs. It may mention audits as supporting evidence, but audits should not be the primary methodology source unless their conclusions have been promoted.

## Repository Roles

Use these boundaries consistently:

| Location | Role | Policy |
| --- | --- | --- |
| `docs/` | Human-readable, tracked, report-facing source of truth | Create after inventory. Keep clean and citation-grade. |
| `.contracts/research/` | Formal constraints and methodology contracts | Update after methodology docs and decision log stabilize. |
| `.contracts/agentic/` | Agent work instructions, local plans, scratch notes | Keep ignored unless explicitly promoted. |
| `audits/` | Evidence trail and investigation records | Preserve; conclusions must be distilled elsewhere before citation. |
| `outputs/` | Raw and derived artifacts/results | Reference by path, schema, hash/count, provenance, and caveat; do not rewrite into docs. |
| `README.md` | Short project entry point | Update navigation after the docs skeleton exists. |

Current ignore intent: `.contracts/agentic/*`, `docs`, `audits`, and `outputs` are ignored unless `.gitignore` is changed later. This plan should remain internal until the user chooses to track documentation.

## Canonical Documentation Architecture

When promoted into tracked docs, target this structure:

```text
docs/
  00_project_map.md
  01_research_story.md
  02_methodology_cluster1.md
  03_methodology_cluster2.md
  04_modal_infrastructure.md
  05_artifacts_and_results_registry.md
  06_failure_taxonomy_and_eval_ladder.md
  07_analysis_and_statistics.md
  08_decision_log.md
  09_preliminary_report_outline.md
  10_cluster3_drift_prevention_plan.md
  handoff/
    codebase_handoff_guide.md
    runbook_cluster1_cluster2.md
    stale_docs_inventory.md
```

Do not create all files blindly in one pass. Build them from inventory, artifacts, tests, code paths, and audits.

## Story To Preserve

The preliminary report should begin with the experimental story, not with Triton internals:

> We are testing whether control mechanisms improve LLM-generated Triton kernels. The study currently covers a 2^2 subset: no control, grammar guidance, correctness feedback, and grammar plus correctness feedback. Cluster 1 established grammar-guided generation and compile-only evaluation. Cluster 2 added correctness-feedback repair, replay controls, Modal execution, paired analysis, and a stricter evaluation ladder. The current preliminary report documents what was built, why it was built, which findings are supported, and what remains caveated before Cluster 3.

### Layer 1: Plain-Language Problem

Explain for non-experts:

- A GPU kernel is low-level code that runs many operations in parallel.
- Triton is a Python-like language for writing GPU kernels.
- LLMs can generate Triton code, but failures often happen at parse, compile/runtime, or numerical-correctness stages.
- The research question is whether inference-time control mechanisms improve generation.

### Layer 2: Experimental Factors

Use consistent report names:

| Report name | Code condition | Meaning |
| --- | --- | --- |
| None | `none` | Baseline generation/replay without grammar or correctness repair. |
| G / C1 | `G` | Task-agnostic grammar-guided decoding plus semantic post-validation. |
| C / C2 | `C` | Correctness-feedback repair without grammar. |
| G+C / C1+C2 | `G+C` | Grammar-guided generation plus correctness-feedback repair. |

Naming boundary:

- Cluster 1 is the implementation layer for `G`.
- Cluster 2 is the implementation layer for `C` and `G+C`.
- `C1+C2` is informal shorthand for `G+C`, not a separate cluster.
- The factor names in analysis and reporting are `G` and `C`.

### Layer 3: Evaluation Ladder

Use this ladder:

| Level | Meaning | Used where |
| --- | --- | --- |
| Level 0 | Parse/signature/surface validity | Cluster 2 eval |
| Level 1 | Compile/runtime launch | Cluster 1 and Cluster 2 |
| Level 2 | Numerical correctness | Cluster 2 |
| F0/F1/F2/F3 | Failure taxonomy | Analysis/reporting |

Important boundary:

- Cluster 1 is compile-only and does not prove functional correctness.
- Cluster 2 adds correctness evaluation and correctness-feedback repair.
- For preliminary analysis, Cluster 1 functional success is normalized as false/unproven because Cluster 1 did not run Level 2.

### Layer 4: Modal Infrastructure

Justify Modal as methodology infrastructure:

- Local hardware is not enough for reliable repeated GPU generation and evaluation.
- Modal provides controlled cloud GPU execution with L4 workers for paper-scale Cluster 2 runs.
- Modal runs model generation, compile/eval, and remote correctness checks.
- Provenance fields are required: model revision, tokenizer revision, Modal image provenance, grammar hash, package versions.
- Durable row writing is part of the methodology because long Modal runs can fail mid-run.

### Layer 5: Traceability

Every substantial claim should trace through:

```text
claim -> contract/doc -> code path -> test -> artifact -> analysis output
```

Example:

```text
G uses task-agnostic grammar
-> docs/02_methodology_cluster1.md
-> cluster1/grammar/triton_kernel_agnostic.gbnf
-> cluster2/modal/generation.py routing
-> cluster2/tests/test_...
-> outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
-> outputs/analysis/factorial_2x2_preliminary.json
```

## Phase State And Agent Handoff

If the user asks to launch a phase with agents or resume after context compaction, maintain an ignored phase-state note:

```text
.contracts/agentic/preliminary_report_phase_state.md
```

Recommended fields:

```text
current_phase:
last_completed_phase:
active_deliverable:
files_changed:
evidence_gathered:
verification:
open_questions:
next_agent_prompt:
```

Each phase should leave a compact baton for the next agent. The baton should point to durable files and exact next actions, not hidden chat context.

## Phased Execution Plan

Run these phases as bounded tasks. Prefer one phase per Codex session or commit-sized review unit. Keep each phase scoped to no more than one or two output documents unless the user explicitly expands scope.

### Phase 0: Repository Inventory And Stale-Doc Audit

Goal: know what exists before rewriting documentation.

Output:

```text
audits/repository_documentation_methodology_readiness_audit.md
```

Required contents:

- folder-by-folder inventory;
- all markdown files;
- all contracts;
- all audits;
- all outputs;
- all current artifacts;
- all ignored docs;
- git status and recent commits;
- likely authoritative files vs stale/historical files.

Classify each relevant file:

| Classification | Meaning |
| --- | --- |
| `AUTHORITATIVE_CURRENT` | Current source of truth or evidence. |
| `NEEDS_UPDATE` | Useful but stale or incomplete. |
| `LEGACY_EVIDENCE` | Historical evidence only. |
| `AGENT_INTERNAL` | Scratch/plan/prompt-like material. |
| `DELETE_CANDIDATE_LATER` | Candidate for archival/removal after review. |
| `UNKNOWN` | Requires further investigation. |

Constraints:

- No code changes.
- No tracked docs changes.
- Do not rewrite audit history.
- If the audit already exists, update only after reading it and preserving useful prior findings.

Acceptance checks:

- `git status --short` shows only the intended audit change, if any.
- The audit clearly labels ignored agent docs and raw outputs as non-canonical unless promoted.
- Current methodology claims are separated from historical evidence.

Negative checks:

- Do not decide new methodology in the inventory phase.
- Do not delete stale files.
- Do not treat audit text as citation-grade.

### Phase 1: Documentation Skeleton And Source-Of-Truth Hierarchy

Goal: create the empty or lightly populated tracked documentation frame, including trust rules.

Candidate outputs:

```text
docs/00_project_map.md
docs/handoff/codebase_handoff_guide.md
docs/handoff/stale_docs_inventory.md
```

Required content:

- project map from README to docs to artifacts to analyzer;
- source-of-truth hierarchy;
- citation-grade vs evidence-grade policy;
- list of docs still empty or intentionally skeletal.

Acceptance checks:

- The skeleton does not contain unsupported methodology claims.
- The docs clarify that audits and agent plans are evidence/context, not current source of truth.
- A future agent can see which docs still need content.

Negative checks:

- Do not fill detailed methodology from memory.
- Do not update formal contracts yet.
- Do not imply the docs are complete.

### Phase 2: Artifact And Result Registry

Goal: freeze result identities and prevent filename drift.

Create or update:

```text
docs/05_artifacts_and_results_registry.md
```

Canonical artifact table seed:

| Condition | Artifact | Rows | Role | Caveat |
| --- | --- | ---: | --- | --- |
| None | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | Baseline replay | Compile-only. |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | Grammar condition | 3 missing matmul rows. |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | Correctness repair | No grammar. |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | about 177 | Combined condition | Replay coverage caveat. |

Also register analyzer output when ready:

```text
outputs/analysis/factorial_2x2_preliminary.json
```

Required fields:

- condition;
- artifact path;
- row count;
- schema;
- role in analysis;
- source cluster;
- provenance fields present/missing;
- known caveats;
- authoritative status;
- linked audit or run report.

Acceptance checks:

- Every result claim in later docs cites this registry first.
- Missing rows and replay caveats are explicit.
- Raw outputs are referenced, not copied.
- Every artifact has row count, schema, provenance, and caveat entries before use in analysis.

Negative checks:

- Do not claim complete 180/180 G coverage if the authoritative artifact is 177/180.
- Do not use old n=5 artifacts for current paper-scale claims.
- Do not mutate output artifacts while documenting them.

### Phase 3: Cluster 1 Methodology Documentation

Goal: explain the current Cluster 1 methodology and caveats in human-readable form.

Create or update:

```text
docs/02_methodology_cluster1.md
```

Required content:

- what Cluster 1 is;
- why grammar guidance exists;
- how task-agnostic `G` works;
- how semantic post-validation fits `G` acceptance;
- what files implement it;
- what tests support it;
- which artifacts prove it;
- what caveats remain.

Acceptance checks:

- Cluster 1 is described as compile-only.
- Task-agnostic `G` is primary.
- Template grammar is diagnostic/reference only.
- Claims trace to code, tests, artifacts, and analyzer behavior.

Negative checks:

- Do not claim Cluster 1 functional correctness.
- Do not present template grammar as the primary `G` condition.
- Do not overstate grammar guidance as general Triton synthesis beyond the documented scope.

### Phase 4: Cluster 2 Methodology Documentation

Goal: explain the current Cluster 2 methodology and its relationship to Cluster 1.

Create or update:

```text
docs/03_methodology_cluster2.md
```

Required content:

- what Cluster 2 is;
- why correctness-feedback repair exists;
- condition routing for `C` and `G+C`;
- replay controls for `none` and `G`;
- F2-only repair policy;
- Level 0/1/2 evaluation responsibilities;
- paired identity and seed semantics;
- what files implement it;
- what tests support it;
- which artifacts prove it;
- what caveats remain.

Acceptance checks:

- `C` repair observes and repairs only allowed failure classes.
- F0/F1 no-repair boundaries are explicit.
- G+C is described as composition of `G` plus correctness feedback, not as a new cluster.
- Replay controls and new-generation conditions are separated.

Negative checks:

- Do not claim Cluster 3 or `P` results.
- Do not claim full `2^3` factorial completion.
- Do not describe compile/runtime repair as part of `C` unless the current code and contracts support it.

### Phase 5: Evaluation Ladder, Failure Taxonomy, And Analyzer Semantics

Goal: define how results become reportable outcomes.

Create or update:

```text
docs/06_failure_taxonomy_and_eval_ladder.md
docs/07_analysis_and_statistics.md
```

Required content:

- Level 0/1/2 definitions;
- F0/F1/F2/F3 semantics;
- how Cluster 1 compile-only outcomes are normalized;
- how F3_EVAL_PIPELINE is handled;
- paired analysis rules;
- estimator and bootstrap behavior;
- analyzer inputs and outputs.

Acceptance checks:

- Every failure code has methodology semantics.
- Every metric maps to a stated research question.
- Analyzer behavior is connected to artifact registry fields.
- Cluster 1 functional_success false/unproven normalization is explicit.

Negative checks:

- Do not report performance, timing, speedup, or profiler metrics unless they are in scope and measured.
- Do not treat compile success as functional correctness.
- Do not hide F3 or pipeline failures inside successful compile claims.

### Phase 6: Modal Infrastructure And Provenance Documentation

Goal: explain why Modal exists and what reproducibility fields it must preserve.

Create or update:

```text
docs/04_modal_infrastructure.md
```

Required content:

- why local hardware is insufficient;
- what Modal runs;
- GPU policy for Cluster 2;
- durable row-writing rationale;
- model/tokenizer/image/package/grammar provenance;
- relevant code paths and tests;
- caveats for failed or partial Modal runs.

Acceptance checks:

- Modal is justified as reproducibility infrastructure, not incidental tooling.
- Provenance requirements are explicit.
- Durable row writes are tied to long-run failure recovery.

Negative checks:

- Do not recommend new Modal runs without required provenance fields.
- Do not treat partial runs as complete without registry caveats.
- Do not include local credential paths or secrets.

### Phase 7: Decision Log Extraction From Audits

Goal: turn audit history into a clean decision record.

Create or update:

```text
docs/08_decision_log.md
```

Seed decisions:

| Date/phase | Decision | Why | Evidence | Current status |
| --- | --- | --- | --- | --- |
| Task-agnostic G adopted | Avoid template confound | G vs G+C must share grammar semantics | audits/fix reports, grammar artifacts | locked |
| F0/F1 terminate C repair | Prevent compile-feedback leakage | C should only use correctness feedback | tests and runner behavior | locked |
| Durable Modal row writes | Avoid total run loss | Long G+C run partially survived crash | artifact evidence | locked |
| F3_EVAL_PIPELINE policy | Conservative evidence semantics | Avoid compile_success contradiction | analyzer fix report | locked |
| Cluster 1 functional_success false | Compile-only Cluster 1 scope | No Level 2 evidence in C1 | analyzer normalization | locked |

Rules:

- Promote decisions, not raw prompts.
- Include evidence paths.
- Mark superseded decisions as historical rather than deleting them.
- Keep wording citation-safe.

Acceptance checks:

- Every decision has a reason and evidence.
- Current status is one of `locked`, `superseded`, `deferred`, or `open`.
- No raw agent instructions are copied into tracked docs.

Negative checks:

- Do not track every audit note as a decision.
- Do not preserve obsolete methodology as current because it appears in an audit.
- Do not cite ignored agent plans as methodology.

### Phase 8: README And Formal Contract Alignment

Goal: align entry-point navigation first, then formal methodology contracts after docs stabilize.

Split this phase:

```text
8a. Update README navigation after the docs skeleton exists.
8b. Update formal contracts after methodology docs and decision log are stable.
```

Candidate targets:

```text
README.md
.contracts/research/research_scope.md
.contracts/research/eval_metrics.md
.contracts/research/scale_policy.md
cluster1/README.md
cluster2/README.md
```

Lock these statements:

- current preliminary report is a `2^2` subset, not full `2^3`;
- Cluster 3 / `P` is deferred;
- task-agnostic `G` is primary;
- template `G` is diagnostic/reference only;
- `G` acceptance means GBNF decoding plus semantic post-validation;
- Cluster 1 is compile-only;
- Cluster 2 uses Level 0/1/2 evaluation;
- `C` repair only runs on F2 numerical-correctness failures;
- F0/F1 do not receive C repair;
- Modal provenance is required;
- paired analysis uses matched seeds/identity where valid.

Acceptance checks:

- README gets readers to canonical docs quickly.
- Contracts are precise, non-agentic, and citation-safe.
- Cluster 1 compile-only scope is not overstated.
- The docs do not claim a full `G/C/P` factorial.

Negative checks:

- Do not update formal contracts before methodology language is stable.
- Do not let README become a second methodology source of truth.
- Do not copy agent-plan prose into contracts.

### Phase 9: Preliminary Report Outline

Goal: prepare the report scaffold without writing the final paper.

Create:

```text
docs/09_preliminary_report_outline.md
```

Recommended outline:

1. Executive summary
2. Plain-language background
3. Research question
4. Experimental design
5. Factor definitions
6. Dataset and kernels
7. Cluster 1 methodology
8. Cluster 2 methodology
9. Modal infrastructure
10. Evaluation ladder and failure taxonomy
11. Artifacts and provenance
12. Statistical analysis
13. Preliminary results
14. Failure-mode analysis
15. Threats to validity
16. Reproducibility checklist
17. Lessons for Cluster 3

Acceptance checks:

- The outline reads like a detailed technical-report scaffold.
- It explicitly avoids unsupported final-paper claims.
- It points to the docs that must supply each section.

Negative checks:

- Do not claim full `2^3` factorial completion.
- Do not claim Cluster 3 / `P` results.
- Do not claim Cluster 1 functional correctness.
- Do not describe template grammar as the primary `G` condition.
- Do not claim complete 180/180 `G` coverage if the artifact is 177/180.
- Do not include performance, timing, or speedup results unless actually measured under scope.

### Phase 10: Cluster 3 Drift-Prevention Plan

Goal: encode what Cluster 3 must inherit from Cluster 1 and Cluster 2.

Create:

```text
docs/10_cluster3_drift_prevention_plan.md
```

Required guardrails:

- definitions before code;
- artifact registry before runs;
- schema contract before Modal;
- shared eval ladder reuse;
- no new result fields without analyzer update;
- no paper-scale run until n=1 smoke plus n=5 dev plus audit;
- every condition has a paired identity specification;
- every failure code has methodology semantics;
- docs updated in the same PR/commit as code;
- every new metric maps to a stated research question;
- every new artifact has a row-count, schema, provenance, and caveat entry before use in analysis;
- every new feedback/control mechanism declares which failure classes it is allowed to observe and modify.

Acceptance checks:

- Cluster 3 cannot introduce `P` semantics without defining failure and repair boundaries.
- New fields and artifacts have analyzer and registry requirements.
- Scale gates are explicit.
- Performance/profiler semantics are tied to a declared metric contract.

Negative checks:

- Do not allow undefined `P` semantics.
- Do not add profiler/performance fields without a declared metric contract.
- Do not allow new Modal runs without provenance fields.
- Do not allow new result fields without analyzer support.
- Do not allow paper-scale runs from an unvalidated smoke path.

### Phase 11: Final Documentation Consistency Audit

Goal: run one read-only consistency check after the docs are written.

Output:

```text
audits/final_preliminary_report_documentation_consistency_audit.md
```

Audit questions:

- Does every current methodology claim have a code path, test path, artifact path, and analysis path?
- Are any docs still claiming old methodology?
- Are any ignored docs being used as source of truth?
- Can a new person follow `README.md` -> `docs/` -> artifacts -> analyzer without agent context?
- Do artifact registry row counts and caveats match the current outputs and audits?
- Do formal contracts agree with the human-readable docs?

Acceptance checks:

- The audit is read-only except for its own output.
- The audit lists required fixes by path and severity.
- No preliminary report writing starts until blocking inconsistencies are resolved or explicitly caveated.

Negative checks:

- Do not rewrite docs during the audit pass.
- Do not hide contradictions by changing claims without evidence.
- Do not treat ignored `.contracts/agentic/` files as final authority.

## Promotion Pipeline

Use this flow:

```text
agent/audit scratch -> extracted claim or decision -> tracked doc -> cited by report
```

Keep raw agent docs ignored when they:

- contain instructions to Codex;
- are verbose;
- include obsolete reasoning;
- are not meant for human readers;
- contain "do this next" prompts.

Promote content into tracked docs when it contains:

- final decisions;
- methodology definitions;
- artifact identities;
- failure semantics;
- statistical choices;
- known caveats;
- run results;
- codebase invariants.

Never copy raw agent prose directly into tracked docs. Distill it.

Example:

```text
Raw audit:
G+C hash gate still referenced stale g_task_agnostic_n5_l4_rerun...

Tracked decision:
G+C replay artifact was updated to use g_task_agnostic_aligned_pipeline_n20_l4.
The n=5 artifact is legacy and must not be used for current G+C analysis.
```

## Practical Next Task Order

1. Phase 0: inventory and stale-doc audit.
2. Phase 1: documentation skeleton and source-of-truth hierarchy.
3. Phase 2: artifact and result registry.
4. Phase 3: Cluster 1 methodology documentation.
5. Phase 4: Cluster 2 methodology documentation.
6. Phase 5: evaluation ladder, failure taxonomy, and analyzer semantics.
7. Phase 6: Modal infrastructure and provenance documentation.
8. Phase 7: decision log extraction from audits.
9. Phase 8a: README navigation.
10. Phase 8b: formal contract alignment.
11. Phase 9: preliminary report outline.
12. Phase 10: Cluster 3 drift-prevention plan.
13. Phase 11: final documentation consistency audit.

## Commit Strategy For Later Promotion

When the user decides to track docs, prefer small commits:

1. `docs: add repository inventory and documentation audit`
2. `docs: add documentation skeleton and source-of-truth policy`
3. `docs: add artifact and results registry`
4. `docs: lock cluster1 methodology`
5. `docs: lock cluster2 methodology`
6. `docs: document evaluation ladder and analyzer semantics`
7. `docs: document modal infrastructure and provenance`
8. `docs: add decision log from audits`
9. `docs: update root README navigation`
10. `docs: align research contracts`
11. `docs: add preliminary report outline`
12. `docs: add cluster3 drift prevention plan`
13. `docs: add final documentation consistency audit`

Do not bundle all documentation architecture into one large commit.

## Working Rules For Future Agents

- Read `.contracts/README.md` before editing contract or documentation surfaces.
- Start each phase by checking `git status --short`.
- Use `rg --files -u` or `find` when inspecting ignored docs and outputs.
- Treat ignored `.contracts/agentic/` files as context, not as citation sources.
- Treat audits as evidence records that may be stale until verified.
- Use structured parsers or existing analyzers for row counts and JSON/JSONL validation.
- Preserve unrelated dirty worktree changes.
- Do not mutate output artifacts while documenting them.
- Do not claim functional correctness for Cluster 1 unless Level 2 evidence exists.
- Do not claim full `2^3` factorial coverage in the preliminary Cluster 1 + Cluster 2 report.
- For launched phase agents, require the agent to update `.contracts/agentic/preliminary_report_phase_state.md` or produce an equivalent handoff note.
- After context compaction, resume from durable files rather than hidden conversation context.

## Done Definition

This handoff-readiness effort is complete when:

- authoritative artifacts are registered by path, row count, schema, provenance, role, and caveat;
- source-of-truth hierarchy and citation-grade policy are visible in tracked docs;
- Cluster 1 and Cluster 2 methodology docs are readable and traceable;
- Modal infrastructure is justified as part of reproducibility, not incidental tooling;
- failure taxonomy and evaluation ladder semantics are explicit;
- every metric maps to a stated research question;
- decisions from audits are distilled into a clean decision log;
- stale docs are labeled with current disposition;
- README navigation points to the canonical docs without becoming a duplicate methodology source;
- formal contracts align with the stabilized methodology docs;
- the preliminary report outline has enough structure to write from;
- Cluster 3 has a drift-prevention plan before implementation work begins;
- a final consistency audit confirms that current claims trace to code, tests, artifacts, and analyzer outputs.
