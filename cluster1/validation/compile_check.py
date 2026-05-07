"""Compilation validation gate for Cluster 1.

Performs actual Triton JIT compilation via dummy kernel launches.
Cluster 1 stops at compile acceptance and does not add later-cluster logic.
"""

from __future__ import annotations

import atexit
import importlib.util
import inspect
import os
import sys
import tempfile
import types
from dataclasses import dataclass
from typing import Any, Callable, Literal

from cluster1.results.dataclass import CompileErrorType

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
    error_type: CompileErrorType
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

    Triton JIT may inspect the decorated kernel's Python source lazily on the
    first dummy launch, so the backing file must stay on disk after import.

    CLEANUP CONTRACT: every successful call here registers an ``atexit``
    cleanup. Callers that use ``load_generated_module`` directly MUST invoke
    ``cleanup_generated_module(module)`` — preferably in a ``finally`` block
    — once Triton has finished any lazy source inspection. Otherwise the
    ``atexit`` registry grows monotonically and temp ``.py`` files leak until
    interpreter shutdown. ``check_compiles`` already does this for you.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".py")
    module_name = f"_generated_kernel_{os.path.basename(tmp_path).replace('.', '_')}"
    cleanup = _GeneratedModuleCleanup(module_name, tmp_path)
    atexit.register(cleanup)

    with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
        tmp.write(source)

    spec = importlib.util.spec_from_file_location(module_name, tmp_path)
    if spec is None or spec.loader is None:
        _run_generated_module_cleanup(cleanup)
        raise ValueError("SignatureError: could not create module spec from generated source")

    module = importlib.util.module_from_spec(spec)
    setattr(module, "__tritongen_cleanup__", cleanup)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except SyntaxError as exc:
        _run_generated_module_cleanup(cleanup)
        raise ValueError(f"SignatureError: syntax error in generated source: {exc}") from exc
    except Exception as exc:
        _run_generated_module_cleanup(cleanup)
        raise ValueError(f"SignatureError: import error in generated source: {exc}") from exc

    return module


class _GeneratedModuleCleanup:
    def __init__(self, module_name: str, source_path: str) -> None:
        self.module_name = module_name
        self.source_path = source_path
        self.active = True

    def __call__(self) -> None:
        if not self.active:
            return
        self.active = False
        _cleanup_generated_module(self.module_name, self.source_path)


def cleanup_generated_module(module: types.ModuleType) -> None:
    """Remove a generated module and its temp source file."""
    cleanup = getattr(module, "__tritongen_cleanup__", None)
    if callable(cleanup):
        _run_generated_module_cleanup(cleanup)
        try:
            atexit.unregister(cleanup)
        except Exception:
            pass
        return

    source_path = getattr(module, "__file__", "")
    _cleanup_generated_module(module.__name__, source_path)


def _run_generated_module_cleanup(cleanup: Callable[[], None]) -> None:
    cleanup()
    try:
        atexit.unregister(cleanup)
    except Exception:
        pass


def _cleanup_generated_module(module_name: str, source_path: str) -> None:
    sys.modules.pop(module_name, None)
    try:
        os.unlink(source_path)
    except OSError:
        pass


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
    module: types.ModuleType | None = None

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

    try:
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
    finally:
        cleanup_generated_module(module)


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

def _classify_error(exc: Exception) -> CompileErrorType:
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
