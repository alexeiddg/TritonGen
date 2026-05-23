# Research Scope

**Status:** research-facing scope summary aligned to the current documentation layer  
**Last aligned:** 2026-05-21  
**Audience:** preliminary report planning, thesis notes, committee-facing methodology

## Purpose

This contract states the current formal research scope for TritonGen. It is
aligned to `docs/00_project_map.md`, `docs/05_artifacts_and_results_registry.md`,
`docs/07_analysis_and_statistics.md`, and `docs/08_decision_log.md`.

The current deliverable is a preliminary Cluster 1 + Cluster 2 technical
handoff. It is not a final research paper.

## Current Preliminary Scope

The current populated study is the 2^2 subset over grammar guidance and
correctness feedback:

| Report condition | Meaning | Current artifact |
| --- | --- | --- |
| `none` | no grammar and no correctness repair | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| `G` | task-agnostic grammar-guided decoding plus semantic post-validation | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |
| `C` | correctness-feedback repair only | `outputs/cluster2/c_paper_n20_l4.jsonl` |
| `G+C` | task-agnostic G plus C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` |

The full 2^3 design and the `P` factor are deferred. P-containing cells
(`P`, `G+P`, `C+P`, `G+C+P`) are not current results and must not be described as
complete or reportable.

## Mechanism Definitions

| Factor | Current status | Mechanism | Boundary |
| --- | --- | --- | --- |
| `G` | current | task-agnostic grammar-guided decoding plus semantic post-validation | Cluster 1; compile-only outcome evidence |
| `C` | current | correctness-feedback repair restricted to F2 numerical/correctness failures | Cluster 2; F0/F1 terminate without repair feedback |
| `P` | deferred | performance/compiler/profiler feedback | Cluster 3 must define semantics before code or results |

Template G and `template_upper_bound` artifacts are diagnostic/reference
material only. They are not the current primary G condition and must not be used
to fill task-agnostic G coverage gaps.

The old template artifact `outputs/cluster1/final_g_l4_n20.jsonl` is preserved
only as legacy `template_upper_bound` compile-only diagnostic evidence. It is
not task-agnostic G, not current primary G, not current G+C pairing evidence,
and not Level 2 functional correctness evidence.

## G Acceptance Contract

Current primary G uses the task-agnostic grammar variant. G acceptance requires
both:

- token-level grammar-guided decoding using GBNF/XGrammar; and
- offline semantic post-validation.

The acceptance field is:

```text
grammar_valid = gbnf_parse_valid AND semantic_valid
```

`grammar_active=true` means grammar-guided decoding was attempted. It does not
by itself mean that a row was accepted by G. `grammar_valid` is a grammar-funnel
diagnostic, not compile success or functional success.

## Evaluation Boundary

Cluster 1 is compile-only. It stops at Level 1 compile/launch validation and
does not run Level 2 numerical correctness. Cluster 1 `compile_success` is a
structural metric, not a functional-correctness claim. In preliminary functional
analysis, none/G rows normalize `functional_success=False` as unproven because
Level 2 was not run.

Cluster 2 evaluates generated C and G+C rows through the Level 0/1/2 ladder
when earlier gates pass. C repair is restricted to F2 numerical/correctness
failures. F0 parse/signature/surface failures and F1 compile/runtime failures
terminate without repair feedback.

F3 failures, including `F3_EVAL_PIPELINE`, represent evaluation-pipeline or
infrastructure failures. They are not functional successes.

## Current Artifact And Analyzer Status

Current artifact identities and row counts are owned by
`docs/05_artifacts_and_results_registry.md`:

| Artifact role | Path | Rows | Caveat |
| --- | --- | ---: | --- |
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | compile-only; legacy schema/provenance |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | missing three matmul rows; compile-only; `modal_image_sha=unknown` |
| C | `outputs/cluster2/c_paper_n20_l4.jsonl` | 180 | C lacks raw `compile_success`; analyzer normalization required |
| G+C | `outputs/cluster2/g_plus_c_paper_n20_l4.jsonl` | 177 | missing same three matmul rows; five `F3_EVAL_PIPELINE` rows |
| analyzer | `outputs/analysis/factorial_2x2_preliminary.json` | 714 loaded rows | valid JSON; `metadata.reportable=true` via `analysis_cli_annotation`; P cells deferred |

The analyzer output is reportable for the current covered 2^2 scope under the
recorded paper-scale annotation. It is not a full 2^3/P result and must carry
the 177/180, F3, single-class model, and provenance caveats.

## Scale Boundary

Scale policy is defined in `.contracts/research/scale_policy.md`.

The current registered 2^2 artifacts are n=20 preliminary-scale artifacts for
this handoff. Development n=5 artifacts, smoke outputs, template-G artifacts,
failed runs, and partial runs are historical evidence unless explicitly
promoted into the artifact registry.

## Triton-Only Boundary

The generated artifact under study is a Python module containing Triton kernels
and Python launch wrappers. The project does not generate raw CUDA C/C++,
CUTLASS, CuTe, TVM, MLIR, or custom DSL kernels.

The project also does not fine-tune, RL-train, or otherwise update model
weights. Current mechanisms are inference-time controls around fixed model
weights.

## Non-Goals For Current Preliminary Scope

- Full 2^3 results.
- Cluster 3 or P results.
- Cluster 1 functional-correctness claims.
- Performance, timing, profiling, or speedup claims.
- Treating template-G as primary G.
- Treating missing G/G+C rows as ignorable.
- Treating analyzer output as broader than the verified, caveated 2^2 scope.

## Future Cluster 3 Boundary

Cluster 3 must define the P factor before implementation or paper-scale runs.
At minimum it must define allowed feedback, failure classes, performance
metrics, artifact schema, provenance requirements, analyzer behavior, and
registry rules before any P artifact can become report-facing evidence.
