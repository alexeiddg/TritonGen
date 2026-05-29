# Preliminary Technical Report Outline

## Opening Note

This is an outline for a preliminary technical report. It is not a research paper and it is not final report prose.

The report should explain the how, why, and what of Cluster 1 and Cluster 2 for a reader who may not know Triton, GPU kernels, or LLM evaluation. It should teach the experimental story, identify the implementation boundaries, point every claim to citation-grade sources, and preserve caveats.

Quote preliminary statistical results only from the verified `outputs/analysis/factorial_2x2_preliminary.json` while it has `metadata.reportable=true`, and preserve the coverage, F3, P-deferred, model-fit, and provenance caveats. The current analyzer output is not a full final 2^3/P result.

Primary sources for this outline:

- `README.md`
- `docs/00_project_map.md`
- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`
- `docs/cluster2_c_limitation_memo.md`
- `.contracts/research/research_scope.md`
- `.contracts/research/eval_metrics.md`
- `.contracts/research/scale_policy.md`
- Ouyang et al. 2025, "KernelBench: Can LLMs Write Efficient GPU
  Kernels?"

## 1. Executive Summary

Purpose placeholder:

- State that the report is a preliminary Cluster 1 + Cluster 2 technical handoff.
- Explain that the project studies control mechanisms for LLM-generated Triton kernels.
- Name the current factors: grammar guidance (`G`) and correctness feedback (`C`).
- State that the current populated scope is the 2^2 subset: `none`, `G`, `C`, and `G+C`.

High-level result-status placeholder:

- Describe what is ready: methodology docs, artifact registry, failure taxonomy, analyzer semantics, decision log, README/contract alignment, and the current four registered artifacts.
- Describe what is not ready: full 2^3/P claims, performance claims, and uncaveated final-paper conclusions.
- Preserve that Cluster 3/P is deferred and full 2^3 results are not current.

Required warning:

> Preliminary statistical claims must cite the verified `outputs/analysis/factorial_2x2_preliminary.json` with `metadata.reportable=true` and must carry the 177/180 coverage, five G+C `F3_EVAL_PIPELINE`, P-deferred, single-class model, and provenance caveats. Do not present the current 2^2 output as a full final 2^3/P result.

Major caveats to preview:

- G and G+C are 177/180, not complete 180/180 artifacts.
- Cluster 1 is compile-only and does not claim functional correctness.
- G has `modal_image_sha=unknown`; none has legacy provenance gaps.
- G+C has five `F3_EVAL_PIPELINE` rows.
- C lacks raw top-level `compile_success`; analyzer normalization is required.
- No performance, timing, profiling, or speedup result is currently claimed.

Primary sources:

- `README.md`
- `docs/00_project_map.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/07_analysis_and_statistics.md`
- `docs/08_decision_log.md`

## 2. Plain-Language Background

This section should teach the reader enough context to understand the experiment.

Planned explanations:

- A GPU kernel is low-level code that runs parallel computation on a GPU.
- Triton is a Python-like language for writing GPU kernels while exposing GPU concepts such as blocks, program IDs, memory loads/stores, and launch grids.
- LLM-generated Triton code can fail at several stages: malformed source, wrong callable surface, compile/runtime launch failure, numerical correctness failure, or evaluation-pipeline failure.
- Control mechanisms are studied because unconstrained LLM output can be syntactically invalid, structurally incompatible with the harness, or numerically wrong.
- Compile success and functional correctness are different: a kernel may compile and still compute incorrect values.

Use plain examples:

- "Code parses" is not the same as "code compiles."
- "Code compiles" is not the same as "code computes the right answer."
- "Code computes the right answer" is still separate from any future speed or profiler claim.

Primary sources:

- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`

## 3. Research Question And Current Scope

Current question:

> Do grammar guidance (`G`) and correctness feedback (`C`) improve LLM-generated Triton kernels under the current preliminary evaluation setup?

Current scope:

- The populated design is 2^2 over `G` and `C`.
- Current conditions are `none`, `G`, `C`, and `G+C`.
- Cluster 3 and the `P` factor are deferred.
- Full 2^3 factorial results are not current and must not be described as completed.

Planned report framing:

- Present this as a technical handoff, not a final research paper.
- Describe Cluster 1 as the implementation layer for `G`.
- Describe Cluster 2 as the implementation layer for `C` and `G+C`.
- Treat Modal as infrastructure/provenance machinery, not as a research factor.

Primary sources:

- `.contracts/research/research_scope.md`
- `docs/00_project_map.md`
- `docs/08_decision_log.md`

## 4. Experimental Conditions

| Condition | Uses G? | Uses C? | Meaning | Artifact |
|---|---:|---:|---|---|
| `none` | no | no | no grammar guidance and no correctness repair | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| `G` | yes | no | task-agnostic grammar-guided decoding plus semantic post-validation | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| `C` | no | yes | correctness-feedback repair only | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| `G+C` | yes | yes | task-agnostic G plus C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |

Text requirements:

- `G` is task-agnostic grammar guidance plus semantic post-validation.
- `C` is correctness-feedback repair only.
- `G+C` is the composition of `G` and `C`, not a new cluster.
- Template G and `template_upper_bound` are diagnostic/reference only.
- The current-pipeline template upper-bound G result at `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` may be discussed only in a diagnostic section or appendix, not in the primary results table.
- The old `outputs/cluster1/final_g_l4_n20.jsonl` 180/180 template result may be mentioned only as legacy compile-only diagnostic evidence.
- Primary results use task-agnostic G and task-agnostic G+C; the old template artifact is not primary G, not a current G+C pairing control, and not Level 2 correctness evidence.
- Old n=5, template, smoke, failed, and partial artifacts are not current report-scale evidence unless promoted into the registry.

Primary sources:

- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/08_decision_log.md`

## 5. Dataset And Kernel Scope

Scaffold content:

- Explain that the current preliminary artifacts use locked KernelBench Level 1 archetypes.
- Explain the original KernelBench scope:
  - Level 1 contains 100 single-primitive tasks;
  - Level 2 contains 100 operator-sequence tasks;
  - Level 3 contains 50 full-architecture tasks.
- List the three archetypes:
  - elementwise ReLU;
  - reduction softmax;
  - tiled GEMM/matmul.
- Include verified problem IDs:
  - ReLU = 19;
  - Softmax = 23;
  - GEMM/matmul = 1.
- Describe dtype coverage: fp32, fp16, and bf16.
- Describe the n=20 paper/preliminary-scale target over kernel class, dtype, and seed/sample identity.
- Preserve the G/G+C coverage caveat: G and G+C are 177/180 because three matmul rows are missing.
- Clarify original KernelBench task names:
  - problem 1 = Square matrix multiplication;
  - problem 19 = ReLU;
  - problem 23 = Softmax.
- Do not describe problem 19 as average pooling or problem 23 as a generic reduction. In the original KernelBench Level 1 list, average-pooling tasks are IDs 44-46 and reduction tasks are IDs 47-53.
- Explain that the current report uses a three-archetype subset of KernelBench Level 1, not the full 100-task Level 1 benchmark.

Coverage caveat to include:

| Kernel class | Dtype | Missing seed |
|---|---|---:|
| matmul | fp32 | 5 |
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |

Primary sources:

- `docs/05_artifacts_and_results_registry.md`
- `docs/02_methodology_cluster1.md`
- `.contracts/research/scale_policy.md`
- Ouyang et al. 2025, "KernelBench: Can LLMs Write Efficient GPU Kernels?"

## 6. Cluster 1 Methodology

Scaffold content:

- Explain that Cluster 1 is the implementation layer for `G`.
- Define `G` as task-agnostic grammar-guided decoding plus semantic post-validation.
- Explain the two-layer G enforcement:
  - token-level grammar-guided decoding using GBNF/XGrammar;
  - offline semantic post-validation.
- State the acceptance rule:

```text
grammar_valid = gbnf_parse_valid AND semantic_valid
```

- Explain that `grammar_active=true` means guidance was attempted, not accepted.
- Explain that `grammar_valid=true` is a grammar-funnel diagnostic, not compile success or functional success.
- Describe the task-agnostic grammar path: `cluster1/grammar/triton_kernel_agnostic.gbnf`.
- State that template G is diagnostic/reference only.
- If the current-pipeline template upper-bound G artifact is mentioned, label it as compile-only `G_template` diagnostic evidence with 180/180 compile success and current metadata-gate pass. State that it is not primary G, not a source for filling missing task-agnostic rows, and not a template G+C result.
- If the old template 180/180 result is mentioned, label it as `template_upper_bound` legacy compile-only diagnostic evidence that fails the current paper-scale generation metadata gate.
- Do not let the old template result compete with task-agnostic G as the primary `G` artifact.
- Describe the Cluster 1 compile-only boundary:
  - Cluster 1 stops at Level 1 compile/launch.
  - Cluster 1 does not run Level 2 numerical correctness.
  - Cluster 1 does not claim functional correctness.
  - Cluster 1 does not run repair loops.
  - Cluster 1 does not claim timing, profiling, speedup, or performance results.

Artifact status:

| Condition | Artifact | Rows | Intended rows | Caveat |
|---|---|---:|---:|---|
| `none` | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | compile-only; legacy schema/provenance |
| `G` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | compile-only; missing three matmul rows; `modal_image_sha=unknown` |

Diagnostic-only Cluster 1 appendix candidate:

| Diagnostic label | Artifact | Rows | Intended rows | Caveat |
|---|---|---:|---:|---|
| `G_template` | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` | 180 | 180 | compile-only template upper-bound diagnostic; not primary G; not in primary analyzer; matching template G+C not yet available |

Primary sources:

- `docs/02_methodology_cluster1.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`

## 7. Cluster 2 Methodology

Scaffold content:

- Explain that Cluster 2 is the implementation layer for `C` and `G+C`.
- Define `C` as correctness-feedback repair restricted to F2 numerical/correctness failures.
- Define `G+C` as task-agnostic `G` plus `C`.
- Explain replay controls:
  - `none` and `G` are frozen Cluster 1 controls;
  - `C` and `G+C` are generated/evaluated through Cluster 2;
  - pairing uses kernel/dtype/seed identity, with `replay_pair_id` where supported and tuple matching where needed.
- Explain the F2-only repair policy:
  - F2 numerical/correctness failures may trigger correctness feedback;
  - F0 parse/signature/surface failures terminate;
  - F1 compile/runtime failures terminate;
  - F0/F1 do not receive feedback prompts.
- Explain F3 handling:
  - malformed correctness payloads become canonical F3 rows;
  - F3 rows are terminal failures, not functional successes;
  - current G+C has five `F3_EVAL_PIPELINE` rows.
- Explain durable row writing:
  - Cluster 2 appends and fsyncs JSONL rows during long runs;
  - older partial runs are historical unless promoted.
- Cite the Cluster 2 C limitation memo when explaining why C should be interpreted as an operational but limited numerical-feedback repair loop, not as a broken implementation. Keep the template G+C evidence in diagnostic framing and outside the primary 2^2 analyzer.

Artifact status:

| Condition | Artifact | Rows | Intended rows | Caveat |
|---|---|---:|---:|---|
| `C` | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | C lacks raw top-level `compile_success`; analyzer normalization required |
| `G+C` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | missing three matmul rows; five `F3_EVAL_PIPELINE` rows |

Primary sources:

- `docs/03_methodology_cluster2.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/cluster2_c_limitation_memo.md`

## 8. Modal Infrastructure And Provenance

Scaffold content:

- Explain why Modal exists:
  - remote GPU-backed generation;
  - remote GPU compile validation;
  - remote correctness evaluation for Cluster 2;
  - repeatable smoke/development/paper-scale runner surfaces;
  - durable outputs and row-level provenance.
- State that Modal is infrastructure, not a research factor.
- State that Modal execution alone does not prove reproducibility.
- Describe provenance fields:
  - `model_id`;
  - `model_revision`;
  - `tokenizer_revision`;
  - `transformers_version`;
  - `tokenizers_version`;
  - `xgrammar_version`;
  - `grammar_sha`;
  - `grammar_path`;
  - `grammar_variant`;
  - `modal_image_sha`;
  - `modal_image_provenance_sha256`;
  - `max_new_tokens`;
  - condition, kernel, dtype, and seed/sample identity fields.
- Describe durable row writing and why it matters for long runs.
- Preserve known provenance caveats:
  - G has `modal_image_sha=unknown`;
  - none has legacy provenance limitations;
  - analyzer output has `metadata.reportable=true` via `analysis_cli_annotation`.

Primary sources:

- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/08_decision_log.md`

## 9. Evaluation Ladder And Failure Taxonomy

Scaffold content:

- Define the ladder:
  - Level 0: parse/signature/surface validity.
  - Level 1: compile/runtime launch.
  - Level 2: numerical correctness.
  - Infrastructure/eval pipeline: evaluation machinery failure.
- Define failure families:
  - F0: parse/signature/grammar/surface failure before compile/launch.
  - F1: compile/runtime launch failure.
  - F2: numerical or shape correctness failure after reaching Level 2.
  - F3: infrastructure/evaluation-pipeline failure.
- State that Cluster 1 stops at Level 1.
- State that Cluster 2 can reach Level 2 when earlier gates pass.
- Preserve `F3_EVAL_PIPELINE` policy:
  - not functional success;
  - not compile success unless independent Level 1/2 evidence exists;
  - current G+C has five F3 rows;
  - F3 caveats must remain visible.

Primary sources:

- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/03_methodology_cluster2.md`
- `docs/07_analysis_and_statistics.md`

## 10. Metrics And Analyzer Semantics

Scaffold content:

- Define `functional_success` as the primary correctness outcome for Cluster 2 and the current 2^2 functional analysis.
- Define `compile_success` as the secondary structural metric.
- Define `grammar_valid` as a grammar-funnel diagnostic for G/G+C.
- Define `failure_code` as failure-mode diagnostic and analyzer-normalization input.
- Explain Cluster 1 normalization:
  - none/G did not run Level 2;
  - none/G functional success is false/unproven in preliminary analysis;
  - compile success remains separate.
- Explain Cluster 2 compile-success normalization:
  - C may lack raw top-level `compile_success`;
  - F0/F1 imply compile failure;
  - F2 implies compile success;
  - F3 is evidence-sensitive and caveated.
- Explain pairing:
  - C vs none expected pair count: 180;
  - G+C vs G expected pair count: 177;
  - G vs none compile diagnostic: 177 when missing G rows are skipped;
  - G+C vs C compile diagnostic: 177 when missing G+C rows are skipped.
- Mention verified statistical methods without quoting final results:
  - exact McNemar-style paired binary test over discordant pairs;
  - paired bootstrap confidence intervals;
  - Wilson confidence intervals for condition rates;
  - Holm correction;
  - logistic model available but not fit in current output because functional outcome has a single observed class.
- Preserve analyzer status:
  - path: `outputs/analysis/factorial_2x2_preliminary.json`;
  - valid JSON;
  - 714 loaded rows;
  - `metadata.reportable=true`;
  - `metadata.scale_tiers=["paper"]`;
  - `metadata.raw_scale_tiers_before_annotation=["unspecified"]`;
  - `metadata.scale_tier_source="analysis_cli_annotation"`;
  - `metadata.requested_scale_tier="paper"`.

Primary sources:

- `docs/07_analysis_and_statistics.md`
- `.contracts/research/eval_metrics.md`
- `docs/05_artifacts_and_results_registry.md`

## 11. Artifacts And Provenance Registry

Use this table as the report-facing artifact summary. Do not copy raw output rows into the report.

| Report condition | Artifact | Rows | Intended rows | Current status |
|---|---|---:|---:|---|
| `none` | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | authoritative control with compile-only and legacy provenance caveats |
| `G` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | authoritative task-agnostic G artifact with coverage caveat |
| `C` | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | 180 | authoritative C artifact with analyzer normalization caveat |
| `G+C` | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | 180 | authoritative G+C artifact with coverage and F3 caveats |
| analyzer | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | N/A | valid JSON, `metadata.reportable=true` via `analysis_cli_annotation` |

Optional diagnostic/reference artifact, not a primary result table row:

| Artifact | Rows | Diagnostic status | Exclusion |
|---|---:|---|---|
| `outputs/cluster1/final_g_l4_n20.jsonl` | 180 | legacy `template_upper_bound` compile-only reference; 180/180 legacy compile success | not current primary G, not task-agnostic G, not current analyzer input, not pairable with current task-agnostic G+C |

Registry rules to carry into the report:

- Artifact identities, row counts, schema caveats, and provenance caveats are owned by `docs/05_artifacts_and_results_registry.md`.
- New artifacts cannot be cited before registration.
- Output artifacts should not be manually rewritten.
- Missing rows must remain explicit.
- Analyzer outputs must preserve their own reportability status.
- Template diagnostic artifacts must stay outside primary results tables unless a separate current-pipeline template G and matching template G+C diagnostic analysis is produced and labeled non-primary.

Primary source:

- `docs/05_artifacts_and_results_registry.md`

## 12. Preliminary Results Section - Placeholder Only

Do not fill uncaveated final-paper statistical claims. Any preliminary result prose must cite the verified `metadata.reportable=true` analyzer output and preserve all current caveats.

This section should eventually include:

- row-count table by condition;
- functional_success by condition;
- compile_success by condition;
- failure-code distributions;
- grammar-funnel metrics for G and G+C;
- paired comparison outputs;
- confidence intervals;
- reportability status and caveats.

Do not include the old template-G 180/180 artifact in the primary results tables. It can appear only in an optional diagnostic/reference paragraph or appendix, and only with the warning that primary results use task-agnostic G/G+C.

External KernelBench Level 1 context to include:

- The original KernelBench paper reports `fast1`, not compile rate, in its
  headline Level 1 baseline table. `fast0` is correctness regardless of
  speed; `fast1` is correctness plus speedup greater than 1x over the
  chosen baseline.
- Original KernelBench Table 1 Level 1 one-shot `fast1` over PyTorch
  Eager on NVIDIA L40S:

| Method/model | KernelBench Level 1 one-shot `fast1` over PyTorch Eager |
|---|---:|
| GPT-4o | 4% |
| OpenAI o1 | 10% |
| DeepSeek V3 | 6% |
| DeepSeek R1 | 12% |
| Claude 3.5 Sonnet | 10% |
| Llama 3.1-70B Instruct | 3% |
| Llama 3.1-405B Instruct | 3% |

- Original KernelBench Table 2 Level 1 `fast1` at a 10-call budget:

| Method | Llama 3.1-70B | DeepSeek V3 | DeepSeek R1 |
|---|---:|---:|---:|
| Single attempt baseline | 3% | 6% | 12% |
| Repeated sampling @10 | 5% | 11% | N/A |
| Iterative refinement with previous generation (`G`) | 9% | 9% | 18% |
| Iterative refinement with generation + execution feedback (`G+E`) | 5% | 13% | 41% |
| Iterative refinement with generation + execution + profiler feedback (`G+E+P`) | 7% | 19% | 43% |

- Use these numbers only as external benchmark context. They are not
  directly comparable to the TritonGen task-agnostic G compile rate:
  current TritonGen `G` compile success is `3/177 = 1.7%`, but that is
  Level 1 compile-only evidence on three locked KernelBench Level 1
  archetypes, three dtypes, and matched seeds. It is not a KernelBench
  `fast0`, `fast1`, or full Level 1 score.
- Suggested wording: "Against original KernelBench Level 1 context,
  frontier one-shot systems report 3-12% `fast1` over PyTorch Eager on
  the full 100-task Level 1 suite, while 10-call iterative refinement
  reaches up to 43% `fast1` for DeepSeek R1. TritonGen's current
  task-agnostic G result is a stricter lower-rung compile-only diagnostic
  over a three-task subset: `3/177 = 1.7%` compile success, with no
  Level 2 correctness or speed claim."

Expected table shells:

| Condition | Rows | Intended rows | Functional-success rate | Compile-success rate | Caveat |
|---|---:|---:|---|---|---|
| `none` | 180 | 180 | TODO: from reportable analyzer output | TODO: from reportable analyzer output | Cluster 1 compile-only; functional success unproven |
| `G` | 177 | 180 | TODO: from reportable analyzer output | TODO: from reportable analyzer output | 177/180; compile-only; G image provenance caveat |
| `C` | 180 | 180 | TODO: from reportable analyzer output | TODO: from reportable analyzer output | C compile success normalized from failure code |
| `G+C` | 177 | 180 | TODO: from reportable analyzer output | TODO: from reportable analyzer output | 177/180; five F3 rows |

| Comparison | Response | Expected pair count | Effect estimate | CI | Statistical test | Caveat |
|---|---|---:|---|---|---|---|
| C vs none | `functional_success` | 180 | TODO | TODO | TODO | none/C matching required |
| G+C vs G | `functional_success` | 177 | TODO | TODO | TODO | 177/180 coverage |
| G vs none | `compile_success` | 177 | TODO | TODO | TODO | secondary structural diagnostic |
| G+C vs C | `compile_success` | 177 | TODO | TODO | TODO | secondary diagnostic; F3 caveat |

Required warning:

> Primary results must use task-agnostic G and task-agnostic G+C. The old template-G 180/180 artifact is legacy diagnostic compile-only evidence, not primary G, not a current G+C pairing control, and not Level 2 correctness evidence.

Primary sources:

- `docs/07_analysis_and_statistics.md`
- `docs/05_artifacts_and_results_registry.md`
- Ouyang et al. 2025, "KernelBench: Can LLMs Write Efficient GPU Kernels?"

## 13. Failure-Mode Analysis Section - Scaffold

Planned subsections:

- F0/F1/F2/F3 distribution by condition.
- Grammar rejection layers for G and G+C.
- `grammar_valid`, `gbnf_parse_valid`, and `semantic_valid` funnel summaries.
- `F3_EVAL_PIPELINE` rows in G+C.
- Missing rows and coverage caveats.
- Modal/provenance caveats.
- Distinction between compile failure and functional failure.

Report constraints:

- Do not hide F3 rows as successes.
- Do not treat grammar acceptance as compile success.
- Do not treat compile success as functional success.
- Do not silently drop missing rows.

Primary sources:

- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/07_analysis_and_statistics.md`
- `docs/05_artifacts_and_results_registry.md`

## 14. Threats To Validity

Include at least these threats:

- n=20 per cell target is small and should be presented as preliminary-scale evidence.
- G and G+C are 177/180, not complete 180/180 artifacts.
- The missing G/G+C rows are matmul-specific.
- Cluster 1 is compile-only and does not run Level 2 correctness.
- Analyzer output has `metadata.reportable=true` via `analysis_cli_annotation`.
- G has `modal_image_sha=unknown`.
- none has legacy schema/provenance limitations.
- G+C has five `F3_EVAL_PIPELINE` rows.
- C lacks raw top-level `compile_success` and requires analyzer normalization.
- Task-agnostic grammar enforces a harness surface contract, not the full Triton language.
- No performance, timing, profiling, or speedup claim is currently in scope.
- Current design is 2^2 only; Cluster 3/P and full 2^3 are deferred.

Primary sources:

- `docs/02_methodology_cluster1.md`
- `docs/03_methodology_cluster2.md`
- `docs/04_modal_infrastructure.md`
- `docs/05_artifacts_and_results_registry.md`
- `docs/07_analysis_and_statistics.md`

## 15. Reproducibility Checklist

Checklist for final report assembly:

- [ ] Artifact paths match `docs/05_artifacts_and_results_registry.md`.
- [ ] Row counts are cited from the registry.
- [ ] G/G+C 177/180 caveat is visible.
- [ ] Missing matmul rows are named.
- [ ] Model revisions are documented where present.
- [ ] Tokenizer revisions are documented where present.
- [ ] Grammar SHA/path/variant are documented for G/G+C.
- [ ] Modal image ID or fallback provenance is documented.
- [ ] `modal_image_sha=unknown` for G is caveated.
- [ ] JSONL validity and schema shape are documented.
- [ ] Failure taxonomy is cited.
- [ ] Analyzer output path is cited.
- [ ] Analyzer `metadata.reportable=true` and scale-tier annotation metadata are cited.
- [ ] Source-of-truth docs are cited for each methodology claim.
- [ ] Agentic notes and audits are not used as primary methodology prose unless promoted.

Primary sources:

- `docs/05_artifacts_and_results_registry.md`
- `docs/04_modal_infrastructure.md`
- `docs/06_failure_taxonomy_and_eval_ladder.md`
- `docs/handoff/codebase_handoff_guide.md`

## 16. Lessons For Cluster 3

Scaffold content:

- Define P before code.
- Define what P can observe before any feedback loop exists.
- Define allowed feedback boundaries before implementation.
- Define failure classes and F3-style infrastructure semantics before paper-scale work.
- Define metrics and analyzer support before runs.
- Define artifact schema before Modal execution.
- Require artifact registration before reporting.
- Require smoke, development, audit, and provenance gates before n=20.
- Avoid Cluster 2 drift patterns:
  - hidden factor changes;
  - missing provenance;
  - mixed schemas without analyzer normalization;
  - missing-row drift;
  - stale docs that outlive implementation changes.

Cluster 3 must inherit:

- source-of-truth hierarchy;
- artifact registry discipline;
- durable row writing;
- reportability metadata;
- explicit pairing identity;
- failure-code to metric mappings;
- caveat-first reporting.

Primary sources:

- `docs/08_decision_log.md`
- future `docs/10_cluster3_drift_prevention_plan.md`

## 17. Appendix Plan

Planned appendices:

- Decision log summary: cite `docs/08_decision_log.md`.
- Artifact registry: cite `docs/05_artifacts_and_results_registry.md`.
- Code path map: use methodology docs and traceability tables.
- Audit trail: cite audits only as evidence-grade supporting material.
- Stale docs inventory: cite `docs/handoff/stale_docs_inventory.md`.
- Contract diff review: use `.contracts/agentic/preliminary_report_handoff/phase_8_contract_diff_review.md` as handoff evidence, not report-facing methodology.
- Command snippets: include only after each command is verified against current CLI/code.

Appendix rules:

- Do not paste raw prompts.
- Do not copy long audit prose.
- Do not treat `.contracts/agentic/` as citation-grade.
- Do not include output rows directly.

## 18. Writing Checklist

Before turning this outline into report prose, verify:

- [ ] No uncaveated final-paper statistical claims beyond the verified 2^2 output.
- [ ] No full 2^3 completion claim.
- [ ] No Cluster 3/P result claim.
- [ ] No Cluster 1 functional correctness claim.
- [ ] No timing, profiling, speedup, or performance result claim.
- [ ] No claim that G or G+C is complete 180/180 coverage.
- [ ] No template G primary claim.
- [ ] No old template-G 180/180 artifact in primary results tables.
- [ ] Any template-G mention is labeled legacy diagnostic/reference and compile-only.
- [ ] No grammar-valid equals compile-success claim.
- [ ] No compile-success equals functional-success claim.
- [ ] No hidden F3-as-success claim.
- [ ] Every methodology claim points to a citation-grade doc or formal contract.
- [ ] Every artifact/result claim points to `docs/05_artifacts_and_results_registry.md`.
- [ ] Every statistics claim points to reportable analyzer output or is explicitly caveated as non-final.

## 19. Section-To-Source Matrix

| Report section | Primary source doc | Artifact source | Status | Blocker/Caveat |
|---|---|---|---|---|
| Executive Summary | `README.md`; `docs/00_project_map.md`; `docs/08_decision_log.md` | `docs/05_artifacts_and_results_registry.md` | ready as outline | Caveated 2^2 stats only |
| Plain-Language Background | `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | N/A | ready as explanatory scaffold | Avoid final-result language |
| Research Question And Scope | `.contracts/research/research_scope.md`; `docs/08_decision_log.md` | analyzer path from registry | ready | 2^2 only; Cluster 3/P deferred |
| Experimental Conditions | `docs/02_methodology_cluster1.md`; `docs/03_methodology_cluster2.md` | all four JSONL artifacts in registry | ready | Template G diagnostic/reference only |
| Dataset And Kernel Scope | `docs/02_methodology_cluster1.md`; `.contracts/research/scale_policy.md` | registry coverage table | ready | G/G+C 177/180 |
| Cluster 1 Methodology | `docs/02_methodology_cluster1.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | none/G artifacts | ready | Compile-only; no functional correctness |
| Cluster 2 Methodology | `docs/03_methodology_cluster2.md`; `docs/06_failure_taxonomy_and_eval_ladder.md` | C/G+C artifacts | ready | F2-only repair; F3 caveat |
| Modal Infrastructure | `docs/04_modal_infrastructure.md` | artifact provenance summaries | ready | G image ID unknown; baseline legacy |
| Evaluation Ladder | `docs/06_failure_taxonomy_and_eval_ladder.md` | failure codes in registry/analyzer docs | ready | F3 rows visible |
| Metrics And Analyzer Semantics | `docs/07_analysis_and_statistics.md`; `.contracts/research/eval_metrics.md` | analyzer JSON | scaffold ready | reportable via `analysis_cli_annotation`; caveats remain |
| Artifacts And Registry | `docs/05_artifacts_and_results_registry.md` | registry owns paths/counts | ready | Do not mutate outputs |
| Preliminary Results Placeholder | `docs/07_analysis_and_statistics.md` | analyzer JSON | ready for caveated preliminary values | Needs caveat-preserving prose and no full 2^3/P claim |
| Failure-Mode Analysis | `docs/06_failure_taxonomy_and_eval_ladder.md`; `docs/07_analysis_and_statistics.md` | failure distributions from registry/docs | scaffold ready | Do not hide F3 or missing rows |
| Threats To Validity | all methodology docs; `docs/08_decision_log.md` | all current artifacts | ready | Must keep caveats visible |
| Reproducibility Checklist | `docs/04_modal_infrastructure.md`; `docs/05_artifacts_and_results_registry.md` | all current artifacts | ready | Provenance gaps remain caveats |
| Lessons For Cluster 3 | `docs/08_decision_log.md` | future registry entries only | scaffold ready | Do not define P results |
| Appendix Plan | `docs/handoff/stale_docs_inventory.md`; handoff files as evidence | registry | scaffold ready | Agentic files are not citation-grade |
