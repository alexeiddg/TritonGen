"""Narrow Cluster 1 adapter for remote generation."""

from __future__ import annotations

from shared.modal_harness.generation import (
    DEFAULT_GENERATION_GPU,
    remote_generator_for_gpu,
)
from shared.modal_harness.schemas import RemoteGenerationRequest, RemoteGenerationResult


def generate_source_modal(
    *,
    prompt: str,
    model_id: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    grammar_active: bool,
    generation_seed: int | None,
    temperature: float,
    max_new_tokens: int,
    run_id: str,
    modal_generation_gpu: str = DEFAULT_GENERATION_GPU,
) -> RemoteGenerationResult:
    factor_cell = "G" if grammar_active else "none"
    req = RemoteGenerationRequest(
        factor_cell=factor_cell,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        prompt=prompt,
        model_id=model_id,
        grammar_active=grammar_active,
        generation_seed=generation_seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        run_id=run_id,
    )
    generator_cls = remote_generator_for_gpu(modal_generation_gpu)
    result_dict = generator_cls(model_id=model_id).generate_one.remote(req.model_dump())
    return RemoteGenerationResult(**result_dict)
