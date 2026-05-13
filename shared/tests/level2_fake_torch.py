"""Small fake torch surface for Level 2 CPU-only tests."""

from __future__ import annotations

import math
import random
import sys
import types
from dataclasses import replace
from typing import Any

import pytest

from cluster1.data.kernels import KERNEL_SPECS


class FakeTensor:
    def __init__(
        self,
        data: tuple[float | bool, ...],
        shape: tuple[int, ...],
        dtype: str = "fp32",
    ) -> None:
        self.data = data
        self.shape = shape
        self.dtype = dtype
        self.is_sparse = False

    def __add__(self, other: float | "FakeTensor") -> "FakeTensor":
        return self._binary(other, lambda left, right: left + right)

    def __sub__(self, other: float | "FakeTensor") -> "FakeTensor":
        return self._binary(other, lambda left, right: left - right)

    def __truediv__(self, other: float | "FakeTensor") -> "FakeTensor":
        return self._binary(other, lambda left, right: left / right)

    def _binary(self, other: float | "FakeTensor", op) -> "FakeTensor":  # type: ignore[no-untyped-def]
        if isinstance(other, FakeTensor):
            if self.shape != other.shape:
                raise ValueError("shape mismatch")
            return FakeTensor(
                tuple(op(float(left), float(right)) for left, right in zip(self.data, other.data)),
                self.shape,
                self.dtype,
            )
        return FakeTensor(tuple(op(float(value), other) for value in self.data), self.shape, self.dtype)

    def relu(self) -> "FakeTensor":
        return FakeTensor(
            tuple(max(0.0, float(value)) for value in self.data),
            self.shape,
            self.dtype,
        )

    def matmul(self, other: "FakeTensor") -> "FakeTensor":
        rows, inner = self.shape
        other_inner, cols = other.shape
        if inner != other_inner:
            raise ValueError("matmul shape mismatch")
        output: list[float] = []
        for row in range(rows):
            for col in range(cols):
                total = 0.0
                for idx in range(inner):
                    total += float(self.data[row * inner + idx]) * float(
                        other.data[idx * cols + col]
                    )
                output.append(total)
        return FakeTensor(tuple(output), (rows, cols), self.dtype)

    def clone(self) -> "FakeTensor":
        return FakeTensor(tuple(self.data), self.shape, self.dtype)

    def with_first(self, value: float) -> "FakeTensor":
        return FakeTensor((value, *self.data[1:]), self.shape, self.dtype)

    def reshape(self, *shape: int) -> "FakeTensor":
        if shape == (-1,):
            return FakeTensor(tuple(self.data), (len(self.data),), self.dtype)
        if math.prod(shape) != len(self.data):
            raise ValueError("reshape element count mismatch")
        return FakeTensor(tuple(self.data), tuple(shape), self.dtype)

    def detach(self) -> "FakeTensor":
        return self

    def cpu(self) -> "FakeTensor":
        return self

    def to(self, *, dtype: str) -> "FakeTensor":
        return FakeTensor(tuple(self.data), self.shape, dtype)

    def to_dense(self) -> "FakeTensor":
        return self

    def numel(self) -> int:
        return len(self.data)

    def max(self) -> "FakeTensor":
        return FakeTensor((max(self.data),), ())

    def any(self) -> "FakeTensor":
        return FakeTensor((any(bool(value) for value in self.data),), ())

    def item(self) -> float | bool:
        if len(self.data) != 1:
            raise ValueError("item() requires exactly one value")
        return self.data[0]


class FakeGenerator:
    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self._rng = random.Random(0)

    def manual_seed(self, seed: int) -> "FakeGenerator":
        self._rng.seed(seed)
        return self


class FakeNoGrad:
    def __init__(self, torch_module: types.ModuleType) -> None:
        self._torch_module = torch_module
        self._previous = True

    def __enter__(self) -> None:
        self._previous = self._torch_module._grad_enabled
        self._torch_module._grad_enabled = False

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self._torch_module._grad_enabled = self._previous


def install_fake_level2_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    torch_module = _build_fake_torch()
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(
        KERNEL_SPECS,
        "elementwise",
        replace(
            KERNEL_SPECS["elementwise"],
            reference_code="""\
import torch

class Model:
    def forward(self, x):
        return torch.relu(x)
""",
        ),
    )


def _build_fake_torch() -> types.ModuleType:
    torch_module = types.ModuleType("torch")
    torch_module.Tensor = FakeTensor
    torch_module.float32 = "fp32"
    torch_module.float16 = "fp16"
    torch_module.bfloat16 = "bf16"
    torch_module.float64 = "fp64"
    torch_module._grad_enabled = True
    torch_module._deterministic_algorithms = None
    torch_module._deterministic_warn_only = None
    torch_module.backends = types.SimpleNamespace(
        cuda=types.SimpleNamespace(
            matmul=types.SimpleNamespace(allow_tf32=True),
        ),
        cudnn=types.SimpleNamespace(
            allow_tf32=True,
            deterministic=False,
            benchmark=True,
        ),
    )

    def randn(
        shape: tuple[int, ...],
        *,
        dtype: str,
        device: str,
        generator: FakeGenerator,
    ) -> FakeTensor:
        del device
        return FakeTensor(
            tuple(generator._rng.uniform(-1.0, 1.0) for _ in range(math.prod(shape))),
            shape,
            dtype,
        )

    def zeros(shape: tuple[int, ...], *, dtype: str) -> FakeTensor:
        return FakeTensor(tuple(0.0 for _ in range(math.prod(shape))), shape, dtype)

    def as_tensor(value: Any) -> FakeTensor:
        if isinstance(value, FakeTensor):
            return value
        if isinstance(value, (int, float, bool)):
            return FakeTensor((value,), ())
        return FakeTensor(tuple(value), (len(value),))

    def abs_tensor(tensor: FakeTensor) -> FakeTensor:
        return FakeTensor(tuple(abs(float(value)) for value in tensor.data), tensor.shape, tensor.dtype)

    def clamp(tensor: FakeTensor, *, min: float) -> FakeTensor:
        return FakeTensor(tuple(max(float(value), min) for value in tensor.data), tensor.shape, tensor.dtype)

    def isnan(tensor: FakeTensor) -> FakeTensor:
        return FakeTensor(tuple(math.isnan(float(value)) for value in tensor.data), tensor.shape)

    def isinf(tensor: FakeTensor) -> FakeTensor:
        return FakeTensor(tuple(math.isinf(float(value)) for value in tensor.data), tensor.shape)

    def allclose(left: FakeTensor, right: FakeTensor, *, atol: float, rtol: float) -> bool:
        if left.shape != right.shape:
            return False
        return all(
            abs(float(left_value) - float(right_value))
            <= atol + rtol * abs(float(right_value))
            for left_value, right_value in zip(left.data, right.data)
        )

    def use_deterministic_algorithms(
        enabled: bool,
        *,
        warn_only: bool = False,
    ) -> None:
        torch_module._deterministic_algorithms = enabled
        torch_module._deterministic_warn_only = warn_only

    torch_module.Generator = FakeGenerator
    torch_module.randn = randn
    torch_module.zeros = zeros
    torch_module.as_tensor = as_tensor
    torch_module.relu = lambda tensor: tensor.relu()
    torch_module.matmul = lambda left, right: left.matmul(right)
    torch_module.no_grad = lambda: FakeNoGrad(torch_module)
    torch_module.abs = abs_tensor
    torch_module.clamp = clamp
    torch_module.isnan = isnan
    torch_module.isinf = isinf
    torch_module.allclose = allclose
    torch_module.use_deterministic_algorithms = use_deterministic_algorithms
    return torch_module
