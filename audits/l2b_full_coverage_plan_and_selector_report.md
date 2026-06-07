# L2b Sharded Full-Coverage Plan And Selector Report

## Summary

status: `L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE`
branch: `codex/l2b-full-coverage-plan-and-selector`
baseline_commit: `4b85c246795f4b6042852dfeb7219c053cc77760`
AUTHORIZES_EXECUTION: NO

This audit records the amended L2b planning branch. The branch now implements a
mandatory sharded model and compressed ladder:

```text
L2b-0: local planning/selector support only
L2b-2: full repo-backed coverage at n=2
L2b-4: same coverage at n=20, unsigned and blocked on L2b-2 validation
```

No Modal/GPU/generation/billing/output/artifact/mlruns mutation, analyzer/report
refresh, Fireworks API call, dependency change, lockfile change, retry, or
resume was performed.

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

- L2b-2 is unsigned until reviewed and signed.
- L2b-4 is unsigned and blocked on L2b-2 completion and validation.
- No L2b output/artifact/billing/analyzer/report evidence exists.
- Fireworks API integration remains TODO-only.

## Classification

`L2B_COMPRESSED_FULL_COVERAGE_PLAN_READY_FOR_SIGNATURE`

## Next Step

Review and, if accepted, sign only the L2b-2 n=2 packet. Do not sign or run
L2b-4 until L2b-2 completes and validates cleanly.
