from __future__ import annotations

from pathlib import Path
import tomllib


def test_cluster1_demo_notebook_exists() -> None:
    notebook_path = Path("cluster1/notebooks/cluster1_demo.ipynb")

    assert notebook_path.exists()
    source = notebook_path.read_text(encoding="utf-8")
    for required in (
        "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "ScalingIntelligence/KernelBench",
        "grammar_active=True",
        "masked_token_rate",
        "compile_success",
        "compile_results_by_dtype",
    ):
        assert required in source


def test_awq_demo_model_runtime_dependency_is_declared() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert any(dependency.startswith("autoawq") for dependency in dependencies)
    assert "autoawq" in requirements
