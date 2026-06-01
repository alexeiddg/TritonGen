from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import cluster3.results.logger as results_logger
from cluster3.results.dataclass import (
    CLUSTER3_RESULTS_SCHEMA_VERSION,
    Cluster3ContentHashSidecar,
    Cluster3EvalRow,
    Cluster3ReplayRowMetadata,
)
from cluster3.results.logger import (
    Cluster3JsonlAppendLogger,
    default_content_hash_sidecar_path,
    load_content_hash_sidecar,
    serialize_cluster3_row,
    validate_content_hash_sidecar_for_rows,
)
from cluster3.tests.test_cluster3_schema import GEN_HASHES, HASH_A, HASH_B, _row


def _sidecar(rows: tuple[Cluster3EvalRow, ...]) -> Cluster3ContentHashSidecar:
    generated_hashes: dict[str, dict[str, str]] = {}
    for row in rows:
        assert row.generated_metadata is not None
        generated_hashes[row.condition] = row.generated_metadata.c3_generation_hashes
    return Cluster3ContentHashSidecar(
        schema_version=CLUSTER3_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes={"shared/eval/pipeline.py": HASH_A},
        generated_condition_hashes=generated_hashes,
        replay_control_hashes={},
        external_pins={"python": "3.14.2"},
    )


def _replay_metadata(
    *,
    generation_hashes: dict[str, str],
) -> Cluster3ReplayRowMetadata:
    return Cluster3ReplayRowMetadata(
        frozen_cluster1_artifact_id="cluster1-none",
        frozen_cluster1_source_hash=HASH_A,
        frozen_cluster1_generation_hashes=generation_hashes,
    )


def _row_with_replay_metadata(
    *,
    generation_hashes: dict[str, str],
    replay_control_condition: str | None = "none",
) -> Cluster3EvalRow:
    baseline = _row()
    assert baseline.generated_metadata is not None
    return _row(
        replay_metadata=_replay_metadata(generation_hashes=generation_hashes),
        generated_metadata=replace(
            baseline.generated_metadata,
            replay_control_condition=replay_control_condition,
        ),
    )


def test_logger_writes_one_row_with_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "cluster3.jsonl"
    row = _row()
    fsync_calls: list[int] = []
    monkeypatch.setattr(results_logger.os, "fsync", lambda fd: fsync_calls.append(fd))
    logger = Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=_sidecar((row,)),
        mode="overwrite",
        fsync=True,
    )

    logger.open()
    fsync_calls.clear()
    try:
        assert logger.append(row) is True
    finally:
        logger.close()

    assert len(fsync_calls) == 1
    assert output.read_text(encoding="utf-8") == serialize_cluster3_row(row) + "\n"


def test_logger_validates_replay_metadata_against_sidecar() -> None:
    frozen_hashes = {"outputs/cluster1/baseline.jsonl": HASH_B}
    row = _row_with_replay_metadata(generation_hashes=frozen_hashes)
    sidecar = _sidecar((row,))
    sidecar = Cluster3ContentHashSidecar(
        schema_version=sidecar.schema_version,
        eval_pipeline_hashes=sidecar.eval_pipeline_hashes,
        generated_condition_hashes=sidecar.generated_condition_hashes,
        replay_control_hashes={"none": frozen_hashes},
        external_pins=sidecar.external_pins,
    )
    validate_content_hash_sidecar_for_rows((row,), sidecar)


def test_logger_rejects_replay_metadata_sidecar_mismatch() -> None:
    row = _row_with_replay_metadata(
        generation_hashes={"outputs/cluster1/baseline.jsonl": HASH_B}
    )
    sidecar = _sidecar((row,))
    bad_sidecar = Cluster3ContentHashSidecar(
        schema_version=sidecar.schema_version,
        eval_pipeline_hashes=sidecar.eval_pipeline_hashes,
        generated_condition_hashes=sidecar.generated_condition_hashes,
        replay_control_hashes={"none": {"outputs/cluster1/baseline.jsonl": HASH_A}},
        external_pins=sidecar.external_pins,
    )
    with pytest.raises(ValueError, match="frozen Cluster 1"):
        validate_content_hash_sidecar_for_rows((row,), bad_sidecar)


def test_logger_replay_metadata_requires_recorded_control_condition() -> None:
    row = _row_with_replay_metadata(
        generation_hashes={"outputs/cluster1/baseline.jsonl": HASH_B},
        replay_control_condition=None,
    )
    sidecar = _sidecar((row,))
    with pytest.raises(ValueError, match="replay_control_condition"):
        validate_content_hash_sidecar_for_rows((row,), sidecar)


def test_logger_resume_matches_existing_prefix(tmp_path: Path) -> None:
    output = tmp_path / "cluster3.jsonl"
    first = _row()
    second = _row(attempt_index=1)
    sidecar = _sidecar((first, second))

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)
        logger.append(second)
    before = output.read_text(encoding="utf-8")

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="resume",
        fsync=False,
    ) as logger:
        assert logger.append(first) is False
        assert logger.append(second) is False

    assert output.read_text(encoding="utf-8") == before


def test_logger_resume_rejects_diverging_prefix(tmp_path: Path) -> None:
    output = tmp_path / "cluster3.jsonl"
    first = _row()
    second = _row(attempt_index=1)
    sidecar = _sidecar((first, second))

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)

    with pytest.raises(ValueError, match="deterministic resume prefix"):
        with Cluster3JsonlAppendLogger(
            output,
            content_hash_sidecar=sidecar,
            mode="resume",
            fsync=False,
        ) as logger:
            logger.append(second)


def test_logger_resume_rejects_extra_existing_rows(tmp_path: Path) -> None:
    output = tmp_path / "cluster3.jsonl"
    first = _row(attempt_index=0)
    second = _row(attempt_index=1)
    third = _row(attempt_index=2)
    sidecar = _sidecar((first, second, third))

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)
        logger.append(second)
        logger.append(third)

    with pytest.raises(ValueError, match="more rows than completed resume"):
        with Cluster3JsonlAppendLogger(
            output,
            content_hash_sidecar=sidecar,
            mode="resume",
            fsync=False,
        ) as logger:
            assert logger.append(first) is False
            assert logger.append(second) is False


def test_logger_manual_close_rejects_extra_existing_rows(tmp_path: Path) -> None:
    output = tmp_path / "cluster3.jsonl"
    first = _row(attempt_index=0)
    second = _row(attempt_index=1)
    sidecar = _sidecar((first, second))

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)
        logger.append(second)

    logger = Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="resume",
        fsync=False,
    )
    logger.open()
    assert logger.append(first) is False
    with pytest.raises(ValueError, match="more rows than completed resume"):
        logger.close()


def test_logger_close_does_not_expose_resume_validation_bypass(tmp_path: Path) -> None:
    output = tmp_path / "cluster3.jsonl"
    first = _row(attempt_index=0)
    second = _row(attempt_index=1)
    sidecar = _sidecar((first, second))

    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(first)
        logger.append(second)

    logger = Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=sidecar,
        mode="resume",
        fsync=False,
    )
    logger.open()
    assert logger.append(first) is False
    with pytest.raises(TypeError):
        logger.close(validate_resume=False)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="more rows than completed resume"):
        logger.close()


def test_logger_sidecar_atomic_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "cluster3.jsonl"
    row = _row()
    original_sidecar = _sidecar((row,))
    with Cluster3JsonlAppendLogger(
        output,
        content_hash_sidecar=original_sidecar,
        mode="overwrite",
        fsync=False,
    ) as logger:
        logger.append(row)

    sidecar_path = default_content_hash_sidecar_path(output)
    original_text = sidecar_path.read_text(encoding="utf-8")
    assert json.loads(original_text)["schema_version"] == CLUSTER3_RESULTS_SCHEMA_VERSION
    assert load_content_hash_sidecar(sidecar_path) == original_sidecar

    replacement_sidecar = Cluster3ContentHashSidecar(
        schema_version=CLUSTER3_RESULTS_SCHEMA_VERSION,
        eval_pipeline_hashes={"shared/eval/pipeline.py": HASH_B},
        generated_condition_hashes={"P": GEN_HASHES},
        replay_control_hashes={},
        external_pins={"python": "3.14.2"},
    )

    def fail_replace(self: Path, target: Path) -> Path:
        raise RuntimeError("simulated replace failure")

    monkeypatch.setattr(results_logger.Path, "replace", fail_replace)
    with pytest.raises(RuntimeError, match="simulated"):
        Cluster3JsonlAppendLogger(
            output,
            content_hash_sidecar=replacement_sidecar,
            mode="overwrite",
            fsync=False,
        ).open()

    assert sidecar_path.read_text(encoding="utf-8") == original_text
