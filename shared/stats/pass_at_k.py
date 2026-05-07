"""Compatibility wrappers for shared evaluation metrics."""

from shared.eval.metrics.pass_at_k import pass_at_k


def pass_at_k_table(n: int, c: int, ks: tuple[int, ...] = (1, 5, 10)) -> dict[int, float]:
    """Compute pass@k for multiple k values at once."""
    return {k: pass_at_k(n, c, k) for k in ks if k <= n}


def unique_solution_rate(hashes: list[str]) -> float:
    """Fraction of distinct outputs — detects grammar-induced mode collapse."""
    if not hashes:
        return 0.0
    return len(set(hashes)) / len(hashes)
