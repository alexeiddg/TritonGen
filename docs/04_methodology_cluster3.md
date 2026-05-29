# Cluster 3 Methodology

## Status

- Status: v1 implemented locally through Phase 10.
- Phase 11 Modal smoke has not been run unless a later report explicitly registers it.
- Phase 11 n=1 Modal smoke requires explicit user approval.
- Paper-scale Cluster 3 results are deferred; paper-scale deferred remains the active scale policy.
- Cluster 3 v1 is development/pre-Modal-smoke until Phase 11 is explicitly authorized and run.

This document describes implemented local v1 surfaces and claim boundaries. It
does not register output rows, measured lift, or paper-scale results.

## Factor Definition

Cluster 3 adds the P factor:

- P = compile-error feedback repair.
- P-containing conditions: `P`, `G+P`, `C+P`, and `G+C+P`.
- No-P controls: `none`, `G`, `C`, and `G+C`.

P is separate from G and C. G remains grammar-guided decoding plus semantic
post-validation. C remains Level 2 correctness-feedback repair. P is bounded to
compile-error feedback after a generated candidate reaches `F1_COMPILE`.

## Eval Ladder Integration

Cluster 3 uses the existing evaluation ladder:

- Level 0: parse, signature, and surface validation.
- Level 1: compile and runtime launch.
- Level 2: numerical correctness.

P observes only `F1_COMPILE`. P does not observe F0, `F1_RUNTIME`, F2, or F3.
F1_RUNTIME is deferred to v2. C remains F2-gated and is not changed by P.

## Dispatcher Policy

The Cluster 3 dispatcher applies these terminal and routing rules:

- F0 terminates.
- `F1_COMPILE` routes to P when P is active.
- `F1_RUNTIME` terminates in v1.
- F2 routes to C only when C is active.
- F3 terminates as an infrastructure/eval-pipeline failure.

P does not add new failure codes. No new failure codes were introduced for P.
P outcomes are represented through Cluster 3 row fields and stop reasons.

## P Repair Policy

`PSeedAttempt` uses cached attempt-0 evaluation. Attempt 0 is not regenerated or
re-evaluated. The default P repair budget is `DEFAULT_P_REPAIR_BUDGET = 5`.

Stop reasons are:

- `p_compile_repaired_then_success`
- `p_compile_repaired_f2_observed`
- `p_budget_exhausted`
- `p_post_compile_f3_observed`
- `p_f3_without_compile_evidence`
- `p_terminal_non_repairable`
- `p_not_applicable`

These stop reasons record local repair-loop outcomes. They are not paper-scale
evidence and do not establish Level 2 gains.

## Feedback Content Boundary

P feedback is compile-error-only. It must not include Level 2 numerical or
correctness details, private eval shapes, or speedup/profiler/performance/
token/benchmark terms. The diagnostic note is deterministic.

The compile-error excerpt cap is 2000 chars. The full raw error hash is stored
as `sha256` where applicable. LLVM/PTX are allowed in P feedback because they
can appear in compiler diagnostics.

## Schema Fields

Cluster 3 uses `CLUSTER3_RESULTS_SCHEMA_VERSION = 1`.

The v1 row schema includes:

- `p_compile_repair_succeeded`
- `p_repair_changed_terminal_class`
- `p_repair_stop_reason`
- `p_terminal_failure_code`
- `c_loop_fired`
- `c_loop_source`
- `c_terminal_failure_code`
- terminal source provenance fields
- `trace_summary`

There is no `p_helped` row field. Any `p_helped` diagnostic belongs to analyzer
output, not raw Cluster 3 rows.

## Analyzer Semantics

`compile_feedback_active` is the P factor in analyzer semantics.
`perf_feedback_active` remains for backward compatibility only. The
analyzer-derived `p_helped` diagnostic is conservative and `PENDING_RESEARCH`.

A three-way interaction is reportable only when all eight cells are populated.
Current Cluster 3 v1 local implementation does not populate all eight cells and
does not support full 2^3 result claims.

## Replay And No-P Controls

P comparisons use paired no-P controls:

- P ↔ none
- G+P ↔ G
- C+P ↔ C
- G+C+P ↔ G+C

The no-P pair manifest path is:

```text
cluster3/contracts/no_p_pair_manifest.json
```

## Scale Policy

Cluster 3 runs local tests first. Phase 11 n=1 Modal smoke requires explicit
user approval. Phase 12 n=5 development scale requires explicit user approval.
Paper-scale n=20 is deferred until smoke/dev gates pass.

No Phase 11, Phase 12, or paper-scale P artifacts are registered by this
document.

## Implementation Traceability

| Surface | Path |
|---|---|
| Constants and condition registry | `cluster3/constants.py` |
| Dispatcher | `cluster3/feedback/dispatcher.py` |
| P repair loop | `cluster3/feedback/compile_error_repair.py` |
| P prompt construction | `cluster3/feedback/prompts.py` |
| P sanitizer | `cluster3/feedback/sanitizer.py` |
| C-loop adapter | `cluster3/feedback/c_loop_adapter.py` |
| Correctness adapter | `cluster3/modal/correctness_runner.py` |
| Row dataclass and schema version | `cluster3/results/dataclass.py` |
| Durable logger | `cluster3/results/logger.py` |
| No-P pair resolver | `cluster3/replay/no_p_pairs.py` |
| No-P manifest builder | `cluster3/replay/build_no_p_pair_manifest.py` |
| Analyzer support | `shared/analysis/factorial.py` |
| Boundary tests | `cluster3/tests/test_cluster3_boundary.py` |
| F1 fixture smoke tests | `cluster3/tests/test_p_repair_f1_fixtures.py` |

Cluster 3 correctness evaluation is local and reuses existing Cluster 2 Modal
surfaces through adapters. Cluster 3 v1 does not create a new Modal correctness
surface.
