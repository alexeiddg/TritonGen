# L2b n20 Attempt2 Two-Lane Rescue Stage Allowlist Patch Report

classification: `L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_STAGE_ALLOWLIST_READY`

## Scope

This patch is a no-execution runtime gate fix for the signed two-lane rescue
authorization packet:

```text
FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

No Modal launch, GPU job, generation, row creation, analyzer, report, billing
query, output deletion, or artifact overwrite occurred.

## Root Cause

The signed rescue stages were present in the planning constants and runtime
authorization validation, but `_run_signed_l2b_selector` still had an older
three-stage allowlist:

```text
l2b_n2_full_coverage
l2b_n20_full_coverage
l2b_n20_attempt2_full_coverage
```

After prelaunch validation, Lane A and Lane B reached selector expansion and
failed before Modal execution with:

```text
ValueError: signed L2b selector requires an approved L2b stage
```

## Stages Approved

The selector expansion allowlist now includes:

```text
l2b_n20_attempt2_wave2_missing360_recovery_full_coverage
l2b_n20_attempt2_wave3_parallel_full_coverage
```

## Token Constraints

Both rescue stages are approved only under:

```text
FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N20_ATTEMPT2_TWO_LANE_RESCUE_AUTHORIZATION_PACKET_V1
```

Lane A remains constrained to:

```text
namespace: l2b_n20_attempt2_wave2_missing360_recovery
selector: wave:3:3
expected rows: 360
recovery cells:
  template_upper_bound__c_off__p_on
  template_upper_bound__c_on__p_on
  task_agnostic__c_off__p_off
  task_agnostic__c_on__p_off
  task_agnostic__c_off__p_on
  task_agnostic__c_on__p_on
```

Lane B remains constrained to:

```text
namespace: l2b_n20_attempt2_wave3_parallel
selector: wave:7:2
scope: matmul__fp16 and matmul__bf16
expected rows: 480
```

The rescue token does not authorize original `l2b_n20_attempt2`, original
`l2b_n20`, `l2b_n2`, `l2b_n2_recovery_missing28`, Wave 4 / `matmul__fp32`,
Fireworks, L3, profiler, benchmark, speedup, mlruns, overwrite, retry, or
resume behavior.

## Tests Added

`cluster3/tests/test_run_cluster3_modal_cli.py` now proves:

```text
Lane A reaches mocked Modal dispatch with the two-lane rescue token.
Lane B reaches mocked Modal dispatch with the two-lane rescue token.
Lane A with the original attempt2 token fails closed.
Lane B with the original attempt2 token fails closed.
The rescue token cannot run the original attempt2 stage.
The rescue token cannot run Wave 4.
Overwrite, retry, and resume fail.
MLflow enabled fails.
Wrong namespace fails.
```

The mocked dispatch tests replace the Modal app context and `run_cluster3`;
they do not write outputs, artifacts, or mlruns.

## Validation Plan

Required static validation:

```bash
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_a.sh
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_lane_b.sh
bash -n scripts/run_l2b_n20_attempt2_two_lane_rescue_parallel.sh
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```
