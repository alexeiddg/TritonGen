# Agentic Transcript v1 Run Packet Template

Version: 1.0.0
Date: 2026-06-03
Status: template only
Purpose: required approval packet format before any `agentic_transcript_v1`
Modal, generation, n=5, n=20, development-scale, paper-scale, or
output-mutating run.

This template does not authorize execution. A completed packet authorizes
nothing unless it contains a fresh explicit approval line from the user or run
authority. Modal, generation, n=5, n=20, paper-scale, and output mutation are
blocked by default.

## Packet Identity

```text
packet_id:
requested_by:
prepared_by:
date:
status: DRAFT_NOT_APPROVED | APPROVED | EXPIRED | REJECTED
target_branch:
target_commit:
worktree:
state_file_version:
document_registry_version:
implementation_spec_version:
approval_source:
approval_timestamp:
```

`status: APPROVED` is valid only when the Explicit Approval section is signed.

## Scope

```text
repair_history_policy:
prompt_template_version:
prompt_renderer_version:
max_prompt_chars:
include_latest_source:
conditions:
kernel_classes:
problem_ids:
dtype:
scale_tier:
n:
model_id:
model_revision:
tokenizer_revision:
grammar_policy:
grammar_variant:
grammar_hash:
observability_policy:
```

Allowed repair-history policy values must be explicit. New agentic artifacts
must use `repair_history_policy=agentic_transcript_v1`. Legacy compatibility
artifacts must use `repair_history_policy=last_attempt_only_v1` or be loaded as
known legacy by an explicit analyzer setting. Do not infer policy from filenames.

## Authorization Flags

```text
authorizes_execution: NO | YES
modal_authorized: NO | YES
gpu_authorized: NO | YES
generation_authorized: NO | YES
output_mutation_authorized: NO | YES
n5_authorized: NO | YES
n20_authorized: NO | YES
paper_scale_authorized: NO | YES
network_authorized: NO | YES
credentialed_access_authorized: NO | YES
secrets_access_authorized: NO | YES
dependency_download_authorized: NO | YES
```

If any flag is `YES`, the packet must name the exact command, expected paths,
hard limits, stop conditions, estimated cost, and approval source. A packet with
`authorizes_execution: NO` cannot be used to run local generation, Modal, GPU,
n=5, n=20, paper-scale, or output-mutating work.

## Output Paths

```text
target_output_path:
sidecar_paths:
hash_sidecar_paths:
mlflow_or_tracking_paths:
overwrite_archive_policy:
resume_policy:
```

New `agentic_transcript_v1` artifacts must not share an output path with legacy
`last_attempt_only_v1` artifacts. Resume is invalid unless this packet
explicitly authorizes resume semantics and verifies that the prior row policy,
prompt template, prompt budget, source hashes, model, tokenizer, and seed plan
match. Mixed resume state must be quarantined.

## Expected Metadata

Every rendered agentic repair row must carry:

- `repair_history_policy`
- `repair_prompt_template_version`
- `repair_prompt_renderer_version`
- `repair_anchor_attempt_index`
- `repair_latest_attempt_index`
- `repair_history_attempt_count`
- `repair_prompt_sha256`
- `repair_prompt_char_count`
- `repair_max_prompt_chars`
- `repair_include_latest_source`
- `repair_anchor_source_hash`
- `repair_latest_source_hash`
- `repair_history_summary_sha256`
- `repair_history_error_code`

No-render terminal rows may leave rendered prompt fields unset only when no
repair prompt was rendered and the row does not represent a repair attempt.

## Analyzer Quarantine Preconditions

Before approval, the packet must identify the analyzer command or fixture proof
that verifies:

- no unknown repair-history policies;
- no mixed-policy artifact unless this packet explicitly authorizes the mix and
  labels it diagnostic-only;
- no incomplete agentic metadata for rendered repair rows;
- no inconsistent template, renderer, prompt budget, or latest-source settings;
- no unlabeled agentic rows;
- missing-policy legacy rows remain known legacy and are not normalized into
  `agentic_transcript_v1`;
- mixed repair-history analysis groups are quarantined from headline paired
  comparisons and model output.

## Pre-Run Validation

```text
git_status_check:
target_commit_check:
required_reports:
local_fixture_or_contract_test:
policy_default_invariance_check:
c_p_boundary_check:
p_to_c_isolation_check:
analyzer_quarantine_check:
forbidden_scope_diff_check:
dry_run_packet_validation:
```

Required reports before any agentic run:

- `audits/agentic_transcript_v1_a1_prompt_core_report.md`
- `audits/agentic_transcript_v1_a2_c_loop_integration_report.md`
- `audits/agentic_transcript_v1_a3_p_loop_integration_report.md`
- `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md`
- `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md`
- `audits/agentic_transcript_v1_a6_run_packet_gate_report.md`

## Run Command Placeholder

```text
command:
working_directory:
interpreter_or_entrypoint:
environment:
max_rows:
max_attempts:
max_wall_clock:
max_estimated_cost:
modal_gpu_class:
modal_image_id_or_unavailable_reason:
```

Do not put an executable command here until the packet is ready for approval.
For draft packets, use `not_authorized`.

## Post-Run Validation

```text
schema_validation:
metadata_validation:
hash_sidecar_validation:
analyzer_quarantine_validation:
factorial_or_summary_validation:
boundary_leakage_scan:
artifact_registry_update:
audit_report_update:
document_registry_update:
state_file_update:
```

Post-run validation must keep mixed-policy artifacts out of headline analysis
unless the packet explicitly authorized a diagnostic mixed-policy artifact and
the analyzer report labels it separately.

## Stop Conditions

Stop immediately if any of these occurs:

- Modal invocation without explicit approval;
- GPU work without explicit approval;
- generation without explicit approval;
- n=5, n=20, paper-scale, or output mutation without explicit approval;
- missing required repair-history metadata on a rendered agentic repair row;
- mixed-policy artifact not approved by the packet;
- policy default drift from `last_attempt_only_v1`;
- P compile-error transcript, P compact history, or P hashes leak into a C
  prompt;
- C repair fires outside F2;
- P repair fires outside `F1_COMPILE`;
- unsupported repair-history policy is accepted instead of failing closed;
- prompt rendering error triggers generation or implicit legacy fallback;
- expected output path already contains incompatible policy rows;
- performance, timing, speedup, profiler, benchmark, or paper-scale claims
  appear without separately approved evidence and validation;
- Modal timeout, preemption, worker interruption, or auth/config failure;
- local or Modal validation disagrees without a recorded disposition.

## No-Go Conditions

The packet is invalid if:

- any required field is blank instead of `not_applicable`, `not_enabled`, or
  `unavailable` with a reason;
- policy, condition, kernel class, dtype, n, scale tier, model, tokenizer,
  output path, overwrite/archive policy, attempts, wall clock, or cost limits
  are omitted;
- it relies on filename inference for policy, condition, or scale;
- it reuses a legacy output path for agentic rows;
- A2, A3, A4, A5, or A6 is missing independent review when review is required;
- analyzer quarantine is unavailable or disabled;
- the packet authorizes mixed policy rows for headline analysis;
- the packet is older than the target commit or state-file version it claims.

## Explicit Approval

The approving user or authority must write the exact approval line below and
replace every bracketed value. Without this line, the packet remains a draft.

```text
I explicitly approve packet [packet_id] for [condition] at [scale_tier], n=[n],
repair_history_policy=[policy], output=[path], Modal=[YES/NO],
generation=[YES/NO], output mutation=[YES/NO], max cost=[amount or
unavailable reason], stop conditions as written.
```
