# Analyzer Scale-Tier Reportability Fix Report

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `FIX_VERIFIED_REPORTABLE`

## 1. Executive summary

Root cause: `outputs/analysis/factorial_2x2_preliminary.json` was non-reportable because the analyzer normalized all loaded rows to `scale_tier="unspecified"` while reportability requires `scale_tiers == ("paper",)`.

Fix implemented: `shared/analysis/factorial.py` now supports explicit analysis-level scale-tier annotation through `scale_tier_annotation` and the CLI flag `--scale-tier`. The annotation only fills rows with no explicit raw `scale_tier`; explicit conflicting raw tiers fail loudly. The analyzer output records raw tiers before annotation, normalized tiers, requested tier, and annotation source.

Output status: the analyzer was rerun successfully and `outputs/analysis/factorial_2x2_preliminary.json` now has `metadata.reportable=true`.

Exact analyzer command run:

```bash
.venv/bin/python -m shared.analysis.factorial --none outputs/cluster1/baseline_repaired_l4_n20.jsonl --g outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl --c outputs/cluster2/c_paper_n20_l4.jsonl --gc outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --scale-tier paper --output outputs/analysis/factorial_2x2_preliminary.json
```

Final classification: `FIX_VERIFIED_REPORTABLE`.

## 2. Root cause

The four current raw JSONL artifacts do not contain a reportability-scale field:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
- `outputs/cluster2/c_paper_n20_l4.jsonl`
- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

The reportability code path was:

- `shared/analysis/factorial.py::normalize_result_rows(...)`
- `shared/analysis/factorial.py::_validate_scale_tiers(...)`
- `shared/analysis/factorial.py::analyze_factorial(...)`
- `shared/analysis/factorial.py::_is_reportable_output(...)`

`normalize_result_rows(...)` defaulted absent scale tiers to `"unspecified"`. `_validate_scale_tiers(...)` returned `["unspecified"]`. `_is_reportable_output(...)` requires primary functional scope, mixed-scale disabled, and exactly `("paper",)`, so reportability stayed false.

This was a metadata/policy blocker, not a data insufficiency blocker. The analyzer already loaded 714 rows, preserved the 177/180 coverage caveat, emitted F3 policy metadata, and produced paired comparisons.

## 3. Implementation

Files modified:

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`

New behavior:

- `normalize_result_rows(...)`, `load_results(...)`, `load_result_paths(...)`, and `analyze_factorial(...)` accept `scale_tier_annotation`.
- CLI supports `--scale-tier paper`.
- CLI also supports condition-specific input flags `--none`, `--g`, `--c`, and `--gc` for the current 2x2 invocation.

Annotation semantics:

- Missing raw scale tier plus `--scale-tier paper` normalizes rows to `scale_tier="paper"`.
- Missing raw scale tier without annotation still normalizes to `scale_tier="unspecified"` and remains non-reportable.
- Explicit raw `scale_tier="paper"` is preserved.
- Explicit raw non-matching tiers such as `development` plus `--scale-tier paper` raise a conflict error; no silent override is allowed.
- Mixed tiers still fail by default; with the diagnostic mixed-scale override they remain non-reportable.

Metadata emitted in analyzer output:

- `scale_tier_source`
- `scale_tier_sources`
- `requested_scale_tier`
- `raw_scale_tiers_before_annotation`
- `normalized_scale_tiers`
- existing `scale_tiers`

The regenerated output records:

```text
scale_tier_source = analysis_cli_annotation
requested_scale_tier = paper
raw_scale_tiers_before_annotation = ["unspecified"]
normalized_scale_tiers = ["paper"]
scale_tiers = ["paper"]
```

## 4. Tests

Tests added/updated in `shared/tests/test_factorial_analysis.py`:

- default missing scale tier remains `unspecified` and non-reportable;
- explicit analysis-level annotation sets missing tiers to `paper`;
- explicit raw `paper` is preserved;
- conflicting explicit raw tier plus annotation raises;
- mixed tiers still raise by default and remain non-reportable under diagnostic override;
- real current artifacts pass the scale-tier check with explicit paper annotation;
- CLI help exposes `--scale-tier` and condition-specific input flags.

Commands run:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or scale_tier or reportable or reportability" -q
```

Result:

```text
86 passed, 484 deselected
```

CLI help:

```bash
.venv/bin/python -m shared.analysis.factorial --help
```

Result: passed; help lists `--scale-tier`, `--none`, `--g`, `--c`, and `--gc`.

Default no-annotation dry run on the current artifacts:

```text
default_reportable False
default_scale_tiers ['unspecified']
default_scale_tier_source raw_missing_default_unspecified
```

## 5. Analyzer rerun

Command:

```bash
.venv/bin/python -m shared.analysis.factorial --none outputs/cluster1/baseline_repaired_l4_n20.jsonl --g outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl --c outputs/cluster2/c_paper_n20_l4.jsonl --gc outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --scale-tier paper --output outputs/analysis/factorial_2x2_preliminary.json
```

Output path:

`outputs/analysis/factorial_2x2_preliminary.json`

Verification:

- valid JSON: yes
- top-level keys: `cell_summaries`, `condition_rates`, `diagnostics`, `factorial_model`, `metadata`, `paired_comparisons`, `paper_tables`
- rows loaded: 714
- condition rows: none 180, G 177, C 180, G+C 177
- scale tiers after normalization: `["paper"]`
- `metadata.reportable`: `true`

## 6. Artifact integrity

Raw JSONL artifacts were not modified.

Verification command:

```bash
git diff -- outputs/cluster1 outputs/cluster2
```

Result: no diff.

No Modal invocation, GPU job, generation job, experiment run, grammar-file edit, raw JSONL rewrite, Cluster 1/Cluster 2 artifact rewrite, or hash re-recording was performed.

## 7. Remaining caveats

The reportability fix does not remove analysis caveats. The regenerated output still records:

- G and G+C are 177/180, not 180/180.
- Missing rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- G+C has five `F3_EVAL_PIPELINE` rows.
- P/Cluster 3 cells are absent/deferred; this is a current 2x2 subset, not full 2^3 completion.
- `factorial_model.warnings` includes `p_cells_not_populated` and `model_outcome_has_single_class`.
- The secondary compile comparisons retain `coverage_warning_skip_missing`.
- Cluster 1 remains compile-only for none/G functional-success normalization.
- G retains the known `modal_image_sha=unknown` provenance caveat from the registry.

## 8. Report implication

Official statistical-result prose for the current registered preliminary/report-scale 2x2 set can now be drafted from the regenerated analyzer output, provided the prose carries the remaining 177/180, F3, P-deferral, single-class model, and provenance caveats.

Do not claim complete 180/180 G or G+C coverage. Do not claim P/Cluster 3 or full 2^3 results. Do not quote unavailable logistic coefficients as fitted estimates.

## 9. Next recommendation

`PROCEED_TO_RESULTS_SECTION_DRAFT`
