"""Tests for Phase 2 isolated KernelBench reference execution."""

from __future__ import annotations

import random
import sys
import types
from dataclasses import replace

import pytest

from cluster1.data.kernels import KERNEL_SPECS
from shared.eval.reference_runner import (
    derive_input_seed,
    load_reference_module,
    make_reference_inputs,
    run_reference,
)


class _FakeTensor:
    def __init__(
        self,
        data: tuple[float | bool, ...],
        shape: tuple[int, ...],
        dtype: str = "fp32",
    ) -> None:
        self.data = data
        self.shape = shape
        self.dtype = dtype

    def __add__(self, other: float) -> "_FakeTensor":
        return _FakeTensor(
            tuple(float(value) + other for value in self.data),
            self.shape,
            self.dtype,
        )

    def relu(self) -> "_FakeTensor":
        return _FakeTensor(
            tuple(max(0.0, float(value)) for value in self.data),
            self.shape,
            self.dtype,
        )

    def matmul(self, other: "_FakeTensor") -> "_FakeTensor":
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
        return _FakeTensor(tuple(output), (rows, cols), self.dtype)

    def item(self) -> float | bool:
        if self.shape != ():
            raise ValueError("item() requires a scalar tensor")
        return self.data[0]


class _FakeGenerator:
    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self._rng = random.Random(0)

    def manual_seed(self, seed: int) -> "_FakeGenerator":
        self._rng.seed(seed)
        return self


class _FakeNoGrad:
    def __init__(self, torch_module: types.ModuleType) -> None:
        self._torch_module = torch_module
        self._previous = True

    def __enter__(self) -> None:
        self._previous = self._torch_module._grad_enabled
        self._torch_module._grad_enabled = False

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._torch_module._grad_enabled = self._previous


@pytest.fixture
def fake_torch(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    torch_module = types.ModuleType("torch")
    torch_module.Tensor = _FakeTensor
    torch_module.float32 = "fp32"
    torch_module.float16 = "fp16"
    torch_module.bfloat16 = "bf16"
    torch_module._grad_enabled = True

    def randn(
        shape: tuple[int, ...],
        *,
        dtype: str,
        device: str,
        generator: _FakeGenerator,
    ) -> _FakeTensor:
        del device
        total = 1
        for dim in shape:
            total *= dim
        data = tuple(generator._rng.uniform(-1.0, 1.0) for _ in range(total))
        return _FakeTensor(data, shape, dtype)

    torch_module.Generator = _FakeGenerator
    torch_module.randn = randn
    torch_module.relu = lambda tensor: tensor.relu()
    torch_module.matmul = lambda left, right: left.matmul(right)
    torch_module.equal = lambda left, right: (
        left.shape == right.shape and left.dtype == right.dtype and left.data == right.data
    )
    torch_module.tensor = lambda value: _FakeTensor((value,), ())
    torch_module.no_grad = lambda: _FakeNoGrad(torch_module)
    torch_module.is_grad_enabled = lambda: torch_module._grad_enabled
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    return torch_module


def test_reference_runner_loads_model_and_calls_forward(
    monkeypatch: pytest.MonkeyPatch,
    fake_torch: types.ModuleType,
) -> None:
    reference_code = """\
import torch

class Model:
    def __init__(self):
        self.offset = 3.0

    def __call__(self, *inputs):
        raise RuntimeError("Model.__call__ should not be used")

    def forward(self, x):
        return x + self.offset

def get_inputs():
    raise RuntimeError("get_inputs should not be called")
"""
    monkeypatch.setitem(
        KERNEL_SPECS,
        "elementwise",
        replace(KERNEL_SPECS["elementwise"], reference_code=reference_code),
    )

    expected_input = make_reference_inputs(
        "relu",
        "fp32",
        (2, 3),
        base_seed=11,
        attempt_index=1,
        split="repair",
    )[0]
    result = run_reference(
        "elementwise",
        "fp32",
        (2, 3),
        base_seed=11,
        attempt_index=1,
        split="repair",
    )

    assert fake_torch.equal(result.output, expected_input + 3.0)


def test_reference_runner_executes_under_no_grad(
    monkeypatch: pytest.MonkeyPatch,
    fake_torch: types.ModuleType,
) -> None:
    del fake_torch
    reference_code = """\
import torch

class Model:
    def forward(self, x):
        return torch.tensor(torch.is_grad_enabled())

def get_inputs():
    raise RuntimeError("get_inputs should not be called")
"""
    monkeypatch.setitem(
        KERNEL_SPECS,
        "elementwise",
        replace(KERNEL_SPECS["elementwise"], reference_code=reference_code),
    )

    result = run_reference(
        "elementwise",
        "fp32",
        (2, 3),
        base_seed=11,
        attempt_index=1,
        split="repair",
    )

    assert result.output.item() is False


def test_reference_runner_avoids_get_inputs(
    monkeypatch: pytest.MonkeyPatch,
    fake_torch: types.ModuleType,
) -> None:
    reference_code = """\
import torch

class Model:
    def forward(self, x):
        return torch.relu(x)

def get_inputs():
    raise AssertionError("get_inputs was called")
"""
    monkeypatch.setitem(
        KERNEL_SPECS,
        "elementwise",
        replace(KERNEL_SPECS["elementwise"], reference_code=reference_code),
    )

    result = run_reference(
        "elementwise",
        "fp32",
        (4,),
        base_seed=5,
        attempt_index=0,
        split="eval",
    )

    assert isinstance(result.output, fake_torch.Tensor)


def test_reference_module_scope_is_isolated(fake_torch: types.ModuleType) -> None:
    del fake_torch
    spec = replace(
        KERNEL_SPECS["elementwise"],
        reference_code="""\
SENTINEL = "module-local"

class Model:
    def forward(self, x):
        return x
""",
    )

    module = load_reference_module(spec)

    assert module.__dict__["SENTINEL"] == "module-local"
    assert "SENTINEL" not in globals()


def test_reference_outputs_are_deterministic_for_same_seed(
    monkeypatch: pytest.MonkeyPatch,
    fake_torch: types.ModuleType,
) -> None:
    reference_code = """\
import torch

class Model:
    def forward(self, A, B):
        return torch.matmul(A, B)

def get_inputs():
    raise RuntimeError("get_inputs should not be called")
"""
    monkeypatch.setitem(
        KERNEL_SPECS,
        "matmul",
        replace(KERNEL_SPECS["matmul"], reference_code=reference_code),
    )

    first = run_reference(
        "matmul",
        "fp32",
        (4, 5, 3),
        base_seed=2026,
        attempt_index=2,
        split="eval",
    )
    second = run_reference(
        "matmul",
        "fp32",
        (4, 5, 3),
        base_seed=2026,
        attempt_index=2,
        split="eval",
    )

    assert fake_torch.equal(first.output, second.output)


def test_reference_inputs_are_deterministic_from_all_seed_components(
    fake_torch: types.ModuleType,
) -> None:
    first = make_reference_inputs(
        "softmax",
        "fp32",
        (3, 7),
        base_seed=12,
        attempt_index=0,
        split="repair",
    )[0]
    second = make_reference_inputs(
        "softmax",
        "fp32",
        (3, 7),
        base_seed=12,
        attempt_index=0,
        split="repair",
    )[0]
    changed_attempt = make_reference_inputs(
        "softmax",
        "fp32",
        (3, 7),
        base_seed=12,
        attempt_index=1,
        split="repair",
    )[0]

    assert fake_torch.equal(first, second)
    assert not fake_torch.equal(first, changed_attempt)


def test_input_seed_derivation_includes_required_components() -> None:
    base = derive_input_seed(
        "relu",
        "fp32",
        (8,),
        base_seed=1,
        attempt_index=0,
        split="repair",
    )
    changed_split = derive_input_seed(
        "relu",
        "fp32",
        (8,),
        base_seed=1,
        attempt_index=0,
        split="eval",
    )

    assert base != changed_split


def test_reference_runner_supports_only_locked_kernels() -> None:
    with pytest.raises(KeyError, match="unsupported C2 kernel_class"):
        run_reference(
            "fused",
            "fp32",
            (8,),
            base_seed=1,
            attempt_index=0,
            split="repair",
        )
