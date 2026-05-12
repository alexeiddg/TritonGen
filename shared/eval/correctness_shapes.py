"""Cluster 2 correctness-shape metadata for the locked KernelBench archetypes.

Phase 0 owns only metadata. Procedural repair/eval shape generation is added in
a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ShapePattern = Literal["ND", "RxC", "MNK"]
KernelClass = Literal["elementwise", "reduction", "matmul"]

MAX_DIM = 16384
MAX_ELEMENTS = 2**24
LOCKED_KERNEL_CLASSES: tuple[KernelClass, ...] = ("elementwise", "reduction", "matmul")


@dataclass(frozen=True)
class CorrectnessShapeMetadata:
    kernel_class: KernelClass
    kernel_name: str
    dataset_problem_id: int
    shape_arity: int
    shape_pattern: ShapePattern


C2_SHAPE_METADATA: dict[KernelClass, CorrectnessShapeMetadata] = {
    "elementwise": CorrectnessShapeMetadata(
        kernel_class="elementwise",
        kernel_name="relu",
        dataset_problem_id=19,
        shape_arity=1,
        shape_pattern="ND",
    ),
    "reduction": CorrectnessShapeMetadata(
        kernel_class="reduction",
        kernel_name="softmax",
        dataset_problem_id=23,
        shape_arity=2,
        shape_pattern="RxC",
    ),
    "matmul": CorrectnessShapeMetadata(
        kernel_class="matmul",
        kernel_name="gemm",
        dataset_problem_id=1,
        shape_arity=3,
        shape_pattern="MNK",
    ),
}


def get_shape_metadata(kernel_class: str) -> CorrectnessShapeMetadata:
    """Return C2-side shape metadata for one locked Cluster 1 kernel class."""

    try:
        return C2_SHAPE_METADATA[kernel_class]  # type: ignore[index]
    except KeyError as exc:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise KeyError(f"unsupported C2 kernel_class {kernel_class!r}; allowed: {allowed}") from exc


def iter_shape_metadata() -> tuple[CorrectnessShapeMetadata, ...]:
    """Return metadata in locked ``KERNEL_SPECS`` order."""

    return tuple(C2_SHAPE_METADATA[kernel_class] for kernel_class in LOCKED_KERNEL_CLASSES)


def validate_metadata_against_cluster1_specs() -> None:
    """Assert C2 metadata matches the frozen three Cluster 1 kernel specs."""

    from cluster1.data.kernels import KERNEL_SPECS

    if tuple(KERNEL_SPECS) != LOCKED_KERNEL_CLASSES:
        raise ValueError("Cluster 1 KERNEL_SPECS order does not match C2 metadata")

    for kernel_class, spec in KERNEL_SPECS.items():
        metadata = get_shape_metadata(kernel_class)
        if metadata.kernel_name != spec.name:
            raise ValueError(f"{kernel_class} kernel name mismatch")
        if metadata.dataset_problem_id != spec.dataset_problem_id:
            raise ValueError(f"{kernel_class} dataset problem id mismatch")
