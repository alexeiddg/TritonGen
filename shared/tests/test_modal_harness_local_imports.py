"""Lock the local-import contract for the Cluster 1 Modal adapter.

Importing ``cluster1.generation.modal_generate`` (or
``shared.modal_harness.generation``) on a developer machine must not pull
in ``torch``, ``transformers``, ``xgrammar``, or ``autoawq`` — those belong
on the Modal container and would otherwise force every local runner /
notebook / unit test to install the GPU stack.
"""

from __future__ import annotations

import subprocess
import sys

HEAVY_MODULES = ("torch", "transformers", "xgrammar", "autoawq")


def _heavy_modules_after_import(target: str) -> list[str]:
    """Subprocess-isolated probe: import ``target`` from a clean interpreter.

    Returns the heavy modules that appear in ``sys.modules`` after the
    import. Running in a subprocess keeps test-process state from leaking
    into the result.
    """
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


def test_modal_generate_does_not_load_heavy_deps() -> None:
    leaked = _heavy_modules_after_import("cluster1.generation.modal_generate")
    assert not leaked, f"local cluster adapter pulled heavy modules: {leaked}"


def test_modal_compile_check_does_not_load_heavy_deps() -> None:
    leaked = _heavy_modules_after_import("cluster1.validation.modal_compile_check")
    assert not leaked, f"local compile adapter pulled heavy modules: {leaked}"


def test_shared_generation_does_not_load_heavy_deps() -> None:
    """Direct import of the harness module must also stay light.

    The harness file defines the ``@app.cls`` decorator at module load
    time, so it has to be importable wherever Modal is — including local
    machines that lack the GPU stack.
    """
    leaked = _heavy_modules_after_import("shared.modal_harness.generation")
    assert not leaked, f"shared generation module pulled heavy modules: {leaked}"


def test_fireworks_generation_does_not_load_heavy_deps() -> None:
    leaked = _heavy_modules_after_import("shared.modal_harness.fireworks_generation")
    assert not leaked, f"Fireworks generation module pulled heavy modules: {leaked}"


def test_run_cluster1_modal_does_not_load_heavy_deps() -> None:
    """The Phase 5 Modal runner must be importable without the GPU stack.

    All ``cluster1.data.kernels`` / ``cluster1.results`` / adapter imports
    are deferred into function bodies so ``import
    cluster1.experiments.run_cluster1_modal`` only pulls in stdlib + Modal.
    """
    leaked = _heavy_modules_after_import("cluster1.experiments.run_cluster1_modal")
    assert not leaked, f"Phase 5 Modal runner pulled heavy modules: {leaked}"
