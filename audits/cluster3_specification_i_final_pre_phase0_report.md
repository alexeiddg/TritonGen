# Cluster 3 Specification Section I Final Pre-Phase-0 Report

## 1. Executive summary

This Section I cleanup patches the Cluster 3 implementation specification for the last pre-Phase-0 ambiguities identified after the Section H review. The patch is documentation-only.

The specification now requires every P-loop terminal status to produce a concrete `PRepairLoopResult.stop_reason`, defines a machine-checkable Phase 0 scaffolding report artifact at `audits/cluster3_phase0_scaffolding_report.md`, and removes the dependency on Cluster 2 exposing C repair prompt hashes by requiring the Cluster 3 C-loop wrapper to hash captured `RepairGenerationInput.prompt` for generated C attempts.

## 2. Review findings addressed

- Completed P-loop stop-reason mapping for successful, compile-repaired, post-P F3, exhausted, unrecoverable, and inactive/no-P terminal states.
- Bound Phase 5 row construction to copy `PRepairLoopResult.stop_reason` when P fired and to use `p_not_applicable` when P did not fire.
- Defined the concrete Phase 0 report path, markdown headings, machine-checkable field labels, and allowed classifications.
- Clarified that Phase 0 report tests are pytest checks over `audits/cluster3_phase0_scaffolding_report.md`.
- Replaced stale C prompt-hash wording with Cluster 3-owned prompt capture and hashing rules.
- Added `terminal_prompt_hash_source` semantics for initial, P, generated C, seed metadata, and unavailable seed prompt cases.

## 3. Files updated

- `docs/cluster3_implementation_specification.md`
- `audits/cluster3_specification_i_final_pre_phase0_report.md`

No source code, artifact, analyzer output, grammar, hash, or unrelated documentation file was modified by this patch.

## 4. P-loop stop_reason mapping

The P-loop section now defines an explicit `P_REPAIR_STATUS_TO_STOP_REASON` table. Required mappings are:

- `compile_repaired_then_success` -> `p_compile_repaired_then_success`
- `compile_repaired_f2_observed` -> `p_compile_repaired_f2_observed`
- `post_p_f3_observed` with compile evidence -> `p_post_compile_f3_observed`
- `post_p_f3_observed` without compile evidence -> `p_f3_without_compile_evidence`
- `compile_unchanged_exhausted` as the v1 budget-exhausted status -> `p_budget_exhausted`
- `terminated_unrecoverable` as the v1 terminal-non-repairable status -> `p_terminal_non_repairable`
- inactive/no-P rows -> `p_not_applicable`

`PRepairLoopResult.stop_reason` must be populated before return. Unknown P-loop status, unknown stop reason, or missing compile evidence for an evidence-dependent stop reason is a validation error before row construction.

## 5. Phase 0 report artifact/schema

Phase 0 now has a concrete required report artifact:

- `audits/cluster3_phase0_scaffolding_report.md`

The report must include these headings:

- `# Cluster 3 Phase 0 Scaffolding Report`
- `## Preflight Git Status`
- `## Known Dirty Paths`
- `## Files Added`
- `## Files Modified`
- `## Tests Added`
- `## Tests Run`
- `## Regression Checks`
- `## Negative Scope Verification`
- `## Classification`

The report must include these machine-checkable labels:

- `preflight_git_status:`
- `known_dirty_paths:`
- `unexpected_dirty_paths:`
- `files_added:`
- `files_modified:`
- `tests_added:`
- `tests_run:`
- `regression_checks:`
- `negative_scope_verified:`
- `classification:`

Allowed Phase 0 classifications are:

- `PHASE0_SCAFFOLDING_COMPLETE`
- `PHASE0_SCAFFOLDING_COMPLETE_WITH_WARNINGS`
- `PHASE0_BLOCKED_DIRTY_TREE`
- `PHASE0_BLOCKED_TEST_FAILURE`
- `PHASE0_SURFACE_REGRESSION`

The specification now adds tests for report existence, required headings, required fields, and allowed classification values.

## 6. terminal_prompt_hash provenance

The terminal prompt hash contract now distinguishes five sources:

- `initial_prompt`: terminal source came from the initial generation prompt.
- `p_repair_prompt`: terminal source came from a P repair prompt.
- `c_repair_prompt`: terminal source came from a generated C repair attempt, and Cluster 3 computes `sha256(RepairGenerationInput.prompt)` from the wrapped C-loop generation input.
- `seed_prompt_metadata`: terminal source is the C-loop seed candidate / attempt 0 and inherited seed prompt metadata is available.
- `seed_prompt_unavailable`: terminal source is the C-loop seed candidate / attempt 0 and prompt metadata is unavailable.

Generated C repair attempts must have a non-null `terminal_prompt_hash`. `terminal_prompt_hash=None` is allowed only for seed-candidate terminal cases with `terminal_prompt_hash_source="seed_prompt_unavailable"`.

## 7. Validation commands and results

Required validation commands were run with the local repository state. The starting and final `git status --short` output showed pre-existing tracked changes in README, Cluster 2 manifests, Cluster 2 code, and Cluster 2 tests. These paths were not modified by this patch.

Because `docs/` and `audits/` are ignored by repository configuration, the required spec/report edits do not appear in `git status --short` or `git diff --stat`.

Commands run:

- `git status --short`
- required pre-edit `rg` searches over the specification and Cluster 2 references
- required post-edit `sed -n` inspections over the patched specification and this report
- required stale-term search:
  - `rg "when Cluster 2 repair loop exposes it|stop_reason.*budget exhaustion.*unrecoverable|PRepairLoopResult.stop_reason.*not populated|p_repair_stop_reason.*optional|Phase 0 report.*not defined|test_phase0_report.*unclear" docs/cluster3_implementation_specification.md`
- required new-term search:
  - `rg "p_compile_repaired_then_success|p_compile_repaired_f2_observed|p_post_compile_f3_observed|p_f3_without_compile_evidence|cluster3_phase0_scaffolding_report.md|preflight_git_status:|known_dirty_paths:|terminal_prompt_hash_source|c_repair_prompt|seed_prompt_unavailable|test_terminal_prompt_hash_generated_c_attempt_hashes_c_prompt" docs/cluster3_implementation_specification.md`
- `.venv/bin/python` syntax/content validation over the specification and report
- `git check-ignore -v docs/cluster3_implementation_specification.md audits/cluster3_specification_i_final_pre_phase0_report.md`
- final `git status --short`
- final `git diff --stat`

Results:

- Stale-term search returned no stale positive claims.
- Required new-term search found all required Section I terms.
- `.venv/bin/python` validation passed.
- `git check-ignore -v` confirmed both edited files are ignored by the repository's `.gitignore`.
- Final `git status --short` remained limited to pre-existing tracked dirty paths outside the allowed Section I edit surface.

## 8. Remaining risks

- Phase 0 implementation must still create `audits/cluster3_phase0_scaffolding_report.md`; this Section I patch defines the artifact but does not implement Phase 0.
- Semantic review of dirty paths remains partly human/audit-driven, although the report fields are now machine-checkable.
- The P-loop stop-reason table intentionally maps the existing v1 status names `compile_unchanged_exhausted` and `terminated_unrecoverable` to the review's semantic classes `budget_exhausted` and `terminal_non_repairable`; implementation should preserve those v1 enum names unless the spec is deliberately revised.

## 9. Classification

SPEC_I_FINAL_PRE_PHASE0_COMPLETE
