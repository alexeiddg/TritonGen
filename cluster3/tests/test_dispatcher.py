from __future__ import annotations

import pytest

from cluster3.feedback.dispatcher import DispatchDecision, dispatch, is_p_eligible
from shared.eval.failure_taxonomy import FAILURE_CODES


CONDITIONS = ("none", "G", "C", "G+C", "P", "G+P", "C+P", "G+C+P")
P_ACTIVE_CONDITIONS = {"P", "G+P", "C+P", "G+C+P"}
C_ACTIVE_CONDITIONS = {"C", "G+C", "C+P", "G+C+P"}
LEVELS = (0, 1, 2, None)
FAILURE_CODES_AND_SUCCESS = tuple(sorted(FAILURE_CODES)) + (None,)


@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("level_reached", LEVELS)
@pytest.mark.parametrize("failure_code", FAILURE_CODES_AND_SUCCESS)
def test_dispatch_table_all_failure_codes_levels_and_conditions(
    condition: str,
    failure_code: str | None,
    level_reached: int | None,
) -> None:
    expected = _expected_decision(condition, failure_code, level_reached)

    if expected is ValueError:
        with pytest.raises(ValueError):
            dispatch(condition, failure_code, level_reached)
        return

    assert dispatch(condition, failure_code, level_reached) == expected


@pytest.mark.parametrize("condition", CONDITIONS)
def test_dispatch_p_eligible_only_f1_compile_at_level1(condition: str) -> None:
    decision = dispatch(condition, "F1_COMPILE", 1)

    if condition in P_ACTIVE_CONDITIONS:
        assert decision.route == "p_loop"
        assert decision.reason == "p_eligible"
    else:
        assert decision.route == "terminate"
        assert decision.reason == "f1_compile_terminal_no_p"
    assert decision.failure_code == "F1_COMPILE"
    assert decision.c_loop_source == "none"


@pytest.mark.parametrize("failure_code", ("F1_COMPILE", "F1_RUNTIME"))
def test_dispatcher_rejects_f1_with_level0(failure_code: str) -> None:
    with pytest.raises(ValueError, match="level_reached"):
        dispatch("P", failure_code, 0)


@pytest.mark.parametrize(
    "failure_code",
    sorted(code for code in FAILURE_CODES if code.startswith("F2_")),
)
def test_dispatcher_rejects_f2_with_level1(failure_code: str) -> None:
    with pytest.raises(ValueError, match="level_reached"):
        dispatch("C+P", failure_code, 1)


@pytest.mark.parametrize("level_reached", (2, 3))
def test_dispatch_c_routing_requires_level_reached_ge_2(level_reached: int) -> None:
    decision = dispatch("C+P", "F2_NUMERIC_LARGE", level_reached)

    assert decision == DispatchDecision(
        route="c_loop",
        reason="c_eligible_initial_f2",
        failure_code="F2_NUMERIC_LARGE",
        c_loop_source="initial_f2",
    )


@pytest.mark.parametrize("failure_code", sorted(FAILURE_CODES))
def test_dispatch_rejects_level_reached_none(failure_code: str) -> None:
    decision = dispatch("G+C+P", failure_code, None)

    assert decision == DispatchDecision(
        route="terminate",
        reason="level_reached_missing",
        failure_code=failure_code,
    )


def test_dispatch_p_eligible_only_f1_compile() -> None:
    for failure_code in FAILURE_CODES_AND_SUCCESS:
        assert is_p_eligible(failure_code) is (failure_code == "F1_COMPILE")


@pytest.mark.parametrize("condition", CONDITIONS)
def test_dispatch_c_routing_requires_c_in_condition(condition: str) -> None:
    decision = dispatch(condition, "F2_NUMERIC_LARGE", 2)

    if condition in C_ACTIVE_CONDITIONS:
        assert decision.route == "c_loop"
        assert decision.reason == "c_eligible_initial_f2"
        assert decision.c_loop_source == "initial_f2"
    else:
        assert decision.route == "terminate"
        assert decision.reason == "f2_terminal_no_c"
        assert decision.c_loop_source == "none"


@pytest.mark.parametrize("condition", ("C+P", "G+C+P"))
def test_dispatch_initial_f2_marks_c_loop_source_initial_f2(condition: str) -> None:
    decision = dispatch(condition, "F2_NUMERIC_LARGE", 2)

    assert decision.route == "c_loop"
    assert decision.reason == "c_eligible_initial_f2"
    assert decision.failure_code == "F2_NUMERIC_LARGE"
    assert decision.c_loop_source == "initial_f2"


def test_dispatcher_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError, match="condition"):
        dispatch("X", None, 2)


def test_dispatcher_rejects_unknown_failure_code() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        dispatch("P", "F4_UNKNOWN", 0)


def test_dispatcher_rejects_unknown_condition_before_success_shortcut() -> None:
    with pytest.raises(ValueError, match="condition"):
        dispatch("X", None, 2, functional_success=True)


def test_dispatcher_rejects_unknown_failure_code_before_level0_terminal() -> None:
    with pytest.raises(ValueError, match="failure_code"):
        dispatch("P", "F4_UNKNOWN", 0)


@pytest.mark.parametrize(
    ("failure_code", "level_reached"),
    (
        ("F0_PARSE", 1),
        ("F0_PARSE", 2),
        ("F1_COMPILE", 0),
        ("F1_COMPILE", 2),
        ("F1_RUNTIME", 0),
        ("F1_RUNTIME", 2),
        ("F2_NUMERIC_LARGE", 0),
        ("F2_NUMERIC_LARGE", 1),
    ),
)
def test_dispatcher_validates_failure_code_level_compatibility(
    failure_code: str,
    level_reached: int,
) -> None:
    with pytest.raises(ValueError, match="level_reached"):
        dispatch("G+C+P", failure_code, level_reached)


def _expected_decision(
    condition: str,
    failure_code: str | None,
    level_reached: int | None,
) -> DispatchDecision | type[ValueError]:
    if failure_code is None:
        return DispatchDecision(
            route="terminate",
            reason="success",
            failure_code=None,
        )
    if level_reached is None:
        return DispatchDecision(
            route="terminate",
            reason="level_reached_missing",
            failure_code=failure_code,
        )
    if failure_code.startswith("F0_"):
        if level_reached != 0:
            return ValueError
        return DispatchDecision(
            route="terminate",
            reason="f0_terminal",
            failure_code=failure_code,
        )
    if failure_code == "F1_COMPILE":
        if level_reached != 1:
            return ValueError
        if condition not in P_ACTIVE_CONDITIONS:
            return DispatchDecision(
                route="terminate",
                reason="f1_compile_terminal_no_p",
                failure_code=failure_code,
            )
        return DispatchDecision(
            route="p_loop",
            reason="p_eligible",
            failure_code=failure_code,
        )
    if failure_code == "F1_RUNTIME":
        if level_reached != 1:
            return ValueError
        return DispatchDecision(
            route="terminate",
            reason="unrecoverable_runtime",
            failure_code=failure_code,
        )
    if failure_code.startswith("F2_"):
        if level_reached < 2:
            return ValueError
        if condition in C_ACTIVE_CONDITIONS:
            return DispatchDecision(
                route="c_loop",
                reason="c_eligible_initial_f2",
                failure_code=failure_code,
                c_loop_source="initial_f2",
            )
        return DispatchDecision(
            route="terminate",
            reason="f2_terminal_no_c",
            failure_code=failure_code,
        )
    if failure_code.startswith("F3_"):
        return DispatchDecision(
            route="terminate",
            reason="f3_terminal",
            failure_code=failure_code,
        )
    raise AssertionError(f"unhandled test failure code {failure_code!r}")
