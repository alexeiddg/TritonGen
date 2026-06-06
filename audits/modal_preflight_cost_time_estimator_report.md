# Modal Preflight Cost/Time Estimator Report

created_at: 2026-06-05
branch: `codex/modal-preflight-cost-time-estimator`
baseline_commit: `76310b5 Audit sidecar stage timing promotion`
classification: `MODAL_PREFLIGHT_COST_TIME_ESTIMATOR_COMPLETE`
AUTHORIZES_EXECUTION: NO

## Executive Summary

This package adds a local-only advisory estimator for future Modal planning
before any L1a/L1b/L2 execution packet. The estimator is pure Python under
`cluster3/planning/modal_preflight_estimator.py` and uses explicit local inputs
for cell count, `n`, GPU label, pricing, cold start, model load, per-row stage
timing, repair activation, fanout, safety multiplier, and optional fixed
overhead.

It does not import Modal, call billing APIs, query pricing, use the network,
run generation, run experiments, write outputs, write artifacts, write
`mlruns/`, refresh reports, change dependencies, or change scientific rows.

## Files Changed

- `cluster3/planning/modal_preflight_estimator.py`
- `cluster3/planning/__init__.py`
- `cluster3/tests/test_modal_preflight_estimator.py`
- `docs/19_modal_full_factorial_optimization_plan.md`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`
- `audits/modal_preflight_cost_time_estimator_report.md`

## Estimator Inputs/Outputs

Inputs:

- `cell_count`
- `n_per_cell`
- `gpu_label`
- `price_per_gpu_second` or `price_per_gpu_hour`
- `cold_start_seconds`
- `model_load_seconds`
- `generation_seconds_per_row`
- `compile_correctness_seconds_per_row`
- `repair_overhead_seconds_per_activated_repair`
- `expected_p_activation_rate`
- `expected_c_activation_rate`
- `fanout_limit`
- `safety_multiplier`
- `fixed_overhead_seconds`
- `pricing_source`
- `pricing_verified`
- `stage_timing_source`
- optional baseline-GPU breakeven inputs

Outputs:

- total planned rows and rows per cell;
- serial and fanout-bounded wall-clock estimates;
- estimated GPU seconds and estimated cost;
- cold-start, model-load, fixed-overhead, generation, correctness-eval, and
  repair shares;
- execution-shape comparison records;
- optional baseline GPU breakeven record;
- warning flags for advisory-only status, stale/unverified pricing, estimated
  timing inputs, and unmeasured larger-GPU speedup.

All estimator outputs are JSON-safe through `to_dict()`.

## Execution-Shape Comparisons

The estimator compares:

- `one_remote_invocation_per_row`
- `one_remote_invocation_per_cell`
- `one_remote_invocation_per_grammar_mode_shard`
- `single_full_plan_invocation`
- `bounded_fanout_across_cells_seeds`

The comparisons are planning-only. They do not change launcher behavior or
submit work.

## GPU Breakeven Policy

The larger-GPU helper computes:

```text
breakeven_speedup = candidate_price_per_gpu_second / baseline_price_per_gpu_second
minimum_justification_speedup = breakeven_speedup + safety_margin
```

A more expensive GPU is not marked cost-justified unless a caller supplies a
measured speedup that clears the price ratio plus safety margin. The estimator
does not claim that L40S, H100, or any other larger GPU is better without
measurement.

## Validation/Fail-Closed Behavior

The estimator rejects:

- negative times;
- zero or negative prices;
- `fanout_limit < 1`;
- `n_per_cell < 1`;
- `cell_count < 1`;
- empty GPU labels;
- invalid activation rates outside `[0, 1]`;
- safety multipliers below `1`;
- non-finite numeric inputs;
- unknown stage-timing source labels;
- partial baseline-GPU comparison inputs;
- measured speedup or positive breakeven safety margin without baseline-GPU
  comparison inputs.

It warns when pricing is unverified and when timing inputs are estimated rather
than measured.

## Source-Of-Truth Boundary

Estimator output is advisory only. It is not experimental evidence, not billing
evidence, and not a substitute for signed packet limits.

The authoritative records remain:

- experiment JSONL rows;
- content-hash sidecars;
- observability sidecars;
- analyzer outputs;
- post-run billing reconciliation when separately approved.

## Tests Run

Commands run locally with `.venv/bin/python`:

```text
.venv/bin/python -m pytest cluster3/tests/test_modal_preflight_estimator.py -q
```

Result: `31 passed in 0.04s`.

```text
.venv/bin/python -m pytest cluster3/tests -k "preflight or estimator or cost or fanout or breakeven" -q
```

Result: `36 passed, 829 deselected in 0.57s`.

```text
.venv/bin/python -m pytest shared/tests -k "preflight or estimator or cost or fanout or breakeven" -q
```

Result: `42 passed, 1064 deselected in 0.53s`.

```text
.venv/bin/python -m compileall -q cluster3/planning cluster3/tests/test_modal_preflight_estimator.py
.venv/bin/python -m compileall -q cluster3 shared
git diff --check
```

Result: passed with no output.

## No-Execution Proof

No Modal, GPU, generation, experiment, benchmark, profiler, billing API,
network, output refresh, report refresh, dependency, lockfile, or MLflow runtime
command was run.

The Modal/network/billing import scan over the full diff only matched negative
authorization wording in docs. The code path itself imports only Python
standard-library modules and has an explicit unit test proving the estimator
source contains no Modal package import statement or billing module reference.

Authorization scan:

Result: no affirmative authorization records.

## No-Output/MLflow Mutation Proof

Protected mutation scan:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Result: empty.

No `outputs/`, `artifacts/`, `mlruns/`, preliminary-report preview, dependency,
or lockfile path changed.

## Remaining Risks

- Pricing values remain user-supplied and must be re-verified before signed
  spend approval.
- The estimator cannot prove real queue delay, container reuse, or GPU speedup
  without later approved timing evidence.
- The current branch does not implement sharded execution or change Modal
  launcher behavior.
- Future packets must attach exact estimator inputs and outputs for the target
  scope; this audit does not authorize any execution packet.

## Classification

`MODAL_PREFLIGHT_COST_TIME_ESTIMATOR_COMPLETE`

The package satisfies the local-only estimator requirements and preserves the
no-execution boundary.

## Next-Step Recommendation

Review and commit this branch. After promotion into `codex-track-handoff-context`,
the next safe step is to use the estimator output as a required attachment for a
future signed L1a packet. Do not draft or run an execution packet until the
signed packet includes exact commands, target commit, paths, numeric stop/spend
limits, and the advisory preflight estimate.
