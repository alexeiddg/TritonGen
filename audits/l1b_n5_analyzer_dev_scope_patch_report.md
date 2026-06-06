# L1b n=5 analyzer development-scope patch audit

## Scope

- branch: `codex-track-handoff-context`
- baseline before patch: `a52d64a Authorize L1b n5 selector profile`
- affected runtime outputs: none
- affected scientific rows: none
- affected repair policy: none
- affected sampling/model settings: none
- affected correctness/pass/fail semantics: none
- classification: `L1B_N5_ANALYZER_DEV_SCOPE_PATCH_COMPLETE`

This patch was made after the authorized L1b n=5 12-cell run exposed an
analyzer shape boundary: the selector output is valid 12-cell grammar-mode
development output, but it does not contain the replay-paired metadata needed
for paired replay comparisons.

## Trigger

The L1b analyzer command:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/*.jsonl --analysis-scope l1b_grammar_mode_cp_dev --scale-tier development --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5_factorial.md
```

initially failed with:

```text
ValueError: missing paired replay metadata: replay_control_condition
```

The failure came from paired-comparison construction, not from row schema,
correctness evaluation, repair semantics, sidecar hashes, or grammar-mode
matrix coverage.

## Patch Summary

Updated:

- `shared/analysis/factorial.py`
- `shared/eval/reporting/tables.py`
- `shared/tests/test_analyzer_cluster3.py`
- `shared/tests/test_reporting_tables.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Analyzer behavior:

- adds `l1b_grammar_mode_cp_dev` to the existing non-paper grammar-mode selector
  pair-skip policy
- keeps ordinary analyzer strictness intact outside the explicit non-paper
  selector scopes
- keeps default and paper-scale analysis raising on missing paired replay
  metadata
- skips only paired replay comparison rows that cannot be built from selector
  outputs lacking pair metadata
- does not alter row parsing, pass/fail labels, repair traces, P/C repair
  semantics, grammar semantics, denominators, or generated metadata

Report behavior:

- labels L1b development output as:
  `L1b development-scale 2^3 factorial diagnostic analysis`
- states that the output is not paper-scale or reportable paper evidence
- states that three-way interaction fields are diagnostic only when metadata
  marks them non-reportable
- preserves the full factorial goal statement

Test isolation behavior:

- redirects the L1b prelaunch guard test to temporary roots so the preserved
  real L1b output namespace does not make the guard test fail
- preserves the runtime fail-if-existing collision guard unchanged

## Strictness Proof

The new analyzer regression test removes `replay_control_condition` metadata
from development rows and verifies both sides of the boundary:

- `analyze_factorial(rows, bootstrap_samples=20)` still raises
  `missing paired replay metadata`
- `analyze_factorial(..., analysis_scope="l1b_grammar_mode_cp_dev")` succeeds
  only as non-reportable development evidence
- `metadata.reportable` remains `False`
- `metadata.scale_tiers` remains `["development"]`
- `metadata.three_way_interaction.reportable` remains `False`
- the three-way reason remains
  `requires_reportable_primary_paper_scale_output`

The report regression test verifies the L1b markdown title and paper-scale
boundary text.

## Validation

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

## Non-Goals Preserved

- no analyzer broadening for paper-scale claims
- no L2 or n=20 execution
- no pass/fail definition changes
- no repair policy changes
- no grammar semantics changes
- no sampling/model setting changes
- no performance, profiler, speedup, or economics claims
- no MLflow runtime writes

## Classification

`L1B_N5_ANALYZER_DEV_SCOPE_PATCH_COMPLETE`

## Next-Step Recommendation

Keep the patch with the L1b completion evidence because it is required to
analyze valid 12-cell n=5 selector output without weakening ordinary or
paper-scale analyzer strictness.
