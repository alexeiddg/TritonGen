# Cluster 1 Task-Agnostic G n=20 Missing Rows and Token Exhaustion RCA

## 1. Executive summary

Artifact analyzed:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
```

Observed row count: **177**.

Expected row count: **180**.

Missing row count: **3**.

Rows with `stop_reason=max_new_tokens`: **72/177 = 40.68%**.

Main root-cause finding:

- The 3 missing rows are not JSONL corruption, duplicate filtering, expected-grid reconstruction error, or row-level compile failures. They are runner-level infrastructure failures before durable row append. The local artifact and sidecar do not preserve the exact exception text for each missing row, so the specific failing stage cannot be proven from local evidence alone.
- Token exhaustion is a real generation behavior under the current 2048-token budget. It is concentrated in reduction and matmul, and representative sources show degenerate repetitive continuations in launcher/meta-expression regions until the token cap, not simply longer valid implementations.

Final decision: **HOLD_FOR_FIX**.

Rationale: the current artifact is incomplete, per-cell infrastructure exception provenance is insufficient, and the token-exhaustion rate remains high enough that a same-configuration rerun is likely to reproduce substantial truncation even if it reaches 180 rows.

## 2. Artifact integrity

| Check | Result |
| --- | --- |
| Artifact exists | PASS |
| Raw line count | 177 |
| Valid JSON rows | 177 |
| Bad JSON lines | 0 |
| File ends with newline | PASS |
| Duplicate logical identities | 0 |
| Unexpected logical identities | 0 |
| Sidecar exists | PASS |
| Sidecar status | `failed_partial` |
| Sidecar expected rows | `180` |
| Sidecar written rows | `177` |
| Sidecar infrastructure failures | `3` |

The JSONL itself is internally well-formed. There are no partial or truncated JSON lines, and there is no evidence of append corruption.

Sidecar path:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl.meta.json
```

Relevant sidecar fields:

```text
status: failed_partial
expected_rows: 180
written_rows: 177
infrastructure_failures: 3
max_new_tokens: 2048
fail_fast: false
```

No `.log` file was found under `outputs/cluster1` for this run. The primary available run evidence is the JSONL, sidecar, previous n=20 report, and runner code.

## 3. Missing-row reconstruction

Expected grid:

```text
3 kernel classes x 3 dtypes x 20 seeds = 180 rows
kernel_class: elementwise, reduction, matmul
dtype: fp32, fp16, bf16
generation_seed: 0..19
```

Observed rows by kernel/dtype:

| kernel_class | dtype | observed rows | missing seeds |
| --- | ---: | ---: | --- |
| elementwise | fp32 | 20 | none |
| elementwise | fp16 | 20 | none |
| elementwise | bf16 | 20 | none |
| reduction | fp32 | 20 | none |
| reduction | fp16 | 20 | none |
| reduction | bf16 | 20 | none |
| matmul | fp32 | 19 | 5 |
| matmul | fp16 | 20 | none |
| matmul | bf16 | 18 | 0, 18 |

Missing logical rows:

| kernel_class | dtype | generation_seed | deterministic run_id |
| --- | --- | ---: | --- |
| matmul | fp32 | 5 | `7781901c-eece-552d-89c8-c97528013d5c` |
| matmul | bf16 | 0 | `c0d18f01-3528-540c-8e34-e00bd29f1a08` |
| matmul | bf16 | 18 | `6244e7a2-ed7e-52c1-b799-ad287c8bd389` |

Adjacent-row evidence:

| Missing row | Adjacent observed rows |
| --- | --- |
| matmul/fp32 seed 5 | seed 4 at line 125, seed 6 at line 126 |
| matmul/bf16 seed 0 | seed 1 at line 160 |
| matmul/bf16 seed 18 | seed 17 at line 176, seed 19 at line 177 |

The missing rows are not a single final tail loss. They are all within the matmul kernel class, with one early/mid-cell gap and two bf16 gaps.

## 4. Missing-row root-cause analysis

Runner behavior from `cluster1/experiments/run_cluster1_modal.py`:

- Each cell calls `_run_one_cell`.
- `_run_one_cell` performs generation, compile, conversion, and local metadata validation.
- Only after those steps does `append_result_jsonl` write the row.
- Any exception in that per-cell block increments `infrastructure_failures`, updates the sidecar, prints a failure line, and continues when `fail_fast=false`.
- If `written_rows != requested_rows` or `infrastructure_failures > 0`, the runner exits non-zero.

Logger behavior from `cluster1/results/logger.py`:

- `append_result_jsonl` writes one JSON object plus trailing newline.
- The current artifact has 177 parseable JSON rows and a final newline, so there is no local evidence of a partial row write.

Classification by missing row:

| Missing row | Classification | Evidence |
| --- | --- | --- |
| matmul/fp32 seed 5 | `UNKNOWN_MISSING_ROW_CAUSE` | Sidecar records an infrastructure failure and the row is absent. Adjacent seeds are present. No per-cell exception text is persisted locally. |
| matmul/bf16 seed 0 | `UNKNOWN_MISSING_ROW_CAUSE` | Sidecar records an infrastructure failure and the row is absent. Seed 1 is present, so this is not a cell-wide skip. No local failure log is available. |
| matmul/bf16 seed 18 | `UNKNOWN_MISSING_ROW_CAUSE` | Sidecar records an infrastructure failure and the row is absent. Seeds 17 and 19 are present. No local failure log is available. |

Ruled out:

- `JSONL_APPEND_OR_FLUSH_FAILURE`: unlikely from local evidence. The file has no malformed line and ends with newline.
- `VALIDATION_FILTERED_ROW`: not supported. The runner does not filter rows after validation; it raises and counts an infrastructure failure.
- `EXPECTED_GRID_RECONSTRUCTION_ERROR`: ruled out by deterministic `generation_seed` 0..19, validator missing-cell output, and matching runner iteration semantics.
- `MODAL_JOB_INTERRUPTION`: not proven. The job continued past at least two gaps, so a single global interruption is not a sufficient explanation.

Most precise supported statement: each missing row corresponds to an exception before durable row write in the per-cell runner path. The exact exception type is not recoverable from the local artifact/sidecar.

## 5. Token exhaustion summary

Overall:

```text
max_new_tokens rows: 72/177 = 40.68%
```

By kernel:

| kernel_class | max_new_tokens | observed rows | rate |
| --- | ---: | ---: | ---: |
| elementwise | 0 | 60 | 0.00% |
| reduction | 47 | 60 | 78.33% |
| matmul | 25 | 57 | 43.86% |

By dtype:

| dtype | max_new_tokens | observed rows | rate |
| --- | ---: | ---: | ---: |
| fp32 | 18 | 59 | 30.51% |
| fp16 | 28 | 60 | 46.67% |
| bf16 | 26 | 58 | 44.83% |

By kernel/dtype:

| kernel_class | dtype | max_new_tokens | observed rows | rate |
| --- | --- | ---: | ---: | ---: |
| elementwise | fp32 | 0 | 20 | 0.00% |
| elementwise | fp16 | 0 | 20 | 0.00% |
| elementwise | bf16 | 0 | 20 | 0.00% |
| reduction | fp32 | 12 | 20 | 60.00% |
| reduction | fp16 | 18 | 20 | 90.00% |
| reduction | bf16 | 17 | 20 | 85.00% |
| matmul | fp32 | 6 | 19 | 31.58% |
| matmul | fp16 | 10 | 20 | 50.00% |
| matmul | bf16 | 9 | 18 | 50.00% |

`generated_token_count` is not present in persisted `GenerationResult` rows, so the analysis cannot summarize exact generated token counts. The `stop_reason=max_new_tokens` field is nevertheless derived by the generator from the generated-token length reaching the configured limit.

Source-length diagnostic:

| kernel/stop_reason | rows | min chars | median chars | max chars |
| --- | ---: | ---: | ---: | ---: |
| elementwise/eos_token | 60 | 611 | 694 | 842 |
| reduction/eos_token | 13 | 685 | 928 | 1171 |
| reduction/max_new_tokens | 47 | 2579 | 5923 | 10863 |
| matmul/eos_token | 32 | 690 | 871 | 986 |
| matmul/max_new_tokens | 25 | 2452 | 6978 | 10687 |

The exhausted rows are much longer than normal completed rows.

## 6. Token exhaustion root-cause analysis

Representative truncated rows show repeated, malformed continuations rather than simply long but complete kernels.

Observed patterns:

- Repeated launcher/meta-function identifiers such as `lambda_metafunc_grid_config_2d_...`.
- Repeated shape/reshape fragments such as `ptr_reshape_1d_ptr_reshape_1d_...`.
- Repeated numeric or device fragments such as `_0_0_0_...`, `CUDAcudaCUDAcuda...`, or long `ifdevice_type...` strings.
- Repeated duplicate kernel skeleton starts in some reduction rows.
- Truncation often occurs in launcher allocation or grid construction, not inside a complete Triton kernel body.

Short representative excerpts:

```text
grid = lambda_metafunc_grid_config_2d_metafunc_grid_config_2d_metafunc_grid_config_2d_...
```

```text
C_ptr = torch.empty(C_shape, device=C_devicedtype_C_dtypecontiguous_ptr_reshape_1d_ptr_reshape_1d_...
```

```text
CUDAcudaCUDAcudaCUDAcudaCUDAcudaCUDAcuda...
```

These are degenerate continuations under the task-agnostic grammar surface. They point to model/grammar/prompt interaction causing runaway valid-token continuations, not to a normal need for thousands of tokens to express valid softmax or GEMM code.

No evidence was found that `grammar_final_state` is being used as an automatic stopping criterion. In `cluster1/generation/constrained_gen.py`, generation stops through Hugging Face `model.generate`; `grammar_final_state_observed` is recorded after generation, and `classify_stop_reason` can label `grammar_final_state` only if explicitly told that generation stopped on that condition. The current path does not pass `stopped_on_grammar_final_state=True`. In this artifact, stop reasons are only `eos_token` and `max_new_tokens`.

## 7. Relationship between truncation and grammar/compile outcomes

For `stop_reason=max_new_tokens` rows:

| Metric | Count | Rate |
| --- | ---: | ---: |
| rows | 72 | 100.00% |
| compile_success | 0 | 0.00% |
| grammar_valid | 0 | 0.00% |
| gbnf_parse_valid | 0 | 0.00% |
| semantic_valid | 0 | 0.00% |

Failure-code distribution among truncated rows:

| failure_code | Count |
| --- | ---: |
| `F0_PARSE` | 13 |
| `F1_RUNTIME` | 59 |

Rejection-layer distribution among truncated rows:

| rejection_layer | Count |
| --- | ---: |
| `gbnf_parse` | 72 |

For `stop_reason=eos_token` rows:

| Metric | Count | Rate |
| --- | ---: | ---: |
| rows | 105 | 100.00% |
| compile_success | 3 | 2.86% |
| grammar_valid | 49 | 46.67% |
| gbnf_parse_valid | 105 | 100.00% |
| semantic_valid | 49 | 46.67% |

Interpretation:

- In this artifact, every token-exhausted row fails the grammar surface parse.
- Token exhaustion is therefore not just a compile-performance issue. It directly prevents G acceptance for those rows.
- Completed rows can still fail semantic validation or compile/runtime checks, but they are structurally much more interpretable than token-exhausted rows.

## 8. Comparison to n=5

Prior n=5 artifact:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl
```

Comparison:

| Metric | n=5 | n=20 observed partial |
| --- | ---: | ---: |
| Rows | 45/45 | 177/180 |
| Compile success | 1/45 = 2.22% | 3/177 = 1.69% |
| Grammar valid | 12/45 = 26.67% | 49/177 = 27.68% |
| max_new_tokens | 18/45 = 40.00% | 72/177 = 40.68% |
| rejection_layer=`gbnf_parse` | 18/45 = 40.00% | 72/177 = 40.68% |

n=5 max-token rows by cell:

| cell | n=5 max_new_tokens |
| --- | ---: |
| elementwise/fp32 | 0 |
| elementwise/fp16 | 0 |
| elementwise/bf16 | 0 |
| reduction/fp32 | 4 |
| reduction/fp16 | 5 |
| reduction/bf16 | 4 |
| matmul/fp32 | 1 |
| matmul/fp16 | 1 |
| matmul/bf16 | 3 |

n=20 observed max-token rows by cell:

| cell | n=20 observed max_new_tokens |
| --- | ---: |
| elementwise/fp32 | 0 |
| elementwise/fp16 | 0 |
| elementwise/bf16 | 0 |
| reduction/fp32 | 12 |
| reduction/fp16 | 18 |
| reduction/bf16 | 17 |
| matmul/fp32 | 6 |
| matmul/fp16 | 10 |
| matmul/bf16 | 9 |

The n=20 partial artifact closely matches the n=5 truncation rate and grammar-valid rate. The 2048 budget did not remove the truncation pattern. The same broad cells dominate: reduction first, then matmul; elementwise is unaffected.

## 9. Rerun decision analysis

### Rerun with same 2048 immediately

Not recommended.

Reasons:

- The missing-row failure is not fully explained.
- The runner/sidecar does not preserve per-cell exception text for infrastructure failures.
- The token-exhaustion rate is stable across n=5 and n=20 at about 40%.
- A same-config rerun may produce 180 rows, but it would likely still contain a large block of GBNF-invalid truncations.

### Rerun after infrastructure fix

Recommended only after the run-completion issue is instrumented or fixed.

Minimum improvement before rerun:

- Persist per-cell infrastructure failure records, including run_id, kernel, dtype, seed, stage, exception type, and exception message.
- Preserve enough local evidence to distinguish generation RPC failure, compile RPC failure, local metadata revalidation failure, conversion failure, invariant failure, and append failure.

### Rerun with 2560

Potentially justified, but not as the immediate next action.

The 2048 truncation pattern is material and stable, but representative outputs show degenerate repetitive continuations. Raising to 2560 may only allow longer repetitive strings unless a small smoke confirms that the extra budget converts a meaningful fraction of reduction/matmul rows to `eos_token` and grammar-valid outputs.

Recommended sequence:

1. Fix or instrument infrastructure failure provenance.
2. Run a small, explicitly approved 2560 smoke focused on the affected non-elementwise cells before committing to a full n=20 rerun at 2560.
3. If 2560 materially reduces `max_new_tokens` without introducing new issues, rerun n=20 at the approved budget.

### Accept 177-row artifact with caveats

Not recommended for freeze or reporting.

The persisted rows are internally valid, but the artifact is incomplete and missing rows are all in `matmul`. Accepting it would introduce a kernel-class-specific missingness caveat that is not defensible as a final Cluster 1 task-agnostic G artifact.

### Run smaller 2560 smoke before rerun

Recommended as a future action after the infrastructure logging/failure provenance issue is addressed. This task did not run any smoke.

## 10. Final recommendation

Decision: **HOLD_FOR_FIX**.

Exact next action:

1. Add a follow-up fix brief for runner infrastructure-failure provenance. The brief should require per-cell failure records in the sidecar or a companion failure JSONL, without weakening strict result validation and without writing synthetic result rows.
2. Add or verify tests that a generation adapter exception, compile adapter exception, local validation exception, and append exception each produce durable failure diagnostics with cell identity.
3. After failure provenance is fixed, run a small, explicitly approved non-elementwise token-budget smoke at 2560 before deciding whether the full n=20 rerun should use 2048 or 2560.

Whether a code/config fix is needed first:

- Yes for infrastructure failure provenance.
- Likely yes or at least a controlled budget-smoke decision for token exhaustion.

Whether n=20 rerun should use 2048 or 2560:

- Do not decide solely from this incomplete artifact.
- 2048 is proven to retain about 40% truncation in n=5 and n=20 observed rows.
- 2560 should be evaluated with a small affected-cell smoke before a full rerun.

Whether missing rows invalidate the current artifact:

- Yes. The current n=20 artifact is invalid for final freeze/reporting because it has 177/180 rows and unexplained matmul missingness.

## 11. Appendix

Commands run:

```bash
rg "task_agnostic_g_aligned_pipeline_n20_l4|missing row|missing-row|row_count|expected_rows|180|177|infrastructure|max_new_tokens|stop_reason|token_budget|max tokens|generated_token_count|generated_tokens|finish_reason|truncat|timeout|exception|error" outputs audits cluster1 shared
```

```bash
rg "for .*dtype|for .*kernel|seed|generation_seed|base_seed|sample_index|append_result|jsonl|flush|overwrite|resume|row_id|attempt" cluster1 shared
```

```bash
rg "max_new_tokens|stop_reason|generated_token_count|eos_token|grammar_final_state|error|unknown|max_new_tokens" cluster1 shared
```

```bash
rg --files outputs/cluster1 audits | rg "(task_agnostic_g_aligned_pipeline_n20_l4|\\.meta\\.json$|\\.log$|n20)"
```

```bash
sed -n '1,260p' cluster1/results/logger.py
sed -n '1,1420p' cluster1/experiments/run_cluster1_modal.py
sed -n '1,260p' cluster1/generation/constrained_gen.py
sed -n '1,220p' cluster1/generation/provenance.py
sed -n '1,260p' shared/modal_harness/generation.py
```

```bash
.venv/bin/python - <<'PY'
# local JSONL integrity, missing-row, truncation, and source-pattern diagnostic
PY
```

Diagnostic output summary:

```text
RAW_LINE_COUNT 177
VALID_JSON_ROWS 177
BAD_JSON_LINES []
FILE_ENDS_WITH_NEWLINE True
SIDE_STATUS failed_partial
SIDE_INFRA_FAILURES 3
MISSING_EXPECTED_GRID [
  {'kernel_class': 'matmul', 'dtype': 'bf16', 'generation_seed': 0},
  {'kernel_class': 'matmul', 'dtype': 'bf16', 'generation_seed': 18},
  {'kernel_class': 'matmul', 'dtype': 'fp32', 'generation_seed': 5}
]
UNEXPECTED_GRID []
DUPLICATES []
```

Primary artifact:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl
```

Primary sidecar:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl.meta.json
```

Primary prior report:

```text
audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md
```

RCA report:

```text
audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md
```
