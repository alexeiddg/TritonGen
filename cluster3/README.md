# Cluster 3 - Compile-Error Repair Loop (P-factor v1)

**Status: IMPLEMENTATION READY - v1 spec reviewed, code not implemented yet**

Cluster 3 research scope is governed by
`.contracts/research/research_scope.md` and
`.contracts/research/scale_policy.md`. Detailed internal execution notes may
exist under `.contracts/agentic/`, but those notes are not paper-facing
methodology.

The active implementation source for v1 is
`docs/cluster3_implementation_specification.md`. It narrows the first
implementation to compile-error repair only. No Cluster 3 artifacts, P results,
profiler feedback, speedup claims, or paper-scale runs exist yet.

## Scope

Cluster 3 v1 owns the P-factor as bounded compile-error repair for generated
Triton kernels. P observes `F1_COMPILE` evidence only and uses structured
Triton compiler errors to improve compilability.

Profiler feedback, timing feedback, speedup optimization, Level 4 performance
repair, and F1 runtime-launch repair are deferred to a future contract. Cluster
3 v1 does not make performance claims.

Cluster 3 is not an RL cluster. It does not train, fine-tune, or update the
model. It also does not generate CUDA/C++/CUTLASS/CuTe kernels.

## Scale policy

Cluster 3 must follow `.contracts/research/scale_policy.md`.

Build P at smoke scale first:

```text
one kernel, condition P, n=1, development model
```

After compile-error repair runs end to end, promote to development scale:

```text
three kernels, active P conditions, n=3..5, development model
```

Cluster 3 paper-scale runs are not allowed until both Cluster 2 and Cluster 3
are stable at development scale. Paper-scale P results require frozen
prompts/feedback templates, explicit artifact manifests, analyzer
reportability, and a separate promotion review.

## Factorial conditions

| Condition | Grammar (G) | Test-driven feedback (C) | Compile-error repair (P) |
|-----------|-------------|--------------------------|------------------------------|
| P         | OFF         | OFF                  | ON                |
| G+P       | ON          | OFF                  | ON                |
| C+P       | OFF         | ON                   | ON                |
| G+C+P     | ON          | ON                   | ON                |

Where G appears, it inherits the Cluster 1 two-layer acceptance model:
grammar-guided decoding plus offline semantic post-validation. XGrammar
token-level masking is the decoding layer; the offline semantic validator is the
structural/surface validation layer. P must not reinterpret grammar rejection as
compile-error repair input unless a later contract explicitly adds that handoff.

`C` in this table means the Cluster 2 test-driven feedback loop is active when
the candidate reaches Level 2 correctness failure. Cluster 3 owns only
P-enabled conditions and reuses Cluster 2 surfaces through the compatibility
adapters defined in the implementation specification.

## Boundary rules

- **IN SCOPE:** Triton compile-error feedback, `F1_COMPILE` dispatch,
  compile-error prompt construction, bounded compile-repair attempts, P/C
  orchestration compatibility, row schema, analyzer compatibility, and local
  tests.
- **OUT OF SCOPE:** Grammar constraint logic (Cluster 1), test-driven semantic
  repair beyond reusing Cluster 2, profiler/timing/speedup repair, runtime
  launch repair, RL/model training, CUDA/C++/CUTLASS/CuTe generation, and
  TritonBench expansion until the core KernelBench subset is stable.

Level 3 memory-safety checks are optional/deferred. Do not block Cluster 3 on
sanitizer tooling unless a separate safety contract is written.

## Dependencies on Cluster 1 and 2

- `shared.eval` - Level 0/1/2 gated evaluation and shared failure taxonomy
- `shared.modal_harness` - existing Modal image and provenance helpers
- `cluster2.feedback` - test-driven Level 2 loop as a sub-component when
  condition contains C
- `cluster1.data.kernels` - same three KernelBench kernel specs as baseline;
  broader datasets are future work

## Contract

The v1 implementation contract is
`docs/cluster3_implementation_specification.md`. Formal research contracts still
govern report-facing claims. Do not expand the v1 scope beyond compile-error
repair without updating the implementation specification, current docs, and
formal contracts first.
