# Agentic Transcript v1 Next Run Packet Draft

Version: 0.1.0
Date: 2026-06-03
STATUS: DRAFT_NOT_APPROVED
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
N5_AUTHORIZED: NO
N20_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO

This packet is a draft planning artifact only. It authorizes no command, no
Modal call, no generation, no GPU work, no n=5 run, no n=20 run, no paper-scale
work, and no output mutation. A future run requires fresh explicit approval
using the approval line in
`docs/handoff/agentic_transcript_v1_run_packet_template.md`.

## Packet Identity

```text
packet_id: ATX-A6-C3-GCP-N1-SMOKE-DRAFT-2026-06-03
requested_by: user
prepared_by: Codex
date: 2026-06-03
status: DRAFT_NOT_APPROVED
target_branch: codex/llm-repair-memory-agentic-transcript-v1
target_commit: 59021f2 or a reviewed descendant containing A6
worktree: /private/tmp/tritongen-llm-repair-memory
state_file_version: docs/handoff/experiment_change_orchestration_state.md v1.5.17
document_registry_version: docs/handoff/document_version_registry.md v1.54.0
implementation_spec_version: docs/18_agentic_transcript_v1_implementation_spec.md v0.1.5
approval_source: not_approved
approval_timestamp: not_applicable
```

## Planned Future Scope

Recommended first executable scope after review and explicit approval:

```text
repair_history_policy: agentic_transcript_v1
prompt_template_version: agentic_transcript_v1
prompt_renderer_version: agentic_transcript_v1
max_prompt_chars: 12000
include_latest_source: true
conditions: G+C+P
kernel_classes: elementwise
problem_ids: one explicitly named smoke problem id, selected before approval
dtype: fp32
scale_tier: smoke
n: 1
model_id: unavailable until approval
model_revision: unavailable until approval
tokenizer_revision: unavailable until approval
grammar_policy: task_agnostic unless approval selects diagnostic template grammar
grammar_variant: unavailable until approval
grammar_hash: unavailable until approval
observability_policy: JSONL and sidecar provenance only; MLflow optional/no-op unless separately authorized
```

The recommended first executable packet is a future n=1 smoke because it is the
smallest meaningful post-A2/A3/A4/A5 check for the integrated G+C+P path. This
draft does not approve that smoke. It also does not approve n=5, n=20,
paper-scale, all-condition, profiling, performance, timing, speedup, or
benchmark work.

## Authorization Flags

```text
authorizes_execution: NO
modal_authorized: NO
gpu_authorized: NO
generation_authorized: NO
output_mutation_authorized: NO
n5_authorized: NO
n20_authorized: NO
paper_scale_authorized: NO
network_authorized: NO
credentialed_access_authorized: NO
secrets_access_authorized: NO
dependency_download_authorized: NO
```

## Planned Output Paths

```text
target_output_path: outputs/cluster3/agentic_transcript_v1_g_plus_c_plus_p_smoke_n1.jsonl
sidecar_paths: outputs/cluster3/agentic_transcript_v1_g_plus_c_plus_p_smoke_n1.meta.json
hash_sidecar_paths: outputs/cluster3/agentic_transcript_v1_g_plus_c_plus_p_smoke_n1.hashes.json
mlflow_or_tracking_paths: not_enabled
overwrite_archive_policy: must_fail_if_path_exists
resume_policy: no_resume
```

These paths are reserved only as a planning suggestion. This draft does not
create, overwrite, append, or validate them. A future approved packet may choose
different paths, but must not reuse a legacy `last_attempt_only_v1` output path.

## Expected Agentic Metadata

Every rendered repair row in any future approved run must include:

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

Approval must be blocked unless the future packet proves:

- no unknown repair-history policies;
- no mixed-policy artifact unless explicitly authorized and labeled
  diagnostic-only;
- no incomplete agentic metadata for rendered repair rows;
- no inconsistent template, renderer, prompt budget, or latest-source settings;
- no unlabeled agentic rows;
- missing-policy legacy rows remain legacy only;
- headline analysis quarantines mixed repair-history groups.

## Pre-Run Validation Required Before Approval

```text
git status --short --branch
git log --oneline --decorate -18
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster2/tests/test_feedback_prompts.py cluster2/tests/test_repair_loop.py cluster2/tests/test_results_logger.py cluster2/tests/test_run_cluster2_modal.py -q
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_p_repair_loop.py cluster3/tests/test_cluster3_schema.py cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_p_to_c_isolation.py -q
git diff --check
git diff --name-only -- cluster1 cluster2/feedback cluster2/experiments cluster2/results cluster3/feedback cluster3/experiments cluster3/results outputs
```

The future approval packet must record exact pass/fail results. The forbidden
scope diff must be empty unless the approval explicitly expands scope before
work begins.

## Run Command Placeholder

```text
command: not_authorized
working_directory: /private/tmp/tritongen-llm-repair-memory
interpreter_or_entrypoint: not_authorized
environment: not_authorized
max_rows: 1
max_attempts: must be specified before approval
max_wall_clock: must be specified before approval
max_estimated_cost: unavailable until approval
modal_gpu_class: unavailable until approval
modal_image_id_or_unavailable_reason: unavailable until approval
```

No command may be inferred from this placeholder.

## Post-Run Validation Required After Any Future Approved Run

```text
schema_validation: required
metadata_validation: required
hash_sidecar_validation: required
analyzer_quarantine_validation: required
factorial_or_summary_validation: diagnostic-only for n=1
boundary_leakage_scan: required for P-to-C transcript/history/hash leakage
artifact_registry_update: required if output is created
audit_report_update: required if output is created
document_registry_update: required if output is created
state_file_update: required if output is created
```

## Stop Conditions

Stop immediately if any of these occurs:

- Modal, GPU, generation, n=5, n=20, paper-scale, or output mutation starts
  without a signed approval packet;
- any required metadata is missing on a rendered agentic repair row;
- any mixed-policy artifact is not explicitly authorized and diagnostic-only;
- `last_attempt_only_v1` stops being the default policy;
- P compile-error transcript/history/hash material appears in a C prompt;
- C repair fires outside F2;
- P repair fires outside `F1_COMPILE`;
- prompt rendering fails and generation still proceeds;
- the target output path already exists or contains incompatible policy rows;
- performance, timing, speedup, profiler, benchmark, or paper-scale claims
  appear without separately approved evidence and validation;
- Modal auth/config/timeout/preemption occurs without an approved disposition.

## No-Go Conditions

This draft cannot be approved as-is if:

- target commit is not updated to the reviewed A6 descendant;
- model, model revision, tokenizer revision, problem id, grammar hash, Modal GPU
  class, Modal image provenance, max attempts, wall clock, or cost limit remains
  `unavailable`;
- A2/A3/A4/A5/A6 independent review is still required by the orchestrator and
  has not accepted the relevant checkpoint;
- analyzer quarantine is disabled or not validated;
- planned output paths conflict with legacy or existing artifacts.

## Explicit Approval

Unsigned. No execution is approved.

```text
NOT APPROVED. A future user approval must replace this line using the exact
approval text from docs/handoff/agentic_transcript_v1_run_packet_template.md.
```
