# Cluster 2 Pre-Smoke Audit

## 1. Executive summary

Final classification: **C2_SMOKE_BLOCKED**.

Readiness:

- F2 fixture smoke: **ready to run locally**. Existing local/mock F2 repair-loop fixture tests passed under `.venv/bin/python`; no Modal, GPU, or generation was invoked.
- C n=1 smoke: **not ready**. The active C2 correctness path does not call shared Level 0 parse/signature or shared Level 1 compile before Level 2 correctness.
- C n=20: **not ready**. C n=20 inherits the C n=1 blocker and also has partial-output risk because results are written only after the full run completes.
- G+C replay: **not ready for the new task-agnostic n=20 artifact**. The requested `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` exists with 177 rows, but it is not registered as the task-agnostic G n=20 replay artifact in the frozen manifest.

Main blockers:

- `cluster2/modal/correctness_runner.py::run_correctness_payload` invokes `shared.eval.pipeline.run_eval_pipeline` with only a `PipelineLevel2Request`; the shared pipeline has deferred Level 0 and Level 1 stages, so generated C rows are not actively gated through `shared/eval/levels/level0_parse.py` or `shared/eval/levels/level1_compile.py`.
- `cluster2/results/logger.py::write_cluster2_results_jsonl` serializes and writes the complete row set via `Path.write_text`; `cluster2/experiments/run_cluster2_modal.py::run_cluster2` calls `_write_rows` only after all condition rows complete. A manual kill can lose the whole partial run.
- The new task-agnostic G artifact `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` has 177/180 rows and is not the configured replay artifact for G+C.

Main warnings:

- C2 requires caller-supplied immutable `model_revision` and `tokenizer_revision`; it validates and propagates them, but the C2 runner does not default the revision to `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- Metadata is captured in generated-row schemas, and paper-scale validation rejects missing/unknown required metadata, but development/smoke runs can still carry `"unknown"` fallbacks for some runtime provenance fields.
- No explicit Modal dollar/budget cap was found. The repair iteration cap is present, but cost monitoring is operational/manual.

## 2. Scope

This is a focused Cluster 2 pre-smoke audit for the C condition and the G+C replay path before cheap smoke tests. It is not the full 18-question cross-cluster compatibility audit, not a full pre-paper factorial audit, and not a paper-scale readiness audit.

No Modal run, GPU job, generation, repair-loop generation, C n=1, C n=20, or G+C run was executed. The audit used static inspection, local CPU-safe tests, and read-only artifact inspection. The only file written is this audit report.

## 3. Evidence inventory

Files inspected:

- `cluster2/modal/generation.py`
- `cluster2/modal/schemas.py`
- `cluster2/generation/modal_generate_c2.py`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/experiments/run_f2_repair_smoke.py`
- `cluster2/feedback/repair_loop.py`
- `cluster2/feedback/prompts.py`
- `cluster2/feedback/trace.py`
- `cluster2/results/dataclass.py`
- `cluster2/results/logger.py`
- `cluster2/replay/manifest.py`
- `cluster2/replay/cluster1_controls.py`
- `cluster2/constants.py`
- `shared/eval/levels/level0_parse.py`
- `shared/eval/levels/level1_compile.py`
- `shared/eval/levels/level2_correctness.py`
- `shared/eval/correctness_shapes.py`
- `shared/eval/failure_taxonomy.py`
- `shared/eval/adapter_cluster1.py`
- `shared/eval/pipeline.py`
- `cluster1/experiments/run_cluster1_modal.py`
- `cluster1/data/prompts/prompt_contract.py`
- `cluster1/data/kernels/`
- `cluster1/results/dataclass.py`

Tests run:

- `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py -q`
- `.venv/bin/python -m pytest cluster2/tests -k "repair or feedback or F2 or corrupted or fixture" -q`
- `.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py shared/tests/test_eval_level2_correctness.py -q`

Artifacts inspected:

- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

Required searches run:

- `rg "condition|grammar_active|grammar_variant|C\+G|G\+C|condition.*C|repair|feedback|max_repair|max_iterations|max_iter" cluster2 shared cluster1`
- `rg "AutoModel|AutoTokenizer|model_revision|tokenizer_revision|8e8ed243bbe6f9a5aff549a0924562fc719b2b8a|Qwen/Qwen2.5-Coder-7B-Instruct-AWQ|revision" cluster2 shared cluster1`
- `rg "prompt|build_prompt|PROMPT_TEMPLATE|base prompt|baseline|none|grammar_active=False|grammar_active = False" cluster2 cluster1 shared`
- `rg "F2_|F0_|F1_|compile|signature|numeric|max abs|max rel|NaN|Inf|shape mismatch|private eval|repair_iteration|feedback_prompt" cluster2 shared`
- `rg "generate_correctness_shape_sets|get_compile_shapes|correctness_shapes|shape schedule|repair shapes|eval shapes|private eval|base_seed|generation_seed|sample_index|seed" cluster2 shared cluster1`
- `rg "frozen_cluster1_artifacts_manifest|baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|replay|coverage|missing|177|180" cluster2 shared outputs audits`

## 4. Block 1 - C generation path integrity

### 1.1 Grammar-free C path

Status: **PASS**

Evidence:

- `cluster2/modal/generation.py::generation_routing_for_condition` returns `C2GenerationRouting(grammar_active=False, grammar_variant=None, grammar_path=None, grammar_claim_scope=None)` for condition `C`.
- The same function raises if a `C` request supplies `grammar_variant`.
- `cluster2/modal/schemas.py::RemoteC2GenerationRequest` validates that `C` must not request a grammar variant.
- `cluster2/modal/generation.py::run_c2_generation_with_loaded_model` loads grammar only when `routing.grammar_active` is true. For C, the unconstrained path is `_generate_unconstrained_source`; injected generation functions receive `grammar_active=False`, `compiled_grammar=None`, and `hardware_checker=None`.
- `cluster2/experiments/run_cluster2_modal.py::_run_generated_cell` passes `grammar_variant=None` for `C`.
- `cluster2/results/dataclass.py::Cluster2EvalRow._validate_source_class_metadata` rejects grammar metadata on condition `C`.

Impact:

- The C generation path is grammar-free by routing, schema validation, remote generation behavior, and result-row validation.

### 1.2 Same base prompt as none baseline

Status: **PASS**

Evidence:

- `cluster2/experiments/run_cluster2_modal.py::_build_base_prompt` imports `cluster1.data.kernels.KERNEL_SPECS` and `cluster1.data.prompts.prompt_contract.build_prompt`.
- `cluster1/data/prompts/prompt_contract.py::build_prompt` uses the locked `PROMPT_TEMPLATE` for Cluster 1 generation.
- `cluster2/feedback/repair_loop.py::run_repair_loop` starts with `next_prompt = base_prompt`; feedback is built only after an attempt fails Level 2 with an allowed correctness failure.
- `cluster2/feedback/repair_loop.py::_must_terminate_without_feedback` terminates before feedback for failures below Level 2.

Impact:

- Initial C generation is byte-identical to the Cluster 1 base prompt for the same kernel spec and dtype because it uses the same prompt builder. C-specific feedback can only enter after an allowed Level 2 correctness failure.

### 1.3 Same model/tokenizer revision as current instrumented path

Status: **PARTIAL**

Evidence:

- `cluster2/experiments/run_cluster2_modal.py::MODEL_ID_DEFAULT` is `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`.
- `cluster2/experiments/run_cluster2_modal.py::Cluster2RunnerConfig.__post_init__` requires `model_revision` and `tokenizer_revision` for new-generation conditions and normalizes them with `_normalize_immutable_revision`.
- `cluster2/modal/schemas.py::RemoteC2GenerationRequest` requires non-empty immutable revisions.
- `cluster2/modal/generation.py::RemoteC2Generator.load_model` passes `revision=self.tokenizer_revision` to `AutoTokenizer.from_pretrained` and `revision=self.model_revision` to `AutoModelForCausalLM.from_pretrained`.
- `cluster2/modal/generation.py::build_success_payload` records requested and observed revisions in `model_identity`; the final `RemoteC2GenerationResult` carries `model_revision` and `tokenizer_revision`.
- `cluster1/experiments/run_cluster1_modal.py::DEFAULT_MODEL_REVISION` pins `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; no equivalent C2 default revision constant was found.

Impact:

- Revisions are propagated and cannot be omitted for generated C2 conditions, so `tokenizer_revision` should not become `"unknown"` when a valid request is submitted.
- The C2 runner does not itself pin the requested revision to `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; the caller must supply it. That is a smoke-readiness warning and a paper-scale provenance risk if launch commands are not explicit.

### 1.4 C path emits instrumented metadata

Status: **PARTIAL**

Evidence:

- `cluster2/results/dataclass.py::Cluster2GeneratedRowMetadata` includes `grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, `stop_reason`, `xgrammar_version`, `transformers_version`, `tokenizers_version`, `model_revision`, `tokenizer_revision`, and `modal_image_sha`.
- `cluster2/experiments/run_cluster2_modal.py::_generation_grammar_metadata_from_payload` enforces that C rows have no active grammar metadata and returns grammar fields as `None`.
- `cluster2/experiments/run_cluster2_modal.py::_default_generation_metadata_from_payload` extracts runtime/version/provenance fields from the Modal payload and falls back to `"unknown"` for missing runtime identity fields.
- `cluster2/results/dataclass.py::validate_generated_paper_scale_metadata` rejects missing or `"unknown"` required metadata for paper-scale generated rows.
- `cluster2/modal/schemas.py::RemoteC2GenerationResult` requires model/runtime/provenance fields in the remote response and rejects grammar metadata on C.

Impact:

- The row schema can carry all required metadata, and paper-scale validation hard-blocks missing/unknown required generated metadata.
- Smoke/development paths can still serialize `"unknown"` fallback values for some runtime fields, so metadata provenance is not fully proven for cheap C smoke until an actual smoke payload is inspected.

## 5. Block 2 - Repair loop integrity

### 2.1 Repair loop fires only on F2 failures

Status: **PASS**

Evidence:

- `cluster2/feedback/repair_loop.py::_must_terminate_without_feedback` returns true for `level_reached < 2`.
- `cluster2/feedback/prompts.py::ALLOWED_CORRECTNESS_FEEDBACK_FAILURE_CODES` is limited to `F2_NUMERIC_LARGE`, `F2_NUMERIC_NAN`, and `F2_SHAPE_MISMATCH`.
- `cluster2/feedback/repair_loop.py::run_repair_loop` records `feedback_type=None`, `feedback_content=None`, and `feedback_prompt=None` before feedback is built.
- The same loop only calls `build_feedback_prompt_from_result` after the non-terminal F2 check passes.

Impact:

- F0 and F1 failures terminate immediately with `repair_iteration=0` and no feedback prompt. Only allowed F2 correctness failures trigger repair.

### 2.2 F2 corrupted-fixture smoke still works locally

Status: **PASS**

Evidence:

- Test command: `.venv/bin/python -m pytest cluster2/tests -k "repair or feedback or F2 or corrupted or fixture" -q`
- Result: `124 passed, 220 deselected`.
- `cluster2/experiments/run_f2_repair_smoke.py::ARCHETYPES` covers `relu`, `softmax`, and `matmul` corrupted fixture families.
- `cluster2/tests/test_f2_repair_smoke_integration.py::test_f2_smoke_activates_repair_loop_for_each_fixture` verifies that each archetype records an initial F2 failure and then a repair iteration with feedback under mock/local execution.
- `cluster2/tests/test_f2_repair_smoke_integration.py::test_f2_smoke_records_budget_exhaustion_when_mock_repair_does_not_fix` verifies terminal budget exhaustion behavior.

Impact:

- Existing local fixture tests demonstrate that corrupted ReLU, softmax, and matmul fixtures activate the F2 repair path and record traces. This does not replace a fresh canonical smoke artifact generated under the current launch configuration.

### 2.3 Feedback prompt contains only public Level 2 information

Status: **PASS**

Evidence:

- `cluster2/feedback/prompts.py::build_feedback_prompt_from_result` receives public summaries and explicitly ignores compile/signature/sanitizer details for F2 correctness feedback.
- `cluster2/feedback/repair_loop.py::run_repair_loop` passes `compile_error=None`, `signature_error=None`, and `sanitizer_errors=()` into `build_feedback_prompt_from_result`.
- `cluster2/feedback/prompts.py::FORBIDDEN_FEEDBACK_TERMS` blocks timing/profiling/performance terms, low-level compiler/backend terms, private/hidden/eval-shape terms, and traceback-style leakage.
- `cluster2/feedback/prompts.py::_public_detail` redacts sensitive terms and truncates public detail text.
- `shared/eval/levels/level2_correctness.py` exposes repair-shape detail for correctness failures but keeps eval-set details generic.
- Fixture traces in `cluster2/tests/fixtures/expected_smoke_traces/` include public Level 2 summaries such as numeric mismatch and shape mismatch text, not private tensors or exact hidden eval inputs.

Impact:

- Feedback can include public max-absolute/max-relative mismatch, shape mismatch, NaN/Inf, and high-level correctness failure information. It does not include compile-language hints, Triton API hints, profiling/timing hints, private eval-set values, private shapes/inputs, or exact reference tensors.

### 2.4 Max-iteration budget respected

Status: **PASS**

Evidence:

- `cluster2/constants.py::DEFAULT_REPAIR_BUDGET` is `5`.
- `cluster2/feedback/repair_loop.py::run_repair_loop` rejects repair budgets above `DEFAULT_REPAIR_BUDGET`.
- The loop iterates over `range(repair_budget + 1)`, so each row has one initial generation plus at most `repair_budget` repair generations.
- Terminal status and reason are recorded through `RepairLoopResult` and trace summaries.
- Tests under `cluster2/tests` verify budget exhaustion and terminal trace recording.

Impact:

- No runaway repair loop is possible under the current local logic. Worst-case generations are bounded by `1 + repair_budget` per base candidate.

## 6. Block 3 - Eval pipeline integration

### 3.1 C2 uses shared Level 0 + Level 1 eval infrastructure

Status: **FAIL**

Evidence:

- `shared/eval/levels/level0_parse.py` provides `check_parse` and `check_signature`.
- `shared/eval/levels/level1_compile.py` provides `check_compile_level1`.
- `cluster2/modal/correctness_runner.py::run_correctness_payload` calls `shared.eval.pipeline.run_eval_pipeline` with a `PipelineLevel2Request`.
- `shared/eval/pipeline.py::run_eval_pipeline` treats Level 0 and Level 1 as deferred placeholders and only evaluates Level 2 when a `PipelineLevel2Request` is supplied.
- No active call from the generated C2 correctness path to `check_parse`, `check_signature`, or `check_compile_level1` was found.
- `cluster2/experiments/run_f2_repair_smoke.py` uses shared parse/signature helpers for fixture setup, but that is not the active Modal correctness path for generated C rows.

Impact:

- Generated C2 rows are not actively gated through shared Level 0 parse/signature or shared Level 1 compile before Level 2 correctness. This can change F0/F1 classification behavior and blocks C n=1/C n=20 smoke readiness.

### 3.2 C2 Level 2 correctness uses aligned shape schedules

Status: **PASS**

Evidence:

- `shared/eval/levels/level2_correctness.py::evaluate_level2_correctness` calls `shared.eval.correctness_shapes.generate_correctness_shape_sets`.
- `shared/eval/correctness_shapes.py` defines the locked kernel classes, dtype handling, repair/eval split generation, and `get_compile_shapes`.
- `cluster2/modal/correctness_runner.py::run_correctness_payload` reaches Level 2 through `run_eval_pipeline` with a `PipelineLevel2Request`.
- Test command `.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py shared/tests/test_eval_level2_correctness.py -q` passed with `33 passed`.

Impact:

- Level 2 correctness uses the shared aligned shape schedule. No active independent C2-only Level 2 shape schedule was found.

### 3.3 C2 canonicalizes failure codes correctly

Status: **PASS**

Evidence:

- `cluster2/replay/cluster1_controls.py::canonical_failure_code_for_replay_row` constructs a Cluster 1 `GenerationResult`, converts it with `shared.eval.adapter_cluster1.eval_result_from_generation_result`, and classifies it with `shared.eval.failure_taxonomy.classify_failure`.
- `cluster2/results/dataclass.py::Cluster2EvalRow` validates `failure_code` against canonical `shared.eval.failure_taxonomy.FAILURE_CODES`.
- Replay metadata can retain legacy Cluster 1 fields, but primary C2 row classification uses canonical `failure_code`.
- Local replay/control tests passed: `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py -q` returned `86 passed`.

Impact:

- Replayed Cluster 1 rows and generated C2 rows use canonical failure codes as the primary result classification. Legacy `compile_error_type` is not the primary C2 failure code.

## 7. Block 4 - Replay configuration

### 4.1 Frozen none baseline manifest

Status: **PASS**

Evidence:

- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` includes artifact `none_baseline_n20_l4` with path `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- The same manifest selects `none_baseline_n20_l4` under `selected_controls.cluster2_v5_template_upper_bound_controls.artifact_ids`.
- `cluster2/constants.py::FROZEN_NONE_REPLAY_ARTIFACT` is `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- Artifact inspection found `outputs/cluster1/baseline_repaired_l4_n20.jsonl` has 180 rows and 20 rows per `(kernel_class, dtype)` cell.

Impact:

- C-vs-none matched-seed replay has a frozen n=20 none baseline configured and present locally.

### 4.2 Seed matching between C generation and none replay

Status: **PASS**

Evidence:

- `cluster2/experiments/run_cluster2_modal.py::_preflight_paired_generation_schedules` runs for new-generation conditions and calls `cluster2.replay.manifest.replay_seed_schedule_for_condition`.
- `cluster2/experiments/run_cluster2_modal.py::_validate_generation_pairing_context` checks `kernel_class`, `dtype`, `base_seed`, `generation_seed`, `prompt_sha256`, `model_id`, and `temperature` against replay context.
- `cluster2/feedback/repair_loop.py::seed_for_attempt` deterministically derives repair attempt seeds; the runner uses the replayed initial `generation_seed` for attempt 0 through `_paired_generation_seed`.
- Local artifact inspection showed `outputs/cluster1/baseline_repaired_l4_n20.jsonl` has 180 rows, 20 per cell.

Impact:

- Initial C candidates can be matched to the frozen none baseline by dense base seed and generation seed before repair attempts diverge.

### 4.3 G n=20 artifact registered for G+C replay

Status: **FAIL**

Evidence:

- The requested artifact `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` exists locally.
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` does not register that path as the selected task-agnostic G n=20 replay artifact.
- The manifest's `selected_controls.task_agnostic_g_status.available_development_artifact_id` points to `g_task_agnostic_n5_l4_rerun`, not the n=20 aligned-pipeline artifact.
- `cluster2/replay/manifest.py::_task_agnostic_g_artifact_id` selects the manifest's available development artifact for task-agnostic G, not the new n=20 file.
- `cluster2/experiments/run_cluster2_modal.py::_preflight_primary_gc_replay_alignment` blocks paper-scale task-agnostic G+C when the manifest says paper rows are not sufficient.

Impact:

- G+C can use the existing n=5 development task-agnostic replay path, but the new n=20 task-agnostic G artifact is not configured as the replay source. G+C n=20/paper replay is blocked until the manifest/configuration is updated with a complete artifact.

### 4.4 Missing 3 matmul rows handled safely

Status: **PARTIAL**

Evidence:

- Artifact inspection found `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` has 177 rows.
- Expected grid is 180 rows: 3 kernel classes x 3 dtypes x 20.
- Missing rows by cell:
  - `matmul/fp32`: 19 present, 1 missing.
  - `matmul/bf16`: 18 present, 2 missing.
  - All other cells: 20 present.
- `cluster2/replay/manifest.py::_coverage_for_artifact` and `_seed_schedule_failures` compute coverage and seed-schedule failures.
- `cluster2/replay/manifest.py::replay_seed_schedule_for_condition` requires enough dense entries for the requested candidate count.
- `cluster2/replay/cluster1_controls.py::map_replay_candidates` returns or raises coverage failures when requested replay candidates are not available.
- The exact 177-row artifact is not registered, so its behavior as a selected C2 replay artifact cannot be fully exercised without modifying configuration.

Impact:

- C2 does not currently treat the 177-row task-agnostic n=20 artifact as full 180 coverage because it is not registered. Existing replay coverage code should reject short/dense-missing schedules if such an artifact is selected for n=20, but the exact artifact is not wired in.

## 8. Block 5 - Sample size and cost guards

### 5.1 Expected C n=20 coverage

Status: **PARTIAL**

Evidence:

- Expected base candidate grid is 3 kernel classes x 3 dtypes x 20 = 180 initial C candidates.
- `cluster2/experiments/run_cluster2_modal.py::MAX_CLI_N` is `20`.
- `cluster2/experiments/run_cluster2_modal.py::_run_generated_condition` iterates configured kernel classes and dtypes and calls `_run_generated_cell` for each cell.
- `cluster2/experiments/run_cluster2_modal.py::_preflight_paired_generation_schedules` validates paired replay schedules before generation.
- Repair attempts produce additional rows beyond the 180 initial candidates, so generated output row count can exceed 180.

Impact:

- The base n=20 pairing grid is enforced by replay schedule preflight, but total JSONL row count is not expected to be exactly 180 once repairs are included. Missing initial candidates should fail preflight rather than be silently ignored.

### 5.2 Cost ceiling / worst-case repair budget

Status: **PARTIAL**

Evidence:

- `cluster2/constants.py::DEFAULT_REPAIR_BUDGET` is `5`.
- Worst-case C n=20 base candidates: 180.
- Worst-case generations per base candidate: initial + 5 repairs = 6.
- Worst-case candidate generations: 180 x 6 = 1080.
- `cluster2/feedback/repair_loop.py::run_repair_loop` enforces the repair budget.
- `cluster2/experiments/run_cluster2_modal.py::Cluster2RunnerConfig.__post_init__` rejects repair budgets above the default budget.
- `cluster2/constants.py::DEFAULT_C2_MODAL_GENERATION_GPU` and `DEFAULT_C2_MODAL_EVAL_GPU` are both `L4`.
- No explicit Modal spend/dollar cap was found in the runner. Live progress appears limited to final summaries and route audits, not durable per-row progress.

Impact:

- Repair cost is bounded by iteration count, but Modal cost is not capped by an explicit spend ceiling. Worst-case cost monitoring remains manual.

### 5.3 Early termination / manual kill path

Status: **FAIL**

Evidence:

- `cluster2/experiments/run_cluster2_modal.py::run_cluster2` calls `_write_rows` only after all selected conditions finish and after `_validate_paper_scale_generation_metadata`.
- `cluster2/results/logger.py` states that there is no append mode; resume validates existing rows and rewrites the full deterministic output.
- `cluster2/results/logger.py::write_cluster2_results_jsonl` materializes `row_tuple = tuple(rows)` and writes the whole output with `output_path.write_text(...)`.
- `cluster2/results/logger.py::_validate_mode` rejects append mode.

Impact:

- A user can manually stop a Modal run externally, but partial outputs are not guaranteed to be valid or even present. JSONL is not flushed per row. This is unsafe for a C n=20 smoke run where partial progress may matter for cost control and diagnosis.

## 9. Block 6 - Pre-flight recommendation

Exact next action: **BLOCK_C_RUN**.

Do not run C n=1 or C n=20 yet. The C generation path itself is grammar-free and the repair loop is locally sound, but C smoke is blocked by active eval integration and output durability:

1. Fix the generated C2 correctness path so it actively calls shared Level 0 parse/signature and shared Level 1 compile before Level 2 correctness.
2. Add or verify durable partial-output handling before spending Modal/GPU money on C n=20.
3. Keep the required sequence after fixes:
   - Run F2 corrupted-fixture smoke fresh.
   - Run C-only n=1 single-kernel smoke.
   - If n=1 passes, run paper-scale C n=20.

For G+C, fix the replay gap before paper-scale G+C by registering a complete task-agnostic G n=20 artifact or explicitly blocking task-agnostic G+C until coverage is 180/180.

## 10. Risk register

Contaminated C condition:

- Status: low current risk.
- C routing, schemas, Modal generation, and result validation reject grammar metadata for C.

Repair loop firing on F0/F1:

- Status: low current risk in local repair-loop logic.
- `_must_terminate_without_feedback` stops below Level 2; fixture tests passed.

Metadata/provenance failure:

- Status: medium risk.
- Revisions are required and propagated, but C2 does not hardcode the expected revision default. Runtime provenance can fall back to `"unknown"` outside paper-scale validation.

Replay coverage gap:

- Status: high risk for G+C task-agnostic n=20.
- The new artifact has 177/180 rows and is not registered for replay.

Runaway repair cost:

- Status: medium risk.
- Repair iterations are capped at 5, but no Modal spend cap was found. Worst-case C n=20 is 1080 candidate generations.

Partial-output handling:

- Status: high risk.
- Results are buffered and written at completion; no per-row JSONL flush or append mode exists.

## 11. Final classification

**C2_SMOKE_BLOCKED**

## 12. Appendix

### Commands run

```bash
rg "condition|grammar_active|grammar_variant|C\+G|G\+C|condition.*C|repair|feedback|max_repair|max_iterations|max_iter" cluster2 shared cluster1
rg "AutoModel|AutoTokenizer|model_revision|tokenizer_revision|8e8ed243bbe6f9a5aff549a0924562fc719b2b8a|Qwen/Qwen2.5-Coder-7B-Instruct-AWQ|revision" cluster2 shared cluster1
rg "prompt|build_prompt|PROMPT_TEMPLATE|base prompt|baseline|none|grammar_active=False|grammar_active = False" cluster2 cluster1 shared
rg "F2_|F0_|F1_|compile|signature|numeric|max abs|max rel|NaN|Inf|shape mismatch|private eval|repair_iteration|feedback_prompt" cluster2 shared
rg "generate_correctness_shape_sets|get_compile_shapes|correctness_shapes|shape schedule|repair shapes|eval shapes|private eval|base_seed|generation_seed|sample_index|seed" cluster2 shared cluster1
rg "frozen_cluster1_artifacts_manifest|baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|replay|coverage|missing|177|180" cluster2 shared outputs audits
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py -q
.venv/bin/python -m pytest cluster2/tests -k "repair or feedback or F2 or corrupted or fixture" -q
.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py shared/tests/test_eval_level2_correctness.py -q
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from collections import Counter, defaultdict

paths = [
    Path("outputs/cluster1/baseline_repaired_l4_n20.jsonl"),
    Path("outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl"),
]

for p in paths:
    print("ARTIFACT", p)
    if not p.exists():
        print("MISSING")
        continue
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    print("rows", len(rows))
    keys = sorted(set().union(*(r.keys() for r in rows))) if rows else []
    print("keys", keys)
    for field in ["kernel_class", "dtype", "grammar_variant", "grammar_valid", "compile_success", "failure_code", "stop_reason", "rejection_layer"]:
        if field in keys:
            print(field, dict(Counter(r.get(field) for r in rows)))
    by_cell = defaultdict(int)
    for r in rows:
        by_cell[(r.get("kernel_class"), r.get("dtype"))] += 1
    print("by_cell", dict(sorted(by_cell.items())))
PY
```

### Key outputs

- `cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py`: `86 passed`.
- `cluster2/tests -k "repair or feedback or F2 or corrupted or fixture"`: `124 passed, 220 deselected`.
- `shared/tests/test_eval_failure_taxonomy.py shared/tests/test_eval_level2_correctness.py`: `33 passed`.
- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`: `180` rows; every `(kernel_class, dtype)` cell has `20` rows.
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`: `177` rows.
- Missing task-agnostic G n=20 rows:
  - `matmul/fp32`: 1 missing.
  - `matmul/bf16`: 2 missing.

### Key file paths and functions

- C grammar routing: `cluster2/modal/generation.py::generation_routing_for_condition`
- C remote generation: `cluster2/modal/generation.py::run_c2_generation_with_loaded_model`
- Remote request/result schemas: `cluster2/modal/schemas.py::RemoteC2GenerationRequest`, `RemoteC2GenerationResult`
- C2 runner: `cluster2/experiments/run_cluster2_modal.py::run_cluster2`, `_run_generated_cell`, `_build_base_prompt`, `_validate_generation_pairing_context`
- Repair loop: `cluster2/feedback/repair_loop.py::run_repair_loop`, `_must_terminate_without_feedback`
- Feedback prompt: `cluster2/feedback/prompts.py::build_feedback_prompt_from_result`, `build_feedback_prompt`, `ALLOWED_CORRECTNESS_FEEDBACK_FAILURE_CODES`
- Shared Level 0: `shared/eval/levels/level0_parse.py::check_parse`, `check_signature`
- Shared Level 1: `shared/eval/levels/level1_compile.py::check_compile_level1`
- Shared Level 2: `shared/eval/levels/level2_correctness.py::evaluate_level2_correctness`
- Shape schedule: `shared/eval/correctness_shapes.py::generate_correctness_shape_sets`, `get_compile_shapes`
- Active C2 correctness runner: `cluster2/modal/correctness_runner.py::run_correctness_payload`
- Replay manifest: `cluster2/replay/manifest.py::replay_seed_schedule_for_condition`
- Replay canonicalization: `cluster2/replay/cluster1_controls.py::canonical_failure_code_for_replay_row`
- Results schema: `cluster2/results/dataclass.py::Cluster2GeneratedRowMetadata`, `Cluster2EvalRow`, `validate_generated_paper_scale_metadata`
- Results writer: `cluster2/results/logger.py::write_cluster2_results_jsonl`
