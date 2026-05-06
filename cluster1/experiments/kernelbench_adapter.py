"""Adapter to export Cluster 1 compile-passing sources into KernelBench layout.

Cluster 1 stops at compile acceptance. This module only writes generated source
files into KernelBench's runs/ directory shape for downstream clusters or
external tooling; it does not create executable commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cluster1.results.dataclass import GenerationResult


@dataclass(frozen=True)
class KernelBenchExportConfig:
    """Configuration for exporting to KernelBench runs/ directory structure."""

    kernelbench_root: Path
    run_name: str
    level: int = 1


def export_to_kernelbench_runs(
    results: list["GenerationResult"],
    config: KernelBenchExportConfig,
) -> list[Path]:
    """Write compile-passing GenerationResult sources into KernelBench runs/ directory.

    Only exports results that passed Tier 1 (compile_success=True).
    Returns the list of paths written.
    """
    written: list[Path] = []

    for result in results:
        if not result.compile_success:
            continue

        problem_id = _resolve_problem_id(result)
        if problem_id is None:
            continue

        out_dir = (
            config.kernelbench_root
            / "runs"
            / config.run_name
            / f"level_{config.level}"
            / f"problem_{problem_id}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        kernel_path = out_dir / "generated_kernel.py"
        kernel_path.write_text(result.source)
        written.append(kernel_path)

    return written


def _resolve_problem_id(result: "GenerationResult") -> int | None:
    """Map kernel_class to the verified KernelBench problem ID."""
    mapping = {
        "elementwise": 19,
        "reduction": 23,
        "matmul": 1,
    }
    return mapping.get(result.kernel_class)
