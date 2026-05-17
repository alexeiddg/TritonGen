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
TASK_AGNOSTIC_GBNF_PATH = Path(__file__).with_name("triton_kernel_agnostic.gbnf")

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

TASK_AGNOSTIC_ALLOWED_TL_CALLS = frozenset(
    {
        "program_id",
        "num_programs",
        "arange",
        "cat",
        "full",
        "zeros",
        "zeros_like",
        "cast",
        "broadcast",
        "broadcast_to",
        "expand_dims",
        "interleave",
        "join",
        "permute",
        "ravel",
        "reshape",
        "split",
        "trans",
        "view",
        "dot",
        "dot_scaled",
        "load",
        "store",
        "make_tensor_descriptor",
        "load_tensor_descriptor",
        "store_tensor_descriptor",
        "make_block_ptr",
        "advance",
        "flip",
        "where",
        "swizzle2d",
        "abs",
        "cdiv",
        "ceil",
        "clamp",
        "cos",
        "div_rn",
        "erf",
        "exp",
        "exp2",
        "fdiv",
        "floor",
        "fma",
        "log",
        "log2",
        "maximum",
        "minimum",
        "rsqrt",
        "sigmoid",
        "sin",
        "softmax",
        "sqrt",
        "sqrt_rn",
        "umulhi",
        "argmax",
        "argmin",
        "max",
        "min",
        "reduce",
        "sum",
        "xor_sum",
        "associative_scan",
        "cumprod",
        "cumsum",
        "histogram",
        "sort",
        "topk",
        "gather",
        "atomic_add",
        "atomic_and",
        "atomic_cas",
        "atomic_max",
        "atomic_min",
        "atomic_or",
        "atomic_xchg",
        "atomic_xor",
        "randint4x",
        "randint",
        "rand",
        "randn",
        "range",
        "static_range",
        "inline_asm_elementwise",
        "assume",
        "debug_barrier",
        "max_constancy",
        "max_contiguous",
        "multiple_of",
        "static_print",
        "static_assert",
        "device_print",
        "device_assert",
    }
)

TENSOR_DESCRIPTOR_METHOD_CALLS = frozenset(
    {
        "load",
        "store",
        "atomic_add",
        "atomic_and",
        "atomic_max",
        "atomic_min",
        "atomic_or",
        "atomic_xor",
        "gather",
        "scatter",
    }
)

STATEMENT_ONLY_TL_CALLS = frozenset(
    {
        "assume",
        "debug_barrier",
        "device_assert",
        "device_print",
        "static_assert",
        "static_print",
        "store",
        "store_tensor_descriptor",
    }
)

STATEMENT_ONLY_DESCRIPTOR_METHOD_CALLS = frozenset({"store", "scatter"})

TASK_AGNOSTIC_RESERVED_BINDINGS = frozenset({"torch", "triton", "tl", "max", "min", "range"})
BLOCK_META_NAME_RE = re.compile(r"^BLOCK_[A-Za-z0-9_]*$")
TRITON_DTYPE_CHAINS = frozenset(
    {
        ("tl", "float64"),
        ("tl", "float32"),
        ("tl", "float16"),
        ("tl", "bfloat16"),
        ("tl", "int1"),
        ("tl", "int8"),
        ("tl", "int16"),
        ("tl", "int32"),
        ("tl", "int64"),
        ("tl", "uint8"),
        ("tl", "uint16"),
        ("tl", "uint32"),
        ("tl", "uint64"),
        ("tl", "bool"),
    }
)

TORCH_DTYPE_CHAINS = frozenset(
    {
        ("torch", "float64"),
        ("torch", "float32"),
        ("torch", "float16"),
        ("torch", "bfloat16"),
        ("torch", "int8"),
        ("torch", "int16"),
        ("torch", "int32"),
        ("torch", "int64"),
        ("torch", "uint8"),
        ("torch", "bool"),
    }
)

TORCH_TENSOR_METHOD_OBJECT_ATTRIBUTES = frozenset({"data_ptr"})

RELU_ELEMENTWISE_TL_CALLS = frozenset(
    {
        "load",
        "store",
        "arange",
        "program_id",
        "where",
    }
)

SOFTMAX_KERNEL_BODY_STMTS = (
    "row = tl.program_id(axis=0)",
    "offsets = tl.arange(0, BLOCK_SIZE)",
    "mask = offsets < n_cols",
    "x = tl.load(x_ptr + row * n_cols + offsets, mask=mask, other=-1000000000.0)",
    "shifted = x - tl.max(x, axis=0)",
    "numer = tl.exp(shifted)",
    "denom = tl.sum(numer, axis=0)",
    "out = numer / denom",
    "tl.store(out_ptr + row * n_cols + offsets, out, mask=mask)",
)

MATMUL_KERNEL_BODY_STMTS = (
    "pid_m = tl.program_id(axis=0)",
    "pid_n = tl.program_id(axis=1)",
    "offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)",
    "offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)",
    "offs_k = tl.arange(0, BLOCK_K)",
    "acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)",
    """\
for k in range(0, K, BLOCK_K):
    a = tl.load(a_ptr + offs_m[:, None] * K + (k + offs_k)[None, :], mask=(offs_m[:, None] < M) & ((k + offs_k)[None, :] < K), other=0.0)
    b = tl.load(b_ptr + (k + offs_k)[:, None] * N + offs_n[None, :], mask=((k + offs_k)[:, None] < K) & (offs_n[None, :] < N), other=0.0)
    acc += tl.dot(a, b, allow_tf32=True)
""",
    "mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)",
    "tl.store(c_ptr + offs_m[:, None] * N + offs_n[None, :], acc, mask=mask)",
)

CANONICAL_LAUNCHER_PARAMS = {
    "relu": ("x",),
    "softmax": ("x",),
    "matmul": ("a", "b"),
}

CANONICAL_HELPERS = {
    launcher_name: f"_{launcher_name}_kernel"
    for launcher_name in CANONICAL_LAUNCHER_PARAMS
}

CANONICAL_HELPER_PARAMS = {
    "relu": (
        ("x_ptr", None),
        ("out_ptr", None),
        ("n_elements", None),
        ("BLOCK_SIZE", ("tl", "constexpr")),
    ),
    "softmax": (
        ("x_ptr", None),
        ("out_ptr", None),
        ("n_cols", ("tl", "constexpr")),
        ("BLOCK_SIZE", ("tl", "constexpr")),
    ),
    "matmul": (
        ("a_ptr", None),
        ("b_ptr", None),
        ("c_ptr", None),
        ("M", ("tl", "constexpr")),
        ("N", ("tl", "constexpr")),
        ("K", ("tl", "constexpr")),
        ("BLOCK_M", ("tl", "constexpr")),
        ("BLOCK_N", ("tl", "constexpr")),
        ("BLOCK_K", ("tl", "constexpr")),
    ),
}

CANONICAL_LAUNCH_ARGS = {
    "relu": ("x", "out", "n_elements", "BLOCK_SIZE"),
    "softmax": ("x", "out", "n_cols", "BLOCK_SIZE"),
    "matmul": ("a", "b", "c", "M", "N", "K", "BLOCK_M", "BLOCK_N", "BLOCK_K"),
}

DIMENSION_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)
DIMENSION_UNARYOPS = (ast.UAdd, ast.USub)

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
    grammar_path = Path(grammar_path)
    gbnf_text = ""
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
        from cluster1.grammar.acceptance_fixtures import (
            BAD_KERNELS,
            GOOD_KERNELS,
            TASK_AGNOSTIC_BAD_KERNELS,
            TASK_AGNOSTIC_GOOD_KERNELS,
        )

        if _uses_task_agnostic_semantics(grammar_path, gbnf_text):
            n_accept_cases = len(TASK_AGNOSTIC_GOOD_KERNELS)
            n_reject_cases = len(TASK_AGNOSTIC_BAD_KERNELS)
        else:
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
        grammar_path = Path(grammar_path)
        gbnf_text = grammar_path.read_text(encoding="utf-8")
        parser = _compile_lark_parser(gbnf_text)
        parser.parse(source)
        tree = ast.parse(source)
        if _uses_task_agnostic_semantics(grammar_path, gbnf_text):
            return _semantic_accepts_task_agnostic(tree)
        return _semantic_accepts(tree)
    except Exception:
        return False


def _uses_task_agnostic_semantics(grammar_path: Path, gbnf_text: str) -> bool:
    return (
        grammar_path.name == TASK_AGNOSTIC_GBNF_PATH.name
        or "agnostic-module ::=" in gbnf_text
    )


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
    if not _canonical_function_pair(kernel_fn, wrapper_fn):
        return False
    if not _decorators_are_valid(kernel_fn):
        return False
    if not _kernel_contains_program_id(kernel_fn):
        return False
    if not _wrapper_surface_contract_is_valid(wrapper_fn, kernel_fn.name):
        return False

    if not _function_statements_are_valid(kernel_fn, in_kernel=True):
        return False
    if not _function_statements_are_valid(wrapper_fn, in_kernel=False):
        return False
    if wrapper_fn.name == "relu" and not _relu_kernel_body_is_valid(kernel_fn):
        return False
    if wrapper_fn.name == "softmax" and not _softmax_kernel_body_is_valid(kernel_fn):
        return False
    if wrapper_fn.name == "matmul" and not _matmul_kernel_body_is_valid(kernel_fn):
        return False

    return _all_calls_are_valid(
        kernel_fn,
        kernel_fn.name,
        allow_tl_calls=True,
        allow_runtime_calls=False,
        allow_kernel_launch=False,
        allowed_tl_calls=_allowed_kernel_tl_calls(wrapper_fn.name),
    ) and (
        _all_calls_are_valid(
            wrapper_fn,
            kernel_fn.name,
            allow_tl_calls=False,
            allow_runtime_calls=True,
            allow_kernel_launch=True,
        )
    )


def _semantic_accepts_task_agnostic(tree: ast.Module) -> bool:
    if not _imports_are_valid(tree):
        return False

    module_body = tree.body[3:]
    if len(module_body) < 2:
        return False
    if not all(isinstance(node, ast.FunctionDef) for node in module_body):
        return False

    helper_fns = [node for node in module_body[:-1] if isinstance(node, ast.FunctionDef)]
    wrapper_fn = module_body[-1]
    if not isinstance(wrapper_fn, ast.FunctionDef) or not helper_fns:
        return False
    if not _agnostic_wrapper_signature_is_valid(wrapper_fn):
        return False

    helper_names: set[str] = set()
    helper_by_name: dict[str, ast.FunctionDef] = {}
    for helper_fn in helper_fns:
        if not _agnostic_helper_signature_is_valid(helper_fn):
            return False
        if helper_fn.name in helper_names:
            return False
        helper_names.add(helper_fn.name)
        helper_by_name[helper_fn.name] = helper_fn

    helper_name_set = frozenset(helper_names)
    reserved_bindings = TASK_AGNOSTIC_RESERVED_BINDINGS | helper_name_set
    if wrapper_fn.name in reserved_bindings:
        return False
    if not _agnostic_wrapper_surface_contract_is_valid(wrapper_fn, helper_by_name):
        return False
    launched_helper = _launched_agnostic_helper_name(wrapper_fn, helper_name_set)
    if launched_helper is None:
        return False

    for helper_fn in helper_fns:
        if not _function_does_not_bind_reserved_names(helper_fn, reserved_bindings):
            return False
        if not _decorators_are_valid(helper_fn):
            return False
        if helper_fn.name == launched_helper and not _kernel_contains_program_id(helper_fn):
            return False
        if not _function_statements_are_valid(
            helper_fn,
            in_kernel=True,
            allow_return=True,
        ):
            return False
        if not _statement_only_tl_calls_are_valid(helper_fn):
            return False
        if not _all_calls_are_valid(
            helper_fn,
            helper_name_set,
            allow_tl_calls=True,
            allow_runtime_calls=False,
            allow_kernel_launch=False,
            allowed_tl_calls=TASK_AGNOSTIC_ALLOWED_TL_CALLS,
        ):
            return False

    if wrapper_fn.name in helper_name_set:
        return False
    if not _function_does_not_bind_reserved_names(wrapper_fn, reserved_bindings):
        return False
    if not _function_statements_are_valid(wrapper_fn, in_kernel=False):
        return False
    if not _all_calls_are_valid(
        wrapper_fn,
        helper_name_set,
        allow_tl_calls=False,
        allow_runtime_calls=True,
        allow_kernel_launch=True,
    ):
        return False
    return _int_literals_are_hardware_safe(tree)


def _agnostic_helper_signature_is_valid(kernel_fn: ast.FunctionDef) -> bool:
    if kernel_fn.name in TASK_AGNOSTIC_RESERVED_BINDINGS:
        return False
    if kernel_fn.args.posonlyargs or kernel_fn.args.kwonlyargs:
        return False
    if kernel_fn.args.vararg is not None or kernel_fn.args.kwarg is not None:
        return False
    if kernel_fn.args.defaults or kernel_fn.args.kw_defaults:
        return False
    if not kernel_fn.args.args:
        return False
    if kernel_fn.returns is not None:
        return False

    for arg in kernel_fn.args.args:
        if arg.annotation is None:
            continue
        if _is_block_meta_name(arg.arg) and _attribute_chain(arg.annotation) != [
            "tl",
            "constexpr",
        ]:
            return False
    return True


def _agnostic_wrapper_signature_is_valid(wrapper_fn: ast.FunctionDef) -> bool:
    if wrapper_fn.name.startswith("_"):
        return False
    if wrapper_fn.args.posonlyargs or wrapper_fn.args.kwonlyargs:
        return False
    if wrapper_fn.args.vararg is not None or wrapper_fn.args.kwarg is not None:
        return False
    if wrapper_fn.args.defaults or wrapper_fn.args.kw_defaults:
        return False
    if not wrapper_fn.args.args:
        return False
    if not all(_annotation_is_wrapper_param(arg.annotation) for arg in wrapper_fn.args.args):
        return False
    return _annotation_is_torch_tensor(wrapper_fn.returns)


def _agnostic_wrapper_surface_contract_is_valid(
    wrapper_fn: ast.FunctionDef,
    helper_by_name: dict[str, ast.FunctionDef],
) -> bool:
    helper_names = frozenset(helper_by_name)
    launch_stmt = _find_agnostic_grid_launch_stmt(wrapper_fn, helper_names)
    if launch_stmt is None:
        return False
    launch_index, launch = launch_stmt

    if not _agnostic_wrapper_names_are_defined(wrapper_fn, helper_names):
        return False
    if not _agnostic_wrapper_attributes_are_valid(wrapper_fn):
        return False
    if not _wrapper_runtime_allocations_are_valid(wrapper_fn):
        return False
    if not _launch_uses_valid_grid(launch, wrapper_fn, launch_index):
        return False
    if not _agnostic_block_meta_surface_is_valid(
        wrapper_fn,
        helper_by_name,
        launch,
        launch_index,
    ):
        return False

    return_info = _single_returned_name_after_launch(wrapper_fn, launch_index)
    if return_info is None:
        return False
    return True


def _find_agnostic_grid_launch_stmt(
    wrapper_fn: ast.FunctionDef,
    helper_names: frozenset[str],
) -> tuple[int, ast.Call] | None:
    matches: list[tuple[int, ast.Call]] = []
    for index, stmt in enumerate(wrapper_fn.body):
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        func = stmt.value.func
        if (
            isinstance(func, ast.Subscript)
            and isinstance(func.value, ast.Name)
            and func.value.id in helper_names
        ):
            matches.append((index, stmt.value))
    if len(matches) != 1:
        return None
    return matches[0]


def _launched_agnostic_helper_name(
    wrapper_fn: ast.FunctionDef,
    helper_names: frozenset[str],
) -> str | None:
    launch_stmt = _find_agnostic_grid_launch_stmt(wrapper_fn, helper_names)
    if launch_stmt is None:
        return None
    _, launch = launch_stmt
    if not isinstance(launch.func, ast.Subscript):
        return None
    if not isinstance(launch.func.value, ast.Name):
        return None
    helper_name = launch.func.value.id
    return helper_name if helper_name in helper_names else None


def _agnostic_block_meta_surface_is_valid(
    wrapper_fn: ast.FunctionDef,
    helper_by_name: dict[str, ast.FunctionDef],
    launch: ast.Call,
    launch_index: int,
) -> bool:
    for helper_fn in helper_by_name.values():
        if not _helper_block_meta_refs_are_constexpr_params(helper_fn):
            return False

    if not isinstance(launch.func, ast.Subscript):
        return False
    if not isinstance(launch.func.value, ast.Name):
        return False

    launched_helper = helper_by_name.get(launch.func.value.id)
    if launched_helper is None:
        return False
    return _launch_binds_block_meta_params(
        launch,
        launched_helper,
        wrapper_fn,
        launch_index,
    )


def _helper_block_meta_refs_are_constexpr_params(helper_fn: ast.FunctionDef) -> bool:
    refs = _block_meta_refs_in_statements(helper_fn.body)
    if not refs:
        return True
    return refs <= _block_meta_constexpr_params(helper_fn)


def _block_meta_constexpr_params(function: ast.FunctionDef) -> set[str]:
    return {
        arg.arg
        for arg in function.args.args
        if _is_block_meta_name(arg.arg)
        and _attribute_chain(arg.annotation) == ["tl", "constexpr"]
    }


def _block_meta_refs_in_statements(statements: list[ast.stmt]) -> set[str]:
    refs: set[str] = set()
    for stmt in statements:
        refs.update(
            child.id
            for child in ast.walk(stmt)
            if isinstance(child, ast.Name)
            and isinstance(child.ctx, ast.Load)
            and _is_block_meta_name(child.id)
        )
    return refs


def _launch_binds_block_meta_params(
    launch: ast.Call,
    helper_fn: ast.FunctionDef,
    wrapper_fn: ast.FunctionDef,
    launch_index: int,
) -> bool:
    keyword_names = [keyword.arg for keyword in launch.keywords]
    if any(name is None for name in keyword_names):
        return False

    keywords = {
        keyword.arg: keyword.value
        for keyword in launch.keywords
        if keyword.arg is not None
    }
    if len(keywords) != len(keyword_names):
        return False

    helper_param_names = {arg.arg for arg in helper_fn.args.args}
    if any(
        _is_block_meta_name(name) and name not in helper_param_names
        for name in keywords
    ):
        return False

    for index, arg in enumerate(helper_fn.args.args):
        if not _is_block_meta_name(arg.arg):
            continue
        if arg.arg in keywords:
            if index < len(launch.args):
                return False
            if not _launch_meta_binding_expr_is_defined(
                wrapper_fn,
                keywords[arg.arg],
                before_index=launch_index,
            ):
                return False
            continue
        if index >= len(launch.args):
            return False
        if not _launch_meta_binding_expr_is_defined(
            wrapper_fn,
            launch.args[index],
            before_index=launch_index,
        ):
            return False
    return True


def _launch_meta_binding_expr_is_defined(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    return _referenced_names(expression) <= _defined_wrapper_names_before(
        wrapper_fn,
        before_index=before_index,
    )


def _is_block_meta_name(name: str) -> bool:
    return BLOCK_META_NAME_RE.fullmatch(name) is not None


def _function_does_not_bind_reserved_names(
    function: ast.FunctionDef,
    reserved_names: frozenset[str],
) -> bool:
    for arg in function.args.args:
        if arg.arg in reserved_names:
            return False
    for stmt in ast.walk(function):
        if isinstance(stmt, ast.Assign):
            if _target_root_names(stmt.targets) & reserved_names:
                return False
            continue
        if isinstance(stmt, ast.AugAssign):
            if _target_root_names([stmt.target]) & reserved_names:
                return False
            continue
        if isinstance(stmt, ast.For):
            if _target_root_names([stmt.target]) & reserved_names:
                return False
    return True


def _single_returned_name_after_launch(
    wrapper_fn: ast.FunctionDef,
    launch_index: int,
) -> tuple[int, str] | None:
    return_stmts = [
        (index, stmt)
        for index, stmt in enumerate(wrapper_fn.body)
        if isinstance(stmt, ast.Return)
    ]
    if len(return_stmts) != 1:
        return None
    return_index, stmt = return_stmts[0]
    if return_index <= launch_index or return_index != len(wrapper_fn.body) - 1:
        return None
    if not isinstance(stmt.value, ast.Name):
        return None
    return return_index, stmt.value.id


def _agnostic_wrapper_names_are_defined(
    wrapper_fn: ast.FunctionDef,
    helper_names: frozenset[str],
) -> bool:
    defined_names = _initial_wrapper_names(wrapper_fn) | set(helper_names)
    for stmt in wrapper_fn.body:
        if isinstance(stmt, ast.Assign):
            if not _assignment_target_names(stmt.targets) <= defined_names:
                return False
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            defined_names.update(_assigned_names(stmt.targets))
            continue
        if isinstance(stmt, ast.AugAssign):
            target_names = _target_root_names([stmt.target]) | _referenced_names(stmt.target)
            if not target_names <= defined_names:
                return False
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
        if isinstance(stmt, ast.Expr):
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
        if isinstance(stmt, ast.Assert):
            refs = _referenced_names(stmt.test)
            if stmt.msg is not None:
                refs |= _referenced_names(stmt.msg)
            if not refs <= defined_names:
                return False
            continue
        if isinstance(stmt, ast.Return):
            if stmt.value is not None and not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
    return True


def _agnostic_wrapper_attributes_are_valid(wrapper_fn: ast.FunctionDef) -> bool:
    for index, stmt in enumerate(wrapper_fn.body):
        parents = _node_parent_map(stmt)
        for node in ast.walk(stmt):
            if isinstance(node, ast.Subscript) and not _wrapper_subscript_ref_is_valid(
                wrapper_fn,
                node,
                before_index=index,
            ):
                return False
            if not isinstance(node, ast.Attribute):
                continue
            if not _wrapper_attribute_ref_is_valid(
                wrapper_fn,
                node,
                parents,
                before_index=index,
            ):
                return False
    return True


def _wrapper_attribute_ref_is_valid(
    wrapper_fn: ast.FunctionDef,
    node: ast.Attribute,
    parents: dict[ast.AST, ast.AST],
    *,
    before_index: int,
) -> bool:
    if _attribute_is_direct_call_func(node, parents):
        return (
            _is_attr_name(node, "torch", "empty")
            or _is_attr_name(node, "torch", "empty_like")
            or _is_attr_name(node, "triton", "cdiv")
            or (
                node.attr == "numel"
                and (
                    _expression_is_tensor_like(
                        wrapper_fn,
                        node.value,
                        before_index=before_index,
                    )
                    or _expression_is_shape_like(
                        wrapper_fn,
                        node.value,
                        before_index=before_index,
                    )
                )
            )
        )
    if tuple(_attribute_chain(node)) in TORCH_DTYPE_CHAINS:
        return _wrapper_terminal_attribute_parent_is_valid(node, parents)
    if node.attr in {"device", "dtype"}:
        return _wrapper_terminal_attribute_parent_is_valid(
            node,
            parents,
        ) and _expression_is_tensor_like(wrapper_fn, node.value, before_index=before_index)
    if node.attr == "shape":
        parent = parents.get(node)
        return (
            (
                isinstance(parent, ast.Subscript)
                and parent.value is node
                and _wrapper_shape_subscript_is_valid(
                    wrapper_fn,
                    parent,
                    before_index=before_index,
                )
            )
            or (
                _wrapper_terminal_attribute_parent_is_valid(node, parents)
                and _expression_is_tensor_like(
                    wrapper_fn,
                    node.value,
                    before_index=before_index,
                )
            )
        )
    if node.attr == "is_cuda":
        return _wrapper_terminal_attribute_parent_is_valid(
            node,
            parents,
        ) and _expression_is_tensor_like(wrapper_fn, node.value, before_index=before_index)
    if node.attr in TORCH_TENSOR_METHOD_OBJECT_ATTRIBUTES:
        return _wrapper_terminal_attribute_parent_is_valid(
            node,
            parents,
        ) and _expression_is_tensor_like(wrapper_fn, node.value, before_index=before_index)
    return False


def _wrapper_subscript_ref_is_valid(
    wrapper_fn: ast.FunctionDef,
    node: ast.Subscript,
    *,
    before_index: int,
) -> bool:
    if isinstance(node.value, ast.Attribute):
        if node.value.attr == "shape":
            return _wrapper_shape_subscript_is_valid(
                wrapper_fn,
                node,
                before_index=before_index,
            )
        if node.value.attr in {"device", "dtype"}:
            return False
        if tuple(_attribute_chain(node.value)) in TORCH_DTYPE_CHAINS:
            return False
    if (
        isinstance(node.value, ast.Subscript)
        and isinstance(node.value.value, ast.Attribute)
        and node.value.value.attr == "shape"
    ):
        return False
    return True


def _wrapper_shape_subscript_is_valid(
    wrapper_fn: ast.FunctionDef,
    node: ast.Subscript,
    *,
    before_index: int,
) -> bool:
    return _expression_is_shape_subscript(wrapper_fn, node, before_index=before_index)


def _wrapper_terminal_attribute_parent_is_valid(
    node: ast.Attribute,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    return not (
        isinstance(parent, ast.Subscript)
        and parent.value is node
        or isinstance(parent, ast.Attribute)
        and parent.value is node
        or isinstance(parent, ast.Call)
        and parent.func is node
    )


def _attribute_is_direct_call_func(
    node: ast.Attribute,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    return isinstance(parent, ast.Call) and parent.func is node


def _int_literals_are_hardware_safe(tree: ast.Module) -> bool:
    return True


def _allowed_kernel_tl_calls(launcher_name: str) -> frozenset[str]:
    if launcher_name == "relu":
        return RELU_ELEMENTWISE_TL_CALLS
    return ALLOWED_TL_CALLS


def _relu_kernel_body_is_valid(kernel_fn: ast.FunctionDef) -> bool:
    store_calls: list[tuple[int, ast.Call]] = []
    for index, stmt in enumerate(kernel_fn.body):
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        if _tl_call_name(stmt.value.func) == "store":
            store_calls.append((index, stmt.value))

    if len(store_calls) != 1:
        return False

    store_index, store_call = store_calls[0]
    if len(store_call.args) < 2:
        return False
    return _relu_store_value_is_valid(
        store_call.args[1],
        kernel_fn,
        before_index=store_index,
    )


def _relu_store_value_is_valid(
    value: ast.AST,
    kernel_fn: ast.FunctionDef,
    *,
    before_index: int,
) -> bool:
    if _is_relu_where_call(value):
        return True
    if not isinstance(value, ast.Name):
        return False

    binding = _latest_kernel_name_binding_before(
        kernel_fn,
        value.id,
        before_index=before_index,
    )
    return binding is not None and _is_relu_where_call(binding)


def _softmax_kernel_body_is_valid(kernel_fn: ast.FunctionDef) -> bool:
    return _function_body_matches(kernel_fn, SOFTMAX_KERNEL_BODY_STMTS)


def _matmul_kernel_body_is_valid(kernel_fn: ast.FunctionDef) -> bool:
    return _function_body_matches(kernel_fn, MATMUL_KERNEL_BODY_STMTS)


def _function_body_matches(
    function: ast.FunctionDef,
    expected_statements: tuple[str, ...],
) -> bool:
    if len(function.body) != len(expected_statements):
        return False
    return all(
        _ast_nodes_match(observed, _parse_single_stmt(expected))
        for observed, expected in zip(function.body, expected_statements, strict=True)
    )


@lru_cache(maxsize=32)
def _parse_single_stmt(source: str) -> ast.stmt:
    module = ast.parse(source)
    if len(module.body) != 1:
        raise ValueError(f"expected one statement: {source!r}")
    return module.body[0]


def _ast_nodes_match(left: ast.AST, right: ast.AST) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(
        right,
        include_attributes=False,
    )


def _latest_kernel_name_binding_before(
    kernel_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> ast.AST | None:
    latest: ast.AST | None = None
    for stmt in kernel_fn.body[:before_index]:
        if not isinstance(stmt, ast.Assign):
            continue
        if any(_target_is_name(target, name) for target in stmt.targets):
            latest = stmt.value
    return latest


def _is_relu_where_call(value: ast.AST) -> bool:
    if not isinstance(value, ast.Call):
        return False
    if _tl_call_name(value.func) != "where":
        return False
    if len(value.args) != 3 or value.keywords:
        return False

    condition, true_value, false_value = value.args
    return (
        _is_relu_positive_condition(condition)
        and _is_name(true_value, "x")
        and _literal_zero(false_value)
    )


def _is_relu_positive_condition(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Compare)
        and _is_name(value.left, "x")
        and len(value.ops) == 1
        and isinstance(value.ops[0], ast.Gt)
        and len(value.comparators) == 1
        and _literal_zero(value.comparators[0])
    )


def _literal_zero(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Constant)
        and not isinstance(value.value, bool)
        and value.value == 0
    )


def _imports_are_valid(tree: ast.Module) -> bool:
    if len(tree.body) < 3:
        return False
    required = [
        [("torch", None)],
        [("triton", None)],
        [("triton.language", "tl")],
    ]
    for node, expected in zip(tree.body[:3], required, strict=True):
        if not isinstance(node, ast.Import):
            return False
        imports = [(alias.name, alias.asname) for alias in node.names]
        if imports != expected:
            return False

    for node in tree.body[3:]:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False
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


def _canonical_function_pair(
    kernel_fn: ast.FunctionDef,
    wrapper_fn: ast.FunctionDef,
) -> bool:
    expected_helper = CANONICAL_HELPERS.get(wrapper_fn.name)
    if expected_helper is None or kernel_fn.name != expected_helper:
        return False
    if not kernel_fn.name.startswith("_") or not kernel_fn.name.endswith("_kernel"):
        return False
    return _wrapper_signature_is_exact(wrapper_fn) and _helper_signature_is_exact(
        kernel_fn,
        wrapper_fn.name,
    )


def _wrapper_signature_is_exact(wrapper_fn: ast.FunctionDef) -> bool:
    expected_params = CANONICAL_LAUNCHER_PARAMS.get(wrapper_fn.name)
    if expected_params is None:
        return False
    if wrapper_fn.args.posonlyargs or wrapper_fn.args.kwonlyargs:
        return False
    if wrapper_fn.args.vararg is not None or wrapper_fn.args.kwarg is not None:
        return False
    if tuple(arg.arg for arg in wrapper_fn.args.args) != expected_params:
        return False
    if not all(_annotation_is_torch_tensor(arg.annotation) for arg in wrapper_fn.args.args):
        return False
    return _annotation_is_torch_tensor(wrapper_fn.returns)


def _helper_signature_is_exact(
    kernel_fn: ast.FunctionDef,
    launcher_name: str,
) -> bool:
    expected_params = CANONICAL_HELPER_PARAMS.get(launcher_name)
    if expected_params is None:
        return False
    if kernel_fn.args.posonlyargs or kernel_fn.args.kwonlyargs:
        return False
    if kernel_fn.args.vararg is not None or kernel_fn.args.kwarg is not None:
        return False
    if kernel_fn.args.defaults or kernel_fn.args.kw_defaults:
        return False
    if len(kernel_fn.args.args) != len(expected_params):
        return False

    for arg, (expected_name, expected_annotation) in zip(
        kernel_fn.args.args,
        expected_params,
        strict=True,
    ):
        if arg.arg != expected_name:
            return False
        if expected_annotation is None:
            if arg.annotation is not None:
                return False
            continue
        if tuple(_attribute_chain(arg.annotation)) != expected_annotation:
            return False

    return kernel_fn.returns is None


def _annotation_is_torch_tensor(node: ast.AST | None) -> bool:
    return _attribute_chain(node) == ["torch", "Tensor"]


def _annotation_is_wrapper_param(node: ast.AST | None) -> bool:
    return _annotation_is_torch_tensor(node) or _attribute_chain(node) in [
        ["int"],
        ["float"],
        ["bool"],
    ]


def _wrapper_param_annotation(
    wrapper_fn: ast.FunctionDef,
    name: str,
) -> list[str] | None:
    for arg in wrapper_fn.args.args:
        if arg.arg == name:
            return _attribute_chain(arg.annotation)
    return None


def _attribute_chain(node: ast.AST | None) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_attribute_chain(node.value), node.attr]
    return []


def _decorators_are_valid(kernel_fn: ast.FunctionDef) -> bool:
    decorators = kernel_fn.decorator_list
    if not decorators or not _is_attr_name(decorators[-1], "triton", "jit"):
        return False

    seen_autotune = False
    seen_heuristics = False
    for decorator in decorators[:-1]:
        if _is_autotune_decorator(decorator):
            if seen_autotune:
                return False
            seen_autotune = True
            continue
        if _is_heuristics_decorator(decorator):
            if seen_heuristics:
                return False
            seen_heuristics = True
            continue
        return False
    return True


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


def _is_heuristics_decorator(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not _is_attr_name(node.func, "triton", "heuristics"):
        return False

    if node.args:
        if len(node.args) != 1 or node.keywords:
            return False
        values = node.args[0]
    else:
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
        if set(kwargs) != {"values"}:
            return False
        values = kwargs["values"]

    if not isinstance(values, ast.Dict):
        return False
    for key, value in zip(values.keys, values.values, strict=True):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return False
        if not _is_heuristic_lambda(value):
            return False
    return True


def _is_heuristic_lambda(node: ast.AST) -> bool:
    if not isinstance(node, ast.Lambda):
        return False
    if len(node.args.args) != 1 or node.args.args[0].arg != "args":
        return False
    body = node.body
    if isinstance(body, ast.Constant) and isinstance(body.value, (bool, int)):
        return True
    if isinstance(body, ast.Call) and _is_attr_name(body.func, "triton", "next_power_of_2"):
        return len(body.args) == 1 and not body.keywords and _is_args_string_subscript(
            body.args[0]
        )
    return False


def _is_args_string_subscript(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and _is_name(node.value, "args")
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    )


def _is_fixed_config(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not _is_attr_name(node.func, "triton", "Config"):
        return False

    keywords: dict[str, ast.AST] = {}
    for keyword in node.keywords:
        if keyword.arg is None or keyword.arg in keywords:
            return False
        keywords[keyword.arg] = keyword.value

    if len(node.args) == 1:
        if "kwargs" in keywords:
            return False
        config_node = node.args[0]
    elif not node.args and "kwargs" in keywords:
        config_node = keywords.pop("kwargs")
    else:
        return False

    if not isinstance(config_node, ast.Dict):
        return False

    config = _literal_dict(config_node)
    if config is None:
        return False
    if not config or not all(key.startswith("BLOCK_") and value > 0 for key, value in config.items()):
        return False

    config_kwargs = {name: _literal_int(value) for name, value in keywords.items()}
    if set(config_kwargs) != {"num_warps", "num_stages"}:
        return False
    return all(value is not None and value > 0 for value in config_kwargs.values())


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
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return node.value
    return None


def _kernel_contains_program_id(kernel_fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call) and _tl_call_name(node.func) == "program_id"
        for node in ast.walk(kernel_fn)
    )


def _is_grid_launch(node: ast.AST, kernel_name: str) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Subscript) and _is_name(func.value, kernel_name):
        return True
    return False


def _wrapper_surface_contract_is_valid(
    wrapper_fn: ast.FunctionDef,
    kernel_name: str,
) -> bool:
    launch_stmt = _find_grid_launch_stmt(wrapper_fn, kernel_name)
    if launch_stmt is None:
        return False
    launch_index, launch = launch_stmt
    if not _wrapper_names_are_defined(wrapper_fn, kernel_name):
        return False
    if not _wrapper_runtime_allocations_are_valid(wrapper_fn):
        return False
    if not _launch_uses_valid_grid(launch, wrapper_fn, launch_index):
        return False
    if not _launch_args_are_exact(launch, wrapper_fn.name):
        return False

    returned_name = _returned_name(wrapper_fn)
    if returned_name is None:
        return False
    if returned_name not in _launch_argument_names(launch):
        return False
    return _latest_binding_is_allocated_output(
        wrapper_fn,
        returned_name,
        before_index=launch_index,
    )


def _find_grid_launch_stmt(
    wrapper_fn: ast.FunctionDef,
    kernel_name: str,
) -> tuple[int, ast.Call] | None:
    matches: list[tuple[int, ast.Call]] = []
    for index, stmt in enumerate(wrapper_fn.body):
        if isinstance(stmt, ast.Expr) and _is_grid_launch(stmt.value, kernel_name):
            matches.append((index, stmt.value))
    if len(matches) != 1:
        return None
    return matches[0]


def _launch_uses_valid_grid(
    launch: ast.Call,
    wrapper_fn: ast.FunctionDef,
    launch_index: int,
) -> bool:
    func = launch.func
    if not isinstance(func, ast.Subscript):
        return False

    grid_expr = func.slice
    return (
        isinstance(grid_expr, ast.Name)
        and grid_expr.id == "grid"
        and _latest_binding_is_grid_tuple(
            wrapper_fn,
            before_index=launch_index,
        )
    )


def _launch_args_are_exact(launch: ast.Call, launcher_name: str) -> bool:
    expected_args = CANONICAL_LAUNCH_ARGS.get(launcher_name)
    if expected_args is None or launch.keywords:
        return False
    return (
        len(launch.args) == len(expected_args)
        and all(isinstance(arg, ast.Name) for arg in launch.args)
        and tuple(arg.id for arg in launch.args if isinstance(arg, ast.Name)) == expected_args
    )


def _latest_binding_is_allocated_output(
    wrapper_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> bool:
    binding = _latest_binding_before(wrapper_fn, name, before_index=before_index)
    if binding is None:
        return False
    binding_index, value = binding
    if not isinstance(value, ast.Call):
        return False
    if not _expression_names_are_defined(wrapper_fn, value, before_index=binding_index):
        return False
    if _is_attr_name(value.func, "torch", "empty_like"):
        return _call_is_valid_empty_like_allocation(
            wrapper_fn,
            value,
            before_index=binding_index,
        )
    if _is_attr_name(value.func, "torch", "empty"):
        return _call_is_valid_empty_allocation(
            wrapper_fn,
            value,
            before_index=binding_index,
        )
    return False


def _wrapper_runtime_allocations_are_valid(wrapper_fn: ast.FunctionDef) -> bool:
    for index, stmt in enumerate(wrapper_fn.body):
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            if _is_attr_name(node.func, "torch", "empty_like"):
                if not _call_is_valid_empty_like_allocation(
                    wrapper_fn,
                    node,
                    before_index=index,
                ):
                    return False
                continue
            if _is_attr_name(
                node.func,
                "torch",
                "empty",
            ) and not _call_is_valid_empty_allocation(
                wrapper_fn,
                node,
                before_index=index,
            ):
                return False
    return True


def _call_is_valid_empty_like_allocation(
    wrapper_fn: ast.FunctionDef,
    call: ast.Call,
    *,
    before_index: int,
) -> bool:
    return (
        len(call.args) == 1
        and not call.keywords
        and _expression_is_tensor_like(wrapper_fn, call.args[0], before_index=before_index)
    )


def _call_is_valid_empty_allocation(
    wrapper_fn: ast.FunctionDef,
    call: ast.Call,
    *,
    before_index: int,
) -> bool:
    kwargs: dict[str, ast.AST] = {}
    for keyword in call.keywords:
        if keyword.arg is None or keyword.arg in kwargs:
            return False
        kwargs[keyword.arg] = keyword.value

    return (
        len(call.args) == 1
        and set(kwargs) == {"device", "dtype"}
        and _expression_is_dimension_shape(wrapper_fn, call.args[0], before_index=before_index)
        and _expression_is_tensor_attribute(
            wrapper_fn,
            kwargs["device"],
            "device",
            before_index=before_index,
        )
        and _expression_is_tensor_dtype(
            wrapper_fn,
            kwargs["dtype"],
            before_index=before_index,
        )
    )


def _latest_binding_is_grid_tuple(
    wrapper_fn: ast.FunctionDef,
    *,
    before_index: int,
) -> bool:
    binding = _latest_binding_before(wrapper_fn, "grid", before_index=before_index)
    if binding is None:
        return False
    binding_index, value = binding
    return (
        isinstance(value, ast.Tuple)
        and bool(value.elts)
        and _expression_names_are_defined(wrapper_fn, value, before_index=binding_index)
        and all(
            _expression_is_dimension_like(wrapper_fn, element, before_index=binding_index)
            for element in value.elts
        )
    )


def _latest_binding_before(
    wrapper_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> tuple[int, ast.AST] | None:
    latest: tuple[int, ast.AST] | None = None
    for index, stmt in enumerate(wrapper_fn.body[:before_index]):
        if isinstance(stmt, ast.Assign) and name in _assigned_names(stmt.targets):
            latest = (index, stmt.value)
        elif isinstance(stmt, ast.AugAssign) and _target_is_name(stmt.target, name):
            latest = (index, stmt)
    return latest


def _expression_names_are_defined(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    defined_names = _defined_wrapper_names_before(wrapper_fn, before_index=before_index)
    return _referenced_names(expression) <= defined_names


def _wrapper_names_are_defined(wrapper_fn: ast.FunctionDef, kernel_name: str) -> bool:
    defined_names = _initial_wrapper_names(wrapper_fn) | {kernel_name}
    for stmt in wrapper_fn.body:
        if isinstance(stmt, ast.Assign):
            if not _assignment_target_names(stmt.targets) <= defined_names:
                return False
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            defined_names.update(_assigned_names(stmt.targets))
            continue
        if isinstance(stmt, ast.AugAssign):
            if not _referenced_names(stmt.target) <= defined_names:
                return False
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
        if isinstance(stmt, ast.Expr):
            if not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
        if isinstance(stmt, ast.Return):
            if stmt.value is not None and not _referenced_names(stmt.value) <= defined_names:
                return False
            continue
    return True


def _defined_wrapper_names_before(
    wrapper_fn: ast.FunctionDef,
    *,
    before_index: int,
) -> set[str]:
    names = _initial_wrapper_names(wrapper_fn)
    for stmt in wrapper_fn.body[:before_index]:
        if isinstance(stmt, ast.Assign):
            names.update(_assigned_names(stmt.targets))
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            if stmt.target.id in names:
                names.add(stmt.target.id)
    return names


def _expression_is_tensor_like(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    return isinstance(expression, ast.Name) and _name_is_tensor_like(
        wrapper_fn,
        expression.id,
        before_index=before_index,
    )


def _expression_is_shape_like(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    return isinstance(expression, ast.Name) and _name_is_shape_like(
        wrapper_fn,
        expression.id,
        before_index=before_index,
    )


def _name_is_shape_like(
    wrapper_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> bool:
    binding = _latest_binding_before(wrapper_fn, name, before_index=before_index)
    if binding is None:
        return False
    binding_index, value = binding
    return _expression_is_tensor_attribute(
        wrapper_fn,
        value,
        "shape",
        before_index=binding_index,
    )


def _name_is_tensor_like(
    wrapper_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> bool:
    if name in _wrapper_parameter_names(wrapper_fn):
        return _wrapper_param_annotation(wrapper_fn, name) == ["torch", "Tensor"]
    binding = _latest_binding_before(wrapper_fn, name, before_index=before_index)
    if binding is None:
        return False
    binding_index, value = binding
    if isinstance(value, ast.Call) and _is_attr_name(value.func, "torch", "empty_like"):
        return _call_is_valid_empty_like_allocation(
            wrapper_fn,
            value,
            before_index=binding_index,
        )
    if isinstance(value, ast.Call) and _is_attr_name(value.func, "torch", "empty"):
        return _call_is_valid_empty_allocation(
            wrapper_fn,
            value,
            before_index=binding_index,
        )
    return False


def _expression_is_dimension_shape(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    if isinstance(expression, ast.Tuple):
        return bool(expression.elts) and all(
            _expression_is_dimension_like(wrapper_fn, element, before_index=before_index)
            for element in expression.elts
        )
    return _expression_is_dimension_like(wrapper_fn, expression, before_index=before_index)


def _expression_is_tensor_attribute(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    attr_name: str,
    *,
    before_index: int,
) -> bool:
    return (
        isinstance(expression, ast.Attribute)
        and expression.attr == attr_name
        and _expression_is_tensor_like(
            wrapper_fn,
            expression.value,
            before_index=before_index,
        )
    )


def _expression_is_tensor_dtype(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    return _expression_is_tensor_attribute(
        wrapper_fn,
        expression,
        "dtype",
        before_index=before_index,
    ) or tuple(_attribute_chain(expression)) in TORCH_DTYPE_CHAINS


def _expression_is_dimension_like(
    wrapper_fn: ast.FunctionDef,
    expression: ast.AST,
    *,
    before_index: int,
) -> bool:
    if isinstance(expression, ast.Constant):
        return isinstance(expression.value, int) and not isinstance(expression.value, bool)
    if isinstance(expression, ast.Name):
        return _name_is_dimension_like(wrapper_fn, expression.id, before_index=before_index)
    if isinstance(expression, ast.BinOp):
        return isinstance(expression.op, DIMENSION_BINOPS) and _expression_is_dimension_like(
            wrapper_fn,
            expression.left,
            before_index=before_index,
        ) and _expression_is_dimension_like(
            wrapper_fn,
            expression.right,
            before_index=before_index,
        )
    if isinstance(expression, ast.UnaryOp):
        return isinstance(expression.op, DIMENSION_UNARYOPS) and _expression_is_dimension_like(
            wrapper_fn,
            expression.operand,
            before_index=before_index,
        )
    if isinstance(expression, ast.Subscript):
        return _expression_is_shape_subscript(wrapper_fn, expression, before_index=before_index)
    if isinstance(expression, ast.Call):
        return _call_is_dimension_like(wrapper_fn, expression, before_index=before_index)
    return False


def _name_is_dimension_like(
    wrapper_fn: ast.FunctionDef,
    name: str,
    *,
    before_index: int,
) -> bool:
    if name in _wrapper_parameter_names(wrapper_fn):
        return _wrapper_param_annotation(wrapper_fn, name) == ["int"]
    binding = _latest_binding_before(wrapper_fn, name, before_index=before_index)
    if binding is None:
        return False
    binding_index, value = binding
    return _expression_is_dimension_like(wrapper_fn, value, before_index=binding_index)


def _expression_is_shape_subscript(
    wrapper_fn: ast.FunctionDef,
    expression: ast.Subscript,
    *,
    before_index: int,
) -> bool:
    return (
        isinstance(expression.value, ast.Attribute)
        and expression.value.attr == "shape"
        and _expression_is_tensor_like(
            wrapper_fn,
            expression.value.value,
            before_index=before_index,
        )
        and isinstance(expression.slice, ast.Constant)
        and isinstance(expression.slice.value, int)
        and not isinstance(expression.slice.value, bool)
    )


def _call_is_dimension_like(
    wrapper_fn: ast.FunctionDef,
    call: ast.Call,
    *,
    before_index: int,
) -> bool:
    if _is_attr_name(call.func, "triton", "cdiv"):
        return len(call.args) == 2 and not call.keywords and all(
            _expression_is_dimension_like(wrapper_fn, arg, before_index=before_index)
            for arg in call.args
        )
    if isinstance(call.func, ast.Attribute) and call.func.attr == "numel":
        return (
            not call.args
            and not call.keywords
            and (
                _expression_is_tensor_like(
                    wrapper_fn,
                    call.func.value,
                    before_index=before_index,
                )
                or _expression_is_shape_like(
                    wrapper_fn,
                    call.func.value,
                    before_index=before_index,
                )
            )
        )
    if isinstance(call.func, ast.Name) and call.func.id in {"max", "min"}:
        return len(call.args) == 2 and not call.keywords and all(
            _expression_is_dimension_like(wrapper_fn, arg, before_index=before_index)
            for arg in call.args
        )
    return False


def _wrapper_parameter_names(wrapper_fn: ast.FunctionDef) -> set[str]:
    return {
        arg.arg
        for arg in (
            [*wrapper_fn.args.posonlyargs]
            + [*wrapper_fn.args.args]
            + [*wrapper_fn.args.kwonlyargs]
        )
    }


def _initial_wrapper_names(wrapper_fn: ast.FunctionDef) -> set[str]:
    names = _wrapper_parameter_names(wrapper_fn)
    names.update({"torch", "triton", "max", "min"})
    return names


def _referenced_names(node: ast.AST) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def _node_parent_map(node: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(node)
        for child in ast.iter_child_nodes(parent)
    }


def _assignment_target_names(targets: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for target in targets:
        names.update(_referenced_names(target))
    return names


def _returned_name(wrapper_fn: ast.FunctionDef) -> str | None:
    for stmt in wrapper_fn.body:
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
            return stmt.value.id
    return None


def _launch_argument_names(launch: ast.Call) -> set[str]:
    names = {arg.id for arg in launch.args if isinstance(arg, ast.Name)}
    for keyword in launch.keywords:
        if isinstance(keyword.value, ast.Name):
            names.add(keyword.value.id)
    return names


def _assigned_names(targets: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _target_root_names(targets: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for target in targets:
        names.update(_target_root_names_from_node(target))
    return names


def _target_root_names_from_node(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Subscript, ast.Attribute)):
        return _target_root_names_from_node(target.value)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_root_names_from_node(element))
        return names
    return set()


def _target_is_name(target: ast.expr, name: str) -> bool:
    return isinstance(target, ast.Name) and target.id == name


def _function_statements_are_valid(
    function: ast.FunctionDef,
    *,
    in_kernel: bool,
    allow_return: bool = False,
) -> bool:
    return all(
        _stmt_is_valid(stmt, in_kernel=in_kernel, allow_return=allow_return)
        for stmt in function.body
    )


def _stmt_is_valid(
    stmt: ast.stmt,
    *,
    in_kernel: bool,
    allow_return: bool = False,
) -> bool:
    if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Expr)):
        return True
    if not in_kernel and isinstance(stmt, ast.Assert):
        return True
    if isinstance(stmt, ast.Return):
        return allow_return or not in_kernel
    if in_kernel and isinstance(stmt, ast.If):
        return all(
            _stmt_is_valid(child, in_kernel=True, allow_return=allow_return)
            for child in stmt.body
        ) and all(
            _stmt_is_valid(child, in_kernel=True, allow_return=allow_return)
            for child in stmt.orelse
        )
    if in_kernel and isinstance(stmt, ast.For):
        return (
            _range_loop_is_valid(stmt)
            and all(
                _stmt_is_valid(child, in_kernel=True, allow_return=allow_return)
                for child in stmt.body
            )
            and not stmt.orelse
        )
    return False


def _statement_only_tl_calls_are_valid(function: ast.FunctionDef) -> bool:
    return _statement_only_tl_calls_are_valid_in_statements(function.body)


def _statement_only_tl_calls_are_valid_in_statements(statements: list[ast.stmt]) -> bool:
    for stmt in statements:
        if isinstance(stmt, ast.Assign):
            if _expression_contains_statement_only_call(stmt.value):
                return False
            continue
        if isinstance(stmt, ast.AugAssign):
            if _expression_contains_statement_only_call(stmt.value):
                return False
            continue
        if isinstance(stmt, ast.Expr):
            if _is_statement_only_call(stmt.value):
                if _expression_contains_statement_only_call(stmt.value, skip_root=True):
                    return False
                continue
            if _expression_contains_statement_only_call(stmt.value):
                return False
            continue
        if isinstance(stmt, ast.Return):
            if stmt.value is not None and _expression_contains_statement_only_call(stmt.value):
                return False
            continue
        if isinstance(stmt, ast.If):
            if _expression_contains_statement_only_call(stmt.test):
                return False
            if not _statement_only_tl_calls_are_valid_in_statements(stmt.body):
                return False
            if not _statement_only_tl_calls_are_valid_in_statements(stmt.orelse):
                return False
            continue
        if isinstance(stmt, ast.For):
            if _expression_contains_statement_only_call(stmt.iter):
                return False
            if not _statement_only_tl_calls_are_valid_in_statements(stmt.body):
                return False
            if not _statement_only_tl_calls_are_valid_in_statements(stmt.orelse):
                return False
    return True


def _expression_contains_statement_only_call(
    expression: ast.AST,
    *,
    skip_root: bool = False,
) -> bool:
    for node in ast.walk(expression):
        if skip_root and node is expression:
            continue
        if _is_statement_only_call(node):
            return True
    return False


def _is_statement_only_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    tl_name = _tl_call_name(node.func)
    if tl_name in STATEMENT_ONLY_TL_CALLS:
        return True
    descriptor_method_name = _descriptor_method_call_name(node.func)
    return descriptor_method_name in STATEMENT_ONLY_DESCRIPTOR_METHOD_CALLS


def _range_loop_is_valid(stmt: ast.For) -> bool:
    if not isinstance(stmt.target, ast.Name):
        return False
    if not isinstance(stmt.iter, ast.Call):
        return False
    if _is_name(stmt.iter.func, "range"):
        return len(stmt.iter.args) == 3 and not stmt.iter.keywords
    if _tl_call_name(stmt.iter.func) in {"range", "static_range"}:
        return _valid_tl_call_shape(_tl_call_name(stmt.iter.func) or "", stmt.iter)
    return False


def _all_calls_are_valid(
    node_root: ast.AST,
    kernel_name: str | frozenset[str],
    *,
    allow_tl_calls: bool,
    allow_runtime_calls: bool,
    allow_kernel_launch: bool,
    allowed_tl_calls: frozenset[str] = ALLOWED_TL_CALLS,
) -> bool:
    for node in ast.walk(node_root):
        if not isinstance(node, ast.Call):
            continue
        tl_name = _tl_call_name(node.func)
        if tl_name is not None:
            if not allow_tl_calls:
                return False
            if tl_name not in allowed_tl_calls:
                return False
            if not _valid_tl_call_shape(tl_name, node):
                return False
            continue
        descriptor_method_name = _descriptor_method_call_name(node.func)
        if descriptor_method_name is not None:
            if not allow_tl_calls:
                return False
            if not _valid_descriptor_method_call_shape(descriptor_method_name, node):
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


def _descriptor_method_call_name(node: ast.AST) -> str | None:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.attr in TENSOR_DESCRIPTOR_METHOD_CALLS
    ):
        return node.attr
    return None


def _valid_descriptor_method_call_shape(name: str, node: ast.Call) -> bool:
    keyword_names = [kw.arg for kw in node.keywords]
    if any(keyword is None for keyword in keyword_names):
        return False
    kwargs = {keyword for keyword in keyword_names if keyword is not None}
    if len(kwargs) != len(keyword_names) or kwargs:
        return False

    if name == "load":
        return len(node.args) == 1
    if name == "store":
        return len(node.args) == 2
    if name in {
        "atomic_add",
        "atomic_and",
        "atomic_max",
        "atomic_min",
        "atomic_or",
        "atomic_xor",
    }:
        return len(node.args) == 2
    if name == "gather":
        return len(node.args) >= 1
    if name == "scatter":
        return len(node.args) >= 2
    return False


def _valid_non_tl_call(
    node: ast.Call,
    kernel_name: str | frozenset[str],
    *,
    allow_runtime_calls: bool,
    allow_kernel_launch: bool,
) -> bool:
    if _is_attr_name(node.func, "triton", "autotune"):
        return _is_autotune_decorator(node)
    if _is_attr_name(node.func, "triton", "Config"):
        return _is_fixed_config(node)
    if _is_attr_name(node.func, "triton", "heuristics"):
        return _is_heuristics_decorator(node)
    if _is_attr_name(node.func, "triton", "next_power_of_2"):
        return len(node.args) == 1 and not node.keywords
    if _is_tensor_to_call(node):
        return not allow_runtime_calls
    if not allow_runtime_calls:
        return _is_name(node.func, "range") and len(node.args) == 3 and not node.keywords
    if _is_attr_name(node.func, "triton", "cdiv"):
        return len(node.args) == 2 and not node.keywords
    if _is_attr_name(node.func, "torch", "empty_like"):
        return len(node.args) == 1 and not node.keywords
    if _is_attr_name(node.func, "torch", "empty"):
        return (
            len(node.args) == 1
            and {kw.arg for kw in node.keywords} == {"device", "dtype"}
        )
    if isinstance(node.func, ast.Attribute) and node.func.attr == "numel":
        return not node.args and not node.keywords and isinstance(node.func.value, ast.Name)
    if isinstance(node.func, ast.Name) and node.func.id in {"max", "min"}:
        return len(node.args) == 2 and not node.keywords
    if _is_name(node.func, "range"):
        return len(node.args) == 3 and not node.keywords
    if (
        allow_kernel_launch
        and isinstance(node.func, ast.Subscript)
        and _is_allowed_kernel_name(node.func.value, kernel_name)
    ):
        return True
    if (
        allow_kernel_launch
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and _is_allowed_kernel_name(node.func.value, kernel_name)
    ):
        return False
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and _is_allowed_kernel_name(node.func.value, kernel_name)
    ):
        return False
    return False


def _is_tensor_to_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "to"
        and isinstance(node.func.value, ast.Name)
        and len(node.args) == 1
        and not node.keywords
        and _is_tl_dtype(node.args[0])
    )


def _is_tl_dtype(node: ast.AST) -> bool:
    return tuple(_attribute_chain(node)) in TRITON_DTYPE_CHAINS


def _is_allowed_kernel_name(node: ast.AST, kernel_name: str | frozenset[str]) -> bool:
    if isinstance(kernel_name, str):
        return _is_name(node, kernel_name)
    return isinstance(node, ast.Name) and node.id in kernel_name


def _valid_tl_call_shape(name: str, node: ast.Call) -> bool:
    keyword_names = [kw.arg for kw in node.keywords]
    if any(keyword is None for keyword in keyword_names):
        return False
    kwargs = {keyword for keyword in keyword_names if keyword is not None}
    if len(kwargs) != len(keyword_names):
        return False

    match name:
        case "load":
            return len(node.args) == 1 and kwargs <= {
                "mask",
                "other",
                "boundary_check",
                "padding_option",
                "cache_modifier",
                "eviction_policy",
                "volatile",
            }
        case "store":
            return len(node.args) == 2 and kwargs <= {
                "mask",
                "boundary_check",
                "cache_modifier",
                "eviction_policy",
            }
        case "arange":
            return len(node.args) == 2 and not kwargs
        case "program_id":
            return _valid_program_id_call(node)
        case "num_programs":
            return _valid_program_id_call(node)
        case "zeros":
            return len(node.args) == 1 and kwargs == {"dtype"}
        case "full":
            return len(node.args) == 2 and kwargs == {"dtype"}
        case "zeros_like":
            return len(node.args) == 1 and not kwargs
        case "cat":
            return len(node.args) == 2 and kwargs <= {"can_reorder", "dim"}
        case "cast":
            return len(node.args) == 2 and kwargs <= {
                "fp_downcast_rounding",
                "bitcast",
            }
        case "broadcast" | "interleave" | "join" | "advance":
            return len(node.args) == 2 and not kwargs
        case "broadcast_to" | "reshape" | "view":
            return len(node.args) >= 2 and kwargs <= {"can_reorder"}
        case "expand_dims":
            return len(node.args) == 2 and not kwargs
        case "permute" | "trans":
            return len(node.args) >= 1 and not kwargs
        case "ravel":
            return len(node.args) == 1 and kwargs <= {"can_reorder"}
        case "split":
            return len(node.args) == 1 and not kwargs
        case "dot":
            return len(node.args) == 2 and kwargs <= {
                "acc",
                "input_precision",
                "allow_tf32",
                "max_num_imprecise_acc",
                "out_dtype",
            }
        case "dot_scaled":
            return len(node.args) == 6 and kwargs <= {
                "acc",
                "fast_math",
                "lhs_k_pack",
                "rhs_k_pack",
                "out_dtype",
            }
        case "make_tensor_descriptor":
            return len(node.args) == 1 and {"shape", "strides", "block_shape"} <= kwargs <= {
                "shape",
                "strides",
                "block_shape",
                "padding_option",
            }
        case "load_tensor_descriptor":
            return len(node.args) == 2 and not kwargs
        case "store_tensor_descriptor":
            return len(node.args) == 3 and not kwargs
        case "make_block_ptr":
            return (len(node.args) == 6 and not kwargs) or (
                not node.args
                and kwargs
                == {"base", "shape", "strides", "offsets", "block_shape", "order"}
            )
        case "flip":
            return len(node.args) in {1, 2} and not kwargs
        case "swizzle2d":
            return len(node.args) == 5 and not kwargs
        case (
            "abs"
            | "ceil"
            | "cos"
            | "erf"
            | "exp2"
            | "floor"
            | "log2"
            | "rsqrt"
            | "sigmoid"
            | "sin"
            | "softmax"
            | "sqrt_rn"
        ):
            return len(node.args) == 1 and kwargs <= {
                "dim",
                "keep_dims",
                "ieee_rounding",
            }
        case "cdiv" | "div_rn" | "fdiv" | "maximum" | "minimum" | "umulhi":
            return len(node.args) == 2 and kwargs <= {
                "ieee_rounding",
                "propagate_nan",
            }
        case "clamp" | "fma":
            return len(node.args) == 3 and kwargs <= {"propagate_nan"}
        case "atomic_add":
            return len(node.args) == 2 and kwargs <= {"mask", "sem", "scope"}
        case (
            "atomic_and"
            | "atomic_max"
            | "atomic_min"
            | "atomic_or"
            | "atomic_xchg"
            | "atomic_xor"
        ):
            return len(node.args) == 2 and kwargs <= {"mask", "sem", "scope"}
        case "atomic_cas":
            return len(node.args) == 3 and kwargs <= {"sem", "scope"}
        case "sum":
            return _valid_axis_reduction_call(
                node,
                {
                    "axis",
                    "keep_dims",
                    "dtype",
                },
            )
        case "max":
            return _valid_axis_reduction_call(
                node,
                {
                    "axis",
                    "keep_dims",
                    "return_indices",
                    "return_indices_tie_break_left",
                },
            )
        case "argmax" | "argmin":
            return _valid_required_axis_reduction_call(
                node,
                {
                    "axis",
                    "keep_dims",
                    "tie_break_left",
                },
            )
        case "min":
            return _valid_axis_reduction_call(
                node,
                {
                    "axis",
                    "keep_dims",
                    "return_indices",
                    "return_indices_tie_break_left",
                },
            )
        case "xor_sum":
            return _valid_axis_reduction_call(node, {"axis", "keep_dims"})
        case "reduce":
            return len(node.args) == 3 and kwargs <= {"keep_dims"}
        case "associative_scan":
            return len(node.args) == 3 and kwargs <= {"reverse"}
        case "cumprod" | "cumsum":
            return len(node.args) == 1 and kwargs <= {"axis", "reverse", "dtype"}
        case "histogram":
            return len(node.args) == 2 and kwargs <= {"mask"}
        case "sort":
            return len(node.args) == 1 and kwargs <= {"dim", "descending"}
        case "topk":
            return len(node.args) == 2 and kwargs <= {"dim", "descending"}
        case "gather":
            return len(node.args) == 3 and not kwargs
        case "randint4x" | "randint" | "rand" | "randn":
            return len(node.args) == 2 and kwargs <= {"n_rounds"}
        case "range":
            return _valid_range_iterator_call(
                node,
                {
                    "num_stages",
                    "loop_unroll_factor",
                    "disallow_acc_multi_buffer",
                    "flatten",
                    "warp_specialize",
                    "disable_licm",
                },
            )
        case "static_range":
            return _valid_range_iterator_call(node, set())
        case "inline_asm_elementwise":
            return not node.args and kwargs == {
                "asm",
                "constraints",
                "args",
                "dtype",
                "is_pure",
                "pack",
            }
        case "assume":
            return len(node.args) == 1 and not kwargs
        case "debug_barrier":
            return not node.args and not kwargs
        case "max_constancy" | "max_contiguous" | "multiple_of":
            return len(node.args) == 2 and not kwargs
        case "static_print":
            return kwargs <= {"sep", "end", "file", "flush"}
        case "static_assert":
            return len(node.args) in {1, 2} and not kwargs
        case "device_print":
            return len(node.args) >= 1 and kwargs <= {"hex"}
        case "device_assert":
            return len(node.args) in {1, 2} and kwargs <= {"mask"}
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


def _valid_axis_reduction_call(
    node: ast.Call,
    allowed_kwargs: set[str],
) -> bool:
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    if len(node.args) not in {1, 2}:
        return False
    if len(node.args) == 2 and "axis" in kwargs:
        return False
    return kwargs <= allowed_kwargs


def _valid_required_axis_reduction_call(
    node: ast.Call,
    allowed_kwargs: set[str],
) -> bool:
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    if len(node.args) == 2 and "axis" in kwargs:
        return False
    if len(node.args) == 2:
        return kwargs <= allowed_kwargs
    if len(node.args) == 1 and "axis" in kwargs:
        return kwargs <= allowed_kwargs
    return False


def _valid_range_iterator_call(
    node: ast.Call,
    compiler_kwargs: set[str],
) -> bool:
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    if not 1 <= len(node.args) <= 3:
        return False
    allowed_kwargs = set(compiler_kwargs)
    if len(node.args) == 1:
        allowed_kwargs |= {"arg2", "step"}
    elif len(node.args) == 2:
        allowed_kwargs.add("step")
    return kwargs <= allowed_kwargs


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
