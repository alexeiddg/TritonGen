from __future__ import annotations

import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from shared.observability.performance_sidecar import (
    PerformanceSidecarRow,
    canonical_performance_row_json,
    load_performance_sidecar_rows,
    validate_performance_sidecar_path,
    write_performance_sidecar_atomic,
)


def _valid_row(**updates: object) -> PerformanceSidecarRow:
    payload: dict[str, object] = {
        "experiment_id": "observability_o6b_performance_smoke",
        "run_id": "o6b_smoke_relu_cuda_events",
        "benchmark_id": "o6b_smoke_relu_fp32_1048576_cuda_events",
        "benchmark_scope": "smoke",
        "kernel_class": "elementwise_relu",
        "problem_id": "smoke_relu",
        "dtype": "fp32",
        "shape_signature": "1048576",
        "baseline_type": "torch_reference",
        "candidate_type": "triton_kernel_fixture",
        "timing_method": "cuda_events",
        "gpu_type": "NVIDIA_L4",
        "warmup_iters": 10,
        "repetitions": 50,
        "baseline_median_ms": 2.0,
        "candidate_median_ms": 1.0,
        "baseline_p25_ms": 1.8,
        "baseline_p75_ms": 2.2,
        "candidate_p25_ms": 0.9,
        "candidate_p75_ms": 1.1,
        "speedup_vs_baseline": 2.0,
        "correctness_prerequisite_passed": True,
        "measurement_status": "complete",
        "caveats": [
            "smoke fixture only; not paper-scale evidence",
            "single shape and dtype only",
        ],
        "scientific_row_mutation_allowed": False,
        "paper_scale_claim_allowed": False,
        "profiler_traces_allowed": False,
    }
    payload.update(updates)
    return PerformanceSidecarRow.model_validate(payload)


def test_performance_sidecar_accepts_valid_smoke_row() -> None:
    row = _valid_row()

    assert row.benchmark_scope == "smoke"
    assert row.timing_method == "cuda_events"
    assert row.speedup_vs_baseline == 2.0
    assert row.correctness_prerequisite_passed is True
    assert row.scientific_row_mutation_allowed is False
    assert row.paper_scale_claim_allowed is False
    assert row.profiler_traces_allowed is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baseline_median_ms", math.inf),
        ("candidate_median_ms", -1.0),
        ("baseline_p25_ms", 0.0),
        ("candidate_p75_ms", math.nan),
    ],
)
def test_performance_sidecar_rejects_nonfinite_or_nonpositive_timing(
    field: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError):
        _valid_row(**{field: value})


def test_performance_sidecar_rejects_invented_speedup() -> None:
    with pytest.raises(ValidationError, match="speedup_vs_baseline"):
        _valid_row(speedup_vs_baseline=999.0)


@pytest.mark.parametrize(
    "field",
    [
        "scientific_row_mutation_allowed",
        "paper_scale_claim_allowed",
        "profiler_traces_allowed",
    ],
)
def test_performance_sidecar_requires_false_boundary_flags(field: str) -> None:
    with pytest.raises(ValidationError):
        _valid_row(**{field: True})


def test_performance_sidecar_rejects_extra_scientific_or_claim_fields() -> None:
    payload = _valid_row().model_dump(mode="json")
    payload["pass_at_k"] = 1.0

    with pytest.raises(ValidationError):
        PerformanceSidecarRow.model_validate(payload)


def test_performance_sidecar_writer_round_trips_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "artifacts/observability_performance/o6b.jsonl"
    row = _valid_row()

    written = write_performance_sidecar_atomic(path, row, repo_root=tmp_path)

    assert written == path
    assert written.read_text(encoding="utf-8") == canonical_performance_row_json(row) + "\n"
    assert load_performance_sidecar_rows(path) == [row]


def test_performance_sidecar_writer_revalidates_model_instances(
    tmp_path: Path,
) -> None:
    path = tmp_path / "artifacts/observability_performance/o6b.jsonl"
    forged = _valid_row().model_copy(
        update={
            "paper_scale_claim_allowed": True,
            "speedup_vs_baseline": 999.0,
        }
    )

    with pytest.raises(ValidationError):
        write_performance_sidecar_atomic(path, forged, repo_root=tmp_path)

    assert not path.exists()


def test_performance_sidecar_writer_rejects_existing_without_overwrite(
    tmp_path: Path,
) -> None:
    path = tmp_path / "artifacts/observability_performance/o6b.jsonl"
    write_performance_sidecar_atomic(path, _valid_row(), repo_root=tmp_path)

    with pytest.raises(FileExistsError):
        write_performance_sidecar_atomic(path, _valid_row(), repo_root=tmp_path)


def test_performance_sidecar_path_must_not_target_outputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outputs"):
        validate_performance_sidecar_path(
            tmp_path / "outputs/cluster3/perf.jsonl",
            repo_root=tmp_path,
        )


def test_performance_sidecar_path_must_stay_under_artifacts_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="artifacts/observability_performance"):
        validate_performance_sidecar_path(
            tmp_path / "artifacts/other/perf.jsonl",
            repo_root=tmp_path,
        )
