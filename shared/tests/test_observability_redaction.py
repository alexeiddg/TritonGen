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
        {"feedback": "try replacing the kernel"},
        {"raw_feedback": "try replacing the source"},
        {"rawModelOutput": "def kernel(): pass"},
        {"raw_compile_log": "Traceback with compiler dump"},
        {"token_ids": [1, 2, 3]},
        {"env": "HF_TOKEN=secret"},
        {"secret_name": "safe-looking-value"},
        {"message": "contains private eval details"},
        {"message": "eval_shape_set=[(1, 2)]"},
        {"message": "torch.testing.assert_close failed"},
        {"message": "allclose mismatch payload"},
        {"message": "MODAL_IDENTITY_TOKEN leaked"},
        {"message": "AWS_SECRET_ACCESS_KEY leaked"},
    ],
)
def test_forbidden_observability_payloads_fail_closed(payload: dict[str, object]) -> None:
    with pytest.raises(ObservabilityRedactionError):
        reject_forbidden_observability_payload(payload)


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


def test_attribute_limits_are_enforced() -> None:
    with pytest.raises(ObservabilityRedactionError, match="key count"):
        sanitize_attributes({f"k{i}": i for i in range(33)})

    with pytest.raises(ObservabilityRedactionError, match="too long"):
        sanitize_attributes({"k": "x" * 513})

    with pytest.raises(ObservabilityRedactionError, match="list length"):
        sanitize_attributes({"items": list(range(33))})
