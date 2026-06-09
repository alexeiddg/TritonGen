# Full Pipeline L2b n20 Attempt2 Wave 4 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_WAVE4_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.1`
packet_type: signed Wave 4-only authorization packet
target_branch: `codex-track-handoff-context`
target_baseline: `84642385ca752b11defd3429ebc681fdab660b3b`
selector_profile_id: `l2b_n20_attempt2_wave4_parallel_full_coverage`
namespace: `l2b_n20_attempt2_wave4_parallel`
classification: `L2B_N20_ATTEMPT2_WAVE4_STAGE_ALLOWLIST_READY`

```text
AUTHORIZES_EXECUTION: YES_L2B_N20_ATTEMPT2_WAVE4_ONLY
MODAL_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_ONLY
GPU_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_ONLY
GENERATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_NAMESPACE_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_NAMESPACE_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N20_ATTEMPT2_WAVE4_RECONCILIATION_ONLY_AFTER_RUN
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
FIREWORKS_EXECUTION_AUTHORIZED: NO
L2B_N20_ATTEMPT2_ORIGINAL_MUTATION_AUTHORIZED: NO
L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_MUTATION_AUTHORIZED: NO
L2B_N2_MUTATION_AUTHORIZED: NO
L2B_N2_RECOVERY_MUTATION_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N20_ATTEMPT2_WAVE4_ONLY
```

## Current Lane Context

This packet is separate from the signed two-lane rescue packet:

```text
two-lane packet: FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
Lane A namespace: l2b_n20_attempt2_wave2_missing360_recovery
Lane B namespace: l2b_n20_attempt2_wave3_parallel
Wave 4 namespace: l2b_n20_attempt2_wave4_parallel
```

Wave 4 may be launched only after at least one current Lane A/B run has
completed or terminally stopped. Prefer launch after Lane B completes because
Lane B is expected to finish faster.

## Authorized Scope

```text
stage: l2b_n20_attempt2_wave4_parallel_full_coverage
shard selector: matmul__fp32
selector: matmul__fp32 single-shard scope
kernel class: matmul
dtype: fp32
n: 20
grammar-mode cells: 12
expected rows: 240
max rows: 240
max rows per cell: 20
max shards: 1
max_gpu_concurrency: 2
max_container_concurrency: 20
max_wall_clock_wave4: 43200s
max_wall_clock_per_cell: 10800s
max_estimated_cost_usd: 150
max_reconciled_billing_cost_usd: 200
```

Wave 4 / `matmul__fp32` is high risk. The signed wall-clock budget is longer
than prior matmul budgets, but no automatic retry or resume is authorized.

The current L2b planner uses zero-based wave selectors over the signed shard
order. The signed launch command therefore uses the stable shard id
`matmul__fp32`; broader wave selectors remain fail-closed for this packet.

## Authorized Namespaces

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel*
```

## Not Authorized

```text
Wave 1 rerun
Wave 2 recovery
Wave 3 rerun
original l2b_n20 mutation
original l2b_n20_attempt2 mutation
Lane A namespace mutation
Lane B namespace mutation
L2b-2 mutation
L2b-2 recovery mutation
Fireworks execution
L3
mlruns
profiler/benchmark/speedup output
overwrite
retry
resume
```

Analyzer, report, and billing reconciliation remain blocked unless the full
logical target is complete and separately validated. Billing reconciliation is
authorized only after the Wave 4 run. Modal empty-tag billing caveat applies:
empty or missing tags are not reportable proof of zero spend.

Timing observability is sidecar-only diagnostic evidence. It is not primary
performance evidence and does not authorize profiler, benchmark, or speedup
outputs.

## Exact Commands

Dry plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave4_parallel_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave4_parallel_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future Wave 4 launch:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave4_parallel_full_coverage --l2b-shard-selector matmul__fp32 --kernel-class matmul --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_WAVE4_AUTHORIZATION_PACKET_V1
```

Wave 4 validation:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_wave4_parallel_full_coverage --wave-id wave_4 --expected-rows 240 --require-content-hash-sidecars --require-observability-sidecars
```

## Launch Script

```text
scripts/run_l2b_n20_attempt2_wave4_parallel.sh
```

The script requires `TRITONGEN_MLFLOW=0`, source/docs/scripts/test/runtime
clean state, origin alignment, absent Wave 4 targets, and tolerates dirty
worktree paths only for live Lane A/B artifact namespaces and `docs/paper_draft/`.
