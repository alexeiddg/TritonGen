# Full Pipeline Grammar-Mode x C x P L2b Compressed Full-Coverage Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_COMPRESSED_FULL_COVERAGE_PACKET_V2`
packet_version: `0.4.0-l2b-n2-signed-boundary`
packet_type: compressed ladder planning packet and L2b-2 signature boundary record
branch: `codex/l2b-full-coverage-plan-and-selector`
target_branch: `codex-track-handoff-context`
baseline_commit: `9974770 Promote Fireworks Modal planning doc`
execution_code_target_commit: `eab664f560404cc40e309caa8d4202346452ecc3`
status: `L2B_2_SIGNED_L2B_4_BLOCKED_NO_EXECUTION_YET`
signature_status: `SIGNED_FOR_L2B_N2_ONLY`
classification: `L2B_N2_FINAL_AUTHORIZATION_READY`
AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY

Execution authorization flags:

```text
MODAL_AUTHORIZED: YES_L2B_N2_ONLY
GPU_AUTHORIZED: YES_L2B_N2_ONLY
GENERATION_AUTHORIZED: YES_L2B_N2_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N2_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N2_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N2_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N2_RECONCILIATION_ONLY_AFTER_RUN
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
FIREWORKS_API_CALLS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
```

This umbrella now records that the separate L2b-2 packet is signed for the
216-row n=2 shard scope only. No execution occurred during packet drafting. This
umbrella does not sign L2b-4, does not authorize retry or resume, and does not
change runtime launcher behavior; a separate execution-readiness step must
verify or enable only the exact signed L2b-2 token/profile/path before launch.

## Reconciliation Context

Current trunk is `codex-track-handoff-context` at `9974770 Promote Fireworks
Modal planning doc`. The signed L2a n=20 attempt is preserved at `04d2eef
Record failed L2 n20 validation` as an incomplete wall-clock/slow-tail run:
228 of 240 rows completed, with only `task_agnostic__c_on__p_on` stopped at 8
of 20 rows. This is not treated here as a scientific evidence failure; analyzer,
report, paper-scale, retry, resume, overwrite, and rerun work remain blocked.

L2b planning is reconciled on top of that trunk state and must not modify the
preserved L2a output, observability, billing, report, analysis, or `mlruns`
surfaces.

## Ladder

Do not run L2b-1.

| Rung | Selector profile | Scope | Status |
|---|---|---|---|
| L2b-0 | local planning only | selector/profile and shard-plan support | implemented locally; no execution |
| L2b-2 | `l2b_n2_full_coverage` | full repo-backed coverage at `n=2` | signed for L2b-2 only; no execution yet |
| L2b-4 | `l2b_n20_full_coverage` | same full coverage at `n=20` | unsigned and blocked on L2b-2 completion/validation |

The branch may prepare L2b-4 selector/profile support and an unsigned packet
draft only. L2b-4 can be signed only after L2b-2 completes and validates. The
L2b-2 packet is now signed, but the target code still has no registered signed
L2b runtime token because this packet-preparation step intentionally did not
change runtime launcher behavior.

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
first_wave_max_gpu_concurrency <= 4
first_wave_max_container_concurrency <= 40
second_wave_after_first_wave_validation_max_gpu_concurrency <= 8
second_wave_after_first_wave_validation_max_container_concurrency <= 80
```

Do not use 10 GPUs or 100 containers unless L2b-2 passes and the first L2b-4
wave validates cleanly.

## Packet Files

The signed L2b-2 packet is:

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

`L2B_N2_FINAL_AUTHORIZATION_READY`
