# L1a Selector Runtime Dispatch Unblock Report

timestamp_utc: 2026-06-06T08:51:48Z

branch: codex/l1a-selector-runtime-dispatch-unblock

base branch: codex-track-handoff-context

## Scope

This branch fixes the local runtime integration bug found during the second
authorized L1a n=1 attempt. That attempt passed the signed prelaunch guard but
failed before Modal launch because `run_cluster3` still treated
`grammar_mode_cp_12cell` as planning-only.

The patch is implementation support only. It does not run Modal, allocate GPU,
perform generation, mutate the real L1a output/artifact namespaces, query
billing, or start L1b/L2/n=5/n=20/paper-scale execution.

## Patch Summary

- Expands Cluster 3 condition support from the P-active subset to the canonical
  2^3 factor cells: `none`, `G`, `C`, `G+C`, `P`, `G+P`, `C+P`, `G+C+P`.
- Adds named no-P, P-active, C-active, and G-active condition groups.
- Maps all eight Cluster 3 cells onto existing Cluster 2 generation/eval labels
  without changing generation, repair, sampling, grammar, or correctness
  semantics.
- Keeps P repair fail-closed to P-active cells only.
- Allows C repair only on C-active cells, including no-P C controls.
- Expands the signed L1a selector into the reviewed 12-cell executable plan and
  invokes the existing `run_cluster3` writer once per planned cell.
- Routes L1a observability summaries into the planned observability artifact
  namespace instead of defaulting summaries next to result JSONL files.
- Keeps runtime MLflow disabled by the signed command environment.

## Selector Behavior

The signed selector remains the only runtime entrypoint for the 12-cell matrix:

`--condition grammar_mode_cp_12cell`

After signed prelaunch validation, the selector expands to exactly 12 cell
configs. Each config uses the planned factor cell, output path, observability
event path, observability summary path, observability hash path, grammar variant
where G is active, and overwrite mode. The selector-level signed authorization
token is not forwarded into ordinary per-cell `run_cluster3` configs.

## Scientific-Semantics Preservation

The patch does not change:

- row JSON schema fields;
- prompt text or prompt construction;
- grammar files or grammar validation semantics;
- C repair eligibility beyond admitting C-active no-P controls required by the
  signed matrix;
- P repair eligibility beyond fail-closing P repair for no-P controls;
- sampling parameters;
- pass/fail definitions;
- analyzer evidence logic.

## Validation Run

Passed:

```text
.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_dispatcher.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_grammar_mode_matrix.py cluster3/tests/test_run_cluster3_modal_cli.py -q
927 passed in 4.16s
```

Passed:

```text
.venv/bin/python -m compileall -q cluster3 shared/factors
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

The protected-path diff command produced empty output.

Ruff was not installed in the local venv, so no Ruff lint run was performed.

## Local No-Execution Proof

No Modal command was run for this patch.

No GPU allocation was requested.

No generation command was run.

No billing query was run.

The new 12-cell selector execution test uses fake generation/correctness
adapters and temporary pytest paths only. It does not touch the real signed L1a
namespaces.

## Output and Artifact Mutation Proof

The protected-path diff command was empty for:

- `outputs`
- `artifacts`
- `mlruns`
- `docs/preliminary_report`
- dependency and lock files

## Remaining Authorization State

The next fresh L1a n=1 attempt is authorized only under the active goal and only
after this implementation is committed and promoted back to
`codex-track-handoff-context`.

No retry/resume of old runs is authorized.

## Remaining Risk

This patch proves the 12-cell selector can expand and write schema-valid rows
locally with fake adapters. It has not yet proven that the real Modal-backed
generation/correctness adapters complete all 12 cells successfully.

If the next run reaches Modal and fails after partial writes, the correct action
is to stop, audit the partial state, and avoid delete/resume unless a later
explicit authorization allows it.

## Classification

L1A_SELECTOR_RUNTIME_DISPATCH_UNBLOCK_LOCAL_COMPLETE

## Next Step

Commit this branch, fast-forward promote it into `codex-track-handoff-context`,
push if credentials permit, then make one fresh authorized L1a n=1 launch
attempt using the exact signed command from the active goal.
