# Modal Preflight Cost/Time Estimator Promotion Audit Report

- Version: 1.0.0
- Date: 2026-06-05
- Source branch: `codex/modal-preflight-cost-time-estimator`
- Target branch: `codex-track-handoff-context`
- Promoted commit: `bd89e67 Add local Modal preflight cost time estimator`
- Promotion method: fast-forward
- Status: `MODAL_PREFLIGHT_COST_TIME_ESTIMATOR_PROMOTION_COMPLETE`
- Citation status: evidence snapshot; do not cite as methodology, billing, cost, runtime, or performance evidence

## Executive Summary

The local Modal preflight cost/time estimator was fast-forward promoted from
`codex/modal-preflight-cost-time-estimator` into
`codex-track-handoff-context`.

The promoted package is local-only and advisory. It estimates planned row
counts, cost/time envelopes, execution-shape comparisons, and optional
larger-GPU breakeven requirements from explicit caller-supplied inputs before
any later signed L1a/L1b/L2 execution packet.

No Modal execution, GPU work, generation, experiment run, billing query,
benchmark, profiler, output mutation, artifact mutation, `mlruns/` mutation,
dependency change, lockfile change, report refresh, or MLflow runtime write was
authorized or performed by this promotion.

## Source Branch

```text
source_branch: codex/modal-preflight-cost-time-estimator
source_commit: bd89e67 Add local Modal preflight cost time estimator
source_head_before_promotion: bd89e67
```

The source branch was confirmed clean before promotion:

```text
## codex/modal-preflight-cost-time-estimator
```

The source branch history contained `bd89e67` at HEAD. The promotion diff from
`codex-track-handoff-context` contained only the estimator, focused tests,
non-authorizing planning/audit docs, and handoff-routing updates committed in
the reviewed estimator package.

## Target Branch

```text
target_branch: codex-track-handoff-context
target_branch_before_promotion: 76310b5 Audit sidecar stage timing promotion
target_branch_after_promotion: bd89e67 Add local Modal preflight cost time estimator
promotion_method: git merge --ff-only codex/modal-preflight-cost-time-estimator
```

`codex-track-handoff-context` was confirmed to be an ancestor of the source
branch before promotion. The target branch was clean before checkout and
fast-forwarded only. No non-fast-forward merge commit was created.

## Promoted Commit

`bd89e67` promotes:

- `cluster3/planning/modal_preflight_estimator.py`;
- `cluster3/planning/__init__.py` exports for the estimator API;
- `cluster3/tests/test_modal_preflight_estimator.py`;
- `audits/modal_preflight_cost_time_estimator_report.md`;
- non-authorizing updates to the Modal optimization plan;
- non-authorizing L1a packet wording requiring a future advisory estimate
  before signature;
- handoff document routing for the estimator package.

## Estimator Summary

The estimator computes local planning estimates for:

- selected design cardinality and row counts;
- serial wall-clock envelope;
- bounded fanout wall-clock envelope;
- GPU-second and advisory cost envelope;
- optional fixed overhead and safety multiplier;
- warning flags for advisory-only output and stale or unverified pricing;
- optional larger-GPU breakeven comparison.

The estimator does not create or inspect runtime outputs. It is a preflight
planning utility, not an experiment runner and not an analyzer.

## Estimator Purity

The promoted estimator is pure local Python. It imports only standard-library
modules and does not import Modal, network clients, billing APIs, subprocess
Modal commands, MLflow runtime clients, result writers, artifact writers, or
report builders.

Focused source tests assert that `modal_preflight_estimator.py` does not contain
`import modal`, `from modal`, or `modal.billing`.

## Input Validation

The estimator fails closed for malformed or incomplete planning inputs. It
rejects:

- non-positive cell counts, sample counts, generation seconds, GPU price,
  repair-attempt limits, fanout limits, and candidate GPU prices;
- negative correctness, P repair, C repair, overhead, and measured speedup
  inputs;
- safety multipliers below `1`;
- unknown stage-timing source values;
- partial baseline GPU comparison fields;
- measured speedup or positive breakeven safety margin without complete
  baseline GPU comparison inputs.

## Output Summary

Estimator outputs are JSON-safe through `to_dict()` and are advisory-only. The
output summary includes row counts, per-row timing assumptions, execution-shape
records, total GPU-second estimates, advisory cost estimates, warning flags,
and optional GPU breakeven details.

No output field is a measured cost, measured runtime, performance result, or
paper-scale evidence claim.

## Execution-Shape Comparison

The promoted estimator compares:

- `serial_single_container`;
- `one_invocation_per_cell`;
- `bounded_fanout_across_cells_seeds`.

The comparison is arithmetic planning only. It does not invoke Modal, create
containers, query queue behavior, measure cold starts, or prove actual wall
time.

## GPU Breakeven Policy

The larger-GPU policy is explicitly advisory. A candidate GPU is treated as
unjustified unless caller-supplied measured speedup clears:

```text
minimum_justification_speedup = candidate_price_per_gpu_second / baseline_price_per_gpu_second + breakeven_safety_margin
```

The estimator does not measure speedup and does not authorize a larger GPU.
Future larger-GPU use still requires a separate signed packet with re-verified
pricing, numeric spend limits, and a scoped microbenchmark or execution
approval.

## Source-of-Truth Boundary

JSONL result rows, observability sidecars, analyzer outputs, and later
sanitized billing reconciliation remain the authoritative evidence surfaces for
real runs. The estimator is a planning input for future authorization packets
and cannot replace run evidence, billing evidence, analyzer evidence, or
scientific row data.

## L1a Authorization Status

L1a remains unsigned and non-executing. The promoted L1a wording requires an
advisory preflight estimate before any future signature, but it does not sign
the packet and does not authorize Modal, GPU, generation, output, artifact,
`mlruns/`, MLflow runtime, n=1, n=5, n=20, paper-scale, benchmark, profiler, or
billing-query work.

## Tests Run

```text
.venv/bin/python -m pytest cluster3/tests/test_modal_preflight_estimator.py -q
31 passed in 0.04s

.venv/bin/python -m pytest cluster3/tests -k "preflight or estimator or cost or fanout or breakeven" -q
36 passed, 829 deselected in 0.55s

.venv/bin/python -m pytest shared/tests -k "preflight or estimator or cost or fanout or breakeven" -q
42 passed, 1064 deselected in 0.52s

.venv/bin/python -m compileall -q cluster3 shared
passed

git diff --check
passed
```

## No-Execution Proof

No Modal, GPU, generation, experiment, benchmark, profiler, billing query,
MLflow tracking execution, n=1 execution, n=5 execution, n=20 execution, or
paper-scale command was run during this promotion.

The Modal/network/billing scan over the promotion diff reported only negative
test assertions and non-authorizing documentation references. The added-line
authorization scan was empty for affirmative execution flags. The broader
authorization scan reported only pre-existing historical O6b approval text and
literal scan-command examples.

## No-Output Or MLRuns Mutation Proof

The protected mutation scan over the promotion diff was empty for:

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

The promotion did not refresh reports, create run artifacts, write result rows,
write observability sidecars, write MLflow state, add dependencies, or change
lockfiles.

## Classification

`MODAL_PREFLIGHT_COST_TIME_ESTIMATOR_PROMOTION_COMPLETE`

`bd89e67` was fast-forward promoted into `codex-track-handoff-context`; the
estimator remains pure/local/advisory; no execution authorization was
introduced; no measured cost/runtime/performance result was claimed; and no
outputs, artifacts, `mlruns/`, dependencies, or lockfiles were changed.

## Next-Step Recommendation

Do not create or run an execution packet yet. The next safe step is to use the
promoted estimator as a required advisory attachment when completing a future
signed L1a approval packet with exact commands, output paths, sidecar paths,
numeric stop limits, spend limits, and explicit user authorization.
