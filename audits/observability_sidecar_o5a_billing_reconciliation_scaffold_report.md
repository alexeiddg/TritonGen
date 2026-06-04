# O5a Actual Billing Reconciliation Scaffold Report

Date: 2026-06-04

Branch:

```text
codex/observability-o5-prep
```

Baseline:

```text
effd644468e237829849f1c2a0cd3ad028a7f5fa
```

## Classification

```text
O5A_SCAFFOLD_COMPLETE_PENDING_REVIEW
```

## Scope

O5a adds sidecar-only scaffolding for post-hoc actual billing reconciliation
metadata. It is limited to strict schema validation, fail-closed redaction, and
logger summary validation over already supplied mocked/static metadata.

O5a does not query billing, use credentials, call Modal billing APIs or CLI,
read invoices, read workspace billing reports, mutate outputs, rewrite
historical sidecars, edit runners, change scientific JSONL row schemas, change
analyzers, add dependencies, or write MLflow runtime state.

## Changed Surfaces

```text
shared/observability/schema.py
shared/observability/redaction.py
shared/observability/logger.py
shared/tests/test_observability_schema.py
shared/tests/test_observability_redaction.py
shared/tests/test_observability_logger.py
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md
```

No runner, output, analyzer, dependency, lockfile, Modal harness, MLflow runtime,
or result-schema file is modified.

## Implemented Behavior

- `ObservabilityActualBillingReconciliation` validates
  unavailable/not_reconciled/reconciled actual-billing metadata.
- Reconciled actual billing requires bounded source metadata, source version,
  UTC time window, attribution method, attribution confidence, USD actual cost,
  and either a query identifier or redacted report hash.
- Unreconciled statuses cannot carry actual cost, currency, source, attribution,
  query, report-hash, or time-window metadata.
- Redaction allowlists only bounded O5 billing fields and rejects raw invoice,
  full API response, unredacted workspace billing report, payment, credential,
  secret, private billing, cost-per-success, pass@k cost, ROI, economic-lift,
  benchmark-economics, and paper-scale cost-conclusion payloads.
- `actual_billing_summary` is derived from validated event sidecars. Atomic
  summary writes reject summaries whose actual billing summary does not match
  the event stream.
- Mocked/static test fixtures are the only source of reconciled metadata in
  this package.

## Non-Goals

O5a does not implement real billing reconciliation execution. It does not
authorize:

```text
billing query
credential use
Modal billing CLI/API invocation
provider billing API invocation
invoice or exported billing report ingestion
output mutation
historical sidecar migration
runner integration
cost-per-success
pass@k cost
ROI
economic lift
benchmark economics
paper-scale cost conclusions
```

## Validation

Focused observability suite:

```bash
.venv/bin/python -m pytest \
  shared/tests/test_observability_schema.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_logger.py \
  shared/tests/test_observability_imports.py -q
```

Result:

```text
208 passed
```

Cluster 3 runner regression suite:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -q
```

Result:

```text
125 passed
```

Combined focused validation:

```bash
.venv/bin/python -m pytest \
  shared/tests/test_observability_schema.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_logger.py \
  shared/tests/test_observability_imports.py \
  cluster3/tests/test_run_cluster3_modal_cli.py -q
```

Result:

```text
333 passed
```

Whitespace validation:

```bash
git diff --check
git diff --check --no-index /dev/null \
  audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md
```

Result:

```text
passed
```

Forbidden modified-surface check:

```bash
git diff --name-only -- \
  cluster1 cluster2 cluster3 shared/modal_harness shared/analysis \
  shared/repair_history outputs pyproject.toml requirements.txt \
  requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Result:

```text
no matches
```

Positive execution authorization scan:

```bash
rg -n "MODAL_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|OUTPUT_MUTATION_AUTHORIZED: YES|GPU_AUTHORIZED: YES|N5_AUTHORIZED: YES|N20_AUTHORIZED: YES|PAPER_SCALE_AUTHORIZED: YES|BILLING_QUERY_AUTHORIZED: YES|CREDENTIAL_USE_AUTHORIZED: YES|DEPENDENCY_CHANGE_AUTHORIZED: YES|AUTHORIZES_EXECUTION: YES" \
  docs/handoff audits shared/observability shared/tests/test_observability_schema.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_logger.py \
  shared/tests/test_observability_imports.py
```

Result:

```text
no matches
```

O5 privacy/billing/economic scan:

```bash
rg -n "modal\\.billing|workspace_billing_report|modal billing report|billing api|billing_api|billingCLI|billing CLI|provider billing API|invoice fetch|credentials?|api key|MODAL_IDENTITY_TOKEN|credit_card|payment_method|raw_invoice|invoice_dump|full_billing_api_response|unredacted_workspace_billing_report|cost_per_success|cost_per_pass|pass_at_k_cost|ROI|economic_lift|benchmark_economics|paper_scale_cost_conclusion|speedup|throughput|latency|kernel_timing|profiler|Nsight|NCU" \
  shared/observability shared/tests/test_observability_schema.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_logger.py \
  shared/tests/test_observability_imports.py \
  docs/handoff/experiment_change_orchestration_state.md \
  docs/handoff/document_version_registry.md \
  audits/observability_sidecar_o5a_billing_reconciliation_scaffold_report.md
```

Result:

```text
hits reviewed as redaction deny rules, negative tests, explicit prohibitions,
historical caveats, or scan command text only
```

Current status:

```bash
git status --short --branch
```

Result:

```text
modified O5a files plus this untracked audit report; no staged files
```

## Caveats

Actual billing remains unreconciled for real runs. The new schema can validate
mocked/static reconciled metadata, but no real billing source is queried or
approved by this package.

A later O5 billing-query packet must still specify source, credential scope,
workspace/account scope, time window, delay buffer, app tags or attribution
keys, raw report handling, redaction policy, output sidecar path, dry-run
command, expected cost/credential risk, and stop conditions before any billing
execution occurs.

## Next Gate

Run independent review on the O5a uncommitted changes. Commit only after review
returns an explicit pass.
