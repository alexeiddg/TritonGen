# TritonGen

**2³ Factorial Experiment: LLM Control Mechanisms for Triton GPU Kernel Generation**

Thesis project investigating whether grammar constraints, compiler feedback, and
performance feedback compose additively or interfere when stacked as LLM control
mechanisms. The experiment is a full 2³ factorial design across three factors.

---

## Research Design

| Factor | Label | Cluster | Mechanism |
|--------|-------|---------|-----------|
| Grammar constraint | G | Cluster 1 | XGrammar CFG-constrained decoding |
| Compiler feedback | C | Cluster 2 | Compiler error → LLM repair loop |
| Performance feedback | P | Cluster 3 | Profiler reward → RL policy |

**Central question:** Do G, C, P compose additively, or do interaction effects
(G×C, G×P, C×P, G×C×P) emerge?

---

## Repository Layout

```
TritonGen/
├── .contracts/                    # Binding design contracts (source of truth)
│   ├── cluster1_contract.md       # Grammar constraint spec (LOCKED)
│   └── cluster1_plan.md           # Phase-by-phase implementation plan
│
├── cluster1/                      # G-factor: Grammar-Constrained Generation
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
├── cluster2/                      # C-factor: Compiler Feedback (NOT STARTED)
│   └── README.md                  # Scope, boundary rules, C1 dependencies
│
├── cluster3/                      # P-factor: RL / Performance Feedback (NOT STARTED)
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
uses the heavier LLM image on L40S GPUs, while compile-only validation uses a
separate Triton image on L4 GPUs. The local process remains light: the Modal
runner and adapters intentionally defer `torch`, `transformers`, `xgrammar`,
and `autoawq` imports until execution inside the remote container.

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

The current active work is Cluster 1 plus the shared Modal GPU infrastructure.
Cluster 1 is the grammar-factor experiment: it compares baseline generation
against grammar-constrained generation while holding the model, prompt,
temperature, token budget, dtype, seed schedule, and kernel task fixed. The
shared Modal harness is the execution substrate for that work. It owns the
single `modal.App` named `tritongen-gpu-harness`, the generation and compile
images, the Hugging Face cache volume, optional Hugging Face secret lookup, and
the request/result schemas used to keep Cluster 1 separate from later compiler
feedback and performance-feedback work.

Modal is not currently training or fine-tuning a model. It is running remote
inference with the AWQ 7B development model and remote compile validation. For
the configured full Cluster 1 run, `--kernel-class all --condition both --n 20`
produces 360 result rows: 3 KernelBench problems × 2 conditions (`none`, `G`) ×
3 dtypes (`fp32`, `fp16`, `bf16`) × 20 seeds. Because each source is
compile-checked across 15 dtype/shape cases for its problem, that full run
attempts up to 5,400 dummy compile launches. Each generated source is sent
through the compile-only gate, which checks the canonical Cluster 1 shapes for
all three dtypes and records compile errors as result fields rather than using
them as feedback.

Cluster 2 and Cluster 3 remain out of the active execution path. Their
factor cells (`C`, `P`, `G+C`, `G+P`, `C+P`, `G+C+P`) are reserved in the
schema vocabulary but rejected by validation until those clusters are built.

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

## Contract compliance

All implementation follows the contract in `.contracts/cluster1_contract.md`.
Any deviation requires an explicit recorded justification in that document.

**Cluster 1 boundary:** compile acceptance is the only correctness gate. Numeric
reference checks, profiling, timing metrics, compiler-feedback prompting, and RL
components belong to later clusters.

The Modal path preserves the same boundary. Remote generation returns source and
grammar diagnostics; remote compile returns pass/fail, per-dtype compile
results, and bounded error text. Compile errors are never fed back into the
prompt in Cluster 1, and no timing, profiler, numerical-correctness, repair, or
reward fields are present in the shared Cluster 1 schemas.

---

## Status

| Cluster | Factor | Status |
|---------|--------|--------|
| Cluster 1 | Grammar (G) | In progress — Modal GPU runner and boundary hardening |
| Shared Modal infra | GPU execution | In progress — remote generation and compile-only validation |
| Cluster 2 | Compiler feedback (C) | Not started |
| Cluster 3 | Performance / RL (P) | Not started |
| Factorial analysis | G×C×P | Not started |

---

## Key references

- XGrammar (2024) — constrained decoding engine
- µCUTLASS (Sun et al., 2025) — context-dep/indep token classification
- LEGO (Tavakkoli et al., 2025) — DSL-mediated layout constraint (cited as future work)
- KernelBench (`ScalingIntelligence/KernelBench`) — evaluation dataset
- HumanEval pass@k (Chen et al., 2021) — unbiased statistical estimator
