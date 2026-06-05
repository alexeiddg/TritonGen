# Full Pipeline Grammar-Mode x C x P L1a n=1 Authorization Packet

## Packet Identity

packet_id: `FULL_PIPELINE_GRAMMAR_MODE_CP_L1A_N1_AUTHORIZATION_PACKET_V1`
packet_version: `0.2.1`
packet_type: draft authorization packet; not an execution packet
branch: `codex/l1a-packet-baseline-pin`
baseline_commit: `9aeb3c1 Audit grammar mode support promotion`
planning_baseline_commit: `9aeb3c1 Audit grammar mode support promotion`
code_support_commit: `c24fbaa Add local grammar-mode support for 12-cell L1a`
superseded_baseline_commit: `0cc43c1 Audit full pipeline launch packet promotion`
launch_packet: `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
created_at: 2026-06-05
baseline_pinned_at: 2026-06-05
status: `DRAFT_NOT_APPROVED`
code_support_status: `LOCAL_REPRESENTABILITY_READY`
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

The active planning baseline is the promoted handoff/audit commit
`9aeb3c1`. The executable local grammar-mode support required for the 12-cell
design is pinned separately to `c24fbaa`. The older `0cc43c1` baseline is
historical context only and is not sufficient for L1a authorization because it
predates the local grammar-mode support proof.

## Launch-Packet Dependency

This L1a packet depends on the patched launch packet selecting the 12-cell
`grammar_mode x C x P` design.

It must not be converted into an execution packet unless:

- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
  continues to name the 12-cell design as the active selected design;
- the old 8-cell design remains superseded for future execution;
- the output namespace uses
  `full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/`;
- local grammar-mode representability proof remains present on the target
  branch, including the 12-cell planner, row labeling, and analyzer grouping
  fixture tests.

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
| `template_upper_bound__c_off__p_off` | `template_upper_bound` | off | off |
| `template_upper_bound__c_on__p_off` | `template_upper_bound` | on | off |
| `template_upper_bound__c_off__p_on` | `template_upper_bound` | off | on |
| `template_upper_bound__c_on__p_on` | `template_upper_bound` | on | on |
| `task_agnostic__c_off__p_off` | `task_agnostic` | off | off |
| `task_agnostic__c_on__p_off` | `task_agnostic` | on | off |
| `task_agnostic__c_off__p_on` | `task_agnostic` | off | on |
| `task_agnostic__c_on__p_on` | `task_agnostic` | on | on |

## Grammar-Mode Mapping

Local representability now uses the repo-supported vocabulary. The execution
approval line remains unsigned until a future signer also supplies exact
runtime command/config, output paths, stop/spend limits, and preflight results.

| grammar_mode | required mapping before execution |
|---|---|
| `grammar_off` | `grammar_active=false`; `grammar_variant=null`; grammar file/hash/scope absent; rows label `grammar_mode=grammar_off` |
| `template_upper_bound` | `grammar_active=true`; `grammar_variant=template_upper_bound`; `grammar_path=cluster1/grammar/triton_kernel.gbnf`; claim scope `diagnostic_non_primary` |
| `task_agnostic` | `grammar_active=true`; `grammar_variant=task_agnostic`; `grammar_path=cluster1/grammar/triton_kernel_agnostic.gbnf`; claim scope `primary` |

Local code-support proof:

- `shared/factors/grammar_modes.py` defines the accepted values
  `grammar_off`, `template_upper_bound`, and `task_agnostic` and fail-closed
  binding checks against legacy `grammar_active`/`grammar_variant` metadata.
- `cluster3/planning/grammar_mode_matrix.py` returns exactly 12 local L1a
  cell specs with unique condition names and output namespace suffixes.
- `cluster3/results/dataclass.py` and `shared/eval/schema.py` can carry
  `grammar_mode` while preserving existing `grammar_active` fields.
- `shared/analysis/factorial.py` can normalize/group explicit
  `grammar_mode` values and distinguishes `template_upper_bound` from
  `task_agnostic`.
- `primary_grammar` is not an executable selector in this repo. Earlier
  wording maps to `template_upper_bound` only when referring to the diagnostic
  template-upper-bound grammar, not to the primary task-agnostic grammar.

## Required Runtime Fields Before Approval

```text
approval_source: not_approved
approval_timestamp: not_applicable
target_branch: unavailable_until_approval
target_commit: unavailable_until_review_commit
command: not_authorized
working_directory: /Users/alexeidelgado/Desktop/TritonGen
exact_condition_list: unavailable_until_approval_must_match_twelve_cell_matrix
output_jsonl_paths: unavailable_until_approval
observability_sidecar_paths: unavailable_until_approval
content_hash_sidecar_paths: unavailable_until_approval
model_id: unavailable_until_approval
model_revision: unavailable_until_approval
tokenizer_revision: unavailable_until_approval
decoding_config: unavailable_until_approval
seed_policy: unavailable_until_approval
kernel_class: elementwise_relu_or_explicit_future_value
problem_ids: unavailable_until_approval
dtype: fp32_or_explicit_future_value
shape_policy: unavailable_until_approval
repair_history_policy: agentic_transcript_v1_for_C_or_P_cells
grammar_file_hash_lock: unavailable_until_approval
observability_mode: best_effort_or_required_until_approval
observability_experiment_id: full_pipeline_grammar_mode_cp_factorial_v1
observability_run_id: unavailable_until_approval
mlflow_disposition: post_hoc_non_authoritative_unavailable_until_approval
max_rows: 12
max_generation_attempts: unavailable_until_approval
max_repair_attempts_per_row: unavailable_until_approval
max_wall_clock: unavailable_until_approval
max_estimated_cost: unavailable_until_approval
stop_on_first_infrastructure_failure: yes
overwrite_policy: fail_if_any_target_path_exists
resume_policy: no_resume_unless_explicitly_approved
post_run_validation_commands: unavailable_until_approval
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
positive-authorization scan over docs, audits, and .contracts, excluding generated preliminary-report previews
```

Additional required proof before approval:

- exact command/config is authorized for all 12 `grammar_mode`/C/P cells;
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
- any packet uses unsupported grammar-mode names such as `primary_grammar` or
  `task_agnostic_grammar` instead of `template_upper_bound` and
  `task_agnostic`;
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
