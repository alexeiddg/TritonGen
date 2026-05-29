# Cluster 3 Implementation Plan Draft Report

> **SUPERSESSION NOTICE (2026-05-22, post-review revision).**
> §5 of this report ("PENDING_DESIGN_DECISION items") lists six items as
> open. Those items are **resolved** in the Part A Addendum below
> (§A2.1–§A2.6) and further refined in the Post-Review Revision section
> (§B1–§B7) that addresses integration findings against the current Modal
> harness, generation surface, repair loop, sanitizer, analyzer, and Modal
> entrypoint. **The implementation specification at
> [docs/cluster3_implementation_specification.md](docs/cluster3_implementation_specification.md)
> reflects the Post-Review Revision and is the single source of truth for
> implementers.** Where this report and the specification disagree, the
> specification wins. The original §5 is preserved for audit traceability
> only.

## 1. Inputs read.

Read the required methodology, registry, taxonomy, analysis, decision log, preliminary report outline, and Cluster 3 drift-prevention documents:

- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `docs/10_cluster3_drift_prevention_plan.md`

Read current research contracts:

- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`

Read current documentation hub files:

- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/code_update_documentation_policy.md`

Read current audits:

- `audits/c1_c2_evaluation_surface_audit.md`
- `audits/final_documentation_consistency_audit.md`
- `audits/cross_pipeline_reportability_alignment_audit.md`
- `audits/scale_tier_docs_contract_alignment_fix_report.md`

Inspected required Cluster 1, Cluster 2, shared, and Cluster 3 surfaces using the mandated search set and targeted line-number reads.

Also incorporated the user-supplied research synthesis on iterative self-repair, automated program repair, GPU kernel generation, grammar-constrained decoding, and paired statistical methodology. Primary paper pages were checked for Self-Debug, Self-Refine, Self-Edit, Repilot, and PGS. The synthesis was used to convert feedback format, iteration budget, memory, and P/C composition from open research placeholders into research-grounded design decisions.

## 2. Plan path.

`docs/cluster3_implementation_plan_draft.md`

## 3. Sections completed.

Completed all required sections:

- 0. Executive Summary
- 1. Factor Definition
- 2. Composition With Existing Factors
- 3. Eval Pipeline Alignment With Cluster 2
- 4. Schema Additions
- 5. Cluster 3 Module Structure
- 6. Modal Integration
- 7. Test Suite Alignment
- 8. Pre-Modal Verification Sequence
- 9. Modal Run Sequence
- 10. Analyzer Updates
- 11. Scale and Budget Plan
- 12. Risks and Unknowns
- 13. Open Research Questions
- 14. Timeline for June 8

## 4. PENDING_RESEARCH items.

- Local fixture ablation for structured compile-error feedback.
- Confirmation of the exact 3-5 iteration budget for Triton F1 failures.
- Whether P and C compose additively or interfere empirically.
- Whether F1_RUNTIME should be included in the first P scope.
- How repaired-vs-organic success should be analyzed.
- Whether P diagnostics belong in primary tables, appendices, or audit-only material.

## 5. PENDING_DESIGN_DECISION items.

- Whether P includes F1_RUNTIME or starts with F1_COMPILE only.
- Exact implementation boundary for the failure-code dispatcher.
- Whether failure taxonomy reuses existing final codes with P flags or adds P-specific repaired codes.
- Whether `cluster3/modal/correctness_runner.py` wraps Cluster 2 or shared runner logic.
- Whether Cluster 3 result dataclass/logger are new copies or strict adaptations of Cluster 2.
- Exact P feedback prompt template, raw excerpt length, and diagnostic redaction policy.

## 6. Code paths cited.

The plan cites Cluster 1, Cluster 2, shared, and Cluster 3 paths including:

- `cluster1/experiments/run_cluster1_modal.py`
- `cluster1/results/dataclass.py`
- `cluster1/validation/compile_check.py`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/feedback/prompts.py`
- `cluster2/feedback/repair_loop.py`
- `cluster2/modal/correctness_runner.py`
- `cluster2/results/dataclass.py`
- `cluster2/results/logger.py`
- `cluster3/README.md`
- `shared/analysis/factorial.py`
- `shared/eval/failure_taxonomy.py`
- `shared/eval/levels/level0_parse.py`
- `shared/eval/levels/level1_compile.py`
- `shared/eval/levels/level2_correctness.py`
- `shared/factors/registry.py`
- `shared/generation_metadata.py`
- `shared/modal_harness/schemas.py`

The plan also cites primary research sources:

- Chen et al. 2023, Self-Debug.
- Madaan et al. 2023, Self-Refine.
- Zhang et al. 2023, Self-Edit.
- Wei, Xia, and Zhang 2023, Repilot.
- He et al. 2025, PGS. Final bibliography should align the citation key if project notes refer to this result as Wang et al. 2025.

## 7. Files created/updated.

Created:

- `docs/cluster3_implementation_plan_draft.md`
- `audits/cluster3_implementation_plan_draft_report.md`

No source code, artifacts, analyzer outputs, grammar files, or hashes were intentionally modified.

## 8. Forbidden claims avoided.

The draft avoids claiming P empirical outcomes, Cluster 3 empirical outcomes, full 2^3 completion, paper-scale completion, Modal completion, performance outcomes, or speedup outcomes. It states only draft/planning status, research-grounded design decisions, remaining design gates, and future validation gates.

## 9. Classification.

DRAFT_COMPLETE

## 10. Next recommendation.

Resolve the remaining PENDING_DESIGN_DECISION items in a short design memo before opening any implementation PR. The first implementation gate should be schema and analyzer fixtures, followed by local synthetic F1 tests before any Modal smoke.

---

## Part A Addendum: Plan Audit and Design-Decision Resolution

This addendum is the Part A audit of `docs/cluster3_implementation_plan_draft.md` performed on 2026-05-22. It verifies cited code paths against the current state of the repository and resolves the six remaining PENDING_DESIGN_DECISION markers using existing Cluster 2 patterns where possible. Its outcome feeds the Part B implementation specification at `docs/cluster3_implementation_specification.md`.

### A1. Citation verification

Each path cited in the draft was opened and the cited line range inspected.

- `shared/eval/failure_taxonomy.py:8-25` — verified: `FAILURE_CODES` set contains the F0/F1/F2/F3 codes the draft names ([failure_taxonomy.py:8](shared/eval/failure_taxonomy.py:8)).
- `shared/eval/levels/level0_parse.py:11-55` — verified: `check_parse` and `check_signature` are AST-only Level 0 functions ([level0_parse.py:11](shared/eval/levels/level0_parse.py:11)).
- `shared/eval/levels/level1_compile.py:1-61` — verified: `Level1CompileResult` and `check_compile_level1` form the shared Level 1 gate ([level1_compile.py:36](shared/eval/levels/level1_compile.py:36)).
- `cluster1/experiments/run_cluster1_modal.py:1-12` — verified: header explicitly states "this runner records compile errors as result fields, never as control signals" ([run_cluster1_modal.py:8](cluster1/experiments/run_cluster1_modal.py:8)).
- `cluster1/experiments/run_cluster1_modal.py:72-85` — verified: `DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"` and `DEFAULT_MODEL_REVISION = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"` ([run_cluster1_modal.py:72](cluster1/experiments/run_cluster1_modal.py:72)).
- `cluster2/feedback/prompts.py:17-23` — verified: `ALLOWED_CORRECTNESS_FEEDBACK_FAILURE_CODES` is F2-only ([prompts.py:17](cluster2/feedback/prompts.py:17)).
- `cluster2/feedback/prompts.py:25-48` — verified: `FORBIDDEN_FEEDBACK_TERMS` includes `speedup`, `profil`, `timing`, `performance`, `LLVM`, `PTX`, `eval_shape_set` etc. ([prompts.py:25](cluster2/feedback/prompts.py:25)).
- `cluster2/feedback/prompts.py:50-57` — verified: deterministic six-section `_SECTION_ORDER` ([prompts.py:50](cluster2/feedback/prompts.py:50)).
- `cluster2/feedback/prompts.py:302-317` — verified: `feedback_allowed_for_failure_code` and `require_correctness_feedback_failure_code` reject non-F2 codes.
- `cluster2/feedback/repair_loop.py:125-143` — verified: `run_repair_loop` accepts only `C` / `G+C` via `require_generated_condition`, with `DEFAULT_REPAIR_BUDGET = 5` enforced ([repair_loop.py:138-143](cluster2/feedback/repair_loop.py:138)).
- `cluster2/feedback/repair_loop.py:366-369` — verified: `_must_terminate_without_feedback` returns True when `level_reached < 2` or the failure code is not in the C-allowed set.
- `cluster2/modal/correctness_runner.py:70-150` — verified: `run_correctness_payload` runs Level 0 parse, Level 0 signature, Level 1 compile, then Level 2 correctness ([correctness_runner.py:70](cluster2/modal/correctness_runner.py:70)).
- `cluster2/modal/correctness_runner.py:208-233` — verified: `_evaluate_generated_level1_gate` returns an F1 result with `compile_success=False` and terminates Level 2 ([correctness_runner.py:208](cluster2/modal/correctness_runner.py:208)).
- `cluster2/experiments/run_cluster2_modal.py:97-143` — verified: `Cluster2RunnerConfig` enforces immutable model and tokenizer revisions for generated conditions.
- `cluster2/experiments/run_cluster2_modal.py:455-464` — verified: runner instantiates `Cluster2JsonlAppendLogger(..., fsync=True)` ([run_cluster2_modal.py:455](cluster2/experiments/run_cluster2_modal.py:455)).
- `cluster2/experiments/run_cluster2_modal.py:1061-1168` — verified: `_paired_replay_control_condition` at line 1061 and `_validate_generation_pairing_context` at line 1123 enforce paired identity across kernel, dtype, seeds, prompt, model revisions, and temperature.
- `cluster2/results/dataclass.py:44` — verified: `CLUSTER2_RESULTS_SCHEMA_VERSION = 1` (the draft claims this implicitly via "Cluster 3 schema version" framing).
- `cluster2/results/dataclass.py:298-329` — verified: `Cluster2GeneratedRowMetadata` captures model/tokenizer revision, Modal image provenance, replay identity, prompt hash, temperature, grammar metadata.
- `cluster2/results/dataclass.py:390-418` — verified: `Cluster2EvalRow` with `condition`, `source_class`, `generation_mode`, `attempt_index`, kernel identity, `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, `failure_code`, `repair_trace`.
- `cluster2/results/logger.py:76-87` — verified: `Cluster2JsonlAppendLogger.__init__` signature with `fsync: bool = True`.
- `cluster2/results/logger.py:129-138` — verified: `open()` writes and fsyncs the empty output and atomic sidecar.
- `cluster2/results/logger.py:449-476` — verified: `_write_sidecar_atomic` performs tempfile write + replace + directory fsync.
- `shared/factors/registry.py:17-21` — verified: `_CLUSTER_ALLOWED_CELLS["cluster3"] = ("P", "G+P", "C+P", "G+C+P")` ([registry.py:17](shared/factors/registry.py:17)).
- `shared/analysis/factorial.py:46-59` — verified: `CANONICAL_CONDITIONS` includes P, `P_CONDITIONS = ("P", "G+P", "C+P", "G+C+P")`, `FACTOR_NAMES = ("G", "C", "P")`.
- `shared/analysis/factorial.py:1810-1863` — verified: the reserved factorial-model formula `... ~ G + C + P + G:C + G:P + C:P + G:C:P ...` exists for the partial-eight-cell case ([factorial.py:1828](shared/analysis/factorial.py:1828)).
- `shared/analysis/factorial.py:2260-2305` — verified: scope-kind branch `partial_factorial` warns when P-cell coverage is partial ([factorial.py:2283](shared/analysis/factorial.py:2283)).
- `shared/modal_harness/schemas.py:1-9` — verified: header states "Cluster 1 must never feed compile errors back to generation" and reserves the `C` / `P` factor cells for the validator to reject.
- `cluster3/README.md:1-3`, `:13-19`, `:44-62`, `:90-93` — verified: status "NOT STARTED - contract TBD", scope mentions "compiler/profiler repair", factorial-conditions table for P-containing cells, contract TBD.
- `docs/03_methodology_cluster2.md:87-102` — verified: section "7. C repair policy" states C repair fires only on F2 and F0/F1 failures terminate without repair feedback.
- `docs/05_artifacts_and_results_registry.md:11-20`, `:168-174`, `:208-215` — verified: registry treats P rows as future artifacts and requires schema/registry/analyzer co-updates.
- `docs/06_failure_taxonomy_and_eval_ladder.md:21-46` — verified: Evaluation Ladder table and F0/F1/F2/F3 family table both present.
- `docs/07_analysis_and_statistics.md:9-18`, `:92-111` — verified: reportable scope is the covered 2^2 subset; paired comparison rules.
- `docs/10_cluster3_drift_prevention_plan.md:168-182` — verified: drift-prevention gate language is consistent with the plan's scale-policy paraphrase.
- `cluster2/constants.py` — `DEFAULT_REPAIR_BUDGET = 5` (cited indirectly by the plan).

No citation in the draft was found to be inaccurate. The draft's claim that the Cluster 3 README's older "compiler/profiler" scope conflicts with the compile-error-only scope of this Cluster 3 plan is corroborated by `cluster3/README.md:13-19` (scope mentions profiler/speedup) and `cluster3/README.md:65-73` (profiler/speedup metrics listed as in-scope). The implementation specification narrows P to compile-error feedback only and defers profiler/speedup to a separate future contract.

### A2. Resolved PENDING_DESIGN_DECISION items

The six PENDING_DESIGN_DECISION items in the Part A summary above are resolved as follows. Each resolution traces to a Cluster 2 pattern (path) or a cited research source.

**A2.1 F1_RUNTIME inclusion in first P scope.**
- Decision: **first P version observes F1_COMPILE only; F1_RUNTIME is excluded from initial scope** but reserved as a future expansion item.
- Rationale: `shared/eval/failure_taxonomy.py:90-94` classifies F1_RUNTIME from a substring match on `"runtime"` in `compile_error`. The boundary is implementation-dependent and may overlap with kernel launch behavior that borders Level 2 numerical correctness. `cluster2/modal/correctness_runner.py:282` defaults the Level 1 failure code to `F1_COMPILE` when the canonical map returns `None`, so F1_COMPILE is the cleaner first-version anchor. Adding F1_RUNTIME later requires only flipping a constant set in the dispatcher.
- Consequence: the dispatcher's `is_p_eligible(failure_code)` returns True only for `"F1_COMPILE"` in v1.

**A2.2 Dispatcher module boundary.**
- Decision: **new module `cluster3/feedback/dispatcher.py`**. Not in `shared/`, not in `cluster2/`.
- Rationale: The dispatcher embodies P-aware routing logic. Putting it in `shared/` would force every cluster's eval surface to import P semantics. Putting it in `cluster2/` would mutate the surface that produced the reportable 2^2 paper-scale artifacts. `cluster3/feedback/dispatcher.py` follows Cluster 2's per-cluster feedback module convention (`cluster2/feedback/{prompts,repair_loop,trace}.py`). The dispatcher consumes a Cluster 2 `_PublicEvaluationResult`-shaped object (`cluster2/feedback/repair_loop.py:312-323`) and decides:
  - F0_* → terminate
  - F1_COMPILE → invoke `cluster3.feedback.compile_error_repair.run_p_loop`
  - F1_RUNTIME → terminate (v1 scope)
  - F2_* → if condition contains C, invoke `cluster2.feedback.repair_loop.run_repair_loop`; else terminate
  - F3_* → terminate
- Consequence: Cluster 2 source remains read-only by Cluster 3.

**A2.3 Failure-code taxonomy: new codes vs flags.**
- Decision: **reuse the existing canonical codes; add P-specific row flags and trace fields**.
- Rationale: `shared/eval/failure_taxonomy.py:8-25` is the canonical registry, and `cluster2/results/dataclass.py:459-460` rejects any non-canonical code. Adding `F1_REPAIRED_BY_P` would require updating the validator, every Cluster 2 paper-scale row's allowed-codes set, and the analyzer's condition rate logic. Cluster 2 already distinguishes organic vs repaired via `repair_trace` ([dataclass.py:418](cluster2/results/dataclass.py:418)) without adding new codes. P mirrors that pattern: the final row's `failure_code` is `None` for success or the unchanged terminal F-code on exhaust, while `p_repair_trace` and `p_repair_succeeded` carry the repair narrative.
- Consequence: no edits required to `shared/eval/failure_taxonomy.py`; no Cluster 2 artifact is invalidated.

**A2.4 `cluster3/modal/correctness_runner.py` ownership.**
- Decision: **thin adapter that delegates to `cluster2.modal.correctness_runner.run_correctness_payload`**.
- Rationale: `cluster2/modal/correctness_runner.py:70-150` already runs the full Level 0 / Level 1 / Level 2 ladder, returns canonical failure codes, and serializes the durable result payload. Reimplementing the ladder in Cluster 3 risks schema drift between the two correctness payloads and would invalidate the analyzer's heterogeneous-row normalization. The Cluster 3 adapter:
  - Accepts a Cluster 3 identity (which has the same eval-relevant fields as `EvalIdentity`),
  - Calls Cluster 2's payload runner,
  - Returns the same wire-shape result.
- Consequence: Cluster 3 inherits Level 0/1/2 behavior automatically. Only the P repair orchestration is new.

**A2.5 Cluster 3 dataclass and logger: new copies vs adaptations.**
- Decision: **new `Cluster3EvalRow` dataclass and new `Cluster3JsonlAppendLogger`**, both modeled on Cluster 2 patterns. Cluster 3 declares its own schema version.
- Rationale: `cluster2/results/dataclass.py:649-659` validates `schema_version == CLUSTER2_RESULTS_SCHEMA_VERSION = 1`. Adding optional P fields to Cluster 2's row would either force a Cluster 2 schema-version bump (invalidating existing n=20 paper-scale Cluster 2 artifacts) or require sentinel defaults that complicate the validator. A separate Cluster 3 dataclass keeps Cluster 2 artifacts immutable, and the logger fork reuses the durable JSONL fsync pattern from `cluster2/results/logger.py:76-87` and the atomic sidecar pattern from `:449-476`.
- Consequence: `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` is its own constant. Cluster 3 rows are loaded by the analyzer through a new normalization path that maps Cluster 3 fields onto the same shape the analyzer already accepts for Cluster 2 rows, with the P fields preserved as additional columns.

**A2.6 P feedback prompt template, raw excerpt length, diagnostic redaction.**
- Decision: **six-section deterministic template** mirroring `cluster2/feedback/prompts.py:50-57`, plus a Compile error section; **2000-character cap** on the redacted compile-error excerpt; **deterministic template-built diagnostic note** (not model-generated).
- Section order:
  1. `Base task:` original prompt verbatim
  2. `Previous source:` full candidate source (no length cap, mirrors Cluster 2 behavior)
  3. `Failure code:` e.g. `F1_COMPILE`
  4. `Feedback:` short natural-language note from the deterministic template lookup
  5. `Compile error:` redacted compile error excerpt, capped at 2000 characters (head-keep, tail-truncate)
  6. `Instruction:` `"Produce a corrected complete Triton Python module."`
- Excerpt cap rationale: Cluster 2 uses `MAX_PUBLIC_DETAIL_CHARS = 200` for short numerical-summary text (`cluster2/feedback/prompts.py:15`). Triton compile errors carry multi-line traces (source line, error class, kernel decorator path). 2000 characters (~500 tokens) preserves the top of the diagnostic while staying comfortably inside `DEFAULT_MAX_NEW_TOKENS = 1536` (`cluster2/constants.py:37`). The full pre-truncation error is stored by sha256 in `p_raw_error_excerpt_sha256` for audit. [Inline-corrected per §C10 from the earlier draft value of 1024.]
- Redaction rationale: reuse Cluster 2's `FORBIDDEN_FEEDBACK_TERMS` (`cluster2/feedback/prompts.py:25-48`) with two exceptions — `LLVM` and `PTX` are **allowed** in P because Triton compile errors legitimately reference those backends in stack frames. All other forbidden terms (`speedup`, `fast@`, `nsight`, `ncu`, `nvml`, `compute-sanitizer`, `profil`, `timing`, `performance`, `token`, `benchmark`, `RL`, `GRPO`, `TRL`, `C++ traceback`, `eval_shape_set`, `hidden`, `private`, `edge cases`, `extra shapes`) remain in the P forbidden list.
- Diagnostic note rationale: Cluster 2 builds `_FAILURE_FEEDBACK` text deterministically from a failure-code lookup table (`cluster2/feedback/prompts.py:59-72`). The P diagnostic note follows the same pattern: a pure function `build_compile_diagnostic_note(failure_code, compile_error_type, compile_error)` returns a one-sentence human description of the failure class without proposing a code patch. This satisfies Self-Debug's rubber-duck pattern ([Chen et al., 2023](https://arxiv.org/abs/2304.05128)) while remaining reproducible and audit-friendly.

### A3. Schema field final names

The DRAFT field list from `docs/cluster3_implementation_plan_draft.md` section 4 is finalized as:

| Field | Type | Required | Notes |
|---|---|---|---|
| `p_repair_attempted` | `bool` | yes | True only when an eligible F1_COMPILE was encountered. |
| `p_repair_succeeded` | `bool` | yes | True only when a P repair changed the row's terminal compile outcome. |
| `p_repair_budget` | `int` | yes | 0..5; matches `DEFAULT_REPAIR_BUDGET` upper bound. |
| `p_repair_attempt_count` | `int` | yes | Number of P attempts actually executed (excludes the original candidate). |
| `p_initial_failure_code` | `str \| None` | when attempted | Failure code at first Level 1 failure. |
| `p_final_failure_code` | `str \| None` | when attempted | Final failure code; None if `p_repair_succeeded`. |
| `p_compile_error_class` | `str \| None` | when attempted | Mirrors `Level1CompileResult.compile_error_type`. |
| `p_raw_error_excerpt_sha256` | `str \| None` | when attempted | SHA256 of the FULL pre-truncation initial compile error. |
| `p_repair_stop_reason` | `str \| None` | when attempted | One of `{compile_success, budget_exhausted, f0_terminal, f3_terminal, unrecoverable_runtime, none}`. |
| `p_feedback_format` | `str` | yes | Constant `"structured_compile_v1"` for v1. |
| `p_history_policy` | `str` | yes | Constant `"conversational_history_v1"` for v1. |
| `p_repair_trace` | `tuple[PRepairAttemptSummary, ...] \| None` | when attempted | Per-attempt trace mirroring Cluster 2's `repair_trace`. |

### A4. Cluster 3 schema version

`CLUSTER3_RESULTS_SCHEMA_VERSION = 1`, declared in the new `cluster3/results/dataclass.py`, independent of Cluster 2's `CLUSTER2_RESULTS_SCHEMA_VERSION = 1` ([dataclass.py:44](cluster2/results/dataclass.py:44)).

### A5. Audit classification

PLAN_AUDIT_VERIFIED_AND_RESOLVED.

- All cited file paths exist with the cited line ranges containing the claimed content.
- All six PENDING_DESIGN_DECISION items are resolved to concrete choices, each grounded in either a Cluster 2 pattern (cited by path) or a research source already cited in the draft.
- The remaining PENDING_RESEARCH items (feedback format ablation, iteration-budget ablation, P/C empirical interaction, F1_RUNTIME later inclusion, repaired-vs-organic reporting convention) are kept as PENDING_RESEARCH because they require empirical evidence the planning pass cannot generate. They are scheduled in the implementation specification's Phase 1 (research review) and Phase 8 (F1 fixture smoke).

### A6. Files written by Part A

- `audits/cluster3_implementation_plan_draft_report.md` (this addendum appended; nothing in the original report was removed or contradicted).

### A7. Handoff to Part B

`docs/cluster3_implementation_specification.md` consumes the resolutions in A2 and A3 and breaks Cluster 3 into commit-sized phases. No code is written by this audit.

---

## Part B: Post-Review Revision (2026-05-22)

A code review of the Part A resolutions and the v1 implementation specification surfaced seven integration findings against the current Modal harness, generation surface, repair loop, sanitizer, analyzer, and Modal entrypoint. Each finding is reproduced here with the codebase evidence and the binding revised contract that the specification now reflects.

### B1. Correctness eval condition translation

**Finding.** The v1 spec mapped Cluster 3 conditions to replay-control conditions before calling Cluster 2's correctness runner (`P → none`, `G+P → G`). Cluster 2's correctness runner gates Level 0 / Level 1 evaluation on `generation_allowed_for_condition(...)` returning True ([cluster2/modal/correctness_runner.py:73-99](cluster2/modal/correctness_runner.py:73); [cluster2/constants.py:107-110](cluster2/constants.py:107)). Replay controls (`none`, `G`) make that gate return False, so Level 0 parse, Level 0 signature, and Level 1 compile are **skipped**. F1_COMPILE would never be produced, and the P dispatcher would never see an eligible failure.

**Revised contract (binding).** The Cluster 3 correctness adapter translates Cluster 3 conditions to **generated** Cluster 2 conditions:

| Cluster 3 condition | Inner eval condition |
|---|---|
| `P` | `C` |
| `G+P` | `G+C` |
| `C+P` | `C` |
| `G+C+P` | `G+C` |

`C`/`G+C` are in `NEW_GENERATION_CONDITIONS` ([cluster2/constants.py:75-84](cluster2/constants.py:75)), so `generation_allowed_for_condition` returns True and the Level 0/1 gates fire. The adapter re-stamps the result's recorded `condition` and `surface` back to the Cluster 3 values before returning. This translation is **eval-surface-only**; the row's persisted `condition` always stays Cluster 3.

### B2. Generation condition adapter

**Finding.** `RemoteC2GenerationRequest` validates `identity.condition` via `require_c2_generation_condition`, which only accepts `C` and `G+C` ([cluster2/modal/schemas.py:223-239](cluster2/modal/schemas.py:223); [cluster2/constants.py:75-84](cluster2/constants.py:75)). The v1 spec left `cluster3/generation/` empty and reused Cluster 2's generation surface, but did not specify how the Cluster 3 condition becomes a Cluster 2-valid generation request.

**Revised contract (binding).** A pure adapter function lives at `cluster3/feedback/condition_adapters.py`:

```
cluster3_to_cluster2_generation_condition(c3_condition: str) -> str:
    {"P": "C", "C+P": "C", "G+P": "G+C", "G+C+P": "G+C"}
```

`run_cluster3_modal.py` calls this adapter before constructing every `RemoteC2GenerationRequest`. The Cluster 3 row records the original Cluster 3 condition; the wire-level generation request records the translated Cluster 2 condition for schema validation. Phase 5 tests assert the four mappings and assert that the Cluster 3 row's recorded condition is the un-translated value.

### B3. P repair success vs row success

**Finding.** Part A §A3 required `failure_code is None` whenever `p_repair_succeeded is True`. That conflates two distinct outcomes:

- P fixed the compile failure (the candidate now passes Level 1).
- The whole row succeeded (the candidate now passes Level 2).

In `P` and `C+P`, P can repair compile and the next eval can still fail F2_NUMERIC_LARGE / F2_NUMERIC_NAN / F2_SHAPE_MISMATCH. Forbidding `failure_code=F2_*` after `p_repair_succeeded=True` rejects a valid and important state.

**Revised contract (binding).** Rename `p_repair_succeeded` → `p_compile_repair_succeeded`. New semantics:

- `p_compile_repair_succeeded=True` means a P repair attempt produced a candidate that **passed Level 1 compile** (regardless of Level 2 outcome).
- The row's `failure_code` is independent: `None` if the candidate also passed Level 2, otherwise the canonical F-code at terminal classification.
- New row-level field `p_repair_changed_outcome: bool` records whether the terminal `failure_code` differs from `p_initial_failure_code`. This is the analyzer's primary "P helped" signal for repaired-vs-organic decomposition.

Updated validation in `Cluster3EvalRow.__post_init__`:

- `p_compile_repair_succeeded=True` ⇒ `compile_success=True` ⇒ `failure_code in (None, F2_NUMERIC_LARGE, F2_NUMERIC_NAN, F2_SHAPE_MISMATCH, F3_*)`.
- `p_compile_repair_succeeded=False` and `p_repair_attempted=True` ⇒ `failure_code == p_initial_failure_code` (P could not change Level 1 outcome).
- `p_repair_changed_outcome=True` ⇒ `p_initial_failure_code != p_final_failure_code` OR `p_initial_failure_code is not None and failure_code is None`.

The §A3 field table is amended: `p_repair_succeeded` is removed; `p_compile_repair_succeeded` and `p_repair_changed_outcome` are added.

### B4. C-loop invocation adapter

**Finding.** `cluster2.feedback.repair_loop.run_repair_loop` validates its `condition` via `require_generated_condition`, which only accepts `C` / `G+C` ([cluster2/feedback/repair_loop.py:125-143](cluster2/feedback/repair_loop.py:125)). The v1 spec said to invoke the C loop when a Cluster 3 condition contains C, but did not specify the condition restamping.

**Revised contract (binding).** A second adapter in `cluster3/feedback/condition_adapters.py`:

```
cluster3_to_cluster2_repair_condition(c3_condition: str) -> str:
    {"C+P": "C", "G+C+P": "G+C"}
```

`run_cluster3` translates the condition before calling `run_repair_loop`, then maps the returned `RepairLoopResult.condition` back to the Cluster 3 value before constructing the row. Phase 5 tests assert:

- Calling the adapter with `P` or `G+P` raises (those conditions cannot invoke C repair).
- C+P → C and G+C+P → G+C round-trip through `run_repair_loop` and the row records the Cluster 3 condition.
- A row produced by the C loop carries Cluster 2's `repair_trace` field unchanged.

### B5. P sanitizer is a separate module

**Finding.** Part A §A2.6 said to reuse Cluster 2's sanitizer "with an exception for `LLVM` and `PTX`". But `FORBIDDEN_FEEDBACK_TERMS` is a module-level constant at [cluster2/feedback/prompts.py:25-48](cluster2/feedback/prompts.py:25), and `_FORBIDDEN_PATTERNS` is a frozen `tuple[re.Pattern]` computed once at module import. There is no public hook for term-set substitution; `validate_no_forbidden_feedback_terms` iterates the hardcoded list. A "reuse with exception" approach would either monkeypatch a Cluster 2 module (forbidden — Cluster 2 stays read-only) or compute results that still fail Cluster 2's validator.

**Revised contract (binding).** Cluster 3 owns its own sanitizer at `cluster3/feedback/sanitizer.py`. It is a self-contained copy of the relevant Cluster 2 logic ([prompts.py:25-98, 286-317](cluster2/feedback/prompts.py:25)) with:

- `P_FORBIDDEN_FEEDBACK_TERMS` = Cluster 2's `FORBIDDEN_FEEDBACK_TERMS` minus `{"LLVM", "PTX"}`.
- `P_SENSITIVE_DETAIL_PATTERNS` = Cluster 2's `_SENSITIVE_DETAIL_PATTERNS` unchanged.
- Public functions `sanitize_p_feedback_text(value, *, limit) -> str` and `validate_no_forbidden_p_terms(value) -> None`.

No part of Cluster 3 imports `cluster2.feedback.prompts` for sanitization. The Phase 1 test `test_p_feedback_allows_llvm_and_ptx` is now an assertion against the Cluster 3 sanitizer specifically, not against Cluster 2's. A Phase 9 boundary test asserts the term lists differ exactly by `{"LLVM", "PTX"}` so any future Cluster 2 update is caught.

### B6. Analyzer factor-name compatibility

**Finding.** `FACTOR_COLUMNS = ("grammar_active", "compiler_feedback_active", "perf_feedback_active")` at [shared/analysis/factorial.py:59](shared/analysis/factorial.py:59) maps the P factor to `perf_feedback_active`, and the row→factor expansion uses `"perf_feedback_active": "P" in parts` ([factorial.py:1069](shared/analysis/factorial.py:1069)). That column name encodes the older "compiler/profiler repair" framing from [cluster3/README.md:13-19](cluster3/README.md:13). The new P meaning is compile-error feedback, not profiler / performance feedback.

A rename would break the existing analyzer output at `outputs/analysis/factorial_2x2_preliminary.json`, where every row currently has `perf_feedback_active=False`. The reportable status of that artifact would be at risk under the existing schema/registry co-update gate ([docs/05_artifacts_and_results_registry.md:208-215](docs/05_artifacts_and_results_registry.md:208)).

**Revised contract (binding).** Two-step rename, both steps in Phase 7:

- **Step 7a (additive, no rename).** Add a new analyzer column `compile_feedback_active`. Populate it from `"P" in parts` (same source as `perf_feedback_active`). `perf_feedback_active` continues to be populated identically for backward compatibility with the existing 2² output. Cluster 3 row normalization populates both columns. The factorial model uses `compile_feedback_active` for the P term; the row-level `perf_feedback_active` column is preserved verbatim in `paper_tables` so existing downstream consumers see the same column.
- **Step 7b (deferred to a separate later PR).** Once downstream consumers (analyzer CLIs, paper-table generators, audit notebooks) read `compile_feedback_active`, remove `perf_feedback_active` and bump the analyzer schema. **Step 7b is OUT OF SCOPE for v1** and is recorded as a future migration in the decision log.

Phase 7 acceptance test `test_analyzer_2x2_reproducible_without_cluster3_rows` continues to enforce byte-identical 2² output. A new test `test_analyzer_compile_feedback_alias_matches_perf_feedback` asserts the two columns are identical for every loaded row.

The canonical short label `P` is unchanged in `CANONICAL_CONDITIONS` and `FACTOR_NAMES`. The semantic note that "P now means compile-error feedback" is added to `docs/08_decision_log.md` in Phase 10.

### B7. Modal entrypoint strategy

**Finding.** The v1 spec described `cluster3/modal/correctness_runner.py` as a "thin adapter over Cluster 2's correctness runner" but did not specify whether the Cluster 3 path:

- (a) calls the existing Modal entrypoint `cluster2.modal.correctness.remote_c2_correctness` from a local orchestrator (which already builds the Cluster 2 + shared eval image at [cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41)), or
- (b) defines a new Modal entrypoint `cluster3/modal/correctness.py` with an image that bundles both `cluster2` and `cluster3` sources.

The Cluster 2 image only adds `cluster2` local sources ([cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41) — `triton_compile_image.add_local_python_source("cluster2")`). Option (b) requires a new image. Option (a) requires nothing new on the Modal side.

**Revised contract (binding).** Choose **option (a) for v1**. The Cluster 3 design avoids any new Modal entrypoint. The flow per (kernel, dtype, base_seed):

1. `run_cluster3` (local) translates Cluster 3 condition → Cluster 2 generation condition (B2).
2. `run_cluster3` calls Cluster 2's generation adapter (existing).
3. `run_cluster3` translates Cluster 3 condition → Cluster 2 eval condition (B1).
4. `run_cluster3` calls `cluster2.modal.correctness.remote_c2_correctness(...)` (existing Modal function on the existing image).
5. The Cluster 3 correctness adapter re-stamps the returned payload's `condition` and `surface` to Cluster 3 values.
6. The P dispatcher and P repair loop run **locally** in the Cluster 3 process; only generation and correctness round-trip to Modal.
7. If C is active, `run_repair_loop` is invoked with the Cluster 2-translated condition (B4) and itself round-trips to Modal via the existing surfaces.

Consequence: **Phase 4 produces only the local adapter, not a Modal function.** The phase's "files to add" is reduced to `cluster3/modal/correctness_runner.py` as a thin Python wrapper plus `cluster3/modal/__init__.py`. No new image, no `add_local_python_source("cluster3")`, no new `@app.function`.

`cluster3/modal/correctness.py` is reserved for v2 if a future contract requires a Cluster 3-only Modal entrypoint (e.g., to add profiler/speedup metrics). v1 explicitly does not need it.

### B8. Specification updates required by B1–B7

The implementation specification `docs/cluster3_implementation_specification.md` is updated in the same revision as this addendum. Changes:

- §1 "Final design summary" gains rows for the two adapters, the renamed P field, the compile_feedback_active alias, and the Modal entrypoint choice.
- Phase 1 sanitizer scope shifts to a Cluster 3-local copy.
- Phase 2 field table is amended (`p_repair_succeeded` → `p_compile_repair_succeeded`; add `p_repair_changed_outcome`).
- Phase 4 narrows to the local adapter only; no Modal function.
- Phase 5 adds the two condition adapters and tests; eval translation uses the C/G+C mapping.
- Phase 7 splits into 7a (additive `compile_feedback_active`) and 7b (deferred rename out of v1 scope).
- Phase 8 boundary tests adjust to the renamed schema field.

### B9. Revised classification

PLAN_AUDIT_VERIFIED_AND_RESOLVED — with binding Post-Review Revision applied.

All seven integration findings are addressed with concrete contracts grounded in the cited file paths. No PENDING_DESIGN_DECISION items remain. PENDING_RESEARCH items from §A2 and the original §5 are unchanged.

---

## Part C: Second-Pass Revision (2026-05-22)

A second code review of the post-review §B specification surfaced ten additional findings, mostly about handoff semantics between the initial eval, the P loop, and the C loop, plus several stale specifics. This Part C is the binding resolution; the implementation specification is updated in the same revision.

### C1. P loop seed-attempt contract

**Finding.** Phase 5 evaluates the initial candidate and dispatches on the resulting failure code. If the dispatcher routes to the P loop, the loop's `seed_candidate_source` parameter only carries the source string, not the already-computed evaluation result. The Cluster 2 loop's `seed_candidate_source` hook at [cluster2/feedback/repair_loop.py:161-162](cluster2/feedback/repair_loop.py:161) skips the first generation but **still runs the first evaluation**. An implementer following the spec literally would either (a) re-evaluate attempt 0 (wasted Modal call) or (b) skip the seed evaluation and regenerate attempt 0 (wasted Modal call and broken attempt-index accounting).

**Revised contract (binding).** The P loop accepts a richer seed parameter that carries the initial candidate source AND its already-known evaluation result:

```
@dataclass(frozen=True)
class PSeedAttempt:
    source: str
    evaluation_result: object       # public_view-compatible result for attempt 0
    failure_code: str               # the canonical code that triggered the P loop
    compile_error: str | None
    compile_error_type: str | None

run_p_repair_loop(
    *,
    base_prompt: str,
    base_seed: int,
    generation: GenerationCallable,
    evaluation: EvaluationCallable,
    seed_attempt: PSeedAttempt,    # required, replaces seed_candidate_source
    repair_budget: int = DEFAULT_P_REPAIR_BUDGET,
) -> PRepairLoopResult
```

Behavior:
- Attempt 0 in the loop's recorded trace is the seed attempt. `generation` is NOT called for attempt 0. `evaluation` is NOT called for attempt 0. The loop uses `seed_attempt.evaluation_result` directly.
- The loop's first generation call (attempt 1) receives the feedback built from `seed_attempt`.
- Attempt indexes in the recorded trace correspond to the standard `seed_for_attempt(base_seed, attempt_index)` formula so paired identity with Cluster 1 / 2 is preserved.

Test additions (Phase 1):
- `test_p_loop_seed_attempt_does_not_call_generation_or_evaluation_for_attempt_0` — assert call counts.
- `test_p_loop_seed_attempt_records_attempt_0_in_trace` — assert `PRepairLoopResult.attempts[0]` matches the seed.
- `test_p_loop_first_feedback_built_from_seed_attempt` — assert the second generation call's `previous_feedback` was constructed from `seed_attempt`.

### C2. P-to-C seed handoff

**Finding.** When the P loop terminates with compile success but the next eval is F2, the orchestrator routes to the C loop. The Cluster 2 C loop's `seed_candidate_source` at [cluster2/feedback/repair_loop.py:160-162](cluster2/feedback/repair_loop.py:160) IS the supported way to feed an existing candidate without regenerating. The §B5 spec said "invoke the C loop" but did not require seeding it. Without seeding, the C loop starts from a fresh generation off the base prompt and **discards the P-repaired source entirely**.

**Revised contract (binding).** Phase 5's control flow step 5 is amended: when the C loop fires after a P repair that reached Level 2:

1. The orchestrator captures the P loop's terminal source (the last attempt's source from `PRepairLoopResult.attempts`).
2. It passes that source as `seed_candidate_source=<p_terminal_source>` to `cluster2.feedback.repair_loop.run_repair_loop`.
3. The C loop's first evaluation runs against the seeded source (no regeneration); the C loop's subsequent attempts are real C-repair generations using the F2 feedback.

The orchestrator also passes the corresponding Level 2 evaluation result by re-using `cluster3.modal.correctness_runner` for the post-P eval; if that call already happened (which it must have, to produce the F2 code that triggered the C route), the orchestrator avoids re-evaluating by injecting the result into the C loop's first evaluation callable. Cluster 2's loop does NOT have a `seed_evaluation_result` hook, so the orchestrator wraps the `evaluation` callable to short-circuit on attempt 0 and return the cached F2 result. This is the smallest local change consistent with treating Cluster 2 as read-only.

Test additions (Phase 5):
- `test_run_cluster3_c_plus_p_seeds_c_loop_with_p_terminal_source` — assert the `seed_candidate_source` argument to `run_repair_loop` equals the terminal P attempt source.
- `test_run_cluster3_c_plus_p_does_not_regenerate_after_p_repair` — assert generation is called exactly N_P + N_C times (initial + P repair attempts + C repair attempts), never N_P + N_C + 1.
- `test_run_cluster3_c_plus_p_c_loop_first_eval_uses_cached_f2_result` — assert the C loop's attempt-0 evaluation does not call the correctness adapter.

### C3. P loop "success" semantics

**Finding.** The §B3 schema allows `p_compile_repair_succeeded=True` with terminal `failure_code=F2_*`. Phase 1's P loop test `test_p_loop_terminates_on_f2_numeric` says the loop returns `status="terminated"` on F2. Phase 5's control flow assumed the P loop returns `status="success"` when compile is repaired. These three statements are internally inconsistent. The loop must explicitly distinguish "P fixed compile" from "row succeeded end-to-end".

**Revised contract (binding).** `PRepairLoopResult.status` enum is now:

| Status | Meaning |
|---|---|
| `"compile_repaired_then_success"` | P fixed compile AND Level 2 passed in the same attempt. Row's `functional_success=True`. |
| `"compile_repaired_f2_observed"` | P fixed compile but Level 2 failed F2. The orchestrator routes to the C loop next (if condition contains C) or terminates with the F2 code. |
| `"compile_repaired_f3_observed"` | P fixed compile but Level 2 was prevented by F3 infrastructure. Terminate. |
| `"compile_unchanged_exhausted"` | Budget exhausted; every attempt still F1_COMPILE. |
| `"terminated_unrecoverable"` | F0_*, F1_RUNTIME, F3_* observed during P attempts. |

`p_compile_repair_succeeded` (the schema field, §B3) is True iff `status` starts with `"compile_repaired_"`. Phase 1 tests are updated:

- `test_p_loop_status_compile_repaired_then_success` — replaces `test_p_loop_success_on_first_attempt`.
- `test_p_loop_status_compile_repaired_f2_observed` — second P attempt yields F2_NUMERIC_LARGE; assert this status (NOT `"terminated"`).
- `test_p_loop_status_compile_repaired_f3_observed` — F3 mid-loop.
- `test_p_loop_status_compile_unchanged_exhausted` — every attempt F1_COMPILE through budget.
- `test_p_loop_status_terminated_unrecoverable` — F0 or F1_RUNTIME mid-loop.

This subsumes the original `test_p_loop_terminates_on_f2_numeric`; the F2 case is no longer a "terminate" — it is a "compile_repaired_f2_observed" and the **orchestrator** decides whether to chain to C.

### C4. Dispatcher must consult level_reached

**Finding.** The §B dispatcher routes on failure code alone. Cluster 2's `_must_terminate_without_feedback` at [cluster2/feedback/repair_loop.py:366-369](cluster2/feedback/repair_loop.py:366) also gates on `level_reached < 2`. Without the level check, the dispatcher could route a payload with `failure_code="F2_NUMERIC_LARGE"` but `level_reached=1` (a defensive code-set mismatch) to the C loop, which would then immediately terminate; conversely, a payload with `failure_code="F1_COMPILE"` but `level_reached=0` (Level 1 never ran) would route to the P loop with no actual compile evidence.

**Revised contract (binding).** The dispatcher signature becomes:

```
dispatch(condition: str, failure_code: str | None, level_reached: int | None) -> DispatchDecision
```

with rules:
- `failure_code is None` → terminate, reason `"success"`.
- `level_reached is None` → terminate, reason `"level_reached_missing"`.
- `level_reached == 0` → terminate, reason `"f0_terminal"` (regardless of code).
- `level_reached == 1` AND `failure_code == "F1_COMPILE"` → `p_loop`, reason `"p_eligible"`.
- `level_reached == 1` AND `failure_code in {"F1_RUNTIME"}` → terminate, reason `"unrecoverable_runtime"`.
- `level_reached >= 2` AND `failure_code in {"F2_NUMERIC_LARGE", "F2_NUMERIC_NAN", "F2_SHAPE_MISMATCH"}` AND condition ∈ `{"C+P", "G+C+P"}` → `c_loop`, reason `"c_eligible"`.
- `level_reached >= 2` AND `failure_code in F2_*` AND condition ∉ `{"C+P", "G+C+P"}` → terminate, reason `"f2_terminal_no_c"`.
- F3_* → terminate, reason `"f3_terminal"`.

Test additions (Phase 3):
- `test_dispatcher_requires_level_reached_for_f1_compile` — F1_COMPILE with level_reached=0 terminates.
- `test_dispatcher_requires_level_reached_ge_2_for_c_loop` — F2_* with level_reached=1 terminates with `"f2_below_level2"`.
- `test_dispatcher_rejects_level_reached_none` — terminates with `"level_reached_missing"`.

### C5. Schema for failed P attempts

**Finding.** §B3 said: if `p_compile_repair_succeeded=False` AND `p_repair_attempted=True`, then `failure_code == p_initial_failure_code`. But a P attempt that regenerates can move the candidate to a DIFFERENT terminal class: P can turn `F1_COMPILE` into `F0_PARSE` (parser breaks on a different syntactic shape), `F1_RUNTIME` (the regenerated code launches but raises), or `F3_EVAL_PIPELINE` (infrastructure flake). All are valid terminal states and the schema must accept them. Also: `p_repair_changed_outcome` was described in §B3 as "P helped"; changing F1_COMPILE → F0_PARSE is a CHANGED outcome but not a HELP.

**Revised contract (binding).** Schema rule replacement:

- If `p_repair_attempted is True`: `p_final_failure_code` may be any member of `FAILURE_CODES` or None. The row's `failure_code` MUST equal `p_final_failure_code` (the row records the terminal P outcome).
- If `p_compile_repair_succeeded is True`: `compile_success is True` AND `failure_code in (None, F2_*, F3_*)` (unchanged from §B3).
- If `p_compile_repair_succeeded is False` AND `p_repair_attempted is True`: `compile_success is False` AND `failure_code` may be any F0/F1/F3 code (including codes different from `p_initial_failure_code`).

Field semantic clarification:
- `p_repair_changed_outcome: bool` is renamed to `p_repair_changed_terminal_class: bool` and explicitly documented as a neutral signal: True iff `p_initial_failure_code != p_final_failure_code` OR `p_initial_failure_code is not None and failure_code is None`. The analyzer treats it as evidence of P activity, NOT as evidence of improvement.
- A separate derived analyzer column `p_helped: bool` (computed by the analyzer, not stored in the row) is True iff the terminal class moved up the ladder (F1 → success, F1 → F2 with C+P then success, etc.). The exact predicate is finalized in Phase 7 once the helper-vs-harmful semantics are settled empirically (PENDING_RESEARCH).

Test additions (Phase 2):
- `test_cluster3_row_p_attempted_failed_allows_terminal_class_change` — `p_initial_failure_code="F1_COMPILE"`, `p_final_failure_code="F0_PARSE"`, `failure_code="F0_PARSE"`, `p_compile_repair_succeeded=False` is accepted.
- `test_cluster3_row_failure_code_must_equal_p_final_when_p_attempted` — mismatch raises.
- `test_cluster3_row_p_helped_not_stored` — assert `Cluster3EvalRow` has no `p_helped` attribute.

### C6. Cluster 3 identity helpers

**Finding.** Phase 0 defines `normalize_cluster3_condition` but not `source_class_for_cluster3_condition` or `generation_mode_for_cluster3_condition`. Cluster 2's helpers at [cluster2/constants.py:87-104](cluster2/constants.py:87) are the closest pattern. The Cluster 3 row schema (Phase 2) and the Cluster 3 correctness adapter (Phase 4) both reference `source_class` and `generation_mode` without saying what values are populated for P-containing rows.

**Revised contract (binding).** Phase 0 adds two helpers to `cluster3/constants.py`:

```
def source_class_for_cluster3_condition(condition: str) -> str:
    # All Cluster 3 conditions generate fresh sources (none are replay controls).
    require_cluster3_condition(condition)
    return GENERATED_SOURCE_CLASS  # imported from cluster2.constants

def generation_mode_for_cluster3_condition(condition: str) -> str:
    # The wire-level generation mode is determined by the Cluster 2 generation
    # condition (§B2), not the Cluster 3 condition, because the underlying
    # generation surface is Cluster 2's.
    c2_condition = cluster3_to_cluster2_generation_condition(condition)
    return cluster2.constants.generation_mode_for_condition(c2_condition)
```

Result: `P` and `C+P` rows carry `generation_mode == C_GENERATION_MODE`; `G+P` and `G+C+P` rows carry `generation_mode == G_PLUS_C_GENERATION_MODE`. `source_class` is always `GENERATED_SOURCE_CLASS`. This mirrors the natural fact that Cluster 3 generation IS Cluster 2 generation under the hood.

The Cluster 3 row schema (Phase 2) validates `source_class` and `generation_mode` against these helpers.

Test additions (Phase 0):
- `test_source_class_for_cluster3_condition_returns_generated_for_all_p_cells`.
- `test_generation_mode_for_cluster3_condition_matches_c2_after_translation` — table of four mappings.

### C7. Sanitizer contradictions

**Finding.** The §B5 binding contract says Cluster 3 sanitizer must NOT import `cluster2.feedback.prompts`. But the Phase 1 Risk + mitigation text says "re-export Cluster 2's `validate_no_forbidden_feedback_terms`". The Phase 9 boundary test `test_p_feedback_excludes_speedup_profiler_language` is described as asserting `validate_no_forbidden_feedback_terms` is invoked — that's the Cluster 2 function. These are contradictions an implementer would have to guess about.

**Revised contract (binding).** Phase 1 Risk + mitigation language is corrected to: "Risk: forbidden-term regex duplication. Mitigation: Cluster 3 owns a self-contained copy at `cluster3/feedback/sanitizer.py`. A Phase 1 test (`test_p_forbidden_terms_differ_from_cluster2_by_exactly_llvm_and_ptx`) locks the divergence against Cluster 2 drift." The Phase 9 boundary test name and body reference `validate_no_forbidden_p_terms` (Cluster 3) only. Every reference in the spec to "Cluster 2 sanitizer" in a Cluster 3 context is removed.

### C8. Analyzer P-pair gating

**Finding.** Extending `PAIRED_REPLAY_COMPARISONS` ([factorial.py:85](shared/analysis/factorial.py:85)) with the four P pairs unconditionally changes:
- The metadata block at [factorial.py:452-458](shared/analysis/factorial.py:452), which iterates `PAIRED_REPLAY_COMPARISONS.items()` to emit `paired_primary_comparisons`. This makes the 2² output's metadata reference P pairs even when no Cluster 3 rows are present.
- The paired comparison rows at [factorial.py:1620-1627](shared/analysis/factorial.py:1620), which raise `ValueError` when a treatment or control is missing under `scope == "primary_functional"`. With P pairs added, missing P cells would raise instead of skipping.

**Revised contract (binding).** Phase 7a does NOT extend `PAIRED_REPLAY_COMPARISONS` as a module constant. Instead it adds:

```
P_PAIRED_REPLAY_COMPARISONS = {"P": "none", "G+P": "G", "C+P": "C", "G+C+P": "G+C"}

def effective_paired_replay_comparisons(populated_cells: Sequence[str]) -> dict[str, str]:
    """Return the paired comparisons active given which cells are populated."""
    base = dict(PAIRED_REPLAY_COMPARISONS)
    for treatment, control in P_PAIRED_REPLAY_COMPARISONS.items():
        if treatment in populated_cells and control in populated_cells:
            base[treatment] = control
    return base
```

The metadata block at [factorial.py:452-458](shared/analysis/factorial.py:452) is changed to iterate `effective_paired_replay_comparisons(populated_cells).items()`. The paired comparison row builder at [factorial.py:1620](shared/analysis/factorial.py:1620) likewise iterates the effective dict. `PAIRED_REPLAY_COMPARISONS` itself is unchanged so any downstream code that imports it sees the original 2² values; new code uses the effective helper.

Test additions (Phase 7a):
- `test_analyzer_metadata_paired_pairs_match_2x2_when_no_cluster3` — assert the metadata's `paired_primary_comparisons` list has exactly the two original entries.
- `test_analyzer_metadata_paired_pairs_extend_when_all_eight_cells_present` — six entries.
- `test_analyzer_does_not_raise_on_missing_p_pair_when_only_2x2_populated` — strict assertion.
- The existing `test_analyzer_2x2_reproducible_without_cluster3_rows` (byte-identical) remains the headline gate.

### C9. Modal image wording

**Finding.** Phase 11's risk note claimed "Cluster 3's adapter imports something Cluster 2's image doesn't already have" and the image bundles "only cluster2". Reality: `triton_compile_image` at [shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21) already bundles `cluster1`, `cluster2`, AND `shared` via `add_local_python_source("cluster1", "cluster2", "shared")`. The Cluster 2 correctness function at [cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41) wraps it with `add_local_python_source("cluster2")` (a no-op redundancy). The current image does NOT contain `cluster3`.

**Revised contract (binding).** Phase 11 risk + image wording is corrected. The accurate statements are:

- The Cluster 2 image bundles `cluster1`, `cluster2`, `shared` ([shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21)). It does NOT bundle `cluster3`.
- In v1, the Cluster 3 path runs the dispatcher, P loop, prompt construction, sanitization, and row construction LOCALLY. Only the existing Cluster 2 generation and correctness Modal entrypoints round-trip to Modal. Those entrypoints never need to import `cluster3`. Therefore the existing image is sufficient and **no image change is required for Cluster 3 v1**.
- The `add_local_python_source("cluster3")` line is explicitly NOT added in v1.
- If a future v2 needs a remote Cluster 3 entrypoint (e.g., to add profiler/speedup measurement), that contract adds `cluster3` to the image AT THAT TIME.

### C10. Stale specifics

**Finding (a).** Canonical kernel names are `elementwise/relu`, `reduction/softmax`, `matmul/gemm` per [shared/eval/correctness_shapes.py:59-79](shared/eval/correctness_shapes.py:59) and the kernel specs at [cluster1/data/kernels/elementwise_relu.py:62](cluster1/data/kernels/elementwise_relu.py:62), [reduction_softmax.py:62](cluster1/data/kernels/reduction_softmax.py:62), [matmul_tiled_gemm.py:65](cluster1/data/kernels/matmul_tiled_gemm.py:65). The spec previously said `elementwise/add`, `reduction/sum`, `matmul`. Corrected to relu/softmax/gemm.

**Finding (b).** `DEFAULT_MAX_NEW_TOKENS` is 1536 in Cluster 2 ([cluster2/constants.py:37](cluster2/constants.py:37)) and 2048 in Cluster 1 ([cluster1/constants.py:7](cluster1/constants.py:7)). The Part A addendum incorrectly cited 1024. The 2000-character compile-error excerpt cap (§A2.6) is still inside Cluster 2's budget; the rationale stands. The Part A addendum is corrected in §C10 footnote below.

**Finding (c).** The original §5 of this report still names `p_repair_succeeded` as a draft field. The supersession banner already declares §5 superseded; for unambiguous reading the implementation specification (which is the single source of truth) uses `p_compile_repair_succeeded` and `p_repair_changed_terminal_class` (§C5 rename of `p_repair_changed_outcome`).

**Part A correction (footnote).** In §A2.6, the sentence "comfortably inside `DEFAULT_MAX_NEW_TOKENS = 1024` ([cluster2/experiments/run_cluster2_modal.py:75](cluster2/experiments/run_cluster2_modal.py:75))" is corrected to "comfortably inside `DEFAULT_MAX_NEW_TOKENS = 1536` ([cluster2/constants.py:37](cluster2/constants.py:37))". The 2000-char cap rationale is unchanged because 1536 is still well above 500 tokens-equivalent.

### C11. Specification updates required by C1–C10

The implementation specification is updated in the same revision as this Part C. Changes:

- §1 table gains rows for the seed-attempt contract (§C1), the P-to-C seed handoff (§C2), the P-loop status enum (§C3), the level-gated dispatch (§C4), the loosened P-failed schema (§C5), and the Cluster 3 identity helpers (§C6).
- Phase 0 adds `source_class_for_cluster3_condition` and `generation_mode_for_cluster3_condition` plus tests.
- Phase 1 P-loop signature changes to accept `PSeedAttempt`; status enum updated; tests rewritten.
- Phase 1 Risk + mitigation language fixed to not reference Cluster 2 sanitizer re-export (§C7).
- Phase 2 schema validation rules updated per §C5; `p_repair_changed_outcome` renamed to `p_repair_changed_terminal_class`.
- Phase 3 dispatcher signature gains `level_reached` (§C4); routing rules updated.
- Phase 5 control flow steps 4–5 expanded for the seed-attempt and seed-handoff contracts.
- Phase 7a introduces `effective_paired_replay_comparisons` helper (§C8) and never extends `PAIRED_REPLAY_COMPARISONS` as a module constant.
- Phase 9 boundary test rewording fixed (§C7) to only mention `validate_no_forbidden_p_terms`.
- Phase 11 and Phase 12 wording corrected for Modal image semantics (§C9) and kernel names (§C10a).
- §22 changelog extended with rows for §C1–§C10.

### C12. Revised classification

PLAN_AUDIT_VERIFIED_AND_RESOLVED — with binding Post-Review Revision (§B) and Second-Pass Revision (§C) applied.

All seventeen total integration findings (§B1–§B7 + §C1–§C10) now have concrete contracts grounded in cited file paths and phase-level acceptance tests. No PENDING_DESIGN_DECISION items remain. PENDING_RESEARCH items are unchanged plus one addition (§C5's `p_helped` predicate, deferred to Phase 7 design once empirical evidence exists).

---

## Part D: Third-Pass Revision (2026-05-22)

A third code review surfaced ten more spec-internal contradictions and stale claims that would either cause failed tests or ambiguous row semantics during implementation. Part D is the binding resolution; the implementation specification is updated in the same revision.

### D1. Phase 0 / Phase 1 import ordering

**Finding.** Phase 0's `generation_mode_for_cluster3_condition` lazily imports `cluster3.feedback.condition_adapters.cluster3_to_cluster2_generation_condition`. That module is created in Phase 1. Under strict phase ordering, the Phase 0 test `test_generation_mode_for_cluster3_condition_matches_c2_after_translation` cannot pass before Phase 1 lands.

**Revised contract (binding).** The four-entry condition mapping table is moved into `cluster3/constants.py` as a private constant `_CLUSTER3_TO_CLUSTER2_GENERATION` and `_CLUSTER3_TO_CLUSTER2_REPAIR`. Phase 0 helpers use these directly with no Phase 1 import. Phase 1 `cluster3/feedback/condition_adapters.py` re-exports the same constants and offers the public `cluster3_to_cluster2_*_condition` helper functions. A Phase 1 test `test_condition_adapter_tables_match_constants` asserts the Phase 1 helpers' tables are identical to the Phase 0 constants. This puts the source of truth in Phase 0 and keeps Phase 1 as the human-facing API surface.

### D2. §1 table stale field name

**Finding.** §1 table row "P success field" (originally added in §B3) still says "Added: `p_repair_changed_outcome: bool`". §C5 supersedes that with `p_repair_changed_terminal_class`. The §1 table is the active summary, not historical text.

**Revised contract (binding).** The §1 "P success field" row is rewritten to state the final §C5 names: `p_compile_repair_succeeded`, `p_repair_changed_terminal_class`. The §C5 row is left as the explicit rename-event audit trail.

### D3. PRepairAttemptSummary has `source_hash`, not `source`

**Finding.** `PRepairAttemptSummary` (Phase 1) carries `source_hash: str | None`, not `source: str`. The Phase 1 test `test_p_loop_terminal_source_equals_last_attempt_source` was written as `result.terminal_source == result.attempts[-1].source` — that attribute does not exist. Cluster 2's trace summaries are intentionally source-free ([cluster2/feedback/repair_loop.py:73-85](cluster2/feedback/repair_loop.py:73)).

**Revised contract (binding).** The trace summary stays source-free (mirrors Cluster 2). Add `import hashlib` and rewrite the test as:

```
def test_p_loop_terminal_source_hash_matches_last_attempt():
    expected = hashlib.sha256(result.terminal_source.encode("utf-8")).hexdigest()
    assert result.attempts[-1].source_hash == expected
```

`PRepairLoopResult.terminal_source` remains the full source string (the orchestrator needs it for the §C2 seeded C handoff); the per-attempt summaries continue to store only the hash.

### D4. PSeedAttempt lacks `generation_seed`

**Finding.** `PRepairAttemptSummary` requires `generation_seed: int`. The P loop records the seed for every attempt. Attempt 0 is the seed candidate, but `PSeedAttempt` has no `generation_seed` field. The spec also says "attempt 0 uses whatever seed the seed_attempt was generated under", but provides no way for the orchestrator to communicate that seed to the loop.

**Revised contract (binding).** `PSeedAttempt` gains `generation_seed: int`. The loop's recorded attempt-0 summary uses `seed_attempt.generation_seed`. Validation: `generation_seed >= 0`.

### D5. `config.c_repair_budget` is undefined

**Finding.** Phase 5 control flow step 5 passes `repair_budget=<config.c_repair_budget>` to `cluster2.feedback.repair_loop.run_repair_loop`. `Cluster3RunnerConfig` (Phase 5) defines only `p_repair_budget`. There is no `c_repair_budget` field. This breaks Phase 5 implementation literally.

**Revised contract (binding).** `Cluster3RunnerConfig` gains a second budget field:

- `p_repair_budget: int` — passed to `run_p_repair_loop`. Validated in `[0, DEFAULT_P_REPAIR_BUDGET]`.
- `c_repair_budget: int` — passed to `cluster2.feedback.repair_loop.run_repair_loop` when the C handoff fires. Default `cluster2.constants.DEFAULT_REPAIR_BUDGET = 5` ([cluster2/constants.py:33](cluster2/constants.py:33)). Validated in `[0, DEFAULT_REPAIR_BUDGET]`.

CLI flags: `--p-repair-budget` and `--c-repair-budget`, both defaulting to 5. A Phase 5 test asserts the two budgets are independently parsed and that the C handoff receives `c_repair_budget` (not `p_repair_budget`).

### D6. C-loop wrapper condition-label ambiguity

**Finding.** When `run_cluster3` invokes `cluster2.feedback.repair_loop.run_repair_loop` after a P→F2 handoff, it passes `generation` and `evaluation` callables. Cluster 2's loop calls those callables with `RepairGenerationInput(condition="C", ...)` or `condition="G+C"` (the §B4-translated condition). If the wrappers feed that received `condition` field back through `cluster3_to_cluster2_generation_condition` to build the next Modal request, the adapter raises because `"C"` is not in `CLUSTER3_CONDITIONS`. The wrappers must close over the OUTER Cluster 3 condition (`C+P` or `G+C+P`) and ignore the inner C2-translated condition for translation purposes.

**Revised contract (binding).** Phase 5 control flow specifies that the wrapped generation and evaluation callables for the C loop are constructed with the outer Cluster 3 condition captured as a free variable:

```
outer_c3_condition = "C+P"  # or "G+C+P"

def wrapped_generation(c2_input: RepairGenerationInput) -> str:
    # Use outer_c3_condition for adapter translation, NOT c2_input.condition.
    # c2_input.condition is the Cluster 2 label the C loop expects in its trace.
    c2_gen_condition = cluster3_to_cluster2_generation_condition(outer_c3_condition)
    # c2_gen_condition will equal c2_input.condition by construction; assert it
    # for safety.
    assert c2_gen_condition == c2_input.condition
    ...  # build and dispatch RemoteC2GenerationRequest with c2_gen_condition

def wrapped_evaluation(c2_input: RepairEvaluationInput) -> RemoteCorrectnessResult:
    c2_eval_condition = cluster3_to_cluster2_eval_condition(outer_c3_condition)
    assert c2_eval_condition == c2_input.condition
    if cached_p_terminal_eval is not None and c2_input.attempt_index == 0:
        result = cached_p_terminal_eval
        cached_p_terminal_eval = None  # one-shot
        return result
    ...  # call cluster3.modal.correctness_runner.run_cluster3_correctness
```

Phase 5 tests add:
- `test_run_cluster3_c_wrapper_uses_outer_c3_condition_for_translation` — the wrapper does NOT pass `c2_input.condition` to `cluster3_to_cluster2_*_condition`.
- `test_run_cluster3_c_wrapper_assertion_holds_for_paired_translations` — the assert never fires (both translations give the same answer by construction).

### D7. `p_final_failure_code` vs row `failure_code` after C succeeds

**Finding.** §C5 said: when `p_repair_attempted=True`, row `failure_code == p_final_failure_code`. But for the C+P / G+C+P happy path (initial F1 → P repairs to F2 → C repairs to success), the row's `failure_code` is `None` while the P loop's terminal classification is F2. Equality is wrong in that case.

**Revised contract (binding).** Rename `p_final_failure_code` → `p_terminal_failure_code` (semantically: "the classification at the end of the P loop, before any C handoff"). The constraint becomes:

- When `p_repair_attempted=True` AND no C loop fired (no §C2 handoff occurred): row `failure_code == p_terminal_failure_code`.
- When `p_repair_attempted=True` AND a C loop fired (status was `compile_repaired_f2_observed` AND condition ∈ {C+P, G+C+P}): row `failure_code` is the C loop's terminal classification (may be None if C succeeded, or an F2 code if C exhausted, or an F3 code if C hit infra failure). `p_terminal_failure_code` records what P ended at; the row's `failure_code` records what the whole row ended at.
- `p_repair_changed_terminal_class` (§C5) is computed from `p_initial_failure_code` vs `p_terminal_failure_code` (the P-only signal), NOT vs the row's final `failure_code` (which may reflect C's work).

The Cluster 3 row gains one more field to disambiguate which path was taken:

- `c_loop_fired: bool` (default False). True iff the C loop ran after P. Used by the schema validator to choose which equality constraint to enforce, and by the analyzer to attribute success to P vs C.

When `c_loop_fired=True`, `condition` must be in `{"C+P", "G+C+P"}` and `repair_trace` (the Cluster 2-shaped trace) must be non-None.

Phase 2 validation updates:
- `c_loop_fired is True` ⇒ `condition ∈ {"C+P", "G+C+P"}` AND `repair_trace is not None` AND `p_repair_attempted is True`.
- `c_loop_fired is False` AND `p_repair_attempted is True` ⇒ `failure_code == p_terminal_failure_code`.
- `c_loop_fired is False` AND `p_repair_attempted is False` ⇒ `repair_trace is None`.

Phase 2 tests:
- `test_cluster3_row_c_plus_p_after_c_success_failure_code_is_none` — `p_repair_attempted=True`, `p_compile_repair_succeeded=True`, `p_terminal_failure_code="F2_NUMERIC_LARGE"`, `c_loop_fired=True`, `failure_code=None`, `functional_success=True` is accepted. (The previous §C5 rule rejected this — it required `failure_code == p_final_failure_code`.)
- `test_cluster3_row_c_loop_fired_requires_c_in_condition` — `c_loop_fired=True`, `condition="P"` raises.
- `test_cluster3_row_p_only_after_p_compile_repair_failure_code_matches_p_terminal` — `condition="P"`, `c_loop_fired=False`, `failure_code != p_terminal_failure_code` raises.

The §A3 + §B3 + §C5 field set is updated accordingly: `p_final_failure_code` is removed; `p_terminal_failure_code` is added; `c_loop_fired` is added.

### D8. Modal adapter stale claims

**Finding.** Phase 4 narrative still has three stale claims:

(a) "The Cluster 2 image at `cluster2/modal/correctness.py:41` only bundles `cluster2` local sources." This is false. `triton_compile_image` at [shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21) bundles `cluster1`, `cluster2`, AND `shared`. `cluster2/modal/correctness.py:41` then re-adds `cluster2` (redundant no-op).

(b) "`RemoteCorrectnessRequest` accepts any factor cell." This is misleading. `RemoteCorrectnessRequest.identity.condition` is a `FactorCell`-typed pydantic field that is normalized by `EvalIdentity`; not literally "any factor cell" but the canonical set.

(c) Phase 4 test `test_adapter_translates_p_to_c_for_inner_eval` asserts `identity.source_class="generated"`. The actual constant value is `"generated_row"` per [cluster2/constants.py:15, 27](cluster2/constants.py:15) (`GENERATED_SOURCE_CLASS: Cluster2SourceClass = "generated_row"`).

**Revised contract (binding).** Phase 4 narrative rewritten:

- "The Cluster 2 image (`triton_compile_image` at [shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21)) already bundles `cluster1`, `cluster2`, and `shared` via `add_local_python_source(...)`. The Cluster 2 correctness function at [cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41) wraps it with another `add_local_python_source("cluster2")` (redundant no-op). The image does NOT bundle `cluster3`, and v1 does not add it."
- "`RemoteCorrectnessRequest` accepts the canonical `FactorCell` set ([shared/factors/cells.py](shared/factors/cells.py)); Cluster 3's wrapper restricts the surface to `CLUSTER3_CONDITIONS`."
- Test rewritten: `identity.source_class == cluster2.constants.GENERATED_SOURCE_CLASS == "generated_row"`. The test uses the constant name, not a hardcoded string, so it stays correct if the constant value changes.

### D9. Correctness payload restamping omits nested identity

**Finding.** Cluster 2's correctness payload nests the eval identity in two places: the top-level wrapper `identity` and the `correctness_result.identity` ([cluster2/modal/correctness_runner.py:288-329](cluster2/modal/correctness_runner.py:288)). The Cluster 2 validator at [correctness_runner.py:463](cluster2/modal/correctness_runner.py:463) asserts they match. The §B7 restamp list in the spec covers top-level `surface`, top-level `identity.condition`, `source_identity.condition`, and `eval_identity.condition`, but omits `correctness_result.identity.condition`.

**Revised contract (binding).** `restamp_cluster3_condition` is amended to restamp all of:

- top-level `surface` ← `"c3_remote_correctness"`
- top-level `condition` (where present) ← outer Cluster 3 condition
- `identity.condition` ← outer Cluster 3 condition
- `source_identity.condition` ← outer Cluster 3 condition
- `eval_identity.condition` ← outer Cluster 3 condition (if the eval_identity dict has a `condition` key — current Cluster 2 builders may not include it but Cluster 3 should restamp defensively)
- `correctness_result.identity.condition` ← outer Cluster 3 condition (NEW per §D9)

A Phase 4 test `test_adapter_restamps_nested_correctness_result_identity` asserts the nested condition is restamped.

Restamping is followed by a validator pass on the Cluster 3 side that re-asserts `wrapper.identity == correctness_result.identity` post-restamp (mirroring Cluster 2's invariant) — so that any future Cluster 2 payload-shape change is caught at Cluster 3's boundary.

### D10. Analyzer `model_type` rename collision

**Finding.** §B6 / Phase 7 said: "Flip the `model_type` branch at [factorial.py:1828](shared/analysis/factorial.py:1828) from `'partial_eight_cell_not_reportable'` to `'full_eight_cell_reportable'` only when ALL eight cells are populated." But current code at [factorial.py:1827](shared/analysis/factorial.py:1827) emits `model_type = "full_eight_cell"`, and `shared/tests/test_factorial_analysis.py:888` asserts `model_type == "full_eight_cell"`. Renaming to `full_eight_cell_reportable` would break the existing test under regression.

**Revised contract (binding).** The `model_type` string `"full_eight_cell"` is preserved verbatim. Reportability is signaled via a separate `metadata.reportable` key (which already exists in the analyzer metadata at [factorial.py:471-475](shared/analysis/factorial.py:471)) and via the `interpretation_flags` list at [factorial.py:476](shared/analysis/factorial.py:476). The spec is corrected: no `model_type` rename. The Phase 7 test that asserts the byte-identical 2² output stays as the gate.

The `partial_eight_cell_not_reportable` branch ([factorial.py:1858](shared/analysis/factorial.py:1858)) likewise stays unchanged in its string name; the existing test at `test_factorial_analysis.py:910` already exercises that path.

### D11. Cleanup: attempt_count semantics + Phase 8 status name + Phase 6 manifest source

**Finding (a).** `p_repair_attempt_count` was defined as `<= p_repair_budget + 1` but the seed-attempt contract (§C1) makes the semantics ambiguous: does it count attempt 0 (the seed) or only the new generations (attempts 1..budget)?

**Resolution.** `p_repair_attempt_count` counts the new P-generation attempts only (attempts 1..budget). The seed candidate (attempt 0) is not counted because it was not produced by P. Bound: `p_repair_attempt_count in [0, p_repair_budget]`. The total trace length is `p_repair_attempt_count + 1` (including the seed). Phase 2 validator updates: `p_repair_attempt_count <= p_repair_budget` (NOT `+ 1`); `len(p_repair_trace) == p_repair_attempt_count + 1` when `p_repair_attempted=True`.

**Finding (b).** Phase 8 fixture test `test_p_loop_exhausts_budget_on_persistent_compile_error` asserts `status="exhausted"`. The post-§C3 enum is `compile_unchanged_exhausted`.

**Resolution.** Phase 8 test name and body corrected: `status="compile_unchanged_exhausted"`, `attempts_executed == DEFAULT_P_REPAIR_BUDGET + 1` (including the seed).

**Finding (c).** Phase 6 said "reads existing Cluster 2 artifact manifest" but `cluster2/contracts/` contains only `frozen_cluster1_artifacts_manifest.json` (the Cluster 1 frozen manifest used as a source for Cluster 2 replay) and `cluster2_plan_hash.txt` / `phase_minus1_manifest.json`. There is no "Cluster 2 artifact manifest" file; Cluster 2 artifact identity lives in `docs/05_artifacts_and_results_registry.md` and the JSONL sidecars under `outputs/cluster2/`.

**Resolution.** Phase 6 builder is concretized:

- Input 1 (none / G rows): `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` (the Cluster 1 frozen manifest, which is what Cluster 2 already uses as its replay control source per [cluster2/experiments/run_cluster2_modal.py:43-55](cluster2/experiments/run_cluster2_modal.py:43)).
- Input 2 (C / G+C rows): a list of Cluster 2 output JSONL paths under `outputs/cluster2/` provided to the builder via CLI argument `--cluster2-outputs path1.jsonl path2.jsonl ...`. The builder reads each JSONL's identity tuples directly (each row has `kernel_class, kernel_name, dtype, base_seed`).
- The builder emits `cluster3/contracts/frozen_no_p_pair_manifest.json` with one entry per `(kernel_class, kernel_name, dtype, base_seed)` and the source artifact path and `source_sha256` per identity.

Phase 6 test `test_build_no_p_pair_manifest_from_fixtures` is updated to pass synthetic input paths matching this shape. Phase 6 documentation note: "If `outputs/cluster2/` paths are not yet established, the manifest is built when the first Cluster 2 paper-scale artifact lands, not before."

### D12. Specification updates required by D1–D11

The implementation specification `docs/cluster3_implementation_specification.md` is updated in the same revision:

- Phase 0: condition-mapping tables moved into `cluster3/constants.py`; Phase 1 condition_adapters becomes a re-export + helper API (§D1).
- §1 table: "P success field" row rewritten to use `p_compile_repair_succeeded` and `p_repair_changed_terminal_class` (§D2).
- Phase 1: `PSeedAttempt` gains `generation_seed: int` field (§D4); trace summary terminal-source test rewritten to compare hash (§D3); Phase 8 status name corrected to `compile_unchanged_exhausted` (§D11b).
- Phase 2: row dataclass gains `c_loop_fired: bool` (§D7); `p_final_failure_code` renamed to `p_terminal_failure_code` (§D7); validation rules split on `c_loop_fired` (§D7); `p_repair_attempt_count` bound is `<= p_repair_budget` (§D11a).
- Phase 4: narrative corrections (§D8) and restamp list expanded (§D9).
- Phase 5: `Cluster3RunnerConfig` gains `c_repair_budget` (§D5); control flow step 5 specifies the C-loop wrappers close over the outer C3 condition (§D6); seed handoff uses `c_repair_budget` (§D5).
- Phase 6: manifest builder source paths concretized (§D11c).
- Phase 7: `model_type` rename revoked (§D10).
- Phase 8: `status="exhausted"` → `status="compile_unchanged_exhausted"` (§D11b).
- §22 changelog extended with rows for §D1–§D11.

### D13. Revised classification

PLAN_AUDIT_VERIFIED_AND_RESOLVED — with binding §B + §C + §D revisions applied.

All twenty-seven total findings (§B1–§B7 + §C1–§C10 + §D1–§D11) now have concrete resolutions traceable to cited file paths and phase-level acceptance tests. No PENDING_DESIGN_DECISION items remain. PENDING_RESEARCH items unchanged.
