# Final Documentation Consistency Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`
Phase: Phase 11 - Final Documentation Consistency Audit

Execution constraints honored: this audit did not invoke Modal, run GPU jobs, run generation, run experiments, rerun the analyzer, modify outputs, modify source code, modify grammar files, re-record hashes, edit README, edit `docs/*.md`, or edit `.contracts/research/*`. Local artifact parsing used `.venv/bin/python`.

## 1. Executive Summary

Final classification: `PHASE11_COMPLETE_WITH_FIXES_NEEDED`.

The documentation set is methodologically consistent enough to support preliminary report drafting with results placeholders and visible caveats. README, the current methodology docs, the artifact registry, the aligned research contracts, and the decision log agree on the core current state:

- current scope is the 2^2 subset: `none`, `G`, `C`, `G+C`;
- full 2^3 and Cluster 3/P are deferred;
- Cluster 1 implements G and is compile-only;
- G is task-agnostic grammar-guided decoding plus semantic post-validation;
- template G is diagnostic/reference only;
- Cluster 2 implements C and G+C;
- C repair is restricted to F2 numerical/correctness failures;
- F0/F1 terminate without repair feedback;
- G+C is task-agnostic G plus C, not a new cluster;
- Modal is infrastructure/provenance machinery, not a research factor;
- analyzer output exists but `metadata.reportable=false`.

No severe methodology contradiction or artifact registry mismatch was found. No live positive claim of final statistical results, Cluster 3/P results, full 2^3 completion, Cluster 1 functional correctness, 180/180 G/G+C coverage, template-G primary status, or performance/speedup results was found in the current README/docs/core contracts.

Remaining bounded documentation fixes:

- `docs/00_project_map.md` still has Phase 1-era navigation statuses that mark later docs as TODO even though docs 02-10 now exist.
- `docs/handoff/stale_docs_inventory.md` still records README and the three core research contracts as needing updates, although Phase 8 aligned those surfaces. It should be revised or clearly labeled as a Phase 0 snapshot before external handoff.
- README navigation does not list `docs/09_preliminary_report_outline.md` or `docs/10_cluster3_drift_prevention_plan.md`, because those files were created after Phase 8.
- Some methodology docs retain "Open TODOs for later phases" entries for phases that are now complete. These are housekeeping issues, not methodology blockers.
- `.contracts/research/eval_metrics.md` intentionally retains future Level 3/4/P material. Its new current-status preamble scopes that material as future-facing, but future readers should be warned not to treat those sections as current P results.

Report-drafting readiness: the preliminary report can begin from `docs/09_preliminary_report_outline.md` after the bounded navigation/status cleanup above, or immediately if the writer uses this audit as the caveat list. Official statistical-result prose remains blocked by `metadata.reportable=false`.

## 2. Scope And Method

Files inspected:

| Category | Files |
|---|---|
| Master/handoff | `.contracts/agentic/preliminary_report_handoff_readiness_plan.md`; `.contracts/agentic/preliminary_report_handoff/phase_state.md`; `.contracts/agentic/preliminary_report_handoff/phase_10_next_agent_brief.md` |
| README/docs | `README.md`; `docs/00_project_map.md`; `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md`; `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md`; `docs/09_preliminary_report_outline.md`; `docs/10_cluster3_drift_prevention_plan.md`; `docs/handoff/codebase_handoff_guide.md`; `docs/handoff/stale_docs_inventory.md` |
| Core research contracts | `.contracts/research/research_scope.md`; `.contracts/research/eval_metrics.md`; `.contracts/research/scale_policy.md` |
| Additional research surfaces checked by searches | `.contracts/research/paper_outline.md`; `.contracts/research/cluster1_generated_surface.md`; `.contracts/research/phase4_parse_reclassification_disposition.md`; `.contracts/research/modal_new_account_setup_guide.md` |
| Evidence/artifacts | four current JSONL artifacts; `outputs/analysis/factorial_2x2_preliminary.json`; `audits/repository_documentation_methodology_readiness_audit.md`; `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md` |

Searches run:

```text
rg "full 2\^3|G\+C\+P|P result|Cluster 3 result|P condition.*current|performance feedback.*current" README.md docs .contracts/research
rg "2\^2|none|G\+C|preliminary|Cluster 3.*deferred|P.*deferred" README.md docs .contracts/research
rg "template.*primary|template.*default|task_agnostic|task-agnostic|diagnostic/reference|diagnostic" README.md docs .contracts/research
rg "functional correctness|Cluster 1.*functional|compile-only|compile only|Level 2|functional_success|compile_success" README.md docs .contracts/research
rg "F0|F1|F2|F3|F3_EVAL_PIPELINE|repair|feedback|terminate|failure taxonomy" README.md docs .contracts/research
rg "177/180|180/180|missing rows|matmul/fp32 seed 5|matmul/bf16 seed 0|matmul/bf16 seed 18" README.md docs .contracts/research
rg "reportable=false|metadata.reportable|reportable=true|official final|final statistical|preliminary results" README.md docs .contracts/research
rg "speedup|performance result|timing result|profiling result|Nsight|NVML" README.md docs .contracts/research
rg "modal_image_sha=unknown|unknown provenance|provenance|tokenizer_revision|model_revision|Modal" README.md docs .contracts/research
rg "n=5|n5|template-G|legacy|non-authoritative|smoke|partial" README.md docs .contracts/research
```

Artifact verification was performed with a read-only `.venv/bin/python` script that loaded each current JSONL/JSON artifact, counted rows, validated JSON, and summarized key fields.

## 3. Current Source-Of-Truth Status

| Surface | Status | Notes |
|---|---|---|
| `README.md` | Methodologically aligned | Correctly states 2^2 current scope, Cluster 3/P deferral, artifact paths, caveats, source hierarchy, and no final results. It lacks links to docs 09/10 because they were created later. |
| `docs/` methodology pages | Mostly aligned | Docs 02-10 consistently state current methodology, artifacts, caveats, and result boundaries. Project map and a few per-doc TODO sections are stale as status/navigation metadata. |
| `.contracts/research/` core contracts | Aligned with caveats | `research_scope.md`, `eval_metrics.md`, and `scale_policy.md` now match the current 2^2 state. `eval_metrics.md` retains future P/performance design sections, but the current-status preamble scopes them as not current. |
| Artifact registry | Verified against files | `docs/05_artifacts_and_results_registry.md` matches direct artifact verification for paths, row counts, failure distributions, provenance caveats, and analyzer reportability. |
| Decision log | Aligned | `docs/08_decision_log.md` records active, superseded, deferred, and historical decisions with evidence paths. Minor stale wording says `docs/10` is future in one traceability cell, but D18 content is consistent. |
| Handoff state | Updated by Phase 10 before audit | Phase state correctly entered Phase 11 as Phase 10 complete / Phase 11 ready with warnings. This audit updates it to Phase 11 complete. |

## 4. Artifact Verification

Direct verification from the current files:

| Artifact | Exists | Valid | Rows / loaded rows | Condition values | Key distributions | Caveats | Registry match |
|---|---:|---:|---:|---|---|---|---:|
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | yes | valid JSONL | 180 rows | absent/null; inferred `none` | `kernel_class`: elementwise 60, reduction 60, matmul 60; `dtype`: fp32 60, fp16 60, bf16 60; `compile_success=false` 180 | Cluster 1 compile-only; legacy flat schema; no model/tokenizer/modal revision provenance | yes |
| `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | yes | valid JSONL | 177 rows | absent/null; inferred `G` | `kernel_class`: elementwise 60, reduction 60, matmul 57; `dtype`: fp32 59, fp16 60, bf16 58; `failure_code`: null 3, F1_RUNTIME 152, F1_COMPILE 9, F0_PARSE 13; `compile_success`: true 3, false 174; `grammar_variant=task_agnostic` 177 | 177/180; missing matmul rows; compile-only; `modal_image_sha=unknown` | yes |
| `outputs/cluster2/c_paper_n20_l4.jsonl` | yes | valid JSONL | 180 rows | `C` 180 | `kernel_class`: elementwise 60, reduction 60, matmul 60; `dtype`: fp32 60, fp16 60, bf16 60; `failure_code=F0_PARSE` 180; `functional_success=false` 180; raw `compile_success` absent/null 180 | analyzer must normalize compile success from failure code; no grammar by design | yes |
| `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | yes | valid JSONL | 177 rows | `G+C` 177 | `kernel_class`: elementwise 60, reduction 60, matmul 57; `dtype`: fp32 59, fp16 60, bf16 58; `failure_code`: F2_NUMERIC_NAN 4, F1_RUNTIME 146, F1_COMPILE 10, F0_PARSE 12, F3_EVAL_PIPELINE 5; `compile_success`: true 4, false 173; `functional_success=false` 177; `grammar_variant=task_agnostic` 177 | 177/180; same missing rows as G; five F3 rows | yes |
| `outputs/analysis/factorial_2x2_preliminary.json` | yes | valid JSON | 714 loaded rows | populated cells: none, G, C, G+C | top-level keys include `metadata`, `diagnostics`, `factorial_model`, `paired_comparisons`, `condition_rates`, `cell_summaries`, `paper_tables`; `metadata.reportable=false`; `diagnostics.rows_loaded=714`; `factorial_model.n_observations=714` | inspectable evidence, not official final result; P cells missing/deferred; scale tier unspecified | yes |

Missing rows verified directly for both G and G+C:

| Kernel class | Dtype | Missing seed |
|---|---|---:|
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |
| matmul | fp32 | 5 |

## 5. Consistency Matrix

| Topic | README | docs | contracts | artifacts/analyzer | Status | Notes |
|---|---|---|---|---|---|---|
| 2^2 scope | states current 2^2 | docs agree | core contracts agree | analyzer populated cells are none/G/C/G+C | pass | Additional future P language is scoped as future/deferred. |
| Cluster 3/P deferred | states deferred | docs 00, 03, 04, 07, 08, 09, 10 agree | core contracts agree | analyzer marks P cells missing/deferred | pass | No P result claim found. |
| G definition | task-agnostic grammar plus semantic validation | docs 02/06/07/08/09 agree | core contracts agree | G/G+C rows have `grammar_variant=task_agnostic` | pass | Template G is diagnostic/reference only. |
| C definition | correctness-feedback repair only | docs 03/06/08 agree | core contracts agree | C artifact has C rows; current rows all F0_PARSE | pass | Current C artifact exercises terminal F0 behavior, not successful repair. |
| G+C definition | task-agnostic G plus C | docs 03/05/08/09 agree | core contracts agree | G+C rows task-agnostic with C2 schema | pass | Not a new cluster and not template G. |
| Cluster 1 compile-only | README caveats it | docs 02/06/07/09 agree | core contracts agree | none/G functional success absent; analyzer normalizes false/unproven | pass | No Cluster 1 functional-correctness claim found. |
| F2-only repair | not detailed but not contradicted | docs 03/06/08 agree | core contracts agree | C/G+C failure codes visible | pass | F0/F1 no-feedback policy preserved. |
| 177/180 caveat | states G/G+C 177/180 | docs agree | core contracts agree | direct row counts match | pass | Missing rows named consistently. |
| Analyzer reportable=false | states caveat | docs agree | core contracts agree | metadata.reportable=false verified | pass | Final statistical-result prose remains blocked. |
| Modal/provenance | navigation/caveats present | docs 04/05/08/09 agree | contracts mention provenance | artifact fields verified | pass | G `modal_image_sha=unknown` and baseline legacy caveats visible. |
| Legacy artifact policy | states non-authoritative | docs 05/08/09/handoff agree | contracts agree | n/a | pass | Old n5/template/smoke/partial artifacts not current. |
| Cluster 3 guardrails | README defers P | docs 08/09/10 agree | contracts defer P | analyzer P cells absent | pass with cleanup | README does not link docs/10 yet. |
| Navigation/status metadata | README omits docs 09/10 | `docs/00_project_map.md` has stale TODO status | n/a | n/a | fix needed | Non-methodology but confusing for handoff/readers. |
| Stale inventory | n/a | stale inventory still marks updated README/contracts as needing update | n/a | n/a | fix needed | Treat as Phase 0 snapshot until refreshed. |

## 6. Overclaim Scan Results

No live positive overclaim was found in current README, docs, or core research contracts for:

- full 2^3 completion;
- current P result or Cluster 3 result;
- template G as the primary G condition;
- Cluster 1 functional correctness;
- official final statistical results while `metadata.reportable=false`;
- performance, timing, profiling, or speedup results;
- complete 180/180 G or G+C coverage.

Allowed negative or future-facing statements found:

- `eval_metrics.md` contains future Level 4/P performance metrics and P-condition examples. The file now begins with a current-status scope note that says the current report-facing scope is 2^2 and P-containing metrics are deferred. This remains a residual risk for careless readers but is not an active current-result overclaim.
- `docs/10_cluster3_drift_prevention_plan.md` contains phrases such as "P result" and "Cluster 3 result" only in explicit negative statements.
- `docs/09_preliminary_report_outline.md` includes result table shells with TODO values. These correctly block final statistics until reportability is resolved.

Unresolved risky phrasing:

| File | Risk | Severity | Recommendation |
|---|---|---:|---|
| `docs/00_project_map.md` | Navigation table and future-phase TODO list still say docs 02-10 are TODO. | Medium | Refresh status metadata before external report drafting or reader handoff. |
| `docs/handoff/stale_docs_inventory.md` | Still says README and core research contracts need update, although Phase 8 updated them. | Medium | Update classifications or mark the file explicitly as a Phase 0 snapshot. |
| `README.md` | Documentation map omits `docs/09_preliminary_report_outline.md` and `docs/10_cluster3_drift_prevention_plan.md`. | Low | Add links in the next docs cleanup phase. |
| `docs/02_methodology_cluster1.md`, `docs/03_methodology_cluster2.md`, `docs/04_modal_infrastructure.md` | Open TODO sections reference later phases that are now complete. | Low | Refresh TODO sections or mark as historical phase notes. |
| `.contracts/research/eval_metrics.md` | Future P/performance sections are retained and could be misread without the current-status preamble. | Low/Medium | Keep current-status note prominent; consider moving future P material to a Cluster 3-specific contract later. |
| `.contracts/research/modal_new_account_setup_guide.md` | Operational guide contains Modal commands. | Low | Do not cite as current methodology; use only when a future phase explicitly authorizes Modal/account work. |

## 7. Traceability Audit

| Claim | Citation-grade doc | Code/test/evidence path | Artifact path | Status |
|---|---|---|---|---|
| Current scope is 2^2 only | `README.md`; `docs/00_project_map.md`; `docs/05_artifacts_and_results_registry.md`; `.contracts/research/research_scope.md` | analyzer metadata | `outputs/analysis/factorial_2x2_preliminary.json` | traced |
| Cluster 3/P deferred | `README.md`; `docs/08_decision_log.md`; `docs/10_cluster3_drift_prevention_plan.md`; `.contracts/research/research_scope.md` | `cluster3/README.md` as evidence | analyzer P cells missing/deferred | traced |
| G is task-agnostic grammar plus semantic post-validation | `docs/02_methodology_cluster1.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `.contracts/research/research_scope.md` | `cluster1/grammar/triton_kernel_agnostic.gbnf`; `cluster1/grammar/triton_kernel_validator.py`; `shared/generation_metadata.py`; tests cited in docs | G and G+C artifacts | traced |
| Template G diagnostic/reference only | `README.md`; `docs/02_methodology_cluster1.md`; `docs/05_artifacts_and_results_registry.md`; `docs/08_decision_log.md` | `shared/generation_metadata.py`; grammar variant tests cited in docs | current registry excludes template artifacts | traced |
| Cluster 1 compile-only | `README.md`; `docs/02_methodology_cluster1.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `.contracts/research/research_scope.md` | `cluster1/validation/compile_check.py`; `shared/eval/adapter_cluster1.py`; `cluster1/tests/test_cluster_boundary.py` | none/G artifacts | traced |
| C repair is F2-only | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/08_decision_log.md`; `.contracts/research/research_scope.md` | `cluster2/feedback/prompts.py`; `cluster2/feedback/repair_loop.py`; Cluster 2 tests cited in docs | C/G+C artifacts | traced |
| F0/F1 terminate without feedback | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | `cluster2/feedback/repair_loop.py`; shared eval levels | C/G+C artifacts | traced |
| G+C is G plus C | `README.md`; `docs/03_methodology_cluster2.md`; `docs/08_decision_log.md` | `cluster2/modal/generation.py`; `cluster2/modal/schemas.py` | G+C artifact | traced |
| G/G+C are 177/180 | `README.md`; `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md`; `.contracts/research/scale_policy.md` | direct artifact verification | G and G+C artifacts | traced |
| Analyzer output not reportable | `README.md`; `docs/05_artifacts_and_results_registry.md`; `docs/07_analysis_and_statistics.md`; `.contracts/research/research_scope.md` | analyzer metadata | `outputs/analysis/factorial_2x2_preliminary.json` | traced |
| F3_EVAL_PIPELINE policy | `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` | `shared/analysis/factorial.py`; `cluster2/experiments/run_cluster2_modal.py`; audits cited in docs | G+C artifact and analyzer JSON | traced |
| Modal infrastructure/provenance | `docs/04_modal_infrastructure.md`; `docs/08_decision_log.md` | `shared/modal_harness/`; `cluster1/experiments/run_cluster1_modal.py`; `cluster2/experiments/run_cluster2_modal.py` | current artifacts with provenance fields | traced |
| Legacy artifacts non-authoritative | `README.md`; `docs/05_artifacts_and_results_registry.md`; `docs/08_decision_log.md`; `docs/handoff/stale_docs_inventory.md` | Phase 0 audit and legacy run reports | current registry excludes legacy artifacts | traced |
| Cluster 3 guardrails | `docs/10_cluster3_drift_prevention_plan.md`; `docs/08_decision_log.md` | Phase 10 handoff | no P artifacts | traced |

## 8. Remaining Blockers

Report-drafting blockers:

- Bounded documentation cleanup should happen before an external or committee-facing draft: refresh `docs/00_project_map.md`, `docs/handoff/stale_docs_inventory.md`, README navigation for docs 09/10, and stale per-doc phase TODOs.

Final statistical-result blockers:

- `outputs/analysis/factorial_2x2_preliminary.json` has `metadata.reportable=false`; official final statistical-result prose remains blocked.
- The analyzer reports `scale_tiers=["unspecified"]`; any final report must resolve or explicitly caveat this.
- Current functional outcome has a single observed class, so the logistic functional model is not fit.

Cluster 3 implementation blockers:

- P semantics are intentionally undefined.
- No P implementation or paper-scale P run should start until `docs/10_cluster3_drift_prevention_plan.md` gates are satisfied: P definition, failure boundary, metric contract, schema/analyzer plan, artifact registry plan, Modal/provenance plan, scale gates, pairing tests, and documentation update plan.

Non-blocking caveats:

- G and G+C are 177/180 with missing matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18.
- G has `modal_image_sha=unknown`.
- none has legacy schema/provenance limitations.
- C lacks raw `compile_success` and requires analyzer normalization.
- G+C has five `F3_EVAL_PIPELINE` rows.
- Old n5/template/smoke/partial artifacts remain searchable but are non-authoritative.

## 9. Recommended Next Actions

Primary recommendation: `FIX_DOCUMENTATION_ISSUES_FIRST`.

Scope of the fix should be narrow:

1. Refresh `docs/00_project_map.md` to mark docs 02-10 and handoff docs as created/current where appropriate.
2. Refresh `docs/handoff/stale_docs_inventory.md` so README and the aligned core research contracts are no longer listed as unresolved, or mark the file explicitly as a Phase 0 snapshot.
3. Add README links to `docs/09_preliminary_report_outline.md` and `docs/10_cluster3_drift_prevention_plan.md`.
4. Refresh stale "Open TODOs for later phases" sections in docs 02/03/04 so they do not imply completed phases are still pending.

After that bounded cleanup, proceed with:

- `START_PRELIMINARY_REPORT_DRAFT_WITH_RESULTS_PLACEHOLDER`
- `RESOLVE_ANALYZER_REPORTABILITY_BEFORE_RESULTS_SECTION`

The report draft may explain methodology, artifacts, caveats, and planned result tables now. It should not quote official final statistical values until analyzer reportability is resolved or the report explicitly labels them non-final exploratory evidence.

## 10. Phase 11 Handoff Summary

Phase pipeline status: complete with bounded documentation fixes needed.

Files changed by Phase 11:

- `audits/final_documentation_consistency_audit.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `.contracts/agentic/preliminary_report_handoff/phase_11_completion_brief.md`

Next human/Codex task:

- Run a narrow documentation cleanup phase for navigation/status metadata only, then start preliminary report drafting from `docs/09_preliminary_report_outline.md` with the results section kept as a placeholder until analyzer `metadata.reportable=false` is resolved or explicitly caveated.

## 11. Appendix

### Commands Run

```text
git status --short
sed -n '1,260p' .contracts/agentic/preliminary_report_handoff_readiness_plan.md
sed -n '1,420p' .contracts/agentic/preliminary_report_handoff/phase_state.md
sed -n '1,240p' .contracts/agentic/preliminary_report_handoff/phase_10_next_agent_brief.md
wc -l README.md docs/00_project_map.md docs/02_methodology_cluster1.md docs/03_methodology_cluster2.md docs/04_modal_infrastructure.md docs/05_artifacts_and_results_registry.md docs/06_failure_taxonomy_and_eval_ladder.md docs/07_analysis_and_statistics.md docs/08_decision_log.md docs/09_preliminary_report_outline.md docs/10_cluster3_drift_prevention_plan.md docs/handoff/codebase_handoff_guide.md docs/handoff/stale_docs_inventory.md .contracts/research/research_scope.md .contracts/research/eval_metrics.md .contracts/research/scale_policy.md
find .contracts/agentic/preliminary_report_handoff -maxdepth 1 -type f | sort
find audits -maxdepth 1 -type f | sort
sed reads for README, docs 00/02/03/04/05/06/07/08/09/10, handoff docs, core research contracts, Phase 8 diff review, Phase 0 audit, and additional research surfaces
required rg searches listed in section 2
.venv/bin/python artifact verification script
.venv/bin/python missing-row verification script
rg -n 'TODO|Future docs/10|future docs/10|Created in Phase 1|Phase [0-9]+:|NEEDS_UPDATE|Later .*phase|Later cleanup' README.md docs .contracts/research .contracts/agentic/preliminary_report_handoff/phase_state.md
```

One exploratory TODO search was first attempted with shell-interpreted backticks in the pattern and produced shell errors for `docs/10` and `future`; it was immediately rerun with single quotes and valid output. No files were modified by that failed search.

### Key Search Findings

| Search area | Finding |
|---|---|
| Full 2^3 / P | Positive P/full-factorial statements were either explicit deferrals, future-form examples, or negative "do not claim" statements. No current P result claim found. |
| Current 2^2 | README, docs, and core contracts consistently state the current 2^2 scope. |
| Task-agnostic vs template G | Current docs and contracts consistently mark task-agnostic G primary and template G diagnostic/reference. |
| Cluster 1 correctness | Current docs and contracts consistently preserve compile-only/no functional-correctness boundary. |
| F0/F1/F2/F3 | Current docs consistently document F2-only repair, F0/F1 termination, and F3 caveats. |
| 177/180 | Current docs and contracts consistently preserve G/G+C 177/180 and missing-row caveats. |
| reportable=false | Current docs and contracts consistently preserve analyzer `metadata.reportable=false`. |
| performance/speedup | Current docs and core contracts do not claim current performance/speedup results. Future P/performance material remains in `eval_metrics.md` but is scoped as future. |
| provenance/Modal | Current docs preserve Modal-as-infrastructure and provenance caveats. |
| legacy artifacts | Current docs preserve non-authoritative policy for n5/template/smoke/partial artifacts. |

### Artifact Verification Output Summary

```text
none: exists, 180 valid JSONL rows, no bad JSON, compile_success false 180
G: exists, 177 valid JSONL rows, no bad JSON, grammar_variant task_agnostic 177, modal_image_sha unknown 177
C: exists, 180 valid JSONL rows, no bad JSON, condition C 180, failure_code F0_PARSE 180, compile_success absent/null 180
G+C: exists, 177 valid JSONL rows, no bad JSON, condition G+C 177, F3_EVAL_PIPELINE 5, grammar_variant task_agnostic 177
analysis: exists, valid JSON, top-level keys present, diagnostics.rows_loaded 714, factorial_model.n_observations 714, metadata.reportable false
missing G/G+C rows: matmul/bf16 seeds 0 and 18; matmul/fp32 seed 5
```
