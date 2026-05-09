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
