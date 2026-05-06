"""Error mapping helpers for the TritonGen Modal harness.

Compile errors flow back to Cluster 1 only as result fields. They are never
fed into a repair loop or appended to a regeneration prompt — that would be a
Cluster 2 control signal and is out of scope here.
"""

from __future__ import annotations

_DEFAULT_MAX_CHARS = 4000


def truncate_output(text: str, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
    """Bound stdout/stderr length for safe JSONL persistence.

    The middle of the output is dropped and replaced with a one-line marker
    so both head and tail (where Triton typically prints diagnostics) are
    preserved.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    dropped = len(text) - max_chars
    return f"{text[:half]}\n... [truncated {dropped} chars] ...\n{text[-half:]}"


def map_compile_error_type(exc: BaseException) -> str:
    """Map a Python exception to the Cluster 1 compile-error taxonomy.

    The taxonomy is fixed by ``cluster1.results.dataclass.CompileErrorType``:
    ``CompilationError``, ``RuntimeError``, ``SignatureError``. Anything that
    falls through is labeled ``UnknownError`` so the runner can flag it for
    review without crashing the experiment loop.
    """
    exc_name = type(exc).__name__
    msg = str(exc)
    if "CompilationError" in exc_name:
        return "CompilationError"
    if exc_name == "SignatureError" or "signature" in msg.lower():
        return "SignatureError"
    if exc_name == "RuntimeError":
        return "RuntimeError"
    return "UnknownError"
