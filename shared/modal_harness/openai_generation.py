"""Remote OpenAI API generation for external TritonGen baselines.

This module deliberately keeps local imports light. The OpenAI SDK is installed
only in the Modal image and imported inside the remote function.
"""

from __future__ import annotations

from typing import Any

from shared.modal_harness.app import app
from shared.modal_harness.images import openai_generation_image
from shared.modal_harness.runtime import current_modal_ids
from shared.modal_harness.secrets import openai_secrets

DEFAULT_OPENAI_MODEL = "gpt-5.1"


@app.function(
    image=openai_generation_image,
    memory=2048,
    cpu=1.0,
    timeout=240,
    max_containers=10,
    min_containers=0,
    scaledown_window=60,
    secrets=openai_secrets,
)
def remote_openai_generate_one(req_dict: dict[str, Any]) -> dict[str, Any]:
    """Generate one kernel source with OpenAI Responses API.

    The caller receives errors as raised Modal call failures. Routine retry is
    kept in the local entrypoint so partial JSONL resume behavior is visible.
    """

    import os

    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not available inside Modal. Create a Modal secret "
            "and export TRITONGEN_MODAL_OPENAI_SECRET before running."
        )

    call_id, input_id = current_modal_ids()
    client = OpenAI(api_key=api_key)
    response = client.responses.create(**_build_responses_kwargs(req_dict))

    return {
        "source": _extract_response_text(response),
        "usage": _usage_dict(response),
        "model": getattr(response, "model", None) or req_dict["model"],
        "modal_function_call_id": call_id,
        "modal_input_id": input_id,
        "api_surface": "openai_responses",
    }


def _build_responses_kwargs(req: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": req["model"],
        "input": req["prompt"],
        "max_output_tokens": int(req["max_output_tokens"]),
    }
    temperature = req.get("temperature")
    if temperature is not None:
        kwargs["temperature"] = float(temperature)
    reasoning_effort = req.get("reasoning_effort")
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return kwargs


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def _usage_dict(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}

    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }
