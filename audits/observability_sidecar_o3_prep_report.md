# O3-Prep Observability Token Telemetry Launch Reconciliation

## Executive Summary

O3-Prep is a docs-only reconciliation for token telemetry sidecars. It records
O2 as committed, narrows O3 token telemetry to counts/status only, names the
later O3 implementation surfaces, and preserves the boundary that scientific
JSONL result rows remain the source of truth.

No O3 runtime code has started. This report authorizes no Modal execution, GPU
work, generation, experiments, output mutation, tokenizer/model imports for
telemetry, dependency changes, billing/cost work, performance telemetry, MLflow
runtime state, or result-row schema changes.

## Worktree Status

- Repository: `/Users/alexeidelgado/Desktop/TritonGen`
- Branch: `codex/observability-sidecar-core`
- Baseline: `6f3001e32f5145bd0efadf7a9e60f87bfe3f323a`
- Initial status: clean before O3-Prep edits
- O3-Prep changed files are docs/audit surfaces only.

## O2 Committed Baseline

O2 Modal runtime context is committed at:

```text
6f3001e O2: Add Modal runtime context sidecar support
```

O2 remains sidecar-only and does not authorize Modal execution, output mutation,
generation, billing, cost, performance telemetry, or result-row schema changes.

## O3 Target Surfaces

Later O3 implementation target surfaces are explicit:

- `shared/observability/schema.py`
- `shared/observability/redaction.py`
- `shared/observability/logger.py`
- `cluster3/experiments/run_cluster3_modal.py`

Later O3 test surfaces are explicit:

- `shared/tests/test_observability_schema.py`
- `shared/tests/test_observability_redaction.py`
- `shared/tests/test_observability_logger.py`
- `shared/tests/test_observability_imports.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

`shared/observability/logger.py` is in scope only for validating summary
`token_totals` against the current event sidecar, matching the existing
event-count and stage-duration audit pattern.

## O3 Allowed Files

O3-Prep may modify only:

- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `docs/16_observability_sidecar_implementation_spec.md`
- `audits/observability_sidecar_o3_prep_report.md`

Later O3 implementation may modify only:

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
- `audits/observability_sidecar_o3_token_telemetry_report.md`

## O3 Forbidden Files

O3-Prep must not modify:

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

Later O3 implementation must not modify:

- `cluster1/**`
- `cluster2/**` except read-only inspection
- `cluster3/results/**`
- `cluster3/feedback/**` except read-only inspection
- `shared/modal_harness/**`
- `shared/analysis/**`
- `shared/repair_history/**`
- `outputs/**`
- `mlruns/**`
- pricing/billing files
- dependency files
- lockfiles
- Modal app/image/function definitions
- scientific result-row schemas
- analyzers

## Allowed Token Telemetry Fields

Allowed O3 token telemetry is counts/status only:

- `token_counts_available`
- `prompt_tokens`
- `generated_tokens`
- `total_tokens`
- `token_count_source` or schema-compatible `count_source` during migration
- `token_count_status` or unavailable equivalent

Allowed token count sources:

- `generation_sequence_length_delta`
- `existing_generation_result`
- `existing_remote_payload`
- `unavailable`
- `not_applicable`

Counts must be non-negative integers. Non-finite, string, float, coerced, or
negative counts must be rejected. When `prompt_tokens`, `generated_tokens`, and
`total_tokens` are all present, `total_tokens` must equal
`prompt_tokens + generated_tokens`.

## Forbidden Token Payloads

O3 must fail closed on:

- `token_ids`
- `input_ids`
- `output_ids`
- `prompt_text`
- `completion_text`
- `generated_text`
- `raw_output`
- `raw_completion`
- `source_text`
- `full_source`
- tokenizer dump
- tokenizer internal state
- hidden prompts
- private eval/feedback details
- raw model output
- raw feedback
- generated source text

## O3 Behavior Constraints

- No generation run.
- No model call.
- No tokenizer/model import in `shared/observability`.
- No tokenizer/model invocation only for telemetry.
- No prompt text, source text, generated text, raw output, raw completion, raw
  feedback, or token ID storage.
- No result-row schema mutation.
- No output mutation.
- No billing, cost, or performance work.
- Observability remains default-off.
- Omitted/off behavior remains unchanged.
- Token counts may be recorded only if already available in the current code
  path, returned by an existing generation payload, cheaply computable from
  already materialized sequence lengths, or supplied by tests/fakes.
- If counts are absent, O3 must record unavailable status rather than invoking
  tokenizer/model/runtime paths.

## Required O3 Tests

- Valid counts accepted.
- Missing counts unavailable-safe.
- Negative, non-int, non-finite, string, float, or coerced counts rejected.
- `total_tokens` consistency enforced.
- Token IDs rejected.
- Prompt/generated/source/raw text rejected.
- Tokenizer dumps/internal state rejected.
- No tokenizer/model imports in `shared/observability`.
- Off mode unchanged.
- Enabled sidecars can include supplied counts.
- Summary `token_totals` match the event stream.
- No result-row mutation.
- No outputs mutation.
- No generation/model/tokenizer execution.

## Stop Conditions

- `O3_PREP_BLOCKED_TARGET_SURFACE_AMBIGUOUS`
- `O3_PREP_BLOCKED_EXECUTION_AUTHORIZATION_LEAK`
- `O3_PREP_BLOCKED_SCOPE_VIOLATION`
- `O3_PREP_BLOCKED_DOC_CONTRADICTION`
- Any runtime code edit during O3-Prep.
- Any output mutation.
- Any dependency or lockfile change.
- Any MLflow runtime state write.
- Any token ID storage.
- Any prompt/source/generated/raw text storage.
- Any private eval/feedback leakage.
- Any tokenizer/model import in `shared/observability`.
- Any generation/model/tokenizer execution.
- Any billing/cost broadening.
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
git status --short --branch
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -16
git diff --check
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
rg -n "<positive execution authorization YES patterns from the O3-Prep prompt>" \
  docs/handoff audits docs/16_observability_sidecar_implementation_spec.md
rg -n "token_ids|input_ids|output_ids|prompt_text|completion_text|generated_text|raw_output|raw_completion|source_text|full_source|tokenizer dump|tokenizer internal|hidden prompt|generation run|model call|billing|cost|speedup|throughput|latency|kernel_timing|profiler|Nsight|NCU" \
  docs/handoff/experiment_change_orchestration_state.md \
  docs/handoff/document_version_registry.md \
  docs/handoff/agentic_document_hub.md \
  docs/16_observability_sidecar_implementation_spec.md \
  audits/observability_sidecar_o3_prep_report.md
```

## Forbidden-Scope Scan Results

- `git diff --check`: passed.
- Direct no-index whitespace check for this new report: passed.
- Forbidden code-scope diff for runtime/code/output/dependency/lockfile/MLflow
  paths: empty.
- Positive authorization scan: empty after removing the literal scan pattern from
  this report's command listing.
- Forbidden O3 scope scan: matches were explicit prohibitions, caveats, stop
  conditions, historical policy text, or scan-command text. No match authorized
  token IDs, prompt/source/generated/raw text storage, generation/model/tokenizer
  execution, billing/cost work, or performance telemetry.

## Unresolved Risks

- O3 implementation still needs to inspect actual generation payload shapes before
  deciding whether counts are already available. If counts are absent or require
  invoking tokenizer/model paths, O3 must record unavailable status.
- Existing O0 token schema currently contains fields that O3-Prep now treats as
  out of scope for O3 telemetry. O3 implementation must tighten or migrate the
  schema without changing scientific result rows.
- Real remote token visibility remains unproven until a later approved execution
  packet. O3 implementation must rely on local fakes/tests only unless explicit
  execution approval is granted later.

## Classification

O3_PREP_COMPLETE

## Next-Step Recommendation

Review the docs-only diff and commit O3-Prep before any O3 implementation
starts. The next O3 implementation agent should use the target surfaces and stop
conditions named here and in
`docs/handoff/experiment_change_orchestration_state.md`.
