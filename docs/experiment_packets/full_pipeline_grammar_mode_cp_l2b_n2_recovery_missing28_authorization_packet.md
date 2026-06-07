# Full Pipeline L2b-2 Recovery Missing-28 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1`
packet_version: `1.0.0-recovery-missing28`
packet_type: recovery-only signed L2b-2 authorization packet
status: `FINAL_SIGNED_L2B_N2_RECOVERY_MISSING28`
target_baseline: `136a8b07cc9043200de73a91be4803b59817cac4`
execution_code_target_commit: `136a8b07cc9043200de73a91be4803b59817cac4`
target_branch: `codex-track-handoff-context`
classification: `L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_READY`
AUTHORIZES_EXECUTION: YES_L2B_N2_RECOVERY_MISSING28_ONLY

Current archived state:

```text
current terminal classification:
- L2B_N2_PARTIAL_ARTIFACTS_ARCHIVED_SLOW_CELL_STOP
- L2B_N2_TERMINAL_PARTIAL_SLOW_CELL_STOP
archived run commit: 136a8b07cc9043200de73a91be4803b59817cac4
planned rows: 216
observed rows: 188
missing rows: 28
complete shards: 6
partial shards: 3
stopped shard/cell: matmul__fp32/template_upper_bound__c_on__p_off
```

This packet is **recovery-only** and does not authorize L2b-4, L3, retry, resume, or overwrite.

## Target Baseline

```text
current branch: codex-track-handoff-context
current head commit: 136a8b07cc9043200de73a91be4803b59817cac4
parent archived run token: 78ea17b61c46f9ce8c6fb27ad82ddb7b8a82b40a / 136a8b0 archive commit
archived run classification: L2B_N2_TERMINAL_PARTIAL_SLOW_CELL_STOP
runtime_mlfow_requirement: TRITONGEN_MLFLOW=0
```

## Recovery Scope (exact)

Authorized recovery scope:

```text
n=2 only
exact partial shard count: 3
exact partial cell-instance count: 14
exact row target: 28
exact total after recovery: 216
shards:
- reduction__fp16 (4 missing cells)
- reduction__bf16 (4 missing cells)
- matmul__fp32 (6 missing cells)
```

Missing rows by shard/cell:

```text
reduction__fp16:
- task_agnostic__c_off__p_off: 2
- task_agnostic__c_on__p_off: 2
- task_agnostic__c_off__p_on: 2
- task_agnostic__c_on__p_on: 2
Total: 8

reduction__bf16:
- task_agnostic__c_off__p_off: 2
- task_agnostic__c_on__p_off: 2
- task_agnostic__c_off__p_on: 2
- task_agnostic__c_on__p_on: 2
Total: 8

matmul__fp32:
- template_upper_bound__c_off__p_on: 2
- template_upper_bound__c_on__p_on: 2
- task_agnostic__c_off__p_off: 2
- task_agnostic__c_on__p_off: 2
- task_agnostic__c_off__p_on: 2
- task_agnostic__c_on__p_on: 2
Total: 12
```

No completed shard IDs or completed cell IDs are included.

## Runtime and Namespace Constraints

Authorized namespaces:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28*
```

Failure policy:

```text
fail_if_recovery_target_path_exists: true
fail_if_base_archive_missing: true
fail_if_base_archive_changed: true (if hashes are available)
fail_if_any_non_missing_row_is_planned: true
fail_if_duplicate_logical_row_key: true
no completed shards
no completed cells
no n=20
no L2b-4
no retry
no resume
no overwrite
```

Append-only behavior is required: do not mutate existing archives under
`outputs/cluster3/.../l2b_n2/` or `artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2/`.

## Exact Future Command Bundle

Recovery dry-plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector all --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Recovery execution-plan:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector all --kernel-class all --scale-tier development --n 2 --dtypes fp32,fp16,bf16 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Exact recovery command (3-shard recovery):

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal \
  --condition grammar_mode_cp_12cell \
  --l2b-stage l2b_n2_full_coverage \
  --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1 \
  --l2b-shard-selector reduction__fp16 \
  --l2b-recovery-cells task_agnostic__c_off__p_off,task_agnostic__c_on__p_off,task_agnostic__c_off__p_on,task_agnostic__c_on__p_on \
  --kernel-class reduction --scale-tier development --n 2 --dtypes fp16 \
  --repair-history-policy agentic_transcript_v1 \
  --overwrite
```

(and equivalent commands for `reduction__bf16` with `--kernel-class reduction --dtypes bf16`, and `matmul__fp32` with `--kernel-class matmul --dtypes fp32`)

Optional one-shard template:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --l2b-stage l2b_n2_full_coverage --l2b-shard-selector <shard_id> --l2b-recovery-cells <cell_selector> --kernel-class <kernel_class> --scale-tier development --n 2 --dtypes <dtype_variant> --repair-history-policy agentic_transcript_v1 --signed-l2b-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2B_N2_RECOVERY_MISSING28_AUTHORIZATION_PACKET_V1 --overwrite
```

Post-recovery validation commands (authorized only after signed recovery completion/stop):

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
TRITONGEN_MLFLOW=0 .venv/bin/python -m compileall -q cluster3 shared
```

Combined logical validation command:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python - <<'PY'
import json
from pathlib import Path

base_root = Path('outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2')
recovery_root = Path('outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28')
shards = {
    'elementwise__fp32': ('elementwise__fp32', 24),
    'elementwise__fp16': ('elementwise__fp16', 24),
    'elementwise__bf16': ('elementwise__bf16', 24),
    'reduction__fp32': ('reduction__fp32', 24),
    'reduction__fp16': ('reduction__fp16', 24),
    'reduction__bf16': ('reduction__bf16', 24),
    'matmul__fp32': ('matmul__fp32', 24),
    'matmul__fp16': ('matmul__fp16', 24),
    'matmul__bf16': ('matmul__bf16', 24),
}

def read_rows(root: Path, shard: str) -> int:
    rows = 0
    for file in root.glob(f'{shard}/*.jsonl'):
        for line in file.read_text(encoding='utf-8').splitlines():
            json.loads(line)
            rows += 1
    return rows

seen = set()
total = 0
for shard, expected in shards.items():
    base = read_rows(base_root, shard)
    rec = read_rows(recovery_root, shard)
    total += base + rec
    missing = expected - (base + rec)
    if missing != 0:
        raise SystemExit(f'{shard} missing {missing}')

print(f'combined rows: {total}')
if total != 216:
    raise SystemExit(f'expected 216 rows, found {total}')
PY
```

Analyzer/report commands are authorized only after the above combined validation passes.

Billing reconciliation command template (after a redacted report window and with post-run authorization):

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python - <<'PY'
from pathlib import Path
from shared.observability.billing_reconciliation import (
    parse_redacted_billing_report,
    reconcile_billing_records_to_run,
)

target_runs = [
    Path('outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n2_recovery_missing28/<shard_id>')
]
redacted_report = Path('artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/billing_redacted_<window>.json')
print('run only after redacted report and authorization')

total_cost = 0.0
for root in target_runs:
    if root.exists():
        _, total_cost = reconcile_billing_records_to_run(
            run_root=root,
            redacted_report=parse_redacted_billing_report(redacted_report),
        )
        print(root, total_cost)
PY
```

## Stop/Execution Limits

```text
max_recovery_rows: 28
max_recovery_shards: 3
max_rows_per_recovery_shard:
  reduction__fp16: 8
  reduction__bf16: 8
  matmul__fp32: 12
max_total_combined_rows_after_recovery: 216
L2B_N2_SIGNED_WALL_CLOCK_SECONDS_PER_CELL: 1800
no retry
no resume
no overwrite
```

## Spend And Concurrency Limits

```text
max_gpu_concurrency: 3
max_container_concurrency: 30
max_estimated_cost_usd: 75.00
max_reconciled_billing_cost_usd: 90.00
carry forward Modal empty-tag UTC-window caveat
```

## Slow-Cell Policy

```text
Known high-cost cells:
- matmul__fp32/template_upper_bound__c_on__p_off already exceeded 1800s
- matmul__fp32/task_agnostic__c_on__p_on may be high risk
- reduction task_agnostic cells may be high risk
If a recovery cell exceeds signed budget, finish active row if safe, stop recovery,
classify L2B_N2_RECOVERY_TERMINAL_SLOW_CELL_LIMIT, and preserve partial audit.
No automatic retry.
No automatic resume.
```

## Runtime Signature Block

```text
AUTHORIZES_EXECUTION: YES_L2B_N2_RECOVERY_MISSING28_ONLY
MODAL_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
GPU_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
GENERATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
EXPERIMENT_EXECUTION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_ONLY
OUTPUT_MUTATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_NAMESPACE_ONLY
ARTIFACT_MUTATION_AUTHORIZED: YES_L2B_N2_RECOVERY_MISSING28_NAMESPACE_ONLY
BILLING_QUERY_AUTHORIZED: YES_L2B_N2_RECOVERY_RECONCILIATION_ONLY_AFTER_RUN
POST_RUN_VALIDATION_AUTHORIZED: YES_LISTED_COMMANDS_ONLY
OVERWRITE_AUTHORIZED: NO
RETRY_AUTHORIZED: NO
RESUME_AUTHORIZED: NO
L2B_N20_AUTHORIZED: NO
L2B_4_AUTHORIZED: NO
L3_AUTHORIZED: NO
SIGNATURE_STATUS: SIGNED_FOR_L2B_N2_RECOVERY_MISSING28_ONLY
```

If any field in this block cannot be made explicit in execution tooling, execution
must remain blocked with `AUTHORIZES_EXECUTION: NO`.
