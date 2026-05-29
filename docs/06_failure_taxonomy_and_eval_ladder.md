# Failure Taxonomy And Evaluation Ladder

## Purpose

This document defines how generated Triton-kernel rows move through evaluation stages and how failures are named. It connects Cluster 1 compile-only evaluation with Cluster 2 correctness evaluation so report-facing docs use the same Level 0/1/2 ladder and F0/F1/F2/F3 failure semantics.

This file is citation-grade documentation for methodology language. Raw row data remains in `outputs/`, and artifact identities remain governed by `docs/05_artifacts_and_results_registry.md`.

## Plain-Language Overview

Generated code can fail before it is useful:

- Python may be unable to parse the generated source.
- The source may parse but expose the wrong callable interface for the harness.
- The callable may have the right surface but fail to compile or launch as Triton code.
- The code may compile and launch but return numerically wrong outputs.
- The evaluation machinery itself may fail, for example because a correctness payload is malformed.

The failure taxonomy separates those cases. This matters because Cluster 2 correctness feedback is only allowed for numerical correctness failures. It must not become a hidden parser, signature, compile, or infrastructure repair loop.

## Evaluation Ladder

| Level | Meaning | Typical evidence | Used in |
|---|---|---|---|
| Level 0 | Parse, signature, and surface validity | AST parser checks, public launcher checks, F0 codes | Cluster 2, shared eval |
| Level 1 | Compile and runtime launch | `compile_success`, F1 codes | Cluster 1, Cluster 2 |
| Level 2 | Numerical correctness | `functional_success`, repair/eval shape checks, F2 codes | Cluster 2 |
| Infrastructure/eval pipeline | Evaluation machinery failure rather than model-code success | F3 codes | Cluster 2 and analyzer |

Cluster 1 stops at Level 1. Its primary outcome is `compile_success`. Cluster 1 does not run Level 2 and does not establish numerical correctness.

Cluster 2 uses the ordered Level 0/1/2 ladder for generated C and G+C rows. Level 2 is reached only after earlier gates pass. Infrastructure and payload failures are recorded separately as F3 failures.

## Failure-Code Taxonomy

The canonical code registry is `shared/eval/failure_taxonomy.py`. The verified code families are:

| Family | Meaning | Verified canonical codes |
|---|---|---|
| F0_* | Parse, signature, grammar, or surface failure before compile/launch | `F0_PARSE`, `F0_GBNF_PARSE`, `F0_SEMANTIC_INVALID`, `F0_GRAMMAR_INVALID`, `F0_NO_DECORATOR`, `F0_BAD_SIGNATURE`, `F0_SURFACE_VIOLATION` |
| F1_* | Compile or runtime-launch failure | `F1_COMPILE`, `F1_RUNTIME` |
| F2_* | Numerical or shape correctness failure after reaching Level 2 | `F2_NUMERIC_LARGE`, `F2_NUMERIC_NAN`, `F2_SHAPE_MISMATCH` |
| F3_* | Infrastructure, timeout, race, out-of-bounds, or evaluation-pipeline failure | `F3_EVAL_PIPELINE`, `F3_OOB`, `F3_RACE`, `F3_TIMEOUT` |

Current report-scale artifacts contain only a subset of these codes. The full registry above is methodologically valid because it is implemented in `shared/eval/failure_taxonomy.py`; row-level claims should still cite the artifact-specific distributions in `docs/07_analysis_and_statistics.md`.

### Cluster 3 P repair fires on F1_COMPILE

Cluster 3 P observes `F1_COMPILE` only. `F1_RUNTIME` terminates in v1.
No new failure codes are added for P; P outcomes are represented through
Cluster 3 row fields and stop reasons instead of new F-code names.

F2 remains the C-loop boundary. F3 remains infrastructure/eval-pipeline and is
not treated as P success.

## Grammar-Validity Failures

G rows have two grammar-related layers:

- token-level grammar-guided decoding with GBNF/XGrammar,
- offline semantic post-validation.

`grammar_active` means grammar guidance was attempted. It is not acceptance. `grammar_valid` means joint acceptance:

```text
grammar_valid = gbnf_parse_valid AND semantic_valid
```

A G or G+C row is grammar-accepting only when both layers pass. `rejection_layer` identifies whether the row failed at the GBNF parse layer or the semantic validator. Grammar failures are surface-level failures and map to F0-style semantics when converted to canonical failure codes.

This is not a claim that the GBNF fully models Triton. Semantic validation exists because surface and harness constraints cannot all be represented safely as a context-free grammar.

## Cluster 1 Semantics

Cluster 1 is compile-only:

- `compile_success` is the primary Cluster 1 outcome.
- Cluster 1 does not run Level 2 numerical correctness.
- Cluster 1 does not claim functional correctness.
- Cluster 1 does not run repair loops.
- Cluster 1 does not run timing, profiling, or speedup evaluation.

For preliminary functional analysis, none and G rows from Cluster 1 normalize `functional_success` to `False`/unproven. `compile_success=True` is preserved separately as structural evidence and must not be treated as `functional_success=True`.

## Cluster 2 Semantics

Cluster 2 generated rows for C and G+C are evaluated through Level 2 when earlier gates pass. Its repair policy is intentionally narrow:

- C repair fires only when Level 2 ran and produced an F2 numerical or shape correctness failure.
- F0 failures terminate without repair feedback.
- F1 failures terminate without repair feedback.
- F3 failures terminate without correctness feedback unless a later phase explicitly documents a different safe policy.

This boundary prevents correctness feedback from becoming parse, signature, compile, or infrastructure repair.

## F3_EVAL_PIPELINE Policy

`F3_EVAL_PIPELINE` records an evaluation-pipeline or payload failure, not a successful generated-kernel result. The current accepted policy is:

- It is not counted as `functional_success`.
- It is not counted as `compile_success` unless independent Level 1 or Level 2 compile-pass evidence is present.
- It is excluded from compile-success rate denominators in condition-rate summaries.
- It is treated as `compile_success=False` in matched-pair analysis when independent compile-pass evidence is absent.
- It must remain visible as a caveat and must not be hidden as a success row.

The current G+C artifact contains five `F3_EVAL_PIPELINE` rows. The analyzer output at `outputs/analysis/factorial_2x2_preliminary.json` exists and has `metadata.reportable=true` under explicit scale-tier annotation, so F3, coverage, P-deferred, and provenance caveats must still be carried into report planning.

## Examples

| Example | Level/family | Typical code |
|---|---|---|
| Source cannot parse as Python | Level 0 / F0 | `F0_PARSE` |
| Public launcher has the wrong signature | Level 0 / F0 | `F0_BAD_SIGNATURE` |
| Triton compilation fails | Level 1 / F1 | `F1_COMPILE` |
| Kernel launch fails at runtime | Level 1 / F1 | `F1_RUNTIME` |
| Kernel compiles but returns NaN or Inf | Level 2 / F2 | `F2_NUMERIC_NAN` |
| Kernel compiles but output shape is wrong | Level 2 / F2 | `F2_SHAPE_MISMATCH` |
| Correctness payload is malformed | Infrastructure/eval pipeline / F3 | `F3_EVAL_PIPELINE` |

## What This Document Does Not Claim

- It does not claim timing, profiling, speedup, or performance results.
- It does not claim Cluster 1 functional correctness.
- It does not claim full 2^3/P results.
- It does not hide F3 rows as successes.
- It does not claim compile success proves correctness.

## Traceability

| Concept | Code path | Test/audit path | Artifact evidence | Caveat |
|---|---|---|---|---|
| Canonical failure-code registry | `shared/eval/failure_taxonomy.py` | `shared/tests/test_failure_taxonomy.py`, `shared/tests/test_eval_failure_taxonomy.py` | Failure-code fields in G, C, and G+C artifacts | none baseline uses legacy/no canonical failure codes |
| Level 0 parse/signature gate | `shared/eval/levels/level0_parse.py`, `shared/eval/levels/level0_ast_sanitizer.py` | `shared/tests/test_eval_level0_parse.py`, `shared/tests/test_eval_level0_ast_sanitizer.py`, `cluster2/tests/test_generated_eval_ladder.py` | C artifact has 180 `F0_PARSE` rows; G+C has 12 `F0_PARSE` rows | Artifact distributions do not exercise every F0 code |
| Level 1 compile/launch gate | `shared/eval/levels/level1_compile.py`, `cluster1/validation/compile_check.py` | `shared/tests/test_eval_level1_compile.py`, `cluster1/tests/test_compile_check.py`, `cluster2/tests/test_generated_eval_ladder.py` | none/G compile fields; G and G+C F1 codes | Cluster 1 compile-only does not imply Level 2 correctness |
| Level 2 correctness gate | `shared/eval/levels/level2_correctness.py` | `shared/tests/test_eval_level2_correctness.py`, `shared/tests/test_eval_pipeline_with_level2.py` | C and G+C functional fields | Current C and G+C artifacts have no functional successes |
| Cluster 1 functional normalization | `shared/analysis/factorial.py`, `shared/eval/adapter_cluster1.py` | `shared/tests/test_factorial_analysis.py`, `audits/factorial_cluster1_functional_success_normalization_fix_report.md` | none and G artifacts | Functional success is false/unproven, not measured false by Level 2 |
| Cluster 2 F2-only repair boundary | `cluster2/feedback/repair_loop.py`, `cluster2/feedback/prompts.py` | `cluster2/tests/test_repair_loop.py`, `cluster2/tests/test_feedback_prompts.py`, `cluster2/tests/test_generated_eval_ladder.py` | G+C has four F2 rows; current C has only F0 rows | Phase 5 documents semantics, not repair effectiveness |
| F3_EVAL_PIPELINE policy | `shared/analysis/factorial.py`, `cluster2/experiments/run_cluster2_modal.py` | `audits/g_plus_c_correctness_payload_failure_fix_report.md`, `audits/factorial_f3_eval_pipeline_compile_success_decision_report.md`, `shared/tests/test_factorial_analysis.py` | G+C has five `F3_EVAL_PIPELINE` rows | Analyzer output is reportable, but F3 rows remain visible caveats |
