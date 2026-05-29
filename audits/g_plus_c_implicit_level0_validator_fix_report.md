# G+C Implicit Level 0 Validator Fix Report

## 1. Executive Summary

Root cause: the original G+C smoke classification treated missing top-level `level0_*`, `parse_success`, and `signature_success` fields as inconclusive even though the current Cluster 2 schema represents Level 0 status implicitly through canonical `failure_code` and downstream evaluation fields.

Fix status: fixed in the schema-aware G+C smoke validator. The validator now accepts implicit Level 0 evidence while preserving canonical failure-code and metadata/provenance strictness.

Updated smoke classification: `G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS`.

## 2. Existing Schema Evidence

Artifact inspected: `outputs/cluster2/g_plus_c_smoke_n1.jsonl`

Row count: 3.

Top-level fields present:

`attempt_index`, `base_seed`, `compile_success`, `condition`, `dtype`, `eval_set_success`, `failure_code`, `functional_success`, `generated_metadata`, `generation_mode`, `grammar_active`, `kernel_class`, `kernel_name`, `repair_set_success`, `repair_trace`, `replay_metadata`, `source_class`, `source_hash`, `trace_summary`

`generated_metadata` fields present:

`c2_generation_hashes`, `gbnf_parse_valid`, `generation_metadata_schema_version`, `generation_seed`, `grammar_claim_scope`, `grammar_path`, `grammar_sha`, `grammar_valid`, `grammar_variant`, `max_new_tokens`, `modal_image_provenance_components`, `modal_image_provenance_sha256`, `modal_image_sha`, `model_id`, `model_revision`, `prompt_sha256`, `rejection_layer`, `replay_base_seed`, `replay_control_condition`, `replay_generation_seed`, `replay_pair_id`, `semantic_valid`, `stop_reason`, `temperature`, `tokenizer_revision`, `tokenizers_version`, `transformers_version`, `xgrammar_version`

Observed terminal evidence:

| Row | `failure_code` | `compile_success` | `functional_success` | Explicit Level 0 fields |
| --- | --- | --- | --- | --- |
| 1 | `F2_NUMERIC_NAN` | `true` | `false` | absent |
| 2 | `F1_RUNTIME` | `false` | `false` | absent |
| 3 | `F1_RUNTIME` | `false` | `false` | absent |

Why Level 0 is implicit: the F1/F2 failure codes prove the row moved past parse/signature. Row 1 also has `compile_success=true`, which is only reachable after Level 0 passed. The schema does not need a persisted top-level `level0_success=true` field for these rows.

## 3. Validator Root Cause

The stale assumption was recorded in `audits/cluster2_g_plus_c_smoke_n1_report.md`, especially Section 6, which classified the smoke as inconclusive because top-level `level0_*`, `parse_success`, and `signature_success` fields were absent.

The checked-in schema-aware validator lived in `cluster2/validation/generated_metadata.py`, but it did not yet expose a reusable current-schema Level 0 evidence rule. This left the validator/reporting contract ambiguous for implicit Level 0 evidence.

## 4. Fix Implementation

Changed files:

- `cluster2/validation/generated_metadata.py`
- `cluster2/validation/__init__.py`
- `cluster2/tests/test_generated_metadata_validation.py`

Implemented `has_level0_evidence(row)` and `level0_passed(row)` in `cluster2/validation/generated_metadata.py`.

Implicit Level 0 evidence rule:

- `F0_*` is valid Level 0 evidence and means Level 0 failed.
- Explicit `level0_success`, `level0_result`, `parse_success`, `signature_success`, or `level0_failure_code` is accepted as evidence when present.
- `F1_*`, `F2_*`, and `F3_*` imply Level 0 passed.
- Presence of top-level `compile_success` implies Level 0 was reached/passed unless the row has an `F0_*` failure.
- `failure_code=None` can imply success only with downstream success evidence such as `compile_success` or `functional_success`.
- Missing `failure_code`, `compile_success`, and `functional_success` remains invalid/inconclusive.

Strict behavior preserved:

- Noncanonical `failure_code` still fails.
- Missing top-level `failure_code` now fails explicitly.
- `failure_code=None` is accepted only for successful rows.
- Top-level `compile_success` remains required for the G+C smoke validator.
- Nested `generated_metadata.compile_success` does not replace top-level `compile_success`.
- Current G+C metadata/provenance checks are unchanged: `condition`, `generation_mode`, `grammar_active`, task-agnostic grammar metadata, immutable model/tokenizer revisions, stable `modal_image_sha`, and metadata schema version remain strict.
- Explicit Level 0 evidence fields are treated as validator-only compatibility evidence and stripped before constructing the current `Cluster2EvalRow`, so the current row schema is not migrated.

## 5. Tests Added/Updated

Added focused tests in `cluster2/tests/test_generated_metadata_validation.py`:

- `test_g_plus_c_explicit_level0_success_row_passes`
- `test_g_plus_c_implicit_level0_success_via_compile_success_passes`
- `test_g_plus_c_implicit_level0_success_via_f1_failure_passes`
- `test_g_plus_c_explicit_f0_failure_is_evidence_not_success`
- `test_g_plus_c_missing_all_level0_evidence_fails`
- `test_existing_g_plus_c_smoke_artifact_validates`

Existing metadata/provenance tests remain in place for nested `generated_metadata`, unknown tokenizer/image provenance rejection, grammar variant enforcement, grammar activity, missing top-level `compile_success`, and legacy flat metadata compatibility.

## 6. Validation Results

Artifact validation:

```bash
.venv/bin/python - <<'PY'
from cluster2.validation.generated_metadata import validate_g_plus_c_smoke_jsonl

result = validate_g_plus_c_smoke_jsonl(
    'outputs/cluster2/g_plus_c_smoke_n1.jsonl',
    expected_rows=3,
)
print('rows', len(result.rows))
print('warnings', list(result.warnings))
print('failure_codes', [row.failure_code for row in result.rows])
print('compile_success', [row.compile_success for row in result.rows])
PY
```

Result: passed.

Output:

```text
rows 3
warnings []
failure_codes ['F2_NUMERIC_NAN', 'F1_RUNTIME', 'F1_RUNTIME']
compile_success [True, False, False]
```

Focused validator tests:

```bash
.venv/bin/python -m pytest cluster2/tests/test_generated_metadata_validation.py -q
```

Result: passed, `16 passed`.

Requested focused selection:

```bash
.venv/bin/python -m pytest cluster2/tests -k "level0 or implicit or smoke or generated_metadata or g_plus_c or validator" -q
```

Result: failed only on the pre-existing Phase -1 hash sentinel `test_shared_modal_files_match_phase_minus1_git_head[shared/modal_harness/smoke.py]`; validator-related tests passed. Summary: `1 failed, 74 passed, 334 deselected`.

Focused selection excluding that unrelated sentinel:

```bash
.venv/bin/python -m pytest cluster2/tests -k "(level0 or implicit or smoke or generated_metadata or g_plus_c or validator) and not test_shared_modal_files_match_phase_minus1_git_head" -q
```

Result: passed, `74 passed, 335 deselected`.

Result/schema regression:

```bash
.venv/bin/python -m pytest cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py cluster2/tests/test_run_cluster2_modal.py -q
```

Result: passed, `133 passed`.

Broad focused regression:

```bash
.venv/bin/python -m pytest cluster2/tests shared/tests -k "metadata or validation or failure_code or level0 or g_plus_c" -q
```

Result: passed, `218 passed, 716 deselected`.

## 7. Existing Smoke Reclassification

`G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS`

The validator/schema mismatch is resolved. The smoke artifact validates under the current schema without adding fake Level 0 fields and without modifying the JSONL artifact.

Warnings:

- The known task-agnostic G replay coverage warning remains: 177/180 replay rows are available, with three missing matmul replay rows.
- The requested focused pytest selection still includes an unrelated Phase -1 hash sentinel for `shared/modal_harness/smoke.py`; no hash was re-recorded.

## 8. Next Recommendation

`HOLD_FOR_REPLAY_COVERAGE_DECISION`

Do not run G+C n=20 until the existing 177/180 task-agnostic G replay coverage decision is resolved or explicitly accepted for covered-row analysis.
