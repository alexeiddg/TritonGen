# G+C Hash Gate And Metadata Fix Report

## 1. Executive Summary

Both targeted G+C readiness blockers were fixed.

Final classification: `FIX_VERIFIED`.

Files modified:

- `cluster2/contracts/phase_minus1_manifest.json`
- `cluster2/modal/generation.py`
- `cluster2/modal/schemas.py`
- `cluster2/results/dataclass.py`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/tests/test_modal_generation_c2.py`
- `cluster2/tests/test_modal_schemas.py`
- `cluster2/tests/test_replay_controls.py`
- `cluster2/tests/test_results_logger.py`
- `cluster2/tests/test_run_cluster2_modal.py`
- `audits/g_plus_c_hash_gate_and_metadata_fix_report.md`

No Modal, GPU, generation, G+C smoke, C n=20, paper-scale runs, source artifact rewrites, grammar edits, or Cluster 1 output rewrites were performed.

## 2. Root Cause

The active G+C hash gate had diverged from replay scheduling. Replay scheduling selected the registered task-agnostic n=20 artifact through `task_agnostic_g_status.available_task_agnostic_g_n20_replay_artifact_id`, but `cluster2/modal/generation.py` still mapped `task_agnostic` to the stale development artifact `g_task_agnostic_n5_l4_rerun`. The Phase -1 manifest hash also still recorded the older frozen manifest digest, so the gate failed before it could validate the current registered n=20 artifact.

Final C2 rows dropped `grammar_active` and `compile_success` because `Cluster2EvalRow` did not carry either field at the canonical row level. The runner had access to grammar routing and terminal correctness results, and nested metadata preserved some grammar details, but row construction and JSONL serialization had no top-level fields to persist.

## 3. Hash Gate Fix

Old active task-agnostic artifact key/path:

- Key: `g_task_agnostic_n5_l4_rerun`
- Path: `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl`

New active task-agnostic artifact key/path:

- Key: `g_task_agnostic_aligned_pipeline_n20_l4`
- Path: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`

`cluster2/modal/generation.py` now maps the active `task_agnostic` G+C hash gate to `g_task_agnostic_aligned_pipeline_n20_l4`. `cluster2/contracts/phase_minus1_manifest.json` now records the current frozen manifest SHA256 `fdb46b817d9b2d9b6c1663b4b31585d2b815e78be7562f575cd801cf9f7c781a`.

The stale n=5 artifact remains only as a legacy artifact entry in `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`; it is no longer selected by the active G+C hash gate or the task-agnostic replay selection path.

The 177/180 status remains explicit: policy `COVERAGE_WARNING_SKIP_MISSING`, observed rows `177`, intended rows `180`, with three missing matmul rows.

## 4. Metadata Persistence Fix

Row construction path:

- Generated rows: `cluster2/experiments/run_cluster2_modal.py` -> `generated_row(...)` -> `Cluster2EvalRow`
- Replay rows: `cluster2/experiments/run_cluster2_modal.py` -> `replay_control_row(...)` -> `Cluster2EvalRow`

Schema and serialization changes:

- `Cluster2EvalRow` now has top-level `grammar_active: bool` and `compile_success: bool`.
- `RemoteC2GenerationResult` now preserves `grammar_active` and validates `C=False`, `G+C=True`.
- JSONL serialization uses `row.to_json()`, so both fields are now emitted in final rows.
- Legacy row loading derives missing fields with `RuntimeWarning`; new dataclass rows must carry the fields.

Behavior:

- C generated rows persist `grammar_active=False`.
- G+C generated rows persist `grammar_active=True`.
- Generated `compile_success` is derived from terminal correctness: explicit `compile_success` when present, success/F2 implies true, F0/F1 implies false.
- Replay rows preserve source `grammar_active` when available and use terminal correctness compile state with frozen compile metadata as fallback.

## 5. Tests Added Or Updated

Added/updated coverage for:

- Current n=20 artifact in the active G+C hash gate.
- Stale n=5 artifact not active for G+C.
- Phase -1/frozen manifest hash gate passing.
- Explicit 177/180 `COVERAGE_WARNING_SKIP_MISSING` coverage warning.
- C row `grammar_active=False` persistence.
- G+C row `grammar_active=True` persistence.
- `compile_success=True` for terminal success/F2-reached generated rows.
- `compile_success=False` for Level 1 failure rows.
- JSONL logger output including both fields.
- Row schema roundtrip preserving both fields.
- Replay row conversion preserving source `grammar_active`.
- Legacy rows missing these fields warning during load.

## 6. Validation Results

Passed:

```bash
.venv/bin/python -m pytest cluster2/tests/test_modal_generation_c2.py cluster2/tests/test_replay_controls.py cluster2/tests/test_run_cluster2_modal.py -q
```

Result: `113 passed in 1.16s`

```bash
.venv/bin/python -m pytest cluster2/tests/test_results_logger.py cluster2/tests/test_modal_schemas.py -q
```

Result: `88 passed in 0.26s`

```bash
.venv/bin/python -m pytest cluster2/tests -k "grammar_active or compile_success or metadata or result or jsonl or logger or manifest or hash or replay" -q
```

Result: `170 passed, 1 skipped, 220 deselected in 82.76s`

```bash
.venv/bin/python -m pytest shared/tests -k "failure_code or metadata or adapter or result" -q
```

Result: `87 passed, 438 deselected in 0.82s`

```bash
.venv/bin/python -m pytest cluster2/tests shared/tests -k "replay or result or logger or metadata or generation or repair or failure_code" -q
```

Result: `463 passed, 453 deselected in 69.44s`

Additional local check:

```bash
.venv/bin/python -m py_compile cluster2/modal/generation.py cluster2/modal/schemas.py cluster2/results/dataclass.py cluster2/experiments/run_cluster2_modal.py
```

Result: passed.

## 7. Remaining Warnings

- Registered task-agnostic G replay artifact is still partial: `177/180`.
- Missing rows remain the same three matmul rows:
  - `matmul/fp32/sample_index=5`
  - `matmul/bf16/sample_index=0`
  - `matmul/bf16/sample_index=18`
- Smoke command docs/config lag around `--scale-tier` was not changed in this targeted fix.

## 8. Next Recommendation

`RERUN_G_PLUS_C_READINESS_AUDIT`
