from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from shared.observability.billing_modal_collection import (
    DEFAULT_MODAL_BILLING_TAG_NAMES,
    MODAL_BILLING_REPORT_SOURCE,
    ModalBillingCollectionError,
    ModalBillingQuery,
    build_modal_billing_report_command,
    build_modal_billing_report_commands,
    collect_and_sanitize_modal_billing_report_cli,
    collect_modal_billing_report_cli,
    sanitize_modal_billing_report,
    split_modal_billing_query,
    write_redacted_modal_billing_report_jsonl,
)
from shared.observability.billing_reconciliation import (
    parse_redacted_billing_report,
    reconcile_billing_records_to_run,
    validate_billing_report_record,
)


def test_command_construction_uses_authorized_window_resolution_and_tags() -> None:
    query = _query()

    command = build_modal_billing_report_command(
        query,
        python_executable=".venv/bin/python",
    )

    assert command == (
        ".venv/bin/python",
        "-m",
        "modal",
        "billing",
        "report",
        "--start",
        "2026-05-01",
        "--end",
        "2026-06-05",
        "--resolution",
        "h",
        "--tag-names",
        "project,experiment_id,run_id,cluster,phase",
        "--json",
    )


def test_hourly_query_splits_into_modal_seven_day_chunks() -> None:
    chunks = split_modal_billing_query(_query())

    assert [
        (chunk.time_window_start_utc, chunk.time_window_end_utc)
        for chunk in chunks
    ] == [
        ("2026-05-01T00:00:00Z", "2026-05-08T00:00:00Z"),
        ("2026-05-08T00:00:00Z", "2026-05-15T00:00:00Z"),
        ("2026-05-15T00:00:00Z", "2026-05-22T00:00:00Z"),
        ("2026-05-22T00:00:00Z", "2026-05-29T00:00:00Z"),
        ("2026-05-29T00:00:00Z", "2026-06-05T00:00:00Z"),
    ]
    commands = build_modal_billing_report_commands(
        _query(),
        python_executable=".venv/bin/python",
    )
    assert len(commands) == 5
    assert commands[0][5:9] == (
        "--start",
        "2026-05-01",
        "--end",
        "2026-05-08",
    )
    assert commands[-1][5:9] == (
        "--start",
        "2026-05-29",
        "--end",
        "2026-06-05",
    )


def test_collect_cli_uses_injected_runner_and_writes_raw_json(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, ...]] = []
    raw_path = tmp_path / "modal_raw.json"

    def fake_runner(command: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(_modal_rows()))

    command = collect_modal_billing_report_cli(
        _query(),
        raw_path,
        python_executable=".venv/bin/python",
        runner=fake_runner,
    )

    assert calls == [command]
    assert raw_path.exists()
    assert json.loads(raw_path.read_text(encoding="utf-8")) == _modal_rows()


def test_collect_and_sanitize_writes_redacted_o5b_jsonl(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "modal_raw.json"
    redacted_path = tmp_path / "modal_redacted.jsonl"

    def fake_runner(command: tuple[str, ...], **_: object) -> subprocess.CompletedProcess[str]:
        rows = []
        if command[6] == "2026-05-01":
            rows = [_modal_row(cost="0.12", interval_start="2026-05-01T00:00:00Z")]
        elif command[6] == "2026-05-08":
            rows = [_modal_row(cost="0.30", interval_start="2026-05-08T00:00:00Z")]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(rows))

    result = collect_and_sanitize_modal_billing_report_cli(
        _query(),
        raw_report_path=raw_path,
        redacted_report_path=redacted_path,
        python_executable=".venv/bin/python",
        runner=fake_runner,
    )

    assert result.raw_record_count == 2
    assert result.redacted_record_count == 1
    assert len(result.commands) == 5
    assert result.time_window_start_utc == "2026-05-01T00:00:00Z"
    assert result.time_window_end_utc == "2026-06-05T00:00:00Z"
    assert result.resolution == "h"
    assert result.tag_names == DEFAULT_MODAL_BILLING_TAG_NAMES
    assert redacted_path.exists()
    records = parse_redacted_billing_report(redacted_path)
    assert len(records) == 1
    assert records[0]["report_source"] == MODAL_BILLING_REPORT_SOURCE
    assert records[0]["total_cost"] == 0.42
    assert records[0]["experiment_id"] == "exp"
    assert records[0]["run_id"] == "run"
    assert result.redacted_report_hash


def test_modal_json_sanitizes_to_o5b_static_format() -> None:
    records = sanitize_modal_billing_report(
        json.dumps(_modal_rows()),
        _query(),
        report_generated_at_utc="2026-06-05T00:00:00Z",
    )

    assert len(records) == 1
    record = validate_billing_report_record(records[0])
    assert record["report_source"] == "redacted_modal_billing_report"
    assert record["report_version"] == "cli.v1"
    assert record["billing_time_window_start_utc"] == "2026-05-01T00:00:00Z"
    assert record["billing_time_window_end_utc"] == "2026-06-05T00:00:00Z"
    assert record["currency"] == "USD"
    assert record["total_cost"] == 0.42
    assert record["attribution_method"] == "app_tag_and_time_window"
    assert record["attribution_confidence"] == "high"


def test_redacted_report_validates_through_o5b_reconciliation(tmp_path: Path) -> None:
    redacted_path = tmp_path / "modal_redacted.jsonl"
    records = sanitize_modal_billing_report(json.dumps(_modal_rows()), _query())
    write_redacted_modal_billing_report_jsonl(records, redacted_path, fsync=False)

    parsed = parse_redacted_billing_report(redacted_path)
    result = reconcile_billing_records_to_run(
        parsed,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-05-02T00:00:00Z", "2026-05-02T01:00:00Z"),
    )

    assert result.metadata.actual_billing_status == "reconciled"
    assert result.metadata.billing_source == "approved_modal_billing_cli_report"
    assert result.metadata.actual_total_cost == 0.42


def test_missing_run_id_or_experiment_id_tags_become_attribution_limited() -> None:
    rows = [
        _modal_row(
            cost="0.25",
            tags={
                "project": "tritongen",
                "cluster": "cluster3",
                "phase": "phase14",
            },
        )
    ]
    records = sanitize_modal_billing_report(json.dumps(rows), _query())

    result = reconcile_billing_records_to_run(
        records,
        experiment_id="exp",
        run_id="run",
        time_window=("2026-05-02T00:00:00Z", "2026-05-02T01:00:00Z"),
    )

    assert result.metadata.actual_billing_status == "attribution_limited"
    assert result.matched_record_count == 0
    assert result.candidate_record_count == 1


def test_raw_modal_private_fields_do_not_survive_redaction() -> None:
    rows = [
        _modal_row(
            object_id="raw-object-id",
            description="private app description",
            environment_name="private-workspace-env",
            payment_method="card",
            customer_id="cus_123",
            ROI="claimed",
        )
    ]

    [record] = sanitize_modal_billing_report(json.dumps(rows), _query())
    encoded = json.dumps(record, sort_keys=True)

    assert "raw-object-id" not in encoded
    assert "private app description" not in encoded
    assert "private-workspace-env" not in encoded
    assert "payment_method" not in encoded
    assert "customer_id" not in encoded
    assert "ROI" not in encoded


@pytest.mark.parametrize(
    "update",
    [
        {"cost": True},
        {"cost": "-0.01"},
        {"cost": "NaN"},
        {"interval_start": "2026-06-05T00:00:00Z"},
        {"tags": {"project": "user@example.com"}},
        {"tags": {"project": "tritongen-" + "x" * 80}},
    ],
)
def test_unsafe_modal_rows_fail_closed(update: dict[str, object]) -> None:
    rows = [_modal_row(**update)]

    with pytest.raises((ModalBillingCollectionError, ValueError)):
        sanitize_modal_billing_report(json.dumps(rows), _query())


def test_query_requires_complete_explicit_utc_window() -> None:
    with pytest.raises(ModalBillingCollectionError, match="ending with Z"):
        ModalBillingQuery("2026-05-01", "2026-06-05T00:00:00Z")

    with pytest.raises(ModalBillingCollectionError, match="after start"):
        ModalBillingQuery("2026-05-01T00:00:00Z", "2026-05-01T00:00:00Z")


def test_artifact_paths_reject_outputs_and_wrong_suffix(tmp_path: Path) -> None:
    with pytest.raises(ModalBillingCollectionError, match=".jsonl"):
        write_redacted_modal_billing_report_jsonl([], tmp_path / "redacted.json")

    with pytest.raises(ModalBillingCollectionError, match="outputs"):
        write_redacted_modal_billing_report_jsonl(
            [],
            tmp_path / "outputs" / "redacted.jsonl",
        )


def _query() -> ModalBillingQuery:
    return ModalBillingQuery(
        time_window_start_utc="2026-05-01T00:00:00Z",
        time_window_end_utc="2026-06-05T00:00:00Z",
        resolution="h",
        tag_names=DEFAULT_MODAL_BILLING_TAG_NAMES,
    )


def _modal_rows() -> list[dict[str, object]]:
    return [
        _modal_row(cost="0.12", interval_start="2026-05-08T00:00:00Z"),
        _modal_row(cost="0.30", interval_start="2026-05-08T01:00:00Z"),
    ]


def _modal_row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "object_id": "ob-123",
        "description": "private modal object description",
        "environment_name": "private-env",
        "interval_start": "2026-05-01T00:00:00Z",
        "cost": "0.12",
        "tags": {
            "project": "tritongen",
            "experiment_id": "exp",
            "run_id": "run",
            "cluster": "cluster3",
            "phase": "phase14",
            "extra_private_tag": "must-not-survive",
        },
    }
    row.update(updates)
    return row
