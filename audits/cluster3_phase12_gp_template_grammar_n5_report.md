# Cluster 3 Phase 12 G+P Template Grammar n=5 Development Run

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

```text
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_docs_consistency.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
```

Dirty-path classification:

| Path | Classification | Notes |
|---|---|---|
| `cluster3/experiments/run_cluster3_modal.py` | `expected_prior_phase_uncommitted_change` | Phase 11 hydration remediation local-entrypoint change; not modified in Phase 12. |
| `cluster3/tests/test_docs_consistency.py` | `expected_prior_phase_uncommitted_change` | Phase 11 documentation-consistency test update; not modified in Phase 12. |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | `expected_prior_phase_uncommitted_change` | Phase 11 hydration remediation tests; not modified in Phase 12. |

No unrelated, unknown, or pre-existing Phase 12 output/artifact dirty paths were present at preflight.

## Authorization Evidence

The operator prompt stated: "User approved Phase 12 and requested template grammar to test the F1 loop more cleanly."

Modal execution was treated as authorized only for this bounded Phase 12 n=5 G+P/template-grammar development run.

## Prerequisites

- `audits/cluster3_phase11_modal_hydration_remediation_report.md` exists.
- `outputs/cluster3/p_smoke_l4_n1.jsonl` exists and is non-empty.
- Phase 11 smoke row count check printed `1`.
- Required Cluster 3 implementation surfaces exist:
  - `cluster3/experiments/run_cluster3_modal.py`
  - `cluster3/modal/correctness_runner.py`
  - `cluster3/results/dataclass.py`
  - `cluster3/results/logger.py`
  - `cluster3/feedback/dispatcher.py`
  - `cluster3/feedback/compile_error_repair.py`
  - `cluster3/feedback/c_loop_adapter.py`
  - `cluster3/replay/no_p_pairs.py`
  - `cluster3/contracts/no_p_pair_manifest.json`
- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` did not exist before the run.

## Known Pre-Existing Regression Status

Pre-spend full regression command:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: stopped only at the known pre-existing Cluster 1 docs-lock failure:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

The pre-spend run reached `1 failed, 130 passed, 7 skipped` before stopping at that known failure.

## Command Discovery Result

Command:

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --help
```

Relevant supported flags:

```text
--condition TEXT              [required]
--kernel-class TEXT           [required]
--scale-tier TEXT             [required]
--n INTEGER                   [required]
--output TEXT                 [required]
--model-id TEXT
--model-revision TEXT
--tokenizer-revision TEXT
--grammar-variant TEXT
--dtypes TEXT
--temperature FLOAT
--max-new-tokens INTEGER
--p-repair-budget INTEGER
--c-repair-budget INTEGER
--modal-generation-gpu TEXT
--modal-eval-gpu TEXT
--overwrite / --no-overwrite
--resume / --no-resume
```

The runner accepts scale-tier choices `smoke`, `development`, and `paper`; therefore Phase 12 used `--scale-tier development`, not `dev`.

## Template Grammar Selection Mechanism

Template grammar was selected with:

```text
--condition G+P --grammar-variant template_upper_bound
```

The repository grammar registry maps `template_upper_bound` to:

| Field | Value |
|---|---|
| `grammar_path` | `cluster1/grammar/triton_kernel.gbnf` |
| `grammar_claim_scope` | `diagnostic_non_primary` |

This is a diagnostic template route only. It is not primary task-agnostic G evidence and is not paper-scale evidence.

## Exact Modal Command

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition G+P --kernel-class elementwise --scale-tier development --n 5 --dtypes fp32 --grammar-variant template_upper_bound --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl --overwrite
```

No profiling, timing, latency, throughput, Nsight, NCU, speedup, benchmark, all-condition, all-kernel, n=20, or paper-scale flags were used.

## Modal Execution Summary

Modal run URL:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-akKoVoIarpz16iyTv6Lwxe
```

Runner summary:

```json
{"output": "outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl", "route_audit": [{"c_loop_calls": 0, "condition": "G+P", "correctness_calls": 5, "generation_calls": 5, "p_loop_calls": 0, "route": "initial_terminal"}], "rows": 5, "write_mode": "overwrite"}
```

Scope remained bounded:

- one condition: `G+P`
- one kernel class: `elementwise`
- one dtype: `fp32`
- `n=5`
- five generation calls
- five correctness calls
- zero P loop calls
- zero C loop calls

## Output Artifacts

| Artifact | Status | Size | SHA256 |
|---|---|---:|---|
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | generated and validated | 23905 bytes | `9447d987655cba5aadb79d42d115f6baa989b1ea36ba7bf6023975d656e54423` |
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json` | logger-created content-hash sidecar | 2218 bytes | `54f3d06c5749bf27b856f0ef79545f6dda1dbb3199a7665726952d59125efb68` |

No `.sha256` or `.manifest.json` sidecar was created by the existing logger for this run.

## Row Count

The post-run row count check printed:

```text
5
```

Exactly five non-empty JSONL rows were present.

## Row Schema Validation Result

Validation used repository validators:

- `Cluster3EvalRow.from_dict(...)`
- `load_content_hash_sidecar(...)`
- `validate_content_hash_sidecar_for_rows(...)`
- `CLUSTER3_RESULTS_SCHEMA_VERSION`

Result:

```text
schema_version 1
sidecar_schema_version 1
cluster3 phase12 schema and sidecar validation passed
```

All rows had `condition == "G+P"`.

## Content Hash / Sidecar Validation Result

The logger sidecar at `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json` loaded successfully and validated against all five parsed `Cluster3EvalRow` rows.

Sidecar schema version was `1`, matching `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`.

## P/F1 Signal Summary

| Metric | Count |
|---|---:|
| Rows | 5 |
| `condition == "G+P"` | 5 |
| `grammar_variant == "template_upper_bound"` | 5 |
| `grammar_path == "cluster1/grammar/triton_kernel.gbnf"` | 5 |
| `grammar_claim_scope == "diagnostic_non_primary"` | 5 |
| `initial_failure_code == F1_COMPILE` | 0 |
| F1 seed count | 0 |
| `p_repair_attempted == true` | 0 |
| P loop calls | 0 |
| C loop calls | 0 |
| `compile_success == true` | 5 |
| `functional_success == true` | 5 |

P did not fire because no row produced an `F1_COMPILE` seed. This run therefore validates development-scale G+P/template plumbing and schema/provenance only. It is not an F1-loop validation and provides insufficient F1 signal.

## P Stop-Reason Counts

```text
{"p_not_applicable": 5}
```

## Terminal Failure-Code Counts

```text
{None: 5}
```

Initial failure-code counts were also `{None: 5}`.

## Boundary Scan Result

Private-eval scan:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|allclose|torch.testing" outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
```

Result: no matches.

Performance/profiling scan:

```bash
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
```

Result: no matches.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to register:

- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`
- condition `G+P`
- grammar variant `template_upper_bound`
- grammar path `cluster1/grammar/triton_kernel.gbnf`
- grammar claim scope `diagnostic_non_primary`
- scale `n=5 development-scale`
- kernel class `elementwise`
- dtype `fp32`
- row count `5`
- schema version `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`
- sidecar path and hashes
- P signal counts: 0 F1 seeds, 0 P attempts, `p_not_applicable: 5`
- caveats: development-scale only, not paper-scale, not pass@k evidence, no P-lift claim, no performance/speedup/profiler claim, insufficient F1 signal

The Phase 11 smoke row and archived blocked attempt records were preserved.

## Tests Run

Pre-spend:

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest cluster3/tests -v` | 728 passed |
| `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` | 128 passed, 480 deselected |

Post-run:

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest cluster3/tests -v` | 728 passed |
| `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` | 128 passed, 480 deselected |

Post-doc update:

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest cluster3/tests/test_docs_consistency.py -v` | 14 passed |
| `.venv/bin/python -m pytest cluster3/tests -v` | 728 passed |
| `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` | 128 passed, 480 deselected |

## Regression Checks

Pre-spend and post-run full regression command:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Pre-spend, post-run, and post-doc-update runs stopped only at the known pre-existing Cluster 1 docs-lock test:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Final full regression result reached `1 failed, 130 passed, 7 skipped` before stopping at that known failure.

## Cost / Spend Notes

No explicit dollar cost was surfaced by the CLI. Spend was bounded by one Modal local-entrypoint run with:

- one condition
- one kernel class
- one dtype
- `n=5`
- five generation calls
- five correctness calls
- zero P repair calls
- zero C repair calls

No repeated run, all-condition run, all-task run, n=20 run, or profiler/performance run was started.

## Negative Scope Verification

Phase 12 did not modify Cluster 1, Cluster 2, shared analyzer/eval source, grammar files, Modal harness source files, Cluster 3 implementation/test files, Cluster 3 feedback/results/modal/replay/contracts files, or analyzer output JSON files.

The only tracked dirty implementation/test paths visible at preflight were the pre-existing Phase 11 hydration remediation changes listed above. They were not modified by Phase 12.

Final `git diff --name-only` showed only those same three tracked Phase 11
remediation files:

```text
cluster3/experiments/run_cluster3_modal.py
cluster3/tests/test_docs_consistency.py
cluster3/tests/test_run_cluster3_modal_cli.py
```

The forbidden implementation mutation check returned diffs only for those same
pre-existing Phase 11 Cluster 3 runner/test changes. No Phase 12 implementation
or test edits were applied.

Phase 12 changes were limited to:

- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`
- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json`
- `audits/cluster3_phase12_gp_template_grammar_n5_report.md`
- `docs/05_artifacts_and_results_registry.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

## Classification

`PHASE12_GP_TEMPLATE_N5_COMPLETE_INSUFFICIENT_F1_SIGNAL_WITH_WARNINGS`

Rationale:

- five valid `G+P` template-grammar development rows were generated;
- schema and sidecar validation passed;
- boundary scans passed;
- local Cluster 3 and analyzer/factorial tests passed;
- full regression still fails only at the known pre-existing Cluster 1 docs-lock failure;
- no new regressions or out-of-scope Phase 12 source mutations were introduced;
- zero rows produced `F1_COMPILE` seeds and zero rows attempted P repair, so the run is not an F1-loop validation.

## Recommendation For Next Gate

Do not promote this artifact to paper-scale evidence, pass@k evidence, P-lift evidence, or performance evidence. Any next gate requires separate explicit approval and should decide whether to target F1-producing seeds or fixtures more directly before spending on broader development-scale or paper-scale P runs.
