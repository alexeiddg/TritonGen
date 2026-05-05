from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Literal

from cluster1.validation.compile_check import CompileSpec


class _TorchStub:
    class Tensor:
        pass

    class dtype:
        pass

    Tensor.__module__ = "torch"
    Tensor.__qualname__ = "Tensor"
    dtype.__module__ = "torch"
    dtype.__qualname__ = "dtype"

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(
            "PyTorch is required for CUDA dummy launch argument construction. "
            f"Attempted to access torch.{name} in an environment without torch."
        )


try:
    import torch as torch
except ImportError:
    torch = _TorchStub()  # type: ignore[assignment]


@dataclass(frozen=True)
class KernelSpec:
    """Canonical kernel metadata consumed by prompt construction, compile validation,
    and experiment runner."""

    name: str
    kernel_class: Literal["elementwise", "reduction", "matmul"]
    launcher_name: str
    reference_signature: inspect.Signature
    compile_spec: CompileSpec
    prompt_template: str
    autotune_configs: list[dict[str, Any]]
    shapes_by_dtype: dict[str, list[tuple[int, ...]]]
    dataset_id: str
    dataset_problem_id: int
    reference_code: str
