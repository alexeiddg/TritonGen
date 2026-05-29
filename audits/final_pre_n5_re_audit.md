# Final Pre-N5 Re-Audit

Date: 2026-05-18

## 1. Executive Summary

Final classification: **GO**.

Fresh instrumented task-agnostic G n=5 can proceed. The current code and artifact evidence independently verify that the prior cross-cluster blockers are resolved: C1 compile shapes derive from the shared shape helper, C1 and shared Level 0 now use parameter-name-only signature semantics, failure classification is routed through shared taxonomy/adapters, C2 replay canonicalizes frozen C1 rows through the shared path, the Phase 4 Modal L4 diagnostic shows 180/180 compile-success agreement and 180/180 C1/C2 entrypoint agreement, and the Phase -1 task-agnostic grammar hash gate passes. No current n=5 methodological compatibility blocker was found.

## 2. Evidence Inventory

- Repository: `/Users/alexeidelgado/Desktop/TritonGen`
- Commit inspected: `f88ec9e03f51b74426ed727d3912268665605bf4`
- Pre-report working tree status: clean (`git status --short` produced no output).
- Phase 4 artifact consumed: `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`
- Phase 4 artifact SHA256: `ef0150058d67bc8bc6e0ce5de57eed173bcc6fc0b31c74657d86dfd1f5957e97`
- Frozen baseline artifact: `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- Frozen baseline SHA256: `1f3e004b25564f347b2fb293216d2a9589ac7aaa60728cabd1d20e40af4f4cc3`
- Current task-agnostic grammar hash: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`
- Prior audit reports consulted for blocker inventory:
  - `audits/pre_paper_factorial_audit.md`
  - `audits/cross_cluster_pipeline_compatibility_audit.md`
  - `audits/cluster1_eval_path_pre_n5_audit.md`
  - `audits/cluster1_eval_path_pre_n5_reaudit.md` was not present.
  - `audits/cross_cluster_pipeline_compatibility_reaudit.md` was not present.

Tests run:

- `.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v` -> 1 passed.
- `.venv/bin/python -m pytest cluster1/tests/test_compile_check.py cluster1/tests/test_signature_gate_consistency.py shared/tests/test_eval_level0_parse.py shared/tests/test_eval_level1_compile.py -q` -> 63 passed, 7 skipped.
- `.venv/bin/python -m pytest shared/tests/test_shape_schedule_consistency.py cluster1/tests/test_kernel_specs.py shared/tests/test_correctness_shapes.py -q` -> 99 passed.
- `.venv/bin/python -m pytest cluster1/tests/test_analyzer_uses_shared_taxonomy.py cluster1/tests/test_analyzer_metadata_taxonomy.py shared/tests/test_eval_failure_taxonomy.py -q` -> 30 passed.
- `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py -q` -> 57 passed.
- `.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_alignment.py shared/tests/test_cross_cluster_eval_byte_identity.py -q` -> 11 passed.
- `.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_run_cluster1.py cluster1/tests/test_run_cluster1_modal.py shared/tests/test_modal_harness_schemas.py -q` -> 173 passed.
- `.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py -q` -> 33 passed.

## 3. Block A - Prior Blocker Resolution

| item | prior blocker | current evidence | status | notes |
| --- | --- | --- | --- | --- |
| A1. Shape schedules unified | C1 had independent compile schedules from C2/shared correctness schedule metadata. | `shared/eval/correctness_shapes.py:114-137` defines `_COMPILE_SHAPE_ANCHORS`; `shared/eval/correctness_shapes.py:238-246` exposes `get_compile_shapes`; `cluster1/data/kernels/elementwise_relu.py:16,69-72`, `cluster1/data/kernels/reduction_softmax.py:16,69-72`, and `cluster1/data/kernels/matmul_tiled_gemm.py:16,72-75` derive `shapes_by_dtype` from `get_compile_shapes`. Diagnostic output: ReLU fp32 `[(32,), (100,), (1024,), (3, 257), (5, 129)]`; Softmax fp32 `[(16, 64), (33, 100), (128, 1001), (16384, 1), (1, 16384)]`; GEMM fp32 `[(24, 24, 24), (48, 48, 48), (128, 128, 64), (100, 100, 100), (16384, 1, 1)]`; all match shared helper and fit `MAX_DIM=16384`, `MAX_ELEMENTS=16777216`. Shape tests passed: 99 passed. | RESOLVED | No independent hard-coded C1 compile shape list remains in the three concrete specs. |
| A2. Signature gate matched | C1 runtime validation compared full `inspect.Signature`, including annotations, while shared Level 0 compared names. | `cluster1/validation/compile_check.py:160-178` now compares `tuple(actual_sig.parameters)` against `tuple(spec.reference_signature.parameters)`. Shared Level 0 uses `_compare_function_params` and generated parameter names only in `shared/eval/levels/level0_parse.py:91-103`. Synthetic 9-case diagnostic showed agreement for ReLU, Softmax, and GEMM across annotated, annotation-drift, and wrong-name cases. Focused signature tests passed: 63 passed, 7 skipped. | RESOLVED | Annotation-only drift no longer rejects; wrong names still reject. |
| A3. Failure taxonomy unified | Analyzer and C1/C2 paths could report legacy labels as primary. | `cluster1/experiments/analyze_cluster1.py:27-28` imports `eval_result_from_generation_result` and `classify_failure`; `_failure_code_distribution_markdown` uses both at `cluster1/experiments/analyze_cluster1.py:725-743`; legacy compile error distribution remains separate at `cluster1/experiments/analyze_cluster1.py:681-722`. `shared/eval/failure_taxonomy.py:8-24` defines canonical codes, `classify_failure` at `shared/eval/failure_taxonomy.py:58-111`, and message-aware legacy mapping at `shared/eval/failure_taxonomy.py:41-55`. Analyzer/taxonomy tests passed: 30 passed. | RESOLVED | Canonical `failure_code` is primary for current analysis; `compile_error_type` remains secondary diagnostics. |
| A4. Metadata schema / legacy artifact canonicalization | Frozen rows lacked canonical `failure_code`; C2 replay could consume legacy labels. | `cluster1/results/dataclass.py:76` adds `failure_code`; new failed rows require it when `compile_error_type` is present at `cluster1/results/dataclass.py:121-125`; legacy deserialization fills missing `failure_code` through shared mapping at `cluster1/results/dataclass.py:441-472`. Adapter carries C1 fields into `EvalResult` at `shared/eval/adapter_cluster1.py:10-65`. C2 replay imports the same adapter/taxonomy at `cluster2/replay/cluster1_controls.py:37-38`; candidate rows carry canonical `failure_code` and `legacy_compile_error_type` at `cluster2/replay/cluster1_controls.py:48-79`; replay tests include legacy canonicalization cases and passed. Frozen baseline artifact has 180 rows, all `compile_success=false`, all legacy `compile_error_type=SignatureError`, and 0 stored non-null `failure_code`; artifact was not modified. | RESOLVED | Backward compatibility is preserved by read-time canonicalization, not artifact mutation. |
| A5. Phase 4 Modal baseline evidence | Prior audits lacked current GPU-backed aligned-pipeline baseline revalidation. | Artifact `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl` exists with 180 rows. Counts: `agreement=True` 180, `entrypoint_agreement=True` 180, `compile_success_drift=False` 180, `cross_category_label_drift=False` 180, `original_canonical_failure_code=F0_PARSE` 180, `new_canonical_failure_code=F0_PARSE` 180, `c1_entrypoint_failure_code=F0_PARSE` 180, `c2_entrypoint_failure_code=F0_PARSE` 180, `drift_reason=expected_legacy_to_canonical_mapping` 180. Diagnostic rows include `diagnostic_only=True`. | RESOLVED | This closes baseline revalidation and C1/C2 entrypoint equality for the frozen none baseline. |
| A6. Generation parameter drift resolved for current n=5 path | Older default/token-budget drift risk around 512-token generation. | `cluster1/constants.py:6-7` sets `DEFAULT_MAX_NEW_TOKENS = 1536`; C1 local generation uses that default at `cluster1/generation/constrained_gen.py:27-35`; C1 Modal local entrypoint defaults `max_new_tokens` to it at `cluster1/experiments/run_cluster1_modal.py:1333-1347` and passes it to generation at `cluster1/experiments/run_cluster1_modal.py:1215-1227`. `cluster2/constants.py:36-37` sets `DEFAULT_MAX_NEW_TOKENS = 1536`; C2 CLI default uses it at `cluster2/experiments/run_cluster2_modal.py:70-72,261`; C2 request builders default to it at `cluster2/generation/modal_generate_c2.py:20-31,50-63`; C2 schema default is 1536 at `cluster2/modal/schemas.py:162-176`. | RESOLVED | Remaining `512` occurrences are smoke/frozen-artifact historical values or kernel block sizes, not the current fresh n=5 task-agnostic G generation path. |
| A7. Phase -1 grammar hash gate | Recorded task-agnostic grammar hash did not match current grammar. | Canonical hash command returned `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`. `cluster2/modal/generation.py:104-127` records the same hash for `cluster1/grammar/triton_kernel_agnostic.gbnf` at lines 112-114. Hash gate test passed: 1 passed. Full `cluster2/tests/test_modal_generation_c2.py` also passed: 33 passed. | RESOLVED | No grammar file or manifest was modified by this audit. |

## 4. Block B - Signature Gate Fix Verification

Classification: **FIX_VERIFIED**.

Implementation inspection:

- C1 runtime signature validation: `cluster1/validation/compile_check.py:160-178`.
  - `actual_sig = inspect.signature(launcher)` is still used to inspect the imported launcher.
  - The comparison is now `actual_params = tuple(actual_sig.parameters)` and `expected_params = tuple(spec.reference_signature.parameters)`.
  - No comparison of parameter annotations or return annotation remains in `validate_signature`.
- Shared Level 0 parse/signature gate: `shared/eval/levels/level0_parse.py:21-55,80-103,121-149`.
  - Expected params are coerced from `inspect.Signature` to names at lines 148-149.
  - Generated params come from AST argument names at lines 80-88.
  - `_compare_function_params` compares generated and expected names at lines 91-103.

Synthetic 9-case diagnostic:

| kernel | variant | expected params | generated params | shared Level 0 | C1 runtime | agreement |
| --- | --- | --- | --- | --- | --- | --- |
| elementwise/ReLU | annotated | `('x',)` | `('x',)` | True | True | True |
| elementwise/ReLU | annotation drift | `('x',)` | `('x',)` | True | True | True |
| elementwise/ReLU | wrong names | `('x',)` | `('wrong_a',)` | False | False | True |
| reduction/Softmax | annotated | `('x',)` | `('x',)` | True | True | True |
| reduction/Softmax | annotation drift | `('x',)` | `('x',)` | True | True | True |
| reduction/Softmax | wrong names | `('x',)` | `('wrong_a',)` | False | False | True |
| matmul/GEMM | annotated | `('a', 'b')` | `('a', 'b')` | True | True | True |
| matmul/GEMM | annotation drift | `('a', 'b')` | `('a', 'b')` | True | True | True |
| matmul/GEMM | wrong names | `('a', 'b')` | `('wrong_a', 'wrong_b')` | False | False | True |

Focused tests:

- `.venv/bin/python -m pytest cluster1/tests/test_compile_check.py cluster1/tests/test_signature_gate_consistency.py shared/tests/test_eval_level0_parse.py shared/tests/test_eval_level1_compile.py -q` -> 63 passed, 7 skipped.
- The dedicated consistency test matrix is in `cluster1/tests/test_signature_gate_consistency.py:80-117`; it exercises elementwise, reduction, and matmul with matching annotations, missing annotations, different annotations, and wrong names.

## 5. Block C - New Finding Sweep

| item | evidence | status | impact on n=5 |
| --- | --- | --- | --- |
| C1. `failure_code` population | `GenerationResult.failure_code` exists at `cluster1/results/dataclass.py:76`; failed new rows require it at `cluster1/results/dataclass.py:121-125`; local C1 generation populates it at `cluster1/experiments/run_cluster1.py:188-233`; Modal C1 conversion populates/preserves it at `cluster1/experiments/run_cluster1_modal.py:838-887`; legacy rows canonicalize at `cluster1/results/dataclass.py:441-472`; `cluster1/tests/test_results.py cluster1/tests/test_run_cluster1.py cluster1/tests/test_run_cluster1_modal.py shared/tests/test_modal_harness_schemas.py` passed with 173 tests. | VERIFIED | None. |
| C2. `get_compile_shapes` is the only C1 compile shape source | Concrete specs import and call `get_compile_shapes`: `cluster1/data/kernels/elementwise_relu.py:16,69-72`, `cluster1/data/kernels/reduction_softmax.py:16,69-72`, `cluster1/data/kernels/matmul_tiled_gemm.py:16,72-75`. `rg` found no other hard-coded `shapes_by_dtype` definitions in those specs. Shape and cross-cluster alignment tests passed. | VERIFIED | None. |
| C3. Grammar-invalid taxonomy codes are reachable | `shared/eval/failure_taxonomy.py:8-24` includes `F0_GBNF_PARSE`, `F0_SEMANTIC_INVALID`, `F0_GRAMMAR_INVALID`; `_classify_grammar_failure` maps metadata to those codes at `shared/eval/failure_taxonomy.py:114-121`. Analyzer grammar rejection reporting uses adapter/taxonomy at `cluster1/experiments/analyze_cluster1.py:804-851`. Tests cover these paths: `cluster1/tests/test_analyzer_metadata_taxonomy.py` and `shared/tests/test_eval_failure_taxonomy.py` passed in the 30-test analyzer/taxonomy run. | VERIFIED | None. Compile metrics remain separate from grammar rejection metadata in analyzer tests. |
| C4. Grammar hash gate test passes | Hash gate command passed: `cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1` -> 1 passed. Full `cluster2/tests/test_modal_generation_c2.py` -> 33 passed. | VERIFIED | None. |
| C5. Phase 4 artifact is authoritative and sufficient | This audit explicitly consumed `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`, counted all 180 rows, verified compile-success agreement and C1/C2 entrypoint agreement, and did not carry forward older baseline concerns without re-checking artifact contents. | VERIFIED | None. |

## 6. Phase 4 Modal Evidence Interpretation

The Phase 4 Modal L4 artifact was consumed directly:

- Path: `outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl`
- Row count: 180
- `agreement=True`: 180/180
- `entrypoint_agreement=True`: 180/180
- `compile_success_drift=False`: 180/180
- `cross_category_label_drift=False`: 180/180
- `original_canonical_failure_code=F0_PARSE`: 180/180
- `new_canonical_failure_code=F0_PARSE`: 180/180
- `c1_entrypoint_failure_code=F0_PARSE`: 180/180
- `c2_entrypoint_failure_code=F0_PARSE`: 180/180
- `drift_reason=expected_legacy_to_canonical_mapping`: 180/180

The original frozen baseline was also inspected: `outputs/cluster1/baseline_repaired_l4_n20.jsonl` has 180 rows, all `compile_success=false`, all legacy `compile_error_type=SignatureError`, and no stored non-null `failure_code`. The diagnostic confirms this legacy label is read-time canonicalized to `F0_PARSE` and agrees with both aligned entrypoints. This closes the baseline revalidation question for the frozen none baseline without modifying the original artifact.

## 7. Hash Gate Verification

- Local grammar path: `cluster1/grammar/triton_kernel_agnostic.gbnf`
- Local grammar SHA256 from `shared.eval.content_hashes.file_sha256`: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`
- Recorded Phase -1 hash: `cluster2/modal/generation.py:112-114` records `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`
- Hash gate test: `.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v` -> 1 passed

## 8. Remaining Risks

N=5 blockers:

- None found.

N=20 blockers:

- The current audit only approves fresh instrumented task-agnostic G n=5. Paper-scale n=20 remains gated on the n=5 output and the project scale policy.
- Cluster 2 paper-scale primary G+C still requires a sufficient frozen task-agnostic G replay artifact; `cluster2/experiments/run_cluster2_modal.py:844-865` explicitly blocks paper-scale primary G+C if the manifest says the available development task-agnostic artifact is insufficient.

Paper-scale blockers:

- Full paper-scale claims still require the later n=20 artifact set and any paper-scale Cluster 2 smoke/factorial gates. This audit did not run Modal, GPU evaluation, generation, or n=20.

Documentation-only follow-ups:

- Keep contracts/runbooks aligned with the verified current behavior: 1536-token current generation defaults, signature parameter-name-only semantics, canonical failure taxonomy as primary, and the Phase 4 parse reclassification disposition.

## 9. Final Recommendation

**GO**.

Next exact step: run fresh instrumented task-agnostic G n=5 using the current C1 Modal generation path with the task-agnostic grammar and the current default `max_new_tokens=1536`. No additional compatibility fix is required before n=5.

Do not interpret this GO as approval for n=20 or paper-scale primary G+C. After n=5 completes, validate the new artifact before promoting it into any replay or paper-scale path.

## 10. Appendix - Commands Run

```bash
git status --short
```

Result: no output before report creation.

```bash
rg "get_compile_shapes|shapes_by_dtype|MAX_DIM|MAX_ELEMENTS" shared cluster1 cluster2
rg "def validate_signature|inspect.signature|reference_signature|check_signature|annotation|return_annotation" cluster1 shared
rg "classify_failure|eval_result_from_generation_result|failure_code|compile_error_type|F0_GBNF_PARSE|F0_SEMANTIC_INVALID|F0_GRAMMAR_INVALID" cluster1 shared cluster2
rg "PHASE_MINUS1_G_GENERATION_SOURCE_HASHES|triton_kernel_agnostic|7896a1be|max_new_tokens|1536|512" cluster1 cluster2 shared
```

Result: inspected current code paths cited above.

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from shared.eval.content_hashes import file_sha256
p = Path("cluster1/grammar/triton_kernel_agnostic.gbnf")
print(file_sha256(p))
PY
```

Result: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from collections import Counter
p = Path("outputs/cluster1/diagnostics/baseline_revalidation_aligned_pipeline_parse_reclassification.jsonl")
rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
print("rows", len(rows))
print("agreement", dict(Counter(r.get("agreement") for r in rows)))
print("entrypoint_agreement", dict(Counter(r.get("entrypoint_agreement") for r in rows)))
print("compile_success_drift", dict(Counter(r.get("compile_success_drift") for r in rows)))
print("cross_category_label_drift", dict(Counter(r.get("cross_category_label_drift") for r in rows)))
print("original_canonical_failure_code", dict(Counter(r.get("original_canonical_failure_code") for r in rows)))
print("new_canonical_failure_code", dict(Counter(r.get("new_canonical_failure_code") for r in rows)))
PY
```

Result: 180 rows, all agreements true, all compile-success drift false, all cross-category label drift false, original/new canonical failure codes all `F0_PARSE`.

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v
```

Result: 1 passed.

```bash
.venv/bin/python -m pytest cluster1/tests/test_compile_check.py cluster1/tests/test_signature_gate_consistency.py shared/tests/test_eval_level0_parse.py shared/tests/test_eval_level1_compile.py -q
```

Result: 63 passed, 7 skipped.

```bash
.venv/bin/python -m pytest shared/tests/test_shape_schedule_consistency.py cluster1/tests/test_kernel_specs.py shared/tests/test_correctness_shapes.py -q
```

Result: 99 passed.

```bash
.venv/bin/python -m pytest cluster1/tests/test_analyzer_uses_shared_taxonomy.py cluster1/tests/test_analyzer_metadata_taxonomy.py shared/tests/test_eval_failure_taxonomy.py -q
```

Result: 30 passed.

```bash
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py -q
```

Result: 57 passed.

```bash
.venv/bin/python -m pytest shared/tests/test_cross_cluster_eval_alignment.py shared/tests/test_cross_cluster_eval_byte_identity.py -q
```

Result: 11 passed.

```bash
.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_run_cluster1.py cluster1/tests/test_run_cluster1_modal.py shared/tests/test_modal_harness_schemas.py -q
```

Result: 173 passed.

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py -q
```

Result: 33 passed.
