# Cluster 1 Methodology

## 1. Purpose

Cluster 1 is the implementation layer for `G`, the grammar-guided generation factor in the current preliminary handoff. `G` means grammar-guided generation: model decoding is constrained by a Triton-oriented grammar, and the resulting source is checked by offline validation before compile validation.

The current report uses task-agnostic `G` as the primary `G` condition. The primary grammar variant is `task_agnostic`, implemented at `cluster1/grammar/triton_kernel_agnostic.gbnf`. Template `G` remains diagnostic/reference material only. It must not be described as the primary grammar condition.

Cluster 1 exists to test whether grammar guidance improves structural and compile outcomes for LLM-generated Triton kernels. It does not test numerical correctness or performance.

## 2. Plain-Language Explanation

A GPU kernel is low-level code that runs many small pieces of work in parallel on a GPU. Triton is a Python-like language for writing those GPU kernels while still exposing GPU concepts such as program IDs, blocks, memory loads, stores, and launch grids.

LLMs can generate Triton code, but generated code often fails before it can be useful. It may include prose, malformed Python, missing imports, wrong launcher names, invalid Triton syntax, bad signatures, invalid launch grids, or code that compiles for only some dtypes. Grammar guidance exists to narrow generation toward the module surface and Triton API forms that the evaluation harness can parse and compile.

Compile success is only a first gate. A kernel can compile and still compute the wrong values, mishandle shapes, be slow, or fail on correctness workloads. Cluster 1 records compile acceptance as structural evidence, not functional correctness.

## 3. Scope Boundary

Cluster 1 is compile-only.

Cluster 1 does not run numerical correctness evaluation. It does not claim functional correctness. It does not run repair loops. It does not run performance, timing, profiling, or speedup evaluation. It is not Cluster 3 and does not implement the `P` factor.

Cluster 1 outputs support Level 0/Level 1 style evidence: parse/signature/surface validity and compile/runtime launch acceptance. Level 2 numerical correctness belongs to later evaluation paths, primarily Cluster 2 for the current preliminary handoff.

Boundary tests in `cluster1/tests/test_cluster_boundary.py` explicitly guard against correctness checks, timing/profiling, speedup claims, repair loops, and compile-error feedback loops entering Cluster 1.

## 4. Role In The Current 2^2 Design

The current preliminary design is the 2^2 subset over grammar guidance and correctness feedback:

- `none`: no grammar guidance and no correctness-feedback repair.
- `G`: Cluster 1 grammar guidance.
- `C`: Cluster 2 correctness-feedback repair.
- `G+C`: Cluster 2 combined grammar guidance plus correctness-feedback repair.

Cluster 1 implements the `G` factor and supplies the current `none` and `G` artifacts used by the artifact registry and analyzer.

| Report condition | Uses G? | Uses C? | Source artifact |
| --- | ---: | ---: | --- |
| none | no | no | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` |
| G | yes | no | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` |

`C` and `G+C` are Cluster 2 conditions and are documented later in `docs/03_methodology_cluster2.md`.

## 5. What G Enforces

`G` uses two enforcement layers:

1. Token-level grammar-guided decoding through GBNF/XGrammar.
2. Offline semantic post-validation of the generated source.

The acceptance field is:

```text
grammar_valid = gbnf_parse_valid AND semantic_valid
```

A row is G-accepting only when both layers pass. This is not a claim that the GBNF alone captures all Triton semantics. The semantic validator checks surface and structural rules that a context-free grammar cannot fully express, such as required launcher/helper relationships, output allocation behavior, launch shape, and allowed structural forms.

Primary paths:

| Role | Path |
| --- | --- |
| Token-level grammar loading | `cluster1/generation/grammar_loader.py` |
| Logits masking during decoding | `cluster1/generation/constrained_decoding.py` |
| Grammar variant mapping | `cluster1/generation/grammar_variants.py` |
| Offline layered validation | `cluster1/grammar/triton_kernel_validator.py` |
| Shared metadata constants | `shared/generation_metadata.py` |

## 6. Task-Agnostic Grammar

The primary grammar variant for current reporting is `task_agnostic`.

| Variant | Path | Current reporting role |
| --- | --- | --- |
| `task_agnostic` | `cluster1/grammar/triton_kernel_agnostic.gbnf` | Primary `G` condition |
| `template_upper_bound` | `cluster1/grammar/triton_kernel.gbnf` | Diagnostic/reference only |

Task-agnostic `G` is primary because `G` and `G+C` must share the same grammar semantics. The shared mapping in `shared/generation_metadata.py` marks `task_agnostic` as `primary` and `template_upper_bound` as `diagnostic_non_primary`.

The template grammar is a reference/diagnostic upper bound. It should not be used as the primary grammar-effect estimate and should not be substituted for missing task-agnostic rows.

The current-pipeline template upper-bound G diagnostic artifact `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` exists for Cluster 1 compile-only reference. It uses `grammar_variant=template_upper_bound` and `cluster1/grammar/triton_kernel.gbnf`, passes the current Cluster 1 metadata gate, and remains non-primary. Task-agnostic `G` remains the primary G condition.

The old template-G artifact `outputs/cluster1/final_g_l4_n20.jsonl` is legacy compile-only diagnostic evidence. It has 180 rows and 180/180 `compile_success=true` under legacy validation, but it fails the current paper-scale generation metadata gate and is not current analyzer-compatible as primary G. It is not task-agnostic G, not Level 2 correctness evidence, not current G+C pairing evidence, and not a source for filling the three missing task-agnostic G rows.

## 7. Structural Surface Contract

Cluster 1 imposes a harness surface contract so generated kernels can be called and evaluated consistently. For the task-agnostic grammar, the generated module must follow a bounded module shape:

- fixed imports: `import torch`, `import triton`, and `import triton.language as tl`;
- one to three `@triton.jit` helper functions;
- one public Python launcher with a stable callable signature;
- output allocation through `torch.empty_like(...)` or `torch.empty(...)`;
- explicit `grid` computation before launch;
- bracket launch syntax such as `helper[grid](...)`;
- return of the allocated output tensor.

This is a harness surface contract, not the full Triton language. Triton permits many valid Python organization patterns that Cluster 1 intentionally excludes so the harness can locate one entry point, run compile probes, and compare conditions.

Supporting paths:

- `cluster1/docs/grammar_surface_contract.md`
- `cluster1/data/prompts/prompt_contract.py`
- `cluster1/tests/test_generated_surface_contract.py`
- `cluster1/tests/test_grammar.py`

## 8. KernelBench And Kernel Scope

Cluster 1 currently uses three locked KernelBench Level 1 archetypes:

| Kernel class | Kernel name | Public launcher | KernelBench problem ID |
| --- | --- | --- | ---: |
| elementwise | ReLU | `relu(x: torch.Tensor) -> torch.Tensor` | 19 |
| reduction | Softmax | `softmax(x: torch.Tensor) -> torch.Tensor` | 23 |
| matmul | GEMM/matmul | `matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor` | 1 |

The IDs are verified by the current kernel specs in:

- `cluster1/data/kernels/elementwise_relu.py`
- `cluster1/data/kernels/reduction_softmax.py`
- `cluster1/data/kernels/matmul_tiled_gemm.py`
- `cluster1/tests/test_kernel_id_consistency.py`

The matmul row keeps `kernel_name="gemm"` for dataset identity while the required public launcher is `matmul`.

Original KernelBench context:

- KernelBench defines Level 1 as 100 single-primitive tasks, Level 2 as
  100 operator-sequence tasks, and Level 3 as 50 full-architecture tasks
  (Ouyang et al., 2025, "KernelBench: Can LLMs Write Efficient GPU
  Kernels?").
- KernelBench problem 1 is "Square matrix multiplication"; problem 19 is
  "ReLU"; problem 23 is "Softmax". Average-pooling tasks are problem IDs
  44-46, and reduction tasks are problem IDs 47-53 in the original
  KernelBench Level 1 list.
- The current TritonGen preliminary subset therefore covers square
  matrix multiplication, ReLU, and Softmax only. Do not describe problem
  19 as average pooling or problem 23 as a generic multi-dimensional
  reduction.
- KernelBench's primary `fast_p` metric combines functional correctness
  with timing. The current Cluster 1 task-agnostic G
  artifact is Level 1 compile-only evidence and is not a KernelBench
  `fast_p`, `fast0`, or `fast1` result.

## 9. Cluster 1 Pipeline

The Cluster 1 flow is:

```text
prompt/kernel spec
-> model generation
-> optional grammar guidance
-> source extraction/normalization
-> grammar/semantic validation
-> compile validation
-> JSONL result logging
-> artifact registry
-> analyzer normalization
```

Key implementation paths:

| Pipeline step | Code path |
| --- | --- |
| Kernel specs | `cluster1/data/kernels/` |
| Prompt contract | `cluster1/data/prompts/prompt_contract.py` |
| Grammar files | `cluster1/grammar/triton_kernel_agnostic.gbnf`, `cluster1/grammar/triton_kernel.gbnf` |
| Grammar loader and decoder | `cluster1/generation/grammar_loader.py`, `cluster1/generation/constrained_gen.py`, `cluster1/generation/constrained_decoding.py` |
| Provenance helpers | `cluster1/generation/provenance.py`, `shared/generation_metadata.py` |
| Offline validation | `cluster1/grammar/triton_kernel_validator.py` |
| Compile validation | `cluster1/validation/compile_check.py`, `cluster1/validation/modal_compile_check.py` |
| Result schema/logger | `cluster1/results/dataclass.py`, `cluster1/results/logger.py` |
| Local runner | `cluster1/experiments/run_cluster1.py` |
| Modal runner wrapper | `cluster1/experiments/run_cluster1_modal.py` |
| Shared analyzer normalization | `shared/analysis/factorial.py` |

The Modal runner records compile errors as result fields. It does not feed compile errors back into the prompt and does not trigger regeneration based on compile failures.

## 10. Compile Validation

`compile_success` is the main Cluster 1 outcome. In Cluster 1, compile validation means the generated Triton module passed the configured parse/signature/import and dummy-launch compile gate across the configured dtype probes.

The main compile path is `cluster1/validation/compile_check.py`. It performs:

- shared Level 0 parse check;
- shared Level 0 signature check;
- generated module import;
- launcher signature check by parameter names;
- dummy launches for fp32, fp16, and bf16 shape schedules.

`compile_success=True` does not mean numerically correct. It does not mean fast. It does not imply Level 2 success.

The shared Level 1 adapter in `shared/eval/levels/level1_compile.py` wraps the same Cluster 1 compile gate for shared evaluation contexts.

## 11. Result Schema And Metadata

Cluster 1 rows are represented by `GenerationResult` in `cluster1/results/dataclass.py` and written by `cluster1/results/logger.py`.

Important fields include:

| Field group | Fields |
| --- | --- |
| Condition and identity | `grammar_active`, `grammar_variant`, `kernel_class`, `kernel_name`, `dtype`, `generation_seed`, `run_id` |
| Source and diversity | `source`, `unique_solution_hash` |
| Compile outcome | `compile_success`, `compile_results_by_dtype`, `compile_error_type`, `compile_error_msg`, `failure_code`, `n_shapes_tested` |
| Grammar evidence | `grammar_sha`, `grammar_path`, `gbnf_parse_valid`, `semantic_valid`, `grammar_valid`, `rejection_layer`, `masked_token_rate`, `stop_reason` |
| Provenance | `model_id`, `model_revision`, `tokenizer_revision`, `xgrammar_version`, `transformers_version`, `tokenizers_version`, `modal_image_sha`, `modal_image_provenance_sha256`, `modal_image_provenance_components`, `generation_metadata_schema_version` |

Current artifact caveats from `docs/05_artifacts_and_results_registry.md`:

- The none artifact is a flat legacy Cluster 1 artifact. It lacks `condition`, `generated_metadata`, and current model/tokenizer/modal/package provenance fields.
- The current G artifact is also flat, has no nested `generated_metadata`, and records `modal_image_sha=unknown`, although model/tokenizer revisions, package versions, grammar SHA, and fallback Modal image provenance fields are present.

## 12. Current Authoritative Artifacts

The artifact source of truth is `docs/05_artifacts_and_results_registry.md`.

| Condition | Artifact path | Rows | Intended rows | Current role |
| --- | --- | ---: | ---: | --- |
| none | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | 180 | Baseline replay/control |
| G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | 180 | Primary task-agnostic grammar condition |

The G artifact is 177/180, not 180/180. Missing G rows:

| Kernel class | Dtype | Missing seed |
| --- | --- | ---: |
| matmul | fp32 | 5 |
| matmul | bf16 | 0 |
| matmul | bf16 | 18 |

Do not use old n=5 artifacts for current report-scale claims. Do not use template-G artifacts as primary `G`. Do not fill the three missing task-agnostic rows from template-G outputs.

Legacy template diagnostic artifact:

| Artifact path | Rows | Legacy evidence | Current exclusion |
| --- | ---: | --- | --- |
| `outputs/cluster1/final_g_l4_n20.jsonl` | 180 | `template_upper_bound` compile-only diagnostic; 180/180 legacy compile success | Not primary G, not task-agnostic G, not Level 2 correctness, not current analyzer input, and not pairable with current task-agnostic G+C |

Current template upper-bound diagnostic artifact:

| Artifact path | Rows | Current evidence | Current exclusion |
| --- | ---: | --- | --- |
| `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` | 180 | `template_upper_bound` compile-only diagnostic; 180/180 compile success; current metadata gate PASS | Not primary G, not task-agnostic G, not Level 2 correctness, not current analyzer input, not a source for filling missing task-agnostic G rows, and not a complete template G+C diagnostic comparison |

## 13. Analyzer Semantics For Cluster 1

For preliminary `functional_success` analysis, Cluster 1 rows normalize `functional_success` to `False`/unproven. This is a methodological boundary: Cluster 1 did not run Level 2 correctness evaluation.

`compile_success` is preserved separately as a structural compile metric. `compile_success=True` is not treated as `functional_success=True`.

Supporting paths:

- `shared/analysis/factorial.py`
- `shared/tests/test_factorial_analysis.py`
- `audits/factorial_cluster1_functional_success_normalization_fix_report.md`

The later `docs/07_analysis_and_statistics.md` page owns the full statistical and analyzer semantics. This document records only the Cluster 1 boundary needed to avoid overclaims.

## 14. Tests And Traceability

| Claim | Code path | Test path | Artifact path | Caveat |
| --- | --- | --- | --- | --- |
| Task-agnostic grammar is primary for current `G` | `shared/generation_metadata.py`; `cluster1/generation/grammar_variants.py`; `cluster1/grammar/triton_kernel_agnostic.gbnf` | `cluster1/tests/test_documentation_language_lock.py`; `cluster1/tests/test_run_cluster1_modal.py`; `cluster1/tests/test_grammar.py` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | `shared.generation_metadata.DEFAULT_GRAMMAR_VARIANT` remains `template_upper_bound` for legacy/default compatibility; current report uses registry and run metadata for primary `G`. |
| Cluster 1 is compile-only | `cluster1/validation/compile_check.py`; `cluster1/validation/modal_compile_check.py`; `shared/eval/adapter_cluster1.py` | `cluster1/tests/test_cluster_boundary.py`; `cluster1/tests/test_compile_check.py`; `cluster1/tests/test_results.py` | `outputs/cluster1/baseline_repaired_l4_n20.jsonl`; `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | Compile-only does not prove Level 2 correctness. |
| G artifact is 177/180 | `cluster1/experiments/run_cluster1_modal.py`; registry path | Phase 2 artifact inspection; coverage evidence in audits | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | Missing matmul/fp32 seed 5 and matmul/bf16 seeds 0 and 18. |
| Template G is diagnostic/reference | `shared/generation_metadata.py`; `cluster1/generation/grammar_variants.py` | `cluster1/tests/test_documentation_language_lock.py`; `shared/tests/test_reporting_language.py`; `audits/template_g_180_legacy_compatibility_audit.md`; `audits/template_upper_bound_g_current_pipeline_n20_l4_run_report.md` | `outputs/cluster1/template_upper_bound_g_current_pipeline_n20_l4.jsonl` is registered as current diagnostic evidence; `outputs/cluster1/final_g_l4_n20.jsonl` is registered only as legacy diagnostic evidence | Template G must not replace task-agnostic G, fill missing task-agnostic rows, or enter the primary analyzer. |
| `grammar_valid` is joint GBNF plus semantic validation | `cluster1/grammar/triton_kernel_validator.py`; `cluster1/results/dataclass.py` | `cluster1/tests/test_grammar.py`; `cluster1/tests/test_generation_provenance.py`; `cluster1/tests/test_results.py` | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | GBNF parser acceptance alone is not enough. |
| Cluster 1 `functional_success` is unproven | `shared/analysis/factorial.py`; `shared/eval/adapter_cluster1.py` | `shared/tests/test_factorial_analysis.py`; `cluster1/tests/test_cluster_boundary.py` | none/G artifacts omit `functional_success` | Analyzer normalizes to `False` for preliminary functional analysis. |

## 15. Known Caveats

- G is 177/180, not 180/180.
- Missing G rows are matmul/fp32 seed 5, matmul/bf16 seed 0, and matmul/bf16 seed 18.
- Cluster 1 is compile-only and has no Level 2 correctness evidence.
- Cluster 1 has no performance, timing, profiling, or speedup evaluation.
- The G artifact records `modal_image_sha=unknown`.
- The none artifact has legacy schema/provenance limitations.
- Old n=5 and template artifacts are legacy or diagnostic evidence only.
- The current template upper-bound G diagnostic artifact is compile-only and non-primary; a matching template G+C artifact is still required for a template correctness-feedback diagnostic comparison.
- The analyzer output exists at `outputs/analysis/factorial_2x2_preliminary.json` and currently has `metadata.reportable=true` under explicit scale-tier annotation, with Cluster 1 compile-only and provenance caveats preserved.

## 16. What This Document Does Not Claim

This document does not claim:

- full 2^3 factorial completion;
- Cluster 3 or `P` results;
- functional correctness for Cluster 1;
- speedup or performance results;
- that task-agnostic GBNF fully models Triton;
- complete 180/180 G coverage;
- that template `G` is the primary grammar condition;
- that compile success implies numerical correctness.

## 17. Open TODOs For Later Phases

- Phase 4: document Cluster 2 methodology in `docs/03_methodology_cluster2.md`, including `C`, `G+C`, F2-only repair, F0/F1 no-repair behavior, replay controls, and pairing.
- Phase 5: define the failure taxonomy, evaluation ladder, F3 policy, and analyzer semantics in `docs/06_failure_taxonomy_and_eval_ladder.md` and `docs/07_analysis_and_statistics.md`.
- Phase 6: document Modal infrastructure and provenance in `docs/04_modal_infrastructure.md`.
- Phase 8: align README and `.contracts/research/*` after methodology docs stabilize.
- Phase 9: outline the preliminary report without converting caveated analyzer output into final report claims.
