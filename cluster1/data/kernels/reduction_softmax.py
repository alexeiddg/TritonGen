"""KernelBench Softmax — reduction kernel spec.

Dataset: ScalingIntelligence/KernelBench, Level 1, Problem 23.
"""

from __future__ import annotations

import inspect
from typing import Any

import torch

from cluster1.data.kernels.spec import CompileSpec, KernelSpec
from cluster1.data.prompts.prompt_contract import (
    PROMPT_TEMPLATE,
    REDUCTION_AUTOTUNE_CONFIGS,
)

REFERENCE_CODE = """\
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.softmax(x, dim=1)

batch_size = 4096
dim = 393216

def get_inputs():
    x = torch.rand(batch_size, dim)
    return [x]

def get_init_inputs():
    return []
"""


def _build_softmax_args(
    shape: tuple[int, ...], dtype: torch.dtype
) -> tuple[list[Any], dict[str, Any]]:
    x = torch.randn(shape, dtype=dtype, device="cuda")
    output = torch.empty_like(x)
    n_cols = shape[-1]
    return [x, output, n_cols], {}


_SOFTMAX_SIGNATURE = inspect.Signature(
    parameters=[
        inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=torch.Tensor),
    ],
    return_annotation=torch.Tensor,
)

_SOFTMAX_COMPILE_SPEC = CompileSpec(
    launcher_name="softmax",
    reference_signature=_SOFTMAX_SIGNATURE,
    build_args=_build_softmax_args,
)

SOFTMAX_SPEC = KernelSpec(
    name="softmax",
    kernel_class="reduction",
    launcher_name="softmax",
    reference_signature=_SOFTMAX_SIGNATURE,
    compile_spec=_SOFTMAX_COMPILE_SPEC,
    prompt_template=PROMPT_TEMPLATE,
    autotune_configs=REDUCTION_AUTOTUNE_CONFIGS,
    shapes_by_dtype={
        # (16, 64)        — smaller-than-block rows, power-of-2 cols
        # (33, 100)       — non-power-of-2 both dims, non-divisible cols
        # (64, 256)       — power-of-2
        # (128, 1001)     — non-divisible cols (1001 not divisible by 64)
        # (4096, 393216)  — large, 393216 = 3×2^17 (non-power-of-2)
        "fp32": [(16, 64), (33, 100), (64, 256), (128, 1001), (4096, 393216)],
        "fp16": [(16, 64), (33, 100), (64, 256), (128, 1001), (4096, 393216)],
        "bf16": [(16, 64), (33, 100), (64, 256), (128, 1001), (4096, 393216)],
    },
    dataset_id="ScalingIntelligence/KernelBench",
    dataset_problem_id=23,
    reference_code=REFERENCE_CODE,
)
