"""Tests for preliminary report data metadata consumption."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = REPO_ROOT / "docs" / "preliminary_report" / "_build_data.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("preliminary_report_build_data", BUILDER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _configure_builder(builder, tmp_path: Path, monkeypatch, analyzer: dict) -> None:
    artifact_paths = {}
    artifact_rows = {
        "none": [
            {
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "compile_success": False,
                "functional_success": False,
                "compile_error_type": "SignatureError",
            }
        ],
        "G": [
            {
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "compile_success": True,
                "functional_success": False,
            }
        ],
        "C": [
            {
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "compile_success": False,
                "functional_success": False,
                "failure_code": "F0_PARSE",
                "repair_trace": [{"attempt": 0}],
            }
        ],
        "G+C": [
            {
                "kernel_class": "elementwise",
                "dtype": "fp32",
                "compile_success": True,
                "functional_success": False,
                "failure_code": "F2_NUMERIC_NAN",
                "repair_trace": [{"attempt": attempt} for attempt in range(6)],
            }
        ],
    }
    for condition, rows in artifact_rows.items():
        path = tmp_path / f"{condition.replace('+', '_plus_')}.jsonl"
        _write_jsonl(path, rows)
        artifact_paths[condition] = path

    analyzer_path = tmp_path / "analyzer.json"
    _write_json(analyzer_path, analyzer)
    monkeypatch.setattr(builder, "ARTIFACTS", artifact_paths)
    monkeypatch.setattr(builder, "TEMPLATE_G_REF", tmp_path / "missing_template_g.jsonl")
    monkeypatch.setattr(builder, "ANALYZER", analyzer_path)


def _base_analyzer(*, s1_metadata: bool = True) -> dict:
    metadata = {
        "analysis_label": "current 2^2 subset analysis over G and C",
        "reportable": True,
        "scale_tiers": ["paper"],
        "scope_kind": "temporary_2^2_subset",
    }
    diagnostics = {
        "grammar_acceptance_summary": [
            {
                "condition": "G",
                "n_rows": 1,
                "gbnf_parse_valid_rate": 1.0,
                "semantic_valid_rate": 1.0,
                "grammar_valid_count": 1,
                "grammar_valid_rate": 1.0,
            }
        ],
        "rejection_layer_breakdown": [],
        "stop_reason_breakdown": [],
    }
    if s1_metadata:
        registry = _s1_metric_registry()
        metadata.update(
            {
                "outcome_family_schema_version": "outcome_family_v1",
                "outcome_families": _s1_outcome_families(),
                "metric_registry_schema_version": "metric_registry_v1",
                "metric_registry": registry,
                "metric_aliases": {
                    "compile_success_rate": "level1_compile_success_rate",
                    "functional_success_rate": "level2_functional_success_rate",
                },
                "registry_provenance": {
                    "schema_version": "registry_provenance_v1",
                    "source_docs": [
                        "docs/14_structural_vs_task_outcome_reporting_plan.md",
                        "docs/17_structural_task_analyzer_metadata_implementation_spec.md",
                    ],
                },
            }
        )
        diagnostics.update(
            {
                "level_reach_rates": [
                    {
                        "condition": "C",
                        "level2_correctness_reached_rows": 0,
                        "level2_evidence_policy": "derived_with_policy",
                    }
                ],
                "feedback_activation": [
                    {
                        "condition": "C",
                        "c_feedback_eligible_rows": 0,
                        "c_feedback_loop_fired_rows": 0,
                        "c_feedback_evidence_policy": "not_available",
                    }
                ],
                "metric_availability": _s1_metric_availability(registry),
            }
        )
    return {
        "condition_rates": {
            "none": _condition_rate("none", compile_successes=0, functional_successes=0),
            "G": _condition_rate("G", compile_successes=1, functional_successes=0),
            "C": _condition_rate("C", compile_successes=0, functional_successes=0),
            "G+C": _condition_rate("G+C", compile_successes=1, functional_successes=0),
        },
        "paired_comparisons": [
            {
                "comparison": "C vs none",
                "metric_name": "level2_functional_success_rate",
                "response_variable": "functional_success",
                "n_pairs": 1,
            },
            {
                "comparison": "G+C vs C",
                "metric_name": "level1_compile_success_rate",
                "response_variable": "compile_success",
                "n_pairs": 1,
            },
        ],
        "factorial_model": {"model_fit_status": "not_fit"},
        "diagnostics": diagnostics,
        "metadata": metadata,
    }


def _condition_rate(
    condition: str,
    *,
    compile_successes: int,
    functional_successes: int,
) -> dict:
    return {
        "condition": condition,
        "compile_success_successes": compile_successes,
        "compile_success_n": 1,
        "compile_success_rate": float(compile_successes),
        "compile_success_wilson_ci_95": [0.0, 1.0],
        "functional_success_successes": functional_successes,
        "functional_success_n": 1,
        "functional_success_rate": float(functional_successes),
        "functional_success_wilson_ci_95": [0.0, 1.0],
    }


def _s1_outcome_families() -> dict:
    return {
        "structural_code_surface": {
            "display_name": "Structural/code-surface quality",
            "question": "What improves generated-code structure?",
        },
        "task_functional": {
            "display_name": "Task/functional quality",
            "question": "What improves numerical correctness?",
        },
        "benchmarkable_performance": {
            "display_name": "Benchmarkable/performance quality",
            "question": "What would qualify future performance evaluation?",
        },
        "mixed_diagnostic": {
            "display_name": "Mixed diagnostic",
            "question": "What explains failure movement?",
        },
    }


def _s1_metric_registry() -> dict:
    def entry(
        metric_name: str,
        *,
        display_name: str,
        outcome_family: str,
        level_gate: str,
        metric_gate: str,
        response_variable: str | None,
        analysis_role: str,
        reportability: str,
        current_status: str,
    ) -> dict:
        return {
            "metric_name": metric_name,
            "display_name": display_name,
            "aliases": [],
            "outcome_family": outcome_family,
            "level_gate": level_gate,
            "metric_gate": metric_gate,
            "response_variable": response_variable,
            "analysis_role": analysis_role,
            "denominator_unit": "experimental_unit",
            "denominator_policy": "test fixture policy",
            "numerator_policy": "test fixture policy",
            "attempt_policy": "test fixture policy",
            "cluster_owner": "cross_cluster",
            "scope": "test fixture",
            "reportability": reportability,
            "current_status": current_status,
            "required_source_fields": [],
            "evidence_policy": (
                "not_computed"
                if current_status in {"planned_deferred", "future_only"}
                else "derived_with_policy"
            ),
            "missing_policy": "test fixture policy",
            "forbidden_interpretations": [],
            "caveat": "test fixture caveat",
            "schema_version": "metric_registry_v1",
        }

    return {
        "level2_functional_success_rate": entry(
            "level2_functional_success_rate",
            display_name="Level 2 task/functional success rate",
            outcome_family="task_functional",
            level_gate="level2_correctness",
            metric_gate="functional_success",
            response_variable="functional_success",
            analysis_role="primary",
            reportability="reportable_primary",
            current_status="current_with_caveats",
        ),
        "level1_compile_success_rate": entry(
            "level1_compile_success_rate",
            display_name="Level 1 structural compile/launch success rate",
            outcome_family="structural_code_surface",
            level_gate="level1_compile_launch",
            metric_gate="compile_success",
            response_variable="compile_success",
            analysis_role="secondary_diagnostic",
            reportability="reportable_secondary",
            current_status="current_with_caveats",
        ),
        "grammar_valid_rate": entry(
            "grammar_valid_rate",
            display_name="Grammar-valid rate",
            outcome_family="structural_code_surface",
            level_gate="level0_parse_surface",
            metric_gate="grammar_valid",
            response_variable=None,
            analysis_role="diagnostic",
            reportability="diagnostic_only",
            current_status="current_with_caveats",
        ),
        "syntax_valid_rate": entry(
            "syntax_valid_rate",
            display_name="Syntax-valid rate",
            outcome_family="structural_code_surface",
            level_gate="level0_parse_surface",
            metric_gate="syntax_valid",
            response_variable=None,
            analysis_role="diagnostic",
            reportability="not_reportable",
            current_status="planned_deferred",
        ),
        "terminal_failure_distribution": entry(
            "terminal_failure_distribution",
            display_name="Terminal failure distribution",
            outcome_family="mixed_diagnostic",
            level_gate="failure_taxonomy",
            metric_gate="terminal_failure",
            response_variable=None,
            analysis_role="diagnostic",
            reportability="diagnostic_only",
            current_status="current_with_caveats",
        ),
        "compile_pass_at_k": entry(
            "compile_pass_at_k",
            display_name="Compile pass-at-k with Level 1 gate",
            outcome_family="structural_code_surface",
            level_gate="level1_compile_launch",
            metric_gate="compile_success",
            response_variable="compile_success",
            analysis_role="diagnostic",
            reportability="diagnostic_only",
            current_status="planned_deferred",
        ),
        "correctness_pass_at_k": entry(
            "correctness_pass_at_k",
            display_name="Correctness pass-at-k with Level 2 gate",
            outcome_family="task_functional",
            level_gate="level2_correctness",
            metric_gate="functional_success",
            response_variable="functional_success",
            analysis_role="primary",
            reportability="not_reportable",
            current_status="planned_deferred",
        ),
        "repair_set_success_rate": entry(
            "repair_set_success_rate",
            display_name="Repair-set task success rate",
            outcome_family="task_functional",
            level_gate="level2_correctness",
            metric_gate="functional_success",
            response_variable="functional_success",
            analysis_role="diagnostic",
            reportability="diagnostic_only",
            current_status="planned_deferred",
        ),
        "eval_set_success_rate": entry(
            "eval_set_success_rate",
            display_name="Evaluation-set task success rate",
            outcome_family="task_functional",
            level_gate="level2_correctness",
            metric_gate="functional_success",
            response_variable="functional_success",
            analysis_role="diagnostic",
            reportability="diagnostic_only",
            current_status="planned_deferred",
        ),
        "benchmarkable_pass_at_k": entry(
            "benchmarkable_pass_at_k",
            display_name="Benchmarkable pass-at-k with future performance gate",
            outcome_family="benchmarkable_performance",
            level_gate="level4_performance",
            metric_gate="future_performance",
            response_variable=None,
            analysis_role="future_only",
            reportability="future_only",
            current_status="future_only",
        ),
    }


def _s1_metric_availability(registry: dict) -> dict:
    availability = {}
    for metric_name, entry in registry.items():
        current_status = entry["current_status"]
        computed = current_status == "current_with_caveats"
        availability[metric_name] = {
            "metric_name": metric_name,
            "outcome_family": entry["outcome_family"],
            "level_gate": entry["level_gate"],
            "metric_gate": entry["metric_gate"],
            "reportability": entry["reportability"],
            "current_status": current_status,
            "available": computed,
            "availability_status": (
                "future_only"
                if current_status == "future_only"
                else ("planned_deferred" if current_status == "planned_deferred" else "available")
            ),
            "computed_value_present": computed,
            "reason": "test fixture availability",
        }
    return availability


def test_aggregate_consumes_s1_metadata_and_groups_metrics(tmp_path, monkeypatch) -> None:
    builder = _load_builder()
    _configure_builder(builder, tmp_path, monkeypatch, _base_analyzer(s1_metadata=True))

    data = builder.aggregate()

    assert data["metadata_consumption"]["status"] == "accepted_s1_metadata"
    assert data["metadata_consumption"]["legacy_metadata_unavailable"] is False
    assert data["analyzer"]["s1_diagnostics"]["feedback_activation"][0]["condition"] == "C"

    groups = data["outcome_metric_groups"]
    structural = {
        metric["metric_name"]: metric
        for metric in groups["structural_code_surface"]["metrics"]
    }
    task = {metric["metric_name"]: metric for metric in groups["task_functional"]["metrics"]}
    mixed = {
        metric["metric_name"]: metric
        for metric in groups["mixed_diagnostic"]["metrics"]
    }
    future = {
        metric["metric_name"]: metric
        for metric in groups["benchmarkable_performance"]["metrics"]
    }

    assert structural["level1_compile_success_rate"]["metric_gate"] == "compile_success"
    assert structural["level1_compile_success_rate"]["section_role"] == (
        "secondary_structural"
    )
    assert structural["level1_compile_success_rate"]["computed_report_value_present"] is True
    assert structural["syntax_valid_rate"]["current_status"] == "planned_deferred"
    assert structural["syntax_valid_rate"]["computed_report_value_present"] is False
    assert "values" not in structural["syntax_valid_rate"]

    assert task["level2_functional_success_rate"]["metric_gate"] == "functional_success"
    assert task["level2_functional_success_rate"]["section_role"] == "primary_task"
    assert task["correctness_pass_at_k"]["current_status"] == "planned_deferred"
    assert task["correctness_pass_at_k"]["computed_report_value_present"] is False
    assert mixed["terminal_failure_distribution"]["section_role"] == "diagnostic"
    assert future["benchmarkable_pass_at_k"]["current_status"] == "future_only"
    assert future["benchmarkable_pass_at_k"]["computed_report_value_present"] is False


def test_aggregate_uses_legacy_fallback_without_s1_only_diagnostics(
    tmp_path,
    monkeypatch,
) -> None:
    builder = _load_builder()
    _configure_builder(builder, tmp_path, monkeypatch, _base_analyzer(s1_metadata=False))

    data = builder.aggregate()

    assert data["metadata_consumption"]["status"] == "legacy_metadata_unavailable"
    assert data["metadata_consumption"]["legacy_metadata_unavailable"] is True
    assert data["analyzer"]["s1_diagnostics"] == {}

    structural_names = {
        metric["metric_name"]
        for metric in data["outcome_metric_groups"]["structural_code_surface"]["metrics"]
    }
    task_names = {
        metric["metric_name"]
        for metric in data["outcome_metric_groups"]["task_functional"]["metrics"]
    }
    assert "level1_compile_success_rate" in structural_names
    assert "grammar_valid_rate" in structural_names
    assert "syntax_valid_rate" not in structural_names
    assert "level2_functional_success_rate" in task_names


def test_aggregate_rejects_unsafe_registry_display_text(tmp_path, monkeypatch) -> None:
    builder = _load_builder()
    analyzer = _base_analyzer(s1_metadata=True)
    analyzer["metadata"]["metric_registry"]["level1_compile_success_rate"][
        "display_name"
    ] = "unsafe <script>"
    _configure_builder(builder, tmp_path, monkeypatch, analyzer)

    with pytest.raises(ValueError, match="unsafe report text"):
        builder.aggregate()


def test_aggregate_report_data_has_no_bare_pass_at_k_text(tmp_path, monkeypatch) -> None:
    builder = _load_builder()
    _configure_builder(builder, tmp_path, monkeypatch, _base_analyzer(s1_metadata=True))

    data = builder.aggregate()

    assert "pass" + "@k" not in json.dumps(data)
