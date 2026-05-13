"""Phase 0 tests for Cluster 2 metadata dataclasses."""

from __future__ import annotations

from dataclasses import fields

import pytest

from cluster2.constants import (
    DEFAULT_EQUAL_ATTEMPTS_N,
    generation_mode_for_condition,
    source_class_for_condition,
)
from cluster2.results.dataclass import (
    Cluster2CandidateIdentity,
    Cluster2CandidateMetadata,
    Cluster2CellIdentity,
    make_candidate_identity,
)


def test_condition_routing_metadata_is_locked() -> None:
    assert DEFAULT_EQUAL_ATTEMPTS_N == 6
    assert source_class_for_condition("none") == "replay_control_row"
    assert source_class_for_condition("G") == "replay_control_row"
    assert source_class_for_condition("C") == "generated_row"
    assert source_class_for_condition("G+C") == "generated_row"
    assert generation_mode_for_condition("none") == "replay_control"
    assert generation_mode_for_condition("G") == "replay_control"
    assert generation_mode_for_condition("C") == "new_c2_generation"
    assert generation_mode_for_condition("G+C") == "new_c2_generation_with_G_adapter"


def test_candidate_identity_builds_condition_consistent_metadata() -> None:
    cell = Cluster2CellIdentity(
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=0,
    )
    identity = make_candidate_identity(cell=cell, condition="G", attempt_index=2)

    assert identity.source_class == "replay_control_row"
    assert identity.generation_mode == "replay_control"
    assert identity.canonical_key() == ("elementwise", "relu", "fp32", 0, "G", 2)


def test_candidate_identity_rejects_mismatched_source_class() -> None:
    cell = Cluster2CellIdentity(
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=0,
    )

    with pytest.raises(ValueError, match="requires source_class"):
        Cluster2CandidateIdentity(
            cell=cell,
            condition="none",
            source_class="generated_row",
            generation_mode="replay_control",
            attempt_index=0,
        )


def test_candidate_metadata_round_trips_with_stable_json() -> None:
    cell = Cluster2CellIdentity(
        kernel_class="matmul",
        kernel_name="gemm",
        dtype="bf16",
        base_seed=3,
    )
    identity = make_candidate_identity(cell=cell, condition="C", attempt_index=1)
    metadata = Cluster2CandidateMetadata(
        identity=identity,
        source_sha256="0" * 64,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision="model-revision",
        tokenizer_revision="tokenizer-revision",
        eval_pipeline_hashes={"shared/eval/schema.py": "1" * 64},
        generation_hashes={"cluster2/modal/generation.py": "2" * 64},
        external_pins={"python_version": "3.12.0"},
    )

    assert metadata.to_json() == metadata.to_json()
    assert Cluster2CandidateMetadata.from_dict(metadata.to_dict()) == metadata


def test_metadata_dataclasses_do_not_define_runtime_metric_fields() -> None:
    forbidden_fragments = ("time", "profil", "speed", "perf")
    for cls in (Cluster2CandidateIdentity, Cluster2CandidateMetadata):
        field_names = [field.name for field in fields(cls)]
        assert not [
            name
            for name in field_names
            if any(fragment in name for fragment in forbidden_fragments)
        ]
