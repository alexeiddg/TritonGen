# Cluster 3 — RL / Performance Feedback (P-factor)

**Status: NOT STARTED — depends on Cluster 1 and 2 completion**

## Scope

Cluster 3 adds performance-based reinforcement learning (P-factor). Instead of
stopping at compile success, it uses profiler feedback (throughput, occupancy,
memory bandwidth) as a reward signal to guide generation.

## Factorial conditions

| Condition | Grammar (G) | Compiler feedback (C) | Perf feedback (P) |
|-----------|-------------|----------------------|-------------------|
| ∅         | OFF         | OFF                  | OFF               |
| G         | ON          | OFF                  | OFF               |
| C         | OFF         | ON                   | OFF               |
| P         | OFF         | OFF                  | ON                |
| G+C       | ON          | ON                   | OFF               |
| G+P       | ON          | OFF                  | ON                |
| C+P       | OFF         | ON                   | ON                |
| G+C+P     | ON          | ON                   | ON                |

## Boundary rules

- **IN SCOPE:** Nsight Compute / `triton.testing.do_bench` profiling,
  reward shaping (throughput vs roofline), RL policy gradient updates,
  speedup calculations, TritonBench integration
- **OUT OF SCOPE:** Grammar constraint logic (Cluster 1), compiler repair
  loops (Cluster 2)

## Dependencies on Cluster 1 and 2

- `cluster1.validation.compile_check` — must compile before profiling
- `cluster2.feedback` — repair loop as a sub-component
- `cluster1.data.kernels` — same three KernelBench kernel specs as baseline;
  TritonBench may be added as a secondary performance dataset

## Contract

See `.contracts/cluster3_contract.md` (to be written after Clusters 1 and 2 are complete).
