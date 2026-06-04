# S1 Analyzer Metric Registry Metadata Report

- Version: 1.0.1
- Date: 2026-06-04
- Branch: `codex/analyzer-metric-registry`
- Classification: `S1_REVIEW_PASS_COMMITTED`
- Scope: additive analyzer metadata and focused analyzer tests only

## Summary

S1 implemented the analyzer-output metadata contract from
`docs/17_structural_task_analyzer_metadata_implementation_spec.md` v0.1.3
without touching report-builder code, raw outputs, generated report assets,
result schemas, dependencies, lockfiles, Modal/GPU/generation runners, or
experiment artifacts.

The existing analyzer top-level output shape remains:

```text
metadata
condition_rates
cell_summaries
paired_comparisons
factorial_model
diagnostics
paper_tables
```

Existing consumers that read legacy top-level keys and legacy numeric summary
fields should continue to work. S1 adds metadata under existing `metadata` and
`diagnostics` containers and optional additive metric annotations on existing
`cell_summaries` and `paired_comparisons` rows.

## Files Changed

```text
shared/analysis/factorial.py
shared/tests/test_factorial_analysis.py
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
audits/structural_task_s1_analyzer_metric_registry_report.md
```

## Lease Status

The `analyzer_metric_registry` serialized-surface lease is active on
`codex/analyzer-metric-registry` for S1 review. The lease scope is limited to
additive analyzer metadata and focused analyzer tests.

## Metadata Fields Added

S1 now emits:

```text
metadata.outcome_family_schema_version
metadata.outcome_families
metadata.metric_registry_schema_version
metadata.metric_registry
metadata.metric_aliases
metadata.registry_provenance
```

Optional row annotations are added to current analyzer summary/comparison rows
when their `metric_name` is registered:

```text
outcome_family
level_gate
metric_gate
metric_display_name
metric_reportability
metric_current_status
```

## Diagnostics Fields Added

S1 now emits:

```text
diagnostics.level_reach_rates
diagnostics.feedback_activation
diagnostics.metric_availability
```

These diagnostics are summary-level and condition-bounded. They do not copy
per-row prompts, generated source, compile logs, feedback text, token IDs,
private eval details, secrets, or absolute user-home paths.

## Registry Entries

Required entries are present and validated before analyzer output is returned:

```text
level2_functional_success_rate
level1_compile_success_rate
grammar_valid_rate
syntax_valid_rate
terminal_failure_distribution
compile_pass_at_k
correctness_pass_at_k
repair_set_success_rate
eval_set_success_rate
benchmarkable_pass_at_k
```

Key status constraints:

- `level2_functional_success_rate` remains the task/functional primary metric.
- `level1_compile_success_rate` remains structural/code-surface and secondary.
- `syntax_valid_rate` is `planned_deferred` and not computed from mixed schemas.
- `benchmarkable_pass_at_k` is `future_only`.
- Gate-specific pass-at-k metric names are used internally; no new ungated
  report-facing pass-at-k metric is emitted.

The local registry validator fails closed for missing required fields, invalid
enums, unknown non-`x_` fields, alias collisions, canonical-name alias
collisions, current or reportable metrics marked `not_computed`, and ungated
pass-at-k aliases.

## Registry Provenance

`metadata.registry_provenance` includes:

```text
schema_version
generated_by_activity
software_entity
analyzer_version
source_docs
source_doc_versions
source_code
source_tests
source_artifact_paths
row_count
scale_tiers
```

Source artifact paths are sorted and deduplicated. Repo-local absolute paths
are converted to repo-relative paths; non-repo absolute paths are reduced to
safe basenames so analyzer metadata does not expose absolute home paths.

## Legacy Compatibility Proof

Focused tests verify that the current four-cell synthetic analyzer contract
keeps legacy behavior stable:

- top-level keys are unchanged;
- `metadata.response_variable`, `analysis_scope`, `reportable`, `scope_kind`,
  `scale_tiers`, `cells_populated`, and `cells_missing` are unchanged;
- `condition_rates` values for functional and compile success are unchanged;
- paired comparison labels, pair counts, success rates, and absolute lifts are
  unchanged;
- paper table keys remain present;
- new registry and outcome-family metadata are deterministic across repeated
  calls.

## JSON Safety Proof

Focused tests serialize the full analyzer result with strict JSON settings and
recursively reject NumPy scalar objects, pandas scalar/container objects, and
non-finite floats. The analyzer final JSON coercion also rejects pandas
containers and non-finite numeric values before returning output.

## Partial Design Behavior

Empty inputs still raise an analyzer error. A compile-only partial input can
emit structural/code-surface metadata and diagnostics, but remains
non-reportable and does not expose an available task/functional primary metric.

Feedback activation diagnostics separate:

- C-factor active rows;
- explicit C eligibility;
- proxy C eligibility;
- C loop-fired rows;
- P-factor active rows;
- P eligibility;
- P loop-fired rows;
- F0/F1/F2/F3 terminal failure counts.

The all-F0 C diagnostic case reports zero C-feedback eligibility and records
that F0 rows are not C-feedback eligible.

## Validation

Commands run:

```text
.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -q
```

Result:

```text
102 passed
```

Command run:

```text
.venv/bin/python -m pytest cluster3/tests/test_cluster3_schema.py cluster3/tests/test_cluster3_imports.py shared/tests/test_repair_history_policies.py -q
```

Result:

```text
170 passed
```

Command run:

```text
git diff --check
```

Result: passed.

Forbidden scope scan:

```text
git diff --name-only -- docs/preliminary_report outputs artifacts cluster1 cluster2 cluster3 pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock mlruns
```

Result: empty output.

Output mutation scan:

```text
git diff --name-only -- outputs artifacts
```

Result: empty output.

S1 code/test gated-metric language scan:

```text
rg scan for the literal ungated pass-at-k token and bare pass-at-k wording in shared/analysis/factorial.py and shared/tests/test_factorial_analysis.py
```

Result: no matches. Existing handoff-state guardrail text still contains legacy
cost/scope references from older O-stream sections and S2 scan instructions;
those were not introduced as S1 analyzer or test output language.

## Requirement Coverage

Covered by focused tests or direct implementation checks:

```text
S1-REQ-001 through S1-REQ-015
S1-REQ-019 through S1-REQ-026
S1-REQ-028
```

Preserved by existing analyzer behavior and regression coverage:

```text
S1-REQ-016
S1-REQ-017
S1-REQ-018
S1-REQ-027
```

## Review Closeout

S1 review passed locally. One validator gap found during review was fixed inside
S1 scope: reportable metrics marked `not_computed` now fail closed, with a
focused negative assertion added to the analyzer tests.

## Remaining Blockers

- S2 report builder work is outside S1 and must start only under the S1/S2
  handoff rule with its own branch and report-data-builder lease, unless a
  later packet scopes legacy-fallback-only or docs-prose-only work.
- S3 output refresh remains blocked pending a separate output-mutation approval
  packet.

## Next Step

After this S1 commit, start S2 only under the S1/S2 handoff rule in
`docs/17_structural_task_analyzer_metadata_implementation_spec.md`; do not
refresh analyzer outputs unless S3 receives a separate output-mutation approval
packet.
