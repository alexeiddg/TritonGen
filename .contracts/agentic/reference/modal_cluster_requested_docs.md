# Images

This guide walks you through how to define a Modal Image, the environment your Modal code runs in.

The typical flow for defining an Image in Modal is
[method chaining](https://jugad2.blogspot.com/2016/02/examples-of-method-chaining-in-python.html)
starting from a base Image, like this:

```python
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_pip_install("torch<3")
    .env({"HALT_AND_CATCH_FIRE": "0"})
    .run_commands("git clone https://github.com/modal-labs/agi && echo 'ready to go!'")
)
```

If you have your own container image definitions, like a Dockerfile or a registry link, you can use those too!
See [this guide](/docs/guide/existing-images).

This page is a high-level guide to using Modal Images.
For reference documentation on the `modal.Image` object, see
[this page](/docs/reference/modal.Image).

## What are Images?

Your code on Modal runs in _containers_. Containers are like light-weight
virtual machines -- container engines use
[operating system tricks](https://earthly.dev/blog/chroot/) to isolate programs
from each other ("containing" them), making them work as though they were
running on their own hardware with their own filesystem. This makes execution
environments more reproducible, for example by preventing accidental
cross-contamination of environments on the same machine. For added security,
Modal runs containers using the sandboxed
[gVisor container runtime](https://cloud.google.com/blog/products/identity-security/open-sourcing-gvisor-a-sandboxed-container-runtime).

Containers are started up from a stored "snapshot" of their filesystem state
called an _image_. Producing the image for a container is called _building_ the
image.

By default, Modal Functions and Sandboxes run in a
[Debian Linux](https://en.wikipedia.org/wiki/Debian) container with a basic
Python installation of the same minor version `v3.x` as your local Python
interpreter.

To make your Apps and Functions useful, you will probably need some third party system packages
or Python libraries. Modal provides a number of options to customize your container images at
different levels of abstraction and granularity, from high-level convenience
methods like `pip_install` through wrappers of core container image build
features like `RUN` and `ENV`. We'll cover each of these in this guide,
along with tips and tricks for building Images effectively when using each tool.

## Add Python packages

The simplest and most common Image modification is to add a third party
Python package, like [`pandas`](https://pandas.pydata.org/).

You can add Python packages to the environment by passing all the packages you
need to the [`Image.uv_pip_install`](/docs/reference/modal.Image#uv_pip_install) method,
which installs packages with [`uv`](https://docs.astral.sh/uv/):

```python
import modal

datascience_image = (
    modal.Image.debian_slim()
    .uv_pip_install("pandas==2.2.0", "numpy")
)


@app.function(image=datascience_image)
def my_function():
    import pandas as pd
    import numpy as np

    df = pd.DataFrame()
    ...
```

You can include
[Python dependency version specifiers](https://peps.python.org/pep-0508/),
like `"torch<3"`, in the arguments. But we recommend pinning dependencies
tightly, like `"torch==2.8.0"`, to improve the reproducibility and robustness
of your builds.

If you run into any issues with
[`Image.uv_pip_install`](/docs/reference/modal.Image#uv_pip_install), then
you can fallback to [`Image.pip_install`](/docs/reference/modal.Image#pip_install) which
uses standard [`pip`](https://pip.pypa.io/en/stable/user_guide/):

```python
datascience_image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("pandas==2.2.0", "numpy")
)
```

Note that because you can define a different environment for each and every
function if you so choose, you don't need to worry about virtual
environment management. Containers make for much better separation of concerns!

If you want to run a specific version of Python remotely rather than just
matching the one you're running locally, provide the `python_version` as a
string when constructing the base image, like we did above.

## Add local files with `add_local_dir` and `add_local_file`

Sometimes your containers need a dependency that's not available on the Internet,
like configuration files or code on your laptop.

To forward files from your local system use the
`image.add_local_dir` and `image.add_local_file` Image methods.

```python
image = modal.Image.debian_slim().add_local_dir("/user/erikbern/.aws", remote_path="/root/.aws")
```

By default, these files are added to your container as it starts up rather than introducing
a new Image layer. This means that the redeployment after making changes is really quick, but
also means you can't run additional build steps after. You can specify a `copy=True` argument
to the `add_local_` methods to instead force the files to be included in the built Image.

### Add local Python code with `add_local_python_source`

You can add Python code that's importable locally to your container
by providing the module name to
[`Image.add_local_python_source`](/docs/reference/modal.Image#add_local_python_source).

```python
image_with_module = modal.Image.debian_slim().add_local_python_source("local_module")

@app.function(image=image_with_module)
def f():
    import local_module

    local_module.do_stuff()
```

The difference from `add_local_dir` is that `add_local_python_source` takes module names as arguments
instead of a file system path and looks up the local package's or module's location via Python's importing
mechanism. The files are then added to directories that make them importable in containers in the
same way as they are locally.

This is intended for pure Python auxiliary modules that are part of your project and that your code imports.
Third party packages should be installed via
[`Image.uv_pip_install`](/docs/reference/modal.Image#uv_pip_install) or similar.

### What if I have different Python packages locally and remotely?

You might want to use packages inside your Modal code that you don't have on
your local computer. In the example above, we build a container that uses
`pandas`. But if we don't have `pandas` locally, on the computer building the
Modal App, we can't put `import pandas` at the top of the script, since it would
cause an `ImportError`.

The easiest solution to this is to put `import pandas` in the function body
instead, as you can see above. This means that `pandas` is only imported when
running inside the remote Modal container, which has `pandas` installed.

Be careful about what you return from Modal Functions that have different
packages installed than the ones you have locally! Modal Functions return Python
objects, like `pandas.DataFrame`s, and if your local machine doesn't have
`pandas` installed, it won't be able to handle a `pandas` object (the error
message you see will mention
[serialization](https://hazelcast.com/glossary/serialization/)/[deserialization](https://hazelcast.com/glossary/deserialization/)).

If you have a lot of Functions and a lot of Python packages, you might want to
keep the imports in the global scope so that every function can use the same
imports. In that case, you can use the
[`Image.imports`](/docs/reference/modal.Image#imports) context manager:

```python
pandas_image = modal.Image.debian_slim().pip_install("pandas", "numpy")


with pandas_image.imports():
    import pandas as pd
    import numpy as np


@app.function(image=pandas_image)
def my_function():
    df = pd.DataFrame()
    ...
```

Because these imports happen before a new container processes its first input,
you can combine this context manager with [Memory Snapshots](/docs/guide/memory-snapshots)
to improve [cold start performance](/docs/guide/cold-start#share-initialization-work-across-cold-starts-with-memory-snapshots)
for Functions that frequently scale up.

## Install system packages with `.apt_install`

You can install Linux packages with the [`apt` package manager](https://www.debian.org/doc/manuals/apt-guide/index.en.html)
using [`Image.apt_install`](/docs/reference/modal.Image#apt_install):

```python
image = modal.Image.debian_slim().apt_install("git", "curl")
```

## Set environment variables with `.env`

You can change the environment variables that your code sees
(in, e.g., [`os.environ`](https://docs.python.org/3/library/os.html#os.environ))
by passing a dictionary to [`Image.env`](/docs/reference/modal.Image#env):

```python
image = modal.Image.debian_slim().env({"PORT": "6443"})
```

Environment variable names and values must be strings.

## Run shell commands with `.run_commands`

You can supply shell commands that should be executed when building the
Image to [`Image.run_commands`](/docs/reference/modal.Image#run_commands):

```python
image_with_repo = (
    modal.Image.debian_slim().apt_install("git").run_commands(
        "git clone https://github.com/modal-labs/gpu-glossary"
    )
)
```

## Run a Python function during your build with `.run_function`

You can run Python code as a build step using the
[`Image.run_function`](/docs/reference/modal.Image#run_function) method.

For example, you can use this to download model parameters from Hugging Face into
your Image:

```python
import os

def download_models() -> None:
    import diffusers

    model_name = "segmind/small-sd"
    pipe = diffusers.StableDiffusionPipeline.from_pretrained(
        model_name, use_auth_token=os.environ["HF_TOKEN"]
    )

hf_cache = modal.Volume.from_name("hf-cache")

image = (
    modal.Image.debian_slim()
        .pip_install("diffusers[torch]", "transformers", "ftfy", "accelerate")
        .run_function(
            download_models,
            secrets=[modal.Secret.from_name("huggingface-secret")],
            volumes={"/root/.cache/huggingface": hf_cache},
        )
)
```

For details on storing model weights on Modal, see
[this guide](/docs/guide/model-weights).

Essentially, this is equivalent to running a Modal Function and snapshotting the
resulting filesystem as a new Image. Any kwargs accepted by [`@app.function`](/docs/reference/modal.App#function)
([`Volume`s](/docs/guide/volumes), [`Secret`s](/docs/guide/secrets), specifications of
resources like [GPUs](/docs/guide/gpu)) can be supplied here.

Whenever you change other features of your Image, like the base Image or the
version of a Python package, the Image will automatically be rebuilt the next
time it is used. This is a bit more complicated when changing the contents of
functions. See the
[reference documentation](/docs/reference/modal.Image#run_function) for details.

## Attach GPUs during setup

If a step in the setup of your Image should be run on an instance with
a GPU (e.g., so that a package can query the GPU to set compilation flags), pass the
desired GPU type when defining that step:

```python
image = (
    modal.Image.debian_slim()
    .pip_install("bitsandbytes", gpu="H100")
)
```

## Use `mamba` instead of `pip` with `micromamba_install`

`pip` installs Python packages, but some Python workloads require the
coordinated installation of system packages as well. The `mamba` package manager
can install both. Modal provides a pre-built
[Micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html)
base image that makes it easy to work with `micromamba`:

```python
app = modal.App("bayes-pgm")

numpyro_pymc_image = (
    modal.Image.micromamba()
    .micromamba_install("pymc==5.10.4", "numpyro==0.13.2", channels=["conda-forge"])
)


@app.function(image=numpyro_pymc_image)
def sample():
    import pymc as pm
    import numpyro as np

    print(f"Running on PyMC v{pm.__version__} with JAX/numpyro v{np.__version__} backend")
    ...
```

## Image caching and rebuilds

Modal uses the definition of an Image to determine whether it needs to be
rebuilt. If the definition hasn't changed since the last time you ran or
deployed your App, the previous version will be pulled from the cache.

Images are cached per layer (i.e., per `Image` method call), and breaking
the cache on a single layer will cause cascading rebuilds for all subsequent
layers. You can shorten iteration cycles by defining frequently-changing
layers last so that the cached version of all other layers can be used.

In some cases, you may want to force an Image to rebuild, even if the
definition hasn't changed. You can do this by adding the `force_build=True`
argument to any of the Image building methods.

```python
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install("slack-sdk", force_build=True)
    .run_commands("echo hi")
)
```

As in other cases where a layer's definition changes, both the `pip_install` and
`run_commands` layers will rebuild, but the `apt_install` will not. Remember to
remove `force_build=True` after you've rebuilt the Image, or it will
rebuild every time you run your code.

Alternatively, you can set the `MODAL_FORCE_BUILD` environment variable (e.g.
`MODAL_FORCE_BUILD=1 modal run ...`) to rebuild all images attached to your App.
But note that when you rebuild a base layer, the cache will be invalidated for _all_
Images that depend on it, and they will rebuild the next time you run or deploy
any App that uses that base. If you're debugging an issue with your Image, a better
option might be using `MODAL_IGNORE_CACHE=1`. This will rebuild the Image from the
top without breaking the Image cache or affecting subsequent builds.

## Image builder updates

Because changes to base images will cause cascading rebuilds, Modal is
conservative about updating the base definitions that we provide. But many
things are baked into these definitions, like the specific versions of the Image
OS, the included Python, and the Modal client dependencies.

We provide a separate mechanism for keeping base images up-to-date without
causing unpredictable rebuilds: the "Image Builder Version". This is a workspace
level-configuration that will be used for every Image built in your workspace.
We release a new Image Builder Version every few months but allow you to update
your workspace's configuration when convenient. After updating, your next
deployment will take longer, because your Images will rebuild. You may also
encounter problems, especially if your Image definition does not pin the version
of the third-party libraries that it installs (as your new Image will get the
latest version of these libraries, which may contain breaking changes).

You can set the Image Builder Version for your workspace by going to your
[workspace settings](/settings/image-config). This page also documents the
important updates in each version.

---

# Request timeouts

Web Function requests should complete quickly, ideally within a
few seconds. All Web Function types
([`modal.fastapi_endpoint`](/docs/reference/modal.fastapi_endpoint),
[`modal.asgi_app`](/docs/reference/modal.asgi_app),
[`modal.wsgi_app`](/docs/reference/modal.wsgi_app),
and [`modal.web_server`](/docs/reference/modal.web_server))
have a maximum HTTP request timeout of 150 seconds enforced. However, the
underlying Modal Function can have a longer [timeout](/docs/guide/timeouts).

In case the Function takes more than 150 seconds to complete, an HTTP status 303
redirect response is returned pointing at the original URL with a special query
parameter linking it that request. This is the _result URL_ for your function.
Most web browsers allow for up to 20 such redirects, effectively allowing up to
50 minutes (20 \* 150 s) for Web Functions before the request times out.

(**Note:** This does not work with requests that require
[CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS), since the
response will not have been returned from your code in time for the server to
populate CORS headers.)

Some libraries and tools might require you to add a flag or option in order to
follow redirects automatically, e.g. `curl -L ...` or `http --follow ...`.

The _result URL_ can be reloaded without triggering a new request. It will block
until the request completes.

(**Note:** As of March 2025, the Python standard library's `urllib` module has the
maximum number of redirects to any single URL set to 4 by default ([source](https://github.com/python/cpython/blob/main/Lib/urllib/request.py)), which would limit the total timeout to 12.5 minutes (5 \* 150 s = 750 s) unless this setting is overridden.)

## Polling solutions

Sometimes it can be useful to be able to poll for results rather than wait for a
long running HTTP request. The easiest way to do this is to have your web
endpoint spawn a `modal.Function` call and return the function call id that
another endpoint can use to poll the submitted function's status. Here is an
example:

```python
import fastapi

import modal


image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App(image=image)

web_app = fastapi.FastAPI()


@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app


@app.function()
def slow_operation():
    ...


@web_app.post("/accept")
async def accept_job(request: fastapi.Request):
    call = slow_operation.spawn()
    return {"call_id": call.object_id}


@web_app.get("/result/{call_id}")
async def poll_results(call_id: str):
    function_call = modal.FunctionCall.from_id(call_id)
    try:
        return function_call.get(timeout=0)
    except TimeoutError:
        http_accepted_code = 202
        return fastapi.responses.JSONResponse({}, status_code=http_accepted_code)
```

[_Document OCR Web App_](/docs/examples/doc_ocr_webapp) is an example that uses
this pattern.


---

# Filesystem Access

There are multiple options for uploading files to a Sandbox and accessing them
from outside the Sandbox.

## Filesystem API

<Callout variant="beta">

This API brings significant reliability improvements compared to the previous Sandbox filesystem API, which was available in releases prior to v1.4.0 and is now deprecated.

</Callout>

The most convenient way to pass data in and out of the Sandbox during
execution is to use our filesystem API:

<CodeTabs>
  {#snippet python()}

```python
import modal

app = modal.App.lookup("sandbox-fs-demo", create_if_missing=True)

sb = modal.Sandbox.create(app=app)

# Write text to a file in the Sandbox.
sb.filesystem.write_text("Hello World!\n", "/tmp/test.txt")

# Read the file back from the Sandbox into a string.
contents = sb.filesystem.read_text("/tmp/test.txt")
print(contents)

sb.terminate()
sb.detach()
```

{/snippet}
{#snippet javascript()}

```javascript notest
import { ModalClient } from "modal";

const modal = new ModalClient();
const app = await modal.apps.fromName("sandbox-fs-demo", {
  createIfMissing: true,
});
const image = modal.images.fromRegistry("python:3.13-slim");

const sb = await modal.sandboxes.create(app, image);

// Write text to a file in the Sandbox.
await sb.filesystem.writeText("Hello World!\n", "/tmp/test.txt");

// Read the file back from the Sandbox into a string.
const contents = await sb.filesystem.readText("/tmp/test.txt");
console.log(contents);

await sb.terminate();
```

{/snippet}
{#snippet go()}

```go notest
package main

import (
	"context"
	"fmt"

	modal "github.com/modal-labs/modal-client/go"
)

func main() {
	ctx := context.Background()
	mc, _ := modal.NewClient()

	app, _ := mc.Apps.FromName(ctx, "sandbox-fs-demo", &modal.AppFromNameParams{
		CreateIfMissing: true,
	})
	image := mc.Images.FromRegistry("python:3.13-slim", nil)

	sb, _ := mc.Sandboxes.Create(ctx, app, image, nil)
	defer sb.Terminate(ctx, nil)

	fs := sb.Filesystem()

	// Write text to a file in the Sandbox.
	fs.WriteText(ctx, "Hello World!\n", "/tmp/test.txt", nil)

	// Read the file back from the Sandbox into a string.
	contents, _ := fs.ReadText(ctx, "/tmp/test.txt", nil)
	fmt.Println(contents)
}
```

{/snippet}
</CodeTabs>

It has convenience APIs for streaming file copies in both directions:

<CodeTabs>
  {#snippet python()}

```python
from pathlib import Path
import modal

# Write a local file.
with open("local-file.txt", "w") as f:
    f.write("Hello World!\n")

app = modal.App.lookup("sandbox-fs-demo", create_if_missing=True)

sb = modal.Sandbox.create(app=app)

# Copy the local file into the Sandbox.
sb.filesystem.copy_from_local("local-file.txt", "/tmp/file-in-sandbox.txt")

# Copy it back to the local filesystem.
sb.filesystem.copy_to_local("/tmp/file-in-sandbox.txt", "local-file-copy.txt")

print(Path("local-file-copy.txt").read_text())

sb.terminate()
sb.detach()
```

{/snippet}
{#snippet javascript()}

```javascript notest
import { readFile, writeFile } from "node:fs/promises";

const sb = await modal.sandboxes.create(app, image);

// Write a local file.
await writeFile("local-file.txt", "Hello World!\n", "utf-8");

// Copy the local file into the Sandbox.
await sb.filesystem.copyFromLocal("local-file.txt", "/tmp/file-in-sandbox.txt");

// Copy it back to the local filesystem.
await sb.filesystem.copyToLocal(
  "/tmp/file-in-sandbox.txt",
  "local-file-copy.txt",
);

console.log(await readFile("local-file-copy.txt", "utf-8"));

await sb.terminate();
```

{/snippet}
{#snippet go()}

```go notest
sb, _ := mc.Sandboxes.Create(ctx, app, image, nil)
defer sb.Terminate(ctx, nil)

fs := sb.Filesystem()

// Write a local file.
os.WriteFile("local-file.txt", []byte("Hello World!\n"), 0o644)

// Copy the local file into the Sandbox.
fs.CopyFromLocal(ctx, "local-file.txt", "/tmp/file-in-sandbox.txt", nil)

// Copy it back to the local filesystem.
fs.CopyToLocal(ctx, "/tmp/file-in-sandbox.txt", "local-file-copy.txt", nil)

data, _ := os.ReadFile("local-file-copy.txt")
fmt.Println(string(data))
```

{/snippet}
</CodeTabs>

It also offers APIs for inspecting and managing files:

<CodeTabs>
  {#snippet python()}

```python
import modal

app = modal.App.lookup("sandbox-fs-demo", create_if_missing=True)

sb = modal.Sandbox.create(app=app)

# Set up a structured project.
sb.filesystem.make_directory("/tmp/project/results")

# Let the Sandbox do some work and write outputs to files.
sb.filesystem.write_text("42\n", "/tmp/project/results/answer.txt")
sb.filesystem.write_text("debug info\n", "/tmp/project/results/debug.log")

# Inspect what was produced.
for entry in sb.filesystem.list_files("/tmp/project/results"):
    print(entry.name, entry.type.value, entry.size)

# Check that the result file has content before downloading it.
info = sb.filesystem.stat("/tmp/project/results/answer.txt")
if info.size > 0:
    answer = sb.filesystem.read_text("/tmp/project/results/answer.txt")
    print(answer)

# Clean up the whole project.
sb.filesystem.remove("/tmp/project", recursive=True)

sb.terminate()
sb.detach()
```

{/snippet}
{#snippet javascript()}

```javascript notest
const sb = await modal.sandboxes.create(app, image);

// Set up a structured project.
await sb.filesystem.makeDirectory("/tmp/project/results");

// Let the Sandbox do some work and write outputs to files.
await sb.filesystem.writeText("42\n", "/tmp/project/results/answer.txt");
await sb.filesystem.writeText("debug info\n", "/tmp/project/results/debug.log");

// Inspect what was produced.
const entries = await sb.filesystem.listFiles("/tmp/project/results");
for (const entry of entries) {
  console.log(entry.name, entry.type, entry.size);
}

// Check that the result file has content before downloading it.
const info = await sb.filesystem.stat("/tmp/project/results/answer.txt");
if (info.size > 0) {
  const answer = await sb.filesystem.readText(
    "/tmp/project/results/answer.txt",
  );
  console.log(answer);
}

// Clean up the whole project.
await sb.filesystem.remove("/tmp/project", { recursive: true });

await sb.terminate();
```

{/snippet}
{#snippet go()}

```go notest
sb, _ := mc.Sandboxes.Create(ctx, app, image, nil)
defer sb.Terminate(ctx, nil)

fs := sb.Filesystem()

// Set up a structured project.
fs.MakeDirectory(ctx, "/tmp/project/results", nil)

// Let the Sandbox do some work and write outputs to files.
fs.WriteText(ctx, "42\n", "/tmp/project/results/answer.txt", nil)
fs.WriteText(ctx, "debug info\n", "/tmp/project/results/debug.log", nil)

// Inspect what was produced.
entries, _ := fs.ListFiles(ctx, "/tmp/project/results", nil)
for _, entry := range entries {
	fmt.Println(entry.Name, entry.Type, entry.Size)
}

// Check that the result file has content before downloading it.
info, _ := fs.Stat(ctx, "/tmp/project/results/answer.txt", nil)
if info.Size > 0 {
	answer, _ := fs.ReadText(ctx, "/tmp/project/results/answer.txt", nil)
	fmt.Println(answer)
}

// Clean up the whole project.
fs.Remove(ctx, "/tmp/project", &modal.SandboxFilesystemRemoveParams{Recursive: true})
```

{/snippet}
</CodeTabs>

These APIs may be used to read files of up to 5GB and write files of any size.

However, if you have a large dataset that you want to use repeatedly from many sandboxes,
consider [using Volumes](#using-volumes).

## Using Volumes

It's possible to use Modal [Volume](/docs/reference/modal.Volume)s or
[CloudBucketMount](/docs/guide/cloud-bucket-mounts)s with Sandboxes.

Volumes and CloudBucketMounts allow you to upload data once and access that
data efficiently from many sandboxes.

To access a Volume from a Sandbox, you can use the `volumes` parameter of `Sandbox.create`:

```python notest
# Find or create a Volume with the name "my-volume".
vol = modal.Volume.from_name("my-volume", create_if_missing=True)
sb = modal.Sandbox.create(
    volumes={"/cache": vol},
    app=my_app,
)
# Read a file in the Volume.
p = sb.exec("bash", "-c", "cat /cache/some-file.txt")
print(p.stdout.read())
p.wait()

# Write a file to the Volume.
p = sb.exec("bash", "-c", "echo foo > /cache/a.txt")
p.wait()
sb.terminate(wait=True)
sb.detach()

# Access the Volume file from outside the Sandbox.
for data in vol.read_file("a.txt"):
    print(data)
```

File syncing behavior differs between Volumes and CloudBucketMounts. For
Volumes, files are only synced back to the Volume when the Sandbox terminates.
For CloudBucketMounts, files are synced automatically.

### Committing Volume changes with `sync` (v2 only)

For [Volumes v2](/docs/guide/volumes#volumes-v2-overview), you can explicitly
commit changes at any point during Sandbox execution by running the `sync`
command on the mountpoint. This persists all data and metadata changes to the
Volume's storage without waiting for the Sandbox to terminate:

```python notest
sb = modal.Sandbox.create(
    volumes={"/data": modal.Volume.from_name("my-v2-volume")},
    app=my_app,
)

# Write files to the volume
sb.exec("bash", "-c", "echo 'hello' > /data/output.txt").wait()

# Commit changes immediately
p = sb.exec("sync", "/data")
p.wait()
if p.returncode != 0:
    raise Exception(f"sync failed with exit code {p.returncode}")

# Changes are now persisted and visible to other containers
sb.terminate()
sb.detach()
```

This is particularly useful for long-running Sandboxes where you want to
persist intermediate results, or when you need changes to be visible to other
containers before the Sandbox terminates.

## Adding files to an Image

In some cases, you may want to [add a file to an Image itself](/docs/guide/images#add-local-files-with-add_local_dir-and-add_local_file).
This is useful if the file will be used by many Sandboxes, or if you
want to access that file from the Sandbox's entrypoint command.

This can be done using the
[`add_local_file`](/docs/reference/modal.Image#add_local_file) and
[`add_local_dir`](/docs/reference/modal.Image#add_local_dir) methods on the
[`Image`](/docs/reference/modal.Image) class:

```python notest
# Eagerly build the image - otherwise the Image will lazily build when the
# Sandbox is created.
image = (
    modal.Image.debian_slim()
    .add_local_dir(
        local_path="/home/user/my_dir",
        remote_path="/app",
    )
    .build(my_app)
)

sb = modal.Sandbox.create(app=my_app, image=image)
p = sb.exec("ls", "/app")
print(p.stdout.read())
p.wait()
sb.detach()
```

<!-- TODO(WRK-956) -->
<!-- ## File Watching

You can watch files or directories for changes using [`watch`](/docs/reference/modal.Sandbox#watch), which is conceptually similar to [`fsnotify`](https://pkg.go.dev/github.com/fsnotify/fsnotify).

```python notest
from modal.file_io import FileWatchEventType

async def watch(sb: modal.Sandbox):
    event_stream = sb.watch.aio(
        "/watch",
        recursive=True,
        filter=[FileWatchEventType.Create, FileWatchEventType.Modify],
    )
    async for event in event_stream:
        print(event)

async def main():
    app = modal.App.lookup("sandbox-file-watch", create_if_missing=True)
    sb = await modal.Sandbox.create.aio(app=app)
    asyncio.create_task(watch(sb))

    await sb.mkdir.aio("/watch")
    for i in range(10):
        async with await sb.open.aio(f"/watch/bar-{i}.txt", "w") as f:
            await f.write.aio(f"hello-{i}")
``` -->

---

# Preemption

All Modal Functions are subject to preemption by default.
If a preemption event interrupts a running Function, Modal will gracefully terminate
the Function and restart it on the same input.

Preemptions are rare, but it is always possible that your Function is
interrupted. Long-running Functions such as model training Functions should take
particular care to tolerate interruptions, as likelihood of interruption increases
with Function run duration.

## Preparing for interruptions

Design your applications to be fault and preemption tolerant. Modal will send an
interrupt signal to your container when preemption occurs. This will cause the
Function's [exit handler](/docs/guide/lifecycle-functions#exit) to run, which
can perform any cleanup within its grace period.

Other best practices for handling preemptions include:

- Divide long-running operations into small tasks or use checkpoints so that you
  can save your work frequently. See our [long training example](/docs/examples/long-training)
  for a practical demonstration of checkpointing.
- Ensure preemptible operations are safely retryable (ie. idempotent).

## Non-preemptible Functions

If you require Functions that are guaranteed not to be preempted, you may set the `nonpreemptible`
parameter (available starting in client version v1.2.3) to `True` in the `@app.function()` or `@app.cls()` decorator.
Note that a 3x multiplier will be applied to the [list price](https://modal.com/pricing) for CPU and Memory usage when
`nonpreemptible` is set to `True`.

**Note:** The `nonpreemptible` parameter is not supported for GPU Functions.

## Non-preemptible Sandboxes

Modal Sandboxes are not subject to preemption, except in the case where a `gpu`
requirement is specified. This is because of availability and scheduling latency constraints.

---

# Failures and retries

Failure is part of life. Sometimes you just have to retry. This guide page documents how to do this on Modal.

For reference documentation on the `modal.Retries` object, see [this page](/docs/reference/modal.Retries).

## Automatically recover from flakes with `retries`

You can configure Modal to automatically retry Function failures if you set the
`retries` option when declaring your Function:

```python
@app.function(retries=3)
def my_flaky_function():
    pass
```

The basic configuration shown provides a fixed 1s delay between retry attempts.
For fine-grained control over retry delays, including exponential backoff
configuration, use [`modal.Retries`](/docs/reference/modal.Retries).

## Handle failures in `Function.map`

By default, failures are propagated back to the caller.
To treat exceptions like successful results and aggregate them in the results list instead,
pass in [`return_exceptions=True`](/docs/guide/scale#exceptions).

When used with [`Function.map()`](/docs/guide/scale#parallel-execution-of-inputs),
each input is retried independently.

## Container crashes

If a `modal.Function` container crashes (either on start-up, e.g. while handling imports in global scope, or during execution, e.g. an out-of-memory error),
Modal will reschedule the container and any work it was currently assigned.

For [ephemeral apps](/docs/guide/apps#ephemeral-apps), container crashes will be retried until a failure rate is exceeded,
after which all pending inputs will be failed and the exception will be propagated to the caller.

For [deployed apps](/docs/guide/apps#deployed-apps), container crashes will be retried indefinitely, so as to not disrupt service.
Modal will instead apply a crash-loop backoff and the rate of new container creation for the Function will be slowed down.
Crash-looping containers are displayed in the [App dashboard](/apps).

---
