# Task-Agnostic Grammar n=5 Incompatibility Audit

## Executive summary

Classification: `PATH_2_OLD_N5_ARTIFACT_INCOMPATIBLE_WITH_CURRENT_GRAMMAR`.

The five compile-passing rejected fp32 matmul rows in
`outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl` are JSONL lines 31-35.
They are syntactically valid Python modules that previously recorded
`compile_success=true`, but they are structurally incomplete under the current
task-agnostic grammar and Cluster 1 generated surface. The first grammar
rejection is not a Triton API call signature. It is the current launch-wrapper
contract:

- `wrapper-body ::= wrapper-prefix-stmts bracket-launch-stmt wrapper-return-stmt`
- `bracket-launch-stmt ::= indent1 private-kernel-name "[" grid-expr "](" wrapper-call-arg-list ")" nl`
- `wrapper-return-stmt ::= indent1 "return " wrapper-expr nl`

All five rows stop after wrapper asserts or dimension bindings and trailing
whitespace. None allocates an output tensor, defines `grid`, calls
`_matmul_kernel[grid](...)`, or returns the allocated output. The current grammar
header and `.contracts/research/cluster1_generated_surface.md` both make those
launcher requirements part of the Cluster 1 surface.

The `tl.*` calls present in the five rows are documented and are accepted by the
current API allow-list:

- `tl.program_id`: pinned reference status `MATCH`, grammar rule
  `tl-program-id-call`.
- `tl.arange`: pinned reference status `MATCH`, grammar rule `tl-arange-call`.

Therefore the five compile-passing rejects do not show that the current grammar
is too strict against the pinned Triton API reference. They show that the old
n=5 artifact is incompatible with the current grammar/surface contract.

## Why the hash gate stopped

The Phase -1 hash gate correctly blocked a silent hash re-record because the
current grammar accepts only 14 of 45 rows from the frozen
`g_task_agnostic_n5_l4_rerun` artifact. Compatibility is not satisfied until
the old artifact is archived/excluded or a fresh n=5 artifact generated under
the current grammar validates cleanly.

No hash, grammar, manifest, frozen output, Cluster 2 runtime, repair-loop, or
metric file was modified during this audit.

## Five compile-passing rejected row analysis

Diagnostic command used:

```bash
.venv/bin/python - <<'PY'
import ast, json, hashlib
from pathlib import Path
from lark import UnexpectedInput
from cluster1.grammar.triton_kernel_validator import (
    TASK_AGNOSTIC_GBNF_PATH,
    _compile_lark_parser,
    _semantic_accepts_task_agnostic,
)

parser = _compile_lark_parser(TASK_AGNOSTIC_GBNF_PATH.read_text(encoding="utf-8"))
p = Path("outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl")
for line_no, line in enumerate(p.open(), start=1):
    if line_no not in range(31, 36):
        continue
    row = json.loads(line)
    source = row["source"]
    try:
        parser.parse(source)
        parsed = True
    except UnexpectedInput as exc:
        parsed = False
        print(line_no, type(exc).__name__, exc.line, exc.column, hashlib.sha256(source.encode()).hexdigest())
PY
```

| line_number | seed | kernel_class | dtype | compile_success | source_sha256 | rejected_construct | grammar_rule | reference_status | diagnosis | recommended_action |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | 0 | matmul/gemm | fp32 | true | `fe4ca6342f09e4fcc7dc663653b34521e935cca99e62de67d4fe59280829a01b` | Wrapper ends after two asserts and whitespace; no output allocation, `grid`, bracket launch, or return. Helper contains `tl.program_id(0/1)` and `tl.arange(0, BLOCK_*)`. | First parser rejection at line 16 col 1. Missing `bracket-launch-stmt` required by `wrapper-body`. | `tl.program_id` and `tl.arange` are documented and `MATCH`; missing launcher tail is Cluster surface, not Triton API reference. | Old artifact/source is structurally incomplete under current grammar. | Do not relax grammar. Archive/exclude old artifact and rerun n=5 under current grammar. |
| 32 | 1 | matmul/gemm | fp32 | true | `bbf0be9be7c67dbce9324043a859b23556ae553e491375e163f4b890bfd7525b` | Wrapper ends after two asserts and whitespace; no output allocation, `grid`, bracket launch, or return. Helper contains `tl.program_id(0)`. | First parser rejection at line 14 col 5. Missing `bracket-launch-stmt` required by `wrapper-body`. | `tl.program_id` is documented and `MATCH`; missing launcher tail is Cluster surface, not Triton API reference. | Old artifact/source is structurally incomplete under current grammar. | Do not relax grammar. Archive/exclude old artifact and rerun n=5 under current grammar. |
| 33 | 2 | matmul/gemm | fp32 | true | `5d7d3710137196ef71b52bdf1288fc7029509d02071492a1c3801fda22d96482` | Wrapper ends after two asserts and whitespace; no output allocation, `grid`, bracket launch, or return. Helper contains `tl.program_id(0/1)` and `tl.arange(0, BLOCK_*)`. | First parser rejection at line 16 col 1. Missing `bracket-launch-stmt` required by `wrapper-body`. | `tl.program_id` and `tl.arange` are documented and `MATCH`; missing launcher tail is Cluster surface, not Triton API reference. | Old artifact/source is structurally incomplete under current grammar. | Do not relax grammar. Archive/exclude old artifact and rerun n=5 under current grammar. |
| 34 | 3 | matmul/gemm | fp32 | true | `e687be1b48892b39f3ad1405ed4d167e627208b88bda020feee8f638cf918fe8` | Wrapper ends after two asserts and whitespace; no output allocation, `grid`, bracket launch, or return. Helper contains `tl.program_id(0)`. | First parser rejection at line 14 col 1. Missing `bracket-launch-stmt` required by `wrapper-body`. | `tl.program_id` is documented and `MATCH`; missing launcher tail is Cluster surface, not Triton API reference. | Old artifact/source is structurally incomplete under current grammar. | Do not relax grammar. Archive/exclude old artifact and rerun n=5 under current grammar. |
| 35 | 4 | matmul/gemm | fp32 | true | `2547a148779b55b73234f924924ec7fd4849253acee47f3ff9f028a428898fdd` | Wrapper ends after asserts and `M/N/K` assignments plus whitespace; no output allocation, `grid`, bracket launch, or return. Helper contains `tl.program_id(0)`. | First parser rejection at line 17 col 1. Missing `bracket-launch-stmt` required by `wrapper-body`. | `tl.program_id` is documented and `MATCH`; missing launcher tail is Cluster surface, not Triton API reference. | Old artifact/source is structurally incomplete under current grammar. | Do not relax grammar. Archive/exclude old artifact and rerun n=5 under current grammar. |

Representative excerpts:

```python
# lines 31 and 33
def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D tensors"
    assert a.shape[1] == b.shape[0], "Matrix dimensions must match"
    # only trailing whitespace follows
```

```python
# line 35
def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.ndim == 2 and b.ndim == 2
    assert a.shape[1] == b.shape[0]
    M = a.shape[0]
    N = b.shape[1]
    K = a.shape[1]
    # only trailing whitespace follows
```

## Current grammar rejection rules

The first failing rule for all five rows is the structural launcher rule, not a
`tl.*` call rule:

```gbnf
launch-wrapper ::= "def " public-launcher-name "(" wrapper-param-list ") -> torch.Tensor:" nl wrapper-body
wrapper-body ::= wrapper-prefix-stmts bracket-launch-stmt wrapper-return-stmt
bracket-launch-stmt ::= indent1 private-kernel-name "[" grid-expr "](" wrapper-call-arg-list ")" nl
wrapper-return-stmt ::= indent1 wrapper-return nl
```

The grammar file also states the same contract in comments:

```text
Launcher must use output allocation, a grid variable, bracket launch, and return.
```

The research surface document repeats the same launcher requirements:

1. Allocate an output tensor.
2. Define an explicit `grid`.
3. Invoke the private Triton helper with bracket launch syntax.
4. Return the output tensor.

Rows 31-35 satisfy none of those wrapper-tail requirements.

## API reference cross-check

The pinned API reference snapshot is
`cluster1/grammar/corpus/triton_language_reference_vmain_2026_05_16.json`.
The relevant entries are:

| construct | pinned reference status | grammar allow-list status | audit result |
| --- | --- | --- | --- |
| `tl.program_id(axis, _semantic=None)` | Documented in Programming Model. | `tl-program-id-call`, arities `1` and `axis=1`, `MATCH`. | Not the rejection cause. |
| `tl.arange(start, end, _semantic=None)` | Documented in Creation Ops. | `tl-arange-call`, arity `2`, `MATCH`. | Not the rejection cause. |
| Missing output allocation / missing `grid` / missing bracket launch / missing return | Not a `triton.language` API function. | Cluster 1 structural launcher surface. | The actual rejection cause. |

This is not an `tl.argmax`/`tl.argmin` axis issue, a `tl.range`/`tl.static_range`
kwarg issue, an integer literal issue, or a `tl.*` arity/kwarg restriction.

## API coverage report consistency check

`cluster1/tests/test_api_coverage.py` passed:

```text
9 passed in 1.60s
```

The API coverage report did not miss a real `tl.*` reference divergence for the
five compile-passing rows. Its scope is the `triton.language` allow-list and
signature comparison. The failing rows are rejected by Cluster 1 structural
launcher requirements, which are enforced by the grammar and acceptance fixtures
rather than by API coverage.

The grammar acceptance suite also passed at the actual repo path:

```text
cluster1/tests/test_grammar_acceptance.py: 215 passed in 29.49s
```

The prompt-suggested path `cluster1/grammar/test_grammar_acceptance.py` does not
exist in this repository and failed collection with "file or directory not
found"; the correct path is `cluster1/tests/test_grammar_acceptance.py`.

## Summary of all 31 rejected rows

Diagnostic over all 45 rows:

- Total rows: 45
- Accepted by current task-agnostic grammar and semantic validator: 14
- Rejected: 31
- Rejected with `compile_success=true`: 5
- Rejected with `compile_success=false`: 26
- Additional `compile_success=true` rows outside the five fp32 matmul rows: 0

Rejected rows by kernel/dtype:

| kernel_class | dtype | rejected |
| --- | --- | ---: |
| reduction | fp32 | 5 |
| reduction | fp16 | 5 |
| reduction | bf16 | 5 |
| matmul | fp32 | 5 |
| matmul | fp16 | 5 |
| matmul | bf16 | 5 |
| elementwise | fp32 | 1 |

Rejected rows by coarse failure category:

| category | count | notes |
| --- | ---: | --- |
| `structural_launcher_missing_launch_return` | 25 | Parser failure before semantic validation; wrappers end without the required launcher tail. Includes all five compile-passing fp32 matmul rows. |
| `invalid_python` | 4 | Artifact rows are not valid Python under `ast.parse`; all had `compile_success=false`. |
| `semantic_other` | 2 | Parser accepted but semantic validator rejected. Line 3 has undefined/unbound `BLOCK_SIZE` surface problems; line 17 has invalid wrapper attributes such as `x.dim`/`x.stride` under the current wrapper surface. Both had `compile_success=false`. |

The five fp32 matmul rows are unique only in that they previously recorded
`compile_success=true`. Their actual current-grammar failure category is
representative of the dominant rejection class: missing launcher tail.

## Path decision

Decision: `PATH_2_OLD_N5_ARTIFACT_INCOMPATIBLE_WITH_CURRENT_GRAMMAR`.

Evidence:

- The five compile-passing rows fail before any disputed Triton API construct is
  reached.
- The `tl.*` calls present in the five rows are documented and current grammar
  support is `MATCH`.
- The rejected construct is absence of required Cluster 1 wrapper structure,
  not an API-reference construct.
- The current grammar, acceptance fixtures, API coverage snapshot, and research
  surface agree that task-agnostic candidates need output allocation, explicit
  `grid`, bracket launch, and return.
- The old n=5 artifact contains structurally incomplete whitespace-padded rows,
  so compile metadata alone is not an adequate source of truth for grammar
  compatibility.

## Recommended next action

1. Do not re-record the grammar hash against the existing n=5 artifact.
2. Archive or explicitly mark `outputs/cluster1/task_agnostic_g_all_n5_l4_rerun.jsonl`
   as a previous-grammar or incompatible artifact for this gate.
3. Generate a new n=5 task-agnostic artifact under the current grammar in a
   controlled non-Modal, non-GPU, non-development-scale run only when approved.
4. Validate the new n=5 artifact with the current grammar and semantic validator.
5. Re-run:
   - `.venv/bin/python -m pytest cluster1/tests/test_grammar_acceptance.py -v`
   - `.venv/bin/python -m pytest cluster1/tests/test_api_coverage.py -v`
   - the discovered Phase -1 hash gate command
6. Re-record the hash only after the current grammar, smoke fixtures, API
   coverage, and new n=5 artifact all pass.

## Go/no-go for hash re-recording

Hash re-recording now: `NO`.

Blockers:

- Existing n=5 compatibility remains 14/45 accepted and 31/45 rejected.
- Five rejected rows have `compile_success=true`, but are incomplete under the
  current structural launcher contract.
- The active old artifact has not been archived/excluded or replaced by a
  current-grammar n=5 artifact.

## Go/no-go for n=5 rerun

n=5 rerun under current grammar: `GO_AFTER_APPROVAL`.

The audit found no evidence that the current grammar is too strict with respect
to the pinned `triton.language` API reference for the five diagnostic rows. A
fresh n=5 run under the current grammar is the correct next compatibility
artifact, but this audit did not run generation and did not invoke Modal or GPU
jobs.

## Remaining risks

- The old artifact's `compile_success=true` semantics should be reviewed before
  using it as compatibility evidence in future gates, because lines 31-35 do not
  contain complete launch wrappers.
- The current API coverage gate checks `tl.*` names/signatures, not every
  structural launcher rule. Structural compatibility remains covered by grammar
  acceptance fixtures and n=5 validation.
- A fresh current-grammar n=5 artifact may surface new incompatibilities that
  are not visible in the stale artifact.
