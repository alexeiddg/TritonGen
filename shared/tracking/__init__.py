"""Optional MLflow experiment tracking for TritonGen.

This subpackage is the single home for all MLflow logic; no cluster or analyzer
module imports ``mlflow`` directly. Tracking is additive and optional: with the
``TRITONGEN_MLFLOW`` flag unset or ``mlflow`` not installed, every call here is
a silent no-op and existing runs/tests behave exactly as before.

Read path: a launcher calls :func:`run_context` (from ``client``), which uses
``config`` to resolve where to log and ``mapping`` to turn project records into
MLflow params/metrics/tags.
"""

from __future__ import annotations

from shared.tracking.client import (
    is_enabled,
    log_cluster2_eval_row,
    log_cluster3_eval_row,
    log_eval_result,
    log_factorial_summary,
    log_generation_result,
    log_metrics,
    log_params,
    mlflow_available,
    run_context,
    set_tags,
)
from shared.tracking.config import (
    TrackingConfig,
    flag_enabled,
    load_tracking_config,
)

__all__ = [
    "TrackingConfig",
    "flag_enabled",
    "is_enabled",
    "load_tracking_config",
    "log_cluster2_eval_row",
    "log_cluster3_eval_row",
    "log_eval_result",
    "log_factorial_summary",
    "log_generation_result",
    "log_metrics",
    "log_params",
    "mlflow_available",
    "run_context",
    "set_tags",
]
