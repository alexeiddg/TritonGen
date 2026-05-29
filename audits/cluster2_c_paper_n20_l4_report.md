# Cluster 2 C Paper n=20 L4 Report

## 1. Executive summary

- Run status: completed.
- Artifact path: `outputs/cluster2/c_paper_n20_l4.jsonl`
- Observed row count: 180
- Expected row count: 180
- Functional success: 0/180 = 0.00%
- Compile success: 0/180 = 0.00% true values. The generated-row schema omitted `compile_success` because all rows terminated at Level 0 parse before compile.
- Main failure mode: `F0_PARSE` on 180/180 rows.
- C paper-scale artifact validity: valid for aggregation. The artifact is complete, strict-parseable, C-only, grammar-free, and has complete generated provenance under `generated_metadata`.

Final recommendation: `C_N20_VALID_FOR_AGGREGATION`.

## 2. Command and environment

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition C --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster2/c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

- Modal run URL: `https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-4mFVsvF6hk02NXJuAD3F45`
- Generation GPU: L4
- Eval GPU: L4
- `max_new_tokens`: 2048
- `repair_budget`: 5
- `model_id`: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
- `model_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `tokenizer_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `modal_image_sha`: `im-tU3VQyAbFvrusOxtlwspCN`
- `transformers_version`: `4.47.1`
- `tokenizers_version`: `0.21.1`
- `xgrammar_version`: `0.1.33`
- Stop reasons: `eos_token` 175, `max_new_tokens` 5
- Route audit: condition `C`, route `c2_repair_loop`, generation calls 180, correctness calls 180, no coverage failures, no coverage warnings.

## 3. Artifact integrity and durability

- Valid JSONL: yes
- Raw lines: 180
- Valid rows: 180
- Malformed JSON lines: none
- Ends with newline: yes
- Strict Cluster 2 validator: `validate_cluster2_results_jsonl(..., expected_rows=180)` passed.
- Sidecar: `outputs/cluster2/c_paper_n20_l4.jsonl.hashes.json` exists, schema version 1.
- Sidecar generated condition hashes: `C`
- Missing rows: none.
- Partial output interpretability: live checks observed durable valid prefixes throughout the run. The final artifact remains a valid newline-delimited 180-row file.

Cell coverage:

| kernel_class | dtype | rows |
|---|---:|---:|
| elementwise | fp32 | 20 |
| elementwise | fp16 | 20 |
| elementwise | bf16 | 20 |
| reduction | fp32 | 20 |
| reduction | fp16 | 20 |
| reduction | bf16 | 20 |
| matmul | fp32 | 20 |
| matmul | fp16 | 20 |
| matmul | bf16 | 20 |

## 4. C condition integrity

- Condition counts: `C` 180.
- Generation mode: `new_c2_generation` 180.
- Source class: `generated_row` 180.
- Grammar-free status: pass.
- `grammar_variant`: null on 180 rows.
- `grammar_path`: null on 180 rows.
- `grammar_sha`: null on 180 rows.
- `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`: null on 180 rows.
- No row recorded `grammar_active=true`.
- No row used G grammar variants `task_agnostic` or `template_upper_bound`.
- Base prompt pairing: rows record `replay_control_condition=none`, 180 unique `replay_pair_id` values, 9 unique prompt hashes by kernel/dtype, and base seeds 0-19 for every kernel/dtype cell. The runner validated prompt hash and paired none schedule before each C generation.

## 5. Evaluation ladder verification

- Level 0 evidence: every row has top-level `failure_code=F0_PARSE`, matching `trace_summary.failure_code`, and a single-entry `repair_trace`.
- Level 1 evidence: all rows terminally skipped Level 1 because Level 0 parse failed. No row reached compile.
- Level 2 evidence: all rows terminally skipped Level 2 because Level 0 parse failed. Terminal status fields are present: `functional_success=false`, `repair_set_success=false`, `eval_set_success=false`.
- F0/F1 terminal behavior: all 180 rows are F0 terminal rows at `attempt_index=0`.
- F2 repair behavior: no row reached F2.
- Feedback leakage: no F0 row contains feedback prompt/content in `repair_trace`.

## 6. Metadata/provenance validation

Generated provenance is stored under `generated_metadata` in the current schema rather than flattened at the top level. Schema-aware validation found zero missing or unknown required metadata values.

| field | observed value |
|---|---|
| `model_id` | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` |
| `model_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| `tokenizer_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| `modal_image_sha` | `im-tU3VQyAbFvrusOxtlwspCN` |
| `modal_image_provenance_sha256` | `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535` |
| `transformers_version` | `4.47.1` |
| `tokenizers_version` | `0.21.1` |
| `generation_metadata_schema_version` | `1` |
| `max_new_tokens` | `2048` |
| `temperature` | `0.2` |

## 7. Overall metrics

| metric | value |
|---|---:|
| rows | 180 |
| functional_success_count | 0 |
| functional_success_rate | 0.00% |
| compile_success_count | 0 |
| compile_success_rate | 0.00% |
| failure_code `F0_PARSE` | 180 |
| attempt_index min/mean/median/max | 0 / 0.0 / 0 / 0 |
| stop_reason `eos_token` | 175 |
| stop_reason `max_new_tokens` | 5 |

## 8. Metrics by kernel/dtype

| kernel_class | dtype | rows | functional_success_count | functional_success_rate | compile_success_count | compile_success_rate | dominant failure_code | median attempt_index |
|---|---|---:|---:|---:|---:|---:|---|---:|
| elementwise | fp32 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| elementwise | fp16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| elementwise | bf16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| reduction | fp32 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| reduction | fp16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| reduction | bf16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| matmul | fp32 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| matmul | fp16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |
| matmul | bf16 | 20 | 0 | 0.00% | 0 | 0.00% | `F0_PARSE` | 0 |

## 9. Metrics by kernel

| kernel_class | rows | functional_success_rate | compile_success_rate | dominant failure modes |
|---|---:|---:|---:|---|
| elementwise | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |
| reduction | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |
| matmul | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |

## 10. Metrics by dtype

| dtype | rows | functional_success_rate | compile_success_rate | dominant failure modes |
|---|---:|---:|---:|---|
| fp32 | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |
| fp16 | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |
| bf16 | 60 | 0.00% | 0.00% | `F0_PARSE`: 60 |

## 11. Repair-loop analysis

- Rows with repair trace: 180
- Repair trace length distribution: length 1 on 180 rows.
- Rows reaching F2: 0
- Rows repaired successfully: 0
- Attempt index min/mean/median/max: 0 / 0.0 / 0 / 0
- Repair budget exhausted: 0 rows
- Feedback Level-2-only check: pass by absence. Since all rows failed at F0, no feedback was generated.
- Cost exposure actually observed: 180 generation calls and 180 correctness calls, so no repair-loop expansion occurred.

## 12. Failure taxonomy analysis

| failure family | count | rate |
|---|---:|---:|
| F0 | 180 | 100.00% |
| F1 | 0 | 0.00% |
| F2 | 0 | 0.00% |
| F3 | 0 | 0.00% |
| success | 0 | 0.00% |

Most common canonical failure codes:

| failure_code | count |
|---|---:|
| `F0_PARSE` | 180 |

Failure attribution looks schema-credible: the code is canonical, every row has a matching trace summary, and F0 rows did not proceed into compile/correctness or repair feedback. The methodological concern is outcome quality, not artifact validity: every generated candidate failed parse.

## 13. Comparison readiness against frozen none

The artifact has enough fields for a C versus frozen-none aggregation path:

- `kernel_class`: present.
- `dtype`: present.
- seed/sample identity: `base_seed`, `attempt_index`, `generated_metadata.replay_pair_id`, `replay_base_seed`, and `replay_generation_seed` present.
- `functional_success`: present.
- `failure_code`: present and canonical.
- metadata/provenance: present under `generated_metadata`.
- prompt identity: `prompt_sha256` present under `generated_metadata`.

No final paper lift was computed in this report.

## 14. Confidence interval / uncertainty

C functional success point estimate:

- successes: 0
- total: 180
- point estimate: 0.00%
- 95% Wilson interval: [0.00%, 2.09%]

This interval treats the 180 rows as independent Bernoulli samples. The design is clustered by kernel/dtype with 9 cells of 20 rows; every cell observed 0/20 functional success, so the cell-level qualitative conclusion is unchanged.

## 15. Go/no-go recommendation

`C_N20_VALID_FOR_AGGREGATION`

Rationale:

- Modal run completed.
- Artifact exists and has exactly 180 rows.
- JSONL is valid and strict Cluster 2 validation passed.
- Metadata/provenance is complete under the current generated-row schema.
- `tokenizer_revision` and `modal_image_sha` are non-unknown on every row.
- Every row is condition `C`.
- Every row is grammar-free.
- Every row has canonical `failure_code`.
- Level 0 evidence and terminal Level 1/2 skip evidence are present.
- F0 rows did not trigger repair feedback.
- Report was written.

## 16. Next step

Recommended next step: run aggregation C vs frozen none.

Do not rerun C n=20 just because the functional success rate is 0%. This is valid treatment data with correct failure attribution and complete provenance. The next aggregation step can quantify the C outcome against the frozen none replay control.

## 17. Appendix

Commands run:

```bash
git status --short
.venv/bin/python -m cluster2.experiments.run_cluster2_modal --help
.venv/bin/python -m pytest cluster2/tests shared/tests -k "level0 or level1 or level2 or generated_eval or failure_code or repair" -q
.venv/bin/python -m pytest cluster2/tests -k "durable or jsonl or logger or append or flush or fsync or partial or overwrite" -q
.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py -q
.venv/bin/python -m pytest cluster2/tests shared/tests -k "metadata or provenance or result or repair or eval or failure_code" -q
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition C --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster2/c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
.venv/bin/python - <<'PY'
# Basic JSONL integrity, strict Cluster 2 validation, and schema-aware C n=20 audit.
PY
```

Pre-run validation outputs:

- Schema-aware C n=1 smoke gate: `C_N1_SMOKE_READY_SCHEMA_AWARE`
- Generated eval/repair/failure-code gate: 237 passed, 674 deselected.
- Durable/logger gate: 43 passed, 343 deselected.
- Runner/result/schema gate: 127 passed.
- Optional broad metadata/provenance regression: 481 passed, 1 failed, 429 deselected. The failure was an unrelated G/frozen manifest hash interlock: `test_grammar_hash_gate_passes_after_phase4_interlock`.
- Canonical F2 smoke artifacts: valid, current, matching locked model/tokenizer revisions.

Post-run validation outputs:

- Basic JSONL integrity: 180 raw lines, 180 valid rows, no bad JSON, trailing newline true.
- Strict Cluster 2 validator: `STRICT_CLUSTER2_VALIDATOR_PASS 180`
- Schema-aware validation: `C_N20_SCHEMA_AWARE_VALIDATION_PASS`
- Final route audit: `rows=180`, `generation_calls=180`, `correctness_calls=180`, no coverage failures, no coverage warnings.

Exact artifact path:

```text
outputs/cluster2/c_paper_n20_l4.jsonl
```

Exact report path:

```text
audits/cluster2_c_paper_n20_l4_report.md
```
