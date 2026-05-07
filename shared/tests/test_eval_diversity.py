"""Tests for source and AST diversity helpers."""

from __future__ import annotations

import pytest

from shared.eval.diversity import ast_structure_hash, source_hash, unique_ratio


def test_sources_differing_only_in_full_line_comments_share_source_hash() -> None:
    first = """
# leading comment
x = 1

y = x + 1
"""
    second = """
x = 1
# different comment
y = x + 1
"""

    assert source_hash(first) == source_hash(second)


def test_variable_renames_collapse_under_ast_hash_but_not_source_hash() -> None:
    first = """
def add(a, b):
    c = a + b
    return c
"""
    second = """
def add(x, y):
    z = x + y
    return z
"""

    assert source_hash(first) != source_hash(second)
    assert ast_structure_hash(first) == ast_structure_hash(second)


def test_unparseable_source_returns_none_for_ast_hash() -> None:
    assert ast_structure_hash("def broken(:\n") is None


def test_unique_ratio_source_mode() -> None:
    sources = ["x = 1\n", "# comment\nx = 1\n", "y = 2\n"]

    assert unique_ratio(sources, mode="source") == 2 / 3


def test_unique_ratio_ast_mode_counts_unparseable_source_fallbacks() -> None:
    renamed_first = "def add(a, b):\n    return a + b\n"
    renamed_second = "def add(x, y):\n    return x + y\n"
    broken = "def broken(:\n"

    assert unique_ratio([renamed_first, renamed_second, broken], mode="ast") == 2 / 3
    assert unique_ratio([broken, broken], mode="ast") == 1 / 2


def test_unique_ratio_empty_list_is_zero() -> None:
    assert unique_ratio([], mode="source") == 0.0


def test_unique_ratio_unknown_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown diversity mode"):
        unique_ratio(["x = 1"], mode="unknown")
