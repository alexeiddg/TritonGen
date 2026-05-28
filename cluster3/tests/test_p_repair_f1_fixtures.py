import hashlib
import ast
import sys
import types
from pathlib import Path

import pytest

from cluster1.data.kernels import get_kernel_spec
from cluster1.data.kernels.spec import torch as spec_torch
from cluster1.validation.compile_check import (
    cleanup_generated_module,
    load_generated_module,
    validate_signature,
)
from cluster3.constants import DEFAULT_P_REPAIR_BUDGET
from cluster3.feedback.compile_error_repair import (
    PRepairEvaluationInput,
    PRepairGenerationInput,
    PSeedAttempt,
    p_compile_repair_succeeded_from_result,
    run_p_repair_loop,
)
from cluster3.feedback.dispatcher import dispatch
from cluster3.feedback.prompts import (
    P_COMPILE_ERROR_EXCERPT_CHARS,
    build_p_feedback_prompt,
    excerpt_compile_error,
)
from shared.eval.levels.level0_ast_sanitizer import check_level0_ast_sanitizer
from shared.eval.levels.level0_parse import check_parse, check_signature


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "f1_compile_kernels"
BASE_PROMPT = "Implement the add kernel as a complete Triton Python module."
BASE_SEED = 23
SAMPLE_INDEX = 0
KERNEL_CLASS = "elementwise"
KERNEL_NAME = "add"
DTYPE = "fp32"

BAD_CONSTEXPR_ERROR = (
    "CompilationError: LLVM lowering failed because constexpr symbol "
    "MISSING_SCALE_FACTOR is undefined."
)
TYPE_ERROR_POINTER_ARITH_ERROR = (
    "CompilationError: PTX assembly rejected pointer arithmetic with fp32 offsets."
)
REMOTE_LAUNCHER_COMPATIBLE_FIXTURE = "launcher_signature_valid_compile_error.py"


def _fixture_source(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _eval_result(
    failure_code: str | None,
    *,
    source: str,
    generation_seed: int = BASE_SEED,
    compile_error: str | None = BAD_CONSTEXPR_ERROR,
    compile_error_type: str | None = "CompilationError",
    level_reached: int = 1,
    compile_success: bool | None = False,
    functional_success: bool | None = None,
) -> dict[str, object]:
    return {
        "failure_code": failure_code,
        "level_reached": level_reached,
        "compile_success": compile_success,
        "functional_success": functional_success,
        "compile_error": compile_error,
        "compile_error_type": compile_error_type,
        "generation_seed": generation_seed,
        "base_seed": BASE_SEED,
        "sample_index": SAMPLE_INDEX,
        "kernel_class": KERNEL_CLASS,
        "kernel_name": KERNEL_NAME,
        "dtype": DTYPE,
        "source_hash": _sha256(source),
        "prompt_hash": _sha256(BASE_PROMPT),
    }


def _seed_attempt(
    *,
    source: str,
    compile_error: str = BAD_CONSTEXPR_ERROR,
    compile_error_type: str = "CompilationError",
) -> PSeedAttempt:
    return PSeedAttempt(
        source=source,
        generation_seed=BASE_SEED,
        base_seed=BASE_SEED,
        sample_index=SAMPLE_INDEX,
        kernel_class=KERNEL_CLASS,
        kernel_name=KERNEL_NAME,
        dtype=DTYPE,
        source_hash=_sha256(source),
        prompt_hash=_sha256(BASE_PROMPT),
        prompt=BASE_PROMPT,
        evaluation_result=_eval_result(
            "F1_COMPILE",
            source=source,
            compile_error=compile_error,
            compile_error_type=compile_error_type,
        ),
        failure_code="F1_COMPILE",
        compile_error=compile_error,
        compile_error_type=compile_error_type,
    )


class _SingleGeneration:
    def __init__(self, source: str) -> None:
        self.source = source
        self.inputs: list[PRepairGenerationInput] = []

    def __call__(self, generation_input: PRepairGenerationInput) -> str:
        self.inputs.append(generation_input)
        return self.source


class _EvaluationQueue:
    def __init__(self, *results: dict[str, object]) -> None:
        self.results = list(results)
        self.inputs: list[PRepairEvaluationInput] = []

    def __call__(self, evaluation_input: PRepairEvaluationInput) -> dict[str, object]:
        self.inputs.append(evaluation_input)
        if not self.results:
            raise AssertionError("unexpected P evaluation call")
        return self.results.pop(0)


def _row_changed_terminal_class(initial: str, terminal: str | None) -> bool:
    return terminal != initial


def _install_fake_gpu_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = types.ModuleType("torch")
    fake_torch.Tensor = spec_torch.Tensor
    fake_torch.empty_like = lambda x: x
    fake_torch.empty = lambda *args, **kwargs: object()

    fake_triton = types.ModuleType("triton")
    fake_triton.__path__ = []
    fake_triton.jit = lambda fn: fn
    fake_triton.cdiv = lambda x, y: (x + y - 1) // y

    fake_tl = types.ModuleType("triton.language")
    fake_tl.constexpr = object()
    fake_tl.float32 = object()
    fake_triton.language = fake_tl

    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "triton", fake_triton)
    monkeypatch.setitem(sys.modules, "triton.language", fake_tl)


def test_invalid_decorator_terminates_p_does_not_fire() -> None:
    source = _fixture_source("invalid_decorator.py")

    decision = dispatch("P", "F0_NO_DECORATOR", 0)
    p_repair_attempted = decision.route == "p_loop"

    assert "@triton.jot" in source
    assert decision.route == "terminate"
    assert decision.route != "p_loop"
    assert p_repair_attempted is False


def test_bad_constexpr_triggers_p_loop() -> None:
    seed_source = _fixture_source("bad_constexpr.py")
    corrected_source = seed_source.replace(
        "MISSING_SCALE_FACTOR + tl.full((BLOCK,), 0.0, tl.float32)",
        "tl.full((BLOCK,), 2.0, tl.float32)",
    )
    generation = _SingleGeneration(corrected_source)
    evaluation = _EvaluationQueue(
        _eval_result(
            None,
            source=corrected_source,
            generation_seed=BASE_SEED * 10 + 1,
            compile_error=None,
            compile_error_type=None,
            level_reached=2,
            compile_success=True,
            functional_success=True,
        )
    )

    result = run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=BASE_SEED,
        generation=generation,
        evaluation=evaluation,
        seed_attempt=_seed_attempt(source=seed_source),
        repair_budget=1,
    )

    assert result.status == "compile_repaired_then_success"
    assert result.stop_reason == "p_compile_repaired_then_success"
    assert result.attempts_executed == 2
    assert result.successful_attempt_index == 1
    assert result.terminal_source == corrected_source
    assert p_compile_repair_succeeded_from_result(result) is True
    assert (
        _row_changed_terminal_class(
            result.initial_failure_code,
            result.final_failure_code,
        )
        is True
    )
    assert len(generation.inputs) == 1
    assert len(evaluation.inputs) == 1


def test_p_loop_exhausts_budget_on_persistent_compile_error() -> None:
    seed_source = _fixture_source("bad_constexpr.py")
    generated_source = seed_source.replace("MISSING_SCALE_FACTOR", "STILL_MISSING")
    failure_results = tuple(
        _eval_result(
            "F1_COMPILE",
            source=generated_source,
            generation_seed=BASE_SEED * 10 + attempt_index,
            compile_error=f"CompilationError: unresolved symbol on attempt {attempt_index}",
            compile_error_type="CompilationError",
        )
        for attempt_index in range(1, DEFAULT_P_REPAIR_BUDGET + 1)
    )

    result = run_p_repair_loop(
        base_prompt=BASE_PROMPT,
        base_seed=BASE_SEED,
        generation=_SingleGeneration(generated_source),
        evaluation=_EvaluationQueue(*failure_results),
        seed_attempt=_seed_attempt(source=seed_source),
        repair_budget=DEFAULT_P_REPAIR_BUDGET,
    )

    assert result.status == "compile_unchanged_exhausted"
    assert result.stop_reason == "p_budget_exhausted"
    assert result.attempts_executed == DEFAULT_P_REPAIR_BUDGET + 1
    assert result.final_failure_code == "F1_COMPILE"


def test_p_feedback_contains_no_level2_information() -> None:
    source = _fixture_source("bad_constexpr.py")

    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        source,
        "F1_COMPILE",
        BAD_CONSTEXPR_ERROR,
        "CompilationError",
    )

    assert prompt is not None
    lowered = prompt.lower()
    forbidden_terms = (
        "correctness",
        "numerical",
        "numeric",
        "nan",
        "inf",
        "shape mismatch",
        "hidden eval",
        "private eval",
        "eval_shape_set",
    )
    assert all(term not in lowered for term in forbidden_terms)


def test_p_feedback_excerpt_truncated_at_2000_chars() -> None:
    full_error = "H" * P_COMPILE_ERROR_EXCERPT_CHARS + "T" * 3000

    excerpt, _digest = excerpt_compile_error(full_error)

    assert len(excerpt) == P_COMPILE_ERROR_EXCERPT_CHARS
    assert excerpt == full_error[:P_COMPILE_ERROR_EXCERPT_CHARS]
    assert full_error[-100:] not in excerpt


def test_p_raw_error_excerpt_sha256_matches_full_error() -> None:
    full_error = (
        "CompilationError: PTX lowering failed at module offset 17\n"
        + "raw compiler detail\n" * P_COMPILE_ERROR_EXCERPT_CHARS
    )
    expected = hashlib.sha256(full_error.encode("utf-8")).hexdigest()

    excerpt, digest = excerpt_compile_error(full_error)

    assert digest == expected
    assert digest != hashlib.sha256(excerpt.encode("utf-8")).hexdigest()


def test_fixture_files_are_read_as_text_not_imported() -> None:
    fixture_names = {
        "invalid_decorator.py",
        "bad_constexpr.py",
        REMOTE_LAUNCHER_COMPATIBLE_FIXTURE,
        "wrong_launch_signature.py",
        "type_error_in_pointer_arith.py",
    }
    module_stems = {name.removesuffix(".py") for name in fixture_names}

    sources = {name: _fixture_source(name) for name in fixture_names}
    imported_fixture_modules = {
        module_name
        for module_name in sys.modules
        for stem in module_stems
        if module_name == stem or module_name.endswith(f".{stem}")
    }

    assert set(sources) == fixture_names
    assert all("@triton.jit" in text or "@triton.jot" in text for text in sources.values())
    assert imported_fixture_modules == set()


@pytest.mark.parametrize(
    "fixture_name",
    ("bad_constexpr.py", "type_error_in_pointer_arith.py"),
)
def test_phase12b_fixtures_do_not_match_remote_relu_launcher_contract(
    fixture_name: str,
) -> None:
    source = _fixture_source(fixture_name)
    spec = get_kernel_spec("elementwise")

    ok, error = check_signature(source, spec)

    assert ok is False
    assert error == "Signature mismatch: launcher 'relu' not found"


def test_launcher_signature_valid_compile_error_fixture_crosses_f0_signature() -> None:
    source = _fixture_source(REMOTE_LAUNCHER_COMPATIBLE_FIXTURE)
    spec = get_kernel_spec("elementwise")
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    launcher = next(node for node in functions if node.name == "relu")

    assert check_parse(source) == (True, None)
    assert check_signature(source, spec) == (True, None)
    assert check_level0_ast_sanitizer(source).safe_success is True
    assert [node.name for node in functions] == ["_relu_kernel", "relu"]
    assert [arg.arg for arg in launcher.args.args] == ["x"]
    assert "MISSING_SCALE_FACTOR" in source
    assert dispatch("P", "F1_COMPILE", 1).route == "p_loop"


def test_launcher_signature_valid_compile_error_fixture_matches_runtime_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_gpu_modules(monkeypatch)
    source = _fixture_source(REMOTE_LAUNCHER_COMPATIBLE_FIXTURE)
    spec = get_kernel_spec("elementwise")
    module = load_generated_module(source)
    try:
        assert validate_signature(module, spec.compile_spec) is None
    finally:
        cleanup_generated_module(module)


def test_wrong_launch_signature_fixture_boundary_is_documented() -> None:
    source = _fixture_source("wrong_launch_signature.py")

    f1_decision = dispatch("P", "F1_COMPILE", 1)
    f0_decision = dispatch("P", "F0_BAD_SIGNATURE", 0)

    assert "alpha: tl.constexpr" in source
    assert "n_elements=x.numel()" in source
    assert f1_decision.route == "p_loop"
    assert f0_decision.route == "terminate"


def test_type_error_pointer_arith_builds_f1_compile_seed() -> None:
    source = _fixture_source("type_error_in_pointer_arith.py")

    seed = _seed_attempt(
        source=source,
        compile_error=TYPE_ERROR_POINTER_ARITH_ERROR,
        compile_error_type="PTXAssemblyError",
    )

    assert "x_ptr + float_offsets" in source
    assert seed.failure_code == "F1_COMPILE"
    assert seed.compile_error == TYPE_ERROR_POINTER_ARITH_ERROR
    assert seed.compile_error_type == "PTXAssemblyError"


def test_p_feedback_allows_llvm_ptx_compile_error_text() -> None:
    prompt = build_p_feedback_prompt(
        BASE_PROMPT,
        _fixture_source("bad_constexpr.py"),
        "F1_COMPILE",
        "LLVM pass failed before PTX assembly completed.",
        "LLVMError",
    )

    assert prompt is not None
    assert "LLVM pass failed" in prompt
    assert "PTX assembly" in prompt


def test_p_feedback_rejects_speedup_profiler_terms_in_fixture_context() -> None:
    with pytest.raises(ValueError, match="speedup"):
        build_p_feedback_prompt(
            BASE_PROMPT,
            _fixture_source("bad_constexpr.py"),
            "F1_COMPILE",
            "CompilationError: speedup profiler details leaked into stderr",
            "CompilationError",
        )
