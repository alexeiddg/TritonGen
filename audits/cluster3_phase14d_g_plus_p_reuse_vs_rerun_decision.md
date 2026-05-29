# Cluster 3 Phase 14d G+P Reuse Vs Rerun Decision Report

## Preflight Git Status

Initial git status command:

`git status --short`

Exact output:

```text
```

Dirty path classification: no dirty paths were present at preflight.

No Modal, GPU, generation, experiment, n=5 execution, n=20 execution,
paper-scale execution, profiler/timing/performance work, output mutation, hash
re-recording, or source mutation was performed in this phase.

## Prior Report And Artifact Status

Required prior reports exist:

- `audits/cluster3_phase12_gp_template_grammar_n5_report.md`
- `audits/cluster3_phase14_n5_condition_matrix_plan.md`
- `audits/cluster3_phase14a_p_only_n5_modal_report.md`
- `audits/cluster3_phase14b_c_plus_p_n5_modal_report.md`
- `audits/cluster3_phase14c_g_plus_c_plus_p_n5_modal_report.md`

Required artifacts exist:

- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`
- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`

## Phase 12 G+P Artifact Comparability Audit

The Phase 12 G+P artifact was compared against the Phase 14 matrix-cell
requirements using `Cluster3EvalRow.from_dict`.

Validation output:

```text
row_count 5
conditions {'G+P': 5}
kernel_classes {'elementwise': 5}
dtypes {'fp32': 5}
grammar_active {True: 5}
grammar_variants {None: 5}
grammar_claim_scopes {None: 5}
generated_grammar_variants {'template_upper_bound': 5}
generated_grammar_claim_scopes {'diagnostic_non_primary': 5}
failure_codes {None: 5}
initial_failure_codes {None: 5}
p_attempted 0
```

The artifact is technically comparable to the planned Phase 14 `G+P`
elementwise/fp32 n=5 matrix cell:

- row count is exactly 5;
- condition is `G+P` for all rows;
- `kernel_class` is `elementwise` for all rows;
- `dtype` is `fp32` for all rows;
- `grammar_active=true` for all rows;
- nested `generated_metadata.grammar_variant=template_upper_bound` for all rows;
- nested `generated_metadata.grammar_claim_scope=diagnostic_non_primary` for all rows;
- all rows are schema-valid;
- all rows are clean successes with `failure_code=None`;
- zero `F1_COMPILE` seeds and zero P attempts were observed.

The only metadata nuance is representational: `grammar_variant` and
`grammar_claim_scope` are null at the top level, while the canonical row
metadata records the values under `generated_metadata`. This matches the
Phase 14c matrix-cell convention and is acceptable for reuse.

## Row Schema Validation

All five rows in `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` validate
with `Cluster3EvalRow.from_dict`.

## Content Hash Validation

`outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl.hashes.json` exists and
validates with `load_content_hash_sidecar` and
`validate_content_hash_sidecar_for_rows` after parsing all five rows as
`Cluster3EvalRow` instances.

Artifact size and SHA256:

- JSONL size: 23905 bytes
- JSONL SHA256: `9447d987655cba5aadb79d42d115f6baa989b1ea36ba7bf6023975d656e54423`
- Sidecar size: 2218 bytes
- Sidecar SHA256: `54f3d06c5749bf27b856f0ef79545f6dda1dbb3199a7665726952d59125efb68`

## Grammar Metadata Validation

All five rows record `grammar_active=true`.

Nested `generated_metadata` records:

- `grammar_variant=template_upper_bound`: 5 rows
- `grammar_claim_scope=diagnostic_non_primary`: 5 rows

The artifact remains a template upper-bound diagnostic/non-primary grammar
route, not primary task-agnostic grammar evidence.

## Boundary Scan Result

Boundary scan commands found no matches:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing|allclose" outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark|throughput" outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl
```

No private-eval, hidden-shape, profiler, timing, speedup, latency, throughput,
benchmark, or performance leakage was found.

## Tests Run

- `.venv/bin/python -m pytest cluster3/tests -v`: 744 passed.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`:
  128 passed, 480 deselected.

## Regression Checks

Full regression command:

`.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`

The run stopped only at the known pre-existing Cluster 1 docs-lock failure:

`cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`

Summary: 1 failed, 130 passed, 7 skipped.

No new regression was observed.

## Reuse Vs Rerun Decision

Decision: reuse the Phase 12 G+P artifact as the Phase 14 matrix `G+P`
elementwise/fp32 n=5 cell.

Rationale:

- the row count, condition, kernel class, dtype, schema, grammar-active status,
  grammar metadata, content hash sidecar, and boundary scans satisfy the Phase
  14 matrix-cell requirements;
- the artifact was already generated through the bounded Cluster 3 Modal runner
  path under `--condition G+P`, `--kernel-class elementwise`, `--scale-tier
  development`, `--n 5`, `--dtypes fp32`, and `--grammar-variant
  template_upper_bound`;
- a fresh Modal rerun would duplicate an already valid comparable cell without
  improving evidence quality for this decision gate.

The artifact must be labeled as reused prior Phase 12 evidence, not as a fresh
Phase 14d Modal run. It remains development-scale only and observed
insufficient repair signal: zero `F1_COMPILE` seeds and zero P attempts.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to record that
`outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` is approved for reuse as
the Phase 14 G+P matrix cell with explicit caveats.

The registry continues to state that the artifact is development-scale only,
template upper-bound diagnostic/non-primary grammar evidence only, not
paper-scale, not pass@k evidence, not P-lift evidence, not statistical
evidence, not correctness-improvement evidence, and not performance evidence.

## Negative Scope Verification

Phase 14d did not invoke Modal, run GPU jobs, run n=5 execution, run n=20,
run paper-scale, run generation, run experiments, modify outputs, modify
Cluster 1 source, modify Cluster 2 source, modify shared analyzer/eval source,
modify grammar files, re-record hashes, run RL, or modify implementation files.

Allowed changes are limited to this decision report, the artifact registry, and
required handoff/routing docs.

## Classification

`PHASE14D_REUSE_GP_CELL_APPROVED_WITH_WARNINGS`

Rationale: the Phase 12 `G+P` artifact is comparable and reusable; row/schema,
grammar metadata, hash, and boundary validation passed; local tests passed;
full regression failed only at the known Cluster 1 docs-lock failure.

## Next-Step Recommendation

Do not run a fresh `G+P` n=5 rerun, n=20, paper-scale, all-condition, or
performance/profiling work from Phase 14d.

The optional non-paper-scale n=5 matrix now has four populated cells:

- `P`: `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `C+P`: `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`
- `G+C+P`: `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`
- `G+P`: reused `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`

Proceed only with a separate explicit approval for a matrix freeze/audit phase
that validates the four-cell development matrix together and preserves all
development-scale and insufficient-signal caveats.
