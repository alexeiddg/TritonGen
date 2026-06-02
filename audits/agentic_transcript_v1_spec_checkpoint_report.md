# Agentic Transcript v1 Spec Checkpoint Report

- Date: 2026-06-02
- Phase: A-SPEC docs-only checkpoint and readiness alignment
- Branch inspected: `codex/llm-repair-memory-agentic-transcript-v1`
- Worktree inspected: `/private/tmp/tritongen-llm-repair-memory`
- Baseline branch checked: `codex-track-handoff-context`
- Requested repository root: `/Users/alexeidelgado/Desktop/TritonGen`
- Classification: `A_SPEC_READY_FOR_A0_WITH_WORKTREE_CAVEATS`
- Readiness audit reconciliation: `aligned_with_spec`
- Modal/output mutation performed: no
- Code implementation performed: no

## Executive Summary

The Agentic Transcript v1 docs-only checkpoint is reviewable and aligned enough
to start the first implementation package, A0 policy constants, from the feature
worktree.

`docs/18_agentic_transcript_v1_implementation_spec.md` v0.1.5 is the primary
implementation contract. It keeps `agentic_transcript_v1` opt-in, preserves
`last_attempt_only_v1` as the default, defines the A0-A6 package sequence, and
sets hard boundaries for prompt rendering, metadata, analyzer grouping, and run
approval.

The requested repository root at `/Users/alexeidelgado/Desktop/TritonGen` is
clean but remains on `codex-track-handoff-context` and does not contain
`docs/18_agentic_transcript_v1_implementation_spec.md`. The complete A-spec
checkpoint exists in `/private/tmp/tritongen-llm-repair-memory` on
`codex/llm-repair-memory-agentic-transcript-v1`.

## Preflight Git Status

Requested root:

```text
worktree: /Users/alexeidelgado/Desktop/TritonGen
branch: codex-track-handoff-context
git status --short: clean
docs/18_agentic_transcript_v1_implementation_spec.md: missing
```

Feature worktree used for this checkpoint:

```text
worktree: /private/tmp/tritongen-llm-repair-memory
branch: codex/llm-repair-memory-agentic-transcript-v1
git status --short before this checkpoint: clean
required source docs: present
```

The root/worktree mismatch is not an A0 implementation blocker as long as A0
starts from `/private/tmp/tritongen-llm-repair-memory`. It does mean the docs
are not yet mirrored onto the `codex-track-handoff-context` checkout.

## Source Docs Inspected

- `docs/00_project_map.md`
- `docs/13_agentic_repair_memory_strategy.md`
- `docs/15_experiment_change_orchestration_contract.md`
- `docs/18_agentic_transcript_v1_implementation_spec.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md`

Additional reference scan:

```text
rg -n "agentic_transcript_v1|last_attempt_only_v1|A0|A0.5|A1 prompt core|repair_history_policy|repair memory|serialized-surface lease" docs audits .contracts cluster2 cluster3 shared
```

Result: expected references in the A-stream docs, routing docs, readiness
report, and the existing Cluster 3 compatibility constant
`cluster3.constants.P_HISTORY_POLICY_V1 == "last_attempt_only_v1"`. No existing
runtime implementation of `agentic_transcript_v1` was found.

## Spec Alignment Status

Status: aligned.

`docs/00_project_map.md` places Agentic Transcript v1 in the planning/spec
navigation map and does not change Cluster 1, Cluster 2, or Cluster 3 ownership
boundaries.

`docs/13_agentic_repair_memory_strategy.md` agrees with the v0.1.5 spec at the
strategy level: repair memory is structured, prompt-visible, deterministic,
public-evidence-only, and separately labeled from legacy artifacts. Open
strategy defaults are superseded for implementation by the resolved decisions in
`docs/18`.

`docs/15_experiment_change_orchestration_contract.md` agrees with the spec on
sequencing, serialized-surface leases, default invariance, no-run policy, and
the requirement that analyzer grouping/quarantine exist before headline mixed
policy comparisons.

`docs/18_agentic_transcript_v1_implementation_spec.md` is the authoritative
A0-A6 implementation contract.

`docs/handoff/agentic_document_hub.md` routes Cluster 2 C feedback work and
Cluster 3/P work through `docs/18`; no read-order change is required for this
checkpoint.

`docs/handoff/document_version_registry.md` already registers the v0.1.5 spec
and the readiness report. This checkpoint adds a new registry entry for this
audit.

`docs/handoff/experiment_change_orchestration_state.md` agrees with the
D-AGENT decisions in the spec. No `A_SPEC_BLOCKED_DOC_STATE_AMBIGUOUS` condition
was found.

`audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md` is
compatible with the implementation spec. Its earlier missing-spec finding is
historical and resolved by `docs/18`.

## Package Rollout Status

Required package order:

```text
docs-only checkpoint
A0 constants only
A0.5 validation/audit only
A1 prompt core only
A2 C-loop integration
A3 P-loop integration
A4 P-to-C isolation
A5 analyzer policy grouping
A6 A/B gate/run-packet planning
```

Current status:

```text
docs-only checkpoint: complete after this report
A0 policy constants: ready to start from feature worktree
A0.5 preflight: blocked until A0 lands
A1 prompt core: blocked until A0.5 passes
A2/A3 integration: blocked until A1 review checkpoint passes and leases are held
A4 isolation: blocked until A2/A3 contracts are stable
A5 analyzer grouping: blocked until analyzer lease and S1 coordination
A6 gate/run-packet planning: blocked until integration and grouping are stable
```

## A0 Readiness Checklist

A0 may modify only:

```text
cluster2/constants.py
cluster3/constants.py
cluster2/tests/test_cluster2_boundary.py
cluster3/tests/test_cluster3_imports.py
```

A0 must not edit:

```text
prompt builders
repair loops
runners
result schemas
Modal code
outputs
analysis code
shared code outside the package scope
```

A0 required checks:

```text
policy constants import cheaply
default history policy is last_attempt_only_v1
agentic_transcript_v1 is a recognized but non-default policy
Cluster 3 P_HISTORY_POLICY_V1 remains last_attempt_only_v1
```

A0 entry recommendation: proceed only in
`/private/tmp/tritongen-llm-repair-memory` or in a new branch/worktree created
from the current A-spec checkpoint.

## Boundary And Non-Goal Verification

Verified boundaries:

```text
default remains last_attempt_only_v1
agentic_transcript_v1 remains opt-in
C remains F2-only correctness repair
P remains F1_COMPILE-only compile repair
P compile logs do not enter C prompts in v1
private eval / hidden shape details do not enter prompts
private eval / hidden shape details do not enter anchor ranking
old rows are not relabeled agentic_transcript_v1
mixed policy rows must be grouped or quarantined before headline comparison
```

Verified non-goals for this checkpoint:

```text
no Modal
no GPU jobs
no generation
no experiments
no n=5
no n=20
no paper-scale work
no output mutation
no profiler, timing, speedup, performance, or benchmark work
no policy constants added yet
no code implementation started
```

## Required Implementation Surfaces

A0 allowed files:

```text
cluster2/constants.py
cluster3/constants.py
cluster2/tests/test_cluster2_boundary.py
cluster3/tests/test_cluster3_imports.py
```

A0.5 allowed files:

```text
audits/llm_repair_memory_agentic_transcript_v1_readiness_report.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
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

A2 allowed files:

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

A3 allowed files:

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

A4 allowed files:

```text
cluster3/feedback/c_loop_adapter.py
cluster3/tests/test_correctness_runner_adapter.py
cluster3/tests/test_p_repair_loop.py
cluster3/tests/test_cluster3_trace.py
```

A5 allowed files:

```text
shared/analysis/factorial.py
shared/tests/test_factorial_analysis.py
shared/tests/fixtures/analysis/
docs/17_structural_task_analyzer_metadata_implementation_spec.md
```

## Implementation Stop Triggers

Stop implementation and update the spec or live state if:

```text
legacy prompt bytes cannot be preserved
renderer needs Modal/Torch/Triton/Transformers/XGrammar/tokenizer imports
required metadata implies broader schema migration than A2/A3 allow
prompt budget requires dropping required sections
private eval leakage would be needed
P-to-C compile-log leakage would be needed
runner integration needs hidden retries or implicit fallback to last_attempt_only_v1
analyzer cannot quarantine mixed policies
```

## Tests Run

Required relative worktree interpreter check:

```bash
.venv/bin/python --version
```

Result in `/private/tmp/tritongen-llm-repair-memory`:

```text
zsh:1: no such file or directory: .venv/bin/python
```

The requested `.venv/bin/python` is present in the baseline checkout, not in the
feature worktree. To avoid system Python, the two requested sanity tests were
run from the feature worktree using the baseline venv interpreter:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
```

Result:

```text
15 passed in 0.04s
```

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -v
```

Result:

```text
25 passed, 1 skipped in 0.79s
```

No broad implementation tests, Modal runs, GPU jobs, generation, experiments,
n=5, n=20, or paper-scale commands were run.

## Negative Scope Verification

Pre-edit worktree diff:

```bash
git diff --name-only
```

Result:

```text
no output
```

Allowed changed files for this phase:

```text
audits/agentic_transcript_v1_spec_checkpoint_report.md
docs/handoff/document_version_registry.md
docs/handoff/experiment_change_orchestration_state.md
```

Forbidden surfaces not modified by this checkpoint:

```text
cluster1/
cluster2/
cluster3/
shared/
outputs/
prompt builders
repair loops
runners
result schemas
analyzers
```

## Files Modified

```text
audits/agentic_transcript_v1_spec_checkpoint_report.md
docs/handoff/document_version_registry.md
docs/handoff/experiment_change_orchestration_state.md
```

## Classification

```text
A_SPEC_READY_FOR_A0_WITH_WORKTREE_CAVEATS
```

The checkpoint is ready for A0 from the feature worktree. The only caveats are:

```text
the requested root checkout does not contain docs/18 yet
the feature worktree does not have a local .venv/bin/python
```

Neither caveat changes the implementation spec or the A0 package boundaries.

## Next-Step Recommendation

Start A0 policy constants as the next package from
`/private/tmp/tritongen-llm-repair-memory`, preserving the package boundary in
`docs/18_agentic_transcript_v1_implementation_spec.md`.

Do not start A1 until A0 lands and A0.5 verifies default invariance, cheap
imports, and forbidden-file boundaries.
