"""Tests for per-operation tolerance lookup."""

from __future__ import annotations

import pytest

from shared.eval.tolerances import TOLERANCE_TABLE, get_tolerances


def test_lookup_each_kernel_class_dtype_combination() -> None:
    for kernel_class, by_dtype in TOLERANCE_TABLE.items():
        for dtype in by_dtype:
            tolerance = get_tolerances(kernel_class, dtype)
            assert set(tolerance) == {
                "atol",
                "rtol",
                "reference_variance_max_abs",
                "reference_variance_max_rel",
            }
            assert tolerance["reference_variance_max_abs"] is None
            assert tolerance["reference_variance_max_rel"] is None


def test_expected_fp32_values() -> None:
    assert get_tolerances("elementwise", "fp32")["atol"] == 1e-5
    assert get_tolerances("elementwise", "fp32")["rtol"] == 1e-5
    assert get_tolerances("reduction", "fp32")["atol"] == 1e-4
    assert get_tolerances("reduction", "fp32")["rtol"] == 1e-4
    assert get_tolerances("matmul", "fp32")["atol"] == 1e-3
    assert get_tolerances("matmul", "fp32")["rtol"] == 1e-3
    assert get_tolerances("fused", "fp32")["atol"] == 1e-3
    assert get_tolerances("fused", "fp32")["rtol"] == 1e-3


def test_expected_fp16_bf16_values() -> None:
    for dtype in ("fp16", "bf16"):
        assert get_tolerances("elementwise", dtype)["atol"] == 1e-3
        assert get_tolerances("elementwise", dtype)["rtol"] == 1e-3
        assert get_tolerances("reduction", dtype)["atol"] == 1e-2
        assert get_tolerances("reduction", dtype)["rtol"] == 1e-2
        assert get_tolerances("matmul", dtype)["atol"] == 5e-2
        assert get_tolerances("matmul", dtype)["rtol"] == 5e-2
        assert get_tolerances("fused", dtype)["atol"] == 5e-2
        assert get_tolerances("fused", dtype)["rtol"] == 5e-2


def test_unknown_kernel_class_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_tolerances("unknown", "fp32")


def test_unknown_dtype_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_tolerances("elementwise", "float64")
