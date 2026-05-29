# Preliminary Report: Grammar and Correctness Feedback for LLM-Generated Triton Kernels

Date: 2026-05-22
Repository: `/Users/alexeidelgado/Desktop/TritonGen`
Analyzer output: `outputs/analysis/factorial_2x2_preliminary.json`
Dashboard: `docs/preliminary_report/index.html`
Scope: 2^2 preliminary report over `none`, `G`, `C`, and `G+C`
Status: preliminary technical report

## 1. Executive Summary

This report asks whether inference-time control mechanisms improve the quality of LLM-generated Triton GPU kernels. The current study is a 2^2 factorial subset over grammar guidance (`G`) and correctness feedback (`C`), with matched seeds over ReLU, Softmax, and GEMM/matmul cells across fp32, fp16, and bf16. The paper-scale target is 20 rows per kernel/dtype cell, or 180 intended rows per condition; the current task-agnostic `G` and `G+C` artifacts are 177/180 because three matmul rows are missing.

The verified analyzer output is reportable for the covered 2^2 scope and loads 714 rows. It reports zero `functional_success` rows in every condition: `none` 0/180, `G` 0/177, `C` 0/180, and `G+C` 0/177. For Cluster 1 conditions, that value is conservative normalization because Level 2 was not run. Grammar-active conditions produced a small compile floor: `G` had 3/177 compile successes, and `G+C` had 4 compile successes with the analyzer's F3-excluded condition-rate denominator of 172. Correctness feedback alone had 0/180 compile and functional successes. The methodological contribution is an audited pipeline with artifact provenance, failure taxonomy, and paired analysis. Deferred work includes Cluster 3/`P`, frontier-model replication, and a current-pipeline template upper-bound diagnostic rerun.

## 2. Plain-Language Introduction

### 2.1 The problem

A GPU kernel is a small program that runs many parallel operations on a GPU. Kernels are the inner loops of accelerated computing: they load data, perform arithmetic, and write results while respecting the GPU's execution and memory model. Triton is a Python-like language for writing GPU kernels without dropping all the way into CUDA C++. It lets a programmer express blocks, program IDs, vectorized loads, stores, and launch grids in a form that can be compiled into efficient GPU code.

LLM-generated Triton is hard because "looks like code" is far below the bar for a usable kernel. A generated module may fail to parse as Python, expose the wrong function signature, use an unsupported surface form, fail Triton compilation, crash at runtime, or compile and launch while returning numerically wrong values. These failures occur at different stages and require different evidence. Parse success is not compile success; compile success is not numerical correctness; numerical correctness is still separate from timing or speed claims.

Researchers care about this problem because GPU programming is specialized and expensive. If LLMs could generate reliable Triton kernels, they might reduce the manual burden of writing kernels and make optimization work more accessible. The current study does not claim that outcome. It tests whether two narrow inference-time controls move generated kernels through the first stages of the evaluation ladder.

### 2.2 The research question

The general question is whether inference-time control mechanisms improve LLM-generated Triton kernel quality. The specific current study compares four conditions: `none`, task-agnostic grammar guidance (`G`), correctness feedback (`C`), and their composition (`G+C`).

Task-agnostic means the grammar is not a per-task template that encodes the body of ReLU, Softmax, or matmul. Instead, current primary `G` uses a Triton-oriented surface contract plus semantic post-validation. This distinction matters because a task-encoded template can force a much narrower solution family. Template `G` is therefore treated only as diagnostic/reference material in this report, not as the primary grammar condition.

## 3. Methodology

### 3.1 Experimental design

The populated experiment is a temporary 2^2 factorial subset over the `G` and `C` factors. The four current conditions are: `none`, with no grammar guidance and no correctness repair; `G`, with task-agnostic grammar-guided decoding plus semantic post-validation; `C`, with correctness-feedback repair only; and `G+C`, which composes task-agnostic `G` with `C`. Cluster 3 and the `P` factor are deferred, so P-containing cells are not included in this report.

Matched-seed pairing is central to the design. Rows are matched by kernel identity, dtype, and seed, with tuple matching for Cluster 1 controls and replay metadata where available for Cluster 2 rows. `C` is paired against the frozen `none` control, and `G+C` is paired against the frozen task-agnostic `G` control. The current `G` and `G+C` artifacts cover 177 of 180 intended rows. The missing covered-row identities are matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18. The analyzer policy skips these missing identities rather than imputing them.

### 3.2 Model and infrastructure

The generated artifacts use `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`. Current `G`, `C`, and `G+C` rows record model and tokenizer revision `8e8ed243bbe6f9a5aff549a0924562fc719b2b8a`; the legacy `none` artifact records the model id but lacks current revision provenance. Temperature is recorded as 0.2 in the four inspected artifacts. The current Cluster 2 rows (`C` and `G+C`) record `max_new_tokens=2048`; the inspected `G` artifact does not serialize that field, so this report treats token budget as artifact-recorded provenance rather than a universal row fact.

Execution used Modal-backed GPU infrastructure, documented as L4 for the current paper-scale artifacts. Modal is infrastructure, not a research factor. It supports remote generation, compile validation, correctness evaluation for Cluster 2, durable row writing, and row-level provenance. Modal execution alone does not guarantee reproducibility; the useful evidence is the recorded model/tokenizer revisions, package versions, grammar SHA, Modal image identifier or fallback image provenance, prompt/replay identity, and immutable artifacts. The current G artifact records `modal_image_sha=unknown` but has fallback Modal image provenance SHA. `C` and `G+C` record `modal_image_sha=im-tU3VQyAbFvrusOxtlwspCN`. The `none` artifact has legacy provenance gaps.

### 3.3 Kernels and dataset

The study uses three locked KernelBench Level 1 archetypes: ReLU as an elementwise kernel, Softmax as a reduction kernel, and GEMM/matmul as a matrix multiplication kernel. Each archetype is evaluated across fp32, fp16, and bf16. This gives nine kernel/dtype cells. At the n=20 paper-scale target, each condition has 180 intended rows. `none` and `C` have 180 valid rows. `G` and `G+C` each have 177 valid rows because of the three missing matmul rows named above.

### 3.4 Evaluation ladder

The evaluation ladder separates surface validity from compile/runtime behavior and numerical correctness. Level 0 covers parse, signature, and surface validity. Typical F0 failures include `F0_PARSE` for Python syntax errors and `F0_BAD_SIGNATURE` for a callable that does not match the harness. Level 1 covers Triton compile and runtime launch; examples are `F1_COMPILE` and `F1_RUNTIME`. Level 2 covers numerical correctness against reference outputs; examples include `F2_NUMERIC_NAN`, `F2_NUMERIC_LARGE`, and `F2_SHAPE_MISMATCH`. F3 codes represent infrastructure or evaluation-pipeline failures rather than generated-kernel success. The current G+C artifact contains five `F3_EVAL_PIPELINE` rows.

### 3.5 Cluster 1 vs Cluster 2 evaluation surface

The C1/C2 Evaluation Surface Audit classifies Cluster 1 as `C1_COMPILE_ONLY_BY_DESIGN` and Cluster 2 as `C2_FULL_LEVEL0_LEVEL1_LEVEL2_WITH_F2_REPAIR`. The accepted asymmetry is `ASYMMETRY_ACCEPTED_COMPILE_ONLY_DESIGN` with `ASYMMETRY_REQUIRES_REPORT_CAVEAT`.

Cluster 1 evaluates generated Triton source through grammar metadata validation and a compile gate that includes Level 0-style parse/signature checks plus Triton import, JIT, and dummy-launch checks. It then stops. It does not run shared Level 2 numerical correctness and does not record `functional_success`. Cluster 2 evaluates generated `C` and `G+C` rows through explicit Level 0 parse/signature, Level 1 compile, and Level 2 numerical correctness gates, with repair feedback only after allowed F2 numerical failures.

For preliminary functional analysis, Cluster 1 `functional_success` is normalized to false/unproven. This is conservative and should not be read as observed Level 2 failure. A compile-success row may be numerically correct, but without Level 2 evaluation it is unmeasured. For `G`, the reported 0/177 functional-success rate is therefore a conservative lower bound that could undercount any numerically correct kernels among the three compile-success rows. Therefore this report does not claim measured functional correctness for Cluster 1 rows. It reports Cluster 1 compile success separately as a structural outcome.

### 3.6 Repair loop semantics

The `C` repair loop is intentionally narrow. It fires only when Level 2 runs and produces an allowed F2 numerical or shape correctness failure. F0 parse/signature/surface failures terminate without repair, and F1 compile/runtime failures also terminate without repair. This preserves `C` as correctness feedback rather than a hidden parser or compile-error repair mechanism. Current docs specify that feedback contains public Level 2 information and excludes private eval leakage and compile-error hints. The standard repair budget is documented as five iterations. In the current artifacts, the four G+C rows that reached F2 have trace length 6, consistent with an initial attempt plus five repairs.

### 3.7 Statistical analysis

The primary response variable is `functional_success`. The primary paired comparisons are `C` vs `none` and `G+C` vs `G`. The secondary structural response is `compile_success`, with diagnostic paired comparisons `G` vs `none` and `G+C` vs `C`. The analyzer emits Wilson 95% confidence intervals for condition rates, exact McNemar-style paired binary tests over discordant pairs, paired bootstrap confidence intervals with 10,000 samples and seed 13013, and Holm correction. The functional logistic model is not fit because all loaded rows have the same functional outcome class. `F3_EVAL_PIPELINE` rows are excluded from G+C compile-success condition-rate denominators and treated as compile failures in matched-pair analysis when independent compile-pass evidence is absent.

## 4. Results

### 4.1 Headline numbers

The analyzer JSON has `metadata.reportable=true`, `metadata.scale_tiers=["paper"]`, and `metadata.scale_tier_source="analysis_cli_annotation"`. Its diagnostics report 714 loaded rows.

| Condition | Rows | Compile Success | Functional Success |
|---|---:|---:|---:|
| `none` | 180 | 0/180 (0.00%, Wilson 95% CI [0.00%, 2.09%]) | 0/180 (0.00%, Wilson 95% CI [0.00%, 2.09%]; Cluster 1 normalized false/unproven) |
| `G` | 177 | 3/177 (1.69%, Wilson 95% CI [0.58%, 4.86%]) | 0/177 (0.00%, Wilson 95% CI [0.00%, 2.12%]; Cluster 1 normalized false/unproven) |
| `C` | 180 | 0/180 (0.00%, Wilson 95% CI [0.00%, 2.09%]) | 0/180 (0.00%, Wilson 95% CI [0.00%, 2.09%]) |
| `G+C` | 177 | 4/172 (2.33%, Wilson 95% CI [0.91%, 5.83%]); matched analysis 4/177 | 0/177 (0.00%, Wilson 95% CI [0.00%, 2.12%]) |

The G+C compile condition-rate denominator is 172 because the analyzer excludes five `F3_EVAL_PIPELINE` rows from compile-success rate denominators. Matched-pair compile analysis still uses 177 covered G+C rows and treats the F3 rows as compile failures absent independent compile-pass evidence.

### 4.2 Paired comparisons

| Comparison | Response | Pairs | Lift | 95% bootstrap CI | p-value | Holm p-value |
|---|---|---:|---:|---:|---:|---:|
| `C` vs `none` | functional_success | 180 | 0.00 pp | [0.00, 0.00] pp | 1.000 | 1.000 |
| `G+C` vs `G` | functional_success | 177 | 0.00 pp | [0.00, 0.00] pp | 1.000 | 1.000 |
| `G` vs `none` | compile_success | 177 | +1.69 pp | [0.00, 3.95] pp | 0.250 | 0.250 |
| `G+C` vs `C` | compile_success | 177 | +2.26 pp | [0.56, 4.52] pp | 0.125 | 0.250 |

Neither primary functional comparison shows a lift. The two compile comparisons are secondary diagnostics and are not significant after Holm correction. The analyzer records functional additive difference-in-differences as 0.0 and does not report a logistic interaction coefficient because the functional outcome has a single observed class.

### 4.3 Failure-mode analysis

The raw artifacts show different failure surfaces by condition. The legacy `none` artifact has 180 rows with `compile_success=false` and no canonical `failure_code` values, so this report does not assign a specific F0 subtype to those rows. `C` has 180/180 `F0_PARSE` rows, so correctness feedback alone never reaches Level 1 or Level 2 in the current setup. `G` has 3 rows with no failure code and `compile_success=true`, plus 152 `F1_RUNTIME`, 9 `F1_COMPILE`, and 13 `F0_PARSE` rows. `G+C` has 4 `F2_NUMERIC_NAN`, 146 `F1_RUNTIME`, 10 `F1_COMPILE`, 12 `F0_PARSE`, and 5 `F3_EVAL_PIPELINE` rows. The repair loop reached F2 candidates only in G+C, with four F2 rows exhausting the five-iteration budget without functional success.

### 4.4 Grammar funnel

| Condition | Rows | gbnf_parse_valid | semantic_valid | grammar_valid | Rejection layers | Compile success | Functional success |
|---|---:|---:|---:|---:|---|---:|---:|
| `G` | 177 | 105/177 (59.32%) | 49/177 (27.68%) | 49/177 (27.68%) | 72 `gbnf_parse`, 56 `semantic_validator` | 3/177 | 0/177 normalized false/unproven |
| `G+C` | 177 | 100/177 (56.50%) | 52/177 (29.38%) | 52/177 (29.38%) | 77 `gbnf_parse`, 48 `semantic_validator` | 4/172 condition-rate denominator; 4/177 matched | 0/177 |

The grammar funnel shows that token-level and semantic acceptance are not enough to ensure Triton compile success. Roughly 28-29% of grammar-active rows pass joint grammar validation, but only 1.69-2.33% survive the compile condition-rate metric, and none reaches functional success.

## 5. Interpretation

### 5.1 What the numbers say

The strongest result is negative at the Level 2 outcome: the analyzer reports zero `functional_success` rows in the current covered 2^2 setup. For Cluster 1 rows, that is a conservative lower bound because Level 2 was not measured. For Cluster 2 rows, it is a direct Level 2 outcome.

Task-agnostic grammar guidance creates a small compile floor. `G` produced 3/177 compile successes where `none` produced 0/180, and `G+C` produced 4 compile successes. This is structural evidence, not numerical-correctness evidence. Correctness feedback alone did not improve outcomes because `C` had 180/180 parse failures and therefore no viable candidates for Level 2 repair. The combined condition slightly improves compile success over `C` in secondary diagnostics, but it still has 0/177 functional successes. In this setup, feedback needed candidates that reached Level 2, and only four G+C rows did so.

### 5.2 Template upper-bound interpretation

The old template `G` artifact with 180/180 legacy compile success is diagnostic/reference only. It is a template upper-bound, compile-only artifact from a legacy pipeline, not primary task-agnostic `G`, not Level 2 correctness evidence, not a current G+C pairing control, and not an input to the primary 2^2 analyzer. It should not be mixed into the headline tables above. A fair template upper-bound comparison would require a separate current-pipeline template `G` rerun and a matching current-pipeline template `G+C` diagnostic analysis, both clearly labeled non-primary.

### 5.3 Feedback mechanism implications

The C mechanism is correctly constrained to F2 failures. That is methodologically important because F0/F1 repair would answer a different question. The current data suggest that correctness feedback is only useful after generation produces candidates that compile, launch, and reach numerical evaluation. Future `P`/Cluster 3 work may address different failure classes or performance-oriented questions, but it is deferred until its semantics, metric contract, artifact schema, and analyzer behavior are defined.

## 6. Threats to Validity

This is a single-model study over `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`; results may not generalize to larger, smaller, or frontier models. The kernel set covers only three archetypes: elementwise ReLU, reduction Softmax, and GEMM/matmul. These are useful workload patterns but not the full range of Triton programs.

Coverage is incomplete for grammar-active conditions. `G` and `G+C` are 177/180, with missingness concentrated in matmul rows. G+C also has five `F3_EVAL_PIPELINE` rows. The analyzer policy is explicit, but different F3 policies would change the G+C compile denominator. Cluster 1 and Cluster 2 have asymmetric evaluation surfaces: Cluster 1 is compile-only, while Cluster 2 measures Level 2 for generated `C` and `G+C` rows. The resulting Cluster 1 functional-success normalization is conservative but not a direct numerical measurement.

The evaluation is strict. `compile_success` is a structural metric and does not imply usefulness. `functional_success` is stricter but still limited to the current correctness harness. No performance, timing, profiling, or speedup metrics are reported. The study is not a full 2^3, does not include Cluster 3/`P`, does not include frontier-model results, and does not bound RL or fine-tuning approaches. Finally, task-agnostic `G` is a harness surface contract and semantic validator, not the full Triton language.

## 7. Reproducibility and Provenance

The current artifacts preserve enough provenance for a caveated preliminary report, but not every condition has the same metadata depth. `G`, `C`, and `G+C` record model/tokenizer revisions where inspected; `none` has legacy provenance gaps. Grammar-active rows record task-agnostic grammar path `cluster1/grammar/triton_kernel_agnostic.gbnf` and grammar SHA `7896a1befca10f68ab6aa4521681fa2577eba6fb669e87daf622c15691a22e32`. Current rows record package versions such as Transformers 4.47.1, Tokenizers 0.21.1, and XGrammar 0.1.33 where present.

The analyzer output records `metadata.reportable=true`, `scale_tiers=["paper"]`, `scale_tier_source="analysis_cli_annotation"`, and `raw_scale_tiers_before_annotation=["unspecified"]`. This annotation is accepted for the current registered 2^2 artifacts; raw JSONL rows were not rewritten. The artifact registry, decision log, and audits provide the traceability layer. The verified count is 714 loaded rows across current primary artifacts, not 720 generated rows. The intended grid is 720 rows, with `G` missing 3 and `G+C` missing 3.

## 8. Forward Plan

The immediate next diagnostic is a current-pipeline template upper-bound rerun if a template comparison is needed. That rerun should produce both template `G` and matching template `G+C` evidence under current metadata, and it should remain separate from primary task-agnostic `G`.

Cluster 3/`P` should proceed only after `P` semantics, allowed feedback, metric contract, row schema, artifact registry policy, and analyzer behavior are defined. A future full 2^3 can then add `P`, `G+P`, `C+P`, and `G+C+P` cells. Frontier-model replication and performance metrics are future work after correctness and measurement contracts are in place.

## 9. Appendix / Companion Materials

Companion materials:

| Material | Path |
|---|---|
| HTML dashboard | `docs/preliminary_report/index.html` |
| Analyzer JSON | `outputs/analysis/factorial_2x2_preliminary.json` |
| Artifact registry | `docs/05_artifacts_and_results_registry.md` |
| Decision log | `docs/08_decision_log.md` |
| Cluster 1 methodology | `docs/02_methodology_cluster1.md` |
| Cluster 2 methodology | `docs/03_methodology_cluster2.md` |
| Audit trail | `audits/` |
