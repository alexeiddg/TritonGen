# C2 Generated Eval Level 0/1 Fix Report

## 1. Executive summary

Blocker fixed: the active generated C2 correctness payload path now evaluates fresh generated candidates through shared Level 0 parse/signature, shared Level 1 compile/runtime import, and only then shared Level 2 correctness.

Files modified:

- `cluster2/modal/correctness_runner.py`
- `cluster2/modal/schemas.py`
- `cluster2/tests/test_generated_eval_ladder.py`
- `cluster2/tests/test_modal_correctness_check.py`
- `cluster2/tests/test_cluster2_boundary.py`

Final classification: `FIX_VERIFIED`.

No Modal command, generation run, GPU job, C n=1, C n=20, G+C run, artifact rewrite, or hash rerecord was run.

## 2. Root cause

The active fresh generated path is `cluster2/experiments/run_cluster2_modal.py::_run_generated_cell()`. Its `evaluation_call()` sends each generated attempt to the C2 correctness adapter. The default adapter reaches `cluster2/modal/correctness_runner.py::run_correctness_payload()`.

Before this fix, `run_correctness_payload()` created a `_GeneratedSourceCandidateRunner` and called `shared.eval.pipeline.run_eval_pipeline(..., level2_request=...)` directly. That path reached shared Level 2 correctness without actively invoking `shared/eval/levels/level0_parse.py` or `shared/eval/levels/level1_compile.py` first.

That could misclassify syntax, signature, or compile/runtime import failures as Level 2/runtime failures because the first active execution happened inside the Level 2 candidate runner.

Phase 4 baseline agreement did not catch this because it verified frozen baseline replay agreement. It did not exercise the fresh C generation -> evaluation -> repair path.

## 3. Implementation summary

Changed `cluster2/modal/correctness_runner.py::run_correctness_payload()` to run generated conditions through this ordered ladder:

1. `check_parse()` and `check_signature()` from `shared.eval.levels.level0_parse`
2. `check_compile_level1()` from `shared.eval.levels.level1_compile`
3. `run_eval_pipeline(..., PipelineLevel2Request(...))`, which calls shared Level 2 correctness

Level 0 parse now runs before kernel-spec loading and before `_configure_correctness_runtime()`, so Cluster 1 metadata imports or Torch/CUDA runtime setup cannot preempt F0 parse attribution for syntactically invalid generated C candidates. Level 0 signature runs after parse passes and before runtime setup. Runtime setup runs only after all Level 0 checks pass and before Level 1/Level 2.

Level 0 and Level 1 failures now return a schema-compatible `RemoteCorrectnessResult` with `level_reached`, parse/signature/compile fields, canonical `failure_code`, no feedback, and zero Level 2 shape counts.

`RemoteCorrectnessResult` now explicitly supports pre-Level 2 fields and rejects pre-Level 2 results that claim Level 2 shape success or include feedback.

The repair-loop budget and prompt construction were not redesigned.

## 4. Level-by-level behavior

| Case | Behavior |
|---|---|
| Level 0 parse/signature failure | Returns `F0_PARSE`, `F0_BAD_SIGNATURE`, or `F0_NO_DECORATOR`; skips Level 1 and Level 2; records failure at attempt 0; no feedback. |
| Level 1 compile/runtime failure | Returns canonical `F1_COMPILE` or `F1_RUNTIME`; skips Level 2; records failure at attempt 0; no feedback. |
| Level 2 F2 failure | Runs only after Level 0 and Level 1 pass; records `F2_*`; existing repair loop may produce numerical/correctness feedback. |
| Level 2 pass | Runs all three levels in order; records success with `failure_code=None`; no repair feedback. |

## 5. Repair-loop guard

Confirmed:

- F0/F1 failures terminate immediately.
- F0/F1 failures do not generate feedback prompts.
- F0/F1 failures do not cause a repair attempt after attempt 0.
- F2 failures remain the only repair-triggering failures.
- Max repair budget is unchanged.

## 6. Tests added/updated

Added `cluster2/tests/test_generated_eval_ladder.py` with synthetic generated-C cases:

- F0 parse failure: Level 0 parse only, no kernel-spec load, no runtime setup, no Level 1, no Level 2, `F0_PARSE`, attempt 0 only.
- F0 bad signature: Level 0 parse, kernel-spec load, then signature; no runtime setup, no Level 1, no Level 2, `F0_BAD_SIGNATURE`, attempt 0 only.
- F1 compile failure: Level 0 passes, runtime setup runs, Level 1 fails, no Level 2, `F1_COMPILE`, attempt 0 only.
- F2 numerical failure: Level 0, Level 1, Level 2 run in order, `F2_NUMERIC_LARGE`, repair fires, feedback prompt contains Level 2 numerical details only.
- Level 2 pass: all levels run in order, success recorded, no repair feedback.

Updated modal correctness tests to provide a Level 0-compatible local source fixture and mock Level 1 in CPU-only tests. Updated one boundary expectation to acknowledge the existing post-Phase-1 `failure_code` field before generation metadata.

## 7. Validation results

Passed:

```text
.venv/bin/python -m pytest cluster2/tests/test_generated_eval_ladder.py -q
5 passed
```

Passed:

```text
.venv/bin/python -m pytest cluster2/tests/test_modal_correctness_check.py cluster2/tests/test_modal_schemas.py -q
65 passed
```

Passed:

```text
.venv/bin/python -m pytest cluster2/tests -k "repair or feedback or level0 or level1 or level2 or generated or correctness or failure_code" -q
179 passed, 170 deselected
```

Passed:

```text
.venv/bin/python -m pytest shared/tests/test_eval_level0_parse.py shared/tests/test_eval_level1_compile.py shared/tests/test_eval_level2_correctness.py shared/tests/test_eval_failure_taxonomy.py -q
60 passed
```

Passed:

```text
.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_results_logger.py cluster2/tests/test_replay_controls.py -q
86 passed
```

Passed after updating the boundary expectation noted above:

```text
.venv/bin/python -m pytest cluster2/tests shared/tests -k "eval or failure_code or repair or feedback or metadata or result" -q
466 passed, 399 deselected
```

`git diff --check` passed.

## 8. Remaining risks

Local-only risk: tests use mocks/fakes for Level 0/1/2 ordering and do not prove CUDA compile behavior locally.

Modal-smoke risk: the fixed ordered ladder has not been exercised in Modal in this task because Modal, GPU jobs, and generation were forbidden.

Paper-scale risk: no paper-scale generated run was executed; content hashes will change because source files changed, so the next pre-smoke audit should confirm expected hash sidecars before any paper-scale run.

## 9. Next recommendation

`REAUDIT_C2_PRE_SMOKE`
