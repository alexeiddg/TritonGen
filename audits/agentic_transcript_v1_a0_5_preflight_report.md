# Agentic Transcript v1 A0.5 Preflight Report

- Date: 2026-06-02
- Phase: A0.5 - Agentic Transcript v1 constants preflight validation
- Classification: `A0_5_PREFLIGHT_COMPLETE_WITH_WORKTREE_CAVEATS`
- Repository root: `/private/tmp/tritongen-llm-repair-memory`
- Baseline worktree: `/Users/alexeidelgado/Desktop/TritonGen`
- Baseline branch: `codex-track-handoff-context`
- Feature branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Baseline venv interpreter:
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`

## Executive Summary

A0.5 validated the A0 constants package without modifying code, outputs,
schemas, prompt builders, repair loops, runners, analyzers, Modal surfaces, or
shared repair-history renderer code.

A0 commit `1e3f44468c5ae91e6467b42b7f93a068fa6acf5f` changed exactly the four
expected files:

```text
cluster2/constants.py
cluster2/tests/test_cluster2_boundary.py
cluster3/constants.py
cluster3/tests/test_cluster3_imports.py
```

The new policy vocabulary recognizes both `last_attempt_only_v1` and
`agentic_transcript_v1`, while the default remains `last_attempt_only_v1`.
Cluster 3 remains pinned to `P_HISTORY_POLICY_V1 = "last_attempt_only_v1"`.
The constants import without loading Modal, Torch, Triton, Transformers, or
XGrammar.

## Worktree Status

Before report creation:

```text
git status --short
<empty>

git branch --show-current
codex/llm-repair-memory-agentic-transcript-v1

git rev-parse HEAD
1e3f44468c5ae91e6467b42b7f93a068fa6acf5f
```

The A0.5 report was created from a clean feature worktree at the A0 commit.

## Baseline/Feature Branch Status

Baseline worktree:

```text
worktree: /Users/alexeidelgado/Desktop/TritonGen
branch: codex-track-handoff-context
HEAD: aa4d20f1f5c64932e72b488d131244542e44459f
git status --short: <empty>
```

Feature worktree:

```text
worktree: /private/tmp/tritongen-llm-repair-memory
branch: codex/llm-repair-memory-agentic-transcript-v1
HEAD: 1e3f44468c5ae91e6467b42b7f93a068fa6acf5f
merge-base with codex-track-handoff-context:
aa4d20f1f5c64932e72b488d131244542e44459f
```

Recent feature history:

```text
1e3f444 (HEAD -> codex/llm-repair-memory-agentic-transcript-v1) A0 - Add repair history policy constants
bfcee79 A-SPEC - Checkpoint agentic transcript v1 readiness
3131986 Add agentic transcript repair-memory implementation spec
aa4d20f (origin/codex-track-handoff-context, codex-track-handoff-context) docs: track handoff context
0578bd2 (origin/main, main) Phase 13b - Commit and Provenance Freeze Verification
```

## A0 Commit Inspected

Inspected commit:

```text
1e3f44468c5ae91e6467b42b7f93a068fa6acf5f
```

Required prior docs exist:

```text
audits/agentic_transcript_v1_spec_checkpoint_report.md
docs/18_agentic_transcript_v1_implementation_spec.md
```

## A0 Changed-Files Validation

`git show --name-only --oneline --stat 1e3f444` and
`git diff-tree --no-commit-id --name-only -r 1e3f444` both reported exactly:

```text
cluster2/constants.py
cluster2/tests/test_cluster2_boundary.py
cluster3/constants.py
cluster3/tests/test_cluster3_imports.py
```

No other file was changed by A0.

## Constants Validation

Command:

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python - <<'PY'
...
PY
```

Observed output:

```text
LAST_ATTEMPT_ONLY_REPAIR_HISTORY_POLICY_V1 last_attempt_only_v1
AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1 agentic_transcript_v1
REPAIR_HISTORY_POLICIES_V1 ['agentic_transcript_v1', 'last_attempt_only_v1']
DEFAULT_REPAIR_HISTORY_POLICY_V1 last_attempt_only_v1
AGENTIC_TRANSCRIPT_MAX_PROMPT_CHARS_V1 24000
P_HISTORY_POLICY_V1 last_attempt_only_v1
forbidden_imports []
```

All assertions passed.

## Default-Invariance Proof

The validation command asserted:

```text
DEFAULT_REPAIR_HISTORY_POLICY_V1 == "last_attempt_only_v1"
AGENTIC_TRANSCRIPT_REPAIR_HISTORY_POLICY_V1 == "agentic_transcript_v1"
REPAIR_HISTORY_POLICIES_V1 == frozenset({
    "last_attempt_only_v1",
    "agentic_transcript_v1",
})
```

This proves `agentic_transcript_v1` is recognized but remains non-default at
the constants layer. A0 did not edit prompt builders, repair loops, runners,
schemas, analyzers, Modal code, or outputs.

## Cluster 3 Compatibility Proof

The validation command asserted:

```text
cluster3.constants.P_HISTORY_POLICY_V1 == "last_attempt_only_v1"
cluster3.constants.P_HISTORY_POLICY_V1 in cluster2.constants.REPAIR_HISTORY_POLICIES_V1
```

Focused Cluster 3 import tests also passed. Cluster 3 therefore keeps the
legacy repair-history policy while sharing the Cluster 2 policy vocabulary.

## Cheap-Import Proof

The constants import check imported only `cluster2.constants` and
`cluster3.constants`, then scanned newly loaded modules for forbidden roots:

```text
modal
torch
triton
transformers
xgrammar
```

Observed forbidden imports:

```text
[]
```

Optional prompt/loop import-only sanity also passed:

```text
prompt_and_loop_imports_ok
```

No generation, Modal invocation, GPU job, experiment, or output mutation was
run.

## Tests Run

Focused tests:

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -v
26 passed, 1 skipped in 0.57s

/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v
15 passed in 0.02s
```

Optional import sanity:

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python - <<'PY'
import cluster2.feedback.prompts
import cluster2.feedback.repair_loop
import cluster3.feedback.prompts
import cluster3.feedback.compile_error_repair
print("prompt_and_loop_imports_ok")
PY
prompt_and_loop_imports_ok
```

## Forbidden-Surface Scan

Command:

```text
git diff --name-only 1e3f444^..1e3f444 -- \
  cluster2/feedback \
  cluster2/experiments \
  cluster2/results \
  cluster3/feedback \
  cluster3/experiments \
  cluster3/results \
  shared \
  outputs \
  docs \
  audits
```

Observed output:

```text
<empty>
```

A0 did not touch forbidden prompt, loop, runner, schema, analyzer, shared,
output, docs, or audit surfaces.

## Negative Scope Verification

A0.5 did not:

- invoke Modal;
- run GPU work;
- run generation;
- run experiments;
- run n=5, n=20, or paper-scale work;
- modify `outputs/`;
- edit prompt builders;
- edit repair loops;
- edit runners;
- edit result schemas;
- edit analyzers;
- edit Modal code;
- edit `shared/repair_history`;
- implement A1 renderer logic;
- add metadata fields;
- change default behavior.

## Files Modified

A0.5 created or updated only:

```text
audits/agentic_transcript_v1_a0_5_preflight_report.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
```

No code or output files were modified in A0.5.

## Classification

`A0_5_PREFLIGHT_COMPLETE_WITH_WORKTREE_CAVEATS`

All required validations passed. The caveat remains that the feature worktree
does not have its own `.venv/bin/python`; A0.5 used the required baseline venv
interpreter at `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`.

## Next-Step Recommendation

Preserve the A0.5 checkpoint before starting A1. After preservation, A1 prompt
core may begin from `codex/llm-repair-memory-agentic-transcript-v1` with the
allowed A1 files in `docs/18_agentic_transcript_v1_implementation_spec.md`.
A1 must remain pure/local and must not edit C/P loops, runners, Modal code,
result schemas, analyzers, or outputs.
