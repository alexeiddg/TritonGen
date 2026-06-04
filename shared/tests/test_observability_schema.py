from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from shared.observability.logger import validate_event_stream
from shared.observability.schema import (
    ObservabilityArtifactIdentity,
    ObservabilityAttemptIdentity,
    ObservabilityCostEstimate,
    ObservabilityEvent,
    ObservabilityHashSidecar,
    ObservabilityModalContext,
    ObservabilityRowIdentity,
    ObservabilitySummary,
    ObservabilityTokenCounts,
    canonical_event_json,
    canonical_json_bytes,
    row_sha256_from_canonical_json,
    sha256_bytes,
    summary_with_digest,
)

GIT_COMMIT = "4a8460081aa35a647901ea5fa120a76e0f7ef0e7"
EVENT_SHA = "a" * 64


def test_event_schema_accepts_canonical_event_and_exports_json_schema() -> None:
    event = _event(sequence=0)

    line = canonical_event_json(event)

    assert line.endswith("}") and "\n" not in line
    assert ObservabilityEvent.model_validate_json(line) == event
    assert ObservabilityEvent.model_json_schema()["additionalProperties"] is False


def test_event_schema_rejects_unknown_top_level_nested_and_enum_fields() -> None:
    payload = _event(sequence=0).model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        ObservabilityEvent.model_validate(payload)

    payload = _event(sequence=0).model_dump(mode="json")
    payload["row_identity"]["unexpected"] = True
    with pytest.raises(ValidationError):
        ObservabilityEvent.model_validate(payload)

    payload = _event(sequence=0).model_dump(mode="json")
    payload["event_type"] = "benchmark_started"
    with pytest.raises(ValidationError):
        ObservabilityEvent.model_validate(payload)


def test_event_schema_requires_uuid_and_valid_duration_fields() -> None:
    payload = _event(sequence=0).model_dump(mode="json")
    payload["event_id"] = "not-a-uuid"
    with pytest.raises(ValidationError, match="UUID"):
        ObservabilityEvent.model_validate(payload)

    payload = _event(sequence=0).model_dump(mode="json")
    payload["duration_ns"] = 10
    payload["end_monotonic_ns"] = payload["start_monotonic_ns"] + 11
    with pytest.raises(ValidationError, match="duration_ns"):
        ObservabilityEvent.model_validate(payload)

    payload = _event(sequence=0, duration_source="unavailable").model_dump(mode="json")
    payload["duration_ns"] = 1
    with pytest.raises(ValidationError, match="unavailable durations"):
        ObservabilityEvent.model_validate(payload)


def test_timestamp_fields_reject_impossible_dates() -> None:
    invalid_timestamp = "2026-99-99T99:99:99Z"

    payload = _event(sequence=0).model_dump(mode="json")
    payload["timestamp_utc"] = invalid_timestamp
    with pytest.raises(ValidationError, match="valid date"):
        ObservabilityEvent.model_validate(payload)

    payload = _summary().model_dump(mode="json")
    payload["generated_at_utc"] = invalid_timestamp
    with pytest.raises(ValidationError, match="valid date"):
        ObservabilitySummary.model_validate(payload)

    payload = _hash_sidecar().model_dump(mode="json")
    payload["generated_at_utc"] = invalid_timestamp
    with pytest.raises(ValidationError, match="valid date"):
        ObservabilityHashSidecar.model_validate(payload)

    with pytest.raises(ValidationError, match="valid date"):
        ObservabilityModalContext(
            modal_context_available=False,
            container_started_at_utc=invalid_timestamp,
            modal_context_source="unavailable",
        )


def test_event_stream_sequences_start_at_zero_without_gaps_and_unique_ids() -> None:
    validate_event_stream((_event(sequence=0), _event(sequence=1)))

    with pytest.raises(ValueError, match="contiguous"):
        validate_event_stream((_event(sequence=1),))

    duplicate = _event(sequence=0)
    with pytest.raises(ValueError, match="unique"):
        validate_event_stream((duplicate, duplicate.model_copy(update={"event_sequence": 1})))


def test_token_counts_and_hash_helpers_are_strict() -> None:
    counts = ObservabilityTokenCounts(
        token_counts_available=True,
        prompt_tokens=2,
        generated_tokens=3,
        total_tokens=5,
        token_count_source="existing_generation_result",
        token_count_status="available",
    )
    assert counts.total_tokens == 5

    unavailable = ObservabilityTokenCounts(
        token_counts_available=False,
        token_count_source="unavailable",
        token_count_status="unavailable",
    )
    assert unavailable.prompt_tokens is None

    with pytest.raises(ValidationError, match="total_tokens"):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=2,
            generated_tokens=3,
            total_tokens=6,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    with pytest.raises(ValidationError, match="available token counts"):
        ObservabilityTokenCounts(
            token_counts_available=True,
            token_count_source="unavailable",
            token_count_status="available",
        )

    with pytest.raises(ValidationError, match="all counts"):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=7,
            generated_tokens=None,
            total_tokens=None,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    partial = ObservabilityTokenCounts(
        token_counts_available=True,
        prompt_tokens=7,
        generated_tokens=None,
        total_tokens=None,
        token_count_source="existing_generation_result",
        token_count_status="partial",
    )
    assert partial.prompt_tokens == 7

    with pytest.raises(ValidationError, match="unavailable token counts"):
        ObservabilityTokenCounts(
            token_counts_available=False,
            total_tokens=1,
            token_count_source="unavailable",
            token_count_status="unavailable",
        )

    row = '{"a":1}'
    assert row_sha256_from_canonical_json(row) == sha256_bytes(row.encode("utf-8"))
    with pytest.raises(ValueError, match="newline"):
        row_sha256_from_canonical_json(row + "\n")


def test_numeric_telemetry_rejects_coerced_types() -> None:
    with pytest.raises(ValidationError):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens="2",
            generated_tokens=3,
            total_tokens=5,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    with pytest.raises(ValidationError):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=2.0,
            generated_tokens=3,
            total_tokens=5,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    with pytest.raises(ValidationError):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=True,
            generated_tokens=3,
            total_tokens=4,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    with pytest.raises(ValidationError):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=-1,
            generated_tokens=3,
            total_tokens=2,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    with pytest.raises(ValidationError):
        ObservabilityTokenCounts(
            token_counts_available=True,
            prompt_tokens=float("inf"),
            generated_tokens=3,
            total_tokens=4,
            token_count_source="existing_generation_result",
            token_count_status="available",
        )

    payload = _summary().model_dump(mode="json")
    payload["row_counts"] = {"completed": "1"}
    with pytest.raises(ValidationError):
        ObservabilitySummary.model_validate(payload)


def test_nonfinite_cost_numbers_are_rejected_before_serialization() -> None:
    with pytest.raises(ValidationError):
        ObservabilityCostEstimate(
            cost_estimate_available=True,
            estimated_input_cost=0.1,
            estimated_output_cost=float("inf"),
            estimated_total_cost=float("inf"),
            currency="USD",
            pricing_source="test_fixture",
            pricing_source_version="v1",
            cost_estimate_status="estimated",
            cost_estimate_method="test_fixture",
        )

    with pytest.raises(ValueError):
        canonical_json_bytes({"estimated_input_cost": float("inf")})


def test_cost_estimate_accepts_safe_estimates_and_unavailable_status() -> None:
    estimate = ObservabilityCostEstimate(
        cost_estimate_available=True,
        estimated_input_cost=0.12,
        estimated_output_cost=0.03,
        estimated_total_cost=0.15,
        currency="USD",
        pricing_source="test_fixture",
        pricing_source_version="2026-06-03",
        cost_estimate_status="estimated",
        cost_estimate_method="test_fixture",
    )
    assert estimate.estimated_total_cost == 0.15

    unavailable = ObservabilityCostEstimate(
        cost_estimate_available=False,
        cost_estimate_status="unavailable",
        cost_estimate_method="unavailable",
    )
    assert unavailable.estimated_total_cost is None


@pytest.mark.parametrize(
    "update",
    [
        {"estimated_input_cost": -0.01},
        {"estimated_input_cost": True},
        {"estimated_input_cost": "0.01"},
        {"estimated_input_cost": float("nan")},
        {"estimated_input_cost": 0.1234567890123},
        {"currency": "EUR"},
        {"estimated_total_cost": 0.14},
        {"pricing_source": None},
        {"pricing_source_version": None},
        {"cost_estimate_method": "unavailable"},
    ],
)
def test_cost_estimate_rejects_invalid_estimates(update: dict[str, object]) -> None:
    payload = {
        "cost_estimate_available": True,
        "estimated_input_cost": 0.12,
        "estimated_output_cost": 0.03,
        "estimated_total_cost": 0.15,
        "currency": "USD",
        "pricing_source": "test_fixture",
        "pricing_source_version": "2026-06-03",
        "cost_estimate_status": "estimated",
        "cost_estimate_method": "test_fixture",
    }
    payload.update(update)
    with pytest.raises(ValidationError):
        ObservabilityCostEstimate.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pricing_source", "billing_api_response"),
        ("pricing_source", "pricing_api_response"),
        ("pricing_source", "cloud_invoice_dump"),
        ("pricing_source", "external_pricing_fetch"),
        ("pricing_source", "modal.billing.workspace_billing_report"),
        ("pricing_source_version", "billingAPIResponse"),
        ("pricing_source_version", "externalPRICINGFetch"),
    ],
)
def test_cost_estimate_rejects_forbidden_pricing_labels(
    field: str,
    value: str,
) -> None:
    payload = {
        "cost_estimate_available": True,
        "estimated_input_cost": 0.12,
        "estimated_output_cost": 0.03,
        "estimated_total_cost": 0.15,
        "currency": "USD",
        "pricing_source": "test_fixture",
        "pricing_source_version": "2026-06-03",
        "cost_estimate_status": "estimated",
        "cost_estimate_method": "test_fixture",
    }
    payload[field] = value
    with pytest.raises(ValidationError, match="billing, invoice, API response"):
        ObservabilityCostEstimate.model_validate(payload)


@pytest.mark.parametrize(
    "update",
    [
        {"estimated_input_cost": 0.01},
        {"estimated_output_cost": 0.01},
        {"estimated_total_cost": 0.01},
        {"currency": "USD"},
        {"pricing_source": "test_fixture"},
        {"pricing_source_version": "v1"},
        {"cost_estimate_status": "estimated"},
        {"cost_estimate_method": "supplied"},
    ],
)
def test_unavailable_cost_estimate_rejects_estimate_metadata(
    update: dict[str, object],
) -> None:
    payload = {
        "cost_estimate_available": False,
        "cost_estimate_status": "unavailable",
        "cost_estimate_method": "unavailable",
    }
    payload.update(update)
    with pytest.raises(ValidationError):
        ObservabilityCostEstimate.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "estimate_status",
        "price_snapshot_id",
        "estimated_gpu_seconds",
        "estimated_cpu_core_seconds",
        "estimated_memory_gib_seconds",
        "estimated_gpu_cost_usd",
        "estimated_cpu_cost_usd",
        "estimated_memory_cost_usd",
        "estimated_total_cost_usd",
        "estimation_confidence",
        "cost_basis",
    ],
)
def test_old_draft_cost_fields_are_rejected(field: str) -> None:
    payload = {
        "cost_estimate_available": False,
        "cost_estimate_status": "unavailable",
        "cost_estimate_method": "unavailable",
        field: "draft",
    }
    with pytest.raises(ValidationError):
        ObservabilityCostEstimate.model_validate(payload)


def test_modal_context_accepts_safe_allowlisted_fields() -> None:
    context = ObservabilityModalContext(
        modal_context_available=True,
        is_remote=True,
        function_call_id="fc-123",
        input_id="in-123",
        task_id="task-123",
        image_id="image-123",
        region="us-east",
        cloud_provider="aws",
        environment_name="prod",
        app_name="tritongen",
        gpu_type="L4",
        gpu_count=1,
        cpu_cores=2.5,
        memory_gib=8.0,
        timeout_s=300,
        container_started_at_utc="2026-06-03T00:00:00Z",
        modal_context_source="runner_config",
    )

    assert context.modal_context_available is True
    assert context.function_call_id == "fc-123"


def test_modal_context_available_requires_identity_or_resource_field() -> None:
    with pytest.raises(ValidationError, match="runtime identity or resource field"):
        ObservabilityModalContext(
            modal_context_available=True,
            modal_context_source="runner_config",
        )


def test_modal_context_missing_values_are_unavailable_safe() -> None:
    context = ObservabilityModalContext(
        modal_context_available=False,
        is_remote=False,
        modal_context_source="unavailable",
    )

    assert context.modal_context_available is False

    with pytest.raises(ValidationError, match="unavailable Modal context"):
        ObservabilityModalContext(
            modal_context_available=False,
            is_remote=False,
            function_call_id="fc-123",
            modal_context_source="unavailable",
        )

    with pytest.raises(ValidationError, match="source unavailable"):
        ObservabilityModalContext(
            modal_context_available=False,
            is_remote=False,
            modal_context_source="runner_config",
        )


def test_modal_context_rejects_negative_and_nonfinite_resources() -> None:
    with pytest.raises(ValidationError):
        ObservabilityModalContext(
            modal_context_available=True,
            gpu_count=-1,
            modal_context_source="runner_config",
        )

    with pytest.raises(ValidationError):
        ObservabilityModalContext(
            modal_context_available=True,
            cpu_cores=-1.0,
            modal_context_source="runner_config",
        )

    with pytest.raises(ValidationError):
        ObservabilityModalContext(
            modal_context_available=True,
            memory_gib=float("inf"),
            modal_context_source="runner_config",
        )


def test_modal_context_rejects_forbidden_values_inside_safe_fields() -> None:
    with pytest.raises(ValidationError):
        ObservabilityModalContext(
            modal_context_available=True,
            is_remote=True,
            function_call_id="MODAL_IDENTITY_TOKEN leaked",
            modal_context_source="runner_config",
        )


def test_summary_rejects_absolute_workspace_and_hashes_self_reference() -> None:
    with pytest.raises(ValidationError, match="workspace"):
        _summary(workspace="/Users/alexeidelgado/Desktop/TritonGen")

    summary = _summary()
    final = summary_with_digest(summary)

    assert final.summary_sha256 is not None
    assert summary_with_digest(final).summary_sha256 == final.summary_sha256


def test_hash_sidecar_summary_status_contract_is_strict() -> None:
    sidecar = _hash_sidecar()
    assert sidecar.summary_status == "not_written"

    payload = sidecar.model_dump(mode="json")
    payload["summary_status"] = "written"
    with pytest.raises(ValidationError, match="summary_json_sha256"):
        ObservabilityHashSidecar.model_validate(payload)


def _event(
    *,
    sequence: int,
    event_id: str | None = None,
    duration_source: str = "local_monotonic",
) -> ObservabilityEvent:
    start = 1000 + sequence * 100
    end = start + 25
    measured = duration_source not in {"unavailable", "not_applicable"}
    return ObservabilityEvent(
        event_id=event_id or str(uuid.uuid4()),
        event_sequence=sequence,
        event_type="stage_completed",
        severity="info",
        timestamp_utc="2026-06-03T00:00:00Z",
        timestamp_unix_ns=1_780_444_800_000_000_000 + sequence,
        monotonic_ns=end,
        clock_scope_id="local-process",
        experiment_id="exp",
        run_id="run",
        artifact=ObservabilityArtifactIdentity(
            result_path="outputs/c3/result.jsonl",
            observability_event_path="outputs/c3/result.observability.jsonl",
            observability_summary_path="outputs/c3/result.observability.summary.json",
            git_commit=GIT_COMMIT,
        ),
        row_identity=ObservabilityRowIdentity(
            cluster="cluster3",
            condition="G+C+P",
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            base_seed=0,
            generation_seed=10,
            attempt_index=1,
            terminal_attempt_index=1,
            source_hash="b" * 64,
            row_sha256="c" * 64,
        ),
        stage="compile_eval",
        attempt=ObservabilityAttemptIdentity(attempt_index=1, condition="G+C+P"),
        status="succeeded",
        duration_ns=end - start if measured else None,
        duration_source=duration_source,
        start_monotonic_ns=start if measured else None,
        end_monotonic_ns=end if measured else None,
        token_counts=ObservabilityTokenCounts(
            token_counts_available=False,
            prompt_tokens=None,
            generated_tokens=None,
            total_tokens=None,
            token_count_source="not_applicable",
            token_count_status="not_applicable",
        ),
        modal_context=ObservabilityModalContext(
            modal_context_available=False,
            is_remote=False,
            modal_context_source="unavailable",
        ),
        cost_estimate=None,
        error_summary=None,
        attributes={"public_failure_code": None, "source_sha256": "b" * 64},
    )


def _summary(*, workspace: str = ".") -> ObservabilitySummary:
    return ObservabilitySummary(
        experiment_id="exp",
        run_id="run",
        result_path="outputs/c3/result.jsonl",
        observability_event_path="outputs/c3/result.observability.jsonl",
        observability_summary_path="outputs/c3/result.observability.summary.json",
        generated_at_utc="2026-06-03T00:00:00Z",
        git_commit=GIT_COMMIT,
        branch="codex/observability-sidecar-core",
        workspace=workspace,
        row_counts={"completed": 1},
        event_counts={"stage_completed": 1},
        stage_durations_ns={"compile_eval": 25},
        token_totals={
            "token_count_status": "unavailable",
            "events_with_token_counts": 1,
            "events_with_available_token_counts": 0,
            "prompt_tokens": 0,
            "generated_tokens": 0,
            "total_tokens": 0,
            "token_count_sources": ["not_applicable"],
        },
        modal_context_summary={"status": "unavailable"},
        estimated_cost_summary={
            "cost_estimate_available": False,
            "estimated_input_cost": None,
            "estimated_output_cost": None,
            "estimated_total_cost": None,
            "currency": None,
            "pricing_source": None,
            "pricing_source_version": None,
            "cost_estimate_status": "unavailable",
            "cost_estimate_method": "unavailable",
        },
        actual_billing_status="not_implemented",
        completeness_status="complete",
        caveats=[],
        source_event_sha256=EVENT_SHA,
        summary_sha256=None,
    )


def _hash_sidecar() -> ObservabilityHashSidecar:
    return ObservabilityHashSidecar(
        experiment_id="exp",
        run_id="run",
        result_path="outputs/c3/result.jsonl",
        observability_event_path="outputs/c3/result.observability.jsonl",
        observability_summary_path="outputs/c3/result.observability.summary.json",
        event_jsonl_sha256=EVENT_SHA,
        summary_json_sha256=None,
        summary_status="not_written",
        event_count=0,
        generated_at_utc="2026-06-03T00:00:00Z",
        hash_algorithm="sha256",
    )
