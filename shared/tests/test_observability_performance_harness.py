from __future__ import annotations

import inspect

import pytest

from shared.observability.performance_contract import required_o6b_run_packet_fields
from shared.observability.performance_harness import (
    TensorBenchmarkSpec,
    TimingSummary,
    build_performance_sidecar_row,
    build_performance_sidecar_row_from_summaries,
    compute_speedup_vs_baseline,
    shape_signature_from_shape,
    summarize_timing_samples,
    validate_same_shape_dtype_device,
)
from shared.observability import performance_modal_smoke

O6B_PERFORMANCE_SIDECAR_PATH = performance_modal_smoke.O6B_PERFORMANCE_SIDECAR_PATH
build_o6b_run_packet = performance_modal_smoke.build_o6b_run_packet
pre_execution_notice = performance_modal_smoke.pre_execution_notice


def _spec(device: str = "cuda:0") -> TensorBenchmarkSpec:
    return TensorBenchmarkSpec(
        shape_signature="1048576",
        dtype="fp32",
        device=device,
    )


def test_shape_signature_from_shape() -> None:
    assert shape_signature_from_shape([1048576]) == "1048576"
    assert shape_signature_from_shape([32, 64]) == "32x64"


@pytest.mark.parametrize("shape", [[], [0], [-1], [True], [1.5]])
def test_shape_signature_rejects_invalid_shapes(shape: list[object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        shape_signature_from_shape(shape)  # type: ignore[arg-type]


def test_timing_summary_quantiles_are_deterministic() -> None:
    summary = summarize_timing_samples([4.0, 1.0, 3.0, 2.0])

    assert summary == TimingSummary(median_ms=2.5, p25_ms=1.75, p75_ms=3.25)


def test_speedup_is_baseline_divided_by_candidate() -> None:
    assert compute_speedup_vs_baseline(
        baseline_median_ms=2.5,
        candidate_median_ms=1.0,
    ) == 2.5


@pytest.mark.parametrize(
    ("baseline", "candidate"),
    [
        (_spec(), TensorBenchmarkSpec("512", "fp32", "cuda:0")),
        (_spec(), TensorBenchmarkSpec("1048576", "fp16", "cuda:0")),
        (_spec(), TensorBenchmarkSpec("1048576", "fp32", "cuda:1")),
    ],
)
def test_shape_dtype_device_mismatch_fails_closed(
    baseline: TensorBenchmarkSpec,
    candidate: TensorBenchmarkSpec,
) -> None:
    with pytest.raises(ValueError, match="same shape/dtype/device"):
        validate_same_shape_dtype_device(baseline, candidate)


def test_build_performance_sidecar_row_from_samples() -> None:
    row = build_performance_sidecar_row(
        experiment_id="observability_o6b_performance_smoke",
        run_id="o6b_smoke_relu_cuda_events",
        benchmark_id="o6b_smoke_relu_fp32_1048576_cuda_events",
        benchmark_scope="smoke",
        kernel_class="elementwise_relu",
        problem_id="smoke_relu",
        dtype="fp32",
        baseline_type="torch_reference",
        candidate_type="triton_kernel_fixture",
        timing_method="cuda_events",
        gpu_type="NVIDIA_L4",
        warmup_iters=10,
        repetitions=4,
        baseline_samples_ms=[2.0, 2.2, 1.8, 2.0],
        candidate_samples_ms=[1.0, 1.1, 0.9, 1.0],
        baseline_spec=_spec(),
        candidate_spec=_spec(),
        correctness_prerequisite_passed=True,
        measurement_status="complete",
        caveats=["smoke fixture only; not paper-scale evidence"],
    )

    assert row.baseline_median_ms == 2.0
    assert row.candidate_median_ms == 1.0
    assert row.speedup_vs_baseline == 2.0
    assert row.scientific_row_mutation_allowed is False
    assert row.paper_scale_claim_allowed is False
    assert row.profiler_traces_allowed is False


def test_build_performance_sidecar_row_requires_correctness_prerequisite() -> None:
    with pytest.raises(ValueError, match="correctness prerequisite"):
        build_performance_sidecar_row_from_summaries(
            experiment_id="observability_o6b_performance_smoke",
            run_id="o6b_smoke_relu_cuda_events",
            benchmark_id="o6b_smoke_relu_fp32_1048576_cuda_events",
            benchmark_scope="smoke",
            kernel_class="elementwise_relu",
            problem_id="smoke_relu",
            dtype="fp32",
            baseline_type="torch_reference",
            candidate_type="triton_kernel_fixture",
            timing_method="cuda_events",
            gpu_type="NVIDIA_L4",
            warmup_iters=10,
            repetitions=50,
            baseline_summary=TimingSummary(2.0, 1.8, 2.2),
            candidate_summary=TimingSummary(1.0, 0.9, 1.1),
            baseline_spec=_spec(),
            candidate_spec=_spec(),
            correctness_prerequisite_passed=False,
            measurement_status="complete",
        )


def test_o6b_run_packet_matches_smoke_scope_and_boundaries() -> None:
    packet = build_o6b_run_packet()

    assert set(required_o6b_run_packet_fields()).issubset(packet)
    assert packet["benchmark_scope"] == "smoke"
    assert packet["benchmark_target_artifact"] == "fixed_built_in_benchmark_fixture"
    assert packet["baseline_artifact_or_type"] == "torch_reference"
    assert packet["candidate_type"] == "triton_kernel_fixture"
    assert packet["kernel_class"] == "elementwise_relu"
    assert packet["problem_id"] == "smoke_relu"
    assert packet["dtype"] == "fp32"
    assert packet["shape_set"] == [[1048576]]
    assert packet["device_gpu_type"] == ["T4", "L4"]
    assert packet["modal_image_digest"].startswith("unavailable:")
    assert packet["timing_method"] == "cuda_events"
    assert packet["warmup_iterations"] == 10
    assert packet["measured_repetitions"] == 50
    assert packet["timeout_s"] == 300
    assert packet["performance_sidecar_output_path"] == str(
        O6B_PERFORMANCE_SIDECAR_PATH
    )
    assert packet["no_scientific_row_mutation"] is True
    assert packet["paper_scale_packet_required_for_claims"] is True
    assert packet["modal_authorized"] is True
    assert packet["gpu_authorized"] is True
    assert packet["performance_execution_authorized"] is True
    assert packet["generation_authorized"] is False
    assert packet["output_mutation_authorized"] is False
    assert packet["paper_scale_authorized"] is False
    assert packet["profiler_trace_authorized"] is False
    assert packet["nsight_authorized"] is False
    assert packet["ncu_authorized"] is False

    old_aliases = {
        "benchmark_target",
        "baseline_type",
        "gpu_type_preference",
        "warmup_iters",
        "repetitions",
        "timeout_seconds",
        "performance_sidecar_path",
        "scientific_row_mutation_allowed",
        "paper_scale_claim_allowed",
        "profiler_traces_allowed",
    }
    assert old_aliases.isdisjoint(packet)


def test_o6b_pre_execution_notice_names_exact_bounds() -> None:
    notice = pre_execution_notice()

    assert notice["gpu_setting"] == ["T4", "L4"]
    assert notice["shape"] == [1048576]
    assert notice["dtype"] == "fp32"
    assert notice["warmup_iters"] == 10
    assert notice["repetitions"] == 50
    assert notice["sidecar_path"] == str(O6B_PERFORMANCE_SIDECAR_PATH)
    assert "outputs/" in notice["no_output_mutation"]


def test_o6b_remote_packet_rejects_sidecar_path_drift() -> None:
    packet = build_o6b_run_packet(
        sidecar_path="artifacts/observability_performance/other.jsonl"
    )

    with pytest.raises(ValueError, match="performance_sidecar_output_path"):
        performance_modal_smoke._validate_remote_packet(packet)


def test_o6b_remote_packet_rejects_extra_fields() -> None:
    packet = build_o6b_run_packet()
    packet["unauthorized_extra_field"] = "not signed"

    with pytest.raises(ValueError, match="packet keys"):
        performance_modal_smoke._validate_remote_packet(packet)


def test_o6b_smoke_rejects_unsigned_sidecar_path_before_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRemote:
        calls = 0

        def remote(self, packet: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return {}

    fake_remote = FakeRemote()
    monkeypatch.setattr(
        performance_modal_smoke,
        "remote_o6b_performance_smoke",
        fake_remote,
        raising=False,
    )

    with pytest.raises(ValueError, match="signed run packet"):
        performance_modal_smoke.run_o6b_smoke(
            sidecar_path="artifacts/observability_performance/other.jsonl"
        )

    assert fake_remote.calls == 0


def test_o6b_smoke_rejects_existing_sidecar_before_remote(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    class FakeRemote:
        calls = 0

        def remote(self, packet: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return {}

    target = tmp_path / O6B_PERFORMANCE_SIDECAR_PATH
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    fake_remote = FakeRemote()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        performance_modal_smoke,
        "remote_o6b_performance_smoke",
        fake_remote,
        raising=False,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        performance_modal_smoke.run_o6b_smoke()

    assert fake_remote.calls == 0


def test_o6b_smoke_entrypoint_does_not_expose_overwrite() -> None:
    assert "overwrite" not in inspect.signature(
        performance_modal_smoke.run_o6b_smoke
    ).parameters
    assert "overwrite" not in inspect.signature(
        performance_modal_smoke._modal_entrypoint
    ).parameters


def test_o6b_smoke_rejects_malformed_correctness_flag_before_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    class FakeRemote:
        calls = 0

        def remote(self, packet: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return {
                "gpu_type": "Tesla_T4",
                "correctness_prerequisite_passed": "false",
                "baseline_summary": {
                    "median_ms": 2.0,
                    "p25_ms": 1.8,
                    "p75_ms": 2.2,
                },
                "candidate_summary": {
                    "median_ms": 1.0,
                    "p25_ms": 0.9,
                    "p75_ms": 1.1,
                },
                "baseline_spec": {
                    "shape_signature": "1048576",
                    "dtype": "fp32",
                    "device": "cuda:0",
                },
                "candidate_spec": {
                    "shape_signature": "1048576",
                    "dtype": "fp32",
                    "device": "cuda:0",
                },
            }

    fake_remote = FakeRemote()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        performance_modal_smoke,
        "remote_o6b_performance_smoke",
        fake_remote,
        raising=False,
    )

    with pytest.raises(ValueError, match="correctness prerequisite"):
        performance_modal_smoke.run_o6b_smoke()

    assert fake_remote.calls == 1
    assert not (tmp_path / O6B_PERFORMANCE_SIDECAR_PATH).exists()


def test_o6b_smoke_rejects_invalid_sidecar_path_before_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRemote:
        calls = 0

        def remote(self, packet: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return {}

    fake_remote = FakeRemote()
    monkeypatch.setattr(
        performance_modal_smoke,
        "remote_o6b_performance_smoke",
        fake_remote,
        raising=False,
    )

    with pytest.raises(ValueError, match="outputs"):
        performance_modal_smoke.run_o6b_smoke(sidecar_path="outputs/o6b_bad.jsonl")

    assert fake_remote.calls == 0
