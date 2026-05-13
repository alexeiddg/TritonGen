"""Isolated Cluster 2 Modal scaffolding.

Phase 0 exposes only cheap metadata imports. Runtime generation and correctness
execution are introduced in later phases.
"""

from cluster2.modal.schemas import (
    C2ModalSurfaceMetadata,
    modal_surface_metadata,
    sidecar_generation_modes,
)

__all__ = [
    "C2ModalSurfaceMetadata",
    "modal_surface_metadata",
    "sidecar_generation_modes",
]
