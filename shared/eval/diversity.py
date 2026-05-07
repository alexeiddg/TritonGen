"""Source and AST diversity helpers."""

from __future__ import annotations

import ast
import hashlib
from typing import Literal


def source_hash(source: str) -> str:
    """Hash normalized source for textual deduplication."""

    normalized = "\n".join(_normalized_source_lines(source))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ast_structure_hash(source: str) -> str | None:
    """Hash AST structure after normalizing variable names.

    Returns ``None`` for syntactically invalid Python.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    normalized = _AstNameNormalizer().visit(tree)
    ast.fix_missing_locations(normalized)
    dumped = ast.dump(normalized, annotate_fields=False, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def unique_ratio(sources: list[str], mode: Literal["source", "ast"]) -> float:
    """Return ``count(unique hashes) / len(sources)``.

    In ``ast`` mode, unparseable sources remain in the denominator and fall back
    to their source hash with an ``unparseable`` prefix. Identical unparseable
    sources therefore count as duplicates; distinct unparseable sources remain
    distinct.
    """

    if not sources:
        return 0.0
    if mode == "source":
        hashes = [source_hash(source) for source in sources]
    elif mode == "ast":
        hashes = [
            ast_structure_hash(source) or f"unparseable:{source_hash(source)}"
            for source in sources
        ]
    else:
        raise ValueError(f"unknown diversity mode: {mode!r}")
    return len(set(hashes)) / len(sources)


def _normalized_source_lines(source: str) -> list[str]:
    return [
        stripped
        for stripped in (line.strip() for line in source.strip().splitlines())
        if stripped and not stripped.startswith("#")
    ]


class _AstNameNormalizer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="VAR", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = "ARG"
        node.annotation = self.visit(node.annotation) if node.annotation else None
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "FUNC"
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = "FUNC"
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = "CLASS"
        return self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> ast.alias:
        node.name = "ALIAS"
        node.asname = "ALIAS" if node.asname is not None else None
        return node
