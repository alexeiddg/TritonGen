"""O6a performance sidecar contract helpers.

This module is intentionally metadata-only. It defines the contract that a
future O6b packet must satisfy before any Modal/GPU timing execution exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from shared.observability.schema import (
    O6B_REQUIRED_PERFORMANCE_RUN_PACKET_FIELDS,
    ObservabilityPerformanceContract,
)

O6A_PERFORMANCE_CONTRACT_VERSION = "o6a.performance_contract.v1"
O6A_REQUIRED_FUTURE_PACKET_TYPE = "O6b_modal_gpu_performance"
O6A_TIMING_METHOD_CANDIDATES = (
    "cuda_events",
    "triton_do_bench",
    "torch_profiler",
)
O6A_SPEEDUP_BASELINE_POLICY = "fixed_baseline_same_shape_dtype_device"
O6A_CLAIM_BOUNDARY = (
    "Smoke or development timing may not be treated as paper-scale performance "
    "claims without a separately approved paper-scale packet."
)


def default_o6a_performance_contract() -> ObservabilityPerformanceContract:
    """Return the accepted O6a contract with execution still unauthorized."""

    return ObservabilityPerformanceContract(
        performance_contract_version=O6A_PERFORMANCE_CONTRACT_VERSION,
        performance_execution_authorized=False,
        required_future_packet_type=O6A_REQUIRED_FUTURE_PACKET_TYPE,
        timing_method_allowed_future=list(O6A_TIMING_METHOD_CANDIDATES),
        speedup_baseline_policy=O6A_SPEEDUP_BASELINE_POLICY,
        shape_dtype_device_lock_required=True,
        warmup_required=True,
        repetitions_required=True,
        separate_performance_sidecar_required=True,
        scientific_row_mutation_allowed=False,
        smoke_dev_paper_scale_claim_boundary=O6A_CLAIM_BOUNDARY,
        future_o6b_required_fields=list(O6B_REQUIRED_PERFORMANCE_RUN_PACKET_FIELDS),
    )


def required_o6b_run_packet_fields() -> tuple[str, ...]:
    """Return required future O6b packet fields without validating real values."""

    return O6B_REQUIRED_PERFORMANCE_RUN_PACKET_FIELDS


def validate_o6a_performance_contract(
    payload: Mapping[str, Any] | ObservabilityPerformanceContract,
) -> ObservabilityPerformanceContract:
    """Validate an O6a metadata-only contract payload."""

    if isinstance(payload, ObservabilityPerformanceContract):
        payload = payload.model_dump(mode="json")
    return ObservabilityPerformanceContract.model_validate(payload)
