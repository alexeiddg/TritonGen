"""Shared evaluation pipeline routing and lightweight Level 2 wiring.

The default path validates routing and reports placeholder stages only. Phase 4
adds an explicit, injectable Level 2 correctness path without generation, Modal,
Triton orchestration, retries, or repair-loop behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cluster2.constants import REPLAY_CONTROL_CONDITIONS, generation_mode_for_condition
from shared.eval.correctness_shapes import (
    DEFAULT_SHAPES_PER_SPLIT,
    CorrectnessShapeSets,
)
from shared.eval.levels.level2_correctness import (
    Level2CandidateRunner,
    Level2CorrectnessResult,
    evaluate_level2_correctness,
)
from shared.eval.run_config import RunConfig


PIPELINE_STAGE_NAMES: tuple[str, ...] = (
    "validate_config",
    "resolve_routing",
    "generation",
    "level0_parse",
    "level1_compile",
    "level2_correctness",
    "repair_loop",
)


@dataclass(frozen=True)
class PipelineStageStatus:
    """Structured placeholder status for one pipeline stage."""

    name: str
    status: str
    detail: str

    def __post_init__(self) -> None:
        if self.name not in PIPELINE_STAGE_NAMES:
            raise ValueError(f"unknown pipeline stage {self.name!r}")
        if not self.status:
            raise ValueError("stage status must not be empty")
        if not self.detail:
            raise ValueError("stage detail must not be empty")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class EvalPipelineSkeletonResult:
    """Pipeline return object for config/routing validation and optional Level 2."""

    condition: str
    source_class: str
    generation_mode: str
    source_route: str
    modal_generation_gpu: str | None
    modal_eval_gpu: str
    generation_runtime_allowed: bool
    runtime_executed: bool
    stages: tuple[PipelineStageStatus, ...]
    level2_result: Level2CorrectnessResult | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stages"] = [stage.to_dict() for stage in self.stages]
        payload["level2_result"] = (
            None if self.level2_result is None else self.level2_result.to_dict()
        )
        return payload


@dataclass(frozen=True)
class PipelineLevel2Request:
    """Explicit CPU-testable Level 2 request for pipeline wiring."""

    kernel_class: str
    dtype: str
    base_seed: int
    candidate_runner: Level2CandidateRunner
    attempt_index: int = 0
    shape_sets: CorrectnessShapeSets | None = None
    shapes_per_split: int = DEFAULT_SHAPES_PER_SPLIT
    device: str = "cpu"


def run_eval_pipeline(
    config: RunConfig | dict[str, Any],
    *,
    level2_request: PipelineLevel2Request | None = None,
) -> EvalPipelineSkeletonResult:
    """Validate ``config`` and optionally run the deterministic Level 2 check."""

    run_config = _coerce_run_config(config)
    _enforce_routing_guards(run_config)

    source_route = (
        "frozen_cluster1_replay_control"
        if run_config.condition in REPLAY_CONTROL_CONDITIONS
        else "future_c2_generated_row"
    )
    generation_runtime_allowed = run_config.condition not in REPLAY_CONTROL_CONDITIONS
    level2_result = _run_level2_request(level2_request)

    return EvalPipelineSkeletonResult(
        condition=run_config.condition,
        source_class=run_config.source_class,
        generation_mode=run_config.generation_mode,
        source_route=source_route,
        modal_generation_gpu=run_config.modal_generation_gpu,
        modal_eval_gpu=run_config.modal_eval_gpu,
        generation_runtime_allowed=generation_runtime_allowed,
        runtime_executed=False,
        stages=_build_phase1_stages(run_config, level2_result),
        level2_result=level2_result,
    )


def _coerce_run_config(config: RunConfig | dict[str, Any]) -> RunConfig:
    if isinstance(config, RunConfig):
        return config
    if isinstance(config, dict):
        return RunConfig.from_dict(config)
    raise TypeError("run_eval_pipeline requires a RunConfig or dict payload")


def _enforce_routing_guards(config: RunConfig) -> None:
    expected_generation_mode = generation_mode_for_condition(config.condition)
    if config.generation_mode != expected_generation_mode:
        raise ValueError(
            f"condition {config.condition!r} requires generation_mode "
            f"{expected_generation_mode!r}; got {config.generation_mode!r}"
        )
    if config.condition in REPLAY_CONTROL_CONDITIONS:
        if config.source_class != "replay_control_row":
            raise ValueError("replay controls must route to replay_control_row")
        if config.modal_generation_gpu is not None:
            raise ValueError("replay controls must not request a generation GPU")
    else:
        if config.source_class != "generated_row":
            raise ValueError("generated conditions must route to generated_row")


def _run_level2_request(
    request: PipelineLevel2Request | None,
) -> Level2CorrectnessResult | None:
    if request is None:
        return None
    return evaluate_level2_correctness(
        request.kernel_class,
        request.dtype,
        request.candidate_runner,
        base_seed=request.base_seed,
        attempt_index=request.attempt_index,
        shape_sets=request.shape_sets,
        shapes_per_split=request.shapes_per_split,
        device=request.device,
    )


def _build_phase1_stages(
    config: RunConfig,
    level2_result: Level2CorrectnessResult | None = None,
) -> tuple[PipelineStageStatus, ...]:
    if config.condition in REPLAY_CONTROL_CONDITIONS:
        generation_status = PipelineStageStatus(
            name="generation",
            status="skipped_replay_control",
            detail="frozen Cluster 1 replay controls do not request generation",
        )
    else:
        generation_status = PipelineStageStatus(
            name="generation",
            status="deferred_phase1",
            detail="new C2 generation is reserved for a later phase",
        )

    return (
        PipelineStageStatus(
            name="validate_config",
            status="validated",
            detail="RunConfig invariants passed",
        ),
        PipelineStageStatus(
            name="resolve_routing",
            status="resolved",
            detail=f"{config.source_class}:{config.generation_mode}",
        ),
        generation_status,
        PipelineStageStatus(
            name="level0_parse",
            status="deferred_phase1",
            detail="runtime parse evaluation is reserved for a later phase",
        ),
        PipelineStageStatus(
            name="level1_compile",
            status="deferred_phase1",
            detail="Triton compile evaluation is reserved for a later phase",
        ),
        _build_level2_stage(level2_result),
        PipelineStageStatus(
            name="repair_loop",
            status="deferred_phase1",
            detail="repair loops are reserved for a later phase",
        ),
    )


def _build_level2_stage(
    level2_result: Level2CorrectnessResult | None,
) -> PipelineStageStatus:
    if level2_result is None:
        return PipelineStageStatus(
            name="level2_correctness",
            status="deferred_phase1",
            detail="correctness evaluation requires an explicit Level 2 request",
        )
    if level2_result.functional_success:
        return PipelineStageStatus(
            name="level2_correctness",
            status="passed",
            detail="functional_success=True",
        )
    return PipelineStageStatus(
        name="level2_correctness",
        status="failed",
        detail=level2_result.correctness_error or "functional_success=False",
    )
