# Cluster 1 Grammar Surface Contract

Cluster 1's `G` control is a structural surface plus Triton API allow-list. It
is not a complete grammar for the Triton language, and paper wording should not
describe it as one.

The contract separates two concerns:

- Structural harness constraints: the generated module shape required by the
  evaluation harness.
- Triton API coverage: the `tl.*` names and call shapes that the grammar permits
  inside JIT helpers.

## Structural Harness Constraints

The public module surface is imposed by the Cluster 1 evaluation harness. These
rules make generated kernels easy to call, validate, and compare across model
conditions. They are not Triton language semantics.

For the task-agnostic grammar, the generated module must contain:

- the fixed imports `torch`, `triton`, and `triton.language as tl`;
- one to three `@triton.jit` helper functions;
- exactly one public Python launcher with typed tensor/scalar parameters and a
  `torch.Tensor` return annotation;
- an output allocation using `torch.empty_like(...)` or `torch.empty(...)`;
- an explicit `grid` binding before launch;
- one bracket launch of a helper kernel using `helper[grid](...)`;
- a final return of the allocated output tensor.

The one to three helper cap is pragmatic and evaluation-set dependent. It keeps
the generation surface bounded while covering the Cluster 1 corpus fixtures and
the current Level 1-style kernels. It is not a Triton property. Level 2+,
multi-stage fused kernels, or kernels with several reusable combiner/helper
functions may require lifting the cap under a separately named grammar variant.

The single typed launcher rule is also a harness interface requirement. Triton
itself permits other valid Python organization patterns, including top-level
launch code, additional host-side helper functions, or different wrapper
signatures. Cluster 1 excludes those forms so that compile validation can locate
one entry point deterministically.

The launcher allocation/grid/bracket-launch/return pattern is an evaluation
contract. A rejection caused only by missing output allocation, missing typed
launcher, direct module-level launch, or use of a different host wrapper shape
should be classified as `HARNESS_CONTRACT_RESTRICTION`, not as evidence that the
Triton program is invalid.

## Triton API Allow-list

The task-agnostic grammar has no generic `tl.<name>(...)` fallback. Every
callable Triton API must be present in the allow-list and have an accepted call
shape. This is the part of `G` that is legitimately about Triton language/API
coverage.

As of the May 15, 2026 corpus audit, the allow-list covers the official
`triton.language` API families represented in
`.contracts/agentic/reference/triton_corpus.md`:

- programming model calls: `program_id`, `num_programs`;
- creation, shape, linear algebra, memory, pointer, and descriptor APIs;
- indexing, math, activation, reduction, scan/sort, atomic, and RNG APIs;
- `tl.range`, `tl.static_range`, `tl.inline_asm_elementwise`;
- compiler hints and debug operations.

The local corpus and the official Triton language reference list do not include
`tl.tanh`. Its absence from the allow-list is therefore not currently a
corpus-validated gap. If a future official tutorial or API reference adds and
uses `tl.tanh`, that would be a narrow API allow-list bug rather than a reason
to redesign the grammar.

## Scope Limits

Valid Triton programs can still fall outside Cluster 1's surface. Current
out-of-scope examples include:

- more than three JIT helpers;
- multiple public launchers or non-typed public launchers;
- top-level benchmark/setup code around a kernel;
- arbitrary Python classes, imports, closures, and host utilities;
- `.run(...)` launch style in the task-agnostic surface;
- broad Level 2+ fused-kernel structures that need more helpers, more outputs,
  or looser host-side orchestration.

When reporting results, use these categories:

- `GRAMMAR_BUG`: a real in-scope `tl.*` API or arity used by the corpus is
  missing from the allow-list.
- `HARNESS_CONTRACT_RESTRICTION`: valid Triton/Python code is rejected because
  it does not follow Cluster 1's module, launcher, allocation, grid, launch, or
  return surface.
- `LEGITIMATE_SCOPE_EXCLUSION`: the code uses official Triton features that are
  intentionally outside the current Level 1 evaluation surface.
- `UNSUPPORTED_LEVEL2_FEATURE`: the code requires multi-kernel or fused-kernel
  structure beyond the current Cluster 1 Level 1 scope.

No grammar behavior should change solely to make the harness look more like the
full Triton language. API allow-list fixes are allowed only when the corpus shows
an in-scope `tl.*` coverage gap, and the fix should be the smallest possible
addition.
