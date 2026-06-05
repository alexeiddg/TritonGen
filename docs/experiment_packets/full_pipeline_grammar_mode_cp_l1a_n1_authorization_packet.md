# Full Pipeline Grammar-Mode x C x P L1a n=1 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
packet_type: draft authorization packet; not an execution packet
branch: `codex/full-pipeline-l1-smoke-dev-approval-packet`
baseline_commit: `0cc43c1 Audit full pipeline launch packet promotion`
launch_packet: `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
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

This packet is a draft authorization artifact for review. It is not signed and
does not authorize Modal, GPU work, generation, experiments, output mutation,
analyzer output refresh, report artifact refresh, MLflow runtime writes,
billing queries, dependency changes, lockfile changes, or paper-scale claims.

## Launch-Packet Dependency

This L1a packet depends on the patched launch packet selecting the 12-cell
`grammar_mode x C x P` design.

It must not be converted into an execution packet unless:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
  continues to name the 12-cell design as the active selected design;
- the old 8-cell design remains superseded for future execution;
- the output namespace uses
  `full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- grammar-mode support and mapping proof are supplied.

## Intended L1a Scope

Purpose:

- command/path validation;
- output namespace validation;
- row schema validation;
- content-hash sidecar validation;
- observability sidecar validation;
- analyzer grouping by `grammar_mode`;
- MLflow post-hoc indexing dry-run or fixture validation after artifacts exist.

Scale:

```text
level: L1a
scale_tier: smoke/dev
n_per_cell: 1
cell_count: 12
expected_rows_if_fully_executed: 12
paper_evidence: no
```

## Twelve-Cell Matrix

| condition_id | grammar_mode | correctness_feedback_C | compile_feedback_P |
|---|---|---:|---:|
| `grammar_off__c_off__p_off` | `grammar_off` | off | off |
| `grammar_off__c_on__p_off` | `grammar_off` | on | off |
| `grammar_off__c_off__p_on` | `grammar_off` | off | on |
| `grammar_off__c_on__p_on` | `grammar_off` | on | on |
| `primary_grammar__c_off__p_off` | `primary_grammar` | off | off |
| `primary_grammar__c_on__p_off` | `primary_grammar` | on | off |
| `primary_grammar__c_off__p_on` | `primary_grammar` | off | on |
| `primary_grammar__c_on__p_on` | `primary_grammar` | on | on |
| `task_agnostic_grammar__c_off__p_off` | `task_agnostic_grammar` | off | off |
| `task_agnostic_grammar__c_on__p_off` | `task_agnostic_grammar` | on | off |
| `task_agnostic_grammar__c_off__p_on` | `task_agnostic_grammar` | off | on |
| `task_agnostic_grammar__c_on__p_on` | `task_agnostic_grammar` | on | on |

## Required Grammar-Mode Mapping Before Approval

The execution approval line must remain unsigned until all fields below are
filled with exact values:

| grammar_mode | required mapping before execution |
|---|---|
| `grammar_off` | explicit no-constrained-decoding config and proof that rows will label `grammar_mode=grammar_off` |
| `primary_grammar` | exact grammar file/path, activation config, grammar hash, claim scope, and proof that this mode is distinct from or intentionally aliased to `task_agnostic_grammar` |
| `task_agnostic_grammar` | exact task-agnostic grammar file/path, activation config, grammar hash, and claim scope |

Current blocker:

- `shared/generation_metadata.py` exposes `template_upper_bound` and
  `task_agnostic` variants.
- `cluster3/experiments/run_cluster3_modal.py` exposes `grammar_variant`, not a
  first-class three-level `grammar_mode` selector.
- Current docs record `task_agnostic` as the report-facing primary grammar and
  `template_upper_bound` as diagnostic/non-primary.
- Therefore this packet is blocked for execution until the future signer
  confirms the exact two active grammar modes and how each row/analyzer output
  will carry `grammar_mode`.

## Required Runtime Fields Before Approval

```text
approval_source: not_approved
approval_timestamp: not_applicable
target_branch: codex/full-pipeline-l1-smoke-dev-approval-packet
target_commit: unavailable_until_review_commit
command: not_authorized
working_directory: /Users/alexeidelgado/Desktop/TritonGen
model_id: unavailable_until_approval
model_revision: unavailable_until_approval
tokenizer_revision: unavailable_until_approval
decoding_config: unavailable_until_approval
kernel_class: elementwise_relu_or_explicit_future_value
problem_ids: unavailable_until_approval
dtype: fp32_or_explicit_future_value
shape_policy: unavailable_until_approval
repair_history_policy: agentic_transcript_v1_for_C_or_P_cells
observability_mode: best_effort_or_required_until_approval
observability_experiment_id: full_pipeline_grammar_mode_cp_factorial_v1
observability_run_id: unavailable_until_approval
max_rows: 12
max_generation_attempts: unavailable_until_approval
max_repair_attempts_per_row: unavailable_until_approval
max_wall_clock: unavailable_until_approval
max_estimated_cost: unavailable_until_approval
stop_on_first_infrastructure_failure: yes
overwrite_policy: fail_if_any_target_path_exists
resume_policy: no_resume_unless_explicitly_approved
```

## Planned Namespaces

These are reserved planning namespaces only. This packet does not create,
overwrite, append, or validate them.

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
artifacts/analysis/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/reports/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/mlflow_index/full_pipeline_grammar_mode_cp_factorial_v1/
artifacts/billing/full_pipeline_grammar_mode_cp_factorial_v1/
```

Any future execution packet must prove all target output and sidecar paths do
not exist before launch unless an explicit resume/append/archive policy is
approved.

## Pre-Approval Validation Required

A future signer must record exact pass/fail results for:

```text
git status --short --branch
git log --oneline --decorate -12
git diff --check
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report shared/tracking shared/analysis shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
rg -n "MODAL_AUTHORIZED: YES|GPU_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|EXPERIMENT_EXECUTION_AUTHORIZED: YES|BENCHMARK_AUTHORIZED: YES|PROFILER_AUTHORIZED: YES|OUTPUT_MUTATION_AUTHORIZED: YES|PAPER_SCALE_AUTHORIZED: YES|MLFLOW_TRACKING_EXECUTION_AUTHORIZED: YES|AUTHORIZES_EXECUTION: YES" docs audits .contracts --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
```

Additional required proof before approval:

- exact command/config supports all 12 `grammar_mode`/C/P cells;
- every planned row will carry `grammar_mode`;
- active grammar rows will carry grammar file/path and grammar hash or matching
  sidecar evidence where supported;
- analyzer grouping is by `grammar_mode`;
- C/P interactions are analyzed conditional on `grammar_mode`;
- derived active-grammar summaries are diagnostic only;
- MLflow indexing remains post-hoc and non-authoritative.

## Post-Run Validation Required After Any Future Approved Run

If a later signed execution packet authorizes L1a and artifacts are created, the
post-run audit must include:

- row-count validation for 12 expected rows or explicit stop-condition
  disposition;
- schema validation;
- content-hash validation;
- observability event/summary/hash sidecar validation;
- grammar-mode/path/hash consistency validation;
- C/P eligibility validation;
- repair-history policy validation;
- analyzer grouping/quarantine validation;
- MLflow post-hoc importer dry-run or fixture validation;
- output/artifact registry and handoff updates.

## Stop Conditions

Stop before or during any future approved L1a execution if:

- the launch packet no longer selects the 12-cell `grammar_mode x C x P` design;
- any target path already exists without an approved resume/append/archive
  policy;
- `primary_grammar` and `task_agnostic_grammar` mapping is unresolved;
- the runner cannot label rows with `grammar_mode`;
- grammar file/path/hash evidence is missing for an active grammar mode;
- C fires outside F2;
- P fires outside `F1_COMPILE`;
- `F1_RUNTIME` is repaired;
- row schema validation fails;
- content-hash validation fails;
- observability required-mode validation fails;
- private-eval, raw prompt/source, token ID, billing secret, credential,
  performance, timing, speedup, profiler, or benchmark leakage appears.

## Explicit Approval

Unsigned. No execution is approved.

```text
NOT APPROVED. A future user approval must replace this line with a signed L1a
approval that names exact command, branch, commit, 12-cell matrix, grammar-mode
mapping, output paths, sidecar paths, model/revision/decoding config, stop/spend
limits, and validation commands.
```
