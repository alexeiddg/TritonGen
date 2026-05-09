"""Locked prompt template for Cluster 1 generation.

The prompt must not change between grammar_active=True and grammar_active=False runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cluster1.data.kernels.spec import KernelSpec

PROMPT_TEMPLATE = """\
You are a Triton GPU kernel engineer. Write a complete Python module.

Public launcher signature: def {signature}:
Private Triton helper name: {helper_name}
Kernel description: {description}
Input dtype: {dtype}  |  Device: CUDA

Required module surface:
- Start with exactly these imports:
  import torch
  import triton
  import triton.language as tl
- Define one private @triton.jit helper named {helper_name}.
- Define one public Python launcher named exactly {launcher_name}.
- The public launcher signature must be exactly: def {signature}:
- The public launcher must allocate the output tensor.
- The public launcher must define an explicit grid.
- The public launcher must launch {helper_name} with bracket syntax.
- The public launcher must return the output tensor.

Allowed block configurations:
{autotune_configs}

Return ONLY the Python module. No explanation. No markdown fences. No prose.
"""

ELEMENTWISE_AUTOTUNE_CONFIGS = [
    {"BLOCK_SIZE": 64, "num_warps": 2, "num_stages": 3},
    {"BLOCK_SIZE": 128, "num_warps": 4, "num_stages": 3},
    {"BLOCK_SIZE": 256, "num_warps": 4, "num_stages": 3},
    {"BLOCK_SIZE": 512, "num_warps": 8, "num_stages": 3},
]

REDUCTION_AUTOTUNE_CONFIGS = [
    {"BLOCK_SIZE": 64, "num_warps": 2, "num_stages": 3},
    {"BLOCK_SIZE": 128, "num_warps": 4, "num_stages": 3},
    {"BLOCK_SIZE": 256, "num_warps": 4, "num_stages": 4},
    {"BLOCK_SIZE": 512, "num_warps": 8, "num_stages": 4},
]

MATMUL_AUTOTUNE_CONFIGS = [
    {"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32, "num_warps": 4, "num_stages": 2},
    {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "num_warps": 4, "num_stages": 3},
    {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "num_warps": 8, "num_stages": 3},
    {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "num_warps": 8, "num_stages": 4},
]


def _format_autotune_configs(configs: list[dict]) -> str:
    lines = []
    for cfg in configs:
        block_items = {
            key: value
            for key, value in cfg.items()
            if key not in {"num_warps", "num_stages"}
        }
        block_parts = ", ".join(
            f'"{key}": {value}' for key, value in block_items.items()
        )
        lines.append(
            "        triton.Config("
            f"{{{block_parts}}}, "
            f"num_warps={cfg['num_warps']}, "
            f"num_stages={cfg['num_stages']})"
        )
    return "[\n" + ",\n".join(lines) + "\n    ]"


KERNEL_DESCRIPTIONS = {
    "relu": "Applies elementwise ReLU activation: output = max(0, x). "
    "Input is a 1D or 2D tensor of arbitrary shape.",
    "softmax": "Computes row-wise softmax along dim=1 for a 2D input tensor. "
    "Each row is independently normalized to sum to 1.",
    "gemm": "Computes C = A @ B for 2D matrices A (M x K) and B (K x N), "
    "producing output C (M x N). Uses tiled matrix multiplication with shared memory.",
}


def build_prompt(spec: "KernelSpec", dtype: str) -> str:
    sig_str = str(spec.reference_signature)
    launcher = spec.launcher_name
    signature_line = f"{launcher}{sig_str}"
    helper_name = f"_{launcher}_kernel"

    description = KERNEL_DESCRIPTIONS.get(spec.name, f"Implements {spec.name} kernel.")
    configs_str = _format_autotune_configs(spec.autotune_configs)

    return PROMPT_TEMPLATE.format(
        signature=signature_line,
        launcher_name=launcher,
        helper_name=helper_name,
        description=description,
        dtype=dtype,
        autotune_configs=configs_str,
    )
