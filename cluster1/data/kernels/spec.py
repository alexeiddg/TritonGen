from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal


@dataclass(frozen=True)
class CompileSpec:
    """Validation spec for the compile gate — independent of dataset loading."""

    launcher_name: str
    reference_signature: inspect.Signature
    build_args: Callable[[tuple[int, ...], "torch.dtype"], tuple[list[Any], dict[str, Any]]]


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
