import torch
import triton
import triton.language as tl

@triton.jit
def abs_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    # element-wise absolute value
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.abs(x)
    tl.store(out_ptr + offsets, out, mask=mask)

def abs(x):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    abs_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
