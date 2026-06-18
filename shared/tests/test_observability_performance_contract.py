from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.observability.performance_contract import (
    default_o6a_performance_contract,
    required_o6b_run_packet_fields,
    validate_o6a_performance_contract,
)
from shared.observability.redaction import (
    ObservabilityRedactionError,
    reject_forbidden_observability_payload,
    sanitize_attributes,
)
from shared.observability.schema import ObservabilityPerformanceContract


def test_o6a_performance_contract_is_metadata_only_and_default_denied() -> None:
    contract = default_o6a_performance_contract()

    assert contract.performance_execution_authorized is False
    assert contract.required_future_packet_type == "O6b_modal_gpu_performance"
    assert set(contract.timing_method_allowed_future) == {
        "cuda_events",
        "triton_do_bench",
        "torch_profiler",
    }
    assert contract.shape_dtype_device_lock_required is True
    assert contract.warmup_required is True
    assert contract.repetitions_required is True
    assert contract.separate_performance_sidecar_required is True
    assert contract.scientific_row_mutation_allowed is False
    assert (
        tuple(contract.future_o6b_required_fields)
        == required_o6b_run_packet_fields()
    )

    revalidated = validate_o6a_performance_contract(contract)
    assert revalidated == contract


@pytest.mark.parametrize(
    "update",
    [
        {"performance_execution_authorized": True},
        {"required_future_packet_type": "O6a_local_smoke"},
        {"timing_method_allowed_future": ["cuda_events"]},
        {"speedup_baseline_policy": "floating_best_observed_baseline"},
        {"shape_dtype_device_lock_required": False},
        {"warmup_required": False},
        {"repetitions_required": False},
        {"separate_performance_sidecar_required": False},
        {"scientific_row_mutation_allowed": True},
        {
            "smoke_dev_paper_scale_claim_boundary": (
                "development measurements are unrestricted"
            )
        },
        {"future_o6b_required_fields": ["benchmark_target_artifact"]},
    ],
)
def test_o6a_contract_rejects_execution_or_incomplete_future_packet_policy(
    update: dict[str, object],
) -> None:
    payload = default_o6a_performance_contract().model_dump(mode="json")
    payload.update(update)

    with pytest.raises(ValidationError):
        ObservabilityPerformanceContract.model_validate(payload)


@pytest.mark.parametrize(
    "extra_field",
    [
        "latency_ms",
        "throughput",
        "speedup",
        "kernel_time",
        "wall_time",
        "timing_samples",
        "profiler_trace",
        "median_ms",
        "speedup_vs_baseline",
    ],
)
def test_o6a_contract_rejects_actual_timing_values(extra_field: str) -> None:
    payload = default_o6a_performance_contract().model_dump(mode="json")
    payload[extra_field] = 1.23

    with pytest.raises(ValidationError):
        ObservabilityPerformanceContract.model_validate(payload)


def test_o6a_contract_payload_passes_redaction_as_planning_metadata() -> None:
    reject_forbidden_observability_payload(
        {
            "performance_contract": default_o6a_performance_contract().model_dump(
                mode="json"
            )
        }
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"performance_execution_authorized": True},
        {"performance_contract_version": "o6a.performance_contract.v1"},
        {"performance_sidecar_output_path": "sidecars/perf.jsonl"},
        {"benchmark_target_artifact": "artifact"},
    ],
)
def test_o6a_redaction_rejects_standalone_contract_keys(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ObservabilityRedactionError):
        reject_forbidden_observability_payload(payload)


def test_o6a_attributes_cannot_claim_performance_execution_authorization() -> None:
    with pytest.raises(ObservabilityRedactionError):
        sanitize_attributes({"performance_execution_authorized": True})


@pytest.mark.parametrize(
    "payload",
    [
        {"latency_ms": 12.0},
        {"throughput": 100.0},
        {"speedup": 2.0},
        {"kernel_time": 10.0},
        {"wall_time": 11.0},
        {"timing_samples": [1.0, 2.0]},
        {"profiler_trace": "trace"},
        {"profiler_output": "trace"},
        {"NsightOutput": "trace"},
        {"ncu_output": "trace"},
        {"benchmark_score": 1.0},
        {"performance_claim": "faster"},
        {"speedup_claim": "2x"},
        {"throughput_claim": "higher"},
        {"paper_scale_claim": "ready"},
        {"notes": "contains profiler trace"},
        {"notes": "contains Nsight output"},
        {"notes": "contains NCU output"},
    ],
)
def test_o6a_redaction_rejects_timing_profiler_and_claim_payloads(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ObservabilityRedactionError):
        reject_forbidden_observability_payload(payload)
