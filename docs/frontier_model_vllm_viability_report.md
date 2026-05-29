# Frontier Model And vLLM Viability Report

Date: 2026-05-26

Status: initial research report, documentation only. No code changes or Modal
runs are authorized by this document.

## 1. Executive Verdict

The requested "vLLM harness for GPT models and Claude models using subscription
price" splits into two very different problems:

1. vLLM is viable for open-weight models on Modal, including OpenAI open-weight
   `gpt-oss` style models and Hugging Face models, where the project can load
   weights, own the tokenizer, and apply grammar-guided decoding in the serving
   stack.
2. vLLM is not a viable way to run proprietary hosted GPT or Claude frontier
   models. OpenAI GPT API models and Anthropic Claude models run behind provider
   APIs. vLLM can expose an OpenAI-compatible server for models it hosts, but
   that compatibility layer is an API shape, not access to OpenAI or Anthropic
   proprietary model weights.
3. ChatGPT subscription pricing is not usable for OpenAI API automation. OpenAI
   documents API usage as separate from ChatGPT subscriptions. Anthropic's Claude
   subscription and Claude Code paths are also not a clean replacement for API
   billing in a Modal research pipeline. Claude Code can use Claude plans for
   interactive/local development workflows, but Anthropic's docs distinguish
   those flows from developer products and Agent SDK/API integrations.

Recommended path:

- Keep the current Transformers/XGrammar Modal backend for the existing artifact
  line.
- Add any vLLM path only as a new open-weight backend lineage, not as a drop-in
  replacement for frozen or comparable rows.
- Add a frontier-provider option for GPT-backed grammar experiments:
  OpenAI Responses API with custom-tool CFG can be tested as the closest
  proprietary-GPT equivalent to grammar-constrained generation. This is not
  XGrammar, and any GBNF reuse requires translation/adaptation.
- Add frontier-provider options for `C` and `P`: GPT and Claude API models can
  be used for correctness-feedback and compile-error-feedback loops because
  those loops are prompt/evaluate/repair orchestration and do not require local
  token masking.
- For frontier GPT performance, prototype an OpenAI Responses API backend that
  preserves the existing generation contract and uses either:
  - OpenAI custom-tool CFG output where the grammar can be translated safely
    from the current GBNF surface; or
  - normal text generation plus the existing offline GBNF and semantic
    validators, clearly labeling `grammar_active=false` and post-validation
    only.
- For Claude, use the official Anthropic API for reproducible research runs.
  Treat Claude's structured-output/tool schema support as JSON/object
  constraint support, not as a Triton GBNF replacement.

## 2. Current Repo Constraints

The current codebase already has strict generation and provenance boundaries:

- Cluster 1 `G` means grammar-guided decoding plus offline semantic
  post-validation. `grammar_active=true` only means decoding guidance was
  attempted; `grammar_valid = gbnf_parse_valid AND semantic_valid`.
- Cluster 1 is compile-only. It does not claim Level 2 numerical correctness.
- Cluster 2 generates only `C` and `G+C`; `none` and `G` replay frozen Cluster 1
  artifacts.
- Cluster 2's Modal generation surface currently loads Hugging Face models with
  `transformers.AutoModelForCausalLM` and `AutoTokenizer`.
- Grammar-guided rows call Cluster 1's `generate_source`, which injects a custom
  `TritonGrammarLogitsProcessor` using XGrammar plus the local hardware checker.
- Cluster 3 v1 is specified as a local orchestration layer over existing Cluster
  2 Modal generation/correctness surfaces, with no new Modal app or image in v1.

Implication: a vLLM backend would be a new generation engine with new RNG,
batching, tokenizer, stop-reason, grammar, and provenance behavior. It should be
treated as a new artifact lineage.

Relevant local anchors:

- `shared/modal_harness/generation.py`
- `cluster2/modal/generation.py`
- `cluster1/generation/constrained_gen.py`
- `cluster1/generation/constrained_decoding.py`
- `cluster1/grammar/triton_kernel_agnostic.gbnf`
- `cluster3/README.md`
- `docs/04_modal_infrastructure.md`

## 3. External Findings

### 3.1 vLLM

vLLM is an inference and serving engine for models whose weights/runtime the
operator controls. Its OpenAI-compatible server exposes OpenAI-style routes for
served models. Modal has official examples for deploying vLLM as an
OpenAI-compatible server.

vLLM structured outputs currently support schema-style constraints and grammar
constraints through a `structured_outputs` interface. The docs identify
XGrammar as the default backend and support grammar constraints, but the grammar
format described in current docs is EBNF-style, not this repo's GBNF file
format verbatim.

Implications for TritonGen:

- Viable for open-weight models on Modal.
- Potentially useful for throughput and continuous batching.
- Not compatible with current artifact lineage without a new backend label.
- Requires grammar-format verification and likely GBNF-to-EBNF/Lark-style
  translation or a second grammar source of truth.
- Does not solve proprietary GPT/Claude subscription access.

### 3.2 OpenAI GPT Frontier Models

OpenAI's official help docs state that API usage is separate from ChatGPT
subscriptions. Therefore ChatGPT Plus/Pro style subscription billing cannot be
used as the billing mechanism for an automated API-backed research pipeline.

OpenAI's API supports structured outputs and custom tool input formats. Current
function/tool docs show custom tools can use context-free grammars in Lark or
regex formats. This is the most promising route for GPT models if the goal is
to get provider-side grammar pressure rather than pure post-validation.

Important distinction:

- OpenAI API grammar/custom-tool support may provide provider-side CFG
  constraint for the generated tool input.
- It is not vLLM/XGrammar.
- It does not expose the same masked-token telemetry as the current
  XGrammar-backed local path.
- It likely requires a source-string tool contract such as `emit_triton_source`
  whose input is the generated source text under the grammar.

### 3.3 Anthropic Claude Frontier Models

Anthropic exposes Claude through the Anthropic API, with token-priced models and
tool/structured-output patterns. Anthropic docs describe strict tool use and
schema validation patterns for structured outputs, but this is not equivalent to
arbitrary Triton GBNF grammar-constrained decoding.

Claude Code and subscription plans can be useful for local development work, but
they should not be treated as the research pipeline backend. Anthropic's own
legal/compliance docs distinguish interactive Claude Code/OAuth use from
developer products and Agent SDK/API-key integrations. That makes subscription
automation a poor fit for reproducible Modal pipelines.

## 4. Viability Matrix

| Option | Runs on Modal | Uses vLLM | Uses subscription billing | Grammar during decoding | Viability |
|---|---:|---:|---:|---|---|
| Open-weight model via current Transformers/XGrammar backend | yes | no | no | current XGrammar/GBNF path | already viable |
| Open-weight model via vLLM on Modal | yes | yes | no | vLLM structured outputs/XGrammar backend, format must be verified | viable as new backend lineage |
| OpenAI `gpt-oss` style open-weight model via vLLM on Modal | yes | yes | no | vLLM structured outputs if supported for model/tokenizer | viable as new backend lineage |
| Proprietary GPT via vLLM | no | no meaningful role | no | not applicable | not viable |
| Proprietary GPT via OpenAI Responses API | optional; Modal can call HTTP API | no | no, token/API billing | possible custom-tool CFG or post-validation | viable and recommended GPT path |
| Claude via Anthropic API | optional; Modal can call HTTP API | no | no, token/API billing | JSON/tool schema plus post-validation | viable, but no GBNF-equivalent guarantee |
| Claude Code subscription CLI as harness | local only in practice | no | maybe for manual dev | prompt only plus post-validation | not recommended for reportable runs |
| ChatGPT web/subscription automation | not appropriate | no | subscription | unknown/uncontrolled | not viable |

## 5. Recommended Architecture

Use a provider-agnostic generation backend boundary rather than a single
"vLLM for everything" harness.

Conceptual backends:

1. `transformers_xgrammar`: existing Modal backend for current open-weight runs.
2. `vllm_xgrammar`: new Modal backend for open-weight throughput experiments.
3. `openai_responses_cfg`: GPT API backend using Responses API custom tool CFG
   where feasible.
4. `openai_responses_postvalidate`: GPT API backend using normal text/source
   output plus existing offline validation.
5. `anthropic_messages_postvalidate`: Claude API backend using tool/schema or
   text generation plus existing offline validation.
6. `openai_responses_feedback`: GPT API backend for Cluster 2 `C` and Cluster 3
   `P` repair attempts, with no claim of XGrammar-style masking.
7. `anthropic_messages_feedback`: Claude API backend for Cluster 2 `C` and
   Cluster 3 `P` repair attempts, with structured output where useful and
   existing validators as the authority.

Every backend should return one normalized generation result:

- source text;
- provider and backend name;
- model id and provider model id;
- provider response id when available;
- token usage when available;
- generation seed or a documented `seed_unavailable` marker;
- temperature, max output tokens, stop reason;
- grammar mode: `xgrammar_decode`, `provider_cfg`, `post_validation_only`, or
  `none`;
- grammar source identity: grammar path/hash or provider grammar hash;
- validation fields: `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`,
  `rejection_layer`;
- runtime identity: Modal image identity for Modal-hosted backends, provider API
  docs date/version for hosted backends;
- prompt hash and feedback-template hash.

For provider APIs, do not pretend to have local tokenizer revision, local
XGrammar version, or masked-token rate. Add explicit unknown/unavailable fields
instead.

## 6. Grammar Strategy

### 6.1 Open-Weight vLLM Path

For vLLM, test grammar support separately from the cluster pipelines:

1. Translate or adapt the current task-agnostic GBNF grammar into the grammar
   format accepted by vLLM structured outputs.
2. Verify that a single prompt can produce a syntactically accepted source.
3. Run the existing offline validator anyway.
4. Record both provider/engine acceptance and offline validator acceptance.
5. Compare outputs against the current Transformers/XGrammar path only as a new
   backend study, not as a row-compatible rerun.

### 6.2 GPT API Path

For OpenAI, the strongest provider-side option is a custom tool with a CFG
grammar. Feasibility hinges on whether the Triton source surface can be safely
represented in the accepted grammar syntax and whether provider-side generation
accepts the grammar complexity.

Recommended smoke:

1. Define an `emit_triton_source` custom tool whose freeform input is the source
   text.
2. Convert a minimal subset of `triton_kernel_agnostic.gbnf` into Lark or the
   provider-supported grammar syntax.
3. Run one ReLU prompt at n=1.
4. Pipe the returned source through the existing parser, semantic validator,
   compile gate, and Level 2 correctness gate.
5. Record `grammar_mode=provider_cfg` and keep offline `grammar_valid` separate.

If this fails, fall back to `grammar_mode=post_validation_only` rather than
calling it `G`.

### 6.3 Claude API Path

For Claude, treat structured output as a way to make the response shape stable,
for example:

```json
{"source": "...", "notes": null}
```

Do not label this as grammar-guided decoding unless Anthropic exposes a
provider-side CFG/GBNF feature that can enforce the Triton source grammar. Use
offline validation and repair loops to filter/repair generated source.

### 6.4 Feedback-Loop Path For C And P

`C` and `P` are the most straightforward frontier-model integration points.
They are feedback loops, not local masked-decoding mechanisms:

- Cluster 2 `C` can call GPT or Claude with the base prompt plus public Level 2
  correctness feedback, then evaluate the returned source through the existing
  Level 0/1/2 ladder.
- Cluster 3 `P` can call GPT or Claude with the base prompt, previous source,
  failure code, sanitized compile-error excerpt, and compile-diagnostic note,
  then evaluate the returned source through the existing compile and correctness
  gates.
- These paths do not need XGrammar or vLLM. They need a provider API backend,
  prompt hashing, output extraction, token-usage accounting, and F3 handling for
  provider/rate-limit failures.
- If the condition is `C` or `P`, provider generation can be a valid experiment
  option after smoke validation.
- If the condition is `G+C` or `G+C+P`, the `G` component must still come from
  either open-weight vLLM/XGrammar-style constrained decoding or a documented
  OpenAI provider-side CFG path. Otherwise the row must be labeled
  `post_validation_only`, not current `G`.

### 6.5 Closest-To-XGrammar Options For GPT And Claude

Assumption: "Cluster 1 control" means the `G` mechanism: grammar-guided
generation plus offline semantic validation. The proprietary GPT/Claude API
models cannot expose local logits for XGrammar masks, so the goal is not exact
XGrammar parity. The goal is the closest auditable provider-side constraint.

Ranked options:

| Rank | Provider | Method | Closeness to XGrammar masking | Best use |
|---:|---|---|---|---|
| 1 | OpenAI GPT | Responses API custom tool with CFG grammar, preferably Lark | Closest for proprietary GPT because it constrains freeform generated text with provider-side grammar | Raw Triton-source `G` smoke, if GBNF can be translated safely |
| 2 | OpenAI GPT | Strict JSON Schema / structured output for a typed kernel IR, then deterministic source renderer | Strong provider-side structure, weaker raw-source grammar equivalence | Fallback if raw source CFG is too brittle |
| 3 | Claude | Structured Outputs / strict tool use with JSON Schema for a typed kernel IR, then deterministic source renderer | Closest practical Claude path because Claude constrains JSON-schema-valid tool input, not arbitrary GBNF source | Claude `G`-adjacent experiments, clearly labeled schema-IR constrained |
| 4 | Claude | Structured output with `{source: string}` plus broad validation | Stable response shape only; source text itself is mostly unconstrained | C/P repair output extraction, not a `G` claim |
| 5 | GPT or Claude | Prompt-only source generation plus offline GBNF/semantic validation and retries | Not provider-side grammar masking | Baseline/provider post-validation studies |
| 6 | Codex/Claude Code pointed at vLLM | vLLM-served open-weight model behind agent API shape | Only applies to open-weight vLLM models, not proprietary GPT/Claude | Developer tooling and open-weight backend experiments |

Selected path for GPT:

1. Build a tiny `openai_responses_cfg` smoke around one ReLU prompt.
2. Translate only the minimal source surface needed for that prompt from
   `cluster1/grammar/triton_kernel_agnostic.gbnf` into OpenAI-supported Lark
   grammar.
3. Use a custom tool such as `emit_triton_source` whose freeform input is the
   generated source.
4. Run the existing offline GBNF parse, semantic validator, compile gate, and
   Level 2 evaluator.
5. Record `grammar_mode=provider_cfg`, `provider_constraint=openai_custom_tool_cfg`,
   and separate offline `grammar_valid` from provider CFG acceptance.

This is the closest proprietary-GPT analog to XGrammar. It is still not
XGrammar, so it must not reuse `xgrammar_version`, `masked_token_rate`, or
local tokenizer-revision claims.

Selected path for Claude:

1. Do not start with raw Triton source grammar. Claude's best constraint surface
   is JSON Schema through Structured Outputs / strict tool use.
2. Define a small typed kernel IR schema with enum-constrained kernel class,
   dtype, function/launcher fields, allowed operation families, block sizes,
   and memory-access pattern fields.
3. Render that IR deterministically into Triton source inside this repo.
4. Run the existing offline GBNF parse, semantic validator, compile gate, and
   Level 2 evaluator.
5. Record `grammar_mode=schema_ir_constrained`, not `xgrammar_decode` and not
   current Cluster 1 `G` unless a later contract explicitly accepts this as a
   separate G variant.

This is weaker than raw-source CFG, but it is stronger and more auditable than
asking Claude for arbitrary source text. For `C` and `P`, Claude can be used
directly as a feedback-loop model without solving raw-source grammar masking.

Practical selection:

- Best closest-to-XGrammar path for GPT: OpenAI custom-tool CFG.
- Best closest-to-XGrammar path for Claude: structured-output kernel IR plus
  deterministic renderer.
- Best near-term frontier-model use overall: GPT/Claude for `C` and `P`
  feedback loops, because those loops do not depend on local token masks.
- Best exact-XGrammar path: vLLM/open-weight only.

## 7. Modal Strategy

For open-weight vLLM:

- Modal is the right place to host vLLM if throughput is the goal.
- Generation containers need GPU, vLLM package pins, model/tokenizer revision
  pins, and a fresh provenance schema.
- vLLM continuous batching is useful only if the runner submits concurrent work.
  Serial one-row calls will not realize most throughput benefits.

For OpenAI/Anthropic hosted APIs:

- Modal does not accelerate inference. The provider does inference.
- Modal can still be useful as a controlled orchestrator that runs generation
  HTTP calls, then compile/correctness evaluation in the same logged remote
  environment.
- Generation itself can run on CPU. GPU spend should be reserved for Triton
  compile/correctness evaluation.
- Provider API keys should live in Modal secrets, not in committed config or
  output rows.

## 8. Cost And Subscription Viability

Subscription billing is not a viable general route for reportable automated
runs:

- OpenAI: ChatGPT subscription does not include API usage. API usage is billed
  separately by API plan/model/token tier.
- Anthropic: Claude subscriptions and API billing are separate operational
  surfaces. Claude Code subscription access may be useful locally, but it is not
  a clean Modal backend and is not appropriate for a reproducible API product
  harness.

Token/API billing is the reliable route for GPT/Claude provider runs. Modal
cost remains separate:

- open-weight vLLM: provider API token cost is zero, but Modal GPU time can be
  high.
- GPT/Claude hosted APIs: provider token cost dominates generation; Modal GPU
  cost applies only to compile/eval unless generation is unnecessarily run on
  GPU containers.

Before any paid run, record:

- pricing page URL and retrieval date;
- model id;
- input/output token price;
- batch/flex/priority tier if used;
- expected prompt tokens, generated tokens, and repair attempts;
- Modal GPU type and expected eval seconds;
- explicit budget cap.

## 9. Pipeline Fit By Cluster

### Cluster 1

Open-weight vLLM can replace the current generation backend only in a new
lineage. It must still output the same source and validation fields, plus new
backend metadata. Do not use it to fill missing task-agnostic G rows in the
current artifact line.

GPT API with provider CFG could create a new `G`-like provider condition only
after the grammar translation and offline validation semantics are documented.
Until then it is source generation plus post-validation, not current `G`.

### Cluster 2

Cluster 2 can use provider backends for fresh `C` and `G+C` generation if:

- replay controls remain frozen;
- C feedback templates and prompt hashes are preserved;
- provider model ids are explicit;
- generated rows keep the same Level 0/1/2 gates;
- `C` rows may use GPT or Claude API models for the feedback loop because C is
  prompt-feedback repair over Level 2 failures, not grammar masking;
- `G+C` is not claimed unless the G component has a documented provider CFG or
  open-weight grammar path plus offline validation.

### Cluster 3

Cluster 3 v1 should not start by adding vLLM. The current spec says Cluster 3 is
a local orchestration layer over existing Cluster 2 Modal surfaces. First make
P compile-error repair work with the existing backend. After that, add provider
backends as a separate generation surface compatibility exercise.

Provider APIs are most useful for Cluster 3's repair prompts because frontier
models may be better at interpreting compiler errors. That path does not require
vLLM.

`P` and `C+P` can use GPT or Claude API models for repair attempts after the
current Cluster 3 v1 orchestration is stable. This should be a provider-backend
option, not a rewrite of the P loop: the loop still owns failure dispatch,
prompt construction, compile/correctness evaluation, terminal provenance, and
trace summaries.

`G+P` and `G+C+P` need the same G caveat as Cluster 2: use provider-side CFG or
open-weight grammar-constrained decoding for a real G claim, or label the
generation as post-validation only.

## 10. Minimum Smoke Plan

No paper-scale run should be attempted before these smoke gates:

1. GPT API post-validation smoke: one ReLU, condition `C`, n=1, no provider CFG,
   existing validators.
2. GPT API C feedback smoke: one ReLU, condition `C`, n=1, one public
   correctness-feedback repair attempt, existing validators.
3. GPT API CFG smoke: one ReLU, condition explicitly labeled
   `provider_cfg_smoke`, n=1, minimal grammar, offline validator required.
4. Claude API C feedback smoke: one ReLU, condition `C`, n=1, one public
   correctness-feedback repair attempt, structured output if stable, existing
   validators.
5. Claude API post-validation smoke: one ReLU, condition `C`, n=1, structured
   JSON/tool output if stable, offline validator required.
6. vLLM open-weight smoke: one ReLU, current development model or `gpt-oss`
   style model, n=1, grammar active if grammar format is verified.
7. Cluster 3 P smoke only after the current P path is stable: one F1 compile
   failure fixture, one GPT provider backend, bounded repair attempts.
8. Cluster 3 P smoke with Claude only after the GPT/provider-neutral path is
   stable: one F1 compile failure fixture, bounded repair attempts.

Each smoke result should be a separate artifact lineage, not an overwrite of
existing current artifacts.

## 11. Main Risks

- Subscription automation risk: not portable to Modal, not auditable, likely
  against provider intent for API-style automation.
- Grammar equivalence risk: GBNF, vLLM EBNF-style grammar, OpenAI Lark grammar,
  and JSON schema are not automatically equivalent.
- Reproducibility risk: hosted GPT/Claude APIs do not expose model weight
  revision, tokenizer revision, or local logits-mask traces.
- Cost risk: repair loops multiply provider output-token cost.
- Research validity risk: changing backend changes model, decoding, and
  stop/repair behavior. Treat as a new experimental factor or new lineage.
- Operational risk: provider rate limits and transient errors need explicit F3
  handling and resume policy.

## 12. Recommendation

Do not pursue "vLLM for GPT and Claude subscription models" as stated.

Pursue two separate tracks:

1. Open-weight performance track: vLLM on Modal, including possible `gpt-oss`
   models, with XGrammar/structured-output verification. This is a new backend
   lineage for throughput experiments.
2. Frontier provider track: OpenAI Responses API and Anthropic Messages API as
   provider backends, token-billed, with Modal used for orchestration and
   evaluation. For GPT, test custom-tool CFG as the best candidate for
   provider-side grammar pressure. For Claude, use structured shape constraints
   plus offline validation and feedback loops.
3. Feedback-loop frontier track: explicitly support GPT and Claude API models
   for Cluster 2 `C` and Cluster 3 `P` repair attempts after smoke validation.
   These are viable because they operate through prompt feedback and external
   evaluation, not through local token masks.

The near-term best use of frontier models is Cluster 3 repair quality, not
vLLM. Make the P loop backend-agnostic after it is stable with the current
generation surface, then plug in GPT/Claude API backends for smoke tests.

## 13. Sources

- vLLM OpenAI-compatible server docs:
  https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- vLLM structured outputs docs:
  https://docs.vllm.ai/en/latest/features/structured_outputs.html
- vLLM supported models docs:
  https://docs.vllm.ai/en/stable/models/supported_models.html
- Modal vLLM deployment example:
  https://modal.com/docs/examples/vllm_inference
- OpenAI help, ChatGPT subscription vs API usage:
  https://help.openai.com/en/articles/8156019-is-api-usage-included-in-chatgpt-subscriptions-even-if-i-have-a-paid-chatgpt-account
- OpenAI function calling/custom tools docs:
  https://platform.openai.com/docs/guides/function-calling
- OpenAI API pricing docs:
  https://developers.openai.com/api/docs/pricing
- OpenAI cookbook, running `gpt-oss` with vLLM:
  https://cookbook.openai.com/articles/gpt-oss/run-vllm/
- Anthropic pricing docs:
  https://docs.anthropic.com/en/docs/about-claude/pricing
- Anthropic tool use docs:
  https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- Anthropic strict tool use docs:
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
- Anthropic structured outputs docs:
  https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency
- Anthropic legal/compliance docs for Claude Code:
  https://docs.anthropic.com/en/docs/claude-code/legal-and-compliance
