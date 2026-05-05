from cluster1.results.dataclass import (
    CompileErrorType,
    GenerationResult,
    compute_unique_solution_hash,
    validate_result_invariants,
)
from cluster1.results.logger import append_result_jsonl

__all__ = [
    "CompileErrorType",
    "GenerationResult",
    "append_result_jsonl",
    "compute_unique_solution_hash",
    "validate_result_invariants",
]
