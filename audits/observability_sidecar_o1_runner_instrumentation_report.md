# Observability Sidecar O1 Runner Instrumentation Report

- Date: 2026-06-03
- Branch: `codex/observability-sidecar-core`
- Package: O1 Cluster 3 local runner instrumentation
- Classification: `O1_LOCAL_RUNNER_INSTRUMENTATION_COMPLETE_WITH_CAVEATS`

## Executive Summary

O1 adds opt-in observability sidecar instrumentation to the named Cluster 3
local runner only: `cluster3/experiments/run_cluster3_modal.py`.

The new interface is disabled by default and writes no sidecars when omitted or
set to `off`. Enabled modes require explicit `experiment_id` and `run_id`, use
the O0 path/logger/schema helpers, and write local run, row, row-append stage,
summary, and hash sidecars only when explicitly enabled.

No Modal, GPU, generation job, experiment run, n=5, n=20, paper-scale work,
`outputs/` mutation, dependency, lockfile, result-row schema, analyzer, billing,
token telemetry, cost-estimation, MLflow runtime state, or Modal runtime identity
work was performed.

## Worktree Status

Implementation was performed in `/Users/alexeidelgado/Desktop/TritonGen` on
`codex/observability-sidecar-core`, starting from O0 plus the O1 target-naming
docs commit `f088c10`.

At report-writing time the O1 implementation is local and uncommitted pending
review.

## Target Runner Identified

Source-of-truth orchestration state names:

- target runner: `cluster3/experiments/run_cluster3_modal.py`
- primary tests: `cluster3/tests/test_run_cluster3_modal_cli.py`

No other runner was selected or modified.

## Files Changed

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `audits/observability_sidecar_o1_runner_instrumentation_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`

## Observability Mode Interface

The runner now accepts:

```text
--observability-mode off|best_effort|required
--observability-experiment-id <id>
--observability-run-id <id>
--observability-output <optional path>
```

Default is `off`. Enabled modes require both IDs. Invalid modes fail through the
existing argparse choices before runner execution.

## Sidecar Event Behavior

When enabled, O1 records these O0-schema-valid events:

- `run_started`
- `row_started`
- `stage_started` for local `row_append`
- `stage_completed` for local `row_append`
- `row_completed`
- `run_completed`

Events use UUID event IDs and zero-based contiguous event sequences. Row events
include public row identity, hashes, condition, kernel class, dtype, base seed,
attempt indexes, and safe route booleans. They do not record source text,
prompt text, raw feedback, raw compile logs, private eval details, token IDs,
secrets, performance/profiler fields, billing claims, or scientific claims.

## Legacy Behavior Proof

Tests prove:

- omitted observability args parse as `off`
- explicit `off` writes no observability event, summary, or hash sidecar
- observability fields are excluded from the stable scientific run-id hash
- existing Cluster 3 runner CLI tests still pass

## Sidecar Path Behavior

When `--observability-output` is supplied and observability is enabled, it is
used as the event JSONL sidecar path and validated by the O0 path resolver
before generated-cell work. The summary path remains the result-based default
and the hash sidecar is event-path based, matching O0 conventions.

When no custom event path is supplied and observability is enabled, the O0
result-adjacent default paths are used.

When mode is `off`, no sidecar paths are resolved or written.

## Failure Behavior

- `off`: no observability logger is constructed and no sidecars are written.
- `best_effort`: setup/write failure disables observability and preserves runner
  outcome.
- `required`: setup/path/write failure raises and fails closed.

Tests prove required path collision and required logger setup failure occur
before generation/correctness adapters are called.

## Schema/Result-Row Non-Mutation Proof

O1 did not edit `cluster3/results/` or any scientific result dataclass/schema.
Tests assert `Cluster3EvalRow` does not gain observability, duration, token, or
cost fields.

Scientific JSONL rows remain the source of truth for experimental outcomes.
Sidecars are adjacent operational audit artifacts only.

## Import/Dependency Boundary Proof

No dependencies or lockfiles were changed. O1 imports the already-implemented
O0 `shared.observability` helpers and Python standard-library modules only.

The forbidden dependency/import scan produced only pre-existing target-runner
metadata labels for `xgrammar_version` and `transformers_version`, plus the O0
import-boundary test's forbidden import tuple. No new Modal, Torch, Triton,
Transformers, XGrammar, MLflow, OpenAI, Anthropic, Google, boto3, or wandb import
was introduced by O1.

## Forbidden Telemetry Scan Results

Forbidden performance/scientific-claim scan matches were limited to negative
assertions in `cluster3/tests/test_run_cluster3_modal_cli.py` and an existing
O0 schema rejection test for `benchmark_started`.

O1 implements orchestration duration fields already allowed by the O0 schema.
It does not implement profiler, speedup, throughput, latency, kernel timing,
benchmark, actual cost, invoice, billing-claim, cost-per-success, pass@k, lift,
or statistical-claim telemetry.

## Resume Behavior

Enabled observability with Cluster 3 `resume` mode is intentionally rejected in
O1 until a dedicated resume-sidecar policy exists. Legacy scientific `resume`
behavior remains available when observability mode is omitted or set to `off`.

## Privacy/Raw-Payload Scan Results

Forbidden raw/private-payload scan matches were limited to negative assertions
in the new O1 tests and existing O0 redaction/logger rejection tests and
denylist rules.

O1 does not store prompt text, source text, full source, raw feedback, raw
compile logs, private eval details, hidden eval data, token IDs, secrets,
credentials, passwords, API keys, or authorization values.

## Tests Run

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -q
```

Result: `112 passed`.

```bash
.venv/bin/python -m pytest shared/tests/test_observability_schema.py shared/tests/test_observability_logger.py shared/tests/test_observability_redaction.py shared/tests/test_observability_imports.py -q
```

Result: `59 passed`.

```bash
.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py -q
```

Result: `152 passed`.

```bash
.venv/bin/python -m pytest shared/tests/test_repair_history_policies.py shared/tests/test_factorial_analysis.py -q
```

Result: `113 passed`.

## Forbidden-Files Check

Forbidden-scope diff checks for Cluster 1, Cluster 2, Cluster 3 result/feedback
surfaces, shared analysis/repair-history/modal-harness surfaces, outputs,
dependencies, lockfiles, and MLflow runtime state returned empty output.

Scientific row schema diff checks for Cluster 1, Cluster 2 results, and Cluster
3 results returned empty output.

## Negative Scope Verification

No Modal command was run. No GPU, generation, experiment, n=5, n=20,
paper-scale, output-mutating, billing, pricing, token telemetry, cost-estimate,
MLflow runtime, dependency, or lockfile work was performed.

Tests use `tmp_path` and dependency-injected fakes only.

## Unresolved Risks

- This is local runner instrumentation only. It does not prove coverage for a
  real Modal/generation run.
- Enabled observability resume is blocked in O1 until an explicit resume event
  and summary-completeness policy is specified and tested.
- Event coverage is limited to local run, row, and row-append orchestration.
  O2/O3/O4 remain required for Modal context, token counts, and estimated cost.
- Independent review is still required before promotion.

## Classification

`O1_LOCAL_RUNNER_INSTRUMENTATION_COMPLETE_WITH_CAVEATS`

The caveats are the deliberate lack of run authorization and the pre-existing
target-runner metadata labels caught by the dependency scan.

## Next-Step Recommendation

Run independent review of the O1 local changes. If review passes, commit the O1
package as a single slice. Do not start O2/O3/O4 or make observability-covered
run claims until O1 is reviewed and promoted.
