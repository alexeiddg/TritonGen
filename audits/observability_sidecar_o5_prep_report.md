# O5-Prep Actual Billing Reconciliation Launch Reconciliation

## Executive Summary

O5-Prep is a docs-only reconciliation package on
`codex/observability-o5-prep` from promoted O0-O4 baseline
`309c451d2710b376cb29b28c73ef28b7ea940bc6`.

It names the future O5 actual billing reconciliation target surfaces, allowed
sidecar-only billing fields, forbidden raw billing/private/economic payloads,
future approval packet requirements, required tests, stop conditions, and
authorization state. It does not implement O5 runtime code, query billing, use
credentials, mutate outputs, rewrite historical sidecars, change scientific
result rows, or change analyzers.

## Branch And Head Status

```text
branch: codex/observability-o5-prep
baseline: 309c451d2710b376cb29b28c73ef28b7ea940bc6
baseline subject: Audit O0-O4 observability branch acceptance
worktree before edits: clean
phase: O5-Prep docs-only launch reconciliation
```

## O0-O4 Promoted Baseline

O0-O4 are promoted into local and remote `codex-track-handoff-context` at
`309c451`. The promoted trunk preserves MLflow integration ancestry,
A2-A6 repair-memory ancestry, and the full O0-O4 observability package.

O5 actual billing reconciliation was not started in O0-O4. The final acceptance
classification was:

```text
O0_O4_FINAL_ACCEPTANCE_PASS_WITH_CAVEATS
```

## O5 Target Surfaces

Later O5 implementation may modify only:

```text
shared/observability/schema.py
shared/observability/redaction.py
shared/observability/logger.py
shared/observability/billing_reconciliation.py
shared/tests/test_observability_schema.py
shared/tests/test_observability_redaction.py
shared/tests/test_observability_logger.py
shared/tests/test_observability_imports.py
shared/tests/test_observability_billing_reconciliation.py
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
audits/observability_sidecar_o5_billing_reconciliation_report.md
```

No runner target is approved by O5-Prep. If later O5 implementation needs a
runner-specific test or code path, the implementation launch packet must name
that exact file before edits begin. No standalone CLI wrapper is approved by
O5-Prep; any command behavior must be behind
`shared/observability/billing_reconciliation.py` unless a later packet amends
the target list.

## O5-Prep Allowed Files

O5-Prep may modify only:

```text
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
docs/handoff/agentic_document_hub.md
docs/16_observability_sidecar_implementation_spec.md
audits/observability_sidecar_o5_prep_report.md
```

## O5-Prep Forbidden Files

O5-Prep must not modify:

```text
shared/observability/**
shared/modal_harness/**
cluster1/**
cluster2/**
cluster3/**
shared/analysis/**
shared/repair_history/**
outputs/**
mlruns/**
pyproject.toml
requirements*.txt
dependency or lock files
```

## Allowed Actual-Billing Reconciliation Fields

Future O5 fields are sidecar-only:

```text
actual_billing_available
actual_billing_status
actual_billing_reconciled_at_utc
billing_source
billing_source_version
billing_time_window_start_utc
billing_time_window_end_utc
billing_attribution_method
billing_attribution_confidence
actual_total_cost
actual_currency
billing_query_id
billing_report_redacted_sha256
billing_reconciliation_notes
```

Allowed source classes are limited to unavailable, approved Modal billing API,
approved Modal billing CLI report, approved exported static report, and approved
manual redacted summary. Actual cost values require approved source metadata,
window metadata, attribution metadata, and either a query identifier or a hash
of a redacted/safe billing summary. The initial currency is USD only.
Reconciliation notes must be bounded, redacted, and operational; they must not
contain raw report excerpts, invoice lines, private account details,
credentials, payment details, or economic/scientific interpretations.

Historical untagged artifacts must be marked attribution-limited or low
confidence unless a non-overlapping time window can be proven. Future app-tagged
runs may support stronger attribution only when the tag policy is recorded
before execution.

## Forbidden Billing, Private, And Economic Payloads

O5 must fail closed on:

```text
raw invoice dump
full billing API response
unredacted workspace billing report
payment method
credit_card
billing account secret
customer account secret
credentials
api key
Modal identity token
provider API key
private per-user billing data
raw provider bill
cost_per_success
cost_per_pass
pass_at_k_cost
ROI
economic lift
benchmark economics
performance/profiler/timing/speedup claim
```

Billing report hashes must be hashes of redacted or otherwise safe summaries,
not hashes of raw invoice dumps, raw workspace reports, full API responses, or
credential-bearing payloads.

## O5 Behavior Constraints

O5 is post-hoc reconciliation only. It must not run during generation, claim
synchronous per-row actual billing, change result rows, mutate outputs, rewrite
historical sidecars, change analyzers, or add economic/scientific claims.

Future O5 implementation must include dry-run behavior and mocked/static unit
fixtures. Real billing query, credential use, Modal billing/API/CLI invocation,
exported report processing, output mutation, or historical sidecar migration
requires a separate explicit approval packet.

Observability remains default-off. Omitted/off behavior remains unchanged.

## Future Approval Packet Requirements

Any later O5 billing-query or credential-use packet must name:

```text
billing source
credential scope
workspace/account scope
time window
delay buffer
app tags or attribution keys
target run_id
target experiment_id
whether historical runs are app-tagged
raw report handling policy
redaction policy
output sidecar path
no-output-mutation or explicit mutation authorization
expected cost/credential risk
dry-run command
stop conditions
```

## Required O5 Tests

Later O5 implementation must test:

- unavailable actual billing status accepted;
- reconciled billing status requires approved source metadata;
- actual cost rejected without approved source metadata;
- negative, non-finite, string, boolean, and coerced actual costs rejected;
- unsupported currency rejected;
- raw invoice and API response payloads rejected;
- credentials, secrets, payment fields, and private billing account fields
  rejected;
- untagged historical attribution marked limited;
- billing report hash accepted only for redacted/safe summaries;
- no billing/provider/Modal API calls in unit tests;
- mocked/static billing fixtures only;
- no result-row mutation;
- no output mutation;
- no economic or scientific claims.

## Stop Conditions

Stop with a blocked classification if:

- O5 target surfaces are ambiguous;
- any docs authorize billing query or credential use without a separate packet;
- any Modal billing/API/CLI invocation occurs during prep;
- raw invoice, full API response, credential, payment method, or private billing
  account data would be stored;
- output mutation, historical sidecar rewrite, result-row schema mutation, or
  analyzer/economic metric change is required;
- cost-per-success, pass@k cost, ROI, economic lift, benchmark economics,
  performance, profiler, timing, speedup, latency, throughput, Nsight, or NCU
  claims appear;
- dependency or lockfile changes are needed;
- docs conflict on target surfaces, allowed fields, authorization state, or O6
  performance boundary.

## Authorization State

```text
AUTHORIZES_EXECUTION: NO
MODAL_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
GPU_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
N5_AUTHORIZED: NO
N20_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
BILLING_QUERY_AUTHORIZED: NO
CREDENTIAL_USE_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

No Modal run, generation run, GPU job, billing query, credential use, output
mutation, dependency change, lockfile change, or MLflow runtime-state write was
authorized or performed by O5-Prep.

## Validation Commands

Planned docs-only validation:

```bash
git diff --check
git status --short --branch
git diff --name-only -- shared/observability shared/modal_harness cluster1 cluster2 cluster3 shared/analysis shared/repair_history outputs pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Also run a positive execution authorization scan for affirmative authorization
flags across the touched docs and audit report. The report intentionally avoids
spelling those affirmative flag strings so the scan can remain empty.

Forbidden O5 scope scan:

```bash
rg -n "raw invoice|invoice dump|full billing API response|payment method|credit_card|billing account secret|credential|api key|MODAL_IDENTITY_TOKEN|modal.billing|workspace_billing_report|modal billing report|cost_per_success|cost_per_pass|pass_at_k_cost|ROI|economic lift|benchmark economics|speedup|throughput|latency|kernel_timing|profiler|Nsight|NCU|billing query|credentialed" \
  docs/handoff/experiment_change_orchestration_state.md \
  docs/handoff/document_version_registry.md \
  docs/handoff/agentic_document_hub.md \
  docs/16_observability_sidecar_implementation_spec.md \
  audits/observability_sidecar_o5_prep_report.md
```

Expected O5 scan hits are only explicit prohibitions, caveats, stop conditions,
or command text.

## Forbidden-Scope Scan Results

Validation results:

```text
git diff --check: passed
direct no-index whitespace check for audits/observability_sidecar_o5_prep_report.md: no diagnostics
forbidden code-scope diff: empty
positive execution authorization scan: empty
forbidden O5 scope scan: hits reviewed as explicit prohibitions, caveats, stop conditions, or command text only
changed surface: docs plus audits/observability_sidecar_o5_prep_report.md only
```

No runtime code, outputs, dependencies, lockfiles, result schemas, analyzers,
MLflow runtime state, Modal calls, billing queries, or credential use were
performed.

## Unresolved Risks

- O5 implementation is not started.
- Real billing reconciliation remains unavailable until a later approved O5
  implementation and a separate billing-query or credential-use packet.
- Historical untagged artifacts remain attribution-limited.
- O5 does not authorize cost-per-success, pass@k cost, ROI, economic lift,
  benchmark economics, analyzer changes, paper-scale conclusions, or
  performance/profiler/timing work.

## Classification

```text
O5_PREP_COMPLETE
```

## Next-Step Recommendation

Run independent docs-only review for O5-Prep. If the review passes, commit this
docs-only package. Do not start O5 billing reconciliation implementation until
O5-Prep is committed and a separate O5 implementation launch packet is approved.
