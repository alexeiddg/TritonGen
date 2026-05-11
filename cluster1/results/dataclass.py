"""Final structured result schema for Cluster 1 generation experiments."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any, Literal, cast


# Task 5.1
CompileErrorType = Literal["CompilationError", "RuntimeError", "SignatureError", None]
GrammarVariant = Literal["template_upper_bound", "task_agnostic"]
DEFAULT_GRAMMAR_VARIANT: GrammarVariant = "template_upper_bound"
VALID_GRAMMAR_VARIANTS: tuple[GrammarVariant, ...] = (
    "template_upper_bound",
    "task_agnostic",
)
_VALID_GRAMMAR_VARIANT_SET = frozenset(VALID_GRAMMAR_VARIANTS)


# Task 5.2
@dataclass(frozen=True)
class GenerationResult:
    source: str
    model_id: str
    grammar_active: bool
    grammar_variant: GrammarVariant | None
    kernel_class: Literal["elementwise", "reduction", "matmul"]
    kernel_name: str
    dtype: Literal["fp32", "fp16", "bf16"]
    compile_success: bool
    compile_results_by_dtype: dict[str, bool]
    compile_error_type: CompileErrorType
    compile_error_msg: str | None
    masked_token_rate: float | None
    unique_solution_hash: str
    n_shapes_tested: int
    generation_seed: int | None
    temperature: float
    run_id: str
    timestamp_utc: str


def validate_result_invariants(result: GenerationResult) -> None:
    validate_grammar_variant_invariants(
        grammar_active=result.grammar_active,
        grammar_variant=result.grammar_variant,
    )
    if not result.grammar_active and result.masked_token_rate is not None:
        raise ValueError("masked_token_rate must be None when grammar_active is False")
    if result.grammar_active and result.masked_token_rate is None:
        raise ValueError("masked_token_rate must not be None when grammar_active is True")


def validate_grammar_variant_invariants(
    *,
    grammar_active: bool,
    grammar_variant: str | None,
    factor_cell: str | None = None,
) -> None:
    if factor_cell == "none" and grammar_active:
        raise ValueError("factor_cell='none' requires grammar_active=False")
    if factor_cell == "none" and grammar_variant is not None:
        raise ValueError("factor_cell='none' requires grammar_variant=None")
    if factor_cell == "G" and not grammar_active:
        raise ValueError("factor_cell='G' requires grammar_active=True")

    if not grammar_active:
        if grammar_variant is not None:
            raise ValueError("grammar_variant must be None when grammar_active is False")
        return

    if grammar_variant not in _VALID_GRAMMAR_VARIANT_SET:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(
            "grammar_variant must be one of "
            f"{allowed} when grammar_active is True; got {grammar_variant!r}"
        )


def default_grammar_variant_for_active_grammar(
    grammar_variant: str | None = None,
) -> GrammarVariant:
    """Return the active-grammar variant, preserving the current G default."""

    if grammar_variant is None:
        return DEFAULT_GRAMMAR_VARIANT
    if grammar_variant not in _VALID_GRAMMAR_VARIANT_SET:
        allowed = ", ".join(VALID_GRAMMAR_VARIANTS)
        raise ValueError(f"invalid grammar_variant {grammar_variant!r}; expected {allowed}")
    return cast(GrammarVariant, grammar_variant)


def grammar_variant_for_cell(
    *,
    factor_cell: str,
    grammar_active: bool,
    grammar_variant: str | None = None,
) -> GrammarVariant | None:
    resolved = (
        default_grammar_variant_for_active_grammar(grammar_variant)
        if grammar_active
        else grammar_variant
    )
    validate_grammar_variant_invariants(
        factor_cell=factor_cell,
        grammar_active=grammar_active,
        grammar_variant=resolved,
    )
    return resolved


def generation_result_record_for_deserialization(
    record: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy with legacy missing ``grammar_variant`` filled in memory."""

    if "grammar_variant" in record:
        return dict(record)

    updated = dict(record)
    updated["grammar_variant"] = (
        DEFAULT_GRAMMAR_VARIANT if updated.get("grammar_active") is True else None
    )
    return updated


# Task 5.3
def compute_unique_solution_hash(source: str) -> str:
    try:
        tree = ast.parse(source)
        normalized = ast.unparse(tree)
    except SyntaxError:
        normalized = " ".join(source.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
