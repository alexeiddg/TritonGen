# Shared Modal Smoke Boundary Hash Resolution Report

## 1. Executive summary

Final classification: `A_INTENTIONAL_BEHAVIOR_CHANGE`.

Chosen resolution: accepted hash. The current `shared/modal_harness/smoke.py` content is retained, and the expected smoke.py boundary hash is re-recorded as a path-specific accepted override rather than by changing the global Phase -1 `git.current_head`.

The G+C n=20 run itself should not be started directly from this fix. The pre-run gate can be retried first.

## 2. Failure summary

Failing file: `shared/modal_harness/smoke.py`.

Failing test: `cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head`.

Expected Phase -1 hash: `03848df1d3196377a8bdaa363f5b7dd47f59cabcafd7f4011091ac933daa9e16`.

Actual current hash: `4c999a29a1e966635e186c16d211fe07a36ebd132e8ba47b150eaebab2691e30`.

The expected hash was not stored as a smoke.py literal before this fix. The sentinel derived it from `cluster2/contracts/phase_minus1_manifest.json` at `git.current_head`, then hashed the `shared/modal_harness/smoke.py` blob from that commit.

## 3. Git diff diagnosis

Required commands run:

```text
git status --short
git log --oneline -- shared/modal_harness/smoke.py
git diff HEAD~1..HEAD -- shared/modal_harness/smoke.py
rg "03848df1d3196377a8bdaa363f5b7dd47f59cabcafd7f4011091ac933daa9e16|4c999a29a1e966635e186c16d211fe07a36ebd132e8ba47b150eaebab2691e30|shared/modal_harness/smoke.py|test_shared_modal_files_match_phase_minus1_git_head" cluster2 shared .contracts tests
```

`git status --short` was clean before applying the resolution. `git diff HEAD~1..HEAD -- shared/modal_harness/smoke.py` was empty, so `HEAD~1` was not the relevant previous boundary. The relevant Phase -1 commit is `e197500a59669eb05e138f44218b2e9f5d9e91bc`, recorded in `cluster2/contracts/phase_minus1_manifest.json`.

The broad `rg` command returned matches but exited non-zero because this repository has no top-level `tests` directory. Re-running the same search over existing roots (`cluster2 shared .contracts`) located the boundary references.

Commits inspected:

```text
a468dcd Modal baseline re-parse
4ce3803 Contrained Grammar Surface
070f0d8 Modal: Remote Model Generation
ee1bfc6 Modal harness Phases 1-3: app, schemas, remote compile smoke
```

Only commit `a468dcd70e035599a39d52e7d9196dde54be76da` touched `shared/modal_harness/smoke.py` after the Phase -1 manifest commit.

Diff summary from `e197500a59669eb05e138f44218b2e9f5d9e91bc..HEAD`:

- The import-only smoke documentation changed from verifying `cluster1` and `shared` to verifying `cluster1`, `cluster2`, and `shared`.
- `import_smoke()` now imports `cluster2`.
- `import_smoke()` now returns `{"cluster1": True, "cluster2": True, "shared": True}`.

Behavior-impact assessment: behavior-affecting, but intentionally limited to the shared Modal import-only smoke. The change aligns with `shared/modal_harness/images.py`, where both Modal images now copy `cluster1`, `cluster2`, and `shared`. No prompt, grammar, generation, evaluation, replay, correctness, result-schema, or G+C n=20 methodology change is hidden in the smoke.py diff.

Classification: `A_INTENTIONAL_BEHAVIOR_CHANGE`.

## 4. Resolution applied

Files modified:

- `cluster2/contracts/phase_minus1_manifest.json`
- `cluster2/tests/test_cluster2_boundary.py`
- `audits/shared_modal_smoke_boundary_hash_resolution_report.md`

Hash update:

- Previous Phase -1 smoke.py hash retained in the manifest override as `previous_phase_minus1_sha256`.
- Accepted current smoke.py hash recorded as `expected_sha256`.
- No unrelated hashes were re-recorded.
- The global Phase -1 `git.current_head` was not changed.

The boundary test now checks `accepted_boundary_hash_overrides.shared_modal_files` for path-specific accepted drifts after preserving the existing special handling for intentionally instrumented `generation.py` and `schemas.py`.

Rationale: accepting the smoke.py hash is safer than changing the global Phase -1 commit because it limits the re-record to exactly one file and leaves all other Phase -1-derived blob checks anchored to the original boundary.

## 5. Validation results

```text
.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py -q
PASS: 25 passed, 1 skipped in 0.56s
```

```text
.venv/bin/python -m pytest cluster2/tests/test_cluster2_boundary.py::test_shared_modal_files_match_phase_minus1_git_head -q
PASS: 3 passed in 0.14s
```

```text
.venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py cluster2/tests/test_modal_schemas.py cluster2/tests/test_results_logger.py -q
PASS: 133 passed in 1.01s
```

```text
.venv/bin/python -m pytest shared/tests -k "modal_harness or smoke or boundary or content_hash" -q
PASS: 77 passed, 448 deselected in 1.51s
```

No Modal command was invoked. No GPU job, generation run, or G+C n=20 run was invoked.

## 6. Remaining risks

`shared/modal_harness/smoke.py` is a smoke-entrypoint file. The accepted diff changes only the `import-only` smoke behavior by requiring `cluster2` to be importable in the shared Modal image. It does not alter compile smoke source, generation smoke parameters, remote generation implementation, evaluation behavior, replay controls, grammar files, or generated artifacts.

No G+C n=20 methodology risk remains from this hash mismatch. The remaining operational risk is that the G+C n=20 pre-run gate may surface a different boundary or environment issue when retried.

## 7. Next recommendation

`RETRY_G_PLUS_C_N20_PRE_RUN_GATE`
