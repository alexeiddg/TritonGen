# Cluster 3 Phase 12d Aligned F1_COMPILE P-Loop Modal Diagnostic

## Preflight Git Status

Command:

```text
git status --short
```

Output:

```text
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_docs_consistency.py
 M cluster3/tests/test_p_repair_f1_fixtures.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
?? cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py
```

Dirty path classification:

| Path | Classification |
|---|---|
| `cluster3/experiments/run_cluster3_modal.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/test_docs_consistency.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/test_p_repair_f1_fixtures.py` | `expected_phase12c_fixture_alignment_change` |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py` | `expected_phase12c_fixture_alignment_change` |

No pre-existing output artifact mutation was present in the preflight status.

## Authorization Evidence

The operator prompt authorized Modal execution only for the bounded n=1 Phase
12d diagnostic and explicitly prohibited n=5, n=20, paper-scale runs,
all-condition runs, all KernelBench task runs, profiling, speedup, latency,
throughput, Nsight, NCU, RL, grammar changes, Cluster 1 changes, Cluster 2
changes, shared analyzer/eval changes, and hash re-recording.

## Phase 12c Fixture Alignment Summary

Required prior report:
`audits/cluster3_phase12c_f1_fixture_alignment_report.md`.

Aligned fixture:
`cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py`.

Phase 12c local evidence recorded:

- `check_parse -> true`
- `check_signature -> true`
- AST sanitizer safe success
- fake torch/triton runtime signature inspection passed
- expected remote initial failure: `F1_COMPILE`

The Phase 12c report classified alignment as
`PHASE12C_F1_FIXTURE_ALIGNMENT_COMPLETE_WITH_WARNINGS` because full regression
still stops only at the known Cluster 1 docs-lock failure.

## Exact Modal Command

```text
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition G+P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --grammar-variant template_upper_bound --diagnostic-seed-source cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py --diagnostic-expected-initial-failure F1_COMPILE --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl --overwrite
```

## Modal Execution Summary

The Modal run completed successfully:

```json
{
  "output": "outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl",
  "route_audit": [
    {
      "c_loop_calls": 0,
      "condition": "G+P",
      "correctness_calls": 2,
      "generation_calls": 1,
      "p_loop_calls": 1,
      "route": "p_loop"
    }
  ],
  "rows": 1,
  "write_mode": "overwrite"
}
```

Modal app URL shown by the CLI:
`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-Zdfl5WA5sTx70EPyvzbiZB`.

No alternate fixture was run.

## Output Artifact Paths

- `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl`
- `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl.hashes.json`

Hashes:

- JSONL SHA256:
  `dedfe81f40eb094b3983c4a16cd32ee1b88a832950922fd6b22b73a1928c929e`
- sidecar SHA256:
  `33b0b976da99f2b14cff65f6734ef8f31986f294e45c82435b0d8f847ba0c3ef`

## Row Count

Exactly one non-empty JSONL row was produced.

## Row Schema Validation

Validation command used `Cluster3EvalRow.from_dict`.

Result: passed.

Observed row fields:

- condition: `G+P`
- initial failure code: `F1_COMPILE`
- final failure code: `None`
- compile success: `true`
- functional success: `true`
- P repair attempted: `true`
- P repair attempt count: `1`
- C loop fired: `false`

Content hash sidecar validation used
`load_content_hash_sidecar` and `validate_content_hash_sidecar_for_rows`.

Result: passed.

## Observed Seed Failure Classification

The aligned fixture classified remotely as `F1_COMPILE`.

It did not classify as `F0_BAD_SIGNATURE`, `F0_PARSE`, `F1_RUNTIME`, `F2`, or
`F3`.

## P Firing Summary

P fired exactly once after the `F1_COMPILE` seed:

- `p_loop_calls=1`
- `p_repair_attempted=true`
- `p_repair_attempt_count=1`
- `correctness_calls=2`
- `generation_calls=1`
- `c_loop_calls=0`

P did not fire outside `F1_COMPILE`.

## P Stop Reason

`p_compile_repaired_then_success`

## Terminal Failure Code

`None`

## Boundary Scan Result

Private/correctness-set leakage scan:

```text
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|allclose|torch.testing" outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl
```

Result: no matches.

Performance/profiler scan:

```text
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl
```

Result: no matches.

## Artifact Registry Update

Updated `docs/05_artifacts_and_results_registry.md` with the Phase 12d artifact:

- condition: `G+P`
- scale: n=1 targeted branch diagnostic
- fixture:
  `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py`
- observed seed failure code: `F1_COMPILE`
- P fired: yes
- P stop reason: `p_compile_repaired_then_success`
- terminal failure code: `None`
- row count: `1`
- schema version: `1`, enforced by `Cluster3EvalRow`
- JSONL and sidecar hashes recorded
- caveats recorded: branch-coverage diagnostic only, not n=5 statistical
  evidence, not n=20 paper-scale evidence, not pass@k evidence, not P-lift
  evidence, not performance/speedup evidence.

## Tests Run

Pre-Modal:

- `.venv/bin/python -m pytest cluster3/tests/test_p_repair_f1_fixtures.py -v`
  - 15 passed
- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v`
  - 81 passed
- `.venv/bin/python -m pytest cluster3/tests -v`
  - 739 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`
  - 128 passed, 480 deselected

Post-run:

- `.venv/bin/python -m pytest cluster3/tests -v`
  - 739 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`
  - 128 passed, 480 deselected

## Regression Checks

Pre-Modal and post-run full regression command:

```text
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Both runs stopped only at the known pre-existing failure:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Post-run summary before stop:

```text
1 failed, 130 passed, 7 skipped
```

No new regression was observed.

## Cost/Spend Notes

Exactly one authorized n=1 Modal diagnostic was run. The CLI showed one app run,
one output row, one P-loop call, and no alternate fixture. No profiler,
performance, timing, latency, throughput, Nsight, NCU, speedup, n=5, n=20,
paper-scale, all-condition, or all-task execution was run. The CLI did not
surface a cost total.

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
file, analyzer output JSON, RL path, or Modal harness source was intentionally
modified in Phase 12d.

Allowed Phase 12d mutations:

- `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl`
- `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl.hashes.json`
- `docs/05_artifacts_and_results_registry.md`
- `audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md`

Pre-existing dirty Cluster 3 runner/test paths from Phase 12b/12c remain
unreverted and are not Phase 12d source changes.

## Classification

`PHASE12D_ALIGNED_F1_P_LOOP_COMPLETE_WITH_WARNINGS`

Reason: exactly one valid row was generated; observed seed failure was
`F1_COMPILE`; P fired; P stop reason was not `p_not_applicable`; schema and hash
sidecar validation passed; boundary scans passed; local tests passed; full
regression still fails only at the known Cluster 1 docs-lock failure.

## Next-Step Recommendation

Do not run n=20 yet. Treat Phase 12d as targeted branch-coverage evidence that
the remote `F1_COMPILE` -> P-loop path works. Any broader development or
paper-scale run needs separate explicit approval and should continue to preserve
the no-performance/no-speedup/no-profiler boundary.
