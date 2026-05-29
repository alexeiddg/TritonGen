Yes — Modal fits this pipeline, but design it as one shared GPU execution layer with cluster-specific adapters.

> **Current status note (2026-05-11):** This is an early draft/reference note.
> The active phased plan is
> `.contracts/agentic/post_cluster1_scope_and_execution_plan.md`, and the
> active Modal requirements reference is
> `.contracts/agentic/modal_integration_plan.md`. Ignore any
> RL or CUDA-source generation implications in this draft for core thesis
> scope; the project is Triton-only and inference-time only.

Core decision

Use Modal for all hardware-dependent stages:

Cluster 1: remote Triton compile gate only. No numerical correctness, no profiling, no repair loop.

Cluster 2: remote correctness tests and test-driven feedback repair.

Cluster 3: remote compiler/runtime feedback, profiling, bounded repair, and
batched evaluation after smoke and development scale are stable.

Modal supports explicit GPU selection via gpu=, including T4, L4, A10, L40S, A100, H100, H200, B200, etc.  ￼ It also supports autoscaling pools that scale to zero by default, with controls like max_containers, min_containers, buffer_containers, and scaledown_window.  ￼ For model weights, Modal recommends using Volumes as shared distributed storage mounted into functions.  ￼

Proposed repository shape

cluster_common/
  remote/
    __init__.py
    modal_app.py
    images.py
    schemas.py
    client.py
    gpu_compile.py
    gpu_correctness.py
    gpu_profile.py
    gpu_inference.py
    sandbox_runner.py
    security.py
    storage.py
    errors.py
cluster1/
  validation/
    compile_check.py              # local interface
    modal_compile_check.py        # calls cluster_common.remote
  experiments/
    run_compile_modal.py
cluster2/
  feedback/
    modal_feedback_loop.py
cluster3/
  profiling/
    modal_profile.py
    repair_loop.py

Do not put Modal directly inside every cluster. Put Modal in cluster_common/remote/, then expose narrow cluster-specific wrappers.

Shared Modal app

# cluster_common/remote/modal_app.py
import modal
app = modal.App("tritongen-gpu-harness")
triton_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "triton",
        "numpy",
        "pydantic",
    )
)
model_volume = modal.Volume.from_name("tritongen-model-cache", create_if_missing=True)
results_volume = modal.Volume.from_name("tritongen-results", create_if_missing=True)

Modal’s batch docs say large fanout jobs can scale to thousands of parallel containers, and .spawn_map is intended for asynchronous large batch submission.  ￼ That is useful later, but for Cluster 1 start with synchronous .remote() and small .map().

Unified schemas

Create one remote result schema that can expand across clusters:

# cluster_common/remote/schemas.py
from dataclasses import dataclass
from typing import Literal, Optional
ClusterMode = Literal[
    "compile_only",
    "correctness",
    "feedback",
    "profile",
    "inference",
]
@dataclass(frozen=True)
class RemoteKernelRequest:
    code: str
    kernel_class: str
    kernel_name: str
    dtype: str
    shapes: list[dict]
    mode: ClusterMode
    timeout_s: int = 30
    generation_id: Optional[str] = None
@dataclass(frozen=True)
class RemoteKernelResult:
    mode: ClusterMode
    compile_success: bool
    runtime_success: Optional[bool]
    correctness_success: Optional[bool]
    profile_success: Optional[bool]
    error_type: Optional[str]
    error_msg: Optional[str]
    stdout: str
    stderr: str
    traceback: Optional[str]
    metadata: dict

For Cluster 1, only these fields matter:

compile_success
error_type
error_msg
stdout
stderr
traceback
metadata

Everything else must stay None.

Cluster 1 Modal compile gate

Cluster 1 should call a Modal function that does exactly this:

1. Receive generated Triton code.
2. Write it to an isolated temp file.
3. Import or execute it inside a subprocess.
4. Build dummy CUDA tensors.
5. Launch the kernel once.
6. Return compile status.
7. Never call torch.allclose.
8. Never record timing.
9. Never profile.
10. Never retry or repair.

Use subprocess isolation because bad CUDA kernels can poison the process.

# cluster_common/remote/gpu_compile.py
import modal
from cluster_common.remote.modal_app import app, triton_image
from cluster_common.remote.schemas import RemoteKernelRequest, RemoteKernelResult
@app.function(
    image=triton_image,
    gpu="L4",
    timeout=120,
    max_containers=20,
)
def remote_compile_only(req: dict) -> dict:
    import json
    import subprocess
    import tempfile
    import textwrap
    import traceback
    request = RemoteKernelRequest(**req)
    runner = f"""
import torch
import triton
import triton.language as tl
import traceback
USER_CODE = {request.code!r}
namespace = {{}}
try:
    exec(USER_CODE, namespace, namespace)
    # Cluster 1 dummy launch only.
    # Adapter must locate wrapper/kernel by known name contract.
    fn = namespace.get("{request.kernel_name}")
    if fn is None:
        raise RuntimeError("Generated kernel function not found: {request.kernel_name}")
    # TODO: replace with KernelSpec-specific dummy launch adapter.
    # Example placeholder:
    x = torch.randn((1024,), device="cuda", dtype=torch.float32)
    y = torch.empty_like(x)
    # Expected wrapper contract should call Triton kernel.
    fn(x, y, 1024)
    torch.cuda.synchronize()
    print("COMPILE_SUCCESS")
except Exception:
    print("COMPILE_FAILURE")
    traceback.print_exc()
    raise
"""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(runner)
            path = f.name
        proc = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=request.timeout_s,
        )
        success = proc.returncode == 0 and "COMPILE_SUCCESS" in proc.stdout
        return RemoteKernelResult(
            mode="compile_only",
            compile_success=success,
            runtime_success=None,
            correctness_success=None,
            profile_success=None,
            error_type=None if success else "triton_jit_error",
            error_msg=None if success else proc.stderr[-4000:],
            stdout=proc.stdout[-4000:],
            stderr=proc.stderr[-4000:],
            traceback=None if success else proc.stderr[-4000:],
            metadata={"returncode": proc.returncode},
        ).__dict__
    except subprocess.TimeoutExpired as e:
        return RemoteKernelResult(
            mode="compile_only",
            compile_success=False,
            runtime_success=None,
            correctness_success=None,
            profile_success=None,
            error_type="timeout",
            error_msg=str(e),
            stdout=e.stdout or "",
            stderr=e.stderr or "",
            traceback=None,
            metadata={},
        ).__dict__
    except Exception as e:
        return RemoteKernelResult(
            mode="compile_only",
            compile_success=False,
            runtime_success=None,
            correctness_success=None,
            profile_success=None,
            error_type="harness_error",
            error_msg=str(e),
            stdout="",
            stderr="",
            traceback=traceback.format_exc(),
            metadata={},
        ).__dict__

Modal Sandboxes are also relevant later because they support command execution with stdout, stderr, stdin, and command timeouts.  ￼ For Cluster 1, subprocess inside a normal GPU function is simpler. Move to Sandboxes only when you need stronger isolation for arbitrary generated code.

Local Cluster 1 adapter

# cluster1/validation/modal_compile_check.py
from cluster_common.remote.gpu_compile import remote_compile_only
from cluster_common.remote.schemas import RemoteKernelRequest
def compile_check_remote(
    code: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    shapes: list[dict],
) -> dict:
    req = RemoteKernelRequest(
        code=code,
        kernel_class=kernel_class,
        kernel_name=kernel_name,
        dtype=dtype,
        shapes=shapes,
        mode="compile_only",
    )
    return remote_compile_only.remote(req.__dict__)

Your existing local compile_check.py should remain the stable interface. Add a backend switch:

def compile_check(..., backend: str = "local"):
    if backend == "local":
        return compile_check_local(...)
    if backend == "modal":
        return compile_check_remote(...)
    raise ValueError(f"Unknown backend: {backend}")

Minimal first milestone

Implement only this first:

modal run cluster1/experiments/run_compile_modal.py

It should take one known-good ReLU Triton fixture, send it to Modal, run dummy JIT launch on GPU, and return:

{
  "compile_success": true,
  "error_type": null,
  "mode": "compile_only"
}

Then test one known-bad kernel and verify:

{
  "compile_success": false,
  "error_type": "triton_jit_error"
}

Cluster expansion plan

Phase M0 — Modal setup

Install and authenticate:

pip install modal
python -m modal setup

Create:

cluster_common/remote/
cluster1/validation/modal_compile_check.py
cluster1/experiments/run_compile_modal.py

Do not touch profiling or feedback yet.

Phase M1 — shared image

Build one image with pinned versions:

modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch==...",
    "triton==...",
    "numpy",
    "pydantic",
)

Pin exact versions once your local tests pass.

Phase M2 — Cluster 1 compile-only remote backend

Add backend="modal" to your compile gate.

Hard boundary:

No allclose.
No torch.testing.
No timing.
No profiler.
No repair loop.
No retry loop.
No performance score.

Phase M3 — batch compile evaluation

Use Modal .map() for pass@k cells:

results = list(remote_compile_only.map([req.__dict__ for req in requests]))

Keep n >= 20 per (kernel_class, grammar_active) cell.

Phase M4 — model inference offload

Add a separate Modal class/function for model loading. Store weights in a Modal Volume because Modal recommends Volumes for model weights and shared access across functions.  ￼

Target:

generate.remote(prompt, grammar_active=True)
compile.remote(code)

Later:

generate.map(prompts)
compile.map(codes)

Phase M5 — Cluster 2 correctness and feedback

Add new mode:

mode="correctness"

Only Cluster 2 may call:

torch.allclose(...)
torch.testing.assert_close(...)

Add compiler feedback extraction:

shape mismatch
NaN/Inf output
max absolute error
max relative error
allclose failure summary

Phase M6 — Cluster 3 compiler/profiler repair

Add profiling only outside Cluster 1:

torch.cuda.Event
triton.testing.do_bench
Nsight/NVML only if explicitly part of later cluster contract

Phase M7 — Paper-scale batch controls

After smoke and development scale are stable, fan out candidate kernels through
Modal batch execution. Modal batch processing is designed for large-scale
parallel jobs and asynchronous submission.  ￼

GPU selection

Use this default policy:

Cluster 1 compile gate: L4 or A10
Cluster 2 correctness: L40S or A100
Cluster 3 profiling: L40S or A100
Model inference 7B AWQ: L40S, A100-40GB, A100-80GB
Paper-scale batch evaluation: L40S/A100 fanout only after development scale is stable

Modal supports specific GPU selection through the gpu argument.  ￼ Start with gpu="L4" for compile-only to control cost.

Important correction to your draft

For Cluster 1, do not implement the “compiler feedback loop” as an experimental behavior. You may capture compiler errors for logging, but you must not feed them back into a repair/retry loop. Compiler-specific repair belongs to Cluster 3 in the current scope.

So the correct Cluster 1 wording is:

Modal remote execution is used only to obtain real GPU-backed Triton JIT compile acceptance. Compiler stderr may be logged as metadata, but no repair, retry, correctness validation, profiling, or performance scoring is performed in Cluster 1.

Implementation order

Start here:

1. Add cluster_common/remote/modal_app.py
2. Add cluster_common/remote/schemas.py
3. Add cluster_common/remote/gpu_compile.py
4. Add cluster1/validation/modal_compile_check.py
5. Add backend="modal" option to existing compile_check interface
6. Add one good and one bad Modal smoke test
7. Add batch pass@k runner using remote_compile_only.map()
8. Freeze Cluster 1 boundary tests
9. Only then add model-serving Modal functions
10. Only then add feedback/profiling modes

This gives you the right architecture: one reusable Modal harness, Cluster 1 kept contract-clean, and later clusters can progressively enable correctness, compiler/profiler repair, profiling, and model inference without rewriting the execution layer.
