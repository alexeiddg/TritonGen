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
│   ├── analysis/factorial.py      # 2³ factorial interaction analysis
│   └── configs/experiment.yaml    # Shared experiment configuration
│
├── outputs/                       # Generated results — gitignored
│   ├── cluster1/
│   ├── cluster2/
│   └── cluster3/
│
├── _legacy/                       # Phase 1 prototypes — DO NOT USE for experiments
│   ├── src/                       # Old constrained_generator, compile_gate, etc.
│   ├── scripts/                   # Old run_smoke.py
│   ├── grammars/                  # Old permissive GBNF grammar
│   ├── configs/                   # Old YAML config
│   ├── experiments/               # Old baseline notebooks
│   └── tests/                     # Old test suite (fixtures now in cluster1/tests/)
│
├── pyproject.toml                 # Python packaging — pip install -e .
└── requirements.txt               # Pinned dependency list
```

---

## Quickstart — Cluster 1

> **Prerequisites:** Python 3.11+, CUDA GPU (for compile gate and generation).

### 1. Install

```bash
pip install -e .
```

### 2. Unit tests (no GPU required)

```bash
pytest cluster1/tests/ -v
```

### 3. Full experiment run (GPU required)

```bash
python -m cluster1.experiments.run_cluster1 \
  --condition both \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/results.jsonl
```

### 4. Analyze

```bash
python -m cluster1.experiments.analyze_cluster1 \
  --input outputs/cluster1/results.jsonl \
  --output outputs/cluster1/summary.md
```

---

## Contract compliance

All implementation follows the contract in `.contracts/cluster1_contract.md`.
Any deviation requires an explicit recorded justification in that document.

**Cluster 1 boundary:** No `torch.allclose`, profiler calls, timing measurements,
repair loops, or RL components. Those belong to Clusters 2 and 3.

---

## Status

| Cluster | Factor | Status |
|---------|--------|--------|
| Cluster 1 | Grammar (G) | In progress — Phase 1–2 |
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
