"""Shared Modal app for the TritonGen GPU harness.

There must be exactly one ``modal.App`` definition in the repository. All
remote functions and classes — generation, compile, and any future Cluster 2/3
additions — register against this single app so that ``modal app logs`` and
``modal deploy`` operate on a single coherent unit.
"""

from __future__ import annotations

import modal

app = modal.App("tritongen-gpu-harness")
