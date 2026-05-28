import torch
import triton
import triton.language as tl


@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    scale = MISSING_SCALE_FACTOR + tl.full((BLOCK_SIZE,), 0.0, tl.float32)
    y = tl.where(x > 0.0, x, 0.0) * scale
    tl.store(out_ptr + offsets, y, mask=mask)


def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
