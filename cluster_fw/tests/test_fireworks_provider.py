from __future__ import annotations

import hashlib

from cluster_fw.providers.fireworks import (
    FireworksGenerationRequest,
    call_fireworks_with_transport,
    list_fireworks_serverless_models,
    normalize_fireworks_response,
)


def test_normalize_responses_api_output_text_and_usage() -> None:
    payload = {
        "id": "resp_123",
        "model": "accounts/fireworks/models/deepseek-r1",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "import torch\n"},
                    {"type": "reasoning", "text": "hidden"},
                ],
            }
        ],
        "usage": {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
            "completion_tokens_details": {"reasoning_tokens": 3},
        },
    }

    normalized = normalize_fireworks_response(
        payload,
        provider_api="responses",
        model_slot="FW-A",
        prompt="prompt",
    )

    assert normalized["provider"] == "fireworks"
    assert normalized["provider_api"] == "responses"
    assert normalized["provider_response_id"] == "resp_123"
    assert normalized["provider_model_id"] == "accounts/fireworks/models/deepseek-r1"
    assert normalized["source"] == "import torch\n"
    assert normalized["input_tokens"] == 11
    assert normalized["output_tokens"] == 7
    assert normalized["reasoning_tokens"] == 3
    assert normalized["prompt_sha256"] == hashlib.sha256(b"prompt").hexdigest()
    assert normalized["source_sha256"] == hashlib.sha256(b"import torch\n").hexdigest()


def test_normalize_chat_completions_shape() -> None:
    payload = {
        "id": "chatcmpl_1",
        "model": "accounts/fireworks/models/llama-v3p1-405b-instruct",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "import triton\n"},
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 6},
    }

    normalized = normalize_fireworks_response(
        payload,
        provider_api="chat_completions",
        model_slot="FW-B",
        prompt="prompt",
    )

    assert normalized["source"] == "import triton\n"
    assert normalized["finish_reason"] == "stop"
    assert normalized["input_tokens"] == 5
    assert normalized["output_tokens"] == 6


def test_normalize_extracts_python_from_markdown_prose() -> None:
    code = (
        "import torch\n"
        "import triton\n"
        "import triton.language as tl\n\n"
        "@triton.jit\n"
        "def _relu_kernel(x, y):\n"
        "    return\n\n"
        "def relu(x: torch.Tensor) -> torch.Tensor:\n"
        "    return x\n"
    )
    payload = {
        "model": "accounts/fireworks/models/kimi-k2p5",
        "status": "completed",
        "output_text": (
            "I will solve it step by step.\n\n"
            "```python\n"
            f"{code}"
            "```\n\n"
            "That is the implementation."
        ),
    }

    normalized = normalize_fireworks_response(
        payload,
        provider_api="responses",
        model_slot="FW-A",
        prompt="prompt",
    )

    assert normalized["source"] == code
    assert normalized["source_extraction_method"] == "markdown_fence"
    assert normalized["source_extraction_warning"] is None
    assert normalized["raw_source_sha256"] != normalized["source_sha256"]


def test_normalize_trims_trailing_non_python_from_unclosed_fence() -> None:
    payload = {
        "model": "accounts/fireworks/models/kimi-k2p5",
        "status": "completed",
        "output_text": (
            "```python\n"
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            "@triton.jit\n"
            "def _relu_kernel(x, y):\n"
            "    return\n\n"
            "def relu(x: torch.Tensor) -> torch.Tensor:\n"
            "    return x\n"
            "Now I will explain why this works"
        ),
    }

    normalized = normalize_fireworks_response(
        payload,
        provider_api="responses",
        model_slot="FW-A",
        prompt="prompt",
    )

    assert normalized["source"].endswith("    return x\n")
    assert "Now I will explain" not in normalized["source"]
    assert normalized["source_extraction_warning"] == "trimmed_trailing_non_python_text"


def test_normalize_ignores_import_only_fence_before_real_module() -> None:
    real_module = (
        "import torch\n"
        "import triton\n"
        "import triton.language as tl\n\n"
        "@triton.jit\n"
        "def _relu_kernel(x, y):\n"
        "    return\n\n"
        "def relu(x: torch.Tensor) -> torch.Tensor:\n"
        "    return x\n"
    )
    payload = {
        "model": "accounts/fireworks/models/kimi-k2p5",
        "status": "completed",
        "output_text": (
            "First, the imports:\n"
            "```python\n"
            "import torch\n"
            "   import triton\n"
            "   import triton.language as tl\n"
            "```\n\n"
            "Now the real module:\n"
            "```python\n"
            f"{real_module}"
            "```"
        ),
    }

    normalized = normalize_fireworks_response(
        payload,
        provider_api="responses",
        model_slot="FW-A",
        prompt="prompt",
    )

    assert normalized["source"] == real_module
    assert normalized["source_extraction_method"] == "markdown_fence"
    assert normalized["source_extraction_warning"] is None


def test_call_fireworks_with_transport_builds_responses_request() -> None:
    seen: dict[str, object] = {}

    def transport(url: str, headers: dict[str, str], body: dict[str, object]) -> dict:
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = body
        return {
            "id": "resp_transport",
            "model": body["model"],
            "status": "completed",
            "output_text": "import torch\n",
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }

    request = FireworksGenerationRequest(
        model_slot="FW-A",
        model_id="accounts/fireworks/models/deepseek-r1",
        prompt="write a kernel",
        provider_api="responses",
        temperature=0.2,
        max_output_tokens=1536,
    )

    normalized = call_fireworks_with_transport(
        request,
        api_key="fw_test",
        transport=transport,
    )

    assert seen["url"] == "https://api.fireworks.ai/inference/v1/responses"
    assert seen["headers"] == {
        "Authorization": "Bearer fw_test",
        "Content-Type": "application/json",
    }
    assert seen["body"] == {
        "model": "accounts/fireworks/models/deepseek-r1",
        "input": "write a kernel",
        "temperature": 0.2,
        "max_output_tokens": 1536,
        "store": False,
        "stream": False,
    }
    assert normalized["source"] == "import torch\n"


def test_call_fireworks_with_transport_builds_chat_grammar_request() -> None:
    seen: dict[str, object] = {}

    def transport(url: str, headers: dict[str, str], body: dict[str, object]) -> dict:
        seen["url"] = url
        seen["body"] = body
        return {
            "id": "chat_grammar",
            "model": body["model"],
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "import torch\n"},
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }

    normalized = call_fireworks_with_transport(
        FireworksGenerationRequest(
            model_slot="FW-A",
            model_id="accounts/fireworks/models/minimax-m2p7",
            prompt="write a kernel",
            provider_api="chat_completions",
            response_format_grammar='root ::= "ok"',
        ),
        api_key="fw_test",
        transport=transport,
    )

    assert seen["url"] == "https://api.fireworks.ai/inference/v1/chat/completions"
    assert seen["body"]["response_format"] == {
        "type": "grammar",
        "grammar": 'root ::= "ok"',
    }
    assert normalized["response_format_type"] == "grammar"
    assert normalized["response_format_grammar_sha256"] == hashlib.sha256(
        b'root ::= "ok"'
    ).hexdigest()


def test_list_fireworks_serverless_models_uses_control_api_filter() -> None:
    seen: dict[str, object] = {}

    def transport(url: str, headers: dict[str, str]) -> dict:
        seen["url"] = url
        seen["headers"] = headers
        return {
            "models": [
                {
                    "name": "accounts/fireworks/models/example",
                    "displayName": "Example",
                }
            ]
        }

    payload = list_fireworks_serverless_models(
        api_key="fw_test",
        transport=transport,
    )

    assert seen["url"] == (
        "https://api.fireworks.ai/v1/accounts/fireworks/models"
        "?filter=supports_serverless%3Dtrue&pageSize=50"
    )
    assert seen["headers"] == {"Authorization": "Bearer fw_test"}
    assert payload["models"][0]["name"] == "accounts/fireworks/models/example"
