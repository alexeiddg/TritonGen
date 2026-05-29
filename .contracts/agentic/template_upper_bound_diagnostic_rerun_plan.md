# Template Upper-Bound Diagnostic Rerun Plan

## 1. Executive summary

This plan defines a current-pipeline, non-primary template upper-bound diagnostic path. It preserves task-agnostic `G` as the primary grammar treatment and treats template `G` only as a task-encoded diagnostic ceiling.

The diagnostic question is:

> How much compile/functional performance is recoverable when the model is given a task-encoded/template-constrained grammar surface, compared with the task-agnostic grammar that serves as the primary research treatment?

The recommended design is Option 2: rerun current-pipeline template `G` and matching current-pipeline template `G+C`, then analyze them in a separate diagnostic output. Template `G` alone is useful for compile and grammar-funnel ceiling evidence, but it is not enough to evaluate the interaction between a template grammar and correctness feedback.

The primary paper path remains unchanged:

```text
none, task-agnostic G, C, task-agnostic G+C
```

The diagnostic path is separate:

```text
template G, template G+C
```

The old legacy artifact `outputs/cluster1/final_g_l4_n20.jsonl` remains useful only as historical compile-only evidence. It must not be used as current-pipeline evidence, must not fill missing task-agnostic rows, and must not be paired with current task-agnostic `G+C`.

## 2. Research framing

Primary `G` means task-agnostic grammar-guided decoding plus semantic post-validation. Its current grammar variant is `task_agnostic` and its primary grammar file is `cluster1/grammar/triton_kernel_agnostic.gbnf`.

Template `G` means a task-encoded/template-constrained grammar surface using `grammar_variant="template_upper_bound"` and `cluster1/grammar/triton_kernel.gbnf`. It is a diagnostic/reference upper bound because the grammar encodes the selected task-family surface more strongly than task-agnostic `G`.

The diagnostic should answer a ceiling question, not a replacement-treatment question. It estimates what is recoverable when grammar guidance is allowed to be task-encoded. It does not estimate the effect of a task-agnostic grammar.

Valid diagnostic interpretation:

- Template `G` is a `template_upper_bound`, `task-encoded`, `diagnostic ceiling`, and `non-primary` condition.
- Template `G+C` asks whether correctness feedback helps even when the grammar already forces a canonical template-shaped surface.
- Comparisons against task-agnostic `G` should be framed as diagnostic contrast, not as a primary factor substitution.

Invalid interpretation:

- Template `G` is not current primary `G`.
- Template `G` is not task-agnostic grammar evidence.
- Template `G` is not a way to repair the 177/180 task-agnostic coverage gap.

## 3. Primary vs diagnostic condition separation

The primary 2x2 remains:

| Role | Condition | Grammar variant | Artifact role |
| --- | --- | --- | --- |
| Primary control | `none` | none | Current baseline/replay control |
| Primary grammar | `G` | `task_agnostic` | Current primary grammar condition |
| Primary feedback | `C` | none | Current correctness-feedback condition |
| Primary combined | `G+C` | `task_agnostic` | Current primary combined condition |

The diagnostic template path is separate:

| Role | Diagnostic label | Raw condition | Grammar variant | Artifact role |
| --- | --- | --- | --- | --- |
| Template grammar ceiling | `G_template` | `G` | `template_upper_bound` | Non-primary diagnostic |
| Template grammar plus feedback | `G_template+C` | `G+C` | `template_upper_bound` | Non-primary diagnostic |

Raw rows may still use canonical `condition="G"` and `condition="G+C"` if existing schemas require canonical conditions. The diagnostic analyzer/report must map `(condition, grammar_variant)` to diagnostic labels such as `G_template` and `G_template+C` in its output.

Separation rules:

- Do not replace task-agnostic `G` with template `G`.
- Do not fill missing task-agnostic `G` rows from template rows.
- Do not mix template `G` with task-agnostic `G+C` in paired analysis.
- Do not add template rows to `outputs/analysis/factorial_2x2_preliminary.json`.
- Do not present a combined table that lets readers mistake template `G` for primary `G`.

## 4. Diagnostic questions

Primary diagnostic question:

> How much compile/functional performance is recoverable when the model is given a task-encoded/template-constrained grammar surface, compared with the task-agnostic grammar that serves as the primary research treatment?

Subquestions:

1. What compile-success ceiling does the template grammar produce under the current generation, validation, metadata, and compile pipeline?
2. How does the template grammar funnel differ from task-agnostic `G` in `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, and `stop_reason`?
3. Does template `G+C` change Level 2 `functional_success` relative to the current `C` path and relative to the no-C template diagnostic baseline semantics?
4. Are any apparent template gains explained by task encoding, mode collapse, or canonical template instantiation rather than general grammar guidance?
5. Does the diagnostic result reveal a grammar-surface gap in task-agnostic `G` that should be addressed separately, without using template rows as primary evidence?

What template `G` alone answers:

- Compile and grammar-funnel ceiling under current metadata.
- Whether the legacy 180/180 compile result is reproducible under current pipeline constraints.
- How much of the task-agnostic compile deficit may be due to grammar generality versus harness/eval behavior.

What template `G` alone does not answer:

- Whether correctness feedback interacts favorably with template grammar.
- Whether template grammar produces Level 2 functional correctness.
- Whether template grammar should replace task-agnostic `G`.

## 5. Recommended design

Recommendation: use Option 2.

### Option 1 - Template G only

Purpose:

- Produce a current-metadata template `G` artifact.
- Estimate a compile/grammar upper-bound against task-agnostic `G`.
- Validate `grammar_variant="template_upper_bound"` under the current Cluster 1 metadata gate.

Produced artifact:

- `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`

Useful metrics:

- `compile_success`
- `failure_code`
- `grammar_valid`
- `gbnf_parse_valid`
- `semantic_valid`
- `rejection_layer`
- `stop_reason`
- row coverage by kernel/dtype/seed

Limit:

- This is not enough for a fair template plus correctness-feedback diagnostic.

### Option 2 - Template G plus template G+C

Purpose:

- Produce matched template `G` and template `G+C` diagnostic artifacts under current metadata.
- Allow a separate diagnostic 2x2-like comparison:

```text
none, template G, C, template G+C
```

- Keep that comparison explicitly non-primary.

Produced artifacts:

- `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl`
- `outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_n20_l4.jsonl`
- `outputs/analysis/template_upper_bound_diagnostic_analysis.json`

Why this is the recommended design:

- It is the only design that can evaluate whether correctness feedback adds anything on top of a task-encoded grammar.
- It avoids pairing old legacy template `G` with current task-agnostic `G+C`.
- It allows current metadata/provenance gates to be applied uniformly.
- It can be reported as a diagnostic appendix without changing the primary paper path.

## 6. Artifact plan

Reserved/planned diagnostic artifacts:

| Artifact | Purpose | Scale | Primary? |
| --- | --- | --- | --- |
| `outputs/cluster1/template_upper_bound_g_current_pipeline_smoke_n1_l4.jsonl` | n=1 Cluster 1 template `G` smoke | smoke | no |
| `outputs/cluster1/template_upper_bound_g_current_pipeline_dev_n5_l4.jsonl` | n=5 Cluster 1 template `G` development gate | development | no |
| `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` | current-pipeline template `G` paper-scale diagnostic | paper | no |
| `outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_smoke_n1_l4.jsonl` | n=1 Cluster 2 template `G+C` smoke | smoke | no |
| `outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_dev_n5_l4.jsonl` | n=5 Cluster 2 template `G+C` development gate | development | no |
| `outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_n20_l4.jsonl` | current-pipeline template `G+C` paper-scale diagnostic | paper | no |
| `outputs/analysis/template_upper_bound_diagnostic_analysis.json` | separate diagnostic analysis output | paper diagnostic | no |
| `outputs/analysis/template_upper_bound_diagnostic_analysis.md` | optional rendered diagnostic report | paper diagnostic | no |
| `audits/template_upper_bound_current_pipeline_diagnostic_audit.md` | final audit after run | audit | no |

Expected sidecars:

- Cluster 1 metadata sidecar: `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl.meta.json`
- Cluster 2 content-hash sidecar, using the existing Cluster 2 sidecar naming convention.
- Diagnostic analysis metadata inside `outputs/analysis/template_upper_bound_diagnostic_analysis.json`.

Manifest and registry requirements:

- Register new artifact IDs instead of reusing `g_template_upper_bound_n20_l4`.
- Suggested Cluster 2 frozen replay artifact ID: `g_template_upper_bound_current_pipeline_n20_l4`.
- Register row counts, intended rows, grammar variant, grammar path/SHA, scale tier, coverage policy, and caveats in `docs/05_artifacts_and_results_registry.md`.
- If Cluster 2 `G+C` template generation uses frozen `G` replay, update the frozen Cluster 1 manifest to select the new current-pipeline template `G` artifact for the diagnostic route.
- If existing C2 hash gates hardcode `g_template_upper_bound_n20_l4`, add a diagnostic-safe mapping to the new artifact ID before running template `G+C`.

Do not overwrite:

- `outputs/cluster1/final_g_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl.meta.json`
- current primary artifacts
- current primary analyzer output

## 7. Metadata/schema requirements

Every new row must include or expose the following fields. For Cluster 2 rows, fields may be top-level or inside `generated_metadata` where the existing schema requires nesting, but the diagnostic analyzer must normalize them consistently.

Required condition and scale fields:

- `condition`
- `scale_tier`
- `grammar_active`
- `grammar_variant="template_upper_bound"`
- `grammar_path`
- `grammar_sha`

Required grammar-funnel fields:

- `gbnf_parse_valid`
- `semantic_valid`
- `grammar_valid`
- `rejection_layer`
- `stop_reason`

Required model/runtime provenance:

- `model_id`
- `model_revision`
- `tokenizer_revision`
- `transformers_version`
- `tokenizers_version`
- `xgrammar_version`
- `modal_image_sha` or `modal_image_provenance_sha256`
- `modal_image_provenance_components` when `modal_image_sha` is `unknown`
- `max_new_tokens`

Required identity fields:

- `kernel_class`
- `kernel_name`
- `dtype`
- `base_seed`
- `generation_seed`
- `sample_index`
- `attempt_index` where applicable
- `replay_pair_id` for Cluster 2 rows where applicable
- `replay_base_seed` and `replay_generation_seed` for Cluster 2 generated rows
- `prompt_sha256`
- `temperature`

Required outcome fields:

- `failure_code`
- `compile_success`
- `functional_success` for Cluster 2/template `G+C` rows
- `repair_set_success` and `eval_set_success` for Cluster 2/template `G+C` rows
- `repair_trace` or `trace_summary` for Cluster 2 generated rows

Required schema/provenance fields:

- `generation_metadata_schema_version`
- `grammar_claim_scope="diagnostic_non_primary"`
- `modal_image_provenance_sha256` when available
- `c2_generation_hashes` for Cluster 2 generated rows
- frozen Cluster 1 replay artifact/hash metadata for template `G+C`

Implementation note:

- Current Cluster 1 rows historically did not serialize row-level `condition`, `scale_tier`, `base_seed`, or `sample_index`. The current-pipeline diagnostic should not repeat that limitation. If the existing Cluster 1 writer still omits these fields, update the schema/logger before the diagnostic run and validate that the generated JSONL rows carry them directly.
- Current Cluster 2 rows have nested generated metadata and top-level condition/outcome fields. The diagnostic analyzer must normalize that shape without flattening raw artifacts by hand.

## 8. Cluster 1 template G run plan

Purpose:

- Produce a current-pipeline Cluster 1 template `G` diagnostic artifact with explicit `grammar_variant="template_upper_bound"` and current metadata.

Preconditions:

- `cluster1/grammar/triton_kernel.gbnf` remains the template upper-bound grammar.
- `grammar_sha` is computed from the exact grammar file used during the run.
- The run uses the same model identity as current primary runs unless a deliberate exception is recorded:
  - `model_id=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`
  - `model_revision=8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
  - `tokenizer_revision=8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`
- Use the same locked kernel classes and dtypes:
  - `elementwise`, `reduction`, `matmul`
  - `fp32`, `fp16`, `bf16`
- Use the same seed grid:
  - `sample_index/base_seed/generation_seed=0..19` within each kernel/dtype cell.
- Use the same current token budget unless a documented exception is made:
  - `max_new_tokens=2048`
- Use `scale_tier` progression:
  - smoke n=1
  - development n=5
  - paper n=20
- No generation prompt, grammar, kernel, dtype, or eval-gate change after paper-scale starts. If any such change is needed, invalidate the run and create a new artifact lineage.

Future command shape, not to run in this plan:

```text
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class all \
  --n 20 \
  --grammar-variant template_upper_bound \
  --scale-tier paper \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --max-new-tokens 2048 \
  --modal-generation-gpu L4 \
  --output outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl \
  --overwrite
```

Required validation after each Cluster 1 run:

```text
.venv/bin/python -m cluster1.experiments.validate_cluster1_results \
  --input outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl \
  --condition G \
  --kernel-class all \
  --n 20 \
  --grammar-variant template_upper_bound \
  --require-generation-metadata
```

Additional Cluster 1 checks:

- Confirm row count is 180 for n=20.
- Confirm each kernel/dtype cell has 20 rows.
- Confirm every row has `grammar_active=true`.
- Confirm every row has `grammar_variant="template_upper_bound"`.
- Confirm `grammar_path` ends with `cluster1/grammar/triton_kernel.gbnf`.
- Confirm `grammar_sha` matches the local grammar file.
- Confirm no row has `scale_tier` missing or conflicting with the sidecar.
- Confirm no row has missing model/tokenizer/runtime provenance.
- Confirm `compile_success`, `failure_code`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, and `stop_reason` are populated consistently.

## 9. Cluster 2 template G+C run plan

Purpose:

- Produce a current-pipeline Cluster 2 template `G+C` diagnostic artifact matched to the new current-pipeline template `G` artifact.

Preconditions:

- The current-pipeline template `G` artifact has passed the Cluster 1 metadata gate.
- The new template `G` artifact is registered in `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` with a new artifact ID.
- The diagnostic route selects the new template `G` artifact, not the old `g_template_upper_bound_n20_l4` legacy artifact.
- C2 hash gates are updated or extended so `grammar_variant="template_upper_bound"` verifies the new diagnostic frozen `G` artifact.
- The paired seed schedule uses the exact template `G` seed grid:
  - same `kernel_class`
  - same `kernel_name`
  - same `dtype`
  - same `base_seed`
  - same `generation_seed`
  - stable `replay_pair_id`
- The route remains explicit:
  - primary `G+C` default stays `grammar_variant="task_agnostic"`
  - template `G+C` requires an explicit diagnostic configuration

Future command shape, not to run in this plan:

```text
modal run -m cluster2.experiments.run_cluster2_modal \
  --condition G+C \
  --kernel-class all \
  --scale-tier paper \
  --n 20 \
  --grammar-variant template_upper_bound \
  --frozen-cluster1-manifest cluster2/contracts/frozen_cluster1_artifacts_manifest.json \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --model-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --tokenizer-revision 8e8ed243bbe6f9a5aff549a0924562fc719b2b8a \
  --max-new-tokens 2048 \
  --repair-budget 5 \
  --modal-generation-gpu L4 \
  --modal-eval-gpu L4 \
  --output outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_n20_l4.jsonl \
  --overwrite
```

Required validation after each Cluster 2 run:

```text
.venv/bin/python -c "from cluster2.results.logger import validate_cluster2_results_jsonl; rows = validate_cluster2_results_jsonl('outputs/cluster2/template_upper_bound_g_plus_c_current_pipeline_n20_l4.jsonl', expected_rows=180); print(len(rows))"
```

Additional Cluster 2 checks:

- Confirm every row has `condition="G+C"`.
- Confirm every row has `grammar_active=true`.
- Confirm generated metadata has `grammar_variant="template_upper_bound"`.
- Confirm `grammar_claim_scope="diagnostic_non_primary"`.
- Confirm `grammar_path` resolves to `cluster1/grammar/triton_kernel.gbnf`.
- Confirm `grammar_sha` matches the local template grammar.
- Confirm `generated_metadata.replay_control_condition="G"`.
- Confirm `replay_pair_id`, `replay_base_seed`, `replay_generation_seed`, `generation_seed`, prompt hash, model id, temperature, and token budget are pair-consistent.
- Confirm `functional_success`, `compile_success`, `repair_set_success`, `eval_set_success`, `failure_code`, and `repair_trace` are populated and schema-valid.
- Confirm F0/F1/F2/F3 semantics follow the current eval ladder and F2-only repair policy.

Optional stricter diagnostic:

- If the team wants Level 2 evaluation for template `G` without correctness feedback, create a separate Cluster 2 replay-evaluation artifact for template `G`. This is not required to mirror the current primary 2x2 analyzer semantics, but it can make the no-C template functional baseline more explicit.

## 10. Analyzer/reporting plan

The primary analyzer output must remain unchanged:

- Keep `outputs/analysis/factorial_2x2_preliminary.json` scoped to current primary `none`, task-agnostic `G`, `C`, and task-agnostic `G+C`.
- Do not append template rows to the primary analyzer inputs.
- Do not reinterpret the primary `G` cell as template `G`.

Use a separate diagnostic output:

- `outputs/analysis/template_upper_bound_diagnostic_analysis.json`
- Optional markdown: `outputs/analysis/template_upper_bound_diagnostic_analysis.md`

Diagnostic condition labels:

- `none`
- `G_template`
- `C`
- `G_template+C`

Raw-to-diagnostic mapping:

| Raw row fields | Diagnostic output label |
| --- | --- |
| `condition="G"`, `grammar_variant="template_upper_bound"` | `G_template` |
| `condition="G+C"`, `grammar_variant="template_upper_bound"` | `G_template+C` |
| `condition="G"`, `grammar_variant="task_agnostic"` | primary `G`, excluded from template diagnostic unless used as a contrast table |
| `condition="G+C"`, `grammar_variant="task_agnostic"` | primary `G+C`, excluded from template diagnostic unless used as a contrast table |

Existing analyzer risk:

- `shared/analysis/factorial.py` accepts only canonical condition labels and uses grammar variants for display labels.
- It can label template rows as "template G reference", but it also contains primary-analysis assumptions and hardcoded coverage language such as task-agnostic `G` replay coverage.
- Therefore, do not rely on the existing primary analyzer directly for the final diagnostic output unless it is wrapped or extended so the output is explicitly diagnostic and cannot be mistaken for the primary 2x2.

Recommended analyzer implementation:

- Add a separate diagnostic analyzer/report script or wrapper that loads the current primary `none` and `C` artifacts plus the new template `G` and template `G+C` artifacts.
- Normalize rows using shared parsing where safe, but emit diagnostic labels and diagnostic metadata.
- Set metadata fields such as:
  - `analysis_kind="template_upper_bound_diagnostic"`
  - `diagnostic_only=true`
  - `primary_2x2=false`
  - `primary_g_grammar_variant="task_agnostic"`
  - `diagnostic_g_grammar_variant="template_upper_bound"`
  - `template_claim_scope="diagnostic_non_primary"`
  - `old_legacy_template_artifact_excluded=true`
  - `template_rows_do_not_fill_task_agnostic_g=true`
- Emit `reportable=false` for primary-paper semantics, or use a separate field such as `diagnostic_reportable=true` only after registry, docs, gates, and audit pass.
- Preserve current F3 policy and compile-success normalization.
- Require exact pair matching for template `G` and template `G+C`.
- Reject mixed template/task-agnostic pairs unless the output section is explicitly a contrast table and not a paired result.

Diagnostic comparisons:

| Comparison | Response | Role |
| --- | --- | --- |
| `G_template` vs `none` | `compile_success` | template compile ceiling diagnostic |
| `G_template+C` vs `G_template` | `functional_success` | correctness-feedback on template grammar diagnostic |
| `G_template+C` vs `C` | `compile_success` and `functional_success` | secondary diagnostic contrast, matched where possible |
| `G_template` vs task-agnostic `G` | `compile_success`, `grammar_valid`, failure funnel | cross-grammar diagnostic contrast, not primary replacement |
| `G_template+C` vs task-agnostic `G+C` | `functional_success`, `compile_success`, grammar funnel | cross-grammar diagnostic contrast, not paired unless seed/control provenance is explicitly matched within each grammar lineage |

Diagnostic report sections:

- Artifact and provenance summary.
- Row coverage and missing-row policy.
- Compile-success ceiling.
- Grammar funnel.
- Failure taxonomy.
- Functional-success results for template `G+C`.
- Paired diagnostic comparisons.
- Contrast to task-agnostic `G` and task-agnostic `G+C`, with non-primary labels.
- Forbidden-claims section.

## 11. Validation gates

No n=20 run should start until smoke, development, metadata, analyzer, and audit gates pass.

Gate 0 - pre-run docs/contracts gate:

- Reserve planned artifact names in `docs/05_artifacts_and_results_registry.md`.
- Define template diagnostics in methodology and contracts.
- Record decision-log entry.
- Define analyzer separation before any paper-scale run.

Gate 1 - n=1 Cluster 1 Modal smoke:

- Run one kernel, all or selected dtypes, `condition=G`, `grammar_variant=template_upper_bound`, `scale_tier=smoke`.
- Validate row schema and metadata.
- Confirm template grammar path/SHA and runtime provenance are present.

Gate 2 - n=1 Cluster 2 template G+C Modal smoke:

- Run one kernel, `condition=G+C`, `grammar_variant=template_upper_bound`, `scale_tier=smoke`.
- Confirm it uses the diagnostic template replay route.
- Confirm no task-agnostic replay artifact is selected by accident.
- Confirm generated metadata and replay metadata are pair-consistent.

Gate 3 - n=5 Cluster 1 development run:

- Run all three kernel classes, all dtypes, n=5, template `G`.
- Pass Cluster 1 validation with `--require-generation-metadata`.
- Confirm no schema fields are missing.
- Confirm no unexpected row duplication.

Gate 4 - n=5 Cluster 2 development run:

- Run all three kernel classes, all dtypes, n=5, template `G+C`.
- Validate row count and generated metadata.
- Run diagnostic analyzer dry-run.
- Confirm all template pairs are matched.

Gate 5 - manifest/hash gate:

- Register the current-pipeline template `G` artifact in the frozen Cluster 1 manifest under a new artifact ID.
- Verify artifact hash, metadata sidecar hash, row records, seed schedule, replay pair IDs, and grammar variant.
- Update or extend C2 frozen-G hash gating for the diagnostic template route.
- Do not reuse the old legacy artifact ID for the new lineage.

Gate 6 - analyzer dry-run:

- Produce a dry-run diagnostic analysis using n=5 artifacts.
- Confirm output labels are `G_template` and `G_template+C`.
- Confirm the primary analyzer output is unchanged.
- Confirm the output is diagnostic-only and cannot be mistaken for primary `G`.

Gate 7 - pre-paper audit:

- Audit smoke/dev artifacts, row schemas, metadata, manifest selection, analyzer labels, and docs/contracts.
- Explicitly check that old `outputs/cluster1/final_g_l4_n20.jsonl` is excluded.

Gate 8 - n=20 Cluster 1 template G:

- Run n=20 only after Gates 0-7 pass.
- Validate with metadata gate.
- Register final row counts and caveats.

Gate 9 - n=20 Cluster 2 template G+C:

- Run n=20 only after final template `G` is registered and selected by the diagnostic replay route.
- Validate strict expected rows.
- Validate generated metadata and replay pairing.

Gate 10 - final analysis and audit:

- Run the separate diagnostic analyzer.
- Write final diagnostic audit.
- Update docs and contracts after final row counts are known.

## 12. Documentation/contracts update plan

Before the run:

| Path | Required update |
| --- | --- |
| `docs/05_artifacts_and_results_registry.md` | Reserve planned diagnostic artifacts, state non-primary role, expected row counts, scale tier, schema/provenance requirements, and legacy-template exclusion. |
| `docs/02_methodology_cluster1.md` | Define current-pipeline `template_upper_bound` diagnostic `G`; state it is task-encoded, diagnostic, compile-only in Cluster 1, and not primary `G`. |
| `docs/03_methodology_cluster2.md` | Define template `G+C` diagnostic if Option 2 is used; state primary `G+C` remains task-agnostic. |
| `docs/07_analysis_and_statistics.md` | Add a separate diagnostic-analysis section and state primary analyzer output remains unchanged. |
| `docs/08_decision_log.md` | Record the decision to rerun template `G`/`G+C` as non-primary diagnostic evidence. |
| `docs/09_preliminary_report_outline.md` | Place template diagnostics in a separate appendix/diagnostic section, not primary results. |
| `docs/10_cluster3_drift_prevention_plan.md` | No result update required unless analyzer/schema changes affect future factor-diagnostic guardrails; if updated, keep it as anti-drift guidance only. |
| `.contracts/research/research_scope.md` | State current-pipeline template diagnostics are non-primary and do not alter primary `G`. |
| `.contracts/research/eval_metrics.md` | Define allowed metrics for template diagnostics and preserve grammar-variant subcondition semantics. |
| `.contracts/research/scale_policy.md` | Register scale progression and require row-level `scale_tier` for this new future artifact lineage. |

After the run:

| Path | Required update |
| --- | --- |
| `docs/05_artifacts_and_results_registry.md` | Replace planned rows with observed row counts, artifact hashes, schema facts, caveats, and diagnostic status. |
| `docs/02_methodology_cluster1.md` | Add observed template `G` row count, grammar-funnel/compile caveats, and non-primary status. |
| `docs/03_methodology_cluster2.md` | Add observed template `G+C` row count, functional/failure caveats, and non-primary status. |
| `docs/07_analysis_and_statistics.md` | Summarize separate diagnostic analysis output, labels, reportability status, and caveats. |
| `docs/08_decision_log.md` | Update decision with final artifact IDs and whether Option 2 passed all gates. |
| `docs/09_preliminary_report_outline.md` | Add final placement and citation rules for the diagnostic appendix. |
| `.contracts/research/research_scope.md` | Confirm primary scope remains unchanged after diagnostic artifacts exist. |
| `.contracts/research/eval_metrics.md` | Add any final diagnostic metric caveats, especially if a separate diagnostic reportability field is used. |
| `.contracts/research/scale_policy.md` | Confirm scale tier, row-level scale metadata, and no mixed-scale analysis. |
| `audits/template_upper_bound_current_pipeline_diagnostic_audit.md` | Record final gate results, commands, row counts, metadata checks, analyzer checks, and forbidden-claim review. |

## 13. Risks and caveats

Reader confusion risk:

- Template `G` has a strong headline because the legacy artifact compiled 180/180. Every table and label must say diagnostic/reference/upper-bound.

Analyzer contamination risk:

- Existing analyzer semantics are built around canonical conditions. A template diagnostic must not be inserted into the primary analyzer as plain `G` or `G+C`.

Manifest/hash-gate risk:

- Current C2 code maps `template_upper_bound` to the old frozen artifact ID. A current-pipeline template `G+C` diagnostic must use a new registered artifact lineage and must not silently select the old legacy artifact.

Schema risk:

- Current Cluster 1 rows may not serialize all future-required fields at row level. The diagnostic run must not proceed at paper scale until row-level `condition`, `scale_tier`, `base_seed`, `sample_index`, and required provenance are present or an explicit current-schema alternative is documented and accepted.

Comparability risk:

- If model revision, tokenizer revision, token budget, kernel set, dtype set, seed grid, grammar file, prompt, or eval ladder changes, the diagnostic becomes a new lineage with a documented exception. It should not be presented as directly comparable to current primary runs without caveats.

Mode-collapse risk:

- Template grammar can force canonical template-shaped outputs. Analyzer/reporting should include a mode-collapse or low-diversity flag where applicable and describe this as task encoding, not general grammar guidance.

Legacy reconstruction risk:

- Reconstructing metadata for `outputs/cluster1/final_g_l4_n20.jsonl` would be post-hoc annotation, not original runtime provenance. It may be useful for audit summaries but should not become current-pipeline evidence.

## 14. Forbidden claims

Do not claim:

- Template `G` is primary `G`.
- Template `G` is current task-agnostic `G`.
- Template `G` fills the three missing task-agnostic `G` rows.
- Template `G` can be mixed with current task-agnostic `G+C` as a paired result.
- The legacy `outputs/cluster1/final_g_l4_n20.jsonl` artifact is current-pipeline evidence.
- The diagnostic result is a full 2^3 result.
- The diagnostic result establishes `P`, performance, timing, profiling, or speedup.
- Compile success proves functional correctness.
- `grammar_valid` proves compile success or functional success.
- Template `G+C` changes the primary `G+C` result.
- A diagnostic analyzer output is the current primary paper analyzer output.
- Development or smoke diagnostic rows are paper-scale evidence.
- Missing or unknown provenance is harmless.

## 15. Proposed phased implementation

Phase A - design lock:

- Update docs/contracts before any run.
- Add or confirm row-level schema requirements.
- Define diagnostic analyzer output format.
- Define new artifact IDs and manifest selection rules.

Phase B - Cluster 1 smoke/dev:

- Run n=1 template `G` smoke.
- Validate metadata.
- Run n=5 template `G` development.
- Validate metadata and row coverage.

Phase C - manifest preparation:

- Register the n=5/current template route as development evidence if needed.
- Prepare the new n=20 current-pipeline template `G` artifact ID.
- Update C2 diagnostic replay selection to use the new template artifact lineage.

Phase D - Cluster 2 smoke/dev:

- Run n=1 template `G+C` smoke.
- Run n=5 template `G+C` development.
- Validate pair consistency and diagnostic analyzer dry-run.

Phase E - pre-paper audit:

- Audit docs, registry, manifest, hash gates, schema, and analyzer separation.
- Confirm no primary output changes.

Phase F - Cluster 1 n=20:

- Run current-pipeline template `G` n=20.
- Validate metadata gate.
- Register observed row count and hashes.

Phase G - Cluster 2 n=20:

- Run matching current-pipeline template `G+C` n=20.
- Validate strict expected rows, metadata, and pair identity.

Phase H - diagnostic analysis and closeout:

- Produce `outputs/analysis/template_upper_bound_diagnostic_analysis.json`.
- Produce final audit.
- Update docs/contracts after run.
- Keep primary analyzer output unchanged.

## 16. Done definition

This diagnostic rerun is done only when:

- Task-agnostic `G` remains the primary grammar condition in docs, contracts, registry, and analyzer output.
- Template `G` and template `G+C` are explicitly labeled `template_upper_bound`, task-encoded, diagnostic ceiling, and non-primary.
- New artifact names and IDs are registered.
- New rows carry required metadata/provenance fields.
- Cluster 1 template `G` passes the metadata gate.
- Cluster 2 template `G+C` passes strict row-count, metadata, and pairing validation.
- The diagnostic analyzer output is separate from the primary 2x2 output.
- The diagnostic analyzer labels template conditions distinctly, for example `G_template` and `G_template+C`.
- Smoke, development, analyzer dry-run, pre-paper audit, n=20 validation, and final audit gates all pass.
- Docs/contracts are updated before and after the run.
- The old legacy template artifact remains unchanged and excluded from current-pipeline evidence.
- No forbidden claims are present in docs, reports, or analysis output.
