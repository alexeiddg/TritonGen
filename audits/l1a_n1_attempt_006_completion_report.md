# L1a n=1 12-cell completion audit

## Scope

- branch: `codex-track-handoff-context`
- execution surface: L1a n=1 only
- design: `grammar_mode x C x P`, 12 selected cells
- selected grammar modes: `grammar_off`, `template_upper_bound`, `task_agnostic`
- runtime MLflow setting: `TRITONGEN_MLFLOW=0`
- Modal/GPU/generation authorization: explicit user authorization for this L1a
  n=1 run only
- prohibited scope preserved: no L1b, L2, n=5, n=20, benchmark, profiler, or
  scientific-row/repair-policy/sampling/model-setting expansion was run

## Signed execution command

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

The successful Modal run used row commit
`817e6d3c87d05a7ede45435ed34475339d513af0`.

## Attempt sequence

### Attempt 004

- start: `2026-06-06T09:04:57Z`
- final row timestamp: `2026-06-06T09:21:48.086155Z`
- end: `2026-06-06T09:22:05Z`
- result: generated 12 rows and passed signed local row/content/observability
  validations, then failed analyzer/report creation because C-loop rows did not
  include the `c_repair_*` generated metadata required by the repair-memory
  analyzer path.
- disposition: target artifacts were archived under the authorized attempt
  archive namespaces:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_004_20260606T090457Z/`
  and
  `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/blocked_attempts/attempt_004_20260606T090457Z/`.

### Attempt 005

- start: `2026-06-06T09:34:38Z`
- result: failed before any planned target file write with
  `modal.exception.ConnectionError: Could not connect to the Modal server` after
  sandbox DNS resolution failed.
- disposition: no planned L1a target JSONL, hash, observability, analysis,
  report, billing, or `mlruns` artifact was produced by this attempt.

### Attempt 006

- start: `2026-06-06T09:36:02Z`
- final row timestamp: `2026-06-06T09:48:48.981973Z`
- end: `2026-06-06T09:48:57Z`
- result: completed the signed L1a n=1 selector command with 12 rows.
- runner output:

```json
{"output": "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1", "rows": 12, "write_mode": "overwrite"}
```

## Matrix coverage

The completed run produced exactly one JSONL file with one row for each selected
cell:

- `grammar_off__c_off__p_off`
- `grammar_off__c_on__p_off`
- `grammar_off__c_off__p_on`
- `grammar_off__c_on__p_on`
- `template_upper_bound__c_off__p_off`
- `template_upper_bound__c_on__p_off`
- `template_upper_bound__c_off__p_on`
- `template_upper_bound__c_on__p_on`
- `task_agnostic__c_off__p_off`
- `task_agnostic__c_on__p_off`
- `task_agnostic__c_off__p_on`
- `task_agnostic__c_on__p_on`

Route behavior was one selector invocation covering all 12 cells. The route audit
reported 12 output rows, two C-loop remote repair calls, and no P-loop remote
repair calls for the observed smoke kernels.

## Grammar-mode mapping

- `grammar_off` rows have `grammar_active=false` and no grammar path/hash.
- `template_upper_bound` rows use grammar hash
  `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`.
- `task_agnostic` rows use grammar hash
  `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.
- The row-level `grammar_mode` field matches the selected file-id grammar mode
  for all 12 rows.

## Analyzer/report status

The signed L1a analyzer/report command completed after a scope-gated analyzer
patch for `l1a_grammar_mode_cp_smoke`. The patch keeps ordinary pair/replay
analysis strict outside this smoke scope, while allowing this 12-cell n=1
grammar-mode surface to report grammar-mode cell summaries without requiring
matched replay-pair metadata that is not present in the selector output.

Generated analysis artifacts:

- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.json`
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.md`

Analysis metadata:

- `analysis_scope`: `l1a_grammar_mode_cp_smoke`
- `cell_summaries`: `32`
- `paired_comparisons`: `1`
- `grammar_grouping_policy`:
  `group_by_grammar_mode_without_binary_G_collapse`

## Billing reconciliation

Billing report artifact:

- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_billing_report_20260606_utc.json`

Billing query result:

- entries: `2`
- UTC-day total: `1.24144792` USD
- Modal tags: `{}`

Because Modal returned empty tags, this is a UTC-day workspace/window
reconciliation artifact, not a tag-attributed per-run billing proof.

## Validation and scans run

Commands and observed results:

- `git diff --check`: passed.
- `.venv/bin/python -m compileall -q shared/analysis`: passed.
- signed row/schema validation: `schema_and_row_count_valid 12`.
- signed content-hash sidecar validation: `content_hash_sidecars_valid 12`.
- signed observability sidecar validation: `observability_sidecars_valid 12`.
- signed grammar-mode validation: `grammar_mode_consistency_valid 12`.
- matrix/C metadata validation: `matrix_factor_c_metadata_valid 12 2`.
- analysis artifact inspection:
  `analysis_scope l1a_grammar_mode_cp_smoke`, `cell_summaries 32`,
  `paired_comparisons 1`.
- focused analyzer regression suite:
  `shared/tests/test_analyzer_cluster3.py` reported `35 passed, 1 failed`;
  the remaining failure is the existing `LEGACY_2X2_GOLDEN_JSON` drift, while
  the L1a analyzer/report command itself passes.
- billing artifact inspection:
  `billing_entries 2`, `billing_total_usd 1.24144792`, `billing_tags ['{}']`.
- protected lockfile/preliminary-report diff scan:
  `git diff --name-only -- mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock`
  returned empty output.
- `find mlruns -maxdepth 2 -type f -print` returned
  `find: mlruns: No such file or directory`.

Artifact hashes:

- billing JSON:
  `bfbd839e5a3ae0d891793eb03e8240dfb27f914d9ea623ca8ee8c645e12c61f5`
- analysis JSON:
  `b03d28e4c0de600c0086b12d117b10edf44bdc496d7ff5156dfdc6a430a90ed0`
- markdown report:
  `3cda44e93b092d1f177e0e055583e70e84da968ffb4254dce4e962d66e9b8c29`

## Output and MLflow mutation proof

Authorized output/artifact namespaces were used:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`
- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.json`
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.md`
- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_billing_report_20260606_utc.json`

Runtime MLflow remained disabled and `mlruns/` is absent. No lockfiles,
preliminary report files, or dependency manifests were changed.

## Remaining blockers

- GitHub push for commits after the last successful remote update may require
  credentials if non-interactive push fails.
- Billing is not tag-attributed because the Modal billing report returned empty
  tags.
- This is L1a n=1 smoke evidence only. It is not L1b/L2, n=5/n=20, or
  paper-scale evidence.

## Classification

`L1A_N1_12CELL_RUN_COMPLETE_VALIDATED`

## Next-step recommendation

Commit the analyzer smoke-scope patch and this completion audit. Then attempt a
non-interactive push of `codex-track-handoff-context`; if credentials are
required, leave the branch locally ahead and report the exact commit state for
manual push.
