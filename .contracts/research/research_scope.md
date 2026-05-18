# Research Scope

**Status:** research-facing scope summary  
**Date:** 2026-05-11  
**Audience:** paper, thesis, committee notes

## Thesis Framing

This project studies inference-time control mechanisms for LLM-generated Triton
kernels. The model weights are held fixed while external scaffolding changes.
The core question is whether the mechanisms compose additively or interfere.

Working claim:

> Inference-time control mechanisms for LLM-generated Triton kernels - grammar
> constraints, test-driven feedback, and compiler/profiler repair - make
> non-additive contributions to functional correctness. Task-agnostic grammar
> constraints provide minimal lift over no constraint alone; published
> grammar-guided decoding successes are substantially attributable to
> task-specific grammar encoding rather than syntactic enforcement.
> Test-driven feedback is expected to dominate as the strongest single
> inference-time mechanism, and combining it with compiler feedback is expected
> to yield the best correctness-per-iteration ratio without model fine-tuning.

## Mechanisms

| Factor | Mechanism | Cluster | Primary defect class |
| --- | --- | --- | --- |
| `G` | Grammar-guided decoding plus offline semantic post-validation | Cluster 1 | invalid syntax, surface shape, and API usage |
| `C` | Test-driven feedback | Cluster 2 | numerical correctness failures |
| `P` | Compiler/profiler repair | Cluster 3 | compiler/runtime failures and slow but correct kernels |

The final factorial vocabulary is:

```text
none
G
C
P
G+C
G+P
C+P
G+C+P
```

## Current Evaluation And Replay Contract

Evaluation semantics are shared across clusters. `shared/eval/` is the source of
truth for shape schedules, Level 0 parse/signature behavior, Level 1 compile
failure codes, Level 2 correctness behavior, and canonical failure taxonomy.
Cluster-specific code may preserve legacy fields for compatibility, but primary
analysis and replay decisions use canonical `failure_code` values.

Cluster 1 compile evaluation is Level 0 plus Level 1 only. Level 0 is explicit
AST parse and launcher-signature validation, followed by Level 1 runtime import,
secondary `inspect.signature` validation, and dummy Triton launches. Cluster 1
compile shapes are derived from shared compile-shape helpers, not independent
per-spec schedules.

Cluster 2 replay controls consume frozen Cluster 1 rows through the shared
Cluster 1 adapter and shared failure taxonomy. Frozen rows are not rewritten on
disk. Legacy fields such as `compile_error_type` remain historical diagnostics;
row-level canonical `failure_code`, or syntax-aware canonicalization from legacy
compile labels and messages, is the replay and analysis contract.

The frozen none baseline was revalidated after alignment through the Phase 4
Modal L4 diagnostic. The accepted post-fix evidence artifact is
`outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`.
It records zero compile-success drift, zero C1/C2 entrypoint disagreement, and
the expected syntax-aware reclassification of legacy `SignatureError` wrappers
to `F0_PARSE`.

## G Enforcement Model

### G acceptance contract

G-acceptance requires both GBNF final-state acceptance and semantic validation.
During generation, XGrammar applies token-level masking against the GBNF
grammar. After generation, the semantic validator checks structural and surface
constraints that are not fully captured by the context-free grammar. GBNF
final-state acceptance is necessary but not sufficient. A row is counted as
G-accepted only when `grammar_valid=true`, which requires both grammar-layer
acceptance and semantic validation. Rows that do not satisfy the joint contract
are labeled `grammar_valid=false` and include `rejection_layer` attribution.

`grammar_active=true` means constrained decoding was attempted.
`grammar_active=true` does not imply G-acceptance. `masked_token_rate` is a
diagnostic for masking activity, not an acceptance metric. `grammar_valid` is
the acceptance field. `rejection_layer` explains where acceptance failed.

Short methodology label:

> grammar-guided decoding plus offline semantic post-validation

The decoding layer is XGrammar token-level masking against the GBNF grammar. The
validation layer is the offline semantic, structural, and surface validator. G
acceptance is the joint pass condition. This clarification does not change the
factor definition; it clarifies the measurement contract for rows generated
under the G factor.

## Current Iteration Scope

The current iteration analyzes a temporary 2² subset over G and C: none, G, C,
and G+C.

The full 2³ factorial over G, C, and P remains the defined project goal.
P-containing cells are deferred for this iteration and are not included in
current paper-claiming outputs. Current 2² outputs must not be described as
completion of the full factorial.

This is a current-status scope statement, not a methodology realignment.

## Triton-Only Boundary

The generated artifact under study is a Python module containing Triton kernels
and Python launch wrappers. The research does not generate raw CUDA C/C++,
CUTLASS, CuTe, TVM, MLIR, or custom DSL kernels.

The project also does not fine-tune, RL-train, or otherwise update model
weights. All mechanisms are inference-time controls around the same model.

## Cluster 1 Reframing

The current template Cluster 1 grammar is retained as a
`template_upper_bound` diagnostic/reference control. It is not the main grammar
result.

Locked attribution language:

- task-agnostic G is the primary grammar condition for paper claims.
- template G is a diagnostic/reference upper bound.
- template G is not used as the primary grammar-effect estimate; it is diagnostic/reference only.
- Primary task-agnostic G comparisons must use the task-agnostic grammar unless
  they are explicitly labeled as template-G diagnostic/reference upper-bound
  results.
- Strict baseline and permissive baseline are separate diagnostics. They are not
  alternate grammar conditions and must not be mixed into the primary
  grammar-effect estimate.

Reason:

- the grammar is family-scoped to ReLU, Softmax, and GEMM;
- the final diagnostic/reference template-grammar condition reached `180/180`
  compile acceptance;
- the diagnostic/reference template-grammar condition produced very low
  diversity;
- the result measures what happens when the grammar is allowed to encode the
  task family.

Paper-safe interpretation:

> A task-aware, family-scoped Triton grammar can force compile acceptance for
> the scoped ReLU, Softmax, and GEMM subset, but this is an upper-bound control
> and not evidence of broad task-agnostic G enforcement for Triton generation.

The task-agnostic G condition is the primary grammar condition for broader
paper-scale claims. The comparison between `G_task_agnostic` and
`G_template_upper_bound_reference` quantifies task encoding versus syntactic
guidance plus offline semantic validation. Template upper-bound results may be reported only as
reference/diagnostic context.

## Scale Boundary

Scale policy is defined in `.contracts/research/scale_policy.md`.

Development may use small runs to validate the pipeline and iterate on design.
Paper claims must come only from paper-scale artifacts with frozen prompts,
grammar variants, feedback templates, seed schedule, kernel set, model, and eval
gates.

The current frozen Cluster 1 `n=20` artifacts are a three-kernel
template-control subset. They are useful as a paper-style upper-bound reference
for that subset, but they are not the full future paper-scale factorial run.

Cluster 2 replay-control claims are paired-by-seed within-subject comparisons:
`C` pairs only against the frozen `none` row with the same
`(kernel_class, dtype, base_seed)`, and primary `G+C` pairs only against the
frozen task-agnostic G row with the same key. Template G replay rows are diagnostic/reference
upper-bound controls only. The replay manifest is the
canonical seed schedule.
Unmatched generated-vs-replay population comparisons are diagnostic only and
are excluded from primary claims.
Legacy compile-only factorial summaries, including
`shared/analysis/factorial.py::factorial_summary`, are structural-validity
diagnostics for Cluster 2. Primary Cluster 2 claims use Level 2
`functional_success` through paired replay summaries.

## Paper-Relevant Design Decisions

- Keep model weights fixed so the causal axis is external inference control,
  not training.
- Use KernelBench Level 1 tasks as the initial benchmark source.
- Use the three kernel classes elementwise, reduction, and matmul as the
  balancing axis.
- Separate syntactic validity, functional correctness, and performance into
  different evaluation levels.
- Report the template grammar as a template G diagnostic/reference upper-bound
  control, not as the main grammar condition.
- Enforce paired replay controls in the runner before new `C` or `G+C`
  generation starts; aggregation reports paired bootstrap lift and
  McNemar-style binary discordance summaries over matched seeds.
- Build Cluster 2 and Cluster 3 at smoke scale first, then development scale,
  then paper scale.

## Non-Goals

- RL, GRPO, TRL, or fine-tuning.
- Raw CUDA C/C++ generation.
- CUTLASS or CuTe generation.
- Prompt-level DSL abstraction as a fourth cluster.
- TritonBench expansion before the KernelBench subset and shared eval pipeline
  are stable.
- Speedup claims for kernels that fail functional correctness.
