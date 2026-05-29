# C2 Replay Readiness For G+C From Task-Agnostic G n=20 Audit

## 1. Executive summary

Final classification: `C2_REPLAY_READY_WITH_COVERAGE_WARNING`.

C2 can read and map the 177-row task-agnostic G artifact at `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` as the selected task-agnostic G replay/control artifact. Local replay diagnostics deserialized 177 rows with 0 schema rejections, and manifest-driven `map_replay_candidates(..., grammar_variant="task_agnostic")` mapped 177 replay candidates from artifact id `g_task_agnostic_aligned_pipeline_n20_l4`.

G+C can proceed using this artifact only with the explicit coverage caveat already encoded in C2: the intended 180-row grid is incomplete by 3 matmul rows. C2 does not silently treat the replay input as complete. It reports `COVERAGE_WARNING_SKIP_MISSING`, maps only matched rows, and surfaces `ok_with_coverage_warning` for the affected matmul cells.

Missing-row behavior classification: `GRACEFUL_SKIP_WITH_WARNING`.

## 2. Scope

This is a narrow replay-readiness audit only. It is not a full cross-cluster audit, not an 18-question audit, and not a full pipeline re-verification.

No Modal, GPU jobs, generation, repair loops, C runs, G+C runs, n=20 reruns, artifact rewrites, hash re-recording, or code modification were run. The only repository write performed was this audit report.

## 3. Artifact summary

Path: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

Observed rows: 177

Expected intended grid: 180 rows = 3 kernels x 3 dtypes x 20 samples

JSONL validity: PASS, 177 valid rows, 0 bad JSON lines.

Cell counts:

| kernel_class | dtype | rows | missing generation_seed values |
|---|---:|---:|---|
| elementwise | bf16 | 20 | none |
| elementwise | fp16 | 20 | none |
| elementwise | fp32 | 20 | none |
| matmul | bf16 | 18 | 0, 18 |
| matmul | fp16 | 20 | none |
| matmul | fp32 | 19 | 5 |
| reduction | bf16 | 20 | none |
| reduction | fp16 | 20 | none |
| reduction | fp32 | 20 | none |

All missing rows are matmul rows:

- `matmul/fp32/sample_index=5`
- `matmul/bf16/sample_index=0`
- `matmul/bf16/sample_index=18`

## 4. Question 1 - C2 deserialization

Answer: PASS.

C2 replay functions inspected:

- `cluster2.replay.cluster1_controls.deserialize_cluster1_replay_artifact`
- `cluster2.replay.cluster1_controls._deserialize_replay_row`
- `cluster2.replay.cluster1_controls.map_replay_candidates`
- `cluster2.replay.cluster1_controls._load_raw_artifact_rows`
- `cluster2.replay.cluster1_controls._candidate_from_record`
- `cluster2.replay.cluster1_controls.canonical_failure_code_for_replay_row`
- `cluster2.replay.manifest.selected_replay_artifact_ids_for_condition`
- `cluster2.replay.manifest.replay_coverage_report_for_condition`
- `cluster2.replay.manifest.replay_seed_schedule_for_condition`
- `cluster2.experiments.run_cluster2_modal._run_replay_condition`
- `cluster2.experiments.run_cluster2_modal._preflight_paired_generation_schedules`

Direct deserialization result:

- Function used: `deserialize_cluster1_replay_artifact(...)`
- Row schema: `FrozenCluster1ReplayRow`
- Intermediate schema validation: raw JSON row -> `generation_result_record_for_deserialization(...)` -> `GenerationResult(...)` -> `validate_result_invariants(...)`
- Rows deserialized: 177
- Rows rejected: 0
- Rejection reasons: none

Manifest-driven replay mapping result:

- Function used: `map_replay_candidates(...)`
- Candidate schema: `FrozenReplayCandidate`
- Selected artifact id: `g_task_agnostic_aligned_pipeline_n20_l4`
- Mapped candidates: 177
- Mapping statuses: 7 complete cells as `ok`, 2 incomplete cells as `ok_with_coverage_warning`

C2 uses `shared.eval.adapter_cluster1.eval_result_from_generation_result` and `shared.eval.failure_taxonomy.classify_failure` in `canonical_failure_code_for_replay_row(...)`.

## 5. Question 2 - field extraction correctness

### Source extraction

Answer: PASS.

Actual field name: `source`.

Raw artifact:

- `source` present and non-empty: 177 / 177

C2 direct deserialization:

- `FrozenCluster1ReplayRow.source` present and non-empty: 177 / 177

C2 manifest-driven mapping:

- `FrozenReplayCandidate.source` present and non-empty: 177 / 177
- `_candidate_from_record(...)` also verifies `source_sha256` against manifest `row_records` before constructing the candidate.

### Seed extraction

Answer: PASS.

Actual raw field name: `generation_seed`.

Actual C2 identity fields:

- direct deserialization: `sample_index` derived from `sample_index`, `generation_seed`, or `base_seed`; this artifact uses `generation_seed`
- replay mapping: manifest `seed_schedule` and `row_records` provide `base_seed`, `generation_seed`, `attempt_index`, `generation_index`, `line_number`, and `replay_pair_id`

Counts:

- raw `generation_seed` present: 177 / 177
- unique raw `generation_seed` values: 20
- direct C2 `sample_index` present: 177 / 177
- direct C2 `generation_seed` present: 177 / 177
- mapped C2 `base_seed` and `generation_seed` present: 177 / 177

Identity is sufficient to reconstruct the expected 20 samples per kernel/dtype cell; the coverage report uses the zero-based sample identity and identifies the three absent identities.

### Canonical failure_code extraction

Answer: PASS.

C2 uses canonical row-level `failure_code` when present, and the shared adapter/taxonomy path otherwise. It does not use legacy `compile_error_type` as the primary replay failure code.

Raw artifact counts:

- row-level `failure_code` present and non-empty: 174 / 177
- row-level `failure_code` absent because compile succeeded: 3 / 177
- `compile_error_type` distribution: `RuntimeError`: 152, `CompilationError`: 9, `SignatureError`: 13, `None`: 3

C2 canonical failure-code distribution, both direct deserialization and mapped candidates:

| canonical failure_code | rows |
|---|---:|
| `F1_RUNTIME` | 152 |
| `F1_COMPILE` | 9 |
| `F0_PARSE` | 13 |
| `None` | 3 |

Unresolved failure codes among failed rows: 0.

### Grammar metadata extraction

Answer: PASS.

C2 preserves the required grammar metadata in both `FrozenCluster1ReplayRow` and `FrozenReplayCandidate`, and replay output construction passes those fields into `replay_control_row(...)` / `Cluster2ReplayRowMetadata`.

Raw artifact grammar metadata:

| field | present | distribution |
|---|---:|---|
| `grammar_active` | 177 / 177 | `True`: 177 |
| `grammar_variant` | 177 / 177 | `task_agnostic`: 177 |
| `grammar_path` | 177 / 177 | `cluster1/grammar/triton_kernel_agnostic.gbnf`: 177 |
| `grammar_sha` | 177 / 177 | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`: 177 |
| `gbnf_parse_valid` | 177 / 177 | `True`: 105, `False`: 72 |
| `semantic_valid` | 177 / 177 | `True`: 49, `False`: 128 |
| `grammar_valid` | 177 / 177 | `True`: 49, `False`: 128 |
| `rejection_layer` | 177 / 177 | `None`: 49, `semantic_validator`: 56, `gbnf_parse`: 72 |
| `stop_reason` | 177 / 177 | `eos_token`: 105, `max_new_tokens`: 72 |

C2 extraction:

- direct C2 complete grammar metadata: 177 / 177
- mapped C2 complete grammar metadata: 177 / 177
- `grammar_valid == (gbnf_parse_valid and semantic_valid)` invariant failures: 0

Required provenance fields observed:

- `model_revision`: 177 / 177, `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `tokenizer_revision`: 177 / 177, `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `xgrammar_version`: 177 / 177, `0.1.33`
- `transformers_version`: 177 / 177, `4.47.1`
- `tokenizers_version`: 177 / 177, `0.21.1`
- `modal_image_sha`: 177 / 177, `unknown`

## 6. Question 3 - missing-row handling

Answer: PASS.

C2 identifies the missing rows through `analyze_replay_grid_coverage(...)` / `replay_coverage_report_for_condition(...)`:

- `matmul/fp32/sample_index=5`
- `matmul/bf16/sample_index=0`
- `matmul/bf16/sample_index=18`

They are all matmul rows.

Coverage report:

- policy: `COVERAGE_WARNING_SKIP_MISSING`
- expected rows: 180
- observed rows: 177
- missing rows: 3
- duplicate rows: 0
- unexpected rows: 0
- invalid rows: 0
- coverage complete: `False`

Manifest-driven mapping behavior:

| kernel_class | dtype | status | mapped candidates |
|---|---:|---|---:|
| elementwise | fp32 | `ok` | 20 |
| elementwise | fp16 | `ok` | 20 |
| elementwise | bf16 | `ok` | 20 |
| matmul | fp32 | `ok_with_coverage_warning` | 19 |
| matmul | fp16 | `ok` | 20 |
| matmul | bf16 | `ok_with_coverage_warning` | 18 |
| reduction | fp32 | `ok` | 20 |
| reduction | fp16 | `ok` | 20 |
| reduction | bf16 | `ok` | 20 |

The G+C schedule preflight path uses the same coverage policy. For task-agnostic `G+C`, `_preflight_paired_generation_schedules(...)` calls `replay_coverage_report_for_condition(...)`, appends the coverage warning when the report is incomplete, and calls `replay_seed_schedule_for_condition(..., allow_incomplete=True)` so only reported missing replay rows are skipped. Malformed duplicate, unexpected, or invalid rows are rejected.

Missing-row behavior classification: `GRACEFUL_SKIP_WITH_WARNING`.

## 7. G+C readiness decision

`C2_REPLAY_READY_WITH_COVERAGE_WARNING`

Reasons:

- C2 deserializes all 177 artifact rows successfully.
- C2 maps all 177 available replay candidates from the selected n=20 artifact.
- C2 extracts source, seed/sample identity, canonical failure code, and grammar metadata for every available replay row.
- C2 explicitly reports the 3 missing matmul rows.
- C2 uses warning-skip behavior for the incomplete task-agnostic G replay grid instead of silently treating it as complete.
- G+C can proceed only with the explicit 177/180 coverage warning and downstream matched-row reporting caveat.

## 8. Required follow-ups

Replay-specific follow-ups only:

1. Keep downstream G+C reporting explicit that task-agnostic G replay coverage is 177/180 and excludes `matmul/fp32/5`, `matmul/bf16/0`, and `matmul/bf16/18`.
2. Ensure any G+C analysis or aggregation consuming this control set retains the coverage warning alongside results so the missing rows are not mistaken for failures or successes.

## 9. Appendix

Commands run:

```bash
rg "replay|frozen|baseline|cluster1|GenerationResult|eval_result_from_generation_result|failure_code|compile_error_type|grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|stop_reason|source|generated_source|generation_seed|sample_index|seed" cluster2 shared cluster1
rg "task_agnostic_g_aligned_pipeline|FROZEN|REPLAY|G\+C|condition.*G\+C|grammar_active|grammar_variant" cluster2 shared cluster1
rg "jsonl|deserialize|from_dict|model_validate|dataclass|read.*rows|load.*artifact|coverage|missing|skip" cluster2 shared cluster1
.venv/bin/python - <<'PY'
# local read-only diagnostic over the artifact, C2 deserializer, C2 manifest mapping, and coverage report
PY
.venv/bin/python - <<'PY'
# local read-only mapped-candidate count diagnostic
PY
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py -q
.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py -q
```

Key output snippets:

```text
VALID_ROWS 177
BAD_JSON_COUNT 0
SOURCE_FIELD source
SOURCE_PRESENT 177 / 177
generation_seed {'present': 177, 'unique': 20, 'examples': [0, 1, 2, 3, 4]}
GRAMMAR_VALID_INVARIANT_FAILURES [] count 0
```

```text
C2_DESERIALIZE
c2_rows 177
c2_rejected 0 []
c2_source_present 177 / 177
c2_sample_index_present 177 / 177
c2_generation_seed_present 177 / 177
c2_failure_code_distribution {None: 3, 'F1_RUNTIME': 152, 'F1_COMPILE': 9, 'F0_PARSE': 13}
c2_failure_codes_unresolved 0
c2_complete_grammar_metadata 177 / 177
c2_grammar_valid_invariant_failures 0
```

```text
c2_coverage {'artifact_id': 'g_task_agnostic_aligned_pipeline_n20_l4', 'condition': 'G', 'replay_coverage_policy': 'COVERAGE_WARNING_SKIP_MISSING', 'replay_expected_rows': 180, 'replay_observed_rows': 177, 'replay_missing_rows': [{'kernel_class': 'matmul', 'dtype': 'fp32', 'sample_index': 5}, {'kernel_class': 'matmul', 'dtype': 'bf16', 'sample_index': 0}, {'kernel_class': 'matmul', 'dtype': 'bf16', 'sample_index': 18}], 'replay_duplicate_rows': [], 'replay_unexpected_rows': [], 'replay_invalid_rows': [], 'replay_coverage_complete': False}
```

```text
MAPPED_CANDIDATES 177
MAPPING_STATUSES {'ok': 7, 'ok_with_coverage_warning': 2}
MAPPED_SOURCE_PRESENT 177 / 177
MAPPED_SEED_PRESENT 177 / 177
MAPPED_FAILURE_CODE_DISTRIBUTION {None: 3, 'F1_RUNTIME': 152, 'F1_COMPILE': 9, 'F0_PARSE': 13}
MAPPED_GRAMMAR_COMPLETE 177 / 177
MAPPED_ARTIFACT_IDS {'g_task_agnostic_aligned_pipeline_n20_l4': 177}
```

Test results:

```text
108 passed in 1.03s
23 passed in 0.03s
```

File paths inspected:

- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
- `cluster2/replay/cluster1_controls.py`
- `cluster2/replay/manifest.py`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/results/dataclass.py`
- `cluster2/results/logger.py`
- `cluster2/constants.py`
- `cluster2/generation/modal_generate_c2.py`
- `cluster2/modal/generation.py`
- `cluster1/results/dataclass.py`
- `cluster1/results/logger.py`
- `shared/eval/adapter_cluster1.py`
- `shared/eval/failure_taxonomy.py`
- `shared/eval/pipeline.py`
- `shared/eval/aggregation.py`
- `cluster2/tests/test_replay_controls.py`
- `cluster2/tests/test_run_cluster2_modal.py`
- `cluster2/tests/test_results_logger.py`
- `shared/tests/test_eval_failure_taxonomy.py`
