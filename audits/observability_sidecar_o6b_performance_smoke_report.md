# O6b Modal GPU Performance Smoke Report

- Version: 1.0.0
- Date: 2026-06-04
- Branch: `codex/observability-o6-performance-contract`
- Baseline: `d966ad0 Add O6a performance contract scaffolding`
- Classification: `O6B_PERFORMANCE_SMOKE_COMPLETE_WITH_CAVEATS`

## Executive Summary

O6b implemented a dedicated performance sidecar schema, pure local benchmark
summary helpers, and an opt-in Modal GPU smoke entrypoint. One bounded Modal GPU
smoke benchmark ran for a fixed built-in ReLU fixture using CUDA events.

The correctness prerequisite passed. The candidate Triton fixture measured
slower than the Torch reference on this single T4 smoke run, so
`speedup_vs_baseline` is below 1.0. This is smoke-only timing evidence and is
not paper-scale performance evidence.

## Run Packet

```text
MODAL_AUTHORIZED: YES
GPU_AUTHORIZED: YES
PERFORMANCE_EXECUTION_AUTHORIZED: YES
GENERATION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO for existing outputs/
PAPER_SCALE_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
NSIGHT_AUTHORIZED: NO
NCU_AUTHORIZED: NO

benchmark_scope: smoke
benchmark_target_artifact: fixed_built_in_benchmark_fixture
baseline_artifact_or_type: torch_reference
candidate_type: triton_kernel_fixture
kernel_class: elementwise_relu
problem_id: smoke_relu
dtype: fp32
shape_set: [[1048576]]
device_gpu_type: [T4, L4]
modal_image_digest: unavailable: shared.modal_harness.images.triton_compile_image digest was not captured by the O6b smoke packet
timing_method: cuda_events
warmup_iterations: 10
measured_repetitions: 50
timeout_s: 300
correctness_prerequisite: candidate and baseline outputs must match before timing
performance_sidecar_output_path: artifacts/observability_performance/o6b_smoke_relu_performance.jsonl
no_scientific_row_mutation: true
paper_scale_packet_required_for_claims: true
modal_authorized: true
gpu_authorized: true
performance_execution_authorized: true
generation_authorized: false
output_mutation_authorized: false
paper_scale_authorized: false
profiler_trace_authorized: false
nsight_authorized: false
ncu_authorized: false
```

## Exact Modal Invocation

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m shared.observability.performance_modal_smoke --sidecar-path artifacts/observability_performance/o6b_smoke_relu_performance.jsonl
```

The entrypoint printed the pre-execution bounds before the remote call:

```text
gpu_setting: [T4, L4]
shape: [1048576]
dtype: fp32
warmup_iters: 10
repetitions: 50
timeout_seconds: 300
sidecar_path: artifacts/observability_performance/o6b_smoke_relu_performance.jsonl
no_output_mutation: existing outputs/ is not read or written
no_generation: model generation is not invoked
no_profiler_trace: profiler traces are not collected
```

## GPU Device Used

```text
gpu_type: Tesla_T4
```

## Timing Method

```text
cuda_events
```

The remote function used CUDA event elapsed time for both the Torch reference
baseline and the Triton fixture candidate. `triton.testing.do_bench`,
`torch.profiler`, Nsight, and NCU were not used.

## Benchmark Target And Baseline

```text
benchmark_id: o6b_smoke_relu_fp32_1048576_cuda_events
kernel_class: elementwise_relu
problem_id: smoke_relu
dtype: fp32
shape_signature: 1048576
baseline_type: torch_reference
candidate_type: triton_kernel_fixture
```

## Correctness Prerequisite Result

```text
correctness_prerequisite_passed: true
```

The remote benchmark verified exact equality between the Torch reference ReLU
output and the fixed Triton ReLU fixture output before any timing samples were
recorded.

## Sidecar Path

```text
artifacts/observability_performance/o6b_smoke_relu_performance.jsonl
sha256: 716bda3a4be56e86543aa6327377649cf7ec2ddb2b4f74b587da86215ee7c931
```

The sidecar is intentionally under `artifacts/observability_performance/`, not
under `outputs/`. It is the reviewed smoke evidence artifact for this O6b
packet; any rerun or overwrite requires a new signed packet.

## Sidecar Row Summary

```text
baseline_median_ms: 0.04639999940991402
baseline_p25_ms: 0.04541599936783314
baseline_p75_ms: 0.04707200080156326
candidate_median_ms: 0.06969600170850754
candidate_p25_ms: 0.06945599988102913
candidate_p75_ms: 0.0707120019942522
warmup_iters: 10
repetitions: 50
measurement_status: complete
scientific_row_mutation_allowed: false
paper_scale_claim_allowed: false
profiler_traces_allowed: false
```

## Speedup Value

```text
speedup_vs_baseline: 0.6657483682345889
```

This value is computed as:

```text
baseline_median_ms / candidate_median_ms
```

Because the value is below 1.0, the fixed Triton smoke fixture was slower than
the Torch reference in this single T4 smoke run.

## No Scientific Row Mutation Proof

No Cluster 1, Cluster 2, Cluster 3, analyzer, shared Modal harness, repair
history, dependency, lockfile, MLflow runtime, or `outputs/` paths are modified
by the O6b implementation. The generated sidecar path is outside `outputs/`.

Final protected-scope diff scan result is recorded below.

## No Profiler Trace Proof

O6b used CUDA events only. The implementation does not call `torch.profiler`,
Nsight, NCU, NVML, or Triton profiler surfaces, and it does not persist trace
files or Modal Volumes.

Final profiler/Nsight/NCU scan result is recorded below.

## Tests Run

- `.venv/bin/python -m pytest shared/tests/test_observability_performance_contract.py shared/tests/test_observability_performance_sidecar.py shared/tests/test_observability_performance_harness.py shared/tests/test_observability_imports.py -q`
  - Result: `91 passed`
- `.venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_redaction.py shared/tests/test_observability_logger.py shared/tests/test_observability_billing_reconciliation.py shared/tests/test_observability_billing_modal_collection.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py shared/tests/test_factorial_analysis.py -q`
  - Result: `527 passed`

## Scans Run

- `git diff --check`
  - Result: passed.
- Direct no-index whitespace checks for untracked O6b code/test/audit files and
  the generated performance sidecar
  - Result: no diagnostics.
- Protected-scope diff scan:

```bash
git diff --name-only -- cluster1 cluster2 cluster3 outputs shared/modal_harness shared/analysis shared/repair_history .github pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Result: empty output.

- Profiler/Nsight/NCU scan:

```text
rg -n "torch\.profiler|nsys|ncu|nvml|pynvml|subprocess.*nsys|subprocess.*ncu|triton\.profiler" shared/observability shared/tests/test_observability_*.py audits/observability_sidecar_o6b_performance_smoke_report.md
```

Result: hits were limited to explicit audit prohibitions, redaction deny
patterns, and import-test forbidden-string fixtures. No profiler/Nsight/NCU
implementation call or persisted trace path was found.

- Claim-boundary scan:

```text
rg -n "paper_scale_claim_allowed.*true|PAPER_SCALE_AUTHORIZED: YES|pass@k|cost_per_success|ROI|economic_lift|benchmark economics" shared/observability shared/tests/test_observability_*.py docs/handoff audits/observability_sidecar_o6b_performance_smoke_report.md
```

Result: hits were deny rules, negative fixtures, or explicit prohibition/caveat
language. No O6b paper-scale, pass@k, cost-per-success, ROI, economic-lift, or
benchmark-economics claim was found.

- Sidecar validation:
  - `load_performance_sidecar_rows(...)` loaded exactly one row.
  - Row `gpu_type`: `Tesla_T4`.
  - Row `speedup_vs_baseline`: `0.6657483682345889`.
  - Sidecar SHA-256:
    `716bda3a4be56e86543aa6327377649cf7ec2ddb2b4f74b587da86215ee7c931`.

## Caveats

- This is one bounded smoke benchmark, not a benchmark matrix.
- This is not paper-scale evidence.
- The measured fixture is intentionally fixed and built in; it is not
  model-generated code.
- The candidate was slower than the baseline in this smoke run.
- The performance sidecar is smoke evidence only; any rerun or overwrite
  requires a new signed packet.

## Classification

```text
O6B_PERFORMANCE_SMOKE_COMPLETE_WITH_CAVEATS
```

## Next-Step Recommendation

Commit the reviewed O6b package, then run the compact O5b/O5c/O6a/O6b final
promotion audit before fast-forwarding `codex-track-handoff-context`.
