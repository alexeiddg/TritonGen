from __future__ import annotations

import pytest

from shared.observability.redaction import (
    ObservabilityRedactionError,
    reject_forbidden_observability_payload,
    sanitize_attributes,
    sanitize_error_summary,
)


def test_sanitize_attributes_accepts_only_shallow_json_primitives() -> None:
    sanitized = sanitize_attributes(
        {
            "stage": "compile_eval",
            "attempt_index": 1,
            "retryable": False,
            "notes": ["bounded", 1, None],
            "source_sha256": "a" * 64,
            "source_event_sha256": "c" * 64,
            "prompt_sha256": "b" * 64,
        }
    )

    assert sanitized["stage"] == "compile_eval"
    assert sanitized["notes"] == ["bounded", 1, None]

    with pytest.raises(ObservabilityRedactionError, match="primitive"):
        sanitize_attributes({"nested": {"not": "allowed"}})

    with pytest.raises(ObservabilityRedactionError, match="bytes"):
        reject_forbidden_observability_payload({"payload": b"raw"})


@pytest.mark.parametrize(
    "payload",
    [
        {"source_text": "def kernel(): pass"},
        {"source": "def kernel(): pass"},
        {"raw_source": "def kernel(): pass"},
        {"source_code": "def kernel(): pass"},
        {"sourceCode": "def kernel(): pass"},
        {"kernel_source": "def kernel(): pass"},
        {"kernelSource": "def kernel(): pass"},
        {"prompt_text": "write a kernel"},
        {"prompt": "write a kernel"},
        {"system_prompt": "write a kernel"},
        {"systemPrompt": "write a kernel"},
        {"user_prompt": "write a kernel"},
        {"hidden_prompt": "write a kernel"},
        {"hiddenPrompt": "write a kernel"},
        {"completion_text": "def kernel(): pass"},
        {"completionText": "def kernel(): pass"},
        {"generated_text": "def kernel(): pass"},
        {"generatedText": "def kernel(): pass"},
        {"feedback": "try replacing the kernel"},
        {"raw_feedback": "try replacing the source"},
        {"private_feedback": "private feedback payload"},
        {"privateFeedback": "private feedback payload"},
        {"rawModelOutput": "def kernel(): pass"},
        {"raw_output": "def kernel(): pass"},
        {"rawOutput": "def kernel(): pass"},
        {"raw_completion": "def kernel(): pass"},
        {"rawCompletion": "def kernel(): pass"},
        {"raw_compile_log": "Traceback with compiler dump"},
        {"token_ids": [1, 2, 3]},
        {"input_ids": [1, 2, 3]},
        {"output_ids": [1, 2, 3]},
        {"tokenizer_dump": {"ids": [1, 2, 3]}},
        {"tokenizerDump": {"ids": [1, 2, 3]}},
        {"tokenizer_state": "internal"},
        {"tokenizerState": "internal"},
        {"tokenizer_id": "tok"},
        {"tokenizerRevision": "rev"},
        {"max_new_tokens": 10},
        {"truncationApplied": False},
        {"env": "HF_TOKEN=secret"},
        {"secret_name": "safe-looking-value"},
        {"message": "contains private eval details"},
        {"message": "eval_shape_set=[(1, 2)]"},
        {"message": "torch.testing.assert_close failed"},
        {"message": "allclose mismatch payload"},
        {"message": "MODAL_IDENTITY_TOKEN leaked"},
        {"message": "AWS_SECRET_ACCESS_KEY leaked"},
        {"MODAL_IDENTITY_TOKEN": "secret"},
        {"token": "secret"},
        {"authorization": "Bearer secret"},
        {"api_key": "secret"},
        {"environment_variables": {"SAFE": "no"}},
        {"env": {"SAFE": "no"}},
        {"billing": {"workspace": "secret"}},
        {"invoice_id": "invoice-1"},
        {"actual_cost": "1.00"},
        {"actualBilling": "1.00"},
        {"actual_billing": "1.00"},
        {"account_charge": "1.00"},
        {"provider_bill": "1.00"},
        {"modalBill": "1.00"},
        {"credit_card": "4111111111111111"},
        {"paymentMethod": "card"},
        {"billing_account": "acct-1"},
        {"billing_account_secret": "secret"},
        {"customer_secret": "secret"},
        {"account_secret": "secret"},
        {"billing_api_response": {"cost": 1}},
        {"full_billing_api_response": {"cost": 1}},
        {"pricingApiResponse": {"rate": 1}},
        {"billingAPIResponse": {"cost": 1}},
        {"pricingAPIResponse": {"rate": 1}},
        {"raw_invoice_dump": "invoice"},
        {"cloud_invoice_dump": "invoice"},
        {"unredacted_workspace_billing_report": "report"},
        {"external_pricing_fetch": "https://example.invalid/pricing"},
        {"externalPRICINGFetch": "https://example.invalid/pricing"},
        {"provider_api_key": "secret"},
        {"cost_per_success": 1.0},
        {"costPerPass": 1.0},
        {"pass_at_k_cost": 1.0},
        {"ROI": 1.0},
        {"economic_lift": 1.0},
        {"benchmark_economics": "claimed"},
        {"benchmark_cost_conclusion": "cheaper"},
        {"paper_scale_cost_conclusion": "claimed"},
        {"billing_reconciliation_notes": "raw invoice dump"},
        {"billing_reconciliation_notes": "cost per success claim"},
        {"price_snapshot_id": "legacy-snapshot"},
        {"estimated_gpu_seconds": 1.0},
        {"estimated_total_cost_usd": "1.00"},
        {"cost_basis": "billing_report_interval"},
        {"gpu_utilization": 50},
        {"gpuPower": 10},
        {"gpu_memory": 1024},
        {"temperature": 80},
        {"profiler_trace": "trace"},
        {"kernel_timing": 12},
        {"latency_ms": 12},
        {"throughput": 1},
        {"speedup": 2},
        {"performance_metrics": {"x": 1}},
    ],
)
def test_forbidden_observability_payloads_fail_closed(payload: dict[str, object]) -> None:
    with pytest.raises(ObservabilityRedactionError):
        reject_forbidden_observability_payload(payload)


def test_safe_token_count_fields_remain_allowed() -> None:
    reject_forbidden_observability_payload(
        {
            "token_counts": {
                "token_counts_available": True,
                "prompt_tokens": 2,
                "generated_tokens": 3,
                "total_tokens": 5,
                "token_count_source": "existing_generation_result",
                "token_count_status": "available",
            },
            "token_totals": {
                "token_count_status": "available",
                "events_with_token_counts": 1,
                "events_with_available_token_counts": 1,
                "prompt_tokens": 2,
                "generated_tokens": 3,
                "total_tokens": 5,
                "token_count_sources": ["existing_generation_result"],
            },
        }
    )


def test_safe_estimated_cost_fields_remain_allowed() -> None:
    reject_forbidden_observability_payload(
        {
            "cost_estimate": {
                "cost_estimate_available": True,
                "estimated_input_cost": 0.12,
                "estimated_output_cost": 0.03,
                "estimated_total_cost": 0.15,
                "currency": "USD",
                "pricing_source": "test_fixture",
                "pricing_source_version": "2026-06-03",
                "cost_estimate_status": "estimated",
                "cost_estimate_method": "test_fixture",
            },
            "estimated_cost_summary": {
                "cost_estimate_available": True,
                "estimated_input_cost": 0.12,
                "estimated_output_cost": 0.03,
                "estimated_total_cost": 0.15,
                "currency": "USD",
                "pricing_source": "test_fixture",
                "pricing_source_version": "2026-06-03",
                "cost_estimate_status": "estimated",
                "cost_estimate_method": "test_fixture",
            },
        }
    )


def test_safe_actual_billing_reconciliation_fields_remain_allowed() -> None:
    reject_forbidden_observability_payload(
        {
            "billing_reconciliation": {
                "actual_billing_available": True,
                "actual_billing_status": "reconciled",
                "actual_billing_reconciled_at_utc": "2026-06-04T00:00:00Z",
                "billing_source": "test_fixture",
                "billing_source_version": "fixture-2026-06-04",
                "billing_time_window_start_utc": "2026-06-04T00:00:00Z",
                "billing_time_window_end_utc": "2026-06-04T00:05:00Z",
                "billing_attribution_method": "test_fixture",
                "billing_attribution_confidence": "high",
                "actual_total_cost": 0.42,
                "actual_currency": "USD",
                "billing_query_id": None,
                "billing_report_redacted_sha256": "d" * 64,
                "billing_reconciliation_notes": "redacted static unit fixture",
            },
            "actual_billing_summary": {
                "actual_billing_available": False,
                "actual_billing_status": "not_reconciled",
                "actual_billing_reconciled_at_utc": None,
                "billing_source": None,
                "billing_source_version": None,
                "billing_time_window_start_utc": None,
                "billing_time_window_end_utc": None,
                "billing_attribution_method": None,
                "billing_attribution_confidence": None,
                "actual_total_cost": None,
                "actual_currency": None,
                "billing_query_id": None,
                "billing_report_redacted_sha256": None,
                "billing_reconciliation_notes": "not reconciled",
            },
        }
    )


def test_error_summary_accepts_bounded_public_hashes_but_rejects_raw_content() -> None:
    summary = sanitize_error_summary(
        {
            "public_failure_code": "F1_COMPILE",
            "bounded_public_error_class": "SyntaxError",
            "error_excerpt_sha256": "c" * 64,
        }
    )

    assert summary is not None
    assert summary["public_failure_code"] == "F1_COMPILE"

    with pytest.raises(ObservabilityRedactionError):
        sanitize_error_summary({"message": "prompt text: write a kernel"})


def test_camel_case_hash_aliases_remain_allowed() -> None:
    reject_forbidden_observability_payload(
        {
            "sourceSha256": "a" * 64,
            "promptSha256": "b" * 64,
            "sourceEventSha256": "c" * 64,
        }
    )


def test_safe_modal_context_keys_remain_allowed() -> None:
    reject_forbidden_observability_payload(
        {
            "modal_context": {
                "modal_context_available": True,
                "is_remote": True,
                "function_call_id": "fc-1",
                "input_id": "in-1",
                "task_id": "task-1",
                "image_id": "image-1",
                "region": "us-east",
                "cloud_provider": "aws",
                "environment_name": "prod",
                "app_name": "tritongen",
                "gpu_type": "L4",
                "gpu_count": 1,
                "cpu_cores": 2.0,
                "memory_gib": 8.0,
                "timeout_s": 300,
                "container_started_at_utc": "2026-06-03T00:00:00Z",
                "modal_context_source": "runner_config",
            },
            "modal_context_summary": {
                "context_status": "available",
                "events_with_modal_context": 1,
                "events_with_available_context": 1,
                "modal_context_sources": ["runner_config"],
            },
            "actual_billing_status": "not_implemented",
        }
    )


def test_attribute_limits_are_enforced() -> None:
    with pytest.raises(ObservabilityRedactionError, match="key count"):
        sanitize_attributes({f"k{i}": i for i in range(33)})

    with pytest.raises(ObservabilityRedactionError, match="too long"):
        sanitize_attributes({"k": "x" * 513})

    with pytest.raises(ObservabilityRedactionError, match="list length"):
        sanitize_attributes({"items": list(range(33))})
