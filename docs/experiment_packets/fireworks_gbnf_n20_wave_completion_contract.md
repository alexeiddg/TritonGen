# Fireworks GBNF n20 Wave Completion Contract

## Contract Identity

contract_id: `FIREWORKS_GBNF_N20_WAVE_COMPLETION_CONTRACT_V1`
contract_version: `1.0.0`
contract_type: bounded manual operator contract
status: `READY_FOR_MANUAL_WAVE_COMPLETION`
experiment_id: `fireworks_api_modal_v1`
run_tier: `fireworks_gbnf_n20`
output_namespace: `outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf`

Execution authorization surface:

```text
MODAL_AUTHORIZED: YES_MANUAL_WAVE_COMMANDS_ONLY
FIREWORKS_API_CALL_AUTHORIZED: YES_MANUAL_WAVE_COMMANDS_ONLY
GENERATION_AUTHORIZED: YES_FW_B_MINIMAX_GBNF_N20_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_WAVES_2_TO_4_AND_RESUME_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2_N20_GBNF_NAMESPACE_ONLY
ARTIFACT_MUTATION_AUTHORIZED: NO
MLRUNS_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
MODEL_CHANGE_AUTHORIZED: NO
GRAMMAR_CHANGE_AUTHORIZED: NO
RETRY_TO_FORCE_PROVIDER_SUCCESS_AUTHORIZED: NO
```

This contract exists to finish the Fireworks GBNF n20 run manually after the
Wave 1 provider-side grammar incident. It authorizes completing the remaining
waves while preserving Fireworks grammar-engine failures as auditable result
rows with `failure_code=F3_EVAL_PIPELINE`.

Provider-error rows caused by account, billing, quota, suspension, or
precondition failures are also preserved as F3 rows for auditability, but they
do not count as an accepted scientific wave. They are stop-condition evidence,
not model/grammar performance evidence.

This contract does not authorize analyzer refreshes, report refreshes, billing
queries, paper-scale claims, model substitution, grammar simplification, output
deletion, or mutation outside the listed output namespace.

## Fixed Run Parameters

The remaining manual waves must use exactly these scientific parameters:

```text
model_slot: FW-B
model_id: accounts/fireworks/models/minimax-m2p7
provider_api: chat_completions
fireworks_grammar_mode: gbnf
n: 20
temperature: 0
max_output_tokens: 4096
kernel_class: all
dtypes: all
compile_modal: true
authorization_token: FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1
```

The run uses the 12-cell `grammar_mode x C x P` selector, split into four
waves:

```text
wave_1:
  grammar_off__c_off__p_off
  task_agnostic__c_off__p_off
  template_upper_bound__c_off__p_off

wave_2:
  grammar_off__c_on__p_off
  task_agnostic__c_on__p_off
  template_upper_bound__c_on__p_off

wave_3:
  grammar_off__c_off__p_on
  task_agnostic__c_off__p_on
  template_upper_bound__c_off__p_on

wave_4:
  grammar_off__c_on__p_on
  task_agnostic__c_on__p_on
  template_upper_bound__c_on__p_on
```

Expected row counts:

```text
rows_per_wave: 540
completed_wave_1_rows: 540
remaining_waves: 3
remaining_rows: 1620
final_total_rows: 2160
unique_key: model_slot + condition_id + kernel_class + dtype + generation_seed
```

## F3 Provider-Error Rule

If Fireworks returns a provider-side grammar-processing error, including:

```text
Grammar processing took too much time. Likely the grammar allows too much
branching.
```

the affected planned row must remain in the JSONL output as a normal result row
with:

```text
finish_reason: provider_error
source: ""
provider_error_type: RuntimeError
compile_success: false
compile_error_type: ProviderError
failure_code: F3_EVAL_PIPELINE
raw_response_shape_version: fireworks_provider_exception_v1
```

These rows are not missing data and must not be deleted, overwritten, manually
edited into success rows, or retried selectively to force a generated source.
They represent a provider-side structured-output limitation of Fireworks GBNF,
especially for the broad `task_agnostic` grammar.

If a wave stops before reaching 540 rows, rerun the same wave with `--resume`.
If a wave prints a traceback but still reports `rows_written` and completes,
validate the JSONL before rerunning; the traceback may correspond to captured
F3 provider-error rows.

## Account/Billing Precondition Rule

If Fireworks returns an account-level precondition error, including HTTP 412
messages such as:

```text
Account ... is suspended, possibly due to reaching the monthly spending limit
or failure to pay past invoices.
```

the runner may still preserve the planned rows as:

```text
finish_reason: provider_error
compile_success: false
compile_error_type: ProviderError
failure_code: F3_EVAL_PIPELINE
```

However, these rows are classified as `billing_412_provider_error` for
operational audit purposes. They are not evidence about Minimax, Triton,
template grammar, task-agnostic grammar, C-loop behavior, or P-loop behavior.

Required action:

```text
1. Stop launching new waves.
2. Preserve the contaminated JSONL as an audit artifact.
3. Fix Fireworks account/API-key/billing access outside the experiment output.
4. Rerun the affected wave only after access is restored.
5. Prefer writing the corrected rerun to a fresh output path unless a separate
   operator note explicitly accepts replacing the contaminated wave file.
```

## Current Wave 1 Baseline

Wave 1 is already complete and should be treated as accepted baseline input for
the final combined validation:

```text
output: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_1.jsonl
rows: 540
unique: 540
provider_errors: 4
F3_EVAL_PIPELINE: 4
```

Operational audit:

```text
audits/fireworks_gbnf_n20_wave1_provider_error_report.md
```

## Authorized Wave Commands

Run one wave at a time. Validate each wave before starting the next one.

### Wave 2

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal \
  --run-tier fireworks_gbnf_n20 \
  --signed-fireworks-authorization FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1 \
  --models FW-B \
  --model-id-overrides FW-B=accounts/fireworks/models/minimax-m2p7 \
  --provider-api chat_completions \
  --fireworks-grammar-mode gbnf \
  --condition-cell wave_2 \
  --kernel-class all \
  --dtypes all \
  --n 20 \
  --temperature 0 \
  --max-output-tokens 4096 \
  --compile-modal \
  --output outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2.jsonl \
  --overwrite
```

If interrupted before 540 rows:

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal \
  --run-tier fireworks_gbnf_n20 \
  --signed-fireworks-authorization FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1 \
  --models FW-B \
  --model-id-overrides FW-B=accounts/fireworks/models/minimax-m2p7 \
  --provider-api chat_completions \
  --fireworks-grammar-mode gbnf \
  --condition-cell wave_2 \
  --kernel-class all \
  --dtypes all \
  --n 20 \
  --temperature 0 \
  --max-output-tokens 4096 \
  --compile-modal \
  --output outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2.jsonl \
  --resume
```

### Wave 3

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal \
  --run-tier fireworks_gbnf_n20 \
  --signed-fireworks-authorization FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1 \
  --models FW-B \
  --model-id-overrides FW-B=accounts/fireworks/models/minimax-m2p7 \
  --provider-api chat_completions \
  --fireworks-grammar-mode gbnf \
  --condition-cell wave_3 \
  --kernel-class all \
  --dtypes all \
  --n 20 \
  --temperature 0 \
  --max-output-tokens 4096 \
  --compile-modal \
  --output outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_3.jsonl \
  --overwrite
```

If interrupted before 540 rows, rerun the same command replacing
`--overwrite` with `--resume`.

### Wave 4

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal \
  --run-tier fireworks_gbnf_n20 \
  --signed-fireworks-authorization FIREWORKS_API_MODAL_GBNF_N20_AUTHORIZATION_PACKET_V1 \
  --models FW-B \
  --model-id-overrides FW-B=accounts/fireworks/models/minimax-m2p7 \
  --provider-api chat_completions \
  --fireworks-grammar-mode gbnf \
  --condition-cell wave_4 \
  --kernel-class all \
  --dtypes all \
  --n 20 \
  --temperature 0 \
  --max-output-tokens 4096 \
  --compile-modal \
  --output outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_4.jsonl \
  --overwrite
```

If interrupted before 540 rows, rerun the same command replacing
`--overwrite` with `--resume`.

## Per-Wave Validation Command

Replace `wave_2` with the wave being validated.

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

wave = "wave_2"
path = Path(f"outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_{wave}.jsonl")
rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
keys = [
    (
        row["model_slot"],
        row["condition_id"],
        row["kernel_class"],
        row["dtype"],
        row["generation_seed"],
    )
    for row in rows
]
provider_errors = [row for row in rows if row.get("finish_reason") == "provider_error"]
f3_rows = [row for row in rows if row.get("failure_code") == "F3_EVAL_PIPELINE"]
billing_errors = [
    row
    for row in provider_errors
    if any(
        marker in (row.get("provider_error_msg") or "").lower()
        for marker in (
            "412",
            "precondition",
            "suspended",
            "spending limit",
            "quota",
            "billing",
            "authentication",
            "unauthorized",
            "forbidden",
        )
    )
]

print("path:", path)
print("rows:", len(rows))
print("unique:", len(set(keys)))
print("duplicates:", len(keys) - len(set(keys)))
print("run_tiers:", sorted({row.get("run_tier") for row in rows}))
print("conditions:", sorted({row.get("condition_id") for row in rows}))
print("provider_errors:", len(provider_errors))
print("F3_EVAL_PIPELINE:", len(f3_rows))
print("billing_or_auth_provider_errors:", len(billing_errors))
print("failure_codes:", Counter(row.get("failure_code") or "success" for row in rows))

assert len(rows) == 540
assert len(set(keys)) == 540
assert {row.get("run_tier") for row in rows} == {"fireworks_gbnf_n20"}
assert len({row.get("condition_id") for row in rows}) == 3
assert all(row.get("failure_code") == "F3_EVAL_PIPELINE" for row in provider_errors)
assert not billing_errors
PY
```

## Combined Validation Command

Run this only after Wave 1 through Wave 4 all validate individually.

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

root = Path("outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf")
paths = [
    root / "fw_b_minimax_wave_1.jsonl",
    root / "fw_b_minimax_wave_2_rerun_after_billing.jsonl",
    root / "fw_b_minimax_wave_3.jsonl",
    root / "fw_b_minimax_wave_4.jsonl",
]
rows = []
for path in paths:
    wave_rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(path.name, len(wave_rows))
    rows.extend(wave_rows)

keys = [
    (
        row["model_slot"],
        row["condition_id"],
        row["kernel_class"],
        row["dtype"],
        row["generation_seed"],
    )
    for row in rows
]
provider_errors = [row for row in rows if row.get("finish_reason") == "provider_error"]
f3_rows = [row for row in rows if row.get("failure_code") == "F3_EVAL_PIPELINE"]
billing_errors = [
    row
    for row in provider_errors
    if any(
        marker in (row.get("provider_error_msg") or "").lower()
        for marker in (
            "412",
            "precondition",
            "suspended",
            "spending limit",
            "quota",
            "billing",
            "authentication",
            "unauthorized",
            "forbidden",
        )
    )
]

print("total_rows:", len(rows))
print("unique:", len(set(keys)))
print("duplicates:", len(keys) - len(set(keys)))
print("run_tiers:", sorted({row.get("run_tier") for row in rows}))
print("conditions:", len({row.get("condition_id") for row in rows}))
print("kernel_classes:", sorted({row.get("kernel_class") for row in rows}))
print("dtypes:", sorted({row.get("dtype") for row in rows}))
print("provider_errors:", len(provider_errors))
print("F3_EVAL_PIPELINE:", len(f3_rows))
print("billing_or_auth_provider_errors:", len(billing_errors))
print("failure_codes:", Counter(row.get("failure_code") or "success" for row in rows))

assert len(rows) == 2160
assert len(set(keys)) == 2160
assert {row.get("run_tier") for row in rows} == {"fireworks_gbnf_n20"}
assert len({row.get("condition_id") for row in rows}) == 12
assert {row.get("kernel_class") for row in rows} == {"elementwise", "reduction", "matmul"}
assert {row.get("dtype") for row in rows} == {"fp32", "fp16", "bf16"}
assert all(row.get("failure_code") == "F3_EVAL_PIPELINE" for row in provider_errors)
assert not billing_errors
PY
```

## Stop Conditions

Stop manual execution and request a new contract if any of the following
occurs:

- A wave produces duplicate unique keys after resume.
- A wave reaches more than 540 rows.
- A wave writes outside `outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf`.
- A command requires changing model, provider API, grammar mode, grammar files,
  kernel classes, dtypes, or `n`.
- Provider errors appear with missing `failure_code=F3_EVAL_PIPELINE`.
- Provider errors contain HTTP 401, 403, 412, account suspension, spending
  limit, quota, authentication, or billing/precondition messages.
- Modal compile infrastructure fails globally rather than row-locally.

Provider/network timeouts may be preserved as `F3_EVAL_PIPELINE` for
auditability, but they must be counted separately from grammar-processing
failures in any validation report.

## Reporting Boundary

After the four waves validate, the output can be described as a completed
Fireworks GBNF n20 run for FW-B/minimax with explicit provider-error accounting.

Any paper-facing interpretation must separate:

```text
model/generated-code failures
Triton compile/runtime failures
Fireworks provider-side GBNF grammar-engine failures
```

The `F3_EVAL_PIPELINE` provider-error rows are part of the empirical finding
about provider-side constrained decoding feasibility. They should be reported as
such, not hidden as missing rows and not merged into ordinary Triton compile
failures without qualification.
