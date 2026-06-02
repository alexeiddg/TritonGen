"""Pure mappers from TritonGen records to MLflow-style primitives.

These functions hold all project-specific knowledge about *what* to track. They
deliberately do **not** import ``mlflow`` so they are trivially unit-testable
and reusable. They never raise on missing optional fields: ``None`` or
non-numeric values are simply skipped.

Each record accepts either the frozen dataclass instance or its ``dict`` form,
so callers may pass a live ``EvalResult`` or a deserialized JSONL row
interchangeably.

Metric namespaces are disjoint per record type so the two independent write
seams never collide within a single run:

* :class:`shared.eval.schema.EvalResult`       -> ``eval.*``
* :class:`cluster1.results.dataclass.GenerationResult` -> ``gen.*``
* :class:`shared.eval.schema.CellSummary`       -> ``cell.*``
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

# Identity/config fields are deliberately excluded from metrics; only outcome
# numerics belong in the time-series. Booleans map to 0.0/1.0.
EVAL_RESULT_METRIC_FIELDS: tuple[str, ...] = (
    "level_reached",
    "parse_success",
    "has_triton_decorator",
    "signature_valid",
    "compile_success",
    "functional_success",
    "safe_success",
    "grammar_active",
    "gbnf_parse_valid",
    "semantic_valid",
    "grammar_valid",
    "compile_time_s",
    "max_abs_diff",
    "max_rel_diff",
    "num_test_shapes",
    "shapes_passed",
    "kernel_time_ms",
    "kernel_time_iqr_ms",
    "eager_time_ms",
    "compile_time_ms",
    "speedup_vs_eager",
    "speedup_vs_compile",
    "tokens_input",
    "tokens_output",
    "generation_time_s",
    "repair_iteration",
    "repair_converged",
)

GENERATION_RESULT_METRIC_FIELDS: tuple[str, ...] = (
    "grammar_active",
    "compile_success",
    "masked_token_rate",
    "n_shapes_tested",
    "temperature",
    "gbnf_parse_valid",
    "semantic_valid",
    "grammar_valid",
    "generation_metadata_schema_version",
)

CELL_SUMMARY_METRIC_FIELDS: tuple[str, ...] = (
    "compile_at_1",
    "pass_at_1",
    "pass_at_5",
    "pass_at_10",
    "safe_at_1",
    "median_speedup_vs_compile",
    "median_speedup_vs_eager",
    "fast_at_0",
    "fast_at_1_0",
    "fast_at_1_2",
    "fast_tc_at_1_0",
    "fast_tc_at_1_2",
    "mean_repair_iters_converged",
    "convergence_rate",
    "repair_efficiency",
    "unique_ratio_source",
    "unique_ratio_ast",
    "mean_tokens_total",
    "cost_adjusted_pass1",
    "pass1_ci_lower",
    "pass1_ci_upper",
)

CLUSTER2_EVAL_ROW_METRIC_FIELDS: tuple[str, ...] = (
    "grammar_active",
    "compile_success",
    "functional_success",
    "repair_set_success",
    "eval_set_success",
)

CLUSTER3_EVAL_ROW_METRIC_FIELDS: tuple[str, ...] = (
    "grammar_active",
    "compile_success",
    "functional_success",
    "repair_set_success",
    "eval_set_success",
    "p_repair_attempted",
    "p_compile_repair_succeeded",
    "p_repair_changed_terminal_class",
    "p_repair_budget",
    "p_repair_attempt_count",
    "c_loop_fired",
    "c_terminal_level_reached",
    "terminal_source_matches_row_source",
)

RUN_CONFIG_PARAM_FIELDS: tuple[str, ...] = (
    "condition",
    "source_class",
    "generation_mode",
    "scale_tier",
    "repair_budget",
    "equal_attempts_n",
    "enable_ast_sanitizer",
    "model_id",
    "model_revision",
    "tokenizer_revision",
    "modal_generation_gpu",
    "modal_eval_gpu",
)


def run_config_to_params(
    run_config: Any,
    cli_args: Any | None = None,
) -> dict[str, Any]:
    """Map a ``RunConfig`` (and optional CLI args) to MLflow params."""

    data = _as_mapping(run_config)
    params: dict[str, Any] = {
        name: data[name] for name in RUN_CONFIG_PARAM_FIELDS if name in data
    }
    dtypes = data.get("dtypes")
    if dtypes is not None:
        params["dtypes"] = ",".join(str(dtype) for dtype in dtypes)
    for key, value in _cli_args_to_mapping(cli_args).items():
        params[f"arg.{key}"] = value
    return params


def run_config_to_tags(
    run_config: Any,
    *,
    backend: str = "local",
    cluster: str | None = None,
) -> dict[str, str]:
    """Map a ``RunConfig`` to filtering tags, including ``reportable``.

    ``reportable`` mirrors the scale-tier policy (only ``paper`` is candidate
    reportable). The analyzer's ``metadata.reportable`` remains authoritative;
    this tag is only for dashboard filtering.
    """

    data = _as_mapping(run_config)
    tags = {
        "backend": str(backend),
        "reportable": "true" if data.get("scale_tier") == "paper" else "false",
    }
    # Emit each label only when present, so callers without a single run-level
    # value never produce empty-string tags: Cluster 1 has no routing fields, and
    # multi-condition Cluster 2/3 runs have no single `condition`.
    for optional in ("condition", "scale_tier", "source_class", "generation_mode"):
        value = data.get(optional)
        if value:
            tags[optional] = str(value)
    if cluster is not None:
        tags["cluster"] = str(cluster)
    return tags


def eval_result_to_metrics(result: Any) -> dict[str, float]:
    """Map an ``EvalResult`` to ``eval.*`` numeric metrics, skipping ``None``."""

    return _collect_metrics(result, EVAL_RESULT_METRIC_FIELDS, prefix="eval")


def eval_result_step(result: Any) -> int | None:
    """Return the per-sample metric step from an ``EvalResult``."""

    data = _as_mapping(result)
    sample_index = data.get("sample_index")
    return sample_index if isinstance(sample_index, int) else None


def generation_result_to_metrics(result: Any) -> dict[str, float]:
    """Map a Cluster 1 ``GenerationResult`` to ``gen.*`` numeric metrics."""

    return _collect_metrics(result, GENERATION_RESULT_METRIC_FIELDS, prefix="gen")


def cluster2_eval_row_to_metrics(row: Any) -> dict[str, float]:
    """Map a Cluster 2 ``Cluster2EvalRow`` to ``c2.*`` numeric metrics."""

    return _collect_metrics(row, CLUSTER2_EVAL_ROW_METRIC_FIELDS, prefix="c2")


def cluster3_eval_row_to_metrics(row: Any) -> dict[str, float]:
    """Map a Cluster 3 ``Cluster3EvalRow`` to ``c3.*`` numeric metrics."""

    return _collect_metrics(row, CLUSTER3_EVAL_ROW_METRIC_FIELDS, prefix="c3")


def cell_summary_to_metrics(summary: Any) -> dict[str, float]:
    """Map a ``shared.eval.schema.CellSummary`` to ``cell.*`` aggregate metrics."""

    return _collect_metrics(summary, CELL_SUMMARY_METRIC_FIELDS, prefix="cell")


def factorial_result_to_metrics(
    analysis_result: Any,
    *,
    summary_level: str = "condition",
) -> dict[str, float]:
    """Map analyzer factorial output to ``cell.*`` success-rate metrics.

    Accepts the full ``analyze_factorial`` result dict or a bare list of its
    ``cell_summaries``. Emits one metric per ``(response_variable, condition)``
    at the requested ``summary_level`` (default the coarse per-condition level),
    keyed as ``cell.<response>.<condition>`` (success rate) plus
    ``cell.<response>.<condition>.n`` (cell size). Condition labels are
    sanitized for MLflow (``+`` -> ``_``), so ``G+C`` becomes ``G_C``.
    """

    if isinstance(analysis_result, Mapping):
        summaries = analysis_result.get("cell_summaries") or []
    else:
        summaries = analysis_result or []
    metrics: dict[str, float] = {}
    for summary in summaries:
        if not isinstance(summary, Mapping):
            continue
        if summary.get("summary_level") != summary_level:
            continue
        response = str(summary.get("response_variable", "")).strip()
        condition = str(summary.get("condition", "")).strip()
        if not response or not condition:
            continue
        rate = _as_metric(summary.get("success_rate"))
        if rate is None:
            continue
        key = f"cell.{response}.{_sanitize_metric_label(condition)}"
        metrics[key] = rate
        size = _as_metric(summary.get("n_cells"))
        if size is not None:
            metrics[f"{key}.n"] = size
    return metrics


def _sanitize_metric_label(label: str) -> str:
    # MLflow metric names allow [A-Za-z0-9_.\-/ :]; condition labels use "+".
    return label.replace("+", "_")


def _collect_metrics(
    record: Any,
    fields: tuple[str, ...],
    *,
    prefix: str,
) -> dict[str, float]:
    data = _as_mapping(record)
    metrics: dict[str, float] = {}
    for name in fields:
        numeric = _as_metric(data.get(name))
        if numeric is not None:
            metrics[f"{prefix}.{name}"] = numeric
    return metrics


def _as_metric(value: Any) -> float | None:
    # bool is a subclass of int, so it is handled by the numeric branch and
    # serialized as 0.0/1.0.
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_mapping(record: Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        produced = to_dict()
        if isinstance(produced, dict):
            return produced
    if is_dataclass(record) and not isinstance(record, type):
        return asdict(record)
    raise TypeError(f"cannot map record of type {type(record).__name__!r}")


def _cli_args_to_mapping(cli_args: Any | None) -> dict[str, Any]:
    if cli_args is None:
        return {}
    if isinstance(cli_args, Mapping):
        return dict(cli_args)
    namespace = getattr(cli_args, "__dict__", None)
    return dict(namespace) if isinstance(namespace, dict) else {}
