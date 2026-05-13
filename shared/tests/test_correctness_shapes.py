"""Tests for Phase 2 procedural correctness shape generation."""

from __future__ import annotations

import math

import pytest

from shared.eval.correctness_shapes import (
    DEFAULT_SHAPES_PER_SPLIT,
    LOCKED_KERNEL_CLASSES,
    MAX_DIM,
    MAX_ELEMENTS,
    CorrectnessShapeSets,
    derive_deterministic_seed,
    generate_correctness_shape_sets,
    get_shape_metadata,
    get_shape_metadata_by_kernel_name,
    validate_shape_for_kernel,
)


def test_repair_shapes_are_deterministic() -> None:
    first = generate_correctness_shape_sets("elementwise", "fp32", base_seed=1234)
    second = generate_correctness_shape_sets("elementwise", "fp32", base_seed=1234)

    assert first.repair_shape_set == second.repair_shape_set


def test_eval_shapes_are_deterministic() -> None:
    first = generate_correctness_shape_sets("reduction", "bf16", base_seed=1234)
    second = generate_correctness_shape_sets("reduction", "bf16", base_seed=1234)

    assert first.eval_shape_set == second.eval_shape_set


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
def test_repair_and_eval_shape_sets_are_disjoint(kernel_class: str) -> None:
    shape_sets = generate_correctness_shape_sets(kernel_class, "fp16", base_seed=55)

    assert len(shape_sets.repair_shape_set) == DEFAULT_SHAPES_PER_SPLIT
    assert len(shape_sets.eval_shape_set) == DEFAULT_SHAPES_PER_SPLIT
    assert set(shape_sets.repair_shape_set).isdisjoint(shape_sets.eval_shape_set)


def test_shape_set_dataclass_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="must be disjoint"):
        CorrectnessShapeSets(
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            base_seed=1,
            repair_shape_set=((32,),),
            eval_shape_set=((32,),),
        )


def test_nd_shapes_are_valid() -> None:
    shape_sets = generate_correctness_shape_sets("elementwise", "fp32", base_seed=7)
    all_shapes = shape_sets.repair_shape_set + shape_sets.eval_shape_set

    assert get_shape_metadata("elementwise").shape_pattern == "ND"
    assert all(len(shape) >= 1 for shape in all_shapes)
    assert any(len(shape) > 1 for shape in all_shapes)
    for shape in all_shapes:
        assert validate_shape_for_kernel("elementwise", shape) == shape


def test_rxc_shapes_are_valid() -> None:
    shape_sets = generate_correctness_shape_sets("reduction", "fp32", base_seed=7)
    all_shapes = shape_sets.repair_shape_set + shape_sets.eval_shape_set

    assert get_shape_metadata("reduction").shape_pattern == "RxC"
    assert all(len(shape) == 2 for shape in all_shapes)
    for shape in all_shapes:
        assert validate_shape_for_kernel("reduction", shape) == shape


def test_mnk_shapes_are_valid() -> None:
    shape_sets = generate_correctness_shape_sets("matmul", "fp32", base_seed=7)
    all_shapes = shape_sets.repair_shape_set + shape_sets.eval_shape_set

    assert get_shape_metadata("matmul").shape_pattern == "MNK"
    assert all(len(shape) == 3 for shape in all_shapes)
    for shape in all_shapes:
        assert validate_shape_for_kernel("matmul", shape) == shape


@pytest.mark.parametrize("kernel_class", LOCKED_KERNEL_CLASSES)
@pytest.mark.parametrize("dtype", ["fp32", "fp16", "bf16"])
def test_max_dim_and_max_elements_are_respected(kernel_class: str, dtype: str) -> None:
    shape_sets = generate_correctness_shape_sets(kernel_class, dtype, base_seed=999)

    for shape in shape_sets.repair_shape_set + shape_sets.eval_shape_set:
        assert max(shape) <= MAX_DIM
        assert math.prod(shape) <= MAX_ELEMENTS


def test_shape_caps_reject_oversized_shapes() -> None:
    with pytest.raises(ValueError, match="MAX_DIM"):
        validate_shape_for_kernel("elementwise", (MAX_DIM + 1,))
    with pytest.raises(ValueError, match="MAX_ELEMENTS"):
        validate_shape_for_kernel("reduction", (MAX_DIM, MAX_DIM))


def test_dtype_participates_in_seed_derivation() -> None:
    fp32_seed = derive_deterministic_seed(
        "correctness_shapes",
        "elementwise",
        "relu",
        "ND",
        "fp32",
        99,
        "repair",
    )
    fp16_seed = derive_deterministic_seed(
        "correctness_shapes",
        "elementwise",
        "relu",
        "ND",
        "fp16",
        99,
        "repair",
    )

    assert fp32_seed != fp16_seed


def test_locked_kernel_name_routing_is_explicit() -> None:
    assert get_shape_metadata_by_kernel_name("relu").kernel_class == "elementwise"
    assert get_shape_metadata_by_kernel_name("softmax").kernel_class == "reduction"
    assert get_shape_metadata_by_kernel_name("gemm").kernel_class == "matmul"
    with pytest.raises(KeyError, match="unsupported C2 kernel_name"):
        get_shape_metadata_by_kernel_name("layernorm")
