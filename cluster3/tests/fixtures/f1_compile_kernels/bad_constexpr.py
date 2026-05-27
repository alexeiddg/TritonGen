"""Text fixture: undefined constexpr name should be classified as F1_COMPILE."""

import torch
import triton
import triton.language as tl


@triton.jit
def scale_kernel(x_ptr, out_ptr, n_elements: tl.constexpr, BLOCK: tl.constexpr):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offsets < n_elements
    scale = MISSING_SCALE_FACTOR + tl.full((BLOCK,), 0.0, tl.float32)
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x * scale, mask=mask)


def scale(x):
    out = torch.empty_like(x)
    block = 128
    grid = (triton.cdiv(x.numel(), block),)
    scale_kernel[grid](x, out, x.numel(), BLOCK=block)
    return out
