# Full Pipeline Grammar-Mode x C x P L2b Full-Coverage Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
packet_version: `0.1.0-plan-only`
packet_type: draft planning packet and local selector/profile support record
branch: `codex/l2b-full-coverage-plan-and-selector`
target_branch: `codex-track-handoff-context`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
status: `DRAFT_NOT_APPROVED_PLAN_ONLY`
signature_status: `UNSIGNED`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
ANALYZER_REFRESH_AUTHORIZED: NO
REPORT_REFRESH_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
FIREWORKS_API_CALLS_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L3_AUTHORIZED: NO
```

This packet designs L2b as the expanded full-coverage successor to the current
L2a `elementwise/fp32` n=20 run. It does not execute L2b, does not query Modal
billing, does not refresh analyzer/report artifacts, does not implement
Fireworks API calls, and does not mutate live L2a paths.

## Live L2a Protection

The current L2a n=20 run may be executing from `codex-track-handoff-context`.
This L2b planning branch must not touch:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
mlruns
```

The L2b proposed namespace is intentionally separate from `l2_n20`.

## L2b Scope

Experiment id:

```text
full_pipeline_grammar_mode_cp_factorial_v1
```

Causal/control cells:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

Repo-backed kernel classes:

```text
elementwise -> relu
reduction -> softmax
matmul -> gemm
```

Sources:

- `shared/eval/correctness_shapes.py` defines `LOCKED_KERNEL_CLASSES` as
  `elementwise`, `reduction`, and `matmul`.
- `shared/eval/correctness_shapes.py` maps those classes to kernel names
  `relu`, `softmax`, and `gemm`.

Repo-backed dtype variants:

```text
fp32
fp16
bf16
```

Source: `cluster2/constants.py` defines `DTYPE_NAMES` as `fp32`, `fp16`, and
`bf16`.

## Expanded Matrix

```text
causal_control_cells: 12
kernel_classes: 3
dtype_variants: 3
expanded_kernel_dtype_cells: 108
n_per_expanded_cell: 20
total_planned_rows: 2160
scale_tier: paper
TRITONGEN_MLFLOW: 0
repair_history_policy: agentic_transcript_v1
retry_policy: no retry
resume_policy: no resume
profiler_or_benchmark_policy: disabled
```

Row-count breakdown:

| Slice | Row count |
|---|---:|
| Per expanded grammar/C/P x kernel_class x dtype cell | 20 |
| Per kernel_class x dtype pair | 240 |
| Per kernel_class | 720 |
| Per dtype variant | 720 |
| Full L2b matrix | 2160 |

The 108 expanded cells are the Cartesian product of 12 causal/control cells,
3 kernel classes, and 3 dtype variants.

## Local Selector/Profile Surface

This branch adds a local-only L2b selector/profile for:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

and:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Expected local payload properties:

```text
authorization_profile: L2b n=20 full coverage local plan
cell_count: 12
planned_rows: 2160
kernel_class_selector: all
kernel_classes: elementwise, reduction, matmul
dtypes: fp32, fp16, bf16
execution_authorized: false
runtime_execution_enabled: false
signed_authorization_available: false
writes_outputs: false
writes_artifacts: false
writes_mlruns: false
support_status: L2B_LOCAL_PLAN_ONLY_RUNTIME_DISABLED_NO_SIGNED_TOKEN
```

No signed L2b token is defined. Runtime execution must fail closed until a
separate future packet explicitly signs an L2b token, stop limits, spend limits,
target commit, and validation bundle.

## Proposed Namespaces

Future output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
```

Future artifact namespaces:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
```

Target paths must be absent before any future signed launch. The path collision
policy remains:

```text
fail_if_any_target_path_exists: true
```

## Proposed Stop Limits

These limits are planning values only and are not signed:

```text
max_rows: 2160
max_generation_attempts: 12960
max_correctness_calls: 12960
max_p_repair_attempts_per_row: 5
max_c_repair_attempts_per_row: 5
max_wall_clock_full_matrix: 216h
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
abort_if_row_count_exceeds: 2160
abort_if_command_requests_l2a_l3_or_non_l2b_namespace: true
abort_if_runtime_mlflow_tracking_enabled: true
```

Rationale: L2a signs 240 rows with 1440 generation and correctness calls and a
24h wall-clock cap. L2b is 9x the L2a row count, so the linear full-matrix
planning ceiling is 2160 rows, 12960 generation calls, 12960 correctness calls,
and 216h. This is too large for a single first launch without separate review;
the staged plan below is preferred.

Stop immediately on target-path collision, row-count mismatch, missing hash
sidecar, missing observability sidecar, P firing in no-P controls, C firing
outside eligible F2 routing, private-eval leakage, profiler/timing/speedup
leakage, dependency/lockfile drift, model/tokenizer drift, grammar drift,
repair-policy drift, or any output/artifact path outside the future L2b
namespace.

## Proposed Spend Limits

These planning values are advisory and unsigned:

```text
l1b_utc_window_cost_usd: 2.13879534
l2a_linear_reference_from_l1b_usd: 8.55518136
l2b_linear_reference_from_l2a_usd: 76.99663224
full_l2b_max_estimated_cost_before_launch_usd: 500
full_l2b_max_reconciled_billing_cap_usd: 750
per_240_row_stratum_estimated_cap_usd: 150
per_240_row_stratum_reconciled_cap_usd: 250
billing_reconciliation_source_of_truth: actual Modal billing report after run
```

The L1b billing caveat carries forward: Modal tags were empty, so future
billing evidence must reconcile to a UTC window and preserve empty-tag caveats
unless tags are demonstrably populated. This packet performs no billing query.

## Staged Execution Option

Recommended future staging, if L2b is later signed:

1. Run one 240-row kernel_class x dtype stratum first, preferably
   `elementwise/fp32` only if L2a has not already supplied compatible evidence
   in the same signed namespace, otherwise pick the next highest-value stratum.
2. Promote to one full kernel class only after the 240-row stratum validates.
   One kernel class is 720 rows.
3. Promote to all 2160 rows only after output validation, analyzer strictness,
   billing reconciliation, and no-retry/no-resume policy are accepted for the
   prior stage.

Each stage needs its own explicit signed packet. This packet signs none.

## Validation Plan

Local pre-review validation for this branch:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Future post-run validation, only after a separately signed L2b execution:

```text
12 JSONL files under the L2b output namespace
2160 total rows
180 rows per causal/control file
20 rows per grammar/C/P x kernel_class x dtype expanded cell
3 kernel_class values: elementwise, reduction, matmul
3 dtype values: fp32, fp16, bf16
content-hash sidecars valid for all output files
observability event, summary, and hash sidecars valid for all files
no P activity in no-P controls
C/P activity only in eligible rows
mlruns absent unless separately authorized
```

Analyzer/report plan:

```text
analysis_scope: primary_functional
scale_tier: paper
controls: kernel_class, dtype
grammar_mode_summary.status: explicit_grammar_mode
no binary grammar collapse for template_upper_bound and task_agnostic
reportable: true only if strict paper-scale analyzer validation passes
```

No analyzer or report command is authorized by this packet.

## Fireworks API Compatibility Boundary

L2b should remain compatible with a later Fireworks API generation backend, but
this branch implements no Fireworks dependency, key handling, network call, or
provider client.

Future TODO boundary:

- introduce a backend abstraction for generation provider selection;
- represent provider config as metadata, not implicit environment defaults;
- record prompt/generation request metadata needed for reproducibility;
- keep provider-side retry disabled unless a later packet signs it;
- keep provider billing/cost metadata sidecar-only and post-hoc;
- preserve JSONL rows as the scientific source of truth.

## No-Execution Proof

This branch is limited to planning docs, local selector/profile planning
metadata, and local tests. It must leave these protected surfaces untouched:

```text
outputs
artifacts
mlruns
docs/preliminary_report
dependency files
lockfiles
```

## Classification

`L2B_FULL_COVERAGE_PLAN_READY_FOR_REVIEW`

## Next-Step Recommendation

Review the L2b packet and local selector/profile support. Do not execute L2b.
If the plan is accepted later, draft a separate signed staged-run packet before
any Modal, GPU, generation, billing, output, artifact, analyzer, or report
operation.
