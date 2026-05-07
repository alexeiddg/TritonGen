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


@app.cls(
    image=llm_generation_image,
    gpu="L40S",
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

    model_id: str = modal.parameter()

    @modal.enter()
    def load_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            trust_remote_code=True,
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
        )
        if hasattr(self.model, "eval"):
            self.model.eval()

        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        pad_token_id = getattr(self.tokenizer, "pad_token_id", None)
        if pad_token_id is not None:
            self.model.generation_config.pad_token_id = pad_token_id

        self.device = getattr(self.model, "device", None)

    @modal.method()
    def generate_one(self, req_dict: dict) -> dict:
        from cluster1.constraints.hardware_checker import HardwareChecker
        from cluster1.generation.constrained_gen import generate_source
        from cluster1.generation.grammar_loader import load_compiled_grammar

        req = RemoteGenerationRequest(**req_dict)
        if req.model_id != self.model_id:
            raise ValueError(
                f"request model_id {req.model_id!r} does not match loaded model "
                f"{self.model_id!r}"
            )

        compiled_grammar = None
        hardware_checker = None
        if req.grammar_active:
            compiled_grammar = load_compiled_grammar(
                _resolve_grammar_path(req.grammar_path),
                req.model_id,
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

        result = RemoteGenerationResult(
            source=decoded.source,
            model_id=req.model_id,
            grammar_active=req.grammar_active,
            masked_token_rate=decoded.masked_token_rate if req.grammar_active else None,
            generation_seed=decoded.generation_seed,
            temperature=decoded.temperature,
            run_id=req.run_id,
            modal_function_call_id=call_id,
            modal_input_id=input_id,
        )
        return result.model_dump()


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
