"""Integration tests for the synthetic F2 C repair-loop smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cluster2.experiments.run_f2_repair_smoke import (
    CORRECTNESS_FEEDBACK_TYPE,
    FORBIDDEN_SMOKE_FEEDBACK_MARKERS,
    MODAL_EVALUATION_MODE,
    MODAL_GENERATION_BACKEND,
    MOCK_EVALUATION_MODE,
    MOCK_GENERATION_BACKEND,
    MOCK_REPAIR_CORRECT,
    MOCK_REPAIR_UNCHANGED,
    _corrected_source,
    _evaluate_mock_smoke_source,
    _extract_prompt_section,
    _normalize_generated_source,
    _resolve_archetype,
    run_f2_repair_smoke,
    validate_canonical_f2_smoke_artifacts,
    validate_f2_smoke_trace,
)
from cluster2.modal.correctness_runner import build_success_payload
from cluster2.modal.schemas import RemoteCorrectnessRequest, RemoteCorrectnessResult


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "cluster2" / "tests" / "fixtures"
EXPECTED_TRACE_DIR = FIXTURE_DIR / "expected_smoke_traces"
TEST_MODEL_REVISION = "a" * 40
TEST_TOKENIZER_REVISION = "b" * 40

FIXTURE_CASES = (
    (
        "relu",
        FIXTURE_DIR / "f2_corrupted_relu.py",
        "F2_NUMERIC_LARGE",
    ),
    (
        "softmax",
        FIXTURE_DIR / "f2_corrupted_softmax.py",
        "F2_NUMERIC_LARGE",
    ),
    (
        "matmul",
        FIXTURE_DIR / "f2_corrupted_matmul.py",
        "F2_NUMERIC_LARGE",
    ),
)


@pytest.mark.parametrize(("archetype", "fixture_path", "failure_code"), FIXTURE_CASES)
def test_f2_smoke_activates_repair_loop_for_each_fixture(
    archetype: str,
    fixture_path: Path,
    failure_code: str,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{archetype}.jsonl"

    rows = run_f2_repair_smoke(
        fixture_path=fixture_path,
        archetype=archetype,
        output_path=output_path,
        repair_budget=1,
        mock_repair=True,
        mock_repair_mode=MOCK_REPAIR_CORRECT,
    )

    assert output_path.is_file()
    assert _read_jsonl(output_path) == list(rows)
    assert [row["repair_iteration"] for row in rows] == [0, 1]

    seed_row = rows[0]
    assert seed_row["candidate_origin"] == "seed_fixture"
    assert seed_row["evaluation_mode"] == MOCK_EVALUATION_MODE
    assert seed_row["generation_backend"] == MOCK_GENERATION_BACKEND
    assert seed_row["level_reached"] == 2
    assert seed_row["failure_code"] == failure_code
    assert seed_row["functional_success"] is False
    assert seed_row["repair_set_success"] is False
    assert seed_row["feedback_content"] is None

    repair_row = rows[1]
    assert repair_row["candidate_origin"] == "mock_repair"
    assert repair_row["evaluation_mode"] == MOCK_EVALUATION_MODE
    assert repair_row["generation_backend"] == MOCK_GENERATION_BACKEND
    assert repair_row["level_reached"] == 2
    assert repair_row["feedback_type"] == CORRECTNESS_FEEDBACK_TYPE
    assert repair_row["feedback_content"]
    assert repair_row["feedback_prompt_sha256"]
    assert repair_row["feedback_prompt_content"]
    assert repair_row["functional_success"] is True
    assert repair_row["repair_converged"] is True
    assert repair_row["successful_attempt_index"] == 1
    assert repair_row["budget_exhausted"] is False

    _assert_numerical_feedback(repair_row["feedback_content"])
    _assert_feedback_prompt_trace(repair_row)
    validate_f2_smoke_trace(rows, expected_failure_code=failure_code)


def test_f2_smoke_records_budget_exhaustion_when_mock_repair_does_not_fix(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "relu_exhausted.jsonl"

    rows = run_f2_repair_smoke(
        fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
        archetype="elementwise",
        output_path=output_path,
        repair_budget=2,
        mock_repair=True,
        mock_repair_mode=MOCK_REPAIR_UNCHANGED,
    )

    assert [row["repair_iteration"] for row in rows] == [0, 1, 2]
    assert all(row["functional_success"] is False for row in rows)
    assert rows[-1]["repair_converged"] is False
    assert rows[-1]["successful_attempt_index"] is None
    assert rows[-1]["budget_exhausted"] is True
    assert rows[-1]["repair_loop_status"] == "exhausted"
    assert rows[1]["feedback_type"] == CORRECTNESS_FEEDBACK_TYPE
    assert rows[2]["feedback_type"] == CORRECTNESS_FEEDBACK_TYPE
    _assert_numerical_feedback(rows[1]["feedback_content"])
    _assert_numerical_feedback(rows[2]["feedback_content"])
    _assert_feedback_prompt_trace(rows[1])
    _assert_feedback_prompt_trace(rows[2])
    validate_f2_smoke_trace(rows, expected_failure_code="F2_NUMERIC_LARGE")


def test_f2_smoke_non_mock_path_uses_injected_modal_adapters(tmp_path: Path) -> None:
    fixture_path = FIXTURE_DIR / "f2_corrupted_relu.py"
    fixture_source = fixture_path.read_text(encoding="utf-8")
    corrected_source = _corrected_source(fixture_source, "relu")
    output_path = tmp_path / "relu_modal_adapter.jsonl"
    generation_calls: list[dict[str, Any]] = []
    correctness_calls: list[RemoteCorrectnessRequest] = []

    def generation_adapter(**kwargs: Any) -> dict[str, Any]:
        generation_calls.append(kwargs)
        assert kwargs["prompt"].startswith("Base task:")
        identity = kwargs["identity"]
        return {
            "source": corrected_source,
            "modal_context": _generation_modal_context(identity.attempt_index),
        }

    def correctness_adapter(request: RemoteCorrectnessRequest) -> dict[str, Any]:
        correctness_calls.append(request)
        return _remote_correctness_payload(
            request,
            functional_success=request.source
            == _normalize_generated_source(corrected_source),
        )

    rows = run_f2_repair_smoke(
        fixture_path=fixture_path,
        archetype="relu",
        output_path=output_path,
        repair_budget=1,
        mock_repair=False,
        model_revision=TEST_MODEL_REVISION,
        tokenizer_revision=TEST_TOKENIZER_REVISION,
        generation_adapter=generation_adapter,
        correctness_adapter=correctness_adapter,
    )

    assert len(generation_calls) == 1
    assert len(correctness_calls) == 2
    assert [request.identity.attempt_index for request in correctness_calls] == [0, 1]
    assert rows[0]["candidate_origin"] == "seed_fixture"
    assert rows[0]["evaluation_mode"] == MODAL_EVALUATION_MODE
    assert rows[0]["generation_backend"] == MODAL_GENERATION_BACKEND
    assert rows[0]["failure_code"] == "F2_NUMERIC_LARGE"
    assert rows[1]["candidate_origin"] == "modal_repair"
    assert rows[1]["functional_success"] is True
    assert rows[1]["repair_converged"] is True
    _assert_feedback_prompt_trace(rows[1])
    validate_f2_smoke_trace(rows, expected_failure_code="F2_NUMERIC_LARGE")


def test_mock_evaluator_does_not_mark_marker_removal_as_correct() -> None:
    fixture_source = (FIXTURE_DIR / "f2_corrupted_matmul.py").read_text(
        encoding="utf-8"
    )
    near_miss_source = fixture_source.replace("acc + 1.0", "acc + 2.0", 1)
    result = _evaluate_mock_smoke_source(
        near_miss_source,
        spec=_resolve_archetype("matmul"),
        dtype="fp32",
        base_seed=731,
        attempt_index=1,
        fixture_source=fixture_source,
        corrected_source=_corrected_source(fixture_source, "matmul"),
    )

    assert result.functional_success is False
    assert result.failure_code == "F2_NUMERIC_LARGE"


@pytest.mark.parametrize("archetype", ("relu", "softmax", "matmul"))
def test_expected_smoke_trace_fixtures_validate(archetype: str) -> None:
    path = EXPECTED_TRACE_DIR / f"{archetype}.jsonl"
    fixture_path = FIXTURE_DIR / f"f2_corrupted_{archetype}.py"
    rows = _read_jsonl(path)

    validate_f2_smoke_trace(
        rows,
        expected_failure_code="F2_NUMERIC_LARGE",
        fixture_path=fixture_path,
        expected_archetype=archetype,
    )
    assert rows[0]["archetype"] == archetype
    assert rows[0]["candidate_origin"] == "seed_fixture"
    assert rows[1]["feedback_type"] == CORRECTNESS_FEEDBACK_TYPE
    _assert_numerical_feedback(rows[1]["feedback_content"])
    _assert_feedback_prompt_trace(rows[1])


def test_expected_smoke_trace_rejects_stale_fixture_hash() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[0]["fixture_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="fixture_sha256 is stale"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_missing_repair_iteration() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")[:1]

    with pytest.raises(ValueError, match="at least one repair iteration"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_iteration_zero_feedback_fields() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[0]["feedback_type"] = rows[1]["feedback_type"]
    rows[0]["feedback_content"] = rows[1]["feedback_content"]
    rows[0]["feedback_prompt_content"] = rows[1]["feedback_prompt_content"]
    rows[0]["feedback_prompt_sha256"] = rows[1]["feedback_prompt_sha256"]

    with pytest.raises(ValueError, match="iteration 0 must not record repair feedback"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_iteration_zero_success_flag() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[0]["functional_success"] = True
    rows[0]["repair_set_success"] = True
    rows[0]["eval_set_success"] = True

    with pytest.raises(ValueError, match="functional_success=False"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_repair_row_origin_mismatch() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[1]["candidate_origin"] = "seed_fixture"

    with pytest.raises(ValueError, match="candidate_origin"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_repair_row_non_f2_failure() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[1]["functional_success"] = False
    rows[1]["repair_set_success"] = False
    rows[1]["eval_set_success"] = False
    rows[1]["level_reached"] = 1
    rows[1]["failure_code"] = "F1_COMPILE"

    with pytest.raises(ValueError, match="failed outcome must reach Level 2"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_inconsistent_repair_budget() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[1]["repair_budget"] = rows[0]["repair_budget"] + 1

    with pytest.raises(ValueError, match="consistent repair_budget"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_truncated_budget_exhaustion() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    for row in rows:
        row["repair_budget"] = 5
        row["repair_converged"] = False
        row["successful_attempt_index"] = None
        row["budget_exhausted"] = True
        row["repair_loop_status"] = "exhausted"
    rows[1]["functional_success"] = False
    rows[1]["repair_set_success"] = False
    rows[1]["eval_set_success"] = False
    rows[1]["failure_code"] = "F2_NUMERIC_LARGE"

    with pytest.raises(ValueError, match="exhausted trace must end at repair_budget"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_rows_after_convergence() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    extra_row = dict(rows[1])
    extra_row["repair_iteration"] = 2
    extra_row["functional_success"] = False
    extra_row["repair_set_success"] = False
    extra_row["eval_set_success"] = False
    extra_row["failure_code"] = "F2_NUMERIC_LARGE"
    extra_row["source_sha256"] = "1" * 64
    rows.append(extra_row)
    for row in rows:
        row["repair_budget"] = 5
        row["repair_converged"] = True
        row["successful_attempt_index"] = 1
        row["budget_exhausted"] = False

    with pytest.raises(
        ValueError,
        match="converged trace must end at successful_attempt_index",
    ):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_multiple_success_rows() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    extra_row = dict(rows[1])
    extra_row["repair_iteration"] = 2
    extra_row["source_sha256"] = "1" * 64
    rows.append(extra_row)
    for row in rows:
        row["repair_budget"] = 5
        row["repair_converged"] = True
        row["successful_attempt_index"] = 2
        row["budget_exhausted"] = False
        row["repair_loop_status"] = "success"

    with pytest.raises(
        ValueError,
        match="converged trace must record exactly one successful row",
    ):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_terminal_status_disagreement() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[0]["repair_converged"] = False

    with pytest.raises(ValueError, match="consistent terminal status fields"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_repair_loop_status_mismatch() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    for row in rows:
        row["repair_loop_status"] = "exhausted"

    with pytest.raises(ValueError, match="repair_loop_status must match terminal flags"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_exhausted_successful_attempt_index() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    for row in rows:
        row["repair_converged"] = False
        row["budget_exhausted"] = True
        row["repair_loop_status"] = "exhausted"
        row["successful_attempt_index"] = 1
    rows[1]["functional_success"] = False
    rows[1]["repair_set_success"] = False
    rows[1]["eval_set_success"] = False
    rows[1]["failure_code"] = "F2_NUMERIC_LARGE"

    with pytest.raises(
        ValueError,
        match="exhausted trace must not record successful_attempt_index",
    ):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("repair_converged", "yes"),
        ("budget_exhausted", "false"),
    ),
)
def test_expected_smoke_trace_rejects_string_terminal_booleans(
    field_name: str,
    value: str,
) -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    rows[1][field_name] = value

    with pytest.raises(ValueError, match=f"{field_name} must be a boolean"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_expected_smoke_trace_rejects_non_numerical_feedback() -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    feedback = rows[1]["feedback_content"]
    prompt = rows[1]["feedback_prompt_content"]
    replacement = "Please try again with a different implementation."
    assert isinstance(feedback, str)
    assert isinstance(prompt, str)

    rows[1]["feedback_content"] = replacement
    rows[1]["feedback_prompt_content"] = prompt.replace(feedback, replacement, 1)
    rows[1]["feedback_prompt_sha256"] = hashlib.sha256(
        rows[1]["feedback_prompt_content"].encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValueError, match="numerical correctness details"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


@pytest.mark.parametrize(
    "replacement",
    (
        "Please use this information. max_abs_diff max_rel_diff",
        "max_abs_diff= max_rel_diff= no numeric values",
    ),
)
def test_expected_smoke_trace_rejects_loose_numerical_markers(
    replacement: str,
) -> None:
    rows = _read_jsonl(EXPECTED_TRACE_DIR / "relu.jsonl")
    feedback = rows[1]["feedback_content"]
    prompt = rows[1]["feedback_prompt_content"]
    assert isinstance(feedback, str)
    assert isinstance(prompt, str)

    rows[1]["feedback_content"] = replacement
    rows[1]["feedback_prompt_content"] = prompt.replace(feedback, replacement, 1)
    rows[1]["feedback_prompt_sha256"] = hashlib.sha256(
        rows[1]["feedback_prompt_content"].encode("utf-8")
    ).hexdigest()

    with pytest.raises(ValueError, match="numerical correctness details"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=FIXTURE_DIR / "f2_corrupted_relu.py",
            expected_archetype="relu",
        )


def test_canonical_smoke_preflight_rejects_mock_trace_artifacts(tmp_path: Path) -> None:
    _copy_canonical_smoke_artifacts(tmp_path, modalized=False)

    with pytest.raises(ValueError, match="expected evaluation_mode"):
        validate_canonical_f2_smoke_artifacts(repo_root=tmp_path)


def test_canonical_smoke_preflight_accepts_modal_trace_artifacts(tmp_path: Path) -> None:
    _copy_canonical_smoke_artifacts(tmp_path, modalized=True)

    validate_canonical_f2_smoke_artifacts(repo_root=tmp_path)


def test_canonical_smoke_preflight_rejects_gc_trace_artifacts(tmp_path: Path) -> None:
    _copy_canonical_smoke_artifacts(tmp_path, modalized=True, condition="G+C")

    with pytest.raises(ValueError, match="expected condition"):
        validate_canonical_f2_smoke_artifacts(repo_root=tmp_path)


def _assert_numerical_feedback(feedback_content: str) -> None:
    lowered = feedback_content.lower()
    assert "max_abs_diff" in feedback_content
    assert "max_rel_diff" in feedback_content
    assert "numeric" in lowered or "shape" in lowered or "nan" in lowered
    assert "compile_error" not in lowered
    assert "signature_error" not in lowered
    assert "correctness_error" not in lowered
    for marker in FORBIDDEN_SMOKE_FEEDBACK_MARKERS:
        assert marker.lower() not in lowered


def _assert_feedback_prompt_trace(row: dict[str, object]) -> None:
    feedback_content = row["feedback_content"]
    prompt_content = row["feedback_prompt_content"]
    assert isinstance(feedback_content, str)
    assert isinstance(prompt_content, str)
    assert row["feedback_prompt_sha256"] == hashlib.sha256(
        prompt_content.encode("utf-8")
    ).hexdigest()
    assert _extract_prompt_section(prompt_content, "Feedback") == feedback_content
    assert "Previous source:" in prompt_content


def _remote_correctness_payload(
    request: RemoteCorrectnessRequest,
    *,
    functional_success: bool,
) -> dict[str, Any]:
    result = RemoteCorrectnessResult(
        identity=request.identity,
        functional_success=functional_success,
        repair_set_success=functional_success,
        eval_set_success=functional_success,
        failure_code=None if functional_success else "F2_NUMERIC_LARGE",
        correctness_error=(
            None
            if functional_success
            else "F2_NUMERIC_LARGE max_abs_diff=1.0 max_rel_diff=1.0"
        ),
        feedback=None if functional_success else "max_abs_diff=1.0 max_rel_diff=1.0",
        num_repair_shapes=1,
        num_eval_shapes=1,
        num_test_shapes=2,
        shapes_passed=2 if functional_success else 0,
        repair_shapes_passed=1 if functional_success else 0,
        eval_shapes_passed=1 if functional_success else 0,
        max_abs_diff=0.0 if functional_success else 1.0,
        max_rel_diff=0.0 if functional_success else 1.0,
    )
    payload = build_success_payload(request, result)
    payload["modal_context"] = _correctness_modal_context(
        request.identity.attempt_index
    )
    return payload


def _generation_modal_context(attempt_index: int) -> dict[str, str]:
    return {
        "function_call_id": f"generation-call-{attempt_index}",
        "input_id": f"generation-input-{attempt_index}",
        "modal_generation_gpu": "L4",
    }


def _correctness_modal_context(attempt_index: int) -> dict[str, str]:
    return {
        "function_call_id": f"correctness-call-{attempt_index}",
        "input_id": f"correctness-input-{attempt_index}",
        "modal_eval_gpu": "L4",
    }


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _copy_canonical_smoke_artifacts(
    repo_root: Path,
    *,
    modalized: bool,
    condition: str = "C",
) -> None:
    fixture_target_dir = repo_root / "cluster2" / "tests" / "fixtures"
    trace_target_dir = repo_root / "outputs" / "cluster2"
    fixture_target_dir.mkdir(parents=True, exist_ok=True)
    trace_target_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "f2_corrupted_relu.py",
        "f2_corrupted_softmax.py",
        "f2_corrupted_matmul.py",
    ):
        (fixture_target_dir / name).write_text(
            (FIXTURE_DIR / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    for archetype in ("relu", "softmax", "matmul"):
        output_path = trace_target_dir / f"smoke_f2_repair_{archetype}.jsonl"
        if modalized:
            fixture_path = fixture_target_dir / f"f2_corrupted_{archetype}.py"
            corrected_source = _corrected_source(
                fixture_path.read_text(encoding="utf-8"),
                archetype,
            )

            def generation_adapter(**kwargs: Any) -> dict[str, Any]:
                identity = kwargs["identity"]
                return {
                    "source": corrected_source,
                    "modal_context": _generation_modal_context(identity.attempt_index),
                }

            def correctness_adapter(request: RemoteCorrectnessRequest) -> dict[str, Any]:
                return _remote_correctness_payload(
                    request,
                    functional_success=request.identity.attempt_index > 0,
                )

            run_f2_repair_smoke(
                fixture_path=fixture_path,
                archetype=archetype,
                output_path=output_path,
                condition=condition,
                repair_budget=1,
                mock_repair=False,
                model_revision=TEST_MODEL_REVISION,
                tokenizer_revision=TEST_TOKENIZER_REVISION,
                generation_adapter=generation_adapter,
                correctness_adapter=correctness_adapter,
            )
        else:
            _write_jsonl(output_path, _read_jsonl(EXPECTED_TRACE_DIR / f"{archetype}.jsonl"))


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        + "\n",
        encoding="utf-8",
    )
