import torch
import triton
import triton.language as tl

@triton.jit
def scalar_mul_kernel(x_ptr, out_ptr, scalar, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = x * scalar
    tl.store(out_ptr + offsets, out, mask=mask)

def scalar_mul(x, scalar):
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    scalar_mul_kernel[grid](x, out, scalar, n_elements, BLOCK_SIZE)
    return out
