"""Text fixture: incompatible pointer arithmetic should be F1_COMPILE."""

import torch
import triton
import triton.language as tl


@triton.jit
def gather_kernel(x_ptr, index_ptr, out_ptr, n_elements: tl.constexpr):
    offsets = tl.program_id(0) * 128 + tl.arange(0, 128)
    mask = offsets < n_elements
    float_offsets = tl.load(index_ptr + offsets, mask=mask, other=0.0).to(tl.float32)
    values = tl.load(x_ptr + float_offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, values, mask=mask)


def gather(x, index):
    out = torch.empty_like(x)
    grid = (triton.cdiv(x.numel(), 128),)
    gather_kernel[grid](x, index, out, x.numel())
    return out
