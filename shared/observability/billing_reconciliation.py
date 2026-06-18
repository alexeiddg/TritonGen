"""Static, redacted billing reconciliation helpers.

O5b is deliberately post-hoc and local-only. This module parses already
redacted/static report fixtures and converts matching records into bounded
observability actual-billing metadata. It does not query billing systems, invoke
Modal, inspect credentials, or mutate scientific result rows.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shared.observability.redaction import reject_forbidden_observability_payload
from shared.observability.schema import (
    ObservabilityActualBillingReconciliation,
    canonical_json_bytes,
)

BillingTimeWindow = tuple[str, str]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,79}$")

_ALLOWED_RECORD_KEYS = {
    "report_id",
    "report_source",
    "report_version",
    "billing_time_window_start_utc",
    "billing_time_window_end_utc",
    "currency",
    "total_cost",
    "experiment_id",
    "run_id",
    "app_tag",
    "attribution_method",
    "attribution_confidence",
    "redacted_report_hash",
    "billing_report_redacted_sha256",
}
_REQUIRED_RECORD_KEYS = {
    "report_id",
    "report_source",
    "report_version",
    "billing_time_window_start_utc",
    "billing_time_window_end_utc",
    "currency",
    "total_cost",
    "attribution_method",
    "attribution_confidence",
}
_OPTIONAL_ID_KEYS = {"experiment_id", "run_id", "app_tag"}
_REPORT_SOURCE_TO_BILLING_SOURCE = {
    "redacted_modal_billing_report": "approved_modal_billing_cli_report",
    "redacted_static_export": "approved_exported_static_report",
    "redacted_provider_static_export": "approved_provider_static_report",
    "test_fixture": "test_fixture",
}
_ALLOWED_ATTRIBUTION_METHODS = {
    "app_tag",
    "time_window",
    "app_tag_and_time_window",
    "redacted_static_report",
    "test_fixture",
}
_ALLOWED_ATTRIBUTION_CONFIDENCE = {"low", "medium", "high"}
_FORBIDDEN_REPORT_LABEL_PATTERNS = {
    "billing_api_response",
    "pricing_api_response",
    "cloud_invoice_dump",
    "external_pricing_fetch",
    "full_billing_api_response",
    "invoice_dump",
    "modal_billing",
    "provider_billing",
    "workspace_billing_report",
    "cost_per_success",
    "pass_at_k_cost",
    "roi",
    "economic_lift",
}


class BillingReconciliationError(ValueError):
    """Raised when static billing reconciliation input is unsafe or inconsistent."""


@dataclass(frozen=True)
class BillingReconciliationResult:
    """Reconciliation outcome for one target run."""

    metadata: ObservabilityActualBillingReconciliation
    total_record_count: int
    matched_record_count: int
    candidate_record_count: int


@dataclass(frozen=True)
class BillingReconciliationDryRun:
    """Dry-run/write outcome for a local static reconciliation request."""

    result: BillingReconciliationResult
    dry_run: bool
    write_path: str | None
    wrote_file: bool


def parse_redacted_billing_report(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Parse a local JSON/JSONL static billing report into validated records."""

    report_path = Path(path)
    raw = report_path.read_text(encoding="utf-8")
    if report_path.suffix == ".jsonl":
        payload = _load_jsonl(raw)
    else:
        payload = json.loads(raw)

    if isinstance(payload, Mapping):
        if "records" in payload:
            records = payload["records"]
        else:
            records = [payload]
    else:
        records = payload

    if not isinstance(records, Sequence) or isinstance(
        records, (str, bytes, bytearray, memoryview)
    ):
        raise BillingReconciliationError("billing report must contain a record list")
    validated = tuple(validate_billing_report_record(record) for record in records)
    if not validated:
        raise BillingReconciliationError("billing report must contain at least one record")
    return validated


def validate_billing_report_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one redacted/static report record and return normalized fields."""

    if not isinstance(record, Mapping):
        raise BillingReconciliationError("billing report records must be objects")
    reject_forbidden_observability_payload(record)

    keys = set(record)
    unsupported = keys - _ALLOWED_RECORD_KEYS
    if unsupported:
        raise BillingReconciliationError(
            "billing report record contains unsupported fields: "
            + ", ".join(sorted(unsupported))
        )
    missing = _REQUIRED_RECORD_KEYS - keys
    if missing:
        raise BillingReconciliationError(
            "billing report record missing required fields: "
            + ", ".join(sorted(missing))
        )

    report_hash = _extract_redacted_report_hash(record)
    normalized: dict[str, Any] = {
        "report_id": _safe_label(record["report_id"], "report_id"),
        "report_source": _report_source(record["report_source"]),
        "report_version": _safe_label(record["report_version"], "report_version"),
        "billing_time_window_start_utc": _validate_utc(
            record["billing_time_window_start_utc"],
            "billing_time_window_start_utc",
        ),
        "billing_time_window_end_utc": _validate_utc(
            record["billing_time_window_end_utc"],
            "billing_time_window_end_utc",
        ),
        "currency": _currency(record["currency"]),
        "total_cost": _cost(record["total_cost"]),
        "attribution_method": _attribution_method(record["attribution_method"]),
        "attribution_confidence": _attribution_confidence(
            record["attribution_confidence"]
        ),
        "billing_report_redacted_sha256": report_hash,
    }
    if _parse_utc(normalized["billing_time_window_end_utc"]) <= _parse_utc(
        normalized["billing_time_window_start_utc"]
    ):
        raise BillingReconciliationError("billing time window end must be after start")

    for key in _OPTIONAL_ID_KEYS:
        normalized[key] = _optional_label(record.get(key), key)

    return normalized


def reconcile_billing_records_to_run(
    records: Sequence[Mapping[str, Any]],
    experiment_id: str,
    run_id: str,
    time_window: BillingTimeWindow | Mapping[str, str],
) -> BillingReconciliationResult:
    """Reconcile validated static billing records to one target run."""

    target_experiment_id = _non_empty_label(experiment_id, "experiment_id")
    target_run_id = _non_empty_label(run_id, "run_id")
    target_window = _normalize_time_window(time_window)
    validated_records = tuple(validate_billing_report_record(record) for record in records)

    candidates = tuple(
        record
        for record in validated_records
        if _windows_overlap(
            (
                record["billing_time_window_start_utc"],
                record["billing_time_window_end_utc"],
            ),
            target_window,
        )
        and _could_belong_to_target(record, target_experiment_id, target_run_id)
    )
    exact_matches = tuple(
        record
        for record in candidates
        if record["experiment_id"] == target_experiment_id
        and record["run_id"] == target_run_id
    )

    if len(exact_matches) == 1:
        metadata = build_actual_billing_reconciliation_metadata(
            exact_matches[0],
            reconciled_at_utc=_utc_now(),
            notes="redacted static report matched by run id",
        )
    elif exact_matches or candidates:
        metadata = build_actual_billing_reconciliation_metadata(
            None,
            status="attribution_limited",
            notes="static report attribution limited by missing or ambiguous run tags",
        )
    else:
        metadata = build_actual_billing_reconciliation_metadata(
            None,
            status="not_reconciled",
            notes="no matching redacted static report record",
        )

    return BillingReconciliationResult(
        metadata=metadata,
        total_record_count=len(validated_records),
        matched_record_count=len(exact_matches),
        candidate_record_count=len(candidates),
    )


def build_actual_billing_reconciliation_metadata(
    record: Mapping[str, Any] | None,
    *,
    status: str = "reconciled",
    reconciled_at_utc: str | None = None,
    notes: str | None = None,
) -> ObservabilityActualBillingReconciliation:
    """Build O5a actual-billing metadata from a validated static record."""

    if status == "reconciled":
        if record is None:
            raise BillingReconciliationError("reconciled metadata requires a record")
        validated = validate_billing_report_record(record)
        return ObservabilityActualBillingReconciliation(
            actual_billing_available=True,
            actual_billing_status="reconciled",
            actual_billing_reconciled_at_utc=reconciled_at_utc or _utc_now(),
            billing_source=_REPORT_SOURCE_TO_BILLING_SOURCE[validated["report_source"]],
            billing_source_version=validated["report_version"],
            billing_time_window_start_utc=validated["billing_time_window_start_utc"],
            billing_time_window_end_utc=validated["billing_time_window_end_utc"],
            billing_attribution_method=validated["attribution_method"],
            billing_attribution_confidence=validated["attribution_confidence"],
            actual_total_cost=validated["total_cost"],
            actual_currency=validated["currency"],
            billing_report_redacted_sha256=validated["billing_report_redacted_sha256"],
            billing_reconciliation_notes=notes,
        )

    if record is not None:
        raise BillingReconciliationError("unreconciled metadata must not include a record")
    if status not in {
        "not_reconciled",
        "attribution_limited",
        "unavailable",
        "pending_approval",
        "approved_not_queried",
        "failed",
    }:
        raise BillingReconciliationError("unsupported actual billing status")
    return ObservabilityActualBillingReconciliation(
        actual_billing_available=False,
        actual_billing_status=status,
        billing_reconciliation_notes=notes,
    )


def dry_run_reconciliation(
    report_path: str | Path,
    *,
    experiment_id: str,
    run_id: str,
    time_window: BillingTimeWindow | Mapping[str, str],
    dry_run: bool = True,
    write_path: str | Path | None = None,
    fsync: bool = True,
) -> BillingReconciliationDryRun:
    """Run local reconciliation and optionally write bounded metadata."""

    records = parse_redacted_billing_report(report_path)
    result = reconcile_billing_records_to_run(
        records,
        experiment_id=experiment_id,
        run_id=run_id,
        time_window=time_window,
    )
    if dry_run:
        return BillingReconciliationDryRun(
            result=result,
            dry_run=True,
            write_path=str(write_path) if write_path is not None else None,
            wrote_file=False,
        )
    if write_path is None:
        raise BillingReconciliationError("non-dry-run reconciliation requires write_path")

    _write_reconciliation_metadata_atomic(write_path, result.metadata, fsync=fsync)
    return BillingReconciliationDryRun(
        result=result,
        dry_run=False,
        write_path=str(write_path),
        wrote_file=True,
    )


def _load_jsonl(raw: str) -> list[Any]:
    records = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise BillingReconciliationError(
                f"invalid JSONL billing report line {line_number}"
            ) from exc
    return records


def _extract_redacted_report_hash(record: Mapping[str, Any]) -> str:
    primary = record.get("redacted_report_hash")
    schema_name = record.get("billing_report_redacted_sha256")
    if primary is None and schema_name is None:
        raise BillingReconciliationError("billing report requires redacted report hash")
    if primary is not None and schema_name is not None and primary != schema_name:
        raise BillingReconciliationError("redacted report hash aliases must match")
    value = primary if primary is not None else schema_name
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value.lower()):
        raise BillingReconciliationError("redacted report hash must be sha256 hex")
    return value.lower()


def _report_source(value: Any) -> str:
    if not isinstance(value, str) or value not in _REPORT_SOURCE_TO_BILLING_SOURCE:
        raise BillingReconciliationError("report_source must be an approved static source")
    return value


def _attribution_method(value: Any) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_ATTRIBUTION_METHODS:
        raise BillingReconciliationError("unsupported attribution_method")
    return value


def _attribution_confidence(value: Any) -> str:
    if not isinstance(value, str) or value not in _ALLOWED_ATTRIBUTION_CONFIDENCE:
        raise BillingReconciliationError("unsupported attribution_confidence")
    return value


def _currency(value: Any) -> str:
    if value != "USD":
        raise BillingReconciliationError("billing report currency must be USD")
    return value


def _cost(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BillingReconciliationError("total_cost must be a finite number")
    if not math.isfinite(value) or value < 0:
        raise BillingReconciliationError("total_cost must be finite and nonnegative")
    return float(value)


def _safe_label(value: Any, field: str) -> str:
    value = _non_empty_label(value, field)
    if not _SAFE_LABEL_RE.fullmatch(value):
        raise BillingReconciliationError(f"{field} must be a bounded safe identifier")
    if field in {"report_id", "report_version"}:
        _reject_forbidden_report_label(value, field)
    reject_forbidden_observability_payload({field: value})
    return value


def _optional_label(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _safe_label(value, field)


def _non_empty_label(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BillingReconciliationError(f"{field} must be a non-empty string")
    return value


def _reject_forbidden_report_label(value: str, field: str) -> None:
    normalized = _normalize_label(value)
    compact = normalized.replace("_", "")
    for pattern in _FORBIDDEN_REPORT_LABEL_PATTERNS:
        if pattern in normalized or pattern.replace("_", "") in compact:
            raise BillingReconciliationError(
                f"{field} must not name billing API, invoice, external pricing, "
                "or economic claim sources"
            )


def _normalize_label(value: str) -> str:
    acronym_split = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", value.strip())
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", acronym_split)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _validate_utc(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        raise BillingReconciliationError(f"{field} must be RFC3339 UTC ending with Z")
    try:
        _parse_utc(value)
    except ValueError as exc:
        raise BillingReconciliationError(f"{field} must be a valid UTC timestamp") from exc
    return value


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


def _normalize_time_window(
    time_window: BillingTimeWindow | Mapping[str, str],
) -> BillingTimeWindow:
    if isinstance(time_window, Mapping):
        start = time_window.get("start_utc") or time_window.get(
            "billing_time_window_start_utc"
        )
        end = time_window.get("end_utc") or time_window.get("billing_time_window_end_utc")
    elif isinstance(time_window, Sequence) and not isinstance(
        time_window, (str, bytes, bytearray, memoryview)
    ):
        if len(time_window) != 2:
            raise BillingReconciliationError("time_window must contain start and end")
        start, end = time_window
    else:
        raise BillingReconciliationError("time_window must be a mapping or pair")

    normalized = (
        _validate_utc(start, "time_window_start_utc"),
        _validate_utc(end, "time_window_end_utc"),
    )
    if _parse_utc(normalized[1]) <= _parse_utc(normalized[0]):
        raise BillingReconciliationError("time_window end must be after start")
    return normalized


def _windows_overlap(left: BillingTimeWindow, right: BillingTimeWindow) -> bool:
    left_start, left_end = (_parse_utc(left[0]), _parse_utc(left[1]))
    right_start, right_end = (_parse_utc(right[0]), _parse_utc(right[1]))
    return left_start < right_end and right_start < left_end


def _could_belong_to_target(
    record: Mapping[str, Any],
    experiment_id: str,
    run_id: str,
) -> bool:
    record_experiment_id = record.get("experiment_id")
    record_run_id = record.get("run_id")
    if record_experiment_id is not None and record_experiment_id != experiment_id:
        return False
    if record_run_id is not None and record_run_id != run_id:
        return False
    return True


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_reconciliation_metadata_atomic(
    write_path: str | Path,
    metadata: ObservabilityActualBillingReconciliation,
    *,
    fsync: bool,
) -> None:
    path = Path(write_path)
    if "outputs" in path.parts or "mlruns" in path.parts:
        raise BillingReconciliationError("O5b writes must not target outputs or mlruns")
    if path.exists() and not path.is_file():
        raise BillingReconciliationError("write_path points at an existing non-file path")
    validated = ObservabilityActualBillingReconciliation.model_validate(
        metadata.model_dump(mode="json")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(canonical_json_bytes(validated))
            tmp.flush()
            if fsync:
                os.fsync(tmp.fileno())
        tmp_path.replace(path)
        if fsync:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except BaseException:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise
