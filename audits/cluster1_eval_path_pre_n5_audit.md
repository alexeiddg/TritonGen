# Cluster 1 Eval Path Pre-n5 Audit

## 1. Executive summary

Overall classification: **BLOCKED_BEFORE_N5**.

The fresh task-agnostic G n=5 should not proceed under the stated decision criteria because the signature gate is not compatible. Shape schedules are compatible: C1 compile probes are now derived from `shared.eval.correctness_shapes.get_compile_shapes`, and C2 Level 2 uses the same shared shape module with explicit compile-vs-correctness differences. Failure-code classification is compatible: the C1 analyzer converts rows through `shared.eval.adapter_cluster1.eval_result_from_generation_result` and classifies with `shared.eval.failure_taxonomy.classify_failure`. The blocker is C1's extra runtime `inspect.Signature` equality gate in `cluster1.validation.compile_check.validate_signature`, which rejects launchers that shared Level 0 accepts because shared Level 0 checks parameter names only.

## 2. Item 1 - Shape schedule audit

Classification: **COMPATIBLE**.

### C1 compile validation path

C1 local generation calls `check_compiles_all_dtypes(decoded.source, spec.compile_spec, spec.shapes_by_dtype)` in `cluster1/experiments/run_cluster1.py:182-186`. `check_compiles_all_dtypes` iterates exactly `("fp32", "fp16", "bf16")`, fetches `shapes_by_dtype[dtype_key]`, and calls `check_compiles` in `cluster1/validation/compile_check.py:281-292`. `check_compiles` builds dummy CUDA args and launches the public launcher once per shape at `cluster1/validation/compile_check.py:246-263`.

C1 Modal compile uses the same core path. `cluster1/experiments/run_cluster1_modal.py:1036-1042` calls `check_compiles_modal`; `shared/modal_harness/compile_runner.py:119-124` resolves `get_kernel_spec(kernel_class)` and calls `check_compiles_all_dtypes(source, spec.compile_spec, spec.shapes_by_dtype)`.

### C1 compile validation shapes per dtype

`KernelSpec.shapes_by_dtype` is defined in `cluster1/data/kernels/spec.py:35-49`. Each locked C1 kernel now imports `get_compile_shapes` from `shared.eval.correctness_shapes`:

- ReLU / elementwise: `cluster1/data/kernels/elementwise_relu.py:16`, used in `RELU_SPEC.shapes_by_dtype` at `cluster1/data/kernels/elementwise_relu.py:69-72`.
- Softmax / reduction: `cluster1/data/kernels/reduction_softmax.py:16`, used in `SOFTMAX_SPEC.shapes_by_dtype` at `cluster1/data/kernels/reduction_softmax.py:69-72`.
- GEMM / matmul: `cluster1/data/kernels/matmul_tiled_gemm.py:16`, used in `GEMM_SPEC.shapes_by_dtype` at `cluster1/data/kernels/matmul_tiled_gemm.py:72-75`.

The shared compile shape anchors are defined in `shared/eval/correctness_shapes.py:114-137`; `get_compile_shapes` validates and returns them at `shared/eval/correctness_shapes.py:238-246`.

Runtime values inspected with `.venv/bin/python`:

- ReLU / elementwise:
  - `fp32`, `fp16`, `bf16`: `[(32,), (100,), (1024,), (3, 257), (5, 129)]`
- Softmax / reduction:
  - `fp32`, `fp16`, `bf16`: `[(16, 64), (33, 100), (128, 1001), (16384, 1), (1, 16384)]`
- GEMM / matmul:
  - `fp32`, `fp16`, `bf16`: `[(24, 24, 24), (48, 48, 48), (128, 128, 64), (100, 100, 100), (16384, 1, 1)]`

### C2 Level 2 correctness shape schedule

`shared/eval/levels/level2_correctness.py` imports `DEFAULT_SHAPES_PER_SPLIT`, `generate_correctness_shape_sets`, `get_shape_metadata`, and `validate_shape_for_kernel` from `shared.eval.correctness_shapes` at `shared/eval/levels/level2_correctness.py:14-22`. `evaluate_level2_correctness` generates shape sets when none are supplied at `shared/eval/levels/level2_correctness.py:158-164`, validates them at `shared/eval/levels/level2_correctness.py:165`, and evaluates repair/eval splits at `shared/eval/levels/level2_correctness.py:172-197`.

The C2 shape source is `shared/eval/correctness_shapes.py`:

- Locked metadata: `C2_SHAPE_METADATA` at `shared/eval/correctness_shapes.py:58-80`.
- Default count: `DEFAULT_SHAPES_PER_SPLIT = 6` at `shared/eval/correctness_shapes.py:30`.
- C2 anchors: `_ANCHOR_SHAPES` at `shared/eval/correctness_shapes.py:87-112`.
- Deterministic generation: `generate_correctness_shape_sets` at `shared/eval/correctness_shapes.py:195-235` and `generate_shape_set` at `shared/eval/correctness_shapes.py:249-286`.
- Caps: `MAX_DIM = 16384`, `MAX_ELEMENTS = 2**24` at `shared/eval/correctness_shapes.py:25-26`, enforced at `shared/eval/correctness_shapes.py:303-325`.
- Metadata alignment check: `validate_metadata_against_cluster1_specs` at `shared/eval/correctness_shapes.py:350-364`; runtime probe returned `validate_metadata_against_cluster1_specs: PASS`.

C2 shape sets are parametric in `base_seed`, `dtype`, and split. Cluster 2 remote correctness passes `request.identity.base_seed` into `PipelineLevel2Request` at `cluster2/modal/correctness_runner.py:79-88`; the shared pipeline forwards it to `evaluate_level2_correctness` at `shared/eval/pipeline.py:152-166`.

Runtime values for `base_seed=0`, `shapes_per_split=6`:

- ReLU / elementwise:
  - `fp32`: repair `[(1,), (32,), (100,), (1024,), (3, 257), (129,)]`; eval `[(2,), (33,), (257,), (4096,), (5, 129), (14319, 647)]`
  - `fp16`: repair `[(1,), (32,), (100,), (1024,), (3, 257), (31, 16145)]`; eval `[(2,), (33,), (257,), (4096,), (5, 129), (32, 1001)]`
  - `bf16`: repair `[(1,), (32,), (100,), (1024,), (3, 257), (512, 65, 155, 3)]`; eval `[(2,), (33,), (257,), (4096,), (5, 129), (7620, 1413)]`
- Softmax / reduction:
  - `fp32`: repair `[(1, 64), (16, 64), (33, 100), (128, 1001), (16384, 1), (16, 10482)]`; eval `[(2, 65), (17, 63), (64, 257), (129, 1000), (1, 16384), (16226, 33)]`
  - `fp16`: repair `[(1, 64), (16, 64), (33, 100), (128, 1001), (16384, 1), (3231, 3731)]`; eval `[(2, 65), (17, 63), (64, 257), (129, 1000), (1, 16384), (63, 14314)]`
  - `bf16`: repair `[(1, 64), (16, 64), (33, 100), (128, 1001), (16384, 1), (9505, 1539)]`; eval `[(2, 65), (17, 63), (64, 257), (129, 1000), (1, 16384), (33, 2913)]`
- GEMM / matmul:
  - `fp32`: repair `[(1, 1, 1), (24, 24, 24), (48, 48, 48), (128, 128, 64), (16384, 1, 1), (5119, 308, 1)]`; eval `[(2, 2, 2), (25, 25, 25), (64, 32, 128), (100, 100, 100), (1, 16384, 1), (12112, 1000, 1)]`
  - `fp16`: repair `[(1, 1, 1), (24, 24, 24), (48, 48, 48), (128, 128, 64), (16384, 1, 1), (12334, 257, 1)]`; eval `[(2, 2, 2), (25, 25, 25), (64, 32, 128), (100, 100, 100), (1, 16384, 1), (8051, 529, 3)]`
  - `bf16`: repair `[(1, 1, 1), (24, 24, 24), (48, 48, 48), (128, 128, 64), (16384, 1, 1), (2048, 31, 2)]`; eval `[(2, 2, 2), (25, 25, 25), (64, 32, 128), (100, 100, 100), (1, 16384, 1), (127, 8342, 1)]`

### Same KernelSpec source of truth?

Not exactly. C1 `KernelSpec.shapes_by_dtype` is populated from the shared `get_compile_shapes` API, while C2 Level 2 generates repair/eval sets independently from the same shared `correctness_shapes` metadata, anchors, caps, and seeded generator. The differences are explicit and non-confounding: compile probes are a deterministic compile-only subset/edge schedule in `_COMPILE_SHAPE_ANCHORS`, while correctness uses repair/eval anchors plus one dtype/base-seed-specific random valid shape per split. This satisfies the compatibility criterion because both schedules are controlled by the same shared shape module and the differences are intentional.

## 3. Item 2 - Signature gate audit

Classification: **INCOMPATIBLE**.

### C1 expected signatures and rejection codes

C1 first calls shared Level 0 parse and signature checks in `check_compiles` at `cluster1/validation/compile_check.py:193-216`. C1 then imports the generated module and performs an additional runtime signature gate, `validate_signature(module, spec)`, at `cluster1/validation/compile_check.py:160-176`; this requires exact `inspect.Signature` equality, including annotations and return annotation.

Expected C1 signatures:

- ReLU: `def relu(x: torch.Tensor) -> torch.Tensor`, defined by `_RELU_SIGNATURE` and `_RELU_COMPILE_SPEC` in `cluster1/data/kernels/elementwise_relu.py:48-59`.
- Softmax: `def softmax(x: torch.Tensor) -> torch.Tensor`, defined by `_SOFTMAX_SIGNATURE` and `_SOFTMAX_COMPILE_SPEC` in `cluster1/data/kernels/reduction_softmax.py:48-59`.
- GEMM: `def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor`, defined by `_MATMUL_SIGNATURE` and `_MATMUL_COMPILE_SPEC` in `cluster1/data/kernels/matmul_tiled_gemm.py:50-62`.

C1 rejection codes:

- Parse failure before import: `failure_code="F0_PARSE"` at `cluster1/validation/compile_check.py:193-202`.
- Shared Level 0 signature failure before import: `failure_code="F0_BAD_SIGNATURE"` at `cluster1/validation/compile_check.py:204-216`.
- Runtime import syntax error: `_classify_import_error` maps to `("SignatureError", "F0_PARSE")` at `cluster1/validation/compile_check.py:317-320`.
- Runtime import launcher/signature mismatch: `_classify_import_error` maps to `("SignatureError", "F0_BAD_SIGNATURE")` at `cluster1/validation/compile_check.py:321-322`.
- Runtime exact-signature mismatch after import: `failure_code="F0_BAD_SIGNATURE"` at `cluster1/validation/compile_check.py:232-242`.

### Shared Level 0 expected signature and rejection codes

Shared Level 0 is implemented in `shared/eval/levels/level0_parse.py`. It parses source without execution at `shared/eval/levels/level0_parse.py:28-31`, extracts expected parameter names from `expected_params`, `compile_spec.signature`, `compile_spec.reference_signature`, or `kernel_spec.reference_signature` at `shared/eval/levels/level0_parse.py:121-135`, resolves the launcher at `shared/eval/levels/level0_parse.py:106-118`, requires a top-level `@triton.jit` or `@jit` helper at `shared/eval/levels/level0_parse.py:37-40`, and compares parameter names only at `shared/eval/levels/level0_parse.py:91-103`.

Shared Level 0 expected parameter names:

- ReLU: `["x"]`
- Softmax: `["x"]`
- GEMM: `["a", "b"]`

Shared Level 0 rejection strings:

- Syntax: `SyntaxError: ...` from `shared/eval/levels/level0_parse.py:28-31`.
- Missing JIT helper: `F0_NO_DECORATOR: No @triton.jit decorated function found` from `shared/eval/levels/level0_parse.py:37-40` and `shared/eval/levels/level0_parse.py:55`.
- Launcher missing: `Signature mismatch: launcher '<name>' not found` from `shared/eval/levels/level0_parse.py:41-49`.
- Unsupported argument kind: `Signature mismatch: unsupported launcher argument kind` from `shared/eval/levels/level0_parse.py:91-98`.
- Parameter mismatch: `Signature mismatch: expected params [...], got [...]` from `shared/eval/levels/level0_parse.py:98-102`.

Shared taxonomy maps canonical signature fields to codes in `shared/eval/failure_taxonomy.py`: `signature_valid is False` maps to `F0_BAD_SIGNATURE` at `shared/eval/failure_taxonomy.py:86-87`, and legacy `SignatureError` maps through `LEGACY_FAILURE_CODE_MAP` at `shared/eval/failure_taxonomy.py:26-32`.

### Same code path or equivalent contract?

No. C1 uses the shared AST signature check, then adds a parallel runtime exact-signature check. The runtime probe confirmed the divergence:

- Source with `def relu(x): return x` plus a top-level `@jit` helper returned `level0_check_signature (True, None)`.
- The same source returned `c1_validate_signature signature mismatch for 'relu': expected (x: torch.Tensor) -> torch.Tensor, got (x)`.

Therefore the C1 and shared Level 0 gates do not enforce exactly the same contract. They agree on parameter-count/name mismatches but differ on annotations and return annotations. Rejection codes are also not fully equivalent at the gate surface: shared Level 0 returns strings, while C1 emits `CompileResult.failure_code`.

## 4. Item 3 - Failure classification audit

Classification: **COMPATIBLE**.

C1 compile emits canonical failure codes during generation:

- Local runner: `cluster1/experiments/run_cluster1.py:189-196` uses `first_error.failure_code` or `shared.eval.failure_taxonomy.canonical_failure_code_from_compile_error`.
- Modal runner conversion: `cluster1/experiments/run_cluster1_modal.py:838-851` maps remote labels and uses `canonical_failure_code_from_compile_error` when the remote did not provide a canonical code.
- Compile check: `cluster1/validation/compile_check.py:20` imports `canonical_failure_code_from_compile_error`; compile launch failures use it at `cluster1/validation/compile_check.py:253-263`.
- Dataclass invariants: `cluster1/results/dataclass.py:25-29` imports shared taxonomy constants/helpers; `validate_failure_code_invariants` requires canonical `FAILURE_CODES` at `cluster1/results/dataclass.py:108-134`; legacy rows are filled in memory by `generation_result_record_for_deserialization` at `cluster1/results/dataclass.py:441-472`.

C1 analyzer failure-code summaries use shared taxonomy:

- `cluster1/experiments/analyze_cluster1.py:27-28` imports `eval_result_from_generation_result` and `classify_failure`.
- `_failure_code_distribution_markdown` converts every row through the shared adapter and calls `classify_failure(eval_result)` at `cluster1/experiments/analyze_cluster1.py:725-770`.
- `_grammar_rejection_markdown` does the same for grammar-invalid rows at `cluster1/experiments/analyze_cluster1.py:804-851`.

There is a cluster-specific diagnostic table, `_compile_error_distribution_markdown`, which summarizes raw `compile_error_type` at `cluster1/experiments/analyze_cluster1.py:681-722`. That table is not the failure-code classification path; it is a legacy compile-error diagnostic. The canonical failure-code path uses `shared.eval.failure_taxonomy.classify_failure`, so C1 artifact failure classification is compatible with Cluster 2/shared eval.

## 5. Smallest fixes if incompatible

Signature gate: either make shared Level 0 enforce the same exact `inspect.Signature` contract as C1, or relax C1's post-import `validate_signature` to match shared Level 0's parameter-name contract after the shared AST gate has passed. The smallest low-blast-radius fix is in `cluster1/validation/compile_check.py`: remove or narrow the post-import exact annotation/return-annotation equality check so C1 relies on `check_signature` for the public launcher contract, then add regression tests showing annotationless but parameter-correct launchers are treated the same by C1 and shared Level 0. Expected validation command: `.venv/bin/python -m pytest cluster1/tests shared/tests -q`.

## 6. Final recommendation

**BLOCKED_BEFORE_N5**

No critical unknowns remain, but Item 2 is incompatible. Do not run the fresh task-agnostic G n=5 until the C1 runtime signature gate and shared Level 0 signature gate enforce the same contract or the difference is explicitly accepted in the evaluation criteria.

## Commands run

- `git status --short`
- `rg "shape|shapes|dtype|dtypes|KernelSpec|compile|dummy|launch" cluster1/validation cluster1/data cluster1/experiments shared/eval`
- `rg "expected_params|signature|launcher|return|failure_code|SIGNATURE|F0|F1" cluster1 shared/eval cluster2`
- `rg "classify_failure|failure_taxonomy|failure_code|compile_success|grammar_valid|summary" cluster1 shared/eval cluster2`
- `rg "level2_correctness|check_correctness|correctness|tolerance|atol|rtol" shared/eval cluster2 cluster1`
- `nl -ba cluster1/validation/compile_check.py`
- `nl -ba cluster1/data/kernels/elementwise_relu.py`
- `nl -ba cluster1/data/kernels/reduction_softmax.py`
- `nl -ba cluster1/data/kernels/matmul_tiled_gemm.py`
- `nl -ba shared/eval/correctness_shapes.py`
- `nl -ba shared/eval/levels/level2_correctness.py`
- `nl -ba shared/eval/levels/level0_parse.py`
- `nl -ba shared/eval/levels/level1_compile.py`
- `nl -ba shared/eval/failure_taxonomy.py`
- `nl -ba cluster1/experiments/analyze_cluster1.py`
- `nl -ba cluster1/experiments/validate_cluster1_results.py`
- `nl -ba cluster1/results/dataclass.py`
- `nl -ba cluster1/experiments/run_cluster1.py`
- `nl -ba cluster1/experiments/run_cluster1_modal.py`
- `nl -ba shared/eval/adapter_cluster1.py`
- `nl -ba cluster2/replay/cluster1_controls.py`
- `nl -ba cluster2/modal/correctness_runner.py`
- `rg -n "def remote_results_to_generation_result|compile_results_by_dtype|failure_code|check_compiles_modal|canonical_failure_code" cluster1/experiments/run_cluster1_modal.py`
- `nl -ba cluster1/validation/modal_compile_check.py`
- `nl -ba shared/modal_harness/compile.py`
- `nl -ba shared/eval/pipeline.py`
- `nl -ba cluster1/data/kernels/spec.py`
- `nl -ba cluster1/data/kernels/__init__.py`
- `nl -ba shared/modal_harness/compile_runner.py`
- `nl -ba shared/modal_harness/schemas.py`
- `sed -n '806,895p' cluster1/experiments/run_cluster1_modal.py | nl -ba -v806`
- `.venv/bin/python -c '...'` runtime probe for C1 signatures, C1 compile shapes, C2 `base_seed=0` shapes, and `DEFAULT_SHAPES_PER_SPLIT`
- `.venv/bin/python -c '...'` runtime probe for C2 `base_seed=0..4` shape schedules
- `.venv/bin/python -c '...'` runtime probe for `validate_metadata_against_cluster1_specs()`
- `.venv/bin/python -c '...'` runtime probe demonstrating shared Level 0 accepts an annotationless launcher while C1 `validate_signature` rejects it
- `ls audits`
- `nl -ba audits/cluster1_eval_path_pre_n5_audit.md`
