# L1a Final Execution Authorization Report

report_version: `1.0.0`
created_at: 2026-06-06
branch: `codex/l1a-final-execution-authorization`
base_branch: `codex-track-handoff-context`
preflight_promotion_commit: `8da7683 Audit L1a expedited signature preflight promotion`
preflight_evidence_commit: `d2ab0a9 Prepare expedited L1a signature and preflight evidence`
execution_code_target_commit: `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`
classification: `L1A_FINAL_EXECUTION_AUTHORIZATION_READY`
AUTHORIZES_EXECUTION: YES_L1A_N1_ONLY

## Executive Summary

This branch converts the expedited preflight digest blocker into an explicitly
signed alternative Modal provenance policy for L1a n=1 only. It patches the
L1a authorization packet to authorize exactly one 12-cell
`grammar_mode x C x P` smoke/dev run with scoped Modal, GPU, generation,
output/artifact, billing reconciliation, and listed post-run validation
authorization.

No runtime code, launcher behavior, scientific semantics, dependencies,
lockfiles, outputs, artifacts, or `mlruns/` paths were changed. No generation,
Modal run, GPU execution, or experiment execution was performed in this branch.

## User Authorization Evidence

Authorization evidence recorded in the packet:

```text
authorization_source: User message: 'i explictly authorize modal and gpu... i have 48 hours max to get them all done.'; current user message: 'promote d2ab0a9, then create a final execution-authorization packet that explicitly accepts the no-digest fallback.'
signature_status: SIGNED_FOR_L1A_N1_ONLY
```

The current request explicitly asks to promote `d2ab0a9` and create a final
execution-authorization packet accepting the no-digest fallback. The packet
keeps this authorization scoped to L1a n=1 only.

## Execution Scope

Authorized scope:

```text
level: L1a
scale_tier: smoke/dev
design: grammar_mode x C x P
cell_count: 12
n_per_cell: 1
expected_rows_if_fully_executed: 12
kernel_class: elementwise
dtype: fp32
model_id: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
model_revision: 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a
tokenizer_revision: 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a
repair_history_policy: agentic_transcript_v1
```

The six no-P cells are signed as controls only and must not be reported as P
evidence.

## execution_code_target_commit

`31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`

The execution-code target is the promoted handoff baseline and remains distinct
from this docs-only approval record. This branch does not move the execution
target forward.

## approval_record_commit policy

`approval_record_commit: TO_BE_FILLED_AFTER_FINAL_AUTH_COMMIT`

The final authorization commit is docs-only and will be named by commit hash
after the commit exists. The packet intentionally separates:

- `execution_code_target_commit`: promoted code/document baseline for the run;
- `approval_record_commit`: docs-only final authorization record created after
  packet signing.

## Remote Digest Waiver And Fallback Provenance Policy

Remote digest policy:

`WAIVED_BY_SIGNED_ALTERNATIVE_PROVENANCE_POLICY_FOR_L1A_ONLY`

Reason:

Modal 1.4.2 did not expose a stable Docker digest, `sha256:` digest, or stable
`im-...` image id through no-generation inspection. The signer accepts a
replacement provenance bundle for L1a n=1 only.

Replacement evidence recorded in the packet:

```text
modal_app_name: tritongen-gpu-harness
modal_client_version: 1.4.2
modal_preflight_app_id: ap-oAbxWPcEyrDGyEfaBRWXqk
modal_preflight_class_id: cs-OBgdIK0FxYbUuKFMpHNjFQ
modal_preflight_generation_class_function_id: fu-Y1J87H1D2noHuthWzEPYB1
modal_preflight_correctness_function_id: fu-6W0frnq4Q6GvPN2Vwyq64z
```

Source hashes recorded in the packet:

```text
shared/modal_harness/app.py sha256=bcf0a38f81f516187be3d7d1fb41d513f253eff16b3e480295ccd5f7ad54061c
shared/modal_harness/images.py sha256=5acc6cff0991542dcba118081d499a6a51c03264d11c63d89fcbffadb95ad61c
cluster2/modal/generation.py sha256=2b811d2c34de00f89d9b0c704f539a7093f5740e5e672d9c7b4e08c3d9c49cb9
cluster2/modal/correctness.py sha256=f3b6dac0f413395c71ae3af240fd73d403c602ac00b84bf06e1aa440f1154260
cluster3/experiments/run_cluster3_modal.py sha256=ed3db24711ed2750b26765a668d871e77fa0c09d2ec4a3ed6f0581a5ff0f2631
cluster3/planning/grammar_mode_matrix.py sha256=33f6b1c5cba6abca430da97fb348244e27b0da9b9d4160af71f8b79d415de139
pyproject.toml sha256=3ed8159e4b71e05172b8d0716ea5d9f3057a0cd8989425d60389a60d0623d908
requirements.txt sha256=1671d73f1d747cc64fae787bdf657ed20f14974292d8c71dcde2c88f20c30df3
```

Post-run requirement:

Capture all available Modal run, image, app, class, function, container,
region, GPU, timing, attempt-status, preemption-status, and billing metadata into the L1a
observability/provenance sidecar and/or signed L1a audit artifacts.

## Pricing/Preflight Evidence

Pricing was verified from official Modal sources on 2026-06-06 and promoted in
`d2ab0a9`.

Signed advisory estimate:

```text
estimated_parallel_wall_clock_seconds: 5047.5
estimated_serial_wall_clock_seconds: 20167.5
estimated_gpu_seconds: 20167.5
estimated_cost: 8.0234382
warning_flags: advisory_only_not_experimental_evidence, stage_timing_inputs_estimated_not_measured
```

The estimate is not experimental evidence. Actual Modal billing
reconciliation remains authoritative.

## Signed Stop Limits

```text
max_rows: 12
max_generation_attempts: 72
max_correctness_calls: 72
max_wall_clock: 4h
stop_on_first_infrastructure_failure: yes
fail_if_any_target_path_exists: true
no_retry: true
no_resume: true
abort_if_unexpected_output_namespace_is_requested: true
abort_if_row_count_exceeds_12: true
abort_if_command_attempts_L1b_L2_or_paper_scale: true
```

## Signed Spend Limits

```text
signable_advisory_estimate: USD 8.0234382
max_estimated_cost: USD 25
max_reconciled_billing_cost: USD 50
over_cap_action: stop further runs and report
billing_reconciliation_required_after_run: yes
```

## Output/Artifact/Mlruns Mutation Authorization

Authorized:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- listed L1a post-run analysis, report, and billing artifact paths.

Not authorized:

- `mlruns/` mutation;
- runtime MLflow tracking;
- output/artifact paths outside the signed L1a n=1 namespaces;
- preliminary-report mutation before post-run validation.

The exact execution command includes `TRITONGEN_MLFLOW=0`.

## Billing Reconciliation Authorization

Billing query authorization is signed for L1a reconciliation only after the
approved run window exists and a redacted report path can be named.

No billing query was run in this branch.

## Post-Run Validation Authorization

Post-run validation is authorized only for the listed L1a commands and only
after L1a artifacts exist. The signed validation bundle includes:

- schema and row-count validation;
- content-hash sidecar validation;
- observability sidecar validation;
- grammar-mode consistency validation;
- analyzer/report command for listed L1a paths only;
- billing reconciliation after signed run window and redacted report path.

## Exact Execution Command

```text
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1 --overwrite
```

## Exact Validation Bundle

Pre-execution local planning checks:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
```

Post-run validation commands are listed in the packet under
`Post-Run Validation Required After Approved L1a Run` and are authorized only
after the signed L1a artifacts exist.

## Non-Authorized Items

This packet does not authorize:

- L1b;
- L2;
- paper-scale runs;
- retry;
- resume;
- benchmarks;
- profilers;
- performance claims;
- speedup claims;
- cost-reduction claims;
- runtime MLflow tracking;
- `mlruns/` mutation;
- dependency or lockfile changes;
- runtime code changes;
- launcher behavior changes;
- scientific semantics changes.

## No-Runtime-Code-Change Proof

The branch changes are docs/audits only. Runtime-code scan is expected empty:

```text
git diff --name-only -- cluster1 cluster2 cluster3 shared
```

## No-Pre-Authorization-Execution Proof

Before this final authorization commit, no generation, GPU run, Modal
experiment execution, billing query, output mutation, artifact mutation, or
`mlruns/` mutation was performed.

Commands in this branch were limited to git inspection/mutation, file
inspection, local hash collection, packet editing, audit authoring, and
validation scans.

## Classification

`L1A_FINAL_EXECUTION_AUTHORIZATION_READY`

## Next Step Recommendation

Commit this final authorization packet, then run the listed pre-execution
validation checks immediately before any launch. Do not broaden scope beyond
the signed L1a n=1 packet, and stop if any target path already exists or if the
command attempts L1b, L2, paper-scale, retry, resume, benchmark, profiler, or
runtime MLflow tracking behavior.
