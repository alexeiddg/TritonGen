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
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    copy_kernel[grid](src, dst, n_elements, BLOCK_SIZE)
    return dst
