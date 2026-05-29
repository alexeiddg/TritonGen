# Experiment Observability Plan

## Purpose

Track experiment observability across Cluster 1, Cluster 2, and Cluster 3 with
the lowest practical blast radius. The required signals are:

- experiment cost, when Modal can report it;
- estimated compute cost, when enough resource and timing data is available;
- kernel performance and speedup, only where the evaluation contract permits it;
- input, output, and generated token counts;
- wall clock duration for runs, stages, and attempts.

This is an instrumentation plan, not a methodology change. Existing experiment
rows should stay stable first; observability should initially land in sidecar
artifacts keyed to existing durable row identity.

## Research Summary

Researched on 2026-05-27.

Modal billing:

- Modal exposes billing reports through `modal.billing.workspace_billing_report`
  and `modal billing report`.
- Billing reports are post-hoc. The billing guide notes that usage can be
  delayed by minutes, so actual cost should be reconciled after a run rather
  than treated as a synchronous per-row value.
- Billing reports can include App tags. The current repo uses one shared Modal
  app, `tritongen-gpu-harness`, with no tags, so per-experiment cost attribution
  is not available without adding tags or enforcing non-overlapping run windows.
- Modal's granular billing report is pre-credit/pre-reservation cost. It is
  useful for attribution, but should not be assumed to equal the final invoice.
- Modal publishes per-second CPU, memory, and GPU rates. These can seed an
  estimated compute cost, but actual Modal billing should remain the source of
  truth when available.

Modal execution identity:

- `modal.current_function_call_id()` and `modal.current_input_id()` are
  available inside containers. The repo already wraps them in
  `shared/modal_harness/runtime.py`.
- Modal runtime environment variables include `MODAL_TASK_ID`, `MODAL_IMAGE_ID`,
  `MODAL_REGION`, `MODAL_CLOUD_PROVIDER`, `MODAL_ENVIRONMENT`, and
  `MODAL_IS_REMOTE`; these are low-risk runtime provenance fields.
- `modal.FunctionCall` supports spawned call objects and call graphs, but the
  current code mostly uses `.remote()`. Switching orchestration to `.spawn()`
  only for telemetry would be a larger behavior change and should not be first.

GPU and kernel metrics:

- Modal GPU metrics cover utilization, power, memory, and temperature. These
  are operational signals, not direct scientific kernel-performance evidence.
- No documented per-function-call GPU metrics API was found in the referenced
  Modal docs.
- Kernel timing should be measured inside the evaluator where allowed, using
  PyTorch CUDA Events or Triton benchmarking helpers.
- `shared/eval/schema.py` already has Level 4 performance fields such as
  `kernel_time_ms`, `eager_time_ms`, and speedup fields.

Sources:

- Modal billing guide: https://modal.com/docs/guide/billing
- Modal billing API: https://modal.com/docs/reference/modal.billing
- Modal billing CLI: https://modal.com/docs/reference/cli/billing
- Modal App tags: https://modal.com/docs/reference/modal.App
- Modal GPU metrics: https://modal.com/docs/guide/gpu-metrics
- Modal environment variables:
  https://modal.com/docs/guide/environment_variables
- Modal current function call ID:
  https://modal.com/docs/reference/modal.current_function_call_id
- Modal FunctionCall: https://modal.com/docs/reference/modal.FunctionCall
- Modal pricing: https://modal.com/pricing
- PyTorch CUDA Events:
  https://docs.pytorch.org/docs/2.12/generated/torch.cuda.Event.html
- Triton benchmarking helper:
  https://triton-lang.org/main/python-api/generated/triton.testing.do_bench.html

## Course Challenge Metric Coverage

The challenge document sets a smaller minimum than the full research goal. The
minimum evaluation requirements are:

- compare grammar-constrained generation against unconstrained generation;
- use the same prompt and same model, changing only the grammar constraint;
- run at least 50 generations with grammar and 50 generations without grammar;
- measure compile success rate;
- measure functional correctness rate;
- measure at least one additional metric of the team's choice;
- demonstrate that the grammar prevents syntactic errors.

The current eval ladder covers the first two required metrics if the analysis
reports them as aggregate rates:

```text
compile_success_rate = rows that pass Level 1 / total generated rows
functional_correctness_rate = rows that pass Level 2 / total generated rows
```

The missing base metric from the challenge language is a grammar/syntax metric:

```text
syntax_valid_rate or grammar_rejection_rate
```

This can be derived from Level 0/F0 outcomes and parser checks. It should be
reported separately from compile success because "the grammar prevents syntax
errors" is a required claim, not just an implementation detail.

Performance and speedup are not strictly required by the minimum rubric, but
they are the best third metric if the paper wants to claim efficient GPU kernel
generation rather than only valid/correct generation.

Existing pass@k status:

- `shared/eval/metrics/pass_at_k.py` implements HumanEval-style pass@k.
- `shared/tests/test_eval_pass_at_k.py` tests the formula, boundary values,
  and invalid inputs.
- `shared/stats/pass_at_k.py` provides pass@k tables for `(1, 5, 10)`.
- `cluster1/experiments/analyze_cluster1.py` and
  `cluster1/experiments/make_cluster1_figures.py` already report compile-only
  pass@k.
- `cluster1/tests/test_analysis.py` asserts Cluster 1 summary rows and markdown
  include `pass@1`, `pass@5`, and `pass@10`.
- `shared/eval/metrics/repair.py` implements `pass_at_1_initial` for repair
  analysis.
- `shared/tests/test_aggregation.py` tests `pass_at_1_initial` over initial
  attempt rows and terminal repair traces.

Targeted verification on 2026-05-27:

```text
.venv/bin/python -m pytest \
  shared/tests/test_eval_pass_at_k.py \
  shared/tests/test_aggregation.py \
  cluster1/tests/test_analysis.py -q

62 passed in 0.51s
```

Current limitation: pass@k is real and tested, but it is mostly compile-only
Cluster 1 reporting plus repair-oriented initial pass@1. It does not yet cover
correctness pass@k or benchmarkable/performance pass@k across Cluster 1,
Cluster 2, Cluster 3, and mixed G/C/P experiments.

The observability plan should therefore extend pass@k reporting rather than
invent it. Current compile-only Cluster 1 pass@k should become cross-cluster
reporting for:

```text
compile_pass@k
correctness_pass@k
benchmarkable_pass@k
```

For the final paper, the recommended headline metric set is:

```text
1. syntax_valid_rate
2. compile_success_rate
3. functional_correctness_rate
4. compile_pass@k
5. correctness_pass@k
6. median_kernel_time_ms
7. speedup_vs_eager
8. speedup_vs_baseline_unconstrained, when comparable correct kernels exist
```

Only compute timing and speedup on kernels that compile and are functionally
correct. Failed rows should stay in the denominators for compile/correctness
rates, but should be excluded from speedup distributions and counted in a
separate "not benchmarkable" bucket.

## Additional Metrics To Track

These metrics are not all required by the minimum course rubric, but they make
the final report more defensible and make mixed G/C/P experiments easier to
interpret.

### Pass@k

Use the existing shared pass@k implementation, but report separate success
definitions:

```text
compile_pass@1, compile_pass@5, compile_pass@10
correctness_pass@1, correctness_pass@5, correctness_pass@10
benchmarkable_pass@1, benchmarkable_pass@5, benchmarkable_pass@10
```

`benchmarkable_pass@k` means at least one sampled candidate compiles, passes
functional correctness, and reaches the performance benchmark stage.

### Cost per success

Raw cost is useful for budgets, but paper comparisons should normalize by
successful outcomes:

```text
cost_per_compiling_kernel
cost_per_correct_kernel
cost_per_benchmarkable_kernel
tokens_per_correct_kernel
wall_clock_per_correct_kernel
```

Compute these from observability summaries after actual or estimated cost is
available. Keep actual Modal cost and estimated compute cost separate.

### Repair efficiency

Needed for Cluster 2 C and Cluster 3 P:

```text
attempts_to_compile
attempts_to_correct
repair_success_rate
marginal_success_after_feedback
feedback_rounds_used
```

Report these by factor combination so P and C can be evaluated independently
and in combination.

### Failure distribution

Every row should end in one terminal bucket:

```text
F0_syntax_parse_signature_rate
F1_compile_rate
F1_runtime_rate
F2_correctness_rate
timeout_rate
oom_rate
illegal_memory_access_rate
not_benchmarkable_rate
```

This prevents aggregate rates from hiding why a condition failed.

### Performance robustness

Do not rely on a single timing number or shape:

```text
median_kernel_time_ms
kernel_time_iqr_ms
kernel_time_p20_ms
kernel_time_p80_ms
speedup_vs_eager
speedup_vs_unconstrained_correct_baseline
speedup_by_input_size
speedup_by_dtype
```

Only compare speedup across candidates that solve the same kernel task, input
shape family, dtype, hardware target, and correctness threshold.

### Fast@p and spurious-speedup audit

For performance-authorized experiment-wide reports, include KernelBench-style
threshold metrics:

```text
fast@0.0
fast@1.0
fast@1.2
fast_tc@1.0
fast_tc@1.2
```

`fast@p` is the fraction of eligible tasks that are functionally correct and
achieve `speedup_vs_eager >= p`. `fast_tc@p` uses `speedup_vs_compile` instead
of eager. `fast@0.0` is effectively Level 2 correctness under the performance
reporting denominator.

Every performance report should also include:

```text
spurious_speedup_rate
```

Expected value is `0.0`. A nonzero value means speedup was measured or retained
for a functionally incorrect kernel, and the performance table should be
treated as invalid until the gate is fixed.

### Best-candidate quality

Generation experiments often care about whether at least one high-quality
candidate appears:

```text
best_speedup_per_task
best_kernel_time_per_task
best_correct_candidate_rank
```

These should be secondary metrics, because best-of-run summaries are sensitive
to sample count.

### Reproducibility metadata

Record these as metadata, not headline metrics:

```text
model_id
prompt_id
prompt_hash
grammar_version
grammar_hash
decoding_temperature
seed
git_sha
modal_image_id
gpu_type
cuda_version
triton_version
torch_version
```

Without these fields, cost, timing, and pass-rate comparisons are hard to audit.

### Statistical evidence

Headline rates should include uncertainty and effect-size summaries, not only
point estimates:

```text
wilson_ci_95_for_rates
bootstrap_ci_95_for_speedup
absolute_lift_vs_baseline
relative_lift_vs_baseline
odds_ratio_or_risk_ratio_for_success
factor_main_effects
factor_interaction_effects
```

Use these for final report tables comparing grammar-on vs grammar-off and
mixed G/C/P factor combinations.

### Constrained-decoding overhead

The grammar can improve validity while slowing generation. Track the overhead
explicitly:

```text
decode_wall_clock_s
tokens_per_second
constraint_overhead_s
constraint_overhead_ratio
grammar_mask_failures
grammar_backtracks_or_rejections
```

If the tokenizer/runtime cannot expose mask/rejection internals, record
`not_available` rather than guessing.

### Diversity and duplication

Pass rates can be inflated by many near-duplicate candidates. Keep diversity as
a secondary diagnostic:

```text
unique_solution_rate
duplicate_candidate_rate
unique_correct_solution_rate
ast_or_source_hash_diversity
```

Cluster 1 already has `unique_solution_rate`; the observability layer should
make equivalent diversity summaries available for mixed experiments when
hashes exist.

### End-to-end yield

For whole-pipeline claims, report the final usable-yield funnel:

```text
generated_count
syntax_valid_count
compile_success_count
correctness_success_count
benchmarkable_count
speedup_positive_count
```

This is the clearest way to show where candidates are lost.

### Fairness and budget parity

When comparing grammar-on and grammar-off, record whether the comparison is
sample-matched, token-budget-matched, wall-clock-budget-matched, or
cost-budget-matched:

```text
comparison_budget_mode
samples_per_condition
tokens_per_condition
wall_clock_s_per_condition
estimated_cost_usd_per_condition
```

The final report should avoid mixing a 50-sample grammar run with a much larger
unconstrained search unless the difference is explicitly labeled.

## Metric Scope Map

Use this scope map when adding analysis outputs. "Cluster-isolated" means the
metric can be computed inside one cluster's owned contract. "Experiment-wide"
means it needs joined terminal rows or sidecars across the full G/C/P pipeline.

```text
Metric family                         Scope
syntax_valid_rate                     Cluster 1 and experiment-wide
grammar_rejection_rate                Cluster 1 and experiment-wide
compile_success_rate                  Cluster 1, Cluster 3 repair, experiment-wide
functional_correctness_rate           Cluster 2 and experiment-wide
compile_pass@k                        Cluster 1 and experiment-wide
correctness_pass@k                    Cluster 2 and experiment-wide
benchmarkable_pass@k                  Experiment-wide only
median_kernel_time_ms                 Experiment-wide Level 4 only
speedup_vs_eager                      Experiment-wide Level 4 only
speedup_vs_unconstrained_baseline     Experiment-wide Level 4 only
fast@p and fast_tc@p                  Experiment-wide Level 4 only
spurious_speedup_rate                 Experiment-wide Level 4 audit
cost_per_success                      Experiment-wide only
tokens_per_success                    Experiment-wide, with cluster-stage breakdown
wall_clock_per_success                Experiment-wide, with cluster-stage breakdown
attempts_to_compile                   Cluster 3 P and experiment-wide
attempts_to_correct                   Cluster 2 C and experiment-wide
repair_success_rate                   Cluster 2, Cluster 3, and experiment-wide
marginal_success_after_feedback       Cluster 2, Cluster 3, and experiment-wide
terminal_failure_distribution         Cluster-isolated and experiment-wide
constrained_decoding_overhead         Cluster 1 generation and experiment-wide
diversity_or_duplicate_rate           Cluster-isolated and experiment-wide
end_to_end_yield_funnel               Experiment-wide only
statistical_ci_and_lift               Experiment-wide, plus cluster-isolated diagnostics
reproducibility_metadata              Cluster-isolated and experiment-wide
```

Cluster-specific guardrails:

- Cluster 1 may report syntax, compile, generation, pass@k, diversity, token,
  and wall-clock metrics. Its pass@k must be labeled `compile_pass@k` or carry
  `metric_gate=compile_success`. It must not claim functional correctness,
  benchmark performance, or speedup.
- Cluster 2 may report correctness, C repair, F2 failure, token, cost, and
  wall-clock metrics for its owned rows. It should not place timing/speedup
  fields into Cluster 2 scientific result rows unless the contract changes.
- Cluster 3 v1 may report P compile-repair efficiency, attempts-to-compile,
  token, cost, and wall-clock metrics. It should not claim F2 repair or Level 4
  performance unless a later contract expands it.
- Experiment-wide reports may join all sidecars and terminal rows, and are the
  right place for cost-per-success, benchmarkable yield, speedup, factor
  effects, and G/C/P interaction analysis.

## Metric Compatibility Guardrails

The audit concern is valid: the codebase currently has metrics with similar
names but different gates and denominators. Some of that is intentional, but
future reports must make those differences explicit.

### 1. Reserve unqualified pass@k for Level 2 correctness

New experiment-wide outputs should not use bare `pass@k` unless:

```text
metric_gate = functional_success
level_gate = Level 2
denominator_unit = sample or task, explicitly declared
```

Cluster 1's existing `pass@1`, `pass@5`, and `pass@10` are tested and real, but
they are compile-gated. New reports should label them as:

```text
compile_pass@1
compile_pass@5
compile_pass@10
metric_gate = compile_success
compile_success_scope = all_dtype_strict
```

Correctness reports should use:

```text
correctness_pass@1
correctness_pass@5
correctness_pass@10
metric_gate = functional_success
```

Performance reports should use:

```text
benchmarkable_pass@1
benchmarkable_pass@5
benchmarkable_pass@10
metric_gate = functional_success AND benchmark_stage_reached
```

### 2. Add a shared metric registry

Every reported metric should have a registry entry with:

```text
metric_name
display_name
metric_gate
level_gate
denominator_unit
attempt_policy
aggregation_policy
cluster_owner
scope
source_schema
source_row_class
compile_success_scope
reportability
comparability_group
```

Recommended enum values:

```text
metric_gate:
  syntax_valid
  compile_success
  functional_success
  benchmarkable
  speedup_threshold

denominator_unit:
  row_sample
  task_cell
  repair_attempt
  terminal_candidate
  paired_replay_cell

attempt_policy:
  initial_only
  terminal_only
  within_n
  best_of_k
  all_attempts

compile_success_scope:
  all_dtype_strict
  prompt_dtype
  terminal_dtype
  not_applicable

reportability:
  paper_primary
  paper_secondary
  diagnostic_only
  smoke_only
  not_reportable
```

### 3. Reject incompatible aggregations

Analyzer code should reject or clearly quarantine any aggregation where rows
mix incompatible:

```text
metric_gate
denominator_unit
attempt_policy
compile_success_scope
source_row_class
```

Examples that must not be compared as the same metric:

- Cluster 1 compile-gated `pass@5` vs Cluster 2 Level 2 correctness pass@5.
- Cluster 1 sample-level pass@k vs Cluster 2 cell-level convergence within 5
  repair attempts.
- Strict all-dtype compile success vs terminal prompt-dtype compile status.
- Raw Cluster 1 compile-only rows vs replay-evaluated Cluster 2 controls for
  primary functional-success analysis.

### 4. Use replay-evaluated controls for primary functional comparisons

Raw Cluster 1 rows are valid for syntax, compile, diversity, generation, and
compile-pass diagnostics. They are not valid primary Level 2 functional rows
because Level 2 was not run.

Primary C/G/P functional comparisons should use rows that actually passed
through the correctness evaluator, including replay-evaluated frozen Cluster 1
controls. If a raw Cluster 1 row appears in an experiment-wide functional table,
it must be marked:

```text
functional_success_status = not_evaluated
reportability = diagnostic_only
```

### 5. Add compatibility tests before paper-scale runs

Planned tests:

- reject unqualified `pass@k` unless `metric_gate=functional_success`;
- reject aggregation across mixed denominator units;
- reject aggregation across mixed attempt policies;
- reject primary functional analysis from raw Cluster 1 compile-only rows;
- require `compile_success_scope` before compile metrics can be compared;
- require `spurious_speedup_rate == 0.0` for any performance report.

## Local Verification

Modal package availability:

```text
modal_version 1.4.2
has_billing True
has_current_function_call_id True
has_current_input_id True
```

Existing dependency floor:

```text
pyproject.toml: modal>=1.0
requirements.txt: modal>=1.0
```

Schema regression smoke test:

```text
.venv/bin/python -m pytest \
  shared/tests/test_modal_harness_schemas.py \
  cluster2/tests/test_modal_schemas.py \
  cluster3/tests/test_cluster3_schema.py -q

227 passed in 0.32s
```

Current relevant worktree state before this doc was added:

```text
 M shared/analysis/factorial.py
?? shared/tests/test_analyzer_cluster3.py
```

Those files appear to be active Phase 7a work and were not modified for this
observability plan.

## Eval-Ladder Clarification

The shorthand "Cluster 1 evals to F0, Cluster 2 to F2, Cluster 3 to F1" is not
quite correct.

- Cluster 1 owns generation and compile-only viability. It can terminally
  observe `F0_*` parse/signature/grammar failures and `F1_*` compile/runtime
  failures. It should not perform numerical correctness, profiling, speedup, or
  repair.
- Cluster 2 owns correctness repair for the C factor. It evaluates through Level
  2 correctness for C and G+C rows, but can still produce terminal F0/F1 rows
  before reaching numerical comparison.
- Cluster 3 v1 owns P, the compile-error feedback loop. It targets
  `F1_COMPILE` repair only. It should not repair F0, F1 runtime, F2 numeric, or
  performance failures unless a later contract expands P.

So a better mapping is:

```text
Cluster 1: G / no-G generation plus Level 0 and Level 1 viability
Cluster 2: C correctness repair plus Level 2 correctness
Cluster 3: P compile-error repair for F1_COMPILE
```

## Interchangeability After Phase 7a

The clusters should become composable by experiment factor, not
interchangeable as full runners.

Desired factor switches:

```text
G: Frontier-conditioned generation, owned by Cluster 1.
C: Correctness feedback loop, owned by Cluster 2.
P: Compile-error feedback loop, owned by Cluster 3.
```

Valid post-Phase-7a combinations should be expressible as rows in a factorial
or ablation plan:

```text
none
G
C
P
G+C
G+P
C+P
G+C+P
```

The orchestrator should sequence cluster-owned components, rather than making
each cluster runner accept every factor. For example:

```text
G+C+P:
  1. generate with the G state selected by the row;
  2. classify initial compile/correctness outcome;
  3. dispatch P only for F1_COMPILE;
  4. dispatch C only for F2 numerical failures;
  5. emit one terminal row plus observability sidecars.
```

Analyzer support can compare:

- P vs none;
- G+P vs G;
- C+P vs C;
- G+C+P vs G+C.

However, the control rows come from different existing owners. None/G controls
come from Cluster 1 replay controls, while C/G+C rows come from Cluster 2
generated rows. That should remain explicit in metadata.

## Lowest-Blast-Radius Integration

### 1. Add sidecar telemetry first

Create a shared package:

```text
shared/observability/
  __init__.py
  schema.py
  logger.py
  pricing.py
  modal_billing.py
```

Write sidecars next to each experiment output:

```text
<output>.observability.jsonl
<output>.observability.summary.json
```

This avoids immediate changes to:

- `GenerationResult`;
- `Cluster2EvalRow`;
- `Cluster3EvalRow`;
- existing hash sidecars;
- current analyzer outputs;
- active Phase 7a analyzer files.

### 2. Key telemetry to existing row identity

Minimum identity fields:

```text
schema_version
experiment_id
run_id
cluster
condition
kernel_class
kernel_name
dtype
base_seed or sample_index
attempt_index
stage
source_hash, when available
result_output_path
result_row_index, when available
```

Do not include source text, private eval payloads, raw feedback, or full
tracebacks in telemetry.

### 3. Instrument wall clock at local orchestration boundaries

Use `time.perf_counter()` around existing local call sites first:

- Cluster 1: generation calls, compile checks, per-cell execution, and full
  runner duration.
- Cluster 2: generated-condition generation, generated-condition evaluation,
  replay-control correctness calls, repair-loop attempts, and full runner
  duration.
- Cluster 3: generation, correctness, dispatcher, P loop, optional C loop, and
  full runner duration.

This provides immediate wall-clock coverage without changing Modal schemas.

### 4. Add Modal runtime identity with small remote schema changes

Extend the shared Modal runtime helper to return:

```text
function_call_id
input_id
task_id
image_id
region
cloud_provider
environment
is_remote
```

Then include an optional `modal_context` object in remote responses. Make it
optional and default to `None` so older fixtures and tests continue to pass.

### 5. Surface token counts deliberately

Current state:

- Cluster 1 already computes generated token count internally in decoded
  kernels.
- Cluster 2 has `C2DecodedKernel.generated_token_count`.
- Existing public result schemas do not durably expose input, output, or
  generated tokens across all clusters.

Recommended fields:

```text
tokens_prompt
tokens_generated
tokens_total
tokenizer_name
token_count_source
```

For wire responses, place these under `generation_telemetry`, not directly in
scientific result rows. Later, analyzers can join sidecars when token-cost or
latency analysis is needed.

### 6. Split actual cost from estimated compute cost

Actual experiment cost:

- Reconcile post-hoc through Modal billing reports.
- Prefer per-experiment Modal App tags once a clean tagging strategy exists.
- Until tags exist, only reconcile actual cost for isolated time windows and
  mark attribution confidence explicitly.

Estimated compute cost:

- Compute from stage wall clock, GPU type, GPU count, CPU count, memory, and a
  pinned pricing snapshot.
- Store the pricing source URL, retrieval date, currency, and formula version.
- Treat it as an estimate, not a billing claim.

### 7. Keep performance and speedup gated

Cluster 1 and Cluster 2 currently forbid or intentionally avoid performance
claims. Therefore:

- record wall clock everywhere;
- record generation/evaluation attempt duration everywhere;
- record `kernel_time_ms`, `eager_time_ms`, and speedup only in evaluators whose
  contract reaches Level 4 performance evaluation;
- store `null` plus a `metric_status` reason when performance is not evaluated.

Recommended statuses:

```text
measured
not_applicable
not_permitted_by_contract
failed_before_level
not_available
estimated
post_hoc_pending
```

## Rollout Plan

### Phase A: Contract and sidecar schema

- Add `shared/observability/schema.py` with Pydantic models for telemetry events
  and run summaries.
- Add `shared/observability/logger.py` for JSONL append and summary write.
- Add tests for schema compatibility, missing optional fields, and JSONL
  round-trip.
- Do not change scientific row schemas in this phase.

### Phase B: Wall clock and Modal identity

- Wrap local orchestration boundaries with a telemetry context manager.
- Add optional Modal runtime context to remote responses.
- Verify existing schema tests still pass.
- Add focused tests for one Cluster 1, one Cluster 2, and one Cluster 3
  telemetry event path.

### Phase C: Token telemetry

- Add generation telemetry objects to Cluster 1 and Cluster 2 remote responses.
- Preserve existing row payloads.
- Record prompt/generated/total tokens in the sidecar.
- Add a tokenizer-source field so later model changes are auditable.

### Phase D: Estimated compute cost

- Add a pinned pricing snapshot file, for example
  `shared/observability/modal_pricing_2026_05_27.json`.
- Add `estimated_compute_cost_usd` to summaries.
- Mark estimates with formula version and pricing source.

### Phase E: Post-hoc Modal billing reconciliation

- Add a small CLI or script that calls Modal billing reports for a run window.
- Join billing rows to experiment summaries by app name, tag when available,
  and time interval.
- Store attribution confidence:

```text
exact_tagged
isolated_window
shared_window_ambiguous
unavailable
```

### Phase F: Performance timing contract

- Only after the paper plan authorizes Level 4 performance evaluation, add
  benchmark events to the evaluator.
- Prefer `triton.testing.do_bench` or CUDA Events consistently.
- Store warmup count, repetitions, median/IQR/p20/p80, eager baseline, compile
  timing, and timing device.

## Trust Readiness Gate

Do not treat the pipeline as paper-trustworthy until implementation proves all
of the following:

- every paper-facing metric has `metric_gate`, `denominator_unit`,
  `attempt_policy`, `scope`, and `reportability`;
- unqualified `pass@k` is reserved for Level 2 `functional_success`;
- Cluster 1 compile-only metrics are renamed to `compile_pass@k` or tagged with
  `metric_gate=compile_success`;
- raw Cluster 1 rows are blocked from primary functional comparisons unless
  they have been replay-evaluated through the correctness evaluator;
- speedup is computed only after Level 2 correctness passes;
- every performance report has `spurious_speedup_rate == 0.0`;
- analyzers reject or quarantine incompatible aggregations;
- tests cover mixed-cluster failure cases, including mismatched gates,
  denominator units, attempt policies, compile scopes, and source row classes;
- a smoke run produces expected observability sidecars and summaries;
- a paper-scale run produces expected observability sidecars, summaries, metric
  registry entries, and compatibility-check outputs.

## Acceptance Criteria

- Final experiment reports include at least 50 constrained and 50 unconstrained
  generations per claimed comparison, or explicitly mark smaller runs as smoke
  tests.
- Reports aggregate `syntax_valid_rate`, `compile_success_rate`, and
  `functional_correctness_rate` for constrained and unconstrained conditions.
- Every reported metric is labeled as cluster-isolated, experiment-wide, or
  both according to the Metric Scope Map.
- Reports include compile, correctness, and benchmarkable pass@k using the
  existing shared pass@k implementation.
- New experiment-wide reports do not use unqualified `pass@k` unless the metric
  gate is Level 2 `functional_success`.
- Every paper-facing metric has a registry entry declaring gate, denominator
  unit, attempt policy, owner, scope, source row class, and reportability.
- Aggregators reject or quarantine rows with mixed metric gates, denominator
  units, attempt policies, compile-success scopes, or source row classes.
- Primary functional comparisons use replay-evaluated controls, not raw Cluster
  1 compile-only rows.
- Reports include uncertainty and lift/effect-size summaries for headline
  comparisons.
- Reports include cost-per-success and wall-clock-per-success summaries when
  cost or wall-clock telemetry is available.
- Reports include constrained-decoding overhead when token/runtime internals
  are available, or an explicit `not_available` status otherwise.
- Reports include diversity or duplication diagnostics when source or AST hashes
  are available.
- Reports include an end-to-end yield funnel from generated candidates to
  benchmarkable and speedup-positive candidates.
- Comparisons state whether they are sample-matched, token-budget-matched,
  wall-clock-budget-matched, or cost-budget-matched.
- Repair-loop reports include attempts-to-success, repair success rate,
  marginal success after feedback, and feedback rounds used.
- Reports include a terminal failure distribution across F0/F1/F2, timeout,
  OOM, illegal memory access, and not-benchmarkable buckets.
- Performance tables include only compile-passing and correctness-passing
  kernels, with a separate count for rows that were not benchmarkable.
- Performance summaries include median, IQR, p20, and p80 timing where Level 4
  timing is authorized.
- Performance reports include `fast@p`, `fast_tc@p`, and
  `spurious_speedup_rate`, with `spurious_speedup_rate` required to be `0.0`.
- Experiment artifacts record model, prompt, grammar, seed, git, Modal image,
  GPU, CUDA, Triton, and Torch provenance where available.
- Every cluster run emits an observability summary with run start, run end,
  total wall clock, artifact paths, and metric availability statuses.
- Every remote stage can optionally report Modal function/input identity.
- Token counts are present for generated model outputs where tokenization is
  available.
- Actual Modal cost is either reconciled post-hoc or marked unavailable with a
  reason.
- Estimated compute cost is clearly separated from actual billing cost.
- Kernel performance and speedup remain absent or `not_permitted_by_contract`
  outside authorized performance evaluation.
- Existing Cluster 1, Cluster 2, Cluster 3, and Phase 7a analyzer tests do not
  require scientific row rewrites.

## Open Decisions

- Should Modal App tags be static per experiment run, or should the project
  create separate app objects for major experiment families?
- What is the canonical `experiment_id` format for mixed-factor runs?
- Should sidecars be required for all future runs, or optional behind a CLI
  flag during rollout?
- Which artifact registry should own billing reconciliation outputs?
- When performance evaluation is authorized, should Level 4 live in Cluster 3
  or in a new shared evaluator invoked after cluster-specific repair completes?
