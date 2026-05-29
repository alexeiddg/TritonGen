# Modal Cost Optimization Auditability Report

Date: 2026-05-19
Scope: read-only analysis of Modal cost optimization options for TritonGen Cluster 1 and Cluster 2 research artifacts.

## Executive Decision

Do not optimize the existing frozen Cluster 1 n=20 artifacts in place.

The current research line depends on exact artifact bytes, row hashes, source hashes, replay schedules, Modal provenance metadata, and explicit coverage policy. Any change that mutates existing JSONL outputs, sidecars, manifests, generation semantics, compile labels, row order, token budgets, GPU type, image provenance, or replay schedules should be treated as a new artifact lineage, not a cost fix to the current frozen artifacts.

The viable cost work is future-only:

1. Preserve the frozen artifacts as-is.
2. Avoid rerunning or overwriting Cluster 1 n=20 outputs.
3. For future non-frozen runs, tune CPU, memory, and warm-container settings first.
4. Treat generation batching, vLLM, GPU switching, and token-budget changes as new experiment lines requiring separate validation and audit trail.

## Current Cost Context

The billing screenshot is dominated by Cluster 1 Modal generation and compile:

| Modal surface | Cost |
| --- | ---: |
| `shared.modal_harness.generation.RemoteGenerator.*` | `$14.61` |
| `shared.modal_harness.compile.remote_compile_only` | `$7.24` |
| Cluster 1 diagnostic revalidation | `$0.67` |
| Cluster 2 generation/correctness | `$0.04` |

Generation plus compile account for roughly `96.6%` of the visible `$22.61` bill.

Resource-level costs were:

| Resource | Cost |
| --- | ---: |
| L4 | `$13.56` |
| CPU | `$5.14` |
| Memory | `$3.91` |

Using the supplied rates, this implies about `16.97` L4-hours and a CPU/memory footprint consistent with the current requests: generation asks for `8 CPU / 32 GiB`, and compile asks for `4 CPU / 24 GiB`.

## Research State And Auditability Gate

The task-agnostic Cluster 1 n=20 run is already registered as an incomplete frozen artifact, not as an open failed job waiting to be completed.

Current registered state:

| Field | Value |
| --- | --- |
| Artifact id | `g_task_agnostic_aligned_pipeline_n20_l4` |
| Path | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| Intended rows | `180` |
| Observed rows | `177` |
| Coverage complete | `false` |
| Coverage policy | `COVERAGE_WARNING_SKIP_MISSING` |

Missing rows are explicitly recorded:

| Kernel class | Dtype | Sample index |
| --- | --- | ---: |
| `matmul` | `fp32` | `5` |
| `matmul` | `bf16` | `0` |
| `matmul` | `bf16` | `18` |

This matters because Cluster 2 uses frozen Cluster 1 rows as replay controls. The manifest records artifact hashes, metadata sidecar hashes, row hashes, source hashes, seed schedules, model identity, tokenizer identity, prompt hashes, and token budgets. Replay code verifies these hashes before mapping controls and does not generate fallback rows for missing controls.

Therefore, the old operational advice, "resume the failed partial run instead of rerunning with overwrite," is only valid before freezing/registering the artifact. After registration, resuming in place would change the artifact bytes and sidecar hashes, which would invalidate the frozen artifact identity.

## Artifact Rules

Use these rules for cost optimization decisions:

| Rule | Rationale |
| --- | --- |
| Never overwrite frozen Cluster 1 outputs. | Artifact hash and row hashes are part of the audit trail. |
| Never append to a frozen artifact under the same artifact id. | Even adding the three missing rows changes the artifact hash and sidecar hash. |
| Never silently change `max_new_tokens`, GPU type, generation backend, model revision, tokenizer revision, grammar, or compile harness for a comparable artifact. | These fields are part of research semantics or provenance. |
| New runtime optimization means new artifact lineage. | Cost changes can be valid, but they need their own artifact id and analysis label. |
| Missing frozen controls must remain missing unless a new lineage is declared. | Current skip policy is explicit and auditable. |

## Decision Matrix

| Change | Cost Upside | Engineering Work | Blast Radius | Audit Risk | Recommendation |
| --- | ---: | ---: | ---: | ---: | --- |
| Keep frozen artifacts untouched and avoid reruns | High prevention | Low | Low | Low | Do it |
| Resume current n=20 task-agnostic artifact in place | Avoids recomputing 177 rows | Low | Medium | High | Do not do it now |
| Create a new completed n=20 artifact id by resuming/copying into a new lineage | Moderate | Medium | Medium | Medium | Only if paper needs full 180/180 |
| CPU/memory right-sizing for future runs | Medium/high | Low/medium | Low/medium | Medium | Worth testing for future runs |
| Shorter `scaledown_window` for smoke/development | Medium | Low | Low | Low/medium | Worth testing for future runs |
| Compile `.map` or batch-style parallelization | Medium | Medium | Medium | Medium | Future-only, useful if more compile-heavy runs |
| Generation dynamic batching | High theoretical | High | High | High | Not for current research line |
| vLLM / high-performance inference backend | High theoretical | Very high | Very high | Very high | Not worth it for current line |
| Modal Memory Snapshots | Unknown/moderate | Medium/high | Medium | Medium/high | Defer |
| GPU switching to T4 | Low/uncertain | Medium | Medium | High | Avoid |
| Lower token budget | High | Low | Medium | High | Avoid for comparable artifacts |
| Input concurrency | Unclear | Medium/high | Medium/high | Medium/high | Avoid before backend redesign |
| Model weight storage changes | Low unless cache misses | Low/medium | Low | Low/medium | Check logs first |

## Findings By Option

### 1. Preserve Frozen Artifacts

Verdict: worth doing, mandatory for auditability.

This is the highest-value "optimization" because it prevents accidental cost blowups from rerunning n=20 artifacts that are already frozen enough for downstream analysis.

Blast radius: low.

Research impact: positive. It preserves the current paired replay contract and explicit skip policy.

Audit impact: positive. Existing artifact, metadata sidecar, row, and source hashes remain stable.

### 2. Resume The Failed Cluster 1 n=20 Run In Place

Verdict: not viable now.

Before the artifact was registered, this would have been the cheapest operational path. After registration, adding the three missing rows to the same file changes the raw JSONL hash and metadata sidecar hash. Since Cluster 2 replay consumes frozen artifact hashes, the current registered identity would no longer match.

Blast radius: medium. The local code path already supports resume safety checks, but the research contract does not allow mutating the frozen artifact in place.

Research impact: high. The current result is explicitly 177/180 with skip policy. Mutating it would turn a registered incomplete artifact into a different artifact.

Audit impact: high. It breaks the existing manifest hash identity unless every downstream reference is intentionally updated.

Alternative: create a new artifact id, for example a `completed_n20` lineage, and keep the 177/180 artifact intact. That is a new research artifact, not a cost fix.

### 3. CPU And Memory Right-Sizing

Verdict: worth testing for future non-frozen runs.

Modal bills CPU and memory based on whichever is higher: request or actual usage. Current Cluster 1 generation requests `8 CPU / 32 GiB`; compile requests `4 CPU / 24 GiB`. The billing screenshot shows CPU and memory at about 40% of the total visible cost, so right-sizing can be material.

Blast radius: low to medium.

Research impact: medium for new generated rows. In theory, CPU/memory request changes should not change generation semantics, but they change runtime provenance and could affect stability, scheduling, OOM behavior, or timing-sensitive failures.

Audit impact: medium. New rows should record new Modal provenance and should not be mixed into an existing frozen artifact.

Recommendation: test in smoke/development only. If stable, use for future artifact lineages with explicit provenance.

### 4. `scaledown_window` Tuning

Verdict: worth testing for future smoke/development runs.

Current generation containers use `scaledown_window=600`; compile/correctness use `120`. Modal documents that keeping warm containers reduces cold starts but bills idle resources while containers remain warm. Because Cluster 1 is serial `generate -> compile -> write`, one surface can remain warm while the other is doing work.

Blast radius: low.

Research impact: low to medium. It should not change generated text or compile labels directly, but it can change cold-start frequency, failure rate, and runtime provenance.

Audit impact: low for future runs; not acceptable as an in-place change to existing frozen artifacts.

Recommendation: use shorter windows for smoke/development and keep longer windows only for known large paper-scale runs.

### 5. Compile `.map` Or Batch Processing

Verdict: future-only, possibly worthwhile.

Compile validation is one remote call per generated row. Modal batch processing and `.map` can run independent calls in parallel. Existing diagnostics already show a pattern where rows are evaluated as a list in one remote call, so there is a local precedent for grouping evaluation work.

Blast radius: medium.

Research impact: medium. If compile results are returned and written in canonical cell order, labels can remain comparable. However, concurrency changes failure timing, timeout behavior, ordering hazards, and metadata call ids.

Audit impact: medium. Any rows produced through a new compile orchestration should be a new lineage or must be validated against old labels before replacing any analysis.

Recommendation: reasonable only if more compile-heavy future runs are planned. Preserve deterministic ordering and per-row identity if implemented later.

### 6. Generation Dynamic Batching

Verdict: not worth it for current artifacts.

Modal dynamic batching can reduce per-request cost for GPU workloads by sharing loaded weights. However, this code currently has a single-request `generate_one` method and a synchronous caller. Batching would require issuing multiple concurrent in-flight calls and changing the generation method to accept and return lists.

There is also a Modal constraint: a class with a batched method cannot also have other batched methods or regular methods. That likely requires a new class surface or a meaningful refactor.

Blast radius: high.

Research impact: high. Batched generation can change RNG handling, prompt padding, tokenization shape, stop behavior, constrained decoding integration, and failure surfaces.

Audit impact: high. It should be treated as a new generation backend or new artifact lineage.

Recommendation: avoid for the frozen line. Consider only for a future benchmarked throughput branch.

### 7. vLLM / High-Performance Inference

Verdict: not worth it for the current research line.

vLLM or a serving-style backend could improve throughput, especially for unconstrained generation. The current generator uses Hugging Face `model.generate` plus xgrammar/hardware checker constrained decoding for G/G+C paths. That means a vLLM migration is not a drop-in replacement.

Blast radius: very high.

Research impact: very high. It changes the inference engine, batching model, RNG behavior, token streaming, stopping, and constrained decoding implementation.

Audit impact: very high. It is a new experimental backend.

Recommendation: only consider after the current audit-sensitive artifact line is complete.

### 8. Memory Snapshots

Verdict: defer.

Modal Memory Snapshots can reduce cold starts, but GPU snapshots are alpha and the docs warn that they often require code rewrites. They also do not speed up model loading when the bottleneck is reading weights from storage. This workload already uses an HF cache volume, and generation cost appears dominated by long-running work rather than just cold starts.

Blast radius: medium to high.

Research impact: medium. Snapshotting interacts with initialization, randomness, and GPU state.

Audit impact: medium to high. It changes runtime provenance and could introduce subtle state reuse issues.

Recommendation: do not prioritize unless logs show cold-start initialization dominates cost.

### 9. GPU Switching

Verdict: avoid.

L4 is already the cheapest likely-safe modern GPU in the supplied rates. T4 is cheaper, but the code and research assumptions rely on L4 for Cluster 2, and generated Triton/BF16 behavior on T4 is a compatibility risk.

Blast radius: medium.

Research impact: high. GPU architecture can affect compile/runtime behavior and supported dtypes.

Audit impact: high. GPU is part of runtime identity and comparability.

Recommendation: keep L4 for research artifacts.

### 10. Lower Token Budget

Verdict: avoid for comparable artifacts.

Lowering `max_new_tokens` can materially reduce generation cost, but it changes the generation budget and is recorded in the replay schedule. Existing artifacts include different token budgets, and the current task-agnostic n=20 aligned run used `2048`.

Blast radius: low engineering, high research.

Research impact: high. It changes what the model is allowed to produce.

Audit impact: high. Not comparable to existing n=20 artifacts unless analyzed as a separate condition.

Recommendation: only use in smoke/dev or a separately labeled experiment.

### 11. Input Concurrency

Verdict: avoid for now.

The current generation method uses synchronous Transformers generation. Adding input concurrency without true batching can contend on one loaded model and may not improve cost. Compile subprocess concurrency inside one GPU container could similarly create resource contention.

Blast radius: medium to high.

Research impact: medium.

Audit impact: medium.

Recommendation: only revisit after a dedicated backend design.

### 12. Model Weights / Volumes

Verdict: low priority.

The generation image already mounts an HF cache volume. Modal docs recommend model-weight storage for cold-start reduction, but this is likely not the first lever unless Modal logs show repeated cache misses or downloads.

Blast radius: low.

Research impact: low to medium.

Audit impact: low to medium.

Recommendation: inspect logs before changing anything.

## Recommended Path

### Now

1. Keep the current frozen Cluster 1 artifacts unchanged.
2. Do not resume, overwrite, append, or repair the registered task-agnostic n=20 artifact in place.
3. Treat the 177/180 task-agnostic n=20 artifact as the canonical state for its current artifact id.
4. Keep the explicit skip policy visible in analysis/reporting.

### If More Runs Are Needed

1. Create a new artifact id before generating anything.
2. Use smoke runs to test lower CPU/memory requests.
3. Use shorter `scaledown_window` for smoke/development.
4. Preserve deterministic row ordering, seed identity, run config, and provenance.
5. Validate labels against old behavior before using results in paper-facing comparisons.

### Avoid Until A New Research Line Exists

1. vLLM or another inference backend.
2. Dynamic generation batching.
3. GPU switching below L4.
4. Token budget reductions for comparable paper-scale artifacts.
5. In-place completion of frozen partial artifacts.

## Source Pointers

Local code and artifact references:

- `cluster1/experiments/run_cluster1_modal.py`: serial `generate -> compile -> write` runner, resume checks, output metadata.
- `shared/modal_harness/generation.py`: Cluster 1 generation Modal class and resource requests.
- `shared/modal_harness/compile.py`: Cluster 1 compile Modal function and resource requests.
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`: frozen artifact ids, hashes, coverage, skip policy, replay schedule.
- `cluster2/replay/cluster1_controls.py`: frozen artifact hash verification and replay mapping.
- `cluster1/results/dataclass.py`: generation metadata and paper-scale auditability validation.
- `.contracts/agentic/reference/modal_opt.md`: Modal docs excerpts for CPU/memory billing, cold starts, batching, dynamic batching, and memory snapshots.

Modal doc concepts used:

- CPU/memory billing is based on request or actual usage, whichever is higher.
- `scaledown_window`, `min_containers`, and `buffer_containers` trade cold-start latency for cost.
- `.map` and `.spawn_map` support large-scale batch processing.
- `@modal.batched` can batch calls, including class methods, but requires list-shaped inputs/outputs and constrains class method shape.
- Memory snapshots can reduce initialization-heavy cold starts but do not speed up storage-bound model weight loading and GPU snapshots have alpha limitations.
