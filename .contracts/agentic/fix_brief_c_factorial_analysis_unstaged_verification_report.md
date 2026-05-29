# Fix Brief C Unstaged Verification Report

Date: 2026-05-16
Branch reviewed: `main`
Scope: unstaged and untracked working-tree changes related to Fix Brief C.

## Verdict

Not good to commit as-is.

The core research alignment is mostly implemented: the analyzer defaults to Level 2
`functional_success`, keeps `compile_success` diagnostic-only, models the current
four-cell design, records missing P cells, emits structured paper-table sections,
and uses paired bootstrap, McNemar-style p-values, and Holm correction for the
paired primary comparisons.

Hold the commit for one concrete execution blocker and one commit hygiene item:

1. Direct script execution fails before argument parsing.
2. The new reporting table test is untracked and must be intentionally included
   or intentionally dropped before commit.

## Working Tree Reviewed

Modified files:

- `.contracts/research/eval_metrics.md`
- `shared/analysis/factorial.py`
- `shared/eval/constants.py`
- `shared/eval/metrics/equal_attempts.py`
- `shared/eval/reporting/tables.py`
- `shared/tests/test_factorial_analysis.py`

Untracked file:

- `shared/tests/test_reporting_tables.py`

No implementation files were changed by this review. This report is isolated
under `.contracts/agentic/`, which is ignored by git.

## Blocking Findings

### P1 - `shared/analysis/factorial.py` cannot be run as a direct script

Evidence:

```bash
.venv/bin/python shared/analysis/factorial.py --inputs outputs/cluster1/baseline_repaired_l4_n20.jsonl outputs/cluster1/final_g_l4_n20.jsonl --response-variable compile_success --analysis-scope secondary_compile_diagnostic --output /private/tmp/factorial_cluster1_compile.json --bootstrap-samples 100
```

Result:

```text
ModuleNotFoundError: No module named 'shared'
```

Cause: `shared/analysis/factorial.py` now has a CLI entrypoint, but it imports
`shared.eval.constants` with an absolute package import near the top of the file.
When invoked by file path, Python puts `shared/analysis` on `sys.path`, not the
repo root, so the package import fails before `main()` can run.

Why this matters: the brief repeatedly describes `shared/analysis/factorial.py`
as the analysis script and the paper-table generation path. A paper-writing user
is likely to run the file path directly. Module execution works, but the script
path itself is currently a broken new error surface.

Required fix before commit:

- Either make direct path execution work, or document and test only
  `python -m shared.analysis.factorial`.
- Add a regression check for the supported invocation path.

### P2 - `shared/tests/test_reporting_tables.py` is untracked

The new table-rendering tests pass, but they are not part of the git diff shown
by `git diff --name-status`. A commit that stages only modified files would miss
the test coverage for `build_factorial_paper_tables()` and
`render_factorial_markdown_report()`.

Required fix before commit:

- Stage `shared/tests/test_reporting_tables.py` if the reporting-table changes
  stay in scope.
- If intentionally excluding it, remove the reporting helper changes or add
  equivalent tracked coverage elsewhere.

## Requirement Coverage

### Primary metric semantics

Status: implemented.

`analyze_factorial()` defaults to `functional_success`, rejects missing
functional success for primary analysis, and marks `compile_success` output as
secondary diagnostic. The metadata exposes both primary and secondary response
variables.

Relevant implementation:

- `PRIMARY_RESPONSE_VARIABLE = "functional_success"`
- `SECONDARY_RESPONSE_VARIABLE = "compile_success"`
- `analysis_scope` defaults to `primary_functional` for functional success and
  `secondary_compile_diagnostic` for compile success.

### Current four-cell and future eight-cell design

Status: implemented with one note.

The analyzer requires the current primary four cells: `none`, `G`, `C`, `G+C`.
For those cells it fits a reduced model with `G`, `C`, and `G:C`, with
`kernel_class` and `dtype` controls. If all eight canonical cells are present,
it switches to the full `G x C x P` term set.

P-containing cells are marked as missing in metadata, diagnostics, paired
comparison flags, and model warnings. Table 1 currently emits rows only for
populated cells. That is acceptable if table consumers read
`metadata.cells_status`; if the planned paper table needs visible not-populated
rows for P cells, add those rows before commit.

### Paired comparison methods

Status: implemented.

The primary comparisons are fixed to:

- `C` vs `none`
- `G+C` vs `G`

The analyzer validates matched replay identity, computes paired rates and
absolute lift, uses paired bootstrap CIs over within-pair differences, computes
McNemar-style exact discordance p-values, and applies Holm correction across the
paired comparison rows.

The paired validation is stricter than the prose contract by adding `kernel_id`
to the pair key in addition to `kernel_class`, `dtype`, and `base_seed`. That is
defensible because it prevents same-seed collisions across kernels and is filled
from `kernel_name` when missing. It does add a validation dependency, but current
schemas and outputs have either `kernel_id` or `kernel_name`.

### Structured output for paper Tables 1-3

Status: implemented.

The analyzer emits:

- `paper_tables.table_1_cell_summaries`
- `paper_tables.table_2_paired_comparisons`
- `paper_tables.table_3_factorial_terms`

`shared/eval/reporting/tables.py` now consumes those sections without
recomputing statistics and can render a Markdown report.

### Mode collapse warning

Status: implemented.

Rows with `grammar_variant == "template_upper_bound"` and `unique_ratio_ast < 0.1`
are flagged with `mode_collapse_warning` in cell summaries and diagnostics.

### Constants as source of truth

Status: implemented.

`shared/eval/constants.py` remains the source for `BOOTSTRAP_SAMPLES`, `CI_LEVEL`,
and `MULTIPLE_TESTING_METHOD`. The equal-attempt paired lift helper now imports
the bootstrap constants from this file instead of keeping local duplicates.

The new logistic constants also live in `shared/eval/constants.py`, which matches
the contract direction even though logistic fitting details were not explicitly
requested in the supporting-file list.

### Contract updates

Status: mostly implemented.

`.contracts/research/eval_metrics.md` was updated to specify primary
`functional_success`, paired methods, Holm correction, compile success as
diagnostic-only, and missing P-cell semantics.

`.contracts/agentic/cluster2_contract.md` already references
`shared/analysis/factorial.py` as the canonical Cluster 2 paper-table path and
labels compile success diagnostic-only. No unstaged change was needed there.

`cluster3_contract.md` does not appear to exist, so the "when written" part is
not actionable in this diff.

## Validation Performed

Targeted tests:

```bash
.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py shared/tests/test_reporting_tables.py
```

Result: 31 passed.

Aggregation/import regression tests for the touched equal-attempt constants path:

```bash
.venv/bin/python -m pytest shared/tests/test_aggregation.py shared/tests/test_eval_imports.py
```

Result: 58 passed.

Whitespace check:

```bash
git diff --check
```

Result: passed with no output.

Cluster 1 compile diagnostic validation using module invocation:

```bash
.venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster1/baseline_repaired_l4_n20.jsonl outputs/cluster1/final_g_l4_n20.jsonl --response-variable compile_success --analysis-scope secondary_compile_diagnostic --output /private/tmp/factorial_cluster1_compile.json --bootstrap-samples 100
```

Result: passed. Extracted summary:

- populated cells: `none`, `G`
- model type: `partial_four_cell_not_reportable`
- `none`: 0 successes / 180 cells, success rate 0.0
- `G`: 180 successes / 180 cells, success rate 1.0

This reproduces the expected Cluster 1 compile contrast as a secondary
diagnostic and correctly avoids claiming a reduced four-cell factorial model.

Cluster 2 phase-12 smoke validation:

```bash
.venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster2/smoke_none_replay_phase12.jsonl outputs/cluster2/smoke_G_replay_phase12.jsonl outputs/cluster2/smoke_C_phase12.jsonl outputs/cluster2/smoke_GC_phase12.jsonl --output /private/tmp/factorial_cluster2_smoke.json --bootstrap-samples 100
```

Result: failed with `missing paired replay metadata: replay_pair_id`.

Interpretation: this looks like stale phase-12 smoke data that predates the
paired replay metadata contract. The hard failure is correct for primary paper
analysis, but these smoke artifacts cannot be used as proof that the analyzer
runs end-to-end on current paper-shape Cluster 2 output.

## Scope Drift Assessment

Acceptable scope expansion:

- Adding structured table rendering in `shared/eval/reporting/tables.py` matches
  the requested paper Tables 1-3 output path.
- Moving equal-attempt bootstrap constants to `shared/eval/constants.py` supports
  the single-source-of-truth statistical contract.
- Adding logistic fit controls and warnings is within the requested reduced and
  full factorial design behavior.

Risky but defensible choices:

- Pair keys now include `kernel_id`. This is stricter than the Cluster 2 contract
  wording but reduces accidental seed collisions and is backed by tests.
- The implementation goes beyond a stub and implements most statistical logic
  now. That is broader than the compromise paragraph, but it is aligned with the
  final analyzer requirements and covered by tests.

Potential missing polish:

- If paper Table 1 must visibly list all eight canonical cells, add explicit
  `not_populated` rows for P-containing cells. Current output records that status
  in metadata and flags, not as Table 1 rows.

## Recommended Fix Plan

1. Fix or formalize CLI invocation.
   - Preferred: make `python -m shared.analysis.factorial` the documented and
     tested invocation.
   - Alternative: make `python shared/analysis/factorial.py` work from repo root.

2. Add a regression test or smoke command for the supported invocation.
   - It can use a tiny synthetic JSONL fixture or invoke `main()` through pytest.

3. Decide Table 1 missing-cell display semantics.
   - If metadata-level `cells_status` is sufficient, leave it.
   - If the paper table itself must show `P`, `G+P`, `C+P`, and `G+C+P` as
     `not_populated`, add those rows and update renderer tests.

4. Stage `shared/tests/test_reporting_tables.py` with the rest of the reporting
   changes.

5. Re-run:
   - `.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py shared/tests/test_reporting_tables.py`
   - `.venv/bin/python -m pytest shared/tests/test_aggregation.py shared/tests/test_eval_imports.py`
   - `git diff --check`

After those items, the changes should be good to commit.
