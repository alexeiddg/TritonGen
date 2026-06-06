# L1a Expedited Signature And Preflight Promotion Audit Report

report_version: `1.0.0`
created_at: 2026-06-06
source_branch: `codex/l1a-expedited-signature-and-preflight`
target_branch: `codex-track-handoff-context`
promoted_commit: `d2ab0a9 Prepare expedited L1a signature and preflight evidence`
classification: `L1A_EXPEDITED_SIGNATURE_PREFLIGHT_PROMOTION_COMPLETE_WITH_DIGEST_POLICY_REMAINING`
AUTHORIZES_EXECUTION: NO

## Promoted Commit: d2ab0a9

`d2ab0a9 Prepare expedited L1a signature and preflight evidence` was promoted
into `codex-track-handoff-context` by fast-forward merge from the source branch.
The promotion introduced:

- `audits/l1a_expedited_signature_and_preflight_report.md`;
- updates to
  `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`.

The promoted commit did not change runtime code, launcher behavior, scientific
rows, repair policy, sampling/model settings, or grammar semantics.

## Remote Digest Blocker

The promoted preflight evidence reached one unresolved execution blocker:

`BLOCKED_REMOTE_IMAGE_DIGEST_NOT_EXPOSED_WITHOUT_BROADER_MODAL_APP_PATH`

Modal 1.4.2 did not expose a Docker digest, `sha256:` digest, or stable
`im-...` image id through the no-generation inspection path. Direct image
hydration raised:

```text
Images cannot currently be hydrated on demand; you can build an Image by running an App that uses it.
```

Ephemeral Modal app registration exposed app/function/class handles but did not
surface image digest metadata in the client-visible output. No generation or
correctness function was invoked to resolve the digest.

## Pricing Verification

The promoted packet records current Modal pricing verification from official
Modal sources retrieved on 2026-06-06:

- Nvidia L4 GPU task: `$0.000222 / sec`;
- CPU physical core: `$0.0000131 / core / sec`;
- memory: `$0.00000222 / GiB / sec`.

The packet also records that actual post-run Modal billing reconciliation is
authoritative and remains scoped to a future signed L1a run window only.

## Signable Advisory Estimate

The promoted packet attaches a pricing-verified advisory estimate for the exact
12-cell L1a n=1 scope:

```text
rows: 12
total_generation_attempt_upper_bound: 72
correctness_call_upper_bound: 72
recommended_shape_name: bounded_fanout_across_cells_seeds
estimated_parallel_wall_clock_seconds: 5047.5
estimated_serial_wall_clock_seconds: 20167.5
estimated_gpu_seconds: 20167.5
estimated_cost: 8.0234382
max_estimated_cost: USD 25
max_reconciled_billing_cost: USD 50
warning_flags: advisory_only_not_experimental_evidence, stage_timing_inputs_estimated_not_measured
```

The estimate is planning evidence only. It does not replace JSONL rows,
observability sidecars, analyzer outputs, MLflow indexing, or Modal billing
reconciliation.

## Remaining Policy Decision

The only remaining policy decision from the promoted preflight is whether to:

1. identify a Modal-supported no-generation API or command that returns stable
   image digest metadata; or
2. explicitly sign an alternative Modal provenance policy for L1a n=1 only.

This promotion audit does not make that decision and does not authorize
execution. The next packet branch must resolve the digest blocker explicitly
before any L1a run.

## No-Generation Proof

The promoted branch records only git inspection, file inspection, Modal
CLI/help/app-registration metadata inspection, official pricing lookup, local
preflight estimator calculation, packet editing, and audit authoring.

No command invoked:

- `cluster3.experiments.run_cluster3_modal`;
- `RemoteC2Generator.generate_one`;
- `remote_c2_correctness.remote`;
- generation adapters;
- correctness adapters;
- paper-scale experiments;
- benchmarks;
- profilers.

All ephemeral Modal inspection apps were verified stopped with `Tasks: 0` in
the promoted evidence.

## No-Output/Mlruns Mutation Proof

The promotion did not mutate output, artifact, `mlruns/`, preliminary report,
dependency, or lockfile paths. Protected-path validation for the promotion
diff was empty:

```text
git diff --name-only d2ab0a9 -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Runtime-code diff validation against the promoted commit was also empty:

```text
git diff --name-only d2ab0a9 -- cluster1 cluster2 cluster3 shared
```

## Classification

`L1A_EXPEDITED_SIGNATURE_PREFLIGHT_PROMOTION_COMPLETE_WITH_DIGEST_POLICY_REMAINING`

## Next-Step Recommendation

Create a separate final authorization branch from the updated
`codex-track-handoff-context` tip. Patch only the L1a packet and authorization
audit to explicitly accept a no-digest fallback provenance policy for L1a n=1
only, while keeping L1b, L2, paper-scale, retry, resume, benchmarks, profilers,
and performance claims out of scope.
