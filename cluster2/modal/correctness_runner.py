"""Subprocess child for Cluster 2 remote correctness evaluation.

CLI::

    python -m cluster2.modal.correctness_runner <request_path> <result_path>

The child reads a ``RemoteCorrectnessRequest`` JSON payload, runs the existing
shared eval pipeline with an explicit Level 2 request, and writes one JSON
document to ``result_path``. This module does not import Modal or generation
surfaces.
"""

from __future__ import annotations

import atexit
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import traceback
import types
from pathlib import Path
from typing import Any

from cluster2.constants import (
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_EQUAL_ATTEMPTS_N,
    DEFAULT_REPAIR_BUDGET,
    generation_allowed_for_condition,
)
from cluster2.modal.schemas import (
    C2ModalSurfaceMetadata,
    EvalIdentity,
    FORBIDDEN_REQUEST_RESULT_FIELD_NAMES,
    RemoteCorrectnessRequest,
    RemoteCorrectnessResult,
    modal_surface_metadata,
)
from shared.eval.content_hashes import (
    collect_eval_pipeline_hashes,
    collect_external_pins,
)
from shared.eval.pipeline import PipelineLevel2Request, run_eval_pipeline
from shared.eval.run_config import RunConfig


C2_CORRECTNESS_PAYLOAD_SCHEMA_VERSION = 1
C2_CORRECTNESS_SURFACE = "c2_remote_correctness"
C2_CORRECTNESS_HASH_CLASS = "shared_eval_pipeline"
C2_CORRECTNESS_EXTERNAL_PIN_CLASS = "python_package_environment"
C2_CORRECTNESS_DEVICE = "cuda"
REMOTE_CORRECTNESS_EVAL_GPU = DEFAULT_C2_MODAL_EVAL_GPU
INFRASTRUCTURE_FAILURE_STATUS = "INFRA_FAILURE"
_INTERNAL_MODEL_ID = "c2-remote-correctness-only"
_UNAVAILABLE_REVISION = "unavailable"
_C2_REMOTE_CORRECTNESS_FORBIDDEN_EXTRA_FIELDS = frozenset({"performance"})


def correctness_runner_surface_metadata() -> C2ModalSurfaceMetadata:
    """Return metadata for the C2 correctness runner."""

    return modal_surface_metadata()


def run_correctness_payload(request_payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and execute one remote correctness request payload."""

    request = RemoteCorrectnessRequest(**request_payload)
    _configure_correctness_runtime()

    launcher_name = _launcher_name_for_request(request)
    candidate_runner = _GeneratedSourceCandidateRunner(
        request.source,
        launcher_name=launcher_name,
    )
    try:
        pipeline_result = run_eval_pipeline(
            _run_config_for_identity(request.identity),
            level2_request=PipelineLevel2Request(
                kernel_class=request.identity.kernel_class,
                dtype=request.identity.dtype,
                base_seed=request.identity.base_seed,
                attempt_index=request.identity.attempt_index,
                candidate_runner=candidate_runner,
                device=C2_CORRECTNESS_DEVICE,
            ),
        )
    finally:
        candidate_runner.close()

    level2_result = pipeline_result.level2_result
    if level2_result is None:
        raise RuntimeError("shared eval pipeline did not return a Level 2 result")

    result = RemoteCorrectnessResult(
        identity=request.identity,
        functional_success=level2_result.functional_success,
        repair_set_success=level2_result.repair_set_success,
        eval_set_success=level2_result.eval_set_success,
        failure_code=level2_result.failure_code,
        correctness_error=level2_result.correctness_error,
        feedback=level2_result.feedback,
        num_repair_shapes=level2_result.num_repair_shapes,
        num_eval_shapes=level2_result.num_eval_shapes,
        num_test_shapes=level2_result.num_test_shapes,
        shapes_passed=level2_result.shapes_passed,
        repair_shapes_passed=level2_result.repair_shapes_passed,
        eval_shapes_passed=level2_result.eval_shapes_passed,
        max_abs_diff=level2_result.max_abs_diff,
        max_rel_diff=level2_result.max_rel_diff,
    )
    return build_success_payload(request, result)


def build_success_payload(
    request: RemoteCorrectnessRequest,
    result: RemoteCorrectnessResult,
) -> dict[str, Any]:
    """Return the Phase 6 wrapper around a schema-compatible result."""

    identity_payload = request.identity.model_dump()
    source_sha256 = hashlib.sha256(request.source.encode("utf-8")).hexdigest()
    return {
        "schema_version": C2_CORRECTNESS_PAYLOAD_SCHEMA_VERSION,
        "surface": C2_CORRECTNESS_SURFACE,
        "correctness_status": (
            "passed" if result.functional_success else "failed"
        ),
        "modal_eval_gpu": REMOTE_CORRECTNESS_EVAL_GPU,
        "eval_pipeline_hash_class": C2_CORRECTNESS_HASH_CLASS,
        "external_pin_class": C2_CORRECTNESS_EXTERNAL_PIN_CLASS,
        "identity": identity_payload,
        "source_identity": {
            "source_sha256": source_sha256,
            "condition": request.identity.condition,
            "source_class": request.identity.source_class,
            "generation_mode": request.identity.generation_mode,
            "kernel_class": request.identity.kernel_class,
            "kernel_name": request.identity.kernel_name,
            "dtype": request.identity.dtype,
            "sample_index": request.identity.sample_index,
            "base_seed": request.identity.base_seed,
            "attempt_index": request.identity.attempt_index,
        },
        "eval_identity": {
            "level": "level2_correctness",
            "pipeline": "shared.eval.pipeline.run_eval_pipeline",
            "device": C2_CORRECTNESS_DEVICE,
            "modal_eval_gpu": REMOTE_CORRECTNESS_EVAL_GPU,
            "kernel_class": request.identity.kernel_class,
            "kernel_name": request.identity.kernel_name,
            "dtype": request.identity.dtype,
            "base_seed": request.identity.base_seed,
            "attempt_index": request.identity.attempt_index,
        },
        "correctness_result": result.model_dump(),
        "eval_pipeline_hashes": collect_eval_pipeline_hashes(),
        "external_pins": collect_external_pins(),
    }


def build_infrastructure_failure_payload(
    request: RemoteCorrectnessRequest | None,
    *,
    error_type: str,
    error_msg: str,
    stdout: str = "",
    stderr: str = "",
    traceback_text: str | None = None,
) -> dict[str, Any]:
    """Return a structured non-correctness failure payload."""

    payload: dict[str, Any] = {
        "schema_version": C2_CORRECTNESS_PAYLOAD_SCHEMA_VERSION,
        "surface": C2_CORRECTNESS_SURFACE,
        "correctness_status": INFRASTRUCTURE_FAILURE_STATUS,
        "modal_eval_gpu": REMOTE_CORRECTNESS_EVAL_GPU,
        "eval_pipeline_hash_class": C2_CORRECTNESS_HASH_CLASS,
        "external_pin_class": C2_CORRECTNESS_EXTERNAL_PIN_CLASS,
        "infrastructure_failure": {
            "error_type": error_type,
            "error_msg": error_msg,
            "stdout": stdout,
            "stderr": stderr,
            "traceback": traceback_text,
        },
        "eval_pipeline_hashes": collect_eval_pipeline_hashes(),
        "external_pins": collect_external_pins(),
    }
    if request is not None:
        payload["identity"] = request.identity.model_dump()
        payload["source_identity"] = {
            "source_sha256": hashlib.sha256(
                request.source.encode("utf-8")
            ).hexdigest(),
            "condition": request.identity.condition,
            "source_class": request.identity.source_class,
            "generation_mode": request.identity.generation_mode,
            "kernel_class": request.identity.kernel_class,
            "kernel_name": request.identity.kernel_name,
            "dtype": request.identity.dtype,
            "sample_index": request.identity.sample_index,
            "base_seed": request.identity.base_seed,
            "attempt_index": request.identity.attempt_index,
        }
        payload["eval_identity"] = {
            "level": "level2_correctness",
            "pipeline": "shared.eval.pipeline.run_eval_pipeline",
            "device": C2_CORRECTNESS_DEVICE,
            "modal_eval_gpu": REMOTE_CORRECTNESS_EVAL_GPU,
            "kernel_class": request.identity.kernel_class,
            "kernel_name": request.identity.kernel_name,
            "dtype": request.identity.dtype,
            "base_seed": request.identity.base_seed,
            "attempt_index": request.identity.attempt_index,
        }
    return payload


def validate_remote_correctness_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the Phase 6 remote correctness wrapper and nested schemas."""

    if not isinstance(payload, dict):
        raise TypeError("remote correctness payload must be a dict")
    _reject_forbidden_payload_fields(payload)
    required = {
        "schema_version",
        "surface",
        "correctness_status",
        "modal_eval_gpu",
        "eval_pipeline_hash_class",
        "external_pin_class",
        "eval_pipeline_hashes",
        "external_pins",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing remote correctness fields: {', '.join(missing)}")
    if payload["schema_version"] != C2_CORRECTNESS_PAYLOAD_SCHEMA_VERSION:
        raise ValueError("unsupported remote correctness schema_version")
    if payload["surface"] != C2_CORRECTNESS_SURFACE:
        raise ValueError("unsupported remote correctness surface")
    if payload["modal_eval_gpu"] != REMOTE_CORRECTNESS_EVAL_GPU:
        raise ValueError("C2 remote correctness must use L4 eval GPU metadata")
    if payload["eval_pipeline_hash_class"] != C2_CORRECTNESS_HASH_CLASS:
        raise ValueError("unexpected eval pipeline hash class")
    if payload["external_pin_class"] != C2_CORRECTNESS_EXTERNAL_PIN_CLASS:
        raise ValueError("unexpected external pin class")
    _validate_string_mapping(payload["eval_pipeline_hashes"], "eval_pipeline_hashes")
    _validate_string_mapping(payload["external_pins"], "external_pins")

    status = payload["correctness_status"]
    if status == INFRASTRUCTURE_FAILURE_STATUS:
        if "infrastructure_failure" not in payload:
            raise ValueError("infrastructure failure payload missing details")
        if "identity" in payload:
            identity = EvalIdentity(**payload["identity"])
            if "source_identity" not in payload or "eval_identity" not in payload:
                raise ValueError(
                    "infrastructure failure payload with identity missing sidecars"
                )
            _validate_identity_sidecars(
                source_identity=payload["source_identity"],
                eval_identity=payload["eval_identity"],
                identity=identity,
            )
        elif "source_identity" in payload or "eval_identity" in payload:
            raise ValueError("infrastructure failure sidecars require identity")
        return payload

    if status not in {"passed", "failed"}:
        raise ValueError(f"unsupported correctness_status {status!r}")
    if "identity" not in payload:
        raise ValueError("success/failure payload missing identity")
    if "source_identity" not in payload:
        raise ValueError("success/failure payload missing source_identity")
    if "eval_identity" not in payload:
        raise ValueError("success/failure payload missing eval_identity")
    if "correctness_result" not in payload:
        raise ValueError("success/failure payload missing correctness_result")

    identity = EvalIdentity(**payload["identity"])
    result = RemoteCorrectnessResult(**payload["correctness_result"])
    if result.identity != identity:
        raise ValueError("correctness_result identity does not match wrapper identity")
    expected_status = "passed" if result.functional_success else "failed"
    if status != expected_status:
        raise ValueError(
            "correctness_status does not match correctness_result functional_success"
        )
    _validate_identity_sidecars(
        source_identity=payload["source_identity"],
        eval_identity=payload["eval_identity"],
        identity=identity,
    )
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write(
            "correctness_runner expects exactly two argv: "
            "<request_path> <result_path>\n"
        )
        sys.exit(2)

    request_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])
    request: RemoteCorrectnessRequest | None = None
    try:
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
        request = RemoteCorrectnessRequest(**request_data)
        payload = run_correctness_payload(request.model_dump())
        _write_result(result_path, payload)
    except Exception as exc:
        _write_result(
            result_path,
            build_infrastructure_failure_payload(
                request,
                error_type=type(exc).__name__,
                error_msg=str(exc),
                traceback_text=traceback.format_exc(),
            ),
        )
        sys.exit(2)


class _GeneratedSourceCandidateRunner:
    """Load generated source once and call the expected public launcher."""

    def __init__(self, source: str, *, launcher_name: str) -> None:
        self._source = source
        self._launcher_name = launcher_name
        self._module: types.ModuleType | None = None
        self._cleanup: _GeneratedModuleCleanup | None = None

    def __call__(self, request: Any) -> Any:
        module = self._ensure_module()
        launcher = getattr(module, self._launcher_name, None)
        if not callable(launcher):
            raise RuntimeError(
                f"launcher {self._launcher_name!r} not found in generated source"
            )
        torch = _torch()
        with torch.no_grad():
            return launcher(*request.inputs)

    def close(self) -> None:
        cleanup = self._cleanup
        self._module = None
        self._cleanup = None
        if cleanup is not None:
            _run_generated_module_cleanup(cleanup)
            try:
                atexit.unregister(cleanup)
            except Exception:
                pass

    def _ensure_module(self) -> types.ModuleType:
        if self._module is None:
            self._module, self._cleanup = _load_generated_module(self._source)
        return self._module


class _GeneratedModuleCleanup:
    def __init__(self, module_name: str, source_path: str) -> None:
        self.module_name = module_name
        self.source_path = source_path
        self.active = True

    def __call__(self) -> None:
        if not self.active:
            return
        self.active = False
        sys.modules.pop(self.module_name, None)
        try:
            os.unlink(self.source_path)
        except OSError:
            pass


def _load_generated_module(
    source: str,
) -> tuple[types.ModuleType, _GeneratedModuleCleanup]:
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".py")
    module_name = f"_c2_correctness_candidate_{os.path.basename(tmp_path).replace('.', '_')}"
    cleanup = _GeneratedModuleCleanup(module_name, tmp_path)
    atexit.register(cleanup)

    with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp:
        tmp.write(source)

    spec = importlib.util.spec_from_file_location(module_name, tmp_path)
    if spec is None or spec.loader is None:
        _run_generated_module_cleanup(cleanup)
        raise RuntimeError("could not create module spec from generated source")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except SyntaxError as exc:
        _run_generated_module_cleanup(cleanup)
        raise RuntimeError(f"syntax error in generated source: {exc}") from exc
    except Exception as exc:
        _run_generated_module_cleanup(cleanup)
        raise RuntimeError(f"import error in generated source: {exc}") from exc
    return module, cleanup


def _run_generated_module_cleanup(cleanup: _GeneratedModuleCleanup) -> None:
    cleanup()


def _launcher_name_for_request(request: RemoteCorrectnessRequest) -> str:
    from cluster1.data.kernels import get_kernel_spec

    spec = get_kernel_spec(request.identity.kernel_class)
    if spec.name != request.identity.kernel_name:
        raise ValueError(
            f"kernel_name mismatch: spec for {request.identity.kernel_class!r} "
            f"expects {spec.name!r}, got {request.identity.kernel_name!r}"
        )
    return spec.launcher_name


def _run_config_for_identity(identity: EvalIdentity) -> RunConfig:
    generation_gpu = (
        "L4" if generation_allowed_for_condition(identity.condition) else None
    )
    return RunConfig(
        condition=identity.condition,  # type: ignore[arg-type]
        source_class=identity.source_class,  # type: ignore[arg-type]
        generation_mode=identity.generation_mode,  # type: ignore[arg-type]
        scale_tier="smoke",
        repair_budget=DEFAULT_REPAIR_BUDGET,
        equal_attempts_n=DEFAULT_EQUAL_ATTEMPTS_N,
        enable_ast_sanitizer=False,
        dtypes=(identity.dtype,),
        model_id=_INTERNAL_MODEL_ID,
        model_revision=_UNAVAILABLE_REVISION,
        tokenizer_revision=_UNAVAILABLE_REVISION,
        modal_generation_gpu=generation_gpu,
        modal_eval_gpu=REMOTE_CORRECTNESS_EVAL_GPU,
    )


def _configure_correctness_runtime() -> None:
    torch = _torch()
    use_deterministic = getattr(torch, "use_deterministic_algorithms", None)
    if callable(use_deterministic):
        try:
            use_deterministic(True, warn_only=True)
        except TypeError:
            use_deterministic(True)

    backends = getattr(torch, "backends", None)
    cuda_backend = getattr(backends, "cuda", None)
    matmul_backend = getattr(cuda_backend, "matmul", None)
    _set_existing_attr(matmul_backend, "allow_tf32", False)

    cudnn_backend = getattr(backends, "cudnn", None)
    _set_existing_attr(cudnn_backend, "allow_tf32", False)
    _set_existing_attr(cudnn_backend, "deterministic", True)
    _set_existing_attr(cudnn_backend, "benchmark", False)


def _set_existing_attr(target: Any, name: str, value: Any) -> None:
    if target is not None and hasattr(target, name):
        setattr(target, name, value)


def _torch() -> Any:
    import torch

    return torch


def _validate_string_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{field_name} must be a non-empty dict")
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_name} values must be non-empty strings")


def _reject_forbidden_payload_fields(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}" if isinstance(key, str) else path
            if (
                key in FORBIDDEN_REQUEST_RESULT_FIELD_NAMES
                or key in _C2_REMOTE_CORRECTNESS_FORBIDDEN_EXTRA_FIELDS
            ):
                raise ValueError(f"forbidden remote correctness field: {key_path}")
            _reject_forbidden_payload_fields(item, key_path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_payload_fields(item, f"{path}[{index}]")


def _validate_identity_sidecars(
    *,
    source_identity: Any,
    eval_identity: Any,
    identity: EvalIdentity,
) -> None:
    if not isinstance(source_identity, dict):
        raise TypeError("source_identity must be a dict")
    if not isinstance(eval_identity, dict):
        raise TypeError("eval_identity must be a dict")

    source_sha256 = source_identity.get("source_sha256")
    if not isinstance(source_sha256, str) or not source_sha256:
        raise ValueError("source_identity must include non-empty source_sha256")

    _validate_sidecar_identity_fields(
        source_identity,
        identity,
        field_name="source_identity",
        fields=(
            "condition",
            "source_class",
            "generation_mode",
            "kernel_class",
            "kernel_name",
            "dtype",
            "sample_index",
            "base_seed",
            "attempt_index",
        ),
    )
    _validate_sidecar_identity_fields(
        eval_identity,
        identity,
        field_name="eval_identity",
        fields=(
            "kernel_class",
            "kernel_name",
            "dtype",
            "base_seed",
            "attempt_index",
        ),
    )

    if eval_identity.get("level") != "level2_correctness":
        raise ValueError("eval_identity must record level2_correctness")
    if eval_identity.get("pipeline") != "shared.eval.pipeline.run_eval_pipeline":
        raise ValueError("eval_identity must record shared eval pipeline")
    if eval_identity.get("device") != C2_CORRECTNESS_DEVICE:
        raise ValueError("eval_identity must record cuda device")
    if eval_identity.get("modal_eval_gpu") != REMOTE_CORRECTNESS_EVAL_GPU:
        raise ValueError("eval_identity must record L4 modal_eval_gpu")


def _validate_sidecar_identity_fields(
    sidecar: dict[str, Any],
    identity: EvalIdentity,
    *,
    field_name: str,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        expected = getattr(identity, field)
        if sidecar.get(field) != expected:
            raise ValueError(
                f"{field_name} {field} does not match wrapper identity"
            )


def _write_result(result_path: Path, payload: dict[str, Any]) -> None:
    result_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
