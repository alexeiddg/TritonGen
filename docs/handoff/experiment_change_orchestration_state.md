# Experiment Change Orchestration State

- Version: 1.5.79
- Date: 2026-06-06
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
  mutation, profiler trace collection, timing execution, speedup computation,
  or benchmark execution unless a later signed run packet explicitly grants
  those permissions. The O6b smoke packet granted exactly one bounded Modal GPU
  performance smoke run and does not authorize broader benchmark matrices,
  profiler traces, output mutation, generation, or paper-scale claims.
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
| Git baseline commit | `426ede8 Enable signed L2 n20 runtime gate` plus promotion audit in progress |
| Git branch | `codex-track-handoff-context` |
| Git status at latest reconciliation | Final L2 n=20 authorization is promoted into `codex-track-handoff-context` at `bd84940` and promotion-audited at `2102259`. Runtime-gate commit `426ede8` is now fast-forwarded into `codex-track-handoff-context`; it enables only the exact signed L2 n=20 selector token/profile/path through local pre-launch validation while preserving fail-closed behavior for wrong tokens, L1a/L1b token reuse, wrong `n`, non-elementwise kernels, non-fp32 dtypes, MLflow-enabled runtime, non-agentic repair history, resume, target-path collisions, row/cell mismatch, namespace mismatch, L3, profiler, benchmark, speedup/performance paths, retry, and other variants. The promotion audit did not run L2, invoke Modal/GPU/generation, query billing, mutate outputs/artifacts/mlruns, refresh analyzer/report artifacts, change dependencies/lockfiles, or refresh preliminary reports. |
| Orchestration contract version | `docs/15_experiment_change_orchestration_contract.md` v1.0.13 |
| Registry version at state reconciliation | `docs/handoff/document_version_registry.md` v1.116.0 |
| Observability spec version | `docs/16_observability_sidecar_implementation_spec.md` v0.2.6 |
| Structural/task analyzer metadata spec version | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.4 |
| MLflow tracking policy version | `.contracts/research/mlflow_tracking_policy.md` v1.0.0 |
| Agentic transcript implementation spec version | `docs/18_agentic_transcript_v1_implementation_spec.md` v0.1.5 |
| Agentic transcript docs-only checkpoint | `audits/agentic_transcript_v1_spec_checkpoint_report.md` v1.0.0 |
| Agentic transcript A0 policy constants | commit `1e3f44468c5ae91e6467b42b7f93a068fa6acf5f` |
| Agentic transcript A0.5 preflight | `audits/agentic_transcript_v1_a0_5_preflight_report.md` v1.0.0 |
| Agentic transcript A1 prompt core | `audits/agentic_transcript_v1_a1_prompt_core_report.md` v1.0.0 |
| Agentic transcript A2 C-loop integration | promoted into A6 handoff trunk by commit `4a84600`; `audits/agentic_transcript_v1_a2_c_loop_integration_report.md` v1.0.0 remains the evidence snapshot |
| Agentic transcript A3 P-loop integration | promoted into A6 handoff trunk by commit `4a84600`; `audits/agentic_transcript_v1_a3_p_loop_integration_report.md` v1.0.0 remains the evidence snapshot; no Modal/output/generation work performed |
| Agentic transcript A4 P-to-C isolation proof | promoted into A6 handoff trunk by commit `4a84600`; `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md` v1.0.0 remains the evidence snapshot; no Modal/output/generation work performed |
| Agentic transcript A5 analyzer grouping/quarantine | promoted into A6 handoff trunk by commit `4a84600`; `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md` v1.0.0 remains the evidence snapshot; no Modal/output/generation work performed |
| Agentic transcript A6 run-packet gate planning | promoted into handoff trunk at commit `4a84600`; `audits/agentic_transcript_v1_a6_run_packet_gate_report.md` v1.0.0 remains the evidence snapshot; `docs/handoff/agentic_transcript_v1_next_run_packet.md` is `DRAFT_NOT_APPROVED` and authorizes no Modal/output/generation/n=5/n=20/paper-scale work |
| Observability O0-O6b package | O0-O4 promoted into handoff trunk at commit `309c451`; O5-Prep/O5a accepted locally through `c41a5bc`; O5b committed at `cf63de8`; O5c adapter-ready blocked state committed at `dc48782`; O6a Level-4 performance contract scaffolding committed at `d966ad0`; O6b smoke sidecar committed at `403cfea`; final O5b/O5c/O6a/O6b promotion audit passed with caveats |
| Structural/task reporting S0-S4 package | S0 terminology accepted at `d9bbdb2`; S1 analyzer metric registry metadata committed at `ff876d2`; S2 report metadata consumption committed at `a7b0cdb`; S3 report refresh docs-only record committed at `f1058eb`; S0-S3 promotion audit committed at `80086f9`; S4 future experiment metric-family guidance committed at `f73ecb9`, fast-forwarded into `codex-track-handoff-context`, and promotion-audited at `d015862`. Generated preliminary-report previews remain ignored local outputs unless a future explicit force-add publication decision is made. |
| Current Cluster 3 gate | L1b n=5 for the 12-cell `grammar_mode x C x P` design completed and was boundary-audited as `L1B_N5_AUDIT_PASS_L2_READY`. The L2 n=20 packet exists at `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md` with audits `audits/l2_n20_authorization_packet_draft_report.md`, `audits/l2_n20_selector_profile_support_report.md`, `audits/l2_n20_selector_profile_support_promotion_audit_report.md`, `audits/l2_n20_final_signature_readiness_report.md`, `audits/l2_n20_final_authorization_report.md`, `audits/l2_n20_final_authorization_promotion_audit_report.md`, `audits/l2_n20_runtime_gate_enable_report.md`, and `audits/l2_n20_runtime_gate_enable_promotion_audit_report.md`. The packet signs `L2_N20_FINAL_AUTHORIZATION_READY` and `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY` for the exact L2 n=20 command surface, 12 cells, 240 rows, stop/spend limits, L2 namespaces, post-run validation commands, and post-run billing reconciliation scope. Runtime-gate commit `426ede8` is promoted and lets only that signed L2 selector command pass local pre-launch validation. No L2 execution has occurred yet. |
| Paper-scale status | L2 n=20 execution authorization packet is signed but no Cluster 3 `n=20` output exists yet; graph/report/paper claims remain blocked until successful L2 execution, output validation, analyzer/report strictness audit, and billing reconciliation pass |

Important repository note: on the handoff trunk, `docs/`, `audits/`, and
`.contracts/agentic/**` are intentionally trackable. Raw outputs and MLflow
runtime state remain ignored. A clean `git status` still does not prove raw
output artifacts are unchanged; inspect `outputs/` directly when relevant.

## Active Worktrees

| Worktree | Branch | Commit | State ownership |
|---|---|---|---|
| `/Users/alexeidelgado/Desktop/TritonGen` | `codex-track-handoff-context` | `426ede8 Enable signed L2 n20 runtime gate` plus promotion audit in progress | Runtime-gate commit is fast-forwarded into the handoff trunk and enables only the exact signed L2 n=20 selector token/profile/path through local pre-launch validation. No L2 execution, Modal/GPU/generation, billing query, protected output/artifact/mlruns mutation, analyzer/report refresh, dependency/lockfile, preliminary-report refresh, profiler, benchmark, speedup, cost-per-success, paper conclusion, or MLflow runtime work occurred during promotion. |
| `/private/tmp/tritongen-llm-repair-memory` | `codex/llm-repair-memory-agentic-transcript-v1` | `4a84600` | reference/history worktree only; same A6 commit as the promoted handoff trunk and not the place for observability work |
| `/Users/alexeidelgado/Desktop/TritonGen/.claude/worktrees/intelligent-pasteur-72d92f` | `claude/intelligent-pasteur-72d92f` | `b0085c1` | external/unknown to this orchestration state; reconcile before relying on it |

## Active Branches

| Branch | Stream/package | Worktree | Status | Notes |
|---|---|---|---|---|
| `codex/l2-n20-runtime-gate-enable` | L2 n=20 runtime-gate enablement | none after promotion | promoted/audit closeout | Created from pushed `codex-track-handoff-context` baseline `2102259`, committed as `426ede8`, and fast-forwarded into `codex-track-handoff-context`. Scope is narrow runtime pre-launch authorization only: allow exactly the signed L2 n=20 token/profile/path to pass and keep all other variants fail-closed. Adds `audits/l2_n20_runtime_gate_enable_report.md`; promotion audit is `audits/l2_n20_runtime_gate_enable_promotion_audit_report.md`. No L2 execution, Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, dependency/lockfile, profiler, benchmark, speedup, cost-per-success, paper conclusion, or MLflow runtime work occurred during the promotion. |
| `codex/l2-n20-final-authorization` | L2 n=20 final authorization packet | none after promotion | promoted/audit closeout | Created from `codex-track-handoff-context` at `182db35`, committed as `bd84940`, and fast-forwarded into `codex-track-handoff-context`. Updates the L2 packet to `SIGNED_FOR_L2_N20_ONLY`, signs `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`, records the exact L2 command bundle, 12-cell and 240-row expectation, signed stop/spend limits, L2 namespaces, post-run validation authorization, post-run billing reconciliation authorization, and adds `audits/l2_n20_final_authorization_report.md`. Promotion audit is `audits/l2_n20_final_authorization_promotion_audit_report.md`. No L2 execution, Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, runtime code change, dependency/lockfile, preliminary-report refresh, profiler, benchmark, speedup, cost-per-success, paper conclusion, or MLflow runtime work occurred in this branch. |
| `codex/l2-n20-selector-profile-support` | L2 n=20 selector/profile support | none after promotion | promoted/audit closeout | Created from pushed handoff baseline `3a21002` and fast-forwarded into `codex-track-handoff-context` at `27493c0`. Adds L2 `paper/n=20` profile support for the 12-cell `grammar_mode x C x P` selector, 240 planned rows, signed-L2 command surfaces, L2 namespaces, fail-closed runtime profile behavior, focused local tests, packet update, and `audits/l2_n20_selector_profile_support_report.md`. Promotion audit is `audits/l2_n20_selector_profile_support_promotion_audit_report.md`. `AUTHORIZES_EXECUTION: NO`; no L2/n20 execution, Modal/GPU/generation, output/artifact/mlruns mutation, billing query, analyzer/report refresh, dependency, lockfile, benchmark, profiler, speedup, cost-per-success, or paper-scale claim is authorized. |
| `codex/l2-n20-authorization-packet` | L2 n=20 authorization packet draft | none after promotion | promoted/reference | Created from `codex-track-handoff-context` at `134bcf9`, then fast-forward promoted into `codex-track-handoff-context` at `4ae7081` and promotion-audited at `3a21002`. Adds the unsigned L2 n=20 packet and packet-draft audit for the 12-cell `grammar_mode x C x P` matrix. The original packet recorded the command-surface blocker that is now addressed locally on `codex/l2-n20-selector-profile-support`. `AUTHORIZES_EXECUTION: NO`; no execution, output/artifact/mlruns mutation, Modal/GPU/generation, billing query, dependency, lockfile, analyzer/report refresh, benchmark, profiler, speedup, cost-per-success, or paper-scale claim is authorized. |
| `codex-track-handoff-context` | L1b n=5 12-cell completion | `/Users/alexeidelgado/Desktop/TritonGen` | completed/local evidence preservation | Runs exactly the authorized L1b n=5 12-cell selector command from support commit `a52d64a`, validates 60 rows and all sidecars, records development-scale analyzer/report output, records UTC-window-only billing with empty Modal tags, and adds `audits/l1b_n5_execution_completion_report.md` plus `audits/l1b_n5_analyzer_dev_scope_patch_report.md`. No L2/n20/paper-scale/profiler/benchmark/speedup/economic-claim or MLflow runtime work is authorized. |
| `codex/l1a-final-signature-packet` | L1a final signature packet preparation | `/Users/alexeidelgado/Desktop/TritonGen` | active/docs-only | Created from promoted handoff baseline `c05e111`. Updates the unsigned L1a packet target to `codex-track-handoff-context` at `c05e111`, records exact promoted selector commit `e9f180a` and promotion audit commit `c05e111`, adds `audits/l1a_final_signature_packet_report.md`, and updates handoff routing. It keeps `AUTHORIZES_EXECUTION: NO`; signature status remains `UNSIGNED`; numeric stop/spend limits remain `PROPOSED_NOT_SIGNED`; advisory estimate remains `NOT_SIGNABLE`; remote image digest, billing authorization, post-run validation authorization, and separate execution approval remain required. |
| `codex/l1a-executable-12cell-selector-support` | L1a executable 12-cell selector support | none after promotion | promoted/audit closeout | Created from pushed handoff baseline `e96f70a` and fast-forwarded into `codex-track-handoff-context` at `e9f180a`. Adds source-backed `--execution-plan` command construction for all 12 `grammar_mode x C x P` cells, including six no-P controls, while preserving dry-plan support and refusing actual runtime selector execution before tracking, generation, Modal, result writers, observability writers, or MLflow runtime setup. Updates the unsigned L1a packet, adds `audits/l1a_executable_12cell_selector_support_report.md`, and is promotion-audited in `audits/l1a_executable_12cell_selector_support_promotion_audit_report.md`. It remains `AUTHORIZES_EXECUTION: NO`; no execution, output/artifact/mlruns mutation, Modal/GPU/generation, dependency, lockfile, benchmark, billing query, profiler, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| `codex/l1a-signature-readiness-gap-closure` | L1a signature-readiness gap closure | none after promotion | promoted/reference | Created from promoted handoff baseline `59fa0d6` and fast-forwarded into `codex-track-handoff-context` at `616ae01`. Patches the unsigned L1a packet to close source-backed signature-readiness gaps without execution: target commit freshness, deterministic observability run-id convention, repo-local Modal app identity, synthetic `NOT_SIGNABLE` preflight placeholder, unsigned proposed stop/spend limits, plan-only billing reconciliation, exact local post-run validation command surfaces, and explicit signature fields. Its executable-command blocker is superseded by promoted executable selector support at `e9f180a`; `AUTHORIZES_EXECUTION: NO` remains. |
| `codex/l1a-final-approval-packet` | L1a final approval packet completion | none after promotion | promoted/reference | Created from promoted handoff baseline `c256af5`. Completed the unsigned signable L1a n=1 packet surface for the 12-cell `grammar_mode x C x P` design, including target commit, exact dry-plan command, path templates, grammar hashes, model/seed policy, advisory preflight requirement, stop/spend placeholders, validation placeholders, and signature block. Promoted packet commit is `e348c2c`; promotion audit is `audits/l1a_final_approval_packet_promotion_audit_report.md`. It remains `AUTHORIZES_EXECUTION: NO`; no execution, output/artifact/mlruns mutation, Modal/GPU/generation, dependency, lockfile, benchmark, billing query, profiler, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| `codex/modal-preflight-cost-time-estimator` | Modal preflight cost/time estimator | none after promotion | promoted/reference | Created from promoted handoff baseline `76310b5`. Adds a pure local estimator for row-count, execution-shape, cost/time, warning, and larger-GPU breakeven planning before any L1a/L1b/L2 execution packet. Promoted estimator commit is `bd89e67`; promotion audit is `c256af5`. It is advisory only and uses explicit local inputs. No execution, output/artifact/mlruns mutation, Modal/GPU/generation, dependency, lockfile, benchmark, billing query, profiler, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| `codex/modal-optimization-intake-review` | Modal optimization intake review | none after promotion | committed/promoted reference | Created from promoted handoff baseline `76ede6a`. Reviews parked `docs/19_modal_full_factorial_optimization_plan.md`, confirms no tracked dirty sidecar timing patch is present, adds `audits/modal_optimization_intake_review_report.md`, and updates routing. Local promoted commit is `6160c88`; no execution or protected mutation was authorized. |
| `codex/grammar-mode-12cell-launcher-support` | Grammar-mode 12-cell launcher/no-P selector support | none after promotion | promoted/reference | Created from `0d1e8e3`. Adds dry-plan-only selector `grammar_mode_cp_12cell`, all 12 L1a cells including six no-P controls, deterministic output/content-hash/observability path planning, grammar hash locks, no-overwrite policy metadata, fail-closed execution validation, L1a packet wording updates, and `audits/grammar_mode_12cell_launcher_support_report.md`; promoted support commit is `e914557` and promotion audit is `76ede6a`. No execution, output/artifact/mlruns mutation, Modal/GPU/generation, dependency, lockfile, benchmark, billing query, profiler, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| `codex/l1a-authorization-packet-completion` | L1a n=1 authorization packet completion for review/signature | none after promotion | promoted/reference | Created after fast-forward promoting `codex/l1a-packet-baseline-pin` into `codex-track-handoff-context` at `d172e02`. Commit `3771b73` completes `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md` for review/user signature only, adds `audits/l1a_authorization_packet_completion_report.md`, records grammar hash locks and a review-only command manifest, and previously blocked execution pending full 12-cell launcher support for no-P cells plus explicit signed approval. Fast-forward promoted into `codex-track-handoff-context`; promotion audit is `audits/l1a_authorization_packet_completion_promotion_audit_report.md`. The no-P launcher-support blocker is now addressed locally on `codex/grammar-mode-12cell-launcher-support` pending promotion; execution remains unauthorized. |
| `codex/l1a-packet-baseline-pin` | L1a n=1 packet baseline pin for promoted grammar-mode support | none after local promotion | promoted/reference | Created from promoted handoff/audit commit `9aeb3c1` and fast-forwarded into `codex-track-handoff-context` at `d172e02`. Patches `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md` so the packet records `code_support_commit: c24fbaa`, `planning_baseline_commit: 9aeb3c1`, and historical `superseded_baseline_commit: 0cc43c1`; adds `audits/l1a_packet_baseline_pin_report.md`; updates handoff routing. L1a remains unsigned and non-executing. |
| `codex/grammar-mode-support-implementation` | Grammar-mode local representability implementation for 12-cell L1a | none after promotion | promoted/reference | Created from `4b0e6da`, implemented local support for `grammar_mode` values `grammar_off`, `template_upper_bound`, and `task_agnostic`, a 12-cell planner, Cluster 3 row/schema labeling, shared eval row support, analyzer grouping for explicit `grammar_mode`, focused tests, L1a draft packet wording update, and implementation audit/handoff records. Promoted support commit is `c24fbaa`; promotion audit is `9aeb3c1`. Execution remains unauthorized and MLflow grammar-mode indexing is deferred. |
| `codex/full-pipeline-l1-smoke-dev-approval-packet` | Full Pipeline Launch Packet v1 12-cell patch, L1a n=1 authorization draft, and grammar-mode code-support audit | none after implementation branch creation | committed/reference for implementation baseline | Created from pushed `codex-track-handoff-context` tip `0cc43c1` and committed through `4b0e6da`. Scope was patching the active launch packet from the superseded 8-cell plan to the selected 12-cell `grammar_mode x C x P` design, adding an unsigned/non-authorizing L1a n=1 draft authorization packet, adding the 12-cell patch audit, adding `audits/grammar_mode_code_support_audit_report.md`, and updating handoff routing. It is now the baseline for `codex/grammar-mode-support-implementation`. No execution authorization was granted. |
| `codex/full-pipeline-launch-packet-v1` | Full Pipeline Launch Packet v1 / superseded 8-cell planning source | none after promotion | promoted/reference; superseded for future execution by 12-cell patch | Created from `7d9ac22 Add C3 n20 metric family packet`, reviewed at `5cc6326`, and fast-forward promoted into `codex-track-handoff-context`. The original selected 8-cell plan is historical context only after the 12-cell patch. No analyzer/report code, report output refresh, raw JSONL rewrite, output/artifact/mlruns mutation, result schema, dependency, lockfile, Modal/GPU/generation, n=5, n=20, paper-scale, profiler, timing, speedup, benchmark, billing query, MLflow runtime write, or execution authorization is in scope. |
| `codex/c3-n20-metric-family-gated-packet` | C3 packet / metric-family-gated future experiment planning | none after handoff-trunk baseline `7d9ac22` | committed/reference | Created the non-authorizing Cluster 3 n20 experiment packet plus handoff registry/audit routing. No analyzer/report code, report output refresh, raw JSONL rewrite, output/artifact mutation, result schema, dependency, lockfile, Modal/GPU/generation, n=5, n=20, paper-scale, profiler, timing, speedup, benchmark, or execution authorization is in scope. |
| `codex-track-handoff-context` | promoted handoff trunk | `/Users/alexeidelgado/Desktop/TritonGen` | promoted/reference | Handoff trunk includes MLflow integration ancestry, A2-A6 repair-memory ancestry, O0-O6b observability metadata features, the final O5c operational billing caveat, structural/task S0-S4, C3 n20 metric-family packet commit `7d9ac22`, Full Pipeline Launch Packet v1, grammar-mode support through `c24fbaa`/`9aeb3c1`, L1a packet baseline/completion through `d172e02`/`3771b73`/`0d1e8e3`, 12-cell launcher support through `e914557`/`76ede6a`, Modal optimization intake at `6160c88`, sidecar stage timing promotion at `ef41890`/`76310b5`, Modal preflight estimator promotion through `bd89e67`/`c256af5`, L1a final approval packet promotion at `e348c2c` plus promotion audit `59fa0d6`, L1a signature-readiness gap closure at `616ae01` plus promotion audit `audits/l1a_signature_readiness_gap_closure_promotion_audit_report.md`, executable selector support at `e9f180a` plus promotion audit `audits/l1a_executable_12cell_selector_support_promotion_audit_report.md`, L2 packet draft promotion through `4ae7081`/`3a21002`, and L2 selector/profile support at `27493c0` plus promotion audit `audits/l2_n20_selector_profile_support_promotion_audit_report.md`. Do not use `main`, `ml_migration`, or stale worktrees for structural/task, observability, C3 packet, full-pipeline packet, L1 planning, or L2 signature-readiness work. |
| `codex/structural-task-s4-experiment-integration` | S4 future experiment metric-family integration | none after promotion | promoted/reference | Started from pushed `codex-track-handoff-context` tip `80086f9`, completed S4 docs/planning guidance, and fast-forwarded into `codex-track-handoff-context` at `f73ecb9`. No analyzer code, report builder, report output refresh, raw JSONL rewrite, output/artifact mutation, result schema, dependency, lockfile, Modal/GPU/generation, n=5, n=20, paper-scale, profiler, timing, speedup, benchmark, or execution authorization is in scope. |
| `codex/structural-task-s0-terminology` | S0 docs terminology acceptance | none after S1 branch creation | accepted/reference | Records G2/S0 terminology acceptance, docs/17 as executable S1 contract, S1 analyzer-metadata-only unblock scope, S2/S3 blocked state, and `audits/structural_task_s0_terminology_acceptance_report.md`. No analyzer code, tests, report builder, outputs, artifacts, dependencies, runtime, Modal, GPU, generation, n=5, n=20, paper-scale, performance, timing, profiler, or speedup work is authorized on this completed branch. |
| `codex/analyzer-metric-registry` | S1 analyzer metric registry metadata | none after S2 branch creation | review passed / commit closeout | S1 analyzer-metadata review passed. Scope was additive analyzer metadata and focused analyzer tests only, plus minimal state/registry/audit records. No report builder, `outputs/`, `artifacts/`, result schemas, dependencies, lockfiles, Modal, GPU, generation, experiment runs, paper-scale work, profiler, timing, speedup, or benchmark work is authorized. |
| `codex/structural-task-s2-report-consumption` | S2 report builder/dashboard consumption | none after S3 branch creation | committed/reference | S2 adds report-data-builder consumption of accepted S1 metadata when present, conservative `legacy_metadata_unavailable` fallback when current embedded/production analyzer data lacks S1 metadata, focused temp-fixture tests, and S2 audit/state/registry records. Ignored dashboard preview files were reviewed for localization parity but are intentionally excluded from the code/docs-only commit unless force-add is separately approved. S2 does not refresh analyzer output, rewrite raw JSONL, run experiments, mutate outputs/artifacts, alter analyzer semantics, or change result schemas/dependencies/lockfiles. |
| `codex/structural-task-s3-report-refresh` | S3 structural/task report output refresh | none after promotion | promoted/reference | S3 committed as `f1058eb` after review passed for docs-only commit, then fast-forwarded into `codex-track-handoff-context`. It ran the existing local preliminary report builder and inlined refreshed report data into ignored English/Spanish HTML previews. Current analyzer data still lacks S1 metadata, so the refreshed payload shows `legacy_metadata_unavailable` fallback plus structural/code-surface, task/functional, mixed diagnostic, and future benchmarkable/performance groups. Generated HTML/data remain ignored local preview outputs unless a future review explicitly approves force-add. |
| `codex/observability-sidecar-core` | O0-O4 observability package | none after promotion | promoted/reference | Created from `codex-track-handoff-context` at `4a84600`; O0 committed as `bcdaede`; O1 target state committed as `f088c10`; O1 committed as `8eaef2e`; O2-Prep committed as `74b3acd`; O2 committed as `6f3001e`; O3-Prep committed as `c93bdc0`; O3 committed as `4ddc767`; O4-Prep committed as `d30aa50`; O4 committed as `d4244af`; final acceptance committed as `309c451`. Treat as complete/reference, not the place for O5. |
| `codex/observability-o5-prep` | O5-Prep and O5a actual billing reconciliation scaffolding | none after O5b branch creation | accepted/reference | Created from promoted `codex-track-handoff-context` at `309c451`; O5-Prep committed as `effd644`, O5a scaffolding committed as `263d317`, and O5a final acceptance committed as `c41a5bc`. Treat as reference/history, not the place for O5b edits. |
| `codex/observability-o5b-reconciliation` | O5b static ingestion plus O5c Modal billing collection adapter | none after O6 branch creation | committed/reference | O5b is committed at `cf63de8`; O5c adapter-ready blocked state is committed at `dc48782`. No nonempty raw/redacted artifact is retained and no output/result-row/analyzer/dependency/generation/GPU/Modal compute/MLflow runtime mutation is authorized. |
| `codex/observability-o6-performance-contract` | O6a contract plus O6b performance smoke | none while `codex/structural-task-s0-terminology` is checked out in `/Users/alexeidelgado/Desktop/TritonGen` | promotion-ready/reference | Created from O5c baseline `dc48782`; O6a committed at `d966ad0`; O6b committed at `403cfea`; final O5b/O5c/O6a/O6b promotion audit passed with caveats. No generation, output mutation, result-row schema mutation, analyzer/economic metric, profiler/Nsight/NCU, dependency/lockfile, historical sidecar/output mutation, or MLflow runtime work is authorized. |
| `codex/integrate-mlflow-into-handoff` | MLflow tracking harness integration | none after promotion | promoted/reference | Merged `origin/ml_migration`, preserved handoff doc/audit tracking policy, validated optional/no-op tracking tests, and was absorbed into the promoted handoff trunk before A6. |
| `codex/llm-repair-memory-agentic-transcript-v1` | A-stream / agentic transcript implementation | `/private/tmp/tritongen-llm-repair-memory` | promoted/reference | Same commit as the promoted handoff trunk at `4a84600`; keep as reference/history, not as an active implementation branch for observability. |

## Active Serialized-Surface Leases

| Surface | Owner branch | Owner worktree | Scope | Start commit | Expected files | Expected tests | Review checkpoint | Status |
|---|---|---|---|---|---|---|---|---|
| analyzer_metric_registry | `codex/analyzer-metric-registry` | `/Users/alexeidelgado/Desktop/TritonGen` | S1 additive analyzer metadata only: outcome-family metadata, metric registry, registry provenance, level-reach diagnostics, feedback-activation diagnostics, metric-availability diagnostics, optional row annotations, JSON-safe deterministic output, and focused compatibility/negative tests | `d9bbdb2 Accept S0 structural task terminology gate` | `shared/analysis/factorial.py`; `shared/tests/test_factorial_analysis.py`; `docs/handoff/experiment_change_orchestration_state.md`; `docs/handoff/document_version_registry.md`; `audits/structural_task_s1_analyzer_metric_registry_report.md` | `.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q`; `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py -q`; `git diff --check`; forbidden-scope diff; output-mutation scan; gated-metric-language scan | S1 review passed locally; metadata may be consumed only under the S1/S2 handoff rule after commit | complete / lease closed |
| report_data_builder | `codex/structural-task-s2-report-consumption` | none after S3 branch creation | S2 report builder/dashboard consumption only: consume S1 metadata when available, emit conservative legacy fallback when unavailable, keep structural/code-surface and task/functional groups separate, and mark deferred/future/diagnostic metrics without promoting them to current headline claims | `ff876d2 Add S1 analyzer metric registry metadata` | `docs/preliminary_report/_build_data.py`; `docs/preliminary_report/tests/test_build_data.py`; `docs/handoff/experiment_change_orchestration_state.md`; `docs/handoff/document_version_registry.md`; `audits/structural_task_s2_report_consumption_report.md`; ignored preview files `docs/preliminary_report/index.html` and `docs/preliminary_report/index.es.html` reviewed but excluded unless force-add is separately approved | `.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py -q`; `.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q`; report-builder smoke via temp fixtures; `git diff --check`; forbidden-scope diff; analyzer-mutation scan; output/artifact scan; report-facing terminology scan; ignored HTML status check | S2 review passed and committed as `a7b0cdb`; S3 consumed the builder without code changes | complete / lease closed |
| report_output_refresh | `codex/structural-task-s3-report-refresh` | none after promotion | S3 derived report refresh only: run the existing local preliminary report builder, inline refreshed JSON into ignored English/Spanish HTML previews, verify structural/task separation, and record generated-file policy without analyzer or raw-output mutation | `a7b0cdb Add S2 report metadata consumption` | ignored local previews `docs/preliminary_report/_report_data.json`, `docs/preliminary_report/index.html`, `docs/preliminary_report/index.es.html`; `docs/handoff/experiment_change_orchestration_state.md`; `docs/handoff/document_version_registry.md`; `audits/structural_task_s3_report_refresh_report.md`; `audits/structural_task_s0_s3_promotion_audit_report.md` | `.venv/bin/python docs/preliminary_report/_build_data.py`; `.venv/bin/python -m pytest docs/preliminary_report/tests/test_build_data.py shared/tests/test_reporting_tables.py -q`; `.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q`; `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py -q`; post-promotion smoke tests; `git diff --check`; protected-scope scan; raw-output scan; Modal/GPU/execution scan; report-facing terminology scan; ignored HTML status check | S3 review passed as docs-only, S3 committed at `f1058eb`, and S0-S3 fast-forwarded into `codex-track-handoff-context`; generated HTML/data remain ignored unless a future review approves force-add | complete / lease closed / promoted |
| O6b Modal GPU performance smoke | `codex/observability-o6-performance-contract` | `/Users/alexeidelgado/Desktop/TritonGen` | Dedicated performance sidecar schema/writer/helper tests plus opt-in Modal smoke entrypoint and one signed smoke sidecar artifact | `d966ad0 Add O6a performance contract scaffolding` | `shared/observability/performance_sidecar.py`; `shared/observability/performance_harness.py`; `shared/observability/performance_modal_smoke.py`; `shared/observability/__init__.py`; `shared/tests/test_observability_performance_sidecar.py`; `shared/tests/test_observability_performance_harness.py`; `shared/tests/test_observability_imports.py`; `docs/handoff/experiment_change_orchestration_state.md`; `docs/handoff/document_version_registry.md`; `audits/observability_sidecar_o6b_performance_smoke_report.md`; `audits/observability_sidecar_o5b_o6b_final_promotion_report.md`; `artifacts/observability_performance/o6b_smoke_relu_performance.jsonl` | focused O5b/O5c/O6a/O6b tests; `git diff --check`; protected-scope diff; profiler/Nsight/NCU scan; claim-boundary scan | Final promotion audit passed; fast-forward into `codex-track-handoff-context` | promotion-ready |

## Gate Status

| Gate | Status | Evidence / note |
|---|---|---|
| G0 baseline freeze | satisfied with caveat | Git status is clean, but ignored docs/audits/outputs must be checked directly when relevant. |
| G1 orchestration contract accepted | satisfied | Contract exists and is routed through project map, hub, and registry. |
| G2 reporting terminology stable | satisfied | S0 terminology acceptance recorded on `codex/structural-task-s0-terminology` with `audits/structural_task_s0_terminology_acceptance_report.md`. Accepted vocabulary is structural/code-surface quality vs task/functional quality; `compile_success` remains structural/secondary or diagnostic; `functional_success` remains task/functional primary; Cluster 1 Level 2 status remains false/unproven rather than measured failure; C activation remains F2-eligible only. |
| G3 observability sidecar contract stable | O0-O6b promotion-ready | `docs/16_observability_sidecar_implementation_spec.md` v0.2.6 defines O0-O6a boundaries, O5c operational billing caveats, and O6b packet requirements. O6a is committed at `d966ad0`; O6b is committed at `403cfea`; final O5b/O5c/O6a/O6b promotion audit passed with caveats. No output mutation, generation, tokenizer/model execution, pricing fetch, analyzer/economic metric, dependency/lockfile change, cost-per-success, pass@k cost, ROI, economic-lift, profiler trace, Nsight, NCU, benchmark matrix, additional Modal/GPU run, or paper-scale performance claim is authorized. |
| G4 analyzer/report metadata compatibility stable | S0-S4 promoted/closed | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.4 records S0-S4. S1 implemented additive analyzer metadata and focused tests; S2 consumed S1 metadata when present and recorded a legacy fallback path when current analyzer JSON lacks S1 metadata. S3 refreshed derived preliminary-report data/ignored HTML previews from existing local inputs and verified that the current payload shows `legacy_metadata_unavailable` plus separated structural/code-surface, task/functional, mixed diagnostic, and future benchmarkable/performance groups. S4 adds future packet metric-family guidance only and was fast-forwarded into `codex-track-handoff-context` at `f73ecb9`; generated HTML/data remain ignored unless a future review approves force-add. |
| G5 agentic prompt core stable | satisfied with baseline-venv caveat | `audits/agentic_transcript_v1_a1_prompt_core_report.md` v1.0.0 records pure prompt-core implementation, typed local errors, policy config validation, public evidence/source models, deterministic anchor ranking, canonical renderer, prompt/history hashes, budget behavior, fixture manifest, prompt-injection fixture, legacy C/P byte-invariance snapshots, import isolation, focused tests, and no forbidden-surface changes. |
| G6 agentic integration stable | promoted to handoff trunk with run gate caveat | A2 C-loop integration, A3 P-loop integration, A4 P-to-C isolation proof, A5 analyzer grouping/quarantine, and A6 run-packet gate planning are present in promoted A6 commit `4a84600`; future agentic execution remains blocked pending signed run approval and required pre-run checks. |
| G7 development run readiness | L2 final authorization packet signed; exact runtime gate promoted | Phase 14e matrix is frozen; the C3 n20 metric-family-gated packet review passed as draft/non-authorizing planning only and defines prerequisites for a future launch. Full Pipeline Launch Packet v1 selects the 12-cell `grammar_mode x C x P` design with L1a n=1 before L1b n=5 and L2 n20. L1a n=1 and L1b n=5 are completed/audited. The L2 n=20 packet now targets `182db35`, signs `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`, records exact commands, signed stop/spend limits, output/artifact namespaces, billing caveat, post-run validation, no retry/no resume, and adds `audits/l2_n20_final_authorization_report.md`. Runtime-gate commit `426ede8` is promoted and enables only the exact signed L2 n=20 selector token/profile/path through local pre-launch validation while keeping L1a/L1b token reuse, wrong variants, path collisions, row/cell mismatch, L3, profiler, benchmark, speedup/performance, retry, and resume fail-closed. No L2 execution occurred. Any broader development-scale, all-condition, diagnostic, L3, profiler, benchmark, speedup, cost-per-success, or paper-claim work needs a separate signed packet. |
| G8 paper-scale readiness | blocked pending successful L2 output and analyzer audit | The L2 n=20 authorization packet is signed and the exact runtime gate is promoted, but no new `n=20` output exists yet. Paper-scale graph/report claims remain blocked until exact signed execution completes, 240 rows and 12 cells validate, analyzer/report strictness passes, and billing reconciliation is audited. |

## Approved Run Packets

One L2 n=20 authorization packet is signed by this state record. Runtime-gate
commit `426ede8` is promoted and enables only the exact signed L2 selector
command through local pre-launch validation. It did not execute during the
runtime-gate promotion.

Current packet records:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
- Status: `DRAFT_NOT_APPROVED`
- `AUTHORIZES_EXECUTION: NO`
- Selects future fresh 12-cell `grammar_mode x C x P` design with L1a n=1
  before L1b n=5 and L2 n20.
- Does not authorize Modal execution, GPU work, generation, experiments,
  output mutation, MLflow runtime writes, billing queries, n=1 execution, n=5, n=20,
  paper-scale work, benchmark, profiler, timing, speedup, or dependency changes.

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- Status: `DRAFT_READY_FOR_USER_SIGNATURE`
- `AUTHORIZES_EXECUTION: NO`
- Unsigned L1a n=1 authorization review draft for the 12-cell design.
- Promoted local representability support, 12-cell dry-plan launcher support, and local
  advisory preflight estimator support are present. The packet now records
  target commit `c256af5`, grammar hashes, path templates, model/revision,
  seed/decoding policy, dry-plan verification command, required exact execution
  command placeholder, numeric stop/spend placeholders, validation placeholders,
  and unsigned signature block. Execution remains blocked pending exact
  executable commands, numeric stop/spend limits, advisory preflight estimate,
  billing reconciliation plan, post-run validation bundle, and a separate
  signed approval.
- Does not authorize Modal execution, GPU work, generation, experiments,
  output mutation, MLflow runtime writes, billing queries, n=1 execution, n=5,
  n=20, paper-scale work, benchmark, profiler, timing, speedup, or dependency
  changes.

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md`
- Status: `SIGNED_FOR_L2_N20_ONLY`
- `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`
- Signed L2 n=20 packet for the 12-cell design at target baseline `182db35`.
  It records the exact 240-row matrix, dry-plan, execution-plan, future
  execution command, analyzer/report command, post-run billing template,
  signed stop/spend limits, future L2 namespaces, billing caveat carry-forward,
  post-run validation plan, no retry/no resume, forbidden scope, and signature
  fields.
- Execution did not occur in this branch. The runtime-gate branch now enables
  only this signed L2 profile to pass pre-launch validation and is promoted on
  `codex-track-handoff-context`; target paths, `TRITONGEN_MLFLOW=0`, no retry,
  and no resume still require immediate pre-launch verification before any
  launch.
- Does not authorize L3, additional kernels, extra dtypes, runtime MLflow
  writes, paper conclusions before post-run audit, benchmark, profiler, timing,
  speedup, cost-per-success, preliminary-report refresh, dependency changes,
  lockfile changes, or output/artifact mutation outside the signed L2 n=20
  namespaces.

- `docs/handoff/agentic_transcript_v1_next_run_packet.md`
- Status: `DRAFT_NOT_APPROVED`
- `AUTHORIZES_EXECUTION: NO`
- `MODAL_AUTHORIZED: NO`
- `GENERATION_AUTHORIZED: NO`
- `OUTPUT_MUTATION_AUTHORIZED: NO`
- `N5_AUTHORIZED: NO`
- `N20_AUTHORIZED: NO`
- `PAPER_SCALE_AUTHORIZED: NO`

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
| observability sidecar implementation spec | complete / tightened | `docs/16_observability_sidecar_implementation_spec.md` v0.2.6 created, routed, clarified for O0, narrowed for O3 token telemetry as counts/status only, tightened for O4 estimated/unavailable cost metadata only, extended with O5 actual-billing reconciliation boundaries, O5c operational collection caveats, and O6a Level-4 performance contract scaffolding plus O6b packet requirements; O0-O4 are promoted at `309c451`, O5-Prep/O5a are accepted locally through `c41a5bc`, O5b is committed at `cf63de8`, O5c adapter-ready blocked state is committed at `dc48782`, O6a is committed at `d966ad0`, O6b is committed at `403cfea`, and final O5b/O5c/O6a/O6b promotion audit passed with caveats. |
| O1 Cluster 3 local runner instrumentation | committed | Commit `8eaef2e` adds opt-in Cluster 3 runner observability sidecars with default-off behavior, required explicit IDs when enabled, tmp_path-only tests, no result-row schema mutation, and no Modal/output/generation authorization. |
| O2 Modal runtime context implementation | committed | Commit `6f3001e` adds optional safe Modal runtime context sidecar support for Cluster 3 only with local fake-context tests, no `.remote()` to `.spawn()` switch, no new Modal invocation, no outputs/result-row mutation, no billing/cost/performance telemetry, and no execution authorization. |
| O3 token telemetry implementation | committed | Commit `4ddc767` adds count/status-only token telemetry, fail-closed token/raw/private payload rejection, event-derived token summary validation, and Cluster 3 injected/unavailable token sidecars with no tokenizer/model/generation/output/result-row/billing/performance changes. |
| O4 estimated cost telemetry implementation | committed | Commit `d4244af` adds supplied estimated or unavailable cost sidecar metadata and validation with no actual billing, invoice, external pricing fetch, output/result-row/analyzer/economic metric, dependency, or performance changes. |
| O0-O4 observability final acceptance | committed | Commit `309c451` records `O0_O4_FINAL_ACCEPTANCE_PASS_WITH_CAVEATS` and promotes the complete O0-O4 observability package into the handoff trunk. O5 was not started in that package. |
| O5-Prep actual billing reconciliation launch reconciliation | committed | Commit `effd644` names future O5 target surfaces, allowed sidecar-only actual-billing reconciliation fields, forbidden billing/private/economic payloads, approval-packet requirements, tests, and stop conditions. |
| O5a actual billing reconciliation scaffolding | accepted with caveats | Commit `263d317` adds shared observability schema/redaction/logger scaffolding for mocked/static actual-billing reconciliation metadata only, and commit `c41a5bc` records final acceptance. No live billing query, credential use, Modal billing CLI/API invocation, output mutation, runner integration, result-row schema mutation, analyzer/economic metric, dependency/lockfile, MLflow runtime state, or historical sidecar mutation is authorized. |
| O5b static/redacted billing reconciliation ingestion | committed | Commit `cf63de8` adds pure local static/redacted report parsing, O5a schema validation, dry-run default, explicit non-output write path, and limited attribution handling. |
| O5c Modal billing report collection | committed / adapter-ready blocked | Commit `dc48782` adds the adapter-ready blocked state. The approved live Modal billing CLI collection remains blocked by Modal billing-report limits. The full hourly window exceeded Modal's 7-day limit, and the chunked strategy hit the workspace billing report rate limit. No nonempty raw/redacted artifact is retained. |
| O6b Modal GPU performance smoke | committed / promotion-ready | Commit `403cfea` adds O6b performance smoke code/docs and the reviewed generated performance sidecar. O6b authorizes no additional Modal/GPU run, generation, profiler/Nsight/NCU, output mutation, result-row schema mutation, analyzer/economic metric, dependency/lockfile, historical sidecar/output mutation, or MLflow runtime work without a new signed packet. |
| structural/task analyzer metadata implementation spec | complete / extended for S4 planning | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.4 is the S0-S4 structural/task contract record. S1 analyzer metadata, S2 report consumption, and S3 report refresh are promoted; S4 adds future experiment packet guidance only and does not touch analyzer/report code or outputs. |
| agentic transcript implementation spec | complete | `docs/18_agentic_transcript_v1_implementation_spec.md` v0.1.5 created, routed, edge-case hardened, research cross-checked, and expanded with implementation checkpoint gates plus canonical rendering, public-evidence-only ranking, fixture manifest, byte-invariance, import-isolation, metadata-nullability, CLI/API/default, mixed-policy analyzer, commit-slicing, rollback, and no-cleanup gates; A0-A6 are promoted into the A6 handoff trunk at `4a84600`. |
| agentic transcript docs-only checkpoint | complete | `audits/agentic_transcript_v1_spec_checkpoint_report.md` v1.0.0 confirms source-doc inspection, readiness-audit reconciliation as `aligned_with_spec`, A0 readiness, no-code/no-output mutation, worktree caveats, and required local docs/import sanity tests. |
| agentic transcript A0 policy constants | complete | Commit `1e3f44468c5ae91e6467b42b7f93a068fa6acf5f` adds policy-name constants, keeps `DEFAULT_REPAIR_HISTORY_POLICY_V1` as `last_attempt_only_v1`, keeps Cluster 3 `P_HISTORY_POLICY_V1` as `last_attempt_only_v1`, and changes only the four allowed constants/test files. |
| agentic transcript A0.5 constants preflight | complete | `audits/agentic_transcript_v1_a0_5_preflight_report.md` v1.0.0 confirms A0 scope, default invariance, Cluster 3 compatibility, cheap imports, focused tests, optional prompt/loop import sanity, no forbidden-surface changes, no code/output mutation in A0.5, and baseline-venv caveat. |
| agentic transcript A1 prompt core | complete | `audits/agentic_transcript_v1_a1_prompt_core_report.md` v1.0.0 confirms pure prompt-core implementation, deterministic fixtures, config/evidence/ranking/rendering tests, legacy C/P byte-invariance snapshots, import isolation, no loop/runner/schema/analyzer/output changes, and baseline-venv caveat. |
| agentic transcript A2 C-loop integration | promoted/reference | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a2_c_loop_integration_report.md` v1.0.0 confirms opt-in Cluster 2 C-loop plumbing, preserved legacy defaults, runner policy flags, nullable/defaultable generated-row repair-history metadata, focused validation, and no Modal/output mutation. |
| agentic transcript A3 P-loop integration | promoted/reference | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a3_p_loop_integration_report.md` v1.0.0 confirms opt-in Cluster 3 P-loop plumbing, preserved legacy defaults, runner policy flags, nullable/defaultable generated-row P repair-history metadata, F1_COMPILE-only eligibility, F1_RUNTIME terminal behavior, no P-to-C transcript leakage, focused validation, and no Modal/output/generation mutation. |
| agentic transcript A4 P-to-C isolation proof | promoted/reference | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md` v1.0.0 confirms integrated post-P F2 and initial-F2 agentic C prompt isolation, P compile-history/hash exclusion, C seed/public-evidence proof, adapter fail-closed coverage, legacy prompt byte-invariance, and no Modal/output/generation mutation. |
| agentic transcript A5 analyzer grouping/quarantine | promoted/reference | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md` v1.0.0 confirms analyzer-side repair-history policy classification, grouping keys, mixed-policy/mixed-analysis quarantine, unknown-policy and incomplete-agentic quarantine, focused fixtures/tests, A1-A4 regression validation, and no Modal/output/generation mutation. |
| agentic transcript A6 run-packet gate planning | promoted/reference | Promoted into handoff trunk at `4a84600`; `docs/handoff/agentic_transcript_v1_run_packet_template.md` v1.0.0 and `docs/handoff/agentic_transcript_v1_next_run_packet.md` v0.1.0 define the future run approval gate; the next-run draft is `DRAFT_NOT_APPROVED`, all execution authorization flags are `NO`, analyzer quarantine and metadata checks are required before approval, and no Modal/output/generation/n=5/n=20/paper-scale mutation occurred. |
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
- Agentic-memory A1 prompt core is complete with baseline-venv caveat.
- Agentic-memory A2 through A6 are promoted into the handoff trunk at `4a84600`
  and preserved as evidence snapshots/reference history; future agentic
  execution still requires a signed run packet.
- The agentic next-run packet is `DRAFT_NOT_APPROVED` and authorizes no
  execution.
- O0 observability sidecar core is committed at `bcdaede` on
  `codex/observability-sidecar-core`.
- O1 local implementation for the explicitly named target
  `cluster3/experiments/run_cluster3_modal.py` is committed at `8eaef2e`; any
  future O1 maintenance agent must still stop with
  `O1_BLOCKED_TARGET_RUNNER_AMBIGUOUS` if this target becomes unclear.
- O2-Prep is committed at `74b3acd`; O2 Modal runtime context is committed at
  `6f3001e` within the named O2 target surfaces. It remains sidecar-only and
  authorizes no Modal/output/generation work.
- O3-Prep is committed at `c93bdc0`; O3 token telemetry implementation is
  committed at `4ddc767`. O3 remains count/status-only sidecar telemetry and
  authorizes no generation, model calls, tokenizer/model imports for telemetry,
  output mutation, billing, cost, performance, or result-row schema change.
- O0-O4 observability is accepted with caveats and promoted at `309c451`.
- O5-Prep and O5a are accepted locally through `c41a5bc`.
- O5b static/redacted billing reconciliation ingestion is committed at
  `cf63de8`; O5c adapter-ready blocked state is committed at `dc48782`.
  No nonempty raw/redacted billing artifact is retained.
- O5c live billing collection did not complete because Modal billing report
  requests hit workspace billing report rate limits. Future experiment-running
  agents should use the O5c adapter after experiment execution, not during
  kernel generation. Preferred manual/local command for multi-day windows:
  `modal billing report --start <YYYY-MM-DD> --end <YYYY-MM-DD> --resolution d --tag-names project,experiment_id,run_id,cluster,phase --json`.
  Daily resolution is preferred for multi-day windows. Hourly resolution should
  be used only for windows of 7 days or less, or after explicit approval. Modal
  billing report start dates are inclusive and end dates are exclusive. Raw
  billing reports must not be committed; sanitized reports must validate through
  O5b/O5a before use. If Modal rate-limits collection, stop and record
  `O5C_BLOCKED_MODAL_BILLING_RATE_LIMIT_WITH_ADAPTER_READY`.
- GitHub Actions must not run live billing collection yet. A future billing
  workflow, if added, must be `workflow_dispatch` only, use protected
  environment secrets and reviewer approval, upload no raw billing artifact,
  and avoid push or pull-request triggers. GitHub Actions may run safety
  tests/scans only for now.
- O6a Level-4 performance contract scaffolding is committed at `d966ad0`.
- O6b Modal GPU performance smoke is committed at `403cfea`. It ran one signed
  T4 smoke benchmark and includes
  `artifacts/observability_performance/o6b_smoke_relu_performance.jsonl` as
  reviewed smoke evidence.
- Compact O5b/O5c/O6a/O6b final promotion audit passed with caveats in
  `audits/observability_sidecar_o5b_o6b_final_promotion_report.md`.
- S0-S3 structural/task reporting is promoted into
  `codex-track-handoff-context` through `f1058eb`; scope was limited to S0
  terminology, S1 additive analyzer metadata, S2 report metadata consumption,
  and S3 derived report refresh. Ignored derived report previews remain
  uncommitted. No analyzer output rerun, raw JSONL rewrite, experiment run,
  Modal/GPU/generation, or raw output/artifact mutation was authorized.
- S4 future experiment integration is planning-only. It records how future
  packets must declare metric families, gates, denominators, evidence sources,
  and claim boundaries, but it produces no new evidence and authorizes no
  analyzer output refresh, report artifact refresh, raw JSONL rewrite,
  Modal/GPU/generation, experiment, benchmark, profiler, timing, speedup, or
  paper-scale work.

## Next Allowed Actions

Allowed next actions:

1. Commit and push the L2 n=20 runtime-gate promotion audit. This action does
   not execute L2.
2. After the promotion audit is pushed, verify the signed packet, verify
   protected paths are absent, verify `TRITONGEN_MLFLOW=0`, and run only the
   exact signed L2 n=20 command from the packet. Do not broaden the signed
   scope.
3. If the L1b analyzer/report artifacts are cited, cite the development-scale
   caveat: they are not paper-scale or reportable paper evidence, and
   three-way interaction fields are diagnostic only.
4. Retry O5c live billing collection only after the Modal workspace billing
   report rate limit clears, using a separate explicit billing approval packet.
   Prefer daily resolution for multi-day windows and hourly resolution only for
   windows of 7 days or less, or after explicit approval.
5. Do not run any additional O6b/O6c performance benchmark, output mutation,
   historical sidecar migration, analyzer/economic metrics,
   cost-per-success/pass@k cost, or paper-scale economic/performance claims
   without a new signed packet.
6. Keep ignored derived report previews
   `docs/preliminary_report/_report_data.json`,
   `docs/preliminary_report/index.html`, and
   `docs/preliminary_report/index.es.html` as local previews unless a future
   explicit review decision force-adds them as publication deliverables. Do not
   rerun analyzer output, rewrite raw JSONL, run experiments, or mutate raw
   outputs/artifacts without a separate signed packet.
7. Review A6 run-packet gate planning or prepare a future signed approval
   packet from `docs/handoff/agentic_transcript_v1_run_packet_template.md`.
   The current next-run packet is `DRAFT_NOT_APPROVED` and does not authorize
   Modal execution, generation, n=5, n=20, paper-scale work, or output
   mutation.
8. Create serialized-surface leases before touching analyzer, runner, repair
   loop, result schema, raw output, or any new report-data-builder surfaces.

Not allowed without explicit approval:

- Modal execution beyond the completed O6b smoke packet and completed L1b n=5
  run;
- another n=5 run execution;
- n=20 or paper-scale work beyond the exact signed L2 n=20 command after
  required pre-execution checks;
- output overwrite or mutation;
- billing query, credential use, Modal billing/API/CLI invocation, raw billing
  report processing, or historical sidecar migration;
- MLflow run creation, MLflow server startup, or writes to `mlruns/`;
- GitHub Actions live billing collection, raw billing artifact upload, or
  push/PR-triggered billing workflow;
- Modal/GPU performance execution, profiler trace collection, Nsight, NCU,
  timing execution, speedup computation, or benchmark execution beyond the
  completed O6b smoke packet without a new signed packet.

## A1 Prompt Core Checkpoint State

The `agentic_transcript_v1` feature branch has completed A0 policy constants,
A0.5 constants preflight, A1 prompt core, A2 C-loop integration, A3 P-loop
integration, A4 P-to-C isolation proof, A5 analyzer grouping/quarantine, and A6
run-packet gate planning. The branch is now the same A6 commit as the promoted
handoff trunk and is preserved as reference/history rather than active
observability work.

Current checkout:

```text
branch: codex/llm-repair-memory-agentic-transcript-v1
worktree: /private/tmp/tritongen-llm-repair-memory
spec: docs/18_agentic_transcript_v1_implementation_spec.md v0.1.5
state: docs/handoff/experiment_change_orchestration_state.md v1.5.22
registry: docs/handoff/document_version_registry.md v1.59.0
spec checkpoint: audits/agentic_transcript_v1_spec_checkpoint_report.md v1.0.0
A0 commit: 1e3f44468c5ae91e6467b42b7f93a068fa6acf5f
A0.5 preflight: audits/agentic_transcript_v1_a0_5_preflight_report.md v1.0.0
A1 prompt core report: audits/agentic_transcript_v1_a1_prompt_core_report.md v1.0.0
A2 C-loop integration: promoted into A6 trunk at 4a84600; audits/agentic_transcript_v1_a2_c_loop_integration_report.md v1.0.0
A3 P-loop integration: promoted into A6 trunk at 4a84600; audits/agentic_transcript_v1_a3_p_loop_integration_report.md v1.0.0
A4 P-to-C isolation proof: promoted into A6 trunk at 4a84600; audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md v1.0.0
A5 analyzer grouping/quarantine: promoted into A6 trunk at 4a84600; audits/agentic_transcript_v1_a5_analyzer_grouping_report.md v1.0.0
A6 run-packet gate planning: promoted into handoff trunk at 4a84600; audits/agentic_transcript_v1_a6_run_packet_gate_report.md v1.0.0; docs/handoff/agentic_transcript_v1_next_run_packet.md is DRAFT_NOT_APPROVED
next observability action: fast-forward `codex-track-handoff-context` to the O6 branch; O5c live billing retry, additional O6 performance runs, and future agentic runs still require the appropriate launch packet or signed run approval packet
```

A1 allowed files:

```text
shared/repair_history/__init__.py
shared/repair_history/policies.py
shared/repair_history/errors.py
shared/repair_history/evidence.py
shared/repair_history/ranking.py
shared/repair_history/rendering.py
shared/tests/test_repair_history_policies.py
shared/tests/test_repair_history_errors.py
shared/tests/test_repair_history_evidence.py
shared/tests/test_repair_history_ranking.py
shared/tests/test_repair_history_rendering.py
shared/tests/fixtures/repair_history/
```

A1 forbidden actions:

```text
no C/P repair-loop edits
no runner edits
no runner CLI edits
no result-schema edits
no analyzer edits
no output mutation
no Modal/generation work
no dependency or lockfile changes
no opportunistic cleanup
```

A1 required proof:

```text
fixture-first golden prompts
fixture acceptance manifest
legacy C/P byte-invariance snapshots
pure prompt-core import isolation
attempt evidence, anchor ranking, rendering, budget, injection, and hash tests
rollback independence from A2/A3 integration
```

Last successful A0.5 validation commands:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -v
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
```

Successful A1 validation commands:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_repair_history_errors.py shared/tests/test_repair_history_evidence.py shared/tests/test_repair_history_ranking.py shared/tests/test_repair_history_rendering.py -v
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -v
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
```

Results: A1 focused tests `63 passed`; Cluster 2 boundary tests `26 passed, 1
skipped`; Cluster 3 import tests `15 passed`. Standalone prompt-core import
isolation reported `forbidden_imports []`.

## Work Package Cards

### Completed Work Package: O0 Sidecar Core

```text
package: O0 sidecar core
launch packet id: O0-SIDECAR-CORE-2026-06-03
branch: codex/observability-sidecar-core
owner: current orchestration agent
scope: reconcile handoff state, tighten O-spec v0.2.1, then implement shared observability schema/logger/path/redaction core and tests only
requirement ids: O0-SCHEMA-STRICT; O0-EVENT-IDENTITY; O0-LOGGER-DURABLE; O0-PATH-COLLISION; O0-REDACTION; O0-IMPORT-BOUNDARY; O0-NO-RUNNER; O0-NO-OUTPUT
allowed files: docs/16_observability_sidecar_implementation_spec.md; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; shared/observability/__init__.py; shared/observability/schema.py; shared/observability/logger.py; shared/observability/paths.py; shared/observability/redaction.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py
forbidden files: cluster1/experiments/**; cluster2/experiments/**; cluster3/experiments/**; cluster1/results/**; cluster2/results/**; cluster3/results/**; shared/analysis/**; outputs/**; audits/**; dependency or lock files; Modal image definitions; MLflow runtime state
serialized surfaces: O0 observability sidecar core
entry gate: branch created from promoted handoff trunk at 4a8460081aa35a647901ea5fa120a76e0f7ef0e7; state reconciled; O-spec tightened to v0.2.1
exit gate: O0 focused tests pass; forbidden telemetry scans reviewed; git diff --check clean; no runner/result-schema/analyzer/raw-output/Modal/billing/MLflow-runtime/dependency changes
tests required: shared/tests/test_observability_schema.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py; forbidden privacy and performance telemetry scans; git diff --check; git status --short --branch
default-invariance proof required: yes, by absence of runner/result-schema/analyzer changes and import-boundary tests
fixture-first proof required: yes, local tmp_path sidecar write/resume fixtures only
independent review required: yes before promotion
commit/package slice: O0 sidecar core only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: strict schema unknown fields; invalid event sequence; path collision; incompatible resume metadata; forbidden private-eval/source/prompt/raw-log/secrets payloads; import-boundary leakage
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
run/output mutation allowed: no
escalation thresholds: stop on any need for runner instrumentation, result row schema changes, analyzer/report changes, raw output mutation, Modal/generation/billing/MLflow runtime access, dependency/network access, private-eval leakage, performance/profiler/timing/speedup telemetry, or branch scope growth beyond O0
handoff due: O0 checkpoint before O1 runner instrumentation
status: committed at bcdaedea4e76b1820978167e1b8439546ba2cc61; O0 focused tests and required boundary scans passed; no runner/result-schema/analyzer/output/Modal/billing/MLflow-runtime/dependency changes
```

### Completed Work Package: O1 Cluster 3 Local Runner Instrumentation

```text
package: O1 Cluster 3 local runner instrumentation
launch packet id: O1-CLUSTER3-RUNNER-OBS-2026-06-03
branch: codex/observability-sidecar-core
owner: current orchestration agent
scope: target discovery first, then opt-in observability events for exactly one local runner
target runner: cluster3/experiments/run_cluster3_modal.py
target tests: cluster3/tests/test_run_cluster3_modal_cli.py; shared/tests/test_observability_runner_contract.py only if a shared runner contract helper is needed
observability mode interface: --observability-mode off|best_effort|required; --observability-experiment-id <id>; --observability-run-id <id>; --observability-output <optional path>
requirement ids: O1-TARGET-DISCOVERY; O1-CLUSTER3-RUNNER-ONLY; O1-OPT-IN-MODE; O1-DEFAULT-OFF; O1-REQUIRED-PREFLIGHT; O1-SIDECAR-PATH-SAFETY; O1-ROW-SCHEMA-STABILITY; O1-NO-MODAL-RUN; O1-NO-OUTPUT-MUTATION; O1-NO-TOKEN-COST-BILLING
allowed files: cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py; shared/tests/test_observability_runner_contract.py if needed; shared/observability/* only for small runner-helper gaps that preserve O0 tests; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o1_runner_instrumentation_report.md
forbidden files: cluster1/**; cluster2/** except read-only inspection; cluster3/results/dataclass.py; cluster3/results/logger.py unless explicitly approved after target discovery; shared/analysis/**; outputs/**; mlruns/**; dependency or lock files; Modal image definitions; billing/pricing/token telemetry integration; scientific result-row schemas
serialized surfaces: Cluster 3 local runner CLI instrumentation for cluster3/experiments/run_cluster3_modal.py only
entry gate: baseline is O0 commit bcdaedea4e76b1820978167e1b8439546ba2cc61; worktree clean except approved O1 docs reconciliation; read this state, registry, hub, O-spec v0.2.1, and O0 core before code edits; confirm target runner and tests above
exit gate: omitted mode and explicit off preserve existing behavior and write no sidecars; enabled modes require experiment_id/run_id; invalid mode or invalid required preflight leaves generation, correctness, repair, and Modal dependencies uncalled; sidecars are tmp_path-only in tests; no scientific row fields change; no Modal/output mutation occurs
tests required: .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py shared/tests/test_observability_schema.py shared/tests/test_observability_logger.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py -q; add shared/tests/test_observability_runner_contract.py if created; no-Modal/no-output-mutation check; forbidden privacy scan; forbidden performance/profiler/timing scan; git diff --check; git status --short --branch
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: O1 Cluster 3 local runner instrumentation only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: target ambiguity stop condition; invalid observability mode; enabled mode without experiment_id/run_id; required mode path collision before runner work; off mode writes no sidecar; dependency adapters uncalled on invalid required preflight; forbidden event payloads rejected
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
run/output mutation allowed: no
escalation thresholds: stop on any need to pick a different runner, touch multiple runners, change result-row schemas, touch analyzers, mutate outputs, call Modal/generation/billing/MLflow runtime, add dependency/network access, record token/cost/billing/Modal identity telemetry, or add performance/profiler/timing/speedup/kernel benchmark fields
handoff due: O1 checkpoint before any O2/O3/O4 work or any observability-covered run claim
status: committed at 8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a; O1 review passed before commit; no Modal/output/generation run authorized or performed
```

### Completed Work Package: O2-Prep Modal Runtime Context Launch Reconciliation

```text
package: O2-Prep Modal runtime context launch reconciliation
launch packet id: O2-PREP-MODAL-CONTEXT-2026-06-03
branch: codex/observability-sidecar-core
owner: current orchestration agent
scope: docs-only target and scope naming before O2 implementation; no O2 runtime code starts in this package
baseline commit: 8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/modal_harness/runtime.py; shared/observability/schema.py; shared/observability/redaction.py; cluster3/experiments/run_cluster3_modal.py
target surfaces for later O2 implementation: shared/observability/schema.py for optional safe Modal context schema tightening already represented by ObservabilityModalContext; shared/observability/redaction.py for Modal-specific allowlist/denylist validation; shared/modal_harness/runtime.py only to expose safe existing Modal function-call/input identifiers through current_modal_ids() without changing invocation semantics; cluster3/experiments/run_cluster3_modal.py only to pass optional safe Modal context into existing O1 sidecar events and summaries; cluster3/tests/test_run_cluster3_modal_cli.py plus shared/tests/test_observability_schema.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py for O2 tests
requirement ids: O2-PREP-TARGET-SURFACE; O2-PREP-SAFE-FIELDS; O2-PREP-FORBIDDEN-FIELDS; O2-PREP-NO-RUNTIME-CODE; O2-PREP-NO-MODAL-RUN; O2-PREP-NO-OUTPUT; O2-PREP-NO-BILLING-COST-PERF; O2-PREP-TEST-PLAN
allowed files for O2-Prep: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md if needed; docs/16_observability_sidecar_implementation_spec.md only for narrow O2 clarification; audits/observability_sidecar_o2_prep_report.md
forbidden files for O2-Prep: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
allowed files for later O2 implementation after O2_PREP_COMPLETE: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/__init__.py only if exports need updating; shared/modal_harness/runtime.py only for safe existing runtime identifier exposure; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py; cluster3/experiments/run_cluster3_modal.py only to pass optional safe Modal context into O1 sidecars without changing Modal execution behavior; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o2_modal_context_report.md
forbidden files for later O2 implementation: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pricing/billing files; dependency or lock files; Modal app/image/function definitions unless a separate approved spec explicitly authorizes them; scientific result-row schemas; analyzers
safe Modal context fields: modal_context_available or spec-equivalent unavailable status; is_remote; function_call_id; input_id; task_id; image_id; region; cloud_provider; environment_name; app_name; gpu_type; gpu_count; cpu_cores; memory_gib; timeout_s; container_started_at_utc; modal_context_source
safe Modal context sources: shared_modal_runtime_helper; modal_environment_allowlist; runner_config; unavailable
allowed Modal environment keys: MODAL_TASK_ID; MODAL_IMAGE_ID; MODAL_REGION; MODAL_CLOUD_PROVIDER; MODAL_ENVIRONMENT; MODAL_IS_REMOTE
forbidden Modal context fields: secrets; tokens; credentials; passwords; API keys; environment variable dumps; Modal identity tokens including MODAL_IDENTITY_TOKEN; billing data; invoice data; actual cost; GPU utilization; GPU power; GPU memory metrics; GPU temperature; profiler data; kernel timing; latency; throughput; speedup; performance metrics; prompts; source text; raw model output; raw feedback; raw compile logs
behavior constraints for later O2: no .remote() to .spawn() switch; no new Modal invocation; no GPU run; no generation run; no output mutation; no scientific result-row schema mutation; no billing/cost/pricing logic; no performance telemetry; only enrich sidecar events when safe context is already present or dependency-injected; observability mode still defaults to off; omitted/off behavior remains unchanged; missing context records unavailable/false rather than crashing
required O2 tests after O2-Prep: safe context fields accepted; forbidden Modal/secrets/env fields rejected; no Modal import in shared/observability core except allowed import-boundary tests; no .spawn() introduction; no new Modal invocation in tests; off mode unchanged; best_effort and required sidecars can include safe context when supplied; missing context marks modal_context_available false or source unavailable; no result-row schema mutation; no outputs mutation
O2-Prep tests/checks: git diff --check; git status --short --branch; forbidden code-scope diff for shared/observability shared/modal_harness cluster1 cluster2 cluster3 shared/analysis shared/repair_history outputs dependencies lockfiles mlruns; positive authorization scan for Modal/GPU/generation/output/n5/n20/paper-scale YES flags; forbidden O2 scope scan reviewed as prohibitions/caveats/stop conditions only
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
stop conditions: O2_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS if exact later implementation surfaces cannot be named; O2_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK if any doc authorizes Modal/GPU/generation/output/n5/n20/paper-scale execution; O2_PREP_BLOCKED_SCOPE_VIOLATION if runtime code, outputs, dependencies, lockfiles, or MLflow state are modified; O2_PREP_BLOCKED_DOC_CONTRADICTION if docs conflict on O2 target, allowed files, or authorization state
handoff destination: audits/observability_sidecar_o2_prep_report.md and this state file
status: committed at 74b3acd504f1dfc252c05a4c746fc9914c186b4d; O2-Prep review passed before commit; no Modal/output/generation run authorized or performed
```

### Completed Work Package: O2 Modal Runtime Context Implementation

```text
package: O2 Modal runtime context implementation
launch packet id: O2-MODAL-CONTEXT-2026-06-03
branch: codex/observability-sidecar-core
owner: current implementation agent
scope: optional safe Modal runtime context sidecar enrichment for Cluster 3 O1 observability only; no Modal execution, output mutation, generation run, billing/cost, GPU metric, performance/profiler/timing, or scientific row schema change
baseline commit: 74b3acd504f1dfc252c05a4c746fc9914c186b4d
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; audits/observability_sidecar_o2_prep_report.md; shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py
target surfaces: shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py
test surfaces: shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py
docs/report surfaces: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o2_modal_context_report.md
requirement ids: O2-SAFE-SCHEMA; O2-REDACTION-DENYLIST; O2-LAZY-RUNTIME-HELPER; O2-CLUSTER3-SIDECAR-WIRING; O2-OFF-NO-COLLECTION; O2-BEST-EFFORT-DEGRADE; O2-REQUIRED-FAIL-CLOSED; O2-NO-MODAL-RUN; O2-NO-SPAWN; O2-NO-OUTPUT; O2-NO-RESULT-SCHEMA
allowed files: shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o2_modal_context_report.md
forbidden files: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; cluster3/feedback/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pricing/billing files; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers
implemented context behavior: ObservabilityModalContext now requires explicit modal_context_available; unavailable context must be source unavailable and cannot carry runtime fields; shared/modal_harness/runtime.py exposes lazy allowlist normalization and current-ID collection helpers without top-level Modal import; Cluster 3 collects no context in off mode and uses dependency-injected or unavailable context in enabled modes
safe Modal context fields: modal_context_available; is_remote; function_call_id; input_id; task_id; image_id; region; cloud_provider; environment_name; app_name; gpu_type; gpu_count; cpu_cores; memory_gib; timeout_s; container_started_at_utc; modal_context_source
forbidden Modal context fields: secrets; tokens; credentials; passwords; API keys; environment variable dumps; Modal identity tokens including MODAL_IDENTITY_TOKEN; billing data; invoice data; actual cost; GPU utilization; GPU power; GPU memory metrics; GPU temperature; profiler data; kernel timing; latency; throughput; speedup; performance metrics; prompts; source text; raw model output; raw feedback; raw compile logs
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
tests/checks run: shared O0/O2 observability suite passed; Cluster 3 runner suite passed; full validation recorded in audits/observability_sidecar_o2_modal_context_report.md
unresolved risk: real remote Modal context remains unproven until a later approved execution packet; O2 only proves schema, redaction, helper, and local fake wiring
status: committed at 6f3001e32f5145bd0efadf7a9e60f87bfe3f323a; O2 review passed before commit; no Modal/output/generation run authorized or performed
```

### Completed Work Package: O3-Prep Token Telemetry Launch Reconciliation

```text
package: O3-Prep token telemetry launch reconciliation
launch packet id: O3-PREP-TOKEN-TELEMETRY-2026-06-03
branch: codex/observability-sidecar-core
owner: current orchestration agent
scope: docs-only target and scope naming before O3 implementation; no O3 runtime code starts in this package
baseline commit: 6f3001e32f5145bd0efadf7a9e60f87bfe3f323a
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py
target surfaces for later O3 implementation: shared/observability/schema.py for count/status-only token schema tightening and non-negative integer/total consistency validation; shared/observability/redaction.py for fail-closed token-ID, prompt, generated-text, raw-output, source, tokenizer-dump, and private-feedback payload rejection; shared/observability/logger.py only to validate token_totals summaries against the event sidecar; cluster3/experiments/run_cluster3_modal.py only to attach token counts to O1 sidecar events when counts are already available or cheaply computable without new generation/model/tokenizer work; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py
requirement ids: O3-PREP-TARGET-SURFACE; O3-PREP-COUNT-FIELDS; O3-PREP-FORBIDDEN-TOKEN-PAYLOADS; O3-PREP-NO-RUNTIME-CODE; O3-PREP-NO-GENERATION; O3-PREP-NO-TOKENIZER-MODEL-IMPORT; O3-PREP-NO-OUTPUT; O3-PREP-NO-BILLING-COST-PERF; O3-PREP-TEST-PLAN
allowed files for O3-Prep: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md only for narrow O3 clarification; audits/observability_sidecar_o3_prep_report.md
forbidden files for O3-Prep: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
allowed files for later O3 implementation after O3_PREP_COMPLETE: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o3_token_telemetry_report.md
forbidden files for later O3 implementation: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; cluster3/feedback/** except read-only inspection; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pricing/billing files; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers
allowed token telemetry fields: token_counts_available; prompt_tokens; generated_tokens; total_tokens; token_count_source or schema-compatible count_source during migration; token_count_status or unavailable equivalent
allowed token count sources: generation_sequence_length_delta; existing_generation_result; existing_remote_payload; unavailable; not_applicable
token count rules: counts are non-negative integers; non-finite, string, float, negative, or coerced counts are rejected; total_tokens equals prompt_tokens plus generated_tokens when all three are present; unavailable counts must be explicit and must not guess
forbidden token payloads: token_ids; input_ids; output_ids; prompt_text; completion_text; generated_text; raw_output; raw_completion; source_text; full_source; tokenizer dump; tokenizer internal state; hidden prompts; private eval/feedback details; raw model output; raw feedback; generated source text
behavior constraints for later O3: no generation run; no model call; no tokenizer/model import in shared/observability; no prompt text/source/generated/raw text storage; no token IDs; no result-row schema mutation; no output mutation; no billing/cost/performance work; observability remains default-off; omitted/off behavior remains unchanged; token counts may be recorded only if already available in the current code path or supplied by tests/fakes; if counts are absent, record unavailable rather than invoking a tokenizer/model path
required O3 tests after O3-Prep: valid counts accepted; missing counts unavailable-safe; negative/non-int/non-finite/coerced counts rejected; total_tokens consistency enforced; token IDs rejected; prompt/generated/raw/source text rejected; tokenizer dumps/internal state rejected; no tokenizer/model imports in shared/observability; off mode unchanged; enabled sidecars can include supplied counts; summary token_totals match event stream; no result-row mutation; no outputs mutation; no generation/model/tokenizer execution
O3-Prep tests/checks: git diff --check; git status --short --branch; forbidden code-scope diff for shared/observability shared/modal_harness cluster1 cluster2 cluster3 shared/analysis shared/repair_history outputs dependencies lockfiles mlruns; positive authorization scan for Modal/GPU/generation/output/n5/n20/paper-scale YES flags; forbidden O3 scope scan reviewed as prohibitions/caveats/stop conditions only
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
stop conditions: O3_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS if exact later implementation surfaces cannot be named; O3_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK if any doc authorizes Modal/GPU/generation/output/n5/n20/paper-scale execution; O3_PREP_BLOCKED_SCOPE_VIOLATION if runtime code, outputs, dependencies, lockfiles, or MLflow state are modified; O3_PREP_BLOCKED_DOC_CONTRADICTION if docs conflict on O3 target, allowed files, token fields, forbidden payloads, or authorization state
handoff destination: audits/observability_sidecar_o3_prep_report.md and this state file
status: committed at c93bdc0d19945e885b2121ee7efe12b6ea05db2e; superseded by the O3 token telemetry implementation package; AUTHORIZES_EXECUTION: NO
```

### Reference Work Package: A2 C-loop Integration

```text
package: A2 C-loop integration
launch packet id: A2-C-LOOP-2026-06-02
branch: codex/llm-repair-memory-agentic-transcript-v1
owner: current orchestration agent
scope: opt-in Cluster 2 C-loop integration for agentic_transcript_v1 prompt history and metadata
requirement ids: A2-C-DEFAULT-INVARIANCE; A2-C-OPT-IN-AGENTIC; A2-C-F2-ONLY; A2-C-FAIL-CLOSED-CONFIG; A2-C-METADATA; A2-C-NO-RUN
allowed files: cluster2/feedback/prompts.py; cluster2/feedback/repair_loop.py; cluster2/feedback/trace.py; cluster2/experiments/run_cluster2_modal.py; cluster2/results/dataclass.py; cluster2/tests/test_feedback_prompts.py; cluster2/tests/test_repair_loop.py; cluster2/tests/test_results_logger.py; cluster2/tests/test_run_cluster2_modal.py
forbidden files: cluster1/**; cluster3/**; shared/analysis/**; outputs/**; result analyzers; dependency or lock files; Modal image definitions beyond allowed runner plumbing
serialized surfaces: C-loop repair policy integration; Cluster 2 runner policy plumbing
entry gate: historical A2 entry gate was A1 prompt core complete plus C-loop and Cluster 2 runner leases; current promoted trunk is 4a84600
exit gate: focused Cluster 2 tests pass; default prompt bytes unchanged for omitted and last_attempt_only_v1 policy; agentic prompt path opt-in only; invalid config fails closed; metadata fields nullable/defaultable for legacy rows; no Modal/output mutation
tests required: cluster2 feedback prompt tests; cluster2 repair loop tests; Cluster 2 runner CLI/default tests if runner touched; Cluster 2 result dataclass/logger tests if result metadata touched; A1 shared prompt-core suite for regression; forbidden-path and git diff checks
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: A2 C-loop integration only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: invalid policy; invalid max_prompt_chars; invalid include_latest_source; C outside F2 remains ineligible; no hidden fallback from failed agentic render
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
docs required: update this state and registry at launch and closeout; create A2 checkpoint report if implementation completes
run/output mutation allowed: no
escalation thresholds: stop on default behavior drift, F2 eligibility drift, hidden fallback need, result-schema migration beyond nullable/defaultable metadata, private-eval leakage, Modal/output mutation need, dependency/network need, or branch scope growth beyond A2
handoff due: A2 review checkpoint before A3/A4/A5
status: promoted into A6 handoff trunk at 4a84600; reference/history only
```

### Reference Work Package: A3 P-loop Integration

```text
package: A3 P-loop integration
launch packet id: A3-P-LOOP-2026-06-02
branch: codex/llm-repair-memory-agentic-transcript-v1
owner: current orchestration agent
scope: opt-in Cluster 3 P-loop integration for agentic_transcript_v1 prompt history and metadata
requirement ids: A3-P-DEFAULT-INVARIANCE; A3-P-OPT-IN-AGENTIC; A3-P-F1-COMPILE-ONLY; A3-P-F1-RUNTIME-TERMINAL; A3-P-FAIL-CLOSED-CONFIG; A3-P-METADATA; A3-P-NO-C-LEAKAGE; A3-P-NO-RUN
allowed files: cluster3/feedback/prompts.py; cluster3/feedback/compile_error_repair.py; cluster3/feedback/trace.py; cluster3/experiments/run_cluster3_modal.py; cluster3/results/dataclass.py; cluster3/tests/test_p_prompts.py; cluster3/tests/test_p_repair_loop.py; cluster3/tests/test_cluster3_schema.py; cluster3/tests/test_run_cluster3_modal_cli.py; cluster3/tests/test_cluster3_imports.py
forbidden files: cluster1/**; cluster2/feedback/**; cluster2/results/**; cluster2/experiments/**; shared/analysis/**; outputs/**; analyzers; dependency or lock files; Modal image definitions beyond allowed runner plumbing; prompt-core files unless a blocking A1 bug is separately scoped
serialized surfaces: P-loop repair policy integration; Cluster 3 runner/schema policy plumbing
entry gate: historical A3 entry gate was A1 prompt core complete, A2 committed, and P-loop / Cluster 3 runner-schema leases; current promoted trunk is 4a84600
exit gate: focused Cluster 3 tests pass; default P prompt bytes unchanged for omitted and last_attempt_only_v1 policy; agentic prompt path opt-in only; invalid config fails closed before generation; metadata fields nullable/defaultable for legacy rows; F1_COMPILE-only P eligibility preserved; F1_RUNTIME remains terminal; no C correctness transcript or P-to-C prompt leakage; no Modal/output/generation mutation
tests required: Cluster 3 P prompt tests; Cluster 3 P repair loop tests; Cluster 3 runner CLI/default tests; Cluster 3 result schema/logger tests if result metadata touched; A1 shared prompt-core suite; A2 focused Cluster 2 suite for regression; Cluster 3 import tests; forbidden-path and git diff checks
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: A3 P-loop integration only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: invalid policy; invalid max_prompt_chars; invalid include_latest_source; P outside F1_COMPILE remains ineligible; F1_RUNTIME terminal; no hidden fallback from failed agentic render; forbidden P feedback terms
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
docs required: update this state and registry at launch and closeout; create A3 checkpoint report if implementation completes
run/output mutation allowed: no
escalation thresholds: stop on default P behavior drift, F1_COMPILE eligibility drift, F1_RUNTIME terminal drift, hidden fallback need, result-schema migration beyond nullable/defaultable metadata, private-eval/C correctness/P-to-C leakage, Modal/output/generation need, dependency/network need, or branch scope growth beyond A3
handoff due: A3 review checkpoint before A4/A5/A6
status: promoted into A6 handoff trunk at 4a84600; reference/history only
```

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
commit/package slice:
rollback independence proof required: yes/no
opportunistic cleanup included: no unless explicitly scoped
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
commit/package slice:
rollback independence proof required: yes/no
opportunistic cleanup included: no unless explicitly scoped
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

### Completed Launch Packet: O0-SIDECAR-CORE-2026-06-03

```text
launch packet id: O0-SIDECAR-CORE-2026-06-03
agent role: implementation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 4a8460081aa35a647901ea5fa120a76e0f7ef0e7
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md
package: O0 sidecar core
requirement ids in scope: O0-SCHEMA-STRICT; O0-EVENT-IDENTITY; O0-LOGGER-DURABLE; O0-PATH-COLLISION; O0-REDACTION; O0-IMPORT-BOUNDARY; O0-NO-RUNNER; O0-NO-OUTPUT
allowed files: docs/16_observability_sidecar_implementation_spec.md; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; shared/observability/__init__.py; shared/observability/schema.py; shared/observability/logger.py; shared/observability/paths.py; shared/observability/redaction.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py
forbidden files: cluster1/experiments/**; cluster2/experiments/**; cluster3/experiments/**; cluster1/results/**; cluster2/results/**; cluster3/results/**; shared/analysis/**; outputs/**; audits/**; dependency or lock files; Modal image definitions; MLflow runtime state
serialized surfaces: O0 observability sidecar core
entry gate: clean promoted handoff trunk at 4a84600; O0 branch created; state/spec/registry reconciliation completed before O0 code
exit gate: O0 handoff records files changed, tests/checks run, import-boundary proof, forbidden-files check, no Modal/output/billing/dependency mutation, unresolved risks, and next blocked package or gate
required tests/checks: .venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_logger.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py -q; forbidden privacy scan; forbidden performance/profiler/timing scan; git diff --check; git status --short --branch
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: O0 sidecar core only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: strict schema unknown fields; invalid event sequence; path collision; incompatible resume metadata; forbidden private-eval/source/prompt/raw-log/secrets payloads; import-boundary leakage
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on any need for runner instrumentation, result row schema changes, analyzer/report changes, raw output mutation, Modal/generation/billing/MLflow runtime access, dependency/network access, private-eval leakage, performance/profiler/timing/speedup telemetry, or branch scope growth beyond O0
stop triggers: O-spec v0.2.1 stop boundaries plus orchestration escalation thresholds
handoff destination: O0 checkpoint and this state file
state update owner: orchestrator
status: committed at bcdaedea4e76b1820978167e1b8439546ba2cc61
```

### Completed Launch Packet: O1-CLUSTER3-RUNNER-OBS-2026-06-03

```text
launch packet id: O1-CLUSTER3-RUNNER-OBS-2026-06-03
agent role: implementation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: bcdaedea4e76b1820978167e1b8439546ba2cc61
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/observability/schema.py; shared/observability/logger.py; shared/observability/paths.py; shared/observability/redaction.py
package: O1 Cluster 3 local runner instrumentation
target discovery gate: exact target runner is cluster3/experiments/run_cluster3_modal.py; exact primary test file is cluster3/tests/test_run_cluster3_modal_cli.py; stop with O1_BLOCKED_TARGET_RUNNER_AMBIGUOUS if any other runner appears to be in scope
requirement ids in scope: O1-TARGET-DISCOVERY; O1-CLUSTER3-RUNNER-ONLY; O1-OPT-IN-MODE; O1-DEFAULT-OFF; O1-REQUIRED-PREFLIGHT; O1-SIDECAR-PATH-SAFETY; O1-ROW-SCHEMA-STABILITY; O1-NO-MODAL-RUN; O1-NO-OUTPUT-MUTATION; O1-NO-TOKEN-COST-BILLING
allowed files: cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py; shared/tests/test_observability_runner_contract.py if needed; shared/observability/* only for small runner-helper gaps that preserve O0 tests; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o1_runner_instrumentation_report.md
forbidden files: cluster1/**; cluster2/** except read-only inspection; cluster3/results/dataclass.py; cluster3/results/logger.py unless explicitly approved after target discovery; shared/analysis/**; outputs/**; mlruns/**; dependency or lock files; Modal image definitions; billing/pricing/token telemetry integration; scientific result-row schemas
serialized surfaces: Cluster 3 local runner CLI instrumentation only
entry gate: clean O0 baseline at bcdaede; target discovery recorded before code edits; no Modal/output/generation/n=5/n=20/paper-scale approval attached
exit gate: focused tests prove off/default invariance, enabled sidecar writes, required preflight failure before runner work, sidecar path safety, no new scientific row fields, no unauthorized output mutation, and no forbidden telemetry leakage
required tests/checks: .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py shared/tests/test_observability_schema.py shared/tests/test_observability_logger.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py -q; shared/tests/test_observability_runner_contract.py if created; no-Modal/no-output-mutation check; forbidden privacy scan; forbidden performance/profiler/timing scan; git diff --check; git status --short --branch
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: O1 Cluster 3 local runner instrumentation only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: invalid observability mode; missing experiment_id/run_id when enabled; path collision in required mode before runner work; off mode no sidecars; dependency adapters uncalled on invalid required preflight; forbidden event payload rejection
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on any need to pick a different runner, touch multiple runners, change result-row schemas, touch analyzers, mutate outputs, call Modal/generation/billing/MLflow runtime, add dependency/network access, record token/cost/billing/Modal identity telemetry, or add performance/profiler/timing/speedup/kernel benchmark fields
stop triggers: O-spec v0.2.1 stop boundaries plus target ambiguity or scope growth beyond cluster3/experiments/run_cluster3_modal.py
handoff destination: O1 checkpoint report and this state file
state update owner: orchestrator
status: committed at 8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a; review passed before commit; no Modal/output/generation run authorized or performed
```

### Completed Launch Packet: O2-PREP-MODAL-CONTEXT-2026-06-03

```text
launch packet id: O2-PREP-MODAL-CONTEXT-2026-06-03
agent role: documentation reconciliation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/modal_harness/runtime.py; shared/observability/schema.py; shared/observability/redaction.py; cluster3/experiments/run_cluster3_modal.py
package: O2-Prep Modal runtime context launch reconciliation
target discovery gate: O2 implementation target surfaces are shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py; their named tests are shared/tests/test_observability_schema.py, shared/tests/test_observability_redaction.py, shared/tests/test_observability_imports.py, and cluster3/tests/test_run_cluster3_modal_cli.py. Stop with O2_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS if these surfaces become unclear.
requirement ids in scope: O2-PREP-TARGET-SURFACE; O2-PREP-SAFE-FIELDS; O2-PREP-FORBIDDEN-FIELDS; O2-PREP-NO-RUNTIME-CODE; O2-PREP-NO-MODAL-RUN; O2-PREP-NO-OUTPUT; O2-PREP-NO-BILLING-COST-PERF; O2-PREP-TEST-PLAN
allowed files: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md if needed; docs/16_observability_sidecar_implementation_spec.md only for narrow O2 clarification; audits/observability_sidecar_o2_prep_report.md
forbidden files: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
serialized surfaces: handoff docs and O2 launch naming only
entry gate: clean O1 baseline at 8eaef2e; O1 committed; no Modal/output/generation/n=5/n=20/paper-scale approval attached
exit gate: O2 target surfaces, allowed files, forbidden files, safe/forbidden Modal fields, required tests, stop conditions, and no-execution authorization state are explicit; runtime code untouched; forbidden code-scope diff empty; positive authorization scan empty
required tests/checks: git diff --check; git status --short --branch; forbidden code-scope diff; positive authorization scan; forbidden O2 scope scan reviewed as prohibitions/caveats/stop conditions only
default-invariance proof required: yes, by docs-only scope and no runtime code changes
fixture-first proof required: not applicable in O2-Prep; required for later O2 implementation tests
independent review required: yes before O2 implementation promotion if runtime code changes in later package
commit/package slice: O2-Prep docs-only launch reconciliation only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required for later O2 implementation: forbidden Modal/secrets/env fields rejected; no .spawn() introduction; no new Modal invocation in tests; off mode unchanged; missing context unavailable-safe; no result-row schema mutation; no outputs mutation
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on target ambiguity, execution authorization leakage, runtime-code edits, output mutation, dependency/lockfile changes, MLflow runtime state changes, secret/token/credential/env-dump capture, GPU metric capture, billing/cost/invoice capture, performance/profiler/timing/speedup/latency/throughput capture, or result-row schema mutation
stop triggers: O2_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS; O2_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK; O2_PREP_BLOCKED_SCOPE_VIOLATION; O2_PREP_BLOCKED_DOC_CONTRADICTION
handoff destination: audits/observability_sidecar_o2_prep_report.md and this state file
state update owner: orchestrator
status: committed at 74b3acd504f1dfc252c05a4c746fc9914c186b4d; O2-Prep complete; AUTHORIZES_EXECUTION: NO
```

### Completed Launch Packet: O2-MODAL-CONTEXT-2026-06-03

```text
launch packet id: O2-MODAL-CONTEXT-2026-06-03
agent role: implementation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 74b3acd504f1dfc252c05a4c746fc9914c186b4d
package: O2 Modal runtime context implementation
target discovery gate: O2 implementation target surfaces are shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py; their named tests are shared/tests/test_observability_schema.py, shared/tests/test_observability_redaction.py, shared/tests/test_observability_imports.py, and cluster3/tests/test_run_cluster3_modal_cli.py. Stop with O2_BLOCKED_TARGET_SURFACE_AMBIGUOUS if these surfaces become unclear.
allowed files: shared/observability/schema.py; shared/observability/redaction.py; shared/modal_harness/runtime.py; cluster3/experiments/run_cluster3_modal.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o2_modal_context_report.md
forbidden files: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; cluster3/feedback/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pricing/billing files; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers
serialized surfaces: O2 sidecar schema/redaction/runtime helper, Cluster 3 O1 sidecar wiring, O2 tests, and O2 audit docs only
entry gate: O2-Prep committed at 74b3acd; O1 committed at 8eaef2e; no Modal/output/generation/n=5/n=20/paper-scale approval attached
exit gate: safe context fields accepted; forbidden Modal/private/performance/billing fields rejected; missing context unavailable-safe; shared.observability import isolation clean; no .remote() to .spawn() switch; no new Modal invocation; off mode unchanged; enabled sidecars include supplied safe context; best_effort degrades safely; required mode fails closed on forbidden context; no result-row schema or outputs mutation
fixture-first proof required: yes, local fake Modal context only
independent review required: yes before O2 commit/promotion
commit/package slice: O2 implementation and audit docs only
opportunistic cleanup included: no
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
stop triggers: O2_BLOCKED_TARGET_SURFACE_AMBIGUOUS; O2_BLOCKED_SCOPE_VIOLATION; O2_BLOCKED_MODAL_BEHAVIOR_CHANGE; O2_BLOCKED_PRIVATE_PAYLOAD_RISK; O2_BLOCKED_TELEMETRY_CLAIM_LEAK
handoff destination: audits/observability_sidecar_o2_modal_context_report.md and this state file
state update owner: implementation agent
status: committed at 6f3001e32f5145bd0efadf7a9e60f87bfe3f323a; O2 review passed before commit; AUTHORIZES_EXECUTION: NO
```

### Completed Launch Packet: O3-PREP-TOKEN-TELEMETRY-2026-06-03

```text
launch packet id: O3-PREP-TOKEN-TELEMETRY-2026-06-03
agent role: documentation reconciliation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 6f3001e32f5145bd0efadf7a9e60f87bfe3f323a
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py
package: O3-Prep token telemetry launch reconciliation
target discovery gate: O3 implementation target surfaces are shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py; their named tests are shared/tests/test_observability_schema.py, shared/tests/test_observability_redaction.py, shared/tests/test_observability_logger.py, shared/tests/test_observability_imports.py, and cluster3/tests/test_run_cluster3_modal_cli.py. Stop with O3_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS if these surfaces become unclear.
requirement ids in scope: O3-PREP-TARGET-SURFACE; O3-PREP-COUNT-FIELDS; O3-PREP-FORBIDDEN-TOKEN-PAYLOADS; O3-PREP-NO-RUNTIME-CODE; O3-PREP-NO-GENERATION; O3-PREP-NO-TOKENIZER-MODEL-IMPORT; O3-PREP-NO-OUTPUT; O3-PREP-NO-BILLING-COST-PERF; O3-PREP-TEST-PLAN
allowed files: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md only for narrow O3 clarification; audits/observability_sidecar_o3_prep_report.md
forbidden files: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
serialized surfaces: handoff docs and O3 token telemetry launch naming only
entry gate: clean O2 baseline at 6f3001e; O2 committed; no Modal/output/generation/n=5/n=20/paper-scale approval attached
exit gate: O3 target surfaces, allowed files, forbidden files, count/status-only token fields, forbidden token/raw text payloads, required tests, stop conditions, and no-execution authorization state are explicit; runtime code untouched; forbidden code-scope diff empty; positive authorization scan empty
required tests/checks: git diff --check; git status --short --branch; forbidden code-scope diff; positive authorization scan; forbidden O3 scope scan reviewed as prohibitions/caveats/stop conditions only
default-invariance proof required: yes, by docs-only scope and no runtime code changes
fixture-first proof required: not applicable in O3-Prep; required for later O3 implementation tests/fakes
independent review required: yes before O3 implementation promotion if runtime code changes in later package
commit/package slice: O3-Prep docs-only launch reconciliation only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required for later O3 implementation: token IDs rejected; prompt/generated/source/raw text rejected; tokenizer dump/internal state rejected; invalid count types rejected; total mismatch rejected; no tokenizer/model imports in shared/observability; off mode unchanged; no result-row schema mutation; no outputs mutation
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on target ambiguity, execution authorization leakage, runtime-code edits during O3-Prep, output mutation, dependency/lockfile changes, MLflow runtime state changes, token ID storage, prompt/source/generated/raw text storage, private eval/feedback leakage, tokenizer/model import in shared/observability, generation/model/tokenizer execution, billing/cost broadening, performance/profiler/timing/speedup/latency/throughput capture, or result-row schema mutation
stop triggers: O3_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS; O3_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK; O3_PREP_BLOCKED_SCOPE_VIOLATION; O3_PREP_BLOCKED_DOC_CONTRADICTION
handoff destination: audits/observability_sidecar_o3_prep_report.md and this state file
state update owner: orchestrator
status: committed at c93bdc0d19945e885b2121ee7efe12b6ea05db2e; O3 implementation has since committed on the same observability branch; AUTHORIZES_EXECUTION: NO
```

### Completed Work Package: O3 Token Telemetry Implementation

```text
package: O3 token telemetry implementation
launch packet id: O3-TOKEN-TELEMETRY-2026-06-03
branch: codex/observability-sidecar-core
owner: current implementation agent
scope: count/status-only token telemetry in observability sidecars for Cluster 3 O1 events; no tokenizer/model/generation execution, no output mutation, no result-row schema mutation, no Modal invocation, no billing/cost/performance telemetry
baseline commit: c93bdc0d19945e885b2121ee7efe12b6ea05db2e
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; audits/observability_sidecar_o3_prep_report.md; shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py
target surfaces: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py
test surfaces: shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py
docs/report surfaces: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o3_token_telemetry_report.md
requirement ids: O3-COUNT-SCHEMA; O3-REDACTION-DENYLIST; O3-SUMMARY-TOKEN-TOTALS; O3-CLUSTER3-INJECTED-COUNTS; O3-OFF-NO-COLLECTION; O3-BEST-EFFORT-DEGRADE; O3-REQUIRED-FAIL-CLOSED; O3-NO-TOKENIZER-MODEL-GENERATION; O3-NO-OUTPUT; O3-NO-RESULT-SCHEMA; O3-NO-BILLING-COST-PERF
allowed files: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o3_token_telemetry_report.md
forbidden files: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; cluster3/feedback/** except read-only inspection; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pricing/billing files; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers
implemented token behavior: ObservabilityTokenCounts accepts only token_counts_available, prompt_tokens, generated_tokens, total_tokens, token_count_source, and token_count_status; counts are strict non-negative integers; total_tokens consistency is enforced; unavailable token counts cannot carry counts; supplied token counts require a non-unavailable source/status plus one or more explicit count fields; token_count_status=available requires prompt, generated, and total counts; incomplete supplied counts must use token_count_status=partial
redaction behavior: token IDs, input/output IDs, prompt/completion/generated/source/raw text, tokenizer dumps/internal state, hidden prompts, private eval/feedback, tokenizer provenance aliases, and raw model outputs fail closed by key/value checks; safe count/status fields remain allowed
summary behavior: logger derives token_totals from validated event sidecars and rejects summaries whose token_totals do not match the current event stream
runner behavior: Cluster 3 off mode does not resolve token metadata; enabled modes attach unavailable token context by default; enabled modes may attach dependency-injected safe counts; best_effort invalid counts disable sidecars without changing runner outcome; required invalid counts fail before generation/correctness adapters run
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
tests/checks run: shared O0-O3 observability suite passed; Cluster 3 runner suite passed; remaining validation is recorded in audits/observability_sidecar_o3_token_telemetry_report.md after final scans
unresolved risk: real token counts remain unavailable in the local Cluster 3 runner path until a later approved existing count source or run packet supplies them; O3 proves schema, redaction, summary validation, default unavailable behavior, and local fake/injected count wiring only
status: committed at 4ddc7673724a709f8a028b4d52e39b48144b56eb; no Modal/output/generation run authorized or performed
```

### Completed Launch Packet: O4-PREP-ESTIMATED-COST-2026-06-03

```text
launch packet id: O4-PREP-ESTIMATED-COST-2026-06-03
agent role: documentation reconciliation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 4ddc7673724a709f8a028b4d52e39b48144b56eb
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py
package: O4-Prep estimated cost telemetry launch reconciliation
target discovery gate: O4 implementation target surfaces are shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py only if O4 attaches supplied estimated/unavailable cost metadata to O1 sidecar events; their named tests are shared/tests/test_observability_schema.py, shared/tests/test_observability_redaction.py, shared/tests/test_observability_logger.py, shared/tests/test_observability_imports.py, and cluster3/tests/test_run_cluster3_modal_cli.py. Stop with O4_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS if these surfaces become unclear.
requirement ids in scope: O4-PREP-TARGET-SURFACE; O4-PREP-ESTIMATED-COST-FIELDS; O4-PREP-FORBIDDEN-BILLING-PAYLOADS; O4-PREP-NO-RUNTIME-CODE; O4-PREP-NO-BILLING-API; O4-PREP-NO-EXTERNAL-PRICING-FETCH; O4-PREP-NO-ECONOMIC-CLAIMS; O4-PREP-NO-OUTPUT; O4-PREP-NO-ANALYZER; O4-PREP-TEST-PLAN
allowed files for O4-Prep: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md if needed; docs/16_observability_sidecar_implementation_spec.md only for narrow O4 clarification; audits/observability_sidecar_o4_prep_report.md
forbidden files for O4-Prep: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
allowed files for later O4 implementation after O4_PREP_COMPLETE: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/experiments/run_cluster3_modal.py only to pass supplied estimated/unavailable cost metadata into O1 sidecars without changing Modal execution behavior; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o4_estimated_cost_report.md
forbidden files for later O4 implementation: cluster1/**; cluster2/** except read-only inspection; cluster3/results/**; cluster3/feedback/** except read-only inspection; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers; billing/pricing API clients; invoice dumps; pricing snapshot directories unless a later approved O4 amendment explicitly adds them
serialized surfaces: handoff docs and O4 estimated cost telemetry launch naming only
entry gate: clean O3 baseline at 4ddc767; O3 committed; no Modal/output/generation/n=5/n=20/paper-scale approval attached
exit gate: O4 target surfaces, allowed files, forbidden files, estimated/unavailable cost fields, forbidden actual-billing/economic payloads, required tests, stop conditions, and no-execution authorization state are explicit; runtime code untouched; forbidden code-scope diff empty; positive authorization scan empty
allowed estimated-cost fields: cost_estimate_available; estimated_input_cost; estimated_output_cost; estimated_total_cost; currency; pricing_source; pricing_source_version; cost_estimate_status; cost_estimate_method
cost field constraints: values are sidecar-only; monetary values must be non-negative finite numbers; currency is USD unless a later spec amendment adds another currency; estimated_total_cost must equal estimated_input_cost plus estimated_output_cost when both components are present; unavailable estimates cannot carry cost values; pricing_source and pricing_source_version must identify a supplied/static basis only and are not billing evidence
forbidden cost/billing payloads: actual_cost; actual_billing; invoice; account_charge; provider_bill; modal_bill; credit_card; payment_method; billing_account; cost_per_success; cost_per_pass; pass_at_k_cost; ROI; economic_lift; benchmark_cost_conclusion; billing_api_response; pricing_api_response; cloud_invoice_dump
behavior constraints for later O4: no billing API query; no invoice query; no Modal billing query; no provider billing query; no external pricing fetch; no generation run; no model/tokenizer execution; no output mutation; no result-row schema mutation; no analyzer/economic metric changes; no pass@k/cost-per-success/lift/statistical claims; observability remains default-off; omitted/off behavior remains unchanged; cost estimates may be recorded only if supplied by config/test/fake/static table explicitly approved by O4 scope; real actual cost remains O5+ only
required tests after O4-Prep: valid estimated costs accepted; missing cost estimates unavailable-safe; negative/non-finite/string/bool costs rejected; estimated_total_cost consistency enforced; unavailable estimates cannot carry cost values; actual billing/invoice/account charge fields rejected; cost-per-success/pass@k/economic claim fields rejected; billing/pricing API response payloads rejected; no billing/provider/Modal/cloud API imports in shared/observability; off mode unchanged; enabled sidecars can include supplied estimated-cost metadata; invalid estimated cost degrades safely in best_effort; invalid estimated cost fails closed in required mode; no result-row mutation; no outputs mutation; no billing API execution; no generation/model/tokenizer execution
required O4-Prep checks: git diff --check; git status --short --branch; forbidden code-scope diff; positive authorization scan; forbidden O4 scope scan reviewed as prohibitions/caveats/stop conditions only
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on target ambiguity, execution authorization leakage, runtime-code edits during O4-Prep, output mutation, dependency/lockfile changes, MLflow runtime state changes, actual billing/invoice/account-charge capture, billing API or pricing API response capture, external pricing fetch, cost-per-success/pass@k/ROI/economic-lift/benchmark-economics claim, generation/model/tokenizer execution, analyzer/statistical/economic broadening, performance/profiler/timing/speedup/latency/throughput capture, or result-row schema mutation
stop triggers: O4_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS; O4_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK; O4_PREP_BLOCKED_BILLING_CLAIM_LEAK; O4_PREP_BLOCKED_SCOPE_VIOLATION; O4_PREP_BLOCKED_DOC_CONTRADICTION
handoff destination: audits/observability_sidecar_o4_prep_report.md and this state file
state update owner: orchestrator
status: committed at d30aa500df9efb0ee0ce987dbb46317ed1db14d3; AUTHORIZES_EXECUTION: NO
```

### Completed Work Package: O4 Estimated Cost Telemetry Implementation

```text
checkpoint id: O4-ESTIMATED-COST-2026-06-03
agent role: implementation agent
branch: codex/observability-sidecar-core
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: d30aa500df9efb0ee0ce987dbb46317ed1db14d3
package: O4 estimated cost telemetry implementation
scope: supplied estimated or unavailable cost metadata in observability sidecars only
target surfaces: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; cluster3/experiments/run_cluster3_modal.py
test surfaces: shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/tests/test_run_cluster3_modal_cli.py
allowed files touched: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; cluster3/experiments/run_cluster3_modal.py; cluster3/tests/test_run_cluster3_modal_cli.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o4_estimated_cost_report.md
implemented behavior: reconciled ObservabilityCostEstimate to the O4 allowed field set; rejects old draft cost fields; validates non-negative finite USD-only estimates; rejects string/bool/non-finite/negative/coerced cost values; enforces estimated_total_cost consistency; unavailable estimates cannot carry cost/pricing metadata; redaction fails closed on actual billing, invoice, account-charge, provider/Modal bill, billing/pricing response, external pricing fetch, cost-per-success, pass@k cost, ROI, economic-lift, and benchmark-cost conclusion keys; logger derives estimated_cost_summary from validated events; Cluster 3 off mode does not resolve cost metadata; enabled modes attach unavailable cost context by default and can attach dependency-injected safe estimates; best_effort invalid costs degrade sidecars safely; required invalid costs fail before generation/correctness adapters run
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
tests/checks run: shared O0-O4 observability suite passed; Cluster 3 runner suite passed; Cluster 3 schema/import guardrails passed; repair-history/factorial lightweight regressions passed; final scans recorded in audits/observability_sidecar_o4_estimated_cost_report.md
unresolved risk: real estimates remain unavailable until a later approved supplied/config/static pricing source is authorized; actual billing remains O5+ only and no invoice/billing API evidence is produced by O4
status: committed at d4244af33ef22abe652a1c5a1a76694f69469c8e; final O0-O4 acceptance committed at 309c451d2710b376cb29b28c73ef28b7ea940bc6; no Modal/output/generation/billing/pricing/API run authorized or performed
```

### Blocked Work Package: O5C-MODAL-BILLING-COLLECTION-2026-06-04

```text
checkpoint id: O5C-MODAL-BILLING-COLLECTION-2026-06-04
agent role: implementation and collection agent
branch: codex/observability-o5b-reconciliation
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: cf63de80a8fe5a9cd20229657126f12f6a0d306d
package: O5c authorized Modal billing report collection
scope: build a deterministic Modal billing report collection adapter, sanitize Modal billing report JSON into O5b redacted static records, and perform only the explicitly approved Modal billing report query for the UTC window `2026-05-01T00:00:00Z` through exclusive end `2026-06-05T00:00:00Z`
target surfaces: shared/observability/billing_reconciliation.py; shared/observability/billing_modal_collection.py; shared/tests/test_observability_billing_reconciliation.py; shared/tests/test_observability_billing_modal_collection.py; shared/tests/test_observability_imports.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o5c_modal_billing_collection_report.md
implemented behavior: deterministic Modal CLI command construction; official `modal billing report` and `modal.billing.workspace_billing_report` reference verification; hourly query splitting into 7-day chunks for Modal CLI compatibility; fixture-only parser/sanitizer tests; O5b redacted Modal report source mapping to `approved_modal_billing_cli_report`; exclusive-end billing-window overlap semantics; raw Modal object id, description, environment, payment, account, and economic fields omitted from redacted records
authorization used: BILLING_QUERY_AUTHORIZED=YES for the supplied O5c window only; MODAL_BILLING_CLI_AUTHORIZED=YES; CREDENTIAL_USE_AUTHORIZED=YES limited to existing local Modal authentication
collection result: blocked by Modal billing-report limits before any nonempty raw report or redacted report artifact was produced
first attempted command: `.venv/bin/python -m modal billing report --start 2026-05-01 --end 2026-06-05 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json`
first failure: Modal reported hourly billing reports cannot span more than 7 days
second attempted strategy: split the same approved inclusive-start/exclusive-end UTC window into five 7-day-or-less hourly `modal billing report` calls
second failure: Modal reported rate limit exceeded for workspace billing report requests
raw artifacts retained: none
redacted artifacts retained: none
forbidden surfaces preserved: no Modal compute job, generation, GPU job, experiment run, n=5, n=20, paper-scale run, output mutation, result-row schema mutation, analyzer edit, dependency/lockfile change, MLflow runtime state change, raw invoice/payment/private account storage, cost-per-success, pass@k cost, ROI, economic lift, or paper-scale economic conclusion
tests/checks so far: O5c-R review validation passed locally with 59 focused O5b/O5c billing tests, 267 shared observability tests, 265 lightweight non-observability regression tests, clean whitespace checks, clean protected-surface diff, empty artifact-retention scan, and expected-only privacy/economic scan hits
classification: O5C_BLOCKED_MODAL_BILLING_RATE_LIMIT_WITH_ADAPTER_READY
handoff destination: audits/observability_sidecar_o5c_modal_billing_collection_report.md and this state file
```

### Completed Launch Packet: O5B-STATIC-BILLING-RECONCILIATION-2026-06-04

```text
launch packet id: O5B-STATIC-BILLING-RECONCILIATION-2026-06-04
agent role: implementation agent
branch: codex/observability-o5b-reconciliation
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 387edfc38b4ce8cccd6b5c40625f3e51bb106497
package: O5b actual billing reconciliation static/redacted report ingestion
scope: pure local parsing and reconciliation of explicitly redacted/static JSON or JSONL report fixtures into O5a `ObservabilityActualBillingReconciliation` sidecar metadata; dry-run by default; no live billing query, credential use, Modal billing CLI/API, provider billing API, output mutation, runner integration, analyzer/economic metric, result-row schema change, dependency change, or MLflow runtime state
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/16_observability_sidecar_implementation_spec.md; audits/observability_sidecar_o5_prep_report.md; audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md; audits/observability_sidecar_o5a_final_acceptance_report.md; O5a observability schema/redaction/logger files and tests
target surfaces: shared/observability/billing_reconciliation.py; shared/tests/test_observability_billing_reconciliation.py; shared/tests/test_observability_imports.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o5b_reconciliation_report.md
conditional target surfaces if strictness bugs are found: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py
runner target surfaces: none; no cluster runner file is approved for O5b
requirement ids in scope: O5B-STATIC-REPORT-PARSER; O5B-O5A-SCHEMA-VALIDATION; O5B-DRY-RUN-DEFAULT; O5B-EXPLICIT-WRITE-PATH; O5B-LIMITED-ATTRIBUTION; O5B-PRIVATE-BILLING-REJECTION; O5B-NO-BILLING-QUERY; O5B-NO-CREDENTIALS; O5B-NO-RUNNER; O5B-NO-OUTPUT-MUTATION; O5B-NO-ECONOMIC-CLAIMS
implemented behavior target: parse only bounded redacted/static report records; require redacted report hash, USD total cost, safe report source/version, UTC time window, attribution method/confidence, and optional run identifiers; reconcile exact app/run/time-window matches to schema-valid actual-billing metadata; downgrade missing or ambiguous attribution to `attribution_limited` with no actual cost; keep unmatched runs `not_reconciled`; write metadata only when `dry_run=False` and an explicit non-output path is supplied
allowed data sources in O5b tests: tmp_path JSON/JSONL fixtures only
forbidden files: cluster1/**; cluster2/**; cluster3/** except no files currently approved; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers; raw invoice dumps; raw billing reports; raw billing API responses; runtime output artifacts
required tests/checks: focused shared observability tests including `shared/tests/test_observability_billing_reconciliation.py`; non-observability regression bundle; git diff --check; forbidden code-scope diff; billing/API/credential execution scan; economic/performance scan; git status --short --branch
authorization state: AUTHORIZES_EXECUTION: NO for live billing; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_QUERY_AUTHORIZED: NO; CREDENTIAL_USE_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on live billing query, credential use, Modal billing CLI/API reference as executable behavior, provider billing API import/call, raw invoice/API response/workspace report storage, output mutation, runner edit, dependency/lockfile change, MLflow runtime state change, result-row schema mutation, analyzer/economic metric change, cost-per-success/pass@k/ROI/economic-lift/benchmark-economics claim, or performance/profiler/timing/speedup/latency/throughput capture
stop triggers: O5B_BLOCKED_BILLING_EXECUTION_AUTHORIZATION_LEAK; O5B_BLOCKED_PRIVATE_BILLING_PAYLOAD_RISK; O5B_BLOCKED_ECONOMIC_CLAIM_LEAK; O5B_BLOCKED_SCOPE_VIOLATION; O5B_BLOCKED_TEST_REGRESSION
handoff destination: audits/observability_sidecar_o5b_reconciliation_report.md and this state file
state update owner: orchestrator
status: committed at cf63de80a8fe5a9cd20229657126f12f6a0d306d; O5b static ingestion complete; O5c live billing collection now tracked separately and blocked by Modal billing-report rate limit
```

### Completed Launch Packet: O5A-BILLING-RECONCILIATION-SCAFFOLD-2026-06-04

```text
launch packet id: O5A-BILLING-RECONCILIATION-SCAFFOLD-2026-06-04
agent role: implementation agent
branch: codex/observability-o5-prep
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: effd644468e237829849f1c2a0cd3ad028a7f5fa
package: O5a actual billing reconciliation sidecar schema/redaction/logger scaffolding
scope: shared observability schema, redaction, logger, and tests only; no billing query, credentials, Modal billing CLI/API, output mutation, runner integration, analyzer/economic metric, result-row schema change, dependency change, or MLflow runtime state
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; audits/observability_sidecar_o5_prep_report.md; O0-O4 observability implementation files and tests
target surfaces: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md
runner target surfaces: none; no cluster runner file is approved for O5a
requirement ids in scope: O5A-ACTUAL-BILLING-SCHEMA; O5A-ACTUAL-BILLING-REDACTION; O5A-EVENT-DERIVED-SUMMARY; O5A-MOCK-STATIC-ONLY; O5A-NO-BILLING-QUERY; O5A-NO-CREDENTIALS; O5A-NO-RUNNER; O5A-NO-OUTPUT-MUTATION; O5A-NO-ECONOMIC-CLAIMS
implemented behavior: strict `ObservabilityActualBillingReconciliation` validates unavailable/not_reconciled/reconciled status metadata; reconciled actual billing requires bounded source, source version, UTC time window, attribution method/confidence, USD actual_total_cost, and either redacted report hash or query identifier; unreconciled statuses cannot carry cost/source metadata; redaction allowlists only bounded O5 fields while rejecting raw invoice, full billing API response, workspace billing report, payment, credential, secret, cost-per-success, pass@k cost, ROI, economic-lift, benchmark-economics, and paper-scale cost-conclusion payloads; logger derives `actual_billing_summary` only from validated event sidecars and rejects summaries that invent billing facts
allowed data sources in O5a tests: mocked/static unit fixtures only
forbidden files: cluster1/**; cluster2/**; cluster3/**; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers; raw invoice dumps; raw billing reports; raw billing API responses; runtime output artifacts
required tests/checks: focused shared observability tests; Cluster 3 CLI regression tests; git diff --check; forbidden code-scope diff; positive execution authorization scan; O5 privacy/billing/economic scan reviewed as denylist tests or prohibitions only; git status --short --branch
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_QUERY_AUTHORIZED: NO; CREDENTIAL_USE_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on billing query, credential use, Modal billing CLI/API reference as executable behavior, raw invoice/API response storage, output mutation, runner edit, dependency/lockfile change, MLflow runtime state change, result-row schema mutation, analyzer/economic metric change, cost-per-success/pass@k/ROI/economic-lift/benchmark-economics claim, or performance/profiler/timing/speedup/latency/throughput capture
stop triggers: O5A_BLOCKED_BILLING_EXECUTION_AUTHORIZATION_LEAK; O5A_BLOCKED_PRIVATE_BILLING_PAYLOAD_RISK; O5A_BLOCKED_ECONOMIC_CLAIM_LEAK; O5A_BLOCKED_SCOPE_VIOLATION; O5A_BLOCKED_TEST_REGRESSION
handoff destination: audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md and this state file
state update owner: orchestrator
status: committed at 263d317 and final acceptance committed at c41a5bc; O5A_FINAL_ACCEPTANCE_PASS_WITH_CAVEATS; O5 billing execution remains not authorized
```

### Completed Launch Packet: O5-PREP-BILLING-RECONCILIATION-2026-06-04

```text
launch packet id: O5-PREP-BILLING-RECONCILIATION-2026-06-04
agent role: documentation reconciliation agent
branch: codex/observability-o5-prep
worktree: /Users/alexeidelgado/Desktop/TritonGen
baseline commit: 309c451d2710b376cb29b28c73ef28b7ea940bc6
package: O5-Prep actual billing reconciliation launch reconciliation
scope: docs-only target/scope naming before any O5 implementation; no O5 runtime code starts in this package
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/16_observability_sidecar_implementation_spec.md; audits/observability_sidecar_o0_o4_final_acceptance_report.md
target surfaces for later O5 implementation: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/observability/billing_reconciliation.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; shared/tests/test_observability_billing_reconciliation.py
runner target surfaces for later O5 implementation: none by default; any runner-specific integration test or code path requires a later launch-packet amendment naming the exact file before edits
docs/report surfaces for later O5 implementation: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o5_billing_reconciliation_report.md
requirement ids in scope: O5-PREP-TARGET-SURFACE; O5-PREP-ACTUAL-BILLING-FIELDS; O5-PREP-FORBIDDEN-BILLING-PAYLOADS; O5-PREP-NO-RUNTIME-CODE; O5-PREP-NO-BILLING-QUERY; O5-PREP-NO-CREDENTIALS; O5-PREP-NO-OUTPUT-MUTATION; O5-PREP-NO-ECONOMIC-CLAIMS; O5-PREP-NO-ANALYZER; O5-PREP-TEST-PLAN
allowed files for O5-Prep: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md if needed; docs/16_observability_sidecar_implementation_spec.md only for narrow O5 clarification; audits/observability_sidecar_o5_prep_report.md
forbidden files for O5-Prep: shared/observability/**; shared/modal_harness/**; cluster1/**; cluster2/**; cluster3/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; pyproject.toml; requirements*.txt; dependency or lock files
allowed files for later O5 implementation after O5_PREP_COMPLETE: shared/observability/schema.py; shared/observability/redaction.py; shared/observability/logger.py; shared/observability/billing_reconciliation.py; shared/tests/test_observability_schema.py; shared/tests/test_observability_redaction.py; shared/tests/test_observability_logger.py; shared/tests/test_observability_imports.py; shared/tests/test_observability_billing_reconciliation.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; optional audits/observability_sidecar_o5_billing_reconciliation_report.md
forbidden files for later O5 implementation unless a new launch-packet amendment explicitly approves them: cluster1/**; cluster2/**; cluster3/**; shared/modal_harness/**; shared/analysis/**; shared/repair_history/**; outputs/**; mlruns/**; dependency or lock files; Modal app/image/function definitions; scientific result-row schemas; analyzers; raw invoice dumps; raw billing reports; raw billing API responses; runtime output artifacts
allowed actual-billing reconciliation fields: actual_billing_available; actual_billing_status; actual_billing_reconciled_at_utc; billing_source; billing_source_version; billing_time_window_start_utc; billing_time_window_end_utc; billing_attribution_method; billing_attribution_confidence; actual_total_cost; actual_currency; billing_query_id; billing_report_redacted_sha256; billing_reconciliation_notes
field constraints: fields are sidecar-only; actual_total_cost requires an approved billing source, time window, attribution method, and redacted report hash or query identifier; actual_currency is USD until a currency policy is approved; historical untagged runs must be attribution_limited or low confidence unless a non-overlapping time window can be proven; report hashes are hashes of redacted/safe summaries, not raw invoice or API payloads
forbidden billing/private/economic payloads: raw invoice dump; full billing API response; unredacted workspace billing report; payment method; credit_card; billing account secret; customer account secret; credentials; api key; Modal identity token; provider API key; private per-user billing data; raw provider bill; cost_per_success; cost_per_pass; pass_at_k_cost; ROI; economic lift; benchmark economics; performance/profiler/timing/speedup claims
behavior constraints for later O5: post-hoc reconciliation only; no synchronous per-row billing claims during generation; no billing query without separate explicit approval; no credential use without separate explicit approval; dry-run first; mocked/static fixtures in unit tests; no raw billing report storage; no output artifact mutation or historical sidecar rewrite unless separately approved; no scientific-row schema mutation; no analyzer/economic metric changes; no cost-per-success/pass@k/ROI/economic-lift/benchmark-economics/paper-scale cost claims; observability remains default-off; omitted/off behavior remains unchanged
future approval packet requirements: billing source; credential scope; workspace/account scope; time window; delay buffer; app tags or attribution keys; target run_id; target experiment_id; whether historical runs are app-tagged; raw report handling policy; redaction policy; output sidecar path; no-output-mutation or explicit mutation authorization; expected cost/credential risk; dry-run command; stop conditions
required tests after O5-Prep: unavailable actual billing status accepted; reconciled billing status requires approved source metadata; actual_total_cost rejected without approved billing source metadata; negative/non-finite/string/bool actual costs rejected; unsupported currency rejected; raw invoice/API response rejected; credentials/secrets/payment fields rejected; untagged historical attribution marked limited; billing report hash accepted only for redacted/safe summaries; no billing/provider/Modal API calls in unit tests; mocked/static billing fixture only; no result-row mutation; no outputs mutation; no economic/scientific claims
required O5-Prep checks: git diff --check; git status --short --branch; forbidden code-scope diff; positive authorization scan; forbidden O5 scope scan reviewed as prohibitions/caveats/stop conditions only
authorization state: AUTHORIZES_EXECUTION: NO; MODAL_AUTHORIZED: NO; GENERATION_AUTHORIZED: NO; GPU_AUTHORIZED: NO; OUTPUT_MUTATION_AUTHORIZED: NO; N5_AUTHORIZED: NO; N20_AUTHORIZED: NO; PAPER_SCALE_AUTHORIZED: NO; BILLING_QUERY_AUTHORIZED: NO; CREDENTIAL_USE_AUTHORIZED: NO; DEPENDENCY_CHANGE_AUTHORIZED: NO
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on target ambiguity, execution authorization leakage, credential/billing query authorization leakage, runtime-code edits during O5-Prep, output mutation, dependency/lockfile changes, MLflow runtime state changes, raw invoice/API response storage, credential/payment/account secret exposure, cost-per-success/pass@k/ROI/economic-lift/benchmark-economics claim, analyzer/statistical/economic broadening, performance/profiler/timing/speedup/latency/throughput capture, or result-row schema mutation
stop triggers: O5_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS; O5_PREP_BLOCKED_BILLING_EXECUTION_AUTHORIZATION_LEAK; O5_PREP_BLOCKED_PRIVATE_BILLING_PAYLOAD_RISK; O5_PREP_BLOCKED_ECONOMIC_CLAIM_LEAK; O5_PREP_BLOCKED_SCOPE_VIOLATION; O5_PREP_BLOCKED_DOC_CONTRADICTION
handoff destination: audits/observability_sidecar_o5_prep_report.md and this state file
state update owner: orchestrator
status: committed at effd644; O5_PREP_COMPLETE; AUTHORIZES_EXECUTION: NO
```

### Reference Launch Packet: A2-C-LOOP-2026-06-02

```text
launch packet id: A2-C-LOOP-2026-06-02
agent role: implementation agent
branch: codex/llm-repair-memory-agentic-transcript-v1
worktree: /private/tmp/tritongen-llm-repair-memory
baseline commit: historical A2 package baseline; promoted trunk commit 4a8460081aa35a647901ea5fa120a76e0f7ef0e7
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/18_agentic_transcript_v1_implementation_spec.md; audits/agentic_transcript_v1_a1_prompt_core_report.md
package: A2 C-loop integration
requirement ids in scope: A2-C-DEFAULT-INVARIANCE; A2-C-OPT-IN-AGENTIC; A2-C-F2-ONLY; A2-C-FAIL-CLOSED-CONFIG; A2-C-METADATA; A2-C-NO-RUN
allowed files: cluster2/feedback/prompts.py; cluster2/feedback/repair_loop.py; cluster2/feedback/trace.py; cluster2/experiments/run_cluster2_modal.py; cluster2/results/dataclass.py; cluster2/tests/test_feedback_prompts.py; cluster2/tests/test_repair_loop.py; cluster2/tests/test_results_logger.py; cluster2/tests/test_run_cluster2_modal.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/agentic_transcript_v1_a2_c_loop_integration_report.md
forbidden files: cluster1/**; cluster3/**; shared/analysis/**; outputs/**; raw artifacts; analyzers; dependency or lock files; prompt-core files unless a blocking A1 bug is separately scoped
serialized surfaces: C-loop repair policy integration; Cluster 2 runner policy plumbing
entry gate: historical A2 entry gate was A1 prompt core complete and preserved plus C-loop and Cluster 2 runner leases; current promoted trunk is 4a84600
exit gate: A2 checkpoint report records files changed, tests/checks run, default-invariance proof, forbidden-files check, no Modal/output mutation, unresolved risks, and next blocked package or gate
required tests/checks: focused Cluster 2 prompt/repair-loop/runner/result tests touched by implementation; A1 shared prompt-core suite; Cluster 2 boundary tests; git diff --name-only; forbidden implementation diff check; git diff --check; git status --short --branch
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: A2 C-loop integration only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: invalid policy; invalid max_prompt_chars; invalid include_latest_source; ineligible C path; no hidden fallback on explicit agentic render failure
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on any need for Modal, generation, n=5, n=20, paper-scale, output mutation, schema/analyzer changes outside A2, dependency/network access, private-eval leakage, hidden fallback, default drift, or branch scope expansion
stop triggers: implementation stop triggers from docs/18_agentic_transcript_v1_implementation_spec.md plus orchestration escalation thresholds
handoff destination: A2 checkpoint report and this state file
state update owner: orchestrator
status: promoted into A6 handoff trunk at 4a84600; reference/history only
```

### Reference Launch Packet: A3-P-LOOP-2026-06-02

```text
launch packet id: A3-P-LOOP-2026-06-02
agent role: implementation agent
branch: codex/llm-repair-memory-agentic-transcript-v1
worktree: /private/tmp/tritongen-llm-repair-memory
baseline commit: historical A3 package baseline; promoted trunk commit 4a8460081aa35a647901ea5fa120a76e0f7ef0e7
required read set: docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; docs/handoff/agentic_document_hub.md; docs/18_agentic_transcript_v1_implementation_spec.md; audits/agentic_transcript_v1_a1_prompt_core_report.md; audits/agentic_transcript_v1_a2_c_loop_integration_report.md
package: A3 P-loop integration
requirement ids in scope: A3-P-DEFAULT-INVARIANCE; A3-P-OPT-IN-AGENTIC; A3-P-F1-COMPILE-ONLY; A3-P-F1-RUNTIME-TERMINAL; A3-P-FAIL-CLOSED-CONFIG; A3-P-METADATA; A3-P-NO-C-LEAKAGE; A3-P-NO-RUN
allowed files: cluster3/feedback/prompts.py; cluster3/feedback/compile_error_repair.py; cluster3/feedback/trace.py; cluster3/experiments/run_cluster3_modal.py; cluster3/results/dataclass.py; cluster3/tests/test_p_prompts.py; cluster3/tests/test_p_repair_loop.py; cluster3/tests/test_cluster3_schema.py; cluster3/tests/test_run_cluster3_modal_cli.py; cluster3/tests/test_cluster3_imports.py; docs/handoff/experiment_change_orchestration_state.md; docs/handoff/document_version_registry.md; audits/agentic_transcript_v1_a3_p_loop_integration_report.md
forbidden files: cluster1/**; cluster2/feedback/**; cluster2/results/**; cluster2/experiments/**; shared/analysis/**; outputs/**; raw artifacts; analyzers; dependency or lock files; prompt-core files unless a blocking A1 bug is separately scoped
serialized surfaces: P-loop repair policy integration; Cluster 3 runner/schema policy plumbing
entry gate: historical A3 entry gate was A1 prompt core complete, A2 committed, and P-loop / Cluster 3 runner-schema leases; current promoted trunk is 4a84600
exit gate: A3 checkpoint report records files changed, tests/checks run, default-invariance proof, forbidden-files check, no Modal/output/generation mutation, unresolved risks, and next blocked package or gate
required tests/checks: focused Cluster 3 prompt/repair-loop/runner/schema tests touched by implementation; A1 shared prompt-core suite; A2 focused Cluster 2 suite; Cluster 3 import tests; import smoke; git diff --name-only; forbidden implementation diff check; git diff --check; git status --short --branch
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes before promotion
commit/package slice: A3 P-loop integration only
rollback independence proof required: yes
opportunistic cleanup included: no
negative tests required: invalid policy; invalid max_prompt_chars; invalid include_latest_source; ineligible P path; F1_RUNTIME terminal; no C correctness transcript in P prompt; no hidden fallback on explicit agentic render failure
dependency/lockfile changes allowed: no
network/dependency-download/API calls allowed: no
secrets/credentials access allowed: no
Modal/output mutation allowed: no
escalation thresholds: stop on any need for Modal, generation, n=5, n=20, paper-scale, output mutation, schema/analyzer changes outside A3, dependency/network access, private-eval/C correctness/P-to-C leakage, hidden fallback, default drift, or branch scope expansion
stop triggers: implementation stop triggers from docs/18_agentic_transcript_v1_implementation_spec.md plus orchestration escalation thresholds
handoff destination: A3 checkpoint report and this state file
state update owner: orchestrator
status: promoted into A6 handoff trunk at 4a84600; reference/history only
```

### Package Backlog

| Package | Suggested branch | Status | Entry gate | Exit gate | Notes |
|---|---|---|---|---|---|
| L2 n=20 runtime-gate enablement | `codex/l2-n20-runtime-gate-enable` then `codex-track-handoff-context` | promoted/audit closeout | promoted final authorization `bd84940` plus promotion audit `2102259` | L2_N20_RUNTIME_GATE_PROMOTION_COMPLETE_EXECUTION_PRECHECK_READY | Narrow code/test branch to allow only the exact signed L2 n=20 token/profile/path through pre-launch authorization while preserving fail-closed behavior for unsigned, wrong-token, wrong-n, L1a/L1b token reuse, non-elementwise, non-fp32, MLflow-enabled, non-agentic repair history, retry/resume, existing target path, row/cell mismatch, namespace mismatch, L3, profiler, benchmark, speedup/performance paths, and all other variants. Promoted commit is `426ede8`; implementation audit is `audits/l2_n20_runtime_gate_enable_report.md`; promotion audit is `audits/l2_n20_runtime_gate_enable_promotion_audit_report.md`. No L2 execution occurred during promotion. |
| L2 n=20 final authorization packet | `codex/l2-n20-final-authorization` then `codex-track-handoff-context` | promoted/audit closeout | `182db35 Review L2 n20 final signature readiness` | L2_N20_FINAL_AUTHORIZATION_PROMOTION_COMPLETE | Updates `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md` to v1.0.0 signed status, adds `audits/l2_n20_final_authorization_report.md`, signs `AUTHORIZES_EXECUTION: YES_L2_N20_ONLY`, records exact commands, 12 cells, 240 rows, signed stop/spend limits, L2 namespaces, post-run validation authorization, post-run billing reconciliation authorization, no retry/no resume, and forbidden scope. Promoted commit is `bd84940`; promotion audit is `audits/l2_n20_final_authorization_promotion_audit_report.md`. No L2 execution, Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, runtime code change, dependency/lockfile, preliminary-report refresh, profiler, benchmark, speedup, cost-per-success, paper conclusion, or MLflow runtime work occurred. Runtime L2 remains fail-closed until the narrow runtime-gate branch verifies or enables only this signed profile. |
| L2 n=20 selector/profile support | `codex/l2-n20-selector-profile-support` then `codex-track-handoff-context` | promoted/audit closeout | `3a21002 Audit L2 n20 packet draft promotion` | L2_N20_SELECTOR_PROFILE_SUPPORT_PROMOTION_COMPLETE | Adds local-only L2 selector/profile support for `grammar_mode_cp_12cell`, `scale_tier=paper`, `n=20`, 12 cells, 240 planned rows, signed-L2 command surfaces, packet update, and `audits/l2_n20_selector_profile_support_report.md`. Promoted support commit is `27493c0`; promotion audit is `audits/l2_n20_selector_profile_support_promotion_audit_report.md`. The L2 runtime profile remains disabled and `AUTHORIZES_EXECUTION: NO`; no Modal/GPU/generation/billing/output/artifact/mlruns mutation is authorized. |
| L2 n=20 final signature-readiness audit | `codex-track-handoff-context` | audit complete / no execution | `48efad7 Audit L2 n20 selector profile support promotion` | L2_N20_SELECTOR_SUPPORT_PROMOTED_SIGNATURE_READY | Adds `audits/l2_n20_final_signature_readiness_report.md`, confirming the unsigned packet path exists, exact source-backed L2 n=20 command surfaces exist, 12 cells and 240 planned rows are recorded, proposed stop/spend limits and L2 namespaces are present, the billing UTC-window caveat is carried forward, post-run validation and analyzer/report audit requirements are present, no retry/no resume policy is present, and runtime execution remains disabled until a later final signature explicitly enables it. |
| L2 n=20 authorization packet draft | `codex/l2-n20-authorization-packet` | promoted/reference | `134bcf9 Audit L1b n5 completion and analyzer boundary` | L2_N20_PACKET_DRAFT_PROMOTION_COMPLETE_SELECTOR_SUPPORT_REQUIRED | Adds `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md` and `audits/l2_n20_authorization_packet_draft_report.md`; fast-forward promoted into `codex-track-handoff-context` at `4ae7081` and promotion-audited at `3a21002`. The original command-surface blocker is now being addressed by the selector/profile support branch. |
| S0 docs terminology | `codex/structural-task-s0-terminology` | accepted | G1 | G2 | Docs-only structural/task terminology gate closed. S0 accepted the existing vocabulary, confirmed `docs/17_structural_task_analyzer_metadata_implementation_spec.md` as the executable implementation contract, and added `audits/structural_task_s0_terminology_acceptance_report.md`. |
| O-spec observability sidecar implementation spec | none | complete / tightened | G1 | spec routed | `docs/16_observability_sidecar_implementation_spec.md` v0.2.3. |
| S-spec structural/task analyzer metadata implementation spec | none | complete / extended for S4 planning | G1 | spec routed | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.4 records S0-S4. S1/S2/S3 are promoted; S4 is docs/planning-only future packet guidance and does not start analyzer/report/output work. |
| A-spec agentic transcript implementation spec | none | complete | G1 | spec routed | `docs/18_agentic_transcript_v1_implementation_spec.md` v0.1.5; A0-A6 are promoted into the A6 handoff trunk at `4a84600`; the repair-memory branch is reference/history. |
| O0 sidecar core | `codex/observability-sidecar-core` | committed | G1 plus O-spec | G3 partial | Pure `shared/observability/*` schema/logger/path/redaction core and focused tests only; commit `bcdaede`; no runner/result-row/analyzer/output/Modal/billing/MLflow-runtime/dependency changes. |
| A0 policy constants | `codex/llm-repair-memory-agentic-transcript-v1` | complete | G1 plus A-spec | no behavior change | Commit `1e3f44468c5ae91e6467b42b7f93a068fa6acf5f`; policy-name constants and default-invariance tests only. |
| A0.5 preflight | `codex/llm-repair-memory-agentic-transcript-v1` | complete | A0 complete | A1 entry readiness | `audits/agentic_transcript_v1_a0_5_preflight_report.md` v1.0.0; default invariance, cheap imports, focused tests, and no forbidden-surface changes verified. |
| A1 prompt core | `codex/llm-repair-memory-agentic-transcript-v1` | complete with baseline-venv caveat | A0.5 complete plus A-spec | G5 satisfied | Pure attempt evidence, anchor selector, transcript renderer, fixture-first golden tests, fixture acceptance manifest, legacy byte-invariance snapshots, prompt-core import isolation, and A1 review checkpoint are recorded in `audits/agentic_transcript_v1_a1_prompt_core_report.md`. |
| S1 analyzer metadata | `codex/analyzer-metric-registry` | review passed / commit closeout | G2 plus S-spec plus closed `analyzer_metric_registry` lease | G4 satisfied for S1 | G2 and S-spec are satisfied. S1 added analyzer outcome-family metadata, metric registry, registry provenance, diagnostics, row annotations, JSON-safe output guards, compatibility tests, validator tests, diagnostic tests, and `audits/structural_task_s1_analyzer_metric_registry_report.md`. Review tightened the validator so reportable metrics marked `not_computed` fail closed. S1 still forbids `outputs/` mutation, report-builder refresh, generation, Modal/GPU runs, dependency or lockfile edits, and result-row schema changes. |
| O1 Cluster 3 local runner instrumentation | `codex/observability-sidecar-core` | committed | O0 plus runner lease | G3 partial | First runner is explicitly `cluster3/experiments/run_cluster3_modal.py`; primary tests are `cluster3/tests/test_run_cluster3_modal_cli.py`; commit `8eaef2e` adds default-off `off|best_effort|required` sidecars with tmp_path tests and no Modal/output/generation authorization. |
| O2-Prep Modal runtime context launch reconciliation | `codex/observability-sidecar-core` | committed | O1 committed | O2 prep complete | Docs-only target/scope naming before O2 implementation; committed at `74b3acd`; O2 target surfaces are `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/modal_harness/runtime.py`, and `cluster3/experiments/run_cluster3_modal.py` for optional safe Modal context sidecar enrichment only. |
| O2 Modal runtime context implementation | `codex/observability-sidecar-core` | committed | O2_PREP_COMPLETE | G3 partial | Commit `6f3001e` adds optional safe Modal context sidecar enrichment for Cluster 3 only; local fake/context tests pass; real remote context remains unproven until a later approved execution packet; no Modal/output/generation/billing/cost/performance/result-row mutation authorized. |
| O3-Prep token telemetry launch reconciliation | `codex/observability-sidecar-core` | committed | O2 committed | O3 prep complete | Commit `c93bdc0` names later O3 target surfaces as `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, `cluster3/experiments/run_cluster3_modal.py`, and their focused tests; O3 token telemetry is counts/status only. |
| O3 token telemetry implementation | `codex/observability-sidecar-core` | committed | O3_PREP_COMPLETE | G3 partial | Commit `4ddc767` adds count/status-only token schema, fail-closed token/raw/private payload rejection, event-derived summary `token_totals`, and Cluster 3 injected-count/unavailable-safe sidecar wiring; no tokenizer/model/generation execution, output mutation, result-row schema mutation, billing/cost, or performance telemetry. |
| O4-Prep estimated cost telemetry launch reconciliation | `codex/observability-sidecar-core` | committed | O3 committed | O4 prep complete | Commit `d30aa50` names later O4 target surfaces as `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `cluster3/experiments/run_cluster3_modal.py` only for supplied estimated/unavailable sidecar cost metadata; no runtime code, actual billing, invoices, external pricing fetch, cost-per-success, pass@k cost, ROI, economic-lift, benchmark economics, output mutation, analyzer change, dependency change, or result-row schema mutation. |
| O4 estimated cost telemetry implementation | `codex/observability-sidecar-core` | committed | O4_PREP_COMPLETE | G3 partial | Commit `d4244af` reconciles `ObservabilityCostEstimate` to the O4 allowed field set, adds fail-closed cost/billing/economic redaction, validates event-derived `estimated_cost_summary`, and wires Cluster 3 dependency-injected supplied/unavailable cost sidecars only; no actual billing, invoice, external pricing fetch, output mutation, result-row schema mutation, analyzer/economic metric change, dependency change, or performance telemetry. |
| O0-O4 final acceptance | `codex/observability-sidecar-core` then `codex-track-handoff-context` | committed/promoted | O4 committed | O0-O4 package accepted with caveats | Commit `309c451` records final acceptance and promotes O0-O4 observability into the handoff trunk. O5 was not started. |
| O5-Prep actual billing reconciliation launch reconciliation | `codex/observability-o5-prep` | committed | O0-O4 promoted | O5_PREP_COMPLETE | Commit `effd644` names future O5 target surfaces, allowed sidecar-only actual-billing reconciliation fields, forbidden billing/private/economic payloads, approval packet requirements, tests, and stop conditions. No runtime code, billing query, credential use, Modal/output/generation, analyzer/economic metric, dependency/lockfile, result-row schema, or historical sidecar/output mutation is authorized. |
| O5a actual billing reconciliation scaffolding | `codex/observability-o5-prep` | accepted with caveats | O5_PREP_COMPLETE | O5a acceptance complete | Commit `263d317` adds shared observability schema/redaction/logger scaffolding for mocked/static actual-billing reconciliation metadata only, and commit `c41a5bc` records `O5A_FINAL_ACCEPTANCE_PASS_WITH_CAVEATS`. No runner integration, billing query, credential use, Modal billing CLI/API invocation, output mutation, result-row schema mutation, analyzer/economic metric, dependency/lockfile, or MLflow runtime change is authorized. |
| O5b static/redacted billing reconciliation ingestion | `codex/observability-o5b-reconciliation` | committed | O5A_FINAL_ACCEPTANCE_PASS_WITH_CAVEATS | O5b complete | Commit `cf63de8` adds pure local JSON/JSONL static-redacted report ingestion, O5a schema validation, dry-run default, explicit non-output metadata write path, and attribution-limited handling. No output mutation, result-row schema mutation, analyzer/economic metric, dependency/lockfile, MLflow runtime state, generation, or O6 work is included. |
| O5c Modal billing report collection | `codex/observability-o5b-reconciliation` | committed / adapter-ready blocked | O5b committed plus explicit O5c billing-query packet | O5C_REVIEW_PASS_COMMIT_ADAPTER_READY_BLOCKED | Commit `dc48782` adds deterministic Modal billing CLI adapter and redacted O5b sanitizer tests, then records the approved `2026-05-01T00:00:00Z` to exclusive-end `2026-06-05T00:00:00Z` hourly report attempt. Modal rejected the full query for the 7-day hourly limit and rejected the chunked strategy with a workspace billing report rate limit. No nonempty raw/redacted billing artifact was retained, no output/result-row/analyzer mutation occurred, and no economic/scientific claim is authorized. |
| O6a Level-4 performance contract scaffolding | `codex/observability-o6-performance-contract` | committed | O5c adapter-ready blocked baseline `dc48782` | O6A_PERFORMANCE_CONTRACT_COMPLETE_WITH_CAVEATS | Commit `d966ad0` adds metadata-only performance contract schema/helper/redaction/tests/docs for future O6b benchmark execution. No Modal/GPU/generation/profiler/benchmark/timing execution occurred in O6a. |
| O6b Modal GPU performance smoke | `codex/observability-o6-performance-contract` | committed / promotion-ready | O6a committed plus signed O6b run packet | O6B_PERFORMANCE_SMOKE_COMPLETE_WITH_CAVEATS | Commit `403cfea` adds dedicated performance sidecar schema/writer, pure timing-summary harness helpers, opt-in Modal smoke entrypoint, and one signed T4 CUDA-event smoke result at `artifacts/observability_performance/o6b_smoke_relu_performance.jsonl` with speedup `0.6657483682345889`. Final O5b/O5c/O6a/O6b promotion audit passed with caveats; no outputs/result rows/analyzers/generation/profiler/Nsight/NCU/dependency/lockfile/MLflow runtime mutation is authorized. |
| A2 C-loop integration | `codex/llm-repair-memory-agentic-transcript-v1` | promoted/reference | A1 | G6 partial | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a2_c_loop_integration_report.md` v1.0.0 records default `last_attempt_only_v1` preserved, `agentic_transcript_v1` opt-in, and no Modal/output mutation. |
| A3 P-loop integration | `codex/llm-repair-memory-agentic-transcript-v1` | promoted/reference | A1/A2 | G6 partial | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a3_p_loop_integration_report.md` v1.0.0 records default `last_attempt_only_v1` preserved, `agentic_transcript_v1` opt-in, F1_COMPILE-only P eligibility preserved, and no Modal/output/generation mutation. |
| A4 P-to-C isolation | `codex/llm-repair-memory-agentic-transcript-v1` | promoted/reference | A2/A3 complete | G6 partial | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md` v1.0.0 remains the isolation evidence snapshot. |
| A5 analyzer grouping/quarantine | `codex/llm-repair-memory-agentic-transcript-v1` | promoted/reference | A2/A3/A4 complete | G6 partial | Promoted into A6 handoff trunk at `4a84600`; `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md` v1.0.0 remains the analyzer grouping/quarantine evidence snapshot. |
| A6 run-packet gate planning | `codex/llm-repair-memory-agentic-transcript-v1` | promoted/reference | A2/A3/A4/A5 complete | G7 remains blocked pending signed packet | Promoted into handoff trunk at `4a84600`; `docs/handoff/agentic_transcript_v1_run_packet_template.md` v1.0.0 and `docs/handoff/agentic_transcript_v1_next_run_packet.md` v0.1.0 define the future approval packet; the draft is `DRAFT_NOT_APPROVED`, all execution flags are `NO`, and no Modal/output/generation/n=5/n=20/paper-scale mutation occurred. |
| S2 report builder/dashboard consumption | `codex/structural-task-s2-report-consumption` | committed/reference | S1 review/commit plus active `report_data_builder` lease | S2 review pass | Consumes accepted S1 metadata when present, emits `legacy_metadata_unavailable` fallback when current analyzer JSON lacks S1 metadata, separates structural/code-surface, task/functional, mixed diagnostic, and future benchmarkable/performance groups, preserves planned-deferred/future-only statuses without current computed values, and proves fallback/display-string safety with focused temp-fixture tests. Ignored dashboard preview files were reviewed for localization parity but excluded from the code/docs-only commit; source-controlled bilingual dashboard publication remains deferred unless force-add is separately approved. S2 did not refresh analyzer output, rewrite raw JSONL, run experiments, mutate `outputs/` or `artifacts/`, alter analyzer semantics, or change result schemas/dependencies/lockfiles. |
| S3 structural/task report output refresh | `codex/structural-task-s3-report-refresh` then `codex-track-handoff-context` | committed/promoted | S2 committed plus approved S3 report-derived output refresh packet | STRUCTURAL_TASK_S0_S3_PROMOTION_COMPLETE | Ran the existing local preliminary-report builder using `.venv/bin/python`, refreshed ignored local `_report_data.json` plus English/Spanish embedded report data, verified `legacy_metadata_unavailable` fallback and separated structural/task/mixed/future groups, added `audits/structural_task_s3_report_refresh_report.md`, committed S3 as `f1058eb`, and fast-forwarded S0-S3 into `codex-track-handoff-context`. Ignored previews remain uncommitted. No analyzer output rerun, raw JSONL rewrite, experiment run, `outputs/` tracked mutation, `artifacts/`, analyzer semantic change, result schema, dependency, lockfile, Modal/GPU/generation, n=5, n=20, paper-scale, profiler, timing, speedup, or benchmark work occurred. |
| S4 future experiment integration | `codex/structural-task-s4-experiment-integration` then `codex-track-handoff-context` | promoted/closed | S0-S3 promoted plus pushed handoff baseline `80086f9` | S4_REVIEW_PASS_PROMOTION_COMPLETE | Future experiment packet guidance now declares primary task/functional metrics, secondary structural/code-surface metrics, mixed diagnostics, `planned_deferred` metrics, `future_only` metrics, benchmarkable/performance metrics, metric gates, denominators, evidence sources, and claim boundaries. S4 validation passed with forbidden-scope, execution authorization, claim-boundary, ignored-preview, and optional local smoke tests clean. S4 did not refresh analyzer outputs, rewrite raw JSONL, run experiments, mutate report artifacts, change analyzer/report-builder code, or authorize paper-scale/performance claims. |
| R2 Phase 14b run | `codex/cluster3-phase14b-c-plus-p-n5` | complete | G7 plus approval | registered diagnostic artifact | Completed elsewhere; insufficient repair signal. |
| R3 Phase 14c run | `codex/cluster3-phase14c-g-plus-c-plus-p-n5` | complete | G7 plus approval | registered diagnostic artifact | Completed elsewhere; insufficient repair signal. |
| R4 Phase 14d G+P reuse decision | `codex/cluster3-phase14d-gp-reuse` | complete | Phase 14c audit | reuse decision registered | Existing Phase 12 G+P n=5 artifact reused as matrix cell. |
| R5 Phase 14e matrix freeze | `codex/cluster3-phase14e-freeze` | complete | four cells present | matrix frozen with warnings | Development-scale condition coverage only; no P/C repair signal. |
| L1b n=5 completion and analyzer boundary audit | `codex-track-handoff-context` | audit complete / pushed-ready | pushed L1b commits `a52d64a` and `387c073` | L1B_N5_AUDIT_PASS_L2_READY | Adds `audits/l1b_n5_completion_and_analyzer_boundary_audit.md`, confirming the pushed L1b 12-cell n=5 package has 60 rows, 12 cells, 5 rows per cell, valid content-hash and observability sidecars, preserved non-paper analyzer/report boundaries, narrow dev-scope pair-skip behavior, UTC-window-only empty-tag billing caveat, and no output/artifact/mlruns mutation during audit. Next allowed step is a separate L2 n=20 authorization packet draft/review, not execution. |
| L1a final signature packet preparation | `codex/l1a-final-signature-packet` | active/docs-only | `c05e111` executable selector support promotion audit baseline | L1A_FINAL_SIGNATURE_PACKET_COMPLETE | Prepares the unsigned final signature packet target at `c05e111`, records promoted selector commit `e9f180a`, preserves 12-cell command/path/grammar/model/seed/validation surfaces, keeps `AUTHORIZES_EXECUTION: NO`, keeps signature status `UNSIGNED`, keeps stop/spend limits `PROPOSED_NOT_SIGNED`, keeps the preflight estimate `NOT_SIGNABLE`, and records remaining blockers in `audits/l1a_final_signature_packet_report.md`. No Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, dependency, lockfile, benchmark, profiler, n=1 execution, n=5, n=20, paper-scale, or MLflow runtime write is authorized. |
| L1a executable 12-cell selector support | `codex/l1a-executable-12cell-selector-support` then `codex-track-handoff-context` | promoted/audit closeout | `e96f70a` L1a signature-readiness gap closure promotion audit baseline | L1A_EXECUTABLE_12CELL_SELECTOR_SUPPORT_PROMOTION_COMPLETE | Adds local `--execution-plan` command construction for the 12-cell `grammar_mode x C x P` selector, including all no-P controls, deterministic target paths, grammar-mode command mapping, signed-authorization placeholder, fail-if-existing policy metadata, focused tests, packet update, and `audits/l1a_executable_12cell_selector_support_report.md`. Promoted selector-support commit is `e9f180a`; promotion audit is `audits/l1a_executable_12cell_selector_support_promotion_audit_report.md`. Actual runtime selector execution remains fail-closed before tracking, generation, Modal, output writers, observability writers, or MLflow runtime setup. No Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, dependency, lockfile, benchmark, profiler, n=1 execution, n=5, n=20, paper-scale, or MLflow runtime write is authorized. |
| L1a signature-readiness gap closure | `codex/l1a-signature-readiness-gap-closure` then `codex-track-handoff-context` | promoted/audit complete | `59fa0d6` L1a approval packet promotion audit baseline | L1A_SIGNATURE_READINESS_GAP_CLOSURE_PROMOTION_COMPLETE | Updates and promotes the unsigned L1a packet from v0.5.0 to v0.5.1 to close source-backed signature-readiness gaps while preserving `AUTHORIZES_EXECUTION: NO`: target commit freshness, deterministic observability run-id convention, Modal app/source-image identity, synthetic `NOT_SIGNABLE` estimator placeholder, proposed unsigned stop/spend limits, plan-only billing reconciliation, and exact validation command surfaces. Promoted gap-closure commit is `616ae01`; promotion audit is `audits/l1a_signature_readiness_gap_closure_promotion_audit_report.md`. Its executable-command blocker is superseded by promoted executable selector support at `e9f180a`; no Modal/GPU/generation, billing query, output/artifact/mlruns mutation, analyzer/report refresh, dependency, lockfile, benchmark, profiler, n=1, n=5, n=20, paper-scale, or MLflow runtime write is authorized. |
| L1a final approval packet completion | `codex/l1a-final-approval-packet` then `codex-track-handoff-context` | promoted/audit closeout | `c256af5` Modal preflight estimator promotion baseline | L1A_FINAL_APPROVAL_PACKET_PROMOTION_COMPLETE | Completes and promotes the exact unsigned signable packet surface for future L1a n=1 human review/signature, recording target branch/commit, 12-cell matrix, dry-plan verification command, output/content-hash/observability path templates, grammar hashes, model/seed policy, preflight requirement, stop/spend placeholders, validation placeholders, and signature block. Promoted packet commit is `e348c2c`; promotion audit is `audits/l1a_final_approval_packet_promotion_audit_report.md`. It remains `AUTHORIZES_EXECUTION: NO`; no execution, Modal/GPU/generation, experiment run, output/artifact/mlruns mutation, analyzer/report refresh, dependency, lockfile, n=1 execution, n=5, n=20, paper-scale work, benchmark, billing query, or MLflow runtime write is authorized. |
| Modal preflight cost/time estimator | `codex/modal-preflight-cost-time-estimator` then `codex-track-handoff-context` | promoted/reference | `76310b5` sidecar stage timing promotion audit baseline | MODAL_PREFLIGHT_COST_TIME_ESTIMATOR_PROMOTION_COMPLETE | Adds a pure local advisory estimator for L1a/L1b/L2 row counts, execution-shape comparisons, caller-supplied cost/time inputs, warning flags, and larger-GPU breakeven planning. Promoted estimator commit is `bd89e67`; promotion audit is `c256af5`. It requires no Modal import, no billing query, no network, and no output/artifact/mlruns writes. No execution, Modal/GPU/generation, experiment run, analyzer/report refresh, dependency, lockfile, n=1 execution, n=5, n=20, paper-scale work, benchmark, billing query, or MLflow runtime write is authorized. |
| Sidecar-only stage timing pre-L1a | `codex/sidecar-stage-timing-pre-l1a` then `codex-track-handoff-context` | promoted/audit complete | `6160c88` Modal optimization intake baseline | SIDECAR_STAGE_TIMING_PROMOTION_COMPLETE | Adds additive observability sidecar stage events for generation, correctness evaluation, P repair, C repair, and row append in `cluster3/experiments/run_cluster3_modal.py`, with focused local tests and `audits/sidecar_stage_timing_pre_l1a_report.md`. Fast-forward promoted commit is `ef41890`; promotion audit is `audits/sidecar_stage_timing_promotion_audit_report.md`. Scientific rows remain unchanged and L1a remains unsigned. No Modal/GPU/generation, experiment run, output/artifact/mlruns mutation, analyzer output refresh, report artifact refresh, dependency, lockfile, benchmark, billing query, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| Modal optimization intake review | `codex/modal-optimization-intake-review` then `codex-track-handoff-context` | committed/promoted local reference | `76ede6a` launcher support promotion audit baseline | MODAL_OPTIMIZATION_INTAKE_REVIEW_COMMITTED_AND_PROMOTED_LOCAL | Reviews parked `docs/19_modal_full_factorial_optimization_plan.md`, confirms no tracked dirty sidecar timing patch is present, records non-execution classification in `audits/modal_optimization_intake_review_report.md`, and updates handoff routing. Local promoted commit is `6160c88`. No Modal/GPU/generation, experiment run, output/artifact/mlruns mutation, analyzer output refresh, report artifact refresh, dependency, lockfile, benchmark, billing query, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| Grammar-mode 12-cell launcher support | `codex/grammar-mode-12cell-launcher-support` then `codex-track-handoff-context` | promoted/reference | `0d1e8e3` L1a packet completion promotion audit baseline | GRAMMAR_MODE_12CELL_LAUNCHER_SUPPORT_PROMOTION_COMPLETE | Adds dry-plan-only selector `grammar_mode_cp_12cell`, all 12 L1a cells including six no-P controls, deterministic output/content-hash/observability path planning, grammar hash locks, no-overwrite policy metadata, fail-closed execution validation, L1a packet wording updates, focused tests, and `audits/grammar_mode_12cell_launcher_support_report.md`. Promoted support commit is `e914557`; promotion audit is `76ede6a`. No Modal/GPU/generation, experiment run, output/artifact/mlruns mutation, analyzer output refresh, report artifact refresh, dependency, lockfile, benchmark, billing query, profiler, MLflow runtime write, n=1 execution, n=5, n=20, or paper-scale work is authorized. |
| L1a authorization packet completion | `codex/l1a-authorization-packet-completion` then `codex-track-handoff-context` | promoted/audit complete | locally promoted baseline-pin commit `d172e02` | L1A_AUTHORIZATION_PACKET_COMPLETION_PROMOTION_COMPLETE | Completes and promotes the unsigned L1a n=1 authorization packet for review/user signature only, with target commit, grammar hashes, output and sidecar path templates, model/revision, seed/decoding policy, and review-only command manifest. `audits/l1a_authorization_packet_completion_promotion_audit_report.md` records the promotion review. Its missing no-P launcher-support blocker is superseded by local dry-plan work on `codex/grammar-mode-12cell-launcher-support` pending promotion; execution still remains blocked because no approval is signed and numeric stop/spend limits are not authorized. |
| L1a packet baseline pin | `codex/l1a-packet-baseline-pin` then `codex-track-handoff-context` | promoted/reference | `9aeb3c1` grammar-mode support promotion audit baseline | L1A_PACKET_BASELINE_PIN_PROMOTED | Updates the unsigned L1a n=1 authorization packet so `code_support_commit` points to `c24fbaa`, `planning_baseline_commit` points to `9aeb3c1`, and `0cc43c1` is historical/superseded context only. Adds `audits/l1a_packet_baseline_pin_report.md`, updates handoff routing, and was fast-forward promoted locally into `codex-track-handoff-context` at `d172e02`. L1a remains unsigned and non-executing. |
| Grammar-mode support implementation for Full Pipeline L1a | `codex/grammar-mode-support-implementation` | promoted/reference | `4b0e6da` grammar-mode code-support audit baseline | GRAMMAR_MODE_SUPPORT_PROMOTION_COMPLETE | Adds local `grammar_mode` support for `grammar_off`, `template_upper_bound`, and `task_agnostic`, a 12-cell planning matrix, Cluster 3 row/schema labeling, shared eval row support, analyzer grouping for explicit grammar mode, focused fixtures, promoted launch packet and L1a draft wording updates, and `audits/grammar_mode_support_implementation_report.md`. Promoted support commit is `c24fbaa`; promotion audit is `9aeb3c1`. MLflow grammar-mode indexing is deferred. No execution, output/artifact/mlruns mutation, analyzer output refresh, report artifact refresh, dependency, lockfile, Modal/GPU/generation, n=1, n=5, n=20, paper-scale, profiler, timing, speedup, benchmark, billing query, or MLflow runtime write is authorized. |
| Grammar-mode code-support audit for Full Pipeline L1a | `codex/full-pipeline-l1-smoke-dev-approval-packet` | committed/reference baseline | 12-cell launch-packet patch, unsigned L1a draft, and historical promoted launch packet baseline `0cc43c1` | GRAMMAR_MODE_CODE_SUPPORT_AUDIT_SUPERSEDED_BY_PROMOTED_IMPLEMENTATION | Adds `audits/grammar_mode_code_support_audit_report.md` and updates handoff routing. Found prior code supported binary `grammar_active` plus `grammar_variant` values `template_upper_bound` and `task_agnostic`, but not first-class `grammar_mode`, packet values `primary_grammar`/`task_agnostic_grammar`, per-row grammar-mode labels, analyzer/report grouping by grammar mode, or 12-cell launch expressibility. It is superseded by promoted implementation commit `c24fbaa` and promotion audit `9aeb3c1`. No runtime execution authorization was granted. |
| Full Pipeline Launch Packet v1 12-cell patch and L1a authorization draft | `codex/full-pipeline-l1-smoke-dev-approval-packet` | docs-only patch complete/reference | Phase 14e freeze, C3 n20 metric-family packet, S4 metric-family guidance, O0-O6 observability state, A6 repair-memory gate, MLflow tracking policy, promoted launch packet baseline `0cc43c1`, and later grammar-mode support baseline `c24fbaa`/`9aeb3c1`/`d172e02` | FULL_PIPELINE_LAUNCH_PACKET_12CELL_PATCH_BLOCKED_SIGNATURE | Patches `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md` from the superseded 8-cell plan to the selected 12-cell `grammar_mode x C x P` design, adds `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md` as an unsigned/non-authorizing L1a n=1 draft, adds `audits/full_pipeline_launch_packet_v1_12cell_patch_report.md`, defines fresh `full_pipeline_grammar_mode_cp_factorial_v1` namespaces, and preserves all execution flags as NO. Later promoted launcher and executable selector support address dry-plan selector/no-P representability plus local execution-plan command construction; execution remains blocked by missing user signature, missing signed numeric stop/spend authorization, and other unsigned approval fields. No protected-scope mutation, output/artifact/mlruns mutation, or execution authorization is in scope. |
| Full Pipeline Launch Packet v1 original promotion | `codex/full-pipeline-launch-packet-v1` then `codex-track-handoff-context` | promoted/audit complete; original 8-cell design superseded for future execution | Phase 14e freeze, C3 n20 metric-family packet, S4 metric-family guidance, O0-O6 observability state, A6 repair-memory gate, and MLflow tracking policy | FULL_PIPELINE_LAUNCH_PACKET_V1_PROMOTION_COMPLETE | Created `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`, `audits/full_pipeline_launch_packet_v1_report.md`, and `audits/full_pipeline_launch_packet_v1_promotion_audit_report.md`; selected a future fresh 8-cell plan before the 12-cell patch, recommended L1 smoke/dev before L2 n20, defined MLflow post-hoc indexing and namespace policy, preserved all execution flags as NO, passed review without protected-scope mutation or execution authorization leakage, and was fast-forward promoted into `codex-track-handoff-context` at `5cc6326`. |
| C3 n20 metric-family-gated packet | `codex/c3-n20-metric-family-gated-packet` | committed/reference | Phase 14e freeze plus S4 metric-family guidance | reviewed packet committed into handoff trunk | Creates `docs/experiment_packets/c3_n20_metric_family_gated_packet.md` and `audits/c3_n20_metric_family_gated_packet_report.md`; defines metric-family declarations, denominator/eligibility policy, claim boundaries, sidecar policy, fail-closed rules, and future launch prerequisites only. No Modal/GPU/generation/experiment/output/paper-scale work is authorized. |
| R6 paper-scale readiness or future run spec | `codex/cluster3-paper-readiness-plan` | not started | Phase 14e freeze plus reviewed C3 n20 packet and relevant specs | run/go-no-go packet ready | Spec only; no Modal run without approval. The C3 n20 packet can be used only as a reviewed non-authorizing prerequisite before any future launch approval uses it. |

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
- For A-stream work, keep commits/packages sliced according to the active
  A-spec: docs-only checkpoint, A0 constants, A0.5 validation, A1 prompt core,
  A2 C integration, A3 P integration, A4 isolation, A5 analyzer grouping, and
  A6 run-packet gate planning remain independently reviewable.
- Every package handoff must include changed files, tests/checks run,
  default-invariance proof, forbidden-files check, no Modal/output mutation
  statement, unresolved risks, and the next blocked package or gate.
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
- Do not include opportunistic cleanup unless the cleanup is required by the
  current package and explicitly listed in scope.
- For A-stream work, record rollback independence: later integration packages
  must be revertible without invalidating earlier accepted packages.
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
| S3 report output refresh | Existing report-builder command; derived output path review; metadata-consumption/reportability review; structural/task separation check; legacy fallback check; ignored HTML/data policy decision; claim-boundary scan; audit and registry update. | Never rewrite raw JSONL artifacts or rerun analyzer semantics without a separate signed packet. |
| S4 future experiment integration | Diff-only docs review; metric-family terminology scan over touched docs; forbidden code/output diff scan; execution authorization scan; no-output-refresh proof; audit and registry/state update. | Docs/planning only. Does not authorize Modal, GPU, generation, experiment execution, analyzer output refresh, raw JSONL rewrite, report artifact refresh, paper-scale claims, timing, speedup, profiler, or benchmark work. |
| O0 sidecar core | Schema validation tests; JSONL append round-trip tests; summary writer tests; source/private-eval/raw-feedback exclusion tests. | No runner integration yet. |
| O1 Cluster 3 local runner instrumentation | Targeted `cluster3/tests/test_run_cluster3_modal_cli.py` tests with observability omitted/off/enabled/required; sidecar path/key tests; invalid required-mode preflight keeps generation/correctness/repair/Modal dependencies uncalled; no unauthorized Modal/output mutation check; O0 suite regression. | First runner is fixed to `cluster3/experiments/run_cluster3_modal.py`; stop if target ambiguity appears. |
| O2 Modal identity | Shared Modal runtime helper tests; remote response schema compatibility tests; fixture/backward-compatibility tests with missing optional context; forbidden Modal/secrets/env-field rejection tests; no-`.spawn()` and no-new-Modal-invocation scans; Cluster 3 off-mode unchanged tests. | Target surfaces are `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/modal_harness/runtime.py`, and `cluster3/experiments/run_cluster3_modal.py` only after O2-Prep completes. No new Modal app/image/function, no outputs mutation, no result-row schema change, no billing/cost, and no GPU/performance telemetry. |
| O3 token telemetry | Schema/redaction/logger tests for count/status-only token telemetry; token-ID, prompt/generated/source/raw-text rejection tests; no tokenizer/model import checks for `shared/observability`; Cluster 3 off-mode and enabled fake-count sidecar tests; sidecar join/key tests; row-schema and outputs stability checks. | Target surfaces are `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `cluster3/experiments/run_cluster3_modal.py` only after O3-Prep completes. Token fields stay out of scientific rows; no generation, model call, tokenizer/model import, output mutation, billing/cost, or performance telemetry is authorized. |
| O4 estimated cost | Schema/redaction/logger tests for supplied estimated/unavailable cost metadata; total/component consistency tests; unavailable-safe tests; forbidden actual-billing, invoice, account-charge, cost-per-success, pass@k cost, ROI, economic-lift, billing-response, and pricing-response rejection tests; no billing/provider/Modal/cloud API import checks for `shared/observability`; Cluster 3 off-mode and enabled fake-cost sidecar tests. | Target surfaces are `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `cluster3/experiments/run_cluster3_modal.py` only after O4-Prep completes. Cost fields stay out of scientific rows; no actual billing, invoice, external pricing fetch, generation, model/tokenizer execution, output mutation, analyzer/economic metric change, cost-per-success/pass@k/lift claim, dependency/lockfile change, or performance telemetry is authorized. |
| O5 billing reconciliation | Schema/redaction/logger tests for actual-billing status and bounded actual-cost fields; pure reconciliation helper tests using mocked/static fixtures; dry-run behavior tests; attribution-confidence tests; rejected raw invoice/API response, credential, payment, private-account, unsupported-currency, non-finite/string/bool/negative cost, cost-per-success, pass@k cost, ROI, economic-lift, benchmark-economics, and performance-claim fixtures; import/no-call checks proving unit tests do not invoke billing/provider/Modal APIs. | Target surfaces are `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `shared/observability/billing_reconciliation.py` only after O5-Prep completes. Real billing query, credential use, Modal billing/API/CLI invocation, exported report processing, output mutation, or historical sidecar migration requires a separate explicit approval packet. Actual billing fields stay out of scientific rows; no analyzer/economic metric or paper-scale cost claim is authorized. |
| A0 policy constants | Import/constants tests; default-policy test proving behavior remains `last_attempt_only_v1` or current default. | No prompt behavior change. |
| A1 prompt core | Attempt evidence tests; anchor selector ranking/tie-break tests; golden prompt tests; fixture acceptance manifest validation; legacy C/P byte-invariance snapshots; prompt-core import-isolation scan; prompt-injection guard tests; truncation/fail-closed tests; prompt-hash exactness tests. | No runner behavior change. |
| A2 C-loop integration | Cluster 2 repair-loop tests; F2-only boundary tests; omitted/legacy/agentic/invalid policy flag parsing and default tests; invalid budget and latest-source setting tests; metadata nullability matrix tests; prompt hash and anchor metadata tests; mixed-policy artifact rejection/quarantine tests where applicable. | Requires C-loop and likely Cluster 2 runner leases. |
| A3 P-loop integration | Cluster 3 P-loop tests; F1_COMPILE-only boundary tests; sanitizer leakage tests; omitted/legacy/agentic/invalid policy flag parsing and default tests; invalid budget and latest-source setting tests; metadata nullability matrix tests; prompt hash and anchor metadata tests. | Requires P-loop and likely Cluster 3 runner leases. |
| A4 P-to-C isolation | History isolation tests; no P compile logs in integrated agentic C prompt tests; C seed provenance tests; post-P F2 handoff tests. | C and P histories remain separate in v1 while the Cluster 3 runner and C adapter forward explicit repair-history config without forwarding P trace objects. |
| A5 analyzer policy grouping | Analyzer tests for legacy/unknown/new policy grouping; mixed-policy quarantine tests; one fixture containing both `last_attempt_only_v1` and `agentic_transcript_v1` rows proving headline metrics are quarantined by default; report metadata review. | Must land before agentic paid runs. |
| A6 run-packet gates | Non-authorizing run-packet template; concrete next-run draft with `DRAFT_NOT_APPROVED`; explicit repair-history policy, condition, model/config, kernel class, scale, authorization flags, expected paths, metadata checklist, analyzer quarantine preconditions, stop/no-go conditions, and post-run validation plan; forbidden-scope and no-execution checks. | Modal, generation, output mutation, n=5, n=20, and paper-scale work still require a future signed approval packet. |
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
| D-OBS-01 | Should observability sidecars be required by default or opt-in during initial rollout? | resolved | O1 runner instrumentation; any run that wants observability evidence | Observability spec owner | Resolved by O-spec v0.2.1 | Existing and development runners default to opt-in/off; final-design or paper-scale runs should use `required` after O0/O1/O3/O4 acceptance. | Initial rollout uses explicit `off`, `best_effort`, or `required` modes; no implicit sidecar writes. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-02 | What is the canonical `experiment_id` / `run_id` format? | resolved | O0/O1 sidecar schema; run approval packets; analyzer joins | Observability spec owner | Resolved by O-spec v0.2.1 | Explicit human-readable `experiment_id` and `run_id`; output path remains a join key but is not the sole ID. | Both IDs are required whenever observability is enabled; O0 event IDs are UUID strings and event sequences start at `0` without gaps. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-03 | Should actual Modal cost attribution use app tags, isolated windows, or both? | resolved | O5 billing reconciliation; cost-per-success claims | Observability/billing owner | Resolved for O0-O5 planning | No actual-cost claim in O0-O4; O5 should prefer App tags plus non-overlapping time windows where possible. | Actual billing remains unavailable until a future approved O5 reconciliation. | `docs/16_observability_sidecar_implementation_spec.md` |
| D-OBS-04 | Should Phase 14c wait for observability sidecars? | resolved | Future final-design or paper-scale run packets | Run spec owner plus user approval | Resolved after Phase 14e state reconciliation | Phase 14c already ran as diagnostic before sidecars; future final-design/paper runs should wait for O0/O1/O3/O4 or explicitly mark observability unavailable. | No retroactive sidecar is fabricated for Phase 14a-14e artifacts. | `docs/16_observability_sidecar_implementation_spec.md`; `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` |
| D-MET-01 | Should metric registry live only in analyzer metadata or also in a shared Python registry module? | resolved | S1 analyzer metadata; S2 report builder | Analyzer/report spec owner | Resolved by S-spec v0.1.2 | Analyzer metadata first; no shared module until justified | S1 implements analyzer-output metadata only; a shared Python registry module is deferred unless a later spec or launch packet justifies extraction. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-MET-02 | What exact formula defines `syntax_valid_rate` across mixed Cluster 1/2/3 schemas? | resolved | S1 metadata; S2 reports; paper-facing syntax claims | Analyzer/report spec owner | Resolved by S-spec v0.1.2 | Do not report mixed-cluster syntax rate; report cluster-local diagnostics only | `syntax_valid_rate` is unavailable for mixed current schemas unless every row has compatible explicit syntax evidence and the same `syntax_valid_definition_id`; S1 should emit availability metadata instead of a mixed aggregate. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-MET-03 | Should current report HTML refresh happen immediately or after analyzer metadata extension? | resolved | S2 report builder/dashboard | Report owner | Resolved by S-spec v0.1.2 | Wait for S1 unless docs-prose-only | S2 report HTML/data refresh waits for S1 metadata unless the change is docs-prose-only. | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| D-AGENT-01 | What is the maximum rendered prompt length and truncation budget for `agentic_transcript_v1`? | resolved | A1 prompt renderer; A2/A3 loop integration | Agentic memory spec owner | Resolved by A-spec v0.1.5 | Default local/development budget is 24000 UTF-8 characters; explicit positive overrides allowed; fail closed if required sections do not fit | Renderer uses a deterministic character budget in v1; tokenizer-derived budgets require later token/observability integration. | `docs/18_agentic_transcript_v1_implementation_spec.md` |
| D-AGENT-02 | Should latest full source be included by default when it differs from best anchor? | resolved | A1 renderer; A2/A3 integration | Agentic memory spec owner | Resolved by A-spec v0.1.5 | Exclude latest full source by default; include only if explicitly enabled and within budget | Default agentic prompts include the full best-anchor source plus latest failure details, not every full prior source. | `docs/18_agentic_transcript_v1_implementation_spec.md` |
| D-AGENT-03 | Does `agentic_transcript_v1` remain opt-in through all development runs? | resolved | A2/A3 integration; A6 run-packet gates; run specs | Orchestration contract owner | Resolved before implementation | Opt-in | `agentic_transcript_v1` remains opt-in until paired A/B review and explicit contract/spec update. | `docs/15_experiment_change_orchestration_contract.md` |
| D-AGENT-04 | Should P-to-C handoff include a one-line P provenance note in C history? | resolved | A4 P-to-C isolation | Agentic memory spec owner | Resolved by A-spec v0.1.5 | No P compile logs and no P provenance note in C prompt text for v1 | C may record metadata that the seed source came from post-P F2, but C prompt-visible history starts from the C seed and public C evidence only. | `docs/18_agentic_transcript_v1_implementation_spec.md` |
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
