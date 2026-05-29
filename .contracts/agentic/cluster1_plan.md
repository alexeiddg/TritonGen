# Cluster 1 Plan

## Phase A Assessment

### Contract Summary

- Contract read: `.contracts/agentic/cluster1_contract.md`. The required implementation shape is `cluster1/` with `grammar/`, `constraints/`, `generation/`, `validation/`, `data/`, `results/`, `experiments/`, `notebooks/`, and `tests/`.
- Layer split: Grammar layer supplies standalone `triton_kernel.gbnf`; hardware checker enforces context-dependent constraints; constrained decoding uses XGrammar with `grammar_active` as the sole experimental toggle; validation uses dummy Triton launches.
- Correctness ladder for Cluster 1 stops at compile acceptance: `compile_success=True` only from actual Triton JIT launch. Numerical correctness, compiler feedback repair loops, and profiler/performance feedback are out of scope.
- Result logging must support pass@k using compile success only, n>=20 generations per `(kernel_class, grammar_active)` cell, `unique_solution_hash`, and `masked_token_rate`.
- Boundary rule: no `torch.allclose`, `torch.testing`, profiler/timing instrumentation, Nsight/NVML, repair/retry/re-prompt loops, speedup calculations, or numerical reference comparisons in the Cluster 1 code path.

### Codebase Map

| File path | Purpose | DoD items covered | Status |
|---|---|---:|---|
| `.contracts/agentic/cluster1_contract.md` | Authoritative Cluster 1 contract | #1-#10 | readable |
| `README.md` | Current Phase 1 project overview and quickstart | #1, #2, #3, #5, #6, #10 partial documentation | readable |
| `requirements.txt` | Dependency list: xgrammar, triton, torch, transformers, pytest, lark | #1, #2, #3 partial dependency support | readable |
| `configs/default.yaml` | Current smoke config with hardcoded model, grammar path, 2 tasks, 10 seeds | #5, #6 partial | readable |
| `grammars/triton_kernel.gbnf` | Existing permissive GBNF grammar | #1 partial | readable |
| `grammars/README.md` | Existing grammar design notes | #1 partial | readable |
| `src/grammar_loader.py` | XGrammar compile/cache and private acceptance helper | #1, #2 partial | readable |
| `src/constrained_generator.py` | Current grammar on/off generation entry point | #2, #4, #5, #6 partial | readable |
| `src/compile_gate.py` | Current subprocess compile gate with CUDA launch harnesses | #3 partial, #8 violation | readable |
| `src/result.py` | Current `GenerationResult` and JSONL append helper | #4 partial | readable |
| `src/prompts.py` | Current prompt specs for `vector_add` and `relu` | #9 partial | readable |
| `src/diagnostics.py` | Current failure taxonomy and baseline summaries | #5 partial, #7 missing, #8 violation | readable |
| `src/__init__.py` | Package marker/version | none | readable |
| `scripts/run_smoke.py` | Current smoke runner for grammar/unconstrained generation | #5, #6 partial, #8 violation | readable |
| `tests/conftest.py` | Test import path setup | test support | readable |
| `tests/test_grammar_loader.py` | Grammar fixture acceptance/rejection tests through XGrammar helper | #1 partial | readable |
| `tests/test_compile_gate.py` | Compile gate tests; CUDA positives auto-skip without GPU | #3 partial | readable |
| `tests/fixtures/README.md` | Fixture inventory | #1 partial | readable |
| `tests/fixtures/valid_kernels/abs.py` | Valid elementwise Triton fixture | #1 partial | readable |
| `tests/fixtures/valid_kernels/axpy.py` | Valid elementwise Triton fixture | #1 partial | readable |
| `tests/fixtures/valid_kernels/copy.py` | Valid elementwise Triton fixture | #1 partial | readable |
| `tests/fixtures/valid_kernels/relu.py` | Valid elementwise Triton fixture | #1, #9 partial | readable |
| `tests/fixtures/valid_kernels/scalar_mul.py` | Valid elementwise Triton fixture | #1 partial | readable |
| `tests/fixtures/valid_kernels/vector_add.py` | Valid elementwise Triton fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/has_if_statement.py` | Negative grammar fixture; currently rejects control flow | #1 partial | readable |
| `tests/fixtures/invalid_kernels/imports_out_of_order.py` | Negative grammar fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/markdown_fence.py` | Negative grammar fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/missing_jit_decorator.py` | Negative grammar fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/missing_launcher.py` | Negative grammar fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/missing_triton_import.py` | Negative grammar fixture | #1 partial | readable |
| `tests/fixtures/invalid_kernels/prose_preamble.py` | Negative grammar fixture | #1 partial | readable |
| `experiments/README.md` | Existing notebook documentation | #5, #6, #10 partial | readable |
| `experiments/00_baseline.ipynb` | Current unconstrained baseline notebook for 2 tasks x 10 seeds | #5 partial, #10 partial | readable |
| `experiments/01_constrained_generation.ipynb` | Current side-by-side constrained/unconstrained sandbox | #6 partial, #10 partial | readable |

### DoD Inventory

| DoD # | Status | Evidence | Gap |
|---:|---|---|---|
| 1 | PARTIAL | `grammars/triton_kernel.gbnf` exists. `tests/test_grammar_loader.py` accepts 6 valid fixtures and rejects 7 invalid fixtures through `grammar_accepts()`. | Missing contract path `cluster1/grammar/triton_kernel.gbnf`. Grammar is permissive over arbitrary dotted calls and does not whitelist required Triton ops. Missing `tl.dot`, `tl.atomic_add`, `tl.sum`, `tl.max`, `tl.zeros`, `tl.full`, `tl.exp`, `tl.log`, `tl.sqrt`, `tl.where` as explicit call forms. Missing control-flow support. Missing `@triton.autotune` fixed-config grammar. Missing required rejection fixtures for wrong-arity `tl.store`, missing `tl.program_id`, free-form autotune config, and launch wrapper missing grid. Missing Lark validator file `cluster1/grammar/triton_kernel_validator.py`. |
| 2 | PARTIAL | `src/grammar_loader.py:53` compiles/caches grammar. `src/constrained_generator.py:56` has `grammar_active` and adds logits processor only when true. | Missing contract path `cluster1/generation/*`. No hardware checker. No tokenizer vocab alignment test. No verified XGrammar `GrammarMatcher` lifecycle. No `masked_token_rate`. Current `fresh_logits_processor()` uses `xgr.contrib.hf.LogitsProcessor(self.compiled)` with no explicit matcher or mask metrics. |
| 3 | PARTIAL | `src/compile_gate.py:148` writes source to temp module and invokes a launcher in subprocess. Harnesses exist for `vector_add` and `relu`. | Missing contract path `cluster1/validation/compile_check.py`. No `inspect.signature()` validation before compile. No separate `CompilationError` vs `RuntimeError`; runner catches broad `Exception`. No fp32/fp16/bf16 matrix. No 5-shape distribution per dtype. No reduction/matmul harnesses. No `n_shapes_tested`. |
| 4 | PARTIAL | `src/result.py:31` defines `GenerationResult`; `append_jsonl()` exists. | Missing required fields from contract/session: `compile_error_type`, `compile_error_msg`, `masked_token_rate`, `unique_solution_hash`, `kernel_class`, `kernel_name`, `dtype`, `n_shapes_tested`, `generation_seed`, `temperature`, `run_id`, `timestamp_utc`. Current fields include out-of-scope timing fields `generation_time_s` and `compile_time_s`. |
| 5 | PARTIAL | `experiments/00_baseline.ipynb` and `scripts/run_smoke.py` can run unconstrained rows. | Only `vector_add` and `relu`; no reduction or matmul. Config has 10 seeds, not n>=20 per kernel class. No evidence of completed logged baseline result files. No KernelBench-backed classes. |
| 6 | PARTIAL | `scripts/run_smoke.py` loops over conditions `["unconstrained", "grammar"]`; `experiments/01_constrained_generation.ipynb` runs grammar ON vs OFF. | Not n>=20 per kernel class. No reduction/matmul. No `masked_token_rate`. No result schema required by DoD. No completed constrained logs. |
| 7 | MISSING | No pass@k/null-hypothesis implementation found. `src/diagnostics.py` computes compile success rate and grammar accept rate only. | Add HumanEval pass@k estimator, unique solution rate, and anomaly/null-hypothesis report comparing grammar OFF failures to grammar ON eliminations. |
| 8 | MISSING | No numerical comparison, Nsight, NVML, or repair loops found. Boundary violations do exist: timing fields and timers are in Cluster 1 code path. | Remove timing instrumentation from Cluster 1 path: `src/constrained_generator.py:10,97-105`, `src/compile_gate.py:30,93,177-202`, `scripts/run_smoke.py:21,165,185`, `src/diagnostics.py:99,113,152-153`. Add automated boundary scanner. |
| 9 | PARTIAL | `src/prompts.py` has prompt specs for `vector_add` and `relu`; fixtures include elementwise kernels. | Missing KernelBench dataset integration. Missing `cluster1/data/kernels/elementwise_relu.py`, `reduction_softmax.py`, `matmul_tiled_gemm.py`. Dataset decision is now resolved to `ScalingIntelligence/KernelBench`, but implementation is still missing. Missing shape distributions per class. |
| 10 | PARTIAL | `experiments/00_baseline.ipynb` and `experiments/01_constrained_generation.ipynb` exist. | Missing contract path `cluster1/notebooks/cluster1_demo.ipynb`. Existing notebooks hardcode model IDs, cover only current Phase 1 tasks, do not demonstrate final schema, pass@k, dtype compile matrix, or annotated result record. |

### Cluster Boundary Scan

- VIOLATION: `src/constrained_generator.py`, `generate()`, lines 97-105. Uses `time.perf_counter()` and records `generation_time_s`. Contract Section 5 forbids timing measurement in Cluster 1.
- VIOLATION: `src/compile_gate.py`, `CompileGateResult` and `run_compile_gate()`, lines 89-94 and 177-202. Uses `time.perf_counter()` and records `elapsed_s`. Contract Section 5 forbids timing measurement in Cluster 1.
- VIOLATION: `scripts/run_smoke.py`, `main()`, lines 165 and 185. Measures total run duration with `time.perf_counter()`.
- VIOLATION: `src/diagnostics.py`, `BaselineSummary` and `compute_summary()`, lines 99, 113, 152-153. Computes and prints mean generation time.
- No `torch.allclose`, `torch.testing`, Nsight Compute, NVML, profiler API, repair loop, retry-on-error LLM feedback, or re-prompt loop detected in scanned files.

### Placeholder Status

Development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`. It is the iteration model for fast T4 validation runs, not the final thesis reporting model.

Dataset placeholder: RESOLVED as `ScalingIntelligence/KernelBench`. No implementation currently loads it; existing local fixtures and `src/prompts.py` specs are not a KernelBench dataset integration.

---

## Phase B Plan

---

## Phase 0: Already Implemented

**DoD items:** None

### Objective

Record that no Cluster 1 DoD item is fully complete; existing code may be mined for ideas but must not be treated as contract-compliant.

### Prerequisite

None.

### Tasks

#### Task 0.1

- **File:** N/A
- **Action:** CREATE
- **Target:** N/A
- **Signature:** N/A
- **Detail:** No DoD item is DONE. Do not skip any implementation phase. Existing partial files are outside the required `cluster1/` contract layout and fail one or more mandatory clauses.
- **DoD item:** N/A
- **Placeholder:** None

### Completion Criterion

Confirm Phase A inventory marks no DoD item as DONE.

---

## Phase 1: Grammar Specification

**DoD items:** #1

### Objective

Create the standalone contract grammar that constrains raw Triton Python structure and required Triton API call forms before any validator or decoding integration depends on it.

### Prerequisite

None.

### Tasks

#### Task 1.1

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** CREATE
- **Target:** `root`
- **Signature:** `root ::= module`
- **Detail:** Define the top-level GBNF module as optional imports, optional fixed `@triton.autotune`, required `@triton.jit` kernel function, and required launch wrapper function. The grammar must accept only raw Python/Triton code and reject markdown/prose. Contract clauses: Section 2.1 required structure, Section 2.2 grammar file specification, G1.
- **DoD item:** #1
- **Placeholder:** None

#### Task 1.2

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** MODIFY
- **Target:** `triton-core-call`
- **Signature:** `triton-core-call ::= tl-load-call | tl-store-call | tl-arange-call | tl-program-id-call | tl-zeros-call | tl-full-call`
- **Detail:** Add explicit call productions for `tl.load(ptr, mask=..., other=...)`, `tl.store(ptr, value, mask=...)`, `tl.arange(start, end)`, `tl.program_id(axis)`, `tl.zeros(shape, dtype=...)`, and `tl.full(shape, value, dtype=...)`. `tl.store` must require exactly pointer, value, and optional `mask=`; wrong arity must be syntactically rejected. `tl.program_id(axis)` must restrict axis to `0 | 1 | 2`. Also add `tl.constexpr` as a type annotation terminal. It must be accepted in kernel function parameter annotations (e.g., `BLOCK_SIZE: tl.constexpr`) and as a standalone expression. It is not a callable — do not place it in `triton-core-call` or `triton-compute-call`. Add a dedicated `constexpr-annotation` terminal to the grammar and verify it is accepted in the `GOOD_KERNELS` fixture set in Task 2.4. Contract clauses: Section 2.2.1 required core ops, G2.
- **DoD item:** #1
- **Placeholder:** None

#### Task 1.3

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** MODIFY
- **Target:** `triton-compute-call`
- **Signature:** `triton-compute-call ::= tl-dot-call | tl-atomic-add-call | tl-sum-call | tl-max-call | tl-math-call | tl-where-call`
- **Detail:** Add explicit productions for `tl.dot(a, b, allow_tf32=...)`, `tl.atomic_add(ptr, val, mask=...)`, `tl.sum(x, axis=...)`, `tl.max(x, axis=...)`, `tl.exp(x)`, `tl.log(x)`, `tl.sqrt(x)`, and `tl.where(cond, x, y)`. Do not permit arbitrary hallucinated `tl.*` names through the Triton-call production. Contract clauses: Section 2.2.1 compute ops, G2.
- **DoD item:** #1
- **Placeholder:** None

#### Task 1.4

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** MODIFY
- **Target:** `control-flow-stmt`
- **Signature:** `control-flow-stmt ::= if-stmt | for-range-stmt`
- **Detail:** Add indented `if`/`else` block grammar and `for` loops over block ranges such as `for k in range(0, K, BLOCK_K):`. The grammar must support nested statement blocks while keeping launch wrapper structure mandatory. Include explicit test cases for nested `for`-loops iterating over K blocks in the Phase 2 GOOD_KERNELS fixture set; this is the most common GBNF indentation failure point and must be verified before the validator is trusted. Contract clauses: Section 2.2.1 control flow, G2.
- **DoD item:** #1
- **Placeholder:** None

#### Task 1.5

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** MODIFY
- **Target:** `autotune-decorator`
- **Signature:** `autotune-decorator ::= "@triton.autotune(configs=" fixed-config-list ", key=" string-list ")" nl`
- **Detail:** Add optional `@triton.autotune` decorator before `@triton.jit`. The grammar must only accept fixed config lists emitted by the prompt contract, not free-form generated configs. Config values must restrict `BLOCK_M`, `BLOCK_N`, `BLOCK_K`, `BLOCK_SIZE`, `num_warps`, and `num_stages` to allowed literals. The set of allowed literal values must exactly match those defined in `cluster1/data/prompts/prompt_contract.py`; divergence between grammar and prompt contract causes silent degenerate outputs. This co-validation is enforced by Task 6.9. Contract clauses: Section 2.2.1 autotuning, G3.
- **DoD item:** #1
- **Placeholder:** None

#### Task 1.6

- **File:** `cluster1/grammar/triton_kernel.gbnf`
- **Action:** MODIFY
- **Target:** `launch-wrapper`
- **Signature:** `launch-wrapper ::= bracket-launch-wrapper | run-launch-wrapper`
- **Detail:** Add wrapper grammar for both `kernel[(grid,)](...)` and `kernel.run(...)`. The wrapper must require a grid expression before invoking the JIT kernel. A wrapper that directly calls the kernel without grid syntax must be rejected. Contract clauses: Section 2.2.1 launch wrapper, G4.
- **DoD item:** #1
- **Placeholder:** None

### Completion Criterion

Manually verify `cluster1/grammar/triton_kernel.gbnf` exists and contains productions named `triton-core-call`, `triton-compute-call`, `control-flow-stmt`, `autotune-decorator`, and `launch-wrapper`. Note: grammar/prompt contract co-validation (Task 6.9) runs in Phase 6 after `prompt_contract.py` exists.

---

## Phase 2: Grammar Offline Validator

**DoD items:** #1

### Objective

Add offline grammar validation and required acceptance/rejection fixtures so the grammar is testable before model generation.

### Prerequisite

Phase 1.

### Tasks

#### Task 2.1

- **File:** `cluster1/grammar/triton_kernel_validator.py`
- **Action:** CREATE
- **Target:** `GrammarValidationReport`
- **Signature:** `@dataclass(frozen=True) class GrammarValidationReport: grammar_path: Path; lark_compiles: bool; n_accept_cases: int; n_reject_cases: int; errors: list[str]`
- **Detail:** Define the validation result object returned by offline validation. It must contain all parse/build failures without raising unless called from CLI. Contract clauses: Section 3.2 grammar validation, G5.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.2

- **File:** `cluster1/grammar/triton_kernel_validator.py`
- **Action:** CREATE
- **Target:** `validate_grammar_file`
- **Signature:** `def validate_grammar_file(grammar_path: Path = DEFAULT_GBNF_PATH) -> GrammarValidationReport`
- **Detail:** Load `cluster1/grammar/triton_kernel.gbnf`, compile its Lark-equivalent grammar using `lark.Lark(..., parser="lalr", start="root")`, and return `GrammarValidationReport`. If the grammar cannot be converted or compiled, populate `errors` with exact exception text. Contract clauses: Section 3.2 item 5, G5.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.3

- **File:** `cluster1/grammar/triton_kernel_validator.py`
- **Action:** CREATE
- **Target:** `accepts_source`
- **Signature:** `def accepts_source(source: str, grammar_path: Path = DEFAULT_GBNF_PATH) -> bool`
- **Detail:** Parse a candidate kernel source using the offline Lark validator and return `True` only when the entire source is accepted. Do not import torch, triton, xgrammar, or execute generated code in this validator. Contract clauses: Section 3.2 acceptance tests, G6.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.4

- **File:** `cluster1/grammar/test_grammar_acceptance.py`
- **Action:** CREATE
- **Target:** `GOOD_KERNELS`
- **Signature:** `GOOD_KERNELS: dict[str, str]`
- **Detail:** Add at least 10 known-good source strings: vector add, ReLU, GELU, copy, AXPY, softmax, sum reduction, max reduction, tiled GEMM with `tl.dot`, and atomic add reduction. Include wrappers with grid launch syntax. Must include at least one kernel that uses a nested `for k in range(0, K, BLOCK_K):` loop to validate Task 1.4's control-flow grammar under realistic matmul patterns. At least one `GOOD_KERNELS` fixture must use `tl.constexpr` in its parameter list to verify the annotation terminal is accepted. Contract clauses: Section 3.2 items 1-2, G6.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.5

- **File:** `cluster1/grammar/test_grammar_acceptance.py`
- **Action:** CREATE
- **Target:** `BAD_KERNELS`
- **Signature:** `BAD_KERNELS: dict[str, str]`
- **Detail:** Add at least 10 known-bad source strings including the four contract-mandated rejections: wrong-arity `tl.store`, missing `tl.program_id`, free-form `@triton.autotune` config, and launch wrapper missing grid. Also include markdown fence, prose preamble, missing `@triton.jit`, hallucinated `tl.load2`, invalid `tl.program_id(axis=7)`, and malformed indentation. Add one `BAD_KERNELS` fixture that uses `tl.constexpr` as a callable (e.g., `tl.constexpr(128)`) and assert it is rejected — `tl.constexpr` is a type annotation only, not a function call. Contract clauses: Section 2.2 rejection requirements, Section 3.2 item 3, G6.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.6

- **File:** `cluster1/tests/test_grammar.py`
- **Action:** CREATE
- **Target:** `test_good_kernels_are_accepted`
- **Signature:** `def test_good_kernels_are_accepted(name: str, source: str) -> None`
- **Detail:** Parametrize over `GOOD_KERNELS` and assert `accepts_source(source)` is true. Failure message must name the rejected fixture. Contract clauses: T1.
- **DoD item:** #1
- **Placeholder:** None

#### Task 2.7

- **File:** `cluster1/tests/test_grammar.py`
- **Action:** CREATE
- **Target:** `test_bad_kernels_are_rejected`
- **Signature:** `def test_bad_kernels_are_rejected(name: str, source: str) -> None`
- **Detail:** Parametrize over `BAD_KERNELS` and assert `accepts_source(source)` is false. Failure message must name the invalid fixture. Contract clauses: T1.
- **DoD item:** #1
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_grammar.py -v` — all grammar acceptance/rejection tests pass and at least 20 total cases execute. Note: `test_grammar_accepts_prompt_contract_configs` (Task 6.9) runs in Phase 6, not here, because `prompt_contract.py` does not exist until Phase 6.

---

## Phase 3: Constrained Decoding Integration

**DoD items:** #2

### Objective

Implement XGrammar loading, hardware-aware masking, and the grammar-on/off generation path with `grammar_active` as the sole experimental toggle.

### Prerequisite

Phase 1 and Phase 2.

### Tasks

#### Task 3.1

- **File:** `cluster1/generation/grammar_loader.py`
- **Action:** CREATE
- **Target:** `load_compiled_grammar`
- **Signature:** `def load_compiled_grammar(grammar_path: str, tokenizer_id: str) -> CompiledGrammar`
- **Detail:** **Public API:** The function accepts `grammar_path: str` and `tokenizer_id: str` as its public parameters. Internally, before caching, it computes `_vocab_fingerprint(tokenizer_id)` — which loads the tokenizer, serializes its vocabulary size and first/last 50 token strings to a stable string, and returns its SHA256 hex digest. The actual `lru_cache` key is `(grammar_path, fingerprint)`, not `(grammar_path, tokenizer_id)`. The public signature does not expose the fingerprint; callers always pass a human-readable `tokenizer_id`. Because `lru_cache` keys must be the cache arguments, implement this as a two-function pattern: a public `load_compiled_grammar(grammar_path, tokenizer_id)` that computes the fingerprint and delegates to a private `_load_compiled_grammar_cached(grammar_path, fingerprint)` decorated with `@lru_cache(maxsize=8)`. Read the GBNF text from `grammar_path`, build `xgrammar.TokenizerInfo.from_huggingface(tokenizer_id)`, compile with `xgrammar.GrammarCompiler`, and cache. The cache key must NOT be the raw `tokenizer_id` string; model name strings are not guaranteed unique across tokenizer variants. This ensures that two tokenizer IDs resolving to different vocabularies always produce distinct compiled grammars, and that switching model versions forces recompilation even if the display name is reused. Contract clauses: Section 3.1 Step 2, D1, D4.
- **DoD item:** #2
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 3.1a

- **File:** `cluster1/tests/test_constrained_gen.py`
- **Action:** CREATE
- **Target:** `test_cache_key_uses_vocab_fingerprint`
- **Signature:** `def test_cache_key_uses_vocab_fingerprint(monkeypatch) -> None`
- **Detail:** Monkeypatch two fake tokenizers with identical `tokenizer_id` strings but different vocabulary sizes. Assert that `_vocab_fingerprint()` returns different digests for both, and that `load_compiled_grammar()` called with both produces two separate `_load_compiled_grammar_cached()` calls, not one cached result. This guards against the silent stale-cache failure mode where a model update changes the vocabulary but the name string stays the same.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.2

- **File:** `cluster1/constraints/hardware_checker.py`
- **Action:** CREATE
- **Target:** `HardwareChecker`
- **Signature:** `class HardwareChecker: def __init__(self, smem_limit: int = 49152, dtype_bytes: int = 2) -> None; def reset(self) -> None; def validate_assignment(self, name: str, value: int) -> bool; def allowed_values(self, name: str) -> set[int]`
- **Detail:** Maintain per-generation state for `BLOCK_M`, `BLOCK_N`, `BLOCK_K`, `num_warps`, and `num_stages`. Enforce the following rules: powers of two `{16,32,64,128,256}` for all `BLOCK_*` values; warp counts `{1,2,4,8,16}`; stage counts `{1,2,3,4,5}`; shared memory `BLOCK_M * BLOCK_N * dtype_bytes <= smem_limit`. Additionally enforce two contract-required semantic checks: (a) **`tl.arange` consistency** — when a `tl.arange(0, N)` call is detected and a `BLOCK_*` value has been sampled, assert `N` equals the relevant block size; flag mismatches as a hardware constraint violation; (b) **`tl.dot` shape compatibility** — after both matrix arguments to `tl.dot` are resolved from context, assert the inner dimensions match; flag mismatches. `reset()` must clear all sampled state between generations. `smem_limit` defaults to `49152` (48KB). Contract clauses: Section 2.3, H1-H5.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.2a

- **File:** `cluster1/tests/test_hardware_checker.py`
- **Action:** CREATE
- **Target:** Full hardware checker test suite
- **Signature:** N/A — multiple test functions
- **Detail:** Create the test file for `HardwareChecker` covering all contract DoD items T2: (a) `test_power_of_two_enforcement` — assert `BLOCK_M=37` is rejected, `BLOCK_M=64` passes; (b) `test_smem_budget` — assert `BLOCK_M=128, BLOCK_N=256, fp16` is rejected (exceeds 48KB), `BLOCK_M=64, BLOCK_N=64` passes; (c) `test_warp_count` — assert `num_warps=3` rejected, `num_warps=4` passes; (d) `test_stage_count` — assert `num_stages=6` rejected, `num_stages=3` passes; (e) `test_arange_consistency` — assert that after sampling `BLOCK_SIZE=64`, a `tl.arange(0, 128)` call is flagged; (f) `test_dot_shape_compatibility` — assert that a `(M, K)` × `(N, K)` dot product (inner dim mismatch) is flagged; (g) `test_reset_clears_state` — call checker with `BLOCK_M=64`, call `reset()`, then assert `BLOCK_N` is no longer constrained by the previous `BLOCK_M` value. Contract clauses: H1-H5, T2.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.3

- **File:** `cluster1/generation/constrained_decoding.py`
- **Action:** CREATE
- **Target:** `TritonGrammarLogitsProcessor`
- **Signature:** `class TritonGrammarLogitsProcessor(LogitsProcessor): def __init__(self, compiled_grammar, tokenizer, hardware_checker: HardwareChecker | None = None) -> None; def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor; def masked_token_rate(self) -> float`
- **Detail:** Wrap XGrammar's matcher with a fresh matcher per generation. On every decoding step, obtain the grammar token bitmask, intersect it with hardware-checker masks at context-dependent token positions, apply `-inf` to disallowed scores, and append the fraction of masked vocabulary to an internal list. `masked_token_rate()` returns the mean fraction masked. Contract clauses: Section 2.4, D3, D5, H5.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.4

- **File:** `cluster1/generation/constrained_gen.py`
- **Action:** CREATE
- **Target:** `DecodedKernel`
- **Signature:** `@dataclass(frozen=True) class DecodedKernel: source: str; masked_token_rate: float | None; generation_seed: int | None; temperature: float`
- **Detail:** Define the raw generation output used before Phase 5 wires the final result dataclass. It must not contain timing fields. Contract clauses: Section 2.4 diagnostic requirements, boundary rule.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.5

- **File:** `cluster1/generation/constrained_gen.py`
- **Action:** CREATE
- **Target:** `generate_source`
- **Signature:** `def generate_source(prompt: str, model, tokenizer, grammar_active: bool, compiled_grammar=None, hardware_checker: HardwareChecker | None = None, max_new_tokens: int = 1024, temperature: float = 0.2, seed: int | None = None) -> DecodedKernel`
- **Detail:** Set `torch.manual_seed(seed)` when seed is not `None`. Tokenize exactly one prompt. Build identical `model.generate()` kwargs for both conditions: same `max_new_tokens`, `temperature`, `do_sample=True`, same seed, same input IDs. If `grammar_active=True`, require `compiled_grammar` and add exactly one fresh `TritonGrammarLogitsProcessor` to `logits_processor`; if false, omit it. Decode only new tokens. Return `masked_token_rate=None` when grammar is off. Contract clauses: Section 2.4 critical invariant, D2-D5.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.6

- **File:** `cluster1/tests/test_constrained_gen.py`
- **Action:** CREATE
- **Target:** `test_grammar_active_only_changes_logits_processor`
- **Signature:** `def test_grammar_active_only_changes_logits_processor(monkeypatch) -> None`
- **Detail:** Use fake model/tokenizer objects to implement three distinct test cases covering the full T3 contract requirement:

  **Case 1 — parameter invariant:** Assert both `grammar_active=True` and `grammar_active=False` paths call `model.generate()` with identical parameters except `logits_processor`. Use `monkeypatch` to capture the kwargs passed to `model.generate()` in both cases and assert all non-`logits_processor` fields are equal.

  **Case 2 — grammar ON produces valid output:** With a fake model that returns a known syntactically valid Triton kernel source, assert that `generate_source(..., grammar_active=True)` returns a `DecodedKernel` where `source` is accepted by `accepts_source()` and `masked_token_rate` is not None and is greater than zero.

  **Case 3 — grammar OFF is capable of producing invalid output:** With a fake model that returns a known syntactically invalid Triton kernel source (e.g., missing `@triton.jit`, prose preamble), assert that `generate_source(..., grammar_active=False)` returns that invalid source unchanged — i.e., the unconstrained path does not filter or modify model output. Assert `masked_token_rate` is None. This case is critical: if the unconstrained path accidentally filters output, your baseline comparison is invalid.

  Contract clauses: D2, D3, T3.
- **DoD item:** #2
- **Placeholder:** None

#### Task 3.7

- **File:** `cluster1/generation/constrained_gen.py`
- **Action:** MODIFY
- **Target:** `__main__` block
- **Signature:** N/A
- **Detail:** Add an `if __name__ == "__main__":` block that parses `--model-id`, `--prompt`, `--grammar-active` (bool), and `--seed` (int) via `argparse`. Call `load_compiled_grammar()` if `grammar_active=True`, instantiate a fresh `HardwareChecker`, call `generate_source()`, print the result source and `masked_token_rate` to stdout. This is the CLI entry point required by the Phase 3 integration smoke command `python -m cluster1.generation.constrained_gen`. Without this block the module has no `__main__` and the smoke command fails with an argument error.
- **DoD item:** #2
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

### Completion Criterion

Run `python -m pytest cluster1/tests/test_constrained_gen.py cluster1/tests/test_hardware_checker.py -v` — all unit tests pass with fake model/tokenizer objects, including the full hardware checker test suite from Task 3.2a.

**Model gate:** The integration smoke below uses the resolved development model `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`. The pytest unit tests are still the sufficient exit condition for Phase 3 and Phase 4 may begin without a CUDA/model host. The integration smoke must be run before Phase 7 starts, not before Phase 4.

On any host with a CUDA GPU and a resolved model (minimum: any 1B-3B parameter HuggingFace causal LM), run:

```bash
python -m cluster1.generation.constrained_gen \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --prompt "Write a Triton kernel for ReLU." \
  --grammar-active true \
  --seed 0
```

Assert the output: (a) is accepted by `accepts_source()`, (b) has `masked_token_rate > 0.0`, and (c) does not contain any `BLOCK` value outside `{16,32,64,128,256}`. This validates that the grammar bitmask and hardware checker bitmask intersection is actually firing during generation, not just in unit tests with fake processors.

---

## Phase 4: Compilation Validation Gate

**DoD items:** #3

### Objective

Implement the launch-time compile gate that separates signature errors, Triton compilation errors, and runtime errors across dtypes and shape distributions.

### Prerequisite

Phase 1. (May be implemented in parallel with Phase 3.)

### Tasks

#### Task 4.1

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `CompileResult`
- **Signature:** `@dataclass(frozen=True) class CompileResult: success: bool; error_type: Literal["CompilationError", "RuntimeError", "SignatureError", None]; error_msg: str | None; dtype: str; n_shapes_tested: int`
- **Detail:** Define the compile validation output. `error_msg` must be truncated to 500 characters. Do not include timing fields. Contract clauses: Section 2.5 error taxonomy, V2, V3.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.2

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `CompileSpec`
- **Signature:** `@dataclass(frozen=True) class CompileSpec: launcher_name: str; reference_signature: inspect.Signature; build_args: Callable[[tuple[int, ...], torch.dtype], tuple[list[Any], dict[str, Any]]]`
- **Detail:** Define a validation spec independent of dataset `KernelSpec` so Phase 4 does not depend on Phase 6. `build_args` must allocate dummy CUDA tensors only; it must not compute or compare reference outputs. Contract clauses: Section 2.5 signature and dummy launch, V1, V4, V5.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.3

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `load_generated_module`
- **Signature:** `def load_generated_module(source: str) -> types.ModuleType`
- **Detail:** Write source to a temporary module, parse/execute it in an isolated namespace, and return the module object. Syntax/import failures that prevent signature inspection must map to `SignatureError` at the caller. Do not catch all errors as success. Contract clauses: V4.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.4

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `validate_signature`
- **Signature:** `def validate_signature(module: types.ModuleType, spec: CompileSpec) -> str | None`
- **Detail:** Locate `spec.launcher_name`, call `inspect.signature()` on it, and compare exactly to `spec.reference_signature`. Return an error string on mismatch or missing launcher; return `None` on match. This must run before any Triton launch. Contract clauses: Section 2.5 Step 1, V4.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.5

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `check_compiles`
- **Signature:** `def check_compiles(source: str, spec: CompileSpec, dtype: torch.dtype, shapes: list[tuple[int, ...]]) -> CompileResult`
- **Detail:** Load module, validate signature, then for each shape call `args, kwargs = spec.build_args(shape, dtype)` and invoke `module.<launcher_name>(*args, **kwargs)` on CUDA to trigger Triton JIT. Catch `triton.compiler.errors.CompilationError` separately as `CompilationError`; catch `RuntimeError` separately as `RuntimeError`; catch signature failures as `SignatureError`. `success=True` only if every shape for that dtype launches. Contract clauses: Section 2.5, V1-V4.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.6

- **File:** `cluster1/validation/compile_check.py`
- **Action:** CREATE
- **Target:** `check_compiles_all_dtypes`
- **Signature:** `def check_compiles_all_dtypes(source: str, spec: CompileSpec, shapes_by_dtype: dict[str, list[tuple[int, ...]]]) -> list[CompileResult]`
- **Detail:** Run `check_compiles()` for `fp32`, `fp16`, and `bf16`. Use `torch.float32`, `torch.float16`, and `torch.bfloat16`. Return one `CompileResult` per dtype. Contract clauses: Section 2.5 multi-dtype check, V3.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.7

- **File:** `cluster1/tests/test_compile_check.py`
- **Action:** CREATE
- **Target:** `test_signature_error_precedes_compile`
- **Signature:** `def test_signature_error_precedes_compile() -> None`
- **Detail:** Provide a generated source with wrong launcher signature and assert `check_compiles()` returns `SignatureError` without attempting launch. Contract clauses: T4.
- **DoD item:** #3
- **Placeholder:** None

#### Task 4.8

- **File:** `cluster1/tests/test_compile_check.py`
- **Action:** CREATE
- **Target:** `test_error_taxonomy`
- **Signature:** `def test_error_taxonomy(cuda_available: bool) -> None`
- **Detail:** Add CUDA-skipped tests for a known-good ReLU compile and a known-bad Triton compile. Assert `CompilationError` and `RuntimeError` are distinct when triggered. Do not perform numerical comparison. Contract clauses: T4, V5.
- **DoD item:** #3
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_compile_check.py -v` — CPU signature tests pass and CUDA compile tests pass when CUDA is available.

---

## Phase 5: Result Dataclass and Logging

**DoD items:** #4

### Objective

Create the final structured result schema and JSONL logger used by generation, validation, and analysis.

### Prerequisite

Phase 3 and Phase 4. (May begin once Phase 4's `CompileResult` shape is stable.)

### Tasks

#### Task 5.1

- **File:** `cluster1/results/dataclass.py`
- **Action:** CREATE
- **Target:** `CompileErrorType`
- **Signature:** `CompileErrorType = Literal["CompilationError", "RuntimeError", "SignatureError", None]`
- **Detail:** Define the only allowed compile error taxonomy. Do not include parse/import/profiler/numerical-correctness error labels in the final Cluster 1 result schema. Contract clauses: Section 2.5, Section 2.6.
- **DoD item:** #4
- **Placeholder:** None

#### Task 5.2

- **File:** `cluster1/results/dataclass.py`
- **Action:** CREATE
- **Target:** `GenerationResult`
- **Signature:** `@dataclass(frozen=True) class GenerationResult: source: str; model_id: str; grammar_active: bool; kernel_class: Literal["elementwise", "reduction", "matmul"]; kernel_name: str; dtype: Literal["fp32", "fp16", "bf16"]; compile_success: bool; compile_results_by_dtype: dict[str, bool]; compile_error_type: CompileErrorType; compile_error_msg: str | None; masked_token_rate: float | None; unique_solution_hash: str; n_shapes_tested: int; generation_seed: int | None; temperature: float; run_id: str; timestamp_utc: str`
- **Detail:** Implement the final record. `model_id` stores the resolved model identifier, with development runs defaulting to `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`. Include `n_shapes_tested` from the session-required field list. Add field: `compile_results_by_dtype: dict[str, bool]` — a dict mapping `"fp32"`, `"fp16"`, `"bf16"` to their individual `compile_success` booleans from `check_compiles_all_dtypes`. This field satisfies contract V3's requirement that fp32/fp16/bf16 pass/fail be logged per dtype. It is a diagnostic field and is not used as the primary `compile_success` gate. The primary `compile_success` field remains `all(r.success for r in compile_results)` as before. `masked_token_rate` must be `None` only when `grammar_active=False`. `unique_solution_hash` must be populated for every row. Do not include timing fields. Also implement `validate_result_invariants(result: GenerationResult) -> None` as a module-level function in this file. It must raise `ValueError` with message `"masked_token_rate must be None when grammar_active is False"` if `grammar_active=False` and `masked_token_rate` is not `None`, and raise `ValueError` with message `"masked_token_rate must not be None when grammar_active is True"` if `grammar_active=True` and `masked_token_rate` is `None`. The runner must call this function before `append_result_jsonl()`. Contract clauses: Section 2.6, R2, V3.
- **DoD item:** #4
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 5.3

- **File:** `cluster1/results/dataclass.py`
- **Action:** CREATE
- **Target:** `compute_unique_solution_hash`
- **Signature:** `def compute_unique_solution_hash(source: str) -> str`
- **Detail:** Normalize source by parsing with `ast.parse`, unparsing with `ast.unparse`, stripping whitespace, and SHA256 hashing the normalized string. If AST parsing fails, hash a whitespace-normalized source string. Contract clauses: Section 2.9 unique solution hash, R6.
- **DoD item:** #4
- **Placeholder:** None

#### Task 5.4

- **File:** `cluster1/results/logger.py`
- **Action:** CREATE
- **Target:** `append_result_jsonl`
- **Signature:** `def append_result_jsonl(path: Path, result: GenerationResult) -> None`
- **Detail:** Append exactly one JSON object per line using `dataclasses.asdict(result)`. Create parent directories. Do not mutate the result. Contract clauses: R3.
- **DoD item:** #4
- **Placeholder:** None

#### Task 5.5

- **File:** `cluster1/generation/constrained_gen.py`
- **Action:** MODIFY
- **Target:** `generate_source` (rename note)
- **Signature:** `def generate_source(...) -> DecodedKernel`
- **Detail:** Keep `generate_source()` as the raw decoding function and require the experiment runner to assemble `GenerationResult` after compile validation. This preserves dependency separation: generation does not decide compile success. Contract clauses: Section 2.4, Section 2.6 data flow.
- **DoD item:** #4
- **Placeholder:** None

#### Task 5.6

- **File:** `cluster1/tests/test_results.py`
- **Action:** CREATE
- **Target:** `test_generation_result_schema`
- **Signature:** `def test_generation_result_schema() -> None`
- **Detail:** Instantiate `GenerationResult` and assert its dataclass fields exactly match the Task 5.2 signature. Assert `compile_results_by_dtype` is present and contains exactly the three dtype keys `"fp32"`, `"fp16"`, and `"bf16"`. Assert no field name ends with `_time_s` and no field contains numerical correctness metrics. Add two invariant test cases: **Case A** — instantiate `GenerationResult` with `grammar_active=False` and `masked_token_rate=0.5`, assert `validate_result_invariants(result)` raises `ValueError` containing `"masked_token_rate must be None when grammar_active is False"`; **Case B** — instantiate `GenerationResult` with `grammar_active=True` and `masked_token_rate=None`, assert `validate_result_invariants(result)` raises `ValueError` containing `"masked_token_rate must not be None when grammar_active is True"`. Contract clauses: R2, R3, V3.
- **DoD item:** #4
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

### Completion Criterion

Run `python -m pytest cluster1/tests/test_results.py -v` — schema, invariant, and JSONL logger tests pass.

---

## Phase 6: Dataset and Kernel Specification

**DoD items:** #9

### Objective

Lock the three KernelBench-backed kernel classes, prompt contracts, reference signatures, autotune configs, and dummy launch shapes. Run grammar/prompt co-validation once `prompt_contract.py` exists.

### Prerequisite

Phase 4 and Phase 5.

### Pre-execution step (required before any task in this phase)

Run the following verification script and record the exact problem IDs before writing any `KernelSpec`:

```python
from datasets import load_dataset

ds = load_dataset("ScalingIntelligence/KernelBench", split="train")
for row in ds:
    if row.get("level") == 1:
        print(row["problem_id"], row["name"])
```

Scan output for: a problem whose reference uses `torch.relu` or pointwise activation (elementwise), a problem whose reference uses `torch.softmax` along a dim (reduction), and a problem whose reference uses `torch.matmul` or `@` on 2D tensors (matmul). Record all three problem IDs. Do not proceed to Tasks 6.4–6.6 until IDs are confirmed.

### Tasks

#### Task 6.1

- **File:** `cluster1/data/kernels/spec.py`
- **Action:** CREATE
- **Target:** `KernelSpec`
- **Signature:** `@dataclass(frozen=True) class KernelSpec: name: str; kernel_class: Literal["elementwise", "reduction", "matmul"]; launcher_name: str; reference_signature: inspect.Signature; compile_spec: CompileSpec; prompt_template: str; autotune_configs: list[dict[str, Any]]; shapes_by_dtype: dict[str, list[tuple[int, ...]]]; dataset_id: str; dataset_problem_id: int`
- **Detail:** Define the canonical kernel metadata object consumed by prompt construction, compile validation, and experiment runner. `dataset_id` must be `"ScalingIntelligence/KernelBench"`. `dataset_problem_id` must be the verified integer from the pre-execution step above; do not hardcode a guess. **Contract deviation note:** Contract clause R1 states reference signatures are locked in `prompt_contract.py`. This plan locks them in `KernelSpec` instead, with `prompt_contract.py` owning only template rendering. This deviation is intentional: `KernelSpec` is the single canonical source of truth for all kernel metadata including signature, shapes, and dataset ID. Splitting signature ownership between `KernelSpec` and `prompt_contract.py` would create two places to update when a signature changes, which is a maintenance hazard. `build_prompt()` reads the signature from `spec.reference_signature` and renders it into the prompt — the contract's intent (signatures are locked before generation) is satisfied; only the file location differs. This deviation is recorded here so a reviewer scanning for R1 compliance finds it immediately. Contract clauses: Section 2.8, R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.2

- **File:** `cluster1/data/prompts/prompt_contract.py`
- **Action:** CREATE
- **Target:** `PROMPT_TEMPLATE`
- **Signature:** `PROMPT_TEMPLATE: str`
- **Detail:** Implement the exact prompt invariant: include function signature, docstring-style semantics, dtype/device, fixed autotune configs, and instruction to return only code with no markdown. The prompt must not vary between grammar ON and OFF. The autotune config literal values defined here must exactly match those allowed by the `autotune-decorator` production in `triton_kernel.gbnf`; Task 6.9 enforces this co-validation. Contract clauses: Section 2.7.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.3

- **File:** `cluster1/data/prompts/prompt_contract.py`
- **Action:** CREATE
- **Target:** `build_prompt`
- **Signature:** `def build_prompt(spec: KernelSpec, dtype: str) -> str`
- **Detail:** Render `PROMPT_TEMPLATE` using the locked `KernelSpec` fields and requested dtype. Include the fixed config list exactly as `spec.autotune_configs`. Do not include feedback from compile errors or previous attempts. Contract clauses: Section 2.7 prompt invariants, boundary rule.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.4

- **File:** `cluster1/data/kernels/elementwise_relu.py`
- **Action:** CREATE
- **Target:** `RELU_SPEC`
- **Signature:** `RELU_SPEC: KernelSpec`
- **Detail:** Define KernelBench ReLU spec with `name="relu"`, `kernel_class="elementwise"`, `launcher_name="relu"`, locked signature `relu(x: torch.Tensor) -> torch.Tensor`, fixed autotune configs for `BLOCK_SIZE in {64,128,256,512}`, and at least 5 shapes per dtype including power-of-2, non-power-of-2, smaller-than-block, and non-divisible cases. Set `dataset_id="ScalingIntelligence/KernelBench"` and `dataset_problem_id=<VERIFIED_ID>` (replace with the integer recorded in the pre-execution step). Contract clauses: Section 2.8, Section 2.5 shape distribution, R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.5

- **File:** `cluster1/data/kernels/reduction_softmax.py`
- **Action:** CREATE
- **Target:** `SOFTMAX_SPEC`
- **Signature:** `SOFTMAX_SPEC: KernelSpec`
- **Detail:** Define KernelBench Softmax spec with `name="softmax"`, `kernel_class="reduction"`, `launcher_name="softmax"`, locked signature `softmax(x: torch.Tensor) -> torch.Tensor`, fixed configs for row/block reduction, and at least 5 2D shapes per dtype covering required shape distribution. Set `dataset_id="ScalingIntelligence/KernelBench"` and `dataset_problem_id=<VERIFIED_ID>`. Contract clauses: Section 2.8, R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.6

- **File:** `cluster1/data/kernels/matmul_tiled_gemm.py`
- **Action:** CREATE
- **Target:** `GEMM_SPEC`
- **Signature:** `GEMM_SPEC: KernelSpec`
- **Detail:** Define KernelBench tiled GEMM spec with `name="gemm"`, `kernel_class="matmul"`, `launcher_name="matmul"`, locked signature `matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor`, fixed configs for `BLOCK_M`, `BLOCK_N`, `BLOCK_K`, `num_warps`, and `num_stages`, and at least 5 `(M,N,K)` shapes per dtype covering required shape distribution. Set `dataset_id="ScalingIntelligence/KernelBench"` and `dataset_problem_id=<VERIFIED_ID>`. Contract clauses: Section 2.8, R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.7

- **File:** `cluster1/data/kernels/__init__.py`
- **Action:** CREATE
- **Target:** `KERNEL_SPECS`
- **Signature:** `KERNEL_SPECS: dict[str, KernelSpec]`
- **Detail:** Export `{"elementwise": RELU_SPEC, "reduction": SOFTMAX_SPEC, "matmul": GEMM_SPEC}` plus lookup helper `def get_kernel_spec(kernel_class: str) -> KernelSpec`. Contract clauses: Section 2.8 three classes, R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.8

- **File:** `cluster1/tests/test_kernel_specs.py`
- **Action:** CREATE
- **Target:** `test_all_kernel_classes_present`
- **Signature:** `def test_all_kernel_classes_present() -> None`
- **Detail:** Assert exactly the three classes `elementwise`, `reduction`, and `matmul` are present; each has 3 dtype keys; each dtype has at least 5 shapes; each `dataset_id == "ScalingIntelligence/KernelBench"` and `dataset_problem_id` is a positive integer for all three specs. Also assert that calling `build_prompt(spec, "fp32")` for each spec produces a string that contains the exact reference signature string — confirming that the signature stored in `KernelSpec` is the one rendered into the prompt and not silently dropped. Contract clauses: R1.
- **DoD item:** #9
- **Placeholder:** None

#### Task 6.9

- **File:** `cluster1/grammar/test_grammar_acceptance.py`
- **Action:** MODIFY
- **Target:** `test_grammar_accepts_prompt_contract_configs`
- **Signature:** `def test_grammar_accepts_prompt_contract_configs() -> None`
- **Detail:** Import `PROMPT_TEMPLATE` and the fixed autotune config lists from `cluster1/data/prompts/prompt_contract.py` (now available because Phase 6 Tasks 6.2 and 6.3 have run). For each kernel class config set — elementwise `BLOCK_SIZE in {64,128,256,512}`, reduction row/block configs, matmul `BLOCK_M/BLOCK_N/BLOCK_K` configs — render a minimal kernel stub using those exact config values and assert `accepts_source(stub)` is `True`. This test guarantees the grammar never rejects a config value the prompt contract is contractually allowed to emit. A grammar that rejects its own prompt contract produces silent degenerate outputs with no error at generation time. Placed in Phase 6 (not Phase 1/2) because `prompt_contract.py` does not exist until this phase. Contract clauses: G3, G6, Section 2.7.
- **DoD item:** #1, #9
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_kernel_specs.py -v` — all three kernel classes, signatures, dtype shape sets, resolved dataset ID (`"ScalingIntelligence/KernelBench"`), and positive-integer problem IDs validate. Additionally, `test_grammar_accepts_prompt_contract_configs` must pass, confirming the grammar accepts every autotune config value the prompt contract is permitted to emit.

---

## Phase 7: Generation Pipeline and Experiment Runner

**DoD items:** #5, #6

### Objective

Build the CLI that runs baseline and constrained cells with n>=20 per kernel class and logs final `GenerationResult` JSONL records.

### Prerequisite

Phase 3 (unit tests complete and model gate resolved), Phase 4, Phase 5, and Phase 6.

### Tasks

#### Task 7.1

- **File:** `cluster1/experiments/run_cluster1.py`
- **Action:** CREATE
- **Target:** `parse_args`
- **Signature:** `def parse_args(argv: list[str] | None = None) -> argparse.Namespace`
- **Detail:** Add CLI args: `--model-id`, default `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`; `--dataset-id`, default `ScalingIntelligence/KernelBench`; `--condition {baseline,G,both}`; `--kernel-class {elementwise,reduction,matmul,all}`; `--n`, default `20`; `--output`, required Path; `--grammar-path`, default `cluster1/grammar/triton_kernel.gbnf`; `--temperature`, default `0.2`; `--max-new-tokens`, default `1024`. Document this default as the development iteration model, not the final thesis reporting model. Contract clauses: R4, R5.
- **DoD item:** #5, #6
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 7.2

- **File:** `cluster1/experiments/run_cluster1.py`
- **Action:** CREATE
- **Target:** `load_model_and_tokenizer`
- **Signature:** `def load_model_and_tokenizer(model_id: str): ...`
- **Detail:** Load HuggingFace tokenizer and model from `model_id`. Return `(model, tokenizer)`. Do not branch behavior by grammar condition. Contract clauses: Section 2.4 invariant.
- **DoD item:** #5, #6
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 7.3

- **File:** `cluster1/experiments/run_cluster1.py`
- **Action:** CREATE
- **Target:** `iter_experiment_cells`
- **Signature:** `def iter_experiment_cells(kernel_classes: list[str], condition: str, n: int, dtypes: list[str] = ["fp32", "fp16", "bf16"]) -> Iterator[tuple[KernelSpec, bool, str, int]]`
- **Detail:** Yield exactly `n` seeds per `(kernel_class, grammar_active, dtype)` cell. Full cell space for a complete run: 3 kernel classes × 2 conditions × 3 dtypes × 20 seeds = 360 total generation calls. For `condition="both"`, yield both `grammar_active=False` and `grammar_active=True`; for `baseline` only false; for `G` only true. Seeds must be deterministic `0..n-1` per cell. Each yielded tuple is `(spec, grammar_active, dtype, seed)`.
- **DoD item:** #5, #6
- **Placeholder:** None

#### Task 7.4

- **File:** `cluster1/experiments/run_cluster1.py`
- **Action:** CREATE
- **Target:** `run_one_generation`
- **Signature:** `def run_one_generation(spec: KernelSpec, dtype: str, seed: int, grammar_active: bool, model, tokenizer, compiled_grammar, args: argparse.Namespace) -> GenerationResult`
- **Detail:** Build prompt with `build_prompt(spec, dtype)`. Call `generate_source()` with the grammar condition. Call `check_compiles_all_dtypes()` to get `list[CompileResult]`, one per dtype. Collapse into `GenerationResult` as follows: `compile_success = all(r.success for r in compile_results)`; `compile_error_type` = first non-None `error_type` across results, else `None`; `compile_error_msg` = first non-None `error_msg` truncated to 500 chars, else `None`; `n_shapes_tested` = the `CompileResult` for the cell's assigned dtype's `n_shapes_tested`. Populate `compile_results_by_dtype = {r.dtype: r.success for r in compile_results}` and include it in the assembled `GenerationResult`. This preserves the per-dtype signal required by V3 without changing the primary gate. The JSONL logger will serialize it as a nested object. Set `result.dtype` to the cell's assigned `dtype` from the iterator — do not override with a different dtype from compile results. Set `masked_token_rate=None` when `grammar_active=False`. Compute `unique_solution_hash` via `compute_unique_solution_hash(source)`. Set `model_id=args.model_id`. Call `validate_result_invariants(result)` before returning — if invariants fail, raise immediately and do not log the record. Contract clauses: Section 2.4, Section 2.5, R2-R5, V3.
- **DoD item:** #5, #6
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 7.5

- **File:** `cluster1/experiments/run_cluster1.py`
- **Action:** CREATE
- **Target:** `main`
- **Signature:** `def main(argv: list[str] | None = None) -> int`
- **Detail:** Resolve selected kernel specs, load model/tokenizer once, load compiled grammar only if any `grammar_active=True` cell is requested, iterate all cells via `iter_experiment_cells`, call `run_one_generation` per cell, and append every result via `append_result_jsonl()`. Exit 0 on completion. Do not retry failed generations, do not re-prompt, do not use compile errors as model feedback. The invariant check inside `run_one_generation` guarantees every record reaching `append_result_jsonl()` is valid; do not add a second check in `main()`. Contract clauses: R4, R5, boundary rule.
- **DoD item:** #5, #6
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 7.6

- **File:** `cluster1/tests/test_run_cluster1.py`
- **Action:** CREATE
- **Target:** `test_iter_experiment_cells_n20`
- **Signature:** `def test_iter_experiment_cells_n20() -> None`
- **Detail:** Assert `condition="both"`, all three kernel classes, all three dtypes, `n=20` yields exactly 360 cells: 3 classes × 2 conditions × 3 dtypes × 20 seeds. Assert each yielded tuple has 4 elements `(spec, grammar_active, dtype, seed)`. Contract clauses: R4, R5.
- **DoD item:** #5, #6
- **Placeholder:** None

#### Task 7.7

- **File:** `cluster1/tests/test_run_cluster1.py`
- **Action:** CREATE
- **Target:** `test_runner_has_no_feedback_loop`
- **Signature:** `def test_runner_has_no_feedback_loop() -> None`
- **Detail:** Static-inspect `cluster1/experiments/run_cluster1.py` and assert forbidden strings `retry`, `repair`, `feedback`, `re_prompt`, and `compile_error` inside prompt construction are absent. Contract clauses: boundary rule, R4, R5.
- **DoD item:** #5, #6
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_run_cluster1.py -v`, then on a CUDA/model host:

```bash
python -m cluster1.experiments.run_cluster1 \
  --condition baseline \
  --kernel-class elementwise \
  --n 3 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --dataset-id ScalingIntelligence/KernelBench \
  --output /tmp/cluster1_smoke.jsonl
```

Load the output JSONL and assert: (a) exactly 3 result records are present for the specified kernel class and condition, (b) all 3 records have distinct `generation_seed` values `{0, 1, 2}`, (c) `unique_solution_hash` is populated for all 3 records, and (d) if `grammar_active=True` was used, all 3 records have `masked_token_rate` that is not `None` and not zero. Assertion (d) catches `HardwareChecker` state leakage between runs — a checker that fails to reset produces identical `masked_token_rate` values across seeds.

---

## Phase 8: pass@k Analysis and Reporting

**DoD items:** #5, #6, #7

### Objective

Add the statistical analysis required to test the Cluster 1 research claim from logged compile-success records.

### Prerequisite

Phase 5 and Phase 7.

### Tasks

#### Task 8.1

- **File:** `cluster1/experiments/analyze_cluster1.py`
- **Action:** CREATE
- **Target:** `pass_at_k`
- **Signature:** `def pass_at_k(n: int, c: int, k: int) -> float`
- **Detail:** Implement unbiased HumanEval estimator `1 - comb(n - c, k) / comb(n, k)`, returning `1.0` when `n - c < k`. Raise `ValueError` when `k > n`. Correct means `compile_success=True` only. Contract clauses: Section 2.9, R7.
- **DoD item:** #5, #6, #7
- **Placeholder:** None

#### Task 8.2

- **File:** `cluster1/experiments/analyze_cluster1.py`
- **Action:** CREATE
- **Target:** `unique_solution_rate`
- **Signature:** `def unique_solution_rate(rows: list[GenerationResult]) -> float`
- **Detail:** Return `len(set(row.unique_solution_hash for row in rows)) / len(rows)`. Use this alongside pass@k to detect grammar-induced mode collapse. Contract clauses: Section 2.9, R6.
- **DoD item:** #5, #6, #7
- **Placeholder:** None

#### Task 8.3

- **File:** `cluster1/experiments/analyze_cluster1.py`
- **Action:** CREATE
- **Target:** `summarize_results`
- **Signature:** `def summarize_results(jsonl_path: Path) -> pd.DataFrame`
- **Detail:** Load JSONL records, group by `kernel_class`, `grammar_active`, and `dtype`, require `n>=20` source generations per group, compute pass@1/pass@5/pass@10 and unique solution rate. Do not use numerical correctness. Contract clauses: R4-R7.
- **DoD item:** #5, #6, #7
- **Placeholder:** None

#### Task 8.4

- **File:** `cluster1/experiments/analyze_cluster1.py`
- **Action:** CREATE
- **Target:** `null_hypothesis_report`
- **Signature:** `def null_hypothesis_report(jsonl_path: Path, output_markdown: Path) -> None`
- **Detail:** Compare grammar OFF vs grammar ON compile failures by `kernel_class` and `dtype`. If OFF has failures and ON has fewer failures, report eliminated failure count. If not, write an anomaly section with exact group counts and state that DoD #7 requires documentation. Contract clauses: DoD #7, R7.
- **DoD item:** #7
- **Placeholder:** None

#### Task 8.5

- **File:** `cluster1/tests/test_analysis.py`
- **Action:** CREATE
- **Target:** `test_pass_at_k_matches_humaneval`
- **Signature:** `def test_pass_at_k_matches_humaneval() -> None`
- **Detail:** Test known cases for k=1,5,10. Assert pass@1 equals `c/n` and pass@k is not the naive rate for k>1. Contract clauses: R7.
- **DoD item:** #7
- **Placeholder:** None

#### Task 8.6

- **File:** `cluster1/tests/test_analysis.py`
- **Action:** CREATE
- **Target:** `test_summary_uses_compile_success_only`
- **Signature:** `def test_summary_uses_compile_success_only(tmp_path: Path) -> None`
- **Detail:** Create synthetic JSONL rows with no numerical correctness fields and assert summary computes pass@k solely from `compile_success`. Contract clauses: Cluster 1 correctness ladder.
- **DoD item:** #5, #6, #7
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_analysis.py -v` and `python -m cluster1.experiments.analyze_cluster1 --input /path/to/results.jsonl --output /path/to/summary.md`. Summary must include pass@1, pass@5, pass@10, unique solution rate, and null-hypothesis section.

---

## Phase 9: Cluster Boundary Hardening

**DoD items:** #8

### Objective

Enforce the Cluster 1 boundary with static tests and remove timing/profiler/feedback/numerical-correctness leakage from the active code path.

### Prerequisite

Phase 1 through Phase 8.

### Tasks

#### Task 9.1

- **File:** `cluster1/tests/test_cluster_boundary.py`
- **Action:** CREATE
- **Target:** `FORBIDDEN_PATTERNS`
- **Signature:** `FORBIDDEN_PATTERNS: dict[str, str]`
- **Detail:** Define forbidden regex patterns for `torch.allclose`, `torch.testing`, `assert_close`, `triton.testing.do_bench`, `torch.profiler`, `nsight`, `ncu`, `nvml`, `pynvml`, `time.perf_counter`, `time.time`, `speedup`, `repair`, `retry`, `re_prompt`, `reprompt`, and compile-error feedback added to prompts. Contract clauses: Section 3.5, Section 5, V5.
- **DoD item:** #8
- **Placeholder:** None

#### Task 9.2

- **File:** `cluster1/tests/test_cluster_boundary.py`
- **Action:** CREATE
- **Target:** `test_no_cluster_boundary_violations`
- **Signature:** `def test_no_cluster_boundary_violations() -> None`
- **Detail:** Recursively scan `cluster1/` Python files, excluding this boundary test file itself, and fail with path plus line number for any forbidden pattern. Contract clauses: DoD #8.
- **DoD item:** #8
- **Placeholder:** None

#### Task 9.3

- **File:** `README.md`
- **Action:** MODIFY
- **Target:** Cluster 1 quickstart
- **Signature:** N/A
- **Detail:** Replace current Phase 1 smoke-run instructions with `cluster1/` contract commands only. Make clear that `src/`, `scripts/run_smoke.py`, and `experiments/*.ipynb` are legacy partial prototypes and are not the Cluster 1 experimental code path. Contract clauses: DoD #8 boundary clarity.
- **DoD item:** #8
- **Placeholder:** None

#### Task 9.4

- **File:** `cluster1/validation/compile_check.py`
- **Action:** MODIFY
- **Target:** `check_compiles`
- **Signature:** `def check_compiles(source: str, spec: CompileSpec, dtype: torch.dtype, shapes: list[tuple[int, ...]]) -> CompileResult`
- **Detail:** Verify no timing fields, broad profiler hooks, numerical comparisons, or retry logic exist. Keep only signature validation and single-pass dummy launch error taxonomy. Contract clauses: V5.
- **DoD item:** #8
- **Placeholder:** None

### Completion Criterion

Run `python -m pytest cluster1/tests/test_cluster_boundary.py -v` — it reports no boundary violations.

---

## Phase 10: End-to-End Notebook

**DoD items:** #10

### Objective

Provide the clean Jupyter walkthrough demonstrating one constrained generation, compile validation, and structured result record.

### Prerequisite

Phase 1 through Phase 9.

### Tasks

#### Task 10.1

- **File:** `cluster1/notebooks/cluster1_demo.ipynb`
- **Action:** CREATE
- **Target:** Notebook cell 1
- **Signature:** N/A
- **Detail:** Add setup cell importing `Path`, `cluster1.data.kernels.get_kernel_spec`, `build_prompt`, `load_compiled_grammar`, `HardwareChecker`, `generate_source`, `check_compiles_all_dtypes`, `GenerationResult`, and `validate_result_invariants`. Define `MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"` and `DATASET_ID = "ScalingIntelligence/KernelBench"`. Annotate that this is the development iteration model, not the thesis reporting model. Contract clauses: T5.
- **DoD item:** #10
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 10.2

- **File:** `cluster1/notebooks/cluster1_demo.ipynb`
- **Action:** CREATE
- **Target:** Notebook cell 2
- **Signature:** N/A
- **Detail:** Select `spec = get_kernel_spec("elementwise")`, `dtype = "fp32"`, render prompt with `build_prompt(spec, dtype)`, and display annotated prompt components: function signature, dtype/device, fixed autotune configs. Do not include numerical reference output. Contract clauses: Section 2.7, T5.
- **DoD item:** #10
- **Placeholder:** None

#### Task 10.3

- **File:** `cluster1/notebooks/cluster1_demo.ipynb`
- **Action:** CREATE
- **Target:** Notebook cell 3
- **Signature:** N/A
- **Detail:** Load tokenizer/model from `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`, compile grammar against tokenizer via `load_compiled_grammar`, instantiate fresh `HardwareChecker`, and run `generate_source(..., grammar_active=True, seed=0)`. Display generated source and `masked_token_rate`. Contract clauses: D5, T5.
- **DoD item:** #10
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

#### Task 10.4

- **File:** `cluster1/notebooks/cluster1_demo.ipynb`
- **Action:** CREATE
- **Target:** Notebook cell 4
- **Signature:** N/A
- **Detail:** Run compile validation across fp32/fp16/bf16 shapes using `check_compiles_all_dtypes`, assemble one `GenerationResult` row including `compile_results_by_dtype`, call `validate_result_invariants` to confirm schema, and display the result as JSON. Do not run `torch.allclose`, profiler, timing, repair, or re-prompt logic. Contract clauses: V1-V5, R2, T5.
- **DoD item:** #10
- **Placeholder:** None

#### Task 10.5

- **File:** `cluster1/tests/test_notebook_exists.py`
- **Action:** CREATE
- **Target:** `test_cluster1_demo_notebook_exists`
- **Signature:** `def test_cluster1_demo_notebook_exists() -> None`
- **Detail:** Assert `cluster1/notebooks/cluster1_demo.ipynb` exists and contains the strings `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`, `ScalingIntelligence/KernelBench`, `grammar_active=True`, `masked_token_rate`, `compile_success`, and `compile_results_by_dtype`. Contract clauses: T5.
- **DoD item:** #10
- **Placeholder:** None — development model resolved as `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

### Completion Criterion

Run `python -m pytest cluster1/tests/test_notebook_exists.py -v`. On a CUDA/model host, run the notebook top-to-bottom and verify it produces one annotated constrained-generation result record with all Task 5.2 `GenerationResult` fields populated.

---

## Full DoD Coverage Matrix

| DoD # | Item | Covered by phase(s) | Task(s) |
|---:|---|---|---|
| 1 | `.gbnf` grammar file and offline validator | Phase 1, Phase 2, Phase 6 | 1.1–1.6, 2.1–2.7, 6.9 |
| 2 | XGrammar integration | Phase 3 | 3.1, 3.1a, 3.2, 3.2a, 3.3–3.7 |
| 3 | Compilation check with launch | Phase 4 | 4.1–4.8 |
| 4 | Result dataclass fields | Phase 5 | 5.1–5.6 |
| 5 | Baseline runs n>=20 | Phase 7, Phase 8 | 7.1–7.7, 8.1–8.6 |
| 6 | Constrained runs n>=20 | Phase 7, Phase 8 | 7.1–7.7, 8.1–8.6 |
| 7 | Null hypothesis test | Phase 8 | 8.1–8.6 |
| 8 | No Cluster 2/3 leakage | Phase 9 | 9.1–9.4 |
| 9 | Dataset with 3 ops/classes; `ScalingIntelligence/KernelBench` via HuggingFace; problem IDs verified before Phase 7 | Phase 6 | 6.1–6.9 |
| 10 | End-to-end notebook | Phase 10 | 10.1–10.5 |

---

## Open Decisions

### Decision 1: RESOLVED — Development model is `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

Use `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` as the default HuggingFace model identifier used by `load_model_and_tokenizer()` and recorded in development-run `result.model_id`.

- **Required before:** Resolved for Phase 3 integration smoke and Phase 7 development runs. Phases 1–6 and Phase 3 unit tests still do not require a CUDA/model host.
- **Development default:** `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`, callable via HuggingFace `pipeline("text-generation", model=...)` or `AutoTokenizer` plus `AutoModelForCausalLM`.
- **Rationale:** AWQ gives the shortest iteration cycle on a T4 while preserving enough 7B baseline quality that pipeline failures are less likely to be caused by an underpowered model. These results are development-time sanity checks, not thesis numbers.
- **Thesis reporting model:** After all clusters are validated, swap to a larger dense model such as `Qwen/Qwen2.5-Coder-14B-Instruct` or `Qwen/Qwen2.5-Coder-32B-Instruct` on suitable hardware and run the full experiment for reported results.

### Decision 2: RESOLVED — Dataset is `ScalingIntelligence/KernelBench` (HuggingFace)

KernelBench is available at `ScalingIntelligence/KernelBench`. Level 1 contains elementwise, reduction, and matmul-class kernels with PyTorch reference implementations. This is the highest-result-yielding option for Cluster 1 because: (a) reference signatures are standardized and locked, (b) it is the dataset used in published kernel generation benchmarks making results directly comparable, (c) it loads with `datasets.load_dataset("ScalingIntelligence/KernelBench", split="train")` with no local checkout required, and (d) Level 1 problems are the correct difficulty for syntactic validity testing without introducing algorithmic complexity belonging to Clusters 2 and 3.

Problem ID verification is the pre-execution step for Phase 6. Do not lock `dataset_problem_id` values without running it.

---

## Execution Order Summary

| Phase | Can start after | Parallelism |
|---|---|---|
| 0 | — | — |
| 1 | Phase 0 | — |
| 2 | Phase 1 | — |
| 3 | Phase 2 | Phase 4 may start in parallel after Phase 1 |
| 4 | Phase 1 | Parallel with Phase 3 |
| 5 | Phase 3 + Phase 4 (`CompileResult` shape stable) | — |
| 6 | Phase 4 + Phase 5 | — |
| 7 | Phase 3 (model gate resolved) + Phase 4 + Phase 5 + Phase 6 | — |
| 8 | Phase 5 + Phase 7 | — |
| 9 | Phase 1–8 | — |
| 10 | Phase 1–9 | — |
