from cluster1.results.dataclass import (
    CompileErrorType,
    GenerationResult,
    canonical_failure_code_for_compile_error_type,
    compute_unique_solution_hash,
    validate_result_invariants,
)
from cluster1.results.logger import append_result_jsonl

__all__ = [
    "CompileErrorType",
    "GenerationResult",
    "append_result_jsonl",
    "canonical_failure_code_for_compile_error_type",
    "compute_unique_solution_hash",
    "validate_result_invariants",
]
