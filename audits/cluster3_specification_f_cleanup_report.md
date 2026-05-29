# Cluster 3 Specification §F Cleanup Report

## 1. Executive summary

Patched `docs/cluster3_implementation_specification.md` to resolve the §F implementation-readiness issues without implementing code or touching artifacts. The spec now places the public pair validator before the runner needs it, gives direct initial-F2 C repair the same helper contract as post-P C repair, defines terminal source provenance, introduces `Cluster3TraceSummary`, expands manifest identity fields, strengthens `PSeedAttempt` hash/kernel binding, fixes dispatcher validation order, clarifies inactive-P metadata, and removes stale or misleading test names.

## 2. Review findings addressed

Addressed all ten §F findings:

- Phase ordering for `validate_pair_identity`.
- Direct initial-F2 C helper contract.
- Terminal source provenance.
- `trace_summary` type/API.
- Phase 6 manifest schema depth.
- `PSeedAttempt` hash and kernel identity binding.
- Dispatcher validation order.
- Inactive P metadata.
- Stale changelog test name.
- P vs none analyzer wording.

## 3. Files updated

- `docs/cluster3_implementation_specification.md`
- `audits/cluster3_specification_f_cleanup_report.md`

No source code, artifacts, analyzer outputs, grammar files, or hashes were modified by this cleanup.

## 4. Phase ordering correction

Phase 5 now owns `cluster3/replay/no_p_pairs.py`, `pair_for_condition`, and public `validate_pair_identity`. Phase 6 is limited to manifest/artifact integration that feeds those Phase 5 primitives. Runner tests now assert public validator usage through `test_cluster3_runner_uses_public_validate_pair_identity`.

## 5. Direct-C helper contract

Phase 5 now specifies `run_cluster3_c_loop_from_f2(...)` in `cluster3/feedback/c_loop_adapter.py`. The helper is shared by `initial_f2` and `post_p_f2`, uses `config.c_repair_budget`, preserves `outer_c3_condition`, returns cached seed evaluation for attempt 0, avoids P compile-error feedback and private eval shapes, and records `c_loop_source`.

## 6. Terminal source provenance

`Cluster3EvalRow` now records `terminal_source_stage`, `terminal_generation_seed`, `terminal_attempt_index`, `terminal_source_hash`, `terminal_prompt_hash`, and `terminal_source_matches_row_source`. Row source/hash and `generated_metadata.generation_seed` are explicitly bound to the terminal source. P terminal fields remain separate when later C attempts regress.

## 7. Trace summary API

Phase 1 now defines `Cluster3TraceSummary` in `cluster3/feedback/trace.py`, with P/C loop status, attempt counts, terminal codes, terminal source stage, failure path, and `private_eval_data_included=False`. Phase 2 requires generated rows to use this type for `trace_summary`.

## 8. Manifest/pair identity schema

Phase 6 now lists the full no-P manifest entry schema needed for pair validation: artifact/path, condition, grammar variant, kernel/dtype/seed/sample identity, replay pair id, source and prompt hashes, model/tokenizer revisions, generation config, scale tier, row index, schema version, and measured outcome fields. Validation rejects revision, temperature, scale-tier, source-hash, seed, and unexpected grammar-variant mismatches.

## 9. PSeedAttempt validation updates

`PSeedAttempt` now includes `kernel_name`, optional prompt text, source hash equality to `sha256(source)`, prompt hash validation, and parent row/control identity matching. Phase 5 construction includes `kernel_name` and the stronger hash/evaluation evidence.

## 10. Dispatcher/inactive-P semantics

The dispatcher now validates condition, active factors, known failure code, and failure-code/level compatibility before success or terminal shortcuts. Inactive P rows still record config constants (`compile_error_template_v1`, `last_attempt_only_v1`) while attempt/outcome fields remain null, false, or zero.

## 11. Test name/wording cleanup

The stale changelog reference to `test_p_loop_terminal_source_equals_last_attempt_source` was replaced with `test_row_source_hash_equals_terminal_source_hash`. Analyzer wording now uses `test_p_vs_none_pairs_no_p_control_rows` and clarifies that P rows are generated Cluster 3 rows while no-P controls may come from existing Cluster 1/2 artifacts.

## 12. Validation commands and results

Executed before editing:

- `git status --short` showed pre-existing tracked changes outside the allowed docs/audits files.
- All required §F `rg` searches over the specification, Cluster 2 references, and shared analyzer/eval references were run.
- Required files were inspected: the Cluster 3 specification, Cluster 2 dataclass/trace/repair runner/correctness references, shared analyzer/eval files, and the available §E report. The two optional prior report paths named in the prompt were not present.

Executed after patching:

- Stale-term search over `docs/cluster3_implementation_specification.md` returned no matches for the required stale patterns.
- Required-new-semantics search found `run_cluster3_c_loop_from_f2`, terminal source fields, `Cluster3TraceSummary`, `validate_pair_identity`, `kernel_name`, inactive-P config fields, `test_p_vs_none_pairs_no_p_control_rows`, and manifest identity tests.
- `.venv/bin/python -c ...` validation passed for required §F markers and stale-marker absence.
- Final `git status --short` still showed only pre-existing tracked changes because `docs/` and `audits/` are ignored in this repository.
- `git diff --stat` still showed only pre-existing tracked changes for the same ignore reason.

## 13. Remaining risks

This is a documentation-only cleanup. Implementation still needs careful tests around manifest-backed control resolution, terminal source provenance for C attempts, and `Cluster3TraceSummary` serialization. No unresolved design blocker remains for Phase 0-2.

## 14. Classification

SPEC_F_CLEANUP_COMPLETE
