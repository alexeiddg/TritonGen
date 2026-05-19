"""Tests for Phase 5: result dataclass, invariants, and JSONL logger."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cluster1.results.dataclass import (
    GENERATION_METADATA_SCHEMA_VERSION,
    GenerationResult,
    compute_unique_solution_hash,
    generation_result_record_for_deserialization,
    validate_paper_scale_metadata,
    validate_result_invariants,
)
from cluster1.results.logger import append_result_jsonl
from shared.generation_metadata import modal_image_provenance_digest


def _fallback_modal_image_components() -> dict[str, object]:
    return {
        "schema": "modal_image_fallback_provenance.v1",
        "image_source": {
            "path": "shared/modal_harness/images.py",
            "sha256": "a" * 64,
            "generation_package_pins": ["torch==2.8.0"],
        },
        "runtime_versions": {
            "xgrammar_version": "0.1.33",
            "transformers_version": "4.47.1",
            "tokenizers_version": "0.21.4",
        },
        "extra": {"modal_generation_gpu": "L4"},
    }


def _fallback_modal_image_sha256() -> str:
    return modal_image_provenance_digest(_fallback_modal_image_components())


def _make_result(**overrides) -> GenerationResult:
    defaults = {
        "source": "import triton\n@triton.jit\ndef k(): pass",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": True,
        "grammar_variant": "template_upper_bound",
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": True,
        "compile_results_by_dtype": {"fp32": True, "fp16": True, "bf16": True},
        "compile_error_type": None,
        "compile_error_msg": None,
        "masked_token_rate": 0.42,
        "unique_solution_hash": "abc123",
        "n_shapes_tested": 5,
        "generation_seed": 0,
        "temperature": 0.2,
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    defaults.update(overrides)
    return GenerationResult(**defaults)


# --- Task 5.6: schema tests ---

def test_generation_result_has_all_required_fields():
    result = _make_result()
    field_names = {f.name for f in result.__dataclass_fields__.values()}

    expected = {
        "source", "model_id", "grammar_active", "grammar_variant", "kernel_class", "kernel_name",
        "dtype", "compile_success", "compile_results_by_dtype",
        "compile_error_type", "compile_error_msg",
        "masked_token_rate", "unique_solution_hash", "n_shapes_tested",
        "generation_seed", "temperature", "run_id", "timestamp_utc",
        "failure_code",
        "generation_metadata_schema_version", "grammar_sha", "grammar_path",
        "gbnf_parse_valid", "semantic_valid", "grammar_valid",
        "rejection_layer", "stop_reason", "xgrammar_version",
        "transformers_version", "tokenizers_version", "model_revision",
        "tokenizer_revision", "modal_image_sha",
        "modal_image_provenance_sha256",
        "modal_image_provenance_components",
    }
    assert field_names == expected


def test_compile_results_by_dtype_has_three_keys():
    result = _make_result()
    assert set(result.compile_results_by_dtype.keys()) == {"fp32", "fp16", "bf16"}


def test_no_timing_fields():
    result = _make_result()
    for name in result.__dataclass_fields__:
        assert not name.endswith("_time_s"), f"forbidden timing field: {name}"


def test_no_numerical_correctness_fields():
    result = _make_result()
    forbidden = {"numerical_correct", "allclose", "reference_diff", "correctness"}
    for name in result.__dataclass_fields__:
        assert name not in forbidden, f"forbidden correctness field: {name}"


# --- Task 5.6: invariant tests ---

def test_invariant_grammar_off_with_masked_rate_raises():
    result = _make_result(
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=0.5,
    )
    with pytest.raises(
        ValueError,
        match="masked_token_rate must be None when grammar_active is False",
    ):
        validate_result_invariants(result)


def test_invariant_grammar_on_with_no_masked_rate_raises():
    result = _make_result(grammar_active=True, masked_token_rate=None)
    with pytest.raises(
        ValueError,
        match="masked_token_rate must not be None when grammar_active is True",
    ):
        validate_result_invariants(result)


def test_invariant_valid_grammar_on():
    result = _make_result(grammar_active=True, masked_token_rate=0.3)
    validate_result_invariants(result)


def test_invariant_valid_grammar_off():
    result = _make_result(grammar_active=False, grammar_variant=None, masked_token_rate=None)
    validate_result_invariants(result)


def test_invariant_grammar_off_with_variant_raises():
    result = _make_result(
        grammar_active=False,
        grammar_variant="template_upper_bound",
        masked_token_rate=None,
    )
    with pytest.raises(ValueError, match="grammar_variant must be None"):
        validate_result_invariants(result)


def test_invariant_grammar_on_with_invalid_variant_raises():
    result = _make_result(grammar_active=True, grammar_variant="bogus")
    with pytest.raises(ValueError, match="grammar_variant must be one of"):
        validate_result_invariants(result)


def test_grammar_valid_must_be_joint_parse_and_semantic() -> None:
    result = _make_result(
        gbnf_parse_valid=True,
        semantic_valid=False,
        grammar_valid=True,
        rejection_layer=None,
    )

    with pytest.raises(ValueError, match="grammar_valid must equal"):
        validate_result_invariants(result)


@pytest.mark.parametrize(
    "field_name",
    (
        "grammar_sha",
        "grammar_path",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
    ),
)
def test_current_schema_grammar_active_requires_complete_metadata(
    field_name: str,
) -> None:
    overrides = {
        "generation_metadata_schema_version": GENERATION_METADATA_SCHEMA_VERSION,
        "grammar_sha": "a" * 64,
        "grammar_path": "/runtime/cluster1/grammar/triton_kernel.gbnf",
        "gbnf_parse_valid": True,
        "semantic_valid": True,
        "grammar_valid": True,
        "rejection_layer": None,
    }
    overrides[field_name] = None
    result = _make_result(**overrides)

    with pytest.raises(ValueError, match=field_name):
        validate_result_invariants(result)


def test_current_schema_unknown_modal_image_requires_fallback_components() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        modal_image_sha="unknown",
        modal_image_provenance_sha256="b" * 64,
        modal_image_provenance_components=None,
    )

    with pytest.raises(ValueError, match="modal_image_provenance_components"):
        validate_result_invariants(result)


def test_current_schema_rejects_malformed_modal_image_fallback_digest() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        modal_image_sha="unknown",
        modal_image_provenance_sha256="not-a-sha",
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    with pytest.raises(ValueError, match="modal_image_provenance_sha256 must be"):
        validate_result_invariants(result)


def test_current_schema_accepts_fallback_sha_as_modal_image_sha() -> None:
    image_sha = _fallback_modal_image_sha256()
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha=image_sha,
        modal_image_provenance_sha256=image_sha,
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    validate_result_invariants(result)
    validate_paper_scale_metadata(result)


def test_current_schema_accepts_modal_image_object_id() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="im-123",
        modal_image_provenance_sha256=_fallback_modal_image_sha256(),
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    validate_result_invariants(result)
    validate_paper_scale_metadata(result)


def test_current_schema_rejects_bad_fallback_digest_with_modal_image_object_id() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="im-123",
        modal_image_provenance_sha256="not-a-sha",
        modal_image_provenance_components=None,
    )

    with pytest.raises(ValueError, match="modal_image_provenance_sha256"):
        validate_result_invariants(result)


def test_legacy_row_deserialization_adds_metadata_defaults() -> None:
    record = _make_result().__dict__.copy()
    for field_name in (
        "generation_metadata_schema_version",
        "grammar_sha",
        "grammar_path",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
        "rejection_layer",
        "stop_reason",
        "xgrammar_version",
        "transformers_version",
        "tokenizers_version",
        "model_revision",
        "tokenizer_revision",
        "modal_image_sha",
        "modal_image_provenance_sha256",
        "modal_image_provenance_components",
    ):
        record.pop(field_name, None)

    updated = generation_result_record_for_deserialization(record)

    assert updated["generation_metadata_schema_version"] == 0
    assert updated["grammar_sha"] is None
    assert updated["stop_reason"] == "unknown"
    assert updated["xgrammar_version"] == "unknown"
    assert updated["failure_code"] is None


def test_legacy_failed_row_deserialization_adds_canonical_failure_code() -> None:
    record = _make_result(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg="signature mismatch",
    ).__dict__.copy()
    record.pop("failure_code", None)

    updated = generation_result_record_for_deserialization(record)

    assert updated["compile_error_type"] == "SignatureError"
    assert updated["failure_code"] == "F0_BAD_SIGNATURE"


def test_legacy_signature_syntax_row_deserialization_adds_parse_failure_code() -> None:
    record = _make_result(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg=(
            "SignatureError: syntax error in generated source: "
            "invalid syntax (tmp.py, line 19)"
        ),
    ).__dict__.copy()
    record.pop("failure_code", None)

    updated = generation_result_record_for_deserialization(record)

    assert updated["compile_error_type"] == "SignatureError"
    assert updated["failure_code"] == "F0_PARSE"


def test_failure_code_is_required_for_new_failed_rows() -> None:
    result = _make_result(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="RuntimeError",
        compile_error_msg="launch failed",
        failure_code=None,
    )

    with pytest.raises(ValueError, match="failure_code is required"):
        validate_result_invariants(result)


def test_failure_code_must_match_legacy_compile_error_type() -> None:
    result = _make_result(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="CompilationError",
        compile_error_msg="bad IR",
        failure_code="F1_RUNTIME",
    )

    with pytest.raises(ValueError, match="inconsistent"):
        validate_result_invariants(result)


def test_paper_scale_metadata_gate_rejects_legacy_g_row() -> None:
    result = _make_result()

    with pytest.raises(ValueError, match="paper-scale rows require"):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_accepts_complete_g_row() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256=_fallback_modal_image_sha256(),
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    validate_paper_scale_metadata(result)


@pytest.mark.parametrize("field_name", ("model_revision", "tokenizer_revision"))
def test_paper_scale_metadata_gate_rejects_floating_revision(field_name: str) -> None:
    overrides = {
        "generation_metadata_schema_version": GENERATION_METADATA_SCHEMA_VERSION,
        "grammar_sha": "a" * 64,
        "grammar_path": "/runtime/cluster1/grammar/triton_kernel.gbnf",
        "gbnf_parse_valid": True,
        "semantic_valid": True,
        "grammar_valid": True,
        "rejection_layer": None,
        "stop_reason": "eos_token",
        "xgrammar_version": "0.1.33",
        "transformers_version": "4.47.1",
        "tokenizers_version": "0.21.4",
        "model_revision": "a" * 40,
        "tokenizer_revision": "b" * 40,
        "modal_image_sha": "unknown",
        "modal_image_provenance_sha256": _fallback_modal_image_sha256(),
        "modal_image_provenance_components": _fallback_modal_image_components(),
    }
    overrides[field_name] = "refs/heads/main"
    result = _make_result(**overrides)

    with pytest.raises(ValueError, match=f"{field_name}_not_immutable"):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_rejects_grammar_path_variant_mismatch() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        grammar_variant="task_agnostic",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256=_fallback_modal_image_sha256(),
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    with pytest.raises(ValueError, match="grammar_path does not match"):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_rejects_missing_rejection_layer() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=False,
        semantic_valid=False,
        grammar_valid=False,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256=_fallback_modal_image_sha256(),
        modal_image_provenance_components=_fallback_modal_image_components(),
    )

    with pytest.raises(ValueError, match="rejection_layer is required"):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_treats_null_modal_image_sha_as_missing() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha=None,
        modal_image_provenance_sha256=None,
    )

    with pytest.raises(
        ValueError,
        match="modal_image_sha_or_modal_image_provenance_sha256",
    ):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_requires_fallback_components() -> None:
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256="b" * 64,
        modal_image_provenance_components=None,
    )

    with pytest.raises(ValueError, match="modal_image_provenance_components"):
        validate_paper_scale_metadata(result)


def test_paper_scale_metadata_gate_rejects_fallback_component_mismatch() -> None:
    components = _fallback_modal_image_components()
    result = _make_result(
        generation_metadata_schema_version=GENERATION_METADATA_SCHEMA_VERSION,
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=True,
        grammar_valid=True,
        rejection_layer=None,
        stop_reason="eos_token",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256="b" * 64,
        modal_image_provenance_components=components,
    )

    with pytest.raises(
        ValueError,
        match="modal_image_provenance_sha256 must equal",
    ):
        validate_paper_scale_metadata(result)


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    (
        ("grammar_sha", "not-a-sha", "grammar_sha_malformed"),
        (
            "modal_image_provenance_sha256",
            "not-a-sha",
            "modal_image_provenance_sha256_malformed",
        ),
        ("modal_image_sha", "mutable-tag", "modal_image_sha_malformed"),
        ("modal_image_sha", " im-123 ", "modal_image_sha_malformed"),
    ),
)
def test_paper_scale_metadata_gate_rejects_malformed_sha_fields(
    field_name: str,
    value: str,
    match: str,
) -> None:
    overrides = {
        "generation_metadata_schema_version": GENERATION_METADATA_SCHEMA_VERSION,
        "grammar_sha": "a" * 64,
        "grammar_path": "/runtime/cluster1/grammar/triton_kernel.gbnf",
        "gbnf_parse_valid": True,
        "semantic_valid": True,
        "grammar_valid": True,
        "rejection_layer": None,
        "stop_reason": "eos_token",
        "xgrammar_version": "0.1.33",
        "transformers_version": "4.47.1",
        "tokenizers_version": "0.21.4",
        "model_revision": "a" * 40,
        "tokenizer_revision": "b" * 40,
        "modal_image_sha": "unknown",
        "modal_image_provenance_sha256": _fallback_modal_image_sha256(),
        "modal_image_provenance_components": _fallback_modal_image_components(),
        field_name: value,
    }
    result = _make_result(**overrides)

    with pytest.raises(ValueError, match=match):
        validate_paper_scale_metadata(result)


# --- Task 5.3: unique solution hash ---

def test_compute_unique_solution_hash_deterministic():
    src = "x = 1 + 2\ny = x * 3"
    h1 = compute_unique_solution_hash(src)
    h2 = compute_unique_solution_hash(src)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_compute_unique_solution_hash_normalizes_whitespace():
    src_a = "x  =  1\n\n\ny = 2"
    src_b = "x = 1\ny = 2"
    assert compute_unique_solution_hash(src_a) == compute_unique_solution_hash(src_b)


def test_compute_unique_solution_hash_fallback_on_bad_syntax():
    bad = "def f(: pass"
    h = compute_unique_solution_hash(bad)
    assert isinstance(h, str) and len(h) == 64


# --- Task 5.4: JSONL logger ---

def test_append_result_jsonl_creates_file(tmp_path: Path):
    out = tmp_path / "sub" / "results.jsonl"
    result = _make_result()
    append_result_jsonl(out, result)
    assert out.exists()
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["model_id"] == "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
    assert record["kernel_class"] == "elementwise"
    assert record["failure_code"] is None


def test_append_result_jsonl_appends(tmp_path: Path):
    out = tmp_path / "results.jsonl"
    append_result_jsonl(out, _make_result(kernel_name="relu"))
    append_result_jsonl(out, _make_result(kernel_name="softmax", kernel_class="reduction"))
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["kernel_name"] == "relu"
    assert json.loads(lines[1])["kernel_name"] == "softmax"


def test_jsonl_roundtrip_all_fields(tmp_path: Path):
    out = tmp_path / "results.jsonl"
    result = _make_result()
    append_result_jsonl(out, result)
    record = json.loads(out.read_text().strip())
    for field_name in result.__dataclass_fields__:
        assert field_name in record, f"missing field in JSONL: {field_name}"
