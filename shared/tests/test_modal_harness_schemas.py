"""Local unit tests for the shared Modal harness schemas.

These run without Modal — the schemas are pure Pydantic. They lock the
Cluster 1 boundary by asserting that reserved factor cells are rejected at
request construction time.
"""

from __future__ import annotations

import pytest

from shared.generation_metadata import modal_image_provenance_digest
from shared.modal_harness.errors import truncate_output
from shared.modal_harness.schemas import (
    RemoteCompileRequest,
    RemoteCompileResult,
    RemoteEvalResult,
    RemoteGenerationRequest,
    RemoteGenerationResult,
    dtype_name_to_bytes,
    remote_compile_result_to_cluster1_fields,
)


# ---------------------------------------------------------------------------
# RemoteCompileRequest.factor_cell validator
# ---------------------------------------------------------------------------

def _make_request(**overrides):
    base = dict(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        source="def relu(x): return x",
        run_id="test-run-id",
    )
    base.update(overrides)
    return RemoteCompileRequest(**base)


def test_none_mode_accepted() -> None:
    req = _make_request(factor_cell="none")
    assert req.factor_cell == "none"


def test_g_mode_accepted() -> None:
    req = _make_request(factor_cell="G")
    assert req.factor_cell == "G"


@pytest.mark.parametrize("reserved", ["C", "P", "G+C", "G+P", "C+P", "G+C+P"])
def test_reserved_modes_rejected(reserved: str) -> None:
    with pytest.raises(ValueError, match="only 'none' and 'G' are implemented"):
        _make_request(factor_cell=reserved)


def test_unknown_mode_rejected_by_literal() -> None:
    # Outside the FactorCell Literal: rejected by Pydantic's enum check
    # before our custom validator gets a chance.
    with pytest.raises(Exception):
        _make_request(factor_cell="bogus")


# ---------------------------------------------------------------------------
# RemoteCompileRequest round-trip
# ---------------------------------------------------------------------------

def test_request_round_trip_preserves_fields() -> None:
    req = _make_request(timeout_s=60)
    payload = req.model_dump()
    rebuilt = RemoteCompileRequest(**payload)
    assert rebuilt == req
    assert rebuilt.timeout_s == 60


# ---------------------------------------------------------------------------
# RemoteGenerationRequest / RemoteGenerationResult
# ---------------------------------------------------------------------------

def _make_generation_request(**overrides):
    base = dict(
        factor_cell="none",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        prompt="write relu",
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
        run_id="test-run-id",
    )
    base.update(overrides)
    return RemoteGenerationRequest(**base)


def test_generation_request_baseline_mode() -> None:
    req = _make_generation_request()
    assert req.factor_cell == "none"
    assert req.grammar_active is False
    assert req.grammar_variant is None
    assert req.grammar_path is None


def test_generation_request_g_mode() -> None:
    req = _make_generation_request(
        factor_cell="G",
        grammar_active=True,
        grammar_variant="template_upper_bound",
    )
    assert req.factor_cell == "G"
    assert req.grammar_active is True
    assert req.grammar_variant == "template_upper_bound"
    assert req.grammar_path == "cluster1/grammar/triton_kernel.gbnf"


def test_generation_request_g_mode_requires_explicit_variant() -> None:
    with pytest.raises(ValueError, match="grammar_variant must be one of"):
        _make_generation_request(factor_cell="G", grammar_active=True)


def test_generation_request_task_agnostic_variant_accepted() -> None:
    req = _make_generation_request(
        factor_cell="G",
        grammar_active=True,
        grammar_variant="task_agnostic",
    )
    assert req.grammar_variant == "task_agnostic"
    assert req.grammar_path == "cluster1/grammar/triton_kernel_agnostic.gbnf"


def test_generation_request_preserves_explicit_revisions() -> None:
    req = _make_generation_request(
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
    )

    assert req.model_revision == "a" * 40
    assert req.tokenizer_revision == "b" * 40
    assert RemoteGenerationRequest(**req.model_dump()) == req


def test_generation_request_rejects_mutable_revisions() -> None:
    with pytest.raises(ValueError, match="immutable revision"):
        _make_generation_request(model_revision="main")
    with pytest.raises(ValueError, match="immutable revision"):
        _make_generation_request(tokenizer_revision="latest")
    with pytest.raises(ValueError, match="40-character Hub commit SHA"):
        _make_generation_request(model_revision="refs/heads/main")


@pytest.mark.parametrize(
    ("grammar_variant", "grammar_path"),
    [
        ("template_upper_bound", "cluster1/grammar/triton_kernel.gbnf"),
        ("task_agnostic", "cluster1/grammar/triton_kernel_agnostic.gbnf"),
    ],
)
def test_generation_request_round_trip_preserves_both_grammar_variants(
    grammar_variant: str,
    grammar_path: str,
) -> None:
    req = _make_generation_request(
        factor_cell="G",
        grammar_active=True,
        grammar_variant=grammar_variant,
    )
    rebuilt = RemoteGenerationRequest(**req.model_dump())

    assert rebuilt == req
    assert rebuilt.grammar_variant == grammar_variant
    assert rebuilt.grammar_path == grammar_path


def test_generation_request_rejects_mismatched_grammar_path() -> None:
    with pytest.raises(ValueError, match="grammar_path must match"):
        _make_generation_request(
            factor_cell="G",
            grammar_active=True,
            grammar_variant="task_agnostic",
            grammar_path="cluster1/grammar/triton_kernel.gbnf",
        )


@pytest.mark.parametrize("reserved", ["C", "P", "G+C", "G+P", "C+P", "G+C+P"])
def test_generation_request_reserved_modes_rejected(reserved: str) -> None:
    with pytest.raises(ValueError, match="only 'none' and 'G' are implemented"):
        _make_generation_request(factor_cell=reserved)


def test_generation_request_factor_cell_matches_grammar_flag() -> None:
    with pytest.raises(ValueError, match="requires grammar_active=False"):
        _make_generation_request(factor_cell="none", grammar_active=True)
    with pytest.raises(ValueError, match="requires grammar_active=True"):
        _make_generation_request(factor_cell="G", grammar_active=False)
    with pytest.raises(ValueError, match="requires grammar_variant=None"):
        _make_generation_request(
            factor_cell="none",
            grammar_active=False,
            grammar_variant="template_upper_bound",
        )


def test_generation_request_invalid_grammar_variant_rejected() -> None:
    with pytest.raises(ValueError):
        _make_generation_request(
            factor_cell="G",
            grammar_active=True,
            grammar_variant="bogus",
        )


def test_generation_result_masked_rate_invariant() -> None:
    baseline = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    assert baseline.masked_token_rate is None

    constrained = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=True,
        grammar_variant="template_upper_bound",
        masked_token_rate=0.25,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    assert constrained.masked_token_rate == 0.25
    assert constrained.grammar_variant == "template_upper_bound"


def test_generation_result_validates_joint_grammar_metadata() -> None:
    result = RemoteGenerationResult(**_current_grammar_result_payload())

    assert result.grammar_valid is False
    assert result.rejection_layer == "semantic_validator"

    with pytest.raises(ValueError, match="grammar_valid must equal"):
        RemoteGenerationResult(
            **{
                **result.model_dump(),
                "grammar_valid": True,
                "rejection_layer": None,
            }
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "grammar_variant",
        "grammar_sha",
        "grammar_path",
        "gbnf_parse_valid",
        "semantic_valid",
        "grammar_valid",
    ],
)
def test_generation_result_rejects_incomplete_current_grammar_metadata(
    field_name: str,
) -> None:
    payload = _current_grammar_result_payload()
    if field_name == "grammar_variant":
        payload.pop(field_name)
    else:
        payload[field_name] = None

    with pytest.raises(ValueError, match=field_name):
        RemoteGenerationResult(**payload)


def test_generation_result_rejects_unknown_image_without_fallback_components() -> None:
    payload = _current_grammar_result_payload(
        modal_image_provenance_components=None,
    )

    with pytest.raises(ValueError, match="modal_image_provenance_components"):
        RemoteGenerationResult(**payload)


def test_generation_result_rejects_unknown_image_with_bad_fallback_digest() -> None:
    payload = _current_grammar_result_payload(
        modal_image_provenance_sha256="b" * 64,
    )

    with pytest.raises(ValueError, match="modal_image_provenance_sha256"):
        RemoteGenerationResult(**payload)


def test_generation_result_legacy_missing_variant_defaults_to_template() -> None:
    result = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=True,
        masked_token_rate=0.25,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )

    assert result.grammar_variant == "template_upper_bound"


def _fallback_modal_image_components() -> dict[str, object]:
    return {
        "image": "cluster1-modal-generation",
        "python_version": "3.11",
        "packages": ["xgrammar", "transformers", "tokenizers"],
        "extra": {"modal_generation_gpu": "L4"},
    }


def _current_grammar_result_payload(**overrides):
    image_components = _fallback_modal_image_components()
    payload = dict(
        source="@triton.jit",
        model_id="model",
        grammar_active=True,
        grammar_variant="task_agnostic",
        grammar_sha="a" * 64,
        grammar_path="/runtime/cluster1/grammar/triton_kernel_agnostic.gbnf",
        gbnf_parse_valid=True,
        semantic_valid=False,
        grammar_valid=False,
        rejection_layer="semantic_validator",
        stop_reason="max_new_tokens",
        xgrammar_version="0.1.33",
        transformers_version="4.47.1",
        tokenizers_version="0.21.4",
        model_revision="a" * 40,
        tokenizer_revision="b" * 40,
        modal_image_sha="unknown",
        modal_image_provenance_sha256=modal_image_provenance_digest(
            image_components
        ),
        modal_image_provenance_components=image_components,
        generation_metadata_schema_version=1,
        masked_token_rate=0.25,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    payload.update(overrides)
    return payload


def test_generation_result_rejects_wrong_masked_rate_shape() -> None:
    with pytest.raises(ValueError, match="must be None"):
        RemoteGenerationResult(
            source="@triton.jit",
            model_id="model",
            grammar_active=False,
            grammar_variant=None,
            masked_token_rate=0.1,
            generation_seed=0,
            temperature=0.2,
            run_id="rid",
        )
    with pytest.raises(ValueError, match="is required"):
        RemoteGenerationResult(
            source="@triton.jit",
            model_id="model",
            grammar_active=True,
            grammar_variant="template_upper_bound",
            masked_token_rate=None,
            generation_seed=0,
            temperature=0.2,
            run_id="rid",
        )


def test_generation_dtype_bytes_for_hardware_masks() -> None:
    assert dtype_name_to_bytes("fp32") == 4
    assert dtype_name_to_bytes("fp16") == 2
    assert dtype_name_to_bytes("bf16") == 2
    with pytest.raises(ValueError, match="unsupported dtype"):
        dtype_name_to_bytes("int8")


# ---------------------------------------------------------------------------
# RemoteCompileResult shape
# ---------------------------------------------------------------------------

def test_result_minimal_construction() -> None:
    result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=15,
        run_id="rid",
    )
    assert result.compile_error_type is None
    assert result.failure_code is None
    assert result.stdout == ""
    assert result.metadata == {}


def test_result_round_trip() -> None:
    result = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="CompilationError",
        compile_error_msg="bad IR",
        failure_code="F1_COMPILE",
        n_shapes_tested=0,
        stdout="hello",
        stderr="oops",
        traceback="Traceback ...",
        run_id="rid",
        factor_cell="G",
        modal_function_call_id="fc-abc",
        modal_input_id="in-abc",
        metadata={"app_name": "tritongen-gpu-harness"},
    )
    rebuilt = RemoteCompileResult(**result.model_dump())
    assert rebuilt == result
    assert rebuilt.factor_cell == "G"


def test_result_factor_cell_defaults_to_none() -> None:
    """Older sidecar logs without the field still parse cleanly."""
    result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=3,
        run_id="rid",
    )
    assert result.factor_cell is None


def test_remote_eval_result_round_trip() -> None:
    generation = RemoteGenerationResult(
        source="@triton.jit",
        model_id="model",
        grammar_active=False,
        grammar_variant=None,
        masked_token_rate=None,
        generation_seed=0,
        temperature=0.2,
        run_id="rid",
    )
    compile_result = RemoteCompileResult(
        compile_success=True,
        compile_results_by_dtype={"fp32": True, "fp16": True, "bf16": True},
        n_shapes_tested=3,
        run_id="rid",
    )
    result = RemoteEvalResult(generation=generation, compile=compile_result)
    rebuilt = RemoteEvalResult(**result.model_dump())
    assert rebuilt == result


def test_remote_compile_result_to_cluster1_fields() -> None:
    result = RemoteCompileResult(
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": True, "bf16": True},
        compile_error_type="RuntimeError",
        compile_error_msg="x" * 600,
        n_shapes_tested=2,
        run_id="rid",
    )

    fields = remote_compile_result_to_cluster1_fields(result)

    assert fields == {
        "compile_success": False,
        "compile_results_by_dtype": {"fp32": False, "fp16": True, "bf16": True},
        "compile_error_type": "RuntimeError",
        "compile_error_msg": "x" * 500,
        "failure_code": "F1_RUNTIME",
        "n_shapes_tested": 2,
    }


def test_result_has_no_timing_fields() -> None:
    """Cluster 1 boundary: no timing / profiling fields anywhere."""
    forbidden = {
        "elapsed_s",
        "compile_time_s",
        "generation_time_s",
        "latency_ms",
        "speedup",
    }
    for model in (RemoteCompileResult, RemoteGenerationResult):
        fields = set(model.model_fields.keys())
        assert forbidden.isdisjoint(fields)


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def test_truncate_output_short_text_unchanged() -> None:
    assert truncate_output("hello") == "hello"


def test_truncate_output_long_text_keeps_head_and_tail() -> None:
    text = "A" * 5000 + "B" * 5000
    out = truncate_output(text, max_chars=4000)
    assert len(out) <= 4000 + 64  # plus the small marker line
    assert out.startswith("A")
    assert out.rstrip().endswith("B")
    assert "truncated" in out


def test_truncate_output_empty_string() -> None:
    assert truncate_output("") == ""
