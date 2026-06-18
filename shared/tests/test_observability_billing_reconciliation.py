from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from shared.observability.billing_reconciliation import (
    BillingReconciliationError,
    build_actual_billing_reconciliation_metadata,
    dry_run_reconciliation,
    parse_redacted_billing_report,
    reconcile_billing_records_to_run,
    validate_billing_report_record,
)
from shared.observability.schema import ObservabilityActualBillingReconciliation

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "shared" / "observability" / "billing_reconciliation.py"


def test_parse_valid_redacted_static_json_report(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    report_path.write_text(json.dumps({"records": [_record()]}), encoding="utf-8")

    records = parse_redacted_billing_report(report_path)

    assert len(records) == 1
    assert records[0]["billing_report_redacted_sha256"] == "a" * 64
    assert records[0]["report_source"] == "redacted_static_export"


def test_parse_valid_redacted_static_jsonl_report(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.jsonl"
    report_path.write_text(json.dumps(_record()) + "\n", encoding="utf-8")

    records = parse_redacted_billing_report(report_path)

    assert records[0]["total_cost"] == 0.42


def test_valid_report_reconciles_to_o5a_metadata(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    report_path.write_text(json.dumps([_record()]), encoding="utf-8")
    records = parse_redacted_billing_report(report_path)

    result = reconcile_billing_records_to_run(
        records,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
    )

    metadata = result.metadata
    assert isinstance(metadata, ObservabilityActualBillingReconciliation)
    assert metadata.actual_billing_status == "reconciled"
    assert metadata.billing_source == "approved_exported_static_report"
    assert metadata.actual_total_cost == 0.42
    assert result.matched_record_count == 1


def test_redacted_modal_report_reconciles_to_modal_cli_source(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "billing.jsonl"
    report_path.write_text(
        json.dumps(_record(report_source="redacted_modal_billing_report")) + "\n",
        encoding="utf-8",
    )
    records = parse_redacted_billing_report(report_path)

    result = reconcile_billing_records_to_run(
        records,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
    )

    assert result.metadata.actual_billing_status == "reconciled"
    assert result.metadata.billing_source == "approved_modal_billing_cli_report"


def test_build_metadata_validates_through_o5a_schema() -> None:
    metadata = build_actual_billing_reconciliation_metadata(
        _record(),
        reconciled_at_utc="2026-06-04T00:05:00Z",
    )

    revalidated = ObservabilityActualBillingReconciliation.model_validate(
        metadata.model_dump(mode="json")
    )
    assert revalidated.billing_report_redacted_sha256 == "a" * 64


def test_dry_run_reconciliation_writes_no_files(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    write_path = tmp_path / "sidecars" / "actual_billing.json"
    report_path.write_text(json.dumps([_record()]), encoding="utf-8")

    result = dry_run_reconciliation(
        report_path,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
        write_path=write_path,
    )

    assert result.dry_run is True
    assert result.wrote_file is False
    assert not write_path.exists()


def test_explicit_write_path_writes_only_reconciliation_metadata(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    write_path = tmp_path / "sidecars" / "actual_billing.json"
    report_path.write_text(json.dumps([_record()]), encoding="utf-8")

    result = dry_run_reconciliation(
        report_path,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
        dry_run=False,
        write_path=write_path,
        fsync=False,
    )

    assert result.wrote_file is True
    payload = json.loads(write_path.read_text(encoding="utf-8"))
    assert payload["actual_billing_status"] == "reconciled"
    assert payload["actual_total_cost"] == 0.42
    assert "result_path" not in payload
    assert "source_event_sha256" not in payload


def test_non_dry_run_requires_explicit_write_path(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    report_path.write_text(json.dumps([_record()]), encoding="utf-8")

    with pytest.raises(BillingReconciliationError, match="write_path"):
        dry_run_reconciliation(
            report_path,
            experiment_id="exp",
            run_id="run",
            time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
            dry_run=False,
        )


def test_ambiguous_or_untagged_attribution_becomes_limited() -> None:
    untagged = _record(run_id=None, app_tag=None)

    result = reconcile_billing_records_to_run(
        [untagged],
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
    )

    assert result.metadata.actual_billing_status == "attribution_limited"
    assert result.metadata.actual_total_cost is None
    assert result.candidate_record_count == 1
    assert result.matched_record_count == 0


@pytest.mark.parametrize(
    "update",
    [
        {"raw_invoice_dump": {"line_items": []}},
        {"billing_api_response": {"total": 0.42}},
        {"workspace_billing_report": "unredacted"},
        {"payment_method": "card"},
        {"billing_account_secret": "secret-value"},
        {"credential": "secret-value"},
        {"api_key": "secret-value"},
        {"customer_id": "cus_123"},
        {"cost_per_success": 0.1},
        {"pass_at_k_cost": 0.2},
        {"ROI": "positive"},
        {"economic_lift": "claimed"},
        {"result_path": "outputs/cluster3/matrix.jsonl"},
    ],
)
def test_private_billing_and_economic_fields_are_rejected(
    update: dict[str, object],
) -> None:
    record = _record()
    record.update(update)

    with pytest.raises((BillingReconciliationError, ValueError)):
        validate_billing_report_record(record)


@pytest.mark.parametrize(
    "update",
    [
        {"report_source": "billing_api_response"},
        {"report_source": "modal_billing_cli"},
        {"report_id": "billingAPIResponse"},
        {"report_version": "invoice_dump"},
        {"report_version": "externalPricingFetch"},
        {"experiment_id": "user@example.com"},
        {"run_id": "user@example.com"},
        {"app_tag": "user@example.com"},
        {"currency": "EUR"},
        {"total_cost": -0.01},
        {"total_cost": "0.42"},
        {"total_cost": True},
        {"redacted_report_hash": None},
        {"billing_report_redacted_sha256": "b" * 64},
        {
            "billing_time_window_start_utc": "2026-06-04T00:06:00Z",
            "billing_time_window_end_utc": "2026-06-04T00:05:00Z",
        },
        {
            "billing_time_window_start_utc": "2026-06-04T00:05:00Z",
            "billing_time_window_end_utc": "2026-06-04T00:05:00Z",
        },
        {"attribution_method": "cost_per_success"},
        {"attribution_confidence": "exact"},
    ],
)
def test_malformed_static_report_records_are_rejected(
    update: dict[str, object],
) -> None:
    record = _record()
    record.update(update)

    with pytest.raises((BillingReconciliationError, ValueError)):
        validate_billing_report_record(record)


def test_write_path_rejects_outputs_mutation(tmp_path: Path) -> None:
    report_path = tmp_path / "billing.json"
    write_path = tmp_path / "outputs" / "actual_billing.json"
    report_path.write_text(json.dumps([_record()]), encoding="utf-8")

    with pytest.raises(BillingReconciliationError, match="outputs"):
        dry_run_reconciliation(
            report_path,
            experiment_id="exp",
            run_id="run",
            time_window=("2026-06-04T00:01:00Z", "2026-06-04T00:02:00Z"),
            dry_run=False,
            write_path=write_path,
            fsync=False,
        )

    assert not write_path.exists()


def test_billing_windows_use_exclusive_end_semantics() -> None:
    result = reconcile_billing_records_to_run(
        [_record()],
        experiment_id="exp",
        run_id="run",
        time_window=("2026-06-04T00:05:00Z", "2026-06-04T00:10:00Z"),
    )

    assert result.metadata.actual_billing_status == "not_reconciled"
    assert result.candidate_record_count == 0


def test_billing_reconciliation_module_has_no_execution_clients() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {
        "boto3",
        "google",
        "httpx",
        "modal",
        "requests",
        "stripe",
        "subprocess",
        "urllib",
    }
    forbidden_subprocess_calls = {"run", "Popen", "check_call", "check_output"}
    forbidden_network_calls = {"urlopen", "request", "get", "post"}
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in forbidden_imports:
                    violations.append(f"import:{node.lineno}:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in forbidden_imports:
                violations.append(f"import-from:{node.lineno}:{node.module}")
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            root = name.split(".", maxsplit=1)[0]
            leaf = name.rsplit(".", maxsplit=1)[-1]
            if root == "subprocess" and leaf in forbidden_subprocess_calls:
                violations.append(f"call:{node.lineno}:{name}")
            if root in {"requests", "httpx", "urllib"} and leaf in forbidden_network_calls:
                violations.append(f"call:{node.lineno}:{name}")

    assert violations == []


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _record(**updates: object) -> dict[str, object]:
    record: dict[str, object] = {
        "report_id": "redacted-report-1",
        "report_source": "redacted_static_export",
        "report_version": "static-v1",
        "billing_time_window_start_utc": "2026-06-04T00:00:00Z",
        "billing_time_window_end_utc": "2026-06-04T00:05:00Z",
        "currency": "USD",
        "total_cost": 0.42,
        "experiment_id": "exp",
        "run_id": "run",
        "app_tag": "tritongen-exp-run",
        "attribution_method": "app_tag_and_time_window",
        "attribution_confidence": "high",
        "redacted_report_hash": "a" * 64,
    }
    for key, value in updates.items():
        if value is None:
            record.pop(key, None)
        else:
            record[key] = value
    return record
