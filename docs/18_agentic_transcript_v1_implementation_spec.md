# Agentic Transcript v1 Implementation Spec

- Version: 0.1.5
- Date: 2026-06-01
- Status: implementation specification / no code changes, output mutation,
  Modal runs, n=5 runs, n=20 runs, paper-scale work, profiler, timing,
  speedup, or benchmark work authorized by itself
- Owner stream: A, agentic repair memory
- Primary planning source: `docs/13_agentic_repair_memory_strategy.md`
- Orchestration source: `docs/15_experiment_change_orchestration_contract.md`
- Live state source: `docs/handoff/experiment_change_orchestration_state.md`
- Current C prompt surface: `cluster2/feedback/prompts.py`
- Current C loop surface: `cluster2/feedback/repair_loop.py`
- Current P prompt surface: `cluster3/feedback/prompts.py`
- Current P loop surface: `cluster3/feedback/compile_error_repair.py`

## Purpose

This document defines the implementation contract for `agentic_transcript_v1`,
an opt-in repair-history policy for Cluster 2 C repair and Cluster 3 P repair.
It converts the strategy in `docs/13_agentic_repair_memory_strategy.md` into
component boundaries, default-invariance rules, prompt-rendering requirements,
metadata requirements, and acceptance tests.

The implementation goal is to give repair generations structured public attempt
history and a best previous source anchor while keeping old
`last_attempt_only_v1` behavior available and separately labeled.

The policy must be deterministic and auditable:

- attempt history is rendered from structured public evidence;
- a deterministic selector chooses the best prior source;
- the rendered prompt has a stable section order and exact prompt hash;
- C remains F2-only correctness repair;
- P remains F1_COMPILE-only compile repair;
- P compile logs do not flow into C prompts in v1;
- all rows produced under the new policy carry explicit policy labels.

## Research Cross-Check

This spec is intentionally conservative relative to current LLM repair-memory
patterns.

- Reflexion uses task feedback and episodic memory across trials:
  <https://arxiv.org/abs/2303.11366>
- Self-Refine uses iterative feedback and refinement at test time:
  <https://arxiv.org/abs/2303.17651>
- OWASP LLM01:2025 treats prompt injection as a first-class risk and recommends
  constrained behavior, output-format validation, input/output filtering,
  least privilege, human approval for high-risk actions, untrusted-content
  segregation, and adversarial testing:
  <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>
- OpenAI structured-output guidance recommends clear key names, schema
  descriptions, and evals for structured interfaces:
  <https://developers.openai.com/api/docs/guides/structured-outputs>

The implementation implication is narrow: keep attempt memory structured,
schema-like, deterministic, and fixture-tested; quote prior source and failure
evidence as untrusted data; keep the final instruction last; and avoid adding
model/provider dependencies to the local renderer.

## Non-Goals

This spec does not:

- make `agentic_transcript_v1` the default;
- delete or reinterpret `last_attempt_only_v1`;
- authorize Modal, GPU, generation, experiment, n=5, n=20, or paper-scale runs;
- rewrite existing JSONL artifacts;
- mix legacy and agentic rows in one output path without analyzer quarantine;
- add private eval shapes, hidden eval details, profiler data, performance data,
  timing, speedup, token-cost feedback, or billing data to repair prompts;
- make C repair F0, F1, F1_RUNTIME, or F3 failures;
- make P repair F0, F1_RUNTIME, F2, or F3 failures;
- pass raw P compile transcripts into C prompts during P-to-C handoff;
- add a new dependency or require network access.

## Local Baseline

The current implementation is last-attempt-only.

| Surface | Current behavior |
|---|---|
| C prompt builder | `cluster2.feedback.prompts.build_feedback_prompt` renders Base task, Previous source, Failure code, Feedback, Public details, Instruction. |
| C loop | `cluster2.feedback.repair_loop.run_repair_loop` stores compact source-free summaries and sends the previous failed source into the next feedback prompt. |
| P prompt builder | `cluster3.feedback.prompts.build_p_feedback_prompt` renders Base task, Previous source, Failure code, Feedback, Compile error, Instruction. |
| P loop | `cluster3.feedback.compile_error_repair.run_p_repair_loop` starts from a cached seed attempt and repairs repeated F1_COMPILE attempts from the latest failed source. |
| P policy constant | `cluster3.constants.P_HISTORY_POLICY_V1 == "last_attempt_only_v1"`. |

Any implementation of this spec must preserve exact legacy behavior when the
selected history policy is `last_attempt_only_v1` or omitted.

## Resolved Agentic Decisions

These decisions supersede the open defaults in the live state file for
implementation work.

| ID | Resolution | Implementation effect |
|---|---|---|
| D-AGENT-01 | `agentic_transcript_v1` uses a default rendered prompt budget of 24000 UTF-8 characters for local tests and development runners. The renderer must also accept an explicit positive `max_prompt_chars`. If required sections do not fit, fail closed instead of silently dropping them. | A1 adds deterministic prompt-budget tests. A2/A3 expose explicit config/CLI plumbing without hidden default changes. |
| D-AGENT-02 | The full latest failed source is excluded by default when it differs from the best anchor. It may be included only behind an explicit `include_latest_source=True` config and only if the rendered prompt stays within budget. Latest failure details are still included. | Default agentic prompts contain exactly one full prior source: the best anchor. |
| D-AGENT-03 | `agentic_transcript_v1` remains opt-in through development and paid rerun gates. | Defaults stay `last_attempt_only_v1`; run packets must name the selected policy. |
| D-AGENT-04 | P-to-C handoff does not include a P provenance note in C prompt text in v1. The C loop may record metadata that the seed source came from a post-P F2 terminal source, but C prompt-visible history starts with the C seed and public C evidence only. | A4 tests must prove no P compile-log or P transcript text appears in C prompts. |

## Policy Constants

A0 must introduce policy names without changing prompt behavior.

Required names:

```text
last_attempt_only_v1
agentic_transcript_v1
```

Required constants:

```text
LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1 = "last_attempt_only_v1"
AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1 = "agentic_transcript_v1"
REPAIR_HISTORY_POLICIES_V1 = frozenset({
    "last_attempt_only_v1",
    "agentic_transcript_v1",
})
DEFAULT_REPAIR_HISTORY_POLICY_V1 = "last_attempt_only_v1"
AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1 = 24000
```

Recommended location:

```text
cluster2/constants.py
```

Cluster 3 may keep `P_HISTORY_POLICY_V1` for schema compatibility, but it must
alias or validate against the shared policy-name constants instead of defining a
different string vocabulary.

## Policy Configuration

A1 must define a small explicit configuration object or equivalent validated
argument group for agentic rendering:

```text
repair_history_policy
max_prompt_chars
include_latest_source
```

Required defaults:

```text
repair_history_policy = "last_attempt_only_v1"
max_prompt_chars = 24000
include_latest_source = False
```

Validation rules:

```text
repair_history_policy must be in REPAIR_HISTORY_POLICIES_V1
max_prompt_chars must be a positive int and must reject bool
include_latest_source must be a bool
```

If the policy is omitted, legacy behavior remains active. If
`agentic_transcript_v1` is explicitly selected and validation fails, the
implementation must raise a typed local error before generation is called. It
must not retry or fall back to `last_attempt_only_v1`.

Configuration precedence for A2/A3 integration is fixed:

```text
direct API argument
CLI flag
config default
legacy default
```

Invalid explicit values fail closed at the earliest local boundary. Omitted
values preserve `last_attempt_only_v1`.

## Prompt Shape

The agentic prompt section order is fixed:

```text
Base task
Repair objective
Attempt history
Best previous source to repair from
Latest failure details
Instruction
```

If `include_latest_source=True`, insert this optional section after the best
source and before latest failure details:

```text
Latest failed source
```

The full best-anchor source is required. The base task is required. The
instruction is required. The latest public failure details are required for a
failed repair attempt. If any required section would be absent or truncated away,
the renderer must raise a typed prompt-budget or invalid-evidence error.

Default instruction:

```text
Produce a corrected complete Triton Python module. Do not explain. Do not
concatenate prior attempts. Use the history only to avoid repeated mistakes.
```

The renderer must not add markdown fences around source code.

## Canonical Rendering Grammar

A1 must make prompt rendering byte-stable. Golden fixtures should validate this
grammar exactly.

Section headers are rendered as:

```text
<Section name>:
```

Sections are separated by exactly one blank line. Section bodies are rendered
with LF newlines. The renderer must not normalize the Base task or selected
source text except for already-applied C/P sanitization.

The Attempt history section is sorted by ascending `attempt_index`. Each history
item is a single line:

```text
Attempt <index>: seed=<generation_seed>; source_sha256=<source_hash>; prompt_sha256=<prompt_hash_or_unavailable>; outcome=<success_or_failure_code>; level=<level_or_unknown>; anchor=<yes_or_no>; latest=<yes_or_no>; summary=<sanitized_public_summary_or_unavailable>
```

Allowed optional suffixes:

```text
; c_repair_shapes=<passed>/<total>
; c_public_eval_shapes=<passed>/<total>
; p_compile_error_type=<type>
; p_compile_error_changed=<yes_or_no>
; repeated_source_sha256=yes
```

Full source sections use explicit evidence delimiters, not markdown fences:

```text
BEGIN BEST PREVIOUS SOURCE
<selected source text>
END BEST PREVIOUS SOURCE
```

When `include_latest_source=True`, the optional latest-source section uses:

```text
BEGIN LATEST FAILED SOURCE
<latest source text>
END LATEST FAILED SOURCE
```

Latest failure details use:

```text
BEGIN LATEST FAILURE DETAILS
<sanitized public failure details>
END LATEST FAILURE DETAILS
```

If source or failure evidence contains fake section headers, fake delimiters, or
instructions to ignore later instructions, those strings remain evidence inside
their section body. They must not change renderer section order or move the
final Instruction section.

## Attempt Evidence

A1 must add a source-free evidence model plus in-memory source records. Durable
rows remain source-free unless a later schema spec says otherwise.

The preferred shared names are:

```text
RepairAttemptEvidence
RepairSourceRecord
RepairHistoryConfig
```

Equivalent names are allowed only if the A1 review checkpoint records the
mapping. `RepairAttemptEvidence` is prompt-visible public evidence. It must not
carry raw source text, private eval cases, hidden eval details, raw compile logs
outside P, raw correctness tensors, token/billing data, profiler data, timing,
or performance fields.

Required common evidence fields:

```text
attempt_index
generation_seed
failure_code
level_reached
compile_success
functional_success
repair_set_success
eval_set_success
public_failure_summary
source_hash
prompt_hash
```

Required C-specific optional fields:

```text
repair_shapes_passed
num_repair_shapes
public_eval_shapes_passed
num_public_eval_shapes
max_abs_diff
max_rel_diff
nan_or_inf_observed
shape_mismatch_observed
```

Required P-specific optional fields:

```text
compile_error_type
compile_error_excerpt_sha256
compile_error_changed_from_previous
post_compile_level_reached
```

Prompt-visible evidence must be public and sanitized by the C or P surface
before rendering. Raw source may be carried in-memory only for the current loop
so the renderer can include the selected best-anchor source.

### Public Evidence Boundary

Anchor ranking and prompt rendering may use only public attempt evidence. Hidden
or private eval details must not influence anchor ranking because that would
leak private evaluation signal into generation behavior even if the details are
not printed in the prompt.

The `public_eval_shapes_passed` and `num_public_eval_shapes` fields are allowed
only for counts that are already public under the current repair surface. If an
implementation cannot prove the counts are public, it must omit them and rank by
the remaining public fields.

Internal result rows may still record private/held-out terminal outcomes when
the existing schema allows it, but `agentic_transcript_v1` must not consume
those fields for prompt text, anchor ranking, or repair-history hashes.

### Active Repair Eligibility

An agentic repair prompt is rendered only when the latest attempt is eligible
for the active loop:

```text
C: latest failure is an F2 correctness failure eligible for C repair
P: latest failure is F1_COMPILE eligible for P repair
```

If the latest attempt succeeds, reaches a non-repairable failure, or belongs to
the other loop's failure class, the loop must not render an agentic repair
prompt and must not write prompt metadata claiming one existed.

## Best Anchor Ranking

The selector ranks previous attempts, including attempt 0. It must be stable and
fully deterministic.

General ranking order:

```text
1. Full success, only for non-active diagnostic histories; active loops stop on success and render no later repair prompt.
2. Level 2 correctness failure with the most public repair/eval shapes passed.
3. Any Level 2 correctness failure.
4. Compile failure with better P evidence.
5. Runtime failure only if a future policy authorizes it.
6. Parse/signature failure.
```

C tie-breaks:

```text
prefer higher repair_shapes_passed
prefer higher public_eval_shapes_passed only when that evidence is public
prefer lower max_abs_diff
prefer lower max_rel_diff
prefer non-NaN over NaN/Inf
prefer shape-correct over shape-mismatch
prefer later attempt only after evidence ties
```

P tie-breaks:

```text
prefer compile_success=True
prefer level_reached >= 2
prefer changed compile error type over identical repeated compile error
prefer specific public compile-error evidence over missing evidence
prefer later attempt only after evidence ties
```

The latest attempt is not automatically the anchor. If the selected anchor is
not latest, the attempt history must say which attempt is the anchor and which
attempt is latest.

## Rendering And Budget

A1 must implement rendering as a pure local operation with no Modal, Torch,
Triton, Transformers, XGrammar, or tokenizer imports.

Budget policy:

- default maximum: 24000 UTF-8 characters;
- explicit `max_prompt_chars` may override the default if positive;
- full latest source is omitted by default;
- if latest source is enabled and the prompt exceeds budget, drop only the
  optional latest-source section and recompute;
- if the prompt still exceeds budget, fail closed;
- never drop Base task, Attempt history, Best previous source, Latest failure
  details, or Instruction;
- prompt hash is SHA256 of the exact rendered string.

The implementation may use character budgets instead of tokenizer budgets in
v1. Tokenizer-derived budgets require a later observability/token integration
work package.

Budget checks count the exact rendered UTF-8 character string after all
delimiters, optional sections, and final instruction text are assembled. Prompt
hashing must use that same exact string.

## Edge-Case Contract

The implementation must make ambiguous states explicit. Do not silently fall
back to legacy prompting after an operator explicitly selects
`agentic_transcript_v1`.

### Evidence Completeness

Attempt evidence is allowed to be partial only where the missing field is
irrelevant to that attempt's failure level.

Required minimums for every rendered history item:

```text
attempt_index
generation_seed
failure_code or success marker
source_hash
```

Additional minimums by outcome:

```text
F2_*: level_reached must be 2 and public_failure_summary must be present
F1_COMPILE in P: compile_success must be False and public compile evidence must be present
F0_*: level_reached must be 0 or unavailable with a public parse/signature summary
F3_*: must not be repairable by v1 and must end the active C/P loop
success: functional_success must be True and failure_code must be None
```

If the renderer cannot produce a truthful compact history line from available
evidence, it must raise an invalid-evidence error before generation is called.

### Source Records

The loop integration must keep in-memory source records keyed by
`attempt_index`. For every rendered anchor:

```text
source_hash == sha256(source)
attempt_index exists in evidence
attempt_index exists in source records
```

Duplicate source hashes are legal. They happen when a model repeats the same
candidate. Ranking must still use attempt evidence first and later attempt only
as the final tie-break. The compact history should mark repeated source hashes
as repeated, but repeated hashes must not be deduplicated away.

Duplicate prompt hashes are also legal. They must not collapse attempts in
history or metadata.

### Seed Candidates And Attempt 0

Attempt 0 can be either newly generated by the loop or supplied as a cached seed
candidate. In both cases:

```text
attempt_index = 0
generation_seed is recorded
source_hash is recorded
attempt 0 appears in compact history before attempt 1 generation
```

When a seed candidate has no prompt text available, prompt metadata may record
the known prompt hash source, but the agentic renderer must not invent or
reconstruct the missing initial prompt. The base task remains the task prompt
passed into the loop.

If attempt 0 succeeds, no repair prompt is rendered. If attempt 0 terminates on
a non-repairable failure, no repair prompt is rendered. Those paths must not
write agentic prompt metadata claiming a rendered repair prompt existed.

### Attempt Index And Resume Semantics

Attempt indexes are contiguous and zero-based within one C or P loop. Resume or
rerun code must not append new attempts to an existing output artifact unless a
run packet explicitly authorizes resume semantics and the prior row policy,
prompt template, prompt budget, source hashes, model, tokenizer, and seed plan
match.

If any of those values differ, the run must use a new output path. Mixed resume
state must be quarantined rather than normalized into `agentic_transcript_v1`.

### Prompt Injection And Source Quoting

Prior source and public failure text are quoted evidence. The renderer must keep
the final Instruction section after all source and failure-evidence sections.

Prompt-injection test fixtures must include at least:

```text
source text that says to ignore later instructions
source text that contains fake section headers
compile/correctness text that asks for prose instead of code
public failure text that includes markdown fences
```

The rendered prompt may include those strings as evidence, but the final output
contract must remain intact and last in the prompt.

### Error Types

A1 should define typed local exceptions, or equivalent error codes, for:

```text
unsupported_history_policy
invalid_attempt_evidence
missing_anchor_source
prompt_budget_exceeded
forbidden_feedback_content
mixed_history_policy
```

A2/A3 runner integration must convert these into fail-closed local errors before
generation is invoked. They must not trigger an implicit retry under
`last_attempt_only_v1`.

### Sanitization Boundaries

The shared renderer must not import C or P sanitizers. C and P integration
layers are responsible for passing already sanitized prompt-visible evidence.
The renderer may still validate generic forbidden terms as a defense in depth,
but it must not weaken C/P-specific sanitizers or add new allowlists.

For C prompts, raw compile logs are not prompt-visible. For P prompts, raw
correctness eval details are not prompt-visible. For P-to-C handoff, neither P
compile logs nor P compact history are prompt-visible in the C prompt.

### History Summary Hash

`repair_history_summary_sha256` hashes the exact compact Attempt history section
text, excluding full source sections. This keeps the summary hash stable even
when optional latest-source inclusion changes.

`repair_prompt_sha256` hashes the exact full prompt text sent to generation,
including optional latest source when present.

### Artifact Mixing

Within one output JSONL artifact, all generated rows should share the same:

```text
repair_history_policy
repair_prompt_template_version
max_prompt_chars
include_latest_source
```

If a future runner deliberately writes mixed policies for a diagnostic, the run
packet must say so and analyzer code must quarantine mixed-policy headline
comparisons by default.

## Implementation Planning Addendum

The implementation should proceed through explicit checkpoints. These gates are
part of the A-stream readiness contract.

### Spec-Only Checkpoint

Before any code implementation starts, preserve the docs-only work as its own
reviewable checkpoint. The checkpoint should contain the A-spec, routing docs,
live state, document registry, and readiness audit. No code files, result
schemas, runners, raw outputs, or generated artifacts should be included in that
checkpoint. Later A0/A1 code diffs should be independently reviewable against
this spec-only baseline.

### Commit And Package Discipline

Implementation should be phased as reviewable commits or independently
reviewable branch slices. No commit may mix prompt core, loop integration,
analyzer changes, runner flags, result-schema changes, or output mutation.

Required slicing:

```text
commit/package 1: docs-only checkpoint
commit/package 2: A0 constants only
commit/package 3: A0.5 validation/audit only
commit/package 4: A1 prompt core only
separate commit/package: A2 C-loop integration
separate commit/package: A3 P-loop integration
separate commit/package: A4 P-to-C isolation
separate commit/package: A5 analyzer policy grouping
separate commit/package: A6 A/B gate/run-packet planning
```

Recommended commit message template:

```text
<package> <short purpose>

Scope:
- <allowed surfaces touched>

Invariance:
- last_attempt_only_v1 unchanged
- no runner/schema/output changes, unless this package explicitly owns them
- no Modal/generation

Validation:
- <commands or checks>

Risk:
- <remaining caveats or none>
```

Every package handoff must include an exit checklist:

```text
files changed
tests/checks run
default-invariance proof
forbidden-files check
no Modal/output mutation statement
unresolved risks
next blocked package or gate
```

Rollback rule: each package must remain revertible without invalidating earlier
packages. If A2 C-loop integration fails review, A1 prompt core must still
remain valid, tested, and usable by A3. If any package cannot be reverted
independently, stop and update this spec or the live state before continuing.

No opportunistic cleanup: agents must not refactor nearby prompt, loop, result,
runner, analyzer, or documentation code unless that cleanup is required for the
current package and named in the package scope. Cosmetic or broad cleanup belongs
in a separate launch packet.

### A0.5 Preflight

After A0 policy constants land and before A1 prompt-core code begins, run an
A0.5 preflight. A0.5 is a validation/checkpoint package, not a code package.

Required checks:

```text
policy constants import cheaply
new constants do not import Modal, Torch, Triton, Transformers, or XGrammar
DEFAULT_REPAIR_HISTORY_POLICY_V1 remains last_attempt_only_v1
P_HISTORY_POLICY_V1 remains last_attempt_only_v1 for compatibility
no prompt-builder or repair-loop files changed in A0
no runner behavior changed in A0
```

If any A0.5 check fails, stop before A1.

### A1 Fixture-First Gate

A1 must add golden fixtures before broad renderer implementation. At minimum,
fixtures must cover:

```text
normal C transcript
C later regression where an earlier F2 attempt is the better anchor
repeated source hash kept as separate attempts
P repeated F1_COMPILE with changed and unchanged error class
prompt-injection source text with fake section headers
over-budget fail-closed rendering
legacy last_attempt_only_v1 untouched baseline prompt
```

Implementation may start with fixture builders, but final A1 acceptance must
include fixed golden prompt text or exact fixture hashes. Generated fixtures must
be deterministic and reviewed before A2/A3 loop integration.

A1 must also add a fixture acceptance manifest before closing the package. The
manifest should live under `shared/tests/fixtures/repair_history/` and list, for
each golden prompt case:

```text
fixture_id
loop_kind
history_policy
expected_anchor_attempt_index
expected_latest_attempt_index
expected_prompt_sha256
expected_history_summary_sha256
include_latest_source
expected_render_error_code or none
legacy_prompt_byte_invariance_expected
```

The manifest is the reviewable source of truth for A1 golden fixtures. Renderer
tests may compute hashes from golden prompt files, but they must compare those
computed values to the manifest instead of accepting newly generated hashes
implicitly.

### Legacy Byte-Invariance Snapshot

A1 must record exact representative legacy prompt bytes for the current
`last_attempt_only_v1` C and P prompt builders before any integration work. The
snapshot may be a golden text fixture, exact SHA256 fixture, or both, but it
must be stable enough for A2/A3 to prove:

```text
omitted policy keeps legacy C prompt bytes unchanged
explicit last_attempt_only_v1 keeps legacy C prompt bytes unchanged
omitted policy keeps legacy P prompt bytes unchanged
explicit last_attempt_only_v1 keeps legacy P prompt bytes unchanged
```

If legacy prompt bytes need to change for any reason, stop and update this spec
plus the live state before continuing.

### Prompt-Core Import Isolation

A1 must add an import-boundary test or equivalent scan proving
`shared/repair_history/*` imports no generation clients, tokenizer packages,
provider SDKs, Modal, Torch, Triton, Transformers, XGrammar, CUDA helpers, or
runner modules. The prompt core should depend only on the Python standard
library and local pure data helpers. Any broader dependency requires a spec
amendment before implementation proceeds.

### Legacy And Migration Test Plan

A1/A5 must define test rows or fixtures for policy classification:

```text
explicit repair_history_policy=last_attempt_only_v1
explicit repair_history_policy=agentic_transcript_v1
missing policy on known legacy artifact
missing policy on unknown artifact
mixed policy values in one artifact
mixed max_prompt_chars or include_latest_source in one artifact
```

Known legacy missing-policy rows load as `last_attempt_only_v1`; unknown
missing-policy rows load as `unknown_legacy`; explicit agentic rows load as
`agentic_transcript_v1`; mixed policy or prompt-budget settings quarantine
headline comparisons. No implementation may relabel missing-policy rows as
`agentic_transcript_v1`.

### Implementation Stop Triggers

Stop implementation and update this spec or the live state before continuing if
any of these occur:

```text
A1 cannot preserve legacy prompt bytes for last_attempt_only_v1
renderer needs tokenizer, Torch, Triton, Modal, Transformers, or XGrammar imports
required metadata implies a larger result-schema migration than A2/A3 allow
prompt budget requires dropping required sections
agentic rendering would need private eval or P-to-C compile-log leakage
runner integration needs hidden retries or implicit fallback to last_attempt_only_v1
analyzer grouping cannot separate legacy and agentic rows
```

### A1 Review Checkpoint

A1 is the architecture checkpoint for the A-stream. Before A2 or A3 begins,
review and record the attempt evidence model, anchor ranking, rendered prompt
sections, prompt/history hash definitions, prompt-injection fixture behavior,
over-budget behavior, legacy prompt byte-invariance evidence, and cheap-import
evidence.

If the review changes prompt wording, ranking, metadata names, or budget
semantics, update this spec and the document registry before integration work.

## Package Rollout

| Package | Scope | Behavior change | Output/run behavior |
|---|---|---|---|
| A0 policy constants | Add policy names, validation helpers, and default-policy tests. | None. | No runs or output mutation. |
| A0.5 preflight | Validate A0 default invariance and cheap-import boundaries before A1. | None. | No runs or output mutation. |
| A1 prompt core | Add evidence model, anchor selector, renderer, golden prompts, budget tests, injection tests, and prompt hash tests. | None in runners. | No runs or output mutation. |
| A2 C-loop integration | Add opt-in C policy plumbing and metadata. | Only when explicitly selected. | No Modal run by implementation alone. |
| A3 P-loop integration | Add opt-in P policy plumbing and metadata. | Only when explicitly selected. | No Modal run by implementation alone. |
| A4 P-to-C isolation | Prove C history starts from the C seed and excludes P compile logs. | Only metadata/handoff semantics. | No Modal run by implementation alone. |
| A5 analyzer policy grouping | Add analyzer grouping/quarantine for mixed repair policies. | Analyzer behavior only. | No raw output rewrite without approval. |
| A6 A/B gates | Define local and development-scale comparison gates. | Spec and run-packet work only. | Any run requires explicit approval. |

## Package Boundaries

### A0 Allowed Files

```text
cluster2/constants.py
cluster3/constants.py
cluster2/tests/test_cluster2_boundary.py
cluster3/tests/test_cluster3_imports.py
```

A0 must not edit prompt builders, repair loops, runners, result schemas, Modal
code, outputs, or analysis code.

### A0.5 Allowed Files

A0.5 should not edit code. It may update only:

```text
audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
```

if validation evidence or package status needs to be recorded.

### A1 Allowed Files

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

A1 may update this spec, the live state file, the document hub, and the
document registry if implementation details are amended.

A1 must not edit C/P repair loops, runner CLIs, Modal code, result schemas,
analyzers, or outputs.

### A2 Allowed Files

```text
cluster2/feedback/prompts.py
cluster2/feedback/repair_loop.py
cluster2/feedback/trace.py
cluster2/experiments/run_cluster2_modal.py
cluster2/results/dataclass.py
cluster2/tests/test_feedback_prompts.py
cluster2/tests/test_repair_loop.py
cluster2/tests/test_results_logger.py
cluster2/tests/test_run_cluster2_modal.py
```

A2 must take the C-loop and Cluster 2 runner serialized-surface leases before
editing loop or runner files.

### A3 Allowed Files

```text
cluster3/feedback/prompts.py
cluster3/feedback/compile_error_repair.py
cluster3/feedback/trace.py
cluster3/experiments/run_cluster3_modal.py
cluster3/results/dataclass.py
cluster3/tests/test_p_repair_loop.py
cluster3/tests/test_p_prompts.py
cluster3/tests/test_cluster3_schema.py
cluster3/tests/test_run_cluster3_modal_cli.py
```

A3 must take the P-loop and Cluster 3 runner serialized-surface leases before
editing loop or runner files.

### A4 Allowed Files

```text
cluster3/feedback/c_loop_adapter.py
cluster3/tests/test_correctness_runner_adapter.py
cluster3/tests/test_p_repair_loop.py
cluster3/tests/test_cluster3_trace.py
```

A4 may also add focused C/P isolation tests in the A2/A3 test files if those
leases are held.

### A5 Allowed Files

```text
shared/analysis/factorial.py
shared/tests/test_factorial_analysis.py
shared/tests/fixtures/analysis/
docs/17_structural_task_analyzer_metadata_implementation_spec.md
```

A5 must coordinate with the S1 analyzer-metadata stream and take the analyzer
serialized-surface lease.

## Metadata Requirements

Rows generated under C or P after A2/A3 must include explicit policy metadata.
Fields may be nullable/defaultable for legacy rows.

Common fields:

```text
repair_history_policy
repair_prompt_template_version
repair_prompt_renderer_version
repair_anchor_attempt_index
repair_latest_attempt_index
repair_history_attempt_count
repair_prompt_sha256
repair_prompt_char_count
repair_max_prompt_chars
repair_include_latest_source
repair_anchor_source_hash
repair_latest_source_hash
repair_history_summary_sha256
repair_history_error_code
```

Cluster 3 P fields:

```text
p_history_policy
p_repair_anchor_attempt_index
p_repair_latest_attempt_index
p_repair_prompt_sha256
p_repair_prompt_char_count
p_repair_max_prompt_chars
p_repair_include_latest_source
```

Cluster 3 C-loop fields:

```text
c_history_policy
c_repair_anchor_attempt_index
c_repair_latest_attempt_index
c_repair_prompt_sha256
c_repair_prompt_char_count
c_repair_max_prompt_chars
c_repair_include_latest_source
c_terminal_prompt_hash_source = "c_repair_prompt"
```

Old rows without these fields must load as `last_attempt_only_v1` when they are
known legacy rows, or as `unknown_legacy` if provenance is insufficient.

For failed pre-generation rendering, the result path must either fail the run
before writing a scientific row or write an explicit infrastructure/error row
only if that row schema already supports it. Do not write a normal failed kernel
row that looks like a model attempt when generation was never called.

### Metadata Nullability Matrix

A2/A3 must define and test a metadata nullability matrix before changing result
schemas or row builders. The matrix must classify every new repair-history field
as required, nullable, defaulted, or absent for:

```text
omitted policy / legacy default path
explicit repair_history_policy=last_attempt_only_v1
explicit repair_history_policy=agentic_transcript_v1
failed pre-generation render
attempt 0 success
attempt 0 terminal non-repairable failure
known legacy row missing policy
unknown artifact row missing policy
```

Required principle: `agentic_transcript_v1` rows must carry enough metadata to
identify policy, prompt template, anchor attempt, latest attempt, prompt hash,
prompt budget, and latest-source inclusion. Legacy/default rows must not be
silently relabeled as agentic, and missing prompt metadata must be explained by
the matrix rather than inferred later by analyzers.

## Tests Required

A0:

```text
policy constants import cheaply
default history policy is last_attempt_only_v1
agentic_transcript_v1 is a recognized but non-default policy
Cluster 3 P_HISTORY_POLICY_V1 remains last_attempt_only_v1
```

A0.5:

```text
A0 changed only allowed constants/tests files
A0 did not touch prompt builders, repair loops, runners, schemas, or outputs
cheap-import checks pass for constants modules
default policy and P compatibility policy remain last_attempt_only_v1
```

A1:

```text
configuration validation rejects unknown policies, bool max_prompt_chars, non-positive max_prompt_chars, and non-bool include_latest_source
fixture-first golden prompt cases exist before broad renderer integration
fixture acceptance manifest lists expected anchor/latest attempts, prompt/history hashes, latest-source setting, render error code, and legacy byte-invariance expectation
legacy C and P last_attempt_only_v1 byte snapshots exist before integration work
prompt-core import isolation rejects generation clients, provider SDKs, tokenizer packages, Modal, Torch, Triton, Transformers, XGrammar, CUDA helpers, and runner imports
canonical rendering grammar is byte-for-byte stable, including section headers, blank lines, source delimiters, and final Instruction placement
evidence validation rejects malformed attempt indexes, hashes, and failure codes
evidence validation rejects non-contiguous rendered histories
evidence validation rejects F2 history without Level 2 evidence
evidence validation rejects P F1_COMPILE history without compile evidence
evidence validation rejects private eval, token, billing, timing, profiler, performance, or raw cross-loop fields in prompt-visible evidence
anchor selection ranks better F2 evidence above later F1/F0 regressions
anchor selection tie-breaks only by later attempt after evidence ties
anchor selection ignores private/hidden eval signal
anchor selection preserves repeated source hashes as separate attempts
P compile-success evidence beats repeated F1_COMPILE
renderer includes base task verbatim
renderer includes all compact attempts
renderer includes best-anchor source in full
renderer excludes latest full source by default
renderer optionally includes latest source only within budget
renderer fails closed when required sections exceed budget
renderer never silently falls back to last_attempt_only_v1 after explicit agentic selection
prompt hash equals exact rendered prompt text
history summary hash equals exact Attempt history section text
prompt-injection fixture cannot remove the final output contract
prompt-injection fixture cannot make fake section headers override renderer section order
success or non-repairable latest attempt produces no agentic repair prompt metadata
legacy last_attempt_only_v1 prompt fixture remains byte-for-byte unchanged
policy-classification fixtures cover explicit, missing-known-legacy, missing-unknown, and mixed-policy rows
```

A2/A3:

```text
legacy default prompts are byte-for-byte unchanged
agentic policy is selected only through explicit config/CLI/API argument
config precedence is direct API argument, then CLI flag, then config default, then legacy default
omitted policy, explicit last_attempt_only_v1, explicit agentic_transcript_v1, invalid policy, invalid budget, and invalid include_latest_source are covered by CLI/API/default tests
metadata nullability matrix covers legacy default, explicit legacy, explicit agentic, failed pre-generation render, attempt 0 success, attempt 0 terminal non-repairable failure, known legacy missing-policy rows, and unknown missing-policy rows
attempt 1 receives history for attempt 0
later attempts receive compact history for all previous attempts
metadata records selected anchor and latest attempt
metadata records max_prompt_chars and include_latest_source
rendering errors fail before generation is invoked
C still terminates non-F2 failures without feedback
P still repairs only F1_COMPILE
forbidden C/P feedback terms fail closed
seed-candidate attempt 0 appears in history before attempt 1 generation
attempt 0 success or terminal non-repairable failure writes no repair prompt metadata
```

A4:

```text
C prompt after P-to-C handoff excludes P compile error text
C prompt after P-to-C handoff excludes P attempt history text
C metadata may record post_p_f2 source provenance without prompt-visible P logs
```

A5:

```text
analyzer separates last_attempt_only_v1 and agentic_transcript_v1 rows
analyzer rejects or quarantines mixed-policy headline comparisons
analyzer fixture with both last_attempt_only_v1 and agentic_transcript_v1 rows proves headline metrics are quarantined by default
legacy rows without explicit policy are not labeled agentic_transcript_v1
mixed max_prompt_chars or include_latest_source values are reported as mixed prompt policy
```

## Run And Artifact Rules

No implementation package may execute paid Modal work by itself. Any smoke,
development-scale, n=5, n=20, paper-scale, or output-mutating run requires a
fresh approval packet naming:

```text
repair_history_policy
prompt_template_version
max_prompt_chars
include_latest_source
output path
condition
kernel class
dtype
n
model id and revision
tokenizer revision
observability policy
stop conditions
expected cost or unavailable reason
```

New agentic artifacts must not share an output path with legacy
`last_attempt_only_v1` artifacts.

## Acceptance Criteria

Before C/P integration starts:

- the spec-only checkpoint is reviewable separately from code changes;
- A0 and A1 tests pass;
- A0.5 preflight passes after A0 and before A1;
- A1 fixture-first and review checkpoints are recorded;
- G5 prompt-core gate is satisfied;
- this spec and the live state file agree on D-AGENT decisions;
- no default prompt behavior has changed.

Before any agentic run:

- G6 integration gate is satisfied;
- analyzer policy grouping or quarantine exists;
- run packet explicitly selects `agentic_transcript_v1`;
- prompt hashes and policy labels are present;
- C/P boundary tests pass;
- no private eval or performance/profiler/timing/speedup leakage is detected.
