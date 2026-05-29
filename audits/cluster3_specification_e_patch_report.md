# Cluster 3 Specification §E Patch Report

## 1. Executive summary

Patched `docs/cluster3_implementation_specification.md` to address the remaining §E blockers without implementing code or touching artifacts. The spec now treats C repair independently from "C after P", separates P-terminal outcomes from final row outcomes, adds Cluster 3-owned correctness-result extraction, updates analyzer P-pair handling, strengthens P seed binding, removes post-P F3 compile-repair overclaiming, requires `trace_summary`, replaces private Cluster 2 pair-validator language, fixes sanitizer drift testing, and corrects Phase 12 P+C cost estimates.

## 2. Review issues addressed

Addressed all twelve §E findings:

- Direct initial-F2 C loop path.
- C loop regression terminal states.
- Stale terminal-code schema language.
- Correctness adapter infrastructure payload handling.
- Cluster 3 correctness-result extraction/synthesis.
- Analyzer P-pair helper compatibility.
- Stronger `PSeedAttempt` binding.
- Post-P F3 compile-evidence gating.
- `trace_summary` clarity.
- Pair identity helper mismatch.
- Sanitizer drift test weakness.
- Phase 12 P+C cost underestimate.

## 3. Files updated

- `docs/cluster3_implementation_specification.md`
- `audits/cluster3_specification_e_patch_report.md`

No source code, artifacts, analyzer outputs, grammar files, or hashes were modified by this task.

## 4. Schema semantic changes

The spec now defines `initial_failure_code`, `p_terminal_failure_code`, `c_terminal_failure_code`, `c_loop_source`, and `c_terminal_level_reached`. Row `failure_code`, `compile_success`, and `functional_success` are final row outcomes after all active loops. `p_compile_repair_succeeded` is explicitly P-terminal and survives later C regression.

## 5. Dispatcher/orchestration changes

The dispatcher now marks direct initial-F2 C eligibility with `c_loop_source="initial_f2"`. Phase 5 now models three paths: direct initial-F2 C, P-to-F2 then C, and C-regression terminal failure. Direct initial-F2 C rows keep P inactive while still allowing `c_loop_fired=True`.

## 6. Correctness adapter/extraction changes

The adapter now gates nested `correctness_result.identity` checks to normal success/failure payloads and preserves infrastructure payloads without crashing. The spec adds `cluster3/modal/result_extraction.py` with `extract_or_synthesize_cluster3_correctness_result_dict(...)` to return canonical result dictionaries for success, failure, infrastructure, and malformed payload shapes.

## 7. Analyzer compatibility changes

The analyzer section now specifies `paired_p_factor_summary(...)` backed by `paired_condition_summary(...)` instead of forcing P pairs through replay-only assumptions. The helper handles replay controls and generated Cluster 2 controls, keys by identity fields including seed/sample/pair metadata, and rejects mixed grammar variants unless explicitly allowed.

## 8. Pairing/provenance changes

Phase 6/runner language now requires Cluster 3's public `validate_pair_identity`; Cluster 2 private pairing-context validation must not be called as the full validator. `PSeedAttempt` now binds generation seed, base seed, sample index, kernel class, dtype, source hash, optional prompt hash, and initial evaluation evidence.

## 9. Tests added to the specification

The specification now lists tests for:

- Direct initial-F2 C loop in C+P and G+C+P.
- Schema accepting direct C without P.
- C terminal F0/F1/F2/F3/None and C regression after P.
- Infrastructure correctness payloads and result extraction.
- P/no-P analyzer pairing over generated and replay controls.
- Strong `PSeedAttempt` validation.
- Post-P F3 compile-evidence gating.
- Required `trace_summary`.
- Cluster 3 pair identity validator usage.
- Current Cluster 2 sanitizer-term drift detection.

## 10. Cost/budget correction

Phase 12 now distinguishes P-only (`1 + P_budget`), C-only (`1 + C_budget`), and P+C (`1 + P_budget + C_budget`) worst cases. With defaults, P+C rows can reach 11 rounds. The spec adds a go/no-go guard that blocks development-scale P+C cells until smoke confirms average repair attempts are within expected bounds.

## 11. Remaining risks

This is a specification-only patch. The remaining risks move to implementation:

- Actual result-extraction code must preserve enough F3 detail without leaking private payloads.
- Analyzer identity-key handling must be tested against real heterogeneous Cluster 1/2/3 rows.
- C-regression validation depends on careful row-builder use of terminal trace summaries.

## 12. Validation commands and results

Executed in this patch run:

- `git status --short` before patch: showed pre-existing tracked changes in `README.md`, `cluster2/contracts/*`, `cluster2/experiments/run_cluster2_modal.py`, `cluster2/modal/generation.py`, `cluster2/results/dataclass.py`, several `cluster2/tests/*`, and `cluster2/validation/generated_metadata.py`.
- Required `rg` searches over the specification, Cluster 2, and shared evidence: completed before editing.
- Required file inspections: completed for the specification, Cluster 2 repair/prompts/correctness/runner/results code, shared analyzer/eval code, the Cluster 3 draft plan, and the available Cluster 3 plan audit report. The specifically named `audits/cluster3_plan_audit_and_design_resolution.md` and `audits/cluster3_implementation_specification_report.md` were not present.
- `sed -n '1,180p'`, `180,420p`, `420,760p`, and `760,1040p` over `docs/cluster3_implementation_specification.md`: completed.
- `sed -n '1,320p' audits/cluster3_specification_e_patch_report.md`: completed.
- `.venv/bin/python -c ...`: passed, confirming required new semantic markers and report classification are present.
- Stale-term search: only two hits remained, both from the required test name `test_schema_allows_c_loop_fired_without_p_repair_attempted_when_source_initial_f2` and the §E1 changelog entry listing that required test. No stale positive claims remained.
- Required-new-semantics search: passed; `c_loop_source`, `initial_f2`, `post_p_f2`, `p_terminal_failure_code`, `c_terminal_failure_code`, `extract_or_synthesize_cluster3_correctness_result_dict`, `paired_p_factor_summary`, `validate_pair_identity`, `post_p_f3_observed`, and `trace_summary` are present.
- Final `git status --short`: still showed only the pre-existing tracked changes because `.gitignore` ignores `docs/` and `audits/`.
- `git diff --stat`: showed only the pre-existing tracked changes for the same reason. `git check-ignore -v` confirmed `.gitignore:43` ignores `docs` and `.gitignore:44` ignores `audits`.

## 13. Classification

SPEC_E_PATCH_COMPLETE
