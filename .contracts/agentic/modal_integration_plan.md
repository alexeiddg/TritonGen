# Modal Integration Plan

> **Current status note (2026-05-11):** The Cluster 1 Modal harness described
> here has largely been implemented under `shared/modal_harness/` and exercised
> by the frozen Cluster 1 run. Treat this file as the Modal requirements and
> design reference. The phased next-step execution plan for Cluster 2/3
> integration lives in
> `.contracts/agentic/post_cluster1_scope_and_execution_plan.md`.
> Do not add C/P behavior to Cluster 1 adapters just because reserved schemas
> appear in this document.

## Purpose

This plan turns Modal into the shared remote execution layer for TritonGen.
The goal is not to make a Cluster 1-only Modal script. The goal is to add one
reusable GPU harness that Cluster 1, Cluster 2, and Cluster 3 can all call while
preserving each cluster boundary.

Immediate implementation scope:

- Run the no-control baseline condition remotely. This is the factorial empty
  cell: no grammar, no test-driven feedback, no compiler/profiler repair, no
  RL. Modal is only infrastructure for model loading, generation, and compile
  acceptance.
- Run the Cluster 1 G condition remotely. This enables grammar-constrained
  decoding, then performs compile acceptance only.
- Defer model loading, model generation, Triton JIT compilation, and GPU tensor
  dummy launches to Modal.

Out of immediate scope:

- Corrective-feedback repair loops.
- Numerical correctness checks.
- Profiling, benchmarking, timings, speedups, Nsight, NVML, or performance
  scoring.
- RL rollouts or training.
- Multi-node or multi-GPU training.
- Web endpoints.

Important Cluster 1 boundary: Modal may capture compile stderr for logging, but
Cluster 1 must not feed it back to the model. A compile error is a result field,
not a control signal.

## Direct Decisions

### Do I create a Modal workspace manually?

The Modal workspace for this project is `tritongen-lab`.

Do not use the workspace's default `main` environment for active TritonGen
experiments. Keep `main` clean as the bootstrap/scratch namespace and create a
dedicated development environment named `tritongen-dev`.

Reason: Modal Environments isolate apps, volumes, secrets, and object lookups
inside the same workspace. Using `tritongen-dev` now prevents early smoke-test
resources from being mixed with later stable thesis runs. Add
`tritongen-prod` only after the smoke tests and full Cluster 1 run are stable.

Recommended setup commands after creating `tritongen-lab`:

```bash
pip install modal
modal setup
modal profile activate tritongen-lab
modal environment create tritongen-dev
modal config set-environment tritongen-dev
```

If `modal profile activate tritongen-lab` fails because the local profile has a
different name than the workspace, run:

```bash
modal profile list
modal profile activate <profile-that-points-to-tritongen-lab>
modal config set-environment tritongen-dev
```

If you do not want to change the default environment for the active profile,
pass `--env tritongen-dev` to every `modal run`, `modal deploy`, and
`modal app logs` command instead. Setting the default is simpler for this repo.

### Do I create a container?

Yes, but not as a Dockerfile at first. Define Modal `Image` objects in Python.
That is the Modal-native container interface and keeps the harness versioned
with the code.

Use two images:

1. `triton_compile_image`: small image for Triton dummy launches.
2. `llm_generation_image`: heavier image for Hugging Face model loading,
   XGrammar, and generation.

Do not start with a custom Dockerfile. Use a Docker/CUDA registry image only if
`torch`, `triton`, `autoawq`, or another dependency fails because it needs a
system CUDA toolkit. Modal provides the GPU driver and CUDA Driver API on GPU
functions, so normal `torch` and `transformers` installs should work through
Python package installs.

Current Modal GPU names include `T4`, `L4`, `A10`, `L40S`, `A100`,
`A100-40GB`, `A100-80GB`, `H100`, `H200`, and `B200`. Use `A10`, not the older
`A10G` string.

### Do I need a notebook?

No. Do not implement or run the harness from a notebook.

Use normal Python modules plus `modal run` for reproducible execution. A
notebook is acceptable later for reading JSONL outputs and making figures, but
it should not own the Modal app, the experiment runner, or the harness logic.

Reason: notebooks add serialization and Python-version matching issues, and the
repo already has reproducible CLI runners under `cluster1/experiments/`.

### Should the app be deployed immediately?

No. Start with ephemeral apps through `modal run` until the smoke tests pass.
Deploy only after the harness contract is stable.

Development:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class elementwise \
  --n 1 \
  --output outputs/cluster1/modal_dev_smoke.jsonl
```

Stable repeated runs:

```bash
modal deploy -m shared.modal_harness.app
```

After deployment, local scripts can look up deployed functions/classes instead
of running an ephemeral app. That is useful later for long-running Cluster 2 and
Cluster 3 pipelines.

### Where should the code live?

Use the existing `shared/` package. Do not put Modal separately in every
cluster.

The draft proposed `cluster_common/remote/`, but this repository already uses
`shared/` for cross-cluster infrastructure. Put the harness here:

```text
shared/modal_harness/
  __init__.py
  app.py
  images.py
  volumes.py
  secrets.py
  schemas.py
  errors.py
  generation.py
  compile.py
  client.py
  logging.py
  smoke.py
```

Cluster-specific adapters live in cluster packages:

```text
cluster1/generation/modal_generate.py
cluster1/validation/modal_compile_check.py
cluster1/experiments/run_cluster1_modal.py
cluster1/tests/test_modal_harness_contract.py
```

Cluster 2 and Cluster 3 should later add adapters that call the same shared
harness instead of copying Modal app definitions.

## Modal Resources

### App

Use one shared app:

```python
app = modal.App("tritongen-gpu-harness")
```

This app groups the shared generation class and compile function. The functions
scale independently, so generation can use heavier GPUs while compile checks use
cheaper GPUs.

### Environments

Workspace:

- `tritongen-lab`

Use:

- `tritongen-dev` for smoke tests and development.
- `tritongen-prod` only after stable full runs.
- `main` only as a clean bootstrap/scratch environment; do not deploy the
  thesis harness there.

All resource lookups should rely on the active Modal Environment by default.
Do not hardcode environment names inside app code unless doing an explicit
cross-environment lookup.

### Current Modal Infra State

Recorded state as of 2026-05-06:

- Workspace `tritongen-lab` exists.
- Local Modal profile `tritongen-lab` is connected to workspace
  `tritongen-lab`.
- Web authentication completed successfully.
- Modal token verification against `https://api.modal.com` completed
  successfully.
- Token material is stored locally in `~/.modal.toml` under the
  `tritongen-lab` profile. Do not copy token IDs or token secrets into this
  repository.
- Active local profile: `tritongen-lab`.
- Default environment for profile `tritongen-lab`: `tritongen-dev`.
- Environment `tritongen-dev` exists.
- `modal app list` in `tritongen-dev` returns no apps yet.
- Local package import smoke passes:

```bash
python -c "import cluster1, shared"
```

Current missing or intentionally deferred Modal resources:

- No Modal app is deployed yet. This is expected until
  `shared/modal_harness/` exists.
- No Modal functions or classes are registered yet. This is expected until the
  first `modal run` or `modal deploy`.
- No Modal images have been built yet. They should be built from the Python
  `modal.Image` definitions during the first smoke run.
- Volumes `tritongen-hf-cache` and `tritongen-eval-artifacts` have not been
  confirmed yet. Let the harness create them with `create_if_missing=True`
  during Phase 1/3 smoke unless manual pre-provisioning is needed.
- Secret `huggingface-token` has not been confirmed yet. It is only required if
  the selected Hugging Face model is gated or private.
- GPU scheduling/quota has not been smoke-tested yet. The first remote compile
  smoke should verify this with the `L4` compile function.

### Volumes

Create these with `create_if_missing=True` in code:

```python
hf_cache_volume = modal.Volume.from_name(
    "tritongen-hf-cache",
    create_if_missing=True,
)
artifact_volume = modal.Volume.from_name(
    "tritongen-eval-artifacts",
    create_if_missing=True,
)
```

Use `tritongen-hf-cache` for Hugging Face model/tokenizer cache:

```text
/cache/huggingface
```

Set image/container env:

```python
.env({
    "HF_HOME": "/cache/huggingface",
    "HF_HUB_CACHE": "/cache/huggingface/hub",
    "TRANSFORMERS_CACHE": "/cache/huggingface/transformers",
})
```

Use `tritongen-eval-artifacts` only for larger future artifacts. For Cluster 1,
the authoritative result log should remain local JSONL under `outputs/cluster1/`.
Avoid many containers appending to the same file inside a Modal Volume. If
remote artifact writing is needed later, write one file per `run_id`.

### Secrets

Create a Hugging Face secret if the model is gated or private:

```bash
modal secret create huggingface-token HF_TOKEN=<token>
export TRITONGEN_MODAL_HF_SECRET=huggingface-token
```

Reference it in the generation class only. In `shared/modal_harness/secrets.py`,
make the secret list opt-in so public-model smoke tests do not fail when the
secret has not been created:

```python
import os
import modal

hf_secrets = (
    [modal.Secret.from_name(os.environ["TRITONGEN_MODAL_HF_SECRET"])]
    if os.environ.get("TRITONGEN_MODAL_HF_SECRET")
    else []
)
```

Do not attach this secret to the compile-only function unless it actually needs
it.

### Images

Create `shared/modal_harness/images.py`.

Compile image:

```python
import modal

PYTHON_VERSION = "3.11"

triton_compile_image = (
    modal.Image.debian_slim(python_version=PYTHON_VERSION)
    .uv_pip_install(
        "torch==2.8.0",
        "triton==3.4.0",
        "numpy==2.1.0",
        "pydantic==2.10.6",
    )
    .add_local_python_source("cluster1", "shared")
)
```

Generation image:

```python
llm_generation_image = (
    modal.Image.debian_slim(python_version=PYTHON_VERSION)
    .uv_pip_install(
        "torch==2.8.0",
        "triton==3.4.0",
        "transformers==4.56.0",
        "accelerate==1.10.0",
        "tokenizers==0.22.0",
        "autoawq==0.2.8",
        "xgrammar==0.1.21",
        "lark==1.2.2",
        "numpy==2.1.0",
        "pydantic==2.10.6",
        "huggingface_hub[hf_transfer]==0.34.0",
    )
    .env({
        "HF_HOME": "/cache/huggingface",
        "HF_HUB_CACHE": "/cache/huggingface/hub",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
    .add_local_python_source("cluster1", "shared")
)
```

Before coding, verify exact versions against local successful installs. The plan
requires pins, but the pins above are placeholders until a first Modal image
build confirms compatibility.

If `autoawq` fails on Debian slim, add a second generation image variant based
on an official CUDA devel image:

```python
modal.Image.from_registry(
    "nvidia/cuda:12.8.1-devel-ubuntu24.04",
    add_python="3.11",
).entrypoint([])
```

Use that only if needed. Keeping the first image simple reduces build time.

## Shared Schemas

Create `shared/modal_harness/schemas.py`. Use Pydantic or dataclasses. Pydantic
is preferred because Modal boundaries are JSON-like and validation errors should
be explicit. If Pydantic is used, add it to `pyproject.toml` and
`requirements.txt` so local adapters can import the schemas without relying on
the Modal image dependency list.

### RemoteGenerationRequest

```python
from typing import Literal
from pydantic import BaseModel, Field

FactorCell = Literal["none", "G", "C", "P", "G+C", "G+P", "C+P", "G+C+P"]
KernelClass = Literal["elementwise", "reduction", "matmul"]
DTypeName = Literal["fp32", "fp16", "bf16"]

class RemoteGenerationRequest(BaseModel):
    factor_cell: FactorCell
    kernel_class: KernelClass
    kernel_name: str
    dtype: DTypeName
    prompt: str
    model_id: str
    grammar_active: bool
    grammar_path: str = "cluster1/grammar/triton_kernel.gbnf"
    max_new_tokens: int = 1024
    temperature: float = 0.2
    generation_seed: int | None = None
    run_id: str
```

Validation invariants:

- `factor_cell == "none"` requires `grammar_active is False`.
- `factor_cell == "G"` requires `grammar_active is True`.
- Immediate implementation must reject all other factor cells.

### RemoteGenerationResult

```python
class RemoteGenerationResult(BaseModel):
    source: str
    model_id: str
    grammar_active: bool
    masked_token_rate: float | None
    generation_seed: int | None
    temperature: float
    run_id: str
    modal_function_call_id: str | None = None
    modal_input_id: str | None = None
    error_type: str | None = None
    error_msg: str | None = None
```

Validation invariants:

- If `grammar_active is False`, `masked_token_rate` must be `None`.
- If `grammar_active is True`, `masked_token_rate` must not be `None`.

### RemoteCompileRequest

```python
class RemoteCompileRequest(BaseModel):
    factor_cell: FactorCell
    kernel_class: KernelClass
    kernel_name: str
    source: str
    run_id: str
    timeout_s: int = 180
```

Do not serialize `CompileSpec`, `inspect.Signature`, or `build_args`. The remote
compile function should import `cluster1.data.kernels.get_kernel_spec()` and
look up the canonical spec by `kernel_class`.

### RemoteCompileResult

```python
class RemoteCompileResult(BaseModel):
    compile_success: bool
    compile_results_by_dtype: dict[DTypeName, bool]
    compile_error_type: str | None
    compile_error_msg: str | None
    n_shapes_tested: int
    stdout: str = ""
    stderr: str = ""
    traceback: str | None = None
    run_id: str
    modal_function_call_id: str | None = None
    modal_input_id: str | None = None
    metadata: dict = Field(default_factory=dict)
```

Cluster 1 result fields must not include timings, speedups, profiler output, or
numerical correctness.

### RemoteEvalResult

This is the bridge back into the existing `GenerationResult` schema.

```python
class RemoteEvalResult(BaseModel):
    generation: RemoteGenerationResult
    compile: RemoteCompileResult
```

The local Cluster 1 runner converts this to
`cluster1.results.dataclass.GenerationResult` and writes JSONL locally.

## Remote Generation Design

Create `shared/modal_harness/generation.py`.

Use a Modal class so model weights load once per container:

```python
import modal

from shared.modal_harness.app import app
from shared.modal_harness.images import llm_generation_image
from shared.modal_harness.secrets import hf_secrets
from shared.modal_harness.volumes import hf_cache_volume

@app.cls(
    image=llm_generation_image,
    gpu="L40S",
    memory=32768,
    cpu=8.0,
    timeout=900,
    max_containers=2,
    min_containers=0,
    scaledown_window=600,
    volumes={"/cache/huggingface": hf_cache_volume},
    secrets=hf_secrets,
)
class RemoteGenerator:
    model_id: str = modal.parameter()

    @modal.enter()
    def load_model(self):
        ...

    @modal.method()
    def generate_one(self, req_dict: dict) -> dict:
        ...
```

Start with `max_containers=2` to avoid downloading the model into too many
containers at once. Increase only after cache behavior and cost are understood.

GPU policy:

- Default generation GPU: `L40S`, because it has enough memory headroom for
  7B/32B experiments and is recommended by Modal docs as a strong inference
  tradeoff.
- Cost smoke option: `A10` or `L4`, only after the AWQ model is confirmed to fit.
- Do not use H100/H200/B200 for Cluster 1 unless a model truly requires it.

`load_model()` responsibilities:

1. Import `torch`, `transformers`, and optional AWQ dependencies inside the
   method, not module global scope.
2. Load tokenizer once.
3. Load model once onto CUDA.
4. Set eval mode.
5. Store `self.tokenizer`, `self.model`, and `self.device`.
6. Do not load or compile XGrammar globally if it depends on request state.

`generate_one()` responsibilities:

1. Validate `RemoteGenerationRequest`.
2. Enforce immediate supported modes: `none` and `G` only.
3. For `none`, call the exact same generation code as Cluster 1 with
   `grammar_active=False`.
4. For `G`, load/compile grammar and instantiate a fresh XGrammar
   logits processor or matcher for this request.
5. Call the existing `cluster1.generation.constrained_gen.generate_source()`
   path if it can run fully remote with the loaded model/tokenizer.
6. Return `RemoteGenerationResult`.
7. Include `modal.current_function_call_id()` and `modal.current_input_id()`
   in result metadata when available.

Do not:

- look at compile results;
- re-prompt;
- retry generation based on compiler errors;
- compare against reference outputs;
- compute timing metrics.

## Remote Compile-Only Design

Create `shared/modal_harness/compile.py`.

Use a Modal function, not a class. Compile checks do not benefit from loading a
large persistent model.

```python
import modal

from shared.modal_harness.app import app
from shared.modal_harness.images import triton_compile_image

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
    ...
```

GPU policy:

- Default compile GPU: `L4`.
- Fallback option: `gpu=["L4", "A10"]` after smoke tests if queueing becomes a
  problem.
- Avoid `gpu="any"` for thesis runs because GPU variation can change Triton
  compile behavior and error surfaces.

Implementation detail:

Run generated code in a subprocess inside the Modal function.

Reason: a bad Triton/CUDA launch can poison the Python process. A subprocess
lets the Modal parent function capture stdout/stderr and return a structured
failure while the child exits.

Parent function steps:

1. Validate `RemoteCompileRequest`.
2. Write a small JSON request file into a temp directory.
3. Write or call a runner module that imports:
   - `cluster1.data.kernels.get_kernel_spec`
   - `cluster1.validation.compile_check.check_compiles_all_dtypes`
4. Run child process:

```python
subprocess.run(
    ["python", "-m", "shared.modal_harness.compile_runner", request_path],
    capture_output=True,
    text=True,
    timeout=req.timeout_s,
)
```

5. Parse the child's JSON result from stdout or an output file.
6. Truncate stdout/stderr to 4000 chars each for JSONL safety.
7. Return `RemoteCompileResult`.

Child runner steps:

1. Read `RemoteCompileRequest`.
2. Look up kernel spec by `kernel_class`.
3. Verify `kernel_name` matches the spec.
4. Call:

```python
compile_results = check_compiles_all_dtypes(
    req.source,
    spec.compile_spec,
    spec.shapes_by_dtype,
)
```

5. Build:

```python
compile_success = all(r.success for r in compile_results)
compile_results_by_dtype = {r.dtype: r.success for r in compile_results}
first_error = next((r for r in compile_results if r.error_type is not None), None)
```

6. Return existing taxonomy:
   - `CompilationError`
   - `RuntimeError`
   - `SignatureError`
   - `None`

Do not:

- use `torch.allclose`;
- use `torch.testing`;
- call `triton.testing.do_bench`;
- record elapsed time;
- run profiler tooling;
- execute repair or retry loops.

## Local Cluster 1 Modal Adapters

### `cluster1/generation/modal_generate.py`

This file should provide a narrow adapter:

```python
def generate_source_modal(
    *,
    prompt: str,
    model_id: str,
    kernel_class: str,
    kernel_name: str,
    dtype: str,
    grammar_active: bool,
    generation_seed: int | None,
    temperature: float,
    max_new_tokens: int,
    run_id: str,
) -> RemoteGenerationResult:
    ...
```

The adapter calls:

```python
RemoteGenerator(model_id=model_id).generate_one.remote(req.model_dump())
```

It must not import `torch`, `transformers`, or `xgrammar` locally.

### `cluster1/validation/modal_compile_check.py`

This file should provide:

```python
def check_compiles_modal(
    *,
    source: str,
    kernel_class: str,
    kernel_name: str,
    factor_cell: str,
    run_id: str,
) -> RemoteCompileResult:
    ...
```

The adapter calls:

```python
remote_compile_only.remote(req.model_dump())
```

Do not modify the current local compile gate behavior except to allow the Modal
runner to choose a backend.

### Backend selection

Add a backend flag where the experiment runner chooses execution:

```python
Literal["local", "modal"]
```

For `run_cluster1_modal.py`, hardcode `backend="modal"` rather than overloading
the existing `run_cluster1.py` too much. Keep the old local runner intact for
CPU/unit-test development and local CUDA debugging.

## Remote Experiment Runner

Create `cluster1/experiments/run_cluster1_modal.py`.

It should be a Modal app local entrypoint, because `modal run` gives the clean
development loop and streams remote output.

CLI:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class elementwise \
  --n 1 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/modal_smoke_baseline.jsonl
```

Arguments should mirror `cluster1/experiments/run_cluster1.py`:

- `--condition baseline|G|both`
- `--kernel-class elementwise|reduction|matmul|all`
- `--n`
- `--model-id`
- `--dataset-id`
- `--output`
- `--temperature`
- `--max-new-tokens`
- `--compile-backend modal`
- `--generation-backend modal`
- `--modal-generation-gpu` later, if the code uses parametric classes or
  separate class definitions per GPU
- `--modal-compile-gpu` later, if needed

Mapping:

```text
condition=baseline -> factor_cell="none", grammar_active=False
condition=G        -> factor_cell="G",    grammar_active=True
condition=both     -> run both cells
```

Do not add `condition=C`, `condition=P`, or other combinations yet. The shared
schema can reserve those labels, but the Cluster 1 Modal runner must reject
them until Cluster 2/3 are implemented.

Runner per-cell flow:

1. Build the same prompt using `cluster1.data.prompts.prompt_contract.build_prompt`.
2. Allocate one `run_id`.
3. Call remote generation.
4. Call remote compile-only validation.
5. Convert remote result to `GenerationResult`.
6. Validate `GenerationResult` invariants.
7. Append one JSONL row locally.
8. Print a one-line progress record.

Progress line format:

```text
run_id=<uuid> condition=<baseline|G> kernel=<class/name> dtype=<dtype> seed=<seed> compile=<true|false> error=<type-or-none>
```

Do not print generated source by default. Add `--dump-source-on-failure` later if
needed, writing source to a separate local artifact file.

## Batch Strategy

Start synchronous. Move to parallel only after `n=1` smoke tests pass.

### M0 smoke

One generated baseline cell:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class elementwise \
  --n 1 \
  --output outputs/cluster1/modal_smoke_baseline.jsonl
```

One generated Cluster 1 cell:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class elementwise \
  --n 1 \
  --output outputs/cluster1/modal_smoke_g.jsonl
```

One compile-only known-good fixture:

```bash
modal run -m shared.modal_harness.smoke --case good-relu-compile
```

One compile-only known-bad fixture:

```bash
modal run -m shared.modal_harness.smoke --case bad-triton-compile
```

### M1 small matrix

Run 2 seeds across all kernel classes for baseline:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class all \
  --n 2 \
  --output outputs/cluster1/modal_baseline_n2.jsonl
```

Run 2 seeds across all kernel classes for G:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class all \
  --n 2 \
  --output outputs/cluster1/modal_g_n2.jsonl
```

### M2 full no-control baseline

This is the immediate full test run with no control mechanism:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/modal_baseline_full.jsonl
```

Expected rows if keeping the current dtype loop:

```text
3 kernel classes * 1 condition * 3 dtypes * 20 seeds = 180 rows
```

### M3 full Cluster 1 G eval

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/modal_g_full.jsonl
```

Expected rows:

```text
3 kernel classes * 1 condition * 3 dtypes * 20 seeds = 180 rows
```

### M4 combined Cluster 1 comparison

Only after M2 and M3 are stable:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition both \
  --kernel-class all \
  --n 20 \
  --model-id Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --output outputs/cluster1/modal_cluster1_both_full.jsonl
```

Expected rows:

```text
3 kernel classes * 2 conditions * 3 dtypes * 20 seeds = 360 rows
```

## Parallelism Rules

### Generation parallelism

Keep generation low-parallel at first.

Use the Modal class container reuse to amortize model loading. Do not launch 20
model-loading containers immediately. Start with `max_containers=2`, then
increase if the HF cache volume is hot and GPU budget allows.

Candidate implementation:

```python
generator = RemoteGenerator(model_id=args.model_id)
for req in generation_requests:
    result = generator.generate_one.remote(req.model_dump())
```

After smoke:

```python
for result_dict in generator.generate_one.map([req.model_dump() for req in requests]):
    ...
```

If class method `.map()` introduces awkward code, keep synchronous generation
and parallelize compile checks first. The model is likely the bottleneck and
should stay controlled until results are reproducible.

### Compile parallelism

Compile checks are embarrassingly parallel.

After synchronous smoke passes:

```python
for compile_result in remote_compile_only.map([req.model_dump() for req in compile_requests]):
    ...
```

For the first full runs, use `max_containers=20`. If Modal quota or cost is a
concern, reduce to `max_containers=5`.

### Async/background jobs

Do not use `.spawn()` or `.spawn_map()` for the first Cluster 1 runs. They are
useful later when results are persisted externally and the caller can disconnect.
For now, the local runner should collect results and append JSONL in order.

Use `.spawn()` later for Cluster 3 rollouts, where a job ID and polling loop are
more appropriate.

## Streaming Output and Logs

During development, use `modal run`. It streams build progress and function
logs to the terminal.

If invoking Modal programmatically with `app.run()`, wrap it:

```python
with modal.enable_output():
    with app.run():
        ...
```

For a deployed app, stream logs:

```bash
modal app logs tritongen-gpu-harness -f --timestamps --show-function-call-id
```

Useful filters:

```bash
modal app logs tritongen-gpu-harness --function-call fc-... --timestamps
modal app logs tritongen-gpu-harness --source stderr --timestamps
```

Remote functions should print structured log lines for major events:

```text
JSON_EVENT {"event":"generation_start","run_id":"...","factor_cell":"G","kernel_class":"elementwise"}
JSON_EVENT {"event":"generation_done","run_id":"...","source_chars":1234}
JSON_EVENT {"event":"compile_start","run_id":"...","kernel_class":"elementwise"}
JSON_EVENT {"event":"compile_done","run_id":"...","compile_success":true,"error_type":null}
```

These logs are for operator visibility. The authoritative experiment output is
the local JSONL row written by the runner.

Do not log:

- full prompts by default;
- HF tokens or environment variables;
- full generated source in Modal logs by default;
- timing or profiling fields in Cluster 1 results.

## Eval Logging

Keep the existing local logger:

```python
cluster1.results.logger.append_result_jsonl()
```

The Modal runner writes rows matching `GenerationResult` exactly.

Add these fields only if the local schema is intentionally extended:

- `modal_generation_call_id`
- `modal_compile_call_id`
- `modal_generation_input_id`
- `modal_compile_input_id`
- `modal_app_name`
- `modal_environment`
- `modal_generation_gpu_requested`
- `modal_compile_gpu_requested`
- `modal_image_version`
- `harness_version`

Do not add any field that looks like:

- `elapsed_s`
- `compile_time_s`
- `generation_time_s`
- `latency_ms`
- `speedup`
- `profile_*`
- `ncu_*`
- `nvml_*`

If call IDs are needed without changing `GenerationResult`, store them in a
sidecar file:

```text
outputs/cluster1/modal_call_index.jsonl
```

Sidecar row:

```json
{"run_id":"...","generation_call_id":"fc-...","compile_call_id":"fc-..."}
```

## Shareability Contract

The shared harness exposes generic remote execution primitives. Cluster code
decides which modes are legal.

Allowed now:

```text
factor_cell="none" -> generation without grammar, compile-only validation
factor_cell="G"    -> grammar generation, compile-only validation
```

Reserved later:

```text
factor_cell="C"       -> test-driven feedback repair, Cluster 2 only
factor_cell="G+C"     -> grammar plus test-driven feedback, Cluster 2 only
factor_cell="P"       -> compiler/profiler repair, Cluster 3 only
factor_cell="G+P"     -> grammar plus compiler/profiler repair, Cluster 3 only
factor_cell="C+P"     -> test-driven plus compiler/profiler repair, Cluster 3 only
factor_cell="G+C+P"   -> full stack, Cluster 3 only
```

Cluster 1 adapters must reject all reserved modes.

Shared harness modules may contain reserved schema fields, but no reserved mode
should execute until the relevant cluster has a contract and tests.

## Future Swappable Factor Orchestration Layer

The shared factor-cell layer is a future extraction point, not a Phase 1-6
requirement. Its purpose is to keep the eight-cell factorial experiment
consistent once C and P exist.

Why this layer is needed:

- The central thesis question requires all eight cells to be evaluated on the
  same tasks, model, seeds, dtypes, and shared metrics.
- Cluster 1 only answers the G slice: `none` versus `G`, using compile
  acceptance only.
- Cluster 2, Cluster 3, and final interaction analysis complete the factorial
  design by adding test-driven feedback and compiler/profiler repair as
  swappable modules.

Canonical factor cells:

```text
none
G
C
P
G+C
G+P
C+P
G+C+P
```

Future file structure:

```text
shared/factors/
  cells.py          # canonical factor labels and validation
  config.py         # FactorConfig(grammar, compiler_feedback, performance_feedback)
  registry.py       # maps condition -> enabled mechanisms

shared/eval/
  # shared metrics/eval pipeline, implemented later

shared/modal_harness/
  # existing remote execution primitives
```

Ownership boundaries:

- `cluster1` may execute only `none` and `G`.
- `cluster2` may execute `none`, `C`, and `G+C` after the Cluster 2 contract
  exists.
- `cluster3` may execute `P`, `G+P`, `C+P`, `G+C+P`, and later possibly all
  eight cells for final comparison.
- Shared schemas may reserve all labels, but clusters must reject unsupported
  cells until their contracts exist.

Scale tiers:

Use `.contracts/research/scale_policy.md` for the authoritative scale
definitions.

- **Smoke scale:** one kernel, one condition, `n=1`, development model. This
  proves the Modal path and cluster runner work end to end.
- **Development scale:** three kernels, active conditions, `n=3..5`,
  development model. This is for iterating on prompts, grammars, repair
  templates, feedback parsing, and harness behavior.
- **Paper scale:** target 6-9 KernelBench problems balanced across classes,
  full factorial where applicable, `n=20`, larger model. This is the only scale
  that supports reported paper claims.

The current strict Cluster 1 grammar remains a three-kernel
`template_upper_bound` control. It should not be silently expanded into the
larger paper-scale G condition.

Correct sequencing:

1. Finish Cluster 1 full `none` and `G` runs.
2. Analyze the compile-only G effect.
3. Extract shared factor-cell config before Cluster 2.
4. Implement C as a swappable test-driven feedback module.
5. Implement P as a swappable compiler/profiler repair module.
6. Run all eight cells with the shared eval layer.

Non-goals for now:

- Do not implement `shared/factors/` before Cluster 1 full baseline and full G
  runs.
- Do not implement C or P now.
- Do not allow Cluster 1 to execute reserved cells.
- Do not add numerical correctness, profiling, timing, speedup, repair loops,
  or performance scoring to Cluster 1.

## Security and Isolation

Generated Triton code is untrusted.

Immediate isolation:

- compile generated source in a subprocess inside the Modal GPU function;
- use temp directories;
- enforce child process timeout;
- capture stdout/stderr;
- return structured errors.

Later isolation:

- evaluate Modal Sandboxes if Cluster 2/3 run more arbitrary code or need
  stronger command-level isolation;
- use Sandboxes for subprocess-like workloads that need separate filesystem or
  command streams;
- keep normal Modal functions for the first Cluster 1 implementation because
  they are simpler and enough for compile smoke tests.

Do not use web endpoints for untrusted generated code in this phase.

## Implementation Phases

### Phase 0: Preflight

Files:

- `.contracts/agentic/modal_integration_plan.md`

Status:

- Complete for non-secret dev setup in workspace `tritongen-lab`.
- Optional `huggingface-token` secret remains pending unless the selected model
  requires it.
- GPU execution remains unverified until the first Modal smoke run.

Tasks:

1. Install Modal locally.
2. Run `modal setup`.
3. Activate the `tritongen-lab` workspace profile.
4. Create `tritongen-dev` if it does not already exist.
5. Set `tritongen-dev` as the default environment for the active profile, or
   commit to passing `--env tritongen-dev` on every Modal command.
6. Create `huggingface-token` secret if needed.
7. Confirm local package imports:

```bash
python -c "import cluster1, shared"
```

Completion:

- `modal app list` works.
- `modal environment --help` works.
- `modal config show` shows the expected profile and `tritongen-dev`
  environment.
- No code changes yet.

### Phase 1: Shared Modal Package

Files:

- `shared/modal_harness/__init__.py`
- `shared/modal_harness/app.py`
- `shared/modal_harness/images.py`
- `shared/modal_harness/volumes.py`
- `shared/modal_harness/secrets.py`

Tasks:

1. Define `modal.App("tritongen-gpu-harness")`.
2. Define HF cache and artifact volumes.
3. Define optional HF secret lookup.
4. Define compile and generation images.
5. Explicitly include local source with `add_local_python_source("cluster1", "shared")`.
6. Keep remote-only imports inside remote functions/methods when dependencies
   are not required locally.

Tests:

```bash
python -m compileall shared/modal_harness
```

Completion:

- `modal run -m shared.modal_harness.smoke --case import-only` can build a
  minimal image and import `cluster1` and `shared` remotely.

### Phase 2: Schemas and Error Mapping

Files:

- `shared/modal_harness/schemas.py`
- `shared/modal_harness/errors.py`

Tasks:

1. Add request/result schemas.
2. Add validation invariants for `none` and `G`.
3. Add helpers to truncate stdout/stderr.
4. Add helper to convert remote compile result to existing Cluster 1 fields.

Tests:

- Unit test schema round trip.
- Unit test invalid mode rejection.
- Unit test `none` with `grammar_active=True` fails.
- Unit test `G` with `grammar_active=False` fails.

Completion:

- All schema tests pass without Modal.

### Phase 3: Remote Compile Smoke

Files:

- `shared/modal_harness/compile.py`
- `shared/modal_harness/compile_runner.py`
- `shared/modal_harness/smoke.py`
- `cluster1/validation/modal_compile_check.py`

Tasks:

1. Implement `remote_compile_only`.
2. Implement subprocess runner.
3. Reuse existing `cluster1.validation.compile_check`.
4. Add known-good ReLU source smoke.
5. Add known-bad Triton source smoke.
6. Return existing Cluster 1 taxonomy.
7. Include Modal call IDs in remote result metadata.

Commands:

```bash
modal run -m shared.modal_harness.smoke --case good-relu-compile
modal run -m shared.modal_harness.smoke --case bad-triton-compile
```

Completion:

- Good fixture returns `compile_success=true`.
- Bad fixture returns `compile_success=false`.
- No forbidden Cluster 1 boundary terms are introduced.

### Phase 4: Remote Model Generation

Files:

- `shared/modal_harness/generation.py`
- `cluster1/generation/modal_generate.py`

Tasks:

1. Implement `RemoteGenerator`.
2. Load model/tokenizer in `@modal.enter()`.
3. Mount HF cache volume.
4. Use HF secret only if required.
5. Reuse `cluster1.generation.constrained_gen.generate_source`.
6. Confirm baseline generation works with `grammar_active=False`.
7. Confirm G generation works with `grammar_active=True`.

Commands:

```bash
modal run -m shared.modal_harness.smoke --case generate-baseline-one
modal run -m shared.modal_harness.smoke --case generate-g-one
```

Completion:

- Baseline returns source and `masked_token_rate=null`.
- G returns source and non-null `masked_token_rate`.
- No compile feedback is passed into generation.

### Phase 5: Modal Cluster 1 Runner

Files:

- `cluster1/experiments/run_cluster1_modal.py`

Tasks:

1. Mirror `run_cluster1.py` arguments.
2. Map `baseline` to `factor_cell="none"`.
3. Map `G` to `factor_cell="G"`.
4. Reject reserved factor cells.
5. Build prompts locally using existing prompt contract.
6. Generate remotely.
7. Compile remotely.
8. Convert to `GenerationResult`.
9. Append JSONL locally.
10. Print one progress line per row.

Smoke commands:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class elementwise \
  --n 1 \
  --output outputs/cluster1/modal_smoke_baseline.jsonl

modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class elementwise \
  --n 1 \
  --output outputs/cluster1/modal_smoke_g.jsonl
```

Completion:

- Both output files exist.
- Each has 3 rows if the dtype loop is unchanged.
- Rows validate with `validate_result_invariants`.

### Phase 6: Batch and Full Runs

Files:

- `cluster1/experiments/run_cluster1_modal.py`
- optional `shared/modal_harness/client.py`

Tasks:

1. Add sequential mode as default.
2. Add `--parallel-compile` after smoke.
3. Add generation `.map()` only after model cache behavior is stable.
4. Add resume behavior: skip `run_id`s already present in output only if a
   manifest exists. Do not infer resume from source hashes.
5. Add `--fail-fast` for debugging and default to continue-on-error for full
   experiment runs.

Full baseline:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition baseline \
  --kernel-class all \
  --n 20 \
  --output outputs/cluster1/modal_baseline_full.jsonl
```

Full G:

```bash
modal run -m cluster1.experiments.run_cluster1_modal \
  --condition G \
  --kernel-class all \
  --n 20 \
  --output outputs/cluster1/modal_g_full.jsonl
```

Completion:

- Baseline full has 180 rows.
- G full has 180 rows.
- No Cluster 1 boundary scanner failures.

### Phase 7: Analysis Compatibility

Files:

- `cluster1/experiments/analyze_cluster1.py`
- optional tests if schema extended

Tasks:

1. Confirm existing analyzer can read Modal JSONL without changes.
2. If call metadata is sidecar-only, analyzer ignores it.
3. Run pass@k report for baseline and G.
4. Compare row counts by `(kernel_class, grammar_active, dtype)`.

Commands:

```bash
python -m cluster1.experiments.analyze_cluster1 \
  --input outputs/cluster1/modal_baseline_full.jsonl \
  --output outputs/cluster1/modal_baseline_summary.md

python -m cluster1.experiments.analyze_cluster1 \
  --input outputs/cluster1/modal_g_full.jsonl \
  --output outputs/cluster1/modal_g_summary.md
```

Completion:

- Analyzer does not know or care that Modal performed GPU work.
- Cluster 1 research outputs remain schema-compatible.

### Phase 8: Deployment

Only after the full smoke matrix is stable:

```bash
modal deploy -m shared.modal_harness.app
```

Then add client lookup helpers:

```python
modal.Function.from_name("tritongen-gpu-harness", "remote_compile_only")
modal.Cls.from_name("tritongen-gpu-harness", "RemoteGenerator")
```

Use deployed invocation for repeated long runs. Keep `modal run` for active
development.

Completion:

- Deployed app visible in Modal dashboard.
- `modal app logs tritongen-gpu-harness -f --timestamps` streams logs.
- Local runner can use deployed lookup if `--deployed` is passed.

## Cluster 2 and 3 Preparation

The harness should be shareable by design but not execute later-cluster modes
yet.

Reserved future files:

```text
shared/modal_harness/correctness.py
shared/modal_harness/feedback.py
shared/modal_harness/profile.py
shared/modal_harness/jobs.py
cluster2/feedback/modal_feedback_loop.py
cluster3/profiling/modal_profile.py
cluster3/profiling/repair_loop.py
```

Cluster 2 additions later:

- `remote_correctness_check`
- structured correctness feedback for prompts
- repair loop orchestration

Cluster 3 additions later:

- `remote_profile_kernel`
- compiler/runtime diagnostic feedback
- performance-summary feedback
- paper-scale fanout through `.spawn_map()` after development scale is stable
- optional persistent job queue
- optional artifacts in `tritongen-eval-artifacts`

Do not pre-code these now. Only reserve schemas and names where doing so keeps
the Cluster 1 harness from being boxed in.

## Tests to Add

### Local unit tests

```text
cluster1/tests/test_modal_harness_contract.py
shared/tests/test_modal_harness_schemas.py
```

If the repo does not currently test `shared/tests`, either add it to
`pyproject.toml` testpaths or place shared harness schema tests under
`cluster1/tests` until Cluster 2/3 tests are active.

Assertions:

- baseline maps to `factor_cell="none"`;
- G maps to `factor_cell="G"`;
- reserved modes are rejected;
- no local Modal adapter imports `torch`, `transformers`, or `xgrammar`;
- remote result converts to `GenerationResult`;
- boundary scanner still passes;
- `masked_token_rate` invariants hold.

### Modal integration smoke

These should not run in normal `pytest` unless an explicit env var is set:

```bash
TRITONGEN_MODAL_TESTS=1 pytest cluster1/tests/test_modal_integration.py -v
```

Integration cases:

- remote import smoke;
- known-good ReLU compile;
- known-bad compile;
- baseline one-cell generation plus compile;
- G one-cell generation plus compile.

## Operational Risks

### Model download latency

First run may be slow because the model cache volume is empty. That is expected.
Keep `max_containers` low during the first generation run to avoid duplicate
downloads.

### Volume consistency

Volumes are not a normal shared POSIX filesystem. Avoid concurrent appends to a
single file. For Cluster 1, write JSONL locally from the runner.

### Dependency drift

Pin remote image dependencies. Do not rely on local `requirements.txt` ranges
for Modal images. A local flexible range is acceptable for development, but the
remote image used for experiment runs should be pinned.

### Modal API drift

Use Modal 1.0 style APIs:

- `modal.App`, not `modal.Stub`;
- `Image.add_local_python_source`, not implicit automounting;
- `min_containers`, `max_containers`, `scaledown_window`, not old autoscaler
  names;
- `modal.fastapi_endpoint` later if web endpoints are added.

### Cluster 1 contamination

The highest research risk is accidentally turning compile errors into a control
signal. Tests must prevent:

- compile error text being added to prompts;
- retry loops;
- repair loops;
- timing or profiling fields;
- correctness checks.

## Definition of Done

Modal integration is done for this milestone when:

1. `modal setup` and the active environment are documented.
2. `shared/modal_harness/` exists and owns the Modal app, images, volumes,
   schemas, generation class, and compile function.
3. Local cluster adapters exist but contain no duplicated Modal app definitions.
4. Known-good remote compile smoke passes.
5. Known-bad remote compile smoke returns structured failure.
6. One baseline Modal generation plus compile row is written locally.
7. One G Modal generation plus compile row is written locally.
8. Full no-control baseline run writes 180 rows.
9. Full Cluster 1 G run writes 180 rows.
10. Existing analysis can read the output JSONL.
11. Boundary tests pass with no Cluster 2/3 leakage.
12. The harness has reserved extension points for Cluster 2 and Cluster 3
    without implementing their control mechanisms.

## Documentation References

- Modal Apps, Functions, and entrypoints: https://modal.com/docs/guide/apps
- Modal GPU acceleration: https://modal.com/docs/guide/gpu
- Modal CUDA guidance: https://modal.com/docs/guide/cuda
- Modal Images and local source inclusion: https://modal.com/docs/guide/images
- Modal Volumes: https://modal.com/docs/guide/volumes
- Modal Secrets: https://modal.com/docs/guide/secrets
- Modal Environments: https://modal.com/docs/guide/environments
- Modal Workspaces: https://modal.com/docs/guide/workspaces
- Modal lifecycle hooks: https://modal.com/docs/guide/lifecycle-functions
- Modal parametrized functions/classes: https://modal.com/docs/guide/parametrized-functions
- Modal batch processing: https://modal.com/docs/guide/batch-processing
- Modal job queues: https://modal.com/docs/guide/job-queue
- Modal deployed function invocation: https://modal.com/docs/guide/trigger-deployed-functions
- Modal logs CLI: https://modal.com/docs/reference/cli/app
- Modal notebooks guidance: https://modal.com/docs/guide/jupyter-notebooks
- Modal 1.0 migration guidance: https://modal.com/docs/guide/modal-1-0-migration
