"""Shared Level 1 compile adapter.

This module is intentionally a thin wrapper around the existing Cluster 1
compile gate. It does not import torch, triton, or Cluster 1 compile modules
at module import time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


_DEFAULT_DTYPES: tuple[str, ...] = ("fp32", "fp16", "bf16")
_MAX_ERROR_CHARS = 500


@dataclass(frozen=True)
class Level1CompileResult:
    """Shared Level 1 compile result.

    Unexpected delegate exceptions are returned as ``UnknownError`` so shared
    evaluation callers receive a structured result. Routine signature,
    compilation, and runtime failures are classified by the existing Cluster 1
    compile gate.
    """

    compile_success: bool
    compile_error: str | None
    compile_error_type: str | None
    compile_results_by_dtype: dict[str, bool]
    n_shapes_tested: int


def check_compile_level1(source: str, kernel_spec: Any) -> Level1CompileResult:
    """Run the Level 1 compile gate using existing Cluster 1 semantics."""

    try:
        compile_spec = _get_required_field(kernel_spec, "compile_spec")
        shapes_by_dtype = _get_required_field(kernel_spec, "shapes_by_dtype")

        # Lazy import preserves the shared module import contract for machines
        # without torch, triton, CUDA, or the Cluster 1 GPU stack installed.
        from cluster1.validation.compile_check import check_compiles_all_dtypes

        compile_results = check_compiles_all_dtypes(
            source,
            compile_spec,
            shapes_by_dtype,
        )
    except Exception as exc:
        return Level1CompileResult(
            compile_success=False,
            compile_error=_truncate_error(f"check_compiles_all_dtypes raised: {exc}"),
            compile_error_type="UnknownError",
            compile_results_by_dtype=_false_dtype_results(kernel_spec),
            n_shapes_tested=0,
        )

    return _from_cluster1_results(compile_results)


def _from_cluster1_results(compile_results: Any) -> Level1CompileResult:
    results = list(compile_results)
    if not results:
        return Level1CompileResult(
            compile_success=False,
            compile_error="check_compiles_all_dtypes returned no compile results",
            compile_error_type="UnknownError",
            compile_results_by_dtype={dtype: False for dtype in _DEFAULT_DTYPES},
            n_shapes_tested=0,
        )

    compile_results_by_dtype = {
        str(_get_field(result, "dtype")): bool(_get_field(result, "success"))
        for result in results
    }
    first_failure = next(
        (result for result in results if not bool(_get_field(result, "success"))),
        None,
    )

    return Level1CompileResult(
        compile_success=all(bool(_get_field(result, "success")) for result in results),
        compile_error=(
            _optional_error(_get_field(first_failure, "error_msg"))
            if first_failure is not None
            else None
        ),
        compile_error_type=(
            _optional_error(_get_field(first_failure, "error_type"))
            if first_failure is not None
            else None
        ),
        compile_results_by_dtype=compile_results_by_dtype,
        n_shapes_tested=sum(
            _coerce_int(_get_field(result, "n_shapes_tested")) for result in results
        ),
    )


def _false_dtype_results(kernel_spec: Any) -> dict[str, bool]:
    try:
        shapes_by_dtype = _get_field(kernel_spec, "shapes_by_dtype")
    except Exception:
        shapes_by_dtype = None
    keys: list[str] = list(_DEFAULT_DTYPES)
    if isinstance(shapes_by_dtype, Mapping):
        keys.extend(str(key) for key in shapes_by_dtype if str(key) not in keys)
    return {key: False for key in keys}


def _get_required_field(obj: Any, name: str) -> Any:
    value = _get_field(obj, name)
    if value is None:
        raise ValueError(f"kernel_spec missing required field {name!r}")
    return value


def _get_field(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _optional_error(value: Any) -> str | None:
    if value is None:
        return None
    return _truncate_error(str(value))


def _truncate_error(error: str) -> str:
    return error[:_MAX_ERROR_CHARS]


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
