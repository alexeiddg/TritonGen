# Scale-Tier Docs/Contracts Alignment Fix Report

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `ALIGNMENT_FIX_COMPLETE`

## 1. Executive summary

The current analyzer output at `outputs/analysis/factorial_2x2_preliminary.json` was verified as valid JSON with `metadata.reportable=true`. The output is reportable for the current covered 2^2 scope because it records explicit paper-scale annotation through `analysis_cli_annotation`.

Files updated:

- `README.md`
- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/09_preliminary_report_outline.md`
- `docs/10_cluster3_drift_prevention_plan.md`
- `docs/handoff/stale_docs_inventory.md`
- `docs/preliminary_report/README.md`
- `docs/preliminary_report/index.html`
- `docs/preliminary_report/index.es.html`
- `.contracts/research/scale_policy.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/research_scope.md`

The patch does not rewrite raw JSONL artifacts, does not modify analyzer output, does not modify source code, does not edit grammar files, and does not re-record hashes.

## 2. Verified analyzer metadata

Read directly with `.venv/bin/python`:

| Field | Verified value |
|---|---|
| `metadata.reportable` | `True` |
| `metadata.scale_tiers` | `["paper"]` |
| `metadata.raw_scale_tiers_before_annotation` | `["unspecified"]` |
| `metadata.scale_tier_source` | `analysis_cli_annotation` |
| `metadata.requested_scale_tier` | `paper` |
| `diagnostics.rows_loaded` | `714` |
| `metadata.rows_loaded` / top-level `rows_loaded` | absent |

The row count is recorded under `diagnostics.rows_loaded`, not in `metadata.rows_loaded`.

## 3. Documentation changes

| File | Stale claim | Updated claim | Evidence |
|---|---|---|---|
| `README.md` | Statistical prose blocked by `metadata.reportable=false` | Preliminary result prose may be drafted from the verified reportable analyzer output with caveats | Analyzer metadata verification |
| `docs/05_artifacts_and_results_registry.md` | Analyzer output present but non-reportable | Analyzer output has `metadata.reportable=true`, `scale_tiers=["paper"]`, raw tiers `["unspecified"]`, source `analysis_cli_annotation`, requested tier `paper` | Analyzer metadata verification |
| `docs/07_analysis_and_statistics.md` | Analyzer `reportable=false` and `scale_tiers=["unspecified"]` | Current 2^2 output is reportable via explicit paper-scale annotation; unspecified raw tiers are not a default paper policy | Analyzer metadata and `shared/analysis/factorial.py` |
| `.contracts/research/scale_policy.md` | Current analyzer output non-reportable; all rows assumed to carry scale tier | Current legacy/current artifacts lack raw row `scale_tier` and are accepted through analyzer annotation; future rows plus registry must carry `scale_tier` | Cross-pipeline audit and analyzer metadata |
| `.contracts/research/eval_metrics.md` | Metric reportability blocked solely by analyzer `metadata.reportable=false` | Current analyzer is reportable; future `EvalResult` and `RunConfig` rows must carry `scale_tier` | Analyzer metadata and current policy |
| `docs/10_cluster3_drift_prevention_plan.md` | P reportability guardrail lacked explicit scale-tier inheritance | Cluster 3/P must serialize row `scale_tier`, register scale tier, and reject analyzer conflicts | Future policy from alignment audit |
| Other report-facing docs | Current analyzer described as non-reportable | Current analyzer is reportable for the covered 2^2 scope, while P, 177/180, F3, model-fit, and provenance caveats remain | Stale-claim search and analyzer metadata |

## 4. Current policy

The current raw none/G/C/G+C artifacts do not serialize row-level `scale_tier`. That is a known legacy/current artifact limitation and was not fixed by rewriting JSONL.

The accepted current analyzer output uses explicit CLI scale-tier annotation. The analyzer records the annotation source and requested tier in metadata:

```text
metadata.scale_tier_source=analysis_cli_annotation
metadata.requested_scale_tier=paper
metadata.raw_scale_tiers_before_annotation=["unspecified"]
```

This policy applies only to the current registered 2^2 artifact set. It does not imply that every unspecified artifact is paper scale by default.

Current caveats remain visible:

- G and G+C are 177/180.
- Missing rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- G+C has five `F3_EVAL_PIPELINE` rows.
- P cells are absent/deferred.
- The functional model is not fit because the functional outcome has a single observed class.
- G has `modal_image_sha=unknown`; none has legacy provenance limitations.

## 5. Future policy

Future rows must include `scale_tier`, and registry entries must include `scale_tier`.

Future policy:

- All future paper-scale rows, including Cluster 3/P rows, must persist `scale_tier` in the row schema.
- The artifact registry or analyzer manifest must record scale tier for each artifact.
- Analyzer reportability must reject conflicts between raw row `scale_tier`, registry/manifest scale tier, and CLI annotation.
- CLI annotation may fill missing legacy/current row tiers only when a registry, manifest, or explicit analysis policy authorizes the exact artifact set.
- CLI annotation is not the normal path for future P paper-scale artifacts.

Cluster 3/P inherits this policy before any P paper-scale run, analyzer output, or report-facing registry entry.

## 6. Validation

Commands run:

```text
git status --short
rg "reportable=false|metadata.reportable=false|non-reportable|not reportable|reportable=true|metadata.reportable" README.md docs .contracts/research audits outputs -u
rg "scale_tier|scale-tier|scale tiers|scale_tiers|unspecified|analysis_cli_annotation|requested_scale_tier|raw_scale_tiers_before_annotation" README.md docs .contracts/research audits shared outputs -u
rg "Cluster 3|P condition|P row|future rows|registry|manifest|paper-scale|scale gate|scale-tier" README.md docs .contracts/research audits -u
rg "official final|preliminary results|factorial_2x2_preliminary|714 loaded|metadata.reportable" README.md docs .contracts/research audits outputs -u
.venv/bin/python analyzer metadata verification script
rg "reportable=false|metadata.reportable=false|scale_tiers=\[\"unspecified\"\]|blocked by analyzer reportability|official final.*blocked" README.md docs .contracts/research
rg "analysis_cli_annotation|raw_scale_tiers_before_annotation|requested_scale_tier|scale_tier_source|scale_tiers.*paper|future rows.*scale_tier|registry.*scale_tier" README.md docs .contracts/research
git diff -- outputs cluster1 cluster2 shared
```

Stale-claim search result:

```text
No matches for the exact stale-claim search across README.md, docs, and .contracts/research.
```

Required-current-terms search result:

```text
Matches found for analysis_cli_annotation, raw_scale_tiers_before_annotation,
requested_scale_tier, scale_tier_source, scale_tiers=["paper"], future rows
must include scale_tier, and registry entries must include scale_tier.
```

Forbidden-diff check:

```text
git diff -- outputs cluster1 cluster2 shared
# no output
```

## 7. Remaining caveats

- G and G+C are 177/180.
- Missing rows are `matmul/fp32/base_seed=5`, `matmul/bf16/base_seed=0`, and `matmul/bf16/base_seed=18`.
- G+C has five `F3_EVAL_PIPELINE` rows.
- P-containing cells remain absent/deferred.
- G has `modal_image_sha=unknown`; none has legacy schema/provenance limitations.
- Current raw JSONL artifacts still do not serialize row-level `scale_tier`; they were not rewritten.
- The preliminary report assets were not regenerated from analyzer output; visible reportability prose was aligned, and no analyzer rerun was performed.

## 8. Next recommendation

`PROCEED_TO_RESULTS_SECTION_DRAFT`

Proceed only from the verified `metadata.reportable=true` analyzer output and keep the caveats above attached to any preliminary result prose.
