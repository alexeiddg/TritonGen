# Full Pipeline Launch Packet v1 12-Cell Patch Report

## Executive Summary

This report records the docs-only patch that changes the active Full Pipeline
Launch Packet v1 design from the superseded 8-cell plan to the selected 12-cell
`grammar_mode x C x P` design.

It also records creation of the unsigned L1a n=1 authorization packet draft:

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`

No execution, output mutation, analyzer refresh, report refresh, MLflow runtime
write, billing query, dependency change, or lockfile change is authorized or
performed by this patch.

## Reason For Patch

The active launch packet and future L1a preregistration must agree before any
execution packet can be prepared. The old 8-cell plan would disagree with the
intended grammar-mode-expanded design, so the launch packet needed to be patched
first.

## Old Design Vs New Design

Old design:

- superseded 8-cell plan over grammar on/off plus C/P feedback;
- old namespace: `full_pipeline_gcp_factorial_v1`;
- old ladder: L1 smoke/dev before L2 n20.

New selected design:

- 12-cell `grammar_mode x C x P`;
- `grammar_mode` values are `grammar_off`, `primary_grammar`, and
  `task_agnostic_grammar`;
- fresh namespace: `full_pipeline_grammar_mode_cp_factorial_v1`;
- ladder: L1a n=1, L1b n=5, L2 n=20.

The old design is superseded for future execution and remains historical
context only.

## Twelve-Cell Matrix

| condition_id | grammar_mode | C | P |
|---|---|---:|---:|
| `grammar_off__c_off__p_off` | `grammar_off` | off | off |
| `grammar_off__c_on__p_off` | `grammar_off` | on | off |
| `grammar_off__c_off__p_on` | `grammar_off` | off | on |
| `grammar_off__c_on__p_on` | `grammar_off` | on | on |
| `primary_grammar__c_off__p_off` | `primary_grammar` | off | off |
| `primary_grammar__c_on__p_off` | `primary_grammar` | on | off |
| `primary_grammar__c_off__p_on` | `primary_grammar` | off | on |
| `primary_grammar__c_on__p_on` | `primary_grammar` | on | on |
| `task_agnostic_grammar__c_off__p_off` | `task_agnostic_grammar` | off | off |
| `task_agnostic_grammar__c_on__p_off` | `task_agnostic_grammar` | on | off |
| `task_agnostic_grammar__c_off__p_on` | `task_agnostic_grammar` | off | on |
| `task_agnostic_grammar__c_on__p_on` | `task_agnostic_grammar` | on | on |

## L1a/L1b/L2 Ladder

| Level | Scope | Purpose | Evidence status |
|---|---|---|---|
| L1a | 12 cells, n=1 | command/path/schema/sidecar/analyzer/MLflow-indexing validation | smoke/dev only; not paper evidence |
| L1b | 12 cells, n=5 | condition-specific instability, repair-loop activation, analyzer/report stability | development only; not paper evidence |
| L2 | 12 cells, n=20 | paper-scale candidate after gates pass | blocked pending L1a, L1b, Gate G8, exact costs/commands/paths, and signed approval |

## Namespace Changes

New namespace family:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/mlflow_index/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/
```

The old `full_pipeline_gcp_factorial_v1` namespace must not be used for this
design. If any target path exists, future launch must stop unless a signed
resume/append/archive policy is approved.

## Metric-Family Implications

- `structural_code_surface` comparisons now include `grammar_mode` as a
  three-level factor.
- `task_functional` comparisons now include `grammar_mode` as a three-level
  factor.
- C/P interactions must be analyzed conditional on `grammar_mode`.
- Grammar-mode comparison must not be collapsed into a binary active-grammar
  label for primary claims.
- Derived active-grammar summaries may be diagnostic only if the derivation is
  explicit.

## Old-Run Comparability Update

- Previous 8-cell or 4-cell planning artifacts are superseded for future
  execution.
- Historical runs can be used only as historical baselines or diagnostics.
- Old `last_attempt_only_v1` rows must not be mixed with
  `agentic_transcript_v1` rows for primary claims.
- Old one-grammar outputs must not be used as if they cover both active grammar
  modes.
- Template/diagnostic grammar rows must not be promoted to primary grammar rows
  without a future explicit contract change.

## Unresolved Code-Support Checks

The planning patch is complete, but L1a execution remains blocked:

- `shared/generation_metadata.py` exposes `template_upper_bound` and
  `task_agnostic` grammar variants.
- Current docs record `task_agnostic` as report-facing primary grammar and
  `template_upper_bound` as diagnostic/non-primary.
- `cluster3/experiments/run_cluster3_modal.py` exposes `grammar_variant`, not a
  first-class three-level `grammar_mode` selector.
- A future signer must confirm whether `primary_grammar` is distinct from
  `task_agnostic_grammar`, map both active grammar modes to exact grammar paths
  and hashes, and prove rows/analyzers can carry `grammar_mode`.

## No-Execution Proof

No Modal, GPU, generation, experiment, benchmark, profiler, timing, speedup,
billing query, MLflow runtime, or paper-scale command was run for this patch.

All execution flags in the patched launch packet and L1a authorization packet
remain `NO`, and both packet statuses remain `DRAFT_NOT_APPROVED`.

## No-Output/Mlruns Mutation Proof

The patch scope is limited to:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/full_pipeline_launch_packet_v1_12cell_patch_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

No `outputs/`, `artifacts/`, or `mlruns/` file is intentionally modified by
this patch.

## Validation Commands

Final validation results after patch files were written:

| Command/check | Result |
|---|---|
| `git diff --check` | pass; empty output |
| `git status --short --branch` | expected docs/audit packet changes on `codex/full-pipeline-l1-smoke-dev-approval-packet` |
| protected-scope diff for outputs, artifacts, mlruns, code, schemas, dependencies, and lockfiles | pass; empty output |
| execution-authorization scan over `docs`, `audits`, and `.contracts` | pass; empty output |
| 12-cell terminology scan | pass; required terms present |
| old-design anti-ambiguity scan | pass; hits are historical/superseded context only |
| MLflow source-of-truth scan | acceptable; hits explicitly state MLflow is not authoritative or that repo artifacts remain authoritative |

## Classification

`FULL_PIPELINE_LAUNCH_PACKET_12CELL_PATCH_BLOCKED_CODE_SUPPORT_AMBIGUITY`

The selected design is patched to the 12-cell `grammar_mode x C x P` design,
and the L1a n=1 draft authorization packet exists. Execution remains blocked
pending explicit approval and grammar-mode support/mapping proof.

## Next-Step Recommendation

Review this patch and the unsigned L1a authorization packet. Do not create or
run an L1a execution packet until the patched launch packet wording is accepted
and a future signed authorization resolves the grammar-mode support/mapping
blocker.
