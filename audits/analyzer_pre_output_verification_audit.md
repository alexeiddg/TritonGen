# Analyzer Pre-Output Verification Audit

Date: 2026-05-21

Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `AUDIT_CONCERNS_RAISED`

## 1. Executive summary

The analyzer methodology is mostly sound for the current 2x2 preliminary functional-success question, but the current implementation cannot emit the official output because direct Cluster 1 control artifacts do not carry the paired replay metadata expected by `shared/analysis/factorial.py`.

Pairing is valid at the tuple level with a coverage caveat:

- `C` vs `none`: 180/180 matched tuples.
- `G+C` vs `G`: 177/177 covered matched tuples.
- Four-way overlap across `none`, `G`, `C`, and `G+C`: 177 tuples.
- Missing covered-row identities are the known task-agnostic G/G+C gaps: `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.

The current analyzer already joins paired outcomes on explicit tuple identity:

`(kernel_class, kernel_id, dtype, base_seed)`

The blocker is not the row join. The blocker is `_validate_pair_metadata_columns(...)`, which requires `replay_pair_id`, replay seed fields, prompt hash, model id, temperature, and token budget on both generated rows and replay controls. Cluster 2 generated rows have those values in `generated_metadata`; raw Cluster 1 artifacts do not have `replay_metadata`.

Recommended minimal fix: **Option B - use tuple-based matching key instead of requiring `replay_pair_id` from raw Cluster 1 artifacts.** Keep generated-row replay metadata validation, but allow direct Cluster 1 controls to be validated by explicit tuple key plus manifest/current-prompt parity rather than requiring raw rows to carry Cluster 2 replay metadata.

Primary concerns raised:

- Individual cell-rate confidence intervals are not emitted; the analyzer emits paired bootstrap CIs for paired lifts only.
- The analyzer's interaction term is a logistic-model `G:C` coefficient, not an additive rate difference-in-differences term.
- Secondary compile comparisons requested for `G vs none` and `G+C vs C` are not currently emitted as paired comparison rows.
- Output documentation should explicitly state the `F3_EVAL_PIPELINE` compile-success policy and the 177/180 coverage caveat.

## 2. Scope

This was an analyzer pre-output verification audit only.

Actions intentionally not performed:

- No code changes.
- No JSONL artifact changes.
- No frozen artifact changes.
- No grammar file changes.
- No hash re-recording.
- No Modal invocation.
- No GPU jobs.
- No generation.
- No C or G+C experiment runs.
- No fix brief.

The only file written by this task is this audit report:

`audits/analyzer_pre_output_verification_audit.md`

## 3. Block 1 - replay_pair_id diagnosis

### 3.1 Definition and construction

`replay_pair_id` is replay-pair provenance for one seed-aligned replay row. It is defined as a field, not as the primary dataframe join key.

Inspected definitions and construction paths:

| File | Function/class | Finding |
| --- | --- | --- |
| `cluster2/replay/manifest.py` | `ReplaySeedScheduleEntry` | Contains `kernel_class`, `kernel_name`, `dtype`, `base_seed`, `generation_seed`, prompt metadata, and `replay_pair_id`. |
| `cluster2/replay/manifest.py` | `_entries_for_schedule_record(...)` | Reads `replay_pair_ids` from the frozen manifest seed schedule and validates each entry against matching `row_records`. |
| `cluster2/replay/manifest.py` | `_validate_schedule_entry_matches_row(...)` | Requires manifest schedule values, including `replay_pair_id`, to match row records. |
| `cluster2/replay/manifest.py` | `_sample_identity_from_row(...)` | Reconstructs sample identity from `sample_index`, then `generation_seed`, then `base_seed`. |
| `cluster2/replay/cluster1_controls.py` | `_sample_identity_from_raw_row(...)` | Uses the same identity fallback order for raw Cluster 1 rows. |
| `cluster2/experiments/run_cluster2_modal.py` | `_validate_generation_pairing_context(...)` | Verifies generated C2 pairing context before generation: kernel class, dtype, base seed, generation seed, prompt hash, model id, temperature, and known revisions. |
| `cluster2/experiments/run_cluster2_modal.py` | `_run_generated_condition_candidate(...)` | Writes `replay_pair_id`, replay seeds, and prompt hash into generated row metadata. |
| `cluster2/results/dataclass.py` | `Cluster2ReplayRowMetadata`, `Cluster2GeneratedRowMetadata` | Both schemas have optional replay pairing fields. |

Observed real recipe:

`replay_pair_id = "{kernel_class}:{dtype}:{base_seed}"`

This recipe was verified for all selected manifest rows:

- `none`: 180 IDs, 180 unique, 0 mismatches.
- `G`: 177 IDs, 177 unique, 0 mismatches.
- `C` generated metadata: 180 rows, 0 mismatches.
- `G+C` generated metadata: 177 rows, 0 mismatches.

Examples:

| Tuple | replay_pair_id |
| --- | --- |
| `elementwise/fp32/0` | `elementwise:fp32:0` |
| `reduction/fp32/0` | `reduction:fp32:0` |
| `matmul/fp32/0` | `matmul:fp32:0` |
| `matmul/bf16/18` | `matmul:bf16:18` |

### 3.2 Analyzer usage

The analyzer does not use `replay_pair_id` as the dataframe join key.

Relevant analyzer code:

| File | Function/constant | Finding |
| --- | --- | --- |
| `shared/analysis/factorial.py` | `PAIR_KEY_COLUMNS = ("kernel_class", "kernel_id", "dtype", "base_seed")` | This is the actual paired row key. |
| `shared/analysis/factorial.py` | `paired_replay_summary(...)` | Groups treatment/control outcomes on `PAIR_KEY_COLUMNS`. |
| `shared/analysis/factorial.py` | `validate_paired_replay_dataframe(...)` | Validates tuple key coverage and then calls metadata validation. |
| `shared/analysis/factorial.py` | `_validate_pair_metadata_columns(...)` | Requires `replay_pair_id`, replay seeds, prompt hash, model id, temperature, and max token budget in generated/replay metadata. |
| `shared/analysis/factorial.py` | `_pair_metadata_frame(...)` | Raises `ValueError: missing paired replay metadata: replay_pair_id` for direct Cluster 1 rows. |

Statistical operations that require the paired identity:

| Operation | Current key or field |
| --- | --- |
| Row join | `PAIR_KEY_COLUMNS`, not `replay_pair_id`. |
| McNemar exact test | Uses paired outcomes produced by the tuple join. |
| Paired bootstrap | Uses paired outcome differences produced by the tuple join. |
| Matched lift | Uses tuple-joined treatment/control rates. |
| G:C factorial model | Uses condition-level cell outcomes grouped by tuple key, not `replay_pair_id`. |

Conclusion: `replay_pair_id` is essential to the current strict metadata validation path, but it is not essential to the statistical pairing itself. It is currently an alias/provenance field for tuple identity.

### 3.3 Cluster 1 equivalent identity fields

Representative raw field availability:

| Condition | Rows | `kernel_class` | `kernel_name` | `dtype` | `generation_seed` | `base_seed` | `sample_index` | `replay_pair_id` | `prompt_sha256` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `none` | 180 | 180 | 180 | 180 | 180 | 0 | 0 | 0 | 0 |
| `G` | 177 | 177 | 177 | 177 | 177 | 0 | 0 | 0 | 0 |
| `C` | 180 | 180 | 180 | 180 | nested 180 | 180 | 0 | nested 180 | nested 180 |
| `G+C` | 177 | 177 | 177 | 177 | nested 177 | 177 | 0 | nested 177 | nested 177 |

Cluster 1 rows do have enough information to construct the deterministic tuple key:

`(kernel_class, kernel_name as kernel_id, dtype, generation_seed as base_seed)`

Cluster 1 rows do not directly contain prompt hashes or replay metadata, but the frozen manifest does. Prompt parity was verified through manifest seed schedules and the current prompt builder.

Recommended identity key:

`(kernel_class, kernel_id/kernel_name, dtype, base_seed normalized from generation_seed/sample_index/base_seed)`

### 3.4 Matched-pair validity

Conclusion: `PAIRED_VALID_WITH_COVERAGE_CAVEAT`

Sample tuple checks:

| Tuple | none | G | C | G+C | Prompt parity |
| --- | --- | --- | --- | --- | --- |
| `elementwise/relu/fp32/0` | present | present | present | present | Current prompt SHA, manifest SHA, and generated metadata SHA all match: `76eb9d064610e428095c402366771d6e6e42a19413815409a7bebb9e6f252109`. |
| `reduction/softmax/fp32/0` | present | present | present | present | Current prompt SHA, manifest SHA, and generated metadata SHA all match: `54173e538f5326f8041af08dc7f98139995941ca62fc7cf73638864c467df6f1`. |
| `matmul/gemm/fp32/0` | present | present | present | present | Current prompt SHA, manifest SHA, and generated metadata SHA all match: `d9b7518e2a0076d7db3ef101a7f101f3f5fdbc18882f4d9ceb02684522f8ccd4`. |
| `matmul/gemm/fp32/5` | present | missing | present | missing | Expected missing G/G+C covered-row gap. |
| `matmul/gemm/bf16/0` | present | missing | present | missing | Expected missing G/G+C covered-row gap. |
| `matmul/gemm/bf16/18` | present | missing | present | missing | Expected missing G/G+C covered-row gap. |

Notes:

- Generated terminal rows may have `generated_metadata.generation_seed != base_seed` when a repair attempt succeeds or terminates after attempt 0. The paired unit remains `base_seed` plus `replay_base_seed`/`replay_generation_seed`, and repair traces preserve attempt-zero visibility.
- `G+C` `elementwise/fp32/base_seed=0` is an example: row `attempt_index=5`, terminal `generation_seed=5`, but `replay_base_seed=0` and `replay_generation_seed=0`.

## 4. Block 2 - statistical methodology

### 4.1 Paired binary test

The analyzer uses exact McNemar-style binomial discordance.

Relevant code:

| File | Function | Finding |
| --- | --- | --- |
| `shared/analysis/factorial.py` | `_mcnemar_exact_p_value(treatment_only, control_only)` | Exact two-sided binomial calculation over discordant pairs. |
| `shared/analysis/factorial.py` | `_paired_comparison_rows(...)` | Computes `discordant_treatment_only`, `discordant_control_only`, exact p-value, paired bootstrap CI, and Holm-adjusted p-values. |
| `shared/analysis/factorial.py` | `_paired_bootstrap_ci(...)` | Bootstraps paired treatment-control differences. |

This is appropriate for low counts and all-zero paired outcomes.

### 4.2 All-zero comparison handling

For both primary functional comparisons:

| Comparison | Pairs | treatment-only | control-only | exact McNemar p | paired bootstrap CI |
| --- | ---: | ---: | ---: | ---: | --- |
| `C vs none` | 180 | 0 | 0 | 1.0 | `[0.0, 0.0]` |
| `G+C vs G` | 177 | 0 | 0 | 1.0 | `[0.0, 0.0]` |

Expected code behavior:

- `_mcnemar_exact_p_value(...)` returns `1.0` when there are zero discordant pairs.
- `_paired_bootstrap_ci(...)` returns a degenerate interval when all paired differences are zero.
- `_factorial_model(...)` returns `not_fit` with `model_outcome_has_single_class` for all-zero functional outcomes.

Actual current run behavior:

- The analyzer does not reach these outputs on raw inputs because it fails earlier on missing Cluster 1 replay metadata.
- An in-memory manifest-metadata patch allowed both paired validations to pass and produced the expected p-values/intervals without writing any artifact.

### 4.3 Confidence intervals for individual rates

The analyzer does not currently emit individual cell-rate confidence intervals.

Current CI support:

- Paired comparison absolute lift: paired bootstrap CI.
- Individual condition rates: point estimates only in `cell_summaries`.

Concern:

- There is no Wilson, Clopper-Pearson, or exact binomial interval for individual 0/n rates in analyzer output.
- For reference, Wilson 95% upper bounds are approximately:
  - `0/180`: 2.09%.
  - `0/177`: 2.12%.

This is an output/documentation gap, not a blocker to paired McNemar testing.

### 4.4 Interaction term

The analyzer does not emit the additive interaction:

`(rate_GC - rate_G) - (rate_C - rate_none)`

Instead, `shared/analysis/factorial.py::_factorial_model(...)` fits or attempts to fit a binary logistic IRLS model and reports the `G:C` coefficient.

Current functional-success result:

- All four functional rates are zero.
- Additive interaction hand-computes to `0.0`.
- Logistic model is `not_fit` due `model_outcome_has_single_class`.

Current compile-success hand-computed additive interaction:

`(4/177 - 3/177) - (0/180 - 0/180) = 1/177 = 0.0056497175`

Concern:

- If thesis/report text expects a rate-scale interaction, the analyzer output needs an explicit additive interaction field in addition to, or instead of, the logistic `G:C` coefficient.

## 5. Block 3 - data flow

### 5.1 Raw to normalized to analyzed counts

| Condition | Raw rows | Bad JSON | Normalized rows | Excluded by normalization | F3 rows | Functional rows used | Compile rows used | Unique tuple keys |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `none` | 180 | 0 | 180 | 0 | 0 | 180 | 180 | 180 |
| `G` | 177 | 0 | 177 | 0 | 0 | 177 | 177 | 177 |
| `C` | 180 | 0 | 180 | 0 | 0 | 180 | 180 | 180 |
| `G+C` | 177 | 0 | 177 | 0 | 5 | 177 | 177 | 177 |

F3 policy:

- F3 rows are not excluded.
- Current analyzer policy treats current `F3_EVAL_PIPELINE` rows as `compile_success=false` and `functional_success=false` unless independent Level 1/2 evidence proves otherwise.

### 5.2 Hand-computed headline rates

| Condition | functional_success | Functional rate | compile_success | Compile rate |
| --- | ---: | ---: | ---: | ---: |
| `none` | 0/180 | 0.000000 | 0/180 | 0.000000 |
| `G` | 0/177 | 0.000000 | 3/177 | 0.016949 |
| `C` | 0/180 | 0.000000 | 0/180 | 0.000000 |
| `G+C` | 0/177 | 0.000000 | 4/177 | 0.022599 |

Failure-code family counts:

| Condition | Success | F0 | F1 | F2 | F3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `none` | 0 | 180 | 0 | 0 | 0 |
| `G` | 3 | 13 | 161 | 0 | 0 |
| `C` | 0 | 180 | 0 | 0 | 0 |
| `G+C` | 0 | 12 | 156 | 4 | 5 |

Detailed failure codes:

| Condition | Counts |
| --- | --- |
| `none` | `F0_PARSE=180` |
| `G` | `SUCCESS=3`, `F1_RUNTIME=152`, `F1_COMPILE=9`, `F0_PARSE=13` |
| `C` | `F0_PARSE=180` |
| `G+C` | `F2_NUMERIC_NAN=4`, `F1_RUNTIME=146`, `F1_COMPILE=10`, `F0_PARSE=12`, `F3_EVAL_PIPELINE=5` |

### 5.3 Matched-pair counts

| Comparison | Expected | Observed | Missing control | Missing treatment |
| --- | ---: | ---: | --- | --- |
| `C vs none` | 180 | 180 | none | none |
| `G+C vs G` | 177 | 177 | none | none |
| Four-way `none/G/C/G+C` | 177 | 177 | n/a | n/a |

Full-grid missing rows:

| Condition | Missing vs 180-grid |
| --- | --- |
| `none` | none |
| `G` | `matmul/gemm/fp32/5`, `matmul/gemm/bf16/0`, `matmul/gemm/bf16/18` |
| `C` | none |
| `G+C` | `matmul/gemm/fp32/5`, `matmul/gemm/bf16/0`, `matmul/gemm/bf16/18` |

### 5.4 Grammar funnel metrics

| Condition | Rows | gbnf_parse_valid | semantic_valid | grammar_valid | `grammar_valid == gbnf_parse_valid and semantic_valid` mismatches |
| --- | ---: | --- | --- | --- | ---: |
| `G` | 177 | `true=105`, `false=72` | `true=49`, `false=128` | `true=49`, `false=128` | 0 |
| `G+C` | 177 | `true=100`, `false=77` | `true=52`, `false=125` | `true=52`, `false=125` | 0 |

Rejection-layer distributions:

| Condition | Distribution |
| --- | --- |
| `G` | `gbnf_parse=72`, `semantic_validator=56`, `None=49` |
| `G+C` | `gbnf_parse=77`, `semantic_validator=48`, `None=52` |

Stop reasons:

| Condition | Distribution |
| --- | --- |
| `G` | `eos_token=105`, `max_new_tokens=72` |
| `G+C` | `eos_token=100`, `max_new_tokens=77` |

Inactive grammar checks:

- `none`: raw `grammar_active=false` for 180/180, no grammar variant.
- `C`: no top-level or nested grammar-active evidence; generated metadata has no grammar variant.

## 6. Block 4 - methodology alignment

### 6.1 Comparison structure

| Comparison | Response variable | Pairing fields | Statistical test | Status | Multiple-comparison correction |
| --- | --- | --- | --- | --- | --- |
| `C vs none` | `functional_success` | `kernel_class`, `kernel_id`, `dtype`, `base_seed` | Exact McNemar + paired bootstrap lift CI | Primary C effect, supported after metadata fix | Holm across paired comparison rows |
| `G+C vs G` | `functional_success` | `kernel_class`, `kernel_id`, `dtype`, `base_seed` | Exact McNemar + paired bootstrap lift CI | Primary C conditional-on-G effect, supported after metadata fix | Holm across paired comparison rows |
| `G vs none` | `compile_success` | Same tuple key possible | Not emitted by current analyzer as paired comparison | Secondary structural G effect, output gap | Not applicable today |
| `G+C vs C` | `compile_success` | Same tuple key possible over 177 common rows | Not emitted by current analyzer as paired comparison | Secondary structural combined effect, output gap | Not applicable today |
| Functional interaction | `functional_success` | Condition-level tuple outcomes | Logistic IRLS `G:C`, not additive rate DiD | Model not fit because all outcomes are false | n/a |
| Compile interaction | `compile_success` | Condition-level tuple outcomes | Logistic IRLS `G:C`, not additive rate DiD | Diagnostic only; additive hand-compute is 0.00565 | n/a |

Excluded comparisons in current analyzer output:

- `G vs none` paired compile-success lift.
- `G+C vs C` paired compile-success lift.
- Unpaired Fisher exact or chi-squared comparisons.
- P-containing comparisons.
- Additive rate-scale interaction terms.

### 6.2 Failure-mode breakdown availability

Available now from raw or normalized data:

- F0/F1/F2/F3/success counts per condition.
- Per kernel/dtype summaries through analyzer `cell_summaries`.
- For `G` and `G+C`, rejection-layer and grammar funnel metrics.
- Stop-reason distributions.

Current analyzer output support:

- `diagnostics.grammar_acceptance_summary` includes grammar-valid, GBNF, and semantic rates for grammar conditions.
- `diagnostics.rejection_layer_breakdown` is available for G-containing conditions.
- `diagnostics.stop_reason_breakdown` is available.
- Failure-code family breakdown is not a first-class analyzer output table today, but can be added without artifact changes.

### 6.3 F3_EVAL_PIPELINE documentation

The analyzer code implements the current strict F3 policy, but report output should make the policy explicit:

- `F3_EVAL_PIPELINE` rows are malformed/infrastructure eval-pipeline failures unless independent Level 1/2 evidence proves compile success.
- The five current G+C F3 rows count as `compile_success=false` and `functional_success=false`.
- F3 rows remain in denominators.

If the current output cannot include this note, flag as documentation/output gap.

## 7. Block 5 - recommended fix path

Chosen option: **Option B - Use tuple-based matching key instead of `replay_pair_id`.**

Rationale:

- The analyzer already joins paired rows by explicit tuple identity, not `replay_pair_id`.
- Raw Cluster 1 artifacts have sufficient tuple identity under different field names.
- The real `replay_pair_id` recipe is just an alias for `(kernel_class, dtype, base_seed)`.
- Prompt parity can be verified from the frozen manifest and current prompt builder even though raw Cluster 1 rows do not carry prompt hashes.
- Deriving only `replay_pair_id` for Cluster 1 would not be enough because current `_validate_pair_metadata_columns(...)` also requires replay seeds, prompt hash, model id, temperature, and max token budget.
- Switching to unpaired analysis is not justified because tuple/prompt/seed parity is verifiable for covered rows.

Exact fields to use:

- `kernel_class`
- `kernel_id`, falling back to `kernel_name`
- `dtype`
- `base_seed`, normalized from first present of `base_seed`, `generation_seed`, `seed`, `sample_index`

Generated-row metadata checks to retain:

- `replay_base_seed == base_seed`
- `replay_generation_seed == base_seed` for attempt-zero generated rows
- `replay_control_condition` is `none` for `C`, `G` for `G+C`
- `prompt_sha256` equals manifest/current prompt hash for `(kernel_class, dtype)`
- known model/tokenizer revision parity when frozen manifest revisions are known

Future fix brief outline:

1. Update `shared/analysis/factorial.py::_validate_pair_metadata_columns(...)` to support direct Cluster 1 control rows without `replay_metadata`.
2. Keep tuple-key matching as the primary pairing mechanism.
3. For direct Cluster 1 controls, derive a control metadata view from tuple fields plus frozen manifest schedule when a source path/input role identifies `none` or `G`.
4. Do not modify JSONL artifacts.
5. Preserve strict generated-row metadata checks.
6. Add tests for raw Cluster 1 controls paired with C2 generated rows.
7. Add output notes for coverage caveat, F3 policy, and direct Cluster 1 control normalization.
8. Consider adding additive interaction and individual-rate CI outputs.

Risks:

- If future replay manifests change `replay_pair_id` format, tuple-key matching remains stable.
- If prompt construction changes without manifest update, prompt-parity validation should fail loudly.
- If using only tuple keys without prompt validation, pairing could become too permissive. The fix should keep prompt parity checks through manifest/current prompt hashes.

## 8. Risks

| Risk | Status | Impact |
| --- | --- | --- |
| Pairing risk | Low for covered rows | Tuple identity, manifest schedules, and generated metadata agree. |
| Prompt parity risk | Low but should remain guarded | Raw Cluster 1 rows lack prompt hashes; manifest/current prompt hash validation is required. |
| All-zero statistics risk | Low | Exact McNemar handles zero discordance with p=1.0; model correctly reports not fit. |
| Coverage caveat risk | Medium | 177/180 G and G+C coverage must be explicit; missing rows must be skipped, not imputed. |
| F3 handling risk | Medium | Five G+C F3 rows remain denominator failures; output needs explicit policy note. |
| Individual CI risk | Medium | No individual rate CIs are emitted. |
| Interaction interpretation risk | Medium | Analyzer reports logistic `G:C`, not additive rate interaction. |
| Documentation risk | Medium | Prior audits and docs have superseded blocker language. |

## 9. Next step

Write the fix brief for **tuple-based matching with manifest-backed prompt parity validation**.

Do not switch to unpaired analysis. Do not rewrite artifacts. Do not derive only `replay_pair_id` unless the fix also addresses the other required metadata fields or relaxes them for direct Cluster 1 controls.

After that fix, run the analyzer directly to produce:

`outputs/analysis/factorial_2x2_preliminary.json`

Then add output documentation for:

- 177/180 coverage caveat.
- F3 denominator policy.
- all-zero functional-success interpretation.
- individual-rate CI method if added.
- additive interaction if added.

## 10. Appendix

### Commands run

Static searches:

```bash
rg "replay_pair_id|pair_id|matched|pair|base_seed|generation_seed|sample_index|prompt_sha|prompt_hash|prompt_sha256|kernel_class|dtype" shared cluster1 cluster2 tests audits outputs
rg -l "replay_pair_id|pair_id|matched|pair|base_seed|generation_seed|sample_index|prompt_sha|prompt_hash|prompt_sha256|kernel_class|dtype" shared cluster1 cluster2 shared/tests cluster1/tests cluster2/tests audits outputs
rg "mcnemar|McNemar|statsmodels|contingency|bootstrap|Wilson|Clopper|confidence|CI|interaction|odds|paired|Fisher|chi" shared tests cluster2 cluster1
rg -l "mcnemar|McNemar|statsmodels|contingency|bootstrap|Wilson|Clopper|confidence|CI|interaction|odds|paired|Fisher|chi" shared cluster1 cluster2 shared/tests cluster1/tests cluster2/tests
rg "functional_success|compile_success|failure_code|F0_|F1_|F2_|F3_|F3_EVAL_PIPELINE|normaliz|factorial" shared cluster1 cluster2 tests audits
rg -l "functional_success|compile_success|failure_code|F0_|F1_|F2_|F3_|F3_EVAL_PIPELINE|normaliz|factorial" shared cluster1 cluster2 shared/tests cluster1/tests cluster2/tests audits
rg -l "grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|grammar_active|grammar_variant|generated_metadata" shared cluster1 cluster2 shared/tests cluster1/tests cluster2/tests outputs
rg -l "baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|c_paper_n20_l4|g_plus_c_paper_n20_l4|factorial_2x2_preliminary" .
```

Notes:

- Commands using top-level `tests` returned exit code 2 because this repository has no top-level `tests/` directory; results were still returned from existing paths.
- Searches were rerun over `shared/tests`, `cluster1/tests`, and `cluster2/tests`.

Validation and analysis:

```bash
.venv/bin/python -m shared.analysis.factorial --help
.venv/bin/python -m pytest shared/tests -k "factorial or replay_pair_id or pairing or mcnemar or bootstrap or Wilson or interaction" -q
```

Result:

- Analyzer help passed.
- Focused tests passed: 71 passed, 482 deselected.

Read-only Python checks used `.venv/bin/python` for:

- artifact JSON parse and schema field inspection,
- analyzer dry validation,
- raw/normalized count tables,
- hand-computed rates and failure counts,
- matched-pair counts,
- grammar funnel metrics,
- manifest replay schedule checks,
- prompt parity checks,
- in-memory metadata-patched analyzer validation.

No Python command wrote artifacts.

### Sample rows inspected

Representative tuple checks:

- `elementwise/relu/fp32/base_seed=0`
- `reduction/softmax/fp32/base_seed=0`
- `matmul/gemm/fp32/base_seed=0`
- `matmul/gemm/fp32/base_seed=5`
- `matmul/gemm/bf16/base_seed=0`
- `matmul/gemm/bf16/base_seed=18`

Artifacts inspected:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
- `outputs/cluster2/c_paper_n20_l4.jsonl`
- `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`
- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`

### File paths and functions inspected

Primary analyzer:

- `shared/analysis/factorial.py`
- `load_results(...)`
- `load_result_paths(...)`
- `normalize_result_rows(...)`
- `analyze_factorial(...)`
- `validate_paired_replay_dataframe(...)`
- `paired_replay_summary(...)`
- `_paired_comparison_rows(...)`
- `_paired_bootstrap_ci(...)`
- `_mcnemar_exact_p_value(...)`
- `_factorial_model(...)`
- `_validate_pair_metadata_columns(...)`
- `_pair_metadata_frame(...)`
- `_validate_generated_seed_metadata(...)`
- `_ensure_pair_identity_columns(...)`

Shared helpers:

- `shared/eval/aggregation.py`
- `validate_paired_replay_alignment(...)`
- `matched_cell_key(...)`
- `shared/eval/adapter_cluster1.py`
- `eval_result_from_generation_result(...)`
- `shared/eval/failure_taxonomy.py`
- `canonical_failure_code_from_compile_error(...)`
- `classify_failure(...)`

Replay and C2 generation:

- `cluster2/replay/manifest.py`
- `ReplaySeedScheduleEntry`
- `replay_seed_schedule_for_condition(...)`
- `_entries_for_schedule_record(...)`
- `_validate_schedule_entry_matches_row(...)`
- `_sample_identity_from_row(...)`
- `cluster2/replay/cluster1_controls.py`
- `_deserialize_replay_row(...)`
- `_sample_identity_from_raw_row(...)`
- `_validate_seed_schedule_cell_structure(...)`
- `_build_replay_candidate(...)`
- `cluster2/experiments/run_cluster2_modal.py`
- `_preflight_paired_generation_schedules(...)`
- `_paired_replay_control_condition(...)`
- `_paired_generation_seed(...)`
- `_validate_generation_pairing_context(...)`
- `_run_generated_condition_candidate(...)`
- `_eval_identity(...)`
- `_build_base_prompt(...)`

Result schemas:

- `cluster1/results/dataclass.py`
- `GenerationResult`
- `cluster2/results/dataclass.py`
- `Cluster2ReplayRowMetadata`
- `Cluster2GeneratedRowMetadata`
- `Cluster2EvalRow`
- `replay_control_row(...)`
- `generated_row(...)`

Relevant prior reports:

- `audits/factorial_cluster1_functional_success_normalization_fix_report.md`
- `audits/factorial_cluster2_compile_success_normalization_fix_report.md`
- `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`
- `audits/repository_documentation_methodology_readiness_audit.md`
- `audits/factorial_2x2_preliminary_analysis_report.md`
