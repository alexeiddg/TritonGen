# L2b n20 Attempt2 Two-Lane Rescue Authorization Report

classification: `L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_READY`

## Scope

This report records a no-execution preparation of an emergency two-lane rescue
authorization for `l2b_n20_attempt2`. No Modal launch, GPU job, generation,
analyzer, report, billing query, output deletion, or artifact overwrite occurred
during preparation.

## Current Partial Row State

```text
source namespace: l2b_n20_attempt2
Wave 1: 720/720 rows, validation pass
Wave 2: 360/720 rows, validation fail due to 360 missing logical keys
current source total: 1080 rows
duplicate logical keys: 0
stop: SLOW_CELL_BUDGET_EXCEEDED
slow cell: reduction__fp16 / template_upper_bound__c_on__p_off
observed duration: 15566.619s > prior signed 7200s
```

Read-only validator evidence:

```json
{"actual_rows": 720, "classification": "L2B_FULL_COVERAGE_VALIDATION_PASS", "complete_shards": 3, "duplicate_logical_keys": 0, "expected_rows": 720, "missing_logical_keys": 0, "stage": "l2b_n20_attempt2_full_coverage", "wave_id": "wave_1"}
{"actual_rows": 360, "classification": "L2B_FULL_COVERAGE_VALIDATION_FAIL", "duplicate_logical_keys": 0, "expected_rows": 720, "missing_logical_keys": 360, "stage": "l2b_n20_attempt2_full_coverage", "wave_id": "wave_2"}
```

## Missing-Key Manifest

Manifest path:

```text
audits/l2b_n20_attempt2_wave2_missing360_recovery_manifest.json
```

Manifest result:

```text
classification: L2B_N20_ATTEMPT2_WAVE2_MISSING360_MANIFEST_READY
completed Wave 2 logical keys: 360
missing Wave 2 logical keys: 360
partial cell files: 0
Lane A expected rows: 360
```

## Lane A

```text
namespace: l2b_n20_attempt2_wave2_missing360_recovery
stage: l2b_n20_attempt2_wave2_missing360_recovery_full_coverage
scope: Wave 2 missing cells only
expected rows: 360
validation after lane: source Wave 1 + source partial Wave 2 + Lane A = 1440 rows
```

Exact signed command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave2_missing360_recovery_full_coverage --l2b-shard-selector wave:3:3 --l2b-recovery-cells template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

## Lane B

```text
namespace: l2b_n20_attempt2_wave3_parallel
stage: l2b_n20_attempt2_wave3_parallel_full_coverage
scope: Wave 3 matmul fp16/bf16 only
expected rows: 480
validation after both lanes: source 1080 + Lane A 360 + Lane B 480 = 1920 rows
```

Exact signed command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n20_attempt2_wave3_parallel_full_coverage --l2b-shard-selector wave:7:2 --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

## Explicit Non-Authorization

Wave 4 / `matmul__fp32` is not authorized. Original `l2b_n20`,
`l2b_n20_attempt2`, `l2b_n2`, and `l2b_n2_recovery_missing28` namespaces are
read-only inputs or forbidden mutation targets. Fireworks, L3, mlruns,
profiler/benchmark/speedup output, analyzer/report generation, and billing
queries are not authorized.

## Validation Plan

Static checks for this preparation:

```bash
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_a.sh
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_b.sh
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_parallel.sh
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Runtime validations embedded in scripts:

```bash
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_wave2_missing360_recovery_full_coverage --wave-id wave_2 --l2b-recovery-cells template_upper_bound__c_off__p_on,template_upper_bound__c_on__p_on,task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on --expected-rows 360 --require-content-hash-sidecars --require-observability-sidecars
.venv/bin/python -m cluster3.analysis.validate_l2b_full_coverage --stage l2b_n20_attempt2_wave3_parallel_full_coverage --wave-id wave_3 --expected-rows 480 --require-content-hash-sidecars --require-observability-sidecars
.venv/bin/python -m cluster3.analysis.validate_l2b_two_lane_rescue_union --mode lane-a --expected-total-rows 1440
.venv/bin/python -m cluster3.analysis.validate_l2b_two_lane_rescue_union --mode full --expected-total-rows 1920
```
