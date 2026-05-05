# Grammar Fixtures

These files are the test bed for `grammars/triton_kernel.gbnf`. The grammar
test suite asserts that everything in `valid_kernels/` is **accepted** and
everything in `invalid_kernels/` is **rejected**.

## Valid kernels

Each one is a real Triton kernel that compiles on a CUDA GPU.

| File | Why it's here |
|------|---------------|
| `vector_add.py` | The canonical 1-D add. Smallest non-trivial kernel. |
| `relu.py` | Single-input element-wise op with `tl.maximum`. |
| `scalar_mul.py` | Scalar-by-pointer multiply; introduces a scalar param. |
| `copy.py` | Pure load → store; verifies grammar accepts no-op kernels. |
| `abs.py` | Tests that the grammar tolerates an inline comment in the body. |
| `axpy.py` | Two pointer reads and a scalar; mixed-arity arithmetic. |

## Invalid kernels

Each one is rejected for **one specific reason**. Adding a new kind of
mistake means adding a new fixture and a row to this table.

| File | Reason for rejection |
|------|----------------------|
| `missing_triton_import.py` | Skips `import triton` |
| `markdown_fence.py` | Wrapped in ` ```python ... ``` ` fences |
| `missing_jit_decorator.py` | Kernel function lacks `@triton.jit` |
| `imports_out_of_order.py` | `import triton` precedes `import torch` |
| `has_if_statement.py` | Uses `if` (no control flow in Phase 1 grammar) |
| `missing_launcher.py` | Kernel only — no launcher function |
| `prose_preamble.py` | "Here is the kernel:" before the imports |

## Adding fixtures

1. Drop a `.py` file in the appropriate directory.
2. Add a row to the table above with the one-line reason.
3. Run `pytest tests/test_grammar_loader.py -v` and confirm it goes
   green.
