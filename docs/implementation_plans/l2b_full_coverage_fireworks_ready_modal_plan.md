# L2b Full-Coverage Fireworks-Ready Modal Plan

## Status

status: `PLAN_ONLY_LOCAL_SELECTOR_SUPPORT`
branch: `codex/l2b-full-coverage-plan-and-selector`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
AUTHORIZES_EXECUTION: NO

This plan expands the current L2a `elementwise/fp32` n=20 design into an L2b
full-coverage matrix while preserving the live L2a branch and paths.

Forbidden in this branch:

```text
Modal execution
GPU execution
generation
experiment execution
billing query
output mutation
artifact mutation
mlruns mutation
analyzer refresh
report refresh
Fireworks API calls
dependency or lockfile changes
profiler, benchmark, speedup, timing, or performance claims
```

## Repo-Backed Scope

Kernel classes come from `shared/eval/correctness_shapes.py`:

| kernel_class | kernel_name | shape pattern |
|---|---|---|
| `elementwise` | `relu` | `ND` |
| `reduction` | `softmax` | `RxC` |
| `matmul` | `gemm` | `MNK` |

Dtype variants come from `cluster2/constants.py`:

```text
fp32
fp16
bf16
```

The current tolerance table in `shared/eval/tolerances.py` already contains
per-kernel-class/per-dtype tolerances for these three repo-backed kernel
classes and dtypes. This branch does not alter numerical semantics or
tolerances.

## Expanded Matrix Definition

Base causal/control matrix:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

Expansion:

```text
12 grammar/C/P cells
x 3 kernel classes
x 3 dtype variants
= 108 expanded cells
```

Rows:

```text
n_per_expanded_cell: 20
total_planned_rows: 2160
rows_per_kernel_class: 720
rows_per_dtype_variant: 720
rows_per_kernel_dtype_pair: 240
rows_per_causal_control_file: 180
```

## Selector/Profile Support

Add a local-only profile:

```text
label: L2b n=20 full coverage local plan
scale_tier: paper
n: 20
kernel_class_selector: all
dtypes: fp32, fp16, bf16
expected_planned_rows: 2160
runtime_execution_enabled: false
signed_authorization_available: false
support_status: L2B_LOCAL_PLAN_ONLY_RUNTIME_DISABLED_NO_SIGNED_TOKEN
```

Dry-plan command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution-plan command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class all --scale-tier paper --n 20 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Runtime execution remains fail-closed because no approved L2b token exists and
the profile has `runtime_execution_enabled=false`.

## Namespace Plan

Output root:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
```

Observability root:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
```

Future analysis/report/billing roots:

```text
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20*
```

This intentionally avoids the live L2a `l2_n20` paths.

## Fireworks-Ready Boundary

The planner should not know whether future generation comes from the current
Modal-backed local entrypoint or a Fireworks API backend. The reusable boundary
is metadata and configuration only:

| Future surface | L2b planning rule |
|---|---|
| Backend abstraction | Defer to a later provider interface; do not add a client here. |
| Provider config | Represent provider/model fields explicitly in run packets. |
| Request metadata | Preserve model id, revisions, grammar mode, prompt hash, seed, temperature, max tokens, kernel_class, dtype, and base_seed. |
| Retry policy | Keep retries disabled unless a future packet signs a provider retry policy. |
| Cost/billing | Keep provider billing metadata sidecar-only and post-hoc. |
| Secrets | Do not add API keys, environment reads, or secret handling in this branch. |

No Fireworks package, API key, network call, or runtime path is added.

## Stop And Spend Planning

Unsigned full-matrix stop ceiling:

```text
max_rows: 2160
max_generation_attempts: 12960
max_correctness_calls: 12960
max_wall_clock_full_matrix: 216h
retry_policy: no retry
resume_policy: no resume
```

Unsigned spend ceiling:

```text
l2b_linear_reference_from_l2a_usd: 76.99663224
full_l2b_max_estimated_cost_before_launch_usd: 500
full_l2b_max_reconciled_billing_cap_usd: 750
per_240_row_stratum_estimated_cap_usd: 150
per_240_row_stratum_reconciled_cap_usd: 250
```

Preferred staged path:

1. Validate one 240-row kernel_class x dtype stratum.
2. Validate one 720-row kernel-class slice.
3. Only then consider all 2160 rows.

Each stage requires a separate signed packet.

## Validation Plan

Local validation for this branch:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Protected mutation scan must show no changed files under:

```text
outputs
artifacts
mlruns
docs/preliminary_report
dependency files
lockfiles
```

## Analyzer/Report Plan

No analyzer/report refresh is allowed in this branch. Future L2b analysis
should require:

```text
scale_tier: paper
analysis_scope: primary_functional
controls: kernel_class, dtype
grammar_mode_summary.status: explicit_grammar_mode
row_count: 2160
reportable: true only after strict analyzer validation
```

Do not collapse `template_upper_bound` and `task_agnostic` into a binary grammar
claim. Do not make profiler, speedup, cost-per-success, or performance claims.

## Acceptance Criteria

`L2B_FULL_COVERAGE_PLAN_READY_FOR_REVIEW` when:

- matrix and row counts are explicit;
- kernel_class and dtype names are repo-backed;
- L2b paths are separate from L2a;
- local dry-plan and execution-plan represent 2160 planned rows;
- runtime remains disabled and unsigned;
- Fireworks API compatibility is planned but not implemented;
- protected L2a outputs/artifacts are untouched.
