# Cluster 2 Paired Replay Alignment Review TODO

<Environment>
  Repository root:
  /Users/alexeidelgado/Desktop/TritonGen

  Local venv interpreter:
  .venv/bin/python

  Conda base interpreter:
  /Users/alexeidelgado/miniconda3/bin/python

  Modal CLI:
  /Users/alexeidelgado/miniconda3/bin/modal

  Execution rules:
  - Always use `.venv/bin/python`.
  - Never use system python.
  - Do not run paper-scale jobs.
  - Smoke-scale validation only.
  - Preserve existing frozen JSONL artifacts unless regeneration is explicitly required by missing seed provenance.
  - Use `.contracts/agentic/cluster2_paired_replay_alignment_plan.md` as the scope contract.
</Environment>

<RuntimeAssumptions>
  Current branch already implements most paired-by-seed replay alignment work.

  Targeted tests currently pass for:
  - cluster2/tests/test_replay_controls.py
  - cluster2/tests/test_replay_manifest.py
  - cluster2/tests/test_run_cluster2_modal.py
  - shared/tests/test_aggregation.py
  - shared/tests/test_factorial_analysis.py

  Passing tests do not fully prove the plan contract because review probes found gaps in:
  - frozen metadata sidecar provenance
  - all-cells-before-generation preflight behavior
  - full seed schedule integrity validation beyond the default equal-attempt prefix.
</RuntimeAssumptions>

<TaskContext>
  The active fix is methodological. Cluster 2 primary claims require paired within-subject replay comparisons:
  - fresh C generation
  vs
  - frozen none replay

  and:
  - fresh G+C generation
  vs
  - frozen G replay

  The branch is close to the paired replay contract, but code review should not accept it while any part of the fix still:
  - leaves sidecar seed provenance implicit
  - spends generation before known requested-cell metadata mismatches are rejected
  - allows corrupt manifest schedules to hide outside the default n=6 validation prefix
  - carries unrelated grammar/documentation changes as part of the seed-alignment patch.
</TaskContext>

<ReviewFindings>
  [P2] Frozen metadata sidecars still do not record seed_schedule.
  The plan requires explicit seed schedules in the selected frozen metadata sidecars. The branch records schedules in cluster2/contracts/frozen_cluster1_artifacts_manifest.json, but outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json and outputs/cluster1/final_g_l4_n20.jsonl.meta.json still contain only run-level metadata and run_config. This leaves the original sidecar contract incomplete and means manifest metadata_sidecar hashes still point at sidecars without schedule provenance.

  [P2] Runner can generate earlier requested cells before a later requested-cell metadata mismatch fails.
  cluster2/experiments/run_cluster2_modal.py validates config-vs-schedule metadata inside _run_generated_cell, after _run_generated_condition has already entered the per-cell generation loop. A targeted probe with fp32 valid and fp16 max_new_tokens drift produced one fp32 generation call before the fp16 mismatch failed. The contract says mismatches must fail before generation begins, with no GPU spend and no partial fresh generation.

  [P2] Manifest integrity validates only the required_attempts prefix, not the full selected schedule.
  cluster2/replay/manifest.py _seed_schedule_failures checks only cell_entries[:required_attempts]. With the default equal-attempt window, corruption after seed 5 can pass validate_replay_manifest_integrity() and fail only later at n=20. The manifest contract says selected artifact seed schedules are dense and deterministic, not merely valid for the current prefix.

  [P3] Branch contains changes outside the paired replay seed-alignment scope.
  cluster1/README.md, cluster1/grammar/test_grammar_acceptance.py, and .gitignore changes are not part of deterministic paired-by-seed replay alignment. Split, revert, or explicitly justify these changes outside this fix so the paired replay patch remains reviewable.
</ReviewFindings>

<ImmediateTask>
  Close only the remaining paired replay correctness gaps and remove or quarantine branch-level scope drift.
</ImmediateTask>

<Rules>
  - Do not redesign the factorial.
  - Do not regenerate frozen JSONL artifacts unless sidecar provenance is truly unrecoverable.
  - Do not change grammar behavior.
  - Do not modify correctness logic.
  - Do not modify repair-loop semantics.
  - Do not introduce token-cost matching.
  - Do not introduce wall-time matching.
  - Do not add unrelated Cluster 1 grammar/documentation changes to this fix.
  - Seed alignment only.
  - Preserve smoke/development/paper tier semantics.
  - Fail loudly on missing or mismatched seed provenance.
  - No silent fallback to fresh seeds.
  - No generation call may happen after any requested-cell metadata mismatch is already knowable from the manifest.
</Rules>

<ScientificGoal>
  Preserve the intended within-subject interpretation:

  "For the same candidate seed/prompt/model configuration
   that frozen none or G would have produced,
   does C or G+C produce a better outcome?"

  Do not weaken the design into unmatched population analysis.
</ScientificGoal>

<RelevantFiles>
  Source plan:
  - .contracts/agentic/cluster2_paired_replay_alignment_plan.md

  Frozen sidecars still missing explicit schedules:
  - outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json
  - outputs/cluster1/final_g_l4_n20.jsonl.meta.json

  Manifest and loader:
  - cluster2/contracts/frozen_cluster1_artifacts_manifest.json
  - cluster2/contracts/phase_minus1_manifest.json
  - cluster2/replay/manifest.py
  - cluster2/replay/cluster1_controls.py

  Runner:
  - cluster2/experiments/run_cluster2_modal.py

  Aggregation/statistics:
  - shared/eval/aggregation.py
  - shared/eval/metrics/equal_attempts.py
  - shared/analysis/factorial.py

  Tests:
  - cluster2/tests/test_replay_controls.py
  - cluster2/tests/test_replay_manifest.py
  - cluster2/tests/test_run_cluster2_modal.py
  - shared/tests/test_aggregation.py
  - shared/tests/test_factorial_analysis.py

  Scope drift candidates:
  - cluster1/README.md
  - cluster1/grammar/test_grammar_acceptance.py
  - .gitignore
</RelevantFiles>

<DetailedWork>
  1. Backfill selected frozen metadata sidecars.
     Update:
     - outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json
     - outputs/cluster1/final_g_l4_n20.jsonl.meta.json

     Requirements:
     - Add explicit seed_schedule without changing frozen JSONL artifact bytes.
     - Derive schedule entries from existing raw rows, sidecar run_config, and manifest row_records.
     - Preserve or recompute sidecar JSON deterministically.
     - Update cluster2/contracts/frozen_cluster1_artifacts_manifest.json metadata_sidecar.sha256 and embedded metadata_sidecar.content.
     - Add a test that fails if either selected sidecar lacks seed_schedule.

  2. Add all-requested-cells generation preflight.
     Update:
     - cluster2/experiments/run_cluster2_modal.py

     Requirements:
     - Before the first generation call for C or G+C, load all requested replay schedules for all requested kernel_class/dtype cells.
     - Validate prompt_hash, model_id, known revisions, dtype, temperature, max_new_tokens, kernel identity, base_seed, and generation_seed for every requested schedule entry.
     - Only after the whole requested schedule passes, enter generation.
     - Keep attempt 0 paired to replay generation_seed.
     - Keep repair attempts on existing seed_for_attempt(base_seed, attempt_index).
     - Add a test where the first requested dtype is valid and the second requested dtype has a token-budget or prompt mismatch; assert generation_calls remains zero.

  3. Harden full schedule integrity validation.
     Update:
     - cluster2/replay/manifest.py

     Requirements:
     - Validate each selected artifact's full seed_schedule, not just cell_entries[:required_attempts].
     - Reject duplicate base_seed per (artifact, kernel_class, dtype).
     - Reject duplicate line_number in row_records.
     - Reject duplicate replay_pair_id.
     - Reject any non-dense full schedule for selected n20 artifacts.
     - Preserve coverage_failure_missing_frozen_control only for genuinely short artifacts such as task-agnostic n5 G.
     - Add a test that corrupts seed 10 of an n20 selected artifact and verifies validate_replay_manifest_integrity() fails under the default integrity path.

  4. Resolve branch-level scope drift.
     Inspect:
     - cluster1/README.md
     - cluster1/grammar/test_grammar_acceptance.py
     - .gitignore

     Requirements:
     - If these changes are not required for paired replay seed alignment, split them out of this branch or revert only those branch-owned edits.
     - If they are intentionally part of a separate accepted review thread, document that they are unrelated and should not be judged as part of PAIRED_REPLAY_VALID.

  5. Re-run focused validation.
     Requirements:
     - Run targeted replay, runner, aggregation, and factorial tests with .venv/bin/python.
     - Run manifest integrity with verify_artifact_hashes=True.
     - Do not run paper-scale jobs.
     - Do not run Modal smoke until the three P2 findings are closed.
</DetailedWork>

<ValidationCommands>
  Sidecar provenance audit:
  .venv/bin/python -c "import json; from pathlib import Path; paths=['outputs/cluster1/baseline_repaired_l4_n20.jsonl.meta.json','outputs/cluster1/final_g_l4_n20.jsonl.meta.json']; [print(p, 'seed_schedule' in json.loads(Path(p).read_text())) for p in paths]"

  Manifest integrity:
  .venv/bin/python -c "from cluster2.replay.manifest import validate_replay_manifest_integrity; print(validate_replay_manifest_integrity(verify_artifact_hashes=True).to_json())"

  Targeted tests:
  .venv/bin/python -m pytest cluster2/tests/test_replay_controls.py -v

  .venv/bin/python -m pytest cluster2/tests/test_replay_manifest.py -v

  .venv/bin/python -m pytest cluster2/tests/test_run_cluster2_modal.py -v

  .venv/bin/python -m pytest shared/tests/test_aggregation.py -v

  .venv/bin/python -m pytest shared/tests/test_factorial_analysis.py -v

  Broader shared/cluster2 validation:
  .venv/bin/python -m pytest shared/tests cluster2/tests -v
</ValidationCommands>

<DecisionCriteria>
  PAIRED_REPLAY_VALID if:
  - selected frozen sidecars and manifest both preserve deterministic seed_schedule
  - fresh C/G+C schedules are fully validated before any generation call
  - runner consumes replay seeds with no fallback
  - repair attempts preserve existing repair-loop seed semantics
  - aggregation emits paired bootstrap lift and McNemar-style binary summaries
  - unmatched or metadata-mismatched pairs are rejected
  - unrelated grammar/documentation changes are removed from this fix or explicitly scoped elsewhere

  PRE_SPEND_BLOCKER if:
  - either selected sidecar still lacks seed_schedule
  - any requested-cell metadata mismatch can be detected only after earlier generation has already occurred
  - manifest integrity accepts corrupt selected n20 schedule rows outside the default n=6 prefix
  - runner silently falls back to fresh seeds

  CONTRACT_DRIFT if:
  - the branch retains unrelated grammar, correctness, repair-loop, token-cost, wall-time, or documentation behavior as part of this seed-alignment fix
  - docs or contracts describe unmatched generated-vs-replay comparisons as primary claims
</DecisionCriteria>

<InterpretationRules>
  Treat these TODOs as correctness blockers for further GPU spend, not cosmetic cleanup.

  The implementation is close, but the remaining failures matter because:
  - sidecars are part of frozen provenance
  - preflight must prevent partial spend under known bad metadata
  - full selected schedules must be trustworthy before n20 paper-scale use
  - scope drift makes code review keep finding unrelated P2/P3 issues.
</InterpretationRules>

<OutputFormat>
  Return exactly:

  <report>
    <findings_closed>
    </findings_closed>

    <sidecar_backfill>
    </sidecar_backfill>

    <runner_preflight>
    </runner_preflight>

    <manifest_integrity>
    </manifest_integrity>

    <scope_drift>
    </scope_drift>

    <tests_run>
    </tests_run>

    <classification>
    </classification>

    <remaining_risks>
    </remaining_risks>

    <next_step_recommendation>
    </next_step_recommendation>
  </report>
</OutputFormat>
