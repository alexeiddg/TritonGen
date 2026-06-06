# L1b n=5 12-cell completion audit

## Scope

- branch: `codex-track-handoff-context`
- pre-run selector support commit:
  `a52d64a368da896e9c24d7b346d167b890c1f522`
- execution surface: L1b n=5 only
- design: `grammar_mode x C x P`, 12 selected cells
- selected grammar modes: `grammar_off`, `template_upper_bound`,
  `task_agnostic`
- runtime MLflow setting: `TRITONGEN_MLFLOW=0`
- output namespace:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- observability namespace:
  `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- analysis artifact:
  `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.json`
- report artifact:
  `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.md`
- billing artifact:
  `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_billing_report_20260606_utc.json`
- classification: `L1B_N5_12CELL_RUN_COMPLETE_VALIDATED`

This audit records one authorized L1b n=5 execution. It does not authorize or
claim L2, n=20, paper-scale evidence, performance profiling, speedup,
cost-per-success, pass@k cost, ROI, economic lift, or benchmark conclusions.

## Signed Command Run

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1B_N5_AUTHORIZATION_GOAL_20260606 --overwrite
```

Invocation count: `1`

Retry count: `0`

Resume count: `0`

## Runner Result

The runner completed successfully:

```text
{"output": "outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5", "rows": 60, "write_mode": "overwrite"}
```

The route audit reported:

- planned cells: `12`
- rows written: `60`
- generation calls: `70`
- correctness calls: `70`
- C-loop remote repair calls: `2`
- P-loop remote repair calls: `2`

## Matrix Coverage

The completed run produced exactly 12 JSONL files with five rows per selected
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

Observed row counts:

- total rows: `60`
- JSONL files: `12`
- rows per cell: `5`
- grammar-mode counts:
  `grammar_off=20`, `template_upper_bound=20`, `task_agnostic=20`
- condition counts:
  `none=5`, `C=5`, `P=5`, `C+P=5`, `G=10`, `G+C=10`,
  `G+P=10`, `G+C+P=10`

## Grammar-Mode Mapping

- `grammar_off` rows have `grammar_active=false`, no grammar path, and no
  grammar SHA.
- `template_upper_bound` rows use grammar hash
  `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`.
- `task_agnostic` rows use grammar hash
  `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.
- Row-level `grammar_mode` matches the selected file-id grammar mode for all
  60 rows.
- Generated metadata `grammar_mode` matches the selected file-id grammar mode
  for all 60 rows.

## No-P Control Proof

The six no-P control cells produced 30 rows total. All 30 no-P rows have:

- `p_repair_attempted=false`
- generated metadata `p_repair_attempted=false`

Observed P repair activity was limited to P-enabled cells:

- P repair rows: `2`
- P repairs in no-P controls: `0`

## Analyzer and Report Status

Generated analysis:

- `analysis_scope`: `l1b_grammar_mode_cp_dev`
- `scale_tiers`: `["development"]`
- `reportable`: `false`
- `cell_summaries`: `32`
- `paired_comparisons`: `0`
- table 1 cell summaries: `32`
- table 2 paired comparisons: `0`
- table 3 factorial terms: `7`
- three-way interaction reportable: `false`
- three-way reason: `requires_reportable_primary_paper_scale_output`

The report title is:

```text
L1b development-scale 2^3 factorial diagnostic analysis
```

The report explicitly states that the output is not paper-scale or reportable
paper evidence and that three-way interaction fields are diagnostic only.

## Analyzer Patch Boundary

The analyzer/report patch required for this valid L1b selector output is
audited in:

```text
audits/l1b_n5_analyzer_dev_scope_patch_report.md
```

The patch only handles missing paired replay metadata for explicit non-paper
grammar-mode selector scopes. It keeps ordinary analyzer strictness intact and
does not alter correctness, repair, row schema, pass/fail, grammar semantics,
or reportability boundaries.

## Billing Reconciliation

Billing query command:

```text
.venv/bin/python -m modal billing report --start 2026-06-06 --end 2026-06-07 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

The Modal billing query succeeded and returned three UTC-day entries. The entry
matching the L1b run hour is:

```text
Interval Start: 2026-06-06T18:00:00
Cost: 2.13879534
Tags: {}
```

Because Modal returned empty tags, the billing artifact is a UTC-window
workspace billing artifact, not a tag-attributed per-run billing proof. No
cost-per-success, pass@k cost, ROI, economic-lift, speedup, or benchmark
claim is made.

The full UTC-day billing artifact includes the earlier L1a 09:00 UTC entries
and the L1b 18:00 UTC entry. The L1b window entry is recorded separately above
to avoid treating the full-day report as a per-run tag attribution.

## Validation and Scans Run

Disk validation:

```text
schema_and_row_count_valid 60
jsonl_files_valid 12
rows_per_cell_valid [5]
content_hash_sidecars_valid 12
observability_sidecars_valid 12
observability_event_counts {'row_completed': 60, 'row_started': 60, 'run_completed': 12, 'run_started': 12, 'stage_completed': 184, 'stage_started': 184}
grammar_mode_counts {'grammar_off': 20, 'task_agnostic': 20, 'template_upper_bound': 20}
condition_counts {'C': 5, 'C+P': 5, 'G': 10, 'G+C': 10, 'G+C+P': 10, 'G+P': 10, 'P': 5, 'none': 5}
no_p_controls_valid 30 p_repairs_in_p_off 0
repair_counts {'c_loop_rows': 2, 'p_repair_rows': 2}
functional_success_rows 20
analysis_valid l1b_grammar_mode_cp_dev False 0
billing_window_entry_usd 2.13879534
mlruns_absent_valid
```

Focused regression bundle:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py shared/tests/test_analyzer_cluster3.py shared/tests/test_reporting_tables.py shared/tests/test_observability_billing_modal_collection.py -q
```

Result:

```text
229 passed
```

Compilation:

```text
.venv/bin/python -m compileall -q cluster3 shared/analysis shared/eval/reporting shared/observability
```

Result: passed.

Whitespace:

```text
git diff --check
```

Result: passed.

Protected-surface diff scan:

```text
git diff --name-only -- mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result: empty output.

MLflow check:

```text
find mlruns -maxdepth 2 -type f -print
```

Result:

```text
find: mlruns: No such file or directory
```

## Artifact Hashes

- output namespace aggregate SHA-256:
  `b8ae97002aace9f0b0a1b718bae2740d7d106e8c5ece935251dec435fb6e6561`
- observability namespace aggregate SHA-256:
  `93df5d8c7ed0428a39552507f8c6d14eef4cbdddfcc706cfa71d27f41f9c9800`
- analysis JSON SHA-256:
  `37d562500e558c9d19f109a59fb2bff285bfdd617cc70d576f7858f7fd9502a0`
- markdown report SHA-256:
  `3cbe2a03bc758257f71dd7668b38fd67a40f13f923f3449e538f95d203ad900e`
- billing JSON SHA-256:
  `de63272553a534917212cab1e399e4d51b66fe03a40e43cf4aec1dcd647f4986`

## Output and MLflow Mutation Proof

Authorized namespaces used:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5`
- `artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.json`
- `artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.md`
- `artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_billing_report_20260606_utc.json`

Runtime MLflow remained disabled and `mlruns/` is absent. No dependency
manifest, lockfile, or preliminary-report file changed.

## Remaining Blockers

- This is L1b n=5 development-scale evidence only.
- It is not L2, n=20, paper-scale, or reportable paper evidence.
- Billing attribution is limited because Modal returned empty tags.
- MLflow grammar-mode indexing remains deferred because runtime MLflow was
  explicitly disabled for this run.
- Any L2/n=20/paper-scale execution requires a separate signed packet.

## Classification

`L1B_N5_12CELL_RUN_COMPLETE_VALIDATED`

## Next-Step Recommendation

Commit this audit, the narrow analyzer/reporting patch, the L1b output rows,
content-hash sidecars, observability sidecars, analysis/report artifacts, and
billing artifact. Then push `codex-track-handoff-context`. Do not proceed to
L2, n=20, paper-scale, benchmarking, profiler, speedup, or economic claims
without a separate signed authorization packet.
