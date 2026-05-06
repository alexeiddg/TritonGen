"""Smoke entrypoints for the TritonGen Modal harness.

Run with::

    modal run -m shared.modal_harness.smoke --case import-only
    modal run -m shared.modal_harness.smoke --case good-relu-compile
    modal run -m shared.modal_harness.smoke --case bad-triton-compile

The ``import-only`` case verifies the compile image can be built and that the
local ``cluster1`` and ``shared`` packages were copied into the container.
The compile cases additionally exercise ``remote_compile_only`` end-to-end
on an L4 GPU.
"""

from __future__ import annotations

from shared.modal_harness.app import app
from shared.modal_harness.compile import remote_compile_only
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.schemas import RemoteCompileRequest

# A minimal but real Triton kernel matching the locked KernelBench ReLU
# signature ``relu(x: torch.Tensor) -> torch.Tensor``. Annotations match the
# canonical reference signature exactly so ``validate_signature`` passes.
GOOD_RELU_SOURCE = '''\
import torch
import triton
import triton.language as tl


@triton.jit
def relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)


def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 256
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
'''


# Triton source that imports cleanly and matches the launcher signature, but
# fails at JIT compile time because ``tl.dot`` requires 2D operands. Used to
# confirm the bad path returns ``compile_success=False`` with a structured
# error type.
BAD_TRITON_SOURCE = '''\
import torch
import triton
import triton.language as tl


@triton.jit
def bad_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    x = tl.load(x_ptr + offsets)
    # tl.dot on a 1D tensor is rejected at compile time.
    bogus = tl.dot(x, x)
    tl.store(out_ptr + offsets, bogus)


def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    bad_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
'''


@app.function(image=triton_compile_image)
def import_smoke() -> dict:
    """Confirm cluster1/shared packages are importable inside the container."""
    import cluster1  # noqa: F401
    import shared  # noqa: F401

    return {"cluster1": True, "shared": True}


def _print_compile_outcome(label: str, result: dict, *, expect_success: bool) -> None:
    success = bool(result.get("compile_success"))
    error_type = result.get("compile_error_type")
    error_msg = result.get("compile_error_msg")
    print(
        f"{label}: compile_success={success} "
        f"error_type={error_type} run_id={result.get('run_id')}"
    )
    if expect_success and not success:
        print(f"UNEXPECTED FAILURE: {error_type}: {error_msg}")
    elif not expect_success and success:
        print("UNEXPECTED SUCCESS: source should not have compiled")
    elif expect_success and success:
        print(f"✓ {label}: compiled successfully")
    else:
        print(f"✓ {label}: failed as expected with {error_type}")


@app.local_entrypoint()
def main(case: str = "import-only") -> None:
    if case == "import-only":
        result = import_smoke.remote()
        print(f"Import smoke passed: {result}")
        return

    if case == "good-relu-compile":
        req = RemoteCompileRequest(
            factor_cell="none",
            kernel_class="elementwise",
            kernel_name="relu",
            source=GOOD_RELU_SOURCE,
            run_id="smoke-good-relu",
        )
        result = remote_compile_only.remote(req.model_dump())
        _print_compile_outcome("good-relu-compile", result, expect_success=True)
        return

    if case == "bad-triton-compile":
        req = RemoteCompileRequest(
            factor_cell="none",
            kernel_class="elementwise",
            kernel_name="relu",
            source=BAD_TRITON_SOURCE,
            run_id="smoke-bad-triton",
        )
        result = remote_compile_only.remote(req.model_dump())
        _print_compile_outcome("bad-triton-compile", result, expect_success=False)
        return

    print(f"Unknown case: {case}")
    print("Available cases: import-only, good-relu-compile, bad-triton-compile")
