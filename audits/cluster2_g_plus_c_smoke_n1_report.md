# Cluster 2 G+C n=1 Smoke Report

## 1. Executive summary

- Smoke status: Modal command completed successfully and wrote `outputs/cluster2/g_plus_c_smoke_n1.jsonl`.
- Pre-run gates: passed. Fix report confirmed, readiness audit not blocked, runner CLI verified, and all focused pytest gates passed.
- Artifact path: `outputs/cluster2/g_plus_c_smoke_n1.jsonl`.
- Row count: 3 valid JSONL rows.
- Final classification: `G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS`.
- Reason: row/schema/provenance checks pass under the current C2 row schema, and the smoke explicitly surfaced the known 177/180 G replay coverage warning.

## 2. Command and environment

Exact Modal command run:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --kernel-class elementwise --scale-tier smoke --n 1 --max-new-tokens 2048 --output outputs/cluster2/g_plus_c_smoke_n1.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --overwrite
```

- Modal run URL: `https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-NW7d7fXI082l0pToXuqQNh`.
- Generation GPU: L4.
- Eval GPU: L4.
- `max_new_tokens`: 2048.
- Model ID: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`.
- Model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- Tokenizer revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- Output path: `outputs/cluster2/g_plus_c_smoke_n1.jsonl`.
- CLI adaptation: current runner requires `--scale-tier`; `--scale-tier smoke` was added. Eval GPU and locked model/tokenizer revisions were supplied explicitly.

## 3. Output artifact integrity

- JSONL integrity: pass.
- Raw lines: 3.
- Valid rows: 3.
- Bad JSON lines: none.
- Ends with newline: true.
- Dtype schedule observed: one seed across default dtypes, `fp32`, `fp16`, and `bf16`.
- Top-level row keys: `attempt_index`, `base_seed`, `compile_success`, `condition`, `dtype`, `eval_set_success`, `failure_code`, `functional_success`, `generated_metadata`, `generation_mode`, `grammar_active`, `kernel_class`, `kernel_name`, `repair_set_success`, `repair_trace`, `replay_metadata`, `source_class`, `source_hash`, `trace_summary`.
- Row identities:
  - `fp32`: `condition=G+C`, `kernel_class=elementwise`, `kernel_name=relu`, `base_seed=0`, `attempt_index=5`, `replay_pair_id=elementwise:fp32:0`.
  - `fp16`: `condition=G+C`, `kernel_class=elementwise`, `kernel_name=relu`, `base_seed=0`, `attempt_index=0`, `replay_pair_id=elementwise:fp16:0`.
  - `bf16`: `condition=G+C`, `kernel_class=elementwise`, `kernel_name=relu`, `base_seed=0`, `attempt_index=0`, `replay_pair_id=elementwise:bf16:0`.

## 4. G+C condition integrity

- Condition counts: `{"G+C": 3}`.
- Kernel class counts: `{"elementwise": 3}`.
- Generation mode counts: `{"new_c2_generation_with_G_adapter": 3}`.
- Route audit: `route=c2_repair_loop_with_g_adapter`, `generation_calls=8`, `correctness_calls=8`.
- Top-level `grammar_active`: `true` for all 3 rows.
- Current schema stores grammar/provenance fields under `generated_metadata`; top-level `grammar_active` and `compile_success` are persisted.
- `generated_metadata.grammar_variant`: `task_agnostic` for all 3 rows.
- `generated_metadata.grammar_path`: `cluster1/grammar/triton_kernel_agnostic.gbnf` for all 3 rows.
- `generated_metadata.grammar_sha`: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` for all 3 rows.
- `template_upper_bound` was not used.

## 5. Grammar metadata verification

Grammar metadata verification passed for all rows:

- `grammar_path`: `cluster1/grammar/triton_kernel_agnostic.gbnf`.
- `grammar_sha`: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.
- `grammar_claim_scope`: `primary`.
- `gbnf_parse_valid`: `true`.
- `semantic_valid`: `true`.
- `grammar_valid`: `true`.
- `rejection_layer`: `null`, expected because grammar validation passed.
- `stop_reason`: `eos_token`.
- `xgrammar_version`: `0.1.33`.
- `grammar_valid == gbnf_parse_valid and semantic_valid`: pass for all rows.

## 6. Evaluation ladder verification

- Level 0 evidence: represented by `trace_summary` and `repair_trace` terminal summaries in the current row schema.
- Level 1 evidence: `compile_success` is top-level and present for all rows.
- Level 2 evidence: `repair_set_success`, `eval_set_success`, and `functional_success` are top-level and present for all rows.
- `compile_success` counts: `{true: 1, false: 2}`.
- `functional_success` counts: `{false: 3}`.
- `repair_set_success` counts: `{true: 1, false: 2}`.
- `eval_set_success` counts: `{false: 3}`.
- Failure code counts: `{"F2_NUMERIC_NAN": 1, "F1_RUNTIME": 2}`.
- Canonical failure code check: pass. All observed failure codes use canonical `F1_` or `F2_` prefixes.

## 7. Repair-loop behavior

- The `fp32` row reached F2: `failure_code=F2_NUMERIC_NAN`, `compile_success=true`, `repair_set_success=true`, `eval_set_success=false`, `repair_trace` length 6, final `attempt_index=5`.
- F2 repair fired: the row advanced through attempts 0 through 5 and persisted public F2 failure summaries for each attempt.
- Full feedback prompt text/hash is not persisted in the final row trace, but repair-loop execution is evidenced by the multi-attempt F2 trace. Local repair/feedback tests passed before the smoke.
- The `fp16` and `bf16` rows were terminal F1 runtime failures at `attempt_index=0`, with `compile_success=false` and `repair_trace` length 1.
- F1 rows did not include `feedback_prompt` or `feedback_content`; no pre-Level-2 feedback was emitted.

## 8. Metadata/provenance check

Provenance fields are populated under `generated_metadata` for all rows:

- `model_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- `tokenizer_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.
- `modal_image_sha`: `im-tU3VQyAbFvrusOxtlwspCN`.
- `modal_image_provenance_sha256`: `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535`.
- `transformers_version`: `4.47.1`.
- `tokenizers_version`: `0.21.1`.
- `xgrammar_version`: `0.1.33`.
- Missing/unknown required metadata count: 0.

## 9. Replay coverage warning check

- The JSONL rows do not carry run-level coverage warnings.
- The Modal runner summary explicitly surfaced the known replay coverage warning.
- `artifact_id`: `g_task_agnostic_aligned_pipeline_n20_l4`.
- `replay_expected_rows`: 180.
- `replay_observed_rows`: 177.
- `replay_coverage_complete`: false.
- `replay_coverage_policy`: `COVERAGE_WARNING_SKIP_MISSING`.
- Missing rows:
  - `{"dtype": "fp32", "kernel_class": "matmul", "sample_index": 5}`
  - `{"dtype": "bf16", "kernel_class": "matmul", "sample_index": 0}`
  - `{"dtype": "bf16", "kernel_class": "matmul", "sample_index": 18}`
- This does not block the n=1 smoke. It remains a paper-scale decision point: run covered-row G+C n=20 with the explicit warning, or regenerate/register the three missing matmul G replay rows first.

## 10. Readiness decision

`G_PLUS_C_N1_SMOKE_PASS_WITH_WARNINGS`

The Modal run completed, the artifact is valid JSONL, all rows are `G+C`/`elementwise`, grammar is active with task-agnostic grammar metadata, the grammar SHA matches the current task-agnostic grammar, `compile_success` is present, failure codes are canonical, provenance is complete, eval ladder evidence is present, and repair behavior is correct for the observed F2 and F1 classes. The remaining warning is the known 177/180 replay coverage warning.

## 11. Next recommendation

`HOLD_FOR_REPLAY_COVERAGE_DECISION`

The n=1 smoke is ready evidence, but paper-scale G+C still needs an explicit decision on the known 177/180 G replay coverage state: accept covered-row analysis with `COVERAGE_WARNING_SKIP_MISSING`, or complete the missing matmul replay rows before G+C n=20.
