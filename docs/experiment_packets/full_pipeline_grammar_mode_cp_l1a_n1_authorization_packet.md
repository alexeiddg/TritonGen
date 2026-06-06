# Full Pipeline Grammar-Mode x C x P L1a n=1 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
packet_version: `0.5.2`
packet_type: completed review packet for possible future authorization; not an execution packet until signed
branch: `codex/l1a-executable-12cell-selector-support`
target_branch: `codex-track-handoff-context`
target_commit: `REQUIRED_AFTER_SELECTOR_SUPPORT_REVIEW_COMMIT_AND_PROMOTION`
baseline_commit: `e96f70a Audit L1a signature readiness gap closure promotion`
planning_baseline_commit: `59fa0d6 Audit L1a approval packet promotion`
previous_execution_planning_baseline_commit: `c256af5 Audit Modal preflight estimator promotion`
code_support_commit: `c24fbaa Add local grammar-mode support for 12-cell L1a`
baseline_pin_commit: `d172e02 Pin L1a packet to grammar mode support baseline`
launcher_support_branch: `codex/grammar-mode-12cell-launcher-support`
launcher_support_commit: `e914557 Add dry-plan launcher support for 12-cell grammar mode matrix`
launcher_support_promotion_audit_commit: `76ede6a Audit 12-cell launcher support promotion`
launcher_support_status: `LOCAL_DRY_PLAN_SELECTOR_READY`
preflight_estimator_commit: `bd89e67 Add local Modal preflight cost time estimator`
preflight_estimator_promotion_audit_commit: `c256af5 Audit Modal preflight estimator promotion`
preflight_estimator_status: `LOCAL_ADVISORY_SYNTHETIC_PLACEHOLDER_ATTACHED_NOT_SIGNABLE`
superseded_baseline_commit: `0cc43c1 Audit full pipeline launch packet promotion`
launch_packet: `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
created_at: 2026-06-05
baseline_pinned_at: 2026-06-05
packet_completed_at: 2026-06-06
signature_readiness_gap_closure_at: 2026-06-06
signature_readiness_gap_closure_commit: `616ae01 Close L1a signature readiness gaps`
signature_readiness_gap_closure_promotion_audit_commit: `e96f70a Audit L1a signature readiness gap closure promotion`
executable_selector_support_branch: `codex/l1a-executable-12cell-selector-support`
executable_selector_support_status: `LOCAL_EXECUTABLE_SELECTOR_COMMAND_BUNDLE_READY_NO_EXECUTION`
status: `DRAFT_READY_FOR_USER_SIGNATURE`
DRAFT_READY_FOR_USER_SIGNATURE: YES
code_support_status: `LOCAL_REPRESENTABILITY_DRY_PLAN_AND_EXECUTABLE_SELECTOR_PLAN_READY`
execution_readiness_status: `BLOCKED_SIGNATURE_UNSIGNED_LIMITS_PREFLIGHT_IMAGE_BILLING_VALIDATION`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
CREDENTIAL_USE_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

This packet is complete for review and possible future user signature. It is
not signed and does not authorize Modal, GPU work, generation, experiments,
output mutation, analyzer output refresh, report artifact refresh, MLflow
runtime writes, billing queries, dependency changes, lockfile changes, or
paper-scale claims.

The active signature-readiness baseline is the promoted handoff trunk commit
`e96f70a`, which includes gap-closure commit `616ae01`. The earlier signature
review packet target `59fa0d6` is historical context for v0.5.1 and predates
the executable selector support added on this branch. Any future signed
execution target must be a reviewed and promoted descendant that includes the
selector support commit. The older `0cc43c1` and `d172e02` baselines are
historical context only and are not sufficient as the current L1a target
because they predate later launcher and estimator support.

Execution remains blocked even after local launcher support because this packet
is unsigned and still lacks approved numeric stop/spend limits, a signable
preflight estimate, remote image digest, billing-query authorization, and
post-run validation authorization. The current Cluster 3 CLI now exposes local
dry-plan and executable-plan selector surfaces for
`--condition grammar_mode_cp_12cell`. Both can select all 12
`grammar_mode x C x P` cells, including the six no-P control cells. The
executable-plan surface constructs exact per-cell future command strings with
target paths and a signed-authorization placeholder; it does not invoke Modal,
generation, correctness evaluation, output writing, artifact writing, tracking,
or MLflow.

Any future signed execution packet must include an advisory preflight estimate
for the exact target scope before launch. The local utility
`cluster3/planning/modal_preflight_estimator.py` can estimate L1a/L1b/L2 row
counts, execution-shape envelopes, and larger-GPU breakeven requirements from
explicit user-supplied pricing and timing inputs. That estimate remains
planning-only: it does not authorize execution, does not replace billing
reconciliation, and does not constitute experimental evidence.

Pricing must be re-verified against official Modal documentation before any
future signature. Human-approved numeric stop limits and numeric spend limits
are also `REQUIRED_BEFORE_SIGNATURE`; the candidate limits in this packet are
`PROPOSED_NOT_SIGNED`.

## Final Approval Surface Summary

```text
target_branch: codex-track-handoff-context
target_commit: REQUIRED_AFTER_SELECTOR_SUPPORT_REVIEW_COMMIT_AND_PROMOTION
packet_completion_branch: codex/l1a-executable-12cell-selector-support
experiment_name: full_pipeline_grammar_mode_cp_factorial_v1
level: L1a
scale_tier: smoke/dev
n_per_cell: 1
cell_count: 12
design: grammar_mode x C x P
dry_plan_selector: --condition grammar_mode_cp_12cell --dry-plan
dry_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
executable_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
exact_intended_execution_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
output_root: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
observability_artifact_root: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
jsonl_path_pattern: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl
content_hash_sidecar_path_pattern: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl.hashes.json
observability_event_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl
observability_summary_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.summary.json
observability_hash_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl.hashes.json
AUTHORIZES_EXECUTION: NO
DRAFT_READY_FOR_USER_SIGNATURE: YES
```

The exact intended execution command surface is now source-backed locally by
`cluster3/experiments/run_cluster3_modal.py` and
`cluster3/planning/grammar_mode_matrix.py`, but it is not signed and is not a
launch command. The signed-authorization placeholder
`SIGNED_L1A_PACKET_ID_REQUIRED` must be replaced by a later explicit human
approval, and the current branch still refuses runtime selector execution before
tracking, generation, Modal, output writers, or observability writers. This
packet does not provide execution authorization.

## Signature Readiness Gap Closure Addendum

This addendum closes repo-local signature-readiness gaps where possible without
authorizing execution. Unresolved execution-critical fields remain explicitly
classified and must still be completed by a future human signature.

Resolved or narrowed fields:

| Field | Status | Source-backed value or classification |
|---|---|---|
| target commit | `REQUIRED_AFTER_SELECTOR_SUPPORT_REVIEW_COMMIT_AND_PROMOTION` | Future signed target must be a reviewed and promoted descendant containing executable selector support |
| executable command | `RESOLVED_LOCAL_COMMAND_SURFACE_NOT_SIGNED` | selector-level future command: `.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite`; per-cell commands are emitted by `--execution-plan` |
| observability run id convention | `PROPOSED_NOT_SIGNED` | global run id convention: `full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__target_<short_commit>__signed_<YYYYMMDDTHHMMSSZ>`; per-cell join key convention: `<run_id>__<condition_id>` |
| current dry-plan observability join key | `RESOLVED_PLANNING_METADATA` | `cluster3/planning/grammar_mode_matrix.py` emits `full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__<condition_id>` join keys |
| Modal app name | `RESOLVED_REPO_LOCAL` | `tritongen-gpu-harness` from `shared/modal_harness/app.py` |
| Modal image definitions | `RESOLVED_REPO_LOCAL_SOURCE_ONLY` | `shared/modal_harness/images.py` defines `llm_generation_image` and `triton_compile_image` |
| Modal image digest | `REQUIRED_BEFORE_SIGNATURE_REMOTE_IMAGE_DIGEST_UNKNOWN` | no Modal or remote image inspection is authorized in this phase |
| advisory preflight estimate | `NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER_ATTACHED` | pure local estimator run with synthetic pricing/timing inputs; official Modal pricing and measured/approved timing remain required |
| numeric stop/spend limits | `PROPOSED_NOT_SIGNED` | candidate limits are listed below for human approval only |
| billing reconciliation plan | `RESOLVED_PLAN_ONLY` | post-run billing is authoritative for actual spend; no billing query is authorized now |
| validation bundle | `PROPOSED_NOT_SIGNED_REQUIRES_POST_RUN_ARTIFACTS` | exact local command surfaces are listed below; analyzer/report writes remain unauthorized until signed |

Synthetic advisory estimate placeholder:

```text
estimate_status: NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER
estimator: cluster3/planning/modal_preflight_estimator.py
inputs: cell_count=12; n_per_cell=1; gpu_label=L4_SYNTHETIC_NOT_SIGNABLE; price_per_gpu_second=0.01; cold_start_seconds=10.0; model_load_seconds=20.0; generation_seconds_per_row=2.0; compile_correctness_seconds_per_row=3.0; repair_overhead_seconds_per_activated_repair=4.0; expected_p_activation_rate=0.25; expected_c_activation_rate=0.5; fanout_limit=4; safety_multiplier=1.0; fixed_overhead_seconds=5.0; pricing_source=synthetic_fixture_not_modal_pricing; pricing_verified=false; stage_timing_source=estimated
total_planned_rows: 12
recommended_shape_name: bounded_fanout_across_cells_seeds
estimated_parallel_wall_clock_seconds: 59.0
estimated_gpu_seconds: 221.0
estimated_cost: 2.21
warning_flags: advisory_only_not_experimental_evidence, pricing_reverification_required, stage_timing_inputs_estimated_not_measured
signability_status: NOT_SIGNABLE until official Modal pricing is re-verified, timing inputs are approved, and the estimate is attached to a signed packet
```

Proposed unsigned stop/spend limits:

```text
max_rows: 12
max_generation_attempts: PROPOSED_NOT_SIGNED_72_total_initial_plus_C_and_P_repair_attempt_ceiling
max_repair_attempts_per_row: PROPOSED_NOT_SIGNED_P_5_when_enabled_C_5_when_enabled_0_otherwise
max_correctness_calls: PROPOSED_NOT_SIGNED_72_total_attempt_ceiling
max_wall_clock: PROPOSED_NOT_SIGNED_4_hours
max_estimated_cost: PROPOSED_NOT_SIGNED_USD_25_requires_official_pricing_reverification
max_reconciled_billing_cost: PROPOSED_NOT_SIGNED_USD_50_billing_reconciliation_authoritative
max_modal_invocations: PROPOSED_NOT_SIGNED_REQUIRES_EXECUTION_SHAPE_SELECTION
stop_on_first_infrastructure_failure: PROPOSED_NOT_SIGNED_yes
retry_policy: PROPOSED_NOT_SIGNED_no_retry_no_resume_unless_explicitly_signed
```

Billing reconciliation plan:

```text
billing_reconciliation_status: PLAN_ONLY_NO_BILLING_QUERY_AUTHORIZED
authoritative_actual_spend_source: post-run reconciled Modal billing artifact
required_after_approved_run: signed start/end UTC window; signed experiment_id; signed run_id; redacted billing report path; redacted report sha256; reconciliation dry-run result; reconciliation write authorization if any sidecar mutation is requested
future_collection_command_status: REQUIRED_BEFORE_SIGNATURE_BILLING_QUERY_AUTHORIZATION_TIME_WINDOW_AND_REDACTED_OUTPUT_PATH_MISSING
future_collection_command_shape: .venv/bin/python -m modal billing report --start <YYYY-MM-DD> --end <YYYY-MM-DD> --resolution d --tag-names project,experiment_id,run_id,cluster,phase --json
local_reconciliation_surface: shared/observability/billing_reconciliation.py dry_run_reconciliation(...)
```

## Launch-Packet Dependency

This L1a packet depends on the patched launch packet selecting the 12-cell
`grammar_mode x C x P` design.

It must not be converted into an execution packet unless:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
  continues to name the 12-cell design as the active selected design;
- the old 8-cell design remains superseded for future execution;
- the output namespace uses
  `full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- local grammar-mode representability proof remains present on the target
  branch, including the 12-cell planner, row labeling, and analyzer grouping
  fixture tests;
- full 12-cell local dry-plan launcher support remains present for all no-P and
  P-containing cells, or a separate signed packet explicitly narrows the run and
  labels it diagnostic.

## Intended L1a Scope

Purpose:

- command/path validation;
- output namespace validation;
- row schema validation;
- content-hash sidecar validation;
- observability sidecar validation;
- analyzer grouping by `grammar_mode`;
- MLflow post-hoc indexing dry-run or fixture validation after artifacts exist.

Scale:

```text
level: L1a
scale_tier: smoke/dev
n_per_cell: 1
cell_count: 12
expected_rows_if_fully_executed: 12
paper_evidence: no
```

## Twelve-Cell Matrix

| condition_id | grammar_mode | correctness_feedback_C | compile_feedback_P |
|---|---|---:|---:|
| `grammar_off__c_off__p_off` | `grammar_off` | off | off |
| `grammar_off__c_on__p_off` | `grammar_off` | on | off |
| `grammar_off__c_off__p_on` | `grammar_off` | off | on |
| `grammar_off__c_on__p_on` | `grammar_off` | on | on |
| `template_upper_bound__c_off__p_off` | `template_upper_bound` | off | off |
| `template_upper_bound__c_on__p_off` | `template_upper_bound` | on | off |
| `template_upper_bound__c_off__p_on` | `template_upper_bound` | off | on |
| `template_upper_bound__c_on__p_on` | `template_upper_bound` | on | on |
| `task_agnostic__c_off__p_off` | `task_agnostic` | off | off |
| `task_agnostic__c_on__p_off` | `task_agnostic` | on | off |
| `task_agnostic__c_off__p_on` | `task_agnostic` | off | on |
| `task_agnostic__c_on__p_on` | `task_agnostic` | on | on |

## Grammar-Mode Mapping

Local representability now uses the repo-supported vocabulary. The execution
approval line remains unsigned until a future signer also supplies exact
runtime command/config, output paths, stop/spend limits, and preflight results.

| grammar_mode | required mapping before execution |
|---|---|
| `grammar_off` | `grammar_active=false`; `grammar_variant=null`; grammar file/hash/scope absent; rows label `grammar_mode=grammar_off` |
| `template_upper_bound` | `grammar_active=true`; `grammar_variant=template_upper_bound`; `grammar_path=cluster1/grammar/triton_kernel.gbnf`; claim scope `diagnostic_non_primary` |
| `task_agnostic` | `grammar_active=true`; `grammar_variant=task_agnostic`; `grammar_path=cluster1/grammar/triton_kernel_agnostic.gbnf`; claim scope `primary` |

Local code-support proof:

- `shared/factors/grammar_modes.py` defines the accepted values
  `grammar_off`, `template_upper_bound`, and `task_agnostic` and fail-closed
  binding checks against legacy `grammar_active`/`grammar_variant` metadata.
- `cluster3/planning/grammar_mode_matrix.py` returns exactly 12 local L1a
  cell specs with unique condition names and output namespace suffixes.
- `cluster3/experiments/run_cluster3_modal.py` exposes dry-plan and
  executable-plan surfaces for selector `grammar_mode_cp_12cell`, which expand
  to all 12 cells with deterministic output paths, content-hash sidecar paths,
  observability sidecar paths, grammar path/hash/scope metadata,
  repair-history policy, per-cell future command strings, signed-authorization
  placeholders, and no-overwrite policy markers.
- `cluster3/results/dataclass.py` and `shared/eval/schema.py` can carry
  `grammar_mode` while preserving existing `grammar_active` fields.
- `shared/analysis/factorial.py` can normalize/group explicit
  `grammar_mode` values and distinguishes `template_upper_bound` from
  `task_agnostic`.
- `primary_grammar` is not an executable selector in this repo. Earlier
  wording maps to `template_upper_bound` only when referring to the diagnostic
  template-upper-bound grammar, not to the primary task-agnostic grammar.

## Required Runtime Fields Before Approval

```text
approval_source: not_approved
approval_timestamp: not_applicable
target_branch: codex-track-handoff-context
target_commit: REQUIRED_AFTER_SELECTOR_SUPPORT_REVIEW_COMMIT_AND_PROMOTION
packet_completion_branch: codex/l1a-executable-12cell-selector-support
command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
command_manifest_status: LOCAL_EXECUTABLE_SELECTOR_COMMAND_BUNDLE_PRESENT_EXECUTION_UNSIGNED
working_directory: /Users/alexeidelgado/Desktop/TritonGen
exact_condition_list: twelve-cell matrix in this packet
output_root: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
observability_artifact_root: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
output_jsonl_paths: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl
content_hash_sidecar_paths: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl.hashes.json
observability_event_sidecar_paths: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl
observability_summary_sidecar_paths: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.summary.json
observability_hash_sidecar_paths: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl.hashes.json
model_id: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
model_revision: 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a
tokenizer_revision: 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a
decoding_config: temperature=0.2; max_new_tokens=1536
seed_policy: n=1 uses base_seed=0 per cell/invocation
kernel_class: elementwise
problem_ids: not_applicable_current_runner_uses_kernel_class_shape_metadata
dtype: fp32
shape_policy: elementwise locked-kernel shape metadata from current Cluster 3 runner
repair_history_policy: agentic_transcript_v1 for C-enabled or P-enabled cells; not_applicable when both C and P are off
grammar_modes: grammar_off, template_upper_bound, task_agnostic
grammar_file_paths: grammar_off=not_applicable_no_grammar; template_upper_bound=cluster1/grammar/triton_kernel.gbnf; task_agnostic=cluster1/grammar/triton_kernel_agnostic.gbnf
grammar_file_hash_lock: grammar_off=not_applicable_no_grammar; template_upper_bound=0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82; task_agnostic=7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32
observability_mode: best_effort
observability_experiment_id: full_pipeline_grammar_mode_cp_factorial_v1
observability_run_id: PROPOSED_NOT_SIGNED full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__target_<short_commit>__signed_<YYYYMMDDTHHMMSSZ>
observability_join_key_convention: <observability_run_id>__<condition_id>
mlflow_disposition: post_hoc_non_authoritative; runtime MLflow writes remain unauthorized; grammar-mode indexing patch remains deferred
max_rows: 12
max_generation_attempts: PROPOSED_NOT_SIGNED_72_total_initial_plus_C_and_P_repair_attempt_ceiling
max_repair_attempts_per_row: PROPOSED_NOT_SIGNED_P_5_when_enabled_C_5_when_enabled_0_otherwise
max_wall_clock: PROPOSED_NOT_SIGNED_4_hours
max_estimated_cost: PROPOSED_NOT_SIGNED_USD_25_requires_official_pricing_reverification
max_reconciled_billing_cost: PROPOSED_NOT_SIGNED_USD_50_billing_reconciliation_authoritative
preflight_estimate: NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER_advisory_only_pricing_and_timing_must_be_reverified
stop_on_first_infrastructure_failure: PROPOSED_NOT_SIGNED_yes
overwrite_policy: fail_if_any_target_path_exists
retry_policy: PROPOSED_NOT_SIGNED_no_retry_no_resume_unless_explicitly_signed
resume_policy: PROPOSED_NOT_SIGNED_no_resume_unless_explicitly_signed
billing_reconciliation_requirement: approved_post_run_modal_billing_reconciliation_required; estimates_do_not_replace_billing
modal_app_name: tritongen-gpu-harness
modal_image_sources: llm_generation_image and triton_compile_image in shared/modal_harness/images.py
modal_image_digest: REQUIRED_BEFORE_SIGNATURE_REMOTE_IMAGE_DIGEST_UNKNOWN
post_run_validation_commands: required list in Post-Run Validation and Analyzer Command Surface sections
```

## Preflight Estimate And Limit Requirements

No signable advisory preflight estimate is attached to this unsigned packet.
Only the synthetic `NOT_SIGNABLE` placeholder in the gap-closure addendum is
present.

Required before a future signature:

- attach an advisory output from `cluster3/planning/modal_preflight_estimator.py`
  for exactly the 12-cell L1a n=1 scope;
- record whether stage timing inputs are measured from approved prior sidecars
  or estimated;
- re-verify Modal pricing against official Modal documentation on the approval
  date;
- record exact numeric stop limits, including row, generation-attempt,
  correctness-call, repair-attempt, infrastructure-failure, and wall-clock
  ceilings;
- record exact numeric spend limits, including estimated preflight cap and
  post-run reconciled billing cap;
- state that estimates are not experimental evidence and do not replace JSONL
  rows, content-hash sidecars, observability sidecars, analyzer outputs, or
  billing reconciliation.

The promoted sidecar stage-timing instrumentation may be used only as
instrumentation. This packet does not claim speedup, reduced runtime, reduced
cost, completed optimization, throughput improvement, or any performance
result.

## L1a Command Manifest For Review

No command in this section is authorized. The manifest records the exact
condition-level intent and the current dry-plan/executable-plan selector
support status.

| condition_id | runner selector | grammar argument | output JSONL | support status |
|---|---|---|---|---|
| `grammar_off__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_off__p_off` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `grammar_off__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_on__p_off` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `grammar_off__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_off__p_on` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `grammar_off__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_on__p_on` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `template_upper_bound__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_off__p_off` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `template_upper_bound__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_on__p_off` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `template_upper_bound__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_off__p_on` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `template_upper_bound__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_on__p_on` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `task_agnostic__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_off__p_off` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `task_agnostic__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_on__p_off` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `task_agnostic__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_off__p_on` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |
| `task_agnostic__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_on__p_on` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl` | `DRY_PLAN_SELECTOR_PRESENT_NO_EXECUTION` |

Local dry-plan command preview:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan --grammar-mode-cell task_agnostic__c_on__p_off
```

Local executable-plan command preview:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan --grammar-mode-cell task_agnostic__c_on__p_off
```

The executable-plan preview emits one `executable_command` per selected cell.
Each emitted command records `--signed-l1a-authorization
SIGNED_L1A_PACKET_ID_REQUIRED`, the planned output JSONL path, the planned
observability event path, `--overwrite`, `path_collision_policy:
fail_if_any_target_path_exists`, and support status
`EXECUTABLE_SELECTOR_PRESENT_AUTHORIZATION_REQUIRED_NO_EXECUTION`. Active
grammar cells include the required `--grammar-variant`; `grammar_off` cells do
not include a grammar argument.

The six no-P cells are now selectable by the local dry-plan and executable-plan
manifests. They still must not be executed or materialized without a later
signed execution packet that approves exact runtime commands, target commit,
target paths, stop/spend limits, and output mutation.

## Exact Execution Command Surface

Current exact dry-plan verification command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
```

Current exact intended execution command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
```

This command is not approved. It is a source-backed command surface for future
signature review only. On this branch, `--condition grammar_mode_cp_12cell`
without local planning mode still refuses before tracking setup, runtime
generation, Modal, output writers, or observability writers. A future signature
must replace `SIGNED_L1A_PACKET_ID_REQUIRED`, name the exact target commit,
attach signable preflight and stop/spend limits, and explicitly approve output
mutation before this command can be used.

## Planned Namespaces

These are reserved planning namespaces only. This packet does not create,
overwrite, append, or validate them.

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/mlflow_index/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/
```

Any future execution packet must prove all target output and sidecar paths do
not exist before launch unless an explicit resume/append/archive policy is
approved.

## Pre-Approval Validation Required

A future signer must record exact pass/fail results for:

```text
git status --short --branch
git log --oneline --decorate -12
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report shared/tracking shared/analysis shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
positive-authorization scan over docs, audits, and .contracts, excluding generated preliminary-report previews
```

Additional required proof before approval:

- exact command/config is authorized for all 12 `grammar_mode`/C/P cells;
- an advisory preflight estimate is attached for the exact packet scope,
  including pricing re-verification status, stage-timing source
  (`measured` or `estimated`), execution-shape comparison, and stop/spend
  envelope;
- every planned row will carry `grammar_mode`;
- active grammar rows will carry grammar file/path and grammar hash or matching
  sidecar evidence where supported;
- analyzer grouping is by `grammar_mode`;
- C/P interactions are analyzed conditional on `grammar_mode`;
- derived active-grammar summaries are diagnostic only;
- MLflow indexing remains post-hoc and non-authoritative.

## Post-Run Validation Required After Any Future Approved Run

If a later signed execution packet authorizes L1a and artifacts are created, the
post-run audit must include these exact validation classes:

- row-count validation for 12 expected rows or explicit stop-condition
  disposition;
- schema validation;
- content-hash validation;
- observability event/summary/hash sidecar validation;
- grammar-mode/path/hash consistency validation;
- C/P eligibility validation;
- repair-history policy validation;
- analyzer grouping/quarantine validation;
- MLflow post-hoc importer dry-run or fixture validation;
- output/artifact registry and handoff updates.

Exact command bundle status:

```text
post_run_schema_validation_command: PROPOSED_NOT_SIGNED see exact command below
post_run_content_hash_validation_command: PROPOSED_NOT_SIGNED see exact command below
post_run_observability_sidecar_validation_command: PROPOSED_NOT_SIGNED see exact command below
post_run_grammar_mode_consistency_command: PROPOSED_NOT_SIGNED see exact command below
post_run_analyzer_report_command: PROPOSED_NOT_SIGNED see exact command below
post_run_billing_reconciliation_command: REQUIRED_BEFORE_SIGNATURE_BILLING_QUERY_TIME_WINDOW_AND_REDACTED_REPORT_PATH_MISSING
```

The analyzer/report command surface must be signed before use. The expected
shape is:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl --analysis-scope l1a_grammar_mode_cp_smoke --scale-tier smoke --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.md --bootstrap-samples 10000 --bootstrap-seed 13013
```

The exact 12 input paths must be expanded before signature rather than supplied
through an unchecked shell glob. The analyzer output and markdown report paths
are planned post-run artifacts only; this packet does not authorize writing
them. Runtime MLflow writes remain disabled unless a later signed packet
separately authorizes MLflow tracking.

Exact local validation command surfaces for a future approved run:

```text
.venv/bin/python -c 'import json; from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; rows=[]; [rows.extend(Cluster3EvalRow.from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line) for path in paths]; assert len(rows)==12, len(rows); print("schema_and_row_count_valid", len(rows))'
.venv/bin/python -c 'from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; from cluster3.results.logger import load_content_hash_sidecar, validate_content_hash_sidecar_for_rows; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; [validate_content_hash_sidecar_for_rows(tuple(Cluster3EvalRow.from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line), load_content_hash_sidecar(f"{path}.hashes.json")) for path in paths]; print("content_hash_sidecars_valid", len(paths))'
.venv/bin/python -c 'from pathlib import Path; from shared.observability.logger import file_sha256, load_observability_events; from shared.observability.schema import ObservabilityHashSidecar, ObservabilitySummary; base=Path("artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1"); ids=["grammar_off__c_off__p_off","grammar_off__c_on__p_off","grammar_off__c_off__p_on","grammar_off__c_on__p_on","template_upper_bound__c_off__p_off","template_upper_bound__c_on__p_off","template_upper_bound__c_off__p_on","template_upper_bound__c_on__p_on","task_agnostic__c_off__p_off","task_agnostic__c_on__p_off","task_agnostic__c_off__p_on","task_agnostic__c_on__p_on"]; [load_observability_events(base / f"{cid}.observability.jsonl") for cid in ids]; [ObservabilitySummary.model_validate_json((base / f"{cid}.observability.summary.json").read_text(encoding="utf-8")) for cid in ids]; sidecars=[ObservabilityHashSidecar.model_validate_json((base / f"{cid}.observability.jsonl.hashes.json").read_text(encoding="utf-8")) for cid in ids]; [(_ for _ in ()).throw(AssertionError(cid)) for cid, sc in zip(ids, sidecars) if sc.event_jsonl_sha256 != file_sha256(base / f"{cid}.observability.jsonl")]; print("observability_sidecars_valid", len(ids))'
.venv/bin/python -c 'from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; expected={"grammar_off":"grammar_off","template_upper_bound":"template_upper_bound","task_agnostic":"task_agnostic"}; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; rows=[Cluster3EvalRow.from_json(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line]; [(_ for _ in ()).throw(AssertionError(row.grammar_mode)) for row in rows if row.grammar_mode not in expected]; print("grammar_mode_consistency_valid", len(rows))'
```

## Go/No-Go Checklist

All items below must be true before any future signature:

- target branch is `codex-track-handoff-context`;
- target commit is the current approved commit and not stale;
- launch packet still selects the 12-cell `grammar_mode x C x P` design;
- dry-plan verification succeeds for all 12 cells;
- exact intended execution command or exact per-cell command bundle is supplied;
- all target JSONL, content-hash, observability, analyzer, report, billing, and
  optional MLflow paths are absent or have a signed archive/resume policy;
- advisory preflight estimate is attached for the exact L1a scope;
- official Modal pricing is re-verified on the approval date;
- numeric stop limits are supplied;
- numeric spend limits are supplied;
- billing reconciliation plan is approved;
- post-run validation command bundle is supplied;
- no-P cells are classified as controls and not as P evidence;
- MLflow remains post-hoc/non-authoritative unless separately approved;
- signature block below is completed by the user.

## Stop Conditions

Stop before or during any future approved L1a execution if:

- the launch packet no longer selects the 12-cell `grammar_mode x C x P` design;
- any target path already exists without an approved resume/append/archive
  policy;
- any packet uses unsupported grammar-mode names such as `primary_grammar` or
  `task_agnostic_grammar` instead of `template_upper_bound` and
  `task_agnostic`;
- the runner cannot label rows with `grammar_mode`;
- grammar file/path/hash evidence is missing for an active grammar mode;
- C fires outside F2;
- P fires outside `F1_COMPILE`;
- `F1_RUNTIME` is repaired;
- row schema validation fails;
- content-hash validation fails;
- observability required-mode validation fails;
- private-eval, raw prompt/source, token ID, billing secret, credential,
  performance, timing, speedup, profiler, or benchmark leakage appears.
- no advisory preflight estimate is attached to the signed packet, or the
  estimate exceeds the packet's approved wall-clock or spend limits.

## Explicit Approval

Ready for human signature review, but not signable until the required fields
below are replaced or explicitly approved by the user. No execution is
approved.

```text
AUTHORIZES_EXECUTION: NO
DRAFT_READY_FOR_USER_SIGNATURE: YES

signature_status: UNSIGNED
signer: REQUIRED_BEFORE_SIGNATURE
signed_at: REQUIRED_BEFORE_SIGNATURE
approval_scope: REQUIRED_BEFORE_SIGNATURE
exact_target_branch: codex-track-handoff-context
exact_target_commit: REQUIRED_AFTER_SELECTOR_SUPPORT_REVIEW_COMMIT_AND_PROMOTION
exact_intended_execution_command: PROPOSED_NOT_SIGNED .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
numeric_stop_limits: PROPOSED_NOT_SIGNED; signer must approve or replace
numeric_spend_limits: PROPOSED_NOT_SIGNED; signer must approve or replace
spend_cap: PROPOSED_NOT_SIGNED_USD_25_estimated_USD_50_reconciled
stop_limits: PROPOSED_NOT_SIGNED_rows_12_generation_attempts_72_correctness_calls_72_wall_clock_4h_stop_on_first_infrastructure_failure
modal_pricing_recheck_completed: REQUIRED_BEFORE_SIGNATURE_yes_no
preflight_estimate_attachment: NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER_ATTACHED; signer must attach signable estimate
advisory_estimate_attached: REQUIRED_BEFORE_SIGNATURE_yes_no
billing_reconciliation_plan: PLAN_ONLY_REQUIRES_SIGNED_TIME_WINDOW_AND_BILLING_QUERY_AUTHORIZATION
post_run_validation_bundle: PROPOSED_NOT_SIGNED_COMMANDS_LISTED_ABOVE
authorization_statement: REQUIRED_BEFORE_SIGNATURE_explicit_human_statement_required

NOT APPROVED. A future user approval must replace this unsigned block with a
signed L1a approval that names this packet, the exact target branch and commit,
the full 12-cell launcher support proof, the output and sidecar paths,
stop/spend limits, advisory preflight estimate, billing reconciliation plan,
and the post-run validation command bundle.
```
