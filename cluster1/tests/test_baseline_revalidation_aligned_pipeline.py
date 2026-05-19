"""Tests for the local baseline revalidation diagnostic utility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cluster1.diagnostics.revalidate_baseline_aligned_pipeline as revalidation_module
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


def test_revalidation_pair_evaluator_records_modal_context(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(input_path, [_legacy_row()])
    modal_context = {
        "function_call_id": "fc-test",
        "input_id": "in-test",
        "modal_app_name": "tritongen-gpu-harness",
        "modal_eval_gpu": "L4",
        "modal_image_sha": "unknown",
        "modal_image_provenance_sha256": "a" * 64,
        "modal_image_provenance_components": {"schema": "test"},
    }

    def pair_evaluator(row_index, raw_row, row):  # type: ignore[no-untyped-def]
        assert row_index == 0
        assert raw_row["generation_seed"] == 0
        assert row.generation_seed == 0
        result = _entrypoint_result(
            compile_success=False,
            compile_error_type="SignatureError",
            canonical_failure_code="F0_BAD_SIGNATURE",
            modal_context=modal_context,
        )
        return result, result

    summary = revalidate_baseline_aligned_pipeline(
        input_path,
        output_path,
        pair_evaluator=pair_evaluator,
    )

    row = _read_jsonl(output_path)[0]
    assert summary["total_rows"] == 1
    assert row["entrypoint_agreement"] is True
    assert row["c1_entrypoint_modal_context"] == modal_context
    assert row["c2_entrypoint_modal_context"] == modal_context


def test_modal_revalidation_context_records_image_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "MODAL_IMAGE_SHA",
        "MODAL_IMAGE_DIGEST",
        "MODAL_IMAGE_ID",
        "MODAL_CONTAINER_IMAGE_ID",
        "MODAL_IMAGE_TAG",
    ):
        monkeypatch.delenv(name, raising=False)

    context = revalidation_module._modal_revalidation_context(
        call_id="fc-test",
        input_id="in-test",
    )

    assert context["function_call_id"] == "fc-test"
    assert context["input_id"] == "in-test"
    assert context["modal_app_name"] == "tritongen-gpu-harness"
    assert context["modal_eval_gpu"] == "L4"
    assert isinstance(context["modal_image_provenance_sha256"], str)
    assert len(context["modal_image_provenance_sha256"]) == 64
    assert context["modal_image_sha"] == context["modal_image_provenance_sha256"]
    assert context["modal_image_provenance_components"]["schema"] == (
        "modal_image_fallback_provenance.v1"
    )
    assert context["modal_image_provenance_components"]["extra"] == {
        "runtime": "phase4_baseline_revalidation",
        "modal_eval_gpu": "L4",
    }


def test_modal_parent_timeout_exceeds_two_child_timeouts() -> None:
    assert revalidation_module._MODAL_ROW_TIMEOUT_S > (
        2 * revalidation_module._ENTRYPOINT_CHILD_TIMEOUT_S
    )


def test_modal_entrypoint_fails_after_writing_summary_on_entrypoint_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = {
        "diagnostic_name": "baseline_revalidation_aligned_pipeline",
        "diagnostic_only": True,
        "output_path": "outputs/cluster1/diagnostics/diagnostic.jsonl",
        "entrypoint_disagreement_count": 1,
    }
    monkeypatch.setattr(
        revalidation_module,
        "revalidate_baseline_aligned_pipeline_modal",
        lambda _input, _output: summary,
    )

    with pytest.raises(RuntimeError, match="failed C1/C2 entrypoint identity"):
        revalidation_module.modal_revalidate_baseline(
            input="baseline.jsonl",
            output="diagnostic.jsonl",
        )

    printed = capsys.readouterr().out
    assert '"entrypoint_disagreement_count": 1' in printed
    assert summary["output_path"] in printed


def test_revalidation_rejects_mixed_pair_and_single_evaluators(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "baseline.jsonl"
    output_path = tmp_path / "diagnostic.jsonl"
    _write_jsonl(input_path, [_legacy_row()])

    with pytest.raises(ValueError, match="pair_evaluator cannot be combined"):
        revalidate_baseline_aligned_pipeline(
            input_path,
            output_path,
            c1_evaluator=_mock_evaluator({0: _entrypoint_result(compile_success=True)}),
            pair_evaluator=lambda _index, _raw, _row: (  # noqa: E731
                _entrypoint_result(compile_success=True),
                _entrypoint_result(compile_success=True),
            ),
        )


def test_entrypoint_child_main_writes_result_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(
        json.dumps({"row_index": 0, "raw_row": _legacy_row()}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        revalidation_module,
        "evaluate_row_via_c1_entrypoint",
        lambda _row: _entrypoint_result(
            compile_success=False,
            compile_error_type="SignatureError",
            canonical_failure_code="F0_BAD_SIGNATURE",
        ),
    )

    status = revalidation_module._entrypoint_eval_child_main(
        [
            "--entrypoint",
            "c1",
            "--request",
            str(request_path),
            "--result",
            str(result_path),
        ]
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert status == 0
    assert payload["compile_success"] is False
    assert payload["compile_error_type"] == "SignatureError"
    assert payload["canonical_failure_code"] == "F0_BAD_SIGNATURE"


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


def test_revalidation_treats_legacy_syntax_wrapper_as_expected_parse_mapping(
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
                compile_error_msg=(
                    "SignatureError: syntax error in generated source: "
                    "invalid syntax (tmp.py, line 19)"
                ),
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
    assert summary["cross_category_label_drift_count"] == 0
    assert summary["expected_legacy_to_canonical_mapping_count"] == 1
    assert row["agreement"] is True
    assert row["canonical_label_agreement"] is True
    assert row["original_canonical_failure_code"] == "F0_PARSE"
    assert row["new_canonical_failure_code"] == "F0_PARSE"
    assert row["label_drift_category"] == "none"
    assert row["cross_category_label_drift"] is False
    assert row["drift_reason"] == "expected_legacy_to_canonical_mapping"


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
    modal_context: dict[str, object] | None = None,
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
        modal_context=modal_context,
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
