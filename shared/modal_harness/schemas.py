"""Request/result schemas for the TritonGen Modal harness.

Cluster boundary: Cluster 1 must never feed compile errors back to generation.
The schemas reflect that — compile errors are *result fields*, not control
signals. Reserved factor cells (``"C"``, ``"P"``, etc.) are accepted by the
type alias but rejected by the request validator until Cluster 2/3 land.

No timing, profiling, numerical-correctness, or repair fields appear here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from cluster1.results.dataclass import (
    DEFAULT_GRAMMAR_VARIANT,
    GrammarVariant,
    grammar_variant_for_cell,
    validate_grammar_variant_invariants,
)
from shared.factors.cells import FactorCell
from shared.factors.registry import (
    allowed_cells_for_cluster,
    require_cell_allowed_for_cluster,
)

KernelClass = Literal["elementwise", "reduction", "matmul"]
DTypeName = Literal["fp32", "fp16", "bf16"]

# Cluster 1 immediate scope — anything outside this set is rejected at request
# validation time so Cluster 2/3 control mechanisms cannot accidentally run.
_SUPPORTED_FACTOR_CELLS = frozenset(allowed_cells_for_cluster("cluster1"))


class RemoteGenerationRequest(BaseModel):
    """Request for one remote model generation."""

    factor_cell: FactorCell
    kernel_class: KernelClass
    kernel_name: str
    dtype: DTypeName
    prompt: str
    model_id: str
    grammar_active: bool
    grammar_variant: GrammarVariant | None = None
    grammar_path: str = "cluster1/grammar/triton_kernel.gbnf"
    max_new_tokens: int = 1024
    temperature: float = 0.2
    generation_seed: int | None = None
    run_id: str

    @field_validator("factor_cell")
    @classmethod
    def _reject_reserved_modes(cls, v: str) -> str:
        return _validate_supported_factor_cell(v)

    @model_validator(mode="after")
    def _validate_factor_matches_grammar(self):
        self.grammar_variant = grammar_variant_for_cell(
            factor_cell=self.factor_cell,
            grammar_active=self.grammar_active,
            grammar_variant=self.grammar_variant,
        )
        return self


class RemoteGenerationResult(BaseModel):
    """Result for one remote model generation. No compile or timing fields."""

    source: str
    model_id: str
    grammar_active: bool
    grammar_variant: GrammarVariant | None = None
    masked_token_rate: float | None
    generation_seed: int | None
    temperature: float
    run_id: str
    modal_function_call_id: str | None = None
    modal_input_id: str | None = None
    error_type: str | None = None
    error_msg: str | None = None

    @model_validator(mode="after")
    def _validate_masked_rate(self):
        if self.grammar_active and self.grammar_variant is None:
            self.grammar_variant = DEFAULT_GRAMMAR_VARIANT
        validate_grammar_variant_invariants(
            grammar_active=self.grammar_active,
            grammar_variant=self.grammar_variant,
        )
        if not self.grammar_active and self.masked_token_rate is not None:
            raise ValueError("masked_token_rate must be None when grammar_active=False")
        if self.grammar_active and self.masked_token_rate is None:
            raise ValueError("masked_token_rate is required when grammar_active=True")
        return self


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
        return _validate_supported_factor_cell(v)


class RemoteCompileResult(BaseModel):
    """Result of compile-only validation. No timing or profiling fields.

    ``factor_cell`` is populated by the harness from the originating
    ``RemoteCompileRequest`` so each result row remains traceable to the
    Cluster 1 condition that produced it. It is optional so direct test
    fixtures and round-trip helpers can still build a result without a
    request, and so older sidecar logs without the field stay parseable.
    """

    compile_success: bool
    compile_results_by_dtype: dict[str, bool]
    compile_error_type: str | None = None
    compile_error_msg: str | None = None
    n_shapes_tested: int
    stdout: str = ""
    stderr: str = ""
    traceback: str | None = None
    run_id: str
    factor_cell: FactorCell | None = None
    modal_function_call_id: str | None = None
    modal_input_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class RemoteEvalResult(BaseModel):
    """Remote generation plus compile result bridge for local JSONL logging."""

    generation: RemoteGenerationResult
    compile: RemoteCompileResult


def remote_compile_result_to_cluster1_fields(
    result: RemoteCompileResult | dict,
) -> dict[str, object]:
    """Return compile fields matching ``cluster1.results.GenerationResult``."""
    if not isinstance(result, RemoteCompileResult):
        result = RemoteCompileResult(**result)

    error_msg = result.compile_error_msg
    return {
        "compile_success": result.compile_success,
        "compile_results_by_dtype": dict(result.compile_results_by_dtype),
        "compile_error_type": result.compile_error_type,
        "compile_error_msg": error_msg[:500] if error_msg is not None else None,
        "n_shapes_tested": result.n_shapes_tested,
    }


def dtype_name_to_bytes(dtype: DTypeName | str) -> int:
    """Return scalar byte width for supported Cluster 1 dtype names."""
    dtype_bytes = {
        "fp32": 4,
        "fp16": 2,
        "bf16": 2,
    }.get(dtype)
    if dtype_bytes is None:
        raise ValueError(f"unsupported dtype for hardware masks: {dtype!r}")
    return dtype_bytes


def _validate_supported_factor_cell(v: str) -> str:
    try:
        return require_cell_allowed_for_cluster("cluster1", v)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported factor_cell {v!r} — only 'none' and 'G' are "
            f"implemented. Cluster 2/3 modes are reserved."
        ) from exc
