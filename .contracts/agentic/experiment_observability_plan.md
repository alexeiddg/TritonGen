# Experiment Observability Plan

## Purpose

Add experiment-level observability for Cluster 1, Cluster 2, and Cluster 3 with
the lowest practical blast radius. The required signals are:

- experiment cost, when Modal can report it;
- estimated compute cost, when enough resource and timing data is available;
- kernel performance and speedup, only where the evaluation contract allows it;
- input/output/generated token counts;
- wall clock duration for runs, stages, and attempts.

This plan is instrumentation-first. It does not authorize new paper-scale runs,
does not reinterpret existing artifacts, and does not make performance claims
for Cluster 1 or Cluster 2. Existing result rows stay methodologically clean;
new observability data should first land in sidecars keyed to durable row
identity.

Companion implementation plan:

- `.contracts/agentic/mlflow_experiment_harness_plan.md` defines a future
  MLflow harness for paper-grade Cluster 1-3 reruns, larger-model campaigns,
  Modal cost/report imports, metric-gated reports, and optional tracing. MLflow
  is planned as an indexing/reporting layer around JSONL rows, sidecars, Modal,
  and repo analyzers; it must not become the source of scientific truth.

## Research Notes

Researched on 2026-05-27.

Modal billing:

- Modal exposes workspace billing reports through the
  `modal.billing.workspace_billing_report` Python API and the
  `modal billing report` CLI.
- Reports can include App tags, but cost is reported by full time intervals and
  billing data can be delayed by minutes. Treat actual cost as post-hoc, not
  a synchronous per-row return value.
- Modal App tags can be set in the App constructor or with `App.set_tags`.
  The current repo uses one shared App, `tritongen-gpu-harness`, with no tags.
  Per-experiment tags are therefore not currently available without changing
  shared Modal app setup or run discipline.
- Modal's granular billing report is pre-credit/pre-reservation cost. It is
  useful for attribution, not necessarily equal to final invoice total.
- Current public pricing page lists per-second GPU, CPU, and memory rates.
  These rates can seed an estimate, but the post-hoc billing report should be
  the source of truth where available.

Modal execution identity:

- Modal Functions expose `modal.current_function_call_id()` and
  `modal.current_input_id()` from inside a container. This repo already wraps
  those in `shared/modal_harness/runtime.py::current_modal_ids()`.
- Modal runtime environment variables include `MODAL_TASK_ID`,
  `MODAL_IMAGE_ID`, `MODAL_REGION`, `MODAL_CLOUD_PROVIDER`,
  `MODAL_ENVIRONMENT`, and `MODAL_IS_REMOTE`. These are good low-cost runtime
  provenance fields for telemetry sidecars.
- `modal.FunctionCall` supports `.spawn()`, object IDs, `.get()`,
  `.get_call_graph()`, and call graph input/task metadata, but current code
  mostly uses `.remote()`. Switching to `.spawn()` purely for telemetry is a
  larger behavior change and should not be first.

Modal GPU metrics:

- Modal documents GPU utilization, power utilization, temperature, and memory
  used as platform metrics. These are useful health/utilization signals, but
  Modal's docs explicitly position them as correlates rather than direct kernel
  performance diagnostics.
- There is no obvious per-function-call GPU metric API in the referenced docs.
  Record kernel timing in our evaluator where allowed; use Modal GPU metrics as
  dashboard or external observability, not as row-level scientific evidence.

Kernel timing:

- PyTorch CUDA Events can measure elapsed GPU time in milliseconds.
- Triton exposes `triton.testing.do_bench(fn, warmup=25, rep=100, ...)` for
  benchmarking callable runtime and percentile/median-style measurements.
- The existing shared metric contract already defines Level 4 performance
  fields (`kernel_time_ms`, `eager_time_ms`, `speedup_vs_eager`,
  `speedup_vs_compile`) in `shared/eval/schema.py`.

Sources:

- Modal billing guide: https://modal.com/docs/guide/billing
- Modal billing API: https://modal.com/docs/reference/modal.billing
- Modal billing CLI: https://modal.com/docs/reference/cli/billing
- Modal App tags: https://modal.com/docs/reference/modal.App
- Modal GPU metrics: https://modal.com/docs/guide/gpu-metrics
- Modal runtime environment variables: https://modal.com/docs/guide/environment_variables
- Modal function call IDs: https://modal.com/docs/reference/modal.current_function_call_id
- Modal function calls: https://modal.com/docs/reference/modal.FunctionCall
- Modal pricing: https://modal.com/pricing
- PyTorch CUDA Event: https://docs.pytorch.org/docs/2.12/generated/torch.cuda.Event.html
- Triton benchmarking: https://triton-lang.org/main/python-api/generated/triton.testing.do_bench.html

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

Current workspace state:

- `pyproject.toml` and `requirements.txt` require `modal>=1.0`.
- Local `.venv` has `modal` version `1.4.2`.
- Local Modal package exposes `modal.billing`,
  `modal.current_function_call_id`, and `modal.current_input_id`.
- Targeted schema tests passed:
  `shared/tests/test_modal_harness_schemas.py`,
  `cluster2/tests/test_modal_schemas.py`, and
  `cluster3/tests/test_cluster3_schema.py` passed with 227 tests.

Important current constraints:

- `cluster1/README.md` and `.contracts/research/eval_metrics.md` state that
  Cluster 1 evaluates Level 0/1 only and must not run numerical correctness,
  timing, profiling, speedup, or repair logic.
- `cluster2/README.md`, `cluster2/results/dataclass.py`, and
  `cluster2/modal/schemas.py` currently forbid timing, token, profiling, and
  speedup fields in Cluster 2 result rows and Modal payloads.
- `cluster3/README.md` says Cluster 3 v1 is compile-error repair only:
  profiler feedback, timing feedback, speedup optimization, and Level 4
  performance repair are deferred to a future contract.
- `shared/eval/schema.py` already has nullable fields for tokens, wall-ish
  generation time, kernel timing, speedup, and repair traces, but current
  cluster-specific rows do not uniformly serialize that shared schema.
- Phase 7a is currently active in local work: `shared/analysis/factorial.py`
  is modified and `shared/tests/test_analyzer_cluster3.py` is untracked. This
  plan must not overwrite or redirect that work.

## Eval-Ladder Clarification

The shorthand "Cluster 1 to F0, Cluster 2 to F2, Cluster 3 to F1" is not quite
right.

- Cluster 1 evaluates Level 0 and Level 1. It can produce F0 parse/signature or
  grammar-surface failures and F1 compile/runtime failures. Its positive
  outcome is compile-only, not functional correctness.
- Cluster 2 evaluates through Level 2 correctness for C and G+C paths. It can
  still terminally record F0/F1 failures before Level 2, and F2 failures once
  a compiled candidate is numerically wrong.
- Cluster 3 v1 owns P as compile-error repair. P observes `F1_COMPILE`
  evidence and attempts compile repair. In C+P or G+C+P, the reused C loop can
  fire only when an initial or post-P candidate reaches an F2 correctness
  failure.

So the better mental model is:

```text
Cluster 1: G factor, Level 0/1 compile-only evidence.
Cluster 2: C factor, Level 2 correctness repair and evaluation.
Cluster 3 v1: P factor, F1_COMPILE repair, with optional C reuse after F2.
```

## Interchangeability After Phase 7a

After Phase 7a, the analyzer is being taught to understand all eight factor
cells:

```text
none, G, C, G+C, P, G+P, C+P, G+C+P
```

That makes analysis more flexible, but the cluster pipelines are not fully
interchangeable implementations.

- G is a generation-time constraint plus offline semantic validation. It is
  safe to combine with C or P only when grammar variant, grammar SHA/path, and
  replay pairing are aligned.
- C is a test-driven Level 2 loop. It should not become a general error or
  performance repair loop.
- P v1 is a compile-error repair loop. It should not handle F0, F1 runtime,
  F2 numeric, or performance feedback unless a later contract expands it.
- C+P and G+C+P require explicit sequencing: generate with the appropriate G
  state, run initial correctness/compile classification, dispatch P only for
  F1_COMPILE, then optionally run C if the terminal or initial state is F2.
- The analyzer can compare P vs none, G+P vs G, C+P vs C, and G+C+P vs G+C,
  but the control rows come from different owners: none/G from Cluster 1
  replay controls, C/G+C from Cluster 2 generated rows.

The right architecture is factor-driven orchestration over cluster-owned
components, not making every cluster runner accept every behavior internally.

## Lowest-Blast-Radius Design

### 1. Add sidecar telemetry before touching row schemas

Create a shared observability package:

```text
shared/observability/
  __init__.py
  schema.py
  logger.py
  pricing.py
  modal_billing.py
```

Write two files next to each experiment output:

```text
<output>.observability.jsonl
<output>.observability.summary.json
```

The JSONL sidecar records stage and attempt telemetry. The summary records run
start/end, aggregate wall clock, estimated compute cost, billing lookup status,
and the source result JSONL path.

This avoids changing:

- `GenerationResult`;
- `Cluster2EvalRow`;
- `Cluster3EvalRow`;
- existing hash sidecars;
- current analyzer outputs;
- active Phase 7a files.

### 2. Key every telemetry row to existing durable identity

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

Use existing row canonical keys where possible. Do not include source text,
private eval payloads, raw feedback, or full tracebacks in telemetry.

### 3. Instrument local orchestration wall clock first

Use `time.perf_counter()` around existing call sites:

- Cluster 1:
  - `generate_source_modal(...)`;
  - `check_compiles_modal(...)`;
  - `_run_one_cell(...)`;
  - full runner wall clock.
- Cluster 2:
  - generated-condition `generation_call(...)`;
  - generated-condition `evaluation_call(...)`;
  - replay-control correctness calls;
  - repair-loop attempt boundaries;
  - full runner wall clock.
- Cluster 3:
  - generation;
  - correctness;
  - dispatcher;
  - P loop;
  - optional C loop;
  - full runner wall clock.

This gives immediate wall-clock coverage without Modal schema changes.

### 4. Add Modal runtime identity with minimal remote changes

Extend `shared/modal_harness/runtime.py` with a function such as
`current_modal_runtime_context()` that returns:

```text
function_call_id
input_id
task_id
image_id
environment
region
cloud_provider
is_remote
```

For Cluster 1, generation already returns function/input IDs and compile
already has a `metadata` field, so compile telemetry can be added with low
schema risk.

For Cluster 2, `modal_context` already carries generation function/input IDs.
Correctness payloads should add a parallel `modal_context` field if not
already present. Do not put performance/tokens inside `generation_result` until
the C2 forbidden-field contract is explicitly revised.

### 5. Token counts require a deliberate wire-contract change

Current generation code already computes output token count:

- `cluster1/generation/constrained_gen.py::DecodedKernel.generated_token_count`
- `cluster2/modal/generation.py::C2DecodedKernel.generated_token_count`

But Cluster 1 and Cluster 2 remote result schemas do not durably expose it.
Input token count is also available at generation time as the prompt sequence
length but is not returned.

Recommended change:

- Add an optional `generation_telemetry` object to remote generation results
  or wrapper payloads, with:
  - `prompt_token_count`;
  - `generated_token_count`;
  - `max_new_tokens`;
  - `stop_reason`;
  - `tokens_per_second`, computed only when generation wall time is known.
- Keep these fields out of Cluster 2 durable result rows at first.
- Update C2 forbidden-field validation so telemetry is allowed only under the
  specific telemetry object and still rejected in row/result payload fields.

### 6. Cost model should have two tiers

Actual Modal cost:

- Post-hoc only.
- Query `modal.billing.workspace_billing_report(...)` or
  `modal billing report --json`.
- Use run `started_at_utc` and `ended_at_utc`, rounded out to full billing
  intervals.
- Include App tags once static tags exist. Until then, filter by App/object
  name and time window.
- Record `cost_attribution_confidence`:
  - `exact_tagged_interval`;
  - `single_app_time_window`;
  - `ambiguous_concurrent_modal_activity`;
  - `unavailable`.

Estimated compute cost:

- Available during or immediately after a run.
- Use observed stage wall clock and requested resources:
  - GPU type/count;
  - CPU request;
  - memory request;
  - Modal pricing snapshot date and rate table.
- Mark it as estimate because Modal CPU/memory can bill based on the greater
  of request and actual usage, and container reuse/cold starts make per-row
  attribution approximate.

Field names:

```text
modal_actual_cost_usd
modal_actual_cost_source
modal_actual_cost_available_at_utc
modal_estimated_compute_cost_usd
modal_estimated_compute_cost_method
modal_pricing_snapshot
```

### 7. Kernel performance and speedup stay gated

Do not add kernel timing to Cluster 1 or Cluster 2 result rows. For those
clusters, telemetry should record:

```text
kernel_time_ms: null
speedup_vs_eager: null
speedup_vs_compile: null
performance_status: "not_evaluated_for_cluster_scope"
```

For Cluster 3, add Level 4 timing only after a dedicated performance contract
is accepted. The implementation should live in a narrow module such as:

```text
cluster3/profiling/timing.py
```

or, if the shared contract is ready:

```text
shared/eval/levels/level4_performance.py
```

Use `triton.testing.do_bench` or CUDA events. Measure only after Level 2
functional success. Record:

```text
kernel_time_ms
kernel_time_iqr_ms
eager_time_ms
torch_compile_time_ms
speedup_vs_eager
speedup_vs_compile
warmup_iters
timing_iters
timing_method
gpu_model
gpu_clock_mhz
```

### 8. App tags should start static, not per-run

Change `shared/modal_harness/app.py` from:

```python
app = modal.App("tritongen-gpu-harness")
```

to static low-risk tags:

```python
app = modal.App(
    "tritongen-gpu-harness",
    tags={"project": "tritongen", "component": "gpu-harness"},
)
```

Do not update tags dynamically per run until concurrency policy is settled.
Modal documents that tags can be included in billing reports, but app-level
tags are too coarse for concurrent per-experiment attribution.

## Proposed Rollout

### Phase A: Contract and schema sidecars

Files:

- add `shared/observability/schema.py`;
- add `shared/observability/logger.py`;
- add `shared/tests/test_observability_schema.py`;
- add `shared/tests/test_observability_logger.py`.

Deliverable:

- JSON-safe dataclasses for `ExperimentTelemetryEvent`,
  `ExperimentObservabilitySummary`, `ModalRuntimeContext`, and
  `CostEstimate`.
- Append logger with overwrite/resume semantics similar to C2/C3 JSONL loggers.

### Phase B: Wall clock and Modal identity

Files:

- `shared/modal_harness/runtime.py`;
- `cluster1/experiments/run_cluster1_modal.py`;
- `cluster2/experiments/run_cluster2_modal.py`;
- `cluster3/experiments/run_cluster3_modal.py`;
- runner tests for injected fake recorders.

Deliverable:

- Every logical stage records local wall clock and any available Modal call IDs.
- Summary files record run start/end and stage aggregates.

### Phase C: Token telemetry

Files:

- `shared/modal_harness/schemas.py`;
- `shared/modal_harness/generation.py`;
- `cluster2/modal/schemas.py`;
- `cluster2/modal/generation.py`;
- Cluster 1/2 modal schema tests.

Deliverable:

- Remote generation exposes prompt/generated token counts through telemetry.
- C2 forbids token fields everywhere except the approved telemetry object.
- Sidecars record tokens without changing result row semantics.

### Phase D: Estimated compute cost

Files:

- `shared/observability/pricing.py`;
- runner summary integration;
- pricing tests.

Deliverable:

- Estimated compute cost from wall-clock seconds, resource requests, and a
  dated Modal pricing snapshot.
- Explicit `estimate_only` caveats in summary.

### Phase E: Post-hoc Modal billing reconciliation

Files:

- `shared/observability/modal_billing.py`;
- optional CLI helper under `shared/observability/cli.py`;
- tests with mocked `modal.billing.workspace_billing_report`.

Deliverable:

- Summary can be updated with actual Modal billing report items when available.
- Actual cost is marked unavailable or ambiguous when the run window overlaps
  other Modal work.

### Phase F: Performance timing contract

Files:

- `cluster3/profiling/timing.py` or `shared/eval/levels/level4_performance.py`;
- Cluster 3 profiling tests with mocks/fakes;
- documentation update to Cluster 3 contract before enabling.

Deliverable:

- Cluster 3-only kernel timing and speedup for Level 2-passing candidates.
- Cluster 1/2 remain null/not-evaluated for performance fields.

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
- Existing result JSONL schemas remain loadable.
- Existing Phase 7a analyzer changes are untouched.
- Running Cluster 1/2/3 with a fake telemetry recorder emits deterministic
  sidecar rows.
- C2 result rows still reject timing/speedup/token fields except in the
  approved sidecar or telemetry wrapper.
- Sidecar rows never contain source text, private eval shapes, raw feedback, or
  raw tracebacks.
- Actual Modal cost is never required for a run to succeed.
- Estimated compute cost is clearly labeled as an estimate.
- Kernel timing is recorded only when the cluster contract enables Level 4.
- Analyzer/reporting can join telemetry sidecars by canonical identity but does
  not treat sidecar data as primary correctness evidence.

## Open Decisions

1. Whether per-experiment Modal cost should require isolated run windows, unique
   Modal environments, or future per-run app names. Static App tags are not
   enough for exact concurrent attribution.
2. Whether token counts belong only in sidecars or also in future shared
   `EvalResult` rows once all clusters converge on that schema.
3. Whether Cluster 3 v1 should remain strictly F1_COMPILE-only with performance
   telemetry null, or whether a later v2 should activate Level 4 timing.
4. Whether estimated compute cost should include container cold-start/model-load
   time as part of each experiment. For budget tracking it should; for per-row
   method comparison it should be reported separately.
5. Whether existing artifact registries need a new section for observability
   sidecars before any new paper-scale run.
