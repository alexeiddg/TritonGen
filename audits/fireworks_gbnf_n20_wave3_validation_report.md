# Fireworks GBNF n20 Wave 3 Validation Report

## Scope

This report records the validation result for `fireworks_gbnf_n20` Wave 3.

This is an operational audit. It is not an analyzer refresh, report refresh,
billing reconciliation, or paper conclusion.

## Run Context

```text
experiment_id: fireworks_api_modal_v1
run_tier: fireworks_gbnf_n20
model_slot: FW-B
model_id: accounts/fireworks/models/minimax-m2p7
provider_api: chat_completions
fireworks_grammar_mode: gbnf
condition_cell: wave_3
n: 20
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_3.jsonl
run_id: a9c71fc9-adff-4891-a217-24fe69849a59
expected_rows: 540
```

Wave 3 includes:

```text
grammar_off__c_off__p_on
task_agnostic__c_off__p_on
template_upper_bound__c_off__p_on
```

## Validation Summary

```text
rows: 540
unique: 540
duplicates: 0
run_tiers: ['fireworks_gbnf_n20']
billing_or_auth_provider_errors: 0
grammar_provider_errors: 7
```

Validated kernel/dtype coverage:

```text
kernel_classes: elementwise, matmul, reduction
dtypes: bf16, fp16, fp32
```

Failure-code distribution:

```text
success: 255
F1_RUNTIME: 183
F0_PARSE: 57
F0_BAD_SIGNATURE: 27
F1_COMPILE: 11
F3_EVAL_PIPELINE: 7
```

By condition:

```text
grammar_off__c_off__p_on:          180 rows, 51 compile_success, 0 provider_errors
task_agnostic__c_off__p_on:        180 rows, 30 compile_success, 7 grammar_provider_errors
template_upper_bound__c_off__p_on: 180 rows, 174 compile_success, 0 provider_errors
```

## Interpretation

Wave 3 is structurally complete and accepted for combined validation. The
`F3_EVAL_PIPELINE` rows are provider-side Fireworks grammar-processing failures
in the broad `task_agnostic` grammar, not billing/account failures.
