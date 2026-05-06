"""Cluster 1 adapter for the shared remote compile-only function.

Thin wrapper so cluster code does not import Modal directly. The shared
harness owns the ``modal.App`` and the function decorator; this adapter just
constructs the request and converts the ``dict`` result back into the typed
``RemoteCompileResult``.
"""

from __future__ import annotations

from shared.modal_harness.compile import remote_compile_only
from shared.modal_harness.schemas import RemoteCompileRequest, RemoteCompileResult


def check_compiles_modal(
    *,
    source: str,
    kernel_class: str,
    kernel_name: str,
    factor_cell: str,
    run_id: str,
    timeout_s: int = 180,
) -> RemoteCompileResult:
    """Run compile-only validation on Modal and return a typed result.

    Cluster 1 boundary: the caller must not feed ``compile_error_msg`` back
    into prompt construction or trigger a regeneration based on a non-success
    outcome. Compile errors are result fields only.
    """
    req = RemoteCompileRequest(
        factor_cell=factor_cell,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        source=source,
        run_id=run_id,
        timeout_s=timeout_s,
    )
    result_dict = remote_compile_only.remote(req.model_dump())
    return RemoteCompileResult(**result_dict)
