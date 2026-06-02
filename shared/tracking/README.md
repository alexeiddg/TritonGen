# `shared/tracking/` — optional MLflow experiment tracking

This is the **only** place in TritonGen that imports `mlflow`. Clusters and the
analyzer call into this package; they never touch MLflow directly. Tracking is
**additive and optional** — with it disabled, every existing run and test
behaves exactly as before.

---

## 1. What each piece is for

| Piece | What it is | Why it exists |
|---|---|---|
| **MLflow** | An experiment-tracking library. It records each run's *params* (config), *metrics* (numbers), *tags* (labels) and *artifacts* (files), and ships a web dashboard to compare runs. | Gives us a searchable, visual history of experiments on top of the raw JSONL — without changing how the pipeline produces results. |
| **`config.py`** | Reads the env vars + `shared/configs/tracking.yaml` into a frozen `TrackingConfig`. No `mlflow` import. | Decides **where** to log (tracking URI) and **which experiment** a run belongs to. One place for the "where". |
| **`mapping.py`** | Pure functions turning `RunConfig` / `EvalResult` / `GenerationResult` / `CellSummary` into params/metrics/tags. No `mlflow` import. | Holds **what** we track. Pure = trivially testable, and reusable from any caller. |
| **`client.py`** | The only `import mlflow` site. No-op-safe `run_context` + `log_*`. | The single integration point. If `mlflow` is missing or the flag is off, everything here is a silent no-op; logging errors are swallowed (warn, never raise) so tracking can never break a run. |
| **`__init__.py`** | Re-exports the public API. | One import surface: `from shared import tracking`. |
| **`shared/configs/tracking.yaml`** | Non-secret defaults (tracking URI, experiment names). | Config you can read/edit without touching code. **No secrets here** — those come from env vars only. |
| **`mlruns/`** | The local store MLflow writes to (gitignored). | Where the runs physically live on disk. The browser/dashboard reads from it. |

**Read path:** a launcher imports `shared.tracking`, calls `run_context(...)` →
`config.py` decides *where*, `mapping.py` decides *what*, `client.py` talks to
MLflow.

### Metric namespaces (disjoint by record type)

So the two write seams never collide inside one run:

| Record | Prefix |
|---|---|
| `EvalResult` | `eval.*` |
| `GenerationResult` (Cluster 1) | `gen.*` |
| `CellSummary` (analyzer) | `cell.*` |

---

## 2. The two gates (why nothing breaks)

Tracking activates **only when both** are true:

1. environment flag `TRITONGEN_MLFLOW=1`, **and**
2. the optional `mlflow` package is installed.

If either is off, every function here is a silent no-op and `run_context(...)`
yields `None`. That is the safety guarantee: a normal `pip install` and a normal
run never pull MLflow and never behave differently.

---

## 3. What `uv` / `uvx` are for

- **`uv`** is a fast Python package manager (an `pip` + `venv` replacement).
  `uv pip install X` installs into the current environment.
- **`uvx`** runs a Python **command-line tool in a throwaway environment without
  installing it permanently** (like `pipx run`). `uvx mlflow ui` downloads
  `mlflow` into a cache, runs the dashboard, and leaves your project env clean.

**Important limit — `uvx` helps with viewing, not logging.** There are two sides:

| Side | What runs `mlflow` | Needs a real install? |
|---|---|---|
| **Logging** (the pipeline writes runs) | `import mlflow` *inside the project's Python* (`client.py`) | **Yes.** An in-process import must find `mlflow` in *this* env. `uvx`'s throwaway env is a different process and cannot satisfy it. |
| **Viewing** (the dashboard at :5000) | the `mlflow` **CLI** | No — `uvx mlflow ui` runs it ephemerally. |

So: install `mlflow` for logging; use `uvx` if you just want to open the
dashboard without installing (e.g. on a view-only machine).

---

## 4. Why we chose the local store (and the reasons)

**Decision:** log to a **local file store** (`file:./mlruns`) and browse it with
`mlflow ui`. We did **not** adopt a remote `mlflow server`.

Reasons:

1. **Single researcher, single machine.** A shared tracking server only pays off
   with multiple people/agents writing concurrently. Here it would be pure
   overhead.
2. **No server to babysit.** With a file store, logging just writes files. With
   the server model you must start `mlflow server` *before* every logging run; if
   you forget, runs are silently dropped (our client swallows the connection
   error by design).
3. **Zero infrastructure / offline.** No ports, no service, no daemon — works on
   a plane. `mlflow ui` is only a *viewer* you start on demand; it does not need
   to run while you log.
4. **No credentials, no leak surface.** A remote URI would mean secrets and
   network config; a `file:` URI has none. (Matches the contracts rule: no
   secrets in committed files.)
5. **Trivially reversible.** Switching to a server later is a one-line env-var
   change (`MLFLOW_TRACKING_URI=http://...`); the wrapper already reads it.

The JSONL files under `outputs/` remain the **source of truth**; MLflow is
parallel shadow metadata that only ever *reads* what the pipeline already wrote.

---

## 5. Install first (only if you need to log)

You only need to install anything to **log**. Viewing can be done with `uvx`
with nothing installed.

```powershell
# Install MLflow into the project environment (needed for logging):
uv pip install "mlflow>=2.10,<3.0"      # or:  pip install "tritongen[tracking]"
```

Check whether it is already installed:

```powershell
python -c "import importlib.util; print(importlib.util.find_spec('mlflow') is not None)"
```

If this prints `False`, logging stays a no-op until you install it (by design).

> **Python 3.14 note:** `mlflow>=2.10,<3.0` pulls MLflow 2.x, which needs
> `pyarrow<16`; those old PyArrow versions have no 3.14 wheel and fail to build.
> Use a 3.11/3.12 environment for logging: `uv venv --python 3.12` then
> `uv pip install "tritongen[tracking]"`.

---

## 6. How to run each thing

### a) Log an experiment run

```powershell
$env:TRITONGEN_MLFLOW = "1"                         # gate 1: turn tracking on
python cluster1/experiments/run_cluster1.py ...     # Seam A is wired here (Phase 1)
```

This opens one run under `mlruns/` with the run's params/tags
(`condition`, `scale_tier`, `model_id`, `backend=local`, `cluster=cluster1`,
`reportable`). With the flag unset, the same command runs identically with no
MLflow writes. (Per-record metrics are added by later phases via the JSONL
writers; Phase 1 logs only the run boundary + params/tags.)

### b) Open the dashboard at http://127.0.0.1:5000

Pick **one** (both read the same local store):

```powershell
mlflow ui --backend-store-uri "file:./mlruns" --port 5000        # if mlflow is installed
uvx mlflow ui --backend-store-uri "file:./mlruns" --port 5000    # ephemeral, no install
```

The UI is just a reader — it does **not** need to be running while you log.

### c) (Optional, deferred) Run the server model instead

Only if you later want HTTP logging / a central backend:

```powershell
uvx mlflow server --backend-store-uri "file:./mlruns" --port 5000
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"   # now logging goes over HTTP
```

Trade-off: the server must be **up while you log**, or runs are dropped. This is
**not** the default here.

### d) Run the tracking tests (no MLflow needed)

```powershell
$env:PYTHONPATH = (Get-Location)
python -m pytest shared/tests/test_tracking_noop.py -q
```

Passes with `mlflow` absent — that is exactly what proves the no-op path.
