# Phase 0 File Classification Table

Classification values: `AUTHORITATIVE_CURRENT`, `NEEDS_UPDATE`, `LEGACY_EVIDENCE`, `AGENT_INTERNAL`, `DELETE_CANDIDATE_LATER`, `UNKNOWN`.

| Path | Classification | Reason | Grade | Recommended action |
| --- | --- | --- | --- | --- |
| `README.md` | `NEEDS_UPDATE` | Mixed current 2^2 scope and stale template-G framing. | citation-grade after update | Update before report prose. |
| `pyproject.toml` | `NEEDS_UPDATE` | Full 2^3 description is a project goal, not current populated scope. | citation-adjacent | Clarify through README/docs. |
| `requirements.txt` | `NEEDS_UPDATE` | Operational header may be stale; not methodology-critical. | ignored for report | Optional cleanup. |
| `.gitignore` | `AUTHORITATIVE_CURRENT` | Confirms docs/audits/outputs/agentic context are ignored unless promoted. | evidence-grade | Keep. |
| `.contracts/README.md` | `AUTHORITATIVE_CURRENT` | Correct contract hierarchy. | citation-grade | Keep. |
| `.contracts/research/research_scope.md` | `NEEDS_UPDATE` | Good scope base, lacks current analyzer/artifact status. | citation-grade after update | Add Phase 1 status addendum. |
| `.contracts/research/eval_metrics.md` | `NEEDS_UPDATE` | Good ladder/metrics base, lacks promoted F3 policy. | citation-grade after update | Add F3 policy. |
| `.contracts/research/cluster1_generated_surface.md` | `AUTHORITATIVE_CURRENT` | Current generated-surface boundary. | citation-grade | Keep. |
| `.contracts/research/scale_policy.md` | `NEEDS_UPDATE` | Stale task-agnostic n20 blocked/template-G language. | citation-grade after update | Update current scale status. |
| `.contracts/research/paper_outline.md` | `NEEDS_UPDATE` | Useful outline but lacks current artifact/analyzer status. | citation-grade after update | Refresh or supersede in docs. |
| `.contracts/research/phase4_parse_reclassification_disposition.md` | `AUTHORITATIVE_CURRENT` | Useful baseline reclassification trace. | evidence/citation hybrid | Keep. |
| `.contracts/research/modal_new_account_setup_guide.md` | `NEEDS_UPDATE` | Operational, not current methodology. | ignored for report | Keep operational. |
| `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` | `AGENT_INTERNAL` | Master execution plan for agents. | ignored | Use as workflow input only. |
| `.contracts/agentic/cluster1_contract.md` | `AGENT_INTERNAL` | Internal contract, partially old. | ignored | Add status header if reused. |
| `.contracts/agentic/cluster2_contract.md` | `AGENT_INTERNAL` | Stale artifact/token defaults. | ignored | Mark superseded/update later. |
| `.contracts/agentic/cluster1_plan.md` | `LEGACY_EVIDENCE` | Historical plan. | ignored/evidence | Mark legacy. |
| `.contracts/agentic/post_cluster1_scope_and_execution_plan.md` | `LEGACY_EVIDENCE` | Historical plan. | ignored/evidence | Mark legacy. |
| `.contracts/agentic/cluster2_integrated_agent_plan.md` | `LEGACY_EVIDENCE` | Historical C2 plan with stale template-G assumptions. | ignored/evidence | Mark legacy; delete candidate later. |
| `.contracts/agentic/cluster2_paired_replay_alignment_plan.md` | `LEGACY_EVIDENCE` | Superseded replay plan. | ignored/evidence | Mark legacy. |
| `.contracts/agentic/cluster2_paired_replay_alignment_review_todo.md` | `DELETE_CANDIDATE_LATER` | Superseded TODO. | ignored | Delete only after review/backup. |
| `.contracts/agentic/reference/*.md` | `AGENT_INTERNAL` | Cached reference/helper material. | ignored | Do not cite directly. |
| `audits/repository_documentation_methodology_readiness_audit.md` | `AUTHORITATIVE_CURRENT` | Current Phase 0 audit. | evidence-grade | Use as handoff evidence. |
| `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current G artifact evidence. | evidence-grade | Use for traceability. |
| `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md` | `AUTHORITATIVE_CURRENT` | Current 177/180/truncation caveat. | evidence-grade | Use for caveat trace. |
| `audits/cluster2_c_paper_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current C artifact evidence. | evidence-grade | Use for traceability. |
| `audits/cluster2_g_plus_c_paper_n20_l4_report.md` | `AUTHORITATIVE_CURRENT` | Current G+C artifact evidence. | evidence-grade | Use for traceability. |
| `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md` | `AUTHORITATIVE_CURRENT` | F3 decision evidence. | evidence-grade | Promote into docs. |
| `audits/factorial_cluster1_functional_success_normalization_fix_report.md` | `AUTHORITATIVE_CURRENT` | C1 functional-success normalization evidence. | evidence-grade | Use for traceability. |
| `audits/factorial_cluster2_compile_success_normalization_fix_report.md` | `LEGACY_EVIDENCE` | Important history, but blocker superseded by F3 policy/output. | evidence-grade | Add superseded header later. |
| `audits/factorial_2x2_preliminary_analysis_report.md` | `LEGACY_EVIDENCE` | Superseded by analyzer output. | evidence-grade | Add superseded header later. |
| older n5/template/pre-paper audits | `LEGACY_EVIDENCE` | Historical context only. | evidence-grade | Mark legacy before sharing. |
| `cluster1/README.md` | `NEEDS_UPDATE` | Stale task-agnostic/template-G status. | citation-grade after update | Rewrite. |
| `cluster1/docs/grammar_surface_contract.md` | `AUTHORITATIVE_CURRENT` | Grammar surface boundary. | citation-grade | Keep. |
| `cluster1/grammar/corpus/api_coverage_report.md` | `AUTHORITATIVE_CURRENT` | Grammar API coverage. | citation/evidence | Keep. |
| `cluster1/grammar/triton_kernel_agnostic.gbnf` | `AUTHORITATIVE_CURRENT` | Current primary task-agnostic grammar file. | code artifact | Do not modify in handoff docs phases. |
| `cluster1/grammar/triton_kernel.gbnf` | `AUTHORITATIVE_CURRENT` | Template/reference grammar file. | code artifact | Keep diagnostic/reference only. |
| `cluster1/notebooks/*.ipynb` | `UNKNOWN` | Not reviewed cell-by-cell. | ignored | Do not cite. |
| `cluster2/README.md` | `NEEDS_UPDATE` | Stale task-agnostic and C2 status. | citation-grade after update | Rewrite. |
| `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` | `AUTHORITATIVE_CURRENT` | Current replay manifest and coverage policy. | artifact/contract evidence | Reference in docs; do not rewrite in Phase 1. |
| `cluster2/constants.py` | `NEEDS_UPDATE` | Stale default token/artifact values. | code evidence | Do not use for future runs until fixed. |
| `cluster3/README.md` | `AUTHORITATIVE_CURRENT` | Correct P/Cluster 3 deferred status. | citation-grade for deferral | Keep. |
| `shared/analysis/factorial.py` | `AUTHORITATIVE_CURRENT` | Current analyzer behavior source. | code evidence | Cite via docs, not directly in report prose. |
| `shared/factors/registry.py` | `AUTHORITATIVE_CURRENT` | Current factor-cell/cluster ownership. | code evidence | Use for traceability. |
| `shared/configs/experiment.yaml` | `AUTHORITATIVE_CURRENT` | Current shared paper-scale n/token budget config. | code/config evidence | Keep. |
| `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | `AUTHORITATIVE_CURRENT` | Current none replay-control artifact. | artifact evidence | Do not modify. |
| `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | `AUTHORITATIVE_CURRENT` | Current primary G artifact. | artifact evidence | Do not modify. |
| `outputs/cluster2/c_paper_n20_l4.jsonl` | `AUTHORITATIVE_CURRENT` | Current C artifact. | artifact evidence | Do not modify. |
| `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | `AUTHORITATIVE_CURRENT` | Current G+C artifact. | artifact evidence | Do not modify. |
| `outputs/analysis/factorial_2x2_preliminary.json` | `AUTHORITATIVE_CURRENT` | Current analyzer output, reportable=false caveat. | citation-grade output after docs contextualize | Do not modify. |
| old n5/template JSONL and summaries | `LEGACY_EVIDENCE` | Historical/development or diagnostic artifacts. | evidence only | Mark legacy; do not cite as current. |
| duplicate old smoke summaries/TODOs | `DELETE_CANDIDATE_LATER` | Search noise after consolidation. | ignored | Delete only after approval. |
