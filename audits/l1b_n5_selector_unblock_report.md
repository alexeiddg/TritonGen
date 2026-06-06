# L1b n=5 Selector Unblock Report

date_utc: 2026-06-06

branch: `codex-track-handoff-context`

baseline_commit: `bc77e9b Audit L1a analyzer patch and golden drift`

## Trigger

The L1b preflight found that the existing executable selector was intentionally
locked to the L1a profile:

- `--scale-tier smoke`
- `--n 1`
- L1a output and observability namespaces
- L1a signed authorization token

That was correct for L1a, but it prevented the authorized L1b n=5 command from
passing prelaunch validation.

## Patch Scope

The patch adds an explicit L1b selector profile while preserving the L1a
profile unchanged:

- L1a profile: smoke, `n=1`, 12 rows, L1a paths, L1a token.
- L1b profile: development, `n=5`, 60 rows, L1b paths, L1b token.

The patch does not change prompts, sampling settings, grammar semantics, C/P
dispatch, repair policy, correctness semantics, pass/fail definitions,
denominators, analyzer evidence logic, Modal image definitions, model settings,
or output schema.

## Validation Run

Local-only validation completed before any Modal/GPU/generation attempt:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Result: `167 passed`.

```bash
.venv/bin/python -m compileall -q cluster3
```

Result: passed.

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Result: planning-only JSON with 12 cells and 60 planned rows.

## No-Execution Proof

At the time this unblock report was written:

- No Modal command had been run for L1b.
- No GPU allocation had been reached.
- No generation had been run for L1b.
- No correctness calls had been run for L1b.
- No L1b outputs, observability artifacts, analysis artifacts, report artifacts,
  billing artifacts, or `mlruns/` had been produced by the unblock patch.

## Classification

L1B_N5_SELECTOR_UNBLOCKED_PRELAUNCH_LOCAL_ONLY
