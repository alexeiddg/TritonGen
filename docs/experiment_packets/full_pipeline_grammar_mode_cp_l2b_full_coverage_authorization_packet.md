# Full Pipeline Grammar-Mode x C x P L2b Compressed Full-Coverage Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_COMPRESSED_FULL_COVERAGE_PACKET_V2`
packet_version: `0.5.0-l2b-n20-signed-boundary`
packet_type: compressed ladder planning packet and L2b n20 signature boundary record
branch: `codex/l2b-full-coverage-plan-and-selector`
target_branch: `codex-track-handoff-context`
baseline_commit: `28255c3afec51a2d61fcd59dbe9ee624b45e1306`
execution_code_target_commit: `28255c3afec51a2d61fcd59dbe9ee624b45e1306`
status: `L2B_N2_COMPLETE_WITH_CAVEAT_L2B_N20_SIGNED_NO_EXECUTION_DURING_DRAFT`
signature_status: `SIGNED_FOR_L2B_N20_ONLY_BY_SEPARATE_PACKET`
classification: `L2B_N20_FINAL_AUTHORIZATION_READY`
AUTHORIZES_EXECUTION: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET

Execution authorization flags:

```text
MODAL_AUTHORIZED: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET
GPU_AUTHORIZED: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET
GENERATION_AUTHORIZED: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N20_NAMESPACES_ONLY_BY_SEPARATE_PACKET
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N20_NAMESPACES_ONLY_BY_SEPARATE_PACKET
BILLING_QUERY_AUTHORIZED: YES_L2B_N20_RECONCILIATION_ONLY_AFTER_WAVES
ANALYZER_REFRESH_AUTHORIZED: YES_AFTER_2160_VALIDATED_ROWS_OR_EXPLICIT_PARTIAL_CAVEAT
REPORT_REFRESH_AUTHORIZED: YES_AFTER_2160_VALIDATED_ROWS_OR_EXPLICIT_PARTIAL_CAVEAT
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
FIREWORKS_API_CALLS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
OVERWRITE_AUTHORIZED: NO
L2B_4_AUTHORIZED: YES_L2B_N20_ONLY_BY_SEPARATE_PACKET
```

This umbrella records the current L2b ladder boundary. The separate L2b-2 packet
and recovery packet together satisfy the 216-row prerequisite with an
observability caveat. The separate L2b-4 n20 packet signs only the 2160-row n20
scope. No execution occurred during packet drafting. Retry, resume, overwrite,
Fireworks execution, L2b-2 mutation, L2b-2 recovery mutation, and L3 remain
unauthorized.

## Reconciliation Context

Current trunk is `codex-track-handoff-context` at
`28255c3afec51a2d61fcd59dbe9ee624b45e1306`. L2b-2 has 188 base rows plus 28
recovery rows for 216/216 logical rows, 0 duplicate logical keys, 0 missing
logical keys, and all 9 shards complete. Carry forward the caveat that the
`reduction__fp16` recovery rows have result/hash sidecars but no observability
sidecars. L2b-4 must use create-only output and observability logger support and
must require observability sidecars for every n20 shard.

## Ladder

Do not run L2b-1.

| Rung | Selector profile | Scope | Status |
|---|---|---|---|
| L2b-0 | local planning only | selector/profile and shard-plan support | implemented locally; no execution |
| L2b-2 | `l2b_n2_full_coverage` | full repo-backed coverage at `n=2` | complete and validated with observability caveat |
| L2b-4 | `l2b_n20_full_coverage` | same full coverage at `n=20` | signed by separate n20 packet only |

The L2b-4 packet token is
`FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`.
The runtime gate must accept only that token for `l2b_n20_full_coverage`, use
create mode without `--overwrite`, reach mocked Modal dispatch in tests, and
fail closed for dirty worktree or local/remote drift before future launch.

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

## Timing Observability

L2b requires per-cell and per-shard timing diagnostics as sidecar metadata only.
These fields are not scientific result rows, analyzer inputs, paper evidence,
profiler outputs, benchmark data, or performance evidence.

Required sidecar diagnostics:

```text
wall_clock_seconds_per_row
generation_attempt_count
compile_attempt_count
correctness_call_count
p_repair_attempt_count
c_repair_attempt_count
terminal_failure_type
timeout_or_stop_reason if applicable
```

Allowed use:

```text
operational_budgeting
slow_cell_identification
```

Forbidden use:

```text
speedup claims
performance claims
paper evidence
throughput or latency claims
```

Known high-cost cell:

```text
task_agnostic__c_on__p_on
```

Risk note: `task_agnostic__c_on__p_on` is expected to be the slowest cell
because it combines the broadest grammar mode with both P and C repair pathways.
L2b budget estimates must not assume uniform row time across cells. For L2b
execution design, this is another reason sharding is mandatory. One slow
`task_agnostic__c_on__p_on` path must not block every kernel/dtype result.

## Slow-Cell Stop Policy

Each signed L2b packet must provide a concrete wall-clock budget before any
execution. If any single cell exceeds that signed wall-clock budget, future
runtime must finish the active row if safe, then stop only that shard and
classify:

```text
SLOW_CELL_BUDGET_EXCEEDED
```

Required behavior:

```text
automatic retry: no
automatic resume: no
preserve partial shard audit: yes
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
artifact paths, concurrency limits, timing observability contract, slow-cell
stop policy, and `fail_if_any_target_path_exists=true`.

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
wave_1_max_gpu_concurrency <= 4
wave_1_max_container_concurrency <= 40
wave_2_max_gpu_concurrency <= 4
wave_2_max_container_concurrency <= 40
wave_3_max_gpu_concurrency <= 4
wave_3_max_container_concurrency <= 40
wave_4_matmul_fp32_max_gpu_concurrency <= 2
wave_4_matmul_fp32_max_container_concurrency <= 20
```

Do not use 10 GPUs or 100 containers. `matmul__fp32` must remain isolated last.

## Packet Files

The signed L2b-2 packet is:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_full_coverage_authorization_packet.md
```

The signed L2b-4 n20 packet is:

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

`L2B_N20_FINAL_AUTHORIZATION_READY`
