# Cluster 3 Phase 8 F1 Fixture Smoke Report

## Preflight Git Status

preflight_git_status:

```text
```

## Dirty Path Classification

dirty_path_classification:
- none; preflight tree was clean.

## Known Pre-Existing Regression Status

known_pre_existing_regression_status:
- `known_pre_existing_cluster1_docs_lock_failure`
- Pre-implementation baseline command `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x` failed only at `cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`.
- Final full `-x` regression still fails first at the same Cluster 1 docs-lock test.
- Phase 8 did not modify `cluster1/`, `cluster2/`, `shared/`, grammar files, docs-lock files, `outputs/`, analyzer outputs, Modal harness files, generation, experiments, or GPU/Modal paths.

## Files Changed

files_added:
- `cluster3/tests/fixtures/f1_compile_kernels/invalid_decorator.py`
- `cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py`
- `cluster3/tests/fixtures/f1_compile_kernels/wrong_launch_signature.py`
- `cluster3/tests/fixtures/f1_compile_kernels/type_error_in_pointer_arith.py`
- `cluster3/tests/test_p_repair_f1_fixtures.py`
- `audits/cluster3_phase8_f1_fixture_smoke_report.md`

files_modified:
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

## Tests Added

tests_added:
- `cluster3/tests/test_p_repair_f1_fixtures.py`
- Added 11 local smoke tests covering text-only fixture reads, F0 invalid-decorator termination without P, F1 compile seed construction, successful P repair to Level 2 success, persistent F1 budget exhaustion with `compile_unchanged_exhausted`, compile-error-only feedback boundaries, absence of Level 2 numerical/correctness details, 2000-character head truncation, full-error SHA256, LLVM/PTX allowance, and speedup/profiler rejection.

## Fixture Summary

fixture_summary:
- `invalid_decorator.py`: contains `@triton.jot`; classified in tests as F0 no-decorator/decorator failure; dispatcher terminates and P does not fire.
- `bad_constexpr.py`: contains undefined `MISSING_SCALE_FACTOR` in a Triton JIT body; used as the F1_COMPILE seed for successful and persistent compile-failure P-loop smoke tests.
- `wrong_launch_signature.py`: intentionally omits the `alpha` constexpr argument at launch; test documents the boundary that local classification may surface as F1_COMPILE or F0_BAD_SIGNATURE.
- `type_error_in_pointer_arith.py`: performs pointer arithmetic with fp32 offsets; used to build an F1_COMPILE seed with PTX assembly compile-error metadata.
- Fixtures are source strings only and are not imported as Python modules during test collection.

## P-Loop Smoke Summary

p_loop_smoke_summary:
- F0-style invalid decorator dispatches to `route="terminate"` and leaves `p_repair_attempted=False`.
- F1_COMPILE bad-constexpr seed invokes the real P loop with dependency-injected generation/evaluation; attempt 1 succeeds with `status="compile_repaired_then_success"`, `stop_reason="p_compile_repaired_then_success"`, `attempts_executed=2`, and terminal source equal to the corrected source.
- Persistent F1_COMPILE attempts run through `DEFAULT_P_REPAIR_BUDGET` and finish with `status="compile_unchanged_exhausted"`, `stop_reason="p_budget_exhausted"`, `attempts_executed == DEFAULT_P_REPAIR_BUDGET + 1`, and `final_failure_code="F1_COMPILE"`.
- The successful smoke result would set `p_compile_repair_succeeded=True` and `p_repair_changed_terminal_class=True` at row construction.

## Feedback Boundary Summary

feedback_boundary_summary:
- P feedback is built through the existing Phase 1 prompt helper.
- Feedback contains compile-error evidence only; it excludes `correctness`, `numerical`, `numeric`, `nan`, `inf`, `shape mismatch`, `hidden eval`, `private eval`, and `eval_shape_set`.
- LLVM/PTX compile-error text is allowed.
- Speedup/profiler language in fixture-context compile-error text is rejected by the Cluster 3 P sanitizer.
- `excerpt_compile_error(...)` keeps the first 2000 characters only and hashes the full raw compile error with SHA256.

## Tests Run

tests_run:
- `git status --short` - preflight clean.
- Phase 7a handoff checks with `test -f shared/analysis/factorial.py` and `test -f audits/cluster3_phase7a_analyzer_support_report.md` - all present.
- Phase 1 P-loop handoff checks with `test -f cluster3/feedback/compile_error_repair.py`, `prompts.py`, `sanitizer.py`, and `dispatcher.py` - all present.
- `.venv/bin/python -m pytest cluster3/tests -v` - passed, 674 tests before Phase 8 edits.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` - passed, 128 selected tests before Phase 8 edits.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x` - pre-edit failed only at the known Cluster 1 docs-lock test.
- `.venv/bin/python -m pytest cluster3/tests/test_p_repair_f1_fixtures.py -v` - first run found one bad test assertion; after fixing the synthetic truncation input, passed 11 tests.
- `.venv/bin/python -m pytest cluster3/tests -v` - passed, 685 tests after Phase 8 test addition.
- `.venv/bin/python -m compileall -q cluster3/tests/test_p_repair_f1_fixtures.py` - passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` - failed first at the known Cluster 1 docs-lock test.

## Regression Checks

regression_checks:
- Phase 8 tests pass.
- Cluster 3 tests pass.
- Analyzer/factorial sanity subset passes.
- Full regression remains unchanged at the known Cluster 1 docs-lock failure.
- No new regression appeared before the known failure.

## Docs Impact

docs_impact:
- Created this Phase 8 report.
- Updated `.contracts/agentic/preliminary_report_handoff/phase_state.md` line 1 and added a Phase 8 handoff block.
- Updated `docs/handoff/document_version_registry.md` to register the Phase 8 report and edited handoff docs.
- Updated `docs/handoff/stale_docs_inventory.md` because Cluster 3 stale-status assumptions changed: Phase 8 F1 fixture smoke is now implemented rather than pending.
- Updated `docs/handoff/agentic_document_hub.md` because the Cluster 3/P read set for Phase 9+ now includes this Phase 8 report.

## Negative Scope Verification

negative_scope_verification:
- No files under `cluster1/`, `cluster2/`, `shared/`, `outputs/`, grammar files, analyzer outputs, Modal harness files, Cluster 3 production source, `cluster3/results/`, `cluster3/modal/`, `cluster3/experiments/`, `cluster3/replay/`, or `cluster3/contracts/` were modified.
- `git diff -- outputs` returns no diff.
- Fixture import safety scan returned no matches for importing fixture modules.
- Heavy/runtime import scan found only fixture text-file imports for `torch`/`triton`; the Phase 8 test module has no runtime `torch`, `triton`, `transformers`, `xgrammar`, or `modal` imports.
- Forbidden Modal/API surface scan found no Phase 8 production matches.
- No Modal execution, GPU jobs, generation, experiments, or output artifact mutation were invoked.

## Blockers

blockers:
- No in-scope Phase 8 blockers.
- The known Cluster 1 docs-lock failure remains unresolved and outside Phase 8 scope.

## Classification

classification:
- `PHASE8_F1_FIXTURE_SMOKE_COMPLETE_WITH_WARNINGS`
- The warning is limited to the unchanged pre-existing Cluster 1 docs-lock failure.

## Next Step

next_step_recommendation:
- Proceed to Cluster 3 Phase 9 boundary tests, reading this Phase 8 report together with the implementation specification and prior Phase 0-7a reports.
