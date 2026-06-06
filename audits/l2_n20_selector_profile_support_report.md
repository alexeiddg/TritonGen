# L2 n=20 Selector/Profile Support Report

## Executive Summary

This branch adds local-only L2 n=20 selector/profile support for the existing
12-cell `grammar_mode x C x P` matrix. The launcher can now represent
`scale_tier=paper`, `n=20`, `dtypes=fp32`, and `kernel_class=elementwise`
without invoking Modal, GPU work, generation, correctness execution, output
writes, artifact writes, `mlruns`, billing queries, analyzer/report refreshes,
or paper-scale claims.

This branch does not authorize L2 execution. The L2 selector profile remains
runtime-disabled until a later final signature branch explicitly enables it.

## Blocker Resolved

Resolved blocker:

```text
L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE
```

The previous packet draft was blocked because `grammar_mode_cp_12cell` selector
profiles only covered L1a n=1 and L1b n=5. This branch adds source-backed
support for the L2 `paper/n=20` planning profile.

## Selector/Profile Behavior

Added source-backed L2 selector profile behavior:

```text
selector: grammar_mode_cp_12cell
profile_label: L2 n=20 paper
scale_tier: paper
n: 20
dtypes: fp32
kernel_class: elementwise
expected_planned_rows: 240
signed_authorization_option: --signed-l2-authorization
signed_authorization_placeholder: SIGNED_L2_PACKET_ID_REQUIRED
runtime_execution_enabled: false
```

The L2 profile is included in `SELECTOR_PROFILES` for planning resolution.
Dry-plan and execution-plan modes can resolve the profile locally. Runtime
selector execution remains fail-closed because the profile records
`runtime_execution_enabled=False`.

L1a and L1b profile behavior remains intact:

```text
L1a smoke/n=1: 12 planned rows
L1b development/n=5: 60 planned rows
L2 paper/n=20: 240 planned rows, planning only
```

## Matrix/Row Planning Result

The represented matrix remains:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
```

Planning result:

```text
cells: 12
rows_per_cell: 20
planned_rows: 240
grammar_off cells: 4
template_upper_bound cells: 4
task_agnostic cells: 4
no-P control cells: 6
P-eligible cells: 6
C-eligible cells: 6
deterministic_ordering: preserved
```

The grammar-mode mapping remains first-class. `template_upper_bound` and
`task_agnostic` remain distinct grammar modes and are not collapsed into a
binary G label.

## Authorization Guard

The runtime guard remains fail-closed:

- L2 execution without `--signed-l2-authorization` is rejected.
- Wrong L2 token values are rejected.
- Even the future L2 token string is currently rejected because the L2 profile
  is runtime-disabled on this branch.
- When a test-only enabled L2 profile is injected, `n != 20` is rejected.
- When a test-only enabled L2 profile is injected, existing target paths are
  rejected before runner work.
- L1a/L1b signed selector guards continue to pass their existing local tests.

This branch adds a source-backed signed-L2 command surface for review, not a
source-backed permission to execute.

## Path/Collision Policy

Future L2 output namespace:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
```

Future L2 observability namespace:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20
```

Future analysis/report/billing namespaces remain packet-level plans:

```text
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20*
```

The selector path policy remains:

```text
fail_if_any_target_path_exists
retry: not authorized
resume: not authorized
```

No test writes to protected repository `outputs/`, `artifacts/`, or `mlruns`.
Runtime-write tests use temporary directories and injected fake adapters.

## Packet Update

Updated packet:

`docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md`

Packet status changed from:

```text
L2_N20_AUTHORIZATION_PACKET_BLOCKED_COMMAND_SURFACE
```

to:

```text
L2_N20_SELECTOR_PROFILE_SUPPORT_READY_FOR_SIGNATURE_REVIEW
```

The packet still keeps:

```text
signature_status: UNSIGNED
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
```

## Tests Run

Focused tests:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_grammar_mode_matrix.py -q
```

Result:

```text
176 passed
```

Compile validation:

```bash
.venv/bin/python -m compileall -q cluster3 shared
```

Result:

```text
passed
```

## No-Execution Proof

No Modal command was run. No GPU job was run. No generation was run. No L2 n=20
execution was run. No billing query was run. No analyzer/report refresh was
run. No preliminary-report refresh was run. No dependency or lockfile command
was run.

The only local execution was the focused pytest bundle and `compileall`; both
operate on local code/tests and do not launch Modal or generation.

## Protected Mutation Proof

Protected paths are outside the patch scope:

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

The protected mutation scan is expected to remain empty:

```bash
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result:

```text
empty
```

Additional validation:

```text
git diff --check: passed
authorization leak scan over L2 packet/new audit/handoff/cluster3/shared: empty
scope scan: only existing parser context and negative/non-authorized wording
cluster1/cluster2/shared/protected-path diff scan: empty
```

## Remaining Blockers

Remaining blockers before any L2 execution:

- final human signature is missing;
- the L2 runtime profile is intentionally disabled;
- numeric stop/spend limits are still proposed, not signed;
- billing query window and billing artifact write are not signed;
- output/artifact mutation is not signed;
- paper-scale analyzer strictness must be proven on actual valid L2 outputs;
- post-run reportability and graph claims must be audited after the run.

## Classification

```text
L2_N20_SELECTOR_PROFILE_SUPPORT_COMPLETE
```

## Next-Step Recommendation

Review and commit this local-only selector/profile support branch, then promote
it into `codex-track-handoff-context` with a promotion audit. After promotion,
perform a separate final signature-readiness pass for L2. Do not run L2 n=20
from this branch.
