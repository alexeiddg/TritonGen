# Grammar-Mode Code Support Audit Report

- Date: 2026-06-05
- Branch: `codex/full-pipeline-l1-smoke-dev-approval-packet`
- Baseline: `205c86a Patch full pipeline packet to 12-cell L1a draft`
- Scope: audit/recon only
- Classification: `GRAMMAR_MODE_CODE_SUPPORT_AUDIT_BLOCKED_IMPLEMENTATION_REQUIRED`

## Executive Summary

The current repo cannot yet run, label, and analyze the patched 12-cell
`grammar_mode x C x P` L1a design without implementation changes.

Current code supports a binary grammar activation path plus a two-value
`grammar_variant` selector:

- `template_upper_bound` -> `cluster1/grammar/triton_kernel.gbnf`
- `task_agnostic` -> `cluster1/grammar/triton_kernel_agnostic.gbnf`

The launch packet's new `grammar_mode` values are not first-class code values.
There is no current `grammar_mode` CLI flag, row field, row-schema validator,
condition taxonomy, analyzer grouping dimension, report table column, or MLflow
index key for `grammar_off`, `primary_grammar`, and
`task_agnostic_grammar`.

L1a remains blocked. The smallest safe next step is a local implementation patch
with fixture tests, not an execution packet.

## Inspected Files And Commands

Commands run:

```bash
git status --short --branch
sed -n '1,520p' /Users/alexeidelgado/.codex/attachments/0d63f380-272c-4c9e-91d7-e903b6e0d4ff/pasted-text.txt
find cluster1 cluster2 cluster3 shared docs .contracts -maxdepth 5 -type f | sort | rg "grammar|gbnf|xgrammar|constrained|task_agnostic|primary"
rg -n "triton_kernel_agnostic|task_agnostic|primary grammar|primary_grammar|grammar_mode|grammar_active|grammar file|gbnf|xgrammar|constrained decoding" cluster1 cluster2 cluster3 shared docs .contracts audits --glob '!outputs/**' --glob '!artifacts/**' --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
rg -n "grammar_active|grammar_mode|condition|result row|GenerationResult|row_schema|jsonl|append|logger|repair_history_policy|agentic_transcript_v1" cluster3 shared docs .contracts --glob '!outputs/**' --glob '!artifacts/**'
rg -n "argparse|click|typer|condition|grammar_active|grammar_mode|constrained|xgrammar|run_matrix|matrix|n_per|num_samples|output_path|sidecar|observability|repair_history_policy" cluster3 shared docs .contracts --glob '!outputs/**' --glob '!artifacts/**'
rg -n "grammar_active|grammar_mode|condition|factor|factorial|groupby|paired_comparisons|cell_summaries|metric_registry|outcome_family" shared docs cluster3 audits --glob '!outputs/**' --glob '!artifacts/**' --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
rg -n "mlflow|tracking|run_context|log_param|log_metric|log_artifact|condition|grammar_active|grammar_mode|experiment_id|run_id|artifact" shared cluster3 docs audits --glob '!outputs/**' --glob '!artifacts/**' --glob '!mlruns/**'
env LC_ALL=C LANG=C shasum -a 256 cluster1/grammar/triton_kernel.gbnf cluster1/grammar/triton_kernel_agnostic.gbnf
```

Primary evidence files inspected:

- `shared/generation_metadata.py`
- `cluster1/generation/grammar_variants.py`
- `shared/modal_harness/schemas.py`
- `shared/modal_harness/generation.py`
- `cluster3/constants.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/results/dataclass.py`
- `cluster3/results/logger.py`
- `cluster3/replay/no_p_pairs.py`
- `shared/factors/cells.py`
- `shared/factors/config.py`
- `shared/factors/registry.py`
- `shared/analysis/factorial.py`
- `shared/eval/reporting/grammar_language.py`
- `shared/eval/reporting/tables.py`
- `shared/tracking/client.py`
- `shared/tracking/mapping.py`
- `shared/observability/schema.py`
- `shared/observability/logger.py`

## Grammar Files And Modes Found

| Code value | File | SHA256 | Current claim scope |
|---|---|---|---|
| `template_upper_bound` | `cluster1/grammar/triton_kernel.gbnf` | `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82` | `diagnostic_non_primary` |
| `task_agnostic` | `cluster1/grammar/triton_kernel_agnostic.gbnf` | `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32` | `primary` |

Evidence:

- `shared/generation_metadata.py:23-38` defines `GrammarVariant` as
  `template_upper_bound` or `task_agnostic`, maps both to grammar files, and
  marks `task_agnostic` as `primary`.
- `cluster1/generation/grammar_variants.py:15-31` re-exports the same mapping
  for runtime grammar-path selection.
- `docs/02_methodology_cluster1.md:74-85` states task-agnostic G is primary and
  template upper-bound G is diagnostic/reference only.

No code-level grammar value named `primary_grammar` or
`task_agnostic_grammar` was found outside planning docs. The nearest executable
values are `task_agnostic` and `template_upper_bound`.

## Grammar-Mode Selection Support

Current support is partial and incompatible with the patched 12-cell packet.

Supported today:

- `grammar_off` can be represented indirectly only by conditions without `G`,
  which set `grammar_active=False`.
- an active grammar can be selected through `--grammar-variant`.
- `--grammar-variant` choices are the keys of `GRAMMAR_PATHS_BY_VARIANT`, namely
  `template_upper_bound` and `task_agnostic`.

Missing today:

- no `--grammar-mode` CLI field;
- no accepted code values `grammar_off`, `primary_grammar`, or
  `task_agnostic_grammar`;
- no explicit mapping from `primary_grammar` to a distinct grammar file;
- no way to represent a `primary_grammar` stratum separately from the current
  `task_agnostic` primary variant unless a future patch intentionally aliases
  them and documents that the 12-cell design collapses to fewer distinct active
  grammar implementations.

Evidence:

- `cluster3/experiments/run_cluster3_modal.py:145-172` has
  `Cluster3RunnerConfig.grammar_variant`, defaulting to `task_agnostic`.
- `cluster3/experiments/run_cluster3_modal.py:786-801` exposes
  `--condition` and `--grammar-variant`, not `--grammar-mode`.
- `cluster3/experiments/run_cluster3_modal.py:1399-1401` and `1618-1620` pass
  `config.grammar_variant` only when the translated Cluster 2 generation
  condition is `G+C`.

## Row/Schema Support

Current row support is partial and L1a-blocking.

Cluster 3 rows contain:

- top-level `condition`;
- top-level `grammar_active`;
- top-level `p_history_policy`;
- nested `generated_metadata.grammar_variant`;
- nested `generated_metadata.grammar_path`;
- nested `generated_metadata.grammar_sha`;
- nested `generated_metadata.grammar_claim_scope`.

Cluster 3 rows do not contain:

- top-level `grammar_mode`;
- nested `generated_metadata.grammar_mode`;
- 12-cell condition ids such as `grammar_off__c_on__p_on`.

`grammar_mode` is not safely derivable for the patched 12-cell design because
`primary_grammar` and `task_agnostic_grammar` are not mapped to unambiguous code
values. Deriving `grammar_off` from `grammar_active=False` is safe, but deriving
the two active grammar modes is not.

Evidence:

- `cluster3/results/dataclass.py:260-308` defines the top-level
  `Cluster3EvalRow` fields and includes `grammar_active` but no `grammar_mode`.
- `cluster3/results/dataclass.py:90-145` defines
  `Cluster3GeneratedRowMetadata` with grammar variant/path/hash/scope fields but
  no `grammar_mode`.
- `cluster3/results/dataclass.py:364-366` hard-codes `grammar_active` to
  `condition in {"G+P", "G+C+P"}`.
- `cluster3/results/dataclass.py:752-783` requires grammar metadata for
  `G+P` and `G+C+P` and requires non-G Cluster 3 rows to remain grammar-free.
- `cluster3/experiments/run_cluster3_modal.py:1867` emits
  `grammar_active=condition in {"G+P", "G+C+P"}`.

Adding an authoritative `grammar_mode` label requires a row schema/runtime
change or a separate audited derived artifact before L1a can be interpreted as a
12-cell grammar-mode design.

## Analyzer/Report Support

Analyzer/report support is not sufficient for 12-cell grammar-mode claims.

Current analyzer behavior:

- validates canonical conditions only:
  `none`, `G`, `C`, `P`, `G+C`, `G+P`, `C+P`, and `G+C+P`;
- derives boolean factors including `grammar_active`;
- groups cell outcomes and paper table summaries by `condition`;
- can use `grammar_variant` only for condition display labels.

Missing today:

- no accepted `grammar_mode` factor;
- no grouping by `grammar_mode`;
- no 12-cell condition-id taxonomy;
- no C/P interaction analysis conditional on `grammar_mode`;
- no report table column for `grammar_mode`.

Evidence:

- `shared/analysis/factorial.py:52-70` defines eight canonical G/C/P
  conditions and boolean factor columns.
- `shared/analysis/factorial.py:1368-1392` normalizes rows to canonical
  condition labels or derives `G/C/P` from booleans.
- `shared/analysis/factorial.py:1753-1818` derives boolean
  `grammar_active`, `compiler_feedback_active`, and P flags from the condition.
- `shared/analysis/factorial.py:3502-3534` builds outcome cells grouped by
  `condition`, kernel, dtype, and base seed.
- `shared/analysis/factorial.py:3537-3575` builds summaries at `condition` and
  `condition_kernel_dtype` levels.
- `shared/analysis/factorial.py:3968-3975` uses `grammar_variant` only for
  display labels.
- `shared/eval/reporting/tables.py:174-216` renders condition-centric tables.

The analyzer should fail closed on current 12-cell labels until a fixture-backed
implementation patch extends the taxonomy.

## MLflow/Tracking Support

MLflow/tracking support is partial and non-authoritative.

Current support:

- tracking is no-op unless explicitly enabled and `mlflow` is importable;
- `run_config_to_params` logs CLI args as `arg.*`, which would include
  `arg.grammar_variant` for current Cluster 3 runs;
- row metrics include numeric `c3.grammar_active`;
- factorial summary metrics are keyed by condition.

Missing today:

- no `grammar_mode` run tag;
- no `grammar_mode` MLflow metric or index key;
- no post-hoc importer implementation for the new
  `full_pipeline_grammar_mode_cp_factorial_v1` namespace;
- no child-run/index grouping by `grammar_mode`.

Evidence:

- `shared/tracking/client.py:1-11` states tracking is no-op-safe and must not
  break experiment runs.
- `shared/tracking/client.py:111-160` opens a run context only when enabled.
- `shared/tracking/mapping.py:118-149` maps run config and CLI args to params.
- `shared/tracking/mapping.py:102-116` maps Cluster 3 row metrics including
  `grammar_active` but not `grammar_mode`.
- `shared/tracking/mapping.py:220-257` maps factorial summaries by condition.
- `shared/tracking/README.md:100` states JSONL files under `outputs/` remain
  the source of truth and MLflow is additive.

## 12-Cell Launch Expressibility

The current orchestration cannot express all 12 cells as the patched packet
requires.

Cluster 3 can currently run only the four P-generation conditions:

- `P`
- `G+P`
- `C+P`
- `G+C+P`

`--condition all` expands to those four conditions. It does not produce the
no-P cells needed for `c_off/p_off`, `c_on/p_off`, or active grammar baselines
without P.

Evidence:

- `cluster3/constants.py:19-21` defines `CLUSTER3_CONDITIONS` as `P`, `G+P`,
  `C+P`, and `G+C+P`.
- `cluster3/experiments/run_cluster3_modal.py:115` defines
  `CONDITION_SELECTOR_CHOICES` as Cluster 3 conditions plus `all`.
- `cluster3/experiments/run_cluster3_modal.py:1178-1181` expands `all` to
  `CLUSTER3_CONDITIONS`.
- `shared/factors/cells.py:8-29` defines the old eight G/C/P factor cells, not
  the 12 grammar-mode/C/P cells.
- `shared/factors/registry.py:17-21` assigns Cluster 3 only the P-containing
  factor cells.

Output namespace paths are parameterized through `--output`, and observability
paths are parameterized through `--observability-output`; however that is
insufficient without condition-id, row-label, and analyzer support.

## Support Matrix

| Capability | Current support | Evidence path | Blocking for L1a? | Remediation needed |
|---|---|---|---|---|
| grammar_off selection | partial | `cluster3/results/dataclass.py:364-366`; `shared/modal_harness/schemas.py:83-98` | yes | Add explicit grammar-mode mapping/labels; grammar-off can map to no constrained decoding. |
| primary_grammar selection | ambiguous | `shared/generation_metadata.py:23-38`; `docs/02_methodology_cluster1.md:74-85` | yes | Define whether `primary_grammar` aliases `task_agnostic` or maps to a distinct file/config. |
| task_agnostic_grammar selection | partial | `shared/generation_metadata.py:30-38`; `cluster3/experiments/run_cluster3_modal.py:798-801` | yes | Map packet value `task_agnostic_grammar` to code value `task_agnostic` and row label. |
| grammar file/hash provenance | partial | `shared/modal_harness/generation.py:109-181`; `cluster3/experiments/run_cluster3_modal.py:2305-2345` | yes | Keep existing path/hash fields and add mode-level provenance binding. |
| per-row grammar_mode label | no | `cluster3/results/dataclass.py:260-308` | yes | Add schema field or audited derived artifact before L1a. |
| per-row repair_history_policy label | yes | `cluster3/results/dataclass.py:299`; `shared/analysis/factorial.py:95-112` | no | No immediate schema change for this capability. |
| 12-cell condition naming | no | `shared/factors/cells.py:8-29`; `cluster3/constants.py:19-21` | yes | Add 12-cell IDs or a matrix planner that writes explicit mode/C/P fields. |
| output namespace parameterization | partial | `cluster3/experiments/run_cluster3_modal.py:162`; `786-842` | no, if implemented carefully | Use explicit fresh `--output` paths and no-overwrite policy. |
| observability sidecar join keys | partial | `cluster3/experiments/run_cluster3_modal.py:1306-1347`; `shared/observability/schema.py:213-225` | yes for grammar-mode observability claims | Add `grammar_mode` to row identity or attributes only after source-of-truth semantics are fixed. |
| analyzer grouping by grammar_mode | no | `shared/analysis/factorial.py:3502-3575` | yes | Extend analyzer taxonomy and grouping with fixture tests. |
| report consumption of grammar_mode | no | `shared/eval/reporting/tables.py:174-216` | yes for report tables | Add table columns/labels after analyzer emits grammar-mode metadata. |
| MLflow indexing/logging of grammar_mode | partial | `shared/tracking/mapping.py:118-149`; `102-116`; `220-257` | yes for MLflow index claim | Add post-hoc/non-authoritative grammar-mode tags or importer fields. |

## Required Remediation

Minimum implementation patch before any L1a execution packet:

1. Add a repo-native grammar-mode mapping.
   - Define code values for `grammar_off`, `primary_grammar`, and
     `task_agnostic_grammar`.
   - Explicitly decide whether `primary_grammar` is an alias for current
     `task_agnostic` or a distinct grammar file.
   - If it is an alias, update the launch packet science design because the
     12 cells do not represent three distinct grammar implementations.

2. Add row/schema support.
   - Add `grammar_mode` to Cluster 3 rows or define a versioned derived-row
     artifact that is authoritative for L1a analysis.
   - Validate consistency between `grammar_mode`, `grammar_active`,
     `grammar_variant`, `grammar_path`, `grammar_sha`, and
     `grammar_claim_scope`.
   - Add negative tests for inconsistent mode/variant/path combinations.

3. Add launch/matrix support.
   - Provide a no-remote local planner/CLI fixture for the 12 cells.
   - Prove exact condition IDs and output paths before Modal.
   - Ensure no current `--condition all` semantics are silently reused as a
     12-cell run.

4. Add analyzer/report support.
   - Extend analysis fixtures to group by `grammar_mode`.
   - Add C/P interaction summaries conditional on grammar mode.
   - Make current analyzer fail closed on 12-cell labels until support is
     complete.

5. Add optional MLflow index support.
   - Keep JSONL/artifacts/analyzers authoritative.
   - Add post-hoc tags/params/index fields for `grammar_mode` only after row
     semantics are stable.

Suggested local gates:

```bash
.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py cluster3/tests/test_cluster3_schema.py shared/tests/test_analyzer_cluster3.py shared/tests/test_factorial_analysis.py shared/tests/test_reporting_tables.py shared/tests/test_tracking_provenance.py -q
git diff --check
```

No Modal, generation, output mutation, analyzer refresh, report refresh, or
MLflow runtime writes should be part of that remediation patch.

## No-Execution Proof

This audit did not invoke Modal, GPU generation, experiments, benchmarks,
profilers, analyzer refreshes, report builders, billing queries, MLflow runtime
writes, or output mutation. Commands were limited to `git status`, `sed`, `nl`,
`rg`, `find`, and `shasum`.

## No-Output/Mlruns Mutation Proof

No files under these protected runtime/result paths were modified:

- `outputs/`
- `artifacts/`
- `mlruns/`
- `docs/preliminary_report/`
- `shared/tracking/`
- `shared/analysis/`
- `shared/tests/`
- `cluster1/`
- `cluster2/`
- `cluster3/`
- `shared/modal_harness/`
- dependency or lock files

Only this audit report and handoff routing docs are in scope.

## Validation Commands

Validation commands planned for this audit closeout:

```bash
git diff --check
git status --short --branch
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report shared/tracking shared/analysis shared/tests cluster1 cluster2 cluster3 shared/modal_harness pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
rg -n "MODAL_AUTHORIZED: YES|GPU_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|EXPERIMENT_EXECUTION_AUTHORIZED: YES|BENCHMARK_AUTHORIZED: YES|PROFILER_AUTHORIZED: YES|OUTPUT_MUTATION_AUTHORIZED: YES|PAPER_SCALE_AUTHORIZED: YES|MLFLOW_TRACKING_EXECUTION_AUTHORIZED: YES|AUTHORIZES_EXECUTION: YES" docs audits .contracts --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
rg -n "grammar_mode|grammar_off|primary_grammar|task_agnostic_grammar|grammar_active|triton_kernel_agnostic|gbnf|xgrammar" audits/grammar_mode_code_support_audit_report.md docs/handoff
```

Expected results:

- `git diff --check` passes.
- Protected-scope diff is empty.
- Execution authorization scan is empty.
- Grammar-mode evidence scan shows this audit and handoff conclusions.

## Classification

Primary classification:

`GRAMMAR_MODE_CODE_SUPPORT_AUDIT_BLOCKED_IMPLEMENTATION_REQUIRED`

Sub-blockers:

- `GRAMMAR_MODE_CODE_SUPPORT_AUDIT_BLOCKED_SELECTION_AMBIGUITY`
- `GRAMMAR_MODE_CODE_SUPPORT_AUDIT_BLOCKED_SCHEMA_REQUIRED`
- `GRAMMAR_MODE_CODE_SUPPORT_AUDIT_BLOCKED_ANALYZER_REQUIRED`

No scope violation or authorization leak was observed.

## Next-Step Recommendation

Do not create an L1 execution packet yet.

Next step should be a local implementation branch or patch that adds
fixture-tested grammar-mode mapping, row/schema labeling, matrix planning, and
analyzer/report support. Only after that patch passes local validation should
the unsigned L1a authorization packet be reviewed again for possible execution
authorization.
