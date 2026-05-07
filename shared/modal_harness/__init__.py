"""TritonGen shared Modal harness.

Reusable GPU execution primitives shared by Cluster 1, Cluster 2, and Cluster 3.
The harness owns:
- the single ``modal.App`` definition
- compile and generation images
- shared volumes and optional HF secret
- request/result schemas with cluster-boundary-aware validation
- subprocess-isolated remote compile function

Cluster-specific control logic (repair loops, numerical correctness, profiling)
must live in cluster adapters, not in this package.
"""

from __future__ import annotations

__all__ = [
    "app",
    "llm_generation_image",
    "triton_compile_image",
    "hf_cache_volume",
    "artifact_volume",
    "hf_secrets",
]


def __getattr__(name: str):
    if name == "app":
        from shared.modal_harness.app import app

        return app
    if name in {"llm_generation_image", "triton_compile_image"}:
        from shared.modal_harness.images import llm_generation_image, triton_compile_image

        return {
            "llm_generation_image": llm_generation_image,
            "triton_compile_image": triton_compile_image,
        }[name]
    if name in {"hf_cache_volume", "artifact_volume"}:
        from shared.modal_harness.volumes import artifact_volume, hf_cache_volume

        return {
            "artifact_volume": artifact_volume,
            "hf_cache_volume": hf_cache_volume,
        }[name]
    if name == "hf_secrets":
        from shared.modal_harness.secrets import hf_secrets

        return hf_secrets
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
