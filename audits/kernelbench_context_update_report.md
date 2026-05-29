# KernelBench Context Update Report

## 1. Inputs read

- `docs/02_methodology_cluster1.md`
- `docs/09_preliminary_report_outline.md`
- `cluster1/README.md`
- `.contracts/research/scale_policy.md`
- Original KernelBench paper: Ouyang et al. 2025, "KernelBench: Can LLMs Write Efficient GPU Kernels?"

## 2. Files updated

- `docs/02_methodology_cluster1.md`
- `docs/09_preliminary_report_outline.md`

## 3. Questions answered

1. Specific KernelBench numbers were added for original KernelBench Level 1 one-shot `fast1` and 10-call `fast1` refinement baselines.
2. Original KernelBench task definitions were added for the TritonGen locked subset: problem 1 is Square matrix multiplication, problem 19 is ReLU, and problem 23 is Softmax.

## 4. Important caveat

The update explicitly states that TritonGen's current task-agnostic G compile rate, `3/177 = 1.7%`, is Level 1 compile-only evidence. It is not directly comparable to KernelBench `fast0`, `fast1`, or full Level 1 benchmark results, which require functional correctness and, for `fast1`, speed greater than PyTorch Eager.

## 5. Corrections made

- Prevented mislabeling KernelBench problem 19 as average pooling.
- Prevented mislabeling KernelBench problem 23 as a generic reduction.
- Recorded that average-pooling tasks are original KernelBench Level 1 IDs 44-46.
- Recorded that reduction tasks are original KernelBench Level 1 IDs 47-53.

## 6. Classification

COMPLETE
