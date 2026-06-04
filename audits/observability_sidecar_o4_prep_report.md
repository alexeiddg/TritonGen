# O4-Prep Observability Estimated Cost Telemetry Launch Reconciliation

## Executive Summary

O4-Prep is a docs-only reconciliation for estimated cost telemetry sidecars. It
records O3 as committed, narrows O4 to supplied/static estimated or unavailable
cost metadata only, names the later O4 implementation surfaces, and preserves
the boundary that scientific JSONL result rows remain the source of truth.

No O4 runtime code has started. This report authorizes no Modal execution, GPU
work, generation, experiments, output mutation, billing API calls, invoice
queries, provider or Modal billing queries, external pricing fetches, analyzer
or economic metric changes, dependency changes, MLflow runtime state, or
result-row schema changes.

## Worktree Status

- Repository: `/Users/alexeidelgado/Desktop/TritonGen`
- Branch: `codex/observability-sidecar-core`
- Baseline: `4ddc7673724a709f8a028b4d52e39b48144b56eb`
- Initial status: clean before O4-Prep edits
- O4-Prep changed files are docs/audit surfaces only.

## O3 Committed Baseline

O3 token telemetry is committed at:

```text
4ddc767 Implement O3 token telemetry
```

O3 remains sidecar-only count/status token telemetry and does not authorize
Modal execution, output mutation, generation, billing, cost, performance
telemetry, tokenizer/model execution, or result-row schema changes.

## O4 Target Surfaces

Later O4 implementation target surfaces are explicit:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/logger.py`
- `cluster3/experiments/run_cluster3_modal.py`

Later O4 test surfaces are explicit:

- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_logger.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

`cluster3/experiments/run_cluster3_modal.py` is in later O4 scope only to pass
supplied estimated/unavailable cost metadata into existing O1 sidecar events. It
must not change Modal invocation behavior, result rows, outputs, analyzers, or
economic reporting.

## O4 Allowed Files

O4-Prep may modify only:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/16_observability_sidecar_implementation_spec.md`
- `audits/observability_sidecar_o4_prep_report.md`

Later O4 implementation may modify only:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/logger.py`
- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_logger.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- optional `audits/observability_sidecar_o4_estimated_cost_report.md`

## O4 Forbidden Files

O4-Prep must not modify:

- `shared/observability/**`
- `shared/modal_harness/**`
- `cluster1/**`
- `cluster2/**`
- `cluster3/**`
- `shared/analysis/**`
- `shared/repair_history/**`
- `outputs/**`
- `mlruns/**`
- dependency files
- lockfiles

Later O4 implementation must not modify:

- `cluster1/**`
- `cluster2/**` except read-only inspection
- `cluster3/results/**`
- `cluster3/feedback/**` except read-only inspection
- `shared/modal_harness/**`
- `shared/analysis/**`
- `shared/repair_history/**`
- `outputs/**`
- `mlruns/**`
- dependency files
- lockfiles
- Modal app/image/function definitions
- scientific result-row schemas
- analyzers
- billing or pricing API clients
- invoice dumps
- pricing snapshot directories unless a later approved O4 amendment explicitly
  adds them

## Allowed Estimated-Cost Fields

Allowed O4 cost telemetry is estimated/unavailable metadata only:

- `cost_estimate_available`
- `estimated_input_cost`
- `estimated_output_cost`
- `estimated_total_cost`
- `currency`
- `pricing_source`
- `pricing_source_version`
- `cost_estimate_status`
- `cost_estimate_method`

Constraints:

- fields are sidecar-only;
- monetary values must be non-negative finite numbers;
- negative, non-finite, string, boolean, or coerced cost values must be
  rejected;
- `currency` is bounded to `USD` unless a later spec amendment adds another
  currency and conversion policy;
- `estimated_total_cost` must equal `estimated_input_cost +
  estimated_output_cost` when both component estimates are present;
- unavailable estimates cannot carry cost values;
- `pricing_source` and `pricing_source_version` identify a supplied/static basis
  only and are not billing evidence.

## Forbidden Cost/Billing Payloads

O4 must fail closed on:

- `actual_cost`
- `actual_billing`
- `invoice`
- `account_charge`
- `provider_bill`
- `modal_bill`
- `credit_card`
- `payment_method`
- `billing_account`
- `cost_per_success`
- `cost_per_pass`
- `pass_at_k_cost`
- `ROI`
- `economic_lift`
- `benchmark_cost_conclusion`
- `billing_api_response`
- `pricing_api_response`
- `cloud_invoice_dump`

## O4 Behavior Constraints

- No billing API query.
- No invoice query.
- No Modal billing query.
- No provider billing query.
- No external pricing fetch.
- No generation run.
- No model/tokenizer execution.
- No output mutation.
- No result-row schema mutation.
- No analyzer or economic metric changes.
- No pass@k, cost-per-success, ROI, lift, statistical, paper-scale, or benchmark
  economics claims.
- Observability remains default-off.
- Omitted/off behavior remains unchanged.
- Cost estimates may be recorded only if supplied by config, tests, fakes, or an
  explicitly approved static table.
- Real actual cost remains O5+ only.

## Required O4 Tests

- Valid estimated costs accepted.
- Missing cost estimates unavailable-safe.
- Negative, non-finite, string, boolean, or coerced costs rejected.
- `estimated_total_cost` consistency enforced.
- Unavailable estimates cannot carry cost values.
- Actual billing, invoice, and account charge fields rejected.
- Cost-per-success, pass@k cost, ROI, economic-lift, and benchmark-economics
  fields rejected.
- Billing API and pricing API response payloads rejected.
- No billing/provider/Modal/cloud API imports in `shared/observability`.
- Off mode unchanged.
- Enabled sidecars can include supplied estimated-cost metadata.
- Invalid estimated cost degrades safely in `best_effort`.
- Invalid estimated cost fails closed in `required` mode.
- No result-row mutation.
- No outputs mutation.
- No billing API execution.
- No generation/model/tokenizer execution.

## Stop Conditions

- `O4_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS`
- `O4_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK`
- `O4_PREP_BLOCKED_BILLING_CLAIM_LEAK`
- `O4_PREP_BLOCKED_SCOPE_VIOLATION`
- `O4_PREP_BLOCKED_DOC_CONTRADICTION`
- Any runtime code edit during O4-Prep.
- Any output mutation.
- Any dependency or lockfile change.
- Any MLflow runtime state write.
- Any actual billing, invoice, account-charge, provider bill, or Modal bill
  capture.
- Any billing API, pricing API, cloud invoice, dashboard, or external pricing
  fetch.
- Any cost-per-success, pass@k cost, ROI, economic-lift, benchmark-economics, or
  paper-scale cost conclusion.
- Any generation/model/tokenizer execution.
- Any analyzer, statistical, or economic broadening.
- Any performance/profiler/timing/speedup/latency/throughput capture.
- Any result-row schema mutation.

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
BILLING_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

## Validation Commands

```bash
git diff --check

git status --short --branch

git diff --name-only -- \
  shared/observability \
  shared/modal_harness \
  cluster1 \
  cluster2 \
  cluster3 \
  shared/analysis \
  shared/repair_history \
  outputs \
  pyproject.toml \
  requirements.txt \
  requirements-dev.txt \
  uv.lock \
  poetry.lock \
  Pipfile.lock \
  mlruns

rg -n "AUTHORIZES_EXECUTION: YE[S]|MODAL_AUTHORIZED: YE[S]|GENERATION_AUTHORIZED: YE[S]|OUTPUT_MUTATION_AUTHORIZED: YE[S]|GPU_AUTHORIZED: YE[S]|N5_AUTHORIZED: YE[S]|N20_AUTHORIZED: YE[S]|PAPER_SCALE_AUTHORIZED: YE[S]|BILLING_AUTHORIZED: YE[S]|DEPENDENCY_CHANGE_AUTHORIZED: YE[S]" \
  docs/handoff audits docs/16_observability_sidecar_implementation_spec.md

rg -n "actual_cost|actual billing|invoice|account charge|provider bill|modal bill|credit_card|payment method|billing account|cost_per_success|cost_per_pass|pass_at_k_cost|ROI|economic lift|benchmark cost|billing API|pricing API|cloud invoice|external pricing fetch|generation run|model call|tokenizer|pricing snapshot|pinned pricing|estimated_gpu|estimated_cpu|estimated_memory|estimate_status|price_snapshot_id|estimation_confidence|cost_basis|estimated_total_cost_usd" \
  docs/handoff/experiment_change_orchestration_state.md \
  docs/handoff/document_version_registry.md \
  docs/handoff/agentic_document_hub.md \
  docs/16_observability_sidecar_implementation_spec.md \
  audits/observability_sidecar_o4_prep_report.md
```

## Forbidden-Scope Scan Results

- `git diff --check`: passed.
- `git status --short --branch`: changed files are limited to the O4-Prep
  docs/audit surfaces.
- Forbidden code-scope diff: empty; no runtime code, outputs, dependencies,
  lockfiles, or MLflow runtime state changed.
- Positive authorization scan: empty after avoiding self-matching command text;
  no doc grants Modal, GPU, generation, output mutation, n=5, n=20, paper-scale,
  or execution authorization.
- Forbidden O4 cost/billing scope scan: hits are explicit prohibitions, caveats,
  stop conditions, historical O3/token caveats, O5 future-work caveats, or
  command text. No hit authorizes actual billing, invoices, account charges,
  provider/Modal billing, external pricing fetches, cost-per-success, pass@k
  cost, ROI, economic lift, benchmark economics, generation, tokenizer/model
  execution, output mutation, analyzer changes, or result-row schema changes.

## Unresolved Risks

- The current O0-O3 `ObservabilityCostEstimate` schema contains older draft cost
  fields. Later O4 implementation must reconcile that schema to the allowed O4
  field set before acceptance.
- O4 will support supplied/static estimates only. Actual billing reconciliation,
  invoices, and cost attribution remain O5+ and require explicit approval.
- No real cost values are proven by O4-Prep. It is a launch reconciliation only.

## Classification

`O4_PREP_COMPLETE`

## Next-Step Recommendation

Run independent O4-Prep docs-only review. If it returns an explicit pass verdict,
commit the docs-only reconciliation. Start O4 implementation only after O4-Prep
is committed and keep it within the named surfaces and authorization boundaries.
