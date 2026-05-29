# Cross-Cluster Evaluation Alignment Plan

## 1. Executive summary

Recent audits identified a pre-n5 blocker class: Cluster 1 compile-only evaluation and Cluster 2 shared evaluation are not yet guaranteed to use the same evaluation semantics for shape schedules, signature gates, and failure-code classification. This is a comparability blocker because `compile_success`, `failure_code`, and downstream replay/control summaries can mean different things depending on whether a row passed through the older Cluster 1 path or the newer `shared/eval/` path.

n=5 task-agnostic G should wait until this alignment plan is implemented and verified. Running n=5 before alignment would create new rows whose compile and failure evidence may not be comparable to Cluster 2 correctness evidence or to the frozen none baseline.

This work is evaluation-path alignment, not generation-method redesign. It must not change prompts, grammar generation, repair generation, model settings, artifacts, manifests, hash records, or the scientific meaning of the experimental factors. The goal is to make `shared/eval/` the source of truth for evaluation behavior while preserving Cluster 1 legacy fields for compatibility.

This work also does not resolve the separate Cluster 1 grammar hash gate from the previous Modal generation audit. That gate is still expected to block n=5 until the recorded Phase -1 hash for `cluster1/grammar/triton_kernel_agnostic.gbnf` is reconciled with the current file. Because these alignment phases do not modify grammar files or re-record hashes, the grammar hash gate must be sequenced after baseline re-validation evidence exists and before the final cross-cluster re-audit.

## 2. Current codebase map

- Cluster 1 `KernelSpec` definitions:
  - Dataclass: `cluster1/data/kernels/spec.py::KernelSpec`.
  - Registry: `cluster1/data/kernels/__init__.py::KERNEL_SPECS`.
  - Concrete specs:
    - `cluster1/data/kernels/elementwise_relu.py::RELU_SPEC`.
    - `cluster1/data/kernels/reduction_softmax.py::SOFTMAX_SPEC`.
    - `cluster1/data/kernels/matmul_tiled_gemm.py::GEMM_SPEC`.
- Cluster 1 compile shape schedules:
  - `KernelSpec.shapes_by_dtype` in each concrete spec.
  - Current schedules are repeated identically for `fp32`, `fp16`, and `bf16`.
  - Current C1 examples include oversized relative to shared C2 caps:
    - ReLU: `(4096, 393216)`.
    - Softmax: `(4096, 393216)`.
    - Matmul: `(4096, 4096, 4096)`.
- Cluster 2 correctness shape schedules:
  - `shared/eval/correctness_shapes.py::generate_correctness_shape_sets`.
  - Anchor schema: private `_ANCHOR_SHAPES`.
  - Metadata: `C2_SHAPE_METADATA`, `CorrectnessShapeMetadata`, `CorrectnessShapeSets`.
  - Current patterns: `ND` for elementwise, `RxC` for reduction, `MNK` for matmul.
- Shared shape schedule helpers:
  - `shared/eval/correctness_shapes.py`.
  - Public helpers include `get_shape_metadata`, `get_shape_metadata_by_kernel_name`, `iter_shape_metadata`, `generate_shape_set`, `validate_shape_for_kernel`, `validate_shape_for_kernel_name`, `validate_shape_for_pattern`, `shape_num_elements`, and `derive_deterministic_seed`.
  - Caps are `MAX_DIM = 16384` and `MAX_ELEMENTS = 2**24`.
  - No `get_compile_shapes` helper exists yet.
- Cluster 1 compile validation:
  - `cluster1/validation/compile_check.py`.
  - Public functions: `load_generated_module`, `validate_signature`, `check_compiles`, `check_compiles_all_dtypes`.
  - It currently imports generated code and uses `inspect.signature` against `CompileSpec.reference_signature` before dummy Triton launches.
  - `check_compiles_all_dtypes` consumes `shapes_by_dtype`.
- Shared Level 0 parse/signature gate:
  - `shared/eval/levels/level0_parse.py`.
  - Public functions: `check_parse(source)` and `check_signature(source, kernel_spec)`.
  - It is AST-only, does not import generated source, and validates launcher params plus `@triton.jit` helper presence.
- Shared Level 1 compile gate:
  - `shared/eval/levels/level1_compile.py::check_compile_level1`.
  - It currently delegates to `cluster1.validation.compile_check.check_compiles_all_dtypes`, wrapping the result in `Level1CompileResult`.
  - It does not currently call shared Level 0 before delegating.
- Shared Level 2 correctness gate:
  - `shared/eval/levels/level2_correctness.py::evaluate_level2_correctness`.
  - It consumes `generate_correctness_shape_sets` when no explicit shape sets are passed.
  - `shared/eval/pipeline.py` wires optional Level 2 requests through `PipelineLevel2Request`.
- Cluster 1 analyzer failure summaries:
  - `cluster1/experiments/analyze_cluster1.py`.
  - Current failure summary is `_compile_error_distribution_markdown(rows)`, grouped by legacy `GenerationResult.compile_error_type`.
  - It does not yet use `shared.eval.adapter_cluster1.eval_result_from_generation_result` or `shared.eval.failure_taxonomy.classify_failure`.
- Shared failure taxonomy:
  - `shared/eval/failure_taxonomy.py`.
  - Canonical codes include `F0_BAD_SIGNATURE`, `F1_COMPILE`, `F1_RUNTIME`, and F2/F3 codes.
  - `LEGACY_FAILURE_CODE_MAP` maps Cluster 1 labels:
    - `SyntaxError -> F0_PARSE`.
    - `NoDecoratorError -> F0_NO_DECORATOR`.
    - `SignatureError -> F0_BAD_SIGNATURE`.
    - `CompilationError -> F1_COMPILE`.
    - `RuntimeError -> F1_RUNTIME`.
- Shared Cluster 1 adapter:
  - `shared/eval/adapter_cluster1.py::eval_result_from_generation_result`.
  - It maps `GenerationResult.compile_error_type` into `EvalResult.failure_code`, relying on taxonomy classification to canonicalize legacy labels.
- Cluster 1 row schema:
  - `cluster1/results/dataclass.py::GenerationResult` currently has `compile_error_type` and no canonical `failure_code` field.
  - The alignment implementation should add canonical `failure_code` to new C1 rows while preserving `compile_error_type`.
  - It already carries instrumentation metadata fields such as `grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, `stop_reason`, library/model/tokenizer revisions, and Modal image metadata; Phase 3.4 ties these fields into analysis and taxonomy.
- Cluster 1 baseline artifact:
  - `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
  - Sidecar: `outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json`.
  - Cluster 2 constants also reference it as `cluster2/constants.py::FROZEN_NONE_REPLAY_ARTIFACT`.
  - Frozen manifest: `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, artifact id `none_baseline_n20_l4`.
  - Existing frozen rows are expected to remain legacy-shaped on disk. For example, the none baseline contains legacy `compile_error_type` values such as `SignatureError`; those rows should be canonicalized at read/analysis/replay time, not rewritten.
- Existing baseline diagnostic/revalidation utilities:
  - Existing diagnostic utility: `shared/eval/diagnostics/permissive_compile.py`.
  - Existing local-vs-Modal validation checks appear in `cluster1/experiments/run_cluster1_modal.py` and `cluster2/experiments/run_cluster2_modal.py`, but no dedicated `baseline_revalidation_aligned_pipeline` utility exists.
  - Existing analysis utilities include `shared/analysis/factorial.py`.

## 3. Problem statement

Independent C1/C2 evaluation logic is a comparability risk because results can share names while being produced by different semantics.

Specific risks:

- Same kernel label but different shape schedule: `kernel_class="matmul"` in C1 currently compiles against hard-coded `KernelSpec.shapes_by_dtype`, while C2 correctness uses shared `MNK` anchors and caps from `shared/eval/correctness_shapes.py`.
- Same signature concept but different rejection code: C1 runtime import plus `inspect.signature` returns legacy `SignatureError`, while shared Level 0 AST validation should canonicalize this as `F0_BAD_SIGNATURE`.
- Same failure summary but different taxonomy: C1 analyzer reports legacy `compile_error_type`; Cluster 2 and shared evaluation reason about canonical `failure_code`.
- Analyzer/replay split risk: if C1 analysis canonicalizes legacy baseline rows as `F0_BAD_SIGNATURE` but Cluster 2 replay consumes the same rows as legacy `SignatureError`, documentation and replay behavior diverge even though they reference the same frozen artifact.
- Baseline artifact evaluated under an older or parallel path: the frozen none baseline may have `compile_success=false` for all rows, but until it is revalidated through the aligned pipeline, those failures are diagnostic evidence from the old path rather than current shared semantics.

## 4. Phase 1 — Shape schedule alignment plan

### Decision

C1 compile shapes and C2 correctness shapes should be semantically distinct but derived from one shared anchor schema. They should not be identical by default:

- C1 compile shapes should be a small deterministic compile-probe subset that catches structural launch/JIT issues across edge cases.
- C2 correctness shapes should remain repair/eval sets with disjointness, deterministic seed derivation, and numeric-comparison coverage.

The source of truth should be `shared/eval/correctness_shapes.py`, extended with a compile-shape public helper rather than duplicating schedules inside Cluster 1 specs.

### Proposed helper

Add:

```python
shared/eval/correctness_shapes.py::get_compile_shapes(kernel_class: str, dtype: str) -> tuple[Shape, ...]
```

Recommended behavior:

- Validate `kernel_class` via `get_shape_metadata`.
- Validate `dtype` via existing `_require_dtype`.
- Return a deterministic, dtype-stable tuple of shapes derived from the same `shape_pattern` and anchor vocabulary as C2 correctness.
- Use explicit compile anchors rather than random shape generation so C1 compile behavior is stable across runs and independent of `base_seed`.
- Validate all returned shapes with `validate_shape_for_kernel`.

### Relationship to C2 correctness anchors

Recommended implementation is a strict subset of the union of C2 repair/eval anchors for now, plus an explicit extension point for future compile-only anchors if needed. This is the conservative path because it proves every C1 compile shape is also valid under the shared C2 cap/schema.

Initial candidate compile subsets:

- elementwise/ND: include `(32,)`, `(100,)`, `(1024,)`, and one valid 2D edge such as `(5, 129)` or `(3, 257)`.
- reduction/RxC: include `(16, 64)`, `(33, 100)`, `(128, 1001)`, and a cap edge such as `(16384, 1)` or `(1, 16384)`.
- matmul/MNK: include `(24, 24, 24)`, `(48, 48, 48)`, `(128, 128, 64)`, `(100, 100, 100)`, and a cap edge such as `(16384, 1, 1)` or `(1, 16384, 1)`.

Do not carry forward oversized C1-only shapes that violate `MAX_ELEMENTS`, such as `(4096, 393216)` or `(4096, 4096, 4096)`, unless the team explicitly creates a separate compile-only cap policy and accepts the cost.

Implementation must record a one-paragraph justification per kernel class in `shared/eval/correctness_shapes.py` near the compile-shape anchors. The justification should identify which edge each shape covers, such as smaller-than-block, non-divisible, non-power-of-two, rank/arity edge, and cap-edge coverage. This makes the reduced compile schedule auditable rather than an implicit choice.

### Cluster 1 `KernelSpec` derivation

After the helper exists, update the three C1 concrete specs so:

```python
shapes_by_dtype = {
    dtype: list(get_compile_shapes(kernel_class, dtype))
    for dtype in ("fp32", "fp16", "bf16")
}
```

Do this inside the spec modules or via a small shared helper imported by those modules. Keep `KernelSpec` field names unchanged for backward compatibility; `check_compiles_all_dtypes` should still receive `shapes_by_dtype`.

### Bounds/caps

- All compile shapes must satisfy `max(shape) <= MAX_DIM`.
- All compile shapes must satisfy `math.prod(shape) <= MAX_ELEMENTS`.
- C1 must stop owning independent cap exceptions.
- If C1 needs a larger compile-only stress shape, add a separately named policy in `shared/eval/correctness_shapes.py`, for example `COMPILE_MAX_ELEMENTS`, and document why it differs. Do not silently bypass C2 caps.

### Required tests

- Add `shared/tests/test_shape_schedule_consistency.py`.
- Update `shared/tests/test_correctness_shapes.py` if the helper belongs there too.
- Update `cluster1/tests/test_kernel_specs.py` to assert `spec.shapes_by_dtype[dtype] == list(get_compile_shapes(spec.kernel_class, dtype))`.
- Optionally add a cross-cluster constants/alignment test asserting compile shapes validate under `validate_shape_for_kernel`.

### Acceptance criteria

- `get_compile_shapes` exists and is the only source for C1 compile shapes.
- Every C1 `KernelSpec.shapes_by_dtype` entry is derived from `get_compile_shapes`.
- Every C1 compile shape validates under the shared shape pattern and caps.
- C1 compile shapes remain non-empty for all `kernel_class x dtype` cells.
- No C2 correctness repair/eval behavior changes unless explicitly required and covered by tests.
- C2 correctness smoke-related tests pass, proving Phase 1 did not alter the existing C2 repair/eval anchor schedule or smoke behavior.

Phase classification when complete: `PHASE_1_READY`.

## 5. Phase 2 — Signature gate alignment plan

### Desired flow

C1 compile validation should call shared Level 0 signature validation before runtime import:

1. In `cluster1/validation/compile_check.py::check_compiles`, explicitly run the shared Level 0 parse check first.
2. If AST parse fails outright, return a structured failure that preserves the legacy C1 surface while recording canonical `F0_PARSE`.
3. If parse passes, call `shared.eval.levels.level0_parse.check_signature(source, kernel_spec_like)` or a wrapper that can accept `CompileSpec`.
4. If Level 0 signature validation rejects, return `CompileResult(success=False, error_type="SignatureError", ...)` to preserve the legacy Cluster 1 surface and record canonical `F0_BAD_SIGNATURE`.
5. Only after Level 0 parse/signature passes, continue to `load_generated_module`, runtime import, `validate_signature`, and dummy launches as the explicit Level 1 compile path.

C1 compile validation should own both Level 0 and Level 1 calls explicitly. `shared/eval/levels/level1_compile.py::check_compile_level1` should remain a thin Level 1 wrapper/delegate and should not implicitly invoke Level 0, because the ordering is easier to audit and debug when C1 owns the visible transition.

### API gap to resolve

`check_compiles` currently receives a `CompileSpec`, not a full `KernelSpec`. `check_signature` can derive params from `compile_spec.reference_signature`, but it also needs launcher name and expects a `kernel_spec`-like object. Implementation options:

- Preferred: introduce a small shared helper or local `SimpleNamespace(compile_spec=spec, launcher_name=spec.launcher_name)` adapter inside compile checking.
- Alternative: adjust `check_compiles` signature to receive `KernelSpec`, but this has wider blast radius and should be avoided unless needed.

### Runtime import / `inspect.signature`

Keep runtime import and `inspect.signature` as a secondary check. The AST Level 0 gate catches deterministic source-level signature failures without executing code. Runtime inspection still protects against import-time aliasing or dynamic behavior after module load. If runtime inspection fails after Level 0 passed, preserve legacy `SignatureError` but classify it canonically as `F0_BAD_SIGNATURE` unless the failure is truly a runtime launch failure.

### Canonical failure codes

Expected canonical mappings:

- Level 0 signature rejection: `F0_BAD_SIGNATURE`.
- AST parse failure before runtime import: `F0_PARSE`.
- Runtime import errors after AST parse succeeds: keep legacy `SignatureError` only when needed for compatibility, but canonicalize according to cause. Signature mismatches remain `F0_BAD_SIGNATURE`, because the row is Python code but does not satisfy the launcher contract.
- Compile-time Triton compiler error: `F1_COMPILE`.
- Dummy launch/runtime exception not classified as Triton compiler error: `F1_RUNTIME`.

### Preserve legacy `compile_error_type`

Do not remove or rename `GenerationResult.compile_error_type`. Continue writing:

- `SignatureError`.
- `CompilationError`.
- `RuntimeError`.
- `None`.

Alignment decision: add canonical `failure_code` to all new Cluster 1 rows. Future analyses need a stable canonical field instead of recomputing taxonomy from legacy `compile_error_type`. Implementation should:

- Extend `cluster1/results/dataclass.py::GenerationResult` with `failure_code: str | None`.
- Preserve `compile_error_type` unchanged for historical compatibility.
- Populate `failure_code=None` when `compile_success=True`.
- Populate `failure_code` with `F0_PARSE`, `F0_BAD_SIGNATURE`, `F1_COMPILE`, or `F1_RUNTIME` for compile-path failures.
- Keep deserialization compatibility for older frozen rows that lack `failure_code`, deriving it through `eval_result_from_generation_result` and `classify_failure` when reading old artifacts.
- Update Cluster 1 result validation tests and JSONL logger tests to require `failure_code` on new rows without mutating old artifacts.

### Required tests

- Add `cluster1/tests/test_signature_gate_consistency.py`.
- Cover:
  - C1 compile gate calls shared Level 0 before `load_generated_module`.
  - AST parse failure maps to canonical `F0_PARSE`.
  - Missing launcher maps to legacy `SignatureError` and canonical `F0_BAD_SIGNATURE`.
  - Wrong launcher params maps to legacy `SignatureError` and canonical `F0_BAD_SIGNATURE`.
  - Valid source still proceeds to runtime import/compile path.
  - Runtime import/`inspect.signature` remains a secondary guard.
- Keep `shared/tests/test_eval_level1_compile.py` focused on Level 1 delegation; do not make Level 1 implicitly invoke Level 0.

### Acceptance criteria

- Shared Level 0 is the first signature authority for C1 compile validation.
- C1 explicitly owns Level 0 parse/signature followed by Level 1 compile ordering.
- C1 legacy `compile_error_type` remains backward-compatible.
- New C1 rows include canonical `failure_code`.
- Aligned diagnostics can report canonical `F0_PARSE` and `F0_BAD_SIGNATURE` distinctly.
- Level 1 compile errors remain distinguishable as `F1_COMPILE` or `F1_RUNTIME`.

Phase classification when complete: `PHASE_2_READY`.

## 6. Phase 3 — Failure classification alignment plan

### Desired analyzer behavior

Update `cluster1/experiments/analyze_cluster1.py` so failure summaries use shared taxonomy:

```python
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.failure_taxonomy import classify_failure
```

For each `GenerationResult` row:

1. Convert to `EvalResult` using `eval_result_from_generation_result(row, sample_index=...)`.
2. Classify with `classify_failure(eval_result)`.
3. Prefer the row's canonical `failure_code` when present; for older rows without the field, derive it from legacy fields through the adapter and taxonomy.
4. Use the canonical value for the primary failure distribution.
5. Keep `compile_error_type` as a secondary diagnostic table or an additional column in the failure summary.

### Legacy labels

Legacy compile error labels must remain available because historical reports, frozen artifacts, and Cluster 1 code use them. They should no longer be the primary cross-cluster failure taxonomy. Primary current analysis should be canonical:

- `SignatureError -> F0_BAD_SIGNATURE`.
- `CompilationError -> F1_COMPILE`.
- `RuntimeError -> F1_RUNTIME`.
- `None -> None` for successful compile rows.
- AST parse failures in new rows should be `F0_PARSE`, not `F0_BAD_SIGNATURE`.

### Required tests

- Add `cluster1/tests/test_analyzer_uses_shared_taxonomy.py`.
- Update `cluster1/tests/test_analysis.py` where existing expected markdown assumes only `compile_error_type`.
- Cover:
  - Analyzer reports canonical failure-code distribution.
  - Legacy compile error distribution is still present as secondary diagnostics.
  - A row with `compile_error_type="SignatureError"` appears under `F0_BAD_SIGNATURE`.
  - A row with `compile_error_type="CompilationError"` appears under `F1_COMPILE`.
  - A new row with `failure_code="F0_PARSE"` appears under `F0_PARSE`.
  - Successful rows produce `None` or an explicit success bucket without misclassifying failures.

### Acceptance criteria

- Analyzer primary failure summary is canonical shared taxonomy.
- Analyzer uses row-level canonical `failure_code` for new rows.
- Legacy `compile_error_type` remains visible for compatibility.
- Existing compile metrics (`compile@1`, strict all-dtype scope, prompt-dtype compile success) are unchanged.
- Historical summaries may change in text/table labels, but the underlying row data is not modified.

Phase classification when complete: `PHASE_3_READY`.

### Phase 3.4 — Instrumentation metadata and grammar taxonomy integration

### Purpose

Recent generation metadata instrumentation adds runtime/provenance and grammar-validation fields that must be part of the same canonical analysis surface as compile and replay failures. The alignment work touches the analyzer and C1 evaluation path, so it must connect these metadata fields to the shared taxonomy instead of leaving a parallel "grammar_valid" classification beside canonical `failure_code`.

### Metadata fields to consume

The analyzer must consume and surface the new C1 metadata fields:

- `grammar_sha`.
- `gbnf_parse_valid`.
- `semantic_valid`.
- `grammar_valid`.
- `rejection_layer`.
- `stop_reason`.
- `xgrammar_version`.
- `transformers_version`.
- `tokenizers_version`.
- `model_revision`.
- `tokenizer_revision`.
- `modal_image_sha`.

If the current schema also exposes image provenance fields such as `modal_image_provenance_sha256` and `modal_image_provenance_components`, the analyzer should preserve them as provenance diagnostics without making them paper-facing failure categories.

### Canonical grammar failure codes

Extend `shared/eval/failure_taxonomy.py::FAILURE_CODES` and `classify_failure` with explicit grammar-surface codes:

- `F0_GBNF_PARSE`: `grammar_active=True`, `gbnf_parse_valid=False`.
- `F0_SEMANTIC_INVALID`: `grammar_active=True`, `gbnf_parse_valid=True`, `semantic_valid=False`.
- `F0_GRAMMAR_INVALID`: fallback when `grammar_active=True`, `grammar_valid=False`, but the layer-specific booleans are missing or inconclusive.

Classification precedence should be:

1. Preserve explicit canonical row `failure_code` when present.
2. Classify grammar-invalid rows before compile/runtime classification because grammar rejection occurs before compile evaluation.
3. Then apply parse/signature/compile/runtime/correctness/sanitizer classification.

### Analyzer behavior

Update `cluster1/experiments/analyze_cluster1.py` so reports include:

- Canonical failure distribution including grammar failure codes.
- Metadata completeness summary for current-schema rows.
- Grammar rejection summary by `rejection_layer`, `gbnf_parse_valid`, `semantic_valid`, and `grammar_valid`.
- Provenance summary for model/tokenizer/library/image fields.

Do not make these metadata summaries alter existing compile metrics. `compile@1`, strict all-dtype scope, and prompt-dtype compile success remain compile-path metrics.

### Required tests

- Add or update C1 analysis tests that create rows with:
  - `gbnf_parse_valid=False`, `semantic_valid=False`, `grammar_valid=False`, expecting `F0_GBNF_PARSE`.
  - `gbnf_parse_valid=True`, `semantic_valid=False`, `grammar_valid=False`, expecting `F0_SEMANTIC_INVALID`.
  - `grammar_valid=False` with missing layer booleans, expecting `F0_GRAMMAR_INVALID`.
- Add/update shared taxonomy tests for the new F0 grammar codes.
- Add analyzer tests proving metadata fields are surfaced without mutating row records.

### Acceptance criteria

- Analyzer consumes and reports the new metadata fields.
- Shared taxonomy owns grammar-invalid classification.
- No parallel grammar-only failure taxonomy remains outside `shared/eval/failure_taxonomy.py`.
- Existing frozen rows without current metadata remain readable.

Phase classification when complete: `PHASE_3_4_READY`.

### Phase 3.5 — Cluster 2 replay canonicalization plan

### Purpose

Frozen Cluster 1 artifacts must remain unchanged on disk, but every current consumer should see the same canonical failure semantics. After Phase 3, `cluster1/experiments/analyze_cluster1.py` will report the frozen none baseline's legacy `compile_error_type="SignatureError"` rows as `F0_BAD_SIGNATURE`. Cluster 2 replay should do the same canonicalization instead of continuing to operate on legacy labels directly.

### Required behavior

Update the Cluster 2 replay path that reads `outputs/cluster1/baseline_repaired_l4_n20.jsonl` and other frozen Cluster 1 replay controls so it canonicalizes rows through the same shared adapter/taxonomy route used by the analyzer:

```python
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.failure_taxonomy import classify_failure
```

For each replayed Cluster 1 row:

1. Deserialize the frozen row without modifying it.
2. Convert it with `eval_result_from_generation_result`.
3. Compute canonical `failure_code = classify_failure(eval_result)`.
4. Use the canonical code for Cluster 2 replay result fields, repair-loop gating, summaries, and route diagnostics.
5. Preserve the original legacy `compile_error_type` as a secondary diagnostic/provenance field when useful.

### Backward compatibility

- Existing frozen artifacts are not rewritten.
- Existing manifests and hashes remain valid because replay canonicalization happens at read time.
- New C1 rows should already carry canonical `failure_code`; the adapter/taxonomy path remains the fallback for older rows without that field.
- If a replay schema currently exposes only `failure_code`, that field should contain the canonical code, not the legacy `compile_error_type`.
- If a replay schema needs the legacy label, use a separate field such as `legacy_compile_error_type` or preserve it inside an optional diagnostics block.

### Likely files to inspect/update

- `cluster2/experiments/run_cluster2_modal.py`.
- `cluster2/results/dataclass.py`.
- `cluster2/results/logger.py`.
- `cluster2/feedback/repair_loop.py`.
- `cluster2/tests/test_replay_controls.py`.
- `cluster2/tests/test_run_cluster2_modal.py`.
- `cluster2/tests/test_results_logger.py`.

The exact edit points must be confirmed during implementation with static inspection before changing code.

### Required tests

- Add or update a Cluster 2 replay test, likely in `cluster2/tests/test_replay_controls.py` or `cluster2/tests/test_run_cluster2_modal.py`, that feeds a frozen-style C1 row with `compile_error_type="SignatureError"` and no row-level `failure_code`.
- Assert replay output uses canonical `failure_code="F0_BAD_SIGNATURE"`.
- Assert the legacy label is still available only as secondary diagnostics/provenance if the schema exposes it.
- Assert no artifact rewrite occurs.
- Assert analyzer and replay produce the same canonical distribution for the same synthetic legacy rows.

### Acceptance criteria

- C1 analyzer and C2 replay agree on canonical codes for frozen legacy rows.
- Cluster 2 replay does not use legacy `compile_error_type` as the primary failure code.
- Existing frozen artifacts, sidecars, manifests, and hashes remain unchanged.
- New C1 row-level canonical `failure_code` is honored directly when present.
- Old C1 rows without `failure_code` canonicalize through `eval_result_from_generation_result` and `classify_failure`.

Phase classification when complete: `PHASE_3_5_READY`.

## 7. Phase 4 — Baseline re-validation plan

### Purpose

After phases 1-3.5 are implemented, run the frozen Cluster 1 none baseline through the aligned pipeline as a diagnostic comparison. This is re-validation, not regeneration. It must not modify the original artifact. Real compile re-validation requires CUDA, so Phase 4 includes one explicit Modal L4 baseline re-validation run after the local diagnostic utility and tests pass.

### Input artifact

`outputs/cluster1/baseline_repaired_l4_n20.jsonl`

### Output artifact

`outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl`

### Non-mutating requirement

- Do not edit `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- Do not edit `outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json`.
- Do not update `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`.
- Do not re-record hashes during the implementation phases.

### Workflow

Create a dedicated diagnostic utility, for example:

`cluster1/diagnostics/revalidate_baseline_aligned_pipeline.py`

The utility should:

1. Read the frozen JSONL artifact.
2. Deserialize each row as `GenerationResult`.
3. Route through the aligned shared/C1 evaluation path.
4. Compute the new compile result and canonical failure code.
5. Write one diagnostic JSONL row per input row.
6. Never append fields to the input artifact.

### Output row fields

Each output row must record:

- `row_index` or `row_id`.
- `kernel_class`.
- `kernel_name`.
- `dtype`.
- `generation_seed` if present.
- `base_seed` if available or derivable from seed schedule.
- `original_compile_success`.
- `new_compile_success`.
- `original_compile_error_type`.
- `original_failure_code` if present.
- `new_compile_error_type` if produced.
- `new_canonical_failure_code`.
- `agreement` boolean.
- `drift_reason` if changed.
- Optional: `original_compile_error_msg`, truncated `new_compile_error_msg`, `n_shapes_tested_original`, `n_shapes_tested_new`.

### Expected outcome

The expected diagnostic outcome is:

- Ideally `180/180` agreement.
- All rows remain `compile_success=false`.
- Most or all failures likely map to canonical signature-related codes, especially `F0_BAD_SIGNATURE`, if the baseline failures were legacy `SignatureError`.

### Drift decision tree

For development decision-making before n=5:

- `0` compile-success drift rows:
  - Proceed to the grammar hash re-record interlock after confirming canonical label mapping is documented.
- `1-5` compile-success drift rows:
  - Hold n=5.
  - Investigate each drifted row individually.
  - Record source hash, row index, kernel class, dtype, old/new compile result, old/new error labels, and root cause.
  - If every row is explained as a methodology refinement where the aligned pipeline is more correct, accept the drift only with a written methodology note and include the diagnostic artifact in the re-audit evidence.
  - If any row reveals an alignment bug, fix the relevant Phase 1-3.5 implementation and rerun Phase 4.
- `6+` compile-success drift rows:
  - Treat as an alignment regression.
  - Revisit Phases 1-3.5 before n=5 can proceed.
  - Do not re-record the grammar hash gate and do not start Phase 5 until the regression is resolved.
- Disagreement only in legacy-vs-canonical label is acceptable if:
  - the source row is unchanged,
  - the old legacy label maps deterministically via `LEGACY_FAILURE_CODE_MAP`,
  - the canonical code is documented in the diagnostic output,
  - the total compile-success count remains unchanged.
- Label drift within expected legacy-to-canonical boundaries is acceptable, for example `SignatureError -> F0_BAD_SIGNATURE`.
- Label drift across semantic categories requires per-row investigation even when `compile_success` is unchanged. Examples include `SignatureError -> F0_PARSE`, `SignatureError -> F1_RUNTIME`, or `CompilationError -> F0_BAD_SIGNATURE`.
- The diagnostic artifact must flag cross-category label drift separately from expected legacy-to-canonical mapping.

### Local vs Modal

The re-validation workflow is local-first for unit/integration testing, but the evidence-bearing baseline re-validation run must use Modal L4 because Triton dummy compile requires CUDA and the original baseline was produced through Modal. Schedule one Modal L4 baseline re-validation run as part of Phase 4 after local tests pass. Budget approximately one hour of L4 time.

The Modal run must:

- Use the aligned pipeline from Phases 1-3.5.
- Read `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- Execute each of the 180 baseline sources through both the C1-entrypoint aligned evaluation path and the C2-entrypoint aligned evaluation path.
- Assert the C1-entrypoint and C2-entrypoint results are identical per row after canonicalization.
- Write only `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl` and any explicitly approved diagnostic sidecar.
- Not modify the original baseline artifact, sidecar, manifests, grammar files, or hashes.
- Capture Modal provenance sufficient to compare environment and image metadata against the original baseline.

Modal GPU policy:

- Preferred: L4, matching the original baseline execution class.
- Acceptable fallback: A10, only if L4 is unavailable and the diagnostic artifact records the GPU divergence and rationale.
- Insufficient fallback: T4 or below. Do not use T4-or-lower evidence to close Phase 4 because memory/tensor-core behavior differs enough from the original baseline class.
- If neither L4 nor A10 is available, hold Phase 4 rather than accepting local-only evidence.

### Required tests

- Add a baseline revalidation unit test if feasible, using small synthetic `GenerationResult` rows and monkeypatched compile/shared gates.
- The test should verify:
  - original input file is not modified,
  - output diagnostic path is written,
  - agreement and drift fields are computed,
  - canonical failure code is produced through shared taxonomy.

### Acceptance criteria

- Diagnostic utility exists and is covered by tests.
- It reads the frozen baseline artifact and writes only the diagnostic artifact.
- It reports compile agreement and canonical failure codes per row.
- It reports C1-entrypoint vs C2-entrypoint equality per baseline row.
- Every baseline row has identical C1-entrypoint and C2-entrypoint aligned results after canonicalization.
- Cross-category label drift is either absent or documented with row-level root cause.
- It can run locally in mocked/unit mode.
- One Modal L4 baseline re-validation run is completed and interpreted with the drift decision tree before the grammar hash re-record and Phase 5 final re-audit.

Phase classification when implementation plus diagnostic design are ready: `PHASE_4_READY`.

## 8. Phase 5 — Final cross-cluster compatibility re-audit plan

### Pre-audit interlock — Cluster 1 grammar hash gate

#### Status

The Cluster 1 grammar hash gate is not resolved by Phases 1-4. The previously identified issue is that the recorded Phase -1 hash for `cluster1/grammar/triton_kernel_agnostic.gbnf` does not match the current grammar file. This alignment plan intentionally does not edit grammar files and does not re-record hashes during Phases 1-4.

#### Required sequencing

Resolve this gate after Phase 4 completes and before Phase 5 begins:

1. Phase 1 aligns shared/C1 shape schedules.
2. Phase 2 aligns C1 Level 0/Level 1 signature and compile ordering.
3. Phase 3 aligns C1 canonical failure recording and analysis.
4. Phase 3.4 integrates instrumentation metadata and grammar-validity failures into the shared taxonomy/analyzer.
5. Phase 3.5 aligns Cluster 2 replay consumption of frozen Cluster 1 rows with the same canonical taxonomy.
6. Phase 4 produces Modal L4 baseline re-validation evidence under the aligned pipeline.
7. Reconcile and re-record the Cluster 1 grammar hash gate only after Phase 4 has passing evidence.
8. Phase 5 then reruns the final cross-cluster compatibility re-audit with both evaluation alignment and grammar hash provenance clean.

#### Rationale

The grammar hash re-record should not happen before Phase 4 because baseline re-validation is the evidence that the current aligned pipeline treats frozen baseline inputs compatibly. Re-recording the hash earlier would update provenance before the evaluation path is proven stable.

#### Acceptance criteria

- Phase 4 Modal L4 re-validation has no unexplained compile-success drift, or has only accepted 1-5 row drift documented under the decision tree.
- Phase 4 side-by-side C1-entrypoint vs C2-entrypoint baseline comparison is identical for all 180 rows after canonicalization.
- The hash re-record task is explicit and separate from evaluation alignment implementation.
- The grammar file is not modified as part of the hash re-record unless a separate grammar-change task authorizes it.
- The updated Phase -1 grammar hash matches the current `cluster1/grammar/triton_kernel_agnostic.gbnf`.
- Phase 5 includes this gate in its final re-audit.

### Re-audit to run

Rerun the cross-cluster compatibility audit that produced the current blocker list, specifically checking:

- shape schedule compatibility,
- signature gate compatibility,
- failure-code classification compatibility,
- instrumentation metadata and grammar-failure taxonomy compatibility,
- Cluster 2 replay canonicalization of frozen Cluster 1 rows,
- baseline re-validation against the current aligned pipeline.
- Cluster 1 grammar hash gate status for `cluster1/grammar/triton_kernel_agnostic.gbnf`.

If no dedicated script exists, create a small read-only audit under tests or diagnostics that asserts the contracts now enforced by phases 1-4.

### Expected outcome

Resolved incompatibilities:

- C1 compile shapes derive from shared shape helpers.
- C1 compile signature rejection uses shared Level 0 semantics before runtime import.
- C1 analyzer reports canonical shared failure codes as primary failure taxonomy.
- C1 analyzer surfaces current instrumentation metadata and classifies grammar-invalid rows through shared F0 grammar codes.
- Cluster 2 replay reports canonical shared failure codes for frozen Cluster 1 rows while preserving legacy labels only as secondary diagnostics.
- Frozen none baseline has a Modal L4 diagnostic re-validation report through the aligned path.
- The actual 180 baseline sources have identical C1-entrypoint and C2-entrypoint aligned results.
- The recorded Phase -1 grammar hash matches the current grammar file after the post-Phase-4 re-record.

Items that may remain deferred:

- Missing P implementation.
- Missing n=20 task-agnostic G artifact.
- F3 sanitizer/performance levels, which are outside this compile/correctness alignment effort.

### Go/hold/block criteria

- Go to n=5 only if phases 1-3.5 are verified, Phase 4 Modal L4 baseline re-validation evidence is acceptable under the drift decision tree, the grammar hash gate has been reconciled, and the Phase 5 final re-audit is clean.
- Hold if shape helper exists but C1 specs still contain independent hard-coded schedules.
- Hold if analyzer emits only legacy `compile_error_type`.
- Hold if analyzer treats `grammar_valid` failures as metadata-only rather than canonical F0 grammar failures.
- Hold if Cluster 2 replay emits legacy `compile_error_type` as primary `failure_code`.
- Block if baseline re-validation shows unexplained compile-success drift.
- Block if Phase 4 is only local/mocked and no Modal L4 baseline re-validation has run.
- Block if any of the 180 baseline sources produce different C1-entrypoint vs C2-entrypoint aligned results after canonicalization.
- Block if the Cluster 1 grammar hash gate remains unresolved after Phase 4.
- Block if implementation modifies frozen artifacts, manifests, hashes, production generation code, or invokes Modal/generation during alignment.

Phase classification after successful re-audit: `PLAN_CONFIRMED`; otherwise `PLAN_BLOCKED`.

### Phase 5.5 — Contract documentation consolidation

After Phase 5 technical re-audit passes and before any n=5 GO decision, update contracts to reflect the implemented behavior. This is a documentation phase, not a code or artifact rewrite phase.

Required contract updates:

- `.contracts/research/research_scope.md`: factor definitions must match the current code and replay behavior.
- `.contracts/agentic/cluster1_contract.md`: document C1 ownership of explicit Level 0 then Level 1 ordering, shared-derived compile shapes, canonical `failure_code` in new rows, and grammar metadata taxonomy integration.
- `.contracts/agentic/cluster2_contract.md`: document replay canonicalization of frozen C1 rows and `DEFAULT_MAX_NEW_TOKENS = 1536` / `max_new_tokens=1536` behavior from the current C2 generation path.
- `.contracts/research/eval_metrics.md`: document canonical failure taxonomy as the primary analysis/replay taxonomy and legacy labels as secondary diagnostics.
- `.contracts/research/scale_policy.md`: document the n=5/n=20 gates, Phase 4 Modal evidence requirement, and post-Phase-4 grammar hash gate sequencing.

Do not update frozen artifacts, sidecars, manifests, or hashes as part of Phase 5.5 except the separately approved grammar hash re-record interlock that occurs between Phase 4 and Phase 5.

## 9. Tests and validation matrix

| Phase | Test file to add/update | Behavior covered | Command to run after implementation | Expected result |
| --- | --- | --- | --- | --- |
| Phase 1 | `shared/tests/test_shape_schedule_consistency.py` | `get_compile_shapes` exists, returns deterministic non-empty shapes for all locked kernels/dtypes, and every shape validates under shared caps | `.venv/bin/python -m pytest shared/tests/test_shape_schedule_consistency.py` | pass |
| Phase 1 | `cluster1/tests/test_kernel_specs.py` | `KernelSpec.shapes_by_dtype` derives from `get_compile_shapes` for every dtype | `.venv/bin/python -m pytest cluster1/tests/test_kernel_specs.py` | pass |
| Phase 1 | `shared/tests/test_correctness_shapes.py` | Existing correctness-shape determinism/disjointness still holds | `.venv/bin/python -m pytest shared/tests/test_correctness_shapes.py` | pass |
| Phase 1 | Existing Cluster 2 smoke-related tests | Phase 1 shape-helper changes do not alter C2 smoke behavior or correctness-shape anchors | `.venv/bin/python -m pytest cluster2/tests/test_canonical_f2_smoke_integration.py cluster2/tests/test_f2_repair_smoke_integration.py shared/tests/test_eval_level2_correctness.py` | pass |
| Phase 2 | `cluster1/tests/test_signature_gate_consistency.py` | C1 compile validation calls shared Level 0 first and maps bad signature to legacy `SignatureError` plus canonical `F0_BAD_SIGNATURE` through taxonomy | `.venv/bin/python -m pytest cluster1/tests/test_signature_gate_consistency.py` | pass |
| Phase 2 | `shared/tests/test_eval_level0_parse.py` | Shared AST signature semantics remain stable for real Cluster 1 specs | `.venv/bin/python -m pytest shared/tests/test_eval_level0_parse.py` | pass |
| Phase 2 | `shared/tests/test_eval_level1_compile.py` | Shared Level 1 compile wrapper still delegates correctly and handles Level 0/Level 1 failures consistently | `.venv/bin/python -m pytest shared/tests/test_eval_level1_compile.py` | pass |
| Phase 3 | `cluster1/tests/test_analyzer_uses_shared_taxonomy.py` | Analyzer uses `eval_result_from_generation_result` and `classify_failure` for primary distribution | `.venv/bin/python -m pytest cluster1/tests/test_analyzer_uses_shared_taxonomy.py` | pass |
| Phase 3 | `cluster1/tests/test_analysis.py` | Existing C1 analysis metrics remain stable while failure table labels are updated | `.venv/bin/python -m pytest cluster1/tests/test_analysis.py` | pass |
| Phase 3 | `shared/tests/test_eval_failure_taxonomy.py` | Legacy C1 labels map to canonical failure codes | `.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py` | pass |
| Phase 3.4 | `cluster1/tests/test_analyzer_metadata_taxonomy.py` | Analyzer consumes instrumentation metadata and reports `F0_GBNF_PARSE`, `F0_SEMANTIC_INVALID`, and `F0_GRAMMAR_INVALID` through shared taxonomy | `.venv/bin/python -m pytest cluster1/tests/test_analyzer_metadata_taxonomy.py shared/tests/test_eval_failure_taxonomy.py` | pass |
| Phase 3.5 | `cluster2/tests/test_replay_controls.py` or `cluster2/tests/test_run_cluster2_modal.py` | Frozen-style C1 replay rows with legacy `compile_error_type="SignatureError"` are consumed as canonical `failure_code="F0_BAD_SIGNATURE"` without artifact rewrite | `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py` | pass |
| Phase 4 | New baseline revalidation test, likely `cluster1/tests/test_baseline_revalidation_aligned_pipeline.py` | Diagnostic workflow is non-mutating and writes agreement/drift/canonical-code rows | `.venv/bin/python -m pytest cluster1/tests/test_baseline_revalidation_aligned_pipeline.py` | pass |
| Phase 4 | Modal L4 baseline re-validation diagnostic | Evidence-bearing re-validation of all 180 frozen baseline rows in CUDA/Modal environment, interpreted with the drift decision tree | Future Modal command defined by the implementation pass; budget about one L4 hour | diagnostic artifact written; drift disposition recorded |
| Phase 4 | Baseline C1/C2 entrypoint identity check | The same 180 baseline sources run through C1-entrypoint and C2-entrypoint aligned paths produce identical canonical results per row | Built into the Phase 4 Modal re-validation command | 180/180 entrypoint agreement |
| Interlock | Existing or new grammar hash gate test | Recorded Phase -1 hash for `cluster1/grammar/triton_kernel_agnostic.gbnf` matches the current file after the explicit post-Phase-4 re-record | Use the existing hash gate command from the previous Modal generation audit, after it is identified in the implementation pass | pass |
| Phase 5 | Cross-cluster constants/alignment test, likely `shared/tests/test_cross_cluster_eval_alignment.py` | C1 specs, shared shapes, Level 0/1 gates, taxonomy contracts, and replay canonicalization are aligned | `.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_alignment.py` | pass |
| Phase 5 | Cross-cluster byte-identity test, likely `shared/tests/test_cross_cluster_eval_byte_identity.py` | For a fixed source such as an F2 smoke fixture, C1 full evaluation and C2 evaluation produce field-for-field identical `EvalResult` payloads after canonicalization | `.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_byte_identity.py` | pass |
| Phase 5 | Modal/local equivalence test, likely `shared/tests/test_modal_local_eval_equivalence.py` | Aligned Modal evaluation pipeline used by C1/C2 Modal generation matches the aligned local pipeline for the same source and seed inputs | `.venv/bin/python -m pytest shared/tests/test_modal_local_eval_equivalence.py` plus one explicit Modal smoke/equivalence command after implementation | pass / no drift |
| Phase 5.5 | Contract documentation review | Contracts reflect actual code behavior, including max_new_tokens=1536, canonical taxonomy, replay canonicalization, derived shapes, and Phase 4 Modal evidence | Documentation review after Phase 5; no test command required | contracts updated |
| Full local suite subset | Existing shared/cluster tests touched by the alignment | Regression check without Modal/GPU/generation | `.venv/bin/python -m pytest shared/tests/test_shape_schedule_consistency.py shared/tests/test_correctness_shapes.py shared/tests/test_eval_level0_parse.py shared/tests/test_eval_level1_compile.py shared/tests/test_eval_failure_taxonomy.py cluster1/tests/test_kernel_specs.py cluster1/tests/test_signature_gate_consistency.py cluster1/tests/test_analyzer_uses_shared_taxonomy.py cluster1/tests/test_analyzer_metadata_taxonomy.py cluster1/tests/test_analysis.py cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py shared/tests/test_cross_cluster_eval_byte_identity.py shared/tests/test_modal_local_eval_equivalence.py` | pass |

Do not run Modal, GPU compile/eval, generation, n=5, n=20, or baseline re-validation during this planning pass.

## 10. Artifact and data policy

- No frozen artifacts are modified.
- Baseline re-validation writes a diagnostic artifact only:
  - `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl`.
- Generated outputs are not regenerated by the implementation phases.
- Existing baseline rows remain byte-for-byte source evidence.
- Existing frozen C1 rows may retain legacy `compile_error_type` on disk, but current analyzer and Cluster 2 replay consumers must canonicalize them at read time.
- Phase 4 includes one evidence-bearing Modal L4 baseline re-validation run; local-only/mocked re-validation is insufficient to close the baseline comparability question.
- If Modal L4 is unavailable for Phase 4, Modal A10 is the only acceptable fallback and must be documented in the diagnostic artifact; T4 or below is insufficient evidence.
- Phase 4 must compare C1-entrypoint and C2-entrypoint aligned results for all 180 baseline rows and require equality after canonicalization.
- Hashes are not re-recorded during implementation unless a later explicit artifact-freezing task approves it.
- The Cluster 1 grammar hash gate is a separate post-Phase-4/pre-Phase-5 interlock. It is not resolved by evaluation alignment itself.
- Contract documentation updates occur in Phase 5.5 after technical re-audit passes and before the n=5 GO decision.
- n=5 waits until alignment is implemented and verified.
- n=5 also waits until the grammar hash gate is reconciled.
- n=20 remains blocked until n=5 and alignment gates pass.

## 11. Risk register

- C1 compile shapes become too small and stop catching structural compile issues.
  - Mitigation: include smaller-than-block, non-divisible, power-of-two, non-power-of-two, rank/arity edge, and cap-edge anchors per kernel class.
- C2 correctness caps become too expensive if raised.
  - Mitigation: do not raise caps in Phase 1; derive C1 compile shapes inside current caps unless a separate costed decision approves otherwise.
- Shared Level 0 signature gate may not expose exactly the API C1 needs.
  - Mitigation: use a kernel-spec-like adapter around `CompileSpec` or extend Level 0 with a narrow public helper.
- Legacy `compile_error_type` and canonical `failure_code` may disagree.
  - Mitigation: preserve legacy as secondary diagnostics and document canonical mapping via `LEGACY_FAILURE_CODE_MAP`.
- Analyzer changes may alter historical summaries.
  - Mitigation: do not mutate historical rows; update summaries to show canonical primary plus legacy secondary tables.
- Cluster 2 replay and Cluster 1 analyzer may diverge on canonical vs legacy failure labels.
  - Mitigation: make both consumers use `eval_result_from_generation_result` plus `classify_failure` for older frozen rows, and row-level `failure_code` for new rows.
- Instrumentation metadata and canonical failure taxonomy may remain parallel systems.
  - Mitigation: add shared F0 grammar codes and make the analyzer classify `grammar_valid=False` through shared taxonomy.
- Baseline re-validation may show drift.
  - Mitigation: apply the Phase 4 drift decision tree: 0 rows proceeds, 1-5 rows require row-level investigation and written disposition, 6+ rows is an alignment regression.
- Modal baseline re-validation has cost and reproducibility implications.
  - Mitigation: schedule exactly one Phase 4 Modal L4 baseline re-validation run after local tests pass, budget about one L4 hour, and record Modal provenance.
- Modal and local aligned pipelines may disagree.
  - Mitigation: add Modal/local equivalence testing and require no unexplained drift before Phase 5.
- Modal L4 may be unavailable when Phase 4 is ready.
  - Mitigation: use A10 only as a documented fallback; wait rather than use T4-or-lower or local-only evidence.
- The Cluster 1 grammar hash gate remains unresolved after evaluation alignment.
  - Mitigation: sequence a separate hash re-record after Phase 4 baseline re-validation passes and before Phase 5 re-audit.
- Contract documentation may drift from implemented code behavior.
  - Mitigation: add Phase 5.5 contract consolidation before the n=5 GO decision, including max_new_tokens=1536 documentation.
- Shared shape helper changes can affect Cluster 2 smoke tests.
  - Mitigation: keep C2 `generate_correctness_shape_sets` behavior stable unless tests explicitly approve a change.
- Import boundaries may regress by pulling torch/triton into shared modules at import time.
  - Mitigation: preserve lazy imports and extend existing import-boundary tests where relevant.

## 12. Decision criteria

### Phase classifications

- `PHASE_1_READY`: shared compile-shape helper is implemented, C1 specs derive from it, shape consistency tests pass.
- `PHASE_2_READY`: C1 compile validation uses shared Level 0 first, legacy labels are preserved, canonical signature classification is verified.
- `PHASE_3_READY`: new C1 rows carry canonical `failure_code`, and C1 analyzer primary failure summaries use shared taxonomy while legacy diagnostics remain.
- `PHASE_3_4_READY`: instrumentation metadata is surfaced by the analyzer and grammar-validity failures classify through shared F0 grammar codes.
- `PHASE_3_5_READY`: Cluster 2 replay canonicalizes frozen Cluster 1 rows through the same adapter/taxonomy path as the analyzer and preserves legacy labels only as secondary diagnostics.
- `PHASE_4_READY`: baseline diagnostic re-validation workflow is implemented, tested in non-mutating mode, one Modal L4 baseline re-validation run has completed with drift disposition recorded, and all 180 baseline rows have identical C1-entrypoint/C2-entrypoint canonical results.
- `PHASE_5_5_READY`: required contract documentation updates are complete and no code/artifact changes are bundled into the documentation phase.
- `PLAN_CONFIRMED`: all alignment phases are implemented or explicitly staged, blockers are resolved, tests pass, and no forbidden work occurred.
- `PLAN_BLOCKED`: actual code paths cannot be identified, shape source of truth cannot be located, signature gate APIs cannot be located, failure taxonomy cannot be located, baseline artifact is missing, baseline drift is unexplained, Phase 4 lacks acceptable Modal/A10 fallback re-validation evidence, C1/C2 baseline entrypoints disagree, contract documentation is stale, or the Cluster 1 grammar hash gate remains unresolved after Phase 4.

### Implementation classifications

- `FIX_VERIFIED`: implementation tests pass and the final re-audit finds the three pre-n5 blockers resolved.
- `STILL_BLOCKED`: one or more blockers remain unresolved or untested.
- `N5_READY`: phases 1-3.5 pass, Phase 4 Modal L4 or acceptable A10 fallback baseline re-validation evidence is acceptable under the drift decision tree, the 180-row baseline C1/C2 entrypoint comparison is identical, the Cluster 1 grammar hash gate is reconciled, Phase 5 re-audit is clean, Phase 5.5 contracts are updated, and no unexplained or unacceptable baseline compile-success drift blocks decision-making.
- `N5_BLOCKED`: any unresolved compile-success drift, 6+ drift rows, C1/C2 baseline entrypoint disagreement, unresolved shape/signature/taxonomy/replay/metadata mismatch, unresolved grammar hash gate, missing acceptable Modal/A10 baseline evidence, stale contracts, missing diagnostic path, or forbidden artifact/generation mutation occurs.

## 13. Exact future commands

Run only after implementation, not during this planning pass:

```bash
.venv/bin/python -m pytest shared/tests/test_shape_schedule_consistency.py
.venv/bin/python -m pytest cluster1/tests/test_kernel_specs.py
.venv/bin/python -m pytest shared/tests/test_correctness_shapes.py
.venv/bin/python -m pytest cluster2/tests/test_canonical_f2_smoke_integration.py cluster2/tests/test_f2_repair_smoke_integration.py shared/tests/test_eval_level2_correctness.py
.venv/bin/python -m pytest cluster1/tests/test_signature_gate_consistency.py
.venv/bin/python -m pytest shared/tests/test_eval_level0_parse.py
.venv/bin/python -m pytest shared/tests/test_eval_level1_compile.py
.venv/bin/python -m pytest cluster1/tests/test_analyzer_uses_shared_taxonomy.py
.venv/bin/python -m pytest cluster1/tests/test_analyzer_metadata_taxonomy.py
.venv/bin/python -m pytest cluster1/tests/test_analysis.py
.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py
.venv/bin/python -m pytest cluster1/tests/test_baseline_revalidation_aligned_pipeline.py
.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_alignment.py
.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_byte_identity.py
.venv/bin/python -m pytest shared/tests/test_modal_local_eval_equivalence.py
```

Combined local subset:

```bash
.venv/bin/python -m pytest \
  shared/tests/test_shape_schedule_consistency.py \
  shared/tests/test_correctness_shapes.py \
  shared/tests/test_eval_level2_correctness.py \
  shared/tests/test_eval_level0_parse.py \
  shared/tests/test_eval_level1_compile.py \
  shared/tests/test_eval_failure_taxonomy.py \
  cluster1/tests/test_kernel_specs.py \
  cluster1/tests/test_signature_gate_consistency.py \
  cluster1/tests/test_analyzer_uses_shared_taxonomy.py \
  cluster1/tests/test_analyzer_metadata_taxonomy.py \
  cluster1/tests/test_analysis.py \
  cluster2/tests/test_replay_controls.py \
  cluster2/tests/test_run_cluster2_modal.py \
  cluster2/tests/test_canonical_f2_smoke_integration.py \
  cluster2/tests/test_f2_repair_smoke_integration.py \
  cluster1/tests/test_baseline_revalidation_aligned_pipeline.py \
  shared/tests/test_cross_cluster_eval_alignment.py \
  shared/tests/test_cross_cluster_eval_byte_identity.py \
  shared/tests/test_modal_local_eval_equivalence.py
```

Future local diagnostic command shape, after implementation:

```bash
.venv/bin/python -m cluster1.diagnostics.revalidate_baseline_aligned_pipeline \
  --input outputs/cluster1/baseline_repaired_l4_n20.jsonl \
  --output outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl
```

Future Modal L4 baseline re-validation command:

```bash
# Required in Phase 4 after local tests pass. The implementation agent must
# identify or add the exact Modal entrypoint, but the command must run one L4
# baseline re-validation over outputs/cluster1/baseline_repaired_l4_n20.jsonl
# and write outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline.jsonl.
# It must also run both C1-entrypoint and C2-entrypoint aligned evaluation paths
# for all 180 sources and assert row-level canonical equality.
# Budget about one L4 hour. If L4 is unavailable, A10 is acceptable with an
# explicit diagnostic note; T4 or below is insufficient.
```

Future Modal/local equivalence command:

```bash
# Required before Phase 5. The implementation agent must identify or add the
# exact Modal smoke/equivalence entrypoint and compare the same source/seed
# against the aligned local pipeline output.
```

Future grammar hash gate command:

```bash
# Run the existing Phase -1 grammar hash gate/re-record command from the
# previous Modal generation audit only after Phase 4 baseline re-validation
# passes. The implementation agent must identify the exact existing command
# before executing it.
```

## 14. Closed decisions

- Compile shapes should initially be a strict subset of the shared C2 repair/eval anchor vocabulary. Add separately tagged compile-only anchors only if Phase 1 testing proves a concrete structural compile issue is no longer caught.
- C1 should reduce its largest compile shapes to fit the current shared caps. Do not raise C2 caps in this alignment pass.
- Baseline re-validation must include one Modal L4 run matching the original baseline execution class. If L4 is unavailable, A10 is acceptable with a recorded diagnostic note; T4 or below is insufficient. Local-only re-validation is useful for tests but insufficient for final evidence.
- Phase 4 baseline re-validation must include side-by-side C1-entrypoint and C2-entrypoint aligned evaluation for all 180 baseline sources, with row-level canonical equality required.
- Agreement threshold before n=5 follows the Phase 4 drift decision tree: 0 compile-success drift rows proceeds; 1-5 rows require row-level investigation and written disposition; 6+ rows blocks and sends Phases 1-3.5 back for review.
- Label drift policy: expected legacy-to-canonical drift is acceptable; cross-category drift such as `SignatureError -> F0_PARSE` or `SignatureError -> F1_RUNTIME` requires row-level investigation.
- Historical analysis outputs generated before this change do not need retroactive edits. New analysis output uses canonical primary taxonomy; old summaries remain historical artifacts.
- Confirmed decision: add canonical `failure_code` to all new C1 rows, while preserving legacy `compile_error_type`.
- Confirmed decision: split syntax into `F0_PARSE` only when AST parse fails outright; keep signature mismatches as `F0_BAD_SIGNATURE`, including signature failures discovered after runtime import.
- Confirmed decision: C1 compile validation owns explicit Level 0 then Level 1 ordering; shared Level 1 remains a thin compile wrapper and does not implicitly invoke Level 0.
- Confirmed sequencing: the Cluster 1 grammar hash gate is not resolved by evaluation alignment; resolve it after Phase 4 baseline re-validation evidence and before Phase 5 final re-audit.
- Confirmed decision: Cluster 2 replay should canonicalize frozen Cluster 1 rows through the same adapter/taxonomy path as the C1 analyzer, while leaving frozen artifacts unchanged.
- Confirmed decision: instrumentation metadata must be surfaced by the analyzer and grammar-invalid rows must classify through shared F0 grammar codes.
- Confirmed decision: Phase 5 requires both cross-cluster byte-identity and Modal/local equivalence tests before n=5 is considered ready.
- Confirmed decision: Phase 5.5 updates contracts after the technical re-audit, including max_new_tokens=1536 documentation, before any n=5 GO.
- Confirmed decision: Phase 1 must justify compile-shape selections in code comments/docstring and run C2 smoke-related regressions.
