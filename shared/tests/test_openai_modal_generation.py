from __future__ import annotations

from types import SimpleNamespace

from shared.modal_harness.openai_generation import (
    DEFAULT_OPENAI_MODEL,
    _build_responses_kwargs,
    _extract_response_text,
    _usage_dict,
)


def test_build_responses_kwargs_minimal_request() -> None:
    kwargs = _build_responses_kwargs(
        {
            "model": DEFAULT_OPENAI_MODEL,
            "prompt": "write code",
            "temperature": 0.2,
            "max_output_tokens": 2048,
            "reasoning_effort": None,
        }
    )

    assert kwargs == {
        "model": DEFAULT_OPENAI_MODEL,
        "input": "write code",
        "temperature": 0.2,
        "max_output_tokens": 2048,
    }


def test_build_responses_kwargs_includes_reasoning_when_requested() -> None:
    kwargs = _build_responses_kwargs(
        {
            "model": DEFAULT_OPENAI_MODEL,
            "prompt": "write code",
            "temperature": 0.2,
            "max_output_tokens": 2048,
            "reasoning_effort": "low",
        }
    )

    assert kwargs["reasoning"] == {"effort": "low"}


def test_extract_response_text_prefers_output_text() -> None:
    response = SimpleNamespace(output_text="import torch\n")

    assert _extract_response_text(response) == "import torch\n"


def test_extract_response_text_falls_back_to_output_items() -> None:
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(text="import torch\n"),
                    SimpleNamespace(text="import triton\n"),
                ]
            )
        ]
    )

    assert _extract_response_text(response) == "import torch\nimport triton\n"


def test_usage_dict_handles_absent_usage() -> None:
    assert _usage_dict(SimpleNamespace()) == {}


def test_usage_dict_extracts_token_counts() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=11, output_tokens=22, total_tokens=33)
    )

    assert _usage_dict(response) == {
        "input_tokens": 11,
        "output_tokens": 22,
        "total_tokens": 33,
    }
