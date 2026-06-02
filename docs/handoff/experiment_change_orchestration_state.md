# Experiment Change Orchestration State

- Version: 1.4.10
- Date: 2026-06-02
- Status: active live state record
- Owner: current orchestration agent
- Contract: `docs/15_experiment_change_orchestration_contract.md`
- Citation status: operational state only; do not cite as methodology or result
  evidence

## Purpose

This is the canonical live state file for orchestrating the docs 12-14 change
set. It records active branches, worktrees, serialized-surface leases, gates,
run approvals, and next allowed actions.

Future agents must read and update this file before starting, merging,
abandoning, or executing work governed by
`docs/15_experiment_change_orchestration_contract.md`.

## State Rules

- Update this file before starting a new implementation branch.
- Update this file before taking or releasing a serialized-surface lease.
- Update this file before requesting or executing any Modal/output-mutating run.
- Update this file after merging, abandoning, or superseding a work package.
- During parallel work, only the orchestrating agent directly edits this file.
  Worker agents must provide handoff notes or patch proposals unless they have
  explicitly taken the orchestrator role and recorded that transfer.
- If this file contradicts current code, tests, artifact registry entries, or
  git/worktree state, stop and reconcile the mismatch before continuing.
- This file does not authorize Modal, n=5, n=20, paper-scale work, output
  mutation, profiler, timing, speedup, or benchmark work.
- The orchestration contract is frozen for implementation use. Add process only
  when a concrete amendment trigger is recorded.

## Edge-Case Guardrails

These guardrails handle failure modes that are easy for parallel agents to miss.
They apply to all packages unless a later approved contract explicitly replaces
them.

### Freshness Check

Before starting any package, taking a lease, writing a run packet, or executing
approved work, re-read these files in this order:

1. `docs/handoff/experiment_change_orchestration_state.md`
2. `docs/handoff/document_version_registry.md`
3. `docs/handoff/agentic_document_hub.md`
4. the package-specific owner docs listed in the work package card

Do not rely on `git status` alone. The operational docs, audit reports, and
outputs are ignored by git in this workspace and can change without appearing in
normal status output.

### State Drift Reconciliation

If the state file, registry, hub, artifact registry, audit reports, or current
filesystem disagree:

- stop implementation or execution work;
- identify the newest source by direct file inspection, not git status;
- preserve all conflicting files;
- update this state file only after the conflict is understood;
- record the reconciliation in the package handoff;
- do not run Modal or mutate outputs while drift is unresolved.

When in doubt, current registered artifacts and their audit reports define what
has actually been run; this state file defines what may happen next only after
it is reconciled to those facts.

### Conflict Resolution Order

If docs, specs, workers, artifacts, or tests disagree, resolve authority in this
order:

1. current code and tests for executable behavior;
2. current registered artifacts, hash sidecars, and audit reports for observed
   results;
3. `docs/15_experiment_change_orchestration_contract.md` for sequencing, gates,
   and run permissions;
4. this live state file for current branches, leases, packets, and next allowed
   actions;
5. component implementation specs for local design details;
6. source planning docs such as docs 12 through 14 for design intent;
7. explicit user decision.

Record the conflict, chosen authority, and required follow-up before continuing.

### Partial Artifact Protocol

If a run writes zero rows, fewer rows than expected, rows without a matching
hash sidecar, a sidecar without matching rows, or any malformed row artifact:

- preserve the artifact and sidecar exactly as written;
- do not overwrite, append, or silently delete it;
- mark the artifact as `blocked`, `partial`, or `zero-row` in the run handoff;
- validate hashes when possible and record validation failures explicitly;
- scan for private-eval and performance/profiling leakage when rows exist;
- require an audit before any resume, retry, archive, overwrite, or rerun;
- do not count the artifact as successful development or paper evidence.

### Cost And Stop Limits

Every run approval packet must include hard limits:

```text
max rows:
max generation attempts:
max repair attempts per row:
max wall clock:
max estimated cost:
stop on first infrastructure/F3: yes/no
```

Default stop policy:

- stop on first Modal timeout, preemption, worker interruption, auth/config
  failure, image failure, or synthesized infrastructure `F3_EVAL_PIPELINE`;
- stop on row-count mismatch;
- stop on schema validation failure;
- stop on hash sidecar mismatch;
- stop on P firing outside `F1_COMPILE`;
- stop on C firing outside eligible F2 conditions;
- stop on private-eval leakage;
- stop on performance/profiler/timing/speedup leakage.

Any exception must be written into the run approval packet before execution.

### Secrets And Credentials Boundary

Workers must not print, persist, or add telemetry for secrets, credentials,
tokens, billing credentials, private keys, environment dumps, private eval data,
or unapproved local machine paths. Approved artifact paths, repo-relative paths,
and explicitly listed non-secret runtime identifiers are allowed.

Credentialed access must be listed in the launch packet or run packet before it
happens, including the credential class, exact operation, redaction plan, and
verification method.

### Network And Dependency-Download Policy

Workers default to offline/no-network behavior. Package installs, lockfile
updates, model or tokenizer downloads, billing API calls, Modal API calls, web
fetches, and external-service calls are forbidden unless explicitly authorized
in the launch packet or run packet.

Record any authorized network or download operation:

```text
operation:
tool/command:
target host or service:
credentials required: yes/no
files changed:
cache/output paths:
reason:
approval source:
```

Unexpected network need is an escalation condition.

### No Silent Defaults

A run packet is invalid if any of these fields are omitted:

```text
condition
kernel_class
dtype
n
scale_tier
repair_history_policy
observability policy
grammar policy or grammar variant
target output path
overwrite/archive policy
max rows
max attempts
max wall clock
max estimated cost
```

Use explicit `not_applicable`, `not_enabled`, or `unavailable` values rather
than leaving fields blank. Do not infer run-critical fields from filenames.

### Abandoned Work Protocol

Before marking a branch, package, lease, or run plan abandoned:

- update the package card status to `abandoned`;
- release or mark abandoned any active leases;
- record files touched, artifacts touched, and whether any Modal/output mutation
  occurred;
- record tests or checks already run;
- record whether partial work can be safely reused;
- record the rollback or cleanup path;
- update `Next Allowed Actions` if abandonment unblocks or blocks downstream
  work.

Never leave a serialized-surface lease active after abandoning a package.

### Orchestrator Dry Run

Before launching multiple parallel workers or promoting the first branch from a
new orchestration cycle, perform a no-code dry run:

```text
simulate launching O0/A1/S0 or the requested package set
simulate assigning and releasing one serialized-surface lease
simulate rejecting a worker without a launch packet
simulate rejecting an invalid run packet
simulate promoting one branch through the merge train
simulate handling one stale worktree
record ambiguity found:
```

If ambiguity remains, patch the contract or this state file before launching
workers.

### Independent Review Gate

Before promotion, require independent review for any branch touching runners,
Modal behavior, analyzer semantics, report data, repair-loop policy, C/P
eligibility, result schemas, artifact paths, sidecars, dependencies, lockfiles,
model/tokenizer revisions, CUDA/Triton versions, or Modal image definitions.

The reviewer must not be the implementing agent. Record review status, findings,
and fixes in the handoff.

### Fixture-First Rollout Gate

Before a new behavior reaches Modal, paid, generation, n=5, n=20, or
output-mutating execution, prove it through a local fixture, synthetic artifact,
or minimal no-remote contract test. The run packet must include the fixture
proof or an explicit user-accepted exception.

### Negative-Test Requirement

High-risk guardrails need at least one negative test, rejection fixture, or
recorded fail-closed check before the related gate can close. Examples include
invalid sidecar path rejection, mixed-policy artifact quarantine, C outside F2
rejection, P outside `F1_COMPILE` rejection, unsupported report-claim rejection,
and invalid run-packet rejection.

If the negative test cannot be added yet, record the blocker and keep the
downstream gate closed.

### Orchestrator Escalation Thresholds

Stop and ask for user direction, or patch the contract/state, when any of these
occur:

- repeated test failure after two focused fix attempts;
- unresolved authority conflict after applying the conflict-resolution order;
- unexpected output mutation, generated artifact, or sidecar write;
- new dependency, lockfile change, model/tokenizer download, Modal image change,
  or network access not listed in the launch packet;
- branch scope grows beyond one work package;
- suspected secret, credential, private-eval, hidden-data, or unapproved path
  exposure;
- default behavior or run eligibility would change;
- paid or output-mutating run would proceed with an untested guardrail.

### Post-Merge Verification Window

After each branch promotion, record a short integration verification before
unblocking the next dependent package:

```text
merged branch:
integration baseline:
serialized leases released/transferred:
targeted smoke or import check:
affected docs/registry/state versions checked:
default-invariance still holds:
negative tests still pass or were re-run:
next package unblocked:
remaining caveats:
```

### Maximum Branch Scope

Each branch owns one work package by default. Do not absorb adjacent fixes,
refactors, dependency updates, or extra cleanup unless the launch packet,
requirement IDs, leases, tests, and review gates are updated before the extra
work starts.

### Contract Freeze And Amendment Policy

The orchestration contract is frozen for implementation use. Do not add more
process requirements unless one of these amendment triggers occurs:

- an implementation agent hits an ambiguity that blocks work;
- the orchestrator dry run fails;
- an independent review finds a missing guardrail;
- a component implementation spec exposes a real conflict;
- a post-merge verification window finds an integration failure;
- a run approval packet exposes an unhandled safety, provenance, cost, or
  artifact-control issue;
- the user approves a new workstream, run type, dependency, network operation,
  credentialed operation, output mutation, or paper-scale decision.

Amendment template:

```text
trigger:
affected packages:
changed gates:
added requirements:
removed requirements:
state-file update required: yes/no
registry update required: yes/no
downstream agents to notify:
version bump:
```

Prefer the narrowest sufficient document. If a package launch packet, component
spec, run packet, or state-file entry can resolve the issue, do not expand the
orchestration contract.

### Stale Worker And Worktree Cleanup

If a worktree, branch, or worker handoff passes its review checkpoint without a
current owner:

- inspect the branch/worktree diff without discarding it;
- record files touched, leases held, tests run, and artifacts touched;
- release, renew, or mark abandoned every lease;
- block merge from that branch until it is rebased onto the current baseline and
  revalidated;
- preserve useful patches or handoff notes before deleting or ignoring the
  worktree.

Do not use stale worker output as a merge source until this cleanup is recorded.

### Provenance Freeze For Runs

Before approving a run, the approval packet must record:

Because `docs/`, `audits/`, and `outputs/` are ignored by git, planning-doc
fingerprints must be explicit document versions and audit references. Do not use
a git commit alone as run provenance.

```text
git commit:
branch/worktree:
orchestration contract version:
state file version:
document registry version:
component spec versions:
artifact registry version or audit references:
model id:
model revision:
tokenizer revision:
prompt/template version:
repair_history_policy:
grammar policy:
grammar variant:
grammar hash:
scale tier:
Modal image id or unavailable reason:
output path:
```

If a value is unavailable before approval, record it as `unavailable` with a
reason. Do not backfill missing provenance silently after execution.

## Current Baseline

| Field | Value |
|---|---|
| Git baseline commit | `aa4d20f1f5c64932e72b488d131244542e44459f` |
| Git branch | `codex-track-handoff-context` as temporary trunk; MLflow integration promoted at `28c52f2` |
| Git status at latest reconciliation | clean after MLflow integration promotion; no Modal, output mutation, or MLflow runtime artifact committed |
| Orchestration contract version | `docs/15_experiment_change_orchestration_contract.md` v1.0.11 |
| Registry version at state reconciliation | `docs/handoff/document_version_registry.md` v1.38.1 |
| Observability spec version | `docs/16_observability_sidecar_implementation_spec.md` v0.2.0 |
| Structural/task analyzer metadata spec version | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.2 |
| MLflow tracking policy version | `.contracts/research/mlflow_tracking_policy.md` v1.0.0 |
| Current Cluster 3 gate | Phase 14e four-cell n=5 development matrix frozen with warnings; no broader run without explicit approval packet |
| Paper-scale status | blocked; no Cluster 3 `n=20` until Gate G8 |

Important repository note: on the handoff trunk, `docs/`, `audits/`, and
`.contracts/agentic/**` are intentionally trackable. Raw outputs and MLflow
runtime state remain ignored. A clean `git status` still does not prove raw
output artifacts are unchanged; inspect `outputs/` directly when relevant.

## Active Worktrees

| Worktree | Branch | Commit | State ownership |
|---|---|---|---|
| `/Users/alexeidelgado/Desktop/TritonGen` | `codex-track-handoff-context` | `28c52f2` plus promotion-state update | temporary trunk with MLflow integration promoted; no Modal or output mutation |
| `/private/tmp/tritongen-llm-repair-memory` | `codex/llm-repair-memory-agentic-transcript-v1` | `368a3c8` | A1 prompt core committed and clean; awaiting trunk update after MLflow integration |
| `/Users/alexeidelgado/Desktop/TritonGen/.claude/worktrees/intelligent-pasteur-72d92f` | `claude/intelligent-pasteur-72d92f` | `b0085c1` | external/unknown to this orchestration state; reconcile before relying on it |

## Active Branches

| Branch | Stream/package | Worktree | Status | Notes |
|---|---|---|---|---|
| `codex-track-handoff-context` | temporary trunk | `/Users/alexeidelgado/Desktop/TritonGen` when not on integration branch | active baseline | Treat as the working main branch for repair/handoff work until final branch repair is complete. |
| `codex/integrate-mlflow-into-handoff` | MLflow tracking harness integration | none after promotion | promoted | Merged `origin/ml_migration`, preserved handoff doc/audit tracking policy, validated optional/no-op tracking tests, and fast-forwarded into the temporary trunk at `28c52f2`. |
| `codex/llm-repair-memory-agentic-transcript-v1` | agentic repair memory | `/private/tmp/tritongen-llm-repair-memory` | A1 committed | A1 prompt core is committed at `368a3c8`; update from the MLflow-integrated trunk before A2/A3 integration work. |

## Active Serialized-Surface Leases

| Surface | Owner branch | Owner worktree | Scope | Start commit | Expected files | Expected tests | Review checkpoint | Status |
|---|---|---|---|---|---|---|---|---|
| none | none | none | none | none | none | none | none | none |

## Gate Status

| Gate | Status | Evidence / note |
|---|---|---|
| G0 baseline freeze | satisfied with caveat | Git status is clean, but ignored docs/audits/outputs must be checked directly when relevant. |
| G1 orchestration contract accepted | satisfied | Contract exists and is routed through project map, hub, and registry. |
| G2 reporting terminology stable | not started | Requires S0 acceptance. |
| G3 observability sidecar contract stable | spec drafted / code not started | `docs/16_observability_sidecar_implementation_spec.md` v0.2.0 defines O0-O4 plus hardening guardrails; G3 still requires implementation and tests. |
| G4 analyzer compatibility stable | spec drafted / code not started | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.2 defines S0-S3 metadata and report-label work; G4 still requires S1 implementation and compatibility tests. |
| G5 agentic prompt core stable | partially satisfied / pending promotion | A1 prompt core committed on `codex/llm-repair-memory-agentic-transcript-v1` at `368a3c8` with targeted prompt-core, boundary, import, diff-check, and forbidden-path validation; merge/review against the MLflow-integrated trunk is still required before treating it as trunk-stable. |
| G6 agentic integration stable | not started | Requires opt-in C/P integration and analyzer grouping. |
| G7 development run readiness | blocked pending fresh approval packet | Phase 14e matrix is frozen; any broader development-scale, all-condition, diagnostic, or paper-readiness run needs a new approval packet. |
| G8 paper-scale readiness | blocked | No `n=20` or paper-scale work. |

## Approved Run Packets

No active run packet is approved by this state record.

Historical context:

- Phase 14a `P` n=5 `elementwise` `fp32` already ran and is registered
  elsewhere. It produced five `F0_PARSE` rows, zero `F1_COMPILE` seeds, and
  zero P attempts. It is insufficient F1/P-loop signal and does not unblock
  `n=20`.
- Phase 14b `C+P` n=5 `elementwise` `fp32` already ran and is registered
  elsewhere. It produced five `F0_PARSE` rows, zero `F1_COMPILE` seeds, zero
  initial F2 rows, zero P attempts, and zero C attempts. It is insufficient
  repair signal and does not unblock `n=20`.
- Phase 14c `G+C+P` n=5 `elementwise` `fp32` already ran and is registered
  elsewhere. It produced five clean-success template-upper-bound diagnostic
  grammar rows, zero `F1_COMPILE` seeds, zero initial F2 rows, zero P attempts,
  and zero C fires.
- Phase 14d approved reuse of the validated Phase 12 `G+P` n=5 artifact as the
  Phase 14 matrix `G+P` cell.
- Phase 14e froze the four-cell n=5 development matrix with 20 schema-valid
  rows, validated hash sidecars, clean boundary scans, zero P attempts, and
  zero C fires. It is development-scale condition coverage only and does not
  unblock `n=20`.

## Rejected Or Expired Run Packets

| Run label | Status | Reason |
|---|---|---|
| none | none | none |

## Merged Packages

| Package | Status | Notes |
|---|---|---|
| orchestration contract | complete | `docs/15_experiment_change_orchestration_contract.md` created and routed. |
| operating-control addendum | complete | State record, lease, decision authority, run packet, merge protocol, and trust boundary added to the contract. |
| observability sidecar implementation spec | complete | `docs/16_observability_sidecar_implementation_spec.md` v0.2.0 created and routed; code implementation not started. |
| structural/task analyzer metadata implementation spec | complete | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.2 created and routed; analyzer/report code implementation not started. |
| MLflow tracking harness integration | complete | `origin/ml_migration` was merged into `codex-track-handoff-context` via `codex/integrate-mlflow-into-handoff` and promoted at `28c52f2`; tracking remains optional/no-op unless `TRITONGEN_MLFLOW` and `mlflow` are present, and JSONL remains the source of truth. |

## Abandoned Packages

| Package | Status | Reason |
|---|---|---|
| none | none | none |

## Known Caveats

- Raw `outputs/` and MLflow `mlruns/` runtime state are ignored; docs, audits,
  and `.contracts/agentic/**` are intentionally trackable on the handoff trunk.
- Known full-regression caveat remains:
  `cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`.
- Phase 14a is development-scale diagnostic only and insufficient F1/P-loop
  signal.
- Phase 14b is development-scale diagnostic only and insufficient repair signal.
- Phase 14c is development-scale diagnostic only and insufficient repair signal.
- Phase 14e is frozen development-scale condition coverage only with zero P
  attempts and zero C fires.
- No paper-scale Cluster 3 results exist.
- A1 agentic-memory prompt core is committed on the memory worktree branch, but
  not yet promoted to the handoff trunk.
- No observability sidecar implementation is active yet.
- No analyzer metric-registry implementation is active yet.

## Next Allowed Actions

Allowed without run approval:

1. Update `codex/llm-repair-memory-agentic-transcript-v1` from the
   MLflow-integrated handoff trunk before A2/A3 work.
2. Create remaining component implementation specs for:
   - agentic repair-memory implementation;
   - paper-scale readiness or future Cluster 3 run packet/spec, if explicitly
     requested.
3. Start safe parallel branches after adding package cards below:
   - S0 docs terminology;
   - O0 sidecar core;
4. Create serialized-surface leases before touching analyzer, runner, repair
   loop, result schema, raw output, or report-data-builder surfaces.

Not allowed without explicit approval:

- Modal execution;
- n=5 run execution;
- n=20 or paper-scale work;
- output overwrite or mutation;
- performance, profiler, timing, speedup, or benchmark work.

## Work Package Cards

Use this template for every package before work begins:

```text
package:
launch packet id:
branch:
owner:
scope:
requirement ids:
allowed files:
forbidden files:
serialized surfaces:
entry gate:
exit gate:
tests required:
default-invariance proof required: yes/no
fixture-first proof required: yes/no
independent review required: yes/no
negative tests required:
dependency/lockfile changes allowed: no unless explicitly listed
network/dependency-download/API calls allowed: no unless explicitly listed
secrets/credentials access allowed: no unless explicitly listed
docs required:
run/output mutation allowed: no
escalation thresholds:
handoff due:
status:
```

## Agent Launch Packet Template

Use this template before starting a delegated parallel worker:

```text
launch packet id:
agent role:
branch:
worktree:
baseline commit:
required read set:
package:
requirement ids in scope:
allowed files:
forbidden files:
serialized surfaces:
entry gate:
exit gate:
required tests/checks:
default-invariance proof required: yes/no
fixture-first proof required: yes/no
independent review required: yes/no
negative tests required:
dependency/lockfile changes allowed: no unless explicitly listed
network/dependency-download/API calls allowed: no unless explicitly listed
secrets/credentials access allowed: no unless explicitly listed
Modal/output mutation allowed: no unless approved run packet is attached
escalation thresholds:
stop triggers:
handoff destination:
state update owner: orchestrator
status:
```

### Package Backlog

| Package | Suggested branch | Status | Entry gate | Exit gate | Notes |
|---|---|---|---|---|---|
| S0 docs terminology | `codex/outcome-taxonomy-docs` | not started | G1 | G2 | Docs-only structural/task terminology alignment. |
| O-spec observability sidecar implementation spec | none | complete | G1 | spec routed | `docs/16_observability_sidecar_implementation_spec.md` v0.2.0. |
| S-spec structural/task analyzer metadata implementation spec | none | complete | G1 | spec routed | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.2; code implementation not started. |
| O0 sidecar core | `codex/observability-sidecar-core` | not started | G1 plus O-spec | G3 partial | New `shared/observability/*` schema/logger/redaction and tests only. |
| A1 prompt core | `codex/llm-repair-memory-agentic-transcript-v1` | committed / pending trunk promotion | G1 | G5 partial | Pure attempt evidence, anchor selector, transcript renderer, golden tests; committed at `368a3c8`, update from MLflow-integrated trunk before A2/A3. |
| S1 analyzer metadata | `codex/analyzer-metric-registry` | blocked | G2 plus S-spec plus lease | G4 partial | Requires `docs/17_structural_task_analyzer_metadata_implementation_spec.md` and `analyzer_metric_registry` lease. |
| O1 runner wall-clock | `codex/observability-runner-instrumentation` | blocked | O0 plus runner lease | G3 | One runner owner at a time. |
| A2 C-loop integration | `codex/agentic-memory-c2-integration` | blocked | A1 plus lease | G6 partial | Requires C-loop and Cluster 2 runner leases. |
| A3 P-loop integration | `codex/agentic-memory-c3-integration` | blocked | A1 plus lease | G6 partial | Requires P-loop and Cluster 3 runner leases. |
| S2 report builder | `codex/report-builder-outcome-families` | blocked | S1 | report labels stable | Requires report-data-builder lease if code is touched. |
| R2 Phase 14b run | `codex/cluster3-phase14b-c-plus-p-n5` | complete | G7 plus approval | registered diagnostic artifact | Completed elsewhere; insufficient repair signal. |
| R3 Phase 14c run | `codex/cluster3-phase14c-g-plus-c-plus-p-n5` | complete | G7 plus approval | registered diagnostic artifact | Completed elsewhere; insufficient repair signal. |
| R4 Phase 14d G+P reuse decision | `codex/cluster3-phase14d-gp-reuse` | complete | Phase 14c audit | reuse decision registered | Existing Phase 12 G+P n=5 artifact reused as matrix cell. |
| R5 Phase 14e matrix freeze | `codex/cluster3-phase14e-freeze` | complete | four cells present | matrix frozen with warnings | Development-scale condition coverage only; no P/C repair signal. |
| R6 paper-scale readiness or future run spec | `codex/cluster3-paper-readiness-plan` | not started | Phase 14e freeze plus relevant specs | run/go-no-go packet ready | Spec only; no Modal run without approval. |

## Validation Matrix

Every work package must list the exact commands or manual checks it used before
claiming its exit gate. If a command is not applicable, the handoff must say why
and name the replacement check.

### Shared Validation Rules

- Record exact commands, not summaries only.
- Record whether commands ran in the main workspace or a worktree.
- Treat the known Cluster 1 docs-lock failure as a caveat only when it is the
  first full-regression failure and no earlier targeted test failed.
- Do not count ignored-doc changes as clean unless the relevant docs were read
  directly.
- For any package that touches a serialized surface, include the active lease in
  the handoff.
- For any package touching runner code, include a no-unauthorized-run check.
- For any component implementation package, map requirement IDs to changed files
  and tests or manual checks before claiming the exit gate.
- For any high-blast-radius package, include a default-invariance proof showing
  legacy behavior is unchanged when new flags are absent, `off`, or legacy.
- For any new behavior used by a run packet, include fixture-first proof from a
  local fixture, synthetic artifact, or minimal no-remote contract test before
  any Modal, paid, generation, n=5, n=20, or output-mutating run.
- For high-risk guardrails, include a negative test, rejection fixture, or
  recorded fail-closed check before closing the related gate.
- For any runner, Modal, analyzer, repair-loop, result-schema, artifact-path,
  sidecar, dependency, model, tokenizer, CUDA, Triton, or lockfile branch,
  record an independent review before promotion.
- Keep branch scope to one work package unless the launch packet is updated
  before adjacent fixes, refactors, or extra cleanup begin.
- Record secrets/credentials and unapproved-path boundary checks for branches
  that touch telemetry, logging, sidecars, Modal, billing, generation, or run
  packets.
- Record network/API/dependency-download activity as absent or explicitly
  authorized.
- After promotion, record post-merge verification before unblocking dependent
  packages.
- Record dependency, lockfile, Modal image, CUDA/Triton/package version, model
  revision, and tokenizer revision diffs. If any changed without spec ownership,
  stop before promotion.

### Package Validation Requirements

| Package type | Required validation | Notes |
|---|---|---|
| S0 docs terminology | Claim-language scan over touched docs; unsupported-claim scan for paper-scale, n=20, pass@k, P/C lift, correctness improvement, performance, speedup, profiler, timing; direct review that C remains F2-only and P remains F1_COMPILE-only. | Docs-only; no code or output mutation. |
| S1 analyzer metadata | Analyzer unit tests; legacy 2^2 compatibility tests; tests that existing keys remain readable; tests that structural/task metadata is additive; metric-registry validator tests; deterministic golden compatibility snapshot; strict JSON-safe metadata round trip; alias-collision rejection; metric status/value consistency tests; partial/empty design behavior tests; condition/factor conflict tests; document-version provenance check; metadata size/cardinality check; mixed-gate or mixed-policy rejection/quarantine tests where implemented. | Requires `analyzer_metric_registry` lease. |
| S2 report builder/dashboard | Report-data builder tests; generated report data diff review; scan for bare `pass@k` without metric gate; manual table review for structural/task separation; legacy analyzer fallback test for `legacy_metadata_unavailable`; registry display-string escaping test; localization parity check or blocking deferral; S1/S3/fallback handoff path recorded. | Do not refresh analyzer output unless S3 is explicitly in scope. |
| S3 analyzer output rerun | Reproducible analyzer command; output path review; metadata/reportability review; primary-rate traceability check; artifact registry or audit note update. | Never rewrite raw JSONL artifacts. |
| O0 sidecar core | Schema validation tests; JSONL append round-trip tests; summary writer tests; source/private-eval/raw-feedback exclusion tests. | No runner integration yet. |
| O1 runner wall-clock | Targeted runner tests with telemetry enabled/disabled; sidecar path/key tests; no unauthorized Modal/output mutation check; existing runner CLI tests. | One runner owner at a time. |
| O2 Modal identity | Shared Modal runtime helper tests; remote response schema compatibility tests; fixture/backward-compatibility tests with missing optional context. | No new Modal app/image/function unless later spec authorizes it. |
| O3 token telemetry | Generation telemetry tests; tokenizer-source tests; sidecar join/key tests; row-schema stability check. | Token fields stay out of scientific rows unless later spec authorizes schema change. |
| O4 estimated cost | Pricing snapshot validation; formula unit tests; summary status tests separating estimated cost from actual billing. | No billing claim. |
| O5 billing reconciliation | CLI argument tests; attribution-confidence tests; dry-run or mocked billing API tests. | Real billing query requires approval if network/credentials are involved. |
| A0 policy constants | Import/constants tests; default-policy test proving behavior remains `last_attempt_only_v1` or current default. | No prompt behavior change. |
| A1 prompt core | Attempt evidence tests; anchor selector ranking/tie-break tests; golden prompt tests; prompt-injection guard tests; truncation/fail-closed tests; prompt-hash exactness tests. | No runner behavior change. |
| A2 C-loop integration | Cluster 2 repair-loop tests; F2-only boundary tests; policy flag parsing/default tests; prompt hash and anchor metadata tests; mixed-policy artifact rejection/quarantine tests where applicable. | Requires C-loop and likely Cluster 2 runner leases. |
| A3 P-loop integration | Cluster 3 P-loop tests; F1_COMPILE-only boundary tests; sanitizer leakage tests; policy flag parsing/default tests; prompt hash and anchor metadata tests. | Requires P-loop and likely Cluster 3 runner leases. |
| A4 P-to-C isolation | History isolation tests; no P compile logs in C prompt tests; C seed provenance tests; post-P F2 handoff tests. | C and P histories remain separate in v1. |
| A5 analyzer policy grouping | Analyzer tests for legacy/unknown/new policy grouping; mixed-policy quarantine tests; report metadata review. | Must land before agentic paid runs. |
| A6 A/B gates | Local fixture smoke commands; paired-seed matrix definition; failure movement table; prompt/cost summary; no private-eval leakage scan. | Modal requires run approval packet. |
| Future Cluster 3 run spec | Complete run approval packet; target output path nonexistence check; pre-spend command list; exact Modal command; stop conditions; post-run validation plan; claim boundaries; observability policy. | Spec only until user approves. |
| Any future run execution | Approved run packet; pre-spend tests; exact command transcript; row-count validation; schema validation; hash sidecar validation; P/C route invariants where applicable; private-eval scan; performance/profiler/timing/speedup scan; post-run registry/audit update. | One run scope per approval. |
| Any result schema change | Schema round-trip tests; old-row load tests; nullable/defaultable field tests; artifact compatibility note. | Requires result-schema lease. |
| Any runner flag change | CLI parse tests; default behavior tests; no-hidden-retry/no-hidden-Modal-change scan where relevant; output path safety tests. | Requires runner lease. |
| Any output mutation | Explicit approval packet; target path policy; hash validation; registry update. | Not allowed from planning context. |

### Standard Scan Commands

Use or adapt these scans when relevant, and record exact output in the handoff:

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|performance improvement|speedup|profiler result|timing result|full 2\\^3 complete|statistically significant" docs audits cluster3/README.md
```

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" outputs/cluster3/*.jsonl
```

```bash
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" outputs/cluster3/*.jsonl
```

For runner-touching packages that should not execute paid work, also record:

```bash
git status --short --branch
```

and a direct statement:

```text
Modal/output mutation performed: no
```

## Open Decisions Register

Use this register for choices that affect component implementation specs,
parallel branch safety, run eligibility, or report interpretation. A package may
begin only if its blocking decisions are resolved or the package explicitly
operates under the listed conservative default.

Decision states:

```text
open: unresolved and blocks at least one downstream package
resolved: decision made and source recorded
deferred: intentionally postponed; default behavior applies until reopened
```

| ID | Decision | Status | Blocks | Owner | Deadline / gate | Current default | Resolution | Source doc |
|---|---|---|---|---|---|---|---|---|
| D-OBS-01 | Should observability sidecars be required by default or opt-in during initial rollout? | resolved | O1 runner instrumentation; any run that wants observability evidence | Observability spec owner | Resolved by O-spec v0.2.0 | Existing and development runners default to opt-in/off; final-design or paper-scale runs should use `required` after O0/O1/O3/O4 acceptance. | Initial rollout uses explicit `off`, `best_effort`, or `required` modes; no implicit sidecar writes. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-02 | What is the canonical `experiment_id` / `run_id` format? | resolved | O0/O1 sidecar schema; run approval packets; analyzer joins | Observability spec owner | Resolved by O-spec v0.2.0 | Explicit human-readable `experiment_id` and `run_id`; output path remains a join key but is not the sole ID. | Both IDs are required whenever observability is enabled. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-03 | Should actual Modal cost attribution use app tags, isolated windows, or both? | resolved | O5 billing reconciliation; cost-per-success claims | Observability/billing owner | Resolved for O0-O5 planning | No actual-cost claim in O0-O4; O5 should prefer App tags plus non-overlapping time windows where possible. | Actual billing remains unavailable until a future approved O5 reconciliation. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-04 | Should Phase 14c wait for observability sidecars? | resolved | Future final-design or paper-scale run packets | Run spec owner plus user approval | Resolved after Phase 14e state reconciliation | Phase 14c already ran as diagnostic before sidecars; future final-design/paper runs should wait for O0/O1/O3/O4 or explicitly mark observability unavailable. | No retroactive sidecar is fabricated for Phase 14a-14e artifacts. | `docs/16_observability_sidecar_implementation_spec.md`; `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` |
| D-MET-01 | Should metric registry live only in analyzer metadata or also in a shared Python registry module? | resolved | S1 analyzer metadata; S2 report builder | Analyzer/report spec owner | Resolved by S-spec v0.1.2 | Analyzer metadata first; no shared module until justified | S1 implements analyzer-output metadata only; a shared Python registry module is deferred unless a later spec or launch packet justifies extraction. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-MET-02 | What exact formula defines `syntax_valid_rate` across mixed Cluster 1/2/3 schemas? | resolved | S1 metadata; S2 reports; paper-facing syntax claims | Analyzer/report spec owner | Resolved by S-spec v0.1.2 | Do not report mixed-cluster syntax rate; report cluster-local diagnostics only | `syntax_valid_rate` is unavailable for mixed current schemas unless every row has compatible explicit syntax evidence and the same `syntax_valid_definition_id`; S1 should emit availability metadata instead of a mixed aggregate. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-MET-03 | Should current report HTML refresh happen immediately or after analyzer metadata extension? | resolved | S2 report builder/dashboard | Report owner | Resolved by S-spec v0.1.2 | Wait for S1 unless docs-prose-only | S2 report HTML/data refresh waits for S1 metadata unless the change is docs-prose-only. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-AGENT-01 | What is the maximum rendered prompt length and truncation budget for `agentic_transcript_v1`? | open | A1 prompt renderer; A2/A3 loop integration | Agentic memory spec owner | Before A1 golden fixtures freeze | Fail closed if over budget; do not guess production budget in runner code | unresolved | `docs/13_agentic_repair_memory_strategy.md` |
| D-AGENT-02 | Should latest full source be included by default when it differs from best anchor? | open | A1 renderer; A2/A3 integration | Agentic memory spec owner | Before A1 golden fixtures freeze | Include only if explicitly enabled and within budget | unresolved | `docs/13_agentic_repair_memory_strategy.md` |
| D-AGENT-03 | Does `agentic_transcript_v1` remain opt-in through all development runs? | resolved | A2/A3 integration; A6 A/B gates; run specs | Orchestration contract owner | Resolved before implementation | Opt-in | `agentic_transcript_v1` remains opt-in until paired A/B review and explicit contract/spec update. | `docs/15_experiment_change_orchestration_contract.md` |
| D-AGENT-04 | Should P-to-C handoff include a one-line P provenance note in C history? | open | A4 P-to-C isolation | Agentic memory spec owner | Before A4 | No P compile logs in C prompts; no provenance note unless spec approves exact wording | unresolved | `docs/13_agentic_repair_memory_strategy.md` |
| D-RUN-01 | What exact threshold promotes n=5 diagnostics toward paper-scale readiness? | open | R5 paper-scale decision; any n=20 proposal | Orchestration owner plus user | Before Gate G8 | No promotion; n=5 diagnostics do not imply paper readiness | unresolved | `docs/15_experiment_change_orchestration_contract.md` |
| D-RUN-02 | Should Phase 14d reuse the existing Phase 12 `G+P` n=5 artifact or rerun fresh? | resolved | R4 G+P matrix completion | Run spec owner | Resolved by Phase 14d | Existing Phase 12 `G+P` n=5 artifact reused after validation. | Reuse approved and registered as the Phase 14 `G+P` matrix cell. | `audits/cluster3_phase14d_g_plus_p_reuse_vs_rerun_decision.md` |
| D-RUN-03 | Should future diagnostic runs continue after repeated all-F0 n=5 cells? | resolved | Future run specs and paper-scale readiness | Orchestration owner plus user | Resolved by Phase 14e freeze | Do not broaden from Phase 14e directly to paper-scale; require paper-scale readiness/go-no-go or sample-selection plan. | Phase 14e froze the development matrix as condition coverage only; broader runs need a fresh approval packet. | `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` |

### Decision Update Template

```text
decision id:
old status:
new status:
resolution:
source doc or audit:
affected packages:
state-file update required: yes
contract/spec update required: yes/no
```

## Serialized-Surface Lease Template

```text
surface:
owner branch:
owner worktree:
scope:
start commit:
expected files:
expected tests:
expires or review checkpoint:
status:
```

## Run Approval Packet Template

```text
run label:
branch/worktree:
baseline commit:
orchestration contract version:
state file version:
document registry version:
component spec versions:
artifact registry version or audit references:
exact command:
condition:
kernel_class:
dtype:
n:
scale_tier:
repair_history_policy:
observability policy:
target output path:
overwrite/archive policy:
estimated cost:
expected wall clock:
max rows:
max generation attempts:
max repair attempts per row:
max wall clock:
max estimated cost:
stop on first infrastructure/F3:
model id:
model revision:
tokenizer revision:
prompt/template version:
grammar policy:
grammar variant:
grammar hash:
Modal image id or unavailable reason:
pre-spend tests:
fixture-first proof:
independent review status:
network/API/dependency-download approval:
secrets/credentials handling:
negative tests:
stop conditions:
post-run validation:
claim boundaries:
approval status:
```

## Handoff Template

```text
branch:
launch packet id:
baseline commit:
stream/package:
requirements implemented:
requirements intentionally out of scope:
files owned:
files intentionally not touched:
gates satisfied:
tests run:
requirement-to-test map:
default-invariance proof:
fixture-first proof:
independent review:
negative tests:
secrets/credentials boundary:
network/API/dependency-download activity:
dependency/lockfile changes:
escalations:
post-merge verification required:
known caveats:
next blocked/unblocked packages:
state update owner:
Modal/output mutation performed: yes/no
artifact compatibility:
legacy behavior:
new metadata fields:
policy labels:
rollback path:
```
