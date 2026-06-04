"""Durable JSONL writer for observability sidecars."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Literal

from shared.observability.paths import (
    ObservabilityPaths,
    default_observability_hash_path,
    default_observability_summary_path,
    default_result_content_hash_path,
    default_result_metadata_path,
    validate_observability_paths,
)
from shared.observability.schema import (
    SCHEMA_VERSION,
    HashSummaryStatus,
    ObservabilityEvent,
    ObservabilityHashSidecar,
    ObservabilitySummary,
    canonical_event_json,
    canonical_json_bytes,
    sha256_bytes,
    summary_with_digest,
)

ObservabilityWriteMode = Literal["overwrite", "resume"]


class ObservabilityJsonlAppendLogger:
    """Durable append logger for sidecar event records."""

    def __init__(
        self,
        event_path: str | Path,
        *,
        experiment_id: str,
        run_id: str,
        result_path: str | Path,
        summary_path: str | Path | None = None,
        hash_path: str | Path | None = None,
        schema_version: str = SCHEMA_VERSION,
        git_commit: str | None = None,
        mode: str = "overwrite",
        fsync: bool = True,
    ) -> None:
        _validate_mode(mode)
        self.event_path = Path(event_path)
        self._result_path = Path(result_path)
        self.summary_path = (
            Path(summary_path)
            if summary_path is not None
            else default_observability_summary_path(self._result_path)
        )
        self.hash_path = (
            Path(hash_path)
            if hash_path is not None
            else default_observability_hash_path(self.event_path)
        )
        self.experiment_id = experiment_id
        self.run_id = run_id
        self.result_path = str(result_path)
        self.schema_version = schema_version
        self.git_commit = git_commit.lower() if git_commit is not None else None
        self.mode = mode
        self.fsync = fsync
        self._file = None
        self._next_sequence = 0
        self._event_ids: set[str] = set()

    def __enter__(self) -> "ObservabilityJsonlAppendLogger":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback
        self.close()

    def open(self) -> None:
        if self._file is not None:
            raise RuntimeError("ObservabilityJsonlAppendLogger is already open")
        self._validate_paths()
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.hash_path.parent.mkdir(parents=True, exist_ok=True)

        if self.mode == "overwrite":
            with self.event_path.open("w", encoding="utf-8") as output:
                output.flush()
                if self.fsync:
                    os.fsync(output.fileno())
            self._next_sequence = 0
            self._event_ids = set()
            self._write_hash_sidecar(summary_status="not_written", summary_sha256=None)
        else:
            if not self.event_path.exists():
                raise FileNotFoundError("resume requires an existing observability event sidecar")
            events = load_observability_events(self.event_path)
            for event in events:
                self._require_compatible_event(event)
            self._validate_existing_hash_sidecar(len(events))
            self._next_sequence = len(events)
            self._event_ids = {event.event_id for event in events}

        self._file = self.event_path.open("a", encoding="utf-8")

    def close(self) -> None:
        if self._file is None:
            return
        self._file.close()
        self._file = None

    def append(self, event: ObservabilityEvent | dict) -> bool:
        """Append one canonical event JSON object and refresh hash metadata."""

        if self._file is None:
            raise RuntimeError("ObservabilityJsonlAppendLogger is not open")
        validated = _revalidate_event(event)
        self._require_compatible_event(validated)
        if validated.event_sequence != self._next_sequence:
            raise ValueError(
                f"event_sequence must be {self._next_sequence}; got {validated.event_sequence}"
            )
        if validated.event_id in self._event_ids:
            raise ValueError("event_id must be unique within the sidecar")

        self._file.write(canonical_event_json(validated) + "\n")
        self._file.flush()
        if self.fsync:
            os.fsync(self._file.fileno())
        self._event_ids.add(validated.event_id)
        self._next_sequence += 1
        self._write_hash_sidecar(summary_status="not_written", summary_sha256=None)
        return True

    def write_summary(self, summary: ObservabilitySummary | dict) -> ObservabilitySummary:
        """Write a canonical summary and mark the hash sidecar as written."""

        validated = _revalidate_summary(summary)
        if validated.experiment_id != self.experiment_id or validated.run_id != self.run_id:
            raise ValueError("summary identity does not match logger identity")
        if validated.result_path != self.result_path:
            raise ValueError("summary result_path does not match logger result_path")
        if validated.observability_event_path != str(self.event_path):
            raise ValueError("summary event path does not match logger event path")
        if validated.observability_summary_path != str(self.summary_path):
            raise ValueError("summary path does not match logger summary path")
        final = write_observability_summary_atomic(
            self.summary_path,
            validated,
            fsync=self.fsync,
        )
        self._write_hash_sidecar(
            summary_status="written",
            summary_sha256=file_sha256(self.summary_path),
        )
        return final

    def _require_compatible_event(self, event: ObservabilityEvent) -> None:
        if event.schema_version != self.schema_version:
            raise ValueError("event schema_version does not match logger schema")
        if event.experiment_id != self.experiment_id:
            raise ValueError("event experiment_id does not match logger identity")
        if event.run_id != self.run_id:
            raise ValueError("event run_id does not match logger identity")
        if event.artifact.result_path != self.result_path:
            raise ValueError("event result_path does not match logger result_path")
        if (
            event.artifact.observability_event_path is not None
            and event.artifact.observability_event_path != str(self.event_path)
        ):
            raise ValueError("event observability_event_path does not match logger event path")
        if (
            event.artifact.observability_summary_path is not None
            and event.artifact.observability_summary_path != str(self.summary_path)
        ):
            raise ValueError("event observability_summary_path does not match logger summary path")
        if self.git_commit is not None and event.artifact.git_commit != self.git_commit:
            raise ValueError("event git_commit does not match logger git_commit")

    def _validate_paths(self) -> None:
        validate_observability_paths(
            ObservabilityPaths(
                result_path=self._result_path,
                event_path=self.event_path,
                summary_path=self.summary_path,
                hash_path=self.hash_path,
            )
        )

    def _validate_existing_hash_sidecar(self, event_count: int) -> None:
        if not self.hash_path.exists():
            return
        existing = ObservabilityHashSidecar.model_validate_json(
            self.hash_path.read_text(encoding="utf-8")
        )
        if existing.experiment_id != self.experiment_id or existing.run_id != self.run_id:
            raise ValueError("existing hash sidecar identity is incompatible")
        if existing.result_path != self.result_path:
            raise ValueError("existing hash sidecar result_path is incompatible")
        if existing.observability_event_path != str(self.event_path):
            raise ValueError("existing hash sidecar event path is incompatible")
        if existing.observability_summary_path != str(self.summary_path):
            raise ValueError("existing hash sidecar summary path is incompatible")
        if existing.event_count != event_count:
            raise ValueError("existing hash sidecar event_count is incompatible")
        if existing.event_jsonl_sha256 != file_sha256(self.event_path):
            raise ValueError("existing hash sidecar event hash is incompatible")

    def _write_hash_sidecar(
        self,
        *,
        summary_status: HashSummaryStatus,
        summary_sha256: str | None,
    ) -> None:
        sidecar = ObservabilityHashSidecar(
            experiment_id=self.experiment_id,
            run_id=self.run_id,
            result_path=self.result_path,
            observability_event_path=str(self.event_path),
            observability_summary_path=str(self.summary_path),
            event_jsonl_sha256=file_sha256(self.event_path),
            summary_json_sha256=summary_sha256,
            summary_status=summary_status,
            event_count=self._next_sequence,
            generated_at_utc=utc_now(),
            hash_algorithm="sha256",
        )
        write_observability_hash_sidecar_atomic(self.hash_path, sidecar, fsync=self.fsync)


def load_observability_events(path: str | Path) -> tuple[ObservabilityEvent, ...]:
    """Load and validate a complete observability JSONL event stream."""

    event_path = Path(path)
    text = event_path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        raise ValueError("observability event sidecar must end with a newline")
    events = tuple(
        ObservabilityEvent.model_validate(json.loads(line))
        for line in text.splitlines()
        if line
    )
    validate_event_stream(events)
    return events


def validate_event_stream(events: tuple[ObservabilityEvent, ...]) -> None:
    """Validate contiguous sequences and unique event IDs."""

    seen_ids: set[str] = set()
    for expected_sequence, event in enumerate(events):
        if event.event_sequence != expected_sequence:
            raise ValueError("event_sequence values must be contiguous from 0")
        if event.event_id in seen_ids:
            raise ValueError("event_id values must be unique")
        seen_ids.add(event.event_id)


def event_counts(events: tuple[ObservabilityEvent, ...]) -> dict[str, int]:
    """Return event-type counts derived from an event stream."""

    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    return counts


def stage_durations_ns(events: tuple[ObservabilityEvent, ...]) -> dict[str, int]:
    """Return stage duration totals derived from measured event durations."""

    totals: dict[str, int] = {}
    for event in events:
        if event.stage is not None and event.duration_ns is not None:
            totals[event.stage] = totals.get(event.stage, 0) + event.duration_ns
    return totals


def token_totals(events: tuple[ObservabilityEvent, ...]) -> dict[str, object]:
    """Return count/status-only token totals derived from an event stream."""

    token_events = [event.token_counts for event in events if event.token_counts is not None]
    available_events = [counts for counts in token_events if counts.token_counts_available]
    if not available_events:
        status = "unavailable"
    elif any(counts.token_count_status == "partial" for counts in available_events):
        status = "partial"
    else:
        status = "available"

    def _sum_available(values: tuple[int | None, ...]) -> int | None:
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)

    return {
        "token_count_status": status,
        "events_with_token_counts": len(token_events),
        "events_with_available_token_counts": len(available_events),
        "prompt_tokens": _sum_available(
            tuple(counts.prompt_tokens for counts in available_events)
        ),
        "generated_tokens": _sum_available(
            tuple(counts.generated_tokens for counts in available_events)
        ),
        "total_tokens": _sum_available(
            tuple(counts.total_tokens for counts in available_events)
        ),
        "token_count_sources": sorted(
            {counts.token_count_source for counts in token_events}
        ),
    }


def estimated_cost_summary(events: tuple[ObservabilityEvent, ...]) -> dict[str, object]:
    """Return estimated/unavailable cost metadata derived from an event stream."""

    cost_events = [
        event.cost_estimate for event in events if event.cost_estimate is not None
    ]
    available_events = [
        estimate for estimate in cost_events if estimate.cost_estimate_available
    ]
    if not available_events:
        return _unavailable_estimated_cost_summary()

    currencies = {estimate.currency for estimate in available_events}
    pricing_sources = {estimate.pricing_source for estimate in available_events}
    pricing_versions = {estimate.pricing_source_version for estimate in available_events}
    methods = {estimate.cost_estimate_method for estimate in available_events}
    if currencies != {"USD"}:
        raise ValueError("available cost estimates must use a single USD currency")
    if len(pricing_sources) != 1 or None in pricing_sources:
        raise ValueError("available cost estimates must use one pricing_source")
    if len(pricing_versions) != 1 or None in pricing_versions:
        raise ValueError("available cost estimates must use one pricing_source_version")
    if len(methods) != 1:
        raise ValueError("available cost estimates must use one cost_estimate_method")

    input_cost = _sum_cost_values(
        tuple(estimate.estimated_input_cost for estimate in available_events)
    )
    output_cost = _sum_cost_values(
        tuple(estimate.estimated_output_cost for estimate in available_events)
    )
    total_cost = _sum_cost_values(
        tuple(estimate.estimated_total_cost for estimate in available_events)
    )
    if total_cost != _round_cost(input_cost + output_cost):
        raise ValueError("estimated_total_cost does not match input/output cost totals")

    return {
        "cost_estimate_available": True,
        "estimated_input_cost": input_cost,
        "estimated_output_cost": output_cost,
        "estimated_total_cost": total_cost,
        "currency": "USD",
        "pricing_source": next(iter(pricing_sources)),
        "pricing_source_version": next(iter(pricing_versions)),
        "cost_estimate_status": "estimated",
        "cost_estimate_method": next(iter(methods)),
    }


def write_observability_summary_atomic(
    summary_path: str | Path,
    summary: ObservabilitySummary | dict,
    *,
    fsync: bool = True,
) -> ObservabilitySummary:
    """Write a summary atomically after computing its self-reference hash."""

    validated = _revalidate_summary(summary)
    path = Path(summary_path)
    _validate_summary_write_path(path, validated)
    _validate_summary_against_event_stream(validated)
    final = summary_with_digest(validated)
    _write_bytes_atomic(path, canonical_json_bytes(final), fsync=fsync)
    return final


def write_observability_hash_sidecar_atomic(
    hash_path: str | Path,
    sidecar: ObservabilityHashSidecar | dict,
    *,
    fsync: bool = True,
) -> None:
    validated = _revalidate_hash_sidecar(sidecar)
    path = Path(hash_path)
    _validate_hash_sidecar_write_path(path, validated)
    _validate_hash_sidecar_against_artifacts(validated)
    _write_bytes_atomic(path, canonical_json_bytes(validated), fsync=fsync)


def file_sha256(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validate_mode(mode: str) -> None:
    if mode == "append":
        raise ValueError("append mode is not supported for observability sidecars")
    if mode not in {"overwrite", "resume"}:
        raise ValueError("mode must be 'overwrite' or 'resume'")


def _revalidate_event(event: ObservabilityEvent | dict) -> ObservabilityEvent:
    payload = event.model_dump(mode="json") if isinstance(event, ObservabilityEvent) else event
    return ObservabilityEvent.model_validate(payload)


def _revalidate_summary(summary: ObservabilitySummary | dict) -> ObservabilitySummary:
    payload = summary.model_dump(mode="json") if isinstance(summary, ObservabilitySummary) else summary
    return ObservabilitySummary.model_validate(payload)


def _revalidate_hash_sidecar(
    sidecar: ObservabilityHashSidecar | dict,
) -> ObservabilityHashSidecar:
    payload = (
        sidecar.model_dump(mode="json")
        if isinstance(sidecar, ObservabilityHashSidecar)
        else sidecar
    )
    return ObservabilityHashSidecar.model_validate(payload)


def _validate_summary_write_path(path: Path, summary: ObservabilitySummary) -> None:
    expected = Path(summary.observability_summary_path)
    if path.resolve(strict=False) != expected.resolve(strict=False):
        raise ValueError("summary_path does not match summary observability_summary_path")
    _reject_write_path_collisions(
        "summary_path",
        path,
        {
            "result_path": Path(summary.result_path),
            "result_content_hash_path": default_result_content_hash_path(summary.result_path),
            "result_metadata_path": default_result_metadata_path(summary.result_path),
            "observability_event_path": Path(summary.observability_event_path),
            "observability_hash_path": default_observability_hash_path(
                summary.observability_event_path
            ),
        },
    )


def _validate_hash_sidecar_write_path(
    path: Path,
    sidecar: ObservabilityHashSidecar,
) -> None:
    validate_observability_paths(
        ObservabilityPaths(
            result_path=Path(sidecar.result_path),
            event_path=Path(sidecar.observability_event_path),
            summary_path=Path(sidecar.observability_summary_path),
            hash_path=path,
        )
    )


def _validate_summary_against_event_stream(summary: ObservabilitySummary) -> None:
    event_path = Path(summary.observability_event_path)
    events = load_observability_events(event_path)
    if summary.source_event_sha256 != file_sha256(event_path):
        raise ValueError("summary source_event_sha256 does not match current event sidecar")
    if summary.event_counts != event_counts(events):
        raise ValueError("summary event_counts do not match event stream")
    if summary.stage_durations_ns != stage_durations_ns(events):
        raise ValueError("summary stage_durations_ns do not match event stream")
    if summary.token_totals != token_totals(events):
        raise ValueError("summary token_totals do not match event stream")
    if summary.estimated_cost_summary != estimated_cost_summary(events):
        raise ValueError("summary estimated_cost_summary does not match event stream")


def _validate_hash_sidecar_against_artifacts(sidecar: ObservabilityHashSidecar) -> None:
    event_path = Path(sidecar.observability_event_path)
    events = load_observability_events(event_path)
    if sidecar.event_jsonl_sha256 != file_sha256(event_path):
        raise ValueError("hash sidecar event hash does not match current event sidecar")
    if sidecar.event_count != len(events):
        raise ValueError("hash sidecar event_count does not match event stream")

    if sidecar.summary_status == "written":
        summary_path = Path(sidecar.observability_summary_path)
        if not summary_path.exists():
            raise ValueError("written hash sidecar summary path does not exist")
        if sidecar.summary_json_sha256 != file_sha256(summary_path):
            raise ValueError("hash sidecar summary hash does not match current summary sidecar")


def _reject_write_path_collisions(
    path_name: str,
    path: Path,
    other_paths: dict[str, Path],
) -> None:
    for other_name, other_path in other_paths.items():
        if path.resolve(strict=False) == other_path.resolve(strict=False):
            raise ValueError(f"{path_name} collides with {other_name}")
    if path.exists() and not path.is_file():
        raise ValueError(f"{path_name} points at an existing non-file path")


def _unavailable_estimated_cost_summary() -> dict[str, object]:
    return {
        "cost_estimate_available": False,
        "estimated_input_cost": None,
        "estimated_output_cost": None,
        "estimated_total_cost": None,
        "currency": None,
        "pricing_source": None,
        "pricing_source_version": None,
        "cost_estimate_status": "unavailable",
        "cost_estimate_method": "unavailable",
    }


def _sum_cost_values(values: tuple[float | None, ...]) -> float:
    if any(value is None for value in values):
        raise ValueError("available cost estimates require complete cost values")
    return _round_cost(sum(value for value in values if value is not None))


def _round_cost(value: float) -> float:
    return round(value, 12)


def _write_bytes_atomic(path: Path, payload: bytes, *, fsync: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
