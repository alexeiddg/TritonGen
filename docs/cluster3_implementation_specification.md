# Cluster 3 Implementation Specification

- Status: Specification / not implemented (post-review revision)
- Scope: phased implementation plan, no code written
- Source plan: [docs/cluster3_implementation_plan_draft.md](docs/cluster3_implementation_plan_draft.md)
- Source audit: [audits/cluster3_implementation_plan_draft_report.md](audits/cluster3_implementation_plan_draft_report.md) plus follow-up spec patch reports through §J
- No artifacts generated, no Modal runs launched
- Resolved design decisions inherit from Part A §A2 and post-review revisions §B–§J
- PENDING_RESEARCH items kept where literature review or empirical evidence is required

> **POST-REVIEW REVISION NOTE.** Successive code reviews of earlier drafts surfaced
> the integration findings recorded in §B–§J: §B1–§B7 (handoffs to the existing Modal /
> generation / repair / sanitizer / analyzer surfaces), §C1–§C10 (seeded P and
> C handoffs, P-loop status semantics, level-gated dispatch, Cluster 3 identity
> helpers, dynamic analyzer P-pair gating, and stale specifics), and §D1–§D11
> (Phase 0/1 ordering, `c_loop_fired` split between P-terminal and row-terminal
> failure codes, `c_repair_budget` config field, C-wrapper condition-label
> capture, payload nested-identity restamping, `model_type` string preservation,
> and several spec-internal contradictions), §E1–§E12 (direct initial-F2 C
> repair, C-regression row terminals, correctness extraction, analyzer P pairs,
> P seed binding, F3 compile-evidence gating, trace summaries, pair validators,
> sanitizer drift, and P+C cost), §F1–§F10 (phase ordering, shared direct-C
> helper contract, terminal source provenance, Cluster 3 trace-summary API,
> manifest identity fields, P seed hash binding, dispatcher validation order,
> inactive-P metadata, stale test names, and analyzer wording), and §G1–§G8
> (C-loop result/provenance contract, explicit C helper `kernel_name`, C terminal
> seed preservation, trace-summary validation fields, dispatcher test corrections,
> optional/derived manifest `sample_index`, P stop reasons, and target-tree hygiene),
> and §H1–§H7 (inactive-P stop-reason policy, required P seed prompt hashes,
> C attempt-count semantics, Cluster 2-compatible C feedback builder typing,
> trace-summary validation phase split, replay-metadata contract wording, and
> dirty-tree preflight handling), and §I1–§I3 (complete P stop-reason mapping,
> concrete Phase 0 implementation report schema, and terminal prompt-hash
> provenance for C repair attempts), and §J1–§J5 (Modal image/source packaging,
> project-structure/import semantics, retry policy, timeout policy, and
> preemption/infrastructure-failure handling).
> This revision binds all findings. Where this
> document and any earlier draft disagree, this document
> wins. The §1 "Final design summary" table below reflects the revised
> contracts.

## 0. How to read this specification

Each phase is one reviewable commit. A phase is "done" when its acceptance tests pass locally on `.venv/bin/python` and all listed regression tests still pass. Phases are strictly ordered unless §13 marks them parallelizable.

Every design decision in this document traces to one of:
- An existing Cluster 2 pattern, cited by `path:line`.
- A research source already cited in the draft plan.
- Part A addendum §A2 of the audit report.

No "TODO: figure out later" remains. Items genuinely deferred for empirical evidence are explicitly marked PENDING_RESEARCH at the phase or section level.

## 1. Final design summary (binding, post-review)

Derived from Part A §A2 / §A3 and post-review revisions §B–§J. All phases below must honor these. Where a row cites a later revision item, that resolution supersedes the original §A version.

| Decision | Resolution | Source |
|---|---|---|
| F1_RUNTIME inclusion | v1 P observes `F1_COMPILE` only; F1_RUNTIME terminates | §A2.1 |
| Dispatcher location | new `cluster3/feedback/dispatcher.py` | §A2.2 |
| Failure codes | reuse canonical set in `shared/eval/failure_taxonomy.py`; add P flags, no new codes | §A2.3 |
| **Correctness runner** | **thin LOCAL adapter; no new Modal entrypoint. Calls the existing `cluster2.modal.correctness.remote_c2_correctness` Modal function. Translates condition `P/C+P → C` and `G+P/G+C+P → G+C` before the call so Level 0/1 gates fire ([cluster2/modal/correctness_runner.py:73-99](cluster2/modal/correctness_runner.py:73)). Re-stamps `condition` and `surface` back to Cluster 3 in the returned payload.** | **§B1, §B7** |
| **Generation surface** | **Cluster 3 reuses Cluster 2 generation via an explicit condition adapter `cluster3_to_cluster2_generation_condition` (`P/C+P → C`, `G+P/G+C+P → G+C`). Required because `RemoteC2GenerationRequest` rejects non-C2 conditions ([cluster2/modal/schemas.py:223-239](cluster2/modal/schemas.py:223)).** | **§B2** |
| **Modal API boundary** | **Cluster 3 v1 is a local orchestration layer over existing Cluster 2 Modal surfaces. It must not define a new `modal.App`, `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.Image.*`, `modal.Volume`, `modal.Secret`, `modal.Queue`, web endpoint, dynamic batcher, or `add_local_python_source("cluster3")`. It may import Modal lazily only through the existing Cluster 2 generation/correctness modules or test-injected callables. The existing Cluster 2 Modal decorators remain the source of truth for images, GPU, CPU, memory, timeouts, secrets, volumes, and scaling.** | **§J1 + §J2** |
| **Modal robustness policy** | **Cluster 3 v1 does not add Modal retries, `.spawn`, `.spawn_map`, `.map`, client-side `FunctionCall.get(timeout=...)`, or job-queue semantics around C2 calls. Calls stay synchronous so repair-attempt budgets remain deterministic. Generation/correctness timeouts are inherited from existing C2 decorators (`timeout=900`; correctness subprocess timeout `600s`). Modal timeout/preemption/infrastructure failures are classified as infrastructure/F3 audit events and stop paid phases unless the user explicitly authorizes a rerun/resume.** | **§J3 + §J4 + §J5** |
| Row dataclass / logger | new `Cluster3EvalRow` + `Cluster3JsonlAppendLogger`; `CLUSTER3_RESULTS_SCHEMA_VERSION = 1` | §A2.5 |
| **P success field** | **`p_repair_succeeded` is RENAMED to `p_compile_repair_succeeded` (means "P fixed Level 1 before any later C loop"). Added: `p_repair_changed_terminal_class: bool` (§C5 — neutral signal). Row's `failure_code` may be `F2_*` after `p_compile_repair_succeeded=True`; if a later C loop regresses, row-level `compile_success` may become False while the P-terminal flag remains True. The row also carries `p_terminal_failure_code`, `c_loop_fired`, `c_loop_source`, and `c_terminal_failure_code`.** | **§B3 + §C5 + §D7 + §E2** |
| **C-loop invocation** | **Cluster 3 calls `cluster2.feedback.repair_loop.run_repair_loop` through `run_cluster3_c_loop_from_f2(...)`, a shared adapter used by both direct initial-F2 and post-P-F2 paths. The helper translates `C+P → C`, `G+C+P → G+C`, uses `repair_budget=config.c_repair_budget`, takes explicit `kernel_name`, records `c_loop_source`, preserves the outer Cluster 3 condition in wrappers, accepts Cluster 2's `FeedbackCallable = Callable[[RepairFeedbackInput], str | None]` or `None`, captures C attempt seeds, and returns a Cluster 3-owned `Cluster3CLoopResult` with terminal source, hash, generation seed, prompt hash, final correctness result, C terminal status, wrapped Cluster 2 repair result, and trace fragment. `c_attempt_count` counts newly generated C repair candidates only and excludes the seed F2 candidate. Row construction uses `Cluster3CLoopResult`, not the raw Cluster 2 repair result, because `cluster2.feedback.repair_loop.RepairLoopResult` is source/provenance-light. The adapter never exposes P compile-error feedback or private eval shapes to C. Required because `run_repair_loop` rejects non-C2 conditions ([cluster2/feedback/repair_loop.py:125-143](cluster2/feedback/repair_loop.py:125)). Row's recorded condition stays Cluster 3.** | **§B4 + §E1 + §F2 + §G1 + §G2 + §G3 + §H3 + §H4** |
| Prompt template | 6-section: Base task, Previous source, Failure code, Feedback, Compile error, Instruction | §A2.6 |
| Compile-error excerpt cap | 2000 chars after redaction; head-keep, tail-truncate; `p_raw_error_excerpt_sha256` of full text | §A2.6 |
| Diagnostic note | deterministic template `build_compile_diagnostic_note(...)` | §A2.6 |
| **P sanitizer** | **NEW Cluster 3 module `cluster3/feedback/sanitizer.py` with its own term list. Does NOT import or monkeypatch `cluster2.feedback.prompts`. Term list = Cluster 2's `FORBIDDEN_FEEDBACK_TERMS` ([cluster2/feedback/prompts.py:25-48](cluster2/feedback/prompts.py:25)) minus `{"LLVM", "PTX"}`.** | **§B5** |
| Repair budget | `DEFAULT_P_REPAIR_BUDGET = 5` (matches Cluster 2's `DEFAULT_REPAIR_BUDGET`); CLI accepts 0..5 | [cluster2/constants.py:33](cluster2/constants.py:33) |
| History policy | conversational history across attempts, deterministic truncation (mirrors Self-Refine) | draft §12 |
| **Analyzer column** | **Phase 7a (in v1): ADD `compile_feedback_active` column populated identically to `perf_feedback_active` ([factorial.py:1069](shared/analysis/factorial.py:1069)). The factorial model uses `compile_feedback_active` for the P term; `perf_feedback_active` is preserved for backward compatibility with `outputs/analysis/factorial_2x2_preliminary.json`. Phase 7b (deferred to a separate PR, OUT OF SCOPE for v1): remove `perf_feedback_active`.** | **§B6** |
| **Analyzer pair gating** | **Do NOT extend `PAIRED_REPLAY_COMPARISONS` as a module constant. Add `P_PAIRED_REPLAY_COMPARISONS` and `effective_paired_replay_comparisons(populated_cells)`; metadata at [factorial.py:452-458](shared/analysis/factorial.py:452) and row builder at [factorial.py:1620-1627](shared/analysis/factorial.py:1620) iterate the helper. Preserves byte-identical 2² metadata and avoids ValueError on missing P cells under `primary_functional` scope.** | **§C8** |
| **P-loop seed handoff** | **P loop accepts `PSeedAttempt` carrying initial source, generation/base/sample/kernel identity including `kernel_name`, source hash, required prompt hash, optional stored prompt text, and already-computed evaluation result. `source_hash == sha256(source)` is required; `prompt_hash` is required for new Cluster 3 seeds and must either equal `sha256(prompt)` when prompt text is stored or equal the prompt-construction metadata hash when prompt text is not stored. Loop does NOT call `generation` or `evaluation` for attempt 0; uses cached result directly and validates F1 compile evidence before entry.** | **§C1 + §E7 + §F6 + §H2** |
| **P-to-C seed handoff** | **When the C loop fires after P repair, the orchestrator calls `run_cluster3_c_loop_from_f2(..., c_loop_source="post_p_f2", seed_candidate_source=<p_terminal_source>, seed_candidate_generation_seed=<p terminal seed>, seed_candidate_evaluation=<cached F2>)`. The helper wraps `evaluation` to return the cached F2 result for attempt 0. No regeneration or re-eval of the P-terminal candidate. If no C attempt is generated, terminal seed/source remain the P terminal seed/source; if C attempt N becomes terminal, terminal seed/source come from C attempt N.** | **§C2 + §F2 + §G3** |
| **P-loop status enum** | **`compile_repaired_then_success`, `compile_repaired_f2_observed`, `post_p_f3_observed`, `compile_unchanged_exhausted`, `terminated_unrecoverable`. `PRepairLoopResult.stop_reason` is always populated before return. The exact stop-reason table maps success to `p_compile_repaired_then_success`, F2 observation to `p_compile_repaired_f2_observed`, budget exhaustion to `p_budget_exhausted`, post-P F3 by compile evidence (`p_post_compile_f3_observed` vs `p_f3_without_compile_evidence`), and F0/F1_RUNTIME terminals to `p_terminal_non_repairable`. Inactive/no-P rows, including direct initial-F2 C rows, record `p_repair_stop_reason="p_not_applicable"`; `p_repair_stop_reason` is always populated. Unknown P statuses are validation errors, not defaults. The orchestrator decides whether to chain to C based on status and evidence.** | **§C3 + §E8 + §G7 + §H1 + §I1** |
| **Dispatcher signature** | **`dispatch(condition, failure_code, level_reached, *, functional_success=None)`. It validates the condition, active factors, known failure code, and failure-code/level compatibility before any success or terminal shortcut. Requires `level_reached >= 2` for C routing, `level_reached == 1` for P routing.** | **§C4 + §F7** |
| **Terminal-code schema** | **`initial_failure_code` is the pre-repair classification. `p_initial_failure_code` / `p_terminal_failure_code` describe the P loop only. `c_terminal_failure_code` describes the C loop only. Row-level `failure_code` is the final terminal outcome after all active loops: P terminal when only P fires, C terminal when C fires, initial terminal when no loop fires. Field `p_repair_changed_outcome` is RENAMED to `p_repair_changed_terminal_class` (neutral signal, not "P helped").** | **§C5 + §E2 + §E3** |
| **Terminal source provenance** | **Every generated row records the terminal source explicitly: `terminal_source_stage`, `terminal_generation_seed`, `terminal_attempt_index`, `terminal_source_hash`, `terminal_prompt_hash`, `terminal_prompt_hash_source`, and `terminal_source_matches_row_source`. Row source/hash and `generated_metadata.generation_seed` point to the terminal source, not blindly to the initial generation. Generated C repair attempts compute `terminal_prompt_hash = sha256(RepairGenerationInput.prompt)` in the Cluster 3 wrapper. P-terminal source fields remain distinct when a later C attempt regresses.** | **§F3 + §I3** |
| **Trace summary API** | **Cluster 3 defines `Cluster3TraceSummary` in `cluster3/feedback/trace.py`. It is JSON serializable, source-free, private-eval-free, and carries P/C loop status, terminal source stage, terminal source hash, terminal generation/prompt hashes, final success flags, attempt counts, terminal codes, and a compact `failure_path`. Phase 1 validates only self-contained summary invariants; Phase 2 row schema validates `trace_summary` against row terminal provenance, generated metadata, and final outcome fields.** | **§E9 + §F4 + §G4 + §H5** |
| **Pair identity validator phase** | **The public `validate_pair_identity` and `pair_for_condition` live in Phase 5 under `cluster3/replay/no_p_pairs.py` because the runner uses them. Phase 6 only builds/loads the manifest and supplies artifact rows for that validator. Cluster 3 may call Cluster 2 primitive checks, but not the Cluster 2 private full pairing-context validator.** | **§E10 + §F1** |
| **Cluster 3 identity helpers** | **`source_class_for_cluster3_condition` (always `GENERATED_SOURCE_CLASS`) and `generation_mode_for_cluster3_condition` (delegates to Cluster 2's helper after `cluster3_to_cluster2_generation_condition` translation) live in `cluster3/constants.py`.** | **§C6** |
| Schema field set | §A3 table, amended by §B3 and §C5 (rename) | §A3 + §B3 + §C5 |

## 2. Final file tree (target)

```
cluster3/
├── README.md                                  (modify: replace TBD scope with compile-error scope)
├── __init__.py                                (existing)
├── constants.py                               (new, Phase 0)
├── contracts/
│   └── no_p_pair_manifest.json                (new, Phase 6; schema file/empty manifest)
├── data/
│   ├── kernels/__init__.py                    (existing)
│   └── prompts/__init__.py                    (existing)
├── experiments/
│   ├── __init__.py                            (existing)
│   └── run_cluster3_modal.py                  (new, Phase 5)
├── feedback/
│   ├── __init__.py                            (new, Phase 1)
│   ├── c_loop_adapter.py                      (new, Phase 5; shared direct-F2 C helper)
│   ├── compile_error_repair.py                (new, Phase 1)
│   ├── condition_adapters.py                  (new, Phase 1; §B2 + §B4)
│   ├── dispatcher.py                          (new, Phase 3)
│   ├── prompts.py                             (new, Phase 1)
│   ├── sanitizer.py                           (new, Phase 1; §B5 — does not import cluster2)
│   └── trace.py                               (new, Phase 1)
├── generation/__init__.py                     (existing; unused in v1)
├── modal/
│   ├── __init__.py                            (new, Phase 4)
│   ├── correctness_runner.py                  (new LOCAL adapter, Phase 4; §B7 — no new Modal entrypoint)
│   └── result_extraction.py                   (new, Phase 4; Cluster 3-owned correctness-result extraction)
├── notebooks/.gitkeep                         (existing)
├── profiling/__init__.py                      (existing; unused in v1)
├── results/
│   ├── __init__.py                            (existing)
│   ├── dataclass.py                           (new, Phase 2)
│   └── logger.py                              (new, Phase 2)
├── reward/__init__.py                         (existing; unused in v1)
├── replay/
│   ├── __init__.py                            (new, Phase 5)
│   ├── build_no_p_pair_manifest.py            (new, Phase 6; manifest builder)
│   └── no_p_pairs.py                          (new, Phase 5; public pair identity validator)
├── tests/
│   ├── __init__.py                            (existing)
│   ├── test_cluster3_imports.py               (new, Phase 0)
│   ├── test_p_prompts.py                      (new, Phase 1)
│   ├── test_p_repair_loop.py                  (new, Phase 1)
│   ├── test_cluster3_schema.py                (new, Phase 2)
│   ├── test_cluster3_logger.py                (new, Phase 2)
│   ├── test_dispatcher.py                     (new, Phase 3)
│   ├── test_condition_adapters.py             (new, Phase 1; §B2 + §B4)
│   ├── test_correctness_runner_adapter.py     (new, Phase 4)
│   ├── test_run_cluster3_modal_cli.py         (new, Phase 5)
│   ├── test_p_sanitizer.py                    (new, Phase 1; §B5)
│   ├── test_replay_pairing.py                 (new, Phase 5/6)
│   ├── test_cluster3_trace.py                 (new, Phase 1)
│   ├── test_p_repair_f1_fixtures.py           (new, Phase 8)
│   ├── test_cluster3_boundary.py              (new, Phase 9)
│   ├── test_analyzer_cluster3.py              (new, Phase 7, may live under shared/tests if convention)
│   └── fixtures/
│       └── f1_compile_kernels/                (new, Phase 8: curated broken kernels)
└── validation/__init__.py                     (existing; unused in v1)
```

Compared to `cluster2/`:
- `cluster3/feedback/` mirrors `cluster2/feedback/` but adds `dispatcher.py`, `condition_adapters.py`, and `sanitizer.py`, and replaces `repair_loop.py` semantics with `compile_error_repair.py`.
- `cluster3/modal/correctness_runner.py` is a LOCAL adapter, not a new Modal entrypoint (§B7). It calls the existing `cluster2.modal.correctness.remote_c2_correctness` Modal function on the existing image. No new `@app.function`, no new image, no `add_local_python_source("cluster3")` in v1.
- `cluster3/results/` mirrors `cluster2/results/` with a new schema version.
- `cluster3/generation/` is intentionally empty in v1: P composes with the existing C generation surface (`cluster2/generation/`) for all four Cluster 3 conditions. Condition is translated via `cluster3_to_cluster2_generation_condition` before constructing each `RemoteC2GenerationRequest` (§B2). Model/tokenizer revisions stay identical to the existing Cluster 1 / Cluster 2 pinning.

## 3. Sequencing dependencies

Strictly ordered phases:
- Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12.

Parallelizable pairs (after Phase 2 merges):
- Phase 3 (dispatcher) can run in parallel with Phase 4 (correctness runner adapter).
- Phase 6 (replay manifest) can run in parallel with Phase 7 (analyzer updates) after Phase 5.
- Phase 8 (F1 fixture smoke) and Phase 9 (boundary tests) can run in parallel after Phase 5.

Strict ordering rationale: the row schema (Phase 2) is consumed by every later phase, so its dataclass must land first. The Modal phases (11, 12) require explicit user approval and are gated on Phase 0..10 passing.

## 4. Phase pre-flight checklist (applies to every phase)

Before starting any phase:
1. Run `git status --short` and record the exact output in the phase report as `preflight_git_status`.
   - If the tree is dirty, classify every dirty path as one of: expected prior-doc/spec/audit change, unrelated tracked code change, artifact/output change, or unknown.
   - The phase may proceed only when every dirty path is known, in scope, and documented in `known_dirty_paths` in the phase report.
   - Phase 0 must not silently build on unreviewed Cluster 2 code changes, artifact/output changes, or unknown tracked changes. Unrelated code/artifact changes require explicit acknowledgement before implementation starts.
2. The phase's listed "Dependencies on prior phases" are all merged on `main`.
3. `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests -x` is green on `main` at the start of the phase.
4. No changes have been made to `cluster1/`, frozen artifacts under `outputs/cluster1/`, `outputs/cluster2/`, or `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` unless the phase explicitly authorizes such changes.
5. The phase's "Files that should not be modified" set is honored.

## 5. Phase 0 — Cluster 3 scaffolding

**Purpose.** Establish the `cluster3/` skeleton so later phases land into existing module paths without cross-cutting `__init__` churn.

**Files to add.**
- `cluster3/constants.py`:
  - `CLUSTER3_CONDITIONS: tuple[str, ...] = ("P", "G+P", "C+P", "G+C+P")`
  - `P_GENERATION_CONDITIONS: tuple[str, ...] = CLUSTER3_CONDITIONS`
  - `DEFAULT_P_REPAIR_BUDGET: int = 5` (matches `cluster2/constants.py:33`)
  - `P_ELIGIBLE_FAILURE_CODES: frozenset[str] = frozenset({"F1_COMPILE"})`
  - `P_FEEDBACK_FORMAT_V1: str = "compile_error_template_v1"`
  - `P_HISTORY_POLICY_V1: str = "last_attempt_only_v1"`
  - `P_REPAIR_STOP_REASONS: frozenset[str] = frozenset({"p_compile_repaired_then_success", "p_budget_exhausted", "p_compile_repaired_f2_observed", "p_post_compile_f3_observed", "p_f3_without_compile_evidence", "p_terminal_non_repairable", "p_not_applicable"})`
  - `normalize_cluster3_condition(value: str) -> str` — accepts only `CLUSTER3_CONDITIONS`; raises `ValueError` otherwise. Mirrors `cluster2.constants.normalize_cluster2_condition`.
  - **§C6 + §D1 identity helpers.** The condition mapping tables live HERE in `cluster3/constants.py` (Phase 0), so the helpers do NOT import any Phase 1 module:
    - `_CLUSTER3_TO_CLUSTER2_GENERATION: dict[str, str] = {"P": "C", "C+P": "C", "G+P": "G+C", "G+C+P": "G+C"}` — private.
    - `_CLUSTER3_TO_CLUSTER2_REPAIR: dict[str, str] = {"C+P": "C", "G+C+P": "G+C"}` — private.
    - `source_class_for_cluster3_condition(condition: str) -> str` — validates input via `normalize_cluster3_condition` and returns `cluster2.constants.GENERATED_SOURCE_CLASS` (= `"generated_row"`, see [cluster2/constants.py:15, 27](cluster2/constants.py:15)). All four Cluster 3 conditions produce fresh sources.
    - `generation_mode_for_cluster3_condition(condition: str) -> str` — validates input, looks up `_CLUSTER3_TO_CLUSTER2_GENERATION[condition]`, then calls `cluster2.constants.generation_mode_for_condition(<translated>)`. Mappings: `P/C+P → C_GENERATION_MODE`; `G+P/G+C+P → G_PLUS_C_GENERATION_MODE`. Phase 1 `condition_adapters.py` will re-export the same tables and offer the public `cluster3_to_cluster2_*_condition` helper API, with a Phase 1 conformance test that the Phase 1 tables equal the Phase 0 constants.

**Files to modify.**
- `cluster3/__init__.py` — keep empty; do not eagerly import heavy submodules.

**Tests to add.**
- `cluster3/tests/test_cluster3_imports.py`:
  - `test_cluster3_package_imports_cheap` — asserts that `import cluster3` and `import cluster3.constants` do not import `torch`, `triton`, `transformers`, `xgrammar`, `modal`. Mirrors `cluster1`/`cluster2` local-imports convention.
  - `test_cluster3_constants_contract` — asserts the exact tuples/frozensets/strings above.
  - `test_cluster3_allowed_cells_match_registry` — asserts `CLUSTER3_CONDITIONS == shared.factors.registry.allowed_cells_for_cluster("cluster3")` (matches [registry.py:17](shared/factors/registry.py:17)).
  - `test_source_class_for_cluster3_condition_returns_generated_for_all_p_cells` (§C6) — all four Cluster 3 conditions return `GENERATED_SOURCE_CLASS`.
  - `test_generation_mode_for_cluster3_condition_matches_c2_after_translation` (§C6) — `P → C_GENERATION_MODE`, `C+P → C_GENERATION_MODE`, `G+P → G_PLUS_C_GENERATION_MODE`, `G+C+P → G_PLUS_C_GENERATION_MODE`.
  - `test_source_class_for_cluster3_condition_rejects_non_cluster3` — `"none"`, `"C"`, `"G+C"` raise.
  - `test_phase0_report_exposes_dirty_tree_fields` (§H7 + §I2) — the Phase 0 report exposes the machine-checkable labels `preflight_git_status:`, `known_dirty_paths:`, and `unexpected_dirty_paths:`. The pytest check validates report structure only; it does not try to reconstruct the pre-implementation `git status --short` output.
  - `test_phase0_report_dirty_path_semantics_marked_for_audit` (§H7 + §I2) — the report contains the fields needed for human/audit review of dirty-path classifications. Semantic correctness of the captured preflight status and dirty-path acknowledgement is an audit responsibility, not a pytest reconstruction.
  - `test_phase0_report_file_exists` (§I2) — `audits/cluster3_phase0_scaffolding_report.md` exists after Phase 0.
  - `test_phase0_report_includes_required_headings` (§I2) — the report contains all required markdown headings listed below.
  - `test_phase0_report_includes_preflight_git_status_field` (§I2) — the report contains the machine-checkable label `preflight_git_status:`.
  - `test_phase0_report_includes_known_dirty_paths_field` (§I2) — the report contains the machine-checkable label `known_dirty_paths:`.
  - `test_phase0_report_classification_is_allowed_value` (§I2) — `classification:` is one of the allowed Phase 0 classification values.

**Phase 0 required report output (§I2).**
- Path: `audits/cluster3_phase0_scaffolding_report.md`.
- Phase 0 pytest tests may read this markdown file and assert that required headings, field labels, and an allowed classification are present. Semantic review of dirty-path classification may remain a human/audit check, but the report must expose the data in a consistent format.
- Required markdown headings:
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
- Required machine-checkable field labels:
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
- Allowed `classification:` values:
  - `PHASE0_SCAFFOLDING_COMPLETE`
  - `PHASE0_SCAFFOLDING_COMPLETE_WITH_WARNINGS`
  - `PHASE0_BLOCKED_DIRTY_TREE`
  - `PHASE0_BLOCKED_TEST_FAILURE`
  - `PHASE0_SURFACE_REGRESSION`
- If `preflight_git_status:` is non-empty, Phase 0 must populate `known_dirty_paths:` with each known dirty path and `unexpected_dirty_paths:` with any dirty path that is not expected or acknowledged. If unrelated code/artifact changes are present and unacknowledged, Phase 0 must classify as `PHASE0_BLOCKED_DIRTY_TREE`.
- Phase 0 pytest tests validate that the report artifact exists and exposes these field labels. They do not compare `preflight_git_status:` to the current working tree after implementation, because that later state cannot reliably reconstruct the pre-implementation status. Review of the captured value and dirty-path classification remains a human/audit check.

**Tests that must pass.**
- The Phase 0 tests above.

**Regression check.**
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests` — must remain green.

**Estimated complexity.** Small (~1 agent-hour).

**Dependencies on prior phases.** None.

**Files that should not be modified.** Everything outside `cluster3/`, except the required Phase 0 report artifact `audits/cluster3_phase0_scaffolding_report.md`.

**Commit message template.**
```
cluster3: phase 0 — package scaffolding and constants

Adds cluster3/constants.py with CLUSTER3_CONDITIONS, DEFAULT_P_REPAIR_BUDGET,
P_ELIGIBLE_FAILURE_CODES, and helpers, plus a smoke import test that locks the
package's local-import contract. No P logic yet.
```

**Risk + mitigation.** Risk: accidental heavy import via `cluster3/__init__.py` masking the local-import test. Mitigation: keep `__init__.py` empty; rely on the import test to fail loudly if anything changes.

## 6. Phase 1 — P repair loop, prompts, trace (local only)

**Purpose.** Implement the P repair orchestration with deterministic feedback prompt construction. No Modal, no real generation.

**Files to add.**
- `cluster3/feedback/__init__.py` — empty.
- `cluster3/feedback/trace.py`:
  - `PRepairAttemptSummary` frozen dataclass: `attempt_index: int`, `generation_seed: int`, `compile_success: bool | None`, `failure_code: str | None`, `compile_error_class: str | None`, `source_hash: str | None`, `feedback_sha256: str | None`.
  - `build_p_attempt_summary(...)` — mirrors [cluster2/feedback/trace.py: build_trace_summary](cluster2/feedback/trace.py) shape.
  - `Cluster3TraceSummary` frozen dataclass (§E9 + §F4), source-free and JSON serializable:
    - `condition: str`
    - `initial_failure_code: str | None`
    - `final_failure_code: str | None`
    - `p_loop_fired: bool`
    - `p_attempt_count: int`
    - `p_terminal_failure_code: str | None`
    - `p_compile_repair_succeeded: bool`
    - `c_loop_fired: bool`
    - `c_loop_source: Literal["none", "initial_f2", "post_p_f2"]`
    - `c_attempt_count: int`
    - `c_terminal_failure_code: str | None`
    - `terminal_source_stage: str`
    - `terminal_attempt_index: int | None`
    - `terminal_source_hash: str`
    - `terminal_generation_seed: int`
    - `terminal_prompt_hash: str | None`
    - `terminal_prompt_hash_source: Literal["initial_prompt", "p_repair_prompt", "c_repair_prompt", "seed_prompt_metadata", "seed_prompt_unavailable"]`
    - `compile_success: bool`
    - `functional_success: bool`
    - `repair_set_success: bool | None`
    - `eval_set_success: bool | None`
    - `row_source_hash: str`
    - `failure_path: list[str]`
    - `private_eval_data_included: Literal[False]`
  - `Cluster3TraceSummary` Phase 1 validation is self-contained because the row dataclass does not exist yet: condition must be a Cluster 3 condition; attempt counts are non-negative; `c_loop_source="none"` iff `c_loop_fired=False`; `private_eval_data_included` must be exactly `False`; failure-code fields must be canonical or None; `terminal_source_hash`, `row_source_hash`, and any present `terminal_prompt_hash` are valid sha256 strings; `terminal_prompt_hash_source` must be one of the allowed provenance markers; `terminal_prompt_hash is None` is allowed only when `terminal_prompt_hash_source == "seed_prompt_unavailable"`; final success flags are booleans; and `failure_path` contains compact labels only (for example `"initial:F1_COMPILE"`, `"p_attempt:1:F2_NUMERIC_LARGE"`, `"c_seed:F2_NUMERIC_LARGE"`, `"c_attempt:2:success"`), never raw source, raw correctness payloads, private shape data, or full compile logs. Row-vs-trace cross-checks are Phase 2 schema responsibilities.
  - `Cluster3TraceSummary.c_attempt_count` semantics (§H3): counts newly generated C repair candidates only and excludes the seed F2 candidate. If C does not fire, `c_attempt_count=0`. If C fires with `c_repair_budget=0`, `c_attempt_count=0`. If C fires and generates N repair candidates, `c_attempt_count=N`. When C fires, the C portion of `failure_path` includes the seed F2 candidate plus generated repair attempts, so its path length is `c_attempt_count + 1`.
  - `build_cluster3_trace_summary(...) -> Cluster3TraceSummary` — builds the terminal whole-row summary from the initial result, optional P loop result, optional C loop result, and terminal source provenance. It must distinguish no-repair, P-only, direct initial-F2 C, and P-to-F2-to-C paths.
- `cluster3/feedback/sanitizer.py` (§B5 — self-contained; does NOT import `cluster2.feedback.prompts`):
  - `P_FORBIDDEN_FEEDBACK_TERMS: tuple[str, ...]` = Cluster 2's `FORBIDDEN_FEEDBACK_TERMS` at [cluster2/feedback/prompts.py:25-48](cluster2/feedback/prompts.py:25), **minus** `{"LLVM", "PTX"}`. Copied verbatim, not imported.
  - `P_SENSITIVE_DETAIL_PATTERNS` = Cluster 2's `_SENSITIVE_DETAIL_PATTERNS` at [cluster2/feedback/prompts.py:87-98](cluster2/feedback/prompts.py:87). Copied verbatim.
  - `_term_pattern(term)`, `_FORBIDDEN_PATTERNS` — local copies of the Cluster 2 regex-builder logic at [cluster2/feedback/prompts.py:75-86](cluster2/feedback/prompts.py:75) applied to `P_FORBIDDEN_FEEDBACK_TERMS`.
  - Public `sanitize_p_feedback_text(value: str | None, *, limit: int | None = 2000) -> str` — head-keep, tail-truncate behavior matching the §A2.6 contract.
  - Public `validate_no_forbidden_p_terms(value: str) -> None` — raises `ValueError(f"feedback contains forbidden term: {term}")` on match.
  - Module-level constant `LLVM_PTX_ALLOWED: bool = True` for explicit documentation; not used at runtime.
  - Drift contract (§E11): production Cluster 3 keeps this independent config, but tests compare the current Cluster 2 term list to `P_FORBIDDEN_FEEDBACK_TERMS ∪ {"LLVM", "PTX"}` by importing or AST-reading the live Cluster 2 constant. The comparison is intentional: if Cluster 2 changes its forbidden terms, Cluster 3 must consciously accept or adapt the P-specific divergence.
- `cluster3/feedback/condition_adapters.py` (§B2 + §B4 + §D1):
  - Re-exports `_CLUSTER3_TO_CLUSTER2_GENERATION` and `_CLUSTER3_TO_CLUSTER2_REPAIR` from `cluster3.constants` (single source of truth lives in Phase 0).
  - `cluster3_to_cluster2_generation_condition(c3_condition: str) -> str` — looks up the Phase 0 generation table; raises `ValueError` for any input not in `CLUSTER3_CONDITIONS`.
  - `cluster3_to_cluster2_eval_condition(c3_condition: str) -> str` — table identical to the generation one (Cluster 2's eval surface uses the same condition labels).
  - `cluster3_to_cluster2_repair_condition(c3_condition: str) -> str` — looks up `_CLUSTER3_TO_CLUSTER2_REPAIR`; raises for `"P"` or `"G+P"` (those conditions cannot invoke C repair).
  - `restamp_cluster3_condition(payload_or_result: dict | object, c3_condition: str) -> None` (§D9 + §E4) — in-place re-stamp of:
    - top-level `surface` → `"c3_remote_correctness"`,
    - top-level `condition` (if present),
    - `identity.condition`,
    - `source_identity.condition`,
    - `eval_identity.condition` (if `eval_identity` carries one),
    - **`correctness_result.identity.condition` only when `correctness_result` exists and is a normal success/failure payload.** Cluster 2 infrastructure failures at [cluster2/modal/correctness_runner.py:332-388](cluster2/modal/correctness_runner.py:332) validly omit `correctness_result`; the restamp preserves those payloads, restamps available wrapper sidecars, and does not index a missing nested result.
  - Phase 1 test `test_condition_adapter_tables_match_constants` (§D1) asserts these tables equal the Phase 0 private constants.
- `cluster3/feedback/prompts.py`:
  - `P_SECTION_ORDER = ("Base task", "Previous source", "Failure code", "Feedback", "Compile error", "Instruction")`.
  - `P_COMPILE_ERROR_EXCERPT_CHARS = 2000` (§A2.6).
  - `build_compile_diagnostic_note(failure_code: str, compile_error_type: str | None, compile_error: str | None) -> str` — pure deterministic template; returns a one-sentence human description of the failure class without proposing a patch. Lookup table keyed on `(failure_code, compile_error_type or "UnknownError")` with a default fallback string. No model call.
  - `build_p_feedback_prompt(base_prompt, candidate_source, failure_code, compile_error, compile_error_type) -> str | None` — returns `None` if `failure_code not in P_ELIGIBLE_FAILURE_CODES`; otherwise builds the six-section prompt. Uses ONLY `cluster3.feedback.sanitizer.sanitize_p_feedback_text` and `validate_no_forbidden_p_terms` (§B5). Does not import `cluster2.feedback.prompts`.
  - `excerpt_compile_error(compile_error: str | None, *, limit: int = P_COMPILE_ERROR_EXCERPT_CHARS) -> tuple[str, str]` — returns `(excerpt, sha256_of_full)`. Head-keep, tail-truncate.
- `cluster3/feedback/compile_error_repair.py` (§C1, §C3, §D4, §E7, §E8, §F6 binding):
  - `PSeedAttempt` frozen dataclass (§C1 + §D4 + §E7 + §F6 + §H2): `source: str`, `generation_seed: int` (§D4 — the seed under which the seed candidate was originally generated), `base_seed: int`, `sample_index: int`, `kernel_class: str`, `kernel_name: str`, `dtype: str`, `source_hash: str`, `prompt_hash: str`, `prompt: str | None`, `evaluation_result: object` (the cached attempt-0 eval), `failure_code: str` (must be in `P_ELIGIBLE_FAILURE_CODES`), `compile_error: str | None`, `compile_error_type: str | None`. Validation in `__post_init__`: source non-empty; `generation_seed >= 0`; `base_seed >= 0`; `sample_index >= 0`; identity fields non-empty; `source_hash` valid sha256 and equal to `sha256(source)`; `prompt_hash` is required and must be a valid sha256; if `prompt` is stored, `prompt_hash == sha256(prompt)`; if prompt text is not stored, `prompt_hash` must equal the prompt construction metadata hash; failure_code in `P_ELIGIBLE_FAILURE_CODES`.
  - `PSeedAttempt` parent binding (§F6 + §H2): `generation_seed`, `base_seed`, `sample_index`, `kernel_class`, `kernel_name`, `dtype`, `source_hash`, and `prompt_hash` must match the parent initial row/control identity and prompt construction metadata used to generate and evaluate the seed. Mismatch raises before the P loop starts.
  - `PSeedAttempt` evaluation binding (§E7): if `failure_code == "F1_COMPILE"`, `evaluation_result` must classify as Level 1 compile failure: `level_reached == 1` or equivalent, `compile_success is False`, and either `compile_error_type` or `compile_error` / `compile_error_excerpt` is present. If the declared `failure_code` differs from the evaluation result's classification, construction raises. This prevents synthetic P seeds that claim F1 without compile-error evidence.
  - `PRepairLoopResult` frozen dataclass (mirrors [cluster2/feedback/repair_loop.py:87-114](cluster2/feedback/repair_loop.py:87)) with the **§C3 + §E8 status enum**: `status` ∈ `{"compile_repaired_then_success", "compile_repaired_f2_observed", "post_p_f3_observed", "compile_unchanged_exhausted", "terminated_unrecoverable"}`. Other fields: `attempts: tuple[PRepairAttemptSummary, ...]`, `attempts_executed: int`, `successful_attempt_index: int | None`, `repair_budget: int`, `initial_failure_code: str`, `final_failure_code: str | None`, `stop_reason: str`, `terminal_source: str`, `terminal_attempt_index: int`, `terminal_generation_seed: int`, `terminal_source_hash: str`, `terminal_compile_success: bool | None`, `terminal_level_reached: int | None` (needed by the orchestrator to decide whether a post-P F3 actually repaired Level 1 and to populate §F3 terminal provenance).
  - `P_REPAIR_STATUS_TO_STOP_REASON` contract (§G7 + §I1): every P terminal status maps to exactly one stop reason, and `PRepairLoopResult.stop_reason` must be populated before return. Unknown P loop status or missing evidence for an evidence-dependent status is a validation error, not a default.

    | P terminal status / evidence | `PRepairLoopResult.stop_reason` / row `p_repair_stop_reason` |
    |---|---|
    | `compile_repaired_then_success` | `p_compile_repaired_then_success` |
    | `compile_repaired_f2_observed` | `p_compile_repaired_f2_observed` |
    | `post_p_f3_observed` with compile evidence (`terminal_compile_success is True` or `terminal_level_reached >= 2`) | `p_post_compile_f3_observed` |
    | `post_p_f3_observed` without compile evidence (`terminal_compile_success is False` and `terminal_level_reached < 2`) | `p_f3_without_compile_evidence` |
    | `compile_unchanged_exhausted` (semantic class: budget exhausted) | `p_budget_exhausted` |
    | `terminated_unrecoverable` for `failure_code.startswith("F0_")` or `failure_code == "F1_RUNTIME"` (semantic class: terminal non-repairable) | `p_terminal_non_repairable` |
    | no P fired / inactive P | `p_not_applicable` |

  - `run_p_repair_loop(*, base_prompt, base_seed, generation, evaluation, seed_attempt: PSeedAttempt, repair_budget: int = DEFAULT_P_REPAIR_BUDGET) -> PRepairLoopResult` (§C1 binding — `seed_attempt` is **required**; replaces the old `seed_candidate_source`):
    1. **Attempt 0 is the seed**: do NOT call `generation`; do NOT call `evaluation`. Record `seed_attempt.source` and `seed_attempt.evaluation_result` as attempt-0 in the trace. `initial_failure_code = seed_attempt.failure_code`.
    2. For `attempt_index` in `1..repair_budget`: build feedback from the prior attempt; call `generation`; call `evaluation`. Classify the new failure code.
       - `failure_code is None` AND `compile_success is True` AND Level 2 passed → return `status="compile_repaired_then_success"`, `stop_reason="p_compile_repaired_then_success"`, `successful_attempt_index=attempt_index`, `final_failure_code=None`.
       - `failure_code in {"F2_NUMERIC_LARGE","F2_NUMERIC_NAN","F2_SHAPE_MISMATCH"}` (compile passed, Level 2 failed) → return `status="compile_repaired_f2_observed"`, `stop_reason="p_compile_repaired_f2_observed"`, `final_failure_code=<F2 code>`. The orchestrator chains to the C loop (§C2) if condition contains C, else terminates.
       - `failure_code` starts with `F3_` → return `status="post_p_f3_observed"`, `stop_reason="p_post_compile_f3_observed"` when the terminal evidence has `compile_success=True` or `level_reached>=2`, otherwise `stop_reason="p_f3_without_compile_evidence"`, `final_failure_code=<F3 code>`, and preserve the post-P compile evidence (`terminal_compile_success`, `terminal_level_reached`). This status does **not** by itself prove Level 1 was repaired; the orchestrator sets `p_compile_repair_succeeded=True` only when compile evidence exists.
       - `failure_code.startswith("F0_")` or `failure_code == "F1_RUNTIME"` → return `status="terminated_unrecoverable"` with `stop_reason="p_terminal_non_repairable"`, `final_failure_code=<that code>`.
       - `failure_code == "F1_COMPILE"` AND `attempt_index < repair_budget` → continue.
       - `failure_code == "F1_COMPILE"` AND `attempt_index == repair_budget` → return `status="compile_unchanged_exhausted"`, `stop_reason="p_budget_exhausted"`, `final_failure_code="F1_COMPILE"`.
    3. `terminal_source` always = the last recorded attempt's source.
  - `seed_for_p_attempt(base_seed, attempt_index) -> int` — same `base_seed * 10 + attempt_index` formula as [cluster2/feedback/repair_loop.py:286-291](cluster2/feedback/repair_loop.py:286) so paired Cluster 1 / 2 / 3 seeds remain comparable. Used for attempts 1..repair_budget; attempt 0 uses whatever seed the seed_attempt was generated under.

**Files to modify.** None.

**Tests to add.**
- `cluster3/tests/test_p_sanitizer.py` (§B5):
  - `test_cluster3_sanitizer_terms_match_cluster2_current_terms` (§E11) — imports or AST-reads the current `cluster2.feedback.prompts.FORBIDDEN_FEEDBACK_TERMS` and asserts `set(P_FORBIDDEN_FEEDBACK_TERMS) == set(cluster2_terms) - {"LLVM", "PTX"}`. This fails when Cluster 2 sanitizer terms change and Cluster 3 is not consciously updated.
  - `test_validate_no_forbidden_p_terms_rejects_speedup` — raises.
  - `test_validate_no_forbidden_p_terms_rejects_profil_token_benchmark` — raises.
  - `test_validate_no_forbidden_p_terms_allows_llvm` — `"LLVM ERROR at ..."` passes.
  - `test_validate_no_forbidden_p_terms_allows_ptx` — `"PTX assembler failed"` passes.
  - `test_sanitize_p_feedback_text_redacts_eval_set_details` — `"eval_shape_set leaks"` → `"[redacted]"`.
  - `test_sanitize_p_feedback_text_truncates_to_limit` — 5000-char input truncates to 2000.
- `cluster3/tests/test_condition_adapters.py` (§B2 + §B4):
  - `test_generation_adapter_maps_p_to_c_and_gp_to_gc` — assert `{"P": "C", "C+P": "C", "G+P": "G+C", "G+C+P": "G+C"}`.
  - `test_generation_adapter_rejects_unknown_condition` — `"none"`, `"C"`, `"G"`, `"G+C"`, `"X"` all raise.
  - `test_eval_adapter_matches_generation_adapter` — same four mappings (§B1).
  - `test_repair_adapter_maps_cp_and_gcp` — `{"C+P": "C", "G+C+P": "G+C"}`.
  - `test_repair_adapter_rejects_p_and_gp` — P and G+P raise (no C invocation).
  - `test_restamp_cluster3_condition_overwrites_returned_payload` — given a payload with `condition="C"` and `surface="c2_remote_correctness"`, restamping to `"P"` produces `condition="P"` and `surface="c3_remote_correctness"`.
- `cluster3/tests/test_p_prompts.py`:
  - `test_excerpt_compile_error_truncates_tail_keeps_head` — 3000-char input yields 2000-char excerpt equal to `input[:2000]` and a sha256 of the full input.
  - `test_excerpt_compile_error_handles_none` — None input yields `("", "")`.
  - `test_build_p_feedback_prompt_returns_none_for_non_f1_compile` — F0_PARSE, F1_RUNTIME, F2_NUMERIC_LARGE, F3_TIMEOUT all return None.
  - `test_build_p_feedback_prompt_includes_six_sections_in_order` — for F1_COMPILE, the output contains the six section headers in `P_SECTION_ORDER`.
  - `test_build_p_feedback_prompt_includes_base_prompt_verbatim` — the base prompt substring appears in the output.
  - `test_build_p_feedback_prompt_rejects_forbidden_terms_in_feedback` — synthesizing a `compile_error` containing `"speedup 2.3x"` raises ValueError.
  - `test_build_p_feedback_prompt_allows_llvm_and_ptx` — a `compile_error` containing `"PTX assembler failed"` or `"LLVM ERROR"` is accepted and appears in the output.
  - `test_build_p_feedback_prompt_uses_cluster3_sanitizer_only` (§B5 + §C7) — monkeypatches `cluster2.feedback.prompts.validate_no_forbidden_feedback_terms` to a raising stub and asserts `build_p_feedback_prompt` still succeeds, proving the Cluster 2 validator is never invoked. This test exists for the negative assertion only; the production code path imports Cluster 3's sanitizer exclusively.
  - `test_build_compile_diagnostic_note_is_deterministic` — same inputs → same output across two calls.
  - `test_build_compile_diagnostic_note_does_not_propose_patches` — assert the output contains neither "use ", "try ", nor "replace " (proxy for patch-style suggestions).
- `cluster3/tests/test_p_repair_loop.py`:
  - `test_p_loop_seed_attempt_does_not_call_generation_for_attempt_0` (§C1) — assert `generation.call_count == 0` after a single seed-only invocation.
  - `test_p_loop_seed_attempt_does_not_call_evaluation_for_attempt_0` (§C1) — assert `evaluation.call_count == 0` after a single seed-only invocation.
  - `test_p_loop_seed_attempt_records_attempt_0_in_trace` (§C1) — assert `result.attempts[0].source_hash == sha256(seed_attempt.source)` and `result.attempts[0].failure_code == seed_attempt.failure_code`.
  - `test_p_loop_first_feedback_built_from_seed_attempt` (§C1) — patch the prompt builder to record its inputs; assert the first attempt-1 call receives `compile_error == seed_attempt.compile_error`.
  - `test_p_loop_status_compile_repaired_then_success` (§C3) — seed F1_COMPILE; attempt 1 returns full Level-2 success; assert `status="compile_repaired_then_success"`, `successful_attempt_index=1`, `final_failure_code=None`.
  - `test_p_loop_status_compile_repaired_f2_observed` (§C3) — seed F1_COMPILE; attempt 1 returns F2_NUMERIC_LARGE; assert `status="compile_repaired_f2_observed"`, `final_failure_code="F2_NUMERIC_LARGE"`. **The loop does NOT terminate as "terminated" on F2** — it returns the dedicated status so the orchestrator can chain to C.
  - `test_p_loop_status_post_p_f3_observed` (§C3 + §E8) — seed F1_COMPILE; attempt 1 returns F3_EVAL_PIPELINE; assert `status="post_p_f3_observed"` and assert compile evidence fields are preserved separately.
  - `test_p_loop_compile_repaired_then_success_sets_stop_reason` (§I1) — success status carries `stop_reason="p_compile_repaired_then_success"`.
  - `test_p_loop_compile_repaired_f2_observed_sets_stop_reason` (§I1) — F2-observed status carries `stop_reason="p_compile_repaired_f2_observed"`.
  - `test_p_loop_post_p_f3_with_compile_evidence_sets_post_compile_stop_reason` (§I1) — post-P F3 with compile evidence carries `stop_reason="p_post_compile_f3_observed"`.
  - `test_p_loop_post_p_f3_without_compile_evidence_sets_no_compile_evidence_stop_reason` (§I1) — post-P F3 without compile evidence carries `stop_reason="p_f3_without_compile_evidence"`.
  - `test_post_p_f3_without_compile_evidence_not_compile_repaired` (§E8) — post-P F3 with `level_reached=0` and `compile_success=False` keeps `p_compile_repair_succeeded=False` at row construction.
  - `test_post_p_f3_with_compile_evidence_can_mark_compile_repaired` (§E8) — post-P F3 with `compile_success=True` or `level_reached>=2` may set `p_compile_repair_succeeded=True`.
  - `test_f3_eval_pipeline_level0_does_not_set_p_compile_repair_succeeded` (§E8) — F3_EVAL_PIPELINE synthesized at level 0 is not compile repair.
  - `test_p_loop_status_compile_unchanged_exhausted` (§C3 + §G7) — every attempt F1_COMPILE through budget; assert `status="compile_unchanged_exhausted"`, `stop_reason="p_budget_exhausted"`, `attempts_executed == repair_budget + 1`.
  - `test_p_loop_status_terminated_unrecoverable_f0` (§C3 + §G7) — attempt 1 returns F0_PARSE; assert `status="terminated_unrecoverable"`, `stop_reason="p_terminal_non_repairable"`.
  - `test_p_loop_status_terminated_unrecoverable_f1_runtime` (§C3 + §G7) — attempt 1 returns F1_RUNTIME; assert `status="terminated_unrecoverable"`, `stop_reason="p_terminal_non_repairable"`.
  - `test_p_stop_reason_compile_repaired_f2_observed` (§G7) — status `compile_repaired_f2_observed` maps to `p_compile_repaired_f2_observed`.
  - `test_p_stop_reason_f3_without_compile_evidence` (§G7) — post-P F3 with no compile evidence maps to `p_f3_without_compile_evidence`.
  - `test_p_terminal_non_repairable_uses_prefix_for_f0` (§G7) — any `failure_code.startswith("F0_")` maps to `p_terminal_non_repairable`.
  - `test_p_loop_unknown_status_rejected_before_row_construction` (§I1) — unknown P loop status raises before Phase 5 can construct a row.
  - `test_p_loop_terminal_source_hash_matches_last_attempt` (§C2 + §D3 enabling test) — assert `result.attempts[-1].source_hash == hashlib.sha256(result.terminal_source.encode("utf-8")).hexdigest()`. `PRepairAttemptSummary` is source-free (it carries only `source_hash`, mirroring Cluster 2 at [cluster2/feedback/repair_loop.py:73-85](cluster2/feedback/repair_loop.py:73)). The orchestrator gets the actual source from `PRepairLoopResult.terminal_source`.
  - `test_p_loop_rejects_budget_above_default` — `repair_budget=DEFAULT_P_REPAIR_BUDGET+1` raises ValueError.
  - `test_p_loop_rejects_seed_attempt_with_non_eligible_failure_code` — `seed_attempt.failure_code="F2_NUMERIC_LARGE"` raises (P loop entry requires F1_COMPILE).
  - `test_p_seed_attempt_requires_generation_seed` (§E7) — omitting or nulling `generation_seed` raises.
  - `test_p_seed_attempt_requires_kernel_name` (§F6) — omitting or nulling `kernel_name` raises.
  - `test_p_seed_attempt_source_hash_matches_source` (§F6) — malformed or non-matching `source_hash` raises.
  - `test_p_seed_attempt_requires_prompt_hash` (§H2) — `prompt_hash` is mandatory for new Cluster 3 seeds.
  - `test_p_seed_attempt_rejects_missing_prompt_hash` (§H2) — `None` or empty prompt hash raises.
  - `test_p_seed_attempt_prompt_hash_matches_prompt_when_prompt_stored` (§F6) — stored prompt text must hash to `prompt_hash`.
  - `test_p_seed_attempt_prompt_hash_matches_prompt_metadata_when_prompt_not_stored` (§H2) — source-only seed records still require the prompt construction metadata hash.
  - `test_p_seed_attempt_identity_matches_parent_row` (§F6) — parent seed/sample/kernel identity mismatch raises before P repair starts.
  - `test_p_seed_attempt_rejects_f1_without_compile_error_evidence` (§E7) — F1 seed with no compile error type or excerpt raises.
  - `test_p_seed_attempt_rejects_failure_code_eval_result_mismatch` (§E7) — declared F1_COMPILE with an evaluation result classified as F0/F2/F3 raises.
  - `test_p_loop_passes_previous_feedback_to_generation` — second attempt's generation input receives the feedback string from the first attempt.
- `cluster3/tests/test_cluster3_trace.py`:
  - `test_cluster3_trace_summary_json_serializable` (§F4) — `Cluster3TraceSummary.to_json()` round-trips through JSON without dataclass/private objects.
  - `test_cluster3_trace_summary_distinguishes_initial_f2_from_post_p_f2` (§F4) — direct C and P-to-C paths produce different `c_loop_source` and `failure_path` values.
  - `test_cluster3_trace_summary_marks_private_eval_data_false` (§F4) — the flag is exactly false and cannot be set true.
  - `test_cluster3_trace_summary_self_contained_invariants` (§H5) — Phase 1 validates required fields, canonical condition/code values, sha256-shaped hashes, boolean final flags, and compact failure-path labels without needing a row object.
  - `test_cluster3_trace_summary_failure_path_consistent_with_loop_flags` (§H5) — summary loop flags and `failure_path` agree for no-repair, P-only, direct-C, and P-to-C paths.
  - `test_c_attempt_count_excludes_seed_candidate` (§H3) — generated C attempt count does not include the seed F2 candidate.
  - `test_c_attempt_count_zero_when_budget_zero` (§H3) — C fires with budget zero but `c_attempt_count == 0`.
  - `test_c_trace_path_length_is_attempt_count_plus_one_when_c_fires` (§H3) — C path has seed plus generated attempts.
  - `test_c_attempt_count_zero_when_c_does_not_fire` (§H3) — no-C summaries always record zero C attempts.
  - `test_trace_summary_no_private_eval_data` (§G4) — no raw correctness payload, private shape data, source text, or full compile logs appear in the serialized summary.

**Tests that must pass.** All `cluster3/tests/test_p_prompts.py`, `cluster3/tests/test_p_repair_loop.py`, and `cluster3/tests/test_cluster3_trace.py`.

**Regression check.** `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests` green.

**Estimated complexity.** Medium (~4 agent-hours; ~400 lines of code, ~600 lines of tests).

**Dependencies on prior phases.** Phase 0.

**Files that should not be modified.** Anything outside `cluster3/`. Specifically: `cluster2/feedback/*.py` is read-only.

**Commit message template.**
```
cluster3: phase 1 — P repair loop and feedback prompts (local only)

Adds cluster3/feedback/{prompts,compile_error_repair,trace}.py with a
deterministic six-section compile-error prompt template, a dependency-injected
P repair loop, and per-attempt trace summaries. No Modal, no real generation.
Mirrors cluster2/feedback patterns where applicable.
```

**Risk + mitigation.** Risk: drift between Cluster 2's `_must_terminate_without_feedback` policy and the P loop's termination policy. Mitigation: tests explicitly enumerate every F-code class. Risk: forbidden-term regex duplication (§C7 fix). Mitigation: Cluster 3 owns a self-contained copy at `cluster3/feedback/sanitizer.py`; the Phase 1 test `test_cluster3_sanitizer_terms_match_cluster2_current_terms` compares against Cluster 2's current term list and requires an intentional Cluster 3 update when Cluster 2 changes. **Cluster 3 does NOT re-export or wrap any function from `cluster2.feedback.prompts`.**

## 7. Phase 2 — Cluster 3 row schema and logger

**Purpose.** Define the `Cluster3EvalRow` dataclass with embedded P fields, and a durable JSONL logger mirroring Cluster 2.

**Files to add.**
- `cluster3/results/dataclass.py`:
  - `CLUSTER3_RESULTS_SCHEMA_VERSION: int = 1`.
  - `PRepairAttemptSummary` and `Cluster3TraceSummary` (frozen dataclasses, may re-export from `cluster3/feedback/trace.py`).
  - `Cluster3ReplayRowMetadata` — mirrors/extends [cluster2/results/dataclass.py:192-294 (Cluster2ReplayRowMetadata)](cluster2/results/dataclass.py:192) for no-P control artifact rows used in pair validation. It is separate from Cluster 3 generated-row metadata and must not be used as generated-row provenance.
  - `Cluster3GeneratedRowMetadata` — extends Cluster 2's generated metadata with the P field set from Part A §A3.
  - `Cluster3EvalRow` frozen dataclass — fields are the union of `Cluster2EvalRow` core fields (`condition`, `source_class`, `generation_mode`, `attempt_index`, `kernel_class`, `kernel_name`, `dtype`, `base_seed`, `source_hash`, `grammar_active`, `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, `failure_code`, `trace_summary`, `replay_metadata`, `generated_metadata`, `repair_trace`) and the post-review P/C field set:
    - `initial_failure_code: str | None` (§E3 — failure before any repair loop; None for initial success)
    - `p_repair_attempted: bool`
    - `p_compile_repair_succeeded: bool` (§B3 + §E2 — renamed from `p_repair_succeeded`; means P-terminal Level 1 repair success before any C loop)
    - `p_repair_changed_terminal_class: bool` (§C5 rename of `p_repair_changed_outcome`; NEUTRAL signal — True iff terminal class differs from initial, not "P helped")
    - `p_repair_budget: int`
    - `p_repair_attempt_count: int` (§D11a — counts NEW P-generation attempts only, not the seed; bound `[0, p_repair_budget]`)
    - `p_initial_failure_code: str | None`
    - `p_terminal_failure_code: str | None` (§D7 + §E3 — classification at the END of the P loop, before any C handoff)
    - `c_loop_fired: bool` (§D7 + §E1 — True iff the C loop ran, whether from direct initial F2 or from post-P F2)
    - `c_loop_source: Literal["none", "initial_f2", "post_p_f2"]` (§E1)
    - `c_terminal_failure_code: str | None` (§E2 + §E3 — classification at the END of the C loop; None on C success)
    - `c_terminal_level_reached: int | None` (§E2 — final level reached by the C loop candidate; accepts 0/1/2/3-equivalent terminal evidence)
    - `p_compile_error_class: str | None`
    - `p_raw_error_excerpt_sha256: str | None`
    - `p_repair_stop_reason: str`
    - `p_feedback_format: str`
    - `p_history_policy: str`
    - `p_repair_trace: tuple[PRepairAttemptSummary, ...] | None`
    - `terminal_source_stage: Literal["initial", "p_attempt", "c_attempt"]` (§F3)
    - `terminal_generation_seed: int` (§F3)
    - `terminal_attempt_index: int | None` (§F3; initial terminal source uses `0`, not None, to mirror Cluster 2 attempt indexing)
    - `terminal_source_hash: str` (§F3)
    - `terminal_prompt_hash: str | None` (§F3)
    - `terminal_prompt_hash_source: Literal["initial_prompt", "p_repair_prompt", "c_repair_prompt", "seed_prompt_metadata", "seed_prompt_unavailable"]` (§I3)
    - `terminal_source_matches_row_source: bool` (§F3)
  - `trace_summary` (§E9 + §F4): required for all generated Cluster 3 rows, including P-only and C/P-composed rows. It is a `Cluster3TraceSummary` terminal compact trace summary for the entire row after all active loops, matches row `failure_code`, P/C loop flags, terminal source provenance, and final `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, and `source_hash`. It excludes raw private eval data, full source text, raw correctness payloads, private shape sets, and full compile logs. Replay controls, if ever represented in the Cluster 3 dataclass, follow Cluster 2's rule that replay rows do not carry generated trace summaries.
  - `__post_init__` validation (post-review, §B3 + §C5 + §E binding):
    - `condition` must be in `CLUSTER3_CONDITIONS` (rejects none/G/C/G+C — those belong to Cluster 1/2).
    - `source_class` resolved by `source_class_for_cluster3_condition` (§C6) — always `GENERATED_SOURCE_CLASS`.
    - `generation_mode` resolved by `generation_mode_for_cluster3_condition` (§C6) — `C_GENERATION_MODE` for P / C+P; `G_PLUS_C_GENERATION_MODE` for G+P / G+C+P.
    - `failure_code` must be in `FAILURE_CODES` or None (matches [cluster2/results/dataclass.py:459-460](cluster2/results/dataclass.py:459)).
    - `initial_failure_code` must equal the first evaluation's classification. If no repair loop fires, row `failure_code == initial_failure_code`.
    - **§F8 + §H1 inactive-P policy.** Config-level P settings are always recorded, even when P does not fire: `p_feedback_format == P_FEEDBACK_FORMAT_V1` (`"compile_error_template_v1"`) and `p_history_policy == P_HISTORY_POLICY_V1` (`"last_attempt_only_v1"`). Attempt/outcome fields are inactive: `p_repair_attempted is False`, `p_repair_attempt_count == 0`, `p_initial_failure_code is None`, `p_terminal_failure_code is None`, `p_repair_trace is None`, `p_compile_error_class is None`, `p_raw_error_excerpt_sha256 is None`, `p_repair_stop_reason == "p_not_applicable"`, `p_compile_repair_succeeded is False`, and `p_repair_changed_terminal_class is False`. Direct initial-F2 C rows follow this same inactive-P policy.
    - If `p_repair_attempted is True`: `p_initial_failure_code` must be in `P_ELIGIBLE_FAILURE_CODES` (= `{"F1_COMPILE"}` in v1). F1_RUNTIME cannot be a P initial because the dispatcher (§C4) terminates F1_RUNTIME before the P loop is entered.
    - **§B3 + §C5 + §E2 contract**: `p_compile_repair_succeeded` is a P-terminal signal only. It is True only if P converted an initial F1 into a post-P evaluation that passed Level 1 (`compile_success=True`) or reached Level 2 before any C loop. It is not overwritten by later C regression.
    - **§C5 binding**: If `p_compile_repair_succeeded is False` and the P loop ran, `p_terminal_failure_code` may be any F0/F1/F3 code (including codes different from `p_initial_failure_code` — a regenerated P candidate can move into F0_PARSE, F1_RUNTIME, F3_*). Post-P F3 requires compile evidence before `p_compile_repair_succeeded` may be True (§E8).
    - Row-level `compile_success` and `functional_success` always reflect the final row outcome after the last active loop. If C fires and regresses to F0/F1, row `compile_success` is False even when the P-terminal success flag remains True.
    - **§D7 + §E1 `c_loop_fired` contract**:
      - If `c_loop_fired is True`, `condition in {"C+P", "G+C+P"}`, `repair_trace is not None`, and `c_loop_source in {"initial_f2", "post_p_f2"}`.
      - `c_loop_source == "initial_f2"`: initial evaluation returned an F2 code at `level_reached >= 2`; P does not fire; `p_*` attempt/outcome fields remain inactive; `p_repair_stop_reason == "p_not_applicable"`; `c_terminal_failure_code` is row `failure_code`.
      - `c_loop_source == "post_p_f2"`: P fired first and its terminal classification is F2; C receives the cached P-terminal F2 candidate as attempt 0; `c_terminal_failure_code` is row `failure_code`.
      - `c_loop_source == "none"` iff `c_loop_fired is False`; then `c_terminal_failure_code is None` and `c_terminal_level_reached is None`.
      - C terminal may be `None`, any F0_* code, F1_COMPILE, F1_RUNTIME, any F2_* code, or any F3_* code. This explicitly allows C repair candidate regression to F0/F1/F3 as well as C success/exhaustion.
    - **§E3 row failure-code binding**:
      - If P fires and C does not fire, row `failure_code == p_terminal_failure_code`.
      - If P fires and then C fires, row `failure_code == c_terminal_failure_code`.
      - If P does not fire and C fires directly, row `failure_code == c_terminal_failure_code`.
      - If neither loop fires, row `failure_code == initial_failure_code`.
    - **§C5 + §D7 contract**: `p_repair_changed_terminal_class is True` iff (`p_initial_failure_code != p_terminal_failure_code`) OR (`p_initial_failure_code is not None` AND `p_terminal_failure_code is None`). This is a NEUTRAL signal of P-induced change in the P loop's own classification, NOT influenced by C-loop outcomes. The analyzer derives `p_helped` separately in Phase 7 (PENDING_RESEARCH on the exact predicate).
    - `p_feedback_format` must equal `P_FEEDBACK_FORMAT_V1`; `p_history_policy` must equal `P_HISTORY_POLICY_V1`.
    - `p_repair_budget` ∈ `[0, DEFAULT_P_REPAIR_BUDGET]`.
    - **§D11a binding**: `p_repair_attempt_count` ∈ `[0, p_repair_budget]` (counts new P generations only, not the seed). When `p_repair_attempted is True`, `len(p_repair_trace) == p_repair_attempt_count + 1` (seed + new attempts).
    - **§F3 terminal source provenance contract**:
      - Row-level source/code field, when present in the in-memory builder, must be the terminal source. Row-level `source_hash` must equal `terminal_source_hash`.
      - `sha256(row.source) == terminal_source_hash` whenever full source text is available; otherwise the builder must validate the terminal attempt record's source before dropping raw source from the row.
      - `generated_metadata.generation_seed == terminal_generation_seed`; this field points to the terminal source, not blindly to the initial generation.
      - `terminal_source_matches_row_source is True` for every emitted row. False is a validation error, not a warning.
      - If the terminal source is the initial generation: `terminal_source_stage="initial"`, `terminal_attempt_index=0`, `terminal_generation_seed=<initial generation seed>`, and `terminal_source_hash=sha256(initial_source)`.
      - If the terminal source is a P candidate: `terminal_source_stage="p_attempt"`, `terminal_attempt_index=<P attempt index>`, `terminal_generation_seed=<P attempt generation seed>`, and `terminal_source_hash=sha256(P terminal source)`.
      - If the terminal source is a C candidate: `terminal_source_stage="c_attempt"`, `terminal_attempt_index=<C attempt index>`, `terminal_generation_seed=<C attempt generation seed>`, and `terminal_source_hash=sha256(C terminal source)`.
      - If C regresses after P, the final row source is the C attempt source and final row fields come from the C terminal evaluation; P terminal failure/source data remain separately recorded in P fields and `p_repair_trace`.
      - `terminal_prompt_hash` and `terminal_prompt_hash_source` identify the prompt used to generate the terminal source:
        - Initial generation terminal source: `terminal_prompt_hash` is the initial generation prompt hash and `terminal_prompt_hash_source="initial_prompt"`.
        - P repair terminal source: `terminal_prompt_hash` is the P repair prompt hash and `terminal_prompt_hash_source="p_repair_prompt"`.
        - Generated C repair terminal source: `terminal_prompt_hash = sha256(RepairGenerationInput.prompt)` captured by the Cluster 3 C-loop wrapper and `terminal_prompt_hash_source="c_repair_prompt"`. This hash is required and must not be None.
        - C-loop seed candidate / attempt 0 terminal source: inherit the seed prompt hash metadata when available and set `terminal_prompt_hash_source="seed_prompt_metadata"` unless the source can be more specifically classified as `initial_prompt` or `p_repair_prompt`. If seed prompt metadata is unavailable, `terminal_prompt_hash=None` is allowed only with `terminal_prompt_hash_source="seed_prompt_unavailable"`.
    - **§G4 + §H5 trace-summary row cross-checks**:
      - `trace_summary.terminal_source_hash == terminal_source_hash`.
      - `trace_summary.row_source_hash == source_hash` and equals `sha256(row.source)` when full source text is available.
      - `trace_summary.terminal_generation_seed == terminal_generation_seed`.
      - `trace_summary.terminal_prompt_hash == terminal_prompt_hash`.
      - `trace_summary.terminal_prompt_hash_source == terminal_prompt_hash_source`.
      - `trace_summary.compile_success == compile_success` and `trace_summary.functional_success == functional_success`.
      - `trace_summary.repair_set_success == repair_set_success` and `trace_summary.eval_set_success == eval_set_success`.
      - `trace_summary.private_eval_data_included is False`.
  - Builders `generated_row(...)` and `replay_control_row(...)` mirror [cluster2/results/dataclass.py:909-974](cluster2/results/dataclass.py:909) shape but produce `Cluster3EvalRow`. `generated_row(...)` requires `trace_summary`. When a C loop ran, `repair_trace` carries Cluster 2 `TraceSummary` entries from the C loop; the terminal C trace's attempt index, failure code, source hash, and success flags must agree with the row's terminal fields and `Cluster3TraceSummary`, but the objects are not equal because the Cluster 3 summary contains P/C orchestration fields.
  - `Cluster3ContentHashSidecar` mirrors `Cluster2ContentHashSidecar`.
- `cluster3/results/logger.py`:
  - `Cluster3JsonlAppendLogger` — copy of `Cluster2JsonlAppendLogger` ([logger.py:76-188](cluster2/results/logger.py:76)) parameterized to `Cluster3EvalRow` and the new sidecar type. Preserves `fsync=True` default, `mode ∈ {"overwrite", "resume"}`, deterministic-prefix resume validation, and `_write_sidecar_atomic` semantics ([logger.py:449-476](cluster2/results/logger.py:449)).
  - `serialize_cluster3_row(row) -> str` — canonical sorted-keys JSON line.
  - `default_content_hash_sidecar_path(path) -> Path` — same convention as Cluster 2.

**Files to modify.** None.

**Tests to add.**
- `cluster3/tests/test_cluster3_schema.py`:
  - `test_cluster3_row_accepts_p_condition` — `Cluster3EvalRow(condition="P", ...)` constructs.
  - `test_cluster3_row_rejects_none_g_c_gc` — each raises ValueError.
  - `test_cluster3_row_rejects_unknown_failure_code` — raises.
  - `test_cluster3_row_p_attempted_false_requires_p_outcome_fields_inactive` — populating any P attempt/outcome field while `p_repair_attempted=False` raises, while config fields remain recorded.
  - `test_inactive_p_rows_record_p_config_but_no_p_attempt` (§F8) — inactive rows still record `p_feedback_format="compile_error_template_v1"` and `p_history_policy="last_attempt_only_v1"`.
  - `test_inactive_p_rows_use_p_not_applicable_stop_reason` (§H1) — inactive rows require `p_repair_stop_reason="p_not_applicable"`.
  - `test_direct_initial_f2_c_row_has_p_attempt_count_zero` (§F8) — direct-C rows have `p_repair_attempt_count == 0`.
  - `test_direct_initial_f2_c_row_uses_p_not_applicable_stop_reason` (§H1) — direct initial-F2 C rows follow the same inactive-P stop-reason policy.
  - `test_inactive_p_terminal_fields_are_null_or_false_except_stop_reason` (§F8 + §H1) — inactive P terminal fields are null or false exactly as specified, while the stop reason is the non-null `p_not_applicable` constant.
  - `test_cluster3_row_p_compile_repair_succeeded_allows_f2_failure_code` (§B3) — `p_compile_repair_succeeded=True`, `compile_success=True`, `failure_code="F2_NUMERIC_LARGE"`, `functional_success=False` constructs without error.
  - `test_p_compile_repair_succeeded_survives_c_regression_to_f1` (§E2) — P terminal reaches F2, C regresses to F1_COMPILE; row preserves `p_compile_repair_succeeded=True` while row-level compile is False.
  - `test_final_row_compile_success_reflects_c_terminal_not_p_terminal` (§E2) — same path asserts row-level `compile_success` follows the C terminal candidate.
  - `test_cluster3_row_p_attempted_failed_allows_terminal_class_change` (§C5) — `p_initial_failure_code="F1_COMPILE"`, `p_terminal_failure_code="F0_PARSE"`, `failure_code="F0_PARSE"`, `p_compile_repair_succeeded=False`, `c_loop_fired=False`, `p_repair_changed_terminal_class=True` is accepted.
  - `test_cluster3_row_p_attempted_failed_allows_f1_runtime_terminal` (§C5) — `p_initial_failure_code="F1_COMPILE"`, `p_terminal_failure_code="F1_RUNTIME"`, `failure_code="F1_RUNTIME"`, `c_loop_fired=False` is accepted.
  - `test_cluster3_row_p_attempted_failed_allows_f3_terminal` (§C5) — same shape, `F3_EVAL_PIPELINE`.
  - `test_cluster3_row_p_only_after_p_compile_repair_failure_code_matches_p_terminal` (§D7) — `condition="P"`, `c_loop_fired=False`, `p_terminal_failure_code="F2_NUMERIC_LARGE"`, `failure_code != "F2_NUMERIC_LARGE"` raises (P alone cannot rescue F2).
  - `test_cluster3_row_c_plus_p_after_c_success_failure_code_is_none` (§D7) — `condition="C+P"`, `p_repair_attempted=True`, `p_compile_repair_succeeded=True`, `p_terminal_failure_code="F2_NUMERIC_LARGE"`, `c_loop_fired=True`, `failure_code=None`, `functional_success=True`, `repair_trace=(...non-empty...)` is accepted.
  - `test_cluster3_row_c_loop_fired_requires_c_in_condition` (§D7) — `c_loop_fired=True`, `condition="P"` raises.
  - `test_cluster3_row_c_loop_fired_requires_repair_trace_non_none` (§D7) — `c_loop_fired=True`, `repair_trace=None` raises.
  - `test_schema_allows_c_loop_fired_without_p_repair_attempted_when_source_initial_f2` (§E1) — direct initial F2 C path validates with inactive P fields and `c_loop_source="initial_f2"`.
  - `test_c_loop_source_none_when_c_not_fired` (§E1) — inactive C rows require `c_loop_source="none"`.
  - `test_c_loop_terminal_allows_f0_f1_f2_f3_none` (§E2) — parametrizes every terminal class and `None`.
  - `test_p_to_f2_then_c_to_f1_row_validates` (§E2) — P-terminal F2 followed by C-terminal F1 is accepted and row `failure_code` is F1.
  - `test_c_loop_source_post_p_requires_p_terminal_f2` (§E1) — `c_loop_source="post_p_f2"` with a non-F2 P terminal raises.
  - `test_c_loop_source_initial_f2_rejects_p_fields` (§E1) — direct initial-F2 C path raises if P fields are populated.
  - `test_cluster3_row_p_repair_attempt_count_excludes_seed` (§D11a) — `p_repair_attempt_count=0` with `p_repair_attempted=True` is accepted (P loop ran the seed only — equivalent to "P attempted but generated zero new candidates"). `p_repair_attempt_count == p_repair_budget` is the maximum.
  - `test_cluster3_row_p_repair_trace_length_matches_attempt_count_plus_seed` (§D11a) — `len(p_repair_trace) == p_repair_attempt_count + 1` when `p_repair_attempted=True`.
  - `test_cluster3_row_p_repair_changed_terminal_class_consistency` (§C5 + §D7) — for every combination of `(p_initial_failure_code, p_terminal_failure_code)`, assert `p_repair_changed_terminal_class` is the deterministic boolean from §C5 (using `p_terminal_failure_code`, NOT row `failure_code`).
  - `test_cluster3_row_p_attempted_false_requires_changed_class_false` — populating `p_repair_changed_terminal_class=True` while `p_repair_attempted=False` raises.
  - `test_cluster3_row_p_attempted_false_allows_direct_c_loop_from_initial_f2` (§E1) — inactive P fields are valid when `c_loop_source="initial_f2"`.
  - `test_cluster3_row_has_no_p_helped_attribute` (§C5) — assert `Cluster3EvalRow` does not declare a `p_helped` field (that signal is analyzer-derived only).
  - `test_cluster3_row_uses_p_terminal_failure_code_attribute` (§D7) — assert the P terminal field is named `p_terminal_failure_code`.
  - `test_cluster3_row_requires_trace_summary` (§E9) — generated rows without `trace_summary` raise.
  - `test_trace_summary_mentions_p_and_c_loop_status_without_private_data` (§E9) — terminal trace summary includes compact P/C loop status and excludes raw source, raw private eval payloads, and full compile logs.
  - `test_trace_summary_terminal_hash_matches_row` (§G4) — schema validation rejects a trace terminal hash that diverges from row terminal provenance.
  - `test_trace_summary_final_success_flags_match_row` (§G4) — schema validation rejects trace final success flags that diverge from row final outcome.
  - `test_trace_summary_terminal_generation_seed_matches_row_metadata` (§G4) — schema validation rejects trace terminal generation seed drift.
  - `test_trace_summary_no_private_eval_data` (§G4) — serialized trace summary remains private-eval-free.
  - `test_cluster3_trace_summary_matches_row_terminal_provenance` (§H5) — Phase 2 schema validation cross-checks trace terminal hash, row source hash, terminal prompt hash, and terminal generation seed against row fields and generated metadata.
  - `test_cluster3_trace_summary_matches_row_final_success_flags` (§H5) — Phase 2 schema validation cross-checks trace final success flags against row-level `compile_success`, `functional_success`, `repair_set_success`, and `eval_set_success`.
  - `test_terminal_source_stage_initial_sets_generation_seed_from_initial` (§F3) — initial terminal rows set terminal generation seed from the initial candidate.
  - `test_terminal_source_stage_p_attempt_sets_generation_seed_from_p_attempt` (§F3) — P-terminal rows set terminal generation seed from the P attempt.
  - `test_terminal_source_stage_c_attempt_sets_generation_seed_from_c_attempt` (§F3) — C-terminal rows set terminal generation seed from the C attempt.
  - `test_row_source_hash_equals_terminal_source_hash` (§F3) — row `source_hash` must equal `terminal_source_hash`.
  - `test_generated_metadata_generation_seed_equals_terminal_generation_seed` (§F3) — generated metadata and terminal provenance agree.
  - `test_p_terminal_source_preserved_when_c_regresses` (§F3) — P terminal fields remain intact when a later C attempt becomes the final row source.
  - `test_terminal_prompt_hash_initial_source_uses_initial_prompt_hash` (§I3) — initial terminal source rows use the initial generation prompt hash and `terminal_prompt_hash_source="initial_prompt"`.
  - `test_terminal_prompt_hash_p_attempt_uses_p_prompt_hash` (§I3) — P-terminal rows use the P repair prompt hash and `terminal_prompt_hash_source="p_repair_prompt"`.
  - `test_terminal_prompt_hash_generated_c_attempt_hashes_c_prompt` (§I3) — generated C terminal attempts use `sha256(RepairGenerationInput.prompt)` and `terminal_prompt_hash_source="c_repair_prompt"`.
  - `test_terminal_prompt_hash_seed_candidate_allows_none_only_with_unavailable_source` (§I3) — seed candidate terminal rows may use `terminal_prompt_hash=None` only with `terminal_prompt_hash_source="seed_prompt_unavailable"`.
  - `test_terminal_prompt_hash_generated_c_attempt_cannot_be_none` (§I3) — generated C terminal attempts reject missing prompt hashes.
  - `test_cluster3_replay_row_metadata_mirrors_cluster2_replay_metadata_contract` (§H6) — replay metadata accepts the no-P control artifact fields from `Cluster2ReplayRowMetadata`.
  - `test_cluster3_replay_row_metadata_not_used_as_generated_row_metadata` (§H6) — generated Cluster 3 rows require generated metadata and cannot substitute replay metadata for generated provenance.
  - `test_cluster3_row_budget_bounds` — `p_repair_budget=6` raises; `0..5` accepted.
  - `test_cluster3_row_attempt_count_bounds` — `p_repair_attempt_count=p_repair_budget+2` raises.
  - `test_cluster3_row_feedback_format_constant` — non-`P_FEEDBACK_FORMAT_V1` raises.
  - `test_cluster3_row_serializes_round_trips` — `to_json` and `from_json` (if provided) round-trip; otherwise direct dataclass equality after `Cluster3EvalRow(**json.loads(line))`.
  - `test_cluster3_schema_version_constant` — `CLUSTER3_RESULTS_SCHEMA_VERSION == 1`.
- `cluster3/tests/test_cluster3_logger.py`:
  - `test_logger_writes_one_row_with_fsync` — open in overwrite mode, append one row, close; assert file ends with `\n` and content matches `serialize_cluster3_row(row) + "\n"`.
  - `test_logger_resume_matches_existing_prefix` — pre-write two rows in overwrite; reopen in resume mode and re-append those two; assert no extra bytes written, no error.
  - `test_logger_resume_rejects_diverging_prefix` — pre-write row A; resume and try to append row B; raises.
  - `test_logger_resume_rejects_extra_existing_rows` — pre-write three rows; resume with two; assert `_validate_no_unconsumed_resume_rows` raises on close.
  - `test_logger_sidecar_atomic_write` — assert sidecar file exists and parses; mock tempfile failure mid-write asserts the original sidecar is preserved.

**Tests that must pass.** All `cluster3/tests/test_cluster3_schema.py` and `cluster3/tests/test_cluster3_logger.py`.

**Regression check.** Full repo test suite green.

**Estimated complexity.** Medium-large (~5 agent-hours; ~600 lines of code, ~700 lines of tests).

**Dependencies on prior phases.** Phase 0, Phase 1 (for `PRepairAttemptSummary`).

**Files that should not be modified.** `cluster2/results/*.py` (read-only). `shared/eval/failure_taxonomy.py` (read-only).

**Commit message template.**
```
cluster3: phase 2 — Cluster3EvalRow dataclass and durable JSONL logger

Adds cluster3/results/{dataclass,logger}.py with the P field set finalized in
the Part A audit addendum (§A3), CLUSTER3_RESULTS_SCHEMA_VERSION=1, and a
fsync-by-default appender mirroring cluster2/results/logger.py. Cluster 2
artifacts are untouched.
```

**Risk + mitigation.** Risk: subtle divergence from Cluster 2's resume semantics. Mitigation: copy the Cluster 2 logger verbatim and parameterize on the row class; do not refactor the resume protocol. Risk: schema field bloat. Mitigation: A3 table is the authoritative field set; no additions in this phase.

## 8. Phase 3 — F1/F2 dispatcher

**Purpose.** Implement the deterministic failure-code dispatcher that routes F1_COMPILE to the P loop, F2_* to the C loop (when C is active), and F0/F1_RUNTIME/F3 to terminal.

**Files to add.**
- `cluster3/feedback/dispatcher.py` (§C4 binding — `level_reached` is now consulted):
  - `DispatchDecision` frozen dataclass: `route: Literal["terminate", "p_loop", "c_loop"]`, `reason: str`, `failure_code: str | None`, `c_loop_source: Literal["none", "initial_f2"] = "none"`.
  - `dispatch(condition: str, failure_code: str | None, level_reached: int | None, *, functional_success: bool | None = None) -> DispatchDecision` with this mandatory validation order (§F7):
    1. Validate `condition` is one of `{"P", "G+P", "C+P", "G+C+P"}`. Unknown conditions raise before success shortcuts.
    2. Derive active factors from condition (`p_active=True` for all Cluster 3 conditions; `c_active=True` only for `C+P` and `G+C+P`) and validate the derived flags are internally consistent.
    3. Validate `failure_code` is in `FAILURE_CODES` when not None. Unknown codes raise before level-0 terminal shortcuts.
    4. When `level_reached is not None`, validate it is compatible with `failure_code`: F0 codes require level 0, F1 codes require level 1, F2 codes require `level_reached >= 2`, and F3 codes may carry the level at which infrastructure failed but must not masquerade as F0/F1/F2.
    5. If `functional_success is True` or `failure_code is None`, return `("terminate", "success", None)`.
    6. Else dispatch by failure code and active factors:
       - `level_reached is None` → `("terminate", "level_reached_missing", failure_code)`.
       - F0_* → `("terminate", "f0_terminal", failure_code)`.
       - `level_reached == 1` AND `failure_code == "F1_COMPILE"` → `("p_loop", "p_eligible", failure_code)`.
       - `level_reached == 1` AND `failure_code == "F1_RUNTIME"` → `("terminate", "unrecoverable_runtime", failure_code)`.
       - F2_* AND `c_active is True` → `("c_loop", "c_eligible_initial_f2", failure_code, c_loop_source="initial_f2")`. This is the direct initial-F2 C path (§E1): P does not fire because the initial failure is already Level 2.
       - F2_* AND `c_active is False` → `("terminate", "f2_terminal_no_c", failure_code)`.
       - F3_* → `("terminate", "f3_terminal", failure_code)`.
  - `is_p_eligible(failure_code: str | None) -> bool` — convenience wrapper around `P_ELIGIBLE_FAILURE_CODES` membership; does NOT check `level_reached` (the dispatcher does that).
  - Module imports only `cluster3.constants` and `shared.eval.failure_taxonomy.FAILURE_CODES`. Does NOT import `cluster2/`; that import lives at the orchestration layer in Phase 5.

**Files to modify.** None.

**Tests to add.**
- `cluster3/tests/test_dispatcher.py`:
  - One parametric test enumerating every member of `FAILURE_CODES` ∪ `{None}` × `level_reached ∈ {0, 1, 2, None}` for each of `{"P", "G+P", "C+P", "G+C+P"}`, asserting the expected `(route, reason)`.
  - `test_dispatch_p_eligible_only_f1_compile_at_level1` (§C4) — F1_COMPILE at level_reached=1 routes to p_loop.
  - `test_dispatcher_rejects_f1_with_level0` (§G5) — F1_COMPILE with `level_reached=0` raises ValueError before routing.
  - `test_dispatcher_rejects_f2_with_level1` (§G5) — F2_NUMERIC_LARGE with `level_reached=1` raises ValueError before routing.
  - `test_dispatch_c_routing_requires_level_reached_ge_2` (§C4) — F2_NUMERIC_LARGE with level_reached=2 and `condition="C+P"` returns `("c_loop", "c_eligible_initial_f2", ...)`.
  - `test_dispatch_rejects_level_reached_none` (§C4) — every failure_code with `level_reached=None` returns `("terminate", "level_reached_missing", ...)`.
  - `test_dispatch_p_eligible_only_f1_compile` — `is_p_eligible("F1_COMPILE")` True; `is_p_eligible("F1_RUNTIME")` False; everything else False.
  - `test_dispatch_c_routing_requires_c_in_condition` — F2_NUMERIC_LARGE at level_reached=2 with `condition="P"` → terminate; with `condition="C+P"` → c_loop.
  - `test_dispatch_initial_f2_marks_c_loop_source_initial_f2` (§E1) — F2_NUMERIC_LARGE at level_reached=2 with `condition="C+P"` or `"G+C+P"` returns `c_loop_source="initial_f2"` and does not route to P.
  - `test_dispatcher_rejects_unknown_condition` (§G5) — `condition="none"` raises ValueError.
  - `test_dispatcher_rejects_unknown_failure_code` (§G5) — `failure_code="F4_UNKNOWN"` raises ValueError.
  - `test_dispatcher_rejects_unknown_condition_before_success_shortcut` (§F7) — unknown condition with `functional_success=True` still raises.
  - `test_dispatcher_rejects_unknown_failure_code_before_level0_terminal` (§F7) — unknown failure code with `level_reached=0` raises.
  - `test_dispatcher_validates_failure_code_level_compatibility` (§F7) — mismatched F-code family and level raise before routing.

**Tests that must pass.** `cluster3/tests/test_dispatcher.py`.

**Regression check.** Full suite green.

**Estimated complexity.** Small (~2 agent-hours; ~100 lines of code, ~250 lines of tests).

**Dependencies on prior phases.** Phase 0.

**Files that should not be modified.** Anything outside `cluster3/`.

**Commit message template.**
```
cluster3: phase 3 — deterministic F1/F2 dispatcher

Adds cluster3/feedback/dispatcher.py routing F1_COMPILE to the P loop,
F2_* to the C loop when condition contains C, and F0/F1_RUNTIME/F3 to
terminal. Pure dispatch; no Modal, no generation, no Cluster 2 import.
```

**Risk + mitigation.** Risk: dispatcher silently terminates a code that should be repairable (regression vector). Mitigation: parametric test enumerates every code so any future addition fails until the dispatcher is taught about it.

## 9. Phase 4 — Cluster 3 correctness runner LOCAL adapter (§B7)

**Purpose.** Provide a LOCAL Python adapter that calls the existing Cluster 2 Modal correctness function `cluster2.modal.correctness.remote_c2_correctness`. Cluster 3 does NOT define a new Modal entrypoint, NOT build a new image, and NOT register a new `@app.function` in v1 (§B7). The shared `triton_compile_image` at [shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21) ALREADY bundles `cluster1`, `cluster2`, AND `shared` via `add_local_python_source("cluster1", "cluster2", "shared")`. The Cluster 2 correctness function at [cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41) then wraps it with another `add_local_python_source("cluster2")` (redundant no-op). The image does NOT bundle `cluster3`, and v1 does not need it (§D8a, §C9). The Cluster 3 path runs entirely in the calling process and round-trips through the existing Cluster 2 entrypoint. Modal docs §J: Functions run in their own configured containers, and source/image configuration belongs to the registered Function; therefore Cluster 3 must not rely on automatic source mounting or image mutation for remote execution.

**Files to add.**
- `cluster3/modal/__init__.py` — empty.
- `cluster3/modal/correctness_runner.py`:
  - `Cluster3CorrectnessRequest` — typed wrapper. Fields are a Cluster 3 identity plus the candidate `source`. The wrapper does NOT subclass `RemoteCorrectnessRequest`; instead it composes one internally after the §B1 condition translation. This keeps Cluster 3's allowed-condition surface (`CLUSTER3_CONDITIONS` only) cleanly separated from `RemoteCorrectnessRequest`'s `FactorCell`-typed condition field (which accepts the canonical factor-cell set defined in [shared/factors/cells.py](shared/factors/cells.py)) (§D8b correction).
  - `run_cluster3_correctness(request: Cluster3CorrectnessRequest, *, modal_call: Callable[[dict], dict] | None = None) -> dict`:
    1. Validate `request.identity.condition` is in `CLUSTER3_CONDITIONS`.
    2. Translate via `cluster3_to_cluster2_eval_condition(request.identity.condition)` (§B1) to get the Cluster 2 condition. `P/C+P → C`, `G+P/G+C+P → G+C`.
    3. Build a `cluster2.modal.schemas.RemoteCorrectnessRequest` whose `identity.condition`, `identity.source_class`, and `identity.generation_mode` use the translated Cluster 2 condition. This makes `generation_allowed_for_condition(...)` return True ([cluster2/modal/correctness_runner.py:73-99](cluster2/modal/correctness_runner.py:73)) so Level 0 parse, Level 0 signature, and Level 1 compile gates all fire.
    4. Call `modal_call` if provided (tests inject a stub); otherwise import lazily and call `cluster2.modal.correctness.remote_c2_correctness.remote(req_dict)` for the real Modal path. Do not use `modal.Function.from_name`, `.spawn`, `FunctionCall.get(timeout=...)`, or a new `modal.App`; v1 uses the in-repo C2 Function object synchronously, matching the existing Cluster 2 runner style.
    5. **§B2 + §D9 + §E4 restamp.** Call `restamp_cluster3_condition(payload, c3_condition)` which re-stamps:
       - top-level `surface` → `"c3_remote_correctness"`,
       - top-level `condition` (if present),
       - `identity.condition`,
       - `source_identity.condition`,
       - `eval_identity.condition` (defensive — restamp if present),
       - **`correctness_result.identity.condition` only when a nested `correctness_result` exists.** Cluster 2's normal success/failure payload at [cluster2/modal/correctness_runner.py:288-329](cluster2/modal/correctness_runner.py:288) nests an identity inside the correctness result, and that identity must be restamped. Cluster 2 infrastructure payloads at [cluster2/modal/correctness_runner.py:332-388](cluster2/modal/correctness_runner.py:332) are valid without a nested correctness result; the adapter must preserve the infrastructure payload, restamp only available identity sidecars, and not crash.
       Other identity fields (`kernel_*`, `dtype`, `base_seed`, `attempt_index`) are NOT restamped — they are the same on both sides.
    6. Post-restamp self-check: for normal success/failure payloads only, assert wrapper identity condition equals nested correctness-result identity condition (mirrors Cluster 2's invariant at [correctness_runner.py:463](cluster2/modal/correctness_runner.py:463)). Skip the nested check for `correctness_status == "INFRA_FAILURE"` or any preserved malformed/infrastructure payload that lacks `correctness_result`; those are handled by result extraction below.
    7. Return the modified payload.
  - `validate_cluster3_remote_correctness_payload(payload) -> dict` — re-stamps `surface` to `"c2_remote_correctness"` and `condition` to the Cluster 2 equivalent before calling `cluster2.modal.correctness_runner.validate_remote_correctness_payload`, then restamps back. This preserves Cluster 2's validator without weakening it.
- `cluster3/modal/result_extraction.py` (§E5):
  - `extract_or_synthesize_cluster3_correctness_result_dict(payload: Any, identity: EvalIdentity | Cluster3 identity) -> dict[str, Any]`.
  - Purpose: Phase 5 must consume a canonical result dict from Cluster 3-restamped success payloads, normal failure payloads, infrastructure payloads, and malformed payloads without importing Cluster 2's private `_extract_or_synthesize_correctness_result_dict`.
  - Behavior:
    - Accepts success payloads and normal failure payloads with `correctness_result`.
    - Accepts infrastructure payloads without `correctness_result`; synthesizes a canonical F3_EVAL_PIPELINE result preserving infrastructure details in the public `correctness_error` / f3 reason field.
    - Accepts Cluster 3 identity stamps in wrapper and nested result payloads.
    - Rejects only truly unrecognized shapes by returning a synthesized F3_EVAL_PIPELINE canonical dict rather than crashing the runner.
    - Returns a dict with `identity`, `failure_code`, `level_reached`, `compile_success`, `functional_success`, `repair_set_success`, `eval_set_success`, `compile_error_type`, `compile_error_excerpt` or `compile_error`, shape/dtype identity if present, and an `f3_reason` / public malformed-payload summary when synthesized.
    - Validates identity when a nested `correctness_result.identity` exists; for infrastructure payloads, validates any wrapper `identity`, `source_identity`, and `eval_identity` that are present.

**Files to modify.** None. **No changes to `cluster2/modal/`. No new Modal image. No new `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.App`, `modal.Image.*`, `modal.Volume`, `modal.Secret`, `modal.Queue`, web endpoint, dynamic batcher, or `add_local_python_source("cluster3")`.**

**Tests to add.**
- `cluster3/tests/test_correctness_runner_adapter.py`:
  - `test_adapter_rejects_non_cluster3_condition` — `condition="C"`, `"none"`, `"G"`, `"G+C"` all raise.
  - `test_adapter_translates_p_to_c_for_inner_eval` (§B1 + §D8c) — inject a stub `modal_call`; assert it receives `identity.condition="C"` AND `identity.source_class == cluster2.constants.GENERATED_SOURCE_CLASS` (= `"generated_row"`, see [cluster2/constants.py:15, 27](cluster2/constants.py:15)) AND `identity.generation_mode == cluster2.constants.generation_mode_for_condition("C")`. The adapter returns a payload with `condition="P"` and `surface="c3_remote_correctness"`. The test uses the constant name, not a hardcoded string, so it stays correct if the constant value changes.
  - `test_adapter_translates_g_plus_p_to_g_plus_c_for_inner_eval` (§B1) — likewise with G+P → G+C.
  - `test_adapter_translates_c_plus_p_to_c` (§B1) — C+P → C.
  - `test_adapter_translates_g_plus_c_plus_p_to_g_plus_c` (§B1) — G+C+P → G+C.
  - `test_adapter_does_not_translate_to_replay_controls` (§B1, regression guard) — assert the stub `modal_call` NEVER receives `condition="none"` or `condition="G"` for any Cluster 3 input. This is the test that locks in §B1.
  - `test_adapter_preserves_canonical_failure_code` — stub returns F1_COMPILE; assert the adapter's returned payload still has F1_COMPILE.
  - `test_adapter_does_not_import_modal_at_module_level` — assert `import cluster3.modal.correctness_runner` does not import `modal`.
  - `test_adapter_uses_no_new_modal_function` (§B7) — assert `cluster3.modal.correctness_runner` does not define any `@app.function` decorated callable (introspect module attributes).
  - `test_adapter_default_modal_call_imports_c2_function_lazily` (§J2) — monkeypatch/import-instrument the module and assert the default real-Modal path imports `cluster2.modal.correctness.remote_c2_correctness` only inside `run_cluster3_correctness`, never at module import.
  - `test_adapter_has_no_cluster3_modal_image_or_app_definitions` (§J1) — AST-scan `cluster3/modal/correctness_runner.py` for forbidden Modal construction: `modal.App`, `modal.Image`, `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.Volume`, `modal.Secret`, `modal.Queue`, and `add_local_python_source("cluster3")`.
  - `test_adapter_restamps_nested_correctness_result_identity` (§D9) — inject a stub that returns a payload with `identity.condition="C"` and `correctness_result.identity.condition="C"`; assert the adapter returns a payload where BOTH are `"P"` for input condition `"P"`.
  - `test_adapter_post_restamp_self_check_raises_on_mismatch` (§D9) — inject a stub that returns a payload where the nested identity's condition diverges from the wrapper's after a fake partial restamp; assert the adapter raises.
  - `test_cluster3_correctness_adapter_allows_infra_payload_without_correctness_result` (§E4) — inject an infrastructure payload with wrapper identity but no nested correctness result; adapter restamps available identities and returns without indexing a missing key.
  - `test_cluster3_correctness_adapter_restamps_success_payload_identity` (§E4) — normal success payload gets wrapper and nested identity restamped.
  - `test_cluster3_correctness_adapter_preserves_f3_eval_pipeline_payload` (§E4) — malformed/infrastructure payload remains available for F3_EVAL_PIPELINE synthesis.
  - `test_extract_cluster3_success_payload` (§E5) — extractor returns canonical success fields.
  - `test_extract_cluster3_f1_compile_payload_with_error_excerpt` (§E5) — extractor preserves `compile_error_type` and compile-error excerpt fields from an F1 payload.
  - `test_extract_cluster3_f3_malformed_payload_synthesizes_eval_pipeline` (§E5) — infrastructure/malformed payload without nested result produces `failure_code="F3_EVAL_PIPELINE"`, `level_reached=0`, `compile_success=False`, `functional_success=False`.
  - `test_extract_cluster3_rejects_unrecognized_payload_shape_with_f3_not_crash` (§E5) — unexpected payload shape yields synthesized F3 canonical result instead of an uncaught exception.

**Tests that must pass.** `cluster3/tests/test_correctness_runner_adapter.py`.

**Regression check.** Full suite green; particularly Cluster 2's correctness runner tests are untouched.

**Estimated complexity.** Small (~2 agent-hours; ~150 lines of code, ~300 lines of tests).

**Dependencies on prior phases.** Phase 0, Phase 1 (`condition_adapters`), Phase 2.

**Files that should not be modified.** `cluster2/modal/*.py` (read-only). `shared/eval/levels/*` (read-only). `shared/modal_harness/*` (read-only).

**Commit message template.**
```
cluster3: phase 4 — local correctness adapter over existing C2 Modal entrypoint

Adds cluster3/modal/correctness_runner.py as a pure-Python adapter that
translates Cluster 3 conditions to C/G+C (so Level 0/1 gates fire) and
delegates to the existing cluster2.modal.correctness.remote_c2_correctness
Modal function. No new Modal image, no new @app.function, no
add_local_python_source("cluster3"). Re-stamps the returned payload's
condition and surface back to Cluster 3 values.
```

**Risk + mitigation.** Risk: silent divergence if Cluster 2's payload schema changes. Mitigation: an adapter contract test asserts the inner payload shape matches `cluster2.modal.correctness_runner.C2_CORRECTNESS_PAYLOAD_SCHEMA_VERSION`. Risk: accidentally importing the Modal app at module top breaks local-import contract or causes source-packaging assumptions to leak into tests. Mitigation (§J1 + §J2): `test_adapter_does_not_import_modal_at_module_level`, `test_adapter_default_modal_call_imports_c2_function_lazily`, and `test_adapter_has_no_cluster3_modal_image_or_app_definitions` enforce a local adapter with lazy C2 Function access only.

## 10. Phase 5 — Cluster 3 Modal generation runner

**Purpose.** CLI orchestration. No Modal calls in tests; tests use dependency-injected adapters as Cluster 2 does ([run_cluster2_modal.py:189-194](cluster2/experiments/run_cluster2_modal.py:189)).

**Files to add.**
- `cluster3/feedback/c_loop_adapter.py` (§F2):
  - `Cluster3CLoopResult` (§G1) and `run_cluster3_c_loop_from_f2(...)` shared helper used for both direct initial-F2 and post-P-F2 C repair. See the contracts below.
- `cluster3/replay/__init__.py` — empty.
- `cluster3/replay/no_p_pairs.py` (§F1 + §E10):
  - `pair_for_condition(p_condition: str) -> str` — `"P" → "none"`, `"G+P" → "G"`, `"C+P" → "C"`, `"G+C+P" → "G+C"`.
  - `validate_pair_identity(p_row, control_row) -> None` — public Cluster 3 validator. It is available in Phase 5 because the runner imports it. It may call Cluster 2 helpers only for shared primitive checks such as immutable revision or digest validation; it must not delegate the full P/no-P pairing contract to any Cluster 2 private pairing-context validator.
- `cluster3/experiments/__init__.py` — already exists; keep empty.
- `cluster3/experiments/run_cluster3_modal.py`:
  - `Cluster3RunnerConfig` frozen dataclass — mirrors `Cluster2RunnerConfig` ([run_cluster2_modal.py:97-186](cluster2/experiments/run_cluster2_modal.py:97)) with these changes:
    - `condition: str` accepts the four P-containing conditions plus `"all"`.
    - `p_repair_budget: int` validated ∈ `[0, DEFAULT_P_REPAIR_BUDGET]`.
    - `c_repair_budget: int` (§D5) validated ∈ `[0, cluster2.constants.DEFAULT_REPAIR_BUDGET]` (= `[0, 5]` per [cluster2/constants.py:33](cluster2/constants.py:33)). Default = `cluster2.constants.DEFAULT_REPAIR_BUDGET = 5`. Required because Phase 5's P→C handoff calls `cluster2.feedback.repair_loop.run_repair_loop(repair_budget=...)`. CLI flag: `--c-repair-budget`.
    - `modal_generation_gpu: str` and `modal_eval_gpu: str` mirror Cluster 2 and are validated against `DEFAULT_C2_MODAL_GENERATION_GPU` / `DEFAULT_C2_MODAL_EVAL_GPU` (= `L4` in v1). Cluster 3 does not introduce a new GPU catalog, fallback list, or resource selector.
    - No Cluster 3 `modal_timeout_s`, `modal_retries`, `max_containers`, `min_containers`, `scaledown_window`, `secrets`, `volumes`, or image fields are added in v1. Those are owned by the existing Cluster 2 Modal decorators: C2 generation uses `timeout=900`, `gpu=REMOTE_C2_GENERATION_GPU`, memory/cpu/secrets/volume/scaling at [cluster2/modal/generation.py:173-184](cluster2/modal/generation.py:173), and C2 correctness uses `timeout=900`, `gpu=REMOTE_CORRECTNESS_EVAL_GPU`, memory/cpu/scaling at [cluster2/modal/correctness.py:44-53](cluster2/modal/correctness.py:44), with an internal correctness subprocess timeout of `600s` at [cluster2/modal/correctness.py:40, 75-86](cluster2/modal/correctness.py:40).
    - Reuses the model/tokenizer revision pinning logic: model = `"Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"`, revision = `"8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"` ([run_cluster1_modal.py:72-73](cluster1/experiments/run_cluster1_modal.py:72)).
  - `RunnerDependencies` — `generation`, `correctness`, `dispatcher`, `pair_identity_validator`, and optional `no_p_control_resolver` callables, all injectable for tests. The default `pair_identity_validator` is `cluster3.replay.no_p_pairs.validate_pair_identity`.
  - Modal execution policy (§J1–§J4): `run_cluster3_modal.py` is an ordinary local argparse CLI, not a Modal App file. It must not define `modal.App`, `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.Image.*`, `modal.Volume`, `modal.Secret`, `modal.Queue`, web endpoints, dynamic batching, or `add_local_python_source("cluster3")`. It invokes existing C2 generation/correctness surfaces synchronously through their current adapters / `.remote()` calls. It must not wrap C2 calls in `.spawn`, `.spawn_map`, `.map`, job queues, or client-side `FunctionCall.get(timeout=...)`, because those APIs would decouple attempts from deterministic row construction and repair-budget accounting.
  - Retry policy (§J3): Cluster 3 does not add Modal `retries=` or `modal.Retries` around generation/correctness. If a C2 remote call returns an infrastructure payload or the Cluster 3 extractor synthesizes `F3_EVAL_PIPELINE`, the row/run records that outcome and the paid phase stops for audit per Phases 11/12. A user-authorized rerun must use explicit resume/overwrite semantics rather than hidden automatic retries.
  - Public pair-identity runner rule (§F1): whenever the runner has a no-P control row available for the current generated Cluster 3 row, it calls `validate_pair_identity(p_row, control_row)` before appending. Phase 6 supplies the manifest-backed control resolver; Phase 5 owns the validator and verifies the runner calls the public Cluster 3 API.
  - `Cluster3CLoopResult` frozen dataclass (§G1), owned by Cluster 3 because Cluster 2's repair result does not carry enough terminal source/provenance for final Cluster 3 row construction:
    - `c_loop_fired: bool`
    - `c_loop_source: Literal["initial_f2", "post_p_f2"]`
    - `c_attempt_count: int` (§H3 — counts generated C repair candidates only; excludes the seed F2 candidate)
    - `c_repair_budget: int`
    - `c_terminal_failure_code: str | None`
    - `c_terminal_level_reached: int | None`
    - `c_terminal_compile_success: bool`
    - `c_terminal_functional_success: bool`
    - `terminal_source: str`
    - `terminal_source_hash: str`
    - `terminal_generation_seed: int`
    - `terminal_prompt_hash: str | None`
    - `terminal_prompt_hash_source: Literal["initial_prompt", "p_repair_prompt", "c_repair_prompt", "seed_prompt_metadata", "seed_prompt_unavailable"]`
    - `terminal_attempt_index: int | None`
    - `terminal_correctness_result: Mapping[str, Any]`
    - `cluster2_repair_result: Mapping[str, Any] | object`
    - `trace_summary_fragment: Mapping[str, Any]`
    - `infrastructure_failure: bool`
    - `f3_reason: str | None`
  - `Cluster3CLoopResult` semantics:
    - `terminal_source` is always the source/code that becomes the row-level source if C is the final active loop.
    - `terminal_source_hash == sha256(terminal_source)`.
    - `terminal_generation_seed` is the seed for the terminal source, not the next seed Cluster 2 would compute internally.
    - `c_attempt_count` excludes the seed candidate. If C fires and `c_repair_budget=0`, `c_attempt_count=0`. If C fires and the adapter generates N repair candidates, `c_attempt_count=N`. If C does not fire, no `Cluster3CLoopResult` is produced and `Cluster3TraceSummary.c_attempt_count=0`.
    - C trace path length is `c_attempt_count + 1` when C fires, because the path includes the seed F2 candidate plus generated C repair attempts.
    - If `c_repair_budget=0`, no C repair candidate is generated; terminal source remains `seed_candidate_source`, terminal hash remains `sha256(seed_candidate_source)`, terminal attempt index remains 0, terminal generation seed remains `seed_candidate_generation_seed`, and `terminal_prompt_hash` / `terminal_prompt_hash_source` come from seed prompt metadata or `seed_prompt_unavailable`.
    - If C produces repair attempts, the adapter records every C attempt's source, correctness result, generation seed, and prompt hash by hashing the captured `RepairGenerationInput.prompt`. If C attempt N becomes terminal, `terminal_source`, `terminal_generation_seed`, `terminal_prompt_hash`, `terminal_prompt_hash_source="c_repair_prompt"`, `terminal_attempt_index`, and `terminal_correctness_result` all come from attempt N. Generated C attempts require a non-null `terminal_prompt_hash`.
    - `terminal_correctness_result` is the canonical final evaluation result after C, accepting success (`failure_code=None`) and F0/F1/F2/F3 terminals.
    - The wrapper may retain the raw/wrapped Cluster 2 repair result for trace/audit context, but row construction must read terminal source/provenance and final correctness from `Cluster3CLoopResult` fields.
  - Shared C-loop helper contract (§F2):
    ```python
    from cluster2.feedback.repair_loop import RepairFeedbackInput
    FeedbackCallable = Callable[[RepairFeedbackInput], str | None]

    def run_cluster3_c_loop_from_f2(
        *,
        outer_c3_condition: str,
        c_loop_source: Literal["initial_f2", "post_p_f2"],
        base_prompt: str,
        base_seed: int,
        sample_index: int,
        kernel_class: str,
        kernel_name: str,
        dtype: str,
        seed_candidate_source: str,
        seed_candidate_generation_seed: int,
        seed_candidate_prompt_hash: str | None,
        seed_candidate_prompt_hash_source: Literal[
            "initial_prompt",
            "p_repair_prompt",
            "seed_prompt_metadata",
            "seed_prompt_unavailable",
        ],
        seed_candidate_evaluation: Mapping[str, Any],
        feedback_builder: FeedbackCallable | None,
        repair_budget: int,
        model_config: Mapping[str, Any],
        provenance_base: Mapping[str, Any],
    ) -> Cluster3CLoopResult:
        ...
    ```
    Required semantics:
    - Uses Cluster 2 C repair loop semantics by calling `cluster2.feedback.repair_loop.run_repair_loop` with the C2-translated repair condition.
    - Uses `repair_budget=config.c_repair_budget`, not the P budget.
    - Passes explicit `kernel_name` into every evaluation identity and wrapper closure. The helper must not hide `kernel_name` inside `provenance_base`.
    - `feedback_builder=None` means use Cluster 2's default public Level 2 feedback builder.
    - Custom feedback builders must satisfy the Cluster 2-compatible `FeedbackCallable = Callable[[RepairFeedbackInput], str | None]` contract from `cluster2.feedback.repair_loop`.
    - Wrapper closures preserve `outer_c3_condition`; they translate from the outer Cluster 3 label and assert the translated label equals the `RepairGenerationInput` / `RepairEvaluationInput` condition received from the C loop.
    - The attempt-0 evaluation returns `seed_candidate_evaluation` without invoking the correctness adapter. Attempts >= 1 call the Cluster 3 correctness adapter and result extractor.
    - The seed candidate / attempt-0 prompt hash is inherited from `seed_candidate_prompt_hash` and `seed_candidate_prompt_hash_source`. If `seed_candidate_prompt_hash is None`, `seed_candidate_prompt_hash_source` must be `"seed_prompt_unavailable"` and the C loop may return None for `terminal_prompt_hash` only when no generated C attempt becomes terminal.
    - The wrapper captures every generated C `RepairGenerationInput.prompt`; for attempts >= 1 it computes `sha256(inputs.prompt)` and records `terminal_prompt_hash_source="c_repair_prompt"` when that attempt becomes terminal.
    - Does not expose P compile-error feedback, P compile-error excerpts, or private eval shapes to C. Custom feedback builders that include P compile-error text or private eval shapes are rejected.
    - Records `c_loop_source` in provenance returned to the runner.
    - Works whether the seed candidate came from the initial generation (`c_loop_source="initial_f2"`) or from the P terminal source (`c_loop_source="post_p_f2"`).
    - The seed candidate source has seed `seed_candidate_generation_seed`; this seed must be preserved even though Cluster 2's repair loop computes its own per-attempt seeds internally.
    - C attempts 1..N may use Cluster 2's C-loop attempt seed schedule, but the adapter must capture those actual per-attempt C seeds in its attempt records.
    - Terminal generation seed is selected by terminal source: no generated C attempt means `terminal_generation_seed=seed_candidate_generation_seed`; C attempt N terminal means `terminal_generation_seed=c_attempt_N_generation_seed`.
    - If Cluster 2 returns or traces a source-free repair summary, the adapter still returns a source/provenance-complete `Cluster3CLoopResult` from the generation/evaluation wrappers' captured attempt records.
  - `run_cluster3(config, *, dependencies=None) -> Cluster3RunResult` — mirrors `run_cluster2` ([run_cluster2_modal.py:433-527](cluster2/experiments/run_cluster2_modal.py:433)) with this post-review control flow per (kernel, dtype, base_seed):
    1. **§B2 translation.** Translate Cluster 3 condition → Cluster 2 generation condition via `cluster3_to_cluster2_generation_condition`. Build the `RemoteC2GenerationRequest` with the translated condition (so [cluster2/modal/schemas.py:223-239](cluster2/modal/schemas.py:223) validation passes). Call the existing Cluster 2 generation surface.
    2. **§B1 + §E5 translation/extraction.** Translate Cluster 3 condition → Cluster 2 eval condition via `cluster3_to_cluster2_eval_condition`. Call `cluster3.modal.correctness_runner.run_cluster3_correctness`, which restamps inputs/outputs internally (Phase 4). Immediately pass the returned payload through `extract_or_synthesize_cluster3_correctness_result_dict(...)`; all subsequent dispatcher and row-building logic consumes that canonical dict, not raw wrapper payloads.
    3. Decide via dispatcher (Phase 3) using the canonical failure code, `level_reached`, and `functional_success` returned by Level 0/1/2 (§C4 + §F7). If route=`"c_loop"` from the initial evaluation, this is the direct initial-F2 C path (§E1): P does not fire, `c_loop_source="initial_f2"`, and the C loop receives the initial F2 candidate as its seed.
    4. **§C1 + §E7 + §F6 + §H2 binding.** If route=`"p_loop"`, build a `PSeedAttempt` from the initial candidate: source, generation_seed, base_seed, sample_index, kernel_class, kernel_name, dtype, source_hash, required prompt_hash, prompt text if retained, the just-computed evaluation result, failure_code, compile_error, and compile_error_type. Construction validates source/prompt hashes, parent row identity, prompt metadata binding, and F1/level-1/compile-error evidence before calling `cluster3.feedback.compile_error_repair.run_p_repair_loop(seed_attempt=...)`. The loop will NOT re-generate or re-evaluate attempt 0. The P loop's `generation` and `evaluation` callables are Cluster 3-conditioned wrappers that perform the §B1/§B2 translations on each call.
    5. **§C3 + §C2 + §B4 + §E1 binding.** Inspect the dispatcher decision or `PRepairLoopResult.status`:
       - Initial route `"c_loop"` with `c_loop_source="initial_f2"`:
         - Call `run_cluster3_c_loop_from_f2(..., c_loop_source="initial_f2", kernel_name=<kernel_name>, seed_candidate_source=<initial_source>, seed_candidate_generation_seed=<initial generation seed>, seed_candidate_prompt_hash=<initial prompt hash or None>, seed_candidate_prompt_hash_source=<"initial_prompt" or "seed_prompt_unavailable">, seed_candidate_evaluation=<cached initial F2 result>, repair_budget=config.c_repair_budget, ...)`.
         - Do not call the P loop; set `p_repair_attempted=False`, `p_repair_attempt_count=0`, `c_loop_fired=True`, and `c_loop_source="initial_f2"`.
       - `status="compile_repaired_then_success"` → terminate with success. Final `failure_code=None`.
       - `status="compile_repaired_f2_observed"` AND condition ∈ `{"C+P", "G+C+P"}`:
         - **§C2 + §D5 + §D6 + §F2 seeded handoff.** Call `run_cluster3_c_loop_from_f2(..., c_loop_source="post_p_f2", kernel_name=<kernel_name>, seed_candidate_source=PRepairLoopResult.terminal_source, seed_candidate_generation_seed=<P terminal generation seed>, seed_candidate_prompt_hash=<P terminal prompt hash or None>, seed_candidate_prompt_hash_source=<"p_repair_prompt" or "seed_prompt_unavailable">, seed_candidate_evaluation=<cached P-terminal F2 result>, repair_budget=config.c_repair_budget, ...)`.
         - Use the returned `Cluster3CLoopResult` for final row source/provenance and C terminal correctness.
         - Set `c_loop_source="post_p_f2"` and set `repair_trace` from `Cluster3CLoopResult.cluster2_repair_result.trace_summaries` or the wrapped mapping equivalent.
       - `status="compile_repaired_f2_observed"` AND condition ∉ `{"C+P", "G+C+P"}` → terminate with the F2 code; `p_compile_repair_succeeded=True`.
       - `status="post_p_f3_observed"` → terminate with the F3 code; `p_compile_repair_succeeded=True` only when the P terminal evidence has `terminal_compile_success=True` or `terminal_level_reached>=2`; otherwise it remains False (§E8).
       - `status="compile_unchanged_exhausted"` → terminate with `failure_code="F1_COMPILE"`; `p_compile_repair_succeeded=False`.
       - `status="terminated_unrecoverable"` → terminate with the final F0/F1_RUNTIME code; `p_compile_repair_succeeded=False`.
    6. **§B3 + §C5 + §D7 + §E2 row construction.** Build the `Cluster3EvalRow`:
       - `initial_failure_code` ← initial canonical result `failure_code`.
       - `p_compile_repair_succeeded` ← True iff the P loop terminal candidate passed Level 1 or reached Level 2 before any C loop. Do not derive this from the status prefix alone.
       - `p_terminal_failure_code` (§D7 rename) ← `PRepairLoopResult.final_failure_code`. This is the P loop's terminal classification, not the row's terminal.
       - `c_loop_fired` (§D7 new field) ← True iff `c_loop_source in {"initial_f2", "post_p_f2"}`.
       - `c_terminal_failure_code` ← `Cluster3CLoopResult.c_terminal_failure_code` when C fires, including F0/F1/F2/F3 or None on C success.
       - `c_terminal_level_reached` ← `Cluster3CLoopResult.c_terminal_level_reached` when C fires.
       - `p_repair_changed_terminal_class` ← True per §C5 definition (initial code != p_terminal_failure_code, or initial non-None and p_terminal_failure_code is None). Computed from P's own terminal, NOT influenced by C-loop outcomes.
       - `p_repair_attempt_count` (§D11a) ← number of new P generations (excludes the seed); equals `PRepairLoopResult.attempts_executed - 1` (the seed is attempt 0).
       - `failure_code` ← terminal classification from the LAST eval. It equals the P terminal when only P ran, `Cluster3CLoopResult.terminal_correctness_result["failure_code"]` when C ran, and the initial classification when no loop ran.
       - `compile_success` ← final row compile result from the LAST eval, including C regression to F0/F1; when C ran, use `Cluster3CLoopResult.c_terminal_compile_success`.
       - `functional_success` ← final row functional result from the LAST eval; when C ran, use `Cluster3CLoopResult.c_terminal_functional_success`.
       - `trace_summary` ← terminal compact trace summary for the entire row (§E9).
       - `repair_trace` ← `Cluster3CLoopResult.cluster2_repair_result.trace_summaries` or equivalent wrapped trace list if the C loop ran, else None.
       - `p_repair_trace` ← the P loop's per-attempt summaries (seed + new attempts).
       - `p_repair_stop_reason` (§H1 + §I1) ← always populated. If P did not fire, set `"p_not_applicable"` (including direct initial-F2 C rows). If P fired, copy `PRepairLoopResult.stop_reason` into the row after validating it is one of `P_REPAIR_STOP_REASONS`; unknown P loop status or stop reason raises before row construction.
       - `terminal_source_stage`, `terminal_generation_seed`, `terminal_attempt_index`, `terminal_source_hash`, `terminal_prompt_hash`, `terminal_prompt_hash_source`, and `terminal_source_matches_row_source` ← terminal source provenance (§F3 + §I3). When C ran and a generated C candidate is terminal, these come from `Cluster3CLoopResult.terminal_source*` fields, `terminal_source_stage="c_attempt"`, `terminal_prompt_hash=sha256(RepairGenerationInput.prompt)`, and `terminal_prompt_hash_source="c_repair_prompt"`. When C fires with `c_repair_budget=0`, no C candidate is generated, so the terminal stage remains the seed candidate's origin: `"initial"` for `c_loop_source="initial_f2"` and `"p_attempt"` for `c_loop_source="post_p_f2"`; the terminal prompt hash comes from inherited seed prompt metadata or is None only with `terminal_prompt_hash_source="seed_prompt_unavailable"`.
       - `generated_metadata.generation_seed` ← `terminal_generation_seed`, not necessarily the initial seed.
       - `p_feedback_format` and `p_history_policy` ← Phase 0 constants even when P is inactive (§F8).
    7. If a no-P control row is available for the paired condition, call the Phase 5 public `validate_pair_identity(row, control_row)` before append. The call is skipped only when the configured control resolver is absent; Phase 6 makes the manifest-backed resolver available for implementation runs.
    8. Append via `Cluster3JsonlAppendLogger` (fsync=True).
  - CLI `main()` with argparse, mirroring [run_cluster2_modal.py CLI](cluster2/experiments/run_cluster2_modal.py) shape and the same flag names where possible.

**Files to modify.** None.

**Tests to add.**
- `cluster3/tests/test_run_cluster3_modal_cli.py`:
  - `test_runner_config_accepts_p_conditions` — `Cluster3RunnerConfig(condition="P", ...)` constructs; same for G+P, C+P, G+C+P, "all".
  - `test_runner_config_rejects_cluster2_conditions` — `condition="C"` raises.
  - `test_runner_config_repair_budget_bounds` — 0..5 accepted; 6 raises.
  - `test_runner_config_modal_gpus_match_cluster2_defaults` (§J1) — only the existing C2 L4 generation/eval GPUs are accepted in v1.
  - `test_runner_config_has_no_cluster3_timeout_or_retry_fields` (§J3 + §J4) — the config has no Cluster 3-specific `modal_timeout_s`, `modal_retries`, `max_containers`, `min_containers`, or `scaledown_window` fields.
  - `test_runner_config_requires_immutable_model_revision` — non-40-char revision raises (mirrors [run_cluster2_modal.py:127-136](cluster2/experiments/run_cluster2_modal.py:127)).
  - `test_run_cluster3_source_defines_no_modal_app_function_or_image` (§J1 + §J2) — AST-scan `cluster3/experiments/run_cluster3_modal.py` for forbidden Modal construction: `modal.App`, `modal.Image`, `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.Volume`, `modal.Secret`, `modal.Queue`, web endpoint decorators, dynamic batching, and `add_local_python_source("cluster3")`.
  - `test_run_cluster3_uses_synchronous_c2_modal_calls_no_spawn_or_map` (§J3) — tests/instrumentation assert the runner does not call `.spawn`, `.spawn_map`, `.map`, or `FunctionCall.get(timeout=...)` around C2 generation/correctness.
  - `test_cluster3_validate_pair_identity_for_p_vs_none` (§F1 + §E10) — public validator accepts a P row paired to the none control with matching identity.
  - `test_cluster3_validate_pair_identity_for_cp_vs_c` (§F1 + §E10) — public validator accepts a C+P row paired to the C control with matching identity.
  - `test_cluster3_runner_uses_public_validate_pair_identity` (§F1) — monkeypatch the Phase 5 public validator and assert the runner invokes it when a no-P control row is supplied.
  - `test_run_cluster3_translates_p_to_c_for_generation` (§B2) — inject a stub generation adapter; for `condition="P"`, assert it receives `RemoteC2GenerationRequest(identity.condition="C", ...)`. Row records `condition="P"`.
  - `test_run_cluster3_translates_gp_to_gc_for_generation` (§B2) — likewise.
  - `test_run_cluster3_dispatches_f1_compile_to_p_loop_with_seed_attempt` (§C1 + §E7 + §F6) — inject initial F1_COMPILE; assert the orchestrator builds a `PSeedAttempt` from the initial evaluation result and identity fields (`generation_seed`, `base_seed`, `sample_index`, `kernel_class`, `kernel_name`, `dtype`, `source_hash`, `prompt_hash`) and calls `run_p_repair_loop(seed_attempt=...)`. Assert the P loop's injected `generation` and `evaluation` are NOT called for attempt 0.
  - `test_run_cluster3_terminates_on_f0_parse` — inject F0_PARSE; assert row has `p_repair_attempted=False`, `failure_code="F0_PARSE"`, `functional_success=False`, `p_repair_changed_terminal_class=False`.
  - `test_run_cluster3_c_plus_p_initial_f2_invokes_c_loop_without_p` (§E1) — inject initial F2_NUMERIC_LARGE for `condition="C+P"`; assert P loop is never called, C loop is called once, row has inactive P fields, `c_loop_fired=True`, and `c_loop_source="initial_f2"`.
  - `test_run_cluster3_gcp_initial_f2_invokes_c_loop_without_p` (§E1) — same for `condition="G+C+P"`.
  - `test_run_cluster3_p_repairs_compile_then_level2_fails_records_f2` (§B3, §C3) — inject initial F1_COMPILE → P attempt 1 yields F2_NUMERIC_LARGE; for `condition="P"` assert row has `p_compile_repair_succeeded=True`, `p_repair_changed_terminal_class=True`, `compile_success=True`, `failure_code="F2_NUMERIC_LARGE"`, `functional_success=False`. No C loop invoked.
  - `test_run_cluster3_c_plus_p_seeds_c_loop_with_p_terminal_source` (§C2) — inject initial F1_COMPILE → P attempt 1 yields F2_NUMERIC_LARGE → for `condition="C+P"`, capture the kwargs passed to `run_repair_loop`; assert `seed_candidate_source` equals the P loop's `terminal_source`.
  - `test_run_cluster3_c_plus_p_passes_c_repair_budget_not_p_repair_budget` (§D5) — set `p_repair_budget=5, c_repair_budget=3`; for `C+P` after P→F2 handoff, assert the `run_repair_loop` kwargs have `repair_budget=3`.
  - `test_run_cluster3_p_repair_budget_independent_from_c_repair_budget` (§D5) — set `p_repair_budget=2, c_repair_budget=5`; assert P loop runs with budget 2 (max 2 new attempts after seed) and the C loop sees budget 5.
  - `test_run_cluster3_c_wrapper_uses_outer_c3_condition_for_translation` (§D6) — instrument the wrappers; for `condition="C+P"` and a C loop call with `RepairGenerationInput(condition="C", ...)`, assert the wrapper's translation call passes `"C+P"` (the outer Cluster 3 condition) to `cluster3_to_cluster2_generation_condition`, NOT `"C"`.
  - `test_run_cluster3_c_wrapper_translation_invariant_holds` (§D6) — the wrapper's `assert c2_gen_condition == c2_input.condition` never fires under normal operation (paired translation invariant).
  - `test_run_cluster3_c_wrapper_rejects_unexpected_inner_condition` (§D6) — feed the wrapper a synthetic `RepairGenerationInput(condition="G+C")` while `outer_c3_condition="C+P"`; assert the wrapper's invariant assert raises (defensive against future C-loop refactors).
  - `test_run_cluster3_c_loop_from_initial_f2_uses_same_budget_as_post_p_f2` (§F2) — both C entry paths pass `config.c_repair_budget` to the helper.
  - `test_run_cluster3_c_loop_from_f2_preserves_outer_c3_condition` (§F2) — wrapper provenance records the Cluster 3 condition, not only C/G+C.
  - `test_run_cluster3_c_loop_from_f2_does_not_pass_p_compile_error_to_c_feedback` (§F2) — C feedback builder receives only public Level 2 feedback fields.
  - `test_run_cluster3_c_loop_from_f2_records_c_loop_source` (§F2) — helper provenance distinguishes `initial_f2` from `post_p_f2`.
  - `test_c_loop_accepts_cluster2_feedback_callable_signature` (§H4) — custom C feedback builders accept `RepairFeedbackInput` and may return `str | None`.
  - `test_c_loop_allows_none_feedback_builder_for_default` (§H4) — `feedback_builder=None` delegates to Cluster 2's default public Level 2 feedback builder.
  - `test_c_loop_rejects_feedback_builder_that_includes_p_compile_error_text` (§H4) — custom C feedback cannot leak P compile-error details.
  - `test_run_cluster3_c_loop_from_f2_requires_kernel_name` (§G2) — omitting or nulling `kernel_name` raises before invoking Cluster 2 repair.
  - `test_run_cluster3_c_loop_from_f2_passes_kernel_name_to_eval_identity` (§G2) — wrapped evaluation identity receives the explicit kernel name.
  - `test_cluster3_c_loop_result_contains_terminal_source_and_hash` (§G1) — helper returns a `Cluster3CLoopResult` whose terminal source hash equals `sha256(terminal_source)`.
  - `test_cluster3_c_loop_result_budget_zero_preserves_seed_candidate_source` (§G1 + §G3) — with `c_repair_budget=0`, result terminal source/hash/seed equal the seed candidate source/hash/seed.
  - `test_cluster3_c_loop_result_terminal_correctness_result_drives_row_failure_code` (§G1) — row `failure_code`, compile success, and functional success are populated from `terminal_correctness_result` when C fires.
  - `test_cluster3_c_loop_result_wraps_cluster2_result_without_losing_provenance` (§G1) — raw Cluster 2 result may be present, but terminal source/provenance remain available on the Cluster 3 result.
  - `test_c_loop_budget_zero_terminal_seed_is_seed_candidate_generation_seed` (§G3) — no generated C attempt leaves terminal seed equal to `seed_candidate_generation_seed`.
  - `test_c_loop_terminal_seed_tracks_final_c_attempt_seed` (§G3) — terminal seed follows the final generated C attempt seed.
  - `test_c_loop_seed_candidate_seed_not_overwritten_by_cluster2_internal_next_seed` (§G3) — the seed candidate seed is not replaced by Cluster 2's internally computed next attempt seed.
  - `test_phase5_row_construction_always_populates_p_repair_stop_reason` (§H1) — every terminal path writes a non-null P stop reason, using `p_not_applicable` when P did not fire.
  - `test_phase5_copies_p_loop_stop_reason_to_row` (§I1) — when P fires, the row `p_repair_stop_reason` equals `PRepairLoopResult.stop_reason` exactly.
  - `test_run_cluster3_row_c_loop_fired_true_after_c_handoff` (§D7) — for `condition="C+P"` with P→F2→C path, assert row has `c_loop_fired=True` and `repair_trace is not None`.
  - `test_run_cluster3_row_c_loop_source_post_p_f2_after_p_handoff` (§E1) — for `C+P` with P→F2→C path, row has `c_loop_source="post_p_f2"`.
  - `test_run_cluster3_row_c_loop_fired_false_for_p_only_condition` (§D7) — for `condition="P"`, assert row always has `c_loop_fired=False`.
  - `test_run_cluster3_row_p_terminal_failure_code_persists_after_c_success` (§D7) — for `C+P` with P→F2→C success, assert row has `p_terminal_failure_code="F2_NUMERIC_LARGE"` (P's own classification) AND `failure_code=None` (whole-row terminal). The P-only and whole-row signals are distinct.
  - `test_run_cluster3_c_plus_p_c_loop_first_eval_uses_cached_f2_result` (§C2) — instrument the wrapped evaluation callable; assert its attempt-0 call returns the cached F2 result WITHOUT invoking the Cluster 3 correctness adapter; attempts >= 1 do invoke the adapter.
  - `test_run_cluster3_c_plus_p_does_not_regenerate_after_p_repair` (§C2) — assert total generation-adapter call count equals `1 (initial) + N_P_attempts + N_C_attempts`, NOT `1 + N_P + 1 (regen) + N_C`.
  - `test_run_cluster3_c_plus_p_translates_repair_condition` (§B4) — for `condition="C+P"`, assert `run_repair_loop` receives `condition="C"`; row records `condition="C+P"`; `repair_trace` is populated from the `Cluster3CLoopResult` wrapped trace list.
  - `test_run_cluster3_g_plus_c_plus_p_translates_repair_condition` (§B4) — G+C+P → G+C.
  - `test_run_cluster3_p_without_c_does_not_invoke_c_loop` (§B4 boundary) — for `condition="P"` after the P loop returns `compile_repaired_f2_observed`, assert `run_repair_loop` is NEVER called.
  - `test_run_cluster3_g_plus_p_without_c_does_not_invoke_c_loop` (§B4 boundary) — same for G+P.
  - `test_run_cluster3_c_plus_p_runs_c_loop_after_p_repair_and_succeeds` — inject initial F1_COMPILE → P attempt 1 yields F2_NUMERIC_LARGE → C loop succeeds at C attempt 2; assert row has `p_compile_repair_succeeded=True`, `p_repair_changed_terminal_class=True`, `repair_trace` non-empty, `functional_success=True`, `failure_code is None`.
  - `test_run_cluster3_c_regression_to_f0_records_final_terminal_failure` (§E2) — C loop after initial F2 or post-P F2 returns F0_PARSE; row `failure_code` is F0_PARSE and row `compile_success=False`.
  - `test_run_cluster3_c_regression_to_f1_records_final_terminal_failure` (§E2) — C loop returns F1_COMPILE; row `failure_code` is F1_COMPILE and row `compile_success=False`.
  - `test_run_cluster3_p_terminal_success_not_invalidated_by_c_regression` (§E2) — P reaches F2, C regresses to F1; row preserves P-terminal compile repair success and final row fields reflect C terminal failure.
  - `test_run_cluster3_post_p_f3_without_compile_evidence_not_compile_repaired` (§E8) — post-P F3_EVAL_PIPELINE at level 0 leaves P-terminal compile repair success false.
  - `test_run_cluster3_post_p_f3_with_compile_evidence_marks_compile_repaired` (§E8) — post-P F3 with `level_reached>=2` may mark P-terminal compile repair success true.
  - `test_run_cluster3_trace_summary_is_terminal_whole_row_summary` (§E9) — row `trace_summary` matches the final terminal outcome after P/C, not only the P terminal attempt.
  - `test_run_cluster3_terminal_source_stage_initial_sets_generation_seed_from_initial` (§F3) — runner populates terminal provenance for no-repair initial terminals.
  - `test_run_cluster3_terminal_source_stage_p_attempt_sets_generation_seed_from_p_attempt` (§F3) — runner populates terminal provenance for P-terminal rows.
  - `test_run_cluster3_terminal_source_stage_c_attempt_sets_generation_seed_from_c_attempt` (§F3) — runner populates terminal provenance for C-terminal rows.
  - `test_run_cluster3_generated_metadata_generation_seed_equals_terminal_generation_seed` (§F3) — runner keeps generated metadata aligned to terminal source provenance.
  - `test_run_cluster3_p_attempt_changes_terminal_class` (§C5 + §D7) — initial F1_COMPILE → P attempt 1 yields F0_PARSE → P loop returns `terminated_unrecoverable`; for `condition="P"` assert row has `p_initial_failure_code="F1_COMPILE"`, `p_terminal_failure_code="F0_PARSE"` (§D7 rename), `failure_code="F0_PARSE"`, `c_loop_fired=False`, `p_compile_repair_succeeded=False`, `p_repair_changed_terminal_class=True`.
  - `test_run_cluster3_writes_durable_jsonl` — assert the output JSONL has exactly one row per (kernel, dtype, base_seed) and the sidecar exists.
  - `test_run_cluster3_writes_to_outputs_cluster3_only` — assert the runner refuses output paths under `outputs/cluster1/` or `outputs/cluster2/`.
  - `test_run_cluster3_cli_parses_args` — argparse round-trip for a representative command.

**Tests that must pass.** `cluster3/tests/test_run_cluster3_modal_cli.py`.

**Regression check.** Full suite green; Cluster 2 runner tests unchanged.

**Estimated complexity.** Large (~8 agent-hours; ~900 lines of code mirroring Cluster 2 runner, ~600 lines of tests).

**Dependencies on prior phases.** Phases 0–4.

**Files that should not be modified.** `cluster2/experiments/run_cluster2_modal.py`. `cluster2/feedback/repair_loop.py`. `shared/modal_harness/*`.

**Commit message template.**
```
cluster3: phase 5 — Cluster 3 Modal runner orchestration

Adds cluster3/experiments/run_cluster3_modal.py with Cluster3RunnerConfig,
RunnerDependencies, run_cluster3, and a CLI mirroring the Cluster 2 runner.
P fires on F1_COMPILE via the Phase 3 dispatcher; C fires on F2_* when
condition contains C. Tests use dependency injection; no Modal calls.
```

**Risk + mitigation.** Risk: paired-identity drift against existing none/G/C/G+C artifacts. Mitigation (§E10 + §F1): the runner calls Cluster 3's Phase 5 public `validate_pair_identity` for the full P/no-P pairing contract whenever a control row is available. It may reuse Cluster 2 primitive checks for immutable revision or prompt-hash comparison, but it must not call a Cluster 2 private full pairing-context validator directly. Risk: silent reuse of stale Cluster 2 paths. Mitigation: a runner test asserts the output path is under `outputs/cluster3/` by convention and refuses paths under `outputs/cluster1/` or `outputs/cluster2/`. Risk: Modal API drift causes Cluster 3 to accidentally become a new Modal app/image surface. Mitigation (§J1–§J4): AST tests lock Cluster 3 to local orchestration, inherited C2 resources/timeouts, and synchronous C2 calls without hidden retries.

## 11. Phase 6 — Replay manifest integration

**Purpose.** Build and validate manifest/artifact data that feeds the already-defined public pair identity validator. This phase does not introduce runner-required primitives; `pair_for_condition` and `validate_pair_identity` already exist in `cluster3/replay/no_p_pairs.py`.

**Files to add.**
- `cluster3/contracts/` (new directory) — `cluster3/contracts/no_p_pair_manifest.json`. Initially empty/schema-only; populated by `cluster3/replay/build_no_p_pair_manifest.py` (also new) (§D11c + §G8 — paths concretized):
  - **none / G source.** Reads `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` (the Cluster 1 frozen manifest, which is what Cluster 2 already uses as its replay control source per [cluster2/experiments/run_cluster2_modal.py:43-55](cluster2/experiments/run_cluster2_modal.py:43)). This manifest enumerates the canonical none/G replay-control identities.
  - **C / G+C source.** Reads a list of Cluster 2 output JSONL paths under `outputs/cluster2/` supplied via CLI argument `--cluster2-outputs path1.jsonl path2.jsonl ...`. There is NO module-level "Cluster 2 artifact manifest" file; Cluster 2 artifact identity lives in the sidecars next to the JSONL outputs and in `docs/05_artifacts_and_results_registry.md`. The builder reads each row's `(kernel_class, kernel_name, dtype, base_seed)` directly.
  - Emits paired identity entries keyed on `(kernel_class, kernel_name, dtype, base_seed)` plus `sample_index` when present/derivable or `replay_pair_id` when present, with the source artifact path and a `source_sha256` per identity.
  - Documentation note: if `outputs/cluster2/` paper-scale paths are not yet established at Phase 6 build time, the manifest is built when the first Cluster 2 paper-scale artifact lands, not before. Phase 6 ships the builder script and the manifest schema; the actual manifest file is populated later.
- Manifest entry schema (§F5), one entry per no-P control row:
  - `artifact_id`
  - `artifact_path`
  - `condition`
  - `grammar_variant`
  - `kernel_class`
  - `kernel_name`
  - `dtype`
  - `base_seed`
  - `generation_seed`
  - `sample_index: int | None`
  - `sample_index_source: Literal["row_sample_index", "base_seed_derived", "attempt_index_derived", "missing"]`
  - `replay_pair_id` if present
  - `source_sha256`
  - `prompt_sha256`
  - `model_id`
  - `model_revision`
  - `tokenizer_revision`
  - `temperature`
  - `max_new_tokens`
  - `scale_tier`
  - `compile_success`
  - `functional_success` if present/measured
  - `failure_code` if present
  - `row_index`
  - `row_schema_version` if present
  - `sample_index` derivation rules (§G6):
    - If the source row exposes `sample_index`, use it and set `sample_index_source="row_sample_index"`.
    - Else if a generated Cluster 2 control row lacks top-level `sample_index` and the run schedule proves `base_seed` is one-to-one with sample identity, derive `sample_index = base_seed` and set `sample_index_source="base_seed_derived"`.
    - Else if docs/code for a specific artifact prove `attempt_index` is the correct schedule identity, derive from `attempt_index` and set `sample_index_source="attempt_index_derived"`.
    - Else set `sample_index=None`, `sample_index_source="missing"`, and reject the row for pair validation rather than guessing.
- Manifest loader and resolver extensions in `cluster3/replay/no_p_pairs.py`:
  - `load_no_p_pair_manifest(path) -> NoPPairManifest`.
  - `resolve_no_p_control(manifest, p_row) -> NoPControlManifestEntry`.
  - The resolver uses `pair_for_condition` from Phase 5 to compare P rows against the expected no-P condition: P vs none, G+P vs G, C+P vs C, and G+C+P vs G+C.
  - Validation by pair:
    - For P vs none, compare against the none control row.
    - For G+P vs G, compare against the task-agnostic G row and reject unexpected grammar-variant mismatch.
    - For C+P vs C, compare against the generated Cluster 2 C row.
    - For G+C+P vs G+C, compare against the generated Cluster 2 G+C row and reject unexpected grammar-variant mismatch.
  - `validate_pair_identity` checks the manifest-backed control row and rejects model/tokenizer revision mismatch, temperature mismatch, `max_new_tokens` mismatch, unexpected seed/sample/pair mismatch, `sample_index_source="missing"`, scale-tier conflict, grammar-variant mismatch for G+P/G+C+P unless the comparison explicitly controls for variant, and any source hash mismatch between manifest entry and artifact row source.

**Files to modify.** None (Cluster 1 / Cluster 2 manifests stay frozen).

**Tests to add.**
- `cluster3/tests/test_replay_pairing.py`:
  - `test_pair_for_condition_full_table` — assert the four mappings.
  - `test_validate_pair_identity_accepts_matching_rows`.
  - `test_validate_pair_identity_rejects_diverging_seed`, `_diverging_kernel`, `_diverging_dtype`, `_diverging_prompt_sha`, `_diverging_model_revision`, `_diverging_tokenizer_revision`.
  - `test_build_no_p_pair_manifest_from_fixtures` — runs the builder against synthetic Cluster 1 / Cluster 2 manifests under a tmp dir; asserts the emitted manifest has expected keys.
  - `test_cluster3_manifest_fields_support_validate_pair_identity` (§F1 + §F5) — manifest rows carry all fields needed by the Phase 5 validator.
  - `test_cluster3_manifest_entries_resolve_no_p_controls` (§F1 + §F5) — resolver finds none/G/C/G+C controls for P/G+P/C+P/G+C+P rows.
  - `test_cluster3_manifest_row_contains_pair_identity_fields` (§F5) — per-entry required fields are present.
  - `test_manifest_derives_sample_index_from_base_seed_when_absent` (§G6) — generated Cluster 2 controls without a top-level sample index derive it from `base_seed` only when the schedule proves that identity.
  - `test_manifest_rejects_missing_sample_index_when_not_derivable` (§G6) — rows with `sample_index_source="missing"` cannot be used for pair validation.
  - `test_validate_pair_identity_accepts_c2_generated_control_with_derived_sample_index` (§G6) — C/C+P and G+C/G+C+P controls validate when the manifest records a proven derived sample index.
  - `test_validate_pair_identity_rejects_model_revision_mismatch` (§F5).
  - `test_validate_pair_identity_rejects_temperature_mismatch` (§F5).
  - `test_validate_pair_identity_rejects_scale_tier_conflict` (§F5).
  - `test_validate_pair_identity_rejects_source_hash_mismatch` (§F5).
  - `test_cluster3_contracts_directory_exists` (§G8) — Phase 6 scaffolding includes `cluster3/contracts/`.
  - `test_build_no_p_pair_manifest_module_importable` (§G8) — `cluster3.replay.build_no_p_pair_manifest` imports without heavy runtime side effects.

**Tests that must pass.** `cluster3/tests/test_replay_pairing.py`.

**Regression check.** Full suite green; **no** existing manifest under `cluster2/contracts/` is modified.

**Estimated complexity.** Medium (~4 agent-hours).

**Dependencies on prior phases.** Phases 0, 2, and 5 (`cluster3/replay/no_p_pairs.py`).

**Files that should not be modified.** `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` and any file under `outputs/`.

**Commit message template.**
```
cluster3: phase 6 — no-P pair manifest and replay identity validation

Adds cluster3/contracts/ and a manifest builder/loader that provide
artifact-backed no-P controls for the Phase 5 pair identity validator
(P↔none, G+P↔G, C+P↔C, G+C+P↔G+C) without mutating existing Cluster 1 or
Cluster 2 manifests.
```

**Risk + mitigation.** Risk: accidental mutation of Cluster 2's frozen manifest. Mitigation: a test asserts a known checksum of `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` is unchanged after running the builder.

## 12. Phase 7a — Analyzer additive Cluster 3 support (§B6)

**Purpose.** Teach `shared/analysis/factorial.py` to consume Cluster 3 rows, compute the four new paired comparisons, emit the 3-way interaction term, and add a `compile_feedback_active` column alongside the existing `perf_feedback_active` column without breaking the byte-identical 2² output (§B6).

**Phase 7b (deferred to a separate PR, OUT OF SCOPE for v1).** Remove `perf_feedback_active`, rename the factor column, bump analyzer schema. Tracked in `docs/08_decision_log.md` via Phase 10.

**Files to modify.**
- `shared/analysis/factorial.py`:
  - **§C8 + §E6 binding — do NOT extend `PAIRED_REPLAY_COMPARISONS` as a module constant.** Add two new module-level definitions:
    - `P_PAIRED_REPLAY_COMPARISONS: dict[str, str] = {"P": "none", "G+P": "G", "C+P": "C", "G+C+P": "G+C"}`.
    - `effective_paired_replay_comparisons(populated_cells: Sequence[str]) -> dict[str, str]` — returns the union of `PAIRED_REPLAY_COMPARISONS` plus any P pair whose treatment AND control are both in `populated_cells`. Preserves dict insertion order (Cluster 2 pairs first, then P pairs).
  - **§E6 P/no-P pair resolver.** Add `paired_p_factor_summary(df, *, treatment_condition, control_condition, response_variable, allow_incomplete_coverage=False, allow_mixed_grammar_variant=False) -> pd.DataFrame`, implemented on top of the generalized `paired_condition_summary(...)` path rather than `paired_replay_summary(...)`. Rationale: P pairs include generated Cluster 2 controls (`C`, `G+C`) as well as replay controls (`none`, `G`), while `paired_replay_summary(...)` assumes generated-vs-replay metadata for `PAIRED_REPLAY_COMPARISONS` only.
    - Handles `P vs none` and `G+P vs G` where controls may be replay/no-P rows from existing Cluster 1 artifacts.
    - Handles `C+P vs C` and `G+C+P vs G+C` where controls are generated Cluster 2 rows.
    - Keys on `(kernel_class, dtype, base_seed)` plus `sample_index` or `replay_pair_id` when present in the current row schema. Include `kernel_name` / `kernel_id` when available to avoid cross-kernel collisions.
    - Rejects mixed grammar variants across a pair unless `allow_mixed_grammar_variant=True` or the comparison explicitly controls for variant. For `G+P vs G` and `G+C+P vs G+C`, variant/hash mismatch is a pairing error, not a warning.
  - **§C8 binding — replace direct iteration of `PAIRED_REPLAY_COMPARISONS`** in two sites:
    - Metadata block at [factorial.py:452-458](shared/analysis/factorial.py:452): iterate `effective_paired_replay_comparisons(populated_cells).items()` instead of `PAIRED_REPLAY_COMPARISONS.items()`. This keeps the 2² metadata bit-identical when no Cluster 3 rows are present.
    - Paired-row builder at [factorial.py:1620-1627](shared/analysis/factorial.py:1620): iterate the effective dict. Existing `ValueError("paired primary comparison cannot be constructed because ...")` under `scope == "primary_functional"` is preserved for the original C / G+C pairs only; for P pairs use `paired_p_factor_summary(...)` and skip missing-control cases with a warning (P pairs are opportunistic until full 8-cell coverage exists).
  - **§B6 additive column.** Update `FACTOR_COLUMNS` at [factorial.py:59](shared/analysis/factorial.py:59) from `("grammar_active", "compiler_feedback_active", "perf_feedback_active")` to `("grammar_active", "compiler_feedback_active", "perf_feedback_active", "compile_feedback_active")`. Both `perf_feedback_active` and `compile_feedback_active` are populated identically from `"P" in parts` ([factorial.py:1069](shared/analysis/factorial.py:1069)). The factorial model uses `compile_feedback_active` for the P term in any NEW interaction expansion; `perf_feedback_active` continues to be present in row-level outputs for backward compatibility with `outputs/analysis/factorial_2x2_preliminary.json`. Group-by code that uses `FACTOR_COLUMNS` ([factorial.py:496](shared/analysis/factorial.py:496)) must dedupe on `(G, C, P)` rather than on the raw columns to avoid creating empty groups; alternatively gate the new column out of the group-by until Phase 7b.
  - In `analyze_factorial`, when P-containing cells are present in `populated_cells`:
    - Emit the additive 3-way interaction `(rate_GCP - rate_GC) - (rate_GP - rate_G) - (rate_CP - rate_C) + (rate_P - rate_none)`.
    - **§D10 binding — do NOT rename `model_type`.** Current code at [factorial.py:1827](shared/analysis/factorial.py:1827) emits `model_type = "full_eight_cell"`, and `shared/tests/test_factorial_analysis.py:888` asserts that exact string. Preserve it verbatim. When all eight cells are populated, the existing `"full_eight_cell"` branch fires; reportability is signaled via the separate `metadata.reportable` key at [factorial.py:471-475](shared/analysis/factorial.py:471) and the `interpretation_flags` list at [factorial.py:476](shared/analysis/factorial.py:476). The `"partial_eight_cell_not_reportable"` string at [factorial.py:1858](shared/analysis/factorial.py:1858) also stays unchanged (existing test at `test_factorial_analysis.py:910` exercises it).
  - Add a normalization pass that maps Cluster 3 rows' P fields onto analyzer-internal columns (`p_repair_attempted`, `p_compile_repair_succeeded` per §B3/§E2, `p_repair_changed_terminal_class` per §C5, `p_repair_trace_summary`). Analyzer `compile_success` and `functional_success` remain row-final outcomes after all active loops; P-terminal success is analyzed only through `p_compile_repair_succeeded`.
  - The analyzer additionally derives a `p_helped: bool` column whose exact predicate is PENDING_RESEARCH (§C5); v1 leaves `p_helped` populated with the conservative definition `p_helped = (failure_code is None) AND p_repair_attempted` (i.e., P was attempted and the row ultimately succeeded). This conservative definition is documented in Phase 10's decision-log entry.
  - The same normalization pass maps C fields onto analyzer-internal columns (`c_loop_fired`, `c_loop_source`, `c_terminal_failure_code`) so downstream code can join direct initial-F2 and post-P-F2 C paths.
  - Update `_scope_metadata` ([factorial.py:2260-2305](shared/analysis/factorial.py:2260)) to recognize partial Cluster 3 coverage.

**Files to add.**
- `shared/tests/test_analyzer_cluster3.py` (or `cluster3/tests/test_analyzer_cluster3.py` if Cluster 3 owns its analyzer tests):
  - `test_analyzer_compile_feedback_alias_matches_perf_feedback` (§B6) — for every fixture row, assert `compile_feedback_active == perf_feedback_active`.
  - `test_analyzer_2x2_reproducible_without_cluster3_rows` (§B6) — fixture none/G/C/G+C only; assert output bit-for-bit matches the pre-change baseline (capture the current `outputs/analysis/factorial_2x2_preliminary.json` as the golden fixture before any Phase 7a edits).
  - `test_analyzer_loads_cluster3_jsonl` — fixture Cluster 3 JSONL with one P row; assert it appears in `populated_cells`.
  - `test_analyzer_emits_paired_p_vs_none` — fixture none + P rows; assert `paired_comparisons` contains the P vs none entry.
  - `test_p_vs_none_pairs_no_p_control_rows` (§E6 + §F10) — fixture generated Cluster 3 P rows paired to none no-P controls from existing Cluster 1/2 artifacts without implying that the none control itself is generated by Cluster 3.
  - `test_gp_vs_g_pairs_replay_control_rows` (§E6) — G+P pairs against G replay controls and validates grammar variant/hash.
  - `test_cp_vs_c_pairs_generated_cluster2_control_rows` (§E6) — C+P pairs against generated C rows.
  - `test_gcp_vs_gc_pairs_generated_cluster2_control_rows` (§E6) — G+C+P pairs against generated G+C rows.
  - `test_p_pair_summary_rejects_mixed_grammar_variant_unless_allowed` (§E6).
  - `test_analyzer_omits_p_pair_when_only_p_present` — only P rows; the pair is skipped, a warning is emitted.
  - `test_analyzer_emits_additive_3way_interaction_when_all_eight_cells_populated` — fixture all eight cells; assert the interaction term is present and numerically equal to the hand-computed expectation.
  - `test_analyzer_rejects_non_p_row_with_p_fields` — a fixture none row with `p_repair_attempted=True` is quarantined / errors.
  - `test_analyzer_handles_p_compile_repair_succeeded_with_f2_failure_code` (§B3) — fixture P row with `p_compile_repair_succeeded=True`, `compile_success=True`, `failure_code="F2_NUMERIC_LARGE"`, `functional_success=False`; assert the row contributes `compile_success=True` to the secondary compile summary and `functional_success=False` to the primary summary, and that `p_repair_changed_terminal_class=True` is preserved in the per-row diagnostic columns.
  - `test_analyzer_metadata_paired_pairs_match_2x2_when_no_cluster3_rows` (§C8) — load fixture with only none/G/C/G+C rows; assert `metadata.paired_primary_comparisons` is exactly the original two entries (C↔none, G+C↔G), proving `effective_paired_replay_comparisons` does NOT add P pairs to the metadata for the 2² case.
  - `test_analyzer_metadata_paired_pairs_extend_when_all_eight_cells_present` (§C8) — load fixture with all eight cells; assert `metadata.paired_primary_comparisons` contains all six entries.
  - `test_analyzer_does_not_raise_on_missing_p_pair_when_only_2x2_populated` (§C8) — load fixture with only none/G/C/G+C and `scope="primary_functional"`; assert no ValueError is raised (P pair entries are not constructed at all).
  - `test_analyzer_module_level_paired_replay_comparisons_unchanged` (§C8 regression guard) — assert `PAIRED_REPLAY_COMPARISONS == {"C": "none", "G+C": "G"}` (the module constant must NOT have been mutated).
  - `test_analyzer_p_helped_derived_conservatively` (§C5) — fixture row with `p_repair_attempted=True`, `failure_code=None` ⇒ derived `p_helped=True`. Same row with `failure_code="F2_NUMERIC_LARGE"` ⇒ `p_helped=False` (under the conservative v1 definition).
  - `test_cluster3_row_does_not_carry_p_helped` (§C5 boundary, may live in `cluster3/tests/test_cluster3_schema.py`) — `p_helped` is analyzer-derived only and must not appear in the row schema.

**Tests that must pass.** New analyzer tests + all existing `shared/tests` and `cluster1/tests` and `cluster2/tests`.

**Regression check.** Existing analyzer outputs under `outputs/analysis/` should be byte-identical when re-run on existing inputs. The "2x2 reproducible without cluster3" test enforces this.

**Estimated complexity.** Large (~10 agent-hours; analyzer is 2916 lines and the change touches paired-comparison and scope-metadata code paths).

**Dependencies on prior phases.** Phases 0–2.

**Files that should not be modified.** `outputs/` (read-only). `cluster1/`, `cluster2/` source code.

**Commit message template.**
```
shared: phase 7 — analyzer recognizes Cluster 3 P-containing cells

Extends shared/analysis/factorial.py with paired P-comparisons (P vs none,
G+P vs G, C+P vs C, G+C+P vs G+C), the additive 3-way interaction term,
and a normalization pass for Cluster 3 p_* fields. Existing 2^2 outputs
remain byte-identical when Cluster 3 rows are absent.
```

**Risk + mitigation.** Risk: silent regression of the 2^2 analyzer output. Mitigation: the golden-fixture test captures the current output and the test fails if any byte changes when no Cluster 3 rows are present. Risk: F3_EVAL_PIPELINE policy ([06_failure_taxonomy_and_eval_ladder.md:87-97](docs/06_failure_taxonomy_and_eval_ladder.md:87)) interacts with P-repaired rows in unexpected ways. Mitigation: a test asserts that F3 rows in Cluster 3 outputs are handled the same way as Cluster 2 (excluded from compile-success denominators).

## 13. Phase 8 — F1 corrupted fixture smoke

**Purpose.** Local analog of Cluster 2's F2 corrupted-fixture smoke. Curate Triton kernels with known compile errors and verify that the P loop fires and produces well-formed feedback.

**Files to add.**
- `cluster3/tests/fixtures/f1_compile_kernels/` — small `.py` files each carrying a deliberately broken Triton kernel:
  - `invalid_decorator.py` — `@triton.jot` (typo) instead of `@triton.jit`. Expected: F0_NO_DECORATOR (proves the dispatcher terminates, P does not fire).
  - `bad_constexpr.py` — uses an undefined `tl.constexpr` symbol. Expected: F1_COMPILE.
  - `wrong_launch_signature.py` — launcher signature mismatches the kernel signature. Expected: F1_COMPILE or F0_BAD_SIGNATURE depending on where the mismatch surfaces.
  - `type_error_in_pointer_arith.py` — pointer arithmetic on incompatible dtypes. Expected: F1_COMPILE.
- `cluster3/tests/test_p_repair_f1_fixtures.py`:
  - `test_invalid_decorator_terminates_p_does_not_fire` — dispatcher returns `terminate`, `p_repair_attempted=False`.
  - `test_bad_constexpr_triggers_p_loop` — first attempt F1_COMPILE; mock the second generation to return a kernel with the constexpr fixed; assert P succeeds; `p_repair_attempted=True`, `p_compile_repair_succeeded=True` (§B3), `p_repair_changed_terminal_class=True` (§C5), `attempts_executed=2`.
  - `test_p_loop_exhausts_budget_on_persistent_compile_error` (§D11b corrected) — all attempts F1_COMPILE; assert `status="compile_unchanged_exhausted"` (the §C3 enum, NOT the old `"exhausted"`), `stop_reason="p_budget_exhausted"`, `attempts_executed == DEFAULT_P_REPAIR_BUDGET + 1` (seed + budget new generations).
  - `test_p_feedback_contains_no_level2_information` — for any fixture, assert the feedback prompt does not contain `correctness`, `numerical`, `nan`, `inf`, or shape-mismatch language.
  - `test_p_feedback_excerpt_truncated_at_2000_chars` — synthesize a 5000-char compile error; assert the prompt's Compile error section is exactly 2000 chars (excluding header).
  - `test_p_raw_error_excerpt_sha256_matches_full_error` — assert `hashlib.sha256(full_error.encode()).hexdigest() == p_raw_error_excerpt_sha256`.

**Files to modify.** None.

**Tests that must pass.** `cluster3/tests/test_p_repair_f1_fixtures.py`.

**Regression check.** Full suite green.

**Estimated complexity.** Medium (~5 agent-hours; fixture curation is the hardest part).

**Dependencies on prior phases.** Phases 0–5.

**Files that should not be modified.** Anything outside `cluster3/tests/`.

**Commit message template.**
```
cluster3: phase 8 — F1 compile-error fixture smoke

Adds cluster3/tests/fixtures/f1_compile_kernels/ with curated broken Triton
kernels and cluster3/tests/test_p_repair_f1_fixtures.py asserting the P loop
fires on F1_COMPILE, terminates on F0_NO_DECORATOR, exhausts at budget on
persistent compile errors, and produces feedback within the 2000-char cap.
```

**Risk + mitigation.** Risk: fixtures import torch/triton and break the local-import contract. Mitigation: fixtures are read as source strings, never imported at test collection time. Risk: real Triton compile error text varies by version, breaking the substring assertions. Mitigation: tests assert structural properties (length cap, sha256 match, absence of forbidden terms), not specific error wording.

## 14. Phase 9 — Cluster 3 boundary tests

**Purpose.** Enforce the methodology guardrails: P only fires on F1_COMPILE, P feedback never leaks Level 2 or task-specific information, dispatcher routes match the table.

**Files to add.**
- `cluster3/tests/test_cluster3_boundary.py`:
  - `test_p_does_not_fire_on_f0_codes` — every F0_* code; dispatcher returns terminate.
  - `test_p_does_not_fire_on_f1_runtime` — F1_RUNTIME; dispatcher terminates with `unrecoverable_runtime`.
  - `test_p_does_not_fire_on_f2_codes` — every F2_*; dispatcher terminates (or routes to c_loop if condition contains C, never to p_loop).
  - `test_p_does_not_fire_on_f3_codes` — every F3_*; dispatcher terminates.
  - `test_p_feedback_excludes_numerical_mismatch_language` — for an F1_COMPILE fixture, the built prompt does not contain `numeric`, `numerical`, `mismatch`, `nan`, `inf`, `shape`.
  - `test_p_feedback_excludes_speedup_profiler_language` (§C7) — assert `cluster3.feedback.sanitizer.validate_no_forbidden_p_terms` is invoked and the prompt has none of `speedup`, `nsight`, `ncu`, `profil`, `timing`, `performance`. **Does NOT call Cluster 2's `validate_no_forbidden_feedback_terms`.**
  - `test_p_feedback_does_not_expose_eval_set_details` — assert prompt does not contain `eval_shape_set`, `hidden`, `private`, `edge cases`, `extra shapes`.
  - `test_p_feedback_does_not_propose_patches` — diagnostic note from `build_compile_diagnostic_note` is checked by a regex that flags `use `, `try `, `replace `, `should be`, `add a`.
  - `test_p_feedback_allows_llvm_and_ptx_in_error_excerpt` — explicit positive assertion that A2.6's LLVM/PTX exception holds.

**Files to modify.** None.

**Tests that must pass.** `cluster3/tests/test_cluster3_boundary.py`.

**Regression check.** Full suite green.

**Estimated complexity.** Small-medium (~3 agent-hours).

**Dependencies on prior phases.** Phases 0–5.

**Files that should not be modified.** Anything outside `cluster3/tests/`.

**Commit message template.**
```
cluster3: phase 9 — methodology boundary tests

Adds cluster3/tests/test_cluster3_boundary.py asserting P fires only on
F1_COMPILE, P feedback excludes Level 2 numerical language, speedup /
profiler / token / benchmark terms, and eval-set details, and does not
propose code patches. LLVM/PTX in the compile-error excerpt are allowed.
```

**Risk + mitigation.** Risk: regex-based "no patch suggestions" check is brittle. Mitigation: keep the regex narrow and document it in the test; treat the boundary test as an early-warning, not a proof.

## 15. Phase 10 — Documentation updates

**Purpose.** Update methodology docs to reflect the Cluster 3 implementation. No paper-claim language is added; everything remains framed as draft/development until §17–§18 produce real data.

**Files to add.**
- `docs/04_methodology_cluster3.md` — new methodology document mirroring `docs/03_methodology_cluster2.md` structure, citing the implemented files. Sections: factor definition, eval ladder integration, dispatcher policy, P repair policy, feedback content boundary, schema fields, scale policy, and the audit-only research prediction in §20.

**Files to modify.**
- `docs/06_failure_taxonomy_and_eval_ladder.md` — add a short subsection "Cluster 3 P repair fires on F1_COMPILE" under the F1 family description. Do NOT modify the canonical code table.
- `docs/08_decision_log.md` — append decision entries for: F1_RUNTIME deferred to v2, dispatcher in `cluster3/feedback/`, no new failure codes, Cluster 3 schema version 1, 2000-char compile-error excerpt cap, LLVM/PTX allowed in P feedback.
- `docs/05_artifacts_and_results_registry.md` — add a Cluster 3 artifact section listing the planned output paths, the Cluster 3 row schema version, and the no-P pair manifest path.
- `cluster3/README.md` — replace the "Status: NOT STARTED - contract TBD" block with "Status: v1 implemented (development scale); paper-scale deferred", narrow scope to compile-error repair only, and explicitly defer profiler/speedup to a future contract.

**Files to add.** None beyond `docs/04_methodology_cluster3.md`.

**Tests to add.**
- A small doc-consistency test in `cluster3/tests/test_docs_consistency.py`:
  - `test_methodology_doc_exists` — `docs/04_methodology_cluster3.md` is present.
  - `test_decision_log_mentions_cluster3` — `docs/08_decision_log.md` references "Cluster 3" or "P factor".
  - `test_registry_mentions_cluster3_schema_version` — `docs/05_artifacts_and_results_registry.md` contains the string `CLUSTER3_RESULTS_SCHEMA_VERSION` or `cluster3 schema version 1`.

**Tests that must pass.** `cluster3/tests/test_docs_consistency.py` + full suite green.

**Regression check.** Existing methodology docs for Cluster 1 / Cluster 2 are untouched except for the F1 subsection addition.

**Estimated complexity.** Medium (~4 agent-hours of writing).

**Dependencies on prior phases.** Phases 0–9.

**Files that should not be modified.** `docs/02_methodology_cluster1.md`, `docs/03_methodology_cluster2.md` (except cross-references).

**Commit message template.**
```
docs: phase 10 — Cluster 3 methodology and decision-log entries

Adds docs/04_methodology_cluster3.md, updates the failure-taxonomy doc to
note P-on-F1_COMPILE, appends Cluster 3 decisions to the decision log,
registers Cluster 3 artifact paths and schema version, and replaces the
TBD scope in cluster3/README.md.
```

**Risk + mitigation.** Risk: methodology docs drift from code. Mitigation: doc-consistency tests in this phase plus the registry's existing schema/registry/analyzer co-update gate ([docs/05_artifacts_and_results_registry.md:208-215](docs/05_artifacts_and_results_registry.md:208)).

## 16. Phase 11 — Modal n=1 smoke (paid, requires user approval)

**Purpose.** Real Modal run producing one Cluster 3 row to verify the durable JSONL path, provenance metadata, and P repair behavior end-to-end. Cost is small. **This phase requires explicit user authorization before launch** (per project rule against unauthorized Modal runs).

**Pre-flight (must all be true).**
- Phases 0–10 merged.
- `.venv/bin/python -m pytest cluster3/tests cluster1/tests cluster2/tests shared/tests -x` green.
- The four `cluster3/tests/fixtures/f1_compile_kernels/` smoke tests pass.
- A go decision from the user.

**Run plan.**
- Condition: `P` only.
- Kernel: one (`elementwise/relu`, per [shared/eval/correctness_shapes.py:59-65](shared/eval/correctness_shapes.py:59) and [cluster1/data/kernels/elementwise_relu.py:62](cluster1/data/kernels/elementwise_relu.py:62) — kernel_class=`elementwise`, kernel_name=`relu`).
- n: 1.
- Scale tier: `smoke`.
- Modal generation GPU: L4 (matches Cluster 2 default).
- Modal eval GPU: L4 (matches `DEFAULT_C2_MODAL_EVAL_GPU`).
- P repair budget: 1 (smoke shortcut).
- Output: `outputs/cluster3/modal_smoke_p_n1.jsonl`.
- Modal API policy (§J1–§J5): run the ordinary Cluster 3 local CLI and let it invoke existing C2 Modal generation/correctness synchronously. Do not deploy a Cluster 3 app, do not define or run a Cluster 3 Modal entrypoint, do not add `cluster3` to any Modal image, and do not enable retries. The inherited remote limits are C2 generation `timeout=900`, C2 correctness `timeout=900`, and correctness subprocess timeout `600s`.
- Validation commands (run with `.venv/bin/python`):
  1. `.venv/bin/python -m json.tool < outputs/cluster3/modal_smoke_p_n1.jsonl` — parses.
  2. Schema validator: a Phase 2 helper that loads each line into `Cluster3EvalRow`.
  3. Provenance check: assert `model_revision`, `tokenizer_revision`, `modal_image_sha` are populated and immutable per `shared/generation_metadata.is_immutable_hub_revision`.
  4. Scale-tier check: assert `scale_tier == "smoke"`.
  5. Analyzer dry-run: load the row with the Phase 7 analyzer and confirm it shows `P` in `populated_cells` and emits a "P vs none missing pair" warning (because none cell is absent in this smoke).

**Cost / wall-clock — ESTIMATE.**
- One generation call + one or two evaluation calls on L4 is typically minutes and low single-digit dollars at current Modal pricing. Estimate $1–5, 5–15 minutes wall-clock including image build cache hit.

**Stop conditions.**
- Schema validation fails → stop, do not proceed to Phase 12.
- Provenance missing → stop.
- Durable JSONL row absent or malformed → stop.
- Any Modal timeout, preemption, worker interruption, or synthesized infrastructure `F3_EVAL_PIPELINE` result → stop and audit. Do not silently retry inside the runner; a rerun requires explicit user authorization and must use the runner's visible resume/overwrite mode.

**Estimated complexity.** Small (~2 agent-hours of setup + run + audit).

**Dependencies on prior phases.** Phases 0–10. User authorization.

**Files that should not be modified.** Anything under `cluster1/`, `cluster2/`, `cluster3/` source. `outputs/cluster1/`, `outputs/cluster2/` (Phase 11 writes only `outputs/cluster3/`).

**Commit message template.**
```
cluster3: phase 11 — Modal n=1 smoke for P condition

Records outputs/cluster3/modal_smoke_p_n1.jsonl and its sidecar. Smoke
budget P=1. Validates schema, provenance, scale tier, and analyzer
intake. No paper claims; smoke only.
```

**Risk + mitigation.** Risk: image rebuild churn from adding `cluster3` to the Modal image. Mitigation (§C9 + §J1): in v1, **no Modal image change is required**. The existing `triton_compile_image` at [shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21) already bundles `cluster1`, `cluster2`, and `shared` via `add_local_python_source("cluster1", "cluster2", "shared")`. The Cluster 3 path runs the dispatcher, P loop, prompt construction, sanitization, condition adapters, and row construction **locally** in the calling Python process. Only the existing `cluster2.modal.correctness.remote_c2_correctness` ([cluster2/modal/correctness.py:41](cluster2/modal/correctness.py:41)) and `cluster2.modal.generation.RemoteC2Generator.generate_one` ([cluster2/modal/generation.py:173-226](cluster2/modal/generation.py:173)) Modal surfaces round-trip to Modal, and neither of those needs to import `cluster3`. Therefore `add_local_python_source("cluster3")` is explicitly NOT added in v1. Risk: inherited Modal timeouts/preemption are mistaken for model failures. Mitigation (§J4 + §J5): timeout/preemption/infrastructure rows are audited as infrastructure/F3 events and block advancement until reviewed.

## 17. Phase 12 — Development-scale runs (paid, requires user approval)

**Purpose.** n=5 rows per P-containing condition for development-scale evidence on June 8.

**Pre-flight.**
- Phase 11 audited as green.
- The Phase 6 no-P pair manifest is built and validated.
- User authorization for each cell.

**Run plan.**
- Conditions: `P`, `G+P`, `C+P`, `G+C+P` (run sequentially, audit between cells).
- Kernels: the three canonical KernelBench kernels used by Cluster 2 — `elementwise/relu`, `reduction/softmax`, `matmul/gemm` — per [shared/eval/correctness_shapes.py:58-79](shared/eval/correctness_shapes.py:58) and the kernel specs at [cluster1/data/kernels/elementwise_relu.py:62](cluster1/data/kernels/elementwise_relu.py:62), [reduction_softmax.py:62](cluster1/data/kernels/reduction_softmax.py:62), [matmul_tiled_gemm.py:65](cluster1/data/kernels/matmul_tiled_gemm.py:65). (§C10 correction — the v1 spec incorrectly listed add/sum/matmul.)
- n: 5 per (condition, kernel, dtype).
- Scale tier: `development`.
- P repair budget: 5 (full default).
- Output: `outputs/cluster3/dev_p_n5.jsonl`, `outputs/cluster3/dev_gp_n5.jsonl`, `outputs/cluster3/dev_cp_n5.jsonl`, `outputs/cluster3/dev_gcp_n5.jsonl`.
- Modal API policy (§J1–§J5): each condition cell uses the same local orchestration policy as Phase 11. No Cluster 3 Modal App, Function, image, volume, secret, queue, web endpoint, dynamic batching, `.spawn`, `.spawn_map`, `.map`, or hidden retry layer is introduced. Use explicit resume/overwrite only at the local runner level.
- Validation commands (per output, with `.venv/bin/python`):
  1. Row count = 5 × kernels × dtypes.
  2. Every row's `scale_tier == "development"`.
  3. Every row's `(kernel_class, kernel_name, dtype, base_seed)` matches an entry in `cluster3/contracts/no_p_pair_manifest.json` for the paired condition.
  4. At least one row has `p_repair_attempted=True` (otherwise the development run is non-informative about P; reassess fixtures or sample selection per draft §11 decision gates).
  5. Analyzer accepts all four files alongside existing Cluster 1 / Cluster 2 inputs and emits the four paired P comparisons.
  6. Audit-only research-prediction metrics are computed from existing row fields, without adding schema fields: `p_repair_attempted`, `p_compile_repair_succeeded`, `p_repair_stop_reason`, `p_repair_attempt_count`, `p_terminal_failure_code`, `c_loop_fired`, and row-final `failure_code` / `compile_success` / `functional_success`.

**Cost / wall-clock — ESTIMATE.**
- These are conservative estimates, not budgets; the actual spend cap is set by the user at launch.
- P-only conditions (`P`, `G+P`): per row, up to `1 + P_budget` generation/evaluation rounds (default worst case 6).
- C-only inherited controls (`C`, `G+C`, already produced by Cluster 2): per row, up to `1 + C_budget` rounds (default worst case 6).
- P+C conditions (`C+P`, `G+C+P`): per row, up to `1 + P_budget + C_budget` rounds because a row can pay the initial evaluation, P repair attempts, and then C repair attempts after P reaches F2 or after direct initial F2. With defaults this is up to 11 rounds, not 6.
- For the development plan, 45 rows per condition means worst-case round counts of ~270 for P/G+P and ~495 for C+P/G+C+P before queue retries or infrastructure failures. Across all four P-containing conditions the conservative upper bound is ~1530 generation/evaluation rounds. At L4 cost and typical Modal queue latency, keep the user-facing estimate broad ($100–400 total, 2–6 hours wall-clock), and replace it with observed attempt-count distributions after smoke.
- Go/no-go cost guard (§E12): do not run development-scale P+C cells (`C+P`, `G+C+P`) until Phase 11 smoke confirms average P and C repair attempts are within expected bounds and the direct initial-F2 versus post-P-F2 split is visible in rows.

**Stop conditions.**
- Any cell's schema/provenance/pairing check fails → stop and audit.
- Zero P firing across all four cells → stop and revisit fixture selection (draft §11 gate).
- Analyzer cannot pair Cluster 3 rows with the existing Cluster 1 / Cluster 2 controls → stop.
- Any Modal timeout, preemption, worker interruption, or synthesized infrastructure `F3_EVAL_PIPELINE` result in a cell → stop that cell, preserve the partial `outputs/cluster3/` artifact, and audit whether to resume or rerun. Do not count infrastructure failures as P/C feedback-loop failures.

**Audit deliverable.**
- `audits/cluster3_dev_p_n5_report.md` (new) covering row counts, P firing rate, pairing success, analyzer output, and a go/no-go for paper-scale.
- The audit must include a Modal robustness section with observed generation/eval call counts, any timeout/preemption/infrastructure events, whether resume/overwrite was used, and confirmation that no Cluster 3 Modal image/app/function was created.
- The audit must include a research-prediction section that compares P's F1 compile-repair behavior against the current C numerical-repair limitation: report `p_compile_repair_succeeded / p_repair_attempted`, `p_budget_exhausted / p_repair_attempted`, and the qualitative comparison to the current template G+C diagnostic C-loop result where 84 F2 rows reached C and 0 were repaired to functional success. This comparison is interpretive only; it is not a schema gate and does not add P to the existing primary 2^2 analyzer claims.

**Estimated complexity.** Medium (~6 agent-hours: launch orchestration, monitoring, audit).

**Dependencies on prior phases.** Phases 0–11. User authorization per condition.

**Files that should not be modified.** Anything under `cluster1/`, `cluster2/`, `cluster3/` source. Cluster 1 / Cluster 2 outputs.

**Commit message template (one per condition; example for P).**
```
cluster3: phase 12 — development-scale n=5 for condition P

Records outputs/cluster3/dev_p_n5.jsonl and its sidecar. Development tier.
P repair budget 5. Validates row count, scale tier, paired identity against
the no-P pair manifest, and minimum P-firing threshold. No paper claims.
```

**Risk + mitigation.** Risk: scale-tier conflict against existing development artifacts. Mitigation: Cluster 3 development output paths are namespaced under `outputs/cluster3/`. Risk: pair-identity failure because Cluster 1 / Cluster 2 frozen artifacts use a different prompt hash than the Cluster 3 runner regenerates. Mitigation: Phase 6's pair manifest is built from the frozen artifacts and the Cluster 3 runner calls Cluster 3's public `validate_pair_identity` before any row is written.

## 18. Go/no-go decision tree

After each phase:

```
Phase passes its acceptance tests AND regression suite stays green?
├── YES → merge; advance to next phase
└── NO  → do not merge
         ├── failure in new tests → diagnose; fix in same phase
         ├── failure in regression tests → revert local changes;
         │   investigate what unrelated assumption changed
         └── ambiguity in design → re-open Part A §A2; this spec is
             binding — if a phase requires deviating, update both
             the audit addendum and this spec in the same PR
```

Phase 11 / Phase 12 specifically:

```
n=1 smoke (Phase 11) audit clean?
├── YES → advance to n=5 development per condition (Phase 12)
└── NO  → stop; do not run development scale until smoke is clean

n=5 condition cell audit clean (per Phase 12 condition)?
├── YES AND P fired in ≥1 row → advance to next condition
├── YES AND P never fired       → stop; revisit fixture selection
                                  (draft §11 gate)
└── NO → stop; audit and fix before any further runs

All four Phase 12 conditions clean?
├── YES → publish development-scale evidence in the June 8 deck with
         explicit "development tier, not paper claim" framing
└── NO  → publish 2² results only and disclose Cluster 3 status as
         implementation plan + smoke

Paper-scale Cluster 3 runs?
└── DEFERRED to paper revision. Requires:
    - Phase 12 audit clean for all four conditions
    - Empirical resolution of the remaining PENDING_RESEARCH items
      (feedback format ablation, iteration budget ablation,
      repaired-vs-organic reporting convention)
    - A new audit confirming readiness
    - Explicit user authorization
```

## 19. Total agent-time budget (post-review)

| Phase | Estimate | Revision note |
|---|---|---|
| 0 | ~2 h | §C6 + §D1 helpers + mapping tables |
| 1 | ~6 h | §C1 seed_attempt + §C3 status enum + §C7 sanitizer cleanup + §D3 hash-based test + §D4 generation_seed |
| 2 | ~6 h | +1 h vs §C for §D7 `c_loop_fired` split + §D11a attempt-count semantics |
| 3 | ~3 h | §C4 level_reached gating |
| 4 | ~3 h | +1 h vs §C for §D9 nested-identity restamp + post-restamp self-check |
| 5 | ~11 h | +1 h vs §C for §D5 c_repair_budget + §D6 wrapper closure invariants + §D7 row construction |
| 6 | ~4 h | §D11c manifest source concretization absorbed |
| 7 | ~12 h | §D10 model_type rename revoked (less work, not more) |
| 8 | ~5 h | §D11b status-name correction absorbed |
| 9 | ~3 h | unchanged |
| 10 | ~4 h | unchanged |
| 11 | ~2 h (excluding Modal wall-clock) | unchanged |
| 12 | ~8 h (excluding Modal wall-clock) | +2 h for P+C cost guard, attempt-distribution audit, and direct initial-F2/post-P-F2 split checks |
| **Subtotal** | **~69 agent-hours** | +5 h net vs §C; +12 h net vs v1 |

Modal wall-clock for Phases 11 / 12 is separate and listed under each phase's cost ESTIMATE.

## 20. PENDING_RESEARCH carry-over

The following items remain PENDING_RESEARCH because they require empirical evidence that planning cannot synthesize. They are surfaced again in this specification so the implementer does not lose track of them:

1. Optimal compile-error feedback format (structured note vs raw stderr vs both). The Phase 8 fixture smoke and Phase 12 dev-scale runs are the first data points.
2. Optimal P repair budget. v1 uses 5 as a maximum; the Phase 12 audit should report the distribution of `p_repair_attempt_count` for successes vs exhausts.
3. Whether F1_RUNTIME should join the P-eligible set in v2.
4. Empirical interaction between P and C in C+P / G+C+P cells.
5. Final reporting convention for repaired-vs-organic success (primary table, appendix, or audit-only).

None of these block Phases 0–12; they block the paper-revision target.

### Cluster 3 Research Prediction (audit-only)

The Cluster 2 template G+C repair-trace audit reframes C as a limitation characterization rather than a broken loop: numerical F2 feedback was operational but low-information, and the current diagnostic run observed 84 F2 rows with 0 repairs to functional success. Cluster 3 therefore carries an audit-only falsifiable prediction: P should repair a measurably higher fraction of eligible `F1_COMPILE` rows than C repaired eligible F2 rows, because compile-error feedback is typically more localized than numerical mismatch feedback. Useful compile-error feedback may include an error class, a failing source location, a compiler diagnostic, or a concrete token/operator context, while C feedback intentionally avoids private eval details and often reports only aggregate numerical mismatch or NaN/Inf behavior.

This prediction is not a Phase 0-2 contract and does not require new row fields. It is evaluated in Phase 12 using existing fields: `p_repair_attempted`, `p_compile_repair_succeeded`, `p_repair_stop_reason`, `p_repair_attempt_count`, `p_terminal_failure_code`, and row-final success/failure fields. If P repairs a meaningful fraction of `F1_COMPILE` failures, the result supports the claim that feedback information content influences repair success. If P also fails despite localized compile-error feedback, the result supports a model-capability limitation: the model could not synthesize valid repairs even when the diagnostic information was more specific. If P rarely fires, the development run is non-informative about the prediction and sample selection must be revisited before paper-scale claims.

## 21. Specification classification

SPECIFICATION_COMPLETE (post-review revision).

- All 13 implementation phases (0–12) plus 8 supporting sections (1–4, 13, 18–20) are specified.
- Every design decision traces to either Part A §A2, post-review revisions §B–§J, an existing Cluster 2 path, or an existing research citation.
- The phase list is sequencable and gives any implementer enough detail to produce a working commit per phase.
- No paper-scale Cluster 3 claims are made; the specification explicitly defers paper-scale to paper revision.
- No code is written by this document.

## 22. Revision changelog (§B + §C original post-review passes)

Tracks the original §B and §C integration findings and where they are resolved in this document. Later patch passes are tracked in §§23–28.

| # | Finding | Resolution location |
|---|---|---|
| §B1 | `P→none`, `G+P→G` skips Level 0/1 gates in Cluster 2 correctness runner | §1 table; §11 Phase 4 (`cluster3_to_cluster2_eval_condition`); §11 tests `test_adapter_translates_*` and `test_adapter_does_not_translate_to_replay_controls` |
| §B2 | `RemoteC2GenerationRequest` rejects non-C/G+C conditions | §1 table; §6 Phase 1 (`condition_adapters.py`); §10 Phase 5 control flow step 1; §10 tests `test_run_cluster3_translates_*_for_generation` |
| §B3 | `p_repair_succeeded` conflated with whole-row success | §1 table; §7 Phase 2 field set + validation; §10 Phase 5 row construction step 6; §10 tests `test_run_cluster3_p_repairs_compile_then_level2_fails_records_f2`; §12 Phase 7 test `test_analyzer_handles_p_compile_repair_succeeded_with_f2_failure_code`; §13 Phase 8 test `test_bad_constexpr_triggers_p_loop` |
| §B4 | C loop rejects Cluster 3 condition labels | §1 table; §6 Phase 1 (`condition_adapters.py`); §10 Phase 5 control flow step 5; §10 tests `test_run_cluster3_c_plus_p_translates_repair_condition`, `test_run_cluster3_p_without_c_does_not_invoke_c_loop` |
| §B5 | Cluster 2 sanitizer hardcodes LLVM/PTX as forbidden | §1 table; §6 Phase 1 (`cluster3/feedback/sanitizer.py`); §6 tests `test_cluster3_sanitizer_terms_match_cluster2_current_terms`, `test_build_p_feedback_prompt_uses_cluster3_sanitizer_only` |
| §B6 | Analyzer P column is `perf_feedback_active` (old meaning) | §1 table; §12 Phase 7a (`compile_feedback_active` additive column); §12 test `test_analyzer_compile_feedback_alias_matches_perf_feedback`; Phase 7b deferred (out of v1 scope) |
| §B7 | Modal entrypoint underspecified | §1 table; §9 Phase 4 (local adapter only, no new `@app.function`, no new image); §9 tests `test_adapter_does_not_import_modal_at_module_level`, `test_adapter_uses_no_new_modal_function` |
| §C1 | P loop seed-attempt re-evaluation hazard | §1 table; §6 Phase 1 (`PSeedAttempt`, `run_p_repair_loop(seed_attempt=...)`); §6 tests `test_p_loop_seed_attempt_does_not_call_*_for_attempt_0`; §10 Phase 5 control flow step 4; §10 test `test_run_cluster3_dispatches_f1_compile_to_p_loop_with_seed_attempt` |
| §C2 | P-to-C handoff discards P-repaired source | §1 table; §10 Phase 5 control flow step 5 (seeded C invocation + wrapped evaluation); §10 tests `test_run_cluster3_c_plus_p_seeds_c_loop_with_p_terminal_source`, `test_run_cluster3_c_plus_p_c_loop_first_eval_uses_cached_f2_result`, `test_run_cluster3_c_plus_p_does_not_regenerate_after_p_repair`; §7 Phase 2 test `test_row_source_hash_equals_terminal_source_hash` (enabling) |
| §C3 | P loop status semantics conflict with §B3 schema | §1 table; §6 Phase 1 (status enum `compile_repaired_then_success` / `compile_repaired_f2_observed` / `post_p_f3_observed` / `compile_unchanged_exhausted` / `terminated_unrecoverable`); §6 tests `test_p_loop_status_*` |
| §C4 | Dispatcher ignores `level_reached` | §1 table; §8 Phase 3 (dispatch rules require `level_reached>=2` for c_loop, `==1` for p_loop); §8 tests `test_dispatch_*_requires_level_reached_*`, `test_dispatch_rejects_level_reached_none` |
| §C5 | Schema too strict for failed P attempts; `changed_outcome` mislabeled "P helped" | §1 table; §7 Phase 2 validation rules (allows F0/F1_RUNTIME/F3 terminal class); §7 field rename `p_repair_changed_outcome → p_repair_changed_terminal_class`; §7 tests `test_cluster3_row_p_attempted_failed_allows_*`, `test_cluster3_row_p_only_after_p_compile_repair_failure_code_matches_p_terminal`; §12 derived analyzer column `p_helped` (conservative v1 definition; final predicate PENDING_RESEARCH) |
| §C6 | Cluster 3 identity helpers missing | §1 table; §5 Phase 0 (`source_class_for_cluster3_condition`, `generation_mode_for_cluster3_condition`); §5 tests `test_source_class_for_cluster3_condition_returns_generated_for_all_p_cells`, `test_generation_mode_for_cluster3_condition_matches_c2_after_translation` |
| §C7 | Sanitizer contradictions (re-export + boundary test wording) | §6 Phase 1 risk note rewritten; §14 Phase 9 test `test_p_feedback_excludes_speedup_profiler_language` rewritten to call `validate_no_forbidden_p_terms` |
| §C8 | Analyzer P-pair gating: extending `PAIRED_REPLAY_COMPARISONS` mutates metadata | §1 table; §12 Phase 7 (`P_PAIRED_REPLAY_COMPARISONS` + `effective_paired_replay_comparisons` helper; iterate the helper at [factorial.py:452-458](shared/analysis/factorial.py:452) and [factorial.py:1620-1627](shared/analysis/factorial.py:1620)); §12 tests `test_analyzer_metadata_paired_pairs_match_2x2_when_no_cluster3_rows`, `test_analyzer_does_not_raise_on_missing_p_pair_when_only_2x2_populated`, `test_analyzer_module_level_paired_replay_comparisons_unchanged` |
| §C9 | Modal image wording contradictions | §17 Phase 11 risk + mitigation rewritten with the correct base-image source set ([shared/modal_harness/images.py:21-30](shared/modal_harness/images.py:21)); explicit "no `add_local_python_source("cluster3")` in v1" statement |
| §C10 | Stale kernel names + DEFAULT_MAX_NEW_TOKENS + p_repair_succeeded carryover | §17 Phase 11 kernel name corrected to `elementwise/relu`; §18 Phase 12 kernel triple corrected to `elementwise/relu`, `reduction/softmax`, `matmul/gemm`; audit Part A §A2.6 corrected via footnote in §C10 of the audit report (1536 not 1024) |

| §D1 | Phase 0 helpers import a Phase 1 file | §5 Phase 0 (mapping tables moved into `cluster3/constants.py`); §6 Phase 1 (`condition_adapters.py` re-exports); §6 test `test_condition_adapter_tables_match_constants` |
| §D2 | §1 table still names old field `p_repair_changed_outcome` | §1 "P success field" row rewritten to use the §C5 final name |
| §D3 | `PRepairAttemptSummary.source` does not exist | §6 Phase 1 test renamed to `test_p_loop_terminal_source_hash_matches_last_attempt` and rewritten to compare sha256 hashes |
| §D4 | `PSeedAttempt` lacks `generation_seed` | §6 Phase 1 dataclass gains `generation_seed: int` field with `>= 0` validation |
| §D5 | `config.c_repair_budget` undefined | §10 Phase 5 `Cluster3RunnerConfig` gains `c_repair_budget`; tests `test_run_cluster3_c_plus_p_passes_c_repair_budget_not_p_repair_budget`, `test_run_cluster3_p_repair_budget_independent_from_c_repair_budget` |
| §D6 | C-loop wrappers receive Cluster 2 condition labels they cannot translate | §10 Phase 5 wrappers close over `outer_c3_condition`; tests `test_run_cluster3_c_wrapper_uses_outer_c3_condition_for_translation`, `test_run_cluster3_c_wrapper_translation_invariant_holds`, `test_run_cluster3_c_wrapper_rejects_unexpected_inner_condition` |
| §D7 | P-terminal and row-terminal classifications were conflated | §7 Phase 2 uses `p_terminal_failure_code` plus C-loop terminal fields; validation rules split P-terminal, C-terminal, and row-final outcomes; tests `test_cluster3_row_c_plus_p_after_c_success_failure_code_is_none`, `test_cluster3_row_c_loop_fired_*`, `test_cluster3_row_p_only_after_p_compile_repair_failure_code_matches_p_terminal`; §10 Phase 5 row construction step 6 updated |
| §D8 | Phase 4 narrative + test had stale image / schema / source_class strings | §9 Phase 4 narrative rewritten; test asserts `GENERATED_SOURCE_CLASS` constant (= `"generated_row"`) |
| §D9 | Restamp omits `correctness_result.identity.condition` | §6 Phase 1 `restamp_cluster3_condition` field list expanded; §9 Phase 4 restamp step expanded; tests `test_adapter_restamps_nested_correctness_result_identity`, `test_adapter_post_restamp_self_check_raises_on_mismatch` |
| §D10 | `model_type` rename would break existing test | §12 Phase 7 rename revoked; existing `"full_eight_cell"` / `"partial_eight_cell_not_reportable"` strings preserved; reportability stays in `metadata.reportable` |
| §D11a | `p_repair_attempt_count` ambiguous after seed-attempt change | §7 Phase 2 bound `[0, p_repair_budget]` (excludes seed); tests `test_cluster3_row_p_repair_attempt_count_excludes_seed`, `test_cluster3_row_p_repair_trace_length_matches_attempt_count_plus_seed` |
| §D11b | Phase 8 still expected `status="exhausted"` | §13 Phase 8 test corrected to `status="compile_unchanged_exhausted"` |
| §D11c | Phase 6 referenced a non-existent Cluster 2 manifest | §11 Phase 6 builder sources concretized to `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` and `--cluster2-outputs` JSONL paths |

All §B/§C/§D findings have addressable resolutions and at least one phase-level acceptance test. The phase order is unchanged.

## 23. Revision changelog (§E blockers)

| # | Finding | Resolution location |
|---|---|---|
| §E1 | Direct initial-F2 C loop missing from Phase 5/schema | §1 C-loop invocation row; §7 Phase 2 fields `c_loop_source`, `c_terminal_failure_code`; §8 dispatcher `c_loop_source="initial_f2"`; §10 Phase 5 initial C path; tests `test_run_cluster3_c_plus_p_initial_f2_invokes_c_loop_without_p`, `test_run_cluster3_gcp_initial_f2_invokes_c_loop_without_p`, `test_schema_allows_c_loop_fired_without_p_repair_attempted_when_source_initial_f2` |
| §E2 | C loop regression to F0/F1/F3 not modeled | §7 Phase 2 separates P terminal outcome from row-final outcome; C terminals allow F0/F1/F2/F3/None; Phase 5 row construction uses C terminal for final row fields; tests `test_p_compile_repair_succeeded_survives_c_regression_to_f1`, `test_final_row_compile_success_reflects_c_terminal_not_p_terminal`, `test_c_loop_terminal_allows_f0_f1_f2_f3_none`, `test_p_to_f2_then_c_to_f1_row_validates` |
| §E3 | Stale schema language in §1 | §1 Terminal-code schema row defines `initial_failure_code`, `p_terminal_failure_code`, `c_terminal_failure_code`, and row `failure_code` binding |
| §E4 | Correctness adapter infrastructure-payload handling | §6 Phase 1 restamp contract and §9 Phase 4 adapter gate nested correctness-result identity checks; tests `test_cluster3_correctness_adapter_allows_infra_payload_without_correctness_result`, `test_cluster3_correctness_adapter_restamps_success_payload_identity`, `test_cluster3_correctness_adapter_preserves_f3_eval_pipeline_payload` |
| §E5 | Missing Cluster 3 correctness-result extraction | §9 Phase 4 adds `cluster3/modal/result_extraction.py` and `extract_or_synthesize_cluster3_correctness_result_dict`; tests `test_extract_cluster3_*` |
| §E6 | Analyzer P-pair helper compatibility | §12 Phase 7 adds `paired_p_factor_summary` backed by `paired_condition_summary`, generated/replay control support, key rules, and grammar-variant rejection; tests `test_p_vs_none_pairs_no_p_control_rows`, `test_gp_vs_g_pairs_replay_control_rows`, `test_cp_vs_c_pairs_generated_cluster2_control_rows`, `test_gcp_vs_gc_pairs_generated_cluster2_control_rows`, `test_p_pair_summary_rejects_mixed_grammar_variant_unless_allowed` |
| §E7 | Weak PSeedAttempt binding | §6 Phase 1 extends `PSeedAttempt` identity fields and evaluation evidence validation; §10 Phase 5 construction list includes generation seed, base seed, sample index, kernel class, kernel name, dtype, source hash, prompt hash, and initial evaluation result; tests `test_p_seed_attempt_*` |
| §E8 | Post-P F3 overclaimed as compile repair | §1 P-loop status row and §6 Phase 1 rename to `post_p_f3_observed`; Phase 5 sets P-terminal compile repair success only with compile evidence; tests `test_post_p_f3_without_compile_evidence_not_compile_repaired`, `test_post_p_f3_with_compile_evidence_can_mark_compile_repaired`, `test_f3_eval_pipeline_level0_does_not_set_p_compile_repair_succeeded` |
| §E9 | Missing `trace_summary` clarity | §7 Phase 2 includes required generated-row `trace_summary` and defines terminal row semantics; tests `test_cluster3_row_requires_trace_summary`, `test_trace_summary_mentions_p_and_c_loop_status_without_private_data`, `test_run_cluster3_trace_summary_is_terminal_whole_row_summary` |
| §E10 | Pair identity helper mismatch | §10 Phase 5 defines the public validator; §11 provides manifest-backed controls; tests `test_cluster3_validate_pair_identity_for_p_vs_none`, `test_cluster3_validate_pair_identity_for_cp_vs_c`, `test_cluster3_runner_uses_public_validate_pair_identity` |
| §E11 | Sanitizer drift test weakness | §6 Phase 1 sanitizer drift contract and `test_cluster3_sanitizer_terms_match_cluster2_current_terms` compare Cluster 3's public config against Cluster 2's current term list |
| §E12 | Phase 12 cost underestimate | §17 Phase 12 cost section distinguishes P-only, C-only, and P+C worst cases and adds the P+C go/no-go guard |

## 24. Revision changelog (§F cleanup)

| # | Finding | Resolution location |
|---|---|---|
| §F1 | Phase 5 used pair identity validation before the spec introduced it | §1 pair identity row; §2 file tree; §10 Phase 5 adds `cluster3/replay/no_p_pairs.py`, `pair_for_condition`, and public `validate_pair_identity`; §11 Phase 6 becomes manifest integration using those primitives |
| §F2 | Direct initial-F2 C path underspecified at call site | §1 C-loop row; §10 Phase 5 adds `run_cluster3_c_loop_from_f2(...)` with one shared contract for `initial_f2` and `post_p_f2`; tests `test_run_cluster3_c_loop_from_f2_*` |
| §F3 | Terminal source provenance missing | §7 Phase 2 adds terminal source provenance fields and validation; §10 Phase 5 row construction populates them; tests `test_terminal_source_stage_*`, `test_row_source_hash_equals_terminal_source_hash`, and `test_generated_metadata_generation_seed_equals_terminal_generation_seed` |
| §F4 | `trace_summary` type/API undefined | §6 Phase 1 defines `Cluster3TraceSummary`; §7 Phase 2 requires row `trace_summary` to use it; tests `test_cluster3_trace_summary_*` |
| §F5 | Phase 6 manifest schema too thin for validator | §11 Phase 6 lists full manifest entry fields and validation rules; tests `test_cluster3_manifest_row_contains_pair_identity_fields`, `test_validate_pair_identity_rejects_*` |
| §F6 | PSeedAttempt hash/kernel binding weak | §6 Phase 1 adds `kernel_name`, source hash equality, prompt hash validation, and parent identity binding; §10 Phase 5 construction list updated |
| §F7 | Dispatcher validation order ambiguous | §8 Phase 3 defines condition/code/level validation before success or terminal shortcuts; tests `test_dispatcher_rejects_unknown_*` and `test_dispatcher_validates_failure_code_level_compatibility` |
| §F8 | Inactive P metadata ambiguous | §7 Phase 2 records P config constants for inactive rows while keeping attempt/outcome fields null or false; §H1 updates inactive rows to use non-null `p_not_applicable` stop reason; tests `test_inactive_p_rows_record_p_config_but_no_p_attempt`, `test_direct_initial_f2_c_row_has_p_attempt_count_zero`, `test_inactive_p_terminal_fields_are_null_or_false_except_stop_reason` |
| §F9 | Stale changelog test name | §22 §C2 row now references `test_row_source_hash_equals_terminal_source_hash` |
| §F10 | P vs none analyzer wording implied generated controls | §12 Phase 7 test renamed to `test_p_vs_none_pairs_no_p_control_rows`; §23 §E6 row updated accordingly |

## 25. Revision changelog (§G contract cleanup)

| # | Finding | Resolution location |
|---|---|---|
| §G1 | C-loop helper return type was source/provenance-light | §1 C-loop row and §10 Phase 5 define `Cluster3CLoopResult`; row construction uses its terminal source/provenance and correctness fields; tests `test_cluster3_c_loop_result_*` |
| §G2 | `run_cluster3_c_loop_from_f2(...)` lacked `kernel_name` | §10 Phase 5 helper signature adds explicit `kernel_name`; tests `test_run_cluster3_c_loop_from_f2_requires_kernel_name` and `test_run_cluster3_c_loop_from_f2_passes_kernel_name_to_eval_identity` |
| §G3 | C terminal seed provenance ambiguous | §1 P-to-C seed handoff and §10 Phase 5 C adapter semantics preserve seed-candidate seed for budget-zero and capture per-attempt C seeds; tests `test_c_loop_*_seed_*` |
| §G4 | `Cluster3TraceSummary` could not satisfy Phase 2 validation claims | §6 Phase 1 adds terminal hashes, terminal seed/prompt hash, final success flags, repair/eval success, and row source hash; §7 Phase 2 adds cross-checks; tests `test_trace_summary_*` |
| §G5 | Dispatcher tests contradicted validation order | §8 Phase 3 tests now expect ValueError for F-code/level mismatches and unknown condition/code cases |
| §G6 | Manifest `sample_index` assumed a top-level C2 field | §11 Phase 6 makes `sample_index` optional with `sample_index_source` derivation/rejection rules; tests `test_manifest_derives_sample_index_from_base_seed_when_absent`, `test_manifest_rejects_missing_sample_index_when_not_derivable`, and `test_validate_pair_identity_accepts_c2_generated_control_with_derived_sample_index` |
| §G7 | P stop-reason contract incomplete | §5 Phase 0 constants and §6 Phase 1 status-to-stop-reason table add `p_compile_repaired_f2_observed`, F3 evidence split, non-repairable F0/F1_RUNTIME handling, and `p_not_applicable`; tests `test_p_stop_reason_*` |
| §G8 | Spec hygiene gaps in target tree and tests | §2 file tree and §11 Phase 6 add `cluster3/contracts/no_p_pair_manifest.json` and `cluster3/replay/build_no_p_pair_manifest.py`; §6 Phase 1 pass list includes `cluster3/tests/test_cluster3_trace.py`; Phase 0 wording no longer says "three tests" |

## 26. Revision changelog (§H pre-Phase-0 cleanup)

| # | Finding | Resolution location |
|---|---|---|
| §H1 | P stop-reason semantics contradicted inactive-P schema | §1 P-loop status row, §7 Phase 2 inactive-P policy, and §10 Phase 5 row construction require `p_repair_stop_reason="p_not_applicable"` when P does not fire and require every row to populate `p_repair_stop_reason`; tests `test_inactive_p_rows_use_p_not_applicable_stop_reason`, `test_direct_initial_f2_c_row_uses_p_not_applicable_stop_reason`, and `test_phase5_row_construction_always_populates_p_repair_stop_reason` |
| §H2 | `PSeedAttempt.prompt_hash` was optional in one place and required in another | §1 P-loop seed handoff and §6 Phase 1 make `prompt_hash: str` required for new Cluster 3 seeds, validate sha256 shape, and bind it to stored prompt text or prompt construction metadata; tests `test_p_seed_attempt_requires_prompt_hash`, `test_p_seed_attempt_rejects_missing_prompt_hash`, and `test_p_seed_attempt_prompt_hash_matches_prompt_metadata_when_prompt_not_stored` |
| §H3 | `c_attempt_count` did not define whether the seed candidate was counted | §1 C-loop row, §6 Phase 1 `Cluster3TraceSummary`, and §10 Phase 5 `Cluster3CLoopResult` define `c_attempt_count` as generated C repairs only, excluding the seed F2 candidate; tests `test_c_attempt_count_*` |
| §H4 | C-loop feedback builder type was broader than Cluster 2's public contract | §1 C-loop row and §10 Phase 5 helper signature define `FeedbackCallable = Callable[[RepairFeedbackInput], str | None]` and allow `feedback_builder=None` for the Cluster 2 default; tests `test_c_loop_accepts_cluster2_feedback_callable_signature`, `test_c_loop_allows_none_feedback_builder_for_default`, and `test_c_loop_rejects_feedback_builder_that_includes_p_compile_error_text` |
| §H5 | Trace-summary validation overclaimed Phase 1 row-level checks | §1 Trace summary row and §6 Phase 1 keep trace validation self-contained; §7 Phase 2 owns row-vs-trace provenance and final-success cross-checks; tests `test_cluster3_trace_summary_self_contained_invariants`, `test_cluster3_trace_summary_matches_row_terminal_provenance`, and `test_cluster3_trace_summary_matches_row_final_success_flags` |
| §H6 | `Cluster3ReplayRowMetadata` claimed to mirror generated metadata | §7 Phase 2 now states it mirrors/extends `Cluster2ReplayRowMetadata` for no-P control artifact rows and is separate from generated row metadata; tests `test_cluster3_replay_row_metadata_mirrors_cluster2_replay_metadata_contract` and `test_cluster3_replay_row_metadata_not_used_as_generated_row_metadata` |
| §H7 | Phase 0 preflight did not define dirty-tree acknowledgement | §4 preflight checklist and §5 Phase 0 report fields require `preflight_git_status`, `known_dirty_paths`, dirty-path classification, and explicit acknowledgement before building on unrelated code/artifact changes; tests `test_phase0_report_exposes_dirty_tree_fields` and `test_phase0_report_dirty_path_semantics_marked_for_audit` validate the report structure while semantic correctness remains human/audit reviewed |

## 27. Revision changelog (§I final pre-Phase-0 cleanup)

| # | Finding | Resolution location |
|---|---|---|
| §I1 | P-loop `stop_reason` under-specified for successful and compile-repaired terminals | §1 P-loop status row, §6 Phase 1 `P_REPAIR_STATUS_TO_STOP_REASON` table, and §10 Phase 5 row construction now require every P terminal status to populate `PRepairLoopResult.stop_reason`; Phase 5 copies it to `p_repair_stop_reason`; tests `test_p_loop_*_sets_stop_reason`, `test_p_loop_unknown_status_rejected_before_row_construction`, and `test_phase5_copies_p_loop_stop_reason_to_row` |
| §I2 | Phase 0 report-field tests lacked a concrete artifact/schema | §5 Phase 0 now requires `audits/cluster3_phase0_scaffolding_report.md`, required headings, machine-checkable field labels, allowed classifications, and pytest checks over that artifact |
| §I3 | C terminal prompt hash depended on Cluster 2 exposing prompt hashes | §7 Phase 2, §10 Phase 5, and `Cluster3CLoopResult` now define `terminal_prompt_hash_source`; generated C attempts hash captured `RepairGenerationInput.prompt`, while seed candidate terminals may use inherited metadata or `seed_prompt_unavailable`; tests `test_terminal_prompt_hash_*` |

## 28. Revision changelog (§J Modal API specificity)

| # | Finding | Resolution location |
|---|---|---|
| §J1 | Modal image/source-packaging contract still depended on informal "no new image" wording | §1 Modal API boundary row, §9 Phase 4, §10 Phase 5, and §16/§17 paid-run plans explicitly forbid new `modal.App`, `@app.function`, `@app.cls`, `@app.local_entrypoint`, `modal.Image.*`, `modal.Volume`, `modal.Secret`, `modal.Queue`, web endpoints, dynamic batching, and `add_local_python_source("cluster3")`; tests AST-scan Cluster 3 Modal/runner files |
| §J2 | File/project-structure semantics for local adapter versus remote code were implicit | §9 Phase 4 now requires lazy access to the existing C2 Function object and forbids relying on Cluster 3 source mounting inside remote containers; tests assert no module-level Modal import and lazy C2 Function import |
| §J3 | Retry behavior around paid Modal calls was unspecified | §1 Modal robustness row and §10 Phase 5 define no Cluster 3 `retries=`, no `modal.Retries`, no `.spawn`, no `.spawn_map`, no `.map`, and no hidden job queue; infrastructure/F3 outcomes are recorded and audited instead of silently retried |
| §J4 | Timeout source of truth was not tied to existing C2 decorators | §10 Phase 5 and §16/§17 paid-run plans bind timeout policy to existing C2 remote decorators (`timeout=900`) and correctness subprocess timeout (`600s`); Cluster 3 adds no client-side `FunctionCall.get(timeout=...)` wrapper |
| §J5 | Preemption/infrastructure failure handling was not explicit for development-scale runs | §16/§17 stop conditions require timeout/preemption/worker interruption/synthesized infrastructure `F3_EVAL_PIPELINE` events to stop the paid phase, preserve partial artifacts, and require explicit user-authorized resume/rerun; audit deliverable records these events |
