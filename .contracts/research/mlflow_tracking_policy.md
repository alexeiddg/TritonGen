# MLflow Tracking Policy

**Status:** Current tracking policy for TritonGen.
**Last revised:** 2026-06-02.
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
| Cluster 2 eval rows | `c2.*` |
| Cluster 3 eval rows | `c3.*` |
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

## 8. Run Provenance and Traceability

Every MLflow run must be traceable back to the evidence it mirrors. Runs should
carry tags that link them to their artifacts and code:

- the source commit (`git_commit`) the run was produced from;
- the output artifact path(s) — the JSONL file(s) the run mirrors;
- `cluster`, `condition`, `scale_tier`, and `backend` (already required by the
  scale-tier policy).

An MLflow run identifies one launcher invocation (a batch of cells). It is not
the same as the per-record `run_id` field on `EvalResult` / `GenerationResult`,
which identifies a single experiment cell. The two must not be conflated.

If files are attached as MLflow artifacts, they are attached as copies or
pointers. A frozen output artifact is never moved, renamed, or rewritten to
satisfy tracking.

## 9. Permitted and Prohibited Content

MLflow params, metrics, tags, and artifacts may only carry configuration and
measurements already produced by the pipeline.

The following must never be logged to MLflow:

- secrets or credentials of any kind (tokens, keys, authenticated remote URIs);
- raw generated kernel source code or full model outputs;
- model weights or tokenizer/model binaries;
- datasets or raw dataset rows.

Logging must not introduce success criteria, thresholds, or derived claims that
are not already defined by the pipeline and its contracts.

## 10. Backfill Policy

Tracking applies to new runs only. Frozen JSONL artifacts are not retroactively
imported into MLflow as part of the normal workflow.

If historical backfill is ever required (for example, a dashboard of past paper
runs), it must be performed by a separate, read-only script that reads the
frozen JSONL and creates MLflow runs without modifying, renaming, or deleting
any file under `outputs/`.

## 11. Documentation Boundary

Operational onboarding belongs in `docs/tracking/README.md`.

Implementation reference belongs in `shared/tracking/README.md`.

Internal implementation plans may live in `.contracts/agentic/`, but they are
not research-facing evidence unless their decisions are sanitized and promoted
into this contract or another file under `.contracts/research/`.
