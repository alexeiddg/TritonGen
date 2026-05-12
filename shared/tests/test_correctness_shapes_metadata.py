"""Tests for Phase 0 C2-side correctness-shape metadata."""

from __future__ import annotations

from dataclasses import fields

import pytest

from cluster1.data.kernels import KERNEL_SPECS
from cluster1.data.kernels.spec import KernelSpec
from shared.eval.correctness_shapes import (
    C2_SHAPE_METADATA,
    LOCKED_KERNEL_CLASSES,
    MAX_DIM,
    MAX_ELEMENTS,
    get_shape_metadata,
    iter_shape_metadata,
    validate_metadata_against_cluster1_specs,
)


def test_shape_metadata_matches_locked_three() -> None:
    assert tuple(C2_SHAPE_METADATA) == LOCKED_KERNEL_CLASSES
    assert tuple(KERNEL_SPECS) == LOCKED_KERNEL_CLASSES

    assert get_shape_metadata("elementwise").shape_pattern == "ND"
    assert get_shape_metadata("elementwise").shape_arity == 1
    assert get_shape_metadata("reduction").shape_pattern == "RxC"
    assert get_shape_metadata("reduction").shape_arity == 2
    assert get_shape_metadata("matmul").shape_pattern == "MNK"
    assert get_shape_metadata("matmul").shape_arity == 3


def test_shape_metadata_matches_cluster1_spec_identity() -> None:
    validate_metadata_against_cluster1_specs()

    for kernel_class, spec in KERNEL_SPECS.items():
        metadata = get_shape_metadata(kernel_class)
        assert metadata.kernel_name == spec.name
        assert metadata.dataset_problem_id == spec.dataset_problem_id


def test_iter_shape_metadata_uses_locked_order() -> None:
    assert tuple(item.kernel_class for item in iter_shape_metadata()) == LOCKED_KERNEL_CLASSES


def test_unknown_shape_metadata_rejected() -> None:
    with pytest.raises(KeyError, match="unsupported C2 kernel_class"):
        get_shape_metadata("fused")


def test_phase0_does_not_add_kernel_spec_fields() -> None:
    assert [field.name for field in fields(KernelSpec)] == [
        "name",
        "kernel_class",
        "launcher_name",
        "reference_signature",
        "compile_spec",
        "prompt_template",
        "autotune_configs",
        "shapes_by_dtype",
        "dataset_id",
        "dataset_problem_id",
        "reference_code",
    ]


def test_phase0_memory_caps_are_metadata_only() -> None:
    assert MAX_DIM == 16384
    assert MAX_ELEMENTS == 2**24
