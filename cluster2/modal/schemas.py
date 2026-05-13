"""Cluster 2 Modal schema metadata scaffolding.

Full Pydantic request/result schemas are intentionally deferred. This module
only locks Phase 0 routing metadata and keeps it separate from
``shared.modal_harness.schemas``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import (
    CLUSTER2_CONDITIONS,
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_C2_MODAL_GENERATION_GPU,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
    generation_mode_for_condition,
    require_generated_condition,
)


C2_MODAL_SCHEMA_VERSION = 1
C2_MODAL_SURFACE_PHASE = "phase0_scaffold"


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
