"""Modal image definitions for the TritonGen GPU harness.

``triton_compile_image`` is intentionally minimal so compile-only smoke tests
keep a small dependency surface. ``llm_generation_image`` carries the heavier
Hugging Face and constrained-decoding stack used by Phase 4 remote generation.

The compile image pins are intentionally fixed for the Phase 3 smoke gate:
``torch==2.8.0``, ``triton==3.4.0``, ``numpy==2.1.0``, and
``pydantic==2.10.6``.

The generation image keeps ``autoawq==0.2.8`` paired with a compatible
``transformers`` release. Do not pair AutoAWQ 0.2.8 with Transformers 4.56.0.
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
    .add_local_python_source("cluster1", "cluster2", "shared")
)

llm_generation_image = (
    modal.Image.debian_slim(python_version=PYTHON_VERSION)
    .uv_pip_install(
        "torch==2.8.0",
        "triton==3.4.0",
        "numpy==2.1.0",
        "pydantic==2.10.6",
    )
    .uv_pip_install(
        "transformers==4.47.1",
        "accelerate==1.2.1",
        "tokenizers==0.21.1",
        "autoawq==0.2.8",
        "xgrammar==0.1.33",
        "lark==1.2.2",
        "huggingface_hub[hf_transfer]==0.34.0",
        extra_options="--no-build-isolation",
    )
    .env(
        {
            "HF_HOME": "/cache/huggingface",
            "HF_HUB_CACHE": "/cache/huggingface/hub",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
    .add_local_python_source("cluster1", "cluster2", "shared")
    .add_local_dir("cluster1/grammar", "/root/cluster1/grammar")
)
