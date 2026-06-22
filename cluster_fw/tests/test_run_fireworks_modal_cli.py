from __future__ import annotations

import json
from pathlib import Path

from cluster_fw.experiments.run_fireworks_modal import run_fireworks_l2b
from cluster_fw.planning.l2b_smoke import FIREWORKS_GBNF_N20_RUN_TIER
from cluster_fw.providers.fireworks import FireworksGenerationRequest


def test_run_fireworks_l2b_writes_rows_with_fake_generation(tmp_path: Path) -> None:
    output = tmp_path / "fw_a.jsonl"
    calls: list[FireworksGenerationRequest] = []
    compile_calls: list[dict[str, object]] = []

    def fake_generation(request: FireworksGenerationRequest) -> dict[str, object]:
        calls.append(request)
        return {
            "provider": "fireworks",
            "provider_api": request.provider_api,
            "provider_model_id": request.model_id,
            "provider_model_snapshot": request.model_id,
            "model_slot": request.model_slot,
            "source": "import torch\nimport triton\nimport triton.language as tl\n",
            "finish_reason": "stop",
            "provider_response_id": "fake_response",
            "provider_request_id": None,
            "input_tokens": 10,
            "output_tokens": 20,
            "reasoning_tokens": None,
            "cached_input_tokens": None,
            "prompt_sha256": request.prompt_sha256,
            "response_sha256": "fake_response_hash",
            "source_sha256": "fake_source_hash",
            "raw_source_sha256": "fake_raw_source_hash",
            "source_extraction_method": "raw_text",
            "source_extraction_warning": None,
            "provider_error_type": None,
            "provider_error_msg": None,
            "raw_response_shape_version": "fixture_v1",
        }

    result = run_fireworks_l2b(
        output=output,
        model_slots=("FW-A",),
        condition_selector="grammar_off__c_off__p_off",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        provider_api="responses",
        generation_adapter=fake_generation,
        compile_adapter=lambda **kwargs: compile_calls.append(kwargs)
        or {
            "compile_success": True,
            "compile_error_type": None,
            "compile_error_msg": None,
            "failure_code": None,
            "compile_results_by_dtype": {"fp32": True},
            "n_shapes_tested": 1,
        },
    )

    assert len(calls) == 1
    assert compile_calls == [
        {
            "source": "import torch\nimport triton\nimport triton.language as tl\n",
            "kernel_class": "elementwise",
            "kernel_name": "relu",
            "factor_cell": "none",
            "run_id": result.run_id,
        }
    ]
    assert result.rows_written == 1
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["model_slot"] == "FW-A"
    assert row["condition_id"] == "grammar_off__c_off__p_off"
    assert row["kernel_class"] == "elementwise"
    assert row["kernel_name"] == "relu"
    assert row["dtype"] == "fp32"
    assert row["generation_seed"] == 0
    assert row["provider"] == "fireworks"
    assert row["compile_success"] is True
    assert row["compile_results_by_dtype"] == {"fp32": True}
    assert row["source"].startswith("import torch")
    assert row["raw_source_sha256"] == "fake_raw_source_hash"
    assert row["source_extraction_method"] == "raw_text"
    assert row["source_extraction_warning"] is None


def test_run_fireworks_l2b_maps_cp_cells_for_cluster1_compile_harness(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fw_a_cp.jsonl"
    compile_calls: list[dict[str, object]] = []

    def fake_generation(request: FireworksGenerationRequest) -> dict[str, object]:
        return {
            "provider": "fireworks",
            "provider_api": request.provider_api,
            "provider_model_id": request.model_id,
            "provider_model_snapshot": request.model_id,
            "model_slot": request.model_slot,
            "source": "import torch\nimport triton\nimport triton.language as tl\n",
            "prompt_sha256": request.prompt_sha256,
            "response_sha256": "fake_response_hash",
            "source_sha256": "fake_source_hash",
            "raw_source_sha256": "fake_raw_source_hash",
            "source_extraction_method": "raw_text",
            "source_extraction_warning": None,
        }

    run_fireworks_l2b(
        output=output,
        model_slots=("FW-A",),
        condition_selector="grammar_off__c_on__p_off",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        generation_adapter=fake_generation,
        compile_adapter=lambda **kwargs: compile_calls.append(kwargs)
        or {
            "compile_success": False,
            "compile_error_type": None,
            "compile_error_msg": None,
            "failure_code": None,
            "compile_results_by_dtype": {"fp32": False},
            "n_shapes_tested": 0,
        },
    )
    run_fireworks_l2b(
        output=output,
        model_slots=("FW-A",),
        condition_selector="task_agnostic__c_on__p_off",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        generation_adapter=fake_generation,
        compile_adapter=lambda **kwargs: compile_calls.append(kwargs)
        or {
            "compile_success": False,
            "compile_error_type": None,
            "compile_error_msg": None,
            "failure_code": None,
            "compile_results_by_dtype": {"fp32": False},
            "n_shapes_tested": 0,
        },
    )

    assert [call["factor_cell"] for call in compile_calls] == ["none", "G"]


def test_run_fireworks_l2b_marks_n20_run_tier(tmp_path: Path) -> None:
    output = tmp_path / "fw_b_n20.jsonl"

    def fake_generation(request: FireworksGenerationRequest) -> dict[str, object]:
        return {
            "provider": "fireworks",
            "provider_api": request.provider_api,
            "provider_model_id": request.model_id,
            "provider_model_snapshot": request.model_id,
            "model_slot": request.model_slot,
            "source": "import torch\nimport triton\nimport triton.language as tl\n",
            "prompt_sha256": request.prompt_sha256,
            "response_sha256": "fake_response_hash",
            "source_sha256": "fake_source_hash",
            "raw_source_sha256": "fake_raw_source_hash",
            "source_extraction_method": "raw_text",
            "source_extraction_warning": None,
        }

    run_fireworks_l2b(
        output=output,
        model_slots=("FW-B",),
        condition_selector="wave_1",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        provider_api="chat_completions",
        run_tier=FIREWORKS_GBNF_N20_RUN_TIER,
        generation_adapter=fake_generation,
    )

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 3
    assert {row["run_tier"] for row in rows} == {FIREWORKS_GBNF_N20_RUN_TIER}


def test_run_fireworks_l2b_can_record_functional_correctness_fields(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fw_functional.jsonl"
    correctness_calls: list[dict[str, object]] = []

    def fake_generation(request: FireworksGenerationRequest) -> dict[str, object]:
        return _fake_provider_payload(request, source="initial source")

    def fake_correctness(**kwargs: object) -> dict[str, object]:
        correctness_calls.append(kwargs)
        return {
            "functional_success": True,
            "repair_set_success": True,
            "eval_set_success": True,
            "failure_code": None,
            "correctness_error": None,
            "feedback": None,
            "max_abs_diff": 0.0,
            "max_rel_diff": 0.0,
            "level_reached": 2,
            "compile_success": True,
            "compile_error": None,
            "compile_error_type": None,
            "num_repair_shapes": 5,
            "num_eval_shapes": 10,
            "num_test_shapes": 15,
            "shapes_passed": 15,
            "repair_shapes_passed": 5,
            "eval_shapes_passed": 10,
        }

    run_fireworks_l2b(
        output=output,
        model_slots=("FW-A",),
        condition_selector="grammar_off__c_off__p_off",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        generation_adapter=fake_generation,
        correctness_adapter=fake_correctness,
    )

    assert len(correctness_calls) == 1
    assert correctness_calls[0]["source"] == "initial source"
    row = json.loads(output.read_text().splitlines()[0])
    assert row["compile_success"] is True
    assert row["functional_success"] is True
    assert row["failure_code"] is None
    assert row["max_abs_diff"] == 0.0
    assert row["num_test_shapes"] == 15
    assert row["c_repair_status"] is None


def test_run_fireworks_l2b_runs_c_repair_loop_for_f2_failures(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fw_repair.jsonl"
    prompts: list[str] = []
    evaluated_sources: list[str] = []

    def fake_generation(request: FireworksGenerationRequest) -> dict[str, object]:
        prompts.append(request.prompt)
        source = "bad source" if len(prompts) == 1 else "fixed source"
        return _fake_provider_payload(request, source=source)

    def fake_correctness(**kwargs: object) -> dict[str, object]:
        source = str(kwargs["source"])
        evaluated_sources.append(source)
        if source == "bad source":
            return {
                "functional_success": False,
                "repair_set_success": False,
                "eval_set_success": False,
                "failure_code": "F2_NUMERIC_LARGE",
                "correctness_error": "max_abs_diff=1.0",
                "feedback": "numeric mismatch",
                "max_abs_diff": 1.0,
                "max_rel_diff": 1.0,
                "level_reached": 2,
                "compile_success": True,
                "compile_error": None,
                "compile_error_type": None,
            }
        return {
            "functional_success": True,
            "repair_set_success": True,
            "eval_set_success": True,
            "failure_code": None,
            "correctness_error": None,
            "feedback": None,
            "max_abs_diff": 0.0,
            "max_rel_diff": 0.0,
            "level_reached": 2,
            "compile_success": True,
            "compile_error": None,
            "compile_error_type": None,
        }

    run_fireworks_l2b(
        output=output,
        model_slots=("FW-A",),
        condition_selector="grammar_off__c_on__p_off",
        kernel_classes=("elementwise",),
        dtypes=("fp32",),
        n=1,
        generation_adapter=fake_generation,
        correctness_adapter=fake_correctness,
        repair_budget=1,
    )

    assert evaluated_sources == ["bad source", "fixed source"]
    assert len(prompts) == 2
    assert "Failure code:" in prompts[1]
    assert "F2_NUMERIC_LARGE" in prompts[1]
    row = json.loads(output.read_text().splitlines()[0])
    assert row["source"] == "fixed source"
    assert row["functional_success"] is True
    assert row["c_repair_status"] == "success"
    assert row["c_repair_attempts_executed"] == 2
    assert row["c_repair_successful_attempt_index"] == 1
    assert row["c_repair_attempts"][0]["failure_code"] == "F2_NUMERIC_LARGE"


def _fake_provider_payload(
    request: FireworksGenerationRequest,
    *,
    source: str,
) -> dict[str, object]:
    return {
        "provider": "fireworks",
        "provider_api": request.provider_api,
        "provider_model_id": request.model_id,
        "provider_model_snapshot": request.model_id,
        "model_slot": request.model_slot,
        "source": source,
        "finish_reason": "stop",
        "provider_response_id": "fake_response",
        "provider_request_id": None,
        "input_tokens": 10,
        "output_tokens": 20,
        "reasoning_tokens": None,
        "cached_input_tokens": None,
        "prompt_sha256": request.prompt_sha256,
        "response_sha256": "fake_response_hash",
        "source_sha256": "fake_source_hash",
        "raw_source_sha256": "fake_raw_source_hash",
        "source_extraction_method": "raw_text",
        "source_extraction_warning": None,
        "provider_error_type": None,
        "provider_error_msg": None,
        "raw_response_shape_version": "fixture_v1",
    }
