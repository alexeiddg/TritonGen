# L1a n=1 Third Attempt Hydration Failure Report

attempt_start_utc: 2026-06-06T08:56:44Z

attempt_end_utc: 2026-06-06T08:57:10Z

branch_at_attempt: codex-track-handoff-context

head_at_attempt: fb860787e644bbb6830492f7db4805519005dea6

implementation_commit_in_scope: fb86078 Unblock L1a selector runtime dispatch

## Exact Command

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

## Result

The command failed before a hydrated Modal app or GPU allocation.

Failure:

```text
modal.exception.ExecutionError: Function has not been hydrated with the metadata it needs to run on Modal, because the App it is defined on is not running.
```

Failure location:

```text
cluster3/experiments/run_cluster3_modal.py:2926
cluster2/generation/modal_generate_c2.py:95
```

The selector reached the first real generation call for
`grammar_off__c_off__p_off`, but the direct Python signed command had not
entered the shared Modal app context. No result row was appended.

## Modal and GPU Status

Modal app context: not hydrated.

Modal runtime context in observability sidecar: unavailable.

GPU allocation: not reached.

Generation completion: not reached.

Correctness evaluation: not reached.

Billing reconciliation: not run because no hydrated Modal run window existed.

## Output and Artifact Status

The failed attempt created pre-row artifacts for the first cell only:

| Path | Row count / event count | SHA256 |
|---|---:|---|
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl` | 0 rows | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl.hashes.json` | sidecar only | `b523732f61abd711af2a625a41eda76cac614cc3e28af97ef3812ed2f498f7f5` |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.observability.jsonl` | 5 events | `2c51fe2831488963d8a224804724728cb8b12e9c1522dbb68ae935c4df8caea5` |
| `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.observability.jsonl.hashes.json` | sidecar only | `88fda97019afdbce88a9c1356c8d7d82cde0de03007f5a0e416b735a44bbe78d` |

The observability stream records `run_started`, `row_started`,
`stage_started:generation`, `stage_failed:generation`, and `run_failed`. It
records unavailable Modal context and no token/cost counts.

No output JSONL row exists.

## Placeholder Archive

The failed pre-row files were archived inside the authorized L1a namespaces so
the exact planned target paths are no longer occupied:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_003_20260606T085644Z/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_003_20260606T085644Z/
```

This was not treated as valid run evidence. It was zero-row failed-attempt
evidence from the current authorized flow.

## Patch Applied After Failure

The follow-up patch is a narrow infrastructure fix:

- direct signed selector execution now enters the shared Modal app context using
  `app.run()`;
- the existing Cluster 2 Modal generation and correctness surfaces are imported
  before entering that app context so their remote handles can hydrate;
- ordinary non-selector `run_cluster3` execution remains unchanged;
- the unit test for the signed selector replaces the app context with
  `nullcontext`, keeping tests local-only.

No generation, repair, grammar, sampling, pass/fail, analyzer, or scientific
row semantics were changed by this hydration patch.

## Validation After Patch

Passed:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_cluster3_imports.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_dispatcher.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_grammar_mode_matrix.py -q
927 passed in 4.20s
```

## Push Status

`codex-track-handoff-context` was locally fast-forwarded to `fb86078`.

Push to origin was attempted before the third launch attempt, but the process
hung in `git-remote-https`; it was terminated after confirming local was ahead
of origin by one commit. Origin therefore remained at `fbb0838` at the time of
this report.

## Stop-Limit Compliance

No retry or resume was used.

No L1b, L2, n=5, n=20, paper-scale, profiler, benchmark, speedup, or
performance run occurred.

Runtime MLflow stayed disabled through `TRITONGEN_MLFLOW=0`.

## Classification

L1A_THIRD_ATTEMPT_FAILED_DIRECT_PYTHON_MODAL_HYDRATION

## Next Step

Commit the hydration fix and this audit, keep the archived zero-row evidence
out of the exact planned target paths, then make one fresh authorized L1a n=1
attempt with the same signed direct-Python command.
