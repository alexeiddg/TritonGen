# Cluster 3 Phase 11 Modal Hydration Remediation Report

## Task

Cluster 3 Phase 11 Modal runner hydration remediation and n=1 P smoke rerun.

## Preflight Git Status

Initial remediation preflight command:

```text
git status --short
```

Initial remediation preflight output:

```text

```

After the narrow source fix, the working tree contained only expected Phase 11
remediation edits:

```text
 M cluster3/experiments/run_cluster3_modal.py
 M cluster3/tests/test_run_cluster3_modal_cli.py
```

Classification: expected Phase 11 Cluster 3 hydration remediation source/test
changes.

## Blocked Artifact Status

The prior blocked Phase 11 report existed at
`audits/cluster3_phase11_modal_n1_smoke_report.md`.

The failed attempt left:

- `outputs/cluster3/p_smoke_l4_n1.jsonl`, size 0 bytes, row count 0.
- `outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json`, size 2216 bytes.

The zero-row file was not treated as valid smoke evidence. Before the rerun, the
blocked evidence was archived without deletion:

| Path | Status | SHA256 |
|---|---|---|
| `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.jsonl` | archived zero-byte blocked attempt, row_count=0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.hashes.json` | archived logger-created sidecar from blocked attempt | `4d54798cc47072e4c04278d63ff33b0a01b8a3e1dc1abcf3527834b43b607aca` |

## Failure Reproduced Or Confirmed

The prior report recorded this failure before any row generation:

```text
modal.exception.ExecutionError: Function has not been hydrated with the metadata it needs to run on Modal, because the App it is defined on is not running.
```

The blocked artifact state confirmed the failure left zero rows and no schema
validation target.

## Root-Cause Classification

`MISSING_MODAL_RUN_CONTEXT`

The direct venv command imported Cluster 2 Modal function objects and called
`.remote(...)` outside a running Modal app context. The symptom was a local
function object that had not been hydrated by `modal run`.

Repository pattern search showed that Cluster 2 uses an existing
`modal run -m` local-entrypoint path in
`cluster2/experiments/run_cluster2_modal.py`. Cluster 3 had no equivalent
Modal local entrypoint, so direct execution could parse the CLI but could not
hydrate Cluster 2 Modal functions.

## Fix Applied

Narrow Cluster 3 adapter/invocation fix only:

- Added a `modal_entrypoint(...)` wrapper in `cluster3/experiments/run_cluster3_modal.py`
  that delegates to the existing argparse `main(...)` path.
- Registered that entrypoint only when Modal is already imported, preserving
  cheap normal imports and avoiding module-level Modal import in ordinary tests.
- Reused the existing shared Modal app and existing Cluster 2 generation and
  correctness Modal functions.
- Used the unique Modal local-entrypoint tag `cluster3_modal_entrypoint` to avoid
  collisions when Cluster 1, Cluster 2, and Cluster 3 experiment modules are
  imported in the same process.
- Added focused tests for entrypoint delegation and mutually exclusive write
  modes.

No new Modal app, image, function, queue, secret, volume, timeout, retry,
profiling path, grammar change, analyzer change, Cluster 1 change, or Cluster 2
source change was made.

## Exact Corrected Invocation Command

Modal CLI discovery confirmed the corrected entrypoint is exposed:

```text
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --help
```

Key exposed options included:

```text
--condition TEXT [required]
--kernel-class TEXT [required]
--scale-tier TEXT [required]
--n INTEGER [required]
--dtypes TEXT
--p-repair-budget INTEGER
--c-repair-budget INTEGER
--output TEXT [required]
--overwrite / --no-overwrite
```

Corrected smoke command:

```text
.venv/bin/python -m modal run -m cluster3.experiments.run_cluster3_modal --condition P --kernel-class elementwise --scale-tier smoke --n 1 --dtypes fp32 --p-repair-budget 5 --c-repair-budget 0 --output outputs/cluster3/p_smoke_l4_n1.jsonl --overwrite
```

## Rerun Execution Summary

The rerun completed through the corrected `modal run -m` hydration path.

Modal local output:

```json
{"output": "outputs/cluster3/p_smoke_l4_n1.jsonl", "route_audit": [{"c_loop_calls": 0, "condition": "P", "correctness_calls": 1, "generation_calls": 1, "p_loop_calls": 0, "route": "initial_terminal"}], "rows": 1, "write_mode": "overwrite"}
```

Run URL shown by Modal:

```text
https://modal.com/apps/alexeiddggpt/tritongen-dev/ap-T7i839uP1dXf1LEZIjAk60
```

The run stayed within scope: one condition, one elementwise fp32 smoke cell,
one generated initial candidate, one correctness call, no C loop, no P loop,
and one logged row.

## Output Artifact Paths

Validated smoke artifacts:

| Path | Status | SHA256 | Size |
|---|---|---|---:|
| `outputs/cluster3/p_smoke_l4_n1.jsonl` | validated n=1 P smoke JSONL, row_count=1 | `361a2dd708b028aa96b785d4f0aaa802134ec4df7092b3371b51c7ab7698e32c` | 4662 bytes |
| `outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json` | logger-created content-hash sidecar, schema_version=1 | `b7ee6a807cc3258d470ab37ac51b7f99ac9b4e27c8240144234fe775fb619483` | 2216 bytes |

Archived blocked attempt:

- `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.jsonl`
- `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.hashes.json`

No `.sha256` or `.manifest.json` sidecar was produced by the existing logger.

## Row Count

Post-rerun row-count check:

```text
outputs/cluster3/p_smoke_l4_n1.jsonl 1
```

## Row Schema Validation Result

Passed.

Validation used repository schema/logger APIs:

- `Cluster3EvalRow.from_dict(...)`
- `load_content_hash_sidecar(...)`
- `validate_content_hash_sidecar_for_rows(...)`
- `CLUSTER3_RESULTS_SCHEMA_VERSION == 1`

Observed row facts:

- `condition`: `P`
- `initial_failure_code`: `F0_PARSE`
- `failure_code`: `F0_PARSE`
- `p_repair_attempted`: `False`
- `p_repair_attempt_count`: `0`
- sidecar `schema_version`: `1`

The JSONL row itself does not serialize a top-level `schema_version`; the v1
schema is enforced by the `Cluster3EvalRow` dataclass and the logger sidecar.

## P Firing Summary

P did not fire:

- `p_loop_calls`: 0
- `p_repair_attempted`: false
- `initial_failure_code`: `F0_PARSE`

This satisfies the Phase 11 policy: P fires only for `F1_COMPILE`; because the
initial result was `F0_PARSE`, P remained inactive.

## Boundary Scan Summary

Private-eval scan:

```text
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|allclose|torch.testing" outputs/cluster3/*.jsonl
```

Result: no matches.

Performance/profiler scan:

```text
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/*.jsonl
```

Result: no matches.

No private eval shape details, Level 2 leakage into P feedback, profiler,
speedup, timing, latency, or performance content was found in the smoke row.

## Artifact Registry Update

`docs/05_artifacts_and_results_registry.md` was updated to:

- preserve the blocked zero-row attempt record and archived paths;
- register `outputs/cluster3/p_smoke_l4_n1.jsonl` as a validated Phase 11 n=1
  smoke-only artifact;
- record condition `P`, row_count=1, schema version 1, hash/sidecar paths, and
  smoke-only caveats;
- state that the artifact is not development-scale, not paper-scale, not
  evidence of P lift, not a full 2^3 result, and not a performance/speedup
  artifact.

## Tests Run

Pre-rerun gates:

- `.venv/bin/python -m pytest cluster3/tests -v` -> 726 passed before source
  changes; 728 passed after the hydration fix.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` ->
  128 passed, 480 deselected.
- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v`
  -> 74 passed after focused entrypoint tests were added.
- `.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x`
  -> final pre-rerun result failed only at the known Cluster 1 docs-lock test
  after 130 passed and 7 skipped.

Intermediate remediation note: an earlier full-regression pass after the first
entrypoint patch exposed a duplicate generic Modal local-entrypoint name during
test collection. The fix was tightened to register a unique
`cluster3_modal_entrypoint` tag, after which targeted, Cluster 3, analyzer, and
full-regression gates returned to the expected state.

Post-rerun gates:

- row-count check -> 1 row.
- repository row/sidecar validation -> passed.
- private-eval boundary scan -> no matches.
- performance/profiler boundary scan -> no matches.
- `.venv/bin/python -m pytest cluster3/tests/test_docs_consistency.py -v` ->
  14 passed after registry/handoff updates.
- `.venv/bin/python -m pytest cluster3/tests/test_run_cluster3_modal_cli.py -v`
  -> 74 passed after the final entrypoint registration fix.
- `.venv/bin/python -m pytest cluster3/tests -v` -> 728 passed.
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` ->
  128 passed, 480 deselected.

## Regression Checks

Final full regression:

```text
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: failed only at the known pre-existing Cluster 1 docs-lock test after
130 passed and 7 skipped:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

No new regression was observed before the stop point.

## Cost And Spend Notes

The only paid/remote rerun was the authorized Phase 11 n=1 P smoke. It used the
existing shared Modal app and existing Cluster 2 L4 generation/correctness
surfaces. The route audit recorded one generation call and one correctness
call. No n=5, n=20, all-task, all-condition, profiling, timing, Nsight, NCU, or
performance measurement run was started.

No exact dollar cost was available from local command output.

## Per-Phase Docs Updates

Updated:

- `audits/cluster3_phase11_modal_n1_smoke_report.md`
- `audits/cluster3_phase11_modal_hydration_remediation_report.md`
- `docs/05_artifacts_and_results_registry.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

`docs/handoff/stale_docs_inventory.md` changed because the Cluster 3 artifact
freshness status changed from blocked/no validated row to one validated
smoke-only row. `docs/handoff/agentic_document_hub.md` changed because the
Phase 12 read set now includes this remediation report and the validated
smoke-only caveats.

## Negative Scope Verification

Allowed Phase 11 remediation changes:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `outputs/cluster3/p_smoke_l4_n1.jsonl`
- `outputs/cluster3/p_smoke_l4_n1.jsonl.hashes.json`
- `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.jsonl`
- `outputs/cluster3/blocked/p_smoke_l4_n1.blocked_attempt_001.hashes.json`
- this remediation report
- required handoff/registry docs

Forbidden-scope implementation diff check:

```text
git diff -- cluster1 cluster2 shared/analysis shared/eval cluster3/feedback cluster3/results cluster3/replay cluster3/contracts
```

Result: no diff.

Tracked diff after final validation:

```text
cluster3/experiments/run_cluster3_modal.py
cluster3/tests/test_docs_consistency.py
cluster3/tests/test_run_cluster3_modal_cli.py
```

Tracked diff stat:

```text
cluster3/experiments/run_cluster3_modal.py    | 126 ++++++++++++++++++++++++++
cluster3/tests/test_docs_consistency.py       |  17 +++-
cluster3/tests/test_run_cluster3_modal_cli.py |  72 +++++++++++++++
3 files changed, 211 insertions(+), 4 deletions(-)
```

The report, registry, handoff docs, and output artifacts are project-owned
ignored paths and therefore do not appear in tracked `git status --short`.

No Cluster 1 source, Cluster 2 source, shared analyzer/eval source, grammar
files, Cluster 3 feedback/results/modal/replay/contracts implementation, Modal
harness source, analyzer output JSON, n=5 output, n=20 output, or grammar hash
recording was modified.

## Classification

`PHASE11_MODAL_HYDRATION_REMEDIATION_COMPLETE_WITH_WARNINGS`

Warnings are limited to the unchanged known Cluster 1 docs-lock regression.

## Next-Step Recommendation

Do not start Phase 12 in this task. Phase 11 now has validated n=1 P smoke
evidence, but any n=5 development-scale Phase 12 run requires a separate
explicit approval and should read this remediation report before execution.
