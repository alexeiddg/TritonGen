"""KernelBench ReLU — elementwise kernel spec.

Dataset: ScalingIntelligence/KernelBench, Level 1, Problem 19.
"""

from __future__ import annotations

import inspect
from typing import Any

from cluster1.data.kernels.spec import CompileSpec, KernelSpec, torch
from cluster1.data.prompts.prompt_contract import (
    ELEMENTWISE_AUTOTUNE_CONFIGS,
    PROMPT_TEMPLATE,
)
from shared.eval.correctness_shapes import get_compile_shapes

REFERENCE_CODE = """\
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(x)

batch_size = 4096
dim = 393216

def get_inputs():
    x = torch.rand(batch_size, dim)
    return [x]

def get_init_inputs():
    return []
"""


def _build_relu_args(
    shape: tuple[int, ...], dtype: torch.dtype
) -> tuple[list[Any], dict[str, Any]]:
    x = torch.randn(shape, dtype=dtype, device="cuda")
    return [x], {}


_RELU_SIGNATURE = inspect.Signature(
    parameters=[
        inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=torch.Tensor),
    ],
    return_annotation=torch.Tensor,
)

_RELU_COMPILE_SPEC = CompileSpec(
    launcher_name="relu",
    reference_signature=_RELU_SIGNATURE,
    build_args=_build_relu_args,
)

RELU_SPEC = KernelSpec(
    name="relu",
    kernel_class="elementwise",
    launcher_name="relu",
    reference_signature=_RELU_SIGNATURE,
    compile_spec=_RELU_COMPILE_SPEC,
    prompt_template=PROMPT_TEMPLATE,
    autotune_configs=ELEMENTWISE_AUTOTUNE_CONFIGS,
    shapes_by_dtype={
        dtype: list(get_compile_shapes("elementwise", dtype))
        for dtype in ("fp32", "fp16", "bf16")
    },
    dataset_id="ScalingIntelligence/KernelBench",
    dataset_problem_id=19,
    reference_code=REFERENCE_CODE,
)
