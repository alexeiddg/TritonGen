# L1a analyzer patch and golden drift audit

## Executive summary

The L1a n=1 12-cell run remains validated as
`L1A_N1_12CELL_RUN_COMPLETE_VALIDATED`, but the pre-scale audit found one
analyzer boundary issue that needed a narrow fix before L1b n=5 planning could
be considered safe.

The `LEGACY_2X2_GOLDEN_JSON` failure was stale expected output caused by
intentional analyzer output expansion for metric registry, outcome-family,
provenance, and repair-history metadata. The production 2x2 analyzer behavior
was not wrong. The golden and its reduced contract key lists were refreshed.

The audit also found that full eight-cell smoke analyses could mark nested
three-way interaction fields as reportable merely because all collapsed
G/C/P conditions were populated, even when the top-level analyzer output was
`reportable: false`. `shared/analysis/factorial.py` now gates three-way
interaction reportability on the same paper-scale/reportable predicate as the
top-level output. A regression test proves L1a smoke output cannot promote
three-way interaction diagnostics into reportable paper-scale claims.

## L1a success evidence checked

- Required local success commit checked: `61fa0ac Validate L1a n1 12-cell completion`.
- Preserved artifact commit checked: `1367cdb Preserve L1a n1 generated artifacts`.
- Signed row/schema validation rerun: `schema_and_row_count_valid 12`.
- Content-hash sidecar validation rerun: `content_hash_sidecars_valid 12`.
- Observability sidecar validation rerun: `observability_sidecars_valid 12`.
- Grammar-mode validation rerun: `grammar_mode_consistency_valid 12`.
- Matrix/C metadata validation rerun: `matrix_factor_c_metadata_valid [12, 2]`.
- Exactly 12 selected cells exist, one for each `grammar_mode x C x P` cell.
- Observed grammar modes: `grammar_off`, `task_agnostic`,
  `template_upper_bound`.
- Observed collapsed conditions: `none`, `G`, `C`, `P`, `G+C`, `G+P`, `C+P`,
  `G+C+P`.
- Runtime MLflow remained disabled for the run; `mlruns/` is absent.
- Billing artifact remains a UTC-day workspace/window reconciliation with two
  entries and empty tags, not tag-attributed per-run billing proof.

## Analyzer patch assessment

The L1a analyzer patch remains narrowly scoped to grammar-mode smoke handling:

- It allows `analysis_scope="l1a_grammar_mode_cp_smoke"` to skip paired replay
  errors that are expected for the selector smoke surface.
- It does not change paired replay strictness outside that scope.
- It preserves required C/P metadata validation and does not fabricate missing
  repair metadata.
- It does not change functional or compile pass/fail definitions.
- It does not change denominator/accounting rules for condition rates or paired
  comparisons.
- It preserves factorial model separation handling; the L1a full-eight-cell
  model remains `model_fit_status: not_fit` under separation.

Additional audit fix:

- `three_way_interaction.reportable` and
  `factorial_model.three_way_interaction_reportable` now inherit the same
  reportability gate as `metadata.reportable`.
- Non-reportable full-eight-cell smoke analyses now carry reason/warning
  `requires_reportable_primary_paper_scale_output`.

## Paper-scale strictness assessment

After the patch, paper-scale reportability remains gated by:

- `analysis_scope == "primary_functional"`;
- no mixed-scale override;
- normalized scale tier exactly `paper`;
- required current cell coverage.

L1a smoke analysis has `analysis_scope: l1a_grammar_mode_cp_smoke`,
`scale_tiers: ["smoke"]`, and `reportable: false`. It is not paper-scale
evidence and cannot mark the nested three-way interaction as reportable after
this audit patch.

## Smoke-report boundary assessment

The preserved L1a artifact report is smoke evidence only. The top-level
analysis artifact already records `reportable: false`, `cell_summaries: 32`,
and `paired_comparisons: 1`.

Important caveat: the already-preserved L1a analysis JSON/report artifacts were
not regenerated in this audit because artifact mutation was not authorized.
Those historical artifacts should be read through this audit if citing the
nested three-way interaction fields. Future analyzer output from the patched
code marks those nested fields non-reportable for smoke scope.

## LEGACY_2X2_GOLDEN_JSON diagnosis

Initial focused analyzer suite result:

```text
shared/tests/test_analyzer_cluster3.py: 35 passed, 1 failed
failed test: test_analyzer_2x2_reproducible_without_cluster3_rows
```

The exact failing assertion was the golden JSON equality check. The observed
diff began with newly emitted row annotations such as `level_gate`,
`metric_current_status`, `metric_display_name`, `metric_gate`,
`metric_reportability`, and `outcome_family`. The reduced contract snapshot
then showed expected key-list drift for metadata and paired-comparison keys,
including `metric_registry`, `metric_aliases`, `registry_provenance`,
`outcome_families`, and repair-history policy metadata.

Diagnosis:

- The legacy golden was stale after intentional analyzer output expansion.
- The deterministic legacy 2x2 fixture still reproduced exactly across runs.
- The sampled values for condition rates, paired comparisons, factorial model
  type, reportability, and paper-table counts remained unchanged.
- The production analyzer behavior was not wrong for the legacy 2x2 path.

## Action taken

- Refreshed `LEGACY_2X2_GOLDEN_JSON` from the deterministic analyzer output.
- Expanded the legacy 2x2 reduced contract snapshot key lists for the new
  metric registry, provenance, outcome-family, and repair-history metadata.
- Patched `shared/analysis/factorial.py` so nested three-way interaction
  reportability follows the overall reportability gate.
- Added `test_smoke_full_eight_cells_do_not_report_three_way_claim`.
- Did not regenerate or mutate existing L1a artifacts, outputs, reports,
  billing files, or `mlruns/`.

## Tests run

```text
.venv/bin/python -m pytest shared/tests/test_analyzer_cluster3.py -q
37 passed

.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
164 passed

.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q
104 passed

.venv/bin/python -m compileall -q shared cluster3
passed

git diff --check
passed
```

Signed/local evidence checks rerun:

```text
schema_and_row_count_valid 12
content_hash_sidecars_valid 12
observability_sidecars_valid 12
grammar_mode_consistency_valid 12
matrix_factor_c_metadata_valid [12, 2]
```

In-memory L1a analyzer check after the patch:

```json
{
  "analysis_scope": "l1a_grammar_mode_cp_smoke",
  "scale_tiers": ["smoke"],
  "reportable": false,
  "cell_summaries": 32,
  "paired_comparisons": 1,
  "factorial_model_type": "full_eight_cell",
  "factorial_model_fit_status": "not_fit",
  "three_way_model_reportable": false
}
```

## Protected mutation proof

Protected diff scan returned empty output:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

`find mlruns -maxdepth 2 -type f -print` returned:

```text
find: mlruns: No such file or directory
```

No Modal command, GPU job, generation command, n=5/n=20 run, billing query,
MLflow write, raw JSONL rewrite, analyzer artifact regeneration, report refresh,
dependency change, or lockfile change was run.

## Remaining caveats

- Existing preserved L1a analyzer/report artifacts were not regenerated; this
  audit supersedes any nested three-way reportability wording in those
  historical derived artifacts.
- Billing remains UTC-day workspace/window reconciliation, not tag-attributed
  per-run proof.
- L1a n=1 is smoke evidence only and remains non-reportable for paper-scale
  claims.
- L1b n=5 execution still requires a separate signed authorization packet with
  explicit stop/spend limits, output paths, validation commands, and mutation
  authorization.

## Go/no-go for L1b n=5

Go for L1b n=5 planning and authorization-packet drafting after this audit
commit.

No-go for L1b n=5 execution until a separate signed packet authorizes Modal/GPU
use, generation, output/artifact mutation, billing policy, validation commands,
and stop/spend limits.

## Classification

`ANALYZER_PATCH_AUDIT_COMPLETE_L1B_N5_PLANNING_READY_NO_EXECUTION`

## Next-step recommendation

Commit and push this audit package. The next branch should be an L1b n=5
planning/authorization packet, not execution. It should explicitly cite this
audit as the analyzer strictness and golden-drift closeout before scaling.
