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
> grammar-constrained decoding successes are substantially attributable to
> task-specific grammar encoding rather than syntactic enforcement.
> Test-driven feedback is expected to dominate as the strongest single
> inference-time mechanism, and combining it with compiler feedback is expected
> to yield the best correctness-per-iteration ratio without model fine-tuning.

## Mechanisms

| Factor | Mechanism | Cluster | Primary defect class |
| --- | --- | --- | --- |
| `G` | Grammar-constrained decoding | Cluster 1 | invalid syntax, surface shape, and API usage |
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

## Triton-Only Boundary

The generated artifact under study is a Python module containing Triton kernels
and Python launch wrappers. The research does not generate raw CUDA C/C++,
CUTLASS, CuTe, TVM, MLIR, or custom DSL kernels.

The project also does not fine-tune, RL-train, or otherwise update model
weights. All mechanisms are inference-time controls around the same model.

## Cluster 1 Reframing

The current strict Cluster 1 grammar is retained as a
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
- the final strict-grammar condition reached `180/180` compile acceptance;
- the strict-grammar condition produced very low diversity;
- the result measures what happens when the grammar is allowed to encode the
  task family.

Paper-safe interpretation:

> A task-aware, family-scoped Triton grammar can force compile acceptance for
> the scoped ReLU, Softmax, and GEMM subset, but this is an upper-bound control
> and not evidence of broad grammar-constrained Triton generation.

The task-agnostic G condition is the primary grammar condition for broader
paper-scale claims. The comparison between `G_task_agnostic` and
`G_template_upper_bound_reference` quantifies task encoding versus syntactic
guidance. Template upper-bound results may be reported only as
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
- Report the strict grammar as a template G diagnostic/reference upper-bound
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
