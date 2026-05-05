"""
Shared model and tokenizer loading.

All clusters use the same loading path so that model swaps (e.g., development
7B → thesis 32B) happen in one place and propagate everywhere.

Development model:  Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
Thesis model:       Qwen/Qwen2.5-Coder-32B-Instruct (or Qwen3-Coder when released)
"""
from __future__ import annotations

from typing import Any


def load_model_and_tokenizer(
    model_id: str,
    device_map: str = "auto",
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
) -> tuple[Any, Any]:
    """Load a HuggingFace causal LM and its tokenizer.

    Args:
        model_id: HuggingFace model identifier.
        device_map: passed to AutoModelForCausalLM.from_pretrained.
        load_in_4bit: enable bitsandbytes 4-bit quantization.
        load_in_8bit: enable bitsandbytes 8-bit quantization.

    Returns:
        (model, tokenizer) tuple ready for generation.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(model_id)

    quant_config = None
    if load_in_4bit or load_in_8bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
        )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map=device_map,
        quantization_config=quant_config,
    )
    model.eval()
    return model, tokenizer
