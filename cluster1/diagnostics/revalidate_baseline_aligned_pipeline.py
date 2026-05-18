"""Non-mutating baseline revalidation diagnostic for the aligned pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cluster1.results.dataclass import (
    GenerationResult,
    canonical_failure_code_for_compile_error_type,
    generation_result_record_for_deserialization,
)
from shared.eval.adapter_cluster1 import eval_result_from_generation_result
from shared.eval.failure_taxonomy import FAILURE_CODES, classify_failure


DIAGNOSTIC_NAME = "baseline_revalidation_aligned_pipeline"
_MAX_ERROR_CHARS = 500
_GENERATION_RESULT_FIELD_NAMES = frozenset(
    field_name for field_name in GenerationResult.__dataclass_fields__
)
_FAILURE_DRIFT_CATEGORIES = {
    "F0_PARSE": "parse",
    "F0_GBNF_PARSE": "gbnf_parse",
    "F0_SEMANTIC_INVALID": "semantic_invalid",
    "F0_GRAMMAR_INVALID": "grammar_invalid",
    "F0_NO_DECORATOR": "signature",
    "F0_BAD_SIGNATURE": "signature",
    "F0_SURFACE_VIOLATION": "surface_violation",
    "F1_COMPILE": "compile",
    "F1_RUNTIME": "runtime",
    "F2_NUMERIC_LARGE": "numeric",
    "F2_NUMERIC_NAN": "numeric",
    "F2_SHAPE_MISMATCH": "shape_mismatch",
    "F3_OOB": "safety_oob",
    "F3_RACE": "safety_race",
    "F3_TIMEOUT": "timeout",
}


@dataclass(frozen=True)
class BaselineEntrypointEvaluation:
    """Canonical Level 1 outcome from one aligned evaluation entrypoint."""

    compile_success: bool
    compile_error_type: str | None
    compile_error_msg: str | None
    canonical_failure_code: str | None
    compile_results_by_dtype: dict[str, bool]
    n_shapes_tested: int

    def __post_init__(self) -> None:
        if self.compile_success and self.canonical_failure_code is not None:
            raise ValueError("successful entrypoint evaluation must not have a failure code")
        if (
            self.canonical_failure_code is not None
            and self.canonical_failure_code not in FAILURE_CODES
        ):
            raise ValueError(
                "canonical_failure_code must be a shared failure code; got "
                f"{self.canonical_failure_code!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BaselineEvaluator = Callable[[GenerationResult], BaselineEntrypointEvaluation]


def revalidate_baseline_aligned_pipeline(
    input_jsonl: str | Path,
    output_jsonl: str | Path,
    *,
    c1_evaluator: BaselineEvaluator | None = None,
    c2_evaluator: BaselineEvaluator | None = None,
) -> dict[str, Any]:
    """Write a row-level non-mutating diagnostic for a frozen C1 baseline."""

    input_path = Path(input_jsonl)
    output_path = Path(output_jsonl)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("diagnostic output path must differ from input artifact path")
    if output_path.exists():
        raise FileExistsError(f"diagnostic output already exists: {output_path}")

    c1 = c1_evaluator or evaluate_row_via_c1_entrypoint
    c2 = c2_evaluator or evaluate_row_via_c2_entrypoint

    rows_written = 0
    compile_success_agreements = 0
    entrypoint_agreements = 0
    cross_category_label_drifts = 0
    expected_legacy_mappings = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temp_path = Path(output.name)
            for row_index, raw_row, row in _iter_generation_rows(input_path):
                diagnostic_row = _diagnostic_row(
                    row_index=row_index,
                    raw_row=raw_row,
                    row=row,
                    c1_result=c1(row),
                    c2_result=c2(row),
                )
                rows_written += 1
                compile_success_agreements += int(bool(diagnostic_row["agreement"]))
                entrypoint_agreements += int(
                    bool(diagnostic_row["entrypoint_agreement"])
                )
                cross_category_label_drifts += int(
                    bool(diagnostic_row["cross_category_label_drift"])
                )
                expected_legacy_mappings += int(
                    diagnostic_row["drift_reason"]
                    == "expected_legacy_to_canonical_mapping"
                )
                output.write(json.dumps(diagnostic_row, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())

        if output_path.exists():
            raise FileExistsError(f"diagnostic output already exists: {output_path}")
        if temp_path is None:
            raise RuntimeError("temporary diagnostic path was not created")
        _publish_temp_file_no_clobber(temp_path, output_path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise

    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_only": True,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "total_rows": rows_written,
        "compile_success_agreement_count": compile_success_agreements,
        "compile_success_drift_count": rows_written - compile_success_agreements,
        "entrypoint_agreement_count": entrypoint_agreements,
        "entrypoint_disagreement_count": rows_written - entrypoint_agreements,
        "cross_category_label_drift_count": cross_category_label_drifts,
        "expected_legacy_to_canonical_mapping_count": expected_legacy_mappings,
    }


def _publish_temp_file_no_clobber(temp_path: Path, output_path: Path) -> None:
    """Atomically publish ``temp_path`` without replacing an existing output."""

    os.link(temp_path, output_path)
    temp_path.unlink(missing_ok=True)


def evaluate_row_via_c1_entrypoint(
    row: GenerationResult,
) -> BaselineEntrypointEvaluation:
    """Run the direct Cluster 1 aligned compile entrypoint for one row."""

    from cluster1.data.kernels import get_kernel_spec
    from cluster1.validation.compile_check import check_compiles_all_dtypes

    spec = get_kernel_spec(row.kernel_class)
    compile_results = check_compiles_all_dtypes(
        row.source,
        spec.compile_spec,
        spec.shapes_by_dtype,
    )
    results = list(compile_results)
    first_failure = next((result for result in results if not result.success), None)
    failure_code = None
    if first_failure is not None:
        failure_code = first_failure.failure_code or _canonical_failure_code_from_error(
            first_failure.error_type,
            first_failure.error_msg,
        )

    return BaselineEntrypointEvaluation(
        compile_success=all(result.success for result in results),
        compile_error_type=first_failure.error_type if first_failure else None,
        compile_error_msg=_truncate(first_failure.error_msg if first_failure else None),
        canonical_failure_code=failure_code,
        compile_results_by_dtype={result.dtype: result.success for result in results},
        n_shapes_tested=sum(result.n_shapes_tested for result in results),
    )


def evaluate_row_via_c2_entrypoint(
    row: GenerationResult,
) -> BaselineEntrypointEvaluation:
    """Run the shared Level 1 path used as the local C2 aligned entrypoint."""

    from cluster1.data.kernels import get_kernel_spec
    from shared.eval.levels.level1_compile import check_compile_level1

    level1 = check_compile_level1(row.source, get_kernel_spec(row.kernel_class))
    failure_code = None
    if not level1.compile_success:
        failure_code = _canonical_failure_code_from_error(
            level1.compile_error_type,
            level1.compile_error,
        )

    return BaselineEntrypointEvaluation(
        compile_success=level1.compile_success,
        compile_error_type=level1.compile_error_type,
        compile_error_msg=_truncate(level1.compile_error),
        canonical_failure_code=failure_code,
        compile_results_by_dtype=dict(level1.compile_results_by_dtype),
        n_shapes_tested=level1.n_shapes_tested,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = revalidate_baseline_aligned_pipeline(args.input, args.output)
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local/non-mutating aligned baseline revalidation diagnostic. "
            "This command does not generate, invoke Modal, or mutate the input."
        )
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def _iter_generation_rows(
    input_path: Path,
) -> Iterator[tuple[int, dict[str, Any], GenerationResult]]:
    for row_index, line in enumerate(input_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            raise ValueError(f"blank JSONL row at line {row_index + 1}")
        raw_row = json.loads(line)
        record = generation_result_record_for_deserialization(raw_row)
        payload = {
            field_name: record[field_name]
            for field_name in _GENERATION_RESULT_FIELD_NAMES
            if field_name in record
        }
        yield row_index, raw_row, GenerationResult(**payload)


def _diagnostic_row(
    *,
    row_index: int,
    raw_row: dict[str, Any],
    row: GenerationResult,
    c1_result: BaselineEntrypointEvaluation,
    c2_result: BaselineEntrypointEvaluation,
) -> dict[str, Any]:
    original_canonical_failure_code = _original_canonical_failure_code(row)
    c1_entrypoint_record = _canonical_entrypoint_record(c1_result)
    c2_entrypoint_record = _canonical_entrypoint_record(c2_result)
    entrypoint_mismatch_fields = _entrypoint_mismatch_fields(
        c1_entrypoint_record,
        c2_entrypoint_record,
    )
    entrypoint_agreement = not entrypoint_mismatch_fields
    compile_success_agreement = row.compile_success == c1_result.compile_success
    label_drift_category = _label_drift_category(
        original_canonical_failure_code,
        c1_result.canonical_failure_code,
    )
    drift_reason = _drift_reason(
        row=row,
        raw_row=raw_row,
        c1_result=c1_result,
        entrypoint_agreement=entrypoint_agreement,
        label_drift_category=label_drift_category,
        original_canonical_failure_code=original_canonical_failure_code,
    )

    return {
        "diagnostic_name": DIAGNOSTIC_NAME,
        "diagnostic_only": True,
        "row_index": row_index,
        "row_number": row_index + 1,
        "source_sha256": hashlib.sha256(row.source.encode("utf-8")).hexdigest(),
        "kernel_class": row.kernel_class,
        "kernel_name": row.kernel_name,
        "dtype": row.dtype,
        "generation_seed": row.generation_seed,
        "base_seed": _base_seed(raw_row, row),
        "original_compile_success": row.compile_success,
        "new_compile_success": c1_result.compile_success,
        "original_compile_error_type": row.compile_error_type,
        "original_failure_code": raw_row.get("failure_code"),
        "original_canonical_failure_code": original_canonical_failure_code,
        "new_compile_error_type": c1_result.compile_error_type,
        "new_canonical_failure_code": c1_result.canonical_failure_code,
        "c1_entrypoint_compile_success": c1_result.compile_success,
        "c1_entrypoint_compile_error_type": c1_result.compile_error_type,
        "c1_entrypoint_failure_code": c1_result.canonical_failure_code,
        "c1_entrypoint_compile_results_by_dtype": c1_result.compile_results_by_dtype,
        "c1_entrypoint_n_shapes_tested": c1_result.n_shapes_tested,
        "c2_entrypoint_compile_success": c2_result.compile_success,
        "c2_entrypoint_compile_error_type": c2_result.compile_error_type,
        "c2_entrypoint_failure_code": c2_result.canonical_failure_code,
        "c2_entrypoint_compile_results_by_dtype": c2_result.compile_results_by_dtype,
        "c2_entrypoint_n_shapes_tested": c2_result.n_shapes_tested,
        "agreement": compile_success_agreement,
        "entrypoint_agreement": entrypoint_agreement,
        "entrypoint_mismatch_fields": entrypoint_mismatch_fields,
        "canonical_label_agreement": (
            original_canonical_failure_code == c1_result.canonical_failure_code
        ),
        "compile_success_drift": not compile_success_agreement,
        "label_drift_category": label_drift_category,
        "cross_category_label_drift": label_drift_category == "cross_category",
        "drift_reason": drift_reason,
        "original_compile_error_msg": _truncate(row.compile_error_msg),
        "new_compile_error_msg": c1_result.compile_error_msg,
        "n_shapes_tested_original": row.n_shapes_tested,
        "n_shapes_tested_new": c1_result.n_shapes_tested,
    }


def _original_canonical_failure_code(row: GenerationResult) -> str | None:
    eval_result = eval_result_from_generation_result(row)
    return classify_failure(eval_result)


def _canonical_entrypoint_record(
    result: BaselineEntrypointEvaluation,
) -> dict[str, Any]:
    return {
        "compile_success": result.compile_success,
        "compile_error_type": result.compile_error_type,
        "canonical_failure_code": result.canonical_failure_code,
        "compile_results_by_dtype": {
            dtype: bool(result.compile_results_by_dtype[dtype])
            for dtype in sorted(result.compile_results_by_dtype)
        },
        "n_shapes_tested": result.n_shapes_tested,
    }


def _entrypoint_mismatch_fields(
    c1_record: dict[str, Any],
    c2_record: dict[str, Any],
) -> list[str]:
    return [
        field_name
        for field_name in c1_record
        if c1_record[field_name] != c2_record.get(field_name)
    ]


def _drift_reason(
    *,
    row: GenerationResult,
    raw_row: dict[str, Any],
    c1_result: BaselineEntrypointEvaluation,
    entrypoint_agreement: bool,
    label_drift_category: str,
    original_canonical_failure_code: str | None,
) -> str | None:
    if not entrypoint_agreement:
        return "entrypoint_disagreement"
    if row.compile_success != c1_result.compile_success:
        return "compile_success_drift"
    if label_drift_category == "cross_category":
        return "cross_category_label_drift"
    if label_drift_category == "same_category":
        return "same_category_label_drift"
    if (
        raw_row.get("failure_code") is None
        and row.compile_error_type is not None
        and original_canonical_failure_code == c1_result.canonical_failure_code
    ):
        return "expected_legacy_to_canonical_mapping"
    return None


def _label_drift_category(
    original_failure_code: str | None,
    new_failure_code: str | None,
) -> str:
    if original_failure_code == new_failure_code:
        return "none"
    if _failure_category(original_failure_code) != _failure_category(new_failure_code):
        return "cross_category"
    return "same_category"


def _failure_category(failure_code: str | None) -> str | None:
    if failure_code is None:
        return None
    return _FAILURE_DRIFT_CATEGORIES.get(failure_code, failure_code)


def _base_seed(raw_row: dict[str, Any], row: GenerationResult) -> int | None:
    value = raw_row.get("base_seed")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return row.generation_seed


def _canonical_failure_code_from_error(
    error_type: str | None,
    error_msg: str | None,
) -> str | None:
    if error_type == "SignatureError" and "syntax" in (error_msg or "").lower():
        return "F0_PARSE"
    mapped = canonical_failure_code_for_compile_error_type(error_type)
    if mapped is not None:
        return mapped
    if error_type is None:
        return None
    if "runtime" in (error_msg or "").lower():
        return "F1_RUNTIME"
    return "F1_COMPILE"


def _truncate(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:_MAX_ERROR_CHARS]


if __name__ == "__main__":
    raise SystemExit(main())
