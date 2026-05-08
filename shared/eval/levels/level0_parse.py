"""Pure AST Level 0 parse and signature checks."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping, Sequence
from typing import Any


def check_parse(source: str) -> tuple[bool, str | None]:
    """Return whether ``source`` is syntactically valid Python."""

    try:
        ast.parse(source)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"
    return True, None


def check_signature(source: str, kernel_spec: Any) -> tuple[bool, str | None]:
    """Verify the launcher signature and presence of a ``@triton.jit`` helper.

    This check intentionally parses only. It does not execute generated source
    and does not import torch or triton.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    expected_params = _expected_param_names(kernel_spec)
    if expected_params is None:
        return False, "Signature mismatch: could not determine expected params"

    functions = _top_level_functions(tree)
    if not any(_has_triton_jit_decorator(node) for node in functions):
        return False, "F0_NO_DECORATOR: No @triton.jit decorated function found"

    launcher_name = _launcher_name(kernel_spec)
    if launcher_name is not None:
        launcher = next(
            (node for node in reversed(functions) if node.name == launcher_name),
            None,
        )
        if launcher is None:
            return False, f"Signature mismatch: launcher {launcher_name!r} not found"
        return _compare_function_params(launcher, expected_params)

    for node in functions:
        if _has_triton_jit_decorator(node):
            return _compare_function_params(node, expected_params)

    return False, "F0_NO_DECORATOR: No @triton.jit decorated function found"


def _has_triton_jit_decorator(node: ast.FunctionDef) -> bool:
    return any(_is_triton_jit_decorator(decorator) for decorator in node.decorator_list)


def _top_level_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in tree.body if isinstance(node, ast.FunctionDef)]


def _is_triton_jit_decorator(decorator: ast.AST) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    chain = _attribute_chain(target)
    return chain == ["triton", "jit"] or chain == ["jit"]


def _attribute_chain(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_attribute_chain(node.value), node.attr]
    return []


def _function_param_names(node: ast.FunctionDef) -> list[str] | None:
    if (
        node.args.posonlyargs
        or node.args.vararg is not None
        or node.args.kwonlyargs
        or node.args.kwarg is not None
    ):
        return None
    return [arg.arg for arg in node.args.args]


def _compare_function_params(
    node: ast.FunctionDef,
    expected_params: list[str],
) -> tuple[bool, str | None]:
    generated_params = _function_param_names(node)
    if generated_params is None:
        return False, "Signature mismatch: unsupported launcher argument kind"
    if generated_params != expected_params:
        return False, (
            f"Signature mismatch: expected params {expected_params}, "
            f"got {generated_params}"
        )
    return True, None


def _launcher_name(kernel_spec: Any) -> str | None:
    compile_spec = _get_field(kernel_spec, "compile_spec")
    for owner in (compile_spec, kernel_spec):
        if owner is None:
            continue
        candidate = _get_field(owner, "launcher_name")
        if isinstance(candidate, str) and candidate:
            return candidate

    candidate = _get_field(kernel_spec, "name")
    if isinstance(candidate, str) and candidate:
        return candidate
    return None


def _expected_param_names(kernel_spec: Any) -> list[str] | None:
    expected_params = _get_field(kernel_spec, "expected_params")
    if expected_params is not None:
        return _coerce_param_names(expected_params)

    compile_spec = _get_field(kernel_spec, "compile_spec")
    for owner in (compile_spec, kernel_spec):
        if owner is None:
            continue
        for field_name in ("signature", "reference_signature"):
            candidate = _get_field(owner, field_name)
            names = _coerce_param_names(candidate)
            if names is not None:
                return names
    return None


def _get_field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _coerce_param_names(value: Any) -> list[str] | None:
    if value is None:
        return None

    if isinstance(value, inspect.Signature):
        return [param.name for param in value.parameters.values()]

    parameters = getattr(value, "parameters", None)
    if isinstance(parameters, Mapping):
        return [str(name) for name in parameters]

    if isinstance(value, Mapping):
        return [str(name) for name in value]

    if isinstance(value, Sequence) and not isinstance(value, str):
        names: list[str] = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
                continue
            name = getattr(item, "name", None)
            if isinstance(name, str):
                names.append(name)
                continue
            return None
        return names

    return None
