# TritonGen

**2³ Factorial Experiment: LLM Control Mechanisms for Triton GPU Kernel Generation**

Thesis project investigating whether grammar constraints, test-driven feedback,
and compiler/profiler repair compose additively or interfere when stacked as
inference-time LLM control mechanisms for Triton-only kernel generation. The
experiment keeps model weights fixed and varies only the external inference
scaffolding.

---

## Research Design

| Mechanism | Schema label | Cluster | Scope |
|--------|-------|---------|-----------|
| Grammar constraints | G | Cluster 1 | Task-agnostic G is primary; current template G is a diagnostic/reference upper-bound control |
| Test-driven feedback | C | Cluster 2 | PyTorch reference tests and numerical failure traces -> LLM repair loop |
| Compiler/profiler repair | P | Cluster 3 | Triton compiler errors, runtime traces, and benchmark/profiler feedback -> LLM repair loop |

**Central question:** Do G, C, P compose additively, or do interaction effects
(G*C, G*P, C*P, G*C*P) emerge?

The core experiment generates and evaluates Triton kernels only. It does not
generate raw CUDA/C++, CUTLASS, CuTe, or custom DSL kernels, and it does not
fine-tune or RL-train the model.

## Revised Thesis Claim

Working claim:

> Inference-time control mechanisms for LLM-generated Triton kernels - grammar
> constraints, test-driven feedback, and compiler/profiler repair - make
> non-additive contributions to functional correctness. Task-agnostic grammar
> constraints provide minimal lift over no constraint alone; published
> grammar-constrained decoding successes are substantially attributable to
> task-specific grammar encoding rather than syntactic enforcement.
> Test-driven feedback is expected to dominate as the strongest single
> inference-time mechanism, and combining it with compiler feedback is expected
> to yield the best correctness-per-iteration ratio without model fine-tuning.

Cluster 1's current `180/180` result is therefore a control, not the main
grammar result. It is the template G diagnostic/reference upper bound: a
measurement of what happens when the grammar is allowed to encode the task
family. Task-agnostic G is the primary grammar condition for paper claims,
compared against both no-control baseline and this upper bound.

The publishable contradiction is the distinction between syntactic guidance and
task encoding. If task-aware grammars explain most of the gain, then the
standard grammar-constrained decoding story is incomplete for Triton kernels.

---

## Scale Policy

Run scale is explicit project metadata. The source of truth is
`.contracts/research/scale_policy.md`.

| Tier | Purpose | Typical run | Claim status |
|------|---------|-------------|--------------|
| `smoke` | Verify the path works end to end | 1 kernel, 1 condition, `n=1`, fast development model | Infrastructure pass/fail only |
| `development` | Iterate on prompts, grammars, repair templates, and harness behavior | 3 kernels, active conditions, `n=3..5`, fast development model | Directional indicators only |
| `paper` | Produce reported results | target 6-9 balanced kernels, full factorial where applicable, `n=20`, larger model | Paper evidence |

Development-scale data is preserved for reproducibility but is not paper
evidence. Paper-scale runs must use frozen prompts, grammars, seed schedule,
kernel set, eval gates, and artifact manifests. Future artifact filenames should
include the scale tier, kernel count, sample count, and model alias.

The current strict Cluster 1 grammar is a special control. It remains frozen as
`template_upper_bound` reference on the original three-kernel subset. The larger
paper-scale task-agnostic G condition should use the planned task-agnostic
Triton grammar unless a future contract explicitly adds a new task-aware
upper-bound control.

---

## Repository Layout

```
TritonGen/
├── .contracts/                    # Binding design contracts (source of truth)
│   ├── README.md                  # Research-facing vs agentic-doc boundary
│   ├── research/                  # Paper-safe methodology/design docs
│   │   ├── research_scope.md      # Thesis scope, factors, non-goals
│   │   ├── scale_policy.md        # Smoke/development/paper scale rules
│   │   ├── eval_metrics.md        # Shared eval metric/schema design
│   │   └── cluster1_generated_surface.md
│   │                              # Generated-code surface for Cluster 1
│   └── agentic/                   # Local/internal implementation notes, gitignored
│
├── cluster1/                      # G-factor: Grammar-Constrained Generation
│   ├── README.md                  # Cluster 1 scope and template upper-bound framing
│   ├── grammar/                   # triton_kernel.gbnf + Lark validator
│   ├── constraints/               # Hardware checker (smem, power-of-2)
│   ├── generation/                # XGrammar constrained decoding
│   ├── validation/                # Triton compile gate (dummy JIT launch)
│   ├── data/
│   │   ├── kernels/               # KernelBench: ReLU, Softmax, GEMM specs
│   │   └── prompts/               # Locked prompt contract
│   ├── results/                   # GenerationResult dataclass + JSONL logger
│   ├── experiments/               # run_cluster1.py + analyze_cluster1.py
│   ├── notebooks/                 # cluster1_demo.ipynb
│   └── tests/
│       └── fixtures/
│           ├── valid_kernels/     # Known-good Triton kernels
│           └── invalid_kernels/   # Known-bad rejection fixtures
│
├── cluster2/                      # C-factor: Test-Driven Feedback (NOT STARTED)
│   └── README.md                  # Scope, boundary rules, C1 dependencies
│
├── cluster3/                      # P-factor: Compiler/Profiler Repair (NOT STARTED)
│   └── README.md                  # Scope, boundary rules, C1+C2 dependencies
│
├── shared/                        # Cross-cluster infrastructure
│   ├── stats/pass_at_k.py         # Unbiased HumanEval pass@k estimator
│   ├── models/loader.py           # Shared model/tokenizer loading
│   ├── modal_harness/             # Shared Modal GPU generation/compile infra
│   ├── analysis/factorial.py      # 2³ factorial interaction analysis
│   └── configs/experiment.yaml    # Shared experiment configuration
│
├── outputs/                       # Generated results — gitignored
│   ├── cluster1/
│   ├── cluster2/
│   └── cluster3/
│
├── pyproject.toml                 # Python packaging — pip install -e .
└── requirements.txt               # Pinned dependency list
```

---

## Quickstart — Cluster 1

> **Prerequisites:** Python 3.11+. Local GPU execution is supported for the
> original runner; the active shared-infra path uses Modal GPUs.

Cluster 1 experiments use only the contract package under `cluster1/`.
Do not use older prototype entry points such as root-level `src/`,
`scripts/run_smoke.py`, `grammars/`, `configs/`, or `experiments/*.ipynb` if
they exist in a local checkout; they are not part of the Cluster 1 experimental
code path.

### 1. Install

```bash
pip install -e .
```

### 2. Unit tests (no GPU required)

```bash
pytest cluster1/tests/ -v
```

### 3. Full local experiment run (GPU required)

```bash
python -m cluster1.experiments.run_cluster1 \
  --condition both \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/results.jsonl
```

### 4. Modal experiment run (active shared GPU path)

Cluster 1 is currently being run through the shared Modal harness. Generation
uses the heavier LLM image and can be selected per run with
`--modal-generation-gpu`; compile-only validation uses a separate Triton image
on L4 GPUs. The final frozen Cluster 1 baseline and template-G reference artifacts used
`--modal-generation-gpu L4`. The Modal app UI may still show the generation
class default `L40S`, but the artifact sidecars record the actual per-run GPU
override. The local process remains light: the Modal runner and adapters
intentionally defer `torch`, `transformers`, `xgrammar`, and `autoawq` imports
until execution inside the remote container.

The active test model is `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`. This is the
development model for Cluster 1 because it is small enough to load quickly,
fits the current Modal generation image comfortably, and keeps GPU runtime cost
low while the team is still validating the grammar, KernelBench task wiring,
result schema, and compile harness. The goal at this stage is fast iteration
and reliable infrastructure feedback, not final model-capability reporting. The
larger thesis-scale model listed in `shared/configs/experiment.yaml` remains a
later-run target once the pipeline is stable.

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition both \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --modal-generation-gpu L4 \
  --output outputs/cluster1/modal_results.jsonl
```

### 5. Analyze

```bash
python -m cluster1.experiments.analyze_cluster1 \
  --input outputs/cluster1/results.jsonl \
  --output outputs/cluster1/summary.md
```

---

## Current Pipeline Status

Cluster 1 is frozen. It is the grammar-factor experiment: it compares baseline
generation against grammar-constrained generation while holding the model,
prompt, temperature, token budget, dtype, seed schedule, and kernel task fixed.
The shared Modal harness is the execution substrate for that work. It owns the
single `modal.App` named `tritongen-gpu-harness`, the generation and compile
images, the Hugging Face cache volume, optional Hugging Face secret lookup, and
the request/result schemas used to keep Cluster 1 separate from later compiler
test-driven feedback and compiler/profiler repair work.

Modal is not currently training or fine-tuning a model. It is running remote
inference with the AWQ 7B development model and remote compile validation. For
the configured full Cluster 1 run, `--kernel-class all --condition both --n 20`
produces 360 result rows: 3 KernelBench problems × 2 conditions (`none`, `G`
with `template_upper_bound` reference) × 3 dtypes (`fp32`, `fp16`, `bf16`) × 20 seeds. Because each source is
compile-checked across 15 dtype/shape cases for its problem, that full run
attempts up to 5,400 dummy compile launches. Each generated source is sent
through the compile-only gate, which checks the canonical Cluster 1 shapes for
all three dtypes and records compile errors as result fields rather than using
them as feedback.

Cluster 2 and Cluster 3 remain out of the active execution path. Their
factor cells (`C`, `P`, `G+C`, `G+P`, `C+P`, `G+C+P`) are reserved in the
schema vocabulary but rejected by validation until those clusters are built.

Frozen Cluster 1 result: the final controlled L4 compile-only comparison uses
`outputs/cluster1/baseline_repaired_l4_n20.jsonl` and
`outputs/cluster1/final_g_l4_n20.jsonl`, combined as
`outputs/cluster1/final_none_vs_g_l4_n20.jsonl`. The final headline is baseline
0/180 compile successes versus template G reference 180/180 compile successes.
Under template G reference, ReLU, Softmax, and GEMM each reached 60/60 compile
acceptance. This remains a
compile-acceptance result only: it makes no numerical-correctness,
performance/speedup, memory-safety, or universal Triton grammar claim. Baseline
failures remain `SignatureError` under unconstrained generation.

Frozen artifact integrity: baseline has 180 rows, template G reference has 180 rows, and the
combined comparison has 360 rows, with `n=20` per condition/kernel-family/dtype
cell. The JSONL artifacts validate, the combined analyzer passes, both final
sidecars report zero infrastructure failures, and both sidecars confirm
`modal_generation_gpu == "L4"`. These artifacts are the frozen three-kernel
template-control subset. They are not the final paper-scale factorial run.

Cluster 1 demonstrates that, for a scoped three-family Triton subset, template G reference
decoding eliminates the dominant structural failure mode of the
unconstrained baseline. Under the repaired canonical function-launcher contract,
the unconstrained condition achieved 0/180 compile acceptance, while the
template G reference condition achieved 180/180. These results support grammar
constraints as a structural validity control, while leaving numerical correctness
and performance to later clusters.

Paper-safe Cluster 1 reference claim: on the scoped ReLU/Softmax/GEMM
KernelBench subset, template G reference decoding improved compile acceptance
from 0/180 to 180/180 under a controlled compile-only evaluation.

Claim boundary: these results are not evidence of numerical correctness,
speedup, memory safety, general KernelBench performance, high-quality Triton
generation in the broad sense, or full G/C/P interaction effects. The grammar is
family-scoped and highly restrictive, so the result should be framed as
structured compile acceptance, not general Triton generation. The high
masked-token rates support that caveat.

Cluster 1 does not need to be reopened unless the study later decides to expand
the problem set, test another model, change the grammar/prompt/validator again,
or change the metric beyond compile acceptance.

---

## KernelBench Usage

KernelBench is used as the source of the Cluster 1 kernel tasks, not as a
training corpus. The active dataset identifier is
`ScalingIntelligence/KernelBench`, split `train`, level `1`. Cluster 1
implements three locked KernelBench-backed specs and stores their reference
code, function signatures, prompt metadata, dtype coverage, and compile shapes
under `cluster1.data.kernels`.

The active KernelBench subset is intentionally three problems, one per kernel
class that Cluster 1 needs to stress. This is not the full KernelBench dataset
and it is not a claim that KernelBench only has three problems. The subset is a
controlled representative slice for the grammar-factor study: one elementwise
kernel, one reduction kernel, and one matrix multiplication kernel. Those
classes exercise different Triton syntax and hardware constraints while keeping
the first experiment small enough to debug the grammar, result schema, and
Modal execution path before expanding the benchmark surface.

| Cluster 1 class | KernelBench task | Problem ID | Why it is included |
|-----------------|------------------|------------|--------------------|
| `elementwise` | ReLU | Level 1, Problem 19 | Covers simple pointwise indexing, masks, and block-size constraints. |
| `reduction` | Softmax | Level 1, Problem 23 | Covers row-wise reductions, numerically sensitive code structure, and reduction-oriented Triton ops. |
| `matmul` | Square GEMM | Level 1, Problem 1 | Covers tiled matrix multiplication, `tl.dot`, multi-axis grids, and shared-memory/tile constraints. |

Each of the three specs defines five shapes per dtype for `fp32`, `fp16`, and
`bf16`, so the compile gate has 15 dtype/shape cases per KernelBench problem.
The shape sets deliberately include smaller-than-block, non-power-of-two,
non-divisible, regular power-of-two, and large cases. That gives Cluster 1
enough coverage to detect trivial, brittle, or over-specialized generated
kernels without crossing into numerical correctness checks or profiling, which
belong to later clusters.

Compile-passing Cluster 1 outputs can be exported into KernelBench's `runs/`
directory layout by `cluster1.experiments.kernelbench_adapter`, but the adapter
only writes generated source files. It does not invoke KernelBench timing,
baseline timing, or `eval_from_generations.py` because those would cross the
Cluster 1 boundary.

---

## Contract Compliance

Research-facing methodology is documented in
`.contracts/research/research_scope.md`,
`.contracts/research/scale_policy.md`, and
`.contracts/research/cluster1_generated_surface.md`. Internal agent execution
notes may exist under `.contracts/agentic/`, but they are not paper-facing
methodology and are ignored by default.

**Cluster 1 boundary:** compile acceptance is the only correctness gate. Numeric
reference checks, test-driven repair, compiler/profiler repair, timing metrics,
and speedup reporting belong to later clusters.

The Modal path preserves the same boundary. Remote generation returns source and
grammar diagnostics; remote compile returns pass/fail, per-dtype compile
results, and bounded error text. Compile errors are never fed back into the
prompt in Cluster 1, and no timing, profiler, numerical-correctness, repair, or
performance-score fields are present in the shared Cluster 1 schemas.

---

## Status

| Cluster | Factor | Status |
|---------|--------|--------|
| Cluster 1 | Grammar (G) | Frozen - final L4 compile-only comparison is baseline 0/180 vs template G reference 180/180 |
| Shared Modal infra | GPU execution | Stable for Cluster 1 freeze - remote generation and compile-only validation |
| Cluster 2 | Test-driven feedback (C) | Not started - contract TBD |
| Cluster 3 | Compiler/profiler repair (P) | Not started - contract TBD |
| Factorial analysis | G*C*P | Not started |

---

## Key references

- XGrammar (2024) — constrained decoding engine
- µCUTLASS (Sun et al., 2025) — context-dep/indep token classification
- LEGO (Tavakkoli et al., 2025) — DSL-mediated layout constraint (cited as future work)
- KernelBench (`ScalingIntelligence/KernelBench`) — evaluation dataset
- HumanEval pass@k (Chen et al., 2021) — unbiased statistical estimator
