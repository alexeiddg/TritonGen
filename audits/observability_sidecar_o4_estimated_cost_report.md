# O4 Observability Estimated Cost Telemetry Report

## Executive Summary

O4 is locally implemented on `codex/observability-sidecar-core` from baseline
`d30aa500df9efb0ee0ce987dbb46317ed1db14d3`. The implementation is sidecar-only:
it accepts supplied estimated cost metadata or explicit unavailable metadata,
and it rejects actual billing, invoices, billing/pricing API payloads, and
economic claim fields.

Classification: `O4_ESTIMATED_COST_COMPLETE_WITH_CAVEATS`.

## Worktree Status

Before O4 implementation, the worktree was clean on
`codex/observability-sidecar-core` at
`d30aa500df9efb0ee0ce987dbb46317ed1db14d3`.

At report time, only O4 allowed files are modified. No commit has been made for
O4 yet.

## Target Surfaces

Implementation surfaces:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/logger.py`
- `cluster3/experiments/run_cluster3_modal.py`

Test surfaces:

- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_logger.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Documentation/report surfaces:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `audits/observability_sidecar_o4_estimated_cost_report.md`

## Files Changed

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/logger.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_logger.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `audits/observability_sidecar_o4_estimated_cost_report.md`

## Estimated-Cost Schema Summary

`ObservabilityCostEstimate` was reconciled to the O4-Prep allowed field set:

- `cost_estimate_available`
- `estimated_input_cost`
- `estimated_output_cost`
- `estimated_total_cost`
- `currency`
- `pricing_source`
- `pricing_source_version`
- `cost_estimate_status`
- `cost_estimate_method`

The schema rejects old draft fields such as `estimate_status`,
`price_snapshot_id`, `estimated_gpu_seconds`, `estimated_total_cost_usd`,
`estimation_confidence`, and `cost_basis`.

Validation now requires estimated values to be non-negative, finite, numeric,
USD-only, decimal-safe to 12 places, complete, and internally consistent:
`estimated_total_cost == estimated_input_cost + estimated_output_cost` with a
1e-9 absolute tolerance for float representation. Unavailable records cannot
carry cost values, currency, pricing source metadata, or an estimate-producing
method.

## Redaction/Cost Safety Summary

Recursive redaction now allows only the O4 estimated-cost keys above and rejects
actual billing and economic claim key families, including invoice, account
charge, provider bill, Modal bill, billing API response, pricing API response,
cloud invoice dump, external pricing fetch, cost-per-success, pass@k cost, ROI,
economic lift, benchmark-cost conclusion, and camelCase variants covered by the
existing key normalizer.

Existing O0/O2/O3 redaction boundaries for secrets, environment dumps, Modal
identity tokens, performance telemetry, token IDs, prompts, source, generated
text, raw outputs, private eval, and feedback payloads remain in force.

## Logger/Summary Behavior

`shared/observability/logger.py` now derives `estimated_cost_summary` from the
validated event stream. Missing or unavailable event cost records produce an
unavailable-safe summary. Available estimates are aggregated only when all
available records share `USD`, one pricing source, one pricing-source version,
and one estimate method.

Atomic summary writing rejects summaries whose `estimated_cost_summary` does not
match the current event stream, alongside the existing event count, stage
duration, token total, and hash validations.

## Cluster 3 Runner Wiring Summary

Cluster 3 gained a dependency-injected `cost_estimate_provider` for tests and
future approved local sources. The default enabled behavior writes explicit
unavailable cost metadata. The runner does not add CLI pricing options, does not
read pricing files, does not call billing or pricing APIs, and does not change
Modal, generation, repair, correctness, or result-row behavior.

## Off/Best_Effort/Required Behavior

- `off`: no sidecar logger opens and no Modal context, token-count, or cost
  provider is called.
- `best_effort`: invalid supplied cost metadata disables sidecars safely and
  preserves the mocked runner outcome.
- `required`: invalid supplied cost metadata fails before generation or
  correctness adapters run.
- Enabled valid paths can include supplied fake/test cost estimates in sidecars.

## Result-Row Non-Mutation Proof

No scientific result dataclasses, row schemas, result loggers, analyzers, or
`outputs/` paths were modified. `cluster3/tests/test_run_cluster3_modal_cli.py`
continues to assert that Cluster 3 result rows do not gain observability,
duration, token, or estimated-cost fields.

`git diff --name-only -- cluster1 cluster2/results cluster3/results` produced
empty output.

## No Billing/Pricing/API Proof

No billing API, Modal billing, provider billing, invoice, dashboard, external
pricing fetch, network client, dependency, or lockfile code was added.

`shared/tests/test_observability_imports.py` now guards `shared.observability`
against billing/pricing/cloud/network client imports including `boto3`, `httpx`,
`requests`, `stripe`, `urllib`, `mlflow`, and `wandb`, in addition to the prior
remote/generation stacks.

## Forbidden Cost/Billing Scan Results

Command:

```bash
rg -n "actual_cost|actual_billing|invoice|account_charge|provider_bill|modal_bill|credit_card|payment_method|billing_account|billing_api_response|pricing_api_response|cloud_invoice_dump|external_pricing_fetch|cost_per_success|cost_per_pass|pass_at_k_cost|ROI|roi|economic_lift|benchmark_cost_conclusion" \
  shared/observability \
  shared/tests/test_observability_*.py \
  cluster3/experiments/run_cluster3_modal.py \
  cluster3/tests/test_run_cluster3_modal_cli.py
```

Result: matches are limited to redaction deny rules, negative tests, explicit
forbidden-payload assertions, `actual_billing_status="not_implemented"`, and
runner caveats that billing/pricing is not queried.

## Forbidden Telemetry/Economic Claim Scan Results

Command:

```bash
rg -n "cost_per_success|pass@k cost|pass_at_k_cost|ROI|roi|economic lift|benchmark economics|GPU utilization|GPU power|GPU memory|temperature|speedup|throughput|latency|kernel_timing|benchmark|profiler|Nsight|nsight|NCU|ncu|statistical" \
  shared/observability \
  shared/tests/test_observability_*.py \
  cluster3/experiments/run_cluster3_modal.py \
  cluster3/tests/test_run_cluster3_modal_cli.py
```

Result: matches are limited to redaction deny rules, negative tests, existing
runner temperature configuration, and explicit absence assertions. No profiler,
GPU utilization, speedup, throughput, latency, benchmark economics, pass@k cost,
ROI, or statistical claim collection was added.

## Tests Run

```bash
.venv/bin/python -m pytest \
  shared/tests/test_observability_schema.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_imports.py \
  shared/tests/test_observability_logger.py -q
```

Result: `167 passed`.

```bash
.venv/bin/python -m pytest \
  cluster3/tests/test_run_cluster3_modal_cli.py -q
```

Result: `125 passed`.

```bash
.venv/bin/python -m pytest \
  cluster3/tests/test_cluster3_schema.py \
  cluster3/tests/test_cluster3_imports.py -q
```

Result: `152 passed`.

```bash
.venv/bin/python -m pytest \
  shared/tests/test_repair_history_policies.py \
  shared/tests/test_factorial_analysis.py -q
```

Result: `113 passed`.

## Forbidden-Files Check

Command:

```bash
git diff --name-only -- \
  cluster1 cluster2 cluster3/results cluster3/feedback \
  shared/modal_harness shared/analysis shared/repair_history outputs \
  pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock \
  Pipfile.lock mlruns
```

Result: empty output.

## Negative Scope Verification

- No Modal invocation.
- No generation run.
- No GPU job.
- No output mutation.
- No billing query.
- No pricing query.
- No dependency or lockfile change.
- No MLflow runtime state write.
- No analyzer change.
- No result-row schema mutation.
- No economic or scientific cost claim implementation.

`git diff --check` passed.

## Unresolved Risks

Real estimated cost remains unavailable until a later explicitly approved
supplied/config/static pricing source exists. Actual billing reconciliation is
still O5+ only and requires separate approval for credentials, billing APIs,
invoices, or billing CLI usage.

## Classification

`O4_ESTIMATED_COST_COMPLETE_WITH_CAVEATS`

## Next-Step Recommendation

Run an independent O4 review of the uncommitted changes. If it returns
`O4_REVIEW_PASS_COMMIT_ALLOWED`, commit O4 as its own package.
