# C2 G Replay Manifest and Metadata Fix Report

## 1. Executive Summary

The G+C replay readiness blocker is fixed for local C2 replay/configuration.

Selected coverage policy: `COVERAGE_WARNING_SKIP_MISSING`.

Final classification: `FIX_VERIFIED`.

The task-agnostic G n=20 artifact is now registered in the active C2 frozen replay manifest. C2 replay loading preserves source, seed/sample identity, canonical `failure_code`, legacy `compile_error_type`, `compile_success`, grammar metadata, and available provenance metadata. The known 177/180 coverage gap is explicit and reported before matched-row G+C scheduling; the three missing rows are skipped, not fabricated and not counted as model failures.

Follow-up review fixes are included: skip-policy scheduling now rejects seed-schedule holes that are not present in the coverage report, and the top-level manifest `coverage_assessment` now reflects the selected n=20 task-agnostic artifact instead of stale n=5 failures.

## 2. Root Cause

The active C2 replay manifest still selected the old task-agnostic G n=5 development artifact, so C2 could not safely identify the new task-agnostic G n=20 replay source for future G+C.

C2 replay candidate/result metadata preserved only a small subset of Cluster 1 replay row metadata. Critical grammar evidence was not carried through replay/canonicalization: `grammar_active`, `grammar_variant`, `grammar_path`, `grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, and `stop_reason`.

The new G artifact has 177 observed rows against an intended 180-row grid. That gap was not represented as an explicit C2 coverage policy, so a future G+C path could either block unclearly or silently treat incomplete coverage as complete.

## 3. Manifest/Config Update

Modified `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`.

Registered artifact path:

`outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

Registered artifact id:

`g_task_agnostic_aligned_pipeline_n20_l4`

Entry summary:

- condition/source condition: `G`
- grammar_variant: `task_agnostic`
- expected_n: `20`
- intended_rows: `180`
- observed_rows: `177`
- coverage_policy: `COVERAGE_WARNING_SKIP_MISSING`
- artifact sha256: `59e6026d18db58fae0472591f3b924f83c837e99b0a543b131efe94a9e37751a`
- metadata sidecar sha256: `a8af73753916f2c5cff2dd35942762890bfc9f8d7d6ab8ec8517c89e18e000b0`

The frozen none baseline entry remains intact:

`outputs/cluster1/baseline_repaired_l4_n20.jsonl`

The existing template-upper-bound G replay entry remains intact:

`outputs/cluster1/final_g_l4_n20.jsonl`

The phase-minus1 manifest hash was not re-recorded. The boundary test now allows only the approved semantic drift: the original none/template/task-agnostic development artifact path/hash summaries must remain unchanged, the template selected-control ids must remain unchanged, and the new task-agnostic G n=20 registration/status must match the exact recorded 177/180 skip policy.

## 4. Replay Row Preservation

Source extraction:

All 177 real G replay rows deserialize with non-empty `source`.

Seed/sample identity:

Each row exposes a logical identity from `generation_seed` as `sample_index`/`base_seed`, plus `kernel_class` and `dtype`.

Failure metadata:

`failure_code` is preserved as the canonical field. `compile_error_type` is retained only as `legacy_compile_error_type`. `compile_success` is preserved in replay metadata.

Grammar metadata:

Replay candidates and C2 replay result metadata now preserve:

`grammar_active`, `grammar_variant`, `grammar_path`, `grammar_sha`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, and `stop_reason`.

Provenance metadata:

When present, replay rows also preserve:

`xgrammar_version`, `transformers_version`, `tokenizers_version`, `model_revision`, `tokenizer_revision`, `modal_image_sha`, `modal_image_provenance_sha256`, and `modal_image_provenance_components`.

The invariant `grammar_valid == (gbnf_parse_valid and semantic_valid)` is enforced in replay-result metadata.

## 5. Coverage Policy

Expected rows: `180`

Observed rows: `177`

Selected policy: `COVERAGE_WARNING_SKIP_MISSING`

Missing logical rows:

- `kernel_class=matmul`, `dtype=fp32`, `sample_index=5`
- `kernel_class=matmul`, `dtype=bf16`, `sample_index=0`
- `kernel_class=matmul`, `dtype=bf16`, `sample_index=18`

Before G+C scheduling starts, C2 reconstructs the replay grid and rejects malformed replay coverage. Direct C2 replay mapping applies the same guard. `COVERAGE_WARNING_SKIP_MISSING` permits missing rows only; duplicate logical identities, unexpected extra identities, or invalid identities that cannot reconstruct `kernel_class`/`dtype`/sample identity raise before scheduling or replay mapping.

For the known 177-row artifact, C2 emits a coverage warning object with:

- `replay_expected_rows: 180`
- `replay_observed_rows: 177`
- `replay_missing_rows: [...]`
- `replay_duplicate_rows: []`
- `replay_unexpected_rows: []`
- `replay_invalid_rows: []`
- `replay_coverage_policy: COVERAGE_WARNING_SKIP_MISSING`
- `replay_coverage_complete: false`

G+C scheduling uses only matched replay rows. Missing rows are skipped, not imputed, and not counted as model failures.

The seed schedule is also cross-checked against the coverage report. Under `COVERAGE_WARNING_SKIP_MISSING`, C2 rejects any schedule identity gap unless that exact `(kernel_class, dtype, sample_index)` appears in `replay_missing_rows`.

## 6. Tests Added/Updated

Manifest registration:

- Updated `cluster2/tests/test_replay_manifest.py` to assert the new G n=20 artifact path/id, skip policy, 177/180 counts, and unchanged none baseline selection.

Replay deserialization:

- Added real-artifact deserialization coverage in `cluster2/tests/test_replay_controls.py`, asserting 177 rows and 0 schema rejections.

Grammar metadata preservation:

- Added assertions over all 177 real replay rows and C2 replay result metadata.

Missing-row detection:

- Added 180-grid reconstruction tests that detect the three missing matmul identities, duplicates, unexpected rows, and invalid row identities.

Coverage-policy behavior:

- Added matched-row skip tests for replay mapping and G+C preflight schedule construction.
- Added G+C preflight rejection tests for duplicate, unexpected, and invalid replay-grid identities under the skip policy.
- Added direct replay-mapping rejection tests for duplicate, unexpected, and invalid replay-grid identities under the skip policy.
- Added manifest accessor, direct replay-mapping, and G+C preflight tests that reject seed-schedule holes not reported by coverage.
- Added manifest coverage-assessment assertions to prevent stale n=5 task-agnostic assessment data from contradicting the selected n=20 artifact.

Frozen none replay regression:

- Existing none replay mapping tests remain passing.
- Manifest tests assert `none_baseline_n20_l4` still points to `outputs/cluster1/baseline_repaired_l4_n20.jsonl`.
- Boundary tests now pin the unchanged none/template artifact path/hash summaries while allowing only the exact task-agnostic G n=20 manifest registration.

## 7. Validation Results

All commands used `.venv/bin/python`.

- `.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py -q`
  PASS: 29 passed.

- `.venv/bin/python -m pytest cluster2/tests/test_replay_manifest.py -q`
  PASS: 13 passed.

- `.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py -q`
  PASS: 43 passed.

- `.venv/bin/python -m pytest cluster2/tests/test_results_logger.py -q`
  PASS: 36 passed.

- `.venv/bin/python -m pytest cluster2/tests -k "replay or manifest or coverage or grammar_metadata or task_agnostic_g or missing" -q`
  PASS: 85 passed, 290 deselected.

- `.venv/bin/python -m pytest shared/tests/test_eval_failure_taxonomy.py -q`
  PASS: 23 passed.

- Artifact read diagnostic using `.venv/bin/python - <<'PY' ... PY`
  PASS: rows `177`; by-cell counts show `matmul/fp32=19`, `matmul/bf16=18`, all other cells `20`.

- `.venv/bin/python -m pytest cluster2/tests shared/tests -k "replay or result or failure_code or metadata or manifest or coverage" -q`
  PASS: 285 passed, 609 deselected.

- `.venv/bin/python -m json.tool cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
  PASS.

- `git diff --check`
  PASS.

- `.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py::test_frozen_cluster1_manifest_hash_matches_phase_minus1 -q`
  PASS: 1 passed.

- `.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py::test_generated_conditions_route_to_generated_path -q`
  PASS: 2 passed.

- `git diff -- outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl outputs/cluster1/baseline_repaired_l4_n20.jsonl`
  PASS: no diff.

## 8. Remaining Risks

Local replay risk:

Low. The real artifact deserializes locally with 0 schema rejections and explicit coverage reporting.

G+C smoke risk:

Not exercised, by request. No G+C, Modal, GPU, or generation command was run.

177/180 coverage reporting risk:

Low for local C2 preflight/result metadata. The report object carries expected, observed, missing rows, duplicates, unexpected rows, invalid rows, policy, and completion status.

Future rerun/full-coverage risk:

The artifact remains incomplete. A future full-coverage task-agnostic G artifact would still be needed to remove the skip warning and claim 180/180 coverage.

## 9. Next Recommendation

`RUN_G_PLUS_C_DRY_REPLAY_ONLY`

Do this only as a replay/scheduling dry run that confirms G+C would enumerate exactly 177 matched replay identities and report the same 3 missing matmul identities before any actual generation/evaluation path is enabled.
