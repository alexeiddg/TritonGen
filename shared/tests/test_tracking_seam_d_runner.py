"""Seam D end-to-end tests: the real hook in ``factorial.main()``.

These exercise the actual analyzer entrypoint (not just the mapper/client with a
synthetic dict, which ``test_tracking_seam_d.py`` covers). The analyzer needs
``pandas``/``numpy``; where they are absent these tests skip cleanly so they run
in CI but never break a lean dev environment.

Guarantees locked here:
* the analyzer JSON output is identical whether tracking is on or off;
* with the flag off, ``main()`` performs no MLflow calls at all;
* with the flag on, metrics are logged *after* the JSON is written, the run is
  opened/closed once, and a ``reportable`` tag is set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pytest.importorskip("pandas")
pytest.importorskip("numpy")

import shared.tracking.client as client  # noqa: E402
from shared.analysis import factorial  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402

# Minimal valid analyzer input (mirrors the known-good single-row case in
# test_factorial_analysis.py). Compile-success secondary scope avoids needing
# the full four primary cells.
_ROW = {
    "condition": "none",
    "kernel_class": "elementwise",
    "kernel_id": 1,
    "kernel_name": "relu",
    "dtype_tested": "fp32",
    "sample_index": 7,
    "compile_success": True,
    "functional_success": True,
    "scale_tier": "paper",
}


def _write_input(tmp_path: Path) -> Path:
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(_ROW) + "\n", encoding="utf-8")
    return path


def _args(inp: Path, out: Path) -> list[str]:
    return [
        "--inputs", str(inp),
        "--output", str(out),
        "--response-variable", "compile_success",
        "--analysis-scope", "secondary_compile_diagnostic",
        "--bootstrap-samples", "10",
    ]


def test_main_output_identical_flag_on_vs_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inp = _write_input(tmp_path)

    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)
    out_off = tmp_path / "off.json"
    assert factorial.main(_args(inp, out_off)) == 0

    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    out_on = tmp_path / "on.json"
    assert factorial.main(_args(inp, out_on)) == 0

    # Tracking is shadow metadata: the analyzer JSON must be unaffected.
    assert json.loads(out_on.read_text("utf-8")) == json.loads(out_off.read_text("utf-8"))


def test_main_disabled_logs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)

    out = tmp_path / "o.json"
    assert factorial.main(_args(_write_input(tmp_path), out)) == 0
    assert out.exists()
    assert fake.calls == []


def test_main_logs_after_writing_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeMlflow()
    out = tmp_path / "o.json"

    # Spy on log_metrics to capture whether the analyzer JSON already exists at
    # the moment tracking logs — proving JSONL/JSON-first ordering.
    observed: dict[str, bool] = {}
    real_log_metrics = fake.log_metrics

    def spy_log_metrics(metrics, step=None):
        observed["output_existed"] = out.exists()
        real_log_metrics(metrics, step=step)

    fake.log_metrics = spy_log_metrics  # type: ignore[method-assign]
    monkeypatch.setattr(client, "_mlflow", fake)
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")

    assert factorial.main(_args(_write_input(tmp_path), out)) == 0

    kinds = [call[0] for call in fake.calls]
    assert kinds.count("start_run") == 1
    assert kinds.count("end_run") == 1
    assert fake.metric_calls, "expected cell.* metrics to be logged"
    metrics = fake.metric_calls[0][1]
    assert any(key.startswith("cell.compile_success") for key in metrics)
    assert observed.get("output_existed") is True
    assert any(call[0] == "set_tag" and call[1] == "reportable" for call in fake.calls)