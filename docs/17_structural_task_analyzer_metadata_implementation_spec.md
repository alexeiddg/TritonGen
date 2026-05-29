# Structural/Task Analyzer Metadata Implementation Spec

- Version: 0.1.2
- Date: 2026-05-28
- Status: implementation specification / no code changes, output mutation, Modal
  runs, n=5 runs, n=20 runs, paper-scale work, profiler, timing, speedup, or
  benchmark work authorized by itself
- Owner stream: S, structural/task analyzer and report metadata
- Primary planning source: `docs/14_structural_vs_task_outcome_reporting_plan.md`
- Orchestration source: `docs/15_experiment_change_orchestration_contract.md`
- Live state source: `docs/handoff/experiment_change_orchestration_state.md`
- Current analyzer surface: `shared/analysis/factorial.py`
- Current analyzer tests: `shared/tests/test_factorial_analysis.py`
- Current report-facing analyzer artifact:
  `outputs/analysis/factorial_2x2_preliminary.json`

## Purpose

This document defines the implementation contract for adding structural/task
outcome metadata to the factorial analyzer and report data path. It is meant to
be precise enough for an implementation agent to work on S0 through S3 without
changing scientific result-row schemas, rewriting historical artifacts, mixing
structural and functional claims, or accidentally authorizing new experiment
runs.

The implementation goal is additive metadata:

- identify every report-facing metric by outcome family;
- separate structural/code-surface quality from task/functional quality;
- keep `functional_success` as the current primary task outcome;
- keep `compile_success` as a secondary structural diagnostic;
- expose feedback activation and level-reach diagnostics;
- validate metric registry entries before report-facing use;
- keep emitted metadata JSON-safe and deterministic;
- preserve existing analyzer output keys for legacy consumers;
- prevent bare `pass@k` or unlabeled "pass" tables from mixing gates.

## Non-Goals

This spec does not:

- change Cluster 2 C from F2-only correctness feedback;
- change Cluster 3 P from F1_COMPILE-only compile feedback;
- make Cluster 2 repair F0, F1, or F3 rows;
- make Cluster 3 P repair F0, F1_RUNTIME, F2, or F3 rows;
- rewrite current JSONL artifacts;
- rewrite `outputs/analysis/factorial_2x2_preliminary.json` in S0 or S1;
- rename or remove existing analyzer keys such as `condition_rates`,
  `cell_summaries`, `paired_comparisons`, `factorial_model`, or `diagnostics`;
- turn Cluster 1 `compile_success=True` into `functional_success=True`;
- treat Cluster 1 `functional_success=False` as measured Level 2 failure;
- report a mixed-schema `syntax_valid_rate` without explicit compatible
  row-level syntax evidence;
- claim performance, speedup, profiler, timing, benchmark, or Level 4 results;
- approve Modal, GPU, paid, generation, n=5, n=20, or paper-scale runs.

## External Research Basis

Research was refreshed on 2026-05-28. The table below records the external
standards-level sources that informed this spec. Implementation agents should
prefer these primary sources if they need to re-verify the reasoning.

| Source | Relevant finding | Implementation implication |
|---|---|---|
| [JSON Schema 2020-12 specification](https://json-schema.org/specification) | JSON Schema is split into Core and Validation documents, and the latest meta-schema is 2020-12. | Version new metadata schemas explicitly; if a machine-readable schema is later exported, use JSON Schema 2020-12. |
| [JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation) | Validation keywords assert instance structure, while metadata keywords annotate data. Format validation is uneven unless format assertion is explicitly required. | Analyzer metadata must use explicit enums and required fields for critical semantics. Do not rely on weak format annotations for reportability decisions. |
| [JSON Schema core `$schema` and `$id`](https://json-schema.org/draft/2020-12/json-schema-core) | `$schema` identifies the dialect; `$id` identifies a schema resource by URI and is not necessarily a network locator. | Any future exported metric-registry schema should carry stable dialect and ID fields without implying network fetches. |
| [W3C PROV overview](https://www.w3.org/TR/prov-overview/) | PROV emphasizes object identity, attribution, processing steps, reproducibility, versioning, procedures, and derivation. | Analyzer metadata should record source entities, generating activity, analyzer version, source docs, and derived metric definitions. |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | PROV-DM is domain-agnostic and centered on entities, activities, agents, derivations, and annotations. | Use a lightweight provenance shape rather than a new dependency: source artifacts and docs are entities; `analyze_factorial` is the activity; the analyzer code/version is the agent-like software attribution. |
| [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) | Tabular data descriptions include fields, types, constraints, missing values, and foreign keys. | Treat `metric_registry` as a constrained field dictionary. Each metric needs explicit type, denominator, gate, status, and missing-value policy. |
| [FDA/ICH E9(R1) estimands guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9r1-statistical-principles-clinical-trials-addendum-estimands-and-sensitivity-analysis-clinical) | Clear descriptions of the treatment effect are needed to avoid misunderstanding; intercurrent-event handling must align with the scientific question. | Use an intent-to-treat analogue for primary condition comparisons and keep eligible-set/feedback-fired analyses diagnostic. This is a design analogy, not a clinical-trial claim. |
| [FDA E9(R1) final guidance PDF](https://www.fda.gov/media/108698/download) | The treatment-policy strategy uses the variable regardless of whether an intercurrent event occurs, while other strategies answer different questions. | Do not drop failed or ineligible rows from primary denominators just because feedback did not activate. Activation rates must sit beside, not replace, primary rates. |

## Local Research Basis

The local code and docs currently establish these facts:

| Source | Verified constraint |
|---|---|
| `docs/06_failure_taxonomy_and_eval_ladder.md` | Level 0/1/2 and F0/F1/F2/F3 semantics are already documented. C is F2-only. P is F1_COMPILE-only. |
| `docs/07_analysis_and_statistics.md` | Current preliminary analysis is a caveated 2^2 subset over none/G/C/G+C, with 714 loaded rows and explicit paper-scale analysis annotation. |
| `docs/14_structural_vs_task_outcome_reporting_plan.md` | The desired vocabulary is structural/code-surface, task/functional, and future benchmarkable/performance. |
| `shared/analysis/factorial.py` | Analyzer output already includes metadata, condition rates, cell summaries, paired comparisons, factorial model, diagnostics, and paper tables. |
| `shared/tests/test_factorial_analysis.py` | Existing tests enforce reportability, scale-tier handling, pairing identity, F3 policy, Cluster 1 functional normalization, and full/partial P-cell scope. |
| `outputs/analysis/factorial_2x2_preliminary.json` | Current report-facing analyzer JSON has `metadata.reportable=true`, `scope_kind=temporary_2^2_subset`, 714 rows, 177/180 G/G+C coverage, and five G+C `F3_EVAL_PIPELINE` rows. |
| `docs/preliminary_report/_build_data.py` | Current report data builder still performs local failure-mode and compile derivations, so S2 must migrate labels toward analyzer metadata after S1. |

## Resolved Analyzer Decisions

This spec resolves the metric decisions that were open in the live state file.

| ID | Resolution | Implementation effect |
|---|---|---|
| D-MET-01 | The first implementation is analyzer-output metadata only. Do not add a shared Python metric-registry module in S1. | Implement registry data inside `shared/analysis/factorial.py` or a private helper in that file. Extracting to a shared module requires a later spec or launch-packet update. |
| D-MET-02 | `syntax_valid_rate` must not be aggregated across mixed Cluster 1/2/3 schemas until every included row has compatible explicit syntax evidence and a shared `syntax_valid_definition_id`. | In S1, register `syntax_valid_rate` as `planned_deferred` unless a homogeneous explicit-evidence subset is implemented. Emit availability metadata rather than a misleading mixed rate. |
| D-MET-03 | Report HTML/data refresh waits for S1 metadata unless the change is docs-prose-only. | S2 starts only after S1 metadata shape is stable. Do not update report tables from hard-coded ambiguous labels before S1. |

## Rollout Summary

| Package | Scope | Output mutation | Modal/run behavior |
|---|---|---|---|
| S0 docs terminology | Align docs/prose terminology around outcome families. | No raw output mutation. | No runs. |
| S1 analyzer metadata | Add metric registry, outcome families, level reach, and feedback activation metadata. | No `outputs/` write unless S3 is explicitly authorized. | No runs. |
| S2 report builder/dashboard | Use S1 analyzer metadata for report labels and sections. | May update docs report assets only when scoped; no raw JSONL rewrite. | No runs. |
| S3 analyzer output rerun | Optional metadata-only analyzer output refresh. | Requires explicit output-mutation approval packet. | No Modal/generation runs. |

## Package Boundaries

### S0 Documentation Terminology

Allowed files:

```text
docs/06_failure_taxonomy_and_eval_ladder.md
docs/07_analysis_and_statistics.md
docs/09_preliminary_report_outline.md
docs/12_experiment_observability_plan.md
docs/14_structural_vs_task_outcome_reporting_plan.md
docs/preliminary_report/preliminary_report.md
docs/preliminary_report/README.md
```

Forbidden in S0:

```text
shared/analysis/*
shared/eval/*
cluster1/*
cluster2/*
cluster3/*
outputs/*
audits/*
```

S0 exit criteria:

- structural/code-surface and task/functional language is consistent;
- no doc says compile success proves numerical correctness;
- no doc says C repairs F0/F1/F3 or P repairs anything except F1_COMPILE;
- no new report claim is made beyond the current caveated 2^2 analyzer output.

### S1 Analyzer Metadata

Allowed files:

```text
shared/analysis/factorial.py
shared/tests/test_factorial_analysis.py
docs/17_structural_task_analyzer_metadata_implementation_spec.md
docs/handoff/experiment_change_orchestration_state.md
docs/handoff/document_version_registry.md
docs/handoff/agentic_document_hub.md
docs/00_project_map.md
```

Optional test fixture files may be added only under:

```text
shared/tests/fixtures/
```

Forbidden in S1:

```text
outputs/*
audits/*
cluster1/experiments/*
cluster2/experiments/*
cluster3/experiments/*
cluster1/results/*
cluster2/results/*
cluster3/results/*
docs/preliminary_report/_report_data.json
docs/preliminary_report/index.html
docs/preliminary_report/index.es.html
```

S1 must take the serialized-surface lease:

```text
surface: analyzer_metric_registry
expected files: shared/analysis/factorial.py, shared/tests/test_factorial_analysis.py
```

S1 may not add dependencies, change lockfiles, change Modal images, import GPU
or generation stacks into the analyzer import path, or mutate result artifacts.

### S2 Report Builder And Dashboard

Allowed files after S1 acceptance:

```text
docs/preliminary_report/_build_data.py
docs/preliminary_report/preliminary_report.md
docs/preliminary_report/README.md
docs/preliminary_report/index.html
docs/preliminary_report/index.es.html
shared/eval/reporting/*
shared/tests/test_reporting_tables.py
shared/tests/test_reporting_language.py
```

S2 must not refresh report data from a new analyzer output unless S3 is also
approved. If S2 changes generated docs assets, the handoff must include a
before/after diff review that confirms no new paper-scale, P-lift, C-lift,
pass@k, correctness-improvement, or performance claim was introduced.

### S3 Analyzer Output Rerun

S3 is not authorized by this spec alone. It requires a separate output-mutation
approval packet with:

```text
exact analyzer command:
input artifact paths:
input artifact registry versions:
output path:
overwrite/archive policy:
expected row count:
metadata-only vs logic-changing rerun:
primary-rate traceability check:
post-rerun audit/registry update plan:
```

S3 may write a new analyzer JSON path or archive-and-replace an old analyzer
JSON only if the packet explicitly approves that path. S3 must never rewrite raw
Cluster 1, Cluster 2, or Cluster 3 JSONL artifacts.

## Outcome Families

S1 must emit `metadata.outcome_family_schema_version` with value
`outcome_family_v1` and `metadata.outcome_families` with at least these entries:

| Key | Display name | Question answered | Level gates | Report role |
|---|---|---|---|---|
| `structural_code_surface` | Structural/code-surface quality | What improves generated-code structure, surface validity, grammar acceptance, compile, or launch? | Level 0 and Level 1 | secondary or diagnostic |
| `task_functional` | Task/functional quality | What improves numerical correctness under the Level 2 task harness? | Level 2 | primary for current C comparisons |
| `benchmarkable_performance` | Benchmarkable/performance quality | What would qualify a correct row for future performance evaluation? | Level 2 plus future Level 4 | future only |
| `mixed_diagnostic` | Mixed diagnostic | What explains failure movement or activation without being a primary outcome? | F0/F1/F2/F3 diagnostics | diagnostic only |

Rules:

- `compile_success` belongs to `structural_code_surface`.
- `functional_success` belongs to `task_functional`.
- `grammar_valid`, `gbnf_parse_valid`, `semantic_valid`, and
  `rejection_layer` belong to `structural_code_surface` or `mixed_diagnostic`
  depending on display context.
- `failure_code_distribution` and terminal failure movement are
  `mixed_diagnostic`.
- Performance/timing/speedup fields must remain `benchmarkable_performance`
  with `current_status=future_only` unless a later Level 4 contract authorizes
  them.

## Metric Registry Schema

S1 must emit:

```text
metadata.metric_registry_schema_version = "metric_registry_v1"
metadata.metric_registry = { ... }
```

`metadata.metric_registry` is keyed by canonical metric name. Each entry must
include these required fields:

| Field | Type | Required values or policy |
|---|---|---|
| `metric_name` | string | Must equal the object key. |
| `display_name` | string | Human label. For pass-at-k metrics, include the gate. |
| `aliases` | list[string] | Legacy or report aliases. Use empty list when none. |
| `outcome_family` | string | One of `structural_code_surface`, `task_functional`, `benchmarkable_performance`, `mixed_diagnostic`. |
| `level_gate` | string | `level0_parse_surface`, `level1_compile_launch`, `level2_correctness`, `level4_performance`, `failure_taxonomy`, or `not_applicable`. |
| `metric_gate` | string | Concrete gate such as `compile_success`, `functional_success`, `grammar_valid`, `terminal_failure`, or `future_performance`. |
| `response_variable` | string or null | Existing analyzer response variable when applicable. |
| `analysis_role` | string | `primary`, `secondary_diagnostic`, `diagnostic`, or `future_only`. |
| `denominator_unit` | string | `row_attempt`, `experimental_unit`, `matched_pair`, `sample_group`, or `not_applicable`. |
| `denominator_policy` | string | Plain English policy, including exclusions and caveats. |
| `numerator_policy` | string | Plain English success/count policy. |
| `attempt_policy` | string | How attempts are collapsed or retained. |
| `cluster_owner` | string | `cluster1`, `cluster2`, `cluster3`, `shared`, or `cross_cluster`. |
| `scope` | string | Current allowed scope. |
| `reportability` | string | `reportable_primary`, `reportable_secondary`, `diagnostic_only`, `not_reportable`, or `future_only`. |
| `current_status` | string | `current`, `current_with_caveats`, `planned_deferred`, `future_only`, or `legacy_alias`. |
| `required_source_fields` | list[string] | Fields needed to compute or verify the metric. |
| `evidence_policy` | string | `explicit_only`, `derived_with_policy`, `proxy_diagnostic`, or `not_computed`. |
| `missing_policy` | string | How missing fields are handled. |
| `forbidden_interpretations` | list[string] | Claims that must not be made from this metric. |
| `caveat` | string | Required caveat text or `none`. |
| `schema_version` | string | `metric_registry_v1`. |

Optional fields:

```text
definition_id
compatibility_notes
source_doc
source_code
source_tests
```

Unknown fields are allowed inside registry entries only if their names begin
with `x_`. Unknown top-level metadata keys are allowed because the analyzer
output remains additive, but new S1 tests must prove existing keys remain
readable.

## Registry Validator Contract

S1 must implement or expose a local validator for the analyzer-emitted
`metadata.metric_registry`. The validator may be a private helper inside
`shared/analysis/factorial.py`; it must not require a new dependency.

The validator must fail closed when:

- a required registry field is missing;
- `metric_name` does not equal the registry object key;
- `schema_version` is not `metric_registry_v1`;
- an enum field contains an unsupported value;
- `aliases`, `required_source_fields`, or `forbidden_interpretations` are not
  lists of strings;
- a non-empty alias appears in more than one metric entry;
- an alias equals a different metric's canonical `metric_name`;
- a pass-at-k metric or alias is report-facing but does not name its gate;
- a registry entry contains an unknown field that does not start with `x_`;
- a current or reportable metric has `evidence_policy=not_computed`;
- a `future_only` metric is marked `reportable_primary` or
  `reportable_secondary`.

S1 tests must call the validator directly or through analyzer execution. A
broken registry fixture must fail in tests before any report builder sees the
metadata.

## Schema Evolution Policy

`metric_registry_v1`, `outcome_family_v1`, and `registry_provenance_v1` are
append-only schemas.

Allowed without a schema-version bump:

- adding new metrics with complete registry entries;
- adding optional fields whose names start with `x_`;
- adding new `current_status=planned_deferred` or `future_only` metrics;
- adding new non-reportable diagnostics under `diagnostics`.

Requires a new schema version such as `metric_registry_v2`:

- renaming or removing required fields;
- changing enum meanings;
- changing denominator or attempt-policy semantics for an existing metric;
- changing reportability semantics;
- changing an existing metric's outcome family or level gate;
- allowing unknown non-`x_` fields inside registry entries.

S2 and later consumers must inspect schema versions. A consumer that sees an
unknown major schema must fail closed for paper-facing output or mark the
metadata as unsupported diagnostic-only.

## Metadata Size And Cardinality Limits

Analyzer metadata must remain summary-level. S1 must not introduce per-row
copies of registry entries, provenance objects, source text, prompts, compile
logs, feedback text, token IDs, private eval details, secrets, or absolute home
paths.

Limits for S1:

- `metadata.metric_registry` should contain only bounded metric definitions,
  not one entry per row, seed, kernel, or attempt;
- `metadata.registry_provenance.source_artifact_paths` must be deduplicated and
  sorted;
- `diagnostics.level_reach_rates` and `diagnostics.feedback_activation` may
  have one entry per populated condition, not per row;
- any exception to these limits requires a spec update or launch-packet
  escalation before implementation.

## JSON-Safe Numeric Contract

Analyzer metadata must be valid, portable JSON. S1 must not emit Python, NumPy,
or pandas scalar/null objects that rely on non-standard JSON serialization.

Rules:

- no `NaN`, `Infinity`, or `-Infinity`;
- no NumPy scalar objects in returned metadata;
- no pandas `NA`, `NaT`, `Timestamp`, `Series`, `Index`, or `DataFrame`
  objects in returned metadata;
- rates and confidence intervals must be finite JSON numbers or `null`;
- missing integer counts must be `null` only when the field is genuinely
  unavailable; otherwise use integer zero;
- sorted deterministic output must remain stable across repeated calls on the
  same input.

S1 must include a JSON round-trip test that serializes the full analyzer result
with strict JSON settings and rejects non-finite values before report builders
consume the result.

## Required Initial Registry Entries

S1 must include at least the following registry entries. It may include extra
entries only if each has the complete schema above.

| Metric | Required status | Required family | Required reportability |
|---|---|---|---|
| `level2_functional_success_rate` | `current_with_caveats` | `task_functional` | `reportable_primary` for current paper-scale annotated 2^2 output only |
| `level1_compile_success_rate` | `current_with_caveats` | `structural_code_surface` | `reportable_secondary` or `diagnostic_only` depending on table |
| `grammar_valid_rate` | `current_with_caveats` | `structural_code_surface` | `diagnostic_only` |
| `syntax_valid_rate` | `planned_deferred` unless homogeneous explicit syntax evidence is implemented | `structural_code_surface` | `not_reportable` until evidence-compatible |
| `terminal_failure_distribution` | `current_with_caveats` | `mixed_diagnostic` | `diagnostic_only` |
| `compile_pass_at_k` | `planned_deferred` or `current_with_caveats` only when gate-specific counts exist | `structural_code_surface` | `diagnostic_only` |
| `correctness_pass_at_k` | `planned_deferred` | `task_functional` | `not_reportable` until Level 2 sample groups exist |
| `repair_set_success_rate` | `planned_deferred` or `current_with_caveats` only with explicit repair-set evidence | `task_functional` | `diagnostic_only` |
| `eval_set_success_rate` | `planned_deferred` or `current_with_caveats` only with explicit eval-set evidence | `task_functional` | `diagnostic_only` |
| `benchmarkable_pass_at_k` | `future_only` | `benchmarkable_performance` | `future_only` |

Name policy:

- Existing analyzer metric names `level2_functional_success_rate` and
  `level1_compile_success_rate` must remain valid.
- New report-facing pass-at-k keys must use `_pass_at_k` internally and may
  display as `compile_pass@k`, `correctness_pass@k`, or
  `benchmarkable_pass@k`.
- No new metadata, table, or report builder output may emit bare `pass@k`
  without a gate.

## Computed-Value And Status Consistency

Metric registry status must agree with emitted values.

Rules:

- `current_status=future_only` must not have current computed rates,
  comparisons, or table rows except deferred placeholders explicitly marked
  `future_only`.
- `current_status=planned_deferred` must not have a populated report-facing
  rate. It may appear in `metadata.metric_registry` and
  `diagnostics.metric_availability` only.
- `reportability=not_reportable` must not appear in `paper_tables` unless the
  row is explicitly marked diagnostic or deferred.
- `reportability=diagnostic_only` may appear in diagnostic sections but must not
  drive headline, abstract, paper-primary, or claim-summary fields.
- `reportable_primary` is allowed only for metrics whose `analysis_role` is
  `primary`, whose evidence is available, and whose analyzer output remains
  `metadata.reportable=true`.

S1 must fail closed or mark output non-reportable if registry status and
computed output disagree.

## Analyzer Output Shape

S1 must preserve the existing top-level output shape:

```text
metadata
condition_rates
cell_summaries
paired_comparisons
factorial_model
diagnostics
paper_tables
```

S1 may add these fields:

```text
metadata.outcome_family_schema_version
metadata.outcome_families
metadata.metric_registry_schema_version
metadata.metric_registry
metadata.metric_aliases
metadata.registry_provenance
diagnostics.level_reach_rates
diagnostics.feedback_activation
diagnostics.metric_availability
```

S1 may add these optional fields to existing row objects in `cell_summaries` and
`paired_comparisons`:

```text
outcome_family
level_gate
metric_gate
metric_display_name
metric_reportability
metric_current_status
```

S1 must not remove, rename, or change semantics for existing fields. Existing
consumers that read only prior keys must keep working.

## Golden Compatibility Snapshot

S1 must add a deterministic compatibility snapshot test for the current
four-cell analyzer contract. The snapshot may be an inline expected object in
`shared/tests/test_factorial_analysis.py` or a fixture under
`shared/tests/fixtures/`.

The snapshot must prove:

- legacy top-level keys remain present;
- current numeric rates and paired-comparison counts remain unchanged;
- `metadata.reportable`, `analysis_scope`, `scope_kind`, `scale_tiers`, and
  populated/missing cells remain unchanged for the fixture;
- new metadata is deterministic under stable input ordering;
- registry keys are sorted or otherwise emitted in a deterministic order;
- no raw artifact output is needed to run the snapshot test.

If an intentional analyzer logic change later changes a legacy numeric value,
the snapshot update must be paired with an explicit analyzer-semantics review
and cannot be hidden inside an S1 metadata-only branch.

## Registry Provenance

S1 must emit `metadata.registry_provenance` with a lightweight provenance shape:

```text
{
  "schema_version": "registry_provenance_v1",
  "generated_by_activity": "analyze_factorial",
  "software_entity": "shared/analysis/factorial.py",
  "analyzer_version": "<existing ANALYZER_VERSION>",
  "source_docs": [
    "docs/14_structural_vs_task_outcome_reporting_plan.md",
    "docs/17_structural_task_analyzer_metadata_implementation_spec.md"
  ],
  "source_doc_versions": {
    "docs/14_structural_vs_task_outcome_reporting_plan.md": "0.1.0",
    "docs/17_structural_task_analyzer_metadata_implementation_spec.md": "0.1.2"
  },
  "source_code": [
    "shared/analysis/factorial.py"
  ],
  "source_tests": [
    "shared/tests/test_factorial_analysis.py"
  ],
  "source_artifact_paths": ["<sorted source_path values when available>"],
  "row_count": <rows_loaded>,
  "scale_tiers": "<existing metadata.scale_tiers>"
}
```

Rules:

- `source_artifact_paths` may be empty for synthetic in-memory tests.
- Paths must be repo-relative when possible.
- `source_doc_versions` must include every spec or planning doc that directly
  governs the registry shape. This is required because `docs/` is ignored by git
  in the current workspace and path-only provenance is insufficient.
- Do not record absolute user home paths in analyzer output.
- Do not record prompts, generated source, compile logs, private eval details,
  secrets, tokens, or raw feedback content in registry provenance.

## Denominator And Attempt Policy

Primary condition comparisons remain intent-to-treat analogues:

- include all generated rows in the condition denominator unless an existing
  analyzer policy explicitly excludes a diagnostic failure from a specific
  rate, such as the current F3 compile-rate denominator policy;
- do not drop F0/F1 rows merely because C did not activate;
- do not drop non-F1_COMPILE rows merely because P did not activate;
- eligible-set and loop-fired analyses are diagnostics, not replacements for
  primary condition comparisons.

Attempt collapse must remain compatible with current analyzer behavior:

- replay control rows use `attempt_index=0`;
- generated rows collapse repeated attempts by experimental unit using success
  if any attempt succeeds for the selected response variable;
- `attempts_observed` and `attempts_considered` remain diagnostic;
- if future repair-history policies change attempt semantics, the analyzer must
  group or quarantine mixed policies before reporting.

## Partial And Empty Design Behavior

S1 metadata must make partial designs predictable rather than half-reportable.

Rules:

- empty inputs remain an analyzer error and must not emit metadata;
- one-condition or two-condition inputs may emit diagnostic metadata only if the
  existing analyzer path accepts them for the requested scope;
- partial non-P designs must remain non-reportable for reduced factorial
  claims unless the current analyzer already permits the specific diagnostic;
- partial P designs must keep `scope_kind=partial_factorial` and must not imply
  full 2^3 completion;
- compile-only inputs may emit structural metadata but must not emit
  task/functional reportable-primary claims;
- `metadata.metric_registry` may still be emitted for diagnostic outputs, but
  metric entries whose evidence is unavailable must be reflected in
  `diagnostics.metric_availability`;
- S1 tests must cover at least one empty/rejected input and one accepted
  diagnostic partial input.

## Condition And Factor Conflict Contract

Canonical `condition` labels own factor semantics. When row booleans or nested
metadata conflict with `condition`, S1 must inherit the existing analyzer
fail-closed behavior or add an equally strict rejection before metadata is
reported.

Conflict examples:

- `condition="none"` with `grammar_active=True`;
- `condition="G"` with `grammar_active=False`;
- `condition="C"` with `compiler_feedback_active=False`;
- `condition="P"` or a P-containing condition with `compile_feedback_active`
  false when the field is present;
- a non-P condition carrying active P diagnostic fields;
- a non-C condition carrying active C-loop-fired evidence.

No metadata may "correct" these conflicts silently. The row must be rejected,
quarantined into diagnostic-only output, or marked non-reportable before any
paper-facing table is generated.

## Level Reach Diagnostics

S1 must emit `diagnostics.level_reach_rates` as a list of per-condition entries
or an object keyed by condition. The schema must be deterministic and tested.
Each condition entry must include:

```text
condition
n_rows
level0_parse_surface_evaluable_rows
level0_parse_surface_pass_rows
level0_parse_surface_pass_rate
level0_evidence_policy
level1_compile_launch_evaluable_rows
level1_compile_launch_reached_rows
level1_compile_launch_reached_rate
level1_evidence_policy
level2_correctness_evaluable_rows
level2_correctness_reached_rows
level2_correctness_reached_rate
level2_evidence_policy
unavailable_reasons
caveats
```

Evidence policies:

| Policy | Meaning |
|---|---|
| `explicit_only` | Computed only from explicit row fields for that level. |
| `derived_with_policy` | Derived from documented failure-code semantics. |
| `proxy_diagnostic` | Useful diagnostic but not reportable as a primary metric. |
| `not_available` | Not computed because compatible evidence is absent. |

Level reach rules:

- Level 0 syntax/surface pass may not be inferred from missing failure codes in
  legacy rows.
- Level 1 reached may be derived from `compile_success=True`,
  `functional_success=True`, F2 failure codes, explicit `level_reached >= 1`,
  or documented Level 1 evidence, but the evidence policy must say how.
- Level 2 reached may be derived from `functional_success` evidence, F2 failure
  codes, explicit `level_reached >= 2`, or documented eval-stage fields.
- F3 rows must remain visible and must not be converted into successful level
  reach unless independent evidence exists.

## Feedback Activation Diagnostics

S1 must emit `diagnostics.feedback_activation` with one entry per populated
condition. Each entry must include:

```text
condition
n_rows
c_factor_active
p_factor_active
c_feedback_eligible_rows
c_feedback_eligibility_proxy_rows
c_feedback_loop_fired_rows
c_feedback_evidence_policy
p_feedback_eligible_rows
p_feedback_loop_fired_rows
p_feedback_evidence_policy
level2_reached_rows
level1_compile_failure_rows
f0_rows
f1_rows
f2_rows
f3_rows
caveats
```

C eligibility:

- C can be eligible only when the C factor is active and the initial failure is
  an F2 correctness failure after Level 2 reached.
- Explicit initial-failure or repair-trace evidence wins.
- A terminal F2 code without initial-failure evidence may be counted only as
  `c_feedback_eligibility_proxy_rows`, not as authoritative loop-fired
  evidence.
- F0, F1, and F3 rows are not C-eligible.

P eligibility:

- P can be eligible only when the P factor is active and the initial failure is
  `F1_COMPILE`.
- `F1_RUNTIME`, F0, F2, and F3 rows are not P-eligible.
- Explicit `p_repair_attempted`, P trace summary, or P attempt-count evidence
  is required for `p_feedback_loop_fired_rows`.

Current C artifact rule:

```text
C feedback eligibility = 0/180 when all current C rows are F0_PARSE.
```

That statement is required whenever the current C artifact is summarized. It is
more accurate than saying correctness feedback was exercised 180 times.

## Syntax Validity Policy

`syntax_valid_rate` is high-risk because current artifacts mix legacy and
current schemas. S1 must follow this policy:

- Do not compute a cross-cluster `syntax_valid_rate` from absence of
  `F0_PARSE`.
- Do not compute a cross-cluster `syntax_valid_rate` from `compile_success`.
- Do not merge parser/surface/grammar/semantic-validator evidence under a
  single syntax label.
- Do not report one mixed aggregate unless every row has a compatible explicit
  evidence field and the same `syntax_valid_definition_id`.

Allowed S1 behavior:

- register `syntax_valid_rate` as `planned_deferred`;
- emit `diagnostics.metric_availability.syntax_valid_rate.status =
  "not_available_mixed_schema"` for mixed current inputs;
- emit per-condition or per-schema-family availability diagnostics only when
  evidence is explicit.

Future formula, once compatible evidence exists:

```text
syntax_valid_rate =
  rows with explicit Python syntax parse success
  / rows with explicit Python syntax parse evidence
```

This formula is not the same as grammar acceptance, semantic validation,
compile success, or functional success.

## Cluster 1 Functional Evidence Policy

Cluster 1 none and G rows remain compile-only. S1 must expose that explicitly:

- `functional_success=False` for Cluster 1 analyzer normalization means
  unproven for Level 2, not measured numerical failure.
- Registry entries for `level2_functional_success_rate` must include a caveat
  that Cluster 1 controls are normalized false/unproven under current analysis
  policy.
- Diagnostics should include a by-condition evidence policy if practical:

```text
functional_success_evidence_policy:
  none: normalized_unproven_cluster1_compile_only
  G: normalized_unproven_cluster1_compile_only
  C: measured_or_derived_level2_cluster2
  G+C: measured_or_derived_level2_cluster2
```

If that exact object is deferred, the caveat must still appear in
`metric_registry.level2_functional_success_rate.caveat`.

## Mixed Policy Guardrails

The analyzer must fail closed or mark output non-reportable when policy fields
exist and are mixed in a way that changes interpretation.

Policy fields to recognize when present:

```text
repair_history_policy
observability_policy
grammar_variant
grammar_claim_scope
scale_tier
syntax_valid_definition_id
metric_registry_schema_version
```

Minimum S1 behavior:

- preserve existing scale-tier rejection behavior;
- preserve existing P-pair grammar-variant mismatch rejection behavior;
- if `repair_history_policy` exists and has more than one non-missing value
  within a condition comparison, add an interpretation flag or reject before
  reportable output;
- if `syntax_valid_definition_id` differs across rows, do not compute an
  aggregate `syntax_valid_rate`;
- unknown policy labels must not be silently promoted to paper-reportable.

## F3 And Coverage Guardrails

S1 must preserve the current F3 and coverage semantics:

- `F3_EVAL_PIPELINE` is not `functional_success`;
- `F3_EVAL_PIPELINE` is not `compile_success` unless independent Level 1 or
  Level 2 evidence exists;
- F3 rows remain excluded from compile-success rate denominators in condition
  summaries under the existing policy;
- F3 rows remain `compile_success=False` in matched-pair analysis when
  independent compile-pass evidence is absent;
- G and G+C 177/180 coverage remains visible;
- missing G/G+C rows must not be silently described as complete coverage.

## Report Builder Contract

S2 report builders must consume S1 metadata instead of hard-coding ambiguous
labels where practical.

Report sections should be ordered:

```text
Structural/code-surface outcomes
Task/functional outcomes
Feedback activation diagnostics
Future benchmarkable/performance outcomes
```

Report table rules:

- Do not put compile and functional success under one unlabeled "pass" heading.
- Every pass-at-k display must include the gate.
- `compile_success` tables must say structural/code-surface or compile/launch.
- `functional_success` tables must say task/functional or Level 2 correctness.
- Feedback activation tables must separate eligible rows from loop-fired rows.
- Current C rows must show zero C-feedback eligibility for the all-F0 C
  artifact.
- Future performance rows must remain deferred unless a later Level 4 contract
  authorizes performance evidence.

### Display String Safety

Metric display text, caveats, condition labels, aliases, and registry-provided
strings are data, not trusted HTML. S2 must escape display strings before
rendering into HTML or use a strict allowlist of static labels.

Rules:

- no registry string may be inserted as raw HTML;
- report builders must escape `<`, `>`, `&`, quotes, and apostrophes where the
  target renderer requires it;
- tests must include a malicious or malformed display string fixture and prove
  it is escaped or rejected;
- Markdown/prose outputs must not turn registry strings into links or HTML
  unless the string came from a static report template.

### Localization Parity

If S2 edits or regenerates both `docs/preliminary_report/index.html` and
`docs/preliminary_report/index.es.html`, structural/task labels and metric
gates must stay semantically aligned across both outputs.

Rules:

- if English and Spanish report assets are both in scope, parity must be
  reviewed before handoff;
- if only one locale is updated, the handoff must record the other locale as an
  explicit deferral and block citation-ready bilingual report use;
- localized labels must preserve gate words such as compile/launch,
  task/functional, Level 2 correctness, diagnostic, deferred, and future-only;
- localization must not soften caveats around C all-F0 non-activation,
  Cluster 1 unproven functional evidence, F3 policy, or 177/180 coverage.

### Legacy Analyzer Fallback

S2 must handle analyzer JSON files that lack `metadata.metric_registry` or
`metadata.outcome_families`. This is required because the current registered
`outputs/analysis/factorial_2x2_preliminary.json` predates S1 metadata.

Fallback behavior:

- mark metadata status as `legacy_metadata_unavailable`;
- use only the explicit legacy fields already present in the analyzer JSON;
- label compile metrics as structural/code-surface and functional metrics as
  task/functional using the spec's conservative mapping;
- do not invent `syntax_valid_rate`, feedback activation counts, or level-reach
  rates from missing metadata;
- do not make paper-facing claims that require S1 metadata;
- include a visible caveat when a report section is rendered from legacy
  analyzer metadata.

### S1 To S2 Handoff Rule

S2 may start only when one of these is true:

1. S1 has landed and the report builder consumes an analyzer output with
   accepted S1 metadata.
2. S3 has been explicitly approved and produced a refreshed analyzer output
   with accepted S1 metadata.
3. S2 is intentionally limited to legacy-fallback behavior and the handoff
   states that no new S1-only diagnostics will be displayed.

The S2 handoff must name which path it used. If path 3 is used, S2 must not
present feedback activation, level-reach, syntax-validity, or metric-registry
tables as if they were computed from the current analyzer JSON.

## Requirement IDs

S1 implementation must map these requirement IDs to tests or explicit manual
checks in its handoff.

| ID | Requirement |
|---|---|
| S1-REQ-001 | Emit `metadata.outcome_family_schema_version` and `metadata.outcome_families`. |
| S1-REQ-002 | Emit `metadata.metric_registry_schema_version` and complete `metadata.metric_registry` entries for required metrics. |
| S1-REQ-003 | Preserve existing analyzer top-level keys and legacy field meanings. |
| S1-REQ-004 | Add outcome metadata to cell summaries and paired comparisons without removing existing keys. |
| S1-REQ-005 | Mark `compile_success` as structural/code-surface and secondary/diagnostic. |
| S1-REQ-006 | Mark `functional_success` as task/functional and current primary. |
| S1-REQ-007 | Mark Cluster 1 functional evidence as normalized unproven, not measured Level 2 failure. |
| S1-REQ-008 | Emit feedback activation diagnostics with separate eligible, proxy-eligible, and loop-fired counts. |
| S1-REQ-009 | Emit level-reach diagnostics with evidence policies and unavailable reasons. |
| S1-REQ-010 | Preserve current F3 compile-rate denominator and matched-pair policy. |
| S1-REQ-011 | Preserve 177/180 G/G+C coverage warnings and missing-row visibility. |
| S1-REQ-012 | Do not compute mixed-schema `syntax_valid_rate`; emit availability metadata instead. |
| S1-REQ-013 | Do not emit bare report-facing `pass@k` without a gate. |
| S1-REQ-014 | Keep current reportability and scale-tier behavior unchanged. |
| S1-REQ-015 | Emit registry provenance without absolute home paths, prompts, generated source, compile logs, secrets, private eval data, or raw feedback. |
| S1-REQ-016 | Recognize mixed policy fields when present and fail closed or mark non-reportable before paper-facing output. |
| S1-REQ-017 | Add negative tests for invalid/mixed metric evidence where implemented. |
| S1-REQ-018 | Require no new dependencies, no Modal import, no output mutation, and no runner changes. |
| S1-REQ-019 | Validate metric registry entries with a fail-closed local validator before report-facing use. |
| S1-REQ-020 | Add a deterministic golden compatibility snapshot for the legacy four-cell analyzer contract. |
| S1-REQ-021 | Preserve schema-evolution rules for `metric_registry_v1`, `outcome_family_v1`, and `registry_provenance_v1`. |
| S1-REQ-022 | Keep analyzer metadata summary-level with bounded cardinality and no per-row source/log/prompt/private data. |
| S1-REQ-023 | Emit only JSON-safe finite metadata values; reject `NaN`, infinities, NumPy scalars, and pandas null/object leakage. |
| S1-REQ-024 | Reject duplicate metric aliases and aliases that collide with another metric's canonical name. |
| S1-REQ-025 | Keep metric status/reportability consistent with emitted computed values and paper-table use. |
| S1-REQ-026 | Define and test metadata behavior for empty, partial, partial-P, and compile-only inputs. |
| S1-REQ-027 | Fail closed or mark non-reportable when condition labels conflict with factor booleans or active C/P diagnostics. |
| S1-REQ-028 | Include governing document versions in `metadata.registry_provenance.source_doc_versions`. |

S2 implementation must map these requirement IDs to tests or explicit manual
checks in its handoff.

| ID | Requirement |
|---|---|
| S2-REQ-001 | Handle analyzer JSON without `metric_registry` using `legacy_metadata_unavailable` fallback behavior. |
| S2-REQ-002 | State whether S2 consumed accepted S1 metadata, an approved S3 refreshed output, or legacy fallback only. |
| S2-REQ-003 | Do not display S1-only diagnostics from legacy analyzer JSON. |
| S2-REQ-004 | Escape or reject registry-sourced display strings before HTML rendering. |
| S2-REQ-005 | Preserve localization parity across English and Spanish report assets or record a blocking deferral. |

## Required Tests

S1 must add or update focused tests under
`shared/tests/test_factorial_analysis.py`. Suggested test names:

```text
test_analyze_factorial_emits_outcome_family_metadata
test_analyze_factorial_emits_complete_metric_registry
test_metric_registry_preserves_existing_2x2_output_contract
test_compile_success_metadata_is_structural_secondary
test_functional_success_metadata_is_task_primary
test_cluster1_functional_metadata_is_unproven_not_measured_failure
test_feedback_activation_reports_c_all_f0_as_zero_eligible
test_feedback_activation_separates_proxy_eligible_from_loop_fired
test_level_reach_rates_include_evidence_policy_and_unavailable_reasons
test_syntax_valid_rate_is_unavailable_for_mixed_legacy_schemas
test_no_bare_pass_at_k_metric_is_emitted
test_registry_provenance_uses_repo_relative_paths
test_metric_registry_validator_rejects_missing_required_fields
test_metric_registry_validator_rejects_invalid_enums
test_metric_registry_validator_rejects_bare_pass_at_k_aliases
test_analyzer_metadata_golden_contract_is_stable
test_metric_registry_schema_version_policy_is_enforced
test_metric_registry_metadata_stays_summary_level
test_report_builder_handles_legacy_analyzer_without_registry
test_analyzer_metadata_json_round_trip_rejects_non_finite_values
test_metric_registry_validator_rejects_alias_collisions
test_metric_registry_status_matches_computed_values
test_partial_and_empty_design_metadata_is_rejected_or_diagnostic
test_condition_factor_conflicts_fail_closed_before_metadata
test_registry_provenance_includes_document_versions
test_report_builder_escapes_registry_display_strings
test_report_builder_checks_locale_parity_or_blocks
```

Compatibility tests must assert that, for `_four_cell_rows()`:

- `metadata.response_variable` is unchanged;
- `metadata.analysis_scope` is unchanged;
- `metadata.reportable` is unchanged;
- `metadata.cells_populated` and `metadata.cells_missing` are unchanged;
- `condition_rates` values for `functional_success` and `compile_success` are
  unchanged;
- paired comparison count, labels, rates, and pair counts are unchanged;
- existing paper table keys remain present.

Negative tests must cover at least:

- mixed or unavailable `syntax_valid_definition_id` prevents
  `syntax_valid_rate` aggregation;
- a metric registry entry missing a required field fails the local builder or
  validation helper;
- invalid metric-registry enum values fail validation;
- unknown non-`x_` registry fields fail validation;
- duplicate aliases and cross-metric alias collisions fail validation;
- bare pass-at-k aliases are not emitted as report-facing metric names;
- non-finite numeric values fail strict JSON serialization or metadata
  validation;
- deferred/future/not-reportable metrics cannot appear as report-facing
  computed values;
- conflicting factor booleans cannot produce reportable metadata;
- C feedback does not count F0/F1/F3 rows as eligible;
- P feedback does not count F0/F1_RUNTIME/F2/F3 rows as eligible when P rows
  are present in synthetic fixtures.

Recommended targeted command:

```bash
pytest shared/tests/test_factorial_analysis.py -k "metric_registry or outcome_family or feedback_activation or level_reach or syntax_valid or four_cell"
```

Recommended broader command before handoff:

```bash
pytest shared/tests/test_factorial_analysis.py shared/tests/test_analyzer_cluster3.py shared/tests/test_reporting_tables.py shared/tests/test_reporting_language.py
```

If the broader command hits the known Cluster 1 docs-lock failure indirectly,
record the exact failure and confirm no S1-targeted test failed first.

## Acceptance Criteria

S1 is complete only when:

- all S1 requirement IDs are mapped to tests or explicit deferrals;
- additive metadata appears in analyzer output for synthetic four-cell tests;
- current numeric results are unchanged for existing four-cell fixtures;
- old consumers can still read prior analyzer keys;
- mixed-schema `syntax_valid_rate` is unavailable rather than misleading;
- feedback activation makes C all-F0 non-activation explicit;
- Cluster 1 functional status is visibly unproven;
- metric-registry validation fails closed for malformed entries;
- a golden compatibility snapshot proves legacy numeric output is unchanged;
- schema-version handling is explicit and tested;
- metadata remains summary-level and bounded;
- metadata is strict JSON-safe with no non-finite or library-specific scalar
  leakage;
- alias collisions are rejected;
- metric status and computed output are consistent;
- partial and empty design behavior is explicit;
- condition/factor conflicts fail closed or become non-reportable before
  metadata is used;
- registry provenance includes governing document versions;
- no raw outputs, run artifacts, Modal code, result schemas, or report HTML are
  touched;
- docs, registry, hub, and state are updated with the spec and D-MET decisions.

S2 is complete only when:

- report data reads S1 metadata for family/gate labels where practical;
- legacy analyzer JSON without S1 metadata is handled through
  `legacy_metadata_unavailable`;
- the handoff states whether S2 used accepted S1 metadata, an approved S3
  refreshed output, or legacy fallback only;
- registry-sourced display strings are escaped or rejected before HTML render;
- English and Spanish report assets remain semantically aligned when both are
  touched, or localization is recorded as a blocking deferral;
- no table mixes structural and functional metrics under one unlabeled heading;
- generated docs/report assets are diff-reviewed for unsupported claims;
- S2 does not refresh analyzer output unless S3 was explicitly approved.

S3 is complete only when:

- the output-mutation approval packet exists;
- the analyzer command is reproducible;
- row count and reportability metadata match expectations;
- primary rates and paired comparisons are traceable to the same registered
  input artifacts unless a new lineage was explicitly introduced;
- artifact registry or audit notes are updated as required.

## Agent Launch Packet Addendum

Any S1 implementation launch packet must include:

```text
component spec: docs/17_structural_task_analyzer_metadata_implementation_spec.md v0.1.2
serialized surface: analyzer_metric_registry
required decisions: D-MET-01 resolved, D-MET-02 resolved, D-MET-03 resolved
allowed output mutation: no
allowed Modal/API/network/dependency download: no
default-invariance proof required: yes
fixture-first proof required: yes
independent review required: yes
negative tests required: yes
```

## Explicit Claim Boundaries

The metadata added by this spec may support clearer reporting language. It must
not be used to claim:

- full 2^3 completion;
- P-lift, C-lift beyond current paired C comparisons, or repair-memory lift;
- n=20 Cluster 3 evidence;
- paper-scale Cluster 3 evidence;
- performance, timing, profiler, speedup, or benchmark results;
- correctness improvement from compile-only evidence;
- C feedback effectiveness for rows that never reached Level 2;
- P feedback effectiveness for rows that never reached F1_COMPILE;
- syntax validity across mixed schemas without explicit compatible evidence.
