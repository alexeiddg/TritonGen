# Full Pipeline L2b n20 Attempt2 Two-Lane Rescue Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.0`
packet_type: signed emergency two-lane rescue authorization packet
target_branch: `codex-track-handoff-context`
selector_profile_ids:
- `l2b_n20_attempt2_wave2_missing360_recovery_full_coverage`
- `l2b_n20_attempt2_wave3_parallel_full_coverage`
status: `SIGNED_TWO_LANE_RESCUE_ONLY_NO_EXECUTION_DURING_PACKET_PREPARATION`
classification: `L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_READY`

```text
AUTHORIZES_EXECUTION: YES_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
MODAL_AUTHORIZED: YES_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
GPU_AUTHORIZED: YES_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
GENERATION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_RESCUE_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_RESCUE_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: NO
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
FIREWORKS_EXECUTION_AUTHORIZED: NO
L2B_N20_ORIGINAL_MUTATION_AUTHORIZED: NO
L2B_N20_ATTEMPT2_MUTATION_AUTHORIZED: NO
L2B_N2_MUTATION_AUTHORIZED: NO
L2B_N2_RECOVERY_MUTATION_AUTHORIZED: NO
L3_AUTHORIZED: NO
MLRUNS_MUTATION_AUTHORIZED: NO
PROFILER_BENCHMARK_SPEEDUP_OUTPUT_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_ONLY
```

This packet authorizes only the two create-only rescue namespaces below. The
existing `l2b_n20_attempt2` namespace remains read-only provenance and is used
only as validation input.

## Current Attempt2 State

Read-only validation state at packet preparation:

```text
Wave 1: 720/720 rows, validation pass
Wave 2: 360/720 rows, validation fail only because 360 logical keys remain missing
current available rows in l2b_n20_attempt2: 1080
duplicate logical keys observed by validator: 0
stop classification: SLOW_CELL_BUDGET_EXCEEDED
stop cell: reduction__fp16 / template_upper_bound__c_on__p_off
observed stop duration: 15566.619s > prior signed 7200s
```

Read-only missing-key manifest:

```text
manifest: audits/l2b_n20_attempt2_wave2_missing360_recovery_manifest.json
classification: L2B_N20_ATTEMPT2_WAVE2_MISSING360_MANIFEST_READY
completed Wave 2 logical keys: 360
missing Wave 2 logical keys: 360
partial cell files: 0
```

## Authorized Lanes

Lane A:

```text
stage: l2b_n20_attempt2_wave2_missing360_recovery_full_coverage
namespace: l2b_n20_attempt2_wave2_missing360_recovery
scope: Wave 2 missing-key recovery only
selector: wave:3:3
cell selector: template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on
expected rows: 360
expected shards: reduction__fp32, reduction__fp16, reduction__bf16
```

Lane B:

```text
stage: l2b_n20_attempt2_wave3_parallel_full_coverage
namespace: l2b_n20_attempt2_wave3_parallel
scope: Wave 3 matmul fp16 and bf16 only
selector: wave:7:2
expected rows: 480
expected shards: matmul__fp16, matmul__bf16
```

Wave 4 / `matmul__fp32` is not authorized by this packet.

## Exact Signed Commands

Lane A launch:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave2_missing360_recovery_full_coverage --l2b-shard-selector wave:3:3 --l2b-recovery-cells template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

Lane B launch:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave3_parallel_full_coverage --l2b-shard-selector wave:7:2 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

Lane A validation:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_wave2_missing360_recovery_full_coverage --wave-id wave_2 --l2b-recovery-cells template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --expected-rows 360 --require-content-hash-sidecars --require-observability-sidecars
```

Lane A cumulative validation:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_two_lane_rescue_union --mode lane-a --expected-total-rows 1440
```

Lane B validation:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_wave3_parallel_full_coverage --wave-id wave_3 --expected-rows 480 --require-content-hash-sidecars --require-observability-sidecars
```

Full two-lane union validation:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_two_lane_rescue_union --mode full --expected-total-rows 1920
```

## Concurrency And Budgets

```text
max_concurrent_lanes: 2
max_total_gpu_concurrency_across_lanes: 2
max_total_container_concurrency_across_lanes: 20
lane_a_max_gpu_concurrency: 1
lane_a_max_container_concurrency: 10
lane_b_max_gpu_concurrency: 1
lane_b_max_container_concurrency: 10
lane_a_general_reduction_cell_budget_seconds: 18000
lane_a_known_slow_cell_budget_seconds: 18000
lane_b_matmul_fp16_bf16_cell_budget_seconds: 14400
```

If either lane exceeds its signed budget, stop only that lane and preserve its
partial lane state. No automatic continuation is authorized.

## Namespaces

Authorized output namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel/
```

Forbidden mutation namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
mlruns/
docs/preliminary_report/
```

## Execution Scripts

```text
scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_a.sh
scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_b.sh
scripts/run_l2b_n20_attempt2_two_lane_rescue_parallel.sh
```

The scripts require `TRITONGEN_MLFLOW=0`, a clean worktree, local/origin
alignment, existing attempt2 source artifacts, and absent rescue target paths.
They write logs to `/tmp/tritongen_l2b_n20_attempt2_two_lane_rescue_logs/`.
