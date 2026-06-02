# `shared/tracking/` — optional MLflow experiment tracking

This is the **only** place in TritonGen that imports `mlflow`. Clusters and the
analyzer call into this package; they never touch MLflow directly. Tracking is
**additive and optional** — with it disabled, every existing run and test
behaves exactly as before.

## The two gates

Tracking activates only when **both** are true:

1. environment flag `TRITONGEN_MLFLOW=1`, and
2. the optional `mlflow` package is installed (`pip install "tritongen[tracking]"`).

If either gate is off, every function here is a silent no-op and
`run_context(...)` yields `None`.

## The four modules (one read path)

| Module | Responsibility |
|---|---|
| `config.py`  | Resolves env + `shared/configs/tracking.yaml` into a frozen `TrackingConfig` (where to log, experiment names). No `mlflow` import. |
| `mapping.py` | Pure functions: `RunConfig`/`EvalResult`/`GenerationResult`/`CellSummary` → params/metrics/tags. No `mlflow` import. |
| `client.py`  | The only `import mlflow` site. No-op-safe `run_context`, `log_*`. Failures are swallowed (warn, never raise). |
| `__init__.py`| Public API surface (re-exports). |

Read path: a launcher imports `shared.tracking`, calls `run_context(...)` →
`config.py` decides *where*, `mapping.py` decides *what*.

## Metric namespaces (disjoint by record type)

| Record | Prefix |
|---|---|
| `EvalResult` | `eval.*` |
| `GenerationResult` (Cluster 1) | `gen.*` |
| `CellSummary` (analyzer) | `cell.*` |

## Usage (once seams are wired)

```python
from shared import tracking

with tracking.run_context(run_config=cfg, cli_args=args, backend="local", cluster="cluster1"):
    ...  # existing loop unchanged; per-record logging happens inside the writers
```

## Browse results

```bash
TRITONGEN_MLFLOW=1 mlflow ui   # then open http://127.0.0.1:5000
```

The local store lives in `mlruns/` (gitignored). The JSONL files under
`outputs/` remain the source of truth; MLflow is parallel shadow metadata.
