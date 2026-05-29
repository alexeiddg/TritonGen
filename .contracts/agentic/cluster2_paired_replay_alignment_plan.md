# Cluster 2 Paired Replay Alignment Plan

**Status:** implementation alignment plan
**Date:** 2026-05-15
**Owner:** single implementer, no parallel work graph
**Scope:** deterministic paired-by-seed replay-control alignment for Cluster 2
**Execution policy:** smoke-scale validation only; always use `.venv/bin/python`; do not run paper-scale jobs

## Purpose

This plan realigns the Cluster 2 seed-pairing fix with the scientific contract:
primary replay-control comparisons must be within-subject comparisons over the
same frozen Cluster 1 seed schedule.

The intended claim is:

```text
For the same candidate seed/prompt/model configuration that frozen none or G
would have produced, does C or G+C produce a better functional outcome?
```

The implementation must not drift into a broader redesign of the factorial,
grammar behavior, correctness logic, repair-loop semantics, token-cost matching,
or wall-time matching.

## Current Audit Snapshot

Observed frozen artifacts:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl`
- `outputs/cluster1/final_g_l4_n20.jsonl`

Current raw JSONL row state:

- `generation_seed` is present on every inspected row.
- `kernel_class`, `kernel_name`, `dtype`, `model_id`, `temperature`, `source`,
  `run_id`, and `unique_solution_hash` are present.
- `base_seed`, `attempt_index`, `generation_index`, `prompt_sha256`,
  `model_revision`, `tokenizer_revision`, and `max_new_tokens` are not present in
  raw JSONL rows.
- Per `(kernel_class, dtype)` cell, raw `generation_seed` values are dense and
  zero-based for both selected frozen artifacts.

Current sidecar state:

- `outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json` exists.
- `outputs/cluster1/final_g_l4_n20.jsonl.meta.json` exists.
- Both sidecars currently contain run-level metadata and `run_config`, but do
  not contain an explicit `seed_schedule`.

Current manifest state:

- `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` is schema
  version `2`.
- It already records `seed_schedule` for selected replay artifacts.
- Selected `none` and template-upper-bound `G` artifacts each have 9 schedule
  records and 180 `row_records`.

Conclusion: seed provenance appears recoverable without regenerating frozen
artifacts. The remaining contract gap is to make sidecars and loaders treat the
schedule as explicit, mandatory provenance rather than inferred convenience.

## Non-Negotiable Boundaries

- Do not regenerate frozen Cluster 1 artifacts unless seed provenance is proven
  unrecoverable from raw rows, sidecars, manifests, and generation logs.
- Do not edit Cluster 1 generation, grammar, prompts, result schema, or frozen
  behavior.
- Do not change grammar behavior for `G` or `G+C`.
- Do not change correctness gates or repair-loop semantics.
- Do not add token-cost, latency, wall-time, profiler, speedup, or performance
  matching.
- Do not silently fall back to newly generated seeds.
- Do not allow unmatched generated-vs-replay comparisons into primary claims.

## Required Contract

The canonical pair key is:

```text
(kernel_class, dtype, base_seed)
```

The required pairing envelope for every frozen schedule entry is:

- `condition`
- `kernel_class`
- `kernel_name`
- `dtype`
- `base_seed`
- `generation_seed`
- `attempt_index`
- `generation_index`
- `prompt_sha256`
- `model_id`
- `model_revision`
- `tokenizer_revision`
- `temperature`
- `max_new_tokens`
- `line_number`
- `replay_pair_id`

For selected frozen Cluster 1 artifacts, `base_seed` must equal the frozen
`generation_seed` for attempt-zero replay pairing. Missing resolved revisions
may use the explicit sentinel `unavailable_in_frozen_cluster1_artifact`; unknown
revision fields must not be silently treated as verified revision pinning.

## Implementation Phases

### Phase 1: Freeze Provenance Audit

Audit both selected frozen artifacts and sidecars with `.venv/bin/python`.

Acceptance criteria:

- Every raw frozen row has `generation_seed`, `kernel_class`, `dtype`,
  `kernel_name`, `model_id`, and `temperature`.
- Per artifact and per `(kernel_class, dtype)` cell, `generation_seed` is dense
  and zero-based over the available frozen rows.
- Sidecars are confirmed to either contain explicit seed schedules or are
  classified as needing deterministic backfill.
- Any missing field is classified as recoverable from existing provenance or as
  `REGENERATION_REQUIRED`.

Do not modify JSONL artifact bytes in this phase.

### Phase 2: Sidecar Seed Schedule Backfill

Update the `.meta.json` sidecars, not the frozen JSONL artifacts, to record an
explicit `seed_schedule` derived from existing frozen provenance.

Backfill source priority:

1. Raw row `generation_seed`, `kernel_class`, `kernel_name`, `dtype`,
   `model_id`, and `temperature`.
2. Sidecar `run_config.max_new_tokens`, `run_config.model_id`, and
   `run_config.temperature`.
3. Existing manifest `row_records` and `seed_schedule` for `prompt_sha256`,
   `line_number`, `row_sha256`, `source_sha256`, and explicit unavailable
   revision sentinels.
4. Generation logs only if manifest and sidecar provenance disagree.

Acceptance criteria:

- Both selected sidecars contain a deterministic `seed_schedule`.
- Sidecar schedule entries match manifest schedule entries byte-for-byte for
  pair identity fields.
- Sidecar schedule backfill preserves frozen JSONL hashes.
- If a schedule cannot be reconstructed, stop and classify as
  `REGENERATION_REQUIRED`.

### Phase 3: Manifest Contract Hardening

Harden `cluster2/contracts/frozen_cluster1_artifacts_manifest.json` as the
runner-facing contract.

Acceptance criteria:

- Every selected replay artifact has `seed_schedule.schedule_type =
  "paired_by_seed"`.
- Each cell schedule records dense `base_seeds`, `generation_seeds`,
  `attempt_indexes`, `generation_indexes`, `line_numbers`, and
  `replay_pair_ids`.
- Manifest records artifact-level invariants:
  `base_seed_equals_generation_seed`, dense zero-based schedule, unique
  `replay_pair_id`, and one replay row per pair key.
- Manifest references the updated sidecar hashes after sidecar backfill.
- Loader failure text names the artifact id, cell, and missing or mismatched
  schedule field.

### Phase 4: Replay Loader Enforcement

Harden `cluster2/replay/manifest.py`.

Acceptance criteria:

- Loading selected replay controls requires `seed_schedule`.
- Missing, malformed, sparse, duplicate, or incomplete schedules are hard
  failures.
- `replay_seed_schedule_for_condition(...)` is the only source for generated
  `C` and `G+C` base seeds.
- The loader exposes deterministic ordering by
  `(kernel_class, dtype, base_seed, line_number)`.
- No loader path synthesizes replacement seeds from `range(n)` unless it is
  validating equality against a manifest schedule.

### Phase 5: Replay Adapter Propagation

Harden `cluster2/replay/cluster1_controls.py`.

Acceptance criteria:

- Replay candidates are selected by manifest schedule, not by incidental raw
  JSONL row order alone.
- Candidate fields preserve `generation_seed`, `base_seed`,
  `frozen_attempt_index`, `generation_index`, `prompt_sha256`, model identity,
  tokenizer/model revision sentinels, `temperature`, `max_new_tokens`,
  `replay_pair_id`, artifact id, artifact hash, and row hash.
- Missing schedule metadata fails before any coverage-failure fallback.
- Replay result rows expose the frozen pair metadata under `replay_metadata`.

### Phase 6: Runner Seed Routing

Harden `cluster2/experiments/run_cluster2_modal.py`.

Acceptance criteria:

- `C` consumes the selected frozen `none` seed schedule.
- `G+C` consumes the selected frozen `G` seed schedule.
- Attempt zero generation uses the replay `generation_seed`.
- Repair attempts derive only from the paired `base_seed` by the existing repair
  seed rule.
- Before generation starts, the runner validates:
  `kernel_class`, `dtype`, `base_seed`, `prompt_sha256`, `model_id`,
  known revisions, `temperature`, and `max_new_tokens`.
- Mismatch fails loudly before Modal generation or correctness calls.
- Output generated rows record `replay_pair_id`,
  `replay_control_condition`, `replay_base_seed`, `replay_generation_seed`,
  and the same prompt/model/token metadata used for validation.

### Phase 7: Paired Aggregation

Harden `shared/eval/aggregation.py`,
`shared/eval/metrics/equal_attempts.py`, and
`shared/analysis/factorial.py`.

Acceptance criteria:

- Primary lift uses matched cells only.
- `pass_rate_within_n` for replay controls is computed per pair cell, not as an
  unpaired row-population statistic.
- Lift CI uses paired bootstrap over matched cells.
- Binary treatment-control summaries include McNemar-style discordance counts
  and p-value where applicable.
- Analysis rejects missing replay pair, missing treatment pair, duplicate replay
  pair, duplicate generated attempt, metadata mismatch, condition mismatch, and
  schedule mismatch.
- Unpaired Fisher-style primary comparisons are removed from the Cluster 2
  primary path. If retained elsewhere, they must be explicitly diagnostic.

### Phase 8: Contract and Research Text

Keep contract text aligned with the implementation.

Acceptance criteria:

- `.contracts/agentic/cluster2_contract.md` states that primary and secondary
  Cluster 2 comparisons are paired by `(kernel_class, dtype, base_seed)`.
- `.contracts/research/research_scope.md` states that replay-control primary
  claims depend on matched-pair generation.
- Both documents exclude unmatched generated-vs-replay analysis from primary
  claims.
- Both documents name the runner as responsible for seed alignment before fresh
  generation begins.

### Phase 9: Tests

Add or maintain focused CI coverage.

Required tests:

- Frozen selected artifacts have recoverable seed metadata.
- Selected sidecars contain explicit `seed_schedule`.
- Manifest rejects missing schedules.
- Manifest rejects sparse, duplicate, or mismatched schedules.
- Replay adapter maps fresh/replay pair keys deterministically.
- Runner consumes replay seeds for `C` and `G+C`.
- Runner rejects prompt/model/dtype/temperature/token mismatch before generation.
- Aggregation rejects unpaired comparisons.
- Aggregation emits paired bootstrap lift and McNemar-style binary summaries.

Targeted commands:

```bash
.venv/bin/python -m pytest cluster2/tests/test_replay_controls.py -v
.venv/bin/python -m pytest cluster2/tests/test_replay_manifest.py -v
.venv/bin/python -m pytest shared/tests/test_aggregation.py -v
```

Broader smoke regression:

```bash
.venv/bin/python -m pytest shared/tests cluster2/tests -v
```

### Phase 10: Smoke Validation

Run only the smoke-scale Modal validation after targeted tests pass:

```bash
/Users/alexeidelgado/miniconda3/bin/modal run -m cluster2.experiments.run_cluster2_modal \
  --condition C \
  --kernel-class elementwise \
  --scale-tier smoke \
  --n 3 \
  --dtypes fp32 \
  --modal-generation-gpu L4 \
  --modal-eval-gpu L4 \
  --repair-budget 1 \
  --output outputs/cluster2/smoke_seed_pairing_validation.jsonl
```

Manual smoke check:

- For each fresh `C` row, find the frozen `none` schedule entry by
  `(kernel_class, dtype, base_seed)`.
- Verify identical `base_seed`, `prompt_sha256`, `model_id`, known revisions,
  `dtype`, `temperature`, `max_new_tokens`, and kernel identity.
- Confirm the only allowed differences are condition, grammar activation, and
  downstream generation/eval/repair fields.
- Run the paired analyzer and verify paired statistics are emitted.
- Confirm the analyzer rejects the smoke output if any generated row lacks a
  matched replay row.

## Code Review Checklist

Use this checklist to prevent scope drift:

- Does the patch edit only manifest, replay, runner, aggregation, tests, and
  contract surfaces named in this plan?
- Did any change alter Cluster 1 generation, grammar, prompt rendering, or
  frozen JSONL contents?
- Is every new generated condition seed derived from a replay schedule entry?
- Is every schedule-missing path a hard failure?
- Are comparisons keyed by `(kernel_class, dtype, base_seed)`?
- Are prompt/model/token metadata validated before generation?
- Are sidecars and manifest mutually consistent?
- Are unmatched comparisons excluded from primary statistics?
- Are tests exercising failure paths, not only happy paths?

## Decision Criteria

Classify the completed fix as `PAIRED_REPLAY_VALID` only if:

- selected frozen artifacts have explicit seed provenance in sidecars and
  manifest;
- fresh `C` and `G+C` rows consume replay schedules;
- generated and replay rows match by seed and metadata;
- paired statistics are emitted;
- missing or mismatched pair metadata fails loudly.

Classify as `PRE_SPEND_BLOCKER` if:

- seed provenance cannot be reconstructed;
- sidecars or manifests lack schedules;
- the runner can fall back to fresh seeds;
- aggregation still accepts unmatched primary comparisons.

Classify as `CONTRACT_DRIFT` if:

- docs describe unmatched replay-control claims;
- tests validate implementation details outside the seed-alignment scope;
- the patch adds unrelated grammar, correctness, repair, token-cost, or timing
  behavior.

## Next Step

Start with Phase 2 sidecar backfill and its tests. The raw frozen artifacts
already expose enough `generation_seed` provenance to avoid regeneration, but
the sidecars remain the clearest current contract gap.
