# Evaluation Metrics Implementation Specification

## TritonGen Factorial Experiment — Shared Metrics Infrastructure

**Version:** 1.0
**Status:** research-facing metric and schema design reference.
**Scope:** Defines every metric, its computation, gating logic, data schema, and code contract for all three clusters. The goal is a single `shared/eval/` package that every cluster imports identically, so baseline runs and experimental runs produce comparable results with zero per-cluster metric code.

> **Current status note (2026-05-11):** This file remains the metric and schema
> reference, but it is not the phased implementation plan. The research scope
> lives in `.contracts/research/research_scope.md`; internal execution notes
> live under `.contracts/agentic/` when present. The current iteration analyzes
> a temporary 2² subset over G and C: none, G, C, and G+C. The full 2³ factorial
> over G, C, and P remains the defined project goal. P-containing cells are
> deferred for this iteration and are not included in current paper-claiming
> outputs. This is a current-status scope statement, not a methodology
> realignment. The core metric ladder, null-field gating convention, and
> result-schema intent remain valid.

---

## 0. Design Principles

1. **One implementation, three consumers.** Cluster 1, 2, and 3 all call the same `shared/eval/` functions. No cluster implements its own metric logic. If a cluster needs a metric it cannot compute (e.g., Cluster 1 cannot measure speedup), it records the field as JSON `null` in `EvalResult` so dataframe loaders convert it to `NaN` — it never omits the field.
2. **Gating is code, not convention.** If Level N fails, Level N+1 metrics are JSON `null` / dataframe `NaN`. This is enforced by the `EvalResult` dataclass and the `run_eval_pipeline()` function, not by hoping each cluster remembers to check.
3. **KernelBench alignment.** Metrics names and semantics align with KernelBench where possible (`fast_p`, `pass@k`). Where we extend beyond KernelBench (repair_iters, failure taxonomy), the extensions are additive — they never redefine a KernelBench metric.
4. **Schema-first.** The `EvalResult` dataclass is the contract. Every downstream consumer (analysis scripts, paper tables, visualization) reads from `EvalResult` JSON. If a field is not in `EvalResult`, it does not exist.
5. **Factor labels are canonical.** The 2³ factors are `G` (grammar), `C` (test-driven correctness feedback), and `P` (compiler/profiler repair). Use `none`, `G`, `C`, `P`, `G+C`, `G+P`, `C+P`, and `G+C+P` in result schemas. Do not add an older `T` label for test-driven feedback.
6. **G acceptance is a two-layer contract.** The G factor means grammar-guided decoding plus offline semantic post-validation. XGrammar masks tokens against the GBNF grammar during generation; the offline validator then enforces structural and surface rules that the context-free grammar cannot fully express. A row is G-accepting only if both layers pass.

---

## 1. The Correctness Ladder — Definitions and Gating Logic

### 1.0 G Acceptance Contract

G consists of two enforcement layers. During generation, XGrammar applies
token-level masking against a context-free grammar defined in GBNF. After
generation, a semantic validator performs additional structural and surface
checks that the context-free grammar cannot express. A generation is counted as
G-accepting only if it passes both layers; rows that pass decoding but fail
semantic validation are recorded as grammar-rejected with explicit
failure-layer attribution.

Preferred short label:

> grammar-guided decoding plus offline semantic post-validation

The grammar-acceptance metric is separate from the correctness ladder below.
`grammar_acceptance`, `grammar_valid`, or equivalent G-acceptance fields mean
joint acceptance by the decoding contract and the offline validator. A row can
be grammar-rejected while still being syntactically valid Python, and a row can
be grammar-accepted while later failing `compile_success` or
`functional_success`.

When available, grammar rejection records should identify one of these failure
layers:

| Failure layer | Meaning |
| --- | --- |
| `gbnf_parse` | Offline GBNF parse rejected the generated source or the generation terminated as an incomplete grammar prefix. |
| `python_ast` | GBNF parse passed, but Python AST parsing failed. |
| `semantic_validator` | GBNF parse and AST parse passed, but offline semantic/surface checks failed. |
| `runtime_error` | Runtime grammar provenance, validator setup, or validation execution failed. |
| `unknown` | The failure layer was not recoverable from the artifact. |

`grammar_active` means the constrained decoding path was attempted. It is not
evidence of G acceptance. `masked_token_rate` is a masking diagnostic over
observed decoding steps, not proof of strict enforcement. Current-generation
paper-scale rows must carry per-row grammar provenance, runtime/model/tokenizer
provenance, stop reason, split validation fields, joint `grammar_valid`, and
`rejection_layer`.

`compile_success` remains the Level 1 compile gate. `functional_success` remains
the Level 2 numerical correctness gate. Neither field should be used as a proxy
for G acceptance.

### 1.1 Level Definitions

| Level | Name         | Gate Criterion | How to Check | Failure Records |
|-------|-------------|----------------|--------------|-----------------|
| 0     | **Parsed**   | Source is syntactically valid Python with a `@triton.jit` decorated function | `ast.parse(source)` succeeds AND AST contains `triton.jit` decorator | `parse_error: str` |
| 1     | **Compiled** | Kernel JIT-compiles when launched with representative dummy inputs | Dummy launch with small tensors inside `try/except` catching `triton.compiler.errors.CompilationError` and `RuntimeError` | `compile_error: str` |
| 2     | **Functional** | Output matches PyTorch reference within per-op tolerance | `torch.allclose(output, reference, atol=atol, rtol=rtol)` across N≥5 random input shapes from KernelBench's `get_inputs()` | `correctness_error: str`, `max_abs_diff: float`, `max_rel_diff: float` |
| 3     | **Safe**     | No illegal memory access or race conditions | `compute-sanitizer --tool memcheck` exits with 0 errors | `sanitizer_errors: list[str]` |
| 4     | **Performant** | Speedup ≥ 1.0× vs `torch.compile(mode="max-autotune")` | Median of 100 timed iterations after 25 warmup, using `torch.cuda.Event` | `speedup_vs_eager: float`, `speedup_vs_compile: float` |

### 1.2 Per-Operation Tolerance Table

This table is authoritative. Do not use a single global tolerance.

| Operation Class | Representative Ops | `atol` (fp32) | `rtol` (fp32) | `atol` (fp16/bf16) | `rtol` (fp16/bf16) |
|----------------|-------------------|---------------|---------------|--------------------|--------------------|
| Elementwise    | ReLU, GELU, Sigmoid, Tanh | 1e-5 | 1e-5 | 1e-3 | 1e-3 |
| Reduction      | Softmax, LayerNorm, Sum, Mean | 1e-4 | 1e-4 | 1e-2 | 1e-2 |
| MatMul         | GEMM, BatchedGEMM | 1e-3 | 1e-3 | 5e-2 | 5e-2 |
| Convolution    | Conv1d, Conv2d, DepthwiseConv | 1e-3 | 1e-3 | 5e-2 | 5e-2 |
| Fused          | MatMul+GELU+Bias, Attention | 1e-3 | 1e-3 | 5e-2 | 5e-2 |

Implementation: store as a `dict[str, dict[str, float]]` in `shared/eval/tolerances.py`. The key is `kernel_class` (from KernelBench problem metadata), the values are `{atol_fp32, rtol_fp32, atol_fp16, rtol_fp16}`. Convolution has its own class rather than inheriting MatMul defaults because its access patterns and numerical behavior differ from GEMM.

**Fused-kernel caution:** Cluster 2+ correctness checks may need fused-op tolerances that are no tighter than the reference path's own observed variance. Before final fused-kernel reporting, run the PyTorch reference repeatedly on a fixed seed/input set and record `reference_variance_max_abs` / `reference_variance_max_rel`. If reference variance exceeds the table tolerance, either widen the fused tolerance with a recorded justification or exclude that fused problem from the Level 2 analysis. This calibration is a correctness-contract concern only; Cluster 1 must not run reference comparisons.

### 1.3 Gating Logic (Pseudocode)

```python
def run_eval_pipeline(
    source: str,
    kernel_spec: KernelSpec,
    run_config: RunConfig,
) -> EvalResult:
    result = EvalResult(kernel_id=kernel_spec.problem_id, condition=run_config.condition)

    # Level 0: Parse
    parse_ok, parse_error = check_parse(source)
    result.level = 0
    result.parse_success = parse_ok
    result.parse_error = parse_error
    if not parse_ok:
        # All downstream = None in JSON / NaN after dataframe loading
        return result

    # Level 1: Compile (requires GPU)
    compile_ok, compile_error = check_compile(source, kernel_spec)
    result.level = 1
    result.compile_success = compile_ok
    result.compile_error = compile_error
    if not compile_ok:
        return result

    # Level 2: Functional correctness
    func_ok, func_details = check_correctness(source, kernel_spec)
    result.level = 2
    result.functional_success = func_ok
    result.max_abs_diff = func_details.max_abs_diff
    result.max_rel_diff = func_details.max_rel_diff
    result.correctness_error = func_details.error
    if not func_ok:
        # speedup = None / dataframe NaN — DO NOT MEASURE
        return result

    # Level 3: Memory safety (optional gate — skip if compute-sanitizer unavailable)
    if run_config.enable_sanitizer:
        safe_ok, sanitizer_errors = check_memory_safety(source, kernel_spec)
        result.level = 3
        result.safe_success = safe_ok
        result.sanitizer_errors = sanitizer_errors
        if not safe_ok:
            # speedup = None / dataframe NaN — DO NOT MEASURE
            return result
    else:
        result.safe_success = None  # Not evaluated
        result.level = 3  # Promote past safety gate when sanitizer disabled

    # Level 4: Performance
    perf = measure_performance(source, kernel_spec, run_config)
    result.level = 4
    result.speedup_vs_eager = perf.speedup_vs_eager
    result.speedup_vs_compile = perf.speedup_vs_compile
    result.kernel_time_ms = perf.kernel_time_ms
    result.eager_time_ms = perf.eager_time_ms
    result.compile_time_ms = perf.compile_time_ms

    return result
```

**Critical rule:** A cluster that only evaluates up to Level 1 (Cluster 1) calls `run_eval_pipeline()` with `run_config.max_level = 1`. The pipeline short-circuits after Level 1 and returns JSON `null` / dataframe `NaN` for all downstream fields. The cluster never implements its own partial pipeline.

---

## 2. Metric Definitions

### 2.1 Primary Metrics (Paper Headline)

#### 2.1.1 `compile@1`

- **Definition:** Fraction of single-shot generations where `compile_success = True` (Level 1 gate passed).
- **Formula:** `compile@1 = count(compile_success) / count(total_generations)` per (kernel, condition) cell.
- **Owner:** Cluster 1 primary metric.
- **Scope:** Computed per kernel class and per condition. Report both per-class and aggregate (aggregate = arithmetic mean across kernel classes, NOT pooled across all generations — pooling lets easy kernels dominate).

#### 2.1.2 `pass@k` (k ∈ {1, 5, 10})

- **Definition:** Probability that at least 1 of k samples is functionally correct (Level 2).
- **Formula (unbiased, from HumanEval):**

```
pass@k = 1 - C(n-c, k) / C(n, k)
```

Where `n` = total samples per (kernel, condition) cell, `c` = count of correct samples.

- **Implementation:**

```python
from math import comb

def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimator of pass@k.

    Args:
        n: Total number of samples generated.
        c: Number of correct (Level 2+) samples.
        k: Number of attempts allowed.

    Returns:
        Estimated probability that at least one of k samples is correct.
    """
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)
```

- **Sample size:** n = 20 per (kernel, condition) cell for paper-scale runs. Smoke and development runs use the scale-tier policy in Section 5.2 and are not valid sources for reported paper claims.
- **Owner:** Cluster 2 primary metric (Level 2 correctness), but Cluster 1 reports `pass@1` at Level 1 (compile-only) as `compile@1`.
- **Report:** `pass@1`, `pass@5`, `pass@10` in all results tables. Three points show the curve shape.

#### 2.1.3 Speedup Ratio (S_tc)

- **Definition:** Ratio of `torch.compile` wall time to generated kernel wall time.
- **Formula:**

```
S_tc = median(torch_compile_times) / median(generated_kernel_times)
```

- **S_tc > 1.0** means the generated kernel is faster.
- **Only computed when Level 2 passes.** If `functional_success = False`, `S_tc = None` in JSON and `NaN` after dataframe loading.
- **Aggregation:** Geometric mean across kernels within a condition. Never arithmetic mean for ratios.
- **Owner:** Cluster 3 primary metric.
- **Also report:** `S_eager = median(eager_times) / median(kernel_times)` as the "low bar."

#### 2.1.3.1 Spurious-Speedup Audit

- **Definition:** Defensive audit proving that speedup metrics are gated by Level 2 correctness.
- **Formula:**

```
spurious_speedup_rate =
  count((speedup_vs_compile > 1.0 OR speedup_vs_eager > 1.0) AND functional_success == False) / count(total)
```

- **Expected value:** Always `0.0` by construction. Nonzero means the pipeline measured or retained a speedup for a functionally incorrect kernel and the analyzer output must be treated as invalid until the gate is fixed.
- **Report:** Every analyzer output should include this value, even when all Level 4 metrics are otherwise omitted.

#### 2.1.4 `fast@p` (KernelBench-aligned)

- **Definition:** Fraction of tasks that are BOTH numerically correct (Level 2) AND achieve speedup ≥ p relative to eager PyTorch.
- **Standard p-values:** Report `fast@0.0` (correctness only = same as `pass@1` at Level 2), `fast@1.0` (matches eager), `fast@1.2` (20% faster than eager).
- **Torch-compile usability variant:** Cluster 3 also reports `fast_tc@1.0` and `fast_tc@1.2`, computed with `speedup_vs_compile` instead of `speedup_vs_eager`. This keeps KernelBench-aligned `fast@p` intact while separately answering whether generated kernels beat the production-grade `torch.compile(mode="max-autotune")` baseline.
- **Formula:**

```python
def fast_at_p(results: list[EvalResult], p: float) -> float:
    """Fraction of results that are correct AND have speedup >= p."""
    eligible = [r for r in results if r.functional_success is not None]
    if not eligible:
        return 0.0
    passing = [
        r for r in eligible
        if r.functional_success and r.speedup_vs_eager is not None and r.speedup_vs_eager >= p
    ]
    return len(passing) / len(eligible)
```

- **Owner:** Cross-cluster summary metric. Reported in the final paper table.

```python
def fast_tc_at_p(results: list[EvalResult], p: float) -> float:
    """Fraction of results that are correct AND speedup_vs_compile >= p."""
    eligible = [r for r in results if r.functional_success is not None]
    if not eligible:
        return 0.0
    passing = [
        r for r in eligible
        if r.functional_success and r.speedup_vs_compile is not None and r.speedup_vs_compile >= p
    ]
    return len(passing) / len(eligible)
```

### 2.2 Secondary Metrics (Interaction Analysis)

#### 2.2.1 `repair_iters`

- **Definition:** Number of generate→validate→feedback→regenerate cycles before a kernel reaches Level 2 (functional correctness), OR the iteration budget is exhausted.
- **Budget:** Fixed at 5 iterations. Document in the paper. Do not allow unbounded repair.
- **What counts as 1 iteration:** One full cycle where (a) the model receives feedback from the previous attempt, (b) generates a new kernel, (c) the new kernel is evaluated. A retry with a new random seed but the same prompt is NOT a repair iteration — it is resampling.
- **Fields recorded per trial:**

```python
@dataclass
class RepairTrace:
    iteration: int              # 0 = initial generation, 1-5 = repair attempts
    source: str                 # generated source at this iteration
    level_reached: int          # 0-4
    feedback_type: str          # "none" | "compile_error" | "correctness_error" | "sanitizer_error" | "perf_feedback"
    feedback_content: str       # the actual error message fed back to the model
    tokens_generated: int       # output tokens for this iteration
    converged: bool             # did this iteration reach Level 2?
```

- **Derived metrics:**

```python
# Mean repair iterations among converged trials
repair_iters_converged = mean([t.iteration for t in traces if t.converged])

# Convergence rate
convergence_rate = count(converged) / count(total_trials)

# Pass@1 after repair (distinct from raw pass@1)
pass1_after_repair = count(converged) / count(total_trials)
```

- **Owner:** Cluster 2 (feedback loops). This is the "sleeper metric" — if G+C+P takes 4.2 repair iterations but C+P takes 2.1, grammar constraints are adding overhead.

#### 2.2.2 Repair Efficiency

- **Definition:** Correctness gain per token spent in repair.
- **Formula:**

```
repair_efficiency = Δpass@1 / total_tokens_to_convergence
```

Where `Δpass@1 = pass@1_after_repair - pass@1_initial` and `total_tokens_to_convergence = sum(tokens_generated across all repair iterations for converged trials)`.

- **Interpretation:** Higher = the feedback loop is efficient. If one condition achieves the same `Δpass@1` with fewer tokens, its repair mechanism is more cost-effective.

#### 2.2.3 Cost-Adjusted pass@1

- **Definition:** Correctness normalized by generation cost.
- **Formula:**

```
cost_adjusted_pass1 = pass@1 / mean_total_tokens_per_trial
```

- **Why:** A method achieving 5% higher pass@1 at 10× token cost is not obviously better. This metric captures the tradeoff.

### 2.3 Diagnostic Metrics (Failure Analysis)

#### 2.3.1 Failure Taxonomy

Every failed generation is categorized into exactly one canonical failure class.
The shared implementation is `shared/eval/failure_taxonomy.py`, and canonical
`failure_code` is the primary analysis and replay field. Legacy Cluster 1
`compile_error_type` labels remain secondary diagnostics and are converted to
canonical codes at read, analysis, and replay time. Explicit row-level canonical
`failure_code` values are never overridden.

| Code | Category | Level Failed | Detection |
|------|----------|-------------|-----------|
| `F0_PARSE` | Syntax error — not valid Python | 0 | `ast.parse()` raises `SyntaxError` |
| `F0_GBNF_PARSE` | Grammar-layer parse rejection | 0 | GBNF parse failed or generation ended as an incomplete grammar prefix |
| `F0_SEMANTIC_INVALID` | Offline semantic validator rejection | 0 | GBNF and AST passed, semantic/surface validation failed |
| `F0_GRAMMAR_INVALID` | Grammar rejection with incomplete layer attribution | 0 | `grammar_valid=false` but the exact rejection layer is unknown |
| `F0_NO_DECORATOR` | Valid Python but no `@triton.jit` | 0 | AST scan finds no `triton.jit` decorator |
| `F0_BAD_SIGNATURE` | Wrong launcher signature | 0 | Shared Level 0 AST signature check rejects, or runtime signature guard rejects |
| `F0_SURFACE_VIOLATION` | Surface-policy violation | 0 | Sanitizer or semantic surface checks identify forbidden generated structure |
| `F1_COMPILE` | Triton compilation failure | 1 | `CompilationError` on dummy launch |
| `F1_RUNTIME` | Runtime crash during dummy launch | 1 | `RuntimeError` during launch |
| `F2_NUMERIC_LARGE` | Output deviates beyond tolerance | 2 | `allclose` fails, `max_abs_diff > atol` |
| `F2_NUMERIC_NAN` | Output contains NaN/Inf | 2 | `torch.isnan(output).any()` or `torch.isinf(output).any()` |
| `F2_SHAPE_MISMATCH` | Output shape doesn't match reference | 2 | `output.shape != reference.shape` |
| `F3_OOB` | Out-of-bounds memory access | 3 | `compute-sanitizer` OOB error |
| `F3_RACE` | Race condition detected | 3 | `compute-sanitizer --tool racecheck` |
| `F3_TIMEOUT` | Sanitizer run timed out | 3 | `subprocess.TimeoutExpired` from `compute-sanitizer` |

- **Implementation:** `classify_failure(result: EvalResult) -> str` returns exactly one code.
- **Storage:** `EvalResult.failure_code: Optional[str]` — `None` if Level 4 reached.
- **Paper output:** Stacked bar chart per condition showing failure distribution.

Syntax-aware legacy mapping is part of the taxonomy. A frozen Cluster 1 row with
`compile_error_type="SignatureError"` and syntax-error text maps to `F0_PARSE`;
a true launcher/signature mismatch maps to `F0_BAD_SIGNATURE`. This keeps the
Phase 4 baseline revalidation disposition consistent with current Level 0
semantics while preserving the frozen baseline JSONL unchanged.

#### 2.3.2 Diversity / Mode Collapse Detection

- **Definition:** Among n=20 samples per cell, how many are textually distinct?
- **Method:** Normalize source (strip comments, normalize whitespace), compute SHA-256 hash, count unique hashes.
- **Metric:** `unique_ratio = count(unique_hashes) / n`
- **Why:** If grammar constraints produce 20 near-identical samples, `pass@5` is misleading because the 5 draws are not independent.
- **Additional signal:** AST structural hash (normalize variable names, hash the AST structure). Two kernels with different variable names but identical structure count as duplicates for the structural metric. Report `unique_ratio_ast` next to `compile@1` for Cluster 1 so mode collapse caused by grammar constraints is visible before Cluster 2/3 spend GPU time on correctness or performance.

```python
import ast
import hashlib

def source_hash(source: str) -> str:
    """Hash normalized source for textual deduplication."""
    normalized = "\n".join(line.strip() for line in source.strip().splitlines() if line.strip() and not line.strip().startswith("#"))
    return hashlib.sha256(normalized.encode()).hexdigest()

def ast_structure_hash(source: str) -> Optional[str]:
    """Hash AST structure for semantic deduplication.
    Normalizes variable names to positional placeholders."""
    try:
        tree = ast.parse(source)
        return hashlib.sha256(ast.dump(tree, annotate_fields=False).encode()).hexdigest()
    except SyntaxError:
        return None
```

---

## 3. The `EvalResult` Schema

This is the single source of truth. Every metric computation reads from this schema. Every cluster writes to it.

```python
from dataclasses import dataclass, field
from typing import Optional
import json
from datetime import datetime

@dataclass
class EvalResult:
    """Immutable evaluation record for one generated kernel.

    Every field below NaN/None conventions:
    - Fields for levels above the achieved level are None (not 0, not False).
    - Boolean fields (parse_success, compile_success, etc.) are True/False/None.
      None means "not evaluated" (level not reached), distinct from False (evaluated and failed).
    - Float fields (speedup, max_abs_diff) are float or None.
      None means "not measured" (gating prevented measurement).
    """

    # ── Identity ──
    kernel_id: int                          # KernelBench problem_id
    kernel_name: str                        # KernelBench problem name
    kernel_class: str                       # "elementwise" | "reduction" | "matmul" | "convolution" | "fused" | "architecture"
    kernelbench_level: int                  # 1, 2, or 3 (KernelBench difficulty level)
    condition: str                          # Factorial condition label, e.g. "none", "G", "C", "G+C", "G+C+P"
    sample_index: int                       # 0..n-1 within the (kernel, condition) cell
    model_id: str                           # Model identifier, e.g. "qwen3-coder-480b"
    run_id: str                             # Unique run identifier for reproducibility
    scale_tier: str                         # "smoke" | "development" | "paper"
    sample_cell_key: str                    # Stable key for the n-sample cell
    grammar_variant: Optional[str] = None   # None | "template_upper_bound" reference | "task_agnostic"

    # ── Metadata ──
    timestamp: str = ""                     # ISO 8601
    gpu_model: str = ""                     # e.g. "NVIDIA A100-SXM4-80GB"
    gpu_clock_mhz: Optional[int] = None     # Locked clock frequency
    dtype_tested: str = "float32"           # "float32" | "float16" | "bfloat16"

    # ── Generation ──
    source: str = ""                        # Generated kernel source code
    tokens_input: int = 0                   # Prompt tokens
    tokens_output: int = 0                  # Generated tokens
    generation_time_s: float = 0.0          # Wall-clock generation time
    source_hash: str = ""                   # SHA-256 of normalized source
    ast_hash: Optional[str] = None          # SHA-256 of AST structure (None if parse fails)

    # ── Level 0: Parse ──
    level_reached: int = -1                 # Highest level passed (0-4), -1 if not evaluated
    parse_success: Optional[bool] = None
    parse_error: Optional[str] = None
    has_triton_decorator: Optional[bool] = None
    signature_valid: Optional[bool] = None

    # ── Level 1: Compile ──
    compile_success: Optional[bool] = None
    compile_error: Optional[str] = None
    compile_time_s: Optional[float] = None  # JIT compilation time

    # ── Level 2: Functional ──
    functional_success: Optional[bool] = None
    correctness_error: Optional[str] = None
    max_abs_diff: Optional[float] = None
    max_rel_diff: Optional[float] = None
    num_test_shapes: Optional[int] = None   # How many input shapes tested
    shapes_passed: Optional[int] = None     # How many passed allclose
    dtype_results: Optional[dict] = None    # {dtype: {passed: bool, max_abs_diff: float}}

    # ── Level 3: Safe ──
    safe_success: Optional[bool] = None
    sanitizer_errors: Optional[list] = None
    sanitizer_tool: Optional[str] = None    # "memcheck" | "racecheck" | "both"

    # ── Level 4: Performant ──
    kernel_time_ms: Optional[float] = None          # Median of 100 runs
    kernel_time_iqr_ms: Optional[float] = None      # IQR for variance reporting
    eager_time_ms: Optional[float] = None
    compile_time_ms: Optional[float] = None          # torch.compile baseline time
    speedup_vs_eager: Optional[float] = None
    speedup_vs_compile: Optional[float] = None
    warmup_iters: int = 25
    timing_iters: int = 100

    # ── Failure Classification ──
    failure_code: Optional[str] = None      # From failure taxonomy, None if Level 4 reached

    # ── Repair (Cluster 2+) ──
    repair_iteration: int = 0               # 0 = initial generation
    repair_budget: int = 5
    repair_converged: Optional[bool] = None
    repair_traces: Optional[list] = None    # List of RepairTrace dicts

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                d[k] = None
            elif isinstance(v, (int, float, str, bool, list, dict)):
                d[k] = v
            else:
                d[k] = str(v)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "EvalResult":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
```

`grammar_variant` is a subcondition of factor `G`, not a new factorial factor.
Use `None` for baseline and non-grammar rows. Use `"template_upper_bound"` reference for
the Cluster 1 template-instantiation diagnostic/reference control and
`"task_agnostic"` for task-agnostic G, the primary grammar condition intended to
represent grammar-guided decoding plus offline semantic post-validation without
task-specific body templates.

Current KernelBench scope is Level 1 only. `kernelbench_level` remains in the
schema because the dataset defines Levels 1, 2, and 3, but Levels 2 (fused
operators) and 3 (full model architectures) are out of scope for this factorial
study. Expanding beyond Level 1 requires explicit grammar coverage and tolerance
tables for the new operator families before results can be compared.

---

## 4. Measurement Protocols

### 4.1 Performance Measurement (Level 4)

**This protocol is non-negotiable for publishable results.**

```python
import torch
import time

def measure_kernel_time(
    kernel_fn,
    input_tensors: list[torch.Tensor],
    warmup: int = 25,
    repeat: int = 100,
) -> dict:
    """Time a Triton kernel using GPU events through the PyTorch runtime.

    Returns dict with median_ms, iqr_ms, all_times_ms.
    """
    torch.cuda.synchronize()

    # Warmup
    for _ in range(warmup):
        kernel_fn(*input_tensors)
    torch.cuda.synchronize()

    # Timed runs
    times = []
    for _ in range(repeat):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)

        start.record()
        kernel_fn(*input_tensors)
        end.record()

        torch.cuda.synchronize()
        times.append(start.elapsed_time(end))  # milliseconds

    times.sort()
    q1 = times[len(times) // 4]
    q3 = times[3 * len(times) // 4]
    median = times[len(times) // 2]

    return {
        "median_ms": median,
        "iqr_ms": q3 - q1,
        "all_times_ms": times,
    }
```

**Environment requirements (enforce in code):**

```python
import subprocess

def lock_gpu_clocks(freq_mhz: int = 1410) -> None:
    """Lock GPU clocks for deterministic benchmarking.
    Call at start of any performance measurement session."""
    subprocess.run(
        ["nvidia-smi", "-lgc", str(freq_mhz)],
        check=True, capture_output=True,
    )

def unlock_gpu_clocks() -> None:
    """Restore default GPU clock behavior."""
    subprocess.run(
        ["nvidia-smi", "-rgc"],
        check=True, capture_output=True,
    )

def get_gpu_info() -> dict:
    """Capture GPU metadata for reproducibility."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,clocks.current.sm,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    parts = result.stdout.strip().split(", ")
    return {
        "gpu_model": parts[0],
        "clock_mhz": int(parts[1]),
        "memory_mb": int(parts[2]),
    }
```

**Run reference and generated Triton kernel through PyTorch in the same process, back-to-back.** Never time them in separate processes — thermal state and GPU scheduler context change between processes.

### 4.2 Compile Check (Level 1) — Triton-Specific

Triton compiles lazily. `@triton.jit` succeeds at decoration time for almost anything. You must trigger actual compilation:

```python
import torch
import triton

def check_compile(source: str, kernel_spec: KernelSpec) -> tuple[bool, Optional[str]]:
    """Verify kernel JIT-compiles by launching with small dummy inputs.

    Returns (success, error_message).
    """
    try:
        # Execute the source to define the function
        exec_globals = {}
        exec(source, exec_globals)

        # Find the triton.jit-decorated function
        kernel_fn = None
        for name, obj in exec_globals.items():
            if hasattr(obj, 'run'):  # triton.jit functions have .run
                kernel_fn = obj
                break

        if kernel_fn is None:
            return False, "No @triton.jit decorated function found in source"

        # Create small dummy inputs matching the spec
        dummy_inputs = kernel_spec.make_dummy_inputs(device="cuda", small=True)

        # Launch with a minimal grid to trigger compilation
        grid = (1,)
        kernel_fn[grid](*dummy_inputs)
        torch.cuda.synchronize()

        return True, None

    except triton.compiler.errors.CompilationError as e:
        return False, f"CompilationError: {str(e)[:500]}"
    except RuntimeError as e:
        return False, f"RuntimeError: {str(e)[:500]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:500]}"
```

### 4.3 Correctness Check (Level 2)

```python
def check_correctness(
    source: str,
    kernel_spec: KernelSpec,
    num_shapes: int = 5,
) -> tuple[bool, dict]:
    """Check numerical correctness against PyTorch reference.

    Tests on multiple random shapes including edge cases.
    Returns (all_passed, details_dict).
    """
    tolerances = get_tolerances(kernel_spec.kernel_class, kernel_spec.dtype)

    shapes = kernel_spec.get_test_shapes(n=num_shapes)  # Includes edge cases
    results = []

    for shape in shapes:
        inputs = kernel_spec.make_inputs(shape, device="cuda")
        reference_output = kernel_spec.run_reference(*inputs)
        generated_output = run_generated_kernel(source, *inputs)

        # Check for NaN/Inf first
        if torch.isnan(generated_output).any():
            results.append({"shape": shape, "passed": False, "error": "output_contains_nan"})
            continue
        if torch.isinf(generated_output).any():
            results.append({"shape": shape, "passed": False, "error": "output_contains_inf"})
            continue

        # Check shape match
        if generated_output.shape != reference_output.shape:
            results.append({
                "shape": shape, "passed": False,
                "error": f"shape_mismatch: expected {reference_output.shape}, got {generated_output.shape}"
            })
            continue

        # Numerical comparison
        abs_diff = (generated_output - reference_output).abs().max().item()
        rel_diff = ((generated_output - reference_output) / (reference_output.abs() + 1e-10)).abs().max().item()
        passed = torch.allclose(
            generated_output, reference_output,
            atol=tolerances["atol"], rtol=tolerances["rtol"]
        )

        results.append({
            "shape": shape,
            "passed": passed,
            "max_abs_diff": abs_diff,
            "max_rel_diff": rel_diff,
        })

    all_passed = all(r["passed"] for r in results)
    max_abs = max((r.get("max_abs_diff", 0.0) for r in results), default=0.0)
    max_rel = max((r.get("max_rel_diff", 0.0) for r in results), default=0.0)

    return all_passed, {
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "num_shapes": num_shapes,
        "shapes_passed": sum(1 for r in results if r["passed"]),
        "per_shape_results": results,
        "error": None if all_passed else results[next(i for i, r in enumerate(results) if not r["passed"])].get("error", "allclose_failed"),
    }
```

### 4.4 Signature Contract Enforcement (Level 0)

Cluster 1 owns the explicit Level 0 then Level 1 ordering. It calls shared
Level 0 parse/signature checks before importing generated code. Runtime
`inspect.signature()` remains a secondary guard after import; it is not the
primary signature authority. Level 1 compile does not implicitly run Level 0.

```python
import ast
import inspect

def check_signature(source: str, kernel_spec: KernelSpec) -> tuple[bool, Optional[str]]:
    """Verify generated function has the correct signature.

    Rejects at parse time, before compilation. This prevents the LLM
    from 'solving' the problem by changing the interface.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    # Find functions with @triton.jit decorator
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            has_jit = any(
                (isinstance(d, ast.Attribute) and d.attr == "jit") or
                (isinstance(d, ast.Name) and d.id == "jit")
                for d in node.decorator_list
            )
            if has_jit:
                generated_params = [arg.arg for arg in node.args.args]
                expected_params = kernel_spec.expected_params

                if generated_params != expected_params:
                    return False, (
                        f"Signature mismatch: expected params {expected_params}, "
                        f"got {generated_params}"
                    )
                return True, None

    return False, "No @triton.jit decorated function found"
```

### 4.5 Memory Safety Check (Level 3)

```python
import subprocess
import tempfile

def check_memory_safety(
    source: str,
    kernel_spec: KernelSpec,
    tools: list[str] = ["memcheck"],
    timeout_s: int = 1800,
) -> tuple[bool, list[str]]:
    """Run compute-sanitizer on the kernel.

    Args:
        tools: List of sanitizer tools to run. Options: "memcheck", "racecheck".
    """
    errors = []

    # Write a runner script that imports and executes the kernel
    runner_code = f'''
import torch
{source}

# Create inputs and run
inputs = {kernel_spec.make_inputs_code()}
# Run the kernel
{kernel_spec.launch_code()}
torch.cuda.synchronize()
print("SANITIZER_RUNNER_OK")
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(runner_code)
        runner_path = f.name

    for tool in tools:
        result = subprocess.run(
            ["compute-sanitizer", f"--tool={tool}", "python", runner_path],
            capture_output=True, text=True, timeout=timeout_s,
        )

        # Parse sanitizer output for errors
        for line in result.stderr.splitlines():
            if "ERROR" in line and "0 errors" not in line:
                errors.append(f"[{tool}] {line.strip()}")

        if result.returncode != 0:
            errors.append(f"[{tool}] Non-zero exit code: {result.returncode}")

    return len(errors) == 0, errors
```

`compute-sanitizer` can be 10-100x slower than an ordinary kernel launch, especially for matmul and fused kernels. The default timeout is intentionally higher than normal compile/correctness timeouts, and final experiments must record `sanitizer_timeout_s` in run metadata. A sanitizer timeout is a Level 3 failure with `failure_code="F3_TIMEOUT"`, not a performance measurement.

---

## 5. Aggregation and Statistical Analysis

### 5.1 Per-Cell Computation

A "cell" is one stable sample identity. At minimum this is
`(kernel_id, condition)`. If dtype, grammar variant, prompt version, or model is
varied inside a run, those fields are part of the cell identity too. Paper-scale
cells have `n=20` `EvalResult` records. Smoke and development cells use the
smaller sample sizes defined in Section 5.2 and must not be mixed into
paper-scale aggregates.

```python
@dataclass
class CellSummary:
    """Aggregated metrics for one (kernel, condition) cell."""
    kernel_id: int
    kernel_class: str
    condition: str
    scale_tier: str
    grammar_variant: Optional[str]
    n_samples: int

    # Correctness
    compile_at_1: float             # compile@1
    pass_at_1: float                # pass@1 (Level 2)
    pass_at_5: float
    pass_at_10: float
    safe_at_1: float                # safe@1 (Level 3)

    # Performance (only from Level 2+ passing samples)
    median_speedup_vs_compile: Optional[float]
    median_speedup_vs_eager: Optional[float]
    fast_at_0: float                # = pass@1 at Level 2
    fast_at_1_0: float              # correct AND speedup >= 1.0
    fast_at_1_2: float              # correct AND speedup >= 1.2
    fast_tc_at_1_0: Optional[float] # correct AND speedup_vs_compile >= 1.0
    fast_tc_at_1_2: Optional[float] # correct AND speedup_vs_compile >= 1.2

    # Repair (Cluster 2+)
    mean_repair_iters_converged: Optional[float]
    convergence_rate: Optional[float]
    repair_efficiency: Optional[float]

    # Diagnostics
    failure_distribution: dict      # {failure_code: count}
    unique_ratio_source: float      # textual diversity
    unique_ratio_ast: float         # structural diversity
    spurious_speedup_rate: float    # must be 0.0 when Level 2 gating is enforced
    interpretation_flags: list[str] # non-fatal analyzer warnings

    # Cost
    mean_tokens_total: float        # input + output
    cost_adjusted_pass1: Optional[float]

    # Statistical
    pass1_ci_lower: float           # 95% bootstrap CI
    pass1_ci_upper: float
```

### 5.2 Scale Tiers and Aggregation Policy

Every `EvalResult` and `RunConfig` must carry a `scale_tier`:

- **smoke:** `n=1`; infrastructure verification only. Smoke results must never be used for design claims.
- **development:** `n=3` to `n=5`; design iteration and directional indicators only.
- **paper:** `n=20`; frozen run and the sole source of reported claims.

Aggregation must reject mixed-scale inputs by default. A cell summary, factorial
model, or paper table cannot combine smoke, development, and paper records unless
the caller opts into a diagnostic mixed-scale mode that is visibly labeled as
non-paper output.

### 5.3 Grammar-Variant Validity and Interpretation

`grammar_variant` is valid only when the grammar factor `G` is active. Baseline
and non-grammar conditions use `None`.

- `"task_agnostic"` may be used for conditions containing `G` when the run is testing grammar-guided decoding plus offline semantic post-validation without task-specific body templates; task-agnostic G is the primary grammar condition.
- `"template_upper_bound"` may be used only for `G` and `G+C` diagnostic/reference rows. The `G+C` case tests whether test-driven feedback helps even when grammar already forces canonical template-shaped solutions.
- `"template_upper_bound"` reference must not be combined with `P`. Compiler/profiler repair on top of an already-converged template solution is methodologically ambiguous and should be rejected by the runner.

Analyzer output should include an interpretation flag, not an error, when:

```python
grammar_variant == "template_upper_bound" and unique_ratio_ast < 0.1  # diagnostic/reference upper-bound control
```

The flag text should be:

```
this cell shows mode collapse — interpret as template instantiation control, not as evidence of task-agnostic G enforcement
```

This codifies the Cluster 1 interpretation rule: template G is a diagnostic/reference upper bound, not evidence that a task-agnostic grammar improves generation.

### 5.4 Bootstrap Confidence Intervals

```python
import numpy as np

def bootstrap_ci(
    successes: int,
    total: int,
    n_bootstrap: int = 10000,
    ci: float = 0.95,
) -> tuple[float, float]:
    """Bootstrap 95% CI for a proportion.

    Used for pass@1, compile@1, etc.
    """
    if total == 0:
        return 0.0, 0.0

    rng = np.random.default_rng(42)  # Fixed seed for reproducibility
    samples = rng.binomial(total, successes / total, size=n_bootstrap) / total
    alpha = (1 - ci) / 2
    return float(np.quantile(samples, alpha)), float(np.quantile(samples, 1 - alpha))
```

### 5.5 Cross-Condition Statistical Comparison — Categorical Metrics

Use Fisher's exact test for categorical pass/fail metrics such as `compile@1`, `pass@1`, `safe@1`, `fast@p`, and `fast_tc@p`. Do not use this test for continuous speedup distributions.

```python
def compute_pairwise_significance(
    cell_summaries: list[CellSummary],
    metric: str = "pass_at_1",
    correction: str = "holm",
) -> list[dict]:
    """Pairwise Fisher exact test with multiple-testing correction.

    Used to determine if differences between conditions are significant.
    Returns list of {condition_a, condition_b, p_value, p_adjusted, significant}.
    """
    from scipy.stats import fisher_exact
    from statsmodels.stats.multitest import multipletests
    from itertools import combinations

    conditions = sorted(set(s.condition for s in cell_summaries))
    pairs = list(combinations(conditions, 2))
    p_values = []

    for ca, cb in pairs:
        # Pool across kernels for this condition pair
        sa = [s for s in cell_summaries if s.condition == ca]
        sb = [s for s in cell_summaries if s.condition == cb]

        successes_a = sum(int(getattr(s, metric) * s.n_samples) for s in sa)
        total_a = sum(s.n_samples for s in sa)
        successes_b = sum(int(getattr(s, metric) * s.n_samples) for s in sb)
        total_b = sum(s.n_samples for s in sb)

        table = [
            [successes_a, total_a - successes_a],
            [successes_b, total_b - successes_b],
        ]
        _, p = fisher_exact(table)
        p_values.append(p)

    # Multiple testing correction
    reject, p_adjusted, _, _ = multipletests(p_values, method=correction)

    results = []
    for i, (ca, cb) in enumerate(pairs):
        results.append({
            "condition_a": ca,
            "condition_b": cb,
            "p_value": p_values[i],
            "p_adjusted": p_adjusted[i],
            "significant": bool(reject[i]),
        })

    return results
```

### 5.6 Cross-Condition Statistical Comparison — Speedup Metrics

Use Mann-Whitney U tests for continuous speedup distributions (`speedup_vs_eager`, `speedup_vs_compile`, `S_tc`) because speedups are ratio-valued, skewed, and usually non-normal. Only include Level 2+ passing samples with finite speedup values.

```python
def compute_speedup_significance(
    results_by_condition: dict[str, list[EvalResult]],
    metric: str = "speedup_vs_compile",
    correction: str = "holm",
) -> list[dict]:
    """Pairwise Mann-Whitney U tests for speedup distributions."""
    from itertools import combinations
    from math import isfinite
    from scipy.stats import mannwhitneyu
    from statsmodels.stats.multitest import multipletests

    pairs = list(combinations(sorted(results_by_condition), 2))
    p_values = []
    raw = []

    for ca, cb in pairs:
        xa = [
            getattr(r, metric)
            for r in results_by_condition[ca]
            if r.functional_success and getattr(r, metric) is not None and isfinite(getattr(r, metric))
        ]
        xb = [
            getattr(r, metric)
            for r in results_by_condition[cb]
            if r.functional_success and getattr(r, metric) is not None and isfinite(getattr(r, metric))
        ]
        if not xa or not xb:
            p = 1.0
        else:
            _, p = mannwhitneyu(xa, xb, alternative="two-sided")
        p_values.append(p)
        raw.append((ca, cb, len(xa), len(xb), p))

    reject, p_adjusted, _, _ = multipletests(p_values, method=correction)
    return [
        {
            "condition_a": ca,
            "condition_b": cb,
            "n_a": n_a,
            "n_b": n_b,
            "p_value": p,
            "p_adjusted": p_adjusted[i],
            "significant": bool(reject[i]),
        }
        for i, (ca, cb, n_a, n_b, p) in enumerate(raw)
    ]
```

### 5.7 Factorial Interaction Analysis

The central thesis question is answered by fitting factorial models over the eight canonical cells: `none`, `G`, `C`, `P`, `G+C`, `G+P`, `C+P`, and `G+C+P`. Main effects alone answer whether each mechanism helps in isolation; interaction terms answer whether mechanisms compose additively or interfere.

For current Cluster 2 paper claims, the canonical analyzer is
`shared/analysis/factorial.py`. Its default primary response is Level 2
`functional_success`, not `compile_success`. The primary Cluster 2 comparisons
are paired by replay-control seed identity: `C` versus frozen `none`, and
`G+C` versus frozen `G`. These paired comparisons must use matched-cell
statistics, paired bootstrap confidence intervals, McNemar-style binary
discordance p-values, and Holm correction for the planned paired tests.

`compile_success` factorial output is secondary structural-validity diagnostic
output only. It may be emitted by the same analyzer when explicitly requested,
but it must not be used as the headline Cluster 2 result.

For the current week/iteration/early testing cycle, the valid current design is
the temporary 2² subset over G and C: `none`, `G`, `C`, and `G+C`. The analyzer
must mark `P`, `G+P`, `C+P`, and `G+C+P` as `not_populated` and describe those
P-containing cells as deferred for this iteration rather than treating them as
failures or blocking current Cluster 2 tables. Current 2² outputs must not be
described as completion of the full factorial. The full 2³ factorial over G, C,
and P remains the defined project goal; this is a current-status scope
statement, not a methodology realignment.

For binary outcomes (`compile_success`, `functional_success`, `fast_tc@1.0`), use a logistic model:

```
logit(y) ~ G + C + P + G:C + G:P + C:P + G:C:P + kernel_class + dtype
```

For continuous Level 4 speedups, use log-speedup as the response:

```
log(speedup_vs_compile) ~ G + C + P + G:C + G:P + C:P + G:C:P + kernel_class + dtype
```

Interpretation:

- Positive main effect: a factor improves the metric when averaged over the other factors.
- Negative two-way interaction: two mechanisms underperform the additive expectation, indicating interference.
- Positive two-way interaction: two mechanisms reinforce each other beyond additivity.
- Significant three-way interaction: the full stack behaves differently than all pairwise effects predict.

---

## 6. Cluster-Specific Evaluation Contracts

### 6.1 Cluster 1 (Grammar Constraints - Factor G)

**What Cluster 1 evaluates:** Levels 0 and 1 only.
**Primary metric:** `compile@1`
**Diagnostic metric:** `pass@1` at Level 2 via KernelBench post-hoc (not in the Cluster 1 code path).

**Cluster 1 calls:**
```python
result = run_eval_pipeline(source, kernel_spec, RunConfig(
    max_level=1,
    enable_sanitizer=False,
    enable_timing=False,
    condition="G" or "none",
))
```

**Forbidden in Cluster 1 code path:**
- `torch.allclose` or any numerical comparison
- `measure_kernel_time` or any timing call
- `compute-sanitizer` invocation
- Any repair/feedback loop
- Any reference to `speedup`, `fast_p`, `repair_iters`

**Boundary enforcement:** The `FORBIDDEN_PATTERNS` scanner checks every `.py` file in `cluster1/` for these symbols. Violations are CI-blocking.

### 6.2 Cluster 2 (Test-Driven Feedback - Factor C)

**What Cluster 2 evaluates:** Levels 0, 1, and 2. Plus repair_iters.
**Primary metric:** `pass@1`, `pass@5` at Level 2.
**Secondary metric:** `repair_iters`, `convergence_rate`, `repair_efficiency`.

**Cluster 2 calls:**
```python
result = run_eval_pipeline(source, kernel_spec, RunConfig(
    max_level=2,
    enable_sanitizer=False,
    enable_timing=False,
    condition="C" or "G+C",
    repair_budget=5,
))
```

**Forbidden in Cluster 2 code path:**
- `measure_kernel_time` or any timing call
- `compute-sanitizer` invocation
- Any reference to `speedup`, `fast_p`, roofline metrics

### 6.3 Cluster 3 (Compiler/Profiler Repair - Factor P)

**What Cluster 3 evaluates:** Levels 0, 1, 2, and 4. Level 3 safety remains optional/deferred unless a separate safety contract enables it.
**Primary metric:** `speedup_vs_compile` (`S_tc`), `fast@1.0`, `fast@1.2`.
**Secondary metric:** compiler/profiler repair iterations plus performance-aware repair.

**Cluster 3 calls:**
```python
result = run_eval_pipeline(source, kernel_spec, RunConfig(
    max_level=4,
    enable_sanitizer=False,
    enable_timing=True,
    condition="P" or "G+C+P" or any condition with P,
    repair_budget=5,
    warmup_iters=25,
    timing_iters=100,
    lock_gpu_clocks=True,
    clock_freq_mhz=1410,
))
```

---

## 7. File Structure

```
shared/
  eval/
    __init__.py               # Exports run_eval_pipeline, EvalResult, CellSummary
    schema.py                 # EvalResult, RepairTrace, CellSummary dataclasses
    pipeline.py               # run_eval_pipeline() — the gated evaluation function
    levels/
      __init__.py
      level0_parse.py         # check_parse(), check_signature()
      level1_compile.py       # check_compile()
      level2_correctness.py   # check_correctness()
      level3_safety.py        # check_memory_safety()
      level4_performance.py   # measure_performance(), lock_gpu_clocks()
    tolerances.py             # Per-op tolerance table
    failure_taxonomy.py       # classify_failure()
    diversity.py              # source_hash(), ast_structure_hash(), unique_ratio()
    metrics/
      __init__.py
      pass_at_k.py            # pass_at_k(), compile_at_1()
      fast_at_p.py            # fast_at_p()
      speedup.py              # compute_speedup(), geometric_mean_speedup()
      repair.py               # repair_iters metrics, repair_efficiency
      cost.py                 # cost_adjusted_pass1
    aggregation.py            # build_cell_summary(), aggregate_across_kernels()
    statistics.py             # bootstrap_ci(), Fisher tests, Mann-Whitney U tests
    factorial.py              # 2³ main-effect and interaction-effect models
    reporting/
      __init__.py
      tables.py               # Generate paper-ready LaTeX/markdown tables
      plots.py                # Generate matplotlib figures for paper
    gpu_utils.py              # lock_gpu_clocks(), get_gpu_info()
    constants.py              # WARMUP_ITERS=25, TIMING_ITERS=100, SAMPLE_SIZE=20, REPAIR_BUDGET=5
```

---

## 8. RunConfig — Cluster-Aware Evaluation Configuration

```python
@dataclass
class RunConfig:
    """Configuration for an evaluation run. Each cluster sets this differently."""

    condition: str                      # "none" | "G" | "C" | "P" | "G+C" | "G+P" | "C+P" | "G+C+P"
    scale_tier: str = "smoke"           # "smoke" | "development" | "paper"
    max_level: int = 4                  # Highest level to evaluate (1 for C1, 2 for C2, 4 for C3)
    enable_sanitizer: bool = False      # Level 3 gate
    enable_timing: bool = False         # Level 4 gate
    repair_budget: int = 0             # 0 = no repair (Cluster 1), 5 = standard (Cluster 2/3)
    warmup_iters: int = 25
    timing_iters: int = 100
    lock_gpu_clocks: bool = False
    clock_freq_mhz: int = 1410
    sample_size: int = 20               # n per (kernel, condition) cell
    kernel_ids: list[int] = field(default_factory=list)
    kernel_count: int = 0
    model_id: str = ""
    seed_schedule: list[int] = field(default_factory=list)
    grammar_variant: Optional[str] = None
    dtypes: list[str] = field(default_factory=lambda: ["float32"])
```

`scale_tier` is required for every run. Aggregation/reporting code should reject
mixed-scale inputs by default. Development-scale reports may exist as explicitly
labeled diagnostics, but paper tables must be generated only from `paper`
records.

`grammar_variant` is required when the grammar factor is active and omitted
otherwise. The variant is part of the cell identity but does not change the
factor label: `template_upper_bound` reference under `G` is still canonical
condition `G`, with the variant recorded as a diagnostic/reference subcondition.
Paper-facing labels must render it as template G reference, not plain `G`.

---

## 9. Output Format

### 9.1 Per-Run Output

Each experimental run produces:

```
results/
  {run_id}/
    config.json               # RunConfig + model_id + timestamp + git_hash
    eval_results.jsonl        # One EvalResult JSON per line, one per generation
    cell_summaries.json       # Aggregated CellSummary per (kernel, condition)
    significance_tests.json   # Pairwise statistical comparisons
    metadata.json             # GPU info, clock settings, software versions
```

### 9.2 Paper Table Generator

The `reporting/tables.py` module reads `cell_summaries.json` and produces:

**Table 1: Correctness by Condition and Kernel Class**

```
| Condition | Elementwise pass@1 | Reduction pass@1 | MatMul pass@1 | Convolution pass@1 | Aggregate pass@1 |
|-----------|-------------------|------------------|---------------|---------------------|------------------|
| none      | 0.XX (±0.XX)      | 0.XX (±0.XX)     | 0.XX (±0.XX)  | 0.XX (±0.XX)        | 0.XX (±0.XX)     |
| G         | 0.XX (±0.XX)      | 0.XX (±0.XX)     | 0.XX (±0.XX)  | 0.XX (±0.XX)        | 0.XX (±0.XX)     |
| C         | ...               | ...              | ...           | ...                 | ...              |
| G+C       | ...               | ...              | ...           | ...                 | ...              |
| P         | ...               | ...              | ...           | ...                 | ...              |
| G+C+P     | ...               | ...              | ...           | ...                 | ...              |
```

**Table 2: Performance (Level 4, Cluster 3 only)**

```
| Condition | Median S_tc | fast@1.0 | fast@1.2 | fast_tc@1.0 | fast_tc@1.2 | Geo-mean Speedup |
```

**Table 3: Repair Efficiency (Cluster 2+)**

```
| Condition | Mean repair_iters | Convergence rate | Repair efficiency | Cost-adjusted pass@1 |
```

---

## 10. Validation Checklist

Before any experimental run, the following must pass:

```python
def preflight_check(run_config: RunConfig) -> list[str]:
    """Return list of failures. Empty list = ready to run."""
    failures = []

    # 1. GPU runtime available
    if not torch.cuda.is_available():
        failures.append("GPU runtime not available")

    # 2. GPU clocks lockable (if timing enabled)
    if run_config.enable_timing:
        try:
            lock_gpu_clocks(run_config.clock_freq_mhz)
            unlock_gpu_clocks()
        except subprocess.CalledProcessError:
            failures.append("Cannot lock GPU clocks — timing results will be noisy")

    # 3. compute-sanitizer available (if Level 3 enabled)
    if run_config.enable_sanitizer:
        result = subprocess.run(["compute-sanitizer", "--version"],
                               capture_output=True, text=True)
        if result.returncode != 0:
            failures.append("compute-sanitizer not found")

    # 4. Triton importable
    try:
        import triton
    except ImportError:
        failures.append("triton not importable")

    # 5. Reference baselines measurable
    if run_config.enable_timing:
        try:
            import torch._dynamo
            compiled = torch.compile(lambda x: x + 1, mode="max-autotune")
            compiled(torch.zeros(16, device="cuda"))
        except Exception as e:
            failures.append(f"torch.compile baseline broken: {e}")

    # 6. Sample size meets scale-tier minimum
    if run_config.scale_tier == "paper":
        if run_config.sample_size < 20:
            failures.append(f"Paper sample size {run_config.sample_size} < 20 minimum")
    elif run_config.scale_tier == "development":
        if run_config.sample_size < 3:
            failures.append(f"Development sample size {run_config.sample_size} < 3 minimum")
    elif run_config.scale_tier == "smoke":
        pass
    else:
        failures.append(f"Unknown scale_tier: {run_config.scale_tier}")

    # 7. Grammar variant is a valid subcondition of factor G
    valid_variants = {None, "task_agnostic", "template_upper_bound"}  # template_upper_bound reference
    if run_config.grammar_variant not in valid_variants:
        failures.append(f"Unknown grammar_variant: {run_config.grammar_variant}")

    active_factors = set(run_config.condition.split("+")) if run_config.condition not in {"none", "baseline"} else set()
    if run_config.grammar_variant is not None and "G" not in active_factors:
        failures.append("grammar_variant requires condition containing G")
    if run_config.grammar_variant == "template_upper_bound" and run_config.condition not in {"G", "G+C"}:  # reference only
        failures.append("template_upper_bound reference is valid only for G and G+C")

    return failures
```

---

## 11. Constants (Non-Negotiable)

```python
# shared/eval/constants.py

# Sampling
SMOKE_SAMPLE_SIZE = 1                 # infrastructure verification only
DEVELOPMENT_MIN_SAMPLE_SIZE = 3       # design iteration lower bound
DEVELOPMENT_MAX_SAMPLE_SIZE = 5       # design iteration upper bound
PAPER_MIN_SAMPLE_SIZE = 20            # n per (kernel, condition) cell for reported claims
PASS_K_VALUES = [1, 5, 10]            # Report these k values

# Timing
WARMUP_ITERS = 25            # Before measurement
TIMING_ITERS = 100           # Measured iterations
DEFAULT_CLOCK_MHZ = 1410     # GPU clock lock frequency

# Repair
REPAIR_BUDGET = 5            # Max feedback iterations
REPAIR_CONVERGENCE_LEVEL = 2 # Must reach Level 2 to count as converged

# Tolerance (see tolerances.py for per-op values)
DEFAULT_ATOL = 1e-3
DEFAULT_RTOL = 1e-3

# Diversity
DUPLICATE_THRESHOLD = 0.9    # Flag if unique_ratio < this

# Statistical
BOOTSTRAP_SAMPLES = 10000
CI_LEVEL = 0.95
SIGNIFICANCE_ALPHA = 0.05
MULTIPLE_TESTING_METHOD = "holm"

# fast@p thresholds
FAST_P_VALUES = [0.0, 1.0, 1.2]
FAST_TC_P_VALUES = [1.0, 1.2]
```

---

## 12. Integration with KernelBench

The `shared/eval/` package is independent of KernelBench's internal evaluator. The integration point is the `KernelSpec` adapter:

```python
# shared/eval/kernelbench_adapter.py

from datasets import load_dataset

def load_kernel_spec(problem_id: int, level: int = 1) -> KernelSpec:
    """Load a KernelBench problem as a KernelSpec for our eval pipeline.

    The KernelSpec wraps the PyTorch reference code and provides:
    - make_inputs(): generates test tensors
    - run_reference(): runs PyTorch forward() as ground truth
    - expected_params: the function signature the LLM must match
    - kernel_class: categorization for tolerance lookup
    """
    ds = load_dataset("ScalingIntelligence/KernelBench", split=f"level_{level}")
    row = next(r for r in ds if r["problem_id"] == problem_id)

    return KernelSpec(
        problem_id=row["problem_id"],
        name=row["name"],
        level=row["level"],
        reference_code=row["code"],
        kernel_class=classify_kernel(row["name"]),  # "elementwise" | "reduction" | "matmul" | "convolution" | etc.
    )

def classify_kernel(name: str) -> str:
    """Map KernelBench problem name to kernel class for tolerance lookup."""
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["relu", "gelu", "sigmoid", "tanh", "silu", "activation", "pointwise"]):
        return "elementwise"
    if any(kw in name_lower for kw in ["softmax", "layernorm", "layer_norm", "sum", "mean", "norm", "reduce"]):
        return "reduction"
    if any(kw in name_lower for kw in ["conv", "convolution"]):
        return "convolution"
    if any(kw in name_lower for kw in ["matmul", "matrix_mul", "gemm", "linear"]):
        return "matmul"
    return "fused"  # Default for Level 2+ fused ops
```

Convolution is deliberately separate from MatMul. If convolution problems enter
the study later, they must use the `convolution` tolerance row and should be
reported as their own class because their memory access patterns differ from
GEMM-style kernels.

**KernelBench's own evaluator** is run separately as a post-hoc diagnostic (see Cluster 1 contract). Its `fast_0`, `fast_1`, `fast_2` results are stored in `results/{run_id}/kernelbench/` and never referenced by Cluster 1 analysis code.

---

## 13. What This Document Does NOT Cover

These are explicitly out of scope and covered by other contracts:

1. **Prompt templates** — how the LLM is instructed to generate kernels.
2. **Grammar definitions** — the GBNF grammar for constrained decoding.
3. **Model selection** — which LLM is used (treated as `[MODEL_PLACEHOLDER]`).
4. **Modal infrastructure** — how evaluation runs on remote GPUs.
5. **KernelBench problem selection** — which specific problems from the 250 are used.
6. **Autotune policy** — whether the LLM writes `@triton.autotune` blocks.

These decisions are made in their respective cluster contracts and are orthogonal to the metric definitions in this document.

---

## 14. Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-06 | Initial specification |
