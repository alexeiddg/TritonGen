"""Cross-cluster checks for lightweight generation metadata constants."""

from __future__ import annotations

import cluster1.results.dataclass as c1
import cluster2.modal.schemas as c2_schemas
import cluster2.results.dataclass as c2
from shared import generation_metadata as shared_metadata


def test_c1_c2_metadata_constants_remain_aligned() -> None:
    assert c1.VALID_GRAMMAR_VARIANTS == shared_metadata.VALID_GRAMMAR_VARIANTS
    assert c2.GRAMMAR_PATHS_BY_VARIANT == shared_metadata.GRAMMAR_PATHS_BY_VARIANT
    assert c1.GRAMMAR_PATHS_BY_VARIANT == shared_metadata.GRAMMAR_PATHS_BY_VARIANT
    assert c2_schemas.VALID_REJECTION_LAYERS == shared_metadata.VALID_REJECTION_LAYERS
    assert c2.VALID_REJECTION_LAYERS == shared_metadata.VALID_REJECTION_LAYERS
    assert c1.VALID_REJECTION_LAYERS == shared_metadata.VALID_REJECTION_LAYERS
    assert c2_schemas.VALID_STOP_REASONS == shared_metadata.VALID_STOP_REASONS
    assert c2.VALID_STOP_REASONS == shared_metadata.VALID_STOP_REASONS
    assert c1.VALID_STOP_REASONS == shared_metadata.VALID_STOP_REASONS


def test_c1_c2_required_generation_metadata_fields_remain_aligned() -> None:
    c1_required = set(c1.PAPER_SCALE_METADATA_FIELD_NAMES)
    c2_required = {
        *shared_metadata.PAPER_SCALE_BASE_REQUIRED_METADATA_FIELD_NAMES,
        *shared_metadata.PAPER_SCALE_GRAMMAR_REQUIRED_METADATA_FIELD_NAMES,
        "modal_image_sha",
        "modal_image_provenance_sha256",
        "modal_image_provenance_components",
    }

    assert c1_required == c2_required
    assert "grammar_valid" in c1_required
    assert "grammar_active" not in c1_required


def test_immutable_hub_revision_helper_requires_commit_sha() -> None:
    revision = "a" * shared_metadata.HUB_COMMIT_SHA_LENGTH

    assert shared_metadata.is_immutable_hub_revision(revision)
    assert (
        shared_metadata.normalize_immutable_hub_revision(
            f" {revision.upper()} ",
            field_name="model_revision",
        )
        == revision.upper()
    )
    for value in ("main", "refs/heads/main", "dev", "v1.0.0", "a" * 39):
        assert not shared_metadata.is_immutable_hub_revision(value)


def test_stable_modal_image_identifier_accepts_sha_and_modal_object_id() -> None:
    assert shared_metadata.is_stable_modal_image_identifier("a" * 64)
    assert shared_metadata.is_stable_modal_image_identifier("sha256:" + "b" * 64)
    assert shared_metadata.is_stable_modal_image_identifier("im-123")
    assert shared_metadata.is_stable_modal_image_identifier("im-tU3VQyAbFvrusOxtlwspCN")

    for value in (
        "unknown",
        "mutable-tag",
        "not-a-sha",
        "sha256:nothex",
        "",
        " im-123 ",
        " " + ("a" * 64),
        "sha256:" + ("b" * 64) + " ",
    ):
        assert not shared_metadata.is_stable_modal_image_identifier(value)
