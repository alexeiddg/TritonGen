"""Tests for the Phase 1 eval pipeline skeleton."""

from __future__ import annotations

import sys

import pytest

from cluster2.constants import generation_mode_for_condition, source_class_for_condition
from shared.eval.pipeline import PIPELINE_STAGE_NAMES, run_eval_pipeline
from shared.eval.run_config import RunConfig


FORBIDDEN_RUNTIME_MODULE_PREFIXES = (
    "modal",
    "torch",
    "triton",
    "transformers",
    "xgrammar",
    "cluster2.modal",
    "shared.modal_harness",
)


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


def test_pipeline_skeleton_does_not_call_generation_or_modal() -> None:
    config = RunConfig(**_run_config_payload("C"))
    before = set(sys.modules)

    result = run_eval_pipeline(config)

    loaded_runtime_modules = sorted(
        name
        for name in set(sys.modules) - before
        if name == "modal" or name.startswith(FORBIDDEN_RUNTIME_MODULE_PREFIXES)
    )
    assert loaded_runtime_modules == []
    assert result.runtime_executed is False
    assert [stage.name for stage in result.stages] == list(PIPELINE_STAGE_NAMES)
    assert result.stages[2].status == "deferred_phase1"


@pytest.mark.parametrize("condition", ["none", "G"])
def test_pipeline_skeleton_preserves_replay_control_routing(condition: str) -> None:
    config = RunConfig(**_run_config_payload(condition))

    result = run_eval_pipeline(config)

    assert result.source_class == "replay_control_row"
    assert result.generation_mode == "replay_control"
    assert result.source_route == "frozen_cluster1_replay_control"
    assert result.modal_generation_gpu is None
    assert result.generation_runtime_allowed is False
    assert result.stages[2].status == "skipped_replay_control"


@pytest.mark.parametrize("condition", ["C", "G+C"])
def test_pipeline_skeleton_routes_generated_conditions_as_placeholders(
    condition: str,
) -> None:
    config = RunConfig(**_run_config_payload(condition))

    result = run_eval_pipeline(config)

    assert result.source_class == "generated_row"
    assert result.source_route == "future_c2_generated_row"
    assert result.generation_runtime_allowed is True
    assert result.runtime_executed is False
    assert result.stages[2].status == "deferred_phase1"


def test_pipeline_accepts_dict_payload_with_runconfig_validation() -> None:
    result = run_eval_pipeline(_run_config_payload("none"))

    assert result.condition == "none"
    assert result.source_class == "replay_control_row"


def test_pipeline_rejects_invalid_config_payload() -> None:
    payload = _run_config_payload("G+C")
    payload["generation_mode"] = "replay_control"

    with pytest.raises(ValueError, match="requires generation_mode"):
        run_eval_pipeline(payload)
