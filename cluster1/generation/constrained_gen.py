"""Controlled grammar-on/off generation entry point for Cluster 1."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from cluster1.constants import DEFAULT_MAX_NEW_TOKENS
from cluster1.constraints.hardware_checker import HardwareChecker
from cluster1.generation.constrained_decoding import TritonGrammarLogitsProcessor
from cluster1.generation.grammar_loader import load_compiled_grammar
from cluster1.generation.provenance import UNKNOWN, classify_stop_reason


@dataclass(frozen=True)
class DecodedKernel:
    source: str
    masked_token_rate: float | None
    generation_seed: int | None
    temperature: float
    stop_reason: str = UNKNOWN
    generated_token_count: int | None = None
    grammar_final_state_observed: bool | None = None


def generate_source(
    prompt: str,
    model,
    tokenizer,
    grammar_active: bool,
    compiled_grammar=None,
    hardware_checker: HardwareChecker | None = None,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    temperature: float = 0.2,
    seed: int | None = None,
) -> DecodedKernel:
    if seed is not None:
        _manual_seed(seed)

    encoded = _move_encoded_to_model_device(
        tokenizer(prompt, return_tensors="pt"),
        model,
    )
    input_ids = encoded["input_ids"]
    prompt_len = _sequence_length(input_ids)

    generate_kwargs = {
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "do_sample": True,
    }
    generate_kwargs.update(encoded)

    processor = None
    if grammar_active:
        if compiled_grammar is None:
            raise ValueError("compiled_grammar is required when grammar_active=True")
        if hardware_checker is not None:
            hardware_checker.reset()
        processor = TritonGrammarLogitsProcessor(
            compiled_grammar,
            tokenizer,
            hardware_checker,
            prompt_length=prompt_len,
        )
        generate_kwargs["logits_processor"] = [processor]

    output_ids = model.generate(**generate_kwargs)
    generated_token_ids = _new_token_ids(output_ids, prompt_len)
    grammar_final_state_observed = None
    if processor is not None:
        try:
            processor.observe_generated_tokens(output_ids)
            grammar_final_state_observed = processor.grammar_final_state_observed()
        except Exception:
            grammar_final_state_observed = None
    source = _decode_new_tokens(tokenizer, output_ids, prompt_len)
    masked_rate = processor.masked_token_rate() if processor is not None else None
    eos_token_id = _eos_token_id(tokenizer)
    return DecodedKernel(
        source=source,
        masked_token_rate=masked_rate,
        generation_seed=seed,
        temperature=temperature,
        stop_reason=classify_stop_reason(
            generated_token_ids=generated_token_ids,
            max_new_tokens=max_new_tokens,
            eos_token_id=eos_token_id,
            grammar_final_state_observed=grammar_final_state_observed,
        ),
        generated_token_count=len(generated_token_ids),
        grammar_final_state_observed=grammar_final_state_observed,
    )


def _move_encoded_to_model_device(encoded, model):
    device = _model_device(model)
    if device is None:
        return encoded
    return {
        key: value.to(device) if hasattr(value, "to") else value
        for key, value in encoded.items()
    }


def _model_device(model):
    device = getattr(model, "device", None)
    if device is not None:
        return device
    parameters = getattr(model, "parameters", None)
    if callable(parameters):
        try:
            first_param = next(parameters())
        except StopIteration:
            return None
        except TypeError:
            return None
        return getattr(first_param, "device", None)
    return None


def _manual_seed(seed: int) -> None:
    try:
        import torch

        torch.manual_seed(seed)
    except Exception:
        return


def _sequence_length(input_ids) -> int:
    shape = getattr(input_ids, "shape", None)
    if shape is not None:
        return int(shape[-1])
    first = input_ids[0] if input_ids and isinstance(input_ids[0], list) else input_ids
    return len(first)


def _decode_new_tokens(tokenizer, output_ids, prompt_len: int) -> str:
    if isinstance(output_ids, str):
        return output_ids

    new_tokens = _new_token_ids(output_ids, prompt_len)
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def _new_token_ids(output_ids, prompt_len: int) -> list[int]:
    if isinstance(output_ids, str):
        return []
    sequence = output_ids[0] if _is_batched(output_ids) else output_ids
    try:
        new_tokens = sequence[prompt_len:]
    except TypeError:
        new_tokens = sequence[:, prompt_len:]
    if hasattr(new_tokens, "tolist"):
        new_tokens = new_tokens.tolist()
    return [int(token_id) for token_id in new_tokens]


def _eos_token_id(tokenizer) -> int | None:
    value = getattr(tokenizer, "eos_token_id", None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_batched(output_ids) -> bool:
    shape = getattr(output_ids, "shape", None)
    if shape is not None:
        return len(shape) == 2
    return bool(output_ids and isinstance(output_ids[0], list))


def _parse_bool(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool: {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--grammar-active", type=_parse_bool, default=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.2)
    args = parser.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    model = AutoModelForCausalLM.from_pretrained(args.model_id)
    compiled_grammar = None
    hardware_checker = None
    if args.grammar_active:
        grammar_path = Path(__file__).parents[1] / "grammar" / "triton_kernel.gbnf"
        compiled_grammar = load_compiled_grammar(str(grammar_path), args.model_id)
        hardware_checker = HardwareChecker()

    decoded = generate_source(
        prompt=args.prompt,
        model=model,
        tokenizer=tokenizer,
        grammar_active=args.grammar_active,
        compiled_grammar=compiled_grammar,
        hardware_checker=hardware_checker,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        seed=args.seed,
    )
    print(decoded.source)
    print(f"masked_token_rate={decoded.masked_token_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
