"""Final structured result schema for Cluster 1 generation experiments."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Literal


# Task 5.1
CompileErrorType = Literal["CompilationError", "RuntimeError", "SignatureError", None]


# Task 5.2
@dataclass(frozen=True)
class GenerationResult:
    source: str
    model_id: str
    grammar_active: bool
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
    if not result.grammar_active and result.masked_token_rate is not None:
        raise ValueError("masked_token_rate must be None when grammar_active is False")
    if result.grammar_active and result.masked_token_rate is None:
        raise ValueError("masked_token_rate must not be None when grammar_active is True")


# Task 5.3
def compute_unique_solution_hash(source: str) -> str:
    try:
        tree = ast.parse(source)
        normalized = ast.unparse(tree)
    except SyntaxError:
        normalized = " ".join(source.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
