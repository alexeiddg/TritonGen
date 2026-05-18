"""Remote Modal class for LLM-backed kernel generation.

Top-level imports are intentionally restricted to ``modal``, this package, and
``importlib.resources`` / ``pathlib``. Anything that transitively pulls in
``torch``, ``transformers``, ``xgrammar``, or ``autoawq`` is deferred into
``load_model()`` / ``generate_one()`` so the local Cluster 1 adapter can
``import shared.modal_harness.generation`` without dragging the heavy ML
stack into the local process.
"""

from importlib import resources
from pathlib import Path

import modal

from shared.modal_harness.app import app
from shared.modal_harness.images import llm_generation_image
from shared.modal_harness.runtime import current_modal_ids
from shared.modal_harness.schemas import (
    RemoteGenerationRequest,
    RemoteGenerationResult,
    dtype_name_to_bytes,
)
from shared.modal_harness.secrets import hf_secrets
from shared.modal_harness.volumes import hf_cache_volume

DEFAULT_GENERATION_GPU = "L40S"
SUPPORTED_GENERATION_GPUS = frozenset({"L40S", "L4", "A10G"})


@app.cls(
    image=llm_generation_image,
    gpu=DEFAULT_GENERATION_GPU,
    memory=32768,
    cpu=8.0,
    timeout=900,
    max_containers=2,
    min_containers=0,
    scaledown_window=600,
    volumes={"/cache/huggingface": hf_cache_volume},
    secrets=hf_secrets,
)
class RemoteGenerator:
    """Load one model per container and serve generation requests."""

    model_id: str = modal.parameter(); model_revision: str = modal.parameter(default=""); tokenizer_revision: str = modal.parameter(default=""); generation_gpu: str = modal.parameter(default=DEFAULT_GENERATION_GPU)

    @modal.enter()
    def load_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch; self.requested_model_revision = self.model_revision or None; self.requested_tokenizer_revision = self.tokenizer_revision or None
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            **_revision_kwargs(self.requested_tokenizer_revision),
        )
        # ``transformers==4.47.1`` (pinned in ``llm_generation_image``)
        # documents ``torch_dtype=`` for big-model loading. Newer releases
        # document the renamed ``dtype=`` kwarg; stay on ``torch_dtype=``
        # while this image pin holds.
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map="auto",
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16,
            trust_remote_code=True,
            **_revision_kwargs(self.requested_model_revision),
        )
        if hasattr(self.model, "eval"):
            self.model.eval()

        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        pad_token_id = getattr(self.tokenizer, "pad_token_id", None)
        if pad_token_id is not None:
            self.model.generation_config.pad_token_id = pad_token_id

        self.device = getattr(self.model, "device", None); self.model_revision, self.tokenizer_revision = _observed_model_tokenizer_revisions(self); self.tokenizer_grammar_id = _resolve_tokenizer_grammar_id(self.model_id, self.tokenizer_revision)
    @modal.method()
    def generate_one(self, req_dict: dict) -> dict:
        from cluster1.constraints.hardware_checker import HardwareChecker
        from cluster1.generation.constrained_gen import generate_source
        from cluster1.generation.grammar_loader import load_compiled_grammar
        from cluster1.generation.provenance import (
            grammar_provenance,
            modal_image_provenance,
            runtime_versions,
        )
        from cluster1.grammar.triton_kernel_validator import validate_source_layers
        from cluster1.results.dataclass import GENERATION_METADATA_SCHEMA_VERSION

        req = RemoteGenerationRequest(**req_dict)
        if req.model_id != self.model_id:
            raise ValueError(
                f"request model_id {req.model_id!r} does not match loaded model "
                f"{self.model_id!r}"
            )

        compiled_grammar = None
        hardware_checker = None
        resolved_grammar_path = None
        grammar_metadata = {
            "grammar_sha": None,
            "grammar_path": None,
            "grammar_variant": req.grammar_variant,
        }
        if req.grammar_active:
            assert req.grammar_path is not None
            resolved_grammar_path = _resolve_grammar_path(req.grammar_path)
            grammar_metadata = grammar_provenance(
                resolved_grammar_path,
                grammar_variant=req.grammar_variant,
            )
            compiled_grammar = load_compiled_grammar(
                resolved_grammar_path,
                _compiled_grammar_tokenizer_id(self, req.model_id),
            )
            hardware_checker = HardwareChecker(dtype_bytes=dtype_name_to_bytes(req.dtype))

        call_id, input_id = current_modal_ids()
        with self.torch.inference_mode():
            decoded = generate_source(
                prompt=req.prompt,
                model=self.model,
                tokenizer=self.tokenizer,
                grammar_active=req.grammar_active,
                compiled_grammar=compiled_grammar,
                hardware_checker=hardware_checker,
                max_new_tokens=req.max_new_tokens,
                temperature=req.temperature,
                seed=req.generation_seed,
            )

        validation_fields = {
            "gbnf_parse_valid": None,
            "semantic_valid": None,
            "grammar_valid": None,
            "rejection_layer": None,
        }
        if req.grammar_active:
            assert resolved_grammar_path is not None
            validation = validate_source_layers(
                decoded.source,
                grammar_path=Path(resolved_grammar_path),
            )
            validation_fields = validation.to_row_fields()

        runtime_metadata = runtime_versions()
        image_metadata = modal_image_provenance(
            extra={
                "modal_generation_gpu": self.generation_gpu,
            }
        )
        result = RemoteGenerationResult(
            source=decoded.source,
            model_id=req.model_id,
            grammar_active=req.grammar_active,
            grammar_variant=req.grammar_variant,
            grammar_sha=grammar_metadata["grammar_sha"],
            grammar_path=grammar_metadata["grammar_path"],
            gbnf_parse_valid=validation_fields["gbnf_parse_valid"],
            semantic_valid=validation_fields["semantic_valid"],
            grammar_valid=validation_fields["grammar_valid"],
            rejection_layer=validation_fields["rejection_layer"],
            stop_reason=decoded.stop_reason,
            xgrammar_version=runtime_metadata["xgrammar_version"],
            transformers_version=runtime_metadata["transformers_version"],
            tokenizers_version=runtime_metadata["tokenizers_version"],
            model_revision=getattr(self, "model_revision", "unknown"),
            tokenizer_revision=getattr(self, "tokenizer_revision", "unknown"),
            modal_image_sha=image_metadata["modal_image_sha"],
            modal_image_provenance_sha256=image_metadata[
                "modal_image_provenance_sha256"
            ],
            modal_image_provenance_components=image_metadata[
                "modal_image_provenance_components"
            ],
            generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
            masked_token_rate=decoded.masked_token_rate if req.grammar_active else None,
            generation_seed=decoded.generation_seed,
            temperature=decoded.temperature,
            run_id=req.run_id,
            modal_function_call_id=call_id,
            modal_input_id=input_id,
        )
        return result.model_dump()


def _revision_kwargs(revision: str | None) -> dict[str, str]:
    return {"revision": revision} if revision is not None else {}


def _observed_model_tokenizer_revisions(generator) -> tuple[str, str]:
    from cluster1.generation.provenance import model_tokenizer_revisions

    revisions = model_tokenizer_revisions(
        generator.model,
        generator.tokenizer,
        model_revision=generator.requested_model_revision,
        tokenizer_revision=generator.requested_tokenizer_revision,
    )
    return revisions["model_revision"], revisions["tokenizer_revision"]


def remote_generator_for_gpu(gpu: str = DEFAULT_GENERATION_GPU):
    """Return the RemoteGenerator class configured for the requested GPU."""
    if gpu not in SUPPORTED_GENERATION_GPUS:
        allowed = ", ".join(sorted(SUPPORTED_GENERATION_GPUS))
        raise ValueError(f"unsupported generation GPU {gpu!r}; allowed: {allowed}")
    if gpu == DEFAULT_GENERATION_GPU:
        return RemoteGenerator
    return RemoteGenerator.with_options(gpu=gpu)


def _resolve_grammar_path(grammar_path: str) -> str:
    requested = Path(grammar_path)
    if requested.is_file():
        return str(requested)

    resource_parts = requested.parts
    if resource_parts and resource_parts[0] == "cluster1":
        resource_parts = resource_parts[1:]

    candidate = resources.files("cluster1").joinpath(*resource_parts)
    if candidate.is_file():
        return str(candidate)

    raise FileNotFoundError(f"grammar file not found: {grammar_path}")


_TOKENIZER_SNAPSHOT_ALLOW_PATTERNS = (
    "added_tokens.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "vocab.json",
    "vocab.txt",
)


def _resolve_tokenizer_grammar_id(model_id: str, tokenizer_revision: str | None) -> str:
    from shared.generation_metadata import UNKNOWN

    if tokenizer_revision in (None, "", UNKNOWN):
        return model_id

    from huggingface_hub import snapshot_download

    return snapshot_download(
        repo_id=model_id,
        revision=tokenizer_revision,
        allow_patterns=_TOKENIZER_SNAPSHOT_ALLOW_PATTERNS,
    )


def _compiled_grammar_tokenizer_id(generator, fallback_model_id: str) -> str:
    tokenizer_grammar_id = getattr(generator, "tokenizer_grammar_id", None)
    return tokenizer_grammar_id or fallback_model_id
