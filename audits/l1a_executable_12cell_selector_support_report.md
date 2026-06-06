# L1a Executable 12-Cell Selector Support Report

## Executive Summary

This branch adds a local executable-selector planning surface for the 12-cell
`grammar_mode x C x P` L1a design. The existing dry-plan selector remains
available. The new `--execution-plan` mode constructs source-backed per-cell
future command strings for all 12 cells, including the six no-P controls, while
actual runtime execution remains fail-closed.

No Modal, GPU, generation, experiment execution, billing query, benchmark,
profiler, output writer, artifact writer, MLflow runtime write, analyzer
refresh, report refresh, dependency change, or lockfile change was authorized
or performed.

## Files Changed

- `cluster3/planning/grammar_mode_matrix.py`
- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_grammar_mode_matrix.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
- `audits/l1a_executable_12cell_selector_support_report.md`
- `docs/handoff/experiment_change_orchestration_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/agentic_document_hub.md`

## Selector Behavior

`cluster3/planning/grammar_mode_matrix.py` now derives dry-plan and
executable-plan cell entries from the same 12-cell matrix. The executable-plan
builder records:

- stable `condition_id` values matching the dry plan;
- deterministic output and observability sidecar paths;
- `path_collision_policy=fail_if_any_target_path_exists`;
- per-cell `executable_command` strings;
- `--signed-l1a-authorization SIGNED_L1A_PACKET_ID_REQUIRED`;
- support status
  `EXECUTABLE_SELECTOR_PRESENT_AUTHORIZATION_REQUIRED_NO_EXECUTION`.

The Cluster 3 CLI accepts:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition grammar_mode_cp_12cell --repair-history-policy agentic_transcript_v1 --execution-plan
```

and returns a local JSON payload without opening result, observability, or
tracking writers.

## Authorization Gate

The selector is still fail-closed for runtime execution:

- `--dry-plan` is local planning only.
- `--execution-plan` is local command construction only.
- `--condition grammar_mode_cp_12cell` without local planning mode requires
  `--signed-l1a-authorization`.
- Even with a signed-looking placeholder, this branch raises before
  `tracking.run_context`, `run_cluster3`, generation, Modal, result writers, or
  observability writers.

This keeps the branch suitable for packet completion and review only. It does
not authorize L1a execution.

## Matrix Coverage

The executable-plan surface covers exactly 12 cells:

- grammar modes: `grammar_off`, `template_upper_bound`, `task_agnostic`;
- correctness feedback factor C: off/on;
- compile feedback factor P: off/on.

The six no-P cells are labeled `execution_role=no_p_control_cell` and remain
controls, not P evidence. The six P-on cells are labeled
`execution_role=p_enabled_generated_cell`.

## Grammar-Mode Mapping

The executable-plan mapping preserves the existing grammar semantics:

- `grammar_off`: no grammar argument, no grammar path, no grammar hash;
- `template_upper_bound`: `--grammar-variant template_upper_bound`,
  `cluster1/grammar/triton_kernel.gbnf`, current SHA-256
  `0f875b88ea80d7bc9573793f2cfb81bd75523af5ef5c0416466bc07d3eaf9b82`;
- `task_agnostic`: `--grammar-variant task_agnostic`,
  `cluster1/grammar/triton_kernel_agnostic.gbnf`, current SHA-256
  `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`.

No grammar files were modified.

## Path And Collision Policy

The L1a output root remains:

```text
outputs/cluster3/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
```

The L1a observability root remains:

```text
artifacts/observability/full_pipeline_grammar_mode_cp_factorial_v1/l1a_n1
```

Each planned cell records deterministic result JSONL, content-hash sidecar,
observability event, observability summary, and observability hash paths. The
planner records `fail_if_any_target_path_exists`; tests do not create those
paths.

## Packet Update

`docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
now records the source-backed executable selector command surface and local
`--execution-plan` verification command. It still keeps:

- `AUTHORIZES_EXECUTION: NO`;
- unsigned signature fields;
- unsigned stop/spend limits;
- remote image digest blocker;
- signable preflight estimate blocker;
- billing-query authorization blocker;
- post-run validation authorization blocker.

## Tests Run

```text
.venv/bin/python -m pytest cluster3/tests -k "grammar_mode_cp_12cell or selector or dry_plan or no_p_control or authorization" -q
Result: 22 passed, 850 deselected

.venv/bin/python -m compileall -q cluster3 shared
Result: pass

git diff --name-only -- outputs artifacts mlruns docs/preliminary_report pyproject.toml requirements.txt requirements-dev.txt uv.lock poetry.lock Pipfile.lock
Result: empty output

git diff --check
Result: pass

git diff -- cluster3 shared docs audits | rg -n "import modal|from modal|modal\\.billing|requests\\.|urllib|httpx|subprocess.*modal|modal run|modal shell|billing query"
Result: only negative/no-authorization docs wording such as no billing query.

rg -n "AUTHORIZES_EXECUTION: YES|MODAL_AUTHORIZED: YES|GPU_AUTHORIZED: YES|GENERATION_AUTHORIZED: YES|EXPERIMENT_EXECUTION_AUTHORIZED: YES|OUTPUT_MUTATION_AUTHORIZED: YES|PAPER_SCALE_AUTHORIZED: YES|MLFLOW_TRACKING_EXECUTION_AUTHORIZED: YES|BENCHMARK_AUTHORIZED: YES|PROFILER_AUTHORIZED: YES|BILLING_QUERY_AUTHORIZED: YES" docs audits .contracts cluster3 shared --glob '!docs/preliminary_report/index*.html' --glob '!docs/preliminary_report/_report_data.json'
Result: historical O6b approval text and literal scan-command examples only; no new affirmative authorization in this branch.

git diff -- cluster3 shared docs audits | rg -n "speedup achieved|cost reduced|runtime reduced|throughput improved|performance result|benchmark result|Modal optimized|optimization complete|billing reconciled"
Result: empty output

git diff -- cluster3 shared | rg -n "open\\(|write_text|mkdir|mlruns|outputs/|artifacts/|Mlflow|modal|generate|benchmark|profile"
Result: safe references only: command strings, explicit writes_mlruns false metadata, and tests that watch planned paths.
```

## No-Execution Proof

The only direct CLI invocation of the new selector surface was local
`--execution-plan`, which printed JSON and returned before runtime execution.
Tests monkeypatch `run_cluster3` to fail if local planning modes call it.

No `modal run`, Modal shell, GPU work, generation, correctness execution,
experiment run, benchmark, profiler, billing query, analyzer refresh, report
refresh, output writer, artifact writer, or MLflow runtime write occurred.

## No-Output Or MLflow Mutation Proof

The protected diff scan over `outputs`, `artifacts`, `mlruns`,
`docs/preliminary_report`, dependency files, and lockfiles returned empty
output. The local planning tests also watch planned result, content-hash,
observability, and `mlruns` paths and assert unchanged existence states.

## Remaining Blockers

- No user signature exists.
- The exact target commit for any future execution must include this support
  after review and promotion.
- Numeric stop/spend limits remain unsigned.
- The advisory preflight estimate remains synthetic/not signable.
- Remote Modal image digest remains unknown.
- Billing-query authorization, time window, and redacted report path remain
  unsigned.
- Post-run validation and analyzer/report writes remain unauthorized until a
  future signed packet approves them.

## Classification

`L1A_EXECUTABLE_12CELL_SELECTOR_SUPPORT_COMPLETE`

## Next-Step Recommendation

Review and commit this local-only implementation. After review, promote the
support into `codex-track-handoff-context`. Do not create or run an L1a
execution packet from this branch.
