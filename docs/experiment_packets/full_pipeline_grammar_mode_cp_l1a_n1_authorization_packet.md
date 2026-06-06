# Full Pipeline Grammar-Mode x C x P L1a n=1 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.0-final-l1a-n1-execution-authorization-no-digest-fallback`
packet_type: final L1a n=1 execution authorization packet; no-digest fallback accepted for L1a only
branch: `codex/l1a-final-execution-authorization`
target_branch: `codex-track-handoff-context`
execution_code_target_commit: `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`
approval_record_commit: `TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT`
target_commit_policy: `execution_code_target_commit_names_latest_promoted_code_bearing_baseline; approval_record_commit_names_docs_only_signed_packet_commit_after_commit`
baseline_commit: `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`
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
preflight_estimator_status: `SIGNABLE_ADVISORY_ATTACHED_PRICING_VERIFIED_TIMING_ESTIMATED_NOT_EXECUTION_EVIDENCE`
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
executable_selector_support_commit: `e9f180a Add executable planning for 12-cell L1a selector`
executable_selector_support_promotion_audit_commit: `c05e111 Audit L1a executable selector support promotion`
final_signature_packet_branch: `codex/l1a-final-signature-packet`
final_signature_packet_prepared_at: 2026-06-06
final_signature_packet_promotion_audit_commit: `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`
human_signature_readiness_review_commit: `3318002 Review L1a human signature readiness`
human_signature_readiness_review_status: `REVIEW_ONLY_INPUT_NOT_EXECUTION_TARGET`
expedited_signature_preflight_branch: `codex/l1a-expedited-signature-and-preflight`
expedited_signature_preflight_at: 2026-06-06
expedited_signature_preflight_commit: `d2ab0a9 Prepare expedited L1a signature and preflight evidence`
expedited_signature_preflight_promotion_audit_commit: `8da7683 Audit L1a expedited signature preflight promotion`
final_execution_authorization_branch: `codex/l1a-final-execution-authorization`
final_execution_authorization_at: 2026-06-06
final_signature_packet_status: `SIGNED_FOR_L1A_N1_ONLY_NO_DIGEST_FALLBACK_ACCEPTED`
status: `L1A_FINAL_EXECUTION_AUTHORIZATION_READY`
DRAFT_READY_FOR_USER_SIGNATURE: SIGNED_FOR_L1A_N1_ONLY
code_support_status: `LOCAL_REPRESENTABILITY_DRY_PLAN_AND_EXECUTABLE_SELECTOR_PLAN_READY`
execution_readiness_status: `AUTHORIZED_L1A_N1_ONLY_PENDING_USER_LAUNCH`
AUTHORIZES_EXECUTION: YES_L1A_N1_ONLY

Execution authorization flags:

```text
MODAL_AUTHORIZED: YES_L1A_N1_ONLY
GPU_AUTHORIZED: YES_L1A_N1_ONLY
GENERATION_AUTHORIZED: YES_L1A_N1_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L1A_N1_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L1A_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L1A_NAMESPACES_ONLY
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO_RUNTIME_MLFLOW_NOT_REQUIRED_BY_LAUNCHER
BILLING_QUERY_AUTHORIZED: YES_L1A_RECONCILIATION_ONLY
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
PAPER_SCALE_AUTHORIZED: NO
L1B_AUTHORIZED: NO
L2_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
BENCHMARK_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
NETWORK_AUTHORIZED: YES_L1A_MODAL_RUN_AND_L1A_BILLING_RECONCILIATION_ONLY
CREDENTIAL_USE_AUTHORIZED: YES_EXISTING_MODAL_AUTH_CONTEXT_L1A_N1_ONLY
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

This packet records the user's final L1a n=1 authorization and explicitly
accepts the no-digest fallback provenance policy below. It authorizes exactly
one 12-cell `grammar_mode x C x P` L1a n=1 run and the listed post-run
validation/billing reconciliation surfaces. It does not authorize L1b, L2,
paper-scale runs, retry, resume, benchmarks, profilers, dependency changes,
lockfile changes, runtime MLflow tracking, or claims about performance,
speedup, cost reduction, throughput improvement, or paper-scale evidence.

The active execution-code target is the latest promoted handoff trunk baseline
`31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet
promotion`. This separates the code target from the future approval record:
the eventual signed packet commit may be newer and docs-only, and the packet
does not need to target itself. The target baseline includes the exact promoted
selector-support commit `e9f180a Add executable planning for 12-cell L1a
selector`, the selector-support promotion audit `c05e111`, and the final
signature packet promotion audit `31a097e`. Earlier signature review targets
such as `59fa0d6`, `e96f70a`, `0cc43c1`, `d172e02`, and `c05e111` are
historical context only unless explicitly named as selector support evidence.

Execution authorization is now scoped to L1a n=1 only. The remote image digest
blocker is waived only by the signed alternative provenance policy in this
packet. The current Cluster 3 CLI exposes local dry-plan and executable-plan
selector surfaces for
`--condition grammar_mode_cp_12cell`. Both can select all 12
`grammar_mode x C x P` cells, including the six no-P control cells. The
executable-plan surface constructs exact per-cell future command strings with
target paths and a signed-authorization token. The planning surface itself does
not invoke Modal, generation, correctness evaluation, output writing, artifact
writing, tracking, or MLflow.

This packet now includes a pricing-verified advisory preflight estimate for
the exact target scope. The local utility
`cluster3/planning/modal_preflight_estimator.py` can estimate row counts,
execution-shape envelopes, and larger-GPU breakeven requirements from explicit
user-supplied pricing and timing inputs, but this packet authorizes only L1a
n=1 and does not authorize L1b or L2. That estimate remains
planning-only: it does not authorize execution, does not replace billing
reconciliation, and does not constitute experimental evidence.

Modal pricing was re-verified against the official Modal pricing page on
2026-06-06 for this expedited preflight. The numeric stop/spend limits below
are signed for L1a n=1 only.

## Final Approval Surface Summary

```text
target_branch: codex-track-handoff-context
execution_code_target_commit: 31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion
approval_record_commit: TO_BE_FILLED_AFTER_COMMIT
exact_promoted_selector_commit: e9f180a Add executable planning for 12-cell L1a selector
exact_selector_support_promotion_audit_commit: c05e111 Audit L1a executable selector support promotion
final_signature_packet_promotion_audit_commit: 31a097e Audit L1a final signature packet promotion
packet_completion_branch: codex/l1a-final-execution-authorization
experiment_name: full_pipeline_grammar_mode_cp_factorial_v1
level: L1a
scale_tier: smoke/dev
n_per_cell: 1
cell_count: 12
design: grammar_mode x C x P
dry_plan_selector: --condition grammar_mode_cp_12cell --dry-plan
dry_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
executable_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
exact_intended_execution_command: TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
output_root: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
observability_artifact_root: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
jsonl_path_pattern: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl
content_hash_sidecar_path_pattern: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl.hashes.json
observability_event_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl
observability_summary_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.summary.json
observability_hash_sidecar_path_pattern: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl.hashes.json
AUTHORIZES_EXECUTION: YES_L1A_N1_ONLY
DRAFT_READY_FOR_USER_SIGNATURE: SIGNED_FOR_L1A_N1_ONLY
```

The exact intended execution command surface is now source-backed locally by
`cluster3/experiments/run_cluster3_modal.py` and
`cluster3/planning/grammar_mode_matrix.py`. The signed-authorization token for
the approved L1a n=1 run is
`FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`. This packet
provides execution authorization only for that scope and token.

## Signed No-Digest Fallback Provenance Policy

remote_image_digest_status:
`WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY`

Reason:

Modal 1.4.2 did not expose a stable Docker digest, `sha256:` digest, or stable
`im-...` image id through no-generation inspection. Direct image hydration was
blocked by the Modal client, and ephemeral app registration exposed
app/function/class handles but not image digest metadata. The signer accepts
this fallback policy for L1a n=1 only.

Replacement evidence:

```text
execution_code_target_commit: 31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion
approval_record_commit: TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT
preflight_evidence_commit: d2ab0a9 Prepare expedited L1a signature and preflight evidence
preflight_promotion_audit_commit: 8da7683 Audit L1a expedited signature preflight promotion
modal_app_name: tritongen-gpu-harness
modal_client_version: 1.4.2
modal_preflight_app_id: ap-oAbxWPcEyrDGyEfaBRWXqk
modal_preflight_class_id: cs-OBgdIK0FxYbUuKFMpHNjFQ
modal_preflight_generation_class_function_id: fu-Y1J87H1D2noHuthWzEPYB1
modal_preflight_correctness_function_id: fu-6W0frnq4Q6GvPN2Vwyq64z
modal_digest_status: BLOCKED_REMOTE_IMAGE_DIGEST_NOT_EXPOSED_WITHOUT_BROADER_MODAL_APP_PATH
pricing_source: official Modal pricing page https://modal.com/pricing retrieved 2026-06-06
```

Image/runtime source files and hashes:

```text
shared/modal_harness/app.py sha256=bcf0a38f81f516187be3d7d1fb41d513f253eff16b3e480295ccd5f7ad54061c
shared/modal_harness/images.py sha256=5acc6cff0991542dcba118081d499a6a51c03264d11c63d89fcbffadb95ad61c
cluster2/modal/generation.py sha256=2b811d2c34de00f89d9b0c704f539a7093f5740e5e672d9c7b4e08c3d9c49cb9
cluster2/modal/correctness.py sha256=f3b6dac0f413395c71ae3af240fd73d403c602ac00b84bf06e1aa440f1154260
cluster3/experiments/run_cluster3_modal.py sha256=ed3db24711ed2750b26765a668d871e77fa0c09d2ec4a3ed6f0581a5ff0f2631
cluster3/planning/grammar_mode_matrix.py sha256=33f6b1c5cba6abca430da97fb348244e27b0da9b9d4160af71f8b79d415de139
```

Dependency and lockfile hashes:

```text
pyproject.toml sha256=3ed8159e4b71e05172b8d0716ea5d9f3057a0cd8989425d60389a60d0623d908
requirements.txt sha256=1671d73f1d747cc64fae787bdf657ed20f14974292d8c71dcde2c88f20c30df3
requirements-dev.txt absent
uv.lock absent
poetry.lock absent
Pipfile.lock absent
```

Post-run requirement:

Capture all available Modal run, image, app, class, function, container,
region, GPU, timing, attempt-status, preemption-status, and billing metadata into the L1a
observability/provenance sidecar and/or the signed L1a audit artifacts without
changing JSONL scientific rows.

Scope:

This fallback policy is valid only for one L1a n=1 12-cell smoke/dev run using
the exact execution-code target and command bundle in this packet.

Not valid for:

- L1b;
- L2;
- paper-scale runs;
- reruns;
- retries;
- resume;
- performance claims;
- speedup claims;
- cost-reduction claims;
- any future packet that changes runtime code, dependencies, image sources,
  scientific semantics, sampling/model settings, repair policy, grammar
  semantics, or pass/fail definitions.

## Signature Readiness Gap Closure Addendum

This addendum records the now-signed L1a n=1 approval surface. The approval
record commit remains `TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT` until this
docs-only packet commit is created.

Resolved or narrowed fields:

| Field | Status | Source-backed value or classification |
|---|---|---|
| execution code target commit | `SIGNED_L1A_N1_ONLY` | `codex-track-handoff-context` at `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`, which contains selector support commit `e9f180a`, selector-support promotion audit `c05e111`, final signature packet commit `316723a`, and final signature packet promotion audit `31a097e` |
| approval record commit | `TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT` | The signed packet commit is newer and docs-only; it is not the execution-code target |
| executable command | `SIGNED_L1A_N1_ONLY` | selector-level command: `TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite`; per-cell commands are emitted by `--execution-plan` |
| observability run id convention | `SIGNED_L1A_N1_ONLY` | global run id convention: `full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__target_31a097e__signed_<YYYYMMDDTHHMMSSZ>`; per-cell join key convention: `<run_id>__<condition_id>` |
| current dry-plan observability join key | `RESOLVED_PLANNING_METADATA` | `cluster3/planning/grammar_mode_matrix.py` emits `full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__<condition_id>` join keys |
| Modal app name | `RESOLVED_REPO_LOCAL` | `tritongen-gpu-harness` from `shared/modal_harness/app.py` |
| Modal image definitions | `RESOLVED_REPO_LOCAL_SOURCE_ONLY` | `shared/modal_harness/images.py` defines `llm_generation_image` and `triton_compile_image`; L1a uses `cluster2.modal.generation.c2_generation_image` and `cluster2.modal.correctness.c2_correctness_image` through the shared `tritongen-gpu-harness` app |
| Modal image digest | `WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY` | Modal 1.4.2 refused direct image hydration; ephemeral app registration hydrated function/class handles with zero tasks and no function invocations but did not expose a Docker digest or stable image id in CLI-visible metadata |
| advisory preflight estimate | `SIGNED_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED` | local estimator run with official Modal pricing and conservative estimated timing inputs; billing reconciliation remains authoritative |
| numeric stop/spend limits | `SIGNED_L1A_N1_ONLY` | limits are listed below and accepted for one L1a n=1 run |
| billing reconciliation plan | `SIGNED_L1A_RECONCILIATION_ONLY_AFTER_APPROVED_RUN` | post-run billing is authoritative for actual spend; billing query authorization is scoped to L1a reconciliation after the signed run window exists |
| validation bundle | `SIGNED_LISTED_COMMANDS_ONLY_AFTER_L1A_ARTIFACTS_EXIST` | exact local command surfaces are listed below; analyzer/report writes are scoped to listed L1a artifacts only |

Signed advisory estimate:

```text
estimate_status: SIGNABLE_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED
estimator: cluster3/planning/modal_preflight_estimator.py
pricing_source: official Modal pricing page https://modal.com/pricing retrieved 2026-06-06
official_rates_used: L4 GPU $0.000222/sec; CPU $0.0000131/core/sec; memory $0.00000222/GiB/sec
conservative_unit_rate: $0.00039784/sec, computed as L4 + 8 CPU cores + 32 GiB memory, the larger of the repo generation and correctness surfaces
inputs: cell_count=12; n_per_cell=1; total_generation_attempt_upper_bound=72; correctness_call_upper_bound=72; gpu_label=L4_PLUS_CPU8_MEM32GI_MAX_UNIT_RATE_OFFICIAL_MODAL_2026_06_06; price_per_gpu_second=0.00039784; cold_start_seconds=120.0; model_load_seconds=180.0; generation_seconds_per_row=360.0; compile_correctness_seconds_per_row=540.0; repair_overhead_seconds_per_activated_repair=60.0; expected_p_activation_rate=1.0; expected_c_activation_rate=1.0; fanout_limit=4; safety_multiplier=1.5; fixed_overhead_seconds=5.0; pricing_verified=true; stage_timing_source=estimated
total_planned_rows: 12
recommended_shape_name: bounded_fanout_across_cells_seeds
estimated_parallel_wall_clock_seconds: 5047.5
estimated_serial_wall_clock_seconds: 20167.5
estimated_gpu_seconds: 20167.5
estimated_cost: 8.0234382
execution_shape_comparison_costs: one_remote_invocation_per_row=$9.4556622; one_remote_invocation_per_cell=$9.4556622; one_remote_invocation_per_grammar_mode_shard=$7.8444102; single_full_plan_invocation=$7.4863542; bounded_fanout_across_cells_seeds=$8.0234382
wall_clock_cap_recommendation: 4 hours
estimated_cost_cap_recommendation: USD 25
reconciled_billing_cap_recommendation: USD 50
warning_flags: advisory_only_not_experimental_evidence, stage_timing_inputs_estimated_not_measured
signability_status: SIGNED_ADVISORY for L1a n=1; actual billing reconciliation remains authoritative
```

Signed stop/spend limits:

```text
max_rows: 12
max_generation_attempts: 72_total_initial_plus_C_and_P_repair_attempt_ceiling
max_repair_attempts_per_row: P_5_when_enabled_C_5_when_enabled_0_otherwise
max_correctness_calls: 72_total_attempt_ceiling
max_wall_clock: 4_hours
max_estimated_cost: USD_25_pricing_verified_2026_06_06
max_reconciled_billing_cost: USD_50_billing_reconciliation_authoritative
max_modal_invocations: execution_shape_planning_bound_12_cell_selector
stop_on_first_infrastructure_failure: yes
retry_policy: no_retry_no_resume
resume_policy: no_resume
fail_if_any_target_path_exists: true
abort_if_unexpected_output_namespace_is_requested: true
abort_if_row_count_exceeds_12: true
abort_if_command_attempts_L1b_L2_or_paper_scale: true
```

Billing reconciliation plan:

```text
billing_reconciliation_status: SIGNED_L1A_RECONCILIATION_ONLY_AFTER_APPROVED_RUN
authoritative_actual_spend_source: post-run reconciled Modal billing artifact
required_after_approved_run: signed start/end UTC window; signed experiment_id; signed run_id; redacted billing report path; redacted report sha256; reconciliation dry-run result; reconciliation write authorization if any sidecar mutation is requested
future_collection_command_status: AUTHORIZED_ONLY_AFTER_SIGNED_L1A_RUN_WINDOW_AND_REDACTED_OUTPUT_PATH_EXIST
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
approval line is signed below for the exact runtime command/config, output
paths, stop/spend limits, and preflight results in this packet.

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

## Signed Runtime Fields For L1a n=1

```text
approval_source: user_message_and_current_prompt
approval_timestamp: 2026-06-06
target_branch: codex-track-handoff-context
execution_code_target_commit: 31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion
approval_record_commit: TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT
exact_promoted_selector_commit: e9f180a Add executable planning for 12-cell L1a selector
exact_selector_support_promotion_audit_commit: c05e111 Audit L1a executable selector support promotion
final_signature_packet_promotion_audit_commit: 31a097e Audit L1a final signature packet promotion
packet_completion_branch: codex/l1a-final-execution-authorization
command: TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
command_manifest_status: LOCAL_EXECUTABLE_SELECTOR_COMMAND_BUNDLE_PRESENT_SIGNED_L1A_N1_ONLY
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
observability_run_id: full_pipeline_grammar_mode_cp_factorial_v1_l1a_n1__target_31a097e__signed_<YYYYMMDDTHHMMSSZ>
observability_join_key_convention: <observability_run_id>__<condition_id>
mlflow_disposition: runtime_mlflow_tracking_disabled_with_TRITONGEN_MLFLOW_0; post_hoc_non_authoritative_indexing_deferred_until_after_artifacts_exist_and_separate_command_is_signed
max_rows: 12
max_generation_attempts: 72_total_initial_plus_C_and_P_repair_attempt_ceiling
max_repair_attempts_per_row: P_5_when_enabled_C_5_when_enabled_0_otherwise
max_correctness_calls: 72_total_attempt_ceiling
max_wall_clock: 4_hours
max_estimated_cost: USD_25_pricing_verified_2026_06_06
max_reconciled_billing_cost: USD_50_billing_reconciliation_authoritative
preflight_estimate: SIGNED_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED
stop_on_first_infrastructure_failure: yes
overwrite_policy: fail_if_any_target_path_exists
retry_policy: no_retry
resume_policy: no_resume
billing_reconciliation_requirement: signed_post_run_modal_billing_reconciliation_required; estimates_do_not_replace_billing
modal_app_name: tritongen-gpu-harness
modal_image_sources: c2_generation_image from cluster2/modal/generation.py using shared llm_generation_image; c2_correctness_image from cluster2/modal/correctness.py using shared triton_compile_image
remote_image_digest_status: WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY
modal_image_digest: WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY
post_run_validation_commands: SIGNED_LISTED_COMMANDS_ONLY in Post-Run Validation and Analyzer Command Surface sections
```

## Preflight Estimate And Limit Requirements

This signed packet attaches an advisory preflight estimate with official Modal
pricing verified on 2026-06-06. It uses conservative estimated timing inputs
rather than measured L1a timing inputs. The signer accepts those inputs for one
L1a n=1 smoke/dev run only. The estimate is planning evidence only; actual
post-run billing reconciliation remains authoritative.

Signed policy:

- the remote Modal image digest is waived by the signed alternative provenance
  policy above for L1a n=1 only;
- conservative estimated timing inputs are accepted for L1a n=1 only;
- the final `approval_record_commit` must be recorded after this docs-only
  commit exists;
- the exact signed run id and signed billing time-window must be recorded in
  the post-run audit;
- estimates are not experimental evidence and do not replace JSONL rows,
  content-hash sidecars, observability sidecars, analyzer outputs, or billing
  reconciliation.

The promoted sidecar stage-timing instrumentation may be used only as
instrumentation. This packet does not claim speedup, reduced runtime, reduced
cost, completed optimization, throughput improvement, or any performance
result.

## L1a Command Manifest

The commands in this section are authorized only within the signed L1a n=1
scope. The manifest records the exact condition-level intent and the current
dry-plan/executable-plan selector support status.

| condition_id | runner selector | grammar argument | output JSONL | support status |
|---|---|---|---|---|
| `grammar_off__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_off__p_off` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `grammar_off__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_on__p_off` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `grammar_off__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_off__p_on` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |
| `grammar_off__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell grammar_off__c_on__p_on` | none | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |
| `template_upper_bound__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_off__p_off` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `template_upper_bound__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_on__p_off` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `template_upper_bound__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_off__p_on` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |
| `template_upper_bound__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell template_upper_bound__c_on__p_on` | `--grammar-variant template_upper_bound` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |
| `task_agnostic__c_off__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_off__p_off` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `task_agnostic__c_on__p_off` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_on__p_off` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl` | `SIGNED_L1A_N1_CONTROL_CELL` |
| `task_agnostic__c_off__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_off__p_on` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |
| `task_agnostic__c_on__p_on` | `--condition grammar_mode_cp_12cell --dry-plan --grammar-mode-cell task_agnostic__c_on__p_on` | `--grammar-variant task_agnostic` | `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl` | `SIGNED_L1A_N1_CELL` |

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
FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`, the planned output JSONL path, the planned
observability event path, `--overwrite`, `path_collision_policy:
fail_if_any_target_path_exists`, and support status
`SIGNED_L1A_N1_ONLY`. Active
grammar cells include the required `--grammar-variant`; `grammar_off` cells do
not include a grammar argument.

The six no-P cells are now selectable by the local dry-plan and executable-plan
manifests. They are signed as L1a n=1 controls only and must not be used as P
evidence.

## Exact Execution Command Surface

Current exact dry-plan verification command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
```

Current exact intended execution command:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

Current source-backed per-cell command bundle surface:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
```

That local planning command emits the exact future per-cell command strings for
all 12 cells, including `--output`, `--observability-mode best_effort`,
`--observability-experiment-id`, `--observability-run-id`,
`--observability-output`, `--grammar-mode-cell`, any required
`--grammar-variant`, `--signed-l1a-authorization
FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`, and
`--overwrite`. The execution-plan verification command is local-only and may be
used to confirm command expansion before launch.

The intended execution command is approved only for the 12-cell L1a n=1 scope,
with `TRITONGEN_MLFLOW=0`, the exact target commit, the signed preflight
estimate, the signed stop/spend limits, fail-if-existing output policy, and the
output/artifact namespaces listed below.

## Authorized L1a Namespaces

These namespaces are authorized for the single signed L1a n=1 run and listed
post-run validation commands only. `mlruns/` mutation and runtime MLflow
tracking remain unauthorized.

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/
```

Before launch, all target output and sidecar paths must be absent. If any
target path exists, the run must stop; retry, resume, append, and archive
policies are not authorized by this packet.

## Pre-Execution Validation Required

The operator must record exact pass/fail results before launch for:

```text
git status --short --branch
git log --oneline --decorate -12
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report shared/tracking shared/analysis shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
positive-authorization scan over docs, audits, and .contracts, excluding generated preliminary-report previews
```

Additional required proof before launch:

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
- MLflow indexing remains post-hoc and non-authoritative, and runtime MLflow is
  disabled for the execution command.

## Post-Run Validation Required After Approved L1a Run

After the signed L1a run creates artifacts, the post-run audit must include
these exact validation classes:

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
post_run_schema_validation_command: SIGNED_LISTED_COMMAND_ONLY see exact command below
post_run_content_hash_validation_command: SIGNED_LISTED_COMMAND_ONLY see exact command below
post_run_observability_sidecar_validation_command: SIGNED_LISTED_COMMAND_ONLY see exact command below
post_run_grammar_mode_consistency_command: SIGNED_LISTED_COMMAND_ONLY see exact command below
post_run_analyzer_report_command: SIGNED_LISTED_COMMAND_ONLY see exact command below
post_run_billing_reconciliation_command: SIGNED_AFTER_L1A_RUN_WINDOW_AND_REDACTED_REPORT_PATH
```

The analyzer/report command surface is signed for the exact L1a n=1 artifact
paths only. The expected shape is:

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl --analysis-scope l1a_grammar_mode_cp_smoke --scale-tier smoke --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1_factorial.md --bootstrap-samples 10000 --bootstrap-seed 13013
```

The exact 12 input paths are expanded rather than supplied through an unchecked
shell glob. The analyzer output and markdown report paths are authorized
post-run L1a artifacts only. Runtime MLflow writes remain disabled.

Exact local validation command surfaces for the approved L1a run:

```text
.venv/bin/python -c 'import json; from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; rows=[]; [rows.extend(Cluster3EvalRow.from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line) for path in paths]; assert len(rows)==12, len(rows); print("schema_and_row_count_valid", len(rows))'
.venv/bin/python -c 'from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; from cluster3.results.logger import load_content_hash_sidecar, validate_content_hash_sidecar_for_rows; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; [validate_content_hash_sidecar_for_rows(tuple(Cluster3EvalRow.from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line), load_content_hash_sidecar(f"{path}.hashes.json")) for path in paths]; print("content_hash_sidecars_valid", len(paths))'
.venv/bin/python -c 'from pathlib import Path; from shared.observability.logger import file_sha256, load_observability_events; from shared.observability.schema import ObservabilityHashSidecar, ObservabilitySummary; base=Path("artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1"); ids=["grammar_off__c_off__p_off","grammar_off__c_on__p_off","grammar_off__c_off__p_on","grammar_off__c_on__p_on","template_upper_bound__c_off__p_off","template_upper_bound__c_on__p_off","template_upper_bound__c_off__p_on","template_upper_bound__c_on__p_on","task_agnostic__c_off__p_off","task_agnostic__c_on__p_off","task_agnostic__c_off__p_on","task_agnostic__c_on__p_on"]; [load_observability_events(base / f"{cid}.observability.jsonl") for cid in ids]; [ObservabilitySummary.model_validate_json((base / f"{cid}.observability.summary.json").read_text(encoding="utf-8")) for cid in ids]; sidecars=[ObservabilityHashSidecar.model_validate_json((base / f"{cid}.observability.jsonl.hashes.json").read_text(encoding="utf-8")) for cid in ids]; [(_ for _ in ()).throw(AssertionError(cid)) for cid, sc in zip(ids, sidecars) if sc.event_jsonl_sha256 != file_sha256(base / f"{cid}.observability.jsonl")]; print("observability_sidecars_valid", len(ids))'
.venv/bin/python -c 'from pathlib import Path; from cluster3.results.dataclass import Cluster3EvalRow; expected={"grammar_off":"grammar_off","template_upper_bound":"template_upper_bound","task_agnostic":"task_agnostic"}; paths=[Path(p) for p in ["outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/template_upper_bound__c_on__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_off.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_off__p_on.jsonl","outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic__c_on__p_on.jsonl"]]; rows=[Cluster3EvalRow.from_json(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line]; [(_ for _ in ()).throw(AssertionError(row.grammar_mode)) for row in rows if row.grammar_mode not in expected]; print("grammar_mode_consistency_valid", len(rows))'
```

## Go/No-Go Checklist

All items below must be true before launch:

- target branch is `codex-track-handoff-context`;
- execution code target commit is
  `31a097e3231e5b73a1402a26d18c660ba2f53d84`;
- approval record commit policy is preserved and the final authorization commit
  is reported after commit;
- launch packet still selects the 12-cell `grammar_mode x C x P` design;
- dry-plan verification succeeds for all 12 cells;
- exact intended execution command or exact per-cell command bundle is supplied;
- all target JSONL, content-hash, observability, analyzer, report, and billing
  paths are absent;
- advisory preflight estimate is attached for the exact L1a scope;
- official Modal pricing is re-verified on the approval date;
- numeric stop limits are supplied and accepted;
- numeric spend limits are supplied and accepted;
- alternative stable provenance policy is explicitly signed for L1a n=1 only;
- billing reconciliation plan is approved;
- post-run validation command bundle is supplied and approved;
- no-P cells are classified as controls and not as P evidence;
- runtime MLflow remains disabled with `TRITONGEN_MLFLOW=0`;
- signature block below is complete.

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

The user signed this packet for exactly one L1a n=1 12-cell run and explicitly
accepted the no-digest fallback provenance policy for L1a only.

```text
AUTHORIZES_EXECUTION: YES_L1A_N1_ONLY
DRAFT_READY_FOR_USER_SIGNATURE: SIGNED_FOR_L1A_N1_ONLY

signature_status: SIGNED_FOR_L1A_N1_ONLY
signer: user
signer_name: user
date_time: 2026-06-06 America/Mexico_City
authorization_source: User message: 'i explictly authorize modal and gpu... i have 48 hours max to get them all done.'; current user message: 'promote d2ab0a9, then create a final execution-authorization packet that explicitly accepts the no-digest fallback.'
approval_scope: L1a n=1, 12 cells only
execution_scope: L1a n=1, 12 cells only
exact_target_branch: codex-track-handoff-context
execution_code_target_commit: 31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion
approval_record_commit: TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT
exact_promoted_selector_commit: e9f180a Add executable planning for 12-cell L1a selector
exact_selector_support_promotion_audit_commit: c05e111 Audit L1a executable selector support promotion
final_signature_packet_promotion_audit_commit: 31a097e Audit L1a final signature packet promotion
preflight_evidence_commit: d2ab0a9 Prepare expedited L1a signature and preflight evidence
preflight_promotion_audit_commit: 8da7683 Audit L1a expedited signature preflight promotion
exact_intended_execution_command: TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
exact_execution_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
exact_dry_plan_verification_command: .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
numeric_stop_limits: SIGNED_rows_12_generation_attempts_72_correctness_calls_72_wall_clock_4h_stop_on_first_infrastructure_failure_fail_if_existing_paths_no_retry_no_resume
numeric_spend_limits: SIGNED_USD_25_estimated_USD_50_reconciled
spend_cap: USD_25_estimated_USD_50_reconciled
approved_spend_cap: USD_50_reconciled_billing_cap
approved_wall_clock_cap: 4h
stop_limits: rows_12_generation_attempts_72_correctness_calls_72_wall_clock_4h_stop_on_first_infrastructure_failure_fail_if_existing_paths
modal_pricing_recheck_completed: YES_2026_06_06_OFFICIAL_MODAL_PRICING_PAGE
preflight_estimate_attachment: SIGNED_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED
advisory_estimate_attached: YES
remote_image_digest_recorded: WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY
remote_digest_policy: WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY
modal_image_digest: WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY
billing_reconciliation_plan: SIGNED_L1A_RECONCILIATION_ONLY_AFTER_SIGNED_RUN_WINDOW
billing_reconciliation_plan_accepted: yes
billing_query_authorized: YES_L1A_RECONCILIATION_ONLY
post_run_validation_bundle: SIGNED_COMMANDS_LISTED_ABOVE_ONLY
post_run_validation_bundle_accepted: yes
output_mutation_scope: outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1 only
artifact_mutation_scope: artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1 plus listed L1a analysis/report/billing artifacts only
mlruns_mutation_scope: none; runtime MLflow disabled with TRITONGEN_MLFLOW=0
not_authorized: L1b, L2, paper-scale, retry, resume, benchmark, profiler, performance claims, speedup claims, dependency changes, lockfile changes, runtime MLflow tracking
authorization_statement: I authorize exactly one L1a n=1 12-cell Modal/GPU generation run using this packet, the exact command above, the signed stop/spend limits above, and the signed no-digest fallback provenance policy above. I do not authorize L1b, L2, paper-scale, retry, resume, performance work, benchmarks, profilers, runtime MLflow tracking, or any output outside the listed L1a namespaces.
authorization_statement_status: SIGNED_L1A_N1_ONLY
```
