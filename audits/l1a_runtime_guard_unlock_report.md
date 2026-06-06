# L1a Runtime Guard Unlock Report

report_version: 1.0.0
created_at: 2026-06-06
branch: codex/l1a-runtime-guard-unlock
base_branch: codex-track-handoff-context
failed_run_audit_commit: 7cd3363 Record failed L1a n1 execution attempt
final_authorization_commit: 8f97129ca66a9619cc55bdc030df13959ee2344c
classification: L1A_RUNTIME_GUARD_UNLOCK_READY_FOR_REVIEW
AUTHORIZES_EXECUTION: NO
AUTHORIZES_RETRY: NO
AUTHORIZES_RESUME: NO

## Executive Summary

The signed L1a n=1 command failed before Modal launch because the
`grammar_mode_cp_12cell` runtime path raised an unconditional fail-closed
`RuntimeError` immediately after the dry-plan and execution-plan branches.

This patch replaces that unconditional guard with a narrow pre-launch
authorization validator for the exact signed selector command. The selector
remains fail-closed by default: unsigned, wrong-token, non-smoke, n>1,
non-elementwise, non-fp32, resume, MLflow-enabled, non-all-cell, existing target
path, and non-12-cell plans are rejected before runtime launch.

No Modal, GPU, generation, correctness, billing, retry, resume, output mutation,
artifact mutation, or `mlruns/` mutation was run.

## Failed Command

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

## Failure Location

`cluster3/experiments/run_cluster3_modal.py:1117`

Original failure:

```text
RuntimeError: grammar_mode_cp_12cell execution is not enabled by this local support branch; the selector remains fail-closed until a separate signed execution packet authorizes launch
```

## Root Cause

The CLI parsed `--signed-l1a-authorization`, but the runtime branch did not
inspect it. After local dry-plan and execution-plan handling, every
`condition == grammar_mode_cp_12cell` runtime invocation raised the same
unconditional `RuntimeError`, including the final signed L1a command.

The signed token therefore did not unlock execution because there was no
selector-level authorization validator connected to the runtime branch.

## Patch Summary

- Added `L1A_SIGNED_AUTHORIZATION_TOKEN` for the exact packet token.
- Added `_validate_l1a_runtime_authorization(...)`.
- Replaced the unconditional `main(...)` runtime guard with that validator.
- Kept dry-plan and execution-plan behavior unchanged.
- Added tests for the signed pre-launch pass path with a mocked runner boundary.
- Added negative tests for unsigned/wrong-token, n=5, non-smoke scale, non-
  elementwise kernel, MLflow enabled, resume, existing target path, and
  non-12-cell plans.

## Exact Authorization Scope

Runtime guard unlock is valid only when all of these are true:

- `condition == grammar_mode_cp_12cell`
- `scale_tier == smoke`
- `n == 1`
- `kernel_class == elementwise`
- `dtypes == ("fp32",)`
- `signed_l1a_authorization == FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
- `TRITONGEN_MLFLOW=0`
- `write_mode == overwrite`
- selector-level output placeholder is used
- `grammar_mode_cell == all`
- executable plan contains exactly 12 cells
- planned row count is exactly 12
- every planned output/content-hash/observability path is under the signed L1a
  n=1 namespaces
- all planned target paths are absent

## Forbidden Scope

This patch does not authorize:

- retry or resume of the failed attempt
- a second L1a execution attempt
- L1b, L2, paper-scale, n=5, n=20, profiler, benchmark, or speedup work
- runtime MLflow tracking or `mlruns/` mutation
- Modal, GPU, generation, correctness, or billing during this patch
- output/artifact mutation during this patch
- changes to row schema, scientific semantics, repair policy, grammar semantics,
  sampling/model settings, or pass/fail definitions

## Tests Added/Updated

Updated `cluster3/tests/test_run_cluster3_modal_cli.py`:

- `test_l1a_12cell_signed_selector_passes_prelaunch_guard_without_modal`
- `test_l1a_12cell_selector_wrong_token_fails_prelaunch`
- `test_l1a_12cell_selector_n5_fails_prelaunch`
- `test_l1a_12cell_selector_non_smoke_scale_fails_prelaunch`
- `test_l1a_12cell_selector_non_elementwise_kernel_fails_prelaunch`
- `test_l1a_12cell_selector_mlflow_enabled_fails_prelaunch`
- `test_l1a_12cell_selector_resume_fails_closed`
- `test_l1a_12cell_selector_existing_target_path_fails_prelaunch`
- `test_l1a_12cell_selector_requires_exactly_12_planned_cells`

Existing dry-plan and execution-plan tests continue to prove both local planning
surfaces emit 12 cells and write no outputs, artifacts, or `mlruns/`.

## Validation Run

Commands run:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
git diff -- cluster3 docs audits | rg -n "L1b|L2|paper-scale|n=5|n 5|retry|resume|profiler|benchmark|speedup|performance"
git diff -- cluster3 tests docs audits | rg -n "modal run|modal shell|gpu|generate|correctness|billing|mlruns|outputs/|artifacts/"
```

Results:

- targeted pytest: `162 passed`
- compileall: pass
- `git diff --check`: pass
- protected runtime/output/dependency diff scan: empty
- scope scan: only negative retry/resume wording appeared
- execution scan: empty

## No Modal/GPU/Generation Proof

No Modal command was run. No GPU command was run. No generation or correctness
surface was invoked. The positive signed-selector test uses a mocked
`run_cluster3` boundary and returns an empty in-memory `Cluster3RunResult`.

## No Output/Artifact/Mlruns Mutation Proof

Protected scan was empty:

```bash
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

No `outputs/`, `artifacts/`, `docs/preliminary_report/`, dependency file,
lockfile, or `mlruns/` mutation was staged or produced.

## Remaining Required Step Before Second Attempt

The failed L1a attempt must not be retried or resumed. Before any second
execution attempt, this branch must be reviewed, promoted, and separately
authorized with a new explicit execution prompt. That future authorization must
confirm that the runtime guard unlock is accepted and that the signed L1a
command should be invoked again as a new attempt, not as a retry/resume.

## Classification

`L1A_RUNTIME_GUARD_UNLOCK_READY_FOR_REVIEW`

## Next-Step Recommendation

Review and commit this narrow runtime-guard unlock branch. After review, promote
it into `codex-track-handoff-context`, then prepare a fresh second-attempt
authorization packet/prompt that explicitly references the prior pre-launch
failure and preserves no retry/no resume semantics.
