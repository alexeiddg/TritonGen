"""Tests for Phase 4 Level 2 wiring in the eval pipeline."""

from __future__ import annotations

import json

import pytest

from cluster2.constants import generation_mode_for_condition, source_class_for_condition
from shared.eval.correctness_shapes import CorrectnessShapeSets
from shared.eval.levels.level2_correctness import (
    GENERIC_EVAL_FAILURE_FEEDBACK,
    Level2CandidateRequest,
)
from shared.eval.pipeline import PipelineLevel2Request, run_eval_pipeline
from shared.eval.run_config import RunConfig
from shared.tests.level2_fake_torch import install_fake_level2_runtime


@pytest.fixture(autouse=True)
def fake_level2_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_level2_runtime(monkeypatch)


def test_pipeline_runs_level2_when_request_is_explicit() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=11)
    config = RunConfig(**_run_config_payload("C"))

    result = run_eval_pipeline(
        config,
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=_matching_candidate,
        ),
    )
    stages = {stage.name: stage for stage in result.stages}

    assert result.level2_result is not None
    assert result.level2_result.functional_success is True
    assert stages["level2_correctness"].status == "passed"
    assert stages["level2_correctness"].detail == "functional_success=True"
    assert stages["repair_loop"].status == "deferred_phase1"
    assert result.runtime_executed is False


def test_pipeline_level2_functional_success_requires_eval_set() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((97,),), base_seed=11)
    config = RunConfig(**_run_config_payload("C"))

    result = run_eval_pipeline(
        config,
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=_offset_candidate(offset=1.0, only_split="eval"),
        ),
    )
    stages = {stage.name: stage for stage in result.stages}

    assert result.level2_result is not None
    assert result.level2_result.repair_set_success is True
    assert result.level2_result.eval_set_success is False
    assert result.level2_result.functional_success is False
    assert stages["level2_correctness"].status == "failed"
    assert stages["level2_correctness"].detail == GENERIC_EVAL_FAILURE_FEEDBACK


def test_pipeline_level2_privacy_hides_eval_shape_from_output() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((97,),), base_seed=11)
    config = RunConfig(**_run_config_payload("C"))

    result = run_eval_pipeline(
        config,
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=_offset_candidate(offset=1.0, only_split="eval"),
        ),
    )
    rendered = json.dumps(result.to_dict(), sort_keys=True)

    assert GENERIC_EVAL_FAILURE_FEEDBACK in rendered
    assert "97" not in rendered
    assert "eval_shape_set" not in rendered
    assert "diff tensor" not in rendered.lower()


def test_pipeline_does_not_retry_or_repair_level2_candidates() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=11)
    calls: list[tuple[str, tuple[int, ...]]] = []

    def recording_candidate(request: Level2CandidateRequest):
        calls.append((request.split, request.shape))
        return _matching_candidate(request)

    run_eval_pipeline(
        RunConfig(**_run_config_payload("C")),
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=recording_candidate,
        ),
    )

    assert calls == [("repair", (2,)), ("eval", (3,))]


def test_pipeline_preserves_replay_control_routing_with_level2_request() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=11)

    result = run_eval_pipeline(
        RunConfig(**_run_config_payload("none")),
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=_matching_candidate,
        ),
    )

    assert result.source_class == "replay_control_row"
    assert result.generation_mode == "replay_control"
    assert result.source_route == "frozen_cluster1_replay_control"
    assert result.modal_generation_gpu is None
    assert result.generation_runtime_allowed is False
    assert result.level2_result is not None
    assert result.level2_result.functional_success is True


def test_pipeline_level2_output_has_no_performance_fields() -> None:
    shape_sets = _elementwise_shape_sets(repair=((2,),), eval_=((3,),), base_seed=11)

    result = run_eval_pipeline(
        RunConfig(**_run_config_payload("C")),
        level2_request=PipelineLevel2Request(
            kernel_class="elementwise",
            dtype="fp32",
            base_seed=11,
            shape_sets=shape_sets,
            candidate_runner=_matching_candidate,
        ),
    )
    rendered = json.dumps(result.to_dict(), sort_keys=True).lower()

    assert "timing" not in rendered
    assert "performance" not in rendered
    assert "speedup" not in rendered
    assert "profiling" not in rendered


def _run_config_payload(condition: str) -> dict[str, object]:
    is_replay_control = condition in {"none", "G"}
    return {
        "condition": condition,
        "source_class": source_class_for_condition(condition),
        "generation_mode": generation_mode_for_condition(condition),
        "scale_tier": "smoke",
        "repair_budget": 5,
        "equal_attempts_n": 6,
        "enable_ast_sanitizer": False,
        "dtypes": ("fp32",),
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": "model-revision",
        "tokenizer_revision": "tokenizer-revision",
        "modal_generation_gpu": None if is_replay_control else "L4",
        "modal_eval_gpu": "L4",
    }


def _matching_candidate(request: Level2CandidateRequest):
    import torch

    if request.kernel_name == "relu":
        return torch.relu(request.inputs[0])
    raise AssertionError(f"unexpected kernel {request.kernel_name!r}")


def _offset_candidate(
    *,
    offset: float,
    only_split: str | None = None,
):
    def run(request: Level2CandidateRequest):
        output = _matching_candidate(request)
        if only_split is not None and request.split != only_split:
            return output
        return output + offset

    return run


def _elementwise_shape_sets(
    *,
    repair: tuple[tuple[int, ...], ...],
    eval_: tuple[tuple[int, ...], ...],
    base_seed: int,
) -> CorrectnessShapeSets:
    return CorrectnessShapeSets(
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=base_seed,
        repair_shape_set=repair,
        eval_shape_set=eval_,
    )
