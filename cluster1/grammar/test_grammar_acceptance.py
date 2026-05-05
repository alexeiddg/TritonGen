"""Known-good and known-bad source fixtures for the Cluster 1 grammar."""

from __future__ import annotations


GOOD_KERNELS: dict[str, str] = {
    "vector_add": """\
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)

def add(x, y):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)
    return out
""",
    "relu": """\
import torch
import triton
import triton.language as tl

@triton.jit
def relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "gelu": """\
import torch
import triton
import triton.language as tl

@triton.jit
def gelu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    scale = tl.sqrt(x * x + 1.0)
    out = 0.5 * x * (1.0 + x / scale)
    tl.store(out_ptr + offsets, out, mask=mask)

def gelu(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    gelu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "copy": """\
import torch
import triton
import triton.language as tl

@triton.jit
def copy_kernel(src_ptr, dst_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(src_ptr + offsets, mask=mask)
    tl.store(dst_ptr + offsets, x, mask=mask)

def copy(src):
    dst = torch.empty_like(src)
    n_elements = src.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    copy_kernel[grid](src, dst, n_elements, BLOCK_SIZE)
    return dst
""",
    "axpy": """\
import torch
import triton
import triton.language as tl

@triton.jit
def axpy_kernel(x_ptr, y_ptr, out_ptr, alpha, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    out = alpha * x + y
    tl.store(out_ptr + offsets, out, mask=mask)

def axpy(x, y, alpha):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 512
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    axpy_kernel[grid](x, y, out, alpha, n_elements, BLOCK_SIZE)
    return out
""",
    "softmax": """\
import torch
import triton
import triton.language as tl

@triton.jit
def softmax_kernel(x_ptr, out_ptr, n_cols, BLOCK_SIZE: tl.constexpr):
    row = tl.program_id(axis=0)
    offsets = tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_cols
    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)
    shifted = x - tl.max(x, axis=0)
    numer = tl.exp(shifted)
    denom = tl.sum(numer, axis=0)
    out = numer / denom
    tl.store(out_ptr + row * n_cols + offsets, out, mask=mask)

def softmax(x):
    out = torch.empty_like(x)
    n_cols = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_cols, BLOCK_SIZE),)
    softmax_kernel[grid](x, out, n_cols, BLOCK_SIZE)
    return out
""",
    "sum_reduction": """\
import torch
import triton
import triton.language as tl

@triton.jit
def sum_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    total = tl.sum(x, axis=0)
    tl.store(out_ptr + pid, total)

def reduce_sum(x):
    out = torch.empty((1,), device=x, dtype=x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    sum_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "max_reduction": """\
import torch
import triton
import triton.language as tl

@triton.jit
def max_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=-1000000000.0)
    total = tl.max(x, axis=0)
    tl.store(out_ptr + pid, total)

def reduce_max(x):
    out = torch.empty((1,), device=x, dtype=x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    max_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "tiled_gemm_nested_for": """\
import torch
import triton
import triton.language as tl

@triton.autotune(configs=[triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=3)], key=["M", "N", "K"])
@triton.jit
def matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
    pid_m = tl.program_id(axis=0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.program_id(axis=1) * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for outer in range(0, K, BLOCK_K):
        for k in range(0, K, BLOCK_K):
            offs_k = k + tl.arange(0, BLOCK_K)
            a = tl.load(a_ptr + offs_m[:, None] * K + offs_k[None, :], mask=offs_m[:, None] < M, other=0.0)
            b = tl.load(b_ptr + offs_k[:, None] * N + offs_n[None, :], mask=offs_n[None, :] < N, other=0.0)
            acc += tl.dot(a, b, allow_tf32=True)
    mask = (offs_m < M) & (offs_n < N)
    tl.store(c_ptr + offs_m * N + offs_n, acc, mask=mask)

def matmul(a, b):
    M = a.numel()
    N = b.numel()
    K = b.numel()
    c = torch.empty((M, N), device=a, dtype=a)
    grid = (triton.cdiv(M, 64), triton.cdiv(N, 64))
    matmul_kernel[grid](a, b, c, M, N, K, 64, 64, 32)
    return c
""",
    "atomic_add_reduction": """\
import torch
import triton
import triton.language as tl

@triton.jit
def atomic_sum_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    total = tl.sum(x, axis=0)
    tl.atomic_add(out_ptr, total, mask=True)

def atomic_sum(x):
    out = torch.empty((1,), device=x, dtype=x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    atomic_sum_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
}


BAD_KERNELS: dict[str, str] = {
    "wrong_arity_store": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "missing_program_id": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    offsets = tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "free_form_autotune_config": """\
import torch
import triton
import triton.language as tl

@triton.autotune(configs=[triton.Config({"BLOCK_SIZE": tile}, num_warps=4, num_stages=3)], key=["n_elements"])
@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "launch_missing_grid": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    bad_kernel(x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "markdown_fence": """\
```python
import torch
import triton
import triton.language as tl
```
""",
    "prose_preamble": """\
Here is the Triton kernel:
import torch
import triton
import triton.language as tl
""",
    "missing_jit": """\
import torch
import triton
import triton.language as tl

def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "hallucinated_tl_load2": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load2(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "invalid_program_id_axis": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=7)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "malformed_indentation": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
  offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "constexpr_callable": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    value = tl.constexpr(128)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "helper_call_not_in_grammar": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tmp = helper(x)
    tl.store(out_ptr + offsets, tmp, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "run_launch_empty_arg_before_grid": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel.run(, grid=grid)
    return out
""",
    "kernel_launch_inside_jit": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x_ptr, out_ptr, n_elements, BLOCK_SIZE)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "kernel_return_statement": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)
    return

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "wrapper_call_inside_jit": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    tmp = torch.empty_like(x_ptr)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "tl_call_inside_wrapper": """\
import torch
import triton
import triton.language as tl

@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x, mask=mask)

def bad(x):
    out = torch.empty_like(x)
    tmp = tl.load(out)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
}
