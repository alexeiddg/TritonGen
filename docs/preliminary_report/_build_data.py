"""
Compute aggregate data for the preliminary HTML report.

Reads:
- outputs/analysis/factorial_2x2_preliminary.json (authoritative for headline numbers)
- outputs/cluster1/baseline_repaired_l4_n20.jsonl  (none)
- outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl  (G)
- outputs/cluster2/c_paper_n20_l4.jsonl  (C)
- outputs/cluster2/g_plus_c_paper_n20_l4.jsonl  (G+C)
- outputs/cluster1/final_g_l4_n20.jsonl  (template-G upper-bound reference, optional)

Emits a single dict written to docs/preliminary_report/_report_data.json.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]

ARTIFACTS = {
    "none": REPO_ROOT / "outputs/cluster1/baseline_repaired_l4_n20.jsonl",
    "G":    REPO_ROOT / "outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl",
    "C":    REPO_ROOT / "outputs/cluster2/c_paper_n20_l4.jsonl",
    "G+C":  REPO_ROOT / "outputs/cluster2/g_plus_c_paper_n20_l4.jsonl",
}
TEMPLATE_G_REF = REPO_ROOT / "outputs/cluster1/final_g_l4_n20.jsonl"
ANALYZER = REPO_ROOT / "outputs/analysis/factorial_2x2_preliminary.json"

OUTCOME_FAMILY_ORDER = [
    "structural_code_surface",
    "task_functional",
    "mixed_diagnostic",
    "benchmarkable_performance",
]
S1_DIAGNOSTIC_KEYS = (
    "level_reach_rates",
    "feedback_activation",
    "metric_availability",
)
CURRENT_STATUSES = {"current", "current_with_caveats"}
COMPUTED_REPORTABILITY = {"reportable_primary", "reportable_secondary", "diagnostic_only"}

LEGACY_OUTCOME_FAMILIES = {
    "structural_code_surface": {
        "display_name": "Structural/code-surface quality",
        "question": "What improves generated-code structure, surface validity, grammar acceptance, compile, or launch?",
        "level_gates": ["level0_parse_surface", "level1_compile_launch"],
        "report_role": "secondary or diagnostic",
        "schema_version": "legacy_fallback_v1",
    },
    "task_functional": {
        "display_name": "Task/functional quality",
        "question": "What improves numerical correctness under the Level 2 task harness?",
        "level_gates": ["level2_correctness"],
        "report_role": "primary for current C comparisons",
        "schema_version": "legacy_fallback_v1",
    },
    "mixed_diagnostic": {
        "display_name": "Mixed diagnostic",
        "question": "What explains failure movement or activation without being a primary outcome?",
        "level_gates": ["failure_taxonomy"],
        "report_role": "diagnostic only",
        "schema_version": "legacy_fallback_v1",
    },
    "benchmarkable_performance": {
        "display_name": "Benchmarkable/performance quality",
        "question": "What would qualify a correct row for future performance evaluation?",
        "level_gates": ["level2_correctness", "level4_performance"],
        "report_role": "future only",
        "schema_version": "legacy_fallback_v1",
    },
}

LEGACY_REPORT_METRICS = {
    "level1_compile_success_rate": {
        "metric_name": "level1_compile_success_rate",
        "display_name": "Level 1 structural compile/launch success rate",
        "outcome_family": "structural_code_surface",
        "level_gate": "level1_compile_launch",
        "metric_gate": "compile_success",
        "response_variable": "compile_success",
        "analysis_role": "secondary_diagnostic",
        "reportability": "reportable_secondary",
        "current_status": "current_with_caveats",
        "metadata_source": "legacy_fallback_conservative_mapping",
        "caveat": "Legacy analyzer metadata unavailable; compile success is structural/code-surface evidence, not task correctness.",
    },
    "grammar_valid_rate": {
        "metric_name": "grammar_valid_rate",
        "display_name": "Grammar-valid rate",
        "outcome_family": "structural_code_surface",
        "level_gate": "level0_parse_surface",
        "metric_gate": "grammar_valid",
        "response_variable": None,
        "analysis_role": "diagnostic",
        "reportability": "diagnostic_only",
        "current_status": "current_with_caveats",
        "metadata_source": "legacy_fallback_conservative_mapping",
        "caveat": "Legacy analyzer metadata unavailable; grammar validity remains a structural diagnostic.",
    },
    "level2_functional_success_rate": {
        "metric_name": "level2_functional_success_rate",
        "display_name": "Level 2 task/functional success rate",
        "outcome_family": "task_functional",
        "level_gate": "level2_correctness",
        "metric_gate": "functional_success",
        "response_variable": "functional_success",
        "analysis_role": "primary",
        "reportability": "reportable_primary",
        "current_status": "current_with_caveats",
        "metadata_source": "legacy_fallback_conservative_mapping",
        "caveat": "Legacy analyzer metadata unavailable; Cluster 1 functional values remain normalized false/unproven, not measured Level 2 failure.",
    },
    "terminal_failure_distribution": {
        "metric_name": "terminal_failure_distribution",
        "display_name": "Terminal failure distribution",
        "outcome_family": "mixed_diagnostic",
        "level_gate": "failure_taxonomy",
        "metric_gate": "terminal_failure",
        "response_variable": None,
        "analysis_role": "diagnostic",
        "reportability": "diagnostic_only",
        "current_status": "current_with_caveats",
        "metadata_source": "legacy_fallback_conservative_mapping",
        "caveat": "Legacy analyzer metadata unavailable; failure distributions are explanatory diagnostics.",
    },
    "benchmarkable_performance_future_scope": {
        "metric_name": "benchmarkable_performance_future_scope",
        "display_name": "Benchmarkable/performance future scope",
        "outcome_family": "benchmarkable_performance",
        "level_gate": "level4_performance",
        "metric_gate": "future_performance",
        "response_variable": None,
        "analysis_role": "future_only",
        "reportability": "future_only",
        "current_status": "future_only",
        "metadata_source": "legacy_fallback_conservative_mapping",
        "caveat": "No current performance, timing, speedup, profiler, or benchmarkability evidence is authorized.",
    },
}


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _safe_report_payload(value: Any, *, path: str) -> Any:
    """Reject registry-sourced strings that would be unsafe inside HTML JSON."""
    if isinstance(value, str):
        lowered = value.lower()
        if "<" in value or ">" in value or "</script" in lowered:
            raise ValueError(f"unsafe report text in {path}")
        return value
    if isinstance(value, list):
        return [
            _safe_report_payload(item, path=f"{path}[{idx}]")
            for idx, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            str(key): _safe_report_payload(item, path=f"{path}.{key}")
            for key, item in value.items()
        }
    return value


def _has_s1_metadata(metadata: Mapping[str, Any]) -> bool:
    return isinstance(metadata.get("metric_registry"), dict) and isinstance(
        metadata.get("outcome_families"),
        dict,
    )


def _metadata_consumption(analyzer: Mapping[str, Any]) -> dict[str, Any]:
    metadata = analyzer.get("metadata", {})
    diagnostics = analyzer.get("diagnostics", {})
    has_s1_metadata = isinstance(metadata, Mapping) and _has_s1_metadata(metadata)
    has_s1_diagnostics = isinstance(diagnostics, Mapping) and all(
        key in diagnostics for key in S1_DIAGNOSTIC_KEYS
    )
    legacy_unavailable = not (has_s1_metadata and has_s1_diagnostics)
    caveats = []
    if legacy_unavailable:
        caveats.append(
            "Analyzer output lacks accepted S1 metric-registry metadata or diagnostics; "
            "report data uses conservative legacy fallback labels only."
        )
    return {
        "status": "accepted_s1_metadata" if not legacy_unavailable else "legacy_metadata_unavailable",
        "s1_metadata_available": bool(has_s1_metadata),
        "s1_diagnostics_available": bool(has_s1_diagnostics),
        "legacy_metadata_unavailable": bool(legacy_unavailable),
        "source_path": (
            "accepted_s1_metadata"
            if not legacy_unavailable
            else "legacy_fallback_only"
        ),
        "s1_to_s2_handoff_path": (
            "path_1_s1_metadata_consumed"
            if not legacy_unavailable
            else "path_3_legacy_fallback_only"
        ),
        "diagnostic_keys": {
            key: bool(isinstance(diagnostics, Mapping) and key in diagnostics)
            for key in S1_DIAGNOSTIC_KEYS
        },
        "caveats": caveats,
    }


def _report_outcome_families(
    metadata: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    if not consumption["legacy_metadata_unavailable"]:
        return _safe_report_payload(
            metadata["outcome_families"],
            path="metadata.outcome_families",
        )
    return json.loads(json.dumps(LEGACY_OUTCOME_FAMILIES))


def _report_metric_registry(
    metadata: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    if not consumption["legacy_metadata_unavailable"]:
        registry = _safe_report_payload(
            metadata["metric_registry"],
            path="metadata.metric_registry",
        )
        return {
            metric_name: {
                **entry,
                "metadata_source": "s1_metric_registry",
            }
            for metric_name, entry in registry.items()
        }
    return json.loads(json.dumps(LEGACY_REPORT_METRICS))


def _report_s1_diagnostics(
    diagnostics: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    if consumption["legacy_metadata_unavailable"]:
        return {}
    return {
        key: _safe_report_payload(diagnostics[key], path=f"diagnostics.{key}")
        for key in S1_DIAGNOSTIC_KEYS
    }


def _availability_for_metric(
    metric_name: str,
    diagnostics: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    if not consumption["legacy_metadata_unavailable"]:
        availability = diagnostics.get("metric_availability", {})
        if isinstance(availability, Mapping):
            metric_availability = availability.get(metric_name, {})
            if isinstance(metric_availability, Mapping):
                return dict(metric_availability)
    legacy_available = metric_name in {
        "level1_compile_success_rate",
        "level2_functional_success_rate",
        "grammar_valid_rate",
        "terminal_failure_distribution",
    }
    return {
        "available": legacy_available,
        "availability_status": "available" if legacy_available else "future_only",
        "computed_value_present": legacy_available,
        "reason": "Conservative legacy fallback from explicit analyzer/report fields.",
    }


def _rate_summary(condition_rates: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        condition: {
            "successes": row.get(f"{prefix}_successes"),
            "n": row.get(f"{prefix}_n"),
            "rate": row.get(f"{prefix}_rate"),
            "wilson_ci_95": row.get(f"{prefix}_wilson_ci_95"),
        }
        for condition, row in condition_rates.items()
    }


def _computed_metric_values(
    metric_name: str,
    *,
    analyzer: Mapping[str, Any],
    failure_modes: Mapping[str, Any],
) -> dict[str, Any]:
    condition_rates = analyzer.get("condition_rates", {})
    diagnostics = analyzer.get("diagnostics", {})
    if metric_name == "level2_functional_success_rate" and isinstance(
        condition_rates,
        Mapping,
    ):
        return {
            "condition_rates": _rate_summary(condition_rates, "functional_success"),
            "paired_comparisons": [
                row
                for row in analyzer.get("paired_comparisons", [])
                if row.get("metric_name") == metric_name
                or row.get("response_variable") == "functional_success"
            ],
        }
    if metric_name == "level1_compile_success_rate" and isinstance(
        condition_rates,
        Mapping,
    ):
        return {
            "condition_rates": _rate_summary(condition_rates, "compile_success"),
            "paired_comparisons": [
                row
                for row in analyzer.get("paired_comparisons", [])
                if row.get("metric_name") == metric_name
                or row.get("response_variable") == "compile_success"
            ],
        }
    if metric_name == "grammar_valid_rate" and isinstance(diagnostics, Mapping):
        return {
            "diagnostic_rows": diagnostics.get("grammar_acceptance_summary", []),
        }
    if metric_name == "terminal_failure_distribution":
        return {
            "diagnostic_distribution": dict(failure_modes),
        }
    return {}


def _metric_section_role(entry: Mapping[str, Any], computed_value_present: bool) -> str:
    if entry["current_status"] == "future_only" or entry["reportability"] == "future_only":
        return "future_only"
    if entry["current_status"] == "planned_deferred":
        return "planned_deferred"
    if entry["reportability"] == "reportable_primary" and computed_value_present:
        return "primary_task"
    if entry["reportability"] == "reportable_secondary" and computed_value_present:
        return "secondary_structural"
    return "diagnostic"


def _report_metric_groups(
    *,
    analyzer: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    failure_modes: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    families: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for family in OUTCOME_FAMILY_ORDER:
        family_meta = families.get(family, {})
        groups[family] = {
            "outcome_family": family,
            "display_name": family_meta.get("display_name", family),
            "question": family_meta.get("question"),
            "metrics": [],
        }

    for metric_name, entry in registry.items():
        family = entry.get("outcome_family", "mixed_diagnostic")
        if family not in groups:
            groups[family] = {
                "outcome_family": family,
                "display_name": family,
                "question": None,
                "metrics": [],
            }
        availability = _availability_for_metric(metric_name, diagnostics, consumption)
        current_status = entry.get("current_status")
        reportability = entry.get("reportability")
        computed_value_present = bool(
            availability.get("computed_value_present")
            and current_status in CURRENT_STATUSES
            and reportability in COMPUTED_REPORTABILITY
        )
        values = (
            _computed_metric_values(
                metric_name,
                analyzer=analyzer,
                failure_modes=failure_modes,
            )
            if computed_value_present
            else {}
        )
        metric_row = {
            "metric_name": metric_name,
            "display_name": entry.get("display_name", metric_name),
            "outcome_family": family,
            "level_gate": entry.get("level_gate"),
            "metric_gate": entry.get("metric_gate"),
            "response_variable": entry.get("response_variable"),
            "analysis_role": entry.get("analysis_role"),
            "reportability": reportability,
            "current_status": current_status,
            "availability_status": availability.get("availability_status"),
            "evidence_available": bool(availability.get("available")),
            "computed_report_value_present": bool(values),
            "section_role": _metric_section_role(entry, bool(values)),
            "headline_eligible": bool(
                reportability == "reportable_primary" and values
            ),
            "metadata_source": entry.get("metadata_source"),
            "caveat": entry.get("caveat"),
        }
        if values:
            metric_row["values"] = values
        groups[family]["metrics"].append(metric_row)

    for group in groups.values():
        group["metrics"].sort(key=lambda row: row["metric_name"])
        group["has_computed_values"] = any(
            row["computed_report_value_present"] for row in group["metrics"]
        )
    return groups


def _row_failure_code(row):
    """
    Classify a row into a failure-mode bucket.

    Cluster 1 rows (none, G) have only compile_success bool + compile_error_type.
    Cluster 2 rows (C, G+C) have failure_code / functional_success.
    Returns one of:
      success, F0_PARSE, F0_BAD_SIGNATURE, F1_COMPILE, F1_RUNTIME,
      F2_NUMERIC, F3_EVAL_PIPELINE, OTHER
    """
    # Cluster 2 path: failure_code present
    fc = row.get("failure_code")
    if row.get("functional_success") is True:
        return "success"
    if fc:
        if fc == "F0_PARSE":
            return "F0_PARSE"
        if fc == "F0_BAD_SIGNATURE":
            return "F0_BAD_SIGNATURE"
        if fc == "F1_COMPILE":
            return "F1_COMPILE"
        if fc == "F1_RUNTIME":
            return "F1_RUNTIME"
        if fc.startswith("F2_"):
            return "F2_NUMERIC"
        if fc == "F3_EVAL_PIPELINE":
            return "F3_EVAL_PIPELINE"
        return "OTHER"
    # Cluster 1 path
    if row.get("compile_success") is True:
        # Compiled but no failure_code → runtime/numeric on the matched-shape probe
        # In Cluster 1 we don't have post-compile evaluation; treat as 'compile_only_success'
        return "compile_only"
    et = row.get("compile_error_type")
    if et in ("SignatureError",):
        return "F0_BAD_SIGNATURE"
    if et == "SyntaxError":
        return "F0_PARSE"
    return "F1_COMPILE"


def _is_compile_success(row, condition):
    """
    Compile success per analyzer policy.
    - Cluster 1: row['compile_success'] bool
    - Cluster 2: derive from failure_code (F1_COMPILE/F0_*/F3 = no; everything else after compile = yes)
                 Cluster 2 G+C rows have an explicit compile_success bool too.
    """
    if "compile_success" in row and isinstance(row["compile_success"], bool):
        return row["compile_success"]
    fc = row.get("failure_code")
    if not fc:
        return bool(row.get("functional_success"))
    # Anything past F1_COMPILE/F0_* implies compile succeeded
    if fc.startswith("F0_") or fc == "F1_COMPILE":
        return False
    if fc == "F3_EVAL_PIPELINE":
        # Per F3 policy: excluded; treat as not-compile-success when no independent evidence
        return False
    return True  # F1_RUNTIME, F2_*, success → compiled


def aggregate():
    out = {"conditions": {}, "per_cell_compile": {}, "failure_modes": {},
           "repair": {}, "totals": {}}

    for cond, path in ARTIFACTS.items():
        rows = load_jsonl(path)
        out["totals"][cond] = len(rows)

        # Per-cell compile rates: keyed by (kernel_class, dtype)
        per_cell = {}
        per_cell_n = {}
        # Failure mode counts
        fm_counts = Counter()
        # Repair counts
        f2_reached = 0
        repair_lengths = []

        for r in rows:
            kc = r.get("kernel_class", "unknown")
            dt = r.get("dtype", "unknown")
            cell_key = f"{kc}/{dt}"
            per_cell.setdefault(cell_key, 0)
            per_cell_n.setdefault(cell_key, 0)
            per_cell_n[cell_key] += 1
            if _is_compile_success(r, cond):
                per_cell[cell_key] += 1

            fm = _row_failure_code(r)
            fm_counts[fm] += 1

            rt = r.get("repair_trace")
            if isinstance(rt, list) and rt:
                repair_lengths.append(len(rt))
                fc = r.get("failure_code", "")
                if fc.startswith("F2_"):
                    f2_reached += 1

        out["per_cell_compile"][cond] = {
            ck: {"successes": per_cell[ck], "n": per_cell_n[ck]}
            for ck in per_cell
        }
        out["failure_modes"][cond] = dict(fm_counts)
        out["repair"][cond] = {
            "f2_reached": f2_reached,
            "repair_trace_lengths": Counter(repair_lengths),
        }

    # Optional template-G reference
    if TEMPLATE_G_REF.exists():
        rows = load_jsonl(TEMPLATE_G_REF)
        out["totals"]["Template_G"] = len(rows)
        n_compile = sum(1 for r in rows if r.get("compile_success") is True)
        out["template_g_reference"] = {
            "n": len(rows), "compile_successes": n_compile,
            "compile_rate": n_compile / len(rows) if rows else 0.0,
        }

    # Pull headline numbers + diagnostics from analyzer JSON
    with open(ANALYZER) as f:
        analyzer = json.load(f)
    metadata = analyzer.get("metadata", {})
    diagnostics = analyzer.get("diagnostics", {})
    if not isinstance(metadata, Mapping):
        metadata = {}
    if not isinstance(diagnostics, Mapping):
        diagnostics = {}
    metadata = _safe_report_payload(metadata, path="metadata")
    diagnostics = _safe_report_payload(diagnostics, path="diagnostics")
    analyzer = {**analyzer, "metadata": metadata, "diagnostics": diagnostics}
    consumption = _metadata_consumption(analyzer)
    outcome_families = _report_outcome_families(metadata, consumption)
    report_metric_registry = _report_metric_registry(metadata, consumption)
    s1_diagnostics = _report_s1_diagnostics(diagnostics, consumption)
    outcome_metric_groups = _report_metric_groups(
        analyzer=analyzer,
        diagnostics=diagnostics,
        failure_modes=out["failure_modes"],
        registry=report_metric_registry,
        families=outcome_families,
        consumption=consumption,
    )
    out["metadata_consumption"] = consumption
    out["outcome_families"] = outcome_families
    out["outcome_metric_groups"] = outcome_metric_groups
    out["analyzer"] = {
        "condition_rates": analyzer["condition_rates"],
        "paired_comparisons": analyzer["paired_comparisons"],
        "factorial_model": analyzer["factorial_model"],
        "diagnostics_grammar": diagnostics["grammar_acceptance_summary"],
        "diagnostics_rejection": diagnostics["rejection_layer_breakdown"],
        "diagnostics_stop_reason": diagnostics["stop_reason_breakdown"],
        "metadata": metadata,
        "metadata_consumption": consumption,
        "outcome_families": outcome_families,
        "report_metric_registry": report_metric_registry,
        "report_metric_groups": outcome_metric_groups,
        "s1_diagnostics": s1_diagnostics,
        "missing_treatment_pairs": [
            pc.get("missing_treatment_pairs", [])
            for pc in analyzer["paired_comparisons"]
            if pc.get("response_variable") == "compile_success"
        ],
    }

    return out


if __name__ == "__main__":
    data = aggregate()
    # Convert Counters to dicts for JSON serialization
    for cond, rd in data["repair"].items():
        rd["repair_trace_lengths"] = {str(k): v for k, v in rd["repair_trace_lengths"].items()}
    out_path = Path(__file__).parent / "_report_data.json"
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Wrote {out_path}")
    print()
    print("=== summary ===")
    for cond in ("none", "G", "C", "G+C"):
        n = data["totals"][cond]
        successes = sum(
            data["per_cell_compile"][cond][ck]["successes"]
            for ck in data["per_cell_compile"][cond]
        )
        print(f"  {cond}: n={n}, compile_successes={successes}")
    print()
    print("Failure modes:")
    for cond in ("none", "G", "C", "G+C"):
        print(f"  {cond}: {data['failure_modes'][cond]}")
    print()
    print("Repair:")
    for cond in ("none", "G", "C", "G+C"):
        print(f"  {cond}: {data['repair'][cond]}")
    print()
    if "template_g_reference" in data:
        print(f"Template G ref: {data['template_g_reference']}")
