"""Run configuration contract for Cluster 2 evaluation routing.

This module is configuration-only. It validates condition/source routing and
does not import Modal, generation, compile, or correctness runtime code.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from typing import Any, Literal, TypeAlias, cast

from cluster2.constants import (
    CLUSTER2_CONDITIONS,
    DTYPE_NAMES,
    REPLAY_CONTROL_CONDITIONS,
    generation_mode_for_condition,
    source_class_for_condition,
)


RunCondition: TypeAlias = Literal["none", "G", "C", "G+C"]
RunSourceClass: TypeAlias = Literal["generated_row", "replay_control_row"]
RunGenerationMode: TypeAlias = Literal[
    "replay_control",
    "new_c2_generation",
    "new_c2_generation_with_G_adapter",
]
ScaleTier: TypeAlias = Literal["smoke", "development", "paper"]

SCALE_TIERS: tuple[ScaleTier, ...] = ("smoke", "development", "paper")
SOURCE_CLASSES: tuple[RunSourceClass, ...] = ("generated_row", "replay_control_row")
GENERATION_MODES: tuple[RunGenerationMode, ...] = (
    "replay_control",
    "new_c2_generation",
    "new_c2_generation_with_G_adapter",
)


@dataclass(frozen=True)
class RunConfig:
    """Strict Phase 1 run configuration.

    The config enforces only routing/configuration invariants. Runtime behavior
    such as generation, compilation, correctness, and repair is intentionally
    deferred to later phases.
    """

    condition: RunCondition
    source_class: RunSourceClass
    generation_mode: RunGenerationMode
    scale_tier: ScaleTier
    repair_budget: int
    equal_attempts_n: int
    enable_ast_sanitizer: bool
    dtypes: tuple[str, ...]
    model_id: str
    model_revision: str
    tokenizer_revision: str
    modal_generation_gpu: str | None
    modal_eval_gpu: str

    def __post_init__(self) -> None:
        condition = _require_condition(self.condition)
        object.__setattr__(self, "condition", condition)

        _require_member(self.source_class, SOURCE_CLASSES, "source_class")
        _require_member(self.generation_mode, GENERATION_MODES, "generation_mode")
        _require_member(self.scale_tier, SCALE_TIERS, "scale_tier")

        _require_non_negative_int(self.repair_budget, "repair_budget")
        _require_non_negative_int(self.equal_attempts_n, "equal_attempts_n")
        if self.equal_attempts_n != self.repair_budget + 1:
            raise ValueError("equal_attempts_n must equal repair_budget + 1")

        if not isinstance(self.enable_ast_sanitizer, bool):
            raise TypeError("enable_ast_sanitizer must be a bool")
        if isinstance(self.dtypes, list):
            object.__setattr__(self, "dtypes", tuple(self.dtypes))
        _require_dtypes(self.dtypes)
        _require_non_empty_str(self.model_id, "model_id")
        _require_non_empty_str(self.model_revision, "model_revision")
        _require_non_empty_str(self.tokenizer_revision, "tokenizer_revision")
        _require_optional_non_empty_str(
            self.modal_generation_gpu,
            "modal_generation_gpu",
        )
        _require_non_empty_str(self.modal_eval_gpu, "modal_eval_gpu")

        expected_source_class = source_class_for_condition(condition)
        if self.source_class != expected_source_class:
            raise ValueError(
                f"condition {condition!r} requires source_class "
                f"{expected_source_class!r}; got {self.source_class!r}"
            )

        expected_generation_mode = generation_mode_for_condition(condition)
        if self.generation_mode != expected_generation_mode:
            raise ValueError(
                f"condition {condition!r} requires generation_mode "
                f"{expected_generation_mode!r}; got {self.generation_mode!r}"
            )

        if condition in REPLAY_CONTROL_CONDITIONS and self.modal_generation_gpu is not None:
            raise ValueError(
                f"condition {condition!r} is replay-only and requires "
                "modal_generation_gpu to be None"
            )

    @property
    def is_replay_control(self) -> bool:
        """Return whether this config routes to frozen replay-control rows."""

        return self.condition in REPLAY_CONTROL_CONDITIONS

    @property
    def permits_new_generation(self) -> bool:
        """Return whether this config is allowed to request future C2 generation."""

        return not self.is_replay_control

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Return a stable JSON string representation."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunConfig":
        """Build ``RunConfig`` from a dictionary and reject unknown fields."""

        if not isinstance(payload, dict):
            raise TypeError("RunConfig.from_dict requires a dict")
        _reject_unknown_fields(cls, payload)
        return cls(**payload)


def _require_condition(value: object) -> RunCondition:
    if not isinstance(value, str):
        raise TypeError("condition must be a string")
    if value not in CLUSTER2_CONDITIONS:
        raise ValueError(
            f"unsupported condition {value!r}; expected one of: "
            f"{', '.join(CLUSTER2_CONDITIONS)}"
        )
    return cast(RunCondition, value)


def _require_member(value: object, allowed: tuple[str, ...], field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if value not in allowed:
        raise ValueError(
            f"unsupported {field_name} {value!r}; expected one of: "
            f"{', '.join(allowed)}"
        )


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_dtypes(value: object) -> None:
    if not isinstance(value, tuple):
        raise TypeError("dtypes must be a tuple")
    if not value:
        raise ValueError("dtypes must not be empty")
    for dtype in value:
        if not isinstance(dtype, str):
            raise TypeError("dtypes entries must be strings")
        if dtype not in DTYPE_NAMES:
            raise ValueError(
                f"unsupported dtype {dtype!r}; expected one of: "
                f"{', '.join(DTYPE_NAMES)}"
            )


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _require_optional_non_empty_str(value: object, field_name: str) -> None:
    if value is None:
        return
    _require_non_empty_str(value, field_name)


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")
