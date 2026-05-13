"""Isolated KernelBench reference execution for the locked C2 archetypes.

This module executes only ``KernelSpec.reference_code`` for ReLU, Softmax, and
GEMM. It does not call KernelBench ``get_inputs()``, Triton, compile checks, or
Cluster 2 pipeline runtime.
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cluster2.constants import DTYPE_NAMES
from shared.eval.correctness_shapes import (
    KernelClass,
    SHAPE_SPLITS,
    Shape,
    ShapeSplit,
    derive_deterministic_seed,
    get_shape_metadata,
    get_shape_metadata_by_kernel_name,
    validate_shape_for_kernel,
    validate_shape_for_kernel_name,
)

if TYPE_CHECKING:
    from cluster1.data.kernels.spec import KernelSpec


@dataclass(frozen=True)
class ReferenceExecutionResult:
    """Reference output and identity metadata for one deterministic input cell."""

    kernel_class: KernelClass
    kernel_name: str
    dtype: str
    shape: Shape
    base_seed: int
    attempt_index: int
    split: ShapeSplit
    output: Any


def run_reference(
    kernel_class: str,
    dtype: str,
    shape: tuple[int, ...],
    *,
    base_seed: int,
    attempt_index: int,
    split: ShapeSplit,
    device: str = "cpu",
) -> ReferenceExecutionResult:
    """Load ``KernelSpec.reference_code`` and execute ``Model.forward`` once."""

    spec = _get_locked_spec(kernel_class)
    metadata = get_shape_metadata(kernel_class)
    if spec.name != metadata.kernel_name:
        raise ValueError(f"{metadata.kernel_class} spec name mismatch: {spec.name!r}")

    validated_shape = validate_shape_for_kernel(metadata.kernel_class, shape)
    inputs = make_reference_inputs(
        metadata.kernel_name,
        dtype,
        validated_shape,
        base_seed=base_seed,
        attempt_index=attempt_index,
        split=split,
        device=device,
    )
    model = load_reference_model(spec)

    torch = _torch()
    with torch.no_grad():
        output = model.forward(*inputs)

    return ReferenceExecutionResult(
        kernel_class=metadata.kernel_class,
        kernel_name=metadata.kernel_name,
        dtype=dtype,
        shape=validated_shape,
        base_seed=base_seed,
        attempt_index=attempt_index,
        split=split,
        output=output,
    )


def make_reference_inputs(
    kernel_name: str,
    dtype: str,
    shape: tuple[int, ...],
    *,
    base_seed: int,
    attempt_index: int,
    split: ShapeSplit,
    device: str = "cpu",
) -> tuple[Any, ...]:
    """Create deterministic reference inputs without calling ``get_inputs()``."""

    metadata = get_shape_metadata_by_kernel_name(kernel_name)
    dtype = _require_dtype_name(dtype)
    split = _require_split(split)
    validated_shape = validate_shape_for_kernel_name(kernel_name, shape)
    seed = derive_input_seed(
        kernel_name,
        dtype,
        validated_shape,
        base_seed=base_seed,
        attempt_index=attempt_index,
        split=split,
    )

    torch = _torch()
    torch_dtype = torch_dtype_from_name(dtype)
    generator_device = "cuda" if str(device).startswith("cuda") else "cpu"
    generator = torch.Generator(device=generator_device)
    generator.manual_seed(seed)

    if metadata.kernel_name == "relu":
        return (
            torch.randn(
                validated_shape,
                dtype=torch_dtype,
                device=device,
                generator=generator,
            ),
        )
    if metadata.kernel_name == "softmax":
        return (
            torch.randn(
                validated_shape,
                dtype=torch_dtype,
                device=device,
                generator=generator,
            ),
        )
    if metadata.kernel_name == "gemm":
        m, n, k = validated_shape
        a = torch.randn((m, k), dtype=torch_dtype, device=device, generator=generator)
        b = torch.randn((k, n), dtype=torch_dtype, device=device, generator=generator)
        return a, b

    raise ValueError(f"unsupported reference kernel {metadata.kernel_name!r}")


def derive_input_seed(
    kernel_name: str,
    dtype: str,
    shape: tuple[int, ...],
    *,
    base_seed: int,
    attempt_index: int,
    split: ShapeSplit,
) -> int:
    """Derive the deterministic input seed required by the Phase 2 contract."""

    validate_shape_for_kernel_name(kernel_name, shape)
    dtype = _require_dtype_name(dtype)
    split = _require_split(split)
    if not isinstance(base_seed, int) or isinstance(base_seed, bool):
        raise TypeError("base_seed must be an int")
    if not isinstance(attempt_index, int) or isinstance(attempt_index, bool):
        raise TypeError("attempt_index must be an int")
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    return derive_deterministic_seed(
        "reference_inputs",
        kernel_name,
        dtype,
        tuple(shape),
        base_seed,
        attempt_index,
        split,
    )


def torch_dtype_from_name(dtype: str) -> Any:
    """Map Cluster 2 dtype names to Torch dtype objects."""

    dtype = _require_dtype_name(dtype)
    torch = _torch()
    if dtype == "fp32":
        return torch.float32
    if dtype == "fp16":
        return torch.float16
    return torch.bfloat16


def load_reference_model(spec: "KernelSpec") -> Any:
    """Instantiate ``Model`` from isolated ``KernelSpec.reference_code`` scope."""

    module = load_reference_module(spec)
    model_cls = module.__dict__.get("Model")
    if model_cls is None:
        raise ValueError(f"KernelSpec {spec.name!r} reference_code does not define Model")
    model = model_cls()
    if hasattr(model, "eval"):
        model.eval()
    return model


def load_reference_module(spec: "KernelSpec") -> types.ModuleType:
    """Execute ``KernelSpec.reference_code`` in a fresh module namespace."""

    if spec.name not in {"relu", "softmax", "gemm"}:
        raise ValueError(f"unsupported KernelSpec reference {spec.name!r}")
    module_seed = derive_deterministic_seed("reference_module", spec.name, spec.reference_code)
    module_name = f"_tritongen_c2_reference_{spec.name}_{module_seed:x}"
    module = types.ModuleType(module_name)
    module.__dict__["__file__"] = f"<{module_name}>"
    code = compile(spec.reference_code, module.__dict__["__file__"], "exec")
    exec(code, module.__dict__)
    return module


def _get_locked_spec(kernel_class: str) -> "KernelSpec":
    metadata = get_shape_metadata(kernel_class)
    from cluster1.data.kernels import get_kernel_spec

    spec = get_kernel_spec(metadata.kernel_class)
    if spec.name not in {"relu", "softmax", "gemm"}:
        raise ValueError(f"unsupported KernelSpec reference {spec.name!r}")
    return spec


def _torch() -> Any:
    import torch

    return torch


def _require_dtype_name(dtype: str) -> str:
    if not isinstance(dtype, str):
        raise TypeError("dtype must be a string")
    if dtype not in DTYPE_NAMES:
        raise ValueError(
            f"unsupported dtype {dtype!r}; expected one of: {', '.join(DTYPE_NAMES)}"
        )
    return dtype


def _require_split(split: ShapeSplit) -> ShapeSplit:
    if split not in SHAPE_SPLITS:
        raise ValueError(f"unsupported shape split {split!r}; expected one of: repair, eval")
    return split
