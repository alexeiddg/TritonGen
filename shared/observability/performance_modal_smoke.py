"""O6b Modal GPU performance smoke entrypoint.

This module is opt-in and only registers Modal functions when invoked through
the Modal CLI. Normal unit-test imports do not import Modal, Torch, or Triton.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from shared.observability.performance_harness import (
    TimingSummary,
    build_performance_sidecar_row_from_summaries,
    shape_signature_from_shape,
    summarize_timing_samples,
)
from shared.observability.performance_sidecar import (
    performance_sidecar_sha256,
    validate_performance_sidecar_path,
    write_performance_sidecar_atomic,
)

O6B_EXPERIMENT_ID = "observability_o6b_performance_smoke"
O6B_RUN_ID = "o6b_smoke_relu_cuda_events"
O6B_BENCHMARK_ID = "o6b_smoke_relu_fp32_1048576_cuda_events"
O6B_BENCHMARK_SCOPE = "smoke"
O6B_KERNEL_CLASS = "elementwise_relu"
O6B_PROBLEM_ID = "smoke_relu"
O6B_DTYPE = "fp32"
O6B_SHAPE = (1048576,)
O6B_BASELINE_TYPE = "torch_reference"
O6B_CANDIDATE_TYPE = "triton_kernel_fixture"
O6B_TIMING_METHOD = "cuda_events"
O6B_WARMUP_ITERS = 10
O6B_REPETITIONS = 50
O6B_TIMEOUT_SECONDS = 300
O6B_GPU_TYPE_PREFERENCE = ("T4", "L4")
O6B_BENCHMARK_TARGET_ARTIFACT = "fixed_built_in_benchmark_fixture"
O6B_MODAL_IMAGE_DIGEST = (
    "unavailable: shared.modal_harness.images.triton_compile_image digest was "
    "not captured by the O6b smoke packet"
)
O6B_PERFORMANCE_SIDECAR_PATH = Path(
    "artifacts/observability_performance/o6b_smoke_relu_performance.jsonl"
)
O6B_REPORT_PATH = Path("audits/observability_sidecar_o6b_performance_smoke_report.md")


def build_o6b_run_packet(
    *,
    sidecar_path: str | Path = O6B_PERFORMANCE_SIDECAR_PATH,
) -> dict[str, Any]:
    """Return the signed O6b smoke packet values used by the entrypoint."""

    return {
        "benchmark_scope": O6B_BENCHMARK_SCOPE,
        "benchmark_target_artifact": O6B_BENCHMARK_TARGET_ARTIFACT,
        "baseline_artifact_or_type": O6B_BASELINE_TYPE,
        "candidate_type": O6B_CANDIDATE_TYPE,
        "kernel_class": O6B_KERNEL_CLASS,
        "problem_id": O6B_PROBLEM_ID,
        "dtype": O6B_DTYPE,
        "shape_set": [list(O6B_SHAPE)],
        "device_gpu_type": list(O6B_GPU_TYPE_PREFERENCE),
        "modal_image_digest": O6B_MODAL_IMAGE_DIGEST,
        "timing_method": O6B_TIMING_METHOD,
        "warmup_iterations": O6B_WARMUP_ITERS,
        "measured_repetitions": O6B_REPETITIONS,
        "timeout_s": O6B_TIMEOUT_SECONDS,
        "correctness_prerequisite": (
            "candidate and baseline outputs must match before timing"
        ),
        "performance_sidecar_output_path": str(sidecar_path),
        "no_scientific_row_mutation": True,
        "paper_scale_packet_required_for_claims": True,
        "modal_authorized": True,
        "gpu_authorized": True,
        "performance_execution_authorized": True,
        "generation_authorized": False,
        "output_mutation_authorized": False,
        "paper_scale_authorized": False,
        "profiler_trace_authorized": False,
        "nsight_authorized": False,
        "ncu_authorized": False,
    }


def pre_execution_notice(
    *,
    sidecar_path: str | Path = O6B_PERFORMANCE_SIDECAR_PATH,
) -> dict[str, Any]:
    """Return the required human-readable execution notice as structured data."""

    return {
        "modal_function_call": (
            "remote_o6b_performance_smoke.remote(build_o6b_run_packet())"
        ),
        "gpu_setting": list(O6B_GPU_TYPE_PREFERENCE),
        "shape": list(O6B_SHAPE),
        "dtype": O6B_DTYPE,
        "warmup_iters": O6B_WARMUP_ITERS,
        "repetitions": O6B_REPETITIONS,
        "sidecar_path": str(sidecar_path),
        "timeout_seconds": O6B_TIMEOUT_SECONDS,
        "no_output_mutation": "existing outputs/ is not read or written",
        "no_generation": "model generation is not invoked",
        "no_profiler_trace": "profiler traces are not collected",
    }


def run_o6b_smoke(
    *,
    sidecar_path: str | Path = O6B_PERFORMANCE_SIDECAR_PATH,
) -> dict[str, Any]:
    """Run the registered remote smoke function and write the local sidecar."""

    remote_function = globals().get("remote_o6b_performance_smoke")
    if remote_function is None:
        raise RuntimeError("O6b Modal function is not registered; use modal run -m")

    target_path = validate_performance_sidecar_path(sidecar_path)
    _require_signed_sidecar_path(sidecar_path)
    if target_path.exists():
        raise FileExistsError(f"performance sidecar already exists: {target_path}")
    packet = build_o6b_run_packet(sidecar_path=sidecar_path)
    print(json.dumps(pre_execution_notice(sidecar_path=sidecar_path), indent=2))
    remote_payload = remote_function.remote(packet)
    if remote_payload.get("correctness_prerequisite_passed") is not True:
        raise ValueError("O6b remote payload did not confirm correctness prerequisite")
    row = build_performance_sidecar_row_from_summaries(
        experiment_id=O6B_EXPERIMENT_ID,
        run_id=O6B_RUN_ID,
        benchmark_id=O6B_BENCHMARK_ID,
        benchmark_scope=O6B_BENCHMARK_SCOPE,
        kernel_class=O6B_KERNEL_CLASS,
        problem_id=O6B_PROBLEM_ID,
        dtype=O6B_DTYPE,
        baseline_type=O6B_BASELINE_TYPE,
        candidate_type=O6B_CANDIDATE_TYPE,
        timing_method=O6B_TIMING_METHOD,
        gpu_type=str(remote_payload["gpu_type"]),
        warmup_iters=O6B_WARMUP_ITERS,
        repetitions=O6B_REPETITIONS,
        baseline_summary=remote_payload["baseline_summary"],
        candidate_summary=remote_payload["candidate_summary"],
        baseline_spec=remote_payload["baseline_spec"],
        candidate_spec=remote_payload["candidate_spec"],
        correctness_prerequisite_passed=True,
        measurement_status="complete",
        caveats=[
            "smoke fixture only; not paper-scale evidence",
            "single shape and dtype only",
        ],
    )
    written_path = write_performance_sidecar_atomic(
        sidecar_path,
        row,
    )
    result = {
        "sidecar_path": str(written_path),
        "sidecar_sha256": performance_sidecar_sha256(written_path),
        "row": row.model_dump(mode="json"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def _o6b_relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: "tl.constexpr"):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    values = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    output = tl.where(values > 0.0, values, 0.0)
    tl.store(out_ptr + offsets, output, mask=mask)


def _remote_o6b_performance_smoke(packet: dict[str, Any]) -> dict[str, Any]:
    import torch
    import triton
    import triton.language as tl_module

    globals()["tl"] = tl_module
    _validate_remote_packet(packet)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the Modal container")

    device = torch.device("cuda:0")
    torch.manual_seed(0)
    x = torch.randn(O6B_SHAPE, device=device, dtype=torch.float32)
    kernel = triton.jit(_o6b_relu_kernel)
    n_elements = x.numel()
    block_size = 1024
    grid = (triton.cdiv(n_elements, block_size),)

    def baseline() -> Any:
        return torch.relu(x)

    def candidate() -> Any:
        out = torch.empty_like(x)
        kernel[grid](x, out, n_elements, BLOCK_SIZE=block_size)
        return out

    expected = baseline()
    actual = candidate()
    torch.cuda.synchronize(device)
    if not torch.equal(expected, actual):
        raise RuntimeError("correctness prerequisite failed for O6b smoke benchmark")

    baseline_samples = _measure_cuda_events(
        baseline,
        warmup_iters=O6B_WARMUP_ITERS,
        repetitions=O6B_REPETITIONS,
        torch_module=torch,
        device=device,
    )
    candidate_samples = _measure_cuda_events(
        candidate,
        warmup_iters=O6B_WARMUP_ITERS,
        repetitions=O6B_REPETITIONS,
        torch_module=torch,
        device=device,
    )
    baseline_summary = summarize_timing_samples(baseline_samples)
    candidate_summary = summarize_timing_samples(candidate_samples)
    shape_signature = shape_signature_from_shape(O6B_SHAPE)
    device_label = "cuda:0"

    return {
        "gpu_type": _safe_gpu_label(torch.cuda.get_device_name(device)),
        "correctness_prerequisite_passed": True,
        "baseline_summary": _timing_summary_payload(baseline_summary),
        "candidate_summary": _timing_summary_payload(candidate_summary),
        "baseline_spec": {
            "shape_signature": shape_signature,
            "dtype": O6B_DTYPE,
            "device": device_label,
        },
        "candidate_spec": {
            "shape_signature": shape_signature,
            "dtype": O6B_DTYPE,
            "device": device_label,
        },
    }


def _measure_cuda_events(
    function: Any,
    *,
    warmup_iters: int,
    repetitions: int,
    torch_module: Any,
    device: Any,
) -> list[float]:
    for _ in range(warmup_iters):
        function()
    torch_module.cuda.synchronize(device)

    samples_ms: list[float] = []
    for _ in range(repetitions):
        start = torch_module.cuda.Event(enable_timing=True)
        end = torch_module.cuda.Event(enable_timing=True)
        start.record()
        function()
        end.record()
        end.synchronize()
        samples_ms.append(float(start.elapsed_time(end)))
    return samples_ms


def _timing_summary_payload(summary: TimingSummary) -> dict[str, float]:
    return {
        "median_ms": summary.median_ms,
        "p25_ms": summary.p25_ms,
        "p75_ms": summary.p75_ms,
    }


def _safe_gpu_label(value: str) -> str:
    label = value.strip().replace(" ", "_")
    return label or "unknown_cuda_gpu"


def _validate_remote_packet(packet: dict[str, Any]) -> None:
    expected = build_o6b_run_packet()
    if set(packet) != set(expected):
        raise ValueError("O6b packet keys do not match the signed contract")
    for key, expected_value in expected.items():
        if packet.get(key) != expected_value:
            raise ValueError(f"O6b packet field {key!r} does not match the contract")


def _require_signed_sidecar_path(sidecar_path: str | Path) -> None:
    if str(sidecar_path) != str(O6B_PERFORMANCE_SIDECAR_PATH):
        raise ValueError("O6b sidecar path must match the signed run packet")


def _modal_entrypoint(
    sidecar_path: str = str(O6B_PERFORMANCE_SIDECAR_PATH),
) -> None:
    run_o6b_smoke(sidecar_path=sidecar_path)


def _register_modal_entrypoint_if_needed() -> None:
    if not _should_register_modal_entrypoint():
        return

    from shared.modal_harness.app import app
    from shared.modal_harness.images import triton_compile_image

    remote_function = app.function(
        image=triton_compile_image,
        gpu=list(O6B_GPU_TYPE_PREFERENCE),
        memory=24576,
        cpu=4.0,
        timeout=O6B_TIMEOUT_SECONDS,
        max_containers=1,
        min_containers=0,
        scaledown_window=120,
        name="remote_o6b_performance_smoke",
    )(_remote_o6b_performance_smoke)

    globals()["remote_o6b_performance_smoke"] = remote_function
    globals()["o6b_performance_smoke"] = app.local_entrypoint(
        name="o6b_performance_smoke"
    )(_modal_entrypoint)


def _should_register_modal_entrypoint() -> bool:
    return Path(sys.argv[0]).name == "modal"


_register_modal_entrypoint_if_needed()
