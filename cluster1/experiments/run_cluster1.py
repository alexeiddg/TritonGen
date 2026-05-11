"""Cluster 1 experiment runner.

The default model is the development iteration model used for local/T4
validation, not the final thesis reporting model.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cluster1.data.kernels import KERNEL_SPECS, get_kernel_spec
from cluster1.data.kernels.spec import KernelSpec
from cluster1.data.prompts.prompt_contract import build_prompt
from cluster1.constraints.hardware_checker import HardwareChecker
from cluster1.generation.constrained_gen import generate_source
from cluster1.generation.grammar_loader import load_compiled_grammar
from cluster1.results.dataclass import (
    DEFAULT_GRAMMAR_VARIANT,
    GenerationResult,
    compute_unique_solution_hash,
    grammar_variant_for_cell,
    validate_result_invariants,
)
from cluster1.results.logger import append_result_jsonl
from cluster1.validation.compile_check import CompileResult, check_compiles_all_dtypes


DEFAULT_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
DEFAULT_DATASET_ID = "ScalingIntelligence/KernelBench"
DEFAULT_GRAMMAR_PATH = Path("cluster1/grammar/triton_kernel.gbnf")
SUPPORTED_GRAMMAR_VARIANTS = ("template_upper_bound", "task_agnostic")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Phase 7 runner CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run Cluster 1 baseline and grammar-constrained generation cells. "
            f"The default model ({DEFAULT_MODEL_ID}) is for development iteration, "
            "not final thesis reporting."
        )
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--condition", choices=("baseline", "G", "both"), required=True)
    parser.add_argument(
        "--kernel-class",
        choices=("elementwise", "reduction", "matmul", "all"),
        required=True,
    )
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--grammar-path", type=Path, default=DEFAULT_GRAMMAR_PATH)
    parser.add_argument(
        "--grammar-variant",
        choices=SUPPORTED_GRAMMAR_VARIANTS,
        default=DEFAULT_GRAMMAR_VARIANT,
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    return parser.parse_args(argv)


def load_model_and_tokenizer(model_id: str) -> tuple[Any, Any]:
    """Load a HuggingFace causal LM and tokenizer once for all conditions."""

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    if hasattr(model, "eval"):
        model.eval()
    return model, tokenizer


def iter_experiment_cells(
    kernel_classes: list[str],
    condition: str,
    n: int,
    dtypes: list[str] = ["fp32", "fp16", "bf16"],
) -> Iterator[tuple[KernelSpec, bool, str, int]]:
    """Yield deterministic Phase 7 experiment cells."""

    selected_classes = list(KERNEL_SPECS) if kernel_classes == ["all"] else kernel_classes
    grammar_conditions = _grammar_conditions(condition)
    for kernel_class in selected_classes:
        spec = get_kernel_spec(kernel_class)
        for grammar_active in grammar_conditions:
            for dtype in dtypes:
                for seed in range(n):
                    yield spec, grammar_active, dtype, seed


def _grammar_conditions(condition: str) -> list[bool]:
    if condition == "baseline":
        return [False]
    if condition == "G":
        return [True]
    if condition == "both":
        return [False, True]
    raise ValueError(f"unknown condition: {condition!r}")


def run_one_generation(
    spec: KernelSpec,
    dtype: str,
    seed: int,
    grammar_active: bool,
    model,
    tokenizer,
    compiled_grammar,
    args: argparse.Namespace,
) -> GenerationResult:
    """Run one generation cell and return a validated result record."""

    prompt = build_prompt(spec, dtype)
    hardware_checker = HardwareChecker() if grammar_active else None
    grammar_variant = grammar_variant_for_cell(
        factor_cell="G" if grammar_active else "none",
        grammar_active=grammar_active,
        grammar_variant=args.grammar_variant if grammar_active else None,
    )
    decoded = generate_source(
        prompt=prompt,
        model=model,
        tokenizer=tokenizer,
        grammar_active=grammar_active,
        compiled_grammar=compiled_grammar,
        hardware_checker=hardware_checker,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        seed=seed,
    )

    compile_results = check_compiles_all_dtypes(
        decoded.source,
        spec.compile_spec,
        spec.shapes_by_dtype,
    )
    dtype_result = _compile_result_for_dtype(compile_results, dtype)
    first_error = next((result for result in compile_results if result.error_type is not None), None)
    result = GenerationResult(
        source=decoded.source,
        model_id=args.model_id,
        grammar_active=grammar_active,
        grammar_variant=grammar_variant,
        kernel_class=spec.kernel_class,
        kernel_name=spec.name,
        dtype=dtype,
        compile_success=all(result.success for result in compile_results),
        compile_results_by_dtype={result.dtype: result.success for result in compile_results},
        compile_error_type=first_error.error_type if first_error is not None else None,
        compile_error_msg=(
            first_error.error_msg[:500]
            if first_error is not None and first_error.error_msg is not None
            else None
        ),
        masked_token_rate=decoded.masked_token_rate if grammar_active else None,
        unique_solution_hash=compute_unique_solution_hash(decoded.source),
        n_shapes_tested=dtype_result.n_shapes_tested,
        generation_seed=seed,
        temperature=args.temperature,
        run_id=str(uuid4()),
        timestamp_utc=datetime.now(UTC).isoformat(),
    )
    validate_result_invariants(result)
    return result


def _compile_result_for_dtype(
    compile_results: list[CompileResult],
    dtype: str,
) -> CompileResult:
    for result in compile_results:
        if result.dtype == dtype:
            return result
    raise ValueError(f"compile results missing dtype {dtype!r}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _validate_grammar_variant_run_path(args)
    kernel_classes = _selected_kernel_classes(args.kernel_class)
    _validate_dataset_id(kernel_classes, args.dataset_id)

    model, tokenizer = load_model_and_tokenizer(args.model_id)
    compiled_grammar = (
        load_compiled_grammar(str(args.grammar_path), args.model_id)
        if _needs_grammar(args.condition)
        else None
    )

    for spec, grammar_active, dtype, seed in iter_experiment_cells(
        kernel_classes,
        args.condition,
        args.n,
    ):
        result = run_one_generation(
            spec=spec,
            dtype=dtype,
            seed=seed,
            grammar_active=grammar_active,
            model=model,
            tokenizer=tokenizer,
            compiled_grammar=compiled_grammar,
            args=args,
        )
        append_result_jsonl(args.output, result)
    return 0


def _selected_kernel_classes(kernel_class: str) -> list[str]:
    if kernel_class == "all":
        return list(KERNEL_SPECS)
    return [kernel_class]


def _validate_dataset_id(kernel_classes: list[str], dataset_id: str) -> None:
    for kernel_class in kernel_classes:
        spec = get_kernel_spec(kernel_class)
        if spec.dataset_id != dataset_id:
            raise ValueError(
                f"{kernel_class} spec uses dataset_id={spec.dataset_id!r}, "
                f"but CLI requested {dataset_id!r}"
            )


def _needs_grammar(condition: str) -> bool:
    return condition in {"G", "both"}


def _validate_grammar_variant_run_path(args: argparse.Namespace) -> None:
    if (
        args.condition in {"G", "both"}
        and args.grammar_variant == "task_agnostic"
        and Path(args.grammar_path) == DEFAULT_GRAMMAR_PATH
    ):
        raise ValueError(
            "grammar_variant='task_agnostic' requires an explicit task-agnostic "
            "grammar path; the task-agnostic grammar is not implemented yet."
        )


if __name__ == "__main__":
    raise SystemExit(main())
