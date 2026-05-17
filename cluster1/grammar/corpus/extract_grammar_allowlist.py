"""Extract the task-agnostic Triton language allow-list from the GBNF grammar.

This script is intentionally offline-only. It reads the checked-in GBNF file and
emits a structured JSON snapshot of the `tl.*` call surface encoded by the
grammar. It does not import Triton, execute kernels, or inspect tutorial
fixtures.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


EXTRACTION_VERSION = "2026-05-16.3"
DEFAULT_GRAMMAR = Path("cluster1/grammar/triton_kernel_agnostic.gbnf")
DEFAULT_OUTPUT = Path("cluster1/grammar/corpus/grammar_allowlist_extracted.json")

_GBNF_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
_TL_CALL_LITERAL_RE = re.compile(r'"tl\.([A-Za-z_][A-Za-z0-9_]*)\(')
_TL_NAME_LITERAL_RE = re.compile(r'"tl\.([A-Za-z_][A-Za-z0-9_]*)"')
_LITERAL_KWARG_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=")

_CONTEXT_ROOTS = {
    "expressions": "triton-value-call",
    "statements": "triton-call-stmt",
    "for_iterators": "range-call",
    "decorators": "decorator-block",
    "launch_context": "bracket-launch-stmt",
}

_LOCAL_TRAVERSAL_STOP = {
    "kernel-expr",
    "kernel-bool-or-expr",
    "kernel-bool-and-expr",
    "kernel-bitwise-expr",
    "kernel-comparison-expr",
    "kernel-add-expr",
    "kernel-mul-expr",
    "kernel-unary-expr",
    "kernel-primary",
    "kernel-primary-base",
    "kernel-atom",
    "kernel-atom-postfix",
    "kernel-subscript-content",
    "kernel-subscript-item",
    "kernel-slice-content",
    "kernel-var-arg-list",
    "kernel-call-arg-list",
    "kernel-keyword-arg-list",
    "kernel-keyword-arg",
    "kernel-tuple-expr",
    "kernel-list-expr",
    "kernel-paren-expr",
    "kernel-shape-tuple",
    "literal",
    "int-literal",
    "float-literal",
    "none-literal",
    "ident",
    "target",
}

_ARG_VALUE_RULES = {
    "bool-literal",
    "dtype",
    "float-literal",
    "ident",
    "int-literal",
    "kernel-expr",
    "kernel-list-expr",
    "kernel-shape-tuple",
    "none-literal",
    "program-id-axis",
    "reduction-axis-arg",
    "str-literal",
}
_VAR_ARG_RULES = {"kernel-var-arg-list"}
_EXPANDABLE_ARITY_REFS = {
    "tl-range-arg-list",
    "tl-range-positional-args",
    "tl-static-range-arg-list",
    "tl-static-range-positional-args",
}


def extract_allowlist(grammar_path: Path) -> dict[str, Any]:
    grammar_path = Path(grammar_path)
    gbnf_text = grammar_path.read_text(encoding="utf-8")
    productions = _collect_gbnf_productions(gbnf_text)
    graph = _build_reference_graph(productions)
    reachable_by_context = {
        context: _reachable_rules(root, graph)
        for context, root in _CONTEXT_ROOTS.items()
        if root in productions
    }
    names_by_rule = _extract_tl_names_by_rule(productions)
    direct_calls_by_rule = _extract_direct_tl_calls_by_rule(productions)

    call_rules_by_name: dict[str, set[str]] = defaultdict(set)
    for rule, names in direct_calls_by_rule.items():
        for name in names:
            call_rules_by_name[f"tl.{name}"].add(rule)

    for name_rule, names in names_by_rule.items():
        for rule, rhs in productions.items():
            if name_rule in _iter_gbnf_references(rhs) and "(" in rhs:
                for name in names:
                    call_rules_by_name[f"tl.{name}"].add(rule)

    functions: list[dict[str, Any]] = []
    for full_name in sorted(call_rules_by_name):
        rules = sorted(call_rules_by_name[full_name])
        allowed_kwargs = sorted(_literal_kwargs_for_function(full_name, rules, productions, names_by_rule))
        contexts = sorted(
            context
            for context, reachable in reachable_by_context.items()
            if any(rule in reachable for rule in rules)
        )
        restrictions = _restrictions_for_function(full_name, rules, productions, names_by_rule, allowed_kwargs)

        functions.append(
            {
                "name": full_name,
                "grammar_rules": rules,
                "allowed_arities": _derive_allowed_arities(full_name, rules, productions, names_by_rule),
                "allowed_kwargs": allowed_kwargs,
                "restrictions": restrictions,
                "contexts": contexts,
                "notes": _notes_for_function(full_name, allowed_kwargs),
            }
        )

    return {
        "source_file": str(grammar_path),
        "extraction_version": EXTRACTION_VERSION,
        "functions": functions,
    }


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
            if not _GBNF_NAME_RE.fullmatch(name):
                raise ValueError(f"invalid production name at line {lineno}: {name!r}")
            productions[name] = [rhs_part.strip()]
            current_name = name
            continue
        if current_name is None:
            raise ValueError(f"continuation without production at line {lineno}")
        productions[current_name].append(line.strip())
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


def _extract_tl_names_by_rule(productions: dict[str, str]) -> dict[str, set[str]]:
    return {
        rule: set(_TL_NAME_LITERAL_RE.findall(rhs))
        for rule, rhs in productions.items()
        if rule.endswith("-name") and _TL_NAME_LITERAL_RE.search(rhs)
    }


def _extract_direct_tl_calls_by_rule(productions: dict[str, str]) -> dict[str, set[str]]:
    return {
        rule: set(_TL_CALL_LITERAL_RE.findall(rhs))
        for rule, rhs in productions.items()
        if _TL_CALL_LITERAL_RE.search(rhs)
    }


def _build_reference_graph(productions: dict[str, str]) -> dict[str, set[str]]:
    return {name: set(_iter_gbnf_references(rhs)) & set(productions) for name, rhs in productions.items()}


def _iter_gbnf_references(rhs: str) -> set[str]:
    stripped = _blank_gbnf_literals(rhs)
    return set(_GBNF_NAME_RE.findall(stripped))


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


def _reachable_rules(root: str, graph: dict[str, set[str]]) -> set[str]:
    visited: set[str] = set()
    queue = deque([root])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(sorted(graph.get(current, set()) - visited))
    return visited


def _literal_kwargs_for_function(
    full_name: str,
    rules: list[str],
    productions: dict[str, str],
    names_by_rule: dict[str, set[str]],
) -> set[str]:
    kwargs: set[str] = set()
    for rule in rules:
        for alternative in _split_top_level_alternatives(productions[rule]):
            if not _alternative_mentions_function(alternative, full_name, names_by_rule):
                continue
            kwargs |= _literal_kwargs_for_alternative(alternative, productions)
    return kwargs


def _literal_kwargs_for_alternative(alternative: str, productions: dict[str, str]) -> set[str]:
    kwargs: set[str] = set()
    kwargs |= _literal_kwargs_in_text(alternative)
    for ref in _iter_gbnf_references(alternative):
        if ref in _LOCAL_TRAVERSAL_STOP:
            continue
        for reachable_rule in _local_reachable_rules(ref, productions):
            kwargs |= _literal_kwargs_in_text(productions[reachable_rule])
            if "kernel-keyword-arg" in _iter_gbnf_references(productions[reachable_rule]):
                kwargs.add("<generic-ident>")
    return kwargs


def _derive_allowed_arities(
    full_name: str,
    rules: list[str],
    productions: dict[str, str],
    names_by_rule: dict[str, set[str]],
) -> list[str]:
    arities: set[str] = set()
    for rule in rules:
        for alternative in _split_top_level_alternatives(productions[rule]):
            if not _alternative_mentions_function(alternative, full_name, names_by_rule):
                continue
            for expanded in _expand_arity_references(alternative, productions):
                arities |= _arity_forms_for_alternative(expanded, productions)
    return sorted(arities, key=_arity_sort_key) or ["unclassified"]


def _alternative_mentions_function(
    alternative: str,
    full_name: str,
    names_by_rule: dict[str, set[str]],
) -> bool:
    direct_names = {f"tl.{name}" for name in _TL_CALL_LITERAL_RE.findall(alternative)}
    if direct_names:
        return full_name in direct_names
    alternative_refs = _iter_gbnf_references(alternative)
    return any(
        full_name in {f"tl.{name}" for name in names} and name_rule in alternative_refs
        for name_rule, names in names_by_rule.items()
    )


def _expand_arity_references(alternative: str, productions: dict[str, str]) -> set[str]:
    expanded = {alternative}
    changed = True
    while changed:
        changed = False
        next_expanded: set[str] = set()
        for item in expanded:
            ref = next((candidate for candidate in _EXPANDABLE_ARITY_REFS if candidate in _iter_gbnf_references(item)), None)
            if ref is None:
                next_expanded.add(item)
                continue
            changed = True
            for replacement in _split_top_level_alternatives(productions[ref]):
                next_expanded.add(re.sub(rf"\b{re.escape(ref)}\b", replacement, item, count=1))
        expanded = next_expanded
    return expanded


def _arity_forms_for_alternative(alternative: str, productions: dict[str, str]) -> set[str]:
    positional_count = 0
    vararg_min = 0
    explicit_kwargs: list[str] = []
    optional_specific_kwargs: list[str] = []
    keyword_list = False
    optional_kw_group = False
    pending_keyword = ""
    tokens = _tokenize_gbnf(alternative)

    for index, (kind, value) in enumerate(tokens):
        if kind == "literal":
            literal_kwargs = _LITERAL_KWARG_RE.findall(value)
            if literal_kwargs:
                pending_keyword = literal_kwargs[-1]
                for kwarg in literal_kwargs:
                    if kwarg not in explicit_kwargs:
                        explicit_kwargs.append(kwarg)
            continue
        if kind != "ref":
            continue

        next_is_optional = index + 1 < len(tokens) and tokens[index + 1] == ("symbol", "?")
        if value.endswith("keyword-arg-list"):
            keyword_list = True
        elif value.endswith("kwargs") or value.endswith("multiline-kwargs"):
            optional_kw_group = optional_kw_group or next_is_optional
            keyword_list = keyword_list or not next_is_optional
        elif value in productions and next_is_optional:
            for kwarg in sorted(_literal_kwargs_for_alternative(productions[value], productions)):
                if kwarg not in optional_specific_kwargs:
                    optional_specific_kwargs.append(kwarg)
        elif value in _VAR_ARG_RULES:
            vararg_min += 1
        elif value in _ARG_VALUE_RULES:
            if pending_keyword:
                pending_keyword = ""
            else:
                positional_count += 1
        elif value in productions and "kernel-keyword-arg" in _iter_gbnf_references(productions[value]):
            keyword_list = True

    base = f"{positional_count + vararg_min}+" if vararg_min else str(positional_count)
    forms: set[str] = set()
    if optional_kw_group:
        forms.add(base)
        forms.add(_append_arity_suffix(base, "kwargs"))
    elif keyword_list:
        forms.add("keyword-list" if base == "0" else _append_arity_suffix(base, "kwargs"))
    elif explicit_kwargs:
        required_form = _arity_with_explicit_kwargs(base, explicit_kwargs)
        forms.add(required_form)
        if optional_specific_kwargs:
            forms.add(_append_arity_suffix(required_form, "+".join(optional_specific_kwargs)))
    elif optional_specific_kwargs:
        forms.add(base)
        forms.add(_append_arity_suffix(base, "+".join(optional_specific_kwargs)))
    else:
        forms.add(base)
    return forms


def _arity_with_explicit_kwargs(base: str, explicit_kwargs: list[str]) -> str:
    if base == "0":
        return f"{explicit_kwargs[0]}=1" if len(explicit_kwargs) == 1 else "keyword-only"
    return _append_arity_suffix(base, "+".join(explicit_kwargs))


def _append_arity_suffix(base: str, suffix: str) -> str:
    return f"{base}{suffix}" if base.endswith("+") else f"{base}+{suffix}"


def _arity_sort_key(form: str) -> tuple[int, int, int, str]:
    if form == "unclassified":
        return (9, 0, 0, form)
    if form in {"keyword-only", "keyword-list"}:
        return (8, 0, 0 if form == "keyword-only" else 1, form)
    match = re.match(r"^(\d+)(\+?)", form)
    if match:
        return (0, int(match.group(1)), 1 if match.group(2) else 0, form)
    return (1, 0, 0, form)


def _restrictions_for_function(
    full_name: str,
    rules: list[str],
    productions: dict[str, str],
    names_by_rule: dict[str, set[str]],
    allowed_kwargs: list[str],
) -> list[str]:
    reachable: set[str] = set()
    for rule in rules:
        for alternative in _split_top_level_alternatives(productions[rule]):
            if not _alternative_mentions_function(alternative, full_name, names_by_rule):
                continue
            for ref in _iter_gbnf_references(alternative):
                if ref not in _LOCAL_TRAVERSAL_STOP:
                    reachable |= _local_reachable_rules(ref, productions)

    reachable_text = " ".join(productions[rule] for rule in sorted(reachable))
    restrictions: list[str] = []
    if "program-id-axis" in reachable:
        restrictions.append("program-id axis grammar restricts values to literal 0, 1, or 2")
    if "dtype" in reachable:
        restrictions.append("dtype arguments are restricted to the dtype production")
    if "str-literal" in reachable:
        restrictions.append("string-valued parameters must be string literals")
    if "bool-literal" in reachable:
        restrictions.append("boolean-valued parameters must be True or False literals")
    if "kernel-call-arg-list" in reachable_text or "<generic-ident>" in allowed_kwargs:
        restrictions.append("generic kernel call argument list accepts arbitrary identifier keywords")
    if full_name == "tl.range":
        restrictions.append(
            "iterator keyword support is split by positional count: arg2 is accepted only before "
            "the second positional argument, step only before the third positional argument, and "
            "compiler loop kwargs remain available after documented positional forms"
        )
    if full_name == "tl.static_range":
        restrictions.append(
            "iterator keyword support is split by positional count: arg2 is accepted only before "
            "the second positional argument and step only before the third positional argument"
        )
    if not restrictions:
        restrictions.append("arguments are restricted to grammar-level kernel expressions or literals")
    return restrictions


def _split_top_level_alternatives(rhs: str) -> list[str]:
    alternatives: list[str] = []
    start = 0
    in_string = False
    in_class = False
    quote = ""
    escaped = False
    for index, char in enumerate(rhs):
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
        if char == "|":
            alternatives.append(rhs[start:index].strip())
            start = index + 1
    alternatives.append(rhs[start:].strip())
    return [alternative for alternative in alternatives if alternative]


def _literal_kwargs_in_text(text: str) -> set[str]:
    kwargs: set[str] = set()
    for literal in _iter_gbnf_string_literals(text):
        kwargs |= set(_LITERAL_KWARG_RE.findall(literal))
    return kwargs


def _iter_gbnf_string_literals(text: str) -> list[str]:
    literals: list[str] = []
    in_string = False
    quote = ""
    escaped = False
    current: list[str] = []
    for char in text:
        if escaped:
            if in_string:
                current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_string:
            if char == quote:
                literals.append("".join(current))
                current = []
                in_string = False
            else:
                current.append(char)
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
    return literals


def _tokenize_gbnf(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char in {"?", "*", "+", "(", ")"}:
            tokens.append(("symbol", char))
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            literal: list[str] = []
            escaped = False
            while index < len(text):
                current = text[index]
                index += 1
                if escaped:
                    literal.append(current)
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    break
                else:
                    literal.append(current)
            tokens.append(("literal", "".join(literal)))
            continue
        if char == "[":
            index += 1
            while index < len(text) and text[index] != "]":
                index += 1
            index += 1
            continue
        match = _GBNF_NAME_RE.match(text, index)
        if match:
            tokens.append(("ref", match.group(0)))
            index = match.end()
            continue
        index += 1
    return tokens


def _local_reachable_rules(root: str, productions: dict[str, str]) -> set[str]:
    graph = _build_reference_graph(productions)
    visited: set[str] = set()
    queue = deque([root])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for ref in sorted(graph.get(current, set())):
            if ref in _LOCAL_TRAVERSAL_STOP:
                continue
            queue.append(ref)
    return visited


def _notes_for_function(name: str, allowed_kwargs: list[str]) -> str:
    if "<generic-ident>" in allowed_kwargs:
        return "Iterator call currently delegates to the generic kernel-call-arg-list production."
    if name in {"tl.store", "tl.store_tensor_descriptor", "tl.device_print", "tl.device_assert", "tl.static_print", "tl.static_assert", "tl.assume", "tl.debug_barrier"}:
        return "Allowed in statement context; value use is restricted unless separately reachable from triton-value-call."
    return "Extracted from explicit task-agnostic GBNF tl.* productions; no generic tl.<name> fallback exists."


def _write_json(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    data = extract_allowlist(args.grammar)
    _write_json(data, args.output)
    print(f"wrote {args.output} ({len(data['functions'])} tl.* functions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
