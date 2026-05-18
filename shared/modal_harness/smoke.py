"""Smoke entrypoints for the TritonGen Modal harness.

Run with::

    modal run -m shared.modal_harness.smoke --case import-only
    modal run -m shared.modal_harness.smoke --case good-relu-compile
    modal run -m shared.modal_harness.smoke --case bad-triton-compile
    modal run -m shared.modal_harness.smoke --case generate-baseline-one
    modal run -m shared.modal_harness.smoke --case generate-g-one

The ``import-only`` case verifies the compile image can be built and that the
local ``cluster1``, ``cluster2``, and ``shared`` packages were copied into the
container.
The compile cases additionally exercise ``remote_compile_only`` end-to-end
on an L4 GPU. The generation cases exercise one baseline and one grammar-active
model call.
"""

from __future__ import annotations

from cluster1.data.kernels import get_kernel_spec
from cluster1.data.prompts.prompt_contract import build_prompt
from cluster1.generation.modal_generate import generate_source_modal
from shared.modal_harness.app import app
from shared.modal_harness.compile import remote_compile_only
from shared.modal_harness.images import triton_compile_image
from shared.modal_harness.schemas import RemoteCompileRequest

DEFAULT_GENERATION_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
# Qwen tokenizer measurements for canonical Cluster 1 modules:
# relu=199, softmax=240, matmul=487. Keep the smoke below the evaluation
# default of 1024 while still allowing a complete canonical module.
GENERATION_SMOKE_MAX_NEW_TOKENS = 512

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
    """Confirm project packages are importable inside the container."""
    import cluster1  # noqa: F401
    import cluster2  # noqa: F401
    import shared  # noqa: F401

    return {"cluster1": True, "cluster2": True, "shared": True}


def _classify_remote_exception(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "image" in text or "build" in text:
        return "image build"
    if "gpu" in text or "quota" in text or "capacity" in text or "allocation" in text:
        return "GPU allocation"
    return f"unknown ({type(exc).__name__})"


def _classify_compile_failure(result: dict) -> str:
    text = " ".join(
        str(result.get(key) or "")
        for key in (
            "compile_error_type",
            "compile_error_msg",
            "stdout",
            "stderr",
            "traceback",
        )
    ).lower()
    if "no module named 'triton'" in text or 'no module named "triton"' in text:
        return "Triton import"
    if "import triton" in text or "triton import failed" in text:
        return "Triton import"
    if "cuda is not available" in text or "torch not compiled with cuda" in text:
        return "CUDA availability"
    if "no nvidia driver" in text or "no cuda-capable device" in text:
        return "CUDA availability"
    if "cuda error" in text and ("device" in text or "driver" in text):
        return "CUDA availability"
    return "Triton JIT compile"


def _print_compile_outcome(label: str, result: dict, *, expect_success: bool) -> bool:
    success = bool(result.get("compile_success"))
    error_type = result.get("compile_error_type")
    error_msg = result.get("compile_error_msg")
    print(
        f"{label}: compile_success={success} "
        f"error_type={error_type} run_id={result.get('run_id')}"
    )
    if expect_success and not success:
        category = _classify_compile_failure(result)
        print(f"UNEXPECTED FAILURE: category={category} {error_type}: {error_msg}")
        return False
    elif not expect_success and success:
        print("UNEXPECTED SUCCESS: source should not have compiled")
        return False
    elif expect_success and success:
        print(f"✓ {label}: compiled successfully")
    else:
        print(f"✓ {label}: failed as expected with {error_type}")
    return True


def _run_compile_smoke(
    label: str,
    req: RemoteCompileRequest,
    *,
    expect_success: bool,
) -> None:
    try:
        result = remote_compile_only.remote(req.model_dump())
    except Exception as exc:
        category = _classify_remote_exception(exc)
        print(f"{label}: remote call failed category={category} error={type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc

    ok = _print_compile_outcome(label, result, expect_success=expect_success)
    if not ok:
        raise SystemExit(1)


def _print_generation_outcome(label: str, result, *, expect_grammar: bool) -> bool:
    source = result.source or ""
    masked_rate = result.masked_token_rate
    print(
        f"{label}: source_chars={len(source)} "
        f"grammar_active={result.grammar_active} "
        f"masked_token_rate={masked_rate} run_id={result.run_id}"
    )
    if not source.strip():
        print("UNEXPECTED EMPTY SOURCE")
        return False
    if result.grammar_active != expect_grammar:
        print("UNEXPECTED GRAMMAR FLAG")
        return False
    if expect_grammar and masked_rate is None:
        print("UNEXPECTED MASKED RATE: expected non-null")
        return False
    if not expect_grammar and masked_rate is not None:
        print("UNEXPECTED MASKED RATE: expected null")
        return False
    print(f"✓ {label}: generated source")
    return True


def _run_generation_smoke(label: str, *, grammar_active: bool) -> None:
    spec = get_kernel_spec("elementwise")
    dtype = "fp32"
    prompt = build_prompt(spec, dtype)
    try:
        result = generate_source_modal(
            prompt=prompt,
            model_id=DEFAULT_GENERATION_MODEL_ID,
            kernel_class=spec.kernel_class,
            kernel_name=spec.name,
            dtype=dtype,
            grammar_active=grammar_active,
            generation_seed=0,
            temperature=0.2,
            max_new_tokens=GENERATION_SMOKE_MAX_NEW_TOKENS,
            run_id=f"smoke-{label}",
        )
    except Exception as exc:
        category = _classify_remote_exception(exc)
        print(f"{label}: remote call failed category={category} error={type(exc).__name__}: {exc}")
        raise SystemExit(1) from exc

    ok = _print_generation_outcome(label, result, expect_grammar=grammar_active)
    if not ok:
        raise SystemExit(1)


@app.local_entrypoint()
def main(case: str = "import-only") -> None:
    if case == "import-only":
        try:
            result = import_smoke.remote()
        except Exception as exc:
            category = _classify_remote_exception(exc)
            print(
                f"import-only failed category={category} "
                f"error={type(exc).__name__}: {exc}"
            )
            raise SystemExit(1) from exc
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
        _run_compile_smoke("good-relu-compile", req, expect_success=True)
        return

    if case == "bad-triton-compile":
        req = RemoteCompileRequest(
            factor_cell="none",
            kernel_class="elementwise",
            kernel_name="relu",
            source=BAD_TRITON_SOURCE,
            run_id="smoke-bad-triton",
        )
        _run_compile_smoke("bad-triton-compile", req, expect_success=False)
        return

    if case == "generate-baseline-one":
        _run_generation_smoke("generate-baseline-one", grammar_active=False)
        return

    if case == "generate-g-one":
        _run_generation_smoke("generate-g-one", grammar_active=True)
        return

    print(f"Unknown case: {case}")
    print(
        "Available cases: import-only, good-relu-compile, bad-triton-compile, "
        "generate-baseline-one, generate-g-one"
    )
