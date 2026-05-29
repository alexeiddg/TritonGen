# Cross-Pipeline Reportability Alignment Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification: `AUDIT_COMPLETE`

## 1. Executive summary

Alignment classification: `PARTIAL_ALIGNMENT_GAP`.

The scale-tier issue is not a broad outcome, pairing, grammar, or provenance mismatch across the none, G, C, and G+C pipelines. Those semantics are aligned well enough for the current covered-row 2^2 analysis. The remaining gap is narrower but cross-cutting: raw rows and row schemas do not carry `scale_tier`, while analyzer reportability and research contracts require a paper-scale label for report-facing outputs.

Important current-workspace finding: the user-supplied blocker state is stale in this checkout. `outputs/analysis/factorial_2x2_preliminary.json` currently has `metadata.reportable=true`, `metadata.scale_tiers=["paper"]`, `metadata.scale_tier_source="analysis_cli_annotation"`, and `metadata.raw_scale_tiers_before_annotation=["unspecified"]`. The raw artifact omission is still real, but the current analyzer output has already been annotated as paper scale.

Scale-tier classification:

- `SCALE_TIER_SCHEMA_DRIFT`: current row dataclasses/loggers do not serialize `scale_tier`, while scale contracts say every run/artifact should record it.
- `SCALE_TIER_POLICY_DOC_DRIFT`: docs and contracts still describe the analyzer output as `metadata.reportable=false` and `scale_tiers=["unspecified"]`, which no longer matches the current analyzer JSON.
- Not `SCALE_TIER_METHODOLOGY_BLOCKER` for the current covered-row 2^2 analysis, because the registry and analyzer annotation are sufficient to identify the current artifacts as paper/preliminary scale without regenerating or rewriting raw JSONL.

Artifact sufficiency: `YES_NO_REGENERATION`. Existing artifacts are sufficient for the current 2^2 covered-row analysis. Do not rewrite or regenerate the raw artifacts for this issue.

Recommended near-term fix path: preserve the explicit analyzer scale-tier annotation path, preferably make it registry/manifest-driven for citation workflows, and update docs after the reportable analyzer output is accepted. Do not rewrite raw artifacts.

Recommended long-term policy: all future rows plus the artifact registry must carry scale tier. Analyzer config/manifest or CLI annotation can support legacy artifacts, but future Cluster 3/P should fail reportability if row, registry, and analyzer annotation disagree.

Previous patch prompt recommendation: replace or substantially modify `PATCH_ANALYZER_REPORTABILITY_POLICY`. The current analyzer already has `--scale-tier` annotation and the current output is reportable; the next prompt should focus on registry alignment, documentation consistency, and future row-schema enforcement rather than reimplementing the already-present annotation path.

## 2. Scope and method

Files inspected included the required analyzer, evaluation, current artifacts, Cluster 1, Cluster 2, docs/contracts, and prior audits:

- Analyzer and shared eval: `outputs/analysis/factorial_2x2_preliminary.json`, `shared/analysis/factorial.py`, `shared/eval/aggregation.py`, `shared/eval/failure_taxonomy.py`.
- Current artifacts: the four JSONL files under `outputs/cluster1/` and `outputs/cluster2/`.
- Cluster 1: `cluster1/results/dataclass.py`, `cluster1/results/logger.py`, `cluster1/experiments/run_cluster1_modal.py`, `cluster1/validation/compile_check.py`, and `cluster1/tests/` search results.
- Cluster 2: `cluster2/results/dataclass.py`, `cluster2/results/logger.py`, `cluster2/experiments/run_cluster2_modal.py`, `cluster2/replay/`, `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`, and `cluster2/tests/` search results.
- Docs/contracts: `README.md`, `docs/05_artifacts_and_results_registry.md`, `docs/07_analysis_and_statistics.md`, `docs/08_decision_log.md`, `docs/10_cluster3_drift_prevention_plan.md`, `.contracts/research/research_scope.md`, `.contracts/research/eval_metrics.md`, `.contracts/research/scale_policy.md`.
- Prior audits: `audits/analyzer_reportability_blocker_audit.md`, `audits/analyzer_pre_output_verification_audit.md`, normalization/fix audits, and final documentation consistency audit search hits.

Required searches were run before conclusions:

```text
rg "scale_tier|scale-tier|scale tiers|scale_tiers|paper|development|smoke|unspecified|reportable|_validate_scale_tiers|_is_reportable_output" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "condition|kernel_class|dtype|base_seed|generation_seed|sample_index|replay_pair_id|prompt_hash|prompt_sha" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "functional_success|compile_success|failure_code|F0_|F1_|F2_|F3_|F3_EVAL_PIPELINE|normaliz" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "grammar_active|grammar_variant|grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|generated_metadata" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "model_revision|tokenizer_revision|modal_image_sha|modal_image_provenance_sha256|grammar_sha|provenance" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "Cluster 3|cluster3|P condition|performance feedback|Level 4|timing|profiling|speedup|scale gate|paper-scale" docs .contracts audits cluster3 shared -u
```

Artifact field audit method:

- Used only `.venv/bin/python`.
- Parsed each current JSONL artifact without modifying it.
- Compared top-level and `generated_metadata` field presence for scale tier, condition, identity, outcome, grammar, and provenance fields.
- Ran a separate read-only pairing summary over tuple keys `(kernel_class, kernel_name, dtype, base_seed/generation_seed)`.

No-edit statement: no code, docs/contracts, analyzer output, or existing artifacts were modified. The only intended repository change from this task is this audit report.

## 3. Scale-tier alignment

### Current raw artifact state

All four current raw artifacts omit `scale_tier`:

| Condition | Path | Rows | Top-level `scale_tier` | Nested `generated_metadata.scale_tier` |
|---|---|---:|---:|---:|
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 0 | 0 |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 0 | 0 |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 0 | 0 |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 0 | 0 |

The omission is consistent across all four current artifacts. It is not isolated to one condition or one cluster.

### Code/schema state

Cluster 1:

- `cluster1/experiments/run_cluster1_modal.py` defines `SUPPORTED_SCALE_TIERS=("smoke","development","paper")` and validates paper-scale metadata when `scale_tier=="paper"`.
- `cluster1/results/dataclass.py::GenerationResult` does not include a `scale_tier` field.
- `cluster1/results/logger.py` does not write a row-level `scale_tier`.

Cluster 2:

- `cluster2/experiments/run_cluster2_modal.py::Cluster2RunnerConfig` requires `scale_tier` and uses it for paper-scale generated metadata gates.
- `cluster2/results/dataclass.py::Cluster2EvalRow` does not include a row-level `scale_tier`.
- `cluster2/results/logger.py` does not write a row-level `scale_tier`.

The runner-level scale gate exists, but the persisted result row schemas do not retain it. That is the core schema alignment gap.

### Analyzer policy state

`shared/analysis/factorial.py` currently supports three scale-tier sources:

- explicit raw row metadata from payload, `generated_metadata`, or `replay_metadata`;
- default `"unspecified"` when raw metadata is absent;
- analysis-level annotation via `--scale-tier`.

The analyzer records:

- `scale_tiers`,
- `raw_scale_tiers_before_annotation`,
- `scale_tier_source`,
- `requested_scale_tier`.

Reportability is still gated by:

```text
scope == "primary_functional"
not allow_mixed_scale
tuple(scale_tiers) == ("paper",)
```

In the current analyzer JSON, the gate passes because `--scale-tier paper` was used:

```text
metadata.reportable = true
metadata.scale_tiers = ["paper"]
metadata.raw_scale_tiers_before_annotation = ["unspecified"]
metadata.scale_tier_source = "analysis_cli_annotation"
```

### Docs/contracts state

Docs/contracts are partly stale or stricter than implementation:

- `docs/05_artifacts_and_results_registry.md` still says the analyzer output has `metadata.reportable=false`.
- `docs/07_analysis_and_statistics.md` still says `metadata.reportable=false` and `metadata.scale_tiers=["unspecified"]`.
- `.contracts/research/scale_policy.md` says every run config, JSONL sidecar, aggregate summary, and filename should record `scale_tier`, and it still describes the analyzer output as non-reportable.
- `.contracts/research/eval_metrics.md` says every `EvalResult` and `RunConfig` must carry `scale_tier`.
- `docs/10_cluster3_drift_prevention_plan.md` covers scale gates and reportability in general, but should explicitly require scale-tier inheritance into P row schemas, registry entries, and analyzer manifests before any P paper-scale run.

### Classification

Primary scale-tier classification:

```text
SCALE_TIER_SCHEMA_DRIFT
SCALE_TIER_POLICY_DOC_DRIFT
```

The missing raw field is a cross-artifact metadata omission, but not a broad methodological blocker. Scale tier is inferable from the current artifact registry and can be safely attached at analyzer runtime. Going forward, scale tier should live in all future rows plus registry; legacy/current artifacts should be handled by an analyzer config/manifest or explicit CLI annotation, with the annotation source recorded in analyzer metadata.

## 4. Outcome-semantics alignment

Outcome semantics are aligned enough for reportability once scale-tier metadata/docs are handled.

| Condition | Raw `compile_success` | Raw `functional_success` | `failure_code` semantics | Analyzer normalization |
|---|---:|---:|---|---|
| none | present, 180 false | absent | absent/null | condition inferred from role; Cluster 1 functional success normalizes to false/unproven |
| G | present, 3 true and 174 false | absent | null 3; `F1_RUNTIME` 152; `F1_COMPILE` 9; `F0_PARSE` 13 | condition inferred from role; Cluster 1 functional success normalizes to false/unproven |
| C | absent | present, 180 false | `F0_PARSE` 180 | analyzer derives `compile_success=false` from F0 |
| G+C | present, 4 true and 173 false | present, 177 false | `F2_NUMERIC_NAN` 4; `F1_RUNTIME` 146; `F1_COMPILE` 10; `F0_PARSE` 12; `F3_EVAL_PIPELINE` 5 | analyzer validates/uses raw compile; F3 policy applies |

Cluster 1 functional normalization is intentional: none/G are compile-only rows and did not run Level 2 correctness. `functional_success=False` for Cluster 1 means unproven for the current primary functional analysis, not measured numeric failure.

Cluster 2 compile normalization is intentional: C lacks raw `compile_success`, but all C rows have `F0_PARSE`, which unambiguously implies compile failure. G+C carries explicit `compile_success`; F2 rows imply compile success, and F0/F1 rows imply compile failure.

`F3_EVAL_PIPELINE` policy is aligned: F3 rows are infrastructure/evaluation-pipeline failures. They are excluded from compile-success rate denominators and treated as compile false in matched-pair analysis unless independent compile-pass evidence exists.

Conclusion: `OUTCOME_SEMANTICS_ALIGNED_WITH_CAVEATS`.

## 5. Pairing/replay alignment

Pairing is aligned enough for current covered-row reportability.

Read-only tuple-key summary:

| Condition | Rows | Unique tuple keys | Duplicates |
|---|---:|---:|---:|
| none | 180 | 180 | 0 |
| G | 177 | 177 | 0 |
| C | 180 | 180 | 0 |
| G+C | 177 | 177 | 0 |

Pair counts:

| Comparison | Pair count |
|---|---:|
| C vs none | 180 |
| G+C vs G | 177 |
| G vs none | 177 |
| G+C vs C | 177 |

Known missing G/G+C rows versus the 180-row baseline grid:

```text
matmul/gemm/fp32/base_seed=5
matmul/gemm/bf16/base_seed=0
matmul/gemm/bf16/base_seed=18
```

C and G+C generated rows carry nested `generated_metadata.replay_pair_id`, `replay_base_seed`, and `replay_generation_seed`; all matched the tuple identity in the audit. Raw Cluster 1 rows do not carry `replay_pair_id`, but the analyzer uses tuple identity for pairing and current paired comparisons are emitted.

The 177/180 handling is a warning for covered-row current 2^2 claims and a blocker only for any claim of complete 180/180 G/G+C coverage. Missing rows must remain named and must not be silently imputed or filled with template-G artifacts.

Conclusion: `PAIRING_REPLAY_ALIGNED_WITH_COVERAGE_WARNING`.

## 6. Grammar/provenance alignment

Grammar metadata is aligned for G-containing current rows.

| Condition | Rows | `grammar_active` | `grammar_variant` | `grammar_valid` | `gbnf_parse_valid` | `semantic_valid` | Invariant mismatches |
|---|---:|---:|---|---:|---:|---:|---:|
| G | 177 | 177 true | `task_agnostic` | 49 true / 128 false | 105 true / 72 false | 49 true / 128 false | 0 |
| G+C | 177 | 177 true | `task_agnostic` | 52 true / 125 false | 100 true / 77 false | 52 true / 125 false | 0 |

Rejection-layer counts:

- G: null 49; `semantic_validator` 56; `gbnf_parse` 72.
- G+C: null 52; `semantic_validator` 48; `gbnf_parse` 77.

C correctly has no active grammar; none correctly has `grammar_active=false` with legacy/flat schema.

Provenance caveats:

- none is a legacy Cluster 1 artifact without current model/tokenizer/modal/package revision provenance fields.
- G has model/tokenizer/package/grammar provenance but `modal_image_sha="unknown"` on 177 rows; it does carry `modal_image_provenance_sha256`.
- C and G+C have model/tokenizer revisions, stable `modal_image_sha`, Modal provenance SHA, prompt hashes, replay seeds, temperature, and token budget under `generated_metadata`.

These caveats are warnings for interpretation and documentation, not blockers for current covered-row analyzer reportability after explicit scale-tier annotation. They must remain visible in report-facing text.

Conclusion: `GRAMMAR_PROVENANCE_ALIGNED_WITH_WARNINGS`.

## 7. Documentation/contract alignment

Documentation is not aligned with the current analyzer output.

Current stale statements:

- `docs/05_artifacts_and_results_registry.md` says `metadata.reportable=false`.
- `docs/07_analysis_and_statistics.md` says `metadata.reportable=false` and `metadata.scale_tiers=["unspecified"]`.
- `.contracts/research/scale_policy.md` says the current analyzer output is valid but non-reportable.
- `README.md` search hits also describe reportability as blocked.

Those statements matched the prior blocker audit, but no longer match the current `outputs/analysis/factorial_2x2_preliminary.json`, which is reportable via `analysis_cli_annotation`.

Contract tension:

- `.contracts/research/scale_policy.md` and `.contracts/research/eval_metrics.md` require scale-tier recording in run/result surfaces.
- Current runners know scale tier, but current row dataclasses/loggers omit it.
- Current analyzer can compensate with CLI annotation, but docs/contracts do not yet define registry/manifest-vs-CLI precedence or conflict checks.

Required future docs/contracts updates after the fix is accepted:

- Update docs/05 and docs/07 to reflect the current analyzer metadata if this reportable output is the accepted output.
- Update scale policy language to distinguish legacy/current artifacts handled by analyzer annotation from future rows that must serialize `scale_tier`.
- Add explicit registry/manifest authority language: registry/manifest should be the durable citation source; CLI annotation should be recorded and should not silently override explicit conflicting raw row tiers.
- Update Cluster 3 guardrails to require scale-tier in P row schemas and registry entries before paper-scale runs.

Conclusion: `DOCUMENTATION_CONTRACT_ALIGNMENT_NEEDS_UPDATE`.

## 8. Cluster 3 implications

Cluster 3/P must inherit the current alignment rules before any P run becomes report-facing:

- Define P semantics, allowed feedback content, metrics, failure taxonomy, and reportability criteria before implementation.
- Require `scale_tier` in all future Cluster 3 row schemas, not only runner config.
- Register each P artifact before citation with path, condition, row count, intended row count, schema, scale tier, model/provenance, seed schedule, metric contract, and caveats.
- Use an analyzer config/manifest for P-containing analyses that lists exact artifacts and their scale tier.
- Make analyzer reportability refuse output if row-level scale tier, registry scale tier, and analyzer annotation disagree.
- Preserve tuple identity and replay/pairing rules before P-generated rows are produced.
- Keep speedup/timing/profiling results gated by Level 2 correctness and by the future P measurement contract.
- Treat smoke/development P artifacts as non-reportable unless explicitly promoted through registry and reportability gates.

Where scale-tier drift could recur:

- P runner config accepts scale tier but P row dataclass omits it.
- P output filename implies `paper` but registry or manifest does not record it.
- P analyzer command receives `--scale-tier paper` without checking registry/row conflicts.
- P docs cite exploratory analyzer output without checking `metadata.reportable`.

Cluster 3 should use `all future rows plus registry` as the policy, with analyzer manifest/CLI annotation only as an explicit legacy or invocation-level source.

## 9. Recommended fix path

Near term:

1. Do not rewrite raw JSONL artifacts.
2. Do not regenerate none, G, C, or G+C artifacts for scale tier.
3. Preserve the current analyzer annotation behavior: explicit `--scale-tier paper` sets missing raw tiers to paper and records `scale_tier_source="analysis_cli_annotation"`.
4. Prefer a registry/manifest-driven analyzer invocation for report-facing reruns so the scale tier is not only a human CLI convention.
5. Keep analyzer conflict behavior: explicit raw `scale_tier` must not be silently overridden by CLI/manifest annotation.
6. Update docs/05, docs/07, README, and scale policy after the accepted analyzer output is chosen so they no longer claim `reportable=false` if the current reportable output is the intended result.

Long term:

1. Add `scale_tier` to future row schemas for all clusters, including Cluster 3/P.
2. Make loggers persist `scale_tier` top-level for future rows; generated metadata may mirror it, but should not be the only durable location.
3. Keep registry as the citation authority for existing and future artifacts.
4. Make analyzer reportability require a single consistent scale tier across row, registry/manifest, and invocation metadata.
5. Add tests that future paper outputs fail reportability when any artifact lacks or conflicts on scale tier.
6. Document the precedence order explicitly: raw explicit row tier and registry/manifest must agree; CLI annotation can fill legacy missing rows only when the registry authorizes it.

Safest near-term fix choice:

```text
explicit analyzer CLI scale-tier annotation, with registry-driven scale-tier annotation as the safer citation workflow
```

Not recommended:

- raw artifact rewrite,
- artifact regeneration,
- analyzer reportability relaxation,
- documentation-only fix.

## 10. Whether to modify previous patch prompt

Recommendation: `replace` the previous `PATCH_ANALYZER_REPORTABILITY_POLICY` prompt, or at minimum modify it heavily.

Reason: the current analyzer already has `--scale-tier`, conflict checks, annotation-source metadata, tests, and a current reportable analyzer JSON. A prompt that asks only to add explicit analyzer annotation is now stale.

Replacement prompt should focus on:

- registry/manifest-driven scale-tier annotation for report-facing analyzer invocation;
- docs/contracts alignment to the current analyzer output;
- future-row schema policy for `scale_tier`;
- Cluster 3/P inheritance and conflict behavior;
- no raw artifact rewrite or regeneration.

## 11. Appendix

### Analyzer metadata inspected

Current `outputs/analysis/factorial_2x2_preliminary.json` metadata:

```text
reportable = true
scale_tiers = ["paper"]
normalized_scale_tiers = ["paper"]
raw_scale_tiers_before_annotation = ["unspecified"]
scale_tier_source = "analysis_cli_annotation"
requested_scale_tier = "paper"
rows_loaded = 714
cells_populated = ["none", "G", "C", "G+C"]
cells_missing = ["P", "G+P", "C+P", "G+C+P"]
g_replay_coverage = 177/180 with named matmul gaps
f3_excluded_counts = {"G+C": 5}
```

### Field audit summary

| Condition | Rows | Condition field | Scale tier | Identity | Outcomes | Grammar | Provenance |
|---|---:|---|---|---|---|---|---|
| none | 180 | absent; role-inferred | absent | `generation_seed` present; no `base_seed`/`replay_pair_id` | compile false; functional absent | inactive | legacy missing revisions/image |
| G | 177 | absent; role-inferred | absent | `generation_seed` present; no `base_seed`/`replay_pair_id` | compile 3 true; functional absent | task-agnostic top-level | revisions present; `modal_image_sha=unknown` |
| C | 180 | `C` | absent | `base_seed` plus nested replay metadata | functional false; compile absent; `F0_PARSE` | inactive/null | nested model/tokenizer/modal/prompt metadata |
| G+C | 177 | `G+C` | absent | `base_seed` plus nested replay metadata | functional false; compile 4 true; F3 caveat | task-agnostic top-level/nested | nested model/tokenizer/modal/prompt/grammar metadata |

### Pairing summary

```text
none rows 180 unique_keys 180 duplicates 0
G rows 177 unique_keys 177 duplicates 0
C rows 180 unique_keys 180 duplicates 0
G+C rows 177 unique_keys 177 duplicates 0

C vs none pairs: 180
G+C vs G pairs: 177
G vs none pairs: 177
G+C vs C pairs: 177

Missing G/G+C rows:
matmul/gemm/fp32/base_seed=5
matmul/gemm/bf16/base_seed=0
matmul/gemm/bf16/base_seed=18

C replay_pair_id mismatches: 0
G+C replay_pair_id mismatches: 0
C replay seed mismatches: 0
G+C replay seed mismatches: 0
```

### Commands run

```text
git status --short

rg "scale_tier|scale-tier|scale tiers|scale_tiers|paper|development|smoke|unspecified|reportable|_validate_scale_tiers|_is_reportable_output" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "condition|kernel_class|dtype|base_seed|generation_seed|sample_index|replay_pair_id|prompt_hash|prompt_sha" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "functional_success|compile_success|failure_code|F0_|F1_|F2_|F3_|F3_EVAL_PIPELINE|normaliz" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "grammar_active|grammar_variant|grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|generated_metadata" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "model_revision|tokenizer_revision|modal_image_sha|modal_image_provenance_sha256|grammar_sha|provenance" shared cluster1 cluster2 docs .contracts audits outputs -u
rg "Cluster 3|cluster3|P condition|performance feedback|Level 4|timing|profiling|speedup|scale gate|paper-scale" docs .contracts audits cluster3 shared -u

rg -n "scale_tier|scale_tiers|reportable|_is_reportable_output|_apply_scale_tier_annotation|_resolve_scale_tier|_raw_scale_tier|--scale-tier|raw_scale_tiers_before_annotation|SCALE_TIER" shared/analysis/factorial.py shared/tests/test_factorial_analysis.py
rg -n "scale_tier|scale-tier|scale tiers|paper|development|smoke|reportable" cluster1/results/dataclass.py cluster1/results/logger.py cluster1/experiments/run_cluster1_modal.py cluster2/results/dataclass.py cluster2/results/logger.py cluster2/experiments/run_cluster2_modal.py cluster2/contracts/frozen_cluster1_artifacts_manifest.json docs/05_artifacts_and_results_registry.md docs/07_analysis_and_statistics.md docs/10_cluster3_drift_prevention_plan.md .contracts/research/scale_policy.md .contracts/research/eval_metrics.md .contracts/research/research_scope.md README.md
rg -n "functional_success|compile_success|failure_code|F3_EVAL_PIPELINE|normalize|normaliz|canonical_failure|compile_success_from" shared/analysis/factorial.py shared/eval/aggregation.py shared/eval/failure_taxonomy.py cluster1/results/dataclass.py cluster1/results/logger.py cluster1/validation/compile_check.py cluster2/results/dataclass.py cluster2/results/logger.py cluster2/replay cluster2/experiments/run_cluster2_modal.py docs/07_analysis_and_statistics.md docs/08_decision_log.md
rg -n "replay_pair_id|replay_base_seed|replay_generation_seed|prompt_sha256|prompt_hash|base_seed|generation_seed|selected_controls|177|180|missing|task-agnostic|task_agnostic" shared/analysis/factorial.py shared/eval/aggregation.py cluster2/replay cluster2/experiments/run_cluster2_modal.py cluster2/contracts/frozen_cluster1_artifacts_manifest.json docs/05_artifacts_and_results_registry.md docs/07_analysis_and_statistics.md docs/08_decision_log.md audits/analyzer_reportability_blocker_audit.md audits/analyzer_pre_output_verification_audit.md audits/final_documentation_consistency_audit.md
rg -n "grammar_active|grammar_variant|grammar_valid|gbnf_parse_valid|semantic_valid|rejection_layer|generated_metadata|modal_image_sha|model_revision|tokenizer_revision|grammar_sha|provenance" cluster1/results/dataclass.py cluster1/results/logger.py cluster1/experiments/run_cluster1_modal.py cluster2/results/dataclass.py cluster2/results/logger.py cluster2/experiments/run_cluster2_modal.py cluster2/replay docs/05_artifacts_and_results_registry.md docs/07_analysis_and_statistics.md docs/10_cluster3_drift_prevention_plan.md .contracts/research/eval_metrics.md audits/analyzer_pre_output_verification_audit.md audits/final_documentation_consistency_audit.md
rg -n "Cluster 3|cluster3|P condition|performance feedback|Level 4|timing|profiling|speedup|paper-scale|scale gate|scale-tier|reportability|registry" docs/10_cluster3_drift_prevention_plan.md docs/08_decision_log.md .contracts/research/scale_policy.md .contracts/research/eval_metrics.md .contracts/research/research_scope.md cluster3/README.md shared/factors/registry.py

.venv/bin/python -m shared.analysis.factorial --help
.venv/bin/python artifact field audit script from task prompt
.venv/bin/python analyzer metadata inspection script
.venv/bin/python pairing/replay summary script

sed -n reads of analyzer, docs, contracts, and prior audit sections
```

### Required conclusion choices

```text
1. Broad alignment classification: PARTIAL_ALIGNMENT_GAP
2. Existing artifacts sufficient: YES_NO_REGENERATION
3. Scale tier should live going forward: all future rows plus registry; analyzer config/manifest or CLI annotation for current legacy rows
4. Safest near-term fix: explicit analyzer CLI scale-tier annotation now; artifact-registry-driven scale-tier annotation for report-facing workflow
5. Safest long-term policy: all future rows plus registry, with analyzer conflict rejection
6. Previous patch prompt: replace or heavily modify; current analyzer annotation path already exists
```
