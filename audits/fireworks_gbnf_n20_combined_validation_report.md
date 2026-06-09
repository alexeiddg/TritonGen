# Fireworks GBNF n20 Combined Validation Report

## Scope

This report records the combined validation result for the completed
`fireworks_gbnf_n20` FW-B/Minimax run.

This is an operational audit. It is not an analyzer refresh, report refresh,
billing reconciliation, or paper conclusion.

## Accepted Input Files

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_1.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2_rerun_after_billing.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_3.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_4.jsonl
```

The original Wave 2 file:

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2.jsonl
```

is excluded from combined validation because it was contaminated by Fireworks
HTTP 412 account/billing precondition errors.

## Combined Validation Summary

```text
total_rows: 2160
unique: 2160
duplicates: 0
run_tiers: ['fireworks_gbnf_n20']
conditions: 12
kernel_classes: elementwise, matmul, reduction
dtypes: bf16, fp16, fp32
billing_or_auth_provider_errors: 0
provider_errors: 22
grammar_provider_errors: 21
timeout_provider_errors: 1
compile_success: 990 / 2160
```

Failure-code distribution:

```text
success: 990
F1_RUNTIME: 757
F0_PARSE: 236
F0_BAD_SIGNATURE: 110
F1_COMPILE: 45
F3_EVAL_PIPELINE: 22
```

Finish-reason distribution:

```text
stop: 1227
length: 911
provider_error: 22
```

## Condition-Level Summary

```text
grammar_off__c_off__p_off:          180 rows, 47 compile_success
grammar_off__c_off__p_on:           180 rows, 51 compile_success
grammar_off__c_on__p_off:           180 rows, 50 compile_success
grammar_off__c_on__p_on:            180 rows, 50 compile_success, 1 timeout_provider_error
task_agnostic__c_off__p_off:        180 rows, 26 compile_success, 4 grammar_provider_errors
task_agnostic__c_off__p_on:         180 rows, 30 compile_success, 7 grammar_provider_errors
task_agnostic__c_on__p_off:         180 rows, 20 compile_success, 5 grammar_provider_errors
task_agnostic__c_on__p_on:          180 rows, 26 compile_success, 5 grammar_provider_errors
template_upper_bound__c_off__p_off: 180 rows, 167 compile_success
template_upper_bound__c_off__p_on:  180 rows, 174 compile_success
template_upper_bound__c_on__p_off:  180 rows, 175 compile_success
template_upper_bound__c_on__p_on:   180 rows, 174 compile_success
```

## Interpretation Boundary

The completed run is structurally valid for downstream analysis:

```text
12 factorial cells x 3 kernel classes x 3 dtypes x 20 seeds = 2160 rows
```

The `F3_EVAL_PIPELINE` rows must be interpreted separately from generated-code
compile/runtime failures:

```text
21 rows: Fireworks provider-side GBNF grammar processing failures
1 row: Fireworks/provider timeout in grammar_off
0 rows: billing/auth/precondition failures in accepted combined inputs
```

The accepted combined input set can be used for analyzer/report work only after
a separate explicit authorization for analyzer/report refresh is given.
