from __future__ import annotations

import hashlib
import importlib
import re
from pathlib import Path

import pytest

from cluster3.feedback.dispatcher import dispatch
from cluster3.feedback.prompts import (
    build_compile_diagnostic_note,
    build_p_feedback_prompt,
    excerpt_compile_error,
)
from cluster3.feedback.sanitizer import (
    sanitize_p_feedback_text,
    validate_no_forbidden_p_terms,
)
from shared.eval.failure_taxonomy import FAILURE_CODES


CONDITIONS = ("P", "G+P", "C+P", "G+C+P")
C_ACTIVE_CONDITIONS = {"C+P", "G+C+P"}
F0_CODES = tuple(sorted(code for code in FAILURE_CODES if code.startswith("F0_")))
F2_CODES = tuple(sorted(code for code in FAILURE_CODES if code.startswith("F2_")))
F3_CODES = tuple(sorted(code for code in FAILURE_CODES if code.startswith("F3_")))
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "f1_compile_kernels"
BASE_PROMPT = "Implement the scale kernel as a complete Triton Python module."
COMPILE_ERROR = (
    "CompilationError: LLVM lowering failed because constexpr symbol "
    "MISSING_SCALE_FACTOR is undefined."
)
PATCH_SUGGESTION_RE = re.compile(
    r"\b(?:use|try|replace)\s+|should\s+be|add\s+a|change\s+|fix\s+by",
    re.IGNORECASE,
)


def _fixture_source(name: str = "bad_constexpr.py") -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _compile_feedback_prompt(
    *,
    compile_error: str = COMPILE_ERROR,
    compile_error_type: str = "CompilationError",
) -> str:
    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        _fixture_source(),
        "F1_COMPILE",
        compile_error,
        compile_error_type,
    )
    assert prompt is not None
    return prompt


def test_p_does_not_fire_on_f0_codes() -> None:
    for failure_code in F0_CODES:
        for condition in CONDITIONS:
            decision = dispatch(condition, failure_code, 0)

            assert decision.route == "terminate"
            assert decision.reason == "f0_terminal"
            assert decision.route != "p_loop"


def test_p_does_not_fire_on_f1_runtime() -> None:
    for condition in CONDITIONS:
        decision = dispatch(condition, "F1_RUNTIME", 1)

        assert decision.route == "terminate"
        assert decision.reason == "unrecoverable_runtime"
        assert decision.route != "p_loop"


def test_p_does_not_fire_on_f2_codes() -> None:
    for failure_code in F2_CODES:
        for condition in CONDITIONS:
            decision = dispatch(condition, failure_code, 2)

            assert decision.route != "p_loop"
            if condition in C_ACTIVE_CONDITIONS:
                assert decision.route == "c_loop"
                assert decision.reason == "c_eligible_initial_f2"
                assert decision.c_loop_source == "initial_f2"
            else:
                assert decision.route == "terminate"
                assert decision.reason == "f2_terminal_no_c"


def test_p_does_not_fire_on_f3_codes() -> None:
    for failure_code in F3_CODES:
        for condition in CONDITIONS:
            decision = dispatch(condition, failure_code, 3)

            assert decision.route == "terminate"
            assert decision.reason == "f3_terminal"
            assert decision.route != "p_loop"
            assert decision.route != "c_loop"


def test_p_feedback_excludes_numerical_mismatch_language() -> None:
    lowered = _compile_feedback_prompt().lower()

    forbidden_terms = (
        "numeric",
        "numerical",
        "correctness",
        "mismatch",
        "allclose",
        "nan",
        "inf",
        "shape",
        "shape mismatch",
    )
    assert all(term not in lowered for term in forbidden_terms)


@pytest.mark.parametrize(
    "term",
    (
        "speedup",
        "performance",
        "profiling",
        "profiler",
        "nsight",
        "ncu",
        "timing",
        "benchmark",
        "tokens/sec",
        "latency",
    ),
)
def test_p_feedback_excludes_speedup_profiler_language(term: str) -> None:
    text = f"compile stderr included {term} detail"
    try:
        validate_no_forbidden_p_terms(text)
    except ValueError:
        return

    sanitized = sanitize_p_feedback_text(text)
    assert term.lower() not in sanitized.lower()


def test_p_feedback_does_not_expose_eval_set_details() -> None:
    lowered = _compile_feedback_prompt().lower()

    forbidden_terms = (
        "eval_shape_set",
        "hidden",
        "private",
        "private eval",
        "edge cases",
        "extra shapes",
        "repair set",
        "eval set",
    )
    assert all(term not in lowered for term in forbidden_terms)


def test_p_feedback_does_not_propose_patches() -> None:
    note = build_compile_diagnostic_note(
        "F1_COMPILE",
        "CompilationError",
        COMPILE_ERROR,
    )

    # Early-warning boundary guard only: this narrow regex catches obvious
    # patch-suggestion phrasing but is not a proof that prose is prescriptive.
    assert PATCH_SUGGESTION_RE.search(note) is None


def test_p_feedback_allows_llvm_and_ptx_in_error_excerpt() -> None:
    prompt = _compile_feedback_prompt(
        compile_error="LLVM ERROR: verifier stopped. PTX assembler failed at line 42.",
        compile_error_type="LLVMError",
    )

    assert "LLVM ERROR" in prompt
    assert "PTX assembler failed" in prompt


def test_boundary_uses_cluster3_sanitizer_not_cluster2(monkeypatch) -> None:
    cluster2_prompts = importlib.import_module("cluster2.feedback" + ".prompts")

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Cluster 2 feedback validator must not be called")

    monkeypatch.setattr(
        cluster2_prompts,
        "validate_no_forbidden" + "_feedback_terms",
        fail_if_called,
    )

    assert _compile_feedback_prompt()


def test_p_feedback_does_not_include_full_private_payload_repr() -> None:
    private_payload = (
        "private eval payload {'eval_shape_set': [(1, 2)], 'hidden': True, "
        "'edge cases': ['large']}; LLVM ERROR remains public."
    )

    prompt = _compile_feedback_prompt(compile_error=private_payload)
    lowered = prompt.lower()

    assert private_payload not in prompt
    assert "eval_shape_set" not in lowered
    assert "hidden" not in lowered
    assert "private" not in lowered
    assert "LLVM ERROR" in prompt


def test_compile_error_excerpt_hash_still_uses_full_error() -> None:
    full_error = "LLVM ERROR: " + ("compile detail " * 300) + "tail detail"
    expected_digest = hashlib.sha256(full_error.encode("utf-8")).hexdigest()

    excerpt, digest = excerpt_compile_error(full_error, limit=80)

    assert digest == expected_digest
    assert "tail detail" not in excerpt
    assert digest != hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def test_dispatcher_rejects_unknown_failure_code_in_boundary_suite() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        dispatch("P", "F4_UNKNOWN", 0)


@pytest.mark.parametrize(
    ("failure_code", "level_reached"),
    (
        ("F0_PARSE", 1),
        ("F1_COMPILE", 0),
        ("F1_RUNTIME", 2),
        ("F2_NUMERIC_LARGE", 1),
    ),
)
def test_dispatcher_rejects_level_mismatch_in_boundary_suite(
    failure_code: str,
    level_reached: int,
) -> None:
    with pytest.raises(ValueError, match="level_reached"):
        dispatch("G+C+P", failure_code, level_reached)
