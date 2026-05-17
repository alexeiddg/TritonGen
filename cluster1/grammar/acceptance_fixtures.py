"""Known-good and known-bad source fixtures for the Cluster 1 grammar."""

from __future__ import annotations

from pathlib import Path


_GOLDEN_DIR = Path(__file__).parents[1] / "tests" / "fixtures" / "golden"


def _read_golden(name: str) -> str:
    return (_GOLDEN_DIR / name).read_text(encoding="utf-8")


_RELU = _read_golden("generated_relu.py.txt")
_SOFTMAX = _read_golden("generated_softmax.py.txt")
_MATMUL = _read_golden("generated_matmul.py.txt")


GOOD_KERNELS: dict[str, str] = {
    "relu": _RELU,
    "softmax": _SOFTMAX,
    "matmul": _MATMUL,
    "relu_block_size_64": _RELU.replace(
        "    BLOCK_SIZE = 256\n",
        "    BLOCK_SIZE = 64\n",
        1,
    ),
    "relu_wrapper_blank_lines": _RELU.replace(
        "    out = torch.empty_like(x)\n"
        "    n_elements = x.numel()\n"
        "    BLOCK_SIZE = 256\n"
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n"
        "    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)\n"
        "    return out\n",
        "    out = torch.empty_like(x)\n"
        "\n"
        "    n_elements = x.numel()\n"
        "\n"
        "    BLOCK_SIZE = 256\n"
        "\n"
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n"
        "\n"
        "    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)\n"
        "\n"
        "    return out\n",
        1,
    ),
    "relu_where_out_assignment": _RELU.replace(
        "    y = tl.where(x > 0.0, x, 0.0)\n"
        "    tl.store(out_ptr + offsets, y, mask=mask)\n",
        "    out = tl.where(x > 0, x, 0)\n"
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "softmax_block_size_256": _SOFTMAX.replace(
        "    BLOCK_SIZE = 512\n",
        "    BLOCK_SIZE = 256\n",
        1,
    ),
    "matmul_k_from_b_shape": _MATMUL.replace(
        "    K = a.shape[1]\n",
        "    K = b.shape[0]\n",
        1,
    ),
    "relu_autotuned": _RELU.replace(
        "@triton.jit",
        '@triton.autotune(configs=[triton.Config({"BLOCK_SIZE": 256}, num_warps=4, num_stages=3)], key=["n_elements"])\n@triton.jit',
        1,
    ),
    "matmul_autotuned": _MATMUL.replace(
        "@triton.jit",
        '@triton.autotune(configs=[triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32}, num_warps=4, num_stages=2)], key=["M", "N", "K"])\n@triton.jit',
        1,
    ),
}


TASK_AGNOSTIC_GOOD_KERNELS: dict[str, str] = {
    "vector_add": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _vector_add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    out = x + y
    tl.store(out_ptr + offsets, out, mask=mask)

def vector_add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)
    return out
""",
    "sigmoid": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _sigmoid_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    neg_x = -x
    denom = 1.0 + tl.exp(neg_x)
    out = 1.0 / denom
    tl.store(out_ptr + offsets, out, mask=mask)

def sigmoid(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _sigmoid_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "square": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _square_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x * x
    tl.store(out_ptr + offsets, out, mask=mask)

def square(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _square_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "scale_full": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _scale_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    scale = tl.full((BLOCK_SIZE,), 2.0, dtype=tl.float32)
    out = x * scale
    tl.store(out_ptr + offsets, out, mask=mask)

def scale(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _scale_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "log_sqrt": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _log_sqrt_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    safe_x = tl.sqrt(x * x) + 1.0
    out = tl.log(safe_x)
    tl.store(out_ptr + offsets, out, mask=mask)

def log_sqrt(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _log_sqrt_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "kernel_to_cast": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _kernel_to_cast_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x.to(tl.float32)
    tl.store(out_ptr + offsets, out, mask=mask)

def kernel_to_cast(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _kernel_to_cast_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "corpus_primitives": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _corpus_primitives_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    n_programs = tl.num_programs(0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    offsets = tl.max_contiguous(tl.multiple_of(offsets, BLOCK_SIZE), BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    bounded = tl.maximum(tl.minimum(tl.abs(x), 1.0), 0.0)
    work = tl.zeros_like(bounded) + tl.sigmoid(bounded)
    for step in tl.static_range(0, 1, 1):
        work = tl.fma(work, 1.0, 0.0)
    if n_programs >= 1:
        tl.debug_barrier()
    tl.store(out_ptr + offsets, work, mask=mask)

def corpus_primitives(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _corpus_primitives_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "block_pointer_copy": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _block_pointer_copy_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    start = pid * BLOCK_SIZE
    x_block = tl.make_block_ptr(base=x_ptr, shape=(n_elements,), strides=(1,), offsets=(start,), block_shape=(BLOCK_SIZE,), order=(0,))
    out_block = tl.make_block_ptr(base=out_ptr, shape=(n_elements,), strides=(1,), offsets=(start,), block_shape=(BLOCK_SIZE,), order=(0,))
    x = tl.load(x_block, boundary_check=(0,), padding_option="zero")
    tl.store(out_block, x, boundary_check=(0,))

def block_pointer_copy(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _block_pointer_copy_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "reduce_combiner": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _combine_kernel(a, b):
    return a + b

@triton.jit
def _reduce_combiner_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    total = tl.reduce(values, 0, _combine_kernel)
    tl.store(out_ptr + pid, total, mask=True)

def reduce_combiner(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty((1024,), device=x.device, dtype=x.dtype)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _reduce_combiner_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "tuple_reduce_combiner": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _combine_pair_kernel(a_left, b_left, a_right, b_right):
    return (a_left + a_right, b_left + b_right)

@triton.jit
def _tuple_reduce_combiner_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    pair = (values, values)
    totals = tl.reduce(pair, 0, _combine_pair_kernel)
    total = totals[0] + totals[1]
    tl.store(out_ptr + pid, total, mask=True)

def tuple_reduce_combiner(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty((1024,), device=x.device, dtype=x.dtype)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _tuple_reduce_combiner_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "tuple_associative_scan_combiner": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _combine_pair_kernel(a_left, b_left, a_right, b_right):
    return (a_left + a_right, b_left + b_right)

@triton.jit
def _tuple_scan_combiner_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    pair = (values, values)
    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)
    total = totals[0] + totals[1]
    tl.store(out_ptr + offsets, total, mask=mask)

def tuple_associative_scan_combiner(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _tuple_scan_combiner_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "tensor_descriptor_methods": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _tensor_descriptor_copy_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    start = pid * BLOCK_SIZE
    in_desc = tl.make_tensor_descriptor(x_ptr, shape=[n_elements], strides=[1], block_shape=[BLOCK_SIZE])
    out_desc = tl.make_tensor_descriptor(out_ptr, shape=[n_elements], strides=[1], block_shape=[BLOCK_SIZE])
    offsets = [start]
    values = in_desc.load(offsets)
    out_desc.store(offsets, values)

def tensor_descriptor_copy(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _tensor_descriptor_copy_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "heuristic_scale": """\
import torch
import triton
import triton.language as tl

@triton.heuristics(values={"BLOCK_SIZE": lambda args: triton.next_power_of_2(args["n_elements"])})
@triton.jit
def _heuristic_scale_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x * 2.0
    tl.store(out_ptr + offsets, out, mask=mask)

def heuristic_scale(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _heuristic_scale_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "scalar_wrapper_param_torch_dtype": """\
import torch
import triton
import triton.language as tl

@triton.jit
def scale_kernel(x_ptr, out_ptr, n_elements: tl.constexpr, scale, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x * scale
    tl.store(out_ptr + offsets, out, mask=mask)

def scale_with_size(x: torch.Tensor, n_elements: int, scale: float) -> torch.Tensor:
    out = torch.empty((n_elements,), device=x.device, dtype=torch.float32)
    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    scale_kernel[grid](x, out, n_elements, scale, BLOCK_SIZE)
    return out
""",
    "scalar_expression_launch_binding": """\
import torch
import triton
import triton.language as tl

@triton.jit
def scale_expression_kernel(x_ptr, out_ptr, n_elements: tl.constexpr, scale, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x * scale
    tl.store(out_ptr + offsets, out, mask=mask)

def scale_expression(x: torch.Tensor, n_elements: int, scale: float) -> torch.Tensor:
    scale2 = scale * 2.0
    out = torch.empty((n_elements,), device=x.device, dtype=torch.float32)
    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    scale_expression_kernel[grid](x, out, n_elements, scale2, BLOCK_SIZE)
    return out
""",
    "bool_constexpr_launch_binding": """\
import torch
import triton
import triton.language as tl

@triton.jit
def flag_kernel(x_ptr, out_ptr, n_elements, DO_SCALE: tl.constexpr, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    if DO_SCALE:
        out = x * 2.0
    else:
        out = x
    tl.store(out_ptr + offsets, out, mask=mask)

def flag_wrapper(x: torch.Tensor, do_scale: bool) -> torch.Tensor:
    n_elements = x.numel()
    out = torch.empty_like(x)
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    flag_kernel[grid](x, out, n_elements, do_scale, BLOCK_SIZE)
    return out
""",
    "generic_autotune_config": """\
import torch
import triton
import triton.language as tl

@triton.autotune(configs=[triton.Config(kwargs={"BLOCK_SIZE": 2048}, num_warps=8, num_stages=5)], key=["n_elements"])
@triton.jit
def autotuned_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x, mask=mask)

def generic_autotuned_copy(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    autotuned_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "positional_axis_reduction": """\
import torch
import triton
import triton.language as tl

@triton.jit
def reduce_axis_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    total = tl.sum(values, 0, keep_dims=False)
    tl.store(out_ptr + pid, total, mask=True)

def reduce_axis(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty((2048,), device=x.device, dtype=x.dtype)
    n_elements = x.numel()
    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    reduce_axis_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
    "comments_and_multiline_calls": """\
import torch
import triton
import triton.language as tl

@triton.jit
def commented_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    # Long memory calls are often wrapped in tutorials.
    x = tl.load(
        x_ptr + offsets,
        mask=mask,
        other=0.0,
    )
    tl.store(
        out_ptr + offsets,
        x,
        mask=mask,
    )

def commented_copy(x: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    # Keep the allocation readable.
    out = torch.empty(
        (n_elements,),
        device=x.device,
        dtype=torch.float32,
    )
    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    commented_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
""",
}

TASK_AGNOSTIC_GOOD_KERNELS["tensor_descriptor_padding_option"] = TASK_AGNOSTIC_GOOD_KERNELS[
    "tensor_descriptor_methods"
].replace(
    "in_desc = tl.make_tensor_descriptor(x_ptr, shape=[n_elements], strides=[1], block_shape=[BLOCK_SIZE])",
    'in_desc = tl.make_tensor_descriptor(x_ptr, shape=[n_elements], strides=[1], block_shape=[BLOCK_SIZE], padding_option="zero")',
    1,
)


_TASK_AGNOSTIC_VECTOR_ADD = TASK_AGNOSTIC_GOOD_KERNELS["vector_add"]

TASK_AGNOSTIC_GOOD_KERNELS["static_range_output_store"] = _TASK_AGNOSTIC_VECTOR_ADD.replace(
    "    tl.store(out_ptr + offsets, out, mask=mask)\n",
    "    for step in tl.static_range(0, 1, 1):\n"
    "        tl.store(out_ptr + offsets, out, mask=mask)\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["range_keyword_args"] = _TASK_AGNOSTIC_VECTOR_ADD.replace(
    "    out = x + y\n",
    "    work = x\n"
    "    for stage in tl.range(0, arg2=1, step=1, num_stages=3):\n"
    "        work = work + 0.0\n"
    "    for stage in tl.range(0, 1, step=1, num_stages=3):\n"
    "        work = work + 0.0\n"
    "    for stage in tl.range(0, 1, 1, num_stages=3):\n"
    "        work = work + 0.0\n"
    "    for stage in tl.static_range(0, arg2=1, step=1):\n"
    "        work = work + 0.0\n"
    "    for stage in tl.static_range(0, 1, step=1):\n"
    "        work = work + 0.0\n"
    "    out = work + y\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["output_pointer_alias"] = _TASK_AGNOSTIC_VECTOR_ADD.replace(
    "    tl.store(out_ptr + offsets, out, mask=mask)\n",
    "    out_offsets = out_ptr + offsets\n"
    "    tl.store(out_offsets, out, mask=mask)\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["advanced_block_pointer_alias"] = TASK_AGNOSTIC_GOOD_KERNELS[
    "block_pointer_copy"
].replace(
    "    tl.store(out_block, x, boundary_check=(0,))\n",
    "    out_block = tl.advance(out_block, (0,))\n"
    "    tl.store(out_block, x, boundary_check=(0,))\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["if_branch_output_store"] = _TASK_AGNOSTIC_VECTOR_ADD.replace(
    "    tl.store(out_ptr + offsets, out, mask=mask)\n",
    "    if pid >= 0:\n"
    "        tl.store(out_ptr + offsets, out, mask=mask)\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["two_helper_kernels_generic"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def helper_transform(value):
    shifted = value + 1.0
    return shifted

@triton.jit
def generic_copy_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x + 1.0
    tl.store(out_ptr + offsets, out, mask=mask)

def generic_copy(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 128
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    generic_copy_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["two_output_tensors"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def two_output_kernel(x_ptr, out_ptr, aux_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    doubled = x + x
    tl.store(out_ptr + offsets, doubled, mask=mask)
    tl.store(aux_ptr + offsets, x, mask=mask)

def two_output_launcher(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    aux = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    two_output_kernel[grid](x, out, aux, n_elements, BLOCK_SIZE)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["generic_launcher_name"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def apply_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.maximum(x, -1.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def apply_transform(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 512
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    apply_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["non_template_body_shape"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def affine_clip_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    shifted = x * 3.0 - 2.0
    squared = shifted * shifted
    out = tl.minimum(squared, 8.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def affine_clip(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    affine_clip_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["keyword_meta_binding"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def keyword_meta_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x, mask=mask)

def keyword_meta(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    grid = (triton.cdiv(n_elements, 256),)
    keyword_meta_kernel[grid](x, out, n_elements, BLOCK_SIZE=256)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["generated_surfacefix_fp32_literal_arange"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, 256)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(0, x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = (n_elements // 256 + 1, 256)
    _relu_kernel[grid](x, output, n_elements)
    return output
"""

TASK_AGNOSTIC_GOOD_KERNELS["native_assert_statement"] = _TASK_AGNOSTIC_VECTOR_ADD.replace(
    "    out = torch.empty_like(x)\n",
    "    assert x.is_cuda\n"
    "    out = torch.empty_like(x)\n",
    1,
)

TASK_AGNOSTIC_GOOD_KERNELS["generated_surfacefix_fp16_shape_numel"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, 256)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(tl.zeros_like(x), x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    assertx_shape = x.shape
    n_elements = assertx_shape.numel()
    output = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, 256), 1)
    _relu_kernel[grid](x, output, n_elements)
    return output
"""

TASK_AGNOSTIC_GOOD_KERNELS["generic_reduction_control_flow"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def generic_reduce_control_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    acc = tl.zeros((BLOCK_SIZE,), dtype=tl.float32)
    for step in range(0, BLOCK_SIZE, BLOCK_SIZE):
        shifted = values + step
        if step >= 0:
            acc += shifted
        else:
            acc += values
    total = tl.sum(acc, axis=0)
    tl.store(out_ptr + pid, total, mask=True)

def generic_reduce_control(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty((1024,), device=x.device, dtype=x.dtype)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    generic_reduce_control_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

TASK_AGNOSTIC_GOOD_KERNELS["generic_nested_loop_tile_control"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def generic_tile_kernel(a_ptr, b_ptr, c_ptr, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for ko in range(0, K, BLOCK_K):
        for inner in range(0, BLOCK_K, BLOCK_K):
            a_vals = tl.load(a_ptr + offs_m[:, None] * K + ko + inner, mask=offs_m[:, None] < M, other=0.0)
            b_vals = tl.load(b_ptr + (ko + inner) * N + offs_n[None, :], mask=offs_n[None, :] < N, other=0.0)
            acc += a_vals * b_vals
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc, mask=mask)

def generic_tile(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M = a.shape[0]
    N = b.shape[1]
    K = a.shape[1]
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    BLOCK_M = 16
    BLOCK_N = 16
    BLOCK_K = 16
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    generic_tile_kernel[grid](a, b, c, M, N, K, BLOCK_M, BLOCK_N, BLOCK_K)
    return c
"""

TASK_AGNOSTIC_GOOD_KERNELS["multiline_nested_tl_expressions"] = """\
import torch
import triton
import triton.language as tl

@triton.jit
def multiline_nested_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(
        x_ptr + offsets,
        mask=mask,
        other=0.0,
    )
    bounded = tl.maximum(tl.minimum(tl.abs(x), 4.0), tl.sqrt(x * x))
    tl.store(
        out_ptr + offsets,
        bounded,
        mask=mask,
    )

def multiline_nested(x: torch.Tensor) -> torch.Tensor:
    assert x.is_cuda, "input must be a CUDA tensor"
    out = torch.empty(
        (x.numel(),),
        device=x.device,
        dtype=x.dtype,
    )
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    multiline_nested_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""


TASK_AGNOSTIC_BAD_KERNELS: dict[str, str] = {
    "missing_imports": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "import torch\nimport triton\nimport triton.language as tl\n\n",
        "",
        1,
    ),
    "missing_jit_helper": _TASK_AGNOSTIC_VECTOR_ADD.replace("@triton.jit\n", "", 1),
    "range_duplicate_arg2_keyword": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    work = x\n"
        "    for stage in tl.range(0, 1, arg2=2):\n"
        "        work = work + 0.0\n"
        "    out = work + y\n",
        1,
    ),
    "range_duplicate_step_keyword": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    work = x\n"
        "    for stage in tl.range(0, 1, 1, step=2):\n"
        "        work = work + 0.0\n"
        "    out = work + y\n",
        1,
    ),
    "static_range_duplicate_arg2_keyword": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    work = x\n"
        "    for stage in tl.static_range(0, 1, arg2=2):\n"
        "        work = work + 0.0\n"
        "    out = work + y\n",
        1,
    ),
    "static_range_duplicate_step_keyword": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    work = x\n"
        "    for stage in tl.static_range(0, 1, 1, step=2):\n"
        "        work = work + 0.0\n"
        "    out = work + y\n",
        1,
    ),
    "missing_public_launcher": _TASK_AGNOSTIC_VECTOR_ADD.split(
        "\ndef vector_add",
        maxsplit=1,
    )[0]
    + "\n",
    "repeated_helper_only_module": """\
import torch
import triton
import triton.language as tl

@triton.jit
def repeated_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

@triton.jit
def repeated_kernel_two(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

@triton.jit
def repeated_kernel_three(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements

@triton.jit
def repeated_kernel_four(x_ptr
""",
    "truncated_public_wrapper_signature": _TASK_AGNOSTIC_VECTOR_ADD.split(
        "\ndef vector_add",
        maxsplit=1,
    )[0]
    + "\n\ndef vector_add(x: torch.Tensor",
    "eof_inside_string": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        '    assert x.is_cuda, "unterminated\n',
        1,
    ),
    "eof_inside_parens": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE)\n",
        1,
    ),
    "missing_bracket_launch": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel(x, y, out, n_elements, BLOCK_SIZE)",
        1,
    ),
    "top_level_solution_comment_drift": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "\n@triton.jit\n",
        "\n# BEGIN SOLUTION\n@triton.jit\n",
        1,
    ),
    "undefined_block_size_meta_reference": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        ", BLOCK_SIZE: tl.constexpr",
        "",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, y, out, n_elements)",
        1,
    ),
    "malformed_ifdevice_type": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    device_type = 'cuda' | 'cpu'\n"
        "    ifdevice_type = 'cuda' | 'cpu'\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "broken_string_or_operations": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        '    device_type = "cuda" | "cpu"\n'
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "unclosed_parens": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE)\n",
        1,
    ),
    "missing_matrix_launcher": """\
import torch
import triton
import triton.language as tl

@triton.jit
def generic_tile_kernel(a_ptr, b_ptr, c_ptr, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc, mask=mask)
""",
    "malformed_wrapper_augassign_assert": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    assert /= n_elements == n_elements\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "malformed_bracket_launch_assignment": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)\n",
        "    _vector_add_kernel[grid] = (x, y, out, n_elements, BLOCK_SIZE)\n",
        1,
    ),
    "generated_n1_fp32_undefined_block_size": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(0.0, x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, 64), 1)
    _relu_kernel[grid](x, output, n_elements)
    return output
""",
    "generated_n1_fp16_assert_div_assignment": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(tl.zeros_like(x), x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    assert /= torch.is_floating_point_dtype // (x.dtype == torch.float16)
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = lambda_metafunc_n_elements // BLOCK_SIZE
    _relu_kernel[grid](x, output, n_elements)
    return output
""",
    "generated_n1_bf16_assert_div_assignment": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(tl.zeros_like(x), x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    assert /= torch.bfloat16
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, 64), 1)
    _relu_kernel[grid](x, output, n_elements)
    return output
""",
    "generated_surfacefix_fp16_assert_assignment": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, 256)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(tl.zeros_like(x), x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    assert = x.dtype == torch.float16
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, 256), 1)
    _relu_kernel[grid](x, output, n_elements)
    return output
""",
    "generated_surfacefix_bf16_assert_assignment": """\
import torch
import triton
import triton.language as tl

@triton.jit
def _relu_kernel(x_ptr: tl.tensor, out_ptr: tl.tensor, n_elements: int):
    pid = tl.program_id(axis=0)
    block_size = tl.program_id(axis=1)
    offsets = pid * block_size + tl.arange(0, 256)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    out = tl.maximum(tl.zeros_like(x), x)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    assert = x.dtype == torch.bfloat16
    n_elements = x.numel()
    output = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, 256), 1)
    _relu_kernel[grid](x, output, n_elements)
    return output
""",
    "launch_wrong_arity": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, out)",
        1,
    ),
    "launch_returned_output_wrong_slot": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](out, x, y, n_elements, BLOCK_SIZE)",
        1,
    ),
    "launch_string_meta_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        '    tmp = "bad"\n'
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, y, out, n_elements, tmp)",
        1,
    ),
    "launch_none_dimension_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = None\n"
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, y, out, tmp, BLOCK_SIZE)",
        1,
    ),
    "launch_list_pointer_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = []\n"
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](tmp, y, out, n_elements, BLOCK_SIZE)",
        1,
    ),
    "launch_int_pointer_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = 1\n"
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](tmp, y, out, n_elements, BLOCK_SIZE)",
        1,
    ),
    "launch_bool_dimension_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = True\n"
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, y, out, tmp, BLOCK_SIZE)",
        1,
    ),
    "launch_float_meta_binding": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = 1.0\n"
        "    out = torch.empty_like(x)\n",
        1,
    ).replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x, y, out, n_elements, tmp)",
        1,
    ),
    "launch_float_shape_binding": """\
import torch
import triton
import triton.language as tl

@triton.jit
def shape_kernel(x_ptr, out_ptr, n_elements, WIDTH: tl.constexpr, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    pad = tl.zeros((WIDTH,), dtype=tl.float32)
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = x + pad[0]
    tl.store(out_ptr + offsets, out, mask=mask)

def shape_wrapper(x: torch.Tensor, width: float) -> torch.Tensor:
    n_elements = x.numel()
    out = torch.empty_like(x)
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    shape_kernel[grid](x, out, n_elements, width, BLOCK_SIZE)
    return out
""",
    "returned_output_rebound_after_launch": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)\n"
        "    return out\n",
        "    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)\n"
        "    out = torch.empty_like(x)\n"
        "    return out\n",
        1,
    ),
    "assigns_void_store_call": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    tmp = tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "assigns_void_debug_call": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    tmp = tl.debug_barrier()\n"
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "store_target_invalid_pointer_arithmetic": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    tl.store(out_ptr * 0, out, mask=mask)\n",
        1,
    ),
    "store_target_invalid_pointer_alias": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    bad_ptr = out_ptr * 0\n"
        "    tl.store(bad_ptr, out, mask=mask)\n",
        1,
    ),
    "store_target_invalid_augassign_alias": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    bad_ptr = out_ptr\n"
        "    bad_ptr *= 0\n"
        "    tl.store(bad_ptr, out, mask=mask)\n",
        1,
    ),
    "store_target_invalid_nested_pointer_expr": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    tl.store(out_ptr + -out_ptr, out, mask=mask)\n",
        1,
    ),
    "store_target_rebound_inside_if": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    if pid >= 0:\n"
        "        out_ptr = x_ptr\n"
        "        tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "store_target_branch_local_only": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    if pid == 0:\n"
        "        out_ptr = x_ptr\n"
        "        tl.store(out_ptr + offsets, out, mask=mask)\n"
        "    else:\n"
        "        tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "kernel_undefined_assignment_name": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    out = missing + y\n",
        1,
    ),
    "kernel_undefined_mask_name": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    mask = offsets < n_elements\n",
        "    mask = missing < n_elements\n",
        1,
    ),
    "kernel_helper_name_as_value": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    out = _vector_add_kernel\n",
        1,
    ),
    "kernel_module_name_as_value": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    out = tl\n",
        1,
    ),
    "kernel_dtype_name_as_value": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    out = tl.float32\n",
        1,
    ),
    "markdown_fence": "```python\n" + _TASK_AGNOSTIC_VECTOR_ADD + "```\n",
    "prose_preamble": "Here is a Triton kernel:\n" + _TASK_AGNOSTIC_VECTOR_ADD,
    "arbitrary_unknown_tl_api": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "out = x + y",
        "out = tl.add2(x, y)",
        1,
    ),
    "malformed_grid": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "grid = (triton.cdiv(n_elements, BLOCK_SIZE),)",
        "grid = ()",
        1,
    ),
    "wrapper_tensor_to_tl_dtype": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = x.to(tl.float32)\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_tl_attribute_reference": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = tl.float32\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_arbitrary_tensor_attribute": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = x.foo\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_arbitrary_triton_attribute": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    BLOCK_SIZE = 256\n",
        "    BLOCK_SIZE = triton.foo\n",
        1,
    ),
    "wrapper_shape_dynamic_subscript": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = x.shape[y]\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_device_subscript": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = x.device[0]\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_torch_dtype_subscript": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = torch.float32[0]\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "wrapper_undefined_augassign": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp += 1\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "kernel_rebinds_tl": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    tl = x\n"
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        1,
    ),
    "wrapper_rebinds_helper": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)\n",
        "    _vector_add_kernel = x\n"
        "    _vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)\n",
        1,
    ),
    "unsafe_module_assignment": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "\n@triton.jit\n",
        "\nunsafe = 1\n\n@triton.jit\n",
        1,
    ),
    "helper_shadows_torch": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "_vector_add_kernel",
        "torch",
    ),
    "launched_helper_return": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    tl.store(out_ptr + offsets, out, mask=mask)\n",
        "    return out\n",
        1,
    ),
    "descriptor_method_on_tensor": _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "    out = x + y\n",
        "    out = x.load(offsets)\n",
        1,
    ),
    "descriptor_method_after_rebind": TASK_AGNOSTIC_GOOD_KERNELS[
        "tensor_descriptor_methods"
    ].replace(
        "    values = in_desc.load(offsets)\n",
        "    in_desc = tl.load(x_ptr + start, mask=True, other=0.0)\n"
        "    values = in_desc.load(offsets)\n",
        1,
    ),
    "descriptor_method_after_branch_rebind": TASK_AGNOSTIC_GOOD_KERNELS[
        "tensor_descriptor_methods"
    ].replace(
        "    values = in_desc.load(offsets)\n",
        "    if start >= 0:\n"
        "        in_desc = tl.load(x_ptr + start, mask=True, other=0.0)\n"
        "    values = in_desc.load(offsets)\n",
        1,
    ),
    "reduce_uses_launched_helper_as_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "reduce_combiner"
    ].replace(
        "    total = tl.reduce(values, 0, _combine_kernel)\n",
        "    total = tl.reduce(values, 0, _reduce_combiner_kernel)\n",
        1,
    ),
    "reduce_combiner_wrong_arity": TASK_AGNOSTIC_GOOD_KERNELS[
        "reduce_combiner"
    ].replace(
        "def _combine_kernel(a, b):\n    return a + b\n",
        "def _combine_kernel(a):\n    return a\n",
        1,
    ),
    "reduce_combiner_odd_arity": TASK_AGNOSTIC_GOOD_KERNELS[
        "reduce_combiner"
    ].replace(
        "def _combine_kernel(a, b):\n    return a + b\n",
        "def _combine_kernel(a, b, c):\n    return a + b\n",
        1,
    ),
    "reduce_tuple_combiner_wrong_arity": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n",
        "def _combine_pair_kernel(a_left, b_left):\n    return a_left + b_left\n",
        1,
    ),
    "reduce_tuple_combiner_branch_rebind_wrong_arity": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n",
        "def _combine_pair_kernel(a_left, b_left):\n    return a_left + b_left\n",
        1,
    ).replace(
        "    pair = (values, values)\n"
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    pair = (values, values)\n"
        "    if pid >= 0:\n"
        "        pair = values\n"
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = totals\n",
        1,
    ),
    "reduce_tuple_combiner_scalar_return": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n",
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return a_left + a_right\n",
        1,
    ),
    "reduce_tuple_combiner_fallthrough_return": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n",
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    if a_left >= 0:\n        return (a_left + a_right, b_left + b_right)\n",
        1,
    ),
    "reduce_tuple_result_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = tl.reduce(totals, 0, _combine_scalar_kernel)\n",
        1,
    ),
    "reduce_nested_tuple_result_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    total = tl.reduce(tl.reduce(pair, 0, _combine_pair_kernel), 0, _combine_scalar_kernel)\n",
        1,
    ),
    "reduce_tuple_result_self_reduction_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_reduce_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    totals = tl.reduce(pair, 0, _combine_pair_kernel)\n"
        "    totals = tl.reduce(totals, 0, _combine_pair_kernel)\n"
        "    total = tl.reduce(totals, 0, _combine_scalar_kernel)\n",
        1,
    ),
    "associative_scan_tuple_combiner_scalar_return": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_associative_scan_combiner"
    ].replace(
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n",
        "def _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return a_left + a_right\n",
        1,
    ),
    "associative_scan_tuple_result_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_associative_scan_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)\n"
        "    total = tl.associative_scan(totals, 0, _combine_scalar_kernel)\n",
        1,
    ),
    "associative_scan_nested_tuple_result_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_associative_scan_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    total = tl.associative_scan(tl.associative_scan(pair, 0, _combine_pair_kernel), 0, _combine_scalar_kernel)\n",
        1,
    ),
    "associative_scan_tuple_result_self_scan_scalar_combiner": TASK_AGNOSTIC_GOOD_KERNELS[
        "tuple_associative_scan_combiner"
    ].replace(
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n",
        "@triton.jit\ndef _combine_pair_kernel(a_left, b_left, a_right, b_right):\n    return (a_left + a_right, b_left + b_right)\n\n@triton.jit\ndef _combine_scalar_kernel(a, b):\n    return a + b\n\n",
        1,
    ).replace(
        "    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)\n"
        "    total = totals[0] + totals[1]\n",
        "    totals = tl.associative_scan(pair, 0, _combine_pair_kernel)\n"
        "    totals = tl.associative_scan(totals, 0, _combine_pair_kernel)\n"
        "    total = tl.associative_scan(totals, 0, _combine_scalar_kernel)\n",
        1,
    ),
}


# Audit metadata for task-agnostic parser/semantic disagreements.
#
# KEEP_SURFACE_CHECK entries are intentionally rejected before compile_check
# because they are malformed generated-code surface, unknown API, or unsafe
# module structure. DELETE_OR_RELAX_COMPILE_CATCHABLE entries are grammar-valid
# Triton-like programs whose failures belong to the real Triton compile/runtime
# gate, not the task-agnostic semantic validator.
TASK_AGNOSTIC_COMPILE_CATCHABLE_REJECTION_REASONS: dict[str, str] = {
    "launch_returned_output_wrong_slot": "DELETE_OR_RELAX_COMPILE_CATCHABLE: output argument position is a convention.",
    "launch_string_meta_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: meta-parameter value type is compile/runtime-owned.",
    "launch_none_dimension_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: dimension value type is compile/runtime-owned.",
    "launch_list_pointer_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: pointer argument role inference is compile/runtime-owned.",
    "launch_int_pointer_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: pointer argument role inference is compile/runtime-owned.",
    "launch_bool_dimension_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: dimension value type is compile/runtime-owned.",
    "launch_float_meta_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: meta-parameter value type is compile/runtime-owned.",
    "launch_float_shape_binding": "DELETE_OR_RELAX_COMPILE_CATCHABLE: symbolic shape/value compatibility is compile-owned.",
    "store_target_invalid_pointer_arithmetic": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store target pointer semantics are compile-owned.",
    "store_target_invalid_pointer_alias": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store aliasing is compile-owned.",
    "store_target_invalid_augassign_alias": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store aliasing is compile-owned.",
    "store_target_invalid_nested_pointer_expr": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store aliasing is compile-owned.",
    "store_target_rebound_inside_if": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store aliasing across branches is compile-owned.",
    "store_target_branch_local_only": "DELETE_OR_RELAX_COMPILE_CATCHABLE: store aliasing across branches is compile-owned.",
    "kernel_undefined_assignment_name": "DELETE_OR_RELAX_COMPILE_CATCHABLE: kernel name resolution is caught during JIT compile.",
    "kernel_undefined_mask_name": "DELETE_OR_RELAX_COMPILE_CATCHABLE: kernel name resolution is caught during JIT compile.",
    "kernel_helper_name_as_value": "DELETE_OR_RELAX_COMPILE_CATCHABLE: helper-as-value semantics are compile-owned.",
    "kernel_module_name_as_value": "DELETE_OR_RELAX_COMPILE_CATCHABLE: module-as-value semantics are compile-owned.",
    "kernel_dtype_name_as_value": "DELETE_OR_RELAX_COMPILE_CATCHABLE: dtype value semantics are compile-owned.",
    "launched_helper_return": "DELETE_OR_RELAX_COMPILE_CATCHABLE: launched-kernel return semantics are compile-owned.",
    "data_ptr_method_object_arguments": "DELETE_OR_RELAX_COMPILE_CATCHABLE: tensor .data_ptr method-object arguments reach the Triton launch.",
    "descriptor_method_on_tensor": "DELETE_OR_RELAX_COMPILE_CATCHABLE: descriptor receiver semantics are compile-owned.",
    "descriptor_method_after_rebind": "DELETE_OR_RELAX_COMPILE_CATCHABLE: descriptor rebind semantics are compile-owned.",
    "descriptor_method_after_branch_rebind": "DELETE_OR_RELAX_COMPILE_CATCHABLE: descriptor branch rebind semantics are compile-owned.",
    "reduce_uses_launched_helper_as_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: combiner function validity is compile-owned.",
    "reduce_combiner_wrong_arity": "DELETE_OR_RELAX_COMPILE_CATCHABLE: combiner arity is compile-owned.",
    "reduce_combiner_odd_arity": "DELETE_OR_RELAX_COMPILE_CATCHABLE: combiner arity is compile-owned.",
    "reduce_tuple_combiner_wrong_arity": "DELETE_OR_RELAX_COMPILE_CATCHABLE: tuple combiner arity is compile-owned.",
    "reduce_tuple_combiner_branch_rebind_wrong_arity": "DELETE_OR_RELAX_COMPILE_CATCHABLE: tuple combiner arity is compile-owned.",
    "reduce_tuple_combiner_scalar_return": "DELETE_OR_RELAX_COMPILE_CATCHABLE: combiner return arity is compile-owned.",
    "reduce_tuple_combiner_fallthrough_return": "DELETE_OR_RELAX_COMPILE_CATCHABLE: combiner return coverage is compile-owned.",
    "reduce_tuple_result_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: reduction result arity is compile-owned.",
    "reduce_nested_tuple_result_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: nested reduction result arity is compile-owned.",
    "reduce_tuple_result_self_reduction_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: nested reduction result arity is compile-owned.",
    "associative_scan_tuple_combiner_scalar_return": "DELETE_OR_RELAX_COMPILE_CATCHABLE: scan combiner return arity is compile-owned.",
    "associative_scan_tuple_result_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: scan result arity is compile-owned.",
    "associative_scan_nested_tuple_result_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: nested scan result arity is compile-owned.",
    "associative_scan_tuple_result_self_scan_scalar_combiner": "DELETE_OR_RELAX_COMPILE_CATCHABLE: nested scan result arity is compile-owned.",
}

TASK_AGNOSTIC_BAD_KERNELS["data_ptr_method_object_arguments"] = (
    _TASK_AGNOSTIC_VECTOR_ADD.replace(
        "_vector_add_kernel[grid](x, y, out, n_elements, BLOCK_SIZE)",
        "_vector_add_kernel[grid](x.data_ptr, y.data_ptr, out.data_ptr, n_elements, BLOCK_SIZE)",
        1,
    )
)

TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS: dict[str, str] = {
    name: TASK_AGNOSTIC_BAD_KERNELS.pop(name)
    for name in TASK_AGNOSTIC_COMPILE_CATCHABLE_REJECTION_REASONS
}

TASK_AGNOSTIC_GENERATED_N5_DISAGREEMENT_REASONS: dict[tuple[str, int], str] = {
    ("fp32", 1): "DELETE_OR_RELAX_COMPILE_CATCHABLE: .data_ptr method-object arguments reach the Triton launch and are compile_check-owned.",
    ("fp32", 2): "KEEP_SURFACE_CHECK: wrapper grid references undefined BLOCK_SIZE before stable launch.",
    ("fp32", 4): "DELETE_OR_RELAX_COMPILE_CATCHABLE: .data_ptr method-object arguments reach the Triton launch and are compile_check-owned.",
    ("fp16", 4): "KEEP_SURFACE_CHECK: wrapper grid and launch arguments reference undefined BLOCK_SIZE before stable launch.",
    ("bf16", 2): "KEEP_SURFACE_CHECK: helper references BLOCK_SIZE without a constexpr parameter or launcher binding.",
}

TASK_AGNOSTIC_SURFACE_REJECTION_REASONS: dict[str, str] = {
    "missing_imports": "KEEP_SURFACE_CHECK: required imports are the generated module boundary.",
    "missing_jit_helper": "KEEP_SURFACE_CHECK: a Triton helper must be present and decorated.",
    "missing_public_launcher": "KEEP_SURFACE_CHECK: public launcher is required to reach compile_check.",
    "repeated_helper_only_module": "KEEP_SURFACE_CHECK: repeated helpers without a public launcher are incomplete module surface.",
    "truncated_public_wrapper_signature": "KEEP_SURFACE_CHECK: EOF inside a public launcher signature is incomplete Python module surface.",
    "eof_inside_string": "KEEP_SURFACE_CHECK: EOF inside a string literal is incomplete Python module surface.",
    "eof_inside_parens": "KEEP_SURFACE_CHECK: EOF inside parentheses is incomplete Python module surface.",
    "missing_bracket_launch": "KEEP_SURFACE_CHECK: bracket launch is the task-agnostic launcher surface.",
    "top_level_solution_comment_drift": "KEEP_SURFACE_CHECK: top-level solution comments can consume the module before the launcher.",
    "undefined_block_size_meta_reference": "KEEP_SURFACE_CHECK: BLOCK_* kernel references must be constexpr helper parameters.",
    "malformed_ifdevice_type": "KEEP_SURFACE_CHECK: malformed wrapper pseudo-if string-or assignment is not stable Python launcher surface.",
    "broken_string_or_operations": "KEEP_SURFACE_CHECK: string bitwise-or expressions in the launcher are malformed generated surface.",
    "unclosed_parens": "KEEP_SURFACE_CHECK: unbalanced parentheses must be rejected before compile_check.",
    "missing_matrix_launcher": "KEEP_SURFACE_CHECK: a matrix-style helper without a public launcher cannot reach compile_check.",
    "malformed_wrapper_augassign_assert": "KEEP_SURFACE_CHECK: invalid assert augmented-assignment syntax is malformed Python.",
    "malformed_bracket_launch_assignment": "KEEP_SURFACE_CHECK: bracket launch must be a call expression, not an assignment target.",
    "generated_n1_fp32_undefined_block_size": "KEEP_SURFACE_CHECK: generated smoke source used BLOCK_SIZE without a helper parameter or launcher binding.",
    "generated_n1_fp16_assert_div_assignment": "KEEP_SURFACE_CHECK: generated smoke source used invalid assert update syntax.",
    "generated_n1_bf16_assert_div_assignment": "KEEP_SURFACE_CHECK: generated smoke source used invalid assert update syntax.",
    "generated_surfacefix_fp16_assert_assignment": "KEEP_SURFACE_CHECK: generated smoke source used invalid assert assignment syntax.",
    "generated_surfacefix_bf16_assert_assignment": "KEEP_SURFACE_CHECK: generated smoke source used invalid assert assignment syntax.",
    "launch_wrong_arity": "KEEP_SURFACE_CHECK: launched BLOCK_* meta parameters must be bound at the launcher call.",
    "assigns_void_store_call": "KEEP_SURFACE_CHECK: statement-only tl.store used as a value is malformed surface.",
    "assigns_void_debug_call": "KEEP_SURFACE_CHECK: statement-only tl.debug_barrier used as a value is malformed surface.",
    "markdown_fence": "KEEP_SURFACE_CHECK: markdown fences are not Python module source.",
    "prose_preamble": "KEEP_SURFACE_CHECK: prose is not Python module source.",
    "arbitrary_unknown_tl_api": "KEEP_SURFACE_CHECK: task_agnostic still rejects unknown tl.* APIs.",
    "malformed_grid": "KEEP_SURFACE_CHECK: launcher grid must be a non-empty generated-code grid tuple.",
    "wrapper_tensor_to_tl_dtype": "KEEP_SURFACE_CHECK: wrapper must not use tl dtype operations.",
    "wrapper_tl_attribute_reference": "KEEP_SURFACE_CHECK: wrapper must not reference tl attributes.",
    "wrapper_arbitrary_tensor_attribute": "KEEP_SURFACE_CHECK: arbitrary tensor attributes are outside launcher surface.",
    "wrapper_arbitrary_triton_attribute": "KEEP_SURFACE_CHECK: arbitrary triton attributes are outside launcher surface.",
    "wrapper_shape_dynamic_subscript": "KEEP_SURFACE_CHECK: dynamic shape indexing is outside launcher surface.",
    "wrapper_device_subscript": "KEEP_SURFACE_CHECK: device subscripting is malformed launcher surface.",
    "wrapper_torch_dtype_subscript": "KEEP_SURFACE_CHECK: dtype subscripting is malformed launcher surface.",
    "wrapper_undefined_augassign": "KEEP_SURFACE_CHECK: wrapper name errors may prevent reaching a kernel launch.",
    "kernel_rebinds_tl": "KEEP_SURFACE_CHECK: rebinding imported module aliases breaks generated-code surface.",
    "wrapper_rebinds_helper": "KEEP_SURFACE_CHECK: rebinding helper names breaks the launcher surface.",
    "unsafe_module_assignment": "KEEP_SURFACE_CHECK: module-level executable assignments are unsafe surface.",
    "helper_shadows_torch": "KEEP_SURFACE_CHECK: helper names must not shadow imported modules.",
    "returned_output_rebound_after_launch": "KEEP_SURFACE_CHECK: public launcher must preserve launch-to-return structure.",
}


BAD_KERNELS: dict[str, str] = {
    "markdown_fence": "```python\n" + _RELU + "\n```\n",
    "prose_preamble": "Here is the Triton kernel:\n" + _RELU,
    "missing_public_launcher": _RELU.split("\ndef relu", maxsplit=1)[0] + "\n",
    "wrong_launcher_signature": _RELU.replace(
        "def relu(x: torch.Tensor) -> torch.Tensor:",
        "def relu(x, y):",
        1,
    ),
    "missing_return_annotation": _RELU.replace(
        "def relu(x: torch.Tensor) -> torch.Tensor:",
        "def relu(x: torch.Tensor):",
        1,
    ),
    "missing_imports": _RELU.replace(
        "import torch\nimport triton\nimport triton.language as tl\n\n",
        "",
        1,
    ),
    "imports_out_of_order": _RELU.replace(
        "import torch\nimport triton\nimport triton.language as tl",
        "import triton\nimport torch\nimport triton.language as tl",
        1,
    ),
    "model_class_only": """\
import torch
import triton
import triton.language as tl

class Model(torch.nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(x)
""",
    "wrong_public_launcher_name": _MATMUL.replace(
        "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:",
        "def gemm(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:",
        1,
    ),
    "non_private_helper": _RELU.replace("_relu_kernel", "relu_kernel"),
    "relu_helper_missing_args": _RELU.replace(
        "def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):",
        "def _relu_kernel(x_ptr):",
        1,
    ),
    "relu_helper_missing_constexpr": _RELU.replace(
        "def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):",
        "def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE):",
        1,
    ),
    "relu_helper_wrong_output_name": _RELU.replace(
        "def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):",
        "def _relu_kernel(x_ptr, y_ptr, n_elements, BLOCK_SIZE: tl.constexpr):",
        1,
    ),
    "softmax_helper_missing_args": _SOFTMAX.replace(
        "def _softmax_kernel(x_ptr, out_ptr, n_cols: tl.constexpr, BLOCK_SIZE: tl.constexpr):",
        "def _softmax_kernel(x_ptr):",
        1,
    ),
    "softmax_helper_missing_constexpr": _SOFTMAX.replace(
        "def _softmax_kernel(x_ptr, out_ptr, n_cols: tl.constexpr, BLOCK_SIZE: tl.constexpr):",
        "def _softmax_kernel(x_ptr, out_ptr, n_cols, BLOCK_SIZE: tl.constexpr):",
        1,
    ),
    "softmax_duplicate_mask_keyword": _SOFTMAX.replace(
        "    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)\n",
        "    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, mask=True)\n",
        1,
    ),
    "softmax_uses_undefined_n_rows_in_kernel": _SOFTMAX.replace(
        "    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)\n",
        "    x = tl.load(x_ptr + row * n_cols + offsets, mask=row < n_rows, other=-1000000000.0)\n",
        1,
    ),
    "softmax_python_min_subscript": _SOFTMAX.replace(
        "    offsets = tl.arange(0, BLOCK_SIZE)\n"
        "    mask = offsets < n_cols\n",
        "    col_start = row * BLOCK_SIZE\n"
        "    col_end = min[col_start + BLOCK_SIZE, n_cols]\n",
        1,
    ),
    "softmax_pointer_slice_assignment": _SOFTMAX.replace(
        "    x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)\n"
        "    shifted = x - tl.max(x, axis=0)\n"
        "    numer = tl.exp(shifted)\n"
        "    denom = tl.sum(numer, axis=0)\n"
        "    out = numer / denom\n"
        "    tl.store(out_ptr + row * n_cols + offsets, out, mask=mask)\n",
        "    x_row = x_ptr[row * n_cols:row * n_cols + BLOCK_SIZE]\n"
        "    max_val = tl.max(x_row, axis=0)\n"
        "    out_row = tl.exp(x_row - max_val)\n"
        "    out_ptr[row * n_cols:row * n_cols + BLOCK_SIZE] = out_row\n",
        1,
    ),
    "softmax_negative_tensor_index_mask": _SOFTMAX.replace(
        "mask=mask, other=-1000000000.0",
        "mask=offsets < (n_cols * offsets[-1]), other=-1000000000.0",
        1,
    ).replace(
        "mask=mask)",
        "mask=offsets < (n_cols * offsets[-1]))",
        1,
    ),
    "softmax_missing_store": _SOFTMAX.replace(
        "    tl.store(out_ptr + row * n_cols + offsets, out, mask=mask)\n",
        "",
        1,
    ),
    "matmul_helper_missing_args": _MATMUL.replace(
        "def _matmul_kernel(a_ptr, b_ptr, c_ptr, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):",
        "def _matmul_kernel(a_ptr):",
        1,
    ),
    "matmul_helper_wrong_ptr_name": _MATMUL.replace(
        "def _matmul_kernel(a_ptr, b_ptr, c_ptr, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):",
        "def _matmul_kernel(a_ptr, b_ptr, out_ptr, M: tl.constexpr, N: tl.constexpr, K: tl.constexpr, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):",
        1,
    ),
    "matmul_program_id_tuple_subscript": _MATMUL.replace(
        "    pid_m = tl.program_id(axis=0)\n"
        "    pid_n = tl.program_id(axis=1)\n"
        "    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
        "    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n",
        "    pid = tl.program_id(0)\n"
        "    i = pid[0] * BLOCK_M + tl.arange(0, BLOCK_M)\n"
        "    j = pid[1] * BLOCK_N + tl.arange(0, BLOCK_N)\n",
        1,
    ),
    "matmul_missing_store": _MATMUL.replace(
        "    tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc, mask=mask)\n",
        "",
        1,
    ),
    "wrong_arity_store": _RELU.replace(
        "tl.store(out_ptr + offsets, y, mask=mask)",
        "tl.store(out_ptr + offsets, mask=mask)",
        1,
    ),
    "missing_program_id": _RELU.replace(
        "    pid = tl.program_id(axis=0)\n",
        "",
        1,
    ),
    "hallucinated_tl_load2": _RELU.replace(
        "tl.load(x_ptr + offsets, mask=mask, other=0.0)",
        "tl.load2(x_ptr + offsets, mask=mask, other=0.0)",
        1,
    ),
    "tl_attribute_value": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.maximum_zeroed_out",
        1,
    ),
    "relu_tl_max_scalar_axis": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.max(0, axis=0)",
        1,
    ),
    "relu_tl_max_x_axis": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.max(x, axis=0)",
        1,
    ),
    "relu_tl_sum_x_axis": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.sum(x, axis=0)",
        1,
    ),
    "relu_tl_dot_x_x": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.dot(x, x)",
        1,
    ),
    "relu_tl_atomic_add": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.atomic_add(out_ptr + offsets, x, mask=mask)",
        1,
    ),
    "relu_tl_exp_x": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.exp(x)",
        1,
    ),
    "relu_tl_log_x": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.log(x)",
        1,
    ),
    "relu_tl_sqrt_x": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.sqrt(x)",
        1,
    ),
    "relu_bare_x_compute": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "x",
        1,
    ),
    "relu_x_plus_one_compute": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "x + 1",
        1,
    ),
    "relu_x_times_x_compute": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "x * x",
        1,
    ),
    "relu_scalar_zero_compute": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "0.0",
        1,
    ),
    "relu_boolean_compute": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "x > 0.0",
        1,
    ),
    "relu_arbitrary_tl_call": _RELU.replace(
        "tl.where(x > 0.0, x, 0.0)",
        "tl.arbitrary_attribute(x)",
        1,
    ),
    "invalid_program_id_axis": _RELU.replace(
        "tl.program_id(axis=0)",
        "tl.program_id(axis=7)",
        1,
    ),
    "launch_missing_grid": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel(x, out, n_elements, BLOCK_SIZE)",
        1,
    ),
    "run_launch_only": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel.run(x, out, n_elements, BLOCK_SIZE, grid=grid)",
        1,
    ),
    "kernel_return_statement": _RELU.replace(
        "    tl.store(out_ptr + offsets, y, mask=mask)\n",
        "    tl.store(out_ptr + offsets, y, mask=mask)\n    return\n",
        1,
    ),
    "tl_call_inside_wrapper": _RELU.replace(
        "    n_elements = x.numel()\n",
        "    tmp = tl.load(out)\n    n_elements = x.numel()\n",
        1,
    ),
    "undefined_name_in_wrapper_prelude": _RELU.replace(
        "    n_elements = x.numel()\n",
        "    n_elements = foo\n",
        1,
    ),
    "relu_missing_dimension_extraction": _RELU.replace(
        "    n_elements = x.numel()\n",
        "",
        1,
    ),
    "relu_wrong_dimension_binding_type": _RELU.replace(
        "    n_elements = x.numel()\n",
        "    n_elements = x\n",
        1,
    ),
    "relu_arbitrary_wrapper_expression": _RELU.replace(
        "    n_elements = x.numel()\n",
        "    n_elements = x.to(tl.float32)\n",
        1,
    ),
    "relu_invalid_prelude_ordering": _RELU.replace(
        "    out = torch.empty_like(x)\n"
        "    n_elements = x.numel()\n",
        "    n_elements = x.numel()\n"
        "    out = torch.empty_like(x)\n",
        1,
    ),
    "relu_missing_return": _RELU.replace(
        "    return out\n",
        "",
        1,
    ),
    "relu_wrong_launch_argument_ordering": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[grid](x, out, BLOCK_SIZE, n_elements)",
        1,
    ),
    "relu_undefined_grid_variable": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (foo,)\n",
        1,
    ),
    "softmax_missing_shape_extraction": _SOFTMAX.replace(
        "    n_cols = x.shape[1]\n",
        "",
        1,
    ),
    "softmax_wrong_shape_binding_type": _SOFTMAX.replace(
        "    n_cols = x.shape[1]\n",
        "    n_cols = x\n",
        1,
    ),
    "softmax_invalid_prelude_ordering": _SOFTMAX.replace(
        "    n_rows = x.shape[0]\n"
        "    n_cols = x.shape[1]\n",
        "    n_cols = x.shape[1]\n"
        "    n_rows = x.shape[0]\n",
        1,
    ),
    "matmul_missing_dimension_extraction": _MATMUL.replace(
        "    K = a.shape[1]\n",
        "",
        1,
    ),
    "matmul_wrong_dimension_binding_type": _MATMUL.replace(
        "    M = a.shape[0]\n",
        "    M = a\n",
        1,
    ),
    "matmul_invalid_grid_construction": _MATMUL.replace(
        "    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))\n",
        "    grid = (triton.cdiv(N, BLOCK_M), triton.cdiv(M, BLOCK_N))\n",
        1,
    ),
    "missing_output_allocation": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    out = x\n",
        1,
    ),
    "launch_uses_input_not_output": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[grid](x, x, n_elements, BLOCK_SIZE)",
        1,
    ),
    "relu_missing_launch_tail": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[grid](x, out)",
        1,
    ),
    "relu_wrong_launch_tail": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[grid](x, out, BLOCK_SIZE)",
        1,
    ),
    "softmax_missing_launch_tail": _SOFTMAX.replace(
        "_softmax_kernel[grid](x, out, n_cols, BLOCK_SIZE)",
        "_softmax_kernel[grid](x, out)",
        1,
    ),
    "matmul_missing_launch_tail": _MATMUL.replace(
        "_matmul_kernel[grid](a, b, c, M, N, K, BLOCK_M, BLOCK_N, BLOCK_K)",
        "_matmul_kernel[grid](a, b, c)",
        1,
    ),
    "return_input_after_allocation": _RELU.replace(
        "    return out\n",
        "    return x\n",
        1,
    ),
    "unused_output_allocation": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = torch.empty_like(x)\n    out = x\n",
        1,
    ),
    "reassigned_output_after_allocation": _RELU.replace(
        "    n_elements = x.numel()\n",
        "    out = x\n    n_elements = x.numel()\n",
        1,
    ),
    "undefined_name_in_output_allocation": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    out = torch.empty_like(foo)\n",
        1,
    ),
    "empty_like_non_tensor_input": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = x.numel()\n    out = torch.empty_like(tmp)\n",
        1,
    ),
    "torch_empty_tensor_shape": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    out = torch.empty((x,), device=x.device, dtype=x.dtype)\n",
        1,
    ),
    "torch_empty_missing_device_dtype": _RELU.replace(
        "    out = torch.empty_like(x)\n    n_elements = x.numel()\n",
        "    n_elements = x.numel()\n    out = torch.empty((n_elements,))\n",
        1,
    ),
    "torch_empty_like_invalid_empty_source": _RELU.replace(
        "    out = torch.empty_like(x)\n",
        "    tmp = torch.empty((x,), device=x.device, dtype=x.dtype)\n"
        "    out = torch.empty_like(tmp)\n",
        1,
    ),
    "missing_grid_assignment": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "",
        1,
    ),
    "launch_uses_wrong_grid_name": _RELU.replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[foo](x, out, n_elements, BLOCK_SIZE)",
        1,
    ),
    "grid_reassigned_after_assignment": _RELU.replace(
        "    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)\n",
        "    grid = foo\n    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)\n",
        1,
    ),
    "undefined_name_in_grid_tuple": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (foo,)\n",
        1,
    ),
    "empty_grid_tuple": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = ()\n",
        1,
    ),
    "tensor_name_in_grid_tuple": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (out,)\n",
        1,
    ),
    "dtype_attribute_in_grid_tuple": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (tl.float32,)\n",
        1,
    ),
    "grid_float_division": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (n_elements / BLOCK_SIZE,)\n",
        1,
    ),
    "grid_matmul_operator": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "    grid = (n_elements @ BLOCK_SIZE,)\n",
        1,
    ),
    "inline_undefined_grid_tuple": _RELU.replace(
        "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n",
        "",
        1,
    ).replace(
        "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
        "_relu_kernel[(foo,)](x, out, n_elements, BLOCK_SIZE)",
        1,
    ),
}
