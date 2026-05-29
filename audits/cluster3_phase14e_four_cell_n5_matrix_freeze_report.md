# Cluster 3 Phase 14e Four-Cell n=5 Matrix Freeze Report

Date: 2026-05-28

Classification: `PHASE14E_FOUR_CELL_N5_MATRIX_FREEZE_COMPLETE_WITH_WARNINGS`

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

```text
```

The working tree was clean at preflight. No Modal, GPU, generation, experiment,
n=20, paper-scale, profiling, timing, speedup, or performance command was run
in this phase.

## Prior Report Status

All required prior reports were present:

- `audits/cluster3_phase14_n5_condition_matrix_plan.md`
- `audits/cluster3_phase14a_p_only_n5_modal_report.md`
- `audits/cluster3_phase14b_c_plus_p_n5_modal_report.md`
- `audits/cluster3_phase14c_g_plus_c_plus_p_n5_modal_report.md`
- `audits/cluster3_phase14d_g_plus_p_reuse_vs_rerun_decision.md`

## Artifact Status

All four n=5 development-scale matrix cells were present and non-empty:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`

The G+P cell is reused prior Phase 12 evidence approved by Phase 14d; it is not
a fresh Phase 14 Modal run.

## Four-Cell Matrix Table

| Cell | Artifact | Rows | Condition validation | Kernel / dtype | Failure counts | Initial failure counts | Grammar metadata | P attempts | C fires | Evidence role |
|---|---|---:|---|---|---|---|---|---:|---:|---|
| P | `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` | 5 | `P=5` | elementwise / fp32 | `F0_PARSE=5` | `F0_PARSE=5` | inactive; no variant/scope | 0 | 0 | Development matrix cell; insufficient F1/P signal |
| C+P | `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` | 5 | `C+P=5` | elementwise / fp32 | `F0_PARSE=5` | `F0_PARSE=5` | inactive; no variant/scope | 0 | 0 | Development matrix cell; insufficient repair signal |
| G+C+P | `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` | 5 | `G+C+P=5` | elementwise / fp32 | `None=5` | `None=5` | `grammar_active=true=5`; `template_upper_bound=5`; `diagnostic_non_primary=5` | 0 | 0 | Development matrix cell; clean-success grammar path |
| G+P | `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | 5 | `G+P=5` | elementwise / fp32 | `None=5` | `None=5` | `grammar_active=true=5`; `template_upper_bound=5`; `diagnostic_non_primary=5` | 0 | 0 | Reused Phase 12 development matrix cell; clean-success grammar path |

Total frozen matrix rows: 20.

## Row And Schema Validation

Validation command used `.venv/bin/python` and `Cluster3EvalRow.from_dict` for
every row in all four artifacts.

Result:

- P: 5 rows, schema OK.
- C+P: 5 rows, schema OK.
- G+C+P: 5 rows, schema OK.
- G+P: 5 rows, schema OK.

The validation also confirmed condition, kernel class, and dtype invariants for
each cell:

- each cell has exactly five rows;
- all rows match the expected condition for their artifact;
- all rows have `kernel_class=elementwise`;
- all rows have `dtype=fp32`.

## Content Hash Validation

Content hash sidecars exist and validated with the repository helper functions
`load_content_hash_sidecar` and `validate_content_hash_sidecar_for_rows`.

| Artifact | JSONL SHA256 | Sidecar | Sidecar SHA256 |
|---|---|---|---|
| `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` | `d9d92f6a809bf3786eefacc8a8ae20358fc92a1aa684cf3ffd5ea12763a693ea` | `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl.hashes.json` | `3928d54583e5d74aac38bd73fb1d43c8a577dc5c84471d719da065f6ca64aad7` |
| `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` | `7ce0606820a3de8735b163ea7cf8e34d1681ddac68fbab35f3ce4364d1c03930` | `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl.hashes.json` | `2199348868fe3ab292cb0bad9ad486d592c733f7c45e4567d3ae07237b86302c` |
| `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` | `90985813219ea1dd461bdc7b06a4c8af0ad25aa730ed1f4564a5bf12784154c0` | `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl.hashes.json` | `e07225fb62f064a68643272c5cccb977ea8919bac30b9cc83d5c9d7c8f4e7fde` |
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | `9447d987655cba5aadb79d42d115f6baa989b1ea36ba7bf6023975d656e54423` | `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json` | `54f3d06c5749bf27b856f0ef79545f6dda1dbb3199a7665726952d59125efb68` |

## Grammar Metadata Summary

Grammar metadata matches the intended matrix semantics:

- P and C+P rows have `grammar_active=false` and no grammar variant/scope.
- G+C+P and G+P rows have `grammar_active=true` on all rows.
- G+C+P and G+P rows record `template_upper_bound` and
  `diagnostic_non_primary` in nested generated metadata.

The template grammar cells remain diagnostic/non-primary grammar evidence.

## P/C Signal Summary

The four-cell matrix is frozen as development-scale condition coverage only.
Repair signal is limited:

- P: `F1_COMPILE` seeds `0`; P attempts `0`; C fires `0`.
- C+P: `F1_COMPILE` seeds `0`; initial F2 rows `0`; P attempts `0`; C fires `0`.
- G+C+P: `F1_COMPILE` seeds `0`; initial F2 rows `0`; P attempts `0`; C fires `0`.
- G+P: `F1_COMPILE` seeds `0`; P attempts `0`; C fires `0`.

This matrix does not provide P-lift, C-lift, pass@k, statistical, correctness
improvement, paper-scale, n=20, or performance evidence.

## Boundary Scan Result

Boundary scans were run against only the four valid matrix artifacts.

Private-eval / hidden-shape / correctness-set scan:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" \
  outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl \
  outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl \
  outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl \
  outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
```

Result: no matches.

Performance/profiler/timing scan:

```bash
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" \
  outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl \
  outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl \
  outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl \
  outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
```

Result: no matches.

## Unsupported Claim Audit

Command:

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|correctness improvement|performance improvement|speedup|profiler result|timing result|full 2\\^3 complete|statistically significant" docs audits cluster3/README.md
```

The scan returned matches in planning text, caveats, prohibitions, historical
reports, command transcripts, and tests. Manual review found no disallowed
completed-evidence claims. Matches that mention speedup, profiler, timing,
paper-scale, n=20, pass@k, P/C lift, correctness improvement, full 2^3, or
statistical significance are framed as caveats, future work, out-of-scope
language, blocked status, or prohibited claim boundaries.

## Tests Run

Cluster 3 test suite:

```bash
.venv/bin/python -m pytest cluster3/tests -v
```

Result: 744 passed.

Shared analyzer/factorial sanity:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v
```

Result: 128 passed, 480 deselected.

## Regression Checks

Full regression:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: stopped only at the known pre-existing Cluster 1 docs-lock failure:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Summary before stop: 130 passed, 7 skipped, 1 failed.

No new regression was observed.

## Artifact Registry Status

`docs/05_artifacts_and_results_registry.md` was updated to register the Phase
14e four-cell n=5 matrix freeze as development-scale condition coverage only.
The registry continues to label all four cells as non-paper-scale, non-pass@k,
non-lift, non-statistical, non-correctness-improvement, and non-performance
evidence.

## Negative Scope Verification

No Modal, GPU, generation, experiment, n=20, paper-scale, profiling, timing,
speedup, performance, RL, grammar, hash re-recording, or raw output mutation
was performed.

Allowed documentation-only files were updated for the freeze:

- `audits/cluster3_phase14e_four_cell_n5_matrix_freeze_report.md`
- `docs/05_artifacts_and_results_registry.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

## Go/No-Go Recommendation

Recommendation: freeze complete with warnings.

The four-cell n=5 development matrix can be treated as frozen development-scale
condition coverage. It is not sufficient for paper-scale claims, pass@k claims,
P/C lift claims, statistical claims, correctness-improvement claims, or
performance claims.

Before any broader run, require a separate explicit approval packet that names
the next scope, artifact paths, stop conditions, and claim boundaries.

## Classification

`PHASE14E_FOUR_CELL_N5_MATRIX_FREEZE_COMPLETE_WITH_WARNINGS`

The warning is the unchanged full-regression stop at the known Cluster 1
documentation-language lock test.

## Next-Step Recommendation

Do not run Modal or n=20 from this state. The next suitable step is a separate
paper-scale readiness/go-no-go plan or a local analysis-planning pass that
continues to preserve the development-scale and no-lift/no-performance claim
boundaries.
