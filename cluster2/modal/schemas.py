"""Cluster 2 Modal schema contracts.

These schemas are intentionally isolated from ``shared.modal_harness.schemas``.
They define the Cluster 2 request/result wire contract only; no Modal runtime,
generation, correctness execution, repair loop, or orchestration code lives in
this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from cluster2.constants import (
    CLUSTER2_CONDITIONS,
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_C2_MODAL_GENERATION_GPU,
    DTYPE_NAMES,
    GENERATED_SOURCE_CLASS,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
    generation_mode_for_condition,
    normalize_cluster2_condition,
    require_generated_condition,
    source_class_for_condition,
)


C2_MODAL_SCHEMA_VERSION = 1
C2_MODAL_SURFACE_PHASE = "phase0_scaffold"

C2KernelClass: TypeAlias = Literal["elementwise", "reduction", "matmul"]
C2DTypeName: TypeAlias = Literal["fp32", "fp16", "bf16"]

KERNEL_CLASSES: tuple[C2KernelClass, ...] = ("elementwise", "reduction", "matmul")
KERNEL_NAME_BY_CLASS: dict[str, str] = {
    "elementwise": "relu",
    "reduction": "softmax",
    "matmul": "gemm",
}
FORBIDDEN_REQUEST_RESULT_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "benchmark_metadata",
        "compile_time_ms",
        "compile_time_s",
        "eager_time_ms",
        "elapsed_ms",
        "elapsed_s",
        "generation_time_s",
        "input_token_count",
        "kernel_time_iqr_ms",
        "kernel_time_ms",
        "latency_ms",
        "output_token_count",
        "profile",
        "profiling",
        "speedup",
        "speedup_vs_compile",
        "speedup_vs_eager",
        "throughput",
        "timing",
        "tokens_generated",
        "tokens_input",
        "tokens_output",
    }
)


class _StrictC2Schema(BaseModel):
    """Base schema: deterministic, JSON-serializable, and no silent extras."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )


class EvalIdentity(_StrictC2Schema):
    """Stable identity and routing sidecar for one Cluster 2 evaluation row."""

    run_id: str
    condition: str
    source_class: str
    generation_mode: str
    kernel_class: str
    kernel_name: str
    dtype: str
    sample_index: int
    base_seed: int
    attempt_index: int = 0

    @field_validator(
        "run_id",
        "condition",
        "source_class",
        "generation_mode",
        "kernel_class",
        "kernel_name",
        "dtype",
    )
    @classmethod
    def _non_empty_strings(cls, value: str) -> str:
        return _require_non_empty_string(value)

    @field_validator("condition")
    @classmethod
    def _validate_condition(cls, value: str) -> str:
        return normalize_cluster2_condition(value)

    @field_validator("kernel_class")
    @classmethod
    def _validate_kernel_class(cls, value: str) -> str:
        return _require_member(value, KERNEL_CLASSES, "kernel_class")

    @field_validator("dtype")
    @classmethod
    def _validate_dtype(cls, value: str) -> str:
        return _require_member(value, DTYPE_NAMES, "dtype")

    @field_validator("sample_index", "base_seed", "attempt_index")
    @classmethod
    def _validate_non_negative_ints(cls, value: int) -> int:
        return _require_non_negative_int(value)

    @model_validator(mode="after")
    def _validate_condition_routing(self) -> "EvalIdentity":
        expected_source_class = source_class_for_condition(self.condition)
        if self.source_class != expected_source_class:
            raise ValueError(
                f"condition {self.condition!r} requires source_class "
                f"{expected_source_class!r}; got {self.source_class!r}"
            )

        expected_generation_mode = generation_mode_for_condition(self.condition)
        if self.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {self.condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.generation_mode!r}"
            )
        expected_kernel_name = KERNEL_NAME_BY_CLASS[self.kernel_class]
        if self.kernel_name != expected_kernel_name:
            raise ValueError(
                f"kernel_class {self.kernel_class!r} requires kernel_name "
                f"{expected_kernel_name!r}; got {self.kernel_name!r}"
            )
        return self


class RemoteC2GenerationRequest(_StrictC2Schema):
    """Request for one Cluster 2 generation candidate.

    Only the generated Cluster 2 conditions may construct this request:
    ``C`` and ``G+C``. Replay controls remain replay controls and must not
    route through C2 generation.
    """

    identity: EvalIdentity
    prompt: str
    model_id: str
    model_revision: str
    tokenizer_revision: str
    max_new_tokens: int = 1024
    temperature: float = 0.2
    generation_seed: int | None = None

    @field_validator("prompt", "model_id", "model_revision", "tokenizer_revision")
    @classmethod
    def _non_empty_strings(cls, value: str) -> str:
        return _require_non_empty_string(value)

    @field_validator("max_new_tokens")
    @classmethod
    def _positive_max_new_tokens(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("max_new_tokens must be an int")
        if value <= 0:
            raise ValueError("max_new_tokens must be positive")
        return value

    @field_validator("generation_seed")
    @classmethod
    def _optional_non_negative_seed(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _require_non_negative_int(value)

    @model_validator(mode="after")
    def _validate_generated_condition(self) -> "RemoteC2GenerationRequest":
        condition = require_c2_generation_condition(self.identity.condition)
        if self.identity.source_class != GENERATED_SOURCE_CLASS:
            raise ValueError(
                f"condition {condition!r} requires source_class "
                f"{GENERATED_SOURCE_CLASS!r}"
            )
        expected_generation_mode = generation_mode_for_condition(condition)
        if self.identity.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.identity.generation_mode!r}"
            )
        return self


class RemoteC2GenerationResult(_StrictC2Schema):
    """Result for one Cluster 2 generation candidate."""

    identity: EvalIdentity
    source: str | None = None
    model_id: str
    model_revision: str
    generation_seed: int | None = None
    error_type: str | None = None
    error_msg: str | None = None

    @field_validator("model_id", "model_revision")
    @classmethod
    def _non_empty_strings(cls, value: str) -> str:
        return _require_non_empty_string(value)

    @field_validator("source", "error_type", "error_msg")
    @classmethod
    def _optional_non_empty_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty_string(value)

    @field_validator("generation_seed")
    @classmethod
    def _optional_non_negative_seed(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _require_non_negative_int(value)

    @model_validator(mode="after")
    def _validate_generated_condition(self) -> "RemoteC2GenerationResult":
        require_c2_generation_condition(self.identity.condition)
        if self.source is None and self.error_type is None:
            raise ValueError("source is required when error_type is None")
        return self


class RemoteCorrectnessRequest(_StrictC2Schema):
    """Request for correctness validation of one identified C2 source."""

    identity: EvalIdentity
    source: str

    @field_validator("source")
    @classmethod
    def _non_empty_source(cls, value: str) -> str:
        return _require_non_empty_string(value)


class RemoteCorrectnessResult(_StrictC2Schema):
    """Correctness result fields that map to the shared evaluation surface."""

    identity: EvalIdentity
    functional_success: bool
    repair_set_success: bool
    eval_set_success: bool
    failure_code: str | None = None
    correctness_error: str | None = None
    feedback: str | None = None
    num_repair_shapes: int
    num_eval_shapes: int
    num_test_shapes: int
    shapes_passed: int
    repair_shapes_passed: int
    eval_shapes_passed: int
    max_abs_diff: float | None = None
    max_rel_diff: float | None = None

    @field_validator("failure_code", "correctness_error", "feedback")
    @classmethod
    def _optional_non_empty_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _require_non_empty_string(value)

    @field_validator(
        "num_repair_shapes",
        "num_eval_shapes",
        "num_test_shapes",
        "shapes_passed",
        "repair_shapes_passed",
        "eval_shapes_passed",
    )
    @classmethod
    def _validate_non_negative_ints(cls, value: int) -> int:
        return _require_non_negative_int(value)

    @field_validator("max_abs_diff", "max_rel_diff")
    @classmethod
    def _validate_optional_non_negative_float(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("diff fields must be numeric")
        if value < 0:
            raise ValueError("diff fields must be non-negative")
        return float(value)

    @model_validator(mode="after")
    def _validate_shape_counts(self) -> "RemoteCorrectnessResult":
        expected_total = self.num_repair_shapes + self.num_eval_shapes
        if self.num_test_shapes != expected_total:
            raise ValueError("num_test_shapes must equal repair plus eval shapes")

        expected_passed = self.repair_shapes_passed + self.eval_shapes_passed
        if self.shapes_passed != expected_passed:
            raise ValueError("shapes_passed must equal repair plus eval passed counts")

        if self.repair_shapes_passed > self.num_repair_shapes:
            raise ValueError("repair_shapes_passed cannot exceed num_repair_shapes")
        if self.eval_shapes_passed > self.num_eval_shapes:
            raise ValueError("eval_shapes_passed cannot exceed num_eval_shapes")

        expected_repair_set_success = (
            self.repair_shapes_passed == self.num_repair_shapes
        )
        if self.repair_set_success != expected_repair_set_success:
            raise ValueError(
                "repair_set_success must equal whether all repair shapes passed"
            )

        expected_eval_set_success = self.eval_shapes_passed == self.num_eval_shapes
        if self.eval_set_success != expected_eval_set_success:
            raise ValueError(
                "eval_set_success must equal whether all eval shapes passed"
            )

        if self.functional_success != (
            self.repair_set_success and self.eval_set_success
        ):
            raise ValueError(
                "functional_success must equal repair_set_success and eval_set_success"
            )
        return self


@dataclass(frozen=True)
class C2ModalSurfaceMetadata:
    schema_version: int
    surface_phase: str
    conditions: tuple[str, ...]
    replay_conditions: tuple[str, ...]
    generated_conditions: tuple[str, ...]
    modal_generation_gpu: str
    modal_eval_gpu: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def modal_surface_metadata() -> C2ModalSurfaceMetadata:
    """Return cheap metadata for C2 Modal surface ownership."""

    return C2ModalSurfaceMetadata(
        schema_version=C2_MODAL_SCHEMA_VERSION,
        surface_phase=C2_MODAL_SURFACE_PHASE,
        conditions=CLUSTER2_CONDITIONS,
        replay_conditions=REPLAY_CONTROL_CONDITIONS,
        generated_conditions=NEW_GENERATION_CONDITIONS,
        modal_generation_gpu=DEFAULT_C2_MODAL_GENERATION_GPU,
        modal_eval_gpu=DEFAULT_C2_MODAL_EVAL_GPU,
    )


def require_c2_generation_condition(condition: str) -> str:
    """Validate that ``condition`` may use the future C2 generation surface."""

    return require_generated_condition(condition)


def sidecar_generation_modes() -> dict[str, dict[str, str]]:
    """Return the locked generation-mode sidecar mapping."""

    return {
        condition: {"generation_mode": generation_mode_for_condition(condition)}
        for condition in CLUSTER2_CONDITIONS
    }


def _require_non_empty_string(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    if not value:
        raise ValueError("value must not be empty")
    return value


def _require_member(value: str, allowed: tuple[str, ...], field_name: str) -> str:
    if value not in allowed:
        raise ValueError(
            f"unsupported {field_name} {value!r}; expected one of: "
            f"{', '.join(allowed)}"
        )
    return value


def _require_non_negative_int(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("value must be an int")
    if value < 0:
        raise ValueError("value must be non-negative")
    return value
