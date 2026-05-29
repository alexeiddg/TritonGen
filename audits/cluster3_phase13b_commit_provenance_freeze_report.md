# Cluster 3 Phase 13b Commit Provenance Freeze Report

## Preflight Git Status

Command:

```bash
git status --short
```

Exact output:

```text
```

The working tree was clean at preflight.

## Commit Identity

Commands:

```bash
git rev-parse HEAD
git log -1 --oneline
```

Output:

```text
0578bd2c87f8fec0e6181ae00c2d23268ff6df73
0578bd2 Phase 13b — Commit and Provenance Freeze Verification
```

## Prior Report Status

All required prior reports exist:

- `audits/cluster3_phase12_gp_template_grammar_n5_report.md`
- `audits/cluster3_phase12b_f1_targeted_p_loop_modal_report.md`
- `audits/cluster3_phase12c_f1_fixture_alignment_report.md`
- `audits/cluster3_phase12d_aligned_f1_p_loop_modal_report.md`
- `audits/cluster3_phase12e_initial_f2_c_loop_modal_report.md`
- `audits/cluster3_phase13_diagnostic_evidence_freeze_report.md`

## Artifact Row And Schema Validation

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
    assert path.exists(), path
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

Sidecar existence check:

```text
outputs/cluster3/p_smoke_l4_n1.jsonl sidecar_exists True
outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl sidecar_exists True
outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl sidecar_exists True
outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl sidecar_exists True
```

Repository helper validation using `load_content_hash_sidecar` and
`validate_content_hash_sidecar_for_rows` passed:

```text
outputs/cluster3/p_smoke_l4_n1.jsonl content_hash_sidecar_valid
outputs/cluster3/g_plus_p_template_dev_l4_n5.jsonl content_hash_sidecar_valid
outputs/cluster3/g_plus_p_aligned_f1_p_loop_smoke_n1.jsonl content_hash_sidecar_valid
outputs/cluster3/g_plus_c_plus_p_initial_f2_c_loop_smoke_n1.jsonl content_hash_sidecar_valid
```

## Boundary Scan Summary

Commands:

```bash
rg -i "private eval|eval_shape_set|hidden|edge cases|extra shapes|torch.testing" outputs/cluster3/*.jsonl
rg -i "speedup|profil|nsight|ncu|timing|latency|tokens/sec|runtime_ms|benchmark" outputs/cluster3/*.jsonl
```

Both scans returned no matches in valid top-level Cluster 3 JSONL artifacts.

## Unsupported Claim Audit

Command:

```bash
rg -i "paper-scale complete|n=20 complete|pass@k result|P lift|C lift|improves correctness|performance improvement|speedup|profiler result|timing result|full 2\^3 complete|statistically significant" docs audits cluster3/README.md
```

Manual review found no unsupported completed-evidence claims. Matches were
caveats, prohibitions, future/planning text, historical reports, test names, or
explicit statements that no paper-scale/pass@k/lift/performance claim is made.

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

Summary before `-x` stop: 1 failed, 130 passed, 7 skipped.

## Clean Tree Verification

Preflight `git status --short` was empty. Final `git status --short` is expected
to remain empty after this ignored audit report is written.

No Modal command was invoked. No GPU job, n=20, n=5, paper-scale run,
generation, experiment, profiler/timing/speedup measurement, raw output
artifact mutation, grammar mutation, hash re-recording, or RL work was run.

## Provenance Freeze Status

The repository commit is recorded, the working tree was clean at preflight, the
required prior reports exist, required artifacts and content-hash sidecars
validate, boundary scans pass, and unsupported-claim audit passes.

The only warning is the known Cluster 1 docs-lock regression that remains the
first full-regression `-x` failure.

## Classification

`PHASE13B_COMMIT_PROVENANCE_FREEZE_COMPLETE_WITH_WARNINGS`

## Next-Step Recommendation

Cluster 3 diagnostic evidence is provenance-frozen for local planning. Any
optional broader non-paper-scale Cluster 3 run still requires separate explicit
approval. Do not run n=20 or paper-scale work yet.
