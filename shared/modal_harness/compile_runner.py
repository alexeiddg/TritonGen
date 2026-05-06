"""Subprocess child for remote Triton compile validation.

Runs inside the Modal container, isolated from the parent function. A bad
Triton/CUDA launch can corrupt CUDA state in the calling process; running
the compile in a fresh Python process means the parent can recover and
return a structured failure even when the child crashes hard.

Reads a JSON request from a path argv, dispatches into the existing
``cluster1.validation.compile_check`` (no duplication of compile semantics),
and emits a single JSON document on stdout. The parent parses that JSON.

This module does not import ``modal`` — it must run as a plain Python
subprocess inside the container.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main() -> None:
    if len(sys.argv) != 2:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": "compile_runner expects exactly one argv: <request_json_path>",
                "n_shapes_tested": 0,
            }
        )
        sys.exit(2)

    request_path = Path(sys.argv[1])
    try:
        request_data = json.loads(request_path.read_text())
    except Exception as exc:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"failed to read request file: {exc}",
                "n_shapes_tested": 0,
            }
        )
        sys.exit(2)

    # Imports inside main() so a missing torch/triton in the parent does not
    # crash the runner before it can return a structured error.
    try:
        from cluster1.data.kernels import get_kernel_spec
        from cluster1.validation.compile_check import check_compiles_all_dtypes
    except Exception as exc:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"cluster1 import failed: {exc}",
                "n_shapes_tested": 0,
                "traceback": traceback.format_exc(),
            }
        )
        sys.exit(2)

    kernel_class = request_data["kernel_class"]
    kernel_name = request_data["kernel_name"]
    source = request_data["source"]

    try:
        spec = get_kernel_spec(kernel_class)
    except KeyError as exc:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "SignatureError",
                "compile_error_msg": str(exc),
                "n_shapes_tested": 0,
            }
        )
        return

    if kernel_name != spec.name:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "SignatureError",
                "compile_error_msg": (
                    f"kernel_name mismatch: spec for {kernel_class!r} expects "
                    f"{spec.name!r}, got {kernel_name!r}"
                ),
                "n_shapes_tested": 0,
            }
        )
        return

    try:
        compile_results = check_compiles_all_dtypes(
            source,
            spec.compile_spec,
            spec.shapes_by_dtype,
        )
    except Exception as exc:
        _emit(
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"check_compiles_all_dtypes raised: {exc}",
                "n_shapes_tested": 0,
                "traceback": traceback.format_exc(),
            }
        )
        sys.exit(2)

    compile_success = all(r.success for r in compile_results)
    compile_results_by_dtype = {r.dtype: r.success for r in compile_results}
    first_error = next((r for r in compile_results if r.error_type is not None), None)
    n_shapes_tested = sum(r.n_shapes_tested for r in compile_results)

    _emit(
        {
            "compile_success": compile_success,
            "compile_results_by_dtype": compile_results_by_dtype,
            "compile_error_type": first_error.error_type if first_error else None,
            "compile_error_msg": first_error.error_msg if first_error else None,
            "n_shapes_tested": n_shapes_tested,
        }
    )


if __name__ == "__main__":
    main()
