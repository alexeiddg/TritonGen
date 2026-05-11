# Cluster 3 - Compiler/Profiler Repair Loop (P-factor)

**Status: NOT STARTED - contract TBD**

Cluster 3 research scope is governed by
`.contracts/research/research_scope.md` and
`.contracts/research/scale_policy.md`. Detailed internal execution notes may
exist under `.contracts/agentic/`, but those notes are not paper-facing
methodology.

## Scope

Cluster 3 owns the P-factor as compiler/profiler repair for Triton-only
kernels. It uses structured Triton compiler/runtime errors to improve
compilability, then uses benchmark/profiler feedback to improve speed once a
candidate is functionally correct.

Cluster 3 is not an RL cluster. It does not train, fine-tune, or update the
model. It also does not generate CUDA/C++/CUTLASS/CuTe kernels.

## Scale policy

Cluster 3 must follow `.contracts/research/scale_policy.md`.

Build P at smoke scale first:

```text
one kernel, condition P, n=1, development model
```

After compiler/runtime feedback and performance gating run end to end, promote
to development scale:

```text
three kernels, active P conditions, n=3..5, development model
```

Cluster 3 paper-scale runs are not allowed until both Cluster 2 and Cluster 3
are stable at development scale. Paper-scale performance results must use
functionally correct kernels only, frozen prompts/feedback templates, frozen
benchmark settings, and explicit artifact manifests. Development-scale timing
data is useful for engineering decisions but is not paper evidence.

## Factorial conditions

| Condition | Grammar (G) | Test-driven feedback (C) | Compiler/profiler repair (P) |
|-----------|-------------|--------------------------|------------------------------|
| P         | OFF         | OFF                  | ON                |
| G+P       | ON          | OFF                  | ON                |
| C+P       | OFF         | ON                   | ON                |
| G+C+P     | ON          | ON                   | ON                |

`C` in this table means the Cluster 2 test-driven feedback loop is active before
compiler/profiler repair. Cluster 3 reads lower-level artifacts for comparison
but only owns P-enabled conditions.

## Boundary rules

- **IN SCOPE:** Triton compiler error feedback, runtime launch failure feedback,
  benchmarked generated Triton launchers, eager PyTorch and `torch.compile`
  baselines when available, speedup calculations, fast@p metrics, bounded
  compiler/profiler re-prompting.
- **OUT OF SCOPE:** Grammar constraint logic (Cluster 1), test-driven semantic
  repair beyond reusing Cluster 2, RL/model training,
  CUDA/C++/CUTLASS/CuTe generation, TritonBench expansion until the core
  KernelBench subset is stable.

Level 3 memory-safety checks are optional/deferred. Do not block Cluster 3 on
sanitizer tooling unless a separate safety contract is written.

## Dependencies on Cluster 1 and 2

- `shared.eval` - Level 0/1/2/4 gated evaluation
- `shared.modal_harness` - remote generation, compile, correctness, and
  performance evaluation
- `cluster2.feedback` - test-driven loop as a sub-component when condition
  contains C
- `cluster1.data.kernels` - same three KernelBench kernel specs as baseline;
  broader datasets are future work

## Contract

The formal Cluster 3 research contract is TBD. Until then, do not expand the
research scope beyond `.contracts/research/research_scope.md` and
`.contracts/research/scale_policy.md`; use internal agentic notes only as
implementation guidance.
