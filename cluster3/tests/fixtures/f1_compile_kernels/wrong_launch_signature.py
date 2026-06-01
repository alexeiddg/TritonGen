"""Text fixture: launcher/kernel signature mismatch boundary smoke case."""

import torch
import triton
import triton.language as tl


@triton.jit
def axpy_kernel(x_ptr, y_ptr, out_ptr, alpha: tl.constexpr, n_elements: tl.constexpr):
    offsets = tl.program_id(0) * 256 + tl.arange(0, 256)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x * alpha + y, mask=mask)


def axpy(x, y, alpha):
    out = torch.empty_like(x)
    grid = (triton.cdiv(x.numel(), 256),)
    axpy_kernel[grid](x, y, out, n_elements=x.numel())
    return out
