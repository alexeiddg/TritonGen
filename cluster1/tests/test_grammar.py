"""Offline grammar acceptance and rejection tests."""

from __future__ import annotations

import ast

import pytest

from cluster1.data.prompts.prompt_contract import (
    ELEMENTWISE_AUTOTUNE_CONFIGS,
    MATMUL_AUTOTUNE_CONFIGS,
    REDUCTION_AUTOTUNE_CONFIGS,
    _format_autotune_configs,
)
from cluster1.grammar.test_grammar_acceptance import BAD_KERNELS, GOOD_KERNELS
from cluster1.grammar.triton_kernel_validator import (
    DEFAULT_GBNF_PATH,
    _compile_lark_parser,
    _semantic_accepts,
    accepts_source,
    validate_grammar_file,
)


def test_validator_compiles_actual_gbnf() -> None:
    report = validate_grammar_file()
    assert report.lark_compiles, "\n".join(report.errors)
    assert report.n_accept_cases >= 5
    assert report.n_reject_cases >= 10


def test_validator_rejects_malformed_gbnf_text(tmp_path) -> None:
    malformed = DEFAULT_GBNF_PATH.read_text(encoding="utf-8").replace(
        'tl-load-call ::= "tl.load(" kernel-expr ")"',
        'tl-load-call ::= "tl.load(" kernel-expr ")" | (',
    )
    grammar_path = tmp_path / "triton_kernel.gbnf"
    grammar_path.write_text(malformed, encoding="utf-8")

    report = validate_grammar_file(grammar_path)

    assert not report.lark_compiles
    assert report.errors


def test_acceptance_uses_actual_gbnf_behavior(tmp_path) -> None:
    tightened = DEFAULT_GBNF_PATH.read_text(encoding="utf-8").replace(
        " | tl-where-call",
        "",
        1,
    )
    grammar_path = tmp_path / "triton_kernel.gbnf"
    grammar_path.write_text(tightened, encoding="utf-8")

    assert not accepts_source(GOOD_KERNELS["relu"], grammar_path)


def test_prompt_contract_autotune_configs_are_accepted_by_grammar() -> None:
    configs = _format_autotune_configs([ELEMENTWISE_AUTOTUNE_CONFIGS[0]])
    source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs={configs},
    key=["n_elements"],
)
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

    assert accepts_source(source)


def test_prompt_contract_renders_python_config_calls() -> None:
    elementwise = _format_autotune_configs([ELEMENTWISE_AUTOTUNE_CONFIGS[0]])
    matmul = _format_autotune_configs([MATMUL_AUTOTUNE_CONFIGS[0]])

    assert (
        'triton.Config({"BLOCK_SIZE": 64}, num_warps=2, num_stages=3)'
        in elementwise
    )
    assert "triton.Config({BLOCK_SIZE=64" not in elementwise
    assert (
        'triton.Config({"BLOCK_M": 32, "BLOCK_N": 32, "BLOCK_K": 32}, '
        "num_warps=4, num_stages=2)"
        in matmul
    )
    assert "triton.Config({BLOCK_M=32" not in matmul


def test_all_prompt_contract_autotune_entries_are_accepted_by_grammar() -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    prompt_configs = (
        ELEMENTWISE_AUTOTUNE_CONFIGS + REDUCTION_AUTOTUNE_CONFIGS + MATMUL_AUTOTUNE_CONFIGS
    )

    for config in prompt_configs:
        config_list = _format_autotune_configs([config])
        source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs={config_list},
    key=["n_elements"],
)
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

        parser.parse(source)


@pytest.mark.parametrize(
    "bad_config",
    [
        'triton.Config({"BLOCK_M": 256, "BLOCK_N": 256, "BLOCK_K": 256}, num_warps=16, num_stages=5)',
        'triton.Config({"BLOCK_SIZE": 64}, num_warps=16, num_stages=5)',
        'triton.Config({"BLOCK_SIZE": 512}, num_warps=4, num_stages=3)',
    ],
)
def test_actual_gbnf_rejects_autotune_configs_outside_prompt_contract(
    bad_config: str,
) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))
    source = f"""\
import torch
import triton
import triton.language as tl

@triton.autotune(configs=[{bad_config}], key=["n_elements"])
@triton.jit
def _relu_kernel(x_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    out = tl.where(x > 0.0, x, 0.0)
    tl.store(out_ptr + offsets, out, mask=mask)

def relu(x: torch.Tensor) -> torch.Tensor:
    out = torch.empty_like(x)
    n_elements = x.numel()
    BLOCK_SIZE = 64
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)
    return out
"""

    with pytest.raises(Exception):
        parser.parse(source)


@pytest.mark.parametrize(
    "source",
    [
        GOOD_KERNELS["relu"].replace(
            "_relu_kernel[grid](x, out, n_elements, BLOCK_SIZE)",
            "_relu_kernel[grid](BLOCK_SIZE=BLOCK_SIZE, x)",
        ),
        GOOD_KERNELS["relu"].replace(
            "grid = (triton.cdiv(n_elements, BLOCK_SIZE),)",
            "grid = [x=1]",
        ),
    ],
)
def test_actual_gbnf_rejects_python_invalid_wrapper_syntax(source: str) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(source)


@pytest.mark.parametrize(
    "bad_name",
    [
        "missing_output_allocation",
        "launch_uses_input_not_output",
        "relu_missing_launch_tail",
        "relu_wrong_launch_tail",
        "softmax_missing_launch_tail",
        "matmul_missing_launch_tail",
        "return_input_after_allocation",
        "unused_output_allocation",
        "reassigned_output_after_allocation",
        "torch_empty_tensor_shape",
        "torch_empty_missing_device_dtype",
        "torch_empty_like_invalid_empty_source",
        "relu_helper_missing_args",
        "relu_helper_missing_constexpr",
        "relu_helper_wrong_output_name",
        "softmax_helper_missing_args",
        "softmax_helper_missing_constexpr",
        "matmul_helper_missing_args",
        "matmul_helper_wrong_ptr_name",
        "grid_float_division",
        "grid_matmul_operator",
    ],
)
def test_actual_gbnf_rejects_validator_mismatch_wrapper_forms(bad_name: str) -> None:
    parser = _compile_lark_parser(DEFAULT_GBNF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(Exception):
        parser.parse(BAD_KERNELS[bad_name])


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_missing_launch_tail",
        "relu_wrong_launch_tail",
        "softmax_missing_launch_tail",
        "matmul_missing_launch_tail",
    ],
)
def test_semantic_validator_rejects_bad_launch_args(bad_name: str) -> None:
    assert not _semantic_accepts(ast.parse(BAD_KERNELS[bad_name]))


@pytest.mark.parametrize(
    "bad_name",
    [
        "relu_helper_missing_args",
        "relu_helper_missing_constexpr",
        "relu_helper_wrong_output_name",
        "softmax_helper_missing_args",
        "softmax_helper_missing_constexpr",
        "matmul_helper_missing_args",
        "matmul_helper_wrong_ptr_name",
    ],
)
def test_semantic_validator_rejects_bad_helper_signatures(bad_name: str) -> None:
    assert not _semantic_accepts(ast.parse(BAD_KERNELS[bad_name]))


@pytest.mark.parametrize("name,source", GOOD_KERNELS.items())
def test_good_kernels_are_accepted(name: str, source: str) -> None:
    assert accepts_source(source), f"GOOD_KERNELS[{name!r}] was rejected"


@pytest.mark.parametrize("name,source", BAD_KERNELS.items())
def test_bad_kernels_are_rejected(name: str, source: str) -> None:
    assert not accepts_source(source), f"BAD_KERNELS[{name!r}] was accepted"
