"""Compatibility entry point for grammar acceptance tests."""

from __future__ import annotations

import pytest

from cluster1.grammar.acceptance_fixtures import (
    BAD_KERNELS,
    GOOD_KERNELS,
    TASK_AGNOSTIC_BAD_KERNELS,
    TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS,
    TASK_AGNOSTIC_GOOD_KERNELS,
)
from cluster1.grammar.triton_kernel_validator import (
    TASK_AGNOSTIC_GBNF_PATH,
    accepts_source,
)


@pytest.mark.parametrize("name,source", GOOD_KERNELS.items())
def test_good_grammar_acceptance_fixtures(name: str, source: str) -> None:
    assert accepts_source(source), f"GOOD_KERNELS[{name!r}] was rejected"


@pytest.mark.parametrize("name,source", BAD_KERNELS.items())
def test_bad_grammar_acceptance_fixtures(name: str, source: str) -> None:
    assert not accepts_source(source), f"BAD_KERNELS[{name!r}] was accepted"


@pytest.mark.parametrize("name", TASK_AGNOSTIC_GOOD_KERNELS)
def test_task_agnostic_good_grammar_acceptance_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_GOOD_KERNELS[name]

    assert accepts_source(
        source,
        TASK_AGNOSTIC_GBNF_PATH,
    ), f"TASK_AGNOSTIC_GOOD_KERNELS[{name!r}] was rejected"


@pytest.mark.parametrize("name", TASK_AGNOSTIC_BAD_KERNELS)
def test_task_agnostic_bad_grammar_acceptance_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_BAD_KERNELS[name]

    assert not accepts_source(
        source,
        TASK_AGNOSTIC_GBNF_PATH,
    ), f"TASK_AGNOSTIC_BAD_KERNELS[{name!r}] was accepted"


@pytest.mark.parametrize("name", TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS)
def test_task_agnostic_compile_catchable_acceptance_fixtures(
    name: str,
) -> None:
    source = TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS[name]

    assert accepts_source(
        source,
        TASK_AGNOSTIC_GBNF_PATH,
    ), f"TASK_AGNOSTIC_COMPILE_CATCHABLE_KERNELS[{name!r}] was rejected"
