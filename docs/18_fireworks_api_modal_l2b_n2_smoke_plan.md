# Fireworks API + Modal L2b n=2 Smoke Plan

- Version: 0.1.0
- Date: 2026-06-06
- Branch: `codex/fireworks-api-modal-implementation-plan`
- Baseline: `4b85c24 Audit L2 n20 runtime gate promotion`
- Status: `IMPLEMENTATION_SCAFFOLD_ADDED — EXECUTION_NOT_RUN`
- Scope: Fireworks API integration scaffold, provider smoke contract, and
  L2b n=2 smoke execution packet outline.

## Authorization State

This document originally authorized no code work and no execution. The current
branch now contains implementation scaffolding authorized by the follow-up goal:
integrate Fireworks end to end with Modal and the codebase, and prove the local
contract works without running paid/provider execution.

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
MLRUNS_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
FIREWORKS_API_CALL_AUTHORIZED: NO
CODE_WORK_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
LOCKFILE_CHANGE_AUTHORIZED: NO
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
```

Provider execution remains blocked until a separate signed authorization packet
sets the Fireworks/Modal/API/output flags to `YES` and names the exact secret,
row cap, command, branch, and output namespace.

## Purpose

This plan narrows the earlier Fireworks full-factorial n=20 concept to a small
pre-implementation package:

1. define the Fireworks API provider boundary;
2. define metadata and response-format handling needed because Fireworks is
   OpenAI-compatible but not guaranteed to be byte-identical to OpenAI,
   Anthropic, or Google SDK responses;
3. define a future L2b n=2 smoke packet that can be signed later;
4. preserve the current Modal compile/correctness infrastructure unchanged.

The plan does not create a new result, does not run Fireworks, and does not
promote any Fireworks row into the artifact registry.

## Reduced Scope

The reduced scope is intentionally smaller than a full paper-scale factorial:

| Item | Included now? | Notes |
|---|---:|---|
| Fireworks provider API design | Yes | Implemented under `cluster_fw/providers/`. |
| Provider response normalization | Yes | Implemented for Responses and Chat Completions shapes. |
| Modal API-generation function | Yes | Implemented as a lightweight API-only Modal function. |
| L2b n=2 smoke packet | Planned only | Command templates only; no provider execution. |
| Full 12-cell n=20 Fireworks run | No | Explicitly out of scope. |
| Analyzer/report refresh | No | Explicitly out of scope. |
| Billing query | No | Explicitly out of scope. |
| Dependency or lockfile change | No | Explicitly out of scope. |

## External API Basis

Fireworks exposes OpenAI-compatible APIs under:

```text
https://api.fireworks.ai/inference/v1
```

The Fireworks docs include both a Responses API and a Chat Completions API. The
Responses guide shows OpenAI SDK usage with `base_url` pointed at Fireworks.
The Chat Completions reference documents an OpenAI-compatible
`/chat/completions` route, and the Python client reference notes additional
Fireworks request/response fields beyond the standard OpenAI API.

Implementation must therefore treat Fireworks as a provider backend with a
normalization boundary, not as a direct copy of the existing OpenAI, Claude, or
Gemini adapters.

Reference sources:

- Fireworks Responses API guide: `https://docs.fireworks.ai/guides/response-api`
- Fireworks create response API reference:
  `https://docs.fireworks.ai/api-reference/post-responses`
- Fireworks Chat Completions API reference:
  `https://docs.fireworks.ai/api-reference/post-chatcompletions`
- Fireworks Python client reference:
  `https://docs.fireworks.ai/tools-sdks/python-client/sdk-reference`

## Model Slots

The L2b smoke should support exactly two Fireworks model slots:

| Slot | Model | Fireworks API ID |
|---|---|---|
| FW-A | DeepSeek-R1 (Fast) | `accounts/fireworks/models/deepseek-r1` |
| FW-B | Llama 3.1 405B Instruct | `accounts/fireworks/models/llama-v3p1-405b-instruct` |

The exact model IDs must be validated against Fireworks before code is merged
or a smoke is signed. A model alias must not be silently substituted for a
snapshot or provider ID in result metadata.

Live smoke note: Fireworks' public model pages currently mark DeepSeek R1 Fast,
DeepSeek R1 Basic, DeepSeek V3, and Llama 3.1 405B Instruct as `Serverless:
Not supported`; these frontier models require an accessible Deploy on Demand
deployment for this runner. The CLI supports
`--model-id-overrides SLOT=MODEL_ID` so a signed smoke can bind `FW-A` or `FW-B`
to the exact deployment/model ID visible to the project account.
Do not run placeholder values like
`accounts/TU_CUENTA/models/TU_DEPLOYMENT_O_MODELO`; replace them with a real
model/deployment ID from Fireworks.

To list serverless models visible to the configured Fireworks API key without
exposing the key locally, use:

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal --list-serverless-models
```

## Proposed Architecture

The future implementation should add a new cluster namespace rather than edit
existing Cluster 1, Cluster 2, or Cluster 3 contracts in place.

```text
cluster_fw/
  experiments/
    run_fireworks_modal.py
  planning/
    l2b_smoke.py
  providers/
    fireworks.py
  tests/
    test_fireworks_provider.py
    test_l2b_smoke_plan.py
    test_run_fireworks_modal_cli.py

shared/modal_harness/
  fireworks_generation.py
```

The `shared/modal_harness` addition is a lightweight API-generation Modal
surface. It does not require GPU and currently uses Fireworks' REST API through
Python stdlib `urllib`, avoiding SDK, dependency, and lockfile changes.
The Fireworks Modal Secret defaults to `fireworks-api` so local and remote
Modal hydration see the same function dependency graph.

Existing compile/correctness/profiling surfaces must be reused unchanged:

```text
shared/modal_harness/compile.py
cluster2/modal/correctness.py
cluster3/modal/*
```

## Provider Boundary Contract

The provider backend must return one normalized payload regardless of whether
Fireworks is called through Responses API or Chat Completions API.

Required normalized fields:

```text
provider: fireworks
provider_api: responses | chat_completions
provider_model_id
provider_model_snapshot
model_slot: FW-A | FW-B
source
finish_reason
provider_response_id
provider_request_id
input_tokens
output_tokens
reasoning_tokens
cached_input_tokens
prompt_sha256
response_sha256
source_sha256
raw_source_sha256
source_extraction_method
source_extraction_warning
provider_error_type
provider_error_msg
raw_response_shape_version
```

`source` is the only field passed to the evaluator. If the provider returns
markdown, prompt echo, or prose around the module, the provider boundary extracts
the Python block before evaluation and records the extraction method/warning.
No hidden reasoning, private chain-of-thought, full provider raw response,
Fireworks secret, prompt text, private eval shapes, or raw billing data may be
written into result rows.

### Source Extraction Policy

The provider must support both likely response shapes:

1. Responses API style:

```text
response.output_text
response.output[*].content[*].text
```

2. Chat Completions style:

```text
response.choices[0].message.content
```

The normalized `source` should prefer, in order:

1. a fenced Python/py markdown block containing the Triton module;
2. text beginning at a top-level `import torch` module boundary;
3. raw provider text only when no Python boundary is detectable.

Indented fenced code is dedented, and trailing non-Python prose is trimmed when
a parseable module prefix can be recovered.

The selected API must be recorded in `provider_api`. If both APIs are tested,
they must write separate output namespaces and must not be merged before a
post-smoke audit.

## L2b n=2 Smoke Definition

`L2b` is a proposed Fireworks smoke rung. It is not the existing L2 n=20 paper
run and must not use the L2 n=20 artifact namespace.

Proposed identity:

```text
experiment_id: fireworks_api_modal_v1
run_tier: l2b_n2_smoke
scale_tier: smoke
model_slots: FW-A, FW-B
design: grammar_mode x C_loop x P_loop
grammar_modes: grammar_off, template_upper_bound, task_agnostic
C_loop: off, on
P_loop: off, on
n: 2
dtypes: fp32, fp16, bf16
kernel_class: elementwise, reduction, matmul
expected_rows_per_model: 216
expected_total_rows: 432
```

The L2b row count is:

```text
12 grammar_mode x C_loop x P_loop cells
* 3 kernel classes
* 3 dtypes
* n=2 seeds
= 216 rows per model slot

216 rows/model * 2 Fireworks model slots = 432 total planned rows
```

The 12 condition cells are:

```text
grammar_off__c_off__p_off
grammar_off__c_on__p_off
grammar_off__c_off__p_on
grammar_off__c_on__p_on
template_upper_bound__c_off__p_off
template_upper_bound__c_on__p_off
template_upper_bound__c_off__p_on
template_upper_bound__c_on__p_on
task_agnostic__c_off__p_off
task_agnostic__c_on__p_off
task_agnostic__c_off__p_on
task_agnostic__c_on__p_on
```

## Proposed Output Namespaces

Future smoke outputs should be isolated from Cluster 3's L1a/L1b/L2 paths:

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2b_n2/<model_slot>/<condition_id>.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2b_n2/<model_slot>/<condition_id>.jsonl.hashes.json
artifacts/observability/fireworks_api_modal_v1/l2b_n2/<model_slot>/<condition_id>.observability.jsonl
artifacts/observability/fireworks_api_modal_v1/l2b_n2/<model_slot>/<condition_id>.observability.summary.json
artifacts/observability/fireworks_api_modal_v1/l2b_n2/<model_slot>/<condition_id>.observability.jsonl.hashes.json
```

No output path above may be created until `OUTPUT_MUTATION_AUTHORIZED: YES` and
`FIREWORKS_API_CALL_AUTHORIZED: YES` appear in a signed packet.

## Future Command Templates

The following commands are templates only. They are not authorized by this
document.

Dry plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster_fw.experiments.run_fireworks_modal \
  --condition grammar_mode_cp_12cell \
  --kernel-class all \
  --scale-tier smoke \
  --run-tier l2b_n2_smoke \
  --n 2 \
  --dtypes all \
  --models FW-A FW-B \
  --model-id-overrides FW-A=accounts/<account-or-fireworks>/models/<accessible-model-or-deployment> \
  --provider-api responses \
  --repair-history-policy agentic_transcript_v1 \
  --dry-plan
```

Execution plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster_fw.experiments.run_fireworks_modal \
  --condition grammar_mode_cp_12cell \
  --kernel-class all \
  --scale-tier smoke \
  --run-tier l2b_n2_smoke \
  --n 2 \
  --dtypes all \
  --models FW-A FW-B \
  --model-id-overrides FW-A=accounts/<account-or-fireworks>/models/<accessible-model-or-deployment> \
  --provider-api responses \
  --repair-history-policy agentic_transcript_v1 \
  --execution-plan
```

Signed smoke execution:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster_fw.experiments.run_fireworks_modal \
  --condition grammar_mode_cp_12cell \
  --kernel-class all \
  --scale-tier smoke \
  --run-tier l2b_n2_smoke \
  --n 2 \
  --dtypes all \
  --models FW-A FW-B \
  --model-id-overrides FW-A=accounts/<account-or-fireworks>/models/<accessible-model-or-deployment> \
  --provider-api responses \
  --repair-history-policy agentic_transcript_v1 \
  --signed-fireworks-l2b-authorization FIREWORKS_API_MODAL_L2B_N2_AUTHORIZATION_PACKET_V1 \
  --overwrite
```

## Future Authorization Packet Requirements

Before the signed smoke command can run, a separate packet must set:

```text
MODAL_AUTHORIZED: YES
GENERATION_AUTHORIZED: YES
EXPERIMENT_EXECUTION_AUTHORIZED: YES
OUTPUT_MUTATION_AUTHORIZED: YES
ARTIFACT_MUTATION_AUTHORIZED: YES
FIREWORKS_API_CALL_AUTHORIZED: YES
CODE_WORK_AUTHORIZED: YES
DEPENDENCY_CHANGE_AUTHORIZED: YES or NO, explicitly
LOCKFILE_CHANGE_AUTHORIZED: YES or NO, explicitly
```

The packet must also name:

- exact branch and commit;
- exact model IDs;
- exact provider API route;
- exact environment variable or Modal Secret name for the Fireworks key;
- exact output namespace;
- row cap and abort policy;
- provider token/spend cap;
- whether `responses` or `chat_completions` is the selected API;
- whether raw provider responses are forbidden or redacted into a private audit
  artifact;
- whether observability sidecars are required or unavailable.

## Future Local Test Plan

When code work is authorized, implement tests before implementation:

```bash
.venv/bin/python -m pytest \
  cluster_fw/tests/test_fireworks_provider_schema.py \
  cluster_fw/tests/test_run_fireworks_modal_cli.py \
  shared/tests/test_modal_harness_local_imports.py \
  -q
```

Expected pre-implementation failure:

```text
ModuleNotFoundError: cluster_fw
```

Expected post-implementation pass:

```text
all selected tests pass; no Modal, Fireworks, GPU, output, or artifact mutation
occurs during unit tests
```

## Future Smoke Acceptance Criteria

The L2b n=2 smoke is acceptable only if a post-run audit verifies:

- exactly two model slots were attempted;
- exactly 12 cells per model slot were planned;
- exactly 24 rows per model slot were expected;
- every written row has `provider="fireworks"` and a valid `model_slot`;
- every row has explicit `provider_api`;
- every row has `source_sha256` and `prompt_sha256`;
- every row records `raw_source_sha256`, `source_extraction_method`, and any
  `source_extraction_warning`;
- every provider error row has `provider_error_type`;
- no hidden reasoning or raw secret appears in JSONL or sidecars;
- compile/correctness evaluators remain existing Modal harness surfaces;
- no L2 n=20 namespace is mutated;
- no analyzer/report refresh occurred unless separately authorized.

## Open Questions

1. Should the first Fireworks smoke use Responses API or Chat Completions API?
   Fireworks supports both, but Chat Completions may be more mature for some
   models while Responses may align better with current provider abstraction.
2. Should `DeepSeek-R1` thinking output be stripped by provider extraction,
   requested as hidden reasoning when supported, or recorded as unavailable?
3. Should grammar-mode `G` be treated as prompt/post-validation only for
   Fireworks, or should a later provider-side CFG/structured-output path be
   researched? This document does not authorize provider-side constrained
   decoding claims.
4. Should the n=2 smoke run both FW-A and FW-B in one signed packet, or one
   model slot at a time to limit spend and isolate provider failures?

## Fireworks GBNF n20 Operational Note

### Functional correctness and C repair loop

The Fireworks runner supports an optional Level-2 correctness path:

```text
--correctness-modal
```

When this flag is active, Fireworks rows are evaluated through the existing
Modal Level-2 correctness surface instead of the shallower compile-only adapter.
The output row records:

```text
functional_success
repair_set_success
eval_set_success
correctness_error
max_abs_diff
max_rel_diff
level_reached
num_repair_shapes
num_eval_shapes
num_test_shapes
```

For C-active cells (`C`, `G+C`, `C+P`, `G+C+P`), the runner routes F2 failures
through the existing Cluster 2 C repair loop. The loop only receives public
correctness feedback and only repairs:

```text
F2_NUMERIC_LARGE
F2_NUMERIC_NAN
F2_SHAPE_MISMATCH
```

F0, F1, and F3 outcomes are recorded as terminal rows and do not receive C
feedback. This preserves the original feedback-content boundary: G handles
surface control, P handles F1_COMPILE when separately implemented, and C handles
numerical correctness failures only.

Minimal functional smoke command:

```bash
modal run -m cluster_fw.experiments.run_fireworks_modal \
  --signed-fireworks-l2b-authorization FIREWORKS_API_MODAL_L2B_N2_AUTHORIZATION_PACKET_V1 \
  --models FW-A \
  --model-id-overrides FW-A=accounts/fireworks/models/<model-id> \
  --provider-api chat_completions \
  --condition-cell grammar_off__c_on__p_off \
  --kernel-class elementwise \
  --dtypes fp32 \
  --n 1 \
  --temperature 0 \
  --max-output-tokens 4096 \
  --correctness-modal \
  --repair-budget 1 \
  --output outputs/cluster_fw/fireworks_api_modal_v1/functional_smoke/fw_a_functional_c_loop.jsonl \
  --overwrite
```

`--correctness-modal` supersedes `--compile-modal` for row outcome fields because
the Level-2 evaluator already runs parse, signature, compile/launch, and
correctness gates. Use `--compile-modal` only for the shallower compile-and-run
stream.

The later `fireworks_gbnf_n20` runner tier uses Fireworks Chat Completions with
provider-side grammar response format. The local GBNF files are normalized
before being sent to Fireworks because the provider expects a stricter line
format than the repo's multiline grammar files.

Observed during Wave 1:

```text
Fireworks HTTP 400:
Grammar processing took too much time. Likely the grammar allows too much
branching. Please simplify the grammar or reach out to Fireworks for support.
```

This occurred for `task_agnostic` grammar-constrained rows. The runner now
records provider exceptions as JSONL rows instead of aborting the wave:

```text
failure_code: F3_EVAL_PIPELINE
compile_error_type: ProviderError
provider_error_type: RuntimeError
response_format_type: grammar
raw_response_shape_version: fireworks_provider_exception_v1
```

Wave 1 evidence is documented in:

```text
audits/fireworks_gbnf_n20_wave1_provider_error_report.md
```

## Explicit Non-Claims

This document does not claim:

- any unsigned Fireworks API call is authorized by this document;
- any newly added functional Fireworks smoke has succeeded;
- L2b or functional smoke output is reportable evidence without a signed
  execution packet and post-run audit;
- n=2 smoke can support statistical conclusions;
- frontier models improve compilation, correctness, C-loop success, P-loop
  success, or grammar-mode lift;
- grammar-constrained decoding is universally available through Fireworks for
  every grammar/model pair;
- performance, speedup, or profiling evidence exists.
