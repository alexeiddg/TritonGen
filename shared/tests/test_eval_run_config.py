"""Tests for Phase 1 RunConfig routing invariants."""

from __future__ import annotations

import json

import pytest

from cluster2.constants import generation_mode_for_condition, source_class_for_condition
from shared.eval.run_config import RunConfig


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


@pytest.mark.parametrize("condition", ["none", "G", "C", "G+C"])
def test_valid_run_config_for_condition(condition: str) -> None:
    config = RunConfig(**_run_config_payload(condition))

    assert config.condition == condition
    assert config.source_class == source_class_for_condition(condition)
    assert config.generation_mode == generation_mode_for_condition(condition)
    assert config.equal_attempts_n == config.repair_budget + 1


@pytest.mark.parametrize("condition", ["none", "G"])
def test_replay_controls_reject_generation_gpu(condition: str) -> None:
    payload = _run_config_payload(condition)
    payload["modal_generation_gpu"] = "L4"

    with pytest.raises(ValueError, match="modal_generation_gpu"):
        RunConfig(**payload)


def test_c_rejects_replay_generation_mode() -> None:
    payload = _run_config_payload("C")
    payload["generation_mode"] = "replay_control"

    with pytest.raises(ValueError, match="requires generation_mode"):
        RunConfig(**payload)


def test_g_plus_c_rejects_replay_generation_mode() -> None:
    payload = _run_config_payload("G+C")
    payload["generation_mode"] = "replay_control"

    with pytest.raises(ValueError, match="requires generation_mode"):
        RunConfig(**payload)


def test_wrong_equal_attempts_n_rejected() -> None:
    payload = _run_config_payload("C")
    payload["equal_attempts_n"] = 5

    with pytest.raises(ValueError, match="repair_budget \\+ 1"):
        RunConfig(**payload)


def test_from_dict_rejects_unknown_fields() -> None:
    payload = _run_config_payload("none")
    payload["timing_iters"] = 100

    with pytest.raises(ValueError, match="unknown RunConfig fields"):
        RunConfig.from_dict(payload)


def test_json_round_trip_normalizes_dtypes_to_tuple() -> None:
    config = RunConfig(**_run_config_payload("G+C"))

    round_tripped = RunConfig.from_dict(json.loads(config.to_json()))

    assert round_tripped == config
    assert round_tripped.dtypes == ("fp32",)
