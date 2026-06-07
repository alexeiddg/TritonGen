# L2b Sharded Full-Coverage Fireworks-Ready Modal Plan

## Status

status: `PLAN_ONLY_LOCAL_SELECTOR_SUPPORT`
branch: `codex/l2b-full-coverage-plan-and-selector`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
classification: `L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE`
AUTHORIZES_EXECUTION: NO

This plan implements local-only selector/profile support for a compressed L2b
ladder:

```text
L2b-0: local planning and selector support only
L2b-2: sharded full coverage at n=2
L2b-4: sharded full coverage at n=20
```

Forbidden in this branch:

```text
Modal execution
GPU execution
generation
experiment execution
billing query
output mutation
artifact mutation
mlruns mutation
analyzer refresh
report refresh
Fireworks API calls
dependency or lockfile changes
profiler, benchmark, speedup, timing, or performance claims
```

## Repo-Backed Discovery

Kernel classes come from `shared/eval/correctness_shapes.py`:

| kernel_class | kernel_name | shape pattern |
|---|---|---|
| `elementwise` | `relu` | `ND` |
| `reduction` | `softmax` | `RxC` |
| `matmul` | `gemm` | `MNK` |

Dtype variants come from `cluster2/constants.py`:

```text
fp32
fp16
bf16
```

No new kernel class, dtype, tolerance, grammar, C/P, correctness, analyzer, or
report semantics are introduced.

## Shard Model

Every shard is one exact tuple:

```text
shard_id = <kernel_class>__<dtype_variant>
```

The plan supports:

```text
--l2b-shard-selector all
--l2b-shard-selector elementwise__fp32
--l2b-shard-selector wave:<start>:<count>
```

Wave selection is deterministic over the locked order:

```text
elementwise__fp32
elementwise__fp16
elementwise__bf16
reduction__fp32
reduction__fp16
reduction__bf16
matmul__fp32
matmul__fp16
matmul__bf16
```

Each shard expands to the existing 12 `grammar_mode x C x P` cells and has
independent result, observability, analysis, report, and billing namespaces.

## Namespaces

For `N in {2, 20}`:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
```

All future execution must enforce:

```text
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
```

## Profiles

| Profile | Rung | n | rows_per_shard | total_rows | Signature state |
|---|---|---:|---:|---:|---|
| `l2b_n2_full_coverage` | L2b-2 | 2 | 24 | 216 | unsigned, ready for signature review |
| `l2b_n20_full_coverage` | L2b-4 | 20 | 240 | 2160 | unsigned, blocked on L2b-2 validation |

Runtime execution remains fail-closed. No signed L2b token exists in this
branch.

## Execution Plan Payload

The local execution-plan JSON reports:

```text
total_shards
selected_shard_count
planned_cells_per_shard
rows_per_shard
total_planned_rows
full_matrix_planned_rows
per-shard future_command
per-shard output_paths
per-shard artifact_paths
concurrency_limits
fail_if_any_target_path_exists=true
writes_outputs=false
writes_artifacts=false
writes_mlruns=false
```

## Commands

L2b-2 all-shard plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

L2b-4 bounded first wave:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector wave:0:4 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Signed runtime shape, still fail-closed in this branch:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector elementwise__fp32 --kernel-class elementwise --scale-tier development --n 2 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization SIGNED_L2B_PACKET_NOT_APPROVED --overwrite
```

## Modal Parallelism Boundary

The shard abstraction is compatible with Modal batch fanout, but this branch
does not implement or call Modal fanout code. Future work should use official
Modal surfaces deliberately:

- batch fanout through `.spawn_map` or equivalent batch submission;
- container caps through `max_containers`;
- optional input concurrency only after thread-safety and GPU-memory review.

Current caps:

```text
L2b-2: max_gpu_concurrency <= 4, max_container_concurrency <= 40
L2b-4 first wave: max_gpu_concurrency <= 4, max_container_concurrency <= 40
L2b-4 second wave after clean first wave: max_gpu_concurrency <= 8, max_container_concurrency <= 80
```

Do not use 10 GPUs or 100 containers unless L2b-2 passes and the first L2b-4
wave validates cleanly.

## Fireworks-Ready Boundary

The planner records backend metadata only:

```text
backend=modal_local_model
future_backend_todo=fireworks_api
```

No Fireworks calls, dependencies, API keys, provider retries, request clients,
or provider billing paths are added here. A later branch may add a provider
interface if it preserves shard identity, prompt metadata, grammar metadata,
seed identity, kernel class, dtype, and output namespace semantics.

## Validation Plan

Local validation for this branch:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Protected mutation scan must show no changed files under `outputs`,
`artifacts`, `mlruns`, dependency files, lockfiles, or live L2a paths.

## Acceptance Criteria

`L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE` when:

- kernel classes and dtypes are repo-backed;
- L2b is sharded by exact `<kernel_class>__<dtype_variant>`;
- L2b-2 and L2b-4 selector profiles exist;
- execution plans support all shards, one shard, and bounded waves;
- execution plans list shard commands, paths, row counts, and concurrency caps;
- runtime remains unsigned and fail-closed;
- L2b-4 remains blocked on L2b-2 validation;
- no Modal/GPU/generation/billing/output/artifact/mlruns mutation occurred.
