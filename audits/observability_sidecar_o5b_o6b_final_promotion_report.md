# O5b-O6b Observability Promotion Audit

- Version: 1.0.0
- Date: 2026-06-04
- Branch: `codex/observability-o6-performance-contract`
- Baseline: `c41a5bc Audit O5a observability acceptance`
- Classification: `O5B_O6B_FINAL_PROMOTION_PASS_WITH_CAVEATS`

## Scope

This compact promotion audit covers the observability packages after O5a:

| Package | Commit | Status |
|---|---|---|
| O5b static/redacted billing reconciliation ingestion | `cf63de8` | committed |
| O5c Modal billing collection adapter | `dc48782` | committed / adapter-ready blocked |
| O6a Level-4 performance contract scaffolding | `d966ad0` | committed |
| O6b Modal GPU performance smoke sidecar | `403cfea` | committed |

No new Modal, GPU, benchmark, billing, generation, or output-mutation command
was run for this audit.

## O5b/O5c Result

O5b adds local-only static/redacted billing reconciliation ingestion. O5c adds a
deterministic Modal billing report collection adapter, but live collection
remains adapter-ready blocked by Modal billing-report limits. No nonempty raw or
redacted billing artifact is retained or committed, and no billing/economic
claim is made.

## O6a/O6b Result

O6a defines the Level-4 performance contract and required O6b packet fields.
O6b adds a dedicated performance sidecar schema/writer, pure timing-summary
helpers, an opt-in Modal smoke entrypoint, and one reviewed smoke sidecar:

```text
artifacts/observability_performance/o6b_smoke_relu_performance.jsonl
sha256: 716bda3a4be56e86543aa6327377649cf7ec2ddb2b4f74b587da86215ee7c931
```

The O6b sidecar contains exactly one row. Its `speedup_vs_baseline` is
`0.6657483682345889`, so the fixed Triton smoke fixture was slower than the
Torch reference in this single T4 smoke run. This is smoke-only evidence and is
not paper-scale performance evidence.

## Validation

Focused O5b/O5c/O6a/O6b test bundle:

```bash
.venv/bin/python -m pytest \
  shared/tests/test_observability_billing_reconciliation.py \
  shared/tests/test_observability_billing_modal_collection.py \
  shared/tests/test_observability_performance_contract.py \
  shared/tests/test_observability_performance_sidecar.py \
  shared/tests/test_observability_performance_harness.py \
  shared/tests/test_observability_imports.py -q
```

Result:

```text
150 passed
```

Additional checks:

```text
git diff --check: passed
protected-scope diff scan: empty
O6b packet required fields: no missing fields
O6b performance sidecar load: exactly one row
```

Profiler/Nsight/NCU scan hits were limited to explicit prohibitions, deny-list
fixtures, negative tests, and audit caveats. Claim-boundary scan hits were
limited to deny rules, negative fixtures, or explicit caveat/prohibition
language.

## Boundaries Preserved

- No additional O6b benchmark or Modal/GPU run was executed.
- No generation was run.
- No `outputs/` path was mutated.
- No Cluster 1/2/3 scientific result row schema was changed.
- No analyzer, MLflow runtime state, dependency, or lockfile change is included.
- No raw billing artifact, invoice, billing API response, credential, or payment
  payload is retained.
- No cost-per-success, pass@k cost, ROI, economic-lift, benchmark-economics, or
  paper-scale performance claim is made.
- No profiler, Nsight, NCU, NVML, Triton profiler, or trace persistence is
  included.

## Promotion Decision

The O5b/O5c/O6a/O6b package is ready for local fast-forward promotion into
`codex-track-handoff-context`.

```text
O5B_O6B_FINAL_PROMOTION_PASS_WITH_CAVEATS
```

After promotion, future O5c live billing retries and any broader O6 performance
benchmark work still require separate explicit approval packets.
