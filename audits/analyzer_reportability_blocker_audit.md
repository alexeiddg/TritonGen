# Analyzer Reportability Blocker Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `AUDIT_COMPLETE`

## 1. Executive summary

`outputs/analysis/factorial_2x2_preliminary.json` has `metadata.reportable=false` because the analyzer normalized the loaded rows to `metadata.scale_tiers=["unspecified"]`, and `shared/analysis/factorial.py::_is_reportable_output(...)` only returns true when all of the following are true:

- `scope == "primary_functional"`
- `allow_mixed_scale` is false
- `scale_tiers == ("paper",)`

The current analyzer output satisfies the first two conditions but fails the third. Direct artifact inspection confirmed that none of the four current JSONL artifacts carries a top-level or nested `scale_tier` field, so `normalize_result_rows(...)` defaults every row to `"unspecified"`.

This is a metadata/reportability-policy blocker, not a statistical-computation blocker. The analyzer loads 714 rows, emits primary paired functional comparisons, emits secondary compile diagnostics, applies the current F3 policy, and records the expected 177/180 coverage caveat. The output is not stale relative to current analyzer code: `shared/analysis/factorial.py` was modified at 2026-05-21 11:44:22 and the analyzer JSON at 2026-05-21 11:45:05. A read-only in-memory dry run with current artifacts still produced `scale_tiers=["unspecified"]` and `reportable=false`; the same dry run with only in-memory `scale_tier="paper"` annotation produced `reportable=true`.

Artifacts are sufficient for the current covered-row 2^2 preliminary analysis. No JSONL artifact needs regeneration to clear this exact blocker. A code/policy fix is needed so the analyzer can attach or infer the report-scale tier from an explicit reportability input, registry, or audited invocation metadata without rewriting raw artifacts. After that fix, the analyzer must be rerun to produce a new reportable output.

Recommended next task: `PATCH_ANALYZER_REPORTABILITY_POLICY`.

## 2. Analyzer output inspection

Path inspected:

`outputs/analysis/factorial_2x2_preliminary.json`

Top-level keys:

```text
cell_summaries
condition_rates
diagnostics
factorial_model
metadata
paired_comparisons
paper_tables
```

Reportability fields:

| Field | Value |
|---|---|
| top-level `reportable` | absent |
| `metadata.reportable` | `false` |
| `metadata.scale_tiers` | `["unspecified"]` |
| `metadata.analysis_scope` | `primary_functional` |
| `metadata.scope_kind` | `temporary_2^2_subset` |
| `metadata.cells_populated` | `none`, `G`, `C`, `G+C` |
| `metadata.cells_missing` | `P`, `G+P`, `C+P`, `G+C+P` |

No explicit `reportability`, `reportability_checks`, `blocking_findings`, `warnings`, `caveats`, `validation`, `row_counts`, or `excluded_rows` top-level sections are present. The reportability value is embedded only under `metadata`.

Key analyzer metadata:

| Metadata key | Value |
|---|---|
| `analyzer_version` | `factorial_alignment_v3_f3_eval_pipeline_policy` |
| `response_variable` | `functional_success` |
| `primary_response_variable` | `functional_success` |
| `secondary_response_variable` | `compile_success` |
| `f3_excluded_counts` | `{"G+C": 5}` |
| `g_replay_coverage` | `177/180 task-agnostic G replay rows; 3 matmul rows missing (...) Policy: COVERAGE_WARNING_SKIP_MISSING.` |
| `interpretation_flags` | `["p_cells_not_populated"]` |

Row counts and emitted analysis:

| Item | Value |
|---|---:|
| `diagnostics.rows_loaded` | 714 |
| none rows in rates | 180 |
| G rows in rates | 177 |
| C rows in rates | 180 |
| G+C rows in rates | 177 |
| primary paired comparisons | `C vs none` n=180, `G+C vs G` n=177 |
| secondary compile diagnostics | `G vs none` n=177, `G+C vs C` n=177 |

Warnings/caveats found in output:

- `factorial_model.warnings=["p_cells_not_populated", "model_outcome_has_single_class"]`
- Secondary compile comparisons carry `coverage_warning_skip_missing`.
- G/G+C missing treatment pairs are the known three matmul rows:
  - `matmul/gemm/fp32/base_seed=5`
  - `matmul/gemm/bf16/base_seed=0`
  - `matmul/gemm/bf16/base_seed=18`
- `G+C` has five `F3_EVAL_PIPELINE` rows.

These caveats are emitted and must travel with results, but they are not the exact code condition that sets `metadata.reportable=false`.

## 3. Code path inspection

Reportability is computed in:

| File | Function | Role |
|---|---|---|
| `shared/analysis/factorial.py` | `normalize_result_rows(...)` | Sets each normalized row's `scale_tier` from the payload, defaulting to `"unspecified"`. |
| `shared/analysis/factorial.py` | `_validate_scale_tiers(...)` | Returns the unique normalized scale tiers and rejects mixed tiers unless `allow_mixed_scale=True`. |
| `shared/analysis/factorial.py` | `analyze_factorial(...)` | Writes `metadata["scale_tiers"]` and `metadata["reportable"]`. |
| `shared/analysis/factorial.py` | `_is_reportable_output(...)` | Computes the boolean reportability policy. |

Relevant logic, summarized:

- `normalize_result_rows(...)` stores `"scale_tier": _first_present(payload, "scale_tier", default="unspecified")`.
- `_validate_scale_tiers(...)` returns `["unspecified"]` when there is no usable row scale tier.
- `analyze_factorial(...)` sets `metadata["reportable"] = _is_reportable_output(scope=scope, scale_tiers=scale_tiers, allow_mixed_scale=allow_mixed_scale)`.
- `_is_reportable_output(...)` returns true only for primary functional analysis, no mixed-scale override, and exactly `("paper",)` scale tiers.

The exact failed condition is:

```text
tuple(scale_tiers) == ("paper",)
```

Observed current value:

```text
scale_tiers == ["unspecified"]
```

The reportability flag is computed from this policy. It is not manually written in the JSON, and it is not directly computed from pairing, F3 rows, missing G rows, unknown provenance, statistical warnings, or P-cell absence.

Test evidence in `shared/tests/test_factorial_analysis.py` confirms intended behavior:

- The current four-cell 2^2 scope can be reportable when rows have `scale_tier="paper"`.
- Primary analysis with `scale_tier` values of `smoke`, `development`, or `unspecified` is intentionally non-reportable.
- Mixed `paper` and `unspecified` scale tiers remain non-reportable even with `allow_mixed_scale=True`.

## 4. Artifact sanity check

Direct JSONL inspection found all current artifacts present and valid.

| Condition | Path | Valid rows | Intended rows | Key facts |
|---|---|---:|---:|---|
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | Compile-only Cluster 1 baseline; `compile_success=false` for all rows; no `functional_success`; no scale tier. |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | Task-agnostic G; 3 compile successes; missing three matmul rows; `modal_image_sha=unknown`; no scale tier. |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | All `F0_PARSE`; `functional_success=false`; raw `compile_success` absent and analyzer derives false; no scale tier. |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | 4 `F2_NUMERIC_NAN`, 5 `F3_EVAL_PIPELINE`; `compile_success=true` for 4 rows; missing same three matmul rows; no scale tier. |

Scale-tier inspection:

| Condition | Top-level `scale_tier` | Nested `generated_metadata.scale_tier` |
|---|---|---|
| none | absent/null on 180 rows | absent/null on 180 rows |
| G | absent/null on 177 rows | absent/null on 177 rows |
| C | absent/null on 180 rows | absent/null on 180 rows |
| G+C | absent/null on 177 rows | absent/null on 177 rows |

The current artifacts match `docs/05_artifacts_and_results_registry.md` for path identity, row counts, missing-row caveats, C compile-normalization caveat, G provenance caveat, and G+C F3 caveat.

In-memory dry-read check:

| Dry-read state | `scale_tiers` | `reportable` | Interpretation |
|---|---|---:|---|
| Current artifacts as loaded | `["unspecified"]` | `false` | Reproduces current blocker. |
| Same loaded rows with in-memory `scale_tier="paper"` only | `["paper"]` | `true` | Confirms no row regeneration is needed for this exact blocker. |

## 5. Blocker classification

| Finding | Evidence | Classification | Blocks official results? | Minimal remedy |
|---|---|---|---|---|
| Analyzer reportability requires exact `scale_tiers=("paper",)` but current rows normalize to `["unspecified"]`. | `shared/analysis/factorial.py::_is_reportable_output(...)`; analyzer metadata; dry-read check. | `ANALYZER_POLICY_BLOCKER` plus metadata-related blocker | Yes | Patch reportability policy or scale-tier annotation path; rerun analyzer. |
| Raw artifacts do not carry `scale_tier`. | Direct artifact inspection: all four artifacts have null/absent top-level and nested scale tier. | `SCHEMA_BLOCKER` / metadata-related, if the policy expects row-level scale tier | Yes, under current policy | Prefer analyzer input/registry scale annotation over modifying generated artifacts. |
| G/G+C are 177/180 and missing three matmul rows. | Direct counts; analyzer `g_replay_coverage`; docs/05 and docs/07. | `NON_BLOCKING_CAVEAT` for current covered-row analysis; `DATA_BLOCKER` only for a complete 180/180 claim | No for current covered-row 2^2 output; yes for 180/180 claim | Keep coverage warning; regenerate only if the report must claim complete 180/180 G/G+C coverage. |
| Direct Cluster 1 controls lack raw `replay_pair_id`. | Prior audit; current analyzer output now emits paired comparisons. | Historical pairing blocker, now resolved for analyzer output | No | No action for current reportability blocker. |
| `F3_EVAL_PIPELINE` rows in G+C. | Five rows; analyzer F3 policy metadata; docs/06 and docs/07. | `NON_BLOCKING_CAVEAT` under current policy | No | Keep F3 caveat; no artifact regeneration required for reportability. |
| C has no raw `compile_success`. | C rows all null/absent; analyzer condition rates derive false from `F0_PARSE`. | Historical schema blocker, now resolved by analyzer normalization | No | No action for current reportability blocker. |
| Cluster 1 `functional_success` absent. | none/G rows have no raw functional success; analyzer normalizes false/unproven. | Historical schema/methodology blocker, now resolved | No | No action for current reportability blocker. |
| Functional outcome has a single observed class, so logistic model is not fit. | `factorial_model.warnings` includes `model_outcome_has_single_class`. | `NON_BLOCKING_CAVEAT` / statistical caveat | No for paired descriptive/test outputs; yes for quoting logistic coefficients | Report paired/all-zero result carefully; do not quote unavailable logistic terms as estimates. |
| P cells are missing/deferred. | Metadata `scope_kind=temporary_2^2_subset`, missing P cells, tests allow current 2^2 paper-scale reportability. | `NON_BLOCKING_CAVEAT` for current 2^2; methodology blocker only for full 2^3 claims | No for current 2^2; yes for full 2^3 | Keep scope caveat; do not claim P or full 2^3 results. |
| G `modal_image_sha=unknown` and none legacy provenance gaps. | Direct artifact inspection; docs/05/08. | `NON_BLOCKING_CAVEAT` / provenance caveat | Not the exact reportability blocker | Preserve caveats; no regeneration required for this reportability issue. |

## 6. Staleness assessment

The current analyzer output does not appear stale with respect to the current reportability logic.

Observed modification times:

| Path | Modified |
|---|---|
| `shared/analysis/factorial.py` | 2026-05-21 11:44:22 |
| `outputs/analysis/factorial_2x2_preliminary.json` | 2026-05-21 11:45:05 |
| `docs/05_artifacts_and_results_registry.md` | 2026-05-21 13:27:03 |
| `docs/07_analysis_and_statistics.md` | 2026-05-21 14:05:34 |
| `docs/08_decision_log.md` | 2026-05-21 14:35:24 |

The output was generated after the current analyzer code and after the earlier Cluster 1 functional-success, Cluster 2 compile-success, F3 policy, and pairing fixes. Later docs describe the same state rather than contradicting the JSON.

A no-output in-memory analyzer dry read with the current code and current artifacts reproduced `reportable=false`. Therefore a no-code rerun would likely preserve `metadata.reportable=false`. This is not a `STALE_OUTPUT_BLOCKER`; it needs a policy/schema metadata fix before rerun.

## 7. Artifact sufficiency assessment

Existing artifacts are sufficient for the current 2^2 covered-row preliminary analysis, assuming reportability policy is fixed or supplied with explicit paper-scale metadata.

| Artifact | Regenerate for this blocker? | Rationale |
|---|---:|---|
| none | No | 180 valid rows; analyzer can normalize and pair it. |
| G | No | 177 valid rows; missing rows are already explicit coverage caveats. |
| C | No | 180 valid rows; analyzer derives compile success from F0 failure codes. |
| G+C | No | 177 valid rows; F3 policy and coverage caveats are already represented. |

Regenerate only if the project changes the claim from "current covered-row 2^2 preliminary analysis" to either:

- complete 180/180 G and G+C coverage, or
- full 2^3 coverage with P-containing cells.

Neither is required to clear the current `metadata.reportable=false` cause.

## 8. Recommended minimal fix path

1. Patch analyzer reportability policy or scale-tier normalization so the current registered artifacts can be explicitly analyzed as paper/preliminary-scale without rewriting raw JSONL artifacts.
   - Preferred safe design: add an explicit analyzer input such as a CLI scale tier, registry-driven artifact metadata, or a small analysis manifest consumed at read time.
   - Avoid filename-only inference unless tests make the policy explicit; paths are documentation evidence but weak as the sole source of reportability.
2. Keep existing caveats visible in the output:
   - 2^2 temporary scope;
   - P cells deferred;
   - G/G+C 177/180 coverage;
   - three missing matmul identities;
   - five G+C `F3_EVAL_PIPELINE` rows;
   - G `modal_image_sha=unknown`;
   - none legacy provenance;
   - all-zero functional outcome and unavailable logistic coefficient.
3. Add or update tests proving:
   - current four-cell `scale_tier="paper"` primary functional output is reportable;
   - `unspecified`, `development`, `smoke`, and mixed tiers remain non-reportable;
   - reportability is not silently granted by row count alone.
4. Rerun the analyzer after the fix using `.venv/bin/python` and the current four inputs.
5. Verify the new analyzer JSON has the intended `metadata.reportable` value and unchanged row/comparison caveats.
6. Update docs only if the reportability field, scale-tier policy wording, or analyzer invocation semantics changed.
7. Do not regenerate artifacts unless a separate method decision requires complete 180/180 or full 2^3 coverage.

Next task category:

`PATCH_ANALYZER_REPORTABILITY_POLICY`

## 9. Report drafting implication

| Drafting question | Answer |
|---|---|
| Can methodology sections be drafted now? | Yes. Current docs and artifacts are aligned for methodology, scope, caveats, and source traceability. |
| Can result tables be drafted with placeholders? | Yes. Table structure, rows, caveat columns, and source references can be drafted now. |
| Can official final result values be quoted? | No. Official final statistical-result prose should wait for a reportable analyzer output or an explicit decision to publish non-final values with visible caveats. |
| Can exploratory/non-reportable values be quoted with caveat? | Yes, if clearly labeled as inspectable/non-final analyzer evidence from `metadata.reportable=false`, not official final results. |

Practical report guidance:

- Use the current analyzer values only as exploratory or placeholder evidence until reportability is resolved.
- Do not quote unavailable logistic coefficients.
- Keep all missing-row, F3, provenance, Cluster 1 compile-only, and P-deferral caveats visible.

## 10. Next Codex prompt recommendation

Recommended next prompt:

```text
Patch the analyzer reportability policy for outputs/analysis/factorial_2x2_preliminary.json. Do not modify raw JSONL artifacts. Add an explicit, audited way for the current registered four-input 2^2 analysis to carry scale_tier="paper" at analyzer runtime, preserve all existing coverage/F3/P/provenance caveats, add focused tests for reportable and non-reportable scale tiers, then rerun the analyzer with .venv/bin/python and verify the new metadata.reportable value.
```

Expected category:

`PATCH_ANALYZER_REPORTABILITY_POLICY`

## 11. Appendix

### Commands run

```text
git status --short
.venv/bin/python analyzer JSON inspection script from the task prompt
.venv/bin/python artifact sanity inspection script from the task prompt
rg "reportable|metadata.reportable|is_reportable|non_reportable|not reportable|blocking|blocker|caveat|warnings|validation" shared docs audits outputs -u
rg "factorial_2x2_preliminary|rows_loaded|loaded rows|714|reportable=false|reportable.*false" shared docs audits outputs -u
rg "replay_pair_id|pairing|matched|paired|base_seed|generation_seed|sample_index|tuple|unmatched|missing rows|177|180" shared docs audits outputs cluster1 cluster2 -u
rg "F3_EVAL_PIPELINE|F3_|eval pipeline|correctness_result|malformed|payload|compile_success" shared docs audits outputs cluster2 -u
rg "functional_success|compile_success|normalization|Cluster 1|Cluster 2|F0_|F1_|F2_" shared docs audits outputs cluster1 cluster2 -u
rg "metadata|provenance|modal_image_sha|unknown|tokenizer_revision|model_revision|grammar_sha" shared docs audits outputs cluster1 cluster2 -u
rg "Wilson|McNemar|bootstrap|Holm|interaction|confidence|CI|all-zero|discordant" shared docs audits outputs -u
rg -n "reportable|analyze_factorial|metadata =|scope_kind|scale_tiers|p_cells|factorial_model|model_outcome_has_single_class|analysis_scope|temporary_2" shared/analysis/factorial.py
sed reads of relevant `shared/analysis/factorial.py` ranges
sed reads of `docs/07_analysis_and_statistics.md`
sed reads of `audits/analyzer_pre_output_verification_audit.md`
sed reads of `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`
rg -n "reportable|scale_tier|allow_mixed_scale|paper" shared/tests/test_factorial_analysis.py shared/analysis/factorial.py docs audits -u
sed reads of `docs/05_artifacts_and_results_registry.md`
sed reads of `docs/06_failure_taxonomy_and_eval_ladder.md`
sed reads of `docs/08_decision_log.md`
sed reads of `audits/final_documentation_consistency_audit.md`
sed reads of `audits/factorial_cluster1_functional_success_normalization_fix_report.md`
sed reads of `audits/factorial_cluster2_compile_success_normalization_fix_report.md`
sed reads of `shared/eval/aggregation.py`
sed reads of `shared/eval/failure_taxonomy.py`
rg targeted checks in `cluster1/results/dataclass.py` and `cluster2/results/dataclass.py`
ls -lT relevant analyzer, docs, audit, and artifact paths
.venv/bin/python analyzer output summary script
.venv/bin/python in-memory dry-read reportability comparison
.venv/bin/python scale_tier field presence check
```

### Inspected files

Required files inspected:

- `outputs/analysis/factorial_2x2_preliminary.json`
- `shared/analysis/factorial.py`
- `docs/07_analysis_and_statistics.md`
- `audits/analyzer_pre_output_verification_audit.md`
- `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`

Additional relevant files inspected:

- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/08_decision_log.md`
- `audits/final_documentation_consistency_audit.md`
- `audits/factorial_cluster1_functional_success_normalization_fix_report.md`
- `audits/factorial_cluster2_compile_success_normalization_fix_report.md`
- `shared/eval/aggregation.py`
- `shared/eval/failure_taxonomy.py`
- `cluster1/results/dataclass.py`
- `cluster2/results/dataclass.py`
- `shared/tests/test_factorial_analysis.py`

Current artifacts inspected read-only:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
- `outputs/cluster2/c_paper_n20_l4.jsonl`
- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`
