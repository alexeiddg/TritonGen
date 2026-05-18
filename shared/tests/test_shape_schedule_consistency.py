"""Cross-cluster checks for shared compile-shape scheduling."""

from __future__ import annotations

import math

import pytest

from cluster1.data.kernels import KERNEL_SPECS
from cluster2.constants import DTYPE_NAMES
from shared.eval.correctness_shapes import (
    LOCKED_KERNEL_CLASSES,
    MAX_DIM,
    MAX_ELEMENTS,
    generate_shape_set,
    get_compile_shapes,
    get_shape_metadata,
    validate_shape_for_kernel,
)


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
@pytest.mark.parametrize("dtype", DTYPE_NAMES)
def test_compile_shapes_are_valid_under_shared_caps(
    kernel_class: str, dtype: str
) -> None:
    compile_shapes = get_compile_shapes(kernel_class, dtype)

    assert compile_shapes
    for shape in compile_shapes:
        assert validate_shape_for_kernel(kernel_class, shape) == shape
        assert max(shape) <= MAX_DIM
        assert math.prod(shape) <= MAX_ELEMENTS


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
def test_compile_shapes_are_dtype_stable(kernel_class: str) -> None:
    fp32_shapes = get_compile_shapes(kernel_class, "fp32")

    for dtype in DTYPE_NAMES:
        assert get_compile_shapes(kernel_class, dtype) == fp32_shapes


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
@pytest.mark.parametrize("dtype", DTYPE_NAMES)
def test_compile_shapes_are_from_correctness_anchor_vocabulary(
    kernel_class: str, dtype: str
) -> None:
    metadata = get_shape_metadata(kernel_class)
    anchor_union = set(
        generate_shape_set(kernel_class, dtype, base_seed=0, split="repair", count=5)
        + generate_shape_set(kernel_class, dtype, base_seed=0, split="eval", count=5)
    )

    assert set(get_compile_shapes(metadata.kernel_class, dtype)).issubset(anchor_union)


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
@pytest.mark.parametrize("dtype", DTYPE_NAMES)
def test_cluster1_kernel_specs_use_shared_compile_shapes(
    kernel_class: str, dtype: str
) -> None:
    spec = KERNEL_SPECS[kernel_class]

    assert spec.shapes_by_dtype[dtype] == list(get_compile_shapes(kernel_class, dtype))
