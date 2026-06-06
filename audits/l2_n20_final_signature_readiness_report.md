# L2 n=20 Final Signature Readiness Report

## Target Baseline

Current promoted baseline:

```text
branch: codex-track-handoff-context
target_commit: 48efad7 Audit L2 n20 selector profile support promotion
promoted_selector_support_commit: 27493c0 Add L2 n20 selector profile support
```

The target baseline is the current pushed handoff HEAD after fast-forward
promotion and promotion-audit closeout.

## Packet Path

Packet under review:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md
```

The packet path exists and records the L2 n=20 12-cell authorization surface.

## Packet Signature Status

The packet remains unsigned:

```text
signature_status: UNSIGNED
AUTHORIZES_EXECUTION: NO
```

No field in this audit changes the packet into an execution authorization.

## Command Surface

The exact L2 n=20 command surfaces exist in the packet and are now
source-backed by the promoted selector/profile support.

Dry-plan, local no-execution planning:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --dry-plan
```

Execution-plan, local no-execution planning:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --execution-plan
```

Future execution command surface, still blocked until final signature and
runtime-gate enablement:

```bash
TRITONGEN_MLFLOW=0 .venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --kernel-class elementwise --scale-tier paper --n 20 --dtypes fp32 --repair-history-policy agentic_transcript_v1 --signed-l2-authorization FULL_PIPELINE_GRAMMAR_MODE_CP_L2_N20_AUTHORIZATION_PACKET_V1 --overwrite
```

## Matrix And Row Planning

The selected L2 matrix is present:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
planned_cells: 12
n_per_cell: 20
planned_rows: 240
scale_tier: paper
kernel_class: elementwise
dtypes: fp32
```

The grammar-mode mapping remains explicit and does not collapse
`template_upper_bound` and `task_agnostic` into a binary grammar label.

## Stop Limits

Stop limits are present as proposed, unsigned limits:

```text
max_rows: 240
max_generation_attempts: 1440
max_correctness_calls: 1440
max_wall_clock: 24h
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
overwrite_policy: only if all target L2 paths are absent before launch
abort_if_row_count_exceeds: 240
abort_if_command_requests_l1a_l1b_l3_or_non_l2_scope: true
```

These limits are signable fields, not active execution permission.

## Spend Limits

Spend limits are present as proposed, unsigned limits:

```text
pricing_status: must be re-verified before final signature
l1b_utc_window_cost_usd: 2.13879534
l1b_billing_attribution: UTC-window-only because Modal tags were empty
l2_row_scale_factor_from_l1b: 4
rough_l2_linear_cost_reference_usd: 8.55518136
max_estimated_cost_before_launch: USD 150
max_reconciled_billing_cap: USD 250
billing_reconciliation_source_of_truth: actual Modal billing report
```

These fields are adequate for signature review but remain unsigned.

## Output And Artifact Namespaces

Future namespaces are present:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
```

The path policy remains `fail_if_any_target_path_exists`.

## Billing UTC-Window Caveat

The L1b empty-tag billing caveat is carried forward:

```text
l1b_billing_attribution: UTC-window-only because Modal tags were empty
```

Future L2 billing can be authoritative only after a separately signed billing
query window and billing artifact write are authorized and reconciled.

## Post-Run Validation Plan

The post-run validation plan is present and requires:

```text
12 JSONL files
240 total rows
20 rows per cell
explicit grammar_mode values
C/P eligibility checks
content-hash sidecars
observability event, summary, and hash sidecars
mlruns absent unless separately authorized
```

## Analyzer/Report Audit Requirement

The packet requires paper-scale analyzer/report strictness after valid L2
outputs exist:

```text
analysis_scope: primary_functional
scale_tier: paper
reportable: true only if analyzer strictness passes
grammar_mode_summary.status: explicit_grammar_mode
no binary grammar collapse
```

The packet does not permit using L1a smoke or L1b development pair-skip scopes
for L2 paper-scale reporting.

## Runtime Gate

The promoted runner includes the L2 selector profile but keeps runtime execution
disabled:

```text
runtime_execution_enabled: false
runtime_block_reason: L2 n=20 execution remains unsigned
```

Final signature must explicitly decide whether to enable the runtime gate before
any L2 execution can occur.

## Validation Run

Promotion review validation already passed before this audit:

```text
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
176 passed

.venv/bin/python -m compileall -q cluster3 shared
passed

git diff --check
passed
```

Post-promotion alignment check:

```text
HEAD: 48efad7fcfb6ee3e71cedc8fa22fc4ddc1657e62
origin/codex-track-handoff-context: 48efad7fcfb6ee3e71cedc8fa22fc4ddc1657e62
```

## No-Execution Proof

No Modal command was run. No GPU job was run. No generation was run. No L2 n=20
execution was run. No billing query was run. No analyzer/report refresh was
run. No preliminary-report refresh was run. No dependency or lockfile command
was run.

## Protected Mutation Proof

Protected mutation scan remained empty for:

```text
outputs/
artifacts/
mlruns/
docs/preliminary_report/
pyproject.toml
requirements.txt
requirements-dev.txt
uv.lock
poetry.lock
Pipfile.lock
```

## Remaining Blockers Before Execution

- Final human signature is missing.
- The L2 runtime selector profile remains disabled.
- Proposed stop/spend limits must be explicitly signed.
- Pricing must be re-verified or explicitly accepted before signature.
- Billing query window and billing artifact write must be explicitly signed.
- Output/artifact mutation must be explicitly signed.
- Post-run analyzer/report audit must pass before graph/report claims.

## Classification

```text
L2_N20_SELECTOR_SUPPORT_PROMOTED_SIGNATURE_READY
```

## Next-Step Recommendation

Prepare a final signed L2 n=20 authorization packet only if the human signer
accepts the current target baseline, command surface, stop limits, spend limits,
output/artifact namespaces, billing caveat, validation plan, no-retry/no-resume
policy, and runtime-gate enablement. Do not execute L2 from this audit.
