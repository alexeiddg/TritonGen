"""No-op-safe MLflow client wrapper — the ONLY module that imports ``mlflow``.

Tracking activates only when BOTH gates pass:

1. ``TRITONGEN_MLFLOW`` is truthy (see :mod:`shared.tracking.config`), and
2. ``mlflow`` is importable.

If either gate is off, every public function here is a silent no-op and
:func:`run_context` yields ``None``. Tracking failures never propagate: a
logging error is logged at WARNING and swallowed, so observability code can
never break an experiment run.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any, Callable

from shared.tracking import mapping
from shared.tracking.config import TrackingConfig, flag_enabled, load_tracking_config

logger = logging.getLogger(__name__)

try:
    import mlflow as _mlflow
except ImportError:  # pragma: no cover - exercised only when mlflow is absent
    _mlflow = None


def mlflow_available() -> bool:
    """Return whether the optional ``mlflow`` package is importable."""

    return _mlflow is not None


def is_enabled(config: TrackingConfig | None = None) -> bool:
    """Return whether tracking is active (feature flag AND mlflow installed)."""

    cfg = config if config is not None else load_tracking_config()
    return cfg.enabled and mlflow_available()


@contextmanager
def run_context(
    *,
    run_config: Any | None = None,
    cli_args: Any | None = None,
    backend: str = "local",
    cluster: str | None = None,
    config: TrackingConfig | None = None,
) -> Iterator[None]:
    """Open an MLflow run for the duration of the ``with`` block.

    When tracking is disabled this is a transparent no-op: it yields ``None``
    and the wrapped body runs unchanged. The run is always ended on exit, even
    if the body raises.
    """

    cfg = config if config is not None else load_tracking_config()
    if not (cfg.enabled and mlflow_available()):
        yield None
        return

    try:
        _mlflow.set_tracking_uri(cfg.tracking_uri)
        _mlflow.set_experiment(cfg.experiment_for(cluster))
        _mlflow.start_run()
    except Exception:  # noqa: BLE001 - tracking must never break a run
        logger.warning("MLflow run setup failed; continuing untracked", exc_info=True)
        yield None
        return

    try:
        if run_config is not None:
            _safe(lambda: _mlflow.log_params(mapping.run_config_to_params(run_config, cli_args)))
            _safe(
                lambda: _mlflow.set_tags(
                    {**cfg.run_tags, **mapping.run_config_to_tags(
                        run_config, backend=backend, cluster=cluster
                    )}
                )
            )
        elif cfg.run_tags:
            _safe(lambda: _mlflow.set_tags(dict(cfg.run_tags)))
        yield None
    finally:
        _safe(_mlflow.end_run)


def log_eval_result(result: Any) -> None:
    """Log one ``EvalResult`` as stepped ``eval.*`` metrics (no-op if disabled)."""

    if not _should_log():
        return
    metrics = mapping.eval_result_to_metrics(result)
    if metrics:
        step = mapping.eval_result_step(result)
        _safe(lambda: _mlflow.log_metrics(metrics, step=step))


def log_generation_result(result: Any) -> None:
    """Log one Cluster 1 ``GenerationResult`` as ``gen.*`` metrics (no-op if disabled)."""

    if not _should_log():
        return
    metrics = mapping.generation_result_to_metrics(result)
    if metrics:
        _safe(lambda: _mlflow.log_metrics(metrics))


def log_factorial_summary(
    cell_summaries: Iterable[Any],
    *,
    reportable: bool | None = None,
) -> None:
    """Log ``CellSummary`` aggregates and an optional ``reportable`` tag.

    Intended to be called post-hoc by the analyzer (Seam D). No-op if disabled
    or if there is no active run.
    """

    if not _should_log():
        return
    if reportable is not None:
        _safe(lambda: _mlflow.set_tag("reportable", "true" if reportable else "false"))
    for summary in cell_summaries:
        metrics = mapping.cell_summary_to_metrics(summary)
        if metrics:
            _safe(lambda payload=metrics: _mlflow.log_metrics(payload))


def log_params(params: Mapping[str, Any]) -> None:
    """Log arbitrary params (no-op if disabled)."""

    if not _should_log() or not params:
        return
    _safe(lambda: _mlflow.log_params(dict(params)))


def log_metrics(metrics: Mapping[str, float], step: int | None = None) -> None:
    """Log arbitrary metrics (no-op if disabled)."""

    if not _should_log() or not metrics:
        return
    _safe(lambda: _mlflow.log_metrics(dict(metrics), step=step))


def set_tags(tags: Mapping[str, str]) -> None:
    """Set arbitrary tags (no-op if disabled)."""

    if not _should_log() or not tags:
        return
    _safe(lambda: _mlflow.set_tags(dict(tags)))


def _should_log() -> bool:
    """Cheap per-call gate: flag on, mlflow installed, and a run is active."""

    if not (flag_enabled() and mlflow_available()):
        return False
    return _mlflow.active_run() is not None


def _safe(call: Callable[[], Any]) -> None:
    try:
        call()
    except Exception:  # noqa: BLE001 - tracking must never break a run
        logger.warning("MLflow logging call failed; ignored", exc_info=True)
