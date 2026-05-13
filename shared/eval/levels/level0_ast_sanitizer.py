"""Allowlist-only AST sanitizer for generated Triton module surfaces.

This module performs static checks only. It does not import torch, import
triton, compile generated code, execute generated code, or inspect task
semantics. The launcher body policy is default-deny: expressions and calls are
allowed only when they are needed to allocate outputs, read tensor metadata, or
launch a Triton kernel.

Threat model: Level 0 checks apply only to Python surfaces that actually
execute. Those are the module top level, launcher function bodies, and the
load-time expressions attached to top-level functions (decorators, default
values, annotations). The body of a ``@triton.jit`` kernel is compiled by
Triton into IR/PTX and is never executed as Python, so arbitrary Python escape
patterns inside a kernel body cannot bypass the evaluator. They surface as
F1_COMPILE failures via Triton's own compiler, not as Level 0 violations.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Final


F0_SURFACE_VIOLATION: Final = "F0_SURFACE_VIOLATION"
SANITIZER_TOOL: Final = "level0_ast_sanitizer"

_ALLOWED_TORCH_ALLOCATORS: Final = frozenset(
    {
        "empty",
        "empty_like",
        "zeros",
        "zeros_like",
        "ones",
        "ones_like",
    }
)
_ALLOWED_TORCH_TYPE_NAMES: Final = frozenset({"Tensor"})
_ALLOWED_TORCH_ATTRS: Final = _ALLOWED_TORCH_ALLOCATORS | _ALLOWED_TORCH_TYPE_NAMES
_ALLOWED_TENSOR_METADATA_ATTRS: Final = frozenset({"shape", "dtype", "device"})
_ALLOWED_TENSOR_METADATA_METHODS: Final = frozenset({"numel", "stride", "size"})
_ALLOWED_TRITON_CALLS: Final = frozenset({"cdiv"})
_ALLOWED_TRITON_DECORATORS: Final = frozenset({"jit"})
_ALLOWED_IMPORTS: Final = frozenset({"torch", "triton", "triton.language"})
_ALLOWED_BINOPS: Final = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.FloorDiv,
    ast.Mod,
)
_ALLOWED_UNARYOPS: Final = (ast.UAdd, ast.USub)

_TORCH_COMPUTE_CALLS: Final = frozenset(
    {
        "relu",
        "softmax",
        "matmul",
        "mm",
        "bmm",
        "einsum",
        "dot",
        "exp",
        "sum",
        "max",
        "mean",
        "var",
        "std",
        "minimum",
        "maximum",
        "where",
        "sigmoid",
        "tanh",
        "gelu",
        "add",
        "mul",
        "sub",
        "div",
    }
)
_DANGEROUS_CALL_NAMES: Final = frozenset(
    {
        "__import__",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }
)
_DANGEROUS_DYNAMIC_ACCESS_NAMES: Final = frozenset(
    {"__getattr__", "__getattribute__", "getattr", "globals", "locals", "vars"}
)
_DANGEROUS_ALIAS_NAMES: Final = (
    _DANGEROUS_CALL_NAMES | _DANGEROUS_DYNAMIC_ACCESS_NAMES
) - frozenset({"input"})
_DANGEROUS_BUILTINS_NAMES: Final = frozenset({"__builtins__", "builtins"})
_DANGEROUS_ROOTS: Final = frozenset(
    {
        "asyncio",
        "ftplib",
        "glob",
        "http",
        "multiprocessing",
        "os",
        "pathlib",
        "pickle",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "urllib",
    }
)
_REFERENCE_CALL_NAMES: Final = frozenset(
    {
        "Model",
        "ReferenceModel",
        "model",
        "ref_model",
        "reference",
        "reference_model",
        "run_reference",
        "get_inputs",
        "forward",
    }
)
_REFERENCE_NAME_FRAGMENTS: Final = ("reference", "ref_model")
_TIMING_SURFACE_FRAGMENTS: Final = (
    "benchmark",
    "cuda.event",
    "event",
    "perf_counter",
    "profile",
    "profiler",
    "speedup",
    "timeit",
    "timing",
)
_RAW_SURFACE_PATTERNS: Final = tuple(
    re.compile(rf"\b{re.escape(fragment)}\b", re.IGNORECASE)
    for fragment in _TIMING_SURFACE_FRAGMENTS
)


@dataclass(frozen=True)
class Level0AstViolation:
    """One static surface violation with source location when available."""

    line_number: int | None
    reason: str
    failure_code: str = F0_SURFACE_VIOLATION

    def format(self) -> str:
        if self.line_number is None:
            return f"{self.failure_code}: {self.reason}"
        return f"{self.failure_code}: line {self.line_number}: {self.reason}"


@dataclass(frozen=True)
class Level0AstSanitizerResult:
    """Static sanitizer result for one generated source string."""

    safe_success: bool
    failure_code: str | None
    violations: tuple[Level0AstViolation, ...] = ()
    sanitizer_tool: str = SANITIZER_TOOL

    @property
    def sanitizer_errors(self) -> list[str] | None:
        if not self.violations:
            return None
        return [violation.format() for violation in self.violations]


@dataclass
class _AliasContext:
    torch_names: set[str]
    triton_names: set[str]
    tl_names: set[str]
    functional_aliases: set[str]
    dangerous_aliases: set[str]
    reference_aliases: set[str]

    @classmethod
    def initial(cls) -> "_AliasContext":
        return cls(
            torch_names={"torch"},
            triton_names={"triton"},
            tl_names={"tl"},
            functional_aliases=set(),
            dangerous_aliases=set(),
            reference_aliases=set(),
        )

    def copy(self) -> "_AliasContext":
        return _AliasContext(
            torch_names=set(self.torch_names),
            triton_names=set(self.triton_names),
            tl_names=set(self.tl_names),
            functional_aliases=set(self.functional_aliases),
            dangerous_aliases=set(self.dangerous_aliases),
            reference_aliases=set(self.reference_aliases),
        )


class _ViolationSink:
    def __init__(self) -> None:
        self.violations: list[Level0AstViolation] = []

    def add(
        self,
        node_or_line: ast.AST | int | None,
        reason: str,
        failure_code: str = F0_SURFACE_VIOLATION,
    ) -> None:
        if isinstance(node_or_line, int):
            line_number = node_or_line
        elif node_or_line is None:
            line_number = None
        else:
            line_number = getattr(node_or_line, "lineno", None)
        self.violations.append(
            Level0AstViolation(line_number, _short_reason(reason), failure_code)
        )

    def deduped(self) -> tuple[Level0AstViolation, ...]:
        seen: set[tuple[int | None, str, str]] = set()
        deduped: list[Level0AstViolation] = []
        for violation in self.violations:
            key = (
                violation.line_number,
                violation.reason,
                violation.failure_code,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(violation)
        return tuple(deduped)


class _ModuleSurfaceScanner(ast.NodeVisitor):
    """Ban dangerous generated-code surfaces while collecting aliases."""

    def __init__(self, sink: _ViolationSink, aliases: _AliasContext) -> None:
        self._sink = sink
        self._aliases = aliases
        self._function_depth = 0

    def visit_Import(self, node: ast.Import) -> None:
        if self._function_depth > 0:
            self._sink.add(node, "nested imports are not allowed in generated code")
            return

        for imported in node.names:
            bound_name = imported.asname or imported.name.split(".", maxsplit=1)[0]
            if imported.name not in _ALLOWED_IMPORTS:
                self._sink.add(
                    node,
                    f"import {imported.name!r} is not allowed in generated code",
                )
                continue
            if imported.name == "torch":
                self._aliases.torch_names.add(bound_name)
            elif imported.name == "triton":
                self._aliases.triton_names.add(bound_name)
            elif imported.name == "triton.language":
                if imported.asname is None:
                    self._sink.add(node, "triton.language import must use an explicit alias")
                else:
                    self._aliases.tl_names.add(imported.asname)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        imported = ", ".join(alias.name for alias in node.names)
        self._sink.add(
            node,
            f"from-import is not allowed: from {module} import {imported}",
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._sink.add(node, "class definitions are not allowed in generated code")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        _check_function_decorators(node, self._sink, self._aliases)
        _check_function_definition_surfaces(node, self._sink)
        if _has_triton_jit_decorator(node, self._aliases):
            # Triton compiles the kernel body, but signature defaults,
            # annotations, and the return annotation are executable Python at
            # module load and still get the full Level 0 surface scan.
            self.visit(node.args)
            if node.returns is not None:
                self.visit(node.returns)
            return
        self._function_depth += 1
        try:
            self.generic_visit(node)
        finally:
            self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        _check_function_decorators(node, self._sink, self._aliases)
        _check_function_definition_surfaces(node, self._sink)
        self._function_depth += 1
        try:
            self.generic_visit(node)
        finally:
            self._function_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_alias_assignment(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_alias_assignment([node.target], node.value)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._sink.add(node, "walrus assignments are not allowed")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.MatMult):
            self._sink.add(node, "tensor @ operator is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if _is_timing_surface_name(node.id):
            self._sink.add(node, f"timing/profiling/speedup surface {node.id!r} is not allowed")
        if _is_reference_symbol(node.id):
            self._sink.add(node, f"reference/model surface {node.id!r} is not allowed")
        if node.id in _DANGEROUS_BUILTINS_NAMES:
            self._sink.add(node, f"dangerous builtins namespace {node.id!r} is not allowed")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        chain = _attribute_chain(node)
        root = chain[0] if chain else None
        attr = chain[-1] if chain else node.attr

        if _is_timing_surface_name(attr):
            self._sink.add(node, f"timing/profiling/speedup surface {attr!r} is not allowed")
        if _is_reference_symbol(attr):
            self._sink.add(node, f"reference/model surface {attr!r} is not allowed")
        if root in self._aliases.functional_aliases or _is_torch_functional_chain(
            chain,
            self._aliases,
        ):
            self._sink.add(node, "torch.nn.functional access is not allowed")
        if root in self._aliases.torch_names and not (
            len(chain) == 2 and attr in _ALLOWED_TORCH_ATTRS
        ):
            self._sink.add(node, f"torch attribute {'.'.join(chain)!r} is not allowlisted")
        if (
            attr in _TORCH_COMPUTE_CALLS
            and root not in self._aliases.torch_names
            and root not in self._aliases.triton_names
            and root not in self._aliases.tl_names
            and root not in self._aliases.functional_aliases
        ):
            self._sink.add(node, f"tensor compute method {attr!r} is not allowed")
        if root in self._aliases.triton_names and not (
            len(chain) == 2
            and attr in _ALLOWED_TRITON_CALLS | _ALLOWED_TRITON_DECORATORS
        ):
            self._sink.add(node, f"triton attribute {'.'.join(chain)!r} is not allowlisted")
        if root in _DANGEROUS_ROOTS:
            self._sink.add(node, f"file/network/process/system surface {root!r} is not allowed")
        if root in _DANGEROUS_BUILTINS_NAMES:
            self._sink.add(node, f"dangerous builtins namespace {root!r} is not allowed")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and _contains_timing_surface(node.value):
            self._sink.add(node, "timing/profiling/speedup string is not allowed")

    def visit_Call(self, node: ast.Call) -> None:
        chain = _call_chain(node.func)
        name = chain[-1] if chain else None
        root = chain[0] if chain else None
        subscript_root = _subscript_root_name(node.func)
        if not isinstance(node.func, (ast.Name, ast.Attribute)):
            dangerous_target = _dangerous_builtin_reference_name(node.func)
            if dangerous_target is not None:
                self._sink.add(
                    node.func,
                    f"dangerous builtin call target {dangerous_target!r} is not allowed",
                )

        if name in _DANGEROUS_CALL_NAMES:
            self._sink.add(node, f"dangerous builtin call {name!r} is not allowed")
        if name in _DANGEROUS_DYNAMIC_ACCESS_NAMES:
            self._sink.add(node, f"dynamic access {name!r} is not allowed")
        if root in _DANGEROUS_ROOTS:
            self._sink.add(node, f"file/network/process/system surface {root!r} is not allowed")
        if root in _DANGEROUS_BUILTINS_NAMES:
            self._sink.add(node, f"dangerous builtins namespace {root!r} is not allowed")
        if root in self._aliases.functional_aliases or _is_torch_functional_chain(
            chain,
            self._aliases,
        ):
            self._sink.add(node, "torch.nn.functional calls are not allowed")
        if root in self._aliases.dangerous_aliases:
            self._sink.add(node, f"dangerous builtin alias call {root!r} is not allowed")
        if subscript_root in self._aliases.dangerous_aliases:
            self._sink.add(
                node,
                f"dangerous builtin container alias call {subscript_root!r} is not allowed",
            )
        if root in self._aliases.torch_names and name not in _ALLOWED_TORCH_ALLOCATORS:
            self._sink.add(
                node,
                f"torch call {'.'.join(chain)!r} is outside the allocation allowlist",
            )
        if (
            isinstance(node.func, ast.Attribute)
            and name in _TORCH_COMPUTE_CALLS
            and root not in self._aliases.torch_names
            and root not in self._aliases.triton_names
            and root not in self._aliases.tl_names
            and root not in self._aliases.functional_aliases
        ):
            self._sink.add(node, f"tensor compute method {name!r} is not allowed")
        if _is_reference_symbol(name or "") or root in self._aliases.reference_aliases:
            self._sink.add(node, f"reference/model call {'.'.join(chain) or '<dynamic>'!r} is not allowed")

        self.generic_visit(node)

    def _record_alias_assignment(
        self,
        targets: list[ast.expr],
        value: ast.expr | None,
    ) -> None:
        if value is None:
            return
        for target_names, bound_value in _iter_assignment_bindings(targets, value):
            self._record_alias_binding(target_names, bound_value)

    def _record_alias_binding(
        self,
        target_names: set[str],
        value: ast.expr,
    ) -> None:
        dangerous_name = _dangerous_builtin_reference_name(value)
        if dangerous_name is not None:
            self._aliases.dangerous_aliases.update(target_names)
            self._sink.add(value, f"dangerous builtin surface {dangerous_name!r} is not allowed")
            return

        chain = _attribute_chain(value)
        if _is_torch_reference(chain, self._aliases):
            self._aliases.torch_names.update(target_names)
        elif _is_triton_reference(chain, self._aliases):
            self._aliases.triton_names.update(target_names)
        elif _is_torch_functional_chain(chain, self._aliases):
            self._aliases.functional_aliases.update(target_names)
        elif chain and _is_reference_symbol(chain[-1]):
            self._aliases.reference_aliases.update(target_names)


class _LauncherBodyChecker:
    """Default-deny checker for non-JIT launcher bodies."""

    def __init__(self, sink: _ViolationSink, module_aliases: _AliasContext) -> None:
        self._sink = sink
        self._aliases = module_aliases.copy()

    def check(self, node: ast.FunctionDef) -> None:
        for statement in node.body:
            self._check_statement(statement)

    def _check_statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Assign):
            self._check_assignment_targets(node.targets)
            self._check_expr(node.value)
            self._record_assignment_aliases(node.targets, node.value)
            return
        if isinstance(node, ast.AnnAssign):
            self._check_assignment_targets([node.target])
            if node.value is not None:
                self._check_expr(node.value)
                self._record_assignment_aliases([node.target], node.value)
            return
        if isinstance(node, ast.Return):
            if node.value is None:
                self._sink.add(node, "launcher return must include a value")
                return
            self._check_expr(node.value)
            return
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._check_expr(node.value)
            return

        self._sink.add(
            node,
            f"launcher statement {type(node).__name__} is not allowlisted",
        )

    def _check_assignment_targets(self, targets: list[ast.expr]) -> None:
        for target in targets:
            if _is_valid_assignment_target(target):
                for name in _assignment_target_names([target]):
                    if _is_timing_surface_name(name):
                        self._sink.add(
                            target,
                            f"timing/profiling/speedup surface {name!r} is not allowed",
                        )
                    if _is_reference_symbol(name):
                        self._sink.add(target, f"reference/model surface {name!r} is not allowed")
                continue
            self._sink.add(
                target,
                f"launcher assignment target {type(target).__name__} is not allowlisted",
            )

    def _record_assignment_aliases(self, targets: list[ast.expr], value: ast.expr) -> None:
        for target_names, bound_value in _iter_assignment_bindings(targets, value):
            self._record_assignment_alias_binding(target_names, bound_value)

    def _record_assignment_alias_binding(
        self,
        target_names: set[str],
        value: ast.expr,
    ) -> None:
        dangerous_name = _dangerous_builtin_reference_name(value)
        if dangerous_name is not None:
            self._aliases.dangerous_aliases.update(target_names)
            return

        chain = _attribute_chain(value)
        if _is_torch_reference(chain, self._aliases):
            self._aliases.torch_names.update(target_names)
        elif _is_triton_reference(chain, self._aliases):
            self._aliases.triton_names.update(target_names)
        elif _is_torch_functional_chain(chain, self._aliases):
            self._aliases.functional_aliases.update(target_names)
        elif chain and _is_reference_symbol(chain[-1]):
            self._aliases.reference_aliases.update(target_names)

    def _check_expr(self, node: ast.AST | None) -> None:
        if node is None:
            return
        if isinstance(node, (ast.Constant, ast.Name)):
            if isinstance(node, ast.Name):
                if _is_timing_surface_name(node.id):
                    self._sink.add(
                        node,
                        f"timing/profiling/speedup surface {node.id!r} is not allowed",
                    )
                if _is_reference_symbol(node.id):
                    self._sink.add(node, f"reference/model surface {node.id!r} is not allowed")
            elif isinstance(node.value, str) and _contains_timing_surface(node.value):
                self._sink.add(node, "timing/profiling/speedup string is not allowed")
            return
        if isinstance(node, (ast.Tuple, ast.List)):
            for item in node.elts:
                self._check_expr(item)
            return
        if isinstance(node, ast.Dict):
            for key in node.keys:
                self._check_expr(key)
            for value in node.values:
                self._check_expr(value)
            return
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _ALLOWED_UNARYOPS):
                self._sink.add(node, f"unary operator {type(node.op).__name__} is not allowlisted")
            self._check_expr(node.operand)
            return
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.MatMult):
                self._sink.add(node, "tensor @ operator is not allowed")
            elif not isinstance(node.op, _ALLOWED_BINOPS):
                self._sink.add(node, f"binary operator {type(node.op).__name__} is not allowlisted")
            self._check_expr(node.left)
            self._check_expr(node.right)
            return
        if isinstance(node, ast.Subscript):
            if not _is_allowlisted_subscript_value(node.value):
                self._sink.add(node, "only tensor metadata subscripts are allowlisted")
            self._check_expr(node.value)
            self._check_expr(node.slice)
            return
        if isinstance(node, ast.Slice):
            self._check_expr(node.lower)
            self._check_expr(node.upper)
            self._check_expr(node.step)
            return
        if isinstance(node, ast.Attribute):
            self._check_attribute(node)
            return
        if isinstance(node, ast.Call):
            self._check_call(node)
            return
        if isinstance(node, ast.keyword):
            self._check_expr(node.value)
            return

        self._sink.add(node, f"launcher expression {type(node).__name__} is not allowlisted")

    def _check_attribute(self, node: ast.Attribute) -> None:
        chain = _attribute_chain(node)
        root = chain[0] if chain else None
        attr = chain[-1] if chain else node.attr

        if _is_timing_surface_name(attr):
            self._sink.add(node, f"timing/profiling/speedup surface {attr!r} is not allowed")
            return
        if _is_reference_symbol(attr):
            self._sink.add(node, f"reference/model surface {attr!r} is not allowed")
            return
        if _is_torch_functional_chain(chain, self._aliases) or root in self._aliases.functional_aliases:
            self._sink.add(node, "torch.nn.functional access is not allowed")
            return
        if root in self._aliases.torch_names:
            self._sink.add(node, f"torch attribute {'.'.join(chain)!r} is not allowlisted")
            return
        if root in self._aliases.triton_names:
            self._sink.add(node, f"triton attribute {'.'.join(chain)!r} is not allowlisted")
            return
        if root in _DANGEROUS_ROOTS:
            self._sink.add(node, f"file/network/process/system surface {root!r} is not allowed")
            return
        if attr in _ALLOWED_TENSOR_METADATA_ATTRS:
            self._check_expr(node.value)
            return

        self._sink.add(node, f"attribute {attr!r} is not allowlisted")

    def _check_call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Subscript):
            self._check_bracket_launch(node)
            return

        chain = _call_chain(node.func)
        root = chain[0] if chain else None
        name = chain[-1] if chain else None

        if isinstance(node.func, ast.Name):
            self._check_name_call(node, node.func.id)
            return
        if not isinstance(node.func, ast.Attribute):
            self._sink.add(node, "call target is not allowlisted")
            return

        if root in _DANGEROUS_ROOTS:
            self._sink.add(node, f"file/network/process/system surface {root!r} is not allowed")
            return
        if _is_torch_functional_chain(chain, self._aliases) or root in self._aliases.functional_aliases:
            self._sink.add(node, "torch.nn.functional calls are not allowed")
            return
        if root in self._aliases.torch_names:
            if len(chain) == 2 and name in _ALLOWED_TORCH_ALLOCATORS:
                self._check_call_arguments(node)
                return
            reason = (
                f"torch compute call {'.'.join(chain)!r} is not allowed"
                if name in _TORCH_COMPUTE_CALLS
                else f"torch call {'.'.join(chain)!r} is outside the allocation allowlist"
            )
            self._sink.add(node, reason)
            return
        if root in self._aliases.triton_names:
            if len(chain) == 2 and name in _ALLOWED_TRITON_CALLS:
                self._check_call_arguments(node)
                return
            self._sink.add(node, f"triton call {'.'.join(chain)!r} is not allowlisted")
            return
        if name in _ALLOWED_TENSOR_METADATA_METHODS:
            self._check_call_arguments(node)
            return
        if name in _TORCH_COMPUTE_CALLS:
            self._sink.add(node, f"tensor compute method {name!r} is not allowed")
            return
        if _is_reference_symbol(name or "") or root in self._aliases.reference_aliases:
            self._sink.add(node, f"reference/model call {'.'.join(chain) or '<dynamic>'!r} is not allowed")
            return

        self._sink.add(node, f"call {'.'.join(chain) or '<dynamic>'!r} is not allowlisted")

    def _check_name_call(self, node: ast.Call, name: str) -> None:
        if name in _DANGEROUS_CALL_NAMES:
            self._sink.add(node, f"dangerous builtin call {name!r} is not allowed")
            return
        if name in _DANGEROUS_DYNAMIC_ACCESS_NAMES:
            self._sink.add(node, f"dynamic access {name!r} is not allowed")
            return
        if _is_reference_symbol(name) or name in self._aliases.reference_aliases:
            self._sink.add(node, f"reference/model call {name!r} is not allowed")
            return
        if name in self._aliases.dangerous_aliases:
            self._sink.add(node, f"dangerous builtin alias call {name!r} is not allowed")
            return
        if name in self._aliases.functional_aliases:
            self._sink.add(node, "torch.nn.functional calls are not allowed")
            return
        self._sink.add(node, f"call {name!r} is not allowlisted")

    def _check_bracket_launch(self, node: ast.Call) -> None:
        launch_target = node.func
        if not isinstance(launch_target.value, ast.Name):
            self._sink.add(node, "Triton bracket launch target must be a kernel name")
        elif launch_target.value.id in self._aliases.torch_names:
            self._sink.add(node, "torch objects cannot be used as Triton launch targets")
        elif launch_target.value.id in self._aliases.dangerous_aliases:
            self._sink.add(node, "dangerous builtin aliases cannot be used as Triton launch targets")
        self._check_expr(launch_target.slice)
        self._check_call_arguments(node)

    def _check_call_arguments(self, node: ast.Call) -> None:
        for arg in node.args:
            self._check_expr(arg)
        for keyword in node.keywords:
            if keyword.arg is None:
                self._sink.add(keyword, "starred keyword arguments are not allowlisted")
                continue
            self._check_expr(keyword.value)


def check_level0_ast_sanitizer(source: str) -> Level0AstSanitizerResult:
    """Return a static Level 0 surface-scan result for generated source."""

    sink = _ViolationSink()
    _scan_raw_surface(source, sink)

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        sink.add(exc.lineno, f"SyntaxError: {exc.msg}", failure_code="F0_PARSE")
        return _result_from_violations(sink.deduped(), failure_code="F0_PARSE")

    aliases = _AliasContext.initial()
    _ModuleSurfaceScanner(sink, aliases).visit(tree)
    _check_module_body(tree, sink, aliases)

    return _result_from_violations(sink.deduped())


def scan_generated_code_surface(source: str) -> Level0AstSanitizerResult:
    """Alias for callers that name the folded surface-scan behavior directly."""

    return check_level0_ast_sanitizer(source)


def _check_module_body(
    tree: ast.Module,
    sink: _ViolationSink,
    aliases: _AliasContext,
) -> None:
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.FunctionDef):
            _check_function_decorators(node, sink, aliases)
            if _has_triton_jit_decorator(node, aliases):
                continue
            _LauncherBodyChecker(sink, aliases).check(node)
            continue
        sink.add(node, f"top-level statement {type(node).__name__} is not allowlisted")


def _scan_raw_surface(source: str, sink: _ViolationSink) -> None:
    for line_number, line in enumerate(source.splitlines(), start=1):
        lowered = line.lower()
        if any(pattern.search(lowered) for pattern in _RAW_SURFACE_PATTERNS):
            sink.add(line_number, "timing/profiling/speedup surface is not allowed")


def _result_from_violations(
    violations: tuple[Level0AstViolation, ...],
    failure_code: str | None = None,
) -> Level0AstSanitizerResult:
    if not violations:
        return Level0AstSanitizerResult(safe_success=True, failure_code=None)
    return Level0AstSanitizerResult(
        safe_success=False,
        failure_code=failure_code or F0_SURFACE_VIOLATION,
        violations=violations,
    )


def _has_triton_jit_decorator(node: ast.FunctionDef, aliases: _AliasContext) -> bool:
    for decorator in node.decorator_list:
        if _is_triton_jit_decorator(decorator, aliases):
            return True
    return False


def _check_function_decorators(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    sink: _ViolationSink,
    aliases: _AliasContext,
) -> None:
    for decorator in node.decorator_list:
        if _is_triton_jit_decorator(decorator, aliases):
            if isinstance(decorator, ast.Call) and (decorator.args or decorator.keywords):
                sink.add(decorator, "triton.jit decorator arguments are not allowlisted")
            continue
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        chain = _attribute_chain(target)
        name = chain[-1] if chain else type(decorator).__name__
        sink.add(decorator, f"function decorator {name!r} is not allowlisted")


def _check_function_definition_surfaces(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    sink: _ViolationSink,
) -> None:
    defaults = [
        *node.args.defaults,
        *(default for default in node.args.kw_defaults if default is not None),
    ]
    for default in defaults:
        dangerous_name = _dangerous_builtin_reference_name(default)
        if dangerous_name is not None:
            sink.add(default, f"dangerous builtin default {dangerous_name!r} is not allowed")

    annotations = [
        *(arg.annotation for arg in node.args.posonlyargs if arg.annotation is not None),
        *(arg.annotation for arg in node.args.args if arg.annotation is not None),
        *(arg.annotation for arg in node.args.kwonlyargs if arg.annotation is not None),
        *((node.args.vararg.annotation,) if node.args.vararg and node.args.vararg.annotation else ()),
        *((node.args.kwarg.annotation,) if node.args.kwarg and node.args.kwarg.annotation else ()),
        *((node.returns,) if node.returns is not None else ()),
    ]
    for annotation in annotations:
        dangerous_name = _dangerous_builtin_reference_name(annotation)
        if dangerous_name is not None:
            sink.add(
                annotation,
                f"dangerous builtin annotation {dangerous_name!r} is not allowed",
            )


def _is_triton_jit_decorator(decorator: ast.expr, aliases: _AliasContext) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    chain = _attribute_chain(target)
    return len(chain) == 2 and chain[0] in aliases.triton_names and chain[1] == "jit"


def _assignment_target_names(targets: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            names.update(
                item.id for item in target.elts if isinstance(item, ast.Name)
            )
    return names


def _iter_assignment_bindings(
    targets: list[ast.expr],
    value: ast.expr,
) -> tuple[tuple[set[str], ast.expr], ...]:
    bindings: list[tuple[set[str], ast.expr]] = []
    for target in targets:
        bindings.extend(_iter_target_bindings(target, value))
    return tuple(bindings)


def _iter_target_bindings(
    target: ast.expr,
    value: ast.expr,
) -> tuple[tuple[set[str], ast.expr], ...]:
    if (
        isinstance(target, (ast.Tuple, ast.List))
        and isinstance(value, (ast.Tuple, ast.List))
        and len(target.elts) == len(value.elts)
    ):
        bindings: list[tuple[set[str], ast.expr]] = []
        for target_item, value_item in zip(target.elts, value.elts, strict=True):
            bindings.extend(_iter_target_bindings(target_item, value_item))
        return tuple(bindings)

    target_names = _assignment_target_names([target])
    if not target_names:
        return ()
    return ((target_names, value),)


def _is_valid_assignment_target(target: ast.expr) -> bool:
    if isinstance(target, ast.Name):
        return True
    if isinstance(target, (ast.Tuple, ast.List)):
        return all(isinstance(item, ast.Name) for item in target.elts)
    return False


def _is_allowlisted_subscript_value(node: ast.expr) -> bool:
    if isinstance(node, (ast.Tuple, ast.List)):
        return True
    if isinstance(node, ast.Attribute) and node.attr == "shape":
        return True
    return isinstance(node, ast.Call) and _call_name(node.func) in {
        "size",
        "stride",
    }


def _attribute_chain(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_attribute_chain(node.value), node.attr]
    return []


def _call_chain(node: ast.AST | None) -> list[str]:
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _attribute_chain(node)
    return []


def _call_name(node: ast.AST | None) -> str | None:
    chain = _call_chain(node)
    return chain[-1] if chain else None


def _subscript_root_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Subscript):
        chain = _attribute_chain(node.value)
        if len(chain) == 1:
            return chain[0]
    return None


def _is_torch_reference(chain: list[str], aliases: _AliasContext) -> bool:
    return len(chain) == 1 and chain[0] in aliases.torch_names


def _is_triton_reference(chain: list[str], aliases: _AliasContext) -> bool:
    return len(chain) == 1 and chain[0] in aliases.triton_names


def _is_dangerous_builtin_reference(chain: list[str]) -> bool:
    return len(chain) == 1 and chain[0] in _DANGEROUS_ALIAS_NAMES


def _dangerous_builtin_reference_name(node: ast.AST) -> str | None:
    for child in ast.walk(node):
        chain = _attribute_chain(child)
        if _is_dangerous_builtin_reference(chain):
            return chain[0]
        if chain and chain[0] in _DANGEROUS_BUILTINS_NAMES:
            return chain[0]
    return None


def _is_torch_functional_chain(chain: list[str], aliases: _AliasContext) -> bool:
    if len(chain) >= 4 and chain[0] in aliases.torch_names and chain[1:3] == [
        "nn",
        "functional",
    ]:
        return True
    return bool(chain and chain[0] in aliases.functional_aliases)


def _is_reference_symbol(name: str) -> bool:
    if name in _REFERENCE_CALL_NAMES:
        return True
    lowered = name.lower()
    return any(fragment in lowered for fragment in _REFERENCE_NAME_FRAGMENTS)


def _is_timing_surface_name(name: str) -> bool:
    lowered = name.lower()
    return _contains_timing_surface(lowered)


def _contains_timing_surface(value: str) -> bool:
    lowered = value.lower()
    return any(fragment in lowered for fragment in _TIMING_SURFACE_FRAGMENTS)


def _short_reason(reason: str) -> str:
    return " ".join(reason.split())[:160]
