# Modal Full-Factorial Runtime Optimization Plan

created_at: 2026-06-06
status: `DRAFT_NOT_APPROVED`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
CREDENTIAL_USE_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

This document is a planning and research artifact only. It does not authorize a
Modal run, benchmark, generation call, billing query, output mutation, MLflow
runtime write, or dependency change.

All Modal API, GPU availability, autoscaling, batching, timeout, billing, and
pricing statements in this draft are planning notes, not current authority. Any
signed execution, benchmark, billing, or spend packet must re-verify the
relevant official Modal documentation and pricing on the packet approval date
and record the checked sources before execution.

## Objective

Plan how to reduce wall time and control cost for future full-factorial Modal
runs, especially the planned 12-cell `grammar_mode x C x P` Cluster 3 design.
The target problem is a run that may take several hours if launched through the
current serial runner path.

The recommended optimization order is:

1. add accurate cardinality, duration, and cost estimates before execution;
2. shard independent cells/seeds into separate outputs and merge
   deterministically;
3. raise horizontal L4 generation fanout under explicit spend limits;
4. test larger GPUs only with a signed A/B microbenchmark and breakeven rule;
5. defer dynamic batching, input concurrency, and vLLM until a new generation
   backend lineage is intentionally declared.

## Current Local Baseline

The active launch packet is still a draft and explicitly blocks Modal, GPU,
generation, performance, billing, and output mutation. It selects a future
12-cell `grammar_mode x C x P` design but requires a later signed approval
packet before L1a, L1b, or L2 execution.

The Cluster 3 runner is local orchestration over existing Cluster 2 Modal
surfaces. `cluster3/experiments/run_cluster3_modal.py` states that it is an
ordinary argparse runner and does not define a Cluster 3 Modal app, image,
queue, endpoint, or async job wrapper. The runner imports existing C2 Modal
generation/correctness adapters and registers a Modal local entrypoint only when
Modal imports are present.

Current resource locks:

| Surface | Code path | GPU | CPU | Memory | Timeout | Autoscaling |
|---|---|---:|---:|---:|---:|---|
| C2/Cluster 3 generation | `cluster2/modal/generation.py::RemoteC2Generator` | `L4` | `8.0` | `32768 MiB` | `900s` | `max_containers=2`, `min_containers=0`, `scaledown_window=600` |
| C2/Cluster 3 correctness | `cluster2/modal/correctness.py::remote_c2_correctness` | `L4` | `4.0` | `24576 MiB` | `900s`; subprocess `600s` | `max_containers=20`, `min_containers=0`, `scaledown_window=120` |
| Cluster 3 local runner | `cluster3/experiments/run_cluster3_modal.py` | validates against C2 `L4` defaults | inherited | inherited | per remote call | row-major local loop |

The current runner loops serially over condition, kernel class, dtype, and
seed. Each logical row performs initial generation, initial correctness, then
optional P and C repair loops. The repair attempts are dependent inside a row,
so they should remain serial unless the repair algorithm is redesigned. The
independent units are cells, kernel/dtype strata, and seed ranges.

Scale implications:

| Scope | Logical rows before repair attempts |
|---|---:|
| L1a 12-cell smoke, one kernel class, one dtype, `n=1` | 12 |
| L1b 12-cell development, one kernel class, one dtype, `n=5` | 60 |
| L2 12-cell candidate, one kernel class, one dtype, `n=20` | 240 |
| L2 12-cell candidate, 3 kernel classes, 3 dtypes, `n=20` | 2160 |

Those are logical terminal rows. Actual generation/correctness calls can be
higher because P and C repair budgets default to 5, giving up to 6 attempts in
the worst case for an activated repair loop.

## Modal API Findings

Official Modal references checked for this plan:

| Area | Modal API or guide fact | Planning implication |
|---|---|---|
| GPU selection | Modal supports `T4`, `L4`, `A10`, `L40S`, `A100`, `A100-40GB`, `A100-80GB`, `RTX-PRO-6000`, `H100`/`H100!`, `H200`, and `B200`/`B200+` via `gpu=`. Multi-GPU can be requested with strings like `H100:8`. | Larger GPUs are possible in Modal, but current C2/Cluster 3 code rejects anything except `L4`. GPU changes require a new code/config lane and new artifact lineage. |
| GPU choice | Modal recommends starting neural-network inference on `L40S` as a cost/performance tradeoff, but also warns that small-batch model inference can be memory-bound rather than arithmetic-bound. | `L40S` is the first larger-GPU candidate. `H100`/`H200`/`B200` should not be assumed cheaper unless measured on this exact workload. |
| Autoscaling | `max_containers`, `min_containers`, `buffer_containers`, and `scaledown_window` control function/class pools and trade cost for lower queue/cold-start latency. | Use `max_containers` for bounded fanout. Avoid `min_containers` until a signed run needs a warm pool. Tune `scaledown_window` per run tier. |
| Dynamic config | `Function.with_options()` can override GPU/CPU/memory/autoscaling at a call site, and each distinct configuration has its own autoscaling pool. Dynamic `Cls` configuration is supported. | Coarse configuration buckets are safer than many per-input variants. Repo code still needs validation/provenance if dynamic options are used. |
| Batch processing | `.map` gathers parallel results; `.spawn_map` submits background jobs, especially with `modal run --detach`. | Good fit for independent shard workers if each shard writes external durable output. Not safe for multiple writers to the same JSONL. |
| Input concurrency | `@modal.concurrent(max_inputs=..., target_inputs=...)` lets one container process multiple inputs concurrently. Modal says it fits IO-bound work, remote function calls, and inference servers with continuous batching; synchronous functions must be thread-safe. | Not first-line for current HF `model.generate` path. It may help a remote orchestrator that mainly calls other Modal functions, but generation containers need batching support to benefit. |
| Dynamic batching | `@modal.batched(max_batch_size=..., wait_ms=...)` requires list-shaped inputs/outputs. For classes, a class with a batched method cannot also have other batched or regular methods. | High-risk for current `RemoteC2Generator.generate_one`; it likely needs a separate batched class and RNG/grammar equivalence tests. |
| Timeouts | Modal functions default to 300s but can specify 1s to 24h. `startup_timeout` can separately cover container/model initialization. | The 7-hour concern is likely aggregate orchestration time, not one remote call. If a new remote shard worker is introduced, give it an explicit bounded timeout. |
| Billing reports | `modal.billing.workspace_billing_report` and `modal billing report` provide post-hoc tabular usage reports. Start is inclusive, end is exclusive, reports are full intervals, data can lag, and tags can be included. | Actual billing collection remains post-hoc and approval-gated. Tag future apps/runs before execution where possible. |

Local installed Modal package observed in the repo virtualenv: `1.4.2`.

## Cost Model

Modal pricing checked on 2026-06-06:

| Resource | Rate |
|---|---:|
| CPU | `$0.0000131 / core / sec` |
| Memory | `$0.00000222 / GiB / sec` |
| L4 | `$0.000222 / sec` |
| A10 | `$0.000306 / sec` |
| L40S | `$0.000542 / sec` |
| A100 40 GB | `$0.000583 / sec` |
| A100 80 GB | `$0.000694 / sec` |
| H100 | `$0.001097 / sec` |
| H200 | `$0.001261 / sec` |
| B200 | `$0.001736 / sec` |

For the current generation container shape, `8 CPU + 32 GiB` adds about
`$0.633/hour` before GPU. Approximate generation-container costs:

| GPU | Total $/hour with current 8 CPU / 32 GiB | Breakeven speedup vs L4 | 7h L4-equivalent breakeven wall time |
|---|---:|---:|---:|
| L4 | `$1.43` | `1.00x` | `7.00h` |
| A10 | `$1.73` | `1.21x` | `5.78h` |
| L40S | `$2.58` | `1.80x` | `3.88h` |
| A100 40 GB | `$2.73` | `1.91x` | `3.67h` |
| A100 80 GB | `$3.13` | `2.19x` | `3.20h` |
| H100 | `$4.58` | `3.20x` | `2.19h` |
| H200 | `$5.17` | `3.61x` | `1.94h` |
| B200 | `$6.88` | `4.81x` | `1.46h` |

Decision rule: do not choose a bigger GPU unless a representative smoke/dev
benchmark beats the breakeven speedup and preserves row semantics. For example,
if a workload takes 7 hours on L4, L40S must finish below about 3h53m to lower
generation compute cost. H100 must finish below about 2h11m. If the goal is
wall-clock latency rather than cost, require a signed spend cap and label the
run as a latency-optimized lineage.

Parallel L4 fanout is often the cleaner first lever. If all containers stay
busy, using four L4 containers for one quarter of the wall time consumes roughly
the same GPU-seconds as one L4 container for the full wall time, plus extra cold
start and idle-window overhead. The current code cannot realize that benefit
until the launcher submits independent work concurrently and generation
`max_containers` is raised above 2.

## Recommended Optimization Ladder

### O0: Preflight Estimator

Add or require a local estimator before any signed execution packet:

- count target cells, kernel classes, dtypes, seeds, and max repair attempts;
- estimate worst-case generation calls and correctness calls;
- load prior observability sidecars when available and compute p50/p95 per
  stage;
- output a spend envelope using current pricing constants captured in the
  approval packet;
- fail closed if the estimated spend or wall time exceeds the packet limit.

This can run locally and does not require Modal credentials.

Acceptance gate:

- estimator output is committed or attached to the approval packet;
- estimates distinguish logical rows from repair attempts;
- no network pricing fetch is performed during local tests.

### O1: Sharded 12-Cell Launcher

Make horizontal fanout the first execution optimization.

Shard by independent units:

```text
grammar_mode/cell -> kernel_class -> dtype -> seed_range
```

Each shard must write a separate JSONL and sidecar path. Do not allow concurrent
writers to append to the same result file. Merge only after all shard files
validate.

Recommended shard sizes:

| Tier | Shard shape |
|---|---|
| L1a | one file per 12-cell condition, `n=1` |
| L1b | one file per cell x dtype or cell x seed range |
| L2 | one file per cell x kernel x dtype x seed chunk, for example chunks of 2-5 seeds |

Merge rules:

- validate schema and content-hash sidecar for each shard;
- sort by preregistered cell order, kernel class order, dtype order, and seed;
- write a new merged artifact path, never mutate shard outputs in place;
- preserve a manifest with shard path, hash, row count, run id, Modal resource
  config, and timing summary.

Why this comes first:

- it keeps row semantics and RNG policy intact;
- it avoids changing HF generation internals;
- failed shards can resume independently;
- it gives a natural stop/resume boundary if spend or time limits are hit.

### O2: Bounded L4 Generation Fanout

Current generation allows at most 2 C2 model containers. A full factorial
launcher should declare an explicit generation fanout, probably still on L4 at
first:

| Gate | Suggested generation max containers | Rationale |
|---|---:|---|
| L1a smoke | 1-2 | prove paths and labels before parallel cost |
| L1b development | 2-4 | expose queue/cold-start behavior without large spend |
| L2 candidate | 4-8 only after L1b timing evidence | lower wall time while staying inside common GPU concurrency limits |

The implementation should not be a casual constant edit. It should add an
approved run-config field and record it in sidecars/provenance. Keep
`min_containers=0` by default. Use `buffer_containers` only if L1b shows queue
delay dominates wall time and the spend cap allows idle warm containers.

### O3: Autoscaling And Warm-Container Tuning

Current generation `scaledown_window=600` can keep expensive model containers
warm for up to 10 minutes; correctness uses `120`. For a sharded paper run,
longer warm windows can reduce cold starts but can also bill idle GPU time while
other shards or local work are active.

Recommended policy:

| Run tier | `scaledown_window` policy |
|---|---|
| L1a | short, e.g. 120-300s |
| L1b | compare 120s vs 600s only if the same approved tiny scope is run twice |
| L2 | choose from L1b data; keep longer only if cold starts materially dominate |

Do not set `min_containers>0` for unattended long runs unless the approval
packet contains a clear idle-cost cap. Warm idle GPU containers are billable.

### O4: Bigger-GPU A/B Microbenchmark

A larger GPU is a benchmark question. It should be a separate diagnostic run,
not folded into the first full factorial evidence run.

Candidate order:

1. L4 baseline;
2. L40S, because Modal recommends it for neural-network inference
   cost/performance and it has 48 GB memory;
3. A10 only if availability or pricing suggests it could beat L4;
4. A100/H100/H200 only if L40S fails wall-time targets and the signed spend cap
   permits the breakeven risk.

Benchmark design:

- same model revision, tokenizer revision, prompts, grammar modes, token budget,
  temperature, seed schedule, repair policy, and image pin;
- representative cells: one `grammar_off`, one `task_agnostic`, one P-active,
  one C-active if possible;
- record p50/p95 generation seconds, correctness seconds, cold-start seconds,
  generated token count if already available, terminal failure-code mix, and
  cost estimate;
- compare semantic outputs only for diagnostics; do not promote benchmark rows
  into report artifacts.

Promotion rule:

```text
larger_gpu_is_allowed_for_next_gate =
    measured_speedup >= breakeven_speedup
    and no schema/provenance drift
    and no failure-code regression
    and signed packet names GPU, max_containers, output namespace, and spend cap
```

### O5: Dynamic Batching

Dynamic batching is not a first-line optimization for the current code.

Reasons:

- current C2 generation is a `generate_one` method with dict input/output;
- Modal `@batched` requires list-shaped inputs and outputs;
- a class with a batched method cannot also expose other regular methods;
- constrained decoding, grammar validation, RNG seeding, and hardware-checker
  behavior must be proven equivalent under batches;
- generated outputs would come from a new generation backend lineage.

If pursued later, implement a separate `RemoteC2BatchedGenerator` rather than
mutating the existing `RemoteC2Generator`. Keep batch sizes tiny at first, such
as 2, then 4 only after GPU memory and output equivalence are measured.

### O6: Input Concurrency

Input concurrency is useful when one container can process multiple inputs at
once without fighting itself. The current synchronous HF generation method is
not obviously thread-safe or throughput-friendly under concurrent calls.

Possible future use:

- a remote orchestrator function that mostly waits on C2 generation/correctness
  calls;
- a vLLM or server-style backend that supports continuous batching.

Do not apply `@modal.concurrent` directly to the current generation class
without thread-safety, GPU memory, logging, and cancellation tests.

### O7: vLLM Or High-Performance Inference Backend

vLLM/continuous batching may eventually be the highest-throughput route, but it
is a new research backend here. The current generator uses Transformers
`model.generate`, XGrammar/constrained decoding, a hardware checker, grammar
metadata, and row-level provenance. A vLLM route would need separate evidence
for grammar support, seed semantics, stop reasons, token counts, and failure
classification.

Recommendation: defer until after the L4 sharded launcher and larger-GPU
benchmark clarify whether the current backend is truly the blocker.

## Implementation Backlog

| Priority | Package | Change | Scope |
|---|---|---|---|
| P0 | estimator | Add local full-factorial cardinality/runtime/cost estimator | local-only, no Modal |
| P0 | launcher | Add dry-run shard manifest for 12-cell L1a/L1b/L2 paths | local-only, no Modal |
| P1 | launcher | Add shard executor that writes one result file per shard | execution-gated |
| P1 | merge | Add deterministic shard merge and validation command | local after execution |
| P1 | Modal config | Add explicit generation `max_containers`/`scaledown_window` run config with validation and provenance | execution-gated |
| P2 | observability | Require per-stage timing summaries for shard runs | execution-gated writes |
| P2 | billing | Ensure app/run tags are available before future billing reconciliation | billing query still approval-gated |
| P3 | GPU benchmark | Add signed microbenchmark packet and non-reporting output namespace | execution-gated |
| P4 | batching | Prototype separate batched generation class | new lineage only |
| P5 | vLLM | Prototype separate continuous-batching backend | new research line |

## Required Approval Packet Fields

Any future executable packet should include:

- exact git commit and branch;
- exact command(s);
- Modal profile/workspace policy;
- `experiment_id`, `run_id`, and app tags if supported;
- output root, shard root, observability root, and merge output path;
- path collision policy;
- cell selector, kernel classes, dtypes, seed ranges, and `n`;
- model id, model revision, tokenizer revision, grammar mode/variant/path/hash;
- P and C repair budgets;
- generation GPU, correctness GPU, CPU, memory, `max_containers`,
  `scaledown_window`, timeout, and any dynamic Modal options;
- estimated logical row count, max generation calls, max correctness calls, wall
  time envelope, and spend envelope;
- stop conditions for timeout, failure rate, spend cap, rate limits, or missing
  sidecars;
- billing collection disposition: no billing, delayed manual billing, or
  approved post-hoc billing query window.

## Stop Conditions

Stop the run and do not auto-rerun if any of these occur:

- output path already exists when the packet requires fresh output;
- shard sidecar hash incompatibility;
- row schema validation failure;
- model/tokenizer/grammar provenance mismatch;
- unexpected GPU type or Modal resource config;
- generation or correctness timeout rate exceeds packet threshold;
- Modal rate limit or billing collection rate limit;
- estimated or observed spend exceeds packet cap;
- observed wall time suggests the run cannot finish inside the packet limit;
- any raw billing report, credential, or private billing data would be written
  into the repository.

## Source Pointers

Local code and docs:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster2/modal/generation.py`
- `cluster2/modal/correctness.py`
- `cluster2/constants.py`
- `shared/modal_harness/app.py`
- `shared/observability/billing_modal_collection.py`
- `docs/16_observability_sidecar_implementation_spec.md`
- `.contracts/agentic/modal_cost_optimization_auditability_report.md`

Official Modal references:

- GPU guide: https://modal.com/docs/guide/gpu
- Scaling guide: https://modal.com/docs/guide/scale
- Batch processing guide: https://modal.com/docs/guide/batch-processing
- Input concurrency guide: https://modal.com/docs/guide/concurrent-inputs
- Dynamic batching guide: https://modal.com/docs/guide/dynamic-batching
- Dynamic function configuration guide: https://modal.com/docs/guide/dynamic-function-config
- Timeout guide: https://frontend.modal.com/docs/guide/timeouts
- Function API reference: https://modal.com/docs/reference/modal.Function
- App API reference: https://modal.com/docs/reference/modal.App
- Billing guide: https://modal.com/docs/guide/billing
- Billing API reference: https://modal.com/docs/reference/modal.billing
- Billing CLI reference: https://modal.com/docs/reference/cli/billing
- Pricing: https://modal.com/pricing
