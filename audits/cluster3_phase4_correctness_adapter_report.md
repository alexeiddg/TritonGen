# Cluster 3 Phase 4 Correctness Adapter Report

## preflight_git_status

`git status --short` produced no output.

```text
```

## dirty_path_classification

No preflight dirty paths were present.

| Path | Classification |
|---|---|
| none | no_dirty_paths |

## prior_phase_artifacts

Confirmed present:

- `cluster3/constants.py`
- `cluster3/feedback/condition_adapters.py`
- `cluster3/feedback/dispatcher.py`
- `cluster3/feedback/compile_error_repair.py`
- `cluster3/results/dataclass.py`
- `cluster3/results/logger.py`
- `audits/cluster3_phase3_dispatcher_report.md`

## known_pre_existing_regression_status

Preflight baseline regression and post-Phase-4 combined regression both failed
only at:

`cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`

This is the known pre-existing Cluster 1 docs-lock failure. Phase 4 did not
modify Cluster 1, grammar files, docs-lock files, outputs, Cluster 2 source,
shared analyzer/eval code, Modal harness files, or analyzer outputs.

## files_changed

Added:

- `cluster3/modal/__init__.py`
- `cluster3/modal/correctness_runner.py`
- `cluster3/modal/result_extraction.py`
- `cluster3/tests/test_correctness_runner_adapter.py`
- `audits/cluster3_phase4_correctness_adapter_report.md`

Modified:

- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

## implementation_summary

Implemented Cluster 3 Phase 4 local correctness-adapter scope:

- Added `Cluster3CorrectnessRequest` as a local wrapper over Cluster 3 identity
  plus source.
- Added `run_cluster3_correctness(...)`, which builds a translated Cluster 2
  `RemoteCorrectnessRequest`, supports injected `modal_call` stubs for tests,
  and lazily calls the existing Cluster 2 correctness function only on the
  default path.
- Added `validate_cluster3_remote_correctness_payload(...)`, which validates a
  Cluster 3-restamped payload through the existing Cluster 2 validator by using
  a temporary translated copy.
- Added Cluster 3-owned correctness result extraction and public F3 synthesis
  for infrastructure, malformed, and unrecognized payloads.

No new Modal app/function/image, runner, replay manifest, analyzer update, F1
fixture smoke, boundary test suite, methodology doc, generation path,
experiment runner, GPU job, Modal invocation, or output artifact was added.

## adapter_translation_summary

The adapter validates the outer condition as one of `P`, `G+P`, `C+P`, or
`G+C+P`, then translates only for the inner Cluster 2 correctness request:

| Cluster 3 condition | Inner Cluster 2 eval condition |
|---|---|
| `P` | `C` |
| `C+P` | `C` |
| `G+P` | `G+C` |
| `G+C+P` | `G+C` |

The adapter never translates to replay controls `none` or `G`.

## payload_restamp_summary

Returned payloads are restamped in-place back to Cluster 3:

- top-level `surface` becomes `c3_remote_correctness`;
- top-level `condition` is Cluster 3 when present;
- `identity.condition`, `source_identity.condition`, and
  `eval_identity.condition` are Cluster 3 when those sidecars exist;
- nested `correctness_result.identity.condition` is Cluster 3 when a nested
  correctness result exists.

Infrastructure payloads without `correctness_result` are preserved and do not
trigger nested identity checks. Normal success/failure payloads self-check that
wrapper and nested result identity conditions agree after restamping.

## result_extraction_summary

`extract_or_synthesize_cluster3_correctness_result_dict(...)` accepts normal
success/failure payloads with `correctness_result` and validates Cluster 3
identity stamps. Payloads without a usable nested result synthesize a canonical
public `F3_EVAL_PIPELINE` dict with:

- `level_reached=0`
- `compile_success=False`
- `functional_success=False`
- `repair_set_success=False`
- `eval_set_success=False`
- no raw private eval payload dump
- a sanitized `f3_reason` / `correctness_error` summary

F1 compile payloads preserve compile error type and compile error excerpt
information for later P-loop consumption.

C2 Level 0 parse/signature payloads that report `compile_success=None` are
normalized to `compile_success=False` when the failure code is F0/F1-shaped, so
the Cluster 3 extractor returns a canonical boolean result.

## modal_boundary_verification

- `cluster3/modal/__init__.py` does not import Modal or Cluster 2 Modal runtime
  modules.
- `cluster3/modal/correctness_runner.py` imports Cluster 2 schema/constants at
  module load, but imports the existing Cluster 2 correctness function lazily
  only when `modal_call` is not injected.
- Tests inject `modal_call` stubs and do not invoke Modal, GPU work, generation,
  or remote functions.
- Forbidden heavy import scan returned no matches.
- Modal import boundary scan returned no matches.
- Forbidden Modal/API surface scan returned no matches.
- Forbidden source packaging scan returned no matches.

## tests_added

- `cluster3/tests/test_correctness_runner_adapter.py`

Coverage includes condition validation/translation, replay-control regression
guards, payload restamping, infrastructure payload handling, Modal boundary
guards, lazy default import behavior, result extraction/F3 synthesis, and
`compile_success=None` normalization for F0 payloads.

## tests_run

Preflight:

- `git status --short`
  - Result: passed; no output.
- Prior artifact existence checks for required Phase 0-3 files.
  - Result: passed.
- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v`
  - Result: 15 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_p_sanitizer.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_p_prompts.py cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_trace.py -v`
  - Result: 76 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 137 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_dispatcher.py -v`
  - Result: 318 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7
    skipped before the stop.

Post-implementation:

- `.venv/bin/python -m pytest cluster3/tests/test_correctness_runner_adapter.py -v`
  - Result: 21 passed after review-fix coverage for F0
    `compile_success=None` normalization.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 567 passed.
- `.venv/bin/python -m compileall -q cluster3/modal`
  - Result: passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7
    skipped before the stop.

## regression_checks

- Full local Cluster 3 suite passed.
- Combined regression still stops at the same pre-existing Cluster 1
  documentation-language-lock failure before reaching Cluster 2, shared, or
  Cluster 3 tests.
- No new baseline failure appeared before the known failure.
- The known failure remains unresolved and unrelated to Phase 4.
- Forbidden heavy import, Modal import, Modal/API surface, and source-packaging
  scans returned no matches for Phase 4 surfaces.

## docs_impact

- Updated `.contracts/agentic/preliminary_report_handoff/phase_state.md` line 1
  with Phase 4 status, classification, report path, and unresolved known
  Cluster 1 docs-lock failure status.
- Updated `docs/handoff/document_version_registry.md` to register this Phase 4
  report and bump edited handoff docs.
- Updated `docs/handoff/stale_docs_inventory.md`; Phase 0-4 implementation
  changes Cluster 3 component-doc freshness assumptions.
- Updated `docs/handoff/agentic_document_hub.md`; Phase 5+ navigation now
  includes the Phase 4 correctness adapter report.

## blockers

- No Phase 4 dirty-tree blocker.
- No Phase 4 or Cluster 3 test blocker.
- The only regression-check warning is the known pre-existing Cluster 1
  docs-lock failure.

## review_fix_pass

Addressed the injected Phase 4 code-review issue:

- `extract_or_synthesize_cluster3_correctness_result_dict(...)` no longer
  preserves `compile_success=None` for normal C2 Level 0/F0 payloads; it derives
  the canonical boolean with `_compile_success_from_result(...)`.
- Added
  `test_extract_cluster3_f0_payload_with_compile_success_none_derives_false`.

Review-fix validation:

- `git status --short`
  - Result: existing Phase 4 untracked `cluster3/modal/` and
    `cluster3/tests/test_correctness_runner_adapter.py` only.
- `.venv/bin/python -m pytest cluster3/tests/test_correctness_runner_adapter.py -v`
  - Result: 21 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 567 passed.
- `.venv/bin/python -m compileall -q cluster3/modal`
  - Result: passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7
    skipped before the stop.
- Forbidden heavy import, Modal import, Modal/API surface, and source-packaging
  scans returned no matches.

## negative_scope_verification

negative_scope_verified: true

- No files under `cluster1/` were modified.
- No files under `cluster2/` were modified.
- No files under `shared/` were modified.
- No files under `outputs/` were modified.
- No grammar files were modified.
- No analyzer outputs were modified.
- No Modal harness files were modified.
- No files under `cluster3/results/`, `cluster3/feedback/`,
  `cluster3/experiments/`, `cluster3/replay/`, or `cluster3/contracts/` were
  modified.
- The only Cluster 3 production files added were under `cluster3/modal/`.

## classification

classification: PHASE4_CORRECTNESS_ADAPTER_COMPLETE_WITH_WARNINGS

## next_step_recommendation

- Proceed to Cluster 3 Phase 5 only with the known Cluster 1 docs-lock failure
  explicitly acknowledged as pre-existing and unrelated, or resolve that
  docs-lock failure in a separately scoped documentation-language-lock fix.
