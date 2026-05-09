# Cluster 1 Generated Code Surface

## Decision

Cluster 1 uses a function-launcher generated-code surface. It does not use the
KernelBench `Model(torch.nn.Module)` class surface.

The KernelBench `Model` class surface is future adapter work. It must be added
through an explicit KernelBench adapter later, not mixed implicitly into Cluster
1 generation, grammar validation, or compile validation.

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
validator must all agree on this surface. If a candidate source satisfies one
layer but not another, the contract is considered broken until the mismatch is
resolved locally.
