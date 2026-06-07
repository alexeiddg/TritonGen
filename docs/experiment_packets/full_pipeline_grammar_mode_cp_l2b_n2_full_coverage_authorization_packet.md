# Full Pipeline L2b-2 n=2 Sharded Full-Coverage Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1`
packet_version: `1.1.0-final-signed-l2b-n2-only`
packet_type: final signed L2b-2 authorization packet
target_branch: `codex-track-handoff-context`
execution_code_target_commit: `eab664f560404cc40e309caa8d4202346452ecc3`
planning_commit: `8b26951e37cde7eab5497f2a35860b95da067302`
selector_profile_id: `l2b_n2_full_coverage`
rung: `L2b-2`
status: `FINAL_SIGNED_L2B_N2_ONLY`
classification: `L2B_N2_FINAL_AUTHORIZATION_READY`
AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY

This packet signs L2b-2 only. It does not execute L2b during packet drafting.
It does not sign L2b-4. It does not change runtime launcher behavior in this
commit. The target code still has no registered signed L2b runtime token, so a
separate execution-readiness step must verify or enable only this exact signed
L2b-2 path before the future launch command is run.

## Target Baseline

```text
target branch: codex-track-handoff-context
execution_code_target_commit: eab664f560404cc40e309caa8d4202346452ecc3
execution_code_target_commit_subject: Prepare final L2b-2 authorization packet
planning_commit: 8b26951e37cde7eab5497f2a35860b95da067302
runtime_launcher_change_in_this_packet: no
runtime_MLflow: disabled with TRITONGEN_MLFLOW=0
```

## L2a Context

The prior signed L2a n=20 attempt is preserved at `04d2eef Record failed L2 n20
validation` as an incomplete wall-clock/slow-tail run, not a scientific evidence
failure:

```text
expected rows: 240
completed rows: 228
partial cell: task_agnostic__c_on__p_on
partial cell rows: 8 of 20
```

L2b-2 is a new sharded n=2 coverage step. It is not a retry, resume, overwrite,
rerun, analyzer refresh, report refresh, or paper-claim unlock for L2a.

## Authorized Scope

```text
condition selector: grammar_mode_cp_12cell
grammar_mode values: grammar_off, template_upper_bound, task_agnostic
C states: off, on
P states: off, on
kernel classes: elementwise, reduction, matmul
dtype variants: fp32, fp16, bf16
n: 2
total_shards: 9
planned_cells_per_shard: 12
rows_per_shard: 24
total_planned_rows: 216
repair_history_policy: agentic_transcript_v1
backend: modal_local_model
future_backend_todo: fireworks_api
L2b-4 authorization: no
L3 authorization: no
```

The repo-backed shard set is exactly:

| shard_id | kernel_class | dtype_variant | planned_cells | planned_rows |
|---|---|---|---:|---:|
| `elementwise__fp32` | `elementwise` | `fp32` | 12 | 24 |
| `elementwise__fp16` | `elementwise` | `fp16` | 12 | 24 |
| `elementwise__bf16` | `elementwise` | `bf16` | 12 | 24 |
| `reduction__fp32` | `reduction` | `fp32` | 12 | 24 |
| `reduction__fp16` | `reduction` | `fp16` | 12 | 24 |
| `reduction__bf16` | `reduction` | `bf16` | 12 | 24 |
| `matmul__fp32` | `matmul` | `fp32` | 12 | 24 |
| `matmul__fp16` | `matmul` | `fp16` | 12 | 24 |
| `matmul__bf16` | `matmul` | `bf16` | 12 | 24 |

Any additional kernel class, dtype variant, grammar mode, C/P state, row count,
backend, model revision, tokenizer revision, correctness semantics, C/P
semantics, analyzer gate, report gate, retry, or resume is outside this
signature.

## Authorized Namespaces

Only these L2b-2 per-shard namespaces are authorized for future execution and
post-run validation.

For each `shard_id`:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>*
```

Path policy:

```text
fail_if_any_target_path_exists: true
no retry
no resume
abort on any target namespace outside l2b_n2
abort if any live L2a namespace would be touched
abort if any output, artifact, or mlruns path outside the authorized L2b-2 namespace would be mutated
```

Protected paths that remain forbidden:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
mlruns
docs/preliminary_report
```

## Exact Command Bundle

Dry-plan command, authorized for local planning only:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution-plan command, authorized for local planning only:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Exact future all-shards L2b-2 command authorized by this packet after a separate
runtime-gate readiness step verifies the token/profile/path:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector all --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Exact future one-shard command template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector <shard_id> --kernel-class <kernel_class> --scale-tier development --n 2 --dtypes <dtype_variant> --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Concrete one-shard example:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector elementwise__fp32 --kernel-class elementwise --scale-tier development --n 2 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Exact future bounded-wave command template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector wave:<start>:<count> --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

Concrete bounded first-wave example:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector wave:0:4 --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_FULL_COVERAGE_AUTHORIZATION_PACKET_V1 --overwrite
```

## Post-Run Validation Commands

These commands are authorized only after the signed L2b-2 execution completes or
stops. They are not authorized during packet drafting.

Local test/compile validation:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
TRITONGEN_MLFLOW=0 .venv/bin/python -m compileall -q cluster3 shared
```

L2b-2 shard and row-count validation:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python - <<'PY'
import json
from pathlib import Path

root = Path("outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2")
expected = (
    "elementwise__fp32", "elementwise__fp16", "elementwise__bf16",
    "reduction__fp32", "reduction__fp16", "reduction__bf16",
    "matmul__fp32", "matmul__fp16", "matmul__bf16",
)
total_rows = 0
for shard in expected:
    shard_root = root / shard
    if not shard_root.is_dir():
        raise SystemExit(f"missing shard output namespace: {shard_root}")
    rows = 0
    files = sorted(shard_root.glob("*.jsonl"))
    if len(files) != 12:
        raise SystemExit(f"{shard} expected 12 cell files, found {len(files)}")
    for path in files:
        with path.open(encoding="utf-8") as handle:
            cell_rows = [json.loads(line) for line in handle if line.strip()]
        if len(cell_rows) != 2:
            raise SystemExit(f"{path} expected 2 rows, found {len(cell_rows)}")
        rows += len(cell_rows)
    if rows != 24:
        raise SystemExit(f"{shard} expected 24 rows, found {rows}")
    total_rows += rows
if total_rows != 216:
    raise SystemExit(f"expected 216 total rows, found {total_rows}")
print("L2b-2 row-count validation passed: 9 shards, 216 rows")
PY
```

Analyzer/report command template, one shard at a time:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m shared.analysis.factorial --inputs outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>/*.jsonl --allow-mixed-scale --scale-tier development --analysis-scope primary_functional --output artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>_primary_functional.json --markdown-output artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/<shard_id>_primary_functional.md
```

Billing reconciliation command template, one shard at a time after a separately
approved post-run billing window and redacted/static billing report exist:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python - <<'PY'
import json
from pathlib import Path
from shared.observability.billing_reconciliation import (
    parse_redacted_billing_report,
    reconcile_billing_records_to_run,
)

shard_id = "<shard_id>"
records = parse_redacted_billing_report("<redacted_billing_report.jsonl>")
result = reconcile_billing_records_to_run(
    records,
    experiment_id="full_pipeline_grammar_mode_cp_factorial_v1",
    run_id=f"full_pipeline_grammar_mode_cp_factorial_v1_l2b_n2_full_coverage__{shard_id}",
    time_window=("<run_start_utc>", "<run_end_utc>"),
)
out = Path("artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2") / f"{shard_id}_billing_reconciliation.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result.metadata.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")
PY
```

## Stop Limits

```text
max_total_rows: 216
max_rows_per_shard: 24
max_shards: 9
max_generation_attempts_per_row: 11
max_generation_attempts_per_shard: 264
max_total_generation_attempts: 2376
max_correctness_calls_per_row: 11
max_correctness_calls_per_shard: 264
max_total_correctness_calls: 2376
max_compile_attempts_per_row: 11
max_compile_attempts_per_shard: 264
max_total_compile_attempts: 2376
max_p_repair_attempts_per_p_active_row: 5
max_c_repair_attempts_per_c_active_row: 5
max_wall_clock_seconds_total: 21600
max_wall_clock_seconds_per_shard: 7200
signed_wall_clock_seconds_per_cell: 1800
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
abort_if_rows_exceed_216_total: true
abort_if_any_shard_exceeds_24_rows: true
abort_on_any_target_namespace_outside_l2b_n2: true
abort_on_l2b_n20_path: true
abort_on_l2_n20_path: true
abort_on_mlruns_write: true
```

The attempt ceilings are derived from launcher defaults:
`DEFAULT_P_REPAIR_BUDGET=5`, `DEFAULT_REPAIR_BUDGET=5`, one initial generation
and correctness call, at most five P repair generations/evaluations, and at most
five generated C repair attempts/evaluations.

## Spend And Concurrency Limits

```text
max_gpu_concurrency: 4
max_container_concurrency: 40
max_estimated_cost_usd: 150.00
max_reconciled_billing_cost_usd: 200.00
backend: modal_local_model
runtime_MLflow: TRITONGEN_MLFLOW=0
```

The Modal empty-tag billing caveat carries forward. If Modal billing tags remain
empty or ambiguous, billing attribution may be UTC-window-only and low
confidence. Raw billing output must not be committed. Any post-run billing query
requires the exact UTC window and redaction boundary before it runs.

## Timing Observability

Future L2b-2 execution must emit per-cell and per-shard timing diagnostics as
sidecar metadata only, under the signed shard observability namespace. These
diagnostics must not mutate result-row schemas and must not be used for speedup,
performance, throughput, latency, profiler, benchmark, paper evidence, or
economic claims.

Required sidecar diagnostics:

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

Allowed use is limited to operational budgeting and identifying slow cells.

## Slow-Cell Stop Policy

Known high-cost cell:

```text
task_agnostic__c_on__p_on
```

Risk note: `task_agnostic__c_on__p_on` is expected to be the slowest cell
because it combines the broadest grammar mode with both P and C repair pathways.
L2b budget estimates must not assume uniform row time across cells. For L2b
execution design, this is another reason sharding is mandatory. One slow
`task_agnostic__c_on__p_on` path must not block every kernel/dtype result.

If any single cell exceeds `signed_wall_clock_seconds_per_cell=1800`, finish the
active row if safe, then stop the current shard and classify:

```text
SLOW_CELL_BUDGET_EXCEEDED
```

Do not retry or resume automatically. Preserve the partial shard audit,
including completed rows, sidecar events, terminal failure type, and timeout or
stop reason if applicable.

## L2b-4 Status

L2b-4 remains unsigned and blocked.

```text
L2B_N20_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
L2b-4 signature prerequisite: L2b-2 completes and validates
L2b-4 execution prerequisite: separate signed L2b-4 packet after L2b-2 validation
```

## Signature Block

```text
AUTHORIZES_EXECUTION: YES_L2B_N2_ONLY
MODAL_AUTHORIZED: YES_L2B_N2_ONLY
GPU_AUTHORIZED: YES_L2B_N2_ONLY
GENERATION_AUTHORIZED: YES_L2B_N2_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N2_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N2_NAMESPACES_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N2_NAMESPACES_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N2_RECONCILIATION_ONLY_AFTER_RUN
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L2B_N20_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNED_TARGET_COMMIT: eab664f560404cc40e309caa8d4202346452ecc3
AUTHORIZED_BY: user final L2b-2 signing prompt
AUTHORIZED_AT_UTC: 2026-06-07T02:22:42Z
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_ONLY
```
