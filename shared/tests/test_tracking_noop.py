"""Phase 0 tests for the optional MLflow tracking subpackage.

Two guarantees are covered:

1. **Disabled path is a true no-op.** With the ``TRITONGEN_MLFLOW`` flag unset,
   importing and calling every public function has no side effects and never
   raises — regardless of whether ``mlflow`` is installed. This is what keeps
   the existing test suite green when ``mlflow`` is absent.
2. **Mappers are pure and correct.** The ``mapping`` functions accept both the
   real frozen dataclasses and their ``dict`` forms, skip ``None`` fields,
   convert booleans to ``0.0``/``1.0``, exclude identity fields from metrics,
   and use disjoint metric namespaces.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cluster1.results.dataclass import GenerationResult  # noqa: E402
from cluster2.constants import (  # noqa: E402
    generation_mode_for_condition,
    source_class_for_condition,
)
from shared.eval.run_config import RunConfig  # noqa: E402
from shared.eval.schema import EvalResult  # noqa: E402
from shared.tracking import client, config, mapping  # noqa: E402
from shared import tracking  # noqa: E402


# --------------------------------------------------------------------------- #
# Builders for real records (kept minimal but valid).
# --------------------------------------------------------------------------- #
def make_run_config(condition: str = "none", scale_tier: str = "smoke") -> RunConfig:
    return RunConfig(
        condition=condition,
        source_class=source_class_for_condition(condition),
        generation_mode=generation_mode_for_condition(condition),
        scale_tier=scale_tier,
        repair_budget=5,
        equal_attempts_n=6,
        enable_ast_sanitizer=False,
        dtypes=("fp32",),
        model_id="test-model",
        model_revision="rev",
        tokenizer_revision="rev",
        modal_generation_gpu=None,
        modal_eval_gpu="A100",
    )


def make_eval_result(**overrides: object) -> EvalResult:
    base: dict[str, object] = dict(
        kernel_id=1,
        kernel_name="relu",
        kernel_class="elementwise",
        kernelbench_level=1,
        condition="C",
        sample_index=3,
        model_id="m",
        run_id="r",
        timestamp="2026-01-01T00:00:00Z",
        dtype_tested="fp32",
        source="x",
        source_hash="h",
        ast_hash=None,
        level_reached=1,
        parse_success=True,
        parse_error=None,
        has_triton_decorator=True,
        signature_valid=True,
        compile_success=True,
        compile_error=None,
        failure_code=None,
    )
    base.update(overrides)
    return EvalResult(**base)  # type: ignore[arg-type]


def make_generation_result(**overrides: object) -> GenerationResult:
    base: dict[str, object] = dict(
        source="x",
        model_id="m",
        grammar_active=True,
        grammar_variant="task_agnostic",
        kernel_class="elementwise",
        kernel_name="relu",
        dtype="fp32",
        compile_success=True,
        compile_results_by_dtype={"fp32": True},
        compile_error_type=None,
        compile_error_msg=None,
        masked_token_rate=0.25,
        unique_solution_hash="h",
        n_shapes_tested=5,
        generation_seed=0,
        temperature=0.2,
        run_id="r",
        timestamp_utc="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return GenerationResult(**base)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _disable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the feature flag is off for every test unless explicitly set."""

    monkeypatch.delenv(config.ENABLE_ENV_VAR, raising=False)


# --------------------------------------------------------------------------- #
# 1. Disabled path is a true no-op.
# --------------------------------------------------------------------------- #
def test_flag_disabled_reports_not_enabled() -> None:
    assert config.flag_enabled() is False
    assert client.is_enabled() is False
    assert isinstance(client.mlflow_available(), bool)


def test_flag_truthy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv(config.ENABLE_ENV_VAR, value)
        assert config.flag_enabled() is True
    for value in ("0", "", "off", "no"):
        monkeypatch.setenv(config.ENABLE_ENV_VAR, value)
        assert config.flag_enabled() is False


def test_run_context_disabled_yields_none_and_runs_body() -> None:
    ran = False
    with tracking.run_context(run_config=make_run_config(), backend="local") as handle:
        ran = True
        assert handle is None
    assert ran is True


def test_disabled_log_calls_are_silent_noops() -> None:
    # None of these require an active MLflow run or installed mlflow.
    tracking.log_eval_result(make_eval_result())
    tracking.log_generation_result(make_generation_result())
    tracking.log_factorial_summary([], reportable=False)
    tracking.log_params({"a": 1})
    tracking.log_metrics({"m": 1.0}, step=0)
    tracking.set_tags({"t": "v"})


def test_load_tracking_config_defaults_when_disabled() -> None:
    cfg = config.load_tracking_config()
    assert cfg.enabled is False
    assert cfg.tracking_uri  # resolved (yaml default or built-in)
    assert cfg.experiment_for("cluster1")
    assert cfg.experiment_for(None) == cfg.default_experiment


def test_tracking_uri_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.TRACKING_URI_ENV_VAR, "file:./custom_store")
    cfg = config.load_tracking_config()
    assert cfg.tracking_uri == "file:./custom_store"


def test_load_tracking_config_missing_yaml_uses_defaults(tmp_path: Path) -> None:
    cfg = config.load_tracking_config(config_path=tmp_path / "missing.yaml")
    assert cfg.tracking_uri == config.DEFAULT_TRACKING_URI
    assert cfg.default_experiment == config.DEFAULT_EXPERIMENT


# --------------------------------------------------------------------------- #
# 2. Mappers are pure and correct.
# --------------------------------------------------------------------------- #
def test_run_config_params_and_tags() -> None:
    cfg = make_run_config(condition="none", scale_tier="smoke")
    params = mapping.run_config_to_params(cfg, cli_args={"n": 1})
    assert params["condition"] == "none"
    assert params["scale_tier"] == "smoke"
    assert params["dtypes"] == "fp32"
    assert params["arg.n"] == 1

    tags = mapping.run_config_to_tags(cfg, backend="local", cluster="cluster1")
    assert tags["condition"] == "none"
    assert tags["backend"] == "local"
    assert tags["cluster"] == "cluster1"
    assert tags["reportable"] == "false"


def test_reportable_tag_true_only_for_paper() -> None:
    paper = mapping.run_config_to_tags(make_run_config(scale_tier="paper"))
    assert paper["reportable"] == "true"


def test_tags_omit_absent_routing_fields() -> None:
    # Cluster 1 style: has condition/scale_tier/source_class but no
    # generation_mode. Absent routing fields must not appear as empty strings.
    tags = mapping.run_config_to_tags(
        {"condition": "baseline", "scale_tier": "smoke", "source_class": "generated_row"},
        backend="local",
        cluster="cluster1",
    )
    assert tags["source_class"] == "generated_row"
    assert "generation_mode" not in tags
    assert "" not in tags.values()
    assert tags["condition"] == "baseline"
    assert tags["cluster"] == "cluster1"


def test_eval_result_metrics_skip_none_and_cast_bools() -> None:
    metrics = mapping.eval_result_to_metrics(make_eval_result())
    assert metrics["eval.compile_success"] == 1.0
    assert metrics["eval.level_reached"] == 1.0
    # Identity fields must never appear as metrics.
    assert "eval.kernel_id" not in metrics
    assert "eval.sample_index" not in metrics
    # Level 2+ fields are None on this record and must be skipped.
    assert "eval.functional_success" not in metrics
    assert "eval.speedup_vs_compile" not in metrics
    # Every emitted value is a float.
    assert all(isinstance(value, float) for value in metrics.values())


def test_eval_result_step_uses_sample_index() -> None:
    assert mapping.eval_result_step(make_eval_result(sample_index=7)) == 7


def test_generation_result_metrics_namespace() -> None:
    metrics = mapping.generation_result_to_metrics(make_generation_result())
    assert metrics["gen.compile_success"] == 1.0
    assert metrics["gen.masked_token_rate"] == 0.25
    assert all(key.startswith("gen.") for key in metrics)


def test_cell_summary_metrics_from_dict() -> None:
    summary = {"compile_at_1": 0.5, "pass_at_1": 0.25, "median_speedup_vs_compile": None}
    metrics = mapping.cell_summary_to_metrics(summary)
    assert metrics == {"cell.compile_at_1": 0.5, "cell.pass_at_1": 0.25}


def test_mappers_accept_dict_and_dataclass_equally() -> None:
    result = make_eval_result()
    from_obj = mapping.eval_result_to_metrics(result)
    from_dict = mapping.eval_result_to_metrics(result.to_dict())
    assert from_obj == from_dict


def test_namespaces_are_disjoint() -> None:
    eval_keys = set(mapping.eval_result_to_metrics(make_eval_result()))
    gen_keys = set(mapping.generation_result_to_metrics(make_generation_result()))
    assert eval_keys and gen_keys
    assert eval_keys.isdisjoint(gen_keys)


def test_unmappable_record_raises_typeerror() -> None:
    with pytest.raises(TypeError):
        mapping.eval_result_to_metrics(object())
