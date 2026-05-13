"""Phase 5 tests for isolated Cluster 2 Modal schemas."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cluster2.modal.schemas import (
    FORBIDDEN_REQUEST_RESULT_FIELD_NAMES,
    KERNEL_NAME_BY_CLASS,
    EvalIdentity,
    RemoteC2GenerationRequest,
    RemoteC2GenerationResult,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "cluster2" / "modal" / "schemas.py"
SHARED_MODAL_SCHEMA_PATH = REPO_ROOT / "shared" / "modal_harness" / "schemas.py"
FORBIDDEN_IMPORT_MODULES = (
    "modal",
    "torch",
    "triton",
    "transformers",
    "xgrammar",
    "autoawq",
    "cluster1",
    "shared.modal_harness",
    "shared.eval.levels",
    "cluster2.modal.generation",
    "cluster2.modal.correctness",
    "cluster2.modal.correctness_runner",
)


def test_generation_request_accepts_c_condition() -> None:
    request = _generation_request("C")

    assert request.identity.condition == "C"
    assert request.identity.source_class == "generated_row"
    assert request.identity.generation_mode == "new_c2_generation"


def test_generation_request_accepts_g_plus_c_condition() -> None:
    request = _generation_request("G+C")

    assert request.identity.condition == "G+C"
    assert request.identity.source_class == "generated_row"
    assert request.identity.generation_mode == "new_c2_generation_with_G_adapter"


@pytest.mark.parametrize("condition", ["none", "G"])
def test_generation_request_rejects_replay_controls(condition: str) -> None:
    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        _generation_request(condition)


@pytest.mark.parametrize("condition", ["P", "G+P", "C+P", "G+C+P"])
def test_generation_request_rejects_p_modes(condition: str) -> None:
    with pytest.raises(ValueError, match="unsupported Cluster 2 condition"):
        _generation_request(condition)


@pytest.mark.parametrize(
    ("condition", "generation_mode"),
    [
        ("C", "replay_control"),
        ("G+C", "new_c2_generation"),
        ("none", "new_c2_generation"),
        ("G", "new_c2_generation_with_G_adapter"),
    ],
)
def test_eval_identity_rejects_invalid_generation_modes(
    condition: str,
    generation_mode: str,
) -> None:
    payload = _identity_payload(condition, generation_mode=generation_mode)

    with pytest.raises(ValueError, match="requires generation_mode"):
        EvalIdentity(**payload)


@pytest.mark.parametrize("kernel_name", ["gemm", "layernorm"])
def test_eval_identity_rejects_kernel_name_mismatch(kernel_name: str) -> None:
    payload = _identity_payload("C", kernel_name=kernel_name)

    with pytest.raises(ValueError, match="requires kernel_name 'relu'"):
        EvalIdentity(**payload)


def test_schema_kernel_mapping_matches_locked_shape_metadata() -> None:
    from shared.eval.correctness_shapes import iter_shape_metadata

    assert KERNEL_NAME_BY_CLASS == {
        metadata.kernel_class: metadata.kernel_name
        for metadata in iter_shape_metadata()
    }


def test_generation_request_serialization_roundtrip_is_deterministic() -> None:
    request = _generation_request("G+C", generation_seed=17)

    payload = request.model_dump()
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    rebuilt = RemoteC2GenerationRequest(**json.loads(rendered))

    assert rebuilt == request
    assert rebuilt.model_dump() == payload
    rerendered = json.dumps(
        rebuilt.model_dump(),
        sort_keys=True,
        separators=(",", ":"),
    )
    assert rerendered == rendered


def test_correctness_schemas_preserve_replay_control_identity() -> None:
    identity = _identity("none")
    request = RemoteCorrectnessRequest(
        identity=identity,
        source="def relu(x):\n    return x\n",
    )
    result = RemoteCorrectnessResult(
        identity=identity,
        functional_success=True,
        repair_set_success=True,
        eval_set_success=True,
        num_repair_shapes=2,
        num_eval_shapes=3,
        num_test_shapes=5,
        shapes_passed=5,
        repair_shapes_passed=2,
        eval_shapes_passed=3,
    )

    rebuilt_request = RemoteCorrectnessRequest(**request.model_dump())
    rebuilt_result = RemoteCorrectnessResult(**result.model_dump())

    assert rebuilt_request == request
    assert rebuilt_result == result
    assert rebuilt_request.identity.generation_mode == "replay_control"


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        (
            {"repair_set_success": True, "repair_shapes_passed": 1},
            "repair_set_success",
        ),
        (
            {"eval_set_success": True, "eval_shapes_passed": 2, "shapes_passed": 3},
            "eval_set_success",
        ),
    ],
)
def test_correctness_result_rejects_set_success_count_mismatch(
    overrides: dict[str, object],
    match: str,
) -> None:
    payload = _correctness_result_payload()
    payload.update(overrides)

    with pytest.raises(ValueError, match=match):
        RemoteCorrectnessResult(**payload)


@pytest.mark.parametrize(
    "overrides",
    [
        {"sample_index": "0"},
        {"sample_index": True},
        {"base_seed": "123"},
        {"attempt_index": False},
    ],
)
def test_eval_identity_rejects_coerced_integer_boundary_values(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        EvalIdentity(**_identity_payload("C", **overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_new_tokens": "1024"},
        {"generation_seed": "17"},
        {"temperature": "0.2"},
    ],
)
def test_generation_request_rejects_coerced_numeric_boundary_values(
    overrides: dict[str, object],
) -> None:
    payload = _generation_request_payload("C")
    payload.update(overrides)

    with pytest.raises(ValueError):
        RemoteC2GenerationRequest(**payload)


@pytest.mark.parametrize(
    "temperature",
    [float("nan"), float("inf"), float("-inf")],
)
def test_generation_request_rejects_non_finite_temperature(
    temperature: float,
) -> None:
    payload = _generation_request_payload("C", temperature=temperature)

    with pytest.raises(ValueError):
        RemoteC2GenerationRequest(**payload)


@pytest.mark.parametrize(
    "overrides",
    [
        {"functional_success": "false"},
        {"repair_set_success": 0},
        {"eval_set_success": "true"},
        {"num_test_shapes": "5"},
        {"max_abs_diff": "1.0"},
    ],
)
def test_correctness_result_rejects_coerced_boundary_values(
    overrides: dict[str, object],
) -> None:
    payload = _correctness_result_payload()
    payload.update(overrides)

    with pytest.raises(ValueError):
        RemoteCorrectnessResult(**payload)


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_abs_diff": float("nan")},
        {"max_abs_diff": float("inf")},
        {"max_abs_diff": float("-inf")},
        {"max_rel_diff": float("nan")},
        {"max_rel_diff": float("inf")},
        {"max_rel_diff": float("-inf")},
    ],
)
def test_correctness_result_rejects_non_finite_diff_values(
    overrides: dict[str, object],
) -> None:
    payload = _correctness_result_payload()
    payload.update(overrides)

    with pytest.raises(ValueError):
        RemoteCorrectnessResult(**payload)


def test_schema_models_reject_forbidden_extra_surfaces() -> None:
    models = (
        EvalIdentity,
        RemoteC2GenerationRequest,
        RemoteC2GenerationResult,
        RemoteCorrectnessRequest,
        RemoteCorrectnessResult,
    )
    for model in models:
        assert FORBIDDEN_REQUEST_RESULT_FIELD_NAMES.isdisjoint(model.model_fields)

    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        RemoteCorrectnessResult(
            **_correctness_result_payload(),
            latency_ms=1.0,
        )


def test_cluster2_modal_schemas_import_without_runtime_modules() -> None:
    leaked = _modules_after_import("cluster2.modal.schemas", FORBIDDEN_IMPORT_MODULES)

    assert leaked == []


def test_cluster2_modal_schemas_do_not_import_generation_or_runtime_modules() -> None:
    imported_modules = _imported_modules(SCHEMA_PATH)
    leaked = sorted(
        module
        for module in imported_modules
        if any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in FORBIDDEN_IMPORT_MODULES
        )
    )

    assert leaked == []


def test_shared_modal_harness_schemas_remain_cluster1_only() -> None:
    source = SHARED_MODAL_SCHEMA_PATH.read_text(encoding="utf-8")
    for c2_name in (
        "EvalIdentity",
        "RemoteC2GenerationRequest",
        "RemoteC2GenerationResult",
        "RemoteCorrectnessRequest",
        "RemoteCorrectnessResult",
    ):
        assert c2_name not in source

    from shared.modal_harness import schemas as shared_schemas

    assert not hasattr(shared_schemas, "RemoteC2GenerationRequest")
    with pytest.raises(ValueError, match="only 'none' and 'G' are implemented"):
        shared_schemas.RemoteGenerationRequest(
            factor_cell="C",
            kernel_class="elementwise",
            kernel_name="relu",
            dtype="fp32",
            prompt="write relu",
            model_id="model",
            grammar_active=False,
            run_id="rid",
        )


def _generation_request(
    condition: str,
    *,
    generation_seed: int | None = None,
) -> RemoteC2GenerationRequest:
    payload = _generation_request_payload(condition, generation_seed=generation_seed)
    return RemoteC2GenerationRequest(**payload)


def _generation_request_payload(
    condition: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "identity": _identity(condition),
        "prompt": "write a complete Triton relu kernel",
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": "model-rev",
        "tokenizer_revision": "tokenizer-rev",
        "generation_seed": None,
    }
    payload.update(overrides)
    return payload


def _identity(condition: str) -> EvalIdentity:
    return EvalIdentity(**_identity_payload(condition))


def _identity_payload(condition: str, **overrides: object) -> dict[str, object]:
    source_class = (
        "replay_control_row" if condition in {"none", "G"} else "generated_row"
    )
    generation_mode = {
        "none": "replay_control",
        "G": "replay_control",
        "C": "new_c2_generation",
        "G+C": "new_c2_generation_with_G_adapter",
    }.get(condition, "new_c2_generation")
    payload: dict[str, object] = {
        "run_id": "phase5-test-run",
        "condition": condition,
        "source_class": source_class,
        "generation_mode": generation_mode,
        "kernel_class": "elementwise",
        "kernel_name": "relu",
        "dtype": "fp32",
        "sample_index": 0,
        "base_seed": 123,
        "attempt_index": 0,
    }
    payload.update(overrides)
    return payload


def _correctness_result_payload() -> dict[str, object]:
    return {
        "identity": _identity("C").model_dump(),
        "functional_success": False,
        "repair_set_success": False,
        "eval_set_success": True,
        "failure_code": "F2_NUMERIC_LARGE",
        "correctness_error": "repair-set mismatch",
        "feedback": "repair-set mismatch",
        "num_repair_shapes": 2,
        "num_eval_shapes": 3,
        "num_test_shapes": 5,
        "shapes_passed": 4,
        "repair_shapes_passed": 1,
        "eval_shapes_passed": 3,
        "max_abs_diff": 1.0,
        "max_rel_diff": 1.0,
    }


def _modules_after_import(target: str, module_names: tuple[str, ...]) -> list[str]:
    code = (
        "import sys\n"
        f"import {target}  # noqa: F401\n"
        "loaded = [name for name in "
        f"{module_names!r} if name in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"probe failed for {target}: rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    out = proc.stdout.strip()
    return out.split(",") if out else []


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules
