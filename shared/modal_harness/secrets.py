"""Optional HuggingFace secret lookup for the TritonGen GPU harness.

The HF secret is only required when the development model is gated or private.
The currently selected dev model — ``Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`` — is
public, so the smoke tests must work with no secret created.

To opt in once a gated model is selected:

    modal secret create huggingface-token HF_TOKEN=<token>
    export TRITONGEN_MODAL_HF_SECRET=huggingface-token

When the env var is unset, ``hf_secrets`` is an empty list and no secret is
attached to remote functions, preventing smoke tests from failing on a
missing-secret lookup.
"""

from __future__ import annotations

import os

import modal

# Computed once at module import time. Changing TRITONGEN_MODAL_HF_SECRET
# at runtime does NOT take effect — restart the process (or the Modal app)
# after creating or rotating the secret.
hf_secrets: list[modal.Secret] = (
    [modal.Secret.from_name(os.environ["TRITONGEN_MODAL_HF_SECRET"])]
    if os.environ.get("TRITONGEN_MODAL_HF_SECRET")
    else []
)

# Fireworks API generation uses a separate Modal Secret. This must resolve to
# the same Modal object in the local CLI process and in the remote container;
# otherwise Modal sees different function dependencies during hydration.
FIREWORKS_MODAL_SECRET_NAME = os.environ.get(
    "TRITONGEN_MODAL_FIREWORKS_SECRET",
    "fireworks-api",
)
fireworks_secrets: list[modal.Secret] = [
    modal.Secret.from_name(FIREWORKS_MODAL_SECRET_NAME)
]
