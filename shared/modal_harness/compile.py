"""Remote compile-only Modal function for the TritonGen GPU harness.

Validates generated Triton source by running ``check_compiles_all_dtypes``
inside a subprocess on a Modal GPU container. Compile errors are returned
as result fields — they are never used as control signals (no repair loop,
no prompt feedback, no retry).

The child's structured result is read from a result file (not parsed from
stdout) so stray ``print()``/warning output from torch, triton, or
transformers cannot corrupt the JSON.

Cluster boundary: this module must not introduce timing, profiling, numerical
correctness, or repair logic. Cluster 2/3 will add their own remote functions
in separate modules.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from shared.modal_harness.app import app
from shared.modal_harness.errors import truncate_output
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.runtime import current_modal_ids
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
    return _run_remote_compile(req_dict)


def _run_remote_compile(req_dict: dict) -> dict:
    """Pure-Python implementation of ``remote_compile_only`` for testability."""
    req = RemoteCompileRequest(**req_dict)
    call_id, input_id = current_modal_ids()

    with tempfile.TemporaryDirectory() as tmpdir:
        request_file = Path(tmpdir) / "request.json"
        result_file = Path(tmpdir) / "result.json"
        request_file.write_text(json.dumps(req.model_dump()))

        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.modal_harness.compile_runner",
                    str(request_file),
                    str(result_file),
                ],
                capture_output=True,
                text=True,
                timeout=req.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            return RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
                compile_error_type="TimeoutError",
                compile_error_msg=f"compile subprocess timed out after {req.timeout_s}s",
                failure_code="F1_RUNTIME",
                n_shapes_tested=0,
                stdout=truncate_output(exc.stdout or ""),
                stderr=truncate_output(exc.stderr or ""),
                run_id=req.run_id,
                factor_cell=req.factor_cell,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            ).model_dump()
        except Exception as exc:
            return RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
                compile_error_type="UnknownError",
                compile_error_msg=str(exc),
                failure_code="F1_RUNTIME",
                n_shapes_tested=0,
                traceback=traceback.format_exc(),
                run_id=req.run_id,
                factor_cell=req.factor_cell,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            ).model_dump()

        stderr = truncate_output(proc.stderr)

        try:
            child_payload = json.loads(result_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
                compile_error_type="UnknownError",
                compile_error_msg=(
                    f"compile_runner did not produce a result file (exit={proc.returncode})"
                ),
                failure_code="F1_RUNTIME",
                n_shapes_tested=0,
                stdout=truncate_output(proc.stdout),
                stderr=stderr,
                run_id=req.run_id,
                factor_cell=req.factor_cell,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            ).model_dump()
        except json.JSONDecodeError as exc:
            return RemoteCompileResult(
                compile_success=False,
                compile_results_by_dtype={"fp32": False, "fp16": False, "bf16": False},
                compile_error_type="UnknownError",
                compile_error_msg=(
                    f"compile_runner result file was not valid JSON (exit="
                    f"{proc.returncode}): {exc}"
                ),
                failure_code="F1_RUNTIME",
                n_shapes_tested=0,
                stdout=truncate_output(proc.stdout),
                stderr=stderr,
                run_id=req.run_id,
                factor_cell=req.factor_cell,
                modal_function_call_id=call_id,
                modal_input_id=input_id,
            ).model_dump()

        return RemoteCompileResult(
            compile_success=bool(child_payload.get("compile_success", False)),
            compile_results_by_dtype=dict(
                child_payload.get("compile_results_by_dtype", {})
            ),
            compile_error_type=child_payload.get("compile_error_type"),
            compile_error_msg=child_payload.get("compile_error_msg"),
            failure_code=child_payload.get("failure_code"),
            n_shapes_tested=int(child_payload.get("n_shapes_tested", 0)),
            stdout="",
            stderr=stderr,
            traceback=child_payload.get("traceback"),
            run_id=req.run_id,
            factor_cell=req.factor_cell,
            modal_function_call_id=call_id,
            modal_input_id=input_id,
            metadata={
                "subprocess_returncode": proc.returncode,
                "modal_app_name": "tritongen-gpu-harness",
            },
        ).model_dump()
