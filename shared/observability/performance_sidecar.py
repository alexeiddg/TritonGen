"""Dedicated O6b performance sidecar schema and JSONL writer."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PERFORMANCE_SIDECAR_SCHEMA_VERSION = "tritongen.observability.performance.v1"
DEFAULT_PERFORMANCE_ARTIFACT_ROOT = Path("artifacts") / "observability_performance"

BenchmarkScope = Literal["smoke"]
TimingMethod = Literal["cuda_events"]
MeasurementStatus = Literal["complete"]

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,127}$")
_SHAPE_SIGNATURE_RE = re.compile(r"^[1-9][0-9]*(?:x[1-9][0-9]*)*$")
_FORBIDDEN_CAVEAT_TERMS = (
    "cost_per_success",
    "economic_lift",
    "paper scale result",
    "paper-scale result",
    "paper scale claim",
    "paper-scale claim",
    "pass@k",
    "roi",
)


class _StrictPerformanceModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
        strict=True,
    )


class PerformanceSidecarRow(_StrictPerformanceModel):
    """One O6b performance benchmark result row.

    This schema is intentionally separate from scientific result rows and from
    the O0-O5 operational event sidecar. It is only for an explicitly approved
    O6b performance packet.
    """

    experiment_id: str
    run_id: str
    benchmark_id: str
    benchmark_scope: BenchmarkScope
    kernel_class: str
    problem_id: str
    dtype: str
    shape_signature: str
    baseline_type: str
    candidate_type: str
    timing_method: TimingMethod
    gpu_type: str
    warmup_iters: int = Field(ge=1)
    repetitions: int = Field(ge=1)
    baseline_median_ms: float = Field(gt=0)
    candidate_median_ms: float = Field(gt=0)
    baseline_p25_ms: float = Field(gt=0)
    baseline_p75_ms: float = Field(gt=0)
    candidate_p25_ms: float = Field(gt=0)
    candidate_p75_ms: float = Field(gt=0)
    speedup_vs_baseline: float = Field(gt=0)
    correctness_prerequisite_passed: Literal[True]
    measurement_status: MeasurementStatus
    caveats: list[str] = Field(default_factory=list, max_length=8)
    scientific_row_mutation_allowed: Literal[False] = False
    paper_scale_claim_allowed: Literal[False] = False
    profiler_traces_allowed: Literal[False] = False

    @field_validator(
        "experiment_id",
        "run_id",
        "benchmark_id",
        "kernel_class",
        "problem_id",
        "dtype",
        "baseline_type",
        "candidate_type",
        "gpu_type",
    )
    @classmethod
    def _safe_label(cls, value: str) -> str:
        value = _require_non_empty(value)
        if not _SAFE_ID_RE.fullmatch(value):
            raise ValueError("performance sidecar labels must be bounded identifiers")
        return value

    @field_validator("shape_signature")
    @classmethod
    def _shape_signature(cls, value: str) -> str:
        value = _require_non_empty(value)
        if not _SHAPE_SIGNATURE_RE.fullmatch(value):
            raise ValueError("shape_signature must be positive dimensions joined by x")
        return value

    @field_validator(
        "baseline_median_ms",
        "candidate_median_ms",
        "baseline_p25_ms",
        "baseline_p75_ms",
        "candidate_p25_ms",
        "candidate_p75_ms",
        "speedup_vs_baseline",
    )
    @classmethod
    def _finite_positive(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("performance timing values must be finite and positive")
        return value

    @field_validator("caveats")
    @classmethod
    def _bounded_caveats(cls, value: list[str]) -> list[str]:
        for caveat in value:
            if not isinstance(caveat, str) or not caveat.strip():
                raise ValueError("caveats must be non-empty strings")
            if len(caveat) > 160:
                raise ValueError("caveats must be bounded strings")
            normalized = caveat.lower()
            if any(term in normalized for term in _FORBIDDEN_CAVEAT_TERMS):
                raise ValueError("caveats must not contain economic or paper claims")
        return value

    @model_validator(mode="after")
    def _performance_contract(self) -> "PerformanceSidecarRow":
        _require_quantile_order(
            "baseline",
            self.baseline_p25_ms,
            self.baseline_median_ms,
            self.baseline_p75_ms,
        )
        _require_quantile_order(
            "candidate",
            self.candidate_p25_ms,
            self.candidate_median_ms,
            self.candidate_p75_ms,
        )
        expected_speedup = self.baseline_median_ms / self.candidate_median_ms
        if not math.isclose(
            self.speedup_vs_baseline,
            expected_speedup,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("speedup_vs_baseline must equal baseline/candidate median")
        return self


def canonical_performance_row_json(row: PerformanceSidecarRow) -> str:
    """Return deterministic JSON for one performance sidecar row."""

    validated = _revalidate_performance_row(row)
    return json.dumps(
        validated.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def write_performance_sidecar_atomic(
    path: str | Path,
    row: PerformanceSidecarRow,
    *,
    repo_root: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Write a one-row O6b performance JSONL sidecar atomically."""

    target = validate_performance_sidecar_path(path, repo_root=repo_root)
    if target.exists() and not overwrite:
        raise FileExistsError(f"performance sidecar already exists: {target}")
    if target.exists() and target.is_dir():
        raise IsADirectoryError(f"performance sidecar path is a directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(canonical_performance_row_json(row) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def load_performance_sidecar_rows(path: str | Path) -> list[PerformanceSidecarRow]:
    """Load and validate a performance sidecar JSONL file."""

    rows: list[PerformanceSidecarRow] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(PerformanceSidecarRow.model_validate_json(stripped))
            except ValueError as exc:
                raise ValueError(f"invalid performance row at line {line_number}") from exc
    return rows


def validate_performance_sidecar_path(
    path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> Path:
    """Resolve and validate the O6b performance sidecar path.

    O6b writes under ``artifacts/observability_performance`` and never under
    ``outputs`` so scientific artifacts remain untouched.
    """

    raw = Path(path)
    if raw.suffix != ".jsonl":
        raise ValueError("performance sidecar path must end with .jsonl")

    root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    target = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    artifact_root = (root / DEFAULT_PERFORMANCE_ARTIFACT_ROOT).resolve()
    outputs_root = (root / "outputs").resolve()

    if target == outputs_root or outputs_root in target.parents:
        raise ValueError("performance sidecar path must not be under outputs")
    if target != artifact_root and artifact_root not in target.parents:
        raise ValueError(
            "performance sidecar path must be under artifacts/observability_performance"
        )
    if target.exists() and target.is_dir():
        raise IsADirectoryError(f"performance sidecar path is a directory: {target}")
    return target


def performance_sidecar_sha256(path: str | Path) -> str:
    """Return SHA-256 for a written performance sidecar file."""

    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _revalidate_performance_row(row: PerformanceSidecarRow) -> PerformanceSidecarRow:
    return PerformanceSidecarRow.model_validate(row.model_dump(mode="json"))


def _require_non_empty(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string")
    return value


def _require_quantile_order(
    label: str,
    p25_ms: float,
    median_ms: float,
    p75_ms: float,
) -> None:
    if p25_ms > median_ms or median_ms > p75_ms:
        raise ValueError(f"{label} quantiles must satisfy p25 <= median <= p75")
