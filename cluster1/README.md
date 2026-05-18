# Cluster 1 - Grammar Constraints

**Status:** frozen as template-grammar upper-bound reference control  
**Research scope:** `.contracts/research/research_scope.md`  
**Generated surface:** `.contracts/research/cluster1_generated_surface.md`

## Purpose

Cluster 1 isolates the G factor for Triton-only kernel generation. Its job is
to answer how much structural validity comes from grammar-guided decoding plus
offline semantic post-validation, before any test-driven feedback or
compiler/profiler repair is introduced.

The current Cluster 1 result is deliberately reframed:

> The strict family-scoped grammar is a template-grammar upper bound, not the
> final grammar result.

This is a useful control. It establishes the ceiling of what task-aware grammars
can achieve when they encode the selected KernelBench families directly. It
does not prove that general task-agnostic G enforcement for Triton generation
works.

## G Enforcement Model

Cluster 1 G is implemented as grammar-guided decoding plus offline semantic
post-validation. XGrammar masks tokens during decoding using the GBNF grammar.
The offline validator enforces additional structural and surface checks. A
generated candidate is counted as G-accepting only if it passes both layers.

Rows that pass token-level decoding but fail the offline validator are
grammar-rejected. They should be attributed to the failing layer where possible,
for example `gbnf_parse`, `python_ast`, `semantic_validator`,
`runtime_error`, or `unknown`.

## Current Frozen Result

The frozen Cluster 1 Modal comparison used the same model, prompt, temperature,
seed schedule, dtype coverage, and compile-only validator for baseline and G.
The intended G toggle was activation of the grammar-guided path and its
associated validation contract.

| Condition | Compile successes | Interpretation |
| --- | ---: | --- |
| `none` | 0/180 | Unconstrained baseline fails the canonical generated-code surface |
| `G` template grammar reference | 180/180 | Task-aware grammar forces compile-accepted canonical ReLU/Softmax/GEMM modules |

The template G reference condition also has `unique_solution_rate = 0.05` per
kernel/dtype cell: one unique solution among 20 seeds. That is the key
diagnostic. The grammar successfully forces structural validity, but it
collapses diversity and behaves like template instantiation.

## Grammar Attribution Language

Task-agnostic G is the primary grammar condition for paper claims. Template G is a diagnostic/reference upper bound,
and template G reference is not used as the primary grammar-effect estimate.

Template G reference is not equivalent to task-agnostic G. Any result using
`template_upper_bound` must be labeled as reference/diagnostic, and any primary
task-agnostic G comparison must use the task-agnostic grammar unless it is
explicitly labeled otherwise.

Paper-safe claim:

> A task-aware, family-scoped Triton grammar can force compile acceptance for
> the scoped ReLU, Softmax, and GEMM subset, but the result is an upper-bound
> control and not evidence of broad task-agnostic G enforcement for Triton
> generation.

## Scale Policy

Cluster 1 follows the shared scale policy in
`.contracts/research/scale_policy.md`.

The current frozen diagnostic/reference template-grammar run uses `n=20`, but it is still a
three-kernel template-control subset: ReLU, Softmax, and GEMM. Treat it as a
paper-style upper-bound control for that subset, not as the full future
paper-scale factorial.

For future paper-scale runs:

- keep the current template grammar frozen as `template_upper_bound` reference;
- report `template_upper_bound` only as reference/diagnostic on the original
  three-kernel subset unless a later contract explicitly expands it;
- use the planned task-agnostic Triton grammar for the primary task-agnostic G
  condition on the larger 6-9 kernel paper-scale set;
- attach `scale_tier`, `kernel_count`, `model_id`, `grammar_variant`, and seed
  schedule metadata before combining Cluster 1 artifacts with later clusters.

If the diagnostic/reference template grammar is expanded to cover more kernels, that expansion must be
reported as a new task-aware upper-bound control. It should not be relabeled as
general task-agnostic G enforcement for Triton generation.

## Grammar Variants

Cluster 1 should ultimately report two grammar variants side by side.

| Variant | Status | Purpose |
| --- | --- | --- |
| `template_upper_bound` reference | implemented and frozen | Measures the diagnostic/reference ceiling when the grammar is allowed to encode ReLU/Softmax/GEMM family structure |
| `task_agnostic` primary | planned | Measures genuine Triton-language syntactic guidance without task-specific body templates |

Do not mutate the current diagnostic/reference template grammar into the task-agnostic grammar. Keep it
fixed as the upper-bound control and add the task-agnostic grammar separately.

## Pre-Registered Task-Agnostic Interpretation Thresholds

These thresholds are fixed before any task-agnostic Modal run:

- Tiny n=1 task-agnostic smoke: GO if 3/3 rows are written, there are no
  infrastructure failures, all rows have `grammar_active=True`,
  `grammar_variant=task_agnostic`, and `masked_token_rate` is non-null.
  `grammar_active` means constrained decoding was attempted; G acceptance is
  measured by `grammar_valid=True`, which requires both `gbnf_parse_valid=True`
  and `semantic_valid=True`.
  `compile_success` is informative but not required at n=1.
- n=5 task-agnostic smoke: STRONG_SIGNAL if compile success is >=9/15,
  PARTIAL_SIGNAL if compile success is 1-8/15, WEAK_OR_ZERO_SIGNAL if compile
  success is 0/15, and STRUCTURAL_FAILURE if SignatureError, missing launcher,
  or grammar invalidity dominates.
- Final n=20: report the measured result without post-hoc grammar tuning unless
  failure is a genuine task-agnostic Triton language-surface bug.

The planned task-agnostic grammar should constrain the Triton/Python language
surface, not the benchmark task. It must not hard-code:

- specific launcher names such as `relu`, `softmax`, or `matmul`;
- fixed ReLU/Softmax/GEMM statement sequences;
- benchmark-specific loop nests;
- specific task operation semantics like "softmax must use `tl.exp`";
- fixed output allocation and launch wrappers tied to only the current three
  problems.

It may still constrain:

- valid Python module shape;
- imports and no-markdown/no-prose surface;
- valid `@triton.jit` helpers and launch wrappers;
- allowed Triton API names and arities;
- block-size literal families and hardware-safe ranges;
- parseable expressions, indexing, masks, and control flow.

## Task-Agnostic API Reference Evidence

The task-agnostic grammar's `triton.language` allow-list is verified against a
pinned official docs snapshot:

- Reference source: `https://triton-lang.org/main/python-api/triton.language.html`
- Docs source label: `main` as fetched on `2026-05-16T00:00:00Z`
- Local pasted corpus gate: `.contracts/agentic/reference/triton_corpus.md`
- Snapshot: `cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json`
- Snapshot SHA-256: `a7a637be7f80d59a0764838a6d21a945e7d17e85f1781992fa5089c67b6a1b80`
- Extracted grammar allow-list: `cluster1/grammar/corpus/grammar_allowlist_extracted.json`
- Coverage report: `cluster1/grammar/corpus/api_coverage_report.md`
- Offline CI guard: `cluster1/tests/test_api_coverage.py`
- Targeted validation: `.venv/bin/python -m pytest cluster1/tests/test_api_coverage.py cluster1/tests/test_grammar_acceptance.py -v`

CI compares against the pinned JSON snapshot and its SHA-256 and does not fetch
live docs. Treat Triton `main` as the upstream source label, not as a stable
citation target. Paper and reviewer-facing docs should cite the local snapshot
path, extraction timestamp, and SHA-256 above. To refresh the reference, run the
extractor manually with network access and then regenerate the grammar
allow-list, coverage report, and expected SHA in the same commit.

## In Scope

Cluster 1 may do only these things:

- generate Triton Python modules;
- apply grammar-guided decoding with GBNF token masks;
- apply offline semantic post-validation for G acceptance;
- apply grammar/hardware token masks;
- validate generated source against the Cluster 1 generated-code surface;
- run dummy Triton launches to check compile acceptance;
- record compile success/failure, masked-token rate, diversity hashes, and
  compile error summaries;
- analyze compile@1, pass@k over compile success, unique solution rate, and
  failure taxonomy.

## Out of Scope

Cluster 1 must not do these things:

- numerical correctness checks against PyTorch references;
- `torch.allclose` or `torch.testing`;
- test-driven repair;
- compiler/profiler repair;
- profiler feedback;
- timing, benchmarking, speedup, or fast@p reporting;
- compute-sanitizer or memory-safety evaluation;
- RL, fine-tuning, or model weight updates;
- raw CUDA/C++/CUTLASS/CuTe/custom DSL generation.

## Relationship to Later Clusters

Cluster 1 provides the structural controls used to interpret later results.

Cluster 2 adds test-driven feedback. It should answer whether semantic
correctness feedback can recover what task-agnostic grammar alone cannot.

Cluster 3 adds compiler/profiler repair. It should answer whether compiler
errors, runtime traces, and benchmark feedback compose with grammar and
test-driven feedback, or interfere with them.

The final paper should compare:

```text
none
G_task_agnostic
G_template_upper_bound_reference
C
G_task_agnostic+C
P
G_task_agnostic+P
C+P
G_task_agnostic+C+P
```

The template upper bound can be reported as a reference/diagnostic control row,
not as the primary task-agnostic G cell in the factorial interaction model.

## Key Artifacts

Current frozen artifacts:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl`
- `outputs/cluster1/final_none_vs_g_l4_n20.jsonl`
- `outputs/cluster1/final_none_vs_g_l4_n20_summary.md`
- `outputs/cluster1/cluster1_final_summary.md`

Primary implementation paths:

- `cluster1/grammar/triton_kernel.gbnf`
- `cluster1/grammar/triton_kernel_validator.py`
- `cluster1/generation/constrained_gen.py`
- `cluster1/generation/constrained_decoding.py`
- `cluster1/validation/compile_check.py`
- `cluster1/experiments/run_cluster1_modal.py`
- `cluster1/experiments/analyze_cluster1.py`

## Next Cluster 1 Work

Before making broad paper claims about task-agnostic G enforcement:

1. Keep the current template grammar frozen as `template_upper_bound` reference.
2. Add a separate task-agnostic Triton grammar.
3. Add `grammar_variant` to future result/eval metadata where needed.
4. Run `none` vs `G_task_agnostic` vs `G_template_upper_bound_reference`.
5. Report the gap between task-agnostic and template-aware grammar as evidence
   of task encoding versus syntactic guidance.

Do not start Cluster 2 or Cluster 3 work inside `cluster1/`. Later mechanisms
must live in their own cluster packages and call shared Modal/eval components.
