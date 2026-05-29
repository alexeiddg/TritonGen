# Cluster 3 Phase 12e Initial-F2 C-Loop Modal Diagnostic

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
| `cluster3/experiments/run_cluster3_modal.py` | `expected_prior_phase_uncommitted_change`; also extended in Phase 12e to allow `F2_NUMERIC_LARGE` diagnostic seeds only for C-containing smoke conditions |
| `cluster3/tests/test_docs_consistency.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/test_p_repair_f1_fixtures.py` | `expected_prior_phase_uncommitted_change` / `expected_phase12c_fixture_alignment_change` |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | `expected_prior_phase_uncommitted_change`; also extended in Phase 12e with focused F2 diagnostic routing tests |
| `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py` | `expected_phase12c_fixture_alignment_change` |

No pre-existing output artifact mutation was present for
`outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl`.

## Authorization Evidence

The operator prompt authorized Modal execution only for this bounded n=1 Phase
12e diagnostic and explicitly prohibited n=5, n=20, paper-scale runs,
all-condition runs, all KernelBench task runs, profiling, timing, speedup,
latency, throughput, Nsight, NCU, RL, grammar changes, Cluster 1 changes,
Cluster 2 changes, shared analyzer/eval changes, and hash re-recording.

## Phase 12d P-Loop Evidence Summary

Required prior report:
`audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md`.

Phase 12d proved the remote `F1_COMPILE` -> P-loop path:

- rows: `1`
- condition: `G+P`
- observed seed failure: `F1_COMPILE`
- route: `p_loop`
- `p_repair_attempted=true`
- P stop reason: `p_compile_repaired_then_success`
- terminal failure code: `None`

## F2 Fixture/Source Mechanism

The narrowest available source mechanism was the existing diagnostic
`--diagnostic-seed-source` path, extended in Phase 12e to accept the canonical
F2 code `F2_NUMERIC_LARGE` only for `C+P` and `G+C+P` smoke runs with `n <= 1`.

The seed fixture was reused from existing Cluster 2 fixture coverage:

```text
cluster2/tests/fixtures/f2_corrupted_relu.py
```

This fixture matches the elementwise ReLU launcher contract, compiles, runs,
and deterministically returns wrong output. Existing Cluster 2 fixture traces
identify it as `F2_NUMERIC_LARGE`.

Focused local tests added in Phase 12e verify:

- expected F2 diagnostic seeds are accepted for `G+C+P` smoke n=1
- expected F2 diagnostic seeds are rejected for P-only conditions
- expected F2 diagnostic seeds are rejected for `n > 1`
- the diagnostic seed still uses the correctness adapter
- the runner does not fabricate F2
- initial F2 routes to C, not P, under `G+C+P`
- `c_loop_source` records `initial_f2`

## Exact Modal Command

```text
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition G+C+P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --grammar-variant template_upper_bound --diagnostic-seed-source cluster2/tests/fixtures/f2_corrupted_relu.py --diagnostic-expected-initial-failure F2_NUMERIC_LARGE --p-repair-budget 5 --c-repair-budget 1 --output outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl --overwrite
```

## Modal Execution Summary

The Modal run completed successfully:

```json
{
  "output": "outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl",
  "route_audit": [
    {
      "c_loop_calls": 1,
      "condition": "G+C+P",
      "correctness_calls": 1,
      "generation_calls": 0,
      "p_loop_calls": 0,
      "route": "initial_c_loop"
    }
  ],
  "rows": 1,
  "write_mode": "overwrite"
}
```

Modal app URL shown by the CLI:
`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-RsNPyD8DCb4W4gLwvUCR2m`.

No alternate fixture, n=5 run, n=20 run, all-condition run, all-task run, or
profiler/performance/timing run was executed.

## Output Artifact Paths

- `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl`
- `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl.hashes.json`

Hashes:

- JSONL SHA256:
  `2d36f185652134f31e9999a00200ad78c19cff2557067840f6f735e519383e69`
- sidecar SHA256:
  `e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde`

## Row Count

Exactly one non-empty JSONL row was produced.

## Row Schema Validation

Validation command used `Cluster3EvalRow.from_dict`.

Result: passed.

Content hash sidecar validation used `load_content_hash_sidecar` and
`validate_content_hash_sidecar_for_rows`.

Result: passed.

Observed row fields:

- condition: `G+C+P`
- kernel class: `elementwise`
- kernel name: `relu`
- dtype: `fp32`
- initial failure code: `F2_NUMERIC_LARGE`
- final failure code: `None`
- compile success: `true`
- functional success: `true`
- repair-set success: `true`
- eval-set success: `true`
- P repair attempted: `false`
- P stop reason: `p_not_applicable`
- C loop fired: `true`
- C loop source: `initial_f2`
- C terminal failure code: `None`
- C terminal level reached: `2`
- terminal source stage: `c_attempt`
- terminal attempt index: `1`

## Observed Initial Failure Classification

The diagnostic seed classified remotely as `F2_NUMERIC_LARGE`.

It did not classify as `F0`, `F1`, or `F3`.

## P Firing Summary

P did not fire:

- `p_loop_calls=0`
- `p_repair_attempted=false`
- `p_repair_stop_reason=p_not_applicable`
- `p_initial_failure_code=None`
- `p_terminal_failure_code=None`

P did not fire on F2.

## C Firing Summary

C fired exactly once after the initial F2 seed:

- `c_loop_calls=1`
- route: `initial_c_loop`
- `c_loop_fired=true`
- `c_loop_source=initial_f2`
- `c_terminal_failure_code=None`
- `c_terminal_level_reached=2`

## C Loop Source

`initial_f2`

## Terminal Failure Code

`None`

## Boundary Scan Result

Private/correctness-set leakage scan:

```text
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing" outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl
```

Result: no matches.

Performance/profiler scan:

```text
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl
```

Result: no matches.

## Artifact Registry Update

Updated `docs/05_artifacts_and_results_registry.md` with the Phase 12e artifact:

- condition: `G+C+P`
- scale: n=1 targeted branch diagnostic
- fixture: `cluster2/tests/fixtures/f2_corrupted_relu.py`
- observed initial failure code: `F2_NUMERIC_LARGE`
- P fired: no
- C fired: yes
- `c_loop_source=initial_f2`
- C terminal failure code: `None`
- row count: `1`
- schema version: `1`, enforced by `Cluster3EvalRow`
- JSONL and sidecar hashes recorded
- caveats recorded: branch-coverage diagnostic only, not n=5 statistical
  evidence, not n=20 paper-scale evidence, not pass@k evidence, not P/C-lift
  evidence, not performance/speedup evidence.

## Tests Run

Pre-Modal / implementation:

- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v`
  - 86 passed
- `.venv/bin/python -m pytest cluster3/tests -v`
  - 744 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`
  - 128 passed, 480 deselected

Post-run:

- `.venv/bin/python -m pytest cluster3/tests -v`
  - 744 passed
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

Observed summary before stop:

```text
1 failed, 130 passed, 7 skipped
```

No new regression was observed.

## Cost/Spend Notes

Exactly one authorized n=1 Modal diagnostic was run. The CLI showed one app run,
one output row, one C-loop call, and no P-loop calls. The CLI did not surface a
cost total.

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
file, analyzer output JSON, RL path, or Modal harness source was intentionally
modified in Phase 12e.

Phase 12e intentional source/test edits:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

Phase 12e allowed output/doc mutations:

- `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl`
- `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl.hashes.json`
- `docs/05_artifacts_and_results_registry.md`
- `audits/cluster3_phase12e_initial_f2_c_loop_modal_report.md`

Forbidden implementation mutation check returned no diff for:

```text
cluster1 cluster2 shared/analysis shared/eval cluster3/feedback cluster3/results cluster3/modal cluster3/replay cluster3/contracts
```

## Classification

`PHASE12E_INITIAL_F2_C_LOOP_COMPLETE_WITH_WARNINGS`

Warnings are limited to the known pre-existing Cluster 1 docs-lock regression.

## Next-Step Recommendation

Do not run n=20 yet. Treat Phase 12e as targeted branch-coverage evidence that
initial remote F2 routes to the C loop under `G+C+P` while P remains inactive.
Any broader development or paper-scale run requires separate explicit approval.
