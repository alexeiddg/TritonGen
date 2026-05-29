# Cluster 3 Phase 11 Modal n=1 Smoke Report

## Task

Cluster 3 Phase 11 Modal n=1 smoke.

## Preflight Git Status

Exact preflight command:

```text
git status --short
```

Exact preflight output:

```text

```

## Authorization Evidence

The operator prompt included the required authorization string:

```text
I authorize Phase 11 n=1 Modal smoke execution.
```

## Dirty Path Classification

No dirty paths were present at preflight. No unrelated, unknown, or pre-existing
output/artifact changes blocked the smoke before execution.

## Required Surface Checks

The Phase 10 report existed at `audits/cluster3_phase10_documentation_report.md`.

The required implementation surfaces existed before Modal execution:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/modal/correctness_runner.py`
- `cluster3/modal/result_extraction.py`
- `cluster3/results/dataclass.py`
- `cluster3/results/logger.py`
- `cluster3/feedback/dispatcher.py`
- `cluster3/feedback/compile_error_repair.py`
- `cluster3/feedback/c_loop_adapter.py`
- `cluster3/replay/no_p_pairs.py`
- `cluster3/contracts/no_p_pair_manifest.json`

The intended output path did not exist before the smoke:
`outputs/cluster3/p_smoke_l4_n1.jsonl`.

## Known Pre-Existing Regression Status

Pre-spend full regression:

```text
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: failed only at the known pre-existing Cluster 1 docs-lock failure after
130 passed and 7 skipped:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Recorded status:
`known_pre_existing_cluster1_docs_lock_failure`.

## Command Discovery Result

Command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --help
```

Key discovered CLI shape:

```text
usage: run_cluster3_modal [-h] --condition {P,G+P,C+P,G+C+P,all}
                          [--kernel-class {elementwise,reduction,matmul,all}]
                          [--scale-tier {smoke,development,paper}] [--n N]
                          [--model-id MODEL_ID]
                          [--model-revision MODEL_REVISION]
                          [--tokenizer-revision TOKENIZER_REVISION]
                          [--grammar-variant {template_upper_bound,task_agnostic}]
                          [--dtypes DTYPES] [--temperature TEMPERATURE]
                          [--max-new-tokens MAX_NEW_TOKENS]
                          [--p-repair-budget P_REPAIR_BUDGET]
                          [--c-repair-budget C_REPAIR_BUDGET]
                          [--modal-generation-gpu MODAL_GENERATION_GPU]
                          [--modal-eval-gpu MODAL_EVAL_GPU] --output OUTPUT
                          (--overwrite | --resume)
```

The runner source confirmed that the default generation path calls
`cluster2.generation.modal_generate_c2.generate_source_c2_modal`, and the
default correctness path calls `cluster3.modal.correctness_runner.run_cluster3_correctness`.

Modal auth/account check:

- `.venv/bin/python -m modal profile current` -> `tritongen-lab-new`
- `.venv/bin/python -m modal token info` succeeded after network escalation;
  token value is intentionally not recorded in this report.
- No GPU job was run for the auth check.

## Exact Modal Smoke Command

Attempted command:

```text
.venv/bin/python -m cluster3.experiments.run_cluster3_modal --condition P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/p_smoke_l4_n1.jsonl --overwrite
```

The command preserved the Phase 11 constraints: condition `P`, smoke tier,
`n=1`, one elementwise `fp32` cell, P repair budget 5, C repair budget 0, and
output under `outputs/cluster3/`.

## Modal Execution Summary

The smoke did not complete. The runner failed immediately before any row was
written:

```text
modal.exception.ExecutionError: Function has not been hydrated with the metadata it needs to run on Modal, because the App it is defined on is not running.
```

Follow-up inspection found that Cluster 2 registers a `modal run -m` local
entrypoint via `cluster2/experiments/run_cluster2_modal.py`, while
`cluster3/experiments/run_cluster3_modal.py` currently exposes only the direct
`if __name__ == "__main__": main()` path and does not register a Modal local
entrypoint. Adding or redesigning that entrypoint would modify runner/harness
source, which was outside the Phase 11 authorization.

No retry through an ad hoc wrapper or new Modal app was attempted.

## Output Artifact Paths

The failed attempt created logger pre-row artifacts:

| Path | Status | SHA256 |
|---|---|---|
| `outputs/cluster3/p_smoke_l4_n1.jsonl` | zero-byte placeholder; not a valid smoke artifact | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json` | content-hash sidecar created before row generation | `4d54798cc47072e4c04278d63ff33b0a01b8a3e1dc1abcf3527834b43b607aca` |

No `.sha256` or `.manifest.json` sidecar was created.

These files are not registered as validated Cluster 3 smoke evidence.

## Row Count

Command:

```text
.venv/bin/python -c "from pathlib import Path; p=Path('outputs/cluster3/p_smoke_l4_n1.jsonl'); rows=[line for line in p.read_text().splitlines() if line.strip()]; print(len(rows))"
```

Result:

```text
0
```

## Row Schema Validation Result

Not run to success. There was no JSONL row to validate. The smoke therefore did
not satisfy the schema gate.

## P Firing Result

No initial candidate completed, no correctness result was returned, and P did
not fire. The Phase 11 P firing behavior is unproven by this attempt.

## Boundary Scan Result

Boundary scans against the zero-byte JSONL returned no matches:

```text
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|allclose|torch.testing" outputs/cluster3/p_smoke_l4_n1.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/p_smoke_l4_n1.jsonl
```

Because no row was written, these scans only prove that the failed placeholder
contains no leakage. They do not validate a Cluster 3 row.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to record that the
Phase 11 smoke path now has a blocked zero-row placeholder and sidecar, not a
generated or validated smoke artifact. No P result row was registered and no P
lift, full 2^3, development-scale, paper-scale, or performance claim was added.

## Tests Run

Pre-spend:

- `.venv/bin/python -m pytest cluster3/tests -v` -> 726 passed.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` -> 128 passed, 480 deselected.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x` -> failed only at the known Cluster 1 docs-lock test after 130 passed and 7 skipped.

Post-attempt:

- Row count check -> 0 rows.
- Private-eval boundary scan on zero-byte output -> no matches.
- Performance/profiler boundary scan on zero-byte output -> no matches.
- `.venv/bin/python -m pytest cluster3/tests/test_docs_consistency.py -v` ->
  first failed because the registry status wording no longer included the
  required `planned / not generated yet` phrase for every planned Cluster 3
  output path; after doc-only wording remediation, rerun -> 14 passed.
- `.venv/bin/python -m pytest cluster3/tests -v` -> 726 passed after the
  documentation wording remediation.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` ->
  128 passed, 480 deselected after the documentation updates.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  -> failed only at the known Cluster 1 docs-lock test after 130 passed and 7
  skipped after the documentation updates.

## Regression Checks

Both the pre-spend and post-documentation full `-x` regression checks failed
only at the known Cluster 1 docs-lock test. No new regression was observed
before the stop point.

## Cost And Spend Notes

- Modal auth/account check used no GPU job.
- The smoke failed before a hydrated remote function call, before image build
  logs, and before any row generation.
- No function call IDs were produced by the failed smoke.
- No evidence of GPU spend was observed in the local output.

## Negative Scope Verification

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
files, Cluster 3 implementation/test files, Modal harness files, or analyzer
output JSON files were modified.

The only new/updated artifacts from the attempted smoke are the zero-byte JSONL
placeholder and the logger-created content-hash sidecar under `outputs/cluster3/`.

## Per-Phase Docs Updates

Updated:

- `audits/cluster3_phase11_modal_n1_smoke_report.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

## Blockers

Phase 11 is blocked on Modal invocation/hydration for the Cluster 3 runner. The
direct venv Python runner can parse the intended CLI and start local
orchestration, but the first remote generation call fails because the Modal app
is not running/hydrated. The existing Cluster 2 pattern uses a `modal run -m`
local entrypoint registration; Cluster 3 does not currently expose an equivalent
entrypoint.

## Classification

Initial attempt classification:

`PHASE11_BLOCKED_MODAL_AUTH_OR_INFRA`

## Hydration Remediation Rerun

Follow-up authorization for bounded Phase 11 hydration remediation and n=1 P
smoke rerun was provided after this blocked report.

Remediation report:
`audits/cluster3_phase11_modal_hydration_remediation_report.md`

The Cluster 3 runner now exposes a Modal local entrypoint using the existing
shared app and existing Cluster 2 generation/correctness Modal functions. The
rerun command was:

```text
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/p_smoke_l4_n1.jsonl --overwrite
```

The zero-row blocked files from the initial attempt were archived under
`outputs/cluster3/blocked/`. The rerun produced exactly one schema-valid row at
`outputs/cluster3/p_smoke_l4_n1.jsonl` with the logger sidecar
`outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json`.

Rerun facts:

- row_count: 1
- condition: `P`
- schema version: `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`, enforced by
  `Cluster3EvalRow` and the content-hash sidecar
- initial_failure_code: `F0_PARSE`
- p_repair_attempted: false
- p_loop_calls: 0
- boundary scans: no private-eval or performance/profiler matches

Updated classification after remediation:

`PHASE11_MODAL_HYDRATION_REMEDIATION_COMPLETE_WITH_WARNINGS`

## Recommendation For Phase 12

Do not proceed to Phase 12 n=5 development scale in this task. Phase 11 now has
validated n=1 P smoke evidence after the hydration remediation, but Phase 12
requires separate explicit approval.
