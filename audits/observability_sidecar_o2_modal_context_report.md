# Observability Sidecar O2 Modal Context Report

- Date: 2026-06-03
- Branch: `codex/observability-sidecar-core`
- Baseline: `74b3acd504f1dfc252c05a4c746fc9914c186b4d`
- Package: O2 Modal runtime context implementation
- Classification: `O2_MODAL_CONTEXT_COMPLETE_WITH_CAVEATS`

## Executive Summary

O2 adds optional safe Modal runtime context support to observability sidecars.
It does not run Modal, mutate outputs, add dependencies, query billing, change
`.remote()` behavior, or change scientific result rows.

Real remote Modal context remains unproven until a later approved execution
packet. This package proves schema, redaction, helper behavior, and Cluster 3
local fake wiring only.

## Worktree Status

Implementation was performed in:

```text
/Users/alexeidelgado/Desktop/TritonGen
branch: codex/observability-sidecar-core
```

The O2 baseline is the O2-Prep commit:

```text
74b3acd504f1dfc252c05a4c746fc9914c186b4d O2-Prep: Reconcile Modal context launch scope
```

## Target Surfaces

Code surfaces:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/modal_harness/runtime.py`
- `cluster3/experiments/run_cluster3_modal.py`

Test surfaces:

- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Doc/report surfaces:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `audits/observability_sidecar_o2_modal_context_report.md`

## Files Changed

Expected changed files are limited to the O2 allowed surfaces above.
Forbidden surfaces such as `outputs/`, `cluster3/results/`, `cluster1/`,
`cluster2/`, analyzers, repair history, dependencies, lockfiles, and `mlruns/`
remain untouched.

## Schema Context Summary

`ObservabilityModalContext` now requires explicit
`modal_context_available`. Unavailable context must use
`modal_context_source="unavailable"` and cannot carry runtime fields.

Safe optional fields remain allowlisted:

```text
is_remote
function_call_id
input_id
task_id
image_id
region
cloud_provider
environment_name
app_name
gpu_type
gpu_count
cpu_cores
memory_gib
timeout_s
container_started_at_utc
modal_context_source
```

Resource quantities reject negative and non-finite values through the strict
Pydantic schema.

## Redaction And Context Safety Summary

The redaction layer rejects Modal-private and out-of-scope operational payload
keys, including:

- tokens, secrets, credentials, passwords, authorization, API keys
- environment variable dumps
- Modal identity tokens
- billing, invoices, and actual cost fields
- GPU utilization, power, memory metric, and temperature fields
- profiler, kernel timing, latency, throughput, speedup, performance, and
  benchmark fields
- prompts, source text, raw model output, raw feedback, and raw compile logs

Existing safe hash/count/status keys remain allowed.

## Runtime Helper Summary

`shared/modal_harness/runtime.py` now exposes:

- `unavailable_modal_context()`
- `normalize_modal_context(raw_context)`
- `get_modal_runtime_context_or_unavailable(...)`
- existing `current_modal_ids()`

The helper uses a strict allowlist. It does not read environment variables,
query billing, query GPU metrics, invoke Modal remotely, or introduce
`.spawn()`. The existing `current_modal_ids()` behavior is preserved but now
imports Modal lazily.

## Cluster 3 Runner Wiring Summary

Cluster 3 O1 observability now carries a single optional
`ObservabilityModalContext` on sidecar events when observability is enabled.
The local runner uses dependency injection for supplied/mock context and
otherwise records unavailable context.

No result-row dataclass, result logger, analyzer, Modal app/image/function, or
scientific JSONL row schema changed.

## Off/Best_Effort/Required Behavior

- `off`: does not collect context and writes no sidecar.
- `best_effort`: context-provider errors degrade to unavailable context while
  preserving the runner outcome.
- `required`: invalid or forbidden context fails closed before runner work.
- enabled valid modes: sidecar events include supplied safe context and
  summaries record context availability counts/source labels.

## Result-Row Non-Mutation Proof

O2 changes only sidecar event payloads and summaries. It does not edit
`cluster3/results/` or any result dataclass/schema/logger.

Existing Cluster 3 tests still assert observability fields do not appear in
`Cluster3EvalRow`.

## Modal Invocation And Spawn Non-Change Proof

No `.remote()` call was changed and no `.spawn()` or `.spawn_map()` call was
introduced. Tests use local fake context providers and `tmp_path` sidecars.

Modal execution performed: no.

## Forbidden Telemetry Scan Results

Forbidden telemetry terms are expected only in redaction rules, negative tests,
or scope caveats. O2 does not implement billing, actual cost, GPU utilization,
GPU power, GPU memory metrics, GPU temperature, profiler data, kernel timing,
latency, throughput, speedup, benchmark, or performance telemetry.

## Privacy And Raw-Payload Scan Results

Forbidden private/raw payload terms are expected only in redaction rules,
negative tests, or scope caveats. O2 does not store prompts, source text, raw
model output, raw feedback, raw compile logs, secrets, credentials, identity
tokens, or environment dumps.

## Tests Run

```text
.venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_logger.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py -q
87 passed

.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -q
117 passed

.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py -q
152 passed

.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_factorial_analysis.py -q
113 passed
```

Static checks:

```text
git diff --check
passed

git diff --no-index --check /dev/null audits/observability_sidecar_o2_modal_context_report.md
no whitespace diagnostics; command exits 1 because the file is intentionally new
```

Scope scans:

```text
forbidden-file diff scan
empty

scientific row schema diff scan
empty

spawn diff scan
empty

positive execution-authorization scan
empty
```

The Modal invocation scan had only added `Modal` context wording/type-name
matches. It had no added `.remote()` or `.spawn()` behavior.

The forbidden telemetry/privacy/import scans were reviewed. Matches were
limited to existing runner config fields, historical docs, redaction deny
patterns, negative tests, or explicit scope caveats.

## Forbidden-Files Check

Expected result:

```text
git diff --name-only -- cluster1 cluster2 cluster3/results cluster3/feedback shared/analysis shared/repair_history outputs pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Output must be empty.

## Negative Scope Verification

O2 did not:

- invoke Modal
- run GPU work
- run generation
- mutate `outputs/`
- query billing or invoice APIs
- add cost/pricing logic
- add token telemetry
- add performance/profiler/timing/speedup telemetry
- add dependencies or lockfile changes
- modify result-row schemas
- modify analyzers

## Unresolved Risks

Real remote Modal context capture is not proven. A later approved execution
packet must validate remote behavior before any reportable remote-context claim.

## Classification

`O2_MODAL_CONTEXT_COMPLETE_WITH_CAVEATS`

The caveat is limited to remote runtime proof, not local implementation
completeness.

## Next-Step Recommendation

Run independent review on the O2 diff. Commit only after review returns an O2
pass verdict allowing commit.
