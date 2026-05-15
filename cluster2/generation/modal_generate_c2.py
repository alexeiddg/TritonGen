"""Local adapter for isolated Cluster 2 Modal generation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cluster2.constants import DEFAULT_C2_MODAL_GENERATION_GPU
from cluster2.modal.generation import (
    REMOTE_C2_GENERATION_GPU,
    remote_c2_generator_for_gpu,
    validate_remote_c2_generation_payload,
)
from cluster2.modal.schemas import EvalIdentity, RemoteC2GenerationRequest


RemoteC2GenerationCall = Callable[[dict[str, Any]], dict[str, Any]]


def build_c2_generation_request(
    *,
    identity: EvalIdentity | dict[str, Any],
    prompt: str,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    generation_seed: int | None,
    temperature: float = 0.2,
    max_new_tokens: int = 1024,
    grammar_variant: str | None = None,
) -> RemoteC2GenerationRequest:
    """Build a strict C2 generation request for ``C`` or ``G+C`` only."""

    resolved_identity = (
        identity if isinstance(identity, EvalIdentity) else EvalIdentity(**identity)
    )
    return RemoteC2GenerationRequest(
        identity=resolved_identity,
        prompt=prompt,
        model_id=model_id,
        model_revision=model_revision,
        tokenizer_revision=tokenizer_revision,
        generation_seed=generation_seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        grammar_variant=grammar_variant,
    )


def generate_source_c2_modal(
    *,
    identity: EvalIdentity | dict[str, Any],
    prompt: str,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    generation_seed: int | None,
    temperature: float = 0.2,
    max_new_tokens: int = 1024,
    grammar_variant: str | None = None,
    modal_generation_gpu: str = DEFAULT_C2_MODAL_GENERATION_GPU,
    remote_call: RemoteC2GenerationCall | None = None,
) -> dict[str, Any]:
    """Generate one allowed C2 condition through the isolated Modal surface.

    ``remote_call`` is an injection point for local tests. When omitted, this
    adapter invokes ``RemoteC2Generator`` on the explicit C2 L4 configuration.
    """

    request = build_c2_generation_request(
        identity=identity,
        prompt=prompt,
        model_id=model_id,
        model_revision=model_revision,
        tokenizer_revision=tokenizer_revision,
        generation_seed=generation_seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        grammar_variant=grammar_variant,
    )
    if modal_generation_gpu != REMOTE_C2_GENERATION_GPU:
        raise ValueError(
            "C2 generation must use explicit L4 Modal GPU; got "
            f"{modal_generation_gpu!r}"
        )

    if remote_call is None:
        generator_cls = remote_c2_generator_for_gpu(modal_generation_gpu)
        remote_call = generator_cls(
            model_id=model_id,
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
        ).generate_one.remote

    payload = remote_call(request.model_dump())
    return validate_remote_c2_generation_payload(payload)


def generate_source_modal_c2(**kwargs: Any) -> dict[str, Any]:
    """Backward-compatible alias for callers that mirror Cluster 1 naming."""

    return generate_source_c2_modal(**kwargs)


def configured_modal_generation_gpu() -> str:
    """Return the C2 generation GPU this adapter is allowed to use."""

    return REMOTE_C2_GENERATION_GPU
