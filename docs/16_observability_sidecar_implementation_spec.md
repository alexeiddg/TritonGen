# Observability Sidecar Implementation Spec

- Version: 0.2.2
- Date: 2026-06-03
- Status: implementation specification / no code changes or runs authorized by
  itself
- Owner stream: O, observability sidecars
- Primary planning source: `docs/12_experiment_observability_plan.md`
- Orchestration source: `docs/15_experiment_change_orchestration_contract.md`
- Live state source: `docs/handoff/experiment_change_orchestration_state.md`
- Current Cluster 3 context: Phase 14e froze the four-cell n=5 development
  matrix; no n=20, paper-scale, performance, profiler, timing, or speedup work
  is authorized by this spec

## Purpose

This document defines the implementation contract for observability sidecars
across TritonGen experiment runners. It is meant to be precise enough for an
agent to implement O0 through O4 without changing scientific result-row schemas,
without creating mixed-policy artifacts, and without accidentally authorizing
paid Modal or paper-scale work.

Observability sidecars record operational facts adjacent to result artifacts:

- run, stage, row, and attempt durations;
- token counts and token-count availability;
- Modal runtime identity and resource context when available;
- estimated compute cost from pinned pricing snapshots;
- post-hoc billing reconciliation status when later implemented;
- artifact and event completeness metadata.

Scientific rows remain the source of truth for experimental outcomes. Sidecars
support auditability, cost planning, and run diagnostics. They do not define new
success metrics by themselves.

## Non-Goals

This spec does not:

- authorize Modal, GPU, generation, experiment, n=5, n=20, or paper-scale runs;
- rewrite existing JSONL artifacts;
- add token, cost, duration, Modal, or billing fields to Cluster 1, Cluster 2,
  or Cluster 3 scientific result rows in O0 through O4;
- record prompts, full source text, raw feedback, raw compile logs, private
  eval details, or hidden correctness data in sidecars;
- implement performance benchmarking, kernel timing, speedup, profiler, Nsight,
  NCU, throughput, or latency measurements;
- make actual Modal billing claims without a later O5 reconciliation contract;
- make cost-per-success, lift, pass@k, statistical, or correctness-improvement
  claims.

## External Research Basis

Research was refreshed on 2026-05-28. Implementation must prefer primary docs
when later verifying these facts.

| Source | Implementation implication |
|---|---|
| [Modal billing guide](https://modal.com/docs/guide/billing) | Billing reports are post-hoc. Actual cost should be reconciled after a run, not written synchronously per row. |
| [Modal billing API](https://modal.com/docs/reference/modal.billing) and [billing CLI](https://modal.com/docs/reference/cli/billing) | O5 may use `modal.billing.workspace_billing_report` or `modal billing report`, but network/credentialed billing access requires explicit approval. |
| [Modal App reference](https://modal.com/docs/reference/modal.App) | App tags can support cost attribution for future runs. Current untagged historical runs cannot be made precisely tag-attributed after the fact. |
| [Modal pricing](https://modal.com/pricing) | Estimated cost must use a pinned pricing snapshot with source URL, retrieval date, currency, and rates. It must not be silently treated as invoice cost. |
| [Modal environment variables](https://modal.com/docs/guide/environment_variables) | Only an allowlist of non-secret Modal runtime variables may be recorded. Secrets and identity tokens must be excluded. |
| [Modal current function call ID](https://modal.com/docs/reference/modal.current_function_call_id) and [current input ID](https://modal.com/docs/reference/modal.current_input_id) | Remote event records may include function-call and input IDs through the existing `shared/modal_harness/runtime.py` helper. |
| [Modal FunctionCall](https://modal.com/docs/reference/modal.FunctionCall) | Switching from `.remote()` to `.spawn()` only for telemetry is a behavior change and is out of scope for initial sidecar work. |
| [Modal GPU metrics](https://modal.com/docs/guide/gpu-metrics) | GPU utilization, power, memory, and temperature are operational metrics, not kernel-performance evidence. They are out of scope unless a later O6/performance contract authorizes them. |
| [JSON Lines](https://jsonlines.org/) | Event sidecars should be UTF-8 newline-delimited JSON, one complete JSON object per line. |
| [Python `time` docs](https://docs.python.org/3/library/time.html) | Durations should use monotonic/performance-counter clocks such as `perf_counter_ns`; wall-clock UTC timestamps are for ordering and human audit, not elapsed-time math. |
| [Pydantic models](https://docs.pydantic.dev/) | Pydantic is already used by the repo's Modal harness and is acceptable for strict sidecar schema validation without adding a new dependency. |
| [Transformers generation docs](https://huggingface.co/docs/transformers/main_classes/text_generation) | Token counts should be derived from tokenizer input length and generated sequence length, or marked unavailable. Do not store token IDs. |
| [OpenTelemetry logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) | Use an event-shaped data model with timestamps, severity, body, and attributes, but do not introduce OpenTelemetry runtime dependencies in O0. |

## Resolved Observability Decisions

These decisions supersede the prior open defaults for observability-sidecar
implementation work.

| ID | Resolution | Implementation effect |
|---|---|---|
| D-OBS-01 | Initial rollout is opt-in for existing and development runners. Paper-scale or final-design runs should use `required` mode once O0/O1/O3/O4 are implemented and accepted. | Add an explicit mode, not an implicit default. Legacy runner behavior remains unchanged when mode is absent or `off`. |
| D-OBS-02 | Canonical IDs are explicit: `experiment_id` names the logical experiment design, and `run_id` names one concrete execution attempt. Both are required when observability is enabled. | Do not infer critical IDs only from filenames. Handoffs may still include output paths as join keys. |
| D-OBS-03 | Actual Modal cost attribution is future O5 and should use App tags plus non-overlapping time windows where possible. Until O5, only estimated cost or `actual_billing_status=unavailable` is allowed. | O0-O4 cannot claim actual spend. Historical untagged runs remain attribution-limited. |
| D-OBS-04 | Phase 14c already ran before sidecars and Phase 14e is now frozen. Future final-design or paper-scale runs should wait for accepted O0/O1/O3/O4 or explicitly mark observability unavailable in the run approval packet. | No retroactive sidecar is fabricated for Phase 14a through Phase 14e artifacts. |

## Rollout Summary

| Package | Scope | Runner behavior | Modal/output mutation |
|---|---|---|---|
| O0 sidecar core | Add `shared/observability` schema, path, logger, redaction, and tests. | None. | None. |
| O1 local runner instrumentation | Add opt-in run/stage/row events to one runner at a time. | Unchanged when mode is `off`; sidecars written only when enabled. | Tests only unless a run packet approves execution. |
| O2 Modal context | Capture optional remote runtime identity and resource context. | No switch from `.remote()` to `.spawn()`. | No new Modal run by implementation alone. |
| O3 token telemetry | Record prompt/generated/total token counts when already available or cheaply computable. | Do not store token IDs or prompt text. | No new generation run by implementation alone. |
| O4 estimated compute cost | Add pinned pricing snapshots and summary math. | No actual billing claim. | No billing API call. |
| O5 actual billing reconciliation | Future CLI/API reconciliation. | Requires billing/tag policy and credentials. | Requires explicit approval if querying billing. |
| O6 performance timing contract | Future Level 4/performance-only contract. | Out of scope. | Out of scope. |

## Package O0: Sidecar Core Contract

### Allowed Files

O0 may create or edit only:

```text
shared/observability/__init__.py
shared/observability/schema.py
shared/observability/logger.py
shared/observability/paths.py
shared/observability/redaction.py
shared/tests/test_observability_schema.py
shared/tests/test_observability_logger.py
shared/tests/test_observability_redaction.py
shared/tests/test_observability_imports.py
```

If O0 needs pricing helpers, defer them to O4 or add them only behind tests that
do not require runner integration.

O1 runner branches may add runner-specific observability tests beside the
runner they instrument and may add a shared runner contract test under:

```text
shared/tests/test_observability_runner_contract.py
```

O4 may add cost-estimate tests under:

```text
shared/tests/test_observability_costs.py
```

### Forbidden Files

O0 must not edit:

```text
cluster1/experiments/*
cluster2/experiments/*
cluster3/experiments/*
cluster1/results/*
cluster2/results/*
cluster3/results/*
shared/analysis/*
outputs/*
audits/*
```

Documentation updates are allowed in the same work unit, but no raw artifact or
Modal output may be changed.

### Schema Technology

Use Pydantic v2 models or repo-style dataclasses with equivalent strict
validation. Pydantic is preferred for O0 because the repo already uses it under
`shared/modal_harness/schemas.py`, and JSON-schema export is useful for audit.
Do not add a new dependency.

`shared/observability` must remain cheap to import:

- no Modal import in `schema.py`, `logger.py`, `paths.py`, or `redaction.py`;
- no Torch, Triton, Transformers, or XGrammar import;
- no network access;
- no environment reads except through explicit helper calls in later O2 code.

### Import Boundary Contract

O0 must include an import-boundary test proving that importing
`shared.observability` and its O0 submodules does not import any GPU, remote, or
generation stack:

```text
modal
torch
triton
transformers
xgrammar
```

The test may inspect `sys.modules` before and after import or use the repo's
existing AST import-scan pattern. Later O2 helpers that touch Modal context must
live behind lazy functions or dependency-injected boundaries and must not make
the package import Modal at module import time.

## Artifact Path Contract

For a result artifact:

```text
outputs/<cluster>/<name>.jsonl
```

the default observability artifacts are:

```text
outputs/<cluster>/<name>.observability.jsonl
outputs/<cluster>/<name>.observability.summary.json
outputs/<cluster>/<name>.observability.jsonl.hashes.json
```

Rules:

- The event sidecar is append-only JSONL.
- The summary is written atomically at run completion or explicit partial-run
  finalization.
- The sidecar hash file records the event JSONL SHA-256 and summary SHA-256
  when the summary exists.
- Sidecar names must not collide with existing `.hashes.json` content-hash
  sidecars.
- A resume must validate the existing event sidecar prefix before appending.
- A run may not append events to a sidecar for a different `experiment_id`,
  `run_id`, result path, schema version, or git commit.
- Existing historical result artifacts do not require retroactive sidecars.

### Path Collision Safety

Custom `--observability-output` paths must be validated before any remote work
or result write. A sidecar path is invalid if it:

- equals the result JSONL path;
- equals the result content-hash sidecar path such as
  `<result>.hashes.json`;
- equals a Cluster 1 metadata path such as `<result>.meta.json`;
- equals the observability summary path;
- equals the observability hash path;
- is a directory;
- points at an existing non-file path;
- points at an existing sidecar whose schema, `experiment_id`, `run_id`, result
  path, git commit, or event prefix is incompatible with the current run;
- resolves outside the approved workspace/output root unless the run packet
  explicitly approves that external path.

The default path policy should keep sidecars next to their result artifact.
Custom paths are allowed only to avoid collisions or support explicitly approved
test fixtures.

## Identity Contract

Observability identity has three levels.

### Experiment Identity

`experiment_id` names the logical design, for example:

```text
cluster3_phase14_matrix_dev
cluster2_paper_2x2_current
```

It must be explicit when observability is enabled. It may be reused across
reruns of the same design.

### Run Identity

`run_id` names one concrete execution attempt, for example:

```text
cluster3_phase14e_freeze_doc_only_20260528
cluster3_paper_readiness_dryrun_20260528T173000Z
```

It must be explicit when observability is enabled. It must not be derived
silently from the output path.

### Row Identity

`row_identity` joins events to result rows without copying the row:

```text
cluster
condition
kernel_class
kernel_name
dtype
base_seed
generation_seed
attempt_index
terminal_attempt_index
source_hash
row_sha256
```

Fields may be `null` before a row exists. A completed-row event should include
the strongest available row identity, preferably including `row_sha256` after
serialization.

`row_sha256` is computed over the exact canonical serialized result-row JSON
string before the trailing JSONL newline is added. Do not hash pretty-printed
JSON, parsed/re-emitted dictionaries, or the newline byte.

## Event Schema Contract

Every event record must include:

```text
schema_version
event_id
event_sequence
event_type
severity
timestamp_utc
timestamp_unix_ns
monotonic_ns
clock_scope_id
experiment_id
run_id
artifact
row_identity
stage
attempt
status
duration_ns
duration_source
start_monotonic_ns
end_monotonic_ns
token_counts
modal_context
cost_estimate
error_summary
attributes
```

Recommended schema version:

```text
tritongen.observability.v1
```

Event identity and clock fields are fixed for O0:

- `event_id` is an RFC 4122 UUID string and must be unique within the sidecar.
- `event_sequence` is zero-based. The first event in a sidecar is `0`, and every
  later event increments by exactly one.
- `timestamp_utc` is an RFC 3339 UTC timestamp ending in `Z`.
- `timestamp_unix_ns` is an integer Unix epoch timestamp in nanoseconds.
- `monotonic_ns`, `start_monotonic_ns`, and `end_monotonic_ns` are process-local
  monotonic or performance-counter values and must not be compared across
  different `clock_scope_id` values.
- `duration_ns` is the top-level elapsed operational duration. If a duration is
  not known for an event, use `duration_ns=null` and an explicit
  `duration_source` of `unavailable` or `not_applicable`.
- `start_monotonic_ns` and `end_monotonic_ns` are nullable top-level fields.
  Completed duration events should include both when they share the same
  `clock_scope_id`.

### Event Types

Allowed initial event types:

```text
run_started
run_completed
run_failed
run_aborted
resume_validated
stage_started
stage_completed
stage_failed
row_started
row_completed
row_skipped
remote_call_started
remote_call_completed
remote_call_failed
summary_written
partial_artifact_detected
cost_estimate_written
```

Do not add `benchmark_*`, `latency_*`, `profile_*`, `speedup_*`, or
`throughput_*` event types in O0 through O5.

### Stages

Allowed initial stages:

```text
preflight
generation
compile_eval
correctness_eval
p_repair
c_repair
row_append
hash_validation
summary
analysis
billing_reconciliation
```

`billing_reconciliation` may appear only in O5. No performance stage is defined
by this spec.

### Status Values

Allowed status values:

```text
started
succeeded
failed
skipped
unavailable
blocked
partial
not_applicable
```

Use `unavailable`, `not_applicable`, or `blocked` explicitly instead of omitting
fields when a value is known to be absent.

### Strict Schema And Attribute Contract

All O0 schema models must be closed-world:

```text
extra = forbid
```

or the equivalent if dataclasses are used. Unknown top-level fields, unknown
nested object fields, and unknown enum values must fail validation.

Allowed `severity` values:

```text
debug
info
warning
error
critical
```

Allowed `attributes` values are limited to JSON primitives and shallow lists of
JSON primitives:

```text
string
integer
number
boolean
null
list[string | integer | number | boolean | null]
```

`attributes` must not contain nested dictionaries, raw objects, bytes, traceback
objects, token IDs, source text, prompts, raw feedback, raw model output, raw
compile logs, private-eval fields, or environment dumps.

Attribute limits:

```text
max attribute keys: 32
max key length: 80 characters
max string value length: 512 characters
max list length: 32
max serialized attributes bytes: 8192
```

Every event, summary, modal-context payload, token-count payload, cost payload,
error summary, and attribute map must pass the recursive forbidden-key and
forbidden-value scans defined by the privacy contract. Redaction is allowed only
for bounded public error summaries; fields that look like source, prompts, raw
logs, private eval, or secrets should fail closed rather than be silently
truncated.

## Summary Schema Contract

The summary JSON must be derived from event records and must not invent facts
that are absent from events.

Required fields:

```text
schema_version
experiment_id
run_id
result_path
observability_event_path
observability_summary_path
generated_at_utc
git_commit
branch
workspace
row_counts
event_counts
stage_durations_ns
token_totals
modal_context_summary
estimated_cost_summary
actual_billing_status
completeness_status
caveats
source_event_sha256
summary_sha256
```

`git_commit`, `branch`, and `workspace` are explicit provenance inputs to the O0
summary writer. The summary writer must not shell out to Git or inspect the
local environment to infer them. `workspace` must be a repo-relative label such
as `.` or an approved workspace identifier; absolute local filesystem paths are
forbidden unless a run packet explicitly approves the path.

`actual_billing_status` must be one of:

```text
not_implemented
not_requested
unavailable
pending
reconciled
ambiguous
failed
```

O0 through O4 must use `not_implemented`, `not_requested`, or `unavailable`.

### Summary And Hash Canonicalization

The summary must be canonicalized before hashing:

1. build the summary object with `summary_sha256=null`;
2. serialize it with sorted keys, compact separators, UTF-8, and one trailing
   newline;
3. compute `summary_sha256` over that byte sequence;
4. write the final summary with the computed `summary_sha256`;
5. verify by reloading the final summary, setting `summary_sha256=null`, and
   recomputing the digest.

The observability hash sidecar must use its own closed schema:

```text
schema_version
experiment_id
run_id
result_path
observability_event_path
observability_summary_path
event_jsonl_sha256
summary_json_sha256
summary_status
event_count
generated_at_utc
hash_algorithm
```

`hash_algorithm` must be `sha256`. `summary_status` must be one of:

```text
not_written
written
unavailable
failed
```

If no summary exists yet, the hash sidecar may record
`summary_json_sha256=null` with `summary_status=not_written`. Once a summary is
written, the hash sidecar must be rewritten atomically with
`summary_status=written`. A resume must reject event sidecars whose stored hash
metadata conflicts with the current event bytes.

### Join And Completeness Validation

Summary generation must validate event/result alignment before reporting
`completeness_status=complete`.

Required checks:

- event sequences are contiguous and unique from `0`;
- event IDs are unique;
- exactly one `run_started` event exists;
- exactly one terminal run event exists among `run_completed`, `run_failed`, or
  `run_aborted`;
- every `row_completed` event has a row identity that can join to a serialized
  result row when result rows exist;
- completed-row event count matches result-row count for complete runs;
- partial runs record the mismatch explicitly;
- duplicate row identities are rejected unless the event type is a resume
  prefix validation event;
- row hashes match when `row_sha256` is available;
- sidecar summary counts match the event stream;
- missing token, Modal context, or cost sections are summarized as
  `unavailable` or `not_applicable`, not omitted.

The summary must not report cost, token, or duration totals from malformed,
unjoined, duplicate, or schema-invalid events.

## Logger Contract

Implement a durable append logger patterned after `Cluster2JsonlAppendLogger`
and `Cluster3JsonlAppendLogger`:

- create parent directories;
- write one canonical JSON object per line;
- flush after each event;
- fsync by default;
- support `overwrite` and `resume`;
- reject unsafe append mode;
- validate schema before writing;
- validate resume prefix compatibility;
- write summaries atomically through a temporary file and `replace`;
- fsync the output directory after summary replace when fsync is enabled.

Canonical event JSON should be deterministic:

```text
sort_keys=True
compact separators
UTF-8
one trailing newline per record
```

The logger must not import Modal or other GPU/runtime stacks.

## Dual-Write Failure Matrix

Result rows and observability sidecars are separate artifacts; they cannot be
treated as one atomic database transaction. Runner instrumentation must preserve
both artifacts and make any divergence visible.

Recommended row-level order:

1. write `row_started` before row work begins when observability is enabled;
2. compute the scientific result row;
3. append and fsync the scientific result row;
4. write `row_completed` with the strongest available row identity and
   `row_sha256`;
5. write or update summary/hash artifacts only at run completion or explicit
   partial finalization.

Failure handling:

| Failure point | `best_effort` behavior | `required` behavior | Required marker |
|---|---|---|---|
| `row_started` sidecar write fails before row work | Continue without sidecar for that row and add warning if possible. | Abort before row work or remote call. | `observability_status=degraded` or preflight failure. |
| Scientific result row append fails after sidecar event | Stop runner according to existing result logger policy. | Same. | Event stream must end as `run_failed` or `run_aborted` if possible; no success summary. |
| Scientific result row append succeeds but `row_completed` sidecar write fails | Preserve result row; continue only if sidecar mode can be degraded and handoff records missing event. | Stop further work, preserve partial artifacts, require audit before resume. | Summary `completeness_status=partial` or unavailable summary. |
| `row_completed` sidecar write succeeds but later result validation fails | Preserve both artifacts; do not delete sidecar event. | Same. | Summary rejects `complete` and records row/schema mismatch. |
| Summary write fails after all rows are written | Preserve result rows and event sidecar; mark summary unavailable in handoff. | Treat as run finalization failure requiring audit before claims. | Missing summary is not observability coverage. |
| Observability hash sidecar write fails | Preserve result rows, event sidecar, and summary; mark hash unavailable. | Treat as finalization failure requiring audit before claims. | `required` runs cannot claim observability coverage. |

No mode may roll back or rewrite scientific result rows to make observability
look complete. No mode may overwrite a partial sidecar without an audit and an
explicit resume or archive policy.

## Timing Contract

Durations are operational wall-clock durations, not kernel performance.

Implementation rules:

- use `time.perf_counter_ns()` or `time.monotonic_ns()` for elapsed durations;
- use UTC timestamps for human ordering and billing windows;
- never compute elapsed time by subtracting UTC timestamps when monotonic data is
  available;
- never combine monotonic values from different processes unless
  `clock_scope_id` matches;
- record cross-process remote-call duration from the local caller's monotonic
  start and end around the remote call;
- remote containers may record their own process-local stage durations with a
  different `clock_scope_id`;
- avoid field names `latency`, `runtime_ms`, `kernel_time`, `timing`,
  `throughput`, or `speedup` until O6.

Preferred duration fields:

```text
start_monotonic_ns
end_monotonic_ns
duration_ns
duration_source
```

Allowed `duration_source` values:

```text
local_monotonic
remote_monotonic
caller_observed_remote_call
unavailable
not_applicable
```

## Modal Context Contract

O2 may add optional Modal context collection, but it must not make local tests
depend on Modal runtime availability.

Allowed fields:

```text
is_remote
function_call_id
input_id
task_id
image_id
region
cloud_provider
environment_name
app_name
gpu_type
gpu_count
cpu_cores
memory_gib
timeout_s
container_started_at_utc
modal_context_source
```

Allowed sources:

```text
shared_modal_runtime_helper
modal_environment_allowlist
runner_config
unavailable
```

Environment allowlist:

```text
MODAL_TASK_ID
MODAL_IMAGE_ID
MODAL_REGION
MODAL_CLOUD_PROVIDER
MODAL_ENVIRONMENT
MODAL_IS_REMOTE
```

Forbidden environment keys include any key containing:

```text
TOKEN
SECRET
PASSWORD
KEY
CREDENTIAL
```

`MODAL_IDENTITY_TOKEN` must never be recorded.

## Token Telemetry Contract

O3 records counts, not tokens.

Allowed O3 token telemetry fields are counts/status only:

```text
token_counts_available
prompt_tokens
generated_tokens
total_tokens
token_count_source
token_count_status
```

Allowed `token_count_source` values:

```text
generation_sequence_length_delta
existing_generation_result
existing_remote_payload
unavailable
not_applicable
```

Rules:

- never store token IDs;
- never store prompts;
- never store generated source text;
- never store tokenizer-private dumps, tokenizer internal state, raw model output,
  raw completion text, or private feedback/eval details;
- do not import or call tokenizers, models, or generation paths only for
  observability telemetry;
- record counts only when they are already supplied by the current code path,
  returned by an existing generation payload, or cheaply computed from already
  materialized sequence lengths without new model/runtime work;
- count generated tokens from generated sequence length minus prompt length when
  both lengths are already available;
- reuse existing scalar fields such as `generated_token_count` where present;
- record `unavailable` instead of guessing if the tokenizer or sequence length
  is unavailable;
- `prompt_tokens`, `generated_tokens`, and `total_tokens` must be non-negative
  integers, and `total_tokens` must equal `prompt_tokens + generated_tokens`
  when all three are present;
- existing model/tokenizer provenance fields such as `max_new_tokens`,
  `tokenizer_id`, `tokenizer_revision`, or truncation flags are not O3 token
  telemetry fields unless a later spec version explicitly reclassifies them;
- token totals in summaries must group by condition, stage, and success/failure
  status without leaking source or prompt content.

## Cost Estimate Contract

O4 estimates compute cost from observed durations and pinned rate snapshots.

Add a pricing snapshot only under:

```text
shared/observability/pricing/
```

Snapshot fields:

```text
snapshot_id
retrieved_at_utc
source_url
currency
provider
rates
notes
```

Cost estimate fields:

```text
estimate_status
price_snapshot_id
currency
estimated_gpu_seconds
estimated_cpu_core_seconds
estimated_memory_gib_seconds
estimated_gpu_cost_usd
estimated_cpu_cost_usd
estimated_memory_cost_usd
estimated_total_cost_usd
estimation_confidence
unavailable_reason
```

Rules:

- represent money as decimal strings in JSON;
- keep estimated and actual billing fields separate;
- do not claim cost-per-success in the sidecar layer;
- do not query Modal billing in O4;
- mark estimates `unavailable` when resource allocation or duration data is
  insufficient;
- document every pricing snapshot with source URL and retrieval date;
- require a spec update if Modal pricing changes format or attribution model.

### Cost Basis And Confidence

Estimated cost must state the measurement basis:

```text
caller_observed_remote_call_wall_time
remote_container_stage_wall_time
configured_resource_request_time
billing_report_interval
unavailable
```

Caller-observed remote-call wall time is useful for budget planning but is not
equivalent to Modal billable/container time. If only caller-observed wall time is
available, set `estimation_confidence=low` unless a later validation proves the
estimate is a conservative upper bound. If resource request fields are missing,
set `estimate_status=unavailable`.

The summary must distinguish:

```text
estimated_compute_cost
actual_billing_cost
cost_basis
estimation_confidence
```

O0 through O4 may populate only estimated fields. Actual billing fields remain
`not_implemented`, `not_requested`, or `unavailable`.

## Actual Billing Reconciliation Contract

O5 is future work. It must not be implemented as part of O0 through O4.

Minimum future requirements:

- explicit user approval for credentialed billing access;
- dry-run mode;
- start/end UTC window with delay buffer after run completion;
- App tag filter where available;
- isolated-window fallback with `attribution_confidence=low` when tags are
  missing;
- clear separation between pre-credit granular cost and final invoice cost;
- no per-row actual billing claim unless Modal can attribute usage at that
  granularity.

## Privacy And Boundary Contract

Sidecars must never contain:

```text
full source text
prompt text
raw model output
raw feedback prompt
raw compile logs
private eval shapes
hidden correctness data
torch.testing payloads
allclose payloads
secret environment variables
Modal identity tokens
Hugging Face tokens
stack traces with secret-bearing environment dumps
```

Allowed alternatives:

```text
source_sha256
prompt_sha256
error_excerpt_sha256
public_failure_code
bounded_public_error_class
row_sha256
```

Redaction tests must include negative fixtures for:

```text
HF_TOKEN
MODAL_IDENTITY_TOKEN
AWS_SECRET_ACCESS_KEY
private eval
eval_shape_set
torch.testing
allclose
```

## Runner Mode Contract

Runner integrations must expose an explicit mode:

```text
off
best_effort
required
```

Mode behavior:

| Mode | Behavior |
|---|---|
| `off` | Default for legacy behavior. No sidecar path is opened. |
| `best_effort` | Sidecar failures are recorded when possible and then degraded to warnings. Scientific row writing continues unless the runner itself fails. |
| `required` | Sidecar initialization failure aborts before remote work. Mid-run sidecar failure stops further work, preserves partial artifacts, and requires audit before resume/rerun. |

Any run claiming observability coverage must use `required`.

## Runner Integration Order

Integrate one runner at a time, under a serialized runner lease.

Recommended order:

1. Cluster 3 runner, because upcoming P/C/G+C+P planning depends most on cost
   and token visibility.
2. Cluster 2 runner, because C repair and correctness evaluation have the
   richest stage boundaries.
3. Cluster 1 runner, because it has older logging and metadata sidecars that
   need more compatibility care.

Do not instrument all runners in one branch unless a reviewer explicitly accepts
the wider blast radius.

## Analyzer And Reporting Boundary

O0 through O4 do not require analyzer changes.

Analyzer joins with observability sidecars are future work and must wait until:

- sidecar schema v1 is accepted;
- result-row join identity is stable;
- structural/task metric registry work defines how token, duration, and cost
  summaries should be labeled;
- mixed-policy and missing-sidecar behavior is defined.

Until then, sidecar summaries are operational diagnostics, not report-facing
statistical result tables.

## Implementation Plan

### Phase O0A - Core Schema

Implement:

```text
ObservabilityRunIdentity
ObservabilityArtifactIdentity
ObservabilityRowIdentity
ObservabilityAttemptIdentity
ObservabilityTokenCounts
ObservabilityModalContext
ObservabilityCostEstimate
ObservabilityErrorSummary
ObservabilityEvent
ObservabilitySummary
```

Acceptance:

- strict validation rejects unknown event types and forbidden field names;
- strict validation rejects unknown top-level and nested schema fields;
- severity values, status values, event types, stage names, and duration sources
  are enumerated;
- event IDs are UUID strings and event sequences start at `0` without gaps;
- attributes are primitive-only and size-limited;
- missing required IDs fail when mode is not `off`;
- `unavailable` and `not_applicable` are explicit;
- summaries reject absolute local workspace paths unless explicitly approved;
- JSON schema export works if Pydantic is used.

### Phase O0B - Paths And Logger

Implement:

```text
default_observability_event_path(result_path)
default_observability_summary_path(result_path)
default_observability_hash_path(event_path)
ObservabilityJsonlAppendLogger
write_observability_summary_atomic
load_observability_events
```

Acceptance:

- JSONL round trip preserves canonical events;
- resume rejects mismatched schema, run ID, result path, or prefix;
- resume rejects incompatible hash-sidecar metadata;
- path validation rejects result, content-hash, metadata, summary, hash, and
  directory collisions;
- summary write is atomic;
- summary hash canonicalization is deterministic and self-reference safe;
- hash sidecar write and rewrite are atomic;
- fsync can be disabled in tests.

### Phase O0C - Redaction

Implement:

```text
sanitize_attributes
sanitize_error_summary
reject_forbidden_observability_payload
```

Acceptance:

- forbidden secrets and private-eval phrases are rejected or redacted;
- source, prompt, raw feedback, and raw compile logs are rejected by key name and
  by representative value fixtures.

### Phase O1 - Local Runner Instrumentation

Under a runner lease, add:

```text
--observability-mode off|best_effort|required
--observability-experiment-id <id>
--observability-run-id <id>
--observability-output <optional path>
```

Acceptance:

- default behavior remains identical with mode `off`;
- mode `required` validates IDs and sidecar path before any remote work;
- invalid `required` mode leaves generation, correctness, repair, and Modal
  dependencies uncalled;
- mode `off` writes no observability event, summary, or hash sidecar;
- dual-write failure cases are covered for the integrated runner;
- no sidecar writes happen unless mode is enabled;
- row-completed events join to serialized row identity;
- no scientific row schema changes.

### Phase O2 - Modal Context

Add a small helper that calls existing Modal runtime helpers only inside remote
code paths or dependency-injected boundaries.

Acceptance:

- local tests pass outside Modal;
- unavailable Modal fields become `unavailable`, not crashes;
- forbidden environment variables are not recorded;
- `.remote()` orchestration remains unchanged.

### Phase O3 - Token Telemetry

Record token counts where tokenizers or existing generation outputs already make
counts available.

Acceptance:

- prompt/generated/total counts are exact when available;
- unavailable counts are explicit;
- no token IDs, prompts, sources, or raw outputs are written;
- summaries aggregate token counts by stage and condition.

### Phase O4 - Estimated Cost

Add pricing snapshot parsing and summary estimates.

Acceptance:

- formulas use decimal arithmetic;
- estimates are separated from actual billing;
- missing resource data yields `estimate_status=unavailable`;
- caller-observed wall-clock estimates are labeled with low confidence unless
  explicitly justified;
- pricing snapshot source URL and retrieval date are recorded;
- no billing API or CLI call occurs.

## Required Tests

O0:

```bash
.venv/bin/python -m pytest \
  shared/tests/test_observability_schema.py \
  shared/tests/test_observability_logger.py \
  shared/tests/test_observability_redaction.py \
  shared/tests/test_observability_imports.py -q
```

O1, per runner:

```bash
.venv/bin/python -m pytest <runner-specific tests> \
  shared/tests/test_observability_runner_contract.py -q
```

O4:

```bash
.venv/bin/python -m pytest shared/tests/test_observability_costs.py -q
```

Required scans before any package exits:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" \
  shared/observability shared/tests/test_observability*
```

```bash
rg -i "speedup|profil|nsight|ncu|latency|runtime_ms|benchmark|throughput" \
  shared/observability docs/16_observability_sidecar_implementation_spec.md
```

Manual review must confirm any matches are prohibitions, caveats, or future
out-of-scope references, not implemented telemetry fields.

For runner-touching branches, also record:

```bash
git status --short --branch
```

and:

```text
Modal/output mutation performed: no
```

## Exit Gates

O0 exits when:

- schema, path, logger, and redaction tests pass;
- strict schema, primitive attributes, import-boundary, path-collision,
  summary-hash, hash-sidecar, and completeness-validation tests pass;
- no runner or result schema files were touched;
- sidecar artifacts can be written and resumed in a temporary directory;
- forbidden payload tests pass;
- docs and registry routing are updated.

O1 exits when:

- one runner supports explicit observability modes;
- mode `off` preserves existing tests and behavior;
- mode `required` fails before remote work when IDs or paths are invalid;
- runner tests prove generation/validation/repair dependencies are uncalled on
  invalid `required` preflight;
- dual-write failure handling is tested for the integrated runner;
- sidecars are written only in local/test paths unless a run packet approves
  execution;
- no raw output artifacts are changed.

O2 exits when:

- Modal context is optional and unavailable-safe;
- Modal allowlist tests pass;
- secret env keys are rejected;
- no orchestration switch to `.spawn()` occurred.

O3 exits when:

- token-count tests pass;
- counts are exact or explicit `unavailable`;
- no token IDs, prompts, sources, or raw outputs are written.

O4 exits when:

- pricing snapshot tests pass;
- estimated cost summaries are deterministic;
- cost basis and confidence are explicit;
- actual billing remains `not_implemented`, `not_requested`, or `unavailable`.

## Rollback Policy

Rollback must be simple:

- deleting or disabling `shared/observability` must not break existing result
  row loading;
- runner observability mode defaults to `off`;
- sidecar files are optional for legacy artifacts;
- analyzers must not require sidecars until a later analyzer integration spec
  says so;
- failed sidecar writes must not corrupt scientific row artifacts.

## Handoff Requirements

Every observability package handoff must include:

```text
package:
branch/worktree:
baseline commit:
files touched:
runner surfaces touched:
serialized leases:
observability mode default:
sidecar schema version:
sidecar path policy:
tests run:
scans run:
Modal/output mutation performed: yes/no
scientific row schema changed: yes/no
actual billing queried: yes/no
known caveats:
next blocked/unblocked packages:
```

## Current Recommendation

Do O0 before any new paid Cluster 3 run. If a diagnostic run is approved before
O0/O1/O3/O4 land, its approval packet must explicitly state:

```text
observability policy: unavailable_current_runner
claim boundary: diagnostic only; no token, cost, duration, paper-scale, lift,
pass@k, statistical, performance, speedup, or cost-per-success claim
```

For final-design or paper-scale runs, require accepted O0/O1/O3/O4 or a written
go/no-go decision explaining why observability remains unavailable.
