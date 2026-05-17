# Cluster 2 - Correctness Feedback Control

**Status:** Phase 0 metadata/hash surfaces implemented.

Cluster 2 is a controlled study of correctness-feedback control for Triton
kernel generation on the three locked Cluster 1 KernelBench Level 1 archetypes:
ReLU/pointwise, Softmax/reduction, and GEMM/tiled matmul.

## Scope

- Current iteration scope: temporary 2² subset analysis over `none`, `G`, `C`,
  and `G+C`.
- Primary comparison: `C` versus frozen Cluster 1 `none` replay controls.
- Secondary comparison: `G+C` versus frozen Cluster 1 `G` replay controls.
- New generation conditions: only `C` and `G+C`.
- Replay-only controls: `none` and `G`.
- Equal attempts means equal candidate-source count, not token cost, wall time,
  or GPU cost.

The full 2³ factorial over G, C, and P remains the defined project goal.
P-containing cells are deferred for this iteration and are not included in
current paper-claiming outputs. This is a current-status scope statement, not a
methodology realignment.

Template replay controls are frozen from:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl`

The task-agnostic G paper path is blocked until an `n=20` artifact is frozen and
the Phase -1 manifests are refreshed.

## Phase 0 Surfaces

Phase 0 adds only metadata, source-hash helpers, and isolated import scaffolds:

- `shared/eval/content_hashes.py`
- `shared/eval/correctness_shapes.py`
- `cluster2/constants.py`
- `cluster2/results/dataclass.py`
- `cluster2/replay/manifest.py`
- `cluster2/modal/`
- tracked Phase -1 manifests under `cluster2/contracts/`

It does not add Cluster 2 runtime orchestration, repair loops, Modal generation,
or correctness execution.

## Boundaries

- Do not edit Cluster 1 generation, grammar, prompt, result, runner, analyzer, or
  Modal entry-point files.
- Do not edit `shared/modal_harness/generation.py`,
  `shared/modal_harness/schemas.py`, or `shared/modal_harness/smoke.py`.
- Do not regenerate `none` or `G`; replay them from frozen Cluster 1 artifacts.
- Do not add timing, profiling, speedup, or performance fields to C2 JSONL rows.
- Do not claim fixed resolved model/tokenizer revisions for replay controls when
  frozen Cluster 1 artifacts record those revisions as unavailable.
