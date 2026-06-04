# O5c Modal Billing Report Collection Report

## Executive Summary

O5c added a narrow Modal billing report collection adapter and fixture-only
redaction tests, but live billing collection is blocked by Modal billing-report
limits.

Classification:

```text
O5C_BLOCKED_MODAL_BILLING_RATE_LIMIT_WITH_ADAPTER_READY
```

No raw or redacted billing artifact was produced or retained. No scientific
outputs, historical JSONL rows, result schemas, analyzers, dependency files,
lockfiles, MLflow runtime state, Modal compute jobs, generation jobs, GPU jobs,
n=5, n=20, paper-scale runs, or economic/scientific claims were touched.

## Branch And Baseline

Repository:

```text
/Users/alexeidelgado/Desktop/TritonGen
```

Branch:

```text
codex/observability-o5b-reconciliation
```

Baseline:

```text
cf63de8 Implement O5b static billing reconciliation ingestion
```

## Approved Billing Query Packet

The user supplied the required UTC window:

```text
time_window_start_utc: 2026-05-01T00:00:00Z
time_window_end_utc: 2026-06-05T00:00:00Z
```

The end timestamp is exclusive.

Approved query parameters:

```text
billing_source: modal_billing_cli preferred
resolution: h
tag_names: project,experiment_id,run_id,cluster,phase
raw_report_path: artifacts/observability_billing/raw/modal_billing_report_20260604T155659Z.json
redacted_report_path: artifacts/observability_billing/redacted/modal_billing_report_redacted_20260604T155659Z.jsonl
```

## Official Modal References

Local installed help:

```text
.venv/bin/python -m modal billing report --help
```

The installed help states that `modal billing report` generates a workspace
billing report, supports `--start`, `--end`, `--for`, `--resolution`,
`--tag-names`, `--json`, and is a CLI frontend for
`modal.billing.workspace_billing_report`. It also states that start is inclusive
and end is exclusive.

Official web references used:

```text
https://modal.com/docs/reference/cli/billing
https://modal.com/docs/reference/modal.billing
```

The API reference describes `WorkspaceBillingReportItem` as containing
`object_id`, `description`, `environment_name`, `interval_start`, `cost`, and
`tags`, and states that `workspace_billing_report` returns interval rows with
UTC timestamps and optional user-provided tags.

## Implementation Summary

Added:

```text
shared/observability/billing_modal_collection.py
shared/tests/test_observability_billing_modal_collection.py
```

Updated:

```text
shared/observability/billing_reconciliation.py
shared/tests/test_observability_billing_reconciliation.py
shared/tests/test_observability_imports.py
```

The adapter:

- builds deterministic `modal billing report` CLI commands without executing
  them during tests
- splits hourly queries into 7-day-or-less chunks after Modal reported the
  hourly range limit
- imports no `modal` package at module import time
- performs no collection unless an explicit collection function is called
- parses Modal JSON report rows
- validates row interval timestamps against the approved query window
- aggregates costs by safe attribution tags
- emits O5b redacted static records with source
  `redacted_modal_billing_report`
- maps that redacted source to `approved_modal_billing_cli_report`
- preserves composed attribution labels exactly and fails closed through O5b
  validation instead of truncating oversized labels
- keeps raw Modal `object_id`, `description`, `environment_name`, payment,
  account, invoice, and economic fields out of redacted records

The O5b reconciliation helper was also tightened to use exclusive-end billing
window overlap semantics.

## Live Collection Attempt

First attempted command:

```text
.venv/bin/python -m modal billing report --start 2026-05-01 --end 2026-06-05 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

Result:

```text
Billing report range limit exceeded. Hourly reports cannot span more than 7 days.
```

Second attempted strategy:

```text
.venv/bin/python -m modal billing report --start 2026-05-01 --end 2026-05-08 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
.venv/bin/python -m modal billing report --start 2026-05-08 --end 2026-05-15 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
.venv/bin/python -m modal billing report --start 2026-05-15 --end 2026-05-22 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
.venv/bin/python -m modal billing report --start 2026-05-22 --end 2026-05-29 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
.venv/bin/python -m modal billing report --start 2026-05-29 --end 2026-06-05 --resolution h --tag-names project,experiment_id,run_id,cluster,phase --json
```

Result:

```text
Rate limit exceeded for workspace billing report requests.
```

The chunked collection stopped before writing a combined raw report. A
zero-byte placeholder created by the first shell-redirection attempt was
removed. No raw or redacted billing artifact remains in the worktree.

## Redaction And Privacy Boundary

The sanitizer preserves only:

```text
report_id
report_source
report_version
billing_time_window_start_utc
billing_time_window_end_utc
currency
total_cost
experiment_id
run_id
app_tag
attribution_method
attribution_confidence
redacted_report_hash
```

Raw Modal object IDs, object descriptions, environment names, unrequested tags,
payment fields, customer/account identifiers, invoice payloads, credentials,
and economic claim fields are not emitted into the redacted O5b report format.

## Validation

Focused O5b/O5c billing tests:

```text
.venv/bin/python -m pytest shared/tests/test_observability_billing_modal_collection.py shared/tests/test_observability_billing_reconciliation.py -q
```

Result:

```text
59 passed
```

Shared observability bundle:

```text
.venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_redaction.py shared/tests/test_observability_logger.py shared/tests/test_observability_imports.py shared/tests/test_observability_billing_reconciliation.py shared/tests/test_observability_billing_modal_collection.py -q
```

Result:

```text
267 passed
```

Lightweight non-observability regression bundle:

```text
.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py shared/tests/test_factorial_analysis.py -q
```

Result:

```text
265 passed
```

Combined validation:

```text
532 passed
```

Compilation check:

```text
.venv/bin/python -m py_compile shared/observability/billing_modal_collection.py shared/observability/billing_reconciliation.py shared/tests/test_observability_billing_modal_collection.py shared/tests/test_observability_billing_reconciliation.py
```

Result:

```text
passed
```

Whitespace:

```text
git diff --check
git diff --check --no-index /dev/null shared/observability/billing_modal_collection.py
git diff --check --no-index /dev/null shared/tests/test_observability_billing_modal_collection.py
git diff --check --no-index /dev/null audits/observability_sidecar_o5c_modal_billing_collection_report.md
```

Result:

```text
passed
```

Forbidden protected-surface diff:

```text
git diff --name-only -- cluster1 cluster2 cluster3/results cluster3/feedback shared/modal_harness shared/analysis shared/repair_history outputs pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Result:

```text
empty
```

Billing/API/credential and economic/performance scans were reviewed. Hits were
expected O5c adapter names, explicit approved billing CLI commands, blocked
collection report text, existing redaction deny patterns, negative tests, or
handoff prohibitions/caveats. No retained raw billing artifact was present:

```text
find artifacts/observability_billing -maxdepth 3 -type f -ls
```

Result:

```text
empty
```

## Current Caveat

O5c is not complete as a real collection package because the approved live
Modal billing report could not be collected. The next safe action is to wait for
the Modal workspace billing-report rate limit to clear, then rerun the same
chunked commands or use the official `modal.billing.workspace_billing_report`
API only if separately approved as the fallback execution surface for the same
UTC window.
