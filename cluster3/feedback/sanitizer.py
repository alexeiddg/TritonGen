"""Cluster 3 compile-feedback sanitization.

This module intentionally owns its feedback policy instead of importing or
wrapping Cluster 2 prompt helpers. P feedback may include compiler diagnostics
that mention LLVM or PTX, but it still excludes performance, profiler, hidden
test, and private evaluation language.
"""

from __future__ import annotations

import re
from typing import Final


LLVM_PTX_ALLOWED: Final[bool] = True

P_FORBIDDEN_FEEDBACK_TERMS: Final[tuple[str, ...]] = (
    "speedup",
    "fast@",
    "nsight",
    "ncu",
    "nvml",
    "compute-sanitizer",
    "profil",
    "timing",
    "latency",
    "performance",
    "token",
    "benchmark",
    "RL",
    "GRPO",
    "TRL",
    "C++ traceback",
    "eval_shape_set",
    "hidden",
    "private",
    "edge cases",
    "extra shapes",
)

P_SENSITIVE_DETAIL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"(?<![A-Za-z0-9_])(?:eval_shape_set|eval[\s_-]+set|eval\s+shapes?)"
        r"(?![A-Za-z0-9_])[^|;]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_])(?:hidden|private|edge\s+cases|extra\s+shapes)"
        r"(?![A-Za-z0-9_])[^|;]*",
        re.IGNORECASE,
    ),
)


def _term_pattern(term: str) -> str:
    escaped = re.escape(term)
    if term in {
        "speedup",
        "profil",
        "timing",
        "latency",
        "performance",
        "token",
        "benchmark",
    }:
        return rf"(?<![A-Za-z0-9]){escaped}[A-Za-z0-9_]*"
    if re.fullmatch(r"[A-Za-z0-9_]+", term):
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return escaped


_FORBIDDEN_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(_term_pattern(term), re.IGNORECASE)
    for term in P_FORBIDDEN_FEEDBACK_TERMS
)


def sanitize_p_feedback_text(value: str | None, *, limit: int | None = 2000) -> str:
    """Return public P feedback text with private/eval details redacted.

    Forbidden non-compile feedback terms raise after sensitive details are
    redacted. Truncation keeps the head of the text and drops the tail.
    """

    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError("value must be a string or None")
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise TypeError("limit must be an int or None")
        if limit < 0:
            raise ValueError("limit must be non-negative")

    text = " ".join(value.split())
    for pattern in P_SENSITIVE_DETAIL_PATTERNS:
        text = pattern.sub("[redacted]", text)
    validate_no_forbidden_p_terms(text)
    if limit is not None:
        text = text[:limit]
    return text.strip()


def validate_no_forbidden_p_terms(value: str) -> None:
    """Raise if P feedback includes forbidden non-compile feedback terms."""

    if not isinstance(value, str):
        raise TypeError("value must be a string")
    for term, pattern in zip(
        P_FORBIDDEN_FEEDBACK_TERMS,
        _FORBIDDEN_PATTERNS,
        strict=True,
    ):
        if pattern.search(value):
            raise ValueError(f"feedback contains forbidden term: {term}")
