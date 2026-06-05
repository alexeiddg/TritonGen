# C3 n20 Metric-Family-Gated Experiment Packet

- Packet id: `C3-N20-METRIC-FAMILY-GATED-2026-06-05`
- Version: 0.1.0
- Date: 2026-06-05
- Status: draft / no execution authorized
- Branch: `codex/c3-n20-metric-family-gated-packet`
- Baseline: `d015862 Audit structural task S4 promotion`
- Packet type: preregistered future experiment packet only

## Explicit Non-Authorizations

This packet does not authorize:

- Modal execution;
- GPU execution;
- generation;
- experiment execution;
- benchmark execution;
- profiler execution;
- timing collection;
- speedup computation;
- output mutation;
- raw JSONL rewrite;
- analyzer output refresh;
- report artifact refresh;
- dependency or lockfile changes;
- paper-scale claims;
- performance or speedup claims.

Authorization flags:

```text
MODAL_AUTHORIZED: NO
GPU_AUTHORIZED: NO
GENERATION_AUTHORIZED: NO
EXPERIMENT_EXECUTION_AUTHORIZED: NO
OUTPUT_MUTATION_AUTHORIZED: NO
PAPER_SCALE_AUTHORIZED: NO
PERFORMANCE_EXECUTION_AUTHORIZED: NO
PROFILER_AUTHORIZED: NO
```

## Experiment Objective

Prepare a future Cluster 3 n20 experiment so structural/code-surface, task/
functional, mixed diagnostic, planned-deferred, future-only, and benchmarkable/
performance metrics are declared before any launch approval, analyzer refresh,
output mutation, or report-facing claim.

The future experiment question is whether P-containing conditions change:

- structural/code-surface outcomes such as Level 0/Level 1 validity, grammar
  acceptance, compile, and launch behavior;
- task/functional outcomes such as Level 2 numerical correctness;
- diagnostics such as gate reach, terminal failure movement, feedback
  eligibility, and feedback activation;
- future benchmarkable/performance readiness, only if a later packet attaches
  approved performance sidecar evidence.

This packet is a prerequisite for a later launch packet. It is not that launch
packet.

## Conditions

Future conditions under consideration:

| Condition | G active | C active | P active | Current packet status |
|---|---:|---:|---:|---|
| `P` | no | no | yes | planned_deferred |
| `G+P` | yes | no | yes | planned_deferred |
| `C+P` | no | yes | yes | planned_deferred |
| `G+C+P` | yes | yes | yes | planned_deferred |

No-P paired controls remain:

| P-containing condition | Paired no-P control |
|---|---|
| `P` | `none` |
| `G+P` | `G` |
| `C+P` | `C` |
| `G+C+P` | `G+C` |

The future launch packet must state whether existing no-P controls are reused,
replayed, or regenerated. This packet does not approve any of those choices.

## Kernel Class And Problem Scope

Initial proposed kernel class: `elementwise_relu`.

Rationale: current Cluster 3 development evidence and smoke surfaces are
elementwise/fp32-oriented. A later launch packet may broaden kernel classes
only by explicitly naming problem IDs, dtype policy, shape policy, pairing
policy, and expected output paths.

This packet does not approve kernel-class expansion.

## Sample-Size Target

Future target: `n=20` per condition cell.

The sample cell identity must include, at minimum:

- condition;
- kernel class;
- problem ID or stable kernel identity;
- dtype;
- shape policy when varied;
- model and decoding config;
- repair-history policy;
- grammar variant when G is active.

This packet does not authorize producing those samples.

## Model And Generation Policy

This packet does not select or authorize a model.

A future launch packet must specify:

- exact model ID;
- model revision;
- tokenizer revision;
- decoding config;
- prompt/template version;
- grammar policy and grammar variant;
- grammar hash when G is active;
- repair-history policy;
- seed policy;
- retry and repair budgets;
- max generation attempts;
- source of any cached attempts;
- private-eval and prompt-content boundaries.

Generation remains unauthorized until that future launch packet is signed.

## Modal Execution Policy

This packet does not authorize Modal or GPU work.

A future launch packet must specify:

- exact branch and commit;
- Modal app/function entrypoint;
- Modal image ID or digest policy;
- Modal workspace/account assumptions;
- credential and secrets handling;
- pre-spend checks;
- max wall clock;
- max estimated cost;
- stop conditions;
- expected output paths;
- expected sidecar paths;
- post-run validation commands.

Any command expansion, resume, retry, output-path change, or condition expansion
requires a new approval packet.

## Output Mutation Policy

No output mutation is authorized by this packet.

The future launch packet must specify exact paths for:

- raw Cluster 3 JSONL rows;
- content-hash sidecars;
- observability sidecars;
- performance sidecars if performance work is separately authorized;
- audit reports;
- analyzer outputs if an analyzer refresh is separately authorized.

The future launch packet must also state:

- whether each path must not exist before launch;
- archive/overwrite policy;
- no raw artifact rewrite policy;
- row-count expectations;
- sidecar join keys;
- hash validation policy.

Raw artifacts must not be rewritten by this packet or by any later packet unless
that later packet explicitly authorizes the exact mutation.

## Metric-Family Declaration Table

Registry-compatible statuses are used here. The experiment is intended for a
future launch, but unevidenced metrics remain `planned_deferred` or
`future_only` until compatible evidence exists.

| metric_name | outcome_family | level_gate | metric_gate | reportability | current_status | evidence_source | denominator_policy | claim_boundary |
|---|---|---|---|---|---|---|---|---|
| `level2_functional_success_rate` | `task_functional` | `level2_correctness` | `correctness` | `reportable_primary` only if all paper-scale prerequisites, output paths, analyzer metadata, and row validations pass | `planned_deferred` (packet intent: planned_for_execution) | future Cluster 3 result rows with Level 2 evidence | intent-to-treat over generated rows unless existing analyzer policy explicitly excludes a diagnostic failure | primary correctness claim only after all cells complete and analyzer metadata validates |
| `level1_compile_success_rate` | `structural_code_surface` | `level1_compile_launch` | `compile_success` | `reportable_secondary` or `diagnostic_only`, not headline task correctness | `planned_deferred` | future Cluster 3 result rows with Level 1 evidence | intent-to-treat over generated rows, preserving F0/F1/F2/F3 terminal distinctions and existing F3 compile-rate policy | structural/code-surface claim only; compile success does not prove task/functional correctness |
| `grammar_valid_rate` | `structural_code_surface` | `level0_parse_surface` | `grammar_valid` | `diagnostic_only` | `planned_deferred` | future G-active rows with compatible grammar metadata | grammar-active generated rows with explicit `grammar_valid`, `gbnf_parse_valid`, and `semantic_valid` evidence | grammar acceptance is structural/diagnostic and not compile or Level 2 correctness |
| `compile_pass_at_k` | `structural_code_surface` | `level1_compile_launch` | `compile_success` | `diagnostic_only` unless a later packet promotes it | `planned_deferred` | future gate-specific sample groups with Level 1 counts | sample groups by condition/kernel/dtype/seed policy only when gate-specific counts exist | may be displayed only as compile-gated pass@k, never as bare pass@k or task correctness |
| `terminal_failure_distribution` | `mixed_diagnostic` | `failure_taxonomy` | `terminal_failure` | `diagnostic_only` | `planned_deferred` | future terminal row states | all terminal rows, retaining F0_PARSE, F1_COMPILE, F1_RUNTIME, F2_FUNCTIONAL-style failures, F3, and success states distinctly | explains movement across gates but does not replace primary condition comparisons |
| `diagnostics.level_reach_rates` | `mixed_diagnostic` | `failure_taxonomy` | `level_reach` | `diagnostic_only` | `planned_deferred` | future analyzer diagnostics from Cluster 3 rows | all generated rows per condition, with Level 0/1/2 reach denominators reported separately | gate reach is explanatory and not a primary success metric unless preregistered otherwise |
| `diagnostics.feedback_activation` | `mixed_diagnostic` | `failure_taxonomy` | `feedback_activation` | `diagnostic_only` | `planned_deferred` | future analyzer diagnostics from C/P route fields | all generated rows for activation rates, plus eligible-set subdiagnostics for C and P | feedback activation is diagnostic unless a later packet preregisters it as a response |
| `diagnostics.metric_availability` | `mixed_diagnostic` | `not_applicable` | `metric_availability` | `diagnostic_only` | `planned_deferred` | future analyzer metadata | one availability decision per metric and condition or declared scope | availability metadata controls fail-closed reporting; it is not result evidence |
| `syntax_valid_rate` | `structural_code_surface` | `level0_parse_surface` | `syntax_valid` | `not_reportable` | `planned_deferred` | future compatible syntax evidence only | all generated rows with explicit compatible syntax evidence and a shared definition ID | must not be reported as computed until compatible row-level syntax evidence exists |
| `correctness_pass_at_k` | `task_functional` | `level2_correctness` | `correctness` | `not_reportable` until Level 2 sample groups exist and preregistered analysis validates | `planned_deferred` | future Level 2 sample groups | sample groups with Level 2 evidence, same grouping policy across compared cells | may be displayed only as correctness-gated pass@k, never as bare pass@k |
| `benchmarkable_pass_at_k` | `benchmarkable_performance` | `level4_performance` | `future_performance` | `future_only` | `future_only` | future Level 2 passing rows plus approved performance sidecar evidence | correct rows that reach an authorized Level 4/performance stage | must not be presented as current without a later approved performance sidecar |
| `speedup_or_performance_metric` | `benchmarkable_performance` | `level4_performance` | `future_performance` | `future_only` | `future_only` | future O6-style performance sidecar evidence, if separately approved | Level 2 passing rows with matching timing baseline, device, dtype, shape, and sidecar join keys | no performance improvement, timing, profiler, benchmark, or speedup claim is authorized by this packet |

## Denominator Policy

Primary condition comparisons use intent-to-treat denominators over generated
rows unless an existing analyzer policy explicitly defines a metric-specific
exception.

Required denominator rules:

- Do not drop F0/F1 rows merely because C did not activate.
- Do not drop non-F1_COMPILE rows merely because P did not activate.
- Preserve F0_PARSE, F1_COMPILE, F1_RUNTIME, F2 functional failures, F3, and
  success terminal states as distinguishable outcomes.
- Keep eligible-set analyses diagnostic and adjacent to primary comparisons.
- Keep loop-fired analyses diagnostic and adjacent to primary comparisons.
- Preserve existing analyzer handling for F3 compile-rate denominators unless a
  later analyzer contract explicitly changes it.

## Attempt-Collapse Policy

The future launch packet must bind attempt handling before execution.

Default policy for this packet:

- attempt 0 is the initial generated candidate;
- repeated attempts are retained in raw rows or trace summaries according to the
  existing Cluster 3 schema;
- analyzer-facing summaries collapse attempts by experimental unit using the
  selected response variable only when that behavior is already documented by
  the analyzer contract;
- `attempts_observed` and `attempts_considered` are diagnostic;
- mixed repair-history policies must be grouped, quarantined, or rejected
  before report-facing comparisons.

## Gate Eligibility Policy

Future Cluster 3 routing must preserve v1 boundaries:

- F0_PARSE and other F0 surface failures terminate.
- P repairs only `F1_COMPILE`.
- `F1_RUNTIME` remains terminal unless a later Cluster 3 v2 contract explicitly
  changes the policy.
- C repairs only F2 numerical or shape correctness failures.
- F3 remains an infrastructure/eval-pipeline failure and is not model success.
- P must not observe F0, F1_RUNTIME, F2, F3, private Level 2 details, profiler
  data, timing data, or speedup data.
- C must not repair F0, F1, or F3 failures.

Direct initial-F2 C paths must be labeled separately from post-P F2 paths when
both are present. In particular:

- direct initial-F2 C path: Level 2 failed before P repair was needed or after a
  no-P route;
- post-P F2 path: P repaired a compile failure or otherwise moved the row to a
  Level 2 failure before C became eligible.

## Feedback Activation Policy

Feedback activation metrics are diagnostics unless preregistered otherwise in a
later launch packet.

Required diagnostics:

- `p_feedback_eligible_rate`: rows ending in `F1_COMPILE` while P is active.
- `p_feedback_loop_fired_rate`: P loop fired among generated rows and among the
  P-eligible set.
- `c_feedback_eligible_rate`: rows ending in F2 while C is active.
- `c_feedback_loop_fired_rate`: C loop fired among generated rows and among the
  C-eligible set.
- direct initial-F2 C activation split from post-P F2 C activation when both
  are present.

Activation rates do not replace primary task/functional or structural/code-
surface comparisons.

## Claim Boundary

This packet:

- does not authorize paper-scale claims;
- does not authorize Modal or GPU execution;
- does not authorize output mutation;
- does not authorize analyzer output refresh;
- does not authorize raw JSONL rewrite;
- does not authorize performance or speedup claims;
- does not authorize causal claim language;
- does not claim P lift, C lift, G lift, interaction effects, or all-condition
  2^3 completion.

Future claims require:

- compatible factorial design;
- fixed budgets;
- compatible denominators;
- same shapes, dtypes, and devices where compared;
- preregistered metrics;
- validated metric registry schema versions;
- complete output paths and sidecar paths;
- clean post-run validation;
- a signed approval packet for the exact claim scope.

If an unknown `metric_registry` major schema is encountered, paper-facing output
must fail closed or mark the affected metric diagnostic-only.

## Sidecar Requirements

Observability sidecars are expected for a future launch if enabled by the launch
packet. This packet does not create or authorize sidecars.

Required future sidecar policy:

- sidecars must be additive and keyed to row identity;
- scientific JSONL rows remain the source of truth for outcomes;
- observability sidecars may record approved runtime, token, Modal identity, and
  estimated/unavailable cost metadata when separately authorized by the
  observability contracts;
- performance/timing/speedup values require a separate performance sidecar
  authorization and compatible Level 2 correctness prerequisites;
- performance sidecar evidence must include device, dtype, shape, baseline,
  timing method, sidecar path, and join-key policy before any performance claim.

Performance sidecar authorization status for this packet: not authorized.

## Fail-Closed Rules

Future analyzer, report, launch, or paper-readiness consumers must fail closed
or mark affected metrics diagnostic-only when:

- an unknown `metric_registry` major schema is encountered;
- `outcome_family` is missing;
- `reportability` is missing;
- `current_status` is missing;
- `level_gate` or `metric_gate` is missing;
- `current_status` conflicts with computed values;
- `reportability` conflicts with computed values;
- `planned_deferred` metrics are presented as current computed values;
- `future_only` metrics are presented as current computed values;
- compile-only evidence is presented as task/functional correctness;
- structural/code-surface metrics are used as primary correctness evidence;
- task/functional metrics are described as structural-only gains;
- benchmarkable/performance claims are requested without approved performance
  sidecar evidence;
- output paths, sidecar paths, row-count expectations, or validation commands
  are missing from a future launch packet;
- C fires outside F2 eligibility;
- P fires outside `F1_COMPILE` eligibility.

## Launch Prerequisites

A future launch packet must specify:

- exact branch and commit;
- exact model and decoding config;
- exact conditions;
- exact `n` per condition;
- kernel classes and problem IDs;
- dtype and shape policy;
- Modal image digest policy;
- output JSONL paths;
- content-hash sidecar paths;
- observability sidecar paths;
- performance sidecar paths if performance work is separately authorized;
- analyzer version expectation;
- metric registry schema expectation;
- outcome family schema expectation;
- registry provenance expectation;
- no raw artifact rewrite policy;
- retry budgets;
- P repair budget;
- C repair budget;
- seed policy;
- grammar policy and grammar hash;
- repair-history policy;
- failure stop conditions;
- row-count expectations;
- post-run validation commands;
- claim-boundary text for each report-facing metric;
- independent review requirement.

Missing launch prerequisites keep execution blocked.

## Next Step

Review this packet. If the packet review passes, create a separate future launch
approval packet with exact commands, paths, budgets, branch/commit, sidecar
paths, and validation commands. Do not run Modal, GPU jobs, generation,
experiments, benchmarks, profilers, timing, speedup, analyzer refresh, output
mutation, or paper-scale work from this packet alone.
