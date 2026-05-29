# C2 Durable Result Writing Fix Report

## 1. Executive summary

The Cluster 2 durable-result-writing blocker is fixed for the C2 runner path. Completed logical rows are now appended to JSONL immediately, flushed, and fsynced before the runner proceeds to the next logical row. A mid-run interruption preserves previously completed rows as valid JSONL.

Final classification: **FIX_VERIFIED_FOR_DURABILITY_WITH_UNRELATED_BROAD_REGRESSION**.

Files modified:

- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/results/__init__.py`
- `cluster2/results/dataclass.py`
- `cluster2/results/logger.py`
- `cluster2/tests/test_generated_eval_ladder.py`
- `cluster2/tests/test_results_logger.py`
- `cluster2/tests/test_run_cluster2_modal.py`
- `shared/analysis/factorial.py`
- `shared/eval/aggregation.py`
- `shared/eval/metrics/repair.py`
- `shared/tests/test_aggregation.py`
- `shared/tests/test_factorial_analysis.py`

No Modal command, GPU job, actual generation run, C n=1, C n=20, G+C, frozen artifact edit, output rewrite, or hash re-recording was performed.

## 2. Root cause

C2 previously buffered the whole run in memory in `cluster2/experiments/run_cluster2_modal.py::run_cluster2` using `rows: list[Cluster2EvalRow]`. All routes appended to that in-memory list, and the runner wrote results only after every requested condition completed by calling `_write_rows(config, rows, content_hash_sidecar)`.

`_write_rows` delegated to `cluster2/results/logger.py::write_cluster2_results_jsonl`, which materialized all rows as a tuple and then wrote the whole JSONL artifact with `output_path.write_text(serialize_cluster2_rows(row_tuple), encoding="utf-8")`. The output file was therefore opened and written only at the end of the run.

That meant a Modal interruption after many completed samples but before `_write_rows` could lose all completed rows. This is unacceptable for C n=20 because the final logical row count is 180, while each logical row may require an initial candidate plus up to the repair budget. With repair budget 5, the worst case is 180 logical rows x 6 generated candidates = 1080 generated candidates.

## 3. Implementation summary

Added `Cluster2JsonlAppendLogger` in `cluster2/results/logger.py`. It is a context manager that initializes the target output, writes the content-hash sidecar, and appends one canonical C2 row at a time.

The runner now opens `Cluster2JsonlAppendLogger` after all preflight checks and records rows through a `record_row` callback. The callback validates paper-scale generated metadata for the row, appends the row to JSONL, and only then adds it to the in-memory return payload.

Flush/fsync policy:

- Each appended row is written as one JSON object plus trailing newline.
- The file object is flushed after every row.
- `os.fsync(file.fileno())` is called after every appended row.
- The overwrite-mode sidecar is written through a temporary file and atomic replace, with fsync of the temp file and containing directory when fsync is enabled.

Overwrite behavior:

- `mode="overwrite"` truncates only the target JSONL file at logger open, before any row work begins.
- The target content-hash sidecar is atomically replaced.
- Unrelated sidecars and artifacts are untouched.
- `mode="resume"` requires an existing JSONL output and sidecar, validates the sidecar hash signature, requires the existing output to end with a newline, and consumes matching existing prefix rows without appending duplicates.
- On successful resume exit, unconsumed existing rows are rejected so stale rows from a larger or different prior output cannot remain silently.

Partial-output behavior:

- Completed rows are valid newline-delimited JSON objects.
- `load_cluster2_results_jsonl` continues to parse strict C2 row JSONL.
- New `validate_cluster2_results_jsonl(..., expected_rows=N)` keeps full-run row-count validation strict.
- `validate_cluster2_results_jsonl(..., expected_rows=N, allow_partial=True)` permits diagnostic inspection of a short partial file without weakening strict validation.

Repair trace/final-row behavior:

- `_run_generated_cell` now returns only the terminal row for the logical sample.
- Intermediate repair attempts are not emitted as final result rows.
- The terminal row records the terminal `attempt_index`, terminal `generation_seed`, terminal status fields, and a compact `repair_trace` tuple of `TraceSummary` entries.
- Shared C2 aggregation, pass@1, convergence, and factorial paired-replay validation now derive attempt-zero visibility from `repair_trace` when a generated row is represented only by its terminal row.
- The expected C n=20 final row count remains 180, not up to 1080.

## 4. Durability guarantees

After each completed logical row, the row has been serialized canonically, written with a trailing newline, flushed, and fsynced. A crash after that point should preserve that completed row in the output JSONL.

The current in-progress logical row can still be lost if the process dies before `record_row` completes.

The implementation avoids malformed completed rows by appending only complete JSON objects with newlines. A crash during the low-level filesystem write remains subject to filesystem semantics, but the app flushes and fsyncs after each row and uses append mode for row writes.

Partial outputs should be interpreted as durable prefixes. Strict full-run validation must still use the expected row count and fail on missing rows. Diagnostic inspection can use `allow_partial=True`.

## 5. Tests added/updated

Added or updated tests covering:

- Append one row: `test_durable_append_logger_writes_one_valid_jsonl_row`
- Append multiple rows incrementally: `test_durable_append_logger_persists_multiple_rows_incrementally`
- Simulated mid-run crash: `test_runner_durable_rows_survive_mid_run_exception`
- Overwrite behavior: `test_durable_append_logger_overwrite_truncates_target_at_start`
- No silent duplicate append on resume: `test_durable_append_logger_resume_does_not_duplicate_existing_rows`
- Stale extra resume rows rejected: `test_durable_append_logger_resume_rejects_stale_extra_rows`
- Strict validation remains strict: `test_strict_row_count_validation_rejects_partial_jsonl`
- Repair final-row semantics: `test_runner_repair_attempts_preserve_repair_loop_seed_schedule` and `test_generated_c_f2_failure_is_only_case_that_fires_repair`
- Terminal-row attempt-zero analysis: `test_pass_at_1_initial_uses_repair_trace_for_terminal_rows`, `test_lift_accepts_terminal_repair_row_with_attempt_zero_trace`, and `test_validate_paired_replay_dataframe_accepts_repair_trace_attempt_zero`
- Fsync path: `test_durable_append_logger_fsyncs_once_per_appended_row`

## 6. Validation results

Passed:

- `.venv/bin/python -m pytest cluster2/tests/test_results_logger.py -q`
  - 36 passed
- `.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py -q`
  - 38 passed
- `.venv/bin/python -m pytest cluster2/tests/test_generated_eval_ladder.py -q`
  - 5 passed
- `.venv/bin/python -m pytest shared/tests/test_aggregation.py shared/tests/test_factorial_analysis.py -q`
  - 68 passed
- `.venv/bin/python -m pytest cluster2/tests -k "result or logger or jsonl or durable or append or overwrite or partial or repair_trace" -q`
  - 68 passed, 289 deselected
- `.venv/bin/python -m pytest cluster1/tests/test_results.py cluster1/tests/test_validate_cluster1_results.py -q`
  - 69 passed
- `git diff --check`
  - passed

Failed with an unrelated baseline/hash guard:

- `.venv/bin/python -m pytest cluster2/tests shared/tests -k "result or logger or jsonl or modal or repair or output" -q`
  - 396 passed, 1 failed, 479 deselected
  - Failure: `cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head[shared/modal_harness/smoke.py]`
  - The failing file `shared/modal_harness/smoke.py` has no worktree diff and was not modified by this fix.
  - The failure compares the current file hash `4c999a29a1e966635e186c16d211fe07a36ebd132e8ba47b150eaebab2691e30` to the phase-minus-1 git-head hash `03848df1d3196377a8bdaa363f5b7dd47f59cabcafd7f4011091ac933daa9e16`.
  - Resolving that would require a separate boundary/hash decision; this fix did not re-record hashes or modify frozen artifacts.

## 7. Remaining risks

Local unit-test risk: the targeted C2/C1 durability tests pass. The broader requested regression has one unrelated baseline hash failure in `shared/modal_harness/smoke.py`.

Modal filesystem risk: per-row flush and fsync are implemented, but final durability still depends on Modal volume/filesystem semantics honoring fsync as expected.

Partial artifact interpretation risk: partial JSONL is now intended to be a durable prefix. Consumers must distinguish strict full-run validation from diagnostic partial inspection.

Resume/deduplication risk: resume avoids duplicate appends for matching existing prefix rows and rejects stale extra rows on successful completion, but it does not skip generation/evaluation for already persisted rows. A true cost-saving resume scheduler remains separate work.

## 8. Next recommendation

**REAUDIT_C2_PRE_SMOKE** after resolving or explicitly accepting the unrelated `shared/modal_harness/smoke.py` boundary hash failure. Do not run C n=1 or C n=20 until that pre-smoke audit is clean.
