# Cluster 3 Phase 9 Boundary Tests Report

## Preflight Git Status

preflight_git_status:

```text
```

## Dirty Path Classification

dirty_path_classification:
- none; preflight tree was clean.

review_fix_preflight_git_status:

```text
?? cluster3/tests/test_cluster3_boundary.py
```

review_fix_dirty_path_classification:
- `cluster3/tests/test_cluster3_boundary.py`: `review_fix_target` and `expected_prior_phase9_change`.

## Known Pre-Existing Regression Status

known_pre_existing_regression_status:
- `known_pre_existing_cluster1_docs_lock_failure`
- Pre-implementation baseline command `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x` failed only at `cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`.
- Post-Phase-9 `-x` regression command `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` still failed first at the same Cluster 1 docs-lock test before reaching Cluster 3.
- Phase 9 did not modify `cluster1/`, `cluster2/`, `shared/`, grammar files, docs-lock files, `outputs/`, analyzer outputs, Modal harness files, generation paths, or experiment paths.

## Files Changed

files_added:
- `cluster3/tests/test_cluster3_boundary.py`
- `audits/cluster3_phase9_boundary_tests_report.md`

files_modified:
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md` during the initial Phase 9 report update; not updated in the review-fix pass because the read set/navigation did not change.

## Tests Added

tests_added:
- `cluster3/tests/test_cluster3_boundary.py`
- Added 17 test cases covering dispatcher termination/C-loop boundaries for all canonical F0/F1_RUNTIME/F2/F3 families, P feedback exclusion of Level 2 numerical/correctness/eval-set/private details, Cluster 3 sanitizer performance/profiler term rejection, no patch-suggestion diagnostic phrasing, LLVM/PTX positive allowance, Cluster 3 sanitizer isolation from the Cluster 2 validator, private payload redaction, full-error SHA256 behavior, unknown failure-code rejection, and failure-code/level mismatch rejection.

## Implementation Summary

implementation_summary:
- Phase 9 added boundary tests only.
- No implementation files were modified.
- No Modal, GPU, generation, real Triton compile, experiment, output artifact mutation, hash re-recording, or analyzer-output mutation was run.
- The required boundary tests exposed an existing sanitizer boundary failure; per Phase 9 scope, behavior was not patched.
- Review-fix pass addressed the injected review issue by splitting the performance-language boundary into per-term cases and restoring the `latency` subcase as an enforcing assertion.
- Cluster 3 validation is red on the `latency` sanitizer boundary because production sanitizer behavior was not authorized for modification in this boundary-test-only phase.

## Dispatcher Boundary Summary

dispatcher_boundary_summary:
- All new dispatcher boundary assertions passed.
- P did not fire for any canonical `F0_*` code.
- `F1_RUNTIME` terminated with `reason="unrecoverable_runtime"`.
- Canonical `F2_*` codes never routed to P; they terminated with `reason="f2_terminal_no_c"` for `P`/`G+P` and routed to C with `c_loop_source="initial_f2"` for `C+P`/`G+C+P`.
- Canonical `F3_*` codes terminated and did not route to P or C.
- Unknown failure codes and incompatible `failure_code`/`level_reached` pairs were rejected.

## Feedback Boundary Summary

feedback_boundary_summary:
- F1_COMPILE fixture-backed P feedback excluded `numeric`, `numerical`, `correctness`, `mismatch`, `allclose`, `nan`, `inf`, `shape`, `shape mismatch`, eval-set/private payload terms, and private eval-set detail reprs.
- Compile diagnostic notes passed the narrow early-warning patch-suggestion regex for `use`, `try`, `replace`, `should be`, `add a`, `change`, and `fix by`.
- LLVM/PTX compile-error text remained allowed in P feedback.
- Full-error SHA256 still hashes the full raw compile error, not the displayed excerpt.

## Sanitizer Boundary Summary

sanitizer_boundary_summary:
- `cluster3.feedback.sanitizer.validate_no_forbidden_p_terms` rejected or caused redaction for all required performance/profiling terms except `latency`.
- The review-fix test enforces the `latency` subcase; it fails because `latency` remains accepted by `validate_no_forbidden_p_terms` and unchanged by `sanitize_p_feedback_text`.
- The boundary test did not call the Cluster 2 feedback validator; the isolation test monkeypatched the Cluster 2 validator to raise and confirmed Cluster 3 prompt construction still succeeds.

## Boundary Failures

boundary_failures:
- `cluster3/tests/test_cluster3_boundary.py::test_p_feedback_excludes_speedup_profiler_language[latency]`
- Failure before the injected review fix: `leaked_terms == ["latency"]`.
- Injected review issue: the intermediate review-fix made this subcase an expected xfail, which allowed Cluster 3 validation to pass while the boundary remained unenforced.
- Current review-fix handling: the xfail was removed, so the boundary detector is enforced and Cluster 3 validation fails on the real sanitizer boundary.
- Classification: required Phase 9 sanitizer boundary failure. The current Cluster 3 sanitizer does not reject or remove `latency`, which Phase 9 specifies as forbidden performance/profiling language.
- No implementation patch was applied in this phase.

## Tests Run

tests_run:
- `git status --short` - preflight clean.
- `test -f cluster3/tests/test_p_repair_f1_fixtures.py` - passed.
- `test -d cluster3/tests/fixtures/f1_compile_kernels` - passed.
- `test -f audits/cluster3_phase8_f1_fixture_smoke_report.md` - passed.
- `.venv/bin/python -m pytest cluster3/tests -v` - pre-edit passed, 685 tests.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` - passed, 128 selected tests.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x` - pre-edit failed only at the known Cluster 1 docs-lock test.
- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_boundary.py -v` - initial Phase 9 run failed with 1 failure and 16 passes; failure was the `latency` sanitizer boundary.
- `.venv/bin/python -m compileall -q cluster3/tests/test_cluster3_boundary.py` - passed.
- `.venv/bin/python -m pytest cluster3/tests -v` - initial Phase 9 run failed with 1 failure and 701 passes; failure was the same `latency` sanitizer boundary.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` - failed first at the known Cluster 1 docs-lock test before reaching Cluster 3.
- Intermediate review-fix run before injected review: `.venv/bin/python -m pytest cluster3/tests/test_cluster3_boundary.py -v` - passed with 25 passed and 1 xfailed.
- Intermediate review-fix run before injected review: `.venv/bin/python -m pytest cluster3/tests -v` - passed with 710 passed and 1 xfailed.
- Current injected-review-fix run: `.venv/bin/python -m pytest cluster3/tests/test_cluster3_boundary.py -v` - failed with 1 failure and 25 passes; failure was `test_p_feedback_excludes_speedup_profiler_language[latency]`.
- Current injected-review-fix run: `.venv/bin/python -m pytest cluster3/tests -v` - failed with 1 failure and 710 passes; failure was the same `latency` sanitizer boundary.

## Regression Checks

regression_checks:
- Phase 9 boundary tests now fail on the enforced sanitizer latency boundary.
- Cluster 3 suite now fails only on the same enforced sanitizer latency boundary.
- Analyzer/factorial sanity subset passed before Phase 9 edits.
- Full `-x` regression remains unchanged at the known Cluster 1 docs-lock failure before reaching Cluster 3.
- No new non-boundary regression was observed before the known Cluster 1 failure.

## Docs Impact

docs_impact:
- Created this Phase 9 report.
- Updated `.contracts/agentic/preliminary_report_handoff/phase_state.md` line 1 and added a Phase 9 blocked handoff block.
- Updated `docs/handoff/document_version_registry.md` to register this report and edited handoff docs.
- Updated `docs/handoff/stale_docs_inventory.md` because Cluster 3 freshness/status changed from Phase 0-8 complete with boundary tests pending to Phase 9 boundary tests added but blocked on the sanitizer latency boundary.
- Updated `docs/handoff/agentic_document_hub.md` because future Cluster 3/P agents must read this Phase 9 boundary-failure report before retrying Phase 9 or proceeding to Phase 10.
- Review-fix pass updated this report, phase state, document version registry, and stale docs inventory. `docs/handoff/agentic_document_hub.md` was not changed in the current injected-review-fix pass because the read-set/navigation remained correct.

## Negative Scope Verification

negative_scope_verification:
- No implementation files were modified.
- No files under `cluster1/`, `cluster2/`, `shared/`, `outputs/`, grammar files, analyzer outputs, Modal harness files, `cluster3/feedback/`, `cluster3/results/`, `cluster3/modal/`, `cluster3/experiments/`, `cluster3/replay/`, or `cluster3/contracts/` were modified.
- `git diff -- outputs` returned no diff.
- Changed/added paths are limited to the Phase 9 test, this report, and justified handoff docs.
- Boundary content scan matches were reviewed manually: Phase 9 test assertions are expected; existing Cluster 3 production matches are sanitizer/private-detail constants, C-loop guards, trace guards, or failure classification logic rather than new P prompt emissions.
- Cluster 2 feedback validator usage scan over the Phase 9 test and `cluster3/feedback` returned no matches.
- Forbidden Modal/API surface scan returned only pre-existing test assertions checking `.spawn`, `.spawn_map`, and `.map` are absent.

## Blockers

blockers:
- `PHASE9_REVIEW_FIX_BOUNDARY_FAILURE`: Cluster 3 sanitizer accepts `latency` in P feedback text. The injected review issue is addressed by restoring the `latency` assertion as an enforcing boundary test; the resulting red Cluster 3 validation is the unresolved production boundary failure.
- The known Cluster 1 docs-lock failure remains unresolved and outside Phase 9 scope.

## Classification

classification:
- `PHASE9_REVIEW_FIX_BOUNDARY_FAILURE`

## Next Step

next_step_recommendation:
- Authorize a focused follow-up fix to Cluster 3 sanitizer behavior for the `latency` performance-language boundary, then rerun Phase 9 boundary tests and the required regression gates.
