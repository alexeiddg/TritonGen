# Post-Cluster 1 Scope and Execution Plan

**Status:** Authoritative bridge plan before Cluster 2 and Cluster 3 contracts
**Date:** 2026-05-11
**Applies to:** shared Modal harness, shared eval suite, Cluster 2 planning, Cluster 3 planning

## Purpose

This document prevents the project from stalling in "what is next" loops after
the Cluster 1 freeze. It does not replace future
`.contracts/agentic/cluster2_contract.md` or
`.contracts/agentic/cluster3_contract.md`.
Those contracts are still TBD. This file defines the pre-contract scope,
sequencing, and bite-sized engineering steps needed to make those contracts
straightforward to write.

The main outcome is a clear integration path for:

- the shared Modal GPU harness;
- the shared eval suite;
- the Cluster 2 test-driven feedback loop;
- the Cluster 3 compiler/profiler repair loop;
- the final Triton-only factorial experiment.

## Non-Negotiable Scope

### Triton-Only Output

The generated artifact under study is a Python module containing Triton kernels
and Python launch wrappers. The project does not generate or evaluate raw CUDA
C/C++, CUTLASS, CuTe, TVM, MLIR, or custom DSL kernels.

Allowed GPU/runtime language in infrastructure:

- PyTorch tensors may use GPU devices.
- Triton may lower kernels to GPU code internally.
- Modal may provide NVIDIA GPU workers.
- Tooling may mention GPU drivers or device availability when unavoidable.

Not allowed as research mechanisms:

- generated CUDA source;
- generated C++ extensions;
- generated CUTLASS or CuTe code;
- model fine-tuning or RL training as part of the core experiment;
- prompt-level DSL abstraction as a fourth cluster.

### Fixed Model, Inference-Time Controls

The thesis studies inference-time control mechanisms around a fixed model.
Changing the model weights is out of scope for the core experiment. This keeps
the causal axis interpretable:

- G changes decoding constraints.
- C changes test-driven correctness feedback during inference.
- P changes compiler/profiler repair during inference.

### Cluster 1 Result Reframing

The current Cluster 1 `180/180` G result must be described as a
task-aware template-grammar upper bound, not as evidence of general
grammar-constrained Triton generation.

Reason:

- the current grammar encodes ReLU, Softmax, and GEMM family surfaces;
- G outputs have one unique source per kernel/dtype cell in the final run;
- masked-token rates are effectively 1.0;
- the grammar is doing much of the structural work.

Paper-safe Cluster 1 wording:

> A task-aware, family-scoped Triton grammar establishes an upper-bound compile
> acceptance control: it can force canonical ReLU, Softmax, and GEMM modules to
> compile, but it collapses diversity and does not demonstrate broad Triton
> generation.

Recommended future Cluster 1 extension, before final paper claims:

- add a task-agnostic Triton grammar variant, or
- explicitly keep the current grammar as an upper-bound control and avoid any
  "general grammar-constrained generation" claim.

If a task-agnostic grammar is added, record it as a grammar variant such as
`grammar_variant="task_agnostic"` versus `grammar_variant="template_upper_bound"`.
Do not create a fourth factorial factor for this. It is a subcondition of G.

## Research Questions

The full study should answer these questions.

1. How much of grammar-constrained compile success comes from syntactic
   restriction versus task encoding?
2. Do inference-time controls for Triton kernel generation compose additively,
   or do they interfere?
3. Does test-driven feedback recover functional correctness that grammar alone
   cannot guarantee?
4. Does compiler/profiler repair improve compilability and speed without
   degrading functional correctness or exploding repair cost?
5. Which failure classes remain after each mechanism is added: parse/surface,
   compile/runtime, numerical correctness, or performance?

## Factor Vocabulary

Keep the existing canonical factor cells:

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

Recommended semantic mapping going forward:

| Factor | Meaning | Primary defect class |
| --- | --- | --- |
| `G` | Grammar-constrained decoding | invalid syntax/surface/API shape |
| `C` | Test-driven correctness feedback | numerical correctness failures |
| `P` | Compiler/profiler repair | compile/runtime failures and slow but correct kernels |

`C` is broader than a simple "run tests once" gate. It builds structured
feedback from PyTorch reference checks and numerical failure traces. Level 0/1
checks remain gates because tests cannot run until source is parseable and
compilable, but compiler-specific repair strategy belongs to P.

`P` covers compiler/profiler repair. It is not RL, and P does not fine-tune
model weights. It may generate repair prompts from Triton compiler/runtime
errors and from measured performance signals. Speed feedback is only valid
after a candidate passes functional correctness.

## Scale Policy

All work after Cluster 1 follows `.contracts/research/scale_policy.md`.

Canonical scale tiers:

| Tier | Use | Default shape |
| --- | --- | --- |
| `smoke` | prove an implementation path runs without crashing | one kernel, one condition, `n=1`, development model |
| `development` | iterate on prompts, grammars, feedback parsing, and harness decisions | three kernels, active conditions, `n=3..5`, development model |
| `paper` | produce reported results | target 6-9 balanced kernels, full factorial where applicable, `n=20`, larger model |

No paper-scale run should start until the relevant smoke and development-scale
paths are stable. Development-scale data may guide engineering decisions, but
it must not be mixed into paper-scale analysis.

Required metadata for new runners and sidecars:

- `scale_tier`;
- `kernel_count`;
- `kernel_ids`;
- `sample_size`;
- `model_id`;
- `seed_schedule`;
- `condition_set`;
- `grammar_variant` when G is enabled.

Cluster 2 should start as `cluster2_smoke_C_k1_n1_*`. Cluster 3 should start as
`cluster3_smoke_P_k1_n1_*`. Promote each to development scale before planning
the final paper-scale factorial.

## Cluster Boundaries

### Cluster 1: Grammar Upper Bound and Baseline

Current status: frozen.

Allowed conditions:

- `none`
- `G`

Evaluation ceiling:

- Level 0 parse/surface checks;
- Level 1 compile acceptance.

No Cluster 1 code path may run correctness tests, performance timing,
benchmarking, sanitizer tooling, or feedback repair.

Cluster 1 outputs remain useful as:

- the no-control baseline;
- the template-grammar upper-bound control;
- shared infrastructure proof for Modal generation and compile-only validation.

### Cluster 2: Test-Driven Feedback Loop

Future contract: `.contracts/agentic/cluster2_contract.md` TBD.

Cluster 2 owns the C factor. Its goal is to use PyTorch reference tests and
numerical failure traces to repair generated Triton kernels until they are
functionally correct, or until a fixed repair budget is exhausted.

Allowed conditions to run in Cluster 2:

- `C`
- `G+C`

Cluster 2 may read Cluster 1 `none` and `G` results for comparison, but it
does not rerun those as Cluster 2 conditions unless a reproducibility run is
explicitly requested.

Cluster 2 evaluation ceiling:

- Level 0 parse/surface;
- Level 1 compile;
- Level 2 functional correctness.

Cluster 2 feedback sources:

- shape mismatches;
- NaN/Inf failures;
- numerical allclose failures with max abs/rel diff summaries.

Cluster 2 must not:

- measure speed;
- benchmark kernels;
- run compiler/profiler repair;
- use profiler traces;
- use RL or model fine-tuning;
- generate non-Triton kernels.

Standard repair budget:

```text
initial attempt: iteration 0
repair attempts: iterations 1..5
max repair attempts: 5
```

### Cluster 3: Compiler/Profiler Repair Loop

Future contract: `.contracts/agentic/cluster3_contract.md` TBD.

Cluster 3 owns the P factor. Its goal is to use Triton compiler/runtime errors
and profiler or benchmark feedback to improve compilability and performance,
and to quantify whether those signals compose with G and C.

Allowed conditions to run in Cluster 3:

- `P`
- `G+P`
- `C+P`
- `G+C+P`

Cluster 3 evaluation ceiling:

- Level 0 parse/surface;
- Level 1 compile;
- Level 2 functional correctness;
- Level 4 performance.

Level 3 memory-safety checks remain optional/deferred. Do not block Cluster 3
on sanitizer work unless a separate safety contract is written.

Cluster 3 feedback sources:

- Triton compiler diagnostics;
- runtime launch errors;
- benchmarked kernel time;
- speedup versus eager PyTorch;
- speedup versus `torch.compile` baseline when available;
- concise performance hints derived from measurements.

Cluster 3 must not:

- fine-tune or RL-train the model;
- use CUTLASS/CuTe/CUDA-source generation;
- report speedups for kernels that fail Level 2;
- report speedups for numerically incorrect kernels.

## Modal Harness Plan

Current state:

- `shared/modal_harness/` exists.
- Remote generation exists.
- Remote compile-only validation exists.
- Cluster 1 Modal runner exists and produced frozen artifacts.
- Schemas currently reject C/P cells, which is correct until Cluster 2/3 land.

The Modal harness should remain shared infrastructure. It should not become
Cluster 2 or Cluster 3 policy code. Cluster-specific orchestration belongs in
`cluster2/` and `cluster3/`.

### M0: Freeze Cluster 1 Harness Behavior

Status: complete for Cluster 1, but keep regression tests.

Checklist:

- keep `RemoteGenerationRequest` accepting only `none` and `G` for Cluster 1;
- keep `RemoteCompileRequest` compile-only;
- keep all Cluster 1 timing/correctness/profiling fields out of remote schemas;
- keep local JSONL as authoritative Cluster 1 output;
- preserve L4 final artifact metadata.

### M1: Add Shared Eval Request Identity

Purpose: make future remote correctness/performance calls traceable without
copying Cluster 1 result schemas.

Small tasks:

1. Add a shared `EvalIdentity` or equivalent Pydantic model under
   `shared/modal_harness/schemas.py`.
2. Include `factor_cell`, `kernel_class`, `kernel_name`, `dtype`, `run_id`,
   `model_id`, `generation_seed`, and `repair_iteration`.
3. Keep source code as a separate field in specific request models.
4. Add tests that C/P requests are still rejected by Cluster 1 adapters.

DoD:

- identity object round-trips through Pydantic;
- no existing Cluster 1 JSONL format changes.

### M2: Add Remote Correctness Evaluation

Purpose: Cluster 2 needs Level 2 checks on GPU workers.

Files to create:

- `shared/eval/levels/level2_correctness.py`
- `shared/modal_harness/correctness.py`
- `shared/modal_harness/correctness_runner.py`
- `cluster2/validation/modal_correctness_check.py`

Small tasks:

1. Define `RemoteCorrectnessRequest`.
2. Define `RemoteCorrectnessResult`.
3. Implement a child-process runner that imports the generated source,
   executes the public launcher, executes the PyTorch reference, and compares
   outputs with `shared.eval.tolerances`.
4. Test ReLU, Softmax, and GEMM known-good fixtures.
5. Test wrong-shape, NaN/Inf, and large-diff failures.
6. Return only structured correctness fields, not performance fields.

DoD:

- one known-good source passes Level 2 for each kernel class;
- one intentionally wrong source fails with a stable failure code;
- no timing or benchmarking data appears in correctness results.

### M3: Add Cluster 2 Repair Orchestration

Purpose: implement C as bounded test-driven feedback.

Files to create:

- `cluster2/feedback/trace.py`
- `cluster2/feedback/prompts.py`
- `cluster2/feedback/repair_loop.py`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/results/dataclass.py`

Small tasks:

1. Define `RepairTrace` ownership for Cluster 2 result logging.
2. Build feedback prompt templates for Level 2 correctness failures.
3. Reuse `generate_source_modal`.
4. Reuse remote compile and remote correctness checks.
5. Stop on first Level 2 pass.
6. Stop after five repair attempts.
7. Write one final result row plus an optional trace artifact per run.

DoD:

- `--condition C --kernel-class elementwise --n 1` completes end to end;
- repair traces show iteration 0 plus any repair attempts;
- failed runs preserve the last failure code and feedback content;
- no performance code is imported by Cluster 2.

### M4: Add Remote Performance Evaluation

Purpose: Cluster 3 needs stable performance metrics for Level 2-passing Triton
kernels.

Files to create:

- `shared/eval/levels/level4_performance.py`
- `shared/modal_harness/performance.py`
- `shared/modal_harness/performance_runner.py`
- `cluster3/profiling/modal_profile.py`

Small tasks:

1. Define `RemotePerformanceRequest`.
2. Define `RemotePerformanceResult`.
3. Require caller-provided proof or re-check that Level 2 passed.
4. Benchmark generated Triton launcher and PyTorch reference in the same worker.
5. Report median, IQR, warmup count, timing count, and speedups.
6. Use local JSONL plus optional per-run artifact files for raw timing samples.

DoD:

- performance request rejects candidates without Level 2 success;
- one known-good fixture returns finite median times;
- speedup fields are null for failed correctness cases;
- no RL training or model update code exists.

### M5: Add Cluster 3 Compiler/Profiler Repair Orchestration

Purpose: implement P as bounded compiler/profiler repair.

Files to create:

- `cluster3/profiling/prompts.py`
- `cluster3/profiling/repair_loop.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/results/dataclass.py`

Small tasks:

1. Reuse Cluster 2 test-driven loop when condition contains C.
2. For P-only, generate, compile, correctness-check, then benchmark.
3. Feed back Triton compiler/runtime diagnostics for non-compiling candidates.
4. Feed back concise performance summaries only after Level 2 pass.
5. Stop after fixed compiler/profiler repair budget.
6. Preserve correctness gating on every repaired candidate.

DoD:

- `--condition P --kernel-class elementwise --n 1` runs without C repair;
- `--condition C+P --kernel-class elementwise --n 1` reuses C then benchmarks;
- no speedup is recorded for any functionally incorrect source.

### M6: Add Batching and Long-Run Controls

Purpose: make full factorial runs reproducible without changing semantics.

Small tasks:

1. Add resumable identities to Cluster 2 and Cluster 3 runners.
2. Keep generation low-parallel and compile/correctness/performance higher
   parallel only after smoke tests pass.
3. Record Modal GPU model and software versions in metadata.
4. Write one row per final sample and one trace artifact per repaired sample.
5. Record `scale_tier`, `kernel_count`, `sample_size`, model, seed schedule,
   condition set, and grammar variant metadata.
6. Add analyzer preflight checks for expected row counts.
7. Reject mixed-scale aggregate reports unless explicitly labeled diagnostic.

DoD:

- interrupted runs can resume without duplicate identities;
- analyzers reject missing or duplicate cells;
- full runs can be staged as smoke, development, then paper scale.

## Eval Suite Plan

Current state:

- `shared/eval/schema.py` exists.
- Level 0 parse/signature helpers exist.
- Level 1 compile adapter exists.
- diversity, pass@k, tolerance, and failure taxonomy helpers exist.
- Cluster 1 adapter to `EvalResult` exists.

Missing before Cluster 2/3:

- `RunConfig`;
- a real gated `run_eval_pipeline`;
- Level 2 correctness;
- Level 4 performance;
- aggregation/reporting modules beyond narrow Cluster 1 summaries;
- factor-interaction analysis over `EvalResult` rows.

### E0: Freeze Eval Levels and Names

Small tasks:

1. Document the active levels in `shared/eval/__init__.py`.
2. Keep Level 3 safety optional/deferred.
3. Rename docs from CUDA-specific wording to GPU/Triton runtime wording where
   the project docs are not quoting external references.
4. Keep `None` as the only representation for unevaluated future-level fields.

DoD:

- eval imports stay light on machines without GPU libraries;
- Cluster 1 tests still prove Level 2-4 fields are null.

### E1: Add RunConfig

Files to create:

- `shared/eval/run_config.py`

Fields:

- `condition`;
- `max_level`;
- `repair_budget`;
- `enable_timing`;
- `warmup_iters`;
- `timing_iters`;
- `dtypes`;
- `sample_size`;
- `grammar_variant` optional.

DoD:

- Cluster 1 can create `RunConfig(max_level=1)`;
- future Cluster 2 can create `RunConfig(max_level=2, repair_budget=5)`;
- future Cluster 3 can create `RunConfig(max_level=4, enable_timing=True)`.

### E2: Add Gated Eval Pipeline

Files to create:

- `shared/eval/pipeline.py`

Small tasks:

1. Run Level 0.
2. Stop if `max_level == 0` or Level 0 fails.
3. Run Level 1.
4. Stop if `max_level == 1` or Level 1 fails.
5. Run Level 2 when implemented.
6. Stop if `max_level == 2` or Level 2 fails.
7. Skip/defer Level 3 unless explicitly enabled later.
8. Run Level 4 only after Level 2 success and `enable_timing=True`.

DoD:

- unit tests verify every gate returns future fields as `None`;
- Cluster 1 adapter output matches pipeline semantics.

### E3: Implement Level 2 Correctness

Files to create:

- `shared/eval/levels/level2_correctness.py`

Small tasks:

1. Add a `CorrectnessResult` dataclass.
2. Use KernelSpec shapes and PyTorch references.
3. Compare shape first.
4. Check NaN/Inf before allclose.
5. Record max abs and max rel diff.
6. Use `shared.eval.tolerances.get_tolerances`.
7. Return stable failure code candidates.

DoD:

- known-good ReLU, Softmax, GEMM generated fixtures pass;
- intentionally wrong outputs fail deterministically;
- no performance measurement occurs.

### E4: Implement Repair Metrics

Files to create:

- `shared/eval/metrics/repair.py`

Small tasks:

1. Compute convergence rate.
2. Compute mean repair iterations among converged samples.
3. Compute pass@1 after repair.
4. Compute token-adjusted repair efficiency when token counts exist.

DoD:

- pure unit tests cover empty, all-fail, and mixed traces.

### E5: Implement Aggregation and Reporting

Files to create:

- `shared/eval/aggregation.py`
- `shared/eval/reporting/tables.py`

Small tasks:

1. Build `CellSummary` from `EvalResult` rows.
2. Aggregate by condition, kernel class, dtype, and grammar variant.
3. Report compile@1, pass@k, unique ratios, failure distributions.
4. Keep speedup metrics null until Level 4 exists.

DoD:

- Cluster 1 final JSONL can be converted into `CellSummary`;
- no Cluster 2/3 fields are required for Cluster 1 summaries.

### E6: Implement Level 4 Performance

Files to create:

- `shared/eval/levels/level4_performance.py`
- `shared/eval/metrics/fast_at_p.py`
- `shared/eval/metrics/speedup.py`

Small tasks:

1. Benchmark only functionally correct kernels.
2. Use fixed warmup and timing iteration counts.
3. Capture median and IQR.
4. Compute speedup versus eager PyTorch.
5. Compute speedup versus `torch.compile` when available.
6. Keep raw samples in optional artifact files, not every JSONL row.

DoD:

- unit tests cover arithmetic on synthetic timings;
- integration smoke returns finite values for one known-good Triton kernel.

### E7: Implement Factorial Analysis

Files to update:

- `shared/analysis/factorial.py`

Small tasks:

1. Consume canonical factor cells rather than inferred booleans only.
2. Support optional `grammar_variant`.
3. Compute main effects and interaction terms for compile, correctness, and
   fast@p separately.
4. Keep partial-analysis mode for incomplete clusters.

DoD:

- analysis can run with only Cluster 1 rows;
- analysis can run with synthetic all-cell rows;
- missing cells are reported, not silently filled.

## Recommended Work Order

Do these in order. Each row should be small enough to land independently.

| Step | Outcome | Primary files |
| --- | --- | --- |
| 1 | Accept this bridge plan and update stale Cluster 2/3 README scope | `.contracts/`, `cluster2/README.md`, `cluster3/README.md` |
| 2 | Add `RunConfig` and eval pipeline skeleton | `shared/eval/run_config.py`, `shared/eval/pipeline.py` |
| 3 | Add Level 2 correctness local helpers | `shared/eval/levels/level2_correctness.py` |
| 4 | Add remote correctness Modal function | `shared/modal_harness/correctness.py` |
| 5 | Add Cluster 2 smoke-scale test-driven loop | `cluster2/feedback/`, `cluster2/experiments/` |
| 6 | Add eval aggregation/reporting for Level 2 | `shared/eval/aggregation.py`, `shared/eval/reporting/tables.py` |
| 7 | Add Level 4 performance helpers | `shared/eval/levels/level4_performance.py` |
| 8 | Add remote performance Modal function | `shared/modal_harness/performance.py` |
| 9 | Add Cluster 3 smoke-scale compiler/profiler loop | `cluster3/profiling/`, `cluster3/experiments/` |
| 10 | Add factorial analysis over all completed cells | `shared/analysis/factorial.py` |

## Do Not Build Yet

These are explicitly out of the next development loop:

- RL/GRPO/TRL training;
- vLLM training workers;
- CUTLASS/CuTe prompt abstractions;
- CUDA/C++ source generation;
- broad KernelBench Level 2-4 expansion;
- TritonBench integration;
- Nsight-driven profiling;
- deployed Modal services;
- detached large batch jobs with `.spawn_map`;
- production dashboarding.

They can be revisited only after Cluster 2 and Cluster 3 contracts exist and
the smoke-scale paths are stable.
