"""Tracking configuration resolution for the optional MLflow integration.

This module is configuration-only. It does **not** import ``mlflow`` and has no
side effects. It reads two environment variables plus an optional YAML file of
non-secret defaults and resolves them into a frozen :class:`TrackingConfig`.

Activation requires BOTH gates to be on:

1. environment ``TRITONGEN_MLFLOW`` set to a truthy value, and
2. the optional ``mlflow`` package importable (checked in
   :mod:`shared.tracking.client`).

When either gate is off, every tracking call elsewhere is a silent no-op.
Secrets (remote URIs, credentials) come only from environment variables or
``modal.Secret`` — never from the committed YAML.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ENABLE_ENV_VAR = "TRITONGEN_MLFLOW"
TRACKING_URI_ENV_VAR = "MLFLOW_TRACKING_URI"
DEFAULT_TRACKING_URI = "file:./mlruns"
DEFAULT_EXPERIMENT = "tritongen"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "tracking.yaml"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def flag_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the ``TRITONGEN_MLFLOW`` feature flag is truthy.

    This reads only the environment and never touches the YAML file, so it is
    cheap enough to gate per-record logging hot paths.
    """

    source = os.environ if env is None else env
    return source.get(ENABLE_ENV_VAR, "").strip().lower() in _TRUTHY


@dataclass(frozen=True)
class TrackingConfig:
    """Resolved tracking configuration.

    ``enabled`` reflects only the feature flag; the second gate (mlflow being
    importable) is enforced in :mod:`shared.tracking.client`.
    """

    enabled: bool
    tracking_uri: str
    default_experiment: str
    experiments_by_cluster: dict[str, str] = field(default_factory=dict)
    run_tags: dict[str, str] = field(default_factory=dict)

    def experiment_for(self, cluster: str | None) -> str:
        """Resolve the experiment name for an optional cluster label."""

        if cluster is None:
            return self.default_experiment
        return self.experiments_by_cluster.get(cluster, self.default_experiment)


def load_tracking_config(
    *,
    config_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> TrackingConfig:
    """Resolve a :class:`TrackingConfig` from env + the non-secret YAML defaults.

    Environment overrides YAML overrides built-in defaults. A missing or
    malformed YAML file degrades silently to defaults so tracking config never
    blocks a run.
    """

    source = os.environ if env is None else env
    data = _read_yaml(config_path or DEFAULT_CONFIG_PATH)
    experiments = _as_dict(data.get("experiments"))
    tracking_uri = (
        source.get(TRACKING_URI_ENV_VAR)
        or data.get("tracking_uri")
        or DEFAULT_TRACKING_URI
    )
    return TrackingConfig(
        enabled=flag_enabled(source),
        tracking_uri=str(tracking_uri),
        default_experiment=str(experiments.get("default", DEFAULT_EXPERIMENT)),
        experiments_by_cluster=_as_str_dict(experiments.get("by_cluster")),
        run_tags=_as_str_dict(data.get("tags")),
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}
