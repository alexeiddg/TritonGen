"""Cluster 1 boundary checks.

Cluster 1 is limited to grammar-constrained generation and compile acceptance.
Numerical correctness, timing/profiling, and feedback repair loops belong to
later clusters.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from pathlib import Path


# Task 9.1: forbidden patterns that would leak Cluster 2/3 concerns into Cluster 1.
TIMING_HELPERS = {
    "time",
    "time_ns",
    "perf_counter",
    "perf_counter_ns",
    "monotonic",
    "monotonic_ns",
    "process_time",
    "process_time_ns",
    "thread_time",
    "thread_time_ns",
}
TIMEIT_HELPERS = {"timeit", "repeat", "default_timer", "Timer"}
TORCH_PROFILER_MODULES = {
    "torch.profiler",
    "torch.autograd.profiler",
    "torch.cuda.profiler",
}
TORCH_PROFILER_PARENT_MODULES = {"torch.autograd", "torch.cuda"}

FORBIDDEN_PATTERNS: dict[str, str] = {
    "numerical_correctness_allclose": r"\btorch\.allclose\b",
    "numerical_correctness_testing": r"\btorch\.testing\b",
    "numerical_correctness_assert_close": r"\bassert_close\b",
    "triton_benchmark": r"\btriton\.testing\.do_bench\b",
    "torch_profiler": r"\btorch\.(?:profiler|autograd\.profiler|cuda\.profiler)\b",
    "timeit_timing": r"\btimeit\.(?:timeit|repeat|default_timer|Timer)\b",
    "nsight": r"\bnsight\b",
    "ncu": r"\bncu\b",
    "nvml": r"\bnvml\b",
    "pynvml": r"\bpynvml\b",
    "time_measurement": (
        r"\btime\.(?:time|time_ns|perf_counter|perf_counter_ns|monotonic|monotonic_ns|"
        r"process_time|process_time_ns|thread_time|thread_time_ns)\b"
    ),
    "kernelbench_baseline_timing": (
        r"\bbuild_baseline_time_command\b"
        r"|\bgenerate_baseline_time\.py\b"
        r"|\bbaseline[_-]time\b"
        r"|\bbaseline\s+time\b"
    ),
    "kernelbench_eval_command": r"\beval_from_generations\.py\b|\bbuild_eval_command\b",
    "speedup": r"\bspeedup\b",
    "compute_sanitizer": r"\bcompute[-_]sanitizer\b",
    "memcheck": r"\bmemcheck\b",
    "repair_loop": r"\brepair\b",
    "retry_loop": r"\bretry\b",
    "re_prompt_loop": r"\bre_prompt\b",
    "reprompt_loop": r"\breprompt\b",
    "compile_error_feedback_prompt": r"compile\s+error.*prompt|prompt.*compile\s+error",
    "compile_error_identifier_prompt": (
        r"\bprompt\b.*\bcompile_error_(?:type|msg)\b"
        r"|\bcompile_error_(?:type|msg)\b.*\bprompt\b"
    ),
}


def _line_violations(line: str) -> list[tuple[str, str]]:
    return [
        (name, line.strip())
        for name, pattern in FORBIDDEN_PATTERNS.items()
        if re.search(pattern, line, flags=re.IGNORECASE)
    ]


def _source_violations(source: str) -> list[tuple[int, str, str]]:
    violations: list[tuple[int, str, str]] = []

    for line_number, line in enumerate(source.splitlines(), start=1):
        for name, excerpt in _line_violations(line):
            violations.append((line_number, name, excerpt))

    violations.extend(_ast_boundary_violations(source))
    return violations


def _ast_boundary_violations(source: str) -> list[tuple[int, str, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[tuple[int, str, str]] = []
    time_module_aliases: set[str] = set()
    timeit_module_aliases: set[str] = set()
    timeit_helper_aliases: set[str] = set()
    timing_helper_aliases: set[str] = set()
    torch_module_aliases: set[str] = set()
    torch_allclose_aliases: set[str] = set()
    torch_testing_aliases: set[str] = set()
    torch_profiler_aliases: set[str] = set()
    torch_profiler_helper_aliases: set[str] = set()
    torch_profiler_parent_aliases: set[str] = set()
    triton_module_aliases: set[str] = set()
    triton_testing_aliases: set[str] = set()
    benchmark_helper_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "time":
                    time_module_aliases.add(alias.asname or alias.name)
                if alias.name == "timeit":
                    timeit_module_aliases.add(alias.asname or alias.name)
                if alias.name == "torch":
                    torch_module_aliases.add(alias.asname or alias.name)
                if alias.name == "torch.testing":
                    torch_testing_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (node.lineno, "numerical_correctness_testing", _source_excerpt(source, node))
                    )
                if alias.name in TORCH_PROFILER_MODULES:
                    if alias.asname:
                        torch_profiler_aliases.add(alias.asname)
                    else:
                        torch_module_aliases.add("torch")
                    violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))
                if alias.name in TORCH_PROFILER_PARENT_MODULES:
                    if alias.asname:
                        torch_profiler_parent_aliases.add(alias.asname)
                    else:
                        torch_module_aliases.add("torch")
                if alias.name == "triton":
                    triton_module_aliases.add(alias.asname or alias.name)
                if alias.name == "triton.testing":
                    if alias.asname:
                        triton_testing_aliases.add(alias.asname)
                    else:
                        triton_module_aliases.add("triton")

        if isinstance(node, ast.ImportFrom) and node.module == "time":
            for alias in node.names:
                if alias.name == "*":
                    timing_helper_aliases.update(TIMING_HELPERS)
                    violations.append(
                        (node.lineno, "imported_timing_helper", _source_excerpt(source, node))
                    )
                if alias.name in TIMING_HELPERS:
                    timing_helper_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (node.lineno, "imported_timing_helper", _source_excerpt(source, node))
                    )

        if isinstance(node, ast.ImportFrom) and node.module == "timeit":
            for alias in node.names:
                if alias.name == "*":
                    timeit_helper_aliases.update(TIMEIT_HELPERS)
                    violations.append(
                        (node.lineno, "timeit_timing", _source_excerpt(source, node))
                    )
                if alias.name in TIMEIT_HELPERS:
                    timeit_helper_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (node.lineno, "timeit_timing", _source_excerpt(source, node))
                    )

        if isinstance(node, ast.ImportFrom) and node.module == "torch":
            for alias in node.names:
                if alias.name == "*":
                    torch_allclose_aliases.add("allclose")
                    torch_testing_aliases.add("testing")
                    torch_profiler_aliases.add("profiler")
                    violations.append(
                        (
                            node.lineno,
                            "numerical_correctness_allclose",
                            _source_excerpt(source, node),
                        )
                    )
                    violations.append(
                        (node.lineno, "numerical_correctness_testing", _source_excerpt(source, node))
                    )
                    violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))
                if alias.name == "allclose":
                    torch_allclose_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (
                            node.lineno,
                            "numerical_correctness_allclose",
                            _source_excerpt(source, node),
                        )
                    )
                if alias.name == "testing":
                    torch_testing_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (node.lineno, "numerical_correctness_testing", _source_excerpt(source, node))
                    )
                if alias.name == "profiler":
                    torch_profiler_aliases.add(alias.asname or alias.name)
                    violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))
                if alias.name in {"autograd", "cuda"}:
                    torch_profiler_parent_aliases.add(alias.asname or alias.name)

        if isinstance(node, ast.ImportFrom) and node.module == "torch.testing":
            violations.append(
                (node.lineno, "numerical_correctness_testing", _source_excerpt(source, node))
            )

        if isinstance(node, ast.ImportFrom) and node.module in TORCH_PROFILER_MODULES:
            for alias in node.names:
                if alias.name == "*":
                    torch_profiler_helper_aliases.add("profile")
                else:
                    torch_profiler_helper_aliases.add(alias.asname or alias.name)
            violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))

        if isinstance(node, ast.ImportFrom) and node.module in {"torch.autograd", "torch.cuda"}:
            for alias in node.names:
                if alias.name == "*":
                    torch_profiler_aliases.add("profiler")
                    violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))
                if alias.name == "profiler":
                    torch_profiler_aliases.add(alias.asname or alias.name)
                    violations.append((node.lineno, "torch_profiler", _source_excerpt(source, node)))

        if isinstance(node, ast.ImportFrom) and node.module == "triton":
            for alias in node.names:
                if alias.name == "testing":
                    triton_testing_aliases.add(alias.asname or alias.name)

        if isinstance(node, ast.ImportFrom) and node.module == "triton.testing":
            for alias in node.names:
                if alias.name in {"do_bench", "*"}:
                    if alias.name == "do_bench":
                        benchmark_helper_aliases.add(alias.asname or alias.name)
                    violations.append(
                        (
                            node.lineno,
                            "imported_triton_benchmark_helper",
                            _source_excerpt(source, node),
                        )
                    )

    compile_error_aliases = _collect_compile_error_aliases(tree)
    timing_helper_aliases.update(
        _collect_timing_aliases(tree, timing_helper_aliases, time_module_aliases)
    )
    timeit_helper_aliases.update(
        _collect_timeit_aliases(tree, timeit_helper_aliases, timeit_module_aliases)
    )
    (
        torch_allclose_aliases,
        torch_testing_aliases,
        torch_profiler_aliases,
        torch_profiler_helper_aliases,
    ) = _collect_torch_boundary_aliases(
        tree,
        torch_module_aliases,
        torch_allclose_aliases,
        torch_testing_aliases,
        torch_profiler_aliases,
        torch_profiler_helper_aliases,
        torch_profiler_parent_aliases,
    )
    benchmark_helper_aliases.update(
        _collect_benchmark_aliases(
            tree,
            benchmark_helper_aliases,
            triton_testing_aliases,
            triton_module_aliases,
        )
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node)
            if call_name in timing_helper_aliases:
                violations.append(
                    (node.lineno, "timing_helper_call", _source_excerpt(source, node))
                )
            if call_name in timeit_helper_aliases:
                violations.append((node.lineno, "timeit_timing", _source_excerpt(source, node)))

            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in TIMING_HELPERS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in time_module_aliases
            ):
                violations.append(
                    (node.lineno, "timing_helper_call", _source_excerpt(source, node))
                )

            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in TIMEIT_HELPERS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in timeit_module_aliases
            ):
                violations.append((node.lineno, "timeit_timing", _source_excerpt(source, node)))

            for name in _torch_boundary_call_names(
                node,
                torch_module_aliases,
                torch_allclose_aliases,
                torch_testing_aliases,
                torch_profiler_aliases,
                torch_profiler_helper_aliases,
                torch_profiler_parent_aliases,
            ):
                violations.append((node.lineno, name, _source_excerpt(source, node)))

            if _is_benchmark_call(node, benchmark_helper_aliases, triton_testing_aliases, triton_module_aliases):
                violations.append(
                    (node.lineno, "triton_benchmark", _source_excerpt(source, node))
                )

        if _is_generation_compile_loop(node):
            violations.append((node.lineno, "retry_loop", _source_excerpt(source, node)))

        if _assigns_prompt_from_compile_error(node, compile_error_aliases):
            violations.append(
                (node.lineno, "compile_error_identifier_prompt", _source_excerpt(source, node))
            )

        if _passes_compile_error_to_prompt_keyword(node, compile_error_aliases):
            violations.append(
                (node.lineno, "compile_error_identifier_prompt", _source_excerpt(source, node))
            )

        if _passes_compile_error_to_prompt_positional(node, compile_error_aliases):
            violations.append(
                (node.lineno, "compile_error_identifier_prompt", _source_excerpt(source, node))
            )

    return violations


def _collect_timing_aliases(
    tree: ast.AST,
    timing_helper_aliases: set[str],
    time_module_aliases: set[str],
) -> set[str]:
    return _collect_name_aliases(
        tree,
        timing_helper_aliases,
        lambda value, aliases: _is_timing_reference(value, aliases, time_module_aliases),
    )


def _is_timing_reference(
    node: ast.AST,
    timing_helper_aliases: set[str],
    time_module_aliases: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in timing_helper_aliases

    chain = _attribute_chain(node)
    return len(chain) == 2 and chain[0] in time_module_aliases and chain[1] in TIMING_HELPERS


def _collect_timeit_aliases(
    tree: ast.AST,
    timeit_helper_aliases: set[str],
    timeit_module_aliases: set[str],
) -> set[str]:
    return _collect_name_aliases(
        tree,
        timeit_helper_aliases,
        lambda value, aliases: _is_timeit_reference(value, aliases, timeit_module_aliases),
    )


def _is_timeit_reference(
    node: ast.AST,
    timeit_helper_aliases: set[str],
    timeit_module_aliases: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in timeit_helper_aliases

    chain = _attribute_chain(node)
    return len(chain) == 2 and chain[0] in timeit_module_aliases and chain[1] in TIMEIT_HELPERS


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _call_leaf_name(node: ast.Call) -> str | None:
    chain = _attribute_chain(node.func)
    return chain[-1] if chain else None


def _is_generation_compile_loop(node: ast.AST) -> bool:
    if not isinstance(node, ast.For | ast.While):
        return False

    has_generation = False
    has_compile_validation = False
    for statement in [*node.body, *node.orelse]:
        for child in ast.walk(statement):
            if not isinstance(child, ast.Call):
                continue
            name = _call_leaf_name(child)
            if name in {"generate", "generate_source", "run_one_generation"}:
                has_generation = True
            if name in {"check_compiles", "check_compiles_all_dtypes", "compile_check"}:
                has_compile_validation = True

    return has_generation and has_compile_validation


def _is_benchmark_call(
    node: ast.Call,
    benchmark_helper_aliases: set[str],
    triton_testing_aliases: set[str],
    triton_module_aliases: set[str],
) -> bool:
    if _call_name(node) in benchmark_helper_aliases:
        return True

    chain = _attribute_chain(node.func)
    if len(chain) == 2 and chain[0] in triton_testing_aliases and chain[1] == "do_bench":
        return True
    return len(chain) == 3 and chain[0] in triton_module_aliases and chain[1:] == [
        "testing",
        "do_bench",
    ]


def _collect_name_aliases(
    tree: ast.AST,
    initial_aliases: set[str],
    is_reference: Callable[[ast.AST, set[str]], bool],
) -> set[str]:
    aliases = set(initial_aliases)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_reference(node.value, aliases):
                for target in node.targets:
                    for name in _target_names(target):
                        if name not in aliases:
                            aliases.add(name)
                            changed = True

            if (
                isinstance(node, ast.AnnAssign)
                and node.value is not None
                and is_reference(node.value, aliases)
            ):
                for name in _target_names(node.target):
                    if name not in aliases:
                        aliases.add(name)
                        changed = True
    return aliases


def _collect_benchmark_aliases(
    tree: ast.AST,
    benchmark_helper_aliases: set[str],
    triton_testing_aliases: set[str],
    triton_module_aliases: set[str],
) -> set[str]:
    aliases = set(benchmark_helper_aliases)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _is_benchmark_reference(
                node.value, aliases, triton_testing_aliases, triton_module_aliases
            ):
                for target in node.targets:
                    for name in _target_names(target):
                        if name not in aliases:
                            aliases.add(name)
                            changed = True

            if (
                isinstance(node, ast.AnnAssign)
                and node.value is not None
                and _is_benchmark_reference(
                    node.value, aliases, triton_testing_aliases, triton_module_aliases
                )
            ):
                for name in _target_names(node.target):
                    if name not in aliases:
                        aliases.add(name)
                        changed = True
    return aliases


def _is_benchmark_reference(
    node: ast.AST,
    benchmark_helper_aliases: set[str],
    triton_testing_aliases: set[str],
    triton_module_aliases: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in benchmark_helper_aliases

    chain = _attribute_chain(node)
    if len(chain) == 2 and chain[0] in triton_testing_aliases and chain[1] == "do_bench":
        return True
    return len(chain) == 3 and chain[0] in triton_module_aliases and chain[1:] == [
        "testing",
        "do_bench",
    ]


def _collect_torch_boundary_aliases(
    tree: ast.AST,
    torch_module_aliases: set[str],
    torch_allclose_aliases: set[str],
    torch_testing_aliases: set[str],
    torch_profiler_aliases: set[str],
    torch_profiler_helper_aliases: set[str],
    torch_profiler_parent_aliases: set[str],
) -> tuple[set[str], set[str], set[str], set[str]]:
    allclose_aliases = set(torch_allclose_aliases)
    testing_aliases = set(torch_testing_aliases)
    profiler_aliases = set(torch_profiler_aliases)
    profiler_helper_aliases = set(torch_profiler_helper_aliases)
    changed = True

    while changed:
        changed = False
        for node in ast.walk(tree):
            targets: list[ast.AST]
            value: ast.AST | None
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            else:
                continue

            reference_names = _torch_boundary_reference_names(
                value,
                torch_module_aliases,
                allclose_aliases,
                testing_aliases,
                profiler_aliases,
                profiler_helper_aliases,
                torch_profiler_parent_aliases,
            )
            if not reference_names:
                continue

            for target in targets:
                for name in _target_names(target):
                    if "allclose" in reference_names and name not in allclose_aliases:
                        allclose_aliases.add(name)
                        changed = True
                    if "testing" in reference_names and name not in testing_aliases:
                        testing_aliases.add(name)
                        changed = True
                    if "profiler" in reference_names and name not in profiler_aliases:
                        profiler_aliases.add(name)
                        changed = True
                    if "profiler_helper" in reference_names and name not in profiler_helper_aliases:
                        profiler_helper_aliases.add(name)
                        changed = True

    return allclose_aliases, testing_aliases, profiler_aliases, profiler_helper_aliases


def _torch_boundary_reference_names(
    node: ast.AST,
    torch_module_aliases: set[str],
    torch_allclose_aliases: set[str],
    torch_testing_aliases: set[str],
    torch_profiler_aliases: set[str],
    torch_profiler_helper_aliases: set[str],
    torch_profiler_parent_aliases: set[str],
) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Name):
        if node.id in torch_allclose_aliases:
            names.add("allclose")
        if node.id in torch_testing_aliases:
            names.add("testing")
        if node.id in torch_profiler_aliases:
            names.add("profiler")
        if node.id in torch_profiler_helper_aliases:
            names.add("profiler_helper")
        return names

    chain = _attribute_chain(node)
    if not chain:
        return names

    if chain[0] in torch_module_aliases and len(chain) >= 2:
        if chain[1] == "allclose":
            names.add("allclose")
        if chain[1] == "testing":
            names.add("testing")
        if "profiler" in chain[1:]:
            if chain[-1] == "profiler":
                names.add("profiler")
            else:
                names.add("profiler_helper")

    if chain[0] in torch_profiler_parent_aliases and "profiler" in chain[1:]:
        if chain[-1] == "profiler":
            names.add("profiler")
        else:
            names.add("profiler_helper")

    if chain[0] in torch_testing_aliases:
        names.add("testing")
    if chain[0] in torch_profiler_aliases:
        if len(chain) == 1:
            names.add("profiler")
        else:
            names.add("profiler_helper")
    if chain[0] in torch_profiler_helper_aliases:
        names.add("profiler_helper")
    return names


def _torch_boundary_call_names(
    node: ast.Call,
    torch_module_aliases: set[str],
    torch_allclose_aliases: set[str],
    torch_testing_aliases: set[str],
    torch_profiler_aliases: set[str],
    torch_profiler_helper_aliases: set[str],
    torch_profiler_parent_aliases: set[str],
) -> list[str]:
    names: list[str] = []
    call_name = _call_name(node)
    if call_name in torch_allclose_aliases:
        names.append("numerical_correctness_allclose")
    if call_name in torch_profiler_helper_aliases:
        names.append("torch_profiler")

    chain = _attribute_chain(node.func)
    if not chain:
        return names

    if chain[0] in torch_module_aliases and len(chain) >= 2:
        if chain[1] == "allclose":
            names.append("numerical_correctness_allclose")
        if chain[1] == "testing":
            names.append("numerical_correctness_testing")
        if "profiler" in chain[1:]:
            names.append("torch_profiler")

    if chain[0] in torch_profiler_parent_aliases and "profiler" in chain[1:]:
        names.append("torch_profiler")

    if chain[0] in torch_testing_aliases:
        names.append("numerical_correctness_testing")
    if chain[0] in torch_profiler_aliases:
        names.append("torch_profiler")
    return names


def _attribute_chain(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [*_attribute_chain(node.value), node.attr]
    return []


def _passes_compile_error_to_prompt_keyword(node: ast.AST, aliases: set[str] | None = None) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return any(
        keyword.arg == "prompt"
        and keyword.value is not None
        and _contains_compile_error(keyword.value, aliases)
        for keyword in node.keywords
    )


def _passes_compile_error_to_prompt_positional(node: ast.AST, aliases: set[str] | None = None) -> bool:
    if not isinstance(node, ast.Call) or not node.args:
        return False
    return _call_takes_prompt_first(node) and _contains_compile_error(node.args[0], aliases)


def _call_takes_prompt_first(node: ast.Call) -> bool:
    chain = _attribute_chain(node.func)
    if not chain:
        return False
    name = chain[-1].lower()
    return name in {"generate", "generate_source"} or "prompt" in name


def _assigns_prompt_from_compile_error(node: ast.AST, aliases: set[str] | None = None) -> bool:
    if isinstance(node, ast.Assign):
        return any(_target_is_prompt(target) for target in node.targets) and _contains_compile_error(
            node.value, aliases
        )
    if isinstance(node, ast.AnnAssign):
        return (
            _target_is_prompt(node.target)
            and node.value is not None
            and _contains_compile_error(node.value, aliases)
        )
    if isinstance(node, ast.AugAssign):
        return _target_is_prompt(node.target) and _contains_compile_error(node.value, aliases)
    return False


def _collect_compile_error_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _contains_compile_error(node.value, aliases):
                for target in node.targets:
                    for name in _target_names(target):
                        if name not in aliases:
                            aliases.add(name)
                            changed = True

            if (
                isinstance(node, ast.AnnAssign)
                and node.value is not None
                and _contains_compile_error(node.value, aliases)
            ):
                for name in _target_names(node.target):
                    if name not in aliases:
                        aliases.add(name)
                        changed = True

            if isinstance(node, ast.AugAssign) and _contains_compile_error(node.value, aliases):
                for name in _target_names(node.target):
                    if name not in aliases:
                        aliases.add(name)
                        changed = True
    return aliases


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, ast.Tuple | ast.List):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_names(element))
        return names
    return set()


def _target_is_prompt(target: ast.AST) -> bool:
    if isinstance(target, ast.Name):
        return target.id == "prompt"
    if isinstance(target, ast.Attribute):
        return target.attr == "prompt"
    if isinstance(target, ast.Tuple | ast.List):
        return any(_target_is_prompt(element) for element in target.elts)
    return False


def _contains_compile_error(node: ast.AST, aliases: set[str] | None = None) -> bool:
    aliases = aliases or set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if _is_compile_error_literal(child.value):
                return True
        if (
            isinstance(child, ast.Name)
            and child.id
            in {"compile_error_type", "compile_error_msg", "error_type", "error_msg", *aliases}
        ):
            return True
        if (
            isinstance(child, ast.Attribute)
            and child.attr in {"compile_error_type", "compile_error_msg", "error_type", "error_msg"}
        ):
            return True
    return False


def _is_compile_error_literal(value: str) -> bool:
    return re.search(r"\bcompile[-_\s]+error\b", value, flags=re.IGNORECASE) is not None


def _source_excerpt(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is None:
        lines = source.splitlines()
        line_number = getattr(node, "lineno", 1)
        segment = lines[line_number - 1] if 0 < line_number <= len(lines) else ""
    return " ".join(segment.split())[:200]


def test_compile_error_identifiers_are_forbidden_in_prompt_paths() -> None:
    bad_lines = [
        "prompt += result.compile_error_msg",
        "prompt = f'{prompt}\\n{row.compile_error_type}'",
        "prompt += first_error.error_msg",
        "prompt = build_prompt() + result.error_type",
    ]

    for line in bad_lines:
        names = [name for _, name, _ in _source_violations(line)]
        assert "compile_error_identifier_prompt" in names


def test_multiline_compile_error_identifier_prompt_is_forbidden() -> None:
    source = """\
def build_next_prompt(result):
    prompt = (
        build_prompt()
        + result.compile_error_msg
    )
    return prompt
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_multiline_compile_error_literal_prompt_is_forbidden() -> None:
    source = """\
def build_next_prompt(error_text):
    prompt = (
        build_prompt()
        + "\\nprevious compile error:\\n"
        + error_text
    )
    return prompt
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_compile_error_identifier_prompt_keyword_is_forbidden() -> None:
    source = """\
def run(result):
    return generate_source(
        prompt=(
            build_prompt()
            + result.compile_error_msg
        ),
        model=model,
    )
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_generic_compile_result_error_prompt_keyword_is_forbidden() -> None:
    source = """\
def run(result):
    return generate_source(
        prompt=build_prompt() + result.error_type,
        model=model,
    )
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_compile_error_identifier_positional_prompt_is_forbidden() -> None:
    source = """\
def run(result):
    return generate_source(
        build_prompt()
        + result.compile_error_msg,
        model=model,
    )
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_compile_error_alias_prompt_feedback_is_forbidden() -> None:
    source = """\
def run(result):
    feedback = result.compile_error_msg
    prompt = build_prompt()
    prompt += feedback
    return prompt
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compile_error_identifier_prompt" in names


def test_imported_timing_helpers_are_forbidden() -> None:
    direct_import_source = """\
from time import monotonic

elapsed = monotonic()
"""
    alias_source = """\
import time as clock

elapsed = clock.process_time()
"""

    direct_names = [name for _, name, _ in _source_violations(direct_import_source)]
    alias_names = [name for _, name, _ in _source_violations(alias_source)]
    assert "imported_timing_helper" in direct_names
    assert "timing_helper_call" in direct_names
    assert "timing_helper_call" in alias_names


def test_star_imported_timing_helpers_are_forbidden() -> None:
    source = """\
from time import *

elapsed = perf_counter()
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "imported_timing_helper" in names
    assert "timing_helper_call" in names


def test_timeit_timing_helpers_are_forbidden() -> None:
    module_source = """\
import timeit

elapsed = timeit.default_timer()
duration = timeit.timeit(fn)
samples = timeit.Timer(fn).repeat(3, 1)
"""
    helper_source = """\
from timeit import Timer, repeat

samples = repeat(fn)
duration = Timer(fn).timeit(1)
"""

    module_names = [name for _, name, _ in _source_violations(module_source)]
    helper_names = [name for _, name, _ in _source_violations(helper_source)]
    assert "timeit_timing" in module_names
    assert "timeit_timing" in helper_names


def test_local_timing_helper_aliases_are_forbidden() -> None:
    time_source = """\
import time as clock

timer = clock.perf_counter
elapsed = timer()
"""
    timeit_source = """\
import timeit as timings

timer = timings.default_timer
elapsed = timer()
"""

    time_names = [name for _, name, _ in _source_violations(time_source)]
    timeit_names = [name for _, name, _ in _source_violations(timeit_source)]
    assert "timing_helper_call" in time_names
    assert "timeit_timing" in timeit_names


def test_generation_compile_retry_loop_is_forbidden() -> None:
    source = """\
for attempt in range(3):
    source = generate_source(prompt)
    results = check_compiles_all_dtypes(source)
    if all(result.compiles for result in results):
        break
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "retry_loop" in names


def test_imported_triton_benchmark_helpers_are_forbidden() -> None:
    helper_import_source = """\
from triton.testing import do_bench

latency = do_bench(fn)
"""
    testing_alias_source = """\
import triton.testing as tt

latency = tt.do_bench(fn)
"""
    triton_alias_source = """\
import triton as tr

latency = tr.testing.do_bench(fn)
"""
    unaliased_testing_source = """\
import triton.testing

latency = (
    triton.testing
    .do_bench(fn)
)
"""

    helper_names = [name for _, name, _ in _source_violations(helper_import_source)]
    testing_alias_names = [name for _, name, _ in _source_violations(testing_alias_source)]
    triton_alias_names = [name for _, name, _ in _source_violations(triton_alias_source)]
    unaliased_testing_names = [
        name for _, name, _ in _source_violations(unaliased_testing_source)
    ]
    assert "imported_triton_benchmark_helper" in helper_names
    assert "triton_benchmark" in helper_names
    assert "triton_benchmark" in testing_alias_names
    assert "triton_benchmark" in triton_alias_names
    assert "triton_benchmark" in unaliased_testing_names


def test_local_triton_benchmark_alias_is_forbidden() -> None:
    source = """\
import triton.testing as tt

bench = tt.do_bench
latency = bench(fn)
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "triton_benchmark" in names


def test_torch_alias_boundary_calls_are_forbidden() -> None:
    source = """\
import torch as th

same = th.allclose(a, b)
with th.profiler.profile() as prof:
    pass
th.testing.assert_close(a, b)
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "numerical_correctness_allclose" in names
    assert "torch_profiler" in names
    assert "numerical_correctness_testing" in names


def test_local_torch_boundary_aliases_are_forbidden() -> None:
    source = """\
import torch as th

close = th.allclose
profile = th.profiler.profile
compare = th.testing.assert_close

same = close(a, b)
with profile() as prof:
    pass
compare(a, b)
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "numerical_correctness_allclose" in names
    assert "torch_profiler" in names
    assert "numerical_correctness_testing" in names


def test_torch_star_import_boundary_calls_are_forbidden() -> None:
    source = """\
from torch import *

same = allclose(a, b)
testing.assert_close(a, b)
with profiler.profile() as prof:
    pass
"""

    violations = {(line_number, name) for line_number, name, _ in _source_violations(source)}
    assert (3, "numerical_correctness_allclose") in violations
    assert (4, "numerical_correctness_testing") in violations
    assert (5, "torch_profiler") in violations


def test_nested_torch_profiler_imports_are_forbidden() -> None:
    sources = [
        (
            """\
from torch.autograd.profiler import profile

with profile() as prof:
    pass
""",
            3,
        ),
        (
            """\
import torch.cuda.profiler as cp

with cp.profile() as prof:
    pass
""",
            3,
        ),
        (
            """\
from torch.cuda import profiler as cp

with cp.profile() as prof:
    pass
""",
            3,
        ),
        (
            """\
from torch import cuda

with cuda.profiler.profile() as prof:
    pass
""",
            3,
        ),
        (
            """\
import torch.autograd as autograd

with autograd.profiler.profile() as prof:
    pass
""",
            3,
        ),
        (
            """\
from torch import cuda as tc

profile = tc.profiler.profile
with profile() as prof:
    pass
""",
            4,
        ),
    ]

    for source, line_number in sources:
        violations = {(line_number, name) for line_number, name, _ in _source_violations(source)}
        assert (line_number, "torch_profiler") in violations


def test_nested_torch_profiler_calls_are_forbidden() -> None:
    source = """\
import torch as th

with th.autograd.profiler.profile() as prof:
    pass
with th.cuda.profiler.profile() as prof:
    pass
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert names.count("torch_profiler") == 2


def test_kernelbench_baseline_timing_command_is_forbidden() -> None:
    source = """\
def build_command(root):
    return [
        str(root / "scripts" / "generate_baseline_time.py"),
    ]
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "kernelbench_baseline_timing" in names


def test_kernelbench_eval_command_is_forbidden() -> None:
    source = """\
def build_command(root):
    return [
        str(root / "scripts" / "eval_from_generations.py"),
    ]
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "kernelbench_eval_command" in names


def test_memcheck_tools_are_forbidden() -> None:
    source = """\
cmd = ["compute-sanitizer", "--tool", "memcheck", "python", "kernel.py"]
"""

    names = [name for _, name, _ in _source_violations(source)]
    assert "compute_sanitizer" in names
    assert "memcheck" in names


def test_no_cluster_boundary_violations() -> None:
    """Fail if Cluster 1 active Python code crosses its contract boundary."""
    cluster_root = Path(__file__).resolve().parents[1]
    this_file = Path(__file__).resolve()
    violations: list[str] = []

    for path in sorted(cluster_root.rglob("*.py")):
        resolved = path.resolve()
        if resolved == this_file:
            continue

        source = path.read_text(encoding="utf-8")
        for line_number, name, excerpt in _source_violations(source):
            rel_path = path.relative_to(cluster_root.parent)
            violations.append(f"{rel_path}:{line_number}: {name}: {excerpt}")

    assert not violations, "Cluster boundary violations found:\n" + "\n".join(violations)
