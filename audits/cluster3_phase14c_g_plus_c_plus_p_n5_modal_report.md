# Cluster 3 Phase 14c G+C+P n=5 Modal Execution Report

## Authorization Evidence

The operator prompt explicitly authorized this bounded run with:

`I authorize Phase 14c G+C+P n=5 Modal execution.`

Scope was limited to one `G+C+P` matrix cell, `elementwise`, `fp32`, `n=5`, no
paper-scale execution, no all-condition run, no profiling/timing/performance
measurement, and no source mutation.

## Preflight Git Status

Initial git status command:

`git status --short`

Exact output:

```text
```

Dirty path classification: no dirty paths were present at preflight.

## Phase 14 Plan Status

`audits/cluster3_phase14_n5_condition_matrix_plan.md` exists and defines the
one-cell-at-a-time optional n=5 matrix plan. Phase 14c was run only after
explicit approval for the planned `G+C+P` cell.

## Phase 14a Status

`audits/cluster3_phase14a_p_only_n5_modal_report.md` exists.

`outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` exists and has exactly
five rows.

Phase 14a classification:
`PHASE14A_P_N5_COMPLETE_INSUFFICIENT_F1_SIGNAL_WITH_WARNINGS`.

## Phase 14b Status

`audits/cluster3_phase14b_c_plus_p_n5_modal_report.md` exists.

`outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` exists and has
exactly five rows.

Phase 14b classification:
`PHASE14B_C_PLUS_P_N5_COMPLETE_INSUFFICIENT_REPAIR_SIGNAL_WITH_WARNINGS`.

## Exact Modal Command

The output path did not exist at preflight, so `--overwrite` was used only to
force the runner into a documented fresh-write mode for this phase.

```bash
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal \
  --condition G+C+P \
  --kernel-class elementwise \
  --scale-tier development \
  --n 5 \
  --dtypes fp32 \
  --grammar-variant template_upper_bound \
  --p-repair-budget 5 \
  --c-repair-budget 5 \
  --output outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl \
  --overwrite
```

Modal run URL:
`https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-toghWw811vJf5quhd570r4`

## Modal Execution Summary

The runner completed successfully and wrote the planned artifact under
`outputs/cluster3/`.

Runner summary:

```json
{
  "output": "outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl",
  "route_audit": [
    {
      "c_loop_calls": 0,
      "condition": "G+C+P",
      "correctness_calls": 5,
      "generation_calls": 5,
      "p_loop_calls": 0,
      "route": "initial_terminal"
    }
  ],
  "rows": 5,
  "write_mode": "overwrite"
}
```

No unbounded spend expansion, multi-condition execution, multi-kernel execution,
paper-scale execution, or performance/profiling path was observed.

## Output Artifact Paths

- `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl.hashes.json`

Artifact size: 23940 bytes.

Sidecar size: 2220 bytes.

JSONL SHA256:
`90985813219ea1dd461bdc7b06a4c8af0ad25aa730ed1f4564a5bf12784154c0`

Sidecar SHA256:
`e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde`

## Row Count

Exactly five non-empty JSONL rows were produced.

## Row Schema Validation

All five rows validate with `Cluster3EvalRow.from_dict`.

All five rows have:

- `condition=G+C+P`
- `kernel_class=elementwise`
- `dtype=fp32`
- `compile_success=true`
- `functional_success=true`
- `eval_set_success=true`
- `repair_set_success=true`

## Content Hash Validation

`outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl.hashes.json`
exists and validates with `load_content_hash_sidecar` and
`validate_content_hash_sidecar_for_rows` after parsing the rows as
`Cluster3EvalRow` instances.

## Grammar Variant And Claim-Scope Summary

Top-level `grammar_active` is `true` for all five rows.

Nested `generated_metadata` records:

- `grammar_variant=template_upper_bound`: 5 rows
- `grammar_claim_scope=diagnostic_non_primary`: 5 rows
- `grammar_path=cluster1/grammar/triton_kernel.gbnf`

The grammar route is therefore recorded as template upper-bound diagnostic
metadata, not primary task-agnostic grammar evidence.

## Failure-Code Counts

- `failure_code=None`: 5

## Initial Failure-Code Counts

- `initial_failure_code=None`: 5

## F1_COMPILE Seed Count

`F1_COMPILE` seeds: 0.

## F2 Initial Count

Initial F2 rows: 0.

## P Firing Summary

`p_repair_attempted` rows: 0.

P did not fire. This is boundary-correct because no row reached
`F1_COMPILE`.

## P Stop-Reason Counts

- `p_not_applicable`: 5

## C Firing Summary

`c_loop_fired` rows: 0.

C did not fire. This is boundary-correct because no row reached an initial F2
or post-P F2 path.

## C Loop Source Counts

- `none`: 5

## C Terminal Failure-Code Counts

No C terminal failure codes were recorded because C did not fire.

## Boundary Scan Result

Boundary scan commands found no matches in the Phase 14c artifact:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl
```

No private-eval, hidden-shape, profiler, timing, speedup, latency, throughput,
benchmark, or performance leakage was found.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to register the Phase
14c `G+C+P` n=5 development matrix cell with row count, schema, hashes, grammar
metadata, failure-code counts, P/C signal counts, and caveats.

The registry explicitly states that this artifact is one development matrix
cell only, uses the template upper-bound diagnostic/non-primary grammar route,
is not paper-scale, is not pass@k evidence, is not P/C-lift evidence, is not
statistical evidence, and is not performance/speedup/profiler/timing evidence.

## Tests Run

Pre-run:

- `.venv/bin/python -m pytest cluster3/tests -v`: 744 passed.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`:
  128 passed, 480 deselected.

Post-run:

- `.venv/bin/python -m pytest cluster3/tests -v`: 744 passed.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`:
  128 passed, 480 deselected.

## Regression Checks

Pre-run full regression:

- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
- Stopped only at the known pre-existing Cluster 1 docs-lock failure:
  `cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`
- Summary: 1 failed, 130 passed, 7 skipped.

Post-run full regression:

- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
- Stopped only at the same known pre-existing Cluster 1 docs-lock failure.
- Summary: 1 failed, 130 passed, 7 skipped.

No new regression was observed.

## Cost/Spend Notes

Only one authorized Phase 14c Modal command was run.

The run was bounded to `condition=G+C+P`, `kernel_class=elementwise`,
`scale-tier=development`, `n=5`, and `dtypes=fp32`. The route audit recorded
five generation calls and five correctness calls, with zero P-loop calls and
zero C-loop calls. No profiling, timing, speedup, latency, throughput,
benchmark, or performance measurement was run.

## Negative Scope Verification

Phase 14c did not modify Cluster 1 source, Cluster 2 source, shared
analysis/eval source, grammar files, Cluster 3 implementation/test files,
analyzer output JSON files, or Modal harness source.

Allowed changes are limited to the new Phase 14c artifact and sidecar, this
report, the artifact registry, and required handoff/routing docs.

## Classification

`PHASE14C_G_C_P_N5_COMPLETE_INSUFFICIENT_REPAIR_SIGNAL_WITH_WARNINGS`

Rationale: exactly five valid `G+C+P` rows were generated; schema validation
passed; grammar metadata is recorded correctly in row metadata; boundary scans
passed; tests passed; full regression failed only at the known Cluster 1
docs-lock failure; however, zero `F1_COMPILE`/P attempts and zero F2/C attempts
occurred.

## Next-Step Recommendation

Do not run n=20 or paper-scale work.

Proceed only with separate explicit approval for Phase 14d: decide whether the
existing Phase 12 `G+P` n=5 template artifact is acceptable as the matrix
`G+P` cell or whether to run a fresh Phase 14-controlled `G+P` n=5
elementwise/fp32 matrix cell at
`outputs/cluster3/matrix_n5_g_plus_p_elementwise_fp32.jsonl`.
