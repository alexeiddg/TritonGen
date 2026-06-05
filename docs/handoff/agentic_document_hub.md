# Agentic Documentation Hub

Version: 1.29.0
Date: 2026-06-05
Status: agent-facing operational index
Audience: Codex, Claude Code, and future engineering agents
Citation status: routing document only; do not cite as methodology

## Purpose

This hub is the central starting point for repository agents. It indexes where
project knowledge lives, what to read for common issue classes, and which docs
must be updated when code changes.

It intentionally includes relevant project-owned markdown that is ignored by
git, including `docs/`, `audits/`, `outputs/`, and `.contracts/agentic/`.
Excluded from this hub are vendored or duplicated markdown files under
`.venv/`, `.pytest_cache/`, and `.claude/worktrees/`.

## Start Here

Before changing code or docs:

1. Run `git status --short` and preserve unrelated user changes.
2. Read this file.
3. Read `docs/handoff/document_version_registry.md`.
4. Read `docs/handoff/code_update_documentation_policy.md`.
5. Pull the issue-specific read set below.
6. Verify claims against the source-of-truth hierarchy before editing.

## Source-Of-Truth Hierarchy

When files disagree, use this order:

1. Current code and tests define behavior.
2. Current output artifacts define observed results.
3. `docs/` defines human-readable methodology and handoff policy.
4. `.contracts/research/` defines formal methodology constraints.
5. `audits/` provides evidence snapshots and investigation history.
6. `.contracts/agentic/` provides agent context and operational plans only.

Agentic docs and audits can explain why something happened, but methodology
claims must be promoted into `docs/` or `.contracts/research/` before they are
treated as report-facing.

## Core Control Documents

| Need | File |
|---|---|
| Full path-by-path markdown inventory and document versions | `docs/handoff/document_version_registry.md` |
| Code-to-doc update rules | `docs/handoff/code_update_documentation_policy.md` |
| Current project scope and trust policy | `docs/00_project_map.md` |
| Experiment change orchestration contract | `docs/15_experiment_change_orchestration_contract.md` |
| Observability sidecar implementation spec | `docs/16_observability_sidecar_implementation_spec.md` |
| MLflow tracking policy | `.contracts/research/mlflow_tracking_policy.md` |
| MLflow tracking onboarding | `docs/tracking/README.md` |
| Structural/task analyzer metadata implementation spec | `docs/17_structural_task_analyzer_metadata_implementation_spec.md` |
| Agentic transcript implementation spec | `docs/18_agentic_transcript_v1_implementation_spec.md` |
| Agentic transcript run-packet template | `docs/handoff/agentic_transcript_v1_run_packet_template.md` |
| Agentic transcript next-run packet draft | `docs/handoff/agentic_transcript_v1_next_run_packet.md` |
| Experiment change orchestration state | `docs/handoff/experiment_change_orchestration_state.md` |
| Current artifact identities and caveats | `docs/05_artifacts_and_results_registry.md` |
| Current Cluster 3/P methodology | `docs/04_methodology_cluster3.md` |
| Current handoff guide | `docs/handoff/codebase_handoff_guide.md` |
| Stale-doc risk map | `docs/handoff/stale_docs_inventory.md` |
| Current agent phase state | `.contracts/agentic/preliminary_report_handoff/phase_state.md` |
| Completed handoff-readiness plan | `.contracts/agentic/preliminary_report_handoff_readiness_plan.md` |

## Current Cluster 3 Planning Gate

Cluster 3 diagnostic evidence is provenance-frozen through
`audits/cluster3_phase13b_commit_provenance_freeze_report.md`. Phase 14e froze
the optional four-cell n=5 development matrix in
`audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md`. The frozen
cells are P at `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`, C+P at
`outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`, G+C+P at
`outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`, and reused
G+P at `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`. Each cell has
five schema-valid elementwise/fp32 rows. The matrix has 20 rows total, zero P
attempts, and zero C fires, so it is development-scale condition coverage only
and insufficient repair-signal evidence. G+C+P and G+P use
`template_upper_bound` with `diagnostic_non_primary` grammar claim scope. For
the broader docs 12-14 change set, first read
`docs/15_experiment_change_orchestration_contract.md`; it controls parallel
branch ownership, serialized surfaces, and run gates. Then read and update
`docs/handoff/experiment_change_orchestration_state.md`; it is the canonical
live state file for active branches, agent launch packets, leases, gate status,
run packets, and next allowed actions. During parallel implementation work, the
state file is single-writer under the orchestrating agent; worker agents require
a launch packet and should return handoff notes or state patches instead of
mutating the state file directly. Launch packets must explicitly authorize any
network access, dependency downloads, credentialed calls, or secrets handling.
The orchestration contract is frozen for implementation use; add process only
when a concrete amendment trigger is recorded.
Observability implementation agents must also read
`docs/16_observability_sidecar_implementation_spec.md` before starting O0-O5
work. O3 token telemetry implementation agents must also read
`audits/observability_sidecar_o3_prep_report.md` and the active O3 launch
packet in `docs/handoff/experiment_change_orchestration_state.md` before
touching runtime code; O3 is limited to token count/status sidecar telemetry
when already available or cheaply computable and authorizes no token IDs,
prompt/source/generated/raw text capture, Modal execution, generation, output
mutation, billing/cost, tokenizer/model imports for telemetry, or performance
telemetry. O4 estimated cost telemetry implementation agents must also read
`audits/observability_sidecar_o4_prep_report.md` and the active O4 launch
packet in `docs/handoff/experiment_change_orchestration_state.md` before
touching runtime code; O4 is limited to supplied/static estimated or unavailable
sidecar cost metadata and authorizes no actual billing, invoices, account
charges, provider/Modal billing, billing API calls, external pricing fetches,
cost-per-success, pass@k cost, ROI, economic lift, benchmark economics, Modal
execution, generation, output mutation, analyzer/economic metric changes,
dependency changes, result-row schema changes, or performance telemetry.
O5 actual billing reconciliation agents must also read
`audits/observability_sidecar_o5_prep_report.md` and a later explicit O5 launch
or billing-query approval packet before touching runtime code, querying billing,
using credentials, processing exported billing reports, or mutating historical
sidecars. O5 is limited to post-hoc sidecar-only actual-billing reconciliation
metadata and authorizes no raw invoice/API-response storage,
cost-per-success, pass@k cost, ROI, economic lift, benchmark economics,
performance/profiler/timing work, result-row schema mutation, analyzer/economic
metric changes, output mutation, dependency changes, Modal execution, or
generation.
Structural/task analyzer, report-metadata, and future experiment packet agents
must also read
`docs/17_structural_task_analyzer_metadata_implementation_spec.md` before
starting S0-S4 work. S4 future experiment integration is planning-only packet
guidance: it requires metric-family, gate, denominator, evidence-source, and
claim-boundary declarations before future experiments, but authorizes no
Modal/GPU/generation, output mutation, analyzer output refresh, report artifact
refresh, raw JSONL rewrite, benchmark, profiler, timing, speedup, or paper-scale
work. Agentic repair-memory implementation agents must also read
`docs/18_agentic_transcript_v1_implementation_spec.md` before starting A0-A6
work. Before any future `agentic_transcript_v1` Modal, generation, n=5, n=20,
paper-scale, or output-mutating work, agents must also read
`docs/handoff/agentic_transcript_v1_run_packet_template.md` and the current
draft or approved packet. The current draft is
`docs/handoff/agentic_transcript_v1_next_run_packet.md`, has status
`DRAFT_NOT_APPROVED`, and authorizes no execution.

Do not run Modal, n=5, n=20, paper-scale work, generation, experiments, or
output mutation from this freeze state without separate explicit approval. Any
broader matrix analysis, paper-scale readiness decision, Modal run, n=20,
all-condition, generation, experiment, or profiling work requires a fresh
approval packet with scope, artifact paths, stop conditions, and claim
boundaries.

## Issue Pull Sets

Use these as the first files to open for each issue type. Then inspect the
referenced code and tests before editing.

| Issue type | Read first | Then inspect | Evidence and artifacts |
|---|---|---|---|
| Cluster 2 correctness, C, or G+C behavior | `docs/03_methodology_cluster2.md`; `docs/cluster2_c_limitation_memo.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` decisions D05-D14 and D17 | `cluster2/feedback/`; `cluster2/experiments/run_cluster2_modal.py`; `cluster2/modal/`; `cluster2/replay/`; `cluster2/results/`; `cluster2/validation/`; `shared/eval/`; `shared/analysis/factorial.py`; `cluster2/tests/`; `shared/tests/` | `outputs/cluster2/c_paper_n20_l4.jsonl`; `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`; diagnostic template G+C: `outputs/cluster2/template_g_plus_c_paper_n20_l4.jsonl`; `outputs/analysis/factorial_2x2_preliminary.json`; `audits/cluster2_g_plus_c_readiness_audit.md`; `audits/cluster2_c_paper_n20_l4_report.md`; `audits/cluster2_g_plus_c_paper_n20_l4_report.md`; `audits/template_g_plus_c_paper_n20_l4_run_report.md` |
| Cluster 2 replay or paired identity | `docs/03_methodology_cluster2.md`; `docs/07_analysis_and_statistics.md`; `docs/05_artifacts_and_results_registry.md`; `.contracts/agentic/cluster2_paired_replay_alignment_plan.md` | `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`; `cluster2/replay/manifest.py`; `cluster2/replay/cluster1_controls.py`; `shared/analysis/factorial.py`; `cluster2/tests/test_replay_controls.py`; `cluster2/tests/test_replay_manifest.py`; `shared/tests/test_factorial_analysis.py` | `audits/c2_replay_readiness_for_g_plus_c_from_g_n20_audit.md`; `audits/analyzer_pre_output_verification_audit.md`; current none/G/C/G+C artifacts |
| Cluster 2 feedback content or F2-only policy | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/08_decision_log.md` D05 and D12; `docs/13_agentic_repair_memory_strategy.md`; `docs/18_agentic_transcript_v1_implementation_spec.md`; `.contracts/agentic/cluster2_f2_repair_smoke_plan.md` | `cluster2/feedback/prompts.py`; `cluster2/feedback/repair_loop.py`; `cluster2/feedback/trace.py`; `cluster2/tests/test_feedback_prompts.py`; `cluster2/tests/test_repair_loop.py`; `cluster2/tests/test_generated_eval_ladder.py` | `audits/g_plus_c_correctness_payload_failure_fix_report.md`; `audits/c2_generated_eval_level0_level1_fix_report.md`; Cluster 2 smoke outputs |
| Cluster 1 grammar or G behavior | `docs/02_methodology_cluster1.md`; `cluster1/docs/grammar_surface_contract.md`; `.contracts/research/cluster1_generated_surface.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/08_decision_log.md` D02-D04, D19, and D20 | `cluster1/grammar/triton_kernel_agnostic.gbnf`; `cluster1/grammar/triton_kernel.gbnf`; `cluster1/grammar/triton_kernel_validator.py`; `cluster1/generation/`; `cluster1/results/`; `cluster1/validation/`; `cluster1/tests/` | Current primary: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`; current diagnostic only: `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`; legacy diagnostic only: `outputs/cluster1/final_g_l4_n20.jsonl`; `audits/task_agnostic_g_aligned_pipeline_n20_l4_report.md`; `audits/task_agnostic_g_n20_missing_rows_and_token_exhaustion_rca.md`; `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md`; `audits/template_g_180_legacy_compatibility_audit.md` |
| Artifact identity, row counts, schema, or provenance | `docs/05_artifacts_and_results_registry.md`; `docs/04_modal_infrastructure.md`; `docs/07_analysis_and_statistics.md`; `.contracts/research/scale_policy.md` | Result dataclasses/loggers and validators in `cluster1/results/`, `cluster2/results/`, `cluster2/validation/`, and `shared/generation_metadata.py` | Raw outputs under `outputs/`; relevant `.meta.json` or `.hashes.json`; `audits/repository_documentation_methodology_readiness_audit.md`; `audits/final_documentation_consistency_audit.md`; `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md` |
| Analyzer, statistics, reportability, or paper tables | `docs/07_analysis_and_statistics.md`; `docs/05_artifacts_and_results_registry.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/14_structural_vs_task_outcome_reporting_plan.md`; `docs/17_structural_task_analyzer_metadata_implementation_spec.md`; `docs/08_decision_log.md` D13-D14 | `shared/analysis/factorial.py`; `shared/tests/test_factorial_analysis.py`; `shared/eval/reporting/`; `shared/eval/constants.py` | `outputs/analysis/factorial_2x2_preliminary.json`; `audits/analyzer_reportability_blocker_audit.md`; `audits/analyzer_scale_tier_reportability_fix_report.md`; `audits/factorial_2x2_preliminary_analysis_report.md` |
| Modal, remote execution, hashes, observability, tracking, or durability | `docs/04_modal_infrastructure.md`; `docs/12_experiment_observability_plan.md`; `docs/16_observability_sidecar_implementation_spec.md`; `audits/observability_sidecar_o3_prep_report.md` before O3 implementation; `audits/observability_sidecar_o4_prep_report.md` before O4 implementation; `audits/observability_sidecar_o5_prep_report.md` before O5 implementation; `.contracts/research/mlflow_tracking_policy.md`; `docs/tracking/README.md`; `shared/tracking/README.md`; `.contracts/agentic/modal_integration_plan.md`; `.contracts/agentic/modal_harness_draft.md`; `docs/08_decision_log.md` D09-D11 and D16 | `shared/modal_harness/`; `shared/observability/` if present; O3 target surfaces after O3-Prep are only `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `cluster3/experiments/run_cluster3_modal.py`; O4 target surfaces after O4-Prep are only `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, and `cluster3/experiments/run_cluster3_modal.py` for supplied estimated/unavailable sidecar cost metadata; O5 target surfaces after O5-Prep are only `shared/observability/schema.py`, `shared/observability/redaction.py`, `shared/observability/logger.py`, `shared/observability/billing_reconciliation.py`, and focused `shared/tests/test_observability_*` tests unless a later launch packet explicitly names more; `shared/tracking/`; `cluster1/experiments/run_cluster1_modal.py`; `cluster2/experiments/run_cluster2_modal.py`; `cluster3/experiments/run_cluster3_modal.py`; `cluster1/results/logger.py`; `cluster2/results/logger.py`; `cluster3/results/logger.py`; `cluster2/modal/`; `cluster3/modal/`; `shared/eval/content_hashes.py` | `audits/observability_sidecar_o1_runner_instrumentation_report.md`; `audits/observability_sidecar_o2_prep_report.md`; `audits/observability_sidecar_o2_modal_context_report.md`; `audits/observability_sidecar_o3_prep_report.md`; `audits/observability_sidecar_o3_token_telemetry_report.md`; `audits/observability_sidecar_o4_prep_report.md`; `audits/observability_sidecar_o4_estimated_cost_report.md`; `audits/observability_sidecar_o0_o4_final_acceptance_report.md`; `audits/observability_sidecar_o5_prep_report.md`; `audits/shared_modal_smoke_boundary_hash_resolution_report.md`; `audits/modal_image_sha_provenance_fix_report.md`; `audits/c2_durable_result_writing_fix_report.md`; `audits/g_plus_c_hash_gate_and_metadata_fix_report.md`; `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md` |
| Preliminary report drafting | `docs/09_preliminary_report_outline.md`; `docs/preliminary_report/README.md`; `README.md`; `docs/00_project_map.md`; `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md`; `docs/cluster2_c_limitation_memo.md`; `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md`; `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md`; `docs/08_decision_log.md` | Report generation assets if present under `docs/preliminary_report/`; analyzer output only after reportability caveat is handled | `audits/final_documentation_consistency_audit.md`; `outputs/analysis/factorial_2x2_preliminary.json` |
| Cluster 3 or P planning | `docs/04_methodology_cluster3.md`; `docs/05_artifacts_and_results_registry.md` Cluster 3 section; `docs/08_decision_log.md` D21-D30; `docs/cluster3_implementation_specification.md`; `docs/13_agentic_repair_memory_strategy.md`; `docs/18_agentic_transcript_v1_implementation_spec.md`; `.contracts/agentic/preliminary_report_handoff/phase_state.md`; `audits/cluster3_phase0_scaffolding_report.md`; `audits/cluster3_phase1_p_repair_loop_report.md`; `audits/cluster3_phase2_schema_logger_report.md`; `audits/cluster3_phase3_dispatcher_report.md`; `audits/cluster3_phase4_correctness_adapter_report.md`; `audits/cluster3_phase5_runner_orchestration_report.md`; `audits/cluster3_phase6_replay_manifest_report.md`; `audits/cluster3_phase7a_analyzer_support_report.md`; `audits/cluster3_phase8_f1_fixture_smoke_report.md`; `audits/cluster3_phase9_boundary_tests_report.md`; `audits/cluster3_phase9_boundary_latency_remediation_report.md`; `audits/cluster3_phase10_documentation_report.md`; `audits/cluster3_phase11_modal_n1_smoke_report.md`; `audits/cluster3_phase11_modal_hydration_remediation_report.md`; `audits/cluster3_phase12_gp_template_grammar_n5_report.md`; `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md`; `audits/cluster3_phase12c_f1_fixture_alignment_report.md`; `audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md`; `audits/cluster3_phase12e_initial_f2_c_loop_modal_report.md`; `audits/cluster3_phase13_diagnostic_evidence_freeze_report.md`; `audits/cluster3_phase13b_commit_provenance_freeze_report.md`; `audits/cluster3_phase14_n5_condition_matrix_plan.md`; `audits/cluster3_phase14a_p_only_n5_modal_report.md`; `audits/cluster3_phase14b_c_plus_p_n5_modal_report.md`; `audits/cluster3_phase14c_g_plus_c_plus_p_n5_modal_report.md`; `audits/cluster3_phase14d_g_plus_p_reuse_vs_rerun_decision.md`; `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md`; `docs/10_cluster3_drift_prevention_plan.md`; `cluster3/README.md`; `.contracts/research/eval_metrics.md` Cluster 3 sections | `cluster3/`; Phase 0-10 local implementation and documentation work is complete with the known Cluster 1 docs-lock warning; Phase 11 hydration remediation produced one validated n=1 P smoke row at `outputs/cluster3/p_smoke_l4_n1.jsonl`; Phase 12 produced one validated n=5 `G+P` template-grammar development artifact at `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`, observed zero `F1_COMPILE` seeds and zero P attempts, and Phase 14d approved it for reuse as the Phase 14 G+P matrix cell; Phase 12b targeted F1 diagnostics attempted two n=1 fixture runs at `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl` and `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl`, both zero-row blocked outputs because the fixtures classified remotely as `F0_BAD_SIGNATURE`; Phase 12c aligned a launcher-compatible F1 fixture locally; Phase 12d validated one remote `F1_COMPILE` -> P-loop branch row; Phase 12e validated one remote initial-F2 -> C-loop branch row under `G+C+P`; Phase 13 froze diagnostic evidence and Phase 13b verified commit/provenance freeze; Phase 14 planned the smallest optional n=5 condition matrix without execution; Phase 14a generated one validated P-only n=5 matrix cell at `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` with five `F0_PARSE` rows, zero `F1_COMPILE` seeds, zero P attempts, and zero C fires; Phase 14b generated one validated C+P n=5 matrix cell at `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` with five `F0_PARSE` rows, zero `F1_COMPILE` seeds, zero initial F2 rows, zero P attempts, and zero C fires; Phase 14c generated one validated G+C+P n=5 matrix cell at `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` with five clean-success rows, `template_upper_bound` diagnostic grammar metadata, zero `F1_COMPILE` seeds, zero initial F2 rows, zero P attempts, and zero C fires; Phase 14e froze the four-cell development matrix with 20 schema-valid rows, validated hash sidecars, clean boundary scans, no disallowed unsupported claims, zero P attempts, and zero C fires; agentic C/P repair-memory work is now routed through `docs/18_agentic_transcript_v1_implementation_spec.md`; the archived Phase 11 zero-row blocked attempt remains under `outputs/cluster3/blocked/`; broader development-scale, all-condition, additional diagnostic, n=20, paper-scale, and performance/profiling runs require separate explicit approval; Phase 7a analyzer support remains documented with its out-of-scope shared documentation-language validation blocker | `audits/cluster3_implementation_plan_draft_report.md`; `audits/cluster3_specification_e_patch_report.md`; `audits/cluster3_specification_f_cleanup_report.md`; `audits/cluster3_specification_g_contract_cleanup_report.md`; `audits/cluster3_specification_h_pre_phase0_cleanup_report.md`; `audits/cluster3_specification_i_final_pre_phase0_report.md`; `audits/pre_paper_factorial_audit.md` |
| Documentation drift or stale claims | This hub; `docs/handoff/document_version_registry.md`; `docs/handoff/code_update_documentation_policy.md`; `docs/handoff/stale_docs_inventory.md`; `docs/00_project_map.md` | All docs touched by the code change; `README.md`; `.contracts/research/` if formal methodology changed | `audits/final_documentation_consistency_audit.md`; `.contracts/agentic/preliminary_report_handoff/phase_state.md` |

## Markdown Shelves

The exhaustive path inventory and document versions live in
`docs/handoff/document_version_registry.md`. Use these shelves to orient before
opening individual files:

| Shelf | Role | Citation policy |
|---|---|---|
| `README.md` and cluster READMEs | Entry points and component summaries | Root README is current; cluster READMEs may be stale unless registry says otherwise |
| `docs/*.md` | Current report-facing handoff and methodology docs | Citation-grade after verification against artifacts and code |
| `docs/handoff/*.md` | Agent handoff, versioning, stale-doc, and update policy | Operational, not result citation |
| `.contracts/research/*.md` | Formal methodology contracts | Citation-grade with stated caveats |
| `.contracts/agentic/*.md` | Agent plans, local runbooks, reference caches, and phase state | Agent-internal unless promoted |
| `audits/*.md` | Evidence snapshots and investigation records | Evidence-grade; do not cite as primary methodology |
| `outputs/**/*.md` | Generated output summaries | Evidence or legacy summaries; registry controls authority |
| `cluster1/**/*.md`, `cluster2/**/*.md`, `cluster3/**/*.md` | Component documentation and grammar/test fixture docs | Use cautiously; cross-check against `docs/` and registry |

## Search Commands

Use this command to find project-owned markdown, including ignored files:

```bash
find . -name '*.md' \
  -not -path './.git/*' \
  -not -path './.venv/*' \
  -not -path './.claude/worktrees/*' \
  -not -path './.pytest_cache/*' \
  -not -path './node_modules/*' \
  -not -path './build/*' \
  -not -path './dist/*'
```

Use this command to see tracked markdown only:

```bash
git ls-files -- '*.md'
```

If those lists differ, the ignored project-owned docs are still part of the
agentic knowledge base and must be considered for documentation impact.

## Maintenance Rule

Any change to code, output artifacts, analysis behavior, methodology, report
scope, or agent-facing process must update:

- the relevant methodology or policy doc,
- `docs/handoff/document_version_registry.md`,
- and any affected entry point such as `README.md`, `docs/00_project_map.md`,
  or `docs/handoff/codebase_handoff_guide.md`.

Use `docs/handoff/code_update_documentation_policy.md` for the required mapping.
