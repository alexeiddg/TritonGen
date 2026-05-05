"""Adapter to export Cluster 1 generation results into KernelBench's runs/ structure.

This enables running KernelBench's eval_from_generations.py with backend=triton
as a Tier 2 diagnostic pass (correctness via fast_0) after the primary compile gate.

Architecture:
  - Pass 1 (Cluster 1 primary): check_compiles_all_dtypes() -> compile_success (pass@k)
  - Pass 2 (diagnostic only): KernelBench eval -> fast_0 (correctness rate)

Boundary rules:
  - fast_0 is reported alongside pass@k but does NOT replace it
  - fast_1, fast_2, speedup numbers are stored separately and NOT referenced in Cluster 1 analysis
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


def build_eval_command(
    config: KernelBenchExportConfig,
    num_gpu_devices: int = 1,
    timeout: int = 300,
) -> list[str]:
    """Build the shell command to run KernelBench evaluation on exported runs."""
    return [
        "uv", "run", "python",
        str(config.kernelbench_root / "scripts" / "eval_from_generations.py"),
        f"run_name={config.run_name}",
        "dataset_src=local",
        f"level={config.level}",
        "backend=triton",
        f"num_gpu_devices={num_gpu_devices}",
        f"timeout={timeout}",
    ]


def build_baseline_time_command(
    kernelbench_root: Path,
    hardware: str = "T4",
) -> list[str]:
    """Build command to generate baseline times for your specific hardware."""
    return [
        "uv", "run", "python",
        str(kernelbench_root / "scripts" / "generate_baseline_time.py"),
        "level=1",
        f"hardware={hardware}",
        "backend=triton",
    ]
