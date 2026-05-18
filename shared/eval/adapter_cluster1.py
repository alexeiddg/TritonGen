"""One-way adapter from Cluster 1 ``GenerationResult`` to ``EvalResult``."""

from __future__ import annotations

from cluster1.results.dataclass import GenerationResult
from shared.eval.schema import EvalResult
from shared.factors.registry import require_cell_allowed_for_cluster


def eval_result_from_generation_result(
    row: GenerationResult,
    *,
    condition: str | None = None,
    sample_index: int | None = None,
) -> EvalResult:
    """Convert one Cluster 1 row into an EvalResult-lite record.

    This preserves the strict all-dtype ``compile_success`` value from
    ``GenerationResult`` and does not evaluate any future Level 2-4 fields.
    """

    factor_cell = _condition_from_row(row) if condition is None else condition
    factor_cell = require_cell_allowed_for_cluster("cluster1", factor_cell)
    level_reached = 1 if row.compile_success else 0

    return EvalResult(
        kernel_id=None,
        kernel_name=row.kernel_name,
        kernel_class=row.kernel_class,
        kernelbench_level=None,
        condition=factor_cell,
        sample_index=sample_index,
        model_id=row.model_id,
        run_id=row.run_id,
        timestamp=row.timestamp_utc,
        dtype_tested=row.dtype,
        source=row.source,
        source_hash=row.unique_solution_hash,
        ast_hash=None,
        level_reached=level_reached,
        parse_success=None,
        parse_error=None,
        has_triton_decorator=None,
        signature_valid=None,
        compile_success=row.compile_success,
        compile_error=row.compile_error_msg,
        failure_code=row.failure_code or row.compile_error_type,
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


def _condition_from_row(row: GenerationResult) -> str:
    return "G" if row.grammar_active else "none"
