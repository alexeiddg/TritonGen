# Cluster 3 Specification §G Contract Cleanup Report

## 1. Executive summary

Patched `docs/cluster3_implementation_specification.md` to resolve the §G implementation-readiness issues without implementing code or touching artifacts. The spec now gives the C-loop adapter a Cluster 3-owned, provenance-complete result type, adds explicit `kernel_name` and seed-preservation rules, extends `Cluster3TraceSummary` to satisfy schema validation claims, corrects dispatcher test expectations, makes manifest `sample_index` optional/derived for Cluster 2 generated controls, completes P stop-reason semantics, and fixes the remaining target-tree/test hygiene.

## 2. Review findings addressed

Addressed all eight §G findings:

- C-loop helper return type was insufficient.
- `run_cluster3_c_loop_from_f2(...)` lacked `kernel_name`.
- Seeded C attempt generation seed rules were ambiguous.
- `Cluster3TraceSummary` lacked terminal provenance and final success fields.
- Dispatcher tests contradicted the validation order.
- Manifest schema assumed top-level `sample_index` on Cluster 2 generated rows.
- P stop-reason mapping was incomplete.
- Target tree and phase-test hygiene had stale paths/wording.

## 3. Files updated

- `docs/cluster3_implementation_specification.md`
- `audits/cluster3_specification_g_contract_cleanup_report.md`

No source code, artifacts, analyzer outputs, grammar files, or hashes were modified by this cleanup.

## 4. C-loop result/provenance contract

Phase 5 now defines `Cluster3CLoopResult` in `cluster3/feedback/c_loop_adapter.py`. The helper returns this Cluster 3-owned result instead of a Cluster 2 repair-result-like object. Row construction now uses `terminal_source`, `terminal_source_hash`, `terminal_generation_seed`, `terminal_prompt_hash`, `terminal_correctness_result`, C terminal fields, and wrapped trace data from `Cluster3CLoopResult`.

## 5. kernel_name and seed preservation

`run_cluster3_c_loop_from_f2(...)` now takes explicit `kernel_name: str` and passes it into evaluation identity/wrapper closures. The spec now states that budget-zero C preserves the seed candidate source and `seed_candidate_generation_seed`, while generated C attempts capture their own attempt seeds and the terminal seed follows whichever source becomes terminal.

## 6. Trace summary contract

`Cluster3TraceSummary` now includes terminal source hash, terminal generation seed, terminal prompt hash, final compile/functional success flags, repair/eval success flags, and row source hash. Phase 2 validation now cross-checks trace fields against row terminal provenance and final outcome fields while preserving the no-private-eval-data rule.

## 7. Dispatcher validation/test correction

Phase 3 tests now expect ValueError for F-code/level mismatches and unknown condition/code cases before routing or terminal shortcuts. The old expectation that mismatched F1-at-level-0 or F2-at-level-1 cases terminate has been removed.

## 8. Manifest sample_index derivation

Phase 6 manifest schema now records `sample_index: int | None` plus `sample_index_source`. The builder uses row sample index when present, derives from `base_seed` only when the run schedule proves one-to-one identity, derives from `attempt_index` only when documented, and marks unresolved rows as missing. Pair validation rejects `sample_index_source="missing"`.

## 9. P stop-reason contract

The spec now maps P statuses to explicit stop reasons: `p_budget_exhausted`, `p_compile_repaired_f2_observed`, `p_post_compile_f3_observed`, `p_f3_without_compile_evidence`, `p_terminal_non_repairable`, `p_not_applicable`, and `p_compile_repaired_then_success`. F0 handling now uses `failure_code.startswith("F0_")`; F1 runtime uses exact equality.

## 10. Spec hygiene updates

The final target tree now includes `cluster3/contracts/`, `cluster3/contracts/no_p_pair_manifest.json`, `cluster3/replay/build_no_p_pair_manifest.py`, and `cluster3/feedback/c_loop_adapter.py`. Phase 1 pass criteria include `cluster3/tests/test_cluster3_trace.py`, Phase 0 wording no longer says "The three tests above", and Phase 6 tests include import/scaffold checks for the contracts and manifest builder.

## 11. Validation commands and results

Executed before editing:

- `git status --short`: showed pre-existing tracked changes outside the allowed docs/audits files.
- All required §G `rg` searches over the specification, Cluster 2 references, and shared references.
- Required files were inspected: the Cluster 3 specification, Cluster 2 repair/trace/results/schemas/runner/correctness references, shared eval/analyzer references, and the available §E/§F reports.

Executed after patching:

- Required `sed` readbacks over `docs/cluster3_implementation_specification.md` and this report completed.
- Stale-term search returned no matches for the required stale patterns.
- Required-new-terms search found `Cluster3CLoopResult`, `kernel_name`, `terminal_correctness_result`, terminal seed/prompt fields, `sample_index_source`, `p_compile_repaired_f2_observed`, `cluster3/contracts`, `build_no_p_pair_manifest`, and `test_cluster3_trace`.
- `.venv/bin/python -c ...` validation passed for required §G markers and stale-marker absence.
- Final `git status --short` still showed only pre-existing tracked changes because `docs/` and `audits/` are ignored in this repository.
- `git diff --stat` still showed only pre-existing tracked changes for the same ignore-rule reason.

## 12. Remaining risks

This remains a documentation-only cleanup. Implementation still needs careful wrapper tests around C attempt seed capture, result extraction from infrastructure payloads, and manifest derivation against real Cluster 2 generated JSONL rows. No unresolved design blocker remains for Phase 0-2 implementation.

## 13. Classification

SPEC_G_CONTRACT_CLEANUP_COMPLETE
