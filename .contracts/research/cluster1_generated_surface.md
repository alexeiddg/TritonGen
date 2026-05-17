# Cluster 1 Generated Code Surface

## Decision

Cluster 1 uses a function-launcher generated-code surface. It does not use the
KernelBench `Model(torch.nn.Module)` class surface.

The KernelBench `Model` class surface is future adapter work. It must be added
through an explicit KernelBench adapter later, not mixed implicitly into Cluster
1 generation, grammar validation, or compile validation.

## Grammar v1 Scope

The Cluster 1 grammar v1 is a scoped experimental grammar for the current
evaluation subset only: ReLU, Softmax, and GEMM. G acceptance is a two-layer
contract: token-level GBNF guidance during decoding plus offline semantic
post-validation after generation.

This is not a universal Triton grammar and must not be described as one. Future
KernelBench expansion requires explicit grammar generalization beyond these
family-specific wrappers.

## Task-Agnostic API Reference Coverage

For the task-agnostic grammar, the `triton.language` API allow-list is evidenced
by `cluster1/grammar/corpus/api_coverage_report.md`. That report is the
canonical audit artifact tying `cluster1/grammar/triton_kernel_agnostic.gbnf`
to the pinned official Triton language reference snapshot in
`cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json`.
That snapshot's current SHA-256 is
`a7a637be7f80d59a0764838a6d21a945e7d17e85f1781992fa5089c67b6a1b80`.
The grammar allow-list evidence must be extracted from the GBNF alternatives,
not from a hand-maintained Triton signature table.
The pasted Triton corpus at `.contracts/agentic/reference/triton_corpus.md` is
the first offline gate before the pinned official reference snapshot: it must
enumerate the same public `triton.language` function and parameter surface.

Paper methodology should cite the coverage report version/source when describing
task-agnostic G as grammar-guided decoding plus offline semantic
post-validation over a harness-imposed structural surface and a documented
`triton.language` API allow-list. Template G remains a diagnostic/reference
upper bound and must not be used as the primary grammar-effect estimate. Do not
claim universal Triton API coverage or complete grammar coverage beyond the
functions, in-scope grammar forms, and validator-enforced surface checks audited
for this project.
Because the upstream source URL is Triton `main`, paper-facing citations must
identify the pinned local JSON snapshot by path, extraction timestamp, and
SHA-256 rather than citing `main` as a stable version.

## GBNF vs Semantic Validator Responsibilities

The GBNF layer captures the context-free, token-level surface used by XGrammar
for decoding masks: module syntax, allowed imports and decorators where encoded,
Triton helper and launcher productions, expression forms, control-flow forms,
literal families, and grammar-level `tl.*` API names, arities, and keyword forms.

The semantic validator is the offline post-generation layer. It enforces the
parts of the Cluster 1 surface that are context dependent, structural, or
outside the reliable context-free GBNF layer, including public launcher signatures,
helper-count rules, duplicate helper detection, defined-name checks, launcher
attribute checks, runtime output allocation checks, grid construction, bracket
launch syntax, return-output requirements, helper statement placement, and any
validator-only API/surface checks.

The `tl.*` API allow-list may be represented in both layers. The GBNF layer
provides token-level API guidance; the semantic validator may still reject a
source that parses under the GBNF if it violates the canonical Cluster 1 surface.
A row is G-accepting only when both layers pass. A row that decodes under
XGrammar but fails the semantic validator is grammar-rejected, not compile- or
functional-success evidence.

## Canonical Module Shape

Every generated Cluster 1 source must be one complete Python module with no
markdown fences and no prose.

The module must start with these imports in this order:

```python
import torch
import triton
import triton.language as tl
```

The module must then define exactly one private Triton helper kernel:

```python
@triton.jit
def _<launcher_name>_kernel(...):
    ...
```

An optional fixed-space `@triton.autotune(...)` decorator may appear before
`@triton.jit` only when it uses prompt-contract configs accepted by the grammar.

The module must then define exactly one public Python launcher. The launcher name
and signature are the current `KernelSpec.compile_spec` contract and are checked
with `inspect.signature()` equality before any dummy launch. That means parameter
annotations and the return annotation are required.

Current launchers:

| kernel_class | KernelSpec.name | public launcher | required signature |
| --- | --- | --- | --- |
| elementwise | `relu` | `relu` | `relu(x: torch.Tensor) -> torch.Tensor` |
| reduction | `softmax` | `softmax` | `softmax(x: torch.Tensor) -> torch.Tensor` |
| matmul | `gemm` | `matmul` | `matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor` |

The matmul row keeps `KernelSpec.name == "gemm"` for dataset identity, but the
generated public launcher must be `matmul` because compile validation uses
`CompileSpec.launcher_name == "matmul"`.

## Launcher Requirements

The public launcher must:

1. Allocate an output tensor.
2. Define an explicit `grid`.
3. Invoke the private Triton helper with bracket launch syntax:

```python
_<launcher_name>_kernel[grid](...)
```

4. Return the output tensor.

`.run(...)` launch syntax is not part of the current canonical Cluster 1
surface.

## Alignment Rule

The prompt, GBNF grammar, offline grammar validator, golden fixtures, and compile
validator must all agree on this surface. Passing the decoding layer alone is
not sufficient for G acceptance. If a candidate source satisfies the GBNF parser
but fails a validator-only structural or semantic rule, it must be recorded as a
grammar rejection with failure-layer attribution. The contract is broken only if
the pipeline records such a row as G-accepting, or if the documented layer
boundary is inconsistent with the implemented validator.
