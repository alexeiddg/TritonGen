# Cluster 2 — Compiler Feedback Loop (C-factor)

**Status: NOT STARTED — depends on Cluster 1 completion**

## Scope

Cluster 2 adds the compiler error feedback mechanism (C-factor) on top of the
grammar-constrained generation from Cluster 1. It implements the repair loop:

1. Generate a Triton kernel (optionally with grammar constraint)
2. Attempt compilation via `cluster1.validation.compile_check`
3. Feed the compiler error back to the LLM as a structured re-prompt
4. Repeat up to N repair iterations, logging each attempt

## Factorial conditions

| Condition | Grammar (G) | Compiler feedback (C) |
|-----------|-------------|----------------------|
| ∅         | OFF         | OFF                  |
| G         | ON          | OFF                  |
| C         | OFF         | ON                   |
| G+C       | ON          | ON                   |

## Boundary rules

- **IN SCOPE:** Compiler error parsing, structured re-prompt construction,
  repair loop orchestration, per-attempt result logging
- **OUT OF SCOPE:** Numerical correctness checks, profiler/timing, RL reward
  shaping — these belong to Cluster 3

## Dependencies on Cluster 1

- `cluster1.validation.compile_check` — compile gate
- `cluster1.results.dataclass.GenerationResult` — extended with repair fields
- `cluster1.data.kernels` — same three KernelBench kernel specs

## Contract

See `.contracts/cluster2_contract.md` (to be written after Cluster 1 is complete).
