# Experiment Change Orchestration Contract

- Version: 1.0.13
- Status: orchestration contract / no code changes authorized by itself
- Scope: sequencing, branch ownership, parallel-work boundaries, gates, run
  controls, and future experiment metric-family declarations for the planned
  changes in docs 12 through 14
- Component implementation specs: `docs/16_observability_sidecar_implementation_spec.md`,
  `docs/17_structural_task_analyzer_metadata_implementation_spec.md`, and
  `docs/18_agentic_transcript_v1_implementation_spec.md`
- Modal status: no Modal command, GPU run, n=5 run, n=20 run, paper-scale run,
  output mutation, profiler, timing, speedup, or benchmark is authorized by this
  contract

## Purpose

This document is the authoritative coordination contract for the next set of
high-blast-radius experiment changes:

1. experiment observability and sidecar telemetry;
2. agentic repair memory for C and P repair loops;
3. structural-vs-task outcome reporting and analyzer/report labeling;
4. optional Cluster 3 development-scale run planning after the above decisions
   are stable.

The goal is to make parallel work safe. This contract defines what may proceed
in parallel, what must be serialized, which files or concepts need a single
owner, and which gates must pass before paid or paper-scale work resumes.

## Authority And Relationship To Existing Plans

This contract coordinates the following planning documents:

| Source | Role under this contract |
|---|---|
| `docs/12_experiment_observability_plan.md` | Observability design source. This contract controls rollout order and integration gates. |
| `docs/13_agentic_repair_memory_strategy.md` | Repair-memory policy source. This contract controls default policy, branch isolation, and rerun gates. |
| `docs/14_structural_vs_task_outcome_reporting_plan.md` | Reporting terminology and analyzer-labeling source. This contract controls when analyzer/report changes may land. |
| `docs/16_observability_sidecar_implementation_spec.md` | Observability implementation contract for O0-O4. |
| `docs/17_structural_task_analyzer_metadata_implementation_spec.md` | Structural/task analyzer, report metadata, and future experiment packet contract record for S0-S4. |
| `docs/18_agentic_transcript_v1_implementation_spec.md` | Agentic repair-memory implementation contract for A0-A6. |
| `audits/cluster3_phase14_n5_condition_matrix_plan.md` | Current optional Cluster 3 n=5 planning source. This contract preserves its one-cell-at-a-time approval rule. |

When this contract and a component plan disagree:

1. current code and tests still define actual behavior;
2. current registered artifacts still define observed evidence;
3. this contract controls sequencing, parallelism, and run gates;
4. component plans control local design intent inside their own scope;
5. future implementation specs may refine component details, but must not weaken
   the gates in this contract without explicitly updating this document.

## Non-Goals

This document does not:

- define final Pydantic schemas for observability;
- define exact prompt text for `agentic_transcript_v1`;
- define analyzer registry data structures;
- define report HTML layout;
- approve any Modal run;
- approve an `n=20` Cluster 3 run;
- promote development-scale artifacts to paper-scale evidence;
- change Cluster 2 C from F2-only correctness feedback;
- change Cluster 3 P from F1_COMPILE-only compile feedback;
- authorize performance, profiler, timing, speedup, or benchmark claims.

## Current Decision

Do not run Cluster 3 `n=20` paper-scale while these changes are unsettled.

Rationale:

- observability changes affect cost, token, and timing interpretation;
- repair-memory changes affect prompts, prompt hashes, source hashes, success
  rates, failure distributions, token use, and Modal wall time;
- structural-vs-task reporting changes affect metric labels, analyzer metadata,
  and report tables;
- a new `n=20` run before those contracts are stable would likely become an
  expensive legacy artifact with limited interpretability.

The current Cluster 3 execution state is the Phase 14e four-cell n=5
development matrix freeze. Phase 14a produced a validated `P` cell with five
`F0_PARSE` rows and zero P attempts. Phase 14b produced a validated `C+P` cell
with five `F0_PARSE` rows, zero P attempts, and zero C attempts. Phase 14c
produced a validated `G+C+P` template-upper-bound diagnostic cell with five
clean-success rows, zero P attempts, and zero C attempts. Phase 14d approved
reuse of the validated Phase 12 `G+P` cell, and Phase 14e froze the four-cell
development matrix with 20 schema-valid rows. The matrix is condition coverage
only. It is insufficient repair signal and does not support P-lift, C-lift,
pass@k, correctness-improvement, statistical, performance, paper-scale, or
`n=20` claims.

## Change Streams

### Stream S: Structural And Task Outcome Reporting

Owner document:

```text
docs/14_structural_vs_task_outcome_reporting_plan.md
```

Purpose:

- distinguish structural/code-surface metrics from task/functional metrics;
- preserve `functional_success` as the primary current task outcome;
- add analyzer/report metadata without breaking legacy consumers.

Primary work packages:

| Package | Description | Parallel status |
|---|---|---|
| S0 docs terminology | Update docs to use structural/task outcome families. | Can run in parallel with O0 and A1. |
| S1 analyzer metadata | Add additive metric registry and feedback-activation diagnostics. | Serialized owner only. |
| S2 report builder/dashboard | Use analyzer metadata for report sections and labels. | Starts after S1 metadata shape is stable. |
| S3 optional analyzer output rerun | Write new analyzer output or documented metadata-only rerun. | Serialized, after S1 and S2. |
| S4 future experiment integration | Require future packets to declare metric families, gates, denominators, evidence sources, and claim boundaries before new evidence or paper-readiness work. | Docs/planning only; no analyzer/output/report refresh. |

### Stream O: Observability Sidecars

Owner document:

```text
docs/12_experiment_observability_plan.md
docs/16_observability_sidecar_implementation_spec.md
```

Purpose:

- add wall-clock, token, Modal identity, and cost observability with minimal row
  schema blast radius;
- keep scientific result rows stable at first;
- write sidecar artifacts keyed to existing row identity.

Primary work packages:

| Package | Description | Parallel status |
|---|---|---|
| O-spec sidecar implementation spec | Define O0-O4 schema, identity, path, logger, privacy, token, Modal context, and cost contracts. | Complete; code not started. |
| O0 sidecar core | Implement `shared/observability` schema, logger, paths, and redaction from the spec. | Can run in parallel with S0 and A1. |
| O1 local wall-clock events | Instrument local orchestration boundaries. | Must coordinate with runner owners. |
| O2 optional Modal context | Add optional remote runtime identity fields. | Serialized with Modal schema owners. |
| O3 token telemetry | Add prompt/generated/total token sidecar fields. | Serialized with generation response owners. |
| O4 estimated compute cost | Add pinned pricing snapshot and estimate summaries. | Can follow O0/O1; no run required. |
| O5 actual billing reconciliation | Add post-hoc billing reconciliation CLI. | Later; requires billing/tag policy. |
| O6 performance timing contract | Add Level 4 timing only if later authorized. | Future only; not part of current run gate. |

### Stream A: Agentic Repair Memory

Owner document:

```text
docs/13_agentic_repair_memory_strategy.md
```

Purpose:

- make repair prompts use explicit structured memory;
- select a best prior source as repair anchor;
- preserve C/P feedback boundaries and hidden-eval protections;
- label all new runs by repair-history policy.

Primary work packages:

| Package | Description | Parallel status |
|---|---|---|
| A0 policy constants | Add policy labels and defaults with no behavior change. | Can run after this contract. |
| A1 pure prompt core | Attempt evidence, anchor selection, transcript rendering, golden tests. | Can run in parallel with S0/O0. |
| A2 Cluster 2 C integration | Opt-in policy flag in C loop, F2-only boundary preserved. | Serialized with Cluster 2 feedback runner owner. |
| A3 Cluster 3 P integration | Opt-in policy flag in P loop, F1_COMPILE-only boundary preserved. | Serialized with Cluster 3 feedback runner owner. |
| A4 P-to-C handoff isolation | Keep histories separate and record seed provenance. | After A2/A3 contracts are stable. |
| A5 analyzer policy grouping | Ensure mixed repair policies are grouped or rejected. | Serialized with S1 analyzer owner. |
| A6 A/B smoke and dev gates | Compare old vs new policy on paired seeds. | Requires explicit run approval if Modal is used. |

### Stream R: Cluster 3 Development Runs

Owner documents:

```text
audits/cluster3_phase14_n5_condition_matrix_plan.md
docs/04_methodology_cluster3.md
docs/05_artifacts_and_results_registry.md
```

Purpose:

- preserve the current Cluster 3 Phase 14e freeze state;
- prevent paid runs from racing ahead of analysis and policy changes;
- avoid mixed-policy or pre-observability artifacts unless explicitly accepted
  as diagnostics.

Primary work packages:

| Package | Description | Parallel status |
|---|---|---|
| R0 no-run hold | Preserve no `n=20`, no paper-scale default. | Always active until all paper gates pass. |
| R1 Phase 14a P n=5 | Completed one-cell `P` `elementwise` `fp32` run; insufficient F1/P-loop signal. | Historical input only; not a paper or P-lift gate. |
| R2 Phase 14b C+P n=5 | Completed one-cell `C+P` `elementwise` `fp32` run; insufficient repair signal. | Historical input only; not a paper, P-lift, or C-lift gate. |
| R3 Phase 14c G+C+P n=5 | Completed one-cell `G+C+P` `elementwise` `fp32` run; clean-success diagnostic grammar rows, zero repair fires. | Historical input only; not a paper, P-lift, or C-lift gate. |
| R4 G+P reuse decision | Completed decision to reuse the validated Phase 12 `G+P` n=5 artifact as the Phase 14 matrix cell. | Historical input only. |
| R5 Phase 14e matrix freeze | Completed four-cell n=5 development matrix freeze with warnings. | Condition coverage only; not paper-scale evidence. |
| R6 n=20 paper-scale or broader-run decision | Future only. | Blocked by gates in this contract and requires separate approval. |

## Global Dependency Graph

The dependency graph is intentionally conservative:

```text
baseline freeze
  -> this orchestration contract
  -> S0 docs terminology
  -> S1 analyzer metadata
  -> S2 report/report-builder labels
  -> S4 future experiment metric-family declarations

baseline freeze
  -> this orchestration contract
  -> O0 sidecar schema/logger
  -> O1 local wall-clock instrumentation
  -> O2 optional Modal runtime identity
  -> O3 token telemetry
  -> O4 estimated compute-cost summaries

baseline freeze
  -> this orchestration contract
  -> A0 policy constants
  -> A1 pure prompt core
  -> A2 C-loop opt-in integration
  -> A3 P-loop opt-in integration
  -> A4 P-to-C history isolation
  -> A5 analyzer policy grouping
  -> A6 paired A/B gates

Future Cluster 3 run or paper-scale readiness packet
  requires baseline freeze
  requires Phase 14e audit/registry state to remain valid
  requires S4 metric-family declarations
  requires explicit user approval
  should wait for O0/O1/O3/O4 if observability is required for the run
  must wait for A5 if agentic_transcript_v1 is enabled

R6 n=20 paper-scale
  requires S1/S2 stable
  requires S4 metric-family declaration guidance
  requires O0/O1 stable, and preferably O2/O3/O4
  requires A5 stable if any repair-history policy changes are in scope
  requires clean n=5 development audits
  requires cost estimate review
  requires separate explicit user approval
```

## Parallelization Contract

### Safe To Parallelize Initially

These lanes can start from the same clean baseline:

| Lane | Branch suggestion | Allowed writes |
|---|---|---|
| S0 docs terminology | `codex/outcome-taxonomy-docs` | Docs only: `docs/06`, `docs/07`, `docs/09`, `docs/14`, preliminary report prose if explicitly included. |
| O0 sidecar core | `codex/observability-sidecar-core` | New `shared/observability/*` and tests for sidecar schema/logger only. |
| A1 prompt core | `codex/agentic-memory-core` | New or isolated prompt-memory helpers and tests; no runner behavior change. |
| Documentation routing | `codex/change-orchestration-contract` | This document and routing docs only. |

### Must Be Serialized

Only one active owner may edit each of these surfaces at a time:

| Surface | Reason |
|---|---|
| `shared/analysis/factorial.py` | Analyzer schema, reportability, and policy grouping can conflict. |
| `shared/tests/test_factorial_analysis.py` and analyzer golden outputs | Snapshot churn and compatibility gates require one owner. |
| `cluster2/feedback/repair_loop.py` | Agentic memory changes affect behavior and prompt hashes. |
| `cluster2/experiments/run_cluster2_modal.py` | Runner flags, telemetry, and repair policy metadata can collide. |
| `cluster3/feedback/compile_error_repair.py` | P prompt policy and F1 boundary tests require one owner. |
| `cluster3/experiments/run_cluster3_modal.py` | Telemetry, policy flags, output paths, and Modal behavior must not diverge. |
| result dataclasses under `cluster2/results/` and `cluster3/results/` | Schema fields must stay nullable/defaultable and artifact-compatible. |
| raw output paths under `outputs/` | Run artifacts must be single-owner and never mixed-policy. |
| Modal execution | Paid runs must be explicit, sequential, and auditable. |

### Conditional Parallelism

These can run in parallel only after their shared contract is stable:

| Work | Condition for parallel work |
|---|---|
| O1 runner instrumentation and A2/A3 runner integration | Split by runner and file owner, or serialize if both need the same runner. |
| S2 report builder and O4 cost summaries | Analyzer metadata keys and sidecar summary keys must be frozen first. |
| A2 C-loop integration and A3 P-loop integration | Policy constants, prompt renderer, and common metadata field names must be frozen first. |
| Future run branches and implementation branches | Avoid concurrent edits to runner/output files. A run branch may proceed only if it uses a clean baseline, no unmerged runner changes, and a fresh approval packet. |

## Branch And Worktree Rules

Use one branch per lane. Branch names should make the lane visible:

```text
codex/change-orchestration-contract
codex/outcome-taxonomy-docs
codex/observability-sidecar-core
codex/observability-runner-instrumentation
codex/agentic-memory-core
codex/agentic-memory-c2-integration
codex/agentic-memory-c3-integration
codex/analyzer-metric-registry
codex/report-builder-outcome-families
codex/cluster3-phase14a-p-n5
```

Worktree rules:

- each branch gets its own worktree;
- each branch starts from the accepted orchestration-contract commit;
- no branch writes raw `outputs/` unless it is the single approved run lane;
- no branch changes Modal execution behavior unless its spec explicitly owns
  that surface;
- no branch changes dependencies, lockfiles, Modal image definitions,
  CUDA/Triton/package versions, model revisions, or tokenizer revisions unless
  its implementation spec explicitly owns that change;
- no branch performs package installs, model downloads, billing queries, Modal
  API calls, web fetches, or other network work unless the launch packet
  explicitly allows it;
- no branch prints, persists, or adds telemetry for secrets, credentials,
  tokens, or unapproved local machine paths;
- one branch owns one work package by default; no opportunistic adjacent fixes,
  bundled refactors, or extra issue cleanup unless the launch packet is updated
  before the work starts;
- any branch touching shared analyzer or runner files must announce ownership in
  its PR or handoff note;
- do not merge two branches that both changed the same serialized surface
  without a manual conflict audit.

## Orchestrator Operating Protocol

An agent may use this contract to coordinate work only if it maintains a visible
state record. The canonical state record is:

```text
docs/handoff/experiment_change_orchestration_state.md
```

### Single-Writer State Rule

Only the orchestrating agent may directly edit the canonical state file during
parallel work. Worker agents must produce handoff notes, branch summaries, or
patch proposals for state changes, but they must not independently mutate the
state file unless they have explicitly taken the orchestrator role in the
current thread and recorded that handoff.

The state file must be updated before starting a lane, before taking a
serialized surface, before launching any paid run, and after merging or
abandoning work. A PR body, audit note, handoff file, or thread summary may
repeat state information, but it does not replace the canonical state file.

The state file also owns the current validation matrix. Work packages must
record the exact commands and manual checks required by that matrix before
claiming an exit gate. If a package cannot run a listed validation, its handoff
must explain why and name the replacement check.

The state file also owns the open decisions register. A package may not start
implementation if an open decision blocks its entry gate, unless the package
explicitly operates under the register's conservative default and records that
choice in its work package card.

The state file also owns edge-case guardrails for freshness checks, state drift,
partial artifacts, hard cost/stop limits, no-silent-defaults policy, abandoned
work, and run provenance freeze. Packages and run packets must satisfy those
guardrails unless a later approved contract explicitly replaces them.

Minimum state record:

```text
baseline commit:
active branches:
active worktrees:
active serialized-surface leases:
current gate:
blocked gates:
approved run packets:
merged packages:
abandoned packages:
known caveats:
```

If `docs/handoff/experiment_change_orchestration_state.md` is missing, a new
orchestrating agent must create it before starting implementation work. If the
state file contradicts current git state, code, tests, or artifact registry
entries, the agent must stop and reconcile the mismatch before proceeding.

## Agent Launch Packet Protocol

Before starting any parallel implementation agent, the orchestrator must create
or record a launch packet. The packet is the agent's executable contract and
must be narrower than or equal to this document and the relevant implementation
spec.

Required launch packet fields:

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
```

The launch packet may be embedded in this state file, a PR body, or a handoff
note, but the state file must reference it before the worker starts.

## Requirement-To-Test Traceability

Every component implementation spec must assign stable requirement IDs before
code work begins. Examples:

```text
O0-REQ-001
A1-REQ-004
S1-REQ-002
```

Each branch handoff must map:

- requirement IDs implemented;
- files changed for each requirement;
- tests or manual checks that prove each requirement;
- requirements intentionally left out of scope.

A branch may not claim an exit gate if a required requirement has no test,
scan, fixture, or explicit manual-review record. If a requirement cannot be
tested yet, the handoff must state the blocker and the downstream gate that
will remain closed.

## Default-Invariance Requirement

Every high-blast-radius branch must prove that default behavior is unchanged
when new flags are absent, `off`, or configured to the legacy policy. The proof
must be a test or a recorded scan, not only a statement.

Required default-invariance checks by stream:

| Stream | Required proof |
|---|---|
| Observability | No sidecar artifacts are written and no result rows change when observability is absent or `off`. |
| Agentic memory | Existing prompt policy remains `last_attempt_only_v1` or the current default until an explicit A/B decision changes it. |
| Analyzer/reporting | Existing artifacts remain readable and legacy metrics remain available under compatible names. |
| Runner flags | Existing CLI defaults do not change Modal behavior, output paths, retry behavior, or repair routing. |

## Independent Review Gate

High-blast-radius branches require a review pass by an agent or reviewer that
did not implement the branch before promotion. This gate applies to any branch
that touches:

- experiment runners or Modal behavior;
- analyzer semantics, metric definitions, or report data;
- repair-loop prompt policy or C/P eligibility;
- result schemas, artifact paths, hashes, or sidecar writes;
- dependency, lockfile, model, tokenizer, CUDA, Triton, or Modal image
  definitions.

The independent review must check scope, requirement-to-test traceability,
default-invariance proof, fixture-first proof where required, unsupported-claim
language, and unauthorized Modal/output mutation. The implementing agent may
fix review findings, but the branch may not promote until the review pass is
recorded in the handoff.

## Fixture-First Rollout Gate

Before any Modal, paid, generation, n=5, n=20, or output-mutating run uses a new
behavior, that behavior must pass a local fixture, synthetic artifact, or
minimal no-remote contract test. The fixture proof must exercise the same
control path that the run would use, including flags, path validation, schema
validation, prompt policy selection, analyzer grouping, or sidecar mode as
applicable.

If a behavior cannot be fixture-tested before a run, the run packet must say
why, list the missing fixture, and keep the run blocked unless the user
explicitly accepts that gap.

## Orchestrator Dry-Run Checklist

Before launching multiple parallel implementation agents, or before promoting
the first branch from a new orchestration cycle, the orchestrator should perform
a no-code dry run against this contract and state file:

```text
simulate launching O0/A1/S0 or the requested package set
simulate assigning and releasing one serialized-surface lease
simulate rejecting a worker without a launch packet
simulate rejecting an invalid run packet
simulate promoting one branch through the merge train
simulate handling one stale worktree
record any contract ambiguity found during the dry run
```

If the dry run exposes ambiguity in branch ownership, gates, tests, state
updates, or run approval, stop and patch the contract or state before launching
parallel workers.

## Conflict Resolution Order

When two sources, specs, agents, or artifacts disagree, resolve the conflict in
this order:

1. current code and tests for actual executable behavior;
2. current registered artifacts, hash sidecars, and audit reports for observed
   results;
3. this orchestration contract for sequencing, gates, and run permissions;
4. the live orchestration state file for current branches, leases, packets, and
   next allowed actions;
5. component implementation specs for local design details;
6. source planning docs such as docs 12 through 14 for design intent;
7. explicit user decision when the above do not resolve the conflict.

Do not resolve conflicts by silently choosing the most convenient source. The
handoff must record the conflict, chosen authority, and any follow-up doc update.

## Maximum Branch Scope

Each branch should implement one work package only. A branch may not add
opportunistic adjacent fixes, unrelated cleanups, broad refactors, dependency
updates, or extra documentation rewrites unless:

- the launch packet is updated before the extra work starts;
- affected leases are recorded;
- added requirements receive IDs and tests;
- downstream gates and review requirements are updated.

If a branch discovers adjacent work, record it as a new package or open decision
instead of absorbing it by default.

## Secrets And Credentials Boundary

Workers must not print, persist, add telemetry for, or route into sidecars any
secret, credential, token, private key, API key, billing credential, Modal
credential, Hugging Face token, shell environment dump, or unapproved local
machine path. Approved artifact paths, repo-relative paths, and explicitly
listed non-secret runtime identifiers are allowed.

Implementation and review must treat these as forbidden by default:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
HF_TOKEN
HUGGING_FACE_HUB_TOKEN
OPENAI_API_KEY
WANDB_API_KEY
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
*_TOKEN
*_SECRET
*_API_KEY
```

If a task truly needs credentialed access, the launch packet or run packet must
state the credential class, the exact operation, why it is required, how output
will be redacted, and how the result will be verified without exposing the
secret.

## Network And Dependency-Download Policy

Implementation workers default to offline/no-network behavior. They may not
install packages, update lockfiles, download models or tokenizers, query Modal
or billing APIs, call external services, fetch web pages, or hydrate remote
assets unless the launch packet explicitly authorizes the operation.

Any authorized network or dependency-download operation must record:

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

Unexpected network need is an escalation condition, not a reason to broaden the
branch silently.

## Negative-Test Requirement

High-risk guardrails must include at least one negative test, rejection fixture,
or explicit fail-closed check. The test should prove that invalid or unsafe
inputs are rejected rather than merely proving that the happy path works.

Examples:

| Area | Negative behavior to prove |
|---|---|
| Observability | Invalid sidecar path, path collision, schema-extra field, forbidden telemetry key, or mismatched resume identity is rejected. |
| Agentic memory | Prompt budget overflow, prompt-injection text, C outside F2, or P outside `F1_COMPILE` fails closed. |
| Analyzer/reporting | Mixed policy, mixed denominator, unknown metric gate, or unsupported report claim is rejected or quarantined. |
| Run packets | Missing stop limits, output path collision, missing provenance, or unapproved network/Modal action blocks execution. |

If a negative test cannot be added in the current branch, the handoff must name
the missing test and keep the related downstream gate closed.

## Orchestrator Escalation Thresholds

The orchestrator must stop and ask for user direction, or require a contract or
state update, when any of these occur:

- repeated test failure after two focused fix attempts;
- unclear authority conflict after applying the conflict-resolution order;
- unexpected output mutation, generated artifact, or sidecar write;
- need for a new dependency, lockfile change, model/tokenizer download, Modal
  image change, or network access not listed in the launch packet;
- branch scope grows beyond one work package;
- secret, credential, private eval, hidden correctness data, or unapproved local
  path exposure is suspected;
- implementation would change default behavior or run eligibility;
- a paid or output-mutating run would proceed with an untested guardrail.

Escalations must record the trigger, current state, options considered, and the
user or contract decision before work resumes.

## Post-Merge Verification Window

After each promoted branch lands in the integration branch or active baseline,
the orchestrator must run or record a short integration verification before
unblocking the next dependent package. This check is separate from the branch's
local tests and is meant to catch merge-order effects.

Minimum post-merge verification:

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

Do not unblock a dependent serialized package until this verification is
recorded or the state file explains why it is not applicable.

## Stale Worker And Worktree Cleanup

If a worktree, branch, or worker handoff passes its review checkpoint without a
current owner, the orchestrator must mark it stale before relying on it.

Stale-work cleanup requires:

- inspect the branch/worktree diff without discarding it;
- record files touched, leases held, tests run, and artifacts touched;
- release, renew, or mark abandoned every lease;
- block merge from the stale branch until it is rebased onto the current
  orchestration baseline and revalidated;
- preserve any useful patch or handoff note before deleting or ignoring the
  worktree.

## Serialized-Surface Lease Protocol

Serialized surfaces require explicit short-lived ownership. A lease prevents two
parallel agents from changing the same high-blast-radius file or concept.

Lease record:

```text
surface:
owner branch:
owner worktree:
scope:
start commit:
expected files:
expected tests:
expires or review checkpoint:
status: active | released | abandoned | merged
```

Rules:

- one active lease per serialized surface;
- a lease covers the concept, not just the filename;
- a lease does not authorize output mutation or Modal execution;
- stale leases must be released, renewed, or marked abandoned before another
  branch takes the surface;
- a branch that needs to expand its lease must update the state record first;
- if two branches discover overlapping leases, both stop before further edits to
  the shared surface.

Recommended serialized-surface names:

```text
analyzer_metric_registry
cluster2_c_repair_loop_policy
cluster3_p_repair_loop_policy
cluster2_runner_flags_and_metadata
cluster3_runner_flags_and_metadata
result_schema_cluster2
result_schema_cluster3
modal_runtime_response_schema
raw_outputs_cluster3
report_data_builder
```

## Decision Authority Table

The orchestrating agent can make routine sequencing decisions, but some choices
must be escalated to the user or to a new contract/spec update.

| Decision | Agent may decide? | Required control |
|---|---:|---|
| Start S0/O0/A1 branches from the accepted baseline | yes | State record updated. |
| Assign or release a serialized-surface lease | yes | Lease record updated. |
| Reorder non-dependent docs-only work | yes | State record updated. |
| Add tests within an owned package | yes | Handoff records tests. |
| Change default repair policy to `agentic_transcript_v1` | no | User decision plus contract/spec update. |
| Run Modal, n=5, or paid smoke | no | Explicit run packet and user approval. |
| Run `n=20` or paper-scale work | no | Gate G8 plus explicit user approval. |
| Rewrite or overwrite existing raw outputs | no | Explicit archive/overwrite approval. |
| Change C eligibility beyond F2 | no | New methodology contract. |
| Change P eligibility beyond F1_COMPILE | no | New methodology contract. |
| Add performance/timing/speedup claims | no | New Level 4/performance contract. |
| Merge two branches with overlapping serialized-surface edits | conditional | Manual conflict audit and tests. |

## Run Approval Packet

Any Modal, paid, n=5, n=20, generation, or output-mutating run needs a written
approval packet before execution. The packet must be reviewed in the current
thread or captured in an audit/handoff note.

Because `docs/`, `audits/`, and `outputs/` may be ignored by git, the packet
must include planning-doc fingerprints as explicit document versions and audit
references. A git commit alone is not enough run provenance for this workstream.

Required fields:

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
```

Approval is scoped to the packet exactly as written. Any command expansion,
condition expansion, output-path change, overwrite, retry, resume, or
paper-scale promotion requires a new approval.

## Future Experiment Metric-Family Declarations

Future launch packets, run approval packets, and paper-readiness packets must
declare which metrics contribute to structural/code-surface, task/functional,
mixed diagnostic, planned-deferred, future-only, and
benchmarkable/performance families before any new experiment, analyzer refresh,
output mutation, or paper-scale claim is approved.

The declaration does not authorize execution. It is a planning requirement that
keeps the S0-S3 analyzer/report separation attached to future experiments.

Required packet section:

```text
metric_family_declarations:
  - metric_name:
    outcome_family:
    level_gate:
    metric_gate:
    reportability:
    current_status:
    evidence_source:
    denominator_policy:
    claim_boundary:
```

Allowed `outcome_family` values for current structural/task reporting are:

```text
structural_code_surface
task_functional
mixed_diagnostic
benchmarkable_performance
```

Planned and future metrics must use `current_status=planned_deferred` or
`current_status=future_only`; they must not be presented as current values.
Benchmarkable/performance metrics must also state whether the evidence is
sidecar-only and whether performance sidecar authorization exists.

Every future experiment packet must also include:

```text
condition matrix:
primary response variable:
secondary response variables:
diagnostic response variables:
denominator policy:
attempt-collapse policy:
gate eligibility policy:
feedback activation policy:
metric_registry compatibility expectation:
planned/future metric handling:
output mutation authorization status:
paper-scale claim authorization status:
performance sidecar authorization status:
```

Contribution-attribution guidance:

- Ask whether a condition changed structural/code-surface quality separately
  from task/functional correctness.
- Ask whether an observed change is only gate reach, denominator movement,
  feedback eligibility, or feedback activation.
- Distinguish rows that fail before Level 2 from rows that reach Level 2 and
  fail the task harness.
- Treat C feedback as activated only on its eligible Level 2/F2 set and P
  feedback as activated only on eligible `F1_COMPILE` rows.
- Keep performance, timing, speedup, profiler, and benchmark values in
  benchmarkable/performance sidecars unless a later packet explicitly promotes
  them.

This declaration enables attribution by metric family and gate. It does not by
itself prove causality. Causal claims still require a compatible factorial
design, fixed budgets, compatible denominators, same shapes, dtypes, and
devices, preregistered metrics, and a signed packet that authorizes the claim
scope.

Future report or analyzer consumers must fail closed, or mark the affected
metric diagnostic-only, when:

- an unknown `metric_registry` major schema is encountered;
- `outcome_family` is missing;
- `reportability` is missing;
- `current_status` or `reportability` conflicts with computed values;
- `planned_deferred` or `future_only` metrics are presented as current;
- compile-only evidence is presented as task/functional correctness;
- benchmarkable/performance claims are requested without an approved
  performance sidecar evidence source.

## Merge And Promotion Protocol

Merges should happen through a narrow promotion sequence rather than by merging
all parallel branches as they finish.

Use an integration branch or explicit merge train for parallel work. Promote one
branch at a time, run its gate, update the state file, then promote the next
branch. Do not merge multiple completed branches directly into the active
baseline just because their local checks passed.

Promotion checklist:

```text
branch rebased or merged onto current orchestration baseline
serialized leases released or transferred
launch packet satisfied
requirement-to-test map complete
tests listed and passing, or caveats documented
default-invariance proof recorded
fixture-first proof recorded where required
independent review recorded where required
negative tests recorded for high-risk guardrails
secrets/credentials boundary checked
network/API/dependency-download activity authorized or absent
branch scope limited to the launch packet
dependency and lockfile diff reviewed
post-merge verification window defined
docs impact reviewed
legacy behavior preserved or migration documented
new metadata fields documented
rollback path documented
no unauthorized output mutation
no unauthorized Modal execution
no unsupported result claim introduced
```

If a branch changes analyzer semantics, prompt semantics, runner flags, result
schemas, or report data, it also needs a promotion note that states:

```text
old artifact compatibility:
new artifact compatibility:
mixed-artifact behavior:
expected analyzer/report changes:
manual review points:
```

Dependency, lockfile, Modal image, CUDA/Triton/package version, model revision,
and tokenizer revision changes must be listed explicitly in the promotion note.
If they were not authorized by the launch packet and implementation spec, the
branch must stop before promotion.

After a promotion, the orchestrator updates the state record and identifies the
next newly unblocked package. Do not start a newly unblocked serialized package
until its predecessor branch has either merged cleanly or been abandoned.

## Agent Trust Boundary

This contract is sufficient for supervised orchestration of parallel engineering
work if the orchestrating agent maintains the state record and respects leases.
It is not sufficient for unsupervised paid experiment execution.

Trust level by activity:

| Activity | Trust status |
|---|---|
| Creating component implementation specs | trusted after G1 |
| Starting safe parallel branches | trusted after state record exists |
| Editing docs-only terminology | trusted within S0 scope |
| Building isolated sidecar core | trusted within O0 scope |
| Building pure prompt core | trusted within A1 scope |
| Editing analyzer or runners | trusted only with active lease and tests |
| Launching Modal or mutating outputs | not trusted without explicit packet approval |
| Running n=20 or paper-scale work | not trusted until G8 and explicit approval |

## Gate Model

### Gate G0: Baseline Freeze

Required before any lane starts:

- `git status --short` is clean, or dirty files are classified and excluded;
- current commit is recorded in the branch/audit note;
- no output mutation is pending;
- known full-regression caveat is recorded:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

### Gate G1: Orchestration Contract Accepted

Required before component implementation specs:

- this document exists and is linked from routing docs;
- no component spec weakens this document's gates;
- no Modal or output mutation is performed by contract creation.

### Gate G2: Reporting Terminology Stable

Required before analyzer/report implementation:

- structural/code-surface and task/functional terminology is accepted;
- `compile_success` is labeled structural, not functional;
- `functional_success` remains task/functional;
- Cluster 1 Level 2 status is called unproven, not measured failure;
- Cluster 2 C activation is described as F2-eligible only.

### Gate G3: Observability Sidecar Contract Stable

Required before runner-wide telemetry:

- sidecar event schema exists;
- summary schema exists;
- JSONL append and summary writes are tested;
- sidecars are keyed to row identity;
- source text, private eval details, raw feedback, and full tracebacks are
  excluded from sidecars by default.

### Gate G4: Analyzer Compatibility Stable

Required before report refreshes or mixed-policy comparisons:

- metric registry metadata is additive;
- legacy `condition_rates`, `paired_comparisons`, `grammar_funnel`, and failure
  distributions remain readable;
- analyzers reject or quarantine mixed gates, denominator units, attempt
  policies, source row classes, and repair-history policies;
- old rows without policy labels are treated as legacy or unknown, not as
  `agentic_transcript_v1`.

### Gate G5: Agentic Prompt Core Stable

Required before C/P loop integration:

- attempt evidence model is tested;
- anchor selector is deterministic and tested;
- transcript renderer has golden prompt tests;
- prompt-injection guard is present;
- prompt hash equals exact rendered prompt text;
- forbidden C/P feedback terms fail closed;
- prompt-length truncation preserves required sections or fails closed.

### Gate G6: Agentic Integration Stable

Required before any agentic paid run:

- `last_attempt_only_v1` remains available;
- `agentic_transcript_v1` is opt-in;
- every new repaired row records the active repair-history policy;
- C remains F2-only;
- P remains F1_COMPILE-only;
- P compile logs do not flow into C prompts in v1;
- analyzer grouping by policy is implemented before headline rates are computed.

### Gate G7: Development Run Readiness

Required before any optional n=5 run:

- target output path does not exist, or overwrite/archive is explicitly
  approved;
- branch is clean except approved run/audit changes;
- pre-spend tests pass or fail only at the known Cluster 1 docs-lock caveat;
- cost and expected wall-clock are stated;
- output path, condition, kernel class, dtype, n, repair policy, and
  observability policy are stated;
- user explicitly approves that exact run.

### Gate G8: Paper-Scale Readiness

Required before any `n=20` Cluster 3 or rerun-scale work:

- G2 through G7 are satisfied for the selected policy;
- future experiment metric-family declarations are present and compatible with
  S1/S2 `metric_registry` metadata or an explicit legacy fallback;
- n=5 development cells are audited and not just generated;
- observability summaries exist or are explicitly marked unavailable with
  reasons;
- analyzer/reporting can separate structural and task outcomes;
- analyzer/reporting can separate legacy and agentic repair policies;
- prompt hashes and policy fields are stable;
- no mixed-policy output paths exist;
- cost estimate and stop controls are reviewed;
- user explicitly approves the exact paper-scale run.

## Control Flow For Common Decisions

### How Should Phase 14a Be Interpreted?

Phase 14a already ran under the current pre-agentic-memory policy. Treat it as a
development diagnostic only:

- it used current default repair behavior, not `agentic_transcript_v1`;
- it is labeled development-scale diagnostic only;
- it has five `F0_PARSE` rows, zero `F1_COMPILE` seeds, and zero P attempts;
- it is insufficient F1/P-loop signal;
- it does not validate agentic memory, P lift, pass@k, or paper-scale behavior.

Recommended default:

- do not rerun Phase 14a unless a later spec gives a specific reason;
- if a run is meant to inform final design, wait for O0/O1 observability;
- if a run is meant to test agentic memory, wait for G5/G6/A5;
- do not use Phase 14a as a reason to start `n=20`.

### How Should Phase 14b Be Interpreted?

Phase 14b already ran under the current pre-agentic-memory policy. Treat it as a
development diagnostic only:

- it used current default repair behavior, not `agentic_transcript_v1`;
- it is labeled development-scale diagnostic only;
- it has five `F0_PARSE` rows, zero `F1_COMPILE` seeds, zero initial F2 rows,
  zero P attempts, and zero C attempts;
- it is insufficient repair signal;
- it does not validate agentic memory, P lift, C lift, pass@k, or paper-scale
  behavior.

Recommended default:

- do not rerun Phase 14b unless a later spec gives a specific reason;
- if a run is meant to inform final design, wait for O0/O1 observability;
- if a run is meant to test agentic memory, wait for G5/G6/A5;
- do not use Phase 14b as a reason to start `n=20`.

### Should Agentic Memory Become Default?

No, not at implementation time.

Contract rule:

- `last_attempt_only_v1` remains the default until a paired A/B gate is reviewed;
- `agentic_transcript_v1` is explicitly selected in runner flags or config;
- any later default change must update this contract, docs 13, analyzer policy,
  and artifact registry rules.

### Should Observability Change Scientific Rows?

No, not in the first implementation phase.

Contract rule:

- sidecars first;
- optional remote metadata only where backward compatible;
- scientific row schema changes require a component implementation spec and
  explicit schema migration tests.

### Should Analyzer Work Wait For Observability?

Not for terminology metadata.

Contract rule:

- S1 metric registry can proceed before O0/O1;
- analyzer joins with observability sidecars wait until sidecar keys and summary
  formats are stable.

### Should Report HTML Be Refreshed Immediately?

Only after S1 metadata is stable, unless the change is docs-prose-only.

Contract rule:

- no new report table should use bare `pass@k` without a metric gate;
- no report table should mix structural and task outcomes under one unlabeled
  pass/success heading;
- refreshed report data must state whether it is old analyzer output, new
  metadata-only analyzer output, or new artifact lineage.

## Implementation Plan By Stream

### Stream S Plan

1. S0 docs terminology:
   - update methodology/report docs with structural/task terminology;
   - preserve current 2^2 numeric results and caveats;
   - do not modify code or artifacts.
2. S1 analyzer metadata:
   - add additive `metric_registry`, `outcome_families`,
     `feedback_activation`, and `level_reach_rates`;
   - preserve existing analyzer keys and old consumer compatibility;
   - add tests for Cluster 1 unproven functional status and C zero-eligibility.
3. S2 report builder:
   - split structural/code-surface and task/functional report sections;
   - label pass@k by gate;
   - show C eligibility and loop-fired diagnostics separately.
4. S3 optional analyzer output:
   - write a new output path or document the metadata-only rerun;
   - never rewrite raw JSONL artifacts;
   - update registry/audit only after validation.
5. S4 future experiment integration:
   - update packet guidance so future experiments declare metric families,
     gates, denominators, evidence sources, and claim boundaries;
   - require planned-deferred, future-only, and benchmarkable/performance
     metrics to remain non-current unless explicitly authorized;
   - do not run experiments, refresh analyzer outputs, rewrite raw JSONL, or
     mutate generated report assets.

### Stream O Plan

1. O0 sidecar core:
   - add schema, logger, summary writer, and round-trip tests;
   - no runner integration yet.
2. O1 local wall-clock:
   - instrument cluster runners one at a time;
   - write sidecars next to outputs when enabled;
   - default behavior must remain backward compatible.
3. O2 Modal identity:
   - extend shared Modal runtime helper with optional context;
   - update remote schema tests for optional fields.
4. O3 token telemetry:
   - surface token counts in sidecars or generation telemetry objects;
   - preserve scientific rows.
5. O4 estimated cost:
   - add pricing snapshot and summary formulas;
   - label estimates separately from actual billing.
6. O5 billing:
   - add post-hoc reconciliation only after tag/window policy is decided.
7. O6 performance:
   - future contract only; blocked until Level 4 evaluation is authorized.

### Stream A Plan

1. A0 constants:
   - define policy names and defaults;
   - no behavior change.
2. A1 pure prompt core:
   - implement attempt evidence coercion, anchor selector, transcript renderer,
     truncation, prompt-injection guard, and golden tests;
   - no runner behavior change.
3. A2 C integration:
   - add opt-in repair-history policy to Cluster 2 C loop;
   - preserve F2-only repair boundary;
   - record prompt hash, policy, and anchor metadata.
4. A3 P integration:
   - add opt-in repair-history policy to Cluster 3 P loop;
   - preserve F1_COMPILE-only repair boundary;
   - record P prompt hash, policy, and anchor metadata.
5. A4 P-to-C isolation:
   - seed C from post-P terminal source when applicable;
   - keep P compile logs out of C prompts;
   - record C history independently.
6. A5 analyzer grouping:
   - group/filter by repair-history policy;
   - quarantine mixed-policy artifacts for headline comparisons.
7. A6 A/B gates:
   - run local fixture smoke first;
   - run Modal only with explicit approval;
   - proceed only if success or diagnostic benefit improves without material
     F0/F1 regression.

### Stream R Plan

1. R0 hold:
   - no n=20;
   - no paper-scale;
   - no all-condition batch.
2. R1 Phase 14a:
   - completed `P` `n=5` `elementwise` `fp32`;
   - preserve as diagnostic-only, insufficient F1/P-loop signal;
   - do not rerun or promote without a new spec.
3. R2 Phase 14b:
   - completed `C+P` `n=5` `elementwise` `fp32`;
   - preserve as diagnostic-only, insufficient repair signal;
   - do not rerun or promote without a new spec.
4. R3/R4/R5:
   - completed Phase 14c, Phase 14d, and Phase 14e are historical inputs;
   - preserve them as development-scale diagnostics only;
   - do not rerun, broaden, or promote without a fresh spec.
5. R6 paper-scale or broader run:
   - blocked until G8.

## Required Handoff For Each Parallel Branch

Every parallel branch should include a short handoff note in its PR, audit, or
final message with:

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
```

For branches that change prompts, analyzer semantics, result schemas, or output
paths, the handoff must also state:

```text
artifact compatibility:
legacy behavior:
new metadata fields:
policy labels:
rollback path:
```

## Stop Conditions

Stop and audit before continuing if any of the following occurs:

- a branch needs to edit a serialized surface already owned by another branch;
- a worker agent mutates the canonical state file without owning the
  orchestrator role;
- a branch lacks a launch packet or attempts work outside its launch packet;
- a branch reaches promotion without requirement-to-test traceability;
- default behavior changes when new flags are absent, `off`, or legacy;
- a high-blast-radius branch reaches promotion without independent review;
- a run packet uses new behavior without fixture-first proof or explicit
  user-accepted exception;
- a high-risk guardrail has no negative test, rejection fixture, or recorded
  fail-closed check;
- an orchestrator launches multiple parallel agents before resolving ambiguity
  found during the dry run;
- the orchestrator hits an escalation threshold and continues without a user,
  contract, or state decision;
- a dependent package is unblocked before post-merge verification is recorded;
- a branch absorbs adjacent fixes or refactors outside its launch-packet scope;
- sources disagree and no conflict-resolution authority is recorded;
- secrets, credentials, private keys, API tokens, billing credentials,
  environment dumps, private eval data, or unapproved local paths are printed,
  persisted, or added to telemetry;
- package installs, model/tokenizer downloads, billing API calls, Modal API
  calls, web fetches, or other network operations occur without launch-packet
  authorization;
- dependencies, lockfiles, Modal image definitions, CUDA/Triton/package
  versions, model revisions, or tokenizer revisions change without explicit
  spec ownership;
- a stale worktree or stale branch is used as a merge source before
  revalidation;
- analyzer output changes primary current rates unexpectedly;
- a repair-history branch changes default behavior without explicit decision;
- C repair fires outside eligible F2 failures;
- P repair fires outside `F1_COMPILE`;
- sidecars include source text, private eval detail, raw feedback, or full
  tracebacks;
- runner output path already exists without overwrite/archive approval;
- Modal timeout, preemption, worker interruption, or infrastructure F3 appears
  during a paid run;
- a paid run produces mixed-policy rows;
- a report table mixes structural and task outcomes without labels;
- a branch attempts n=20, paper-scale, performance, profiling, timing, speedup,
  or benchmark work without an updated contract and explicit approval.

## Merge Order

Recommended merge order:

1. this orchestration contract and routing updates;
2. S0 docs terminology;
3. O0 sidecar core;
4. A0/A1 agentic policy constants and pure prompt core;
5. S1 analyzer metadata and compatibility tests;
6. O1 runner wall-clock instrumentation, one runner owner at a time;
7. A2/A3 C/P opt-in integration, one loop owner at a time;
8. A5 analyzer policy grouping;
9. S2 report builder labels;
10. S4 future experiment metric-family declaration guidance;
11. optional future run branch only after explicit approval;
12. later development or paper-readiness cells after audited gates;
13. no R6 paper-scale until G8.

## Contract Freeze And Amendment Policy

This orchestration contract is frozen for implementation use. Do not add more
process requirements unless there is a concrete implementation, review, or
execution trigger.

Allowed amendment triggers:

- an implementation agent hits an ambiguity that blocks work;
- the orchestrator dry run fails;
- an independent review finds a missing guardrail;
- a component implementation spec exposes a real conflict;
- a post-merge verification window finds an integration failure;
- a run approval packet exposes an unhandled safety, provenance, cost, or
  artifact-control issue;
- the user approves a new workstream, run type, dependency, network operation,
  credentialed operation, output mutation, or paper-scale decision.

Future amendments must state:

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

Amendments must be narrower than the trigger. If the issue can be resolved in a
component implementation spec, package launch packet, run packet, or state-file
entry, prefer that narrower document instead of expanding this contract.

## Deliverables This Contract Enables

The next documents should be component implementation specs, one per stream or
serialized surface:

| Future spec | Should cover |
|---|---|
| Observability sidecar implementation spec | Complete as `docs/16_observability_sidecar_implementation_spec.md`; use it for O0-O4 implementation. |
| Structural/task analyzer implementation spec | Metric registry keys, diagnostics, compatibility tests, and report-data changes. |
| Agentic repair-memory implementation spec | Evidence model, anchor selector, prompt renderer, C/P integration, metadata, and A/B gates. |
| Future Cluster 3 run or paper-readiness spec | Exact command or go/no-go criteria, target path, pre-spend tests, expected cost, validation, observability policy, and audit template. |

No future implementation spec may approve `n=20` unless it also satisfies Gate
G8 and updates this contract or explicitly cites a later replacement contract.

## Classification

`EXPERIMENT_CHANGE_ORCHESTRATION_CONTRACT_ACTIVE`

This document is a control-plane contract. It coordinates parallel engineering
work and paid-run gates. It is not evidence of new results, not a component
implementation spec, and not approval to run Modal.
