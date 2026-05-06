"""Shared Modal volumes for the TritonGen GPU harness.

Both volumes use ``create_if_missing=True`` so the first remote run provisions
them on demand. Do not pre-create these via ``modal volume create``.

- ``tritongen-hf-cache``: HuggingFace model and tokenizer cache. Mounted at
  ``/cache/huggingface`` on the generation image.
- ``tritongen-eval-artifacts``: Reserved for larger remote artifacts. For
  Cluster 1 the authoritative result log remains local JSONL under
  ``outputs/cluster1/``; do not concurrently append to a single file inside
  this volume.
"""

from __future__ import annotations

import modal

hf_cache_volume = modal.Volume.from_name(
    "tritongen-hf-cache",
    create_if_missing=True,
)

artifact_volume = modal.Volume.from_name(
    "tritongen-eval-artifacts",
    create_if_missing=True,
)
