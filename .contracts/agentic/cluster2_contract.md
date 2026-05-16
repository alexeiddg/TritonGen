# Cluster 2 Contract

Cluster 2 tests whether correctness-feedback control improves convergence on
three locked Triton kernel archetypes under fixed prompts and matched
candidate-source counts.

## Locked Comparisons

- Primary: `C` versus frozen Cluster 1 `none` replay controls, paired by
  `(kernel_class, dtype, base_seed)`.
- Secondary: `G+C` versus frozen Cluster 1 `G` replay controls, paired by
  `(kernel_class, dtype, base_seed)`.
- `none` and `G` are replay-only and must not invoke model generation.
- Only `C` and `G+C` may invoke new Cluster 2 generation.
- Unmatched generated-vs-replay analyses are excluded from primary claims.

Template replay controls come from:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl`

The task-agnostic G paper path is blocked until an `n=20` artifact is frozen and
the Phase -1 manifests are refreshed.

## Paired Replay Enforcement

The frozen Cluster 1 manifest is the canonical source of replay seed schedules.
For each generated Cluster 2 row, the runner must consume the corresponding
replay seed, prompt hash, model identity, dtype, temperature, and token budget
before generation starts. Missing seed schedules, duplicate pairs, prompt/model
mismatches, dtype mismatches, temperature mismatches, or token-budget mismatches
are hard failures; the runner must not synthesize replacement seeds.

Replay rows must expose the frozen pairing metadata in Cluster 2 result rows.
Generated rows must expose the replay pair they consumed. Aggregation must use
paired statistics over matched seed cells, including paired bootstrap lift and
binary discordance/McNemar-style summaries where applicable.

The canonical path for Cluster 2 paper-table generation is
`shared/analysis/factorial.py`. It must be used for Level 2
`functional_success` factorial summaries, paired `C` vs `none` and `G+C` vs `G`
comparisons, missing-P-cell reporting, and Table 1-3 structured output.
Parallel ad hoc analysis scripts are diagnostic only and are not canonical
paper-table sources. `compile_success` output from the analyzer is secondary
structural-validity diagnostic output, not the headline Cluster 2 claim.

## Cluster 1 Freeze

Do not modify:

- `shared/modal_harness/generation.py`
- `shared/modal_harness/schemas.py`
- `shared/modal_harness/smoke.py`
- Cluster 1 generation, grammar, prompt, result, runner, analyzer, or validation
  files.

`G+C` may use frozen G behavior only through byte-hash-gated adapters. The C2
adapter must compile/load grammar with the tokenizer path/revision used by the
C2 generation path, without modifying the Cluster 1 grammar loader.

## Claim Wording

If frozen Cluster 1 artifacts do not contain resolved model/tokenizer revisions,
the claim must say fixed `model_id`, not fixed resolved revision. Revision
pinning for replay controls may be claimed only when revisions are actually
present in the frozen artifacts.

## Output Boundary

C2 JSONL rows must contain no timing, profiling, speedup, or performance fields.

## Synthetic F2 Repair Smoke Precondition

Before any Phase 15 or paper-scale Cluster 2 `C` or `G+C` run, the synthetic F2
repair smoke must pass for all three canonical archetypes:

- `cluster2/tests/fixtures/f2_corrupted_relu.py`
- `cluster2/tests/fixtures/f2_corrupted_softmax.py`
- `cluster2/tests/fixtures/f2_corrupted_matmul.py`

The smoke is a mechanism-validity gate only. It must show:

- iteration 0 is the seeded corrupted fixture candidate;
- iteration 0 reaches Level 2 and fails with an existing F2 code;
- repair feedback is constructed only after that F2 failure;
- `feedback_content` contains public numerical correctness information only;
- repair iterations are recorded contiguously;
- convergence or budget exhaustion is recorded explicitly;
- canonical Modal rows record non-empty Modal correctness call/input IDs, repair
  rows record non-empty Modal generation call/input IDs, and model/tokenizer
  revisions are immutable full 40-character commit SHAs rather than floating
  branch names;
- the trace schema passes `validate_canonical_f2_smoke_artifacts()` for all
  three archetypes;
- canonical paper-gate artifacts were produced by the Modal smoke path, not by
  local mock repair/evaluation.

Canonical smoke artifacts live at:

- `outputs/cluster2/smoke_f2_repair_relu.jsonl`
- `outputs/cluster2/smoke_f2_repair_softmax.jsonl`
- `outputs/cluster2/smoke_f2_repair_matmul.jsonl`

The paper-scale runner must refuse to start if these artifacts are missing,
older than 30 days, stale relative to the fixture hashes or fixture mtimes,
missing Modal provenance, using model/tokenizer revisions that differ from the
paper run, malformed, or failing validation. The validated smoke trace
`feedback_content` fields are the canonical demonstration of C repair-loop
function and the canonical source for the Fix 4 manual audit of actual C
feedback prompts. This smoke must not be aggregated into paper-scale
convergence, grammar, speed, or model-quality claims.
