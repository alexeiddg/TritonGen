# Cluster 3 Phase 12b F1-Targeted P-Loop Modal Diagnostic Report

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output at Phase 12b start:

```text
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_docs_consistency.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
```

Dirty path classification:

| Path | Classification | Notes |
|---|---|---|
| `cluster3/experiments/run_cluster3_modal.py` | expected prior-phase uncommitted runner change, then Phase 12b allowed runner edit | Prior Phase 11/12 Modal local-entrypoint work was already dirty; Phase 12b added diagnostic seed flags here. |
| `cluster3/tests/test_docs_consistency.py` | expected prior-phase uncommitted test change | Present before Phase 12b; not edited during Phase 12b. |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | expected prior-phase uncommitted test change, then Phase 12b allowed focused test edit | Prior Phase 11/12 test work was already dirty; Phase 12b added diagnostic seed tests here. |

The tree was not clean despite the expected prompt state. The dirty paths were Cluster 3 runner/test surfaces already present from prior phases, and Phase 12b edits stayed within the explicitly allowed implementation files.

## Authorization Evidence

The operator prompt authorized only this bounded diagnostic:

> Modal execution is authorized only for this bounded F1-targeted diagnostic.

The prompt also stated: "Do not run n=20 yet. Test that Cluster 3 works end-to-end, specifically the F1_COMPILE -> P-loop branch."

## Phase 12 Insufficient F1 Signal Summary

Validated before Phase 12b:

```text
f1_seed_count 0
p_attempted 0
```

The Phase 12 artifact `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` existed, had five rows, and had zero `F1_COMPILE` seeds and zero P attempts. Phase 12 therefore validated bounded G+P/template plumbing but not the F1_COMPILE -> P-loop branch.

## Command Discovery

Initial Modal help did not expose a diagnostic seed/source override:

```text
--resume / --no-resume
--overwrite / --no-overwrite
--modal-eval-gpu TEXT
--modal-generation-gpu TEXT
--c-repair-budget INTEGER
--p-repair-budget INTEGER
--max-new-tokens INTEGER
--temperature FLOAT
--dtypes TEXT
--grammar-variant TEXT
--tokenizer-revision TEXT
--model-revision TEXT
--model-id TEXT
--output TEXT                   [required]
--n INTEGER                     [required]
--scale-tier TEXT               [required]
--kernel-class TEXT             [required]
--condition TEXT                [required]
```

Search confirmed no existing safe source-injection path in the runner.

After the narrow runner implementation, Modal help exposed:

```text
--diagnostic-expected-initial-failure TEXT
--diagnostic-seed-source TEXT
```

## Diagnostic Source Mechanism

Added a disabled-by-default diagnostic seed-source mode in `cluster3/experiments/run_cluster3_modal.py`:

- `--diagnostic-seed-source PATH`
- `--diagnostic-expected-initial-failure F1_COMPILE`

The mode is bounded to condition `P` or `G+P`, smoke scale, one kernel class, one dtype, and `n <= 2`. It reads a repository-local fixture source, evaluates that source through the normal Cluster 3 correctness adapter, and validates the actual remote initial failure against the expected value. It does not fabricate `F1_COMPILE`; if the remote classifier returns any other failure, the runner stops before dispatching P or writing a row.

Schema metadata was not extended because `Cluster3EvalRow`/`Cluster3GeneratedRowMetadata` are strict and do not permit diagnostic-specific fields. The fixture path and expected failure are recorded in this report and in `docs/05_artifacts_and_results_registry.md`.

Focused tests added in `cluster3/tests/test_run_cluster3_modal_cli.py` cover diagnostic bounds, non-P condition rejection, correctness adapter use, no F1 fabrication, and F1 dispatch to P under stubs.

## Exact Modal Commands

Primary attempt:

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition G+P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --grammar-variant template_upper_bound --diagnostic-seed-source cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py --diagnostic-expected-initial-failure F1_COMPILE --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl --overwrite
```

Alternate attempt:

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition G+P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --grammar-variant template_upper_bound --diagnostic-seed-source cluster3/tests/fixtures/f1_compile_kernels/type_error_in_pointer_arith.py --diagnostic-expected-initial-failure F1_COMPILE --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl --overwrite
```

## Modal Execution Summary

Primary Modal app:

`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-6fgPaHryjtKDn0v03FyAYo`

Result:

```text
RuntimeError: diagnostic seed expected initial failure F1_COMPILE; got F0_BAD_SIGNATURE
```

Alternate Modal app:

`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-Ifk6EIpZLq2ZUhsqBZsUda`

Result:

```text
RuntimeError: diagnostic seed expected initial failure F1_COMPILE; got F0_BAD_SIGNATURE
```

Both attempts initialized the existing Modal app and Cluster 2 remote correctness/generation objects, evaluated one injected seed through the correctness adapter, then stopped locally before row append because the actual remote initial failure was `F0_BAD_SIGNATURE`, not `F1_COMPILE`.

No additional diagnostic attempts were run.

## Output Artifacts

| Path | Size | Rows | SHA256 | Sidecar |
|---|---:|---:|---|---|
| `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl` | 0 bytes | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl.hashes.json`, SHA256 `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef`, schema_version 1 |
| `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl` | 0 bytes | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl.hashes.json`, SHA256 `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef`, schema_version 1 |

These outputs are blocked-run evidence only. They are not valid Cluster 3 smoke, branch-coverage, schema-row, P-loop, pass@k, P-lift, or performance evidence.

## Row Count

Both attempted JSONL outputs have row count 0.

## Row Schema Validation

No row schema validation was possible because no JSONL row was written. Zero-row files were not treated as valid artifacts.

## Seed Failure Classification

| Fixture | Remote initial classification |
|---|---|
| `cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py` | `F0_BAD_SIGNATURE` |
| `cluster3/tests/fixtures/f1_compile_kernels/type_error_in_pointer_arith.py` | `F0_BAD_SIGNATURE` |

The existing Phase 8 fixture tests exercise P-loop behavior with synthetic F1 evaluations, but the fixtures do not match the locked remote `elementwise` launcher signature expected for `kernel_name=relu`, so remote correctness stops at the signature boundary.

## P Firing Summary

P did not fire in either attempt:

- `p_repair_attempted` rows: 0
- `p_loop_calls`: 0
- P stop reason: not applicable because no row was written

This is not F1-loop validation.

## Boundary Scan Summary

Commands:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|allclose|torch.testing" outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/g_plus_p_f1_targeted_smoke_n1.jsonl outputs/cluster3/g_plus_p_f1_targeted_smoke_n1_alt.jsonl
```

Both scans returned no matches. The files are zero-row outputs.

## Tests Run

Pre-implementation/pre-Modal:

- `.venv/bin/python -m pytest cluster3/tests -v` -> 728 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` -> 128 passed, 480 deselected
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` -> failed only at the known Cluster 1 docs-lock test after 130 passed, 7 skipped

After implementation:

- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v` -> 81 passed
- `.venv/bin/python -m pytest cluster3/tests -v` -> 735 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` -> 128 passed, 480 deselected
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` -> failed only at the known Cluster 1 docs-lock test after 130 passed, 7 skipped

Post-Modal attempts:

- `.venv/bin/python -m pytest cluster3/tests -v` -> 735 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` -> 128 passed, 480 deselected

## Regression Checks

Full regression remains unchanged: the first failure is still:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

This is the known pre-existing Cluster 1 docs-lock failure. No new pre-spend or post-attempt regression was observed before that known failure.

## Cost / Spend Notes

Two n=1 Modal diagnostic attempts were run, matching the explicit maximum in the operator prompt. Both attempts stopped after the initial remote correctness classification and before P-loop generation. No n=20, paper-scale, all-condition, all-task, profiling, timing, speedup, latency, throughput, Nsight, NCU, or performance work was run.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to register both Phase 12b zero-row blocked diagnostic attempts, their fixture paths, remote seed classification (`F0_BAD_SIGNATURE`), sidecars, hashes, and caveats. The registry explicitly marks them as not valid F1/P-loop evidence.

## Per-Phase Docs Updates

Updated:

- `docs/05_artifacts_and_results_registry.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

Created:

- `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md`

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar files, analyzer outputs, n=20 artifacts, paper-scale artifacts, or profiling/performance artifacts were modified.

Phase 12b source edits were limited to:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

`cluster3/tests/test_docs_consistency.py` was already dirty before Phase 12b and was not edited in this phase.

## Classification

`PHASE12B_BLOCKED_NO_F1_FIXTURE_SIGNAL`

## Next-Step Recommendation

Do not run n=20 or broader development-scale P work from this state. A future targeted diagnostic needs a fixture aligned to the locked remote correctness launcher signature for the selected kernel class, then separate explicit approval for another bounded n=1 diagnostic attempt.
