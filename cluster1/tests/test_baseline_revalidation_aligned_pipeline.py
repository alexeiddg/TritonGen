"""Tests for the local baseline revalidation diagnostic utility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cluster1.diagnostics.revalidate_baseline_aligned_pipeline import (
    BaselineEntrypointEvaluation,
    _publish_temp_file_no_clobber,
    revalidate_baseline_aligned_pipeline,
)
from cluster1.results.dataclass import compute_unique_solution_hash


def test_revalidation_writes_diagnostics_without_mutating_input(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(
                source="import triton\n# row 0\n",
                compile_success=False,
                compile_error_type="SignatureError",
                compile_error_msg="signature mismatch",
            ),
            _legacy_row(
                source="import triton\n# row 1\n",
                generation_seed=1,
                compile_success=True,
                compile_error_type=None,
                compile_error_msg=None,
            ),
        ],
    )
    original_bytes = input_path.read_bytes()

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
                1: _entrypoint_result(compile_success=True),
            }
        ),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
                1: _entrypoint_result(compile_success=True),
            }
        ),
    )

    rows = _read_jsonl(output_path)
    assert input_path.read_bytes() == original_bytes
    assert summary["diagnostic_name"] == "baseline_revalidation_aligned_pipeline"
    assert summary["diagnostic_only"] is True
    assert summary["total_rows"] == 2
    assert summary["compile_success_drift_count"] == 0
    assert summary["entrypoint_disagreement_count"] == 0
    assert rows[0]["diagnostic_only"] is True
    assert rows[0]["row_index"] == 0
    assert rows[0]["row_number"] == 1
    assert rows[0]["kernel_class"] == "elementwise"
    assert rows[0]["kernel_name"] == "relu"
    assert rows[0]["dtype"] == "fp32"
    assert rows[0]["generation_seed"] == 0
    assert rows[0]["base_seed"] == 0
    assert rows[0]["original_compile_success"] is False
    assert rows[0]["new_compile_success"] is False
    assert rows[0]["original_compile_error_type"] == "SignatureError"
    assert rows[0]["original_failure_code"] is None
    assert rows[0]["original_canonical_failure_code"] == "F0_BAD_SIGNATURE"
    assert rows[0]["new_compile_error_type"] == "SignatureError"
    assert rows[0]["new_canonical_failure_code"] == "F0_BAD_SIGNATURE"
    assert rows[0]["agreement"] is True
    assert rows[0]["entrypoint_agreement"] is True
    assert rows[0]["entrypoint_mismatch_fields"] == []
    assert rows[0]["canonical_label_agreement"] is True
    assert rows[0]["compile_success_drift"] is False
    assert rows[0]["cross_category_label_drift"] is False
    assert rows[0]["drift_reason"] == "expected_legacy_to_canonical_mapping"
    assert rows[1]["new_canonical_failure_code"] is None
    assert rows[1]["drift_reason"] is None


def test_revalidation_flags_compile_success_and_entrypoint_drift(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(
                compile_success=False,
                compile_error_type="SignatureError",
                compile_error_msg="signature mismatch",
            )
        ],
    )

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator({0: _entrypoint_result(compile_success=True)}),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                )
            }
        ),
    )

    row = _read_jsonl(output_path)[0]
    assert summary["compile_success_drift_count"] == 1
    assert summary["entrypoint_disagreement_count"] == 1
    assert row["agreement"] is False
    assert row["entrypoint_agreement"] is False
    assert "compile_success" in row["entrypoint_mismatch_fields"]
    assert row["compile_success_drift"] is True
    assert row["drift_reason"] == "entrypoint_disagreement"


def test_revalidation_flags_entrypoint_shape_or_dtype_map_drift(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(
                compile_success=False,
                compile_error_type="SignatureError",
                compile_error_msg="signature mismatch",
            )
        ],
    )

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                    compile_results_by_dtype={
                        "fp32": False,
                        "fp16": False,
                        "bf16": False,
                    },
                    n_shapes_tested=0,
                )
            }
        ),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                    compile_results_by_dtype={
                        "fp32": False,
                        "fp16": True,
                        "bf16": False,
                    },
                    n_shapes_tested=4,
                )
            }
        ),
    )

    row = _read_jsonl(output_path)[0]
    assert summary["compile_success_drift_count"] == 0
    assert summary["entrypoint_disagreement_count"] == 1
    assert row["agreement"] is True
    assert row["entrypoint_agreement"] is False
    assert row["entrypoint_mismatch_fields"] == [
        "compile_results_by_dtype",
        "n_shapes_tested",
    ]
    assert row["drift_reason"] == "entrypoint_disagreement"


def test_revalidation_flags_cross_category_label_drift(tmp_path: Path) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(
                compile_success=False,
                compile_error_type="SignatureError",
                compile_error_msg="signature mismatch",
            )
        ],
    )

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="RuntimeError",
                    canonical_failure_code="F1_RUNTIME",
                )
            }
        ),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="RuntimeError",
                    canonical_failure_code="F1_RUNTIME",
                )
            }
        ),
    )

    row = _read_jsonl(output_path)[0]
    assert summary["cross_category_label_drift_count"] == 1
    assert row["agreement"] is True
    assert row["canonical_label_agreement"] is False
    assert row["label_drift_category"] == "cross_category"
    assert row["cross_category_label_drift"] is True
    assert row["drift_reason"] == "cross_category_label_drift"


def test_revalidation_flags_signature_to_parse_label_drift(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(
                compile_success=False,
                compile_error_type="SignatureError",
                compile_error_msg="signature mismatch",
            )
        ],
    )

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_PARSE",
                )
            }
        ),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_PARSE",
                )
            }
        ),
    )

    row = _read_jsonl(output_path)[0]
    assert summary["cross_category_label_drift_count"] == 1
    assert row["agreement"] is True
    assert row["canonical_label_agreement"] is False
    assert row["original_canonical_failure_code"] == "F0_BAD_SIGNATURE"
    assert row["new_canonical_failure_code"] == "F0_PARSE"
    assert row["label_drift_category"] == "cross_category"
    assert row["cross_category_label_drift"] is True
    assert row["drift_reason"] == "cross_category_label_drift"


def test_revalidation_refuses_to_mutate_input_or_overwrite_output(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(input_path, [_legacy_row()])
    output_path.write_text("existing\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must differ from input"):
        revalidate_baseline_aligned_pipeline(input_path, input_path)

    with pytest.raises(FileExistsError, match="diagnostic output already exists"):
        revalidate_baseline_aligned_pipeline(input_path, output_path)


def test_revalidation_failure_does_not_publish_partial_output(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(
        input_path,
        [
            _legacy_row(generation_seed=0),
            _legacy_row(generation_seed=1, source="import triton\n# row 1\n"),
        ],
    )

    def failing_c1_evaluator(row):  # type: ignore[no-untyped-def]
        if row.generation_seed == 1:
            raise RuntimeError("simulated evaluator failure")
        return _entrypoint_result(
            compile_success=False,
            compile_error_type="SignatureError",
            canonical_failure_code="F0_BAD_SIGNATURE",
        )

    with pytest.raises(RuntimeError, match="simulated evaluator failure"):
        revalidate_baseline_aligned_pipeline(
            input_path,
            output_path,
            c1_evaluator=failing_c1_evaluator,
            c2_evaluator=_mock_evaluator(
                {
                    0: _entrypoint_result(
                        compile_success=False,
                        compile_error_type="SignatureError",
                        canonical_failure_code="F0_BAD_SIGNATURE",
                    )
                }
            ),
        )

    assert not output_path.exists()
    assert list(tmp_path.glob(".diagnostic.jsonl.*.tmp")) == []

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        c1_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
                1: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
            }
        ),
        c2_evaluator=_mock_evaluator(
            {
                0: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
                1: _entrypoint_result(
                    compile_success=False,
                    compile_error_type="SignatureError",
                    canonical_failure_code="F0_BAD_SIGNATURE",
                ),
            }
        ),
    )
    assert summary["total_rows"] == 2
    assert output_path.exists()


def test_publish_temp_file_no_clobber_refuses_existing_output(
    tmp_path: Path,
) -> None:
    temp_path = tmp_path / ".diagnostic.jsonl.tmp"
    output_path = tmp_path / "diagnostic.jsonl"
    temp_path.write_text("new diagnostic\n", encoding="utf-8")
    output_path.write_text("existing diagnostic\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _publish_temp_file_no_clobber(temp_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "existing diagnostic\n"
    assert temp_path.read_text(encoding="utf-8") == "new diagnostic\n"


def test_publish_temp_file_no_clobber_removes_temp_after_success(
    tmp_path: Path,
) -> None:
    temp_path = tmp_path / ".diagnostic.jsonl.tmp"
    output_path = tmp_path / "diagnostic.jsonl"
    temp_path.write_text("diagnostic\n", encoding="utf-8")

    _publish_temp_file_no_clobber(temp_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "diagnostic\n"
    assert not temp_path.exists()


def _mock_evaluator(
    results_by_seed: dict[int, BaselineEntrypointEvaluation],
):
    def evaluate(row):  # type: ignore[no-untyped-def]
        assert row.generation_seed is not None
        return results_by_seed[row.generation_seed]

    return evaluate


def _entrypoint_result(
    *,
    compile_success: bool,
    compile_error_type: str | None = None,
    canonical_failure_code: str | None = None,
    compile_results_by_dtype: dict[str, bool] | None = None,
    n_shapes_tested: int | None = None,
) -> BaselineEntrypointEvaluation:
    return BaselineEntrypointEvaluation(
        compile_success=compile_success,
        compile_error_type=compile_error_type,
        compile_error_msg=None if compile_success else "mock compile failure",
        canonical_failure_code=canonical_failure_code,
        compile_results_by_dtype=(
            compile_results_by_dtype
            if compile_results_by_dtype is not None
            else {
                "fp32": compile_success,
                "fp16": compile_success,
                "bf16": compile_success,
            }
        ),
        n_shapes_tested=(
            n_shapes_tested
            if n_shapes_tested is not None
            else 4 if compile_success else 0
        ),
    )


def _legacy_row(**overrides) -> dict[str, object]:
    source = str(overrides.pop("source", "import triton\n# test row\n"))
    compile_success = bool(overrides.get("compile_success", False))
    defaults: dict[str, object] = {
        "source": source,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "grammar_active": False,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "compile_success": compile_success,
        "compile_results_by_dtype": {
            "fp32": compile_success,
            "fp16": compile_success,
            "bf16": compile_success,
        },
        "compile_error_type": "SignatureError" if not compile_success else None,
        "compile_error_msg": "signature mismatch" if not compile_success else None,
        "masked_token_rate": None,
        "unique_solution_hash": compute_unique_solution_hash(source),
        "n_shapes_tested": 0,
        "generation_seed": 0,
        "temperature": 0.2,
        "run_id": "run-0",
        "timestamp_utc": "2026-05-10T00:00:00+00:00",
    }
    defaults.update(overrides)
    return defaults


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
