# O6a Performance Contract Report

- Date: 2026-06-04
- Branch: `codex/observability-o6-performance-contract`
- Baseline: `dc48782 Add O5c Modal billing collection adapter`
- Classification: `O6A_PERFORMANCE_CONTRACT_COMPLETE_WITH_CAVEATS`

## Executive Summary

O6 is now the Level-4 performance sidecar track rather than a disabled-only
placeholder. This O6a package does not execute timing work. It adds the
sidecar-only contract, schema validation, fail-closed redaction, future O6b
packet requirements, and tests needed before any Modal/GPU benchmark run can be
approved.

O6a keeps performance data out of Cluster 1/2/3 scientific result rows. It does
not mutate existing outputs, does not run Modal, does not run GPU work, does
not run generation, does not run profilers, and does not claim paper-scale
performance.

## Official Docs Consulted

- Modal GPU acceleration: https://modal.com/docs/guide/gpu
  - Modal supports GPU Functions and configurable GPU types.
- Modal Function reference: https://modal.com/docs/reference/modal.Function
  - Modal Functions can be invoked remotely and configured with resource
    options, but O6a does not invoke them.
- Modal PyTorch profiling example:
  https://frontend.modal.com/docs/examples/torch_profiling
  - Profiler traces are files on disk in ephemeral containers and require
    explicit persistence such as Modal Volumes if retained.
- PyTorch CUDA Event reference:
  https://docs.pytorch.org/docs/2.9/generated/torch.cuda.Event.html
  - CUDA events are a future timing-method candidate for O6b only.
- Triton `triton.testing.do_bench` reference:
  https://triton-lang.org/main/python-api/generated/triton.testing.do_bench.html
  - Triton benchmarking helpers are a future timing-method candidate for O6b
    only.

## Why O6 Is Performance-Enabled

The project now needs real Level-4 performance and speedup measurement, so O6
cannot remain a permanent disabled placeholder. The safe split is:

- O6a: contract, schema, redaction, docs, and fixture-only tests.
- O6b: separately approved Modal/GPU benchmark execution packet.

This preserves the observability sidecar boundary while making the future
benchmark packet explicit and reviewable.

## O6a/O6b Split

O6a authorizes no execution. It defines:

- `ObservabilityPerformanceContract`
- `default_o6a_performance_contract()`
- `required_o6b_run_packet_fields()`
- `validate_o6a_performance_contract()`

O6b must provide a signed packet with:

- benchmark target artifact
- baseline artifact or baseline type
- kernel class and problem ID
- dtype and shape set
- device/GPU type
- Modal image digest
- timing method
- warmup iterations
- measured repetitions
- timeout
- correctness prerequisite
- performance sidecar output path
- explicit no-scientific-row-mutation flag
- paper-scale packet requirement for claims

## Planned Timing Method Candidates

O6a records future candidates only:

- `cuda_events`
- `triton_do_bench`
- `torch_profiler`

O6a imports none of the runtime libraries for these methods and calls no timing
APIs.

## Baseline And Speedup Policy

Speedup is future O6b-only. O6a requires a fixed baseline policy:

```text
fixed_baseline_same_shape_dtype_device
```

O6b must lock shape, dtype, device/GPU type, correctness prerequisite, and
baseline artifact or baseline type before execution. Smoke or development
timing cannot become paper-scale performance claims without a separate
paper-scale packet.

## Sidecar-Only Artifact Policy

Future O6b measurements must be written to a dedicated performance sidecar.
They must not be added to compile/correctness rows, prior Cluster 1/2/3 result
schemas, historical outputs, analyzers, or pass@k scientific result rows.

O6a rejects measurement fields such as latency, throughput, speedup, kernel
time, wall time, timing samples, profiler traces, Nsight/NCU outputs, benchmark
scores, and performance/paper-scale claim fields. Review hardening also keeps
performance contract keys context-sensitive, so standalone sidecar attributes
cannot claim `performance_execution_authorized`.

## No-Execution Proof

O6a modified only shared observability schema/redaction/helper/test files and
docs/audit files. It does not add Modal, Torch, Triton, profiler, Nsight, NCU,
NVML, timing, generation, runner, output, analyzer, dependency, lockfile, or
MLflow runtime execution code.

## Future O6b Run-Packet Requirements

Future O6b must explicitly set:

```text
MODAL_AUTHORIZED:
GPU_AUTHORIZED:
PERFORMANCE_EXECUTION_AUTHORIZED:
GENERATION_AUTHORIZED:
OUTPUT_MUTATION_AUTHORIZED:
PAPER_SCALE_AUTHORIZED:
PROFILER_TRACE_AUTHORIZED:
NSIGHT_AUTHORIZED:
NCU_AUTHORIZED:
```

Profiler traces, Nsight, NCU, and trace persistence remain separately blocked
unless a later profiler packet names retention, redaction, and deletion policy.

## Tests Run

- `.venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_redaction.py shared/tests/test_observability_logger.py shared/tests/test_observability_imports.py shared/tests/test_observability_performance_contract.py -q`
  - Result: `254 passed`
- `.venv/bin/python -m pytest shared/tests/test_observability_billing_reconciliation.py shared/tests/test_observability_billing_modal_collection.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py shared/tests/test_factorial_analysis.py -q`
  - Result: `324 passed`

## Scans Run

Focused import-boundary tests prove shared observability modules do not import
remote/generation/performance stacks.

- `git diff --check`
  - Result: passed.
- Direct no-index whitespace checks for untracked O6a files
  - Result: no diagnostics.
- forbidden execution/scope diff scan
  - Result: empty.
- execution authorization scan
  - Result: empty.
- timing implementation import scan
  - Result: hits only negative/import-scan tests and redaction deny rules.
- performance claim scan
  - Result: hits only contract fields, deny rules, negative tests, future O6b
    packet requirements, and existing prohibitions/caveats.

## Unresolved Risks

- Actual timing quality is unproven until O6b runs under a signed Modal/GPU
  benchmark packet.
- Baseline selection still requires a concrete O6b packet decision.
- Profiler traces, Nsight, and NCU remain out of scope unless separately
  authorized.
- Smoke/development timing remains non-paper-scale evidence.

## Classification

```text
O6A_PERFORMANCE_CONTRACT_COMPLETE_WITH_CAVEATS
```

## Next Step Recommendation

Run an O6a review. If it passes, commit O6a. Start O6b only from a reviewed
packet that explicitly authorizes Modal/GPU performance execution and names the
benchmark target, baseline, resources, timing method, sidecar path, and claim
boundaries.
