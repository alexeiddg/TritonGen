# Cluster 1 Task-Agnostic G n=5 L4 Report

## 1. Executive summary

Final run status: `N5_RUN_CONFIRMED`.

Artifact: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl`.

Observed row count: 45 rows, matching the expected 3 kernels x 3 dtypes x 5 generations schedule.

Strict metadata gate: PASS. The validator reported 0 file failures, 0 row-count failures, 0 deserialization failures, 0 invariant failures, 0 masked-token-rate failures, 0 generation metadata failures, 0 compile-results-by-dtype failures, 0 missing cells, 0 unexpected cells, 0 duplicate identities, 0 seed failures, and 0 sample-size failures.

Overall compile_success rate: 1/45 = 2.22%.

Overall grammar_valid rate: 12/45 = 26.67%.

Main observed bottleneck: non-elementwise rows remain token-budget sensitive. `stop_reason=max_new_tokens` occurred in 18/45 rows, concentrated in reduction and matmul. The run used the current uniform `max_new_tokens=2048` default, so the 2048 bump reduced neither the need for caution nor the need for a token-budget decision before n=20.

N20 planning recommendation: `HOLD_FOR_TOKEN_BUDGET_FIX`.

## 2. Run provenance

Exact Modal command:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster1.experiments.run_cluster1_modal --condition G --grammar-variant task_agnostic --kernel-class all --n 5 --output outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl --modal-generation-gpu L4 --overwrite
```

Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-vdVwAPAhxlDQsvyJ7FiIa6
```

Provenance fields observed in the artifact:

| Field | Value |
| --- | --- |
| model_id | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` |
| model_revision | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| tokenizer_revision | `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` |
| max_new_tokens | `2048` from run metadata sidecar |
| Modal GPU | `L4` |
| grammar_variant | `task_agnostic` |
| grammar_path | `cluster1/grammar/triton_kernel_agnostic.gbnf` |
| grammar_sha | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` |
| xgrammar_version | `0.1.33` |
| transformers_version | `4.47.1` |
| tokenizers_version | `0.21.1` |
| modal_image_sha | present, value `unknown` in all 45 rows |

Sidecar run metadata:

| Field | Value |
| --- | --- |
| status | `completed` |
| expected_rows | `45` |
| written_rows | `45` |
| infrastructure_failures | `0` |
| tokenizer_revision_policy | `same_repo_model_revision` |

`modal_image_sha` remains present but unknown. This did not fail the strict metadata gate used for this development n=5 run because the critical non-unknown provenance checks are model revision, tokenizer revision, xgrammar version, transformers version, and tokenizers version.

## 3. Artifact integrity

Expected row count: 45.

Observed row count: 45.

Kernel/dtype cell counts:

| kernel_class | dtype | rows |
| --- | --- | ---: |
| elementwise | bf16 | 5 |
| elementwise | fp16 | 5 |
| elementwise | fp32 | 5 |
| matmul | bf16 | 5 |
| matmul | fp16 | 5 |
| matmul | fp32 | 5 |
| reduction | bf16 | 5 |
| reduction | fp16 | 5 |
| reduction | fp32 | 5 |

Missing field check: PASS. Required fields were present on every row.

Tokenizer revision check: PASS. All 45 rows had tokenizer_revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; no row had null, empty, or `unknown`.

Model revision check: PASS. All 45 rows had model_revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; no row had null, empty, or `unknown`.

Grammar SHA check: PASS. Every row matched `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`, and the local grammar file hash matched the same value.

Grammar-valid invariant check: PASS. For every row, `grammar_valid == (gbnf_parse_valid and semantic_valid)`.

Rejection-layer invariant check: PASS. Valid rows had no rejection layer, and invalid rows had a populated rejection layer.

Strict metadata gate status: PASS.

## 4. Overall metrics

| Metric | Count | Rate |
| --- | ---: | ---: |
| compile_success | 1/45 | 2.22% |
| grammar_valid | 12/45 | 26.67% |
| gbnf_parse_valid | 27/45 | 60.00% |
| semantic_valid | 12/45 | 26.67% |

Failure-code distribution:

| failure_code | Count |
| --- | ---: |
| `<null>` | 1 |
| `F0_PARSE` | 1 |
| `F1_COMPILE` | 1 |
| `F1_RUNTIME` | 42 |

Compile-error-type distribution:

| compile_error_type | Count |
| --- | ---: |
| `<null>` | 1 |
| `CompilationError` | 1 |
| `RuntimeError` | 42 |
| `SignatureError` | 1 |

The single `<null>` failure_code and compile_error_type row is the one compile-success row.

## 5. Metrics by kernel/dtype

| kernel_class | dtype | rows | compile_success_count | compile_success_rate | grammar_valid_count | grammar_valid_rate | gbnf_parse_valid_rate | semantic_valid_rate | dominant rejection_layer | dominant stop_reason |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| elementwise | bf16 | 5 | 0 | 0.00% | 5 | 100.00% | 100.00% | 100.00% | `<null>` | `eos_token` |
| elementwise | fp16 | 5 | 0 | 0.00% | 4 | 80.00% | 100.00% | 80.00% | `<null>` | `eos_token` |
| elementwise | fp32 | 5 | 1 | 20.00% | 3 | 60.00% | 100.00% | 60.00% | `<null>` | `eos_token` |
| matmul | bf16 | 5 | 0 | 0.00% | 0 | 0.00% | 40.00% | 0.00% | `gbnf_parse` | `max_new_tokens` |
| matmul | fp16 | 5 | 0 | 0.00% | 0 | 0.00% | 80.00% | 0.00% | `semantic_validator` | `eos_token` |
| matmul | fp32 | 5 | 0 | 0.00% | 0 | 0.00% | 80.00% | 0.00% | `semantic_validator` | `eos_token` |
| reduction | bf16 | 5 | 0 | 0.00% | 0 | 0.00% | 20.00% | 0.00% | `gbnf_parse` | `max_new_tokens` |
| reduction | fp16 | 5 | 0 | 0.00% | 0 | 0.00% | 0.00% | 0.00% | `gbnf_parse` | `max_new_tokens` |
| reduction | fp32 | 5 | 0 | 0.00% | 0 | 0.00% | 20.00% | 0.00% | `gbnf_parse` | `max_new_tokens` |

## 6. Rejection-layer analysis

Rejection-layer distribution:

| rejection_layer | Count | Rate |
| --- | ---: | ---: |
| `<null>` | 12 | 26.67% |
| `gbnf_parse` | 18 | 40.00% |
| `semantic_validator` | 15 | 33.33% |

The failures are split between GBNF parse rejection and semantic-validator rejection. There is no evidence of unknown rejection-layer behavior: all invalid rows had a rejection layer, and all valid rows had `<null>`.

Elementwise rows dominate accepted grammar-valid outputs: 12/15 elementwise rows were grammar_valid, while all reduction and matmul rows were grammar_invalid. Matmul reached GBNF parse validity more often than reduction, but failed semantic validation in most fp16/fp32 rows.

## 7. Stop-reason analysis

Stop-reason distribution:

| stop_reason | Count | Rate |
| --- | ---: | ---: |
| `eos_token` | 27 | 60.00% |
| `max_new_tokens` | 18 | 40.00% |

`max_new_tokens` truncation remains a material issue at the current 2048 budget. It is concentrated outside elementwise:

| Cell | max_new_tokens rows |
| --- | ---: |
| reduction/fp16 | 5/5 |
| reduction/fp32 | 4/5 |
| reduction/bf16 | 4/5 |
| matmul/bf16 | 3/5 |
| matmul/fp16 | 1/5 |
| matmul/fp32 | 1/5 |
| elementwise/* | 0/15 |

The 2048 token budget is not sufficient for an unbiased n=20 planning run as-is. 2560 should be considered before n=20, or the team should explicitly accept the residual truncation bias. Per-kernel budgets were not used here and should remain out of scope unless a later methodology decision accepts that confound.

## 8. Failure-code analysis

Canonical failure-code distribution:

| failure_code | Interpretation | Count |
| --- | --- | ---: |
| `<null>` | compile success | 1 |
| `F0_PARSE` | grammar-surface parse failure | 1 |
| `F1_COMPILE` | compile failure | 1 |
| `F1_RUNTIME` | runtime failure | 42 |

Most compile failures are classified as `F1_RUNTIME`. This agrees with `compile_error_type=RuntimeError` for 42 rows. The one `CompilationError` row maps to `F1_COMPILE`, and the one compile-success row has null compile error and null failure_code.

One row has `compile_error_type=SignatureError` and `failure_code=F0_PARSE`. This is interpretable because the row is grammar-invalid at the GBNF layer, so the canonical failure is assigned to the grammar-surface parse failure rather than the downstream compile-check category.

## 9. Masked-token-rate analysis

Overall masked-token-rate summary:

| Count | Min | Max | Mean | Median |
| ---: | ---: | ---: | ---: | ---: |
| 45 | 0.729088 | 0.851857 | 0.783639 | 0.788418 |

By kernel/dtype:

| kernel_class | dtype | count | min | max | mean | median |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| elementwise | bf16 | 5 | 0.800085 | 0.805290 | 0.803707 | 0.805290 |
| elementwise | fp16 | 5 | 0.800962 | 0.806477 | 0.804199 | 0.804039 |
| elementwise | fp32 | 5 | 0.836081 | 0.851857 | 0.843281 | 0.841904 |
| matmul | bf16 | 5 | 0.740859 | 0.755322 | 0.745505 | 0.741079 |
| matmul | fp16 | 5 | 0.729088 | 0.811026 | 0.756351 | 0.748355 |
| matmul | fp32 | 5 | 0.746621 | 0.816784 | 0.792945 | 0.794940 |
| reduction | bf16 | 5 | 0.745522 | 0.807433 | 0.767758 | 0.750648 |
| reduction | fp16 | 5 | 0.745901 | 0.788418 | 0.766540 | 0.769809 |
| reduction | fp32 | 5 | 0.747796 | 0.805614 | 0.772464 | 0.773578 |

`masked_token_rate` is a masking diagnostic, not acceptance evidence. It should not be read as grammar acceptance, compile likelihood, or correctness.

`generated_token_count` was not present as an integer field in any row, so no generated-token-count summary is available from the artifact.

## 10. Comparison against previous diagnostic n=5

The current grammar_valid rate is 26.67%, close to the expected prior diagnostic range of roughly 28-30%.

The current `max_new_tokens` truncation rate is 40.00%, higher than the expected prior diagnostic pattern of roughly 33%. This run used `max_new_tokens=2048`, not 1536, so the result is a stronger signal that reduction and some matmul cells still hit the budget.

No statistical significance is claimed from this comparison. This is a development-scale n=5 run and should be used as a planning signal, not paper-scale evidence.

## 11. Cell-level findings

Best-performing compile cell: elementwise/fp32, with 1/5 compile_success and 3/5 grammar_valid.

Worst-performing compile cells: eight of nine cells had 0/5 compile_success.

Cells with 0/5 compile_success:

- elementwise/bf16
- elementwise/fp16
- matmul/bf16
- matmul/fp16
- matmul/fp32
- reduction/bf16
- reduction/fp16
- reduction/fp32

Cells with high grammar_valid but low compile_success:

- elementwise/bf16: 5/5 grammar_valid, 0/5 compile_success
- elementwise/fp16: 4/5 grammar_valid, 0/5 compile_success
- elementwise/fp32: 3/5 grammar_valid, 1/5 compile_success

Cells with low grammar_valid:

- all reduction cells: 0/5 grammar_valid
- all matmul cells: 0/5 grammar_valid

Cells dominated by `max_new_tokens`:

- reduction/fp16: 5/5
- reduction/fp32: 4/5
- reduction/bf16: 4/5
- matmul/bf16: 3/5

## 12. N20 planning recommendation

Recommendation: `HOLD_FOR_TOKEN_BUDGET_FIX`.

Rationale: the run is valid, interpretable, and provenance-complete, but 18/45 rows stopped at `max_new_tokens` despite the current 2048 default. That truncation is concentrated in reduction and matmul, and it is high enough to likely bias an n=20 planning run if left unchanged.

The next token-budget decision should remain methodologically uniform. A uniform 2560 smoke or development check is more defensible than per-kernel budgets or adaptive retries.

## 13. Remaining risks

Development-scale statistical uncertainty: n=5 per cell is small. The 2.22% compile rate is a planning signal, not a statistically conclusive estimate.

Token-budget risk: 2048 remains insufficient for reduction and matmul, with 40.00% overall truncation and 86.67% truncation across reduction rows.

Methodology risk: increasing to 2560 changes the current run configuration and should be treated as a pre-n20 methodology/config update, not a repair loop over this artifact.

Infrastructure/provenance risk: tokenizer_revision and model_revision are fixed end-to-end, but `modal_image_sha` remains `unknown` in row metadata. This did not fail the strict gate for this run but should be tracked if paper-scale provenance requirements become stricter.

Reporting/documentation follow-ups: document that this n=5 run is the first metadata-valid aligned development-scale run after the tokenizer provenance fix, while also documenting that it is not sufficient to proceed to n=20 without a token-budget decision.

## 14. Appendix

Artifact path:

```text
outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl
```

Report path:

```text
audits/task_agnostic_g_aligned_pipeline_n5_l4_report.md
```

Pre-run commands:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from collections import Counter

p = Path("outputs/cluster1/smoke/tokenizer_revision_metadata_smoke_task_agnostic_g_elementwise_n1.jsonl")
if not p.exists():
    raise SystemExit("TOKENIZER_REVISION_SMOKE_ARTIFACT_MISSING")

rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
if not rows:
    raise SystemExit("TOKENIZER_REVISION_SMOKE_EMPTY")

bad = [
    (i, r.get("tokenizer_revision"))
    for i, r in enumerate(rows, start=1)
    if r.get("tokenizer_revision") in (None, "", "unknown")
]

print("smoke_rows", len(rows))
print("tokenizer_revisions", dict(Counter(r.get("tokenizer_revision") for r in rows)))

if bad:
    raise SystemExit(f"TOKENIZER_REVISION_SMOKE_FAILED: {bad}")

print("TOKENIZER_REVISION_SMOKE_CONFIRMED")
PY
```

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

p = Path("audits/final_pre_n5_re_audit.md")
if not p.exists():
    print("FINAL_PRE_N5_RE_AUDIT_NOT_FOUND: continuing only if this was intentionally not required")
    raise SystemExit(0)

text = p.read_text()
if "GO" not in text:
    raise SystemExit("FINAL_PRE_N5_RE_AUDIT_NOT_GO")

print("FINAL_PRE_N5_RE_AUDIT_GO_CONFIRMED")
PY
```

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from shared.eval.content_hashes import file_sha256

p = Path("cluster1/grammar/triton_kernel_agnostic.gbnf")
h = file_sha256(p)
expected = "7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32"

print("grammar_sha", h)

if h != expected:
    raise SystemExit(f"GRAMMAR_HASH_MISMATCH: got {h}, expected {expected}")
PY
```

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 -v
```

```bash
.venv/bin/python -m cluster1.experiments.run_cluster1_modal --help
```

The help command exited 0 but printed no help text, so `cluster1/experiments/run_cluster1_modal.py` was inspected directly. The source confirmed the active flags and `DEFAULT_MAX_NEW_TOKENS = 2048`.

```bash
.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_run_cluster1_modal.py cluster1/tests/test_validate_cluster1_results.py cluster1/tests/test_compile_check.py cluster1/tests/test_signature_gate_consistency.py shared/tests/test_shape_schedule_consistency.py shared/tests/test_eval_failure_taxonomy.py -q
```

Validation outputs:

```text
TOKENIZER_REVISION_SMOKE_CONFIRMED
FINAL_PRE_N5_RE_AUDIT_GO_CONFIRMED
grammar_sha 7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32
cluster2/tests/test_modal_generation_c2.py::test_remote_generator_generate_one_hash_matches_phase_minus_1 PASSED
239 passed, 7 skipped
```

Modal completion output:

```text
wrote 45 rows to outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl
Stopping app - local entrypoint completed.
App completed.
```

Strict validation command:

```bash
.venv/bin/python -m cluster1.experiments.validate_cluster1_results --input outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl --condition G --kernel-class all --n 5 --grammar-variant task_agnostic --require-generation-metadata
```

Strict validation output:

```text
Cluster 1 result validation: PASS
row_count: 45 expected=45
condition_coverage: expected=['G'] observed=['G']
kernel_coverage: expected=['elementwise', 'reduction', 'matmul'] observed=['elementwise', 'matmul', 'reduction']
grammar_variant_coverage: expected=['task_agnostic'] observed=['task_agnostic']
dtype_coverage: expected=['fp32', 'fp16', 'bf16'] observed=['bf16', 'fp16', 'fp32']
file_failures: 0
row_count_failures: 0
deserialization_failures: 0
invariant_failures: 0
masked_token_rate_failures: 0
generation_metadata_failures: 0
compile_results_by_dtype_failures: 0
missing_cells: 0
unexpected_cells: 0
duplicate_identities: 0
seed_failures: 0
sample_size_failures: 0
```

Raw artifact analysis result:

```text
ROW_COUNT 45
compile_success_count 1
compile_success_rate 0.022222222222222223
grammar_valid_count 12
grammar_valid_rate 0.26666666666666666
gbnf_parse_valid_count 27
gbnf_parse_valid_rate 0.6
semantic_valid_count 12
semantic_valid_rate 0.26666666666666666
rejection_layer {'<null>': 12, 'gbnf_parse': 18, 'semantic_validator': 15}
stop_reason {'eos_token': 27, 'max_new_tokens': 18}
failure_code {'<null>': 1, 'F0_PARSE': 1, 'F1_COMPILE': 1, 'F1_RUNTIME': 42}
masked_token_rate count=45 min=0.7290882468131753 max=0.8518569552403374 mean=0.7836388693434625 median=0.7884177358864934
POST_RUN_ANALYSIS_PASS
```

Optional analyzer:

```bash
.venv/bin/python -m cluster1.experiments.analyze_cluster1 --input outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4.jsonl --output outputs/cluster1/task_agnostic_g_aligned_pipeline_n5_l4_summary.md --condition G --kernel-class all --n 5 --grammar-variant task_agnostic --validate --allow-small-matrix
```

The first analyzer attempt without `--allow-small-matrix` failed because the analyzer expected at least 20 rows per cell. The adapted command above completed for this n=5 development matrix.
