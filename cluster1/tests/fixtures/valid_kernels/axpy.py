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
