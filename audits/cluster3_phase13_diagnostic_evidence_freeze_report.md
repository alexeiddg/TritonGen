# Cluster 3 Phase 13 Diagnostic Evidence Freeze Report

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

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
| `cluster3/tests/test_p_repair_f1_fixtures.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/test_run_cluster3_modal_cli.py` | `expected_prior_phase_uncommitted_change` |
| `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py` | `expected_prior_phase_uncommitted_change` |

No unrelated or unknown dirty paths were present at preflight. The tree is not clean enough for broader expansion without a commit/provenance freeze.

## Prior Reports Status

All required prior reports were present:

- `audits/cluster3_phase11_modal_hydration_remediation_report.md`
- `audits/cluster3_phase12_gp_template_grammar_n5_report.md`
- `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md`
- `audits/cluster3_phase12c_f1_fixture_alignment_report.md`
- `audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md`
- `audits/cluster3_phase12e_initial_f2_c_loop_modal_report.md`

## Artifact Status

All required valid evidence artifacts existed and were non-empty:

| Artifact | Status |
|---|---|
| `outputs/cluster3/p_smoke_l4_n1.jsonl` | present / non-empty |
| `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | present / non-empty |
| `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl` | present / non-empty |
| `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl` | present / non-empty |

Known blocked zero-row artifacts were recorded in `docs/05_artifacts_and_results_registry.md` and the Phase 11/12b reports as blocked/non-evidence. They were not treated as valid smoke, F1/P-loop, schema-row, pass@k, lift, or performance evidence.

## Evidence Matrix

| Phase | Artifact | Condition | Rows | Observed route / branch | P fired? | C fired? | Classification | Evidence role |
|---|---|---:|---:|---|---|---|---|---|
| Phase 11 P smoke | `outputs/cluster3/p_smoke_l4_n1.jsonl` | `P` | 1 | initial terminal `F0_PARSE` | no; `p_not_applicable` | no | `PHASE11_MODAL_HYDRATION_REMEDIATION_COMPLETE_WITH_WARNINGS` | Modal/schema/logger/provenance plumbing only |
| Phase 12 G+P n=5 | `outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl` | `G+P` | 5 | clean-success G+P template path; F1 seeds `0`; P attempts `0`; terminal `None=5` | no | no | `PHASE12_GP_TEMPLATE_N5_COMPLETE_INSUFFICIENT_F1_SIGNAL_WITH_WARNINGS` | bounded development plumbing; insufficient F1 signal |
| Phase 12d aligned F1 | `outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl` | `G+P` | 1 | observed seed `F1_COMPILE`; P stop reason `p_compile_repaired_then_success`; terminal `None` | yes | no | `PHASE12D_ALIGNED_F1_P_LOOP_COMPLETE_WITH_WARNINGS` | `F1_COMPILE` -> P-loop branch coverage |
| Phase 12e initial F2 | `outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl` | `G+C+P` | 1 | observed initial `F2_NUMERIC_LARGE`; `c_loop_source=initial_f2`; terminal `None` | no | yes | `PHASE12E_INITIAL_F2_C_LOOP_COMPLETE_WITH_WARNINGS` | initial-F2 -> C-loop branch coverage under `G+C+P` |

Required caveats: this matrix is diagnostic-scale only. It is not paper-scale, not n=20, not pass@k evidence, not P-lift evidence, not C-lift evidence, and not performance/speedup/profiler evidence.

## Row And Schema Validation

Command:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from cluster3.results.dataclass import Cluster3EvalRow

artifacts = {
    "phase11_p_smoke": ("outputs/cluster3/p_smoke_l4_n1.jsonl", 1),
    "phase12_gp_n5": ("outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl", 5),
    "phase12d_f1_p": ("outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl", 1),
    "phase12e_f2_c": ("outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl", 1),
}

for name, (path_s, expected_count) in artifacts.items():
    path = Path(path_s)
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert len(rows) == expected_count, (name, len(rows), expected_count)
    for row in rows:
        Cluster3EvalRow.from_dict(row)
    print(name, "rows", len(rows), "schema_ok")
PY
```

Output:

```text
phase11_p_smoke rows 1 schema_ok
phase12_gp_n5 rows 5 schema_ok
phase12d_f1_p rows 1 schema_ok
phase12e_f2_c rows 1 schema_ok
```

## Content Hash Validation

All expected `.hashes.json` sidecars existed:

```text
outputs/cluster3/p_smoke_l4_n1.jsonl sidecar_exists True
outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl sidecar_exists True
outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl sidecar_exists True
outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl sidecar_exists True
```

Repository helper validation using `load_content_hash_sidecar` and `validate_content_hash_sidecar_for_rows` passed for all four valid artifacts.

## Boundary Scan Summary

Commands:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing" outputs/cluster3/*.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/*.jsonl
```

Both scans returned no matches across the top-level Cluster 3 JSONL files. The zero-row blocked files were not treated as valid evidence rows.

## Unsupported Claim Audit

Command:

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|performance improvement|speedup|profiler result|timing result|full 2\^3 complete|statistically significant" docs audits cluster3/README.md
```

Manual review found no disallowed completed-evidence claims. Matches were caveats, prohibitions, historical report text, future/planning sections, boundary-test names, or explicit statements that no paper-scale/pass@k/lift/performance claim is made.

## Tests Run

- `.venv/bin/python -m pytest cluster3/tests -v` -> 744 passed
- `.venv/bin/python -m pytest shared/tests -k "factorial or analyzer" -v` -> 128 passed, 480 deselected

## Regression Checks

Command:

```bash
.venv/bin/python -m pytest cluster1/tests cluster2/tests shared/tests cluster3/tests -x
```

Result: failed only at the known pre-existing Cluster 1 docs-lock test:

```text
cluster1/tests/test_documentation_language_lock.py::test_committed_docs_lock_primary_and_reference_grammar_roles
```

Summary before `-x` stop: 1 failed, 130 passed, 7 skipped. No new regression was observed before the known failure.

## Provenance Status

Evidence artifacts, row counts, schema validation, and content-hash sidecars validate. The remaining provenance caveat is the dirty working tree from expected prior Phase 12b/12c/12d/12e changes. Broader expansion should wait until those implementation/test/fixture/docs/report/artifact changes are committed or otherwise frozen.

## Files Added

- `audits/cluster3_phase13_diagnostic_evidence_freeze_report.md`

## Files Modified

Phase 13 documentation/handoff updates:

- `docs/05_artifacts_and_results_registry.md`
- `.contracts/agentic/preliminary_report_handoff/phase_state.md`
- `docs/handoff/document_version_registry.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/handoff/agentic_document_hub.md`

Pre-existing uncommitted tracked Cluster 3 paths remained dirty from prior phases:

- `cluster3/experiments/run_cluster3_modal.py`
- `cluster3/tests/test_docs_consistency.py`
- `cluster3/tests/test_p_repair_f1_fixtures.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `cluster3/tests/fixtures/f1_compile_kernels/launcher_signature_valid_compile_error.py`

## Negative Scope Verification

No Modal command was invoked. No GPU job, n=20, n=5, paper-scale run, generation, experiment, RL, profiling, timing, Nsight, NCU, speedup, latency, throughput, or performance measurement was run.

No output artifact was modified in Phase 13. `git diff -- outputs` returned no diff. Forbidden implementation scope checks returned no diff for Cluster 1, Cluster 2, shared analysis/eval, Cluster 3 feedback/results/modal/replay/contracts, grammar files, or analyzer outputs.

## Classification

`PHASE13_HOLD_FOR_COMMIT_AND_PROVENANCE_FREEZE`

All diagnostic evidence validates, tests pass, boundary scans pass, and no unsupported claims were found. The hold is specifically for dirty-tree/provenance freeze before any broader run.

## Go / No-Go Recommendation

`HOLD_FOR_COMMIT_AND_PROVENANCE_FREEZE`

Do not run broader development-scale or paper-scale work until the current prior-phase code/test/fixture/docs/report/artifact state is committed or otherwise frozen. After that freeze, the diagnostic Cluster 3 v1 evidence is ready for an optional separately approved non-paper-scale n=5 matrix, not for n=20 paper-scale.
