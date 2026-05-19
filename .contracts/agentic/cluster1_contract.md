# CLUSTER 1 — DESIGN CONTRACT
## Grammar-Constrained Triton Kernel Generation
**Frontier-Grade Direct Triton Approach | v1.0 | May 2026**

> **PURPOSE:** This document is a binding technical contract for Cluster 1. It locks WHY each decision was made, WHAT must be built, and HOW it must work. Any code agent, collaborator, or future-you working on this cluster must treat this document as the single source of truth. Deviations require an explicit recorded justification.

> ⛔ **SCOPE LOCK:** Cluster 1 covers constrained decoding + grammar only. It does NOT include numerical correctness checks, compiler feedback loops, profiler integration, repair loops, or any RL component. Any such addition is a Cluster 2/3 concern and constitutes a boundary violation.

> **GRAMMAR v1 SCOPE:** The current Cluster 1 grammar is family-constrained for
> the selected ReLU, Softmax, and GEMM evaluation kernels. It is not a universal
> Triton grammar; broader KernelBench coverage requires explicit future
> generalization.

> **TASK-AGNOSTIC API COVERAGE CONTRACT:** The task-agnostic grammar's
> `triton.language` allow-list must remain auditable through
> `cluster1/grammar/corpus/api_coverage_report.md`. Any grammar modification
> that changes accepted `tl.*` names, arities, kwargs, or encoded value
> restrictions must update, in the same commit:
> `cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json`
> if the reference version/source changes,
> `cluster1/grammar/corpus/grammar_allowlist_extracted.json`,
> `cluster1/grammar/corpus/api_coverage_report.md`, and
> `cluster1/tests/test_api_coverage.py` expectations if the pinned snapshot
> SHA-256 or classification policy changes.
> The grammar allow-list extractor must derive accepted `tl.*` kwargs/arities
> from the GBNF alternatives rather than from a hand-maintained Triton signature
> table.
> The pasted Triton corpus at
> `.contracts/agentic/reference/triton_corpus.md` is the first offline gate for
> `tl.*` API coverage; CI must fail if its public function or parameter surface
> drifts from the pinned reference snapshot.
> Triton `main` is only the upstream source label. Reviewer-facing claims must
> cite the pinned local JSON snapshot by path, extraction timestamp, and SHA-256:
> `a7a637be7f80d59a0764838a6d21a945e7d17e85f1781992fa5089c67b6a1b80`.

> **EVALUATION ALIGNMENT ADDENDUM:** Cluster 1 evaluation delegates shared
> semantics to `shared/eval/`. Compile validation owns the explicit ordering:
> shared Level 0 AST parse and launcher-signature validation first, then Level 1
> runtime import, secondary `inspect.signature` validation that compares ordered
> launcher parameter names only and ignores type/return annotations, and dummy
> Triton launches. `KernelSpec.shapes_by_dtype` is derived from
> `shared.eval.correctness_shapes.get_compile_shapes()`. New Cluster 1 rows
> carry canonical `failure_code` in addition to legacy `compile_error_type`;
> legacy labels remain secondary diagnostics only. Grammar instrumentation fields
> (`gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`,
> stop/provenance fields, and Modal image provenance) are part of the analysis
> surface and feed the shared grammar failure taxonomy.

---

## Table of Contents

1. [WHY — Research Rationale & Design Decisions](#1-why)
2. [WHAT — Complete Deliverable Specification](#2-what)
3. [HOW — Implementation Guide & Gotchas](#3-how)
4. [Definition of Done — Full Checklist](#4-definition-of-done)
5. [Out of Scope — Do Not Build These](#5-out-of-scope)
6. [Agent Work Breakdown — Parallelizable Tasks](#6-agent-work-breakdown)
7. [Key References](#7-key-references)

---

## 1. WHY

### 1.1 Thesis Position

This project runs a 2³ factorial experiment across three LLM control mechanism clusters for Triton GPU kernel generation. The central research question is: **when control mechanisms are stacked, do they compose additively or interfere?**

Cluster 1 is the **G-factor (Grammar)**. It must be the strongest available direct-Triton grammar constraint implementation so that any weakness in the combined-condition results cannot be attributed to a weak baseline. A weak Cluster 1 invalidates the interaction-effect finding.

### 1.2 Why Grammar Constraint at All?

| Problem Without Constraint | What Grammar Constraint Fixes |
|---|---|
| Model generates hallucinated Triton APIs (`tl.load2`, `tl.storev`, etc.) | Grammar whitelist ensures only valid Triton ops appear in output |
| Tile sizes like `BLOCK_M=37` pass syntax check but fail at runtime | Hybrid hardware checker enforces power-of-two and smem limits at generation time |
| Pass@1 rates low due to trivially fixable syntax errors | Literature reports +40–60% pass@1 improvement with grammar constraints |
| Unconstrained generation explores a search space of ~10⁵ token sequences | Grammar reduces this by ~10³, making generation tractable |

### 1.3 Why Pragmatic Frontier (Not DSL/IR)?

The literature frontier uses DSL-mediated approaches: µCUTLASS applies a 170-line EBNF over a specialized DSL, and LEGO constrains layout expressions rather than kernel bodies. These are stronger theoretical bounds but introduce a critical confound for this thesis.

> **KEY DESIGN DECISION:** A DSL layer is itself a control mechanism independent of constrained decoding. If we constrain a DSL instead of raw Triton, we cannot isolate the effect of grammar constraint from the effect of the DSL abstraction. To preserve experimental validity, we apply grammar constraint directly to Triton Python syntax — the pragmatic frontier — and cite DSL approaches as future work.

This is not a limitation. It is a methodological choice that protects the factorial design. A well-framed thesis paragraph citing µCUTLASS and LEGO as related work is stronger than an overbuilt system that confounds variables.

### 1.4 Why This Specific Technical Stack?

| Component | Choice | Rationale |
|---|---|---|
| Decoding engine | XGrammar | Fastest available CFG-constrained decoding; native HuggingFace LogitsProcessor integration; GBNF grammar format; active maintenance as of 2026 |
| Grammar format | GBNF (standalone `.gbnf` file) | Editable without touching Python; XGrammar's native format; grammar must be auditable independently of generation code |
| Hardware checker | Python attribute grammar checker | Standard CFGs cannot enforce `BLOCK_M * BLOCK_N <= smem_limit`; imperative Python checker runs alongside FSM; keeps grammar file declarative |
| Token classification | Context-independent / context-dependent split | µCUTLASS methodology; prevents `BLOCK_M=37` from passing; enables tighter constraint on numeric literals |
| Primary model | Qwen3-Coder (recommended) or Qwen2.5-Coder-32B | Model is a swappable variable — the thesis studies control mechanisms not model capability; Qwen3-Coder leads open-weight code benchmarks as of May 2026 |
| Baseline dataset | KernelBench (3 representative kernels) | Pre-stratified by kernel class; standardized reference signatures; lighter than TritonBench which is performance-focused (Cluster 3 territory) |

---

## 2. WHAT

### 2.1 Repository Structure (Required)

The following structure is mandatory. File names are contracts — do not rename without updating this document.

```
cluster1/
├── grammar/
│   ├── triton_kernel.gbnf          ← PRIMARY GRAMMAR FILE (standalone, editable)
│   ├── triton_kernel_validator.py  ← Lark-based offline grammar validator
│   └── test_grammar_acceptance.py  ← Known-good and known-bad kernel test suite
├── constraints/
│   └── hardware_checker.py         ← Attribute grammar: smem, power-of-2, register
├── generation/
│   ├── grammar_loader.py           ← Loads + caches compiled XGrammar object
│   └── constrained_gen.py          ← Main generation function, grammar_active flag
├── validation/
│   └── compile_check.py            ← Dummy launch validator, error taxonomy
├── data/
│   ├── kernels/
│   │   ├── elementwise_relu.py     ← KernelBench ReLU reference
│   │   ├── reduction_softmax.py    ← KernelBench Softmax reference
│   │   └── matmul_tiled_gemm.py    ← KernelBench GEMM reference
│   └── prompts/
│       └── prompt_contract.py      ← Locked prompt templates per kernel class
├── results/
│   ├── dataclass.py                ← GenerationResult with all required fields
│   └── logger.py                   ← JSONL result logger
├── experiments/
│   └── run_cluster1.py             ← Orchestrates n=20 runs per (kernel, condition)
├── notebooks/
│   └── cluster1_demo.ipynb         ← End-to-end walkthrough with annotated output
└── tests/
    ├── test_grammar.py              ← Grammar acceptance/rejection tests
    ├── test_hardware_checker.py     ← Checker edge cases
    ├── test_constrained_gen.py      ← Grammar ON vs OFF comparison
    └── test_compile_check.py        ← Compilation gate correctness
```

### 2.2 Grammar File Specification (`triton_kernel.gbnf`)

The grammar must cover ALL of the following. Any token the model might generate that is absent from the grammar will cause degenerate masked outputs — do not leave gaps.

#### 2.2.1 Required Triton Core Ops (Context-Independent Tokens)

| Token / Pattern | Coverage Required | Notes |
|---|---|---|
| `@triton.jit` | Decorator on kernel function | Must be first line of kernel definition |
| `@triton.autotune` | Optional decorator with fixed configs list | Config list must be grammar-constrained to fixed search space |
| `tl.program_id(axis)` | axis must be 0, 1, or 2 only | Reject axis > 2 at grammar level |
| `tl.load(ptr, mask=, other=)` | Full arity including optional kwargs | |
| `tl.store(ptr, value, mask=)` | Full arity | Wrong arity is a known hallucination pattern |
| `tl.arange(start, end)` | Both args required | |
| `tl.constexpr` | Type annotation form | Used in function signatures |
| `tl.dot(a, b, allow_tf32=)` | Matrix multiply op | Critical for matmul-class kernels |
| `tl.atomic_add(ptr, val, mask=)` | Atomic op | Required for reduction kernels |
| `tl.sum(x, axis=)` | Reduction op | |
| `tl.max(x, axis=)` | Reduction op | |
| `tl.zeros(shape, dtype=)` | Tensor init | Shape must be tuple of constexpr |
| `tl.full(shape, value, dtype=)` | Tensor init | |
| `tl.exp`, `tl.log`, `tl.sqrt` | Elementwise math | |
| `tl.where(cond, x, y)` | Conditional select | |
| Launch wrapper | Python function with `[(grid,)](...)` or `.run()` | Must be included — kernel is unusable without it |

#### 2.2.2 Context-Dependent Tokens (Hardware-Constrained)

These tokens require the Python hybrid checker — they cannot be enforced by CFG alone:

- `BLOCK_M`, `BLOCK_N`, `BLOCK_K`: must be powers of two (16, 32, 64, 128, 256)
- `BLOCK_M * BLOCK_N * dtype_bytes` must not exceed GPU shared memory limit (default: 48KB for A100/H100)
- `num_warps`: must be in {1, 2, 4, 8, 16}
- `num_stages`: must be in {1, 2, 3, 4, 5}
- Numeric literals in `tl.arange`: must be consistent with declared BLOCK size

### 2.3 Hardware Checker Specification (`hardware_checker.py`)

The checker is a Python class that runs after each context-dependent token is sampled. It maintains state across the generation of a single kernel and updates XGrammar constraints dynamically.

| Check | Rule | Action on Violation |
|---|---|---|
| Power-of-two enforcement | `BLOCK_M`, `BLOCK_N`, `BLOCK_K` ∈ {16,32,64,128,256} | Mask all non-power-of-two numeric literals at that token position |
| Shared memory budget | `BLOCK_M * BLOCK_N * dtype_bytes ≤ smem_limit` | After `BLOCK_M` is sampled, dynamically update max allowed `BLOCK_N` |
| Warp count | `num_warps` ∈ {1,2,4,8,16} | Mask all other integers at `num_warps` token position |
| Stage count | `num_stages` ∈ {1,2,3,4,5} | Mask integers > 5 at `num_stages` position |
| `tl.dot` shape compatibility | Inner dims of A and B must match | Check after both matrix vars are resolved; flag if mismatch |

> **IMPLEMENTATION NOTE:** The checker must be stateless between kernel generations (reset on each new generation call) but stateful within a single generation. Pass the checker instance into the XGrammar LogitsProcessor callback. `smem_limit` should be a configurable parameter defaulting to `49152` bytes (48KB, covers A100 and H100).

### 2.4 Generation Function Specification (`constrained_gen.py`)

This is the most critical interface in Cluster 1. It must be clean enough that flipping `grammar_active=False` produces a perfectly controlled baseline.

```python
def generate(
    prompt: str,
    model,                         # HuggingFace model or API client
    tokenizer,
    grammar_active: bool,           # THE experimental flag
    compiled_grammar=None,          # Required if grammar_active=True
    hardware_checker=None,          # Required if grammar_active=True
    max_new_tokens: int = 1536,
    temperature: float = 0.2,
    seed: int | None = None,        # Must pass through to torch.manual_seed
) -> GenerationResult
```

> ⛔ **CRITICAL INVARIANT:** When `grammar_active=False`, this function must make EXACTLY the same model call with EXACTLY the same parameters — same prompt, same temperature, same seed, same `max_new_tokens` — with the sole difference being the absence of the XGrammar `LogitsProcessor`. Any other difference between the two paths invalidates your baseline comparison.

XGrammar-specific implementation notes:

- Create a FRESH `LogitsProcessor` instance per `generate()` call — the compiled grammar is reusable but the matcher/processor is stateful and must not be shared across generations
- Log `masked_token_rate` as `(tokens_masked / total_tokens)` averaged across all generation steps — this is a required diagnostic field
- Temperature should default to `0.2` for reproducibility; do not use greedy (`0.0`) as it collapses diversity and breaks pass@k statistics

### 2.5 Compilation Check Specification (`compile_check.py`)

Triton compiles lazily. A clean `triton.jit()` call or import **does not** trigger compilation. You must perform a dummy kernel launch with small representative inputs.

| Step | Required Action | Wrong Approach |
|---|---|---|
| 1. Shared Level 0 parse/signature | Run `shared.eval.levels.level0_parse.check_parse()` and `check_signature()` before runtime import | Importing generated code before rejecting syntax or launcher contract errors |
| 2. Runtime signature guard | After Level 0 passes, import the module and keep `inspect.signature()` as a secondary dynamic guard | Treating runtime inspection as the primary signature authority |
| 3. Dummy launch | Call the kernel with shared compile shapes from `get_compile_shapes()`, all required dtypes, and `device=cuda` | Calling `triton.jit()` alone, or using independent C1-only shape schedules |
| 4. Error taxonomy | Catch `triton.compiler.errors.CompilationError` separately from runtime failures and record canonical `failure_code` | Reporting only legacy `compile_error_type` and losing F0/F1 distinctions |
| 5. Multi-dtype check | Run dummy launch for `fp32`, `fp16`, `bf16` and log pass/fail per dtype | Testing only `fp32`, since bf16/fp16 failures are common and thesis-relevant |
| 6. Result population | Set `compile_success=True` only if all dtype launches succeed; successful rows have `failure_code=None` | Setting `compile_success` from parse result, import success, or one dtype |

Canonical compile-path failure codes are:

- `F0_PARSE` for AST parse failures, including syntax errors previously wrapped
  under legacy `SignatureError`.
- `F0_BAD_SIGNATURE` for Python source whose launcher does not satisfy the
  locked signature contract.
- `F1_COMPILE` for Triton compiler failures during dummy launch.
- `F1_RUNTIME` for import, launch, or runtime failures that are not signature or
  compiler failures.

Legacy `compile_error_type` remains populated for compatibility with frozen
artifacts and historical reports, but current rows and analyses must use
canonical `failure_code` as the primary classification.

### 2.6 Result Dataclass Specification (`results/dataclass.py`)

Every generation run must produce a `GenerationResult`. All fields are required — no `Optional` fields except where noted.

| Field | Type | Description | Notes |
|---|---|---|---|
| `source` | `str` | Raw generated kernel source text | |
| `model_id` | `str` | Model identifier string | e.g. `'Qwen/Qwen2.5-Coder-32B-Instruct'` |
| `grammar_active` | `bool` | Whether constraint was active | THE experimental condition flag |
| `kernel_class` | `str` | `elementwise` \| `reduction` \| `matmul` | |
| `kernel_name` | `str` | Specific kernel name | e.g. `'relu'`, `'softmax'`, `'gemm'` |
| `dtype` | `str` | `fp32` \| `fp16` \| `bf16` | |
| `compile_success` | `bool` | True only if all dtype launches pass | |
| `compile_error_type` | `str \| None` | `CompilationError` \| `RuntimeError` \| `SignatureError` \| `None` | |
| `compile_error_msg` | `str \| None` | Raw error message | Truncated to 500 chars |
| `failure_code` | `str \| None` | Canonical shared failure code | `None` when `compile_success=True`; required for new failed rows |
| `masked_token_rate` | `float \| None` | Avg fraction of vocab masked per step | `None` if `grammar_active=False` |
| `unique_solution_hash` | `str` | AST hash or normalized source hash | For diversity / mode collapse detection |
| `generation_seed` | `int \| None` | Seed passed to `torch.manual_seed` | |
| `temperature` | `float` | Sampling temperature used | |
| `run_id` | `str` | UUID for this specific generation | |
| `timestamp_utc` | `str` | ISO 8601 UTC timestamp | |

Current G/G+C rows also carry grammar and provenance metadata:
`grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`,
`rejection_layer`, `stop_reason`, `xgrammar_version`, `transformers_version`,
`tokenizers_version`, `model_revision`, `tokenizer_revision`,
`modal_image_sha`, and fallback Modal image provenance when the image digest is
unknown. `grammar_valid=true` means both GBNF parse and semantic validation
passed; `grammar_active=true` alone is not G acceptance.

### 2.7 Prompt Contract (`data/prompts/prompt_contract.py`)

The prompt is a fixed contract. It must not change between `grammar_active=True` and `grammar_active=False` runs. It must be locked before generation runs begin.

> **PROMPT INVARIANTS:** (1) Always includes the function signature. (2) Always includes a docstring describing the kernel semantics. (3) Explicitly instructs: return ONLY valid Triton kernel code — no explanation, no markdown fences, no wrapper text. (4) Specifies dtype and device explicitly. (5) Includes `@triton.autotune` with a FIXED config list (not free-form) so the model does not invent tile sizes.

```python
PROMPT_TEMPLATE = '''
You are a Triton GPU kernel engineer. Write a complete, valid Triton kernel.

Function signature: {signature}
Kernel description: {description}
Input dtype: {dtype}  |  Device: CUDA

Use the following autotune configs exactly:
{autotune_configs}

Return ONLY the kernel code. No explanation. No markdown. No comments.
Start your response with @triton.autotune or @triton.jit.
'''
```

### 2.8 Dataset Specification (`data/kernels/`)

Three kernels from KernelBench, one per kernel class. Reference signatures must be locked before any generation run begins — do not change them mid-experiment.

| Kernel | Class | KernelBench Source | Reference Signature (locked) |
|---|---|---|---|
| ReLU | Elementwise / memory-bound | KernelBench level 1, problem 19 | `relu(x: torch.Tensor) -> torch.Tensor` |
| Softmax | Reduction / memory-bound | KernelBench level 1, problem 23 | `softmax(x: torch.Tensor) -> torch.Tensor` |
| Tiled GEMM | Matmul-class / compute-bound | KernelBench level 1, problem 1 | `matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor` |

The locked Cluster 1 KernelBench Level 1 problem IDs are ReLU=19, Softmax=23, and GEMM/Matmul=1. These IDs are pinned to the corresponding KernelBench problems used by the frozen artifacts and data adapter. Any future change to the kernel set or problem IDs must update this contract, the data adapter, and the frozen-artifact manifest in the same commit.

> **WHY NOT TRITONBENCH?** TritonBench is performance-focused and better suited to Cluster 3 (profiler/RL evaluation). KernelBench has standardized reference implementations for correctness diffing, is pre-stratified by kernel class matching your experimental design, and is lighter to run. TritonBench may be used as a secondary dataset in the final evaluation phase but is not required for Cluster 1.

### 2.9 Statistical Requirements

These are non-negotiable for the thesis to be statistically valid.

- Minimum **n=20 generations** per (kernel_class × condition) cell — this is the floor for the unbiased HumanEval pass@k estimator
- Report **pass@k for k ∈ {1, 5, 10}** using the UNBIASED estimator: `pass@k = E[1 - C(n-c, k) / C(n, k)]`
- For Cluster 1: "correct" means `compile_success=True` ONLY — do NOT use numerical correctness here
- Track `unique_solution_hash` across all 20 runs per cell to detect **mode collapse** — if grammar constrains outputs so tightly that all generations are near-identical, pass@5 is misleading
- Conditions to run: `grammar_active=True` and `grammar_active=False` (the ∅ baseline) — you need both to make any claim about the G factor

---

## 3. HOW

### 3.1 XGrammar Integration — Step by Step

This is the highest-risk implementation area. The most common failure modes are documented here.

#### Step 1: Install and verify

```bash
pip install xgrammar transformers torch triton
python -c 'import xgrammar as xgr; print(xgr.__version__)'
```

#### Step 2: Compile the grammar (`grammar_loader.py`)

```python
import xgrammar as xgr
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=8)
def load_compiled_grammar(grammar_path: str, tokenizer_id: str):
    grammar_str = Path(grammar_path).read_text()
    tokenizer_info = xgr.TokenizerInfo.from_huggingface(tokenizer_id)
    compiler = xgr.GrammarCompiler(tokenizer_info)
    return compiler.compile_grammar(xgr.Grammar.from_ebnf(grammar_str))
```

> ⚠️ **GOTCHA #1:** The compile step is expensive (~2–10 seconds). Always cache per `(grammar_path, tokenizer_id)`. The compiled grammar is reusable across generations. The `LogitsProcessor` is NOT reusable — create a fresh one per `generate()` call.

#### Step 3: Attach LogitsProcessor (`constrained_gen.py`)

```python
import xgrammar as xgr
from xgrammar.contrib.hf import XGrammarLogitsProcessor

# Inside generate() when grammar_active=True:
matcher = xgr.GrammarMatcher(compiled_grammar)  # fresh per call
processor = XGrammarLogitsProcessor(matcher)
output = model.generate(
    input_ids,
    logits_processor=[processor],
    max_new_tokens=max_new_tokens,
    temperature=temperature,
    do_sample=True,
)
```

> ⚠️ **GOTCHA #2 — TOKENIZER VOCAB ALIGNMENT:** XGrammar maps grammar terminals to the model's actual token vocabulary. If you switch models (e.g., from Qwen2.5 to Qwen3), you must recompile the grammar for the new tokenizer. The compiled grammar is tokenizer-specific. This is the most common silent failure — wrong tokenizer produces bizarre masked outputs with no error.

### 3.2 Grammar File Validation — Do This Before Touching the Model

Write these tests BEFORE you run a single generation. A broken grammar produces confusing generation outputs with no useful error message.

1. Collect 10–15 known-good Triton kernels from official Triton tutorials (`vector_add`, `softmax`, `matmul`, `layernorm`, `flash_attention`)
2. For each, verify grammar acceptance using XGrammar's acceptance testing API
3. Collect 10 deliberately broken kernels: missing `@triton.jit`, wrong-arity `tl.store`, invalid `BLOCK_M=37`, missing launch wrapper
4. Verify all broken kernels are REJECTED by the grammar
5. Run Lark-based offline validator on the `.gbnf` file to check internal consistency

> **IF GRAMMAR IS TOO TIGHT:** You will see valid kernels being rejected. Symptom: model outputs are all empty shells or single-line stubs. Fix: expand expression grammar to be permissive on statement bodies while staying tight on structure.

> **IF GRAMMAR IS TOO LOOSE:** Invalid kernels pass the grammar check. Symptom: `compile_success` rate does not improve with `grammar_active=True` vs `False`. Fix: audit which failure modes are still appearing and add grammar rules for them.

### 3.3 Compilation Check — What "Actual Compilation" Means

```python
import triton
import triton.compiler.errors
import torch
import inspect
from shared.eval.levels.level0_parse import check_parse, check_signature

def check_compiles(source: str, kernel_spec, dtype=torch.float32):
    # Step 1: shared Level 0 checks before runtime import.
    parse_ok, parse_error = check_parse(source)
    if not parse_ok:
        return False, "SyntaxError", str(parse_error)[:500], "F0_PARSE"
    signature_ok, signature_error = check_signature(source, kernel_spec)
    if not signature_ok:
        return False, "SignatureError", str(signature_error)[:500], "F0_BAD_SIGNATURE"

    # Step 2: runtime import and secondary signature guard.
    module = load_generated_module(source)
    launcher = getattr(module, kernel_spec.launcher_name)
    if inspect.signature(launcher) != kernel_spec.compile_spec.reference_signature:
        return False, "SignatureError", "Signature mismatch", "F0_BAD_SIGNATURE"

    # Step 3: dummy launch over shared compile shapes to trigger JIT compilation.
    try:
        x = torch.randn(32, dtype=dtype, device="cuda")
        launcher[(1,)](x, ...)  # adjust args to match signature
        return True, None, "", None
    except triton.compiler.errors.CompilationError as e:
        return False, "CompilationError", str(e)[:500], "F1_COMPILE"
    except RuntimeError as e:
        return False, "RuntimeError", str(e)[:500], "F1_RUNTIME"
```

### 3.4 Model Configuration

| Parameter | Value | Reason |
|---|---|---|
| Primary model | `Qwen/Qwen3-Coder` (latest) or `Qwen/Qwen2.5-Coder-32B-Instruct` | Strongest open-weight code model as of May 2026; thesis requires open-weight for reproducibility |
| Secondary model (cross-check) | `DeepSeek-Coder-V2-Instruct` | Verify findings generalize beyond one model's training distribution |
| Temperature | `0.2` | Low enough for reproducibility; high enough to avoid mode collapse in pass@k stats |
| `max_new_tokens` | `1536` | Current code default; avoids budget-exhaustion confounds for complete launcher plus kernel generations |
| Seed | Enumerated: `0..19` for n=20 runs | Reproducible; each run gets a different seed so diversity is real, not seeded collapse |
| Quantization | 4-bit or 8-bit if VRAM constrained | Document quantization level in every result — it affects generation quality |

### 3.5 Boundary Violations — What Must NOT Appear in Cluster 1 Code

These are hard stops. If any of the following appear in the Cluster 1 code path, it is a boundary violation that must be removed immediately.

| Violation | Why It Matters | Which Cluster It Belongs To |
|---|---|---|
| `torch.allclose()` or any numerical correctness check | Numerical validation is Cluster 2 (feedback loop) territory | Cluster 2 |
| Any Nsight Compute call or perf metric collection | Performance measurement is Cluster 3 territory | Cluster 3 |
| Any repair loop, retry, or LLM feedback step | Repair loops are the definition of Cluster 2 | Cluster 2 |
| Speedup calculation or timing measurement | Timing is Cluster 3 territory; timing incorrect kernels is reward hacking | Cluster 3 |
| `compute-sanitizer` or memcheck integration | Memory safety is Cluster 2 territory | Cluster 2 |

---

## 4. DEFINITION OF DONE

Cluster 1 is complete when ALL of the following are checked. No exceptions.

### 4.1 Grammar Layer

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| G1 | `triton_kernel.gbnf` exists | File present, standalone, covers all ops in Section 2.2 table | @grammar |
| G2 | Context-independent tokens | All fixed Triton ops whitelisted; wrong-arity calls rejected | @grammar |
| G3 | Context-dependent tokens | `BLOCK_*` restricted to powers-of-two; `num_warps`/`num_stages` restricted | @grammar |
| G4 | Launch wrapper grammar | `[(grid,)](...)` and `.run()` syntax included and tested | @grammar |
| G5 | Offline validator passes | Lark validator confirms grammar is internally consistent | @grammar |
| G6 | Grammar acceptance test suite | 10+ known-good kernels accepted; 10+ known-bad kernels rejected | @grammar |

### 4.2 Hardware Checker Layer

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| H1 | `hardware_checker.py` exists | Checker class with state reset per generation call | @constraints |
| H2 | Power-of-two enforcement | `BLOCK_M=37` is rejected; `BLOCK_M=64` passes; test present | @constraints |
| H3 | Shared memory budget | `BLOCK_M=128, BLOCK_N=256, fp16` correctly rejected (exceeds 48KB); test present | @constraints |
| H4 | `smem_limit` configurable | Parameter defaults to `49152`; can be overridden per GPU target | @constraints |
| H5 | Checker integrates with XGrammar | Checker updates logit mask at `BLOCK_*` token positions during generation | @constraints |

### 4.3 Constrained Decoding Layer

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| D1 | `grammar_loader.py` with caching | Compiled grammar cached per `(grammar_path, tokenizer_id)`; second call does not recompile | @generation |
| D2 | `grammar_active` flag is sole diff | Code review confirms: same prompt, same params, same model — only `LogitsProcessor` differs | @generation |
| D3 | Fresh `LogitsProcessor` per call | Confirmed in code that matcher/processor is not reused across `generate()` calls | @generation |
| D4 | Tokenizer vocab alignment verified | Test confirms grammar compiles correctly for each model's tokenizer; switching model triggers recompile | @generation |
| D5 | `masked_token_rate` logged | Float field present in `GenerationResult`; non-None for `grammar_active=True` runs | @generation |

### 4.4 Validation Gate

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| V1 | Dummy launch triggers JIT | Compilation check uses actual kernel launch, not `triton.jit()` call alone | @validation |
| V2 | `CompilationError` vs `RuntimeError` split | Both caught separately; logged to `compile_error_type` and canonical `failure_code` fields | @validation |
| V3 | Multi-dtype check | `fp32`, `fp16`, `bf16` all tested; pass/fail logged per dtype | @validation |
| V4 | Signature validation before compile | Shared Level 0 parse/signature runs before import; runtime `inspect.signature()` remains a secondary guard; failures record canonical F0 codes | @validation |
| V5 | No Cluster 2/3 leakage | Code review: no `torch.allclose`, no timing, no repair loop in `compile_check.py` | @validation |

### 4.5 Data & Runs

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| R1 | 3 KernelBench kernels present | ReLU, Softmax, GEMM — reference signatures locked in `prompt_contract.py` | @data |
| R2 | `GenerationResult` dataclass complete | All required fields from Section 2.6 present and populated in every result, including canonical `failure_code` for new failed rows | @results |
| R3 | JSONL logger works | Results append-write to `.jsonl`; loadable with pandas for analysis | @results |
| R4 | Baseline runs (`grammar_active=False`) | n≥20 unconstrained generations per kernel class; logged as ∅ condition | @experiments |
| R5 | Constrained runs (`grammar_active=True`) | n≥20 constrained generations per kernel class; `compile_success` rate computed | @experiments |
| R6 | `unique_solution_hash` populated | AST or normalized hash present for all runs; diversity report generated | @experiments |
| R7 | pass@k computed (k=1,5,10) | Unbiased HumanEval estimator used; NOT naive rate; results in summary table | @experiments |

### 4.6 Tests & Notebook

| ID | Deliverable | Definition of Done | Owner Tag |
|---|---|---|---|
| T1 | `test_grammar.py` | ≥20 acceptance/rejection tests; all pass in CI | @tests |
| T2 | `test_hardware_checker.py` | Power-of-two, smem budget, warp/stage range tests; edge cases covered | @tests |
| T3 | `test_constrained_gen.py` | Grammar ON generates valid kernel; Grammar OFF can produce invalid kernel; `masked_token_rate > 0` when `grammar_active=True` | @tests |
| T4 | `test_compile_check.py` | Known-bad kernel fails check; known-good passes; error types logged correctly | @tests |
| T5 | `cluster1_demo.ipynb` | End-to-end: load model → constrained generation → compilation check → result display; runs clean top-to-bottom | @notebooks |

---

## 5. OUT OF SCOPE

> ⛔ If you find yourself building any of the following, you have drifted out of Cluster 1 scope. Stop, record the idea, and assign it to Cluster 2 or 3.

- DSL or IR layer (µCUTLASS, LEGO-style) — cited in related work, not implemented here
- Earley parsing engine — XGrammar's FSM is sufficient; Earley is a separate implementation project
- Numerical correctness validation (`torch.allclose`, reference diff)
- Compiler error feedback to the LLM (repair loop)
- Profiler integration (Nsight Compute, roofline analysis)
- RL reward shaping or policy gradient
- `compute-sanitizer` / memcheck integration
- Multi-GPU or distributed generation
- CUDA kernel generation (Triton only)
- Cross-architecture constraint (H100 vs A100 register pressure) — noted as future work

---

## 6. AGENT WORK BREAKDOWN

These tasks can be assigned to separate code agents working in parallel. Each agent should receive this full contract plus its specific task tag below.

| Tag | Task | Input Dependencies | Output |
|---|---|---|---|
| @grammar | Write `triton_kernel.gbnf`, Lark validator, and grammar test suite | Section 2.2 op list | `triton_kernel.gbnf`, `triton_kernel_validator.py`, `test_grammar.py` |
| @constraints | Write `hardware_checker.py` and its tests | Section 2.3 spec, grammar file | `hardware_checker.py`, `test_hardware_checker.py` |
| @generation | Write `grammar_loader.py` and `constrained_gen.py` | grammar file, checker, Section 2.4 spec | `grammar_loader.py`, `constrained_gen.py`, `test_constrained_gen.py` |
| @validation | Write `compile_check.py` and its tests | Section 2.5 spec | `compile_check.py`, `test_compile_check.py` |
| @data | Pull KernelBench kernels, lock signatures, write `prompt_contract.py` | Section 2.7–2.8 spec | `data/kernels/*.py`, `data/prompts/prompt_contract.py` |
| @results | Write `GenerationResult` dataclass and JSONL logger | Section 2.6 field list | `results/dataclass.py`, `results/logger.py` |
| @experiments | Write `run_cluster1.py` orchestrator and analysis scripts | All above outputs | `experiments/run_cluster1.py`, pass@k summary report |
| @notebooks | Write `cluster1_demo.ipynb` | All above outputs | `notebooks/cluster1_demo.ipynb` |

> **INTEGRATION ORDER:** `@grammar` and `@data` can start immediately in parallel. `@constraints` depends on `@grammar`. `@generation` depends on `@grammar` and `@constraints`. `@validation` and `@results` are independent. `@experiments` depends on all. `@notebooks` depends on all.

---

## 7. KEY REFERENCES

Papers to cite in the Cluster 1 related work section:

- **XGrammar** (2024) — Flexible and Efficient Structured Generation Engine for Large Language Models. Primary constrained decoding engine.
- **µCUTLASS** (Sun et al., 2025) — Earley-driven dynamic pruning; source of context-independent/context-dependent token classification methodology.
- **LEGO** (Tavakkoli et al., 2025) — Layout Expression for Generating One-to-one Mapping. DSL-mediated approach; cited as stronger bound in related work. https://doi.org/10.48550/arxiv.2505.08091
- **CRANE / GREATGRAMMA** — Prior grammar constraint work; establishes the baseline this work builds on.
- **KernelBench** — Dataset source; cite as evaluation benchmark.
- **HumanEval pass@k estimator** (Chen et al., 2021) — Statistical method for unbiased pass@k computation.
- **Liger Kernel** (Hsu et al., 2024) — Efficient Triton Kernels for LLM Training. https://doi.org/10.48550/arxiv.2410.10989

---

*END OF CLUSTER 1 CONTRACT | Any change to this document must be versioned and dated.*
