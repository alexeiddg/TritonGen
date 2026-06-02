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

import functools
import logging
from collections.abc import Iterator, Mapping
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


def _never_raises(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a public logging function so a tracking error can never break a run.

    This is the centralized contract guarantee: every per-record/aggregate
    logging entry point below is wrapped, so a failure anywhere in mapping or
    the mlflow call (not just the inner ``_safe`` site) is logged and swallowed.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception:  # noqa: BLE001 - tracking must never break a run
            logger.warning("MLflow %s failed; ignored", fn.__name__, exc_info=True)
            return None

    return wrapper


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


@_never_raises
def log_eval_result(result: Any) -> None:
    """Log one ``EvalResult`` as stepped ``eval.*`` metrics (no-op if disabled)."""

    if not _should_log():
        return
    metrics = mapping.eval_result_to_metrics(result)
    if metrics:
        step = mapping.eval_result_step(result)
        _safe(lambda: _mlflow.log_metrics(metrics, step=step))


@_never_raises
def log_generation_result(result: Any) -> None:
    """Log one Cluster 1 ``GenerationResult`` as ``gen.*`` metrics (no-op if disabled)."""

    if not _should_log():
        return
    metrics = mapping.generation_result_to_metrics(result)
    if metrics:
        _safe(lambda: _mlflow.log_metrics(metrics))


@_never_raises
def log_factorial_summary(
    analysis_result: Any,
    *,
    reportable: bool | None = None,
    summary_level: str = "condition",
) -> None:
    """Log analyzer factorial aggregates (Seam D), post-hoc and opt-in.

    Accepts the ``analyze_factorial`` result dict (or a bare list of its
    ``cell_summaries``). Logs condition-level ``cell.*`` success-rate metrics and
    sets the ``reportable`` tag (read from ``metadata.reportable`` unless given
    explicitly). No-op if disabled or if there is no active run.
    """

    if not _should_log():
        return
    resolved_reportable = reportable
    if resolved_reportable is None and isinstance(analysis_result, Mapping):
        metadata = analysis_result.get("metadata")
        if isinstance(metadata, Mapping):
            resolved_reportable = metadata.get("reportable")
    if resolved_reportable is not None:
        flag = "true" if resolved_reportable else "false"
        _safe(lambda: _mlflow.set_tag("reportable", flag))
    metrics = mapping.factorial_result_to_metrics(analysis_result, summary_level=summary_level)
    if metrics:
        _safe(lambda: _mlflow.log_metrics(metrics))


@_never_raises
def log_params(params: Mapping[str, Any]) -> None:
    """Log arbitrary params (no-op if disabled)."""

    if not _should_log() or not params:
        return
    _safe(lambda: _mlflow.log_params(dict(params)))


@_never_raises
def log_metrics(metrics: Mapping[str, float], step: int | None = None) -> None:
    """Log arbitrary metrics (no-op if disabled)."""

    if not _should_log() or not metrics:
        return
    _safe(lambda: _mlflow.log_metrics(dict(metrics), step=step))


@_never_raises
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
