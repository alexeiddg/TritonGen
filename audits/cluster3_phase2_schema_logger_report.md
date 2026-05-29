# Cluster 3 Phase 2 Schema Logger Report

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
- `cluster3/feedback/compile_error_repair.py`
- `cluster3/feedback/trace.py`
- `cluster3/feedback/prompts.py`
- `cluster3/feedback/sanitizer.py`
- `audits/cluster3_phase1_p_repair_loop_report.md`

## known_pre_existing_regression_status

Preflight baseline regression and final regression both failed only at:

`cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`

This is the known pre-existing Cluster 1 docs-lock failure. Phase 2 did not
modify Cluster 1, grammar files, docs-lock files, outputs, Cluster 2 source,
shared analyzer/eval code, Modal harness files, or analyzer outputs.

## files_changed

Added:

- `cluster3/results/dataclass.py`
- `cluster3/results/logger.py`
- `cluster3/tests/test_cluster3_schema.py`
- `cluster3/tests/test_cluster3_logger.py`
- `audits/cluster3_phase2_schema_logger_report.md`

Modified:

- `cluster3/results/__init__.py`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`

Not updated:

- `docs/handoff/stale_docs_inventory.md` — not updated; no citation/stale/supersession change.
- `docs/handoff/agentic_document_hub.md` — not updated; no read-set/navigation change.

## implementation_summary

Implemented Cluster 3 Phase 2 schema/logger scope only:

- `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`.
- `Cluster3ReplayRowMetadata`, `Cluster3GeneratedRowMetadata`,
  `Cluster3EvalRow`, `Cluster3ContentHashSidecar`, and optional diagnostics.
- Lightweight `cluster3.results` re-exports.
- `Cluster3JsonlAppendLogger`, canonical row serialization, default hash-sidecar
  path, sidecar loading, row/sidecar hash compatibility validation, and atomic
  sidecar writes.

No dispatcher, runner, Modal adapter, replay manifest builder, analyzer update,
F1 fixture smoke, boundary tests, methodology docs, generation, experiments, GPU
jobs, or Modal invocation were implemented.

Review-fix pass:

- Tightened terminal source provenance validation so impossible `p_attempt` and
  `c_attempt` terminal stages are rejected when their loops did not fire.
- Allowed valid post-P C seed terminals to retain P-attempt terminal provenance
  with seed prompt metadata or unavailable seed prompt hash provenance.
- Added generated grammar metadata variant/path/scope matrix validation matching
  the Cluster 2 generated metadata contract.

Second review-fix pass:

- Bound `p_attempt` terminal attempt provenance to the terminal P trace entry
  and `p_repair_attempt_count`.
- Bound `c_attempt` terminal attempt provenance to the terminal C repair trace
  entry.
- Made `generated_row(...)` terminal prompt provenance explicit instead of
  defaulting to an invalid initial-terminal prompt hash combination.

Third review-fix pass:

- Rejected `initial` terminal provenance after generated P attempts.
- Bound P terminal source hash and generation seed to the terminal P trace entry.
- Bound C terminal source hash to the terminal C repair trace entry.
- Validated replay metadata frozen Cluster 1 generation hashes against the
  content-hash sidecar using the row's recorded replay control condition.

Fourth review-fix pass:

- Bound active P terminal failure code and compile-repair success evidence to
  the terminal P trace entry.
- Rejected `p_attempt` terminal provenance when no generated P attempt exists.
- Bound generated C terminal failure code and available success flags to the
  terminal C repair trace entry.
- Restricted replay-control metadata and sidecar condition keys to Cluster 2
  replay controls (`none` and `G`).

Fifth review-fix pass:

- Allowed `p_compile_repair_succeeded` to be proven by the
  `p_post_compile_f3_observed` stop reason when compact P trace
  `compile_success` is false.
- Validated P trace attempt indexes from seed through
  `p_repair_attempt_count`, including P-then-C rows whose final terminal source
  is C.
- Rejected initial or post-P C seed terminal provenance when generated C repair
  trace entries are present, and cross-checked trace-summary C attempt count
  against the stored C repair trace.

Sixth review-fix pass:

- Cross-checked `trace_summary.terminal_source_stage` and
  `trace_summary.terminal_attempt_index` against the row terminal provenance.
- Validated generated C repair trace attempt indexes from 1 through the stored
  generated C attempt count.
- Mirrored Cluster 2 generated runtime metadata validation for stop reasons,
  rejection layers, grammar validation fields, stable Modal image identifiers,
  and Modal image provenance component digests.

Seventh review-fix pass:

- Bound compile-repaired P stop reasons to `p_compile_repair_succeeded=True`
  so rows cannot encode successful P compile repair in `p_repair_stop_reason`
  while recording a false success flag.

Eighth review-fix pass:

- Bound every active P stop reason to the compatible P terminal failure class
  and `p_compile_repair_succeeded` value.
- Rejected empty generated metadata replay pairing strings for
  `cluster1_artifact_id` and `replay_source`.

Ninth review-fix pass:

- Rejected C repair traces when `c_loop_fired=False` so inactive-C rows cannot
  carry generated C attempt provenance.

Tenth review-fix pass:

- Moved resume extra-existing-row validation into `Cluster3JsonlAppendLogger.close()`
  so both context-managed and manual `open()`/`append()`/`close()` lifecycles
  enforce the deterministic-prefix resume contract.

Eleventh review-fix pass:

- Bound the active P seed trace entry to the recorded initial F1 compile
  failure, compile-success false status, compile-error class, and raw error
  excerpt hash presence.
- Kept the resume-validation bypass private by restoring the public
  `Cluster3JsonlAppendLogger.close()` API to always enforce resume tail
  validation.

Twelfth review-fix pass:

- Bound active P row-level `initial_failure_code` to `p_initial_failure_code`
  so durable rows cannot contradict the P seed trace's initial F1 compile
  classification.

## schema_summary

`Cluster3EvalRow` enforces:

- Cluster 3-only conditions and condition-derived source class/generation mode.
- Canonical failure codes and row-final compile/functional consistency.
- Inactive P policy with recorded config constants and `p_not_applicable`.
- Active P budget, attempt-count, seed-plus-attempt trace length, stop reason,
  stop-reason/terminal-outcome matrix, P-terminal failure-code binding, P
  initial failure binding, P seed trace binding, attempt-index sequence
  binding, and neutral `p_repair_changed_terminal_class` semantics.
- Direct initial-F2 C rows with inactive P fields.
- P-terminal success surviving later C regression while row-level success flags
  reflect the final terminal outcome.
- C-loop source, condition, terminal-code, terminal-level, and repair-trace
  requirements, including inactive-C trace rejection and generated C
  repair-trace attempt-index sequencing.
- Row failure-code binding across initial, P-only, direct-C, and P-then-C paths.
- Terminal source provenance, prompt-hash provenance, generated metadata seed
  alignment, selected trace-entry hash/seed binding, and trace-summary row
  cross-checks.
- JSON round-trip for nested dataclasses and tuple traces.

## logger_summary

`Cluster3JsonlAppendLogger` mirrors Cluster 2 durable append behavior:

- `fsync=True` default.
- `mode in {"overwrite", "resume"}`.
- Deterministic-prefix resume validation.
- Resume rejection for divergent or extra existing rows across context-managed
  and manual-close lifecycles without a public bypass flag.
- Sorted-key canonical JSONL line serialization.
- Newline-terminated output.
- Atomic content-hash sidecar replacement with original sidecar preservation on
  write/replace failure.
- Replay metadata sidecar validation for rows carrying frozen Cluster 1 control
  provenance.

## tests_added

- `cluster3/tests/test_cluster3_schema.py` with 127 schema/provenance tests.
- `cluster3/tests/test_cluster3_logger.py` with 10 durable logger tests.

## tests_run

Preflight:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v`
  - Result: 15 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_p_sanitizer.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_p_prompts.py cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_trace.py -v`
  - Result: 76 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Post-implementation:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 87 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 178 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_imports.py -v`
  - Result: 15 passed.
- `.venv/bin/python -m pytest cluster3/tests/test_p_sanitizer.py cluster3/tests/test_condition_adapters.py cluster3/tests/test_p_prompts.py cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_trace.py -v`
  - Result: 76 passed.
- `.venv/bin/python -m compileall -q cluster3/results`
  - Result: passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Second review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 92 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 183 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Third review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 99 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 190 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Fourth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 106 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 197 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Fifth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 110 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 201 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Sixth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 116 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 207 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Seventh review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 119 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 210 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Eighth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: first run failed due outdated test expectations, then 127 passed after the narrow test/setup fix.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 218 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Ninth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 128 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 219 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Tenth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: 129 passed.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 220 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Eleventh review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: first run failed due one outdated direct-C test setup, then 135 passed after the narrow test/setup fix.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 226 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

Twelfth review-fix pass:

- `.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_logger.py -v`
  - Result: first run failed due one outdated direct-C test expectation, then 137 passed after the narrow test/setup fix.
- `.venv/bin/python -m pytest cluster3/tests -v`
  - Result: 228 passed.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  - Result: failed only at the known Cluster 1 docs-lock test; 130 passed, 7 skipped before the stop.

## regression_checks

- Known pre-existing Cluster 1 docs-lock failure remained unchanged before and
  after Phase 2.
- Phase 2 tests passed, including the twelfth review-fix pass at 137 passed.
- Full Cluster 3 test suite passed, including the twelfth review-fix pass at 228 passed.
- Full regression under `-x` reached the same pre-existing Cluster 1 docs-lock
  failure and stopped before Cluster 2/shared/Cluster 3 tests, with no new
  failure observed.

## negative_scope_verification

- Forbidden heavy import scan over `cluster3/results`,
  `cluster3/tests/test_cluster3_schema.py`, and
  `cluster3/tests/test_cluster3_logger.py` returned no matches for Torch,
  Triton, transformers, xgrammar, or Modal imports.
- Forbidden Modal/API surface scan over `cluster3` returned no matches.
- `git diff --name-only` showed only tracked `cluster3/results/__init__.py`;
  the other Phase 2 paths are new or ignored project-owned files listed above.
- Final `git status --short` showed only Phase 2 Cluster 3 result/test files
  and the lightweight `cluster3/results/__init__.py` tracked edit.

## docs_impact

- Updated handoff phase state to Phase 2 complete with warnings.
- Updated document version registry to version 1.6.12 and registered this report.
- `docs/handoff/stale_docs_inventory.md` not updated; no citation/stale/supersession change.
- `docs/handoff/agentic_document_hub.md` not updated; no read-set/navigation change.

## blockers

No Phase 2 blocker remains. The only warning is the unresolved known
pre-existing Cluster 1 docs-lock failure.

## classification

PHASE2_SCHEMA_LOGGER_COMPLETE_WITH_WARNINGS
