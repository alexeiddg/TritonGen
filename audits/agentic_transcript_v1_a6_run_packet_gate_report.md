# Agentic Transcript v1 A6 Run-Packet Gate Report

Date: 2026-06-03
Status: complete with no-execution caveat
Classification: A6_RUN_PACKET_GATE_PLANNING_COMPLETE_NO_EXECUTION

## Executive Summary

A6 adds the run-packet gate required before future `agentic_transcript_v1`
execution. It creates a reusable approval-packet template and one concrete
next-run draft for a possible future Cluster 3 G+C+P n=1 smoke. The draft is
explicitly not approved and authorizes no command, Modal call, GPU work,
generation, n=5, n=20, paper-scale work, output mutation, network access,
credentialed access, dependency download, or MLflow runtime artifact.

No runner, prompt builder, repair loop, analyzer behavior, Modal code, raw
output artifact, generation command, n=5 run, n=20 run, or paper-scale behavior
was changed.

## Worktree Status

- Worktree: `/private/tmp/tritongen-llm-repair-memory`
- Branch: `codex/llm-repair-memory-agentic-transcript-v1`
- Entry HEAD: `59021f2 A5: Add repair-history analyzer quarantine`
- Baseline sequence: `6c859b3` A2 -> `d2a9f2a` A3 -> `d1c8196` A4 ->
  `59021f2` A5
- Baseline venv interpreter reserved for any Python validation:
  `/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python`
- No Modal, GPU, generation, experiment execution/artifact, n=5, n=20,
  paper-scale, MLflow runtime artifact, or `outputs/` mutation was performed.

## Files Changed

- `docs/handoff/agentic_transcript_v1_run_packet_template.md`
- `docs/handoff/agentic_transcript_v1_next_run_packet.md`
- `audits/agentic_transcript_v1_a6_run_packet_gate_report.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/agentic_document_hub.md`

## Packet Template

`docs/handoff/agentic_transcript_v1_run_packet_template.md` defines the
required approval packet before any future agentic run. It requires explicit
fields for:

- packet identity and approval source;
- target branch, commit, state version, registry version, and implementation
  spec version;
- repair-history policy, prompt template, renderer, budget, latest-source
  setting, condition, kernel class, dtype, scale tier, n, model, tokenizer,
  grammar, and observability policy;
- Modal/GPU/generation/output/n=5/n=20/paper-scale/network/credential/secrets/
  dependency authorization flags;
- output, sidecar, hash, tracking, overwrite, and resume policy;
- expected metadata, analyzer quarantine preconditions, pre-run validation,
  run command placeholder, post-run validation, stop conditions, no-go
  conditions, and the explicit approval line.

The template states that it authorizes no execution by itself. It also states
that mixed repair-history-policy artifacts are quarantined unless a future
approved packet explicitly authorizes and labels them diagnostic-only.

## Concrete Draft Packet

`docs/handoff/agentic_transcript_v1_next_run_packet.md` is a draft for a
possible future Cluster 3 G+C+P n=1 smoke using
`repair_history_policy=agentic_transcript_v1`.

Its hard authorization fields are:

```text
STATUS: DRAFT_NOT_APPROVED
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
N5_AUTHORIZED: NO
N20_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
```

The draft includes planned output paths only as non-authorizing placeholders.
It records that model revision, tokenizer revision, grammar hash, Modal GPU
class, Modal image provenance, max attempts, wall clock, and cost limit must be
filled before any approval.

## Metadata Checklist

The packet gate requires rendered agentic repair rows to carry:

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

Future approval is blocked unless the packet records checks proving:

- no unknown repair-history policies;
- no mixed-policy artifact unless explicitly authorized and labeled
  diagnostic-only;
- no incomplete agentic metadata for rendered repair rows;
- no inconsistent template, renderer, prompt budget, or latest-source values;
- no unlabeled agentic rows;
- missing-policy legacy rows remain legacy only;
- headline analysis quarantines mixed repair-history groups.

## Stop Conditions

The gate requires stopping on:

- Modal, GPU, generation, n=5, n=20, paper-scale, or output mutation without
  signed approval;
- missing required metadata on rendered agentic repair rows;
- unapproved mixed-policy artifacts;
- policy default drift from `last_attempt_only_v1`;
- P compile-error transcript/history/hash material leaking into a C prompt;
- C repair outside F2;
- P repair outside `F1_COMPILE`;
- prompt rendering failure followed by generation;
- incompatible existing output paths;
- performance, timing, speedup, profiler, benchmark, or paper-scale claims
  without separately approved evidence and validation;
- Modal auth/config/timeout/preemption without an approved disposition.

## Validation

Preflight completed:

```text
git status --short --branch
```

Result: clean A5 entry state on
`codex/llm-repair-memory-agentic-transcript-v1`, ahead of origin by four
commits.

```text
git log --oneline --decorate -18
```

Result included expected A2/A3/A4/A5 sequence with HEAD at `59021f2`.

Required prior reports were present:

- `audits/agentic_transcript_v1_a1_prompt_core_report.md`
- `audits/agentic_transcript_v1_a2_c_loop_integration_report.md`
- `audits/agentic_transcript_v1_a3_p_loop_integration_report.md`
- `audits/agentic_transcript_v1_a4_p_to_c_isolation_report.md`
- `audits/agentic_transcript_v1_a5_analyzer_grouping_report.md`
- `docs/18_agentic_transcript_v1_implementation_spec.md`

Post-edit validation completed:

```text
git diff --check
```

Result: passed with empty output.

```text
git diff --name-only -- cluster1 cluster2/feedback cluster2/experiments cluster2/results cluster3/feedback cluster3/experiments cluster3/results shared/repair_history outputs
```

Result: empty output.

Authorization-positive scan over the draft packet, template, and A6 report:
no uppercase execution authorization flag was set to an affirmative value.

```text
rg -n "^STATUS: DRAFT_NOT_APPROVED$|^AUTHORIZES_EXECUTION: NO$|^MODAL_AUTHORIZED: NO$|^GENERATION_AUTHORIZED: NO$|^OUTPUT_MUTATION_AUTHORIZED: NO$|^N5_AUTHORIZED: NO$|^N20_AUTHORIZED: NO$|^PAPER_SCALE_AUTHORIZED: NO$" docs/handoff/agentic_transcript_v1_next_run_packet.md
```

Result: matched all required draft header authorization lines.

```text
rg -n "^command:" docs/handoff/agentic_transcript_v1_next_run_packet.md docs/handoff/agentic_transcript_v1_run_packet_template.md
```

Result: the concrete draft uses `command: not_authorized`; the template contains
only a placeholder field.

This report should not be treated as a run approval packet.

## Forbidden-Scope Statement

A6 is planning and gate documentation only. It does not touch:

- `cluster1/`
- `cluster2/feedback/`
- `cluster2/experiments/run_cluster2_modal.py`
- `cluster2/results/`
- `cluster3/feedback/`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/results/`
- `shared/repair_history/`
- `outputs/`
- Modal execution code

## Unresolved Risks

- A2/A3/A4/A5/A6 remain pending independent review before promotion or future
  run approval.
- The next-run packet is only a draft. It intentionally leaves model revision,
  tokenizer revision, grammar hash, Modal GPU class, Modal image provenance,
  wall clock, cost, problem id, and exact command unavailable until a future
  approval pass.

## Classification

A6_RUN_PACKET_GATE_PLANNING_COMPLETE_NO_EXECUTION

## Next-Step Recommendation

Request independent review of the A6 gate documents. Do not execute Modal,
generation, n=5, n=20, paper-scale, all-condition, profiling, performance,
timing, speedup, or output-mutating work without a fresh signed approval packet.
