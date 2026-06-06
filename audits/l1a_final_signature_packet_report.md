# L1a Final Signature Packet Report

report_version: `1.0.0`
date: 2026-06-06
branch: `codex/l1a-final-signature-packet`
target_branch: `codex-track-handoff-context`
target_commit: `c05e111 Audit L1a executable selector support promotion`
classification: `L1A_FINAL_SIGNATURE_PACKET_COMPLETE`
AUTHORIZES_EXECUTION: NO

## Executive Summary

This docs-only package prepares the final L1a signature packet surface for
human review. It refreshes the packet target to the promoted handoff trunk
commit `c05e111`, records exact selector provenance through promoted commit
`e9f180a` and promotion audit commit `c05e111`, and keeps the packet unsigned
with `AUTHORIZES_EXECUTION: NO`.

No Modal, GPU, generation, experiment execution, output mutation, artifact
creation, MLflow runtime tracking, billing query, analyzer refresh, report
build, benchmark, profiler, dependency change, or lockfile change is authorized
or performed by this package.

## Files Changed

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/l1a_final_signature_packet_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Target Approval Fields

The packet now names:

- target branch: `codex-track-handoff-context`
- target commit: `c05e111 Audit L1a executable selector support promotion`
- exact promoted selector commit:
  `e9f180a Add executable planning for 12-cell L1a selector`
- exact promotion audit commit:
  `c05e111 Audit L1a executable selector support promotion`

The target fields are review-ready but not signed. Future execution still
requires an explicit human signature against the exact target commit.

## Execution Command Surface

The source-backed local planning command surface is:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
```

The source-backed selector-level future command surface recorded for signature
review is:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
```

The per-cell executable commands are source-backed by
`cluster3/planning/grammar_mode_matrix.py` and emitted by the local
`--execution-plan` selector. They include per-cell output and observability
paths, `--grammar-mode-cell`, required `--grammar-variant` values for active
grammar cells, `SIGNED_L1A_PACKET_ID_REQUIRED`, and `--overwrite`. They were
not run.

## 12-Cell Matrix Status

The packet preserves the 12-cell `grammar_mode x C x P` matrix:

- `grammar_mode` in `grammar_off`, `template_upper_bound`, `task_agnostic`
- C in `off`, `on`
- P in `off`, `on`
- total cells: 12

The six no-P cells remain controls, not P evidence.

## Path/Collision Status

The packet preserves these planned namespaces:

- output root:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`
- observability root:
  `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1`
- JSONL path pattern:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl`
- content-hash sidecar pattern:
  `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.jsonl.hashes.json`
- observability sidecar patterns:
  `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<condition_id>.observability.jsonl`,
  `<condition_id>.observability.summary.json`, and
  `<condition_id>.observability.jsonl.hashes.json`
- collision policy: `fail_if_any_target_path_exists`

No path was created, written, validated against live artifacts, overwritten, or
mutated in this package.

## Grammar Hash Status

The packet preserves the current grammar-mode mapping and hash locks:

- `grammar_off`: no grammar file, no grammar hash
- `template_upper_bound`:
  `cluster1/grammar/triton_kernel.gbnf`,
  `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`
- `task_agnostic`:
  `cluster1/grammar/triton_kernel_agnostic.gbnf`,
  `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`

No grammar file was modified.

## Model/Seed Status

The packet preserves:

- model id: `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
- model revision:
  `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- tokenizer revision:
  `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- decoding config: `temperature=0.2; max_new_tokens=1536`
- n per cell: `1`
- base seed policy: `base_seed=0` per cell/invocation
- retry/resume policy:
  `PROPOSED_NOT_SIGNED_no_retry_no_resume_unless_explicitly_signed`

## Preflight Estimate Status

The packet still carries only a synthetic advisory placeholder:
`NOT_SIGNABLE_SYNTHETIC_PLACEHOLDER`. It remains advisory only, not evidence,
not billing reconciliation, and not sufficient for signature. Official pricing
must be re-verified before a future signature.

## Stop/Spend Limit Status

The packet retains proposed candidate limits only:

- rows: 12
- generation attempts: `PROPOSED_NOT_SIGNED_72_total_initial_plus_C_and_P_repair_attempt_ceiling`
- correctness calls: `PROPOSED_NOT_SIGNED_72_total_attempt_ceiling`
- wall clock: `PROPOSED_NOT_SIGNED_4_hours`
- estimated cap: `PROPOSED_NOT_SIGNED_USD_25_requires_official_pricing_reverification`
- reconciled billing cap:
  `PROPOSED_NOT_SIGNED_USD_50_billing_reconciliation_authoritative`

These are not approved spend or stop limits.

## Modal Image Digest Status

The packet keeps
`REQUIRED_BEFORE_SIGNATURE_REMOTE_IMAGE_DIGEST_UNKNOWN`. No Modal command,
remote image inspection, billing query, or network lookup was run.

## Billing Reconciliation Status

Billing remains `PLAN_ONLY_NO_BILLING_QUERY_AUTHORIZED`. A later signed packet
must supply an exact time window, approved billing-query operation, redacted
report path, report hash, reconciliation plan, and write authorization for any
sidecar mutation. Actual post-run billing reconciliation remains authoritative
for spend.

## Post-Run Validation Bundle Status

The packet lists proposed local command surfaces for:

- row count and schema validation
- content-hash sidecar validation
- observability sidecar validation
- grammar-mode consistency validation
- analyzer/report command surface
- billing reconciliation requirement

All post-run commands remain `PROPOSED_NOT_SIGNED` or
`REQUIRED_BEFORE_SIGNATURE`. They were not run in this package.

## Signature Block Status

The signature block is present and explicitly unsigned. It includes fields for:

- signer name
- date/time
- target commit
- spend cap
- stop limits
- Modal pricing recheck completed: yes/no
- advisory estimate attached: yes/no
- remote image digest recorded: yes/no
- billing reconciliation plan accepted: yes/no
- post-run validation bundle accepted: yes/no
- authorization statement
- signature status: `UNSIGNED`

No signature field was filled with approval language.

## Unresolved Blockers

- human signature is absent;
- exact approval remains unsigned;
- proposed stop/spend limits are not signed;
- preflight estimate is not signable;
- remote Modal image digest is unknown;
- billing-query authorization is absent;
- post-run validation and analyzer/report writes are not authorized;
- output/artifact/mlruns mutation remains unauthorized;
- separate execution approval remains required.

## No-Execution Proof

This package only inspected files and edited docs. It did not invoke Modal,
GPU jobs, generation, experiment launchers, benchmarks, profilers, billing
queries, analyzer/report refreshes, MLflow runtime tracking, or any command
that writes outputs, artifacts, or `mlruns/`.

## No-Output/Mlruns Mutation Proof

Protected diff scans over `outputs`, `artifacts`, `mlruns`,
`docs/preliminary_report`, dependency files, and lockfiles are expected to
remain empty for this package. No protected path is intentionally edited.

## Validation/Scans Run

Validation commands for this package:

```text
git diff --check
git status --short --branch
git diff --name-only
git diff --name-only -- cluster1 cluster2 cluster3 shared
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
positive authorization scan over packet/audit/handoff docs
required status scan over packet and audit
evidence-boundary scan over the docs/audits diff
false-signature scan over the docs/audits diff
```

Observed validation result:

- `git diff --check`: pass;
- `git status --short --branch`: branch
  `codex/l1a-final-signature-packet` with four tracked docs modified and this
  audit report untracked;
- tracked diff scan: packet plus the three handoff docs;
- supplemental untracked-file scan: this audit report;
- runtime-code scan over `cluster1`, `cluster2`, `cluster3`, and `shared`:
  empty;
- protected mutation scan over outputs, artifacts, `mlruns`,
  `docs/preliminary_report`, dependency files, and lockfiles: empty;
- positive authorization scan: empty;
- required status scan: contains the expected no-execution, unsigned,
  proposed, not-signable, image-digest-required, billing, preflight,
  `grammar_mode_cp_12cell`, `c05e111`, and `e9f180a` markers;
- evidence-boundary scan: empty;
- false-signature scan: only negated or placeholder terms such as
  `UNSIGNED`, `PROPOSED_NOT_SIGNED`, and `SIGNED_L1A_PACKET_ID_REQUIRED`.

## Classification

`L1A_FINAL_SIGNATURE_PACKET_COMPLETE`

## Next-Step Recommendation

Review the unsigned packet for human signature readiness only. Do not create or
run an L1a execution packet until a later explicit signature supplies the exact
target commit, command bundle, stop/spend limits, signable preflight estimate,
remote image digest, billing reconciliation authorization, post-run validation
authorization, and output/artifact/mlruns mutation authorization.
