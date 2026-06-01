from __future__ import annotations

import ast
import importlib
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from cluster2.constants import (
    GENERATED_SOURCE_CLASS,
    generation_mode_for_condition,
)


def test_adapter_rejects_non_cluster3_condition() -> None:
    runner = _runner_module()
    for condition in ("C", "none", "G", "G+C"):
        request = runner.Cluster3CorrectnessRequest(
            identity=_identity(condition),
            source=_source(),
        )
        with pytest.raises(ValueError):
            runner.run_cluster3_correctness(request, modal_call=lambda _: {})


def test_adapter_translates_p_to_c_for_inner_eval() -> None:
    _assert_translation("P", "C")


def test_adapter_translates_g_plus_p_to_g_plus_c_for_inner_eval() -> None:
    _assert_translation("G+P", "G+C")


def test_adapter_translates_c_plus_p_to_c() -> None:
    _assert_translation("C+P", "C")


def test_adapter_translates_g_plus_c_plus_p_to_g_plus_c() -> None:
    _assert_translation("G+C+P", "G+C")


def test_adapter_does_not_translate_to_replay_controls() -> None:
    observed: list[str] = []

    for c3_condition in ("P", "G+P", "C+P", "G+C+P"):
        request = _request(c3_condition)

        def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
            observed.append(req_dict["identity"]["condition"])
            return _payload(req_dict["identity"], status="failed")

        _runner_module().run_cluster3_correctness(request, modal_call=modal_call)

    assert set(observed) == {"C", "G+C"}
    assert "none" not in observed
    assert "G" not in observed


def test_adapter_preserves_canonical_failure_code() -> None:
    request = _request("P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        return _payload(req_dict["identity"], failure_code="F1_COMPILE")

    payload = _runner_module().run_cluster3_correctness(request, modal_call=modal_call)

    assert payload["correctness_result"]["failure_code"] == "F1_COMPILE"


def test_adapter_restamps_nested_correctness_result_identity() -> None:
    request = _request("P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(req_dict["identity"], failure_code="F1_COMPILE")
        assert payload["correctness_result"]["identity"]["condition"] == "C"
        return payload

    payload = _runner_module().run_cluster3_correctness(request, modal_call=modal_call)

    assert payload["identity"]["condition"] == "P"
    assert payload["correctness_result"]["identity"]["condition"] == "P"


def test_adapter_post_restamp_self_check_raises_on_mismatch() -> None:
    request = _request("P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(req_dict["identity"], failure_code="F1_COMPILE")
        payload["correctness_result"]["identity"] = object()
        return payload

    with pytest.raises(ValueError, match="identity condition mismatch"):
        _runner_module().run_cluster3_correctness(request, modal_call=modal_call)


def test_cluster3_correctness_adapter_allows_infra_payload_without_correctness_result() -> None:
    request = _request("G+P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        return _infra_payload(req_dict["identity"])

    payload = _runner_module().run_cluster3_correctness(request, modal_call=modal_call)

    assert payload["surface"] == "c3_remote_correctness"
    assert payload["identity"]["condition"] == "G+P"
    assert payload["source_identity"]["condition"] == "G+P"
    assert payload["eval_identity"]["condition"] == "G+P"
    assert "correctness_result" not in payload


def test_cluster3_correctness_adapter_restamps_success_payload_identity() -> None:
    request = _request("G+C+P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        return _payload(req_dict["identity"], status="passed", failure_code=None)

    payload = _runner_module().run_cluster3_correctness(request, modal_call=modal_call)

    assert payload["condition"] == "G+C+P"
    assert payload["surface"] == "c3_remote_correctness"
    assert payload["identity"]["condition"] == "G+C+P"
    assert payload["correctness_result"]["identity"]["condition"] == "G+C+P"


def test_cluster3_correctness_adapter_preserves_f3_eval_pipeline_payload() -> None:
    request = _request("C+P")

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        payload = _infra_payload(req_dict["identity"])
        payload["infrastructure_failure"]["error_type"] = "SubprocessResultSchemaError"
        return payload

    payload = _runner_module().run_cluster3_correctness(request, modal_call=modal_call)
    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        payload,
        _identity("C+P"),
    )

    assert result["failure_code"] == "F3_EVAL_PIPELINE"
    assert "SubprocessResultSchemaError" in result["f3_reason"]


def test_adapter_does_not_import_modal_at_module_level() -> None:
    sys.modules.pop("cluster3.modal.correctness_runner", None)
    sys.modules.pop("modal", None)

    importlib.import_module("cluster3.modal.correctness_runner")

    assert "modal" not in sys.modules


def test_adapter_uses_no_new_modal_function() -> None:
    module = _runner_module()
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    decorated_functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.decorator_list
    ]
    assert decorated_functions == []


def test_adapter_default_modal_call_imports_c2_function_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner_module()
    fake_call = _FakeRemoteCall()
    fake_module = types.ModuleType("cluster2.modal.correctness")
    fake_module.remote_c2_correctness = fake_call
    monkeypatch.setitem(sys.modules, "cluster2.modal.correctness", fake_module)

    payload = runner.run_cluster3_correctness(_request("P"))

    assert fake_call.calls == 1
    assert fake_call.last_request["identity"]["condition"] == "C"
    assert payload["identity"]["condition"] == "P"


def test_adapter_has_no_cluster3_modal_image_or_app_definitions() -> None:
    module = _runner_module()
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attrs = {
        ("modal", "App"),
        ("modal", "Image"),
        ("modal", "Volume"),
        ("modal", "Secret"),
        ("modal", "Queue"),
        ("app", "function"),
        ("app", "cls"),
        ("app", "local_entrypoint"),
    }
    forbidden_calls = {"spawn", "spawn_map", "map"}
    source_packager = "add_local_python_" + "source"

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                assert (node.value.id, node.attr) not in forbidden_attrs
            assert node.attr not in forbidden_calls
            assert node.attr != source_packager

    assert "FunctionCall" + ".get" not in source
    assert source_packager not in source


def test_extract_cluster3_success_payload() -> None:
    identity = _identity("P")
    payload = _payload(identity, status="passed", failure_code=None)
    payload["condition"] = "P"
    payload["surface"] = "c3_remote_correctness"
    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        payload,
        identity,
    )

    assert result["identity"]["condition"] == "P"
    assert result["failure_code"] is None
    assert result["functional_success"] is True
    assert result["compile_success"] is True


def test_extract_cluster3_f1_compile_payload_with_error_excerpt() -> None:
    identity = _identity("P")
    payload = _payload(identity, failure_code="F1_COMPILE")
    payload["correctness_result"]["level_reached"] = 1
    payload["correctness_result"]["compile_success"] = False
    payload["correctness_result"]["compile_error_type"] = "CompilationError"
    payload["correctness_result"]["compile_error"] = "compile exploded"

    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        payload,
        identity,
    )

    assert result["failure_code"] == "F1_COMPILE"
    assert result["compile_error_type"] == "CompilationError"
    assert result["compile_error_excerpt"] == "compile exploded"


def test_extract_cluster3_f0_payload_with_compile_success_none_derives_false() -> None:
    identity = _identity("P")
    payload = _payload(identity, failure_code="F0_PARSE")
    payload["correctness_result"]["level_reached"] = 0
    payload["correctness_result"]["parse_success"] = False
    payload["correctness_result"]["signature_valid"] = None
    payload["correctness_result"]["compile_success"] = None

    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        payload,
        identity,
    )

    assert result["failure_code"] == "F0_PARSE"
    assert result["compile_success"] is False


def test_extract_cluster3_f3_malformed_payload_synthesizes_eval_pipeline() -> None:
    identity = _identity("C+P")
    payload = _infra_payload(identity)
    payload["surface"] = "c3_remote_correctness"

    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        payload,
        identity,
    )

    assert result["failure_code"] == "F3_EVAL_PIPELINE"
    assert result["level_reached"] == 0
    assert result["compile_success"] is False
    assert result["functional_success"] is False
    assert "source = " not in result["f3_reason"]


def test_extract_cluster3_rejects_unrecognized_payload_shape_with_f3_not_crash() -> None:
    result = _extractor_module().extract_or_synthesize_cluster3_correctness_result_dict(
        ["unexpected"],
        _identity("G+C+P"),
    )

    assert result["failure_code"] == "F3_EVAL_PIPELINE"
    assert result["level_reached"] == 0
    assert "payload_type=list" in result["f3_reason"]


def _assert_translation(c3_condition: str, c2_condition: str) -> None:
    calls: list[dict[str, Any]] = []
    request = _request(c3_condition)

    def modal_call(req_dict: dict[str, Any]) -> dict[str, Any]:
        calls.append(req_dict)
        return _payload(req_dict["identity"], status="failed")

    payload = _runner_module().run_cluster3_correctness(
        request,
        modal_call=modal_call,
    )

    inner_identity = calls[0]["identity"]
    assert inner_identity["condition"] == c2_condition
    assert inner_identity["condition"] not in {"none", "G"}
    assert inner_identity["source_class"] == GENERATED_SOURCE_CLASS
    assert inner_identity["generation_mode"] == generation_mode_for_condition(
        c2_condition
    )
    assert payload["condition"] == c3_condition
    assert payload["surface"] == "c3_remote_correctness"
    assert payload["identity"]["condition"] == c3_condition


def _runner_module() -> Any:
    return importlib.import_module("cluster3.modal.correctness_runner")


def _extractor_module() -> Any:
    return importlib.import_module("cluster3.modal.result_extraction")


def _request(condition: str) -> Any:
    return _runner_module().Cluster3CorrectnessRequest(
        identity=_identity(condition),
        source=_source(),
    )


def _identity(condition: str) -> dict[str, Any]:
    if condition in {"G", "G+P", "G+C", "G+C+P"}:
        generation_mode = generation_mode_for_condition("G+C")
    else:
        generation_mode = generation_mode_for_condition("C")
    return {
        "run_id": "phase4-test",
        "condition": condition,
        "source_class": GENERATED_SOURCE_CLASS,
        "generation_mode": generation_mode,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "sample_index": 7,
        "base_seed": 7,
        "attempt_index": 0,
    }


def _source() -> str:
    return "def relu(x):\n    return x\n"


def _payload(
    identity: dict[str, Any],
    *,
    status: str = "failed",
    failure_code: str | None = "F1_COMPILE",
) -> dict[str, Any]:
    success = status == "passed"
    level_reached = 2 if success or failure_code != "F1_COMPILE" else 1
    return {
        "schema_version": 1,
        "surface": "c2_remote_correctness",
        "condition": identity["condition"],
        "correctness_status": status,
        "modal_eval_gpu": "L4",
        "eval_pipeline_hash_class": "shared_eval_pipeline",
        "external_pin_class": "python_package_environment",
        "identity": dict(identity),
        "source_identity": {
            "source_sha256": "a" * 64,
            "condition": identity["condition"],
            "source_class": identity["source_class"],
            "generation_mode": identity["generation_mode"],
            "kernel_class": identity["kernel_class"],
            "kernel_name": identity["kernel_name"],
            "dtype": identity["dtype"],
            "sample_index": identity["sample_index"],
            "base_seed": identity["base_seed"],
            "attempt_index": identity["attempt_index"],
        },
        "eval_identity": {
            "condition": identity["condition"],
            "level": "level2_correctness" if level_reached >= 2 else "level1_compile",
            "pipeline": "shared.eval.pipeline.run_eval_pipeline",
            "device": "cuda",
            "modal_eval_gpu": "L4",
            "kernel_class": identity["kernel_class"],
            "kernel_name": identity["kernel_name"],
            "dtype": identity["dtype"],
            "base_seed": identity["base_seed"],
            "attempt_index": identity["attempt_index"],
        },
        "correctness_result": {
            "identity": dict(identity),
            "functional_success": success,
            "repair_set_success": success,
            "eval_set_success": success,
            "level_reached": level_reached,
            "parse_success": True,
            "parse_error": None,
            "signature_valid": True,
            "signature_error": None,
            "compile_success": success if failure_code is None else False,
            "compile_error": None,
            "compile_error_type": None,
            "failure_code": failure_code,
            "correctness_error": None,
            "feedback": None,
            "num_repair_shapes": 1 if level_reached >= 2 else 0,
            "num_eval_shapes": 1 if level_reached >= 2 else 0,
            "num_test_shapes": 2 if level_reached >= 2 else 0,
            "shapes_passed": 2 if success else 0,
            "repair_shapes_passed": 1 if success else 0,
            "eval_shapes_passed": 1 if success else 0,
            "max_abs_diff": None,
            "max_rel_diff": None,
        },
        "eval_pipeline_hashes": {"pipeline": "hash"},
        "external_pins": {"python": "version"},
    }


def _infra_payload(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "surface": "c2_remote_correctness",
        "condition": identity["condition"],
        "correctness_status": "INFRA_FAILURE",
        "modal_eval_gpu": "L4",
        "eval_pipeline_hash_class": "shared_eval_pipeline",
        "external_pin_class": "python_package_environment",
        "identity": dict(identity),
        "source_identity": {
            "source_sha256": "a" * 64,
            "condition": identity["condition"],
            "source_class": identity["source_class"],
            "generation_mode": identity["generation_mode"],
            "kernel_class": identity["kernel_class"],
            "kernel_name": identity["kernel_name"],
            "dtype": identity["dtype"],
            "sample_index": identity["sample_index"],
            "base_seed": identity["base_seed"],
            "attempt_index": identity["attempt_index"],
        },
        "eval_identity": {
            "condition": identity["condition"],
            "level": "level2_correctness",
            "pipeline": "shared.eval.pipeline.run_eval_pipeline",
            "device": "cuda",
            "modal_eval_gpu": "L4",
            "kernel_class": identity["kernel_class"],
            "kernel_name": identity["kernel_name"],
            "dtype": identity["dtype"],
            "base_seed": identity["base_seed"],
            "attempt_index": identity["attempt_index"],
        },
        "infrastructure_failure": {
            "error_type": "TimeoutError",
            "error_msg": "public timeout",
            "stdout": "",
            "stderr": "",
            "traceback": None,
        },
        "eval_pipeline_hashes": {"pipeline": "hash"},
        "external_pins": {"python": "version"},
    }


class _FakeRemoteCall:
    def __init__(self) -> None:
        self.calls = 0
        self.last_request: dict[str, Any] | None = None

    def remote(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        self.last_request = request
        return _payload(request["identity"], status="failed")
