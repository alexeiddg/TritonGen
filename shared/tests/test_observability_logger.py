from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from shared.observability.logger import (
    ObservabilityJsonlAppendLogger,
    file_sha256,
    load_observability_events,
    write_observability_hash_sidecar_atomic,
    write_observability_summary_atomic,
)
from shared.observability.paths import (
    default_observability_event_path,
    default_observability_hash_path,
    default_observability_summary_path,
    resolve_observability_paths,
)
from shared.observability.schema import (
    ObservabilityArtifactIdentity,
    ObservabilityAttemptIdentity,
    ObservabilityEvent,
    ObservabilityHashSidecar,
    ObservabilityRowIdentity,
    ObservabilitySummary,
    ObservabilityTokenCounts,
)

GIT_COMMIT = "4a8460081aa35a647901ea5fa120a76e0f7ef0e7"


def test_default_paths_are_adjacent_and_collision_safe(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)

    assert paths.event_path == default_observability_event_path(result)
    assert paths.summary_path == default_observability_summary_path(result)
    assert paths.hash_path == default_observability_hash_path(paths.event_path)

    with pytest.raises(ValueError, match="collides"):
        resolve_observability_paths(
            result,
            event_path=result,
            workspace_root=tmp_path,
        )
    with pytest.raises(ValueError, match="collides"):
        resolve_observability_paths(
            result,
            event_path=Path(f"{result}.hashes.json"),
            workspace_root=tmp_path,
        )
    with pytest.raises(ValueError, match="collides"):
        resolve_observability_paths(
            result,
            event_path=Path(f"{result}.meta.json"),
            workspace_root=tmp_path,
        )

    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(ValueError, match="non-file"):
        resolve_observability_paths(
            result,
            event_path=directory,
            workspace_root=tmp_path,
        )

    with pytest.raises(ValueError, match="outside"):
        resolve_observability_paths(
            result,
            event_path=tmp_path.parent / "outside.observability.jsonl",
            workspace_root=tmp_path,
        )


def test_logger_writes_canonical_events_and_hash_sidecar(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(
            _event(
                0,
                result_path=str(result),
                event_path=str(paths.event_path),
                summary_path=str(paths.summary_path),
            )
        )
        logger.append(
            _event(
                1,
                result_path=str(result),
                event_path=str(paths.event_path),
                summary_path=str(paths.summary_path),
            )
        )

    lines = paths.event_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_sequence"] == 0
    assert load_observability_events(paths.event_path)[1].event_sequence == 1

    hash_sidecar = ObservabilityHashSidecar.model_validate_json(
        paths.hash_path.read_text(encoding="utf-8")
    )
    assert hash_sidecar.event_count == 2
    assert hash_sidecar.summary_status == "not_written"
    assert hash_sidecar.event_jsonl_sha256 == file_sha256(paths.event_path)


def test_logger_default_summary_path_matches_path_helper(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    event_path = default_observability_event_path(result)
    logger = ObservabilityJsonlAppendLogger(
        event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        fsync=False,
    )

    assert logger.summary_path == default_observability_summary_path(result)


def test_custom_event_path_uses_result_based_default_summary_path(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    event_path = tmp_path / "custom" / "events.jsonl"

    paths = resolve_observability_paths(
        result,
        event_path=event_path,
        workspace_root=tmp_path,
    )
    logger = ObservabilityJsonlAppendLogger(
        event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        fsync=False,
    )

    assert paths.summary_path == default_observability_summary_path(result)
    assert logger.summary_path == paths.summary_path


def test_logger_rejects_sidecar_collision_before_truncating_result(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    result.parent.mkdir(parents=True)
    original_result = '{"scientific":"row"}\n'
    result.write_text(original_result, encoding="utf-8")

    logger = ObservabilityJsonlAppendLogger(
        result,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        fsync=False,
    )
    with pytest.raises(ValueError, match="collides"):
        logger.open()

    assert result.read_text(encoding="utf-8") == original_result


def test_resume_validates_identity_prefix_and_hash_metadata(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        logger.append(
            _event(
                2,
                result_path=str(result),
                event_path=str(paths.event_path),
                summary_path=str(paths.summary_path),
            )
        )

    assert len(load_observability_events(paths.event_path)) == 3

    with pytest.raises(ValueError, match="identity"):
        ObservabilityJsonlAppendLogger(
            paths.event_path,
            experiment_id="exp",
            run_id="different",
            result_path=str(result),
            summary_path=paths.summary_path,
            hash_path=paths.hash_path,
            git_commit=GIT_COMMIT,
            mode="resume",
            fsync=False,
        ).open()

    sidecar = ObservabilityHashSidecar.model_validate_json(
        paths.hash_path.read_text(encoding="utf-8")
    )
    paths.hash_path.write_text(
        sidecar.model_copy(
            update={
                "observability_summary_path": str(
                    paths.summary_path.with_name("other.summary.json")
                )
            }
        ).model_dump_json(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="summary path"):
        ObservabilityJsonlAppendLogger(
            paths.event_path,
            experiment_id="exp",
            run_id="run",
            result_path=str(result),
            summary_path=paths.summary_path,
            hash_path=paths.hash_path,
            git_commit=GIT_COMMIT,
            mode="resume",
            fsync=False,
        ).open()

    paths.hash_path.write_text(
        sidecar.model_copy(update={"event_jsonl_sha256": "0" * 64}).model_dump_json(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="event hash"):
        ObservabilityJsonlAppendLogger(
            paths.event_path,
            experiment_id="exp",
            run_id="run",
            result_path=str(result),
            summary_path=paths.summary_path,
            hash_path=paths.hash_path,
            git_commit=GIT_COMMIT,
            mode="resume",
            fsync=False,
        ).open()


def test_logger_rejects_unsafe_mode_sequence_mismatch_and_duplicate_id(
    tmp_path: Path,
) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)

    with pytest.raises(ValueError, match="append mode"):
        ObservabilityJsonlAppendLogger(
            paths.event_path,
            experiment_id="exp",
            run_id="run",
            result_path=str(result),
            mode="append",
            fsync=False,
        )

    event_id = str(uuid.uuid4())
    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(
            _event(
                0,
                result_path=str(result),
                event_path=str(paths.event_path),
                summary_path=str(paths.summary_path),
                event_id=event_id,
            )
        )
        with pytest.raises(ValueError, match="event_sequence"):
            logger.append(
                _event(
                    2,
                    result_path=str(result),
                    event_path=str(paths.event_path),
                    summary_path=str(paths.summary_path),
                )
            )
        with pytest.raises(ValueError, match="unique"):
            logger.append(
                _event(
                    1,
                    result_path=str(result),
                    event_path=str(paths.event_path),
                    summary_path=str(paths.summary_path),
                    event_id=event_id,
                )
            )


def test_summary_write_is_atomic_and_hash_sidecar_is_rewritten(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    source_event_hash = file_sha256(paths.event_path)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=source_event_hash,
    )

    written = write_observability_summary_atomic(paths.summary_path, summary, fsync=False)
    assert written.summary_sha256 is not None
    assert json.loads(paths.summary_path.read_text(encoding="utf-8"))["summary_sha256"]

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        final = logger.write_summary(summary)

    hash_sidecar = ObservabilityHashSidecar.model_validate_json(
        paths.hash_path.read_text(encoding="utf-8")
    )
    assert hash_sidecar.summary_status == "written"
    assert hash_sidecar.summary_json_sha256 == file_sha256(paths.summary_path)


def test_atomic_writers_reject_sidecar_path_collisions(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    result.parent.mkdir(parents=True)
    original_result = '{"scientific":"row"}\n'
    result.write_text(original_result, encoding="utf-8")
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=file_sha256(paths.event_path),
    )

    with pytest.raises(ValueError, match="summary_path"):
        write_observability_summary_atomic(result, summary, fsync=False)

    collision_summary = summary.model_copy(
        update={"observability_summary_path": str(result)}
    )
    with pytest.raises(ValueError, match="collides"):
        write_observability_summary_atomic(result, collision_summary, fsync=False)

    hash_sidecar = ObservabilityHashSidecar.model_validate_json(
        paths.hash_path.read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="collides"):
        write_observability_hash_sidecar_atomic(result, hash_sidecar, fsync=False)

    assert result.read_text(encoding="utf-8") == original_result


def test_atomic_summary_writer_rejects_event_stream_mismatches(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=file_sha256(paths.event_path),
    )

    with pytest.raises(ValueError, match="source_event_sha256"):
        write_observability_summary_atomic(
            paths.summary_path,
            summary.model_copy(update={"source_event_sha256": "0" * 64}),
            fsync=False,
        )
    with pytest.raises(ValueError, match="event_counts"):
        write_observability_summary_atomic(
            paths.summary_path,
            summary.model_copy(update={"event_counts": {"stage_completed": 999}}),
            fsync=False,
        )
    with pytest.raises(ValueError, match="stage_durations_ns"):
        write_observability_summary_atomic(
            paths.summary_path,
            summary.model_copy(update={"stage_durations_ns": {"summary": 999}}),
            fsync=False,
        )

    assert not paths.summary_path.exists()


def test_atomic_hash_writer_rejects_stale_artifact_metadata(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    original_hash_sidecar = paths.hash_path.read_text(encoding="utf-8")
    hash_sidecar = ObservabilityHashSidecar.model_validate_json(original_hash_sidecar)

    with pytest.raises(ValueError, match="event hash"):
        write_observability_hash_sidecar_atomic(
            paths.hash_path,
            hash_sidecar.model_copy(update={"event_jsonl_sha256": "0" * 64}),
            fsync=False,
        )
    with pytest.raises(ValueError, match="event_count"):
        write_observability_hash_sidecar_atomic(
            paths.hash_path,
            hash_sidecar.model_copy(update={"event_count": 999}),
            fsync=False,
        )

    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=file_sha256(paths.event_path),
    )
    written_summary = write_observability_summary_atomic(
        paths.summary_path,
        summary,
        fsync=False,
    )
    with pytest.raises(ValueError, match="summary hash"):
        write_observability_hash_sidecar_atomic(
            paths.hash_path,
            hash_sidecar.model_copy(
                update={
                    "summary_status": "written",
                    "summary_json_sha256": "0" * 64,
                }
            ),
            fsync=False,
        )

    assert written_summary.summary_sha256 is not None
    assert paths.hash_path.read_text(encoding="utf-8") == original_hash_sidecar


def test_logger_rejects_summary_with_stale_event_hash(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash="0" * 64,
    )

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        with pytest.raises(ValueError, match="source_event_sha256"):
            logger.write_summary(summary)

    assert not paths.summary_path.exists()


def test_logger_rejects_summary_with_mismatched_event_aggregates(
    tmp_path: Path,
) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=file_sha256(paths.event_path),
    )

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        with pytest.raises(ValueError, match="event_counts"):
            logger.write_summary(
                summary.model_copy(update={"event_counts": {"stage_completed": 999}})
            )
        with pytest.raises(ValueError, match="stage_durations_ns"):
            logger.write_summary(
                summary.model_copy(update={"stage_durations_ns": {"summary": 999}})
            )

    assert not paths.summary_path.exists()


def test_summary_path_identity_is_checked(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path.with_name("other.summary.json")),
        source_event_hash=file_sha256(paths.event_path),
    )

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        with pytest.raises(ValueError, match="summary path"):
            logger.write_summary(summary)


def test_event_sidecar_path_identity_is_checked(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        with pytest.raises(ValueError, match="observability_event_path"):
            logger.append(
                _event(
                    0,
                    result_path=str(result),
                    event_path=str(paths.event_path.with_name("other.observability.jsonl")),
                    summary_path=str(paths.summary_path),
                )
            )
        with pytest.raises(ValueError, match="observability_summary_path"):
            logger.append(
                _event(
                    0,
                    result_path=str(result),
                    event_path=str(paths.event_path),
                    summary_path=str(paths.summary_path.with_name("other.summary.json")),
                )
            )

    assert paths.event_path.read_text(encoding="utf-8") == ""


def test_incompatible_event_payload_is_rejected_before_write(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    payload = _event(
        0,
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
    ).model_dump(mode="json")
    payload["attributes"] = {"source_text": "def kernel(): pass"}

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        with pytest.raises(ValidationError):
            logger.append(payload)


def test_logger_revalidates_event_model_instances_before_write(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    event = _event(
        0,
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
    )
    invalid = event.model_copy(
        update={"attributes": {"source_text": "def kernel(): pass"}}
    )

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        with pytest.raises(ValidationError):
            logger.append(invalid)

    assert paths.event_path.read_text(encoding="utf-8") == ""


def test_logger_revalidates_summary_model_instances_before_write(tmp_path: Path) -> None:
    result = tmp_path / "outputs" / "cluster3" / "matrix.jsonl"
    paths = resolve_observability_paths(result, workspace_root=tmp_path)
    _write_two_events(paths.event_path, paths.summary_path, paths.hash_path, result)
    summary = _summary(
        result_path=str(result),
        event_path=str(paths.event_path),
        summary_path=str(paths.summary_path),
        source_event_hash=file_sha256(paths.event_path),
    )
    invalid = summary.model_copy(
        update={"token_totals": {"source_text": "def kernel(): pass"}}
    )

    with ObservabilityJsonlAppendLogger(
        paths.event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=paths.summary_path,
        hash_path=paths.hash_path,
        git_commit=GIT_COMMIT,
        mode="resume",
        fsync=False,
    ) as logger:
        with pytest.raises(ValidationError):
            logger.write_summary(invalid)

    assert not paths.summary_path.exists()


def _write_two_events(
    event_path: Path,
    summary_path: Path,
    hash_path: Path,
    result: Path,
) -> None:
    with ObservabilityJsonlAppendLogger(
        event_path,
        experiment_id="exp",
        run_id="run",
        result_path=str(result),
        summary_path=summary_path,
        hash_path=hash_path,
        git_commit=GIT_COMMIT,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(
            _event(
                0,
                result_path=str(result),
                event_path=str(event_path),
                summary_path=str(summary_path),
            )
        )
        logger.append(
            _event(
                1,
                result_path=str(result),
                event_path=str(event_path),
                summary_path=str(summary_path),
            )
        )


def _event(
    sequence: int,
    *,
    result_path: str,
    event_path: str,
    summary_path: str,
    event_id: str | None = None,
) -> ObservabilityEvent:
    start = 1_000 + sequence * 100
    end = start + 10
    return ObservabilityEvent(
        event_id=event_id or str(uuid.uuid4()),
        event_sequence=sequence,
        event_type="stage_completed",
        severity="info",
        timestamp_utc="2026-06-03T00:00:00Z",
        timestamp_unix_ns=1_780_444_800_000_000_000 + sequence,
        monotonic_ns=end,
        clock_scope_id="local-process",
        experiment_id="exp",
        run_id="run",
        artifact=ObservabilityArtifactIdentity(
            result_path=result_path,
            observability_event_path=event_path,
            observability_summary_path=summary_path,
            git_commit=GIT_COMMIT,
        ),
        row_identity=ObservabilityRowIdentity(cluster="cluster3", row_sha256="c" * 64),
        stage="summary",
        attempt=ObservabilityAttemptIdentity(attempt_index=sequence),
        status="succeeded",
        duration_ns=end - start,
        duration_source="local_monotonic",
        start_monotonic_ns=start,
        end_monotonic_ns=end,
        token_counts=ObservabilityTokenCounts(
            count_source="not_applicable",
            token_counts_available=False,
        ),
        modal_context=None,
        cost_estimate=None,
        error_summary=None,
        attributes={"row_sha256": "c" * 64},
    )


def _summary(
    *,
    result_path: str,
    event_path: str,
    summary_path: str,
    source_event_hash: str,
) -> ObservabilitySummary:
    return ObservabilitySummary(
        experiment_id="exp",
        run_id="run",
        result_path=result_path,
        observability_event_path=event_path,
        observability_summary_path=summary_path,
        generated_at_utc="2026-06-03T00:00:00Z",
        git_commit=GIT_COMMIT,
        branch="codex/observability-sidecar-core",
        workspace=".",
        row_counts={"completed": 0},
        event_counts={"stage_completed": 2},
        stage_durations_ns={"summary": 20},
        token_totals={"status": "not_applicable"},
        modal_context_summary={"status": "unavailable"},
        estimated_cost_summary={"estimate_status": "not_implemented"},
        actual_billing_status="not_implemented",
        completeness_status="complete",
        caveats=[],
        source_event_sha256=source_event_hash,
        summary_sha256=None,
    )
