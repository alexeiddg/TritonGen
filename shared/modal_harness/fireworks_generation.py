"""Modal remote Fireworks generation surface."""

from __future__ import annotations

import os
from typing import Any

from shared.modal_harness.app import app
from shared.modal_harness.images import fireworks_api_image
from shared.modal_harness.secrets import fireworks_secrets


@app.function(
    image=fireworks_api_image,
    secrets=fireworks_secrets,
    timeout=300,
)
def generate_fireworks_remote(request_payload: dict[str, Any]) -> dict[str, Any]:
    """Generate one kernel source through Fireworks inside Modal."""

    from cluster_fw.providers.fireworks import (
        FireworksGenerationRequest,
        call_fireworks_with_transport,
    )

    request = FireworksGenerationRequest(**request_payload)
    return call_fireworks_with_transport(
        request,
        api_key=os.environ.get("FIREWORKS_API_KEY", ""),
    )


@app.function(
    image=fireworks_api_image,
    secrets=fireworks_secrets,
    timeout=120,
)
def list_fireworks_serverless_models_remote() -> dict[str, Any]:
    """List Fireworks serverless models visible to the configured API key."""

    from cluster_fw.providers.fireworks import list_fireworks_serverless_models

    return list_fireworks_serverless_models(
        api_key=os.environ.get("FIREWORKS_API_KEY", ""),
    )
