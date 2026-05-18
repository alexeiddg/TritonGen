"""Byte-identity audit for C1 and C2 aligned compile entrypoints."""

from __future__ import annotations

from typing import Any

from cluster1.diagnostics.revalidate_baseline_aligned_pipeline import (
    BaselineEntrypointEvaluation,
    evaluate_row_via_c1_entrypoint,
    evaluate_row_via_c2_entrypoint,
)
from cluster1.results.dataclass import GenerationResult, compute_unique_solution_hash
from shared.eval.failure_taxonomy import classify_failure
from shared.eval.schema import EvalResult


FIXED_PARSE_FAILURE_SOURCE = """\
import triton
import triton.language as tl

@triton.jit
def relu_kernel(x_ptr,
"""


def test_c1_and_c2_entrypoints_produce_identical_eval_result_payloads() -> None:
    row = _generation_row(FIXED_PARSE_FAILURE_SOURCE)

    c1_result = evaluate_row_via_c1_entrypoint(row)
    c2_result = evaluate_row_via_c2_entrypoint(row)

    assert _entrypoint_payload(c1_result) == _entrypoint_payload(c2_result)
    assert _eval_payload(row, c1_result) == _eval_payload(row, c2_result)


def _entrypoint_payload(result: BaselineEntrypointEvaluation) -> dict[str, Any]:
    return {
        "compile_success": result.compile_success,
        "compile_error_type": result.compile_error_type,
        "compile_error_msg": result.compile_error_msg,
        "canonical_failure_code": result.canonical_failure_code,
        "compile_results_by_dtype": {
            dtype: result.compile_results_by_dtype[dtype]
            for dtype in sorted(result.compile_results_by_dtype)
        },
        "n_shapes_tested": result.n_shapes_tested,
    }


def _eval_payload(
    row: GenerationResult,
    result: BaselineEntrypointEvaluation,
) -> dict[str, Any]:
    eval_result = EvalResult(
        kernel_id=None,
        kernel_name=row.kernel_name,
        kernel_class=row.kernel_class,
        kernelbench_level=None,
        condition="none",
        sample_index=0,
        model_id=row.model_id,
        run_id=row.run_id,
        timestamp=row.timestamp_utc,
        dtype_tested=row.dtype,
        source=row.source,
        source_hash=row.unique_solution_hash,
        ast_hash=None,
        level_reached=0 if not result.compile_success else 1,
        parse_success=False,
        parse_error=result.compile_error_msg,
        has_triton_decorator=None,
        signature_valid=None,
        compile_success=result.compile_success,
        compile_error=result.compile_error_msg,
        failure_code=result.canonical_failure_code,
        grammar_active=row.grammar_active,
        grammar_variant=row.grammar_variant,
        grammar_sha=row.grammar_sha,
        grammar_path=row.grammar_path,
        gbnf_parse_valid=row.gbnf_parse_valid,
        semantic_valid=row.semantic_valid,
        grammar_valid=row.grammar_valid,
        rejection_layer=row.rejection_layer,
        stop_reason=row.stop_reason,
        xgrammar_version=row.xgrammar_version,
        transformers_version=row.transformers_version,
        tokenizers_version=row.tokenizers_version,
        model_revision=row.model_revision,
        tokenizer_revision=row.tokenizer_revision,
        modal_image_sha=row.modal_image_sha,
        modal_image_provenance_sha256=row.modal_image_provenance_sha256,
        modal_image_provenance_components=row.modal_image_provenance_components,
    )
    payload = eval_result.to_dict()
    payload["failure_code"] = classify_failure(eval_result)
    return payload


def _generation_row(source: str) -> GenerationResult:
    return GenerationResult(
        source=source,
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        grammar_active=False,
        grammar_variant=None,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        compile_success=False,
        compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
        compile_error_type="SignatureError",
        compile_error_msg="SyntaxError: '(' was never closed",
        masked_token_rate=None,
        unique_solution_hash=compute_unique_solution_hash(source),
        n_shapes_tested=0,
        generation_seed=0,
        temperature=0.2,
        run_id="phase5-byte-identity",
        timestamp_utc="2026-05-18T00:00:00Z",
        failure_code="F0_PARSE",
    )
