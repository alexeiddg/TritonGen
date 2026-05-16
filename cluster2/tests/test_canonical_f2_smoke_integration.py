"""Canonical F2 smoke schema and preflight tests."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cluster2.experiments.run_f2_repair_smoke import (
    CORRECTNESS_FEEDBACK_TYPE,
    F2_SMOKE_SCHEMA_VERSION,
    MODAL_EVALUATION_MODE,
    MODAL_GENERATION_BACKEND,
    _corrected_source,
    load_f2_smoke_trace,
    run_f2_repair_smoke,
    validate_canonical_f2_smoke_artifacts,
    validate_f2_smoke_trace,
)
from cluster2.feedback.repair_loop import (
    REPAIR_LOOP_TERMINATED_STATUS,
    RepairEvaluationInput,
    RepairGenerationInput,
    run_repair_loop,
)
from cluster2.modal.correctness_runner import build_success_payload
from cluster2.modal.schemas import RemoteCorrectnessRequest, RemoteCorrectnessResult


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "cluster2" / "tests" / "fixtures"
EXPECTED_TRACE_DIR = FIXTURE_DIR / "expected_smoke_traces"
ARCHETYPE_CASES = (
    ("relu", "f2_corrupted_relu.py"),
    ("softmax", "f2_corrupted_softmax.py"),
    ("matmul", "f2_corrupted_matmul.py"),
)
TEST_MODEL_REVISION = "a" * 40
TEST_TOKENIZER_REVISION = "b" * 40


def test_schema_only_minimal_modal_trace_passes_validator() -> None:
    fixture_path = FIXTURE_DIR / "f2_corrupted_relu.py"
    rows = _minimal_modal_rows(fixture_path, archetype="relu")

    validate_f2_smoke_trace(
        rows,
        expected_failure_code="F2_NUMERIC_LARGE",
        fixture_path=fixture_path,
        expected_archetype="relu",
        expected_condition="C",
        expected_evaluation_mode=MODAL_EVALUATION_MODE,
        expected_generation_backend=MODAL_GENERATION_BACKEND,
    )


def test_schema_only_modal_trace_rejects_missing_modal_call_ids() -> None:
    fixture_path = FIXTURE_DIR / "f2_corrupted_relu.py"
    rows = [dict(row) for row in _minimal_modal_rows(fixture_path, archetype="relu")]
    rows[0]["modal_provenance"] = dict(rows[0]["modal_provenance"])
    rows[0]["modal_provenance"]["correctness_function_call_id"] = None

    with pytest.raises(ValueError, match="correctness_function_call_id"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=fixture_path,
            expected_archetype="relu",
            expected_condition="C",
            expected_evaluation_mode=MODAL_EVALUATION_MODE,
            expected_generation_backend=MODAL_GENERATION_BACKEND,
        )

    rows = [dict(row) for row in _minimal_modal_rows(fixture_path, archetype="relu")]
    rows[1]["modal_provenance"] = dict(rows[1]["modal_provenance"])
    rows[1]["modal_provenance"]["generation_input_id"] = None

    with pytest.raises(ValueError, match="generation_input_id"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=fixture_path,
            expected_archetype="relu",
            expected_condition="C",
            expected_evaluation_mode=MODAL_EVALUATION_MODE,
            expected_generation_backend=MODAL_GENERATION_BACKEND,
        )


def test_schema_only_modal_trace_rejects_floating_revision() -> None:
    fixture_path = FIXTURE_DIR / "f2_corrupted_relu.py"
    rows = [dict(row) for row in _minimal_modal_rows(fixture_path, archetype="relu")]
    rows[0]["model_revision"] = "refs/heads/main"

    with pytest.raises(ValueError, match="40-character commit SHA"):
        validate_f2_smoke_trace(
            rows,
            expected_failure_code="F2_NUMERIC_LARGE",
            fixture_path=fixture_path,
            expected_archetype="relu",
            expected_condition="C",
            expected_evaluation_mode=MODAL_EVALUATION_MODE,
            expected_generation_backend=MODAL_GENERATION_BACKEND,
        )


def test_schema_only_canonical_modal_artifacts_pass_validator(tmp_path: Path) -> None:
    _copy_fixtures(tmp_path)
    output_dir = tmp_path / "outputs" / "cluster2"
    output_dir.mkdir(parents=True)
    for archetype, fixture_name in ARCHETYPE_CASES:
        fixture_path = tmp_path / "cluster2" / "tests" / "fixtures" / fixture_name
        _write_jsonl(
            output_dir / f"smoke_f2_repair_{archetype}.jsonl",
            _minimal_modal_rows(fixture_path, archetype=archetype),
        )

    validate_canonical_f2_smoke_artifacts(repo_root=tmp_path)


@pytest.mark.parametrize(("archetype", "fixture_name"), ARCHETYPE_CASES)
def test_committed_modal_smoke_trace_fixture_passes_validator(
    archetype: str,
    fixture_name: str,
) -> None:
    rows = load_f2_smoke_trace(EXPECTED_TRACE_DIR / f"modal_{archetype}.jsonl")

    validate_f2_smoke_trace(
        rows,
        expected_failure_code="F2_NUMERIC_LARGE",
        fixture_path=FIXTURE_DIR / fixture_name,
        expected_archetype=archetype,
        expected_condition="C",
        expected_evaluation_mode=MODAL_EVALUATION_MODE,
        expected_generation_backend=MODAL_GENERATION_BACKEND,
    )


def test_local_runner_modal_schema_artifacts_pass_canonical_validator(
    tmp_path: Path,
) -> None:
    _copy_fixtures(tmp_path)
    output_dir = tmp_path / "outputs" / "cluster2"
    output_dir.mkdir(parents=True)

    for archetype, fixture_name in ARCHETYPE_CASES:
        fixture_path = tmp_path / "cluster2" / "tests" / "fixtures" / fixture_name
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
            output_path=output_dir / f"smoke_f2_repair_{archetype}.jsonl",
            repair_budget=1,
            mock_repair=False,
            model_revision=TEST_MODEL_REVISION,
            tokenizer_revision=TEST_TOKENIZER_REVISION,
            generation_adapter=generation_adapter,
            correctness_adapter=correctness_adapter,
        )

    validate_canonical_f2_smoke_artifacts(repo_root=tmp_path)


def test_canonical_schema_repair_feedback_is_numerical_c_only(
    tmp_path: Path,
) -> None:
    fixture_path = FIXTURE_DIR / "f2_corrupted_relu.py"
    rows = _minimal_modal_rows(fixture_path, archetype="relu")
    _write_jsonl(tmp_path / "relu.jsonl", rows)

    repair_rows = [row for row in rows if row["repair_iteration"] > 0]
    assert repair_rows
    for row in repair_rows:
        feedback = row["feedback_content"]
        assert row["condition"] == "C"
        assert row["feedback_type"] == CORRECTNESS_FEEDBACK_TYPE
        assert isinstance(feedback, str)
        assert "max_abs_diff=1.0" in feedback
        assert "max_rel_diff=1.0" in feedback
        assert "compile" not in feedback.lower()
        assert "signature" not in feedback.lower()
        assert "surface" not in feedback.lower()


def test_f0_f1_failures_do_not_trigger_c_repair_generation() -> None:
    generation_calls: list[RepairGenerationInput] = []

    def generation(request: RepairGenerationInput) -> str:
        generation_calls.append(request)
        return "unreachable repair source"

    def evaluation(request: RepairEvaluationInput) -> object:
        return SimpleNamespace(
            level_reached=1,
            functional_success=False,
            repair_set_success=False,
            eval_set_success=False,
            failure_code="F1_COMPILE",
            public_failure_summary="compile failed before Level 2",
        )

    result = run_repair_loop(
        condition="C",
        base_prompt="Implement the kernel.",
        base_seed=731,
        generation=generation,
        evaluation=evaluation,
        repair_budget=2,
        seed_candidate_source="seed fixture source",
    )

    assert result.status == REPAIR_LOOP_TERMINATED_STATUS
    assert generation_calls == []


def _minimal_modal_rows(
    fixture_path: Path,
    *,
    archetype: str,
) -> tuple[dict[str, Any], ...]:
    fixture_source = fixture_path.read_text(encoding="utf-8")
    fixture_hash = hashlib.sha256(fixture_source.encode("utf-8")).hexdigest()
    feedback = "Numeric mismatch: max_abs_diff=1.0 max_rel_diff=1.0"
    prompt = (
        "Base task:\n"
        "Implement the kernel.\n\n"
        "Previous source:\n"
        f"{fixture_source}\n\n"
        "Failure code:\n"
        "F2_NUMERIC_LARGE\n\n"
        "Feedback:\n"
        f"{feedback}\n\n"
        "Public details:\n"
        f"{feedback}\n\n"
        "Instruction:\n"
        "Produce a corrected complete Triton Python module."
    )
    base = {
        "schema_version": F2_SMOKE_SCHEMA_VERSION,
        "run_id": f"f2-smoke-{archetype}-{fixture_hash[:12]}-b731-r1-modal",
        "condition": "C",
        "archetype": archetype,
        "kernel_class": {
            "relu": "elementwise",
            "softmax": "reduction",
            "matmul": "matmul",
        }[archetype],
        "kernel_name": {
            "relu": "relu",
            "softmax": "softmax",
            "matmul": "gemm",
        }[archetype],
        "dtype": "fp32",
        "base_seed": 731,
        "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "model_revision": TEST_MODEL_REVISION,
        "tokenizer_revision": TEST_TOKENIZER_REVISION,
        "evaluation_mode": MODAL_EVALUATION_MODE,
        "generation_backend": MODAL_GENERATION_BACKEND,
        "fixture_path": fixture_path.as_posix(),
        "fixture_sha256": fixture_hash,
        "repair_budget": 1,
        "repair_converged": True,
        "successful_attempt_index": 1,
        "budget_exhausted": False,
        "repair_loop_status": "success",
    }
    return (
        {
            **base,
            "repair_iteration": 0,
            "candidate_origin": "seed_fixture",
            "modal_provenance": _modal_context_trace(
                attempt_index=0,
                include_generation=False,
            ),
            "source_sha256": fixture_hash,
            "level_reached": 2,
            "failure_code": "F2_NUMERIC_LARGE",
            "feedback_type": None,
            "feedback_content": None,
            "feedback_prompt_sha256": None,
            "feedback_prompt_content": None,
            "functional_success": False,
            "repair_set_success": False,
            "eval_set_success": False,
            "eval_summary": {
                "correctness_error": feedback,
                "max_abs_diff": 1.0,
                "max_rel_diff": 1.0,
            },
        },
        {
            **base,
            "repair_iteration": 1,
            "candidate_origin": "modal_repair",
            "modal_provenance": _modal_context_trace(
                attempt_index=1,
                include_generation=True,
            ),
            "source_sha256": hashlib.sha256(b"corrected source").hexdigest(),
            "level_reached": 2,
            "failure_code": None,
            "feedback_type": CORRECTNESS_FEEDBACK_TYPE,
            "feedback_content": feedback,
            "feedback_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "feedback_prompt_content": prompt,
            "functional_success": True,
            "repair_set_success": True,
            "eval_set_success": True,
            "eval_summary": {
                "correctness_error": None,
                "max_abs_diff": 0.0,
                "max_rel_diff": 0.0,
            },
        },
    )


def _copy_fixtures(repo_root: Path) -> None:
    target = repo_root / "cluster2" / "tests" / "fixtures"
    target.mkdir(parents=True)
    for _, fixture_name in ARCHETYPE_CASES:
        shutil.copyfile(FIXTURE_DIR / fixture_name, target / fixture_name)


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


def _modal_context_trace(
    *,
    attempt_index: int,
    include_generation: bool,
) -> dict[str, str | None]:
    generation_context = (
        _generation_modal_context(attempt_index) if include_generation else {}
    )
    correctness_context = _correctness_modal_context(attempt_index)
    return {
        "modal_generation_gpu": "L4",
        "modal_eval_gpu": "L4",
        "generation_function_call_id": generation_context.get("function_call_id"),
        "generation_input_id": generation_context.get("input_id"),
        "correctness_function_call_id": correctness_context["function_call_id"],
        "correctness_input_id": correctness_context["input_id"],
    }


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


def _write_jsonl(path: Path, rows: tuple[dict[str, Any], ...]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        + "\n",
        encoding="utf-8",
    )
