"""Remote compile-only Modal function for the TritonGen GPU harness.

Validates generated Triton source by running ``check_compiles_all_dtypes``
inside a subprocess on a Modal GPU container. Compile errors are returned
as result fields — they are never used as control signals (no repair loop,
no prompt feedback, no retry).

Cluster boundary: this module must not introduce timing, profiling, numerical
correctness, or repair logic. Cluster 2/3 will add their own remote functions
in separate modules.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import traceback
from pathlib import Path

import modal

from shared.modal_harness.app import app
from shared.modal_harness.errors import truncate_output
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.schemas import RemoteCompileRequest, RemoteCompileResult


@app.function(
    image=triton_compile_image,
    gpu="L4",
    memory=24576,
    cpu=4.0,
    timeout=300,
    max_containers=20,
    min_containers=0,
    scaledown_window=120,
)
def remote_compile_only(req_dict: dict) -> dict:
    """Compile-only validation entrypoint.

    Returns ``RemoteCompileResult.model_dump()``. Errors are captured in
    result fields rather than raised, so the caller never has to wrap this
    in a try/except for routine compile failures.
    """
    req = RemoteCompileRequest(**req_dict)

    call_id: str | None
    input_id: str | None
    try:
        call_id = modal.current_function_call_id()
    except Exception:
        call_id = None
    try:
        input_id = modal.current_input_id()
    except Exception:
        input_id = None

    with tempfile.TemporaryDirectory() as tmpdir:
        request_file = Path(tmpdir) / "request.json"
        request_file.write_text(json.dumps(req.model_dump()))

        try:
            proc = subprocess.run(
                [
                    "python",
                    "-m",
                    "shared.modal_harness.compile_runner",
                    str(request_file),
                ],
                capture_output=True,
                text=True,
                timeout=req.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            result = RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={},
                compile_error_type="TimeoutError",
                compile_error_msg=f"compile subprocess timed out after {req.timeout_s}s",
                n_shapes_tested=0,
                stdout=truncate_output(exc.stdout or ""),
                stderr=truncate_output(exc.stderr or ""),
                run_id=req.run_id,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            )
            return result.model_dump()
        except Exception as exc:
            result = RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={},
                compile_error_type="UnknownError",
                compile_error_msg=str(exc),
                n_shapes_tested=0,
                traceback=traceback.format_exc(),
                run_id=req.run_id,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            )
            return result.model_dump()

        stdout = truncate_output(proc.stdout)
        stderr = truncate_output(proc.stderr)

        try:
            child_payload = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            result = RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={},
                compile_error_type="UnknownError",
                compile_error_msg=(
                    f"compile_runner produced no JSON (exit={proc.returncode})"
                ),
                n_shapes_tested=0,
                stdout=stdout,
                stderr=stderr,
                run_id=req.run_id,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            )
            return result.model_dump()

        result = RemoteCompileResult(
            compile_success=bool(child_payload.get("compile_success", False)),
            compile_results_by_dtype=dict(
                child_payload.get("compile_results_by_dtype", {})
            ),
            compile_error_type=child_payload.get("compile_error_type"),
            compile_error_msg=child_payload.get("compile_error_msg"),
            n_shapes_tested=int(child_payload.get("n_shapes_tested", 0)),
            stdout=stdout,
            stderr=stderr,
            traceback=child_payload.get("traceback"),
            run_id=req.run_id,
            modal_function_call_id=call_id,
            modal_input_id=input_id,
            metadata={
                "subprocess_returncode": proc.returncode,
                "modal_app_name": "tritongen-gpu-harness",
            },
        )
        return result.model_dump()
