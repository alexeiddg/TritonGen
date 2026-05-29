# Repository Documentation and Methodology Readiness Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`
Phase: Phase 0 - Repository Inventory And Stale-Doc Audit
Scope: Cluster 1 + Cluster 2 preliminary technical-report handoff readiness. Cluster 3/P is deferred.

Execution constraints honored: no Modal invocation, no GPU jobs, no generation, no experiment runs, no output-artifact modification, no grammar modification, no hash re-recording, no commits, and no tracked methodology-doc edits. Local parsing/validation used `.venv/bin/python`.

## 1. Executive summary

Overall classification: `PHASE0_COMPLETE_WITH_WARNINGS`.

Report-writing should not start as final prose yet. Phase 1 can start by creating citation-grade documentation that promotes verified methodology, artifact identities, caveats, and current analyzer semantics. The raw material is now sufficient for documentation construction: the four required JSONL inputs exist, and `outputs/analysis/factorial_2x2_preliminary.json` exists as a valid analyzer output. The current analyzer output is still marked `reportable: false`, so Phase 1 must preserve that caveat instead of turning the analyzer output into overbroad paper claims.

Docs can be created next. The most important next work is to build a clean `docs/` source-of-truth layer that separates current 2^2 results from legacy template-G and n5 history.

Top blockers:

- Citation-grade docs are stale or missing. `docs/` is absent, README files mix current and historical status, and research contracts need status addenda.
- The analyzer output exists but has `metadata.reportable=false`; Phase 1 must explain why and what can be safely claimed.
- G and G+C use 177/180 covered rows, not a complete 180/180 balanced matrix.
- `F3_EVAL_PIPELINE` policy is now present in analyzer metadata but still needs promotion to research methodology docs.
- Cluster 2 code-facing defaults still contain stale token/artifact defaults and must not guide future runs without review.

Top stale docs:

| Path | Issue |
| --- | --- |
| `README.md` | Current 2^2 scope appears, but template-G history remains too prominent for report-facing status. |
| `cluster1/README.md` | Still foregrounds template-G/reference results and does not cleanly present task-agnostic G n20 as the current primary G artifact. |
| `cluster2/README.md` | Still contains stale blocked/path language for task-agnostic G and old C2 status framing. |
| `.contracts/research/scale_policy.md` | Still describes task-agnostic n20 as blocked by n5 gates and cites template G as frozen G. |
| `.contracts/agentic/cluster2_contract.md` | Agent-internal, but stale enough to mislead future agents: template G path and 1536-token defaults. |
| `cluster2/constants.py` | Code-facing stale defaults: `DEFAULT_MAX_NEW_TOKENS=1536` and template G replay path. Do not edit in Phase 0. |
| Old n5/template output summaries | Historical evidence only; not current report artifacts. |

Top update priorities:

1. Create a citation-grade docs skeleton and source-of-truth hierarchy.
2. Promote the current 2^2 scope and defer P/Cluster 3 explicitly.
3. Promote the current artifact registry: none 180, G 177, C 180, G+C 177, analyzer JSON present.
4. Promote the 177/180 skip-not-impute policy.
5. Promote analyzer semantics: Cluster 1 functional success false/unproven, Cluster 2 compile-success normalization, and `F3_EVAL_PIPELINE` treatment.
6. Mark stale agent plans, n5 summaries, and template-G summaries as legacy evidence before any external sharing.

## 2. Scope and commands run

Folders inspected:

| Folder | Purpose | Current relevance | Documentation status |
| --- | --- | --- | --- |
| repository root | Entry points and packaging | High | `README.md`, `pyproject.toml`, `requirements.txt`, `.gitignore` inspected; README needs update. |
| `docs/` | Intended citation-grade docs | High for next phase | Directory absent/not populated. |
| `.contracts/research/` | Formal methodology constraints | High | Mostly useful, but `scale_policy.md` and `eval_metrics.md` need current status updates. |
| `.contracts/agentic/` | Agent working context | Evidence/working context only | Many plans are stale or superseded; do not cite directly. |
| `audits/` | Evidence trail | High as evidence | Useful but mixed currency; this report supersedes older blocker status. |
| `cluster1/` | G implementation and compile-only evaluation | High | Code/tests current; README needs update. |
| `cluster2/` | C and G+C implementation, replay, Modal evaluation | High | Code/tests/artifacts mostly current; README/constants need update. |
| `cluster3/` | P factor | Deferred | README correctly states not started/TBD. |
| `shared/` | Shared eval, analyzer, factors, Modal harness | High | Analyzer output now produced; docs must explain semantics. |
| `outputs/` | Raw and derived artifacts | High | Current artifacts exist; many old summaries are legacy evidence. |
| tests under `cluster1/tests`, `cluster2/tests`, `shared/tests` | Behavioral traceability | High | Used as traceability; no tests were run in this phase beyond read-only parsing. |

Required commands run:

```text
git status --short
sed -n '1,260p' .contracts/agentic/preliminary_report_handoff_readiness_plan.md
find . -maxdepth 3 -type f | sort
rg --files -u
rg --files -u | rg '(^|/)(README|.*\.md)$'
rg --files -u .contracts audits
find outputs -maxdepth 4 -type f | sort || true
git log --oneline --decorate -n 50
git log --oneline -- README.md docs .contracts audits cluster1 cluster2 shared 2>/dev/null || true
rg "template_upper_bound|template G|template grammar|upper bound" . -u
rg "task_agnostic|triton_kernel_agnostic|grammar_variant|grammar_active" . -u
rg "2\^3|full factorial|eight cells|none / G / C / P|G\+C\+P|Cluster 3|P condition|performance feedback" . -u
rg "2\^2|subset|none.*G.*C.*G\+C|preliminary" . -u
rg "max_new_tokens|max-new-tokens|512|1536|2048|2560" . -u
rg "functional_success|compile_success|Level 2|correctness|compile-only|compile only|Level 1" . -u
rg "grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|generated_metadata" . -u
rg "baseline_repaired_l4_n20|task_agnostic_g_aligned_pipeline_n20_l4|c_paper_n20_l4|g_plus_c_paper_n20_l4|g_task_agnostic_n5|n5|n=5" . -u
rg "F0_|F1_|F2_|F3_|failure_code|failure taxonomy|correctness_result|F3_EVAL_PIPELINE" . -u
rg "Modal|modal_image_sha|tokenizer_revision|model_revision|provenance|image_provenance" . -u
rg "seed|matched|paired|McNemar|bootstrap|interaction|factorial|replay_pair_id" . -u
rg "stale|legacy|deprecated|archive|TODO|FIXME|HOLD|BLOCKED|INCONCLUSIVE" . -u
```

Additional read-only inspection:

- Existing `audits/repository_documentation_methodology_readiness_audit.md` was read before update.
- Artifact validation and analyzer summaries were generated with `.venv/bin/python` without modifying artifacts.
- Git state was clean at phase start.
- Recent history includes `e8f2d60 ANALYZER_OUTPUT_PRODUCED`, `b87c4be factorial_alignment_v3_f3_eval_pipeline_policy`, and earlier analyzer/schema/provenance fixes.

## 3. Repository inventory

| Area | Purpose | Current relevance | Documentation status |
| --- | --- | --- | --- |
| `README.md` | Public entry point | High | Needs update before report; contains mixed current and legacy result framing. |
| `pyproject.toml` | Package metadata/test config | Medium | Describes full 2^3 project goal; acceptable if README clarifies current 2^2 scope. |
| `requirements.txt` | Dependency pin list | Medium | Operational, not methodology; header may be stale. |
| `.gitignore` | Ignore policy | High for process | Ignores `.contracts/agentic/*`, `docs`, `audits`, and `outputs`; outputs in this phase are local unless explicitly promoted. |
| `.contracts/research/` | Formal method contracts | High | Most useful for Phase 1; needs updates for current artifacts/F3 policy. |
| `.contracts/agentic/` | Agent scratch/plans | Medium as evidence | Many stale; classify as `AGENT_INTERNAL` or `LEGACY_EVIDENCE`. |
| `audits/` | Historical verification records | High evidence value | Useful, but older audit conclusions are superseded by latest analyzer output. |
| `cluster1/` | None/G generation and compile-only eval | High | Code/tests current; README stale. |
| `cluster2/` | C/G+C generation, repair, replay, Modal eval | High | Code/tests/artifacts current enough; README/constants stale. |
| `cluster3/` | P factor | Deferred | README says not started/TBD; cite only for deferral. |
| `shared/` | Shared eval/analyzer/factors/modal harness | High | Analyzer and reporting guards are the current behavior source. |
| `outputs/cluster1/` | Cluster 1 raw/summary artifacts | High | Current JSONL artifacts plus many legacy summaries. |
| `outputs/cluster2/` | Cluster 2 raw/hash artifacts | High | Current C/G+C JSONL artifacts plus smoke/dev outputs. |
| `outputs/analysis/` | Derived analyzer outputs | High | Current analyzer JSON exists and is valid. |
| test dirs | Behavior/evaluation traceability | High | Tests provide evidence for boundaries, metadata, replay, analyzer, taxonomy. |

## 4. Artifact inventory

| Artifact | Exists | Valid JSON/JSONL | Rows | Condition values | Kernel/dtype coverage | Key distributions | Known caveats | Report readiness |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | Yes | Yes | 180 | inferred `none` | 3 kernel classes x 3 dtypes x 20 seeds | `compile_success`: false 180; `functional_success`: null 180; `grammar_active`: false 180 | Legacy C1 schema: no failure_code, no model/tokenizer/modal provenance, no replay_pair_id. Compile-only, not Level 2. | Ready as frozen none replay/control evidence with caveats. |
| `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | Yes | Yes | 177 | inferred `G` | Missing matmul/fp32 seed 5 and matmul/bf16 seeds 0,18 | `compile_success`: true 3, false 174; `grammar_valid`: true 49, false 128; `stop_reason`: eos 105, max_new_tokens 72; `failure_code`: null 3, F1_RUNTIME 152, F1_COMPILE 9, F0_PARSE 13 | 177/180 coverage; C1 has no functional correctness; modal image is `unknown` but fallback provenance is present. | Ready as primary task-agnostic G artifact with explicit partial-coverage caveat. |
| `outputs/cluster2/c_paper_n20_l4.jsonl` | Yes | Yes | 180 | `C` | 3 kernel classes x 3 dtypes x 20 seeds | `functional_success`: false 180; `failure_code`: F0_PARSE 180; `compile_success`: absent; `max_new_tokens`: 2048 180 | Compile success must be normalized from failure_code; all rows are F0 parse failures. | Ready as raw C artifact and analyzer input. |
| `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | Yes | Yes | 177 | `G+C` | Same three missing matmul rows as G | `functional_success`: false 177; `compile_success`: true 4, false 173; `grammar_valid`: true 52, false 125; `failure_code`: F1_RUNTIME 146, F0_PARSE 12, F1_COMPILE 10, F3_EVAL_PIPELINE 5, F2_NUMERIC_NAN 4 | 177/180 coverage; F3 rows require the analyzer policy. | Ready as raw G+C artifact and analyzer input with caveats. |
| `outputs/analysis/factorial_2x2_preliminary.json` | Yes | Yes | n/a | populated: none, G, C, G+C | Analyzer loaded 714 rows | Primary functional success: 0 for all four cells. Secondary compile: none 0/180, G 3/177, C 0/180, G+C 4/172 with 5 F3 excluded from rate; paired comparisons emitted. | `metadata.reportable=false`; P cells not populated; model not fit because functional outcome has a single class; F3 policy must be promoted to docs. | Present and authoritative as analyzer output, but not directly paper-claiming without caveats. |

Analyzer metadata highlights:

- `scope_kind`: `temporary_2^2_subset`
- `analyzer_version`: `factorial_alignment_v3_f3_eval_pipeline_policy`
- `cells_missing`: `P`, `G+P`, `C+P`, `G+C+P`
- `g_replay_coverage`: 177/180 with `COVERAGE_WARNING_SKIP_MISSING`
- `f3_eval_pipeline_policy`: F3 rows excluded from compile-success rate calculations and treated as `compile_success=false` in matched-pair analysis when independent compile-pass evidence is absent
- primary paired comparisons: `C vs none` with 180 pairs and `G+C vs G` with 177 pairs, both 0 absolute lift on functional success

## 5. Documentation and contract inventory

Classification legend:

- `AUTHORITATIVE_CURRENT`: current source of truth or current evidence.
- `NEEDS_UPDATE`: useful but stale or incomplete.
- `LEGACY_EVIDENCE`: historical evidence only.
- `AGENT_INTERNAL`: scratch/plan/prompt-like material.
- `DELETE_CANDIDATE_LATER`: candidate for archival/removal after review.
- `UNKNOWN`: requires further investigation.

| Path | Classification | Reason | Grade | Recommended action |
| --- | --- | --- | --- | --- |
| `README.md` | `NEEDS_UPDATE` | Mixed current 2^2 scope and stale template-G/result framing. | Citation-grade only after update | Update in Phase 1/2. |
| `cluster1/README.md` | `NEEDS_UPDATE` | Does not cleanly present current task-agnostic G n20 status. | Citation-grade only after update | Rewrite current status/artifacts/caveats. |
| `cluster2/README.md` | `NEEDS_UPDATE` | Stale C2 readiness and G artifact language. | Citation-grade only after update | Rewrite C/G+C, replay, F2-only repair, analyzer status. |
| `cluster3/README.md` | `AUTHORITATIVE_CURRENT` | Correct for Cluster 3/P deferred status. | Citation-grade for deferral only | Keep. |
| `.contracts/README.md` | `AUTHORITATIVE_CURRENT` | Correctly separates contract roles. | Citation-grade for contract map | Keep. |
| `.contracts/research/research_scope.md` | `NEEDS_UPDATE` | Good scope/factor basis but lacks current artifact/analyzer status. | Citation-grade after addendum | Add current 2^2 artifact status. |
| `.contracts/research/eval_metrics.md` | `NEEDS_UPDATE` | Good ladder/metric basis but lacks promoted F3 policy. | Citation-grade after update | Add `F3_EVAL_PIPELINE` policy. |
| `.contracts/research/cluster1_generated_surface.md` | `AUTHORITATIVE_CURRENT` | Current surface/grammar boundary support. | Citation-grade | Keep. |
| `.contracts/research/scale_policy.md` | `NEEDS_UPDATE` | Stale task-agnostic n20 blocked/template-G language. | Citation-grade after update | Update current scale/artifact policy. |
| `.contracts/research/paper_outline.md` | `NEEDS_UPDATE` | Useful outline, missing current artifact/analyzer state. | Citation-grade after update | Add current status or replace with docs outline. |
| `.contracts/research/phase4_parse_reclassification_disposition.md` | `AUTHORITATIVE_CURRENT` | Useful baseline reclassification evidence. | Citation/evidence hybrid | Keep. |
| `.contracts/research/modal_new_account_setup_guide.md` | `NEEDS_UPDATE` | Operational guide, not current methodology. | Ignored for report | Keep operational only. |
| `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` | `AGENT_INTERNAL` | Master plan for this workflow; not citation-grade. | Ignored/can inform agents | Keep internal. |
| `.contracts/agentic/cluster1_contract.md` | `AGENT_INTERNAL` | Useful but internal and partly old. | Ignored for report | Add status header if reused. |
| `.contracts/agentic/cluster2_contract.md` | `AGENT_INTERNAL` | Stale artifact/token defaults. | Ignored for report | Mark superseded/update before agents use. |
| `.contracts/agentic/*plan*.md` | `AGENT_INTERNAL` or `LEGACY_EVIDENCE` | Historical plans and TODOs. | Ignored/evidence only | Mark legacy; do not cite. |
| `.contracts/agentic/reference/*.md` | `AGENT_INTERNAL` | Cached/reference helper material. | Ignored | Do not cite without verification. |
| `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current evidence for G artifact counts/caveats. | Evidence-grade | Use as traceability, not primary methodology. |
| `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md` | `AUTHORITATIVE_CURRENT` | Current evidence for 177/180 and truncation caveat. | Evidence-grade | Use for caveat trace. |
| `audits/cluster2_c_paper_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current C artifact evidence. | Evidence-grade | Use as trace. |
| `audits/cluster2_g_plus_c_paper_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current G+C artifact evidence. | Evidence-grade | Use as trace with analyzer caveat. |
| `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md` | `AUTHORITATIVE_CURRENT` | Evidence of F3 policy decision. | Evidence-grade | Promote decision into research docs. |
| `audits/factorial_2x2_preliminary_analysis_report.md` | `LEGACY_EVIDENCE` | Superseded by actual analyzer output. | Evidence-grade historical | Add superseded header later. |
| Older n5/template/pre-paper audits | `LEGACY_EVIDENCE` | Useful history but not current artifact status. | Evidence-grade historical | Mark legacy; do not cite as current. |
| `outputs/cluster1/*_summary.md` | `LEGACY_EVIDENCE` or `DELETE_CANDIDATE_LATER` | Many summarize old n5/template/dev runs. | Evidence only | Mark legacy/archive after review. |
| `outputs/cluster1/baseline_repaired_l4_n20_summary.md` | `AUTHORITATIVE_CURRENT` | Current baseline summary with legacy metadata caveat. | Evidence-grade | Safe as baseline trace only. |
| `cluster1/docs/grammar_surface_contract.md` | `AUTHORITATIVE_CURRENT` | Current grammar surface doc. | Citation-grade | Keep. |
| `cluster1/grammar/corpus/api_coverage_report.md` | `AUTHORITATIVE_CURRENT` | Current grammar API coverage support. | Citation/evidence | Keep. |
| `cluster1/notebooks/*.ipynb` | `UNKNOWN` | Not semantically audited. | Ignored | Do not cite without review. |
| `.venv/`, `.pytest_cache/`, `.idea/`, `.claude/` | `UNKNOWN`/ignored | Environment/editor/cache material. | Ignored | Exclude from methodology. |

A fuller file classification baton is also in `.contracts/agentic/preliminary_report_handoff/phase_0_file_classification_table.md`.

## 6. Current methodology reconstruction

### Cluster 1

Cluster 1 implements the `G` factor as task-agnostic grammar-guided decoding plus semantic post-validation. The current primary grammar is `cluster1/grammar/triton_kernel_agnostic.gbnf`. The template grammar remains diagnostic/reference only and must not be reported as the primary grammar effect.

Cluster 1 is compile-only. It supports Level 0/Level 1 evidence but does not prove Level 2 numerical correctness. For the analyzer, Cluster 1 `functional_success` is normalized as false/unproven.

### Cluster 2

Cluster 2 implements `C` and `G+C`. `C` is correctness-feedback repair without grammar. `G+C` is task-agnostic grammar generation plus the same C repair loop.

Correctness feedback is scoped to F2 numerical/correctness failures. F0 parse/signature failures and F1 compile/runtime failures terminate without repair feedback. This protects the C factor from leaking parse/compile/performance guidance into correctness feedback.

### Modal

Modal is methodology infrastructure, not a research factor. It provides controlled cloud GPU generation/evaluation, L4 workers for paper-scale runs, durable row writing, and provenance fields for model revision, tokenizer revision, Modal image provenance, grammar metadata, and package/runtime versions.

### Analyzer

The current analyzer output exists at `outputs/analysis/factorial_2x2_preliminary.json`. It analyzes a temporary 2^2 subset over G and C: `none`, `G`, `C`, and `G+C`.

Analyzer semantics verified in output/code/audits:

- Cluster 1 functional success is normalized false/unproven.
- Cluster 2 C compile success is normalized from `failure_code` when absent.
- `F3_EVAL_PIPELINE` rows are excluded from compile-success rate denominators and treated as compile false in matched-pair analysis when independent compile-pass evidence is absent.
- Pairing uses tuple identity `(kernel_class, kernel_id/kernel_name, dtype, base_seed)`; C2 rows also carry `replay_pair_id`.
- Primary functional comparisons are paired McNemar/bootstrap summaries for `C vs none` and `G+C vs G`.
- The logistic functional model is not fit because all functional outcomes are false.

### Current 2^2 scope

Current report scope is the 2^2 subset: `none`, `G`, `C`, `G+C`. The full 2^3 factorial remains the project goal, but P-containing cells are not populated and are not current results.

### Deferred Cluster 3 scope

Cluster 3/P is deferred. `cluster3/README.md` and analyzer metadata agree that P-containing cells (`P`, `G+P`, `C+P`, `G+C+P`) are not populated.

## 7. Stale or contradictory claims

| Claim | File path | Why stale or contradictory | Correct current statement | Severity | Recommended action |
| --- | --- | --- | --- | --- | --- |
| Template G 180/180 is the primary G result | `README.md`, `cluster1/README.md`, old output summaries | Template G is diagnostic/reference only. | Primary G is task-agnostic G with 177/180 rows; template G is an upper-bound reference. | High | Rewrite report-facing status. |
| Task-agnostic G is planned/blocked | `cluster1/README.md`, `cluster2/README.md`, `.contracts/research/scale_policy.md` | Current n20 task-agnostic artifact exists. | Task-agnostic G exists at 177/180; missing rows are skipped, not imputed. | High | Update docs/contracts. |
| G replay artifact is `final_g_l4_n20.jsonl` | `cluster2/README.md`, `.contracts/agentic/cluster2_contract.md`, `cluster2/constants.py` | That artifact is template/reference G. | Current primary G replay uses `task_agnostic_g_aligned_pipeline_n20_l4.jsonl`. | High | Update or mark superseded. |
| Cluster 2 default max tokens is 1536 | `.contracts/agentic/cluster2_contract.md`, `cluster2/constants.py` | Current paper artifacts record 2048. | Current C/G+C paper-setting artifacts use `max_new_tokens=2048`. | Medium | Update before future runs. |
| Analyzer output missing/blocked | Older readiness audit, `audits/factorial_2x2_preliminary_analysis_report.md` | `outputs/analysis/factorial_2x2_preliminary.json` now exists. | Analyzer output is present but `reportable=false`; caveats remain. | High | Mark older audit status superseded. |
| F3 policy unresolved | Older audit text | Latest analyzer output has an F3 policy. | F3 rows are excluded from compile-success rates and treated compile false for matched analysis absent independent compile-pass evidence. | Medium | Promote policy to `eval_metrics.md`. |
| Full 2^3 is current | `pyproject.toml` if read literally, older plans | P cells are not populated. | Full 2^3 is future project goal; current output is 2^2. | Medium | Clarify in README/docs. |
| n5 summaries are current artifacts | Old summaries/audits | Current preliminary artifacts are n20/177-row artifacts plus analyzer output. | n5 artifacts are development/legacy evidence. | Low | Mark legacy/archive. |

## 8. Traceability gaps

| Claim | Doc path | Code path | Test path | Artifact path | Analysis output | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| Current scope is 2^2 subset | `.contracts/research/research_scope.md` needs status addendum | `shared/analysis/factorial.py`, `shared/factors/registry.py` | `shared/tests/test_factorial_analysis.py`, `shared/tests/test_reporting_tables.py` | Four JSONL inputs | `outputs/analysis/factorial_2x2_preliminary.json` | Citation doc needs current artifact/analyzer addendum. |
| Cluster 3/P deferred | `cluster3/README.md`, research scope | `shared/factors/registry.py` | `shared/tests/test_factor_cells.py` | Analyzer missing cells metadata | Analyzer metadata | Good; keep explicit. |
| G is task-agnostic grammar + semantic validation | `cluster1/docs/grammar_surface_contract.md`, research docs need current artifact addendum | `cluster1/grammar/triton_kernel_agnostic.gbnf`, `cluster1/grammar/triton_kernel_validator.py`, `cluster1/generation/*` | `cluster1/tests/test_grammar.py`, `cluster1/tests/test_generation_provenance.py` | G and G+C artifacts | Analyzer grammar diagnostics | README stale. |
| Template grammar diagnostic only | Research docs mostly support | `shared/generation_metadata.py`, `shared/eval/reporting/grammar_language.py` | `shared/tests/test_reporting_language.py` | Old template artifacts | Analyzer excludes template G from primary cells | README/output summaries overemphasize template history. |
| Cluster 1 compile-only | Research docs | `cluster1/validation/*`, `shared/eval/levels/level1_compile.py` | `cluster1/tests/test_compile_check.py`, shared eval tests | none/G artifacts | Analyzer normalizes functional false | Citation docs should state false/unproven normalization. |
| C and G+C implement correctness feedback | Research docs need current status | `cluster2/feedback/*`, `cluster2/experiments/run_cluster2_modal.py` | `cluster2/tests/test_repair_loop.py`, `cluster2/tests/test_feedback_prompts.py` | C and G+C artifacts | Analyzer paired comparisons | Cluster2 README stale. |
| C repair only on F2; F0/F1 terminate | `eval_metrics.md` mostly | `cluster2/feedback/prompts.py`, `cluster2/feedback/repair_loop.py` | `cluster2/tests/test_feedback_prompts.py`, `cluster2/tests/test_run_cluster2_modal.py` | C/G+C repair traces | Analyzer failure summaries | Promote concise report wording. |
| Modal as infrastructure | research docs partially; Modal docs absent in `docs/` | `shared/modal_harness/*`, `cluster1/experiments/run_cluster1_modal.py`, `cluster2/experiments/run_cluster2_modal.py` | modal/provenance tests | C/G+C provenance fields, hashes sidecars | Analyzer input provenance | Needs `docs/04_modal_infrastructure.md`. |
| Artifact row counts | No citation-grade registry yet | loaders/analyzer | artifact parsing script this phase | all required outputs | analyzer JSON | Needs `docs/05_artifacts_and_results_registry.md`. |
| Analyzer semantics | No citation-grade docs yet | `shared/analysis/factorial.py` | `shared/tests/test_factorial_analysis.py`, `shared/tests/test_reporting_tables.py` | all required outputs | analyzer JSON | Needs `docs/07_analysis_and_statistics.md`. |
| F3 policy | Audit/analyzer metadata only | `shared/analysis/factorial.py` | factorial tests | G+C artifact has 5 F3 rows | analyzer JSON | Must be promoted to research/citation docs. |
| Replay pairing | Manifest/audits; docs incomplete | `cluster2/replay/*`, `shared/analysis/factorial.py` | replay/factorial tests | C/G+C rows carry replay_pair_id; C1 controls pair by tuple | analyzer paired comparisons | Report must explain tuple pairing and missing-row skip. |

## 9. Recommended next phase

Phase 1 can start.

Phase 1 should create a tracked/citation-grade documentation skeleton, not the preliminary report itself. Exact files to create first:

- `docs/00_project_map.md`
- `docs/01_research_story.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/handoff/stale_docs_inventory.md`

Phase 1 must not:

- modify raw artifacts in `outputs/`
- modify grammar files
- re-record hashes
- run Modal, generation, GPU evaluation, or experiments
- overrule analyzer `reportable=false`
- cite `.contracts/agentic/` directly as methodology
- promote template G as the primary G effect
- treat 177/180 as 180/180
- claim Cluster 3/P results

## 10. Appendix

### Artifact summaries

- none: 180 valid rows, inferred condition none, full 3 x 3 x 20 coverage, 0 compile successes, no functional correctness.
- G: 177 valid rows, inferred condition G, task-agnostic grammar, missing matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18, 49 grammar-valid rows, 3 compile successes.
- C: 180 valid rows, condition C, full coverage, all `F0_PARSE`, 0 functional successes, compile_success absent and normalized by analyzer.
- G+C: 177 valid rows, condition G+C, same missing rows as G, 52 grammar-valid rows, 4 explicit compile successes, 0 functional successes, 5 F3 rows handled by analyzer policy.
- Analyzer: valid JSON, 714 rows loaded, 80 cell summaries, 4 paired comparisons, P cells missing, `reportable=false`.

### Search summaries

- Template-G searches found correct diagnostic/reference language in code/tests and stale foregrounding in READMEs and old summaries.
- Task-agnostic searches found current implementation/artifact support and stale planned/blocked wording.
- 2^3/P searches found clear deferral in analyzer output and Cluster 3 README; full factorial remains future goal.
- Token-budget searches found current 2048 in current artifacts and Cluster 1/shared config, but stale 1536 in Cluster 2 constants and C2 agentic contract.
- Functional/compile searches confirmed C1 compile-only and C2 Level 2 boundaries.
- Grammar-valid searches confirmed current G acceptance is joint GBNF parse plus semantic validation.
- Artifact-name searches confirmed required current artifacts exist and n5/template artifacts are historical.
- F0/F1/F2/F3 searches found F3 policy evidence in analyzer/audits and F2-only repair constraints.
- Modal/provenance searches confirmed C/G+C rows include model/tokenizer/modal image provenance; baseline is legacy.
- Seed/pairing searches confirmed tuple-pairing/replay_pair_id support and paired analyzer output.
- Stale/legacy searches found many old audit records and agent plans needing status headers.

### Git history snippets

Recent relevant commits:

```text
e8f2d60 ANALYZER_OUTPUT_PRODUCED
b87c4be factorial_alignment_v3_f3_eval_pipeline_policy
8861cea C2: analyzer schema normalization
f8a8168 analyzer schema normalization
112929f runner defensive payload handling
a2b436e Update the validator to accept implicit Level 0 evidence
62ad704 fix schema/validator mismatch
280de72 replay_control_row fix
f502ffe Modal image provenance flow
360a112 C2 replay manifest, and C2 Grammar
66f6b60 fix: C2 result writing is not durable per row.
b716615 FIX: C2 generated correctness bypasses Level 0 and Level 1
b423a0b max_new_tokens bump to 2048
5b2ba65 Lock current scope to 2^2 subset in writing
```

### Phase 0 verification status

- Master plan was read.
- Repository inventory was performed, including ignored files.
- Required artifacts were inspected read-only with `.venv/bin/python`.
- Docs/contracts/audits were classified.
- Current and stale methodology claims were separated.
- Audit report and handoff files were written.
- No code, artifacts, grammar files, formal research contracts, README files, hashes, or commits were modified.
