import torch
import triton
import triton.language as tl

# Synthetic F2 smoke fixture.
# Archetype: reduction softmax.
# Corruption: stores shifted logits divided by the correct denominator instead
# of exp(shifted) divided by the denominator.
# Expected failure: F2_NUMERIC_LARGE against torch.softmax(x, dim=1).
# Level 0/1 rationale: the launcher signature, @triton.jit surface, row-wise
# indexing, masks, launch grid, and output shape match the known-good softmax
# fixture; only the numerical output expression is corrupted.


@triton.jit
def _softmax_kernel(x_ptr, out_ptr, n_cols: tl.constexpr, BLOCK_SIZE: tl.constexpr):
    row = tl.program_id(axis=0)
    offsets = tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_cols
    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)
    shifted = x - tl.max(x, axis=0)
    numer = tl.exp(shifted)
    denom = tl.sum(numer, axis=0)
    out = shifted / denom
    tl.store(out_ptr + row * n_cols + offsets, out, mask=mask)


def softmax(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_rows = x.shape[0]
    n_cols = x.shape[1]
    BLOCK_SIZE = 512
    grid = (n_rows,)
    _softmax_kernel[grid](x, out, n_cols, BLOCK_SIZE)
    return out
