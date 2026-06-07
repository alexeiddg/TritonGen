# Full Pipeline L2b-2 n=2 Sharded Full-Coverage Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
packet_version: `0.1.1-unsigned-signature-ready`
packet_type: unsigned authorization packet draft
branch: `codex/l2b-full-coverage-plan-and-selector`
target_branch: `codex-track-handoff-context`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
selector_profile_id: `l2b_n2_full_coverage`
rung: `L2b-2`
status: `UNSIGNED_READY_FOR_SIGNATURE_REVIEW`
AUTHORIZES_EXECUTION: NO

This packet is prepared so L2b-2 can be signed first after review. It does not
authorize execution in this branch.

## Scope

```text
condition selector: grammar_mode_cp_12cell
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
kernel classes: elementwise, reduction, matmul
dtype variants: fp32, fp16, bf16
n: 2
total_shards: 9
planned_cells_per_shard: 12
rows_per_shard: 24
total_planned_rows: 216
repair_history_policy: agentic_transcript_v1
backend: modal_local_model
future_backend_todo: fireworks_api
```

## Shards

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

Each shard is exactly `<kernel_class>__<dtype_variant>` and produces 24 rows.

## Namespaces

For each `shard_id`:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
```

Path policy:

```text
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
```

## Timing Observability

Future L2b-2 execution must emit per-cell and per-shard timing diagnostics as
sidecar metadata only, under the signed shard observability namespace. These
diagnostics must not mutate result-row schemas and must not be used for
speedup, performance, throughput, latency, profiler, benchmark, or paper
evidence claims.

Required diagnostics:

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

Allowed use is limited to operational budgeting and identifying slow cells.

Known high-cost cell risk note: `task_agnostic__c_on__p_on` is expected to be
the slowest cell because it combines the broadest grammar mode with both P and C
repair pathways. L2b budget estimates must not assume uniform row time across
cells. For L2b execution design, this is another reason sharding is mandatory.
One slow `task_agnostic__c_on__p_on` path must not block every kernel/dtype
result.

## Planning Commands

Dry plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future signed shard command shape:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector elementwise__fp32 --kernel-class elementwise --scale-tier development --n 2 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization SIGNED_L2B_PACKET_NOT_APPROVED --overwrite
```

The placeholder token is intentionally not authorized by this branch.

## Concurrency Caps

```text
max_gpu_concurrency <= 4
max_container_concurrency <= 40
```

The plan may use Modal parallelism after signature, but this branch does not
call Modal. Modal `.spawn_map` and `max_containers` remain future implementation
surfaces, not code changes here.

## Slow-Cell Stop Policy

The signed L2b-2 packet must provide a concrete per-cell wall-clock budget before
execution. If any single cell exceeds that signed budget, finish the active row
if safe, then stop the current shard and classify:

```text
SLOW_CELL_BUDGET_EXCEEDED
```

Do not retry or resume automatically. Preserve the partial shard audit, including
completed rows, sidecar events, terminal failure type, and timeout or stop reason
if applicable.

## Stop Conditions

Stop before launch if any target path exists, if shard ids do not match the
repo-backed kernel/dtype Cartesian product, if row counts are not 24 per shard
and 216 total, if any live L2a path would be touched, if C/P/grammar semantics
would change, if analyzer/report paper gates must be loosened, or if the signed
per-cell wall-clock budget is missing.

## Signature Block

```text
SIGNATURE_STATUS: UNSIGNED
AUTHORIZES_EXECUTION_AFTER_SIGNATURE_ONLY: PENDING_SIGNATURE_REVIEW_L2B_2_N2_ONLY
AUTHORIZES_L2B_4: NO
AUTHORIZED_BY:
AUTHORIZED_AT_UTC:
SIGNED_TARGET_COMMIT:
```
