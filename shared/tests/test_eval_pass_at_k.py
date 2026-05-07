"""Tests for shared compile-only-safe metric primitives."""

from __future__ import annotations

import math

import pytest

from shared.eval.metrics.pass_at_k import compile_at_1, pass_at_k


def test_pass_at_k_matches_humaneval_formula() -> None:
    expected_k5 = 1.0 - math.comb(15, 5) / math.comb(20, 5)
    expected_k10 = 1.0 - math.comb(15, 10) / math.comb(20, 10)

    assert pass_at_k(20, 5, 1) == 5 / 20
    assert pass_at_k(20, 5, 5) == pytest.approx(expected_k5)
    assert pass_at_k(20, 5, 10) == pytest.approx(expected_k10)


@pytest.mark.parametrize("k", [1, 5, 10])
def test_pass_at_k_n20_contract_values(k: int) -> None:
    assert pass_at_k(20, 0, k) == 0.0
    assert pass_at_k(20, 20, k) == 1.0


def test_pass_at_k_edge_cases() -> None:
    assert pass_at_k(20, 0, 1) == 0.0
    assert pass_at_k(20, 20, 10) == 1.0
    assert pass_at_k(20, 16, 5) == 1.0

    with pytest.raises(ValueError, match="k must be <= n"):
        pass_at_k(0, 0, 1)
    with pytest.raises(ValueError, match="k must be <= n"):
        pass_at_k(4, 1, 5)
    with pytest.raises(ValueError, match="c must satisfy"):
        pass_at_k(20, 21, 1)
    with pytest.raises(ValueError, match="k must be positive"):
        pass_at_k(20, 1, 0)


def test_compile_at_1() -> None:
    assert compile_at_1(0, 20) == 0.0
    assert compile_at_1(5, 20) == 0.25
    assert compile_at_1(20, 20) == 1.0


def test_compile_at_1_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="total must be positive"):
        compile_at_1(0, 0)
    with pytest.raises(ValueError, match="successes must satisfy"):
        compile_at_1(21, 20)
