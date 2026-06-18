"""Seam E tests: Cluster 2/3 eval-row writers -> ``c2.*`` / ``c3.*`` metrics.

Cluster 2 and Cluster 3 each have their own JSONL writer and record type
(``Cluster2EvalRow`` / ``Cluster3EvalRow``), distinct from the ``EvalResult``
(Seam B) and ``GenerationResult`` (Seam C) writers. These cover the new mappers
and client entry points using dict rows (mappers accept dicts), plus the
run-config tag fix for multi-condition Modal runs. A fake mlflow is injected.

The logger hooks themselves are 3-line mirrors of the verified Seam B/C pattern
(``cluster{2,3}/results/logger.py::...append`` -> ``tracking.log_clusterN_eval_row``).
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


_C2_ROW = {
    "condition": "C",
    "source_class": "generated_row",
    "generation_mode": "new_c2_generation",
    "kernel_class": "elementwise",
    "kernel_name": "relu",
    "dtype": "fp32",
    "attempt_index": 0,
    "base_seed": 1,
    "source_hash": "h",
    "grammar_active": False,
    "compile_success": True,
    "functional_success": True,
    "repair_set_success": True,
    "eval_set_success": True,
    "failure_code": None,
}

_C3_ROW = {
    **_C2_ROW,
    "p_repair_attempted": True,
    "p_compile_repair_succeeded": False,
    "p_repair_changed_terminal_class": False,
    "p_repair_budget": 3,
    "p_repair_attempt_count": 2,
    "c_loop_fired": True,
    "c_terminal_level_reached": 2,
    "terminal_source_matches_row_source": True,
}


# --------------------------------------------------------------------------- #
# Pure mappers
# --------------------------------------------------------------------------- #
def test_cluster2_mapper_namespace_and_bools() -> None:
    metrics = mapping.cluster2_eval_row_to_metrics(_C2_ROW)
    assert metrics["c2.compile_success"] == 1.0
    assert metrics["c2.functional_success"] == 1.0
    assert metrics["c2.grammar_active"] == 0.0
    assert all(key.startswith("c2.") for key in metrics)
    # Identity fields are never metrics.
    assert "c2.base_seed" not in metrics
    assert "c2.attempt_index" not in metrics


def test_cluster3_mapper_includes_p_and_c_diagnostics() -> None:
    metrics = mapping.cluster3_eval_row_to_metrics(_C3_ROW)
    assert metrics["c3.p_repair_attempted"] == 1.0
    assert metrics["c3.p_repair_budget"] == 3.0
    assert metrics["c3.c_terminal_level_reached"] == 2.0
    assert metrics["c3.terminal_source_matches_row_source"] == 1.0
    assert all(key.startswith("c3.") for key in metrics)


def test_c2_and_c3_namespaces_are_disjoint() -> None:
    c2 = set(mapping.cluster2_eval_row_to_metrics(_C2_ROW))
    c3 = set(mapping.cluster3_eval_row_to_metrics(_C3_ROW))
    assert c2 and c3
    assert c2.isdisjoint(c3)


# --------------------------------------------------------------------------- #
# run_config_to_tags: omit absent single-value labels (multi-condition runs)
# --------------------------------------------------------------------------- #
def test_tags_omit_absent_condition_and_scale_tier() -> None:
    tags = mapping.run_config_to_tags({"model_id": "m"}, backend="modal", cluster="cluster2")
    assert "condition" not in tags
    assert "scale_tier" not in tags
    assert tags["backend"] == "modal"
    assert tags["cluster"] == "cluster2"
    assert tags["reportable"] == "false"


def test_tags_present_when_given() -> None:
    tags = mapping.run_config_to_tags(
        {"condition": "C", "scale_tier": "paper"}, backend="modal"
    )
    assert tags["condition"] == "C"
    assert tags["scale_tier"] == "paper"
    assert tags["reportable"] == "true"


# --------------------------------------------------------------------------- #
# Client logging within a run
# --------------------------------------------------------------------------- #
def test_log_cluster2_eval_row_within_run(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    with tracking.run_context(
        run_config={"scale_tier": "smoke", "model_id": "m"},
        backend="modal",
        cluster="cluster2",
    ):
        tracking.log_cluster2_eval_row(_C2_ROW)

    assert len(fake_mlflow.metric_calls) == 1
    metrics = fake_mlflow.metric_calls[0][1]
    assert metrics["c2.functional_success"] == 1.0
    tags = next(call[1] for call in fake_mlflow.calls if call[0] == "set_tags")
    assert tags["backend"] == "modal"
    assert tags["cluster"] == "cluster2"
    assert "condition" not in tags  # multi-condition run: no single condition


def test_log_cluster3_eval_row_within_run(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    with tracking.run_context(backend="modal", cluster="cluster3"):
        tracking.log_cluster3_eval_row(_C3_ROW)

    assert len(fake_mlflow.metric_calls) == 1
    assert all(key.startswith("c3.") for key in fake_mlflow.metric_calls[0][1])


def test_disabled_and_no_active_run_are_noops(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "0")
    tracking.log_cluster2_eval_row(_C2_ROW)
    assert fake_mlflow.calls == []

    # Flag on but no active run: still a no-op (no implicit run).
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    tracking.log_cluster3_eval_row(_C3_ROW)
    assert fake_mlflow.metric_calls == []
    assert not any(call[0] == "start_run" for call in fake_mlflow.calls)