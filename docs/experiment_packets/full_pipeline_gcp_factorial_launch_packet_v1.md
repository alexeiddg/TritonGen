# Full Pipeline G/C/P Factorial Launch Packet v1

## Packet Identity

packet_id: `FULL_PIPELINE_GCP_FACTORIAL_LAUNCH_PACKET_V1`
packet_type: draft launch planning packet
branch: `codex/full-pipeline-launch-packet-v1`
baseline_commit: `7d9ac22 Add C3 n20 metric family packet`
created_at: 2026-06-05
status: `DRAFT_NOT_APPROVED`
AUTHORIZES_EXECUTION: NO

Execution authorization flags:

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
BILLING_QUERY_AUTHORIZED: NO
CREDENTIAL_USE_AUTHORIZED: NO
DEPENDENCY_CHANGE_AUTHORIZED: NO
```

This packet creates a plan only. It does not authorize Modal, GPU work,
generation, experiments, benchmarks, profilers, output mutation, analyzer output
refresh, report artifact refresh, MLflow runtime writes, billing queries,
dependency changes, lockfile changes, or paper-scale claims.

## Objective

Plan the first fresh post-change Cluster 3 G/C/P run after MLflow tracking,
observability sidecars, `agentic_transcript_v1` repair memory, and
structural/task reporting changes have landed in the handoff trunk.

The packet answers four launch-design questions:

1. whether to target a fresh 8-cell G/C/P factorial or only the 4 P-containing
   Cluster 3 extension;
2. whether the next execution gate should be smoke/dev or paper-scale;
3. how MLflow should index repo artifacts post-hoc;
4. how result rows, content hashes, observability sidecars, analyzer outputs,
   report artifacts, repair-history labels, metric-family metadata, and billing
   reconciliation should join without making any metadata layer authoritative.

## Governing Evidence

This plan was written against these governing surfaces:

- `docs/15_experiment_change_orchestration_contract.md`
- `docs/experiment_packets/c3_n20_metric_family_gated_packet.md`
- `docs/16_observability_sidecar_implementation_spec.md`
- `docs/17_structural_task_analyzer_metadata_implementation_spec.md`
- `docs/18_agentic_transcript_v1_implementation_spec.md`
- `docs/14_structural_vs_task_outcome_reporting_plan.md`
- `docs/07_analysis_and_statistics.md`
- `.contracts/research/mlflow_tracking_policy.md`
- `docs/tracking/README.md`
- `shared/tracking/README.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

`audits/full_pipeline_run_recon_report.md` was not present in this checkout.
The local reconnaissance conclusion supplied to this packet is therefore treated
as task context, while the files above remain the inspected repo evidence.

## Scientific Rationale

The scientifically meaningful post-change reason to rerun is
`agentic_transcript_v1`, because it changes C/P repair prompt behavior. MLflow,
observability sidecars, and structural/task metric metadata improve auditability,
provenance, report interpretation, and artifact indexing, but they do not by
themselves change the generated candidates or repair loop behavior.

A fresh run should therefore avoid mixing historical `last_attempt_only_v1`
controls with new `agentic_transcript_v1` treatment cells in headline paper
claims. Historical rows remain useful as baselines, diagnostics, or
compatibility checks only when the analysis explicitly models repair-history
policy as a cohort/factor and labels the caveat.

## Design Choice

Selected design: fresh 8-cell G/C/P factorial.

Conditions:

- `none`
- `G`
- `C`
- `P`
- `G+C`
- `G+P`
- `C+P`
- `G+C+P`

The rejected narrower design is a 4-cell P-containing extension:

- `P`
- `G+P`
- `C+P`
- `G+C+P`

The 4-cell extension is cheaper and aligns with the existing Cluster 3 n20
metric-family packet, but it risks primary comparisons against older no-P
controls unless the launch packet explicitly reuses those controls as a
separate historical cohort. A fresh all-cell run is cleaner for attribution
across grammar constraint G, correctness feedback C, compile feedback P, repair
history policy, structural/code-surface outcomes, and task/functional outcomes.

## Recommended Execution Gate

The next executable gate should be L1 smoke/dev, not L2 paper-scale.

L1 should be `n=1` or another small explicitly bounded sample that proves:

- the command path is valid;
- all output namespaces are fresh;
- content-hash sidecars are written;
- observability sidecars write in the approved mode;
- rows carry repair-history labels where applicable;
- analyzer grouping/quarantine handles repair-history policy;
- structural/task metric metadata can be consumed;
- MLflow post-hoc indexing can import or index artifacts after they exist;
- no overwrite/resume behavior occurs without approval.

L1 is not paper evidence. L2 paper-scale remains blocked until L1 passes and a
separate signed approval packet names exact commands, paths, model revisions,
budgets, stop conditions, analysis commands, reporting commands, MLflow import
commands, and cost/spend boundaries.

## Execution Ladder

| Level | Status | Purpose | Scope | Authorization state |
|---|---|---|---|---|
| L0 packet only | current phase | Plan the launch design and artifact policy | Docs only; no outputs; no MLflow runtime writes | Open in this packet; execution not authorized |
| L1 smoke/dev | future only | Validate command path, namespace, sidecars, analyzer compatibility, MLflow post-hoc indexing, and no-overwrite protections | `n=1` or small n; exact command and paths required in a later approval | Blocked pending explicit user approval |
| L2 paper-scale | future only | Paper candidate for the selected 8-cell design | Proposed `n=20` per condition only after L1 passes | Blocked pending L1 pass, Gate G8, exact cost/spend boundary, exact Modal command, exact output paths, exact analyzer/report/MLflow import commands, and explicit user approval |

## Condition Matrix

| condition | G active? | C active? | P active? | repair_history_policy | expected feedback eligibility | primary structural metrics | primary task metrics | diagnostics | comparability notes |
|---|---:|---:|---:|---|---|---|---|---|---|
| `none` | no | no | no | `not_applicable`; no repair-loop memory activation | No C or P feedback | `level1_compile_success_rate`, syntax/harness diagnostics where evidence exists | `level2_functional_success_rate` if Level 2 evidence exists | terminal failure distribution, `level_reach_rates`, `metric_availability` | Fresh control for all G/C/P factors; do not reuse old `last_attempt_only_v1` rows for primary claims unless modeled as historical cohort |
| `G` | yes | no | no | `not_applicable`; no repair-loop memory activation | Grammar constraint only; no C or P feedback | `grammar_valid_rate`, `level1_compile_success_rate`, syntax/harness diagnostics | `level2_functional_success_rate` if Level 2 evidence exists | grammar rejection layer, terminal failures, `level_reach_rates`, `metric_availability` | Fresh G-only control; historical G rows are diagnostic unless explicitly modeled |
| `C` | no | yes | no | `agentic_transcript_v1` when C repair loop is explicitly enabled | C repairs only F2 functional failures; F0/F1/F1_RUNTIME/F3 do not trigger C | `level1_compile_success_rate` and gate reach | `level2_functional_success_rate`, repair-set/eval-set success where evidence exists | `feedback_activation`, initial-F2 C path, terminal failure distribution, mixed policy quarantine | Compare to fresh `none`; old C rows under `last_attempt_only_v1` are historical baselines only |
| `P` | no | no | yes | `agentic_transcript_v1` when P repair loop is explicitly enabled | P repairs only F1_COMPILE; F1_RUNTIME remains terminal; F0/F2/F3 do not trigger P | `level1_compile_success_rate`, compile repair success, compile pass@k if gate-qualified | `level2_functional_success_rate` only after Level 2 evidence exists | `feedback_activation`, P attempt count, terminal failure distribution, `level_reach_rates` | Compare to fresh `none`; old P rows under `last_attempt_only_v1` are not primary-comparable |
| `G+C` | yes | yes | no | `agentic_transcript_v1` when C repair loop is explicitly enabled | Grammar plus C repairs only F2 | `grammar_valid_rate`, `level1_compile_success_rate` | `level2_functional_success_rate`, repair-set/eval-set success where evidence exists | grammar rejection, C activation, terminal failures, `metric_availability` | Compare to fresh `G` and fresh `C`; old G+C rows are historical unless explicitly modeled |
| `G+P` | yes | no | yes | `agentic_transcript_v1` when P repair loop is explicitly enabled | Grammar plus P repairs only F1_COMPILE; F1_RUNTIME remains terminal | `grammar_valid_rate`, `level1_compile_success_rate`, compile repair success | `level2_functional_success_rate` only after Level 2 evidence exists | grammar rejection, P activation, terminal failures | Compare to fresh `G` and fresh `P`; do not treat reused Phase 12/14 G+P as primary paper evidence |
| `C+P` | no | yes | yes | `agentic_transcript_v1` when C/P loops are explicitly enabled | P repairs only F1_COMPILE; C repairs only F2; direct initial-F2 and post-P F2 paths must be distinct | `level1_compile_success_rate`, compile repair success, gate reach | `level2_functional_success_rate`, C repair success where evidence exists | P activation, C activation, initial-F2 vs post-P F2, terminal failures, mixed policy quarantine | Compare to fresh `C`, fresh `P`, and fresh `none`; mixed legacy controls require explicit caveat |
| `G+C+P` | yes | yes | yes | `agentic_transcript_v1` when C/P loops are explicitly enabled | Grammar plus P F1_COMPILE repair plus C F2 repair; F1_RUNTIME remains terminal | `grammar_valid_rate`, `level1_compile_success_rate`, compile repair success | `level2_functional_success_rate`, C repair success where evidence exists | `feedback_activation`, initial-F2, post-P F2, grammar rejection, terminal failures | Full treatment cell; primary comparisons require fresh all-cell controls under the same policy and budgets |

## Kernel And Problem Scope

Recommended L1 scope:

- kernel class: `elementwise_relu` or another explicitly named Cluster 3 smoke
  fixture selected before approval;
- problem IDs: exact stable problem IDs must be listed in the future approval
  packet;
- scale tier: smoke/dev only;
- row count: `n=1` per selected condition or another small bounded n explicitly
  approved before execution.

Recommended L2 scope:

- kernel class: start with the same class validated by L1 unless the L2 packet
  explicitly broadens scope;
- proposed row count: `n=20` per condition cell;
- all problem IDs, seeds, shapes, dtypes, model revisions, grammar variants, and
  repair budgets must be fixed before approval.

## Dtype And Shape Scope

Recommended initial dtype is `fp32`, matching the current Cluster 3 Phase 14e
development matrix orientation. A later packet may add `fp16` or `bf16` only if
it explicitly locks shape/dtype/device policy, denominator handling, and
separate claim boundaries.

Shape scope must be fixed before execution. If shapes differ across conditions,
the future packet must specify matching or stratification rules before any
headline paired analysis.

## Model And Decoding Policy

A future executable packet must specify:

- `model_id`;
- `model_revision` or an explicit unavailable reason;
- tokenizer revision if relevant;
- decoding configuration;
- seed policy;
- maximum generation attempts;
- maximum repair attempts;
- prompt/template versions;
- grammar variant and grammar hash for G-active cells;
- whether all cells use the same model/revision/decoding configuration.

No model download, tokenizer download, API call, generation call, or dependency
change is authorized by this packet.

## Repair-History Policy

`agentic_transcript_v1` must be explicitly enabled in the future command or
configuration for C/P repair loops. It is not the default.

Policy requirements:

- `none` and `G` have no repair-loop memory activation.
- C/P cells must label `repair_history_policy` in rows/artifacts when the
  current schema supports it.
- `agentic_transcript_v1` applies only to C/P repair loops when enabled.
- P repairs only F1_COMPILE.
- C repairs only F2.
- F1_RUNTIME remains terminal.
- Direct initial-F2 C paths must remain distinct from post-P F2 paths.
- If explicit `agentic_transcript_v1` validation fails, the run must fail closed
  rather than silently falling back to `last_attempt_only_v1`.
- Analyzer/reporting must group or quarantine by `repair_history_policy`.
- Historical `last_attempt_only_v1` outputs are baselines/diagnostics only
  unless a future packet explicitly models policy as a cohort/factor.

New `agentic_transcript_v1` artifacts must not share output paths with legacy
`last_attempt_only_v1` artifacts.

## Observability Policy

Future L1 smoke/dev recommendation:

- mode: `best_effort` unless the approval packet chooses `required`;
- `observability_experiment_id`: `full_pipeline_gcp_factorial_v1`;
- `observability_run_id`: explicit per execution, for example
  `full_pipeline_gcp_factorial_v1_smoke_<YYYYMMDD>_<shortid>`;
- sidecar path: use the namespace in this packet;
- failure behavior: preserve scientific rows; degraded sidecars make the run
  development-only and must be recorded in the handoff.

Future L2 paper-scale recommendation:

- mode: `required` unless the approval packet explicitly accepts the gap;
- sidecar initialization failure aborts before remote work;
- mid-run sidecar failure stops further work, preserves partial artifacts, and
  requires audit before resume/rerun;
- missing summary/hash sidecars block observability coverage claims.

Join keys:

- `experiment_id`;
- `run_id`;
- output JSONL path;
- row identity fields;
- row SHA256 when available;
- condition;
- kernel class;
- dtype;
- seed/problem ID.

Observability metadata remains sidecar-only. Scientific rows must not be mutated
solely to add token, duration, Modal, billing, cost, or observability-only
metadata unless the current schema already supports the field and the future
packet explicitly authorizes that behavior.

## MLflow Post-Hoc Indexing Policy

MLflow is not the source of truth and is not authoritative. JSONL rows, content
hash sidecars, observability sidecars, analyzer JSON, report files, and billing
reconciliation artifacts remain authoritative in repo/artifact paths.

MLflow should hook into the pipeline as a post-hoc artifact index and dashboard:

```text
Modal GPU work
-> local runner writes JSONL rows
-> content-hash sidecars validate output bytes
-> observability sidecars record operational metadata
-> analyzer/report commands produce derived artifacts
-> optional post-hoc MLflow importer indexes params, tags, metrics, and artifact pointers/copies
```

Modal containers should not be required to import or call MLflow. The local
orchestrator may use existing optional `shared/tracking` live metrics when
`TRITONGEN_MLFLOW=1` and `mlflow` is importable, but that gate is not sufficient
for broad artifact indexing unless a post-hoc importer exists.

Future work item M0:

- implement or script a post-hoc MLflow artifact importer before L2 paper-scale;
- importer input should be already-written repo artifacts;
- importer must not recompute scientific metrics except by invoking accepted
  repo analyzers under an explicitly authorized analyzer/report plan;
- importer must not modify raw JSONL, hash sidecars, observability sidecars,
  analyzer JSON, report files, or billing artifacts;
- importer must be idempotent by `experiment_id`, `run_id`, artifact path, and
  artifact SHA256.

This packet does not authorize creating MLflow runs, starting an MLflow server,
or writing to `mlruns/`.

### MLflow Logging And Indexing Table

| item | MLflow type | source of truth | timing | join key | notes |
|---|---|---|---|---|---|
| `experiment_id` | tag | launch packet / observability sidecar | post-hoc | `experiment_id` | Logical design identity |
| `run_id` | tag | launch packet / observability sidecar | post-hoc | `run_id` | Concrete execution attempt |
| `cluster` | tag | launch packet / row metadata | post-hoc | output path + row metadata | Expected `cluster3` for this packet |
| `phase` | tag | launch packet / handoff | post-hoc | `experiment_id` | L1 smoke/dev or L2 paper-scale |
| `condition` | tag/param | JSONL rows | post-hoc or in-run if available | condition + row identity | Per-row or per-child-run index policy must be fixed before L2 |
| `grammar_active` | param/tag | condition matrix / row metadata | post-hoc | condition | G factor |
| `correctness_feedback_active` | param/tag | condition matrix / row metadata | post-hoc | condition | C factor |
| `compile_feedback_active` | param/tag | condition matrix / row metadata | post-hoc | condition | P factor |
| `repair_history_policy` | param/tag | row/artifact metadata | post-hoc | repair_history_policy + output path | Required for C/P comparability |
| `model_id` | param | future approval packet / row metadata | post-hoc | run_id | Must be explicit before execution |
| `model_revision` | param | future approval packet / row metadata | post-hoc | run_id | Use explicit unavailable reason if absent |
| decoding config | param/artifact | future approval packet | post-hoc | run_id | Store sanitized config, not secrets |
| seed | param/metric table artifact | JSONL rows | post-hoc | row identity | Per-row index or summary artifact |
| dtype | param/tag | JSONL rows | post-hoc | row identity | Required for stratification |
| kernel class | param/tag | JSONL rows | post-hoc | row identity | Required for scope labels |
| problem ID | param/artifact | JSONL rows | post-hoc | row identity | Use artifact table if too many values |
| output JSONL path | artifact/tag | repo output path | post-hoc | output path | Pointer or copied artifact only |
| output JSONL SHA256 | tag/artifact | content-hash sidecar | post-hoc | output path + hash | Must match repo sidecar |
| content-hash sidecar path | artifact/tag | repo sidecar | post-hoc | output path | Never rewrite sidecar |
| observability event sidecar path | artifact/tag | observability sidecar | post-hoc | experiment_id + run_id | Required for observability coverage claims |
| observability summary sidecar path | artifact/tag | observability summary | post-hoc | experiment_id + run_id | Summary is operational evidence |
| observability hash sidecar path | artifact/tag | observability hash sidecar | post-hoc | experiment_id + run_id | Required for sidecar integrity |
| analyzer JSON path | artifact/tag | analyzer output | post-hoc | analysis_id / output paths | Analyzer remains authoritative for derived metrics |
| analyzer schema/registry version | tag/param | analyzer metadata | post-hoc | analyzer JSON path | Include `metric_registry_v1` / `outcome_family_v1` when present |
| report path | artifact/tag | report files | post-hoc | analyzer JSON path | Report is derived from analyzer output |
| billing reconciliation path | artifact/tag | billing artifact if later available | post-hoc | experiment_id + run_id + billing window | Only after separate billing approval; raw billing not committed |
| `level2_functional_success_rate` | metric | analyzer JSON | post-hoc | analyzer output + condition | task_functional primary only when prerequisites pass |
| `level1_compile_success_rate` | metric | analyzer JSON | post-hoc | analyzer output + condition | structural_code_surface secondary/diagnostic |
| `feedback_activation` | metric/artifact | analyzer diagnostics / rows | post-hoc | condition + policy | Mixed diagnostic |
| `level_reach_rates` | metric/artifact | analyzer diagnostics | post-hoc | condition | Mixed diagnostic |
| `metric_availability` | artifact | analyzer diagnostics | post-hoc | analyzer JSON path | Required for deferred/future metrics |

## Structural/Task Metric-Family Policy

Future packets and analyzer/report outputs must preserve the S4 metric-family
guidance:

- structural/code-surface metrics use `outcome_family=structural_code_surface`;
- task/functional metrics use `outcome_family=task_functional`;
- mixed diagnostics use `outcome_family=mixed_diagnostic`;
- benchmarkable/performance metrics use `outcome_family=benchmarkable_performance`
  and remain `future_only` unless a later O6-style performance packet authorizes
  measurement.

Primary task metrics:

- `level2_functional_success_rate`;
- repair-set success where explicit Level 2 repair-set evidence exists;
- eval-set success where explicit Level 2 eval-set evidence exists;
- `correctness_pass_at_k` only if gate-qualified and not bare pass@k.

Primary/secondary structural metrics:

- syntax validity when compatible explicit evidence exists;
- grammar validity for G-active rows;
- harness compatibility;
- `level1_compile_success_rate`;
- `compile_pass_at_k` only if gate-qualified and not bare pass@k.

Mixed diagnostics:

- terminal failure distribution;
- `level_reach_rates`;
- `feedback_activation`;
- `metric_availability`.

Future-only/performance:

- `benchmarkable_pass_at_k`;
- speedup;
- timing;
- profiler outputs;
- performance metrics requiring a separate O6-style sidecar and approval.

S4 does not change runtime behavior by itself. The launch, analyzer, report, and
MLflow indexing commands must consume the metadata to benefit from it.

## Output Namespace Reservation

Fresh namespaces:

```text
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/
outputs/cluster3/full_pipeline_gcp_factorial_v1/n20/
artifacts/observability/full_pipeline_gcp_factorial_v1/smoke/
artifacts/observability/full_pipeline_gcp_factorial_v1/n20/
artifacts/analysis/full_pipeline_gcp_factorial_v1/
artifacts/reports/full_pipeline_gcp_factorial_v1/
artifacts/mlflow_index/full_pipeline_gcp_factorial_v1/
artifacts/billing/full_pipeline_gcp_factorial_v1/
```

No overwrite policy:

- output JSONL names must include condition, n, dtype, kernel scope, and date or
  run_id;
- if any target path exists, stop unless an explicit resume/append/archive
  policy is approved before execution;
- raw JSONL must never be rewritten to repair metadata;
- content-hash sidecars must be generated from the final JSONL bytes;
- legacy outputs must not be reused as fresh controls for primary claims.

Example future L1 names, not authorized by this packet:

```text
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-none_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-g_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-c_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-p_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-g-plus-c_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-g-plus-p_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-c-plus-p_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_gcp_factorial_v1/smoke/condition-g-plus-c-plus-p_n1_fp32_elementwise_relu_<run_id>.jsonl
```

## Sidecar Namespace Reservation

Expected sidecars:

- content-hash sidecar adjacent to each JSONL output;
- observability event sidecar;
- observability summary sidecar;
- observability hash sidecar.

Preferred L1 sidecar namespace:

```text
artifacts/observability/full_pipeline_gcp_factorial_v1/smoke/<run_id>/
```

Preferred L2 sidecar namespace:

```text
artifacts/observability/full_pipeline_gcp_factorial_v1/n20/<run_id>/
```

If sidecars stay adjacent to output JSONL paths, the future packet must show the
exact derived event, summary, and hash paths before approval.

## Analyzer And Report Namespace Reservation

Analyzer and report artifacts should be separate from raw outputs:

```text
artifacts/analysis/full_pipeline_gcp_factorial_v1/<run_id>/factorial_analysis.json
artifacts/reports/full_pipeline_gcp_factorial_v1/<run_id>/
```

The future packet must list exact analyzer and report commands. Analyzer output
refresh and report artifact refresh are not authorized here.

## Billing Namespace Reservation

Billing reconciliation is future post-hoc work only:

```text
artifacts/billing/full_pipeline_gcp_factorial_v1/<run_id>/
```

Actual billing collection requires a separate approval packet naming source,
credential scope, time window, attribution keys, raw-report handling, redaction
policy, dry-run command, stop conditions, and output path. Raw billing reports
must not be committed. If Modal billing collection is rate-limited, stop and
record `O5C_BLOCKED_MODAL_BILLING_RATE_LIMIT_WITH_ADAPTER_READY`.

## Denominator And Eligibility Policy

Default denominator policy:

- use intent-to-treat over generated rows unless a metric-specific analyzer
  policy explicitly defines a different denominator;
- do not drop F0/F1 rows because feedback was inactive;
- do not treat missing feedback activation as success or failure without a
  metric-specific rule;
- preserve terminal failure categories;
- report feedback activation separately from success rates.

Eligibility:

- P eligibility is only `F1_COMPILE`;
- C eligibility is only F2 functional failure paths;
- `F1_RUNTIME` is terminal;
- direct initial-F2 and post-P F2 paths must be labeled distinctly;
- mixed repair-history policies must be grouped, quarantined, or rejected before
  headline claims.

## Stop And Spend Limits

Every future executable packet must specify:

```text
max Modal budget:
max wall-clock time:
max rows:
max generation attempts:
max repair attempts per row:
max failures before abort:
max consecutive F0_PARSE:
max consecutive infrastructure errors:
required sidecar write success:
required hash sidecar success:
required post-run analyzer validation:
```

Default stop requirements:

- stop on first Modal timeout, preemption, worker interruption, auth/config
  failure, image failure, or synthesized infrastructure failure unless a future
  packet explicitly allows continuation;
- stop on row-count mismatch;
- stop on schema validation failure;
- stop on hash sidecar mismatch;
- stop on P firing outside `F1_COMPILE`;
- stop on C firing outside F2;
- stop on `F1_RUNTIME` repair attempt;
- stop on private-eval, raw prompt/source, token ID, billing secret, or
  credential leakage;
- stop on performance/profiler/timing/speedup leakage in non-performance
  artifacts.

## Validation Plan

Future L1 approval must include:

- exact Modal command, but not in this packet;
- exact target output paths and sidecar paths;
- preflight path-existence check;
- command/config proof for `repair_history_policy=agentic_transcript_v1` on C/P
  loops where enabled;
- observability preflight for `experiment_id`, `run_id`, and sidecar path;
- protected-scope diff scan;
- authorization scan;
- post-run JSONL schema validation;
- content-hash validation;
- observability sidecar completeness validation;
- analyzer grouping/quarantine validation;
- structural/task metric metadata validation;
- MLflow post-hoc importer dry-run or fixture proof before any L2 approval.

Future L2 approval must additionally include:

- L1 audit reference;
- Gate G8 readiness proof;
- exact n=20 condition matrix;
- exact model/revision/decoding details;
- exact cost/spend boundary;
- billing reconciliation plan or explicit unavailable status;
- exact analyzer/report commands;
- exact MLflow import/indexing command;
- claim-boundary review.

## Launch Prerequisites

L1 remains blocked until a later approval packet supplies:

- approval source and timestamp;
- exact branch and commit;
- exact command;
- exact conditions to run;
- exact n;
- exact output paths;
- exact observability IDs and paths;
- exact model/revision/decoding policy;
- exact repair-history policy config;
- exact stop/spend limits;
- exact validation commands;
- target path nonexistence proof;
- statement that generated artifacts are development-only.

L2 remains blocked until:

- L1 passes;
- Gate G8 is satisfied;
- a post-hoc MLflow importer or equivalent script exists and passes a fixture or
  L1 import proof;
- analyzer/reporting can separate repair-history policies;
- structural/task metric-family metadata validates;
- observability summaries and hash sidecars are complete or explicitly accepted
  as unavailable;
- billing is reconciled or explicitly unavailable under an approved O5 policy;
- exact paper-scale command, outputs, budgets, and claim boundaries are
  approved.

## Explicit Non-Authorizations

This packet does not authorize:

- Modal execution;
- GPU work;
- generation;
- experiments;
- benchmarks;
- profilers;
- n=5, n=20, paper-scale, or broader matrix execution;
- output mutation;
- raw JSONL rewrite;
- analyzer output refresh;
- report artifact refresh;
- MLflow run creation;
- MLflow server startup;
- writes to `mlruns/`;
- billing query or credential use;
- raw billing artifact processing;
- performance, timing, speedup, profiler, Nsight, NCU, or benchmark evidence;
- result schema edits;
- code edits;
- dependency or lockfile changes;
- treating MLflow, observability, or reports as a replacement for JSONL and
  analyzer evidence.

## Classification

`FULL_PIPELINE_LAUNCH_PACKET_V1_COMPLETE` is satisfied for L0 only if the
packet, audit, handoff updates, and validation scans pass without protected
scope changes or authorization leakage.
