"""Phase 0 placeholder for future Cluster 2 Modal generation.

No model loading, Modal app wiring, or generation loop exists in Phase 0.
"""

from __future__ import annotations

from cluster2.modal.schemas import (
    C2ModalSurfaceMetadata,
    modal_surface_metadata,
    require_c2_generation_condition,
)


def generation_surface_metadata() -> C2ModalSurfaceMetadata:
    """Return metadata for the isolated C2 generation surface."""

    return modal_surface_metadata()


def validate_future_generation_condition(condition: str) -> str:
    """Validate future C2 generation routing without invoking generation."""

    return require_c2_generation_condition(condition)
