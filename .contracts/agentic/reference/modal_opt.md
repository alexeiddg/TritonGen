# Memory Snapshots

Modal Memory Snapshots can dramatically reduce the [cold start](/docs/guide/cold-start) latency of Modal Functions by skipping initialization work on most container boots.

For instance, during initialization, your code might issue many file read operations sequentially,
like the >20,000 file operations required to load `torch`.
It might then run a JIT compiler that takes several minutes or more,
like the one in PyTorch.
Memory Snapshots replace this initialization work with direct restoration of the memory state that work created.

The relative speedup is unbounded: the more work you do to create fewer bytes, the greater it becomes.
In our experience, practical initialization-heavy Functions often start up
[3-10x faster from Memory Snapshots](/blog/gpu-mem-snapshots).

There are two variants of Memory Snapshots.
[CPU Memory Snapshots](#cpu-memory-snapshots) capture the state of CPU memory.
[GPU Memory Snapshots](#gpu-memory-snapshots-alpha), an [alpha feature](/docs/guide/feature-maturity), also capture the state of GPU memory.

## CPU Memory Snapshots

CPU Memory Snapshots capture the state of a container and save it to disk.
This saved snapshot can then be used to put new containers directly into the exact same state.

You can enable Memory Snapshots for your Function with the `enable_memory_snapshot=True` parameter:

```python
@app.function(enable_memory_snapshot=True)
def my_func():
    ...
```

Then deploy the App, e.g. with `modal deploy`. Memory Snapshots are created only for deployed Apps.

Any code executed in global scope, such as imports, will be captured in the Memory Snapshot.
Use the [`Image.imports` context manager](/docs/reference/modal.Image#imports)
to import remote-only dependencies in the global scope.

```python
image = modal.Image.debian_slim().uv_pip_install("pandas")

with image.imports():
    import pandas as pd


@app.function(enable_memory_snapshot=True, image=image)
def my_func():
    print(f"pandas v{pd.__version__}")
```

## Container lifecycle hooks and Memory Snapshots

Modal's [container lifecycle hooks](/docs/guide/lifecycle-functions)
provide additional control over what parts of container initialization work
are included in Memory Snapshots. Put initialization code that you want to run
before snapshotting inside methods decorated with `@modal.enter(snap=True)`.

```python
@app.cls(enable_memory_snapshot=True)
class MyCls:
    @modal.enter(snap=True)
    def load(self):
        ...  # will be snapshot

    @modal.enter()
    def load_more(self):
        ...  # will not be snapshot
```

## GPU Memory Snapshots (Alpha)

<Callout variant="alpha">

This feature is currently in alpha. See [feature maturity](/docs/guide/feature-maturity) for more details.

</Callout>

GPU Memory Snapshots build on CPU Memory Snapshots and additionally capture GPU state.

In addition to `enable_memory_snapshot=True`,
pass `experimental_options={"enable_gpu_snapshot": True}` to your Function or Cls
to enable GPU Memory Snapshots.

```python
@app.function(
    gpu="a10",
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True}
    )
def my_gpu_func():
    ...
```

You'll generally want to include any expensive initialization work that
requires the GPU in the Memory Snapshot.
Use a Modal [Cls](/docs/guide/lifecycle-functions)
and put that work inside a `@modal.enter` method,
like so:

```python
image = modal.Image.debian_slim().uv_pip_install("transformers[torch]")

with image.imports():
     import torch
     from transformers import pipeline


@app.cls(
    gpu="h100",
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
    image=image,
)
class Llm:
    @modal.enter(snap=True)
    def init(self):
        self.pipeline = pipeline(model="Qwen/Qwen3-1.7B", device_map="cuda")
        self.pipeline.model = torch.compile(self.pipeline.model, mode="reduce-overhead")
        context = [{"role": "user", "content": DEFAULT_PROMPT}]
        self.pipeline(context)
```

You can find a complete code sample [here](/docs/examples/gpu_snapshot).

We recommend warming up your model by running a few forward passes on sample data
in the `@modal.enter(snap=True)` method to move more initialization work into the snapshotting phase.
Without warmup, this work is generally done on the first few requests after container start
(regardless of whether Memory Snapshots are used),
which shows up as tail latency.

### Limitations of GPU Memory Snapshots

[We've seen](/blog/gpu-mem-snapshots) that GPU Memory Snapshots can massively reduce cold start time,
but they are subject to certain limitations.
The underlying checkpoint/restore technology in the device drivers
is still quite new. We expect these limitations to be resolved as the drivers update.
We recommend reviewing the material below
before adding GPU Memory Snapshots to your Modal Functions.

#### You may need to rewrite code for compatibility or to improve performance

While most GPU-accelerated Modal Functions can take advantage of GPU Memory Snapshots,
apart from the limitations described below,
most Functions will need some of their code rewritten to ensure compatibility with GPU Memory Snapshots
or to deliver performance improvements.

This is particularly true for more complex inference engines,
like those used to maximize [LLM inference performance](/docs/guide/high-performance-llm-inference).
For instance, it is often better to discard the initial, unfilled KV cache before the snapshot is taken,
then recreate it on restore, rather than writing and then reading the KV cache's meaningless pages in a snapshot.
See [this example with vLLM](/docs/examples/vllm_snapshot)
and [this example with SGLang](/docs/examples/sglang_snapshot)
for sample code, patterns, and other guidance.

#### GPU Memory Snapshots are generally incompatible with multi-GPU code

Though a few simple programs interacting with multiple GPUs can be successfully snapshot,
there are known issues with most practical uses of multiple GPUs,
stemming from multi-process and multi-GPU resource management concerns.
We anticipate improvements here in future drivers.

#### GPU Memory Snapshots are generally incompatible with non-CUDA GPU code

For instance, use of graphics capabilities prior to snapshotting will generally cause failures.

#### GPU Memory Snapshots do not speed up model loading from storage

Memory Snapshots use the same high-performance distributed filesystem
that delivers Modal [Images](/docs/guide/images)
and Modal [Volumes](/docs/guide/volumes)
to our worldwide fleet of containers at minimum latency and maximum throughput.

That means that if the majority of your initialization latency is spent loading weights,
GPU Memory Snapshots will generally not improve your cold start times --
and may even worsen them, by adding overhead.
Instead, Memory Snapshots should primarily be used to "skip past" work
that is not bottlenecked by storage bandwidth, like library initialization (imports)
and JIT compilation (Torch, DeepGEMM, Triton, etc.).

#### GPU Memory Snapshots can interact poorly with `torch.compile`

In certain cases, running the Torch Compiler can cause Memory Snapshot creation to fail.

Some of these failures can be fixed by setting the environment variable `TORCHINDUCTOR_COMPILE_THREADS` to `1` before compiling.

## Memory Snapshots FAQs

### How do I know whether Memory Snapshots are being created or used?

You can see Memory Snapshots in action in your Function's "Containers" tab. Containers that created a memory snapshot are marked with a <CloudUpload size={16} class="inline opacity-80" /> icon in the Startup column. Containers that restored from a snapshot are marked with a <CloudLightning size={16} class="inline opacity-80" /> icon. In the below screenshot, the container startup times when restoring from a memory snapshot are significantly faster.

![snapshot icons](https://modal-cdn.com/cdnbot/memory-snapshot-iconss6tm168n_cb303ec9.webp)

You can also search your Modal App's logs for the line `Snapshot created. Restoring Function from memory snapshot.`

### When are Memory Snapshots updated?

Redeploying your Function with new configuration (e.g. a [new GPU type](/docs/guide/gpu))
or new code will cause previous Memory Snapshots to become obsolete.
Subsequent invocations to the new Function version will automatically create new Memory Snapshots with the new configuration and code.

Changes to [Modal Volumes](/docs/guide/volumes) do not cause Memory Snapshots to update.
Deleting files in a Volume used during restore will cause restore failures.

### I haven't changed my Function. Why do I still see Memory Snapshots being created sometimes?

Modal recaptures Memory Snapshots to keep up with the platform's latest runtime and security changes.

Additionally, you may observe your Function being snapshot multiple times during its first few invocations.
This happens because Memory Snapshots are specific to the underlying worker type that created them
(e.g. CPU flags), and Modal Functions run across a handful of worker types.

Snapshot creation may add some latency to Function initialization.

CPU-only Functions need around 6 snapshots for full coverage, and Functions targeting a specific
GPU (e.g. A100) need 2-3.

### How do Memory Snapshots handle randomness?

If your application depends on uniqueness of state, you must evaluate your
Function code and verify that it is resilient to snapshotting operations. For
example, if a variable is randomly initialized and that value included in a Memory Snapshot,
that variable will be identical after every restore, possibly breaking uniqueness expectations
of later code.

## Advanced usage of Memory Snapshots

### Using GPUs without using GPU Memory Snapshots

CPU Memory Snapshots on their own block GPU access,
but GPU Functions can still benefit from Memory Snapshots.
This involves refactoring your initialization code to run across two separate `@modal.enter` functions:
one that runs before creating the snapshot (`snap=True`),
and one that runs after restoring from the snapshot (`snap=False`).

For instance, you might load model weights into CPU memory in the `snap=True` method,
then move the weights onto GPU memory in the `snap=False` method.

Even without GPU snapshotting, this technique reduces the startup time for `Embedder.run`
in the below example by about 3x, from ~6 seconds down to just ~2 seconds.

```python
import modal

image = modal.Image.debian_slim().uv_pip_install("sentence-transformers")
app = modal.App("sentence-transformers", image=image)

with image.imports():
    from sentence_transformers import SentenceTransformer

model_vol = modal.Volume.from_name("sentence-transformers-models", create_if_missing=True)


@app.cls(gpu="a10", volumes={"/models": model_vol}, enable_memory_snapshot=True)
class Embedder:
    model_id = "BAAI/bge-small-en-v1.5"

    @modal.enter(snap=True)
    def load(self):
        # Create a memory snapshot with the model loaded in CPU memory.
        self.model = SentenceTransformer(f"/models/{self.model_id}", device="cpu")

    @modal.enter(snap=False)
    def setup(self):
        self.model.to("cuda")  # Move the model to the GPU!

    @modal.method()
    def run(self, sentences:list[str]):
        embeddings = self.model.encode(sentences, normalize_embeddings=True)
        print(embeddings)


@app.local_entrypoint()
def main():
    Embedder().run.remote(sentences=["what is the meaning of life?"])


if __name__ == "__main__":
    cls = modal.Cls.from_name("sentence-transformers", "Embedder")
    cls().run.remote(sentences=["what is the meaning of life?"])
```

#### GPUs are not available in CPU-only Memory Snapshots

If you are using the GPU Memory Snapshot feature (`enable_gpu_snapshot`), then
GPUs are available within `@modal.enter(snap=True)`.

If you are using memory snapshots _without_ `enable_gpu_snapshot`, then it's important
to note that GPUs will not be available within the `@modal.enter(snap=True)` method.

```python
image = modal.Image.debian_slim().uv_pip_install("torch", "numpy")


@app.cls(enable_memory_snapshot=True, gpu="a10", image=image)
class GPUAvailability:
    @modal.enter(snap=True)
    def no_gpus_available_during_snapshots(self):
        import torch
        print(f"GPUs available: {torch.cuda.is_available()}")  # False

    @modal.enter(snap=False)
    def gpus_available_following_restore(self):
        import torch
        print(f"GPUs available: {torch.cuda.is_available()}")  # True

    @modal.method()
    def demo(self):
        print(f"GPUs available: {torch.cuda.is_available()}") # True
```

#### Watch out for accidental GPU initialization during CPU-only Memory Snapshots

The `torch.cuda` module has multiple functions which, if called during
snapshotting, will initialize CUDA as having zero GPU devices. Such functions
include `torch.cuda.is_available` and `torch.cuda.get_device_capability`.
If you're using a framework that calls these methods during its import phase,
it may not be compatible with memory snapshots. The problem can manifest as
confusing "cuda not available" or "no CUDA-capable device is detected" errors.

We have found that importing PyTorch twice solves the problem in some cases:

```python

@app.cls(enable_memory_snapshot=True, gpu="A10")
class GPUAvailability:
    @modal.enter(snap=True)
    def pre_snap(self):
        import torch
        ...
    @modal.enter(snap=False)
    def post_snap(self):
        import torch   # re-import to re-init GPU availability state
        ...
```

In particular, `xformers` is known to call `torch.cuda.get_device_capability` on
import, so if it is imported during snapshotting it can unhelpfully initialize
CUDA with zero GPUs. The
[workaround](https://github.com/facebookresearch/xformers/issues/1030) for this
is to set the `XFORMERS_ENABLE_TRITON` environment variable to `1` in your `modal.Image`.

```python
image = modal.Image.debian_slim().pip_install("xformers>=0.28")  # for instance
image = image.env({"XFORMERS_ENABLE_TRITON": "1"})
```

------

# High-performance LLM inference

This high-level guide documents the key techniques used to achieve high performance
when running LLM inference on Modal.

Open weights models and open source inference engines have
closed much of the gap with proprietary models and proprietary engines
and continue to improve as they attract work from a broad community.
It is now and will increasingly be economical to run many generative AI applications in-house,
rather than relying on external providers.

Achieving competitive performance and cost is not instantaneous, however.
It requires some thought and tuning.
And LLM inference is in many ways quite different to the web serving and database workloads
that engineers are used to deploying and optimizing.

This guide collects techniques we have seen work in production inference deployments.
We include code samples so that you can try high-performance LLM inference for yourself.

We split the guide by the key performance criterion that matters for the workload:

- **[throughput](#achieving-high-throughput-llm-inference-tps)**,
  for large "jobs" made of many parallel requests that are only finished when they all finish,
- **[latency](#minimizing-llm-inference-latency-ttfttpotttlt)**,
  for serving each individual request as fast as possible, usually on human-interactive timescales,
- **[cold start time](#high-performance-llm-inference-for-bursty-workloads-cold-start-time)**,
  for bursty workloads that mix latency- and throughput-sensitive components.

This high-level guide and the attendant code samples are intended to kick-start
your own process of inference deployment and performance optimization.
You can find [baseline benchmarks](/llm-almanac/advisor)
and [benchmarking recommendations](/llm-almanac/how-to-benchmark)
in our [LLM Engineer's Almanac](/llm-almanac/workloads).

If you just want to get started running a basic LLM server on Modal, see
[this example](https://modal.com/docs/examples/llm_inference).
If you just want to dive into code, see
[this example for high throughput](https://modal.com/docs/examples/vllm_throughput),
[this example for low latency](https://modal.com/docs/examples/sglang_low_latency),
and [this example for low cold start time](https://modal.com/docs/examples/sglang_snapshot).

## Achieving high throughput LLM inference (TPS)

The quintessential "high throughput" LLM inference workload is a database backfill:
on a trigger, a large number (100s or more) of rows need to be processed,
e.g. to produce a sentiment score as part of an analytics pipeline
or to produce a generation that will be scored as part of offline evals.
No person or system is waiting on the result from any particular row.

Performance is defined by _throughput_, the rate at which tasks are completed,
which translates to end-to-end latency for the entire job.
For most deployments, this in turn directly determines cost.
It is measured in tokens per second (TPS).

Many, but not all, high throughput LLM inference applications have large contexts and small outputs,
which means they are dominated by prefill/prompt processing time, rather than decode/token generation time.
Combined with batching that increases
[arithmetic intensity](https://modal.com/gpu-glossary/perf/arithmetic-intensity),
throughput-oriented LLM inference jobs are generally
[compute-bound](https://modal.com/gpu-glossary/perf/compute-bound).

In general, high throughput is easier to achieve than low latency.
GPUs are inherently [designed for maximum throughput](https://modal.com/gpu-glossary/perf/latency-hiding).
Additionally, LLM training is a throughput-sensitive workload, so good kernels
are typically made available open source earlier.

For instance, the [Flash Attention 4 kernel](/blog/reverse-engineer-flash-attention-4)
that extends the Flash Attention kernel series to [Blackwell GPUs](https://modal.com/blog/introducing-b200-h200)
is, at time of writing months after its initial release,
primarily suitable for throughput-sensitive applications -- but watch this space!

For related reasons, we don't recommend using 4bit floating point (FP4) for these jobs.
FP4 is only supported in [Blackwell or later GPUs](https://modal.com/gpu-glossary/device-software/compute-capability).
Instead, we recommend the more mature 8bit floating point (FP8),
supported in Hopper or later GPUs (one generation back).

On Modal, the [rates](/pricing) for 16bit FLOP/$ are roughly the same across
A100s, H100s, and B200s -- newer GPUs run faster but cost more to match.
So peak throughput per _dollar_ per replica is roughly the same,
even though throughput per _second_ per replica is lower.

But older GPUs running at lower rates offer a few advantages:

- any time spent [underutilizing the GPUs](/blog/gpu-utilization-guide) is less expensive
- GPUs a generation or two back are generally available in larger quantities from hyperscalers

Throughput-oriented jobs don't necessarily benefit from scaling up each replica to more GPUs.
The aggregate throughput is the same as more replicas with fewer GPUs,
but fewer GPUs means reduced communication overhead and
reduced complexity, especially for single GPU-per-replica deployments.
Importantly, you must be able to fit a large enough batch of sequences
into the [GPU RAM](https://modal.com/gpu-glossary/device-hardware/gpu-ram)
that you are compute-bound, or else efficiency will decrease.

We recommend the [vLLM](https://vllm.ai/) inference server for this use case.
It is better able to schedule a mix of prefill and decode work,
which leads to higher throughput.

### High throughput LLM inference on Modal

The lack of latency constraints opens up a large number
of architectural choices for high throughput LLM inference.

For instance, values can be retrieved from an external datastore
or a [Modal Volume](/docs/guide/volumes)
based on identifiers or other information in the datastore.
This is particularly useful for
[cronjob deployments on Modal](/docs/guide/cron).
Results can then be placed back in that datastore.

Modal provides primitives for building a
[job queue](/docs/guide/job-queue)
that can scale to millions of pending inputs
and jobs that last up to a week.
In this case, the underlying LLM inference is provided by a
[Modal Cls](/docs/guide/lifecycle-functions)
invoked via
[`.spawn`](/docs/guide/job-queue).
Each call gets a string
[`modal.FunctionCall` identifier](/docs/reference/modal.FunctionCall)
that can be used to query the result for up to a week.

The primary scaling limit from Modal in this case is the rate at which these calls can be queued.
If the inference system can complete more than 400 tasks per second,
we recommend batching multiple tasks into a single Function input until peak throughput
in tasks per second is serviced by 400 inputs per second.

See [this code sample](https://modal.com/docs/examples/vllm_throughput)
for a system that implements these recommendatons and
achieves maximal per-replica throughput.

## Minimizing LLM inference latency (TTFT/TPOT/TTLT)

The quintessential "low latency" LLM inference workload is a chatbot:
each request represents a waiting user, and users operate at the scale of a few hundred milliseconds.
Generating a token of usefully intelligent text often also takes on the order of milliseconds,
and users want many tokens in responses, so latency budgets are tight.

Performance is defined by _latency_, the time a given task spends waiting.
It is measured in time-to-first-token (TTFT) and time-per-output-token (TPOT)
or in time-to-last-token (TTLT),
depending on to what degree the application supports streaming responses.
For streaming applications, like most chatbots, TTFT matters most.

To whatever degree the application does support streaming, it is strongly recommended
to improve perceived latency by users.
Contemporary Transformer language models are sequential and so generate their responses
serially, leading to long gaps between the creation of the first token in a response and the last.

These long decode or token generation phases demand quite different performance
from hardware than long prefills do.
They are typically [memory-bound](https://modal.com/gpu-glossary/perf/memory-bound)
and so benefit from techniques that reduce the amount of memory loaded per token into the
[Streaming Multiprocessors](https://modal.com/gpu-glossary/device-hardware/streaming-multiprocessor)
or increase the amount of available
[memory bandwidth](https://modal.com/gpu-glossary/perf/memory-bandwidth).

Several techniques can reduce the amount of memory loaded per token:

- smaller and more aggressively [quantized](https://quant.exposed) models require less memory
- [speculative decoding](https://huggingface.co/docs/text-generation-inference/en/conceptual/speculation)
  generates multiple tokens at once via draft models

For memory-bound workloads, quantizing a model to a format not natively supported by the hardware
can still sometimes lead to gains.
The reduced demand on memory bandwidth cuts memory latency and there is generally sufficient unused
[arithmetic bandwidth](https://modal.com/gpu-glossary/perf/arithmetic-bandwidth)
to perform extra numerical conversions.

There are a wide variety of speculative decoding techniques, ranging from simple n-gram speculation
to stacks of models drafting tokens for each other in sequence.
We have generally found that the [EAGLE-3 method](https://arxiv.org/abs/2503.01840)
provides the best performance improvement for the least overhead --
computationally and operationally.
Generic draft models are available on Hugging Face,
but we have also seen major improvements from custom draft models
trained on sample production data using tools like
[SpecForge](https://lmsys.org/blog/2025-07-25-spec-forge/).

Additionally, using multiple GPUs to generate a single token increases the aggregate memory bandwidth,
at the cost of some extra communication.
Critically, multiple accelerators need to be used to load model weights in parallel,
or latency will not be reduced.
That means the usual form of parallelism used to reduce latency is _tensor parallelism_,
which splits up individual matrix multiplications across GPUs,
rather than _pipeline parallelism_,
which splits the entire model across GPUs.

There are few models below 70B parameters that work well in 4bit floating point
(with exceptions like [GPT-OSS](https://modal.com/docs/examples/gpt_oss_inference)).
Additionally, at time of writing in early 2026, there are not high-quality open source
Blackwell-optimized kernels for latency-sensitive LLM inference.
Therefore, we generally recommend FP8-quantized models on H100s or H200s.

Finally, we recommend the [SGLang](https://docs.sglang.io/)
inference engine for these workloads.
SGLang generally exhibits lower host overhead --
time when the GPU idles waiting on the CPU --
for decode-heavy workloads, especially for smaller models.
You can read more about host overhead and its solutions in
[this blog post](/blog/host-overhead-inference-efficiency).

### Low latency LLM inference on Modal

For latency budgets in the few hundreds of milliseconds,
network latencies and proxy/load-balancing overhead matter --
communicating with clients across an ocean takes dozens of milliseconds,
due to speed-of-light constraints.

Modal offers ultra-low-latency, regionalized web server deployment with
`modal.experimental.http_server`
to reduce network overhead below 100ms.
Please contact us if you are interested in running production LLM inference
with the experimental `http_server`.

You can find an example demonstrating all the pieces of
low latency LLM inference on Modal together
[here](https://modal.com/docs/examples/sglang_low_latency).

## High performance LLM inference for bursty workloads (cold start time)

The final major class of workloads sits between pure throughput and pure latency.
The quintessential application is a "workflow" where LLM inference is one workflow step,
and the workflow is sometimes run interactively by a human and at other times run asynchronously in bulk.

For these applications, the primary concern is handling the high
[peak-to-average load ratio](https://brooker.co.za/blog/2023/03/23/economics.html).
For instance, a pipeline might serve zero requests per second most of the time,
then ten for a bit, then one hundred, then back down to zero.
Statically provisioning enough resources to handle one hundred requests is clearly wasteful,
but spinning up new resources on demand incurs latency.

The key performance criterion, then, is
[_cold start time_](/docs/guide/cold-start):
how long does it take for a new replica to spin up and start handling requests.
On a typical cloud deployment, that includes instance requisition, machine boot, and container setup.
We've written about the resource allocation challenges [here](/blog/gpu-utilization-guide).

Approaches based on requesting resources from clouds directly take minutes to tens of minutes.
Modal has been designed from the kernel up to provide sub-second latencies
all the way through to container start.
From there, the primary performance concern is speeding up server startup.

- **Use small models and quantize aggressively**.
  Models can be loaded from a [Modal Volume](/docs/guide/volumes)
  at a rate of 1-2 GB/s. That means you're incurring nearly a second of cold start latency
  per gigabyte of model weights. More exotic compression formats, like integer quantization
  or even ternary quantization, are particularly helpful here, even when they don't improve
  latency during inference.

- **Skip compilation steps**.
  Optimizations like CUDA Graph capture, JIT-compiled kernels, and Torch compilation
  are great for improving latency and throughput but they are generally quite tricky to cache
  and cache hits sometimes take nearly as long as cache misses.
  That often means a large latency penalty from compilation on each boot,
  and latencies can easily range into the tens of seconds or even tens of minutes.

- **Restore from snapshots**.
  In some cases, startup-time work like JIT compilation is unavoidable.
  For these workloads, Modal provides
  [Memory Snapshots](/docs/guide/memory-snapshots):
  the full in-memory state of a container just before it is ready to
  handle requests is serialized to disk and future container starts
  only need to deserialize this back into memory.
  Modal includes support for
  [GPU Memory Snapshots](/blog/gpu-mem-snapshots)
  so that GPU-accelerated LLM inference servers can be snapshot as well.
  Memory snapshotting is powerful
  ([we've observed 10x reductions in cold start time](/blog/gpu-mem-snapshots)),
  but it requires some code modification, described below.

Which optimizations discussed above apply
depend on the balance of the workload between low latency and high throughput.
But a few general statements can be made.
For instance, speculative decoding is generally a bad choice,
since it harms performance in the high throughput regime.

Relatedly, we don't have a particular recommendation between vLLM and SGLang here.
Besides the points made above about host overhead latency vs bulk throughput,
the primary difference we have seen is that vLLM is a bit faster to market with new models
and new features, but SGLang is a bit easier to hack on and extend.

### Serving bursty LLM inference workloads on Modal

Modal's rapid autoscaling infrastructure,
from [the custom container runtime and filesystem](/blog/jono-containers-talk),
to [memory snapshot support](/blog/gpu-mem-snapshots),
is particularly well-suited
to bursty LLM inference workloads.

These workloads can either be served by vanilla
[Functions](/docs/guide/apps)
invoked via remote Python calls or as
[Web Functions](/docs/guide/webhooks)
invoked via HTTP.
Web Functions are better for integrating with a variety
of producers and consumers.
The tradeoff of lower overhead for increased complexity
with `modal.experimental.http_server` is generally not worth it.

The [`@modal.concurrent` decorator](/docs/guide/concurrent-inputs)
supports setting both a limit (`max_inputs`)
and a target (`target_inputs`).
Set the limit higher than the target to absorb load increases into
existing capacity (typically at the expense of longer latency).
Make sure that the inference server is configured to handle batches as large as `max_inputs`
without internal queueing!

Almost all GPU programs can be snapshot, but most GPU programs
require some code changes to be snapshot.
For instance, both the vLLM and SGLang inference servers require
manual offloading of weights/KV cache to CPU memory before snapshotting.

For details, see our full sample code for running bursty workloads on Modal
with vLLM [here](https://modal.com/docs/examples/vllm_snapshot)
and with SGLang [here](https://modal.com/docs/examples/sglang_snapshot).

----


# Batch Processing

Modal is optimized for large-scale batch processing, allowing functions to scale to thousands of parallel containers with zero additional configuration. Function calls can be submitted asynchronously for background execution, eliminating the need to wait for jobs to finish or tune resource allocation.

This guide covers Modal's batch processing capabilities, from basic invocation to integration with existing pipelines.

## Background Execution with `.spawn_map`

The fastest way to submit multiple jobs for asynchronous processing is by invoking a function with `.spawn_map`. When combined with the [`--detach`](/docs/reference/cli/run) flag, your App continues running until all jobs are completed.

Here's an example of submitting 100,000 videos for parallel embedding. You can disconnect after submission, and the processing will continue to completion in the background:

```python
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
```

This pattern works best for jobs that store results externally—for example, in a [Modal Volume](/docs/guide/volumes), [Cloud Bucket Mount](/docs/guide/cloud-bucket-mounts), or your own database\*.

_\* For database connections, consider using [Modal Proxy](/docs/guide/proxy-ips) to maintain a static IP across thousands of containers._

## Parallel Processing with `.map`

Using `.map` allows you to offload expensive computations to powerful machines while gathering results. This is particularly useful for pipeline steps with bursty resource demands. Modal handles all infrastructure provisioning and de-provisioning automatically.

Here's how to implement parallel video similarity queries as a single Modal function call:

```python
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
```

This example runs `compute_video_similarity` on an autoscaling pool of L40S GPUs, returning scores to a local process for further processing.

## Integration with Existing Systems

The recommended way to use Modal Functions within your existing data pipeline is through [deployed function invocation](/docs/guide/trigger-deployed-functions). After deployment, you can call Modal functions from external systems:

```python
def external_function(inputs):
    compute_similarity = modal.Function.from_name(
        "gather-results-example",
        "compute_video_similarity"
    )
    for result in compute_similarity.map(inputs):
        # Process results
        pass
```

You can invoke Modal Functions from any Python context, gaining access to built-in observability, resource management, and GPU acceleration.


----

# Dynamic batching

Modal's `@batched` feature allows you to accumulate requests
and process them in dynamically-sized batches, rather than one-by-one.

Batching increases throughput at a potential cost to latency.
Batched requests can share resources and reuse work, reducing the time and cost per request.
Batching is particularly useful for GPU-accelerated machine learning workloads,
as GPUs are designed to maximize throughput and are frequently bottlenecked on shareable resources,
like weights stored in memory.

Static batching can lead to unbounded latency, as the function waits for a fixed number of requests to arrive.
Modal's dynamic batching waits for the lesser of a fixed time _or_ a fixed number of requests before executing,
maximizing the throughput benefit of batching while minimizing the latency penalty.

## Enable dynamic batching with `@batched`

To enable dynamic batching, apply the
[`@modal.batched` decorator](/docs/reference/modal.batched) to the target
Python function. Then, wrap it in `@app.function()` and run it on Modal,
and the inputs will be accumulated and processed in batches.

Here's what that looks like:

```python
import modal

app = modal.App()

@app.function()
@modal.batched(max_batch_size=2, wait_ms=1000)
async def batch_add(xs: list[int], ys: list[int]) -> list[int]:
    return [x + y for x, y in zip(xs, ys)]
```

When you invoke a function decorated with `@batched`, you invoke it asynchronously on individual inputs.
Outputs are returned where they were invoked.

For instance, the code below invokes the decorated `batch_add` function above three times, but `batch_add`
only executes twice:

```python continuation
@app.local_entrypoint()
async def main():
    inputs = [(1, 300), (2, 200), (3, 100)]
    async for result in batch_add.starmap.aio(inputs):
        print(f"Sum: {result}")
        # Sum: 301
        # Sum: 202
        # Sum: 103
```

The first time it is executed with `xs` batched to `[1, 2]`
and `ys` batched to `[300, 200]`. After about a one second delay, it is executed with `xs`
batched to `[3]` and `ys` batched to `[100]`.
The result is an iterator that yields `301`, `202`, and `103`.

## Use `@batched` with functions that take and return lists

For a Python function to be compatible with `@modal.batched`, it must adhere to
the following rules:

- ** The inputs to the function must be lists. **
  In the example above, we pass `xs` and `ys`, which are both lists of `int`s.
- ** The function must return a list**. In the example above, the function returns
  a list of sums.
- ** The lengths of all the input lists and the output list must be the same. **
  In the example above, if `L == len(xs) == len(ys)`, then `L == len(batch_add(xs, ys))`.

## Modal `Cls` methods are compatible with dynamic batching

Methods on Modal [`Cls`](/docs/guide/lifecycle-functions)es also support dynamic batching.

```python
import modal

app = modal.App()

@app.cls()
class BatchedClass():
    @modal.batched(max_batch_size=2, wait_ms=1000)
    async def batch_add(self, xs: list[int], ys: list[int]) -> list[int]:
        return [x + y for x, y in zip(xs, ys)]
```

One additional rule applies to classes with Batched Methods:

- If a class has a Batched Method, it **cannot have other Batched Methods or [Methods](/docs/reference/modal.method#modalmethod)**.

## Configure the wait time and batch size of dynamic batches

The `@batched` decorator takes in two required configuration parameters:

- `max_batch_size` limits the number of inputs combined into a single batch.
- `wait_ms` limits the amount of time the Function waits for more inputs after
  the first input is received.

The first invocation of the Batched Function initiates a new batch, and subsequent
calls add requests to this ongoing batch. If `max_batch_size` is reached,
the batch immediately executes. If the `max_batch_size` is not met but `wait_ms`
has passed since the first request was added to the batch, the unfilled batch is
executed.

### Selecting a batch configuration

To optimize the batching configurations for your application, consider the following heuristics:

- Set `max_batch_size` to the largest value your function can handle, so you
  can amortize and parallelize as much work as possible.

- Set `wait_ms` to the difference between your targeted latency and the execution time. Most applications
  have a targeted latency, and this allows the latency of any request to stay
  within that limit.

## Serve Web Functions with dynamic batching

Here's a simple example of serving a Function that batches requests dynamically
with a [`@modal.fastapi_endpoint`](/docs/guide/webhooks). Run
[`modal serve`](/docs/reference/cli/serve), submit requests to the endpoint,
and the Function will batch your requests on the fly.

```python
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
```

Now, you can submit requests to the Web Function and process them in batches. For instance, the three requests
in the following example, which might be requests from concurrent clients in a real deployment,
will be batched into two executions:

```python notest
import asyncio
import aiohttp

async def send_post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.json()

async def main():
    # Enter the Web Function URL here
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
```


-----

# Cold start performance

This guide page details the techniques and Modal features used to improve cold start performance.

## What is a cold start?

Modal Functions are run in [containers](/docs/guide/images).

If a container is already ready to run your Function, it will be reused.

If not, Modal spins up a new container.
This is known as a _cold start_,
and it is often associated with higher latency.

There are two sources of increased latency during cold starts:

1. inputs may **spend more time waiting** in a queue for a container
   to become ready or "warm".
2. when an input is handled by the container that just started,
   there may be **extra work that only needs to be done on the first invocation**
   ("initialization").

If you are invoking Functions with no warm containers
or if you otherwise see inputs spending too much time in the "pending" state,
you should
[target queueing time for optimization](#reduce-time-spent-queueing-for-warm-containers).

If you see some Function invocations taking much longer than others,
and those invocations are the first handled by a new container,
you should
[target initialization for optimization](#reduce-latency-from-initialization).

## Reduce time spent queueing for warm containers

New containers are booted when there are not enough other warm containers to
to handle the current number of inputs.

For example, the first time you send an input to a Function,
there are zero warm containers and there is one input,
so a single container must be booted up.
The total latency for the input will include
the time it takes to boot a container.

If you send another input right after the first one finishes,
there will be one warm container and one pending input,
and no new container will be booted.

Generalizing, there are two factors that affect the time inputs spend queueing:
the time it takes for a container to boot and become warm (which we solve by booting faster)
and the time until a warm container is available to handle an input (which we solve by having more warm containers).

### Warm up containers faster

The time taken for a container to become warm
and ready for inputs can range from seconds to minutes.

Modal's custom container stack has been heavily optimized to reduce this time.
You can read about some of our optimizations [here](https://modal.com/blog/jono-containers-talk).
Containers boot in about one second.

But before a container is considered warm and ready to handle inputs,
we need to execute any logic in your code's global scope (such as imports)
or in any
[`modal.enter` methods](/docs/guide/lifecycle-functions).
So if your boots are slow, these are the first places to work on optimization.

For example, you might be downloading a large model from a model server
during the boot process.
You can instead
[download the model ahead of time](/docs/guide/model-weights),
so that it only needs to be downloaded once.

For models in the tens of gigabytes,
this can reduce boot times from minutes to seconds.

### Run more warm containers

It is not always possible to speed up boots sufficiently.
For example, seconds of added latency to load a model may not
be acceptable in an interactive setting.

In this case, the only option is to have more warm containers running.
This increases the chance that an input will be handled by a warm container,
for example one that finishes an input while another container is booting.

Modal currently exposes [three parameters](/docs/guide/scale) that control how
many containers will be warm: `scaledown_window`, `min_containers`,
and `buffer_containers`.

All of these strategies can increase the resources consumed by your Function
and so introduce a trade-off between cold start latencies and cost.

#### Keep containers warm for longer with `scaledown_window`

Modal containers will remain idle for a short period before shutting down. By
default, the maximum idle time is 60 seconds. You can configure this by setting
the `scaledown_window` on the [`@function`](/docs/reference/modal.App#function)
decorator. The value is measured in seconds, and it can be set anywhere between
two seconds and twenty minutes.

```python
import modal

app = modal.App()

@app.function(scaledown_window=300)
def my_idle_greeting():
    return {"hello": "world"}
```

Increasing the `scaledown_window` reduces the chance that subsequent requests
will require a cold start, although you will be billed for any resources used
while the container is idle (e.g., GPU reservation or residual memory
occupancy). Note that containers will not necessarily remain alive for the
entire window, as the autoscaler will scale down more aggressively when the
Function is substantially over-provisioned.

#### Overprovision resources with `min_containers` and `buffer_containers`

Keeping already warm containers around longer doesn't help if there are no warm
containers to begin with, as when Functions scale from zero.

To keep some containers warm and running at all times, set the `min_containers`
value on the [`@function`](/docs/reference/modal.App#function) decorator. This
puts a floor on the the number of containers so that the Function doesn't scale
to zero. Modal will still scale up and spin down more containers as the
demand for your Function fluctuates above the `min_containers` value, as usual.

While `min_containers` overprovisions containers while the Function is idle,
`buffer_containers` provisions extra containers while the Function is active.
This "buffer" of extra containers will be idle and ready to handle inputs if
the rate of requests increases. This parameter is particularly useful for
bursty request patterns, where the arrival of one input predicts the arrival of more inputs,
like when a new user or client starts hitting the Function.

```python
import modal

app = modal.App(image=modal.Image.debian_slim().pip_install("fastapi"))

@app.function(min_containers=3, buffer_containers=3)
def my_warm_greeting():
    return "Hello, world!"
```

## Reduce latency from initialization

Some work is done the first time that a function is invoked
but can be used on every subsequent invocation.
This is
[_amortized work_](https://www.cs.cornell.edu/courses/cs312/2006sp/lectures/lec18.html)
done at initialization.

For example, you may be using a large pre-trained model
whose weights need to be loaded from disk to memory the first time it is used.

This results in longer latencies for the first invocation of a warm container,
which shows up in the application as occasional slow calls: high tail latency or elevated p9Xs.

### Move initialization work out of the first invocation

Some work done on the first invocation can be moved up and completed ahead of time.

Any work that can be saved to disk, like
[downloading model weights](/docs/guide/model-weights),
should be done as early as possible. The results can be included in the
[container's Image](/docs/guide/images)
or saved to a
[Modal Volume](/docs/guide/volumes).

Some work is tricky to serialize, like spinning up a network connection or an inference server.
If you can move this initialization logic out of the function body and into the global scope or a
[container `enter` method](https://modal.com/docs/guide/lifecycle-functions#enter),
you can move this work into the warm up period.
Containers will not be considered warm until all `enter` methods have completed,
so no inputs will be routed to containers that have yet to complete this initialization.

For more on how to use `enter` with machine learning model weights, see
[this guide](/docs/guide/model-weights).

Note that `enter` doesn't get rid of the latency --
it just moves the latency to the warm up period,
where it can be handled by
[running more warm containers](#run-more-warm-containers).

### Share initialization work across cold starts with Memory Snapshots

Cold starts can also be made faster by using Modal
[Memory Snapshots](/docs/guide/memory-snapshots).

Invocations of a Function after the first
are faster in part because the memory is already populated
with values that otherwise need to be computed or read from disk,
like the contents of imported libraries.

Memory snapshotting captures the state of a container's memory
at user-controlled points after it has been warmed up
and reuses that state in future boots, which can substantially
reduce cold start latency penalties and warm up period duration.

Refer to the [Memory Snapshots guide](/docs/guide/memory-snapshots)
for details.

### Optimize initialization code

Sometimes, there is nothing to be done but to speed this work up.

Here, we share specific patterns that show up in optimizing initialization
in Modal Functions.

#### Load multiple large files concurrently

Often Modal applications need to read large files into memory (eg. model
weights) before they can process inputs. Where feasible these large file
reads should happen concurrently and not sequentially. Concurrent IO takes
full advantage of our platform's high disk and network bandwidth
to reduce latency.

One common example of slow sequential IO is loading multiple independent
Huggingface `transformers` models in series.

```python notest
from transformers import CLIPProcessor, CLIPModel, BlipProcessor, BlipForConditionalGeneration
model_a = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor_a = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model_b = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
processor_b = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
```

The above snippet does four `.from_pretrained` loads sequentially.
None of the components depend on another being already loaded in memory, so they
can be loaded concurrently instead.

They could instead be loaded concurrently using a function like this:

```python notest
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import CLIPProcessor, CLIPModel, BlipProcessor, BlipForConditionalGeneration

def load_models_concurrently(load_functions_map: dict) -> dict:
    model_id_to_model = {}
    with ThreadPoolExecutor(max_workers=len(load_functions_map)) as executor:
        future_to_model_id = {
            executor.submit(load_fn): model_id
            for model_id, load_fn in load_functions_map.items()
        }
        for future in as_completed(future_to_model_id.keys()):
            model_id_to_model[future_to_model_id[future]] = future.result()
    return model_id_to_model

components = load_models_concurrently({
    "clip_model": lambda: CLIPModel.from_pretrained("openai/clip-vit-base-patch32"),
    "clip_processor": lambda: CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32"),
    "blip_model": lambda: BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large"),
    "blip_processor": lambda: BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
})
```

If performing concurrent IO on large file reads does _not_ speed up your cold
starts, it's possible that some part of your function's code is holding the
Python [GIL](https://wiki.python.org/moin/GlobalInterpreterLock) and reducing
the efficacy of the multi-threaded executor.


----


# Configuring CPU, memory, and disk

Each Modal Function or Sandbox container has a default request of 0.125 CPU cores and 128 MiB of memory.
Containers can exceed this minimum if the worker has available CPU or memory.
You can also guarantee access to more resources by requesting larger values, [similarly to Kubernetes](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

## CPU cores

If you have code that must run on a larger number of cores, you can
request that using the `cpu` argument. This allows you to specify a
floating-point number of CPU cores:

```python
import modal

app = modal.App()

@app.function(cpu=8.0)
def my_function():
    # code here will have access to at least 8.0 cores
    ...
```

Note that this value corresponds to physical cores, not vCPUs.

Modal also will set several environment variables that control multi-threading
behavior in linear algebra libraries (e.g., `OPENBLAS_NUM_THREADS`,
`OMP_NUM_THREADS`, `MKL_NUM_THREADS`) based on your CPU request.

## Memory

If you have code that needs more guaranteed memory, you can request it using the
`memory` argument. This expects an integer number of megabytes:

```python
import modal

app = modal.App()

@app.function(memory=32768)
def my_function():
    # code here will have access to at least 32 GiB of RAM
    ...
```

## How much can I request?

For both CPU and memory, a maximum is enforced at Function or Sandbox creation time to
ensure your containers can be scheduled for execution. Requests exceeding the
maximum will be rejected with an
[`InvalidError`](/docs/reference/modal.exception#modalexceptioninvaliderror).

## Billing

For CPU and memory, you'll be charged based on whichever is higher: your request or actual usage.

Disk requests are billed by increasing the memory request at a 20:1 ratio. For example, requesting 500 GiB of disk will increase the memory request to 25 GiB, if it is not already set higher.

## Resource limits

### CPU limits

Modal containers have a default soft CPU limit that is set at 16 physical cores above the CPU request.
Given that the default CPU request is 0.125 cores, the default soft CPU limit is 16.125 cores.
Above this limit, the host will begin to throttle the CPU usage of the container.

You can alternatively set the CPU limit explicitly:

```python
cpu_request = 1.0
cpu_limit = 4.0
@app.function(cpu=(cpu_request, cpu_limit))
def f():
    ...
```

### Memory limits

Modal containers can have a hard memory limit which will 'Out of Memory' (OOM) kill
containers which attempt to exceed the limit. This functionality is useful when a process
has a serious memory leak. You can set the limit and have the container killed to avoid paying
for the leaked GBs of memory.

Specify this limit using the `memory` parameter on [`@app.function()`](/docs/reference/modal.App#function) or [`Sandbox.create()`](/docs/reference/modal.Sandbox#create):

```python
mem_request = 1024
mem_limit = 2048
@app.function(
    memory=(mem_request, mem_limit),
)
def f():
    ...
```

### Disk limits

Running Modal containers have access to many GBs of SSD disk, but the amount
of writes is limited by:

1. The size of the underlying worker's SSD disk capacity
2. A per-container disk quota that defaults to 512 GiB.

Hitting either limit will cause the container's disk writes to be rejected, which
typically manifests as an `OSError`.

Increased disk sizes can be requested with the `ephemeral_disk` parameter on [`@app.function()`](/docs/reference/modal.App#function) or [`Sandbox.create()`](/docs/reference/modal.Sandbox#create). The maximum
disk size is 3.0 TiB (3,145,728 MiB). Larger disks are intended to be used for [dataset processing](/docs/guide/dataset-ingestion).
