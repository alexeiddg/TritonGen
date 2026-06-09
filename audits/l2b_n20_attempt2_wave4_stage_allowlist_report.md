# L2b n20 Attempt2 Wave 4 Stage Allowlist Report

classification: `L2B_N20_ATTEMPT2_WAVE4_STAGE_ALLOWLIST_READY`

## Scope

This is a no-execution stage allowlist patch for:

```text
stage: l2b_n20_attempt2_wave4_parallel_full_coverage
namespace: l2b_n20_attempt2_wave4_parallel
token: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_WAVE4_AUTHORIZATION_PACKET_V1
signature: SIGNED_FOR_L2B_N20_ATTEMPT2_WAVE4_ONLY
```

No Modal launch, GPU job, generation, row creation, Fireworks call, analyzer,
report, billing query, output mutation, artifact mutation, deletion, overwrite,
or live Lane A/B artifact staging is authorized by this patch.

## Root Cause

The Wave 4 manual launch failed before Modal dispatch because
`l2b_n20_attempt2_wave4_parallel_full_coverage` was absent from the L2b stage
choice and runtime allowlist. The existing allowlist included L2b n2, original
n20, attempt2, and the two-lane rescue Lane A/B stages only.

## Runtime Gate

The runtime allowlist accepts the Wave 4 stage only under:

```text
FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_WAVE4_AUTHORIZATION_PACKET_V1
```

Required scope:

```text
TRITONGEN_MLFLOW=0
stage: l2b_n20_attempt2_wave4_parallel_full_coverage
shard selector: matmul__fp32
kernel class: matmul
dtypes: fp32
n: 20
recovery cells: all
write mode: create
selected shards: 1
planned rows: 240
namespace: l2b_n20_attempt2_wave4_parallel
max_gpu_concurrency <= 2
max_container_concurrency <= 20
```

The current L2b planner uses zero-based wave selectors over the signed shard
order, so the runtime and script require the stable shard id `matmul__fp32`.
Wave selectors that do not resolve to exactly that shard remain fail-closed.

Wrong token, two-lane rescue token reuse, original attempt2 token reuse, Wave 1,
Wave 2, Wave 3, wrong namespace, `n != 20`, MLflow enabled, overwrite, retry,
and resume all fail closed.

## Launch Script

```text
scripts/run_l2b_n20_attempt2_wave4_parallel.sh
```

The script embeds only the signed Wave 4 command, writes logs to
`/tmp/tritongen_l2b_n20_attempt2_wave4_parallel_logs/`, requires source/docs
and scripts to be clean and origin-aligned, allows dirty worktree state only for
authorized Lane A/B artifact namespaces plus `docs/paper_draft/`, and fails if
Wave 4 target paths already exist.

## Validation

Static validation result:

```bash
bash -n scripts/run_l2b_n20_attempt2_wave4_parallel.sh
rg -- '--overwrite|--retry|--resume' scripts/run_l2b_n20_attempt2_wave4_parallel.sh
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result:

```text
bash -n: pass
forbidden flag grep: empty
pytest: 255 passed
compileall: pass
git diff --check: pass
protected mutation scan: empty
```
