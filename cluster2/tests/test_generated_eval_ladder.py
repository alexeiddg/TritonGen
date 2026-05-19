"""Focused tests for generated C Level 0 -> Level 1 -> Level 2 ordering."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cluster2.experiments.run_cluster2_modal import RunnerDependencies, run_cluster2
from cluster2.modal import correctness_runner
from cluster2.tests.test_run_cluster2_modal import _config, _fake_generation
from shared.eval.levels.level1_compile import Level1CompileResult


def test_generated_c_f0_parse_stops_before_level1_level2(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    call_order: list[str] = []
    _install_ladder_fakes(
        monkeypatch,
        call_order=call_order,
        parse_result=(False, "SyntaxError: invalid syntax"),
    )

    result = _run_c_ladder_case(tmp_path, generation_calls, repair_budget=2)

    assert call_order == ["level0_parse"]
    assert len(generation_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 0
    assert result.rows[0].failure_code == "F0_PARSE"
    assert result.rows[0].functional_success is False


def test_generated_c_f0_bad_signature_stops_before_level1_level2(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    call_order: list[str] = []
    _install_ladder_fakes(
        monkeypatch,
        call_order=call_order,
        signature_result=(False, "Signature mismatch: expected ['x'], got ['y']"),
    )

    result = _run_c_ladder_case(tmp_path, generation_calls, repair_budget=2)

    assert call_order == ["level0_parse", "kernel_spec", "level0_signature"]
    assert len(generation_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 0
    assert result.rows[0].failure_code == "F0_BAD_SIGNATURE"
    assert result.rows[0].functional_success is False


def test_generated_c_f1_compile_stops_before_level2(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    call_order: list[str] = []
    _install_ladder_fakes(
        monkeypatch,
        call_order=call_order,
        compile_result=Level1CompileResult(
            compile_success=False,
            compile_error="compile failed",
            compile_error_type="CompilationError",
            compile_results_by_dtype={"fp32": False},
            n_shapes_tested=1,
        ),
    )

    result = _run_c_ladder_case(tmp_path, generation_calls, repair_budget=2)

    assert call_order == [
        "level0_parse",
        "kernel_spec",
        "level0_signature",
        "runtime_config",
        "level1_compile",
    ]
    assert len(generation_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 0
    assert result.rows[0].failure_code == "F1_COMPILE"
    assert result.rows[0].functional_success is False


def test_generated_c_f2_failure_is_only_case_that_fires_repair(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    call_order: list[str] = []
    _install_ladder_fakes(
        monkeypatch,
        call_order=call_order,
        level2_success_by_attempt={0: False, 1: True},
    )

    result = _run_c_ladder_case(tmp_path, generation_calls, repair_budget=1)

    assert call_order == [
        "level0_parse",
        "kernel_spec",
        "level0_signature",
        "runtime_config",
        "level1_compile",
        "level2_correctness",
        "level0_parse",
        "kernel_spec",
        "level0_signature",
        "runtime_config",
        "level1_compile",
        "level2_correctness",
    ]
    assert [row.attempt_index for row in result.rows] == [0, 1]
    assert result.rows[0].failure_code == "F2_NUMERIC_LARGE"
    assert result.rows[1].failure_code is None
    assert len(generation_calls) == 2
    feedback_prompt = generation_calls[1]["prompt"]
    assert "Failure code:\nF2_NUMERIC_LARGE" in feedback_prompt
    assert "max_abs_diff=1" in feedback_prompt
    assert "compile failed" not in feedback_prompt
    assert "Signature mismatch" not in feedback_prompt


def test_generated_c_level2_pass_records_success_without_repair(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generation_calls: list[dict[str, Any]] = []
    call_order: list[str] = []
    _install_ladder_fakes(
        monkeypatch,
        call_order=call_order,
        level2_success_by_attempt={0: True},
    )

    result = _run_c_ladder_case(tmp_path, generation_calls, repair_budget=1)

    assert call_order == [
        "level0_parse",
        "kernel_spec",
        "level0_signature",
        "runtime_config",
        "level1_compile",
        "level2_correctness",
    ]
    assert len(generation_calls) == 1
    assert len(result.rows) == 1
    assert result.rows[0].attempt_index == 0
    assert result.rows[0].failure_code is None
    assert result.rows[0].functional_success is True


def _run_c_ladder_case(
    tmp_path,
    generation_calls: list[dict[str, Any]],
    *,
    repair_budget: int,
):
    return run_cluster2(
        _config(tmp_path, condition="C", repair_budget=repair_budget, n=1),
        dependencies=RunnerDependencies(
            generation=_fake_generation(generation_calls),
            correctness=lambda request: correctness_runner.run_correctness_payload(
                request.model_dump()
            ),
        ),
    )


def _install_ladder_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    call_order: list[str],
    parse_result: tuple[bool, str | None] = (True, None),
    signature_result: tuple[bool, str | None] = (True, None),
    compile_result: Level1CompileResult | None = None,
    level2_success_by_attempt: dict[int, bool] | None = None,
) -> None:
    resolved_compile_result = compile_result or Level1CompileResult(
        compile_success=True,
        compile_error=None,
        compile_error_type=None,
        compile_results_by_dtype={"fp32": True},
        n_shapes_tested=1,
    )
    resolved_level2_success = level2_success_by_attempt or {0: True}

    monkeypatch.setattr(
        correctness_runner,
        "_configure_correctness_runtime",
        lambda: call_order.append("runtime_config"),
    )

    def fake_kernel_spec_for_request(request: object) -> SimpleNamespace:
        call_order.append("kernel_spec")
        identity = getattr(request, "identity")
        return SimpleNamespace(
            name=identity.kernel_name,
            launcher_name=identity.kernel_name,
            expected_params=["x"],
        )

    monkeypatch.setattr(
        correctness_runner,
        "_kernel_spec_for_request",
        fake_kernel_spec_for_request,
    )

    def fake_check_parse(source: str) -> tuple[bool, str | None]:
        del source
        call_order.append("level0_parse")
        return parse_result

    def fake_check_signature(
        source: str,
        kernel_spec: object,
    ) -> tuple[bool, str | None]:
        del source, kernel_spec
        call_order.append("level0_signature")
        return signature_result

    def fake_check_compile_level1(
        source: str,
        kernel_spec: object,
    ) -> Level1CompileResult:
        del source, kernel_spec
        call_order.append("level1_compile")
        return resolved_compile_result

    def fake_run_eval_pipeline(config: object, *, level2_request: object):
        del config
        call_order.append("level2_correctness")
        attempt_index = getattr(level2_request, "attempt_index")
        success = resolved_level2_success.get(attempt_index, False)
        return SimpleNamespace(
            level2_result=_level2_result(success=success),
        )

    monkeypatch.setattr(correctness_runner, "check_parse", fake_check_parse)
    monkeypatch.setattr(correctness_runner, "check_signature", fake_check_signature)
    monkeypatch.setattr(
        correctness_runner,
        "check_compile_level1",
        fake_check_compile_level1,
    )
    monkeypatch.setattr(correctness_runner, "run_eval_pipeline", fake_run_eval_pipeline)


def _level2_result(*, success: bool) -> SimpleNamespace:
    if success:
        return SimpleNamespace(
            functional_success=True,
            repair_set_success=True,
            eval_set_success=True,
            failure_code=None,
            correctness_error=None,
            feedback=None,
            num_repair_shapes=1,
            num_eval_shapes=1,
            num_test_shapes=2,
            shapes_passed=2,
            repair_shapes_passed=1,
            eval_shapes_passed=1,
            max_abs_diff=0.0,
            max_rel_diff=0.0,
        )
    return SimpleNamespace(
        functional_success=False,
        repair_set_success=False,
        eval_set_success=False,
        failure_code="F2_NUMERIC_LARGE",
        correctness_error=(
            "Repair shape (2,) failed Level 2: Numeric mismatch: "
            "max_abs_diff=1, max_rel_diff=1, atol=0.001, rtol=0.001"
        ),
        feedback=(
            "Repair shape (2,) failed Level 2: Numeric mismatch: "
            "max_abs_diff=1, max_rel_diff=1, atol=0.001, rtol=0.001"
        ),
        num_repair_shapes=1,
        num_eval_shapes=1,
        num_test_shapes=2,
        shapes_passed=0,
        repair_shapes_passed=0,
        eval_shapes_passed=0,
        max_abs_diff=1.0,
        max_rel_diff=1.0,
    )
