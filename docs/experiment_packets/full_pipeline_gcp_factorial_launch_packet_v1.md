# Full Pipeline Grammar-Mode x C x P Launch Packet v1

## Packet Identity

packet_id: `FULL_PIPELINE_GCP_FACTORIAL_LAUNCH_PACKET_V1`
packet_type: patched draft launch planning packet
branch_created_on: `codex/full-pipeline-launch-packet-v1`
patch_branch: `codex/full-pipeline-l1-smoke-dev-approval-packet`
baseline_commit: `0cc43c1 Audit full pipeline launch packet promotion`
created_at: 2026-06-05
patched_at: 2026-06-05
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

## Patch Summary

This patch supersedes the previously selected fresh 8-cell design for future
execution. The selected preregistered design is now a 12-cell
`grammar_mode x C x P` design.

The older 8-cell planning artifact remains historical context only. It must not
be used as the active future execution design, preregistration design, output
namespace, or L1/L2 condition matrix.

## Objective

Plan the first fresh post-change Cluster 3 full-pipeline run after MLflow
tracking, observability sidecars, `agentic_transcript_v1` repair memory, and
structural/task reporting changes have landed in the handoff trunk.

The packet answers four launch-design questions:

1. whether to target the superseded 8-cell plan or the selected 12-cell
   grammar-mode-expanded design;
2. whether the next executable gate should be L1a smoke/dev, L1b
   development/stability, or L2 paper-scale;
3. how MLflow should index repo artifacts post-hoc;
4. how result rows, content hashes, observability sidecars, analyzer outputs,
   report artifacts, repair-history labels, grammar-mode labels,
   metric-family metadata, and billing reconciliation should join without
   making any metadata layer authoritative.

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
- `cluster1/README.md`
- `shared/generation_metadata.py`
- `cluster3/experiments/run_cluster3_modal.py`

## Scientific Rationale

The scientifically meaningful post-change reason to rerun is
`agentic_transcript_v1`, because it changes C/P repair prompt behavior. MLflow,
observability sidecars, and structural/task metric metadata improve auditability,
provenance, report interpretation, and artifact indexing, but they do not by
themselves change the generated candidates or repair loop behavior.

The grammar-mode expansion is scientifically meaningful only if future
execution can prove that the active grammar modes are distinct, supported, and
reported as a three-level factor. It allows C/P feedback effects to be compared
within each grammar mode and prevents a binary grammar-on interpretation from
collapsing materially different grammar surfaces.

A fresh run should avoid mixing historical `last_attempt_only_v1` controls with
new `agentic_transcript_v1` treatment cells in headline paper claims. Historical
rows remain useful as baselines, diagnostics, or compatibility checks only when
the analysis explicitly models repair-history policy as a cohort/factor and
labels the caveat.

## Terminology

`grammar_mode` is the primary grammar factor for this packet.

Allowed planned values:

- `grammar_off`: no grammar-constrained decoding.
- `primary_grammar`: the current primary grammar path, if available and
  confirmed in code/config before execution.
- `task_agnostic_grammar`: the task-agnostic grammar path.

Current code-support caveat:

- Repo evidence currently records `task_agnostic` as the report-facing primary
  grammar variant and `template_upper_bound` as diagnostic/non-primary.
- `shared/generation_metadata.py` exposes `template_upper_bound` and
  `task_agnostic` grammar variants, while `cluster3/experiments/run_cluster3_modal.py`
  exposes a `grammar_variant` field rather than a first-class three-level
  `grammar_mode` selector.
- Therefore 12-cell L1a execution is blocked until the future authorization
  packet confirms whether `primary_grammar` is distinct from
  `task_agnostic_grammar`, maps each active mode to exact grammar paths and
  hashes, and proves the Cluster 3 path can label/analyze `grammar_mode` per
  row.

## Design Choice

Selected design: fresh 12-cell `grammar_mode x C x P` design.

The superseded design was a fresh 8-cell plan over grammar on/off plus C/P
feedback. That design is no longer the active future-execution plan.

## Twelve-Cell Matrix

| condition_id | grammar_mode | correctness_feedback_C | compile_feedback_P | repair_history_policy | primary comparison role |
|---|---|---:|---:|---|---|
| `grammar_off__c_off__p_off` | `grammar_off` | off | off | `not_applicable` | Baseline for no grammar and no feedback |
| `grammar_off__c_on__p_off` | `grammar_off` | on | off | `agentic_transcript_v1` when C loop is enabled | C effect without grammar and without P |
| `grammar_off__c_off__p_on` | `grammar_off` | off | on | `agentic_transcript_v1` when P loop is enabled | P effect without grammar and without C |
| `grammar_off__c_on__p_on` | `grammar_off` | on | on | `agentic_transcript_v1` when C/P loops are enabled | C/P interaction without grammar |
| `primary_grammar__c_off__p_off` | `primary_grammar` | off | off | `not_applicable` | Grammar-mode baseline for primary grammar |
| `primary_grammar__c_on__p_off` | `primary_grammar` | on | off | `agentic_transcript_v1` when C loop is enabled | C effect under primary grammar |
| `primary_grammar__c_off__p_on` | `primary_grammar` | off | on | `agentic_transcript_v1` when P loop is enabled | P effect under primary grammar |
| `primary_grammar__c_on__p_on` | `primary_grammar` | on | on | `agentic_transcript_v1` when C/P loops are enabled | C/P interaction under primary grammar |
| `task_agnostic_grammar__c_off__p_off` | `task_agnostic_grammar` | off | off | `not_applicable` | Grammar-mode baseline for task-agnostic grammar |
| `task_agnostic_grammar__c_on__p_off` | `task_agnostic_grammar` | on | off | `agentic_transcript_v1` when C loop is enabled | C effect under task-agnostic grammar |
| `task_agnostic_grammar__c_off__p_on` | `task_agnostic_grammar` | off | on | `agentic_transcript_v1` when P loop is enabled | P effect under task-agnostic grammar |
| `task_agnostic_grammar__c_on__p_on` | `task_agnostic_grammar` | on | on | `agentic_transcript_v1` when C/P loops are enabled | C/P interaction under task-agnostic grammar |

## Execution Ladder

| Level | Status | Purpose | Scope | Authorization state |
|---|---|---|---|---|
| L0 packet patch | current phase | Patch the active planning design and handoff routing | Docs only; no outputs; no MLflow runtime writes | Open in this packet; execution not authorized |
| L1a smoke/dev | future approval only | Validate command path, output namespace, row schema, sidecars, analyzer grouping, and MLflow post-hoc indexing for the 12-cell design | 12 cells, `n=1` per cell, exact command and paths required in a later signed approval | Blocked pending explicit user approval and grammar-mode support proof |
| L1b dev/stability | future approval only | Check condition-specific instability, repair-loop activation, analyzer/report stability, and sidecar stability | 12 cells, `n=5` per cell, only after L1a passes | Blocked pending L1a pass and explicit user approval |
| L2 paper-scale candidate | future approval only | Paper candidate for the selected 12-cell design | 12 cells, proposed `n=20` per cell only after L1a/L1b pass | Blocked pending L1a and L1b pass, Gate G8, exact costs/commands/paths, exact analyzer/report/MLflow commands, and explicit user approval |

L1a and L1b are not paper evidence. L2 paper-scale remains blocked until L1a
and L1b pass and a separate signed approval packet names exact commands, paths,
model revisions, budgets, stop conditions, analysis commands, reporting
commands, MLflow import commands, and cost/spend boundaries.

## Kernel And Problem Scope

Recommended L1a scope:

- kernel class: `elementwise_relu` or another explicitly named Cluster 3 smoke
  fixture selected before approval;
- problem IDs: exact stable problem IDs must be listed in the future approval
  packet;
- scale tier: smoke/dev only;
- row count: `n=1` per selected 12-cell condition.

Recommended L1b scope:

- kernel class: same as L1a unless L1b approval explicitly broadens it;
- row count: `n=5` per 12-cell condition;
- purpose: development/stability only, not paper evidence.

Recommended L2 scope:

- kernel class: start with the same class validated by L1a/L1b unless the L2
  packet explicitly broadens scope;
- proposed row count: `n=20` per 12-cell condition;
- all problem IDs, seeds, shapes, dtypes, model revisions, grammar modes,
  grammar paths/hashes, and repair budgets must be fixed before approval.

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
- exact `grammar_mode` values;
- exact grammar file/path or grammar activation config for each active grammar
  mode;
- grammar file hash or sidecar grammar hash where supported;
- proof that both active grammar modes are supported by current code;
- whether all cells use the same model/revision/decoding configuration.

No model download, tokenizer download, API call, generation call, or dependency
change is authorized by this packet.

## Repair-History Policy

`agentic_transcript_v1` must be explicitly enabled in the future command or
configuration for C/P repair loops. It is not the default.

Policy requirements:

- rows with C off and P off have no repair-loop memory activation;
- C/P cells must label `repair_history_policy` in rows/artifacts when the
  current schema supports it;
- `agentic_transcript_v1` applies only to C/P repair loops when enabled;
- P repairs only `F1_COMPILE`;
- C repairs only F2;
- `F1_RUNTIME` remains terminal;
- direct initial-F2 C paths must remain distinct from post-P F2 paths;
- if explicit `agentic_transcript_v1` validation fails, the run must fail
  closed rather than silently falling back to `last_attempt_only_v1`;
- analyzer/reporting must group or quarantine by `repair_history_policy`;
- historical `last_attempt_only_v1` outputs are baselines/diagnostics only
  unless a future packet explicitly models policy as a cohort/factor.

New `agentic_transcript_v1` artifacts must not share output paths with legacy
`last_attempt_only_v1` artifacts.

## Observability Policy

Future L1a smoke/dev recommendation:

- mode: `best_effort` unless the approval packet chooses `required`;
- `observability_experiment_id`: `full_pipeline_grammar_mode_cp_factorial_v1`;
- `observability_run_id`: explicit per execution, for example
  `full_pipeline_grammar_mode_cp_factorial_v1_l1a_<YYYYMMDD>_<shortid>`;
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
- `condition_id`;
- `grammar_mode`;
- kernel class;
- dtype;
- seed/problem ID.

Observability metadata remains sidecar-only. Scientific rows must not be
mutated solely to add token, duration, Modal, billing, cost, or
observability-only metadata unless the current schema already supports the
field and the future packet explicitly authorizes that behavior.

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
| `phase` | tag | launch packet / handoff | post-hoc | `experiment_id` | L1a, L1b, or L2 |
| `condition_id` | tag/param | JSONL rows or sidecar labels | post-hoc | condition_id + row identity | Per-row or per-child-run index policy must be fixed before L2 |
| `grammar_mode` | param/tag | launch packet / row metadata | post-hoc | grammar_mode + row identity | Three-level primary grammar factor |
| `grammar_variant` | param/tag | row metadata | post-hoc | grammar_mode + grammar path/hash | Diagnostic/mapping field, not a replacement for `grammar_mode` |
| `correctness_feedback_active` | param/tag | condition matrix / row metadata | post-hoc | condition_id | C factor |
| `compile_feedback_active` | param/tag | condition matrix / row metadata | post-hoc | condition_id | P factor |
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
| `level2_functional_success_rate` | metric | analyzer JSON | post-hoc | analyzer output + condition_id | task_functional primary only when prerequisites pass |
| `level1_compile_success_rate` | metric | analyzer JSON | post-hoc | analyzer output + condition_id | structural_code_surface secondary/diagnostic |
| `feedback_activation` | metric/artifact | analyzer diagnostics / rows | post-hoc | condition_id + policy | Mixed diagnostic |
| `level_reach_rates` | metric/artifact | analyzer diagnostics | post-hoc | condition_id | Mixed diagnostic |
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

Metric-family interpretation changes for the 12-cell design:

- structural/code-surface comparisons include `grammar_mode` as a three-level
  factor;
- task/functional comparisons include `grammar_mode` as a three-level factor;
- C/P interactions must be analyzed conditional on `grammar_mode`;
- the grammar-mode comparison must not be collapsed into a two-level active
  grammar flag for primary claims;
- a derived binary active-grammar diagnostic may be reported only as diagnostic
  if the derivation is explicit.

Primary task metrics:

- `level2_functional_success_rate`;
- repair-set success where explicit Level 2 repair-set evidence exists;
- eval-set success where explicit Level 2 eval-set evidence exists;
- `correctness_pass_at_k` only if gate-qualified and not bare pass@k.

Primary/secondary structural metrics:

- syntax validity when compatible explicit evidence exists;
- grammar validity for active grammar-mode rows;
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
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/mlflow_index/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/
```

The old `full_pipeline_gcp_factorial_v1` namespace must not be used for this
design. If any target path already exists, future launch must stop unless an
explicit resume/append/archive policy is approved before execution.

No overwrite policy:

- output JSONL names must include `grammar_mode`, C/P settings, n, dtype, kernel
  scope, and date or run_id;
- if any target path exists, stop unless an explicit resume/append/archive
  policy is approved before execution;
- raw JSONL must never be rewritten to repair metadata;
- content-hash sidecars must be generated from the final JSONL bytes;
- legacy outputs must not be reused as fresh controls for primary claims.

Example future L1a names, not authorized by this packet:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_off__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/grammar_off__c_on__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/primary_grammar__c_off__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/primary_grammar__c_on__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/primary_grammar__c_off__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/primary_grammar__c_on__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic_grammar__c_off__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic_grammar__c_on__p_off_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic_grammar__c_off__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/task_agnostic_grammar__c_on__p_on_n1_fp32_elementwise_relu_<run_id>.jsonl
```

## Sidecar Namespace Reservation

Expected sidecars:

- content-hash sidecar adjacent to each JSONL output;
- observability event sidecar;
- observability summary sidecar;
- observability hash sidecar.

Preferred L1a sidecar namespace:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/<run_id>/
```

Preferred L1b sidecar namespace:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1b_n5/<run_id>/
```

Preferred L2 sidecar namespace:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l2_n20/<run_id>/
```

If sidecars stay adjacent to output JSONL paths, the future packet must show the
exact derived event, summary, and hash paths before approval.

## Analyzer And Report Namespace Reservation

Analyzer and report artifacts should be separate from raw outputs:

```text
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/<run_id>/factorial_analysis.json
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/<run_id>/
```

The future packet must list exact analyzer and report commands. Analyzer output
refresh and report artifact refresh are not authorized here.

Analyzer grouping requirements:

- group by `grammar_mode`, not only an active-grammar boolean;
- preserve C/P factors within each `grammar_mode`;
- reject or quarantine rows missing `grammar_mode`;
- reject or quarantine rows where `grammar_mode`, grammar path, and grammar hash
  conflict;
- treat derived active-grammar summaries as diagnostic only.

## Billing Namespace Reservation

Billing reconciliation is future post-hoc work only:

```text
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/<run_id>/
```

Actual billing collection requires a separate approval packet naming source,
credential scope, time window, attribution keys, raw-report handling, redaction
policy, dry-run command, stop conditions, and output path. Raw billing reports
must not be committed. If Modal billing collection is rate-limited, stop and
record `O5C_BLOCKED_MODAL_BILLING_RATE_LIMIT_WITH_ADAPTER_READY`.

## Old-Run Comparability Policy

Previous 8-cell or 4-cell planning artifacts are superseded for future
execution. Historical runs can be used only as historical baselines or
diagnostics.

Comparability requirements:

- old `last_attempt_only_v1` rows must not be mixed with
  `agentic_transcript_v1` rows for primary claims;
- old one-grammar outputs must not be used as if they cover both active grammar
  modes;
- template or diagnostic grammar rows must not be treated as primary grammar
  rows unless a future contract explicitly changes their role;
- historical rows may appear only in labeled diagnostic/baseline sections;
- primary claims for this design require fresh rows for all 12 cells under the
  same approved repair-history, grammar-mode, model, dtype, shape, and stop
  policies.

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
- stop on missing or unsupported `grammar_mode`;
- stop on grammar-mode/path/hash mismatch;
- stop on P firing outside `F1_COMPILE`;
- stop on C firing outside F2;
- stop on `F1_RUNTIME` repair attempt;
- stop on private-eval, raw prompt/source, token ID, billing secret, or
  credential leakage;
- stop on performance/profiler/timing/speedup leakage in non-performance
  artifacts.

## Validation Plan

Future L1a approval must include:

- exact command, but not in this packet;
- exact 12-cell condition matrix;
- exact target output paths and sidecar paths;
- exact `grammar_mode` values;
- exact grammar file/path or grammar activation config for each active grammar
  mode;
- validation that both active grammar modes are supported by current code;
- per-row `grammar_mode` label;
- per-row grammar file/hash or sidecar grammar hash where supported;
- analyzer grouping by `grammar_mode`, not only an active-grammar boolean;
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

Future L1b approval must include:

- L1a audit reference;
- exact `n=5` condition matrix;
- exact instability and repair-loop activation review criteria;
- exact analyzer/report stability commands.

Future L2 approval must additionally include:

- L1a and L1b audit references;
- Gate G8 readiness proof;
- exact `n=20` condition matrix;
- exact model/revision/decoding details;
- exact cost/spend boundary;
- billing reconciliation plan or explicit unavailable status;
- exact analyzer/report commands;
- exact MLflow import/indexing command;
- claim-boundary review.

## Launch Prerequisites

L1a remains blocked until a later signed authorization packet supplies:

- approval source and timestamp;
- exact branch and commit;
- exact command;
- exact 12 conditions to run;
- exact n;
- exact output paths;
- exact observability IDs and paths;
- exact model/revision/decoding policy;
- exact `grammar_mode` mapping;
- exact grammar file/path or activation config for `primary_grammar`;
- exact grammar file/path or activation config for `task_agnostic_grammar`;
- proof that both active grammar modes are supported and distinct or an
  explicit approved decision that they are intentionally aliased;
- exact repair-history policy config;
- exact stop/spend limits;
- exact validation commands;
- target path nonexistence proof;
- statement that generated artifacts are development-only.

L1b remains blocked until:

- L1a passes;
- L1a artifact/audit references are recorded;
- instability and repair-loop activation review criteria are accepted;
- a separate L1b approval packet is signed.

L2 remains blocked until:

- L1a and L1b pass;
- Gate G8 is satisfied;
- a post-hoc MLflow importer or equivalent script exists and passes a fixture or
  L1 import proof;
- analyzer/reporting can separate repair-history policies and `grammar_mode`;
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
- L1a, L1b, L2, n=1, n=5, n=20, paper-scale, or broader matrix execution;
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

`FULL_PIPELINE_LAUNCH_PACKET_12CELL_PATCH_BLOCKED_CODE_SUPPORT_AMBIGUITY` is
the current classification for L0 planning: the selected design has been patched
to the 12-cell `grammar_mode x C x P` design, but L1a execution remains blocked
until a future authorization packet confirms the distinct active grammar-mode
mapping and proves row/analyzer support.
