"""Narrow Cluster 1 adapter for remote generation."""

from __future__ import annotations

from shared.modal_harness.generation import (
    DEFAULT_GENERATION_GPU,
    remote_generator_for_gpu,
)
from shared.modal_harness.schemas import RemoteGenerationRequest, RemoteGenerationResult
from cluster1.generation.grammar_variants import (
    DEFAULT_GRAMMAR_PATH,
    grammar_path_for_cell,
)
from cluster1.generation.provenance import (
    normalize_explicit_revision,
    resolve_tokenizer_revision,
)
from cluster1.results.dataclass import grammar_variant_for_cell


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
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
    grammar_variant: str | None = None,
    grammar_path: str | None = None,
    modal_generation_gpu: str = DEFAULT_GENERATION_GPU,
) -> RemoteGenerationResult:
    factor_cell = "G" if grammar_active else "none"
    resolved_variant = grammar_variant_for_cell(
        factor_cell=factor_cell,
        grammar_active=grammar_active,
        grammar_variant=grammar_variant if grammar_active else None,
    )
    resolved_grammar_path = grammar_path_for_cell(
        grammar_active=grammar_active,
        grammar_variant=resolved_variant,
    )
    if grammar_path != resolved_grammar_path and grammar_path is not None:
        raise ValueError(
            "grammar_path is selected by grammar_variant; expected "
            f"{resolved_grammar_path!r}, got {grammar_path!r}"
        )
    resolved_model_revision = normalize_explicit_revision(
        model_revision,
        field_name="model_revision",
    )
    resolved_tokenizer_revision = resolve_tokenizer_revision(
        model_id=model_id,
        model_revision=resolved_model_revision,
        tokenizer_revision=tokenizer_revision,
    )
    req = RemoteGenerationRequest(
        factor_cell=factor_cell,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        prompt=prompt,
        model_id=model_id,
        model_revision=resolved_model_revision,
        tokenizer_revision=resolved_tokenizer_revision,
        grammar_active=grammar_active,
        grammar_variant=resolved_variant,
        grammar_path=resolved_grammar_path,
        generation_seed=generation_seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        run_id=run_id,
    )
    generator_cls = remote_generator_for_gpu(modal_generation_gpu)
    result_dict = generator_cls(
        model_id=model_id,
        model_revision=resolved_model_revision or "",
        tokenizer_revision=resolved_tokenizer_revision or "",
        generation_gpu=modal_generation_gpu,
    ).generate_one.remote(req.model_dump())
    return RemoteGenerationResult(**result_dict)
