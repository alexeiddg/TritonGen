"""Deterministic synthetic F2 smoke for Cluster 2 repair-loop activation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import types
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cluster2.constants import (
    DEFAULT_C2_MODAL_EVAL_GPU,
    DEFAULT_C2_MODAL_GENERATION_GPU,
    DEFAULT_REPAIR_BUDGET,
    generation_mode_for_condition,
    source_class_for_condition,
)
from cluster2.feedback.prompts import (
    CORRECTNESS_FEEDBACK_TYPE,
    FORBIDDEN_FEEDBACK_TERMS,
    validate_no_forbidden_feedback_terms,
)
from cluster2.feedback.repair_loop import (
    REPAIR_LOOP_EXHAUSTED_STATUS,
    REPAIR_LOOP_SUCCESS_STATUS,
    RepairEvaluationInput,
    RepairGenerationInput,
    run_repair_loop,
)
from shared.eval.correctness_shapes import CorrectnessShapeSets
from shared.eval.levels.level0_ast_sanitizer import check_level0_ast_sanitizer
from shared.eval.levels.level0_parse import check_parse, check_signature
from shared.eval.levels.level2_correctness import (
    Level2CandidateRequest,
    evaluate_level2_correctness,
)
from cluster2.modal.schemas import EvalIdentity, RemoteCorrectnessRequest
from cluster2.validation.modal_correctness_check import extract_correctness_result


BASE_SEED = 731
DEFAULT_DTYPE = "fp32"
MODEL_ID_DEFAULT = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
MAX_NEW_TOKENS_DEFAULT = 512
MOCK_REPAIR_CORRECT = "correct"
MOCK_REPAIR_UNCHANGED = "unchanged"
MOCK_EVALUATION_MODE = "mock_local_marker"
MODAL_EVALUATION_MODE = "modal_correctness"
MOCK_GENERATION_BACKEND = "mock_local"
MODAL_GENERATION_BACKEND = "modal_generation"
F2_SMOKE_FAILURE_CODES = frozenset(
    {
        "F2_NUMERIC_LARGE",
        "F2_NUMERIC_NAN",
        "F2_SHAPE_MISMATCH",
    }
)

RemoteGenerationAdapter = Callable[..., dict[str, Any]]
RemoteCorrectnessAdapter = Callable[[RemoteCorrectnessRequest], dict[str, Any]]


@dataclass(frozen=True)
class F2SmokeArchetype:
    name: str
    kernel_class: str
    kernel_name: str
    fixture_filename: str
    expected_failure_code: str


ARCHETYPES: dict[str, F2SmokeArchetype] = {
    "relu": F2SmokeArchetype(
        name="relu",
        kernel_class="elementwise",
        kernel_name="relu",
        fixture_filename="f2_corrupted_relu.py",
        expected_failure_code="F2_NUMERIC_LARGE",
    ),
    "softmax": F2SmokeArchetype(
        name="softmax",
        kernel_class="reduction",
        kernel_name="softmax",
        fixture_filename="f2_corrupted_softmax.py",
        expected_failure_code="F2_NUMERIC_LARGE",
    ),
    "matmul": F2SmokeArchetype(
        name="matmul",
        kernel_class="matmul",
        kernel_name="gemm",
        fixture_filename="f2_corrupted_matmul.py",
        expected_failure_code="F2_NUMERIC_LARGE",
    ),
}
ARCHETYPE_ALIASES = {
    "elementwise": "relu",
    "reduction": "softmax",
    "gemm": "matmul",
}

FORBIDDEN_SMOKE_FEEDBACK_MARKERS: tuple[str, ...] = (
    "SyntaxError",
    "ParseError",
    "SignatureError",
    "CompilationError",
    "RuntimeError",
    "tl.",
    "triton.",
    "AST sanitizer",
    "missing @triton.jit",
    "missing launcher",
    "wrong signature",
    "traceback",
    "CUDA compiler",
    "PTX",
    "LLVM",
    "C++ traceback",
    "pro" + "filer",
    "tim" + "ing",
    "speed" + "up",
    "hidden",
    "private",
    "eval_shape_set",
    "edge cases",
    *FORBIDDEN_FEEDBACK_TERMS,
)
FEEDBACK_PROMPT_SECTION_NAMES: tuple[str, ...] = (
    "Base task",
    "Previous source",
    "Failure code",
    "Feedback",
    "Public details",
    "Instruction",
)


def run_f2_repair_smoke(
    *,
    fixture_path: str | Path,
    archetype: str,
    output_path: str | Path,
    condition: str = "C",
    repair_budget: int = DEFAULT_REPAIR_BUDGET,
    mock_repair: bool = False,
    mock_repair_mode: str = MOCK_REPAIR_CORRECT,
    base_seed: int = BASE_SEED,
    dtype: str = DEFAULT_DTYPE,
    model_id: str = MODEL_ID_DEFAULT,
    model_revision: str | None = None,
    tokenizer_revision: str | None = None,
    temperature: float = 0.2,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    grammar_variant: str | None = None,
    modal_generation_gpu: str = DEFAULT_C2_MODAL_GENERATION_GPU,
    modal_eval_gpu: str = DEFAULT_C2_MODAL_EVAL_GPU,
    generation_adapter: RemoteGenerationAdapter | None = None,
    correctness_adapter: RemoteCorrectnessAdapter | None = None,
) -> tuple[dict[str, Any], ...]:
    """Run one synthetic F2 repair-loop smoke and write its JSONL trace."""

    if mock_repair_mode not in {MOCK_REPAIR_CORRECT, MOCK_REPAIR_UNCHANGED}:
        raise ValueError("unsupported mock_repair_mode")
    if repair_budget < 0 or repair_budget > DEFAULT_REPAIR_BUDGET:
        raise ValueError(f"repair_budget must be between 0 and {DEFAULT_REPAIR_BUDGET}")
    if modal_eval_gpu != DEFAULT_C2_MODAL_EVAL_GPU:
        raise ValueError("F2 smoke correctness must use the locked C2 L4 eval GPU")
    if modal_generation_gpu != DEFAULT_C2_MODAL_GENERATION_GPU:
        raise ValueError("F2 smoke generation must use the locked C2 L4 generation GPU")
    if not mock_repair:
        _require_real_generation_metadata(
            model_revision=model_revision,
            tokenizer_revision=tokenizer_revision,
        )

    if mock_repair:
        _ensure_mock_level2_runtime_available()
    spec = _resolve_archetype(archetype)
    path = Path(fixture_path)
    fixture_source = path.read_text(encoding="utf-8")
    corrected_source = _corrected_source(fixture_source, spec.name)
    fixture_hash = _sha256(fixture_source)
    evaluation_mode = MOCK_EVALUATION_MODE if mock_repair else MODAL_EVALUATION_MODE
    generation_backend = MOCK_GENERATION_BACKEND if mock_repair else MODAL_GENERATION_BACKEND
    mode_label = "mock" if mock_repair else "modal"
    run_id = (
        f"f2-smoke-{spec.name}-{fixture_hash[:12]}-"
        f"b{base_seed}-r{repair_budget}-{mode_label}"
    )
    base_prompt = (
        f"Implement the {spec.kernel_name} kernel as a complete Triton Python module."
    )

    generation_inputs: dict[int, RepairGenerationInput] = {}
    source_by_attempt: dict[int, str] = {0: fixture_source}
    result_by_attempt: dict[int, object] = {}

    def generation(request: RepairGenerationInput) -> str:
        generation_inputs[request.attempt_index] = request
        if request.attempt_index == 0:
            raise AssertionError("seed candidate should bypass iteration-0 generation")
        if mock_repair:
            source = (
                corrected_source
                if mock_repair_mode == MOCK_REPAIR_CORRECT
                else fixture_source
            )
        else:
            source = _generate_modal_repair_source(
                request,
                condition=condition,
                spec=spec,
                run_id=run_id,
                dtype=dtype,
                model_id=model_id,
                model_revision=str(model_revision),
                tokenizer_revision=str(tokenizer_revision),
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                grammar_variant=grammar_variant,
                modal_generation_gpu=modal_generation_gpu,
                generation_adapter=generation_adapter,
            )
        source_by_attempt[request.attempt_index] = source
        return source

    def evaluation(request: RepairEvaluationInput) -> object:
        source_by_attempt[request.attempt_index] = request.source
        if mock_repair:
            result = _evaluate_mock_smoke_source(
                request.source,
                spec=spec,
                dtype=dtype,
                base_seed=base_seed,
                attempt_index=request.attempt_index,
                fixture_source=fixture_source,
                corrected_source=corrected_source,
            )
        else:
            result = _evaluate_modal_smoke_source(
                request.source,
                condition=condition,
                spec=spec,
                run_id=run_id,
                dtype=dtype,
                base_seed=base_seed,
                attempt_index=request.attempt_index,
                correctness_adapter=correctness_adapter,
            )
        result_by_attempt[request.attempt_index] = result
        return result

    repair_result = run_repair_loop(
        condition=condition,
        base_prompt=base_prompt,
        base_seed=base_seed,
        generation=generation,
        evaluation=evaluation,
        repair_budget=repair_budget,
        seed_candidate_source=fixture_source,
    )
    rows = _build_trace_rows(
        repair_result=repair_result,
        result_by_attempt=result_by_attempt,
        source_by_attempt=source_by_attempt,
        generation_inputs=generation_inputs,
        run_id=run_id,
        condition=condition,
        spec=spec,
        fixture_path=path,
        fixture_hash=fixture_hash,
        repair_budget=repair_budget,
        base_seed=base_seed,
        dtype=dtype,
        evaluation_mode=evaluation_mode,
        generation_backend=generation_backend,
    )
    validate_f2_smoke_trace(
        rows,
        expected_failure_code=spec.expected_failure_code,
        fixture_path=path,
        expected_archetype=spec.name,
    )
    _write_jsonl(Path(output_path), rows)
    return rows


def validate_f2_smoke_trace(
    rows: Sequence[dict[str, Any]],
    *,
    expected_failure_code: str | None = None,
    fixture_path: str | Path | None = None,
    expected_archetype: str | None = None,
    expected_condition: str | None = None,
    expected_evaluation_mode: str | None = None,
    expected_generation_backend: str | None = None,
) -> None:
    """Validate the smoke sidecar trace without running generation or eval."""

    if not rows:
        raise ValueError("F2 smoke trace must contain at least one row")
    iterations = [row.get("repair_iteration") for row in rows]
    if iterations != list(range(len(rows))):
        raise ValueError(f"repair_iteration values are not contiguous: {iterations}")
    repair_budget = rows[0].get("repair_budget")
    if (
        not isinstance(repair_budget, int)
        or isinstance(repair_budget, bool)
        or repair_budget < 0
    ):
        raise ValueError("trace rows must record a non-negative integer repair_budget")
    for row in rows:
        if row.get("repair_budget") != repair_budget:
            raise ValueError("trace rows must record a consistent repair_budget")

    first = rows[0]
    expected_fixture_hash = (
        _file_sha256(Path(fixture_path)) if fixture_path is not None else None
    )
    recorded_fixture_hash = first.get("fixture_sha256")
    if not isinstance(recorded_fixture_hash, str) or not recorded_fixture_hash:
        raise ValueError("iteration 0 must record fixture_sha256")
    if expected_fixture_hash is not None and recorded_fixture_hash != expected_fixture_hash:
        raise ValueError("fixture_sha256 is stale relative to fixture_path")
    if (
        expected_fixture_hash is not None
        and first.get("source_sha256") != expected_fixture_hash
    ):
        raise ValueError("iteration 0 source_sha256 must match fixture source hash")
    if expected_archetype is not None and first.get("archetype") != expected_archetype:
        raise ValueError(
            "iteration 0 archetype mismatch: "
            f"expected {expected_archetype}, got {first.get('archetype')}"
        )
    if first.get("candidate_origin") != "seed_fixture":
        raise ValueError("iteration 0 must be the seed fixture candidate")
    if first.get("level_reached") != 2:
        raise ValueError("iteration 0 must reach Level 2")
    if (
        expected_failure_code is not None
        and first.get("failure_code") != expected_failure_code
    ):
        raise ValueError(
            "iteration 0 failure_code mismatch: "
            f"expected {expected_failure_code}, got {first.get('failure_code')}"
        )
    if first.get("failure_code") not in F2_SMOKE_FAILURE_CODES:
        raise ValueError("iteration 0 must fail with an F2 failure code")
    if first.get("functional_success") is not False:
        raise ValueError("iteration 0 must record functional_success=False")
    _validate_smoke_eval_outcome(first, iteration=0)
    for field_name in (
        "feedback_type",
        "feedback_content",
        "feedback_prompt_content",
        "feedback_prompt_sha256",
    ):
        if first.get(field_name) not in (None, ""):
            raise ValueError("iteration 0 must not record repair feedback")
    if len(rows) < 2:
        raise ValueError("F2 smoke trace must contain at least one repair iteration")

    for repair_row in rows[1:]:
        iteration = repair_row.get("repair_iteration")
        expected_origin = _expected_repair_candidate_origin(
            repair_row.get("generation_backend")
        )
        if repair_row.get("candidate_origin") != expected_origin:
            raise ValueError(
                f"repair row {iteration} must record {expected_origin} "
                "candidate_origin"
            )
        _validate_smoke_eval_outcome(repair_row, iteration=iteration)
        if repair_row.get("feedback_type") != CORRECTNESS_FEEDBACK_TYPE:
            raise ValueError(
                f"repair row {iteration} must carry correctness_error feedback"
            )
        feedback = repair_row.get("feedback_content")
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError(f"repair row {iteration} must carry feedback_content")
        _validate_smoke_feedback_content(feedback)
        prompt = repair_row.get("feedback_prompt_content")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                f"repair row {iteration} must carry feedback_prompt_content"
            )
        prompt_hash = repair_row.get("feedback_prompt_sha256")
        if prompt_hash != _sha256(prompt):
            raise ValueError("feedback_prompt_sha256 does not match prompt content")
        if _extract_prompt_section(prompt, "Feedback") != feedback:
            raise ValueError("feedback_content must match the prompt Feedback section")

    converged, exhausted, success_index = _validate_smoke_terminal_status(rows)
    if converged == exhausted:
        raise ValueError("trace must record exactly one of convergence or exhaustion")
    final_iteration = rows[-1].get("repair_iteration")
    if converged:
        if success_index is None:
            raise ValueError("converged trace missing successful_attempt_index")
        if success_index != final_iteration:
            raise ValueError("converged trace must end at successful_attempt_index")
        if final_iteration > repair_budget:
            raise ValueError("converged trace cannot exceed repair_budget")
        success_rows = [
            row for row in rows if row.get("functional_success") is True
        ]
        if len(success_rows) != 1:
            raise ValueError("converged trace must record exactly one successful row")
        if success_rows[0].get("repair_iteration") != success_index:
            raise ValueError("successful_attempt_index does not identify the success row")
    if exhausted and final_iteration != repair_budget:
        raise ValueError("exhausted trace must end at repair_budget")
    if exhausted and any(row.get("functional_success") is True for row in rows):
        raise ValueError("exhausted trace must not contain a successful row")

    for row in rows:
        if row.get("fixture_sha256") != recorded_fixture_hash:
            raise ValueError("trace rows must record a consistent fixture_sha256")
        if expected_archetype is not None and row.get("archetype") != expected_archetype:
            raise ValueError("trace rows must record the expected archetype")
        if expected_condition is not None and row.get("condition") != expected_condition:
            raise ValueError(
                "trace rows must record expected condition "
                f"{expected_condition}"
            )
        if (
            expected_evaluation_mode is not None
            and row.get("evaluation_mode") != expected_evaluation_mode
        ):
            raise ValueError(
                "trace rows must record expected evaluation_mode "
                f"{expected_evaluation_mode}"
            )
        if (
            expected_generation_backend is not None
            and row.get("generation_backend") != expected_generation_backend
        ):
            raise ValueError(
                "trace rows must record expected generation_backend "
                f"{expected_generation_backend}"
            )
        if (
            expected_generation_backend == MODAL_GENERATION_BACKEND
            and not str(row.get("run_id", "")).endswith("-modal")
        ):
            raise ValueError("modal smoke trace rows must record a modal run_id")
        for forbidden_key in (
            "tokens_generated",
            "tokens_input",
            "tokens_output",
            "tim" + "ing",
            "speed" + "up",
            "profile",
            "pro" + "filer",
        ):
            if forbidden_key in row:
                raise ValueError(f"forbidden smoke trace field: {forbidden_key}")
        feedback = row.get("feedback_content")
        if isinstance(feedback, str) and feedback:
            _validate_smoke_feedback_content(feedback)


def load_f2_smoke_trace(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Load a smoke JSONL trace and reject malformed rows early."""

    trace_path = Path(path)
    if not trace_path.exists():
        raise FileNotFoundError(f"missing F2 smoke trace artifact: {trace_path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        trace_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(
                f"F2 smoke trace row {line_number} in {trace_path} is not an object"
            )
        rows.append(row)
    return tuple(rows)


def _expected_repair_candidate_origin(generation_backend: object) -> str:
    if generation_backend == MOCK_GENERATION_BACKEND:
        return "mock_repair"
    if generation_backend == MODAL_GENERATION_BACKEND:
        return "modal_repair"
    raise ValueError(
        "repair rows must record a known generation_backend before "
        "candidate_origin validation"
    )


def _validate_smoke_eval_outcome(row: dict[str, Any], *, iteration: object) -> None:
    functional_success = row.get("functional_success")
    failure_code = row.get("failure_code")
    level_reached = row.get("level_reached")
    repair_set_success = row.get("repair_set_success")
    eval_set_success = row.get("eval_set_success")

    if functional_success is True:
        if failure_code is not None:
            raise ValueError(
                f"row {iteration} successful outcome must not record failure_code"
            )
        if level_reached != 2:
            raise ValueError(
                f"row {iteration} successful outcome must reach Level 2"
            )
        if repair_set_success is not True or eval_set_success is not True:
            raise ValueError(
                f"row {iteration} successful outcome must pass repair and eval sets"
            )
        return

    if functional_success is not False:
        raise ValueError(
            f"row {iteration} must record functional_success as a boolean"
        )
    if level_reached != 2:
        raise ValueError(f"row {iteration} failed outcome must reach Level 2")
    if failure_code not in F2_SMOKE_FAILURE_CODES:
        raise ValueError(
            f"row {iteration} failed outcome must record an F2 failure_code"
        )
    if not isinstance(repair_set_success, bool) or not isinstance(eval_set_success, bool):
        raise ValueError(
            f"row {iteration} failed outcome must record repair/eval set flags"
        )
    if repair_set_success and eval_set_success:
        raise ValueError(
            f"row {iteration} failed outcome contradicts repair/eval set success"
        )


def _validate_smoke_terminal_status(
    rows: Sequence[dict[str, Any]],
) -> tuple[bool, bool, int | None]:
    converged = _require_terminal_bool(rows[0], "repair_converged")
    exhausted = _require_terminal_bool(rows[0], "budget_exhausted")
    success_index = _coerce_successful_attempt_index(
        rows[0].get("successful_attempt_index")
    )
    loop_status = rows[0].get("repair_loop_status")
    if loop_status not in {REPAIR_LOOP_SUCCESS_STATUS, REPAIR_LOOP_EXHAUSTED_STATUS}:
        raise ValueError("repair_loop_status must record success or exhausted")

    for row in rows[1:]:
        if _require_terminal_bool(row, "repair_converged") != converged:
            raise ValueError("trace rows must record consistent terminal status fields")
        if _require_terminal_bool(row, "budget_exhausted") != exhausted:
            raise ValueError("trace rows must record consistent terminal status fields")
        if (
            _coerce_successful_attempt_index(row.get("successful_attempt_index"))
            != success_index
        ):
            raise ValueError("trace rows must record consistent terminal status fields")
        if row.get("repair_loop_status") != loop_status:
            raise ValueError("trace rows must record consistent terminal status fields")

    if loop_status == REPAIR_LOOP_SUCCESS_STATUS:
        if not converged or exhausted:
            raise ValueError("repair_loop_status must match terminal flags")
        if success_index is None:
            raise ValueError("converged trace missing successful_attempt_index")
    if loop_status == REPAIR_LOOP_EXHAUSTED_STATUS:
        if converged or not exhausted:
            raise ValueError("repair_loop_status must match terminal flags")
        if success_index is not None:
            raise ValueError("exhausted trace must not record successful_attempt_index")

    return converged, exhausted, success_index


def _require_terminal_bool(row: dict[str, Any], field_name: str) -> bool:
    value = row.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _coerce_successful_attempt_index(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            "successful_attempt_index must be a non-negative integer or null"
        )
    return value


def validate_canonical_f2_smoke_artifacts(
    repo_root: str | Path | None = None,
) -> None:
    """Validate all canonical smoke artifacts against current fixture hashes."""

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    for spec in ARCHETYPES.values():
        fixture_path = root / "cluster2" / "tests" / "fixtures" / spec.fixture_filename
        trace_path = (
            root
            / "outputs"
            / "cluster2"
            / f"smoke_f2_repair_{spec.name}.jsonl"
        )
        rows = load_f2_smoke_trace(trace_path)
        validate_f2_smoke_trace(
            rows,
            expected_failure_code=spec.expected_failure_code,
            fixture_path=fixture_path,
            expected_archetype=spec.name,
            expected_condition="C",
            expected_evaluation_mode=MODAL_EVALUATION_MODE,
            expected_generation_backend=MODAL_GENERATION_BACKEND,
        )


def _generate_modal_repair_source(
    request: RepairGenerationInput,
    *,
    condition: str,
    spec: F2SmokeArchetype,
    run_id: str,
    dtype: str,
    model_id: str,
    model_revision: str,
    tokenizer_revision: str,
    temperature: float,
    max_new_tokens: int,
    grammar_variant: str | None,
    modal_generation_gpu: str,
    generation_adapter: RemoteGenerationAdapter | None,
) -> str:
    adapter = generation_adapter
    if adapter is None:
        from cluster2.generation.modal_generate_c2 import generate_source_c2_modal

        adapter = generate_source_c2_modal
    payload = adapter(
        identity=_eval_identity(
            run_id=run_id,
            condition=condition,
            spec=spec,
            dtype=dtype,
            base_seed=request.base_seed,
            attempt_index=request.attempt_index,
        ),
        prompt=request.prompt,
        model_id=model_id,
        model_revision=model_revision,
        tokenizer_revision=tokenizer_revision,
        generation_seed=request.generation_seed,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        grammar_variant=grammar_variant if condition == "G+C" else None,
        modal_generation_gpu=modal_generation_gpu,
    )
    return _extract_generated_source(payload)


def _extract_generated_source(payload: dict[str, Any]) -> str:
    error_type = payload.get("error_type")
    if error_type is not None:
        raise RuntimeError(f"remote C2 generation failed: {error_type}")
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("remote C2 generation did not return source")
    return source


def _evaluate_modal_smoke_source(
    source: str,
    *,
    condition: str,
    spec: F2SmokeArchetype,
    run_id: str,
    dtype: str,
    base_seed: int,
    attempt_index: int,
    correctness_adapter: RemoteCorrectnessAdapter | None,
) -> object:
    adapter = correctness_adapter
    if adapter is None:
        from cluster2.validation.modal_correctness_check import check_remote_correctness

        adapter = check_remote_correctness
    request = RemoteCorrectnessRequest(
        identity=_eval_identity(
            run_id=run_id,
            condition=condition,
            spec=spec,
            dtype=dtype,
            base_seed=base_seed,
            attempt_index=attempt_index,
        ),
        source=source,
    )
    payload = adapter(request)
    result = extract_correctness_result(payload)
    if result is None:
        raise RuntimeError("remote C2 correctness returned infrastructure failure")
    return SimpleNamespace(
        level_reached=_level_reached_for_failure_code(result.failure_code),
        parse_success=None,
        parse_error=None,
        safe_success=None,
        sanitizer_errors=(),
        signature_valid=None,
        signature_error=None,
        compile_success=None,
        compile_error=None,
        functional_success=result.functional_success,
        repair_set_success=result.repair_set_success,
        eval_set_success=result.eval_set_success,
        failure_code=result.failure_code,
        correctness_error=result.correctness_error,
        public_failure_summary=result.correctness_error,
        feedback=result.feedback,
        max_abs_diff=result.max_abs_diff,
        max_rel_diff=result.max_rel_diff,
        num_test_shapes=result.num_test_shapes,
        shapes_passed=result.shapes_passed,
        repair_shapes_passed=result.repair_shapes_passed,
        eval_shapes_passed=result.eval_shapes_passed,
        dtype_results=None,
        repair_shape_results=None,
    )


def _evaluate_mock_smoke_source(
    source: str,
    *,
    spec: F2SmokeArchetype,
    dtype: str,
    base_seed: int,
    attempt_index: int,
    fixture_source: str,
    corrected_source: str,
) -> object:
    static_failure = _static_gate_failure(source, spec)
    if static_failure is not None:
        return static_failure

    level2_result = evaluate_level2_correctness(
        spec.kernel_class,
        dtype,
        _mock_candidate_runner_for_source(
            source,
            spec.name,
            fixture_source=fixture_source,
            corrected_source=corrected_source,
        ),
        base_seed=base_seed,
        attempt_index=attempt_index,
        shape_sets=_smoke_shape_sets(spec, dtype=dtype, base_seed=base_seed),
        device="cpu",
    )
    return SimpleNamespace(
        level_reached=2,
        parse_success=True,
        parse_error=None,
        safe_success=True,
        sanitizer_errors=None,
        signature_valid=True,
        signature_error=None,
        compile_success=True,
        compile_error=None,
        functional_success=level2_result.functional_success,
        repair_set_success=level2_result.repair_set_success,
        eval_set_success=level2_result.eval_set_success,
        failure_code=level2_result.failure_code,
        correctness_error=level2_result.correctness_error,
        public_failure_summary=level2_result.correctness_error,
        feedback=level2_result.feedback,
        max_abs_diff=level2_result.max_abs_diff,
        max_rel_diff=level2_result.max_rel_diff,
        num_test_shapes=level2_result.num_test_shapes,
        shapes_passed=level2_result.shapes_passed,
        repair_shapes_passed=level2_result.repair_shapes_passed,
        eval_shapes_passed=level2_result.eval_shapes_passed,
        dtype_results=level2_result.to_eval_fields()["dtype_results"],
        repair_shape_results=[
            shape_result.to_dict()
            for shape_result in level2_result.repair_shape_results
        ],
    )


def _static_gate_failure(source: str, spec: F2SmokeArchetype) -> object | None:
    parse_success, parse_error = check_parse(source)
    if not parse_success:
        return SimpleNamespace(
            level_reached=0,
            parse_success=False,
            parse_error=parse_error,
            signature_valid=None,
            signature_error=None,
            compile_success=None,
            compile_error=None,
            functional_success=False,
            repair_set_success=False,
            eval_set_success=False,
            failure_code="F0_PARSE",
            correctness_error=parse_error,
            public_failure_summary=parse_error,
            sanitizer_errors=(),
        )

    sanitizer_result = check_level0_ast_sanitizer(source)
    if not sanitizer_result.safe_success:
        summary = "; ".join(sanitizer_result.sanitizer_errors or ())
        return SimpleNamespace(
            level_reached=0,
            parse_success=True,
            parse_error=None,
            signature_valid=None,
            signature_error=None,
            compile_success=None,
            compile_error=None,
            functional_success=False,
            repair_set_success=False,
            eval_set_success=False,
            failure_code=sanitizer_result.failure_code,
            correctness_error=summary,
            public_failure_summary=summary,
            sanitizer_errors=tuple(sanitizer_result.sanitizer_errors or ()),
        )

    signature_valid, signature_error = check_signature(
        source,
        _kernel_spec_for_archetype(spec),
    )
    if not signature_valid:
        return SimpleNamespace(
            level_reached=0,
            parse_success=True,
            parse_error=None,
            signature_valid=False,
            signature_error=signature_error,
            compile_success=None,
            compile_error=None,
            functional_success=False,
            repair_set_success=False,
            eval_set_success=False,
            failure_code="F0_BAD_SIGNATURE",
            correctness_error=signature_error,
            public_failure_summary=signature_error,
            sanitizer_errors=(),
        )
    return None


def _mock_candidate_runner_for_source(
    source: str,
    archetype: str,
    *,
    fixture_source: str,
    corrected_source: str,
):
    corrected = source == corrected_source
    del fixture_source

    def run(request: Level2CandidateRequest) -> Any:
        if corrected:
            return _matching_candidate(request)
        return _corrupted_candidate(request, archetype)

    return run


def _matching_candidate(request: Level2CandidateRequest) -> Any:
    torch = _torch()
    if request.kernel_name == "relu":
        return torch.relu(request.inputs[0])
    if request.kernel_name == "softmax":
        return torch.softmax(request.inputs[0], dim=1)
    if request.kernel_name == "gemm":
        return torch.matmul(request.inputs[0], request.inputs[1])
    raise AssertionError(f"unexpected kernel {request.kernel_name!r}")


def _corrupted_candidate(request: Level2CandidateRequest, archetype: str) -> Any:
    torch = _torch()
    if archetype == "relu":
        return _relu_with_wrong_negative_branch(request.inputs[0])
    if archetype == "softmax":
        return torch.softmax(request.inputs[0], dim=0)
    if archetype == "matmul":
        return _matching_candidate(request) + 1.0
    raise AssertionError(f"unexpected archetype {archetype!r}")


def _relu_with_wrong_negative_branch(tensor: Any) -> Any:
    if hasattr(tensor, "data") and hasattr(tensor, "shape"):
        return type(tensor)(
            tuple(float(value) if float(value) > 0.0 else 1.0 for value in tensor.data),
            tuple(tensor.shape),
            getattr(tensor, "dtype", DEFAULT_DTYPE),
        )
    torch = _torch()
    return torch.where(tensor > 0.0, tensor, torch.ones_like(tensor))


def _corrected_source(source: str, archetype: str) -> str:
    if archetype == "relu":
        return _replace_required(
            source,
            "tl.where(x > 0.0, x, 1.0)",
            "tl.where(x > 0.0, x, 0.0)",
        )
    if archetype == "softmax":
        return _replace_required(source, "out = shifted / denom", "out = numer / denom")
    if archetype == "matmul":
        return _replace_required(
            source,
            "tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc + 1.0, mask=mask)",
            "tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc, mask=mask)",
        )
    raise AssertionError(f"unexpected archetype {archetype!r}")


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise ValueError(f"fixture source missing expected corruption marker: {old}")
    return source.replace(old, new, 1)


def _smoke_shape_sets(
    spec: F2SmokeArchetype,
    *,
    dtype: str,
    base_seed: int,
) -> CorrectnessShapeSets:
    if spec.name == "relu":
        repair_shapes = ((4,),)
        eval_shapes = ((5,),)
    elif spec.name == "softmax":
        repair_shapes = ((2, 4),)
        eval_shapes = ((3, 5),)
    elif spec.name == "matmul":
        repair_shapes = ((2, 3, 4),)
        eval_shapes = ((3, 2, 5),)
    else:
        raise AssertionError(f"unexpected archetype {spec.name!r}")
    return CorrectnessShapeSets(
        kernel_class=spec.kernel_class,
        kernel_name=spec.kernel_name,
        dtype=dtype,
        base_seed=base_seed,
        repair_shape_set=repair_shapes,
        eval_shape_set=eval_shapes,
    )


def _build_trace_rows(
    *,
    repair_result: Any,
    result_by_attempt: dict[int, object],
    source_by_attempt: dict[int, str],
    generation_inputs: dict[int, RepairGenerationInput],
    run_id: str,
    condition: str,
    spec: F2SmokeArchetype,
    fixture_path: Path,
    fixture_hash: str,
    repair_budget: int,
    base_seed: int,
    dtype: str,
    evaluation_mode: str,
    generation_backend: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    repair_converged = repair_result.status == REPAIR_LOOP_SUCCESS_STATUS
    budget_exhausted = repair_result.status == REPAIR_LOOP_EXHAUSTED_STATUS
    for attempt in repair_result.attempts:
        iteration = attempt.attempt_index
        result = result_by_attempt[iteration]
        source = source_by_attempt[iteration]
        feedback_content = None
        feedback_type = None
        feedback_prompt_sha256 = None
        feedback_prompt_content = None
        if iteration > 0:
            feedback_prompt_content = generation_inputs[iteration].prompt
            feedback_content = _extract_prompt_section(
                feedback_prompt_content,
                "Feedback",
            )
            _validate_smoke_feedback_content(feedback_content)
            feedback_type = CORRECTNESS_FEEDBACK_TYPE
            feedback_prompt_sha256 = _sha256(feedback_prompt_content)
        rows.append(
            {
                "run_id": run_id,
                "condition": condition,
                "archetype": spec.name,
                "kernel_class": spec.kernel_class,
                "kernel_name": spec.kernel_name,
                "dtype": dtype,
                "base_seed": base_seed,
                "evaluation_mode": evaluation_mode,
                "generation_backend": generation_backend,
                "fixture_path": fixture_path.as_posix(),
                "fixture_sha256": fixture_hash,
                "repair_budget": repair_budget,
                "repair_iteration": iteration,
                "candidate_origin": (
                    "seed_fixture"
                    if iteration == 0
                    else (
                        "mock_repair"
                        if generation_backend == MOCK_GENERATION_BACKEND
                        else "modal_repair"
                    )
                ),
                "source_sha256": _sha256(source),
                "level_reached": getattr(result, "level_reached", None),
                "failure_code": getattr(result, "failure_code", None),
                "feedback_type": feedback_type,
                "feedback_content": feedback_content,
                "feedback_prompt_sha256": feedback_prompt_sha256,
                "feedback_prompt_content": feedback_prompt_content,
                "functional_success": getattr(result, "functional_success", None),
                "repair_set_success": getattr(result, "repair_set_success", None),
                "eval_set_success": getattr(result, "eval_set_success", None),
                "repair_converged": repair_converged,
                "successful_attempt_index": repair_result.successful_attempt_index,
                "budget_exhausted": budget_exhausted,
                "repair_loop_status": repair_result.status,
                "eval_summary": _eval_summary(result),
            }
        )
    return tuple(rows)


def _eval_summary(result: object) -> dict[str, Any]:
    return _json_safe(
        {
            "correctness_error": getattr(result, "correctness_error", None),
            "max_abs_diff": getattr(result, "max_abs_diff", None),
            "max_rel_diff": getattr(result, "max_rel_diff", None),
            "num_test_shapes": getattr(result, "num_test_shapes", None),
            "shapes_passed": getattr(result, "shapes_passed", None),
            "repair_shapes_passed": getattr(result, "repair_shapes_passed", None),
            "eval_shapes_passed": getattr(result, "eval_shapes_passed", None),
            "repair_shape_results": getattr(result, "repair_shape_results", None),
        }
    )


def _validate_smoke_feedback_content(value: str) -> None:
    validate_no_forbidden_feedback_terms(value)
    lowered = value.lower()
    for marker in FORBIDDEN_SMOKE_FEEDBACK_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"feedback_content contains forbidden marker: {marker}")
    numeric_value = r"(?:[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|nan|inf)"
    has_diff_metrics = bool(
        re.search(rf"\bmax_abs_diff\s*=\s*{numeric_value}\b", value, re.IGNORECASE)
        and re.search(
            rf"\bmax_rel_diff\s*=\s*{numeric_value}\b",
            value,
            re.IGNORECASE,
        )
    )
    has_shape_detail = bool(
        re.search(r"\b(?:shape\s+mismatch|wrong\s+shape)\b", value, re.IGNORECASE)
        and re.search(r"(?:\([0-9,\s]+\)|\[[0-9,\s]+\])", value)
    )
    has_nan_inf_detail = bool(
        re.search(r"(?<![A-Za-z0-9_])(?:nan|inf)(?![A-Za-z0-9_])", value, re.IGNORECASE)
    )
    if not (has_diff_metrics or has_shape_detail or has_nan_inf_detail):
        raise ValueError("feedback_content must include numerical correctness details")


def _extract_prompt_section(prompt: str, section_name: str) -> str:
    if section_name not in FEEDBACK_PROMPT_SECTION_NAMES:
        raise ValueError(f"unsupported prompt section {section_name!r}")
    header = f"{section_name}:\n"
    start = prompt.find(header)
    if start < 0:
        raise ValueError(f"feedback prompt missing {section_name!r} section")
    value_start = start + len(header)
    next_starts = [
        prompt.find(f"\n\n{name}:\n", value_start)
        for name in FEEDBACK_PROMPT_SECTION_NAMES
        if name != section_name
    ]
    next_starts = [index for index in next_starts if index >= 0]
    value_end = min(next_starts) if next_starts else len(prompt)
    value = prompt[value_start:value_end].strip()
    if not value:
        raise ValueError(f"feedback prompt {section_name!r} section is empty")
    return value


def _resolve_archetype(archetype: str) -> F2SmokeArchetype:
    key = ARCHETYPE_ALIASES.get(archetype, archetype)
    try:
        return ARCHETYPES[key]
    except KeyError as exc:
        allowed = ", ".join(sorted((*ARCHETYPES, *ARCHETYPE_ALIASES)))
        raise ValueError(f"unsupported archetype {archetype!r}; allowed: {allowed}") from exc


def _kernel_spec_for_archetype(spec: F2SmokeArchetype) -> object:
    from cluster1.data.kernels import get_kernel_spec

    return get_kernel_spec(spec.kernel_class)


def _eval_identity(
    *,
    run_id: str,
    condition: str,
    spec: F2SmokeArchetype,
    dtype: str,
    base_seed: int,
    attempt_index: int,
) -> EvalIdentity:
    return EvalIdentity(
        run_id=run_id,
        condition=condition,
        source_class=source_class_for_condition(condition),
        generation_mode=generation_mode_for_condition(condition),
        kernel_class=spec.kernel_class,
        kernel_name=spec.kernel_name,
        dtype=dtype,
        sample_index=0,
        base_seed=base_seed,
        attempt_index=attempt_index,
    )


def _level_reached_for_failure_code(failure_code: str | None) -> int:
    if failure_code is None or failure_code.startswith("F2_"):
        return 2
    if failure_code.startswith("F1_"):
        return 1
    if failure_code.startswith("F0_"):
        return 0
    return 2


def _require_real_generation_metadata(
    *,
    model_revision: str | None,
    tokenizer_revision: str | None,
) -> None:
    if not isinstance(model_revision, str) or not model_revision.strip():
        raise ValueError("model_revision is required for non-mock F2 smoke")
    if not isinstance(tokenizer_revision, str) or not tokenizer_revision.strip():
        raise ValueError("tokenizer_revision is required for non-mock F2 smoke")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows
    )
    path.write_text(f"{payload}\n", encoding="utf-8")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _torch() -> Any:
    import torch

    return torch


def _ensure_mock_level2_runtime_available() -> None:
    try:
        import torch  # noqa: F401
    except ModuleNotFoundError:
        _install_fake_torch()


class _FakeTensor:
    def __init__(
        self,
        data: Sequence[float | bool],
        shape: Sequence[int],
        dtype: str = DEFAULT_DTYPE,
    ) -> None:
        self.data = tuple(data)
        self.shape = tuple(shape)
        self.dtype = dtype
        self.device = "cpu"
        self.is_sparse = False

    def __add__(self, other: float | "_FakeTensor") -> "_FakeTensor":
        return self._binary(other, lambda left, right: left + right)

    def __sub__(self, other: float | "_FakeTensor") -> "_FakeTensor":
        return self._binary(other, lambda left, right: left - right)

    def __truediv__(self, other: float | "_FakeTensor") -> "_FakeTensor":
        return self._binary(other, lambda left, right: left / right)

    def _binary(self, other: float | "_FakeTensor", op) -> "_FakeTensor":  # type: ignore[no-untyped-def]
        if isinstance(other, _FakeTensor):
            if self.shape != other.shape:
                raise ValueError("fake tensor shape mismatch")
            return _FakeTensor(
                tuple(
                    op(float(left), float(right))
                    for left, right in zip(self.data, other.data, strict=True)
                ),
                self.shape,
                self.dtype,
            )
        return _FakeTensor(
            tuple(op(float(value), other) for value in self.data),
            self.shape,
            self.dtype,
        )

    def relu(self) -> "_FakeTensor":
        return _FakeTensor(
            tuple(max(0.0, float(value)) for value in self.data),
            self.shape,
            self.dtype,
        )

    def matmul(self, other: "_FakeTensor") -> "_FakeTensor":
        rows, inner = self.shape
        other_inner, cols = other.shape
        if inner != other_inner:
            raise ValueError("fake matmul shape mismatch")
        output: list[float] = []
        for row in range(rows):
            for col in range(cols):
                total = 0.0
                for idx in range(inner):
                    total += float(self.data[row * inner + idx]) * float(
                        other.data[idx * cols + col]
                    )
                output.append(total)
        return _FakeTensor(tuple(output), (rows, cols), self.dtype)

    def detach(self) -> "_FakeTensor":
        return self

    def cpu(self) -> "_FakeTensor":
        return self

    def to(self, *, dtype: str) -> "_FakeTensor":
        return _FakeTensor(tuple(self.data), self.shape, dtype)

    def to_dense(self) -> "_FakeTensor":
        return self

    def numel(self) -> int:
        return len(self.data)

    def max(self) -> "_FakeTensor":
        return _FakeTensor((max(self.data),), ())

    def any(self) -> "_FakeTensor":
        return _FakeTensor((any(bool(value) for value in self.data),), ())

    def item(self) -> float | bool:
        if len(self.data) != 1:
            raise ValueError("fake tensor item requires one value")
        return self.data[0]


class _FakeGenerator:
    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self._rng = random.Random(0)

    def manual_seed(self, seed: int) -> "_FakeGenerator":
        self._rng.seed(seed)
        return self


class _FakeNoGrad:
    def __init__(self, torch_module: types.ModuleType) -> None:
        self._torch_module = torch_module
        self._previous = True

    def __enter__(self) -> None:
        self._previous = self._torch_module._grad_enabled
        self._torch_module._grad_enabled = False

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self._torch_module._grad_enabled = self._previous


class _FakeModule:
    def __init__(self) -> None:
        pass

    def eval(self) -> "_FakeModule":
        return self


def _install_fake_torch() -> None:
    torch_module = types.ModuleType("torch")
    nn_module = types.ModuleType("torch.nn")
    nn_module.Module = _FakeModule
    torch_module.Tensor = _FakeTensor
    torch_module.float32 = "fp32"
    torch_module.float16 = "fp16"
    torch_module.bfloat16 = "bf16"
    torch_module.float64 = "fp64"
    torch_module.nn = nn_module
    torch_module._grad_enabled = True
    torch_module._deterministic_algorithms = None
    torch_module._deterministic_warn_only = None
    torch_module.backends = types.SimpleNamespace(
        cuda=types.SimpleNamespace(
            matmul=types.SimpleNamespace(allow_tf32=True),
        ),
        cudnn=types.SimpleNamespace(
            allow_tf32=True,
            deterministic=False,
            benchmark=True,
        ),
    )

    def randn(
        shape: Sequence[int],
        *,
        dtype: str,
        device: str,
        generator: _FakeGenerator,
    ) -> _FakeTensor:
        del device
        normalized_shape = tuple(shape)
        return _FakeTensor(
            tuple(
                generator._rng.uniform(-1.0, 1.0)
                for _ in range(math.prod(normalized_shape))
            ),
            normalized_shape,
            dtype,
        )

    def rand(
        *shape: int,
        dtype: str = DEFAULT_DTYPE,
        device: str = "cpu",
    ) -> _FakeTensor:
        del device
        rng = random.Random(0)
        return _FakeTensor(
            tuple(rng.random() for _ in range(math.prod(shape))),
            shape,
            dtype,
        )

    def empty(shape: Sequence[int], *, device: str, dtype: str) -> _FakeTensor:
        del device
        normalized_shape = tuple(shape)
        return _FakeTensor(
            tuple(0.0 for _ in range(math.prod(normalized_shape))),
            normalized_shape,
            dtype,
        )

    def empty_like(tensor: _FakeTensor) -> _FakeTensor:
        return _FakeTensor(tuple(0.0 for _ in tensor.data), tensor.shape, tensor.dtype)

    def zeros(shape: Sequence[int], *, dtype: str) -> _FakeTensor:
        normalized_shape = tuple(shape)
        return _FakeTensor(
            tuple(0.0 for _ in range(math.prod(normalized_shape))),
            normalized_shape,
            dtype,
        )

    def ones_like(tensor: _FakeTensor) -> _FakeTensor:
        return _FakeTensor(tuple(1.0 for _ in tensor.data), tensor.shape, tensor.dtype)

    def as_tensor(value: Any) -> _FakeTensor:
        if isinstance(value, _FakeTensor):
            return value
        if isinstance(value, (int, float, bool)):
            return _FakeTensor((value,), ())
        return _FakeTensor(tuple(value), (len(value),))

    def abs_tensor(tensor: _FakeTensor) -> _FakeTensor:
        return _FakeTensor(
            tuple(abs(float(value)) for value in tensor.data),
            tensor.shape,
            tensor.dtype,
        )

    def clamp(tensor: _FakeTensor, *, min: float) -> _FakeTensor:
        return _FakeTensor(
            tuple(max(float(value), min) for value in tensor.data),
            tensor.shape,
            tensor.dtype,
        )

    def isnan(tensor: _FakeTensor) -> _FakeTensor:
        return _FakeTensor(
            tuple(math.isnan(float(value)) for value in tensor.data),
            tensor.shape,
        )

    def isinf(tensor: _FakeTensor) -> _FakeTensor:
        return _FakeTensor(
            tuple(math.isinf(float(value)) for value in tensor.data),
            tensor.shape,
        )

    def allclose(
        left: _FakeTensor,
        right: _FakeTensor,
        *,
        atol: float,
        rtol: float,
    ) -> bool:
        if left.shape != right.shape:
            return False
        return all(
            abs(float(left_value) - float(right_value))
            <= atol + rtol * abs(float(right_value))
            for left_value, right_value in zip(left.data, right.data, strict=True)
        )

    def softmax(tensor: _FakeTensor, *, dim: int) -> _FakeTensor:
        if len(tensor.shape) != 2:
            raise ValueError("fake softmax supports 2D tensors only")
        rows, cols = tensor.shape
        dim = 1 if dim == -1 else dim
        output = [0.0 for _ in tensor.data]
        if dim == 1:
            for row in range(rows):
                start = row * cols
                values = [float(value) for value in tensor.data[start : start + cols]]
                max_value = max(values)
                exps = [math.exp(value - max_value) for value in values]
                denom = sum(exps)
                output[start : start + cols] = [value / denom for value in exps]
        elif dim == 0:
            for col in range(cols):
                values = [
                    float(tensor.data[row * cols + col]) for row in range(rows)
                ]
                max_value = max(values)
                exps = [math.exp(value - max_value) for value in values]
                denom = sum(exps)
                for row, value in enumerate(exps):
                    output[row * cols + col] = value / denom
        else:
            raise ValueError("fake softmax supports dim 0 or 1")
        return _FakeTensor(tuple(output), tensor.shape, tensor.dtype)

    def use_deterministic_algorithms(
        enabled: bool,
        *,
        warn_only: bool = False,
    ) -> None:
        torch_module._deterministic_algorithms = enabled
        torch_module._deterministic_warn_only = warn_only

    torch_module.Generator = _FakeGenerator
    torch_module.randn = randn
    torch_module.rand = rand
    torch_module.empty = empty
    torch_module.empty_like = empty_like
    torch_module.zeros = zeros
    torch_module.ones_like = ones_like
    torch_module.as_tensor = as_tensor
    torch_module.relu = lambda tensor: tensor.relu()
    torch_module.softmax = softmax
    torch_module.matmul = lambda left, right: left.matmul(right)
    torch_module.no_grad = lambda: _FakeNoGrad(torch_module)
    torch_module.abs = abs_tensor
    torch_module.clamp = clamp
    torch_module.isnan = isnan
    torch_module.isinf = isinf
    torch_module.allclose = allclose
    torch_module.use_deterministic_algorithms = use_deterministic_algorithms
    sys.modules["torch"] = torch_module
    sys.modules["torch.nn"] = nn_module


def _canonical_fixture_path(spec: F2SmokeArchetype) -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / spec.fixture_filename
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--archetype", choices=sorted((*ARCHETYPES, *ARCHETYPE_ALIASES)))
    parser.add_argument("--condition", default="C")
    parser.add_argument("--repair-budget", type=int, default=DEFAULT_REPAIR_BUDGET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/cluster2"))
    parser.add_argument("--mock-repair", action="store_true")
    parser.add_argument(
        "--mock-repair-mode",
        choices=(MOCK_REPAIR_CORRECT, MOCK_REPAIR_UNCHANGED),
        default=MOCK_REPAIR_CORRECT,
    )
    parser.add_argument("--model-id", default=MODEL_ID_DEFAULT)
    parser.add_argument("--model-revision")
    parser.add_argument("--tokenizer-revision")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS_DEFAULT)
    parser.add_argument("--grammar-variant")
    parser.add_argument("--modal-generation-gpu", default=DEFAULT_C2_MODAL_GENERATION_GPU)
    parser.add_argument("--modal-eval-gpu", default=DEFAULT_C2_MODAL_EVAL_GPU)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.all:
        output_suffix = "_mock" if args.mock_repair else ""
        for spec in ARCHETYPES.values():
            run_f2_repair_smoke(
                fixture_path=_canonical_fixture_path(spec),
                archetype=spec.name,
                output_path=args.output_dir
                / f"smoke_f2_repair_{spec.name}{output_suffix}.jsonl",
                condition=args.condition,
                repair_budget=args.repair_budget,
                mock_repair=args.mock_repair,
                mock_repair_mode=args.mock_repair_mode,
                model_id=args.model_id,
                model_revision=args.model_revision,
                tokenizer_revision=args.tokenizer_revision,
                temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
                grammar_variant=args.grammar_variant,
                modal_generation_gpu=args.modal_generation_gpu,
                modal_eval_gpu=args.modal_eval_gpu,
            )
        return 0

    if args.fixture is None or args.archetype is None or args.output is None:
        raise SystemExit("--fixture, --archetype, and --output are required without --all")
    run_f2_repair_smoke(
        fixture_path=args.fixture,
        archetype=args.archetype,
        output_path=args.output,
        condition=args.condition,
        repair_budget=args.repair_budget,
        mock_repair=args.mock_repair,
        mock_repair_mode=args.mock_repair_mode,
        model_id=args.model_id,
        model_revision=args.model_revision,
        tokenizer_revision=args.tokenizer_revision,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        grammar_variant=args.grammar_variant,
        modal_generation_gpu=args.modal_generation_gpu,
        modal_eval_gpu=args.modal_eval_gpu,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
