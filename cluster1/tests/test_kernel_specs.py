"""Tests for KernelBench-backed kernel specs (Phase 6, Task 6.8)."""

import pytest

from cluster1.data.kernels import KERNEL_SPECS, get_kernel_spec
from cluster1.data.kernels.spec import KernelSpec
from cluster1.data.prompts.prompt_contract import build_prompt
from cluster1.validation.compile_check import CompileSpec


class _FakeTorch:
    float32 = object()

    @staticmethod
    def randn(*shape, dtype=None, device=None):
        return {"shape": shape, "dtype": dtype, "device": device}


class TestKernelSpecsPresent:
    def test_all_kernel_classes_present(self):
        assert set(KERNEL_SPECS.keys()) == {"elementwise", "reduction", "matmul"}

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_spec_is_kernelspec(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert isinstance(spec, KernelSpec)
        assert isinstance(spec.compile_spec, CompileSpec)

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_three_dtype_keys(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert set(spec.shapes_by_dtype.keys()) == {"fp32", "fp16", "bf16"}

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_at_least_five_shapes_per_dtype(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        for dtype_key, shapes in spec.shapes_by_dtype.items():
            assert len(shapes) >= 5, (
                f"{kernel_class}/{dtype_key} has only {len(shapes)} shapes, need >=5"
            )

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_dataset_id_is_kernelbench(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert spec.dataset_id == "ScalingIntelligence/KernelBench"

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_dataset_problem_id_is_positive_int(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert isinstance(spec.dataset_problem_id, int)
        assert spec.dataset_problem_id > 0

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_build_prompt_contains_signature(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        prompt = build_prompt(spec, "fp32")
        sig_str = str(spec.reference_signature)
        assert sig_str in prompt, (
            f"Prompt for {kernel_class} does not contain signature: {sig_str}"
        )

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_compile_arg_builder_matches_launcher_signature(
        self, kernel_class: str, monkeypatch
    ):
        spec = get_kernel_spec(kernel_class)
        build_args = spec.compile_spec.build_args
        monkeypatch.setitem(build_args.__globals__, "torch", _FakeTorch)

        shape = spec.shapes_by_dtype["fp32"][0]
        args, kwargs = build_args(shape, _FakeTorch.float32)

        assert len(args) == len(spec.reference_signature.parameters)
        assert kwargs == {}

    @pytest.mark.parametrize("kernel_class", ["elementwise", "reduction", "matmul"])
    def test_reference_code_not_empty(self, kernel_class: str):
        spec = get_kernel_spec(kernel_class)
        assert len(spec.reference_code) > 50

    def test_get_kernel_spec_raises_on_unknown(self):
        with pytest.raises(KeyError):
            get_kernel_spec("unknown_class")


class TestVerifiedProblemIds:
    """Verify the problem IDs match KernelBench Level 1 expectations."""

    def test_relu_is_problem_19(self):
        assert get_kernel_spec("elementwise").dataset_problem_id == 19

    def test_softmax_is_problem_23(self):
        assert get_kernel_spec("reduction").dataset_problem_id == 23

    def test_matmul_is_problem_1(self):
        assert get_kernel_spec("matmul").dataset_problem_id == 1


class TestLockedReferenceSignatures:
    def test_relu_signature_is_contract_exact(self):
        spec = get_kernel_spec("elementwise")
        assert spec.launcher_name + str(spec.reference_signature) == (
            "relu(x: torch.Tensor) -> torch.Tensor"
        )

    def test_softmax_signature_is_contract_exact(self):
        spec = get_kernel_spec("reduction")
        assert spec.launcher_name + str(spec.reference_signature) == (
            "softmax(x: torch.Tensor) -> torch.Tensor"
        )

    def test_matmul_signature_is_contract_exact(self):
        spec = get_kernel_spec("matmul")
        assert spec.launcher_name + str(spec.reference_signature) == (
            "matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor"
        )
