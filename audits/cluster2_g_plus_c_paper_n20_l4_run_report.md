# Cluster 2 G+C Paper n20 L4 Run Report

## 1. Executive summary

Run status: `G_PLUS_C_RUN_COMPLETE`.

Artifact: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.

Rows written: 177 valid JSONL rows. This is complete for the current covered-row G+C schedule and matches the known 177/180 task-agnostic G replay coverage caveat.

The prior unhandled `correctness_result` crash did not recur. Malformed correctness payloads with `missing_field=correctness_result` did recur on 5 rows, but they were recorded durably as `F3_EVAL_PIPELINE` and the run continued through row 177.

Compile success: 4/177 = 2.26%.

Functional success: 0/177 = 0.00%.

F2 reached: 4/177 rows, all `F2_NUMERIC_NAN`.

Main outcome: the G+C artifact is valid for covered-row inspection and is aggregation-ready from the G+C side, with the explicit 177/180 replay coverage caveat.

## 2. Command and environment

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal --condition G+C --kernel-class all --scale-tier paper --n 20 --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a --grammar-variant task_agnostic --max-new-tokens 2048 --output outputs/cluster2/g_plus_c_paper_n20_l4.jsonl --modal-generation-gpu L4 --modal-eval-gpu L4 --overwrite
```

GPU: L4 for generation and evaluation.

Model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.

Tokenizer revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`.

Max new tokens: 2048.

Grammar variant: `task_agnostic`.

Output path: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.

## 3. Monitoring notes

Modal app: `ap-iuNj0gScfLM1GIDWvbsEQ7`.

Observed Modal timestamps: started at 2026-05-20 23:17:36 CST and completed at 2026-05-21 05:37:13 CST, about 6h 19m 37s.

Cost estimate: not visible in the CLI output or log tails.

Dashboard/log observations: the logs showed model checkpoint loading and repeated GPU health warnings of `Xid 31` MMU faults early in the run. No Python traceback was emitted in the primary run stream.

Throughput notes: elementwise completed first and persisted normally. Reduction rows were slower and uneven; at least one row exceeded 5 minutes, was allowed to complete for inspection, and the run continued. The run crossed the previous row-91 failure point and completed all 177 scheduled rows.

Manual kill: not needed.

## 4. Artifact integrity

Basic JSONL validation passed.

- Raw lines: 177.
- Valid JSON rows: 177.
- Bad JSON lines: 0.
- Ends with newline: true.
- Durable output behavior: rows persisted incrementally during the run, and the final file is complete for the covered schedule.

Expected row count: nominal 180, covered-row expected 177 due to the known G replay gap.

Cell coverage:

| kernel_class | dtype | rows |
|---|---:|---:|
| elementwise | bf16 | 20 |
| elementwise | fp16 | 20 |
| elementwise | fp32 | 20 |
| matmul | bf16 | 18 |
| matmul | fp16 | 20 |
| matmul | fp32 | 19 |
| reduction | bf16 | 20 |
| reduction | fp16 | 20 |
| reduction | fp32 | 20 |

## 5. G+C condition integrity

Condition: `G+C` for 177/177 rows.

Grammar active: true for 177/177 rows.

Grammar variant: `task_agnostic` for 177/177 rows.

Grammar path: `cluster1/grammar/triton_kernel_agnostic.gbnf` for 177/177 rows.

Grammar SHA: `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` for 177/177 rows.

`template_upper_bound` was not used.

## 6. Metadata/provenance validation

Tokenizer revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` for 177/177 rows.

Model revision: `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` for 177/177 rows.

Modal image SHA: `im-tU3VQyAbFvrusOxtlwspCN` for 177/177 rows.

Package versions:

- `transformers_version`: `4.47.1`.
- `tokenizers_version`: `0.21.1`.
- `xgrammar_version`: `0.1.33`.

Generated metadata shape: current nested `generated_metadata` fields are present and validated for grammar routing, grammar validity, rejection layer, stop reason, model/tokenizer provenance, package versions, and Modal image provenance.

## 7. Evaluation/failure behavior

Failure code distribution:

| failure_code | rows |
|---|---:|
| F1_RUNTIME | 146 |
| F0_PARSE | 12 |
| F1_COMPILE | 10 |
| F3_EVAL_PIPELINE | 5 |
| F2_NUMERIC_NAN | 4 |

Compile success distribution:

| compile_success | rows |
|---|---:|
| false | 173 |
| true | 4 |

Functional success distribution:

| functional_success | rows |
|---|---:|
| false | 177 |

F2 count: 4.

F3/infrastructure count: 5.

Malformed correctness payload behavior: 5 rows recorded `F3_EVAL_PIPELINE` with a public summary beginning `Malformed correctness payload: missing_field=correctness_result`. These were recorded instead of crashing, including row 92, and the run continued through completion.

## 8. Repair-loop analysis

Rows reaching F2: 4.

Rows repaired successfully: 0.

Terminal attempt distribution:

| attempt_index | rows |
|---:|---:|
| 0 | 173 |
| 5 | 4 |

Repair trace length distribution:

| trace length | rows |
|---:|---:|
| 1 | 173 |
| 6 | 4 |

The 4 F2 rows exhausted the repair budget through terminal attempt 5 and remained `F2_NUMERIC_NAN`.

F0/F1 rows avoided feedback repair traces under the validation checks.

## 9. Replay coverage caveat

The active task-agnostic G replay artifact is `g_task_agnostic_aligned_pipeline_n20_l4`.

Observed G replay rows: 177/180.

Missing rows:

- `matmul/fp32`, sample_index 5.
- `matmul/bf16`, sample_index 0.
- `matmul/bf16`, sample_index 18.

The Modal summary reported the same coverage warning under `COVERAGE_WARNING_SKIP_MISSING`. The run output reflects expected covered-row scheduling: 177 rows, not a silent 180-row fill.

## 10. Aggregation readiness

`READY_WITH_COVERAGE_CAVEAT`.

The G+C artifact itself is valid for covered-row aggregation. The separate factorial analyzer step is blocked by input schema incompatibility in the non-G+C inputs, documented in `audits/factorial_2x2_preliminary_analysis_report.md`.

## 11. Next recommendation

`HOLD_FOR_MANUAL_REVIEW`.

Recommended action: decide whether to update the analyzer or provide schema-normalized input artifacts for the preliminary 2x2 analysis. The G+C run does not need a rerun for the prior `correctness_result` crash.
