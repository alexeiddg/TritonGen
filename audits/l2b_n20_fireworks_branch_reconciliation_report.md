# L2b n20 Fireworks Branch Reconciliation Report

## Executive Summary

The teammate branch `origin/codex/fireworks-api-modal-implementation-plan`
contains Fireworks GBNF n20 validation documents for a separate evidence stream,
not completion evidence for the current Modal L2b n20 attempt2 stream.

The reported `2160/2160` rows are tied to
`outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf`, with run tier
`fireworks_gbnf_n20`, model slot `FW-B`, and Minimax over the Fireworks
Chat Completions API using GBNF. The current Modal stream uses
`outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*`
and remains separate.

The three teammate docs/audits can be carried into the current branch as
docs-only records. The teammate branch itself must not be merged wholesale,
because its branch delta includes output/artifact deletions and runtime changes
outside this reconciliation scope.

Classification: `FIREWORKS_N20_RECONCILED_SEPARATE_EVIDENCE_STREAM`.

## Current Modal Attempt2 State

Current branch inspection:

```text
branch: codex-track-handoff-context
tracked diff before reconciliation: none
untracked live artifact paths:
  artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery/
  artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel/
untracked paper path:
  docs/paper_draft/
```

Current recent trunk commits:

```text
e0cba5e Allowlist L2b n20 attempt2 rescue stages
dd59df9 Archive L2b n20 attempt2 partial observability artifacts
a59995c Prepare L2b n20 attempt2 two-lane rescue authorization
c6ee2e6 Repair L2b n20 attempt2 validation continuation
c5667e7 Add L2b n20 attempt2 wave runner
a6b7c23 Authorize L2b n20 attempt2 execution
2e9ca7b Archive L2b n20 partial wave1 launch blocker
430c342 Authorize L2b n20 full coverage execution
28255c3 Reconcile L2b n2 post-recovery runtime fixes
fbe835c Complete L2b n2 missing row recovery
```

No Modal, Fireworks, GPU, generation, analyzer, report, billing, cleanup, retry,
resume, overwrite, or Wave 4 launch was run during this reconciliation.

## Teammate Branch State

Fetched branch:

```text
origin/codex/fireworks-api-modal-implementation-plan
commit: b67f265c716579dafac1e7af9e17ed9f03d52edf
```

The branch includes the requested Fireworks GBNF documents:

```text
audits/fireworks_gbnf_n20_combined_validation_report.md
audits/fireworks_gbnf_n20_wave4_validation_report.md
docs/experiment_packets/fireworks_gbnf_n20_wave_completion_contract.md
```

The branch also has wider differences relative to current trunk, including
tracked output/artifact deletions, runner-script deletions, and runtime code
changes. Those wider changes are out of scope and unsafe to merge as a branch
merge in the current live-artifact state.

## Files Inspected

Read from `origin/codex/fireworks-api-modal-implementation-plan` without
checking out the branch:

```text
audits/fireworks_gbnf_n20_combined_validation_report.md
audits/fireworks_gbnf_n20_wave4_validation_report.md
docs/experiment_packets/fireworks_gbnf_n20_wave_completion_contract.md
```

Then restored only those three files into the current worktree for docs-only
recording.

## Evidence Stream Classification

The teammate result is Fireworks-backed, not Modal L2b-backed.

Evidence identifiers in the teammate docs:

```text
experiment_id: fireworks_api_modal_v1
run_tier: fireworks_gbnf_n20
model_slot: FW-B
model_id: accounts/fireworks/models/minimax-m2p7
provider_api: chat_completions
fireworks_grammar_mode: gbnf
output_namespace: outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf
```

The current Modal L2b attempt2 evidence identifiers use:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave2_missing360_recovery/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave3_parallel/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2_wave4_parallel/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2b_n20_attempt2*
```

These are separate namespaces and separate execution/evidence streams.

## Namespace Comparison

The Fireworks docs reference accepted combined inputs:

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_1.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2_rerun_after_billing.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_3.jsonl
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_4.jsonl
```

They explicitly exclude:

```text
outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf/fw_b_minimax_wave_2.jsonl
```

The Fireworks docs do not claim current Modal attempt2 namespaces as raw input
for the `2160/2160` validation.

## Artifact Availability

The inspected branch contains audit/contract documents, but the requested
inspection did not find committed raw Fireworks JSONL result artifacts under
`outputs/cluster_fw/fireworks_api_modal_v1/l2_n20_gbnf`.

Therefore the imported docs are evidence snapshots and operational validation
records. They do not by themselves import raw rows into the current branch.

## Raw-Row Provenance

Raw-row provenance is document-referenced rather than raw-artifact-present in
this reconciliation. The combined validation report names the four accepted
input JSONL files and the excluded contaminated Wave 2 file. The Wave 4 report
names the Wave 4 output path, initial Modal app id, resume run id, and expected
row count.

Because the raw JSONL files are not included in the docs-only import, downstream
analyzer/report work remains blocked until separately authorized and until the
raw Fireworks artifacts are available through the approved artifact path or an
explicit artifact import/reconstruction step.

## Validation Provenance

The combined validation report records:

```text
total_rows: 2160
unique: 2160
duplicates: 0
conditions: 12
kernel_classes: elementwise, matmul, reduction
dtypes: bf16, fp16, fp32
billing_or_auth_provider_errors: 0
provider_errors: 22
grammar_provider_errors: 21
timeout_provider_errors: 1
compile_success: 990 / 2160
```

The Wave 4 report records:

```text
rows: 540
unique: 540
duplicates: 0
billing_or_auth_provider_errors: 0
grammar_provider_errors: 5
timeout_provider_errors: 1
```

These validation claims are accepted as teammate-branch operational audit
claims for the Fireworks stream, not as direct local raw-row revalidation in
this no-execution/no-output-mutation reconciliation.

## Compile-Success Figure Provenance

The `990/2160` compile-success figure comes from
`audits/fireworks_gbnf_n20_combined_validation_report.md`.

Condition-level compile-success values in that report sum to 990 across the 12
conditions.

## F3_EVAL_PIPELINE Provenance

The combined report records `F3_EVAL_PIPELINE: 22`:

```text
21 rows: Fireworks provider-side GBNF grammar processing failures
1 row: Fireworks/provider timeout in grammar_off
0 rows: billing/auth/precondition failures in accepted combined inputs
```

The Wave 4 report records 6 of those F3 rows:

```text
5 Fireworks grammar-processing failures in task_agnostic__c_on__p_on
1 provider/network timeout in grammar_off__c_on__p_on
```

These rows are provider-side Fireworks/GBNF operational outcomes and must not be
collapsed into ordinary Triton compile/runtime failures.

## Current Modal Wave 4 Decision

The teammate Fireworks Wave 4 document does not complete the current Modal L2b
n20 attempt2 Wave 4 namespace.

Current Modal Wave 4 remains a separate decision under its own signed namespace:

```text
l2b_n20_attempt2_wave4_parallel
```

The Fireworks result can inform analysis planning, but it does not make the
current Modal stream complete.

## Merge Safety

Safe now:

```text
audits/fireworks_gbnf_n20_combined_validation_report.md
audits/fireworks_gbnf_n20_wave4_validation_report.md
docs/experiment_packets/fireworks_gbnf_n20_wave_completion_contract.md
audits/l2b_n20_fireworks_branch_reconciliation_report.md
handoff document references
```

Unsafe now:

```text
whole-branch merge from origin/codex/fireworks-api-modal-implementation-plan
tracked output/artifact deletions from the teammate branch
runtime implementation changes from the teammate branch
script deletions from the teammate branch
any mutation of live Lane A or Lane B artifact namespaces
any paper-draft staging
```

## Analyzer And Report Boundary

Analyzer/report refresh remains blocked. The imported Fireworks docs are
operational validation records only. No analyzer, report, billing, or paper
conclusion is authorized or performed by this reconciliation.

## Recommended Next Action

Keep the three Fireworks validation documents as a separate evidence-stream
record on `codex-track-handoff-context`. Do not treat them as completion of the
current Modal L2b n20 attempt2 stream. Decide separately whether to launch
Modal Wave 4 under the already prepared Wave 4-only authorization after current
Lane A/B state reaches a safe terminal point and source/docs/scripts are clean
and aligned.

## Classification

`FIREWORKS_N20_RECONCILED_SEPARATE_EVIDENCE_STREAM`
