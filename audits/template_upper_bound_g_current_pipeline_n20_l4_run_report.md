# Template Upper-Bound G Current-Pipeline n20 L4 Run Report

## 1. Executive summary

Run status: completed with documentation registration and metadata caveats.

Artifact path: `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`.

The Modal L4 Cluster 1 run wrote 180/180 rows for condition `G` with `grammar_variant=template_upper_bound`. All 180 rows have `compile_success=true`. The current Cluster 1 validator passed in basic mode, metadata-gated mode, and grammar-variant-gated mode.

Classification: diagnostic/non-primary template upper-bound G. This artifact is compile-only Cluster 1 evidence. It is not primary G, does not fill task-agnostic G missing rows, and is not included in the primary 2x2 analyzer.

## 2. Preflight

- Initial `git status --short`: clean.
- Output path nonexistence check passed for `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`.
- Sidecar nonexistence check passed for `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl.meta.json`.
- `.venv/bin/python -m cluster1.experiments.run_cluster1_modal --help` exited 0 but emitted no argparse text because the module exposes a Modal local entrypoint rather than a direct Python argparse CLI.
- Exact Modal CLI flags were verified with `/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --help` and the runner source. Verified flags included `--condition`, `--grammar-variant`, `--kernel-class`, `--scale-tier`, `--n`, `--model-id`, `--model-revision`, `--tokenizer-revision`, `--max-new-tokens`, `--output`, `--modal-generation-gpu`, and `--overwrite / --no-overwrite`.
- Output safety was verified in `cluster1/experiments/run_cluster1_modal.py`: without `--overwrite`, a non-empty existing output is refused.
- Grammar routing was verified in `cluster1/generation/grammar_variants.py` and runner call sites. `template_upper_bound` routes to `cluster1/grammar/triton_kernel.gbnf`.
- `cluster1/grammar/triton_kernel.gbnf` exists and its local SHA-256 is `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`.

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant template_upper_bound --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl --modal-generation-gpu L4
```

No `--overwrite` flag was used.

## 3. Run result

- Modal app URL: `https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-ILqtMeBYFaKsevXlwUJwL4`
- Sidecar `started_at_utc`: `2026-05-22T04:43:40.888792+00:00`
- Sidecar `finished_at_utc`: `2026-05-22T08:50:46.765919+00:00`
- Modal generation GPU: `L4`
- Sidecar status: `completed`
- Written rows: 180
- Expected rows: 180
- Infrastructure failures: 0
- Terminal status: process exited 0 and printed `wrote 180 rows to outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`
- Log caveat: Modal emitted intermittent `Logs may not be continuous` warnings. The sidecar recorded zero infrastructure failures and validation found no missing rows.

## 4. Validation

Basic validator:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl --condition G --kernel-class all --n 20
```

Result: PASS. Row count 180/180, missing cells 0, unexpected cells 0, duplicate identities 0.

Metadata gate:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl --condition G --kernel-class all --n 20 --require-generation-metadata
```

Result: PASS. `generation_metadata_failures=0`.

Grammar-variant gate:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl --condition G --kernel-class all --n 20 --grammar-variant template_upper_bound --require-generation-metadata
```

Result: PASS. Observed grammar variant coverage was `template_upper_bound`.

The primary analyzer was not run with this artifact, and `outputs/analysis/factorial_2x2_preliminary.json` was not modified.

## 5. Artifact analysis

All counts below were computed with `.venv/bin/python` from the JSONL artifact.

| Metric | Value |
| --- | ---: |
| Valid rows | 180 |
| Intended rows | 180 |
| Malformed JSON lines | 0 |
| Missing cells | 0 |
| `compile_success=true` | 180/180 (100.0%) |
| `grammar_valid=true` | 60/180 (33.3%) |
| `gbnf_parse_valid=true` | 180/180 (100.0%) |
| `semantic_valid=true` | 60/180 (33.3%) |

By kernel/dtype:

| Cell | Rows |
| --- | ---: |
| elementwise/fp32 | 20 |
| elementwise/fp16 | 20 |
| elementwise/bf16 | 20 |
| reduction/fp32 | 20 |
| reduction/fp16 | 20 |
| reduction/bf16 | 20 |
| matmul/fp32 | 20 |
| matmul/fp16 | 20 |
| matmul/bf16 | 20 |

Distributions:

| Field | Distribution |
| --- | --- |
| `grammar_active` | true 180 |
| `grammar_variant` | `template_upper_bound` 180 |
| `grammar_path` | `cluster1/grammar/triton_kernel.gbnf` 180 |
| `grammar_sha` | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` 180 |
| `rejection_layer` | null 60; `semantic_validator` 120 |
| `stop_reason` | `eos_token` 180 |
| `failure_code` | null 180 |
| `compile_error_type` | null 180 |
| `functional_success` | null 180 |
| `generation_seed` | seeds 0-19, nine rows per seed |
| `temperature` | 0.2 on 180 rows |

Provenance:

| Field | Distribution |
| --- | --- |
| `model_id` | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` 180 |
| `model_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` 180 |
| `tokenizer_revision` | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` 180 |
| `modal_image_sha` | `im-tU3VQyAbFvrusOxtlwspCN` 180 |
| `modal_image_provenance_sha256` | `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535` 180 |
| `transformers_version` | 4.47.1 on 180 rows |
| `tokenizers_version` | 0.21.1 on 180 rows |
| `xgrammar_version` | 0.1.33 on 180 rows |

Metadata caveat: rows are flat Cluster 1 rows. The sidecar records `condition=G`, `scale_tier=paper`, `max_new_tokens=2048`, and `overwrite=false`, but rows do not serialize row-level `condition`, `scale_tier`, `base_seed`, `sample_index`, or `max_new_tokens`. The current validator still passed the metadata gate.

## 6. Diagnostic comparison

Diagnostic only, not a primary causal comparison:

| Artifact | Rows | Compile success | Grammar metadata status |
| --- | ---: | ---: | --- |
| Current template upper-bound G | 180 | 180/180 | Current grammar/provenance fields present; metadata gate PASS; flat-row caveats above |
| Legacy template G `outputs/cluster1/final_g_l4_n20.jsonl` | 180 | 180/180 | Legacy rows lack current grammar funnel/provenance metadata and fail current paper-scale metadata expectations |
| Current task-agnostic G `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 3/177 | Current primary G; 177/180 with three missing matmul rows; task-agnostic grammar surface |

The template artifact is a stronger task-encoded grammar reference. It is not primary G, not task-agnostic evidence, not a repair for missing task-agnostic rows, and not a current primary analyzer input.

## 7. Registry/docs updates

Updated:

- `README.md`
- `docs/02_methodology_cluster1.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md`

Registered:

- `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`
- diagnostic label `G_template` / template upper-bound G
- Cluster 1 compile-only / Level 1 surface
- row count, compile success, grammar funnel, validator status, provenance fields, and caveats

Not changed:

- source code
- grammar files
- hash manifests
- primary raw artifacts
- `outputs/analysis/factorial_2x2_preliminary.json`
- `.contracts/research/`

## 8. Remaining caveats

- Cluster 1 is compile-only.
- No Level 2 numerical correctness was run for this artifact.
- No matching current-pipeline template G+C artifact exists yet.
- This artifact is not primary G.
- This artifact is not part of the primary 2x2 analyzer.
- Rows are flat Cluster 1 rows with some run-level metadata in the sidecar, as noted above.

## 9. Next recommendation

PROCEED_TO_TEMPLATE_G_PLUS_C_PLAN_UPDATE

Before spending on template G+C, update the diagnostic plan/manifest path so the new current-pipeline template G artifact is selected explicitly and the flat-row metadata caveats are handled intentionally.
