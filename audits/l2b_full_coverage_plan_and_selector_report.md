# L2b Sharded Full-Coverage Plan And Selector Report

## Summary

status: `L2B_PLANNING_RECONCILED_READY_FOR_L2B2_SIGNATURE`
report_version: `2.0.1`
branch: `codex/l2b-full-coverage-plan-and-selector`
baseline_commit: `9974770 Promote Fireworks Modal planning doc`
promoted_planning_commit: `8b26951e37cde7eab5497f2a35860b95da067302`
AUTHORIZES_EXECUTION: NO

This audit records the reconciled L2b planning branch. The branch is now replayed
onto current `codex-track-handoff-context` at `9974770 Promote Fireworks Modal
planning doc` and implements a mandatory sharded model and compressed ladder:

```text
L2b-0: local planning/selector support only
L2b-2: full repo-backed coverage at n=2
L2b-4: same coverage at n=20, unsigned and blocked on L2b-2 validation
```

No Modal/GPU/generation/billing/output/artifact/mlruns mutation, analyzer/report
refresh, Fireworks API call, dependency change, lockfile change, retry, or
resume was performed.

The separate final unsigned L2b-2 packet now pins `SIGNED_TARGET_COMMIT` to
promoted planning commit `8b26951e37cde7eab5497f2a35860b95da067302`. It remains
unsigned and does not authorize execution.

## Current Trunk Context

The signed L2a n=20 attempt is preserved at `04d2eef Record failed L2 n20
validation` as an incomplete wall-clock/slow-tail run, not as a scientific
evidence failure:

```text
expected rows: 240
completed rows: 228
partial cell: task_agnostic__c_on__p_on
partial cell rows: 8 of 20
```

Analyzer/report refresh remains blocked. Retry, resume, overwrite, rerun,
paper-scale claims, benchmark, speedup, and cost-per-success work remain blocked
unless separately authorized. L2b planning does not modify the preserved L2a
output, observability, billing, report, analysis, or `mlruns` surfaces.

## Files Added Or Updated

Planning artifacts:

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_full_coverage_authorization_packet.md`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n2_full_coverage_authorization_packet.md`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l2b_n20_full_coverage_authorization_packet.md`
- `docs/implementation_plans/l2b_full_coverage_fireworks_ready_modal_plan.md`
- `audits/l2b_full_coverage_plan_and_selector_report.md`

Local selector/profile support:

- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_grammar_mode_matrix.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Handoff records:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Repo-Backed Discovery

Kernel classes are discovered from `shared/eval/correctness_shapes.py`:

```text
elementwise
reduction
matmul
```

Dtype variants are discovered from `cluster2/constants.py`:

```text
fp32
fp16
bf16
```

No naming ambiguity remains, and no new kernel/dtype names were invented.

## Shard Contract

Each shard is exactly:

```text
shard_id = <kernel_class>__<dtype_variant>
```

The deterministic order is:

```text
elementwise__fp32
elementwise__fp16
elementwise__bf16
reduction__fp32
reduction__fp16
reduction__bf16
matmul__fp32
matmul__fp16
matmul__bf16
```

Each shard has 12 planned grammar/C/P cells and independent output,
observability, analysis, report, and billing namespaces.

## Row Counts

| Rung | Selector profile | n | rows_per_shard | total_shards | full_matrix_rows |
|---|---|---:|---:|---:|---:|
| L2b-2 | `l2b_n2_full_coverage` | 2 | 24 | 9 | 216 |
| L2b-4 | `l2b_n20_full_coverage` | 20 | 240 | 9 | 2160 |

Execution-plan payloads also report `selected_shard_count` and
`total_planned_rows` for all-shard, one-shard, or bounded-wave selections.

## Namespace Plan

For `N in {2, 20}`:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n{N}/<shard_id>*
```

The payload and shard entries report:

```text
fail_if_any_target_path_exists: true
writes_outputs: false
writes_artifacts: false
writes_mlruns: false
```

## Selector/Profile Status

Added local-only selector arguments:

```text
--l2b-stage {l2b_n2_full_coverage,l2b_n20_full_coverage}
--l2b-shard-selector all
--l2b-shard-selector <kernel_class>__<dtype_variant>
--l2b-shard-selector wave:<start>:<count>
--signed-l2b-authorization <token>
```

Runtime remains fail-closed because no signed L2b token is registered. The
placeholder `SIGNED_L2B_PACKET_NOT_APPROVED` parses as a command-shape draft but
is not an approved authorization token.

The L2b-2 packet is now the only final unsigned signature-ready L2b packet.
L2b-4 remains unsigned and blocked on L2b-2 validation.

Existing L2a `paper/n=20/elementwise/fp32` selector behavior remains separate
from explicit L2b profiles.

## Concurrency Plan

L2b-2:

```text
max_gpu_concurrency <= 4
max_container_concurrency <= 40
```

L2b-4:

```text
first_wave_max_gpu_concurrency <= 4
first_wave_max_container_concurrency <= 40
second_wave_after_first_wave_validation_max_gpu_concurrency <= 8
second_wave_after_first_wave_validation_max_container_concurrency <= 80
```

Do not use 10 GPUs or 100 containers unless L2b-2 passes and the first L2b-4
wave validates cleanly.

## Timing Observability And Slow Cells

The L2b plan now records per-cell and per-shard timing diagnostics as
sidecar-only metadata. These fields are planning/runtime observability metadata,
not scientific result rows, analyzer inputs, report evidence, profiler data,
benchmark data, speedup evidence, or performance evidence.

Required diagnostics:

```text
wall_clock_seconds_per_row
generation_attempt_count
compile_attempt_count
correctness_call_count
p_repair_attempt_count
c_repair_attempt_count
terminal_failure_type
timeout_or_stop_reason if applicable
```

Permitted use is limited to operational budgeting and identifying slow cells.
Speedup, performance, throughput, latency, profiler, benchmark, or paper-evidence
claims are explicitly disallowed.

Known high-cost cell:

```text
task_agnostic__c_on__p_on
```

Risk note: `task_agnostic__c_on__p_on` is expected to be the slowest cell
because it combines the broadest grammar mode with both P and C repair pathways.
L2b budget estimates must not assume uniform row time across cells. For L2b
execution design, this is another reason sharding is mandatory: one slow
`task_agnostic__c_on__p_on` path must not block every kernel/dtype result.

The future signed-runtime stop policy is:

```text
signed per-cell wall-clock budget: required
if any single cell exceeds budget: finish active row if safe, stop shard
classification: SLOW_CELL_BUDGET_EXCEEDED
automatic retry: no
automatic resume: no
preserve partial shard audit: yes
```

## Fireworks Boundary

The shard abstraction records:

```text
backend: modal_local_model
future_backend_todo: fireworks_api
```

No Fireworks client, dependency, API key, provider retry, network call, or
provider billing path is implemented.

## L2a Live Job Protection

The original checkout remains separate from this isolated L2b worktree:

```text
/private/tmp/tritongen-l2b-full-coverage-plan-and-selector
```

This branch must not mutate:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
mlruns
```

## Validation Performed

Focused selector tests:

```text
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m pytest cluster3/tests/test_grammar_mode_matrix.py cluster3/tests/test_run_cluster3_modal_cli.py -q
```

Result:

```text
200 passed
```

Additional closeout validation required before final commit:

```bash
/Users/alexeidelgado/Desktop/TritonGen/.venv/bin/python -m compileall -q cluster3 shared
git diff --check
git diff --cached --check
```

## Remaining Blockers

No planning blocker remains. Execution blockers remain:

- L2b-2 is unsigned until reviewed and signed; runtime remains fail-closed.
- L2b-4 is unsigned and blocked on L2b-2 completion and validation.
- A concrete per-cell wall-clock budget is required before any L2b execution
  signature.
- No L2b output/artifact/billing/analyzer/report evidence exists.
- Fireworks API integration remains TODO-only.

## Classification

`L2B_PLANNING_RECONCILED_READY_FOR_L2B2_SIGNATURE`

## Next Step

Promote this reconciled planning/selector branch, then review and sign only the
L2b-2 n=2 packet. Do not launch L2b during reconciliation or packet drafting.
Do not sign or run L2b-4 until L2b-2 completes and validates cleanly.
