# Cluster 3 - Compile-Error Repair Loop (P-factor v1)

**Status: v1 implemented locally through Phase 10.**

Development-scale/paper-scale runs are deferred until paid Modal gates. Scope:
compile-error feedback repair only.

The report-facing methodology owner is `docs/04_methodology_cluster3.md`. The
implementation contract remains `docs/cluster3_implementation_specification.md`.

## What Cluster 3 Adds

Cluster 3 adds P, a compile-error feedback repair factor for generated Triton
kernels. P is bounded to `F1_COMPILE` evidence and does not change Cluster 1 G
or Cluster 2 C semantics.

## Conditions

P-containing conditions are:

- `P`
- `G+P`
- `C+P`
- `G+C+P`

Their no-P controls are `none`, `G`, `C`, and `G+C` through
`cluster3/contracts/no_p_pair_manifest.json`.

## What P Observes

P observes `F1_COMPILE` only.

## What P Does Not Observe

P does not observe F0, `F1_RUNTIME`, F2, or F3. `F1_RUNTIME` is deferred to v2.
F3 remains infrastructure/eval-pipeline failure, not P success.

## Relationship To Cluster 2

Generation and correctness surfaces are reused through local adapters over the
existing Cluster 2 Modal surfaces. C remains F2-gated. Cluster 3 P does not
turn C into a compile-error repair loop and does not introduce new failure
codes.

## Key Files

| Surface | Path |
|---|---|
| Constants | `cluster3/constants.py` |
| Dispatcher | `cluster3/feedback/dispatcher.py` |
| P repair loop | `cluster3/feedback/compile_error_repair.py` |
| P prompts and sanitizer | `cluster3/feedback/prompts.py`, `cluster3/feedback/sanitizer.py` |
| C adapter | `cluster3/feedback/c_loop_adapter.py` |
| Correctness adapter | `cluster3/modal/correctness_runner.py` |
| Row schema and logger | `cluster3/results/dataclass.py`, `cluster3/results/logger.py` |
| No-P replay controls | `cluster3/replay/no_p_pairs.py`, `cluster3/replay/build_no_p_pair_manifest.py` |
| Analyzer support | `shared/analysis/factorial.py` |

## Tests

- `cluster3/tests/test_dispatcher.py`
- `cluster3/tests/test_p_prompts.py`
- `cluster3/tests/test_p_sanitizer.py`
- `cluster3/tests/test_p_repair_loop.py`
- `cluster3/tests/test_cluster3_schema.py`
- `cluster3/tests/test_cluster3_logger.py`
- `cluster3/tests/test_correctness_runner_adapter.py`
- `cluster3/tests/test_run_cluster3_modal_cli.py`
- `cluster3/tests/test_replay_pairing.py`
- `cluster3/tests/test_p_repair_f1_fixtures.py`
- `cluster3/tests/test_cluster3_boundary.py`
- `cluster3/tests/test_docs_consistency.py`

## Out Of Scope

- profiler
- speedup
- timing
- RL
- performance feedback
- paper-scale claims

## Next Gate

Phase 11 n=1 Modal smoke requires explicit user approval.
