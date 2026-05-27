from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "phase0_scaffolding_report.json"
)

ALLOWED_DIRTY_CLASSIFICATIONS = {
    "expected_prior_doc_spec_audit_change",
    "unrelated_tracked_code_change",
    "artifact_output_change",
    "unknown",
}
ALLOWED_DIRTY_ACTIONS = {
    "acknowledged",
    "blocks_phase0",
    "resolved_before_phase0",
}
ALLOWED_TEST_RESULTS = {"passed", "failed", "skipped"}
ALLOWED_PHASE0_CLASSIFICATIONS = {
    "PHASE0_SCAFFOLDING_COMPLETE",
    "PHASE0_SCAFFOLDING_COMPLETE_WITH_WARNINGS",
    "PHASE0_BLOCKED_DIRTY_TREE",
    "PHASE0_BLOCKED_TEST_FAILURE",
    "PHASE0_SURFACE_REGRESSION",
}


def _read_report() -> dict[str, Any]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_cluster3_package_imports_cheap() -> None:
    heavy_modules = {"torch", "triton", "transformers", "xgrammar", "modal"}
    removed_modules = {}
    cluster3_modules_under_test = ("cluster3.constants", "cluster3")
    removed_cluster3_modules = {
        module_name: sys.modules.pop(module_name)
        for module_name in cluster3_modules_under_test
        if module_name in sys.modules
    }
    for module_name in list(sys.modules):
        root_name = module_name.split(".", 1)[0]
        if root_name in heavy_modules:
            removed_modules[module_name] = sys.modules.pop(module_name)

    try:
        importlib.import_module("cluster3")
        importlib.import_module("cluster3.constants")

        imported_heavy_modules = sorted(
            module_name
            for module_name in sys.modules
            if module_name.split(".", 1)[0] in heavy_modules
        )
        assert imported_heavy_modules == []
    finally:
        for module_name in list(sys.modules):
            root_name = module_name.split(".", 1)[0]
            if root_name in heavy_modules or module_name in cluster3_modules_under_test:
                sys.modules.pop(module_name)
        sys.modules.update(removed_modules)
        sys.modules.update(removed_cluster3_modules)


def test_cluster3_constants_contract() -> None:
    from cluster3 import constants

    assert constants.CLUSTER3_CONDITIONS == ("P", "G+P", "C+P", "G+C+P")
    assert constants.P_GENERATION_CONDITIONS == constants.CLUSTER3_CONDITIONS
    assert constants.DEFAULT_P_REPAIR_BUDGET == 5
    assert constants.P_ELIGIBLE_FAILURE_CODES == frozenset({"F1_COMPILE"})
    assert constants.P_FEEDBACK_FORMAT_V1 == "compile_error_template_v1"
    assert constants.P_HISTORY_POLICY_V1 == "last_attempt_only_v1"
    assert constants.P_REPAIR_STOP_REASONS == frozenset(
        {
            "p_compile_repaired_then_success",
            "p_budget_exhausted",
            "p_compile_repaired_f2_observed",
            "p_post_compile_f3_observed",
            "p_f3_without_compile_evidence",
            "p_terminal_non_repairable",
            "p_not_applicable",
        }
    )


def test_cluster3_allowed_cells_match_registry() -> None:
    from cluster3.constants import CLUSTER3_CONDITIONS
    from shared.factors.registry import allowed_cells_for_cluster

    assert CLUSTER3_CONDITIONS == allowed_cells_for_cluster("cluster3")


def test_source_class_for_cluster3_condition_returns_generated_for_all_p_cells() -> None:
    from cluster2.constants import GENERATED_SOURCE_CLASS
    from cluster3.constants import CLUSTER3_CONDITIONS, source_class_for_cluster3_condition

    for condition in CLUSTER3_CONDITIONS:
        assert source_class_for_cluster3_condition(condition) == GENERATED_SOURCE_CLASS


def test_generation_mode_for_cluster3_condition_matches_c2_after_translation() -> None:
    from cluster2.constants import generation_mode_for_condition
    from cluster3.constants import generation_mode_for_cluster3_condition

    assert generation_mode_for_cluster3_condition("P") == generation_mode_for_condition("C")
    assert generation_mode_for_cluster3_condition("C+P") == generation_mode_for_condition(
        "C"
    )
    assert generation_mode_for_cluster3_condition("G+P") == generation_mode_for_condition(
        "G+C"
    )
    assert generation_mode_for_cluster3_condition(
        "G+C+P"
    ) == generation_mode_for_condition("G+C")


def test_source_class_for_cluster3_condition_rejects_non_cluster3() -> None:
    from cluster3.constants import source_class_for_cluster3_condition

    for condition in ("none", "G", "C", "G+C", "X"):
        with pytest.raises(ValueError):
            source_class_for_cluster3_condition(condition)


def test_phase0_contract_report_json_exists() -> None:
    assert REPORT_PATH.exists()


def test_phase0_contract_report_schema() -> None:
    report = _read_report()
    expected_keys = {
        "schema_version",
        "phase",
        "task",
        "preflight_git_status",
        "known_dirty_paths",
        "unexpected_dirty_paths",
        "files_added",
        "files_modified",
        "tests_added",
        "tests_run",
        "regression_checks",
        "negative_scope_verified",
        "classification",
    }
    assert set(report) == expected_keys
    assert report["schema_version"] == "cluster3.phase0_scaffolding_report.v1"
    assert report["phase"] == 0
    assert report["task"] == "cluster3_scaffolding"
    assert isinstance(report["files_added"], list)
    assert isinstance(report["files_modified"], list)
    assert isinstance(report["tests_added"], list)
    assert isinstance(report["tests_run"], list)
    assert isinstance(report["regression_checks"], list)
    assert isinstance(report["negative_scope_verified"], bool)
    for field_name in ("files_added", "files_modified", "tests_added"):
        assert all(isinstance(value, str) for value in report[field_name])
    for field_name in ("tests_run", "regression_checks"):
        for check in report[field_name]:
            assert set(check) == {"command", "result", "notes"}
            assert isinstance(check["command"], str)
            assert check["result"] in ALLOWED_TEST_RESULTS
            assert isinstance(check["notes"], str)


def test_phase0_contract_report_classification_allowed() -> None:
    report = _read_report()

    assert report["classification"] in ALLOWED_PHASE0_CLASSIFICATIONS


def test_phase0_contract_report_has_git_status_fields() -> None:
    report = _read_report()

    assert "preflight_git_status" in report
    assert "known_dirty_paths" in report
    assert "unexpected_dirty_paths" in report


def test_phase0_contract_report_preflight_git_status_is_string() -> None:
    report = _read_report()

    assert isinstance(report["preflight_git_status"], str)


def test_phase0_contract_report_known_dirty_paths_schema() -> None:
    report = _read_report()

    assert isinstance(report["known_dirty_paths"], list)
    for dirty_path in report["known_dirty_paths"]:
        assert set(dirty_path) == {"path", "classification", "action", "notes"}
        assert isinstance(dirty_path["path"], str)
        assert dirty_path["classification"] in ALLOWED_DIRTY_CLASSIFICATIONS
        assert dirty_path["action"] in ALLOWED_DIRTY_ACTIONS
        assert isinstance(dirty_path["notes"], str)


def test_phase0_contract_report_unexpected_dirty_paths_schema() -> None:
    report = _read_report()

    assert isinstance(report["unexpected_dirty_paths"], list)
    for dirty_path in report["unexpected_dirty_paths"]:
        assert isinstance(dirty_path, str)


def test_phase0_contract_report_blocks_on_unexpected_dirty_paths() -> None:
    report = _read_report()

    if report["unexpected_dirty_paths"]:
        assert report["classification"] == "PHASE0_BLOCKED_DIRTY_TREE"


def test_phase0_contract_report_does_not_require_current_git_status_match() -> None:
    report = _read_report()

    assert isinstance(report["preflight_git_status"], str)
    assert "current_git_status" not in report
