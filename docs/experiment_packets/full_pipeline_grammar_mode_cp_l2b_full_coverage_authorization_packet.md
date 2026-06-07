# Full Pipeline Grammar-Mode x C x P L2b Compressed Full-Coverage Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_COMPRESSED_FULL_COVERAGE_PACKET_V2`
packet_version: `0.2.0-plan-only`
packet_type: compressed ladder planning packet and local selector/profile record
branch: `codex/l2b-full-coverage-plan-and-selector`
target_branch: `codex-track-handoff-context`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
status: `DRAFT_NOT_APPROVED_PLAN_ONLY`
signature_status: `UNSIGNED`
classification: `L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
FIREWORKS_API_CALLS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
```

This packet replaces the earlier monolithic L2b n=20 planning shape with a
compressed two-stage sharded ladder. It does not run Modal, GPU work,
generation, billing, analyzer/report refresh, Fireworks API calls, or any
output/artifact mutation.

## Ladder

Do not run L2b-1.

| Rung | Selector profile | Scope | Status |
|---|---|---|---|
| L2b-0 | local planning only | selector/profile and shard-plan support | implemented locally; no execution |
| L2b-2 | `l2b_n2_full_coverage` | full repo-backed coverage at `n=2` | unsigned, ready for signature review |
| L2b-4 | `l2b_n20_full_coverage` | same full coverage at `n=20` | unsigned and blocked on L2b-2 completion/validation |

The branch may prepare L2b-4 selector/profile support and an unsigned packet
draft only. L2b-4 can be signed only after L2b-2 completes and validates.

## Repo-Backed Scope

Kernel classes come from `shared/eval/correctness_shapes.py`:

```text
elementwise
reduction
matmul
```

Dtype variants come from `cluster2/constants.py`:

```text
fp32
fp16
bf16
```

This branch does not change C/P semantics, correctness semantics, grammar
semantics, analyzer paper gates, tolerances, model revisions, or tokenizer
revisions.

## Mandatory Shard Model

Each shard is exactly one tuple:

```text
shard_id = <kernel_class>__<dtype_variant>
```

The nine repo-backed shards are:

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

Each shard contains the existing 12 `grammar_mode x C x P` cells and produces
`12 x n` rows.

## Deterministic Namespaces

For `N in {2, 20}` and each `shard_id`:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
```

The path collision policy is mandatory:

```text
fail_if_any_target_path_exists: true
```

No live L2a namespace may be touched:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
mlruns
```

## Row Counts

| Rung | n | total_shards | rows_per_shard | total_planned_rows |
|---|---:|---:|---:|---:|
| L2b-2 | 2 | 9 | 24 | 216 |
| L2b-4 | 20 | 9 | 240 | 2160 |

The 12 cells per shard are:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

## Selector Commands

L2b-2 all-shard dry plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

L2b-2 all-shard execution plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

One-shard planning example:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector elementwise__fp32 --kernel-class elementwise --scale-tier development --n 2 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Bounded-wave planning example:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_full_coverage --l2b-shard-selector wave:0:4 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

The execution-plan JSON must report `total_shards`, `rows_per_shard`,
`total_planned_rows`, per-shard command, per-shard output paths, per-shard
artifact paths, concurrency limits, and `fail_if_any_target_path_exists=true`.

## Parallelism Plan

Backend now:

```text
backend: modal_local_model
```

Future backend TODO only:

```text
backend: fireworks_api
```

No Fireworks client, dependency, API key, network call, provider retry, or
provider billing path is implemented here.

L2b-2 concurrency caps:

```text
max_gpu_concurrency <= 4
max_container_concurrency <= 40
```

L2b-4 staged caps:

```text
first_wave_max_gpu_concurrency <= 4
first_wave_max_container_concurrency <= 40
second_wave_after_first_wave_validation_max_gpu_concurrency <= 8
second_wave_after_first_wave_validation_max_container_concurrency <= 80
```

Do not use 10 GPUs or 100 containers unless L2b-2 passes and the first L2b-4
wave validates cleanly.

## Packet Files

The signature-ready L2b-2 draft is:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_full_coverage_authorization_packet.md
```

The L2b-4 blocked draft is:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_full_coverage_authorization_packet.md
```

## Validation Plan

Local validation for this branch:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Protected mutation scan must show no changed files under `outputs`,
`artifacts`, `mlruns`, dependency or lock files, or live L2a namespaces.

## Classification

`L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE`
