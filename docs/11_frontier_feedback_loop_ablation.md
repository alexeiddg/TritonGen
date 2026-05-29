# Frontier Feedback-Loop Ablation Plan

Date: 2026-05-26

Status: research proposal / methodology draft. This document does not authorize
OpenAI API calls, Modal runs, paper-scale runs, artifact rewrites, or result
claims.

## 1. Executive Summary

This project can run a plausible and useful ablation that swaps the repair model
inside Cluster 2 and Cluster 3 feedback loops for a frontier model such as GPT.
The clean version is not "replace TritonGen with GPT" and not "let GPT grade the
kernel." The clean version is:

```text
fixed candidate source + fixed feedback signal + fixed evaluator
    -> repair model backend changes
    -> compare terminal outcome, attempts, cost, and failure movement
```

For Cluster 2, GPT would be used only for the `C` correctness-feedback repair
attempt after an eligible Level 2/F2 correctness failure. It must receive the
same public correctness feedback that the current loop can expose.

For Cluster 3, GPT would be used only for the `P` compile-error repair attempt
after an eligible `F1_COMPILE` failure. It must receive the same sanitized
compiler evidence and deterministic diagnostic note defined by the Cluster 3 P
prompt contract.

The strongest methodology is a seeded repair ablation: keep the initial
candidate fixed, then compare local repair, GPT repair, and no-feedback retries
under equal repair budgets. This isolates whether frontier models make better
use of the same feedback signal, rather than confounding the study with a new
initial generator.

## 2. Why Consider This

TritonGen's research question is about control mechanisms for LLM-generated GPU
kernels. The current design already separates grammar guidance (`G`),
correctness feedback (`C`), and compile-error feedback (`P`). A frontier-model
feedback ablation would add a second axis:

```text
control factor: none / G / C / P / combinations
repair backend: local open-weight model / frontier provider model / no-feedback retry
```

This matters because the current feedback-loop results can be limited by either
the feedback design or the model's ability to use the feedback. If a frontier
model succeeds where the local model fails under the same feedback content, the
feedback signal has latent value. If even a frontier model fails, the bottleneck
is more likely the prompt boundary, evaluation signal, source surface, or kernel
task difficulty.

The research literature supports this question. Self-Refine shows that LLM
outputs can improve through iterative feedback and refinement without training.
Reflexion studies language agents that use external or internal feedback
signals and explicitly includes ablations over feedback signals and
incorporation methods. FeedbackEval focuses directly on feedback-driven code
repair and reports that feedback type and iteration count materially affect
repair success, with diminishing returns after two or three iterations.

This is especially relevant for GPU kernels because KernelBench frames the task
as generating kernels that are both correct and efficient, and it shows that
correctness and speed are separate requirements. TritonGen already mirrors that
separation through Level 0/1/2 evaluation and deferred performance claims.

## 3. What It Adds To The Research

This ablation would add five concrete research contributions:

1. **Feedback-value measurement.** It tests whether the existing C and P signals
   are useful when interpreted by a stronger model.
2. **Model-capacity sensitivity.** It separates "the loop is weak" from "the
   repair model is weak."
3. **C/P complementarity.** In Cluster 3 `C+P` and `G+C+P`, it can test whether
   frontier P repairs expose more F2 cases that C can then fix.
4. **Cost-quality frontier.** It measures whether frontier repair improves
   pass rates enough to justify token/API cost and provider nondeterminism.
5. **Boundary validation.** It stress-tests the existing rule that C sees only
   correctness feedback and P sees only compile feedback.

The ablation should not be used to patch current artifacts or fill missing rows.
It should be a new lineage with its own backend labels, provider metadata,
artifact registry entries, and reportability gate.

## 4. Research Questions

RQ1. For Cluster 2 C, does GPT improve repair success on eligible F2 numerical
failures compared with the current local repair backend under the same feedback
template and repair budget?

RQ2. For Cluster 3 P, does GPT improve compile repair on eligible `F1_COMPILE`
failures compared with the current local P repair backend under the same
sanitized compiler feedback and repair budget?

RQ3. In composite Cluster 3 conditions (`C+P`, `G+C+P`), does making P frontier,
C frontier, or both frontier change the terminal failure distribution?

RQ4. Are observed gains feedback-driven, or are they explained by stronger
frontier generation alone? This requires a GPT no-feedback retry control.

RQ5. What is the marginal value of additional repair attempts after attempt 1,
and where does it stop being cost-effective?

## 5. Core Hypotheses

H1. GPT repair will outperform local repair on P because compiler errors are
language-rich and frontier coding models are strong at interpreting diagnostic
text.

H2. GPT repair may help C, but the effect may be smaller unless the Level 2
feedback contains enough localized signal about indexing, masks, shapes, or
arithmetic.

H3. GPT no-feedback retries will improve over local no-feedback retries, but
should underperform GPT with feedback if the feedback signal is genuinely
useful.

H4. Most benefit will arrive in the first one to three repair attempts. More
attempts are likely to have diminishing returns and higher cost.

H5. Some frontier gains will be invalid for current `G` claims unless the G
component is still provided by the existing grammar path or a separately
documented provider-side CFG path.

## 6. Ablation Cells

### 6.1 Cluster 2 C Ablation

Use the same initial candidate, same base prompt, same public F2 feedback, same
Level 0/1/2 evaluator, and same repair budget.

| Cell | Initial source | Feedback shown | Repair backend | Purpose |
|---|---|---|---|---|
| `C2_seed_only` | fixed | none | none | attempt-0 denominator |
| `C2_local_C` | fixed | C feedback | current local backend | existing-loop control |
| `C2_gpt_C` | fixed | C feedback | GPT provider backend | frontier feedback treatment |
| `C2_gpt_retry_no_feedback` | fixed | none | GPT provider backend | controls for frontier generation without feedback |
| `C2_local_retry_no_feedback` | fixed | none | current local backend | controls for extra attempts without feedback |

Important current-artifact caveat: the present paper-scale C artifact has all
current rows as `F0_PARSE`, so the real C loop does not fire broadly in that
artifact. A meaningful C ablation therefore needs a targeted F2 seed set first:
existing canonical F2 smoke fixtures, current G+C F2 rows, or newly frozen
development-scale candidates that actually reach Level 2 and fail numerically.

### 6.2 Cluster 3 P Ablation

Use the same initial candidate, same sanitized compiler error, same diagnostic
note, same compile/correctness evaluator, and same repair budget.

| Cell | Initial source | Feedback shown | Repair backend | Purpose |
|---|---|---|---|---|
| `C3_seed_only` | fixed F1 candidate | none | none | attempt-0 denominator |
| `C3_local_P` | fixed F1 candidate | P compile feedback | current local backend | existing-loop control |
| `C3_gpt_P` | fixed F1 candidate | P compile feedback | GPT provider backend | frontier feedback treatment |
| `C3_gpt_retry_no_feedback` | fixed F1 candidate | none | GPT provider backend | controls for frontier generation without feedback |
| `C3_local_retry_no_feedback` | fixed F1 candidate | none | current local backend | controls for extra attempts without feedback |

### 6.3 Composite C+P Ablation

For `C+P` and `G+C+P`, test backend assignment by loop:

| Cell | P backend | C backend | Interpretation |
|---|---|---|---|
| `local_P_local_C` | local | local | baseline composite loop |
| `gpt_P_local_C` | GPT | local | isolates frontier compile repair |
| `local_P_gpt_C` | local | GPT | isolates frontier correctness repair |
| `gpt_P_gpt_C` | GPT | GPT | full frontier repair treatment |

The evaluator must decide C routing from observed terminal evidence. If P
repairs compilation and then exposes F2, C may fire only in conditions where C
is active. P must not receive correctness feedback, and C must not receive raw
compiler feedback.

## 7. Methodology

### 7.1 Unit Of Analysis

The matched unit should be:

```text
kernel identity x dtype x base_seed x initial source hash x failure class
```

The initial source hash is essential. Without it, a GPT treatment might be
repairing a different seed candidate, which would confound repair ability with
initial generation quality.

### 7.2 Fixed Inputs

Freeze these before any run:

- kernel set and dtype set;
- base prompts;
- initial candidate sources;
- initial evaluation payloads;
- C feedback template;
- P feedback template;
- repair budget;
- model ids and provider snapshots;
- temperature, max output tokens, reasoning effort, and extraction format;
- evaluator image/provenance and failure taxonomy version.

### 7.3 Frontier Backend Definition

For OpenAI, the natural implementation path is the Responses API with a pinned
model snapshot, such as a current GPT model snapshot, and structured output for
source extraction. Current OpenAI docs list GPT-5.5 as a frontier coding and
professional-work model with Responses API support, function calling,
structured outputs, snapshots, and token-usage pricing; the API reference also
documents request IDs that should be logged for production troubleshooting. The
exact model snapshot must be frozen at run time rather than relying on a moving
alias.

Recommended output contract:

```json
{
  "source": "complete Triton Python module",
  "repair_notes": "optional short public notes or null"
}
```

Only `source` is evaluated. `repair_notes` is diagnostic and must not enter the
evaluator. Do not request or store hidden chain-of-thought. Store provider
request IDs, response IDs, token usage, model id, snapshot id, and prompt hash.

### 7.4 Prompt Controls

Cluster 2 GPT C prompt:

- base task;
- previous source;
- canonical failure code;
- existing public correctness feedback;
- instruction to produce a complete Triton Python module.

Forbidden for C:

- raw compiler tracebacks;
- private eval-set shapes;
- timing/profiling data;
- P compile diagnostics;
- hidden evaluator details.

Cluster 3 GPT P prompt:

- base task;
- previous source;
- `F1_COMPILE`;
- deterministic compile diagnostic note;
- sanitized compile-error excerpt;
- instruction to produce a complete Triton Python module.

Forbidden for P:

- Level 2 correctness feedback unless the separate C loop later fires;
- private eval-set shapes;
- timing/profiling data;
- unredacted infrastructure traces or secrets.

### 7.5 Equal-Budget Policy

Compare equal candidate-source budgets, not equal token cost. A repair budget
of `R=1`, `R=3`, and `R=5` is useful:

- `R=1`: minimal cost, isolates one-shot feedback use.
- `R=3`: likely captures most iterative benefit.
- `R=5`: matches current maximum-style bounded repair budgets and tests
  diminishing returns.

Report token/API cost separately. Do not call a frontier run "equal cost" unless
token and Modal costs are actually matched.

### 7.6 Metrics

Primary metrics:

- Cluster 2: `functional_success` after C repair.
- Cluster 3 P-only: `compile_success` after P repair.
- Cluster 3 C+P: final `functional_success`, plus P-specific compile repair
  success before any C loop.

Secondary metrics:

- terminal failure-code family;
- terminal failure-code class;
- attempts to first success;
- repair-set success and eval-set success;
- P changed terminal class;
- C loop fired after P;
- provider token usage and estimated provider cost;
- Modal GPU evaluation time;
- F3 provider/infrastructure rate;
- feedback-boundary violations.

Diagnostics:

- source hash changes by attempt;
- prompt hash and feedback hash;
- structured-output parse failure rate;
- cases where GPT produces non-Triton, CUDA, explanatory prose, or partial
  modules;
- distribution of fixes by kernel class and dtype.

### 7.7 Statistical Analysis

For matched binary outcomes, use the same family of methods already documented
for TritonGen:

- paired exact McNemar-style tests over discordant pairs;
- paired bootstrap confidence intervals for lift;
- Holm correction for multiple comparisons;
- Wilson intervals for condition-level rates;
- logistic models only when outcome variation is sufficient.

Pre-register the primary comparisons:

1. `C2_gpt_C` vs `C2_local_C`.
2. `C2_gpt_C` vs `C2_gpt_retry_no_feedback`.
3. `C3_gpt_P` vs `C3_local_P`.
4. `C3_gpt_P` vs `C3_gpt_retry_no_feedback`.
5. For C+P, `gpt_P_local_C` vs `local_P_local_C`.
6. For C+P, `local_P_gpt_C` vs `local_P_local_C`.
7. For C+P, `gpt_P_gpt_C` vs each single-frontier-loop treatment.

Do not overclaim if the seeded fixture set is small. Smoke and development
scales should produce engineering evidence and directional signals, not final
paper claims.

## 8. Feasibility

This is feasible in the current architecture because both loops are already
dependency-injected:

- `cluster2.feedback.repair_loop.run_repair_loop` accepts a generation callable,
  evaluation callable, feedback builder, repair budget, and optional seed source.
- `cluster3.feedback.compile_error_repair.run_p_repair_loop` accepts a
  generation callable, evaluation callable, seed attempt, and repair budget.
- `cluster3.feedback.c_loop_adapter.run_cluster3_c_loop_from_f2` already wraps
  Cluster 2 C repair for Cluster 3 composite conditions.

That means GPT can be introduced as a generation callable for repair attempts
without changing the evaluator or weakening the C/P boundaries.

The hard parts are not conceptual. They are engineering controls:

- provider API credentials and secrets;
- structured source extraction;
- provider request/response provenance;
- provider failure classification into F3;
- deterministic artifact writing and resume behavior;
- cost caps;
- model snapshot pinning;
- fake-provider tests before paid calls;
- artifact registry and analyzer compatibility.

## 9. Implementation Plan

### Phase A: Documented Smoke Contract

Add a frontier-ablation artifact plan before code:

- planned output paths;
- allowed conditions;
- scale tier;
- provider model ids;
- repair budgets;
- row-count targets;
- provider metadata fields;
- F3 provider-failure policy;
- cost cap;
- go/no-go criteria.

### Phase B: Provider Client Boundary

Add a small provider boundary, for example:

```text
shared/provider_backends/openai_responses.py
shared/provider_backends/schema.py
```

The boundary should expose a callable compatible with the existing repair loop
generation inputs. It should return source text plus metadata, while tests use
a fake provider that returns deterministic source.

Required metadata:

- `provider="openai"`;
- `provider_api="responses"`;
- `provider_model_id`;
- `provider_model_snapshot`;
- `reasoning_effort`;
- `temperature`;
- `max_output_tokens`;
- `response_id`;
- `request_id`;
- `input_tokens`;
- `output_tokens`;
- `cached_input_tokens` where available;
- `provider_error_type` on failure;
- `prompt_sha256`;
- `response_sha256`;
- `source_sha256`.

### Phase C: Cluster 2 Seeded C Runner

Add a runner that consumes fixed F2 seed candidates and runs the C ablation
cells. Candidate seed sources can come from:

- existing F2 smoke fixtures;
- current G+C F2 rows;
- a frozen development artifact designed to produce F2 failures.

Do not use current C paper rows as the only seed source, because they are
currently F0 and would not exercise C.

### Phase D: Cluster 3 Seeded P Runner

Add a runner that consumes fixed F1 compile-failure seed candidates and runs
the P ablation cells. This should use the existing `PSeedAttempt` validation so
attempt 0 is cached, hash-bound, and not regenerated.

### Phase E: Composite C+P Runner

After C and P smokes are independently green, run `C+P` and `G+C+P` with a
backend matrix:

```text
P_backend in {local, gpt}
C_backend in {local, gpt}
```

The runner should store both loop-specific terminal fields and the row-level
terminal outcome.

### Phase F: Analyzer Extension

Add analyzer support for:

- `repair_backend`;
- `c_repair_backend`;
- `p_repair_backend`;
- `provider_model_id`;
- `provider_model_snapshot`;
- provider-F3 counts;
- cost summaries;
- matched-pair backend comparisons.

Do not mix frontier-backend rows into current `outputs/analysis/factorial_2x2_preliminary.json`.
Create a new analyzer output lineage.

## 10. Scale Gates

Recommended progression:

| Gate | Scope | Claim level |
|---|---|---|
| smoke | one kernel, one dtype, one seed, one repair budget | infrastructure only |
| seeded development | three kernel classes, selected F2/F1 seeds, `R=1` and `R=3` | directional only |
| broad development | all three current archetypes, dtypes, selected seeds, fake-provider tests green | directional only |
| paper-candidate | frozen artifacts, registry, analyzer, cost report, audit, sufficient row count | reportable only after review |

No paper-scale frontier run should start until provider-cost estimates, rate
limits, row schema, and analyzer behavior are reviewed.

## 11. Is It Possible

Yes. It is possible as a new ablation lineage because the current repair loops
are already structured around injected generation callables and external
evaluation. GPT does not need to run Triton, evaluate correctness, or see hidden
state. It only needs to return a candidate source module that the existing
TritonGen evaluator can test.

It is not possible to make the result directly comparable to current artifacts
by silently swapping GPT into old rows. The provider model, decoding behavior,
prompt extraction, token costs, and reproducibility profile are different. This
must be treated as a new backend factor or new artifact lineage.

## 12. Would It Be Beneficial

Likely yes, especially for Cluster 3 P. Compiler feedback is structured natural
language plus compiler diagnostics, and frontier coding models are strong at
repairing code from diagnostic context. A successful P ablation would show that
the compile-feedback loop is a high-value control surface.

Cluster 2 C is also worth testing, but the benefit depends on the quality of
the public Level 2 feedback. If the feedback says only that numeric values are
wrong, GPT may still struggle. If the feedback includes stable public shape and
diff summaries without leaking private eval data, GPT may extract useful
indexing, mask, stride, or arithmetic fixes.

The study is beneficial even if GPT does not help. A negative result would be
strong evidence that the current feedback signal is insufficient, that the
Triton source surface is too brittle, or that the evaluator/prompt boundary
needs redesign.

## 13. Risks And Controls

| Risk | Control |
|---|---|
| Frontier model changes over time | pin provider model snapshot and record retrieval date |
| Cost blowup | hard budget caps, R=1 smoke first, token estimates before run |
| Provider nondeterminism | matched seeded design, repeated seeds, snapshot pinning, report variance |
| Hidden evaluator leakage | use existing C/P prompt sanitizers and boundary tests |
| GPT output extraction failures | structured output schema plus strict source validation |
| Invalid comparability | new artifact lineage and backend labels |
| F3/provider failures | explicit provider-F3 failure taxonomy and retry policy |
| Overclaiming from fixtures | separate fixture, development, and paper-candidate claims |
| G semantics drift | only claim G when grammar path is actually active and documented |

## 14. Recommended First Experiment

Start with two smoke studies:

1. **Cluster 2 C smoke.**
   - One ReLU F2 fixture from `cluster2/tests/fixtures/`.
   - `R=1`.
   - Compare `local_C`, `gpt_C`, and `gpt_retry_no_feedback`.
   - Outcome: Level 2 functional success and terminal failure code.

2. **Cluster 3 P smoke.**
   - One curated F1 compile-failure Triton fixture.
   - `R=1`.
   - Compare `local_P`, `gpt_P`, and `gpt_retry_no_feedback`.
   - Outcome: compile success, terminal failure code, and whether F2 is exposed.

If both pass infrastructure checks, move to development scale with all three
kernel archetypes and repair budgets `R=1` and `R=3`.

## 15. Decision

The frontier-feedback ablation is worth pursuing, but only as a controlled
seeded repair study first. It should not rewrite current Cluster 2 artifacts,
should not claim full 2^3 results, and should not conflate frontier repair with
grammar guidance or evaluator judgment.

The most defensible thesis framing is:

```text
We ablate the feedback consumer while holding the feedback signal and evaluator
constant, asking whether C and P contain actionable information that stronger
frontier models can exploit.
```

## 16. Sources

- [OpenAI GPT-5.5 model documentation](https://developers.openai.com/api/docs/models/gpt-5.5)
- [OpenAI structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI API reference overview, request IDs and model stability guidance](https://developers.openai.com/api/reference/overview)
- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [FeedbackEval: A Benchmark for Evaluating Large Language Models in Feedback-Driven Code Repair Tasks](https://arxiv.org/abs/2504.06939)
- [KernelBench: Can LLMs Write Efficient GPU Kernels?](https://arxiv.org/abs/2502.10517)
- [LLMLOOP: Improving LLM-Generated Code and Tests through Automated Iterative Feedback Loops](https://arxiv.org/abs/2603.23613)
- [INTERVENOR: Prompting the Coding Ability of Large Language Models through Interactive Chain of Repair](https://aclanthology.org/2024.findings-acl.124.pdf)
- [TritonGen frontier model and vLLM viability report](frontier_model_vllm_viability_report.md)
- [TritonGen Cluster 2 methodology](03_methodology_cluster2.md)
- [TritonGen Cluster 3 implementation specification](cluster3_implementation_specification.md)
