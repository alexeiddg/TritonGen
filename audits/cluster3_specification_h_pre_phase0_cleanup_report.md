# Cluster 3 Specification H Pre-Phase-0 Cleanup Report

## 1. Executive summary

Patched `docs/cluster3_implementation_specification.md` for the §H pre-Phase-0 cleanup. The cleanup resolves the remaining contract inconsistencies around inactive-P stop reasons, required P seed prompt hashes, C attempt counting, Cluster 2-compatible C feedback-builder typing, trace-summary validation staging, replay metadata wording, and Phase 0 dirty-tree preflight handling.

No implementation code, artifacts, analyzer outputs, grammar files, or hashes were modified.

## 2. Review findings addressed

- H1: inactive P rows now use `p_repair_stop_reason="p_not_applicable"` and row construction always populates the stop reason.
- H2: `PSeedAttempt.prompt_hash` is required for new Cluster 3 seeds and validates against stored prompt text or prompt construction metadata.
- H3: `c_attempt_count` counts generated C repair candidates only and excludes the seed F2 candidate.
- H4: C feedback builders use Cluster 2's `FeedbackCallable = Callable[[RepairFeedbackInput], str | None]`, with `None` selecting the Cluster 2 default.
- H5: Phase 1 trace-summary validation is self-contained; Phase 2 owns row-vs-trace consistency checks.
- H6: `Cluster3ReplayRowMetadata` now mirrors/extends `Cluster2ReplayRowMetadata` for no-P control rows, not generated metadata.
- H7: Phase 0 preflight now requires explicit dirty-tree classification and reporting.

## 3. Files updated

- `docs/cluster3_implementation_specification.md`
- `audits/cluster3_specification_h_pre_phase0_cleanup_report.md`

## 4. P stop-reason policy

The spec now makes `p_repair_stop_reason` a required string field. Inactive P rows, including direct initial-F2 C rows, require `p_repair_stop_reason="p_not_applicable"`. Phase 5 row construction now states that every row populates `p_repair_stop_reason`; P-fired rows use the status-to-stop-reason table.

Added/updated specified tests include `test_inactive_p_rows_use_p_not_applicable_stop_reason`, `test_direct_initial_f2_c_row_uses_p_not_applicable_stop_reason`, and `test_phase5_row_construction_always_populates_p_repair_stop_reason`.

## 5. PSeedAttempt prompt hash contract

`PSeedAttempt.prompt_hash` is now `str`, required, and must be a valid sha256. If prompt text is stored, it must equal `sha256(prompt)`. If prompt text is not stored, it must equal the prompt construction metadata hash. Phase 5 no longer says `prompt_hash if available`.

Added specified tests include `test_p_seed_attempt_requires_prompt_hash`, `test_p_seed_attempt_rejects_missing_prompt_hash`, and `test_p_seed_attempt_prompt_hash_matches_prompt_metadata_when_prompt_not_stored`.

## 6. C attempt count semantics

`c_attempt_count` now mirrors the intended P count convention: it counts only newly generated C repair candidates and excludes the seed F2 candidate. Budget-zero C runs have `c_attempt_count=0`; when C fires, the C trace path length is `c_attempt_count + 1`.

Added specified tests include `test_c_attempt_count_excludes_seed_candidate`, `test_c_attempt_count_zero_when_budget_zero`, `test_c_trace_path_length_is_attempt_count_plus_one_when_c_fires`, and `test_c_attempt_count_zero_when_c_does_not_fire`.

## 7. C feedback-builder type

The C helper signature now defines `FeedbackCallable = Callable[[RepairFeedbackInput], str | None]` from `cluster2.feedback.repair_loop` and accepts `feedback_builder: FeedbackCallable | None`. `None` selects Cluster 2's default public Level 2 feedback builder. Custom builders must not include P compile-error text or private eval shapes.

Added specified tests include `test_c_loop_accepts_cluster2_feedback_callable_signature`, `test_c_loop_allows_none_feedback_builder_for_default`, and `test_c_loop_rejects_feedback_builder_that_includes_p_compile_error_text`.

## 8. Trace-summary validation split

Phase 1 `Cluster3TraceSummary` validation is now limited to self-contained invariants: required fields, canonical condition/failure-code values, sha256-shaped hashes, booleans, private-data exclusion, and compact failure-path consistency. Phase 2 row schema retains terminal-provenance and final-success cross-checks against row fields and generated metadata.

Added specified tests include `test_cluster3_trace_summary_self_contained_invariants`, `test_cluster3_trace_summary_matches_row_terminal_provenance`, and `test_cluster3_trace_summary_matches_row_final_success_flags`.

## 9. Replay metadata wording/type

`Cluster3ReplayRowMetadata` now explicitly mirrors/extends `Cluster2ReplayRowMetadata` for no-P control artifact rows and is separate from Cluster 3 generated row metadata.

Added specified tests include `test_cluster3_replay_row_metadata_mirrors_cluster2_replay_metadata_contract` and `test_cluster3_replay_row_metadata_not_used_as_generated_row_metadata`.

## 10. Phase 0 dirty-tree policy

The preflight checklist now requires `git status --short`, dirty-path classification, and report fields `preflight_git_status` plus `known_dirty_paths` when dirty. Phase 0 must not silently build on unreviewed Cluster 2 code changes, artifact changes, or unknown tracked changes.

The starting tree had pre-existing tracked changes outside this task, including README, Cluster 2 source/tests/contracts, and validation files. They were not modified by this cleanup.

## 11. Validation commands and results

- `git status --short` before patch: showed pre-existing tracked changes in README and Cluster 2 files.
- Required §H `rg` searches: completed before editing; findings matched the review input and were patched.
- Required post-patch `sed` inspections: completed.
- Stale/inconsistent-term search: no stale positive claims returned.
- Required-new-term search: returned all required §H terms.
- `.venv/bin/python` validation/parsing check: completed using the repository venv.
- Final `git status --short` and `git diff --stat`: completed. They continue to show only the pre-existing tracked dirty paths because `.gitignore` ignores `docs/` and `audits/`; targeted `git check-ignore -v` confirmed `.gitignore:43:docs` and `.gitignore:44:audits` apply to the two files changed by this task.

## 12. Remaining risks

- Phase 0 implementation must explicitly acknowledge the current pre-existing dirty tree before beginning.
- This is a specification-only patch; the listed tests still need to be implemented in the appropriate phases.

## 13. Classification

SPEC_H_PRE_PHASE0_CLEANUP_COMPLETE
