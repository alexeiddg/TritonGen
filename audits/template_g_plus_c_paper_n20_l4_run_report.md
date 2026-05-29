# Template G+C Paper n20 L4 Run Report

## 1. Executive summary

Run status: `TEMPLATE_G_PLUS_C_RUN_COMPLETE`.

Artifact: `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl`.

Rows written: 180 valid JSONL rows. The run used the diagnostic `template_upper_bound` grammar route and replayed `g_template_upper_bound_current_pipeline_n20_l4`, not task-agnostic G and not the legacy template artifact.

Compile success: 180/180 = 100.00%.

Functional success: 96/180 = 53.33%.

F2 reached: 84/180 rows. All 84 exhausted terminal attempt 5; 0 repaired to functional success.

This artifact is diagnostic-only and is not a primary analyzer input.

## 2. Modal command and run URL

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --grammar-variant template_upper_bound --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-TtPF7BjWSIAz2VokzP23N6
```

Runner result:

```json
{"coverage_failures": [], "coverage_warnings": [], "output": "outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl", "route_audit": [{"condition": "G+C", "correctness_calls": 600, "generation_allowed": true, "generation_calls": 600, "route": "c2_repair_loop_with_g_adapter"}], "rows": 180, "write_mode": "overwrite"}
```

## 3. Pre-launch checks

| Check | Result |
| --- | --- |
| Requested output absent before launch | pass |
| User approval for `--overwrite` | granted for this paper-scale path |
| Git status | only unrelated `cluster3/` changes were present and were ignored per user instruction |
| Manifest entry | `g_template_upper_bound_current_pipeline_n20_l4` present |
| Template G artifact | present with 180 valid rows |
| Template grammar SHA | matched `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` |
| Free disk space under `outputs/` | greater than 100 MB |
| CLI flags | verified against `cluster2.experiments.run_cluster2_modal --help` |

## 4. During-run notes

Launch time: 2026-05-26T05:38:28Z.

Final row write time: 2026-05-26T15:27:16Z by output file mtime. Approximate wall-clock to final durable row: 9h 48m 48s.

The 30-minute checkpoint showed elementwise progress and durable row writes. The 2-hour checkpoint confirmed reduction kernels had started, so the run was not stuck on elementwise.

The CLI repeatedly emitted `WARNING: Logs may not be continuous`. Durable JSONL row counts were used as the monitoring source of truth.

Reduction rows and matmul/fp32 rows had repeated intervals above five minutes per row. The run remained attached and continued writing durable rows, so no manual kill or recovery action was taken.

Cost telemetry was not exposed in the local CLI output.

## 5. Post-run validation

| Check | Result |
| --- | --- |
| Artifact exists | yes |
| Valid JSONL rows | 180 |
| Bad JSON lines | 0 |
| Ends with newline | true |
| Expected row count | 180/180 |
| Condition | `G+C` on 180/180 |
| Grammar variant | `template_upper_bound` on 180/180 |
| Grammar SHA | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` on 180/180 |
| Replay source | `g_template_upper_bound_current_pipeline_n20_l4` on 180/180 |
| Cluster 1 artifact ID | `g_template_upper_bound_current_pipeline_n20_l4` on 180/180 |
| Row-level `scale_tier` | not serialized on raw rows |

## 6. Provenance verification

| Field | Distribution |
| --- | --- |
| `model_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` on 180/180 |
| `tokenizer_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` on 180/180 |
| `modal_image_sha` | `im-tU3VQyAbFvrusOxtlwspCN` on 180/180 |
| `modal_image_provenance_sha256` | `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535` on 180/180 |
| `transformers_version` | `4.47.1` on 180/180 |
| `tokenizers_version` | `0.21.1` on 180/180 |
| `xgrammar_version` | `0.1.33` on 180/180 |
| `generated_metadata` | present on 180/180 |

## 7. Headline metrics

| Metric | Count | Rate |
| --- | ---: | ---: |
| Compile success | 180/180 | 100.00% |
| Functional success | 96/180 | 53.33% |
| F2 reached | 84/180 | 46.67% |
| F2 repaired to success | 0/84 | 0.00% |
| F2 exhausted repair budget | 84/84 | 100.00% |
| F3 eval pipeline | 0/180 | 0.00% |

Failure-code distribution:

| failure_code | rows |
| --- | ---: |
| null | 96 |
| `F2_NUMERIC_NAN` | 60 |
| `F2_NUMERIC_LARGE` | 24 |

## 8. Per-cell breakdown

| kernel_class | dtype | rows | compile_success | functional_success | failure_code distribution |
| --- | --- | ---: | ---: | ---: | --- |
| elementwise | bf16 | 20 | 20 | 20 | null 20 |
| elementwise | fp16 | 20 | 20 | 20 | null 20 |
| elementwise | fp32 | 20 | 20 | 20 | null 20 |
| matmul | bf16 | 20 | 20 | 16 | null 16; `F2_NUMERIC_LARGE` 4 |
| matmul | fp16 | 20 | 20 | 20 | null 20 |
| matmul | fp32 | 20 | 20 | 0 | `F2_NUMERIC_LARGE` 20 |
| reduction | bf16 | 20 | 20 | 0 | `F2_NUMERIC_NAN` 20 |
| reduction | fp16 | 20 | 20 | 0 | `F2_NUMERIC_NAN` 20 |
| reduction | fp32 | 20 | 20 | 0 | `F2_NUMERIC_NAN` 20 |

## 9. Repair-loop analysis

Rows with trace length 1: 96.

Rows with trace length 6: 84.

Terminal attempt distribution:

| attempt_index | rows |
| ---: | ---: |
| 0 | 96 |
| 5 | 84 |

Rows entering F2 on initial attempt: 84.

Rows repaired to functional success: 0.

Rows exhausting repair budget: 84.

The Modal route audit reported `generation_calls=600` and `correctness_calls=600`, matching 96 immediate success traces and 84 six-attempt repair traces.

## 10. Tests run

Artifact/provenance inspection:

```bash
.venv/bin/python - <<'PY'
# JSONL integrity, replay source, grammar SHA, provenance, and per-cell metrics.
PY
```

Result: passed.

Strict validator/schema target:

```bash
.venv/bin/python -m pytest cluster2/tests -k "validator or schema" -q
```

Result: 73 passed, 341 deselected.

## 11. Registry update

Updated `docs/05_artifacts_and_results_registry.md` with diagnostic artifact ID `g_plus_c_template_upper_bound_current_pipeline_n20_l4`, path, row count, diagnostic-only role, replay caveat, and primary-analyzer exclusion.

No primary analyzer artifact was modified.

## 12. Classification

`TEMPLATE_G_PLUS_C_RUN_COMPLETE`

## 13. Next recommendation

`DIAGNOSTIC_TEMPLATE_G_PLUS_C_READY_FOR_REVIEW`
