# Phase 0 Inventory Notes

## Repository shape

- Root contains README/package/dependency metadata.
- `docs/` is absent/unpopulated and should be created by Phase 1.
- `.contracts/research/` contains useful formal methodology contracts, but several need status addenda.
- `.contracts/agentic/` contains working plans and should not be citation-grade unless promoted.
- `audits/` contains useful evidence, with mixed currency.
- `cluster1/`, `cluster2/`, and `shared/` contain current implementation and tests.
- `cluster3/` exists but is deferred/not-started for current report scope.
- `outputs/` contains current artifacts plus many legacy summaries/smokes.

## Current artifact counts

| Role | Path | Rows/status |
| --- | --- | --- |
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 valid JSONL rows |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 valid JSONL rows |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 valid JSONL rows |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 valid JSONL rows |
| analysis | `outputs/analysis/factorial_2x2_preliminary.json` | present, valid JSON |

## Current caveats to preserve

- G and G+C are partial 177/180 artifacts.
- Missing rows are skipped, not imputed.
- Analyzer output is present but marked `reportable=false`.
- Primary functional success is 0 across all populated cells.
- Secondary compile success is diagnostic only.
- P cells are not populated.
- Template G is diagnostic/reference only.
- Baseline C1 artifact is legacy schema/provenance.

## Stale surfaces

- `README.md`, `cluster1/README.md`, `cluster2/README.md`.
- `.contracts/research/scale_policy.md`.
- `.contracts/agentic/cluster2_contract.md`.
- `cluster2/constants.py`.
- Old n5 and template output summaries.
- Older factorial/n5/pre-paper audits.

## Commands and validation

All required Phase 0 inventory/search commands were run. Artifact parsing was done with `.venv/bin/python`. No tests, Modal, GPU jobs, generation, experiment runs, artifact rewrites, grammar edits, hash re-recording, or commits were performed.
