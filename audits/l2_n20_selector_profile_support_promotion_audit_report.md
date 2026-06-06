# L2 n=20 Selector/Profile Support Promotion Audit Report

## Source Branch

`codex/l2-n20-selector-profile-support`

## Promoted Commit

`27493c0 Add L2 n20 selector profile support`

## Selector/Profile Behavior

The promoted support adds a local-only L2 selector profile for the existing
`grammar_mode_cp_12cell` selector:

```text
profile_label: L2 n=20 paper
scale_tier: paper
n: 20
dtypes: fp32
kernel_class: elementwise
signed_authorization_option: --signed-l2-authorization
runtime_execution_enabled: false
```

Dry-plan and execution-plan modes can build source-backed command surfaces for
the L2 profile without invoking Modal, generation, correctness execution,
output writers, artifact writers, `mlruns`, or billing queries. Runtime L2
execution remains disabled by the profile-level gate.

## Matrix/Row Planning Result

The promoted matrix remains the selected 12-cell design:

```text
grammar_mode in {grammar_off, template_upper_bound, task_agnostic}
C in {off, on}
P in {off, on}
cells: 12
rows_per_cell: 20
planned_rows: 240
```

The grammar-mode mapping remains explicit. `template_upper_bound` and
`task_agnostic` are not collapsed into a binary grammar label, and no-P
controls remain represented as first-class cells.

## Authorization Guard Status

The promoted support does not authorize execution:

```text
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
ARTIFACT_MUTATION_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
```

The signed-L2 option is present only as a future command-surface review field.
Even the future L2 token remains blocked because the L2 selector profile records
`runtime_execution_enabled=False`.

## Packet Update Status

The promoted packet remains:

```text
packet: docs/experiment_packets/full_pipeline_grammar_mode_cp_l2_n20_authorization_packet.md
status: UNSIGNED_SELECTOR_PROFILE_SUPPORT_READY_FOR_SIGNATURE_REVIEW
signature_status: UNSIGNED
AUTHORIZES_EXECUTION: NO
```

The command-surface blocker from the draft packet is resolved at the local
planning layer. Final human signature, runtime-gate enablement, output/artifact
mutation authorization, billing authorization, and analyzer/report audit remain
separate future requirements.

## Tests Run

Focused test bundle:

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

Whitespace validation:

```bash
git diff --check
```

Result:

```text
passed
```

## Protected Mutation Proof

Protected path scan:

```bash
git diff --name-only codex-track-handoff-context..HEAD -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result:

```text
empty before promotion
```

No output, artifact, `mlruns`, preliminary-report, dependency, or lockfile path
was changed by the selector/profile support promotion.

## No-Execution Proof

No Modal command was run. No GPU job was run. No generation was run. No L2 n=20
execution was run. No billing query was run. No analyzer/report refresh was
run. No preliminary-report refresh was run. No dependency or lockfile command
was run.

Validation was limited to local pytest, local compile validation, git status,
git log, protected-diff scans, authorization scans, and the fast-forward-only
git promotion.

## Remaining Blockers

- Final human signature is missing.
- The L2 runtime selector profile remains disabled.
- Numeric stop/spend limits are proposed but not signed.
- Billing query window and billing artifact write are not signed.
- Output/artifact mutation is not signed.
- Paper-scale analyzer strictness must be audited on actual valid L2 outputs.
- Post-run graph/report claims remain blocked until output validation and
  analyzer/report audit pass.

## Classification

```text
L2_N20_SELECTOR_PROFILE_SUPPORT_PROMOTION_COMPLETE
```

## Next-Step Recommendation

Prepare the final L2 n=20 signature-readiness audit against the promoted handoff
baseline. Do not execute L2, n=20, Modal/GPU generation, billing queries,
output/artifact mutation, analyzer/report refresh, or paper-scale reporting
unless a later final signature explicitly authorizes those actions.
