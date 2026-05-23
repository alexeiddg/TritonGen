# Cluster 1 - Grammar Guidance

**Status:** current primary G is task-agnostic; legacy template G is diagnostic only  
**Current methodology:** `docs/02_methodology_cluster1.md`  
**Current artifact registry:** `docs/05_artifacts_and_results_registry.md`  
**Research scope:** `.contracts/research/research_scope.md`

## Purpose

Cluster 1 implements the grammar-guided generation factor (`G`) for
Triton-only kernel generation. Its current report-facing role is to provide
compile-only evidence for task-agnostic grammar-guided decoding plus offline
semantic post-validation.

Cluster 1 does not run Level 2 numerical correctness, repair loops, timing,
profiling, or speedup measurement. Compile success is structural evidence only.

## Current Primary G Status

Current primary G uses the task-agnostic grammar variant:

| Role | Artifact | Rows | Current status |
| --- | --- | ---: | --- |
| Baseline control | `outputs/cluster1/baseline_repaired_l4_n20.jsonl` | 180 | current 2^2 control with legacy schema/provenance caveats |
| Primary G | `outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl` | 177 | current task-agnostic G with coverage caveat |

The current primary G artifact is 177/180, not 180/180. Missing rows are
`matmul/fp32` seed 5 and `matmul/bf16` seeds 0 and 18. Do not fill those gaps
from template-G artifacts.

## Legacy Template-G Diagnostic

The old template artifact is preserved only as historical diagnostic evidence:

| Artifact | Rows | Legacy evidence | Current exclusion |
| --- | ---: | --- | --- |
| `outputs/cluster1/final_g_l4_n20.jsonl` | 180 | `template_upper_bound` compile-only diagnostic; 180/180 legacy compile success | not primary G, not task-agnostic G, not Level 2 correctness, not current analyzer input, and not pairable with current task-agnostic G+C |

That artifact fails the current paper-scale generation metadata gate. It lacks
the current split grammar validation fields, grammar provenance,
model/tokenizer revisions, Modal image/provenance fields, package versions,
stop reason, and row-level `scale_tier`.

Valid claim:

> Under the legacy Cluster 1 template grammar setup,
> `outputs/cluster1/final_g_l4_n20.jsonl` produced 180/180 compile-success
> rows over the legacy n=20 per kernel/dtype grid.

Invalid claims:

- current primary G evidence;
- task-agnostic G evidence;
- current task-agnostic G+C pairing evidence;
- Level 2 functional correctness;
- current primary 2^2 analyzer evidence.

## G Enforcement Model

Cluster 1 G is grammar-guided decoding plus offline semantic post-validation.
XGrammar masks tokens during decoding using a GBNF grammar. The offline
validator then enforces structural and surface checks that the grammar cannot
fully express.

A generated candidate is counted as G-accepting only when:

```text
grammar_valid = gbnf_parse_valid AND semantic_valid
```

`grammar_active=true` means constrained decoding was attempted. It is not
evidence that the row was accepted by G.

## Grammar Variants

| Variant | Current role | Notes |
| --- | --- | --- |
| `task_agnostic` | primary G | Current report-facing G condition, implemented by `cluster1/grammar/triton_kernel_agnostic.gbnf` |
| `template_upper_bound` | diagnostic/reference only | Legacy or explicit template-reference control; must not replace task-agnostic G |

Template G reference is not equivalent to task-agnostic G. Any result using
`template_upper_bound` must be labeled as diagnostic/reference, and a fair
template diagnostic comparison would require matching current-pipeline template
G and template G+C artifacts analyzed separately from the primary 2^2 results.

## Kernel Scope

Current Cluster 1 artifacts use three locked KernelBench Level 1 archetypes:

| Kernel class | Kernel name | Public launcher | KernelBench problem ID |
| --- | --- | --- | ---: |
| elementwise | ReLU | `relu(x: torch.Tensor) -> torch.Tensor` | 19 |
| reduction | Softmax | `softmax(x: torch.Tensor) -> torch.Tensor` | 23 |
| matmul | GEMM/matmul | `matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor` | 1 |

The current n=20 target spans three kernel classes, three dtypes, and 20 seeds
per kernel/dtype cell.

## Generated Surface Contract

For the task-agnostic grammar, generated modules must follow the harness
surface documented in `cluster1/docs/grammar_surface_contract.md`:

- fixed imports: `import torch`, `import triton`, and
  `import triton.language as tl`;
- one to three `@triton.jit` helper functions;
- one public Python launcher with a stable callable signature;
- output allocation through `torch.empty_like(...)` or `torch.empty(...)`;
- explicit `grid` computation before launch;
- bracket launch syntax such as `helper[grid](...)`;
- return of the allocated output tensor.

This is a harness surface contract, not the full Triton language.

## In Scope

Cluster 1 may:

- generate Triton Python modules;
- apply GBNF/XGrammar token masks during decoding;
- apply offline semantic post-validation for G acceptance;
- validate generated source against the Cluster 1 harness surface;
- run dummy Triton launches to check compile acceptance;
- record compile outcomes, grammar-funnel fields, masked-token diagnostics,
  diversity hashes, and provenance where available.

## Out Of Scope

Cluster 1 must not:

- run numerical correctness checks against PyTorch references;
- run test-driven repair;
- run compiler/profiler repair;
- use profiler feedback;
- report timing, benchmarking, speedup, or fast@p;
- generate raw CUDA/C++/CUTLASS/CuTe/custom DSL code;
- fine-tune, RL-train, or update model weights.

## Key Implementation Paths

- `cluster1/grammar/triton_kernel_agnostic.gbnf`
- `cluster1/grammar/triton_kernel.gbnf`
- `cluster1/grammar/triton_kernel_validator.py`
- `cluster1/generation/constrained_gen.py`
- `cluster1/generation/constrained_decoding.py`
- `cluster1/validation/compile_check.py`
- `cluster1/experiments/run_cluster1_modal.py`
- `cluster1/experiments/analyze_cluster1.py`

## Reporting Rules

- Use `docs/02_methodology_cluster1.md` and
  `docs/05_artifacts_and_results_registry.md` as the current source of truth.
- Present task-agnostic G as the current primary G condition.
- Present `outputs/cluster1/final_g_l4_n20.jsonl` only as legacy
  `template_upper_bound` compile-only diagnostic evidence.
- Do not use legacy template rows to fill missing task-agnostic rows.
- Do not pair legacy template G with current task-agnostic G+C.
- Do not convert Cluster 1 compile success into Level 2 functional success.
