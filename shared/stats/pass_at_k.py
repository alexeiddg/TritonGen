"""
Unbiased pass@k estimator (Chen et al., 2021 — HumanEval).

Used by all three clusters. Correctness definition varies per cluster:
  Cluster 1: compile_success=True
  Cluster 2: compile_success=True after ≤N repair rounds
  Cluster 3: compile_success=True AND speedup ≥ threshold
"""
from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimator: 1 - C(n-c, k) / C(n, k).

    Args:
        n: total number of samples
        c: number of correct samples
        k: k in pass@k

    Returns:
        Estimated pass@k probability.

    Raises:
        ValueError: if k > n.
    """
    if k > n:
        raise ValueError(f"k={k} cannot exceed n={n}")
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_at_k_table(n: int, c: int, ks: tuple[int, ...] = (1, 5, 10)) -> dict[int, float]:
    """Compute pass@k for multiple k values at once."""
    return {k: pass_at_k(n, c, k) for k in ks if k <= n}


def unique_solution_rate(hashes: list[str]) -> float:
    """Fraction of distinct outputs — detects grammar-induced mode collapse."""
    if not hashes:
        return 0.0
    return len(set(hashes)) / len(hashes)
