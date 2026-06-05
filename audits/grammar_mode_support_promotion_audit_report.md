# Grammar-Mode Support Promotion Audit Report

## Scope

source_branch: `codex/grammar-mode-support-implementation`
target_branch: `codex-track-handoff-context`
promoted_commit: `c24fbaa Add local grammar-mode support for 12-cell L1a`
promotion_method: `git merge --ff-only codex/grammar-mode-support-implementation`
promotion_status: `FAST_FORWARD_COMPLETE`

This audit records the local promotion of grammar-mode representability support
for the 12-cell `grammar_mode x C x P` L1a planning design. It does not
authorize Modal, GPU work, generation, experiments, output mutation, analyzer
artifact refresh, report artifact refresh, MLflow runtime writes, dependency
changes, lockfile changes, or paper-scale claims.

## Implementation Summary

The promoted implementation adds local-only support for representing and
validating the 12-cell design without running it:

- shared grammar-mode factors for `grammar_off`, `template_upper_bound`, and
  `task_agnostic`;
- a planning-only 12-cell matrix under `cluster3/planning`;
- row/schema carrying of explicit `grammar_mode`;
- analyzer normalization and grouping by `grammar_mode`;
- tests for grammar-mode values, the planning matrix, row/schema handling, and
  factorial analyzer grouping.

The Cluster 3 execution launcher remains a separate authorization surface. This
promotion does not convert the planning matrix into an executable launch path.

## Grammar Mode Model

The local model distinguishes three explicit modes:

| grammar_mode | grammar_active | grammar_variant | grammar_path | claim_scope |
|---|---:|---|---|---|
| `grammar_off` | false | null | null | null |
| `template_upper_bound` | true | `template_upper_bound` | `cluster1/grammar/triton_kernel.gbnf` | `diagnostic_non_primary` |
| `task_agnostic` | true | `task_agnostic` | `cluster1/grammar/triton_kernel_agnostic.gbnf` | `primary` |

`primary_grammar` and `task_agnostic_grammar` are not accepted executable
selectors in the promoted support.

## Twelve-Cell Planner

`cluster3/planning/grammar_mode_matrix.py` returns 12 local planning cells:

- four `grammar_off` cells crossed with C off/on and P off/on;
- four `template_upper_bound` cells crossed with C off/on and P off/on;
- four `task_agnostic` cells crossed with C off/on and P off/on.

Each cell has a unique condition name and output namespace suffix. The planner
imports no Modal, Torch, Triton, generation, correctness-runtime, or artifact
mutation entrypoints.

## Row And Schema Labeling

`shared/eval/schema.py` and `cluster3/results/dataclass.py` can carry optional
top-level and metadata-level `grammar_mode` values. Generated-row validation
derives and validates the mode against legacy `grammar_active`,
`grammar_variant`, `grammar_path`, and `grammar_claim_scope` fields.

The existing Cluster 3 runner metadata path labels current legacy conditions as
`grammar_off` for non-G conditions and by active grammar variant for G-enabled
conditions. This preserves existing execution behavior while allowing future
rows to be explicitly grouped by grammar mode after a separately authorized
launch path exists.

## Analyzer Grouping

`shared/analysis/factorial.py` now normalizes explicit `grammar_mode` evidence
and groups grammar summaries by the actual mode rather than collapsing all
active grammar rows into a binary G bucket. Legacy 2x2 analyzer behavior remains
preserved unless explicit grammar-mode evidence or a legacy active-G missing
mode requires a grammar-mode diagnostic.

## MLflow Tracking Deferral

MLflow is intentionally not a scientific source of truth for this promotion.
The promoted code does not create MLflow runs, start an MLflow server, write to
`mlruns/`, refresh MLflow index artifacts, or add tracking dependencies.

Future L1a work should keep MLflow post-hoc and non-authoritative: JSONL rows
and sidecar artifacts remain the primary evidence, and any MLflow importer or
indexer requires a separate explicit authorization packet.

## L1a Authorization Status

The promoted packet at
`docs/experiment_packets/full_pipeline_grammar_mode_cp_l1a_n1_authorization_packet.md`
remains:

- `status: DRAFT_NOT_APPROVED`;
- `AUTHORIZES_EXECUTION: NO`;
- `code_support_status: LOCAL_REPRESENTABILITY_READY`;
- a draft authorization artifact, not an execution packet.

Packet review result:

- The packet correctly names the selected 12-cell `grammar_mode x C x P`
  matrix and uses the supported labels `grammar_off`, `template_upper_bound`,
  and `task_agnostic`.
- The packet correctly keeps exact command, runtime config, target paths,
  stop/spend limits, model/revision data, observability IDs, and final approval
  unavailable until a future signed approval.
- Before any authorization, the packet must be pinned to the promoted support
  tip or later. It still records `baseline_commit: 0cc43c1 Audit full pipeline
  launch packet promotion`, while the local representability proof now depends
  on `c24fbaa Add local grammar-mode support for 12-cell L1a`.

## Tests Run

```text
.venv/bin/python -m pytest cluster3/tests -k "grammar_mode or grammar_variant or condition or matrix or schema or row" -q
469 passed, 347 deselected in 0.45s

.venv/bin/python -m pytest shared/tests -k "factorial or grammar_mode or metric_registry" -q
121 passed, 985 deselected in 7.33s

.venv/bin/python -m pytest shared/tests/test_eval_schema.py shared/tests/test_tracking_noop.py -q
31 passed in 0.08s

git diff --check
clean
```

## No-Execution Proof

No Modal, GPU, generation, experiment, benchmark, profiler, billing, or MLflow
runtime command was run during this promotion.

Execution authorization scan notes:

- broad scan hits include pre-existing historical approved-smoke audit lines
  and command examples;
- diff-only positive authorization hits are scan-command text added to packet
  and audit documentation, not affirmative authorization fields;
- no new positive execution authorization field was introduced by the promoted
  implementation.

## No Output Or MLflow Mutation Proof

Protected mutation scan against the promoted implementation was empty for:

```text
outputs
artifacts
mlruns
docs/preliminary_report
pyproject.toml
requirements.txt
requirements-dev.txt
uv.lock
poetry.lock
Pipfile.lock
```

After promotion, the working-tree diff for the same protected paths remained
empty. No dependencies or lockfiles were changed.

## Classification

`GRAMMAR_MODE_SUPPORT_PROMOTION_COMPLETE`

The implementation is promoted to `codex-track-handoff-context`, local tests
pass, protected mutation scans are clean, no new execution authorization leak
was introduced, and L1a remains unsigned and unexecuted.

## Next-Step Recommendation

Review or patch the L1a n=1 authorization packet on the next branch
`codex/full-pipeline-l1-smoke-dev-approval-packet` so the packet pins its target
commit to the promoted grammar-mode support tip or later. Do not create an L1
execution packet until that packet names an exact command/config, output paths,
observability IDs, stop/spend limits, grammar hashes, MLflow disposition, and
approval signature.
