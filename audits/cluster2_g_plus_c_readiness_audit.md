# Cluster 2 G+C Readiness Audit

## 1. Executive summary

Final classification: **G_PLUS_C_SMOKE_READY_WITH_WARNINGS**.

G+C is ready for the optional n=1 Modal smoke after explicit approval. It is not ready for a complete 180/180 paper-scale matched analysis because the registered task-agnostic G replay artifact has 177/180 rows. A paper-scale covered-row run is locally gated as warning-skip-missing and would analyze only the covered matched rows unless the missing matmul replay rows are regenerated and registered.

Main warnings:

- The registered task-agnostic G replay artifact is intentionally incomplete: 177 observed rows out of 180 intended rows. Missing identities are `matmul/fp32/sample_index=5`, `matmul/bf16/sample_index=0`, and `matmul/bf16/sample_index=18`.
- The optional smoke command must include the current required CLI flag `--scale-tier smoke`; `cluster2/experiments/run_cluster2_modal.py:252-255` requires `--scale-tier`.
- Live Modal-only evidence, such as the actual runtime `modal_image_sha` and tokenizer/model revision values emitted by a smoke row, was not produced because Modal and G+C generation were forbidden during this audit.

No blocking issue was found in the local G+C routing, registered replay pairing, matched-seed semantics, F2 repair behavior, or row metadata schema.

## 2. Scope

This is a five-question focused G+C readiness audit. It is not a full cross-cluster audit, not a full pre-paper factorial audit, and not a re-audit of unrelated C-only issues.

No Modal, GPU compile/eval, G+C generation, C n=20, paper-scale run, artifact rewrite, hash update, or code modification was run. The only repository change made by this audit is this markdown report.

## 3. Question 1 - Task-agnostic grammar routing

Status: **PASS**.

Evidence:

- `cluster2/modal/generation.py:58-59` sets `C2_G_PLUS_C_GRAMMAR_VARIANT = "task_agnostic"` and resolves `C2_G_PLUS_C_GRAMMAR_PATH` from `GRAMMAR_PATHS_BY_VARIANT`.
- `cluster2/modal/generation.py:261-292`, `generation_routing_for_condition`, defaults G+C to that variant when no explicit `grammar_variant` is provided, returns `grammar_active=True`, and resolves `grammar_path="cluster1/grammar/triton_kernel_agnostic.gbnf"`.
- `cluster2/experiments/run_cluster2_modal.py:77-82` defines the supported variants, and `cluster2/experiments/run_cluster2_modal.py:263-267` makes `--grammar-variant` default to `task_agnostic`.
- `cluster2/experiments/run_cluster2_modal.py:371-382` defaults the Modal entrypoint argument to `task_agnostic`.
- `shared/generation_metadata.py:30-38` maps `task_agnostic` to `cluster1/grammar/triton_kernel_agnostic.gbnf` with claim scope `primary`; `template_upper_bound` maps to `cluster1/grammar/triton_kernel.gbnf` with claim scope `diagnostic_non_primary`.
- Local route reconstruction returned `C2GenerationRouting(condition='G+C', grammar_active=True, grammar_variant='task_agnostic', grammar_path='cluster1/grammar/triton_kernel_agnostic.gbnf', grammar_claim_scope='primary')`.

Template-upper-bound status:

- Still supported as an explicit diagnostic/reference option in `cluster2/modal/generation.py:60-68`, `cluster2/modal/generation.py:80-82`, and `cluster2/experiments/run_cluster2_modal.py:79-82`.
- Not the default active G+C path.

## 4. Question 2 - Registered G replay artifact

Status: **PASS**.

Manifest/config evidence:

- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:16917-16932` registers `g_task_agnostic_aligned_pipeline_n20_l4` for condition `G`, expected grammar variant `task_agnostic`, `coverage_policy=COVERAGE_WARNING_SKIP_MISSING`, `expected_n=20`, and `intended_rows=180`.
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:16980-16984` records `observed_rows=177`, path `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, and `row_count=177`.
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:23243-23270` records `available_task_agnostic_g_n20_replay_artifact_id="g_task_agnostic_aligned_pipeline_n20_l4"`, the same artifact path, `coverage_complete=false`, `coverage_policy=COVERAGE_WARNING_SKIP_MISSING`, and the three missing rows.
- `cluster2/modal/generation.py:80-82` maps the task-agnostic G+C hash gate to `g_task_agnostic_aligned_pipeline_n20_l4`; local hash-gate reconstruction returned `{'task_agnostic': 'g_task_agnostic_aligned_pipeline_n20_l4', 'template_upper_bound': 'g_template_upper_bound_n20_l4'}` and verified the manifest hash `fdb46b817d9b2d9b6c1663b4b31585d2b815e78be7562f575cd801cf9f7c781a`.
- `cluster2/replay/manifest.py:208-220` selects the task-agnostic G artifact when replay condition is `G` and `grammar_variant="task_agnostic"`.
- `cluster2/replay/manifest.py:625-648` reads `available_task_agnostic_g_n20_replay_artifact_id` first, falls back only to `available_development_artifact_id` if absent, and validates that the selected artifact belongs to condition `G` and is marked task-agnostic.

Artifact inspection:

- Local artifact path exists: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`.
- Local row count is `177`.
- All rows have `grammar_variant="task_agnostic"`.
- By cell: `elementwise/*` and `reduction/*` each have 20 rows; `matmul/fp32` has 19 rows; `matmul/fp16` has 20 rows; `matmul/bf16` has 18 rows.

Missing-row warning/block behavior:

- `cluster2/experiments/run_cluster2_modal.py:984-1011` preflights G+C task-agnostic replay coverage, treats `COVERAGE_WARNING_SKIP_MISSING` as `allow_incomplete`, rejects duplicate/unexpected/invalid rows, and appends a coverage warning when coverage is incomplete.
- `cluster2/replay/manifest.py:431-518` returns the manifest-authoritative seed schedule and raises a clear `seed_schedule coverage failure` or dense-window error when incomplete coverage is not allowed.
- `cluster2/replay/cluster1_controls.py:325-350` reports a coverage failure rather than generating fallback rows when missing rows are not covered by skip policy.

No stale fallback:

- The old `g_task_agnostic_n5_l4_rerun` artifact remains registered as a historical/development artifact at `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:15036-15090`, but it is not selected by the current G+C hash gate or `selected_controls.task_agnostic_g_status`.
- Template G replay resolves only through the explicit `template_upper_bound` diagnostic route.

## 5. Question 3 - Matched-seed semantics

Status: **PASS**.

Identity fields actually used:

- `kernel_class`
- `dtype`
- `sample_index` when present in source rows
- `generation_seed` as the sample identity fallback for raw Cluster 1 rows
- `base_seed` in manifest row records and generated C2 rows
- `attempt_index`
- `generation_index`
- `replay_pair_id`

Evidence:

- The raw task-agnostic G artifact contains `generation_seed` but not top-level `sample_index` or `base_seed`; local artifact inspection reported `generation_seed present 177 unique 20`.
- `cluster2/replay/manifest.py:951-960` derives replay sample identity from `sample_index`, then `generation_seed`, then `base_seed`.
- Manifest row records materialize `base_seed`, `generation_seed`, `attempt_index`, `generation_index`, and `replay_pair_id`, as shown at `cluster2/contracts/frozen_cluster1_artifacts_manifest.json:16985-17005`.
- `cluster2/replay/manifest.py:431-518` constructs the selected replay seed schedule from the selected artifact and validates it against coverage when skip-missing is active.
- `cluster2/replay/manifest.py:521-593` rejects skip-policy schedules that omit rows not reported in `replay_missing_rows`, contain duplicate logical identities, or schedule unexpected rows.
- `cluster2/replay/cluster1_controls.py:563-678` validates seed schedule list lengths, uniqueness, `generation_seeds == base_seeds`, `generation_indexes == attempt_indexes`, and emits `ReplaySeedScheduleEntry` values keyed by base seed.
- `cluster2/experiments/run_cluster2_modal.py:976-1036` uses the same paired schedule mechanism for generated conditions; `cluster2/experiments/run_cluster2_modal.py:1058-1063` maps `C -> none` and `G+C -> G`.
- `cluster2/experiments/run_cluster2_modal.py:1103-1109` uses the replay `generation_seed` for attempt 0 and deterministic `seed_for_attempt(base_seed, attempt_index)` for repair attempts.
- `cluster2/experiments/run_cluster2_modal.py:1120-1166` validates the pairing context before generation, including `kernel_class`, `dtype`, `base_seed`, `generation_seed`, prompt hash, model id, known revisions, and temperature.
- `cluster2/experiments/run_cluster2_modal.py:1215-1233` records generated C2 identity with `sample_index=base_seed` and `base_seed=base_seed`.

Local dry reconstruction:

- For task-agnostic G with `candidate_count=20`, the schedule selected 177 covered entries and skipped only the three manifest-reported missing matmul identities.
- Covered schedules kept `generation_seed == base_seed`, `generation_index == attempt_index`, and stable `replay_pair_id` values.
- Matched-pair analysis remains valid for covered rows because missing G replay rows are detected during preflight/schedule construction and are not silently counted as failures or successes.

## 6. Question 4 - F2 repair behavior for G+C

Status: **PASS**.

Conditionals inspected:

- `cluster2/feedback/repair_loop.py:138` accepts generated conditions through `require_generated_condition`, which allows both `C` and `G+C`.
- `cluster2/feedback/repair_loop.py:183-187` terminates without feedback only for success or `_must_terminate_without_feedback`.
- `cluster2/feedback/repair_loop.py:234-246` returns a terminated result for non-repairable failures.
- `cluster2/feedback/repair_loop.py:251-270` builds feedback and advances to the next prompt for repairable failed attempts.
- `cluster2/feedback/repair_loop.py:366-369` terminates without feedback for `level_reached < 2` or failure codes not allowed for feedback.
- `cluster2/feedback/prompts.py:17-23` allows only F2 correctness feedback codes: `F2_NUMERIC_LARGE`, `F2_NUMERIC_NAN`, and `F2_SHAPE_MISMATCH`.
- `cluster2/feedback/prompts.py:138-142` allows feedback for all `NEW_GENERATION_CONDITIONS`, which are `C` and `G+C`; there is no `grammar_active` or `grammar_variant` gate.
- `cluster2/feedback/prompts.py:190-250` builds the prompt from public Level-2 failure fields and validates that forbidden non-Level-2 detail is absent.
- `cluster2/modal/schemas.py:505-511` rejects feedback on pre-Level-2 failures in correctness result schema.
- `cluster2/experiments/run_cluster2_modal.py:740-764` passes `grammar_variant=config.grammar_variant` on G+C generation calls, including repair attempts, while `run_repair_loop` controls retry behavior by failure class.

Tests/local evidence:

- `cluster2/tests/test_repair_loop.py:62-74` parametrizes repair-loop acceptance over `C` and `G+C`.
- `cluster2/tests/test_repair_loop.py:139-166` verifies F0/F1 seed failures terminate without feedback.
- `cluster2/tests/test_repair_loop.py:169-191` verifies G+C retries through repair attempts after F2 failures.
- `cluster2/tests/test_run_cluster2_modal.py:388-423` verifies repair attempt seed scheduling and trace persistence.
- Focused feedback/repair tests passed: `128 passed, 265 deselected`.

Conclusion:

Repair is failure-class-based for generated conditions. No inspected conditional suppresses repair for `condition == "G+C"`, `grammar_active=True`, or `grammar_variant="task_agnostic"`. F0/F1 terminate without feedback; F2 failures enter the same repair path as C.

## 7. Question 5 - G+C metadata schema

Status: **PASS**.

C metadata fields in final rows:

- `cluster2/results/dataclass.py:391-418` defines final row fields including `condition`, `source_class`, `generation_mode`, `attempt_index`, `kernel_class`, `kernel_name`, `dtype`, `base_seed`, `source_hash`, `grammar_active`, `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, `failure_code`, `trace_summary`, `replay_metadata`, `generated_metadata`, and `repair_trace`.
- `cluster2/results/dataclass.py:420-465` validates condition routing, kernel/dtype identity, boolean fields, `functional_success`, canonical `failure_code`, and `compile_success` consistency.
- `cluster2/results/dataclass.py:533-553` enforces generated-row grammar-active semantics: G+C rows require `grammar_active=True` and grammar metadata; C rows must remain grammar-free.
- `cluster2/results/dataclass.py:938-986`, `generated_row`, writes the generated final row and nested generated metadata.
- `cluster2/results/logger.py:165-188` appends canonical `Cluster2EvalRow` JSONL rows, and `cluster2/results/logger.py:292-319` validates generated rows against generated-condition hash sidecars.

Grammar and provenance fields:

- `cluster2/modal/schemas.py:245-268` defines `RemoteC2GenerationResult` fields for `model_revision`, `tokenizer_revision`, grammar metadata, runtime versions, Modal image provenance, schema version, and `generation_seed`.
- `cluster2/modal/schemas.py:301-309` enforces `C` has `grammar_active=False` and `G+C` has `grammar_active=True`.
- `cluster2/modal/schemas.py:357-367` enforces `grammar_valid == (gbnf_parse_valid and semantic_valid)` and correct `rejection_layer` nullability.
- `cluster2/modal/schemas.py:370-393` requires current-schema G+C generation results to include non-null `grammar_sha`, `grammar_path`, `grammar_variant`, `gbnf_parse_valid`, `semantic_valid`, and `grammar_valid`.
- `cluster2/modal/generation.py:438-464` constructs `RemoteC2GenerationResult` with grammar validation fields, `stop_reason`, `xgrammar_version`, `transformers_version`, `tokenizers_version`, `modal_image_sha`, Modal image provenance, schema version, and `generation_seed`.
- `cluster2/modal/generation.py:532-566` includes `generation_identity`, `model_identity`, and `runtime_identity` in the generation payload.
- `cluster2/experiments/run_cluster2_modal.py:1312-1405` extracts and validates G+C grammar metadata, requiring `grammar_active=True`, non-empty grammar fields, a 64-character `grammar_sha`, and local grammar revalidation.
- `cluster2/experiments/run_cluster2_modal.py:1408-1451` verifies `grammar_path` against `grammar_path_for_variant`, verifies `grammar_sha` against the local canonical grammar file, and compares Modal validation fields against local `validate_source_layers`.
- `cluster2/experiments/run_cluster2_modal.py:1472-1517` extracts model/tokenizer/runtime provenance defaults.
- `cluster2/results/dataclass.py:298-329` defines generated metadata fields including `generation_seed`, `grammar_variant`, `grammar_path`, `grammar_sha`, `grammar_claim_scope`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, `stop_reason`, `xgrammar_version`, `transformers_version`, `tokenizers_version`, `modal_image_sha`, Modal provenance, replay pairing, model revisions, temperature, and max token budget.
- `cluster2/results/dataclass.py:1196-1222` validates grammar variant/path/scope consistency.
- `cluster2/results/dataclass.py:1225-1307` validates current-schema generated runtime and grammar metadata, including the grammar-valid invariant.
- `cluster2/results/dataclass.py:1383-1447` applies paper-scale generated metadata gates for model/tokenizer revisions, runtime versions, grammar fields, Modal image provenance, and schema version.

Analyzer readiness:

- `shared/analysis/factorial.py:54-63` recognizes the four current cells, uses `compile_success` and `functional_success`, maps `G+C` paired replay comparison to `G`, and pairs on `kernel_class`, `kernel_id`, `dtype`, and `base_seed`.
- `shared/analysis/factorial.py:888-894` uses `grammar_variant` when labeling grammar conditions.
- Final rows can distinguish C from G+C using top-level `condition`, `generation_mode`, `grammar_active`, and nested grammar metadata.

Local test evidence:

- Result/schema tests passed: `90 passed`.
- Broad targeted selector passed: `185 passed, 208 deselected`.
- Metadata-specific tests in `cluster2/tests/test_results_logger.py` and `cluster2/tests/test_modal_schemas.py` cover generated C/G+C separation, current-schema grammar metadata requirements, `grammar_valid` invariant behavior, model/tokenizer provenance, and Modal image provenance fallback.

Live-value caveat:

The schema and local construction path populate the required grammar fields for G+C. Actual non-unknown runtime values for the optional smoke checks, especially `modal_image_sha`, can only be confirmed by the explicitly approved Modal smoke.

## 8. Optional smoke recommendation

Recommendation: **G_PLUS_C_N1_SMOKE_RECOMMENDED**.

Use the task's proposed smoke only after explicit approval, with the current required `--scale-tier smoke` flag added:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal \
  --condition G+C \
  --kernel-class elementwise \
  --scale-tier smoke \
  --n 1 \
  --max-new-tokens 2048 \
  --output outputs/cluster2/g_plus_c_smoke_n1.jsonl \
  --modal-generation-gpu L4 \
  --modal-eval-gpu L4 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --overwrite
```

Do not run paper-scale until the project accepts either covered-row analysis with the explicit 177/180 warning or registers a complete task-agnostic G replay artifact.

## 9. Final classification

**G_PLUS_C_SMOKE_READY_WITH_WARNINGS**

## 10. Appendix

### Commands run

- Required search: `rg -n "G\+C|G_PLUS_C|g_plus_c|condition.*G|condition.*C|grammar_active|grammar_variant|task_agnostic|template_upper_bound|triton_kernel_agnostic|triton_kernel.gbnf" cluster2 cluster1 shared`
- Required search: `rg -n "frozen_cluster1_artifacts_manifest|g_task_agnostic_aligned_pipeline_n20_l4|task_agnostic_g_aligned_pipeline_n20_l4|g_task_agnostic_n5|coverage|COVERAGE_WARNING_SKIP_MISSING|missing|177|180" cluster2 outputs audits`
- Required search: `rg -n "base_seed|generation_seed|sample_index|seed|matched|pair|replay|attempt_index|kernel_class|dtype" cluster2 shared cluster1`
- Required search: `rg -n "F2_|F0_|F1_|repair|feedback|repair_loop|grammar_active|grammar_variant|condition|should_repair|build_feedback_prompt" cluster2 shared`
- Required search: `rg -n "grammar_sha|gbnf_parse_valid|semantic_valid|grammar_valid|rejection_layer|stop_reason|tokenizer_revision|modal_image_sha|model_revision|xgrammar_version" cluster2 shared cluster1`
- Artifact inspection with `.venv/bin/python`: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
- Manifest coverage reconstruction with `.venv/bin/python`: `replay_coverage_report_for_condition("G", grammar_variant="task_agnostic")`
- Replay schedule dry reconstruction with `.venv/bin/python`: `replay_seed_schedule_for_condition(... allow_incomplete=True)` for all kernel/dtype cells.
- Routing/hash-gate reconstruction with `.venv/bin/python`: `generation_routing_for_condition("G+C")`, `C2_FROZEN_G_ARTIFACT_BY_GRAMMAR_VARIANT`, and `_verify_phase_minus1_frozen_g_manifest(grammar_variant="task_agnostic")`.
- `.venv/bin/python -m pytest cluster2/tests -k "g_plus_c or G\+C or grammar_variant or task_agnostic or replay or matched or seed or repair or metadata" -q`
- `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py -q`
- `.venv/bin/python -m pytest cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py -q`
- `.venv/bin/python -m pytest cluster2/tests -k "repair or feedback or F2 or failure_code" -q`

### Key outputs

- G+C route: `grammar_active=True`, `grammar_variant=task_agnostic`, `grammar_path=cluster1/grammar/triton_kernel_agnostic.gbnf`, `grammar_claim_scope=primary`.
- Hash-gate artifact map: `task_agnostic -> g_task_agnostic_aligned_pipeline_n20_l4`; `template_upper_bound -> g_template_upper_bound_n20_l4`.
- Verified frozen manifest hash: `fdb46b817d9b2d9b6c1663b4b31585d2b815e78be7562f575cd801cf9f7c781a`.
- Registered task-agnostic G replay artifact: `g_task_agnostic_aligned_pipeline_n20_l4`.
- Artifact path: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`.
- Artifact rows: observed `177`, intended `180`.
- Missing replay identities: `matmul/fp32/5`, `matmul/bf16/0`, `matmul/bf16/18`.
- Artifact inspection: `grammar_variant {'task_agnostic': 177}`, `generation_seed present 177 unique 20`, `grammar_valid {True: 49, False: 128}`.
- Schedule reconstruction: all covered entries keep `generation_seed == base_seed`; missing entries are skipped only under `COVERAGE_WARNING_SKIP_MISSING`.

### Tests

- Broad local selector: `185 passed, 208 deselected`.
- Replay/runner tests: `72 passed`.
- Result/schema tests: `90 passed`.
- Feedback/repair tests: `128 passed, 265 deselected`.

### Files inspected

- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/modal/generation.py`
- `cluster2/modal/schemas.py`
- `cluster2/generation/modal_generate_c2.py`
- `cluster2/constants.py`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- `cluster2/replay/manifest.py`
- `cluster2/replay/cluster1_controls.py`
- `cluster2/feedback/repair_loop.py`
- `cluster2/feedback/prompts.py`
- `cluster2/feedback/trace.py`
- `cluster2/results/dataclass.py`
- `cluster2/results/logger.py`
- `cluster2/tests/`
- `shared/generation_metadata.py`
- `shared/analysis/factorial.py`
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
