# MLflow Tracking - Team Onboarding

A practical guide for everyone working on TritonGen. By the end, you should
understand what MLflow gives us, how to run an experiment with tracking on, and
how to browse the results. No prior MLflow experience is required.

For implementation details, see the technical reference at
[`shared/tracking/README.md`](../../shared/tracking/README.md).

---

## 1. Why we use MLflow

We generate many Triton kernels across conditions (`none`, `G`, `C`, `G+C`),
kernel classes, dtypes, and seeds. The raw results are JSONL files in
`outputs/`. Those files are the source of truth, but they are hard to compare by
eye.

MLflow is a logbook and dashboard on top of those results. Every tracked run
records the settings we used and the numbers we got, then exposes them in a web
UI where we can filter, sort, and chart them.

Most important rule: MLflow is optional and additive. If it is off or not
installed, the scripts still run normally and write the same JSONL files. You
can ignore MLflow entirely and nothing breaks.

---

## 2. Core Concepts

| MLflow term | Plain meaning | In TritonGen |
| --- | --- | --- |
| Experiment | A folder of related runs | One per cluster, such as `tritongen_cluster1` or `tritongen_cluster2` |
| Run | One execution of a launcher | One `run_cluster1.py` or Modal invocation |
| Params | Fixed settings for that run | `condition`, `scale_tier`, `model_id`, CLI args as `arg.*` |
| Metrics | Numbers measured during the run | `compile_success`, `functional_success`, `max_abs_diff`, etc. |
| Tags | Labels used for filtering | `cluster`, `condition`, `scale_tier`, `backend`, `reportable`, plus provenance `git_commit` + `output_path` (auto) |

One thing to internalize: one MLflow run means one launch of a script. The
per-kernel results live inside that run as metrics. Do not confuse the MLflow
run with the `run_id` field on each result record; that field is a per-cell
experiment id.

We use separate metric namespaces so result types do not collide:

| Source | Metric prefix | Example |
| --- | --- | --- |
| Cluster 1 generation results | `gen.*` | `gen.compile_success` |
| Cluster 2 eval rows | `c2.*` | `c2.functional_success` |
| Cluster 3 eval rows | `c3.*` | `c3.functional_success` |
| Shared eval results | `eval.*` | `eval.functional_success`, `eval.max_abs_diff` |
| Analyzer cell summaries | `cell.*` | `cell.functional_success.G_C` |

---

## 3. First Run From Zero

Use this path the first time you touch MLflow in this repo. It avoids GPU,
Triton, model downloads, and cluster-specific setup.

### Step 1: Start in the repo root

Open a PowerShell terminal in the `TritonGen/` folder, then set `PYTHONPATH` so
the demo can import the local `shared` package:

```powershell
$env:PYTHONPATH = (Get-Location)
```

### Step 2: Write one demo MLflow run

Tracking turns on only when both gates are open:

1. `TRITONGEN_MLFLOW=1` is set.
2. The `mlflow` package is available to the Python process that is running the
   script.

This command uses `uv` to run the demo in a temporary Python 3.12 environment
with MLflow installed:

```powershell
$env:TRITONGEN_MLFLOW = "1"
$env:MLFLOW_TRACKING_URI = "file:./mlruns"
uv run --no-project --python 3.12 --with "mlflow>=2.10,<3.0" python _mlflow_demo.py
```

Expected terminal output:

```text
Demo MLflow run written if TRITONGEN_MLFLOW=1 and mlflow is installed.
```

Expected filesystem result:

```text
mlruns/
```

That folder is local, generated, and gitignored. It is where MLflow stores the
runs that the dashboard reads.

### Step 3: Open the dashboard

In a second terminal, from the same `TritonGen/` folder:

```powershell
uvx --python 3.12 --from "mlflow>=2.10,<3.0" mlflow ui --backend-store-uri "file:./mlruns" --port 5000
```

Then open:

```text
http://127.0.0.1:5000
```

Expected UI result:

1. The left sidebar shows an experiment such as `tritongen_cluster1`.
2. The run table has a row for the demo launch.
3. The run detail page shows params such as `condition=demo`, tags such as
   `cluster=cluster1`, and metrics such as `gen.compile_success`.

Important: the dashboard is only a viewer. It does not need to be running while
an experiment logs results.

---

## 4. Browse Results

Open the dashboard at:

```text
http://127.0.0.1:5000
```

If it is not running, start it from the `TritonGen/` folder:

```powershell
uvx --python 3.12 --from "mlflow>=2.10,<3.0" mlflow ui --backend-store-uri "file:./mlruns" --port 5000
```

What to look for:

1. Left sidebar: experiments such as `tritongen_cluster1` and
   `tritongen_cluster2`.
2. Runs table: each row is one launcher execution. Use the "Columns" button to
   show or hide params, metrics, and tags.
3. Run detail page:
   - Parameters: settings such as condition, scale tier, model, and CLI args.
   - Tags: labels such as `cluster`, `backend`, and `reportable`.
   - Metrics: numbers logged during the run. Click a metric to chart it.

The dashboard only reads `./mlruns`. It does not need to be running while you
log an experiment.

---

## 5. Run Real Experiments

### Option A: Real Cluster 1 smoke run with tracking

Use this after the demo works. Unlike `_mlflow_demo.py`, this enters the real
Cluster 1 pipeline and may depend on the normal project/runtime requirements.

```powershell
# from TritonGen/
$env:TRITONGEN_MLFLOW = "1"
python cluster1/experiments/run_cluster1.py --condition baseline --kernel-class elementwise --n 2 --output outputs/cluster1/smoke.jsonl
```

Expected result:

```text
outputs/cluster1/smoke.jsonl
mlruns/
```

With `TRITONGEN_MLFLOW` unset, the same command writes the same JSONL but does
not log to MLflow.

### Option B: Install MLflow into a reusable environment

Install note: use a Python 3.12 environment for MLflow. On Python 3.14, the
current `mlflow>=2.10,<3.0` pin fails because it depends on older PyArrow builds
that do not provide Python 3.14 wheels.

```powershell
uv venv --python 3.12 .venv-mlflow
.\.venv-mlflow\Scripts\Activate.ps1
uv pip install "mlflow>=2.10,<3.0"
```

If you install the project package itself, the tracking extra is also available:

```powershell
uv pip install -e ".[tracking]"
```

---

## 6. How It Works Internally

All MLflow integration code lives in `shared/tracking/`. Cluster code calls the
tracking package; it does not import `mlflow` directly.

There are three main seams:

| Seam | Where | What it does |
| --- | --- | --- |
| Run boundary | Launchers such as `run_cluster1.py` | Opens one optional MLflow run and records params/tags |
| Per-result metrics | JSONL writers | Logs metrics after writing each JSONL line |
| Analyzer summaries | Factorial analysis | Logs aggregate `cell.*` metrics and reportability tags |

The JSONL write happens first. If MLflow is disabled, missing, or errors out,
tracking becomes a no-op and the experiment still runs.

---

## 7. Modal

Modal runs the GPU work; your local process does the logging.

The Modal launchers call remote GPU functions and receive results back on your
machine. The local process then writes JSONL and logs to MLflow, so:

- No MLflow package is required inside the Modal container.
- No MLflow credentials are shipped to the cloud.
- The local `file:./mlruns` store stays on your machine.

The Modal launchers wrap their local orchestration in `tracking.run_context`.
Per-result logging still happens locally when rows are written.

---

## 8. FAQ

**I ran something but nothing appeared in the UI.**

Check the two gates:

```powershell
echo $env:TRITONGEN_MLFLOW
python -c "import importlib.util; print(importlib.util.find_spec('mlflow') is not None)"
```

The env var should be `1`, and the Python check should print `True`.

Also check that the dashboard is reading the same store you wrote to:

```powershell
echo $env:MLFLOW_TRACKING_URI
```

For the default local setup, use `file:./mlruns` or leave it unset and start the
UI with `--backend-store-uri "file:./mlruns"` from the repo root.

**The demo worked but the real Cluster 1 command failed.**

That means MLflow is probably fine. The demo only tests tracking. The real
launcher still needs the normal Cluster 1 runtime requirements, model access,
and any compute setup required by that command.

**Do I need to keep the dashboard running while the experiment runs?**

No. Logging writes to `./mlruns`; the dashboard is only a viewer.

**Are MLflow runs committed to git?**

No. `mlruns/` and `outputs/` are gitignored. JSONL files remain the source of
truth; MLflow is a local mirror for browsing and comparison.

**Can I compare smoke, development, and paper runs together?**

No. Use the `scale_tier` and `reportable` tags. Smoke and development runs are
for iteration and should not be mixed into paper-scale conclusions.
