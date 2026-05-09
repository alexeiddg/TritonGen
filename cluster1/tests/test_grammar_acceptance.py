"""Compatibility entry point for grammar acceptance tests."""

from __future__ import annotations

import pytest

from cluster1.grammar.acceptance_fixtures import BAD_KERNELS, GOOD_KERNELS
from cluster1.grammar.triton_kernel_validator import accepts_source


@pytest.mark.parametrize("name,source", GOOD_KERNELS.items())
def test_good_grammar_acceptance_fixtures(name: str, source: str) -> None:
    assert accepts_source(source), f"GOOD_KERNELS[{name!r}] was rejected"


@pytest.mark.parametrize("name,source", BAD_KERNELS.items())
def test_bad_grammar_acceptance_fixtures(name: str, source: str) -> None:
    assert not accepts_source(source), f"BAD_KERNELS[{name!r}] was accepted"
