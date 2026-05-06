"""Modal image definitions for the TritonGen GPU harness.

Phase 1–3 of the plan only requires ``triton_compile_image``. The generation
image is deferred to Phase 4. The compile image is intentionally minimal so
the first remote build is fast and the dependency surface for compile-only
smoke tests stays small.

DEPENDENCY PINS (open question — verify against a successful Modal build
before depending on these for the M2/M3 full runs):

The plan marks ``torch==2.8.0``, ``triton==3.4.0``, ``numpy==2.1.0``, and
``pydantic==2.10.6`` as placeholders subject to verification. The local
development host is a Mac with no CUDA/Triton, so versions cannot be verified
against a working local install. The values below match the plan placeholders;
if a build fails or the good-ReLU smoke fails with a cryptic dtype/runtime
error, the most likely cause is a torch/triton mismatch.
"""

from __future__ import annotations

import modal

PYTHON_VERSION = "3.11"

triton_compile_image = (
    modal.Image.debian_slim(python_version=PYTHON_VERSION)
    .uv_pip_install(
        "torch==2.8.0",
        "triton==3.4.0",
        "numpy==2.1.0",
        "pydantic==2.10.6",
    )
    .add_local_python_source("cluster1", "shared")
)
