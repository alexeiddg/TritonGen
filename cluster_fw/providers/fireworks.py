"""Fireworks API provider boundary.

This module is dependency-light by design: it uses the Fireworks REST API via
``urllib`` so the repo does not need an SDK or lockfile change for the first
adapter. Modal supplies the networked runtime and the API key secret.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

ProviderApi = Literal["responses", "chat_completions"]

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
FIREWORKS_CONTROL_BASE_URL = "https://api.fireworks.ai/v1"
RESPONSES_ENDPOINT = f"{FIREWORKS_BASE_URL}/responses"
CHAT_COMPLETIONS_ENDPOINT = f"{FIREWORKS_BASE_URL}/chat/completions"
SERVERLESS_MODELS_ENDPOINT = (
    f"{FIREWORKS_CONTROL_BASE_URL}/accounts/fireworks/models"
    "?filter=supports_serverless%3Dtrue&pageSize=50"
)


@dataclass(frozen=True)
class FireworksGenerationRequest:
    """One Fireworks generation request after prompt construction."""

    model_slot: str
    model_id: str
    prompt: str
    provider_api: ProviderApi = "responses"
    temperature: float = 0.2
    max_output_tokens: int = 1536
    response_format_grammar: str | None = None

    @property
    def prompt_sha256(self) -> str:
        return _sha256(self.prompt)

    @property
    def response_format_grammar_sha256(self) -> str | None:
        if self.response_format_grammar is None:
            return None
        return _sha256(self.response_format_grammar)


Transport = Callable[[str, dict[str, str], dict[str, object]], dict[str, Any]]


def call_fireworks_with_transport(
    request: FireworksGenerationRequest,
    *,
    api_key: str,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Call Fireworks and return the normalized provider payload."""

    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY is required for Fireworks generation")
    if request.provider_api not in ("responses", "chat_completions"):
        raise ValueError(f"unsupported Fireworks provider_api: {request.provider_api!r}")
    if request.response_format_grammar and request.provider_api != "chat_completions":
        raise ValueError("Fireworks GBNF response_format requires chat_completions")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if request.provider_api == "responses":
        url = RESPONSES_ENDPOINT
        body: dict[str, object] = {
            "model": request.model_id,
            "input": request.prompt,
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
            "stream": False,
        }
    else:
        url = CHAT_COMPLETIONS_ENDPOINT
        body = {
            "model": request.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        if request.response_format_grammar is not None:
            body["response_format"] = {
                "type": "grammar",
                "grammar": request.response_format_grammar,
            }

    raw_payload = (transport or _urllib_transport)(url, headers, body)
    return normalize_fireworks_response(
        raw_payload,
        provider_api=request.provider_api,
        model_slot=request.model_slot,
        prompt=request.prompt,
        response_format_grammar=request.response_format_grammar,
    )


def list_fireworks_serverless_models(
    *,
    api_key: str,
    transport: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return Fireworks models available on serverless for this API key."""

    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY is required to list Fireworks models")
    headers = {"Authorization": f"Bearer {api_key}"}
    return (transport or _urllib_get_transport)(SERVERLESS_MODELS_ENDPOINT, headers)


def normalize_fireworks_response(
    payload: dict[str, Any],
    *,
    provider_api: ProviderApi,
    model_slot: str,
    prompt: str,
    response_format_grammar: str | None = None,
) -> dict[str, Any]:
    """Normalize known Fireworks response shapes into TritonGen metadata."""

    raw_source = _extract_response_text(payload, provider_api=provider_api)
    extracted = _extract_python_module(raw_source)
    source = extracted["source"]
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    finish_reason = _finish_reason(payload, provider_api=provider_api)
    response_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
    model_id = _string_or_none(payload.get("model"))

    return {
        "provider": "fireworks",
        "provider_api": provider_api,
        "provider_model_id": model_id,
        "provider_model_snapshot": model_id,
        "model_slot": model_slot,
        "source": source,
        "finish_reason": finish_reason,
        "provider_response_id": _string_or_none(payload.get("id")),
        "provider_request_id": _provider_request_id(payload),
        "input_tokens": _usage_value(usage, "input_tokens", "prompt_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens", "completion_tokens"),
        "reasoning_tokens": _reasoning_tokens(usage),
        "cached_input_tokens": _cached_input_tokens(usage),
        "prompt_sha256": _sha256(prompt),
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "source_sha256": _sha256(source),
        "raw_source_sha256": _sha256(raw_source),
        "source_extraction_method": extracted["method"],
        "source_extraction_warning": extracted["warning"],
        "response_format_type": "grammar" if response_format_grammar else None,
        "response_format_grammar_sha256": (
            _sha256(response_format_grammar) if response_format_grammar else None
        ),
        "provider_error_type": _provider_error_type(payload),
        "provider_error_msg": _provider_error_msg(payload),
        "raw_response_shape_version": _raw_shape_version(provider_api),
    }


def _urllib_transport(
    url: str,
    headers: dict[str, str],
    body: dict[str, object],
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        model = body.get("model")
        hint = ""
        if exc.code == 404 and isinstance(model, str):
            hint = (
                " Hint: this usually means the Fireworks model is not available "
                "to this API key on the selected endpoint. Some frontier models "
                "require Deploy on Demand; pass the accessible deployment/model "
                "ID with --model-id-overrides SLOT=MODEL_ID."
            )
        raise RuntimeError(
            f"Fireworks HTTP {exc.code} for model={model!r}: {detail[:500]}{hint}"
        ) from exc


def _urllib_get_transport(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fireworks HTTP {exc.code}: {detail[:500]}") from exc


def _extract_response_text(payload: dict[str, Any], *, provider_api: ProviderApi) -> str:
    if provider_api == "responses":
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text:
            return output_text
        texts: list[str] = []
        for item in _list(payload.get("output")):
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            for content in _list(item.get("content")):
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"reasoning", "summary_text"}:
                    continue
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
        return "".join(texts)

    choices = _list(payload.get("choices"))
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
    return ""


_FENCED_CODE_RE = re.compile(
    r"```(?:python|py)?[ \t]*\n(?P<code>.*?)(?:\n```|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_MODULE_START_RE = re.compile(r"(?m)^[ \t]*import torch\s*$")


def _extract_python_module(raw_source: str) -> dict[str, str | None]:
    """Best-effort extraction of the Python module from provider prose."""

    if not raw_source.strip():
        return {"source": "", "method": "empty", "warning": "no_text"}

    fallback: dict[str, str | None] | None = None
    for match in _FENCED_CODE_RE.finditer(raw_source):
        candidate = match.group("code")
        if _looks_like_kernel_module(candidate):
            source, warning = _trim_to_parseable_module(candidate)
            result = {
                "source": source,
                "method": "markdown_fence",
                "warning": warning,
            }
            if _is_usable_extracted_module(source, warning):
                return result
            fallback = fallback or result

    for module_start in _MODULE_START_RE.finditer(raw_source):
        candidate = raw_source[module_start.start() :]
        if not _looks_like_kernel_module(candidate):
            continue
        source, warning = _trim_to_parseable_module(candidate)
        result = {
            "source": source,
            "method": "module_start",
            "warning": warning,
        }
        if _is_usable_extracted_module(source, warning):
            return result
        fallback = fallback or result

    if fallback is not None:
        fallback["warning"] = fallback["warning"] or "kernel_module_candidate_did_not_parse"
        return fallback

    source = raw_source.strip()
    if source:
        source += "\n"
    return {
        "source": source,
        "method": "raw_text",
        "warning": "no_python_module_boundary_found",
    }


def _looks_like_kernel_module(source: str) -> bool:
    return (
        "import torch" in source
        and "import triton" in source
        and "triton.language" in source
        and "@triton.jit" in source
        and "def " in source
    )


def _is_usable_extracted_module(source: str, warning: str | None) -> bool:
    return (
        warning in {None, "trimmed_trailing_non_python_text"}
        and _looks_like_kernel_module(source)
    )


def _trim_to_parseable_module(source: str) -> tuple[str, str | None]:
    cleaned = _dedent_from_module_start(source)
    if not cleaned:
        return "", "empty_extracted_block"
    if _parseable_python(cleaned):
        return cleaned + "\n", None

    lines = cleaned.splitlines()
    for end in range(len(lines) - 1, 0, -1):
        candidate = "\n".join(lines[:end]).rstrip()
        if "def " not in candidate:
            continue
        if _parseable_python(candidate):
            return candidate + "\n", "trimmed_trailing_non_python_text"

    return cleaned + "\n", "extracted_source_does_not_parse"


def _dedent_from_module_start(source: str) -> str:
    cleaned = source.strip()
    lines = cleaned.splitlines()
    for line in lines:
        if not line.strip():
            continue
        match = re.match(r"^([ \t]+)import torch\s*$", line)
        if not match:
            return cleaned
        indent = match.group(1)
        return "\n".join(
            item[len(indent) :] if item.startswith(indent) else item
            for item in lines
        ).strip()
    return cleaned


def _parseable_python(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def _finish_reason(payload: dict[str, Any], *, provider_api: ProviderApi) -> str | None:
    if provider_api == "responses":
        incomplete = payload.get("incomplete_details")
        if isinstance(incomplete, dict) and incomplete.get("reason"):
            return str(incomplete["reason"])
        return _string_or_none(payload.get("status"))
    choices = _list(payload.get("choices"))
    if choices and isinstance(choices[0], dict):
        return _string_or_none(choices[0].get("finish_reason"))
    return None


def _provider_request_id(payload: dict[str, Any]) -> str | None:
    for key in ("request_id", "x-request-id", "fireworks_request_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _provider_error_type(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict):
        return _string_or_none(error.get("type") or error.get("code"))
    return None


def _provider_error_msg(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if isinstance(error, dict):
        message = _string_or_none(error.get("message"))
        return message[:500] if message else None
    return None


def _usage_value(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return None


def _reasoning_tokens(usage: dict[str, Any]) -> int | None:
    direct = _usage_value(usage, "reasoning_tokens")
    if direct is not None:
        return direct
    for key in ("completion_tokens_details", "output_tokens_details"):
        details = usage.get(key)
        if isinstance(details, dict):
            value = details.get("reasoning_tokens")
            if isinstance(value, int):
                return value
    return None


def _cached_input_tokens(usage: dict[str, Any]) -> int | None:
    for key in ("prompt_tokens_details", "input_tokens_details"):
        details = usage.get(key)
        if isinstance(details, dict):
            value = details.get("cached_tokens") or details.get("cached_input_tokens")
            if isinstance(value, int):
                return value
    return None


def _raw_shape_version(provider_api: ProviderApi) -> str:
    return f"fireworks_{provider_api}_v1"


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
