"""Cluster 2 remote correctness Modal function.

Manual smoke command, when Modal execution is intentionally desired::

    /Users/alexeidelgado/miniconda3/bin/modal run cluster2/modal/correctness.py::smoke_remote_correctness

The smoke path calls this C2 module directly and exercises only correctness
plumbing. It does not call generation, repair-loop orchestration, benchmarking,
or Cluster 1 Modal entry points.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

from cluster2.modal.correctness_runner import (
    INFRASTRUCTURE_FAILURE_STATUS,
    REMOTE_CORRECTNESS_EVAL_GPU,
    build_infrastructure_failure_payload,
    validate_remote_correctness_payload,
)
from cluster2.modal.schemas import (
    C2ModalSurfaceMetadata,
    EvalIdentity,
    RemoteCorrectnessRequest,
    modal_surface_metadata,
)
from shared.modal_harness.app import app
from shared.modal_harness.errors import truncate_output
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.runtime import current_modal_ids


CORRECTNESS_SUBPROCESS_TIMEOUT_S = 600
c2_correctness_image = triton_compile_image.add_local_python_source("cluster2")


@app.function(
    image=c2_correctness_image,
    gpu=REMOTE_CORRECTNESS_EVAL_GPU,
    memory=24576,
    cpu=4.0,
    timeout=900,
    max_containers=20,
    min_containers=0,
    scaledown_window=120,
)
def remote_c2_correctness(req_dict: dict) -> dict:
    """Run one C2 correctness check inside a subprocess-isolated Modal call."""

    return _run_remote_c2_correctness(req_dict)


def _run_remote_c2_correctness(req_dict: dict[str, Any]) -> dict[str, Any]:
    """Pure-Python implementation of ``remote_c2_correctness`` for tests."""

    request = RemoteCorrectnessRequest(**req_dict)
    call_id, input_id = current_modal_ids()

    with tempfile.TemporaryDirectory() as tmpdir:
        request_file = Path(tmpdir) / "request.json"
        result_file = Path(tmpdir) / "result.json"
        request_file.write_text(
            json.dumps(request.model_dump(), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cluster2.modal.correctness_runner",
                    str(request_file),
                    str(result_file),
                ],
                capture_output=True,
                text=True,
                timeout=CORRECTNESS_SUBPROCESS_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as exc:
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type="TimeoutError",
                    error_msg=(
                        "correctness subprocess exceeded the remote execution limit"
                    ),
                    stdout=_truncate_subprocess_output(exc.stdout),
                    stderr=_truncate_subprocess_output(exc.stderr),
                ),
                call_id=call_id,
                input_id=input_id,
            )
        except Exception as exc:
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type=type(exc).__name__,
                    error_msg=str(exc),
                    traceback_text=traceback.format_exc(),
                ),
                call_id=call_id,
                input_id=input_id,
            )

        try:
            child_payload = json.loads(result_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type="SubprocessResultMissing",
                    error_msg=(
                        "correctness_runner did not produce a result file "
                        f"(exit={proc.returncode})"
                    ),
                    stdout=_truncate_subprocess_output(proc.stdout),
                    stderr=_truncate_subprocess_output(proc.stderr),
                ),
                call_id=call_id,
                input_id=input_id,
            )
        except json.JSONDecodeError as exc:
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type="SubprocessResultInvalid",
                    error_msg=(
                        "correctness_runner result file was not valid JSON "
                        f"(exit={proc.returncode}): {exc}"
                    ),
                    stdout=_truncate_subprocess_output(proc.stdout),
                    stderr=_truncate_subprocess_output(proc.stderr),
                ),
                call_id=call_id,
                input_id=input_id,
            )

        try:
            validate_remote_correctness_payload(child_payload)
        except Exception as exc:
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type="SubprocessResultSchemaError",
                    error_msg=str(exc),
                    stdout=_truncate_subprocess_output(proc.stdout),
                    stderr=_truncate_subprocess_output(proc.stderr),
                    traceback_text=traceback.format_exc(),
                ),
                call_id=call_id,
                input_id=input_id,
            )

        if proc.returncode != 0 and (
            child_payload.get("correctness_status") != INFRASTRUCTURE_FAILURE_STATUS
        ):
            return _with_modal_context(
                build_infrastructure_failure_payload(
                    request,
                    error_type="SubprocessNonZeroExit",
                    error_msg=(
                        "correctness_runner exited nonzero without an "
                        "infrastructure payload"
                    ),
                    stdout=_truncate_subprocess_output(proc.stdout),
                    stderr=_truncate_subprocess_output(proc.stderr),
                ),
                call_id=call_id,
                input_id=input_id,
            )

        return _with_modal_context(child_payload, call_id=call_id, input_id=input_id)


def correctness_surface_metadata() -> C2ModalSurfaceMetadata:
    """Return metadata for the isolated C2 correctness surface."""

    return modal_surface_metadata()


@app.local_entrypoint()
def smoke_remote_correctness() -> None:
    """Run a minimal remote correctness smoke on L4."""

    identity = EvalIdentity(
        run_id="phase6-smoke",
        condition="C",
        source_class="generated_row",
        generation_mode="new_c2_generation",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        sample_index=0,
        base_seed=123,
        attempt_index=0,
    )
    request = RemoteCorrectnessRequest(
        identity=identity,
        source=(
            "import torch\n\n"
            "def relu(x: torch.Tensor) -> torch.Tensor:\n"
            "    return torch.relu(x)\n"
        ),
    )
    result = remote_c2_correctness.remote(request.model_dump())
    print(json.dumps(result, sort_keys=True))


def _with_modal_context(
    payload: dict[str, Any],
    *,
    call_id: str | None,
    input_id: str | None,
) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["modal_context"] = {
        "function_call_id": call_id,
        "input_id": input_id,
        "modal_eval_gpu": REMOTE_CORRECTNESS_EVAL_GPU,
    }
    validate_remote_correctness_payload(enriched)
    return enriched


def _truncate_subprocess_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    return truncate_output(output)
