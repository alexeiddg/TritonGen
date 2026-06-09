# Fireworks GBNF n20 Wave 1 Provider Error Report

## Scope

This report documents the Fireworks provider-side grammar failure observed
during the `fireworks_gbnf_n20` Wave 1 manual run and the mitigation applied to
preserve row-level auditability.

This is an operational audit for the Fireworks API + Modal runner. It is not an
analyzer refresh, report refresh, billing report, or paper conclusion.

## Run Context

```text
experiment_id: fireworks_api_modal_v1
run_tier: fireworks_gbnf_n20
model_slot: FW-B
model_id: accounts/fireworks/models/minimax-m2p7
provider_api: chat_completions
fireworks_grammar_mode: gbnf
condition_cell: wave_1
n: 20
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_1.jsonl
expected_rows: 540
```

Wave 1 includes:

```text
grammar_off__c_off__p_off
task_agnostic__c_off__p_off
template_upper_bound__c_off__p_off
```

## Incident

The first Wave 1 run stopped after writing 487 rows. Fireworks returned HTTP
400 for some grammar-constrained requests using the `task_agnostic` grammar.

Observed provider message:

```text
Grammar processing took too much time. Likely the grammar allows too much
branching. Please simplify the grammar or reach out to Fireworks for support.
```

The failure occurred before source generation for affected rows. It is a
provider-side structured-output grammar processing failure, not a Modal compile
failure, not a CUDA failure, and not a local parsing failure.

## Root Cause

The local task-agnostic grammar:

```text
cluster1/grammar/triton_kernel_agnostic.gbnf
```

is intentionally broad. After normalization for Fireworks grammar mode, the
grammar is syntactically accepted, but some requests exceed Fireworks'
provider-side grammar processing budget because the grammar permits too much
branching.

The stricter template grammar:

```text
cluster1/grammar/triton_kernel.gbnf
```

did not show this provider-side processing failure in Wave 1.

## Mitigation

The Fireworks runner was changed so provider exceptions no longer abort an
entire wave. A provider exception is now converted into a normal JSONL result
row with:

```text
provider_error_type: RuntimeError
provider_error_msg: <truncated provider error>
finish_reason: provider_error
source: ""
compile_success: false
failure_code: F3_EVAL_PIPELINE
compile_error_type: ProviderError
response_format_type: grammar
raw_response_shape_version: fireworks_provider_exception_v1
```

The row still preserves the planned identity:

```text
model_slot
condition_id
kernel_class
dtype
generation_seed
run_tier
grammar_mode
grammar_variant
grammar_path
grammar_sha256
response_format_grammar_sha256
prompt_sha256
```

This keeps the n20 wave resumable and auditable without silently dropping
provider failures.

## Resume Result

The wave was resumed with `--resume`. The resume wrote 53 additional rows,
bringing the wave to the expected row count.

Validation summary:

```text
rows: 540
unique: 540
duplicates: 0
run_tiers: ['fireworks_gbnf_n20']
grammar_rows: 360
provider_errors: 4
```

Final Wave 1 compile summary:

```text
compile_success: 240 / 540
provider_errors: 4 / 540
```

By condition:

```text
grammar_off__c_off__p_off:          180 rows, 47 compile_success, 0 provider_errors
task_agnostic__c_off__p_off:        180 rows, 26 compile_success, 4 provider_errors
template_upper_bound__c_off__p_off: 180 rows, 167 compile_success, 0 provider_errors
```

Failure-code distribution:

```text
success: 240
F1_RUNTIME: 188
F0_PARSE: 67
F0_BAD_SIGNATURE: 28
F1_COMPILE: 13
F3_EVAL_PIPELINE: 4
```

## Interpretation Boundary

The `F3_EVAL_PIPELINE` rows in this wave indicate provider-side grammar
processing failures for Fireworks structured output. They should not be counted
as model-generated Triton source failures because no source was produced.

For paper reporting, these rows should be separated or explicitly labeled as
provider/grammar-engine failures when comparing:

```text
grammar_off
task_agnostic GBNF
template_upper_bound GBNF
```

The provider errors are especially relevant for `task_agnostic` because they
show that provider-side GBNF feasibility differs from local XGrammar feasibility.

## Operator Guidance

If a future wave prints a remote Fireworks traceback but the local entrypoint
finishes with a `rows_written` summary, validate the JSONL before rerunning.
The traceback may correspond to rows captured as provider errors rather than a
failed wave.

Expected per-wave validation:

```text
rows: 540
unique: 540
run_tiers: ['fireworks_gbnf_n20']
```

If a wave stops before 540 rows, rerun the same wave with `--resume`.
