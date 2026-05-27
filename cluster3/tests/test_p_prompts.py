import hashlib

import pytest

from cluster3.feedback.prompts import (
    P_SECTION_ORDER,
    build_compile_diagnostic_note,
    build_p_feedback_prompt,
    excerpt_compile_error,
)


BASE_PROMPT = "Implement the relu kernel as a complete Triton Python module."
SOURCE = "def relu_kernel(x):\n    return x\n"


def test_excerpt_compile_error_truncates_tail_keeps_head() -> None:
    error = "x" * 3000

    excerpt, digest = excerpt_compile_error(error)

    assert excerpt == error[:2000]
    assert digest == hashlib.sha256(error.encode("utf-8")).hexdigest()


def test_excerpt_compile_error_handles_none() -> None:
    assert excerpt_compile_error(None) == ("", "")


def test_build_p_feedback_prompt_returns_none_for_non_f1_compile() -> None:
    for failure_code in (
        "F0_PARSE",
        "F1_RUNTIME",
        "F2_NUMERIC_LARGE",
        "F3_TIMEOUT",
    ):
        assert (
            build_p_feedback_prompt(
                BASE_PROMPT,
                SOURCE,
                failure_code,
                "compiler failed",
                "CompilationError",
            )
            is None
        )


def test_build_p_feedback_prompt_includes_six_sections_in_order() -> None:
    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        SOURCE,
        "F1_COMPILE",
        "compiler failed",
        "CompilationError",
    )

    assert prompt is not None
    positions = [prompt.index(f"{section}:") for section in P_SECTION_ORDER]
    assert positions == sorted(positions)


def test_build_p_feedback_prompt_includes_base_prompt_verbatim() -> None:
    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        SOURCE,
        "F1_COMPILE",
        "compiler failed",
        "CompilationError",
    )

    assert prompt is not None
    assert BASE_PROMPT in prompt


def test_build_p_feedback_prompt_rejects_forbidden_terms_in_feedback() -> None:
    with pytest.raises(ValueError, match="speedup"):
        build_p_feedback_prompt(
            BASE_PROMPT,
            SOURCE,
            "F1_COMPILE",
            "compiler mentioned speedup 2.3x",
            "CompilationError",
        )


def test_build_p_feedback_prompt_allows_llvm_and_ptx() -> None:
    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        SOURCE,
        "F1_COMPILE",
        "LLVM ERROR followed by PTX assembler failed",
        "LLVMError",
    )

    assert prompt is not None
    assert "LLVM ERROR" in prompt
    assert "PTX assembler failed" in prompt


def test_build_p_feedback_prompt_uses_cluster3_sanitizer_only(monkeypatch) -> None:
    import cluster2.feedback.prompts as c2_prompts

    def raising_validator(value: str) -> None:
        raise AssertionError(f"Cluster 2 sanitizer called with {value!r}")

    monkeypatch.setattr(
        c2_prompts,
        "validate_no_forbidden_feedback_terms",
        raising_validator,
    )

    assert build_p_feedback_prompt(
        BASE_PROMPT,
        SOURCE,
        "F1_COMPILE",
        "PTX assembler failed",
        "PTXAssemblyError",
    )


def test_build_compile_diagnostic_note_is_deterministic() -> None:
    first = build_compile_diagnostic_note(
        "F1_COMPILE",
        "CompilationError",
        "compiler failed",
    )
    second = build_compile_diagnostic_note(
        "F1_COMPILE",
        "CompilationError",
        "compiler failed",
    )

    assert first == second


def test_build_compile_diagnostic_note_does_not_propose_patches() -> None:
    note = build_compile_diagnostic_note(
        "F1_COMPILE",
        "CompilationError",
        "compiler failed",
    ).lower()

    assert "use " not in note
    assert "try " not in note
    assert "replace " not in note

