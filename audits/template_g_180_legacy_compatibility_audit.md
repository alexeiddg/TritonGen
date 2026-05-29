# Template G 180/180 Legacy Compatibility Audit

Date: 2026-05-21
Repository: `/Users/alexeidelgado/Desktop/TritonGen`

Final classification:

- Old template artifact validity: `VALID_AS_LEGACY_DIAGNOSTIC_ONLY`
- Current primary G/G+C analysis compatibility: `NO_PRIMARY_ANALYSIS_INCOMPATIBLE`
- Pipeline classification: `COMPATIBLE_DIAGNOSTIC_ONLY`; incompatible with the current primary analyzer design as a primary G substitute
- Raw artifact rewrite needed: no
- Audit status: `AUDIT_COMPLETE_WITH_WARNINGS`

## 1. Executive summary

`outputs/cluster1/final_g_l4_n20.jsonl` exists, is valid JSONL, has 180 rows, covers the 3 kernel classes x 3 dtypes x 20 seeds grid, and passes the legacy Cluster 1 validator as `G` with inferred `template_upper_bound` grammar. All 180 rows have `compile_success=true`.

The artifact remains valid only for a narrow historical claim: legacy template-grammar, Cluster 1, compile-only, n=20 per kernel/dtype cell produced 180/180 compile successes under the legacy run. It is not valid as current primary G evidence.

The artifact fails the current paper-scale generation metadata gate on all 180 rows. The missing metadata is not a cosmetic schema difference: the rows do not carry current grammar split fields, grammar provenance, tokenizer/model revisions, Modal image/provenance fields, package versions, or generation stop reasons. Some identity and run settings are recoverable from the sidecar, but recovering them now would be post-hoc derived metadata, not original runtime provenance.

The current primary G condition is task-agnostic grammar-guided decoding with semantic post-validation. Current primary G and G+C artifacts are 177/180 task-agnostic rows, paired on covered replay tuples. The old 180/180 template artifact must not be used to fill those missing rows, must not be paired with current task-agnostic G+C, and must not enter the current primary 2x2 factorial analysis.

Recommended next action: preserve the old artifact as a documented legacy diagnostic/template upper-bound reference. For current primary evidence, complete or rerun task-agnostic G and matching G+C under the current metadata pipeline. For a fair template diagnostic comparison, run a separate current-pipeline template G and matching template G+C over the same seed grid, then analyze that as non-primary template-reference evidence.

## 2. Scope and method

Execution constraints honored:

- No Modal invocation.
- No GPU jobs.
- No generation or experiment runs.
- No analyzer rerun.
- No source code, grammar, docs/contracts, manifests, analyzer output, raw artifacts, or hashes were modified.
- Local parsing and validation used `.venv/bin/python`.
- The only intended repository change from this task is this audit report.

Hub/registry consultation:

- The required `.contracts/agentic/agentic_document_hub.md`, `.contracts/agentic/document_version_registry.md`, and `.contracts/agentic/code_update_documentation_policy.md` paths are absent in this checkout.
- Current hub files were found and read under `docs/handoff/`:
  - `docs/handoff/agentic_document_hub.md`
  - `docs/handoff/document_version_registry.md`
  - `docs/handoff/code_update_documentation_policy.md`
- The hub identifies current source hierarchy as code/tests, current artifacts, docs, `.contracts/research`, audits, then agentic handoff material.
- The hub issue pull sets relevant to this audit are Cluster 2/G+C, replay/pairing, Cluster 1 grammar/G, artifact identity/provenance, and analyzer outputs.

Files inspected:

- Artifact under audit:
  - `outputs/cluster1/final_g_l4_n20.jsonl`
  - `outputs/cluster1/final_g_l4_n20.jsonl.meta.json`
- Current primary artifacts:
  - `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`
  - `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`
  - `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
  - `outputs/cluster2/c_paper_n20_l4.jsonl`
- Current analyzer output:
  - `outputs/analysis/factorial_2x2_preliminary.json`
- Docs/contracts:
  - `README.md`
  - `docs/02_methodology_cluster1.md`
  - `docs/03_methodology_cluster2.md`
  - `docs/05_artifacts_and_results_registry.md`
  - `docs/06_failure_taxonomy_and_eval_ladder.md`
  - `docs/07_analysis_and_statistics.md`
  - `docs/08_decision_log.md`
  - `docs/09_preliminary_report_outline.md`
  - `docs/10_cluster3_drift_prevention_plan.md`
  - `.contracts/research/research_scope.md`
  - `.contracts/research/eval_metrics.md`
  - `.contracts/research/scale_policy.md`
- Code paths:
  - `cluster1/experiments/validate_cluster1_results.py`
  - `cluster1/results/dataclass.py`
  - `cluster1/results/logger.py`
  - `cluster1/grammar/triton_kernel_validator.py`
  - `shared/generation_metadata.py`
  - `shared/analysis/factorial.py`
  - `shared/eval/schema.py`
  - `shared/eval/pipeline.py`
  - `shared/eval/failure_taxonomy.py`
  - `cluster2/replay/cluster1_controls.py`
  - `cluster2/contracts/frozen_cluster1_artifacts_manifest.json`
  - `cluster2/experiments/run_cluster2_modal.py`
- Prior audits:
  - `audits/cross_pipeline_reportability_alignment_audit.md`
  - `audits/final_documentation_consistency_audit.md`
  - `audits/repository_documentation_methodology_readiness_audit.md`
  - `audits/analyzer_pre_output_verification_audit.md`
  - `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`

Hub/registry status:

| Topic | Hub/registry knows it? | Notes |
|---|---:|---|
| template G | yes | Current docs and registry classify template G as diagnostic/reference only, not primary. `cluster1/README.md` still foregrounds the historical template result. |
| `final_g_l4_n20.jsonl` | yes, indirectly | Present in Cluster 1 legacy summaries, frozen controls/manifests, and superseded/historical references. It is not a current primary artifact in `docs/05`. |
| task-agnostic G | yes | Current primary G artifact is `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`. |
| current analyzer output | yes, with drift | Docs/registry still contain older `reportable=false` language in places. The current JSON now has `metadata.reportable=true` via `analysis_cli_annotation`. |
| `scale_tier` policy | yes | `.contracts/research/scale_policy.md` requires scale-tier provenance; current raw rows omit it and analyzer annotation supplies it for the current output. |
| legacy artifact policy | yes | Legacy/template/n5/smoke/partial artifacts are non-authoritative unless explicitly promoted with caveats. |

## 3. Artifact identity

Artifact under audit:

| Field | Result |
|---|---|
| Path | `outputs/cluster1/final_g_l4_n20.jsonl` |
| Sidecar | `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` exists |
| JSONL validity | valid |
| Rows | 180 |
| Kernel/dtype cells | 9 cells, 20 rows each |
| Top-level `condition` | absent in raw rows |
| Top-level `grammar_variant` | absent in raw rows |
| Top-level `generated_metadata` | absent |
| `compile_success` | true on 180/180 rows |
| `functional_success` | absent |
| `failure_code` | absent |
| `scale_tier` | absent |

Raw row schema summary:

- Top-level keys include `compile_error_msg`, `compile_error_type`, `compile_results_by_dtype`, `compile_success`, `dtype`, `generation_seed`, `grammar_active`, `kernel_class`, `kernel_name`, `masked_token_rate`, `model_id`, `n_shapes_tested`, `run_id`, `source`, `temperature`, `timestamp_utc`, and `unique_solution_hash`.
- `generated_metadata` is absent on all rows.
- `grammar_active=true` on all rows.
- `model_id=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` on all rows.
- `generation_seed` values are dense 0-19 within each kernel/dtype cell.

Template identity:

- The raw rows do not explicitly say `template_upper_bound`.
- The sidecar also does not explicitly record `grammar_variant`, `grammar_path`, or `grammar_sha`.
- The legacy validator reports observed grammar variant `template_upper_bound` because legacy Cluster 1 deserialization/validation defaults the old G rows to the template grammar variant.
- Template status is therefore supported by legacy code/docs/manifests and validator behavior, not by explicit row-level grammar metadata.

Sidecar summary:

| Sidecar field | Status |
|---|---|
| `condition` | `G` |
| `expected_rows` | 180 |
| `written_rows` | present in sidecar |
| `finished_at_utc` | `2026-05-11T03:02:43.783576+00:00` |
| `git_commit` | `b4b0872f140fdf86fa2e0132b78e997988cfe04a` |
| model | `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ` |
| max new tokens | 512 |
| temperature | 0.2 |
| seed schedule | 9 records, 20 rows each, pair key fields `kernel_class`, `dtype`, `base_seed` |
| prompt hashes | present per kernel/dtype cell |
| `model_revision` | `unavailable_in_frozen_cluster1_artifact` in seed records |
| `tokenizer_revision` | `unavailable_in_frozen_cluster1_artifact` in seed records |
| `scale_tier` | absent |
| grammar variant/path/SHA | absent |
| Modal image/provenance/package versions | absent |

Available metadata:

- Artifact path, row count, condition label `G`, model id, token budget, temperature, seed schedule, prompt hashes, compile backend, generation backend, and git commit.

Missing current paper-scale metadata:

- `generation_metadata_schema_version`
- `grammar_path`
- `grammar_sha`
- `gbnf_parse_valid`
- `semantic_valid`
- `grammar_valid`
- `stop_reason`
- `model_revision`
- `tokenizer_revision`
- `modal_image_sha` or `modal_image_provenance_sha256`
- `modal_image_provenance_components`
- `transformers_version`
- `tokenizers_version`
- `xgrammar_version`
- `scale_tier`

## 4. Validation results

Legacy validation command:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results \
  --input outputs/cluster1/final_g_l4_n20.jsonl \
  --condition G \
  --kernel-class all \
  --n 20
```

Result: pass.

Summary:

- `row_count: 180 expected=180`
- `condition_coverage: expected=['G'] observed=['G']`
- `kernel_coverage: expected=['elementwise', 'reduction', 'matmul'] observed=['elementwise', 'matmul', 'reduction']`
- `grammar_variant_coverage: expected=['template_upper_bound'] observed=['template_upper_bound']`
- `dtype_coverage: expected=['fp32', 'fp16', 'bf16'] observed=['bf16', 'fp16', 'fp32']`
- `file_failures: 0`
- `row_count_failures: 0`
- `deserialization_failures: 0`
- `invariant_failures: 0`
- `masked_token_rate_failures: 0`
- `generation_metadata_failures: 0`
- `compile_results_by_dtype_failures: 0`
- `missing_cells: 0`
- `unexpected_cells: 0`
- `duplicate_identities: 0`
- `seed_failures: 0`
- `sample_size_failures: 0`

Current metadata gate command:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results \
  --input outputs/cluster1/final_g_l4_n20.jsonl \
  --condition G \
  --kernel-class all \
  --n 20 \
  --require-generation-metadata
```

Result: fail.

Failure summary:

- `generation_metadata_failures: 180`
- No row count, JSON, compile-results-by-dtype, missing-cell, unexpected-cell, duplicate-identity, seed, or sample-size failures were reported.
- The failure is due to the current paper-scale generation metadata gate.

Exact missing fields reported for each row:

- `gbnf_parse_valid`
- `generation_metadata_schema_version`
- `grammar_path`
- `grammar_sha`
- `grammar_valid`
- `modal_image_provenance_components`
- `modal_image_sha_or_modal_image_provenance_sha256`
- `model_revision`
- `semantic_valid`
- `stop_reason`
- `tokenizer_revision`
- `tokenizers_version`
- `transformers_version`
- `xgrammar_version`

Recoverability:

| Field group | Recoverable from sidecar/logs? | Provenance status |
|---|---:|---|
| row count, condition, model id, token budget, temperature, prompt hashes, seed schedule | mostly yes | sidecar records these |
| model/tokenizer revisions | no | sidecar explicitly records `unavailable_in_frozen_cluster1_artifact` |
| grammar path/SHA | derivable only from repository assumptions | post-hoc, not row runtime provenance |
| parse/semantic/grammar validity split | recomputable only by rerunning validators on saved text | post-hoc derived, not original generation metadata |
| stop reason | no reliable row source found | not recoverable as original runtime field |
| Modal image/provenance/package versions | no reliable row source found | not recoverable as original runtime field |
| scale tier | inferable from context/registry only | annotation, not raw artifact metadata |

Conclusion: missing fields are partly reconstructable for audit annotation, but not recoverable as original runtime provenance. Backfilling the raw artifact would not make it genuinely current-pipeline evidence.

Analyzer help inspection:

```text
.venv/bin/python -m shared.analysis.factorial --help
```

Result: help printed successfully. No dry-run mode was found. The analyzer was not rerun.

Current analyzer output inspection:

- `outputs/analysis/factorial_2x2_preliminary.json` exists and is valid JSON.
- Current metadata has `reportable=true`, `scale_tiers=["paper"]`, `raw_scale_tiers_before_annotation=["unspecified"]`, `scale_tier_source="analysis_cli_annotation"`, and `g_replay_coverage="177/180 task-agnostic G replay rows..."`.
- This conflicts with older docs/audits that still describe the analyzer output as `reportable=false`. That doc drift does not make the old template artifact current-primary compatible.

## 5. Compatibility with current pipeline

Current primary G definition:

- The current primary G condition is task-agnostic grammar-guided decoding plus semantic post-validation.
- Current primary G artifact: `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl`.
- Current G+C artifact: `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl`.
- Both current G-containing artifacts use `grammar_variant=task_agnostic`.
- Both current G-containing artifacts have 177/180 covered rows with the same three missing matmul rows:
  - `matmul/gemm/fp32/base_seed=5`
  - `matmul/gemm/bf16/base_seed=0`
  - `matmul/gemm/bf16/base_seed=18`

Compatibility matrix:

| Dimension | Old template G 180/180 | Current task-agnostic G/G+C | Compatibility |
|---|---|---|---|
| Grammar variant | inferred `template_upper_bound`; not explicit in rows | explicit `task_agnostic` | incompatible for primary G |
| Grammar validation fields | absent | `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer` present | incompatible |
| Grammar provenance | absent path/SHA | current grammar path/SHA present | incompatible |
| Row provenance | legacy flat rows, no current metadata | current generation metadata/provenance fields present for G/G+C | incompatible |
| Scale tier | absent; only inferable | current analyzer annotates paper scale; raw rows still omit tier | not primary compatible for old template |
| Compile semantics | 180/180 compile success, compile-only | G 3/177 compile success; G+C 4/177 compile success | not same metric surface |
| Functional semantics | absent/unproven | primary analyzer uses Level 2 `functional_success`; Cluster 1 normalized false/unproven | old template cannot support Level 2 |
| Failure taxonomy | no `failure_code` | F0/F1/F2/F3 taxonomy present/normalized | incompatible |
| Pairing identity | no row-level `base_seed`, `sample_index`, or `replay_pair_id`; sidecar has seed schedule | current paired analyzer uses covered replay tuple grid and generated metadata | incompatible as primary analyzer input |
| Row coverage | complete 180/180 template grid | 177/180 task-agnostic grid | cannot fill or mix |

Current artifact field summaries:

| Artifact | Rows | Grammar variant | Grammar valid | Compile success | Functional success | Notes |
|---|---:|---|---|---|---|---|
| `baseline_repaired_l4_n20.jsonl` | 180 | none/inactive | absent | false 180 | absent | legacy Cluster 1 control |
| `task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | `task_agnostic` | true 49 / false 128 | true 3 / false 174 | absent | current primary G, compile-only |
| `c_paper_n20_l4.jsonl` | 180 | none/inactive | absent | absent raw, derived false from F0 | false 180 | current C |
| `g_plus_c_paper_n20_l4.jsonl` | 177 | `task_agnostic` | true 52 / false 125 | true 4 / false 173 | false 177 | current G+C, paired to task-agnostic G |

Pipeline classification:

- `COMPATIBLE_PRIMARY_G`: no.
- `COMPATIBLE_DIAGNOSTIC_ONLY`: yes.
- `INCOMPATIBLE_WITH_CURRENT_PIPELINE`: yes for primary 2x2 analysis and current G/G+C pairing.
- `UNKNOWN`: no, enough evidence exists to classify it.

## 6. Valid and invalid claims

| Claim | Supported? | Reason |
|---|---:|---|
| template grammar legacy compile-only 180/180 | yes | Legacy validator passes; 180 valid rows; all rows compile; sidecar confirms n=20 grid. Template identity is inferred by legacy validation/docs rather than explicit row metadata. |
| current task-agnostic G performance | no | The artifact is legacy template G, not task-agnostic G, and lacks current grammar/provenance metadata. |
| current G+C comparability | no | Current G+C is paired to task-agnostic G over 177 covered rows; no matching current template G+C exists for this old artifact. |
| Level 2 functional correctness | no | Cluster 1 artifact is compile-only and has no `functional_success` or correctness evaluation. |
| current primary 2x2 factorial evidence | no | Current analyzer scope is none/G/C/G+C with task-agnostic G and matching task-agnostic G+C; old template rows cannot be substituted. |
| diagnostic template upper-bound reference | yes, with caveats | It can be cited as a historical template upper-bound compile-only reference if docs state metadata-gate failure and non-primary status. |

Valid claim:

```text
Under the legacy Cluster 1 template grammar setup, final_g_l4_n20.jsonl produced 180/180 compile-success rows over the legacy n=20 per kernel/dtype grid. This is a diagnostic/template upper-bound compile-only result.
```

Invalid claims:

- This is current primary G evidence.
- This is task-agnostic grammar performance.
- This can fill the three missing task-agnostic G rows.
- This can be paired with current task-agnostic G+C.
- This supports Level 2 functional correctness.
- This belongs in the current primary 2x2 factorial analysis.
- This proves current paper-scale G metadata compliance.

## 7. Options

### Option A - Primary task-agnostic rerun path

Purpose: produce current primary paper evidence.

Required runs/artifacts:

- Complete or rerun task-agnostic G to the intended 180/180 grid with current metadata.
- Rerun matching G+C from the same task-agnostic G grid and seed schedule.
- Analyze none/G/C/G+C through the current paired analyzer.
- Preserve missing-row policy if the run still has gaps; do not impute from template artifacts.

Analyzer compatibility:

- Compatible with current primary design if rows carry current metadata and G/G+C share the same task-agnostic matched grid.

Docs/contracts updates:

- Update `docs/05`, `docs/07`, `docs/08`, README, and research contracts with new row counts, provenance, reportability, and analyzer output.

Cost/risk:

- Highest cost because it requires generation/evaluation reruns.
- Lowest interpretability risk for primary evidence.

Recommendation:

- This is the default path if the goal is current primary G/G+C evidence.

### Option B - Diagnostic template rerun path

Purpose: produce a fair template diagnostic comparison at the same metrics/schema level as current artifacts, without relabeling template as primary G.

Required runs/artifacts:

- Rerun template G under the current pipeline with explicit `grammar_variant=template_upper_bound` and current generation metadata.
- Generate matching template G+C over the same 180 rows/seeds.
- Use the same token budget, model revision, tokenizer revision, Modal provenance, package versions, grammar path/SHA, stop-reason, and grammar-validity schema expected by the current metadata gate.
- Analyze separately as a template-reference diagnostic.

Analyzer compatibility:

- Requires a separate diagnostic analysis route or explicit labels so template G/template G+C are not mixed with current task-agnostic G/G+C.
- Should not be inserted into the current primary 2x2 analyzer as plain `G`/`G+C`.

Docs/contracts updates:

- Add a separate template-reference diagnostic section and artifact registry entries.
- State that it is non-primary and does not replace task-agnostic G.

Cost/risk:

- Medium to high cost because it requires both template G and matching template G+C.
- Main risk is reader confusion if template diagnostic labels are not prominent.

Recommendation:

- Use only if the report needs a fair template upper-bound diagnostic at current metrics/provenance level.

### Option C - Legacy-only preservation path

Purpose: preserve the old result without rerunning.

Required actions:

- Register or document `outputs/cluster1/final_g_l4_n20.jsonl` as a legacy diagnostic/template upper-bound artifact.
- Record row count: 180.
- Record scope: Cluster 1 compile-only.
- Record current metadata-gate failure.
- Record non-primary status.
- Do not use it for current task-agnostic G.
- Do not use it for G+C paired comparison.
- Do not rewrite the raw artifact.

Analyzer compatibility:

- No current primary analyzer integration.
- A derived audit summary can exist, but it must be clearly post-hoc and non-provenance-bearing.

Docs/contracts updates:

- Update registry and decision log to point to this audit and state the valid/invalid claim boundaries.

Cost/risk:

- Lowest cost.
- Low technical risk if labels are clear; medium communication risk if the old 180/180 headline is repeated without the diagnostic-only caveat.

Recommendation:

- This is the recommended immediate path for the existing artifact.

Default recommendation:

- Preserve old template G via Option C now.
- Use Option A for current primary evidence.
- Use Option B only if a fair template diagnostic comparison is actually needed.

## 8. Documentation update requirements

Do not perform these updates in this audit. If this audit is accepted, the following future doc/contract updates are needed:

| Path | Required future update |
|---|---|
| `docs/05_artifacts_and_results_registry.md` | Add or clarify `final_g_l4_n20.jsonl` as legacy diagnostic/template upper-bound, 180 rows, compile-only, current metadata-gate failure, non-primary. Also reconcile current analyzer reportability if the `reportable=true` JSON is accepted. |
| `docs/02_methodology_cluster1.md` | Clarify that the old template 180/180 artifact is not current G and cannot fill task-agnostic missing rows. |
| `docs/07_analysis_and_statistics.md` | State that old template G is excluded from the current primary 2x2 analysis; add separate diagnostic-template analysis requirements if Option B is used. Reconcile analyzer reportability drift. |
| `docs/08_decision_log.md` | Record this audit decision: old template G is valid only as legacy diagnostic compile-only evidence. |
| `README.md` | Keep template G language clearly diagnostic/reference only; update analyzer status if accepting the current `reportable=true` output. |
| `.contracts/research/research_scope.md` | Ensure primary G is task-agnostic and template G is only diagnostic/reference. |
| `.contracts/research/eval_metrics.md` | Ensure template diagnostics are label-separated from current primary G/G+C metrics and cannot support Level 2 unless rerun through Level 2. |
| `.contracts/research/scale_policy.md` | Clarify how legacy artifacts without raw `scale_tier` can be annotated versus what future rows must persist. |
| `docs/handoff/agentic_document_hub.md` | If artifact statuses are summarized there, add this audit as the template-G legacy compatibility source. |
| `docs/handoff/document_version_registry.md` | Register this audit and update stale analyzer/template artifact status if needed. |
| `docs/handoff/code_update_documentation_policy.md` | No direct change required unless future policy wants explicit legacy-template audit handling. |
| `cluster1/README.md` | De-emphasize old template result as primary-looking output; label it as frozen diagnostic upper-bound reference. |

Also note the path drift: the requested hub files under `.contracts/agentic/` are not present, while current hub files live under `docs/handoff/`. If future prompts rely on the old paths, they should be updated.

## 9. Final recommendation

Do now:

- Keep `outputs/cluster1/final_g_l4_n20.jsonl` unchanged.
- Cite it only as `VALID_AS_LEGACY_DIAGNOSTIC_ONLY`.
- Document that it passes legacy validation and fails the current metadata gate.
- Use this audit as the compatibility boundary for report writing.

Do not do:

- Do not rewrite raw rows to add inferred metadata.
- Do not re-record hashes for this artifact.
- Do not use the old template 180/180 rows as current task-agnostic G.
- Do not fill the current task-agnostic 177/180 gaps with template rows.
- Do not compare old template G directly against current G+C.
- Do not include the old template artifact in the current primary 2x2 factorial analysis.

Regeneration guidance:

| Goal | Regeneration needed? | Required path |
|---|---:|---|
| Legacy diagnostic compile-only claim | no | Preserve old artifact and document caveats. |
| Current primary task-agnostic G claim | yes | Complete/rerun task-agnostic G and matching G+C with current metadata. |
| Fair template diagnostic comparison | yes | Rerun template G and matching template G+C under current metadata and analyze separately. |

Cleanest path:

- Immediate clean path: preserve legacy diagnostic only.
- Clean primary evidence path: rerun or complete task-agnostic G/G+C.
- Clean fair-template path: rerun template G/template G+C separately as non-primary diagnostic.

## 10. Appendix

### Commands run

Initial status:

```text
git status --short
```

Hub/document inspection:

```text
nl -ba docs/handoff/agentic_document_hub.md
nl -ba docs/handoff/document_version_registry.md
nl -ba docs/handoff/code_update_documentation_policy.md
```

Required searches:

```text
rg "final_g_l4_n20|template_upper_bound|template G|template-G|template grammar|template.*diagnostic|upper-bound|upper bound" . -u
rg "task_agnostic|task-agnostic|triton_kernel_agnostic|grammar_variant|grammar_valid|gbnf_parse_valid|semantic_valid" README.md docs .contracts cluster1 cluster2 shared audits outputs -u
rg "require-generation-metadata|generation metadata|metadata gate|paper-scale metadata|grammar_sha|grammar_path|model_revision|tokenizer_revision|modal_image_sha|stop_reason" cluster1 shared docs .contracts audits outputs -u
rg "functional_success|compile_success|failure_code|compile-only|Level 2|correctness|F0_|F1_|F2_|F3_" README.md docs .contracts cluster1 cluster2 shared audits outputs -u
rg "replay_pair_id|paired|pairing|base_seed|generation_seed|sample_index|matched|seed schedule|177|180|missing rows" README.md docs .contracts cluster1 cluster2 shared audits outputs -u
rg "scale_tier|scale-tier|paper|unspecified|analysis_cli_annotation|reportable|reportable=false|reportable=true" README.md docs .contracts shared audits outputs -u
rg "legacy|diagnostic|reference|non-authoritative|authoritative|artifact registry|registry" README.md docs .contracts audits outputs -u
```

Artifact inspection:

```text
.venv/bin/python - <<'PY'
# Parsed old template G, current task-agnostic G, current G+C, none, and C JSONL artifacts.
# Summarized row counts, JSON validity, schema keys, field presence/counts, cell coverage, and tuple uniqueness.
PY
```

Sidecar and analyzer inspection:

```text
.venv/bin/python - <<'PY'
# Parsed outputs/cluster1/final_g_l4_n20.jsonl.meta.json.
# Summarized run config, seed schedule, prompt hashes, revision placeholders, scale tier, and grammar metadata.
PY

.venv/bin/python - <<'PY'
# Parsed outputs/analysis/factorial_2x2_preliminary.json.
# Summarized metadata.reportable, scale tier annotation, g_replay_coverage, and paired comparisons.
PY
```

Validation:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results \
  --input outputs/cluster1/final_g_l4_n20.jsonl \
  --condition G \
  --kernel-class all \
  --n 20

.venv/bin/python -m cluster1.experiments.validate_cluster1_results \
  --input outputs/cluster1/final_g_l4_n20.jsonl \
  --condition G \
  --kernel-class all \
  --n 20 \
  --require-generation-metadata

.venv/bin/python -m shared.analysis.factorial --help
```

Prior audit inspection:

```text
rg -n "template|task-agnostic|task_agnostic|reportable|legacy|diagnostic|F3|metadata|scale_tier|final_g_l4_n20|177|180|primary" audits/cross_pipeline_reportability_alignment_audit.md audits/final_documentation_consistency_audit.md audits/repository_documentation_methodology_readiness_audit.md audits/analyzer_pre_output_verification_audit.md audits/factorial_f3_eval_pipeline_compile_success_decision_report.md
```

### Summarized field counts

Old template G, `outputs/cluster1/final_g_l4_n20.jsonl`:

| Field | Summary |
|---|---|
| rows | 180 |
| bad JSON | 0 |
| `kernel_class` | elementwise 60, reduction 60, matmul 60 |
| `dtype` | fp32 60, fp16 60, bf16 60 |
| cells | all 9 kernel/dtype cells have 20 rows |
| `condition` | absent 180 |
| `grammar_active` | true 180 |
| `grammar_variant` | absent 180 |
| `grammar_path` / `grammar_sha` | absent 180 |
| `gbnf_parse_valid` / `semantic_valid` / `grammar_valid` | absent 180 |
| `compile_success` | true 180 |
| `functional_success` | absent 180 |
| `failure_code` | absent 180 |
| `model_id` | Qwen/Qwen2.5-Coder-7B-Instruct-AWQ 180 |
| `model_revision` / `tokenizer_revision` | absent 180 |
| `modal_image_sha` / Modal provenance | absent 180 |
| `transformers_version` / `tokenizers_version` / `xgrammar_version` | absent 180 |
| `scale_tier` | absent 180 |
| `replay_pair_id` | absent 180 |
| duplicate tuple keys | 0 using kernel/dtype/generation_seed identity |

Current task-agnostic G:

| Field | Summary |
|---|---|
| rows | 177 |
| grammar variant | `task_agnostic` 177 |
| grammar valid | true 49, false 128 |
| GBNF parse valid | true 105, false 72 |
| semantic valid | true 49, false 128 |
| stop reason | eos_token 105, max_new_tokens 72 |
| compile success | true 3, false 174 |
| failure code | null 3, F1_RUNTIME 152, F1_COMPILE 9, F0_PARSE 13 |
| missing rows | matmul/fp32/base_seed=5; matmul/bf16/base_seed=0; matmul/bf16/base_seed=18 |

Current G+C:

| Field | Summary |
|---|---|
| rows | 177 |
| grammar variant | `task_agnostic` 177 |
| grammar valid | true 52, false 125 |
| GBNF parse valid | true 100, false 77 |
| semantic valid | true 52, false 125 |
| stop reason | eos_token 100, max_new_tokens 77 |
| compile success | true 4, false 173 |
| functional success | false 177 |
| failure code | F2_NUMERIC_NAN 4, F1_RUNTIME 146, F1_COMPILE 10, F0_PARSE 12, F3_EVAL_PIPELINE 5 |
| missing rows | same three matmul rows as current task-agnostic G |

Current analyzer output:

| Field | Summary |
|---|---|
| populated cells | none, G, C, G+C |
| missing cells | P, G+P, C+P, G+C+P |
| reportable | true |
| scale tiers | `["paper"]` |
| raw scale tiers before annotation | `["unspecified"]` |
| scale tier source | `analysis_cli_annotation` |
| G replay coverage | 177/180 task-agnostic rows; skip missing rows |
| primary comparisons | C vs none, 180 pairs; task-agnostic G+C vs task-agnostic G, 177 pairs |
| secondary compile comparisons | task-agnostic G vs none, 177 pairs; task-agnostic G+C vs C, 177 pairs |
