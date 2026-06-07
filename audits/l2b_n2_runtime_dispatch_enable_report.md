# L2b-2 Runtime Dispatch Enable Report

## Executive Summary

This patch removes the remaining no-dispatch guard for the already signed
L2b-2 n=2 full-coverage scope only. The signed all-shards selector can now pass
pre-launch validation, enter the mocked Modal dispatch boundary in tests, and
expand to the 9-shard, 108-cell runner surface that will produce 216 rows when
run with the real adapters.

No L2b execution, Modal invocation, GPU work, generation, billing query,
output mutation, artifact mutation, `mlruns/` mutation, analyzer refresh, or
preliminary-report refresh occurred during this patch.

## Previous Blocked Launch Result

The prior launch attempt stopped before execution with:

```text
L2B_N2_RUN_BLOCKED_PRELAUNCH_NO_DISPATCH_GUARD
```

Preflight had already passed, including the 9-shard/216-row plan checks, but
`cluster3/experiments/run_cluster3_modal.py` validated the signed L2b-2 gate
and then deliberately raised a no-dispatch runtime error.

## Root Cause

The L2b-2 validator accepted the signed token/profile/path constraints, but
`main()` still treated L2b as a no-execution runtime-gate branch. It never
routed the validated shard plan into the existing signed selector execution
surface.

## Patch Summary

- Replaced the post-validation no-dispatch guard with a signed L2b-2 dispatch
  route in `main()`.
- Added `_run_signed_l2b_selector_with_modal_context()` and
  `_signed_l2b_modal_app_context()` so tests can mock the Modal boundary.
- Added `_run_signed_l2b_selector()` to execute only validated L2b-2 shard
  plans, using bounded shard-level parallelism from the signed stage
  concurrency limit.
- Added `_run_signed_l2b_shard()` and `_l2b_cell_plans_for_shard()` so each
  shard expands into exactly its 12 validated per-cell commands and paths.
- Cleared selector-only L2b fields before each per-cell `run_cluster3()` call.
- Added a signed operational stop check for
  `SLOW_CELL_BUDGET_EXCEEDED` when a completed cell exceeds
  `signed_wall_clock_seconds_per_cell=1800`.

## Exact Dispatch Pass Conditions

Dispatch remains reachable only after `_validate_l2b_runtime_authorization()`
accepts all signed conditions:

```text
signed token: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1
signature status: SIGNED_FOR_L2B_N2_ONLY
selector/profile: l2b_n2_full_coverage
n: 2
total shards: 9
rows per shard: 24
total planned rows: 216
kernel classes: elementwise, reduction, matmul
dtypes: fp32, fp16, bf16
TRITONGEN_MLFLOW: 0
max_gpu_concurrency: <= 4
max_container_concurrency: <= 40
write mode: overwrite only
target policy: fail_if_any_target_path_exists=true
namespaces: deterministic l2b_n2/<shard_id> output and artifact namespaces
```

The all-shards command expands to 9 shards x 12 cells x n=2. One-shard and
bounded-wave selectors remain accepted only inside the same signed L2b-2 scope.

## Fail-Closed Conditions

The gate still fails closed for unsigned L2b-2, wrong token, L1/L2 token reuse,
L2b-4/n20, unknown shard, row/shard mismatch, MLflow enabled, retry/resume,
target path collision, namespace escape, and non-L2b-2 selector/profile values.

The code path does not add profiler, benchmark, speedup, performance evidence,
Fireworks API, dependency, analyzer, report, billing, or MLflow runtime
behavior.

## Tests Run

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py::test_l2b_n2_signed_all_shards_reaches_mocked_modal_dispatch_boundary cluster3/tests/test_run_cluster3_modal_cli.py::test_l2b_n2_namespace_escape_fails_prelaunch cluster3/tests/test_run_cluster3_modal_cli.py::test_l2b_n2_slow_cell_budget_exceeded_stops_shard -q
```

Result:

```text
3 passed
```

Full requested test bundle:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Result:

```text
214 passed
```

## Validation Run

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Both commands completed with no output.

## No-Execution Proof

- No signed launch command was run during this patch.
- The dispatch-boundary test replaces the Modal app context with a mock context.
- The dispatch-boundary test replaces `run_cluster3()` with a fake result
  producer and verifies no watched output, artifact, or `mlruns/` path changes.
- No Modal CLI/API command, GPU job, generation call, billing query, analyzer
  refresh, report refresh, or preliminary-report refresh was invoked.

## Protected Mutation Proof

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Final result was empty output.

## Remaining Step Before Launch

After this dispatch-enable commit is pushed, rerun the immediate L2b-2 launch
preflight:

- confirm `HEAD` is the pushed dispatch-enable commit;
- confirm all `l2b_n2` output/artifact target paths are absent;
- run the exact signed all-shards command with `TRITONGEN_MLFLOW=0`;
- do not retry or resume automatically if any shard stops.

## Classification

```text
L2B_N2_RUNTIME_DISPATCH_ENABLE_READY_FOR_LAUNCH
```

## Next-Step Recommendation

Launch only the signed L2b-2 all-shards command after push and immediate
target-path absence checks. Keep L2b-4, retry/resume, analyzer/report refresh,
billing reconciliation, profiler/benchmark/speedup, paper claims, and L2a
artifact mutation blocked.
