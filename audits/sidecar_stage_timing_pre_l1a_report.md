# Sidecar Stage Timing Pre-L1a Report

- Version: 1.0.0
- Date: 2026-06-05
- Branch: `codex/sidecar-stage-timing-pre-l1a`
- Baseline: `6160c88 Add Modal optimization intake plan`
- Status: `SIDECAR_STAGE_TIMING_PRE_L1A_COMPLETE`
- Citation status: evidence snapshot; do not cite as methodology or result evidence

## Executive Summary

This local-only package adds additive observability stage timing around the
Cluster 3 runner's existing dependency-injected local orchestration calls. The
implementation records sidecar events for generation, correctness evaluation,
P repair, C repair, and row append where each stage is actually active.

The patch does not run Modal, call a GPU, execute generation, execute an
experiment, mutate repository outputs, create artifacts, write `mlruns/`, query
billing, add dependencies, change lockfiles, or sign L1a.

## Files Changed

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `audits/sidecar_stage_timing_pre_l1a_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Timing Events Added

The existing observability sidecar stream now records these completed stage
names when applicable:

- `generation`
- `correctness_eval`
- `p_repair`
- `c_repair`
- `row_append`

`row_append` already existed and remains present. New pre-row helper methods
reuse the existing `ObservabilityEvent` schema, row identity schema, event
ordering, duration fields, summary aggregation, token metadata, cost metadata,
and Modal-context sidecar plumbing.

Diagnostic-seed rows omit initial `generation` timing because no generation
adapter call occurs on that path. Repair stages are omitted when the dispatcher
does not route into the corresponding repair path.

## Sidecar-Only Guarantee

Timing data is written only through the existing observability event sidecar
and event-derived summary. No timing field is added to `Cluster3EvalRow`, no
scientific row field is added, and no result-row serializer is changed.

The off-vs-required observability regression test writes the same local row
twice under the same runner config and proves the row JSON payload remains
byte-identical while the sidecar is additive.

## Scientific Boundary Preservation

The implementation wraps existing calls without changing their arguments,
return values, dispatch choices, model configuration, prompt construction,
grammar selection, repair policy, correctness extraction, row construction, or
row append behavior.

No execution packet is signed. L1a remains unsigned and non-executing.

## Tests Run

```text
.venv/bin/python -m compileall -q cluster3/experiments/run_cluster3_modal.py
passed

.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -k "observability or timing or stage or grammar_mode or dry_plan" -q
44 passed, 94 deselected in 2.76s

.venv/bin/python -m pytest shared/tests -k "observability or tracking_noop" -q
370 passed, 736 deselected in 2.81s

git diff --check
passed

git status --short --branch
## codex/sidecar-stage-timing-pre-l1a
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
 M docs/handoff/agentic_document_hub.md
 M docs/handoff/document_version_registry.md
 M docs/handoff/experiment_change_orchestration_state.md
?? audits/sidecar_stage_timing_pre_l1a_report.md
```

## No-Execution Proof

Execution authorization remains negative:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
MLFLOW_TRACKING_EXECUTION_AUTHORIZED: NO
```

No Modal command, GPU job, generation job, experiment run, benchmark, billing
query, repository output mutation, artifact creation, dependency change,
lockfile change, or MLflow runtime write was performed.

## No-Output Or MLRuns Mutation Proof

The implementation tests write only to pytest `tmp_path` directories. The
protected mutation scan over repository `outputs/`, `artifacts/`, `mlruns/`,
preliminary report artifacts, dependency files, and lockfiles was empty.

The positive execution-flag scan over current docs, audits, contracts, Cluster
3, and shared code reported only historical O6b approval text plus literal scan
examples outside this package. A zero-context added-line authorization scan was
empty.

The broad scientific-boundary scan reported diff context from historical docs
and one unchanged generation-call configuration scalar now inside the measured
wrapper. No new semantic toggle, route condition, row field, or claim text was
introduced.

## Remaining Risks

- Timing durations are caller-observed local monotonic durations for the runner
  call boundaries. They are not remote timing evidence.
- Generation and evaluation calls nested inside P/C internals are represented
  by the enclosing repair-stage duration in this package.
- Future signed L1a/L1b/L2 packets still need explicit observability policy,
  output paths, stop limits, spend limits, and approval.

## Classification

`SIDECAR_STAGE_TIMING_PRE_L1A_COMPLETE`

## Next-Step Recommendation

Review and commit this branch locally. After review, promote it into
`codex-track-handoff-context` before any L1a execution packet wording is
advanced.
