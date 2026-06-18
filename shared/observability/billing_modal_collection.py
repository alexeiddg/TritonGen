"""Authorized Modal billing report collection and redaction helpers.

O5c is the first package that may invoke the Modal billing report surface, but
only when an explicit approval packet supplies a complete UTC window. Importing
this module is inert: no Modal package is imported and no CLI/API call runs until
the collection function is called.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from shared.observability.billing_reconciliation import (
    validate_billing_report_record,
)
from shared.observability.schema import canonical_json_bytes

DEFAULT_MODAL_BILLING_TAG_NAMES = (
    "project",
    "experiment_id",
    "run_id",
    "cluster",
    "phase",
)
MODAL_BILLING_REPORT_SOURCE = "redacted_modal_billing_report"
MODAL_BILLING_REPORT_VERSION = "cli.v1"

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_SAFE_TAG_KEYS = frozenset(DEFAULT_MODAL_BILLING_TAG_NAMES)
_CLI_DATE_FORMAT = "%Y-%m-%d"
_MAX_RAW_REPORT_BYTES = 25 * 1024 * 1024
_Runner = Callable[..., subprocess.CompletedProcess[str]]


class ModalBillingCollectionError(ValueError):
    """Raised when Modal billing collection or redaction cannot proceed safely."""


@dataclass(frozen=True)
class ModalBillingQuery:
    """Bounded, explicit Modal billing report query packet."""

    time_window_start_utc: str
    time_window_end_utc: str
    resolution: str = "h"
    tag_names: tuple[str, ...] = DEFAULT_MODAL_BILLING_TAG_NAMES

    def __post_init__(self) -> None:
        start = _parse_utc(self.time_window_start_utc, "time_window_start_utc")
        end = _parse_utc(self.time_window_end_utc, "time_window_end_utc")
        if end <= start:
            raise ModalBillingCollectionError("Modal billing end must be after start")
        if self.resolution not in {"h", "d"}:
            raise ModalBillingCollectionError("Modal billing resolution must be h or d")
        if not self.tag_names:
            raise ModalBillingCollectionError("Modal billing tag_names must be non-empty")
        unsupported = tuple(tag for tag in self.tag_names if tag not in _SAFE_TAG_KEYS)
        if unsupported:
            raise ModalBillingCollectionError(
                "unsupported Modal billing tag_names: " + ", ".join(unsupported)
            )


@dataclass(frozen=True)
class ModalBillingCollectionResult:
    """Local result of a Modal billing report collection and redaction."""

    commands: tuple[tuple[str, ...], ...]
    raw_report_path: str
    redacted_report_path: str
    redacted_report_hash: str
    report_generated_at_utc: str
    time_window_start_utc: str
    time_window_end_utc: str
    resolution: str
    tag_names: tuple[str, ...]
    raw_record_count: int
    redacted_record_count: int


def build_modal_billing_report_command(
    query: ModalBillingQuery,
    *,
    python_executable: str = sys.executable,
) -> tuple[str, ...]:
    """Build the exact CLI command without executing it."""

    _ = ModalBillingQuery(
        time_window_start_utc=query.time_window_start_utc,
        time_window_end_utc=query.time_window_end_utc,
        resolution=query.resolution,
        tag_names=query.tag_names,
    )
    return (
        python_executable,
        "-m",
        "modal",
        "billing",
        "report",
        "--start",
        _cli_time(query.time_window_start_utc),
        "--end",
        _cli_time(query.time_window_end_utc),
        "--resolution",
        query.resolution,
        "--tag-names",
        ",".join(query.tag_names),
        "--json",
    )


def split_modal_billing_query(
    query: ModalBillingQuery,
    *,
    max_hourly_span_days: int = 7,
) -> tuple[ModalBillingQuery, ...]:
    """Split a query into Modal-compatible chunks without changing coverage."""

    if query.resolution != "h":
        return (query,)
    if max_hourly_span_days <= 0:
        raise ModalBillingCollectionError("max_hourly_span_days must be positive")

    start = _parse_utc(query.time_window_start_utc, "time_window_start_utc")
    end = _parse_utc(query.time_window_end_utc, "time_window_end_utc")
    span = timedelta(days=max_hourly_span_days)
    chunks: list[ModalBillingQuery] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + span, end)
        chunks.append(
            ModalBillingQuery(
                time_window_start_utc=_format_utc(cursor),
                time_window_end_utc=_format_utc(chunk_end),
                resolution=query.resolution,
                tag_names=query.tag_names,
            )
        )
        cursor = chunk_end
    return tuple(chunks)


def build_modal_billing_report_commands(
    query: ModalBillingQuery,
    *,
    python_executable: str = sys.executable,
) -> tuple[tuple[str, ...], ...]:
    """Build all CLI commands needed for an approved query window."""

    return tuple(
        build_modal_billing_report_command(
            chunk,
            python_executable=python_executable,
        )
        for chunk in split_modal_billing_query(query)
    )


def collect_modal_billing_report_cli(
    query: ModalBillingQuery,
    raw_report_path: str | Path,
    *,
    python_executable: str = sys.executable,
    runner: _Runner = subprocess.run,
    timeout_s: int = 300,
) -> tuple[str, ...]:
    """Run the approved Modal CLI report command and write raw JSON bytes locally."""

    command = build_modal_billing_report_command(
        query,
        python_executable=python_executable,
    )
    path = Path(raw_report_path)
    _validate_artifact_path(path, expected_suffix=".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = runner(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        raise ModalBillingCollectionError(
            "Modal billing report command failed: " + (proc.stderr or "").strip()
        )
    raw = proc.stdout
    if not raw.strip():
        raise ModalBillingCollectionError("Modal billing report returned empty output")
    raw_bytes = raw.encode("utf-8")
    if len(raw_bytes) > _MAX_RAW_REPORT_BYTES:
        raise ModalBillingCollectionError("Modal billing report exceeds size limit")
    _write_bytes_atomic(path, raw_bytes, fsync=True)
    return command


def collect_modal_billing_report_cli_chunked(
    query: ModalBillingQuery,
    raw_report_path: str | Path,
    *,
    python_executable: str = sys.executable,
    runner: _Runner = subprocess.run,
    timeout_s: int = 300,
) -> tuple[tuple[str, ...], ...]:
    """Run one or more Modal CLI report commands and write combined raw JSON."""

    path = Path(raw_report_path)
    _validate_artifact_path(path, expected_suffix=".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    commands: list[tuple[str, ...]] = []
    for chunk in split_modal_billing_query(query):
        command = build_modal_billing_report_command(
            chunk,
            python_executable=python_executable,
        )
        commands.append(command)
        proc = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            raise ModalBillingCollectionError(
                "Modal billing report command failed: " + (proc.stderr or "").strip()
            )
        if not proc.stdout.strip():
            raise ModalBillingCollectionError("Modal billing report returned empty output")
        all_rows.extend(_modal_rows(proc.stdout))

    raw_bytes = json.dumps(
        all_rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if len(raw_bytes) > _MAX_RAW_REPORT_BYTES:
        raise ModalBillingCollectionError("Modal billing report exceeds size limit")
    _write_bytes_atomic(path, raw_bytes, fsync=True)
    return tuple(commands)


def sanitize_modal_billing_report(
    raw_report: str | bytes | Mapping[str, Any] | Sequence[Any],
    query: ModalBillingQuery,
    *,
    report_generated_at_utc: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Convert Modal report JSON into the O5b redacted static report format."""

    generated_at = report_generated_at_utc or _utc_now()
    _parse_utc(generated_at, "report_generated_at_utc")
    query_start = _parse_utc(query.time_window_start_utc, "time_window_start_utc")
    query_end = _parse_utc(query.time_window_end_utc, "time_window_end_utc")
    rows = _modal_rows(raw_report)
    grouped: dict[tuple[str | None, str | None, str | None], Decimal] = {}
    for row in rows:
        interval_start = _modal_interval_start(row)
        if interval_start < query_start or interval_start >= query_end:
            raise ModalBillingCollectionError(
                "Modal billing row interval_start falls outside query window"
            )
        cost = _modal_cost(row)
        if cost == 0:
            continue
        tags = _safe_modal_tags(row.get("tags"))
        experiment_id = tags.get("experiment_id")
        run_id = tags.get("run_id")
        app_tag = _app_tag(tags)
        key = (experiment_id, run_id, app_tag)
        grouped[key] = grouped.get(key, Decimal("0")) + cost

    if not grouped:
        return ()

    records: list[dict[str, Any]] = []
    for key, total_cost in sorted(grouped.items(), key=lambda item: _sort_key(item[0])):
        experiment_id, run_id, app_tag = key
        base = {
            "report_id": _report_id(query, key),
            "report_source": MODAL_BILLING_REPORT_SOURCE,
            "report_version": MODAL_BILLING_REPORT_VERSION,
            "billing_time_window_start_utc": query.time_window_start_utc,
            "billing_time_window_end_utc": query.time_window_end_utc,
            "currency": "USD",
            "total_cost": _decimal_to_float(total_cost),
            "attribution_method": _attribution_method(experiment_id, run_id, app_tag),
            "attribution_confidence": _attribution_confidence(
                experiment_id,
                run_id,
                app_tag,
            ),
        }
        if experiment_id is not None:
            base["experiment_id"] = experiment_id
        if run_id is not None:
            base["run_id"] = run_id
        if app_tag is not None:
            base["app_tag"] = app_tag

        record_hash = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
        record = dict(base)
        record["redacted_report_hash"] = record_hash
        validated = validate_billing_report_record(record)
        records.append(validated)

    return tuple(records)


def write_redacted_modal_billing_report_jsonl(
    records: Sequence[Mapping[str, Any]],
    redacted_report_path: str | Path,
    *,
    fsync: bool = True,
) -> str:
    """Write validated O5b redacted records as JSONL and return file SHA-256."""

    path = Path(redacted_report_path)
    _validate_artifact_path(path, expected_suffix=".jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for record in records:
        validated = validate_billing_report_record(record)
        lines.append(canonical_json_bytes(validated).decode("utf-8"))
    payload = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    _write_bytes_atomic(path, payload, fsync=fsync)
    return hashlib.sha256(payload).hexdigest()


def collect_and_sanitize_modal_billing_report_cli(
    query: ModalBillingQuery,
    *,
    raw_report_path: str | Path,
    redacted_report_path: str | Path,
    python_executable: str = sys.executable,
    runner: _Runner = subprocess.run,
    timeout_s: int = 300,
) -> ModalBillingCollectionResult:
    """Collect raw Modal JSON, sanitize it, and write a redacted JSONL artifact."""

    commands = collect_modal_billing_report_cli_chunked(
        query,
        raw_report_path,
        python_executable=python_executable,
        runner=runner,
        timeout_s=timeout_s,
    )
    raw_text = Path(raw_report_path).read_text(encoding="utf-8")
    raw_rows = _modal_rows(raw_text)
    report_generated_at_utc = _utc_now()
    records = sanitize_modal_billing_report(
        raw_text,
        query,
        report_generated_at_utc=report_generated_at_utc,
    )
    if not records:
        raise ModalBillingCollectionError("Modal billing report produced no redacted records")
    redacted_hash = write_redacted_modal_billing_report_jsonl(
        records,
        redacted_report_path,
    )
    return ModalBillingCollectionResult(
        commands=commands,
        raw_report_path=str(raw_report_path),
        redacted_report_path=str(redacted_report_path),
        redacted_report_hash=redacted_hash,
        report_generated_at_utc=report_generated_at_utc,
        time_window_start_utc=query.time_window_start_utc,
        time_window_end_utc=query.time_window_end_utc,
        resolution=query.resolution,
        tag_names=query.tag_names,
        raw_record_count=len(raw_rows),
        redacted_record_count=len(records),
    )


def _modal_rows(
    raw_report: str | bytes | Mapping[str, Any] | Sequence[Any],
) -> tuple[dict[str, Any], ...]:
    if isinstance(raw_report, bytes):
        raw_report = raw_report.decode("utf-8")
    if isinstance(raw_report, str):
        try:
            payload = json.loads(raw_report)
        except json.JSONDecodeError as exc:
            raise ModalBillingCollectionError("Modal billing report is not valid JSON") from exc
    else:
        payload = raw_report

    if isinstance(payload, Mapping):
        for key in ("records", "rows", "items", "data", "report"):
            if key in payload:
                payload = payload[key]
                break
        else:
            payload = (payload,)
    if not isinstance(payload, Sequence) or isinstance(
        payload,
        (str, bytes, bytearray, memoryview),
    ):
        raise ModalBillingCollectionError("Modal billing report must contain rows")

    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, Mapping):
            raise ModalBillingCollectionError("Modal billing report rows must be objects")
        rows.append(dict(row))
    return tuple(rows)


def _safe_modal_tags(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ModalBillingCollectionError("Modal billing row tags must be objects")
    tags: dict[str, str] = {}
    for key in DEFAULT_MODAL_BILLING_TAG_NAMES:
        tag_value = value.get(key)
        if tag_value is None:
            continue
        if not isinstance(tag_value, str):
            raise ModalBillingCollectionError("Modal billing tag values must be strings")
        clean = tag_value.strip()
        if not clean:
            continue
        tags[key] = clean
    return tags


def _app_tag(tags: Mapping[str, str]) -> str | None:
    parts = [
        tags.get("project"),
        tags.get("cluster"),
        tags.get("phase"),
    ]
    present = [part for part in parts if part]
    if not present:
        return None
    return "/".join(present)


def _modal_cost(row: Mapping[str, Any]) -> Decimal:
    value = row.get("cost")
    if value is None:
        raise ModalBillingCollectionError("Modal billing row missing cost")
    if isinstance(value, bool):
        raise ModalBillingCollectionError("Modal billing row cost must be numeric")
    try:
        cost = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ModalBillingCollectionError("Modal billing row cost must be numeric") from exc
    if not cost.is_finite() or cost < 0:
        raise ModalBillingCollectionError(
            "Modal billing row cost must be finite and nonnegative"
        )
    return cost


def _decimal_to_float(value: Decimal) -> float:
    quantized = value.quantize(Decimal("0.000000000001"))
    as_float = float(quantized)
    if not math.isfinite(as_float):
        raise ModalBillingCollectionError("Modal billing total cost is not finite")
    return as_float


def _report_id(
    query: ModalBillingQuery,
    key: tuple[str | None, str | None, str | None],
) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "source": MODAL_BILLING_REPORT_SOURCE,
                "start": query.time_window_start_utc,
                "end": query.time_window_end_utc,
                "resolution": query.resolution,
                "tag_names": list(query.tag_names),
                "key": list(key),
            }
        )
    ).hexdigest()[:24]
    return f"modal-{digest}"


def _attribution_method(
    experiment_id: str | None,
    run_id: str | None,
    app_tag: str | None,
) -> str:
    if experiment_id is not None and run_id is not None:
        return "app_tag_and_time_window"
    if app_tag is not None:
        return "app_tag"
    return "time_window"


def _attribution_confidence(
    experiment_id: str | None,
    run_id: str | None,
    app_tag: str | None,
) -> str:
    if experiment_id is not None and run_id is not None:
        return "high"
    if app_tag is not None:
        return "medium"
    return "low"


def _sort_key(key: tuple[str | None, str | None, str | None]) -> tuple[str, str, str]:
    return tuple(value or "" for value in key)


def _cli_time(value: str) -> str:
    parsed = _parse_utc(value, "time_window")
    if (
        parsed.hour,
        parsed.minute,
        parsed.second,
        parsed.microsecond,
    ) == (0, 0, 0, 0):
        return parsed.strftime(_CLI_DATE_FORMAT)
    return parsed.strftime(_UTC_FORMAT)


def _parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ModalBillingCollectionError(f"{field} must be RFC3339 UTC ending with Z")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ModalBillingCollectionError(f"{field} must be a valid UTC timestamp") from exc
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime(_UTC_FORMAT)


def _modal_interval_start(row: Mapping[str, Any]) -> datetime:
    value = row.get("interval_start")
    if value is None:
        raise ModalBillingCollectionError("Modal billing row missing interval_start")
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ModalBillingCollectionError(
                "Modal billing interval_start must be a valid timestamp"
            ) from exc
    else:
        raise ModalBillingCollectionError("Modal billing interval_start is invalid")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime(_UTC_FORMAT)


def _validate_artifact_path(path: Path, *, expected_suffix: str) -> None:
    if path.suffix != expected_suffix:
        raise ModalBillingCollectionError(
            f"billing artifact path must end with {expected_suffix}"
        )
    if "outputs" in path.parts or "mlruns" in path.parts:
        raise ModalBillingCollectionError(
            "billing artifacts must not target outputs or mlruns"
        )


def _write_bytes_atomic(path: Path, payload: bytes, *, fsync: bool) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(payload)
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
