"""Offline validator for the Cluster 1 Triton GBNF grammar.

This module deliberately does not import torch, triton, xgrammar, or execute
generated source. It uses Lark for a layout-level parse and Python's AST for
static checks that mirror the contract-sensitive grammar restrictions.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from cluster1.data.prompts.prompt_contract import (
    ELEMENTWISE_AUTOTUNE_CONFIGS,
    MATMUL_AUTOTUNE_CONFIGS,
    REDUCTION_AUTOTUNE_CONFIGS,
)


DEFAULT_GBNF_PATH = Path(__file__).with_name("triton_kernel.gbnf")

REQUIRED_PRODUCTIONS = frozenset(
    {
        "triton-core-call",
        "triton-compute-call",
        "control-flow-stmt",
        "autotune-decorator",
        "launch-wrapper",
    }
)

ALLOWED_TL_CALLS = frozenset(
    {
        "load",
        "store",
        "arange",
        "program_id",
        "zeros",
        "full",
        "dot",
        "atomic_add",
        "sum",
        "max",
        "exp",
        "log",
        "sqrt",
        "where",
    }
)

PROMPT_AUTOTUNE_CONFIGS = (
    ELEMENTWISE_AUTOTUNE_CONFIGS + REDUCTION_AUTOTUNE_CONFIGS + MATMUL_AUTOTUNE_CONFIGS
)
ALLOWED_AUTOTUNE_CONFIGS = frozenset(
    (
        tuple(
            sorted(
                (key, value)
                for key, value in config.items()
                if key not in {"num_warps", "num_stages"}
            )
        ),
        config["num_warps"],
        config["num_stages"],
    )
    for config in PROMPT_AUTOTUNE_CONFIGS
)


@dataclass(frozen=True)
class GrammarValidationReport:
    grammar_path: Path
    lark_compiles: bool
    n_accept_cases: int
    n_reject_cases: int
    errors: list[str]


def validate_grammar_file(
    grammar_path: Path = DEFAULT_GBNF_PATH,
) -> GrammarValidationReport:
    errors: list[str] = []
    n_accept_cases = 0
    n_reject_cases = 0

    try:
        gbnf_text = grammar_path.read_text(encoding="utf-8")
        _validate_gbnf_text(gbnf_text)
        _compile_lark_parser(gbnf_text)
        lark_compiles = True
    except Exception as exc:  # noqa: BLE001 - report object must collect all failures.
        errors.append(f"{type(exc).__name__}: {exc}")
        lark_compiles = False

    try:
        from cluster1.grammar.test_grammar_acceptance import BAD_KERNELS, GOOD_KERNELS

        n_accept_cases = len(GOOD_KERNELS)
        n_reject_cases = len(BAD_KERNELS)
    except Exception as exc:  # noqa: BLE001 - fixture import is diagnostic only.
        errors.append(f"fixture import failed: {type(exc).__name__}: {exc}")

    return GrammarValidationReport(
        grammar_path=grammar_path,
        lark_compiles=lark_compiles,
        n_accept_cases=n_accept_cases,
        n_reject_cases=n_reject_cases,
        errors=errors,
    )


def accepts_source(
    source: str,
    grammar_path: Path = DEFAULT_GBNF_PATH,
) -> bool:
    try:
        gbnf_text = grammar_path.read_text(encoding="utf-8")
        parser = _compile_lark_parser(gbnf_text)
        parser.parse(source)
        tree = ast.parse(source)
        return _semantic_accepts(tree)
    except Exception:
        return False


@lru_cache(maxsize=8)
def _compile_lark_parser_from_text(gbnf_text: str):
    from lark import Lark

    _validate_gbnf_text(gbnf_text)
    return Lark(_gbnf_to_lark(gbnf_text), parser="earley", start="root")


def _compile_lark_parser(gbnf_text: str):
    return _compile_lark_parser_from_text(gbnf_text)


def _validate_required_productions(gbnf_text: str) -> None:
    missing = sorted(
        name for name in REQUIRED_PRODUCTIONS if f"{name} ::=" not in gbnf_text
    )
    if missing:
        raise ValueError(f"missing required GBNF productions: {', '.join(missing)}")


def _validate_gbnf_text(gbnf_text: str) -> None:
    _validate_required_productions(gbnf_text)
    productions = _collect_gbnf_productions(gbnf_text)
    _parse_gbnf_productions(productions)
    _validate_gbnf_references(productions)


def _gbnf_to_lark(gbnf_text: str) -> str:
    productions = _collect_gbnf_productions(gbnf_text)
    lines = [
        f"{_lark_rule_name(name)}: {_gbnf_rhs_to_lark(rhs)}"
        for name, rhs in productions.items()
    ]
    return "\n".join(lines) + "\n"


def _collect_gbnf_productions(gbnf_text: str) -> dict[str, str]:
    productions: dict[str, list[str]] = {}
    current_name: str | None = None

    for lineno, raw_line in enumerate(gbnf_text.splitlines(), start=1):
        line = _strip_gbnf_comment(raw_line).rstrip()
        if not line.strip():
            continue

        if "::=" in line:
            name_part, rhs_part = line.split("::=", 1)
            name = name_part.strip()
            if not _is_gbnf_name(name):
                raise ValueError(f"invalid production name at line {lineno}: {name!r}")
            if name in productions:
                raise ValueError(f"duplicate production {name!r} at line {lineno}")
            productions[name] = [rhs_part.strip()]
            current_name = name
            continue

        if current_name is None:
            raise ValueError(f"continuation without production at line {lineno}")
        productions[current_name].append(line.strip())

    if "root" not in productions:
        raise ValueError("missing root production")
    return {name: " ".join(parts).strip() for name, parts in productions.items()}


def _strip_gbnf_comment(line: str) -> str:
    in_string = False
    in_class = False
    quote = ""
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_string:
            if char == quote:
                in_string = False
            continue
        if in_class:
            if char == "]":
                in_class = False
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
            continue
        if char == "[":
            in_class = True
            continue
        if char == "#":
            return line[:index]
    return line


def _parse_gbnf_productions(productions: dict[str, str]) -> None:
    from lark import Lark

    parser = Lark(_GBNF_RHS_GRAMMAR, parser="lalr", start="rhs")
    for name, rhs in productions.items():
        try:
            parser.parse(rhs)
        except Exception as exc:
            raise ValueError(f"invalid RHS for production {name!r}: {exc}") from exc


def _validate_gbnf_references(productions: dict[str, str]) -> None:
    defined = set(productions)
    undefined: dict[str, set[str]] = {}
    for name, rhs in productions.items():
        refs = set(_iter_gbnf_references(rhs))
        missing = refs - defined
        if missing:
            undefined[name] = missing

    if undefined:
        details = "; ".join(
            f"{name}: {', '.join(sorted(missing))}"
            for name, missing in sorted(undefined.items())
        )
        raise ValueError(f"undefined GBNF references: {details}")


def _iter_gbnf_references(rhs: str):
    stripped = _blank_gbnf_literals(rhs)
    for match in _GBNF_NAME_RE.finditer(stripped):
        yield match.group(0)


def _blank_gbnf_literals(text: str) -> str:
    chars = list(text)
    in_string = False
    in_class = False
    quote = ""
    escaped = False
    for index, char in enumerate(chars):
        if escaped:
            chars[index] = " "
            escaped = False
            continue
        if char == "\\":
            if in_string or in_class:
                chars[index] = " "
                escaped = True
            continue
        if in_string:
            chars[index] = " "
            if char == quote:
                in_string = False
            continue
        if in_class:
            chars[index] = " "
            if char == "]":
                in_class = False
            continue
        if char in {"'", '"'}:
            chars[index] = " "
            in_string = True
            quote = char
            continue
        if char == "[":
            chars[index] = " "
            in_class = True
            continue
    return "".join(chars)


_GBNF_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")

_GBNF_RHS_GRAMMAR = r"""
rhs: choice
choice: sequence ("|" sequence)*
sequence: factor*
factor: atom POSTFIX?
?atom: NAME
     | STRING
     | CHAR_CLASS
     | "(" choice ")"
POSTFIX: "?" | "*" | "+"
NAME: /[A-Za-z_][A-Za-z0-9_-]*/
STRING: /"([^"\\]|\\.)*"/ | /'([^'\\]|\\.)*'/
CHAR_CLASS: /\[(\\.|[^\]\\])+\]/
%import common.WS_INLINE
%ignore WS_INLINE
"""


def _is_gbnf_name(value: str) -> bool:
    return _GBNF_NAME_RE.fullmatch(value) is not None


def _gbnf_rhs_to_lark(rhs: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(rhs):
        char = rhs[index]
        if char in {"'", '"'}:
            literal, index = _read_gbnf_string(rhs, index)
            if literal in {'""', "''"}:
                continue
            output.append(literal)
            continue
        if char == "[":
            char_class, index = _read_gbnf_char_class(rhs, index)
            output.append(f"/{char_class}/")
            continue
        if _is_gbnf_name_start(char):
            name, index = _read_gbnf_name(rhs, index)
            output.append(_lark_rule_name(name))
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _read_gbnf_string(text: str, start: int) -> tuple[str, int]:
    quote = text[start]
    index = start + 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            return text[start : index + 1], index + 1
        index += 1
    raise ValueError(f"unterminated string literal in GBNF RHS: {text[start:]!r}")


def _read_gbnf_char_class(text: str, start: int) -> tuple[str, int]:
    index = start + 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "]":
            return text[start : index + 1], index + 1
        index += 1
    raise ValueError(f"unterminated character class in GBNF RHS: {text[start:]!r}")


def _read_gbnf_name(text: str, start: int) -> tuple[str, int]:
    index = start + 1
    while index < len(text) and _is_gbnf_name_char(text[index]):
        index += 1
    return text[start:index], index


def _lark_rule_name(name: str) -> str:
    return name.replace("-", "_")


def _is_gbnf_name_start(char: str) -> bool:
    return char.isalpha() or char == "_"


def _is_gbnf_name_char(char: str) -> bool:
    return char.isalnum() or char in {"_", "-"}


def _semantic_accepts(tree: ast.Module) -> bool:
    if not _imports_are_valid(tree):
        return False

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 2:
        return False

    kernel_fn, wrapper_fn = functions
    if not _decorators_are_valid(kernel_fn):
        return False
    if not _kernel_contains_program_id(kernel_fn):
        return False
    if not _wrapper_launches_with_grid(wrapper_fn, kernel_fn.name):
        return False

    if not _function_statements_are_valid(kernel_fn, in_kernel=True):
        return False
    if not _function_statements_are_valid(wrapper_fn, in_kernel=False):
        return False

    return _all_calls_are_valid(
        kernel_fn,
        kernel_fn.name,
        allow_tl_calls=True,
        allow_runtime_calls=False,
        allow_kernel_launch=False,
    ) and (
        _all_calls_are_valid(
            wrapper_fn,
            kernel_fn.name,
            allow_tl_calls=False,
            allow_runtime_calls=True,
            allow_kernel_launch=True,
        )
    )


def _imports_are_valid(tree: ast.Module) -> bool:
    non_import_seen = False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if non_import_seen:
                return False
            if not _is_allowed_import(node):
                return False
        else:
            non_import_seen = True
    return True


def _is_allowed_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        imports = [(alias.name, alias.asname) for alias in node.names]
        return imports in [
            [("torch", None)],
            [("triton", None)],
            [("triton.language", "tl")],
        ]
    return False


def _decorators_are_valid(kernel_fn: ast.FunctionDef) -> bool:
    decorators = kernel_fn.decorator_list
    if len(decorators) == 1:
        return _is_attr_name(decorators[0], "triton", "jit")
    if len(decorators) == 2:
        return _is_autotune_decorator(decorators[0]) and _is_attr_name(
            decorators[1], "triton", "jit"
        )
    return False


def _is_autotune_decorator(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not _is_attr_name(node.func, "triton", "autotune"):
        return False

    kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
    if set(kwargs) != {"configs", "key"}:
        return False
    if not isinstance(kwargs["configs"], ast.List):
        return False
    if not isinstance(kwargs["key"], ast.List):
        return False
    if not all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in kwargs["key"].elts):
        return False
    return all(_is_fixed_config(entry) for entry in kwargs["configs"].elts)


def _is_fixed_config(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not _is_attr_name(node.func, "triton", "Config"):
        return False
    if len(node.args) != 1 or not isinstance(node.args[0], ast.Dict):
        return False

    config = _literal_dict(node.args[0])
    if config is None:
        return False

    kwargs = {kw.arg: _literal_int(kw.value) for kw in node.keywords if kw.arg is not None}
    if set(kwargs) != {"num_warps", "num_stages"}:
        return False
    normalized = (
        tuple(sorted(config.items())),
        kwargs["num_warps"],
        kwargs["num_stages"],
    )
    return normalized in ALLOWED_AUTOTUNE_CONFIGS


def _literal_dict(node: ast.Dict) -> dict[str, int] | None:
    output: dict[str, int] = {}
    for key_node, value_node in zip(node.keys, node.values, strict=True):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            return None
        value = _literal_int(value_node)
        if value is None:
            return None
        output[key_node.value] = value
    return output


def _literal_int(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def _kernel_contains_program_id(kernel_fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call) and _tl_call_name(node.func) == "program_id"
        for node in ast.walk(kernel_fn)
    )


def _wrapper_launches_with_grid(wrapper_fn: ast.FunctionDef, kernel_name: str) -> bool:
    return any(_is_grid_launch(node, kernel_name) for node in ast.walk(wrapper_fn))


def _is_grid_launch(node: ast.AST, kernel_name: str) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Subscript) and _is_name(func.value, kernel_name):
        return True
    if isinstance(func, ast.Attribute) and func.attr == "run" and _is_name(func.value, kernel_name):
        return any(kw.arg == "grid" for kw in node.keywords)
    return False


def _function_statements_are_valid(function: ast.FunctionDef, *, in_kernel: bool) -> bool:
    return all(_stmt_is_valid(stmt, in_kernel=in_kernel) for stmt in function.body)


def _stmt_is_valid(stmt: ast.stmt, *, in_kernel: bool) -> bool:
    if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Expr)):
        return True
    if isinstance(stmt, ast.Return):
        return not in_kernel
    if in_kernel and isinstance(stmt, ast.If):
        return all(_stmt_is_valid(child, in_kernel=True) for child in stmt.body) and all(
            _stmt_is_valid(child, in_kernel=True) for child in stmt.orelse
        )
    if in_kernel and isinstance(stmt, ast.For):
        return (
            _range_loop_is_valid(stmt)
            and all(_stmt_is_valid(child, in_kernel=True) for child in stmt.body)
            and not stmt.orelse
        )
    return False


def _range_loop_is_valid(stmt: ast.For) -> bool:
    if not isinstance(stmt.target, ast.Name):
        return False
    if not isinstance(stmt.iter, ast.Call):
        return False
    return (
        _is_name(stmt.iter.func, "range")
        and len(stmt.iter.args) == 3
        and not stmt.iter.keywords
    )


def _all_calls_are_valid(
    node_root: ast.AST,
    kernel_name: str,
    *,
    allow_tl_calls: bool,
    allow_runtime_calls: bool,
    allow_kernel_launch: bool,
) -> bool:
    for node in ast.walk(node_root):
        if not isinstance(node, ast.Call):
            continue
        tl_name = _tl_call_name(node.func)
        if tl_name is not None:
            if not allow_tl_calls:
                return False
            if tl_name not in ALLOWED_TL_CALLS:
                return False
            if not _valid_tl_call_shape(tl_name, node):
                return False
            continue
        if not _valid_non_tl_call(
            node,
            kernel_name,
            allow_runtime_calls=allow_runtime_calls,
            allow_kernel_launch=allow_kernel_launch,
        ):
            return False
    return True


def _valid_non_tl_call(
    node: ast.Call,
    kernel_name: str,
    *,
    allow_runtime_calls: bool,
    allow_kernel_launch: bool,
) -> bool:
    if _is_attr_name(node.func, "triton", "autotune"):
        return _is_autotune_decorator(node)
    if _is_attr_name(node.func, "triton", "Config"):
        return _is_fixed_config(node)
    if not allow_runtime_calls:
        return _is_name(node.func, "range") and len(node.args) == 3 and not node.keywords
    if _is_attr_name(node.func, "triton", "cdiv"):
        return len(node.args) == 2 and not node.keywords
    if _is_attr_name(node.func, "torch", "empty_like"):
        return len(node.args) == 1 and not node.keywords
    if _is_attr_name(node.func, "torch", "empty"):
        return len(node.args) == 1 and {kw.arg for kw in node.keywords} <= {
            "device",
            "dtype",
        }
    if isinstance(node.func, ast.Attribute) and node.func.attr == "numel":
        return not node.args and not node.keywords and isinstance(node.func.value, ast.Name)
    if isinstance(node.func, ast.Attribute) and node.func.attr == "to":
        return len(node.args) == 1 and not node.keywords and isinstance(node.func.value, ast.Name)
    if isinstance(node.func, ast.Name) and node.func.id in {"max", "min"}:
        return len(node.args) == 2 and not node.keywords
    if _is_name(node.func, "range"):
        return len(node.args) == 3 and not node.keywords
    if (
        allow_kernel_launch
        and isinstance(node.func, ast.Subscript)
        and _is_name(node.func.value, kernel_name)
    ):
        return True
    if (
        allow_kernel_launch
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and _is_name(node.func.value, kernel_name)
    ):
        return any(kw.arg == "grid" for kw in node.keywords)
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and _is_name(node.func.value, kernel_name)
    ):
        return False
    return False


def _valid_tl_call_shape(name: str, node: ast.Call) -> bool:
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    if any(kw.arg is None for kw in node.keywords):
        return False

    match name:
        case "load":
            return len(node.args) == 1 and kwargs <= {"mask", "other"}
        case "store":
            return len(node.args) == 2 and kwargs <= {"mask"}
        case "arange":
            return len(node.args) == 2 and not kwargs
        case "program_id":
            return _valid_program_id_call(node)
        case "zeros":
            return len(node.args) == 1 and kwargs == {"dtype"}
        case "full":
            return len(node.args) == 2 and kwargs == {"dtype"}
        case "dot":
            return len(node.args) == 2 and kwargs <= {"allow_tf32"}
        case "atomic_add":
            return len(node.args) == 2 and kwargs <= {"mask"}
        case "sum" | "max":
            return len(node.args) == 1 and kwargs == {"axis"}
        case "exp" | "log" | "sqrt":
            return len(node.args) == 1 and not kwargs
        case "where":
            return len(node.args) == 3 and not kwargs
        case _:
            return False


def _valid_program_id_call(node: ast.Call) -> bool:
    if len(node.args) == 1 and not node.keywords:
        return _literal_int(node.args[0]) in {0, 1, 2}
    if not node.args and len(node.keywords) == 1 and node.keywords[0].arg == "axis":
        return _literal_int(node.keywords[0].value) in {0, 1, 2}
    return False


def _is_attr_name(node: ast.AST, base_name: str, attr_name: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attr_name
        and _is_name(node.value, base_name)
    )


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _tl_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and _is_name(node.value, "tl"):
        return node.attr
    return None


if __name__ == "__main__":
    report = validate_grammar_file()
    print(report)
    raise SystemExit(0 if report.lark_compiles and not report.errors else 1)
