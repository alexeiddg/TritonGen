"""Text fixture: malformed Triton decorator should remain an F0 boundary case."""

import torch
import triton
import triton.language as tl


@triton.jot
def add_kernel(x_ptr, y_ptr, out_ptr, n_elements: tl.constexpr):
    pid = tl.program_id(0)
    offsets = pid * 1024 + tl.arange(0, 1024)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x, y):
    out = torch.empty_like(x)
    grid = (triton.cdiv(x.numel(), 1024),)
    add_kernel[grid](x, y, out, x.numel())
    return out
