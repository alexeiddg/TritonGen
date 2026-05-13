"""Phase 6 tests for C2 remote correctness plumbing."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from cluster2.modal import correctness_runner
from cluster2.modal.correctness import _run_remote_c2_correctness
from cluster2.modal.correctness_runner import (
    INFRASTRUCTURE_FAILURE_STATUS,
    REMOTE_CORRECTNESS_EVAL_GPU,
    build_infrastructure_failure_payload,
    run_correctness_payload,
    validate_remote_correctness_payload,
)
from cluster2.modal.schemas import (
    FORBIDDEN_REQUEST_RESULT_FIELD_NAMES,
    EvalIdentity,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
)
from cluster2.validation.modal_correctness_check import (
    SMOKE_COMMANDS,
    build_correctness_request,
    check_remote_correctness,
    configured_modal_eval_gpu,
    extract_correctness_result,
)
from shared.tests.level2_fake_torch import install_fake_level2_runtime


REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE6_PATHS = (
    REPO_ROOT / "cluster2" / "modal" / "correctness.py",
    REPO_ROOT / "cluster2" / "modal" / "correctness_runner.py",
    REPO_ROOT / "cluster2" / "validation" / "modal_correctness_check.py",
)
FORBIDDEN_SHARED_MODAL_IMPORTS = (
    "shared.modal_harness.generation",
    "shared.modal_harness.schemas",
    "shared.modal_harness.smoke",
)
FORBIDDEN_GENERATION_IMPORTS = (
    "cluster2.modal.generation",
    "cluster1.generation",
    "shared.modal_harness.generation",
)
HEAVY_MODULES = ("torch", "triton", "transformers", "xgrammar", "autoawq")


@pytest.fixture(autouse=True)
def fake_level2_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_level2_runtime(monkeypatch)


def test_remote_correctness_request_validation() -> None:
    request = build_correctness_request(identity=_identity("C"), source=_relu_source())

    assert isinstance(request, RemoteCorrectnessRequest)
    assert request.identity.condition == "C"
    assert request.identity.source_class == "generated_row"

    with pytest.raises(ValueError, match="must not be empty"):
        build_correctness_request(identity=_identity("C"), source="")


def test_correctness_runner_handles_valid_payload() -> None:
    payload = run_correctness_payload(_request().model_dump())

    assert payload["correctness_status"] == "passed"
    assert payload["modal_eval_gpu"] == "L4"
    assert payload["eval_identity"]["modal_eval_gpu"] == "L4"
    assert payload["eval_identity"]["device"] == "cuda"
    assert payload["source_identity"]["source_sha256"]
    assert payload["eval_pipeline_hashes"]
    assert payload["external_pins"]


def test_correctness_runner_returns_schema_compatible_result() -> None:
    payload = validate_remote_correctness_payload(
        run_correctness_payload(_request().model_dump())
    )

    result = RemoteCorrectnessResult(**payload["correctness_result"])

    assert result.identity == _identity("C")
    assert result.functional_success is True
    assert result.num_test_shapes == (
        result.num_repair_shapes + result.num_eval_shapes
    )


def test_correctness_payload_rejects_status_result_mismatch() -> None:
    payload = run_correctness_payload(_request().model_dump())
    payload["correctness_status"] = "failed"

    with pytest.raises(ValueError, match="correctness_status does not match"):
        validate_remote_correctness_payload(payload)


@pytest.mark.parametrize(
    ("sidecar", "field", "value"),
    (
        ("source_identity", "dtype", "fp16"),
        ("source_identity", "sample_index", 1),
        ("eval_identity", "base_seed", 124),
    ),
)
def test_correctness_payload_rejects_identity_sidecar_mismatch(
    sidecar: str,
    field: str,
    value: str | int,
) -> None:
    payload = run_correctness_payload(_request().model_dump())
    payload[sidecar][field] = value

    with pytest.raises(ValueError, match=f"{sidecar} {field} does not match"):
        validate_remote_correctness_payload(payload)


def test_infrastructure_payload_rejects_identity_sidecar_mismatch() -> None:
    payload = build_infrastructure_failure_payload(
        _request(),
        error_type="TimeoutError",
        error_msg="subprocess timed out",
    )
    payload["eval_identity"]["attempt_index"] = 1

    with pytest.raises(ValueError, match="eval_identity attempt_index does not match"):
        validate_remote_correctness_payload(payload)


def test_infrastructure_payload_with_identity_requires_sidecars() -> None:
    payload = build_infrastructure_failure_payload(
        _request(),
        error_type="TimeoutError",
        error_msg="subprocess timed out",
    )
    del payload["source_identity"]

    with pytest.raises(ValueError, match="with identity missing sidecars"):
        validate_remote_correctness_payload(payload)


def test_validation_adapter_calls_injected_remote_and_extracts_result() -> None:
    request = _request()

    def fake_remote(req_dict: dict[str, Any]) -> dict[str, Any]:
        return run_correctness_payload(req_dict)

    payload = check_remote_correctness(request, remote_call=fake_remote)
    result = extract_correctness_result(payload)

    assert result is not None
    assert result.functional_success is True
    assert configured_modal_eval_gpu() == "L4"


def test_modal_function_imports_without_forbidden_shared_modal_files() -> None:
    leaked = _modules_after_import(
        "cluster2.modal.correctness",
        FORBIDDEN_SHARED_MODAL_IMPORTS,
    )

    assert leaked == []


def test_modal_function_imports_without_heavy_runtime_modules() -> None:
    leaked = _modules_after_import("cluster2.modal.correctness", HEAVY_MODULES)

    assert leaked == []


def test_phase6_files_do_not_import_generation_or_remote_generator() -> None:
    for path in PHASE6_PATHS:
        imported_modules = _imported_modules(path)
        leaked = sorted(
            module
            for module in imported_modules
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_GENERATION_IMPORTS
            )
        )
        source = path.read_text(encoding="utf-8")

        assert leaked == []
        assert "RemoteGenerator" not in source
        assert ".generate_one(" not in source


def test_remote_payload_has_no_timing_or_performance_fields() -> None:
    payload = run_correctness_payload(_request().model_dump())
    keys = _all_keys(payload)

    assert FORBIDDEN_REQUEST_RESULT_FIELD_NAMES.isdisjoint(keys)
    assert "performance" not in keys


@pytest.mark.parametrize("forbidden_field", ("timing", "performance"))
def test_remote_payload_rejects_forbidden_fields_at_boundary(
    forbidden_field: str,
) -> None:
    payload = run_correctness_payload(_request().model_dump())
    payload["modal_context"] = {"modal_eval_gpu": "L4", forbidden_field: "not allowed"}

    with pytest.raises(ValueError, match="forbidden remote correctness field"):
        validate_remote_correctness_payload(payload)


def test_eval_hashes_and_external_pins_are_included() -> None:
    payload = run_correctness_payload(_request().model_dump())

    assert payload["eval_pipeline_hash_class"] == "shared_eval_pipeline"
    assert "shared/eval/pipeline.py" in payload["eval_pipeline_hashes"]
    assert payload["external_pin_class"] == "python_package_environment"
    assert "python_version" in payload["external_pins"]


def test_subprocess_failure_maps_to_infrastructure_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> types.SimpleNamespace:
        del args, kwargs
        return types.SimpleNamespace(returncode=2, stdout="child out", stderr="child err")

    monkeypatch.setattr(subprocess, "run", fake_run)

    payload = _run_remote_c2_correctness(_request().model_dump())

    assert payload["correctness_status"] == INFRASTRUCTURE_FAILURE_STATUS
    assert payload["infrastructure_failure"]["error_type"] == "SubprocessResultMissing"
    assert payload["infrastructure_failure"]["stderr"] == "child err"
    assert payload["modal_eval_gpu"] == "L4"
    assert payload["eval_pipeline_hashes"]


def test_subprocess_timeout_failure_decodes_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise subprocess.TimeoutExpired(
            cmd=["python", "-m", "cluster2.modal.correctness_runner"],
            timeout=1,
            output=b"child out",
            stderr=b"child err",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    payload = _run_remote_c2_correctness(_request().model_dump())

    assert payload["correctness_status"] == INFRASTRUCTURE_FAILURE_STATUS
    assert payload["infrastructure_failure"]["error_type"] == "TimeoutError"
    assert payload["infrastructure_failure"]["stdout"] == "child out"
    assert payload["infrastructure_failure"]["stderr"] == "child err"
    json.dumps(payload, sort_keys=True)


def test_l4_is_configured_eval_gpu_in_runner_and_metadata_paths() -> None:
    payload = run_correctness_payload(_request().model_dump())

    assert REMOTE_CORRECTNESS_EVAL_GPU == "L4"
    assert correctness_runner.REMOTE_CORRECTNESS_EVAL_GPU == "L4"
    assert configured_modal_eval_gpu() == "L4"
    assert payload["modal_eval_gpu"] == "L4"
    assert payload["eval_identity"]["modal_eval_gpu"] == "L4"


def test_smoke_commands_are_documented_without_runner_or_generation_flags() -> None:
    rendered = "\n".join(SMOKE_COMMANDS)

    assert "cluster2/modal/correctness.py::smoke_remote_correctness" in rendered
    assert "cluster2/tests/test_modal_correctness_check.py" in rendered
    assert "generation" not in rendered
    assert "repair" not in rendered


def _request(condition: str = "C") -> RemoteCorrectnessRequest:
    return RemoteCorrectnessRequest(identity=_identity(condition), source=_relu_source())


def _identity(condition: str) -> EvalIdentity:
    source_class = (
        "replay_control_row" if condition in {"none", "G"} else "generated_row"
    )
    generation_mode = {
        "none": "replay_control",
        "G": "replay_control",
        "C": "new_c2_generation",
        "G+C": "new_c2_generation_with_G_adapter",
    }[condition]
    return EvalIdentity(
        run_id="phase6-test-run",
        condition=condition,
        source_class=source_class,
        generation_mode=generation_mode,
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        sample_index=0,
        base_seed=123,
        attempt_index=0,
    )


def _relu_source() -> str:
    return (
        "import torch\n\n"
        "def relu(x: torch.Tensor) -> torch.Tensor:\n"
        "    return torch.relu(x)\n"
    )


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


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()
