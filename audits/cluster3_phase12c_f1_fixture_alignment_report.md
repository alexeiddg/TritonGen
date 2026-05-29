# Cluster 3 Phase 12c F1 Fixture Alignment Report

## Preflight Git Status

Exact `git status --short` at phase start:

```text
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_docs_consistency.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
```

Dirty path classification:

| path | classification | note |
| --- | --- | --- |
| `cluster3/experiments/run_cluster3_modal.py` | expected_prior_phase_uncommitted_change | Phase 12b diagnostic runner flag work already present before Phase 12c. |
| `cluster3/tests/test_docs_consistency.py` | expected_prior_phase_uncommitted_change | Existing prior-phase tracked change; not edited in Phase 12c. |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | expected_prior_phase_uncommitted_change | Phase 12b diagnostic CLI tests already present before Phase 12c. |

No unrelated, unknown, or output artifact mutation was present at preflight.

## Phase 12b Blocked Reason Confirmed

The prior report `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md` exists and records:

- `PHASE12B_BLOCKED_NO_F1_FIXTURE_SIGNAL`
- `cluster3/tests/fixtures/f1_compile_kernels/bad_constexpr.py` classified remotely as `F0_BAD_SIGNATURE`
- `cluster3/tests/fixtures/f1_compile_kernels/type_error_in_pointer_arith.py` classified remotely as `F0_BAD_SIGNATURE`

Phase 12b therefore did not validate the `F1_COMPILE -> P` branch.

## Signature Contract

The remote correctness adapter path for generated Cluster 3 `G+P` sources delegates to the existing Cluster 2 correctness request. For `kernel_class=elementwise`, that request resolves the locked Cluster 1 KernelSpec:

| field | value |
| --- | --- |
| kernel_class | `elementwise` |
| kernel_name | `relu` |
| dataset_problem_id | `19` |
| public launcher | `relu` |
| public launcher signature | `(x: torch.Tensor) -> torch.Tensor` |
| compile spec launcher | `relu` |
| compile probe shapes for fp32 | `(32,)`, `(100,)`, `(1024,)`, `(3, 257)`, `(5, 129)` |

The local and remote F0 gate uses `shared.eval.levels.level0_parse.check_parse` followed by `check_signature(source, get_kernel_spec("elementwise"))`. Signature matching is by public launcher name and parameter names; annotations are ignored for matching but still must be import/load safe.

## Old Fixture Failure Root Cause

Root-cause classification: `FIXTURE_WRONG_FUNCTION_NAME`.

The two Phase 12b fixtures were useful local P-loop text fixtures, but not remote-launcher-compatible for the selected elementwise ReLU task:

| fixture | public launcher in fixture | expected launcher | local F0 signature result |
| --- | --- | --- | --- |
| `bad_constexpr.py` | `scale(x)` | `relu(x)` | `Signature mismatch: launcher 'relu' not found` |
| `type_error_in_pointer_arith.py` | `gather(x, index)` | `relu(x)` | `Signature mismatch: launcher 'relu' not found` |

This explains the remote `F0_BAD_SIGNATURE` classification before Triton compilation.

## Candidate Fixture

Added:

`cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py`

The fixture mirrors the canonical ReLU generated surface:

- imports `torch`, `triton`, and `triton.language as tl`
- defines a Triton JIT helper `_relu_kernel`
- defines the public launcher `relu(x: torch.Tensor) -> torch.Tensor`
- allocates `out = torch.empty_like(x)`
- computes `n_elements = x.numel()`
- computes a standard 1D grid
- launches `_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)`
- returns `out`

The intended F1 trigger is an undefined symbol inside the Triton JIT body:

```python
scale = MISSING_SCALE_FACTOR + tl.full((BLOCK_SIZE,), 0.0, tl.float32)
```

Because this expression is inside the JIT body, it does not execute at Python import/signature time and should surface only when Triton compiles the kernel.

## Local F0 Alignment Validation

Local validation performed without Modal, GPU, generation, experiment execution, output mutation, or hash re-recording:

```text
parse (True, None)
signature (True, None)
ast_sanitizer True None None
```

Focused tests added/updated in `cluster3/tests/test_p_repair_f1_fixtures.py` assert that:

- the two Phase 12b fixtures fail the locked ReLU signature locally with `launcher 'relu' not found`
- the new fixture is syntactically valid
- the new fixture passes `check_signature` for `get_kernel_spec("elementwise")`
- the new fixture passes the optional Level 0 AST surface sanitizer
- the new fixture exposes functions in the expected order: `_relu_kernel`, `relu`
- the public launcher has exactly one parameter: `x`
- fake-module import plus `validate_signature(module, spec.compile_spec)` succeeds
- `F1_COMPILE` remains routed to the P loop by the dispatcher

## Expected Remote Failure

Expected remote initial failure for this aligned fixture: `F1_COMPILE`.

Rationale:

- F0 parse succeeds locally.
- F0 signature succeeds locally against the same locked `elementwise` KernelSpec used by the remote correctness adapter.
- Runtime signature inspection succeeds with fake `torch`/`triton` modules.
- The intentional error is inside the Triton JIT helper body, so it should be reached only after the remote Level 1 compile launch attempts.

This phase did not invoke Modal, so the remote classification remains a ready-to-test expectation rather than observed evidence.

## Tests Run

```text
.venv/bin/python -m pytest cluster3/tests -v
739 passed
```

```text
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
1 failed, 130 passed, 7 skipped
```

The full regression failure was the known pre-existing Cluster 1 docs-lock test:

`cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles`

Focused and auxiliary validation:

```text
.venv/bin/python -m pytest cluster3/tests/test_p_repair_f1_fixtures.py -v
15 passed

.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v
81 passed

.venv/bin/python -m compileall -q cluster3/tests cluster3/experiments
passed
```

## Negative Scope Verification

No Modal command was run. No GPU job was run. No n=20, paper-scale, development-scale, generation, experiment, RL, profiling, timing, speedup, latency, throughput, or performance measurement was run.

No `outputs/` mutation was made in Phase 12c.

Out-of-scope source areas were not edited:

- `cluster1/`
- `cluster2/`
- `shared/`
- grammar files
- `outputs/`

## Files Added

- `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py`
- `audits/cluster3_phase12c_f1_fixture_alignment_report.md`

## Files Modified

- `cluster3/tests/test_p_repair_f1_fixtures.py`

Existing dirty prior-phase tracked files remained dirty and were not part of the Phase 12c fixture alignment change:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_docs_consistency.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`

## Classification

`PHASE12C_F1_FIXTURE_ALIGNMENT_COMPLETE_WITH_WARNINGS`

Reason: a launcher-compatible F1_COMPILE candidate fixture is ready and local Cluster 3 validation passes; the full regression still fails only at the known pre-existing Cluster 1 docs-lock test.

## Next Step Recommendation

Do not run n=20. With separate explicit approval, rerun the bounded Phase 12b n=1 diagnostic using `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py` as the diagnostic seed source to observe whether the remote correctness path classifies it as `F1_COMPILE` and dispatches P.
