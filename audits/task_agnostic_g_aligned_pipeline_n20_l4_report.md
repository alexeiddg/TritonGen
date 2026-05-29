# Cluster 1 Task-Agnostic G n=20 L4 Report

## 1. Executive Summary

Run status: **N20_RUN_FAILED**.

The approved Cluster 1 task-agnostic G n=20 Modal L4 run was invoked once with `max_new_tokens=2048`, but the Modal runner exited non-zero after writing only 177 of the expected 180 rows. The sidecar status is `failed_partial`, with `infrastructure_failures=3`.

Artifact path: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

Expected row count: 180

Observed row count: 177

Strict metadata gate: **FAIL**. The validator reported one row-count failure and three missing cells:

- `condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=0`
- `condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=18`
- `condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=fp32 seed=5`

Partial overall compile_success rate: 3/177 = 1.69%.

Partial overall grammar_valid rate: 49/177 = 27.68%.

Main observed bottlenecks in persisted rows are token-budget termination and grammar rejection in reduction/matmul. However, the run is not a valid Cluster 1 task-agnostic G reporting artifact because three rows are missing.

Cluster 1 task-agnostic G reporting validity: **invalid / not reportable as n=20**.

## 2. Run Provenance

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class all --n 20 --max-new-tokens 2048 --output outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl --modal-generation-gpu L4 --overwrite
```

Modal app URL printed by CLI:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-fLaBWiri43TkmLMqGA02X1
```

Sidecar provenance:

| Field | Value |
|---|---|
| model_id | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` |
| model_revision | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| tokenizer_revision | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| tokenizer_revision_policy | `same_repo_model_revision` |
| max_new_tokens | `2048` |
| Modal GPU | `L4` |
| condition | `G` |
| grammar_variant | `task_agnostic` |
| kernel_class | `all` |
| n | `20` |
| started_at_utc | `2026-05-19T05:55:12.458481+00:00` |
| finished_at_utc | `2026-05-19T13:15:18.076043+00:00` |
| sidecar status | `failed_partial` |
| expected_rows | `180` |
| written_rows | `177` |
| infrastructure_failures | `3` |

Persisted-row provenance:

| Field | Value |
|---|---|
| grammar_path | `cluster1/grammar/triton_kernel_agnostic.gbnf` |
| grammar_sha | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` |
| xgrammar_version | `0.1.33` |
| transformers_version | `4.47.1` |
| tokenizers_version | `0.21.1` |
| modal_image_sha | `unknown` on 177/177 persisted rows |

The `modal_image_sha` field is present but unknown. The strict failure in this run is the missing row count, not model/tokenizer provenance.

## 3. Artifact Integrity

Expected row count: 180.

Observed row count: 177.

Strict validator result: **FAIL**.

Validator failure summary:

```text
Cluster 1 result validation: FAIL
row_count: 177 expected=180
row_count_failures: 1; expected 180 rows; observed 177
missing_cells: 3; condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=0 | condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=18 | condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=fp32 seed=5
generation_metadata_failures: 0
invariant_failures: 0
duplicate_identities: 0
```

Kernel/dtype cell counts:

| kernel_class | dtype | observed rows | expected rows |
|---|---:|---:|---:|
| elementwise | bf16 | 20 | 20 |
| elementwise | fp16 | 20 | 20 |
| elementwise | fp32 | 20 | 20 |
| matmul | bf16 | 18 | 20 |
| matmul | fp16 | 20 | 20 |
| matmul | fp32 | 19 | 20 |
| reduction | bf16 | 20 | 20 |
| reduction | fp16 | 20 | 20 |
| reduction | fp32 | 20 | 20 |

Required field check on persisted rows: PASS, 0 missing required fields.

Tokenizer revision check on persisted rows: PASS, 177/177 non-unknown.

Model revision check on persisted rows: PASS, 177/177 non-unknown.

Grammar SHA check on persisted rows: PASS, 177/177 match the expected grammar SHA.

Grammar-valid invariant check on persisted rows: PASS, 0 invariant failures.

Because the artifact is missing three expected identities, these checks do not make it a valid n=20 artifact.

## 4. Overall Metrics Across Persisted Rows

These metrics are descriptive only because the artifact is incomplete.

| Metric | Count | Rate |
|---|---:|---:|
| compile_success | 3/177 | 1.69% |
| grammar_valid | 49/177 | 27.68% |
| gbnf_parse_valid | 105/177 | 59.32% |
| semantic_valid | 49/177 | 27.68% |

Failure-code distribution:

| failure_code | Count |
|---|---:|
| `F1_RUNTIME` | 152 |
| `F0_PARSE` | 13 |
| `F1_COMPILE` | 9 |
| null | 3 |

Compile-error-type distribution:

| compile_error_type | Count |
|---|---:|
| `RuntimeError` | 152 |
| `SignatureError` | 13 |
| `CompilationError` | 9 |
| null | 3 |

Stop-reason distribution:

| stop_reason | Count |
|---|---:|
| `eos_token` | 105 |
| `max_new_tokens` | 72 |

Rejection-layer distribution:

| rejection_layer | Count |
|---|---:|
| `gbnf_parse` | 72 |
| `semantic_validator` | 56 |
| null | 49 |

## 5. Metrics By Kernel/Dtype

| kernel_class | dtype | rows | compile_success_count | compile_success_rate | grammar_valid_count | grammar_valid_rate | gbnf_parse_valid_rate | semantic_valid_rate | dominant rejection_layer | dominant stop_reason | dominant failure_code |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| elementwise | bf16 | 20 | 0 | 0.00% | 16 | 80.00% | 100.00% | 80.00% | null (16) | eos_token (20) | F1_RUNTIME (20) |
| elementwise | fp16 | 20 | 0 | 0.00% | 19 | 95.00% | 100.00% | 95.00% | null (19) | eos_token (20) | F1_RUNTIME (20) |
| elementwise | fp32 | 20 | 3 | 15.00% | 14 | 70.00% | 100.00% | 70.00% | null (14) | eos_token (20) | F1_COMPILE (9) |
| matmul | bf16 | 18 | 0 | 0.00% | 0 | 0.00% | 50.00% | 0.00% | semantic_validator (9) | max_new_tokens (9) | F1_RUNTIME (14) |
| matmul | fp16 | 20 | 0 | 0.00% | 0 | 0.00% | 50.00% | 0.00% | semantic_validator (10) | max_new_tokens (10) | F1_RUNTIME (15) |
| matmul | fp32 | 19 | 0 | 0.00% | 0 | 0.00% | 68.42% | 0.00% | semantic_validator (13) | eos_token (13) | F1_RUNTIME (18) |
| reduction | bf16 | 20 | 0 | 0.00% | 0 | 0.00% | 15.00% | 0.00% | gbnf_parse (17) | max_new_tokens (17) | F1_RUNTIME (19) |
| reduction | fp16 | 20 | 0 | 0.00% | 0 | 0.00% | 10.00% | 0.00% | gbnf_parse (18) | max_new_tokens (18) | F1_RUNTIME (19) |
| reduction | fp32 | 20 | 0 | 0.00% | 0 | 0.00% | 40.00% | 0.00% | gbnf_parse (12) | max_new_tokens (12) | F1_RUNTIME (19) |

## 6. Metrics By Kernel Class

| kernel_class | rows | compile_success_count | compile_success_rate | grammar_valid_count | grammar_valid_rate | stop_reason distribution | rejection_layer distribution |
|---|---:|---:|---:|---:|---:|---|---|
| elementwise | 60 | 3 | 5.00% | 49 | 81.67% | eos_token: 60 | null: 49; semantic_validator: 11 |
| reduction | 60 | 0 | 0.00% | 0 | 0.00% | max_new_tokens: 47; eos_token: 13 | gbnf_parse: 47; semantic_validator: 13 |
| matmul | 57 | 0 | 0.00% | 0 | 0.00% | eos_token: 32; max_new_tokens: 25 | semantic_validator: 32; gbnf_parse: 25 |

## 7. Metrics By Dtype

| dtype | rows | compile_success_count | compile_success_rate | grammar_valid_count | grammar_valid_rate | failure_code distribution |
|---|---:|---:|---:|---:|---:|---|
| bf16 | 58 | 0 | 0.00% | 16 | 27.59% | F1_RUNTIME: 53; F0_PARSE: 5 |
| fp16 | 60 | 0 | 0.00% | 19 | 31.67% | F1_RUNTIME: 54; F0_PARSE: 6 |
| fp32 | 59 | 3 | 5.08% | 14 | 23.73% | F1_RUNTIME: 45; F1_COMPILE: 9; F0_PARSE: 2; null: 3 |

## 8. Rejection-Layer Analysis

Persisted rows show rejection dominated by `gbnf_parse` and `semantic_validator`:

- `gbnf_parse`: 72/177
- `semantic_validator`: 56/177
- null: 49/177

The null rejection-layer rows align with grammar-valid rows. On persisted rows, the invariant `grammar_valid == (gbnf_parse_valid and semantic_valid)` held for every row.

Elementwise is the only kernel class with grammar-valid rows: 49/60. Reduction and matmul have 0 grammar-valid persisted rows. Reduction is primarily parse-rejected, with 47/60 rows at `gbnf_parse`. Matmul is split between semantic rejection and parse rejection, with 32/57 semantic-validator rejections and 25/57 parse rejections.

No Python AST rejection layer appears in the persisted metadata distribution. Runtime and compile outcomes are reflected in `compile_error_type` and `failure_code`, not `rejection_layer`.

## 9. Stop-Reason Analysis

Persisted stop-reason distribution:

- `eos_token`: 105/177 = 59.32%
- `max_new_tokens`: 72/177 = 40.68%

Under `max_new_tokens=2048`, token-budget truncation remains material. It is concentrated in reduction and matmul:

- reduction: 47/60 rows stopped at `max_new_tokens`
- matmul: 25/57 persisted rows stopped at `max_new_tokens`
- elementwise: 0/60 rows stopped at `max_new_tokens`

By cell:

- reduction/fp16: 18/20 max_new_tokens
- reduction/bf16: 17/20 max_new_tokens
- reduction/fp32: 12/20 max_new_tokens
- matmul/fp16: 10/20 max_new_tokens
- matmul/bf16: 9/18 max_new_tokens
- matmul/fp32: 6/19 max_new_tokens

Compared to the earlier n=5 2048 run, where 18/45 rows stopped at `max_new_tokens`, this partial n=20 artifact has 72/177 persisted rows stopped at `max_new_tokens`. The truncation rate is therefore similar at roughly 40%, but this comparison is descriptive because the n=20 artifact is incomplete.

2560 should be considered only after the infrastructure failure is understood. A valid n=20 cannot be frozen from this artifact.

## 10. Failure-Code Analysis

Canonical failure-code distribution on persisted rows:

- `F1_RUNTIME`: 152/177
- `F0_PARSE`: 13/177
- `F1_COMPILE`: 9/177
- null: 3/177

The three null failure-code rows are the three compile_success rows.

Most non-compiling persisted rows are runtime failures. `F0_PARSE` is concentrated in reduction/matmul and aligns with parse-surface failures. `F1_COMPILE` appears only in elementwise/fp32 in this run.

Where both fields exist, `failure_code` and `compile_error_type` agree at a high level:

- `CompilationError` corresponds to `F1_COMPILE`.
- `RuntimeError` and `SignatureError` correspond to `F1_RUNTIME`.
- null `compile_error_type` corresponds to compile_success rows with null `failure_code`.

The artifact failure is not caused by these persisted row-level compile/runtime failures. It is caused by three missing identities and sidecar `infrastructure_failures=3`.

## 11. Compile-Success Analysis

Persisted compile_success: 3/177 = 1.69%.

All three compile successes are in `elementwise/fp32`:

- elementwise/fp32: 3/20 = 15.00%
- every other observed kernel/dtype cell: 0 compile successes

Cells with 0/20 compile success:

- elementwise/bf16
- elementwise/fp16
- matmul/fp16
- reduction/bf16
- reduction/fp16
- reduction/fp32

Cells with 0 compile success and incomplete counts:

- matmul/bf16: 0/18 persisted
- matmul/fp32: 0/19 persisted

Cells where grammar_valid is high but compile_success is low:

- elementwise/fp16: 19/20 grammar_valid, 0/20 compile_success
- elementwise/bf16: 16/20 grammar_valid, 0/20 compile_success
- elementwise/fp32: 14/20 grammar_valid, 3/20 compile_success

For persisted rows, compile failures look like model/output behavior rather than a metadata schema problem. The missing rows are an infrastructure/completion problem and invalidate the artifact.

## 12. Grammar-Validity Analysis

Persisted grammar_valid: 49/177 = 27.68%.

Persisted gbnf_parse_valid: 105/177 = 59.32%.

Persisted semantic_valid: 49/177 = 27.68%.

Grammar-valid but compile-failing rows:

- grammar_valid rows: 49
- compile_success rows: 3
- grammar-valid compile-failing rows: 46

Grammar-invalid rows by rejection layer:

- `gbnf_parse`: 72
- `semantic_validator`: 56

Grammar validity is entirely concentrated in elementwise rows. Reduction and matmul produced no grammar-valid persisted rows.

## 13. Masked-Token-Rate Analysis

Masked-token-rate is a masking diagnostic, not G-acceptance evidence.

Overall persisted masked-token-rate:

| count | min | max | mean | median |
|---:|---:|---:|---:|---:|
| 177 | 0.5982023457485418 | 0.8518569552403374 | 0.7829152278938922 | 0.7838772121904675 |

By kernel/dtype:

| kernel_class | dtype | count | min | max | mean | median |
|---|---:|---:|---:|---:|---:|---:|
| elementwise | bf16 | 20 | 0.766574990461868 | 0.8052904571324869 | 0.7993461337526648 | 0.800926035799477 |
| elementwise | fp16 | 20 | 0.800961602488248 | 0.808260517639021 | 0.8044959930831451 | 0.8048394063368022 |
| elementwise | fp32 | 20 | 0.7995049773952356 | 0.8518569552403374 | 0.8432543984934411 | 0.8468467822943346 |
| matmul | bf16 | 18 | 0.7348412141561378 | 0.8093854014059166 | 0.754443042393169 | 0.7515200573185878 |
| matmul | fp16 | 20 | 0.7290882468131753 | 0.8110259433962265 | 0.7560017611605409 | 0.7466869942764087 |
| matmul | fp32 | 19 | 0.7466206662984006 | 0.8226288655293841 | 0.7893271551691955 | 0.7949395642326282 |
| reduction | bf16 | 20 | 0.5982023457485418 | 0.8074332458736394 | 0.7568579905391232 | 0.7545663596002341 |
| reduction | fp16 | 20 | 0.7432273967498882 | 0.7890398225056997 | 0.7669296588624138 | 0.7695887482126151 |
| reduction | fp32 | 20 | 0.747795541679819 | 0.8056138149392991 | 0.7730542954050297 | 0.7766680481400134 |

## 14. Comparison Against n=5

The previous aligned n=5 run was valid and had:

- compile_success: 1/45 = 2.22%
- grammar_valid: 12/45 = 26.67%
- stop_reason: `eos_token`: 27; `max_new_tokens`: 18
- rejection_layer: null: 12; `gbnf_parse`: 18; `semantic_validator`: 15

The partial n=20 persisted rows have:

- compile_success: 3/177 = 1.69%
- grammar_valid: 49/177 = 27.68%
- stop_reason: `eos_token`: 105; `max_new_tokens`: 72
- rejection_layer: null: 49; `gbnf_parse`: 72; `semantic_validator`: 56

The partial n=20 pattern is broadly similar to n=5 in grammar_valid rate and token-budget pressure, but the n=20 artifact is not valid. It cannot confirm or revise the n=5 estimate as a complete n=20 result.

No statistical-significance claim should be made from this failed partial run.

## 15. Confidence Interval / Uncertainty Estimate

The following Wilson intervals are computed over the 177 persisted rows only. They are descriptive and not valid as final n=20 evidence because the artifact is incomplete and rows are grouped by kernel/dtype rather than fully IID.

| Metric | Estimate | 95% Wilson interval |
|---|---:|---:|
| compile_success | 3/177 = 1.69% | [0.58%, 4.86%] |
| grammar_valid | 49/177 = 27.68% | [21.62%, 34.70%] |

## 16. Methodological Interpretation

This run attempted task-agnostic G under the aligned Cluster 1 pipeline.

This is not template G.

This is grammar-guided decoding plus offline semantic validation.

`grammar_active=true` means constrained decoding was attempted.

`grammar_valid=true` is G-acceptance evidence.

`compile_success=true` is strict compile evidence only.

`masked_token_rate` is diagnostic only.

Because the artifact is incomplete, none of the persisted-row rates should be treated as a valid full n=20 estimate.

## 17. Go/No-Go Recommendation For Next Experiment

Recommendation: **BLOCK_CLUSTER1_G_REPORTING**.

Rationale:

- The Modal command exited non-zero.
- The artifact has 177/180 rows.
- The strict metadata/result gate failed.
- Three expected identities are missing.
- The sidecar reports `failed_partial` and `infrastructure_failures=3`.

The persisted rows have valid model/tokenizer provenance and grammar metadata, but completeness is a hard reporting requirement.

## 18. Remaining Risks

Statistical uncertainty:

- No valid n=20 estimate exists from this run.
- Partial Wilson intervals are descriptive only.

Token-budget risk:

- Among persisted rows, 72/177 stopped at `max_new_tokens`.
- Truncation remains concentrated in reduction and matmul.

Methodology risk:

- Freezing or reporting this artifact would mix complete and incomplete cells.
- The missing rows are all in matmul, creating a kernel-specific completeness bias.

Infrastructure/provenance risk:

- Tokenizer and model revision provenance are populated on persisted rows.
- `modal_image_sha` is present but `unknown` on persisted rows.
- Modal/runner recorded `infrastructure_failures=3`, causing incomplete output.

Reporting/documentation follow-ups:

- Document that this n=20 attempt failed and must not be used as the Cluster 1 n=20 artifact.
- Preserve the partial artifact as failed-run evidence unless the project policy says to archive failed outputs elsewhere.

## 19. Appendix

Pre-run gate commands:

```bash
git status --short
.venv/bin/python -c '... tokenizer revision smoke artifact check ...'
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl --condition G --kernel-class all --n 5 --grammar-variant task_agnostic --require-generation-metadata
.venv/bin/python -c '... grammar hash check ...'
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v
.venv/bin/python -m cluster1.experiments.run_cluster1_modal --help
.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_run_cluster1_modal.py cluster1/tests/test_validate_cluster1_results.py cluster1/tests/test_compile_check.py cluster1/tests/test_signature_gate_consistency.py shared/tests/test_shape_schedule_consistency.py shared/tests/test_eval_failure_taxonomy.py -q
```

Pre-run gate outputs:

```text
TOKENIZER_REVISION_SMOKE_CONFIRMED
Cluster 1 n=5 result validation: PASS
grammar_sha 7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32
cluster2 hash gate: 1 passed
focused local validation: 239 passed, 7 skipped
```

Modal run command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class all --n 20 --max-new-tokens 2048 --output outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl --modal-generation-gpu L4 --overwrite
```

Modal terminal failure:

```text
run incomplete requested_rows=180 written_rows=177 infrastructure_failures=3
Stopping app - uncaught exception raised locally: SystemExit(1).
```

Strict validation command:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl --condition G --kernel-class all --n 20 --grammar-variant task_agnostic --require-generation-metadata
```

Strict validation output:

```text
Cluster 1 result validation: FAIL
input: outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
row_count: 177 expected=180
condition_coverage: expected=['G'] observed=['G']
kernel_coverage: expected=['elementwise', 'reduction', 'matmul'] observed=['elementwise', 'matmul', 'reduction']
grammar_variant_coverage: expected=['task_agnostic'] observed=['task_agnostic']
dtype_coverage: expected=['fp32', 'fp16', 'bf16'] observed=['bf16', 'fp16', 'fp32']
file_failures: 0
row_count_failures: 1; expected 180 rows; observed 177
deserialization_failures: 0
invariant_failures: 0
masked_token_rate_failures: 0
generation_metadata_failures: 0
compile_results_by_dtype_failures: 0
missing_cells: 3; condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=0 | condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=bf16 seed=18 | condition=G grammar_variant=task_agnostic kernel_class=matmul dtype=fp32 seed=5
unexpected_cells: 0
duplicate_identities: 0
seed_failures: 0
sample_size_failures: 0
```

Row-count summary:

```text
expected_rows: 180
written_rows: 177
missing_rows: 3
sidecar_status: failed_partial
infrastructure_failures: 3
```

Exact artifact path:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
```

Exact sidecar path:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl.meta.json
```

Exact report path:

```text
audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md
```
