"""Request/result schemas for the TritonGen Modal harness.

Phase 1–3 scope: only the compile-side schemas are implemented. Generation
schemas (``RemoteGenerationRequest`` / ``RemoteGenerationResult``) are
deferred to Phase 4.

Cluster boundary: Cluster 1 must never feed compile errors back to generation.
The schemas reflect that — compile errors are *result fields*, not control
signals. Reserved factor cells (``"C"``, ``"P"``, etc.) are accepted by the
type alias but rejected by the request validator until Cluster 2/3 land.

No timing, profiling, numerical-correctness, or repair fields appear here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# The full factorial label space. Reserved cells are NOT executed yet — see
# the validator on RemoteCompileRequest.factor_cell.
FactorCell = Literal[
    "none",
    "G",
    "C",
    "P",
    "G+C",
    "G+P",
    "C+P",
    "G+C+P",
]
KernelClass = Literal["elementwise", "reduction", "matmul"]
DTypeName = Literal["fp32", "fp16", "bf16"]

# Cluster 1 immediate scope — anything outside this set is rejected at request
# validation time so Cluster 2/3 control mechanisms cannot accidentally run.
_SUPPORTED_FACTOR_CELLS: frozenset[str] = frozenset({"none", "G"})


class RemoteCompileRequest(BaseModel):
    """Request for compile-only validation of generated Triton source.

    The remote function looks up the canonical ``KernelSpec`` by
    ``kernel_class`` rather than serializing ``CompileSpec`` /
    ``inspect.Signature`` / ``build_args`` over the wire.
    """

    factor_cell: FactorCell
    kernel_class: KernelClass
    kernel_name: str
    source: str
    run_id: str
    timeout_s: int = 180

    @field_validator("factor_cell")
    @classmethod
    def _reject_reserved_modes(cls, v: str) -> str:
        if v not in _SUPPORTED_FACTOR_CELLS:
            raise ValueError(
                f"Unsupported factor_cell {v!r} — only 'none' and 'G' are "
                f"implemented. Cluster 2/3 modes are reserved."
            )
        return v


class RemoteCompileResult(BaseModel):
    """Result of compile-only validation. No timing or profiling fields."""

    compile_success: bool
    compile_results_by_dtype: dict[str, bool]
    compile_error_type: str | None = None
    compile_error_msg: str | None = None
    n_shapes_tested: int
    stdout: str = ""
    stderr: str = ""
    traceback: str | None = None
    run_id: str
    modal_function_call_id: str | None = None
    modal_input_id: str | None = None
    metadata: dict = Field(default_factory=dict)
