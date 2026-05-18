"""KernelBench Square Matmul — matmul-class kernel spec.

Dataset: ScalingIntelligence/KernelBench, Level 1, Problem 1.
"""

from __future__ import annotations

import inspect
from typing import Any

from cluster1.data.kernels.spec import CompileSpec, KernelSpec, torch
from cluster1.data.prompts.prompt_contract import (
    MATMUL_AUTOTUNE_CONFIGS,
    PROMPT_TEMPLATE,
)
from shared.eval.correctness_shapes import get_compile_shapes

REFERENCE_CODE = """\
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
        return torch.matmul(A, B)

N = 2048 * 2

def get_inputs():
    A = torch.rand(N, N)
    B = torch.rand(N, N)
    return [A, B]

def get_init_inputs():
    return []
"""


def _build_matmul_args(
    shape: tuple[int, ...], dtype: torch.dtype
) -> tuple[list[Any], dict[str, Any]]:
    M, N, K = shape
    a = torch.randn(M, K, dtype=dtype, device="cuda")
    b = torch.randn(K, N, dtype=dtype, device="cuda")
    return [a, b], {}


_MATMUL_SIGNATURE = inspect.Signature(
    parameters=[
        inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=torch.Tensor),
        inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=torch.Tensor),
    ],
    return_annotation=torch.Tensor,
)

_MATMUL_COMPILE_SPEC = CompileSpec(
    launcher_name="matmul",
    reference_signature=_MATMUL_SIGNATURE,
    build_args=_build_matmul_args,
)

GEMM_SPEC = KernelSpec(
    name="gemm",
    kernel_class="matmul",
    launcher_name="matmul",
    reference_signature=_MATMUL_SIGNATURE,
    compile_spec=_MATMUL_COMPILE_SPEC,
    prompt_template=PROMPT_TEMPLATE,
    autotune_configs=MATMUL_AUTOTUNE_CONFIGS,
    shapes_by_dtype={
        dtype: list(get_compile_shapes("matmul", dtype))
        for dtype in ("fp32", "fp16", "bf16")
    },
    dataset_id="ScalingIntelligence/KernelBench",
    dataset_problem_id=1,
    reference_code=REFERENCE_CODE,
)
