# Decision Log

## 1. Purpose

This decision log distills audit and development history into citation-safe decision records for the preliminary Cluster 1 + Cluster 2 technical handoff. It is not a raw audit dump, and it does not copy agent instructions or long audit prose.

The records below promote only decisions that affect current methodology, artifact identity, analysis semantics, or future Cluster 3 drift prevention. Evidence-grade audits remain supporting evidence; current `docs/` pages and registered artifacts own report-facing wording.

## 2. Source Policy

Citation-grade sources are `docs/` pages, formal `.contracts/research/` contracts after alignment, the artifact registry, and final analyzer outputs when reportable. Evidence-grade sources include `audits/`, tests, git history, ignored handoff notes, and intermediate smoke or run reports.

`.contracts/agentic/` files are working context. They can explain why a decision was needed, but they are not cited as methodology unless a verified conclusion has been promoted into `docs/` or formal contracts.

Each decision below was checked against the current docs layer, current artifacts, current audit evidence, and, where relevant, code/test paths. Historical states are marked superseded or historical rather than silently removed.

## 3. Decision Record Format

Each record uses this format:

- Status: `locked`, `superseded`, `deferred`, or `open`, with a short human label.
- Decision: one concise statement.
- Rationale: why the decision was made.
- Evidence: paths to docs, code, tests, audits, or artifacts.
- Consequences: what changed because of the decision.
- Current caveats: known limitations.
- Report impact: how the preliminary handoff must describe it.
- Cluster 3 implication: what future P work must inherit or avoid.

## D01 - Current Scope Is 2^2, Not Full 2^3

- Status: locked (accepted / active)
- Decision: The current preliminary scope is `none`, `G`, `C`, and `G+C`; P-containing cells and Cluster 3 are deferred.
- Rationale: Current artifacts and analyzer output populate only the 2^2 subset over grammar guidance and correctness feedback.
- Evidence: `docs/00_project_map.md`, `docs/05_artifacts_and_results_registry.md`, `docs/07_analysis_and_statistics.md`, `audits/repository_documentation_methodology_readiness_audit.md`, `outputs/analysis/factorial_2x2_preliminary.json`.
- Consequences: Report-facing docs must not present full 2^3 completion or P results.
- Current caveats: The analyzer output is valid and has `metadata.reportable=true` under explicit scale-tier annotation, but P cells remain deferred and the 177/180, F3, single-class model, and provenance caveats remain.
- Report impact: The preliminary report can describe a Cluster 1 + Cluster 2 handoff only.
- Cluster 3 implication: Cluster 3 must define P before adding P cells to the factorial.

## D02 - Task-Agnostic G Is Primary; Template G Is Diagnostic

- Status: locked (accepted / active)
- Decision: Primary G uses `task_agnostic`; `template_upper_bound` is diagnostic/reference material only.
- Rationale: G and G+C must share grammar semantics for comparisons to be interpretable.
- Evidence: `docs/02_methodology_cluster1.md`, `docs/03_methodology_cluster2.md`, `docs/05_artifacts_and_results_registry.md`, `shared/generation_metadata.py`, `cluster1/grammar/triton_kernel_agnostic.gbnf`, `audits/cluster2_g_plus_c_readiness_audit.md`, `audits/g_plus_c_hash_gate_and_metadata_fix_report.md`.
- Consequences: Template-G artifacts cannot fill missing task-agnostic rows or serve as the primary G estimate.
- Current caveats: Some old output summaries, constants, and agentic plans still foreground template-G history; current docs and the Cluster 1 README label it diagnostic/reference only.
- Report impact: Use task-agnostic G for current G/G+C methodology language.
- Cluster 3 implication: P work must avoid introducing a hidden alternate control surface under the same factor name.

## D03 - G Means Grammar-Guided Decoding Plus Semantic Post-Validation

- Status: locked (accepted / active)
- Decision: G acceptance requires token-level grammar-guided decoding plus offline semantic post-validation.
- Rationale: The GBNF grammar constrains syntax-like forms, while the semantic validator checks harness and surface rules that the grammar cannot fully encode.
- Evidence: `docs/02_methodology_cluster1.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `cluster1/generation/constrained_decoding.py`, `cluster1/generation/grammar_loader.py`, `cluster1/grammar/triton_kernel_validator.py`, `cluster1/tests/test_grammar.py`, `cluster1/tests/test_results.py`.
- Consequences: `grammar_active` means guidance was attempted; `grammar_valid` means acceptance.
- Current caveats: `grammar_valid = gbnf_parse_valid AND semantic_valid`; GBNF acceptance alone is not a full Triton semantic proof.
- Report impact: Grammar-funnel claims must distinguish attempted guidance from accepted rows.
- Cluster 3 implication: Any P-side structural gate must define attempted routing and acceptance separately.

## D04 - Cluster 1 Is Compile-Only

- Status: locked (accepted / active)
- Decision: Cluster 1 stops at compile/launch validation and does not claim Level 2 functional correctness.
- Rationale: Cluster 1 artifacts contain compile evidence only; numerical correctness is not evaluated there.
- Evidence: `docs/02_methodology_cluster1.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `docs/07_analysis_and_statistics.md`, `cluster1/validation/compile_check.py`, `shared/eval/adapter_cluster1.py`, `cluster1/tests/test_cluster_boundary.py`, `audits/factorial_cluster1_functional_success_normalization_fix_report.md`.
- Consequences: Cluster 1 `compile_success` stays separate from `functional_success`.
- Current caveats: For preliminary functional analysis, none/G rows normalize `functional_success=False` as unproven, not as measured Level 2 failure.
- Report impact: Never use Cluster 1 compile success as numerical-correctness evidence.
- Cluster 3 implication: P must not treat an earlier compile gate as sufficient for performance or correctness claims.

## D05 - C Repair Is F2-Only

- Status: locked (accepted / active)
- Decision: C repair fires only after Level 2 produces an F2 numerical or shape correctness failure.
- Rationale: Allowing feedback on parse, signature, or compile failures would change C from correctness feedback into a broader repair assistant.
- Evidence: `docs/03_methodology_cluster2.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `cluster2/feedback/prompts.py`, `cluster2/feedback/repair_loop.py`, `cluster2/tests/test_feedback_prompts.py`, `cluster2/tests/test_repair_loop.py`, `audits/cluster2_g_plus_c_readiness_audit.md`.
- Consequences: F0 and F1 rows terminate without feedback.
- Current caveats: Current C artifact contains only F0 parse failures, so it exercises terminal no-feedback behavior rather than successful repair.
- Report impact: Describe C as correctness-feedback repair, not compile/signature repair.
- Cluster 3 implication: P must define allowed feedback classes before implementing a repair loop.

## D06 - G+C Is G Plus C, Not A New Cluster

- Status: locked (accepted / active)
- Decision: G+C composes task-agnostic G with F2-only C repair; it is not a third cluster or a template-grammar condition.
- Rationale: The combined condition should estimate the joint use of the two current factors, not introduce a separate mechanism.
- Evidence: `docs/03_methodology_cluster2.md`, `docs/05_artifacts_and_results_registry.md`, `cluster2/modal/generation.py`, `cluster2/modal/schemas.py`, `cluster2/tests/test_modal_generation_c2.py`, `audits/cluster2_g_plus_c_readiness_audit.md`, `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md`.
- Consequences: G+C rows must record `grammar_active=True`, `grammar_variant=task_agnostic`, and C-style correctness evaluation/repair.
- Current caveats: G+C is 177/180 and has five `F3_EVAL_PIPELINE` rows.
- Report impact: Present G+C as the combined G/C cell in the 2^2 design.
- Cluster 3 implication: Future G+C+P must be a composition of defined factors, not a new untracked mechanism.

## D07 - Frozen Replay Controls And Paired Identity Are Required

- Status: locked (accepted / active)
- Decision: none and G are frozen controls, and C/G+C comparisons must use matched replay identity.
- Rationale: Pairing preserves within-unit comparisons across kernel, dtype, and seed identity.
- Evidence: `docs/03_methodology_cluster2.md`, `docs/07_analysis_and_statistics.md`, `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, `cluster2/replay/manifest.py`, `cluster2/replay/cluster1_controls.py`, `shared/analysis/factorial.py`, `audits/analyzer_pre_output_verification_audit.md`.
- Consequences: Generated C/G+C rows carry replay metadata where supported; raw Cluster 1 controls may need tuple matching.
- Current caveats: Direct Cluster 1 rows do not carry raw `replay_pair_id`; tuple matching remains required for those controls.
- Report impact: Pair counts and missing identities must be explicit.
- Cluster 3 implication: P runs must define replay identity and pairing validation before paper-scale execution.

## D08 - G And G+C Are 177/180 With Explicit Missing-Row Caveat

- Status: locked (accepted / active)
- Decision: Current G and G+C artifacts are 177/180, and the missing rows must remain visible.
- Rationale: The task-agnostic G replay artifact is incomplete, and G+C schedules only covered rows under the accepted coverage-warning policy.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/07_analysis_and_statistics.md`, `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`, `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`, `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md`, `audits/c2_replay_readiness_for_g_plus_c_from_g_n20_audit.md`, `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md`.
- Consequences: The missing rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- Current caveats: Missingness is matmul-specific and must not be silently imputed.
- Report impact: Do not claim complete G or G+C coverage.
- Cluster 3 implication: Future artifacts must distinguish complete grids from covered-row schedules before analysis.

## D09 - Modal Is Infrastructure, Not A Research Factor

- Status: locked (accepted / active)
- Decision: Modal provides GPU execution, provenance, and durability infrastructure; it is not an experimental treatment.
- Rationale: Modal is needed to execute generation/evaluation consistently, but the current factors are G and C.
- Evidence: `docs/04_modal_infrastructure.md`, `shared/modal_harness/`, `cluster1/experiments/run_cluster1_modal.py`, `cluster2/experiments/run_cluster2_modal.py`, `audits/shared_modal_smoke_boundary_hash_resolution_report.md`.
- Consequences: Modal configuration and provenance must be documented, but Modal is not a reported condition.
- Current caveats: Remote execution supports reproducibility only when provenance, hashes, versions, and artifact identity are recorded.
- Report impact: Explain Modal as methodology infrastructure, not a result.
- Cluster 3 implication: P should reuse infrastructure discipline without treating hardware plumbing as the P factor.

## D10 - Provenance Fields Are Required, And Unknown Values Are Caveats

- Status: locked (accepted / active)
- Decision: Model/tokenizer revisions, package versions, grammar SHA, Modal image provenance, token budget, condition, kernel, dtype, and seed identity must be recorded for report-scale artifacts.
- Rationale: Without row-level provenance, current artifacts cannot be audited or compared safely.
- Evidence: `docs/04_modal_infrastructure.md`, `docs/05_artifacts_and_results_registry.md`, `shared/generation_metadata.py`, `cluster1/generation/provenance.py`, `cluster2/modal/schemas.py`, `cluster2/validation/generated_metadata.py`, `audits/modal_image_sha_provenance_fix_report.md`.
- Consequences: Unknown provenance is a caveat, not a harmless default.
- Current caveats: G has `modal_image_sha=unknown`; none has legacy schema/provenance gaps.
- Report impact: Preserve provenance caveats whenever citing artifact results.
- Cluster 3 implication: P artifacts must fail gates or carry visible caveats when required provenance is missing.

## D11 - Durable Row Writing Is Required For Long Cluster 2 Runs

- Status: locked (accepted / active)
- Decision: Cluster 2 long runs must write completed logical rows durably as JSONL append/flush/fsync rows.
- Rationale: A long remote run can fail mid-stream; losing all completed rows would damage auditability.
- Evidence: `docs/04_modal_infrastructure.md`, `docs/03_methodology_cluster2.md`, `cluster2/results/logger.py`, `cluster2/experiments/run_cluster2_modal.py`, `cluster2/tests/test_results_logger.py`, `audits/c2_durable_result_writing_fix_report.md`, `audits/g_plus_c_correctness_payload_failure_fix_report.md`.
- Consequences: Partial outputs are durable prefixes and remain historical unless promoted.
- Current caveats: Full-run consumers still need strict row-count validation.
- Report impact: Current G+C is the completed 177-row artifact, not the older partial run.
- Cluster 3 implication: P runs must use durable result writing before paper-scale execution.

## D12 - Malformed Correctness Payloads Become F3_EVAL_PIPELINE Rows

- Status: locked (accepted / active)
- Decision: Missing or malformed `correctness_result` payloads are recorded as terminal `F3_EVAL_PIPELINE` rows instead of crashing the run.
- Rationale: The issue is an evaluation-pipeline failure, not an F2 numerical failure, and it should remain auditable.
- Evidence: `docs/03_methodology_cluster2.md`, `docs/04_modal_infrastructure.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `cluster2/experiments/run_cluster2_modal.py`, `shared/eval/failure_taxonomy.py`, `audits/g_plus_c_correctness_payload_failure_fix_report.md`, `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md`.
- Consequences: F3 rows are terminal failures, not functional successes.
- Current caveats: Current G+C has five `F3_EVAL_PIPELINE` rows.
- Report impact: F3 rows must be named in results and analysis caveats.
- Cluster 3 implication: P infrastructure failures need their own taxonomy and cannot be hidden as model outcomes.

## D13 - Cluster 2 Compile-Success Normalization Comes From Failure-Code Semantics

- Status: locked (accepted / active)
- Decision: Cluster 2 compile-success interpretation may be normalized from canonical failure codes when raw schema fields differ.
- Rationale: C rows lack raw top-level `compile_success`, but their F0 failure codes establish compile failure.
- Evidence: `docs/07_analysis_and_statistics.md`, `docs/06_failure_taxonomy_and_eval_ladder.md`, `shared/analysis/factorial.py`, `shared/tests/test_factorial_analysis.py`, `audits/factorial_cluster2_compile_success_normalization_fix_report.md`, `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`.
- Consequences: F0/F1 imply compile failure; F2 implies compile success; F3 is evidence-sensitive.
- Current caveats: `F3_EVAL_PIPELINE` is compile false unless independent Level 1/2 evidence exists.
- Report impact: Compile diagnostics must cite analyzer normalization, especially for C.
- Cluster 3 implication: P must define failure-code to metric mapping before analysis.

## D14 - Analyzer Output Exists And Is Reportable For The Covered 2^2 Scope

- Status: locked (accepted / active)
- Decision: `outputs/analysis/factorial_2x2_preliminary.json` is reportable for the current covered 2^2 scope under explicit `analysis_cli_annotation` paper-scale policy.
- Rationale: The analyzer loaded 714 rows, emits current summaries, and records `metadata.reportable=true`, `metadata.scale_tiers=["paper"]`, `metadata.raw_scale_tiers_before_annotation=["unspecified"]`, `metadata.scale_tier_source="analysis_cli_annotation"`, and `metadata.requested_scale_tier="paper"`.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/07_analysis_and_statistics.md`, `outputs/analysis/factorial_2x2_preliminary.json`, `audits/analyzer_scale_tier_reportability_fix_report.md`, `audits/cross_pipeline_reportability_alignment_audit.md`.
- Consequences: Preliminary statistical prose may use the verified analyzer output only with all caveats preserved.
- Current caveats: Functional outcomes have a single observed class, G/G+C are 177/180, and F3 policy remains visible.
- Report impact: The preliminary handoff can describe current 2^2 analyzer results, but not full 2^3/P results or uncaveated final-paper conclusions.
- Cluster 3 implication: P analysis outputs must expose reportability metadata and row/registry scale-tier agreement before report use.

## D15 - Old n=5, Template, Smoke, And Partial Artifacts Are Non-Authoritative

- Status: locked (accepted / active)
- Decision: Development-scale, template, smoke, failed, and partial artifacts are evidence only unless explicitly promoted into the registry.
- Rationale: Current report-scale artifact identity is controlled by `docs/05_artifacts_and_results_registry.md`.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/handoff/stale_docs_inventory.md`, `audits/repository_documentation_methodology_readiness_audit.md`, `audits/current_grammar_n5_rerun_hash_gate_report.md`, `audits/task_agnostic_g_aligned_pipeline_n5_l4_report.md`.
- Consequences: Old artifacts can explain history but cannot support current result claims.
- Current caveats: Some old summaries and agent plans remain in the repository and search results.
- Report impact: Cite registry artifacts for current rows and counts.
- Cluster 3 implication: P smoke and development artifacts must not become paper-scale evidence by accident.

## D16 - Hash And Boundary Gates Block GPU Spend Until Drift Is Explained

- Status: locked (accepted / active)
- Decision: Phase -1 and frozen-boundary hash mismatches require diagnosis and accepted documentation before expensive or report-facing runs continue.
- Rationale: Hash gates protect source, replay, grammar, and infrastructure boundaries from silent drift.
- Evidence: `docs/04_modal_infrastructure.md`, `shared/eval/content_hashes.py`, `cluster2/contracts/phase_minus1_manifest.json`, `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, `cluster2/tests/test_cluster2_boundary.py`, `audits/shared_modal_smoke_boundary_hash_resolution_report.md`, `audits/g_plus_c_hash_gate_and_metadata_fix_report.md`.
- Consequences: Hashes should not be re-recorded casually or during documentation-only phases.
- Current caveats: Some accepted historical hash changes exist, but current docs and registry own report-facing state.
- Report impact: Hash gates are reproducibility controls, not results.
- Cluster 3 implication: P implementation must inherit boundary gates before paper-scale Modal execution.

## D17 - New Fields Require Analyzer And Registry Updates

- Status: locked (accepted / active)
- Decision: Schema changes must propagate through result dataclasses, loggers, validators, analyzer normalization, docs, and the artifact registry.
- Rationale: Drift between raw rows, validators, and analyzer assumptions caused prior blocker chains.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/07_analysis_and_statistics.md`, `cluster2/results/dataclass.py`, `cluster2/results/logger.py`, `cluster2/validation/generated_metadata.py`, `shared/analysis/factorial.py`, `audits/g_plus_c_nested_metadata_validator_fix_report.md`, `audits/g_plus_c_implicit_level0_validator_fix_report.md`.
- Consequences: Adding or moving fields is a methodology change when report-facing analysis depends on them.
- Current caveats: Cluster 1 flat rows, Cluster 2 nested metadata, and analyzer normalization still require explicit schema notes.
- Report impact: Schema caveats must travel with artifact citations.
- Cluster 3 implication: P schema must be defined before paper-scale generation/evaluation.

## D18 - Cluster 3 Must Define P Before Code

- Status: deferred (accepted boundary)
- Decision: Cluster 3/P work must define factor semantics, allowed feedback, failure boundaries, metrics, artifact schema, and analyzer behavior before implementation.
- Rationale: The current workflow exists because Cluster 1 and Cluster 2 accumulated methodology drift across docs, artifacts, and analyzer semantics.
- Evidence: `docs/00_project_map.md`, `docs/04_modal_infrastructure.md`, `docs/07_analysis_and_statistics.md`, `audits/pre_paper_factorial_audit.md`, `audits/repository_documentation_methodology_readiness_audit.md`, `cluster3/README.md`.
- Consequences: P is deferred until the design is locked.
- Current caveats: Existing `.contracts/research/` P language is useful but must be aligned after current docs stabilize.
- Report impact: Preliminary report should name Cluster 3 inheritance rules, not P results.
- Cluster 3 implication: Start with contracts, failure taxonomy, metrics, schemas, and registry rules before code or runs.

## D19 - Old Template G 180/180 Is Preserved As Legacy Diagnostic Only

- Status: locked (accepted / active)
- Decision: Old template G 180/180 is preserved as legacy diagnostic only.
- Rationale: `outputs/cluster1/final_g_l4_n20.jsonl` has 180 rows and 180/180 `compile_success=true` under legacy Cluster 1 validation, but it is a legacy `template_upper_bound` compile-only artifact that fails the current paper-scale generation metadata gate.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/02_methodology_cluster1.md`, `audits/template_g_180_legacy_compatibility_audit.md`, `outputs/cluster1/final_g_l4_n20.jsonl`, `outputs/cluster1/final_g_l4_n20.jsonl.meta.json`.
- Consequences: The artifact remains available as historical template upper-bound compile-only evidence, but it is excluded from the current primary 2^2 analyzer.
- Current caveats: It is not current primary G, not task-agnostic G evidence, not current G+C pairing evidence, and not Level 2 functional correctness evidence.
- Report impact: Mention it only in optional diagnostic/reference discussion. Do not include it in primary results tables, do not use it to fill missing task-agnostic G rows, and do not pair it with current task-agnostic G+C.
- Cluster 3 implication: Future diagnostic controls must be labeled separately from primary factor cells and must carry current metadata before analysis.

## D20 - Current Template Upper-Bound G Is A Non-Primary Diagnostic Ceiling

- Status: locked (accepted / active)
- Decision: The current-pipeline `template_upper_bound` G artifact is a diagnostic ceiling/reference only.
- Rationale: `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` reruns template G under the current Cluster 1 runner and metadata gate, but it uses a task-encoded grammar surface. It is therefore useful for compile and grammar-funnel diagnostics, not for replacing task-agnostic G.
- Evidence: `docs/05_artifacts_and_results_registry.md`, `docs/02_methodology_cluster1.md`, `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md`, `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`, `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl.meta.json`.
- Consequences: The artifact is labeled `G_template` / template upper-bound G in diagnostic contexts, excluded from `outputs/analysis/factorial_2x2_preliminary.json`, and cannot fill missing task-agnostic G rows.
- Current caveats: It is Cluster 1 compile-only evidence, rows are flat Cluster 1 rows with some run fields in the sidecar, and no matching current-pipeline template G+C artifact exists yet.
- Report impact: Discuss only in an optional diagnostic section or appendix. Do not include it in the primary results table.
- Cluster 3 implication: Future diagnostic surfaces must remain separately labeled and must not masquerade as primary factor cells.

## D21 - Cluster 3 F1_RUNTIME Is Deferred To v2

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 P repair handles `F1_COMPILE`; `F1_RUNTIME` terminates in v1 and is deferred to v2.
- Rationale: Runtime-launch evidence needs a separate feedback contract and should not be mixed with compile-error repair.
- Implementation path: `cluster3/feedback/dispatcher.py`; `cluster3/feedback/compile_error_repair.py`
- Test/report evidence path: `cluster3/tests/test_dispatcher.py`; `cluster3/tests/test_cluster3_boundary.py`; `audits/cluster3_phase3_dispatcher_report.md`; `audits/cluster3_phase9_boundary_tests_report.md`
- Caveat: This is a v1 boundary decision, not a claim about future runtime repair effectiveness.

## D22 - Cluster 3 Dispatcher Lives In cluster3/feedback/dispatcher.py

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 routing policy is centralized in `cluster3/feedback/dispatcher.py`.
- Rationale: A single deterministic dispatcher makes F0, F1, F2, and F3 routing auditable before runner orchestration.
- Implementation path: `cluster3/feedback/dispatcher.py`
- Test/report evidence path: `cluster3/tests/test_dispatcher.py`; `cluster3/tests/test_run_cluster3_modal_cli.py`; `audits/cluster3_phase3_dispatcher_report.md`; `audits/cluster3_phase5_runner_orchestration_report.md`
- Caveat: The dispatcher is local routing logic; it does not imply Modal smoke has run.

## D23 - P Does Not Add New Failure Codes

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 P reuses canonical F0/F1/F2/F3 codes and adds no new failure-code names.
- Rationale: P outcomes are row diagnostics and stop reasons, while failure families remain shared taxonomy semantics.
- Implementation path: `shared/eval/failure_taxonomy.py`; `cluster3/results/dataclass.py`; `cluster3/feedback/dispatcher.py`
- Test/report evidence path: `cluster3/tests/test_cluster3_schema.py`; `cluster3/tests/test_cluster3_boundary.py`; `audits/cluster3_phase2_schema_logger_report.md`; `audits/cluster3_phase9_boundary_tests_report.md`
- Caveat: P-specific fields can describe repair outcomes, but they are not canonical F-code extensions.

## D24 - Cluster 3 Schema Version Is 1

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 result rows use `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`.
- Rationale: The P/C row shape is new relative to Cluster 2 and needs an explicit schema version for validators, loggers, and analyzer consumers.
- Implementation path: `cluster3/results/dataclass.py`; `cluster3/results/logger.py`
- Test/report evidence path: `cluster3/tests/test_cluster3_schema.py`; `cluster3/tests/test_cluster3_logger.py`; `audits/cluster3_phase2_schema_logger_report.md`
- Caveat: Version 1 describes local v1 row schema only; it does not register output artifacts.

## D25 - Compile-Error Excerpts Are Capped At 2000 Chars

- Status: locked (Cluster 3 v1 active)
- Decision: P feedback uses a 2000-char compile-error excerpt cap and stores the full raw error hash where applicable.
- Rationale: Bounded excerpts reduce feedback leakage and prompt drift while preserving full-error identity through `sha256`.
- Implementation path: `cluster3/feedback/prompts.py`; `cluster3/modal/result_extraction.py`
- Test/report evidence path: `cluster3/tests/test_p_prompts.py`; `cluster3/tests/test_p_repair_f1_fixtures.py`; `cluster3/tests/test_cluster3_boundary.py`; `audits/cluster3_phase8_f1_fixture_smoke_report.md`
- Caveat: The cap is a content-boundary rule, not an output-result claim.

## D26 - LLVM/PTX Are Allowed In P Feedback

- Status: locked (Cluster 3 v1 active)
- Decision: LLVM and PTX terms are allowed in P feedback when they appear in compiler diagnostics.
- Rationale: Compiler diagnostics often contain LLVM/PTX text; banning those terms would remove relevant compile-error evidence.
- Implementation path: `cluster3/feedback/sanitizer.py`; `cluster3/feedback/prompts.py`
- Test/report evidence path: `cluster3/tests/test_p_sanitizer.py`; `cluster3/tests/test_p_prompts.py`; `cluster3/tests/test_cluster3_boundary.py`; `audits/cluster3_phase9_boundary_tests_report.md`
- Caveat: This allowance does not permit profiler, speedup, timing, benchmark, token-rate, or Level 2 correctness feedback.

## D27 - P Feedback Is Compile-Error-Only

- Status: locked (Cluster 3 v1 active)
- Decision: P feedback is restricted to compile-error diagnostics and excludes Level 2 correctness details, private eval shapes, and optimizer/profiler language.
- Rationale: P is the compile-error repair factor; allowing other evidence would confound P with C or future factors.
- Implementation path: `cluster3/feedback/prompts.py`; `cluster3/feedback/sanitizer.py`; `cluster3/feedback/compile_error_repair.py`
- Test/report evidence path: `cluster3/tests/test_p_prompts.py`; `cluster3/tests/test_p_sanitizer.py`; `cluster3/tests/test_cluster3_boundary.py`; `audits/cluster3_phase1_p_repair_loop_report.md`; `audits/cluster3_phase9_boundary_latency_remediation_report.md`
- Caveat: This is a boundary claim about allowed feedback, not downstream outcome evidence.

## D28 - Cluster 3 Correctness Runner Is A Local Adapter

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 correctness evaluation is a local adapter over existing Cluster 2 Modal correctness surfaces.
- Rationale: Reusing Cluster 2 correctness surfaces keeps Level 2 semantics aligned and avoids introducing a second correctness implementation.
- Implementation path: `cluster3/modal/correctness_runner.py`; `cluster3/modal/result_extraction.py`; `cluster3/feedback/c_loop_adapter.py`
- Test/report evidence path: `cluster3/tests/test_correctness_runner_adapter.py`; `cluster3/tests/test_run_cluster3_modal_cli.py`; `audits/cluster3_phase4_correctness_adapter_report.md`; `audits/cluster3_phase5_runner_orchestration_report.md`
- Caveat: The adapter is local; Phase 11 Modal smoke still requires explicit user approval.

## D29 - compile_feedback_active Is Added While perf_feedback_active Is Preserved

- Status: locked (Cluster 3 v1 active)
- Decision: Cluster 3 analyzer semantics add `compile_feedback_active` as the P factor while preserving `perf_feedback_active` for backward compatibility.
- Rationale: P is compile-error feedback, not a performance factor, but existing downstream consumers may still expect the legacy feedback column name.
- Implementation path: `shared/analysis/factorial.py`
- Test/report evidence path: `shared/tests/test_analyzer_cluster3.py`; `shared/tests/test_factorial_analysis.py`; `audits/cluster3_phase7a_analyzer_support_report.md`
- Caveat: The analyzer-derived `p_helped` diagnostic is conservative and `PENDING_RESEARCH`; it is not a row field or result claim.

## D30 - Phase 11 Modal Smoke Requires Explicit User Approval

- Status: locked (Cluster 3 v1 active)
- Decision: Phase 11 n=1 Modal smoke must not run unless the user explicitly authorizes it.
- Rationale: Modal execution can spend paid resources and crosses from local implementation validation into remote smoke execution.
- Implementation path: `cluster3/experiments/run_cluster3_modal.py`; `cluster3/modal/correctness_runner.py`
- Test/report evidence path: `cluster3/tests/test_run_cluster3_modal_cli.py`; `audits/cluster3_phase5_runner_orchestration_report.md`; `audits/cluster3_phase10_documentation_report.md`
- Caveat: No Phase 11 Modal smoke rows are registered by this decision log.

## 4. Superseded Or Legacy Decisions

| Historical state | Current status | Current replacement | Evidence |
|---|---|---|---|
| Template-G or `final_g_l4_n20.jsonl` treated as the primary G/G+C route | superseded | Task-agnostic G is primary; template-G is diagnostic/reference only | `docs/02_methodology_cluster1.md`; `docs/05_artifacts_and_results_registry.md`; `audits/repository_documentation_methodology_readiness_audit.md` |
| n=5 artifacts treated as development gate evidence for current report-scale claims | historical only | n=5 artifacts are development/legacy unless promoted | `docs/05_artifacts_and_results_registry.md`; `docs/handoff/stale_docs_inventory.md` |
| 1536-token defaults in older docs/constants treated as current paper artifact settings | superseded for current artifacts | Current C/G+C artifacts record `max_new_tokens=2048`; code/config cleanup is later work | `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md`; `audits/repository_documentation_methodology_readiness_audit.md` |
| Analyzer-missing blocker | superseded | Analyzer output exists and is reportable via explicit scale-tier annotation | `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md` |
| Raw agent plans as methodology | historical only | Agent plans are context, not citation-grade | `docs/00_project_map.md`; `docs/handoff/stale_docs_inventory.md` |
| Failed or partial G+C output as current artifact | superseded | Completed 177-row G+C artifact is current; partial outputs are historical evidence | `docs/05_artifacts_and_results_registry.md`; `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md` |

## 5. Decision-To-Document Traceability

| Decision | Current doc owner | Supporting artifact/code/audit | Current status | Caveat |
|---|---|---|---|---|
| D01 | `docs/00_project_map.md`; `docs/07_analysis_and_statistics.md` | analyzer JSON; Phase 0 audit | locked | P cells deferred |
| D02 | `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md` | grammar files; G/G+C artifacts | locked | Old evidence remains searchable |
| D03 | `docs/02_methodology_cluster1.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | validators and grammar tests | locked | GBNF is not full Triton semantics |
| D04 | `docs/02_methodology_cluster1.md`; `docs/07_analysis_and_statistics.md` | none/G artifacts; C1 normalization audit | locked | Functional success unproven |
| D05 | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | feedback code/tests | locked | Current C has only F0 rows |
| D06 | `docs/03_methodology_cluster2.md` | G+C artifact and routing tests | locked | G+C 177/180 and F3 caveats |
| D07 | `docs/03_methodology_cluster2.md`; `docs/07_analysis_and_statistics.md` | replay manifest; analyzer audit | locked | Raw C1 controls need tuple matching |
| D08 | `docs/05_artifacts_and_results_registry.md` | G/G+C artifacts; missing-row audits | locked | Missingness is matmul-specific |
| D09 | `docs/04_modal_infrastructure.md` | Modal harness code/tests | locked | Modal alone does not prove reproducibility |
| D10 | `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md` | provenance helpers/schemas | locked | G image ID unknown; baseline legacy |
| D11 | `docs/04_modal_infrastructure.md` | C2 logger and durability audit | locked | Partial outputs need strict caveats |
| D12 | `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md` | G+C artifact; payload fix audit | locked | Five current F3 rows |
| D13 | `docs/07_analysis_and_statistics.md` | analyzer code/tests; normalization audits | locked | F3 policy evidence-sensitive |
| D14 | `docs/07_analysis_and_statistics.md` | analyzer JSON | locked | reportable via `analysis_cli_annotation`; caveats remain |
| D15 | `docs/05_artifacts_and_results_registry.md`; `docs/handoff/stale_docs_inventory.md` | legacy audits/summaries | locked | Old files remain searchable |
| D16 | `docs/04_modal_infrastructure.md` | hash manifests/tests/audits | locked | Accepted historical drifts need audit trail |
| D17 | `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md` | schema validators/analyzer | locked | Mixed schemas remain documented |
| D18 | future `docs/10_cluster3_drift_prevention_plan.md` | current docs; Phase 0 audit | deferred | P is not defined for results yet |
| D19 | `docs/05_artifacts_and_results_registry.md`; `docs/02_methodology_cluster1.md` | legacy template G artifact; template-G audit | locked | Diagnostic only; not current primary G |
| D20 | `docs/05_artifacts_and_results_registry.md`; `docs/02_methodology_cluster1.md`; `docs/07_analysis_and_statistics.md` | current template upper-bound G artifact and run report | locked | Diagnostic only; matching template G+C still required for template C interaction |
| D21 | `docs/04_methodology_cluster3.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | dispatcher and boundary tests | locked | F1_RUNTIME deferred to v2 |
| D22 | `docs/04_methodology_cluster3.md` | Cluster 3 dispatcher tests and reports | locked | Local routing only |
| D23 | `docs/04_methodology_cluster3.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | Cluster 3 schema and taxonomy tests | locked | No new F-code names |
| D24 | `docs/04_methodology_cluster3.md`; `docs/05_artifacts_and_results_registry.md` | Cluster 3 dataclass/logger tests | locked | No rows registered |
| D25 | `docs/04_methodology_cluster3.md` | P prompt and F1 fixture tests | locked | Excerpt cap only |
| D26 | `docs/04_methodology_cluster3.md` | P sanitizer and prompt tests | locked | Compiler diagnostics only |
| D27 | `docs/04_methodology_cluster3.md` | P sanitizer, prompt, and boundary tests | locked | No downstream outcome claim |
| D28 | `docs/04_methodology_cluster3.md` | correctness adapter tests and reports | locked | Phase 11 not run |
| D29 | `docs/04_methodology_cluster3.md`; `docs/07_analysis_and_statistics.md` | analyzer tests and report | locked | `p_helped` remains `PENDING_RESEARCH` |
| D30 | `docs/04_methodology_cluster3.md`; `docs/05_artifacts_and_results_registry.md` | runner CLI tests and Phase 10 report | locked | Requires explicit approval |

## 6. Cluster 3 Inheritance Checklist

- Define the P factor before implementation.
- Define allowed feedback before any P repair loop.
- Define failure classes before feedback routing.
- Define artifact schema before Modal execution.
- Define provenance requirements before paper-scale runs.
- Define pairing identity and missing-row policy before analysis.
- Update analyzer normalization before citing P outputs.
- Update the artifact registry before report-facing docs cite P artifacts.
- Run smoke, development, and audit gates before any paper-scale P run.
- Keep raw artifacts immutable; use new artifact IDs for new lineages.
- Preserve source-of-truth hierarchy: code/tests, artifacts, docs, contracts, audits, agent context.
