# Modal Optimization Intake Review Report

- Version: 1.0.0
- Date: 2026-06-05
- Branch: `codex/modal-optimization-intake-review`
- Baseline: `76ede6a Audit 12-cell launcher support promotion`
- Status: `MODAL_OPTIMIZATION_INTAKE_REVIEW_PASS_READY_TO_COMMIT`
- Citation status: evidence snapshot; do not cite as methodology or result evidence

## Executive Summary

This intake isolates the parked Modal optimization planning work before any L1a
execution packet. The available parked artifact is
`docs/19_modal_full_factorial_optimization_plan.md`. It is a planning and
research draft, not execution authorization.

The reported sidecar-only stage timing patch is not present as a tracked dirty
diff in this worktree. Baseline Cluster 3 observability code already contains
stage events and duration summaries, but there is no separate uncommitted timing
patch to classify or accept in this intake branch.

The planning draft was patched only to add an explicit re-verification
requirement for Modal API, GPU, and pricing claims before any signed execution,
benchmark, billing, or spend packet.

## Worktree State

Pre-branch state on `codex-track-handoff-context`:

```text
## codex-track-handoff-context...origin/codex-track-handoff-context
?? docs/19_modal_full_factorial_optimization_plan.md
```

Tracked dirty files before branch creation: none.

Untracked files before branch creation:

```text
docs/19_modal_full_factorial_optimization_plan.md
```

Intake branch:

```text
codex/modal-optimization-intake-review
```

Current edited surfaces:

- `docs/19_modal_full_factorial_optimization_plan.md`
- `audits/modal_optimization_intake_review_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Planning Doc Assessment

`docs/19_modal_full_factorial_optimization_plan.md` is classified as a Modal
planning doc.

Assessment:

- Status is `DRAFT_NOT_APPROVED`.
- `AUTHORIZES_EXECUTION: NO` is present.
- Modal, GPU, generation, experiment execution, output mutation, paper-scale,
  performance execution, profiler, billing query, credential use, and dependency
  change flags are all `NO`.
- The document separates estimator, sharding, fanout, autoscaling, larger-GPU
  microbenchmarking, batching, input concurrency, and vLLM into future packages.
- Cost/time estimation is treated as preflight planning, not execution.
- Larger GPUs are conditional on measured breakeven and a signed packet.
- JSONL rows, hash sidecars, observability sidecars, analyzer validation, and
  billing reconciliation remain the authoritative surfaces for future runs.
- Pricing and Modal API claims now require re-verification against official
  Modal documentation and pricing before any signed execution packet.

## Sidecar Timing Assessment

No new sidecar-only timing patch is present in the current dirty state.

Baseline code inspection found existing observability stage support in:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `shared/observability/schema.py`
- `shared/observability/logger.py`

The existing baseline event vocabulary includes the expected sidecar stage
names:

```text
generation
correctness_eval
p_repair
c_repair
row_append
```

Because the reported timing patch is not present as a diff, this intake does
not accept, modify, or commit new timing instrumentation.

## Scope Separation From Launcher/L1a

The launcher vertical is already promoted into `codex-track-handoff-context`
through:

- `e914557 Add dry-plan launcher support for 12-cell grammar mode matrix`
- `76ede6a Audit 12-cell launcher support promotion`

This Modal optimization intake branch is separate from launcher support and
separate from the L1a authorization packet. It does not sign L1a, complete an
execution packet, change launcher selection, change scientific rows, change
repair policy, change grammar semantics, or change pass/fail definitions.

## Execution Authorization Status

No execution is authorized by this intake.

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

No Modal command, GPU job, generation job, experiment run, benchmark, profiler,
billing query, output mutation, artifact creation, dependency change, lockfile
change, or MLflow runtime write was performed for this intake.

## Protected Path Scan

Protected paths for this intake:

```text
outputs
artifacts
mlruns
docs/preliminary_report
pyproject.toml
requirements.txt
requirements-dev.txt
uv.lock
poetry.lock
Pipfile.lock
```

Result:

- `git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock`: no output.
- `git ls-files --others --exclude-standard -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock`: no output.

Protected path scan passed.

## Validation Commands

Planned local validation:

```text
.venv/bin/python -m compileall -q cluster3/experiments/run_cluster3_modal.py
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -k "observability or timing or stage or grammar_mode or dry_plan" -q
.venv/bin/python -m pytest shared/tests -k "observability or tracking_noop" -q
git diff --check
git status --short --branch
```

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Authorization scan:

```text
positive execution-authorization flag scan over docs, audits, .contracts, cluster3, and shared, excluding generated preliminary-report files
```

Scientific-boundary scan:

```text
git diff -- cluster3 shared docs audits | rg -n "speedup|throughput|latency claim|benchmark result|retry|re-prompt|repair loop|torch.allclose|profiler|nsight|ncu|nvml"
```

Validation results:

```text
.venv/bin/python -m compileall -q cluster3/experiments/run_cluster3_modal.py
passed

.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -k "observability or timing or stage or grammar_mode or dry_plan" -q
39 passed, 94 deselected in 1.25s

.venv/bin/python -m pytest shared/tests -k "observability or tracking_noop" -q
370 passed, 736 deselected in 2.51s

git diff --check
passed

git status --short --branch
## codex/modal-optimization-intake-review
 M docs/handoff/agentic_document_hub.md
 M docs/handoff/document_version_registry.md
 M docs/handoff/experiment_change_orchestration_state.md
?? audits/modal_optimization_intake_review_report.md
?? docs/19_modal_full_factorial_optimization_plan.md
```

Authorization scan:

- matched only literal scan-command examples and the historical signed O6b
  smoke approval text in `audits/observability_sidecar_o6b_performance_smoke_report.md`;
- found no new affirmative execution authorization in the intake files.

Scientific-boundary scan:

- matched only negative authorization, protected-scope, or claim-boundary text in
  the docs diff;
- found no code changes, scientific row changes, retry or repair-loop semantic
  changes, benchmark result claims, profiler execution, or speedup claim.

## Commit Split Recommendation

Recommended commit split:

1. Commit the planning doc plus intake audit and handoff routing.
2. Do not create a sidecar timing instrumentation commit in this branch unless
   the reported timing patch is separately restored or supplied as a diff.

Do not combine this intake with L1a authorization, L1a execution packet work,
launcher changes, or Modal execution.

## Remaining Risks

- Modal API and pricing facts are time-sensitive and must be re-verified from
  official Modal sources before any signed execution or spend packet.
- The sidecar timing patch could not be reviewed because it is not present in
  the current worktree diff.
- Existing baseline observability stage durations are local-code reviewed here
  only as context; no new runtime evidence was collected.
- L1a remains unsigned, numeric stop/spend limits remain unsigned, and execution
  remains blocked.

## Classification

```text
MODAL_OPTIMIZATION_INTAKE_REVIEW_PASS_READY_TO_COMMIT
```

## Next-Step Recommendation

Review the intake diff and commit the planning/audit/handoff package if
validation is clean. If sidecar timing instrumentation is still desired, restore
or provide that patch on a separate implementation branch and review it as a
separate sidecar-only code change before any execution packet.
