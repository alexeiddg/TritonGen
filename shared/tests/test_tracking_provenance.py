"""Provenance tests: every MLflow run is tagged with git_commit + output_path.

Per the tracking policy (run provenance), ``run_context`` auto-tags each run with
the source commit and the JSONL artifact path (read from ``cli_args.output``), so
a dashboard run is traceable back to its evidence and code. A fake mlflow is
injected since mlflow is not installed here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import shared.tracking.client as client  # noqa: E402
from shared import tracking  # noqa: E402
from shared.tests._fake_mlflow import FakeMlflow  # noqa: E402
from shared.tracking import config  # noqa: E402


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> FakeMlflow:
    fake = FakeMlflow()
    monkeypatch.setattr(client, "_mlflow", fake)
    return fake


def _set_tags(fake: FakeMlflow) -> dict:
    return next(call[1] for call in fake.calls if call[0] == "set_tags")


# --------------------------------------------------------------------------- #
# Pure provenance-tag builder
# --------------------------------------------------------------------------- #
def test_provenance_tags_from_mapping_output() -> None:
    tags = client._provenance_tags({"output": "outputs/cluster2/run.jsonl"})
    assert tags["output_path"] == "outputs/cluster2/run.jsonl"
    expected = client._resolve_git_commit()
    if expected:
        assert tags["git_commit"] == expected


def test_provenance_tags_from_namespace_output() -> None:
    tags = client._provenance_tags(SimpleNamespace(output="o.jsonl", n=2))
    assert tags["output_path"] == "o.jsonl"


def test_provenance_tags_no_output_when_absent() -> None:
    assert "output_path" not in client._provenance_tags(None)
    assert "output_path" not in client._provenance_tags(SimpleNamespace(n=2))


def test_git_commit_is_a_sha_in_this_repo() -> None:
    commit = client._resolve_git_commit()
    # This repo is a git checkout, so a commit is expected; assert its shape.
    assert commit is not None
    assert 7 <= len(commit) <= 40
    assert all(ch in "0123456789abcdef" for ch in commit)


# --------------------------------------------------------------------------- #
# run_context auto-tags provenance
# --------------------------------------------------------------------------- #
def test_run_context_tags_provenance_with_run_config(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    with tracking.run_context(
        run_config={"scale_tier": "smoke", "model_id": "m"},
        cli_args={"output": "outputs/cluster2/run.jsonl"},
        backend="modal",
        cluster="cluster2",
    ):
        pass

    tags = _set_tags(fake_mlflow)
    assert tags["output_path"] == "outputs/cluster2/run.jsonl"
    assert tags["backend"] == "modal"
    assert tags["cluster"] == "cluster2"
    if client._resolve_git_commit():
        assert "git_commit" in tags


def test_run_context_tags_provenance_without_run_config(
    fake_mlflow: FakeMlflow, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Analyzer style: run_context with no run_config still gets provenance.
    monkeypatch.setenv(config.ENABLE_ENV_VAR, "1")
    with tracking.run_context(backend="local"):
        pass

    tags = _set_tags(fake_mlflow)
    assert tags.get("backend") == "local"
    if client._resolve_git_commit():
        assert "git_commit" in tags