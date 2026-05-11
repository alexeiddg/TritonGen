# Cluster 2 - Test-Driven Feedback Loop (C-factor)

**Status: NOT STARTED - contract TBD**

Cluster 2 research scope is governed by
`.contracts/research/research_scope.md` and
`.contracts/research/scale_policy.md`. Detailed internal execution notes may
exist under `.contracts/agentic/`, but those notes are not paper-facing
methodology.

## Scope

Cluster 2 owns the C-factor as correctness/test-driven feedback for Triton-only
generation. It repairs candidates until they pass PyTorch reference tests, or
until a fixed repair budget is exhausted.

The loop is centered on Level 2 functional correctness:

- shape mismatches;
- NaN/Inf outputs;
- numerical allclose failures;
- max absolute and relative error summaries;
- per-shape failure traces.

Level 0 parse/surface and Level 1 compile checks remain gates because tests
cannot run until source is valid and compilable. Cluster 2 may record those
failures, but compiler-specific repair strategy belongs to Cluster 3.

It implements the repair loop:

1. Generate a Triton kernel (optionally with grammar constraint)
2. Evaluate through the shared eval pipeline up to Level 2
3. Feed structured failure feedback back to the LLM
4. Repeat up to N repair iterations
5. Log the final result and the per-iteration repair trace

The standard repair budget is 5 repair attempts after the initial generation.

## Scale policy

Cluster 2 must follow `.contracts/research/scale_policy.md`.

Build C at smoke scale first:

```text
one kernel, condition C, n=1, development model
```

After the Level 2 correctness loop runs end to end, promote to development
scale:

```text
three kernels, active C conditions, n=3..5, development model
```

Cluster 2 paper-scale runs are not allowed until the repair loop is stable at
development scale. Paper-scale data must use the frozen paper kernel set, seed
schedule, prompts, feedback templates, and model. Development-scale repair
results are directional indicators only and must not be mixed into paper result
tables.

## Factorial conditions

| Condition | Grammar (G) | Test-driven feedback (C) |
|-----------|-------------|-------------------------|
| C         | OFF         | ON                      |
| G+C       | ON          | ON                      |

Cluster 2 reads Cluster 1 `none` and `G` artifacts for comparison. It does not
need to rerun them unless a reproducibility run explicitly requires it.

## Boundary rules

- **IN SCOPE:** PyTorch reference tests, tolerance-aware numerical comparison,
  correctness feedback, structured re-prompt construction, bounded repair loop
  orchestration, per-attempt result logging.
- **OUT OF SCOPE:** compiler-specific repair strategy, performance timing,
  profiler feedback, speedup reporting, RL/model fine-tuning,
  CUDA/C++/CUTLASS/CuTe generation.

## Dependencies

- `cluster1.validation.compile_check` - compile gate
- `cluster1.generation.modal_generate` - shared remote generation adapter
- `cluster1.data.kernels` - same three KernelBench kernel specs
- `shared.eval` - Level 0/1/2 gated evaluation
- `shared.modal_harness` - remote generation, compile, and correctness checks

## Contract

The formal Cluster 2 research contract is TBD. Until then, do not expand the
research scope beyond `.contracts/research/research_scope.md` and
`.contracts/research/scale_policy.md`; use internal agentic notes only as
implementation guidance.
