# L2b-2 Post-Recovery Dirty Worktree Reconciliation Report

## Executive Summary

This audit reconciles the dirty worktree that remained after commit
`fbe835c61b560f174f5e4ec02ae448e61b6b19a2` archived the L2b-2 missing-28
recovery result. No Modal launch, GPU execution, experiment execution, output
mutation, artifact mutation, MLflow mutation, or billing query was performed.

Classification:
`L2B_N2_POST_RECOVERY_BASELINE_CLEAN_READY_FOR_L2B4_AUTHORIZATION`.

The remaining source and test diffs are required recovery runtime fixes or
test-only support for the already-completed missing-28 recovery launch path.
They are safe to carry as source/test baseline because they preserve create-only
recovery semantics and do not authorize L2b-4 execution.

## Baseline

- Branch: `codex-track-handoff-context`
- Required baseline: `fbe835c61b560f174f5e4ec02ae448e61b6b19a2`
- Phase: Reconcile Dirty Worktree After L2b-2 Recovery - No Execution
- Local interpreter: `.venv/bin/python`

## Dirty Diff Summary

`git diff --stat` before reconciliation showed:

```text
cluster3/experiments/run_cluster3_modal.py    | 257 +++++++++++++++++++++++---
cluster3/planning/grammar_mode_matrix.py      |  54 ++++--
cluster3/results/logger.py                    |  22 ++-
cluster3/tests/test_run_cluster3_modal_cli.py |  34 +++-
shared/observability/logger.py                |  26 ++-
5 files changed, 349 insertions(+), 44 deletions(-)
```

No dirty changes were present in
`cluster3/tests/test_grammar_mode_matrix.py`.

## Change Classification

### `cluster3/experiments/run_cluster3_modal.py`

Classification: `REQUIRED_RECOVERY_RUNTIME_FIX`.

The diff adds the signed missing-28 recovery token aliases, recovery output and
artifact namespace roots, create-mode selection for that token, recovery-token
selector-profile routing, no-`--overwrite` validation for signed recovery, and
prelaunch validation that recovery scope targets exactly one authorized missing
shard/cell subset. It also routes recovery commands into the dedicated
`l2b_n2_recovery_missing28` namespaces.

The Modal DNS preflight is classified as `REQUIRED_RECOVERY_RUNTIME_FIX` for the
recovery launch surface because it fails before Modal dispatch when the local
machine cannot resolve Modal. It does not authorize execution.

### `cluster3/planning/grammar_mode_matrix.py`

Classification: `REQUIRED_RECOVERY_RUNTIME_FIX`.

The diff allows L2b full-coverage shard planning to receive explicit output,
observability, analysis, reports, and billing roots. This is required for
recovery commands to target the recovery namespace instead of the base L2b-2
archive namespace. It also suppresses `--overwrite` for signed missing-28
recovery command construction.

### `cluster3/results/logger.py`

Classification: `REQUIRED_RECOVERY_RUNTIME_FIX`.

The diff adds `create` mode for result JSONL logging. This mode requires both
the JSONL output and hash sidecar to be absent and opens the output with
exclusive creation. It is required to support recovery without overwrite or
resume semantics.

### `shared/observability/logger.py`

Classification: `REQUIRED_OBSERVABILITY_CREATE_MODE_FIX`.

The diff adds `create` mode for observability sidecars. This mode requires the
event, hash, and summary sidecars to be absent and creates a fresh event file
with an initial hash sidecar. It is required for recovery sidecar creation
without overwriting existing observability artifacts.

### `cluster3/tests/test_run_cluster3_modal_cli.py`

Classification: `TEST_ONLY_SUPPORT`.

The diff updates recovery prelaunch tests to use the signed recovery packet
token, adjusts one namespace-escape expected error to match the strengthened
namespace validation path, and adds tests for the Modal DNS preflight helper.

## L2b-4 Safety Assessment

No dirty diff signs or authorizes L2b-4. The changes are limited to:

- L2b-2 missing-28 recovery token recognition.
- Recovery namespace routing.
- create-only output and sidecar write mode.
- Local prelaunch validation and DNS preflight.
- Targeted tests.

No L2b-4/n20 output, artifact, billing, MLflow, dependency, or preliminary
report surface was modified.

## Validation

Requested validation was run locally only:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
224 passed

.venv/bin/python -m compileall -q cluster3 shared
passed

git diff --check
passed
```

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result: empty output.

## No Execution Proof

The only commands run for this reconciliation were git inspection, local pytest,
local compileall, diff whitespace checks, protected mutation scans, audit file
creation, staging, commit, and push. No Modal command, GPU command, generation
entrypoint, experiment launch, output mutation command, artifact mutation
command, MLflow command, or billing query was run.

## Recommendation

Commit these source/test fixes with this audit report, push
`codex-track-handoff-context`, and require a clean post-commit status plus
remote-ref alignment before any separate L2b-4 authorization review.
