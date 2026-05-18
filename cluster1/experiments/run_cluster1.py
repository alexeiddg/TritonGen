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
from cluster1.generation.constrained_gen import DEFAULT_MAX_NEW_TOKENS, generate_source
from cluster1.generation.grammar_loader import load_compiled_grammar
from cluster1.generation.grammar_variants import grammar_path_for_variant
from cluster1.generation.provenance import (
    grammar_provenance,
    modal_image_provenance,
    model_tokenizer_revisions,
    runtime_versions,
)
from cluster1.grammar.triton_kernel_validator import validate_source_layers
from cluster1.results.dataclass import (
    DEFAULT_GRAMMAR_VARIANT,
    GENERATION_METADATA_SCHEMA_VERSION,
    GenerationResult,
    compute_unique_solution_hash,
    grammar_variant_for_cell,
    validate_paper_scale_metadata,
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
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument(
        "--scale-tier",
        choices=("smoke", "development", "paper"),
        default="smoke",
        help="Use 'paper' to enforce current generation metadata before writing.",
    )
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
    grammar_path = getattr(args, "grammar_path", DEFAULT_GRAMMAR_PATH)
    if grammar_active:
        assert grammar_variant is not None
        _ensure_grammar_path_matches_variant(grammar_path, grammar_variant)
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
    runtime_metadata = runtime_versions()
    revision_metadata = model_tokenizer_revisions(model, tokenizer)
    image_metadata = modal_image_provenance(extra={"runtime": "local"})
    grammar_metadata = {
        "grammar_sha": None,
        "grammar_path": None,
    }
    validation_fields = {
        "gbnf_parse_valid": None,
        "semantic_valid": None,
        "grammar_valid": None,
        "rejection_layer": None,
    }
    if grammar_active:
        grammar_metadata = grammar_provenance(
            grammar_path,
            grammar_variant=grammar_variant,
        )
        validation = validate_source_layers(decoded.source, grammar_path=grammar_path)
        validation_fields = validation.to_row_fields()

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
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha=grammar_metadata["grammar_sha"],
        grammar_path=grammar_metadata["grammar_path"],
        gbnf_parse_valid=validation_fields["gbnf_parse_valid"],
        semantic_valid=validation_fields["semantic_valid"],
        grammar_valid=validation_fields["grammar_valid"],
        rejection_layer=validation_fields["rejection_layer"],
        stop_reason=getattr(decoded, "stop_reason", "unknown"),
        xgrammar_version=runtime_metadata["xgrammar_version"],
        transformers_version=runtime_metadata["transformers_version"],
        tokenizers_version=runtime_metadata["tokenizers_version"],
        model_revision=revision_metadata["model_revision"],
        tokenizer_revision=revision_metadata["tokenizer_revision"],
        modal_image_sha=image_metadata["modal_image_sha"],
        modal_image_provenance_sha256=image_metadata[
            "modal_image_provenance_sha256"
        ],
        modal_image_provenance_components=image_metadata[
            "modal_image_provenance_components"
        ],
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
        if args.scale_tier == "paper":
            validate_paper_scale_metadata(result)
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
    if not _needs_grammar(args.condition):
        return
    _ensure_grammar_path_matches_variant(args.grammar_path, args.grammar_variant)


def _ensure_grammar_path_matches_variant(
    grammar_path: str | Path,
    grammar_variant: str,
) -> None:
    expected_path = Path(grammar_path_for_variant(grammar_variant))
    observed_path = Path(grammar_path)
    if _normalized_grammar_path(observed_path) != _normalized_grammar_path(
        expected_path,
    ):
        raise ValueError(
            "grammar_path must match grammar_variant mapping: "
            f"{grammar_variant!r} -> {expected_path.as_posix()!r}; "
            f"got {observed_path.as_posix()!r}"
        )


def _normalized_grammar_path(path: Path) -> Path:
    if not path.is_absolute():
        return Path(path.as_posix())
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return path.resolve()


if __name__ == "__main__":
    raise SystemExit(main())
