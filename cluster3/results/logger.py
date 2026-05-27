"""Deterministic JSONL append logger for Cluster 3 evaluation rows."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Literal

from cluster3.results.dataclass import (
    Cluster3ContentHashSidecar,
    Cluster3EvalRow,
)


Cluster3WriteMode = Literal["overwrite", "resume"]


class Cluster3JsonlAppendLogger:
    """Durable path-bound appender for completed Cluster 3 logical rows."""

    def __init__(
        self,
        output_path: str | Path,
        *,
        content_hash_sidecar: Cluster3ContentHashSidecar,
        mode: str = "overwrite",
        sidecar_path: str | Path | None = None,
        fsync: bool = True,
    ) -> None:
        _validate_mode(mode)
        if not isinstance(content_hash_sidecar, Cluster3ContentHashSidecar):
            raise TypeError("content_hash_sidecar must be a Cluster3ContentHashSidecar")
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

    def __enter__(self) -> "Cluster3JsonlAppendLogger":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        self._close(validate_resume=exc_type is None)

    def open(self) -> None:
        """Initialize output policy and open the JSONL file for appends."""

        if self._file is not None:
            raise RuntimeError("Cluster3JsonlAppendLogger is already open")
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
        self._close(validate_resume=True)

    def _close(self, *, validate_resume: bool) -> None:
        if self._file is None:
            return
        try:
            if validate_resume:
                self._validate_no_unconsumed_resume_rows()
        finally:
            self._file.close()
            self._file = None

    def _validate_no_unconsumed_resume_rows(self) -> None:
        if self.mode != "resume":
            return
        if self._resume_index < len(self._existing_lines):
            raise ValueError("existing JSONL output has more rows than completed resume")

    def append(self, row: Cluster3EvalRow) -> bool:
        """Append one row unless resume mode consumes a matching prefix row."""

        if self._file is None:
            raise RuntimeError("Cluster3JsonlAppendLogger is not open")
        validate_content_hash_sidecar_for_rows((row,), self.content_hash_sidecar)
        line = serialize_cluster3_row(row)
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
    """Return the default content-hash sidecar path for a Cluster 3 JSONL output."""

    output_path = Path(path)
    return output_path.with_name(f"{output_path.name}.hashes.json")


def serialize_cluster3_row(row: Cluster3EvalRow) -> str:
    """Return one canonical JSON object string for a Cluster 3 row."""

    if not isinstance(row, Cluster3EvalRow):
        raise TypeError("row must be a Cluster3EvalRow")
    return row.to_json()


def load_content_hash_sidecar(path: str | Path) -> Cluster3ContentHashSidecar:
    """Load a strict Cluster 3 content-hash sidecar."""

    return Cluster3ContentHashSidecar.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def validate_content_hash_sidecar_for_rows(
    rows: tuple[Cluster3EvalRow, ...],
    sidecar: Cluster3ContentHashSidecar,
) -> None:
    """Validate that row generation hashes match the supplied sidecar."""

    if not isinstance(sidecar, Cluster3ContentHashSidecar):
        raise TypeError("sidecar must be a Cluster3ContentHashSidecar")
    for row in rows:
        if not isinstance(row, Cluster3EvalRow):
            raise TypeError("rows must contain Cluster3EvalRow instances")
        expected = sidecar.generated_condition_hashes.get(row.condition)
        if expected is None:
            raise ValueError(
                f"missing generated_condition_hashes for condition {row.condition!r}"
            )
        if row.generated_metadata is None:
            raise ValueError("Cluster 3 row is missing generated_metadata")
        if row.generated_metadata.c3_generation_hashes != expected:
            raise ValueError("Cluster 3 row uses hashes outside C3 generation class")
        if row.replay_metadata is None:
            continue
        replay_condition = row.generated_metadata.replay_control_condition
        if replay_condition is None:
            raise ValueError(
                "generated_metadata.replay_control_condition is required for replay sidecar validation"
            )
        replay_expected = sidecar.replay_control_hashes.get(replay_condition)
        if replay_expected is None:
            raise ValueError(
                f"missing replay_control_hashes for condition {replay_condition!r}"
            )
        if row.replay_metadata.frozen_cluster1_generation_hashes != replay_expected:
            raise ValueError("replay row uses hashes outside frozen Cluster 1 class")


def _validate_mode(mode: str) -> None:
    if mode == "append":
        raise ValueError("append mode is not supported for Cluster 3 results")
    if mode not in {"overwrite", "resume"}:
        raise ValueError("mode must be 'overwrite' or 'resume'")


def _write_sidecar_atomic(
    sidecar_path: Path,
    sidecar: Cluster3ContentHashSidecar,
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
