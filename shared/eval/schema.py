"""Shared evaluation result schema.

The schema is intentionally broader than Cluster 1. Cluster 1 adapters must
leave Level 2-4 fields as ``None`` and must not execute future-level logic.
``from_dict`` rejects unknown fields so schema drift is explicit.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from shared.eval.constants import TIMING_ITERS, WARMUP_ITERS


@dataclass(frozen=True)
class RepairTrace:
    """One generate-validate-feedback iteration in a future repair trace."""

    iteration: int
    source: str
    level_reached: int
    feedback_type: str
    feedback_content: str
    tokens_generated: int
    converged: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RepairTrace":
        return _from_dict_strict(cls, payload)


@dataclass(frozen=True)
class EvalResult:
    """JSON-safe shared evaluation record for one generated kernel.

    Fields for levels above the evaluated level remain ``None``. This is
    distinct from ``False`` or ``0``, which mean an evaluated negative result
    or a measured value.
    """

    kernel_id: int | None
    kernel_name: str
    kernel_class: str
    kernelbench_level: int | None
    condition: str
    sample_index: int | None
    model_id: str
    run_id: str
    timestamp: str
    dtype_tested: str
    source: str
    source_hash: str
    ast_hash: str | None
    level_reached: int
    parse_success: bool | None
    parse_error: str | None
    has_triton_decorator: bool | None
    signature_valid: bool | None
    compile_success: bool | None
    compile_error: str | None
    failure_code: str | None

    grammar_active: bool | None = None
    grammar_variant: str | None = None
    grammar_sha: str | None = None
    grammar_path: str | None = None
    gbnf_parse_valid: bool | None = None
    semantic_valid: bool | None = None
    grammar_valid: bool | None = None
    rejection_layer: str | None = None
    stop_reason: str | None = None
    xgrammar_version: str | None = None
    transformers_version: str | None = None
    tokenizers_version: str | None = None
    model_revision: str | None = None
    tokenizer_revision: str | None = None
    modal_image_sha: str | None = None
    modal_image_provenance_sha256: str | None = None
    modal_image_provenance_components: dict[str, Any] | None = None

    gpu_model: str = ""
    gpu_clock_mhz: int | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    generation_time_s: float = 0.0
    compile_time_s: float | None = None
    functional_success: bool | None = None
    correctness_error: str | None = None
    max_abs_diff: float | None = None
    max_rel_diff: float | None = None
    num_test_shapes: int | None = None
    shapes_passed: int | None = None
    dtype_results: dict[str, Any] | None = None
    safe_success: bool | None = None
    sanitizer_errors: list[str] | None = None
    sanitizer_tool: str | None = None
    kernel_time_ms: float | None = None
    kernel_time_iqr_ms: float | None = None
    eager_time_ms: float | None = None
    compile_time_ms: float | None = None
    speedup_vs_eager: float | None = None
    speedup_vs_compile: float | None = None
    warmup_iters: int = WARMUP_ITERS
    timing_iters: int = TIMING_ITERS
    repair_iteration: int | None = None
    repair_budget: int | None = None
    repair_converged: bool | None = None
    repair_traces: list[RepairTrace] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Return a stable JSON string representation."""

        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvalResult":
        """Build ``EvalResult`` from a dictionary.

        Unknown fields are rejected intentionally. Missing nullable future
        fields use dataclass defaults; missing required identity/Level 0/1
        fields raise ``ValueError``.
        """

        if not isinstance(payload, dict):
            raise TypeError("EvalResult.from_dict requires a dict")

        _reject_unknown_fields(cls, payload)
        converted = dict(payload)
        traces = converted.get("repair_traces")
        if traces is not None:
            if not isinstance(traces, list):
                raise ValueError("invalid EvalResult payload: repair_traces must be a list")
            converted["repair_traces"] = [
                trace if isinstance(trace, RepairTrace) else RepairTrace.from_dict(trace)
                for trace in traces
            ]

        try:
            return cls(**converted)
        except TypeError as exc:
            raise ValueError(f"invalid EvalResult payload: {exc}") from exc


@dataclass(frozen=True)
class CellSummary:
    """Aggregated metrics for one ``(kernel_id, condition)`` cell."""

    kernel_id: int
    kernel_class: str
    condition: str
    n_samples: int
    compile_at_1: float
    pass_at_1: float
    pass_at_5: float
    pass_at_10: float
    safe_at_1: float
    median_speedup_vs_compile: float | None
    median_speedup_vs_eager: float | None
    fast_at_0: float
    fast_at_1_0: float
    fast_at_1_2: float
    fast_tc_at_1_0: float | None
    fast_tc_at_1_2: float | None
    mean_repair_iters_converged: float | None
    convergence_rate: float | None
    repair_efficiency: float | None
    failure_distribution: dict[str, int]
    unique_ratio_source: float
    unique_ratio_ast: float
    mean_tokens_total: float
    cost_adjusted_pass1: float | None
    pass1_ci_lower: float
    pass1_ci_upper: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CellSummary":
        return _from_dict_strict(cls, payload)


def append_result(path: str | Path, result: EvalResult) -> None:
    """Append one ``EvalResult`` JSON object as one JSONL line."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(result.to_json())
        f.write("\n")
    # Seam B: mirror the record into the active MLflow run as stepped eval.*
    # metrics. Imported locally to keep schema.py decoupled from tracking. The
    # tracking client is the single safety boundary — it no-ops when disabled
    # and never raises — so no extra guarding is needed here.
    from shared import tracking

    tracking.log_eval_result(result)


LEVEL_2_TO_4_FIELDS: tuple[str, ...] = (
    "functional_success",
    "correctness_error",
    "max_abs_diff",
    "max_rel_diff",
    "num_test_shapes",
    "shapes_passed",
    "dtype_results",
    "safe_success",
    "sanitizer_errors",
    "sanitizer_tool",
    "kernel_time_ms",
    "kernel_time_iqr_ms",
    "eager_time_ms",
    "compile_time_ms",
    "speedup_vs_eager",
    "speedup_vs_compile",
    "repair_iteration",
    "repair_budget",
    "repair_converged",
    "repair_traces",
)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _from_dict_strict(cls: type[Any], payload: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        raise TypeError(f"{cls.__name__}.from_dict requires a dict")
    _reject_unknown_fields(cls, payload)
    try:
        return cls(**payload)
    except TypeError as exc:
        raise ValueError(f"invalid {cls.__name__} payload: {exc}") from exc


def _reject_unknown_fields(cls: type[Any], payload: dict[str, Any]) -> None:
    field_names = {field.name for field in fields(cls)}
    unknown = sorted(set(payload) - field_names)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {', '.join(unknown)}")
