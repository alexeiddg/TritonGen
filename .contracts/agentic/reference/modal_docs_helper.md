Using CUDA on Modal
Modal makes it easy to accelerate your workloads with datacenter-grade NVIDIA GPUs.

To take advantage of the hardware, you need to use matching software: the CUDA stack. This guide explains the components of that stack and how to install them on Modal. For more on which GPUs are available on Modal and how to choose a GPU for your use case, see this guide. For a deep dive on both the GPU hardware and software and for even more detail on the CUDA stack, see our GPU Glossary.

Here’s the tl;dr:

The NVIDIA Accelerated Graphics Driver for Linux-x86_64, version 580.95.05, and CUDA Driver API, version 13.0, are already installed. You can call nvidia-smi or run compiled CUDA programs from any Modal Function with access to a GPU.
That means you can install many popular libraries like torch that bundle their other CUDA dependencies with a simple pip_install.
For bleeding-edge libraries like flash-attn, you may need to install CUDA dependencies manually. To make your life easier, use an existing image.
What is CUDA?
When someone refers to “installing CUDA” or “using CUDA”, they are referring not to a library, but to a stack with multiple layers. Your application code (and its dependencies) can interact with the stack at different levels.

The CUDA stack

This leads to a lot of confusion. To help clear that up, the following sections explain each component in detail.

Level 0: Kernel-mode driver components
At the lowest level are the kernel-mode driver components. The Linux kernel is essentially a single program operating the entire machine and all of its hardware. To add hardware to the machine, this program is extended by loading new modules into it. These components communicate directly with hardware — in this case the GPU.

Because they are kernel modules, these driver components are tightly integrated with the host operating system that runs your containerized Modal Functions and are not something you can inspect or change yourself.

Level 1: User-mode driver API
All action in Linux that doesn’t occur in the kernel occurs in user space. To talk to the kernel drivers from our user space programs, we need user-mode driver components.

Most prominently, that includes:

the CUDA Driver API, a shared object called libcuda.so. This object exposes functions like cuMemAlloc, for allocating GPU memory.
the NVIDIA management library, libnvidia-ml.so, and its command line interface nvidia-smi. You can use these tools to check the status of the system’s GPU(s).
These components are installed on all Modal machines with access to GPUs. Because they are user-level components, you can use them directly:

import modal

app = modal.App()

@app.function(gpu="any")
def check_nvidia_smi():
    import subprocess
    output = subprocess.check_output(["nvidia-smi"], text=True)
    assert "Driver Version:" in output
    assert "CUDA Version:" in output
    print(output)
    return output
Copy
Level 2: CUDA Toolkit
Wrapping the CUDA Driver API is the CUDA Runtime API, the libcudart.so shared library. This API includes functions like cudaLaunchKernel and is more commonly used in CUDA programs (see this HackerNews comment for color commentary on why). This shared library is not installed by default on Modal.

The CUDA Runtime API is generally installed as part of the larger NVIDIA CUDA Toolkit, which includes the NVIDIA CUDA compiler driver (nvcc) and its toolchain and a number of useful goodies for writing and debugging CUDA programs (cuobjdump, cudnn, profilers, etc.).

Contemporary GPU-accelerated machine learning workloads like LLM inference frequently make use of many components of the CUDA Toolkit, such as the run-time compilation library nvrtc.

So why aren’t these components installed along with the drivers? A compiled CUDA program can run without the CUDA Runtime API installed on the system, by statically linking the CUDA Runtime API into the program binary, though this is fairly uncommon for CUDA-accelerated Python programs. Additionally, older versions of these components are needed for some applications and some application deployments even use several versions at once. Both patterns are compatible with the host machine driver provided on Modal.

Install GPU-accelerated torch and transformers with pip_install
The components of the CUDA Toolkit can be installed via pip, via PyPI packages like nvidia-cuda-runtime-cu12 and nvidia-cuda-nvrtc-cu12. These components are listed as dependencies of some popular GPU-accelerated Python libraries, like torch.

Because Modal already includes the lower parts of the CUDA stack, you can install these libraries with the pip_install method of modal.Image, just like any other Python library:

image = modal.Image.debian_slim().pip_install("torch")


@app.function(gpu="any", image=image)
def run_torch():
    import torch
    has_cuda = torch.cuda.is_available()
    print(f"It is {has_cuda} that torch can access CUDA")
    return has_cuda
Copy
Many libraries for running open-weights models, like transformers and vllm, use torch under the hood and so can be installed in the same way:

image = modal.Image.debian_slim().pip_install("transformers[torch]")
image = image.apt_install("ffmpeg")  # for audio processing


@app.function(gpu="any", image=image)
def run_transformers():
    from transformers import pipeline
    transcriber = pipeline(model="openai/whisper-tiny.en", device="cuda")
    result = transcriber("https://modal-cdn.com/mlk.flac")
    print(result["text"])  # I have a dream that one day this nation will rise up live out the true meaning of its creed
Copy
For more complex setups, use an officially-supported CUDA image
The disadvantage of installing the CUDA stack via pip is that many other libraries that depend on its components being installed as normal system packages cannot find them.

For these cases, we recommend you use an image that already has the full CUDA stack installed as system packages and all environment variables set correctly, like the nvidia/cuda:*-devel-* images on Docker Hub.

TensorRT-LLM is an inference engine that accelerates and optimizes performance for the large language models. It requires the full CUDA toolkit for installation.

cuda_version = "12.8.1"  # should be no greater than host CUDA version
flavor = "devel"  # includes full CUDA toolkit
operating_sys = "ubuntu24.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"
HF_CACHE_PATH = "/cache"


image = (
    modal.Image.from_registry(f"nvidia/cuda:{tag}", add_python="3.12")
    .entrypoint([])  # remove verbose logging by base image on entry
    .apt_install("libopenmpi-dev")  # required for tensorrt
    .pip_install("tensorrt-llm==0.19.0", "pynvml", extra_index_url="https://pypi.nvidia.com")
    .pip_install("hf-transfer", "huggingface_hub[hf_xet]")
    .env({"HF_HUB_CACHE": HF_CACHE_PATH, "HF_HUB_ENABLE_HF_TRANSFER": "1", "PMIX_MCA_gds": "hash"})
)


app = modal.App("tensorrt-llm", image=image)
hf_cache_volume = modal.Volume.from_name("hf_cache_tensorrt", create_if_missing=True)


@app.function(gpu="A10G", volumes={HF_CACHE_PATH: hf_cache_volume})
def run_tiny_model():
    from tensorrt_llm import LLM, SamplingParams

    sampling_params = SamplingParams(temperature=0.8, top_p=0.95)

    llm = LLM(model="TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    output = llm.generate("The capital of France is", sampling_params)
    print(f"Generated text: {output.outputs[0].text}")
    return output.outputs[0].text
Copy
Make sure to choose a version of CUDA that is no greater than the version provided by the host machine. Older versions in the 12.* and 13.* series are guaranteed to be compatible with the host machine’s driver, but older major versions (11.*, 10.*, etc.) may not be.

---

Configuring CPU, memory, and disk
Each Modal Function or Sandbox container has a default request of 0.125 CPU cores and 128 MiB of memory. Containers can exceed this minimum if the worker has available CPU or memory. You can also guarantee access to more resources by requesting larger values, similarly to Kubernetes.

CPU cores
If you have code that must run on a larger number of cores, you can request that using the cpu argument. This allows you to specify a floating-point number of CPU cores:

import modal

app = modal.App()

@app.function(cpu=8.0)
def my_function():
    # code here will have access to at least 8.0 cores
    ...
Copy
Note that this value corresponds to physical cores, not vCPUs.

Modal also will set several environment variables that control multi-threading behavior in linear algebra libraries (e.g., OPENBLAS_NUM_THREADS, OMP_NUM_THREADS, MKL_NUM_THREADS) based on your CPU request.

Memory
If you have code that needs more guaranteed memory, you can request it using the memory argument. This expects an integer number of megabytes:

import modal

app = modal.App()

@app.function(memory=32768)
def my_function():
    # code here will have access to at least 32 GiB of RAM
    ...
Copy
How much can I request?
For both CPU and memory, a maximum is enforced at Function or Sandbox creation time to ensure your containers can be scheduled for execution. Requests exceeding the maximum will be rejected with an InvalidError.

Billing
For CPU and memory, you’ll be charged based on whichever is higher: your request or actual usage.

Disk requests are billed by increasing the memory request at a 20:1 ratio. For example, requesting 500 GiB of disk will increase the memory request to 25 GiB, if it is not already set higher.

Resource limits
CPU limits
Modal containers have a default soft CPU limit that is set at 16 physical cores above the CPU request. Given that the default CPU request is 0.125 cores, the default soft CPU limit is 16.125 cores. Above this limit, the host will begin to throttle the CPU usage of the container.

You can alternatively set the CPU limit explicitly:

cpu_request = 1.0
cpu_limit = 4.0
@app.function(cpu=(cpu_request, cpu_limit))
def f():
    ...
Copy
Memory limits
Modal containers can have a hard memory limit which will ‘Out of Memory’ (OOM) kill containers which attempt to exceed the limit. This functionality is useful when a process has a serious memory leak. You can set the limit and have the container killed to avoid paying for the leaked GBs of memory.

Specify this limit using the memory parameter on @app.function() or Sandbox.create():

mem_request = 1024
mem_limit = 2048
@app.function(
    memory=(mem_request, mem_limit),
)
def f():
    ...
Copy
Disk limits
Running Modal containers have access to many GBs of SSD disk, but the amount of writes is limited by:

The size of the underlying worker’s SSD disk capacity
A per-container disk quota that defaults to 512 GiB.
Hitting either limit will cause the container’s disk writes to be rejected, which typically manifests as an OSError.

---

Batch Processing
Modal is optimized for large-scale batch processing, allowing functions to scale to thousands of parallel containers with zero additional configuration. Function calls can be submitted asynchronously for background execution, eliminating the need to wait for jobs to finish or tune resource allocation.

This guide covers Modal’s batch processing capabilities, from basic invocation to integration with existing pipelines.

Background Execution with .spawn_map
The fastest way to submit multiple jobs for asynchronous processing is by invoking a function with .spawn_map. When combined with the --detach flag, your App continues running until all jobs are completed.

Here’s an example of submitting 100,000 videos for parallel embedding. You can disconnect after submission, and the processing will continue to completion in the background:

# Kick off asynchronous jobs with `modal run --detach batch_processing.py`
import modal

app = modal.App("batch-processing-example")
volume = modal.Volume.from_name("video-embeddings", create_if_missing=True)

@app.function(volumes={"/data": volume})
def embed_video(video_id: int):
    # Business logic:
    # - Load the video from the volume
    # - Embed the video
    # - Save the embedding to the volume
    ...

@app.local_entrypoint()
def main():
    embed_video.spawn_map(range(100_000))
Copy
This pattern works best for jobs that store results externally—for example, in a Modal Volume, Cloud Bucket Mount, or your own database*.

* For database connections, consider using Modal Proxy to maintain a static IP across thousands of containers.

Parallel Processing with .map
Using .map allows you to offload expensive computations to powerful machines while gathering results. This is particularly useful for pipeline steps with bursty resource demands. Modal handles all infrastructure provisioning and de-provisioning automatically.

Here’s how to implement parallel video similarity queries as a single Modal function call:

# Run jobs and collect results with `modal run gather.py`
import modal

app = modal.App("gather-results-example")

@app.function(gpu="L40S")
def compute_video_similarity(query: str, video_id: int) -> tuple[int, int]:
    # Embed video with GPU acceleration & compute similarity with query
    return video_id, score


@app.local_entrypoint()
def main():
    import itertools

    queries = itertools.repeat("Modal for batch processing")
    video_ids = range(100_000)

    for video_id, score in compute_video_similarity.map(queries, video_ids):
        # Process results (e.g., extract top 5 most similar videos)
        pass
Copy
This example runs compute_video_similarity on an autoscaling pool of L40S GPUs, returning scores to a local process for further processing.

Integration with Existing Systems
The recommended way to use Modal Functions within your existing data pipeline is through deployed function invocation. After deployment, you can call Modal functions from external systems:

def external_function(inputs):
    compute_similarity = modal.Function.from_name(
        "gather-results-example",
        "compute_video_similarity"
    )
    for result in compute_similarity.map(inputs):
        # Process results
        pass
Copy
You can invoke Modal Functions from any Python context, gaining access to built-in observability, resource management, and GPU acceleration.

---

Job processing
Modal can be used as a scalable job queue to handle asynchronous tasks submitted from a web app or any other Python application. This allows you to offload up to 1 million long-running or resource-intensive tasks to Modal, while your main application remains responsive.

Creating jobs with .spawn()
The basic pattern for using Modal as a job queue involves three key steps:

Defining and deploying the job processing function using modal deploy.
Submitting a job using modal.Function.spawn()
Polling for the job’s result using modal.FunctionCall.get()
Here’s a simple example that you can run with modal run my_job_queue.py:

# my_job_queue.py
import modal

app = modal.App("my-job-queue")

@app.function()
def process_job(data):
    # Perform the job processing here
    return {"result": data}

def submit_job(data):
    # Since the `process_job` function is deployed, need to first look it up
    process_job = modal.Function.from_name("my-job-queue", "process_job")
    call = process_job.spawn(data)
    return call.object_id

def get_job_result(call_id):
    function_call = modal.FunctionCall.from_id(call_id)
    try:
        result = function_call.get(timeout=5)
    except modal.exception.OutputExpiredError:
        result = {"result": "expired"}
    except TimeoutError:
        result = {"result": "pending"}
    return result

@app.local_entrypoint()
def main():
    data = "my-data"

    # Submit the job to Modal
    call_id = submit_job(data)
    print(get_job_result(call_id))
Copy
In this example:

process_job is the Modal function that performs the actual job processing. To deploy the process_job function on Modal, run modal deploy my_job_queue.py.
submit_job submits a new job by first looking up the deployed process_job function, then calling .spawn() with the job data. It returns the unique ID of the spawned function call.
get_job_result attempts to retrieve the result of a previously submitted job using FunctionCall.from_id() and FunctionCall.get(). FunctionCall.get() waits indefinitely by default. It takes an optional timeout argument that specifies the maximum number of seconds to wait, which can be set to 0 to poll for an output immediately. Here, if the job hasn’t completed yet, we return a pending response.
The results of a .spawn() are accessible via FunctionCall.get() for up to 7 days after completion. After this period, we return an expired response.
Document OCR Web App is an example that uses this pattern.

Integration with web frameworks
You can easily integrate the job queue pattern with web frameworks like FastAPI. Here’s an example, assuming that you have already deployed process_job on Modal with modal deploy as above. This example won’t work if you haven’t deployed your app yet.

# my_job_queue_endpoint.py
import modal

image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("fastapi-modal", image=image)


@app.function()
@modal.asgi_app()
@modal.concurrent(max_inputs=20)
def fastapi_app():
    from fastapi import FastAPI

    web_app = FastAPI()

    @web_app.post("/submit")
    async def submit_job_endpoint(data):
        process_job = modal.Function.from_name("my-job-queue", "process_job")

        call = await process_job.spawn.aio(data)
        return {"call_id": call.object_id}


    @web_app.get("/result/{call_id}")
    async def get_job_result_endpoint(call_id: str):
        function_call = modal.FunctionCall.from_id(call_id)
        try:
            result = await function_call.get.aio(timeout=0)
        except modal.exception.OutputExpiredError:
            return fastapi.responses.JSONResponse(content="", status_code=404)
        except TimeoutError:
            return fastapi.responses.JSONResponse(content="", status_code=202)

        return result

    return web_app
Copy
In this example:

The /submit endpoint accepts job data, submits a new job using await process_job.spawn.aio(), and returns the job’s ID to the client.
The /result/{call_id} endpoint allows the client to poll for the job’s result using the job ID. If the job hasn’t completed yet, it returns a 202 status code to indicate that the job is still being processed. If the job has expired, it returns a 404 status code to indicate that the job is not found.
You can try this app by serving it with modal serve:

modal serve my_job_queue_endpoint.py
Copy
Then interact with its endpoints with curl:

# Make a POST request to your app endpoint with.
$ curl -X POST $YOUR_APP_ENDPOINT/submit?data=data
{"call_id":"fc-XXX"}

# Use the call_id value from above.
$ curl -X GET $YOUR_APP_ENDPOINT/result/fc-XXX
Copy
Scaling and reliability
Modal automatically scales the job queue based on the workload, spinning up new instances as needed to process jobs concurrently. It also provides built-in reliability features like automatic retries and timeout handling.

You can customize the behavior of the job queue by configuring the @app.function() decorator with options like retries, timeout, and max_containers.

---

Dynamic batching
Modal’s @batched feature allows you to accumulate requests and process them in dynamically-sized batches, rather than one-by-one.

Batching increases throughput at a potential cost to latency. Batched requests can share resources and reuse work, reducing the time and cost per request. Batching is particularly useful for GPU-accelerated machine learning workloads, as GPUs are designed to maximize throughput and are frequently bottlenecked on shareable resources, like weights stored in memory.

Static batching can lead to unbounded latency, as the function waits for a fixed number of requests to arrive. Modal’s dynamic batching waits for the lesser of a fixed time or a fixed number of requests before executing, maximizing the throughput benefit of batching while minimizing the latency penalty.

Enable dynamic batching with @batched
To enable dynamic batching, apply the @modal.batched decorator to the target Python function. Then, wrap it in @app.function() and run it on Modal, and the inputs will be accumulated and processed in batches.

Here’s what that looks like:

import modal

app = modal.App()

@app.function()
@modal.batched(max_batch_size=2, wait_ms=1000)
async def batch_add(xs: list[int], ys: list[int]) -> list[int]:
    return [x + y for x, y in zip(xs, ys)]
Copy
When you invoke a function decorated with @batched, you invoke it asynchronously on individual inputs. Outputs are returned where they were invoked.

For instance, the code below invokes the decorated batch_add function above three times, but batch_add only executes twice:

@app.local_entrypoint()
async def main():
    inputs = [(1, 300), (2, 200), (3, 100)]
    async for result in batch_add.starmap.aio(inputs):
        print(f"Sum: {result}")
        # Sum: 301
        # Sum: 202
        # Sum: 103
Copy
The first time it is executed with xs batched to [1, 2] and ys batched to [300, 200]. After about a one second delay, it is executed with xs batched to [3] and ys batched to [100]. The result is an iterator that yields 301, 202, and 103.

Use @batched with functions that take and return lists
For a Python function to be compatible with @modal.batched, it must adhere to the following rules:

The inputs to the function must be lists. In the example above, we pass xs and ys, which are both lists of ints.
The function must return a list. In the example above, the function returns a list of sums.
The lengths of all the input lists and the output list must be the same. In the example above, if L == len(xs) == len(ys), then L == len(batch_add(xs, ys)).
Modal Cls methods are compatible with dynamic batching
Methods on Modal Clses also support dynamic batching.

import modal

app = modal.App()

@app.cls()
class BatchedClass():
    @modal.batched(max_batch_size=2, wait_ms=1000)
    async def batch_add(self, xs: list[int], ys: list[int]) -> list[int]:
        return [x + y for x, y in zip(xs, ys)]
Copy
One additional rule applies to classes with Batched Methods:

If a class has a Batched Method, it cannot have other Batched Methods or Methods.
Configure the wait time and batch size of dynamic batches
The @batched decorator takes in two required configuration parameters:

max_batch_size limits the number of inputs combined into a single batch.
wait_ms limits the amount of time the Function waits for more inputs after the first input is received.
The first invocation of the Batched Function initiates a new batch, and subsequent calls add requests to this ongoing batch. If max_batch_size is reached, the batch immediately executes. If the max_batch_size is not met but wait_ms has passed since the first request was added to the batch, the unfilled batch is executed.

Selecting a batch configuration
To optimize the batching configurations for your application, consider the following heuristics:

Set max_batch_size to the largest value your function can handle, so you can amortize and parallelize as much work as possible.

Set wait_ms to the difference between your targeted latency and the execution time. Most applications have a targeted latency, and this allows the latency of any request to stay within that limit.

Serve web endpoints with dynamic batching
Here’s a simple example of serving a Function that batches requests dynamically with a @modal.fastapi_endpoint. Run modal serve, submit requests to the endpoint, and the Function will batch your requests on the fly.

import modal

app = modal.App(image=modal.Image.debian_slim().pip_install("fastapi"))

@app.function()
@modal.batched(max_batch_size=2, wait_ms=1000)
async def batch_add(xs: list[int], ys: list[int]) -> list[int]:
    return [x + y for x, y in zip(xs, ys)]


@app.function()
@modal.fastapi_endpoint(method="POST", docs=True)
async def add(body: dict[str, int]) -> dict[str, int]:
    result = await batch_add.remote.aio(body["x"], body["y"])
    return {"result": result}
Copy
Now, you can submit requests to the web endpoint and process them in batches. For instance, the three requests in the following example, which might be requests from concurrent clients in a real deployment, will be batched into two executions:

import asyncio
import aiohttp

async def send_post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.json()

async def main():
    # Enter the URL of your web endpoint here
    url = "https://workspace--app-name-endpoint-name.modal.run"

    async with aiohttp.ClientSession() as session:
        # Submit three requests asynchronously
        tasks = [
            send_post_request(session, url, {"x": 1, "y": 300}),
            send_post_request(session, url, {"x": 2, "y": 200}),
            send_post_request(session, url, {"x": 3, "y": 100}),
        ]
        results = await asyncio.gather(*tasks)
        for result in results:
            print(f"Sum: {result['result']}")

asyncio.run(main())

---

# Apps, Functions, and entrypoints

An [`App`](/docs/reference/modal.App) represents an application running on Modal. It groups one or more Functions for atomic deployment and acts as a shared namespace. All Functions and Clses are associated with an
App.

A [`Function`](/docs/reference/modal.Function) acts as an independent unit once it is deployed, and [scales up and down](/docs/guide/scale) independently from other Functions. If there are no live inputs to the Function then by default, no containers will run and your account will not be charged for compute resources, even if the App it belongs to is deployed.

An App can be ephemeral or deployed. You can view a list of all currently running Apps on the [`apps`](/apps) page.

The code for a Modal App defining two separate Functions might look something like this:

```python

import modal

app = modal.App(name="my-modal-app")


@app.function()
def f():
    print("Hello world!")


@app.function()
def g():
    print("Goodbye world!")

```

## Ephemeral Apps

An ephemeral App is created when you use the
[`modal run`](/docs/reference/cli/run) CLI command, or the
[`app.run`](/docs/reference/modal.App#run) method. This creates a temporary
App that only exists for the duration of your script.

Ephemeral Apps are stopped automatically when the calling program exits, or when
the server detects that the client is no longer connected.
You can use
[`--detach`](/docs/reference/cli/run) in order to keep an ephemeral App running even
after the client exits.

By using `app.run` you can run your Modal apps from within your Python scripts:

```python
def main():
    ...
    with app.run():
        some_modal_function.remote()
```

By default, running your app in this way won't propagate Modal logs and progress bar messages. To enable output, use the [`modal.enable_output`](/docs/reference/modal.enable_output) context manager:

```python
def main():
    ...
    with modal.enable_output():
        with app.run():
            some_modal_function.remote()
```

## Deployed Apps

A deployed App is created using the [`modal deploy`](/docs/reference/cli/deploy)
CLI command. The App is persisted indefinitely until you stop it via the
[web UI](/apps) or the [`modal app stop`](/docs/reference/cli/app#modal-app-stop) command. Functions in a deployed App that have an attached
[schedule](/docs/guide/cron) will be run on a schedule. Otherwise, you can
invoke them manually using
[web endpoints or Python](/docs/guide/trigger-deployed-functions).

Deployed Apps are named via the [`App`](/docs/reference/modal.App#modalapp)
constructor. Re-deploying an existing `App` (based on the name) will update it
in place.

## Entrypoints for ephemeral Apps

The code that runs first when you `modal run` an App is called the "entrypoint".

You can register a local entrypoint using the
[`@app.local_entrypoint()`](/docs/reference/modal.App#local_entrypoint)
decorator. You can also use a regular Modal function as an entrypoint, in which
case only the code in global scope is executed locally.

### Argument parsing

If your entrypoint function takes arguments with primitive types, `modal run`
automatically parses them as CLI options. For example, the following function
can be called with `modal run script.py --foo 1 --bar "hello"`:

```python
# script.py

@app.local_entrypoint()
def main(foo: int, bar: str):
    some_modal_function.remote(foo, bar)
```

If you wish to use your own argument parsing library, such as `argparse`, you can instead accept a variable-length argument list for your entrypoint or your function. In this case, Modal skips CLI parsing and forwards CLI arguments as a tuple of strings. For example, the following function can be invoked with `modal run my_file.py --foo=42 --bar="baz"`:

```python
import argparse

@app.function()
def train(*arglist):
    parser = argparse.ArgumentParser()
    parser.add_argument("--foo", type=int)
    parser.add_argument("--bar", type=str)
    args = parser.parse_args(args = arglist)
```

### Manually specifying an entrypoint

If there is only one `local_entrypoint` registered,
[`modal run script.py`](/docs/reference/cli/run) will automatically use it. If
you have no entrypoint specified, and just one decorated Modal function, that
will be used as a remote entrypoint instead. Otherwise, you can direct
`modal run` to use a specific entrypoint.

For example, if you have a function decorated with
[`@app.function()`](/docs/reference/modal.App#function) in your file:

```python
# script.py

@app.function()
def f():
    print("Hello world!")


@app.function()
def g():
    print("Goodbye world!")


@app.local_entrypoint()
def main():
    f.remote()
```

Running [`modal run script.py`](/docs/reference/cli/run) will execute the `main`
function locally, which would call the `f` function remotely. However you can
instead run `modal run script.py::app.f` or `modal run script.py::app.g` to
execute `f` or `g` directly.

## Apps were once Stubs

The `modal.App` class in the client was previously called `modal.Stub`. The
old name was kept as an alias for some time, but from Modal 1.0.0 onwards,
using `modal.Stub` will result in an error.

---

# Invoking deployed functions

Modal lets you take a function created by a
[deployment](/docs/guide/managing-deployments) and call it from other contexts.

There are two ways of invoking deployed functions. If the invoking client is
running Python, then the same
[Modal client library](https://pypi.org/project/modal/) used to write Modal code
can be used. HTTPS is used if the invoking client is not running Python and
therefore cannot import the Modal client library.

## Invoking with Python

Some use cases for Python invocation include:

- An existing Python web server (eg. Django, Flask) wants to invoke Modal
  functions.
- You have split your product or system into multiple Modal applications that
  deploy independently and call each other.

### Function lookup and invocation basics

Let's say you have a script `my_shared_app.py` and this script defines a Modal
app with a function that computes the square of a number:

```python
import modal

app = modal.App("my-shared-app")


@app.function()
def square(x: int):
    return x ** 2
```

You can deploy this app to create a persistent deployment:

```
% modal deploy shared_app.py
✓ Initialized.
✓ Created objects.
├── 🔨 Created square.
├── 🔨 Mounted /Users/erikbern/modal/shared_app.py.
✓ App deployed! 🎉

View Deployment: https://modal.com/apps/erikbern/my-shared-app
```

Let's try to run this function from a different context. For instance, let's
fire up the Python interactive interpreter:

```bash
% python
Python 3.9.5 (default, May  4 2021, 03:29:30)
[Clang 12.0.0 (clang-1200.0.32.27)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import modal
>>> f = modal.Function.from_name("my-shared-app", "square")
>>> f.remote(42)
1764
>>>
```

This works exactly the same as a regular modal `Function` object. For example,
you can `.map()` over functions invoked this way too:

```bash
>>> f = modal.Function.from_name("my-shared-app", "square")
>>> f.map([1, 2, 3, 4, 5])
[1, 4, 9, 16, 25]
```

#### Authentication

The Modal Python SDK will read the token from `~/.modal.toml` which typically is
created using `modal token new`.

Another method of providing the credentials is to set the environment variables
`MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`. If you want to call a Modal function
from a context such as a web server, you can expose these environment variables
to the process.

#### Lookup of lifecycle functions

[Lifecycle functions](/docs/guide/lifecycle-functions) are defined on classes,
which you can look up in a different way. Consider this code:

```python
import modal

app = modal.App("my-shared-app")


@app.cls()
class MyLifecycleClass:
    @modal.enter()
    def enter(self):
        self.var = "hello world"

    @modal.method()
    def foo(self):
        return self.var
```

Let's say you deploy this app. You can then call the function by doing this:

```bash
>>> cls = modal.Cls.from_name("my-shared-app", "MyLifecycleClass")
>>> obj = cls()  # You can pass any constructor arguments here
>>> obj.foo.remote()
'hello world'
```

### Asynchronous invocation

In certain contexts, a Modal client will need to trigger Modal functions without
waiting on the result. This is done by spawning functions and receiving a
[`FunctionCall`](/docs/reference/modal.FunctionCall) as a
handle to the triggered execution.

The following is an example of a Flask web server (running outside Modal) which
accepts model training jobs to be executed within Modal. Instead of the HTTP
POST request waiting on a training job to complete, which would be infeasible,
the relevant Modal function is spawned and the
[`FunctionCall`](/docs/reference/modal.FunctionCall)
object is stored for later polling of execution status.

```python
from uuid import uuid4
from flask import Flask, jsonify, request

app = Flask(__name__)
pending_jobs = {}

...

@app.route("/jobs", methods = ["POST"])
def create_job():
    predict_fn = modal.Function.from_name("example", "train_model")
    job_id = str(uuid4())
    function_call = predict_fn.spawn(
        job_id=job_id,
        params=request.json,
    )
    pending_jobs[job_id] = function_call
    return {
        "job_id": job_id,
        "status": "pending",
    }
```

### Importing a Modal function between Modal apps

You can also import one function defined in an app from another app:

```python
import modal

app = modal.App("another-app")

square = modal.Function.from_name("my-shared-app", "square")


@app.function()
def cube(x):
    return x * square.remote(x)


@app.local_entrypoint()
def main():
    assert cube.remote(42) == 74088
```

### Comparison with HTTPS

Compared with HTTPS invocation, Python invocation has the following benefits:

- Avoids the need to create web endpoint functions.
- Avoids handling serialization of request and response data between Modal and
  your client.
- Uses the Modal client library's built-in authentication.
  - Web endpoints are public to the entire internet, whereas function `lookup`
    only exposes your code to you (and your org).
- You can work with shared Modal functions as if they are normal Python
  functions, which might be more convenient.

## Invoking with HTTPS

Any application that can make HTTPS requests can interact with deployed Modal
applications via [web endpoint functions](/docs/guide/webhooks). Note that
all deployed web endpoint functions have [a stable HTTPS
URL](/docs/guide/webhook-urls).

Some use cases for HTTPS invocation include:

- Calling Modal functions from a web browser client running JavaScript
- Calling Modal functions from backend services in languages we don't yet have
  official SDKs for (Java, Ruby, etc.)
- Calling Modal functions using UNIX tools (`curl`, `wget`)

However, if the client of your Modal deployment is running Python, JavaScript,
or Go, it's better to use the [Modal Python
SDK](https://pypi.org/project/modal/) or [libmodal SDKs for JavaScript and
Go](/docs/guide/sdk-javascript-go) to invoke your Modal code.

For more detail on setting up functions for invocation over HTTP see the
[web endpoints guide](/docs/guide/webhooks).

---

# Managing deployments

Once you've finished using `modal run` or `modal serve` to iterate on your Modal
code, it's time to deploy. A Modal deployment creates and then persists an
application and its objects, providing the following benefits:

- Repeated application function executions will be grouped under the deployment,
  aiding observability and usage tracking. Programmatically triggering lots of
  ephemeral App runs can clutter your web and CLI interfaces.
- Function calls are much faster because deployed functions are persistent and
  reused, not created on-demand by calls. Learn how to trigger deployed
  functions in
  [Invoking deployed functions](/docs/guide/trigger-deployed-functions).
- [Scheduled functions](/docs/guide/cron) will continue scheduling separate from
  any local iteration you do, and will notify you on failure.
- [Web endpoints](/docs/guide/webhooks) keep running when you close your laptop,
  and their URL address matches the deployment name.

## Creating deployments

Deployments are created using the
[`modal deploy` command](/docs/reference/cli/app#modal-app-list).

```
 % modal deploy -m whisper_pod_transcriber.main
✓ Initialized. View app page at https://modal.com/apps/ap-PYc2Tb7JrkskFUI8U5w0KG.
✓ Created objects.
├── 🔨 Created populate_podcast_metadata.
├── 🔨 Mounted /home/ubuntu/whisper_pod_transcriber at /root/whisper_pod_transcriber
├── 🔨 Created fastapi_app => https://modal-labs-whisper-pod-transcriber-fastapi-app.modal.run
├── 🔨 Mounted /home/ubuntu/whisper_pod_transcriber/whisper_frontend/dist at /assets
├── 🔨 Created search_podcast.
├── 🔨 Created refresh_index.
├── 🔨 Created transcribe_segment.
├── 🔨 Created transcribe_episode..
└── 🔨 Created fetch_episodes.
✓ App deployed! 🎉

View Deployment: https://modal.com/apps/modal-labs/whisper-pod-transcriber
```

Running this command on an existing deployment will redeploy the App,
incrementing its version. For detail on how live deployed apps transition
between versions, see the [Updating deployments](#updating-deployments) section.

Deployments can also be created programmatically using Modal's
[Python API](/docs/reference/modal.App#deploy).

## Viewing deployments

Deployments can be viewed in the [web UI](/apps) on an App's "Deployment History"
page, or from the command line using the
[`modal app list` command](/docs/reference/cli/app#modal-app-list).

### Deployment history on metric charts

You can overlay deployment history information on your Function's metric charts by enabling
the **Show Deployments** toggle. Each marker represents one or more deployments
that occurred within a time bucket.

Hovering over a marker shows the version number and timestamp of each deployment, plus a link to the full "Deployment History" page.

![Deployment history overlay on a metric chart](https://modal-cdn.com/cdnbot/deployment-historyt991cvw__b284b7fa.webp)

## Updating deployments

A deployment can deploy a new App or redeploy a new version of an existing
deployed App. It's useful to understand how Modal handles the transition between
versions when an App is redeployed. In general, Modal aims to support
zero-downtime deployments by gradually transitioning traffic to the new version.

If the deployment involves building new versions of the Images used by the App,
the build process will need to complete successfully. The existing version of
the App will continue to handle requests during this time. Errors during the
build will abort the deployment with no change to the status of the App.

After the build completes, Modal will start to bring up new containers running
the latest version of the App. The existing containers will continue handling
requests (using the previous version of the App) until the new containers have
completed their cold start.

Once the new containers are ready, old containers will stop accepting new
requests. However, the old containers will continue running any requests they
had previously accepted. The old containers will not terminate until they have
finished processing all ongoing requests.

Any warm pool containers will also be cycled during a deployment, as the
previous version's warm pool are now outdated.

## Deployment rollbacks

<Callout variant="gated-feature">
Deployment rollbacks are available on the <a href="/pricing">Team and Enterprise plans</a>. Visit <a href="/settings/plans">workspace settings</a> to upgrade.
</Callout>

To quickly reset an App back to a previous version, you can perform a deployment
_rollback_. Rollbacks can be triggered from either the App dashboard or the CLI.
Rollback deployments look like new deployments: they increment the version number
and are attributed to the user who triggered the rollback. But the App's functions
and metadata will be reset to their previous state independently of your current
App codebase.

## Stopping deployments

Deployed apps can be stopped in the web UI by clicking the red "Stop app" button on
the App's "Overview" page, or alternatively from the command line using the
[`modal app stop` command](/docs/reference/cli/app#modal-app-stop).

Stopping an App is a destructive action. Apps cannot be restarted from this state;
a new App will need to be deployed from the same source files. Objects associated
with stopped deployments will eventually be garbage collected.

---

# Secrets

Securely provide credentials and other sensitive information to your Modal Functions with Secrets.

You can create and edit Secrets via
the [dashboard](/secrets),
the command line interface ([`modal secret`](/docs/reference/cli/secret)), and
programmatically from Python code ([`modal.Secret`](/docs/reference/modal.Secret)).

To inject Secrets into the container running your Function, add the
`secrets=[...]` argument to your `app.function` or `app.cls` decoration.

## Limits

Each key-value pair in a Secret is subject to the following limits:

- **Key names** can be at most **16,384 characters** long. They must contain only letters, digits, and underscores, and cannot start with a digit.
- **Values** can be at most **32,768 characters** long.

If you need to provide larger values to your containers, consider writing the data to a [Volume](/docs/guide/volumes) and reading it at runtime.

## Deploy Secrets from the Modal Dashboard

The most common way to create a Modal Secret is to use the
[Secrets panel of the Modal dashboard](/secrets),
which also shows any existing Secrets.

When you create a new Secret, you'll be prompted with a number of templates to help you get started.
These templates demonstrate standard formats for credentials for everything from Postgres and MongoDB
to Weights & Biases and Hugging Face.

## Use Secrets in your Modal Apps

You can then use your Secret by constructing it `from_name` when defining a Modal App
and then accessing its contents as environment variables.
For example, if you have a Secret called `secret-keys` containing the key
`MY_PASSWORD`:

```python
@app.function(secrets=[modal.Secret.from_name("secret-keys")])
def some_function():
    import os

    secret_key = os.environ["MY_PASSWORD"]
    ...
```

Each Secret can contain multiple keys and values but you can also inject
multiple Secrets, allowing you to separate Secrets into smaller reusable units:

```python
@app.function(secrets=[
    modal.Secret.from_name("my-secret-name"),
    modal.Secret.from_name("other-secret"),
])
def other_function():
    ...
```

The Secrets are applied in order, so key-values from later `modal.Secret`
objects in the list will overwrite earlier key-values in the case of a clash.
For example, if both `modal.Secret` objects above contained the key `FOO`, then
the value from `"other-secret"` would always be present in `os.environ["FOO"]`.

## Create Secrets programmatically

In addition to defining Secrets on the web dashboard, you can
programmatically create a Secret directly in your script and send it along to
your Function using `Secret.from_dict(...)`. This can be useful if you want to
send Secrets from your local development machine to the remote Modal App.

```python
import os

if modal.is_local():
    local_secret = modal.Secret.from_dict({"FOO": os.environ["LOCAL_FOO"]})
else:
    local_secret = modal.Secret.from_dict({})


@app.function(secrets=[local_secret])
def some_function():
    import os

    print(os.environ["FOO"])
```

If you have [`python-dotenv`](https://pypi.org/project/python-dotenv/) installed,
you can also use `Secret.from_dotenv()` to create a Secret from the variables in a `.env`
file

```python
@app.function(secrets=[modal.Secret.from_dotenv()])
def some_other_function():
    print(os.environ["USERNAME"])
```

## Interact with Secrets from the command line

You can create, list, and delete your Modal Secrets with the `modal secret` command line interface.

View your Secrets and their timestamps with

```bash
modal secret list
```

Create a new Secret by passing `{KEY}={VALUE}` pairs to `modal secret create`:

```bash
modal secret create database-secret PGHOST=uri PGPORT=5432 PGUSER=admin PGPASSWORD=hunter2
```

or using environment variables (assuming below that the `PGPASSWORD` environment variable is set
e.g. by your CI system):

```bash
modal secret create database-secret PGHOST=uri PGPORT=5432 PGUSER=admin PGPASSWORD="$PGPASSWORD"
```

Remove Secrets by passing their name to `modal secret delete`:

```bash
modal secret delete database-secret
```

---

# Environment variables

The Modal runtime sets several environment variables during initialization. The
keys for these environment variables are reserved and cannot be overridden by
your Function or Sandbox configuration.

These variables provide information about the container's runtime
environment.

## Container runtime environment variables

The following variables are present in every Modal container:

- **`MODAL_CLOUD_PROVIDER`** — Modal executes containers across a number of cloud
  providers ([AWS](https://aws.amazon.com/), [GCP](https://cloud.google.com/),
  [OCI](https://www.oracle.com/cloud/)). This variable specifies which cloud
  provider the Modal container is running within.
- **`MODAL_IMAGE_ID`** — The ID of the
  [`modal.Image`](/docs/reference/modal.Image) used by the Modal container.
- **`MODAL_REGION`** — This will correspond to a geographic area identifier from
  the cloud provider associated with the Modal container (see above). For AWS, the
  identifier is a "region". For GCP it is a "zone", and for OCI it is an
  "availability domain". Example values are `us-east-1` (AWS), `us-central1`
  (GCP), `us-ashburn-1` (OCI). See the [full list here](/docs/guide/region-selection#region-options).
- **`MODAL_TASK_ID`** — The ID of the container running the Modal Function or Sandbox.

## Function runtime environment variables

The following variables are present in containers running Modal Functions:

- **`MODAL_ENVIRONMENT`** — The name of the
  [Modal Environment](/docs/guide/environments) the container is running within.
- **`MODAL_IS_REMOTE`** - Set to '1' to indicate that Modal Function code is running in
  a remote container.
- **`MODAL_IDENTITY_TOKEN`** — An [OIDC token](/docs/guide/oidc-integration)
  encoding the identity of the Modal Function.

## Sandbox environment variables

The following variables are present within [`modal.Sandbox`](/docs/reference/modal.Sandbox) instances.

- **`MODAL_SANDBOX_ID`** — The ID of the Sandbox.

## Container image environment variables

The container image layers used by a `modal.Image` may set
environment variables. These variables will be present within your container's runtime
environment. For example, the
[`debian_slim`](/docs/reference/modal.Image#debian_slim) image sets the
`GPG_KEY` variable.

To override image variables or set new ones, use the
[`.env`](https://modal.com/docs/reference/modal.Image#env) method provided by
`modal.Image`.

---

# Web endpoints

This guide explains how to set up web endpoints with Modal.

All deployed Modal Functions can be [invoked from any other Python application](/docs/guide/trigger-deployed-functions)
using the Modal client library. We additionally provide multiple ways to expose
your Functions over the web for non-Python clients.

You can [turn any Python function into a web endpoint](#simple-endpoints) with a single line
of code, you can [serve a full app](#serving-asgi-and-wsgi-apps) using
frameworks like FastAPI, Django, or Flask, or you can
[serve anything that speaks HTTP and listens on a port](#non-asgi-web-servers).

Below we walk through each method, assuming you're familiar with web applications outside of Modal.
For a detailed walkthrough of basic web endpoints on Modal aimed at developers new to web applications,
see [this tutorial](/docs/examples/basic_web).

## Simple endpoints

The easiest way to create a web endpoint from an existing Python function is to use the
[`@modal.fastapi_endpoint` decorator](/docs/reference/modal.fastapi_endpoint).

```python
image = modal.Image.debian_slim().pip_install("fastapi[standard]")


@app.function(image=image)
@modal.fastapi_endpoint()
def f():
    return "Hello world!"
```

This decorator wraps the Modal Function in a
[FastAPI application](#how-do-web-endpoints-run-in-the-cloud).

_Note: Prior to v0.73.82, this function was named `@modal.web_endpoint`_.

### Developing with `modal serve`

You can run this code as an ephemeral app, by running the command

```shell
modal serve server_script.py
```

Where `server_script.py` is the file name of your code. This will create an
ephemeral app for the duration of your script (until you hit Ctrl-C to stop it).
It creates a temporary URL that you can use like any other REST endpoint. This
URL is on the public internet.

The `modal serve` command will live-update an app when any of its supporting
files change.

Live updating is particularly useful when working with apps containing web
endpoints, as any changes made to web endpoint handlers will show up almost
immediately, without requiring a manual restart of the app.

### Deploying with `modal deploy`

You can also deploy your app and create a persistent web endpoint in the cloud
by running `modal deploy`:

<Asciinema recordingId="jYpIj1nL6JI9cw4W77GV2l5Wl" />

### Passing arguments to an endpoint

When using `@modal.fastapi_endpoint`, you can add
[query parameters](https://fastapi.tiangolo.com/tutorial/query-params/) which
will be passed to your Function as arguments. For instance

```python
image = modal.Image.debian_slim().pip_install("fastapi[standard]")


@app.function(image=image)
@modal.fastapi_endpoint()
def square(x: int):
    return {"square": x**2}
```

If you hit this with a URL-encoded query string with the `x` parameter present,
the Function will receive the value as an argument:

```
$ curl https://modal-labs--web-endpoint-square-dev.modal.run?x=42
{"square":1764}
```

If you want to use a `POST` request, you can use the `method` argument to
`@modal.fastapi_endpoint` to set the HTTP verb. To accept any valid JSON object,
[use `dict` as your type annotation](https://fastapi.tiangolo.com/tutorial/body-nested-models/?h=dict#bodies-of-arbitrary-dicts)
and FastAPI will handle the rest.

```python
image = modal.Image.debian_slim().pip_install("fastapi[standard]")


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def square(item: dict):
    return {"square": item['x']**2}
```

This now creates an endpoint that takes a JSON body:

```
$ curl -X POST -H 'Content-Type: application/json' --data-binary '{"x": 42}' https://modal-labs--web-endpoint-square-dev.modal.run
{"square":1764}
```

This is often the easiest way to get started, but note that FastAPI recommends
that you use
[typed Pydantic models](https://fastapi.tiangolo.com/tutorial/body/) in order to
get automatic validation and documentation. FastAPI also lets you pass data to
web endpoints in other ways, for instance as
[form data](https://fastapi.tiangolo.com/tutorial/request-forms/) and
[file uploads](https://fastapi.tiangolo.com/tutorial/request-files/).

## How do web endpoints run in the cloud?

Note that web endpoints, like everything else on Modal, only run when they need
to. When you hit the web endpoint the first time, it will boot up the container,
which might take a few seconds. Modal keeps the container alive for a short
period in case there are subsequent requests. If there are a lot of requests,
Modal might create more containers running in parallel.

For the shortcut `@modal.fastapi_endpoint` decorator, Modal wraps your function in a
[FastAPI](https://fastapi.tiangolo.com/) application. This means that the
[Image](/docs/guide/images)
your Function uses must have FastAPI installed, and the Functions that you write
need to follow its request and response
[semantics](https://fastapi.tiangolo.com/tutorial). Web endpoint Functions can use
all of FastAPI's powerful features, such as Pydantic models for automatic validation,
typed query and path parameters, and response types.

Here's everything together, combining Modal's abilities to run functions in
user-defined containers with the expressivity of FastAPI:

```python
import modal
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

image = modal.Image.debian_slim().pip_install("fastapi[standard]", "boto3")
app = modal.App(image=image)


class Item(BaseModel):
    name: str
    qty: int = 42


@app.function()
@modal.fastapi_endpoint(method="POST")
def f(item: Item):
    import boto3
    # do things with boto3...
    return HTMLResponse(f"<html>Hello, {item.name}!</html>")
```

This endpoint definition would be called like so:

```bash
curl -d '{"name": "Erik", "qty": 10}' \
    -H "Content-Type: application/json" \
    -X POST https://ecorp--web-demo-f-dev.modal.run
```

Or in Python with the [`requests`](https://pypi.org/project/requests/) library:

```python
import requests

data = {"name": "Erik", "qty": 10}
requests.post("https://ecorp--web-demo-f-dev.modal.run", json=data, timeout=10.0)
```

## Serving ASGI and WSGI apps

You can also serve any app written in an
[ASGI](https://asgi.readthedocs.io/en/latest/) or
[WSGI](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface)-compatible
web framework on Modal.

ASGI provides support for async web frameworks. WSGI provides support for
synchronous web frameworks.

### ASGI apps - FastAPI, FastHTML, Starlette

For ASGI apps, you can create a function decorated with
[`@modal.asgi_app`](/docs/reference/modal.asgi_app) that returns a reference to
your web app:

```python
image = modal.Image.debian_slim().pip_install("fastapi[standard]")

@app.function(image=image)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI, Request

    web_app = FastAPI()


    @web_app.post("/echo")
    async def echo(request: Request):
        body = await request.json()
        return body

    return web_app
```

Now, as before, when you deploy this script as a Modal App, you get a URL for
your app that you can hit:

<Asciinema recordingId="fNSKPUK5hiiFgQEx0pDaMCYBg" />

The `@modal.concurrent` decorator enables a single container
to process multiple inputs at once, taking advantage of the asynchronous
event loops in ASGI applications. See [this guide](/docs/guide/concurrent-inputs)
for details.

#### ASGI Lifespan

While we recommend using [`@modal.enter`](https://modal.com/docs/guide/lifecycle-functions#enter) for defining container lifecycle hooks, we also support the [ASGI lifespan protocol](https://asgi.readthedocs.io/en/latest/specs/lifespan.html). Lifespans begin when containers start, typically at the time of the first request. Here's an example using [FastAPI](https://fastapi.tiangolo.com/advanced/events/#lifespan):

```python
import modal

app = modal.App("fastapi-lifespan-app")

image = modal.Image.debian_slim().pip_install("fastapi[standard]")

@app.function(image=image)
@modal.asgi_app()
def fastapi_app_with_lifespan():
    from fastapi import FastAPI, Request

    def lifespan(wapp: FastAPI):
        print("Starting")
        yield
        print("Shutting down")

    web_app = FastAPI(lifespan=lifespan)

    @web_app.get("/")
    async def hello(request: Request):
        return "hello"

    return web_app
```

### WSGI apps - Django, Flask

You can serve WSGI apps using the
[`@modal.wsgi_app`](/docs/reference/modal.wsgi_app) decorator:

```python
image = modal.Image.debian_slim().pip_install("flask")


@app.function(image=image)
@modal.concurrent(max_inputs=100)
@modal.wsgi_app()
def flask_app():
    from flask import Flask, request

    web_app = Flask(__name__)


    @web_app.post("/echo")
    def echo():
        return request.json

    return web_app
```

See [Flask's docs](https://flask.palletsprojects.com/en/2.1.x/deploying/asgi/)
for more information on using Flask as a WSGI app.

Because WSGI apps are synchronous, concurrent inputs will be run on separate
threads. See [this guide](/docs/guide/concurrent-inputs) for details.

## Non-ASGI web servers

Not all web frameworks offer an ASGI or WSGI interface. For example,
[`aiohttp`](https://docs.aiohttp.org/) and [`tornado`](https://www.tornadoweb.org/)
use their own asynchronous network binding, while others like
[`text-generation-inference`](https://github.com/huggingface/text-generation-inference)
actually expose a Rust-based HTTP server running as a subprocess.

For these cases, you can use the
[`@modal.web_server`](/docs/reference/modal.web_server) decorator to "expose" a
port on the container:

```python
@app.function()
@modal.concurrent(max_inputs=100)
@modal.web_server(8000)
def my_file_server():
    import subprocess
    subprocess.Popen("python -m http.server -d / 8000", shell=True)
```

Just like all web endpoints on Modal, this is only run on-demand. The function
is executed on container startup, creating a file server at the root directory.
When you hit the web endpoint URL, your request will be routed to the file
server listening on port `8000`.

For `@modal.web_server` endpoints, you need to make sure that the application binds to
the external network interface, not just localhost. This usually means binding
to `0.0.0.0` instead of `127.0.0.1`.

See, for instance, our examples of how to serve [Streamlit](/docs/examples/serve_streamlit) and
[vLLM](/docs/examples/vllm_inference) on Modal.

## Serve many configurations with parametrized functions

Python functions that launch ASGI/WSGI apps or web servers on Modal
cannot take arguments.

One simple pattern for allowing client-side configuration of these web endpoints
is to use [parametrized functions](/docs/guide/parametrized-functions).
Each different choice for the values of the parameters will create a distinct
auto-scaling container pool.

```python
@app.cls()
@modal.concurrent(max_inputs=100)
class Server:
    root: str = modal.parameter(default=".")

    @modal.web_server(8000)
    def files(self):
        import subprocess
        subprocess.Popen(f"python -m http.server -d {self.root} 8000", shell=True)
```

The values are provided in URLs as query parameters:

```bash
curl https://ecorp--server-files.modal.run		# use the default value
curl https://ecorp--server-files.modal.run?root=.cache  # use a different value
curl https://ecorp--server-files.modal.run?root=%2F	# don't forget to URL encode!
```

For details, see [this guide to parametrized functions](/docs/guide/parametrized-functions).

## WebSockets

Functions annotated with `@modal.web_server`, `@modal.asgi_app`, or `@modal.wsgi_app` also support
the WebSocket protocol. Consult your web framework for appropriate documentation
on how to use WebSockets with that library.

WebSockets on Modal maintain a single function call per connection, which can be
useful for keeping state around. Most of the time, you will want to set your
handler function to [allow concurrent inputs](/docs/guide/concurrent-inputs),
which allows multiple simultaneous WebSocket connections to be handled by the
same container.

We support the full WebSocket protocol as per
[RFC 6455](https://www.rfc-editor.org/rfc/rfc6455), but we do not yet have
support for [RFC 8441](https://www.rfc-editor.org/rfc/rfc8441) (WebSockets over
HTTP/2) or [RFC 7692](https://datatracker.ietf.org/doc/html/rfc7692)
(`permessage-deflate` extension). WebSocket messages can be up to 2 MiB each.

## Performance and scaling

If you have no active containers when the web endpoint receives a request, it will
experience a "cold start". Consult the guide page on
[cold start performance](/docs/guide/cold-start) for more information on when
Functions will cold start and advice how to mitigate the impact.

If your Function uses `@modal.concurrent`, multiple requests to the same
endpoint may be handled by the same container. Beyond this limit, additional
containers will start up to scale your App horizontally. When you reach the
Function's limit on containers, requests will queue for handling.

Each workspace on Modal has a rate limit on total operations. For a new account,
this is set to 200 function inputs or web endpoint requests per second, with a
burst multiplier of 5 seconds. If you reach the rate limit, excess requests to
web endpoints will return a
[429 status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429),
and you'll need to [get in touch](mailto:support@modal.com) with us about
raising the limit.

Web endpoint request bodies can be up to 4 GiB, and their response bodies are
unlimited in size.

## Authentication

Modal offers first-class web endpoint protection via [proxy auth tokens](https://modal.com/docs/guide/webhook-proxy-auth).
Proxy auth tokens protect web endpoints by requiring a key and token combination to be passed
in the `Modal-Key` and `Modal-Secret` headers.
Modal works as a proxy, rejecting requests that aren't authorized to access
your endpoint.

We also support standard techniques for securing web servers.

### Token-based authentication

This is easy to implement in whichever framework you're using. For example, if
you're using `@modal.fastapi_endpoint` or `@modal.asgi_app` with FastAPI, you
can validate a Bearer token like this:

```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import modal

image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App("auth-example", image=image)

auth_scheme = HTTPBearer()


@app.function(secrets=[modal.Secret.from_name("my-web-auth-token")])
@modal.fastapi_endpoint()
async def f(request: Request, token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    import os

    print(os.environ["AUTH_TOKEN"])

    if token.credentials != os.environ["AUTH_TOKEN"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Function body
    return "success!"
```

This assumes you have a [Modal Secret](https://modal.com/secrets) named
`my-web-auth-token` created, with contents `{AUTH_TOKEN: secret-random-token}`.
Now, your endpoint will return a 401 status code except when you hit it with the
correct `Authorization` header set (note that you have to prefix the token with
`Bearer `):

```bash
curl --header "Authorization: Bearer secret-random-token" https://modal-labs--auth-example-f.modal.run
```

### Client IP address

You can access the IP address of the client making the request. This can be used
for geolocation, whitelists, blacklists, and rate limits.

```python
from fastapi import Request

import modal

image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App(image=image)


@app.function()
@modal.fastapi_endpoint()
def get_ip_address(request: Request):
    return f"Your IP address is {request.client.host}"
```

---

# Streaming endpoints

Modal `fastapi_endpoint`s support streaming responses using FastAPI's
[`StreamingResponse`](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
class. This class accepts asynchronous generators, synchronous generators, or
any Python object that implements the
[_iterator protocol_](https://docs.python.org/3/library/stdtypes.html#typeiter),
and can be used with Modal Functions!

## Simple example

This simple example combines Modal's `@modal.fastapi_endpoint` decorator with a
`StreamingResponse` object to produce a real-time SSE response.

```python
import time

def fake_event_streamer():
    for i in range(10):
        yield f"data: some data {i}\n\n".encode()
        time.sleep(0.5)


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]"))
@modal.fastapi_endpoint()
def stream_me():
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        fake_event_streamer(), media_type="text/event-stream"
    )
```

If you serve this web endpoint and hit it with `curl`, you will see the ten SSE
events progressively appear in your terminal over a ~5 second period.

```shell
curl --no-buffer https://modal-labs--example-streaming-stream-me.modal.run
```

The MIME type of `text/event-stream` is important in this example, as it tells
the downstream web server to return responses immediately, rather than buffering
them in byte chunks (which is more efficient for compression).

You can still return other content types like large files in streams, but they
are not guaranteed to arrive as real-time events.

## Streaming responses with `.remote`

A Modal Function wrapping a generator function body can have its response passed
directly into a `StreamingResponse`. This is particularly useful if you want to
do some GPU processing in one Modal Function that is called by a CPU-based web
endpoint Modal Function.

```python
@app.function(gpu="any")
def fake_video_render():
    for i in range(10):
        yield f"data: finished processing some data from GPU {i}\n\n".encode()
        time.sleep(1)


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]"))
@modal.fastapi_endpoint()
def hook():
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        fake_video_render.remote_gen(), media_type="text/event-stream"
    )
```

## Streaming responses with `.map` and `.starmap`

You can also combine Modal Function parallelization with streaming responses,
enabling applications to service a request by farming out to dozens of
containers and iteratively returning result chunks to the client.

```python
@app.function()
def map_me(i):
    return f"segment {i}\n"


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]"))
@modal.fastapi_endpoint()
def mapped():
    from fastapi.responses import StreamingResponse
    return StreamingResponse(map_me.map(range(10)), media_type="text/plain")
```

This snippet will spread the ten `map_me(i)` executions across containers, and
return each string response part as it completes. By default the results will be
ordered, but if this isn't necessary pass `order_outputs=False` as keyword
argument to the `.map` call.

### Asynchronous streaming

The example above uses a synchronous generator, which automatically runs on its
own thread, but in asynchronous applications, a loop over a `.map` or `.starmap`
call can block the event loop. This will stop the `StreamingResponse` from
returning response parts iteratively to the client.

To avoid this, you can use the `.aio()` method to convert a synchronous `.map`
into its async version. Also, other blocking calls should be offloaded to a
separate thread with `asyncio.to_thread()`. For example:

```python
@app.function(gpu="any", image=modal.Image.debian_slim().pip_install("fastapi[standard]"))
@modal.fastapi_endpoint()
async def transcribe_video(request):
    from fastapi.responses import StreamingResponse

    segments = await asyncio.to_thread(split_video, request)
    return StreamingResponse(wrapper(segments), media_type="text/event-stream")


# Notice that this is an async generator.
async def wrapper(segments):
    async for partial_result in transcribe_video.map.aio(segments):
        yield "data: " + partial_result + "\n\n"
```

## Further examples

- Complete code the for the simple examples given above is available
  [in our modal-examples Github repository](https://github.com/modal-labs/modal-examples/blob/main/07_web_endpoints/streaming.py).
- [An end-to-end example of streaming Youtube video transcriptions with OpenAI's whisper model.](https://github.com/modal-labs/modal-examples/blob/main/06_gpu_and_ml/openai_whisper/streaming/main.py)

---

# Tunnels

Modal allows you to expose live TCP ports on a Modal container. This is done by
creating a _tunnel_ that forwards the port to the public Internet.

```python
import modal

app = modal.App()


@app.function()
def start_app():
    # Inside this `with` block, port 8000 on the container can be accessed by
    # the address at `tunnel.url`, which is randomly assigned.
    with modal.forward(8000) as tunnel:
        print(f"tunnel.url        = {tunnel.url}")
        print(f"tunnel.tls_socket = {tunnel.tls_socket}")
        # ... start some web server at port 8000, using any framework
```

Tunnels are direct connections and terminate TLS automatically. Within a few
milliseconds of container startup, this function prints a message such as:

```
tunnel.url        = https://wtqcahqwhd4tu0.r5.modal.host
tunnel.tls_socket = ('wtqcahqwhd4tu0.r5.modal.host', 443)
```

You can also create tunnels on a [Sandbox](/docs/guide/sandbox-networking#forwarding-ports)
to directly expose the container's ports.

## Build with tunnels

Tunnels are the fastest way to get a low-latency, direct connection to a running
container. You can use them to run live browser applications with **interactive
terminals**, **Jupyter notebooks**, **VS Code servers**, and more.

As a quick example, here is how you would expose a Jupyter notebook:

```python
import os
import secrets
import subprocess

import modal


image = modal.Image.debian_slim().pip_install("jupyterlab")
app = modal.App(image=image)


@app.function()
def run_jupyter():
    token = secrets.token_urlsafe(13)
    with modal.forward(8888) as tunnel:
        url = tunnel.url + "/?token=" + token
        print(f"Starting Jupyter at {url}")
        subprocess.run(
            [
                "jupyter",
                "lab",
                "--no-browser",
                "--allow-root",
                "--ip=0.0.0.0",
                "--port=8888",
                "--LabApp.allow_origin='*'",
                "--LabApp.allow_remote_access=1",
            ],
            env={**os.environ, "JUPYTER_TOKEN": token, "SHELL": "/bin/bash"},
            stderr=subprocess.DEVNULL,
        )
```

When you run the function, it starts Jupyter and gives you the public URL. It's
as simple as that.

All Modal features are supported. If you
[need GPUs](https://modal.com/docs/guide/gpu), pass `gpu=` to the
`@app.function()` decorator. If you
[need more CPUs, RAM](https://modal.com/docs/guide/resources), or to attach
[volumes](https://modal.com/docs/guide/volumes), those
also just work.

### Programmable startup

The tunnel API is completely on-demand, so you can start them as the result of a
web request.

For example, you could make something like Jupyter Hub without leaving Modal,
giving your users their own Jupyter notebooks when they visit a URL:

```python
import modal


image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App(image=image)


@app.function(timeout=900)  # 15 minutes
def run_jupyter(q):
    ...  # as before, but return the URL on app.q


@app.function()
@modal.fastapi_endpoint(method="POST")
def jupyter_hub():
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse

    ...  # do some validation on the secret or bearer token

    if is_valid:
        with modal.Queue.ephemeral() as q:
            run_jupyter.spawn(q)
            url = q.get()
            return RedirectResponse(url, status_code=303)

    else:
        raise HTTPException(401, "Not authenticated")
```

This gives every user who sends a POST request to the web endpoint their own
Jupyter notebook server, on a fully isolated Modal container.

You could do the same with VS Code and get some basic version of an instant,
serverless IDE!

### Advanced: Unencrypted TCP tunnels

By default, tunnels are only exposed to the Internet at a secure random URL, and
connections have automatic TLS (the "S" in HTTPS). However, sometimes you might
need to expose a protocol like an SSH server that goes directly over TCP. In
this case, we have support for _unencrypted_ tunnels:

```python notest
with modal.forward(8000, unencrypted=True) as tunnel:
    print(f"tunnel.tcp_socket = {tunnel.tcp_socket}")
```

Might produce an output like:

```
tunnel.tcp_socket = ('r3.modal.host', 23447)
```

You can then connect over TCP, for example with `nc r3.modal.host 23447`. Unlike
encrypted TLS sockets, these cannot be given a non-guessable, cryptographically
random URL due to how the TCP protocol works, so they are assigned a random port
number instead.

## Pricing

Modal only charges for containers based on
[the resources you use](https://modal.com/pricing). There is no additional
charge for having an active tunnel.

For example, if you start a Jupyter notebook on port 8888 and access it via
tunnel, you can use it for an hour for development (with 0.01 CPUs) and then
actually run an intensive job with 16 CPUs for one minute. The amount you would
be billed for in that hour is 0.01 + 16 \* (1/60) = **0.28 CPUs**, even though
you had access to 16 CPUs without needing to restart your notebook.

## Security

Tunnels are run on Modal's private global network of Internet relays. On
startup, your container will connect to the nearest tunnel so you get the
minimum latency, very similar in performance to a direct connection with the
machine.

This makes them ideal for live debugging sessions, using web-based terminals
like [ttyd](https://github.com/tsl0922/ttyd).

The generated URLs are cryptographically random, but they are also public on the
Internet, so anyone can access your application if they are given the URL.

We do not currently do any detection of requests above L4, so if you are running
a web server, we will not add special proxy HTTP headers or translate HTTP/2.
You're just getting the TLS-encrypted TCP stream directly!

---

# Passing local data

If you have a function that needs access to some data not present in your Python
files themselves you have a few options for bundling that data with your Modal
app.

## Passing function arguments

The simplest and most straight-forward way is to read the data from your local
script and pass the data to the outermost Modal function call:

```python
import json


@app.function()
def foo(a):
    print(sum(a["numbers"]))


@app.local_entrypoint()
def main():
    data_structure = json.load(open("blob.json"))
    foo.remote(data_structure)
```

Any data of reasonable size that is serializable through
[cloudpickle](https://github.com/cloudpipe/cloudpickle) is passable as an
argument to Modal functions.

Refer to the section on [global variables](/docs/guide/global-variables) for how
to work with objects in global scope that can only be initialized locally.

## Including local files

For including local files for your Modal Functions to access, see [Defining Images](/docs/guide/images).

---

# Volumes

Volumes are a high-performance distributed file system for Modal applications. They are optimized for write-once, read-many I/O workloads, like creating machine learning model weights and distributing them for inference.

Key benefits:

- Volumes are distributed by default, so you can use them alongside Modal’s global compute pool without needing to manage replicas across regions.
- Volumes have caching and chunking optimizations built-in to maximize throughput.
- Volumes come with a fully-featured filesystem interface for easy integration into your favorite ML tools and frameworks.
- Volumes are backed by multiple underlying cloud providers to guarantee high availability.

This page is a high-level guide to using Modal Volumes.
For reference documentation on the `modal.Volume` object, see
[this page](/docs/reference/modal.Volume).
For reference documentation on the `modal volume` CLI command, see
[this page](/docs/reference/cli/volume).

## Pricing

Please refer to our [pricing page](/pricing) for up-to-date prices. We calculate usage by snapshotting your total storage once a day. When you delete data, you may still be billed for that storage for up to four days, to reflect our underlying processing costs.

## Volumes v2 (Beta)

<Callout variant="beta">

This feature is in beta. We'd love to hear your feedback — please reach out via [Slack](/slack) or email us at [support@modal.com](mailto:support@modal.com). Instructions specific to v2 Volumes will be annotated with 🌱 below.

</Callout>

Read more about [Volumes v2](#volumes-v2-overview) below.

## Creating a Volume

The easiest way to create a Volume and use it as a part of your App is to use
the [`modal volume create`](/docs/reference/cli/volume#modal-volume-create) CLI command. This will create the Volume and output
some sample code:

```bash
% modal volume create my-volume
Created volume 'my-volume' in environment 'main'.
```

> 🌱 To create a v2 Volume, pass `--version=2` in the command above.

## Using a Volume on Modal

To attach an existing Volume to a Modal Function, use [`Volume.from_name`](/docs/reference/modal.Volume#from_name):

```python
vol = modal.Volume.from_name("my-volume")


@app.function(volumes={"/data": vol})
def run():
    with open("/data/xyz.txt", "w") as f:
        f.write("hello")
    vol.commit()  # Needed to make sure all changes are persisted before exit
```

You can also browse and manipulate Volumes from an ad hoc Modal Shell:

```bash
% modal shell --volume my-volume --volume another-volume
```

Volumes will be mounted under `/mnt`.

Volumes are designed to provide up to 2.5 GB/s of bandwidth.
Actual throughput is not guaranteed and may be lower depending on network conditions.

## Downloading a file from a Volume

While there’s no file size limit for individual files in a volume, the frontend only supports downloading files up to 16 MB. For larger files, please use the CLI:

```bash
% modal volume get my-volume xyz.txt xyz-local.txt
```

### Creating Volumes lazily from code

You can also create Volumes lazily from code using:

```python
vol = modal.Volume.from_name("my-volume", create_if_missing=True)
```

> 🌱 To create a v2 Volume, pass `version=2` to the call to `from_name()` in the code above.

This will create the Volume if it doesn't exist.

## Using a Volume from outside of Modal

Volumes can also be used outside Modal via the [Python SDK](/docs/reference/modal.Volume#modalvolume) or our [CLI](/docs/reference/cli/volume).

### Using a Volume from local code

You can interact with Volumes from anywhere you like using the `modal` Python client library.

```python notest
vol = modal.Volume.from_name("my-volume")

with vol.batch_upload() as batch:
    batch.put_file("local-path.txt", "/remote-path.txt")
    batch.put_directory("/local/directory/", "/remote/directory")
    batch.put_file(io.BytesIO(b"some data"), "/foobar")
```

For more details, see the [reference documentation](/docs/reference/modal.Volume).

### Using a Volume via the command line

You can also interact with Volumes using the command line interface. You can run
`modal volume` to get a full list of its subcommands:

```bash
% modal volume
Usage: modal volume [OPTIONS] COMMAND [ARGS]...

 Read and edit modal.Volume volumes.
 Note: users of modal.NetworkFileSystem should use the modal nfs command instead.

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                            │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ File operations ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ cp       Copy within a modal.Volume. Copy source file to destination file or multiple source files to destination directory.                                                                           │
│ get      Download files from a modal.Volume object.                                                                                                                                                    │
│ ls       List files and directories in a modal.Volume volume.                                                                                                                                          │
│ put      Upload a file or directory to a modal.Volume.                                                                                                                                                 │
│ rm       Delete a file or directory from a modal.Volume.                                                                                                                                               │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Management ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ create   Create a named, persistent modal.Volume.                                                                                                                                                      │
│ delete   Delete a named, persistent modal.Volume.                                                                                                                                                      │
│ list     List the details of all modal.Volume volumes in an Environment.                                                                                                                               │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

For more details, see the [reference documentation](/docs/reference/cli/volume).

## Volume commits and reloads

Unlike a normal filesystem, you need to explicitly reload the Volume to see
changes made since it was first mounted. This reload is handled by invoking the
[`.reload()`](/docs/reference/modal.Volume#reload) method on a Volume object.
Similarly, any Volume changes made within a container need to be committed for
those the changes to become visible outside the current container. This is handled
periodically by [background commits](#background-commits) and directly by invoking
the [`.commit()`](/docs/reference/modal.Volume#commit)
method on a `modal.Volume` object.

At container creation time the latest state of an attached Volume is mounted. If
the Volume is then subsequently modified by a commit operation in another
running container, that Volume modification won't become available until the
original container does a [`.reload()`](/docs/reference/modal.Volume#reload).

Consider this example which demonstrates the effect of a reload:

```python
import pathlib
import modal

app = modal.App()

volume = modal.Volume.from_name("my-volume")

p = pathlib.Path("/root/foo/bar.txt")


@app.function(volumes={"/root/foo": volume})
def f():
    p.write_text("hello")
    print(f"Created {p=}")
    volume.commit()  # Persist changes
    print(f"Committed {p=}")


@app.function(volumes={"/root/foo": volume})
def g(reload: bool = False):
    if reload:
        volume.reload()  # Fetch latest changes
    if p.exists():
        print(f"{p=} contains '{p.read_text()}'")
    else:
        print(f"{p=} does not exist!")


@app.local_entrypoint()
def main():
    g.remote()  # 1. container for `g` starts
    f.remote()  # 2. container for `f` starts, commits file
    g.remote(reload=False)  # 3. reuses container for `g`, no reload
    g.remote(reload=True)   # 4. reuses container, but reloads to see file.
```

The output for this example is this:

```
p=PosixPath('/root/foo/bar.txt') does not exist!
Created p=PosixPath('/root/foo/bar.txt')
Committed p=PosixPath('/root/foo/bar.txt')
p=PosixPath('/root/foo/bar.txt') does not exist!
p=PosixPath('/root/foo/bar.txt') contains hello
```

This code runs two containers, one for `f` and one for `g`. Only the last
function invocation reads the file created and committed by `f` because it was
configured to reload.

### Background commits

Modal Volumes run background commits:
every few seconds while your Function executes,
the contents of attached Volumes will be committed
without your application code calling `.commit`.
A final snapshot and commit is also automatically performed on container shutdown.

Being able to persist changes to Volumes without changing your application code
is especially useful when [training or fine-tuning models using frameworks](#model-checkpointing).

## Model serving

A single ML model can be served by simply baking it into a `modal.Image` at
build time using [`run_function`](/docs/reference/modal.Image#run_function). But
if you have dozens of models to serve, or otherwise need to decouple image
builds from model storage and serving, use a `modal.Volume`.

Volumes can be used to save a large number of ML models and later serve any one
of them at runtime with great performance. This snippet below shows the
basic structure of the solution.

```python
import modal

app = modal.App()
volume = modal.Volume.from_name("model-store")
model_store_path = "/vol/models"


@app.function(volumes={model_store_path: volume}, gpu="any")
def run_training():
    model = train(...)
    save(model_store_path, model)
    volume.commit()  # Persist changes


@app.function(volumes={model_store_path: volume})
def inference(model_id: str, request):
    try:
        model = load_model(model_store_path, model_id)
    except NotFound:
        volume.reload()  # Fetch latest changes
        model = load_model(model_store_path, model_id)
    return model.run(request)
```

For more details, see our [guide to storing model weights on Modal](/docs/guide/model-weights).

## Model checkpointing

Checkpoints are snapshots of an ML model and can be configured by the callback
functions of ML frameworks. You can use saved checkpoints to restart a training
job from the last saved checkpoint. This is particularly helpful in managing
[preemption](/docs/guide/preemption).

For more, see our [example code for long-running training](/docs/examples/long-training).

### Hugging Face `transformers`

To periodically checkpoint into a `modal.Volume`, just set the `Trainer`'s
[`output_dir`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.output_dir)
to a directory in the Volume.

```python
import pathlib

volume = modal.Volume.from_name("my-volume")
VOL_MOUNT_PATH = pathlib.Path("/vol")

@app.function(
    gpu="A10G",
    timeout=2 * 60 * 60,  # run for at most two hours
    volumes={VOL_MOUNT_PATH: volume},
)
def finetune():
    from transformers import Seq2SeqTrainer
    ...

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(VOL_MOUNT_PATH / "model"),
        # ... more args here
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_xsum_train,
        eval_dataset=tokenized_xsum_test,
    )
```

## Volume performance

Volumes work best when they contain less than 50,000 files and directories. The
latency to attach or modify a Volume scales linearly with the number of files in
the Volume, and past a few tens of thousands of files the linear component
starts to dominate the fixed overhead.

There is currently a hard limit of 500,000 inodes (files, directories and
symbolic links) per Volume. If you reach this limit, any further attempts to
create new files or directories will error with
[`ENOSPC` (No space left on device)](https://pubs.opengroup.org/onlinepubs/9799919799/).

If you need to work with a large number of files, consider using Volumes v2!
It is currently in Beta. See below for more info.

## Filesystem consistency

### Concurrent modification

Concurrent modification from multiple containers is supported, but concurrent
modifications of the same files should be avoided. Last write wins in case of
concurrent modification of the same file — any data the last writer didn't have
when committing changes will be lost!

The number of commits you can run concurrently is limited. If you run too many
concurrent commits each commit will take longer due to contention. If you are
committing small changes, avoid doing more than 5 concurrent commits (the number
of concurrent commits you can make is proportional to the size of the changes
being committed).

As a result, Volumes are typically not a good fit for use cases where you need
to make concurrent modifications to the same file (nor is distributed file
locking supported).

While a reload is in progress the Volume will appear empty to the container that
initiated the reload. That means you cannot read from or write to a Volume in a
container where a reload is ongoing (note that this only applies to the
container where the reload was issued, other containers remain unaffected).

### Busy Volume errors

You can only reload a Volume when there no open files on the Volume. If you have
open files on the Volume the [`.reload()`](/docs/reference/modal.Volume#reload)
operation will fail with "volume busy". The following is a simple example of how
a "volume busy" error can occur:

```python
volume = modal.Volume.from_name("my-volume")


@app.function(volumes={"/vol": volume})
def reload_with_open_files():
    f = open("/vol/data.txt", "r")
    volume.reload()  # Cannot reload when files in the Volume are open.
```

### Can't find file on Volume errors

When accessing files in your Volume, don't forget to pre-pend where your Volume
is mounted in the container.

In the example below, where the Volume has been mounted at `/data`, "hello" is
being written to `/data/xyz.txt`.

```python
import modal

app = modal.App()
vol = modal.Volume.from_name("my-volume")


@app.function(volumes={"/data": vol})
def run():
    with open("/data/xyz.txt", "w") as f:
        f.write("hello")
    vol.commit()
```

If you instead write to `/xyz.txt`, the file will be saved to the local disk of the Modal Function.
When you dump the contents of the Volume, you will not see the `xyz.txt` file.

## Disk usage reporting

Modal Volumes are not block devices and do not have a fixed capacity.
Additionally, used space is not currently reported at the filesystem level.
As a result, tools that query disk usage via the `statfs` syscall
(e.g. `shutil.disk_usage()`, `os.statvfs()`, `df`) will return placeholder
values.

If you need to check the size of a Volume, refer to the size shown in the Modal
dashboard, or use `du` on the mounted Volume within a container.

## Volumes v2 overview

Volumes v2 generally behave just like Volumes v1, and most of the existing APIs
and CLI commands that you are used to will work the same between versions.
Because the file system implementation is completely different, there will be
some significant performance characteristics that can differ from version 1
Volumes. Below is an outline of the key differences you should be aware of.

### Volumes v2 are still in Beta

<Callout variant="beta">

This feature is in beta. We'd love to hear your feedback — please reach out via [Slack](/slack) or email us at [support@modal.com](mailto:support@modal.com). We cannot yet guarantee that no data will be lost, so we don't recommend using Volumes v2 for mission-critical data at this time.

</Callout>

You can still reap the benefits of v2 for
data that isn't precious, or that is easy to rebuild, such as log files,
regularly updated training data and model weights, caches, and more.

### Volumes v2 are HIPAA compliant

If you delete the volume, the data is guaranteed to be lost according to HIPAA requirements.

### Volumes v2 is more scaleable

Volumes v2 support more files, higher throughput, and more irregular access
patterns. Commits and reloads are also faster.

Additionally, Volumes v2 supports hard-linking of files, where multiple paths
can point to the same inode.

### In v2, you can store as many files as you want

There is no limit on the number of files in Volumes v2.

By contrast, in Volumes v1, there is a limit on the number of files of 500,000,
and we recommend keeping the count to 50,000 or less.

### In v2, you can write concurrently from hundreds of containers

The file system should not experience any performance degradation as more
containers write to distinct files simultaneously.

By contrast, in Volumes v1, we recommend no more than five writers access the
Volume at once.

Note, however, that concurrent access to a particular _file_ in a Volume still
has last-write-wins semantics in many circumstances. These semantics are
unacceptable for most applications, so any particular file should only be
written to by a single container at a time.

### In v2, random accesses have improved performance

In v1, writes to locations inside a file would sometimes incur substantial
overhead, like a rewrite of the entire file.

In v2, this overhead is removed, and only changes are written.

### In v2, you can commit using `sync`

For Volumes v2, you can trigger a commit from within a Sandbox or modal shell
by running the `sync` command on the mountpoint:

```bash
sync /path/to/mountpoint
```

This is useful when you don't have access to the Python SDK's
[`.commit()`](/docs/reference/modal.Volume#commit) method, such as when running
shell commands in a Sandbox or during an interactive `modal shell` session.

Running `sync` on the mountpoint will flush any pending writes to the kernel
and then persist all data and metadata changes to the Volume's persistent
storage.

For example, to commit changes in a modal shell session:

```bash
% modal shell --volume my-v2-volume
root / → echo "hello" > /mnt/my-v2-volume/test.txt
root / → sync /mnt/my-v2-volume  # Persist changes before exiting
```

Or to commit from within a Sandbox:

```python notest
sb = modal.Sandbox.create(
    volumes={"/data": modal.Volume.from_name("my-v2-volume")},
    app=my_app,
)
sb.exec("bash", "-c", "echo 'hello' > /data/test.txt").wait()

# Persist changes and check for errors
p = sb.exec("sync", "/data")
p.wait()
if p.returncode != 0:
    raise Exception(f"sync failed with exit code {p.returncode}")
```

> ⚠️ This feature is only available for Volumes v2.

### Volumes v2 has a few limits in place

While we work out performance trade-offs and listen to user feedback, we have
put some artificial limits in place.

- Files must be less than 1 TiB.
- At most 262,144 files can be stored in a single directory.
  Directory depth is unbounded, so the total file count is unbounded.
- Traversing the filesystem can be slower in v2 than in v1, due to demand
  loading of the filesystem tree.

### Upgrading v1 Volumes

Currently, there is no automated tool for upgrading v1 Volumes to v2. We are
planning to implement an automated migration path but for now v1 Volumes need
to be manually migrated by creating a new v2 Volume and either copying files
over from the v1 Volume or writing new files.

To reuse the name of an existing v1 Volume for a new v2 Volume, first stop all
apps that are utilizing the v1 Volume before deleting it. If this is not
feasible, e.g. due to wanting to avoid downtime, use a new name for the v2
Volume.

**Warning:** When deleting an existing Volume, any deployed apps or running
functions utilizing that Volume will cease to function, even if a new Volume is
created with the same name. This is because Volumes are identified with opaque
unique IDs that are resolved at application deployment or start time. A newly
created Volume with the same name as a deleted Volume will have a new Volume ID
and any deployed or running apps will still be referring to the old ID until
these apps are re-deployed or restarted.

In order to create a new volume and copy data over from the old volume, you can
use a tool like `cp` if you intend to copy all the data in one go, or `rsync`
if you want to incrementally copy the data across a longer time span:

```shell
$ modal volume create --version=2 2files2furious
$ modal shell --volume files-and-furious --volume 2files2furious
Welcome to Modal's debug shell!
We've provided a number of utilities for you, like `curl` and `ps`.
# Option 1: use `cp`
root / → cp -rp /mnt/files-and-furious/. /mnt/2files2furious/.
root / → sync /mnt/2files2furious # Ensure changes are persisted before exiting

# Option 2: use `rsync`
root / → apt install -y rsync
root / → rsync -a /mnt/files-and-furious/. /mnt/2files2furious/.
root / → sync /mnt/2files2furious # Ensure changes are persisted before exiting
```

## Further examples

- [Character LoRA fine-tuning](/docs/examples/diffusers_lora_finetune) with model storage on a Volume
- [Protein folding](/docs/examples/chai1) with model weights and output files stored on Volumes
- [Dataset visualization with Datasette](/docs/examples/cron_datasette) using a SQLite database on a Volume

---

# Storing model weights on Modal

Efficiently managing the weights of large models is crucial for optimizing the
build times and startup latency of many ML and AI applications.

Our recommended method for working with model weights is to store them in a Modal [Volume](/docs/guide/volumes),
which acts as a distributed file system, a "shared disk" all of your Modal Functions can access.

## Storing weights in a Modal Volume

To store your model weights in a Volume, you need to either
make the Volume available to a Modal Function that saves the model weights
or upload the model weights into the Volume from a client.

### Saving model weights into a Modal Volume from a Modal Function

If you're already generating the weights on Modal, you just need to
attach the Volume to your Modal Function, making it available for reading and writing:

```python
from pathlib import Path

volume = modal.Volume.from_name("model-weights-vol", create_if_missing=True)
MODEL_DIR = Path("/models")

@app.function(gpu="any", volumes={MODEL_DIR: volume})  # attach the Volume
def train_model(data, config):
    import run_training

    model = run_training(config, data)
    model.save(config, MODEL_DIR)
```

Volumes are attached by including them in a dictionary that maps
a path on the remote machine to a `modal.Volume` object.
They look just like a normal file system, so model weights can be saved to them
without adding any special code.

If the model weights are generated outside of Modal and made available
over the Internet, for example by an open-weights model provider
or your own training job on a dedicated cluster,
you can also download them into a Volume from a Modal Function:

```python continuation
@app.function(volumes={MODEL_DIR: volume})
def download_model(model_id):
    import model_hub

    model_hub.download(model_id, local_dir=MODEL_DIR / model_id)
```

Add [Modal Secrets](/docs/guide/secrets) to access weights that require authentication.

See [below](#storing-weights-from-the-hugging-face-hub-on-modal) for
more on downloading from the popular Hugging Face Hub.

### Uploading model weights into a Modal Volume

Instead of pulling weights into a Modal Volume from inside a Modal Function,
you might wish to push weights into Modal from a client,
like your laptop or a dedicated training cluster.

For that, you can use the `batch_upload` method of
[`modal.Volume`](/docs/reference/modal.Volume)s
via the Modal Python client library:

```python continuation
volume = modal.Volume.from_name("model-weights-vol", create_if_missing=True)

@app.local_entrypoint()
def main(local_path: str, remote_path: str):
    with volume.batch_upload() as upload:
        upload.put_directory(local_path, remote_path)
```

Alternatively, you can upload model weights using the
[`modal volume`](/docs/reference/cli/volume) CLI command:

```bash
modal volume put model-weights-vol path/to/model path/on/volume
```

### Mounting cloud buckets as Modal Volumes

If your model weights are already in cloud storage,
for example in an S3 bucket, you can connect them
to Modal Functions with a `CloudBucketMount`.

See [the guide](/docs/guide/cloud-bucket-mounts) for details.

## Reading model weights from a Modal Volume

You can read weights from a Volume as you would normally read them
from disk, so long as you attach the Volume to your Function.

```python continuation
@app.function(gpu="any", volumes={MODEL_DIR: volume})
def inference(prompt, model_id):
    import load_model

    model = load_model(MODEL_DIR / model_id)
    model.run(prompt)
```

## Storing weights in the Modal Image

It is also possible to store weights in your Function's Modal [Image](/docs/guide/images),
the private file system state that a Function sees when it starts up.
The weights might be downloaded via shell commands with [`Image.run_commands`](/docs/guide/images)
or downloaded using a Python function with [`Image.run_function`](/docs/guide/images).

We recommend storing model weights in a Modal [Volume](/docs/guide/volumes),
as described [above](#storing-weights-in-a-modal-volume). Performance is similar
for the two methods. Volumes are more flexible.
Images are rebuilt when their definition changes, starting from the changed layer,
which increases reproducibility for some builds but leads to unnecessary extra downloads
in most cases.

## Optimizing model weight reads with `@modal.enter`

In the above code samples, weights are loaded from disk into memory each time
the `inference` function is run. This isn't so bad if inference is much
slower than model loading (e.g. it is run on very large datasets)
or if the model loading logic is smart enough to skip reloading.

To guarantee a particular model's weights are only loaded once, you can use the `@modal.enter`
[container lifecycle hook](/docs/guide/lifecycle-functions)
to load the weights only when a new container starts.

```python continuation
MODEL_ID = "some-model-id"

@app.cls(gpu="any", volumes={MODEL_DIR: volume})
class Model:
    @modal.enter()
    def setup(self, model_id=MODEL_ID):
        import load_model

        self.model = load_model(MODEL_DIR, model_id)

    @modal.method()
    def inference(self, prompt):
        return self.model.run(prompt)
```

Note that methods decorated with `@modal.enter` can't be passed dynamic arguments.

If you need to load a single but possibly different model on each container start, you can
[parametrize](/docs/guide/parametrized-functions) your Modal Cls.
Below, we use the `modal.parameter` syntax.

```python continuation
@app.cls(gpu="any", volumes={MODEL_DIR: volume})
class ParametrizedModel:
    model_id: str = modal.parameter()

    @modal.enter()
    def setup(self):
        import load_model

        self.model = load_model(MODEL_DIR, self.model_id)

    @modal.method()
    def inference(self, prompt):
        return self.model.run(prompt)
```

## Storing weights from the Hugging Face Hub on Modal

The [Hugging Face Hub](https://huggingface.co/models) has over 1,000,000 models
with weights available for download.

The snippet below shows some additional tricks for downloading models
from the Hugging Face Hub on Modal.

```python
from typing import Optional
from pathlib import Path

import modal

# create a Volume, or retrieve it if it exists
volume = modal.Volume.from_name("model-weights-vol", create_if_missing=True)
MODEL_DIR = Path("/models")

# define dependencies for downloading model
download_image = (
    modal.Image.debian_slim()
    .pip_install("huggingface_hub")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"}) # enable fast data transfer
)
app = modal.App()

@app.function(
    volumes={MODEL_DIR.as_posix(): volume},  # "mount" the Volume, sharing it with your function
    image=download_image,  # only download dependencies needed here
)
def download_model(
    repo_id: str = "hf-internal-testing/tiny-random-GPTNeoXForCausalLM",
    revision: Optional[str] = None,  # include a revision to prevent surprises!
):
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id, local_dir=MODEL_DIR / repo_id, revision=revision)
    print(f"Model downloaded to {MODEL_DIR / repo_id}")
```

---

# Cloud bucket mounts

The [`modal.CloudBucketMount`](/docs/reference/modal.CloudBucketMount) is a
mutable volume that allows for both reading and writing files from a cloud
bucket. It supports AWS S3, Cloudflare R2, and Google Cloud Storage buckets.

Cloud bucket mounts are built on top of AWS'
[`mountpoint`](https://github.com/awslabs/mountpoint-s3) technology and inherits
its limitations. See the [Limitations and troubleshooting](#limitations-and-troubleshooting) section for more details.

## Mounting Cloudflare R2 buckets

`CloudBucketMount` enables Cloudflare R2 buckets to be mounted as file system
volumes. Because Cloudflare R2 is
[S3-Compatible](https://developers.cloudflare.com/r2/api/s3/api/) the setup is
very similar between R2 and S3. See
[modal.CloudBucketMount](/docs/reference/modal.CloudBucketMount#modalcloudbucketmount)
for usage instructions.

When creating the R2 API token for use with the mount, you need to have the
ability to read, write, and list objects in the specific buckets you will mount.
You do _not_ need admin permissions, and you should _not_ use "Client IP Address
Filtering".

## Mounting Google Cloud Storage buckets

`CloudBucketMount` enables Google Cloud Storage (GCS) buckets to be mounted as file system
volumes. See [modal.CloudBucketMount](/docs/reference/modal.CloudBucketMount#modalcloudbucketmount)
for GCS setup instructions.

## Mounting S3 buckets

`CloudBucketMount` enables S3 buckets to be mounted as file system volumes. To
interact with a bucket, you must have the appropriate IAM permissions configured
(refer to the section on [IAM Permissions](#iam-permissions)).

```python
import modal
import subprocess

app = modal.App()

s3_bucket_name = "s3-bucket-name"  # Bucket name not ARN.
s3_access_credentials = modal.Secret.from_dict({
    "AWS_ACCESS_KEY_ID": "...",
    "AWS_SECRET_ACCESS_KEY": "...",
    "AWS_REGION": "..."
})

@app.function(
    volumes={
        "/my-mount": modal.CloudBucketMount(s3_bucket_name, secret=s3_access_credentials)
    }
)
def f():
    subprocess.run(["ls", "/my-mount"])
```

### Specifying S3 bucket region

Amazon S3 buckets are associated with a single AWS Region. [`Mountpoint`](https://github.com/awslabs/mountpoint-s3) attempts to automatically detect the region for your S3 bucket at startup time and directs all S3 requests to that region. However, in certain scenarios, like if your container is running on an AWS worker in a certain region, while your bucket is in a different region, this automatic detection may fail.

To avoid this issue, you can specify the region of your S3 bucket by adding an `AWS_REGION` key to your Modal secrets, as in the code example above.

### Using AWS temporary security credentials

`CloudBucketMount`s also support AWS temporary security credentials by passing
the additional environment variable `AWS_SESSION_TOKEN`. Temporary credentials
will expire and will not get renewed automatically. You will need to update
the corresponding Modal Secret in order to prevent failures.

You can get temporary credentials with the [AWS CLI](https://aws.amazon.com/cli/) with:

```shell
$ aws configure export-credentials --format env
export AWS_ACCESS_KEY_ID=XXX
export AWS_SECRET_ACCESS_KEY=XXX
export AWS_SESSION_TOKEN=XXX...
```

All these values are required.

### Using OIDC identity tokens

Modal provides [OIDC integration](/docs/guide/oidc-integration) and will automatically generate identity tokens to authenticate to AWS.
OIDC eliminates the need for manual token passing through Modal secrets and is based on short-lived tokens, which limits the window of exposure if a token is compromised.
To use this feature, you must [configure AWS to trust Modal's OIDC provider](/docs/guide/oidc-integration#step-1-configure-aws-to-trust-modals-oidc-provider)
and [create an IAM role that can be assumed by Modal Functions](/docs/guide/oidc-integration#step-2-create-an-iam-role-that-can-be-assumed-by-modal-functions).

Then, you specify the IAM role that your Modal Function should assume to access the S3 bucket.

```python
import modal

app = modal.App()

s3_bucket_name = "s3-bucket-name"
role_arn = "arn:aws:iam::123456789abcd:role/s3mount-role"

@app.function(
    volumes={
        "/my-mount": modal.CloudBucketMount(
            bucket_name=s3_bucket_name,
            oidc_auth_role_arn=role_arn
        )
    }
)
def f():
    subprocess.run(["ls", "/my-mount"])
```

### Mounting a path within a bucket

To mount only the files under a specific subdirectory, you can specify a path prefix using `key_prefix`.
Since this prefix specifies a directory, it must end in a `/`.
The entire bucket is mounted when no prefix is supplied.

```python
import modal
import subprocess

app = modal.App()

s3_bucket_name = "s3-bucket-name"
prefix = 'path/to/dir/'

s3_access_credentials = modal.Secret.from_dict({
    "AWS_ACCESS_KEY_ID": "...",
    "AWS_SECRET_ACCESS_KEY": "...",
})

@app.function(
    volumes={
        "/my-mount": modal.CloudBucketMount(
            bucket_name=s3_bucket_name,
            key_prefix=prefix,
            secret=s3_access_credentials
        )
    }
)
def f():
    subprocess.run(["ls", "/my-mount"])
```

This will only mount the files in the bucket `s3-bucket-name` that are prefixed by `path/to/dir/`.

### Read-only mode

To mount a bucket in read-only mode, set `read_only=True` as an argument.

```python
import modal
import subprocess

app = modal.App()

s3_bucket_name = "s3-bucket-name"  # Bucket name not ARN.
s3_access_credentials = modal.Secret.from_dict({
    "AWS_ACCESS_KEY_ID": "...",
    "AWS_SECRET_ACCESS_KEY": "...",
})

@app.function(
    volumes={
        "/my-mount": modal.CloudBucketMount(s3_bucket_name, secret=s3_access_credentials, read_only=True)
    }
)
def f():
    subprocess.run(["ls", "/my-mount"])
```

While S3 mounts support both write and read operations, they are optimized for
reading large files sequentially. Certain file operations, such as renaming
files, are not supported. For a comprehensive list of supported operations,
consult the
[Mountpoint documentation](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md).

### IAM permissions

To utilize `CloudBucketMount` for reading and writing files from S3 buckets,
your IAM policy must include permissions for `s3:PutObject`,
`s3:AbortMultipartUpload`, and `s3:DeleteObject`. These permissions are not
required for mounts configured with `read_only=True`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ModalListBucketAccess",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::<MY-S3-BUCKET>"]
    },
    {
      "Sid": "ModalBucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject"
      ],
      "Resource": ["arn:aws:s3:::<MY-S3-BUCKET>/*"]
    }
  ]
}
```

## Limitations and troubleshooting

Cloud Bucket Mounts have certain limitations that do not apply to [Volumes](/docs/guide/volumes).
These limitations are primarily around the way that files can be opened and edited in Cloud Bucket Mounts. For
a comprehensive list of limitations, see the [Mountpoint troubleshooting documentation](https://github.com/awslabs/mountpoint-s3/blob/a6179c72bfc237a1fdd06eb4a0863ca537f8d8a7/doc/TROUBLESHOOTING.md)
and the [Mountpoint semantics documentation](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md).

The most common issues that users encounter are:

- Files cannot be opened in append mode.
- Files cannot be written to at arbitrary offsets i.e. `seek` and write are not supported together.
- To write to a file, you must open it in `truncate` mode.

These operations typically result in a `PermissionError: [Errno 1] Operation not permitted` error.

If you need these features, give [Volumes](/docs/guide/volumes) a try! If you need these features in S3
and are willing to pay extra for your bucket, you may be able to use [S3 Express](https://aws.amazon.com/s3/storage-classes/express-one-zone/).
Contact us [in our Slack](https://modal.com/slack) if you're interested in using S3 Express.

### Writing files in append mode

If you're using a library which must open a file in append mode, it's best to write to a temporary file
and then move it to your bucket's mount path. A similar approach can be used to write to a file at an arbitrary offset.

```python notest
import tempfile
import shutil

@app.function(
    volumes={"/bucket": modal.CloudBucketMount("my-bucket", secret=s3_credentials)}
)
def append_to_log():
    # Write to a temporary file that supports append mode
    with tempfile.NamedTemporaryFile(mode='a', delete=False) as temp_file:
        temp_file.write("Log entry 1\n")
        temp_file.write("Log entry 2\n")
        temp_path = temp_file.name

    # Move the completed file to the bucket mount
    shutil.move(temp_path, "/bucket/logfile.txt")
```

### Creating a file without a parent directory

If you try to create a file in a directory that doesn't exist, you'll get a `Operation not permitted` error.
To fix this, create the parent directory first with `Path(dst).parent.mkdir(exist_ok=True, parents=True)`.

### Using `np.savez`

`np.savez` seeks to random offsets in a file, making it unsafe for Cloud Bucket Mounts. If your file is large,
you can write it to a temporary file and then move it to your bucket's mount path. If it's small, however,
you can solve this with an in-memory buffer:

```python notest
import io
import numpy as np
import shutil

data = np.random.rand(1000, 512)

# 1. Build the archive entirely in memory
tmp = io.BytesIO()
np.savez_compressed(tmp, array=data)

# 2. Copy it once, sequentially, to the mount point
dest = "/bucket/data.npz"
with open(dest, "wb") as f:
    shutil.copyfileobj(tmp, f)
```

### Torchtune writing checkpoint files

Old versions of [Torchtune](https://github.com/pytorch/torchtune) are incompatible with Cloud Bucket Mounts.
Upgrade to a version greater than or equal to `0.6.1` to ensure checkpoints can be written to the bucket.

### Using the TensorBoard `SummaryWriter`

The TensorBoard `SummaryWriter` opens log files in append mode. These files are quite small, though,
so we recommend writing to a temporary directory and using the [Watchdog](https://github.com/gorakhargosh/watchdog)
Python library to copy the files to the bucket mount path as they come in.

This is a case where it may be worth it to use [Volumes](/docs/guide/volumes) instead - in particular,
training logs are sometimes not subject to the same compliance requirements that force something like checkpoints
or model weights to be stored in a secure location. We even have an example of
[how to use TensorBoard on Volumes](/docs/examples/torch_profiling#serving-tensorboard-on-modal-to-view-pytorch-profiles-and-traces).

---

# Large dataset ingestion

This guide provides best practices for downloading, transforming, and storing large datasets within
Modal. A dataset is considered large if it contains hundreds of thousands of files and/or is over
100 GiB in size.

These guidelines ensure that large datasets can be ingested fully and reliably.

## Configure your Function for heavy disk usage

Large datasets should be downloaded and transformed using a `modal.Function` and stored
into a [Volume](/docs/guide/volumes).

This `modal.Function` should specify a large `timeout` because large dataset processing can take hours,
and it should request a larger ephemeral disk in cases where the dataset being downloaded and processed
is hundreds of GiBs.

```python
volume = modal.Volume.from_name("datasets", create_if_missing=True)


@app.function(
    volumes={"/mnt/datasets": volume},
    ephemeral_disk=1000 * 1000,  # 1 TiB
    timeout=60 * 60 * 12,  # 12 hours

)
def download_and_transform() -> None:
    ...
    volume.commit()
```

### Prefer sharded or archived outputs for tiny-file datasets

Volumes can store large datasets, but datasets made up of millions of tiny files are
still usually easier to ingest and consume when they are first grouped into larger artifacts such as
tar shards, WebDataset archives, Parquet files, or other batched formats.

See the [transforming](#transforming) section below for more details.

## Experimentation

Downloading and transforming large datasets can be fiddly. While iterating on a reliable ingestion program
you may want an interactive environment so you can inspect downloaded files, validate credentials,
and benchmark transforms before automating the full ingestion job. [Modal Notebooks](/docs/guide/notebooks)
work well for this. Attach the same Volume that your ingestion Functions use, keep transient scratch
data in `/tmp`, and persist intermediate artifacts under `/mnt/...`.

## Downloading

The raw dataset data should be first downloaded into the container at `/tmp/` and not placed
directly into the mounted volume. This serves a couple purposes.

1. Download tools often create temporary files, partial files, or rename targets while writing, and local SSD handles that more efficiently.
2. The raw dataset data may need to be transformed before use, in which case it is wasteful to store it permanently.

This snippet shows the basic download-and-copy procedure:

```python notest
import pathlib
import shutil
import subprocess

tmp_path = pathlib.Path("/tmp/imagenet/")
vol_path = pathlib.Path("/mnt/datasets/imagenet/")
filename = "imagenet-object-localization-challenge.zip"
# 1. Download into /tmp/
subprocess.run(
    f"kaggle competitions download -c imagenet-object-localization-challenge --path {tmp_path}",
    shell=True,
    check=True
)
vol_path.mkdir(parents=True, exist_ok=True)
# 2. Copy (without transform) into mounted volume.
shutil.copy2(tmp_path / filename, vol_path / filename)
volume.commit()
```

## Transforming

When ingesting a large dataset it is sometimes necessary to transform it before storage, so that it is in
an optimal format for loading at runtime. A common kind of necessary transform is gzip decompression. Very large
datasets are often gzipped for storage and network transmission efficiency, but gzip decompression (80 MiB/s)
is hundreds of times slower than reading from a solid state drive (SSD)
and should be done once before storage to avoid decompressing on every read against the dataset.

Transformations should be performed after storing the raw dataset in `/tmp/`. Performing transformations almost always increases container disk usage and this is where the [`ephemeral_disk` parameter](/docs/reference/modal.App#function) parameter becomes important. For example, a
100 GiB raw, compressed dataset may decompress to into 500 GiB, occupying 600 GiB of container disk space.

Transformations should also typically be performed against `/tmp/`. This is because

1. transforms can be IO intensive and IO latency is lower against local SSD.
2. transforms can create temporary data which is wasteful to store permanently.

Once the transform is complete, write the final dataset layout to the attached Volume and commit it so
subsequent Functions and Notebooks can reload and use the same data.

## Examples

The best practices offered in this guide are demonstrated in the [`modal-examples` repository](https://github.com/modal-labs/modal-examples/tree/main/12_datasets).

The examples include these popular large datasets:

- [ImageNet](https://www.image-net.org/), the image labeling dataset that kicked off the deep learning revolution
- [COCO](https://cocodataset.org/#download), the Common Objects in COntext dataset of densely-labeled images
- [LAION-400M](https://laion.ai/blog/laion-400-open-dataset/), the Stable Diffusion training dataset
- Data derived from the [Big "Fantastic" Database](https://bfd.mmseqs.com/),
  [Protein Data Bank](https://www.wwpdb.org/), and [UniProt Database](https://www.uniprot.org/)
  used in training the [RoseTTAFold](https://github.com/RosettaCommons/RoseTTAFold) protein structure model

---

# Workspaces

This page is a high-level guide to Modal Workspaces,
the primary unit of organization for Modal resources
and authentication.

A **Workspace** is an area where a user can deploy Modal apps and other
resources. There are two types of Workspaces: personal and shared. After a new
user has signed up to Modal, a personal Workspace is automatically created for
them. The name of the personal Workspace is based on your GitHub username, but
it might be randomly generated if already taken or invalid.

To collaborate with others, a new shared Workspace needs to be created.

## Create a Workspace

All additional Workspaces are shared Workspaces, meaning you can invite others
by email to collaborate with you. There are two ways to create a Modal Workspace
on the [settings](/settings/workspaces) page.

<Callout variant="info">

If your Modal account was provisioned through Okta, you will not have the option to create a new Workspace. Your Workspace is managed by your organization's Okta configuration. If you need a new Workspace, contact your organization's Okta administrator.

</Callout>

![view of workspaces creation interface](https://modal-cdn.com/cdnbot/create-new-workspace-viewk0ka46_7_800f2053.webp)

1. Create from [GitHub organization](https://docs.github.com/en/organizations). Allows members in GitHub organization to auto-join the Workspace.

2. Create from scratch. You can invite anyone to your Workspace.

If you're interested in having a Workspace associated with your Okta
organization, then check out our [Okta SSO docs](/docs/guide/okta-sso).

If you're interested in using SSO through Google or other providers, then please reach out to us at [support@modal.com](mailto:support@modal.com).

## Auto-joining a Workspace associated with a GitHub organization

Note: This is only relevant for Workspaces created from a GitHub organization.

Users can automatically join a Workspace on their [Workspace settings page](/settings/workspaces) if they are a member of the GitHub organization associated with the Workspace.

To turn off this functionality a Workspace Manager can disable it on the **Workspace Management** tab of their Workspace's settings page.

## Inviting new Workspace members

To invite a new Workspace member, you can visit the [settings](/settings) page
and navigate to the members tab for the appropriate Workspace.

You can either send an email invite or share an invite link. Both existing Modal
users and non-existing users can use the links to join your Workspace. If they
are a new user a Modal account will be created for them.

![invite member section](../../assets/screenshots/invite-member.png)

## Create a token for a Workspace

To interact with a Workspace's resources programmatically, you need to add an
API token for that Workspace. Your existing API tokens are displayed on
[the settings page](/settings/tokens) and new API tokens can be added for a
particular Workspace.

After adding a token for a Workspace to your Modal config file you can activate
that Workspace's profile using the CLI (see below).

As an manager or Workspace owner you can manage active tokens for a Workspace on
[the member tokens page](/settings/tokens/member-tokens). For more information on API
token management see the
[documentation about configuration](/docs/reference/modal.config).

## Switching active Workspace

When on the dashboard or using the CLI, the active profile determines which
personal or organizational Workspace is associated with your actions.

### Dashboard

You can switch between organization Workspaces and your Personal Workspace by
using the workspace selector at the top of [the dashboard](/home).

### CLI

To switch the Workspace associated with CLI commands, use
`modal profile activate`.

## Administering Workspace membership

Workspaces have three different levels of access privileges:

- Owner
- Manager
- Member

The user that creates a Workspace is automatically set as the **Owner** for that
workspace. The owner can assign any other roles within the workspace, as well as
remove other members of the workspace.

A **Manager** within a workspace can assign all roles except **Owner** and can
also remove other members of the workspace.

A **Member** of a workspace can not assign any access privileges within the
workspace but can otherwise perform any action like running and deploying apps
and modify Secrets.

As an Owner or Manager you can administrate the access privileges of other
members on the `Workspace Management` tab in [settings](/settings/workspace-management).

<Callout variant="info">

Modal supports [Role-Based Access Control (RBAC)](/docs/guide/rbac) for more granular control over permissions at both the Workspace and Environment level.

</Callout>

## Leaving a Workspace

To leave a workspace, navigate to [the settings page](/settings/workspaces) and
click "Leave" on a listed Workspace. There must be at least one owner assigned
to a Workspace.

---

# Environments

Modal Environments isolate Modal applications and resources from one another.

Environments are sub-divisions of [Workspaces](/docs/guide/workspaces),
allowing you to deploy the same App (or set of Apps)
in multiple instances for different purposes without changing code.

Typical use cases for Environments include having one `dev`
Environment and one `prod` Environment. Production Apps are protected from overwriting
when developing new features, but you can still deploy and test changes with a
"live" and potentially complex structure of Apps.

Each Environment has its own set of [Secrets](/docs/guide/secrets) and any
object lookups, say for [Dicts](/docs/guide/dicts) or [Volumes](/docs/guide/volumes),
performed from an App in an Environment will by default look for objects in the same Environment.

By default, every Workspace has a single Environment called "main". New
Environments can be created on the CLI:

```sh
modal environment create dev
```

Run `modal environment --help` for more info.

Workspaces can have up to 1500 Environments.

Once created, Environments show up as a dropdown menu in the navbar of the
[Modal dashboard](/apps), letting you set browse all Modal Apps, Secrets, and Storage
filtered by which Environment they were deployed to.

Most CLI commands also support an `--env` flag letting you specify which
Environment you intend to interact with, e.g.:

```sh
modal run --env=dev app.py
modal volume create --env=dev storage
```

To set a default Environment for your current CLI profile you can use
`modal config set-environment`, e.g.:

```sh
modal config set-environment dev
```

Alternatively, you can set the `MODAL_ENVIRONMENT` environment variable.

## Environment web suffixes

Environments have a 'web suffix' which is used to make
[web endpoint URLs](/docs/guide/webhook-urls) unique across your workspace. One
Environment is allowed to have no suffix (`""`).

## Cross environment lookups

It's possible to explicitly look up objects in Environments other than the Environment
your App runs within:

```python
production_secret = modal.Secret.from_name(
    "my-secret",
    environment_name="main",
)
```

```python notest
modal.Function.from_name(
    "my_app",
    "some_function",
    environment_name="dev"
)
```

However, the `environment_name` argument is optional and omitting it will use
the Environment from the object's associated App or calling context.

---

# Developing Modal code with LLMs and agents

Modal is designed for fast iteration on infrastructure by both humans and machines.

Modal was [built to provide human backend engineers the rapid feedback loops frontend engineers take for granted](https://erikbern.com/2022/12/07/what-ive-been-working-on-modal.html).
This [also means](/blog/agents-devex) that Modal works well with code generation agents, especially those that can run CLI commands like `modal run` in an implement, test and debug loop, like OpenCode, Amp, Claude Code, Cursor's agent mode, Gemini CLI, etc.

There are of course also many concepts and design patterns that are unique to Modal, so below we gather rules and guidelines that we have found useful when developing Modal code with LLMs. You can paste/import this into your `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/modal.mdc`, etc. or use it as a starting point for your own rules or prompts.
We also provide an [`llms.txt`](/llms.txt).

If you're instead looking for information about how to run code generation agents _on Modal_,
see [the guide page for Modal Sandboxes](/docs/guide/sandboxes)
or [this example code](https://modal.com/docs/examples/sandbox_agent).

````markdown
# Modal Rules and Guidelines for LLMs

This file provides rules and guidelines for LLMs when implementing Modal code.

## General

- Modal is a serverless cloud platform for running Python code with minimal configuration
- Designed for AI/ML workloads but supports general-purpose cloud compute
- Serverless billing model - you only pay for resources used

## Modal documentation

- Extensive documentation is available at: modal.com/docs (and in markdown format at modal.com/llms-full.txt)
- A large collection of examples is available at: modal.com/docs/examples (and github.com/modal-labs/modal-examples)
- Reference documentation is available at: modal.com/docs/reference

Always refer to documentation and examples for up-to-date functionality and exact syntax.

## Core Modal concepts

### App

- A group of functions, classes and sandboxes that are deployed together.

### Function

- The basic unit of serverless execution on Modal.
- Each Function executes in its own container, and you can configure different Images for different Functions within the same App:

  ```python
  image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch", "numpy", "transformers")
    .apt_install("ffmpeg")
    .run_commands("mkdir -p /models")
  )

  @app.function(image=image)
  def square(x: int) -> int:
    return x * x
  ```

- You can configure individual hardware requirements (CPU, memory, GPUs, etc.) for each Function.

  ```python
  @app.function(
    gpu="H100",
    memory=4096,
    cpu=2,
  )
  def inference():
    ...
  ```

  Some examples specificly for GPUs:

  ```python
  @app.function(gpu="A10G")  # Single GPU, e.g. T4, A10G, A100, H100, or "any"
  @app.function(gpu="A100:2")  # Multiple GPUs, e.g. 2x A100 GPUs
  @app.function(gpu=["H100", "A100", "any"]) # GPU with fallbacks
  ```

- Functions can be invoked in a number of ways. Some of the most common are:
  - `foo.remote()` - Run the Function in a separate container in the cloud. This is by far the most common.
  - `foo.local()` - Run the Function in the same context as the caller. Note: This does not necessarily mean locally on your machine.
  - `foo.map()` - Parallel map over a set of inputs.
  - `foo.spawn()` - Calls the function with the given arguments, without waiting for the results. Terminating the App will also terminate spawned functions.
- Web endpoint: You can turn any Function into an HTTP web endpoint served by adding a decorator:

  ```python
  @app.function()
  @modal.fastapi_endpoint()
  def fastapi_endpoint():
    return {"status": "ok"}

  @app.function()
  @modal.asgi_app()
  def asgi_app():
    app = FastAPI()
    ...
    return app
  ```

- You can run Functions on a schedule using e.g. `@app.function(schedule=modal.Period(minutes=5))` or `@app.function(schedule=modal.Cron("0 9 * * *"))`.

### Classes (a.k.a. `Cls`)

- For stateful operations with startup/shutdown lifecycle hooks. Example:

  ```python
  @app.cls(gpu="A100")
  class ModelServer:
      @modal.enter()
      def load_model(self):
          # Runs once when container starts
          self.model = load_model()

      @modal.method()
      def predict(self, text: str) -> str:
          return self.model.generate(text)

      @modal.exit()
      def cleanup(self):
          # Runs when container stops
          cleanup()
  ```

### Other important concepts

- Image: Represents a container image that Functions can run in.
- Sandbox: Allows defining containers at runtime and securely running arbitrary code inside them.
- Volume: Provide a high-performance distributed file system for your Modal applications.
- Secret: Enables securely providing credentials and other sensitive information to your Modal Functions.
- Dict: Distributed key/value store, managed by Modal.
- Queue: Distributed, FIFO queue, managed by Modal.

## Differences from standard Python development

- Modal always executes code in the cloud, even while you are developing. You can use Environments for separating development and production deployments.
- Dependencies: It's common and encouraged to have different dependency requirements for different Functions within the same App. Consider defining dependencies in Image definitions (see Image docs) that are attached to Functions, rather than in global `requirements.txt`/`pyproject.toml` files, and putting `import` statements inside the Function `def`. Any code in the global scope needs to be executable in all environments where that App source will be used (locally, and any of the Images the App uses).

## Modal coding style

- Modal Apps, Volumes, and Secrets should be named using kebab-case.
- Always use `import modal`, and qualified names like `modal.App()`, `modal.Image.debian_slim()`.
- Modal evolves quickly, and prints helpful deprecation warnings when you `modal run` an App that uses deprecated features. When writing new code, never use deprecated features.

## Common commands

Running `modal --help` gives you a list of all available commands. All commands also support `--help` for more details.

### Running your Modal app during development

- `modal run path/to/your/app.py` - Run your app on Modal.
- `modal run -m module.path.to.app` - Run your app on Modal, using the Python module path.
- `modal serve modal_server.py` - Run web endpoint(s) associated with a Modal app, and hot-reload code on changes. Will print a URL to the web endpoint(s). Note: you need to use `Ctrl+C` to interrupt `modal serve`.

### Deploying your Modal app

- `modal deploy path/to/your/app.py` - Deploy your app (Functions, web endpoints, etc.) to Modal.
- `modal deploy -m module.path.to.app` - Deploy your app to Modal, using the Python module path.

Logs:

- `modal app logs <app_name>` - Stream logs for a deployed app. Note: you need to use `Ctrl+C` to interrupt the stream.

### Resource management

- There are CLI commands for interacting with resources like `modal app list`, `modal volume list`, and similarly for `secret`, `dict`, `queue`, etc.
- These also support other command than `list` - use e.g. `modal app --help` for more.

## Testing and debugging

- When using `app.deploy()`, you can wrap it in a `with modal.enable_output():` block to get more output.
````

---

# API Reference

This is the API reference for the [`modal`](https://pypi.org/project/modal/)
Python package, which allows you to run distributed applications on Modal.

The reference is intended to be limited to low-level descriptions of various
programmatic functionality. If you're just getting started with Modal, we would
instead recommend looking at the [guide](/docs/guide) first
or to get started quickly with an [example](/docs/examples).

## Application construction

|                                                      |                                                  |
| ---------------------------------------------------- | ------------------------------------------------ |
| [`App`](/docs/reference/modal.App)                   | The main unit of deployment for code on Modal    |
| [`App.function`](/docs/reference/modal.App#function) | Decorator for registering a function with an App |
| [`App.cls`](/docs/reference/modal.App#cls)           | Decorator for registering a class with an App    |

## Serverless execution

|                                              |                                                                   |
| -------------------------------------------- | ----------------------------------------------------------------- |
| [`Function`](/docs/reference/modal.Function) | A serverless function backed by an autoscaling container pool     |
| [`Cls`](/docs/reference/modal.Cls)           | A serverless class supporting parametrization and lifecycle hooks |

## Extended Function configuration

### Class parametrization

|                                                |                                                            |
| ---------------------------------------------- | ---------------------------------------------------------- |
| [`parameter`](/docs/reference/modal.parameter) | Used to define class parameters, akin to a Dataclass field |

### Lifecycle hooks

|                                          |                                                                        |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| [`enter`](/docs/reference/modal.enter)   | Decorator for a method that will be executed during container startup  |
| [`exit`](/docs/reference/modal.exit)     | Decorator for a method that will be executed during container shutdown |
| [`method`](/docs/reference/modal.method) | Decorator for exposing a method as an invokable function               |

### Web integrations

|                                                              |                                                                |
| ------------------------------------------------------------ | -------------------------------------------------------------- |
| [`fastapi_endpoint`](/docs/reference/modal.fastapi_endpoint) | Decorator for exposing a simple FastAPI-based endpoint         |
| [`asgi_app`](/docs/reference/modal.asgi_app)                 | Decorator for functions that construct an ASGI web application |
| [`wsgi_app`](/docs/reference/modal.wsgi_app)                 | Decorator for functions that construct a WSGI web application  |
| [`web_server`](/docs/reference/modal.web_server)             | Decorator for functions that construct an HTTP web server      |

### Function semantics

|                                                  |                                                                               |
| ------------------------------------------------ | ----------------------------------------------------------------------------- |
| [`batched`](/docs/reference/modal.batched)       | Decorator that enables [dynamic input batching](/docs/guide/dynamic-batching) |
| [`concurrent`](/docs/reference/modal.concurrent) | Decorator that enables [input concurrency](/docs/guide/concurrent-inputs)     |

### Scheduling

|                                          |                                           |
| ---------------------------------------- | ----------------------------------------- |
| [`Cron`](/docs/reference/modal.Cron)     | A schedule that runs based on cron syntax |
| [`Period`](/docs/reference/modal.Period) | A schedule that runs at a fixed interval  |

### Exception handling

|                                            |                                          |
| ------------------------------------------ | ---------------------------------------- |
| [`Retries`](/docs/reference/modal.Retries) | Function retry policy for input failures |

## Sandboxed execution

|                                                                                                      |                                               |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| [`Sandbox`](/docs/reference/modal.Sandbox)                                                           | An interface for restricted code execution    |
| [`ContainerProcess`](/docs/reference/modal.container_process#modalcontainer_processcontainerprocess) | An object representing a sandboxed process    |
| [`FileIO`](/docs/reference/modal.file_io#modalfile_iofileio)                                         | A handle for a file in the Sandbox filesystem |

## Container configuration

|                                          |                                                                    |
| ---------------------------------------- | ------------------------------------------------------------------ |
| [`Image`](/docs/reference/modal.Image)   | An API for specifying container images                             |
| [`Secret`](/docs/reference/modal.Secret) | A pointer to secrets that will be exposed as environment variables |

## Data primitives

### Persistent storage

|                                                                |                                                                 |
| -------------------------------------------------------------- | --------------------------------------------------------------- |
| [`Volume`](/docs/reference/modal.Volume)                       | Distributed storage supporting highly performant parallel reads |
| [`CloudBucketMount`](/docs/reference/modal.CloudBucketMount)   | Storage backed by a third-party cloud bucket (S3, etc.)         |
| [`NetworkFileSystem`](/docs/reference/modal.NetworkFileSystem) | Shared, writeable cloud storage (superseded by `modal.Volume`)  |

### In-memory storage

|                                        |                               |
| -------------------------------------- | ----------------------------- |
| [`Dict`](/docs/reference/modal.Dict)   | A distributed key-value store |
| [`Queue`](/docs/reference/modal.Queue) | A distributed FIFO queue      |

## Networking

|                                            |                                                                     |
| ------------------------------------------ | ------------------------------------------------------------------- |
| [`Proxy`](/docs/reference/modal.Proxy)     | An object that provides a static outbound IP address for containers |
| [`forward`](/docs/reference/modal.forward) | A context manager for publicly exposing a port from a container     |
