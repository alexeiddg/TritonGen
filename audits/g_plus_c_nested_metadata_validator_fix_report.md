# G+C Nested Metadata Validator Fix Report

## 1. Executive summary

Root cause: the G+C n=1 smoke was classified `G_PLUS_C_N1_SMOKE_INCONCLUSIVE` because the audit check expected flattened top-level grammar/provenance fields and old explicit Level 0 fields. The current Cluster 2 row schema stores grammar/provenance metadata under `generated_metadata`, while result/eval fields such as `grammar_active`, `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, `failure_code`, `trace_summary`, and `repair_trace` are top-level.

Fix status: fixed in a schema-aware Cluster 2 validation helper. The existing artifact `outputs/cluster2/g_plus_c_smoke_n1.jsonl` validates locally without rerunning Modal, generation, GPU jobs, or artifact rewrites.

Final classification: `FIX_VERIFIED`. The existing smoke reclassifies to `G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS` because the validator mismatch is resolved and the only remaining smoke-level warning is the known 177/180 replay coverage caveat.

## 2. Existing artifact schema inspection

Artifact: `outputs/cluster2/g_plus_c_smoke_n1.jsonl`

Rows: 3

Top-level keys:

`attempt_index`, `base_seed`, `compile_success`, `condition`, `dtype`, `eval_set_success`, `failure_code`, `functional_success`, `generated_metadata`, `generation_mode`, `grammar_active`, `kernel_class`, `kernel_name`, `repair_set_success`, `repair_trace`, `replay_metadata`, `source_class`, `source_hash`, `trace_summary`

`generated_metadata` keys:

`c2_generation_hashes`, `gbnf_parse_valid`, `generation_metadata_schema_version`, `generation_seed`, `grammar_claim_scope`, `grammar_path`, `grammar_sha`, `grammar_valid`, `grammar_variant`, `max_new_tokens`, `modal_image_provenance_components`, `modal_image_provenance_sha256`, `modal_image_sha`, `model_id`, `model_revision`, `prompt_sha256`, `rejection_layer`, `replay_base_seed`, `replay_control_condition`, `replay_generation_seed`, `replay_pair_id`, `semantic_valid`, `stop_reason`, `temperature`, `tokenizer_revision`, `tokenizers_version`, `transformers_version`, `xgrammar_version`

Required field locations:

| field | location | observed |
|---|---|---|
| `condition` | top level | `G+C` for 3/3 |
| `generation_mode` | top level | `new_c2_generation_with_G_adapter` for 3/3 |
| `grammar_active` | top level in current C2 final row schema | `true` for 3/3 |
| `grammar_variant` | `generated_metadata` | `task_agnostic` for 3/3 |
| `grammar_path` | `generated_metadata` | `cluster1/grammar/triton_kernel_agnostic.gbnf` for 3/3 |
| `grammar_sha` | `generated_metadata` | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` for 3/3 |
| `model_revision` | `generated_metadata` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` for 3/3 |
| `tokenizer_revision` | `generated_metadata` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` for 3/3 |
| `modal_image_sha` | `generated_metadata` | `im-tU3VQyAbFvrusOxtlwspCN` for 3/3 |
| `compile_success` | top level | `{true: 1, false: 2}` |
| `functional_success` | top level | `false` for 3/3 |
| `failure_code` | top level | `F2_NUMERIC_NAN: 1`, `F1_RUNTIME: 2` |
| eval ladder evidence | top-level `trace_summary` and `repair_trace`, plus result booleans | present for 3/3 |

## 3. Stale validator root cause

The stale check was represented in `audits/cluster2_g_plus_c_smoke_n1_report.md`, not as a checked-in reusable validator function. The old audit assumptions were:

- Sections 4 and 8 treated `grammar_variant`, `grammar_path`, `grammar_sha`, `model_revision`, `tokenizer_revision`, `transformers_version`, `tokenizers_version`, and `modal_image_sha` as required top-level fields.
- Section 6 treated missing top-level `level0_*`, `parse_success`, and `signature_success` as inconclusive even though current C2 result evidence is stored through `failure_code`, `trace_summary`, and `repair_trace`.

That conflicted with the current schema defined in `cluster2/results/dataclass.py`, `cluster2/results/logger.py`, and `cluster2/modal/schemas.py`, where final generated rows carry a nested `Cluster2GeneratedRowMetadata` object for generation/provenance/grammar evidence and top-level booleans/result fields for eval outcomes.

## 4. Fix implementation

Added `cluster2/validation/generated_metadata.py`.

Key helpers:

- `get_generated_metadata(row)` returns current-schema `row["generated_metadata"]` when dict-like, else `{}`.
- `get_field(row, field_name, allow_legacy_top_level_metadata=False)` reads current top-level fields from the row and generated/provenance/grammar fields from `generated_metadata`.
- `validate_g_plus_c_smoke_jsonl(path, expected_rows=...)` loads raw JSONL and validates without hiding missing fields behind legacy dataclass backfills.
- `validate_g_plus_c_smoke_rows(...)` validates raw mappings or `Cluster2EvalRow` objects.

Legacy fallback:

- Strict current validation requires `generated_metadata`.
- Flat legacy metadata is supported only when `allow_legacy_top_level_metadata=True`; the helper reconstructs a current-schema payload for `Cluster2EvalRow.from_dict`.

No row schema, G+C generation behavior, grammar routing, repair-loop semantics, artifact, output, or hash record was changed.

## 5. Strict validation semantics after fix

The new G+C smoke validator enforces:

- `condition == "G+C"`.
- top-level `generation_mode == "new_c2_generation_with_G_adapter"`.
- top-level `grammar_active is True`.
- `generated_metadata.grammar_variant == "task_agnostic"`.
- `generated_metadata.grammar_path` contains `cluster1/grammar/triton_kernel_agnostic.gbnf`.
- `generated_metadata.grammar_sha` matches the current task-agnostic grammar SHA `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.
- `generated_metadata.model_revision` and `generated_metadata.tokenizer_revision` are non-empty, non-unknown immutable Hub revisions.
- `generated_metadata.modal_image_sha` is non-empty, non-unknown, and a stable Modal image identifier.
- `generated_metadata.generation_metadata_schema_version >= 1`.
- grammar validation booleans are present.
- top-level `compile_success` is present and boolean.
- top-level `functional_success`, `repair_set_success`, and `eval_set_success` are boolean.
- `failure_code` is canonical or null only when successful.
- `trace_summary` and non-empty `repair_trace` provide current-schema eval ladder evidence.

Confirmed by tests:

- `tokenizer_revision="unknown"` fails.
- `modal_image_sha="unknown"` fails.
- `grammar_variant="template_upper_bound"` fails.
- `grammar_active=False` fails.
- missing top-level `compile_success` fails.
- nested valid G+C rows pass.

## 6. Tests added/updated

Added `cluster2/tests/test_generated_metadata_validation.py`.

Covered cases:

- nested G+C `generated_metadata` passes.
- missing `generated_metadata` fails under strict current validation.
- unknown nested `tokenizer_revision` fails.
- unknown nested `modal_image_sha` fails.
- wrong nested `grammar_variant` fails.
- top-level `grammar_active=False` fails for G+C.
- missing top-level `compile_success` fails.
- nested `generated_metadata.compile_success` does not satisfy the required top-level `compile_success` field.
- legacy flat metadata validates only when the explicit legacy fallback option is enabled.
- C nested generated metadata still parses and passes the existing generated metadata gate.

## 7. Validation results

Commands run with `.venv/bin/python`:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
...
PY
```

Outcome: passed. Artifact inspection showed 3 rows, nested `generated_metadata`, top-level result fields, `task_agnostic` grammar metadata, non-unknown tokenizer/model/image provenance, and present `compile_success`.

```bash
.venv/bin/python - <<'PY'
from cluster2.validation.generated_metadata import validate_g_plus_c_smoke_jsonl
result = validate_g_plus_c_smoke_jsonl(
    'outputs/cluster2/g_plus_c_smoke_n1.jsonl',
    expected_rows=3,
)
print('g_plus_c_smoke_validation', 'PASS', len(result.rows))
PY
```

Outcome: `g_plus_c_smoke_validation PASS 3`.

```bash
.venv/bin/python -m pytest cluster2/tests/test_generated_metadata_validation.py -q
```

Outcome: `10 passed`.

```bash
.venv/bin/python -m pytest cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py cluster2/tests/test_run_cluster2_modal.py -q
```

Outcome: `133 passed`.

```bash
.venv/bin/python -m pytest cluster2/tests -k "validate or validation or strict" -q
```

Outcome: `20 passed, 383 deselected`.

```bash
.venv/bin/python -m pytest cluster2/tests shared/tests -k "metadata or result or logger or validation or g_plus_c" -q
```

Outcome: `188 passed, 739 deselected`.

```bash
.venv/bin/python -m pytest cluster2/tests -k "g_plus_c or generated_metadata or nested or smoke or metadata or validator" -q
```

Outcome: 1 unrelated pre-existing hash-gate failure, `93 passed, 308 deselected`. The failure was `cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head[shared/modal_harness/smoke.py]`, where the expected phase-minus-one hash was `03848df1d3196377a8bdaa363f5b7dd47f59cabcafd7f4011091ac933daa9e16` and the current file hash was `4c999a29a1e966635e186c16d211fe07a36ebd132e8ba47b150eaebab2691e30`. This report did not modify `shared/modal_harness/smoke.py` and did not re-record hashes.

Additional isolating command:

```bash
.venv/bin/python -m pytest cluster2/tests -k "(g_plus_c or generated_metadata or nested or smoke or metadata or validator) and not test_shared_modal_files_match_phase_minus1_git_head" -q
```

Outcome: `93 passed, 309 deselected`.

```bash
git diff --check
```

Outcome: passed.

## 8. Updated G+C smoke classification

`G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS`

The existing G+C n=1 smoke artifact now passes strict current-schema validation. The warning is the already-known 177/180 task-agnostic G replay coverage caveat surfaced by the prior smoke report. This is a warning for proceeding to paper-scale matched analysis, not evidence that the G+C generated row schema or grammar/provenance metadata is invalid.

## 9. Next recommendation

`HOLD_FOR_REPLAY_COVERAGE_DECISION`

The validator/schema mismatch is fixed. The next blocker before G+C n=20 is the existing replay coverage decision for the three missing task-agnostic G replay rows, not the nested metadata schema.
