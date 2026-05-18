"""Cluster 2 correctness-shape metadata and generators.

The public surface is intentionally limited to the three locked KernelBench
archetypes and their C2-side shape patterns: ``ND``, ``RxC``, and ``MNK``.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from cluster2.constants import DTYPE_NAMES


ShapePattern = Literal["ND", "RxC", "MNK"]
ShapeSplit = Literal["repair", "eval"]
KernelClass = Literal["elementwise", "reduction", "matmul"]
Shape = tuple[int, ...]

MAX_DIM = 16384
MAX_ELEMENTS = 2**24
LOCKED_KERNEL_CLASSES: tuple[KernelClass, ...] = ("elementwise", "reduction", "matmul")
LOCKED_KERNEL_NAMES: tuple[str, ...] = ("relu", "softmax", "gemm")
SHAPE_SPLITS: tuple[ShapeSplit, ...] = ("repair", "eval")
DEFAULT_SHAPES_PER_SPLIT = 6


@dataclass(frozen=True)
class CorrectnessShapeMetadata:
    kernel_class: KernelClass
    kernel_name: str
    dataset_problem_id: int
    shape_arity: int
    shape_pattern: ShapePattern


@dataclass(frozen=True)
class CorrectnessShapeSets:
    """Deterministic repair/eval shapes for one locked kernel/dtype/seed cell."""

    kernel_class: KernelClass
    kernel_name: str
    dtype: str
    base_seed: int
    repair_shape_set: tuple[Shape, ...]
    eval_shape_set: tuple[Shape, ...]

    def __post_init__(self) -> None:
        if set(self.repair_shape_set) & set(self.eval_shape_set):
            raise ValueError("repair_shape_set and eval_shape_set must be disjoint")


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

KERNEL_NAME_TO_CLASS: dict[str, KernelClass] = {
    metadata.kernel_name: kernel_class
    for kernel_class, metadata in C2_SHAPE_METADATA.items()
}

_ANCHOR_SHAPES: dict[ShapePattern, dict[ShapeSplit, tuple[Shape, ...]]] = {
    "ND": {
        "repair": ((1,), (32,), (100,), (1024,), (3, 257)),
        "eval": ((2,), (33,), (257,), (4096,), (5, 129)),
    },
    "RxC": {
        "repair": ((1, 64), (16, 64), (33, 100), (128, 1001), (16384, 1)),
        "eval": ((2, 65), (17, 63), (64, 257), (129, 1000), (1, 16384)),
    },
    "MNK": {
        "repair": (
            (1, 1, 1),
            (24, 24, 24),
            (48, 48, 48),
            (128, 128, 64),
            (16384, 1, 1),
        ),
        "eval": (
            (2, 2, 2),
            (25, 25, 25),
            (64, 32, 128),
            (100, 100, 100),
            (1, 16384, 1),
        ),
    },
}

_COMPILE_SHAPE_ANCHORS: dict[KernelClass, tuple[Shape, ...]] = {
    # Elementwise compile probes cover the common 1D launcher cases and the
    # rank edge shared with C2 correctness anchors. The selected anchors cover
    # smaller-than-block work, non-power-of-two and non-divisible lengths,
    # a power-of-two length, and both repair/eval 2D edge shapes without
    # reintroducing the old oversized C1-only tensors.
    "elementwise": ((32,), (100,), (1024,), (3, 257), (5, 129)),
    # Reduction compile probes exercise a small power-of-two row/column case,
    # non-power-of-two rows and columns, a non-divisible long-column case, and
    # both row-major and column-major cap edges under the shared MAX_DIM and
    # MAX_ELEMENTS policy.
    "reduction": ((16, 64), (33, 100), (128, 1001), (16384, 1), (1, 16384)),
    # Matmul compile probes cover below-block square work, non-power-of-two
    # square work, a rectangular power-of-two K edge, an irregular square case,
    # and a shared cap-edge case. Larger stress shapes require an explicit
    # compile-only cap policy instead of bypassing the C2 caps here.
    "matmul": (
        (24, 24, 24),
        (48, 48, 48),
        (128, 128, 64),
        (100, 100, 100),
        (16384, 1, 1),
    ),
}

_EDGE_DIMS: tuple[int, ...] = (
    1,
    2,
    3,
    16,
    24,
    31,
    32,
    33,
    48,
    63,
    64,
    65,
    100,
    127,
    128,
    129,
    257,
    512,
    1000,
    1001,
    1024,
    2048,
    4096,
    8192,
    16384,
)


def get_shape_metadata(kernel_class: str) -> CorrectnessShapeMetadata:
    """Return C2-side shape metadata for one locked Cluster 1 kernel class."""

    try:
        return C2_SHAPE_METADATA[kernel_class]  # type: ignore[index]
    except KeyError as exc:
        allowed = ", ".join(LOCKED_KERNEL_CLASSES)
        raise KeyError(f"unsupported C2 kernel_class {kernel_class!r}; allowed: {allowed}") from exc


def get_shape_metadata_by_kernel_name(kernel_name: str) -> CorrectnessShapeMetadata:
    """Return C2-side shape metadata for one locked KernelBench kernel name."""

    try:
        kernel_class = KERNEL_NAME_TO_CLASS[kernel_name]
    except KeyError as exc:
        allowed = ", ".join(LOCKED_KERNEL_NAMES)
        raise KeyError(f"unsupported C2 kernel_name {kernel_name!r}; allowed: {allowed}") from exc
    return get_shape_metadata(kernel_class)


def iter_shape_metadata() -> tuple[CorrectnessShapeMetadata, ...]:
    """Return metadata in locked ``KERNEL_SPECS`` order."""

    return tuple(C2_SHAPE_METADATA[kernel_class] for kernel_class in LOCKED_KERNEL_CLASSES)


def generate_correctness_shape_sets(
    kernel_class: str,
    dtype: str,
    *,
    base_seed: int,
    shapes_per_split: int = DEFAULT_SHAPES_PER_SPLIT,
) -> CorrectnessShapeSets:
    """Generate deterministic, disjoint repair/eval shape sets.

    Shape generation is scoped to the locked ``kernel_class`` routes and includes
    ``dtype`` in the seed derivation so dtype-specific cells are reproducible.
    """

    metadata = get_shape_metadata(kernel_class)
    dtype = _require_dtype(dtype)
    base_seed = _require_int(base_seed, "base_seed")
    shapes_per_split = _require_positive_int(shapes_per_split, "shapes_per_split")

    repair_shapes = generate_shape_set(
        metadata.kernel_class,
        dtype,
        base_seed=base_seed,
        split="repair",
        count=shapes_per_split,
    )
    eval_shapes = generate_shape_set(
        metadata.kernel_class,
        dtype,
        base_seed=base_seed,
        split="eval",
        count=shapes_per_split,
        exclude=repair_shapes,
    )
    return CorrectnessShapeSets(
        kernel_class=metadata.kernel_class,
        kernel_name=metadata.kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        repair_shape_set=repair_shapes,
        eval_shape_set=eval_shapes,
    )


def get_compile_shapes(kernel_class: str, dtype: str) -> tuple[Shape, ...]:
    """Return deterministic C1 compile probes from the shared shape schema."""

    metadata = get_shape_metadata(kernel_class)
    _require_dtype(dtype)
    return tuple(
        validate_shape_for_kernel(metadata.kernel_class, shape)
        for shape in _COMPILE_SHAPE_ANCHORS[metadata.kernel_class]
    )


def generate_shape_set(
    kernel_class: str,
    dtype: str,
    *,
    base_seed: int,
    split: ShapeSplit,
    count: int = DEFAULT_SHAPES_PER_SPLIT,
    exclude: Iterable[Sequence[int]] = (),
) -> tuple[Shape, ...]:
    """Generate one deterministic shape split for a locked kernel class."""

    metadata = get_shape_metadata(kernel_class)
    dtype = _require_dtype(dtype)
    base_seed = _require_int(base_seed, "base_seed")
    count = _require_positive_int(count, "count")
    split = _require_split(split)
    excluded = {_normalize_shape(shape) for shape in exclude}

    rng = random.Random(
        derive_deterministic_seed(
            "correctness_shapes",
            metadata.kernel_class,
            metadata.kernel_name,
            metadata.shape_pattern,
            dtype,
            base_seed,
            split,
        )
    )

    shapes: list[Shape] = []
    for shape in _ANCHOR_SHAPES[metadata.shape_pattern][split]:
        _append_shape_if_valid(shapes, shape, metadata.shape_pattern, excluded, count)
    while len(shapes) < count:
        shape = _random_shape(metadata.shape_pattern, rng)
        _append_shape_if_valid(shapes, shape, metadata.shape_pattern, excluded, count)

    return tuple(shapes)


def validate_shape_for_kernel(kernel_class: str, shape: Sequence[int]) -> Shape:
    """Validate a generated shape against the locked kernel route and caps."""

    metadata = get_shape_metadata(kernel_class)
    return validate_shape_for_pattern(metadata.shape_pattern, shape)


def validate_shape_for_kernel_name(kernel_name: str, shape: Sequence[int]) -> Shape:
    """Validate a generated shape against the locked kernel-name route."""

    metadata = get_shape_metadata_by_kernel_name(kernel_name)
    return validate_shape_for_pattern(metadata.shape_pattern, shape)


def validate_shape_for_pattern(pattern: ShapePattern, shape: Sequence[int]) -> Shape:
    """Validate one shape for ``ND``, ``RxC``, or ``MNK``."""

    normalized = _normalize_shape(shape)
    if pattern == "ND":
        if len(normalized) < 1:
            raise ValueError("ND shapes must have at least one dimension")
    elif pattern == "RxC":
        if len(normalized) != 2:
            raise ValueError("RxC shapes must have exactly two dimensions")
    elif pattern == "MNK":
        if len(normalized) != 3:
            raise ValueError("MNK shapes must have exactly three dimensions")
    else:
        raise ValueError(f"unsupported shape pattern {pattern!r}")

    if max(normalized) > MAX_DIM:
        raise ValueError(f"shape dimension exceeds MAX_DIM={MAX_DIM}: {normalized!r}")
    if shape_num_elements(normalized) > MAX_ELEMENTS:
        raise ValueError(
            f"shape element product exceeds MAX_ELEMENTS={MAX_ELEMENTS}: {normalized!r}"
        )
    return normalized


def shape_num_elements(shape: Sequence[int]) -> int:
    """Return the product of a normalized shape tuple."""

    return math.prod(_normalize_shape(shape))


def derive_deterministic_seed(namespace: str, *components: Any) -> int:
    """Derive a stable 64-bit seed from JSON-serializable components."""

    if not isinstance(namespace, str) or not namespace:
        raise ValueError("namespace must be a non-empty string")
    payload = json.dumps(
        {
            "namespace": namespace,
            "components": [_json_safe_component(component) for component in components],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


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


def _append_shape_if_valid(
    shapes: list[Shape],
    shape: Shape,
    pattern: ShapePattern,
    excluded: set[Shape],
    count: int,
) -> None:
    if len(shapes) >= count:
        return
    validated = validate_shape_for_pattern(pattern, shape)
    if validated in excluded or validated in shapes:
        return
    shapes.append(validated)


def _random_shape(pattern: ShapePattern, rng: random.Random) -> Shape:
    if pattern == "ND":
        return _random_nd_shape(rng)
    if pattern == "RxC":
        return _random_rxc_shape(rng)
    if pattern == "MNK":
        return _random_mnk_shape(rng)
    raise ValueError(f"unsupported shape pattern {pattern!r}")


def _random_nd_shape(rng: random.Random) -> Shape:
    rank = rng.choice((1, 1, 2, 2, 3, 4))
    remaining = MAX_ELEMENTS
    dims: list[int] = []
    for _ in range(rank):
        dim = _bounded_dim(rng, min(MAX_DIM, remaining))
        dims.append(dim)
        remaining = max(1, remaining // dim)
    return tuple(dims)


def _random_rxc_shape(rng: random.Random) -> Shape:
    rows = _bounded_dim(rng, MAX_DIM)
    cols = _bounded_dim(rng, min(MAX_DIM, MAX_ELEMENTS // rows))
    return rows, cols


def _random_mnk_shape(rng: random.Random) -> Shape:
    m = _bounded_dim(rng, MAX_DIM)
    n = _bounded_dim(rng, min(MAX_DIM, MAX_ELEMENTS // m))
    k = _bounded_dim(rng, min(MAX_DIM, MAX_ELEMENTS // (m * n)))
    return m, n, k


def _bounded_dim(rng: random.Random, upper_bound: int) -> int:
    upper_bound = max(1, min(MAX_DIM, upper_bound))
    edge_choices = [dim for dim in _EDGE_DIMS if dim <= upper_bound]
    if edge_choices and rng.random() < 0.7:
        return rng.choice(edge_choices)
    return rng.randint(1, upper_bound)


def _require_dtype(dtype: str) -> str:
    if not isinstance(dtype, str):
        raise TypeError("dtype must be a string")
    if dtype not in DTYPE_NAMES:
        raise ValueError(
            f"unsupported dtype {dtype!r}; expected one of: {', '.join(DTYPE_NAMES)}"
        )
    return dtype


def _require_split(split: ShapeSplit) -> ShapeSplit:
    if split not in SHAPE_SPLITS:
        raise ValueError(f"unsupported shape split {split!r}; expected one of: repair, eval")
    return split


def _require_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    return value


def _require_positive_int(value: int, field_name: str) -> int:
    value = _require_int(value, field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _normalize_shape(shape: Sequence[int]) -> Shape:
    if isinstance(shape, (str, bytes)):
        raise TypeError("shape must be a sequence of positive integers")
    normalized = tuple(shape)
    if not normalized:
        raise ValueError("shape must not be empty")
    for dim in normalized:
        if not isinstance(dim, int) or isinstance(dim, bool):
            raise TypeError("shape dimensions must be integers")
        if dim <= 0:
            raise ValueError("shape dimensions must be positive")
    return normalized


def _json_safe_component(component: Any) -> Any:
    if isinstance(component, tuple):
        return [_json_safe_component(item) for item in component]
    if isinstance(component, list):
        return [_json_safe_component(item) for item in component]
    if isinstance(component, dict):
        return {
            str(key): _json_safe_component(value)
            for key, value in sorted(component.items(), key=lambda item: str(item[0]))
        }
    if isinstance(component, (str, int, float, bool)) or component is None:
        return component
    return repr(component)
