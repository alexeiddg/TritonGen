# MLflow Tracking Policy

**Status:** Current tracking policy for TritonGen.
**Audience:** Research-facing methodology and reproducibility notes.

This contract defines how MLflow tracking may be used in TritonGen without
changing the evidentiary role of JSONL artifacts or the scale-tier policy.

## 1. Purpose

MLflow is an optional observability layer for experiment tracking. It records
run parameters, metrics, and tags so researchers can inspect and compare runs in
a dashboard.

MLflow is not a replacement for the project artifacts. It is a local mirror of
metadata and measurements already produced by the pipeline.

## 2. Source of Truth

The JSONL artifacts under `outputs/` remain the source of truth for experiment
results. MLflow records are secondary and must not be used to override, rewrite,
or repair JSONL evidence.

Tracking code must be additive:

- pipeline behavior must remain unchanged when MLflow is disabled;
- JSONL writes must happen before MLflow metric logging;
- MLflow failures must not break experiment execution;
- no frozen output artifact may be mutated to satisfy tracking.

When MLflow and JSONL disagree, current JSONL artifacts and current code/tests
take precedence.

## 3. Activation Policy

MLflow tracking activates only when both conditions are true:

1. `TRITONGEN_MLFLOW=1` is set;
2. the optional `mlflow` package is importable in the active Python environment.

If either condition is false, tracking must be a no-op. This preserves normal
development, testing, and reproduction flows for environments without MLflow.

## 4. Storage Policy

The default tracking store is local:

```text
file:./mlruns
```

The local `mlruns/` directory is runtime state and must not be committed. It is
used for browsing and comparison only.

Remote MLflow servers are out of scope for the default workflow. If a remote
server is introduced later, its URI and credentials must come from environment
variables or an approved secret mechanism, never from committed config files.

## 5. Reportability and Scale Tiers

MLflow tags must preserve the project's scale-tier policy. Runs should carry
`scale_tier` and `reportable` tags so smoke, development, and paper-scale runs
can be filtered.

Smoke and development runs are not paper evidence. They must not be mixed into
paper-scale conclusions, even if they appear in the same local MLflow store.

Analyzer metadata remains authoritative for reportability. The MLflow
`reportable` tag is a dashboard filter, not a promotion mechanism.

## 6. Metric Namespaces

Metric names must remain namespaced by record type to avoid collisions:

| Record source | Metric namespace |
| --- | --- |
| Cluster 1 generation records | `gen.*` |
| Shared evaluation records | `eval.*` |
| Factorial/analyzer summaries | `cell.*` |

Metrics may summarize or mirror values already emitted by the pipeline, but
they must not introduce undocumented success criteria.

## 7. Modal Policy

The default Modal policy is local-orchestrator logging:

- Modal performs remote GPU computation.
- Results return to the local process.
- The local process writes JSONL and logs to MLflow.

Under this default, MLflow is not required inside Modal containers, and no
tracking credentials are shipped to remote GPU workers.

## 8. Documentation Boundary

Operational onboarding belongs in `docs/tracking/README.md`.

Implementation reference belongs in `shared/tracking/README.md`.

Internal implementation plans may live in `.contracts/agentic/`, but they are
not research-facing evidence unless their decisions are sanitized and promoted
into this contract or another file under `.contracts/research/`.
