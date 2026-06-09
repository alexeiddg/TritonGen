# Fireworks GBNF n20 Wave 4 Validation Report

## Scope

This report records the validation result for `fireworks_gbnf_n20` Wave 4 after
the interrupted run was resumed.

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
condition_cell: wave_4
n: 20
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_4.jsonl
initial_run_app: ap-47QgLLTdFiZaTx1meGbQnq
resume_run_id: a12c5134-abed-443d-a650-d11c9f1c1059
expected_rows: 540
```

Wave 4 includes:

```text
grammar_off__c_on__p_on
task_agnostic__c_on__p_on
template_upper_bound__c_on__p_on
```

The first Wave 4 attempt stopped after 528 unique rows. The same wave was
resumed with `--resume`, which wrote the 12 missing rows. The final file is
complete and duplicate-free.

## Validation Summary

```text
rows: 540
unique: 540
duplicates: 0
run_tiers: ['fireworks_gbnf_n20']
billing_or_auth_provider_errors: 0
grammar_provider_errors: 5
timeout_provider_errors: 1
```

Validated kernel/dtype coverage:

```text
kernel_classes: elementwise, matmul, reduction
dtypes: bf16, fp16, fp32
```

Failure-code distribution:

```text
success: 250
F1_RUNTIME: 188
F0_PARSE: 52
F0_BAD_SIGNATURE: 33
F1_COMPILE: 11
F3_EVAL_PIPELINE: 6
```

By condition:

```text
grammar_off__c_on__p_on:          180 rows, 50 compile_success, 1 timeout_provider_error
task_agnostic__c_on__p_on:        180 rows, 26 compile_success, 5 grammar_provider_errors
template_upper_bound__c_on__p_on: 180 rows, 174 compile_success, 0 provider_errors
```

## Interpretation

Wave 4 is structurally complete and accepted for combined validation. Five
`F3_EVAL_PIPELINE` rows are provider-side Fireworks grammar-processing failures
in the broad `task_agnostic` grammar. One additional `F3_EVAL_PIPELINE` row is
a provider/network timeout in `grammar_off`; it is an operational provider
failure and should not be interpreted as a Triton compile/runtime failure.
