"""TritonGen shared Modal harness.

Reusable GPU execution primitives shared by Cluster 1, Cluster 2, and Cluster 3.
The harness owns:
- the single ``modal.App`` definition
- compile and (later) generation images
- shared volumes and optional HF secret
- request/result schemas with cluster-boundary-aware validation
- subprocess-isolated remote compile function

Cluster-specific control logic (repair loops, numerical correctness, profiling)
must live in cluster adapters, not in this package.
"""

from __future__ import annotations

from shared.modal_harness.app import app
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.secrets import hf_secrets
from shared.modal_harness.volumes import artifact_volume, hf_cache_volume

__all__ = [
    "app",
    "triton_compile_image",
    "hf_cache_volume",
    "artifact_volume",
    "hf_secrets",
]
