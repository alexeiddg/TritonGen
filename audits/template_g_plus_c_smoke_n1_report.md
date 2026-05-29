# Template G+C Smoke n1 Report

## 1. Executive summary

Phase 2 status: `SMOKE_PASS`.

The explicit diagnostic template G+C smoke completed on Modal L4 and wrote 3 rows to `outputs/cluster2/template_g_plus_c_smoke_n1.jsonl`. Rows cover elementwise fp32, fp16, and bf16 for base seed 0. The smoke uses `condition=G+C`, `grammar_variant=template_upper_bound`, and replay source `g_template_upper_bound_current_pipeline_n20_l4`.

This is a smoke artifact only. It is diagnostic/non-primary and does not imply a template G+C n=20 artifact exists.

## 2. Modal command

The smoke output did not exist before the run. `--overwrite` was used intentionally only for this smoke path.

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --grammar-variant template_upper_bound --kernel-class elementwise --scale-tier smoke --n 1 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster2/template_g_plus_c_smoke_n1.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-CW3gftI3h2NCM1gAxwuXyM
```

Runner result:

```json
{"coverage_failures": [], "coverage_warnings": [], "output": "outputs/cluster2/template_g_plus_c_smoke_n1.jsonl", "route_audit": [{"condition": "G+C", "correctness_calls": 3, "generation_allowed": true, "generation_calls": 3, "route": "c2_repair_loop_with_g_adapter"}], "rows": 3, "write_mode": "overwrite"}
```

## 3. Smoke row count

| Check | Result |
| --- | --- |
| Artifact exists | yes |
| Valid JSONL rows | 3 |
| Bad JSON lines | 0 |
| Kernel class | `elementwise` on 3/3 |
| Dtypes | fp32, fp16, bf16 |
| Base seed | 0 on 3/3 |

## 4. Replay source verification

| Field | Distribution |
| --- | --- |
| `generated_metadata.cluster1_artifact_id` | `g_template_upper_bound_current_pipeline_n20_l4` on 3/3 |
| `generated_metadata.replay_source` | `g_template_upper_bound_current_pipeline_n20_l4` on 3/3 |
| `generated_metadata.replay_control_condition` | `G` on 3/3 |
| `generated_metadata.replay_pair_id` | `elementwise:fp32:0`, `elementwise:fp16:0`, `elementwise:bf16:0` |

The smoke did not replay task-agnostic G and did not replay the legacy template artifact `g_template_upper_bound_n20_l4`.

## 5. Grammar metadata verification

| Field | Distribution |
| --- | --- |
| `condition` | `G+C` on 3/3 |
| `grammar_active` | true on 3/3 |
| `grammar_variant` | `template_upper_bound` on 3/3 |
| `grammar_path` | `cluster1/grammar/triton_kernel.gbnf` on 3/3 |
| `grammar_sha` | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` on 3/3 |
| `grammar_claim_scope` | `diagnostic_non_primary` on 3/3 |
| `gbnf_parse_valid` | true on 3/3 |
| `semantic_valid` | true on 3/3 |
| `grammar_valid` | true on 3/3 |

## 6. Provenance verification

| Field | Distribution |
| --- | --- |
| `model_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` on 3/3 |
| `tokenizer_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` on 3/3 |
| `max_new_tokens` | 2048 on 3/3 |
| `modal_image_sha` | `im-tU3VQyAbFvrusOxtlwspCN` on 3/3 |
| `modal_image_provenance_sha256` | `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535` on 3/3 |

The content-hash sidecar was written at `outputs/cluster2/template_g_plus_c_smoke_n1.jsonl.hashes.json`.

## 7. Schema/failure-code verification

| Field | Distribution |
| --- | --- |
| `failure_code` | null on 3/3 |
| `compile_success` | true on 3/3 |
| `functional_success` | true on 3/3 |
| `repair_trace` | one attempt-0 success trace on 3/3 |

Strict row reconstruction with `Cluster2EvalRow.from_dict` passed for all rows. `validate_generated_paper_scale_metadata` passed for all generated metadata records. Failure-code taxonomy validation passed.

## 8. Tests run

Runner help:

```bash
.venv/bin/python -m cluster2.experiments.run_cluster2_modal --help
```

Result: passed.

Smoke inspection:

```bash
.venv/bin/python - <<'PY'
# JSONL row/provenance inspection with unhashable repair_trace values stringified.
PY
```

Result: 3 valid rows, expected replay source and metadata.

Schema/taxonomy validation:

```bash
.venv/bin/python - <<'PY'
# Cluster2EvalRow.from_dict, validate_generated_paper_scale_metadata,
# failure-code taxonomy, replay source, and template grammar checks.
PY
```

Result: 3 rows valid.

Broad smoke/schema test selection:

```bash
.venv/bin/python -m pytest cluster2/tests -k "template or replay or schema or metadata or smoke" -q
```

Result: 215 passed, 199 deselected.

## 9. Smoke classification

`SMOKE_PASS`

## 10. Next recommendation

`REQUEST_USER_APPROVAL_FOR_TEMPLATE_G_PLUS_C_N20`

Do not launch paper-scale template G+C without explicit user approval.
