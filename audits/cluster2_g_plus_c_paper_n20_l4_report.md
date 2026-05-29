# Cluster 2 G+C Paper n=20 L4 Report

## 1. Executive summary

Run status: `FAILED_PARTIAL_MODAL_RUN`.

The single requested G+C paper-scale Modal run was launched once and failed mid-execution with:

```text
RuntimeError: correctness payload did not contain correctness_result
```

Artifact path: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

Observed row count: 91 persisted rows.

Nominal expected row count: 180.

Expected row count under known replay coverage warning: 177.

Partial functional_success rate: 0/91 = 0.0000.

Partial compile_success rate: 5/91 = 0.0549.

Partial F2 reached count: 5/91.

Main persisted failure mode: `F1_RUNTIME` with 75/91 rows.

G+C paper-scale artifact validity: not valid for aggregation. The partial rows are JSONL-valid and metadata-valid, but the run did not complete the matched 177-row schedule.

## 2. Command and environment

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --grammar-variant task_agnostic --max-new-tokens 2048 --output outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

Modal run URL:

`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-YJqForXjPOxdB0wn1ix8hD`

Generation GPU: L4.

Eval GPU: L4.

`max_new_tokens`: 2048.

`repair_budget`: 5.

`model_id`: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`.

`model_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.

`tokenizer_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.

Persisted package and image metadata:

| field | value |
|---|---|
| `modal_image_sha` | `im-tU3VQyAbFvrusOxtlwspCN` |
| `transformers_version` | `4.47.1` |
| `tokenizers_version` | `0.21.1` |
| `xgrammar_version` | `0.1.33` |

## 3. Artifact integrity and durability

The partial artifact exists and is parseable JSONL.

| check | result |
|---|---:|
| raw non-empty lines | 91 |
| valid JSON rows | 91 |
| bad JSON lines | 0 |
| ends with newline | true |
| condition rows | `G+C: 91` |

Cell coverage in the partial artifact:

| kernel_class | dtype | rows |
|---|---|---:|
| elementwise | bf16 | 20 |
| elementwise | fp16 | 20 |
| elementwise | fp32 | 20 |
| reduction | fp16 | 11 |
| reduction | fp32 | 20 |

Scheduled rows not reached before the failure: 86/177.

Unreached scheduled rows by cell:

| kernel_class | dtype | missing scheduled rows |
|---|---|---:|
| reduction | fp16 | 9 |
| reduction | bf16 | 20 |
| matmul | fp32 | 19 |
| matmul | fp16 | 20 |
| matmul | bf16 | 18 |

Coverage warning status: the registered task-agnostic G replay control remains explicitly incomplete at 177/180, with `COVERAGE_WARNING_SKIP_MISSING`.

## 4. G+C condition integrity

All 91 persisted rows are `condition == "G+C"`.

| field | observed |
|---|---|
| `generation_mode` | `new_c2_generation_with_G_adapter` for 91/91 |
| `grammar_active` | `true` for 91/91 |
| `grammar_variant` | `task_agnostic` for 91/91 |
| `grammar_path` | `cluster1/grammar/triton_kernel_agnostic.gbnf` for 91/91 |
| `grammar_sha` | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` for 91/91 |

`template_upper_bound` was not used in any persisted row.

## 5. Metadata/provenance validation

The partial rows preserve required nested `generated_metadata` and top-level result fields.

Missing or unknown required metadata count: 0 across persisted rows.

Required provenance fields were non-empty and non-unknown for all 91 rows:

- `model_revision`
- `tokenizer_revision`
- `transformers_version`
- `tokenizers_version`
- `modal_image_sha`
- `xgrammar_version`

The generated metadata shape included grammar fields, replay identity fields, prompt hash, generation seed, package versions, Modal image provenance, and C2 generation hashes.

## 6. Grammar metadata analysis

| metric | count | rate |
|---|---:|---:|
| `gbnf_parse_valid` | 70/91 | 0.7692 |
| `semantic_valid` | 49/91 | 0.5385 |
| `grammar_valid` | 49/91 | 0.5385 |

Rejection layer distribution:

| rejection_layer | rows |
|---|---:|
| `None` | 49 |
| `semantic_validator` | 21 |
| `gbnf_parse` | 21 |

Stop reason distribution:

| stop_reason | rows |
|---|---:|
| `eos_token` | 70 |
| `max_new_tokens` | 21 |

Grammar invariant status: passed. For all persisted rows with grammar booleans, `grammar_valid == (gbnf_parse_valid and semantic_valid)`.

## 7. Evaluation ladder verification

Implicit Level 0 evidence is present for all 91 persisted rows through `compile_success`, canonical `failure_code`, and current-schema trace fields.

Level 1 compile evidence is present through top-level `compile_success` for all 91 rows.

Level 2 evidence is present for rows that reached F2, identified by `F2_NUMERIC_NAN` and six-entry repair traces.

F0/F1 terminal behavior:

- `F0_PARSE`: 2 rows, repair trace length 1.
- `F1_RUNTIME`: 75 rows, repair trace length 1.
- `F1_COMPILE`: 9 rows, repair trace length 1.

F2 repair behavior:

- `F2_NUMERIC_NAN`: 5 rows.
- Each F2 row has repair trace length 6 and terminal attempt index 5.
- No F2 row repaired to functional success.

No F0/F1 feedback leakage was observed in persisted rows. F0/F1 rows terminate with a single trace entry and do not show repair-loop expansion.

## 8. Overall metrics

| metric | count | rate |
|---|---:|---:|
| rows | 91 | n/a |
| functional_success | 0 | 0.0000 |
| compile_success | 5 | 0.0549 |
| F2 reached | 5 | 0.0549 |
| grammar_valid | 49 | 0.5385 |

Failure code distribution:

| failure_code | rows |
|---|---:|
| `F1_RUNTIME` | 75 |
| `F1_COMPILE` | 9 |
| `F2_NUMERIC_NAN` | 5 |
| `F0_PARSE` | 2 |

Repair iteration distribution: no top-level `repair_iteration` field is persisted. Repair behavior is represented by `repair_trace`.

Repair trace length distribution:

| repair_trace length | rows |
|---:|---:|
| 1 | 86 |
| 6 | 5 |

## 9. Metrics by kernel/dtype

| kernel_class | dtype | rows | functional_success_count | functional_success_rate | compile_success_count | compile_success_rate | grammar_valid_count | grammar_valid_rate | F2 count | dominant failure_code | median repair_trace_len |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| elementwise | bf16 | 20 | 0 | 0.0000 | 1 | 0.0500 | 18 | 0.9000 | 1 | `F1_RUNTIME` | 1 |
| elementwise | fp16 | 20 | 0 | 0.0000 | 0 | 0.0000 | 17 | 0.8500 | 0 | `F1_RUNTIME` | 1 |
| elementwise | fp32 | 20 | 0 | 0.0000 | 4 | 0.2000 | 14 | 0.7000 | 4 | `F1_COMPILE` | 1 |
| reduction | fp16 | 11 | 0 | 0.0000 | 0 | 0.0000 | 0 | 0.0000 | 0 | `F1_RUNTIME` | 1 |
| reduction | fp32 | 20 | 0 | 0.0000 | 0 | 0.0000 | 0 | 0.0000 | 0 | `F1_RUNTIME` | 1 |

## 10. Metrics by kernel

| kernel_class | rows | functional_success_rate | compile_success_rate | grammar_valid_rate | F2 count | dominant failure modes |
|---|---:|---:|---:|---:|---:|---|
| elementwise | 60 | 0.0000 | 0.0833 | 0.8167 | 5 | `F1_RUNTIME: 46`, `F1_COMPILE: 9`, `F2_NUMERIC_NAN: 5` |
| reduction | 31 | 0.0000 | 0.0000 | 0.0000 | 0 | `F1_RUNTIME: 29`, `F0_PARSE: 2` |

Matmul was not reached before the run failure.

## 11. Metrics by dtype

| dtype | rows | functional_success_rate | compile_success_rate | grammar_valid_rate | dominant failure modes |
|---|---:|---:|---:|---:|---|
| fp32 | 40 | 0.0000 | 0.1000 | 0.3500 | `F1_RUNTIME: 27`, `F1_COMPILE: 9`, `F2_NUMERIC_NAN: 4` |
| fp16 | 31 | 0.0000 | 0.0000 | 0.5484 | `F1_RUNTIME: 29`, `F0_PARSE: 2` |
| bf16 | 20 | 0.0000 | 0.0500 | 0.9000 | `F1_RUNTIME: 19`, `F2_NUMERIC_NAN: 1` |

## 12. Repair-loop analysis

Rows with `repair_trace`: 91/91.

Rows reaching F2: 5/91.

Rows repaired successfully: 0.

Repair trace length summary:

| statistic | value |
|---|---:|
| min | 1 |
| max | 6 |
| mean | 1.2747 |
| median | 1 |

Repair budget exhausted count: 5 inferred from F2 rows with six trace entries and terminal attempt index 5 under `repair_budget=5`.

Feedback was Level-2-only by behavior: only F2 rows expanded beyond one trace entry. F0/F1 rows stayed terminal with one trace entry.

## 13. Replay coverage warning analysis

Registered task-agnostic G replay artifact:

`outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

Observed replay rows: 177/180.

Missing replay rows:

| kernel_class | dtype | sample_index |
|---|---|---:|
| matmul | fp32 | 5 |
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |

The G+C preflight handled this safely with `COVERAGE_WARNING_SKIP_MISSING` and scheduled 177 rows. The run failure is separate from the known replay coverage caveat.

Effect on interpretation: even if the run had completed, paired comparison scope would be 177 matched rows, not 180. Because the run failed at 91 rows, this artifact is not ready for paired aggregation.

## 14. Comparison readiness against frozen G

The persisted partial rows have the required fields for row-level comparison:

- `kernel_class`
- `dtype`
- replay pair identity in `generated_metadata.replay_pair_id`
- `base_seed`
- terminal `attempt_index`
- `functional_success`
- `failure_code`
- grammar metadata
- provenance metadata

However, the artifact is not aggregation-ready because 86 scheduled matched rows were not reached before the runtime failure.

## 15. Confidence interval / uncertainty

Partial G+C functional_success point estimate:

0/91 = 0.0000.

95% Wilson interval for the partial rows:

`[0.0000, 0.0405]`.

This interval is descriptive only. It is not a final paper-scale uncertainty estimate because the run stopped mid-schedule, matmul was not reached, reduction bf16 was not reached, and the known replay coverage gap still limits paired scope to 177 rows.

## 16. Methodological interpretation

This is the task-agnostic G+C treatment route, not template G+C.

The G layer is grammar-guided decoding plus offline semantic validation:

- `grammar_active=True`
- `grammar_variant=task_agnostic`
- grammar path `cluster1/grammar/triton_kernel_agnostic.gbnf`

The C layer repairs only failures that reach F2. Persisted behavior is consistent with that rule: F2 rows have expanded repair traces, while F0/F1 rows remain terminal with one trace entry.

The 177/180 G replay coverage warning affects paired comparison scope, but it was not the cause of this run failure.

## 17. Go/no-go recommendation

`G_PLUS_C_N20_HOLD_FOR_FIX`

Reason: the partial artifact rows are valid, but the Modal run failed before completing the 177-row schedule due to a correctness payload schema/runtime issue.

## 18. Next step

`fix artifact/schema issue`

Specifically, inspect why an infrastructure-style correctness payload without `correctness_result` reached `_extract_correctness_result_dict` during generated-row evaluation. The runner should either convert that structured infrastructure failure into a canonical row-level failure or fail with enough context to identify the exact row and remote error payload.

Do not use this partial artifact for final aggregation.

## 19. Appendix

Commands run:

```bash
git status --short
.venv/bin/python -m cluster2.experiments.run_cluster2_modal --help
.venv/bin/python -m pytest cluster2/tests -k "g_plus_c or G_PLUS_C or grammar_active or grammar_variant or task_agnostic or replay or manifest or hash or coverage" -q
.venv/bin/python -m pytest cluster2/tests -k "compile_success or grammar_active or generated_metadata or metadata or result or logger or jsonl" -q
.venv/bin/python -m pytest cluster2/tests -k "implicit or level0 or nested or validator or smoke" -q
.venv/bin/python -m pytest cluster2/tests shared/tests -k "repair or feedback or F2 or level0 or level1 or level2 or failure_code" -q
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --grammar-variant task_agnostic --max-new-tokens 2048 --output outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

Pre-run validation summary:

- G+C smoke artifact validated under current nested metadata validator.
- Registered task-agnostic G replay coverage warning confirmed: 177/180.
- Local runner preflight scheduled exactly 177 G+C rows.
- Focused tests passed before launch.

Modal failure traceback endpoint:

```text
cluster2/experiments/run_cluster2_modal.py:1253
RuntimeError: correctness payload did not contain correctness_result
```

Exact artifact path:

`outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

Exact report path:

`audits/cluster2_g_plus_c_paper_n20_l4_report.md`
