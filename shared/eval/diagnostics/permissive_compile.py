"""Diagnostic-only permissive Triton compile extraction.

This module answers a narrower attribution question than the strict Level 1
surface check: does an unconstrained generation contain any top-level
``@triton.jit`` function that can be launched far enough to trigger Triton JIT
compilation under relaxed extraction?

It is intentionally not imported by the normal shared eval pipeline.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DIAGNOSTIC_NAME = "permissive_compile"
DEFAULT_TENSOR_NUMEL = 1024
DEFAULT_BLOCK_VALUE = 64
DEFAULT_DIM_VALUE = 16
_MAX_ERROR_CHARS = 500
_DEFAULT_MODAL_GPU = "L4"
_FORBIDDEN_OUTPUT_SUBSTRINGS = ("tim" + "ing", "profil" + "ing", "speed" + "up")


@dataclass(frozen=True)
class TritonJitFunction:
    """Top-level Triton JIT function selected from a generated source."""

    name: str
    node: ast.FunctionDef
    ordinal: int


@dataclass(frozen=True)
class TensorInputSpec:
    """Unit-testable placeholder for a permissive tensor argument."""

    name: str
    shape: tuple[int, ...] = (DEFAULT_TENSOR_NUMEL,)
    dtype: str = "fp32"
    device: str = "cuda"


@dataclass(frozen=True)
class PermissiveLaunchInputs:
    """Launch arguments and metadata for a permissive JIT attempt."""

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    grid: tuple[int, int, int]
    parameter_kinds: dict[str, str]


@dataclass(frozen=True)
class PermissiveCompileAttempt:
    """Result of the relaxed dummy-launch compile attempt."""

    compile_success: bool
    failure_type: str | None = None
    error_summary: str | None = None


CompileRunner = Callable[[str, TritonJitFunction], PermissiveCompileAttempt]
TensorFactory = Callable[[TensorInputSpec], Any]


def strip_markdown_fences(source: str) -> str:
    """Return code from the first Python/plain markdown fence, or raw source."""

    lines = source.splitlines()
    for index, line in enumerate(lines):
        info = _fence_info(line)
        if info is None or info not in {"", "python", "py"}:
            continue

        body: list[str] = []
        for candidate in lines[index + 1 :]:
            if _is_closing_fence(candidate):
                return "\n".join(body)
            body.append(candidate)
        return "\n".join(body)

    return source


def extract_triton_jit_functions(source: str) -> list[TritonJitFunction]:
    """Find top-level functions decorated with ``@triton.jit``."""

    stripped_source = strip_markdown_fences(source)
    tree = ast.parse(stripped_source)
    functions: list[TritonJitFunction] = []
    for ordinal, node in enumerate(tree.body):
        if not isinstance(node, ast.FunctionDef):
            continue
        if _has_triton_jit_decorator(node):
            functions.append(TritonJitFunction(name=node.name, node=node, ordinal=ordinal))
    return functions


def build_permissive_launch_inputs(
    function_ast_or_signature: ast.FunctionDef | inspect.Signature,
    *,
    tensor_factory: TensorFactory | None = None,
) -> PermissiveLaunchInputs:
    """Build conservative dummy launch inputs for a Triton JIT function."""

    params = _parameter_descriptors(function_ast_or_signature)
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    parameter_kinds: dict[str, str] = {}

    for param in params:
        kind = _infer_parameter_kind(param)
        parameter_kinds[param.name] = kind
        if kind == "pointer":
            value = _make_tensor_value(param.name, tensor_factory)
            args.append(value)
        elif kind == "constexpr":
            kwargs[param.name] = _small_int_value_for_name(param.name)
        else:
            args.append(_small_int_value_for_name(param.name))

    return PermissiveLaunchInputs(
        args=tuple(args),
        kwargs=kwargs,
        grid=(1, 1, 1),
        parameter_kinds=parameter_kinds,
    )


def evaluate_source_permissive_compile(
    source: str,
    metadata: Mapping[str, Any] | None = None,
    *,
    compile_runner: CompileRunner | None = None,
) -> dict[str, Any]:
    """Evaluate one generated source with diagnostic-only permissive compile."""

    metadata = metadata or {}
    stripped_source = strip_markdown_fences(source)
    base = _base_output_row(metadata)
    base["stripped_source_sha256"] = _sha256(stripped_source)

    try:
        tree = ast.parse(stripped_source)
    except (SyntaxError, ValueError) as exc:
        base.update(
            {
                "parse_success": False,
                "parse_error_type": type(exc).__name__,
                "parse_error_summary": _short_error(exc),
                "no_jit_found": False,
                "selected_jit_function": None,
                "permissive_compile_success": False,
                "failure_type": "ParseError",
                "error_summary": _short_error(exc),
            }
        )
        return _assert_no_forbidden_output_fields(base)

    base.update(
        {
            "parse_success": True,
            "parse_error_type": None,
            "parse_error_summary": None,
        }
    )
    functions = [
        TritonJitFunction(name=node.name, node=node, ordinal=ordinal)
        for ordinal, node in enumerate(tree.body)
        if isinstance(node, ast.FunctionDef) and _has_triton_jit_decorator(node)
    ]
    if not functions:
        base.update(
            {
                "no_jit_found": True,
                "selected_jit_function": None,
                "permissive_compile_success": False,
                "failure_type": "NoJitFound",
                "error_summary": "no top-level @triton.jit function found",
            }
        )
        return _assert_no_forbidden_output_fields(base)

    selected = functions[0]
    runner = compile_runner or _attempt_permissive_compile
    attempt = runner(stripped_source, selected)
    base.update(
        {
            "no_jit_found": False,
            "selected_jit_function": selected.name,
            "permissive_compile_success": attempt.compile_success,
            "failure_type": attempt.failure_type,
            "error_summary": attempt.error_summary,
        }
    )
    return _assert_no_forbidden_output_fields(base)


def evaluate_jsonl_permissive_compile(
    input_jsonl: str | Path,
    output_jsonl: str | Path,
    summary_json: str | Path,
    *,
    overwrite: bool = False,
    compile_runner: CompileRunner | None = None,
) -> dict[str, Any]:
    """Evaluate an existing JSONL artifact and write diagnostic JSONL/summary."""

    input_path = Path(input_jsonl)
    output_path = Path(output_jsonl)
    summary_path = Path(summary_json)
    _check_output_path(output_path, overwrite=overwrite)
    _check_output_path(summary_path, overwrite=overwrite)

    rows = _read_jsonl(input_path)
    output_rows = [
        _evaluate_input_row(row, source_index=index, compile_runner=compile_runner)
        for index, row in enumerate(rows)
    ]
    summary = summarize_permissive_compile_rows(output_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def summarize_permissive_compile_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize diagnostic rows without mixing them into primary metrics."""

    failures = Counter(
        str(row.get("failure_type"))
        for row in rows
        if not bool(row.get("permissive_compile_success"))
    )
    failures.pop("None", None)
    return {
        "diagnostic_only": True,
        "diagnostic_name": DIAGNOSTIC_NAME,
        "metric_interpretation": (
            "diagnostic attribution only; not a correctness, resource, "
            "convergence, or strict surface metric"
        ),
        "total_rows": len(rows),
        "parse_success_count": sum(bool(row.get("parse_success")) for row in rows),
        "parse_failure_count": sum(not bool(row.get("parse_success")) for row in rows),
        "no_jit_found_count": sum(bool(row.get("no_jit_found")) for row in rows),
        "permissive_compile_success_count": sum(
            bool(row.get("permissive_compile_success")) for row in rows
        ),
        "permissive_compile_failure_count": sum(
            not bool(row.get("permissive_compile_success")) for row in rows
        ),
        "failure_breakdown": dict(sorted(failures.items())),
    }


def main(argv: Sequence[str] | None = None) -> dict[str, Any]:
    """CLI entrypoint for local diagnostic evaluation."""

    args = _parse_args(argv)
    if args.modal_gpu:
        raise SystemExit(
            "--modal-gpu requires running through Modal, for example "
            "`/Users/alexeidelgado/miniconda3/bin/modal run -m "
            "shared.eval.diagnostics.permissive_compile ...`"
        )
    summary = evaluate_jsonl_permissive_compile(
        args.input,
        args.output,
        args.summary,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


@dataclass(frozen=True)
class _ParameterDescriptor:
    name: str
    annotation: ast.AST | inspect._empty | Any = inspect.Signature.empty


def _evaluate_input_row(
    row: Mapping[str, Any],
    *,
    source_index: int,
    compile_runner: CompileRunner | None,
) -> dict[str, Any]:
    source = row.get("source")
    if not isinstance(source, str):
        metadata = dict(row)
        metadata["source_index"] = source_index
        result = _base_output_row(metadata)
        result.update(
            {
                "stripped_source_sha256": None,
                "parse_success": False,
                "parse_error_type": "MissingSource",
                "parse_error_summary": "row source is missing or not a string",
                "no_jit_found": False,
                "selected_jit_function": None,
                "permissive_compile_success": False,
                "failure_type": "MissingSource",
                "error_summary": "row source is missing or not a string",
            }
        )
        return _assert_no_forbidden_output_fields(result)

    metadata = dict(row)
    metadata["source_index"] = source_index
    return evaluate_source_permissive_compile(
        source,
        metadata,
        compile_runner=compile_runner,
    )


def _attempt_permissive_compile(
    stripped_source: str,
    selected_function: TritonJitFunction,
) -> PermissiveCompileAttempt:
    module = None
    try:
        from cluster1.validation.compile_check import (
            _classify_error,
            cleanup_generated_module,
            load_generated_module,
        )

        module = load_generated_module(stripped_source)
        kernel = getattr(module, selected_function.name, None)
        if kernel is None:
            return PermissiveCompileAttempt(
                compile_success=False,
                failure_type="KernelNotLoaded",
                error_summary=f"selected kernel {selected_function.name!r} not found",
            )

        import torch

        if not torch.cuda.is_available():
            return PermissiveCompileAttempt(
                compile_success=False,
                failure_type="RuntimeError",
                error_summary="CUDA is not available for permissive compile launch",
            )

        launch_inputs = build_permissive_launch_inputs(
            selected_function.node,
            tensor_factory=_torch_tensor_factory(torch),
        )
        kernel[launch_inputs.grid](*launch_inputs.args, **launch_inputs.kwargs)
        torch.cuda.synchronize()
        return PermissiveCompileAttempt(compile_success=True)
    except ValueError as exc:
        return PermissiveCompileAttempt(
            compile_success=False,
            failure_type=_classify_load_error(exc),
            error_summary=_short_error(exc),
        )
    except Exception as exc:
        error_type = _classify_runtime_error(exc)
        try:
            from cluster1.validation.compile_check import _classify_error

            error_type = str(_classify_error(exc))
        except Exception:
            pass
        return PermissiveCompileAttempt(
            compile_success=False,
            failure_type=error_type,
            error_summary=_short_error(exc),
        )
    finally:
        if module is not None:
            try:
                from cluster1.validation.compile_check import cleanup_generated_module

                cleanup_generated_module(module)
            except Exception:
                pass


def _torch_tensor_factory(torch_module: Any) -> TensorFactory:
    def make_tensor(spec: TensorInputSpec) -> Any:
        return torch_module.empty(
            spec.shape,
            device=spec.device,
            dtype=torch_module.float32,
        )

    return make_tensor


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostic-only permissive compile check for frozen JSONL rows."
    )
    parser.add_argument("--input", required=True, help="Input JSONL artifact.")
    parser.add_argument("--output", required=True, help="Output diagnostic JSONL.")
    parser.add_argument("--summary", required=True, help="Output summary JSON.")
    parser.add_argument(
        "--modal-gpu",
        default=None,
        help="Run compile attempts remotely on this Modal GPU when invoked by Modal.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing diagnostic outputs.",
    )
    return parser.parse_args(argv)


def _base_output_row(metadata: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "diagnostic_only": True,
        "diagnostic_name": DIAGNOSTIC_NAME,
        "metric_interpretation": (
            "diagnostic attribution only; separate from strict canonical "
            "surface pass/fail"
        ),
    }
    for key in (
        "source_index",
        "run_id",
        "model_id",
        "grammar_active",
        "kernel_class",
        "kernel_name",
        "dtype",
        "generation_seed",
        "temperature",
        "unique_solution_hash",
    ):
        if key in metadata:
            output[key] = metadata[key]

    if "compile_success" in metadata:
        output["strict_compile_success"] = bool(metadata["compile_success"])
    if "compile_error_type" in metadata:
        output["strict_compile_error_type"] = metadata["compile_error_type"]
    return output


def _parameter_descriptors(
    function_ast_or_signature: ast.FunctionDef | inspect.Signature,
) -> list[_ParameterDescriptor]:
    if isinstance(function_ast_or_signature, ast.FunctionDef):
        args = function_ast_or_signature.args
        descriptors = [
            _ParameterDescriptor(arg.arg, arg.annotation)
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]
        ]
        if args.vararg is not None:
            descriptors.append(
                _ParameterDescriptor(args.vararg.arg, args.vararg.annotation)
            )
        if args.kwarg is not None:
            descriptors.append(
                _ParameterDescriptor(args.kwarg.arg, args.kwarg.annotation)
            )
        return descriptors

    descriptors = []
    for param in function_ast_or_signature.parameters.values():
        descriptors.append(_ParameterDescriptor(param.name, param.annotation))
    return descriptors


def _infer_parameter_kind(param: _ParameterDescriptor) -> str:
    if _is_pointer_like_name(param.name):
        return "pointer"
    if _is_constexpr_parameter(param):
        return "constexpr"
    return "scalar"


def _is_constexpr_parameter(param: _ParameterDescriptor) -> bool:
    if _is_tl_constexpr_annotation(param.annotation):
        return True

    name = param.name
    upper = name.upper()
    if name == upper and any(char.isalpha() for char in name):
        return True
    if "BLOCK" in upper or "SIZE" in upper:
        return True
    parts = _name_parts(name)
    return any(part in {"N", "M", "K"} for part in parts)


def _is_pointer_like_name(name: str) -> bool:
    lower = name.lower()
    parts = {part.lower() for part in _name_parts(name)}
    if lower in {"x", "y", "a", "b", "c", "input", "output", "out"}:
        return True
    if {"x", "y", "a", "b", "c", "input", "output", "out"} & parts:
        return True
    return any(marker in lower for marker in ("ptr", "input", "output", "out"))


def _small_int_value_for_name(name: str) -> int:
    upper = name.upper()
    if "BLOCK" in upper or "SIZE" in upper:
        return DEFAULT_BLOCK_VALUE
    if upper in {"M", "N", "K"} or any(part in {"M", "N", "K"} for part in _name_parts(name)):
        return DEFAULT_DIM_VALUE
    if "STRIDE" in upper:
        return 1
    return DEFAULT_DIM_VALUE


def _make_tensor_value(name: str, tensor_factory: TensorFactory | None) -> Any:
    spec = TensorInputSpec(name=name)
    if tensor_factory is None:
        return spec
    return tensor_factory(spec)


def _has_triton_jit_decorator(node: ast.FunctionDef) -> bool:
    return any(_is_triton_jit_decorator(decorator) for decorator in node.decorator_list)


def _is_triton_jit_decorator(decorator: ast.AST) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return (
        isinstance(target, ast.Attribute)
        and target.attr == "jit"
        and isinstance(target.value, ast.Name)
        and target.value.id == "triton"
    )


def _is_tl_constexpr_annotation(annotation: ast.AST | inspect._empty | Any) -> bool:
    if annotation is inspect.Signature.empty or annotation is None:
        return False
    if isinstance(annotation, ast.Attribute):
        return (
            annotation.attr == "constexpr"
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == "tl"
        )
    rendered = str(annotation)
    return rendered in {"tl.constexpr", "triton.language.constexpr"}


def _name_parts(name: str) -> set[str]:
    normalized = "".join(char if char.isalnum() else "_" for char in name)
    return {token.upper() for token in normalized.split("_") if token}


def _fence_info(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("```"):
        return None
    return stripped[3:].strip().lower()


def _is_closing_fence(line: str) -> bool:
    stripped = line.strip()
    return stripped == "```" or (stripped.startswith("```") and stripped[3:].strip() == "")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(payload)
    return rows


def _check_output_path(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")


def _assert_no_forbidden_output_fields(row: dict[str, Any]) -> dict[str, Any]:
    forbidden = [
        key
        for key in row
        if any(fragment in key.lower() for fragment in _FORBIDDEN_OUTPUT_SUBSTRINGS)
    ]
    if forbidden:
        raise AssertionError(f"diagnostic row contains forbidden fields: {forbidden}")
    return row


def _classify_load_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "syntax error" in message:
        return "SyntaxError"
    if "import error" in message or "no module named" in message:
        return "ImportError"
    return "ModuleLoadError"


def _classify_runtime_error(exc: Exception) -> str:
    if type(exc).__name__ == "CompilationError":
        return "CompilationError"
    if isinstance(exc, AttributeError):
        return "AttributeError"
    if isinstance(exc, TypeError):
        return "TypeError"
    if isinstance(exc, RuntimeError):
        return "RuntimeError"
    return type(exc).__name__


def _short_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:_MAX_ERROR_CHARS]


def _sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _register_modal_entrypoint_if_needed() -> None:
    if not _should_register_modal_entrypoint():
        return

    from shared.modal_harness.app import app
    from shared.modal_harness.images import triton_compile_image

    diagnostic_image = triton_compile_image.add_local_python_source("cluster2")
    remote_function = app.function(
        image=diagnostic_image,
        gpu=_DEFAULT_MODAL_GPU,
        memory=24576,
        cpu=4.0,
        timeout=900,
        max_containers=10,
        min_containers=0,
        scaledown_window=120,
    )(_remote_evaluate_rows)

    globals()["remote_permissive_compile_rows"] = remote_function
    globals()["modal_entrypoint"] = app.local_entrypoint()(_modal_entrypoint)


def _should_register_modal_entrypoint() -> bool:
    if "modal" in sys.modules:
        return True
    executable = Path(sys.argv[0]).name
    return executable == "modal"


def _remote_evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output_rows = [
        _evaluate_input_row(row, source_index=index, compile_runner=None)
        for index, row in enumerate(rows)
    ]
    return {
        "rows": output_rows,
        "summary": summarize_permissive_compile_rows(output_rows),
    }


def _modal_entrypoint(
    input: str,
    output: str,
    summary: str,
    modal_gpu: str = _DEFAULT_MODAL_GPU,
    overwrite: bool = False,
) -> None:
    if modal_gpu != _DEFAULT_MODAL_GPU:
        raise ValueError(
            f"this diagnostic entrypoint is registered for {_DEFAULT_MODAL_GPU}; "
            f"got {modal_gpu!r}"
        )
    rows = _read_jsonl(Path(input))
    output_path = Path(output)
    summary_path = Path(summary)
    _check_output_path(output_path, overwrite=overwrite)
    _check_output_path(summary_path, overwrite=overwrite)

    remote_function = globals()["remote_permissive_compile_rows"]
    payload = remote_function.remote(rows)
    output_rows = payload["rows"]
    summary_payload = payload["summary"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_payload, indent=2, sort_keys=True))


_register_modal_entrypoint_if_needed()


if __name__ == "__main__":
    main()
