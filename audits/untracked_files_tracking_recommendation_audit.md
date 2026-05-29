# Untracked Files Tracking Recommendation Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`
Task: read-only recommendation audit for ignored/untracked handoff files

Execution constraints honored: this audit did not invoke Modal, run GPU jobs, run generation, run experiments, modify output artifacts, modify source code, modify grammar files, re-record hashes, edit `.gitignore`, delete files, or run `git add`. Local parsing/summarization used `.venv/bin/python`.

## 1. Executive Summary

Overall recommendation: track the clean citation-grade documentation layer and a small set of final/high-value audits; keep raw outputs, caches, generated report assets, and agentic working context ignored.

`docs/` should be tracked selectively with `git add -f` because `.gitignore` currently ignores the whole directory. The Phase 0-11 docs are now the human-readable source layer for methodology, artifact identities, decisions, analyzer caveats, report outline, and Cluster 3 guardrails. Not tracking them would lose the main handoff story.

`audits/` should be partially tracked with `git add -f`. Track the final consistency audit, this recommendation audit, and the Phase 0 repository-readiness audit. Do not track every historical smoke/fix audit by default; most are evidence-grade history already distilled into `docs/08_decision_log.md` and the methodology docs.

`.contracts/agentic/preliminary_report_handoff/` should remain ignored by default. It is useful local context, but most files are phase-state, next-agent briefs, or operational baton material. If a compact handoff record is later desired, promote or copy its distilled content into a tracked `docs/` or `audits/` file rather than tracking the agentic directory directly.

`outputs/` should remain ignored. Current JSONL/JSON artifacts are large generated artifacts and should be referenced through `docs/05_artifacts_and_results_registry.md`, not committed into Git.

There are no non-ignored untracked files. The working tree currently has one tracked modification: `README.md`.

## 2. Git Ignore/Status Context

Commands run:

```text
git status --short
git status --short --ignored
git ls-files --others --exclude-standard
git ls-files --others -i --exclude-standard
git ls-files README.md docs .contracts/research audits .contracts/agentic 2>/dev/null || true
sed -n '1,260p' .gitignore
find docs -maxdepth 4 -type f | sort || true
find audits -maxdepth 2 -type f | sort || true
find .contracts/agentic/preliminary_report_handoff -maxdepth 2 -type f | sort || true
find .contracts/research -maxdepth 2 -type f | sort || true
find docs audits .contracts/agentic/preliminary_report_handoff .contracts/research -type f -exec wc -c {} + 2>/dev/null | sort -n
find outputs -type f -maxdepth 5 -exec wc -c {} + 2>/dev/null | sort -n | tail -40 || true
rg "ImmediateTask|Execution rules|OutputFormat|You are Codex|prompt|Modal run|ForbiddenActions|DecisionCriteria" docs audits .contracts/agentic/preliminary_report_handoff .contracts/research README.md -u
rg "source-of-truth|artifact registry|methodology|decision log|traceability|reproducibility|Cluster 1|Cluster 2|Cluster 3|2\^2|reportable=false|F2-only|task-agnostic|Modal|provenance" docs audits .contracts/agentic/preliminary_report_handoff .contracts/research README.md -u
```

Status summary:

| Check | Result |
|---|---|
| `git status --short` | `M README.md` |
| `git ls-files --others --exclude-standard` | no paths |
| ignored paths count | 10,703 paths |
| tracked docs/contracts/audits/agentic paths | `README.md`, `.contracts/research/*`, `.contracts/agentic/cluster1_contract.md`, `.contracts/agentic/cluster2_contract.md` |

Ignored-path category summary from `.venv/bin/python`:

| Category | Count | Recommendation |
|---|---:|---|
| `.venv/` | 5,802 | keep ignored |
| caches / `__pycache__` / `.pytest_cache` | 4,689 | keep ignored |
| `outputs/` | 114 | keep ignored generated artifacts |
| `audits/` | 35 | partially force-add selected audits |
| `.contracts/agentic/preliminary_report_handoff/` | 17 | keep ignored agent context by default |
| other `.contracts/agentic/` | 18 | keep ignored agent context |
| `docs/` | 16 | force-add selected citation-grade docs; hold generated report assets |
| editor/local agent state | 10 | keep ignored |

Relevant `.gitignore` rules:

```text
outputs/
.claude
.contracts/*
!.contracts/README.md
!.contracts/research/
!.contracts/research/**
!.contracts/agentic/
.contracts/agentic/*
!.contracts/agentic/cluster1_contract.md
!.contracts/agentic/cluster2_contract.md
.contracts/agentic/reference/*
docs
audits
```

Interpretation: `.gitignore` is currently causing citation-grade `docs/` and high-value `audits/` to be ignored. For this handoff, prefer `git add -f` for selected files. Do not change `.gitignore` without a separate policy decision.

## 3. Recommended TRACK_NOW Set

These files are clean, human-readable, report-facing, or high-value audit records. They should be committed for handoff traceability. Because `docs/` and `audits/` are ignored, use `git add -f` for those paths.

| Path | Why track | Handoff value | Risk if not tracked | Notes |
|---|---|---|---|---|
| `README.md` | Root navigation/status entrypoint; currently modified with post-Phase-11 links/status | Gives new readers the current scope, docs map, artifact caveats, and source hierarchy | Readers start from stale or incomplete project entrypoint | Tracked file; normal `git add` is enough |
| `docs/00_project_map.md` | Source-of-truth hierarchy and documentation map | Establishes citation-grade vs evidence-grade policy | Handoff loses trust policy and current drafting status | Track now |
| `docs/02_methodology_cluster1.md` | Cluster 1/G methodology | Preserves compile-only boundary, task-agnostic G, semantic validation | Future reports may drift into functional-correctness or template-G claims | Track now |
| `docs/03_methodology_cluster2.md` | Cluster 2/C and G+C methodology | Preserves F2-only repair, F0/F1 termination, replay controls, G+C composition | C/G+C could be misdescribed as broader repair or template-G based | Track now |
| `docs/04_modal_infrastructure.md` | Modal and provenance methodology | Explains Modal as infrastructure, not a factor | Provenance/durable-write lessons become buried in ignored audits | Track now |
| `docs/05_artifacts_and_results_registry.md` | Citation-grade artifact registry | Freezes artifact paths, row counts, schemas, caveats | Highest risk file to omit; filenames/counts can drift | Track now |
| `docs/06_failure_taxonomy_and_eval_ladder.md` | Evaluation ladder and failure-code semantics | Defines F0/F1/F2/F3 and Cluster 1/2 boundaries | Analyzer and repair semantics become ambiguous | Track now |
| `docs/07_analysis_and_statistics.md` | Analyzer/normalization/statistics semantics | Documents `reportable=false`, pairing, normalization, response variables | Report could quote unsupported or misnormalized results | Track now |
| `docs/08_decision_log.md` | Distilled decision records | Replaces raw audits/agent plans with citation-safe decisions | Future agents re-read prompt-like history and re-litigate decisions | Track now |
| `docs/09_preliminary_report_outline.md` | Detailed report scaffold | Enables report drafting with result placeholders | Drafting loses section/source matrix and caveat checklist | Track now |
| `docs/10_cluster3_drift_prevention_plan.md` | Cluster 3 guardrails | Prevents P/Cluster 3 drift before implementation | Future Cluster 3 work may start without factor/schema/metric gates | Track now |
| `docs/handoff/codebase_handoff_guide.md` | Practical onboarding guide | Explains how to use repo without hidden chat context | Handoff remains dependent on local conversation history | Track now |
| `docs/handoff/stale_docs_inventory.md` | Refreshed stale/non-authoritative surface map | Warns future readers away from stale README/contracts/audits/artifacts | Stale historical docs may be treated as current methodology | Track now |
| `audits/final_documentation_consistency_audit.md` | Final Phase 11 audit | Verifies README/docs/contracts/artifacts consistency | No independent evidence that documentation set was checked | Track now |
| `audits/untracked_files_tracking_recommendation_audit.md` | This audit | Records why only selected ignored files should be tracked | Handoff set may become arbitrary or too broad | Track now |
| `audits/repository_documentation_methodology_readiness_audit.md` | Phase 0 inventory/readiness audit | Shows the initial stale-doc/artifact evidence baseline | Later docs lose their reconstruction trail | Track now as evidence-grade support |

## 4. Recommended TRACK_AFTER_CLEANUP Set

These files may be valuable, but should not be tracked in their current form without review, relocation, or explicit labeling.

| Path | Reason not TRACK_NOW | Cleanup needed |
|---|---|---|
| `docs/preliminary_report/README.md` | Describes an HTML preliminary report that quotes non-final analyzer-derived values while `metadata.reportable=false` | Review after analyzer reportability decision; ensure the report is intentionally non-final or update values/status |
| `docs/preliminary_report/index.html` | Human-facing HTML with embedded data and specific result language; outside Phase 0-11 citation-grade docs | Track only if the team wants to preserve the non-final meeting artifact and accepts caveats |
| `docs/preliminary_report/_build_data.py` | Report-generation helper, not part of citation-grade docs; uses write behavior if run | Track only with the HTML report as a coherent report artifact, after review |
| `docs/preliminary_report/_report_data.json` | Generated aggregate data derived from ignored outputs/analyzer | Prefer keep ignored; if report bundle is tracked, consider regenerability and size policy |
| `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md` | Useful compact contract diff, but lives under ignored agentic context | Promote distilled table into a tracked audit/docs appendix if needed |
| `.contracts/agentic/preliminary_report_handoff/phase_11_completion_brief.md` | Compact final baton, but agent-specific | Track only if converted to a non-agentic audit/handoff note |
| `.contracts/agentic/preliminary_report_handoff/post_phase11_doc_cleanup_report.md` | Compact cleanup record, but agentic and already reflected by this audit | Track only if moved/promoted into `audits/` |
| selected decision/fix audits such as `audits/factorial_cluster1_functional_success_normalization_fix_report.md`, `audits/factorial_cluster2_compile_success_normalization_fix_report.md`, `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`, `audits/analyzer_pre_output_verification_audit.md`, `audits/g_plus_c_correctness_payload_failure_fix_report.md`, `audits/shared_modal_smoke_boundary_hash_resolution_report.md`, `audits/g_plus_c_hash_gate_and_metadata_fix_report.md`, `audits/g_plus_c_nested_metadata_validator_fix_report.md`, `audits/g_plus_c_implicit_level0_validator_fix_report.md`, `audits/cluster2_c_paper_n20_l4_report.md`, `audits/cluster2_g_plus_c_paper_n20_l4_run_report.md`, `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md`, `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md` | Useful evidence, but mostly superseded by docs/decision log/final audit for commit-facing handoff | If a deeper audit trail is required, create a curated evidence bundle or index before tracking |

## 5. Recommended KEEP_IGNORED_AGENT_CONTEXT Set

These files are useful for local Codex continuity or historical reconstruction, but are not citation-grade and should not be added by default.

| Path or group | Rationale |
|---|---|
| `.contracts/agentic/preliminary_report_handoff/phase_state.md` | Active/local handoff state; operational, mutable, and agent-specific |
| `.contracts/agentic/preliminary_report_handoff/phase_0_next_agent_brief.md` through `phase_10_next_agent_brief.md` | Compact but prompt-like next-agent batons; superseded by tracked docs/audits |
| `.contracts/agentic/preliminary_report_handoff/phase_0_inventory_notes.md` | Internal phase notes; Phase 0 audit is the cleaner trackable record |
| `.contracts/agentic/preliminary_report_handoff/phase_0_file_classification_table.md` | Detailed internal classification; useful if needed, but noisy relative to stale-doc inventory and this audit |
| `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md` | Valuable but agentic; promote before tracking if needed |
| `.contracts/agentic/preliminary_report_handoff/phase_11_completion_brief.md` | Final baton, but agentic; final audit is the trackable version |
| `.contracts/agentic/preliminary_report_handoff/post_phase11_doc_cleanup_report.md` | Cleanup baton; this audit captures the tracking decision |
| `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` | Master workflow plan; prompt/phase-control material, not report methodology |
| `.contracts/agentic/*plan*.md`, `.contracts/agentic/*todo*.md`, `.contracts/agentic/*report*.md` outside the two tracked contracts | Historical agent plans/reports, many stale or operational |
| `.contracts/agentic/reference/*.md` | Cached reference/helper material; should not be citation-grade without verification |
| `.claude/` | Local agent/editor settings and worktrees |

## 6. Recommended KEEP_IGNORED_GENERATED_ARTIFACT Set

Do not track raw generated outputs.

| Path or group | Rationale |
|---|---|
| `outputs/analysis/factorial_2x2_preliminary.json` | Analyzer artifact is current and important, but generated; cite it via `docs/05_artifacts_and_results_registry.md` |
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` and sidecars/summaries | Current artifact, but generated and large; keep external/ignored |
| `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` and sidecars | Current artifact, but generated and large; registry captures path/count/caveats |
| `outputs/cluster2/c_paper_n20_l4.jsonl` and hash sidecar | Current artifact, but generated and large |
| `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` and hash sidecar | Current artifact, but generated and large |
| `outputs/cluster1/*n5*`, `outputs/cluster1/*smoke*`, `outputs/cluster1/final_g_l4_n20*`, old `full_*` / `repaired_*` outputs | Development, smoke, template, or legacy artifacts; non-authoritative unless promoted |
| `outputs/cluster2/*smoke*`, diagnostics, local validation JSONL, hash sidecars | Smoke/development/evidence artifacts, not commit-facing source |
| `outputs/cluster1/figures/*.png` | Generated figures; should be regenerated or explicitly bundled in a report package only after approval |

The large-output check showed the current paper-scale JSONL files range from hundreds of KB to about 0.9 MB each, with ignored outputs totaling about 9.9 MB in the inspected set. Size is not the only issue: they are generated result artifacts and should not be hand-edited or committed as source.

## 7. Recommended KEEP_IGNORED_CACHE_OR_BUILD Set

| Path or group | Rationale |
|---|---|
| `.venv/` | Local virtual environment |
| `.pytest_cache/` | Test cache |
| `**/__pycache__/` and `*.pyc` | Python bytecode cache |
| `.idea/` | Local IDE project state |
| `.claude/` | Local agent state/worktrees |
| `docs/preliminary_report/_report_data.json` | Generated report data; keep ignored unless tracking a reviewed report bundle |
| generated/static report assets under `docs/preliminary_report/` | Treat as a generated report bundle until explicitly promoted |

## 8. DELETE_CANDIDATE_LATER

Do not delete anything as part of this task. Potential later cleanup candidates:

| Path or group | Why later review is reasonable |
|---|---|
| stale `.contracts/agentic/*plan*.md` files | Superseded by tracked docs and final audits; may confuse future agents if left without status labels |
| old output summaries under `outputs/cluster1/*summary.md` | Many summarize legacy n=5/template/dev runs and can be misleading if browsed casually |
| failed/partial/smoke artifacts under `outputs/` | Historical evidence only; should remain ignored, archived externally, or deleted only after retention policy review |
| `.claude/worktrees/*` | Local agent workspace state; delete only with user approval |

## 9. Suggested Git Add Commands

Do not run these in this audit. These commands are the recommended staging plan if the user chooses to prepare a handoff commit.

```bash
git add README.md .contracts/research/research_scope.md .contracts/research/eval_metrics.md .contracts/research/scale_policy.md
```

The `.contracts/research/*` paths are already tracked and currently do not appear modified in `git status --short`, but including them in a staging command is harmless if they are part of the intended handoff commit.

```bash
git add -f docs/00_project_map.md docs/02_methodology_cluster1.md docs/03_methodology_cluster2.md docs/04_modal_infrastructure.md docs/05_artifacts_and_results_registry.md docs/06_failure_taxonomy_and_eval_ladder.md docs/07_analysis_and_statistics.md docs/08_decision_log.md docs/09_preliminary_report_outline.md docs/10_cluster3_drift_prevention_plan.md docs/handoff/codebase_handoff_guide.md docs/handoff/stale_docs_inventory.md
```

```bash
git add -f audits/final_documentation_consistency_audit.md audits/untracked_files_tracking_recommendation_audit.md audits/repository_documentation_methodology_readiness_audit.md
```

Do not stage these by default:

```bash
# Do not run as a bulk add:
git add -f docs/preliminary_report .contracts/agentic/preliminary_report_handoff audits outputs
```

## 10. Suggested Commit Structure

Preferred three-commit structure:

1. `docs: align research scope and handoff entrypoints`
   - `README.md`
   - existing tracked `.contracts/research/research_scope.md`
   - existing tracked `.contracts/research/eval_metrics.md`
   - existing tracked `.contracts/research/scale_policy.md`
   - `docs/00_project_map.md`
   - `docs/handoff/codebase_handoff_guide.md`
   - `docs/handoff/stale_docs_inventory.md`

2. `docs: add preliminary methodology and artifact registry`
   - `docs/02_methodology_cluster1.md`
   - `docs/03_methodology_cluster2.md`
   - `docs/04_modal_infrastructure.md`
   - `docs/05_artifacts_and_results_registry.md`
   - `docs/06_failure_taxonomy_and_eval_ladder.md`
   - `docs/07_analysis_and_statistics.md`

3. `docs: add auditability and Cluster 3 guardrails`
   - `docs/08_decision_log.md`
   - `docs/09_preliminary_report_outline.md`
   - `docs/10_cluster3_drift_prevention_plan.md`
   - `audits/repository_documentation_methodology_readiness_audit.md`
   - `audits/final_documentation_consistency_audit.md`
   - `audits/untracked_files_tracking_recommendation_audit.md`

Acceptable single-commit alternative:

```text
docs: add preliminary handoff methodology
```

Use the single commit if the goal is one coherent handoff package rather than reviewable slices.

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Tracking too much agent scratch | Commit becomes noisy and future readers may treat prompts as methodology | Track docs/final audits only; keep `.contracts/agentic/` ignored |
| Not tracking `docs/` | Loses citation-grade methodology, artifact registry, decision log, report outline, and Cluster 3 guardrails | Force-add selected docs |
| Not tracking final audits | Weakens accountability and traceability for the documentation pipeline | Track final audit, this audit, and Phase 0 readiness audit |
| Tracking `outputs/` | Bloats repo and encourages treating generated data as hand-edited source | Keep outputs ignored; cite via registry |
| Tracking stale audits as current | Confuses current methodology with superseded blockers or old smoke states | Track only curated audits; rely on decision log and docs for current claims |
| Tracking preliminary HTML report before reportability decision | Could make non-final statistical prose look official | Review `docs/preliminary_report/` after analyzer reportability is resolved or explicitly label it as non-final meeting material |
| Changing `.gitignore` casually | May expose caches, outputs, or agent files in future bulk adds | Use `git add -f` now; revisit ignore policy separately |

## 12. Final Recommendation

Track now:

```text
README.md
docs/00_project_map.md
docs/02_methodology_cluster1.md
docs/03_methodology_cluster2.md
docs/04_modal_infrastructure.md
docs/05_artifacts_and_results_registry.md
docs/06_failure_taxonomy_and_eval_ladder.md
docs/07_analysis_and_statistics.md
docs/08_decision_log.md
docs/09_preliminary_report_outline.md
docs/10_cluster3_drift_prevention_plan.md
docs/handoff/codebase_handoff_guide.md
docs/handoff/stale_docs_inventory.md
audits/final_documentation_consistency_audit.md
audits/untracked_files_tracking_recommendation_audit.md
audits/repository_documentation_methodology_readiness_audit.md
```

Leave ignored:

```text
outputs/
.venv/
.pytest_cache/
**/__pycache__/
.idea/
.claude/
.contracts/agentic/preliminary_report_handoff/
.contracts/agentic/* plans/reports/reference files not explicitly tracked
most historical audits unless a curated evidence bundle is requested
```

Manual review before tracking:

```text
docs/preliminary_report/
selected historical decision/fix audits if a deeper evidence bundle is desired
selected .contracts/agentic/preliminary_report_handoff/*.md if promoted into docs/ or audits/
```

Classification: `AUDIT_COMPLETE`.
