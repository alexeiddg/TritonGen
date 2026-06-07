# L2b Full-Coverage Plan And Selector Report

## Summary

status: `L2B_FULL_COVERAGE_PLAN_READY_FOR_REVIEW`
branch: `codex/l2b-full-coverage-plan-and-selector`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
AUTHORIZES_EXECUTION: NO

This audit records the L2b planning branch for expanded
`grammar_mode x C x P x kernel_class x dtype` coverage. The branch adds
planning docs and local selector/profile support only. It does not run Modal,
GPU work, generation, billing, analyzer/report refresh, Fireworks API calls, or
any experiment.

## Files Added Or Updated

New planning artifacts:

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_full_coverage_authorization_packet.md`
- `docs/implementation_plans/l2b_full_coverage_fireworks_ready_modal_plan.md`
- `audits/l2b_full_coverage_plan_and_selector_report.md`

Local selector/profile support:

- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Handoff records:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Repo-Backed Matrix Scope

Kernel classes:

```text
elementwise
reduction
matmul
```

Evidence:

- `shared/eval/correctness_shapes.py` defines `LOCKED_KERNEL_CLASSES`.
- The same module maps those classes to `relu`, `softmax`, and `gemm`.

Dtype variants:

```text
fp32
fp16
bf16
```

Evidence:

- `cluster2/constants.py` defines `DTYPE_NAMES`.
- `shared/eval/tolerances.py` contains per-kernel-class/per-dtype tolerances.

No new kernel names, dtypes, tolerances, or numerical semantics were invented.

## Expanded Matrix Count

```text
grammar_mode values: 3
C states: 2
P states: 2
causal_control_cells: 12
kernel_classes: 3
dtype_variants: 3
expanded_cells: 108
n_per_expanded_cell: 20
total_planned_rows: 2160
rows_per_kernel_class: 720
rows_per_dtype_variant: 720
rows_per_kernel_dtype_pair: 240
rows_per_causal_control_file: 180
```

## Selector/Profile Status

Added L2b constants:

```text
L2B_OUTPUT_ROOT
L2B_OBSERVABILITY_ROOT
L2B_RUN_ID_PREFIX
L2B_SIGNED_AUTHORIZATION_PLACEHOLDER
L2B_EXECUTABLE_SELECTOR_SUPPORT_STATUS
L2B_DRY_PLAN_PLACEHOLDER_OUTPUT
L2B_EXECUTION_SELECTOR_PLACEHOLDER_OUTPUT
```

Added profile:

```text
label: L2b n=20 full coverage local plan
scale_tier: paper
n: 20
kernel_class_selector: all
dtypes: fp32, fp16, bf16
expected_planned_rows: 2160
runtime_execution_enabled: false
runtime_block_reason: L2b full coverage is planning-only; no signed execution token exists
signed_authorization_token: none
support_status: L2B_LOCAL_PLAN_ONLY_RUNTIME_DISABLED_NO_SIGNED_TOKEN
```

Profile selection now preserves existing L2a behavior for
`paper/n=20/elementwise/fp32` and selects L2b only for the explicit
`paper/n=20/all/fp32,fp16,bf16` local planning surface.

Runtime remains fail-closed because no approved token maps to the L2b profile.

## L2a Live Job Protection

The current checkout used to create this branch was not switched away from the
existing user workspace. This branch was created in an isolated worktree at:

```text
/private/tmp/tritongen-l2b-full-coverage-plan-and-selector
```

L2b namespaces are separate from live L2a namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_full_coverage_n20
```

The branch must not mutate:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
mlruns
```

## Fireworks API Boundary

This branch plans Fireworks compatibility only. It adds no Fireworks client,
dependency, key handling, network call, provider billing call, retry policy, or
runtime execution code.

Future Fireworks work should use a separate packet for:

- backend abstraction boundary;
- provider config metadata;
- prompt/generation request metadata;
- disabled provider-side retry unless signed later;
- sidecar-only provider cost/billing metadata.

## Validation Performed

Focused selector tests:

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Result:

```text
193 passed
```

The isolated worktree does not contain the ignored `.venv/` directory, so the
same repository virtualenv was invoked by absolute path while keeping the
working directory on this branch.

Additional required validation to run before review closeout:

```bash
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

## No-Execution Proof

No command in this branch invoked:

```text
modal
cluster3.experiments.run_cluster3_modal without --dry-plan or --execution-plan
generation adapters
correctness execution against GPU
billing report
analyzer/report refresh
Fireworks API
```

Protected mutation scan requirement:

```text
outputs: empty diff
artifacts: empty diff
mlruns: empty diff
docs/preliminary_report: empty diff
dependency files: empty diff
lockfiles: empty diff
```

## Remaining Blockers

No repo naming ambiguity remains for the planned L2b matrix. Remaining items are
execution-stage prerequisites, not blockers for plan review:

- no signed L2b execution token exists;
- no L2b Modal/GPU/generation/billing authorization exists;
- no L2b output exists;
- analyzer/report strictness remains future post-run work;
- Fireworks API integration remains a future backend abstraction.

## Classification

`L2B_FULL_COVERAGE_PLAN_READY_FOR_REVIEW`

## Next Step

Review this planning branch. If accepted, draft a separate staged L2b run packet
for one 240-row kernel_class x dtype stratum before authorizing any execution.
