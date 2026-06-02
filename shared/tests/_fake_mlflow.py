"""Shared test double for mlflow used by the tracking seam tests.

`mlflow` is not installed in this environment, so the tracking client's only
import site (`shared.tracking.client._mlflow`) is patched with this fake, which
records every call and tracks active-run state. Not a test module (the leading
underscore keeps pytest from collecting it), mirroring `level2_fake_torch.py`.
"""

from __future__ import annotations

from types import SimpleNamespace


class FakeMlflow:
    """Minimal mlflow stand-in that records calls and active-run state."""

    def __init__(self) -> None:
        self.calls: list = []
        self._active = False

    def set_tracking_uri(self, uri) -> None:
        self.calls.append(("set_tracking_uri", uri))

    def set_experiment(self, name) -> None:
        self.calls.append(("set_experiment", name))

    def start_run(self):
        self._active = True
        self.calls.append(("start_run",))
        return SimpleNamespace(info=SimpleNamespace(run_id="fake"))

    def active_run(self):
        return SimpleNamespace() if self._active else None

    def log_params(self, params) -> None:
        self.calls.append(("log_params", dict(params)))

    def set_tags(self, tags) -> None:
        self.calls.append(("set_tags", dict(tags)))

    def set_tag(self, key, value) -> None:
        self.calls.append(("set_tag", key, value))

    def log_metrics(self, metrics, step=None) -> None:
        self.calls.append(("log_metrics", dict(metrics), step))

    def end_run(self) -> None:
        self._active = False
        self.calls.append(("end_run",))

    @property
    def metric_calls(self) -> list:
        """All recorded ``log_metrics`` calls as ``(name, metrics, step)``."""

        return [call for call in self.calls if call[0] == "log_metrics"]
