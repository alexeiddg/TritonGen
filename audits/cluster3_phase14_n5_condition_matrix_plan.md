# Cluster 3 Phase 14 n=5 Condition Matrix Plan

## Executive Summary

Phase 14 is planning-only. No Modal command, GPU job, generation, experiment,
n=5 execution, n=20 execution, paper-scale run, profiler, timing, speedup, or
output mutation was performed.

The smallest optional next non-paper-scale matrix should run one n=5 condition
cell at a time, with `elementwise` only, `fp32` only, and a separate explicit
approval before each Modal run. The recommended first execution cell is
Phase 14a: P-only n=5 elementwise fp32.

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

```text
```

The working tree was clean at preflight. No dirty path classification was
required.

## Prior Evidence Status

The required prior report exists:

- `audits/cluster3_phase13b_commit_provenance_freeze_report.md`

The required diagnostic artifacts exist and are non-empty:

- `outputs/cluster3/p_smoke_l4_n1.jsonl`
- `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl`
- `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl`
- `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl`

Current evidence state:

| Evidence | Artifact | Condition | Rows | Observed route | P fired | C fired | Role |
|---|---|---:|---:|---|---|---|---|
| Phase 11 P smoke | `outputs/cluster3/p_smoke_l4_n1.jsonl` | `P` | 1 | initial terminal, `F0_PARSE` | no | no | Modal/schema/logger/provenance plumbing only |
| Phase 12 G+P n=5 | `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | `G+P` | 5 | clean-success initial terminal | no; zero F1 seeds | no | G+P template development plumbing; insufficient F1 signal |
| Phase 12d aligned F1 | `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl` | `G+P` | 1 | `F1_COMPILE` seed -> P | yes; `p_compile_repaired_then_success` | no | F1_COMPILE -> P-loop branch coverage |
| Phase 12e initial F2 | `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl` | `G+C+P` | 1 | `F2_NUMERIC_LARGE` seed -> C | no | yes; `c_loop_source=initial_f2` | initial-F2 -> C-loop branch coverage under G+C+P |

These artifacts are diagnostic-scale or development-scale only. They are not
paper-scale, pass@k, P-lift, C-lift, statistical-significance, performance,
speedup, profiler, or timing evidence.

## Proposed n=5 Condition Matrix

| Condition | Grammar active | Correctness feedback active | Compile feedback active | Intended kernel_class | Dtype | n | Expected artifact path | Expected row count | Expected route coverage | Approval status |
|---|---|---|---|---|---|---:|---|---:|---|---|
| `P` | no | no | yes | `elementwise` | `fp32` | 5 | `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` | 5 | P-only initial classifications; P fires only on any naturally occurring `F1_COMPILE` seeds; no C route | Not approved; requires separate Phase 14a authorization |
| `G+P` | yes, `template_upper_bound` | no | yes | `elementwise` | `fp32` | 5 | `outputs/cluster3/matrix_n5_g_plus_p_elementwise_fp32.jsonl` if rerun is required | 5 | G+P template route; P fires only on `F1_COMPILE`; expected clean-success route may repeat Phase 12 behavior | Not approved; Phase 14d should decide reuse vs rerun |
| `C+P` | no | yes | yes | `elementwise` | `fp32` | 5 | `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl` | 5 | C-containing non-G route; P only on `F1_COMPILE`; C only on eligible F2 failures | Not approved; requires separate Phase 14b authorization |
| `G+C+P` | yes, `template_upper_bound` | yes | yes | `elementwise` | `fp32` | 5 | `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl` | 5 | Combined G/C/P route; P only on `F1_COMPILE`; C on eligible F2 failures, including initial-F2 if observed | Not approved; requires separate Phase 14c authorization |

The existing Phase 12 artifact
`outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` may be reused only as a
clearly labeled prior-evidence `G+P` development cell. For a uniform Phase 14
matrix, a fresh `G+P` rerun should use
`outputs/cluster3/matrix_n5_g_plus_p_elementwise_fp32.jsonl`. The recommended
decision is to defer reuse vs rerun until after the missing P-only and
C-containing cells are evaluated.

## Recommended Execution Order

1. Phase 14a: `P` n=5, `elementwise`, `fp32`.
2. Phase 14b: `C+P` n=5, `elementwise`, `fp32`.
3. Phase 14c: `G+C+P` n=5, `elementwise`, `fp32`.
4. Phase 14d: decide whether to reuse the existing Phase 12 `G+P` n=5 artifact
   as prior evidence or rerun a fresh Phase 14-controlled `G+P` matrix cell.

Rationale:

- `G+P` already has a validated n=5 artifact from Phase 12.
- P-only behavior beyond the n=1 smoke has not been exercised.
- C-containing n=5 cells are missing.
- One condition per approval limits spend and isolates failures.

## Artifact Path Plan

Recommended matrix paths:

- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_g_plus_c_plus_p_elementwise_fp32.jsonl`
- `outputs/cluster3/matrix_n5_g_plus_p_elementwise_fp32.jsonl` only if a fresh
  `G+P` rerun is required

Before any future run, verify the target path does not already exist. If it
exists, stop and request explicit archive, timestamped-path, or overwrite
authorization.

## Spend And Stop Controls

Required controls for any future Phase 14a+ execution:

- one condition per explicit approval;
- n=5 maximum per approved run;
- `elementwise` only;
- `fp32` only;
- no n=20;
- no paper-scale;
- no all-task run;
- no all-condition batch unless separately approved after one-cell validation;
- no profiler, timing, latency, throughput, Nsight, NCU, speedup, benchmark, or
  performance measurement;
- output path must remain under `outputs/cluster3/`;
- stop on Modal auth, configuration, image, or remote infrastructure instability;
- stop on command expansion beyond the approved scope;
- stop on row-count mismatch;
- stop on schema validation failure;
- stop on content-hash sidecar mismatch;
- stop on P firing outside `F1_COMPILE`;
- stop on C firing outside eligible F2 conditions;
- stop on private-eval, hidden-shape, correctness-set, profiler, timing,
  speedup, or performance leakage.

## Validation Plan

For each future matrix cell:

1. Preflight `git status --short`.
2. Confirm the target output path does not exist.
3. Run pre-spend local tests:
   - `.venv/bin/python -m pytest cluster3/tests -v`
   - `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v`
   - `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
4. Execute exactly one approved Modal command.
5. Confirm the artifact exists and contains exactly five non-empty rows.
6. Validate every row with `Cluster3EvalRow.from_dict`.
7. Validate the logger-created `.hashes.json` sidecar with repository helper
   functions when available.
8. Validate condition-specific invariants:
   - every row has the requested `condition`;
   - P is attempted only when the seed or initial failure is `F1_COMPILE`;
   - C fires only for eligible F2 failures when C is active;
   - `c_loop_source` is recorded when C fires;
   - no C route fires in P-only or G+P-only cells.
9. Run boundary scans against the new artifact:
   - private-eval and hidden-shape terms;
   - profiler, timing, latency, speedup, benchmark, and performance terms.
10. Rerun Cluster 3 tests, shared analyzer/factorial sanity, and full
    regression with the known Cluster 1 docs-lock caveat.
11. Update the artifact registry and handoff docs only after the artifact
    validates.

The known acceptable full-regression warning remains:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

## Claim Boundaries

Phase 14 planning and any future n=5 condition-matrix cells must not claim:

- paper-scale completion;
- n=20 completion;
- pass@k results;
- P-lift;
- C-lift;
- correctness improvement;
- statistical significance;
- full 2^3 completion;
- performance improvement;
- speedup;
- profiler results;
- timing results.

Future n=5 matrix cells are development-scale diagnostics only unless a later
approved methodology phase explicitly promotes them with adequate validation and
claim boundaries.

## Go/No-Go Criteria For Phase 14a

Phase 14a should be authorized only if:

- this Phase 14 plan is complete;
- the working tree is clean or only Phase 14 planning docs are dirty;
- `outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl` does not already exist;
- the user explicitly authorizes the specific `P` n=5 `elementwise` `fp32`
  Modal run;
- local pre-spend tests pass or fail only at the known Cluster 1 docs-lock
  full-regression gate;
- the command is limited to one condition, one kernel class, `fp32`, and n=5;
- no profiling, timing, speedup, benchmark, or performance options are used.

## Tests Run

Command:

```bash
.venv/bin/python -m pytest cluster3/tests -v
```

Result:

```text
744 passed
```

Command:

```bash
.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v
```

Result:

```text
128 passed, 480 deselected
```

## Regression Checks

Command:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: stopped only at the known pre-existing Cluster 1 docs-lock failure:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Summary before `-x` stop:

```text
1 failed, 130 passed, 7 skipped
```

## Unsupported Claim Audit

Command:

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|performance improvement|speedup|profiler result|timing result|full 2\^3 complete|statistically significant" docs audits cluster3/README.md
```

Manual review found no unsupported completed-evidence claims. Matches were
caveats, prohibitions, future/planning text, historical reports, existing test
names, or explicit statements that no paper-scale/pass@k/lift/statistical or
performance claim is made.

## Negative Scope Verification

Phase 14 created planning and handoff documentation only. It did not invoke
Modal, run GPU jobs, execute n=5, run n=20, run paper-scale work, run
generation, run experiments, mutate `outputs/`, change Cluster 1 source, change
Cluster 2 source, change shared analyzer/eval source, modify grammar files,
re-record hashes, or run RL.

## Classification

`PHASE14_N5_MATRIX_PLAN_COMPLETE_WITH_WARNINGS`

Reason: the plan is complete; local Cluster 3 tests and shared
analyzer/factorial sanity passed; the full regression failed only at the known
Cluster 1 docs-lock failure; the unsupported-claim audit found no disallowed
completed-evidence claims; and no output/source mutation or execution occurred.

## Next-Step Recommendation

Recommended first execution cell: Phase 14a `P` n=5 `elementwise` `fp32`, using
`outputs/cluster3/matrix_n5_p_elementwise_fp32.jsonl`, only after separate
explicit user approval.
