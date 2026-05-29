# Factorial 2x2 Preliminary Analysis Report

## 1. Executive summary

Analyzer status: `FACTORIAL_ANALYSIS_BLOCKED`.

Requested output path: `outputs/analysis/factorial_2x2_preliminary.json`.

Output status: not written.

Dataset rows per condition available on disk:

| condition | artifact | rows |
|---|---|---:|
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 |

Primary result summary: the analyzer could not produce the preliminary 2x2 JSON because the current primary functional analyzer requires `functional_success` for all rows, but the frozen Cluster 1 none/G inputs do not contain that field. The secondary compile diagnostic is also blocked because the C artifact does not contain `compile_success`.

## 2. Inputs

None artifact: `outputs/cluster1/baseline_repaired_l4_n20.jsonl`, 180 rows.

G artifact: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, 177 rows.

C artifact: `outputs/cluster2/c_paper_n20_l4.jsonl`, 180 rows.

G+C artifact: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`, 177 rows.

Coverage caveat: the G and G+C covered-row schedule is 177/180 due to missing G replay rows for `matmul/fp32` sample 5 and `matmul/bf16` samples 0 and 18.

## 3. Pairing validation

Pairing was not completed by the analyzer because response validation failed before paired comparisons were emitted.

Seed/sample identity status:

- Cluster 2 C and G+C rows contain `base_seed`.
- Cluster 1 none/G rows contain `generation_seed`, which the analyzer can normalize as `base_seed`.
- The G and G+C row counts align at 177 covered rows.

Matched rows: not emitted.

Unmatched rows: not emitted.

Missing G/G+C rows: the known 3 missing matmul rows listed above.

## 4. Metrics

Available raw metrics:

| condition | functional_success | compile_success |
|---|---:|---:|
| none | missing for 180/180 rows | 0/180 |
| G | missing for 177/177 rows | 3/177 |
| C | 0/180 | missing for 180/180 rows |
| G+C | 0/177 | 4/177 |

Because the response fields are not present consistently across all four inputs, no primary functional or secondary compile factorial result was produced.

## 5. Statistical outputs

Paired comparisons: not produced.

Bootstrap confidence intervals: not produced.

McNemar tests: not produced.

G:C interaction: not produced.

Primary analyzer command attempted:

```bash
.venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster1/baseline_repaired_l4_n20.jsonl outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl outputs/cluster2/c_paper_n20_l4.jsonl outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --output outputs/analysis/factorial_2x2_preliminary.json
```

Failure:

```text
ValueError: missing functional_success for primary Cluster 2 factorial analysis
```

Secondary diagnostic command attempted:

```bash
.venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster1/baseline_repaired_l4_n20.jsonl outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl outputs/cluster2/c_paper_n20_l4.jsonl outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --response-variable compile_success --analysis-scope secondary_compile_diagnostic --output outputs/analysis/factorial_2x2_preliminary.json
```

Failure:

```text
ValueError: missing compile_success for requested analysis
```

## 6. Interpretation

This remains preliminary only and limited to the current 2x2 subset over G and C.

No statistical claim should be made from this analyzer run because the output JSON was not produced.

The blocker is not the new G+C artifact. The new G+C artifact passed strict validation. The blocker is mixed response-field availability across frozen Cluster 1 and Cluster 2 inputs.

Do not impute `functional_success` or `compile_success` across clusters without an explicit methodology decision, because that would mix compile-only Cluster 1 semantics with functional Cluster 2 semantics.

## 7. Next report-ready summary

The G+C n=20 L4 run completed and produced a valid 177-row covered artifact. The preliminary 2x2 factorial analyzer is blocked: current frozen none/G inputs lack `functional_success`, and C lacks `compile_success`, so the analyzer cannot emit paired comparisons, bootstrap intervals, McNemar tests, or a G:C interaction term without a schema/methodology update.
