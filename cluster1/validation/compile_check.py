"""Compilation validation gate for Cluster 1.

Performs actual Triton JIT compilation via dummy kernel launches.
No timing, no numerical comparisons, no repair loops — Cluster 1 boundary.
"""

from __future__ import annotations

import inspect
import os
import types
import tempfile
import importlib.util
from dataclasses import dataclass
from typing import Any, Callable, Literal

try:
    import torch as _torch
    _TORCH_DTYPE_MAP = {
        "fp32": _torch.float32,
        "fp16": _torch.float16,
        "bf16": _torch.bfloat16,
    }
except ImportError:
    _torch = None  # type: ignore[assignment]
    _TORCH_DTYPE_MAP = {}


# ---------------------------------------------------------------------------
# Task 4.1: CompileResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompileResult:
    success: bool
    error_type: Literal["CompilationError", "RuntimeError", "SignatureError", None]
    error_msg: str | None
    dtype: str
    n_shapes_tested: int

    def __post_init__(self):
        if self.error_msg is not None and len(self.error_msg) > 500:
            object.__setattr__(self, "error_msg", self.error_msg[:500])


# ---------------------------------------------------------------------------
# Task 4.2: CompileSpec
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompileSpec:
    launcher_name: str
    reference_signature: inspect.Signature
    build_args: Callable[[tuple[int, ...], Any], tuple[list[Any], dict[str, Any]]]


# ---------------------------------------------------------------------------
# Task 4.3: load_generated_module
# ---------------------------------------------------------------------------

def load_generated_module(source: str) -> types.ModuleType:
    """Write source to a temp file and import it as an isolated module.

    Raises ValueError with error_type hint 'SignatureError' on syntax/import
    failures so callers can map the exception to the right taxonomy.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
            tmp.write(source)

        spec = importlib.util.spec_from_file_location("_generated_kernel", tmp_path)
        if spec is None or spec.loader is None:
            raise ValueError("SignatureError: could not create module spec from generated source")

        module = types.ModuleType("_generated_kernel")
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except SyntaxError as exc:
            raise ValueError(f"SignatureError: syntax error in generated source: {exc}") from exc
        except Exception as exc:
            raise ValueError(f"SignatureError: import error in generated source: {exc}") from exc
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return module


# ---------------------------------------------------------------------------
# Task 4.4: validate_signature
# ---------------------------------------------------------------------------

def validate_signature(module: types.ModuleType, spec: CompileSpec) -> str | None:
    """Return an error string if the launcher signature mismatches, else None."""
    launcher = getattr(module, spec.launcher_name, None)
    if launcher is None:
        return f"launcher '{spec.launcher_name}' not found in generated module"

    try:
        actual_sig = inspect.signature(launcher)
    except (TypeError, ValueError) as exc:
        return f"could not inspect signature of '{spec.launcher_name}': {exc}"

    if actual_sig != spec.reference_signature:
        return (
            f"signature mismatch for '{spec.launcher_name}': "
            f"expected {spec.reference_signature}, got {actual_sig}"
        )
    return None


# ---------------------------------------------------------------------------
# Task 4.5: check_compiles
# ---------------------------------------------------------------------------

def check_compiles(
    source: str,
    spec: CompileSpec,
    dtype,
    shapes: list[tuple[int, ...]],
) -> CompileResult:
    """Validate signature then trigger Triton JIT via dummy launches."""
    dtype_str = _dtype_str(dtype)

    # Step 1: load module and validate signature before any compilation attempt.
    try:
        module = load_generated_module(source)
    except ValueError as exc:
        return CompileResult(
            success=False,
            error_type="SignatureError",
            error_msg=str(exc)[:500],
            dtype=dtype_str,
            n_shapes_tested=0,
        )

    sig_error = validate_signature(module, spec)
    if sig_error is not None:
        return CompileResult(
            success=False,
            error_type="SignatureError",
            error_msg=sig_error[:500],
            dtype=dtype_str,
            n_shapes_tested=0,
        )

    launcher = getattr(module, spec.launcher_name)

    # Step 2: dummy launch for each shape to trigger Triton JIT.
    for n_tested, shape in enumerate(shapes):
        try:
            args, kwargs = spec.build_args(shape, dtype)
            launcher(*args, **kwargs)
        except Exception as exc:
            error_type = _classify_error(exc)
            return CompileResult(
                success=False,
                error_type=error_type,
                error_msg=str(exc)[:500],
                dtype=dtype_str,
                n_shapes_tested=n_tested,
            )

    return CompileResult(
        success=True,
        error_type=None,
        error_msg=None,
        dtype=dtype_str,
        n_shapes_tested=len(shapes),
    )


# ---------------------------------------------------------------------------
# Task 4.6: check_compiles_all_dtypes
# ---------------------------------------------------------------------------

def check_compiles_all_dtypes(
    source: str,
    spec: CompileSpec,
    shapes_by_dtype: dict[str, list[tuple[int, ...]]],
) -> list[CompileResult]:
    """Run check_compiles for fp32, fp16, and bf16."""
    results: list[CompileResult] = []
    for dtype_key in ("fp32", "fp16", "bf16"):
        dtype = _TORCH_DTYPE_MAP.get(dtype_key, dtype_key)
        shapes = shapes_by_dtype.get(dtype_key, [])
        results.append(check_compiles(source, spec, dtype, shapes))
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_error(exc: Exception) -> Literal["CompilationError", "RuntimeError"]:
    """Map an exception to the two allowed Triton error taxonomy labels."""
    try:
        import triton.compiler.errors as triton_errors
        if isinstance(exc, triton_errors.CompilationError):
            return "CompilationError"
    except Exception:
        pass
    # Check by name for environments where triton is not installed.
    if type(exc).__name__ == "CompilationError":
        return "CompilationError"
    return "RuntimeError"


def _dtype_str(dtype) -> str:
    name = getattr(dtype, "__name__", None) or str(dtype)
    mapping = {
        "float32": "fp32",
        "float16": "fp16",
        "bfloat16": "bf16",
        "torch.float32": "fp32",
        "torch.float16": "fp16",
        "torch.bfloat16": "bf16",
    }
    return mapping.get(name, name)
