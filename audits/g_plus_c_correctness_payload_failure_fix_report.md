# G+C Correctness Payload Failure Fix Report

## 1. Executive summary

The G+C n=20 run failed because `cluster2/experiments/run_cluster2_modal.py` assumed every correctness wrapper contained a dict-valued `correctness_result`. Valid infrastructure-failure wrappers and malformed eval wrappers can omit that field, so the runner raised `RuntimeError: correctness payload did not contain correctness_result` before recording the logical sample row.

Fix status: implemented and validated. Missing or non-dict `correctness_result` now becomes an explicit `F3_EVAL_PIPELINE` result row with malformed-payload details in the generated trace summary, and the runner continues to the next scheduled row.

Final classification: `FIX_VERIFIED`.

## 2. Partial artifact investigation

Artifact: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`

Read-only diagnostics:

- Raw nonblank lines: 91
- Valid JSON rows: 91
- Bad JSON rows: 0
- Ends with newline: yes
- Dataclass-valid rows: 91
- All rows have generated metadata, trace summary, and nonempty repair trace.

Last completed row:

- Row number: 91
- Condition: `G+C`
- Kernel class: `reduction`
- Kernel name: `softmax`
- Dtype: `fp16`
- Base seed: 10
- Generation seed: 10
- Replay pair id: `reduction:fp16:10`
- Attempt index: 0
- Failure code: `F0_PARSE`
- Compile success: false
- Functional success: false
- Trace summary: `SyntaxError: '(' was never closed (<unknown>, line 21)`

Inferred next scheduled row:

- Expected row number: 92
- Condition: `G+C`
- Kernel class: `reduction`
- Kernel name: `softmax`
- Dtype: `fp16`
- Base seed: 11
- Generation seed: 11
- Replay pair id: `reduction:fp16:11`

Expected paper schedule:

- Total scheduled rows under current G replay skip policy: 177
- Missing replay controls already known by schedule policy: `matmul/fp32/5`, `matmul/bf16/0`, `matmul/bf16/18`

Per-cell observed row counts:

- `elementwise/fp32`: 20
- `elementwise/fp16`: 20
- `elementwise/bf16`: 20
- `reduction/fp32`: 20
- `reduction/fp16`: 11

Expected per-cell schedule counts:

- `elementwise/fp32`: 20
- `elementwise/fp16`: 20
- `elementwise/bf16`: 20
- `reduction/fp32`: 20
- `reduction/fp16`: 20
- `reduction/bf16`: 20
- `matmul/fp32`: 19
- `matmul/fp16`: 20
- `matmul/bf16`: 18

Distributions:

- `failure_code`: `F1_RUNTIME=75`, `F1_COMPILE=9`, `F2_NUMERIC_NAN=5`, `F0_PARSE=2`
- `compile_success`: `False=86`, `True=5`
- `functional_success`: `False=91`
- `repair_iteration`: field absent/`None` for all 91 rows
- `attempt_index`: `0=86`, `5=5`
- `repair_trace` length: `1=86`, `6=5`

Anomalies near crash:

- The crash did not occur at a cell boundary. It occurred mid-cell in `reduction/fp16`, after 11 of 20 scheduled rows for that cell.
- It was not entering matmul.
- The last three rows were ordinary recorded failures: two `F1_RUNTIME` rows with public summary `Input tensor must be 2D`, followed by one `F0_PARSE`.
- No earlier row recorded a payload/eval-pipeline failure code indicating the same malformed correctness wrapper had previously been handled.

## 3. Crash root cause

File/function/line:

- `cluster2/experiments/run_cluster2_modal.py`
- `_extract_correctness_result_dict`
- Old failure point: line 1253 in the reported run

Failing access:

- The runner called `payload.get("correctness_result")`.
- If that value was not a dict, it raised `RuntimeError("correctness payload did not contain correctness_result")`.

Expected payload shape:

- Normal correctness wrapper with top-level wrapper fields plus a nested `correctness_result` dict.
- The nested result carries `identity`, success flags, `failure_code`, public correctness error, and shape counters.

Observed/possible malformed shapes:

- Valid infrastructure wrapper with `correctness_status="INFRA_FAILURE"` and `infrastructure_failure`, but no `correctness_result`.
- Wrapper with error-like fields such as `error`, `error_message`, `error_msg`, `exception`, `message`, or `raw_error`.
- Non-dict or otherwise malformed wrapper returned by the adapter.

This is not G+C-specific in code structure. The same extractor is used by replay correctness and by generated `C`/`G+C` evaluation. The crash surfaced in G+C because the generated repair-loop evaluation callback raised before returning a terminal result to the durable row writer.

## 4. Fix implementation

Changed files:

- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/feedback/trace.py`
- `shared/eval/failure_taxonomy.py`
- `cluster2/tests/test_run_cluster2_modal.py`
- `shared/tests/test_failure_taxonomy.py`

Implementation details:

- Added `_extract_or_synthesize_correctness_result_dict`.
- Normal payloads still require dict-valued `correctness_result` and still run `_validate_correctness_identity`.
- Missing or non-dict `correctness_result` is converted into a synthetic terminal correctness result for the current request identity.
- The synthetic result records:
  - `functional_success=False`
  - `repair_set_success=False`
  - `eval_set_success=False`
  - `compile_success=False`
  - `failure_code="F3_EVAL_PIPELINE"`
  - `feedback=None`
  - zero shape counters
  - malformed-payload details in `correctness_error`
- The generated path stores that synthetic result in the existing attempt record, lets `run_repair_loop` terminate without feedback, builds the final row through the existing `generated_row` path, and appends it through the durable logger.
- The replay path also uses the defensive extractor, so infrastructure wrappers do not crash replay correctness processing.
- `cluster2/feedback/trace.py` now preserves full sanitized `F3_EVAL_PIPELINE` diagnostic summaries instead of applying the normal 200-character feedback-detail limit.

## 5. Failure taxonomy decision

No existing F3 code represented “evaluation pipeline/harness failed or returned malformed payload.” Existing F3 codes were `F3_OOB`, `F3_RACE`, and `F3_TIMEOUT`.

Added canonical code:

- `F3_EVAL_PIPELINE`

Rationale:

- The generated source did not produce an F0 parse, F1 compile/runtime, or F2 numerical failure at the time of the runner crash.
- The malformed wrapper is an infrastructure/evaluation-pipeline failure.
- F2 would incorrectly trigger repair semantics, while this failure should be recorded and terminal for that sample.
- `classify_failure` already preserves explicit canonical codes, so registering the new code is sufficient and is covered by tests.

## 6. Durable-write behavior

Malformed payload handling now returns a normal final row to the existing runner flow. The existing `Cluster2JsonlAppendLogger` validates the row against content-hash sidecars, writes one canonical JSON line, flushes, and fsyncs.

Regression coverage verifies:

- A malformed payload row is appended to JSONL.
- The JSONL remains valid.
- A subsequent scheduled row is appended after the malformed row.
- The runner does not stop at the malformed row.

The partial production artifact was not modified, rewritten, repaired, or hash-rerecorded.

## 7. Tests added/updated

Added/updated tests:

- `test_runner_records_malformed_correctness_payload_and_continues`
  - Parameterized over `C` and `G+C`.
  - Supplies a synthetic payload with no `correctness_result`.
  - Verifies no unhandled `RuntimeError`, `F3_EVAL_PIPELINE`, false success flags, preserved generated metadata, trace debug fields, no repair attempt, and continuation to the next scheduled row.
- `test_malformed_correctness_payload_durable_jsonl_remains_appendable`
  - Verifies malformed row plus subsequent row are both valid JSONL and reload through the result loader.
- `test_well_formed_correctness_payload_still_records_success`
  - Verifies normal correctness payload behavior remains unchanged.
- `test_f3_eval_pipeline_is_registered_and_preserved`
  - Verifies `F3_EVAL_PIPELINE` is in `FAILURE_CODES` and `classify_failure` preserves it.

Existing broader repair-loop and feedback tests verify that non-F2 codes do not generate repair feedback.

## 8. Validation results

Commands run with `.venv/bin/python`:

- `.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py -q`
  - Passed: 47 passed
- `.venv/bin/python -m pytest cluster2/tests -k "correctness_payload or correctness_result or malformed or eval_pipeline or infra or payload" -q`
  - Passed: 50 passed, 364 deselected
- `.venv/bin/python -m pytest cluster2/tests -k "durable or logger or jsonl or append or partial" -q`
  - Passed: 49 passed, 365 deselected
- `.venv/bin/python -m pytest shared/tests -k "failure_taxonomy or F3 or classify_failure" -q`
  - Passed: 30 passed, 497 deselected
- `.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_feedback_trace.py shared/tests/test_failure_taxonomy.py -q`
  - Passed: 62 passed
- `.venv/bin/python -m pytest cluster2/tests shared/tests -k "run_cluster2 or correctness or payload or failure_code or repair or result or logger" -q`
  - Passed: 380 passed, 561 deselected

No Modal command, GPU job, generation command, G+C n=20 rerun, C n=20 run, artifact rewrite, grammar edit, Cluster 1 artifact edit, or hash rerecording was performed.

## 9. Rerun recommendation

Recommendation: `RUN_SMALL_G_PLUS_C_PAYLOAD_SMOKE`

Reasoning: the local runner robustness bug is fixed and regression-tested, but the exact production malformed payload came from remote correctness plumbing. Run a small G+C payload smoke first to verify the remote wrapper path records `F3_EVAL_PIPELINE` instead of crashing if the malformed shape recurs. After that smoke passes, the full G+C n=20 paper run can be resumed or rerun according to the experiment policy.
