# L2 n=20 Authorization Packet Draft Report

## Executive Summary

This audit created the draft L2 n=20 authorization packet for the 12-cell
`grammar_mode x C x P` experiment and kept it non-authorizing. No Modal, GPU,
generation, L2 execution, n=20 execution, billing query, output mutation,
artifact mutation, MLflow runtime write, dependency change, lockfile change,
preliminary-report refresh, runtime code edit, analyzer/report artifact refresh,
benchmark, profiler, speedup analysis, or cost-per-success analysis was run.

Classification:

`L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE`

The packet is useful as a bounded approval surface, but it is not yet signable.
The current launcher supports selector profiles only for L1a n=1 and L1b n=5.
It rejects `grammar_mode_cp_12cell` planning for `scale_tier=paper`, `n=20`,
and no signed L2 CLI option/token exists.

## L1a Readiness Evidence

Reviewed L1a evidence:

- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/l1a_n1_attempt_006_completion_report.md`
- `audits/l1a_analyzer_patch_and_golden_drift_audit.md`

Relevant committed L1a ladder:

- `61fa0ac Validate L1a n1 12-cell completion`
- `1367cdb Preserve L1a n1 generated artifacts`
- `bc77e9b Audit L1a analyzer patch and golden drift`

L1a established that the 12-cell selector can produce one row per cell under
the signed L1a n=1 scope. L1a remains smoke-scale evidence and cannot be cited
as paper-scale evidence.

## L1b Readiness Evidence

Reviewed L1b evidence:

- `audits/l1b_n5_execution_authorization_report.md`
- `audits/l1b_n5_execution_completion_report.md`
- `audits/l1b_n5_analyzer_dev_scope_patch_report.md`
- `audits/l1b_n5_completion_and_analyzer_boundary_audit.md`

Relevant committed L1b ladder:

- `a52d64a Authorize L1b n5 selector profile`
- `387c073 Complete L1b n5 12-cell validation`
- `134bcf9 Audit L1b n5 completion and analyzer boundary`

L1b produced 60 rows, 12 cells, and five rows per cell. The completion/boundary
audit classified the state as `L1B_N5_AUDIT_PASS_L2_READY` for packet drafting
and review only. The L1b analysis/report remained development-scale and
non-paper.

## Target Baseline

```text
target_branch: codex-track-handoff-context
execution_code_target_commit: 134bcf9c7fda9da933acf6fe3f93766b2b0a731e
baseline_commit: 134bcf9 Audit L1b n5 completion and analyzer boundary
draft_branch: codex/l2-n20-authorization-packet
```

The starting worktree was clean and aligned with
`origin/codex-track-handoff-context` before the L2 draft branch was created.

## L2 Matrix and Row Expectations

The drafted L2 matrix is:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

Expected execution shape:

```text
cells: 12
n_per_cell: 20
kernel_class: elementwise
dtypes: fp32
expected_rows: 240
scale_tier: paper
runtime_mlflow: disabled with TRITONGEN_MLFLOW=0
```

## Command Bundle Status

Packet path created:

```text
docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md
```

The packet records proposed future dry-plan, execution-plan, execution,
analyzer/report, and billing command surfaces. The run commands are explicitly
blocked because current launcher code supports only the L1a n=1 and L1b n=5
selector profiles for `grammar_mode_cp_12cell`.

Source-backed blocker:

- `cluster3/experiments/run_cluster3_modal.py` defines `L1A_SELECTOR_PROFILE`
  and `L1B_SELECTOR_PROFILE`.
- `SELECTOR_PROFILES` contains only those two profiles.
- `_selector_profile_for_scale()` rejects any other `scale_tier` and `n` pair.
- `build_l1a_dry_plan_payload()` and `build_l1a_execution_plan_payload()` both
  resolve through `_selector_profile_for_scale()`.
- The CLI exposes signed L1a/L1b options only; no signed L2 authorization
  option is present.

## Output/Artifact Namespace Plan

Future L2 output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
```

Future L2 artifact namespaces:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
```

The packet requires `fail_if_any_target_path_exists: true`, no retry, and no
resume unless a later deterministic signed resume policy exists. This draft does
not authorize writes to those namespaces.

## Stop-Limit Proposal

Proposed limits in the packet:

```text
max_rows: 240
max_generation_attempts: 1440
max_correctness_calls: 1440
max_wall_clock: 24h
fail_if_any_target_path_exists: true
retry_policy: no retry
resume_policy: no resume
```

The call caps scale the L1b 60-row cap of 360 generation attempts and 360
correctness calls by four. The wall-clock cap scales the L1b authorization cap
of 6h by four. Final signature should refresh the wall-clock cap from available
observability timings if those timings are used as evidence.

## Spend-Limit Proposal

The packet carries the L1b billing caveat forward:

```text
l1b_utc_window_cost_usd: 2.13879534
l1b_billing_attribution: UTC-window-only because Modal tags were empty
rough_l2_linear_cost_reference_usd: 8.55518136
max_estimated_cost_before_launch: USD 150
max_reconciled_billing_cap: USD 250
```

The draft requires pricing re-verification before final signature and treats
actual Modal billing reconciliation as authoritative. It does not claim
cost-per-success, ROI, speedup, or economic lift.

## Billing Caveat Carry-Forward

The L1b billing artifact matched the UTC hour:

```text
Interval Start: 2026-06-06T18:00:00
Cost: 2.13879534
Tags: {}
```

Because tags were empty, the L2 packet requires the same caveat unless future
Modal billing tags are demonstrably populated. Billing attribution remains
UTC-window-only unless proven otherwise.

## Analyzer/Report Validation Plan

The packet lists the intended L2 analyzer/report command with
`analysis_scope=primary_functional` and `scale_tier=paper`. It also records a
blocking requirement: L2 may not reuse the L1a smoke or L1b development
pair-skip scopes. Paper-scale analyzer strictness must pass on the actual L2
outputs before any reportable conclusion is made.

Future graphs must keep `grammar_mode` first-class. They must not collapse
`template_upper_bound` and `task_agnostic` into an unqualified `G` result.

## Evidence-Boundary Statement

L2 n=20 is the first evidence-quality rung for this 12-cell matrix, but it is
not a paper conclusion until the post-run analyzer/report output is audited.
This packet does not authorize paper conclusions, speedup claims, performance
claims, economic claims, billing claims beyond reconciliation, or analyzer
strictness relaxation.

## Signature Status

The packet remains:

```text
signature_status: UNSIGNED
AUTHORIZES_EXECUTION: NO
```

All human approval fields are blank placeholders. Modal/GPU/generation,
output/artifact mutation, billing reconciliation, post-run validation,
stop/spend limits, target commit, command bundle, and no-retry/no-resume remain
unsigned.

## Unresolved Blockers

1. Add source-backed L2 selector/profile support for `paper/n=20`.
2. Add a signed L2 authorization option/token distinct from L1a/L1b.
3. Add L2 output, observability, run-id, and selector placeholder constants.
4. Prove dry-plan and execution-plan for 12 cells and 240 rows without running
   Modal or generation.
5. Prove signed L2 selector validation rejects wrong scale, wrong n, existing
   paths, non-L2 scopes, retry, and resume.
6. Prove paper-scale analyzer strictness passes for the intended valid selector
   output, or block signature until a paper-safe analysis strategy is approved.
7. Re-verify Modal pricing before signature.
8. Sign stop/spend limits, billing query window, and output/artifact mutation
   scope before any launch.

## No-Execution Proof

No Modal command, GPU command, generation command, L2 run, n=20 run, billing
query, analyzer/report artifact refresh, preliminary-report refresh, profiler,
benchmark, or performance/speedup command was run during this packet draft.

The only validation commands used for this audit were Git/file scans and source
inspection. Runtime code was not changed.

## Validation and Scans Run

Whitespace validation:

```text
git diff --check
```

Result: passed.

Runtime-code diff scan:

```text
git diff --name-only -- cluster1 cluster2 cluster3 shared
```

Result: empty output.

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result: empty output.

Broad authorization scan:

```text
rg over docs/audits for affirmative execution, Modal, GPU, generation,
output/artifact mutation, billing-query, and L2 signature tokens
```

Result: non-empty historical matches from prior scoped L1a, L1b, and O6b
authorization artifacts, plus historical audit text that quotes scan patterns.
No L2 signature-token match was found, and this L2 draft did not introduce a
new affirmative L2 authorization.

Targeted L2/handoff authorization scan:

```text
rg over the new L2 packet, L2 audit, and updated handoff docs for affirmative
execution, Modal, GPU, generation, output/artifact mutation, billing-query, and
L2 signature tokens
```

Result: empty output.

Required status scan:

```text
rg -n "AUTHORIZES_EXECUTION: NO|UNSIGNED|L2|n=20|240|grammar_mode_cp_12cell|134bcf9|billing|UTC-window|no retry|no resume|fail_if_any_target_path_exists" docs audits
```

Result: required L2 concepts were present, including in the new packet, this
audit, and the updated handoff docs.

## Protected Mutation Proof

No runtime code, dependency manifests, lockfiles, preliminary-report files,
raw outputs, artifacts, or `mlruns/` files were changed. The only changed files
are the L2 packet, this audit, and the three handoff docs.

## Classification

`L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE`

## Next-Step Recommendation

Create a narrow local-only implementation branch for L2 selector/profile
support. It should add only the representability and signed planning surface
needed for `grammar_mode_cp_12cell`, `scale_tier=paper`, `n=20`, and 240
planned rows. It must not run Modal, generation, billing, L2, n=20, analyzer
artifact refresh, report artifact refresh, or output/artifact mutation.
