# Observability Sidecar O2-Prep Report

## Executive Summary

O2-Prep reconciles launch documentation for O2 Modal runtime context before any
runtime implementation starts. O1 Cluster 3 observability instrumentation is
committed at `8eaef2e`. O2 target surfaces are explicit, and this package is
docs-only.

O2 implementation is limited to optional safe Modal context sidecar enrichment
when context is already available or dependency-injected. O2 does not authorize
Modal execution, generation, GPU work, output mutation, result-row schema
changes, billing, cost logic, token telemetry, dependencies, lockfiles, MLflow
runtime state, or performance/profiler/timing/speedup work.

## Worktree Status

- Repository: `/Users/alexeidelgado/Desktop/TritonGen`
- Branch: `codex/observability-sidecar-core`
- O2-Prep baseline: `8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a`
- Baseline subject: `O1: Add Cluster 3 observability instrumentation`
- O2-Prep scope: docs and audit report only

## O1 Committed Baseline

Required prior packages are present:

- O0: `bcdaedea4e76b1820978167e1b8439546ba2cc61`
- O1 target naming: `f088c10f2f5466e22c272665820c459bdda30ad1`
- O1 implementation: `8eaef2e52b881d5cf4a3fcfaeefc907daf2dfc2a`

O1 target remains `cluster3/experiments/run_cluster3_modal.py`.

## O2 Target Surfaces

Later O2 implementation may touch only these runtime/code surfaces:

- `shared/observability/schema.py`: tighten or validate optional safe Modal
  context fields already represented by `ObservabilityModalContext`.
- `shared/observability/redaction.py`: enforce Modal-specific allowlist and
  denylist behavior for context fields and environment-key shaped inputs.
- `shared/modal_harness/runtime.py`: expose safe existing Modal runtime
  identifiers from `current_modal_ids()` or equivalent helper behavior without
  changing Modal invocation semantics.
- `cluster3/experiments/run_cluster3_modal.py`: pass optional safe Modal
  context into existing O1 sidecar events and summaries only.

Later O2 tests are expected in:

- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

If these surfaces become ambiguous, O2 must stop with
`O2_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS`.

## O2 Allowed Files

O2-Prep allowed files:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/16_observability_sidecar_implementation_spec.md` only for narrow O2
  clarification
- `audits/observability_sidecar_o2_prep_report.md`

Later O2 implementation allowed files after `O2_PREP_COMPLETE`:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/__init__.py` only if exports need updating
- `shared/modal_harness/runtime.py`
- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- optional `audits/observability_sidecar_o2_modal_context_report.md`

## O2 Forbidden Files

O2-Prep must not modify:

- `shared/observability/**`
- `shared/modal_harness/**`
- `cluster1/**`
- `cluster2/**`
- `cluster3/**`
- `shared/analysis/**`
- `shared/repair_history/**`
- `outputs/**`
- `mlruns/**`
- `pyproject.toml`
- requirements files
- lockfiles

Later O2 implementation must not modify:

- `cluster1/**`
- `cluster2/**` except read-only inspection
- `cluster3/results/**`
- scientific result-row schemas
- analyzers
- `shared/analysis/**`
- `shared/repair_history/**`
- `outputs/**`
- `mlruns/**`
- pricing or billing files
- dependency or lock files
- Modal app/image/function definitions unless a later approved spec explicitly
  authorizes them

## Safe Modal Context Fields

Allowed safe context fields:

- `modal_context_available` or the schema-equivalent unavailable status
- `is_remote`
- `function_call_id`
- `input_id`
- `task_id`
- `image_id`
- `region`
- `cloud_provider`
- `environment_name`
- `app_name`
- `gpu_type`
- `gpu_count`
- `cpu_cores`
- `memory_gib`
- `timeout_s`
- `container_started_at_utc`
- `modal_context_source`

Allowed context sources:

- `shared_modal_runtime_helper`
- `modal_environment_allowlist`
- `runner_config`
- `unavailable`

Allowed Modal environment keys:

- `MODAL_TASK_ID`
- `MODAL_IMAGE_ID`
- `MODAL_REGION`
- `MODAL_CLOUD_PROVIDER`
- `MODAL_ENVIRONMENT`
- `MODAL_IS_REMOTE`

## Forbidden Modal Context Fields

Forbidden capture:

- secrets
- tokens
- credentials
- passwords
- API keys
- environment variable dumps
- Modal identity tokens, including `MODAL_IDENTITY_TOKEN`
- billing data
- invoice data
- actual cost
- GPU utilization
- GPU power
- GPU memory metrics
- GPU temperature
- profiler data
- kernel timing
- latency
- throughput
- speedup
- performance metrics
- prompts
- source text
- raw model output
- raw feedback
- raw compile logs

## O2 Behavior Constraints

- No `.remote()` to `.spawn()` switch.
- No new Modal invocation.
- No GPU run.
- No generation run.
- No output mutation.
- No scientific result-row schema mutation.
- No billing, cost, pricing, or invoice logic.
- No performance, profiler, timing, speedup, latency, throughput, or kernel
  benchmark telemetry.
- O2 only enriches sidecar events when safe context is already present,
  unavailable-safe, or dependency-injected in tests.
- Observability mode still defaults to `off`.
- Omitted/off behavior remains unchanged.
- Missing context records unavailable/false rather than crashing.

## Required O2 Tests

Later O2 implementation must test:

- safe context fields accepted;
- forbidden Modal, secrets, token, credential, and env-dump fields rejected;
- no Modal import in `shared/observability` core unless the spec explicitly
  allows it;
- no `.spawn()` introduction;
- no new Modal invocation in tests;
- off mode unchanged;
- `best_effort` and `required` sidecars can include safe context when supplied;
- missing context marks `modal_context_available` false or
  `modal_context_source=unavailable`;
- no result-row schema mutation;
- no outputs mutation.

## Stop Conditions

- `O2_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS`: exact O2 target surface cannot be
  named.
- `O2_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK`: any doc authorizes Modal, GPU,
  generation, output mutation, n=5, n=20, or paper-scale execution.
- `O2_PREP_BLOCKED_SCOPE_VIOLATION`: runtime code, outputs, dependencies,
  lockfiles, or MLflow runtime state are modified.
- `O2_PREP_BLOCKED_DOC_CONTRADICTION`: docs conflict on O2 target, allowed
  files, or authorization state.
- Stop on any secret, token, credential, env-dump, GPU metric, billing, cost,
  invoice, performance, profiler, timing, speedup, latency, throughput, result
  schema, or output-mutation requirement.

## Authorization State

- `AUTHORIZES_EXECUTION: NO`
- `MODAL_AUTHORIZED: NO`
- `GENERATION_AUTHORIZED: NO`
- `GPU_AUTHORIZED: NO`
- `OUTPUT_MUTATION_AUTHORIZED: NO`
- `N5_AUTHORIZED: NO`
- `N20_AUTHORIZED: NO`
- `PAPER_SCALE_AUTHORIZED: NO`
- `BILLING_AUTHORIZED: NO`
- `DEPENDENCY_CHANGE_AUTHORIZED: NO`

## Validation Commands

Commands run:

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
rg -n "<positive execution authorization patterns>" \
  docs/handoff audits docs/16_observability_sidecar_implementation_spec.md
rg -n "spawn|GPU utilization|GPU power|GPU memory|temperature|billing|invoice|actual cost|speedup|throughput|latency|kernel_timing|profiler|Nsight|NCU|secret|credential|token|environment variable dump" \
  docs/handoff/experiment_change_orchestration_state.md \
  docs/handoff/document_version_registry.md \
  docs/handoff/agentic_document_hub.md \
  docs/16_observability_sidecar_implementation_spec.md \
  audits/observability_sidecar_o2_prep_report.md
git diff --no-index --check /dev/null \
  audits/observability_sidecar_o2_prep_report.md
```

Results:

- `git diff --check`: passed.
- `git status --short --branch`: docs-only O2-Prep changes present on
  `codex/observability-sidecar-core`.
- Forbidden code-scope diff: empty output.
- Positive authorization scan: empty output.
- Forbidden O2 scope scan: matches are prohibitions, caveats, stop conditions,
  or validation command text only; no implemented telemetry fields.
- New report no-index whitespace check: no diagnostics.

## Forbidden-Scope Scan Results

Changed files are limited to:

- `docs/handoff/agentic_document_hub.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `audits/observability_sidecar_o2_prep_report.md`

Forbidden code-scope diff for `shared/observability`, `shared/modal_harness`,
`cluster1`, `cluster2`, `cluster3`, `shared/analysis`,
`shared/repair_history`, `outputs`, dependency files, lockfiles, and `mlruns`
was empty.

## Unresolved Risks

- O2 implementation still needs a focused code review because it will touch
  runner and Modal helper surfaces.
- O2 context availability in real remote containers remains unproven until a
  separately approved run packet allows execution.
- O2 does not implement O3 token counts, O4 estimated cost, or O5 billing
  reconciliation.

## Classification

O2_PREP_COMPLETE

## Next-Step Recommendation

Start O2 implementation within the named target surfaces only. Do not run
Modal, mutate outputs, or broaden into token, cost, billing, performance,
analyzer, or result-row schema work without a later approved package and run
packet.
