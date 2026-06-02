"""Seam D tests: analyzer factorial aggregates -> MLflow ``cell.*`` metrics.

Seam D is post-hoc and opt-in: the analyzer's ``main()`` calls
``tracking.log_factorial_summary(result)`` after writing its JSON. These tests
exercise the mapping + client against a synthetic analyzer-shaped result dict, so
they do **not** import the heavy analyzer (which needs pandas/numpy). A fake
mlflow is injected since mlflow is not installed here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import shared.tracking.client as client  # noqa: E402
from shared import tracking  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config, mapping  # noqa: E402


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def make_analysis_result(reportable: bool = True) -> dict:
    """A minimal dict shaped like ``analyze_factorial`` output."""

    return {
        "metadata": {
            "reportable": reportable,
            "response_variable": "functional_success",
            "analysis_scope": "primary_functional",
            "analyzer_version": "vTest",
        },
        "cell_summaries": [
            {
                "summary_level": "condition",
                "response_variable": "functional_success",
                "condition": "none",
                "success_rate": 0.0,
                "n_cells": 4,
            },
            {
                "summary_level": "condition",
                "response_variable": "functional_success",
                "condition": "G+C",  # the "+" must be sanitized for MLflow
                "success_rate": 0.5,
                "n_cells": 4,
            },
            {
                "summary_level": "condition",
                "response_variable": "compile_success",
                "condition": "G+C",
                "success_rate": 1.0,
                "n_cells": 4,
            },
            {
                # finer level -> must be ignored at the default summary_level
                "summary_level": "condition_kernel_dtype",
                "response_variable": "functional_success",
                "condition": "G",
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "success_rate": 1.0,
                "n_cells": 1,
            },
        ],
    }


# --------------------------------------------------------------------------- #
# Pure mapper
# --------------------------------------------------------------------------- #
def test_mapping_condition_level_and_plus_sanitized() -> None:
    metrics = mapping.factorial_result_to_metrics(make_analysis_result())
    assert metrics["cell.functional_success.none"] == 0.0
    assert metrics["cell.functional_success.G_C"] == 0.5
    assert metrics["cell.compile_success.G_C"] == 1.0
    assert metrics["cell.functional_success.G_C.n"] == 4.0
    # No "+" may leak into any metric name (MLflow rejects it).
    assert all("+" not in key for key in metrics)
    # Finer summary level is excluded at the default condition level.
    assert not any(key.endswith(".G") for key in metrics)


def test_mapping_accepts_bare_summary_list() -> None:
    summaries = make_analysis_result()["cell_summaries"]
    metrics = mapping.factorial_result_to_metrics(summaries)
    assert "cell.functional_success.none" in metrics


def test_mapping_skips_non_numeric_rate() -> None:
    result = {
        "cell_summaries": [
            {
                "summary_level": "condition",
                "response_variable": "functional_success",
                "condition": "none",
                "success_rate": None,
                "n_cells": 0,
            }
        ]
    }
    assert mapping.factorial_result_to_metrics(result) == {}


# --------------------------------------------------------------------------- #
# Client (Seam D) with a fake mlflow
# --------------------------------------------------------------------------- #
def test_active_run_logs_cell_metrics_and_reportable_tag(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")

    with tracking.run_context(backend="local"):
        tracking.log_factorial_summary(make_analysis_result(reportable=True))

    assert len(fake_mlflow.metric_calls) == 1
    metrics = fake_mlflow.metric_calls[0][1]
    assert metrics["cell.functional_success.G_C"] == 0.5
    assert metrics["cell.compile_success.G_C"] == 1.0
    assert all("+" not in key for key in metrics)
    assert ("set_tag", "reportable", "true") in fake_mlflow.calls


def test_reportable_false_tag(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    with tracking.run_context(backend="local"):
        tracking.log_factorial_summary(make_analysis_result(reportable=False))
    assert ("set_tag", "reportable", "false") in fake_mlflow.calls


def test_disabled_flag_logs_nothing(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "0")
    tracking.log_factorial_summary(make_analysis_result())
    assert fake_mlflow.calls == []


def test_enabled_without_active_run_logs_nothing(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    tracking.log_factorial_summary(make_analysis_result())  # no run_context
    assert fake_mlflow.metric_calls == []
    assert not any(call[0] == "start_run" for call in fake_mlflow.calls)