"""Tests for schema-aware Cluster 2 generated metadata validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cluster2.feedback.trace import TraceSummary
from cluster2.results.dataclass import (
    Cluster2EvalRow,
    generated_row,
    validate_generated_paper_scale_metadata,
)
from cluster2.validation.generated_metadata import (
    has_level0_evidence,
    level0_passed,
    validate_g_plus_c_smoke_jsonl,
    validate_g_plus_c_smoke_rows,
)
from shared.generation_metadata import (
    CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION,
    GRAMMAR_PATHS_BY_VARIANT,
)


MODEL_REVISION = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
TOKENIZER_REVISION = "8e8ed243bbe6f9a5aff549a0924562fc719b2b8a"
MODAL_IMAGE_SHA = "im-tU3VQyAbFvrusOxtlwspCN"


def test_g_plus_c_nested_generated_metadata_passes() -> None:
    result = validate_g_plus_c_smoke_rows([_valid_g_plus_c_payload()])

    assert len(result.rows) == 1
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.grammar_variant == "task_agnostic"


def test_g_plus_c_missing_generated_metadata_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload.pop("generated_metadata")

    with pytest.raises(ValueError, match="missing generated_metadata"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_unknown_tokenizer_revision_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload["generated_metadata"]["tokenizer_revision"] = "unknown"

    with pytest.raises(ValueError, match="generated_metadata.tokenizer_revision"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_unknown_modal_image_sha_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload["generated_metadata"]["modal_image_sha"] = "unknown"

    with pytest.raises(ValueError, match="generated_metadata.modal_image_sha"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_wrong_grammar_variant_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload["generated_metadata"]["grammar_variant"] = "template_upper_bound"

    with pytest.raises(ValueError, match="generated_metadata.grammar_variant"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_inactive_grammar_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload["grammar_active"] = False

    with pytest.raises(ValueError, match="grammar_active"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_missing_compile_success_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload.pop("compile_success")

    with pytest.raises(ValueError, match="missing top-level compile_success"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_nested_compile_success_does_not_replace_top_level_field() -> None:
    payload = _valid_g_plus_c_payload()
    compile_success = payload.pop("compile_success")
    payload["generated_metadata"]["compile_success"] = compile_success

    with pytest.raises(ValueError, match="missing top-level compile_success"):
        validate_g_plus_c_smoke_rows([payload])


def test_g_plus_c_explicit_level0_success_row_passes() -> None:
    payload = _valid_g_plus_c_payload()
    payload["level0_success"] = True

    result = validate_g_plus_c_smoke_rows([payload])

    assert len(result.rows) == 1
    assert has_level0_evidence(payload)
    assert level0_passed(payload)


def test_g_plus_c_implicit_level0_success_via_compile_success_passes() -> None:
    payload = _valid_g_plus_c_payload()
    _set_terminal_status(
        payload,
        failure_code=None,
        compile_success=True,
        functional_success=True,
        repair_set_success=True,
        eval_set_success=True,
    )

    result = validate_g_plus_c_smoke_rows([payload])

    assert len(result.rows) == 1
    assert has_level0_evidence(payload)
    assert level0_passed(payload)


def test_g_plus_c_implicit_level0_success_via_f1_failure_passes() -> None:
    payload = _valid_g_plus_c_payload()
    _set_terminal_status(
        payload,
        failure_code="F1_COMPILE",
        compile_success=False,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
    )

    result = validate_g_plus_c_smoke_rows([payload])

    assert len(result.rows) == 1
    assert has_level0_evidence(payload)
    assert level0_passed(payload)


def test_g_plus_c_explicit_f0_failure_is_evidence_not_success() -> None:
    payload = _valid_g_plus_c_payload()
    _set_terminal_status(
        payload,
        failure_code="F0_BAD_SIGNATURE",
        compile_success=False,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
    )

    result = validate_g_plus_c_smoke_rows([payload])

    assert len(result.rows) == 1
    assert has_level0_evidence(payload)
    assert not level0_passed(payload)


def test_g_plus_c_missing_all_level0_evidence_fails() -> None:
    payload = _valid_g_plus_c_payload()
    payload.pop("compile_success")
    payload.pop("functional_success")
    payload.pop("failure_code")

    with pytest.raises(ValueError, match="missing_level0_evidence"):
        validate_g_plus_c_smoke_rows([payload])


def test_existing_g_plus_c_smoke_artifact_validates() -> None:
    path = Path("outputs/cluster2/g_plus_c_smoke_n1.jsonl")
    if not path.exists():
        pytest.skip(f"missing smoke artifact: {path}")

    result = validate_g_plus_c_smoke_jsonl(path, expected_rows=3)

    assert len(result.rows) == 3


def test_g_plus_c_legacy_flat_metadata_can_be_validated_when_enabled() -> None:
    payload = _valid_g_plus_c_payload()
    generated_metadata = payload.pop("generated_metadata")
    payload.update(generated_metadata)

    result = validate_g_plus_c_smoke_rows(
        [payload],
        allow_legacy_top_level_metadata=True,
    )

    assert len(result.rows) == 1
    assert result.rows[0].generated_metadata is not None
    assert result.rows[0].generated_metadata.grammar_variant == "task_agnostic"


def test_c_nested_generated_metadata_regression_still_passes() -> None:
    row = Cluster2EvalRow.from_dict(_valid_c_payload())

    assert row.condition == "C"
    assert row.generated_metadata is not None
    assert row.generated_metadata.grammar_variant is None
    validate_generated_paper_scale_metadata(row.generated_metadata)


def _valid_g_plus_c_payload() -> dict:
    source_hash = _source_hash("gc")
    trace = _trace("F2_NUMERIC_LARGE", source_hash=source_hash)
    row = generated_row(
        condition="G+C",
        attempt_index=0,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=0,
        source_hash=source_hash,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        failure_code="F2_NUMERIC_LARGE",
        trace_summary=trace,
        repair_trace=(trace,),
        c2_generation_hashes=_c2_hashes(),
        generation_seed=0,
        grammar_variant="task_agnostic",
        grammar_path=GRAMMAR_PATHS_BY_VARIANT["task_agnostic"],
        grammar_sha=_task_agnostic_grammar_sha(),
        grammar_claim_scope="primary",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.1",
        modal_image_sha=MODAL_IMAGE_SHA,
        generation_metadata_schema_version=(
            CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        ),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=MODEL_REVISION,
        tokenizer_revision=TOKENIZER_REVISION,
        max_new_tokens=2048,
        temperature=0.2,
    )
    return row.to_dict()


def _valid_c_payload() -> dict:
    source_hash = _source_hash("c")
    trace = _trace("F0_PARSE", source_hash=source_hash)
    row = generated_row(
        condition="C",
        attempt_index=0,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        base_seed=0,
        source_hash=source_hash,
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        failure_code="F0_PARSE",
        trace_summary=trace,
        repair_trace=(trace,),
        c2_generation_hashes=_c2_hashes(),
        generation_seed=0,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.1",
        modal_image_sha=MODAL_IMAGE_SHA,
        generation_metadata_schema_version=(
            CLUSTER2_GENERATION_METADATA_SCHEMA_VERSION
        ),
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        model_revision=MODEL_REVISION,
        tokenizer_revision=TOKENIZER_REVISION,
        max_new_tokens=2048,
        temperature=0.2,
    )
    return row.to_dict()


def _trace(failure_code: str, *, source_hash: str) -> TraceSummary:
    return TraceSummary(
        attempt_index=0,
        failure_code=failure_code,
        public_failure_summary="Validation failed.",
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        source_hash=source_hash,
    )


def _set_terminal_status(
    payload: dict,
    *,
    failure_code: str | None,
    compile_success: bool,
    functional_success: bool,
    repair_set_success: bool,
    eval_set_success: bool,
) -> None:
    trace = TraceSummary(
        attempt_index=payload["attempt_index"],
        failure_code=failure_code,
        public_failure_summary=None if failure_code is None else "Validation failed.",
        functional_success=functional_success,
        repair_set_success=repair_set_success,
        eval_set_success=eval_set_success,
        source_hash=payload["source_hash"],
    )
    payload["compile_success"] = compile_success
    payload["functional_success"] = functional_success
    payload["repair_set_success"] = repair_set_success
    payload["eval_set_success"] = eval_set_success
    payload["failure_code"] = failure_code
    payload["trace_summary"] = trace.to_dict()
    payload["repair_trace"] = [trace.to_dict()]


def _source_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _c2_hashes() -> dict[str, str]:
    return {"cluster2/modal/generation.py": "3" * 64}


def _task_agnostic_grammar_sha() -> str:
    path = Path("cluster1/grammar/triton_kernel_agnostic.gbnf")
    return hashlib.sha256(path.read_bytes()).hexdigest()
