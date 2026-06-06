# Grammar-Mode 12-Cell Launcher Support Report

## Executive Summary

This branch adds local dry-plan launcher support for the selected 12-cell
`grammar_mode x C x P` L1a design. The new selector is
`grammar_mode_cp_12cell` and is accepted only with `--dry-plan`. It expands to
all 12 cells, including the six no-P control cells, and emits deterministic
cell metadata without opening result writers, observability writers, MLflow
tracking, Modal, generation, correctness evaluation, benchmarks, or profilers.

The implementation keeps the old Cluster 3 selectors backward-compatible.
`--condition all` still expands to the original P-containing Cluster 3
conditions only.

## Files Changed

- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_grammar_mode_matrix.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/grammar_mode_12cell_launcher_support_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Launcher Selector Support

The Cluster 3 CLI now accepts:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
```

It also accepts a single-cell dry-plan selector:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan --grammar-mode-cell task_agnostic__c_on__p_off
```

The selector is fail-closed for execution. If `grammar_mode_cp_12cell` is passed
without `--dry-plan`, config validation raises before any runner work.

## Dry-Plan Support

The dry plan emits one JSON object with:

- selector and selected cell count;
- condition name and stable condition ID;
- `grammar_mode`, `grammar_active`, `grammar_variant`, grammar path, grammar
  hash, and grammar claim scope;
- C/P activation booleans;
- repair-history policy;
- output namespace suffix;
- planned output JSONL path;
- planned content-hash sidecar path;
- planned observability event, summary, and hash sidecar paths;
- observability experiment ID, run ID suffix, and join key;
- path-collision policy;
- execution role and support status.

The dry-plan path returns before `run_cluster3`, tracking context setup, JSONL
logging, or observability logging.

## No-P Control Support

The dry-plan selector includes six no-P cells:

- `grammar_off__c_off__p_off`
- `grammar_off__c_on__p_off`
- `template_upper_bound__c_off__p_off`
- `template_upper_bound__c_on__p_off`
- `task_agnostic__c_off__p_off`
- `task_agnostic__c_on__p_off`

These cells are labeled with `execution_role=no_p_control_cell`. This makes
them selectable and path-plannable locally. It does not materialize control rows
or approve output mutation.

## Grammar-Mode Support

The dry plan includes all three repo-supported grammar modes:

- `grammar_off`
- `template_upper_bound`
- `task_agnostic`

Active grammar modes include deterministic grammar paths and local SHA-256
hashes. `grammar_off` rows record absent grammar path/hash/scope metadata.

## Path-Planning And No-Overwrite Support

Planned output paths use:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
```

Planned observability paths use:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1/
```

Every cell records `path_collision_policy=fail_if_any_target_path_exists`.
The dry plan does not create these directories or files.

## Backward Compatibility

Legacy selector behavior is unchanged:

- `P`, `G+P`, `C+P`, and `G+C+P` remain executable selectors under the old
  runner path.
- `all` still expands to the original `CLUSTER3_CONDITIONS` tuple only.
- `grammar_mode_cp_12cell` is a dry-plan selector and cannot reach
  `run_cluster3`.

## Tests Run

```text
.venv/bin/python -m pytest cluster3/tests/test_grammar_mode_matrix.py cluster3/tests/test_run_cluster3_modal_cli.py -k "grammar_mode or l1a or dry_plan or selector or cli_parses_args" -q
Result: 17 passed, 124 deselected

.venv/bin/python -m pytest cluster3/tests -k "launcher or selector or condition or matrix or grammar_mode or dry" -q
Result: 327 passed, 502 deselected

.venv/bin/python -m pytest cluster3/tests -k "schema or row or grammar_mode" -q
Result: 172 passed, 657 deselected

.venv/bin/python -m pytest shared/tests -k "grammar_mode or factorial or metric_registry" -q
Result: 121 passed, 985 deselected

.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
Result: emitted one local JSON dry-plan object with 12 cells

git diff --check
Result: clean
```

Review reran the same focused validation bundle before commit and also checked
protected mutation and execution-authorization scans. The authorization scan
found only historical already-approved O6b text and literal scan-command
examples, not new affirmative authorization in this branch.

## No-Execution Proof

This task did not invoke Modal, GPU workers, generation, correctness evaluation,
experiments, benchmarks, profilers, billing queries, MLflow runtime writes, or
output/artifact refreshes.

The only CLI invocation of the launcher was local dry-plan mode:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --dry-plan
```

The dry-plan implementation returns before `run_cluster3`, `tracking.run_context`,
`Cluster3JsonlAppendLogger`, or `ObservabilityJsonlAppendLogger`.

## No-Output Or MLflow Mutation Proof

The dry-plan tests watched all planned result, content-hash, observability event,
observability summary, observability hash, and `mlruns` paths and asserted that
existence states were unchanged after dry-plan execution.

Final protected-scope scans are required before commit/promotion:

```text
git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
```

Expected result: empty output.

## Remaining Blockers

- The L1a packet remains unsigned.
- Numeric stop/spend limits remain pending.
- Exact execution commands remain pending a later signed packet.
- Output mutation remains forbidden until a later signed packet authorizes it.
- MLflow runtime tracking remains forbidden; post-hoc indexing remains
  non-authoritative and deferred until artifacts exist.
- The no-P cells are locally selectable in dry-plan form only; they are not
  materialized or counted as executed evidence.

## Classification

`GRAMMAR_MODE_12CELL_LAUNCHER_SUPPORT_COMPLETE`

## Next-Step Recommendation

Promote the committed local-only implementation into
`codex-track-handoff-context`. Only after promotion should a separate L1a final
numeric stop/spend and command approval packet be prepared for user signature.
Do not create or run an execution packet from this branch.
