"""HumanEval-style pass@k and compile@1 metrics."""

from __future__ import annotations

from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    """Return the unbiased HumanEval pass@k estimate.

    ``n`` is the total number of samples and ``c`` is the number of successful
    samples under the caller's active gate. Cluster 1 callers must pass strict
    all-dtype ``compile_success`` counts only.
    """

    if n < 0:
        raise ValueError("n must be non-negative")
    if c < 0 or c > n:
        raise ValueError("c must satisfy 0 <= c <= n")
    if k <= 0:
        raise ValueError("k must be positive")
    if k > n:
        raise ValueError("k must be <= n")
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def compile_at_1(successes: int, total: int) -> float:
    """Return compile@1 as strict compile successes divided by total rows."""

    if total <= 0:
        raise ValueError("total must be positive")
    if successes < 0 or successes > total:
        raise ValueError("successes must satisfy 0 <= successes <= total")
    return successes / total
