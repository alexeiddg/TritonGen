"""Subprocess child for remote Triton compile validation.

Runs inside the Modal container, isolated from the parent function. A bad
Triton/CUDA launch can corrupt CUDA state in the calling process; running
the compile in a fresh Python process means the parent can recover and
return a structured failure even when the child crashes hard.

CLI::

    python -m shared.modal_harness.compile_runner <request_path> <result_path>

The child reads ``RemoteCompileRequest`` JSON from ``request_path``,
dispatches into the existing ``cluster1.validation.compile_check`` (no
duplication of compile semantics), and writes exactly one JSON document to
``result_path``. ``stdout`` and ``stderr`` remain diagnostics only — the
parent captures them for debugging but never parses them.

This module does not import ``modal`` — it must run as a plain Python
subprocess inside the container.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def _write_result(result_path: Path, payload: dict) -> None:
    result_path.write_text(json.dumps(payload), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write(
            "compile_runner expects exactly two argv: <request_path> <result_path>\n"
        )
        sys.exit(2)

    request_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])
    try:
        request_data = json.loads(request_path.read_text())
    except Exception as exc:
        _write_result(
            result_path,
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"failed to read request file: {exc}",
                "failure_code": "F1_RUNTIME",
                "n_shapes_tested": 0,
            },
        )
        sys.exit(2)

    # Imports inside main() so a missing torch/triton in the parent does not
    # crash the runner before it can return a structured error.
    try:
        from cluster1.data.kernels import get_kernel_spec
        from shared.eval.failure_taxonomy import (
            canonical_failure_code_from_compile_error,
        )
        from cluster1.validation.compile_check import check_compiles_all_dtypes
    except Exception as exc:
        _write_result(
            result_path,
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"cluster1 import failed: {exc}",
                "failure_code": "F1_RUNTIME",
                "n_shapes_tested": 0,
                "traceback": traceback.format_exc(),
            },
        )
        sys.exit(2)

    kernel_class = request_data["kernel_class"]
    kernel_name = request_data["kernel_name"]
    source = request_data["source"]

    try:
        spec = get_kernel_spec(kernel_class)
    except KeyError as exc:
        _write_result(
            result_path,
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "SignatureError",
                "compile_error_msg": str(exc),
                "failure_code": "F0_BAD_SIGNATURE",
                "n_shapes_tested": 0,
            },
        )
        return

    if kernel_name != spec.name:
        _write_result(
            result_path,
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "SignatureError",
                "compile_error_msg": (
                    f"kernel_name mismatch: spec for {kernel_class!r} expects "
                    f"{spec.name!r}, got {kernel_name!r}"
                ),
                "failure_code": "F0_BAD_SIGNATURE",
                "n_shapes_tested": 0,
            },
        )
        return

    try:
        compile_results = check_compiles_all_dtypes(
            source,
            spec.compile_spec,
            spec.shapes_by_dtype,
        )
    except Exception as exc:
        _write_result(
            result_path,
            {
                "compile_success": False,
                "compile_results_by_dtype": {},
                "compile_error_type": "UnknownError",
                "compile_error_msg": f"check_compiles_all_dtypes raised: {exc}",
                "failure_code": "F1_RUNTIME",
                "n_shapes_tested": 0,
                "traceback": traceback.format_exc(),
            },
        )
        sys.exit(2)

    compile_success = all(r.success for r in compile_results)
    compile_results_by_dtype = {r.dtype: r.success for r in compile_results}
    # first_error reflects the first failing dtype only; per-dtype booleans live in compile_results_by_dtype.
    first_error = next((r for r in compile_results if r.error_type is not None), None)
    n_shapes_tested = sum(r.n_shapes_tested for r in compile_results)

    _write_result(
        result_path,
        {
            "compile_success": compile_success,
            "compile_results_by_dtype": compile_results_by_dtype,
            "compile_error_type": first_error.error_type if first_error else None,
            "compile_error_msg": first_error.error_msg if first_error else None,
            "failure_code": (
                first_error.failure_code
                if first_error and first_error.failure_code is not None
                else canonical_failure_code_from_compile_error(
                    first_error.error_type if first_error else None,
                    first_error.error_msg if first_error else None,
                )
            ),
            "n_shapes_tested": n_shapes_tested,
        },
    )


if __name__ == "__main__":
    main()
