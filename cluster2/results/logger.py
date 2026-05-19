"""Deterministic JSONL logger for Cluster 2 evaluation rows.

The batch writer remains available for tests and small deterministic rewrites.
Long C2 runs should use ``Cluster2JsonlAppendLogger`` so each completed logical
row is flushed and fsynced before the next row starts.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal

from cluster2.constants import (
    CLUSTER2_CONDITIONS,
    DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    NEW_GENERATION_CONDITIONS,
    REPLAY_CONTROL_CONDITIONS,
)
from cluster2.results.dataclass import (
    CLUSTER2_RESULTS_SCHEMA_VERSION,
    Cluster2ContentHashSidecar,
    Cluster2EvalRow,
    Cluster2OptionalDiagnostics,
)
from shared.eval.content_hashes import (
    collect_c2_generation_hashes,
    collect_cluster1_frozen_generation_hashes,
    collect_eval_pipeline_hashes,
    collect_external_pins,
)


Cluster2WriteMode = Literal["overwrite", "resume"]


@dataclass(frozen=True)
class Cluster2ResultsLogger:
    """Small path-bound wrapper around the Phase 10 JSONL writer."""

    output_path: Path
    content_hash_sidecar_path: Path | None = None

    def overwrite(
        self,
        rows: Iterable[Cluster2EvalRow],
        content_hash_sidecar: Cluster2ContentHashSidecar | None = None,
    ) -> None:
        write_cluster2_results_jsonl(
            self.output_path,
            rows,
            content_hash_sidecar=content_hash_sidecar,
            mode="overwrite",
            sidecar_path=self.content_hash_sidecar_path,
        )

    def resume(
        self,
        rows: Iterable[Cluster2EvalRow],
        content_hash_sidecar: Cluster2ContentHashSidecar | None = None,
    ) -> None:
        write_cluster2_results_jsonl(
            self.output_path,
            rows,
            content_hash_sidecar=content_hash_sidecar,
            mode="resume",
            sidecar_path=self.content_hash_sidecar_path,
        )


class Cluster2JsonlAppendLogger:
    """Durable path-bound appender for completed C2 logical result rows."""

    def __init__(
        self,
        output_path: str | Path,
        *,
        content_hash_sidecar: Cluster2ContentHashSidecar,
        mode: str = "overwrite",
        sidecar_path: str | Path | None = None,
        fsync: bool = True,
    ) -> None:
        _validate_mode(mode)
        if not isinstance(content_hash_sidecar, Cluster2ContentHashSidecar):
            raise TypeError("content_hash_sidecar must be a Cluster2ContentHashSidecar")
        self.output_path = Path(output_path)
        self.sidecar_path = (
            default_content_hash_sidecar_path(self.output_path)
            if sidecar_path is None
            else Path(sidecar_path)
        )
        self.content_hash_sidecar = content_hash_sidecar
        self.mode = mode
        self.fsync = fsync
        self._file = None
        self._existing_lines: tuple[str, ...] = ()
        self._resume_index = 0

    def __enter__(self) -> "Cluster2JsonlAppendLogger":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        try:
            if exc_type is None:
                self._validate_no_unconsumed_resume_rows()
        finally:
            self.close()

    def open(self) -> None:
        """Initialize output policy and open the JSONL file for appends."""

        if self._file is not None:
            raise RuntimeError("Cluster2JsonlAppendLogger is already open")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        if self.mode == "overwrite":
            with self.output_path.open("w", encoding="utf-8") as output:
                output.flush()
                if self.fsync:
                    os.fsync(output.fileno())
            _write_sidecar_atomic(
                self.sidecar_path,
                self.content_hash_sidecar,
                fsync=self.fsync,
            )
        else:
            if not self.output_path.exists():
                raise FileNotFoundError("resume requires an existing JSONL output")
            if not self.sidecar_path.exists():
                raise FileNotFoundError("resume requires an existing content-hash sidecar")
            existing_sidecar = load_content_hash_sidecar(self.sidecar_path)
            existing_sidecar.require_hash_compatible(self.content_hash_sidecar)
            existing_text = self.output_path.read_text(encoding="utf-8")
            if existing_text and not existing_text.endswith("\n"):
                raise ValueError("existing JSONL output must end with a newline for resume")
            self._existing_lines = tuple(existing_text.splitlines())

        self._file = self.output_path.open("a", encoding="utf-8")

    def close(self) -> None:
        if self._file is None:
            return
        self._file.close()
        self._file = None

    def _validate_no_unconsumed_resume_rows(self) -> None:
        if self.mode != "resume":
            return
        if self._resume_index < len(self._existing_lines):
            raise ValueError("existing JSONL output has more rows than completed resume")

    def append(self, row: Cluster2EvalRow) -> bool:
        """Append one row if it is not already present in a resume prefix.

        Returns ``True`` when bytes were written and ``False`` when resume mode
        consumed a matching existing prefix row.
        """

        if self._file is None:
            raise RuntimeError("Cluster2JsonlAppendLogger is not open")
        validate_content_hash_sidecar_for_rows((row,), self.content_hash_sidecar)
        line = serialize_cluster2_row(row)
        if self._resume_index < len(self._existing_lines):
            existing = self._existing_lines[self._resume_index]
            if existing != line:
                raise ValueError("existing JSONL rows do not match deterministic resume prefix")
            self._resume_index += 1
            return False

        self._file.write(line + "\n")
        self._file.flush()
        if self.fsync:
            os.fsync(self._file.fileno())
        self._resume_index += 1
        return True


def default_content_hash_sidecar_path(path: str | Path) -> Path:
    """Return the default content-hash sidecar path for a C2 JSONL output."""

    output_path = Path(path)
    return output_path.with_name(f"{output_path.name}.hashes.json")


def serialize_cluster2_row(row: Cluster2EvalRow) -> str:
    """Return one canonical JSON object string for a C2 row."""

    if not isinstance(row, Cluster2EvalRow):
        raise TypeError("row must be a Cluster2EvalRow")
    return row.to_json()


def serialize_cluster2_rows(rows: Iterable[Cluster2EvalRow]) -> str:
    """Return canonical newline-delimited JSON for C2 rows."""

    lines = [serialize_cluster2_row(row) for row in rows]
    return "" if not lines else "\n".join(lines) + "\n"


def build_content_hash_sidecar(
    rows: Iterable[Cluster2EvalRow],
    *,
    eval_pipeline_hashes: dict[str, str] | None = None,
    generated_condition_hashes: dict[str, dict[str, str]] | None = None,
    replay_control_hashes: dict[str, dict[str, str]] | None = None,
    frozen_cluster1_manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    external_pins: dict[str, str] | None = None,
    optional_diagnostics: Cluster2OptionalDiagnostics | None = None,
) -> Cluster2ContentHashSidecar:
    """Build an authoritative sidecar for the conditions represented by rows."""

    row_tuple = tuple(rows)
    generated_hashes = (
        _collect_generated_hashes_for_rows(row_tuple)
        if generated_condition_hashes is None
        else dict(generated_condition_hashes)
    )
    replay_hashes = (
        _collect_replay_hashes_for_rows(row_tuple, frozen_cluster1_manifest_path)
        if replay_control_hashes is None
        else dict(replay_control_hashes)
    )

    return Cluster2ContentHashSidecar(
        schema_version=CLUSTER2_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes=(
            collect_eval_pipeline_hashes()
            if eval_pipeline_hashes is None
            else dict(eval_pipeline_hashes)
        ),
        generated_condition_hashes=generated_hashes,
        replay_control_hashes=replay_hashes,
        external_pins=collect_external_pins() if external_pins is None else dict(external_pins),
        optional_diagnostics=optional_diagnostics,
    )


def collect_content_hash_sidecar_for_conditions(
    conditions: Iterable[str],
    *,
    frozen_cluster1_manifest_path: str | Path = DEFAULT_FROZEN_CLUSTER1_MANIFEST,
    eval_pipeline_hashes: dict[str, str] | None = None,
    external_pins: dict[str, str] | None = None,
    optional_diagnostics: Cluster2OptionalDiagnostics | None = None,
) -> Cluster2ContentHashSidecar:
    """Collect current hash sidecars for requested C2 conditions."""

    normalized_conditions = _normalize_condition_sequence(conditions)
    generated_hashes = {
        condition: collect_c2_generation_hashes(condition)
        for condition in normalized_conditions
        if condition in NEW_GENERATION_CONDITIONS
    }
    replay_hashes = {
        condition: collect_cluster1_frozen_generation_hashes(
            condition,
            str(frozen_cluster1_manifest_path),
        )
        for condition in normalized_conditions
        if condition in REPLAY_CONTROL_CONDITIONS
    }
    return Cluster2ContentHashSidecar(
        schema_version=CLUSTER2_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes=(
            collect_eval_pipeline_hashes()
            if eval_pipeline_hashes is None
            else dict(eval_pipeline_hashes)
        ),
        generated_condition_hashes=generated_hashes,
        replay_control_hashes=replay_hashes,
        external_pins=collect_external_pins() if external_pins is None else dict(external_pins),
        optional_diagnostics=optional_diagnostics,
    )


def validate_content_hash_sidecar_for_rows(
    rows: Iterable[Cluster2EvalRow],
    sidecar: Cluster2ContentHashSidecar,
) -> None:
    """Validate that row provenance uses the matching hash class in ``sidecar``."""

    if not isinstance(sidecar, Cluster2ContentHashSidecar):
        raise TypeError("sidecar must be a Cluster2ContentHashSidecar")
    for row in rows:
        if row.condition in REPLAY_CONTROL_CONDITIONS:
            expected = sidecar.replay_control_hashes.get(row.condition)
            if expected is None:
                raise ValueError(
                    f"missing replay_control_hashes for condition {row.condition!r}"
                )
            if row.replay_metadata is None:
                raise ValueError("replay row is missing replay_metadata")
            if row.replay_metadata.frozen_cluster1_generation_hashes != expected:
                raise ValueError("replay row uses hashes outside frozen Cluster 1 class")
            continue

        if row.condition in NEW_GENERATION_CONDITIONS:
            expected = sidecar.generated_condition_hashes.get(row.condition)
            if expected is None:
                raise ValueError(
                    f"missing generated_condition_hashes for condition {row.condition!r}"
                )
            if row.generated_metadata is None:
                raise ValueError("generated row is missing generated_metadata")
            if row.generated_metadata.c2_generation_hashes != expected:
                raise ValueError("generated row uses hashes outside C2 generation class")
            continue

        raise ValueError(f"unsupported Cluster 2 condition {row.condition!r}")


def write_cluster2_results_jsonl(
    path: str | Path,
    rows: Iterable[Cluster2EvalRow],
    *,
    content_hash_sidecar: Cluster2ContentHashSidecar | None = None,
    mode: str = "overwrite",
    sidecar_path: str | Path | None = None,
) -> None:
    """Write C2 rows and their content-hash sidecar deterministically."""

    output_path = Path(path)
    resolved_sidecar_path = (
        default_content_hash_sidecar_path(output_path)
        if sidecar_path is None
        else Path(sidecar_path)
    )
    row_tuple = tuple(rows)
    _validate_mode(mode)
    sidecar = (
        build_content_hash_sidecar(row_tuple)
        if content_hash_sidecar is None
        else content_hash_sidecar
    )
    validate_content_hash_sidecar_for_rows(row_tuple, sidecar)

    if mode == "resume":
        _validate_resume_state(output_path, resolved_sidecar_path, row_tuple, sidecar)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_cluster2_rows(row_tuple), encoding="utf-8")
    resolved_sidecar_path.write_text(sidecar.to_json() + "\n", encoding="utf-8")


def write_cluster2_jsonl(
    path: str | Path,
    rows: Iterable[Cluster2EvalRow],
    *,
    content_hash_sidecar: Cluster2ContentHashSidecar | None = None,
    mode: str = "overwrite",
    sidecar_path: str | Path | None = None,
) -> None:
    """Backward-compatible short alias for the C2 results writer."""

    write_cluster2_results_jsonl(
        path,
        rows,
        content_hash_sidecar=content_hash_sidecar,
        mode=mode,
        sidecar_path=sidecar_path,
    )


def load_cluster2_results_jsonl(path: str | Path) -> tuple[Cluster2EvalRow, ...]:
    """Load strict C2 result rows from a newline-delimited JSON file."""

    rows: list[Cluster2EvalRow] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            raise ValueError(f"blank JSONL line at {line_number}")
        rows.append(Cluster2EvalRow.from_dict(json.loads(line)))
    return tuple(rows)


def validate_cluster2_results_jsonl(
    path: str | Path,
    *,
    expected_rows: int | None = None,
    allow_partial: bool = False,
) -> tuple[Cluster2EvalRow, ...]:
    """Load C2 JSONL and optionally enforce a strict expected row count."""

    rows = load_cluster2_results_jsonl(path)
    if expected_rows is None:
        return rows
    if expected_rows < 0:
        raise ValueError("expected_rows must be non-negative")
    if len(rows) == expected_rows:
        return rows
    if allow_partial and len(rows) < expected_rows:
        return rows
    raise ValueError(f"expected {expected_rows} rows, found {len(rows)}")


def load_content_hash_sidecar(path: str | Path) -> Cluster2ContentHashSidecar:
    """Load a strict C2 content-hash sidecar."""

    return Cluster2ContentHashSidecar.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def _validate_mode(mode: str) -> None:
    if mode == "append":
        raise ValueError("append mode is not supported for Cluster 2 results")
    if mode not in {"overwrite", "resume"}:
        raise ValueError("mode must be 'overwrite' or 'resume'")


def _validate_resume_state(
    output_path: Path,
    sidecar_path: Path,
    rows: Sequence[Cluster2EvalRow],
    sidecar: Cluster2ContentHashSidecar,
) -> None:
    if not output_path.exists():
        raise FileNotFoundError("resume requires an existing JSONL output")
    if not sidecar_path.exists():
        raise FileNotFoundError("resume requires an existing content-hash sidecar")

    existing_sidecar = load_content_hash_sidecar(sidecar_path)
    existing_sidecar.require_hash_compatible(sidecar)

    existing_text = output_path.read_text(encoding="utf-8")
    if existing_text and not existing_text.endswith("\n"):
        raise ValueError("existing JSONL output must end with a newline for resume")
    existing_lines = existing_text.splitlines()
    if len(existing_lines) > len(rows):
        raise ValueError("existing JSONL output has more rows than requested resume")
    expected_prefix = [row.to_json() for row in rows[: len(existing_lines)]]
    if existing_lines != expected_prefix:
        raise ValueError("existing JSONL rows do not match deterministic resume prefix")


def _write_sidecar_atomic(
    sidecar_path: Path,
    sidecar: Cluster2ContentHashSidecar,
    *,
    fsync: bool,
) -> None:
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{sidecar_path.name}.",
        suffix=".tmp",
        dir=sidecar_path.parent,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(sidecar.to_json() + "\n")
            tmp.flush()
            if fsync:
                os.fsync(tmp.fileno())
        tmp_path.replace(sidecar_path)
        if fsync:
            directory_fd = os.open(sidecar_path.parent, os.O_RDONLY)
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


def _collect_generated_hashes_for_rows(
    rows: Sequence[Cluster2EvalRow],
) -> dict[str, dict[str, str]]:
    return {
        condition: collect_c2_generation_hashes(condition)
        for condition in _conditions_present(rows, NEW_GENERATION_CONDITIONS)
    }


def _collect_replay_hashes_for_rows(
    rows: Sequence[Cluster2EvalRow],
    frozen_cluster1_manifest_path: str | Path,
) -> dict[str, dict[str, str]]:
    return {
        condition: collect_cluster1_frozen_generation_hashes(
            condition,
            str(frozen_cluster1_manifest_path),
        )
        for condition in _conditions_present(rows, REPLAY_CONTROL_CONDITIONS)
    }


def _conditions_present(
    rows: Sequence[Cluster2EvalRow],
    allowed_conditions: tuple[str, ...],
) -> tuple[str, ...]:
    requested = {row.condition for row in rows if row.condition in allowed_conditions}
    return tuple(condition for condition in allowed_conditions if condition in requested)


def _normalize_condition_sequence(conditions: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(conditions))
    unknown = [condition for condition in requested if condition not in CLUSTER2_CONDITIONS]
    if unknown:
        raise ValueError(f"unsupported Cluster 2 conditions: {', '.join(unknown)}")
    return tuple(condition for condition in CLUSTER2_CONDITIONS if condition in requested)
