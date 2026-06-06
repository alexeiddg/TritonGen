# Full Pipeline Grammar-Mode x C x P L1a n=1 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
packet_version: `0.5.0`
packet_type: completed review packet for possible future authorization; not an execution packet until signed
branch: `codex/l1a-final-approval-packet`
target_branch: `codex-track-handoff-context`
target_commit: `c256af5 Audit Modal preflight estimator promotion`
baseline_commit: `c256af5 Audit Modal preflight estimator promotion`
planning_baseline_commit: `c256af5 Audit Modal preflight estimator promotion`
code_support_commit: `c24fbaa Add local grammar-mode support for 12-cell L1a`
baseline_pin_commit: `d172e02 Pin L1a packet to grammar mode support baseline`
launcher_support_branch: `codex/grammar-mode-12cell-launcher-support`
launcher_support_commit: `e914557 Add dry-plan launcher support for 12-cell grammar mode matrix`
launcher_support_promotion_audit_commit: `76ede6a Audit 12-cell launcher support promotion`
launcher_support_status: `LOCAL_DRY_PLAN_SELECTOR_READY`
preflight_estimator_commit: `bd89e67 Add local Modal preflight cost time estimator`
preflight_estimator_promotion_audit_commit: `c256af5 Audit Modal preflight estimator promotion`
preflight_estimator_status: `LOCAL_ADVISORY_ESTIMATOR_REQUIRED_BEFORE_SIGNATURE`
superseded_baseline_commit: `0cc43c1 Audit full pipeline launch packet promotion`
launch_packet: `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
created_at: 2026-06-05
baseline_pinned_at: 2026-06-05
packet_completed_at: 2026-06-06
status: `DRAFT_READY_FOR_USER_SIGNATURE`
DRAFT_READY_FOR_USER_SIGNATURE: YES
code_support_status: `LOCAL_REPRESENTABILITY_AND_DRY_PLAN_SELECTOR_READY`
execution_readiness_status: `BLOCKED_PENDING_SIGNATURE_STOP_SPEND_AND_EXECUTION_PACKET`
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

The active planning baseline is the promoted handoff trunk commit `c256af5`.
That baseline includes local grammar-mode support (`c24fbaa`), 12-cell
dry-plan launcher support (`e914557`), sidecar-only stage timing
instrumentation, and the local advisory Modal preflight estimator (`bd89e67`).
The older `0cc43c1` and `d172e02` baselines are historical context only and
are not sufficient as the current L1a target because they predate later
launcher and estimator support.

Execution remains blocked even after local launcher support because this packet
is unsigned and still lacks approved numeric stop/spend limits and a signed
execution command bundle. The current Cluster 3 CLI now exposes a local dry-plan
selector, `--condition grammar_mode_cp_12cell --dry-plan`, that can select all
12 `grammar_mode x C x P` cells, including the six no-P control cells. That
selector emits deterministic plan metadata only; it does not invoke Modal,
generation, correctness evaluation, output writing, artifact writing, or MLflow
tracking.

Any future signed execution packet must include an advisory preflight estimate
for the exact target scope before launch. The local utility
`cluster3/planning/modal_preflight_estimator.py` can estimate L1a/L1b/L2 row
counts, execution-shape envelopes, and larger-GPU breakeven requirements from
explicit user-supplied pricing and timing inputs. That estimate remains
planning-only: it does not authorize execution, does not replace billing
reconciliation, and does not constitute experimental evidence.

Pricing must be re-verified against official Modal documentation before any
future signature. Exact numeric stop limits and exact numeric spend limits are
also `REQUIRED_BEFORE_SIGNATURE`.

## Final Approval Surface Summary

```text
target_branch: codex-track-handoff-context
target_commit: c256af5 Audit Modal preflight estimator promotion
packet_completion_branch: codex/l1a-final-approval-packet
experiment_name: full_pipeline_grammar_mode_cp_factorial_v1
level: L1a
scale_tier: smoke/dev
n_per_cell: 1
cell_count: 12
design: grammar_mode x C x P
dry_plan_selector: --condition grammar_mode_cp_12cell --dry-plan
dry_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
exact_intended_execution_command: REQUIRED_BEFORE_SIGNATURE_current_selector_is_dry_plan_only
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

The exact intended execution command is still `REQUIRED_BEFORE_SIGNATURE`
because the current `grammar_mode_cp_12cell` selector is explicitly
dry-plan-only in `cluster3/experiments/run_cluster3_modal.py`. A future signer
must either approve a code-supported executable 12-cell launcher command or
provide an exact per-cell command bundle that maps each `grammar_mode`/C/P cell
to supported runner conditions without changing row semantics. This packet does
not provide that authorization and must not be used as a launch command.

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
- `cluster3/experiments/run_cluster3_modal.py` exposes the dry-plan-only
  selector `grammar_mode_cp_12cell`, which expands to all 12 cells with
  deterministic output paths, content-hash sidecar paths, observability sidecar
  paths, grammar path/hash/scope metadata, repair-history policy, and
  no-overwrite policy markers.
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
target_commit: c256af5 Audit Modal preflight estimator promotion
packet_completion_branch: codex/l1a-final-approval-packet
command: REQUIRED_BEFORE_SIGNATURE_current_12cell_selector_is_dry_plan_only
command_manifest_status: LOCAL_DRY_PLAN_SELECTOR_PRESENT_EXECUTION_COMMAND_REQUIRED_BEFORE_SIGNATURE
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
observability_run_id: REQUIRED_BEFORE_SIGNATURE_exact_run_id
mlflow_disposition: post_hoc_non_authoritative; runtime MLflow writes remain unauthorized; grammar-mode indexing patch remains deferred
max_rows: 12
max_generation_attempts: REQUIRED_BEFORE_SIGNATURE_exact_total_attempt_ceiling
max_repair_attempts_per_row: P=5 when P is enabled; C=5 when C is enabled; 0 otherwise
max_wall_clock: REQUIRED_BEFORE_SIGNATURE_numeric_limit
max_estimated_cost: REQUIRED_BEFORE_SIGNATURE_numeric_spend_limit
max_reconciled_billing_cost: REQUIRED_BEFORE_SIGNATURE_numeric_spend_limit
preflight_estimate: REQUIRED_BEFORE_SIGNATURE_advisory_only_pricing_must_be_reverified
stop_on_first_infrastructure_failure: yes
overwrite_policy: fail_if_any_target_path_exists
retry_policy: no_retry_no_resume_unless_explicitly_approved_in_signed_packet
resume_policy: no_resume_unless_explicitly_approved
billing_reconciliation_requirement: approved_post_run_modal_billing_reconciliation_required; estimates_do_not_replace_billing
modal_app_name: REQUIRED_BEFORE_SIGNATURE
modal_image_digest: REQUIRED_BEFORE_SIGNATURE
post_run_validation_commands: required list in Post-Run Validation and Analyzer Command Surface sections
```

## Preflight Estimate And Limit Requirements

No advisory preflight estimate is attached to this unsigned packet.

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
condition-level intent and the current dry-plan selector support status.

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

The six no-P cells are now selectable by the local dry-plan manifest. They still
must not be executed or materialized without a later signed execution packet that
approves exact runtime commands, target commit, target paths, stop/spend limits,
and output mutation.

## Exact Execution Command Surface

Current exact dry-plan verification command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
```

Current exact intended execution command:

```text
REQUIRED_BEFORE_SIGNATURE
```

Reason: `grammar_mode_cp_12cell` is dry-plan-only in the current local runner.
The current code rejects `--condition grammar_mode_cp_12cell` unless
`--dry-plan` is also present, and `--grammar-mode-cell` is supported only with
dry-plan. A future signature must therefore name one of these exact command
surfaces before execution:

- a code-supported executable 12-cell launcher command on the target commit; or
- an explicit per-cell Modal command bundle for all 12 condition IDs, with
  target output, content-hash sidecar, observability event/summary/hash sidecar,
  grammar-mode mapping, repair-history policy, stop/spend limits, and
  fail-if-existing checks for each cell.

Do not infer the executable command from the dry-plan selector.

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
post_run_schema_validation_command: REQUIRED_BEFORE_SIGNATURE
post_run_content_hash_validation_command: REQUIRED_BEFORE_SIGNATURE
post_run_observability_sidecar_validation_command: REQUIRED_BEFORE_SIGNATURE
post_run_grammar_mode_consistency_command: REQUIRED_BEFORE_SIGNATURE
post_run_billing_reconciliation_command: REQUIRED_BEFORE_SIGNATURE
```

The analyzer/report command surface must be signed before use. The expected
shape is:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs <12 explicit L1a JSONL paths> --analysis-scope l1a_grammar_mode_cp_smoke --scale-tier smoke --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.md --bootstrap-samples 10000 --bootstrap-seed 13013
```

The exact 12 input paths must be expanded before signature rather than supplied
through an unchecked shell glob. The analyzer output and markdown report paths
are planned post-run artifacts only; this packet does not authorize writing
them. Runtime MLflow writes remain disabled unless a later signed packet
separately authorizes MLflow tracking.

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

Ready for user signature but unsigned. No execution is approved.

```text
AUTHORIZES_EXECUTION: NO
DRAFT_READY_FOR_USER_SIGNATURE: YES

signature_status: UNSIGNED
signer: REQUIRED_BEFORE_SIGNATURE
signed_at: REQUIRED_BEFORE_SIGNATURE
approval_scope: REQUIRED_BEFORE_SIGNATURE
exact_target_branch: codex-track-handoff-context
exact_target_commit: c256af5 Audit Modal preflight estimator promotion
exact_intended_execution_command: REQUIRED_BEFORE_SIGNATURE
numeric_stop_limits: REQUIRED_BEFORE_SIGNATURE
numeric_spend_limits: REQUIRED_BEFORE_SIGNATURE
preflight_estimate_attachment: REQUIRED_BEFORE_SIGNATURE
billing_reconciliation_plan: REQUIRED_BEFORE_SIGNATURE
post_run_validation_bundle: REQUIRED_BEFORE_SIGNATURE

NOT APPROVED. A future user approval must replace this unsigned block with a
signed L1a approval that names this packet, the exact target branch and commit,
the full 12-cell launcher support proof, the output and sidecar paths,
stop/spend limits, advisory preflight estimate, billing reconciliation plan,
and the post-run validation command bundle.
```
