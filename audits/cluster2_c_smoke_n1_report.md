# Cluster 2 C n=1 Modal Smoke Report

## 1. Executive summary

- Smoke status: completed and validated, with warnings.
- Artifact path: `outputs/cluster2/c_smoke_n1.jsonl`
- Row count: 3 rows. The runner default dtype schedule emitted one row each for `fp32`, `fp16`, and `bf16`.
- Final classification: `C_N1_SMOKE_PASS_WITH_WARNINGS`
- Final result: all live rows terminated at `F0_PARSE`. This is acceptable for this regression smoke because the failure code is canonical, no repair feedback fired for F0, metadata/provenance is populated, and local fixture tests covered F2 repair behavior.

## 2. Command and environment

Pre-run gates were executed with `.venv/bin/python` and passed:

- Working tree check: `git status --short` returned clean output.
- Runner help: `.venv/bin/python -m cluster2.experiments.run_cluster2_modal --help` succeeded.
- Level 0/1/2 ordering, generated eval, failure code, and repair gate: `237 passed, 674 deselected`.
- Durable JSONL/logger gate: `43 passed, 343 deselected`.
- Runner/result/schema smoke-adjacent gate: `127 passed`.

Exact Modal command run:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition C --kernel-class elementwise --scale-tier smoke --n 1 --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --max-new-tokens 2048 --output outputs/cluster2/c_smoke_n1.jsonl --modal-generation-gpu L4 --overwrite
```

- Generation GPU: `L4`
- Eval GPU: `L4` by runner default
- `max_new_tokens`: 2048
- Model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- Tokenizer revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- Output path: `outputs/cluster2/c_smoke_n1.jsonl`
- Modal route audit: `generation_calls=3`, `correctness_calls=3`, `route=c2_repair_loop`, `write_mode=overwrite`

CLI adaptations:

- The current runner requires `--scale-tier`; `--scale-tier smoke` was added.
- Generated conditions require immutable `--model-revision` and `--tokenizer-revision`; both were set to the established immutable revision.
- The runner default dtype schedule is `fp32,fp16,bf16`; no `--dtypes` override was supplied.
- `--modal-eval-gpu` was not required by the CLI and remained at the default `L4`.

## 3. Output artifact integrity

- Valid JSONL: yes
- Raw lines: 3
- Valid rows: 3
- Malformed JSON lines: none
- Ends with newline: yes
- Strict validator: `validate_cluster2_results_jsonl("outputs/cluster2/c_smoke_n1.jsonl", expected_rows=3)` passed.
- Content-hash sidecar exists: `outputs/cluster2/c_smoke_n1.jsonl.hashes.json`
- Sidecar schema version: `1`
- Sidecar generated-condition hashes: `C`

Row identity fields present in each row:

- `condition`, `kernel_class`, `kernel_name`, `dtype`, `base_seed`, `attempt_index`, `generation_mode`, `source_class`, `source_hash`

Row identities:

- `C / generated_row / new_c2_generation / elementwise / relu / fp32 / base_seed=0 / attempt_index=0`
- `C / generated_row / new_c2_generation / elementwise / relu / fp16 / base_seed=0 / attempt_index=0`
- `C / generated_row / new_c2_generation / elementwise / relu / bf16 / base_seed=0 / attempt_index=0`

The output supports durable append expectations after completion: it is newline-delimited, contains no partial line, has all rows parseable through the strict Cluster 2 row loader, and includes the generated-condition hash sidecar for `C`.

## 4. Blocker 1 verification - Level 0/1/2 ladder

Real smoke result:

- All rows terminate at Level 0 with canonical `F0_PARSE`.
- Level 0 evidence:
  - Top-level `failure_code=F0_PARSE`
  - `trace_summary.failure_code=F0_PARSE`
  - `trace_summary.public_failure_summary` records `SyntaxError: invalid syntax`
  - `repair_trace` contains exactly one attempt, attempt `0`
- Level 1 evidence:
  - Not reached in the real smoke because Level 0 failed.
  - The terminal `F0_PARSE` attribution is the expected skip reason for compile.
- Level 2 evidence:
  - Not reached in the real smoke because Level 0 failed.
  - `functional_success=false`, `repair_set_success=false`, and `eval_set_success=false` are present as terminal status fields.
- Call-order and skip evidence:
  - Modal route audit reported `generation_calls=3` and `correctness_calls=3`, matching one initial generation/evaluation attempt per row.
  - All rows have `attempt_index=0`.
  - All rows have a single-entry `repair_trace`.
  - No row records feedback prompt/content.

Shared eval ladder evidence from pre-run gates:

- Focused Level 0/1/2, generated eval, failure code, and repair tests passed: 237 selected tests.
- Durable/logger and runner/schema tests also passed before Modal invocation.

Interpretation: the live smoke verified F0 terminal behavior on the generated C path. It did not exercise Level 1 or Level 2 in the live rows because all candidates failed parse. Local tests verify Level 0 -> Level 1 -> Level 2 ordering and F2-only repair behavior.

## 5. Blocker 2 verification - durable writing

- Runner source uses `Cluster2JsonlAppendLogger(..., fsync=True)` for Cluster 2 output.
- Focused durable-result-writing tests passed: `43 passed, 343 deselected`.
- Relevant coverage includes per-row append/flush/fsync behavior, overwrite truncation at run start, strict partial JSONL rejection, resume prefix validation, and simulated mid-run exception preserving completed rows.
- Smoke artifact validity after run:
  - output exists,
  - sidecar exists,
  - row count is 3,
  - each row is newline-delimited,
  - no malformed partial line exists.

Remaining limitation: true in-run observation was not performed. The evidence is unit-test coverage for simulated mid-run durability plus completed smoke artifact integrity. No rerun was performed to observe in-run writes.

## 6. Canonical failure-code check

- Failure-code distribution: `F0_PARSE: 3`
- `F0_PARSE` is in the canonical taxonomy.
- Legacy labels are absent from the smoke rows.
- No noncanonical failure code was observed.

## 7. Metadata/provenance check

Per-row generated metadata:

- `model_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `tokenizer_revision`: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- `transformers_version`: `4.47.1`
- `tokenizers_version`: `0.21.1`
- `modal_image_sha`: `im-tU3VQyAbFvrusOxtlwspCN`
- `modal_image_provenance_sha256`: `82fb2024879bf2db36d75995b0704ade1a9c32dc2d3d3aff6207332995dc7535`
- `generation_metadata_schema_version`: `1`
- `model_id`: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
- `temperature`: `0.2`
- `max_new_tokens`: `2048`
- `stop_reason`: `eos_token`
- `xgrammar_version`: `0.1.33`

C-condition grammar fields:

- `grammar_variant`: `null`
- `grammar_path`: `null`
- `grammar_sha`: `null`
- `gbnf_parse_valid`: `null`
- `semantic_valid`: `null`
- `grammar_valid`: `null`
- `rejection_layer`: `null`

Metadata verdict: pass. Required provenance fields are populated, including `tokenizer_revision` and `modal_image_sha`. The C rows remain grammar-free.

## 8. Repair-loop behavior

- No row reached F2.
- No repair fired in the real smoke, as expected for F0 failures.
- No feedback prompt/content was emitted for F0 rows.
- Repair trace distribution: one trace entry per row, all attempt `0`, all `F0_PARSE`.
- F2 repair behavior remains verified by local fixture tests from the pre-run gate rather than by this live smoke.

## 9. Readiness decision

`C_N1_SMOKE_PASS_WITH_WARNINGS`

Reasons:

- Modal command completed.
- Output artifact exists and is valid JSONL.
- Row count is 3 due to default dtype schedule.
- All rows are `condition=C`, `kernel_class=elementwise`, grammar-free.
- Failure code is canonical.
- Required metadata/provenance fields are populated.
- F0 failures did not trigger repair feedback.
- Durable writing is supported by unit tests and completed-smoke artifact integrity.

Warnings:

- The live generated rows did not reach F2, so F2 repair behavior was verified by local tests only.
- True in-run durable-write observation was not performed.

## 10. Next recommendation

`RUN_C_N20`
