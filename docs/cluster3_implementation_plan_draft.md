# Cluster 3 Implementation Plan Draft

- Status: Draft / not implemented
- Scope: planning only
- No code written
- No artifacts generated
- No Modal runs launched
- Research-dependent sections marked PENDING_RESEARCH
- Design-dependent sections marked PENDING_DESIGN_DECISION

## 0. Executive Summary

Cluster 3 defines the P factor as compile-error feedback repair: a repair mechanism that observes compile-stage failures, sends bounded compiler feedback back to the model, and retries generation without altering the existing none, G, C, or G+C records. P matters because the current 2^2 study isolates grammar-guided decoding (G) and correctness-feedback repair (C), while compile failures remain terminal in the Cluster 2 repair ladder: the Cluster 2 methodology states that C feedback is only eligible after Level 2 failures and that Level 0/1 failures terminate without C repair (`docs/03_methodology_cluster2.md:87-102`). The research-grounded first P design uses structured compile-error feedback, a 3-5 iteration budget, conversational history across attempts, no profiler/performance feedback, and dispatch by failure code so F1 routes to P and F2 routes to C. P composes with G and C by adding four future cells, P, G+P, C+P, and G+C+P, which must be paired by seed against the existing no-P cells without overwriting those artifacts. The June 8 target should be development-scale evidence for the four P-containing cells if local tests, schema, analyzer support, and n=1 smoke pass; paper-scale P should remain a paper-revision target unless all gates in the existing scale policy are satisfied. The remaining design-dependent items are F1_RUNTIME scope, exact prompt template, exact schema names, and repaired-vs-organic reporting.

## 1. Factor Definition

P = compile-error feedback repair. As a research factor, P is active when a candidate kernel reaches the compile/evaluation ladder and fails at the compile stage, then receives feedback derived from that compile failure before a bounded retry. The current ladder separates Level 0 parse/signature checks, Level 1 compile/JIT/import checks, Level 2 numerical correctness, and F3 evaluation-pipeline failures (`docs/06_failure_taxonomy_and_eval_ladder.md:21-46`). Cluster 1 already records compile-stage failures but explicitly does not feed compiler messages back to the model (`cluster1/experiments/run_cluster1_modal.py:1-12`), so Cluster 3 changes only that feedback boundary.

P likely observes F1_COMPILE and possibly F1_RUNTIME. The taxonomy defines F1_COMPILE for module import/Triton JIT/compile failures and F1_RUNTIME for launch/runtime exceptions before correctness comparison (`docs/06_failure_taxonomy_and_eval_ladder.md:36-46`; `shared/eval/failure_taxonomy.py:8-25`). Whether F1_RUNTIME belongs inside the first P version is PENDING_DESIGN_DECISION because runtime exceptions can border Level 2 behavior depending on when tensors are compared.

P does not observe F0 parse failures unless a later contract explicitly redefines P. Level 0 parse/signature failures are pre-compile structural failures (`docs/06_failure_taxonomy_and_eval_ladder.md:36-40`; `shared/eval/levels/level0_parse.py:11-55`). P also does not observe F2 numerical failures; those belong to C. Cluster 2 states that C repair is triggered only for Level 2 numerical mismatches and that F0/F1 failures terminate without C feedback (`docs/03_methodology_cluster2.md:87-102`). The C prompt boundary enforces this by allowing only F2 numeric, NaN/Inf, and shape feedback (`cluster2/feedback/prompts.py:17-23`).

Feedback format is now a research-grounded design decision: structured compile-error feedback following Self-Debug's rubber-duck pattern, adapted for Triton. Self-Debug teaches the model to investigate execution results and explain generated code in natural language ([Chen et al., 2023](https://arxiv.org/abs/2304.05128)); P adapts that pattern as kernel source plus Triton compile error message plus a structured natural-language diagnostic note. The note should contain failure code, compiler diagnostic class, line/symbol references when available, a short stderr excerpt, and a stable hash of the full raw error for auditability. The feedback should not include task-specific tiling hints, profiler observations, numerical mismatch details, or generated code patches.

Repilot is the main alternative design to cite, but not the design chosen here. Repilot fuses an LLM with a completion engine that prunes infeasible tokens and proactively completes tokens during patch synthesis ([Wei, Xia, and Zhang, 2023](https://arxiv.org/abs/2309.00608)). A Repilot-style AST/completion-engine approach would move compile-error handling into token-time synthesis, while this Cluster 3 plan keeps P as an inference-time repair factor after Level 1 so it composes cleanly with existing G and C cells. PENDING_DESIGN_DECISION: exact prompt template, raw excerpt length, and diagnostic parser format. The `cluster3/README.md` currently leaves the Cluster 3 contract TBD (`cluster3/README.md:90-93`), so this draft treats the factor definition as a gated research contract.

## 2. Composition With Existing Factors

Full 2^3 analysis requires eight cells: none, G, C, G+C, P, G+P, C+P, and G+C+P. The current primary report has only four cells and explicitly excludes P-containing conditions (`docs/05_artifacts_and_results_registry.md:11-20`; `.contracts/research/research_scope.md:17-39`). P-containing cells must be written as new Cluster 3 artifacts and must not overwrite existing Cluster 1 or Cluster 2 artifacts.

Condition P has only compile-error feedback repair active. Cluster 3 should own the row. It needs fresh generation because the P retry behavior changes the path after an F1 failure. It pairs by `(kernel_class, kernel_name, dtype, base_seed)` against the none cell.

Condition G+P has grammar guidance and compile-error feedback active. Cluster 3 should own the row while reusing the Cluster 1 grammar configuration and shared generation metadata. It needs fresh P-aware generation or replay from a frozen G control only when the replay contract preserves the same prompt, seed, model revision, grammar variant, and temperature. It pairs against G.

Condition C+P has correctness repair and compile-error feedback active. Cluster 3 should own the row because both repair mechanisms may be present. It should reuse Cluster 2 C repair components where safe, but the row must capture P-specific trace metadata. It pairs against C.

Condition G+C+P has all three factors active. Cluster 3 should own the row, inherit G from Cluster 1, inherit C semantics from Cluster 2, and add P at the compile-failure boundary. It pairs against G+C.

Cluster 2 already freezes replay controls for C and G+C and validates paired context across kernel, dtype, seeds, prompt, model revisions, and generation parameters (`cluster2/experiments/run_cluster2_modal.py:1061-1168`). Cluster 3 should preserve that paired identity discipline. The shared registry already reserves the allowed Cluster 3 cells (`shared/factors/registry.py:17-21`), and the analyzer contains labels for P-containing cells, but current documentation marks P rows missing/deferred rather than reportable (`docs/07_analysis_and_statistics.md:9-18`; `shared/analysis/factorial.py:46-59`).

Replay should be treated as a control-preservation mechanism, not as permission to mutate old rows. If an existing no-P row is reused as the paired baseline, Cluster 3 should reference it through immutable identity metadata and a manifest entry. If the P-containing condition needs a new first attempt because the P runner changes prompt wiring, retry policy, or row schema, the new row should still reuse the same base seed and comparable generation settings. Any deviation from the seed, prompt, model, tokenizer, grammar variant, or temperature pairing contract should make the pair non-reportable until reviewed.

## 3. Eval Pipeline Alignment With Cluster 2

Cluster 3 should inherit the shared Level 0/1/2 ladder. The shared levels are provided as parse/signature checks, compile checks, and correctness checks under `shared/eval/levels/` (`shared/eval/levels/level0_parse.py:11-55`; `shared/eval/levels/level1_compile.py:1-61`; `shared/eval/levels/level2_correctness.py:139-201`). Cluster 2 uses this ladder before applying C repair and records F3 rows when the evaluation harness itself fails (`docs/03_methodology_cluster2.md:74-83`; `cluster2/modal/correctness_runner.py:70-150`).

P repair fits after a Level 1 failure and before final terminal classification. In current Cluster 2, Level 1 compile failures return F1 with `compile_success=false` and terminate without C feedback (`cluster2/modal/correctness_runner.py:208-233`; `cluster2/feedback/repair_loop.py:366-369`). Cluster 3 changes that terminal point for P-active cells only: an eligible F1 failure can trigger a bounded compile-error repair loop. P remains methodologically distinct from C because P acts on F1 while C acts on F2. Cluster 2's repair loop currently supports only `C` and `G+C` conditions (`cluster2/feedback/repair_loop.py:125-143`), so Cluster 3 should not silently route P through the existing C loop without a new contract.

P fires on F1 just as C fires on F2. When both P and C are active, the design is dispatch by failure code, not a unified repair loop: F0 and F3 terminate; eligible F1 routes to the P-specific compile-error loop; after each P attempt the candidate re-enters Level 0/1/2; eligible F2 routes to the C-specific correctness loop when C is active. This keeps compile-time and runtime/numerical feedback separate and prevents C from seeing compiler diagnostics or P from seeing numerical mismatches. The specialization follows the PGS principle that feedback should be targeted and structurally minimal rather than general critique ([He et al., 2025](https://arxiv.org/abs/2506.18315); align final bibliography key if project notes use Wang et al., 2025). PENDING_DESIGN_DECISION: exact dispatcher module boundary. The current Cluster 3 README says C is active before compiler/profiler repair for C+P cells (`cluster3/README.md:44-62`), while this compile-error plan needs a precise F1/F2 dispatcher before code.

Self-Edit provides the closest execution-comment pattern for P feedback. Self-Edit executes generated code on examples and wraps execution results into a supplementary comment for a fault-aware editor ([Zhang et al., 2023](https://aclanthology.org/2023.acl-long.45/)). P follows that structure but changes the content to Triton compile repair: kernel source, compile stderr/error class, and a structured natural-language note. P rows should not include stdout/test-result comments unless they are part of the compile harness; Level 2 numerical feedback remains C-owned.

Failure-code taxonomy is also PENDING_DESIGN_DECISION. The safer default is to reuse canonical final failure codes (`shared/eval/failure_taxonomy.py:8-25`) and add P repair flags/traces, but new codes such as `F1_REPAIRED_BY_P` may help diagnostics. The analyzer must distinguish organic success from P-repaired success without changing the meaning of `compile_success` or `functional_success`.

## 4. Schema Additions

Cluster 3 rows should extend the Cluster 2 row shape only where P needs additional evidence. Cluster 2 rows already include condition, identity, compile and functional success, failure code, replay/generated metadata, and repair trace (`cluster2/results/dataclass.py:390-418`). Generated metadata already validates model/tokenizer revision, Modal image provenance, replay identity, prompt hash, temperature, and grammar fields (`cluster2/results/dataclass.py:298-329`; `cluster2/results/dataclass.py:1225-1307`).

Candidate Cluster 3 fields are DRAFT unless already present elsewhere:

- `p_repair_attempted: bool`
- `p_repair_succeeded: bool`
- `p_repair_budget: int` with draft range `3-5`
- `p_repair_attempt_count: int`
- `p_feedback_trace: list`
- `p_initial_failure_code`
- `p_final_failure_code`
- `p_compile_error_summary`
- `p_repair_stop_reason`
- `p_feedback_format`
- `p_history_policy`
- `p_compile_error_class`
- `p_raw_error_excerpt_sha256`

The analyzer should read these fields as optional P diagnostics. For non-P rows, missing P fields must normalize to inactive/default values without changing existing none/G/C/G+C semantics. For P rows, `p_repair_attempted` should be true only when an eligible F1 failure was encountered; `p_repair_succeeded` should be true only when a P repair changed the final compile outcome. `p_initial_failure_code` and `p_final_failure_code` should preserve before/after classification. `p_feedback_format` should distinguish structured diagnostics from raw logs, and `p_history_policy` should record the research-grounded default: conversational history across attempts, following Self-Refine's feedback-and-refine history pattern.

The registry should record the schema version, condition set, required P fields, scale tier, and provenance expectations for any Cluster 3 artifact. Existing registry rules already require future artifacts to update schema/registry/analyzer together and to persist `scale_tier` in future rows (`docs/05_artifacts_and_results_registry.md:208-215`; `docs/08_decision_log.md:229-239`). Scale tier is required in all future Cluster 3 rows because the scale policy rejects mixed or missing tiers for reportability (`.contracts/research/scale_policy.md:129-199`; `shared/analysis/factorial.py:1100-1190`).

Conflict handling should be strict. If row-level and sidecar metadata disagree on `scale_tier`, model revision, tokenizer revision, condition, seed identity, or replay identity, validation should fail before analysis. Provenance should inherit the shared generation metadata schema (`shared/generation_metadata.py:60-80`) and Cluster 2 generated paper-scale metadata gate (`cluster2/results/dataclass.py:1383-1447`).

## 5. Cluster 3 Module Structure

The existing `cluster3/` tree is a placeholder with a README that marks the contract TBD (`cluster3/README.md:1-3`; `cluster3/README.md:90-93`). The implementation should mirror Cluster 2 where the behavior is shared, and create new modules only for compile-error repair.

Proposed files:

- `cluster3/feedback/compile_error_repair.py`: new. Owns the P repair loop, F1 eligibility checks, budget handling, and stop reasons. It should borrow the bounded-loop pattern from Cluster 2 (`cluster2/feedback/repair_loop.py:159-246`) but must not reuse F2-only prompt rules.
- `cluster3/feedback/prompts.py`: new. Builds compile-error feedback prompts using the draft default of structured diagnostics plus bounded raw excerpt. Exact wording, redaction, and excerpt length are PENDING_DESIGN_DECISION.
- `cluster3/experiments/run_cluster3_modal.py`: new/adapted. Mirrors Cluster 2 runner configuration, durable writes, paired replay validation, and scale-tier checks (`cluster2/experiments/run_cluster2_modal.py:97-143`; `cluster2/experiments/run_cluster2_modal.py:455-464`).
- `cluster3/modal/correctness_runner.py`: adapted or shared reuse. PENDING_DESIGN_DECISION. It may wrap Cluster 2's correctness runner to preserve Level 0/1/2 behavior, or move common runner code into shared infrastructure.
- `cluster3/results/dataclass.py`: new if P fields require strict row validation. Otherwise adapted from Cluster 2 with a Cluster 3 schema version.
- `cluster3/results/logger.py`: reused or adapted. Cluster 2 already has durable JSONL appending with fsync and atomic sidecars (`cluster2/results/logger.py:76-87`; `cluster2/results/logger.py:449-476`).
- `cluster3/tests/`: new. Contains boundary, schema, replay, repair-loop, durable-write, analyzer-normalization, and scale-tier conflict tests.

Inherited/shared dependencies should be explicit: `shared/eval/`, `shared/eval/levels/`, `shared/modal_harness/`, `shared/generation_metadata.py`, and `cluster2/replay/` if replay controls can be reused without mutating frozen manifests. The Modal request schema already states that Cluster 1 generation must not feed compile errors back (`shared/modal_harness/schemas.py:1-9`), so Cluster 3 should introduce a separate P-aware request/runner contract rather than weakening Cluster 1.

## 6. Modal Integration

Cluster 3 should reuse `shared/modal_harness/` and the existing Cluster 1/2 model stack unless a new research contract changes it. Cluster 1's runner pins the default model to `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` and revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a` (`cluster1/experiments/run_cluster1_modal.py:72-85`). Cluster 2 validates immutable model and tokenizer revisions in its runner config (`cluster2/experiments/run_cluster2_modal.py:97-143`). Cluster 3 should use the same model revision and tokenizer revision for comparability.

Modal L4 should remain the smoke/development default unless a later scale review changes the hardware. No paper-scale Cluster 3 run should start until n=1 smoke, n=5 development, metadata validation, analyzer pairing, and an audit all pass. This follows the existing Cluster 3 drift-prevention gate: n=1 before n=5, audit before n=20, and no paper-scale until schema, analyzer, registry, and failure boundaries are stable (`docs/10_cluster3_drift_prevention_plan.md:168-182`).

Durable per-row JSONL writing is required. Cluster 2 uses `Cluster2JsonlAppendLogger(..., fsync=True)` before paper-scale appends (`cluster2/experiments/run_cluster2_modal.py:455-464`), and its logger fsyncs row and sidecar writes (`cluster2/results/logger.py:76-87`; `cluster2/results/logger.py:129-138`). Cluster 3 should match that behavior to avoid losing partial P runs.

Per-row provenance is required: `model_id`, `model_revision`, `tokenizer_revision`, package versions, Modal image provenance such as `modal_image_sha`, `scale_tier`, seed identity, `failure_code`, and repair trace metadata. Cluster 2 generated metadata already records model/tokenizer revisions, package and Modal image fields, replay identity, prompt hash, temperature, and grammar metadata (`cluster2/results/dataclass.py:298-329`). Cluster 3 should add P trace metadata without weakening these checks.

## 7. Test Suite Alignment

Cluster 3 tests should mirror Cluster 2's structure but assert P boundaries. Required categories:

- Boundary tests: P fires only on F1 failures, not F0 parse/signature failures and not F2 numerical failures. These should use synthetic outcomes matching the canonical failure taxonomy (`shared/eval/failure_taxonomy.py:8-25`).
- Repair budget tests: P loop terminates at the configured 3-5 iteration budget with a stable `p_repair_stop_reason`; smoke may run with budget one only as an execution shortcut.
- Schema validation tests: mock Cluster 3 rows validate condition, identity, P fields, final failure code, and provenance.
- Provenance tests: model id, model revision, tokenizer revision, Modal image provenance, package versions, scale tier, prompt hash, and seed identity are present.
- Replay tests: G+P pairs with G and G+C+P pairs with G+C using frozen context fields equivalent to Cluster 2's replay validation (`cluster2/experiments/run_cluster2_modal.py:1123-1168`).
- Failure-code taxonomy tests: F1 routes to P, F2 routes to C when C is active, F0/F3 remain terminal.
- Repair-loop tests: synthetic F1 compile-error fixtures trigger compile-error feedback and produce bounded attempts.
- Feedback-format tests: feedback includes structured diagnostic class, line/symbol references when available, bounded raw stderr excerpt, and full-error hash; feedback excludes numerical mismatch details, profiler metrics, task-specific tiling hints, and model-written patch suggestions.
- Durable-write tests: row append and sidecar writes survive interruption using the Cluster 2 logger pattern.
- Analyzer normalization tests: P rows normalize without changing current none/G/C/G+C rows.
- Scale-tier conflict tests: mismatched row/sidecar scale tiers fail analysis, matching existing analyzer behavior (`shared/analysis/factorial.py:1100-1190`).

Cluster 3 also needs an F1 analog of the F2 corrupted fixture smoke. Curate small kernels with known compile errors, such as invalid Triton symbols, wrong launch signatures, or type errors that fail before numerical comparison. P should attempt repair on those fixtures. If a fixture repair succeeds, the row must record `p_repair_attempted`, `p_repair_succeeded`, before/after failure codes, attempt count, and a feedback trace. These tests must pass before any Modal smoke.

Suggested future test names are `test_p_boundary_f1_only.py`, `test_p_repair_budget.py`, `test_p_feedback_format.py`, `test_cluster3_schema.py`, `test_cluster3_replay_pairing.py`, `test_cluster3_durable_writes.py`, and `test_cluster3_analyzer_normalization.py`. These names are DRAFT, but the separation matters: boundary tests should not depend on Modal, schema tests should not depend on model calls, and analyzer tests should use small local fixtures. Local parsing and validation commands should use `.venv/bin/python`, matching the execution rule for this repository.

## 8. Pre-Modal Verification Sequence

Pre-Modal verification should finish before any remote run is requested.

1. Run local fixture tests for synthetic F1 failures. These tests should verify that P sees F1_COMPILE and the selected F1_RUNTIME subset, while F0 and F2 remain outside P.
2. Validate a mock Cluster 3 row against the DRAFT schema, including P fields, generated metadata, `scale_tier`, model/tokenizer revisions, and Modal image provenance placeholders.
3. Add an analyzer fixture that accepts P-containing rows, preserves the existing 2^2 semantics, and reports missing cells rather than overstating full 2^3 coverage.
4. Validate manifest and registry behavior for any new Cluster 3 artifact entries. The registry currently treats P rows as future artifacts and requires schema/registry updates for additions (`docs/05_artifacts_and_results_registry.md:208-215`).
5. Validate provenance. The Cluster 3 row should include the same generation metadata and runtime provenance fields expected for Cluster 2 generated rows (`cluster2/results/dataclass.py:1225-1307`; `cluster2/results/dataclass.py:1383-1447`).
6. Run a hash gate if new frozen files are introduced. If Cluster 3 reuses `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, it must not re-record hashes.
7. Confirm local tests, schema checks, analyzer fixture checks, registry checks, and provenance checks are green.

No Modal smoke should start until the above sequence passes. This is an execution gate, not a documentation claim. The current task writes only this plan and the companion audit report.

The pre-Modal command sequence should be explicit once tests exist. A future implementation branch should provide commands equivalent to `.venv/bin/python -m pytest cluster3/tests`, `.venv/bin/python -m pytest shared/analysis/tests -k cluster3`, and a registry/schema validator invoked through `.venv/bin/python`. Exact module paths are PENDING_DESIGN_DECISION because the Cluster 3 test files do not exist yet, but system Python should not be used for these checks.

## 9. Modal Run Sequence

n=1 smoke should run one minimal P-containing condition first, then the remaining P-containing conditions only if metadata and repair routing are correct. Conditions: P, then G+P, C+P, and G+C+P as needed. Expected outputs: one durable JSONL row per condition, sidecar metadata, P trace fields when an eligible F1 occurs, and analyzer fixture compatibility. Validation commands should include row schema validation, scale-tier validation, analyzer dry run, and artifact registry check. Cost/wall-clock: ESTIMATE, one L4 smoke batch should be small, likely minutes and low single-digit dollars depending on queue and retries.

n=5 development scale should run all four P-containing conditions with matched seeds against existing no-P controls. The draft P budget range is 3-5 repair attempts, with early stop on compile success, F0/F3 terminal failure, or budget exhaustion. Expected outputs: durable Cluster 3 JSONL artifacts, sidecars, P trace diagnostics, and pairing keys for P vs none, G+P vs G, C+P vs C, and G+C+P vs G+C. Validation commands should check row counts, scale tier, seed pairing, condition labels, P trace presence, feedback-format compliance, no artifact overwrite, and analyzer normalization. Cost/wall-clock: ESTIMATE, target roughly the same order as earlier development runs, but repair retries can multiply runtime. Verify that eligible F1 candidates exist and P actually fires before continuing.

n=20 paper/preliminary scale should be deferred to paper revision unless n=1, n=5, audit, schema, analyzer, registry, and provenance gates pass. Conditions: all four P-containing cells, preserving matched identity with current controls or regenerated approved controls if a later contract requires it. Expected outputs: paper-scale Cluster 3 artifacts and updated analyzer/report outputs. Cost/wall-clock: ESTIMATE, substantially higher than n=5 due to four conditions and repair retries.

June 8 target: development-scale P-containing cells if the timeline is tight. Paper-scale P should remain a paper-revision target unless all gates are satisfied early.

The future validation command set should be recorded with each run plan before launch. For n=1, require commands that validate one row end to end: JSONL parse, schema validation, P trace validation, scale-tier check, and analyzer dry run. For n=5, require the same checks plus paired-key completeness and condition coverage for all four P-containing cells. For n=20, require all n=5 checks plus registry update review, audit report generation, and a reportability check that confirms all eight factorial cells are present before any full 2^3 analysis language is used. All local commands should use `.venv/bin/python`; Modal commands remain prohibited until the pre-Modal gate is green and explicitly approved by the future run plan.

## 10. Analyzer Updates

The analyzer must recognize P, G+P, C+P, and G+C+P while preserving current none/G/C/G+C semantics. The shared analyzer already has canonical labels and factor expansion for P-containing conditions (`shared/analysis/factorial.py:46-59`; `shared/analysis/factorial.py:1064-1081`), but current documentation says the reportable scope is the covered 2^2 subset until P artifacts exist (`docs/07_analysis_and_statistics.md:9-18`; `docs/05_artifacts_and_results_registry.md:168-174`).

Required paired P comparisons:

- P vs none
- G+P vs G
- C+P vs C
- G+C+P vs G+C

These extend the current paired comparison rules without removing existing comparisons (`docs/07_analysis_and_statistics.md:92-111`). Pairing should use kernel, dtype, and seed identity, and should fail closed when replay metadata conflicts.

The additive 3-way interaction should be:

`(rate_GCP - rate_GC) - (rate_GP - rate_G) - (rate_CP - rate_C) + (rate_P - rate_none)`

If model fit is stable, the logistic model can include the 3-way coefficient `G:C:P`. The analyzer already reserves a full eight-cell factorial formula with `G`, `C`, `P`, pairwise interactions, and `G:C:P`, but it marks partial P coverage as not full 2^3 reportable (`shared/analysis/factorial.py:1810-1863`; `shared/analysis/factorial.py:2260-2305`). Cluster 3 work should turn that reserved path into tested behavior for actual P rows.

The analyzer must handle heterogeneous schema across Cluster 1 rows for none/G, Cluster 2 rows for C/G+C, and Cluster 3 rows for P-containing conditions. It should surface P repair trace diagnostics separately from primary success rates so repaired-vs-organic success can be audited. It must not reinterpret C repair traces as P traces or infer P activity from condition labels alone when row fields disagree.

Normalization should be conservative. A P-labeled row with missing P trace fields should be accepted only if the condition has no eligible F1 event and the schema explicitly allows no-attempt rows. A non-P row with populated P trace fields should be rejected or quarantined as a schema conflict. Current 2^2 analyzer outputs should remain reproducible when Cluster 3 rows are absent.

## 11. Scale and Budget Plan

June 8 target: n=5 development-scale for the four P-containing conditions. This gives a small but useful integration check for P, G+P, C+P, and G+C+P while avoiding a premature paper-scale claim. It should be treated as development-scale evidence only. Cost: ESTIMATE, approximately low tens of dollars if the 3-5 iteration budget is retained and L4 availability is normal; exact cost depends on repair iterations, queue time, and failure rate.

Paper revision target: n=20 paper-scale for all P-containing conditions after the P contract, schema, analyzer, registry, and audit gates are stable. Cost: ESTIMATE, higher than the existing four-cell study because each P cell may require multiple compile attempts. The earlier handoff estimate of roughly $60-80 for P paper-scale should remain a placeholder until observed n=5 runtime and retry counts are measured.

Decision gates:

- If n=5 has no eligible F1 candidates or P does not fire, reassess the fixture design, sample selection, or whether compile-error repair can be evaluated on the current benchmark slice.
- If metadata fails, stop. Do not proceed to broader runs until row and sidecar provenance match the required model, tokenizer, Modal image, scale tier, and seed identity.
- If the analyzer cannot pair P rows against no-P controls, stop. Analysis without valid pairing would break the factorial methodology.
- If P repair traces cannot distinguish organic success from repaired success, stop before report integration.
- If feedback-format checks show task-specific hints, model-written patch suggestions, numerical mismatch details, or profiler/performance information, stop and revise the P contract.
- If F1_RUNTIME cannot be separated cleanly from F2 behavior, defer that subset and keep first P scope to F1_COMPILE.

The cost-benefit boundary is simple: n=5 is for implementation confidence and presentation readiness; n=20 is for paper-facing estimates only after reportability gates pass.

## 12. Risks and Unknowns

Feedback format is a design decision: structured compile-error feedback following Self-Debug's rubber-duck pattern, adapted for Triton. The row should preserve kernel source, compile error message, compiler diagnostic class, and a structured natural-language note that explains the failure without proposing a patch. This follows Chen et al. (2023), where Self-Debug uses execution results plus natural-language explanation as the debugging signal. The risk is over-informing the repair loop: feedback must not include task-specific tiling hints, profiler observations, numerical mismatch details, or performance advice.

Iteration budget is a design decision: P should use 3-5 repair iterations with early stop on compile success, F0/F3 terminal failure, or budget exhaustion. This matches the small fixed iteration regime used by Self-Refine and the empirical plateau described in the supplied research synthesis for Madaan et al. (2023). The risk is cost inflation and prompt drift if the upper budget is used broadly; n=1 smoke may still use a one-attempt execution shortcut, but development and paper-scale plans should record the configured P budget in every row.

Memory is a design decision: P should use conversational history across attempts, following Self-Refine's pattern of conditioning refinement on the original prompt, prior outputs, and prior feedback (Madaan et al., 2023). For Triton, that history should be structured and bounded: previous kernel attempt identifiers, previous compile-error summaries, and previous stop reasons may persist, while long raw logs should be stored by hash or artifact reference. The risk is context growth; the mitigation is a fixed history budget and deterministic truncation.

Compile-error summarization is a design decision: use deterministic structured diagnostics plus bounded raw excerpt and full-error hash. The parser, redaction rules, and excerpt budget still need implementation review, but the research direction is fixed by the structured execution-feedback pattern from Self-Debug and Self-Edit. Self-Edit's execution-comment pattern is especially relevant because it wraps observed execution results into a supplementary comment for editing; P uses the same shape with Triton compile errors instead of example test outputs.

P/C composition is a design decision: dispatch by failure code, with no unified repair loop. F1 routes to P; F2 routes to C; F0/F3 terminate. PGS motivates this specialization: property-oriented, structurally minimal feedback is more targeted than general critique, so compile feedback and correctness feedback should remain separate loops. The risk is orchestration complexity when a P repair reaches Level 2 and then fails numerically; the mitigation is explicit dispatcher trace metadata showing which loop fired and why.

Implementation risks include Modal image rebuild churn if shared harness changes, schema drift if Cluster 3 fields are added without analyzer updates, replay manifest churn if new frozen controls are introduced, and mixed `scale_tier` conflicts across row and sidecar metadata. Existing scale-tier policy explicitly requires future artifacts to serialize scale tier and treats conflicts as reportability blockers (`.contracts/research/scale_policy.md:181-199`).

Methodology risks include P feedback becoming too informative and blurring into task-specific repair, F1_RUNTIME vs F2 boundary ambiguity, and interference between P and C when both are active. Cluster 3 should also avoid importing the older performance/profiler ambitions from `cluster3/README.md` into this compile-error plan without a separate research contract (`cluster3/README.md:13-19`).

The GPU-kernel research synthesis also warns that compile-error repair can rescue kernels while degrading hardware efficiency. For this Cluster 3 plan, that risk is handled by keeping P scoped to compile repair and recording repaired-vs-organic status. P should not report speed or fast-p style metrics in the June 8 plan. Any later profiler-aware factor should be a separate contract because it would observe different signals and require Level 4 methodology.

## 13. Open Research Questions

What compiler feedback format improves LLM repair success for Triton compile errors? Research-grounded answer: structured compile-error feedback following Self-Debug, adapted for Triton as kernel source plus compile error message plus structured natural-language note. PENDING_DESIGN_DECISION: exact template. PENDING_RESEARCH: local ablation.

Should P see full error traces, structured summaries, error classes only, or repair suggestions? Research-informed draft answer: structured summaries with diagnostic class, line/symbol references when available, bounded raw excerpt, and full-error hash. It should not see repair suggestions.

What iteration budget is optimal for compile-error repair under the study's cost and reportability constraints? Research-grounded answer: 3-5 iterations with early stop, following the small fixed-budget Self-Refine pattern. PENDING_RESEARCH: confirm budget choice with local F1 fixtures before paper-scale use.

Should each repair iteration see only the latest failed attempt, or the full attempt history? Research-grounded answer: conversational history across attempts, following Self-Refine, with deterministic truncation for long raw logs.

How should compile-error summaries be produced so they are faithful, reproducible, and not overly task-specific? Research-informed draft answer: deterministic structured diagnostics plus bounded raw excerpt and full-error hash. PENDING_DESIGN_DECISION: parser and redaction rules. PENDING_RESEARCH: local ablation.

Does P compose additively with C or interfere with C's F2 repair behavior? PENDING_RESEARCH.

Should P operate before C through a sequential ladder, or should a unified loop route both mechanisms? Research-grounded answer: dispatch by failure code, with no unified repair loop. F1 routes to P; F2 routes to C. PENDING_DESIGN_DECISION: exact dispatcher implementation boundary.

Should P include F1_RUNTIME in the first version, or should first scope be restricted to F1_COMPILE? PENDING_RESEARCH and PENDING_DESIGN_DECISION.

How should repaired-vs-organic success be analyzed? PENDING_RESEARCH. The implementation can expose trace flags, but the final primary/secondary reporting convention should be chosen after statistical and methodology review.

Should P diagnostics be part of primary paper tables, appendices, or audit-only artifacts? PENDING_RESEARCH.

## 14. Timeline for June 8

Day 0, May 22: finalize this plan draft, confirm that no code or artifacts changed, and circulate the P definition gate. Critical path: P definition first.

Day 1: research review for compile-error feedback formats, iteration budgets, and history policies. Output should be a short decision memo with PENDING_RESEARCH items either resolved or explicitly deferred.

Day 2: finalize P contract: eligible failure codes, feedback content, budget, stop reasons, and repaired-vs-organic success fields. Critical path: schema/analyzer before runs.

Day 3: design Cluster 3 schema and analyzer fixture contract. Confirm `scale_tier`, provenance, pairing identity, and P trace fields.

Day 4: create local F1 fixtures and boundary-test design. No Modal. Verify the fixture set covers F1_COMPILE and excluded F0/F2 cases.

Day 5: implement local fixtures and schema/analyzer tests in the future Cluster 3 branch. This plan does not perform that work.

Day 6: run local test sequence and fix schema/analyzer issues. Gate: no Modal until local tests pass.

Day 7: prepare n=1 smoke manifest and registry entries, then audit metadata expectations.

Day 8: run Modal n=1 smoke only if all gates pass. Verify durable JSONL, sidecar, P trace, and no artifact overwrite.

Day 9: audit n=1 outputs. Stop if metadata, pairing, failure routing, or analyzer normalization fails.

Day 10-11: run n=5 development scale for P, G+P, C+P, and G+C+P if n=1 passes.

Day 12: validate n=5 row counts, P firing behavior, schema, scale tier, pairing, and analyzer output.

Day 13: write development-scale audit and decide whether June 8 presentation can include P development evidence or only the implementation plan.

Day 14-15: integrate presentation language. Avoid paper-scale claims unless paper-scale gates are actually complete later.

Day 16: dry-run presentation tables and caveats.

Day 17, June 8: present current 2^2 results plus Cluster 3 plan or development-scale status, clearly separating draft/planning, development-scale, and paper-revision targets.
