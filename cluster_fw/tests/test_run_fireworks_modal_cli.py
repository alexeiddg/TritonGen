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
