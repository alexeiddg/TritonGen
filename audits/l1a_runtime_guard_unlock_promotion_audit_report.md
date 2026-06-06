# L1a Runtime Guard Unlock Promotion Audit Report

report_version: 1.0.0
created_at: 2026-06-06
source_branch: codex/l1a-runtime-guard-unlock
target_branch: codex-track-handoff-context
promoted_commit: bf7989d Unlock signed L1a n1 runtime guard
classification: L1A_RUNTIME_GUARD_UNLOCK_PROMOTION_COMPLETE

## Promoted Commit

`bf7989d Unlock signed L1a n1 runtime guard` was promoted into
`codex-track-handoff-context` by fast-forward merge.

The target branch already contained the first failed-run audit at
`7cd3363 Record failed L1a n1 execution attempt`, so the promotion preserves the
record of the pre-launch failure before adding the guard unlock.

## Failed First-Attempt Location

The first authorized L1a n=1 invocation failed before Modal launch at:

`cluster3/experiments/run_cluster3_modal.py:1117`

Observed error:

```text
RuntimeError: grammar_mode_cp_12cell execution is not enabled by this local support branch; the selector remains fail-closed until a separate signed execution packet authorizes launch
```

## Root Cause

The CLI accepted `--signed-l1a-authorization`, but the runtime path for
`condition == grammar_mode_cp_12cell` still raised an unconditional fail-closed
guard after local dry-plan and execution-plan handling.

The signed authorization token was therefore never inspected by the runtime
branch, and the command stopped before Modal, GPU allocation, generation,
correctness checks, output writes, artifact writes, or billing reconciliation.

## Patch Summary

The promoted patch replaces the unconditional pre-launch runtime guard with a
narrow validator for the exact signed L1a n=1 selector command.

The validator permits the command to pass only when the selector remains inside
the signed L1a scope:

- `condition == grammar_mode_cp_12cell`
- `scale_tier == smoke`
- `n == 1`
- `kernel_class == elementwise`
- `dtypes == ("fp32",)`
- signed token is
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
- `TRITONGEN_MLFLOW=0`
- write mode is overwrite and resume is forbidden
- all-cell selector is used
- executable plan has exactly 12 cells and 12 planned rows
- planned output, content-hash, and observability paths remain under the signed
  L1a n=1 namespaces
- all planned target paths are absent before launch

Dry-plan and execution-plan behavior remains local-only.

## Exact Authorization Scope

The promoted guard unlock supports one signed L1a n=1 12-cell selector launch in
principle. It does not authorize any broader execution surface by itself.

Authorized second-attempt scope for the current phase is supplied by the user
prompt:

`SECOND_L1A_N1_ATTEMPT_AUTHORIZED: YES`

`AUTHORIZATION_SOURCE: "User message: I authorize a second attempt."`

The authorized matrix is:

- `grammar_mode in {grammar_off, template_upper_bound, task_agnostic}`
- `C in {off, on}`
- `P in {off, on}`

Expected rows: 12 total, exactly 1 row per cell.

## Forbidden Scope

The promotion does not authorize:

- retry or resume of the failed pre-launch attempt
- L1b or L2 execution
- paper-scale execution
- n=5 or n=20 execution
- profiler, benchmark, speedup, or performance-claim work
- MLflow tracking execution unless a signed packet explicitly requires it
- output or artifact writes outside the L1a n=1 namespaces
- mutation of `mlruns/`
- changes to scientific rows, grammar semantics, repair policy, sampling/model
  settings, or pass/fail definitions

## Tests and Scans Run

Commands run before promotion:

```bash
git status --short --branch
git log --oneline -8
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3
git diff --check
git diff --name-only codex-track-handoff-context..HEAD -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
git diff codex-track-handoff-context..HEAD -- cluster3 docs audits | rg -n "L1b|L2|paper-scale|n=5|n 5|retry|resume|profiler|benchmark|speedup|performance"
```

Results:

- source branch: `codex/l1a-runtime-guard-unlock`
- source branch status: clean
- `bf7989d` was HEAD on source branch
- targeted pytest: `162 passed`
- compileall: pass
- `git diff --check`: pass
- protected mutation scan: empty
- scope scan: only negative tests and explicitly non-authorized wording

Guard behavior confirmed by tests:

- signed L1a n=1 selector reaches a mocked runner boundary without Modal
- wrong token fails closed
- n=5 fails closed
- non-smoke scale tier fails closed
- non-elementwise kernel fails closed
- MLflow-enabled invocation fails closed
- resume fails closed
- existing target path fails closed
- non-12-cell executable plan fails closed

## No Modal/GPU/Generation During Patch Proof

No Modal command was run during the guard patch or promotion review. No GPU was
allocated. No generation or correctness command was invoked.

The positive signed-selector test uses a mocked `run_cluster3` boundary and does
not invoke Modal.

## No Output/Artifact/Mlruns Mutation Proof

The protected mutation scan before promotion was empty:

```bash
git diff --name-only codex-track-handoff-context..HEAD -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

No `outputs/`, `artifacts/`, `docs/preliminary_report/`, dependency file,
lockfile, or `mlruns/` mutation was included in the promoted guard patch.

## Second-Attempt Authorization Source

The current user prompt explicitly authorizes one fresh second L1a n=1 attempt
after promotion:

`AUTHORIZATION_SOURCE: "User message: I authorize a second attempt."`

This is not a retry or resume of the failed pre-launch attempt. It is a new
authorized attempt after the runtime guard patch.

## Classification

`L1A_RUNTIME_GUARD_UNLOCK_PROMOTION_COMPLETE`

## Next-Step Recommendation

Push `codex-track-handoff-context`, create and commit the second-attempt
authorization audit, run the required pre-execution validation, then invoke
exactly one signed L1a n=1 command if all preflight checks remain clean.
