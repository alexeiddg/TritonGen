"""Per-operation numeric tolerances from the evaluation contract."""

from __future__ import annotations

from typing import TypedDict


class Tolerance(TypedDict):
    atol: float
    rtol: float
    reference_variance_max_abs: float | None
    reference_variance_max_rel: float | None


TOLERANCE_TABLE: dict[str, dict[str, Tolerance]] = {
    "elementwise": {
        "fp32": {
            "atol": 1e-5,
            "rtol": 1e-5,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "fp16": {
            "atol": 1e-3,
            "rtol": 1e-3,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "bf16": {
            "atol": 1e-3,
            "rtol": 1e-3,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
    },
    "reduction": {
        "fp32": {
            "atol": 1e-4,
            "rtol": 1e-4,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "fp16": {
            "atol": 1e-2,
            "rtol": 1e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "bf16": {
            "atol": 1e-2,
            "rtol": 1e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
    },
    "matmul": {
        "fp32": {
            "atol": 1e-3,
            "rtol": 1e-3,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "fp16": {
            "atol": 5e-2,
            "rtol": 5e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "bf16": {
            "atol": 5e-2,
            "rtol": 5e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
    },
    "fused": {
        "fp32": {
            "atol": 1e-3,
            "rtol": 1e-3,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "fp16": {
            "atol": 5e-2,
            "rtol": 5e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
        "bf16": {
            "atol": 5e-2,
            "rtol": 5e-2,
            "reference_variance_max_abs": None,
            "reference_variance_max_rel": None,
        },
    },
}

DTYPE_ALIASES = {
    "float32": "fp32",
    "float16": "fp16",
    "bfloat16": "bf16",
}


def get_tolerances(kernel_class: str, dtype: str) -> Tolerance:
    """Return tolerance values for a kernel class and dtype.

    Unknown kernel classes and dtypes raise ``KeyError``. There is no global
    silent fallback because the contract requires per-operation tolerances.
    """

    class_table = TOLERANCE_TABLE[kernel_class]
    dtype_key = DTYPE_ALIASES.get(dtype, dtype)
    return dict(class_table[dtype_key])  # type: ignore[return-value]
