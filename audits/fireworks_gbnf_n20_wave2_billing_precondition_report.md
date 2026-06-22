# Fireworks GBNF n20 Wave 2 Billing Precondition Report

## Scope

This report documents the Fireworks account-level precondition failure observed
during the `fireworks_gbnf_n20` Wave 2 manual run.

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
condition_cell: wave_2
n: 20
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2.jsonl
expected_rows: 540
```

Wave 2 includes:

```text
grammar_off__c_on__p_off
task_agnostic__c_on__p_off
template_upper_bound__c_on__p_off
```

## Incident

Fireworks returned HTTP 412 during the wave:

```text
Account ... is suspended, possibly due to reaching the monthly spending limit
or failure to pay past invoices.
```

The runner preserved affected planned rows as provider-error rows instead of
dropping them or aborting without row-level evidence.

## Validation Summary

```text
rows: 540
unique: 540
duplicates: 0
run_tiers: ['fireworks_gbnf_n20']
provider_errors: 426
F3_EVAL_PIPELINE: 426
provider_error_class: billing_412
```

Failure-code distribution:

```text
F3_EVAL_PIPELINE: 426
success: 47
F1_RUNTIME: 35
F0_PARSE: 22
F1_COMPILE: 5
F0_BAD_SIGNATURE: 5
```

By condition:

```text
grammar_off__c_on__p_off:          180 rows, 34 compile_success, 86 billing_412_provider_error
task_agnostic__c_on__p_off:        180 rows, 2 compile_success, 171 billing_412_provider_error
template_upper_bound__c_on__p_off: 180 rows, 11 compile_success, 169 billing_412_provider_error
```

## Interpretation

This Wave 2 file is structurally complete but scientifically contaminated by an
account/billing precondition failure. The `F3_EVAL_PIPELINE` rows in this file
are not evidence about model capability, grammar quality, Triton compilation,
C-loop behavior, or P-loop behavior.

The file should be preserved for auditability, but Wave 2 should be rerun after
Fireworks account/API-key/billing access is restored. Do not continue to Wave 3
or Wave 4 until this access issue is resolved.

## Required Next Step

After account access is restored, rerun Wave 2 under the same fixed scientific
parameters. Prefer a fresh output path so the billing-contaminated artifact
remains available for audit.

## Rerun Closure

Wave 2 was rerun after the billing/account precondition was cleared:

```text
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2_rerun_after_billing.jsonl
run_id: fb050cdc-d901-4783-a395-f3671cc4080d
rows: 540
unique: 540
duplicates: 0
billing_or_auth_provider_errors: 0
grammar_provider_errors: 5
```

Validated condition coverage:

```text
grammar_off__c_on__p_off
task_agnostic__c_on__p_off
template_upper_bound__c_on__p_off
```

Validated kernel/dtype coverage:

```text
kernel_classes: elementwise, matmul, reduction
dtypes: bf16, fp16, fp32
```

Failure-code distribution:

```text
success: 245
F1_RUNTIME: 198
F0_PARSE: 60
F0_BAD_SIGNATURE: 22
F1_COMPILE: 10
F3_EVAL_PIPELINE: 5
```

By condition:

```text
grammar_off__c_on__p_off:          180 rows, 50 compile_success, 0 provider_errors
task_agnostic__c_on__p_off:        180 rows, 20 compile_success, 5 grammar_provider_errors
template_upper_bound__c_on__p_off: 180 rows, 175 compile_success, 0 provider_errors
```

The accepted Wave 2 file for combined validation is:

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2_rerun_after_billing.jsonl
```

The original `fw_b_minimax_wave_2.jsonl` remains a contaminated billing
precondition artifact and must not be used in the final combined n20 analysis.
