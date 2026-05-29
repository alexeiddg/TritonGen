# MLflow Experiment Harness Plan

## Purpose

Define a future MLflow harness for TritonGen paper-grade reruns across Cluster
1, Cluster 2, and Cluster 3, especially when running larger models and more
expensive Modal jobs.

This is a planning document only. It does not authorize a paper-scale run, does
not reinterpret existing artifacts, and does not replace the existing JSONL
result contracts, sidecars, Modal provenance, metric registry plan, or analyzer
logic.

## Recommendation

Use MLflow, but use it as a harness around the existing experiment system, not
as the source of scientific truth.

Recommended architecture:

```text
Modal executes GPU work
repo evaluators decide truth
JSONL rows and sidecars remain source of record
repo analyzers compute paper metrics
MLflow indexes runs, artifacts, reports, traces, and comparisons
```

This is worth the investment because future work plans include:

- larger models with higher Modal cost;
- paper-grade reruns for all three clusters;
- future 2^3 G/C/P factorial comparisons;
- more need to compare runs across model size, prompt version, grammar version,
  repair policy, GPU route, and evaluator code;
- a higher burden to explain why a metric exists at one cluster level but not
  another.

The first implementation should be a post-hoc importer/report harness. Live
MLflow tracing inside Modal containers should come later, after the sidecar
schema and metric registry are stable.

## Why MLflow Fits This Project

MLflow is useful here because TritonGen has a multi-stage experiment lifecycle
rather than a single model-training run. The useful MLflow capabilities are:

- experiment and run tracking for comparing paper-grade reruns;
- artifact logging for JSONL outputs, sidecars, analyzer outputs, generated
  reports, figures, and Modal billing exports;
- tags and params for model revisions, grammar hashes, git SHAs, GPU routes,
  scale tiers, and cluster/condition identity;
- parent/child runs for grouping campaigns, clusters, conditions, and model
  variants;
- GenAI tracing for future per-candidate generation, compile, correctness,
  repair, and benchmark spans;
- custom GenAI scorers for deterministic report gates and evaluator audits;
- evaluation datasets for stable golden sets once a SQL-backed MLflow server is
  in place;
- prompt registry for future prompt-version governance when prompt variants
  become first-class experiment variables.

MLflow is not useful as the place to decide whether a generated Triton kernel
is correct. The correctness contract belongs to the repo evaluator. MLflow
should only record and present those decisions.

## Non-Goals And Guardrails

- Do not write timing, token, GPU, cost, or speedup fields into existing result
  rows when the row schema forbids them.
- Do not use MLflow metric names that hide gates. `pass_at_5` is invalid as a
  standalone paper metric unless it is explicitly Level 2 correctness. Prefer
  `compile_pass_at_5`, `correctness_pass_at_5`, and
  `benchmarkable_pass_at_5`.
- Do not let an MLflow outage fail a Modal paper run. The run should continue
  writing durable JSONL rows even if MLflow is unavailable.
- Do not log secrets, API tokens, local credential paths, or raw account
  billing identifiers.
- Do not treat Modal GPU utilization as kernel speedup evidence. Use evaluator
  timing for Level 4 metrics and keep GPU utilization as operational metadata.
- Do not switch Modal `.remote()` calls to `.spawn()` only to collect telemetry
  in the first phase.
- Do not cite this agentic plan in the paper. Promote sanitized decisions into
  `docs/` or `.contracts/research/` when they become methodology.

## Current Repo Constraints

The existing observability plan already requires cost, estimated compute cost,
token counts, wall-clock durations, and performance metrics only where the
evaluation contract permits them.

Relevant local facts:

- The repo currently has no MLflow dependency in `pyproject.toml` or
  `requirements.txt`.
- The shared Modal app is `tritongen-gpu-harness` and currently has no tags.
- Cluster 1 Modal runner is compile-only. It records compile errors as result
  fields and explicitly does not perform correctness, repair, timing, or
  profiling logic.
- Cluster 2 result rows intentionally forbid timing, token, throughput,
  speedup, and profiler fields in primary result payloads.
- Cluster 3 currently has a local orchestration runner that uses Modal-backed
  generation/correctness adapters but does not define a separate Cluster 3
  Modal app.
- Current authoritative artifacts remain JSONL files and analyzer JSON under
  the artifact registry.

These constraints point to a sidecar-first MLflow integration.

## Source Research Notes

Researched on 2026-05-27.

MLflow:

- MLflow Tracking stores run metadata such as run IDs, start/end times,
  params, metrics, and tags in a backend store; artifacts are stored separately
  in an artifact store.
- The MLflow Tracking Server hosts REST APIs and the UI. A local file-backed
  setup is fine for small solo development, but database-backed metadata is
  better for larger volumes of runs, traces, and paper-grade audit history.
- `mlflow server` supports `--backend-store-uri`,
  `--default-artifact-root`, `--serve-artifacts`, `--host`, and `--port`.
- MLflow GenAI evaluation uses `mlflow.genai.evaluate()` and `Scorer` objects.
  It is separate from classic `mlflow.models.evaluate()`.
- MLflow GenAI custom scorers can inspect inputs, outputs, expectations, and
  traces. Built-in LLM judges are not the right source of truth for Triton
  correctness, but custom deterministic scorers are useful for report audits.
- MLflow manual tracing supports `@mlflow.trace`, `mlflow.start_span()`,
  span inputs/outputs, span attributes, trace tags, and automatic exception
  capture.
- `mlflow.search_traces()` can retrieve traces as DataFrames or trace objects;
  large searches should use client pagination.
- MLflow Evaluation Datasets require a SQL-backed MLflow Tracking Server and
  can be created from traces, dictionaries, or DataFrames.
- MLflow Prompt Registry supports versioned prompts, tags, aliases, and model
  configuration. This is useful later for prompt governance but should not be
  first.
- MLflow REST APIs can create/list/get experiments and runs and log params,
  metrics, tags, and artifacts when direct Python SDK use is not convenient.

Modal:

- Modal billing reports are available through `modal.billing` and the
  `modal billing` CLI. Reports are post-hoc, interval based, and can include
  app tags. Costs are pre-credit/pre-reservation.
- Modal App tags can be set in the App constructor or with `App.set_tags`, and
  billing reports can include those tags.
- Modal `FunctionCall` objects are created with `.spawn()`, can be polled with
  `.get()`, and can expose call graphs. Current repo use of `.remote()` should
  stay unchanged for the first phase.
- Modal runtime environment variables include `MODAL_CLOUD_PROVIDER`,
  `MODAL_IMAGE_ID`, `MODAL_REGION`, `MODAL_TASK_ID`, `MODAL_ENVIRONMENT`, and
  `MODAL_IS_REMOTE`.
- Modal OpenTelemetry integration can export audit logs, function logs,
  container metrics, and platform metrics such as CPU utilization, memory,
  GPU memory, GPU compute utilization, running containers, and input event
  timing.
- Modal GPU metrics are health/utilization correlates and are not direct kernel
  performance diagnostics.

Primary source URLs:

- MLflow GenAI overview: https://mlflow.org/docs/latest/genai/
- MLflow Tracking: https://mlflow.org/docs/latest/ml/tracking/
- MLflow tracking API and nested runs:
  https://mlflow.org/docs/latest/ml/tracking/tracking-api/
- MLflow server CLI:
  https://mlflow.org/docs/latest/api_reference/cli.html
- MLflow architecture:
  https://mlflow.org/docs/latest/self-hosting/architecture/overview/
- MLflow artifact store:
  https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/
- MLflow GenAI evaluation:
  https://mlflow.org/docs/latest/genai/eval-monitor/
- MLflow GenAI API:
  https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html
- MLflow manual tracing:
  https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/
- MLflow search traces:
  https://mlflow.org/docs/latest/genai/tracing/search-traces/
- MLflow evaluation datasets:
  https://mlflow.org/docs/latest/genai/datasets/
- MLflow prompt registry:
  https://mlflow.org/docs/latest/genai/prompt-registry/
- MLflow REST API:
  https://mlflow.org/docs/latest/api_reference/rest-api.html
- Modal billing:
  https://modal.com/docs/guide/billing
- Modal billing API:
  https://modal.com/docs/reference/modal.billing
- Modal App tags:
  https://modal.com/docs/reference/modal.App
- Modal FunctionCall:
  https://modal.com/docs/reference/modal.FunctionCall
- Modal job queue and `.spawn()`:
  https://modal.com/docs/guide/job-queue
- Modal runtime environment variables:
  https://modal.com/docs/guide/environment_variables
- Modal GPU metrics:
  https://modal.com/docs/guide/gpu-metrics
- Modal OpenTelemetry integration:
  https://modal.com/docs/guide/otel-integration

## Recommended MLflow Storage Setup

### Development Setup

Use a local SQL-backed MLflow server, not the default `./mlruns` file store.
SQLite is enough for local development and supports Evaluation Datasets.

Example future command:

```bash
mlflow server \
  --backend-store-uri sqlite:///outputs/mlflow/mlflow.db \
  --default-artifact-root file:/Users/alexeidelgado/Desktop/TritonGen/outputs/mlflow/artifacts \
  --host 127.0.0.1 \
  --port 5000
```

Recommended local environment:

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export TRITONGEN_MLFLOW_EXPERIMENT=tritongen-local
```

### Paper-Grade Setup

Use a shared or persistent tracking server before expensive reruns.

Minimum paper-grade properties:

- database-backed backend store, preferably PostgreSQL for long-lived shared
  use, SQLite only for local single-user runs;
- artifact root on durable storage;
- backups before schema upgrades;
- access restricted by network, auth, or managed service controls;
- explicit `MLFLOW_TRACKING_URI`;
- no secrets in params, tags, trace metadata, or artifact filenames;
- server reachable from local orchestration, and reachable from Modal only if
  live remote tracing is enabled.

For the first paper-grade MLflow use, do not require Modal containers to write
to MLflow. Let local post-hoc import run after JSONL artifacts are complete.

## Experiment And Run Structure

Use one MLflow experiment per research campaign, not one per cluster.

Suggested experiment names:

```text
tritongen-paper-reruns
tritongen-observability-smoke
tritongen-model-scaling
```

Use parent/child runs:

```text
parent run: campaign or paper-grade rerun batch
  child run: cluster1
    child run: cluster1/none/model_variant
    child run: cluster1/G/model_variant
  child run: cluster2
    child run: cluster2/none/replay
    child run: cluster2/G/replay
    child run: cluster2/C/model_variant
    child run: cluster2/G+C/model_variant
  child run: cluster3
    child run: cluster3/P/model_variant
    child run: cluster3/G+P/model_variant
    child run: cluster3/C+P/model_variant
    child run: cluster3/G+C+P/model_variant
```

Do not create one MLflow run per row in the first phase. That will create too
many runs and make the UI noisy. Per-row detail belongs in JSONL artifacts,
sidecars, and optional traces.

## Required Run Tags

Every MLflow run created by the harness should include these tags when known:

```text
project = tritongen
harness_kind = post_hoc_import | local_orchestrator | modal_live_trace
cluster = cluster1 | cluster2 | cluster3 | experiment_wide
condition = none | G | C | G+C | P | G+P | C+P | G+C+P | mixed
scale_tier = smoke | development | paper
paper_grade_candidate = true | false
reportability = reportable | caveated | diagnostic_only | smoke_only
git_sha = <repo commit>
artifact_registry_status = registered | unregistered | candidate
source_of_truth = jsonl_sidecar
mlflow_role = index_and_report
```

Every campaign parent run should include:

```text
campaign_id
analysis_label
analysis_scope = 2x2 | 2x3 | partial | diagnostic
comparison_budget_mode = sample_matched | token_budget_matched | wall_clock_budget_matched | cost_budget_matched
metric_registry_sha256
```

## Required Run Params

Log stable configuration as params, not metrics:

```text
model_id
model_revision
tokenizer_revision
max_new_tokens
temperature
grammar_variant
grammar_sha
repair_budget
p_repair_budget
c_repair_budget
modal_generation_gpu
modal_eval_gpu
kernel_classes
dtypes
n_per_cell
runner
runner_version_or_git_sha
```

Avoid high-cardinality row identifiers as MLflow params. Put row-level data in
artifacts or traces.

## Required Artifacts

Every imported paper-grade run should log these artifacts when available:

```text
artifacts/raw/<cluster_or_condition>.jsonl
artifacts/sidecars/*.json
artifacts/sidecars/*.jsonl
artifacts/analyzer/*.json
artifacts/reports/*.md
artifacts/reports/*.html
artifacts/tables/*.csv
artifacts/tables/*.json
artifacts/figures/*.png
artifacts/registry/metric_registry.json
artifacts/registry/artifact_manifest.json
artifacts/provenance/run_config.json
artifacts/provenance/git_status_summary.txt
artifacts/provenance/modal_billing_report.json
artifacts/provenance/modal_billing_report.csv
artifacts/provenance/modal_runtime_summary.json
```

For large artifacts, log summaries and stable pointers if the artifact store is
not durable enough.

## Identity, Idempotency, And Import Lineage

The MLflow harness must be idempotent. Re-running the importer over the same
artifact set should not silently create duplicate paper-candidate runs.

Define a deterministic import identity:

```text
campaign_id
artifact_set_sha256
analysis_output_sha256
metric_registry_sha256
git_sha
importer_version
```

Recommended behavior:

- compute `artifact_set_sha256` over the manifest of imported JSONL, sidecar,
  analyzer, report, and billing files;
- search MLflow for an existing run with the same `campaign_id` and
  `artifact_set_sha256` before creating a new parent run;
- if the exact import already exists, either no-op or create an explicit
  `import_attempt` child run, never a second indistinguishable parent;
- log `mlflow_import_manifest.json` as an artifact on every import;
- write a local sidecar mapping TritonGen campaign IDs and artifact hashes to
  MLflow run IDs;
- never mutate a reportable run's metrics after promotion except to add
  clearly versioned post-hoc artifacts such as delayed billing reports.

Suggested import manifest fields:

```text
campaign_id
import_started_at_utc
import_finished_at_utc
mlflow_experiment_id
mlflow_parent_run_id
source_artifacts
source_artifact_sha256
analyzer_sha256
metric_registry_sha256
billing_report_sha256
importer_git_sha
importer_version
import_status
```

## Run Lifecycle Status

MLflow tags should make run trust state obvious. Use a lifecycle tag rather
than relying on run names or freeform notes.

Recommended lifecycle values:

```text
planned
running
completed_unvalidated
failed_partial
validated
imported
reportable
superseded
retracted
diagnostic_only
```

Rules:

- a live run can be `running`, `completed_unvalidated`, or `failed_partial`;
- a post-hoc import can become `imported` only after artifact hashes and row
  counts pass;
- a parent run can become `reportable` only after repo analyzers, metric
  registry checks, and caveat checks pass;
- `superseded` means a newer run replaces the run for current reporting but
  the old run remains historical evidence;
- `retracted` means the run must not be used for any paper claim.

## Metric Naming Policy

Use MLflow-safe metric keys with explicit gates.

Allowed examples:

```text
syntax_valid_rate
grammar_rejection_rate
compile_success_rate
functional_correctness_rate
compile_pass_at_1
compile_pass_at_5
compile_pass_at_10
correctness_pass_at_1
correctness_pass_at_5
correctness_pass_at_10
benchmarkable_pass_at_1
benchmarkable_pass_at_5
benchmarkable_pass_at_10
median_kernel_time_ms
kernel_time_iqr_ms
speedup_vs_eager_median
fast_at_0_0
fast_at_1_0
fast_at_1_2
spurious_speedup_rate
cost_per_correct_kernel_usd
estimated_cost_per_correct_kernel_usd
wall_clock_per_correct_kernel_s
tokens_per_correct_kernel
repair_success_rate
attempts_to_compile_mean
attempts_to_correct_mean
timeout_rate
oom_rate
```

Forbidden examples for new MLflow paper metrics:

```text
pass_at_5
speedup
cost
latency
success
score
```

If a human-readable paper table wants `pass@5`, store that label in the metric
registry as `display_name`, not as the only MLflow metric key.

## Metric Registry Requirements

Before MLflow logs any paper-facing aggregate metric, the metric must have a
registry entry with:

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
mlflow_metric_key
paper_table_eligible
```

Recommended enum values:

```text
metric_gate:
  syntax_valid
  compile_success
  functional_success
  benchmarkable
  speedup_threshold
  cost_attribution
  diagnostic

level_gate:
  level0
  level1
  level2
  level3
  level4
  experiment_wide
  not_applicable

denominator_unit:
  row_sample
  task_cell
  repair_attempt
  terminal_candidate
  paired_replay_cell
  condition_run

attempt_policy:
  initial_only
  terminal_only
  within_n
  best_of_k
  all_attempts

reportability:
  paper_primary
  paper_secondary
  diagnostic_only
  smoke_only
  not_reportable
```

The MLflow harness must reject, or mark diagnostic-only, any metric whose
registry entry is missing or incompatible with the run scope.

## Metric Scope Decisions

Use this map when explaining where each metric is evaluated and why.

```text
Metric family                         MLflow scope
syntax_valid_rate                     Cluster 1 child runs and experiment-wide parent run
grammar_rejection_rate                Cluster 1 child runs and experiment-wide parent run
compile_success_rate                  Cluster 1, Cluster 3 P, and experiment-wide
functional_correctness_rate           Cluster 2, Cluster 3 terminal rows, and experiment-wide
compile_pass_at_k                     Cluster 1 and experiment-wide when compile rows are joined
correctness_pass_at_k                 Cluster 2/3 or experiment-wide after Level 2 evaluation exists
benchmarkable_pass_at_k               Experiment-wide Level 4 only
median_kernel_time_ms                 Experiment-wide Level 4 only
speedup_vs_eager                      Experiment-wide Level 4 only
fast_at_p                             Experiment-wide Level 4 only
spurious_speedup_rate                 Experiment-wide Level 4 audit
cost_per_success                      Experiment-wide, plus condition child runs
tokens_per_success                    Experiment-wide, with cluster-stage breakdown
wall_clock_per_success                Experiment-wide, with cluster-stage breakdown
attempts_to_compile                   Cluster 3 P and experiment-wide
attempts_to_correct                   Cluster 2 C, Cluster 3 C loop, and experiment-wide
repair_success_rate                   Cluster 2, Cluster 3, and experiment-wide
failure_distribution                  Cluster-isolated and experiment-wide
constrained_decoding_overhead         Cluster 1 generation and experiment-wide
diversity_or_duplicate_rate           Cluster-isolated and experiment-wide
end_to_end_yield_funnel               Experiment-wide only
statistical_ci_and_lift               Experiment-wide and cluster diagnostics
```

The explanation for current `pass@k` is:

```text
Current pass@k exists mainly in Cluster 1 and is compile-gated. It answers:
"Did at least one of k generated candidates compile under the Cluster 1
contract?"

It does not answer:
"Did at least one of k generated candidates pass numerical correctness?"

Therefore the MLflow harness must log it as compile_pass_at_k until Level 2
correctness rows are available.
```

## Trace Model For Future Live Runs

Live tracing should use one trace per candidate cell or terminal candidate, not
one trace per entire campaign.

Recommended trace tags:

```text
project
campaign_id
tritongen_run_id
cluster
condition
source_class
generation_mode
kernel_class
kernel_name
dtype
base_seed
sample_index
attempt_index
model_id
model_revision
tokenizer_revision
grammar_variant
grammar_sha
modal_app_name
modal_function_name
modal_function_call_id
modal_input_id
modal_image_id
modal_region
modal_cloud_provider
```

Recommended spans:

```text
candidate
  build_prompt
  generation
  level0_parse_or_syntax
  level1_compile
  level2_correctness
  c_repair_attempt_1
  c_repair_attempt_2
  p_repair_attempt_1
  p_repair_attempt_2
  level4_benchmark
  row_write
```

Span attributes should include hashes and compact metadata by default. Full
source, full prompts, and full compiler logs should be controlled by an
explicit artifact/privacy policy.

Suggested span output policy:

```text
source_hash: ok
prompt_hash: ok
trace_summary: ok
failure_code: ok
public_failure_summary: ok
full_source: artifact only if already allowed by row contract
full_private_compile_log: avoid by default
full_prompt: avoid unless prompt is already report-safe
```

## Security, Redaction, And Access Control

MLflow can make artifacts and traces easier to browse, which also makes
accidental leakage easier. Treat all logged metadata as potentially visible to
future collaborators.

Do not log:

```text
Modal tokens
Hugging Face tokens
MLflow auth tokens
local credential paths
MODAL_IDENTITY_TOKEN
raw billing account identifiers
private environment dumps
full private compiler logs by default
full prompts by default
full generated source by default when source-free row contracts apply
```

Safe defaults:

- log hashes and compact public summaries first;
- log full source only as an explicit artifact policy decision;
- redact environment captures to an allowlist;
- store billing reports with account identifiers stripped or hashed;
- keep MLflow server access local or authenticated for paper-grade artifacts;
- log a `redaction_policy_version` tag on every imported parent run.

Recommended allowlisted runtime fields:

```text
python_version
platform
git_sha
mlflow_version
modal_version
torch_version
triton_version
transformers_version
tokenizers_version
xgrammar_version
cuda_version
modal_image_id
modal_region
modal_cloud_provider
modal_environment
```

## Storage, Retention, And Backups

Paper-grade MLflow data becomes audit evidence. Treat the MLflow backend and
artifact root as part of the experiment record once reportable runs are logged.

Required storage decisions before paper-grade use:

- backend store type: SQLite for local single-user runs, PostgreSQL for durable
  shared runs;
- artifact store location and durability;
- backup location and cadence;
- trace retention policy;
- artifact retention policy;
- MLflow version pin and upgrade policy.

Before paper-grade imports:

- back up the MLflow database;
- back up or snapshot the artifact root;
- record the MLflow package version and server command;
- record the schema migration status if using a database backend;
- test restore on a small local copy at least once before relying on the
  server for final paper evidence.

Do not depend on MLflow as the only copy of raw outputs. The repo's output
artifacts and registry remain the recovery path.

## Data Volume And Cardinality Policy

Large model reruns can produce many rows, attempts, traces, and artifacts.
Unbounded MLflow logging can make the UI slow and the backend noisy.

Policy:

- no one-run-per-row in the MVP;
- no high-cardinality row IDs as MLflow params;
- use artifacts for row-level tables;
- use traces for selected candidate/stage debugging or future live runs;
- for full live tracing, prefer one trace per terminal candidate or sampled
  failure class, not every internal helper call;
- store large tables as JSONL/CSV/Parquet artifacts and log aggregate metrics
  only;
- include `row_count`, `trace_count`, `artifact_count`, and
  `artifact_total_bytes` in the import summary.

Recommended trace sampling modes:

```text
all_smoke
all_failures
all_paper
failures_plus_sampled_successes
sampled_only
off
```

Default:

```text
smoke: all_smoke
paper live remote: failures_plus_sampled_successes
post_hoc import: off unless traces already exist
```

## Promotion, Freeze, And Signoff

MLflow makes it easy to browse and compare runs, but paper-facing promotion
still needs an explicit governance step.

Promotion rule:

```text
An MLflow run is not paper-facing until it has:
1. registered source artifacts;
2. validated row counts and hash sidecars;
3. passing metric registry checks;
4. passing reportability/audit scorers;
5. generated report artifacts;
6. recorded caveats;
7. reviewer/signoff metadata.
```

Required promotion tags:

```text
promotion_status = candidate | approved | rejected | superseded | retracted
promotion_reviewer
promotion_reviewed_at_utc
promotion_basis_artifact_sha256
paper_snapshot_id
paper_snapshot_status = draft | frozen | amended
```

When a result becomes paper-facing, create a frozen evidence bundle:

```text
paper_snapshot/
  artifact_manifest.json
  metric_registry.json
  analyzer_output.json
  reports/
  caveats.md
  mlflow_run_mapping.json
  checksums.sha256
```

Do not rely on MLflow UI state alone for paper evidence. The frozen snapshot
should be reproducible from repo artifacts and import manifests.

## Concurrency And Locking

Imports and long runs may overlap once larger campaigns start. The MLflow
harness should avoid race conditions and duplicate promotion.

Rules:

- acquire a local or backend lock for each `campaign_id` during post-hoc import;
- reject concurrent imports that target the same `campaign_id` and output path;
- write import manifests atomically;
- never promote a run while an import is incomplete;
- if multiple agents run imports, require them to use distinct campaign IDs or
  an explicit reimport mode.

Suggested lock identity:

```text
campaign_id
artifact_set_sha256
mlflow_experiment_name
importer_version
```

## Harness Schema And Compatibility

The MLflow harness should version its own metadata separately from experiment
row schemas.

Recommended versions:

```text
mlflow_harness_schema_version
mlflow_import_manifest_schema_version
mlflow_metric_registry_schema_version
mlflow_trace_schema_version
mlflow_report_bundle_schema_version
```

Compatibility rules:

- importer rejects unknown future major versions;
- importer accepts older minor versions only through explicit migration code;
- reportable imports must log the harness schema versions;
- migration scripts must preserve old import manifests;
- any change to metric gates or denominator semantics requires a new metric
  registry version.

## Failure Recovery And Resume

MLflow integration should handle interruptions without losing the underlying
experiment.

Recovery policy:

- Modal/JSONL run recovery remains owned by existing durable row writers;
- post-hoc import can resume from an import manifest;
- partial MLflow imports must be tagged `import_status=partial`;
- reimport must either complete the same parent run or create an explicit
  `reimport_attempt` child run;
- failed live trace writes should be counted in a sidecar, not retried
  indefinitely inside Modal containers;
- importer should emit a human-readable recovery report when it detects partial
  previous state.

Useful recovery metrics:

```text
mlflow_import_attempt_count
mlflow_import_failed_artifact_count
mlflow_trace_write_failure_count
mlflow_recovered_partial_import_count
```

## Model License And Weight-Cache Provenance

Larger-model experiments add non-metric constraints. Before paper-grade
campaigns, record model access and license provenance without storing secrets.

Recommended fields:

```text
model_license_name
model_license_url
model_usage_restriction_summary
weights_source
weights_revision
weights_cache_policy
weights_cache_hit = true | false | unknown
weights_cache_volume
weights_download_wall_clock_s
model_load_wall_clock_s
model_memory_footprint_gb
```

The purpose is not legal analysis. The purpose is to avoid future confusion
about whether a result depended on a particular model license, private model
access grant, cache state, or slow first-load path.

## Modal Integration Strategy

### Phase 1: No Live Modal MLflow Dependency

Post-hoc import only:

- Modal runners continue to write JSONL and sidecars exactly as before.
- After the run completes, local code imports artifacts into MLflow.
- Modal billing report is fetched after a delay and logged as an artifact.
- MLflow is not required for the Modal run to succeed.

This is the safest first paper-grade path.

### Phase 2: Local Orchestrator Spans

Trace around local orchestration calls:

- start a campaign run before invoking Modal runners;
- record local wall-clock stage durations;
- log row counts and output paths;
- keep spans outside remote containers.

This gives useful timing without adding MLflow network dependencies to Modal
containers.

### Phase 3: Live Remote Spans

Only after the sidecar/importer path is stable:

- add optional MLflow dependency to Modal image;
- configure `MLFLOW_TRACKING_URI` and any auth through Modal secrets;
- set tracing to best-effort mode;
- catch and quarantine MLflow write failures;
- include Modal runtime variables and `current_modal_ids()` values in span
  attributes;
- keep JSONL durability independent.

This is useful for debugging large-model failures, but it is not required for
paper-grade report generation.

### Phase 4: Modal App Tags And Billing Join

Add App tags or run discipline for cost attribution:

```text
project=tritongen
campaign_id=<campaign>
scale_tier=paper
cluster=<cluster or mixed>
model_family=<model family>
```

Caveat: Modal App tags apply at app/report interval level. They are useful for
attribution but not exact row-level cost unless runs are isolated by time and
app tag.

Import Modal billing with:

```text
modal.billing.workspace_billing_report(
    start=<utc run start>,
    end=<utc run end plus buffer>,
    resolution="h",
    tag_names=["*"],
)
```

Then log:

```text
actual_modal_cost_usd_by_condition
actual_modal_cost_usd_by_cluster
estimated_compute_cost_usd_by_condition
cost_reconciliation_status
billing_report_lag_minutes
```

Keep actual Modal cost and estimated compute cost separate.

### Cost Guardrails And Stop Conditions

Before expensive Modal campaigns, the MLflow harness should record planned cost
and budget controls. This is especially important for larger models.

Pre-run budget fields:

```text
estimated_generation_cost_usd
estimated_eval_cost_usd
estimated_total_cost_usd
max_allowed_cost_usd
max_wall_clock_hours
max_rows
max_failures_before_abort
budget_owner
cost_estimate_method
cost_estimate_inputs_sha256
```

Runtime status fields:

```text
rows_completed
rows_expected
estimated_cost_so_far_usd
wall_clock_so_far_s
abort_reason
budget_status = within_budget | warning | exceeded | unknown
```

Stop conditions should be enforced by the runner or orchestration layer, not by
MLflow. MLflow records the planned limits and observed outcome.

### Phase 5: Optional OpenTelemetry

Modal OpenTelemetry integration can export platform metrics and logs to an
OTel provider. Treat this as operational observability, not paper evidence.

Use OTel for:

- container health;
- GPU utilization and memory;
- cold start and queue timing;
- input event success counts;
- app/function-level dashboards.

Do not use OTel GPU utilization as Level 4 performance evidence.

## API Surface To Harness

### MLflow Tracking

Use for run organization, params, metrics, tags, and artifacts:

```python
import mlflow

mlflow.set_tracking_uri(...)
mlflow.set_experiment("tritongen-paper-reruns")

with mlflow.start_run(run_name="paper_rerun_2026_...", tags={...}) as parent:
    mlflow.log_params({...})
    mlflow.set_tags({...})
    mlflow.log_metric("functional_correctness_rate", 0.0)
    mlflow.log_artifacts("outputs/analysis", artifact_path="analyzer")

    with mlflow.start_run(run_name="cluster2_G+C", nested=True):
        mlflow.log_params({...})
        mlflow.log_metric("correctness_pass_at_1", 0.0)
```

Important APIs:

```text
mlflow.set_tracking_uri
mlflow.set_experiment
mlflow.create_experiment
mlflow.start_run(nested=True)
mlflow.log_param
mlflow.log_params
mlflow.log_metric
mlflow.log_metrics
mlflow.log_dict
mlflow.log_text
mlflow.log_artifact
mlflow.log_artifacts
mlflow.set_tag
mlflow.set_tags
mlflow.search_runs
mlflow.get_artifact_uri
```

### MLflow Tracing

Use for future candidate/stage traces:

```python
import mlflow

with mlflow.start_span(name="level2_correctness") as span:
    span.set_inputs({"source_hash": source_hash, "dtype": dtype})
    result = run_correctness(...)
    span.set_outputs({"functional_success": result.functional_success})
    span.set_attributes({
        "failure_code": result.failure_code,
        "modal_function_call_id": call_id,
    })
```

Important APIs:

```text
mlflow.trace
mlflow.start_span
mlflow.get_current_active_span
mlflow.update_current_trace
mlflow.search_traces
mlflow.tracing.context
mlflow.tracing.get_tracing_context_headers_for_http_request
mlflow.tracing.disable
mlflow.tracing.enable
```

### MLflow GenAI Evaluation

Use for deterministic report and trace audits, not for Triton numerical
correctness itself:

```python
from mlflow.genai.scorers import scorer
import mlflow

@scorer
def reportability_gate(inputs, outputs, expectations, trace=None):
    return bool(outputs["metadata"]["reportable"])

result = mlflow.genai.evaluate(
    data=rows_or_trace_dataframe,
    scorers=[reportability_gate],
)
```

Useful deterministic scorers for TritonGen:

```text
metric_registry_present
no_bare_pass_at_k
no_speedup_for_incorrect_rows
paper_scale_row_count_valid
hash_sidecar_present
modal_provenance_present
failure_code_terminal_bucket_valid
cluster1_has_no_level2_claim
cluster2_has_no_forbidden_timing_fields
cluster3_p_metrics_have_p_gate
```

### MLflow Evaluation Datasets

Use after SQL-backed tracking is running:

```text
dataset: tritongen_kernelbench_locked_cells
records: kernel_class, kernel_name, dtype, base_seed, prompt_hash,
         expectations, source artifact pointer
```

Good uses:

- golden smoke suite for harness changes;
- locked paper-grade cell list;
- larger-model comparison suite;
- regression set for prompts and repair policies.

Avoid making MLflow datasets the only record of the paper experiment. The repo
manifest and JSONL outputs should remain authoritative.

### MLflow Prompt Registry

Adopt only when prompt variants become a real experimental factor.

Recommended prompt registry entries:

```text
tritongen_cluster1_generation_prompt
tritongen_cluster2_c_repair_prompt
tritongen_cluster3_p_compile_repair_prompt
tritongen_cluster3_dispatch_prompt
```

Store:

```text
prompt template
prompt version
prompt hash
model_config
temperature
max_new_tokens
grammar_variant compatibility
cluster owner
experimental status
```

Do not replace existing prompt hashes. MLflow prompt versions should point back
to repo prompt hashes and git SHAs.

### Modal APIs

Use in the MLflow harness:

```text
modal.current_function_call_id
modal.current_input_id
modal.App(tags=...)
modal.App.set_tags
modal.billing.workspace_billing_report
modal.Function.spawn
modal.FunctionCall.get
modal.FunctionCall.get_call_graph
```

First implementation should only use billing and existing runtime IDs, not
`.spawn()` orchestration changes.

## Post-Hoc Importer Design

Create a future command such as:

```bash
python -m shared.mlflow_harness.import_experiment \
  --experiment-name tritongen-paper-reruns \
  --campaign-id paper_rerun_c1_c2_c3_<date> \
  --artifact-manifest docs/05_artifacts_and_results_registry.md \
  --analysis outputs/analysis/<analysis>.json \
  --metric-registry outputs/analysis/<metric_registry>.json \
  --output-root outputs/
```

Responsibilities:

1. Validate artifacts exist.
2. Validate hash sidecars.
3. Load analyzer output.
4. Load metric registry.
5. Reject incompatible metrics.
6. Create MLflow parent run.
7. Create nested cluster/condition runs.
8. Log params, tags, metrics, and artifacts.
9. Emit an import summary artifact.
10. Exit nonzero if paper-facing gates fail.

The importer should not recompute scientific metrics unless it calls the same
repo analyzer functions used for paper tables.

## Future Live Harness Design

Only after the post-hoc importer is stable, add an optional wrapper around
runner dependencies:

```text
shared/mlflow_harness/
  __init__.py
  config.py
  importer.py
  metric_registry.py
  modal_billing.py
  tracing.py
  artifacts.py
  report.py
```

Proposed behavior:

- disabled by default;
- enabled by CLI flag or environment variable;
- never required for JSONL row writes;
- writes only sidecars or MLflow events;
- tests use a local SQLite backend or monkeypatched MLflow client.

Potential feature flags:

```text
TRITONGEN_MLFLOW_ENABLE=0|1
TRITONGEN_MLFLOW_MODE=post_hoc|local_trace|remote_trace
TRITONGEN_MLFLOW_EXPERIMENT=...
TRITONGEN_MLFLOW_CAMPAIGN_ID=...
TRITONGEN_MLFLOW_TRACKING_URI=...
TRITONGEN_MLFLOW_LOG_FULL_SOURCE=0|1
TRITONGEN_MLFLOW_FAIL_CLOSED=0|1
TRITONGEN_MLFLOW_TRACE_SAMPLING=off|all_smoke|all_failures|all_paper|failures_plus_sampled_successes|sampled_only
TRITONGEN_MLFLOW_REDACTION_POLICY=hash_only|public_summary|full_artifacts_allowed
```

Default should be:

```text
TRITONGEN_MLFLOW_ENABLE=0
TRITONGEN_MLFLOW_FAIL_CLOSED=0
TRITONGEN_MLFLOW_LOG_FULL_SOURCE=0
TRITONGEN_MLFLOW_TRACE_SAMPLING=off
TRITONGEN_MLFLOW_REDACTION_POLICY=hash_only
```

For paper imports, `FAIL_CLOSED=1` is acceptable after the run has already
completed, because failing the import does not lose GPU work.

## Report Generation

MLflow should store reports but not become the only report renderer.

Recommended generated artifacts:

```text
reports/experiment_summary.md
reports/experiment_summary.html
reports/metric_gate_table.csv
reports/metric_scope_table.csv
reports/failure_distribution.csv
reports/cost_summary.csv
reports/pass_at_k_summary.csv
reports/performance_level4_summary.csv
reports/reproducibility_manifest.json
```

Every report should answer:

- what was run;
- which clusters were in scope;
- which conditions were in scope;
- which model/revision was used;
- which grammar/revision was used;
- what metric gates and denominators were used;
- which metrics were intentionally not evaluated at a cluster;
- which rows/artifacts are caveated;
- whether output is paper-primary, paper-secondary, diagnostic, or smoke-only.

## Paper-Grade Rerun Checklist

Before running:

- MLflow server started and reachable if live tracing is enabled.
- Post-hoc importer works on a smoke artifact.
- Importer idempotency verified on the same smoke artifact twice.
- Import lock behavior verified for the campaign ID.
- Metric registry exists and rejects bare `pass_at_k`.
- Observability sidecar schema is stable.
- Modal billing attribution strategy is chosen.
- Modal app tags or isolated time windows are planned.
- Artifact output paths are unique for the campaign.
- Git SHA, dirty status, and runner config will be captured.
- MLflow failure mode is set to non-blocking for live runs.
- Redaction policy is selected.
- Cost estimate and max allowed cost are recorded.
- MLflow database and artifact root backup plan is known.
- Trace sampling mode is selected.
- Harness schema versions are recorded.
- Model license/cache provenance fields are planned for larger-model runs.

During running:

- JSONL row writing remains durable.
- Sidecars are written incrementally where possible.
- MLflow live logging is best-effort only.
- Modal run windows are recorded in UTC.
- No paper-grade result depends on a live MLflow trace being present.
- Stop conditions and budget status are monitored outside MLflow.

After running:

- Validate row counts and hash sidecars.
- Run analyzers.
- Generate reports.
- Wait for Modal billing data to settle.
- Import artifacts into MLflow.
- Import Modal billing as artifact and aggregate metric.
- Run MLflow GenAI deterministic scorer audits.
- Mark MLflow parent run as `reportability=reportable` only after repo gates
  pass.
- Record lifecycle status transitions.
- Mark older comparable runs as `superseded` when appropriate.
- Create a frozen evidence bundle before paper-facing promotion.
- Record reviewer/signoff metadata before setting `promotion_status=approved`.

## Bigger-Model Planning

For larger models, MLflow helps most with comparison and cost accountability.

Add these params/tags before big-model campaigns:

```text
model_family
model_size_bucket
quantization
context_window
weights_source
weights_revision
model_license_name
model_license_url
weights_cache_policy
weights_cache_hit
modal_gpu_class
modal_min_containers
modal_max_containers
modal_timeout_s
generation_batching_policy
prompt_template_version
trace_sampling_mode
redaction_policy_version
cost_guardrail_usd
```

Add these metrics:

```text
decode_wall_clock_s_median
tokens_per_second_median
generation_timeout_rate
generation_oom_rate
estimated_generation_cost_usd
actual_generation_cost_usd
cost_per_correct_kernel_usd
cost_per_benchmarkable_kernel_usd
correctness_lift_vs_baseline
compile_lift_vs_baseline
```

Large-model campaigns should have a smoke/import dry run before any paper-scale
Modal spend.

Additional large-model controls:

- require a budget estimate before the run;
- require a smaller smoke run on the same Modal image and GPU class;
- track cold-start and model-load wall time separately from decode time;
- record whether weights were already cached;
- record model license and access provenance without secrets;
- record OOM, timeout, and preemption counts separately;
- prefer post-hoc import over remote live tracing until the larger-model route
  is stable.

## Implementation Phases

### Phase 0: Documentation And Contracts

- Create this plan.
- Add a pointer from the observability plan.
- Decide whether the sanitized architecture belongs in `docs/12` later.
- Add identity/idempotency, lifecycle, security, retention, budget, and
  cardinality policies to this plan.
- Add promotion/signoff, concurrency, schema compatibility, recovery, and
  model license/cache provenance policies to this plan.

Exit criteria:

- future agents know MLflow is approved as a harness, not source of truth;
- no code changes required.

### Phase 1: Post-Hoc Import MVP

- Add optional MLflow dependency.
- Add a local SQLite setup note.
- Implement importer for existing 2^2 artifacts and analyzer JSON.
- Log parent run, child runs, params, metrics, tags, and artifacts.
- Include metric registry enforcement.
- Implement deterministic import identity and no-op/reimport behavior.
- Emit local MLflow run mapping sidecar.
- Implement import lock or equivalent duplicate-import protection.
- Emit partial-import recovery reports.

Exit criteria:

- importer works on existing preliminary artifacts without changing them;
- no Modal code path depends on MLflow.

### Phase 2: Observability Sidecar Join

- Add sidecar fields for stage duration, token counts, runtime identity, and
  estimated cost.
- Import sidecars to MLflow as artifacts and aggregate metrics.
- Build cost/tokens/wall-clock per success summaries.
- Add import summary row counts, artifact counts, byte counts, and redaction
  policy metadata.

Exit criteria:

- MLflow can answer "what did this run cost per correct kernel?" with explicit
  caveats.

### Phase 3: Modal Billing Reconciliation

- Add Modal billing report fetcher.
- Add App tag or isolated-run-window policy.
- Log billing report artifacts.
- Keep actual and estimated cost separate.
- Record pre-run budget estimates and post-run reconciliation status.

Exit criteria:

- MLflow parent run contains post-hoc Modal cost evidence.

### Phase 4: Local Tracing

- Add MLflow tracing around local orchestration stages.
- Log candidate/stage trace metadata without remote container writes.
- Search traces and attach deterministic scorer audits.
- Add configurable trace sampling.

Exit criteria:

- traces improve debugging without changing Modal execution semantics.

### Phase 5: Optional Remote Tracing

- Add MLflow to Modal image only if needed.
- Add Modal secret/env config for tracking URI/auth.
- Add best-effort remote spans for generation/correctness/repair/benchmark.

Exit criteria:

- live traces exist for future runs and failures do not corrupt JSONL output.

### Phase 6: Evaluation Datasets And Prompt Registry

- Create SQL-backed golden datasets for smoke and paper-grade cells.
- Register prompt templates if prompt variants become experiment variables.
- Keep repo hashes as cross-reference.
- Define retention/backups before datasets become paper evidence.

Exit criteria:

- prompt/dataset governance is useful and does not fork source-of-truth.

## Testing Plan

Unit tests:

- metric registry rejects missing gates;
- bare `pass_at_k` cannot be logged as paper-facing;
- Cluster 1 functional metrics are rejected unless source rows have Level 2;
- Cluster 2 timing/speedup fields remain forbidden in primary rows;
- post-hoc importer logs expected metrics from fixture analyzer output;
- MLflow failures do not block JSONL row recording when live mode is enabled;
- import summary includes artifact hashes.
- importing the same artifact set twice does not create duplicate paper-parent
  runs;
- concurrent imports for the same campaign are rejected or serialized;
- redaction allowlist excludes known secret-bearing fields;
- lifecycle status transitions reject invalid reportable promotions.
- harness schema version compatibility is enforced.
- failed/partial imports can be resumed or explicitly reimported.

Integration tests:

- run importer against tiny fixture JSONL/sidecar/analyzer output;
- create a local SQLite MLflow backend in a temp directory;
- verify runs, tags, params, metrics, and artifacts are present;
- verify nested run parent IDs;
- verify no secrets are logged;
- verify trace search returns expected spans when local tracing is enabled.
- verify backup/restore instructions on a tiny local SQLite backend.
- verify frozen evidence bundle checksums.

Paper-grade preflight:

- import smoke artifacts;
- verify metric registry;
- verify billing report fetcher on a narrow window;
- verify reportability scorer gates;
- verify MLflow server backup path.
- verify cost guardrail fields are logged before launch.
- verify trace sampling and redaction policy tags are present.
- verify promotion/signoff fields are present before paper-facing approval.

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| MLflow becomes source of truth | Bad paper claims | JSONL/artifact registry remain authoritative. |
| Metric names hide gates | Misleading comparisons | Metric registry and explicit MLflow keys. |
| Live MLflow outage breaks Modal run | Lost GPU spend | Post-hoc first; live mode best-effort. |
| Too many MLflow runs | UI noise | Runs at campaign/cluster/condition level; row detail in artifacts/traces. |
| Billing attribution is approximate | Bad cost claims | Store actual vs estimated separately; use tags/time windows. |
| Prompt registry forks repo prompt hashes | Repro drift | Registry points back to git SHA and prompt hash. |
| SQL backend maintenance burden | Operational delay | SQLite locally; Postgres only for durable/shared paper use. |
| Remote tracing logs sensitive payloads | Privacy/repro risk | Hash-first trace policy; full payloads only by explicit artifact policy. |
| Duplicate imports create conflicting runs | Confusing evidence | Deterministic import identity and no-op/reimport behavior. |
| MLflow database or artifact root is lost | Lost audit index | Backup database/artifact root; raw repo artifacts remain authoritative. |
| Trace volume overwhelms backend | Slow UI and noisy evidence | Sampling modes and aggregate metrics only. |
| Bigger-model costs exceed expectations | Budget overrun | Pre-run estimates, stop conditions, Modal billing reconciliation. |
| Reportable status is set too early | Bad paper claims | Lifecycle state machine and reportability gates. |
| Concurrent imports race | Duplicate or partial evidence | Campaign locks and deterministic import identity. |
| Harness schema drifts silently | Incompatible imports | Explicit harness schema versions and migration rules. |
| Partial import is mistaken for complete | Bad evidence trail | `import_status=partial`, recovery reports, and resume policy. |
| Model license/access is unclear later | Paper or sharing friction | Log license/cache provenance without secrets. |
| MLflow UI state diverges from paper evidence | Audit confusion | Frozen evidence bundle with checksums. |

## Decision Summary

MLflow is beneficial for TritonGen because the project is moving from one
preliminary 2^2 result set to repeated, expensive, paper-grade Cluster 1-3
campaigns. The largest benefit is not automatic evaluation; it is trustworthy
experiment bookkeeping:

- one place to compare model-scale reruns;
- one place to browse artifacts and generated reports;
- one place to connect metrics to gates and denominators;
- one place to reconcile Modal cost;
- one place to debug long-running generation/repair failures.

The safest implementation order is:

```text
1. post-hoc importer
2. metric registry enforcement
3. observability sidecar import
4. Modal billing import
5. local traces
6. optional remote traces
7. evaluation datasets and prompt registry
```

This sequence gives useful reporting before adding operational risk to Modal
paper runs.
