"""Phase 0 tests for isolated Cluster 2 Modal scaffolding."""

from __future__ import annotations

import subprocess
import sys

import pytest

from cluster2.modal.generation import (
    generation_surface_metadata,
    validate_future_generation_condition,
)
from cluster2.modal.schemas import modal_surface_metadata, sidecar_generation_modes


HEAVY_MODULES = ("torch", "transformers", "xgrammar", "autoawq", "triton")


def _heavy_modules_after_import(target: str) -> list[str]:
    code = (
        "import sys\n"
        f"import {target}  # noqa: F401\n"
        "loaded = [name for name in "
        f"{HEAVY_MODULES!r} if name in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"probe failed for {target}: rc={proc.returncode} "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    out = proc.stdout.strip()
    return out.split(",") if out else []


@pytest.mark.parametrize(
    "target",
    [
        "cluster2.modal.schemas",
        "cluster2.modal.generation",
        "cluster2.modal.correctness",
        "cluster2.modal.correctness_runner",
    ],
)
def test_cluster2_modal_scaffolds_import_without_heavy_runtime_modules(target: str) -> None:
    assert _heavy_modules_after_import(target) == []


def test_modal_surface_metadata_is_cluster2_isolated() -> None:
    metadata = modal_surface_metadata()

    assert metadata.surface_phase == "phase0_scaffold"
    assert metadata.replay_conditions == ("none", "G")
    assert metadata.generated_conditions == ("C", "G+C")
    assert metadata.modal_generation_gpu == "L4"
    assert metadata.modal_eval_gpu == "L4"
    assert generation_surface_metadata() == metadata


def test_future_generation_surface_rejects_replay_controls() -> None:
    assert validate_future_generation_condition("C") == "C"
    assert validate_future_generation_condition("G+C") == "G+C"

    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        validate_future_generation_condition("none")
    with pytest.raises(ValueError, match="must not invoke C2 generation"):
        validate_future_generation_condition("G")


def test_sidecar_generation_modes_are_artifact_driven_for_replay_controls() -> None:
    assert sidecar_generation_modes() == {
        "none": {"generation_mode": "replay_control"},
        "G": {"generation_mode": "replay_control"},
        "C": {"generation_mode": "new_c2_generation"},
        "G+C": {"generation_mode": "new_c2_generation_with_G_adapter"},
    }
