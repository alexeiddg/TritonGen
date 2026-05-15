"""Tests for cross-cluster factorial analysis helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from shared.analysis.factorial import validate_paired_replay_dataframe


def test_validate_paired_replay_dataframe_reads_nested_metadata() -> None:
    df = pd.DataFrame(
        [
            _generated_row(base_seed=0),
            _replay_row(base_seed=0),
        ]
    )

    validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_nested_metadata_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["replay_metadata"]["prompt_sha256"] = "d" * 64
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_replay_base_seed_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["replay_metadata"]["replay_base_seed"] = 1
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_known_revision_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(
        base_seed=0,
        model_revision="frozen-model-rev",
        tokenizer_revision="frozen-tokenizer-rev",
    )
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_missing_pair_metadata() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated.pop("generated_metadata")
    replay.pop("replay_metadata")
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="missing paired replay metadata"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_generated_seed_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated["generated_metadata"]["generation_seed"] = 999
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_control_condition_mismatch() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    generated["generated_metadata"]["replay_control_condition"] = "G"
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="metadata mismatch"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_nonzero_replay_attempt() -> None:
    generated = _generated_row(base_seed=0)
    replay = _replay_row(base_seed=0)
    replay["attempt_index"] = 5
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="attempt_index 0"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def test_validate_paired_replay_dataframe_rejects_missing_generated_attempt_zero() -> None:
    generated = _generated_row(base_seed=0, attempt_index=1)
    generated["generated_metadata"]["generation_seed"] = 1
    replay = _replay_row(base_seed=0)
    df = pd.DataFrame([generated, replay])

    with pytest.raises(ValueError, match="attempt_index 0"):
        validate_paired_replay_dataframe(df, treatment_condition="C")


def _generated_row(*, base_seed: int, attempt_index: int = 0) -> dict[str, object]:
    return {
        "condition": "C",
        "kernel_class": "elementwise",
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": attempt_index,
        "functional_success": True,
        "generated_metadata": _generated_pair_metadata(base_seed),
    }


def _replay_row(
    *,
    base_seed: int,
    model_revision: str = "unavailable_in_frozen_cluster1_artifact",
    tokenizer_revision: str = "unavailable_in_frozen_cluster1_artifact",
) -> dict[str, object]:
    return {
        "condition": "none",
        "kernel_class": "elementwise",
        "dtype": "fp32",
        "base_seed": base_seed,
        "attempt_index": 0,
        "functional_success": False,
        "replay_metadata": _pair_metadata(
            base_seed,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
        ),
    }


def _pair_metadata(
    base_seed: int,
    *,
    model_revision: str = "model-rev",
    tokenizer_revision: str = "tok-rev",
) -> dict[str, object]:
    return {
        "replay_pair_id": f"elementwise:fp32:{base_seed}",
        "replay_base_seed": base_seed,
        "replay_generation_seed": base_seed,
        "prompt_sha256": "c" * 64,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": model_revision,
        "tokenizer_revision": tokenizer_revision,
        "temperature": 0.2,
        "max_new_tokens": 512,
    }


def _generated_pair_metadata(base_seed: int) -> dict[str, object]:
    metadata = _pair_metadata(base_seed)
    metadata["generation_seed"] = base_seed
    metadata["replay_control_condition"] = "none"
    return metadata
