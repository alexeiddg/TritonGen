# Grammar-Mode Support Implementation Report

## Executive Summary

This branch makes the 12-cell `grammar_mode x C x P` L1a design locally
representable and fixture-testable without running it. The implementation adds
first-class grammar-mode mapping, a local 12-cell planner, Cluster 3 row labels,
shared row-schema support, and analyzer grouping for explicit `grammar_mode`.

Execution remains unauthorized. No Modal, GPU, generation, experiment,
benchmark, profiler, output mutation, analyzer artifact refresh, report artifact
refresh, MLflow runtime write, billing query, dependency change, or lockfile
change was performed.

## Files Changed

- `shared/factors/grammar_modes.py`
- `shared/factors/__init__.py`
- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/planning/__init__.py`
- `cluster3/results/dataclass.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `shared/eval/schema.py`
- `shared/analysis/factorial.py`
- `shared/tests/test_grammar_modes.py`
- `shared/tests/test_factorial_analysis.py`
- `cluster3/tests/test_grammar_mode_matrix.py`
- `cluster3/tests/test_cluster3_schema.py`
- `docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/grammar_mode_support_implementation_report.md`
- handoff state/registry/hub documents for routing updates

## Grammar-Mode Model

`shared/factors/grammar_modes.py` defines exactly three accepted values:

- `grammar_off`
- `template_upper_bound`
- `task_agnostic`

Mappings:

| grammar_mode | grammar_active | grammar_variant | grammar_path | claim scope |
|---|---:|---|---|---|
| `grammar_off` | false | null | null | null |
| `template_upper_bound` | true | `template_upper_bound` | `cluster1/grammar/triton_kernel.gbnf` | `diagnostic_non_primary` |
| `task_agnostic` | true | `task_agnostic` | `cluster1/grammar/triton_kernel_agnostic.gbnf` | `primary` |

Invalid combinations fail closed. Examples covered by tests include
`grammar_off` with a non-null variant, active grammar without a variant, and a
mode/variant mismatch.

## Twelve-Cell Planner

`cluster3/planning/grammar_mode_matrix.py` adds
`build_l1a_grammar_mode_cp_matrix()`, which returns exactly 12 local
`GrammarModeCellSpec` records:

- four `grammar_off` cells over C/P off/on;
- four `template_upper_bound` cells over C/P off/on;
- four `task_agnostic` cells over C/P off/on.

Each spec includes:

- `condition_name`
- legacy `factor_cell`
- `grammar_mode`
- `grammar_active`
- `grammar_variant`
- `grammar_path`
- `grammar_claim_scope`
- `correctness_feedback_active`
- `compile_feedback_active`
- `repair_history_policy`
- `output_namespace_suffix`
- `expected_eligibility_notes`

The planner is metadata-only and imports no Modal, Torch, Triton, generation,
or correctness runtime.

## Launch Packet Vocabulary Alignment

The promoted launch packet now uses the same selected grammar-mode values as
the local implementation:

- `grammar_off`
- `template_upper_bound`
- `task_agnostic`

Former packet labels `primary_grammar` and `task_agnostic_grammar` are not
treated as executable selectors. The launch packet keeps them only as
unsupported-label stop-condition examples for future approval review.

## Row/Schema Labeling

`shared/eval/schema.py` now accepts optional `grammar_mode` for shared eval
rows.

`cluster3/results/dataclass.py` now carries optional top-level row
`grammar_mode` and optional generated-metadata `grammar_mode`. New generated
rows emit the metadata field, and legacy callers that omit top-level
`grammar_mode` derive it from existing `grammar_active` plus `grammar_variant`
when possible.

Existing `grammar_active` remains preserved. `grammar_off` rows require absent
grammar metadata. Active grammar rows require supported variant/path/scope
metadata.

## Analyzer/Report Support

`shared/analysis/factorial.py` now normalizes explicit `grammar_mode` from
top-level rows or generated metadata, derives a mode from legacy
`grammar_variant` when safe, marks legacy active-G rows without a mode/variant
as `legacy_missing_grammar_mode`, and rejects explicit condition/mode
mismatches.

When explicit `grammar_mode` evidence is present, diagnostics include
`grammar_mode_summary` with:

- grouping policy `group_by_grammar_mode_without_binary_G_collapse`;
- supported modes;
- per-mode row counts;
- conditions represented by each mode;
- active-grammar values and variants.

The analyzer also includes `grammar_mode` in P-pair grammar metadata
consistency checks.

Existing 2x2 output without explicit grammar-mode rows is not expanded with a
new `grammar_mode_summary` key.

## Tracking Support Or Deferral

MLflow/tracking runtime was not changed. The current implementation keeps
tracking no-op-safe by leaving per-row `grammar_mode` string indexing deferred
to a future post-hoc MLflow indexing patch. JSONL rows and analyzer diagnostics
remain the scientific source of truth.

Classification therefore uses the tracking-deferred variant rather than full
tracking completion.

## Backward Compatibility

Backward-compatible behavior:

- legacy rows without `grammar_mode` still load;
- non-G rows derive `grammar_off`;
- active-G rows with legacy `grammar_variant` derive the corresponding
  grammar mode;
- active-G rows missing both `grammar_mode` and `grammar_variant` are marked
  with explicit legacy status in analyzer normalization rather than silently
  collapsed to binary G;
- existing analyzer outputs without explicit grammar-mode evidence do not gain
  a new diagnostics key.

## Tests Run

Passed:

```text
.venv/bin/python -m pytest shared/tests/test_grammar_modes.py cluster3/tests/test_grammar_mode_matrix.py cluster3/tests/test_cluster3_schema.py -q
150 passed
```

```text
.venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -k "grammar_mode or template_upper_bound_condition_label" -q
3 passed, 101 deselected
```

```text
.venv/bin/python -m pytest cluster3/tests -k "grammar_mode or grammar_variant or condition or matrix or schema or row" -q
469 passed, 347 deselected
```

```text
.venv/bin/python -m pytest shared/tests -k "factorial or grammar_mode or metric_registry" -q
121 passed, 985 deselected
```

```text
.venv/bin/python -m pytest shared/tests/test_eval_schema.py shared/tests/test_tracking_noop.py -q
31 passed
```

Additional nearby check:

```text
.venv/bin/python -m pytest shared/tests/test_analyzer_cluster3.py shared/tests/test_factor_cells.py -q
66 passed, 1 failed
```

The failed test is
`shared/tests/test_analyzer_cluster3.py::test_analyzer_2x2_reproducible_without_cluster3_rows`.
The failure is the existing legacy 2x2 golden JSON expecting older
metric-registry row shape; the new grammar-mode diagnostics key is absent for
that legacy 2x2 result. A direct check confirmed
`"grammar_mode_summary" in result["diagnostics"]` is `False` for the legacy
2x2 fixture. Updating that unrelated golden snapshot is outside this narrow
implementation scope.

Final local checks:

```text
git diff --check
passed
```

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
empty
```

```text
git diff -U0 -- docs audits .contracts cluster3 shared | rg -n '^[+][^+].*(MODAL_AUTHORIZED: YES|GPU_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|EXPERIMENT_EXECUTION_AUTHORIZED: YES|BENCHMARK_AUTHORIZED: YES|PROFILER_AUTHORIZED: YES|OUTPUT_MUTATION_AUTHORIZED: YES|PAPER_SCALE_AUTHORIZED: YES|MLFLOW_TRACKING_EXECUTION_AUTHORIZED: YES|AUTHORIZES_EXECUTION: YES)'
empty
```

```text
rg -n 'primary_grammar__|task_agnostic_grammar__|\| `primary_grammar`|\| `task_agnostic_grammar`' docs/experiment_packets/full_pipeline_gcp_factorial_launch_packet_v1.md docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md
empty
```

## No-Execution Proof

No commands invoked:

- `modal`
- GPU jobs
- generation
- experiment runners for execution
- benchmark or profiler tools
- MLflow server or MLflow run creation
- billing queries

All executed commands were local pytest or inspection commands.

## No-Output/Mlruns Mutation Proof

This implementation did not intentionally edit or write:

- `outputs/`
- `artifacts/`
- `mlruns/`
- `docs/preliminary_report/`
- dependency or lock files

The protected mutation scan was empty for those paths.

## Remaining Risks

- The code is locally representable and fixture-tested, but L1a execution still
  needs a signed approval packet with exact command/config, target paths,
  stop/spend limits, model/revision/decoding config, observability IDs, and
  preflight results.
- MLflow post-hoc indexing by `grammar_mode` is deferred.
- The execution runner still has a legacy `--condition all` path for the four
  P-containing Cluster 3 conditions; the new 12-cell planner is local planning
  support, not an execution launcher.
- The unrelated `shared/tests/test_analyzer_cluster3.py` legacy golden snapshot
  remains stale against current metric-registry output.

## Classification

`GRAMMAR_MODE_SUPPORT_IMPLEMENTATION_PARTIAL_TRACKING_DEFERRED`

Local 12-cell representability, row labeling, and analyzer grouping blockers
are resolved for fixture review. Tracking grammar-mode indexing remains a
future post-hoc metadata patch, and execution remains unauthorized.

## Next-Step Recommendation

Review and commit this local implementation branch. Do not draft or run an L1a
execution packet yet. The next packet review may evaluate the unsigned L1a
authorization draft as code-support-ready, but execution still requires a
separate explicit approval packet.
