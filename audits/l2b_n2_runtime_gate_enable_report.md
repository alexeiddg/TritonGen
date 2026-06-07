# L2b n2 Runtime Gate Enable Report

Date: 2026-06-07
Branch: `codex-track-handoff-context`
Baseline: `b770521 Authorize L2b n2 full coverage execution`
Classification: `L2B_N2_RUNTIME_GATE_ENABLE_READY_FOR_LAUNCH`

## Executive Summary

This patch enables a narrow signed L2b-2 pre-launch runtime gate for the final
signed n=2 sharded full-coverage packet. The gate validates the signed packet
ID, signature status, selector profile, shard set, row counts, namespaces,
concurrency ceilings, MLflow-off requirement, overwrite-only mode, and
fail-if-target-path-exists policy before any future L2b-2 launch.

No L2b execution was performed. No Modal command, GPU job, generation run,
billing query, analyzer/report refresh, dependency update, lockfile change,
preliminary-report refresh, or protected output/artifact/mlruns mutation was
performed.

## Signed Authorization Reference

- Packet:
  `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_full_coverage_authorization_packet.md`
- Packet ID / CLI token:
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
- Packet signature status: `SIGNED_FOR_L2B_N2_ONLY`
- Packet execution authorization: `AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY`
- Signed packet commit: `b770521 Authorize L2b n2 full coverage execution`
- Runtime-gate scope: L2b-2 n=2 only

## Runtime-Gate Patch Summary

- `cluster3/planning/grammar_mode_matrix.py`
  - registers the signed L2b-2 packet token and signature status;
  - marks only `l2b_n2_full_coverage` as signed-token available;
  - keeps `l2b_n20_full_coverage` unsigned and blocked;
  - gives L2b-2 shard plans the signed packet token by default;
  - keeps timing diagnostics sidecar-only and non-performance.
- `cluster3/experiments/run_cluster3_modal.py`
  - narrows L2b-2 authorization to a shard-level validator;
  - prevents non-L2b profile selection from treating L2b-2 as a normal
    monolithic 12-cell selector;
  - validates all/one/wave shard selectors without invoking Modal;
  - rejects non-sharded namespaces, target path collisions, retry/resume,
    MLflow-enabled runtime, L2b-4, and cross-rung token reuse.
- `cluster3/tests/test_run_cluster3_modal_cli.py`
  - adds positive pre-launch tests for all shards, one shard, and a bounded
    wave;
  - adds fail-closed tests for unsigned, wrong-token, n=20/L2b-4, unknown shard,
    shard-count mismatch, row-count mismatch, MLflow enabled, resume, and target
    path collision.
- `cluster3/tests/test_grammar_mode_matrix.py`
  - updates L2b-2 stage and shard-plan expectations for the signed gate while
    preserving L2b-4 blocked expectations.

## Exact Signed L2b-2 Pass Conditions

The pre-launch gate passes only when all of these conditions hold:

- CLI token is
  `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`;
- signature status is `SIGNED_FOR_L2B_N2_ONLY`;
- `TRITONGEN_MLFLOW=0`;
- `--condition grammar_mode_cp_12cell`;
- `--l2b-stage l2b_n2_full_coverage`;
- `--repair-history-policy agentic_transcript_v1`;
- `--overwrite`;
- no selector-level `--output` override;
- no selector-level observability overrides;
- repo-backed kernel classes are exactly `elementwise`, `reduction`, `matmul`;
- repo-backed dtype variants are exactly `fp32`, `fp16`, `bf16`;
- shard IDs are exactly the nine signed `kernel_class__dtype_variant` tuples;
- selected shard mode is `all`, one exact shard ID, or a bounded `wave:start:count`;
- `n == 2`;
- `planned_cells_per_shard == 12`;
- `rows_per_shard == 24`;
- `full_matrix_planned_rows == 216`;
- all-shards commands use `--kernel-class all --dtypes fp32,fp16,bf16`;
- one-shard commands use the shard's exact kernel class and dtype;
- wave commands use `--kernel-class all --dtypes fp32,fp16,bf16`;
- output and observability paths are under the deterministic L2b-2 per-shard
  namespaces;
- analysis/report/billing namespace globs remain under the deterministic L2b-2
  per-shard namespaces;
- `max_gpu_concurrency <= 4`;
- `max_container_concurrency <= 40`;
- every planned output, hash sidecar, observability event, observability
  summary, and observability hash target is absent before launch;
- `fail_if_any_target_path_exists=true`.

## Fail-Closed Conditions

The gate remains fail-closed for:

- unsigned L2b-2 runtime commands;
- wrong packet tokens;
- L1a/L1b/L2 token reuse;
- L2b-4 / n=20;
- `n != 2`;
- missing shard plans;
- shard count mismatch for all-shards mode;
- row count mismatch;
- unknown shard IDs;
- kernel classes outside `elementwise`, `reduction`, `matmul`;
- dtype variants outside `fp32`, `fp16`, `bf16`;
- all-shards or wave commands that do not use all signed kernels/dtypes;
- one-shard commands whose kernel or dtype does not match the shard ID;
- `TRITONGEN_MLFLOW` not set to `0`;
- retry or resume mode;
- target path collisions;
- namespaces outside `l2b_n2`;
- sidecar timing marked as performance evidence;
- automatic retry or automatic resume in the slow-cell policy;
- profiler, benchmark, performance, speedup, L3, or paper-claim expansion.

## L2b-4 Blocked Status

L2b-4 remains unsigned and blocked. The n=20 selector profile has no signed
token, remains `UNSIGNED_BLOCKED_ON_L2B_2_VALIDATION`, and cannot pass the
L2b-2 runtime gate. It can be signed only after L2b-2 completes and validates
under a separate packet.

## Tests Run

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Observed result: `211 passed`.

## Validation Run

```bash
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Observed result before final commit: compileall passed; `git diff --check`
passed; protected mutation scan was empty.

## No-Execution Proof

- No `modal run` command was run.
- No signed L2b-2 runtime command was run.
- No Modal app context was invoked by the new positive tests.
- No GPU, generation, correctness execution, billing query, analyzer/report
  refresh, or preliminary-report refresh was run.
- The only runtime behavior exercised locally was the pre-launch validator in
  pytest.

## Protected Mutation Proof

The protected mutation scan was empty for:

```text
outputs
artifacts
mlruns
docs/preliminary_report
pyproject.toml
requirements.txt
requirements-dev.txt
uv.lock
poetry.lock
Pipfile.lock
```

No protected output, artifact, MLflow, dependency, lockfile, or preliminary
report file is part of this runtime-gate patch.

## Classification

`L2B_N2_RUNTIME_GATE_ENABLE_READY_FOR_LAUNCH`

## Next-Step Recommendation

Review and promote this runtime-gate commit before any launch. After promotion,
rerun the protected target-path absence checks immediately before execution and
launch only the exact signed L2b-2 packet command or a valid signed one-shard or
bounded-wave command. Do not run L2b-4, retry/resume, analyzer/report refresh,
billing reconciliation, profiler/benchmark/speedup work, or paper-claim work
without a separate signed packet.
