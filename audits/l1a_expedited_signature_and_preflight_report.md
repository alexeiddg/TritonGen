# L1a Expedited Signature And Preflight Report

report_version: `1.0.0`
created_at: 2026-06-06
branch: `codex/l1a-expedited-signature-and-preflight`
base_branch: `codex-track-handoff-context`
base_commit: `31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`
classification: `L1A_EXPEDITED_SIGNATURE_BLOCKED_REMOTE_DIGEST`
AUTHORIZES_EXECUTION: NO

## Executive Summary

This branch refreshed the L1a packet target policy, recorded the user's limited
Modal/GPU authorization for remote digest and pricing/preflight work, verified
current Modal pricing from official Modal sources, and replaced the synthetic
preflight placeholder with a pricing-verified advisory estimate for the exact
12-cell L1a n=1 scope.

The packet is not signable as-is because Modal 1.4.2 did not expose a remote
image digest or stable image id through the no-generation inspection paths used
here. Direct image hydration is blocked by the Modal client, and ephemeral app
registration hydrated class/function handles but did not expose image digest
metadata. No generation, experiment execution, output/artifact/mlruns mutation,
benchmark, profiler, or runtime code change was performed.

## User Authorization Received

The user authorized Modal and GPU use for this phase, with explicit inquiry,
while keeping generation, experiment execution, output mutation, paper-scale
execution, performance/profiling, and MLflow runtime tracking blocked.

Scoped authorization recorded in the packet:

```text
MODAL_AUTHORIZED: YES_FOR_REMOTE_IMAGE_DIGEST_AND_CURRENT_PRICING_VERIFICATION_ONLY
GPU_AUTHORIZED: YES_FOR_REMOTE_IMAGE_DIGEST_PREFLIGHT_VERIFICATION_ONLY_NO_FUNCTION_INVOCATION_PERFORMED
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: YES_FOR_L1A_RECONCILIATION_ONLY_AFTER_RUN
```

## execution_code_target_commit

`31a097e3231e5b73a1402a26d18c660ba2f53d84 Audit L1a final signature packet promotion`

This is the latest promoted `codex-track-handoff-context` baseline at branch
creation. Inspection did not identify a newer promoted runtime-code-bearing
commit. The execution target remains anchored to this promoted baseline rather
than the later review-only commit `3318002`.

## approval_record_commit policy

The packet now separates:

- `execution_code_target_commit`: the promoted code/document baseline that
  future L1a execution would target;
- `approval_record_commit`: the future docs-only packet commit containing final
  signed approval.

This avoids infinite target staleness. The final signed packet may be newer
than the execution-code target and does not need to target itself.

## Stale Target Fix

The packet no longer treats `c05e111 Audit L1a executable selector support
promotion` as the active execution target. It is retained only as selector
support promotion evidence. The active execution-code target is `31a097e`, and
the final signature packet promotion audit is also recorded as `31a097e`.

## Modal Image Digest Evidence

Repo-supported Modal surfaces inspected:

- app: `tritongen-gpu-harness` from `shared/modal_harness/app.py`;
- generation surface: `cluster2.modal.generation.RemoteC2Generator` using
  `c2_generation_image`, derived from `shared.modal_harness.images.llm_generation_image`;
- correctness surface: `cluster2.modal.correctness.remote_c2_correctness`
  using `c2_correctness_image`, derived from
  `shared.modal_harness.images.triton_compile_image`.

Commands and outcomes:

```text
.venv/bin/python -m pip show modal
```

Observed Modal client: `modal==1.4.2`.

```text
.venv/bin/python -m modal --help
.venv/bin/python -m modal deploy --help
.venv/bin/python -m modal app --help
.venv/bin/python -m modal run --help
```

These commands inspected CLI surfaces only.

```text
.venv/bin/python - <<'PY'
from cluster2.modal.generation import c2_generation_image
from cluster2.modal.correctness import c2_correctness_image
for image in (c2_generation_image, c2_correctness_image):
    image.hydrate()
PY
```

Outcome: blocked before digest retrieval. Modal raised:

```text
Images cannot currently be hydrated on demand; you can build an Image by running an App that uses it.
```

```text
.venv/bin/python - <<'PY'
import cluster2.modal.generation
import cluster2.modal.correctness
from shared.modal_harness.app import app
with app.run():
    ...
PY
```

Outcome: ephemeral app registration succeeded with no method invocation. It
hydrated:

- app id: `ap-oAbxWPcEyrDGyEfaBRWXqk`;
- class id: `cs-OBgdIK0FxYbUuKFMpHNjFQ`;
- generation class function id: `fu-Y1J87H1D2noHuthWzEPYB1`;
- correctness function id: `fu-6W0frnq4Q6GvPN2Vwyq64z`.

No Docker digest, `sha256:` digest, or stable `im-...` image id was exposed in
the client-visible function/class metadata.

An attempted app-layout metadata query created a zero-task ephemeral app,
`ap-Jvg9KmH3pCXVVIcJv7Ev42`, but the layout query did not return digest
metadata. The app was stopped with:

```text
.venv/bin/python -m modal app stop --yes ap-Jvg9KmH3pCXVVIcJv7Ev42
```

Final app-list verification showed all inspection apps stopped with `Tasks: 0`.

Remote build status: not determinable from client-visible output. No GPU
function executed. No generation method was invoked. No correctness method was
invoked. No L1a launcher command was invoked.

Digest classification:

`BLOCKED_REMOTE_IMAGE_DIGEST_NOT_EXPOSED_WITHOUT_BROADER_MODAL_APP_PATH`

## Pricing Verification Evidence

Official source: Modal pricing page, `https://modal.com/pricing`, retrieved on
2026-06-06.

Official rates recorded:

- Nvidia L4 GPU task: `$0.000222 / sec`;
- CPU physical core: `$0.0000131 / core / sec`;
- memory: `$0.00000222 / GiB / sec`.

Official billing documentation source:
`https://modal.com/docs/guide/billing`, retrieved on 2026-06-06. It states that
up-to-date unit pricing is on Modal's pricing page and that billing report
interfaces exist for Team and Enterprise workspaces. Actual billing
reconciliation remains authoritative and must be scoped to the signed L1a run
window after execution.

GPU type assumed: `L4`, matching the current Cluster 3 runner validation and
the Cluster 2 generation/correctness defaults used by L1a.

Uncertainty:

- official page rates can change and must be rechecked before L2/L3 or any
  paper-scale run;
- region selection and non-preemptible execution multipliers are not selected
  here and are not included;
- actual billing reconciliation after the approved run is authoritative.

## Signable Preflight Estimate

Estimator:

`cluster3/planning/modal_preflight_estimator.py`

Estimator input:

```text
rows: 12
n_per_cell: 1
total_generation_attempt_upper_bound: 72
correctness_call_upper_bound: 72
gpu_type: L4
price_source: official Modal pricing page, retrieved 2026-06-06
L4_GPU_rate: 0.000222/sec
CPU_rate: 0.0000131/core/sec
memory_rate: 0.00000222/GiB/sec
conservative_unit_rate: 0.00039784/sec
unit_rate_basis: max(L4 + 8 CPU cores + 32 GiB memory, L4 + 4 CPU cores + 24 GiB memory)
cold_start_seconds: 120
model_load_seconds: 180
generation_seconds_per_row: 360
compile_correctness_seconds_per_row: 540
repair_overhead_seconds_per_activated_repair: 60
expected_p_activation_rate: 1.0
expected_c_activation_rate: 1.0
fanout_limit: 4
safety_multiplier: 1.5
fixed_overhead_seconds: 5
stage_timing_source: estimated
fail_if_existing_policy: fail_if_any_target_path_exists
retry_policy: no_retry_no_resume_unless_explicitly_signed
```

Estimator output:

```text
recommended_shape_name: bounded_fanout_across_cells_seeds
estimated_parallel_wall_clock_seconds: 5047.5
estimated_serial_wall_clock_seconds: 20167.5
estimated_gpu_seconds: 20167.5
estimated_cost: 8.0234382
one_remote_invocation_per_row_cost: 9.4556622
one_remote_invocation_per_cell_cost: 9.4556622
one_remote_invocation_per_grammar_mode_shard_cost: 7.8444102
single_full_plan_invocation_cost: 7.4863542
bounded_fanout_across_cells_seeds_cost: 8.0234382
warning_flags: advisory_only_not_experimental_evidence, stage_timing_inputs_estimated_not_measured
```

Recommended caps:

```text
max_rows: 12
max_generation_attempts: 72
max_correctness_calls: 72
max_wall_clock: 4 hours
max_estimated_cost: USD 25
max_reconciled_billing_cost: USD 50
stop_on_first_infrastructure_failure: yes
retry_policy: no retry and no resume unless explicitly signed
```

Signability status:

`SIGNABLE_ADVISORY_PRICING_VERIFIED_TIMING_ESTIMATED`, pending human acceptance
of the estimated timing inputs. It is not experimental evidence and does not
replace JSONL rows, observability sidecars, analyzer outputs, or Modal billing
reconciliation.

## Stop/Spend Limits

The packet now marks stop/spend limits as ready for signature but inactive
until the human signer approves them:

- rows: 12;
- generation attempts: 72;
- correctness calls: 72;
- wall clock: 4 hours;
- estimated advisory cap: USD 25;
- reconciled billing cap: USD 50;
- stop on first infrastructure failure: yes;
- retry/resume: no retry and no resume unless explicitly signed.

## Billing Authorization

Billing query authorization is scoped to post-run L1a reconciliation only after
a signed run exists and a signed start/end UTC window can be named. No billing
query was run in this branch.

## Output/Artifact/Mlruns Mutation Authorization

Output, artifact, and `mlruns/` mutation remain inactive because the packet is
not signed and the remote image digest is blocked. The packet records only the
future L1a namespace scope:

- `outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- planned analysis/report/billing/MLflow-index namespaces listed in the packet.

## Post-Run Validation Authorization

The exact post-run validation command surfaces are ready for signature but not
active. They require real post-run artifacts and a signed packet before use:

- schema and row-count validation;
- content-hash sidecar validation;
- observability sidecar validation;
- grammar-mode consistency validation;
- analyzer/report command surface;
- billing reconciliation after signed run window.

## Exact Execution Command

Still not authorized:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED --overwrite
```

The signed authorization placeholder must be replaced by a final signed packet
id before execution.

## No-Generation Proof

Commands run in this branch were limited to git inspection, text/file
inspection, Modal CLI/API help/list/app-registration metadata inspection,
official pricing lookup, local estimator calculation, packet editing, and audit
authoring.

No command invoked:

- `cluster3.experiments.run_cluster3_modal`;
- `RemoteC2Generator.generate_one`;
- `remote_c2_correctness.remote`;
- generation adapters;
- correctness adapters;
- paper-scale experiments;
- benchmarks or profilers.

Modal app-list verification showed all inspection apps stopped with `Tasks: 0`.

## No-Output/Mlruns Mutation Proof

No output, artifact, or `mlruns/` path was intentionally written. Protected-path
validation must remain empty before commit:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

## Remaining Blockers

- Remote Modal image digest or explicitly signed alternative stable Modal image
  provenance policy is still required.
- Human signature is still absent.
- `approval_record_commit` must be filled after the final signed packet commit.
- The exact signed run id and billing reconciliation time window must be filled
  before any post-run billing collection.
- Output/artifact/mlruns mutation remains inactive until final signature.

## Classification

`L1A_EXPEDITED_SIGNATURE_BLOCKED_REMOTE_DIGEST`

## Next-Step Recommendation

Do not run L1a yet. The next narrow step is to decide the Modal provenance
policy: either identify a Modal-supported no-generation command/API that
returns the image digest, or explicitly sign an alternate stable Modal
image/object provenance policy for L1a. After that, patch only the remote image
digest/provenance field and `approval_record_commit` policy before requesting a
human execution signature.
